#include "UI/EXResultsWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Flight/EXHoverCraft.h"
#include "Race/EXRaceDirector.h"
#include "UI/EXUiStyle.h"

namespace
{
	constexpr int32 MaxCards = 6;
	constexpr int32 MaxRows = 16;

	FString ResultClock(float Seconds)
	{
		const int32 Minutes = FMath::FloorToInt(Seconds / 60.0f);
		return FString::Printf(TEXT("%d:%04.1f"), Minutes, Seconds - Minutes * 60.0f).Replace(TEXT("."), TEXT(","));
	}

	FString Km(float Metres)
	{
		return FString::Printf(TEXT("%.1f km"), Metres / 1000.0f).Replace(TEXT("."), TEXT(","));
	}

	/** The verdict's colour: green (EXTRACTED), red (DESTROYED), amber (STRANDED). */
	FLinearColor VerdictColour(uint8 State)
	{
		return State == 1 ? EXUi::Hex(95, 230, 130) : (State == 2 ? EXUi::Hex(255, 70, 50) : EXUi::Hex(255, 180, 70));
	}

	/** A dark plate with a coloured bar on its left (the hangar's panels). */
	UWidget* ResultPlate(UWidgetTree* Tree, UWidget* Content, const FLinearColor& Bar, const FMargin& Padding)
	{
		UOverlay* Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		EXUi::AddO(Root, EXUi::Box(Tree, EXUi::Plate(0.9f)), HAlign_Fill, VAlign_Fill);
		EXUi::AddO(Root, Content, HAlign_Fill, VAlign_Fill, Padding);
		EXUi::AddO(Root, EXUi::Sized(Tree, 4.0f, 0.0f, EXUi::Box(Tree, Bar)), HAlign_Left, VAlign_Fill);
		return Root;
	}

	/** A small caption over a value (TEMPO 7:42,3). */
	UWidget* Stat(UWidgetTree* Tree, const FString& Caption, const FString& Value, const FLinearColor& Colour)
	{
		UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
		EXUi::AddV(Column, EXUi::WeightText(Tree, Caption, 10, EXUi::Sand(), 800, 200));
		EXUi::AddV(Column, EXUi::TitleText(Tree, Value, 22, Colour, 20), FMargin(0.0f, 4.0f, 0.0f, 0.0f));
		return Column;
	}

