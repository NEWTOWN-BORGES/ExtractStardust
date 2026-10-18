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

	/** Turns a 0..1 slope into ledges, like eroded rock strata. */
	float Terrace(float T, float Steps)
	{
		const float Scaled = FMath::Clamp(T, 0.0f, 1.0f) * Steps;
		const float Base = FMath::Floor(Scaled);
		return FMath::Min(1.0f, (Base + Step(0.0f, 0.35f, Scaled - Base)) / Steps);
	}

	struct FMesa
	{
		FVector2D Center;
		float Radius;
		float Height;
	};

	// Isolated buttes on the plain, as in Wadi Rum.
	const FMesa Mesas[] = {
		{ FVector2D(-1350.0f, -250.0f), 170.0f, 85.0f },
		{ FVector2D(-950.0f, 650.0f), 110.0f, 55.0f },
		{ FVector2D(-1500.0f, 1250.0f), 230.0f, 110.0f },
		{ FVector2D(-450.0f, -1550.0f), 140.0f, 70.0f },
		{ FVector2D(-1250.0f, -1600.0f), 90.0f, 45.0f },
		{ FVector2D(-700.0f, 150.0f), 60.0f, 35.0f },
	};

	// Canyon route through the plateau: control points with half-width, half-pipe depth and floor height (metres).
	struct FCanyonKey
	{
		FVector2D Point;
		float HalfWidth;
		float HalfPipe;
		float Floor;
	};

	const FCanyonKey CanyonKeys[] = {
		{ FVector2D(-950.0f, -950.0f), 45.0f, 0.0f, 0.0f },
		{ FVector2D(-450.0f, -850.0f), 32.0f, 4.0f, -1.0f },
		{ FVector2D(0.0f, -1000.0f), 22.0f, 14.0f, -3.0f },     // natural half-pipe
		{ FVector2D(450.0f, -950.0f), 18.0f, 16.0f, -5.0f },
		{ FVector2D(800.0f, -600.0f), 10.0f, 2.0f, -7.0f },     // narrow stone corridor
		{ FVector2D(900.0f, -100.0f), 9.0f, 2.0f, -8.0f },
		{ FVector2D(650.0f, 350.0f), 45.0f, 3.0f, -10.0f },     // dry basin
		{ FVector2D(900.0f, 800.0f), 55.0f, 3.0f, -10.0f },
		{ FVector2D(1350.0f, 1050.0f), 30.0f, 10.0f, -8.0f },
		{ FVector2D(1250.0f, 1500.0f), 14.0f, 2.0f, -6.0f },    // canyon throat
		{ FVector2D(700.0f, 1650.0f), 12.0f, 2.0f, -5.0f },
		{ FVector2D(150.0f, 1450.0f), 25.0f, 8.0f, -3.0f },
		{ FVector2D(-350.0f, 1550.0f), 35.0f, 2.0f, -1.0f },
		{ FVector2D(-950.0f, 1350.0f), 45.0f, 0.0f, 0.0f },
	};
	constexpr int32 CanyonKeyCount = UE_ARRAY_COUNT(CanyonKeys);
	constexpr int32 SamplesPerSegment = 40;

	struct FCanyonSample
	{
		FVector2D Point;
		float HalfWidth;
		float HalfPipe;
		float Floor;
		float Distance;
	};

	/** Catmull-Rom path with per-sample attributes, a jump profile on the floor and a grid for fast lookups. */
	struct FCanyon
	{
		TArray<FCanyonSample> Samples;
		TArray<FVector2D> Points;
		float Length = 0.0f;
		static constexpr float CellM = 100.0f;
		static constexpr int32 GridCells = 42;
		TArray<TArray<int32>> Grid;

		FCanyon()
		{
			for (int32 Key = 0; Key < CanyonKeyCount - 1; ++Key)
			{
				const FCanyonKey& P0 = CanyonKeys[FMath::Max(Key - 1, 0)];
				const FCanyonKey& P1 = CanyonKeys[Key];
				const FCanyonKey& P2 = CanyonKeys[Key + 1];
				const FCanyonKey& P3 = CanyonKeys[FMath::Min(Key + 2, CanyonKeyCount - 1)];
				for (int32 Sub = 0; Sub < SamplesPerSegment; ++Sub)
				{
					const float T = static_cast<float>(Sub) / SamplesPerSegment;
					const float T2 = T * T;
					const float T3 = T2 * T;
					const FVector2D Point = 0.5f * ((2.0f * P1.Point) + (-P0.Point + P2.Point) * T
						+ (2.0f * P0.Point - 5.0f * P1.Point + 4.0f * P2.Point - P3.Point) * T2
						+ (-P0.Point + 3.0f * P1.Point - 3.0f * P2.Point + P3.Point) * T3);
					const float Smooth = T2 * (3.0f - 2.0f * T);
					FCanyonSample Sample;
					Sample.Point = Point;
					Sample.HalfWidth = FMath::Lerp(P1.HalfWidth, P2.HalfWidth, Smooth);
					Sample.HalfPipe = FMath::Lerp(P1.HalfPipe, P2.HalfPipe, Smooth);
					Sample.Floor = FMath::Lerp(P1.Floor, P2.Floor, Smooth);
					Sample.Distance = Samples.Num() > 0 ? Samples.Last().Distance + FVector2D::Distance(Samples.Last().Point, Point) : 0.0f;
					Samples.Add(Sample);
				}
			}
			FCanyonSample Last;
			Last.Point = CanyonKeys[CanyonKeyCount - 1].Point;
			Last.HalfWidth = CanyonKeys[CanyonKeyCount - 1].HalfWidth;
			Last.HalfPipe = CanyonKeys[CanyonKeyCount - 1].HalfPipe;
			Last.Floor = CanyonKeys[CanyonKeyCount - 1].Floor;
			Last.Distance = Samples.Last().Distance + FVector2D::Distance(Samples.Last().Point, Last.Point);
			Samples.Add(Last);
			Length = Last.Distance;
			for (const FCanyonSample& Sample : Samples)
			{
				Points.Add(Sample.Point);
			}

			// Each grid cell lists the path segments that can influence it (canyon half-width plus walls).
			Grid.SetNum(GridCells * GridCells);
			const float Reach = 160.0f;
			for (int32 Index = 0; Index < Samples.Num() - 1; ++Index)
			{
				const FVector2D A = Samples[Index].Point;
				const FVector2D B = Samples[Index + 1].Point;
				const int32 MinX = CellOf(FMath::Min(A.X, B.X) - Reach);
				const int32 MaxX = CellOf(FMath::Max(A.X, B.X) + Reach);
				const int32 MinY = CellOf(FMath::Min(A.Y, B.Y) - Reach);
				const int32 MaxY = CellOf(FMath::Max(A.Y, B.Y) + Reach);
				for (int32 CellY = MinY; CellY <= MaxY; ++CellY)
				{
					for (int32 CellX = MinX; CellX <= MaxX; ++CellX)
					{
						Grid[CellY * GridCells + CellX].Add(Index);
					}
				}
			}
		}

		static int32 CellOf(float Coordinate)
		{
			return FMath::Clamp(FMath::FloorToInt((Coordinate + FEXDesertTerrain::HalfSizeM) / CellM), 0, GridCells - 1);
		}

		/** Nearest point on the path: distance to it and the interpolated canyon attributes there. */
		bool Nearest(const FVector2D& Point, float& OutDistance, FCanyonSample& OutSample) const
		{
			const TArray<int32>& Candidates = Grid[CellOf(Point.Y) * GridCells + CellOf(Point.X)];
			float BestSquared = TNumericLimits<float>::Max();
			int32 BestIndex = INDEX_NONE;
			float BestT = 0.0f;
			for (const int32 Index : Candidates)
			{
				const FVector2D A = Samples[Index].Point;
				const FVector2D AB = Samples[Index + 1].Point - A;
				const float LengthSquared = AB.SizeSquared();
				const float T = LengthSquared > KINDA_SMALL_NUMBER ? FMath::Clamp(FVector2D::DotProduct(Point - A, AB) / LengthSquared, 0.0f, 1.0f) : 0.0f;
				const float DistanceSquared = FVector2D::DistSquared(Point, A + AB * T);
				if (DistanceSquared < BestSquared)
				{
					BestSquared = DistanceSquared;
					BestIndex = Index;
					BestT = T;
				}
			}
			if (BestIndex == INDEX_NONE)
			{
				return false;
			}
			const FCanyonSample& A = Samples[BestIndex];
			const FCanyonSample& B = Samples[BestIndex + 1];
			OutDistance = FMath::Sqrt(BestSquared);
			OutSample.Point = FMath::Lerp(A.Point, B.Point, BestT);
			OutSample.HalfWidth = FMath::Lerp(A.HalfWidth, B.HalfWidth, BestT);
			OutSample.HalfPipe = FMath::Lerp(A.HalfPipe, B.HalfPipe, BestT);
			OutSample.Floor = FMath::Lerp(A.Floor, B.Floor, BestT);
			OutSample.Distance = FMath::Lerp(A.Distance, B.Distance, BestT);
			return true;
		}
	};

	const FCanyon& Canyon()
	{
		static const FCanyon Instance;
		return Instance;
	}

	/** Rock kickers on the canyon floor: a ramp that rises over 30 m and drops off sharply. */
	float JumpProfile(float DistanceAlong, float Length)
	{
		const float Jumps[] = { 0.33f, 0.71f };
		float Height = 0.0f;
		for (const float Fraction : Jumps)
		{
			const float Offset = DistanceAlong - Fraction * Length;
			if (Offset > -30.0f && Offset < 0.0f)
			{
				Height = FMath::Max(Height, 3.5f * (1.0f + Offset / 30.0f));
			}
		}
		return Height;
	}

	float PlainHeight(float X, float Y)
	{
		return 2.5f * Fbm(X / 500.0f, Y / 500.0f, 4) + 0.6f * Fbm(X / 60.0f, Y / 60.0f, 3);
	}

	float DuneHeight(float X, float Y)
	{
		const FVector2D Start = FEXDesertTerrain::StartPoint();
		const float Region = Step(0.05f, 0.35f, Fbm(X / 700.0f + 5.0f, Y / 700.0f - 3.0f, 3)) * Step(-350.0f, -650.0f, X)
			* Step(250.0f, 450.0f, FVector2D::Distance(FVector2D(X, Y), Start));
		if (Region <= 0.0f)
		{
			return 0.0f;
		}
		// Wind from the west: long gentle windward slopes and short steep slip faces, broken up by noise.
		const float Phase = X / 110.0f + 0.35f * Fbm(X / 300.0f, Y / 300.0f, 3) * 3.0f + 0.15f * Y / 110.0f;
		const float P = Phase - FMath::Floor(Phase);
		const float Profile = P < 0.78f ? FMath::Pow(P / 0.78f, 1.6f) : FMath::Square(1.0f - (P - 0.78f) / 0.22f);
		return Region * 14.0f * Profile * (0.6f + 0.4f * Fbm(X / 250.0f, Y / 250.0f, 2) + 0.2f);
	}

	float MesaHeight(float X, float Y)
	{
		float Height = 0.0f;
		for (const FMesa& Mesa : Mesas)
		{
			const float Radius = Mesa.Radius * (1.0f + 0.15f * Fbm(X / 80.0f, Y / 80.0f, 3));
			const float D = FVector2D::Distance(FVector2D(X, Y), Mesa.Center) / Radius;
			if (D > 1.4f)
			{
				continue;
			}
			const float Top = Mesa.Height * (1.0f + 0.03f * Fbm(X / 40.0f, Y / 40.0f, 3));
			const float Body = Top * Terrace(Step(1.0f, 0.93f, D), 2.0f);
			const float Talus = Step(1.35f, 1.0f, D) * 0.14f * Mesa.Height;
			Height = FMath::Max(Height, FMath::Max(Body, Talus));
		}
		return Height;
	}

	float PlateauHeight(float X, float Y)
	{
		// Squircle-shaped tableland on the east side, with a wobbling cliff edge and terraced tops.
		const float QX = (X - 450.0f) / 1050.0f;
		const float QY = (Y - 300.0f) / 1350.0f;
		const float Q = FMath::Pow(FMath::Pow(FMath::Abs(QX), 4.0f) + FMath::Pow(FMath::Abs(QY), 4.0f), 0.25f) + 0.06f * Fbm(X / 150.0f, Y / 150.0f, 4);
		if (Q > 1.15f)
		{
			return 0.0f;
		}
		const float Top = FMath::Clamp(90.0f + 15.0f * FMath::RoundToFloat(Fbm(X / 600.0f, Y / 600.0f, 3) * 2.0f), 60.0f, 110.0f);
		const float Cliff = Top * Terrace(Step(1.0f, 0.97f, Q), 3.0f);
		const float Talus = Step(1.12f, 1.0f, Q) * 12.0f;
		return FMath::Max(Cliff, Talus);
	}

	float RimHeight(float X, float Y)
	{
		const float Edge = FMath::Max(FMath::Abs(X), FMath::Abs(Y)) - 1750.0f;
		return Edge > 0.0f ? FMath::Pow(Edge / 266.0f, 1.6f) * 130.0f * (0.85f + 0.3f * Fbm(X / 200.0f, Y / 200.0f, 3)) : 0.0f;
	}
}

