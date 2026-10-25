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
#include "Game/EXProfile.h"
#include "Race/EXRaceDirector.h"
#include "UI/EXUiStyle.h"

namespace
{
	constexpr int32 HangarRosterSize = 5;
	constexpr float HangarStatBarWidth = 192.0f;   // inside a 222 px tile

	/** What the roster and the title say about each ship (the mock-up the player approved). */
	struct FHangarShipText
	{
		const TCHAR* Name;
		const TCHAR* Role;
		const TCHAR* Subtitle;
	};
	const FHangarShipText HangarShipTexts[] = {
		{ TEXT("STRIX"), TEXT("INTERCEPTOR \u00B7 EQUILIBRADO"), TEXT("INTERCEPTOR  \u00B7  UM MOTOR CENTRAL, ASAS EM QUEDA") },
		{ TEXT("WRAITH"), TEXT("CA\u00C7A EM U \u00B7 R\u00C1PIDO"), TEXT("CA\u00C7A EM FORQUILHA  \u00B7  3 MOTORES DE PLASMA") },
		{ TEXT("NOMAD"), TEXT("DROPSHIP \u00B7 CARGA GRANDE"), TEXT("DROPSHIP  \u00B7  4 MOTORES EM BRA\u00C7OS") },
		{ TEXT("BASTION"), TEXT("BLINDADO \u00B7 MODELO PROVIS\u00D3RIO"), TEXT("BLINDADO  \u00B7  UM MOTOR COLOSSAL (EM CONSTRU\u00C7\u00C3O)") },
		{ TEXT("VORTEX"), TEXT("DELTA \u00B7 O MAIS R\u00C1PIDO, FR\u00C1GIL"), TEXT("ASA VOADORA  \u00B7  MOTOR EMBUTIDO NA CAUDA") },
	};

	const FHangarShipText& HangarTextFor(const FString& ShipName)
	{
		for (const FHangarShipText& Entry : HangarShipTexts)
		{
			if (ShipName.Contains(Entry.Name))
			{
				return Entry;
			}
		}
		return HangarShipTexts[0];
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

	// Top band: HANGAR and the wallet.
	UHorizontalBox* Top = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Top, EXUi::OutlinedText(Tree, TEXT("HANGAR"), 27, EXUi::Bone(), 160, 1, EXUi::Ink(0.6f)));
	EXUi::AddH(Top, EXUi::Text(Tree, TEXT("NAVE E CARGA DA EXPEDI\u00C7\u00C3O"), 11, EXUi::RustHot(), true, 220), FMargin(28.0f, 4.0f, 0.0f, 0.0f));
	EXUi::AddH(Top, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	EXUi::AddH(Top, EXUi::Gem(Tree, 14.0f, EXUi::RustHot()), FMargin(0.0f, 0.0f, 14.0f, 0.0f));
	WalletText = EXUi::Text(Tree, TEXT("0"), 16, EXUi::Bone(), true);
	EXUi::AddH(Top, WalletText, FMargin(0.0f, 0.0f, 10.0f, 0.0f));
	EXUi::AddH(Top, EXUi::Text(Tree, TEXT("STARDUST"), 11, EXUi::Sand(), true, 200));
	EXUi::AddO(Root, EXUi::Sized(Tree, 0.0f, 77.0f, EXUi::Box(Tree, EXUi::Ink(0.55f), FMargin(58.0f, 0.0f, 58.0f, 0.0f), Top)),
		HAlign_Fill, VAlign_Top);

	// The ship's name over the turntable.
	UVerticalBox* Title = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	ShipTitle = EXUi::OutlinedText(Tree, TEXT("-"), 50, EXUi::Bone(), 100, 2, EXUi::Ink(0.75f));
	EXUi::AddV(Title, ShipTitle, FMargin(0.0f), HAlign_Center);
	ShipSubtitle = EXUi::OutlinedText(Tree, TEXT("-"), 11, EXUi::Bone(), 300, 1, EXUi::Ink(0.75f));
	EXUi::AddV(Title, ShipSubtitle, FMargin(0.0f, 4.0f, 0.0f, 0.0f), HAlign_Center);
	EXUi::AddO(Root, Title, HAlign_Center, VAlign_Top, FMargin(0.0f, 112.0f, 0.0f, 0.0f));

	EXUi::AddO(Root, BuildRoster(), HAlign_Left, VAlign_Top, FMargin(58.0f, 112.0f, 0.0f, 0.0f));
	EXUi::AddO(Root, BuildCargo(), HAlign_Right, VAlign_Top, FMargin(0.0f, 112.0f, 48.0f, 0.0f));
	EXUi::AddO(Root, BuildStats(), HAlign_Left, VAlign_Bottom, FMargin(430.0f, 0.0f, 0.0f, 96.0f));
	EXUi::AddO(Root, BuildLaunch(), HAlign_Right, VAlign_Bottom, FMargin(0.0f, 0.0f, 48.0f, 82.0f));

	// Bottom: the keys.
	UHorizontalBox* Keys = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("W"), TEXT("S") }, TEXT("Item")), FMargin(0.0f, 0.0f, 30.0f, 0.0f));
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("A"), TEXT("D") }, TEXT("Quantidade")), FMargin(0.0f, 0.0f, 30.0f, 0.0f));
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("Tab") }, TEXT("Nave")), FMargin(0.0f, 0.0f, 30.0f, 0.0f));
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("Rato"), TEXT("Q"), TEXT("E") }, TEXT("Rodar")), FMargin(0.0f, 0.0f, 30.0f, 0.0f));
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("Roda") }, TEXT("Zoom")), FMargin(0.0f, 0.0f, 30.0f, 0.0f));
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("Espa\u00E7o") }, TEXT("Rodar sozinha")), FMargin(0.0f, 0.0f, 30.0f, 0.0f));
	EXUi::AddH(Keys, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("Esc") }, TEXT("Voltar ao menu")));
	UVerticalBox* Bottom = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Bottom, EXUi::Sized(Tree, 0.0f, 1.0f, EXUi::Box(Tree, EXUi::Rust(0.5f))));
	EXUi::AddV(Bottom, EXUi::Sized(Tree, 0.0f, 55.0f, EXUi::Box(Tree, EXUi::Ink(0.92f), FMargin(58.0f, 0.0f, 58.0f, 0.0f), Keys)));
	EXUi::AddO(Root, Bottom, HAlign_Fill, VAlign_Bottom);
}

