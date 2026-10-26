#include "UI/EXHangarWidget.h"

#include "Blueprint/WidgetLayoutLibrary.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WrapBox.h"
#include "Engine/World.h"
#include "Flight/EXHoverCraft.h"
#include "Game/EXHangarModel.h"
#include "Game/EXProfile.h"
#include "GameFramework/PlayerController.h"
#include "Race/EXRaceDirector.h"

// Sizes are the mock-ups' (1600 x 900) times 1.2, in Slate units at 1920 x 1080; font sizes are the mock-ups' pixels
// times 0.9 (Slate sizes are points at 96 DPI).
namespace
{
	constexpr int32 HangarSlotRows = 8;
	constexpr int32 HangarListRows = 7;
	constexpr int32 HangarShipRows = 5;
	constexpr int32 HangarCandidateRows = 5;
	constexpr int32 HangarStockRows = 6;
	constexpr int32 HangarInfoRows = 6;
	constexpr int32 HangarCards = 10;
	constexpr int32 HangarCallouts = 2;
	constexpr int32 HangarTabs = static_cast<int32>(EEXHangarTab::Count);
	constexpr float HangarStatBarWidth = 196.0f;
	constexpr float PanelLeft = 43.0f;
	constexpr float PanelTop = 110.0f;
	constexpr float KeyBarHeight = 55.0f;
	// The cache's grid (mock-up cofre.png): five cards a row, glowing round the edges.
	constexpr float CardW = 248.0f;
	constexpr float CardH = 331.0f;
	constexpr float CardArt = 158.0f;
	constexpr float CardGap = 19.0f;
	constexpr float CardGlow = 22.0f;
	constexpr float CardRaise = 10.0f;
	constexpr float GridW = CardW * 5.0f + CardGap * 4.0f + CardGlow * 2.0f;
	constexpr float GridH = CardH * 2.0f + CardGap + CardGlow * 2.0f + CardRaise;

	/** The stats under the ship, in EEXStat order (the eight core stats). */
	const TCHAR* const HangarStatNames[8] = { TEXT("VELOCIDADE"), TEXT("ACELERAÇÃO"), TEXT("MANOBRA"), TEXT("ESTABILIDADE"),
		TEXT("CASCO  ·  VIDAS"), TEXT("EFICIÊNCIA"), TEXT("REFRIGERAÇÃO"), TEXT("NITRO") };
	/** The quick slots round the d-pad: key 1 up, 2 down, 3 left, 4 right. */
	const TCHAR* const QuickArrows[EXMeta::QuickSlots] = { TEXT("▲"), TEXT("▼"), TEXT("◀"), TEXT("▶") };

	FLinearColor PlateFill() { return EXUi::Hex(18, 12, 8, 0.72f); }
	FLinearColor Bad() { return EXUi::Hex(255, 90, 74); }
	FLinearColor Gold() { return EXUi::Hex(255, 208, 64); }
	FLinearColor WithAlpha(const FLinearColor& Colour, float Alpha)
	{
		return FLinearColor(Colour.R, Colour.G, Colour.B, Alpha);
	}

	/** A row of small diamonds (the lives, the stars, a quick slot's count). */
	UHorizontalBox* Diamonds(UWidgetTree* Tree, int32 Count, float Size, float Gap, UBorder** Out)
	{
		UHorizontalBox* Row = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		for (int32 Index = 0; Index < Count; ++Index)
		{
			UBorder* Pip = EXUi::Box(Tree, EXUi::Ok());
			USizeBox* Holder = EXUi::Sized(Tree, Size, Size, Pip);
			Holder->SetRenderTransformAngle(45.0f);
			EXUi::AddH(Row, Holder, FMargin(Index > 0 ? Gap : 0.0f, 0.0f, 0.0f, 0.0f));
			Out[Index] = Pip;
		}
		return Row;
	}

	/** Value with the STARDUST gem after it ("≈ 7 200 ✦"). */
	UWidget* ValueWithGem(UWidgetTree* Tree, UTextBlock*& OutText, int32 Size, const FLinearColor& Colour)
	{
		UHorizontalBox* Row = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		OutText = EXUi::WeightText(Tree, TEXT(""), Size, Colour, 600);
		EXUi::AddH(Row, OutText);
		EXUi::AddH(Row, EXUi::GemImage(Tree, Size * 0.95f), FMargin(4.0f, 0.0f, 0.0f, 0.0f));
		return Row;
	}

	FString ValueText(const FEXHangarRow& Row)
	{
		return Row.Value < 0 ? FString() : (Row.bApprox ? TEXT("≈ ") : TEXT("")) + EXUi::Thousands(Row.Value);
	}
}

void UEXHangarWidget::InitializeHangar(AEXRaceDirector* InRaceDirector)
{
	RaceDirector = InRaceDirector;
	// The mouse turns the ship (game input): the widget never takes it.
	SetVisibility(ESlateVisibility::HitTestInvisible);
}

TSharedRef<SWidget> UEXHangarWidget::RebuildWidget()
{
	// Built in code: the tree must exist before the Slate widgets are made from it.
	if (WidgetTree && !WidgetTree->RootWidget)
	{
		BuildTree();
	}
	return Super::RebuildWidget();
}

void UEXHangarWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	Refresh();
}

// ------------------------------------------------------------------------------------------------------------ building

void UEXHangarWidget::BuildTree()
{
	UWidgetTree* Tree = WidgetTree;
	UOverlay* Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("HangarRoot"));
	Tree->RootWidget = Root;

	// The notes pinned to the ship sit on their own layer, placed where the module is on the screen.
	CalloutLayer = Tree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass());
	EXUi::AddO(Root, CalloutLayer, HAlign_Fill, VAlign_Fill);
	for (int32 Index = 0; Index < HangarCallouts; ++Index)
	{
		FCalloutView View;
		UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		View.Bar = EXUi::Box(Tree, EXUi::Rust());
		EXUi::AddH(Line, EXUi::Sized(Tree, 2.0f, 0.0f, View.Bar), FMargin(0.0f), false, VAlign_Fill);
		View.Text = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Bone(), 500);
		EXUi::AddH(Line, EXUi::Box(Tree, EXUi::Hex(10, 7, 5, 0.72f), FMargin(10.0f, 5.0f, 10.0f, 5.0f), View.Text), FMargin(0.0f), false, VAlign_Fill);
		View.Root = Line;
		View.Slot = CalloutLayer->AddChildToCanvas(Line);
		View.Slot->SetAutoSize(true);
		Line->SetVisibility(ESlateVisibility::Collapsed);
		CalloutViews.Add(View);
	}

	EXUi::AddO(Root, BuildTopBar(), HAlign_Fill, VAlign_Top);
	ShipTitleBox = BuildShipTitle();
	EXUi::AddO(Root, ShipTitleBox, HAlign_Center, VAlign_Top, FMargin(0.0f, 110.0f, 0.0f, 0.0f));

	SlotsPanel = BuildSlotsPanel();
	EXUi::AddO(Root, SlotsPanel, HAlign_Left, VAlign_Top, FMargin(PanelLeft, PanelTop, 0.0f, 0.0f));
	ListPanel = BuildListPanel();
	EXUi::AddO(Root, ListPanel, HAlign_Left, VAlign_Top, FMargin(PanelLeft, PanelTop, 0.0f, 0.0f));
	QuickPanel = BuildQuickPanel();
	EXUi::AddO(Root, QuickPanel, HAlign_Left, VAlign_Top, FMargin(PanelLeft, PanelTop, 0.0f, 0.0f));
	CandidatesPanel = BuildCandidatesPanel();
	EXUi::AddO(Root, CandidatesPanel, HAlign_Right, VAlign_Top, FMargin(0.0f, PanelTop, PanelLeft, 0.0f));
	StockPanel = BuildStockPanel();
	EXUi::AddO(Root, StockPanel, HAlign_Right, VAlign_Top, FMargin(0.0f, PanelTop, PanelLeft, 0.0f));
	InfoPanel = BuildInfoPanel();
	EXUi::AddO(Root, InfoPanel, HAlign_Right, VAlign_Top, FMargin(0.0f, PanelTop, PanelLeft, 0.0f));

	StatsPanel = BuildStats();
	EXUi::AddO(Root, EXUi::Sized(Tree, 910.0f, 0.0f, StatsPanel), HAlign_Center, VAlign_Bottom, FMargin(0.0f, 0.0f, 50.0f, KeyBarHeight));
	ActionPanel = BuildAction();
	EXUi::AddO(Root, ActionPanel, HAlign_Right, VAlign_Bottom, FMargin(0.0f, 0.0f, PanelLeft - 22.0f, 74.0f - 22.0f));
	QuickSummaryPanel = BuildQuickSummary();
	EXUi::AddO(Root, QuickSummaryPanel, HAlign_Center, VAlign_Bottom, FMargin(0.0f, 0.0f, 0.0f, 74.0f));
	PreviewPanel = BuildPreviewLabel();
	EXUi::AddO(Root, PreviewPanel, HAlign_Center, VAlign_Bottom, FMargin(0.0f, 0.0f, 0.0f, 326.0f));

	NoticeText = EXUi::OutlinedText(Tree, TEXT(""), 13, EXUi::RustHot(), 60, 1, EXUi::Ink(0.8f));
	EXUi::AddO(Root, NoticeText, HAlign_Center, VAlign_Bottom, FMargin(0.0f, 0.0f, 0.0f, 282.0f));

	CacheOverlay = BuildCacheOverlay();
	EXUi::AddO(Root, CacheOverlay, HAlign_Fill, VAlign_Fill);

	// Bottom: the keys of the tab (rebuilt when they change).
	KeyBar = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	UVerticalBox* Bottom = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Bottom, EXUi::Sized(Tree, 0.0f, 1.0f, EXUi::Box(Tree, EXUi::Rust(0.5f))));
	EXUi::AddV(Bottom, EXUi::Sized(Tree, 0.0f, KeyBarHeight, EXUi::Box(Tree, EXUi::Hex(8, 5, 3, 0.92f), FMargin(58.0f, 0.0f, 58.0f, 0.0f), KeyBar)));
	EXUi::AddO(Root, Bottom, HAlign_Fill, VAlign_Bottom);
}

