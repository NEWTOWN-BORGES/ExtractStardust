#include "EXDesertBuilder.h"

#include "Async/ParallelFor.h"
#include "FileHelpers.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/Engine.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/PlayerStart.h"
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "Materials/MaterialInterface.h"
#include "Misc/PackageName.h"
#include "RenderingThread.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "World/EXDesertTerrain.h"

namespace
{
	constexpr float CmPerM = 100.0f;
	/** Landscape Z scale 100 maps one height unit to 1/128 m, giving a range of +/-256 m around zero. */
	constexpr float HeightUnitsPerM = 128.0f;

	/** Sculpted rock meshes (Scripts/sculpt_rocks.py): half footprint and wall height above the ground (m). */
	struct FRockMesh
	{
		const TCHAR* Name;
		float HalfX;
		float HalfY;
		float Height;
	};
	const FRockMesh RockMeshes[] = {
		{ TEXT("SM_Mesa_A"), 73.0f, 58.0f, 55.0f }, { TEXT("SM_Mesa_B"), 88.0f, 58.0f, 40.0f }, { TEXT("SM_Butte_A"), 34.0f, 29.0f, 65.0f },
		{ TEXT("SM_Spire_A"), 14.0f, 13.0f, 42.0f }, { TEXT("SM_Spire_B"), 12.0f, 12.0f, 30.0f },
		{ TEXT("SM_Cliff_A"), 57.0f, 16.0f, 60.0f }, { TEXT("SM_Cliff_B"), 54.0f, 21.0f, 45.0f }, { TEXT("SM_Cliff_C"), 69.0f, 12.0f, 75.0f },
		{ TEXT("SM_Boulder_A"), 3.0f, 3.0f, 4.0f }, { TEXT("SM_Boulder_B"), 8.0f, 6.0f, 6.0f }, { TEXT("SM_Boulder_C"), 2.5f, 2.0f, 2.4f } };
	enum ERockKind { MesaA, MesaB, Butte, SpireA, SpireB, CliffA, CliffB, CliffC, BoulderA, BoulderB, BoulderC, RockKindCount };
	const TCHAR* RockMaterials[] = { TEXT("MI_Rock_Red"), TEXT("MI_Rock_Dark"), TEXT("MI_Rock_Pale"), TEXT("MI_Rock_Banded") };

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

	struct FRockPlacer
	{
		UWorld* World = nullptr;
		UStaticMesh* Meshes[RockKindCount] = {};
		UMaterialInterface* Materials[4] = {};
		int32 Count = 0;

