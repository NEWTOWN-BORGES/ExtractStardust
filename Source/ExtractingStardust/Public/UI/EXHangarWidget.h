#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "UI/EXUiStyle.h"
#include "EXHangarWidget.generated.h"

class AEXHoverCraft;
class AEXRaceDirector;
class UBorder;
class UCanvasPanel;
class UHorizontalBox;
class UEXHangarModel;
class UImage;
class USizeBox;
class UTextBlock;
class UVerticalBox;
class UWidget;
class UWrapBox;
struct FEXHangarRow;

/**
 * The hangar, as the mock-ups the player approved draw it (Docs/MENU_HANGAR.md, Docs/MODULOS.md sec. 10:
 * equip_wing.png, equip_engine.png, consumiveis.png, cofre.png): the workshop with the ship on the turntable and five
 * tabs over it, in the mock-ups' fonts (Inter, Orbitron), glows and icons.
 * - NAVE: the roster (lives and stars of each ship), the ship's name over the turntable, its passive and what is at
 *   risk, the stats and LANÇAR EXPEDIÇÃO.
 * - EQUIPAR: the slots on the left (icon, module in its rarity's colour, class badge, insured shield), the pieces for
 *   the slot on the right (flame bar, rarity, value, chips), the label under the ship and notes pinned to the module,
 *   the stats now and with the piece, MONTAR.
 * - CONSUMÍVEIS: the four quick slots round the d-pad, the safe stock with its buy buttons, the summary.
 * - LOJA and COFRE: caches and modules; the module looked at shows as a card with the photo of the ship wearing it.
 * - An opened cache: the cards (the photo of the ship with the module, glowing in the rarity's colour, NOVO on the
 *   epic ones) turn over one by one; then keep everything or sell the commons.
 * The state is in UEXHangarModel; this widget only shows it. Built in code.
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
	static constexpr int32 MaxChips = 6;

	/** The frame round a line: fill, four edges, the colour bar on its left. */
	struct FLineFrame
	{
		UWidget* Root = nullptr;
		UBorder* Fill = nullptr;
		UBorder* Edges[4] = {};
		UBorder* Bar = nullptr;
		UImage* Wash = nullptr;
	};
	/** A slot of the ship (EQUIPAR, left): icon, family, module, class badge, insured shield. */
	struct FSlotView
	{
		FLineFrame Frame;
		UImage* Icon = nullptr;
		UTextBlock* Label = nullptr;
		UTextBlock* Title = nullptr;
		UWidget* SizeBox = nullptr;
		UTextBlock* SizeText = nullptr;
		UImage* Shield = nullptr;
	};
	/** A module line (EQUIPAR right, LOJA, COFRE): name, flame bar, tag, rarity, maker, value, chips. */
	struct FItemView
	{
		FLineFrame Frame;
		UImage* Icon = nullptr;
		UWidget* IconBox = nullptr;
		UTextBlock* Title = nullptr;
		USizeBox* FlameBox = nullptr;
		UImage* Flame = nullptr;
		UWidget* TagBox = nullptr;
		UTextBlock* Tag = nullptr;
		UTextBlock* Rarity = nullptr;
		UTextBlock* Maker = nullptr;
		UWidget* ValueBox = nullptr;
		UTextBlock* Value = nullptr;
		UWrapBox* ChipBox = nullptr;
		EXUi::FChipView Chips[MaxChips];
	};
	/** A ship of the roster (NAVE): name, role, lives and stars. */
	struct FShipView
	{
		FLineFrame Frame;
		UTextBlock* Name = nullptr;
		UTextBlock* Role = nullptr;
		UBorder* Lives[6] = {};
		UBorder* Stars[7] = {};
	};
	/** A quick slot round the d-pad (CONSUMÍVEIS): key, arrow, icon, name, count. */
	struct FTileView
	{
		UWidget* Root = nullptr;
		UBorder* Fill = nullptr;
		UBorder* Edges[4] = {};
		UImage* Icon = nullptr;
		UTextBlock* Name = nullptr;
		UBorder* Pips[2] = {};
	};
	/** A consumable of the safe stock (CONSUMÍVEIS, right): icon, name, effect, stock, buy button. */
	struct FStockView
	{
		FLineFrame Frame;
		UImage* Icon = nullptr;
		UTextBlock* Name = nullptr;
		UTextBlock* Effect = nullptr;
		UTextBlock* Count = nullptr;
		UTextBlock* Button = nullptr;
	};
	/** A plain line of the right panel (NAVE, LOJA, COFRE): label, value, note. */
	struct FInfoView
	{
		FLineFrame Frame;
		UTextBlock* Label = nullptr;
		UTextBlock* Title = nullptr;
		UTextBlock* Sub = nullptr;
	};
	/** A card: of an opened cache, or the module looked at in the shop and the vault. */
	struct FCardView
	{
		UWidget* Root = nullptr;
		UWidget* Front = nullptr;
		UWidget* Back = nullptr;
		UImage* GlowOuter = nullptr;
		UImage* GlowInner = nullptr;
		UBorder* Edges[4] = {};
		UBorder* ArtLine = nullptr;
		UImage* Photo = nullptr;
		UImage* Halo = nullptr;
		UImage* Icon = nullptr;
		UTextBlock* Rarity = nullptr;
		UTextBlock* Title = nullptr;
		UTextBlock* Maker = nullptr;
		UWrapBox* ChipBox = nullptr;
		EXUi::FChipView Chips[MaxChips];
		UTextBlock* Value = nullptr;
		UWidget* Ribbon = nullptr;
		UBorder* RibbonFill = nullptr;
		UTextBlock* RibbonText = nullptr;
		UTextBlock* Tag = nullptr;
		/** Where it stands in the cache grid (canvas slot) and its glow, raised when it is epic. */
		class UCanvasPanelSlot* Slot = nullptr;
		class UCanvasPanelSlot* GlowSlot = nullptr;
		FVector2D Home = FVector2D(0.0f, 0.0f);
	};
	struct FStatView
	{
		UTextBlock* Value = nullptr;
		UTextBlock* Delta = nullptr;
		USizeBox* Fill = nullptr;
		USizeBox* Change = nullptr;
		UBorder* ChangeColour = nullptr;
	};
	/** A note pinned next to the ship. */
	struct FCalloutView
	{
		UWidget* Root = nullptr;
		UBorder* Bar = nullptr;
		UTextBlock* Text = nullptr;
		class UCanvasPanelSlot* Slot = nullptr;
	};

	void BuildTree();
	FLineFrame MakeLineFrame(UWidget* Content, float BarWidth, const FMargin& Padding, bool bWash);
	void ShowLineFrame(const FLineFrame& Frame, const FLinearColor& Bar, bool bSelected, const FLinearColor& Accent) const;
	FSlotView MakeSlot();
	FItemView MakeItem(float Width);
	FShipView MakeShip();
	FTileView MakeTile(int32 Slot);
	FStockView MakeStock();
	FInfoView MakeInfo();
	FCardView MakeCard(float Width, float Height, float ArtHeight);
	UWidget* MakePanel(UWidget* Content, float Width, bool bAccentTop);
	UWidget* BuildTopBar();
	UWidget* BuildShipTitle();
	UWidget* BuildSlotsPanel();
	UWidget* BuildListPanel();
	UWidget* BuildQuickPanel();
	UWidget* BuildCandidatesPanel();
	UWidget* BuildStockPanel();
	UWidget* BuildInfoPanel();
	UWidget* BuildStats();
	UWidget* BuildAction();
	UWidget* BuildQuickSummary();
	UWidget* BuildPreviewLabel();
	UWidget* BuildCacheOverlay();
	void ShowSlot(const FSlotView& View, const FEXHangarRow* Row, bool bSelected) const;
	void ShowItem(const FItemView& View, const FEXHangarRow* Row, bool bSelected) const;
	void ShowShip(const FShipView& View, const FEXHangarRow* Row, bool bSelected) const;
	void ShowStock(const FStockView& View, const FEXHangarRow* Row, bool bSelected) const;
	void ShowInfo(const FInfoView& View, const FEXHangarRow* Row) const;
	void ShowCard(const FCardView& View, const FEXHangarRow* Card, bool bTurned, bool bInGrid) const;
	void Refresh();
	void RefreshStats(const UEXHangarModel* Model, bool bShow);
	void RefreshQuick(const UEXHangarModel* Model);
	void RefreshCallouts(const UEXHangarModel* Model, AEXHoverCraft* Craft);
	void RefreshCards(const UEXHangarModel* Model);
	void RefreshHints(const UEXHangarModel* Model);
	AEXHoverCraft* GetPlayerCraft() const;
	static bool IsUnder(const UWidget* Widget, const FPointerEvent& MouseEvent);

	UPROPERTY(Transient) TObjectPtr<AEXRaceDirector> RaceDirector;
	// Plain pointers into the widget tree (it owns the widgets and lives as long as this widget).
	TArray<UBorder*> TabFills;
	TArray<UBorder*> TabEdges;
	TArray<UTextBlock*> TabTexts;
	TArray<FSlotView> SlotViews;
	TArray<FItemView> ListViews;
	TArray<FShipView> ShipViews;
	TArray<FTileView> TileViews;
	TArray<FItemView> CandidateViews;
	TArray<FStockView> StockViews;
	TArray<FInfoView> InfoViews;
	TArray<FCardView> CardViews;
	TArray<FStatView> StatViews;
	TArray<FCalloutView> CalloutViews;
	FCardView LookedCard;
	UTextBlock* WalletText = nullptr;
	UTextBlock* ShipTitle = nullptr;
	UTextBlock* ShipSubtitle = nullptr;
	UHorizontalBox* ShipStars = nullptr;
	UBorder* ShipStarPips[7] = {};
	UTextBlock* ShipStarText = nullptr;
	UWidget* ShipTitleBox = nullptr;
	UTextBlock* SlotsTitle = nullptr;
	UTextBlock* ListTitle = nullptr;
	UTextBlock* ListMore = nullptr;
	UTextBlock* QuickTitle = nullptr;
	UTextBlock* CandidatesTitle = nullptr;
	UTextBlock* CandidatesMore = nullptr;
	UTextBlock* StockTitle = nullptr;
	UTextBlock* InfoTitle = nullptr;
	UTextBlock* InfoDetail = nullptr;
	UTextBlock* QuickSummaryText = nullptr;
	UTextBlock* NoticeText = nullptr;
	UTextBlock* ModeText = nullptr;
	UTextBlock* ActionText = nullptr;
	UTextBlock* LivesText = nullptr;
	UTextBlock* PreviewText = nullptr;
	UBorder* PreviewEdges[4] = {};
	UBorder* PreviewDiamond = nullptr;
	UTextBlock* CacheTitle = nullptr;
	UTextBlock* CacheSummary = nullptr;
	UTextBlock* CacheSoFar = nullptr;
	UTextBlock* CacheCost = nullptr;
	UWidget* SlotsPanel = nullptr;
	UWidget* ListPanel = nullptr;
	UWidget* QuickPanel = nullptr;
	UWidget* CandidatesPanel = nullptr;
	UWidget* StockPanel = nullptr;
	UWidget* InfoPanel = nullptr;
	UWidget* StatsPanel = nullptr;
	UWidget* ActionPanel = nullptr;
	UWidget* QuickSummaryPanel = nullptr;
	UWidget* PreviewPanel = nullptr;
	UWidget* CacheOverlay = nullptr;
	UWidget* CacheButtons = nullptr;
	UCanvasPanel* CalloutLayer = nullptr;
	UHorizontalBox* KeyBar = nullptr;
	FString ShownHints;
	// What the lists showed at the last Refresh: the first row of each window and the selected row (for the clicks).
	int32 LeftFirst = 0;
	int32 LeftSelected = 0;
	int32 RightFirst = 0;
	int32 RightSelected = -1;
};
