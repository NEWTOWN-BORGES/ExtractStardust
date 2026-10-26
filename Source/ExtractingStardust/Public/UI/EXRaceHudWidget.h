#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "EXRaceHudWidget.generated.h"

class AEXRaceDirector;
class UBorder;
class UImage;
class USizeBox;
class UTextBlock;
class UWidget;

/**
 * The race HUD of the mock-up hud.png, in the mock-ups' fonts and icons: the place, time, distance and sector (top
 * left), the lives and what is at risk (top right), the speed with the nitro, heat and fuel bars (bottom left) and the
 * four quick slots round the d-pad with their icons (bottom right). The minimap, the guide arrow, the toasts and the
 * extraction table stay on the canvas (AEXHud). Built in code.
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
	void Refresh();

	UPROPERTY(Transient) TObjectPtr<AEXRaceDirector> RaceDirector;
	UTextBlock* PlaceText = nullptr;
	UTextBlock* FieldText = nullptr;
	UTextBlock* ClockText = nullptr;
	UTextBlock* SectorText = nullptr;
	UBorder* LifePips[6] = {};
	UTextBlock* RiskText = nullptr;
	UTextBlock* SpeedText = nullptr;
	FGaugeView Gauges[3];
	FSlotView Slots[4];
};
