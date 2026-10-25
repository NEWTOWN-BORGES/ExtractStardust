#include "UI/EXMainMenuWidget.h"

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
#include "Flight/EXHoverCraft.h"
#include "Framework/Application/SlateApplication.h"
#include "Game/EXProfile.h"
#include "InputCoreTypes.h"
#include "Race/EXRaceDirector.h"
#include "UI/EXRouteMapWidget.h"
#include "UI/EXUiStyle.h"

namespace
{
	constexpr int32 MenuLineCount = 4;            // 0 solo, 1 bots, 2 hangar, 3 quit (AEXRaceDirector::MenuInput)
	constexpr float MenuColumnWidth = 624.0f;
	constexpr float BriefCardWidth = 564.0f;
	constexpr float BriefAverageKmh = 340.0f;     // the duration shown: the race line at this average speed
	/** Short cargo names for the briefing, by EEXItem. */
	const TCHAR* const MenuCargoNames[] = { TEXT("Repara\u00E7\u00E3o"), TEXT("Surge"), TEXT("Escudo"), TEXT("Combust\u00EDvel") };
}

void UEXMainMenuWidget::InitializeMenu(AEXRaceDirector* InRaceDirector)
{
	RaceDirector = InRaceDirector;
	// The whole screen takes the mouse: the lines are highlighted and clicked here (keys still go to the game).
	SetVisibility(ESlateVisibility::Visible);
}

TSharedRef<SWidget> UEXMainMenuWidget::RebuildWidget()
{
	// Built in code: the tree must exist before the Slate widgets are made from it.
	if (WidgetTree && !WidgetTree->RootWidget)
	{
		BuildTree();
	}
	return Super::RebuildWidget();
}

void UEXMainMenuWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	Refresh();
}

