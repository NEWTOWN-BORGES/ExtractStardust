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

protected:
	virtual int32 NativePaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;

private:
	/** The line, scaled so its longer side is 1 (Extent: its size in those units). */
	TArray<FVector2f> Points;
	FVector2f Extent = FVector2f(1.0f, 1.0f);
};