UWidget* UEXHangarWidget::BuildRoster()
{
	UWidgetTree* Tree = WidgetTree;
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Column, EXUi::OutlinedText(Tree, TEXT("NAVES"), 11, EXUi::RustHot(), 220, 1, EXUi::Ink(0.6f)), FMargin(0.0f, 0.0f, 0.0f, 10.0f));
	for (int32 Index = 0; Index < HangarRosterSize; ++Index)
	{
		FShipCard Card;
		const EXUi::FFrame CardFrame = EXUi::Frame(Tree, EXUi::Bone(0.08f), EXUi::Plate(0.82f), 1.0f, FMargin(22.0f, 10.0f, 16.0f, 10.0f));
		UOverlay* CardRoot = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		EXUi::AddO(CardRoot, CardFrame.Root, HAlign_Fill, VAlign_Fill);
		UWidget* Bar = EXUi::Sized(Tree, 5.0f, 0.0f, EXUi::Box(Tree, EXUi::Rust()));
		EXUi::AddO(CardRoot, Bar, HAlign_Left, VAlign_Fill);

		UVerticalBox* TextColumn = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
		UHorizontalBox* Head = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		Card.Name = EXUi::Text(Tree, TEXT("-"), 17, EXUi::Bone(), true, 100);
		EXUi::AddH(Head, Card.Name);
		EXUi::AddH(Head, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
		for (int32 Pip = 0; Pip < 5; ++Pip)
		{
			// Lives: small diamonds, green while the ship has them.
			Card.Pips[Pip] = EXUi::Box(Tree, EXUi::Ok());
			USizeBox* Holder = EXUi::Sized(Tree, 9.0f, 9.0f, Card.Pips[Pip]);
			Holder->SetRenderTransformAngle(45.0f);
			EXUi::AddH(Head, Holder, FMargin(4.0f, 0.0f, 3.0f, 0.0f));
		}
		EXUi::AddV(TextColumn, Head);
		Card.Role = EXUi::Text(Tree, TEXT("-"), 10, EXUi::Sand(), false, 120);
		EXUi::AddV(TextColumn, Card.Role, FMargin(0.0f, 4.0f, 0.0f, 0.0f));
		CardFrame.Fill->SetContent(TextColumn);
		CardFrame.Fill->SetVerticalAlignment(VAlign_Center);

		Card.Root = EXUi::Sized(Tree, 348.0f, 77.0f, CardRoot);
		Card.Fill = CardFrame.Fill;
		for (int32 Side = 0; Side < 4; ++Side)
		{
			Card.Edges[Side] = CardFrame.Edges[Side];
		}
		Card.Bar = Bar;
		EXUi::AddV(Column, Card.Root, FMargin(0.0f, 0.0f, 0.0f, 10.0f));
		Cards.Add(Card);
	}
	return Column;
}