void UEXMainMenuWidget::BuildTree()
{
	UWidgetTree* Tree = WidgetTree;
	UOverlay* Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("MenuRoot"));
	Tree->RootWidget = Root;

	// A light shade behind the left column, so the text reads over the lit garage.
	EXUi::AddO(Root, EXUi::Sized(Tree, 900.0f, 0.0f, EXUi::Fade(Tree, EXUi::Ink(), 0.62f, 0.0f, 24)), HAlign_Left, VAlign_Fill);

	// Top: the expedition and the wallet.
	UHorizontalBox* Top = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Top, EXUi::Text(Tree, TEXT("EXPEDI\u00C7\u00C3O 01  \u00B7  RED DUST DIVIDE"), 11, EXUi::Rust(), true, 220));
	EXUi::AddH(Top, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	EXUi::AddH(Top, EXUi::Gem(Tree, 14.0f, EXUi::RustHot()), FMargin(0.0f, 0.0f, 14.0f, 0.0f));
	WalletText = EXUi::Text(Tree, TEXT("0"), 16, EXUi::Bone(), true);
	EXUi::AddH(Top, WalletText, FMargin(0.0f, 0.0f, 10.0f, 0.0f));
	EXUi::AddH(Top, EXUi::Text(Tree, TEXT("STARDUST"), 11, EXUi::Sand(), true, 200));
	EXUi::AddO(Root, EXUi::Sized(Tree, 0.0f, 77.0f, Top), HAlign_Fill, VAlign_Top, FMargin(58.0f, 0.0f, 58.0f, 0.0f));

	// Left: the logo and the four lines.
	UVerticalBox* Left = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Left, EXUi::Text(Tree, TEXT("EXTRACT"), 20, EXUi::Bone(), true, 620), FMargin(0.0f, 19.0f, 0.0f, 0.0f));
	UTextBlock* Logo = EXUi::Text(Tree, TEXT("STARDUST"), 68, EXUi::Hex(243, 154, 76), true, 150);
	Logo->SetShadowOffset(FVector2D(0.0f, 3.0f));
	Logo->SetShadowColorAndOpacity(EXUi::Hex(120, 30, 6, 0.85f));
	EXUi::AddV(Left, Logo, FMargin(0.0f, -4.0f, 0.0f, 0.0f));
	EXUi::AddV(Left, EXUi::Text(Tree, TEXT("RACE  \u00B7  SURVIVE  \u00B7  EXTRACT"), 13, EXUi::Rust(), true, 420), FMargin(0.0f, 6.0f, 0.0f, 46.0f));
	const TCHAR* const Titles[MenuLineCount] = { TEXT("EXPEDI\u00C7\u00C3O SOLO"), TEXT("PELOT\u00C3O 15"), TEXT("HANGAR"), TEXT("SAIR") };
	const TCHAR* const Descriptions[MenuLineCount] = {
		TEXT("Tu contra o deserto. Chega vivo a B."),
		TEXT("Quinze rivais na grelha. S\u00F3 quem chega vivo a B extrai."),
		TEXT("Nave e carga para a expedi\u00E7\u00E3o. As luzes acendem-se."),
		TEXT("Fechar o jogo. O perfil fica guardado."),
	};
	for (int32 Index = 0; Index < MenuLineCount; ++Index)
	{
		EXUi::AddV(Left, BuildItem(Index, Titles[Index], Descriptions[Index]), FMargin(0.0f, 0.0f, 0.0f, 8.0f));
	}
	EXUi::AddO(Root, EXUi::Sized(Tree, MenuColumnWidth, 0.0f, Left), HAlign_Left, VAlign_Top, FMargin(77.0f, 115.0f, 0.0f, 0.0f));

	// Right: the briefing.
	EXUi::AddO(Root, BuildBriefing(), HAlign_Right, VAlign_Top, FMargin(0.0f, 115.0f, 67.0f, 0.0f));

	// Bottom: the keys.
	UHorizontalBox* Keys = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("W"), TEXT("S") }, TEXT("Navegar")), FMargin(0.0f, 0.0f, 34.0f, 0.0f));
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("Enter"), TEXT("X") }, TEXT("Confirmar")), FMargin(0.0f, 0.0f, 34.0f, 0.0f));
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("Tab") }, TEXT("Nave")), FMargin(0.0f, 0.0f, 34.0f, 0.0f));
	EXUi::AddH(Keys, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
	EXUi::AddH(Keys, EXUi::Hint(Tree, TArray<FString>{ TEXT("Esc") }, TEXT("Sair")));
	UVerticalBox* Bottom = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Bottom, EXUi::Sized(Tree, 0.0f, 1.0f, EXUi::Box(Tree, EXUi::Rust(0.5f))));
	EXUi::AddV(Bottom, EXUi::Sized(Tree, 0.0f, 55.0f, EXUi::Box(Tree, EXUi::Ink(0.92f), FMargin(58.0f, 0.0f, 58.0f, 0.0f), Keys)));
	EXUi::AddO(Root, Bottom, HAlign_Fill, VAlign_Bottom);
}

UWidget* UEXMainMenuWidget::BuildItem(int32 Index, const FString& Title, const FString& Description)
{
	UWidgetTree* Tree = WidgetTree;
	UOverlay* Line = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	// The highlight: an orange wash fading to the right and the bar on the left.
	UWidget* Glow = EXUi::Fade(Tree, EXUi::Rust(), 0.30f, 0.0f, 12);
	EXUi::AddO(Line, Glow, HAlign_Fill, VAlign_Fill);
	UWidget* Bar = EXUi::Sized(Tree, 5.0f, 0.0f, EXUi::Box(Tree, EXUi::Rust()));
	EXUi::AddO(Line, Bar, HAlign_Left, VAlign_Fill);

	UVerticalBox* TextColumn = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* Head = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	UTextBlock* Number = EXUi::Text(Tree, FString::Printf(TEXT("%02d"), Index + 1), 13, EXUi::Dim(), true, 60);
	EXUi::AddH(Head, EXUi::Sized(Tree, 53.0f, 0.0f, Number));
	UTextBlock* TitleText = EXUi::Text(Tree, Title, 27, EXUi::Sand(), true, 80);
	EXUi::AddH(Head, TitleText);
	EXUi::AddV(TextColumn, Head);
	UTextBlock* DescriptionText = EXUi::Text(Tree, Description, 13, EXUi::Hex(215, 195, 160), false, 20);
	EXUi::AddV(TextColumn, DescriptionText, FMargin(53.0f, 6.0f, 0.0f, 0.0f));
	EXUi::AddO(Line, TextColumn, HAlign_Fill, VAlign_Center, FMargin(26.0f, 16.0f, 22.0f, 16.0f));

	ItemRoots.Add(Line);
	ItemGlows.Add(Glow);
	ItemBars.Add(Bar);
	ItemNumbers.Add(Number);
	ItemTitles.Add(TitleText);
	ItemDescriptions.Add(DescriptionText);
	return Line;
}

