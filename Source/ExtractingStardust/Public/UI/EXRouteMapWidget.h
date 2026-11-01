#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "EXRouteMapWidget.generated.h"

/** The briefing's map: the race line from A to B seen from above, north up, fitted to the widget, with the two ends. */
UCLASS()
class EXTRACTINGSTARDUST_API UEXRouteMapWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** The race line in metres (AEXHoverCraft::GetMapRoute); thinned to a few hundred points. */
	void SetRoute(const TArray<FVector2D>& RouteM);
	bool HasRoute() const { return Points.Num() > 1; }
	/** The race HUD's minimap (player, 2026-11-01): a window round the craft that turns with it, the race line as a
	 *  glowing cyan track, the checkpoints (passed gold, the next one bright), B with its flag colours, the rivals. */
	void SetRadar(const TArray<FVector2D>& RouteM, float WindowM);
	void SetRadarView(const FVector2D& HereM, const FVector2D& Forward, int32 RouteIndex, const TArray<FVector2D>& RivalsM,
		const TArray<FVector2D>& GatesM, int32 GatesPassed, int32 MissedGate);

protected:
	virtual int32 NativePaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;

private:
	/** The line, scaled so its longer side is 1 (Extent: its size in those units). */
	TArray<FVector2f> Points;
	FVector2f Extent = FVector2f(1.0f, 1.0f);
	int32 PaintRadar(const FGeometry& Geometry, FSlateWindowElementList& OutDrawElements, int32 Layer) const;
	bool bRadar = false;
	float RadarWindowM = 2400.0f;
	TArray<FVector2D> RadarRoute;
	FVector2D RadarHere = FVector2D::ZeroVector;
	FVector2D RadarForward = FVector2D(1.0f, 0.0f);
	int32 RadarIndex = 0;
	TArray<FVector2D> RadarRivals;
	TArray<FVector2D> RadarGates;
	int32 RadarPassed = 0;
	int32 RadarMissed = 0;
};
