#pragma once

#include "Blueprint/UserWidget.h"
#include "StardustRaceHudWidget.generated.h"

class APawn;
class UProgressBar;
class UTextBlock;
class UStardustCraftMovementComponent;
class UStardustRaceProgressComponent;

UCLASS()
class EXTRACTSTARDUSTUE_API UStardustRaceHudWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void SetCraft(APawn* InCraft);

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	UPROPERTY(Transient)
	TObjectPtr<APawn> CraftPawn;

	UPROPERTY(Transient)
	TObjectPtr<UStardustCraftMovementComponent> CraftMovement;

	UPROPERTY(Transient)
	TObjectPtr<UStardustRaceProgressComponent> RaceProgress;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> StateText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> SpeedText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> RaceText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> VitalsText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> ControlsText;

	UPROPERTY(Transient)
	TObjectPtr<UProgressBar> RaceProgressBar;

	void BuildHud();
	void RefreshHud();
};
