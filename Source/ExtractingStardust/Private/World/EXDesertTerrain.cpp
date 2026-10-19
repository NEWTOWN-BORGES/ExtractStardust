#include "World/EXDesertTerrain.h"

namespace
{
	float Noise(float X, float Y)
	{
		return FMath::PerlinNoise2D(FVector2D(X, Y));
	}

	float Fbm(float X, float Y, int32 Octaves)
	{
		float Sum = 0.0f;
		float Amplitude = 0.5f;
		float Frequency = 1.0f;
		for (int32 Octave = 0; Octave < Octaves; ++Octave)
		{
			Sum += Amplitude * Noise(X * Frequency + Octave * 17.13f, Y * Frequency - Octave * 9.71f);
			Frequency *= 2.03f;
			Amplitude *= 0.5f;
		}
		return Sum;
	}

	/** Hermite step that also works with A > B (falling edge). */
	float Step(float A, float B, float X)
	{
		const float T = FMath::Clamp((X - A) / (B - A), 0.0f, 1.0f);
		return T * T * (3.0f - 2.0f * T);
	}

	// ---- Designed layout (Docs/MAPA_01_RED_DUST_DIVIDE_S01.md) ----
	const FVector2D GridPoint(-2150.0f, -1400.0f);
	const FVector2D BasinCenter(-1850.0f, -1400.0f);
	const FVector2D ForkStart(-250.0f, -760.0f);
	const FVector2D BowlCenter(600.0f, -420.0f);
	const FVector2D IslandCenter(175.0f, -590.0f);
	const FVector2D ArchCenter(-700.0f, -350.0f);
	const FVector2D ApproachKeys[] = { FVector2D(-2150, -1400), FVector2D(-1800, -1400), FVector2D(-1400, -1340),
		FVector2D(-1000, -1200), FVector2D(-600, -1000), FVector2D(-250, -760) };
	// Canyon head: centre, half-width and floor (m). The last key closes as a box canyon until S02 is built.
	struct FCanyonKey
	{
		FVector2D Point;
		float HalfWidth;
		float Floor;
	};
	const FCanyonKey CanyonKeys[] = { { FVector2D(600, -420), 60.0f, -3.0f }, { FVector2D(900, -430), 30.0f, -6.0f },
		{ FVector2D(1250, -380), 24.0f, -20.0f }, { FVector2D(1600, -420), 20.0f, -45.0f }, { FVector2D(1950, -520), 26.0f, -60.0f },
		{ FVector2D(2250, -600), 14.0f, -62.0f } };
	constexpr int32 FinishKey = 4;

	struct FDome
	{
		FVector2D Point;
		float Radius;
		float Height;
	};
	// Navajo slickrock domes framing the basin and the first wash (never on the race line).
	const FDome Domes[] = { { FVector2D(-1950, -1060), 110.0f, 24.0f }, { FVector2D(-1640, -990), 90.0f, 18.0f },
		{ FVector2D(-1980, -1760), 120.0f, 28.0f }, { FVector2D(-1560, -1740), 95.0f, 20.0f },
		{ FVector2D(-1150, -1520), 80.0f, 16.0f }, { FVector2D(-820, -1390), 70.0f, 14.0f } };

	// The arch faces south-west: seen through from the grid and along the whole approach wash.
	const FEXDesertTerrain::FLandmark Arch = { ArchCenter, 130.0f, 70.0f, 245.0f };
	// Footprint kept inside 80 m so the RACING line (130 m away) keeps 40 m of open slickrock beside it.
	const FEXDesertTerrain::FLandmark Island = { IslandCenter, 80.0f, 95.0f, 20.0f };
	const FEXDesertTerrain::FLandmark Boundary[] = {
		{ FVector2D(-2250, 2050), 300.0f, 140.0f, 10.0f }, { FVector2D(-1250, 1950), 260.0f, 120.0f, 75.0f },
		{ FVector2D(-250, 2050), 320.0f, 150.0f, 140.0f }, { FVector2D(800, 1950), 280.0f, 130.0f, 200.0f },
		{ FVector2D(1850, 2050), 300.0f, 140.0f, 260.0f }, { FVector2D(2700, 1300), 280.0f, 130.0f, 320.0f },
		{ FVector2D(2700, 200), 300.0f, 140.0f, 40.0f }, { FVector2D(2750, -1250), 280.0f, 130.0f, 110.0f } };

