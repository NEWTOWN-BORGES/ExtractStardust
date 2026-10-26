#include "UI/EXRaceHudWidget.h"

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
#include "Engine/World.h"
#include "Flight/EXHoverCraft.h"
#include "Game/EXProfile.h"
#include "Race/EXRaceDirector.h"
#include "UI/EXUiStyle.h"

// Sizes are the mock-up's (1600 x 900) times 1.2, fonts its pixels times 0.9 (as in UEXHangarWidget).
namespace
{
	constexpr float GaugeWidth = 248.0f;
	constexpr float BarWidth = 760.0f;       // the race bar along the top, A to B
	constexpr int32 MaxRivals = 24;
	constexpr int32 SpeedSegmentCount = 30;
	const TCHAR* const HudArrows[4] = { TEXT("▲"), TEXT("▼"), TEXT("◀"), TEXT("▶") };

	FString HudClock(float Seconds)
	{
		const int32 Minutes = FMath::FloorToInt(Seconds / 60.0f);
		return FString::Printf(TEXT("%02d:%04.1f"), Minutes, Seconds - Minutes * 60.0f);
	}

	/** A plate with the rust bar on one side (the mock-up's panels): fades towards the screen's middle. */
	UWidget* HudPlate(UWidgetTree* Tree, UWidget* Content, bool bBarLeft, const FMargin& Padding)
	{
		UOverlay* Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		EXUi::AddO(Root, EXUi::Fade(Tree, EXUi::Hex(30, 18, 12), bBarLeft ? 0.82f : 0.2f, bBarLeft ? 0.2f : 0.82f, 16), HAlign_Fill, VAlign_Fill);
		EXUi::AddO(Root, Content, HAlign_Fill, VAlign_Fill, Padding);
		EXUi::AddO(Root, EXUi::Sized(Tree, 4.0f, 0.0f, EXUi::Box(Tree, EXUi::Rust())), bBarLeft ? HAlign_Left : HAlign_Right, VAlign_Fill);
		return Root;
	}
}

void UEXRaceHudWidget::InitializeHud(AEXRaceDirector* InRaceDirector)
{
	RaceDirector = InRaceDirector;
	SetVisibility(ESlateVisibility::HitTestInvisible);
}

TSharedRef<SWidget> UEXRaceHudWidget::RebuildWidget()
{
	if (WidgetTree && !WidgetTree->RootWidget)
	{
		BuildTree();
	}
	return Super::RebuildWidget();
}

void UEXRaceHudWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	Refresh();
}

