#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "EXHud.generated.h"

class UEXHangarWidget;
class UEXMainMenuWidget;

/**
 * Race HUD on maps with a route (spline tagged EXRoute):
 * - minimap (top right), turning with the craft: the race line around it, the craft at the centre;
 * - a guide arrow (top centre) pointing to where the race line goes ~150 m ahead, green when on course, and
 *   "SENTIDO ERRADO" when driving against the lap;
 * - lap progress in km;
 * - in the game modes (AEXRaceDirector): time, place, lives, the cargo (repair kits, surges, shields), countdown,
 *   messages, the other racers on the minimap, and the extraction results (EXTRACTED / DESTROYED / STRANDED, rewards).
 * The menu and the hangar are UMG widgets (UEXMainMenuWidget, UEXHangarWidget) over the workshop (AEXHangarStage).
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXHud : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;

private:
	void DrawMinimap(const TArray<FVector2D>& Route, const FVector2D& Here, const FVector2D& Forward, int32 Index,
		const TArray<FVector2D>& Others);
	/** Game modes: time, place, lives, the cargo, countdown, messages, the extraction results at the end. */
	void DrawRace(const class AEXRaceDirector* Race, const class AEXHoverCraft* Craft);
	/** Shows the menu or the hangar widget (or neither) and sets the input for it: the menu takes the mouse, the hangar
	 *  and the race leave it to the game (the mouse turns the ship in the hangar). */
	void ShowScreens(class AEXRaceDirector* Race, bool bMenu, bool bHangar);
	void DrawArrow(const FVector2D& Center, float AngleDeg, float Size, const FLinearColor& Colour);

	UPROPERTY(Transient)
	TObjectPtr<UEXMainMenuWidget> MainMenuWidget;

	UPROPERTY(Transient)
	TObjectPtr<UEXHangarWidget> HangarWidget;

	/** The input set last: -1 none yet, 0 the game only, 1 the menu (game and UI, cursor shown). */
	int32 InputScreen = -1;
};