UEXHangarWidget::FLineFrame UEXHangarWidget::MakeLineFrame(UWidget* Content, float BarWidth, const FMargin& Padding, bool bWash)
{
	UWidgetTree* Tree = WidgetTree;
	FLineFrame Frame;
	UOverlay* Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	// Under the text: the fill, then the selection's wash fading to the right (the mock-ups' gradient).
	Frame.Fill = EXUi::Box(Tree, EXUi::Bone(0.035f));
	EXUi::AddO(Root, Frame.Fill, HAlign_Fill, VAlign_Fill);
	if (bWash)
	{
		Frame.Wash = EXUi::Image(Tree, EXUi::Icon(TEXT("ui_fade_h")), EXUi::Rust(0.22f));
		Frame.Wash->SetVisibility(ESlateVisibility::Collapsed);
		EXUi::AddO(Root, Frame.Wash, HAlign_Fill, VAlign_Fill);
	}
	EXUi::AddO(Root, Content, HAlign_Fill, VAlign_Center, Padding);
	for (int32 Side = 0; Side < 4; ++Side)
	{
		Frame.Edges[Side] = EXUi::Box(Tree, EXUi::Bone(0.07f));
		const bool bHorizontal = Side < 2;
		EXUi::AddO(Root, EXUi::Sized(Tree, bHorizontal ? 0.0f : 1.0f, bHorizontal ? 1.0f : 0.0f, Frame.Edges[Side]),
			bHorizontal ? HAlign_Fill : (Side == 2 ? HAlign_Left : HAlign_Right), bHorizontal ? (Side == 0 ? VAlign_Top : VAlign_Bottom) : VAlign_Fill);
	}
	if (BarWidth > 0.0f)
	{
		Frame.Bar = EXUi::Box(Tree, EXUi::Rust());
		EXUi::AddO(Root, EXUi::Sized(Tree, BarWidth, 0.0f, Frame.Bar), HAlign_Left, VAlign_Fill, FMargin(0.0f, BarWidth < 4.0f ? 7.0f : 0.0f, 0.0f,
			BarWidth < 4.0f ? 7.0f : 0.0f));
	}
	Frame.Root = Root;
	return Frame;
}

