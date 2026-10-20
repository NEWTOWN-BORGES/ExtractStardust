#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "EXHud.generated.h"

/**
 * Race HUD on maps with a route (spline tagged EXRoute):
 * - minimap (top right), turning with the craft: the race line around it, the craft at the centre;
 * - a guide arrow (top centre) pointing to where the race line goes ~150 m ahead, green when on course, and
 *   "SENTIDO ERRADO" when driving against the lap;
 * - lap progress in km.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXHud : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;

private:
	void DrawMinimap(const TArray<FVector2D>& Route, const FVector2D& Here, const FVector2D& Forward, int32 Index);
	void DrawArrow(const FVector2D& Center, float AngleDeg, float Size, const FLinearColor& Colour);
};
