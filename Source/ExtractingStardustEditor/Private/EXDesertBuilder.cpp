#include "EXDesertBuilder.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Async/ParallelFor.h"
#include "Components/SplineComponent.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/DirectionalLight.h"
#include "Engine/Engine.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PointLight.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerStart.h"
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "Materials/MaterialInterface.h"
#include "RenderingThread.h"
#include "UObject/Package.h"
#include "World/EXDesertTerrain.h"

namespace
{
	using FTerrain = FEXDesertTerrain;

	constexpr float CmPerM = 100.0f;
	/** Landscape Z scale 100 maps one height unit to 1/128 m, giving a range of +/-256 m around zero. */
	constexpr float HeightUnitsPerM = 128.0f;
	constexpr int32 SurfaceMapSize = 2048;
	const TCHAR* SurfaceMapPackage = TEXT("/Game/Desert/Textures/T_SurfaceMap");

	uint32 Hash(uint32 X)
	{
		X ^= X >> 16;
		X *= 0x7feb352dU;
		X ^= X >> 15;
		X *= 0x846ca68bU;
		X ^= X >> 16;
		return X;
	}

	float Hash01(uint32 Seed)
	{
		return static_cast<float>(Hash(Seed) & 0xFFFFFF) / static_cast<float>(0x1000000);
	}

	float Ground(const FVector2D& P)
	{
		return FTerrain::HeightAt(P.X, P.Y);
	}

	FVector2D Direction(float YawDeg)
	{
		const float Radians = FMath::DegreesToRadians(YawDeg);
		return FVector2D(FMath::Cos(Radians), FMath::Sin(Radians));
	}

	float YawOf(const FVector2D& V)
	{
		return FMath::RadiansToDegrees(FMath::Atan2(V.Y, V.X));
	}

	/** Springs that keep ground wet all year: the bowl where the routes rejoin and the head of the box canyon. */
	float Seep(const FVector2D& P)
	{
		const TArray<FTerrain::FCanyonPoint>& Canyon = FTerrain::CanyonPoints();
		const float Bowl = 1.0f - FVector2D::Distance(P, Canyon[0].Point) / 95.0f;
		const float Head = 1.0f - FVector2D::Distance(P, Canyon.Last().Point) / 140.0f;
		return FMath::Clamp(FMath::Max(Bowl, Head), 0.0f, 1.0f);
	}