	/** Dense Catmull-Rom sampling (about one point every 5 m). */
	void SampleSpline(const TArray<FVector2D>& Keys, TArray<FVector2D>& Out)
	{
		for (int32 Key = 0; Key < Keys.Num() - 1; ++Key)
		{
			const FVector2D& P0 = Keys[FMath::Max(Key - 1, 0)];
			const FVector2D& P1 = Keys[Key];
			const FVector2D& P2 = Keys[Key + 1];
			const FVector2D& P3 = Keys[FMath::Min(Key + 2, Keys.Num() - 1)];
			const int32 Steps = FMath::Max(2, FMath::CeilToInt(FVector2D::Distance(P1, P2) / 5.0f));
			for (int32 Sub = 0; Sub < Steps; ++Sub)
			{
				const float T = static_cast<float>(Sub) / Steps;
				const float T2 = T * T;
				const float T3 = T2 * T;
				Out.Add(0.5f * ((2.0f * P1) + (-P0 + P2) * T + (2.0f * P0 - 5.0f * P1 + 4.0f * P2 - P3) * T2 + (-P0 + 3.0f * P1 - 3.0f * P2 + P3) * T3));
			}
		}
		Out.Add(Keys.Last());
	}

	/** The fork around the island butte: SAFE swings 200 m north (about +6 % distance), RACING 130 m south. */
	void BranchKeys(float OffsetM, TArray<FVector2D>& Out)
	{
		const FVector2D Direction = (BowlCenter - ForkStart).GetSafeNormal();
		const FVector2D Left(-Direction.Y, Direction.X);
		for (int32 Index = 0; Index <= 6; ++Index)
		{
			const float T = Index / 6.0f;
			Out.Add(FMath::Lerp(ForkStart, BowlCenter, T) + Left * OffsetM * FMath::Sin(PI * T));
		}
	}

	/** A sampled channel (wash or canyon) with a grid for fast nearest-point queries. */
	struct FChannel
	{
		TArray<FVector2D> Points;
		TArray<float> Along;
		static constexpr float CellM = 120.0f;
		int32 Cells = 0;
		TArray<TArray<int32>> Grid;

		void Build(const TArray<FVector2D>& InPoints, float Reach)
		{
			Points = InPoints;
			Along.SetNumZeroed(Points.Num());
			for (int32 Index = 1; Index < Points.Num(); ++Index)
			{
				Along[Index] = Along[Index - 1] + FVector2D::Distance(Points[Index - 1], Points[Index]);
			}
			Cells = FMath::CeilToInt(2.0f * FEXDesertTerrain::HalfSizeM / CellM);
			Grid.SetNum(Cells * Cells);
			for (int32 Index = 0; Index < Points.Num() - 1; ++Index)
			{
				const FVector2D A = Points[Index];
				const FVector2D B = Points[Index + 1];
				for (int32 CellY = CellOf(FMath::Min(A.Y, B.Y) - Reach); CellY <= CellOf(FMath::Max(A.Y, B.Y) + Reach); ++CellY)
				{
					for (int32 CellX = CellOf(FMath::Min(A.X, B.X) - Reach); CellX <= CellOf(FMath::Max(A.X, B.X) + Reach); ++CellX)
					{
						Grid[CellY * Cells + CellX].Add(Index);
					}
				}
			}
		}

		int32 CellOf(float Coordinate) const
		{
			return FMath::Clamp(FMath::FloorToInt((Coordinate + FEXDesertTerrain::HalfSizeM) / CellM), 0, Cells - 1);
		}

		/** Distance to the centre line and the parameter (segment index + fraction) of the nearest point. */
		bool Nearest(const FVector2D& Point, float& OutDistance, int32& OutIndex, float& OutT) const
		{
			float Best = TNumericLimits<float>::Max();
			OutIndex = INDEX_NONE;
			for (const int32 Index : Grid[CellOf(Point.Y) * Cells + CellOf(Point.X)])
			{
				const FVector2D A = Points[Index];
				const FVector2D AB = Points[Index + 1] - A;
				const float LengthSquared = AB.SizeSquared();
				const float T = LengthSquared > KINDA_SMALL_NUMBER ? FMath::Clamp(FVector2D::DotProduct(Point - A, AB) / LengthSquared, 0.0f, 1.0f) : 0.0f;
				const float DistanceSquared = FVector2D::DistSquared(Point, A + AB * T);
				if (DistanceSquared < Best)
				{
					Best = DistanceSquared;
					OutIndex = Index;
					OutT = T;
				}
			}
			OutDistance = FMath::Sqrt(Best);
			return OutIndex != INDEX_NONE;
		}
	};