float FEXDesertTerrain::HeightAt(float X, float Y)
{
	// Surrounding ground: plain, dunes, mesas, plateau and the raised map rim.
	float Ground = PlainHeight(X, Y) + DuneHeight(X, Y);
	Ground = FMath::Max(Ground, MesaHeight(X, Y));
	Ground = FMath::Max(Ground, PlateauHeight(X, Y));
	Ground += RimHeight(X, Y);

	// Flatten the start grid.
	const float StartBlend = Step(120.0f, 220.0f, FVector2D::Distance(FVector2D(X, Y), StartPoint()));
	Ground = FMath::Lerp(PlainHeight(X, Y) * 0.3f, Ground, StartBlend);

	// Carve the canyon: half-pipe floor between the walls, terraced walls up to the surrounding ground.
	float Distance = 0.0f;
	FCanyonSample Sample;
	if (Canyon().Nearest(FVector2D(X, Y), Distance, Sample))
	{
		const float Floor = Sample.Floor + JumpProfile(Sample.Distance, Canyon().Length) + 0.4f * Fbm(X / 30.0f, Y / 30.0f, 2);
		const float WallWidth = 6.0f + 0.12f * FMath::Max(0.0f, Ground - Floor);
		if (Distance < Sample.HalfWidth + WallWidth)
		{
			const float Inside = Distance / FMath::Max(1.0f, Sample.HalfWidth);
			float Carved;
			if (Distance <= Sample.HalfWidth)
			{
				Carved = Floor + Sample.HalfPipe * FMath::Square(Inside);
			}
			else
			{
				const float Wall = Step(Sample.HalfWidth, Sample.HalfWidth + WallWidth, Distance);
				Carved = FMath::Lerp(Floor + Sample.HalfPipe, Ground, Terrace(Wall, 3.0f));
			}
			Ground = FMath::Min(Ground, Carved);
		}
	}
	return Ground;
}

const TArray<FVector2D>& FEXDesertTerrain::CanyonPath()
{
	return Canyon().Points;
}

FVector2D FEXDesertTerrain::StartPoint()
{
	return FVector2D(-1600.0f, -1050.0f);
}

float FEXDesertTerrain::StartYawDeg()
{
	const FVector2D Direction = CanyonKeys[0].Point - StartPoint();
	return FMath::RadiansToDegrees(FMath::Atan2(Direction.Y, Direction.X));
}