	UStaticMesh* LoadMesh(const TCHAR* Folder, const TCHAR* Name)
	{
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("/Game/Desert/%s/%s.%s"), Folder, Name, Name));
		if (!Mesh)
		{
			UE_LOG(LogTemp, Error, TEXT("EXBUILD missing mesh %s/%s"), Folder, Name);
		}
		return Mesh;
	}

	UMaterialInterface* LoadMaterial(const TCHAR* Name)
	{
		UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(TEXT("/Game/Desert/%s.%s"), Name, Name));
		if (!Material)
		{
			UE_LOG(LogTemp, Error, TEXT("EXBUILD missing material %s"), Name);
		}
		return Material;
	}

	/** Mesh bounds in metres: half extents on X and Y around the pivot, and the top above it. */
	struct FMeshSize
	{
		float HalfX = 1.0f;
		float HalfY = 1.0f;
		float Top = 1.0f;
	};

	FMeshSize SizeOf(const UStaticMesh* Mesh)
	{
		const FBox Box = Mesh->GetBoundingBox();
		FMeshSize Size;
		Size.HalfX = static_cast<float>(FMath::Max(-Box.Min.X, Box.Max.X) / CmPerM);
		Size.HalfY = static_cast<float>(FMath::Max(-Box.Min.Y, Box.Max.Y) / CmPerM);
		Size.Top = static_cast<float>(Box.Max.Z / CmPerM);
		return Size;
	}

	/** Lowest ground under an elliptical footprint (m): a rock based there never floats on a slope. */
	float LowestGround(const FVector2D& Center, float HalfX, float HalfY, float YawDeg)
	{
		const FVector2D AxisX = Direction(YawDeg);
		const FVector2D AxisY(-AxisX.Y, AxisX.X);
		float Lowest = Ground(Center);
		for (const float Ring : { 0.5f, 0.8f, 1.0f })
		{
			for (int32 Step = 0; Step < 32; ++Step)
			{
				const float Angle = Step * 2.0f * PI / 32.0f;
				Lowest = FMath::Min(Lowest, Ground(Center + AxisX * (HalfX * Ring * FMath::Cos(Angle)) + AxisY * (HalfY * Ring * FMath::Sin(Angle))));
			}
		}
		return Lowest;
	}

	/** The meshes and the stratum materials of the sector (Docs/MAPA_01_RED_DUST_DIVIDE_S01.md, 3). */
	struct FRockSet
	{
		UStaticMesh* Boulders[3] = {};
		UStaticMesh* Cliffs[3] = {};
		UStaticMesh* Mesas[2] = {};
		UStaticMesh* Slabs[2] = {};
		UMaterialInterface* Navajo = nullptr;
		UMaterialInterface* Kayenta = nullptr;
		UMaterialInterface* Wingate = nullptr;

		bool Load()
		{
			const TCHAR* BoulderNames[] = { TEXT("SM_Boulder_A"), TEXT("SM_Boulder_B"), TEXT("SM_Boulder_C") };
			const TCHAR* CliffNames[] = { TEXT("SM_Cliff_A"), TEXT("SM_Cliff_B"), TEXT("SM_Cliff_C") };
			bool bOk = true;
			for (int32 Index = 0; Index < 3; ++Index)
			{
				Boulders[Index] = LoadMesh(TEXT("Rocks"), BoulderNames[Index]);
				Cliffs[Index] = LoadMesh(TEXT("Rocks"), CliffNames[Index]);
				bOk &= Boulders[Index] && Cliffs[Index];
			}
			Mesas[0] = LoadMesh(TEXT("Rocks"), TEXT("SM_Mesa_A"));
			Mesas[1] = LoadMesh(TEXT("Rocks"), TEXT("SM_Mesa_B"));
			Slabs[0] = LoadMesh(TEXT("S01"), TEXT("SM_Slab_A"));
			Slabs[1] = LoadMesh(TEXT("S01"), TEXT("SM_Slab_B"));
			Navajo = LoadMaterial(TEXT("MI_Navajo"));
			Kayenta = LoadMaterial(TEXT("MI_Kayenta"));
			Wingate = LoadMaterial(TEXT("MI_Wingate"));
			return bOk && Mesas[0] && Mesas[1] && Slabs[0] && Slabs[1] && Navajo && Kayenta && Wingate;
		}
	};

	struct FPlacer
	{
		UWorld* World = nullptr;
		FRockSet Rocks;
		int32 Count = 0;

		AStaticMeshActor* Spawn(UStaticMesh* Mesh, UMaterialInterface* Material, const FVector& LocationM, const FRotator& Rotation,
			const FVector& Scale, const FName Folder)
		{
			if (!Mesh)
			{
				return nullptr;
			}
			AStaticMeshActor* Actor = World->SpawnActor<AStaticMeshActor>(LocationM * CmPerM, Rotation);
			UStaticMeshComponent* Component = Actor->GetStaticMeshComponent();
			Component->SetStaticMesh(Mesh);
			if (Material)
			{
				Component->SetMaterial(0, Material);
			}
			Actor->SetActorScale3D(Scale);
			Actor->SetFolderPath(Folder);
			++Count;
			return Actor;
		}

		/** A block fallen from the wall above, resting on the slope at P. Never closer than MinRouteM to a race line. */
		void Boulder(UMaterialInterface* Material, const FVector2D& P, float Size, uint32 Seed, float MinRouteM)
		{
			if (FTerrain::RouteDistance(P.X, P.Y) < MinRouteM)
			{
				return;
			}
			float Rest = Ground(P);
			for (int32 Step = 0; Step < 6; ++Step)
			{
				Rest = FMath::Min(Rest, Ground(P + Direction(Step * 60.0f) * (2.0f * Size)));
			}
			Spawn(Rocks.Boulders[Hash(Seed) % 3], Material, FVector(P, Rest - 0.45f * Size),
				FRotator(0.0f, Hash01(Seed + 1) * 360.0f, 0.0f), FVector(Size), TEXT("S01/Talus"));
		}

		/** Talus all around the foot of a standing rock: the wall is found with a trace at mid height, so the blocks
		 *  lie a few metres out from the real (irregular) wall. */
		void FootTalus(UMaterialInterface* Material, const FVector2D& Center, float Reach, float TraceHeight, int32 Stones,
			uint32 Seed, float MinRouteM)
		{
			for (int32 Stone = 0; Stone < Stones; ++Stone)
			{
				const uint32 S = Seed * 977 + Stone * 31;
				const FVector2D Out = Direction((Stone + 0.7f * Hash01(S)) * 360.0f / Stones);
				FHitResult Hit;
				const FVector Start(FVector2D(Center + Out * Reach) * CmPerM, TraceHeight * CmPerM);
				const FVector End(FVector2D(Center) * CmPerM, TraceHeight * CmPerM);
				if (!World->LineTraceSingleByChannel(Hit, Start, End, ECC_WorldStatic))
				{
					continue;
				}
				const FVector2D Wall = FVector2D(Hit.ImpactPoint) / CmPerM;
				Boulder(Material, Wall + Out * (2.0f + 7.0f * Hash01(S + 1)), 0.45f + 0.8f * Hash01(S + 2), S + 3, MinRouteM);
			}
		}
	};

	/** Arch mesa, island butte and the Navajo mesas that close the sector, each on its talus mound. */
	void PlaceLandmarks(FPlacer& Placer)
	{
		// Arch mesa: the fin stands on the mesh's -Y side, turned so the opening faces the basin.
		const FTerrain::FLandmark Arch = FTerrain::MesaArch();
		if (UStaticMesh* Mesh = LoadMesh(TEXT("S01"), TEXT("SM_MesaArch")))
		{
			const FMeshSize Size = SizeOf(Mesh);
			const float Yaw = Arch.YawDeg + 90.0f;
			const float Base = LowestGround(Arch.Point, Size.HalfX, Size.HalfY, Yaw) - 1.0f;
			Placer.Spawn(Mesh, Placer.Rocks.Navajo, FVector(Arch.Point, Base), FRotator(0.0f, Yaw, 0.0f), FVector(1.0f), TEXT("S01/Landmarks"));
			Placer.FootTalus(Placer.Rocks.Navajo, Arch.Point, Size.HalfX * 1.6f, Base + 30.0f, 16, 101, 30.0f);
		}

		const FTerrain::FLandmark Island = FTerrain::IslandButte();
		if (UStaticMesh* Mesh = LoadMesh(TEXT("S01"), TEXT("SM_IslandButte")))
		{
			const FMeshSize Size = SizeOf(Mesh);
			const float Base = LowestGround(Island.Point, Size.HalfX, Size.HalfY, Island.YawDeg) - 1.0f;
			Placer.Spawn(Mesh, Placer.Rocks.Navajo, FVector(Island.Point, Base), FRotator(0.0f, Island.YawDeg, 0.0f), FVector(1.0f), TEXT("S01/Landmarks"));
			Placer.FootTalus(Placer.Rocks.Navajo, Island.Point, Size.HalfX * 1.6f, Base + 40.0f, 12, 202, 34.0f);
		}

		// Boundary mesas, alternating the two mesa shapes, scaled to the designed footprint and height.
		TArray<FTerrain::FLandmark> Boundary;
		FTerrain::BoundaryMesas(Boundary);
		for (int32 Index = 0; Index < Boundary.Num(); ++Index)
		{
			const FTerrain::FLandmark& Site = Boundary[Index];
			UStaticMesh* Mesh = Placer.Rocks.Mesas[Index % 2];
			const FMeshSize Size = SizeOf(Mesh);
			const float ScaleXY = Site.Radius / FMath::Max(Size.HalfX, Size.HalfY);
			const float Base = LowestGround(Site.Point, Size.HalfX * ScaleXY, Size.HalfY * ScaleXY, Site.YawDeg) - 2.0f;
			const float ScaleZ = (Ground(Site.Point) + Site.Height - Base) / Size.Top;
			Placer.Spawn(Mesh, Placer.Rocks.Navajo, FVector(Site.Point, Base), FRotator(0.0f, Site.YawDeg, 0.0f),
				FVector(ScaleXY, ScaleXY, ScaleZ), TEXT("S01/BoundaryMesas"));
		}
	}

	/** Four Kayenta slabs on their flat beds, each lifting 1.2 m at the far end (flow jumps), and broken slabs
	 *  lying flush beside the RACING line so the jumps read as part of one fractured bench. */
	void PlaceSlabs(FPlacer& Placer)
	{
		TArray<FTerrain::FSlab> Jumps;
		FTerrain::RacingSlabs(Jumps);
		const float Twist[] = { 2.0f, -3.0f, 1.0f, -2.0f };
		const float TopHalfLength[] = { 17.0f, 15.0f };
		for (int32 Index = 0; Index < Jumps.Num(); ++Index)
		{
			const FTerrain::FSlab& Slab = Jumps[Index];
			const int32 Kind = Index % 2;
			const float Bed = Ground(Slab.Point);
			const float EntryTop = Bed - 0.1f;
			const float ExitTop = Bed + 1.2f;
			const float PitchDeg = FMath::RadiansToDegrees(FMath::Atan2(ExitTop - EntryTop, 2.0f * TopHalfLength[Kind]));
			Placer.Spawn(Placer.Rocks.Slabs[Kind], Placer.Rocks.Kayenta, FVector(Slab.Point, (EntryTop + ExitTop) * 0.5f),
				FRotator(PitchDeg, Slab.YawDeg + Twist[Index % 4], 0.0f), FVector(1.0f), TEXT("S01/Slabs"));
			UE_LOG(LogTemp, Display, TEXT("EXBUILD jump slab %d at (%.0f, %.0f) pitch %.1f deg, lip %.2f m"), Index, Slab.Point.X, Slab.Point.Y,
				PitchDeg, ExitTop - Bed);
		}
		// Flush slabs halfway between the jumps, 44 m to alternate sides, lying on the ground's own tilt.
		for (int32 Index = 0; Index + 1 < Jumps.Num(); ++Index)
		{
			const FVector2D Mid = (Jumps[Index].Point + Jumps[Index + 1].Point) * 0.5f;
			const FVector2D Along = (Jumps[Index + 1].Point - Jumps[Index].Point).GetSafeNormal();
			const FVector2D Side(-Along.Y, Along.X);
			for (const float Offset : { 44.0f, -50.0f })
			{
				const float Sign = (Index % 2 == 0) ? 1.0f : -1.0f;
				const FVector2D Center = Mid + Side * Offset * Sign;
				const float Yaw = YawOf(Along) + 14.0f * Sign * (Offset > 0.0f ? 1.0f : -0.6f);
				const FVector2D Forward = Direction(Yaw);
				const FVector2D Right(-Forward.Y, Forward.X);
				const float Front = Ground(Center + Forward * 13.0f);
				const float Back = Ground(Center - Forward * 13.0f);
				const float RightSide = Ground(Center + Right * 10.0f);
				const float LeftSide = Ground(Center - Right * 10.0f);
				const float Pitch = FMath::RadiansToDegrees(FMath::Atan2(Front - Back, 26.0f));
				float Roll = FMath::RadiansToDegrees(FMath::Atan2(RightSide - LeftSide, 20.0f));
				// Match the roll sign to the engine's convention: the slab's right edge must follow the ground.
				if (FMath::Sign(FRotator(0.0f, Yaw, Roll).RotateVector(FVector(0.0f, 10.0f, 0.0f)).Z) != FMath::Sign(RightSide - LeftSide))
				{
					Roll = -Roll;
				}
				const float Top = (Front + Back + RightSide + LeftSide) * 0.25f + 0.12f;
				Placer.Spawn(Placer.Rocks.Slabs[(Index + 1) % 2], Placer.Rocks.Kayenta, FVector(Center, Top), FRotator(Pitch, Yaw, Roll),
					FVector(0.8f + 0.15f * Index, 0.85f, 1.0f), TEXT("S01/Slabs"));
			}
		}
	}

	/** Wingate cliffs on both sides of the canyon head wherever it is cut deeper than 12 m: the cliff face stands on
	 *  the upper part of the wall slope, the Chinle talus below it, blocks fallen from it on the talus. */
	void PlaceCanyonWalls(FPlacer& Placer)
	{
		int32 Placed = 0;
		auto Wall = [&Placer, &Placed](const FVector2D& Base, const FVector2D& Outward, float HalfWidth, float Floor)
		{
			const uint32 Seed = 5000 + Placed;
			const float Bench = Ground(Base + Outward * (HalfWidth + 50.0f));
			const float Height = Bench - Floor;
			if (Height < 12.0f)
			{
				return;
			}
			const float WallWidth = FTerrain::CanyonWallWidth(Height);
			UStaticMesh* Mesh = Placer.Rocks.Cliffs[Placed % 3];
			const FMeshSize Size = SizeOf(Mesh);
			const float ScaleXY = 95.0f / (2.0f * Size.HalfX);
			const float Front = HalfWidth + 0.45f * WallWidth;
			const FVector2D Center = Base + Outward * (Front + Size.HalfY * ScaleXY);
			const float BaseZ = Floor + 0.2f * Height;
			const float ScaleZ = (Bench + 3.0f - BaseZ) / Size.Top;
			const FVector2D Tangent(-Outward.Y, Outward.X);
			Placer.Spawn(Mesh, Placer.Rocks.Wingate, FVector(Center, BaseZ), FRotator(0.0f, YawOf(Tangent) + (Hash01(Seed) - 0.5f) * 8.0f, 0.0f),
				FVector(ScaleXY, ScaleXY, ScaleZ), TEXT("S01/CanyonWalls"));
			// Fallen blocks come to rest at the foot of the talus, where the slope eases onto the floor.
			for (int32 Stone = 0; Stone < 3; ++Stone)
			{
				const uint32 S = Seed * 131 + Stone;
				const FVector2D P = Base + Tangent * ((Stone - 1) * 26.0f + (Hash01(S) - 0.5f) * 14.0f)
					+ Outward * (HalfWidth + 1.5f + 0.12f * WallWidth * Hash01(S + 1));
				Placer.Boulder(Placer.Rocks.Wingate, P, 0.4f + 0.5f * Hash01(S + 2), S + 3, HalfWidth + 1.0f);
			}
			++Placed;
		};

		const TArray<FTerrain::FCanyonPoint>& Points = FTerrain::CanyonPoints();
		float Along = 0.0f;
		float Next = 40.0f;
		for (int32 Index = 1; Index < Points.Num(); ++Index)
		{
			Along += FVector2D::Distance(Points[Index - 1].Point, Points[Index].Point);
			if (Along < Next)
			{
				continue;
			}
			Next = Along + 64.0f;
			const FTerrain::FCanyonPoint& Point = Points[Index];
			const FVector2D Tangent = (Point.Point - Points[Index - 1].Point).GetSafeNormal();
			const FVector2D Normal(-Tangent.Y, Tangent.X);
			Wall(Point.Point, Normal, Point.HalfWidth, Point.Floor);
			Wall(Point.Point, -Normal, Point.HalfWidth, Point.Floor);
		}
		// Box canyon head: the walls close around the end of the cut until S02 continues it.
		const FTerrain::FCanyonPoint& End = Points.Last();
		const FVector2D Tangent = (End.Point - Points[Points.Num() - 2].Point).GetSafeNormal();
		for (const float Turn : { -60.0f, 0.0f, 60.0f })
		{
			Wall(End.Point, Tangent.GetRotated(Turn), End.HalfWidth, End.Floor);
		}
		UE_LOG(LogTemp, Display, TEXT("EXBUILD canyon walls: %d Wingate cliffs"), Placed);
	}

	/** Navajo cliff band along the tableland edge to the north and east: it stands on the upper half of the rise,
	 *  talus below. Skipped where a boundary mesa already forms the edge. */
	void PlaceEscarpment(FPlacer& Placer)
	{
		TArray<FTerrain::FLandmark> Mesas;
		FTerrain::BoundaryMesas(Mesas);
		constexpr float Mid = 55.0f;
		TArray<FVector2D> North;
		TArray<FVector2D> East;
		for (float X = -2900.0f; X <= 2300.0f; X += 80.0f)
		{
			for (float Y = 1250.0f; Y < 2300.0f; Y += 4.0f)
			{
				if (FTerrain::HeightAt(X, Y) > Mid)
				{
					North.Add(FVector2D(X, Y));
					break;
				}
			}
		}
		for (float Y = -2900.0f; Y <= 1500.0f; Y += 80.0f)
		{
			for (float X = 2150.0f; X < 2950.0f; X += 4.0f)
			{
				if (FTerrain::HeightAt(X, Y) > Mid)
				{
					East.Add(FVector2D(X, Y));
					break;
				}
			}
		}
		int32 Placed = 0;
		const TPair<TArray<FVector2D>*, FVector2D> Edges[] = { { &North, FVector2D(0.0f, -1.0f) }, { &East, FVector2D(-1.0f, 0.0f) } };
		for (const TPair<TArray<FVector2D>*, FVector2D>& Edge : Edges)
		{
			const TArray<FVector2D>& Points = *Edge.Key;
			for (int32 Index = 0; Index < Points.Num(); ++Index)
			{
				const FVector2D& Point = Points[Index];
				bool bCovered = false;
				for (const FTerrain::FLandmark& Mesa : Mesas)
				{
					bCovered |= FVector2D::Distance(Point, Mesa.Point) < Mesa.Radius + 40.0f;
				}
				if (bCovered)
				{
					continue;
				}
				const FVector2D Along = (Points[FMath::Min(Index + 1, Points.Num() - 1)] - Points[FMath::Max(Index - 1, 0)]).GetSafeNormal();
				FVector2D Outward(-Along.Y, Along.X);
				if (FVector2D::DotProduct(Outward, Edge.Value) < 0.0f)
				{
					Outward = -Outward;
				}
				UStaticMesh* Mesh = Placer.Rocks.Cliffs[(Placed + 1) % 3];
				const FMeshSize Size = SizeOf(Mesh);
				const float ScaleXY = 115.0f / (2.0f * Size.HalfX);
				const float BaseZ = Ground(Point) - 4.0f;
				const float Top = Ground(Point - Outward * 180.0f) + 3.0f;
				Placer.Spawn(Mesh, Placer.Rocks.Navajo, FVector(Point - Outward * (Size.HalfY * ScaleXY), BaseZ),
					FRotator(0.0f, YawOf(Along) + (Hash01(9000 + Placed) - 0.5f) * 10.0f, 0.0f),
					FVector(ScaleXY, ScaleXY, (Top - BaseZ) / Size.Top), TEXT("S01/Escarpment"));
				++Placed;
			}
		}
		UE_LOG(LogTemp, Display, TEXT("EXBUILD escarpment: %d Navajo cliffs"), Placed);
	}

	// ---- Vegetation: every plant grows where its water, rock and sand needs are met. ----

	enum EPlant { Cottonwood, Juniper, Willow, Sage, DeadBrush, DryGrass, GreenGrass, PricklyPear, Yucca, PlantCount };

	/** Vegetation never collides: at 400+ km/h a bush or a tree must not stop the craft (player decision). */
	struct FPlantKind
	{
		const TCHAR* Meshes[2];
		bool bShadow;
		float CullM;   // 0: always drawn
		float ClearM;  // closest distance to a race line
		float MinScale;
		float MaxScale;
		int32 MinCluster;
		int32 MaxCluster;
		float ClusterM;
	};

	const FPlantKind PlantKinds[PlantCount] = {
		{ { TEXT("SM_Cottonwood_A"), TEXT("SM_Cottonwood_B") }, true, 0.0f, 34.0f, 0.8f, 1.15f, 1, 1, 0.0f },
		{ { TEXT("SM_Juniper_A"), TEXT("SM_Juniper_B") }, true, 0.0f, 30.0f, 0.7f, 1.25f, 1, 1, 0.0f },
		{ { TEXT("SM_Willow"), nullptr }, true, 700.0f, 30.0f, 0.8f, 1.2f, 1, 3, 3.5f },
		{ { TEXT("SM_Sagebrush"), nullptr }, true, 400.0f, 24.0f, 0.7f, 1.3f, 1, 3, 2.5f },
		{ { TEXT("SM_DeadBrush"), nullptr }, true, 300.0f, 24.0f, 0.7f, 1.3f, 1, 2, 2.0f },
		{ { TEXT("SM_DryGrass"), nullptr }, false, 180.0f, 22.0f, 0.7f, 1.4f, 4, 7, 1.8f },
		{ { TEXT("SM_GreenGrass"), nullptr }, false, 180.0f, 22.0f, 0.8f, 1.4f, 5, 9, 2.2f },
		{ { TEXT("SM_PricklyPear"), nullptr }, true, 300.0f, 26.0f, 0.7f, 1.3f, 1, 2, 1.5f },
		{ { TEXT("SM_Yucca"), nullptr }, true, 350.0f, 26.0f, 0.8f, 1.2f, 1, 1, 0.0f } };

	/** How likely each plant is to take a 10 m cell at P. Cottonwoods and willows need water under the wash banks
	 *  or a seep; junipers root in slickrock cracks and gravel; sage, grass, yucca and cactus want sandy soil;
	 *  dunes stay bare in the core, dead brush on their margins; nothing on cliffs or on the race lines. */
	bool PlantChances(const FVector2D& P, float OutChance[PlantCount])
	{
		FMemory::Memzero(OutChance, sizeof(float) * PlantCount);
		const float Route = FTerrain::RouteDistance(P.X, P.Y);
		if (Route < 22.0f)
		{
			return false;
		}
		const float SlopeX = Ground(P + FVector2D(2.0f, 0.0f)) - Ground(P - FVector2D(2.0f, 0.0f));
		const float SlopeY = Ground(P + FVector2D(0.0f, 2.0f)) - Ground(P - FVector2D(0.0f, 2.0f));
		if (FMath::Sqrt(SlopeX * SlopeX + SlopeY * SlopeY) / 4.0f > 0.55f)
		{
			return false;
		}
		const FLinearColor Surface = FTerrain::SurfaceAt(P.X, P.Y);
		const float Slick = Surface.R;
		const float Deep = Surface.G;
		const float Gravel = Surface.B;
		const float Wash = FTerrain::WashDistance(P.X, P.Y);
		const float Bank = Wash > 14.0f ? FMath::Exp(-(Wash - 14.0f) / 30.0f) : 0.3f;
		const float Wet = FMath::Max(Bank, Seep(P));
		const float Dry = 1.0f - Wet;
		const float Soil = (1.0f - Deep) * (1.0f - 0.6f * Slick);
		const float Margin = 4.0f * Deep * (1.0f - Deep);
		const float Near = Route < 450.0f ? 1.0f : 0.0f;

		OutChance[Cottonwood] = 0.06f * Wet * Wet * (1.0f - Deep);
		OutChance[Willow] = Near * 0.1f * Wet * Wet * (1.0f - Deep);
		OutChance[GreenGrass] = Near * 0.3f * Wet * (1.0f - Deep) * (1.0f - Slick);
		OutChance[Juniper] = (1.0f - Deep) * (0.006f + 0.04f * Slick + 0.025f * Gravel) * (1.0f - 0.8f * Wet);
		OutChance[Sage] = Near * Soil * (0.03f + 0.1f * Bank) * (1.0f - 0.5f * Seep(P));
		OutChance[DryGrass] = Near * (1.0f - 0.7f * Slick) * (0.04f + 0.1f * Margin) * Dry;
		OutChance[PricklyPear] = Near * (1.0f - Deep) * (0.008f + 0.025f * Gravel + 0.012f * Slick) * Dry;
		OutChance[Yucca] = Near * Soil * 0.012f * Dry;
		OutChance[DeadBrush] = Near * (0.006f + 0.05f * Margin + 0.015f * Gravel) * Dry;

		// Plants gather in patches (seed spread, small soil differences), never as an even sprinkle.
		const float Patch = FMath::Clamp(0.5f + 0.9f * FMath::PerlinNoise2D(P / 140.0f), 0.0f, 1.0f);
		for (int32 Kind = 0; Kind < PlantCount; ++Kind)
		{
			OutChance[Kind] = Route < PlantKinds[Kind].ClearM ? 0.0f : OutChance[Kind] * (0.3f + 1.4f * Patch);
		}
		return true;
	}

	struct FPlantInstance
	{
		int32 Kind;
		int32 Variant;
		FTransform Transform;
	};

	void PlaceVegetation(UWorld* World)
	{
		constexpr float CellM = 10.0f;
		const FVector2D Min(-2800.0f, -2400.0f);
		const FVector2D Max(2750.0f, 1500.0f);
		const int32 Columns = FMath::CeilToInt((Max.X - Min.X) / CellM);
		const int32 Rows = FMath::CeilToInt((Max.Y - Min.Y) / CellM);
		TArray<TArray<FPlantInstance>> RowInstances;
		RowInstances.SetNum(Rows);
		ParallelFor(Rows, [&](int32 Row)
		{
			float Chance[PlantCount];
			for (int32 Column = 0; Column < Columns; ++Column)
			{
				const uint32 Seed = Hash(static_cast<uint32>(Row * 7919 + Column * 104729 + 17));
				const FVector2D P(Min.X + (Column + 0.5f + 0.9f * (Hash01(Seed) - 0.5f)) * CellM, Min.Y + (Row + 0.5f + 0.9f * (Hash01(Seed + 1) - 0.5f)) * CellM);
				if (!PlantChances(P, Chance))
				{
					continue;
				}
				float Pick = Hash01(Seed + 2);
				int32 Kind = INDEX_NONE;
				for (int32 Candidate = 0; Candidate < PlantCount; ++Candidate)
				{
					if (Pick < Chance[Candidate])
					{
						Kind = Candidate;
						break;
					}
					Pick -= Chance[Candidate];
				}
				if (Kind == INDEX_NONE)
				{
					continue;
				}
				const FPlantKind& Plant = PlantKinds[Kind];
				const int32 Variants = Plant.Meshes[1] ? 2 : 1;
				const int32 Members = Plant.MinCluster + static_cast<int32>(Hash(Seed + 3) % static_cast<uint32>(Plant.MaxCluster - Plant.MinCluster + 1));
				for (int32 Member = 0; Member < Members; ++Member)
				{
					const uint32 S = Seed + 10 + Member * 7;
					const FVector2D Q = P + Direction(Hash01(S) * 360.0f) * (Member == 0 ? 0.0f : Plant.ClusterM * FMath::Sqrt(Hash01(S + 1)));
					if (Member > 0 && FTerrain::RouteDistance(Q.X, Q.Y) < Plant.ClearM)
					{
						continue;
					}
					float Z = Ground(Q);
					for (int32 Step = 0; Step < 4; ++Step)
					{
						Z = FMath::Min(Z, Ground(Q + Direction(Step * 90.0f) * 0.6f));
					}
					const float Scale = FMath::Lerp(Plant.MinScale, Plant.MaxScale, Hash01(S + 2));
					RowInstances[Row].Add({ Kind, static_cast<int32>(Hash(S + 3) % static_cast<uint32>(Variants)),
						FTransform(FRotator(0.0f, Hash01(S + 4) * 360.0f, 0.0f), FVector(Q, Z - 0.05f) * CmPerM, FVector(Scale)) });
				}
			}
		});

		// One instanced component per plant mesh.
		TArray<FTransform> Buckets[PlantCount][2];
		for (const TArray<FPlantInstance>& Instances : RowInstances)
		{
			for (const FPlantInstance& Instance : Instances)
			{
				Buckets[Instance.Kind][Instance.Variant].Add(Instance.Transform);
			}
		}
		int32 Total = 0;
		for (int32 Kind = 0; Kind < PlantCount; ++Kind)
		{
			const FPlantKind& Plant = PlantKinds[Kind];
			for (int32 Variant = 0; Variant < 2; ++Variant)
			{
				const TCHAR* Name = Plant.Meshes[Variant];
				if (!Name || Buckets[Kind][Variant].Num() == 0)
				{
					continue;
				}
				UStaticMesh* Mesh = LoadMesh(TEXT("Plants"), Name);
				if (!Mesh)
				{
					continue;
				}
				AActor* Holder = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity);
				UHierarchicalInstancedStaticMeshComponent* Component = NewObject<UHierarchicalInstancedStaticMeshComponent>(Holder, TEXT("Instances"));
				Component->SetMobility(EComponentMobility::Static);
				Component->SetStaticMesh(Mesh);
				Component->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
				Component->SetCastShadow(Plant.bShadow);
				if (Plant.CullM > 0.0f)
				{
					Component->SetCullDistances(FMath::RoundToInt(Plant.CullM * 0.75f * CmPerM), FMath::RoundToInt(Plant.CullM * CmPerM));
				}
				Holder->SetRootComponent(Component);
				Holder->AddInstanceComponent(Component);
				Component->RegisterComponent();
				Component->AddInstances(Buckets[Kind][Variant], false, true);
				Holder->SetActorLabel(FString::Printf(TEXT("Plants_%s"), Name));
				Holder->SetFolderPath(TEXT("S01/Vegetation"));
				Total += Buckets[Kind][Variant].Num();
				UE_LOG(LogTemp, Display, TEXT("EXBUILD vegetation %s: %d"), Name, Buckets[Kind][Variant].Num());
			}
		}
		UE_LOG(LogTemp, Display, TEXT("EXBUILD vegetation total %d plants"), Total);
	}

	/** Sun, sky and dusty air. Movable lighting only: the project has no baked lighting. */
	void AddSky(UWorld* World, float FogDensity)
	{
		ADirectionalLight* Sun = World->SpawnActor<ADirectionalLight>(FVector(0.0f, 0.0f, 50000.0f), FRotator(-23.0f, -35.0f, 0.0f));   // low golden-hour sun: long raking shadows give the canyons depth
		if (UDirectionalLightComponent* SunLight = Cast<UDirectionalLightComponent>(Sun->GetLightComponent()))
		{
			SunLight->SetMobility(EComponentMobility::Movable);
			SunLight->SetIntensity(13.0f);   // the sun is lower than before: more lux for the same exposure
			SunLight->SetLightColor(FLinearColor(1.0f, 0.86f, 0.68f));
			SunLight->SetEnableLightShaftBloom(true);   // god rays through the dust
			SunLight->SetBloomScale(0.22f);
			SunLight->SetBloomThreshold(0.0f);
			SunLight->SetBloomTint(FColor(255, 196, 140));
			SunLight->SetVolumetricScatteringIntensity(1.6f);
			SunLight->ContactShadowLength = 0.04f;
			SunLight->SetAtmosphereSunLight(true);
			SunLight->SetDynamicShadowDistanceMovableLight(60000.0f);
		}
		// The sky: a dusty desert atmosphere (more aerosol, so the low sun burns orange and the distance goes hazy) and
		// real volumetric clouds high up, lit by the sun and seen by Lumen (player, 2026-10-26: cinematic).
		if (ASkyAtmosphere* Atmosphere = World->SpawnActor<ASkyAtmosphere>(FVector::ZeroVector, FRotator::ZeroRotator))
		{
			if (USkyAtmosphereComponent* Air = Atmosphere->GetComponent())
			{
				Air->SetMieScatteringScale(0.0075f);
				Air->SetMieAnisotropy(0.82f);
				Air->SetRayleighScatteringScale(0.031f);
			}
		}
		if (AVolumetricCloud* Clouds = World->SpawnActor<AVolumetricCloud>(FVector::ZeroVector, FRotator::ZeroRotator))
		{
			if (UVolumetricCloudComponent* Cloud = Clouds->FindComponentByClass<UVolumetricCloudComponent>())
			{
				Cloud->SetLayerBottomAltitude(4.5f);
				Cloud->SetLayerHeight(6.0f);
			}
		}
		ASkyLight* Sky = World->SpawnActor<ASkyLight>(FVector(0.0f, 0.0f, 20000.0f), FRotator::ZeroRotator);
		if (USkyLightComponent* SkyLight = Sky->GetLightComponent())
		{
			SkyLight->SetMobility(EComponentMobility::Movable);
			SkyLight->SetRealTimeCapture(true);
			SkyLight->SetIntensity(1.15f);
			SkyLight->SetLowerHemisphereColor(FLinearColor(0.34f, 0.2f, 0.12f));   // warm sand bounce under the rocks
		}
		AExponentialHeightFog* Fog = World->SpawnActor<AExponentialHeightFog>(FVector(0.0f, 0.0f, 0.0f), FRotator::ZeroRotator);
		if (UExponentialHeightFogComponent* FogComponent = Fog->GetComponent())
		{
			FogComponent->SetFogDensity(FogDensity);
			FogComponent->SetFogHeightFalloff(0.12f);
			FogComponent->SetFogInscatteringColor(FLinearColor(0.62f, 0.47f, 0.36f));
			FogComponent->SetDirectionalInscatteringColor(FLinearColor(1.0f, 0.72f, 0.48f));
			FogComponent->SetStartDistance(4000.0f);
			FogComponent->SetVolumetricFog(true);   // dust hanging in the air, lit by the sun
			FogComponent->SetVolumetricFogScatteringDistribution(0.4f);
			FogComponent->SetVolumetricFogExtinctionScale(1.2f);
			FogComponent->SetVolumetricFogDistance(30000.0f);		}
		APostProcessVolume* Post = World->SpawnActor<APostProcessVolume>(FVector::ZeroVector, FRotator::ZeroRotator);
		Post->bUnbound = true;
		Post->Settings.bOverride_BloomIntensity = true;
		Post->Settings.BloomIntensity = 0.75f;
		Post->Settings.bOverride_VignetteIntensity = true;
		Post->Settings.VignetteIntensity = 0.42f;
		Post->Settings.bOverride_WhiteTemp = true;
		Post->Settings.WhiteTemp = 6300.0f;
		// Cinematic grade: warm highlights, cool shadows, a little more contrast and colour, ambient occlusion, speed blur,
		// a hint of lens fringe and film grain.
		Post->Settings.bOverride_ColorSaturation = true;
		Post->Settings.ColorSaturation = FVector4(1.14, 1.14, 1.14, 1.0);
		Post->Settings.bOverride_ColorContrast = true;
		Post->Settings.ColorContrast = FVector4(1.1, 1.1, 1.1, 1.0);
		Post->Settings.bOverride_ColorGainHighlights = true;
		Post->Settings.ColorGainHighlights = FVector4(1.05, 1.0, 0.9, 1.0);
		Post->Settings.bOverride_ColorGainShadows = true;
		Post->Settings.ColorGainShadows = FVector4(0.92, 0.97, 1.08, 1.0);
		Post->Settings.bOverride_AmbientOcclusionIntensity = true;
		Post->Settings.AmbientOcclusionIntensity = 0.75f;
		Post->Settings.bOverride_AmbientOcclusionRadius = true;
		Post->Settings.AmbientOcclusionRadius = 220.0f;
		Post->Settings.bOverride_MotionBlurAmount = true;
		Post->Settings.MotionBlurAmount = 0.35f;
		Post->Settings.bOverride_SceneFringeIntensity = true;
		Post->Settings.SceneFringeIntensity = 0.6f;
		Post->Settings.bOverride_FilmGrainIntensity = true;
		Post->Settings.FilmGrainIntensity = 0.07f;
		// Lumen: a little sky light into the deep shade (the cave, the slot canyons), and lens flares off the sun.
		Post->Settings.bOverride_LumenSkylightLeaking = true;
		Post->Settings.LumenSkylightLeaking = 0.12f;
		Post->Settings.bOverride_LensFlareIntensity = true;
		Post->Settings.LensFlareIntensity = 0.35f;
	}

	/** Invisible walls around an area (cm), 1.2 km tall around CenterZ: the map edge can never be crossed. */
	void AddEdgeWalls(UWorld* World, const FBox2D& Area, float CenterZ)
	{
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		if (!Cube)
		{
			return;
		}
		const FVector2D Center = Area.GetCenter();
		const FVector2D Size = Area.GetSize() + FVector2D(4000.0f, 4000.0f);
		const FVector Centers[] = { FVector(Area.Max.X, Center.Y, CenterZ), FVector(Area.Min.X, Center.Y, CenterZ),
			FVector(Center.X, Area.Max.Y, CenterZ), FVector(Center.X, Area.Min.Y, CenterZ) };
		for (int32 Index = 0; Index < 4; ++Index)
		{
			const bool bAlongY = Index < 2;
			AStaticMeshActor* Wall = World->SpawnActor<AStaticMeshActor>(Centers[Index], FRotator::ZeroRotator);
			Wall->GetStaticMeshComponent()->SetStaticMesh(Cube);
			Wall->SetActorScale3D(bAlongY ? FVector(10.0f, Size.Y / 100.0f, 1200.0f) : FVector(Size.X / 100.0f, 10.0f, 1200.0f));
			Wall->SetActorHiddenInGame(true);
		}
	}

	void PlaceS01(UWorld* World)
	{
		FPlacer Placer;
		Placer.World = World;
		if (!Placer.Rocks.Load())
		{
			UE_LOG(LogTemp, Error, TEXT("EXBUILD S01 rock set incomplete: run Scripts/import_rocks.py and import_s01.py first"));
			return;
		}
		PlaceLandmarks(Placer);
		PlaceSlabs(Placer);
		PlaceCanyonWalls(Placer);
		PlaceEscarpment(Placer);
		UE_LOG(LogTemp, Display, TEXT("EXBUILD placed %d rock pieces"), Placer.Count);
		PlaceVegetation(World);
	}
}