void UEXHangarWidget::ShowLineFrame(const FLineFrame& Frame, const FLinearColor& Bar, bool bSelected, const FLinearColor& Accent) const
{
	Frame.Fill->SetBrushColor(bSelected ? WithAlpha(Accent, 0.14f) : EXUi::Bone(0.035f));
	for (UBorder* Edge : Frame.Edges)
	{
		Edge->SetBrushColor(bSelected ? WithAlpha(Accent, 0.75f) : EXUi::Bone(0.07f));
	}
	if (Frame.Wash)
	{
		Frame.Wash->SetColorAndOpacity(WithAlpha(Accent, 0.22f));
		Frame.Wash->SetVisibility(bSelected && EXUi::Icon(TEXT("ui_fade_h")) ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	}
	if (Frame.Bar)
	{
		Frame.Bar->SetBrushColor(Bar);
	}
}

UWidget* UEXHangarWidget::MakePanel(UWidget* Content, float Width, bool bAccentTop)
{
	const EXUi::FFrame Panel = EXUi::Frame(WidgetTree, bAccentTop ? EXUi::Rust(0.35f) : EXUi::Bone(0.09f), PlateFill(), 1.0f,
		FMargin(17.0f, 17.0f, 17.0f, 12.0f), bAccentTop ? 4.0f : -1.0f);
	if (bAccentTop)
	{
		Panel.Edges[0]->SetBrushColor(EXUi::Rust());
	}
	Panel.Fill->SetContent(Content);
	return EXUi::Sized(WidgetTree, Width, 0.0f, Panel.Root);
}

UWidget* UEXHangarWidget::BuildTopBar()
{
	UWidgetTree* Tree = WidgetTree;
	UOverlay* Bar = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	// A dark band fading down (linear-gradient(180deg, rgba(8,6,5,.82), transparent)).
	if (UTexture2D* Fade = EXUi::Icon(TEXT("ui_fade_v")))
	{
		EXUi::AddO(Bar, EXUi::Image(Tree, Fade, EXUi::Hex(8, 6, 5, 0.82f)), HAlign_Fill, VAlign_Fill);
	}
	else
	{
		EXUi::AddO(Bar, EXUi::Box(Tree, EXUi::Hex(8, 6, 5, 0.55f)), HAlign_Fill, VAlign_Fill);
	}
	UHorizontalBox* Top = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Top, EXUi::TitleText(Tree, TEXT("HANGAR"), 22, EXUi::Bone(), 160), FMargin(0.0f, 0.0f, 41.0f, 0.0f));
	for (int32 Tab = 0; Tab < HangarTabs; ++Tab)
	{
		UTextBlock* Label = EXUi::WeightText(Tree, UEXHangarModel::TabName(static_cast<EEXHangarTab>(Tab)), 11, EXUi::Sand(), 600, 180);
		const EXUi::FFrame Chip = EXUi::Frame(Tree, EXUi::Bone(0.15f), EXUi::Hex(10, 7, 5, 0.35f), 1.0f, FMargin(19.0f, 10.0f, 19.0f, 10.0f));
		Chip.Fill->SetContent(Label);
		EXUi::AddH(Top, Chip.Root, FMargin(0.0f, 0.0f, 7.0f, 0.0f));
		TabFills.Add(Chip.Fill);
		TabEdges.Append(Chip.Edges, 4);
		TabTexts.Add(Label);
	}
	EXUi::AddH(Top, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	EXUi::AddH(Top, EXUi::GemImage(Tree, 16.0f), FMargin(0.0f, 0.0f, 12.0f, 0.0f));
	WalletText = EXUi::WeightText(Tree, TEXT("0"), 16, EXUi::Bone(), 800);
	EXUi::AddH(Top, WalletText, FMargin(0.0f, 0.0f, 10.0f, 0.0f));
	EXUi::AddH(Top, EXUi::WeightText(Tree, TEXT("STARDUST"), 11, EXUi::Sand(), 600, 200));
	EXUi::AddO(Bar, Top, HAlign_Fill, VAlign_Center, FMargin(48.0f, 0.0f, 48.0f, 0.0f));
	return EXUi::Sized(Tree, 0.0f, 77.0f, Bar);
}

UWidget* UEXHangarWidget::BuildShipTitle()
{
	// The ship's name over the turntable, dark on the lit workshop (mock-up hangar2), its line and its stars.
	UWidgetTree* Tree = WidgetTree;
	UVerticalBox* Title = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	ShipTitle = EXUi::TitleText(Tree, TEXT("-"), 49, EXUi::Hex(29, 20, 14, 0.9f), 100);
	ShipTitle->SetShadowOffset(FVector2D(0.0f, 1.0f));
	ShipTitle->SetShadowColorAndOpacity(FLinearColor(1.0f, 1.0f, 1.0f, 0.4f));
	EXUi::AddV(Title, ShipTitle, FMargin(0.0f), HAlign_Center);
	ShipSubtitle = EXUi::WeightText(Tree, TEXT("-"), 12, EXUi::Hex(90, 70, 54), 700, 300);
	EXUi::AddV(Title, ShipSubtitle, FMargin(0.0f, 5.0f, 0.0f, 0.0f), HAlign_Center);
	ShipStars = Diamonds(Tree, EXMeta::MaxStars, 11.0f, 7.0f, ShipStarPips);
	UHorizontalBox* StarLine = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(StarLine, ShipStars);
	ShipStarText = EXUi::WeightText(Tree, TEXT(""), 11, EXUi::Hex(150, 104, 20), 800, 160);
	EXUi::AddH(StarLine, ShipStarText, FMargin(12.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddV(Title, StarLine, FMargin(0.0f, 9.0f, 0.0f, 0.0f), HAlign_Center);
	return Title;
}

UEXHangarWidget::FSlotView UEXHangarWidget::MakeSlot()
{
	UWidgetTree* Tree = WidgetTree;
	FSlotView View;
	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	// The slot's icon in a small dark square.
	const EXUi::FFrame IconFrame = EXUi::Frame(Tree, EXUi::Bone(0.12f), EXUi::Ink(0.35f), 1.0f, FMargin(9.0f));
	View.Icon = EXUi::Image(Tree, nullptr, EXUi::RustHot());
	IconFrame.Fill->SetContent(View.Icon);
	EXUi::AddH(Line, EXUi::Sized(Tree, 41.0f, 41.0f, IconFrame.Root), FMargin(0.0f, 0.0f, 12.0f, 0.0f));
	UVerticalBox* Text = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	View.Label = EXUi::WeightText(Tree, TEXT(""), 9, EXUi::Sand(), 700, 180);
	View.Title = EXUi::WeightText(Tree, TEXT(""), 13, EXUi::Bone(), 700);
	EXUi::AddV(Text, View.Label);
	EXUi::AddV(Text, View.Title, FMargin(0.0f, 2.0f, 0.0f, 0.0f));
	EXUi::AddH(Line, Text, FMargin(0.0f), true);
	View.Shield = EXUi::Image(Tree, EXUi::Icon(TEXT("fam_4")), EXUi::Ok());
	EXUi::AddH(Line, EXUi::Sized(Tree, 15.0f, 15.0f, View.Shield), FMargin(0.0f, 0.0f, 12.0f, 0.0f));
	const EXUi::FFrame Badge = EXUi::Frame(Tree, EXUi::Bone(0.25f), EXUi::Ink(0.0f), 1.0f, FMargin(6.0f, 1.0f, 6.0f, 1.0f));
	View.SizeText = EXUi::WeightText(Tree, TEXT(""), 9, EXUi::Sand(), 800);
	Badge.Fill->SetContent(View.SizeText);
	View.SizeBox = Badge.Root;
	EXUi::AddH(Line, Badge.Root);
	View.Frame = MakeLineFrame(Line, 3.0f, FMargin(17.0f, 9.0f, 12.0f, 9.0f), false);
	return View;
}

UEXHangarWidget::FItemView UEXHangarWidget::MakeItem(float Width)
{
	UWidgetTree* Tree = WidgetTree;
	FItemView View;
	UHorizontalBox* Outer = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	// The icon (caches, and modules in the shop and the vault lists).
	const EXUi::FFrame IconFrame = EXUi::Frame(Tree, EXUi::Bone(0.15f), EXUi::Ink(0.35f), 1.0f, FMargin(10.0f));
	View.Icon = EXUi::Image(Tree, nullptr, EXUi::Bone());
	IconFrame.Fill->SetContent(View.Icon);
	View.IconBox = EXUi::Sized(Tree, 48.0f, 48.0f, IconFrame.Root);
	EXUi::AddH(Outer, View.IconBox, FMargin(0.0f, 0.0f, 14.0f, 0.0f), false, VAlign_Top);
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	// Name, flame bar, tag ... rarity.
	UHorizontalBox* Head = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	View.Title = EXUi::WeightText(Tree, TEXT(""), 14, EXUi::Bone(), 800);
	EXUi::AddH(Head, View.Title);
	View.Flame = EXUi::Image(Tree, nullptr);
	View.FlameBox = EXUi::Sized(Tree, 55.0f, 11.0f, View.Flame);
	EXUi::AddH(Head, View.FlameBox, FMargin(10.0f, 0.0f, 0.0f, 0.0f));
	const EXUi::FFrame Tag = EXUi::Frame(Tree, EXUi::Sand(), EXUi::Ink(0.0f), 1.0f, FMargin(7.0f, 1.0f, 7.0f, 2.0f));
	View.Tag = EXUi::WeightText(Tree, TEXT(""), 8, EXUi::Sand(), 800, 160);
	Tag.Fill->SetContent(View.Tag);
	View.TagBox = Tag.Root;
	EXUi::AddH(Head, Tag.Root, FMargin(8.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddH(Head, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	View.Rarity = EXUi::WeightText(Tree, TEXT(""), 9, EXUi::Bone(), 800, 200);
	EXUi::AddH(Head, View.Rarity, FMargin(8.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddV(Column, Head);
	// Maker line ... value.
	UHorizontalBox* Second = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	View.Maker = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Sand(), 400);
	EXUi::AddH(Second, View.Maker, FMargin(0.0f), true);
	View.ValueBox = ValueWithGem(Tree, View.Value, 10, EXUi::Sand());
	EXUi::AddH(Second, View.ValueBox, FMargin(8.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddV(Column, Second, FMargin(0.0f, 3.0f, 0.0f, 0.0f));
	// The chips, wrapping.
	View.ChipBox = Tree->ConstructWidget<UWrapBox>(UWrapBox::StaticClass());
	View.ChipBox->SetInnerSlotPadding(FVector2D(6.0f, 6.0f));
	for (int32 Index = 0; Index < MaxChips; ++Index)
	{
		View.Chips[Index] = EXUi::Chip(Tree, 10);
		View.ChipBox->AddChildToWrapBox(View.Chips[Index].Root);
	}
	EXUi::AddV(Column, View.ChipBox, FMargin(0.0f, 8.0f, 0.0f, 0.0f));
	EXUi::AddH(Outer, Column, FMargin(0.0f), true);
	View.Frame = MakeLineFrame(EXUi::Sized(Tree, Width - 33.0f, 0.0f, Outer), 4.0f, FMargin(19.0f, 13.0f, 14.0f, 13.0f), true);
	return View;
}

UEXHangarWidget::FShipView UEXHangarWidget::MakeShip()
{
	UWidgetTree* Tree = WidgetTree;
	FShipView View;
	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	UVerticalBox* Text = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	View.Name = EXUi::TitleText(Tree, TEXT(""), 16, EXUi::Bone(), 80);
	View.Role = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Sand(), 600, 100);
	EXUi::AddV(Text, View.Name);
	EXUi::AddV(Text, View.Role, FMargin(0.0f, 4.0f, 0.0f, 0.0f));
	EXUi::AddH(Line, Text, FMargin(0.0f), true);
	// Lives (green) and stars (gold), as pips.
	UVerticalBox* Pips = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Pips, Diamonds(Tree, 6, 10.0f, 5.0f, View.Lives), FMargin(0.0f), HAlign_Right);
	EXUi::AddV(Pips, Diamonds(Tree, EXMeta::MaxStars, 7.0f, 5.0f, View.Stars), FMargin(0.0f, 9.0f, 0.0f, 0.0f), HAlign_Right);
	EXUi::AddH(Line, Pips, FMargin(10.0f, 2.0f, 0.0f, 0.0f), false, VAlign_Top);
	View.Frame = MakeLineFrame(Line, 5.0f, FMargin(22.0f, 14.0f, 17.0f, 14.0f), false);
	return View;
}

UEXHangarWidget::FTileView UEXHangarWidget::MakeTile(int32 Slot)
{
	UWidgetTree* Tree = WidgetTree;
	FTileView View;
	UOverlay* Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	View.Fill = EXUi::Box(Tree, EXUi::Bone(0.035f));
	EXUi::AddO(Root, View.Fill, HAlign_Fill, VAlign_Fill);
	// The key in a small box (top left) and the d-pad arrow (top right).
	const EXUi::FFrame Key = EXUi::Frame(Tree, EXUi::Bone(0.7f), EXUi::Ink(0.0f), 1.0f, FMargin(0.0f));
	UTextBlock* KeyText = EXUi::WeightText(Tree, FString::FromInt(Slot + 1), 10, EXUi::Bone(), 800);
	Key.Fill->SetContent(KeyText);
	Key.Fill->SetHorizontalAlignment(HAlign_Center);
	Key.Fill->SetVerticalAlignment(VAlign_Center);
	EXUi::AddO(Root, EXUi::Sized(Tree, 22.0f, 22.0f, Key.Root), HAlign_Left, VAlign_Top, FMargin(9.0f));
	EXUi::AddO(Root, EXUi::WeightText(Tree, QuickArrows[Slot], 10, EXUi::Rust(), 700), HAlign_Right, VAlign_Top, FMargin(0.0f, 8.0f, 10.0f, 0.0f));
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	View.Icon = EXUi::Image(Tree, nullptr);
	EXUi::AddV(Column, EXUi::Sized(Tree, 40.0f, 40.0f, View.Icon), FMargin(0.0f), HAlign_Center);
	View.Name = EXUi::WeightText(Tree, TEXT(""), 11, EXUi::Bone(), 700);
	EXUi::AddV(Column, View.Name, FMargin(0.0f, 9.0f, 0.0f, 0.0f), HAlign_Center);
	EXUi::AddV(Column, Diamonds(Tree, 2, 9.0f, 7.0f, View.Pips), FMargin(0.0f, 7.0f, 0.0f, 0.0f), HAlign_Center);
	EXUi::AddO(Root, Column, HAlign_Center, VAlign_Center, FMargin(0.0f, 14.0f, 0.0f, 0.0f));
	for (int32 Side = 0; Side < 4; ++Side)
	{
		View.Edges[Side] = EXUi::Box(Tree, EXUi::Bone(0.1f));
		const bool bHorizontal = Side < 2;
		EXUi::AddO(Root, EXUi::Sized(Tree, bHorizontal ? 0.0f : 1.0f, bHorizontal ? 1.0f : 0.0f, View.Edges[Side]),
			bHorizontal ? HAlign_Fill : (Side == 2 ? HAlign_Left : HAlign_Right), bHorizontal ? (Side == 0 ? VAlign_Top : VAlign_Bottom) : VAlign_Fill);
	}
	View.Root = EXUi::Sized(Tree, 142.0f, 142.0f, Root);
	return View;
}

UEXHangarWidget::FStockView UEXHangarWidget::MakeStock()
{
	UWidgetTree* Tree = WidgetTree;
	FStockView View;
	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	const EXUi::FFrame IconFrame = EXUi::Frame(Tree, EXUi::Bone(0.15f), EXUi::Ink(0.35f), 1.0f, FMargin(12.0f));
	View.Icon = EXUi::Image(Tree, nullptr);
	IconFrame.Fill->SetContent(View.Icon);
	EXUi::AddH(Line, EXUi::Sized(Tree, 53.0f, 53.0f, IconFrame.Root), FMargin(0.0f, 0.0f, 16.0f, 0.0f));
	UVerticalBox* Text = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	View.Name = EXUi::WeightText(Tree, TEXT(""), 14, EXUi::Bone(), 700);
	View.Effect = EXUi::WeightText(Tree, TEXT(""), 11, EXUi::Sand(), 400);
	View.Effect->SetAutoWrapText(true);
	EXUi::AddV(Text, View.Name);
	EXUi::AddV(Text, View.Effect, FMargin(0.0f, 3.0f, 0.0f, 0.0f));
	EXUi::AddH(Line, Text, FMargin(0.0f), true);
	UVerticalBox* Right = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Right, EXUi::WeightText(Tree, TEXT("no stock"), 10, EXUi::Sand(), 400), FMargin(0.0f), HAlign_Right);
	View.Count = EXUi::WeightText(Tree, TEXT(""), 14, EXUi::Bone(), 800);
	EXUi::AddV(Right, View.Count, FMargin(0.0f, 1.0f, 0.0f, 3.0f), HAlign_Right);
	// The buy button: the orange gradient, dark text, the gem.
	UOverlay* Button = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Button, EXUi::Box(Tree, EXUi::Rust()), HAlign_Fill, VAlign_Fill);
	if (UTexture2D* Gradient = EXUi::Icon(TEXT("ui_button")))
	{
		EXUi::AddO(Button, EXUi::Image(Tree, Gradient), HAlign_Fill, VAlign_Fill);
	}
	UHorizontalBox* Label = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	View.Button = EXUi::WeightText(Tree, TEXT(""), 9, EXUi::Hex(26, 11, 4), 800, 120);
	EXUi::AddH(Label, View.Button);
	EXUi::AddH(Label, EXUi::GemImage(Tree, 7.0f), FMargin(4.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddO(Button, Label, HAlign_Center, VAlign_Center, FMargin(9.0f, 3.0f, 9.0f, 3.0f));
	EXUi::AddV(Right, Button, FMargin(0.0f), HAlign_Right);
	EXUi::AddH(Line, Right, FMargin(12.0f, 0.0f, 0.0f, 0.0f));
	View.Frame = MakeLineFrame(Line, 0.0f, FMargin(14.0f, 12.0f, 14.0f, 12.0f), false);
	return View;
}

UEXHangarWidget::FInfoView UEXHangarWidget::MakeInfo()
{
	UWidgetTree* Tree = WidgetTree;
	FInfoView View;
	UVerticalBox* Text = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	View.Label = EXUi::WeightText(Tree, TEXT(""), 9, EXUi::Rust(), 700, 180);
	View.Title = EXUi::WeightText(Tree, TEXT(""), 14, EXUi::Bone(), 700);
	View.Sub = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Sand(), 400);
	View.Sub->SetAutoWrapText(true);
	EXUi::AddV(Text, View.Label);
	EXUi::AddV(Text, View.Title, FMargin(0.0f, 2.0f, 0.0f, 0.0f));
	EXUi::AddV(Text, View.Sub, FMargin(0.0f, 2.0f, 0.0f, 0.0f));
	View.Frame = MakeLineFrame(Text, 4.0f, FMargin(18.0f, 10.0f, 14.0f, 10.0f), false);
	return View;
}

UEXHangarWidget::FCardView UEXHangarWidget::MakeCard(float Width, float Height, float ArtHeight)
{
	UWidgetTree* Tree = WidgetTree;
	FCardView View;
	UOverlay* Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());

	// The back: rust stripes over a dark gradient, a glowing diamond with a question mark, "ESPAÇO".
	UOverlay* Back = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Back, EXUi::Box(Tree, EXUi::Hex(28, 16, 10, 0.98f)), HAlign_Fill, VAlign_Fill);
	EXUi::AddO(Back, EXUi::Tiled(Tree, TEXT("ui_stripes"), EXUi::Rust(0.08f), 24.0f), HAlign_Fill, VAlign_Fill);
	EXUi::AddO(Back, EXUi::Glow(Tree, EXUi::Rust(0.0f)), HAlign_Fill, VAlign_Fill);
	UVerticalBox* BackColumn = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UOverlay* Question = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Question, EXUi::Sized(Tree, 120.0f, 120.0f, EXUi::Image(Tree, EXUi::Icon(TEXT("ui_radial")), EXUi::Rust(0.45f))), HAlign_Center, VAlign_Center);
	USizeBox* Diamond = EXUi::Sized(Tree, 84.0f, 84.0f, EXUi::Box(Tree, EXUi::Rust(), FMargin(2.0f), EXUi::Box(Tree, EXUi::Hex(30, 17, 10))));
	Diamond->SetRenderTransformAngle(45.0f);
	EXUi::AddO(Question, Diamond, HAlign_Center, VAlign_Center);
	EXUi::AddO(Question, EXUi::WeightText(Tree, TEXT("?"), 27, EXUi::RustHot(), 900), HAlign_Center, VAlign_Center);
	EXUi::AddV(BackColumn, EXUi::Sized(Tree, 130.0f, 130.0f, Question), FMargin(0.0f), HAlign_Center);
	EXUi::AddV(BackColumn, EXUi::WeightText(Tree, TEXT("ESPAÇO"), 10, EXUi::Sand(), 700, 200), FMargin(0.0f, 6.0f, 0.0f, 0.0f), HAlign_Center);
	EXUi::AddO(Back, BackColumn, HAlign_Center, VAlign_Center);
	const EXUi::FFrame BackEdges = EXUi::Frame(Tree, EXUi::Rust(0.6f), EXUi::Ink(0.0f), 1.0f, FMargin(0.0f));
	EXUi::AddO(Back, BackEdges.Root, HAlign_Fill, VAlign_Fill);
	EXUi::AddO(Root, Back, HAlign_Fill, VAlign_Fill);

	// The front: the photo (or the icon glowing), the rarity line under it, then what it is.
	UOverlay* Front = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	Front->SetClipping(EWidgetClipping::ClipToBounds);
	EXUi::AddO(Front, EXUi::Box(Tree, EXUi::Hex(21, 15, 10, 0.97f)), HAlign_Fill, VAlign_Fill);
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UOverlay* Art = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Art, EXUi::Box(Tree, EXUi::Hex(17, 17, 17)), HAlign_Fill, VAlign_Fill);
	View.Photo = EXUi::Image(Tree, nullptr);
	EXUi::AddO(Art, View.Photo, HAlign_Fill, VAlign_Fill);
	View.Halo = EXUi::Image(Tree, EXUi::Icon(TEXT("ui_radial")), EXUi::Bone(0.3f));
	EXUi::AddO(Art, EXUi::Sized(Tree, ArtHeight, ArtHeight, View.Halo), HAlign_Center, VAlign_Center);
	View.Icon = EXUi::Image(Tree, nullptr);
	EXUi::AddO(Art, EXUi::Sized(Tree, 77.0f, 77.0f, View.Icon), HAlign_Center, VAlign_Center);
	View.Tag = EXUi::WeightText(Tree, TEXT(""), 9, EXUi::Bone(), 800, 160);
	EXUi::AddO(Art, EXUi::Box(Tree, EXUi::Hex(10, 7, 5, 0.75f), FMargin(7.0f, 2.0f, 7.0f, 2.0f), View.Tag), HAlign_Left, VAlign_Bottom, FMargin(8.0f));
	EXUi::AddV(Column, EXUi::Sized(Tree, 0.0f, ArtHeight, Art));
	View.ArtLine = EXUi::Box(Tree, EXUi::Rust());
	EXUi::AddV(Column, EXUi::Sized(Tree, 0.0f, 2.0f, View.ArtLine));
	UVerticalBox* Body = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	View.Rarity = EXUi::WeightText(Tree, TEXT(""), 9, EXUi::Bone(), 900, 200);
	View.Title = EXUi::WeightText(Tree, TEXT(""), 13, EXUi::Bone(), 700);
	View.Title->SetAutoWrapText(true);
	View.Maker = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Sand(), 400);
	View.Maker->SetAutoWrapText(true);
	EXUi::AddV(Body, View.Rarity);
	EXUi::AddV(Body, View.Title, FMargin(0.0f, 3.0f, 0.0f, 0.0f));
	EXUi::AddV(Body, View.Maker, FMargin(0.0f, 3.0f, 0.0f, 0.0f));
	View.ChipBox = Tree->ConstructWidget<UWrapBox>(UWrapBox::StaticClass());
	View.ChipBox->SetInnerSlotPadding(FVector2D(6.0f, 6.0f));
	for (int32 Index = 0; Index < MaxChips; ++Index)
	{
		View.Chips[Index] = EXUi::Chip(Tree, 9);
		View.ChipBox->AddChildToWrapBox(View.Chips[Index].Root);
	}
	EXUi::AddV(Body, View.ChipBox, FMargin(0.0f, 7.0f, 0.0f, 0.0f));
	EXUi::AddV(Column, EXUi::Box(Tree, EXUi::Ink(0.0f), FMargin(13.0f, 11.0f, 13.0f, 11.0f), Body));
	EXUi::AddO(Front, Column, HAlign_Fill, VAlign_Fill);
	EXUi::AddO(Front, ValueWithGem(Tree, View.Value, 10, EXUi::Sand()), HAlign_Right, VAlign_Bottom, FMargin(0.0f, 0.0f, 12.0f, 11.0f));
	// The rarity's glow inside the edges, the edges, the NOVO ribbon across the corner.
	View.GlowInner = EXUi::Sliced(Tree, TEXT("ui_inset"), EXUi::Bone(0.18f), 0.4f);
	EXUi::AddO(Front, View.GlowInner, HAlign_Fill, VAlign_Fill);
	const EXUi::FFrame Edges = EXUi::Frame(Tree, EXUi::Rust(), EXUi::Ink(0.0f), 1.0f, FMargin(0.0f));
	for (int32 Side = 0; Side < 4; ++Side)
	{
		View.Edges[Side] = Edges.Edges[Side];
	}
	EXUi::AddO(Front, Edges.Root, HAlign_Fill, VAlign_Fill);
	View.RibbonText = EXUi::WeightText(Tree, TEXT("NOVO"), 9, EXUi::Hex(20, 6, 31), 900, 200);
	View.RibbonFill = EXUi::Box(Tree, EXUi::Hex(181, 108, 255), FMargin(41.0f, 4.0f, 41.0f, 4.0f), View.RibbonText);
	View.Ribbon = View.RibbonFill;
	View.Ribbon->SetRenderTransformAngle(38.0f);
	EXUi::AddO(Front, View.Ribbon, HAlign_Right, VAlign_Top, FMargin(0.0f, 16.0f, -38.0f, 0.0f));
	EXUi::AddO(Root, Front, HAlign_Fill, VAlign_Fill);

	View.Front = Front;
	View.Back = Back;
	View.Root = EXUi::Sized(Tree, Width, Height, Root);
	return View;
}

UWidget* UEXHangarWidget::BuildSlotsPanel()
{
	UWidgetTree* Tree = WidgetTree;
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	SlotsTitle = EXUi::WeightText(Tree, TEXT("-"), 11, EXUi::Rust(), 700, 220);
	EXUi::AddV(Column, SlotsTitle, FMargin(0.0f, 0.0f, 0.0f, 12.0f));
	for (int32 Index = 0; Index < HangarSlotRows; ++Index)
	{
		FSlotView View = MakeSlot();
		EXUi::AddV(Column, EXUi::Sized(Tree, 0.0f, 60.0f, View.Frame.Root), FMargin(0.0f, 0.0f, 0.0f, 6.0f));
		SlotViews.Add(View);
	}
	UHorizontalBox* Foot = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Foot, EXUi::Sized(Tree, 13.0f, 13.0f, EXUi::Image(Tree, EXUi::Icon(TEXT("fam_4")), EXUi::Ok())), FMargin(2.0f, 0.0f, 8.0f, 0.0f));
	EXUi::AddH(Foot, EXUi::WeightText(Tree, TEXT("Seguro: nunca se perde (1 por expedição)"), 10, EXUi::Sand(), 400));
	EXUi::AddV(Column, Foot, FMargin(0.0f, 4.0f, 0.0f, 0.0f));
	return MakePanel(Column, 420.0f, false);
}