	struct FWorld
	{
		FChannel ApproachWash;
		FChannel SafeWash;
		FChannel Canyon;
		FChannel RacingLine;
		FChannel SafeLine;
		TArray<float> CanyonHalfWidth;
		TArray<float> CanyonFloor;
		TArray<FVector2D> Racing;
		TArray<FVector2D> Safe;
		TArray<FEXDesertTerrain::FCanyonPoint> CanyonPoints;
		TArray<FEXDesertTerrain::FSlab> Slabs;

		FWorld()
		{
			TArray<FVector2D> Approach;
			SampleSpline(TArray<FVector2D>(ApproachKeys, UE_ARRAY_COUNT(ApproachKeys)), Approach);
			ApproachWash.Build(Approach, 150.0f);

			TArray<FVector2D> SafeKeys;
			TArray<FVector2D> RacingKeys;
			BranchKeys(200.0f, SafeKeys);
			BranchKeys(-130.0f, RacingKeys);
			TArray<FVector2D> SafeBranch;
			TArray<FVector2D> RacingBranch;
			SampleSpline(SafeKeys, SafeBranch);
			SampleSpline(RacingKeys, RacingBranch);
			SafeWash.Build(SafeBranch, 150.0f);

			TArray<FVector2D> CanyonKeyPoints;
			for (const FCanyonKey& Key : CanyonKeys)
			{
				CanyonKeyPoints.Add(Key.Point);
			}
			TArray<FVector2D> CanyonLine;
			SampleSpline(CanyonKeyPoints, CanyonLine);
			Canyon.Build(CanyonLine, 150.0f);
			// Per-sample half-width and floor, interpolated between keys by distance.
			TArray<float> KeyAlong;
			KeyAlong.Add(0.0f);
			for (int32 Key = 1; Key < UE_ARRAY_COUNT(CanyonKeys); ++Key)
			{
				KeyAlong.Add(KeyAlong.Last() + FVector2D::Distance(CanyonKeys[Key - 1].Point, CanyonKeys[Key].Point));
			}
			const float Scale = Canyon.Along.Last() / KeyAlong.Last();
			for (int32 Index = 0; Index < CanyonLine.Num(); ++Index)
			{
				const float S = Canyon.Along[Index] / Scale;
				int32 Key = 0;
				while (Key < KeyAlong.Num() - 2 && S > KeyAlong[Key + 1])
				{
					++Key;
				}
				const float T = Step(KeyAlong[Key], KeyAlong[Key + 1], S);
				CanyonHalfWidth.Add(FMath::Lerp(CanyonKeys[Key].HalfWidth, CanyonKeys[Key + 1].HalfWidth, T));
				CanyonFloor.Add(FMath::Lerp(CanyonKeys[Key].Floor, CanyonKeys[Key + 1].Floor, T));
				CanyonPoints.Add({ CanyonLine[Index], CanyonHalfWidth.Last(), CanyonFloor.Last() });
			}

			// Race lines: approach, branch, then the canyon head up to the finish key.
			TArray<FVector2D> Exit;
			SampleSpline(TArray<FVector2D>(CanyonKeyPoints.GetData(), FinishKey + 1), Exit);
			for (TArray<FVector2D>* Line : { &Racing, &Safe })
			{
				Line->Append(Approach);
				Line->Append(Line == &Racing ? RacingBranch : SafeBranch);
				Line->Append(Exit);
			}
			RacingLine.Build(Racing, 450.0f);
			SafeLine.Build(Safe, 450.0f);

			// Four broken Kayenta slabs on the RACING branch, each tilted so its far end lifts ~1.2 m: a flow jump.
			for (const float Fraction : { 0.16f, 0.36f, 0.56f, 0.76f })
			{
				const int32 Index = FMath::Clamp(FMath::RoundToInt(Fraction * (RacingBranch.Num() - 1)), 1, RacingBranch.Num() - 1);
				const FVector2D Tangent = (RacingBranch[Index] - RacingBranch[Index - 1]).GetSafeNormal();
				Slabs.Add({ RacingBranch[Index], static_cast<float>(FMath::RadiansToDegrees(FMath::Atan2(Tangent.Y, Tangent.X))), 34.0f, 26.0f });
			}
		}
	};

