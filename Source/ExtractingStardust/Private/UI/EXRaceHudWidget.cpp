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
	auto MakeSlot = [&](int32 Slot) -> UWidget*
	{
		UOverlay* Tile = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		Slots[Slot].Fill = EXUi::Box(Tree, EXUi::Hex(30, 18, 12, 0.72f));
		EXUi::AddO(Tile, Slots[Slot].Fill, HAlign_Fill, VAlign_Fill);
		const EXUi::FFrame Key = EXUi::Frame(Tree, EXUi::Bone(0.8f), EXUi::Ink(0.0f), 1.0f, FMargin(0.0f));
		Key.Fill->SetContent(EXUi::WeightText(Tree, FString::FromInt(Slot + 1), 10, EXUi::Bone(), 800));
		Key.Fill->SetHorizontalAlignment(HAlign_Center);
		Key.Fill->SetVerticalAlignment(VAlign_Center);
		EXUi::AddO(Tile, EXUi::Sized(Tree, 20.0f, 20.0f, Key.Root), HAlign_Left, VAlign_Top, FMargin(8.0f));
		EXUi::AddO(Tile, EXUi::WeightText(Tree, HudArrows[Slot], 10, EXUi::Rust(), 700), HAlign_Right, VAlign_Top, FMargin(0.0f, 7.0f, 9.0f, 0.0f));
		UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
		Slots[Slot].Icon = EXUi::Image(Tree, nullptr);
		EXUi::AddV(Column, EXUi::Sized(Tree, 34.0f, 34.0f, Slots[Slot].Icon), FMargin(0.0f), HAlign_Center);
		Slots[Slot].Count = EXUi::WeightText(Tree, TEXT(""), 11, EXUi::Bone(), 800);
		EXUi::AddV(Column, Slots[Slot].Count, FMargin(0.0f, 6.0f, 0.0f, 0.0f), HAlign_Center);
		EXUi::AddO(Tile, Column, HAlign_Center, VAlign_Center, FMargin(0.0f, 10.0f, 0.0f, 0.0f));
		const EXUi::FFrame Edges = EXUi::Frame(Tree, EXUi::Bone(0.12f), EXUi::Ink(0.0f), 1.0f, FMargin(0.0f));
		for (int32 Side = 0; Side < 4; ++Side)
		{
			Slots[Slot].Edges[Side] = Edges.Edges[Side];
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
	for (int32 Slot = 0; Slot < 4; ++Slot)
	{
		const FEXQuickSlot Q = Quick.IsValidIndex(Slot) ? Quick[Slot] : FEXQuickSlot();
		const EXMeta::FConsumableDef& Def = EXMeta::Consumable(static_cast<EEXConsumable>(Q.Kind));
		const bool bHas = Q.Kind != 0 && Q.Count > 0;
		const bool bRecent = Craft->GetLastQuickSlot() == Slot && Now - Craft->GetLastQuickTime() < 0.8f;
		Slots[Slot].Fill->SetBrushColor(bRecent ? FLinearColor(Def.Colour.R, Def.Colour.G, Def.Colour.B, 0.3f) : EXUi::Hex(30, 18, 12, bHas ? 0.72f : 0.45f));
		for (UBorder* Edge : Slots[Slot].Edges)
		{
			Edge->SetBrushColor(bRecent ? Def.Colour : EXUi::Bone(0.12f));
		}
		EXUi::SetImage(Slots[Slot].Icon, Q.Kind != 0 ? EXUi::Icon(FString::Printf(TEXT("con_%s"), Def.Id)) : nullptr, bHas ? Def.Colour : EXUi::Bone(0.3f));
		EXUi::SetText(Slots[Slot].Count, Q.Kind != 0 ? FString::Printf(TEXT("×%d"), Q.Count) : FString(TEXT("vazio")));
	}
}