UWidget* UEXHangarWidget::BuildCargo()
{
	UWidgetTree* Tree = WidgetTree;
	const EXUi::FFrame Panel = EXUi::Frame(Tree, EXUi::Rust(0.35f), EXUi::Plate(0.9f), 1.0f, FMargin(24.0f, 22.0f, 24.0f, 22.0f), 4.0f);
	Panel.Edges[0]->SetBrushColor(EXUi::Rust());
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	Panel.Fill->SetContent(Column);

	EXUi::AddV(Column, EXUi::Text(Tree, TEXT("CARGA DA EXPEDI\u00C7\u00C3O"), 11, EXUi::Rust(), true, 220));
	UHorizontalBox* CapacityRow = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(CapacityRow, EXUi::Text(Tree, TEXT("Capacidade"), 12, EXUi::Sand(), false));
	EXUi::AddH(CapacityRow, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	CapacityText = EXUi::Text(Tree, TEXT("0 / 0"), 13, EXUi::Bone(), true);
	EXUi::AddH(CapacityRow, CapacityText);
	EXUi::AddV(Column, CapacityRow, FMargin(0.0f, 10.0f, 0.0f, 6.0f));
	CapacityBar = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddV(Column, EXUi::Sized(Tree, 0.0f, 8.0f, CapacityBar), FMargin(0.0f, 0.0f, 0.0f, 14.0f));

	for (int32 Item = 0; Item < EXEconomy::ItemCount; ++Item)
	{
		EXUi::AddV(Column, BuildCargoRow(Item), FMargin(0.0f, 0.0f, 0.0f, 10.0f));
	}

	EXUi::AddV(Column, EXUi::Sized(Tree, 0.0f, 1.0f, EXUi::Box(Tree, EXUi::Bone(0.1f))), FMargin(0.0f, 6.0f, 0.0f, 12.0f));
	UHorizontalBox* RiskRow = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(RiskRow, EXUi::Text(Tree, TEXT("Valor em risco:"), 13, EXUi::Bone(0.9f), false));
	RiskText = EXUi::Text(Tree, TEXT("0"), 16, EXUi::RustHot(), true);
	EXUi::AddH(RiskRow, RiskText, FMargin(8.0f, 0.0f, 9.0f, 0.0f));
	EXUi::AddH(RiskRow, EXUi::Gem(Tree, 10.0f, EXUi::RustHot()));
	EXUi::AddV(Column, RiskRow);
	UTextBlock* Explain = EXUi::Text(Tree, TEXT("Se fores destru\u00EDdo, a carga perde-se e vai para quem extrair. Chega a B para ficares com ela e com a tua "
		"parte do esp\u00F3lio."), 12, EXUi::Bone(0.85f), false);
	Explain->SetAutoWrapText(true);
	EXUi::AddV(Column, Explain, FMargin(0.0f, 6.0f, 0.0f, 0.0f));
	NoticeText = EXUi::Text(Tree, TEXT(""), 12, EXUi::RustHot(), true);
	EXUi::AddV(Column, NoticeText, FMargin(0.0f, 10.0f, 0.0f, 0.0f));
	return EXUi::Sized(Tree, 480.0f, 0.0f, Panel.Root);
}

UWidget* UEXHangarWidget::BuildIcon(int32 Item)
{
	UWidgetTree* Tree = WidgetTree;
	UOverlay* Icon = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Icon, EXUi::Box(Tree, EXUi::Ink(0.55f)), HAlign_Fill, VAlign_Fill);
	switch (static_cast<EEXItem>(Item))
	{
	case EEXItem::Repair:
		// A green cross.
		EXUi::AddO(Icon, EXUi::Sized(Tree, 22.0f, 6.0f, EXUi::Box(Tree, EXUi::Ok())), HAlign_Center, VAlign_Center);
		EXUi::AddO(Icon, EXUi::Sized(Tree, 6.0f, 22.0f, EXUi::Box(Tree, EXUi::Ok())), HAlign_Center, VAlign_Center);
		break;
	case EEXItem::Surge:
		EXUi::AddO(Icon, EXUi::Text(Tree, TEXT("\u00BB"), 24, EXUi::Hex(255, 200, 60), true), HAlign_Center, VAlign_Center);
		break;
	case EEXItem::Shield:
		// A blue badge.
		EXUi::AddO(Icon, EXUi::Sized(Tree, 22.0f, 26.0f, EXUi::Box(Tree, EXUi::Hex(90, 170, 255), FMargin(3.0f), EXUi::Box(Tree, EXUi::Ink(0.9f)))),
			HAlign_Center, VAlign_Center);
		break;
	default:
		EXUi::AddO(Icon, EXUi::Sized(Tree, 16.0f, 22.0f, EXUi::Box(Tree, EXUi::Dim(), FMargin(2.0f), EXUi::Box(Tree, EXUi::Ink(0.9f)))),
			HAlign_Center, VAlign_Center);
		break;
	}
	return EXUi::Sized(Tree, 46.0f, 46.0f, Icon);
}

