#pragma once

#include "CoreMinimal.h"

/**
 * RED DUST DIVIDE, sector S01 THE BASIN + BROKEN MESA (see Docs/MAPA_01_RED_DUST_DIVIDE_S01.md).
 * Geology first: a Kayenta bench (datum 0 m) with Navajo domes, mesas and buttes on top, dry washes draining
 * east into a canyon cut through the Wingate cliff band, Chinle slopes at its foot, a dune sea to the west and
 * south. The race lines follow that geology. Every feature has a designed position; nothing is scattered at random.
 * Units: metres, with the map centred on the origin.
 */
struct EXTRACTINGSTARDUST_API FEXDesertTerrain
{
	/** Landscape vertices per side (24 x 24 components of 2 x 63 quads), 2 m apart: 6.05 km square. */
	static constexpr int32 Resolution = 3025;
	static constexpr float SpacingM = 2.0f;
	static constexpr float HalfSizeM = (Resolution - 1) * SpacingM * 0.5f;

	enum class ERoute : uint8
	{
		Racing,
		Safe
	};

	/** Ground height in metres. */
	static float HeightAt(float X, float Y);

	/** Surface mix: R = exposed slickrock, G = deep sand, B = gravel/talus (0..1 each); sand elsewhere. */
	static FLinearColor SurfaceAt(float X, float Y);

	/** Race line from the grid to the end of the sector, densely sampled (metres). */
	static const TArray<FVector2D>& RoutePath(ERoute Route);

	static FVector2D StartPoint();
	static float StartYawDeg();

	/** A designed landmark: centre, footprint radius and height (m), and the compass direction its main face looks
	 *  towards (degrees, 0 = +X); for the arch mesa that is the direction the opening faces. */
	struct FLandmark
	{
		FVector2D Point;
		float Radius;
		float Height;
		float YawDeg;
	};
	static FLandmark MesaArch();
	static FLandmark IslandButte();
	/** Navajo mesas that close the sector to the north and east. */
	static void BoundaryMesas(TArray<FLandmark>& Out);

	/** Broken Kayenta slabs on the RACING line: each is a flow-jump ramp. */
	struct FSlab
	{
		FVector2D Point;
		float YawDeg;
		float LengthM;
		float WidthM;
	};
	static void RacingSlabs(TArray<FSlab>& Out);

	/** The canyon head the route descends into: centre line, half-width and floor height (m). */
	struct FCanyonPoint
	{
		FVector2D Point;
		float HalfWidth;
		float Floor;
	};
	static const TArray<FCanyonPoint>& CanyonPoints();
	/** Horizontal width (m) of the canyon wall slope between the floor edge and the bench rim. */
	static float CanyonWallWidth(float WallHeight);

	/** Distance (m) to the nearest dry wash centre line (approach and SAFE washes): where water runs after storms
	 *  and soaks the banks. Exact up to about 150 m, larger beyond. */
	static float WashDistance(float X, float Y);

	/** Distance (m) to the nearest race line (RACING or SAFE); exact up to about 450 m, larger beyond. */
	static float RouteDistance(float X, float Y);
};
