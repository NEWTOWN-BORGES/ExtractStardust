#pragma once

#include "CoreMinimal.h"

/**
 * The procedural desert world: an open sand plain with dunes, sandstone mesas, a plateau cut by a winding
 * canyon (half-pipes, narrow corridors, natural jumps) and a raised rim along the map edge.
 * Everything comes from code and a fixed layout, so the editor map builder and the game agree on the terrain.
 * Units: metres, with the map centred on the origin.
 */
struct EXTRACTINGSTARDUST_API FEXDesertTerrain
{
	/** Landscape vertices per side (16 x 16 components of 2 x 63 quads). */
	static constexpr int32 Resolution = 2017;
	static constexpr float SpacingM = 2.0f;
	static constexpr float HalfSizeM = (Resolution - 1) * SpacingM * 0.5f;

	/** Ground height in metres at a point of the map. */
	static float HeightAt(float X, float Y);

	/** Centre line of the canyon route, densely sampled (metres), from the south-west entry to the north-west exit. */
	static const TArray<FVector2D>& CanyonPath();

	/** Race start on the open plain and the direction it faces. */
	static FVector2D StartPoint();
	static float StartYawDeg();

	/** Canyon centre-line samples with the canyon half-width and floor height there (metres). */
	struct FCanyonPoint
	{
		FVector2D Point;
		float HalfWidth;
		float Floor;
	};
	static const TArray<FCanyonPoint>& CanyonPoints();

	/** Distance (m) from a point to the canyon centre line; optionally the canyon half-width there. */
	static float DistanceToCanyon(float X, float Y, float* OutHalfWidth = nullptr);

	/** Sites where sculpted mesas/buttes stand: X, Y, radius, height (m). */
	static void MesaSites(TArray<FVector4>& Out);

	static FVector2D PlateauCenter();
};
