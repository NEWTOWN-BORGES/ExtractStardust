#include "UI/EXHangarWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/World.h"
#include "Flight/EXHoverCraft.h"
#include "Game/EXHangarModel.h"
#include "Game/EXProfile.h"
#include "Race/EXRaceDirector.h"
#include "UI/EXUiStyle.h"

namespace
{
	constexpr int32 HangarLeftRows = 9;
	constexpr int32 HangarRightRows = 8;
	constexpr int32 HangarCards = 10;
	constexpr float HangarStatBarWidth = 176.0f;
	constexpr int32 HangarTabs = static_cast<int32>(EEXHangarTab::Count);

	/** The stats shown under the ship, in EEXStat order (the eight core stats). */
	const TCHAR* const HangarStatNames[8] = { TEXT("VELOCIDADE"), TEXT("ACELERA\u00C7\u00C3O"), TEXT("MANOBRA"), TEXT("ESTABILIDADE"),
		TEXT("CASCO"), TEXT("EFICI\u00CANCIA"), TEXT("REFRIGERA\u00C7\u00C3O"), TEXT("NITRO") };

	FLinearColor HangarSelectedFill()
	{
		return EXUi::Hex(58, 26, 11, 0.92f);
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

void UEXHangarWidget::BuildTree()
{
	UWidgetTree* Tree = WidgetTree;
	UOverlay* Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("HangarRoot"));
	Tree->RootWidget = Root;

	// Top band: HANGAR, the tabs and the wallet.
	UHorizontalBox* Top = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Top, EXUi::OutlinedText(Tree, TEXT("HANGAR"), 27, EXUi::Bone(), 160, 1, EXUi::Ink(0.6f)), FMargin(0.0f, 0.0f, 34.0f, 0.0f));
	for (int32 Tab = 0; Tab < HangarTabs; ++Tab)
	{
		UTextBlock* Label = EXUi::Text(Tree, UEXHangarModel::TabName(static_cast<EEXHangarTab>(Tab)), 12, EXUi::Sand(), true, 180);
		UBorder* Chip = EXUi::Box(Tree, EXUi::Ink(0.35f), FMargin(18.0f, 9.0f, 18.0f, 9.0f), Label);
		EXUi::AddH(Top, Chip, FMargin(0.0f, 0.0f, 6.0f, 0.0f));
		TabFills.Add(Chip);
		TabTexts.Add(Label);
	}
	EXUi::AddH(Top, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	EXUi::AddH(Top, EXUi::Gem(Tree, 14.0f, EXUi::RustHot()), FMargin(0.0f, 0.0f, 14.0f, 0.0f));
	WalletText = EXUi::Text(Tree, TEXT("0"), 16, EXUi::Bone(), true);
	EXUi::AddH(Top, WalletText, FMargin(0.0f, 0.0f, 10.0f, 0.0f));
	EXUi::AddH(Top, EXUi::Text(Tree, TEXT("STARDUST"), 11, EXUi::Sand(), true, 200));
	EXUi::AddO(Root, EXUi::Sized(Tree, 0.0f, 77.0f, EXUi::Box(Tree, EXUi::Ink(0.55f), FMargin(58.0f, 0.0f, 58.0f, 0.0f), Top)),
		HAlign_Fill, VAlign_Top);

	// The ship's name over the turntable.
	UVerticalBox* Title = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	ShipTitle = EXUi::OutlinedText(Tree, TEXT("-"), 44, EXUi::Bone(), 100, 2, EXUi::Ink(0.75f));
	EXUi::AddV(Title, ShipTitle, FMargin(0.0f), HAlign_Center);
	ShipSubtitle = EXUi::OutlinedText(Tree, TEXT("-"), 11, EXUi::Bone(), 300, 1, EXUi::Ink(0.75f));
	EXUi::AddV(Title, ShipSubtitle, FMargin(0.0f, 4.0f, 0.0f, 0.0f), HAlign_Center);
	EXUi::AddO(Root, Title, HAlign_Center, VAlign_Top, FMargin(0.0f, 100.0f, 0.0f, 0.0f));

	EXUi::AddO(Root, BuildLeftPanel(), HAlign_Left, VAlign_Top, FMargin(48.0f, 104.0f, 0.0f, 0.0f));
	RightPanel = BuildRightPanel();
	EXUi::AddO(Root, RightPanel, HAlign_Right, VAlign_Top, FMargin(0.0f, 104.0f, 48.0f, 0.0f));
	StatsPanel = BuildStats();
	EXUi::AddO(Root, StatsPanel, HAlign_Center, VAlign_Bottom, FMargin(0.0f, 0.0f, 40.0f, 82.0f));
	LaunchPanel = BuildLaunch();
	EXUi::AddO(Root, LaunchPanel, HAlign_Right, VAlign_Bottom, FMargin(0.0f, 0.0f, 48.0f, 82.0f));
	NoticeText = EXUi::OutlinedText(Tree, TEXT(""), 14, EXUi::RustHot(), 60, 1, EXUi::Ink(0.8f));
	EXUi::AddO(Root, NoticeText, HAlign_Center, VAlign_Bottom, FMargin(0.0f, 0.0f, 0.0f, 262.0f));
	CacheOverlay = BuildCacheOverlay();
	EXUi::AddO(Root, CacheOverlay, HAlign_Fill, VAlign_Fill);

	// Bottom: the keys of the tab (rebuilt when they change).
	KeyBar = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	UVerticalBox* Bottom = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Bottom, EXUi::Sized(Tree, 0.0f, 1.0f, EXUi::Box(Tree, EXUi::Rust(0.5f))));
	EXUi::AddV(Bottom, EXUi::Sized(Tree, 0.0f, 55.0f, EXUi::Box(Tree, EXUi::Ink(0.92f), FMargin(58.0f, 0.0f, 58.0f, 0.0f), KeyBar)));
	EXUi::AddO(Root, Bottom, HAlign_Fill, VAlign_Bottom);
}

