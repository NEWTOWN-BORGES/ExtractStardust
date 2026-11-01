#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "EXRaceHudWidget.generated.h"

class AEXHoverCraft;
class AEXRaceDirector;
class UBorder;
class UCanvasPanelSlot;
class UEXRouteMapWidget;
class UImage;
class UOverlaySlot;
class USizeBox;
class UTextBlock;
class UTexture2D;
class UWidget;

/**
 * The race HUD after the player's concept (2026-11-01: "não tem de ser igual, mas seguir o princípio o máximo possível,
 * adaptado ao jogo"): dark navy plates with glowing cyan edges (Scripts/make_hud_art.py), italic Orbitron figures.
 * - Top left: the logo, the place ("1 / 16 POSIÇÃO") and the standings (ship, name; extracted gold, destroyed red).
 * - Top centre: the clock, the checkpoint count (this game's laps) and the race bar from A to B.
 * - Top right: the piggy bank, animated, with the spoils (ESPÓLIOS) and the rivals still racing; under it the minimap.
 * - Middle: the danger banner on the left (PERIGO!: a missed checkpoint, the hull, heat, fuel, the wrong way) and the
 *   checkpoint toast on the right (CHECKPOINT! +40).
 * - Bottom: the four consumables in hexagons (key and name), the speed with the boost bar, the ship's blueprint with the
 *   hull, fuel and heat, the lives and what is at risk.
 * The guide arrow and the messages stay on the canvas (AEXHud); the results are UEXResultsWidget. Built in code.
 */
UCLASS()
class EXTRACTINGSTARDUST_API UEXRaceHudWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void InitializeHud(AEXRaceDirector* InRaceDirector);

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	static constexpr int32 RowCount = 8;
	struct FRowView
	{
		UWidget* Root = nullptr;
		UImage* Back = nullptr;
		UImage* BackMe = nullptr;
		UTextBlock* Place = nullptr;
		UImage* Ship = nullptr;
		UTextBlock* Name = nullptr;
		UTextBlock* Tag = nullptr;
	};
	struct FHexView
	{
		UImage* Frame = nullptr;
		UImage* FrameOn = nullptr;
		UImage* Icon = nullptr;
		UTextBlock* Count = nullptr;
		UTextBlock* Name = nullptr;
		UWidget* Root = nullptr;
	};
	struct FStatView
	{
		USizeBox* Fill = nullptr;
		UBorder* Colour = nullptr;
		UTextBlock* Value = nullptr;
		UBorder* Light = nullptr;
	};

	void BuildTree();
	UWidget* BuildPlace(class UWidgetTree* Tree);
	UWidget* BuildTimer(class UWidgetTree* Tree);
	UWidget* BuildSpoils(class UWidgetTree* Tree);
	UWidget* BuildMap(class UWidgetTree* Tree);
	UWidget* BuildWarning(class UWidgetTree* Tree);
	UWidget* BuildToast(class UWidgetTree* Tree);
	UWidget* BuildSlots(class UWidgetTree* Tree);
	UWidget* BuildSpeed(class UWidgetTree* Tree);
	UWidget* BuildStatus(class UWidgetTree* Tree);
	UWidget* BuildStartLights(class UWidgetTree* Tree);
	void Refresh();
	void RefreshPlace();
	void RefreshTimer(const AEXHoverCraft* Craft);
	void RefreshSpoils(float Dt);
	void RefreshPiggySprite(float Dt);
	void RefreshMap(const AEXHoverCraft* Craft);
	void RefreshWarning(const AEXHoverCraft* Craft, float Now);
	void RefreshToast();
	void RefreshSlots(const AEXHoverCraft* Craft, float Now);
	void RefreshSpeed(const AEXHoverCraft* Craft, float Now);
	void RefreshStatus(const AEXHoverCraft* Craft, float Now);
	void RefreshStart();

	UPROPERTY(Transient) TObjectPtr<AEXRaceDirector> RaceDirector;

	// Place and standings.
	UTextBlock* PlaceText = nullptr;
	UTextBlock* FieldText = nullptr;
	UTextBlock* PlaceLabel = nullptr;
	FRowView Rows[RowCount];
	UWidget* RowsBox = nullptr;
	// Clock, checkpoint count, the race bar.
	UTextBlock* ClockText = nullptr;
	UTextBlock* CheckpointText = nullptr;
	UImage* CheckpointTab = nullptr;
	TArray<UBorder*> CheckpointTicks;
	TArray<UOverlaySlot*> CheckpointTickSlots;
	TArray<UOverlaySlot*> RivalSlots;
	TArray<UBorder*> RivalDots;
	UOverlaySlot* PlayerMarkSlot = nullptr;
	USizeBox* PassedFill = nullptr;
	UTextBlock* DistanceText = nullptr;
	// The piggy bank and its spoils.
	UWidget* PiggyIconBox = nullptr;
	UTextBlock* PiggyValue = nullptr;
	UTextBlock* PiggyGain = nullptr;
	UTextBlock* PiggySub = nullptr;
	TArray<UBorder*> RivalPips;
	float PiggyShown = 0.0f;
	/** The piggy itself, animated from its HD frames (SourceArt/UI/Piggy, Scripts/import_piggy.py): beams in, idles and
	 *  blinks, catches the coins when the pool grows, jumps and celebrates on extraction, cries when the player is out. */
	UImage* PiggySprite = nullptr;
	UCanvasPanelSlot* PiggySpriteSlot = nullptr;
	UPROPERTY(Transient) TArray<TObjectPtr<UTexture2D>> PiggyFrameAll;
	int32 PiggyFirst[8] = {};
	int32 PiggyAnim = 7;
	float PiggyTime = 0.0f;
	float PiggyBlinkAt = 4.0f;
	float PiggyLastPool = -1.0f;
	int32 PiggyShownAnim = -1;
	// The minimap.
	UEXRouteMapWidget* Map = nullptr;
	bool bMapRoute = false;
	// The danger banner and the checkpoint toast.
	UWidget* WarningBox = nullptr;
	UTextBlock* WarningTitle = nullptr;
	UTextBlock* WarningText = nullptr;
	UWidget* ToastBox = nullptr;
	UTextBlock* ToastTitle = nullptr;
	UTextBlock* ToastPrize = nullptr;
	// Consumables, speed and boost, the ship's state.
	FHexView Hexes[4];
	UTextBlock* SpeedText = nullptr;
	TArray<UBorder*> BoostSegments;
	UImage* Blueprint = nullptr;
	FString BlueprintShip;
	FStatView Stats[3];
	TArray<UBorder*> LifePips;
	UTextBlock* RiskText = nullptr;
	float HullShown = 1.0f;
	// The start: three lights that turn red one by one, then all green.
	UWidget* StartPanel = nullptr;
	UBorder* StartLights[3] = {};
	UTextBlock* StartText = nullptr;
};