	const FWorld& World()
	{
		static const FWorld Instance;
		return Instance;
	}

	float Bench(float X, float Y)
	{
		return 1.2f * Fbm(X / 450.0f, Y / 450.0f, 4) + 0.4f * Fbm(X / 90.0f, Y / 90.0f, 3);
	}

	/** Navajo tableland rising to the north and east: the natural edge of the sector. */
	float PlateauMask(float X, float Y)
	{
		const float North = Step(1550.0f, 1800.0f, Y + 120.0f * Fbm(X / 600.0f, 0.3f, 3));
		const float East = Step(2450.0f, 2700.0f, X + 120.0f * Fbm(0.7f, Y / 600.0f, 3));
		return FMath::Max(North, East);
	}

	/** Dune sea to the west and south (deep sand, the soft natural limit). */
	float DuneMask(float X, float Y)
	{
		return FMath::Max(Step(-2200.0f, -2550.0f, X + 80.0f * Fbm(0.1f, Y / 400.0f, 3)), Step(-2100.0f, -2450.0f, Y + 80.0f * Fbm(X / 400.0f, 0.9f, 3)));
	}

	float DuneHeight(float X, float Y)
	{
		const float Mask = DuneMask(X, Y);
		if (Mask <= 0.0f)
		{
			return 0.0f;
		}
		// Prevailing wind from the south-west: gentle windward slopes, short steep slip faces.
		const float Phase = (X * 0.7f + Y * 0.7f) / 120.0f + Fbm(X / 300.0f, Y / 300.0f, 3) * 1.2f;
		const float P = Phase - FMath::Floor(Phase);
		const float Profile = P < 0.78f ? FMath::Pow(P / 0.78f, 1.6f) : FMath::Square(1.0f - (P - 0.78f) / 0.22f);
		return Mask * (8.0f + 14.0f * Mask) * Profile * (0.75f + 0.25f * Fbm(X / 220.0f, Y / 220.0f, 2) + 0.25f);
	}

	float Mound(const FEXDesertTerrain::FLandmark& Site, float X, float Y)
	{
		const float D = FVector2D::Distance(FVector2D(X, Y), Site.Point) / Site.Radius;
		return Step(1.35f, 0.75f, D) * 0.18f * Site.Height;
	}

	/** Natural low ledges across the approach wash: flow jumps (1 m lip, < 4 degree ramp). */
	float WashLedges(float Along)
	{
		float Height = 0.0f;
		for (const float At : { 650.0f, 1350.0f })
		{
			const float Offset = Along - At;
			if (Offset > -15.0f && Offset < 0.0f)
			{
				Height = FMath::Max(Height, 1.0f + Offset / 15.0f);
			}
			else if (Offset >= 0.0f && Offset < 4.0f)
			{
				Height = FMath::Max(Height, 1.0f - Offset / 4.0f);
			}
		}
		return Height;
	}