UEXHangarWidget::FRowView UEXHangarWidget::MakeRow(float Width, float Height)
{
	UWidgetTree* Tree = WidgetTree;
	FRowView View;
	const EXUi::FFrame RowFrame = EXUi::Frame(Tree, EXUi::Bone(0.08f), EXUi::Bone(0.03f), 1.0f, FMargin(18.0f, 5.0f, 12.0f, 5.0f));
	RowFrame.Fill->SetClipping(EWidgetClipping::ClipToBounds);
	UOverlay* RowRoot = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(RowRoot, RowFrame.Root, HAlign_Fill, VAlign_Fill);
	View.Bar = EXUi::Box(Tree, EXUi::Rust());
	EXUi::AddO(RowRoot, EXUi::Sized(Tree, 4.0f, 0.0f, View.Bar), HAlign_Left, VAlign_Fill, FMargin(0.0f, 5.0f, 0.0f, 5.0f));

	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	UVerticalBox* TextColumn = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	View.Label = EXUi::Text(Tree, TEXT(""), 9, EXUi::Sand(), true, 160);
	View.Title = EXUi::Text(Tree, TEXT(""), 14, EXUi::Bone(), true);
	View.Sub = EXUi::Text(Tree, TEXT(""), 10, EXUi::Sand(), false);
	EXUi::AddV(TextColumn, View.Label);
	EXUi::AddV(TextColumn, View.Title, FMargin(0.0f, 1.0f, 0.0f, 0.0f));
	EXUi::AddV(TextColumn, View.Sub, FMargin(0.0f, 1.0f, 0.0f, 0.0f));
	EXUi::AddH(Line, TextColumn, FMargin(0.0f), true);
	UVerticalBox* RightColumn = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	View.Right = EXUi::Text(Tree, TEXT(""), 12, EXUi::Bone(), true);
	View.Tag = EXUi::Text(Tree, TEXT(""), 9, EXUi::RustHot(), true, 120);
	EXUi::AddV(RightColumn, View.Right, FMargin(0.0f), HAlign_Right);
	EXUi::AddV(RightColumn, View.Tag, FMargin(0.0f, 4.0f, 0.0f, 0.0f), HAlign_Right);
	EXUi::AddH(Line, RightColumn, FMargin(10.0f, 0.0f, 0.0f, 0.0f));
	RowFrame.Fill->SetContent(Line);
	RowFrame.Fill->SetVerticalAlignment(VAlign_Center);

	View.Root = EXUi::Sized(Tree, Width, Height, RowRoot);
	View.Fill = RowFrame.Fill;
	for (int32 Side = 0; Side < 4; ++Side)
	{
		View.Edges[Side] = RowFrame.Edges[Side];
	}
	return View;
}

