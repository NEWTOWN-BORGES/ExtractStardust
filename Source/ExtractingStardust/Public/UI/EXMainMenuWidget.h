#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "EXMainMenuWidget.generated.h"

class AEXHoverCraft;
class AEXRaceDirector;
class UEXRouteMapWidget;
class UTextBlock;
class UWidget;

/**
 * The start menu (the mock-up the player approved), drawn over the workshop where the chosen ship turns on the turntable
 * with the workshop lit (menu2.png; the dark menu was refused): the logo and the four lines on the left (EXPEDICAO SOLO, PELOTAO 15, HANGAR, SAIR), the
 * expedition briefing on the right (route map, distance, time, ship, cargo and what is at risk), the wallet at the top and
 * the keys at the bottom. Keyboard and pad drive it through the director (W/S or the d-pad, Enter or Cross); the mouse
 * highlights and clicks the lines. Built in code (no widget blueprint).
 */
UCLASS()
class EXTRACTINGSTARDUST_API UEXMainMenuWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void InitializeMenu(AEXRaceDirector* InRaceDirector);

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;
	virtual FReply NativeOnMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent) override;
	virtual FReply NativeOnMouseMove(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent) override;

private:
	void BuildTree();
	UWidget* BuildItem(int32 Index, const FString& Title, const FString& Description);
	UWidget* BuildBriefing();
	void Refresh();
	int32 ItemUnder(const FPointerEvent& MouseEvent) const;
	AEXHoverCraft* GetPlayerCraft() const;

	UPROPERTY(Transient) TObjectPtr<AEXRaceDirector> RaceDirector;
	// The four lines: the whole line (for the mouse), its highlight, its bar, number, title and description.
	UPROPERTY(Transient) TArray<TObjectPtr<UWidget>> ItemRoots;
	UPROPERTY(Transient) TArray<TObjectPtr<UWidget>> ItemGlows;
	UPROPERTY(Transient) TArray<TObjectPtr<UWidget>> ItemBars;
	UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> ItemNumbers;
	UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> ItemTitles;
	UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> ItemDescriptions;
	// The briefing and the wallet.
	UPROPERTY(Transient) TObjectPtr<UTextBlock> WalletText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> BriefSubText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> DistanceText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> DurationText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> ShipText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> CargoText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> RiskText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> LastRunText;
	UPROPERTY(Transient) TObjectPtr<UEXRouteMapWidget> RouteMap;
	int32 ShownChoice = INDEX_NONE;
	int32 HoveredItem = INDEX_NONE;
};
