#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "EXRaceHudWidget.generated.h"

class AEXRaceDirector;
class UBorder;
class UImage;
class USizeBox;
class UOverlaySlot;
class UTextBlock;
class UWidget;

/**
 * The race HUD of the mock-up hud.png, in the mock-ups' fonts and icons: the place, time, distance and sector (top
 * left), the lives and what is at risk (top right), the speed with the nitro, heat and fuel bars (bottom left) and the
 * four quick slots round the d-pad with their icons (bottom right). Player, 2026-10-26 ("em barra, como na versão
 * Unity"): the race as a bar along the top, A to B, with the checkpoints, the rivals and the player on it; the speed as
 * a segmented bar; the start lights; the checkpoint call-outs. The minimap, the guide arrow and the toasts stay on the
 * canvas (AEXHud); the results are UEXResultsWidget. Built in code.
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
	struct FGaugeView
	{
		USizeBox* Fill = nullptr;
		UBorder* Colour = nullptr;
		UTextBlock* Value = nullptr;
	};
	struct FSlotView
	{
		UBorder* Fill = nullptr;
		UBorder* Edges[4] = {};
		UImage* Icon = nullptr;
		UTextBlock* Count = nullptr;
	};

	void BuildTree();
	UWidget* BuildProgressBar(UWidgetTree* Tree);
	UWidget* BuildStartLights(UWidgetTree* Tree);
	void Refresh();
	void RefreshProgress(const class AEXHoverCraft* Craft);
	void RefreshStart();

	UPROPERTY(Transient) TObjectPtr<AEXRaceDirector> RaceDirector;
	UTextBlock* PlaceText = nullptr;
	UTextBlock* FieldText = nullptr;
	UTextBlock* ClockText = nullptr;
	UTextBlock* SectorText = nullptr;
	// The hull (CASCO), as in the Unity version: a bar from green to red with the percentage.
	USizeBox* HullFill = nullptr;
	UBorder* HullColour = nullptr;
	UTextBlock* HullText = nullptr;
	float HullShown = 1.0f;
	USizeBox* HullLoss = nullptr;
	UTextBlock* RiskText = nullptr;
	UTextBlock* SpeedText = nullptr;
	FGaugeView Gauges[3];
	FSlotView Slots[4];
	// The race bar (top): checkpoint ticks, the rivals' dots and the player's marker, moved by their overlay slots.
	TArray<UBorder*> CheckpointTicks;
	TArray<UOverlaySlot*> RivalSlots;
	TArray<UBorder*> RivalDots;
	UOverlaySlot* PlayerMarkSlot = nullptr;
	UOverlaySlot* PassedSlot = nullptr;
	USizeBox* PassedFill = nullptr;
	UTextBlock* ProgressText = nullptr;
	UWidget* CheckpointCall = nullptr;
	UTextBlock* CheckpointCallText = nullptr;
	UTextBlock* CheckpointCallPrize = nullptr;
	// The segmented speed bar under the number.
	TArray<UBorder*> SpeedSegments;
	// The start: three lights that turn red one by one, then all green.
	UWidget* StartPanel = nullptr;
	UBorder* StartLights[3] = {};
	UTextBlock* StartText = nullptr;
};