	/** Ground before the canyon is cut: bench, domes, mounds, plateau, dunes, basin, bowl and washes. */
	float GroundHeight(float X, float Y, float* OutWashFactor = nullptr)
	{
		const FVector2D P(X, Y);
		const float Base = Bench(X, Y);
		float Height = Base;
		for (const FDome& Dome : Domes)
		{
			const float T = FVector2D::Distance(P, Dome.Point) / Dome.Radius;
			if (T < 1.0f)
			{
				Height = FMath::Max(Height, Base + Dome.Height * FMath::Pow(1.0f - T * T, 1.5f));
			}
		}
		Height = FMath::Max(Height, Base + Mound(Arch, X, Y));
		Height = FMath::Max(Height, Base + Mound(Island, X, Y));
		for (const FEXDesertTerrain::FLandmark& Mesa : Boundary)
		{
			Height = FMath::Max(Height, Base + Mound(Mesa, X, Y));
		}
		Height = FMath::Max(Height, PlateauMask(X, Y) * (110.0f + 10.0f * Fbm(X / 300.0f, Y / 300.0f, 3)));
		Height += DuneHeight(X, Y);
		const float Edge = FMath::Max(FMath::Abs(X), FMath::Abs(Y)) - 2750.0f;
		if (Edge > 0.0f)
		{
			Height += FMath::Pow(Edge / 274.0f, 1.6f) * 90.0f;
		}

		// The basin: a shallow slickrock depression around the grid, and the bowl where the fork rejoins.
		const float Basin = FMath::Sqrt(FMath::Square((X - BasinCenter.X) / 480.0f) + FMath::Square((Y - BasinCenter.Y) / 280.0f));
		Height -= 6.0f * Step(1.0f, 0.55f, Basin);
		Height -= 5.0f * Step(75.0f, 15.0f, FVector2D::Distance(P, BowlCenter));

		// Dry washes drain the basin east to the canyon: shallow channels with gravel beds.
		float WashFactor = 0.0f;
		float Distance;
		int32 Index;
		float T;
		const FWorld& W = World();
		if (W.ApproachWash.Nearest(P, Distance, Index, T))
		{
			const float Along = FMath::Lerp(W.ApproachWash.Along[Index], W.ApproachWash.Along[FMath::Min(Index + 1, W.ApproachWash.Along.Num() - 1)], T);
			const float Inside = Step(28.0f, 16.0f, Distance);
			Height -= 1.5f * Inside;
			Height += WashLedges(Along) * Step(30.0f, 20.0f, Distance);
			WashFactor = FMath::Max(WashFactor, Inside);
		}
		if (W.SafeWash.Nearest(P, Distance, Index, T))
		{
			const float Inside = Step(24.0f, 12.0f, Distance);
			Height -= 2.5f * Inside;
			WashFactor = FMath::Max(WashFactor, Inside);
		}

		// Each jump slab lies on a flat bed of the bench, so its top rises evenly from flush to the 1.2 m lip.
		for (const FEXDesertTerrain::FSlab& Slab : W.Slabs)
		{
			const FVector2D Local = (P - Slab.Point).GetRotated(-Slab.YawDeg);
			const float Outside = FMath::Max(FMath::Abs(Local.X) - Slab.LengthM * 0.5f, FMath::Abs(Local.Y) - Slab.WidthM * 0.5f);
			if (Outside < 9.0f)
			{
				Height = FMath::Lerp(Height, Bench(Slab.Point.X, Slab.Point.Y) - 0.1f, Step(9.0f, 2.0f, Outside));
			}
		}
		if (OutWashFactor)
		{
			*OutWashFactor = WashFactor;
		}
		return Height;
	}
}

float FEXDesertTerrain::CanyonWallWidth(float WallHeight)
{
	return 6.0f + 0.4f * FMath::Max(0.0f, WallHeight);
}

float FEXDesertTerrain::WashDistance(float X, float Y)
{
	float Best = TNumericLimits<float>::Max();
	float Distance;
	int32 Index;
	float T;
	const FWorld& W = World();
	for (const FChannel* Channel : { &W.ApproachWash, &W.SafeWash })
	{
		if (Channel->Nearest(FVector2D(X, Y), Distance, Index, T))
		{
			Best = FMath::Min(Best, Distance);
		}
	}
	return Best;
}

float FEXDesertTerrain::RouteDistance(float X, float Y)
{
	float Best = TNumericLimits<float>::Max();
	float Distance;
	int32 Index;
	float T;
	const FWorld& W = World();
	for (const FChannel* Channel : { &W.RacingLine, &W.SafeLine })
	{
		if (Channel->Nearest(FVector2D(X, Y), Distance, Index, T))
		{
			Best = FMath::Min(Best, Distance);
		}
	}
	return Best;
}

float FEXDesertTerrain::HeightAt(float X, float Y)
{
	float Height = GroundHeight(X, Y);
	// The canyon head cuts down through the bench: flat floor, then a steep wall slope up to the bench
	// (the Wingate cliff meshes stand on that slope; the lower part is the Chinle talus).
	float Distance;
	int32 Index;
	float T;
	const FWorld& W = World();
	if (W.Canyon.Nearest(FVector2D(X, Y), Distance, Index, T))
	{
		const int32 Next = FMath::Min(Index + 1, W.CanyonFloor.Num() - 1);
		const float HalfWidth = FMath::Lerp(W.CanyonHalfWidth[Index], W.CanyonHalfWidth[Next], T);
		const float Floor = FMath::Lerp(W.CanyonFloor[Index], W.CanyonFloor[Next], T) + 0.3f * Fbm(X / 40.0f, Y / 40.0f, 2);
		const float WallWidth = CanyonWallWidth(Height - Floor);
		if (Distance < HalfWidth)
		{
			Height = FMath::Min(Height, Floor);
		}
		else if (Distance < HalfWidth + WallWidth)
		{
			Height = FMath::Min(Height, FMath::Lerp(Floor, Height, Step(HalfWidth, HalfWidth + WallWidth, Distance)));
		}
	}
	return Height;
}