bool UEXDesertBuilder::BuildSurfaceMap()
{
	// R slickrock, G deep sand, B gravel (FEXDesertTerrain::SurfaceAt), A seep wetness; one texel per 2.95 m.
	const int32 Size = SurfaceMapSize;
	const float Texel = 2.0f * FTerrain::HalfSizeM / Size;
	TArray<FColor> Pixels;
	Pixels.SetNumUninitialized(Size * Size);
	ParallelFor(Size, [&](int32 Row)
	{
		const float Y = -FTerrain::HalfSizeM + (Row + 0.5f) * Texel;
		for (int32 Column = 0; Column < Size; ++Column)
		{
			const float X = -FTerrain::HalfSizeM + (Column + 0.5f) * Texel;
			const FLinearColor Surface = FTerrain::SurfaceAt(X, Y);
			auto Byte = [](float Value) { return static_cast<uint8>(FMath::Clamp(FMath::RoundToInt(Value * 255.0f), 0, 255)); };
			Pixels[Row * Size + Column] = FColor(Byte(Surface.R), Byte(Surface.G), Byte(Surface.B), Byte(Seep(FVector2D(X, Y))));
		}
	});

	UTexture2D* Texture = LoadObject<UTexture2D>(nullptr, *FString::Printf(TEXT("%s.T_SurfaceMap"), SurfaceMapPackage), nullptr, LOAD_NoWarn | LOAD_Quiet);
	UPackage* Package = Texture ? Texture->GetOutermost() : CreatePackage(SurfaceMapPackage);
	if (!Texture)
	{
		Texture = NewObject<UTexture2D>(Package, TEXT("T_SurfaceMap"), RF_Public | RF_Standalone | RF_Transactional);
		FAssetRegistryModule::AssetCreated(Texture);
	}
	Texture->PreEditChange(nullptr);
	Texture->Source.Init(Size, Size, 1, 1, TSF_BGRA8, reinterpret_cast<const uint8*>(Pixels.GetData()));
	Texture->SRGB = false;
	Texture->CompressionSettings = TC_Default;
	Texture->AddressX = TA_Clamp;
	Texture->AddressY = TA_Clamp;
	Texture->PostEditChange();
	Package->MarkPackageDirty();
	const bool bSaved = UEditorLoadingAndSavingUtils::SavePackages({ Package }, false);
	UE_LOG(LogTemp, Display, TEXT("EXBUILD surface map %d x %d saved: %s"), Size, Size, bSaved ? TEXT("OK") : TEXT("FAILED"));
	return bSaved;
}