	/** One line of the ledger: what, then the amount on the right. */
	UWidget* LedgerLine(UWidgetTree* Tree, const FString& What, const FString& Amount, const FLinearColor& Colour, bool bTotal = false)
	{
		UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		EXUi::AddH(Line, EXUi::WeightText(Tree, What, bTotal ? 15 : 13, bTotal ? EXUi::Bone() : EXUi::Sand(), bTotal ? 800 : 600, bTotal ? 150 : 0),
			FMargin(0.0f), true, VAlign_Center);
		EXUi::AddH(Line, bTotal ? static_cast<UWidget*>(EXUi::TitleText(Tree, Amount, 26, Colour, 20)) : EXUi::WeightText(Tree, Amount, 14, Colour, 800),
			FMargin(16.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
		if (bTotal)
		{
			EXUi::AddH(Line, EXUi::GemImage(Tree, 14.0f), FMargin(8.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
		}
		return Line;
	}
}

void UEXResultsWidget::InitializeResults(AEXRaceDirector* InRaceDirector)
{
	RaceDirector = InRaceDirector;
	SetVisibility(ESlateVisibility::HitTestInvisible);
}

TSharedRef<SWidget> UEXResultsWidget::RebuildWidget()
{
	if (WidgetTree && !WidgetTree->RootWidget)
	{
		BuildTree();
	}
	return Super::RebuildWidget();
}

void UEXResultsWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	// The screen comes in: a short fade and a slide up.
	Age += InDeltaTime;
	if (Panel)
	{
		const float T = FMath::Clamp(Age / 0.45f, 0.0f, 1.0f);
		const float Ease = 1.0f - FMath::Square(1.0f - T);
		Panel->SetRenderOpacity(Ease);
		Panel->SetRenderTranslation(FVector2D(0.0f, 40.0f * (1.0f - Ease)));
	}
}

void UEXResultsWidget::BuildTree()
{
	UWidgetTree* Tree = WidgetTree;
	UOverlay* Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("ResultsRoot"));
	Tree->RootWidget = Root;
	if (!RaceDirector)
	{
		return;
	}
	const FEXRaceSummary& Summary = RaceDirector->GetSummary();
	const FLinearColor Colour = VerdictColour(Summary.State);
	EXUi::AddO(Root, EXUi::Box(Tree, EXUi::Ink(0.78f)), HAlign_Fill, VAlign_Fill);
	EXUi::AddO(Root, EXUi::Sized(Tree, 0.0f, 6.0f, EXUi::Box(Tree, Colour)), HAlign_Fill, VAlign_Top);

	UVerticalBox* Page = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* Columns = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	UVerticalBox* Left = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Left, BuildVerdict(Tree));
	EXUi::AddV(Left, BuildLedger(Tree), FMargin(0.0f, 26.0f, 0.0f, 0.0f));
	EXUi::AddH(Columns, EXUi::Sized(Tree, 600.0f, 0.0f, Left));
	EXUi::AddH(Columns, BuildPieces(Tree), FMargin(36.0f, 0.0f, 0.0f, 0.0f), true);
	EXUi::AddH(Columns, EXUi::Sized(Tree, 520.0f, 0.0f, BuildStandings(Tree)), FMargin(36.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddV(Page, Columns);
	UHorizontalBox* Keys = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Keys, EXUi::Hint(Tree, { TEXT("Enter"), TEXT("X") }, Summary.State == 1 ? TEXT("RECOLHER E CONTINUAR") : TEXT("CONTINUAR")));
	EXUi::AddV(Page, Keys, FMargin(0.0f, 30.0f, 0.0f, 0.0f), HAlign_Right);
	Panel = Page;
	Panel->SetRenderOpacity(0.0f);
	EXUi::AddO(Root, Page, HAlign_Fill, VAlign_Center, FMargin(70.0f, 40.0f));
}

UWidget* UEXResultsWidget::BuildVerdict(UWidgetTree* Tree)
{
	const FEXRaceSummary& Summary = RaceDirector->GetSummary();
	const FLinearColor Colour = VerdictColour(Summary.State);
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Column, EXUi::WeightText(Tree, TEXT("EXPEDIÇÃO  ·  RED DUST DIVIDE"), 11, EXUi::Rust(), 800, 300));
	const FString Title = Summary.State == 1 ? TEXT("EXTRAÍDO") : (Summary.State == 2 ? TEXT("DESTRUÍDO") : TEXT("ENCALHADO"));
	EXUi::AddV(Column, EXUi::OutlinedText(Tree, Title, 64, Colour, 80, 2, EXUi::Ink()), FMargin(0.0f, 6.0f, 0.0f, 0.0f));
	FString Sub;
	if (Summary.State == 1)
	{
		Sub = FString::Printf(TEXT("VITÓRIA  ·  %d.º DE %d"), Summary.Place, Summary.Field);
	}
	else if (Summary.State == 2)
	{
		Sub = FString::Printf(TEXT("DERROTA  ·  DESTRUÍDA AO KM %s"), *FString::Printf(TEXT("%.1f"), Summary.DistanceM / 1000.0f).Replace(TEXT("."), TEXT(",")));
	}
	else
	{
		Sub = FString::Printf(TEXT("A CAMINHO DE B  ·  %d.º DE %d"), Summary.Place, Summary.Field);
	}
	EXUi::AddV(Column, EXUi::TitleText(Tree, Sub, 18, EXUi::Bone(), 60), FMargin(0.0f, 2.0f, 0.0f, 0.0f));
	UHorizontalBox* Stats = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Stats, Stat(Tree, TEXT("TEMPO"), ResultClock(Summary.Time), EXUi::Bone()));
	EXUi::AddH(Stats, Stat(Tree, TEXT("CHECKPOINTS"), FString::Printf(TEXT("%d / %d"), Summary.Checkpoints, Summary.CheckpointCount),
		Summary.Checkpoints >= Summary.CheckpointCount ? EXUi::Ok() : EXUi::Bone()), FMargin(40.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddH(Stats, Stat(Tree, TEXT("DISTÂNCIA"), Km(Summary.DistanceM), EXUi::Bone()), FMargin(40.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddV(Column, Stats, FMargin(0.0f, 22.0f, 0.0f, 0.0f));
	return Column;
}

UWidget* UEXResultsWidget::BuildLedger(UWidgetTree* Tree)
{
	const FEXRaceSummary& Summary = RaceDirector->GetSummary();
	UVerticalBox* Lines = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	const FLinearColor Gain = EXUi::Ok();
	const FLinearColor Loss = EXUi::Hex(255, 90, 70);
	auto Add = [&](UWidget* Line, float Top = 10.0f) { EXUi::AddV(Lines, Line, FMargin(0.0f, Top, 0.0f, 0.0f)); };
	if (Summary.State == 1)
	{
		EXUi::AddV(Lines, EXUi::WeightText(Tree, TEXT("GANHOS"), 11, EXUi::Rust(), 800, 300));
		Add(LedgerLine(Tree, FString::Printf(TEXT("Lugar  ·  %d.º"), Summary.Place), FString::Printf(TEXT("+%s"), *EXUi::Thousands(Summary.PlaceReward)), Gain), 14.0f);
		Add(LedgerLine(Tree, TEXT("Bónus de extração"), FString::Printf(TEXT("+%s"), *EXUi::Thousands(Summary.ExtractBonus)), Gain));
		Add(LedgerLine(Tree, FString::Printf(TEXT("Checkpoints  ·  %d × %d%s"), Summary.Checkpoints, AEXRaceDirector::GetCheckpointPrize(),
			Summary.Checkpoints >= Summary.CheckpointCount ? TEXT("  +  todos") : TEXT("")), FString::Printf(TEXT("+%s"), *EXUi::Thousands(Summary.CheckpointReward)), Gain));
		if (Summary.FirstBonus > 0)
		{
			Add(LedgerLine(Tree, TEXT("Primeira extração"), FString::Printf(TEXT("+%s"), *EXUi::Thousands(Summary.FirstBonus)), Gain));
		}
		int32 WonValue = 0;
		for (const FEXItem& Item : Summary.Won)
		{
			WonValue += Item.Value;
		}
		if (WonValue > 0)
		{
			Add(LedgerLine(Tree, FString::Printf(TEXT("Espólio  ·  %d peças (valor)"), Summary.Won.Num()), FString::Printf(TEXT("+%s"), *EXUi::Thousands(WonValue)),
				EXUi::Hex(255, 200, 80)));
		}
		Add(EXUi::Sized(Tree, 0.0f, 1.0f, EXUi::Box(Tree, EXUi::Bone(0.15f))), 14.0f);
		Add(LedgerLine(Tree, TEXT("TOTAL EM STARDUST"), FString::Printf(TEXT("+%s"), *EXUi::Thousands(Summary.Total)), Gain, true), 12.0f);
	}
	else
	{
		EXUi::AddV(Lines, EXUi::WeightText(Tree, Summary.State == 2 ? TEXT("PERDAS") : TEXT("SEM GANHOS NEM PERDAS"), 11, Summary.State == 2 ? Loss : EXUi::Rust(), 800, 300));
		int32 LostValue = 0;
		for (const FEXItem& Item : Summary.Lost)
		{
			LostValue += Item.Value;
		}
		if (Summary.State == 2)
		{
			Add(LedgerLine(Tree, FString::Printf(TEXT("Peças para o espólio  ·  %d"), Summary.Lost.Num()), FString::Printf(TEXT("-%s"), *EXUi::Thousands(LostValue)), Loss), 14.0f);
			Add(LedgerLine(Tree, TEXT("Consumíveis levados"), TEXT("perdidos"), Loss));
			Add(LedgerLine(Tree, FString::Printf(TEXT("Checkpoints  ·  %d / %d"), Summary.Checkpoints, Summary.CheckpointCount), TEXT("só pagam na extração"), EXUi::Sand()));
		}
		else
		{
			Add(LedgerLine(Tree, TEXT("Ficas com tudo o que levaste"), TEXT("0"), EXUi::Bone()), 14.0f);
			Add(LedgerLine(Tree, TEXT("Os checkpoints só pagam na extração"), FString::Printf(TEXT("%d / %d"), Summary.Checkpoints, Summary.CheckpointCount), EXUi::Sand()));
		}
		Add(EXUi::Sized(Tree, 0.0f, 1.0f, EXUi::Box(Tree, EXUi::Bone(0.15f))), 14.0f);
		Add(LedgerLine(Tree, TEXT("TOTAL EM STARDUST"), Summary.State == 2 ? FString::Printf(TEXT("-%s"), *EXUi::Thousands(LostValue)) : FString(TEXT("0")),
			Summary.State == 2 ? Loss : EXUi::Bone(), true), 12.0f);
	}
	return ResultPlate(Tree, Lines, Summary.State == 1 ? EXUi::Ok() : (Summary.State == 2 ? Loss : EXUi::Rust()), FMargin(26.0f, 20.0f, 26.0f, 22.0f));
}

UWidget* UEXResultsWidget::MakeCard(UWidgetTree* Tree, const FEXItem& Item, bool bLost, bool bSaved)
{
	// A module card: the rarity's band on top, the family icon, the rarity, the name and the value; lost ones in red.
	const EEXRarity Rarity = static_cast<EEXRarity>(Item.Rarity);
	const FLinearColor RarityColour = EXMeta::RarityColour(Rarity);
	const EXMeta::FModuleDef* Def = EXMeta::Find(Item);
	UOverlay* Card = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Card, EXUi::Box(Tree, bLost ? EXUi::Hex(60, 14, 10, 0.92f) : EXUi::Plate(0.95f)), HAlign_Fill, VAlign_Fill);
	EXUi::AddO(Card, EXUi::Glow(Tree, FLinearColor(RarityColour.R, RarityColour.G, RarityColour.B, bLost ? 0.12f : 0.25f)), HAlign_Fill, VAlign_Fill);
	EXUi::AddO(Card, EXUi::Sized(Tree, 0.0f, 6.0f, EXUi::Box(Tree, bLost ? EXUi::Hex(255, 70, 50) : RarityColour)), HAlign_Fill, VAlign_Top);
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UTexture2D* Icon = Def ? EXUi::Icon(FString::Printf(TEXT("fam_%d"), static_cast<int32>(Def->Family))) : nullptr;
	EXUi::AddV(Column, EXUi::Sized(Tree, 64.0f, 64.0f, EXUi::Image(Tree, Icon, bLost ? EXUi::Bone(0.45f) : RarityColour)), FMargin(0.0f, 4.0f, 0.0f, 0.0f), HAlign_Center);
	EXUi::AddV(Column, EXUi::WeightText(Tree, EXMeta::RarityName(Rarity).ToUpper(), 10, RarityColour, 800, 200), FMargin(0.0f, 10.0f, 0.0f, 0.0f), HAlign_Center);
	UTextBlock* Name = EXUi::WeightText(Tree, EXMeta::ItemLabel(Item), 13, EXUi::Bone(), 700);
	Name->SetAutoWrapText(true);
	Name->SetJustification(ETextJustify::Center);
	EXUi::AddV(Column, Name, FMargin(0.0f, 4.0f, 0.0f, 0.0f), HAlign_Center);
	EXUi::AddV(Column, EXUi::WeightText(Tree, FString::Printf(TEXT("%s%s"), bLost ? TEXT("-") : TEXT(""), *EXUi::Thousands(Item.Value)), 14,
		bLost ? EXUi::Hex(255, 90, 70) : EXUi::Hex(255, 200, 80), 800), FMargin(0.0f, 8.0f, 0.0f, 0.0f), HAlign_Center);
	const FString Tag = bLost ? TEXT("PERDIDA") : (bSaved ? TEXT("SEGURA  ·  FICOU CONTIGO") : TEXT("NOVA"));
	EXUi::AddV(Column, EXUi::Box(Tree, bLost ? EXUi::Hex(255, 70, 50, 0.85f) : (bSaved ? EXUi::Hex(80, 230, 255, 0.8f) : EXUi::Rust(0.9f)), FMargin(10.0f, 3.0f),
		EXUi::WeightText(Tree, Tag, 9, EXUi::Ink(), 800, 150)), FMargin(0.0f, 10.0f, 0.0f, 0.0f), HAlign_Center);
	EXUi::AddO(Card, Column, HAlign_Fill, VAlign_Fill, FMargin(14.0f, 18.0f, 14.0f, 14.0f));
	return EXUi::Sized(Tree, 196.0f, 250.0f, Card);
}

UWidget* UEXResultsWidget::BuildPieces(UWidgetTree* Tree)
{
	const FEXRaceSummary& Summary = RaceDirector->GetSummary();
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	const bool bWon = Summary.State == 1;
	EXUi::AddV(Column, EXUi::WeightText(Tree, bWon ? TEXT("ESPÓLIO GANHO") : (Summary.State == 2 ? TEXT("PEÇAS PERDIDAS PARA O ESPÓLIO") : TEXT("AS TUAS PEÇAS")),
		11, bWon ? EXUi::Hex(255, 200, 80) : EXUi::Hex(255, 90, 70), 800, 300));
	TArray<TPair<FEXItem, int32>> Cards;   // 0 won, 1 lost, 2 insured and kept
	for (const FEXItem& Item : bWon ? Summary.Won : Summary.Lost)
	{
		Cards.Add(TPair<FEXItem, int32>(Item, bWon ? 0 : 1));
	}
	if (Summary.Saved.IsValid())
	{
		Cards.Add(TPair<FEXItem, int32>(Summary.Saved, 2));
	}
	if (Cards.Num() == 0)
	{
		const FString None = bWon ? TEXT("Ninguém foi destruído: o espólio ficou vazio.") : TEXT("Nenhuma peça mudou de mãos.");
		EXUi::AddV(Column, EXUi::WeightText(Tree, None, 14, EXUi::Sand(), 600), FMargin(0.0f, 18.0f, 0.0f, 0.0f));
		return Column;
	}
	UHorizontalBox* Row = nullptr;
	for (int32 Index = 0; Index < FMath::Min(Cards.Num(), MaxCards); ++Index)
	{
		if (Index % 3 == 0)
		{
			Row = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
			EXUi::AddV(Column, Row, FMargin(0.0f, 16.0f, 0.0f, 0.0f), HAlign_Left);
		}
		EXUi::AddH(Row, MakeCard(Tree, Cards[Index].Key, Cards[Index].Value == 1, Cards[Index].Value == 2), FMargin(Index % 3 > 0 ? 16.0f : 0.0f, 0.0f, 0.0f, 0.0f));
	}
	if (Cards.Num() > MaxCards)
	{
		EXUi::AddV(Column, EXUi::WeightText(Tree, FString::Printf(TEXT("+ %d peças no Cofre"), Cards.Num() - MaxCards), 12, EXUi::Sand(), 700), FMargin(0.0f, 10.0f, 0.0f, 0.0f));
	}
	if (Summary.PoolValue > 0)
	{
		EXUi::AddV(Column, EXUi::WeightText(Tree, FString::Printf(TEXT("Espólio da expedição: %s STARDUST em peças dos destruídos, repartido por quem extraiu"),
			*EXUi::Thousands(Summary.PoolValue)), 11, EXUi::Sand(), 600), FMargin(0.0f, 14.0f, 0.0f, 0.0f));
	}
	return Column;
}

UWidget* UEXResultsWidget::BuildStandings(UWidgetTree* Tree)
{
	UVerticalBox* Lines = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Lines, EXUi::WeightText(Tree, TEXT("CLASSIFICAÇÃO"), 11, EXUi::Rust(), 800, 300));
	const TArray<FEXRacer>& Standings = RaceDirector->GetStandings();
	for (int32 Place = 0; Place < FMath::Min(Standings.Num(), MaxRows); ++Place)
	{
		const FEXRacer& Racer = Standings[Place];
		const uint8 State = Racer.State;
		const FLinearColor Colour = Racer.bPlayer ? EXUi::Hex(80, 230, 255) : (State == 2 ? EXUi::Hex(255, 90, 70) : (State == 1 ? EXUi::Bone() : EXUi::Sand()));
		UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		EXUi::AddH(Line, EXUi::Sized(Tree, 34.0f, 0.0f, EXUi::TitleText(Tree, FString::FromInt(Place + 1), 14, Colour)), FMargin(0.0f), false, VAlign_Center);
		EXUi::AddH(Line, EXUi::WeightText(Tree, Racer.bPlayer ? TEXT("TU") : Racer.Name, 13, Colour, Racer.bPlayer ? 800 : 600), FMargin(6.0f, 0.0f, 0.0f, 0.0f), true, VAlign_Center);
		const FString Result = State == 1 ? (Racer.bProjected ? FString::Printf(TEXT("~%s"), *ResultClock(Racer.FinishTime)) : ResultClock(Racer.FinishTime))
			: (State == 2 ? FString::Printf(TEXT("km %s"), *FString::Printf(TEXT("%.1f"), Racer.OutAtM / 1000.0f).Replace(TEXT("."), TEXT(","))) : FString(TEXT("a caminho")));
		EXUi::AddH(Line, EXUi::Sized(Tree, 96.0f, 0.0f, EXUi::WeightText(Tree, Result, 12, Colour, 700)), FMargin(8.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
		const FString Tag = State == 1 ? TEXT("EXTRAÍDO") : (State == 2 ? TEXT("DESTRUÍDO") : TEXT("ENCALHADO"));
		EXUi::AddH(Line, EXUi::Sized(Tree, 92.0f, 0.0f, EXUi::WeightText(Tree, Tag, 10, State == 2 ? EXUi::Hex(255, 90, 70) : (State == 1 ? EXUi::Ok() : EXUi::Sand()), 800, 100)),
			FMargin(8.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
		const FString Money = State == 1 ? FString::Printf(TEXT("+%s"), *EXUi::Thousands(Racer.Reward)) : (State == 2 && Racer.LostValue > 0 ? FString::Printf(TEXT("-%s"), *EXUi::Thousands(Racer.LostValue)) : FString());
		EXUi::AddH(Line, EXUi::Sized(Tree, 70.0f, 0.0f, EXUi::WeightText(Tree, Money, 12, State == 2 ? EXUi::Hex(255, 90, 70) : EXUi::Hex(255, 200, 80), 800)),
			FMargin(8.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
		UWidget* Row = Racer.bPlayer ? static_cast<UWidget*>(EXUi::Box(Tree, EXUi::Hex(80, 230, 255, 0.12f), FMargin(8.0f, 4.0f), Line))
			: static_cast<UWidget*>(EXUi::Box(Tree, EXUi::Ink(0.0f), FMargin(8.0f, 4.0f), Line));
		EXUi::AddV(Lines, Row, FMargin(0.0f, Place == 0 ? 12.0f : 2.0f, 0.0f, 0.0f));
	}
	return ResultPlate(Tree, Lines, EXUi::Rust(), FMargin(22.0f, 18.0f, 18.0f, 18.0f));
}