UWidget* UEXHangarWidget::BuildCargoRow(int32 Item)
{
	UWidgetTree* Tree = WidgetTree;
	const EXEconomy::FItemDef& Def = EXEconomy::Item(static_cast<EEXItem>(Item));
	FCargoRow Row;
	const EXUi::FFrame RowFrame = EXUi::Frame(Tree, EXUi::Bone(0.08f), EXUi::Bone(0.03f), 1.0f, FMargin(12.0f, 10.0f, 12.0f, 10.0f));
	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Line, BuildIcon(Item), FMargin(0.0f, 0.0f, 14.0f, 0.0f));

	UVerticalBox* TextColumn = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(TextColumn, EXUi::Text(Tree, Def.Name, 13, EXUi::Bone(), true));
	EXUi::AddV(TextColumn, EXUi::Text(Tree, Def.Effect, 10, EXUi::Sand(), false), FMargin(0.0f, 3.0f, 0.0f, 0.0f));
	EXUi::AddH(Line, TextColumn, FMargin(0.0f), true);

	UVerticalBox* Right = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* Stepper = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Stepper, EXUi::KeyCap(Tree, TEXT("-")));
	Row.Count = EXUi::Text(Tree, TEXT("0"), 16, EXUi::Bone(), true);
	Row.Count->SetJustification(ETextJustify::Center);
	EXUi::AddH(Stepper, EXUi::Sized(Tree, 36.0f, 0.0f, Row.Count));
	EXUi::AddH(Stepper, EXUi::KeyCap(Tree, TEXT("+")));
	EXUi::AddV(Right, Stepper, FMargin(0.0f), HAlign_Right);
	UHorizontalBox* Price = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	Row.Cost = EXUi::Text(Tree, Def.bAvailable ? FString::FromInt(Def.Cost) : FString(TEXT("em breve")), 10, EXUi::Sand(), false);
	EXUi::AddH(Price, Row.Cost);
	if (Def.bAvailable)
	{
		EXUi::AddH(Price, EXUi::Gem(Tree, 7.0f, EXUi::Sand()), FMargin(6.0f, 0.0f, 6.0f, 0.0f));
		EXUi::AddH(Price, EXUi::Text(Tree, TEXT("cada"), 10, EXUi::Sand(), false));
	}
	EXUi::AddV(Right, Price, FMargin(0.0f, 5.0f, 0.0f, 0.0f), HAlign_Right);
	EXUi::AddH(Line, Right);
	RowFrame.Fill->SetContent(Line);

	Row.Root = RowFrame.Root;
	Row.Fill = RowFrame.Fill;
	for (int32 Side = 0; Side < 4; ++Side)
	{
		Row.Edges[Side] = RowFrame.Edges[Side];
	}
	Rows.Add(Row);
	return RowFrame.Root;
}