FLinearColor FEXDesertTerrain::SurfaceAt(float X, float Y)
{
	const FVector2D P(X, Y);
	float WashFactor = 0.0f;
	const float Ground = GroundHeight(X, Y, &WashFactor);
	const float Height = HeightAt(X, Y);

	// Kayenta slickrock shows through the sand on the bench; fully bare on domes, the basin floor and the slab field.
	float Slick = FMath::Clamp(0.3f + 0.7f * Fbm(X / 220.0f, Y / 220.0f, 3), 0.0f, 0.6f);
	for (const FDome& Dome : Domes)
	{
		Slick = FMath::Max(Slick, Step(1.05f, 0.85f, FVector2D::Distance(P, Dome.Point) / Dome.Radius));
	}
	const float Basin = FMath::Sqrt(FMath::Square((X - BasinCenter.X) / 480.0f) + FMath::Square((Y - BasinCenter.Y) / 280.0f));
	Slick = FMath::Max(Slick, Step(1.0f, 0.7f, Basin) * (Fbm(X / 60.0f, Y / 60.0f, 3) > -0.1f ? 0.85f : 0.2f));
	const TArray<FVector2D>& Racing = RoutePath(ERoute::Racing);
	for (int32 Index = 0; Index < Racing.Num(); Index += 6)
	{
		if (FVector2D::DistSquared(Racing[Index], IslandCenter) < FMath::Square(260.0f) && FVector2D::DistSquared(Racing[Index], P) < FMath::Square(45.0f))
		{
			Slick = FMath::Max(Slick, 0.8f);
			break;
		}
	}

	// Deep sand: the dune sea and loose patches in the SAFE wash.
	float Deep = DuneMask(X, Y);
	float Distance;
	int32 Index;
	float T;
	const FWorld& W = World();
	if (W.SafeWash.Nearest(P, Distance, Index, T) && Distance < 22.0f && Fbm(X / 50.0f, Y / 50.0f, 2) > 0.05f)
	{
		Deep = FMath::Max(Deep, 0.85f);
	}

	// Gravel: wash beds, the canyon floor and its talus slopes, and the mounds under the mesas.
	float Gravel = WashFactor * 0.5f;
	const float Cut = Ground - Height;
	Gravel = FMath::Max(Gravel, Step(1.0f, 6.0f, Cut) * 0.9f);
	for (const FLandmark& Site : { Arch, Island })
	{
		Gravel = FMath::Max(Gravel, Step(1.35f, 0.95f, FVector2D::Distance(P, Site.Point) / Site.Radius) * 0.7f);
	}
	Gravel = FMath::Max(Gravel, PlateauMask(X, Y) * (1.0f - PlateauMask(X, Y)) * 2.4f);
	Slick *= 1.0f - FMath::Max(Deep, WashFactor);
	return FLinearColor(FMath::Clamp(Slick, 0.0f, 1.0f), FMath::Clamp(Deep, 0.0f, 1.0f), FMath::Clamp(Gravel, 0.0f, 1.0f), 1.0f);
}

const TArray<FVector2D>& FEXDesertTerrain::RoutePath(ERoute Route)
{
	return Route == ERoute::Racing ? World().Racing : World().Safe;
}

FVector2D FEXDesertTerrain::StartPoint()
{
	return GridPoint;
}

float FEXDesertTerrain::StartYawDeg()
{
	return 0.0f;
}

FEXDesertTerrain::FLandmark FEXDesertTerrain::MesaArch()
{
	return Arch;
}

FEXDesertTerrain::FLandmark FEXDesertTerrain::IslandButte()
{
	return Island;
}

void FEXDesertTerrain::BoundaryMesas(TArray<FLandmark>& Out)
{
	Out.Append(Boundary, UE_ARRAY_COUNT(Boundary));
}

void FEXDesertTerrain::RacingSlabs(TArray<FSlab>& Out)
{
	Out.Append(World().Slabs);
}

const TArray<FEXDesertTerrain::FCanyonPoint>& FEXDesertTerrain::CanyonPoints()
{
	return World().CanyonPoints;
}