UWidget* UEXHangarWidget::BuildListPanel()
{
	UWidgetTree* Tree = WidgetTree;
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	ListTitle = EXUi::WeightText(Tree, TEXT("-"), 11, EXUi::Rust(), 700, 220);
	EXUi::AddV(Column, ListTitle, FMargin(0.0f, 0.0f, 0.0f, 12.0f));
	for (int32 Index = 0; Index < HangarShipRows; ++Index)
	{
		FShipView View = MakeShip();
		EXUi::AddV(Column, View.Frame.Root, FMargin(0.0f, 0.0f, 0.0f, 10.0f));
		ShipViews.Add(View);
	}
	for (int32 Index = 0; Index < HangarListRows; ++Index)
	{
		FItemView View = MakeItem(470.0f);
		EXUi::AddV(Column, View.Frame.Root, FMargin(0.0f, 0.0f, 0.0f, 8.0f));
		ListViews.Add(View);
	}
	ListMore = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Sand(), 700, 120);
	EXUi::AddV(Column, ListMore, FMargin(2.0f, 2.0f, 0.0f, 0.0f));
	return MakePanel(Column, 504.0f, false);
}

UWidget* UEXHangarWidget::BuildQuickPanel()
{
	// The four quick slots as the d-pad (mock-up consumiveis.png): 1 up, 3 left, 4 right, 2 down, the pad between them.
	UWidgetTree* Tree = WidgetTree;
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	QuickTitle = EXUi::WeightText(Tree, TEXT("-"), 11, EXUi::Rust(), 700, 220);
	EXUi::AddV(Column, QuickTitle, FMargin(0.0f, 0.0f, 0.0f, 14.0f));
	UCanvasPanel* Cross = Tree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass());
	const FVector2D Cells[EXMeta::QuickSlots] = { FVector2D(152.0f, 0.0f), FVector2D(152.0f, 304.0f), FVector2D(0.0f, 152.0f), FVector2D(304.0f, 152.0f) };
	for (int32 Slot = 0; Slot < EXMeta::QuickSlots; ++Slot)
	{
		FTileView View = MakeTile(Slot);
		UCanvasPanelSlot* CellSlot = Cross->AddChildToCanvas(View.Root);
		CellSlot->SetAutoSize(false);
		CellSlot->SetPosition(Cells[Slot]);
		CellSlot->SetSize(FVector2D(142.0f, 142.0f));
		TileViews.Add(View);
	}
	if (UTexture2D* Pad = EXUi::Icon(TEXT("ui_dpad")))
	{
		UCanvasPanelSlot* PadSlot = Cross->AddChildToCanvas(EXUi::Image(Tree, Pad));
		PadSlot->SetAutoSize(false);
		PadSlot->SetPosition(FVector2D(152.0f + 29.0f, 152.0f + 29.0f));
		PadSlot->SetSize(FVector2D(84.0f, 84.0f));
	}
	EXUi::AddV(Column, EXUi::Sized(Tree, 446.0f, 446.0f, Cross), FMargin(0.0f), HAlign_Center);
	// Teclado 1 2 3 4  ·  Comando ▲ ▼ ◀ ▶
	UHorizontalBox* Keys = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Keys, EXUi::WeightText(Tree, TEXT("Teclado"), 12, EXUi::Sand(), 400), FMargin(0.0f, 0.0f, 8.0f, 0.0f));
	for (int32 Slot = 0; Slot < EXMeta::QuickSlots; ++Slot)
	{
		EXUi::AddH(Keys, EXUi::KeyCap(Tree, FString::FromInt(Slot + 1)), FMargin(0.0f, 0.0f, 7.0f, 0.0f));
	}
	EXUi::AddH(Keys, EXUi::WeightText(Tree, TEXT("·  Comando"), 12, EXUi::Sand(), 400), FMargin(4.0f, 0.0f, 8.0f, 0.0f));
	for (int32 Slot = 0; Slot < EXMeta::QuickSlots; ++Slot)
	{
		EXUi::AddH(Keys, EXUi::KeyCap(Tree, QuickArrows[Slot]), FMargin(0.0f, 0.0f, 7.0f, 0.0f));
	}
	EXUi::AddV(Column, Keys, FMargin(0.0f, 14.0f, 0.0f, 4.0f), HAlign_Left);
	return MakePanel(Column, 504.0f, false);
}