UWidget* UEXHangarWidget::BuildStats()
{
	UWidgetTree* Tree = WidgetTree;
	UHorizontalBox* Tiles = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	const TCHAR* const Labels[4] = { TEXT("VELOCIDADE"), TEXT("BLINDAGEM"), TEXT("CARGA"), TEXT("RESIST\u00CANCIA") };
	for (int32 Index = 0; Index < 4; ++Index)
	{
		UVerticalBox* Tile = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
		EXUi::AddV(Tile, EXUi::Text(Tree, Labels[Index], 10, EXUi::Sand(), true, 120));
		Stats[Index].Value = EXUi::Text(Tree, TEXT("-"), 20, EXUi::Bone(), true);
		EXUi::AddV(Tile, Stats[Index].Value, FMargin(0.0f, 4.0f, 0.0f, 8.0f));
		UOverlay* Track = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		EXUi::AddO(Track, EXUi::Sized(Tree, 0.0f, 4.0f, EXUi::Box(Tree, EXUi::Bone(0.12f))), HAlign_Fill, VAlign_Center);
		Stats[Index].Fill = EXUi::Sized(Tree, 10.0f, 4.0f, EXUi::Box(Tree, EXUi::Rust()));
		EXUi::AddO(Track, Stats[Index].Fill, HAlign_Left, VAlign_Center);
		EXUi::AddV(Tile, Track);
		const EXUi::FFrame TileFrame = EXUi::Frame(Tree, EXUi::Bone(0.08f), EXUi::Plate(0.84f), 1.0f, FMargin(14.0f, 12.0f, 14.0f, 12.0f));
		TileFrame.Fill->SetContent(Tile);
		EXUi::AddH(Tiles, EXUi::Sized(Tree, 222.0f, 98.0f, TileFrame.Root), FMargin(0.0f, 0.0f, Index < 3 ? 12.0f : 0.0f, 0.0f));
	}
	return Tiles;
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
	EXUi::AddV(Column, EXUi::Sized(Tree, 480.0f, 70.0f, EXUi::Box(Tree, EXUi::Rust(), FMargin(28.0f, 0.0f, 22.0f, 0.0f), Button)));
	return Column;
}