bool UEXDesertBuilder::BuildDesertMap()
{
	UWorld* World = UEditorLoadingAndSavingUtils::NewBlankMap(false);
	if (!World)
	{
		UE_LOG(LogTemp, Error, TEXT("EXBUILD could not create a blank map"));
		return false;
	}

	// Height field from the shared terrain description.
	const int32 Size = FTerrain::Resolution;
	const float HalfSize = FTerrain::HalfSizeM;
	TArray<uint16> Heights;
	Heights.SetNumUninitialized(Size * Size);
	float MinHeight = TNumericLimits<float>::Max();
	float MaxHeight = TNumericLimits<float>::Lowest();
	FCriticalSection RangeLock;
	ParallelFor(Size, [&](int32 Row)
	{
		const float Y = -HalfSize + Row * FTerrain::SpacingM;
		float RowMin = TNumericLimits<float>::Max();
		float RowMax = TNumericLimits<float>::Lowest();
		for (int32 Column = 0; Column < Size; ++Column)
		{
			const float Height = FTerrain::HeightAt(-HalfSize + Column * FTerrain::SpacingM, Y);
			RowMin = FMath::Min(RowMin, Height);
			RowMax = FMath::Max(RowMax, Height);
			Heights[Row * Size + Column] = static_cast<uint16>(FMath::Clamp(FMath::RoundToInt(32768.0f + Height * HeightUnitsPerM), 0, 65535));
		}
		FScopeLock Lock(&RangeLock);
		MinHeight = FMath::Min(MinHeight, RowMin);
		MaxHeight = FMath::Max(MaxHeight, RowMax);
	});
	UE_LOG(LogTemp, Display, TEXT("EXBUILD heights %d x %d, range %.1f m .. %.1f m"), Size, Size, MinHeight, MaxHeight);

	ALandscape* Landscape = World->SpawnActor<ALandscape>(FVector(-HalfSize * CmPerM, -HalfSize * CmPerM, 0.0f), FRotator::ZeroRotator);
	Landscape->SetActorRelativeScale3D(FVector(FTerrain::SpacingM * CmPerM, FTerrain::SpacingM * CmPerM, 100.0f));
	Landscape->LandscapeMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Desert/M_Desert.M_Desert"));
	UE_LOG(LogTemp, Display, TEXT("EXBUILD landscape material: %s"), *GetNameSafe(Landscape->LandscapeMaterial));
	TMap<FGuid, TArray<uint16>> HeightData;
	HeightData.Add(FGuid(), MoveTemp(Heights));
	TMap<FGuid, TArray<FLandscapeImportLayerInfo>> LayerData;
	LayerData.Add(FGuid(), TArray<FLandscapeImportLayerInfo>());
	Landscape->Import(FGuid::NewGuid(), 0, 0, Size - 1, Size - 1, 2, 63, HeightData, TEXT(""), LayerData,
		ELandscapeImportAlphamapType::Additive, TArrayView<const FLandscapeLayer>());
	if (ULandscapeInfo* Info = Landscape->GetLandscapeInfo())
	{
		Info->UpdateLayerInfoMap(Landscape);
	}
	Landscape->ForceLayersFullUpdate();
	FlushRenderingCommands();

	AddSky(World, 0.012f);

	// Race start, tagged so the game mode knows this map brings its own world.
	const FVector2D Start = FTerrain::StartPoint();
	APlayerStart* PlayerStart = World->SpawnActor<APlayerStart>(
		FVector(Start.X * CmPerM, Start.Y * CmPerM, (FTerrain::HeightAt(Start.X, Start.Y) + 3.0f) * CmPerM),
		FRotator(0.0f, FTerrain::StartYawDeg(), 0.0f));
	PlayerStart->Tags.Add(TEXT("EXWorld"));

	// Invisible walls just inside the landscape edge: the raised rim is the visible border, these make it absolute.
	const float Inner = (HalfSize - 10.0f) * CmPerM;
	AddEdgeWalls(World, FBox2D(FVector2D(-Inner, -Inner), FVector2D(Inner, Inner)), 20000.0f);

	PlaceS01(World);

	const bool bSaved = UEditorLoadingAndSavingUtils::SaveMap(World, TEXT("/Game/Maps/DesertCanyon"));
	UE_LOG(LogTemp, Display, TEXT("EXBUILD saved /Game/Maps/DesertCanyon: %s"), bSaved ? TEXT("OK") : TEXT("FAILED"));
	return bSaved;
}