UWidget* UEXHangarWidget::BuildCandidatesPanel()
{
	UWidgetTree* Tree = WidgetTree;
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	CandidatesTitle = EXUi::WeightText(Tree, TEXT("-"), 11, EXUi::Rust(), 700, 220);
	EXUi::AddV(Column, CandidatesTitle, FMargin(0.0f, 0.0f, 0.0f, 12.0f));
	for (int32 Index = 0; Index < HangarCandidateRows; ++Index)
	{
		FItemView View = MakeItem(436.0f);
		View.IconBox->SetVisibility(ESlateVisibility::Collapsed);
		EXUi::AddV(Column, View.Frame.Root, FMargin(0.0f, 0.0f, 0.0f, 8.0f));
		CandidateViews.Add(View);
	}
	CandidatesMore = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Sand(), 700, 120);
	EXUi::AddV(Column, CandidatesMore, FMargin(2.0f, 2.0f, 0.0f, 0.0f));
	return MakePanel(Column, 470.0f, false);
}

UWidget* UEXHangarWidget::BuildStockPanel()
{
	UWidgetTree* Tree = WidgetTree;
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	StockTitle = EXUi::WeightText(Tree, TEXT("-"), 11, EXUi::Rust(), 700, 220);
	EXUi::AddV(Column, StockTitle, FMargin(0.0f, 0.0f, 0.0f, 12.0f));
	for (int32 Index = 0; Index < HangarStockRows; ++Index)
	{
		FStockView View = MakeStock();
		EXUi::AddV(Column, View.Frame.Root, FMargin(0.0f, 0.0f, 0.0f, 7.0f));
		StockViews.Add(View);
	}
	return MakePanel(Column, 504.0f, false);
}

UWidget* UEXHangarWidget::BuildInfoPanel()
{
	UWidgetTree* Tree = WidgetTree;
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	InfoTitle = EXUi::WeightText(Tree, TEXT("-"), 11, EXUi::Rust(), 700, 220);
	EXUi::AddV(Column, InfoTitle, FMargin(0.0f, 0.0f, 0.0f, 12.0f));
	// The module looked at in the shop or the vault, as a card with the photo of the ship wearing it.
	LookedCard = MakeCard(CardW * 1.2f, CardH * 1.2f, CardArt * 1.2f);
	LookedCard.Back->SetVisibility(ESlateVisibility::Collapsed);
	EXUi::AddV(Column, LookedCard.Root, FMargin(0.0f, 0.0f, 0.0f, 12.0f), HAlign_Center);
	for (int32 Index = 0; Index < HangarInfoRows; ++Index)
	{
		FInfoView View = MakeInfo();
		EXUi::AddV(Column, View.Frame.Root, FMargin(0.0f, 0.0f, 0.0f, 6.0f));
		InfoViews.Add(View);
	}
	InfoDetail = EXUi::WeightText(Tree, TEXT(""), 11, EXUi::Bone(0.85f), 400);
	InfoDetail->SetAutoWrapText(true);
	EXUi::AddV(Column, EXUi::Sized(Tree, 436.0f, 0.0f, InfoDetail), FMargin(0.0f, 6.0f, 0.0f, 0.0f));
	return MakePanel(Column, 470.0f, true);
}

UWidget* UEXHangarWidget::BuildStats()
{
	UWidgetTree* Tree = WidgetTree;
	const EXUi::FFrame Panel = EXUi::Frame(Tree, EXUi::Bone(0.09f), PlateFill(), 1.0f, FMargin(17.0f, 14.0f, 17.0f, 12.0f));
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	Panel.Fill->SetContent(Column);
	for (int32 RowIndex = 0; RowIndex < 2; ++RowIndex)
	{
		UHorizontalBox* Cells = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		for (int32 Cell = 0; Cell < 4; ++Cell)
		{
			const int32 Stat = RowIndex * 4 + Cell;
			FStatView View;
			UVerticalBox* Box = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
			EXUi::AddV(Box, EXUi::WeightText(Tree, HangarStatNames[Stat], 9, EXUi::Sand(), 700, 160));
			UHorizontalBox* Numbers = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
			View.Value = EXUi::WeightText(Tree, TEXT("-"), 14, EXUi::Bone(), 800);
			View.Delta = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Ok(), 800);
			EXUi::AddH(Numbers, View.Value);
			EXUi::AddH(Numbers, View.Delta, FMargin(7.0f, 0.0f, 0.0f, 0.0f));
			EXUi::AddV(Box, Numbers, FMargin(0.0f, 1.0f, 0.0f, 5.0f));
			UOverlay* Track = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
			EXUi::AddO(Track, EXUi::Sized(Tree, HangarStatBarWidth, 6.0f, EXUi::Box(Tree, EXUi::Bone(0.08f))), HAlign_Left, VAlign_Center);
			UHorizontalBox* Bar = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
			View.Fill = EXUi::Sized(Tree, 10.0f, 6.0f, EXUi::Box(Tree, EXUi::Rust()));
			View.ChangeColour = EXUi::Box(Tree, EXUi::Ok());
			View.Change = EXUi::Sized(Tree, 0.0f, 6.0f, View.ChangeColour);
			EXUi::AddH(Bar, View.Fill);
			EXUi::AddH(Bar, View.Change);
			EXUi::AddO(Track, Bar, HAlign_Left, VAlign_Center);
			EXUi::AddV(Box, Track);
			EXUi::AddH(Cells, EXUi::Sized(Tree, 206.0f, 56.0f, Box), FMargin(0.0f, 0.0f, Cell < 3 ? 12.0f : 0.0f, 0.0f));
			StatViews.Add(View);
		}
		EXUi::AddV(Column, Cells, FMargin(0.0f, 0.0f, 0.0f, RowIndex == 0 ? 8.0f : 0.0f));
	}
	LivesText = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Ok(), 800, 100);
	EXUi::AddV(Column, LivesText, FMargin(0.0f, 4.0f, 0.0f, 0.0f));
	return Panel.Root;
}