UWidget* UEXHangarWidget::BuildLeftPanel()
{
	UWidgetTree* Tree = WidgetTree;
	const EXUi::FFrame Panel = EXUi::Frame(Tree, EXUi::Bone(0.08f), EXUi::Plate(0.78f), 1.0f, FMargin(14.0f, 14.0f, 14.0f, 10.0f));
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	Panel.Fill->SetContent(Column);
	LeftTitle = EXUi::Text(Tree, TEXT("-"), 11, EXUi::Rust(), true, 220);
	EXUi::AddV(Column, LeftTitle, FMargin(0.0f, 0.0f, 0.0f, 10.0f));
	for (int32 Index = 0; Index < HangarLeftRows; ++Index)
	{
		FRowView View = MakeRow(400.0f, 60.0f);
		EXUi::AddV(Column, View.Root, FMargin(0.0f, 0.0f, 0.0f, 5.0f));
		LeftRows.Add(View);
	}
	LeftMore = EXUi::Text(Tree, TEXT(""), 10, EXUi::Sand(), true, 120);
	EXUi::AddV(Column, LeftMore, FMargin(2.0f, 2.0f, 0.0f, 0.0f));
	return EXUi::Sized(Tree, 430.0f, 0.0f, Panel.Root);
}

UWidget* UEXHangarWidget::BuildRightPanel()
{
	UWidgetTree* Tree = WidgetTree;
	const EXUi::FFrame Panel = EXUi::Frame(Tree, EXUi::Rust(0.35f), EXUi::Plate(0.82f), 1.0f, FMargin(14.0f, 14.0f, 14.0f, 14.0f), 3.0f);
	Panel.Edges[0]->SetBrushColor(EXUi::Rust());
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	Panel.Fill->SetContent(Column);
	RightTitle = EXUi::Text(Tree, TEXT("-"), 11, EXUi::Rust(), true, 220);
	EXUi::AddV(Column, RightTitle, FMargin(0.0f, 0.0f, 0.0f, 10.0f));
	for (int32 Index = 0; Index < HangarRightRows; ++Index)
	{
		FRowView View = MakeRow(440.0f, 58.0f);
		EXUi::AddV(Column, View.Root, FMargin(0.0f, 0.0f, 0.0f, 5.0f));
		RightRows.Add(View);
	}
	RightDetail = EXUi::Text(Tree, TEXT(""), 12, EXUi::Bone(0.85f), false);
	RightDetail->SetAutoWrapText(true);
	EXUi::AddV(Column, EXUi::Sized(Tree, 440.0f, 0.0f, RightDetail), FMargin(0.0f, 8.0f, 0.0f, 0.0f));
	return EXUi::Sized(Tree, 470.0f, 0.0f, Panel.Root);
}