namespace
{
	TSharedPtr<FJsonObject> LoadJsonFile(const FString& Path)
	{
		FString Text;
		TSharedPtr<FJsonObject> Root;
		if (!FFileHelper::LoadFileToString(Text, *Path) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid())
		{
			UE_LOG(LogTemp, Error, TEXT("EXWORLD could not read %s"), *Path);
			return nullptr;
		}
		return Root;
	}

	/** World metres (from the world centre, y north) to Unreal centimetres: Y is mirrored, as the FBX import mirrors
	 *  every mesh the world was built with. */
	FVector WorldToUnreal(double X, double Y, double Z)
	{
		return FVector(X * CmPerM, -Y * CmPerM, Z * CmPerM);
	}

	UHierarchicalInstancedStaticMeshComponent* AddInstances(UWorld* World, UStaticMesh* Mesh, const TArray<FTransform>& Transforms, bool bCollide,
		float CullM, const FName Folder)
	{
		AActor* Holder = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity);
		UHierarchicalInstancedStaticMeshComponent* Component = NewObject<UHierarchicalInstancedStaticMeshComponent>(Holder, TEXT("Instances"));
		Component->SetMobility(EComponentMobility::Static);
		Component->SetStaticMesh(Mesh);
		Component->SetCollisionProfileName(bCollide ? UCollisionProfile::BlockAll_ProfileName : UCollisionProfile::NoCollision_ProfileName);
		if (CullM > 0.0f)
		{
			Component->SetCullDistances(FMath::RoundToInt(CullM * 0.75f * CmPerM), FMath::RoundToInt(CullM * CmPerM));
		}
		Holder->SetRootComponent(Component);
		Holder->AddInstanceComponent(Component);
		Component->RegisterComponent();
		Component->AddInstances(Transforms, false, true);
		Holder->SetActorLabel(FString::Printf(TEXT("Props_%s"), *Mesh->GetName()));
		Holder->SetFolderPath(Folder);
		return Component;
	}

	/** How far away each kind of plant stops being drawn (m); 0 keeps it at any distance. */
	float PlantCullM(const FString& Mesh)
	{
		if (Mesh.Contains(TEXT("Grass")))
		{
			return 250.0f;
		}
		if (Mesh.Contains(TEXT("Sagebrush")) || Mesh.Contains(TEXT("DeadBrush")) || Mesh.Contains(TEXT("PricklyPear")) || Mesh.Contains(TEXT("Yucca")))
		{
			return 500.0f;
		}
		return Mesh.Contains(TEXT("Willow")) ? 900.0f : 0.0f;
	}
}