UWidget* UEXHangarWidget::BuildAction()
{
	// LANÇAR EXPEDIÇÃO (NAVE) or MONTAR (EQUIPAR): the orange button with its glow and the ENTER key.
	UWidgetTree* Tree = WidgetTree;
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	ModeText = EXUi::OutlinedText(Tree, TEXT(""), 11, EXUi::Bone(), 140, 1, EXUi::Ink(0.6f));
	EXUi::AddV(Column, ModeText, FMargin(0.0f, 0.0f, 22.0f, 0.0f), HAlign_Right);
	UHorizontalBox* Content = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Content, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	ActionText = EXUi::TitleText(Tree, TEXT("MONTAR"), 14, EXUi::Hex(26, 11, 4), 200);
	EXUi::AddH(Content, ActionText);
	const EXUi::FFrame Key = EXUi::Frame(Tree, EXUi::Hex(26, 11, 4), EXUi::Ink(0.0f), 1.0f, FMargin(7.0f, 2.0f, 7.0f, 2.0f));
	Key.Fill->SetContent(EXUi::WeightText(Tree, TEXT("ENTER"), 10, EXUi::Hex(26, 11, 4), 800, 100));
	EXUi::AddH(Content, Key.Root, FMargin(14.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddH(Content, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	EXUi::AddV(Column, EXUi::OrangeButton(Tree, Content, FMargin(0.0f), 470.0f, 62.0f));
	return Column;
}

UWidget* UEXHangarWidget::BuildQuickSummary()
{
	UWidgetTree* Tree = WidgetTree;
	QuickSummaryText = EXUi::WeightText(Tree, TEXT(""), 12, EXUi::Bone(0.9f), 400);
	QuickSummaryText->SetAutoWrapText(true);
	const EXUi::FFrame Panel = EXUi::Frame(Tree, EXUi::Bone(0.09f), PlateFill(), 1.0f, FMargin(22.0f, 14.0f, 22.0f, 14.0f));
	Panel.Fill->SetContent(QuickSummaryText);
	return EXUi::Sized(Tree, 756.0f, 0.0f, Panel.Root);
}

UWidget* UEXHangarWidget::BuildPreviewLabel()
{
	// "◆ PRÉ-VISUALIZAÇÃO · WRAITH GLIDE" under the ship, in the piece's rarity colour.
	UWidgetTree* Tree = WidgetTree;
	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	PreviewDiamond = EXUi::Box(Tree, EXUi::Hex(181, 108, 255));
	USizeBox* Diamond = EXUi::Sized(Tree, 11.0f, 11.0f, PreviewDiamond);
	Diamond->SetRenderTransformAngle(45.0f);
	EXUi::AddH(Line, Diamond, FMargin(0.0f, 0.0f, 11.0f, 0.0f));
	PreviewText = EXUi::WeightText(Tree, TEXT(""), 11, EXUi::Bone(), 800, 140);
	EXUi::AddH(Line, PreviewText);
	const EXUi::FFrame Frame = EXUi::Frame(Tree, EXUi::Hex(181, 108, 255), EXUi::Hex(10, 7, 5, 0.78f), 1.0f, FMargin(14.0f, 8.0f, 16.0f, 8.0f));
	Frame.Fill->SetContent(Line);
	for (int32 Side = 0; Side < 4; ++Side)
	{
		PreviewEdges[Side] = Frame.Edges[Side];
	}
	return Frame.Root;
}

UWidget* UEXHangarWidget::BuildCacheOverlay()
{
	// The opened cache (mock-up cofre.png): the workshop dimmed under a purple-dark vignette, the title, ten cards and the
	// summary with its two buttons.
	UWidgetTree* Tree = WidgetTree;
	UOverlay* Layer = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Layer, EXUi::Box(Tree, EXUi::Hex(30, 14, 40, 0.55f)), HAlign_Fill, VAlign_Fill);
	EXUi::AddO(Layer, EXUi::Sliced(Tree, TEXT("ui_vignette"), EXUi::Hex(5, 3, 2, 0.9f), 0.0f), HAlign_Fill, VAlign_Fill);
	UVerticalBox* Header = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	CacheTitle = EXUi::TitleText(Tree, TEXT("-"), 31, EXUi::Bone(), 140);
	EXUi::AddV(Header, CacheTitle, FMargin(0.0f), HAlign_Center);
	CacheSummary = EXUi::WeightText(Tree, TEXT(""), 12, EXUi::Sand(), 600, 120);
	EXUi::AddV(Header, CacheSummary, FMargin(0.0f, 7.0f, 0.0f, 0.0f), HAlign_Center);
	EXUi::AddO(Layer, Header, HAlign_Center, VAlign_Top, FMargin(0.0f, 101.0f, 0.0f, 0.0f));

	UCanvasPanel* Grid = Tree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass());
	for (int32 Index = 0; Index < HangarCards; ++Index)
	{
		FCardView View = MakeCard(CardW, CardH, CardArt);
		const FVector2D Home(CardGlow + (Index % 5) * (CardW + CardGap), CardGlow + CardRaise + (Index / 5) * (CardH + CardGap));
		View.GlowOuter = EXUi::Glow(Tree, EXUi::Rust(0.45f));
		View.GlowSlot = Grid->AddChildToCanvas(View.GlowOuter);
		View.GlowSlot->SetAutoSize(false);
		View.GlowSlot->SetZOrder(0);
		View.Slot = Grid->AddChildToCanvas(View.Root);
		View.Slot->SetAutoSize(false);
		View.Slot->SetZOrder(1);
		View.Slot->SetSize(FVector2D(CardW, CardH));
		View.Home = Home;
		CardViews.Add(View);
	}
	EXUi::AddO(Layer, EXUi::Sized(Tree, GridW, GridH, Grid), HAlign_Center, VAlign_Top, FMargin(0.0f, 214.0f - CardGlow - CardRaise, 0.0f, 0.0f));

	// "Até agora: 14 140 ✦ · custou 6 000 ✦"   [VENDER COMUNS (25%)] [GUARDAR TUDO]
	UHorizontalBox* Sum = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Sum, EXUi::WeightText(Tree, TEXT("Até agora: "), 12, EXUi::Sand(), 400));
	CacheSoFar = EXUi::WeightText(Tree, TEXT("0"), 14, EXUi::Bone(), 800);
	EXUi::AddH(Sum, CacheSoFar);
	EXUi::AddH(Sum, EXUi::GemImage(Tree, 10.0f), FMargin(5.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddH(Sum, EXUi::WeightText(Tree, TEXT("  ·  custou "), 12, EXUi::Sand(), 400));
	CacheCost = EXUi::WeightText(Tree, TEXT("0"), 12, EXUi::Sand(), 400);
	EXUi::AddH(Sum, CacheCost);
	EXUi::AddH(Sum, EXUi::GemImage(Tree, 9.0f), FMargin(5.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddH(Sum, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	UHorizontalBox* Buttons = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	const EXUi::FFrame Sell = EXUi::Frame(Tree, EXUi::Rust(), EXUi::Ink(0.0f), 1.0f, FMargin(22.0f, 12.0f, 22.0f, 12.0f));
	Sell.Fill->SetContent(EXUi::WeightText(Tree, TEXT("VENDER COMUNS (25%)"), 11, EXUi::Bone(), 900, 160));
	EXUi::AddH(Buttons, Sell.Root, FMargin(0.0f, 0.0f, 12.0f, 0.0f));
	UOverlay* Keep = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Keep, EXUi::Box(Tree, EXUi::Rust()), HAlign_Fill, VAlign_Fill);
	if (UTexture2D* Gradient = EXUi::Icon(TEXT("ui_button")))
	{
		EXUi::AddO(Keep, EXUi::Image(Tree, Gradient), HAlign_Fill, VAlign_Fill);
	}
	EXUi::AddO(Keep, EXUi::WeightText(Tree, TEXT("GUARDAR TUDO"), 11, EXUi::Hex(26, 11, 4), 900, 160), HAlign_Center, VAlign_Center,
		FMargin(22.0f, 12.0f, 22.0f, 12.0f));
	EXUi::AddH(Buttons, Keep);
	CacheButtons = Buttons;
	EXUi::AddH(Sum, Buttons);
	const EXUi::FFrame SumPanel = EXUi::Frame(Tree, EXUi::Bone(0.09f), PlateFill(), 1.0f, FMargin(22.0f, 14.0f, 22.0f, 14.0f));
	SumPanel.Fill->SetContent(Sum);
	EXUi::AddO(Layer, EXUi::Sized(Tree, GridW - CardGlow * 2.0f, 0.0f, SumPanel.Root), HAlign_Center, VAlign_Top, FMargin(0.0f, 924.0f, 0.0f, 0.0f));
	Layer->SetVisibility(ESlateVisibility::Collapsed);
	return Layer;
}

// ------------------------------------------------------------------------------------------------------------ showing

void UEXHangarWidget::ShowSlot(const FSlotView& View, const FEXHangarRow* Row, bool bSelected) const
{
	if (!Row)
	{
		View.Frame.Root->SetVisibility(ESlateVisibility::Collapsed);
		return;
	}
	View.Frame.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
	ShowLineFrame(View.Frame, Row->Colour, bSelected, EXUi::Rust());
	EXUi::SetImage(View.Icon, EXUi::Icon(Row->Icon), bSelected ? EXUi::RustHot() : EXUi::Bone(0.85f));
	EXUi::SetText(View.Label, Row->Label);
	EXUi::SetText(View.Title, Row->Title);
	View.Title->SetColorAndOpacity(FSlateColor(Row->bDim ? EXUi::Dim() : (Row->Colour.R + Row->Colour.G + Row->Colour.B < 1.4f ? EXUi::Bone(0.8f) : Row->Colour)));
	EXUi::SetText(View.SizeText, Row->Size);
	View.SizeBox->SetVisibility(Row->Size.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
	View.Shield->SetVisibility(Row->bInsured && EXUi::Icon(TEXT("fam_4")) ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Hidden);
	View.Frame.Root->SetRenderOpacity(Row->bDim && !bSelected ? 0.55f : 1.0f);
}

void UEXHangarWidget::ShowItem(const FItemView& View, const FEXHangarRow* Row, bool bSelected) const
{
	if (!Row)
	{
		View.Frame.Root->SetVisibility(ESlateVisibility::Collapsed);
		return;
	}
	View.Frame.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
	ShowLineFrame(View.Frame, Row->Colour, bSelected, Row->Colour);
	if (View.IconBox->GetVisibility() != ESlateVisibility::Collapsed || !Row->Icon.IsEmpty())
	{
		UTexture2D* IconTexture = EXUi::Icon(Row->Icon);
		EXUi::SetImage(View.Icon, IconTexture, Row->Value >= 0 && Row->Chips.Num() == 0 ? EXUi::RustHot() : Row->Colour);
	}
	EXUi::SetText(View.Title, Row->Title);
	UTexture2D* FlameTexture = Row->Flame >= 0 ? EXUi::Icon(FString::Printf(TEXT("flame_%d"), Row->Flame)) : nullptr;
	EXUi::SetImage(View.Flame, FlameTexture);
	View.FlameBox->SetVisibility(FlameTexture ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	EXUi::SetText(View.Tag, Row->Tag);
	View.TagBox->SetVisibility(Row->Tag.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
	EXUi::SetText(View.Rarity, Row->Rarity);
	View.Rarity->SetColorAndOpacity(FSlateColor(Row->Colour));
	EXUi::SetText(View.Maker, Row->Maker.IsEmpty() ? Row->Sub : Row->Maker);
	const FString Value = ValueText(*Row);
	EXUi::SetText(View.Value, Value);
	View.ValueBox->SetVisibility(Value.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
	for (int32 Index = 0; Index < MaxChips; ++Index)
	{
		EXUi::SetChip(View.Chips[Index], Row->Chips.IsValidIndex(Index) ? Row->Chips[Index].Text : FString(),
			Row->Chips.IsValidIndex(Index) ? Row->Chips[Index].Sign : 0);
	}
	View.ChipBox->SetVisibility(Row->Chips.Num() > 0 ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	View.Frame.Root->SetRenderOpacity(Row->bDim && !bSelected ? 0.55f : 1.0f);
}

void UEXHangarWidget::ShowShip(const FShipView& View, const FEXHangarRow* Row, bool bSelected) const
{
	if (!Row)
	{
		View.Frame.Root->SetVisibility(ESlateVisibility::Collapsed);
		return;
	}
	View.Frame.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
	ShowLineFrame(View.Frame, bSelected ? EXUi::Rust() : EXUi::Rust(0.0f), bSelected, EXUi::Rust());
	View.Frame.Fill->SetBrushColor(bSelected ? EXUi::Hex(38, 18, 9, 0.9f) : EXUi::Hex(20, 13, 9, 0.62f));
	EXUi::SetText(View.Name, Row->Title);
	EXUi::SetText(View.Role, Row->Label);
	for (int32 Index = 0; Index < 6; ++Index)
	{
		View.Lives[Index]->SetBrushColor(Index < Row->Lives ? EXUi::Ok() : EXUi::Bone(0.12f));
		View.Lives[Index]->GetParent()->SetVisibility(Index < FMath::Max(Row->Lives, 5) ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	}
	for (int32 Index = 0; Index < EXMeta::MaxStars; ++Index)
	{
		View.Stars[Index]->SetBrushColor(Index < Row->Stars ? Gold() : EXUi::Bone(0.1f));
	}
}

void UEXHangarWidget::ShowStock(const FStockView& View, const FEXHangarRow* Row, bool bSelected) const
{
	if (!Row)
	{
		View.Frame.Root->SetVisibility(ESlateVisibility::Collapsed);
		return;
	}
	View.Frame.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
	ShowLineFrame(View.Frame, Row->Colour, bSelected, EXUi::Rust());
	EXUi::SetImage(View.Icon, EXUi::Icon(Row->Icon), Row->Colour);
	EXUi::SetText(View.Name, Row->Title);
	EXUi::SetText(View.Effect, Row->Maker);
	EXUi::SetText(View.Count, FString::Printf(TEXT("×%d"), FMath::Max(0, Row->Count)));
	EXUi::SetText(View.Button, Row->Button);
}

void UEXHangarWidget::ShowInfo(const FInfoView& View, const FEXHangarRow* Row) const
{
	if (!Row)
	{
		View.Frame.Root->SetVisibility(ESlateVisibility::Collapsed);
		return;
	}
	View.Frame.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
	ShowLineFrame(View.Frame, Row->Colour, false, EXUi::Rust());
	EXUi::SetText(View.Label, Row->Label);
	View.Label->SetColorAndOpacity(FSlateColor(Row->Colour));
	EXUi::SetText(View.Title, Row->Title);
	EXUi::SetText(View.Sub, Row->Sub);
	View.Sub->SetVisibility(Row->Sub.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
}

void UEXHangarWidget::ShowCard(const FCardView& View, const FEXHangarRow* Card, bool bTurned, bool bInGrid) const
{
	if (!Card)
	{
		View.Root->SetVisibility(ESlateVisibility::Collapsed);
		if (View.GlowOuter)
		{
			View.GlowOuter->SetVisibility(ESlateVisibility::Collapsed);
		}
		return;
	}
	View.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
	View.Front->SetVisibility(bTurned ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Hidden);
	View.Back->SetVisibility(bTurned || !bInGrid ? ESlateVisibility::Hidden : ESlateVisibility::HitTestInvisible);
	const FLinearColor Colour = Card->Colour;
	const bool bShine = bTurned && Card->bNew;
	// Epic and better (and a ship copy) rise, grow a little and glow stronger (.cd.ep in the mock-up).
	if (bInGrid && View.Slot && View.GlowSlot && View.GlowOuter)
	{
		const FVector2D At = View.Home - FVector2D(0.0f, bShine ? CardRaise : 0.0f);
		View.Slot->SetPosition(At);
		const float Spread = bShine ? CardGlow * 1.6f : CardGlow;
		View.GlowSlot->SetPosition(At - FVector2D(Spread, Spread));
		View.GlowSlot->SetSize(FVector2D(CardW + Spread * 2.0f, CardH + Spread * 2.0f));
		View.GlowOuter->SetColorAndOpacity(bTurned ? WithAlpha(Colour, bShine ? 0.75f : 0.45f) : EXUi::Rust(0.3f));
		View.GlowOuter->SetVisibility(EXUi::Icon(TEXT("ui_glow")) ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
		View.Root->SetRenderScale(FVector2D(bShine ? 1.04f : 1.0f, bShine ? 1.04f : 1.0f));
	}
	if (!bTurned)
	{
		return;
	}
	for (UBorder* Edge : View.Edges)
	{
		Edge->SetBrushColor(Colour);
	}
	View.ArtLine->SetBrushColor(Colour);
	View.GlowInner->SetColorAndOpacity(WithAlpha(Colour, bShine ? 0.25f : 0.18f));
	// The photo of the ship wearing the module; without one, the icon glowing in the art box.
	UTexture2D* Photo = EXUi::Thumb(Card->Thumb);
	EXUi::SetImage(View.Photo, Photo);
	UTexture2D* IconTexture = Photo ? nullptr : EXUi::Icon(Card->Icon);
	const FLinearColor IconColour = Card->Maker.Equals(TEXT("Consumível")) ? EXMeta::Consumable(EEXConsumable::None).Colour : Colour;
	EXUi::SetImage(View.Icon, IconTexture, Card->Chips.Num() > 0 && Card->Chips[0].Sign < 0 && !Photo ? EXUi::Hex(106, 208, 255) : Colour);
	(void)IconColour;
	View.Halo->SetVisibility(IconTexture ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	View.Halo->SetColorAndOpacity(WithAlpha(Colour, 0.35f));
	EXUi::SetText(View.Rarity, Card->Rarity.IsEmpty() ? Card->Label : Card->Rarity);
	View.Rarity->SetColorAndOpacity(FSlateColor(Colour));
	EXUi::SetText(View.Title, Card->Title);
	EXUi::SetText(View.Maker, Card->Maker);
	for (int32 Index = 0; Index < MaxChips; ++Index)
	{
		EXUi::SetChip(View.Chips[Index], Card->Chips.IsValidIndex(Index) ? Card->Chips[Index].Text : FString(),
			Card->Chips.IsValidIndex(Index) ? Card->Chips[Index].Sign : 0);
	}
	EXUi::SetText(View.Value, Card->Value >= 0 ? EXUi::Thousands(Card->Value) : FString());
	View.Value->GetParent()->SetVisibility(Card->Value >= 0 ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	View.Ribbon->SetVisibility(bShine ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	View.RibbonFill->SetBrushColor(Colour);
	EXUi::SetText(View.RibbonText, Card->Tag.IsEmpty() || Card->Tag.Equals(TEXT("NOVO")) ? FString(TEXT("NOVO")) : Card->Tag);
	EXUi::SetText(View.Tag, Card->bNew ? FString() : Card->Tag);
	View.Tag->GetParent()->SetVisibility(Card->bNew || Card->Tag.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
	View.Front->SetRenderOpacity(Card->bDim ? 0.45f : 1.0f);
}

void UEXHangarWidget::Refresh()
{
	AEXHoverCraft* Craft = GetPlayerCraft();
	const UEXHangarModel* Model = Craft ? Craft->GetHangarModel() : nullptr;
	if (!Model)
	{
		return;
	}
	const UEXProfileSave* Profile = Model->GetProfile();
	const FString ShipName = Model->GetShipName();
	const EEXHangarTab Tab = Model->GetTab();
	EXUi::SetText(WalletText, EXUi::Thousands(Profile ? Profile->Stardust : 0));
	for (int32 Index = 0; Index < TabFills.Num(); ++Index)
	{
		const bool bOn = Index == static_cast<int32>(Tab);
		TabFills[Index]->SetBrushColor(bOn ? EXUi::Rust(0.22f) : EXUi::Hex(10, 7, 5, 0.35f));
		TabTexts[Index]->SetColorAndOpacity(FSlateColor(bOn ? EXUi::Bone() : EXUi::Sand()));
		for (int32 Side = 0; Side < 4 && TabEdges.IsValidIndex(Index * 4 + Side); ++Side)
		{
			TabEdges[Index * 4 + Side]->SetBrushColor(bOn ? EXUi::Rust() : EXUi::Bone(0.15f));
		}
	}

	// Which panels each tab has.
	const bool bShip = Tab == EEXHangarTab::Ship;
	const bool bEquip = Tab == EEXHangarTab::Equip;
	const bool bQuick = Tab == EEXHangarTab::Quick;
	const bool bList = Tab == EEXHangarTab::Shop || Tab == EEXHangarTab::Vault;
	auto Show = [](UWidget* Widget, bool bOn)
	{
		if (Widget)
		{
			Widget->SetVisibility(bOn ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
		}
	};
	Show(ShipTitleBox, bShip);
	Show(SlotsPanel, bEquip);
	Show(ListPanel, bShip || bList);
	Show(QuickPanel, bQuick);
	Show(CandidatesPanel, bEquip);
	Show(StockPanel, bQuick);
	Show(InfoPanel, bShip || bList);
	Show(ActionPanel, bShip || bEquip);
	Show(QuickSummaryPanel, bQuick);

	// The ship's name, line and stars over the turntable.
	if (bShip)
	{
		EXUi::SetText(ShipTitle, ShipName);
		EXUi::SetText(ShipSubtitle, UEXHangarModel::ShipSubtitle(ShipName));
		const int32 Stars = Profile ? Profile->StarsOf(ShipName) : 0;
		for (int32 Index = 0; Index < EXMeta::MaxStars; ++Index)
		{
			ShipStarPips[Index]->SetBrushColor(Index < Stars ? Gold() : EXUi::Hex(29, 20, 14, 0.18f));
		}
		EXUi::SetText(ShipStarText, FString::Printf(TEXT("%d/%d ESTRELAS"), Stars, EXMeta::MaxStars));
	}

	// Left.
	FString Title;
	TArray<FEXHangarRow> Rows;
	int32 Selected = 0;
	Model->BuildLeft(Title, Rows, Selected);
	if (bEquip)
	{
		EXUi::SetText(SlotsTitle, Title);
		for (int32 Index = 0; Index < SlotViews.Num(); ++Index)
		{
			ShowSlot(SlotViews[Index], Rows.IsValidIndex(Index) ? &Rows[Index] : nullptr, Index == Selected);
		}
	}
	else if (bShip || bList)
	{
		EXUi::SetText(ListTitle, Title);
		for (int32 Index = 0; Index < ShipViews.Num(); ++Index)
		{
			ShowShip(ShipViews[Index], bShip && Rows.IsValidIndex(Index) ? &Rows[Index] : nullptr, Index == Selected);
		}
		const int32 First = FMath::Clamp(Selected - HangarListRows / 2, 0, FMath::Max(0, Rows.Num() - HangarListRows));
		for (int32 Index = 0; Index < ListViews.Num(); ++Index)
		{
			const int32 RowIndex = First + Index;
			ShowItem(ListViews[Index], bList && Rows.IsValidIndex(RowIndex) ? &Rows[RowIndex] : nullptr, RowIndex == Selected);
		}
		EXUi::SetText(ListMore, bList && Rows.Num() > HangarListRows ? FString::Printf(TEXT("%d / %d"), Selected + 1, Rows.Num()) : FString());
	}
	else if (bQuick)
	{
		EXUi::SetText(QuickTitle, Title);
		for (int32 Index = 0; Index < TileViews.Num(); ++Index)
		{
			const FTileView& View = TileViews[Index];
			const FEXHangarRow* Row = Rows.IsValidIndex(Index) ? &Rows[Index] : nullptr;
			const bool bOn = Index == Selected;
			View.Fill->SetBrushColor(bOn ? EXUi::Rust(0.14f) : EXUi::Bone(0.035f));
			for (UBorder* Edge : View.Edges)
			{
				Edge->SetBrushColor(bOn ? EXUi::Rust(0.85f) : EXUi::Bone(0.1f));
			}
			EXUi::SetImage(View.Icon, Row ? EXUi::Icon(Row->Icon) : nullptr, Row ? Row->Colour : EXUi::Bone());
			EXUi::SetText(View.Name, Row ? Row->Title : FString());
			for (int32 Pip = 0; Pip < 2; ++Pip)
			{
				View.Pips[Pip]->SetBrushColor(Row && Pip < Row->Count ? EXUi::Rust() : EXUi::Bone(0.15f));
			}
		}
	}

	// Right.
	FString Detail;
	Model->BuildRight(Title, Rows, Selected, Detail);
	if (bEquip)
	{
		EXUi::SetText(CandidatesTitle, Title);
		const int32 First = Selected >= 0 ? FMath::Clamp(Selected - HangarCandidateRows / 2, 0, FMath::Max(0, Rows.Num() - HangarCandidateRows)) : 0;
		for (int32 Index = 0; Index < CandidateViews.Num(); ++Index)
		{
			const int32 RowIndex = First + Index;
			ShowItem(CandidateViews[Index], Rows.IsValidIndex(RowIndex) ? &Rows[RowIndex] : nullptr, RowIndex == Selected);
		}
		EXUi::SetText(CandidatesMore, Rows.Num() > HangarCandidateRows ? FString::Printf(TEXT("%d / %d"), Selected + 1, Rows.Num()) : FString());
	}
	else if (bQuick)
	{
		EXUi::SetText(StockTitle, Title);
		for (int32 Index = 0; Index < StockViews.Num(); ++Index)
		{
			ShowStock(StockViews[Index], Rows.IsValidIndex(Index) ? &Rows[Index] : nullptr, Index == Selected);
		}
		EXUi::SetText(QuickSummaryText, Model->GetQuickSummary());
	}
	else if (bShip || bList)
	{
		EXUi::SetText(InfoTitle, Title);
		FEXHangarRow Card;
		const bool bCard = bList && Model->GetLookedCard(Card);
		ShowCard(LookedCard, bCard ? &Card : nullptr, true, false);
		for (int32 Index = 0; Index < InfoViews.Num(); ++Index)
		{
			// With the card shown, its stats are on it: only the caches' odds and the ship's lines stay as lines.
			ShowInfo(InfoViews[Index], !bCard && Rows.IsValidIndex(Index) ? &Rows[Index] : nullptr);
		}
		EXUi::SetText(InfoDetail, Detail);
	}

	// The stats (ship and equip tabs, and a module that fits in the shop or vault).
	int32 Now[EXMeta::StatCount];
	int32 Next[EXMeta::StatCount];
	int32 LivesNow = 0, LivesNext = 0;
	Model->GetStats(Now, Next, LivesNow, LivesNext);
	bool bChanges = false;
	for (int32 Stat = 0; Stat < EXMeta::CoreStats; ++Stat)
	{
		bChanges |= Now[Stat] != Next[Stat];
	}
	Show(StatsPanel, bShip || bEquip || (bList && bChanges));
	if (bShip || bEquip || bList)
	{
		for (int32 Stat = 0; Stat < StatViews.Num() && Stat < EXMeta::CoreStats; ++Stat)
		{
			const FStatView& View = StatViews[Stat];
			const int32 Delta = Next[Stat] - Now[Stat];
			EXUi::SetText(View.Value, Delta == 0 ? FString::FromInt(Now[Stat]) : FString::Printf(TEXT("%d → %d"), Now[Stat], Next[Stat]));
			EXUi::SetText(View.Delta, Delta == 0 ? FString() : FString::Printf(TEXT("%s%d"), Delta > 0 ? TEXT("▲") : TEXT("▼"), FMath::Abs(Delta)));
			View.Delta->SetColorAndOpacity(FSlateColor(Delta > 0 ? EXUi::Ok() : Bad()));
			View.Fill->SetWidthOverride(HangarStatBarWidth * FMath::Clamp(FMath::Min(Now[Stat], Next[Stat]) / 100.0f, 0.02f, 1.0f));
			View.Change->SetWidthOverride(HangarStatBarWidth * FMath::Abs(Delta) / 100.0f);
			View.ChangeColour->SetBrushColor(Delta > 0 ? EXUi::Ok() : WithAlpha(Bad(), 0.85f));
		}
		EXUi::SetText(LivesText, LivesNow == LivesNext ? FString::Printf(TEXT("%d VIDAS"), LivesNow)
			: FString::Printf(TEXT("%d VIDAS → %d VIDAS"), LivesNow, LivesNext));
	}

	// The orange button: launch from the ship tab, fit in the equip tab.
	EXUi::SetText(ActionText, bShip ? FString(TEXT("LANÇAR EXPEDIÇÃO")) : FString(TEXT("MONTAR")));
	const bool bSolo = RaceDirector && RaceDirector->GetLaunchMode() == EEXRaceMode::Solo;
	EXUi::SetText(ModeText, !bShip ? FString() : (bSolo ? FString(TEXT("EXPEDIÇÃO SOLO  ·  só tu")) : FString(TEXT("PELOTÃO 15  ·  16 naves"))));

	// Under the ship: the label and the notes pinned to the module.
	FLinearColor PreviewColour = EXUi::Sand();
	const FString Preview = Model->IsOpening() ? FString() : Model->GetPreviewLabel(PreviewColour);
	Show(PreviewPanel, bEquip && !Preview.IsEmpty());
	EXUi::SetText(PreviewText, Preview);
	PreviewDiamond->SetBrushColor(PreviewColour);
	for (UBorder* Edge : PreviewEdges)
	{
		Edge->SetBrushColor(PreviewColour);
	}
	RefreshCallouts(Model, Craft);

	const float NoticeAge = GetWorld() ? GetWorld()->GetTimeSeconds() - Model->GetNoticeTime() : 100.0f;
	EXUi::SetText(NoticeText, NoticeAge < 3.0f ? Model->GetNotice() : FString());
	NoticeText->SetRenderOpacity(FMath::Clamp((3.0f - NoticeAge) / 0.5f, 0.0f, 1.0f));

	RefreshCards(Model);
	RefreshHints(Model);
}

void UEXHangarWidget::RefreshCallouts(const UEXHangarModel* Model, AEXHoverCraft* Craft)
{
	const TArray<FEXHangarCallout> Callouts = Model->IsOpening() ? TArray<FEXHangarCallout>() : Model->GetCallouts();
	APlayerController* Player = GetOwningPlayer();
	const float Scale = FMath::Max(0.1f, UWidgetLayoutLibrary::GetViewportScale(this));
	for (int32 Index = 0; Index < CalloutViews.Num(); ++Index)
	{
		const FCalloutView& View = CalloutViews[Index];
		FVector World;
		FVector2D Screen;
		const bool bOn = Callouts.IsValidIndex(Index) && Craft && Player && Craft->GetModuleAnchor(Callouts[Index].Family, World)
			&& Player->ProjectWorldLocationToScreen(World, Screen, true);
		if (!bOn)
		{
			View.Root->SetVisibility(ESlateVisibility::Collapsed);
			continue;
		}
		View.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
		EXUi::SetText(View.Text, Callouts[Index].Text);
		View.Bar->SetBrushColor(Callouts[Index].Colour);
		// Beside the module, a little above it (the first note to the right, the second to the left).
		const FVector2D At = Screen / Scale + (Index == 0 ? FVector2D(28.0f, -44.0f) : FVector2D(-260.0f, -60.0f));
		View.Slot->SetPosition(At);
	}
}

void UEXHangarWidget::RefreshCards(const UEXHangarModel* Model)
{
	const bool bOpening = Model->IsOpening();
	CacheOverlay->SetVisibility(bOpening ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	if (!bOpening)
	{
		return;
	}
	const TArray<FEXHangarRow>& Cards = Model->GetCards();
	EXUi::SetText(CacheTitle, Model->GetCacheTitle());
	int32 Shown = 0;
	int32 SoFar = 0;
	for (int32 Index = 0; Index < CardViews.Num(); ++Index)
	{
		const bool bTurned = Index < Model->GetRevealed();
		const FEXHangarRow* Card = Cards.IsValidIndex(Index) ? &Cards[Index] : nullptr;
		ShowCard(CardViews[Index], Card, bTurned, true);
		if (Card && bTurned)
		{
			++Shown;
			SoFar += FMath::Max(0, Card->Value);
		}
	}
	EXUi::SetText(CacheSummary, FString::Printf(TEXT("%d ITENS  ·  %d / %d REVELADOS"), Cards.Num(), Shown, Cards.Num()));
	EXUi::SetText(CacheSoFar, EXUi::Thousands(SoFar));
	EXUi::SetText(CacheCost, EXUi::Thousands(Model->GetCachePrice()));
	CacheButtons->SetRenderOpacity(Shown >= Cards.Num() ? 1.0f : 0.45f);
}

void UEXHangarWidget::RefreshHints(const UEXHangarModel* Model)
{
	const TArray<FEXHangarHint> Hints = Model->GetHints();
	FString Signature;
	for (const FEXHangarHint& Hint : Hints)
	{
		Signature += FString::Join(Hint.Keys, TEXT("+")) + TEXT(":") + Hint.Label + TEXT("|");
	}
	if (Signature == ShownHints || !KeyBar)
	{
		return;
	}
	ShownHints = Signature;
	KeyBar->ClearChildren();
	for (int32 Index = 0; Index < Hints.Num(); ++Index)
	{
		if (Index == Hints.Num() - 1)
		{
			EXUi::AddH(KeyBar, EXUi::Sized(WidgetTree, 1.0f, 1.0f), FMargin(0.0f), true);   // the last one (Esc) on the right
		}
		EXUi::AddH(KeyBar, EXUi::Hint(WidgetTree, Hints[Index].Keys, Hints[Index].Label), FMargin(0.0f, 0.0f, 34.0f, 0.0f));
	}
}

AEXHoverCraft* UEXHangarWidget::GetPlayerCraft() const
{
	return Cast<AEXHoverCraft>(GetOwningPlayerPawn());
}