UWidget* UEXHangarWidget::BuildStats()
{
	UWidgetTree* Tree = WidgetTree;
	const EXUi::FFrame Panel = EXUi::Frame(Tree, EXUi::Bone(0.08f), EXUi::Plate(0.84f), 1.0f, FMargin(16.0f, 12.0f, 16.0f, 10.0f));
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
			EXUi::AddV(Box, EXUi::Text(Tree, HangarStatNames[Stat], 9, EXUi::Sand(), true, 150));
			UHorizontalBox* Numbers = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
			View.Value = EXUi::Text(Tree, TEXT("-"), 15, EXUi::Bone(), true);
			View.Delta = EXUi::Text(Tree, TEXT(""), 11, EXUi::Ok(), true);
			EXUi::AddH(Numbers, View.Value);
			EXUi::AddH(Numbers, View.Delta, FMargin(8.0f, 0.0f, 0.0f, 0.0f));
			EXUi::AddV(Box, Numbers, FMargin(0.0f, 1.0f, 0.0f, 4.0f));
			UOverlay* Track = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
			EXUi::AddO(Track, EXUi::Sized(Tree, HangarStatBarWidth, 5.0f, EXUi::Box(Tree, EXUi::Bone(0.1f))), HAlign_Left, VAlign_Center);
			UHorizontalBox* Bar = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
			View.Fill = EXUi::Sized(Tree, 10.0f, 5.0f, EXUi::Box(Tree, EXUi::Rust()));
			View.ChangeColour = EXUi::Box(Tree, EXUi::Ok());
			View.Change = EXUi::Sized(Tree, 0.0f, 5.0f, View.ChangeColour);
			EXUi::AddH(Bar, View.Fill);
			EXUi::AddH(Bar, View.Change);
			EXUi::AddO(Track, Bar, HAlign_Left, VAlign_Center);
			EXUi::AddV(Box, Track);
			EXUi::AddH(Cells, EXUi::Sized(Tree, 200.0f, 50.0f, Box), FMargin(0.0f, 0.0f, Cell < 3 ? 14.0f : 0.0f, 0.0f));
			StatViews.Add(View);
		}
		EXUi::AddV(Column, Cells, FMargin(0.0f, 0.0f, 0.0f, RowIndex == 0 ? 6.0f : 0.0f));
	}
	LivesText = EXUi::Text(Tree, TEXT(""), 11, EXUi::Ok(), true, 100);
	EXUi::AddV(Column, LivesText, FMargin(0.0f, 6.0f, 0.0f, 0.0f));
	return Panel.Root;
}

UWidget* UEXHangarWidget::BuildLaunch()
{
	UWidgetTree* Tree = WidgetTree;
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	ModeText = EXUi::OutlinedText(Tree, TEXT("-"), 12, EXUi::Bone(), 120, 1, EXUi::Ink(0.6f));
	EXUi::AddV(Column, ModeText, FMargin(0.0f, 0.0f, 0.0f, 8.0f), HAlign_Right);
	UHorizontalBox* Button = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Button, EXUi::Text(Tree, TEXT("LAN\u00C7AR EXPEDI\u00C7\u00C3O"), 16, EXUi::Ink(), true, 200));
	EXUi::AddH(Button, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	EXUi::AddH(Button, EXUi::KeyCap(Tree, TEXT("ENTER"), true));
	EXUi::AddV(Column, EXUi::Sized(Tree, 470.0f, 64.0f, EXUi::Box(Tree, EXUi::Rust(), FMargin(28.0f, 0.0f, 22.0f, 0.0f), Button)));
	return Column;
}