bool UEXDesertBuilder::BuildWorldMap(const FString& WorldFolder, const FString& MapName)
{
	const TSharedPtr<FJsonObject> Meta = LoadJsonFile(WorldFolder / TEXT("unreal/world_unreal.json"));
	const TSharedPtr<FJsonObject> Field = LoadJsonFile(WorldFolder / TEXT("canyon_field.json"));
	const TSharedPtr<FJsonObject> Props = LoadJsonFile(WorldFolder / TEXT("props.json"));
	if (!Meta || !Field || !Props)
	{
		return false;
	}
	const TArray<TSharedPtr<FJsonValue>>& SizeField = Meta->GetArrayField(TEXT("size"));
	const TArray<TSharedPtr<FJsonValue>>& OriginField = Meta->GetArrayField(TEXT("origin_cm"));
	const int32 SizeX = static_cast<int32>(SizeField[0]->AsNumber());
	const int32 SizeY = static_cast<int32>(SizeField[1]->AsNumber());
	const double SpacingCm = Meta->GetNumberField(TEXT("spacing_m")) * CmPerM;
	TArray<uint8> Raw;
	if (!FFileHelper::LoadFileToArray(Raw, *(WorldFolder / TEXT("unreal/world.r16"))) || Raw.Num() != SizeX * SizeY * 2)
	{
		UE_LOG(LogTemp, Error, TEXT("EXWORLD world.r16 missing or not %d x %d"), SizeX, SizeY);
		return false;
	}
	TArray<uint16> Heights;
	Heights.SetNumUninitialized(SizeX * SizeY);
	FMemory::Memcpy(Heights.GetData(), Raw.GetData(), Raw.Num());

	UWorld* World = UEditorLoadingAndSavingUtils::NewBlankMap(false);
	if (!World)
	{
		return false;
	}
	// Landscape: one vertex per height sample, 2 x 2 sections of 63 quads per component.
	ALandscape* Landscape = World->SpawnActor<ALandscape>(FVector(OriginField[0]->AsNumber(), OriginField[1]->AsNumber(),
		Meta->GetNumberField(TEXT("actor_z_cm"))), FRotator::ZeroRotator);
	Landscape->SetActorRelativeScale3D(FVector(SpacingCm, SpacingCm, Meta->GetNumberField(TEXT("z_scale"))));
	Landscape->LandscapeMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/World/M_World.M_World"));
	TMap<FGuid, TArray<uint16>> HeightData;
	HeightData.Add(FGuid(), MoveTemp(Heights));
	TMap<FGuid, TArray<FLandscapeImportLayerInfo>> LayerData;
	LayerData.Add(FGuid(), TArray<FLandscapeImportLayerInfo>());
	Landscape->Import(FGuid::NewGuid(), 0, 0, SizeX - 1, SizeY - 1, 2, 63, HeightData, TEXT(""), LayerData,
		ELandscapeImportAlphamapType::Additive, TArrayView<const FLandscapeLayer>());
	if (ULandscapeInfo* Info = Landscape->GetLandscapeInfo())
	{
		Info->UpdateLayerInfoMap(Landscape);
	}
	Landscape->ForceLayersFullUpdate();
	FlushRenderingCommands();
	UE_LOG(LogTemp, Display, TEXT("EXWORLD landscape %d x %d at %.0f cm, material %s"), SizeX, SizeY, SpacingCm, *GetNameSafe(Landscape->LandscapeMaterial));

	AddSky(World, 0.0025f);
	const TArray<TSharedPtr<FJsonValue>>& WorldSize = Meta->GetArrayField(TEXT("world_size_m"));
	const double HalfX = WorldSize[0]->AsNumber() * 0.5 * CmPerM;
	const double HalfY = WorldSize[1]->AsNumber() * 0.5 * CmPerM;
	AddEdgeWalls(World, FBox2D(FVector2D(-HalfX + 1000.0, -HalfY + 1000.0), FVector2D(HalfX - 1000.0, HalfY - 1000.0)), 20000.0f);

	// Props: one instanced component per mesh. Rotation as the world placed them (Blender XYZ: tilt x, tilt y, yaw),
	// mirrored with Y: roll keeps tilt x, pitch and yaw change sign.
	TMap<FString, TArray<FTransform>> ByMesh;
	for (const TSharedPtr<FJsonValue>& Value : Props->GetArrayField(TEXT("props")))
	{
		const TSharedPtr<FJsonObject> Prop = Value->AsObject();
		// Rotation: "rot" (Euler XYZ, expedition) or "tilt" (x, y) + "yaw" (world); scale: per axis or uniform.
		double RotX = 0.0;
		double RotY = 0.0;
		double RotZ = Prop->GetNumberField(TEXT("yaw"));
		const TArray<TSharedPtr<FJsonValue>>* Rot = nullptr;
		const TArray<TSharedPtr<FJsonValue>>* Tilt = nullptr;
		if (Prop->TryGetArrayField(TEXT("rot"), Rot) && Rot->Num() == 3)
		{
			RotX = (*Rot)[0]->AsNumber();
			RotY = (*Rot)[1]->AsNumber();
			RotZ = (*Rot)[2]->AsNumber();
		}
		else if (Prop->TryGetArrayField(TEXT("tilt"), Tilt) && Tilt->Num() == 2)
		{
			RotX = (*Tilt)[0]->AsNumber();
			RotY = (*Tilt)[1]->AsNumber();
		}
		FVector Scale(1.0);
		const TArray<TSharedPtr<FJsonValue>>* Scales = nullptr;
		if (Prop->TryGetArrayField(TEXT("scale"), Scales) && Scales->Num() == 3)
		{
			Scale = FVector((*Scales)[0]->AsNumber(), (*Scales)[1]->AsNumber(), (*Scales)[2]->AsNumber());
		}
		else
		{
			Scale = FVector(Prop->GetNumberField(TEXT("scale")));
		}
		ByMesh.FindOrAdd(Prop->GetStringField(TEXT("mesh"))).Add(FTransform(FRotator(-RotY, -RotZ, RotX),
			WorldToUnreal(Prop->GetNumberField(TEXT("x")), Prop->GetNumberField(TEXT("y")), Prop->GetNumberField(TEXT("z"))), Scale));
	}
	int32 Placed = 0;
	for (const TPair<FString, TArray<FTransform>>& Group : ByMesh)
	{
		UStaticMesh* Mesh = nullptr;
		FString Folder;
		for (const TCHAR* Candidate : { TEXT("/Game/World/Kit"), TEXT("/Game/Desert/Rocks"), TEXT("/Game/Desert/S01"), TEXT("/Game/Desert/Plants") })
		{
			Mesh = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), Candidate, *Group.Key, *Group.Key), nullptr, LOAD_NoWarn | LOAD_Quiet);
			if (Mesh)
			{
				Folder = Candidate;
				break;
			}
		}
		if (!Mesh)
		{
			UE_LOG(LogTemp, Warning, TEXT("EXWORLD missing mesh %s (%d props)"), *Group.Key, Group.Value.Num());
			continue;
		}
		const bool bKit = !Folder.EndsWith(TEXT("Plants"));  // rocks of any kind
		const bool bWood = Group.Key.Contains(TEXT("Dead"));
		// The arches over the line (Arches Run, the finish) are landmarks to fly through, never walls to die on
		// (player, 2026-10-26: "tem obstáculos que chocamos").
		const bool bArch = Group.Key.Contains(TEXT("Arch"));
		AddInstances(World, Mesh, Group.Value, bKit && !bWood && !bArch, bKit ? 0.0f : PlantCullM(Group.Key), bKit ? TEXT("World/Rocks") : TEXT("World/Plants"));
		Placed += Group.Value.Num();
	}
	UE_LOG(LogTemp, Display, TEXT("EXWORLD props placed %d in %d meshes"), Placed, ByMesh.Num());

	// Tunnel roofs: the core's were exported in the core map's frame, the grand circuit's in the world's.
	const TArray<TSharedPtr<FJsonValue>>& CoreOffset = Meta->GetArrayField(TEXT("core_tunnel_offset_m"));
	const TSharedPtr<FJsonObject> Circuit = Field->GetObjectField(TEXT("grand_circuit"));
	int32 Roofs = 0;
	auto PlaceRoofs = [&](const TArray<TSharedPtr<FJsonValue>>& Tunnels, const FVector& Offset)
	{
		for (const TSharedPtr<FJsonValue>& Tunnel : Tunnels)
		{
			const FString Name = Tunnel->AsObject()->GetStringField(TEXT("name"));
			UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("/Game/World/Tunnels/%s.%s"), *Name, *Name));
			if (!Mesh)
			{
				UE_LOG(LogTemp, Warning, TEXT("EXWORLD missing tunnel roof %s"), *Name);
				continue;
			}
			AStaticMeshActor* Roof = World->SpawnActor<AStaticMeshActor>(Offset, FRotator::ZeroRotator);
			Roof->GetStaticMeshComponent()->SetStaticMesh(Mesh);
			Roof->SetActorLabel(Name);
			Roof->SetFolderPath(TEXT("World/Tunnels"));
			++Roofs;
		}
	};
	PlaceRoofs(Field->GetArrayField(TEXT("tunnels")), WorldToUnreal(CoreOffset[0]->AsNumber(), CoreOffset[1]->AsNumber(), 0.0));
	PlaceRoofs(Circuit->GetArrayField(TEXT("tunnels")), FVector::ZeroVector);
	UE_LOG(LogTemp, Display, TEXT("EXWORLD tunnel roofs %d"), Roofs);

	// The grand circuit as a spline (one point every 20 m) the autopilot and later the AI follow, and the start.
	const TArray<TSharedPtr<FJsonValue>>& LapPoints = Circuit->GetObjectField(TEXT("lap"))->GetArrayField(TEXT("points"));
	AActor* Route = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity);
	USplineComponent* Spline = NewObject<USplineComponent>(Route, TEXT("Route"));
	Route->SetRootComponent(Spline);
	Route->AddInstanceComponent(Spline);
	Spline->RegisterComponent();
	Spline->ClearSplinePoints(false);
	auto LapPoint = [&LapPoints](int32 Index)
	{
		const TArray<TSharedPtr<FJsonValue>>& P = LapPoints[Index]->AsArray();
		return WorldToUnreal(P[0]->AsNumber(), P[1]->AsNumber(), P[2]->AsNumber());
	};
	for (int32 Index = 0; Index < LapPoints.Num(); Index += 5)
	{
		Spline->AddSplinePoint(LapPoint(Index) + FVector(0.0f, 0.0f, 50.0f), ESplineCoordinateSpace::World, false);
	}
	bool bClosed = true;  // the world's grand circuit is a lap; the expedition runs from A to B
	Circuit->TryGetBoolField(TEXT("closed"), bClosed);
	Spline->SetClosedLoop(bClosed, false);
	Spline->UpdateSpline();
	Route->Tags.Add(TEXT("EXRoute"));
	Route->SetActorLabel(TEXT("Route_GrandCircuit"));
	// Guide beacons: glowing posts 3 m outside the floor's edge, on the outside of every bend tighter than 400 m
	// (one every 60 m) and every 250 m on the straights, standing on the ground; they never collide.
	const TArray<TSharedPtr<FJsonValue>>& LapWidths = Circuit->GetObjectField(TEXT("lap"))->GetArrayField(TEXT("width_m"));
	TArray<FTransform> Beacons;
	float SinceLast = 1000.0f;
	float SinceCaveLight = 1000.0f;
	float SinceCaveLamp = 1000.0f;
	int32 CaveLamps = 0;
	double StraightSide = 1.0;
	for (int32 Index = 10; Index + 10 < LapPoints.Num(); ++Index)
	{
		SinceLast += 4.0f;
		SinceCaveLight += 4.0f;
		SinceCaveLamp += 4.0f;
		const FVector A = LapPoint(Index - 10);
		const FVector B = LapPoint(Index);
		const FVector C = LapPoint(Index + 10);
		const double Cross = FVector2D(B - A) ^ FVector2D(C - B);
		const double RadiusM = FMath::Abs(Cross) > 1.0
			? FVector2D::Distance(FVector2D(A), FVector2D(B)) * FVector2D::Distance(FVector2D(B), FVector2D(C)) * FVector2D::Distance(FVector2D(C), FVector2D(A)) / (2.0 * FMath::Abs(Cross)) / CmPerM
			: 1.0e6;
		const bool bBend = RadiusM < 400.0;
		if (!((bBend && SinceLast >= 60.0f) || SinceLast >= 250.0f))
		{
			continue;
		}
		FHitResult Hit;
		if (World->LineTraceSingleByChannel(Hit, B + FVector(0.0, 0.0, 200.0), B + FVector(0.0, 0.0, 6000.0), ECC_WorldStatic))
		{
			// Under a cave roof: short glowing posts on both sides every 40 m, 4 m inside the foot of the vault, and a
			// warm lamp under the vault every 160 m (no shadows), so the way reads in the dark.
			const FVector2D CaveDir = FVector2D(C - A).GetSafeNormal();
			const FVector2D CaveLeft(-CaveDir.Y, CaveDir.X);
			if (SinceCaveLight >= 40.0f)
			{
				SinceCaveLight = 0.0f;
				const double InsideCm = FMath::Max(2.0, 0.5 * LapWidths[Index]->AsNumber() - 4.0) * CmPerM;
				for (const double Side : {1.0, -1.0})
				{
					const FVector2D Post = FVector2D(B) + CaveLeft * Side * InsideCm;
					double GroundZ = B.Z;
					if (World->LineTraceSingleByChannel(Hit, FVector(Post, B.Z + 500.0), FVector(Post, B.Z - 8000.0), ECC_WorldStatic))
					{
						GroundZ = Hit.ImpactPoint.Z;
					}
					Beacons.Add(FTransform(FRotator::ZeroRotator, FVector(Post, GroundZ + 60.0), FVector(0.3, 0.3, 1.4)));
				}
			}
			if (SinceCaveLamp >= 160.0f)
			{
				SinceCaveLamp = 0.0f;
				APointLight* Lamp = World->SpawnActor<APointLight>(B + FVector(0.0, 0.0, 1200.0), FRotator::ZeroRotator);
				Lamp->SetMobility(EComponentMobility::Movable);
				Lamp->PointLightComponent->SetIntensityUnits(ELightUnits::Candelas);
				Lamp->PointLightComponent->SetIntensity(2500.0f);  // the sun is 10 lux: ~15 lux on the floor below
				Lamp->PointLightComponent->SetAttenuationRadius(9000.0f);
				Lamp->PointLightComponent->SetLightColor(FLinearColor(1.0f, 0.62f, 0.32f));
				Lamp->PointLightComponent->SetCastShadows(false);
				Lamp->SetFolderPath(TEXT("World/CaveLamps"));
				++CaveLamps;
			}
			continue;
		}
		SinceLast = 0.0f;
		const FVector2D Dir = FVector2D(C - A).GetSafeNormal();
		const FVector2D Left(-Dir.Y, Dir.X);
		const double Side = bBend ? (Cross > 0.0 ? -1.0 : 1.0) : (StraightSide = -StraightSide);
		const double OffsetCm = (0.5 * LapWidths[Index]->AsNumber() + 3.0) * CmPerM;
		const FVector2D Post = FVector2D(B) + Left * Side * OffsetCm;
		double GroundZ = B.Z;
		if (World->LineTraceSingleByChannel(Hit, FVector(Post, B.Z + 8000.0), FVector(Post, B.Z - 8000.0), ECC_WorldStatic))
		{
			GroundZ = Hit.ImpactPoint.Z;
		}
		Beacons.Add(FTransform(FRotator::ZeroRotator, FVector(Post, GroundZ + 160.0), FVector(0.35, 0.35, 3.5)));
	}
	if (UStaticMesh* Post = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder")))
	{
		if (UHierarchicalInstancedStaticMeshComponent* Posts = AddInstances(World, Post, Beacons, false, 0.0f, TEXT("World/Beacons")))
		{
			Posts->SetMaterial(0, LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/World/M_Beacon.M_Beacon")));
		}
	}
	UE_LOG(LogTemp, Display, TEXT("EXWORLD beacons %d, cave lamps %d"), Beacons.Num(), CaveLamps);

	const FVector Start = LapPoint(0);
	const FVector Ahead = LapPoint(FMath::Min(10, LapPoints.Num() - 1));
	APlayerStart* PlayerStart = World->SpawnActor<APlayerStart>(Start + FVector(0.0f, 0.0f, 300.0f), FRotator(0.0f, (Ahead - Start).Rotation().Yaw, 0.0f));
	PlayerStart->Tags.Add(TEXT("EXWorld"));
	UE_LOG(LogTemp, Display, TEXT("EXWORLD route %d points (%d m lap)"), Spline->GetNumberOfSplinePoints(), static_cast<int32>(Spline->GetSplineLength() / CmPerM));

	const FString MapPath = TEXT("/Game/Maps/") + MapName;
	const bool bSaved = UEditorLoadingAndSavingUtils::SaveMap(World, MapPath);
	UE_LOG(LogTemp, Display, TEXT("EXWORLD saved %s: %s"), *MapPath, bSaved ? TEXT("OK") : TEXT("FAILED"));
	return bSaved;
}