UWidget* UEXMainMenuWidget::BuildBriefing()
{
	UWidgetTree* Tree = WidgetTree;
	const EXUi::FFrame Card = EXUi::Frame(Tree, EXUi::Rust(0.35f), EXUi::Plate(0.88f), 1.0f, FMargin(29.0f, 26.0f, 29.0f, 26.0f), 4.0f);
	Card.Edges[0]->SetBrushColor(EXUi::Rust());   // the accent along the top
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	Card.Fill->SetContent(Column);

	EXUi::AddV(Column, EXUi::Text(Tree, TEXT("BRIEFING DA EXPEDI\u00C7\u00C3O"), 11, EXUi::Rust(), true, 220));
	EXUi::AddV(Column, EXUi::Text(Tree, TEXT("RED DUST DIVIDE"), 23, EXUi::Bone(), true, 60), FMargin(0.0f, 7.0f, 0.0f, 2.0f));
	BriefSubText = EXUi::Text(Tree, TEXT(""), 12, EXUi::Sand(), false);
	EXUi::AddV(Column, BriefSubText);

	// The race line from above.
	RouteMap = Tree->ConstructWidget<UEXRouteMapWidget>(UEXRouteMapWidget::StaticClass());
	const EXUi::FFrame MapFrame = EXUi::Frame(Tree, EXUi::Bone(0.12f), EXUi::Ink(0.45f), 1.0f, FMargin(0.0f));
	MapFrame.Fill->SetContent(EXUi::Sized(Tree, 0.0f, 300.0f, RouteMap));
	EXUi::AddV(Column, MapFrame.Root, FMargin(0.0f, 17.0f, 0.0f, 7.0f));

	// Distance, duration, shortcuts.
	UHorizontalBox* Stats = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	auto AddStat = [&](const FString& Value, const FString& Label, float RightGap) -> UTextBlock*
	{
		UVerticalBox* Tile = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
		UTextBlock* ValueText = EXUi::Text(Tree, Value, 20, EXUi::Bone(), true);
		EXUi::AddV(Tile, ValueText);
		EXUi::AddV(Tile, EXUi::Text(Tree, Label, 10, EXUi::Sand(), true, 120), FMargin(0.0f, 3.0f, 0.0f, 0.0f));
		EXUi::AddH(Stats, EXUi::Box(Tree, EXUi::Bone(0.04f), FMargin(14.0f, 12.0f), Tile), FMargin(0.0f, 0.0f, RightGap, 0.0f), true, VAlign_Fill);
		return ValueText;
	};
	DistanceText = AddStat(TEXT("--"), TEXT("DIST\u00C2NCIA"), 10.0f);
	DurationText = AddStat(TEXT("--"), TEXT("DURA\u00C7\u00C3O"), 10.0f);
	AddStat(TEXT("7"), TEXT("ATALHOS"), 0.0f);
	EXUi::AddV(Column, Stats, FMargin(0.0f, 7.0f, 0.0f, 0.0f));

	// What the expedition holds.
	auto AddChipRow = [&](const TArray<FString>& Chips)
	{
		UHorizontalBox* Row = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		for (const FString& Chip : Chips)
		{
			const EXUi::FFrame ChipFrame = EXUi::Frame(Tree, EXUi::Rust(0.45f), EXUi::Rust(0.14f), 1.0f, FMargin(10.0f, 4.0f));
			ChipFrame.Fill->SetContent(EXUi::Text(Tree, Chip, 11, EXUi::Hex(243, 211, 184), false));
			EXUi::AddH(Row, ChipFrame.Root, FMargin(0.0f, 0.0f, 7.0f, 0.0f));
		}
		EXUi::AddV(Column, Row, FMargin(0.0f, 7.0f, 0.0f, 0.0f), HAlign_Left);
	};
	AddChipRow(TArray<FString>{ TEXT("T\u00FAnel The Hollow"), TEXT("Lajes partidas"), TEXT("Salto-her\u00F3i") });
	AddChipRow(TArray<FString>{ TEXT("Dunas"), TEXT("Fendas"), TEXT("19 saltos") });

	// Ship, cargo, risk, the last expedition.
	auto AddRow = [&](const FString& Label, UTextBlock* Value, bool bLineAbove)
	{
		if (bLineAbove)
		{
			EXUi::AddV(Column, EXUi::Sized(Tree, 0.0f, 1.0f, EXUi::Box(Tree, EXUi::Bone(0.1f))), FMargin(0.0f, 14.0f, 0.0f, 10.0f));
		}
		UHorizontalBox* Row = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		EXUi::AddH(Row, EXUi::Text(Tree, Label, 13, EXUi::Bone(0.9f), false));
		EXUi::AddH(Row, EXUi::Sized(Tree, 1.0f, 1.0f), FMargin(0.0f), true);
		EXUi::AddH(Row, Value);
		EXUi::AddV(Column, Row, FMargin(0.0f, bLineAbove ? 0.0f : 6.0f, 0.0f, 0.0f));
	};
	ShipText = EXUi::Text(Tree, TEXT("-"), 13, EXUi::Bone(), true, 120);
	AddRow(TEXT("A tua nave"), ShipText, true);
	CargoText = EXUi::Text(Tree, TEXT("-"), 13, EXUi::Bone(), false);
	AddRow(TEXT("Carga"), CargoText, false);
	RiskText = EXUi::Text(Tree, TEXT("0"), 13, EXUi::RustHot(), true);
	AddRow(TEXT("Em risco se fores destru\u00EDdo"), RiskText, true);
	LastRunText = EXUi::Text(Tree, TEXT("-"), 13, EXUi::Sand(), true);
	AddRow(TEXT("\u00DAltima expedi\u00E7\u00E3o"), LastRunText, false);

	return EXUi::Sized(Tree, BriefCardWidth, 0.0f, Card.Root);
}

