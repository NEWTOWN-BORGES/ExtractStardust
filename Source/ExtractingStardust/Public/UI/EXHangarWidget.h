#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "EXHangarWidget.generated.h"

class AEXHoverCraft;
class AEXRaceDirector;
class UBorder;
class UHorizontalBox;
class USizeBox;
class UTextBlock;
class UWidget;

/**
 * The hangar (the mock-up the player approved, hangar2.png): the workshop with the lights on and the ship turning on
 * the turntable, the roster of ships on the left (lives as pips), the ship's name on top, the cargo for the expedition on
 * the right (capacity, the items with their count and price, what is at risk), the ship's numbers at the bottom and the
 * launch button. Driven from the craft (W/S row, A/D quantity, Tab ship, mouse or Q/E to turn, wheel to zoom, Enter to
 * launch, Esc back to the menu); this widget only shows the state. Built in code (no widget blueprint).
 */
UCLASS()
class EXTRACTINGSTARDUST_API UEXHangarWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void InitializeHangar(AEXRaceDirector* InRaceDirector);

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	struct FShipCard
	{
		UWidget* Root = nullptr;
		UBorder* Fill = nullptr;
		UBorder* Edges[4] = {};
		UWidget* Bar = nullptr;
		UTextBlock* Name = nullptr;
		UTextBlock* Role = nullptr;
		UBorder* Pips[5] = {};
	};
	struct FCargoRow
	{
		UWidget* Root = nullptr;
		UBorder* Fill = nullptr;
		UBorder* Edges[4] = {};
		UTextBlock* Count = nullptr;
		UTextBlock* Cost = nullptr;
	};
	struct FStatTile
	{
		UTextBlock* Value = nullptr;
		USizeBox* Fill = nullptr;
	};

	void BuildTree();
	UWidget* BuildRoster();
	UWidget* BuildCargo();
	UWidget* BuildCargoRow(int32 Item);
	UWidget* BuildIcon(int32 Item);
	UWidget* BuildStats();
	UWidget* BuildLaunch();
	void Refresh();
	AEXHoverCraft* GetPlayerCraft() const;

	UPROPERTY(Transient) TObjectPtr<AEXRaceDirector> RaceDirector;
	// Plain pointers into the widget tree (it owns the widgets and lives as long as this widget).
	TArray<FShipCard> Cards;
	TArray<FCargoRow> Rows;
	FStatTile Stats[4];
	UPROPERTY(Transient) TObjectPtr<UTextBlock> WalletText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> ShipTitle;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> ShipSubtitle;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> CapacityText;
	UPROPERTY(Transient) TObjectPtr<UHorizontalBox> CapacityBar;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> RiskText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> NoticeText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> ModeText;
	int32 ShownCapacity = -1, ShownWeight = -1;
};