UWidget* UEXHangarWidget::BuildCacheOverlay()
{
	UWidgetTree* Tree = WidgetTree;
	UOverlay* Layer = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Layer, EXUi::Box(Tree, EXUi::Ink(0.86f)), HAlign_Fill, VAlign_Fill);
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	CacheTitle = EXUi::OutlinedText(Tree, TEXT("-"), 34, EXUi::Bone(), 140, 1, EXUi::Ink(0.8f));
	EXUi::AddV(Column, CacheTitle, FMargin(0.0f), HAlign_Center);
	CacheSummary = EXUi::Text(Tree, TEXT(""), 13, EXUi::Sand(), true, 120);
	EXUi::AddV(Column, CacheSummary, FMargin(0.0f, 8.0f, 0.0f, 22.0f), HAlign_Center);
	for (int32 RowIndex = 0; RowIndex < 2; ++RowIndex)
	{
		UHorizontalBox* Cards = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		for (int32 Index = 0; Index < HangarCards / 2; ++Index)
		{
			FCardView View;
			UOverlay* CardRoot = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
			// The back: a rust diamond with a question mark.
			UOverlay* Back = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
			EXUi::AddO(Back, EXUi::Box(Tree, EXUi::Hex(36, 21, 13, 0.97f)), HAlign_Fill, VAlign_Fill);
			USizeBox* Diamond = EXUi::Sized(Tree, 70.0f, 70.0f, EXUi::Box(Tree, EXUi::Rust(), FMargin(3.0f), EXUi::Box(Tree, EXUi::Hex(36, 21, 13))));
			Diamond->SetRenderTransformAngle(45.0f);
			EXUi::AddO(Back, Diamond, HAlign_Center, VAlign_Center);
			EXUi::AddO(Back, EXUi::Text(Tree, TEXT("?"), 30, EXUi::RustHot(), true), HAlign_Center, VAlign_Center);
			EXUi::AddO(CardRoot, Back, HAlign_Fill, VAlign_Fill);
			// The front: the rarity band on top, then what it is.
			const EXUi::FFrame Face = EXUi::Frame(Tree, EXUi::Bone(0.3f), EXUi::Hex(24, 17, 12, 0.97f), 1.0f, FMargin(14.0f, 16.0f, 14.0f, 12.0f));
			UOverlay* Front = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
			EXUi::AddO(Front, Face.Root, HAlign_Fill, VAlign_Fill);
			View.Band = EXUi::Box(Tree, EXUi::Rust());
			EXUi::AddO(Front, EXUi::Sized(Tree, 0.0f, 6.0f, View.Band), HAlign_Fill, VAlign_Top);
			UVerticalBox* Text = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
			View.Label = EXUi::Text(Tree, TEXT(""), 9, EXUi::Sand(), true, 160);
			View.Title = EXUi::Text(Tree, TEXT(""), 15, EXUi::Bone(), true);
			View.Title->SetAutoWrapText(true);
			View.Sub = EXUi::Text(Tree, TEXT(""), 11, EXUi::Sand(), false);
			View.Sub->SetAutoWrapText(true);
			View.Right = EXUi::Text(Tree, TEXT(""), 12, EXUi::Bone(0.8f), true);
			View.Tag = EXUi::Text(Tree, TEXT(""), 10, EXUi::Hex(181, 108, 255), true, 200);
			EXUi::AddV(Text, View.Tag, FMargin(0.0f), HAlign_Right);
			EXUi::AddV(Text, View.Label, FMargin(0.0f, 2.0f, 0.0f, 0.0f));
			EXUi::AddV(Text, View.Title, FMargin(0.0f, 4.0f, 0.0f, 0.0f));
			EXUi::AddV(Text, View.Sub, FMargin(0.0f, 6.0f, 0.0f, 0.0f));
			EXUi::AddV(Text, View.Right, FMargin(0.0f, 10.0f, 0.0f, 0.0f));
			Face.Fill->SetContent(Text);
			for (int32 Side = 0; Side < 4; ++Side)
			{
				View.Edges[Side] = Face.Edges[Side];
			}
			EXUi::AddO(CardRoot, Front, HAlign_Fill, VAlign_Fill);
			View.Front = Front;
			View.Back = Back;
			View.Root = EXUi::Sized(Tree, 236.0f, 270.0f, CardRoot);
			EXUi::AddH(Cards, View.Root, FMargin(Index > 0 ? 16.0f : 0.0f, 0.0f, 0.0f, 0.0f));
			CardViews.Add(View);
		}
		EXUi::AddV(Column, Cards, FMargin(0.0f, RowIndex > 0 ? 16.0f : 0.0f, 0.0f, 0.0f), HAlign_Center);
	}
	EXUi::AddO(Layer, Column, HAlign_Center, VAlign_Center, FMargin(0.0f, 0.0f, 0.0f, 40.0f));
	Layer->SetVisibility(ESlateVisibility::Collapsed);
	return Layer;
}