void UEXRaceHudWidget::BuildTree()
{
	UWidgetTree* Tree = WidgetTree;
	UOverlay* Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("RaceHudRoot"));
	Tree->RootWidget = Root;

	// Top left: "3 / 16", the time and the distance, the sector.
	UVerticalBox* Place = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* PlaceLine = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	PlaceText = EXUi::TitleText(Tree, TEXT("-"), 38, EXUi::Bone(), 20);
	EXUi::AddH(PlaceLine, PlaceText, FMargin(0.0f), false, VAlign_Bottom);
	FieldText = EXUi::TitleText(Tree, TEXT(""), 17, EXUi::Sand(), 20);
	EXUi::AddH(PlaceLine, FieldText, FMargin(10.0f, 0.0f, 0.0f, 5.0f), false, VAlign_Bottom);
	EXUi::AddV(Place, PlaceLine);
	ClockText = EXUi::WeightText(Tree, TEXT(""), 15, EXUi::Bone(), 700);
	EXUi::AddV(Place, ClockText, FMargin(0.0f, 4.0f, 0.0f, 0.0f));
	SectorText = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Rust(), 800, 200);
	EXUi::AddV(Place, SectorText, FMargin(0.0f, 6.0f, 0.0f, 0.0f));
	EXUi::AddO(Root, EXUi::Sized(Tree, 300.0f, 0.0f, HudPlate(Tree, Place, true, FMargin(22.0f, 12.0f, 18.0f, 12.0f))), HAlign_Left, VAlign_Top,
		FMargin(34.0f, 26.0f, 0.0f, 0.0f));

	// Top right: VIDAS and the diamonds, EM RISCO.
	UVerticalBox* Lives = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	EXUi::AddV(Lives, EXUi::WeightText(Tree, TEXT("VIDAS"), 11, EXUi::Rust(), 800, 200), FMargin(0.0f), HAlign_Right);
	UHorizontalBox* Pips = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	for (int32 Index = 0; Index < 6; ++Index)
	{
		LifePips[Index] = EXUi::Box(Tree, EXUi::Ok());
		USizeBox* Pip = EXUi::Sized(Tree, 19.0f, 19.0f, LifePips[Index]);
		Pip->SetRenderTransformAngle(45.0f);
		EXUi::AddH(Pips, Pip, FMargin(Index > 0 ? 9.0f : 0.0f, 0.0f, 0.0f, 0.0f));
	}
	EXUi::AddV(Lives, Pips, FMargin(0.0f, 9.0f, 4.0f, 8.0f), HAlign_Right);
	UHorizontalBox* Risk = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	RiskText = EXUi::WeightText(Tree, TEXT(""), 11, EXUi::Bone(), 800, 120);
	EXUi::AddH(Risk, RiskText);
	EXUi::AddH(Risk, EXUi::GemImage(Tree, 9.0f), FMargin(5.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddV(Lives, Risk, FMargin(0.0f), HAlign_Right);
	EXUi::AddO(Root, EXUi::Sized(Tree, 190.0f, 0.0f, HudPlate(Tree, Lives, false, FMargin(16.0f, 12.0f, 20.0f, 12.0f))), HAlign_Right, VAlign_Top,
		FMargin(0.0f, 26.0f, 34.0f, 0.0f));

	// Bottom left: the speed in Orbitron, KM/H, then the nitro, the heat and the fuel.
	UVerticalBox* Speed = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* SpeedLine = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	SpeedText = EXUi::TitleText(Tree, TEXT("0"), 58, EXUi::Bone(), 0);
	EXUi::AddH(SpeedLine, SpeedText, FMargin(0.0f), false, VAlign_Bottom);
	EXUi::AddH(SpeedLine, EXUi::TitleText(Tree, TEXT("KM/H"), 14, EXUi::Sand(), 80), FMargin(10.0f, 0.0f, 0.0f, 10.0f), false, VAlign_Bottom);
	EXUi::AddV(Speed, SpeedLine);
	UHorizontalBox* Segments = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	for (int32 Index = 0; Index < SpeedSegmentCount; ++Index)
	{
		UBorder* Segment = EXUi::Box(Tree, EXUi::Bone(0.12f));
		SpeedSegments.Add(Segment);
		EXUi::AddH(Segments, EXUi::Sized(Tree, 11.0f, 9.0f + Index * 0.35f, Segment), FMargin(Index > 0 ? 3.0f : 0.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Bottom);
	}
	EXUi::AddV(Speed, Segments, FMargin(0.0f, 4.0f, 0.0f, 2.0f), HAlign_Left);
	const TCHAR* const Names[3] = { TEXT("NITRO"), TEXT("CALOR"), TEXT("COMBUSTÍVEL") };
	for (int32 Index = 0; Index < 3; ++Index)
	{
		UHorizontalBox* Row = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		EXUi::AddH(Row, EXUi::Sized(Tree, 144.0f, 0.0f, EXUi::WeightText(Tree, Names[Index], 10, EXUi::Sand(), 800, 160)));
		UOverlay* Track = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		EXUi::AddO(Track, EXUi::Sized(Tree, GaugeWidth, 10.0f, EXUi::Box(Tree, EXUi::Bone(0.12f))), HAlign_Left, VAlign_Center);
		Gauges[Index].Colour = EXUi::Box(Tree, EXUi::Rust());
		Gauges[Index].Fill = EXUi::Sized(Tree, 10.0f, 10.0f, Gauges[Index].Colour);
		EXUi::AddO(Track, Gauges[Index].Fill, HAlign_Left, VAlign_Center);
		EXUi::AddH(Row, Track);
		Gauges[Index].Value = EXUi::WeightText(Tree, TEXT(""), 12, EXUi::Bone(), 800);
		EXUi::AddH(Row, EXUi::Sized(Tree, 70.0f, 0.0f, Gauges[Index].Value), FMargin(14.0f, 0.0f, 0.0f, 0.0f));
		EXUi::AddV(Speed, Row, FMargin(0.0f, Index == 0 ? 10.0f : 9.0f, 0.0f, 0.0f));
	}
	EXUi::AddO(Root, EXUi::Sized(Tree, 504.0f, 0.0f, HudPlate(Tree, Speed, true, FMargin(22.0f, 10.0f, 18.0f, 14.0f))), HAlign_Left, VAlign_Bottom,
		FMargin(41.0f, 0.0f, 0.0f, 41.0f));

	// Bottom right: the four quick slots round the d-pad (1 up, 2 down, 3 left, 4 right), key, arrow, icon, count.
	UVerticalBox* Cross = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	auto MakeSlot = [&](int32 QuickIndex) -> UWidget*
	{
		UOverlay* Tile = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		Slots[QuickIndex].Fill = EXUi::Box(Tree, EXUi::Hex(30, 18, 12, 0.72f));
		EXUi::AddO(Tile, Slots[QuickIndex].Fill, HAlign_Fill, VAlign_Fill);
		const EXUi::FFrame Key = EXUi::Frame(Tree, EXUi::Bone(0.8f), EXUi::Ink(0.0f), 1.0f, FMargin(0.0f));
		Key.Fill->SetContent(EXUi::WeightText(Tree, FString::FromInt(QuickIndex + 1), 10, EXUi::Bone(), 800));
		Key.Fill->SetHorizontalAlignment(HAlign_Center);
		Key.Fill->SetVerticalAlignment(VAlign_Center);
		EXUi::AddO(Tile, EXUi::Sized(Tree, 20.0f, 20.0f, Key.Root), HAlign_Left, VAlign_Top, FMargin(8.0f));
		EXUi::AddO(Tile, EXUi::WeightText(Tree, HudArrows[QuickIndex], 10, EXUi::Rust(), 700), HAlign_Right, VAlign_Top, FMargin(0.0f, 7.0f, 9.0f, 0.0f));
		UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
		Slots[QuickIndex].Icon = EXUi::Image(Tree, nullptr);
		EXUi::AddV(Column, EXUi::Sized(Tree, 34.0f, 34.0f, Slots[QuickIndex].Icon), FMargin(0.0f), HAlign_Center);
		Slots[QuickIndex].Count = EXUi::WeightText(Tree, TEXT(""), 11, EXUi::Bone(), 800);
		EXUi::AddV(Column, Slots[QuickIndex].Count, FMargin(0.0f, 6.0f, 0.0f, 0.0f), HAlign_Center);
		EXUi::AddO(Tile, Column, HAlign_Center, VAlign_Center, FMargin(0.0f, 10.0f, 0.0f, 0.0f));
		const EXUi::FFrame Edges = EXUi::Frame(Tree, EXUi::Bone(0.12f), EXUi::Ink(0.0f), 1.0f, FMargin(0.0f));
		for (int32 Side = 0; Side < 4; ++Side)
		{
			Slots[QuickIndex].Edges[Side] = Edges.Edges[Side];
		}
		EXUi::AddO(Tile, Edges.Root, HAlign_Fill, VAlign_Fill);
		return EXUi::Sized(Tree, 124.0f, 124.0f, Tile);
	};
	EXUi::AddV(Cross, MakeSlot(0), FMargin(0.0f), HAlign_Center);
	UHorizontalBox* Middle = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Middle, MakeSlot(2));
	EXUi::AddH(Middle, EXUi::Sized(Tree, 135.0f, 124.0f), FMargin(0.0f));
	EXUi::AddH(Middle, MakeSlot(3));
	EXUi::AddV(Cross, Middle, FMargin(0.0f, 11.0f, 0.0f, 11.0f));
	EXUi::AddV(Cross, MakeSlot(1), FMargin(0.0f), HAlign_Center);
	EXUi::AddO(Root, Cross, HAlign_Right, VAlign_Bottom, FMargin(0.0f, 0.0f, 48.0f, 36.0f));

	EXUi::AddO(Root, BuildProgressBar(Tree), HAlign_Center, VAlign_Top, FMargin(0.0f, 22.0f, 0.0f, 0.0f));
	EXUi::AddO(Root, BuildStartLights(Tree), HAlign_Center, VAlign_Center, FMargin(0.0f, 0.0f, 0.0f, 220.0f));
}

UWidget* UEXRaceHudWidget::BuildProgressBar(UWidgetTree* Tree)
{
	// A ---|---|---|--- B: the line from the start to the extraction point, a tick per checkpoint (lit once passed),
	// a dot per rival, the player's marker; under it the checkpoint count and the distance to B.
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Line, EXUi::TitleText(Tree, TEXT("A"), 15, EXUi::Bone(), 40), FMargin(0.0f, 0.0f, 12.0f, 0.0f), false, VAlign_Center);
	UOverlay* Track = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Track, EXUi::Sized(Tree, BarWidth, 22.0f), HAlign_Left, VAlign_Center);
	EXUi::AddO(Track, EXUi::Sized(Tree, BarWidth, 4.0f, EXUi::Box(Tree, EXUi::Bone(0.18f))), HAlign_Left, VAlign_Center);
	PassedFill = EXUi::Sized(Tree, 0.0f, 4.0f, EXUi::Box(Tree, EXUi::Rust()));
	PassedSlot = EXUi::AddO(Track, PassedFill, HAlign_Left, VAlign_Center);
	const int32 Count = RaceDirector ? RaceDirector->GetCheckpointCount() : 0;
	for (int32 Index = 1; Index < Count; ++Index)
	{
		UBorder* Tick = EXUi::Box(Tree, EXUi::Bone(0.35f));
		CheckpointTicks.Add(Tick);
		EXUi::AddO(Track, EXUi::Sized(Tree, 2.0f, 12.0f, Tick), HAlign_Left, VAlign_Center, FMargin(BarWidth * Index / Count - 1.0f, 0.0f, 0.0f, 0.0f));
	}
	for (int32 Index = 0; Index < MaxRivals; ++Index)
	{
		UBorder* Dot = EXUi::Box(Tree, EXUi::Bone(0.8f));
		USizeBox* DotBox = EXUi::Sized(Tree, 7.0f, 7.0f, Dot);
		DotBox->SetRenderTransformAngle(45.0f);
		RivalDots.Add(Dot);
		RivalSlots.Add(EXUi::AddO(Track, DotBox, HAlign_Left, VAlign_Center));
		DotBox->SetVisibility(ESlateVisibility::Collapsed);
	}
	UOverlay* Mark = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Mark, EXUi::Sized(Tree, 14.0f, 22.0f, EXUi::Box(Tree, EXUi::Hex(80, 230, 255, 0.25f))), HAlign_Center, VAlign_Center);
	EXUi::AddO(Mark, EXUi::Sized(Tree, 4.0f, 22.0f, EXUi::Box(Tree, EXUi::Hex(80, 230, 255))), HAlign_Center, VAlign_Center);
	PlayerMarkSlot = EXUi::AddO(Track, Mark, HAlign_Left, VAlign_Center);
	EXUi::AddH(Line, Track, FMargin(0.0f), false, VAlign_Center);
	EXUi::AddH(Line, EXUi::TitleText(Tree, TEXT("B"), 15, EXUi::Rust(), 40), FMargin(12.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
	EXUi::AddV(Column, Line, FMargin(0.0f), HAlign_Center);
	ProgressText = EXUi::WeightText(Tree, TEXT(""), 10, EXUi::Sand(), 800, 160);
	EXUi::AddV(Column, ProgressText, FMargin(0.0f, 2.0f, 0.0f, 0.0f), HAlign_Center);
	// The call-out when a checkpoint is passed: its number and what it pays on extraction.
	UHorizontalBox* Call = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	CheckpointCallText = EXUi::TitleText(Tree, TEXT(""), 24, EXUi::Bone(), 60);
	EXUi::AddH(Call, CheckpointCallText, FMargin(0.0f), false, VAlign_Center);
	CheckpointCallPrize = EXUi::WeightText(Tree, TEXT(""), 15, EXUi::Ok(), 800, 60);
	EXUi::AddH(Call, CheckpointCallPrize, FMargin(16.0f, 0.0f, 6.0f, 0.0f), false, VAlign_Center);
	EXUi::AddH(Call, EXUi::GemImage(Tree, 12.0f), FMargin(0.0f), false, VAlign_Center);
	CheckpointCall = Call;
	EXUi::AddV(Column, Call, FMargin(0.0f, 54.0f, 0.0f, 0.0f), HAlign_Center);
	return Column;
}

UWidget* UEXRaceHudWidget::BuildStartLights(UWidgetTree* Tree)
{
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* Gantry = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	for (int32 Index = 0; Index < 3; ++Index)
	{
		StartLights[Index] = EXUi::Box(Tree, EXUi::Ink(0.8f));
		const EXUi::FFrame Frame = EXUi::Frame(Tree, EXUi::Bone(0.35f), EXUi::Ink(0.0f), 2.0f, FMargin(6.0f));
		Frame.Fill->SetContent(StartLights[Index]);
		EXUi::AddH(Gantry, EXUi::Sized(Tree, 74.0f, 74.0f, Frame.Root), FMargin(Index > 0 ? 18.0f : 0.0f, 0.0f, 0.0f, 0.0f));
	}
	EXUi::AddV(Column, EXUi::Box(Tree, EXUi::Hex(16, 10, 6, 0.82f), FMargin(22.0f, 16.0f), Gantry), FMargin(0.0f), HAlign_Center);
	StartText = EXUi::OutlinedText(Tree, TEXT(""), 64, EXUi::Bone(), 60, 3, EXUi::Ink());
	EXUi::AddV(Column, StartText, FMargin(0.0f, 18.0f, 0.0f, 0.0f), HAlign_Center);
	StartPanel = Column;
	return Column;
}

void UEXRaceHudWidget::Refresh()
{
	const AEXHoverCraft* Craft = Cast<AEXHoverCraft>(GetOwningPlayerPawn());
	if (!Craft || !RaceDirector)
	{
		return;
	}
	const bool bBots = RaceDirector->GetMode() == EEXRaceMode::Bots;
	const int32 Field = RaceDirector->GetStandings().Num();
	EXUi::SetText(PlaceText, FString::FromInt(bBots ? RaceDirector->GetPlayerPlace() : 1));
	EXUi::SetText(FieldText, FString::Printf(TEXT("/ %d"), bBots ? Field : 1));
	const TArray<FVector2D>& Route = Craft->GetMapRoute();
	const float RouteKm = Route.Num() * 5.0f / 1000.0f;
	EXUi::SetText(ClockText, FString::Printf(TEXT("%s  ·  %.1f / %.0f km"), *HudClock(RaceDirector->GetRaceTime()), Craft->GetRouteIndex() * 5.0f / 1000.0f,
		RouteKm).Replace(TEXT("."), TEXT(",")));
	EXUi::SetText(SectorText, bBots ? FString(TEXT("PELOTÃO 15  ·  RED DUST DIVIDE")) : FString(TEXT("EXPEDIÇÃO SOLO  ·  RED DUST DIVIDE")));

	for (int32 Index = 0; Index < 6; ++Index)
	{
		LifePips[Index]->SetBrushColor(Index < Craft->GetLives() ? EXUi::Ok() : EXUi::Bone(0.14f));
		LifePips[Index]->GetParent()->SetVisibility(Index < Craft->GetMaxLives() ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	}
	const UEXProfileSave* Profile = Craft->GetProfile();
	EXUi::SetText(RiskText, FString::Printf(TEXT("EM RISCO %s"), *EXUi::Thousands(Profile ? EXEconomy::RiskValue(Profile, Craft->GetShipName()) : 0)));

	EXUi::SetText(SpeedText, FString::FromInt(FMath::RoundToInt(Craft->GetSpeedKmh())));
	// The speed bar: lit up to the speed, white, then orange near the top, cyan with the nitro.
	const float SpeedFrac = FMath::Clamp(Craft->GetSpeedKmh() / FMath::Max(1.0f, Craft->GetTopSpeedKmh()), 0.0f, 1.0f);
	const int32 Lit = FMath::RoundToInt(SpeedFrac * SpeedSegmentCount);
	for (int32 Index = 0; Index < SpeedSegments.Num(); ++Index)
	{
		const float At = static_cast<float>(Index) / SpeedSegmentCount;
		const FLinearColor On = Craft->IsBoosting() ? EXUi::Hex(80, 230, 255) : (At > 0.8f ? EXUi::RustHot() : (At > 0.6f ? EXUi::Hex(255, 200, 80) : EXUi::Bone()));
		SpeedSegments[Index]->SetBrushColor(Index < Lit ? On : EXUi::Bone(0.1f));
	}
	const float Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0f;
	const float Blink = 0.6f + 0.4f * FMath::Sin(Now * 10.0f);
	const float Values[3] = { Craft->GetNitro() * 100.0f, Craft->GetHeat(), Craft->GetFuel() };
	const FLinearColor Colours[3] = {
		EXUi::Rust(),
		Craft->IsOverheated() ? FLinearColor(1.0f, 0.15f * Blink, 0.08f) : FMath::Lerp(EXUi::Hex(255, 200, 80), EXUi::Hex(255, 70, 40), Craft->GetHeat() / 100.0f),
		Craft->GetFuel() < 15.0f ? EXUi::Hex(255, 80, 60) : EXUi::Hex(95, 209, 122),
	};
	for (int32 Index = 0; Index < 3; ++Index)
	{
		Gauges[Index].Fill->SetWidthOverride(GaugeWidth * FMath::Clamp(Values[Index] / 100.0f, 0.0f, 1.0f));
		Gauges[Index].Colour->SetBrushColor(Colours[Index]);
		EXUi::SetText(Gauges[Index].Value, Index == 2 ? FString::Printf(TEXT("%d%%"), FMath::RoundToInt(Values[Index])) : FString::FromInt(FMath::RoundToInt(Values[Index])));
	}

	const TArray<FEXQuickSlot>& Quick = Craft->GetQuickSlots();
	for (int32 QuickIndex = 0; QuickIndex < 4; ++QuickIndex)
	{
		const FEXQuickSlot Q = Quick.IsValidIndex(QuickIndex) ? Quick[QuickIndex] : FEXQuickSlot();
		const EXMeta::FConsumableDef& Def = EXMeta::Consumable(static_cast<EEXConsumable>(Q.Kind));
		const bool bHas = Q.Kind != 0 && Q.Count > 0;
		const bool bRecent = Craft->GetLastQuickSlot() == QuickIndex && Now - Craft->GetLastQuickTime() < 0.8f;
		Slots[QuickIndex].Fill->SetBrushColor(bRecent ? FLinearColor(Def.Colour.R, Def.Colour.G, Def.Colour.B, 0.3f) : EXUi::Hex(30, 18, 12, bHas ? 0.72f : 0.45f));
		for (UBorder* Edge : Slots[QuickIndex].Edges)
		{
			Edge->SetBrushColor(bRecent ? Def.Colour : EXUi::Bone(0.12f));
		}
		EXUi::SetImage(Slots[QuickIndex].Icon, Q.Kind != 0 ? EXUi::Icon(FString::Printf(TEXT("con_%s"), Def.Id)) : nullptr, bHas ? Def.Colour : EXUi::Bone(0.3f));
		EXUi::SetText(Slots[QuickIndex].Count, Q.Kind != 0 ? FString::Printf(TEXT("×%d"), Q.Count) : FString(TEXT("vazio")));
	}
	RefreshProgress(Craft);
	RefreshStart();
}

void UEXRaceHudWidget::RefreshProgress(const AEXHoverCraft* Craft)
{
	const float RouteM = FMath::Max(1.0f, RaceDirector->GetRouteLengthM());
	const float Mine = FMath::Clamp(Craft->GetRaceProgressM() / RouteM, 0.0f, 1.0f);
	PlayerMarkSlot->SetPadding(FMargin(BarWidth * Mine - 7.0f, 0.0f, 0.0f, 0.0f));
	PassedFill->SetWidthOverride(BarWidth * Mine);
	const int32 Passed = RaceDirector->GetPlayerCheckpoint();
	for (int32 Index = 0; Index < CheckpointTicks.Num(); ++Index)
	{
		CheckpointTicks[Index]->SetBrushColor(Index + 1 <= Passed ? EXUi::Rust() : EXUi::Bone(0.35f));
	}
	int32 Dot = 0;
	for (const FEXRacer& Racer : RaceDirector->GetStandings())
	{
		if (Racer.bPlayer || !IsValid(Racer.Craft) || Dot >= RivalSlots.Num())
		{
			continue;
		}
		const float At = Racer.bFinished ? 1.0f : FMath::Clamp((Racer.bOut ? Racer.OutAtM : Racer.Craft->GetRaceProgressM()) / RouteM, 0.0f, 1.0f);
		RivalSlots[Dot]->SetPadding(FMargin(BarWidth * At - 3.5f, 0.0f, 0.0f, 0.0f));
		RivalDots[Dot]->SetBrushColor(Racer.bOut ? EXUi::Hex(255, 80, 60, 0.6f) : EXUi::Bone(0.85f));
		RivalDots[Dot]->GetParent()->SetVisibility(ESlateVisibility::HitTestInvisible);
		++Dot;
	}
	for (; Dot < RivalSlots.Num(); ++Dot)
	{
		RivalDots[Dot]->GetParent()->SetVisibility(ESlateVisibility::Collapsed);
	}
	const float LeftKm = FMath::Max(0.0f, RouteM - Craft->GetRaceProgressM()) / 1000.0f;
	EXUi::SetText(ProgressText, FString::Printf(TEXT("CHECKPOINT %d / %d   \u00B7   %s KM PARA B"), Passed, RaceDirector->GetCheckpointCount(),
		*FString::Printf(TEXT("%.1f"), LeftKm).Replace(TEXT("."), TEXT(","))));
	// The call-out: 2.4 s after each checkpoint, fading.
	const float Since = RaceDirector->GetRaceTime() - RaceDirector->GetLastCheckpointTime();
	const bool bCall = Since >= 0.0f && Since < 2.4f && Passed > 0 && !RaceDirector->IsOver();
	CheckpointCall->SetVisibility(bCall ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	if (bCall)
	{
		CheckpointCall->SetRenderOpacity(FMath::Clamp((2.4f - Since) / 0.6f, 0.0f, 1.0f));
		const bool bLast = Passed >= RaceDirector->GetCheckpointCount();
		EXUi::SetText(CheckpointCallText, bLast ? FString(TEXT("EXTRA\u00C7\u00C3O")) : FString::Printf(TEXT("CHECKPOINT %d / %d"), Passed, RaceDirector->GetCheckpointCount()));
		EXUi::SetText(CheckpointCallPrize, FString::Printf(TEXT("+%d"), AEXRaceDirector::GetCheckpointPrize()));
	}
}

void UEXRaceHudWidget::RefreshStart()
{
	// 3 s: one red light per second; then all green and PARTIDA! for a moment.
	const float Countdown = RaceDirector->GetCountdown();
	const bool bGo = Countdown <= 0.0f && RaceDirector->GetRaceTime() < 1.4f;
	StartPanel->SetVisibility(Countdown > 0.0f || bGo ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	if (Countdown <= 0.0f && !bGo)
	{
		return;
	}
	const int32 Count = FMath::CeilToInt(Countdown - 1.0f);   // 3, 2, 1, then 0
	for (int32 Index = 0; Index < 3; ++Index)
	{
		const bool bRed = !bGo && Count > 0 && Index < 4 - Count;
		StartLights[Index]->SetBrushColor(bGo ? EXUi::Hex(70, 235, 110) : (bRed ? EXUi::Hex(255, 45, 30) : EXUi::Ink(0.8f)));
	}
	EXUi::SetText(StartText, bGo || Count <= 0 ? FString(TEXT("PARTIDA!")) : FString::FromInt(Count));
	StartText->SetColorAndOpacity(FSlateColor(bGo || Count <= 0 ? EXUi::Hex(70, 235, 110) : EXUi::Bone()));
}