		bool Load()
		{
			for (int32 Kind = 0; Kind < RockKindCount; ++Kind)
			{
				Meshes[Kind] = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("/Game/Desert/Rocks/%s.%s"), RockMeshes[Kind].Name, RockMeshes[Kind].Name));
				if (!Meshes[Kind])
				{
					UE_LOG(LogTemp, Error, TEXT("EXBUILD missing rock mesh %s"), RockMeshes[Kind].Name);
					return false;
				}
			}
			for (int32 Index = 0; Index < 4; ++Index)
			{
				Materials[Index] = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(TEXT("/Game/Desert/%s.%s"), RockMaterials[Index], RockMaterials[Index]));
			}
			return true;
		}

		void Spawn(int32 Kind, const FVector& LocationM, float YawDeg, const FVector& Scale, uint32 Seed)
		{
			AStaticMeshActor* Rock = World->SpawnActor<AStaticMeshActor>(LocationM * CmPerM, FRotator(0.0f, YawDeg, 0.0f));
			UStaticMeshComponent* Component = Rock->GetStaticMeshComponent();
			Component->SetStaticMesh(Meshes[Kind]);
			if (UMaterialInterface* Material = Materials[Hash(Seed) % 4])
			{
				Component->SetMaterial(0, Material);
			}
			Rock->SetActorScale3D(Scale);
			Rock->SetFolderPath(TEXT("Rocks"));
			++Count;
		}
	};

	/** Squircle radius of the plateau outline along a direction (no edge noise). */
	float PlateauRadius(const FVector2D& Direction)
	{
		const float A = FMath::Pow(FMath::Abs(Direction.X) / 1050.0f, 4.0f) + FMath::Pow(FMath::Abs(Direction.Y) / 1350.0f, 4.0f);
		return FMath::Pow(1.0f / FMath::Max(A, 1.0e-12f), 0.25f);
	}

	void PlaceRocks(UWorld* World)
	{
		FRockPlacer Placer;
		Placer.World = World;
		if (!Placer.Load())
		{
			return;
		}

		// Mesas and buttes stand on their talus mounds; the base sits at the mound's rim so nothing floats.
		TArray<FVector4> Mesas;
		FEXDesertTerrain::MesaSites(Mesas);
		for (int32 Index = 0; Index < Mesas.Num(); ++Index)
		{
			const FVector4& Site = Mesas[Index];
			const float Radius = Site.Z;
			const int32 Kind = Radius >= 150.0f ? (Index % 2 ? MesaA : MesaB) : (Radius >= 90.0f ? MesaA : Butte);
			const FRockMesh& Mesh = RockMeshes[Kind];
			const float Scale = Radius / ((Mesh.HalfX + Mesh.HalfY) * 0.5f);
			float Rim = TNumericLimits<float>::Max();
			for (int32 Step = 0; Step < 8; ++Step)
			{
				const float Angle = Step * PI / 4.0f;
				Rim = FMath::Min(Rim, FEXDesertTerrain::HeightAt(Site.X + Radius * FMath::Cos(Angle), Site.Y + Radius * FMath::Sin(Angle)));
			}
			Placer.Spawn(Kind, FVector(Site.X, Site.Y, Rim - 2.0f), Hash01(Index * 7 + 1) * 360.0f, FVector(Scale, Scale, Site.W / Mesh.Height), Index);

			// Scree: boulders fallen around the foot.
			for (int32 Stone = 0; Stone < 18; ++Stone)
			{
				const uint32 Seed = 1000 + Index * 64 + Stone;
				const float Angle = Hash01(Seed) * 2.0f * PI;
				const float Distance = Radius * (1.0f + 0.3f * Hash01(Seed + 1));
				const float X = Site.X + Distance * FMath::Cos(Angle);
				const float Y = Site.Y + Distance * FMath::Sin(Angle);
				const float Size = 0.6f + 1.2f * Hash01(Seed + 2);
				Placer.Spawn(BoulderA + Hash(Seed + 3) % 3, FVector(X, Y, FEXDesertTerrain::HeightAt(X, Y) - 0.5f), Hash01(Seed + 4) * 360.0f, FVector(Size), Seed);
			}
		}

		// Canyon walls: a cliff every 70 m on each side wherever the canyon is cut deep enough.
		const TArray<FEXDesertTerrain::FCanyonPoint>& Points = FEXDesertTerrain::CanyonPoints();
		float Along = 0.0f;
		float Next = 0.0f;
		for (int32 Index = 1; Index < Points.Num(); ++Index)
		{
			Along += FVector2D::Distance(Points[Index - 1].Point, Points[Index].Point);
			if (Along < Next)
			{
				continue;
			}
			Next = Along + 70.0f;
			const FEXDesertTerrain::FCanyonPoint& Point = Points[Index];
			const FVector2D Tangent = (Point.Point - Points[Index - 1].Point).GetSafeNormal();
			const FVector2D Normal(-Tangent.Y, Tangent.X);
			for (int32 SideIndex = 0; SideIndex < 2; ++SideIndex)
			{
				const float Side = SideIndex == 0 ? -1.0f : 1.0f;
				const uint32 Seed = 5000 + Index * 2 + SideIndex;
				const FVector2D Outside = Point.Point + Normal * Side * (Point.HalfWidth + 70.0f);
				const float WallHeight = FEXDesertTerrain::HeightAt(Outside.X, Outside.Y) - Point.Floor;
				if (WallHeight < 15.0f)
				{
					continue;
				}
				const int32 Kind = CliffA + Hash(Seed) % 3;
				const FRockMesh& Mesh = RockMeshes[Kind];
				const float Scale = 95.0f / (2.0f * Mesh.HalfX) * (0.9f + 0.25f * Hash01(Seed + 1));
				const FVector2D Center = Point.Point + Normal * Side * (Point.HalfWidth + 3.0f + Mesh.HalfY * Scale);
				const float Yaw = FMath::RadiansToDegrees(FMath::Atan2(Tangent.Y, Tangent.X)) + (Hash01(Seed + 2) - 0.5f) * 12.0f;
				Placer.Spawn(Kind, FVector(Center.X, Center.Y, Point.Floor - 2.0f), Yaw, FVector(Scale, Scale, (WallHeight + 4.0f) / Mesh.Height), Seed);
			}
		}

		// Plateau rim: cliffs every 5 degrees where its edge drops to the plain, leaving the canyon mouths open.
		const FVector2D Center = FEXDesertTerrain::PlateauCenter();
		for (int32 Step = 0; Step < 72; ++Step)
		{
			const float Angle = FMath::DegreesToRadians(Step * 5.0f);
			const FVector2D Direction(FMath::Cos(Angle), FMath::Sin(Angle));
			const float Nominal = PlateauRadius(Direction);
			float Edge = -1.0f;
			for (float Radius = Nominal * 0.85f; Radius < Nominal * 1.2f; Radius += 4.0f)
			{
				const FVector2D Probe = Center + Direction * Radius;
				if (FEXDesertTerrain::HeightAt(Probe.X, Probe.Y) < 30.0f)
				{
					Edge = Radius;
					break;
				}
			}
			const FVector2D EdgePoint = Center + Direction * Edge;
			if (Edge < 0.0f || FEXDesertTerrain::DistanceToCanyon(EdgePoint.X, EdgePoint.Y) < 90.0f
				|| FMath::Max(FMath::Abs(EdgePoint.X), FMath::Abs(EdgePoint.Y)) > 1700.0f)
			{
				continue;
			}
			const FVector2D Inner = Center + Direction * (Edge - 60.0f);
			const FVector2D Outer = Center + Direction * (Edge + 40.0f);
			const float Top = FEXDesertTerrain::HeightAt(Inner.X, Inner.Y);
			const float Base = FEXDesertTerrain::HeightAt(Outer.X, Outer.Y);
			if (Top - Base < 20.0f)
			{
				continue;
			}
			const uint32 Seed = 9000 + Step;
			const int32 Kind = CliffA + Hash(Seed) % 3;
			const FRockMesh& Mesh = RockMeshes[Kind];
			const float Scale = 100.0f / (2.0f * Mesh.HalfX) * (0.9f + 0.2f * Hash01(Seed + 1));
			const FVector2D Place = Center + Direction * (Edge - Mesh.HalfY * Scale * 0.6f);
			Placer.Spawn(Kind, FVector(Place.X, Place.Y, Base - 3.0f), Step * 5.0f + 90.0f + (Hash01(Seed + 2) - 0.5f) * 10.0f,
				FVector(Scale, Scale, (Top - Base + 5.0f) / Mesh.Height), Seed);
		}

		// Hoodoos on the open plain, and boulders scattered off the racing line.
		const FVector2D Start = FEXDesertTerrain::StartPoint();
		int32 Hoodoos = 0;
		for (int32 Try = 0; Try < 200 && Hoodoos < 14; ++Try)
		{
			const uint32 Seed = 20000 + Try;
			const float X = -1700.0f + 1350.0f * Hash01(Seed);
			const float Y = -1700.0f + 3400.0f * Hash01(Seed + 1);
			bool bClear = FVector2D::Distance(FVector2D(X, Y), Start) > 300.0f && FEXDesertTerrain::DistanceToCanyon(X, Y) > 100.0f;
			for (const FVector4& Site : Mesas)
			{
				bClear &= FVector2D::Distance(FVector2D(X, Y), FVector2D(Site.X, Site.Y)) > Site.Z * 1.4f + 30.0f;
			}
			if (!bClear)
			{
				continue;
			}
			const float Size = 0.7f + 0.8f * Hash01(Seed + 2);
			Placer.Spawn(Hash(Seed + 3) % 2 ? SpireA : SpireB, FVector(X, Y, FEXDesertTerrain::HeightAt(X, Y) - 1.5f), Hash01(Seed + 4) * 360.0f, FVector(Size), Seed);
			++Hoodoos;
		}
		for (int32 Try = 0; Try < 420; ++Try)
		{
			const uint32 Seed = 40000 + Try;
			const float X = -1700.0f + 3400.0f * Hash01(Seed);
			const float Y = -1700.0f + 3400.0f * Hash01(Seed + 1);
			float HalfWidth = 0.0f;
			const float ToCanyon = FEXDesertTerrain::DistanceToCanyon(X, Y, &HalfWidth);
			if (FVector2D::Distance(FVector2D(X, Y), Start) < 200.0f || ToCanyon < HalfWidth * 0.6f)
			{
				continue;
			}
			const float Size = 0.5f + 1.5f * Hash01(Seed + 2);
			Placer.Spawn(BoulderA + Hash(Seed + 3) % 3, FVector(X, Y, FEXDesertTerrain::HeightAt(X, Y) - 0.5f), Hash01(Seed + 4) * 360.0f, FVector(Size), Seed);
		}
		UE_LOG(LogTemp, Display, TEXT("EXBUILD placed %d sculpted rocks"), Placer.Count);
	}
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
	const int32 Size = FEXDesertTerrain::Resolution;
	const float HalfSize = FEXDesertTerrain::HalfSizeM;
	TArray<uint16> Heights;
	Heights.SetNumUninitialized(Size * Size);
	float MinHeight = TNumericLimits<float>::Max();
	float MaxHeight = TNumericLimits<float>::Lowest();
	FCriticalSection RangeLock;
	ParallelFor(Size, [&](int32 Row)
	{
		const float Y = -HalfSize + Row * FEXDesertTerrain::SpacingM;
		float RowMin = TNumericLimits<float>::Max();
		float RowMax = TNumericLimits<float>::Lowest();
		for (int32 Column = 0; Column < Size; ++Column)
		{
			const float Height = FEXDesertTerrain::HeightAt(-HalfSize + Column * FEXDesertTerrain::SpacingM, Y);
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
	Landscape->SetActorRelativeScale3D(FVector(FEXDesertTerrain::SpacingM * CmPerM, FEXDesertTerrain::SpacingM * CmPerM, 100.0f));
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

	// Sun, sky and dusty air. Movable lighting only: the project has no baked lighting.
	ADirectionalLight* Sun = World->SpawnActor<ADirectionalLight>(FVector(0.0f, 0.0f, 50000.0f), FRotator(-38.0f, -35.0f, 0.0f));
	if (UDirectionalLightComponent* SunLight = Cast<UDirectionalLightComponent>(Sun->GetLightComponent()))
	{
		SunLight->SetMobility(EComponentMobility::Movable);
		SunLight->SetIntensity(10.0f);
		SunLight->SetLightColor(FLinearColor(1.0f, 0.93f, 0.84f));
		SunLight->SetAtmosphereSunLight(true);
		SunLight->SetDynamicShadowDistanceMovableLight(25000.0f);
	}
	World->SpawnActor<ASkyAtmosphere>(FVector::ZeroVector, FRotator::ZeroRotator);
	ASkyLight* Sky = World->SpawnActor<ASkyLight>(FVector(0.0f, 0.0f, 20000.0f), FRotator::ZeroRotator);
	if (USkyLightComponent* SkyLight = Sky->GetLightComponent())
	{
		SkyLight->SetMobility(EComponentMobility::Movable);
		SkyLight->SetRealTimeCapture(true);
		SkyLight->SetIntensity(1.0f);
	}
	AExponentialHeightFog* Fog = World->SpawnActor<AExponentialHeightFog>(FVector(0.0f, 0.0f, 0.0f), FRotator::ZeroRotator);
	if (UExponentialHeightFogComponent* FogComponent = Fog->GetComponent())
	{
		FogComponent->SetFogDensity(0.012f);
		FogComponent->SetFogHeightFalloff(0.12f);
		FogComponent->SetFogInscatteringColor(FLinearColor(0.62f, 0.47f, 0.36f));
		FogComponent->SetDirectionalInscatteringColor(FLinearColor(1.0f, 0.72f, 0.48f));
		FogComponent->SetStartDistance(4000.0f);
	}
	APostProcessVolume* Post = World->SpawnActor<APostProcessVolume>(FVector::ZeroVector, FRotator::ZeroRotator);
	Post->bUnbound = true;
	Post->Settings.bOverride_BloomIntensity = true;
	Post->Settings.BloomIntensity = 0.45f;
	Post->Settings.bOverride_VignetteIntensity = true;
	Post->Settings.VignetteIntensity = 0.3f;
	Post->Settings.bOverride_WhiteTemp = true;
	Post->Settings.WhiteTemp = 6100.0f;

	// Race start, tagged so the game mode knows this map brings its own world.
	const FVector2D Start = FEXDesertTerrain::StartPoint();
	APlayerStart* PlayerStart = World->SpawnActor<APlayerStart>(
		FVector(Start.X * CmPerM, Start.Y * CmPerM, (FEXDesertTerrain::HeightAt(Start.X, Start.Y) + 3.0f) * CmPerM),
		FRotator(0.0f, FEXDesertTerrain::StartYawDeg(), 0.0f));
	PlayerStart->Tags.Add(TEXT("EXWorld"));

	// Invisible walls just inside the landscape edge: the raised rim is the visible border, these make it absolute.
	if (UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")))
	{
		const float Inner = (HalfSize - 10.0f) * CmPerM;
		const float Length = (HalfSize * 2.0f + 40.0f) * CmPerM;
		const FVector Centers[] = { FVector(Inner, 0, 0), FVector(-Inner, 0, 0), FVector(0, Inner, 0), FVector(0, -Inner, 0) };
		for (int32 Index = 0; Index < 4; ++Index)
		{
			const bool bAlongY = Index < 2;
			AStaticMeshActor* Wall = World->SpawnActor<AStaticMeshActor>(Centers[Index] + FVector(0.0f, 0.0f, 20000.0f), FRotator::ZeroRotator);
			Wall->GetStaticMeshComponent()->SetStaticMesh(Cube);
			Wall->SetActorScale3D(bAlongY ? FVector(10.0f, Length / 100.0f, 600.0f) : FVector(Length / 100.0f, 10.0f, 600.0f));
			Wall->SetActorHiddenInGame(true);
		}
	}

	PlaceRocks(World);

	const bool bSaved = UEditorLoadingAndSavingUtils::SaveMap(World, TEXT("/Game/Maps/DesertCanyon"));
	UE_LOG(LogTemp, Display, TEXT("EXBUILD saved /Game/Maps/DesertCanyon: %s"), bSaved ? TEXT("OK") : TEXT("FAILED"));
	return bSaved;
}