void UEXMainMenuWidget::Refresh()
{
	const int32 Choice = RaceDirector ? RaceDirector->GetMenuChoice() : 1;
	if (Choice != ShownChoice)
	{
		ShownChoice = Choice;
		for (int32 Index = 0; Index < ItemTitles.Num(); ++Index)
		{
			const bool bOn = Index == Choice;
			ItemGlows[Index]->SetVisibility(bOn ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Hidden);
			ItemBars[Index]->SetVisibility(bOn ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Hidden);
			ItemNumbers[Index]->SetColorAndOpacity(FSlateColor(bOn ? EXUi::Rust() : EXUi::Dim()));
			ItemTitles[Index]->SetColorAndOpacity(FSlateColor(bOn ? EXUi::Bone() : EXUi::Sand()));
			ItemDescriptions[Index]->SetVisibility(bOn ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
		}
	}
	EXUi::SetText(BriefSubText, FString::Printf(TEXT("Canyonlands  \u00B7  de A (The Basin) a B (Mesa Arch)  \u00B7  %s"),
		Choice == 0 ? TEXT("s\u00F3 tu") : TEXT("16 naves")));

	const AEXHoverCraft* Craft = GetPlayerCraft();
	if (!Craft)
	{
		return;
	}
	const TArray<FVector2D>& Route = Craft->GetMapRoute();
	if (Route.Num() > 1)
	{
		if (RouteMap && !RouteMap->HasRoute())
		{
			RouteMap->SetRoute(Route);
		}
		const float RouteM = (Route.Num() - 1) * 5.0f;
		EXUi::SetText(DistanceText, FString::Printf(TEXT("%.1f km"), RouteM / 1000.0f).Replace(TEXT("."), TEXT(",")));
		const int32 Seconds = FMath::RoundToInt(RouteM / (BriefAverageKmh / 3.6f));
		EXUi::SetText(DurationText, FString::Printf(TEXT("~%d:%02d"), Seconds / 60, Seconds % 60));
	}
	EXUi::SetText(ShipText, Craft->GetShipName().ToUpper());

	const UEXProfileSave* Profile = Craft->GetProfile();
	if (!Profile)
	{
		return;
	}
	EXUi::SetText(WalletText, EXUi::Thousands(Profile->Stardust));
	FString Cargo;
	for (int32 Index = 0; Index < EXEconomy::ItemCount && Index < static_cast<int32>(UE_ARRAY_COUNT(MenuCargoNames)); ++Index)
	{
		const int32 Count = Profile->Count(static_cast<EEXItem>(Index));
		if (Count > 0)
		{
			Cargo += FString::Printf(TEXT("%s%s \u00D7%d"), Cargo.IsEmpty() ? TEXT("") : TEXT("  \u00B7  "), MenuCargoNames[Index], Count);
		}
	}
	EXUi::SetText(CargoText, Cargo.IsEmpty() ? FString(TEXT("vazia (o hangar vende)")) : Cargo);
	EXUi::SetText(RiskText, EXUi::Thousands(EXEconomy::CargoValue(Profile)) + TEXT(" STARDUST"));
	const FString LastRun = Profile->Expeditions == 0 ? FString(TEXT("nenhuma ainda"))
		: (Profile->LastReward >= 0 ? FString::Printf(TEXT("+%s STARDUST"), *EXUi::Thousands(Profile->LastReward))
			: FString::Printf(TEXT("carga perdida (%s)"), *EXUi::Thousands(Profile->LastReward)));
	if (LastRunText && !LastRunText->GetText().ToString().Equals(LastRun))
	{
		LastRunText->SetText(FText::FromString(LastRun));
		LastRunText->SetColorAndOpacity(FSlateColor(Profile->Expeditions == 0 ? EXUi::Sand() : (Profile->LastReward >= 0 ? EXUi::Ok() : EXUi::Rust())));
	}
}

int32 UEXMainMenuWidget::ItemUnder(const FPointerEvent& MouseEvent) const
{
	// Screen space on both sides (the mouse and the lines' last geometry).
	const double MouseX = MouseEvent.GetScreenSpacePosition().X;
	const double MouseY = MouseEvent.GetScreenSpacePosition().Y;
	for (int32 Index = 0; Index < ItemRoots.Num(); ++Index)
	{
		if (!ItemRoots[Index])
		{
			continue;
		}
		const FGeometry& Geometry = ItemRoots[Index]->GetCachedGeometry();
		const double Left = Geometry.GetAbsolutePosition().X;
		const double Top = Geometry.GetAbsolutePosition().Y;
		if (MouseX >= Left && MouseY >= Top && MouseX < Left + Geometry.GetAbsoluteSize().X && MouseY < Top + Geometry.GetAbsoluteSize().Y)
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

FReply UEXMainMenuWidget::NativeOnMouseMove(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent)
{
	// The line under the mouse lights up (once per line entered, so W/S still move the highlight).
	const int32 Index = ItemUnder(InMouseEvent);
	if (Index != HoveredItem)
	{
		HoveredItem = Index;
		if (Index != INDEX_NONE && RaceDirector)
		{
			RaceDirector->HoverMenuChoice(Index);
		}
	}
	return Super::NativeOnMouseMove(InGeometry, InMouseEvent);
}

FReply UEXMainMenuWidget::NativeOnMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent)
{
	if (InMouseEvent.GetEffectingButton() == EKeys::LeftMouseButton)
	{
		const int32 Index = ItemUnder(InMouseEvent);
		if (Index != INDEX_NONE && RaceDirector)
		{
			RaceDirector->StartMenuChoice(Index);
		}
	}
	// The keys keep going to the game (W/S, Enter, Tab): the game viewport keeps the focus.
	if (FSlateApplication::IsInitialized())
	{
		FSlateApplication::Get().SetAllUserFocusToGameViewport();
	}
	return FReply::Handled();
}

AEXHoverCraft* UEXMainMenuWidget::GetPlayerCraft() const
{
	return Cast<AEXHoverCraft>(GetOwningPlayerPawn());
}