void UEXHangarWidget::ShowRow(const FRowView& View, const FEXHangarRow* Row, bool bSelected) const
{
	if (!Row)
	{
		View.Root->SetVisibility(ESlateVisibility::Collapsed);
		return;
	}
	View.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
	EXUi::SetText(View.Label, Row->Label);
	EXUi::SetText(View.Title, Row->Title);
	EXUi::SetText(View.Sub, Row->Sub);
	EXUi::SetText(View.Right, Row->Right);
	EXUi::SetText(View.Tag, Row->Tag);
	View.Bar->SetBrushColor(Row->Colour);
	// The small label takes the row's colour (the rarity), the title stays bone.
	View.Label->SetColorAndOpacity(FSlateColor(Row->Colour.Desaturate(0.1f)));
	View.Root->SetRenderOpacity(Row->bDim && !bSelected ? 0.5f : 1.0f);
	View.Fill->SetBrushColor(bSelected ? HangarSelectedFill() : EXUi::Bone(0.03f));
	for (UBorder* Edge : View.Edges)
	{
		Edge->SetBrushColor(bSelected ? EXUi::Rust() : EXUi::Bone(0.08f));
	}
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
	EXUi::SetText(ShipTitle, ShipName);
	EXUi::SetText(ShipSubtitle, UEXHangarModel::ShipSubtitle(ShipName));
	EXUi::SetText(WalletText, EXUi::Thousands(Profile ? Profile->Stardust : 0));
	for (int32 Index = 0; Index < TabFills.Num(); ++Index)
	{
		const bool bOn = Index == static_cast<int32>(Tab);
		TabFills[Index]->SetBrushColor(bOn ? EXUi::Rust(0.32f) : EXUi::Ink(0.35f));
		TabTexts[Index]->SetColorAndOpacity(FSlateColor(bOn ? EXUi::Bone() : EXUi::Sand()));
	}

	// Left: the tab's list, a window round the selected row.
	FString Title;
	TArray<FEXHangarRow> Rows;
	int32 Selected = 0;
	Model->BuildLeft(Title, Rows, Selected);
	EXUi::SetText(LeftTitle, Title);
	const int32 First = FMath::Clamp(Selected - HangarLeftRows / 2, 0, FMath::Max(0, Rows.Num() - HangarLeftRows));
	for (int32 Index = 0; Index < LeftRows.Num(); ++Index)
	{
		const int32 RowIndex = First + Index;
		ShowRow(LeftRows[Index], Rows.IsValidIndex(RowIndex) ? &Rows[RowIndex] : nullptr, RowIndex == Selected);
	}
	EXUi::SetText(LeftMore, Rows.Num() > HangarLeftRows ? FString::Printf(TEXT("%d / %d"), Selected + 1, Rows.Num()) : FString());

	// Right: the pieces for the slot, the stock, the details.
	FString Detail;
	Model->BuildRight(Title, Rows, Selected, Detail);
	EXUi::SetText(RightTitle, Title);
	const int32 RightFirst = Selected >= 0 ? FMath::Clamp(Selected - HangarRightRows / 2, 0, FMath::Max(0, Rows.Num() - HangarRightRows)) : 0;
	for (int32 Index = 0; Index < RightRows.Num(); ++Index)
	{
		const int32 RowIndex = RightFirst + Index;
		ShowRow(RightRows[Index], Rows.IsValidIndex(RowIndex) ? &Rows[RowIndex] : nullptr, RowIndex == Selected);
	}
	EXUi::SetText(RightDetail, Detail);

	// Bottom: the stats now and with the piece looked at (ship and equip tabs, and a module that fits in the shop or vault).
	int32 Now[EXMeta::StatCount];
	int32 Next[EXMeta::StatCount];
	int32 LivesNow = 0, LivesNext = 0;
	Model->GetStats(Now, Next, LivesNow, LivesNext);
	bool bChanges = false;
	for (int32 Stat = 0; Stat < EXMeta::CoreStats; ++Stat)
	{
		bChanges |= Now[Stat] != Next[Stat];
	}
	const bool bShowStats = Tab == EEXHangarTab::Ship || Tab == EEXHangarTab::Equip || bChanges;
	StatsPanel->SetVisibility(bShowStats ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	for (int32 Stat = 0; Stat < StatViews.Num() && Stat < EXMeta::CoreStats; ++Stat)
	{
		const FStatView& View = StatViews[Stat];
		const int32 Delta = Next[Stat] - Now[Stat];
		EXUi::SetText(View.Value, Delta == 0 ? FString::FromInt(Now[Stat]) : FString::Printf(TEXT("%d \u2192 %d"), Now[Stat], Next[Stat]));
		EXUi::SetText(View.Delta, Delta == 0 ? FString() : FString::Printf(TEXT("%s%d"), Delta > 0 ? TEXT("\u25B2") : TEXT("\u25BC"), FMath::Abs(Delta)));
		View.Delta->SetColorAndOpacity(FSlateColor(Delta > 0 ? EXUi::Ok() : EXUi::Hex(255, 90, 74)));
		View.Fill->SetWidthOverride(HangarStatBarWidth * FMath::Clamp(FMath::Min(Now[Stat], Next[Stat]) / 100.0f, 0.02f, 1.0f));
		View.Change->SetWidthOverride(HangarStatBarWidth * FMath::Abs(Delta) / 100.0f);
		View.ChangeColour->SetBrushColor(Delta > 0 ? EXUi::Ok() : EXUi::Hex(255, 90, 74, 0.85f));
	}
	EXUi::SetText(LivesText, LivesNow == LivesNext ? FString::Printf(TEXT("%d VIDAS"), LivesNow)
		: FString::Printf(TEXT("%d VIDAS \u2192 %d VIDAS"), LivesNow, LivesNext));

	// The launch button belongs to the ship tab.
	LaunchPanel->SetVisibility(Tab == EEXHangarTab::Ship ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	const bool bSolo = RaceDirector && RaceDirector->GetLaunchMode() == EEXRaceMode::Solo;
	EXUi::SetText(ModeText, bSolo ? FString(TEXT("EXPEDI\u00C7\u00C3O SOLO  \u00B7  s\u00F3 tu")) : FString(TEXT("PELOT\u00C3O 15  \u00B7  16 naves")));

	const float NoticeAge = GetWorld() ? GetWorld()->GetTimeSeconds() - Model->GetNoticeTime() : 100.0f;
	EXUi::SetText(NoticeText, NoticeAge < 3.0f ? Model->GetNotice() : FString());
	NoticeText->SetRenderOpacity(FMath::Clamp((3.0f - NoticeAge) / 0.5f, 0.0f, 1.0f));

	RefreshCards(Model);
	RefreshHints(Model);
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
	for (int32 Index = 0; Index < CardViews.Num(); ++Index)
	{
		const FCardView& View = CardViews[Index];
		if (!Cards.IsValidIndex(Index))
		{
			View.Root->SetVisibility(ESlateVisibility::Collapsed);
			continue;
		}
		View.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
		const bool bTurned = Index < Model->GetRevealed();
		View.Front->SetVisibility(bTurned ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Hidden);
		View.Back->SetVisibility(bTurned ? ESlateVisibility::Hidden : ESlateVisibility::HitTestInvisible);
		const FEXHangarRow& Card = Cards[Index];
		View.Band->SetBrushColor(Card.Colour);
		for (UBorder* Edge : View.Edges)
		{
			Edge->SetBrushColor(FLinearColor(Card.Colour.R, Card.Colour.G, Card.Colour.B, 0.7f));
		}
		EXUi::SetText(View.Label, Card.Label);
		View.Label->SetColorAndOpacity(FSlateColor(Card.Colour));
		EXUi::SetText(View.Title, Card.Title);
		EXUi::SetText(View.Sub, Card.Sub);
		EXUi::SetText(View.Right, Card.Right + TEXT(" STARDUST"));
		EXUi::SetText(View.Tag, Card.Tag);
		Shown += bTurned ? 1 : 0;
	}
	EXUi::SetText(CacheSummary, FString::Printf(TEXT("%d / %d REVELADAS  \u00B7  VALOR %s STARDUST  \u00B7  CUSTA %s"), Shown, Cards.Num(),
		*EXUi::Thousands(Model->GetCacheValue()), *EXUi::Thousands(Model->GetCachePrice())));
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
		EXUi::AddH(KeyBar, EXUi::Hint(WidgetTree, Hints[Index].Keys, Hints[Index].Label), FMargin(0.0f, 0.0f, 30.0f, 0.0f));
	}
}

AEXHoverCraft* UEXHangarWidget::GetPlayerCraft() const
{
	return Cast<AEXHoverCraft>(GetOwningPlayerPawn());
}