void UEXHangarWidget::Refresh()
{
	const AEXHoverCraft* Craft = GetPlayerCraft();
	if (!Craft)
	{
		return;
	}
	const UEXProfileSave* Profile = Craft->GetProfile();
	const FString ShipName = Craft->GetShipName().ToUpper();
	EXUi::SetText(ShipTitle, ShipName);
	EXUi::SetText(ShipSubtitle, HangarTextFor(ShipName).Subtitle);

	// The roster: the chosen ship lit, the others plain; lives as pips.
	const int32 ShipCount = Craft->GetShipCount();
	for (int32 Index = 0; Index < Cards.Num(); ++Index)
	{
		const FShipCard& Card = Cards[Index];
		if (Index >= ShipCount)
		{
			Card.Root->SetVisibility(ESlateVisibility::Collapsed);
			continue;
		}
		Card.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
		const FString Name = Craft->GetShipNameAt(Index).ToUpper();
		const bool bOn = Index == Craft->GetShipIndex();
		EXUi::SetText(Card.Name, Name);
		EXUi::SetText(Card.Role, HangarTextFor(Name).Role);
		int32 CardLives = 3;
		float CardSpeedMul = 1.0f, CardWallHitMps = 24.0f;
		AEXHoverCraft::GetShipRaceStats(Name, CardLives, CardSpeedMul, CardWallHitMps);
		for (int32 Pip = 0; Pip < 5; ++Pip)
		{
			Card.Pips[Pip]->SetBrushColor(Pip < CardLives ? EXUi::Ok() : EXUi::Bone(0.15f));
		}
		Card.Fill->SetBrushColor(bOn ? EXUi::Hex(58, 26, 11, 0.94f) : EXUi::Plate(0.82f));
		for (UBorder* Edge : Card.Edges)
		{
			Edge->SetBrushColor(bOn ? EXUi::Rust() : EXUi::Bone(0.08f));
		}
		Card.Bar->SetVisibility(bOn ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Hidden);
	}

	// The cargo: capacity of this ship, the rows, what is at risk.
	const int32 Capacity = EXEconomy::ShipCapacity(ShipName);
	const int32 Weight = EXEconomy::CargoWeight(Profile);
	EXUi::SetText(CapacityText, FString::Printf(TEXT("%d / %d"), Weight, Capacity));
	if (CapacityBar && (Capacity != ShownCapacity || Weight != ShownWeight))
	{
		ShownCapacity = Capacity;
		ShownWeight = Weight;
		CapacityBar->ClearChildren();
		for (int32 Unit = 0; Unit < Capacity; ++Unit)
		{
			EXUi::AddH(CapacityBar, EXUi::Box(WidgetTree, Unit < Weight ? EXUi::Rust() : EXUi::Bone(0.12f)),
				FMargin(0.0f, 0.0f, Unit + 1 < Capacity ? 4.0f : 0.0f, 0.0f), true, VAlign_Fill);
		}
	}
	const int32 Selected = Craft->GetHangarRow();
	for (int32 Item = 0; Item < Rows.Num(); ++Item)
	{
		const FCargoRow& Row = Rows[Item];
		const bool bOn = Item == Selected;
		EXUi::SetText(Row.Count, FString::FromInt(Profile ? Profile->Count(static_cast<EEXItem>(Item)) : 0));
		Row.Fill->SetBrushColor(bOn ? EXUi::Hex(58, 26, 11, 0.9f) : EXUi::Bone(0.03f));
		for (UBorder* Edge : Row.Edges)
		{
			Edge->SetBrushColor(bOn ? EXUi::Rust() : EXUi::Bone(0.08f));
		}
		Row.Root->SetRenderOpacity(EXEconomy::Item(static_cast<EEXItem>(Item)).bAvailable ? 1.0f : 0.45f);
	}
	EXUi::SetText(RiskText, EXUi::Thousands(EXEconomy::CargoValue(Profile)));
	EXUi::SetText(WalletText, EXUi::Thousands(Profile ? Profile->Stardust : 0));
	const float NoticeAge = GetWorld() ? GetWorld()->GetTimeSeconds() - Craft->GetHangarNoticeTime() : 100.0f;
	EXUi::SetText(NoticeText, NoticeAge < 2.5f ? Craft->GetHangarNotice() : FString());
	if (NoticeText)
	{
		NoticeText->SetRenderOpacity(FMath::Clamp((2.5f - NoticeAge) / 0.5f, 0.0f, 1.0f));
	}

	// The ship's numbers (the race rules of AEXHoverCraft: top speed, lives, cargo units, the wall hit that costs a life).
	int32 Lives = 3;
	float SpeedMul = 1.0f, WallHitMps = 24.0f;
	AEXHoverCraft::GetShipRaceStats(ShipName, Lives, SpeedMul, WallHitMps);
	auto ShowStat = [this](int32 Index, const FString& Value, float Share)
	{
		EXUi::SetText(Stats[Index].Value, Value);
		Stats[Index].Fill->SetWidthOverride(HangarStatBarWidth * FMath::Clamp(Share, 0.05f, 1.0f));
	};
	ShowStat(0, FString::Printf(TEXT("%d km/h"), FMath::RoundToInt(Craft->GetBaseTopSpeedMps() * SpeedMul * 3.6f)), (SpeedMul - 0.86f) / 0.22f);
	ShowStat(1, FString::Printf(TEXT("%d vidas"), Lives), Lives / 5.0f);
	ShowStat(2, FString::Printf(TEXT("%d espa\u00E7os"), Capacity), Capacity / 7.0f);
	ShowStat(3, FString::Printf(TEXT("choque a %d km/h"), FMath::RoundToInt(WallHitMps * 3.6f)), WallHitMps / 32.0f);

	const bool bSolo = RaceDirector && RaceDirector->GetLaunchMode() == EEXRaceMode::Solo;
	EXUi::SetText(ModeText, bSolo ? FString(TEXT("EXPEDI\u00C7\u00C3O SOLO  \u00B7  s\u00F3 tu")) : FString(TEXT("PELOT\u00C3O 15  \u00B7  16 naves")));
}

AEXHoverCraft* UEXHangarWidget::GetPlayerCraft() const
{
	return Cast<AEXHoverCraft>(GetOwningPlayerPawn());
}
