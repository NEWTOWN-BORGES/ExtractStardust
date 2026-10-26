#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "EXHangarWidget.generated.h"

class AEXHoverCraft;
class AEXRaceDirector;
class UBorder;
class UHorizontalBox;
class UEXHangarModel;
class USizeBox;
class UTextBlock;
class UWidget;
struct FEXHangarRow;

/**
 * The hangar (Docs/MODULOS.md sec. 10, mock-ups equip_wing.png, equip_engine.png, consumiveis.png and cofre.png): the
 * workshop with the ship on the turntable and five tabs over it. NAVE: the ships and the launch button. EQUIPAR: the
 * slots on the left, the pieces for the slot on the right (the ship wears the one looked at; engine, propulsion,
 * reactor and utility show the skeleton with the engine running), the stats now and with it at the bottom.
 * CONSUMIVEIS: the four quick slots and the stock. LOJA: caches and the rotation of modules. COFRE: caches to open (the
 * cards turn over one by one) and the modules owned, to sell. The state is in UEXHangarModel; this widget only shows
 * it. Built in code.
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
	/** Player, 2026-10-25: the pieces could only be chosen with W/S/A/D/Enter; now the mouse clicks tabs, slots and pieces. */
	virtual FReply NativeOnMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent) override;

private:
	/** One list line: a colour bar, small label, title, sub-line, right text and tag. */
	struct FRowView
	{
		UWidget* Root = nullptr;
		UBorder* Fill = nullptr;
		UBorder* Edges[4] = {};
		UBorder* Bar = nullptr;
		UTextBlock* Label = nullptr;
		UTextBlock* Title = nullptr;
		UTextBlock* Sub = nullptr;
		UTextBlock* Right = nullptr;
		UTextBlock* Tag = nullptr;
	};
	/** One card of a cache being opened. */
	struct FCardView
	{
		UWidget* Root = nullptr;
		UWidget* Front = nullptr;
		UWidget* Back = nullptr;
		UBorder* Band = nullptr;
		UBorder* Edges[4] = {};
		UTextBlock* Label = nullptr;
		UTextBlock* Title = nullptr;
		UTextBlock* Sub = nullptr;
		UTextBlock* Right = nullptr;
		UTextBlock* Tag = nullptr;
	};
	struct FStatView
	{
		UTextBlock* Value = nullptr;
		UTextBlock* Delta = nullptr;
		USizeBox* Fill = nullptr;
		USizeBox* Change = nullptr;
		UBorder* ChangeColour = nullptr;
	};

	void BuildTree();
	FRowView MakeRow(float Width, float Height);
	UWidget* BuildLeftPanel();
	UWidget* BuildRightPanel();
	UWidget* BuildStats();
	UWidget* BuildLaunch();
	UWidget* BuildCacheOverlay();
	void ShowRow(const FRowView& View, const FEXHangarRow* Row, bool bSelected) const;
	void Refresh();
	void RefreshCards(const UEXHangarModel* Model);
	void RefreshHints(const UEXHangarModel* Model);
	AEXHoverCraft* GetPlayerCraft() const;
	/** Index of the first widget in Views that is shown and under the mouse (INDEX_NONE if none). */
	static int32 RowUnder(const TArray<FRowView>& Views, const FPointerEvent& MouseEvent);
	static bool IsUnder(const UWidget* Widget, const FPointerEvent& MouseEvent);

	UPROPERTY(Transient) TObjectPtr<AEXRaceDirector> RaceDirector;
	// Plain pointers into the widget tree (it owns the widgets and lives as long as this widget).
	TArray<UBorder*> TabFills;
	TArray<UTextBlock*> TabTexts;
	TArray<FRowView> LeftRows;
	TArray<FRowView> RightRows;
	TArray<FCardView> CardViews;
	TArray<FStatView> StatViews;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> WalletText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> ShipTitle;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> ShipSubtitle;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> LeftTitle;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> LeftMore;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> RightTitle;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> RightDetail;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> NoticeText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> ModeText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> LivesText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> CacheTitle;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> CacheSummary;
	UPROPERTY(Transient) TObjectPtr<UWidget> StatsPanel;
	UPROPERTY(Transient) TObjectPtr<UWidget> LaunchPanel;
	UPROPERTY(Transient) TObjectPtr<UWidget> CacheOverlay;
	UPROPERTY(Transient) TObjectPtr<UWidget> RightPanel;
	UPROPERTY(Transient) TObjectPtr<UHorizontalBox> KeyBar;
	FString ShownHints;
	// What the lists showed at the last Refresh: the first row of each window and the selected row (for the clicks).
	int32 LeftFirst = 0;
	int32 LeftSelected = 0;
	int32 RightFirst = 0;
	int32 RightSelected = -1;
};
