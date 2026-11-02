#include "UI/EXRaceHudWidget.h"

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
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "Flight/EXHoverCraft.h"
#include "Game/EXMeta.h"
#include "Game/EXProfile.h"
#include "Race/EXRaceDirector.h"
#include "UI/EXRouteMapWidget.h"
#include "UI/EXUiStyle.h"

// Sizes are Slate units at 1920 x 1080 (UMG scales them with the screen). The look is the player's concept: navy
// plates with glowing cyan edges (Scripts/make_hud_art.py: T_Icon_hud_*), Orbitron figures leaning forward, Inter labels.
namespace
{
	constexpr float BarWidth = 620.0f;           // the race bar, A to B
	constexpr int32 MaxRivals = 24;
	constexpr int32 BoostSegmentCount = 10;
	constexpr float MapSize = 300.0f;
	constexpr float MapWindowM = 2400.0f;        // metres across the minimap
	constexpr float StatBarHeight = 46.0f;
	const TCHAR* const QuickArrows[4] = { TEXT("▲"), TEXT("▼"), TEXT("◀"), TEXT("▶") };

	FLinearColor Cyan(float A = 1.0f) { return EXUi::Hex(70, 220, 255, A); }
	FLinearColor CyanSoft(float A = 1.0f) { return EXUi::Hex(150, 225, 255, A); }
	FLinearColor Gold(float A = 1.0f) { return EXUi::Hex(255, 200, 60, A); }
	FLinearColor White(float A = 1.0f) { return EXUi::Hex(245, 250, 255, A); }
	FLinearColor Danger(float A = 1.0f) { return EXUi::Hex(255, 90, 40, A); }
	FLinearColor Navy(float A = 0.7f) { return EXUi::Hex(8, 18, 38, A); }

	/** Leans a widget forward, like the concept's italic figures. */
	void Italic(UWidget* Widget, float Degrees = -11.0f)
	{
		Widget->SetRenderTransform(FWidgetTransform(FVector2D::ZeroVector, FVector2D(1.0f, 1.0f), FVector2D(Degrees, 0.0f), 0.0f));
	}

	/** A figure: Orbitron, a dark outline for any background, leaning forward. */
	UTextBlock* Figure(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Colour, int32 Spacing = 0)
	{
		UTextBlock* Block = EXUi::TitleText(Tree, Value, Size, Colour, Spacing);
		FSlateFontInfo Font = EXUi::Orbitron(Size, Spacing);
		Font.OutlineSettings.OutlineSize = FMath::Max(1, Size / 18);
		Font.OutlineSettings.OutlineColor = EXUi::Hex(2, 8, 20, 0.9f);
		Block->SetFont(Font);
		Italic(Block);
		return Block;
	}

	/** A label: Inter extra bold, spaced, with a thin outline. */
	UTextBlock* Label(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Colour, int32 Spacing = 120, bool bLean = true)
	{
		UTextBlock* Block = EXUi::WeightText(Tree, Value, Size, Colour, 800, Spacing);
		FSlateFontInfo Font = EXUi::Inter(Size, 800, Spacing);
		Font.OutlineSettings.OutlineSize = 1;
		Font.OutlineSettings.OutlineColor = EXUi::Hex(2, 8, 20, 0.85f);
		Block->SetFont(Font);
		if (bLean)
		{
			Italic(Block, -8.0f);
		}
		return Block;
	}

	/** A piece of HUD art at a size; a plain navy box while the art is not imported. */
	UWidget* Art(UWidgetTree* Tree, const TCHAR* Name, float Width, float Height, const FLinearColor& Tint = FLinearColor::White)
	{
		if (UTexture2D* Texture = EXUi::Icon(Name))
		{
			return EXUi::Image(Tree, Texture, Tint, Width, Height);
		}
		return EXUi::Sized(Tree, Width, Height, EXUi::Box(Tree, Navy()));
	}

	/** A plate 9-sliced from its art at a scale (so the chamfers stay small and sharp at any size). */
	UWidget* Plate(UWidgetTree* Tree, const TCHAR* Name, float Scale = 0.5f, float Margin = 0.3f)
	{
		UTexture2D* Texture = EXUi::Icon(Name);
		if (!Texture)
		{
			return EXUi::Box(Tree, Navy());
		}
		UImage* Picture = Tree->ConstructWidget<UImage>(UImage::StaticClass());
		FSlateBrush Brush;
		Brush.SetResourceObject(Texture);
		Brush.ImageSize = FVector2D(Texture->GetSizeX(), Texture->GetSizeY()) * Scale;
		Brush.DrawAs = ESlateBrushDrawType::Box;
		Brush.Margin = FMargin(Margin);
		Picture->SetBrush(Brush);
		return Picture;
	}

	FString HudClock(float Seconds)
	{
		const int32 Minutes = FMath::FloorToInt(Seconds / 60.0f);
		const float Rest = Seconds - Minutes * 60.0f;
		const int32 Whole = FMath::FloorToInt(Rest);
		return FString::Printf(TEXT("%02d:%02d.%03d"), Minutes, Whole, FMath::Clamp(FMath::FloorToInt((Rest - Whole) * 1000.0f), 0, 999));
	}

	FString Km(float Metres)
	{
		return FString::Printf(TEXT("%.1f"), Metres / 1000.0f).Replace(TEXT("."), TEXT(","));
	}

	/** The piggy's animations (SourceArt/UI/Piggy/HD2x/Piggy_Spritesheet_HD2x.json; frames padded to multiples of 4):
	 *  file stem, frames, frame size, pivot at the feet, frames per second, loop. */
	struct FPiggyAnim
	{
		const TCHAR* File;
		int32 Frames;
		float W, H, PX, PY, Fps;
		bool bLoop;
	};
	enum EPiggy : int32 { PiggyIdle, PiggyBlink, PiggyCoins, PiggyJump, PiggyCelebrate, PiggyReaction, PiggyMove, PiggyTeleport };
	const FPiggyAnim PiggyAnims[8] = {
		{ TEXT("Idle"), 6, 956.0f, 892.0f, 478.0f, 812.0f, 8.0f, true },
		{ TEXT("Blink"), 4, 940.0f, 896.0f, 470.0f, 822.0f, 10.0f, false },
		{ TEXT("Receive_Coins"), 8, 952.0f, 1160.0f, 476.0f, 1068.0f, 12.0f, false },
		{ TEXT("Reward_Jump"), 4, 1504.0f, 1100.0f, 752.0f, 1056.0f, 10.0f, false },
		{ TEXT("Celebrate"), 6, 1088.0f, 1056.0f, 544.0f, 992.0f, 12.0f, true },
		{ TEXT("Reaction"), 12, 976.0f, 1056.0f, 488.0f, 998.0f, 0.0f, false },
		{ TEXT("Move"), 3, 1488.0f, 896.0f, 744.0f, 816.0f, 12.0f, true },
		{ TEXT("Teleport"), 3, 840.0f, 872.0f, 420.0f, 838.0f, 10.0f, false },
	};
	constexpr float PiggyBox = 196.0f;            // the piggy's square on the HUD
	constexpr float PiggyScale = 0.17f;           // HD frame pixels to HUD pixels (the idle pig ~162 px wide)
	constexpr int32 PiggyCrying = 7;              // REACTION frame: crying (the player is out)
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
	EXUi::AddO(Root, BuildPlace(Tree), HAlign_Left, VAlign_Top, FMargin(30.0f, 16.0f, 0.0f, 0.0f));
	EXUi::AddO(Root, BuildTimer(Tree), HAlign_Center, VAlign_Top, FMargin(0.0f, 12.0f, 0.0f, 0.0f));
	EXUi::AddO(Root, BuildSpoils(Tree), HAlign_Right, VAlign_Top, FMargin(0.0f, 8.0f, 26.0f, 0.0f));
	EXUi::AddO(Root, BuildMap(Tree), HAlign_Right, VAlign_Top, FMargin(0.0f, 214.0f, 26.0f, 0.0f));
	EXUi::AddO(Root, BuildWarning(Tree), HAlign_Left, VAlign_Center, FMargin(30.0f, 170.0f, 0.0f, 0.0f));
	EXUi::AddO(Root, BuildToast(Tree), HAlign_Right, VAlign_Center, FMargin(0.0f, 170.0f, 26.0f, 0.0f));
	EXUi::AddO(Root, BuildSlots(Tree), HAlign_Left, VAlign_Bottom, FMargin(30.0f, 0.0f, 0.0f, 20.0f));
	EXUi::AddO(Root, BuildSpeed(Tree), HAlign_Center, VAlign_Bottom, FMargin(0.0f, 0.0f, 0.0f, 10.0f));
	EXUi::AddO(Root, BuildStatus(Tree), HAlign_Right, VAlign_Bottom, FMargin(0.0f, 0.0f, 26.0f, 20.0f));
	EXUi::AddO(Root, BuildStartLights(Tree), HAlign_Center, VAlign_Center, FMargin(0.0f, 0.0f, 0.0f, 220.0f));
}

UWidget* UEXRaceHudWidget::BuildPlace(UWidgetTree* Tree)
{
	// The logo, then "1 / 16 POSIÇÃO" on a plate, then the standings (the player's row lit).
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	if (UTexture2D* Logo = EXUi::Icon(TEXT("ui_logo")))
	{
		EXUi::AddV(Column, EXUi::Image(Tree, Logo, FLinearColor::White, 246.0f, 72.0f), FMargin(0.0f, 0.0f, 0.0f, 6.0f), HAlign_Left);
	}
	UOverlay* Place = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Place, Plate(Tree, TEXT("hud_panel")), HAlign_Fill, VAlign_Fill);
	UVerticalBox* Inside = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	PlaceText = Figure(Tree, TEXT("1"), 62, Gold());
	EXUi::AddH(Line, PlaceText, FMargin(0.0f), false, VAlign_Bottom);
	FieldText = Figure(Tree, TEXT("/1"), 30, White());
	EXUi::AddH(Line, FieldText, FMargin(8.0f, 0.0f, 0.0f, 9.0f), false, VAlign_Bottom);
	EXUi::AddV(Inside, Line);
	PlaceLabel = Label(Tree, TEXT("POSIÇÃO"), 14, CyanSoft(), 220);
	EXUi::AddV(Inside, PlaceLabel, FMargin(4.0f, 0.0f, 0.0f, 0.0f));
	EXUi::AddO(Place, Inside, HAlign_Left, VAlign_Center, FMargin(26.0f, 4.0f, 18.0f, 10.0f));
	EXUi::AddV(Column, EXUi::Sized(Tree, 250.0f, 124.0f, Place), FMargin(0.0f), HAlign_Left);

	UVerticalBox* List = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	for (int32 Index = 0; Index < RowCount; ++Index)
	{
		FRowView& Row = Rows[Index];
		UOverlay* Back = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		UWidget* Quiet = Art(Tree, TEXT("hud_row"), 300.0f, 38.0f);
		UWidget* Me = Art(Tree, TEXT("hud_row_me"), 300.0f, 38.0f);
		Row.Back = Cast<UImage>(Quiet);
		Row.BackMe = Cast<UImage>(Me);
		EXUi::AddO(Back, Quiet, HAlign_Fill, VAlign_Fill);
		EXUi::AddO(Back, Me, HAlign_Fill, VAlign_Fill);
		UHorizontalBox* Cells = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		Row.Place = Figure(Tree, FString::FromInt(Index + 1), 18, White());
		EXUi::AddH(Cells, EXUi::Sized(Tree, 30.0f, 0.0f, Row.Place), FMargin(0.0f), false, VAlign_Center);
		Row.Ship = EXUi::Image(Tree, nullptr, FLinearColor::White, 34.0f, 34.0f);
		Row.Ship->SetRenderTransformAngle(90.0f);          // the blueprints have the nose up: point it down the road
		EXUi::AddH(Cells, EXUi::Sized(Tree, 34.0f, 34.0f, Row.Ship), FMargin(2.0f, 0.0f, 10.0f, 0.0f), false, VAlign_Center);
		Row.Name = Label(Tree, TEXT(""), 15, White(), 40);
		EXUi::AddH(Cells, Row.Name, FMargin(0.0f), true, VAlign_Center);
		Row.Tag = Label(Tree, TEXT(""), 10, Gold(), 80);
		EXUi::AddH(Cells, Row.Tag, FMargin(6.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
		EXUi::AddO(Back, Cells, HAlign_Fill, VAlign_Center, FMargin(10.0f, 0.0f, 30.0f, 0.0f));
		Row.Root = EXUi::Sized(Tree, 300.0f, 38.0f, Back);
		EXUi::AddV(List, Row.Root, FMargin(0.0f, 0.0f, 0.0f, 3.0f), HAlign_Left);
	}
	RowsBox = List;
	EXUi::AddV(Column, List, FMargin(0.0f, 10.0f, 0.0f, 0.0f), HAlign_Left);
	return Column;
}

UWidget* UEXRaceHudWidget::BuildTimer(UWidgetTree* Tree)
{
	// The clock on its plate, the checkpoint count on a tab under it (this game's "VOLTA 1/3"), then the race bar from
	// A to B: a tick per checkpoint, a dot per rival, the player's marker; the distance to B under it.
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UOverlay* Clock = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Clock, Art(Tree, TEXT("hud_timer"), 440.0f, 104.0f), HAlign_Fill, VAlign_Fill);
	UHorizontalBox* ClockLine = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(ClockLine, Art(Tree, TEXT("hud_stopwatch"), 44.0f, 44.0f), FMargin(0.0f, 0.0f, 14.0f, 0.0f), false, VAlign_Center);
	ClockText = Figure(Tree, TEXT("00:00.000"), 36, White());
	EXUi::AddH(ClockLine, ClockText, FMargin(0.0f), false, VAlign_Center);
	EXUi::AddO(Clock, ClockLine, HAlign_Center, VAlign_Center, FMargin(0.0f, 0.0f, 0.0f, 2.0f));
	EXUi::AddV(Column, EXUi::Sized(Tree, 440.0f, 104.0f, Clock), FMargin(0.0f), HAlign_Center);

	UOverlay* Tab = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	UWidget* TabArt = Art(Tree, TEXT("hud_tab"), 300.0f, 54.0f);
	CheckpointTab = Cast<UImage>(TabArt);
	EXUi::AddO(Tab, TabArt, HAlign_Fill, VAlign_Fill);
	CheckpointText = Label(Tree, TEXT(""), 16, CyanSoft(), 140);
	EXUi::AddO(Tab, CheckpointText, HAlign_Center, VAlign_Center, FMargin(0.0f, 0.0f, 0.0f, 3.0f));
	EXUi::AddV(Column, EXUi::Sized(Tree, 300.0f, 54.0f, Tab), FMargin(0.0f), HAlign_Center);

	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Line, Figure(Tree, TEXT("A"), 15, White()), FMargin(0.0f, 0.0f, 12.0f, 0.0f), false, VAlign_Center);
	UOverlay* Track = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Track, EXUi::Sized(Tree, BarWidth, 22.0f), HAlign_Left, VAlign_Center);
	EXUi::AddO(Track, EXUi::Sized(Tree, BarWidth, 6.0f, EXUi::Box(Tree, Navy(0.75f))), HAlign_Left, VAlign_Center);
	EXUi::AddO(Track, EXUi::Sized(Tree, BarWidth, 2.0f, EXUi::Box(Tree, Cyan(0.35f))), HAlign_Left, VAlign_Center);
	PassedFill = EXUi::Sized(Tree, 0.0f, 4.0f, EXUi::Box(Tree, Cyan()));
	EXUi::AddO(Track, PassedFill, HAlign_Left, VAlign_Center);
	const int32 Count = RaceDirector ? RaceDirector->GetCheckpointCount() : 0;
	for (int32 Index = 1; Index < Count; ++Index)
	{
		UBorder* Tick = EXUi::Box(Tree, CyanSoft(0.45f));
		CheckpointTicks.Add(Tick);
		CheckpointTickSlots.Add(EXUi::AddO(Track, EXUi::Sized(Tree, 3.0f, 14.0f, Tick), HAlign_Left, VAlign_Center,
			FMargin(BarWidth * Index / Count - 1.5f, 0.0f, 0.0f, 0.0f)));
	}
	for (int32 Index = 0; Index < MaxRivals; ++Index)
	{
		UBorder* Dot = EXUi::Box(Tree, EXUi::Hex(255, 140, 80, 0.9f));
		USizeBox* DotBox = EXUi::Sized(Tree, 7.0f, 7.0f, Dot);
		DotBox->SetRenderTransformAngle(45.0f);
		RivalDots.Add(Dot);
		RivalSlots.Add(EXUi::AddO(Track, DotBox, HAlign_Left, VAlign_Center));
		DotBox->SetVisibility(ESlateVisibility::Collapsed);
	}
	UOverlay* Mark = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Mark, EXUi::Sized(Tree, 16.0f, 24.0f, EXUi::Box(Tree, Cyan(0.3f))), HAlign_Center, VAlign_Center);
	EXUi::AddO(Mark, EXUi::Sized(Tree, 4.0f, 24.0f, EXUi::Box(Tree, White())), HAlign_Center, VAlign_Center);
	PlayerMarkSlot = EXUi::AddO(Track, Mark, HAlign_Left, VAlign_Center);
	EXUi::AddH(Line, Track, FMargin(0.0f), false, VAlign_Center);
	EXUi::AddH(Line, Figure(Tree, TEXT("B"), 15, Gold()), FMargin(12.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
	EXUi::AddV(Column, Line, FMargin(0.0f, 4.0f, 0.0f, 0.0f), HAlign_Center);
	DistanceText = Label(Tree, TEXT(""), 12, CyanSoft(0.85f), 140, false);
	EXUi::AddV(Column, DistanceText, FMargin(0.0f, 2.0f, 0.0f, 0.0f), HAlign_Center);
	return Column;
}

UWidget* UEXRaceHudWidget::BuildSpoils(UWidgetTree* Tree)
{
	// The piggy bank (animated from its HD frames when imported), then the spoils on a gold plate: the coin and the
	// value, ESPÓLIOS on a tab, the pieces and the rivals still racing; a gain pops beside the value.
	UOverlay* Row = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	UOverlay* Icon = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Icon, EXUi::Glow(Tree, FLinearColor(1.0f, 0.78f, 0.25f, 0.22f)), HAlign_Fill, VAlign_Fill, FMargin(34.0f));
	PiggyFrameAll.Reset();
	for (int32 Anim = 0; Anim < 8; ++Anim)
	{
		PiggyFirst[Anim] = PiggyFrameAll.Num();
		for (int32 Frame = 0; Frame < PiggyAnims[Anim].Frames; ++Frame)
		{
			const FString Name = FString::Printf(TEXT("T_Piggy_%s_%02d"), PiggyAnims[Anim].File, Frame);
			PiggyFrameAll.Add(LoadObject<UTexture2D>(nullptr, *FString::Printf(TEXT("/Game/UI/Piggy/%s.%s"), *Name, *Name), nullptr,
				LOAD_NoWarn | LOAD_Quiet));
		}
	}
	const bool bHd = PiggyFrameAll.Num() > 0 && PiggyFrameAll[0] != nullptr;
	float Box = 72.0f;
	if (bHd)
	{
		UCanvasPanel* Stage = Tree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass());
		PiggySprite = EXUi::Image(Tree, PiggyFrameAll[0], FLinearColor::White);
		PiggySpriteSlot = Stage->AddChildToCanvas(PiggySprite);
		PiggySpriteSlot->SetAutoSize(false);
		EXUi::AddO(Icon, Stage, HAlign_Fill, VAlign_Fill);
		Box = PiggyBox;
		PiggyAnim = PiggyTeleport;      // it beams in when the race screen comes up
		PiggyTime = 0.0f;
		PiggyShownAnim = -1;
	}
	else
	{
		EXUi::AddO(Icon, EXUi::Image(Tree, EXUi::Icon(TEXT("piggy")), Gold()), HAlign_Fill, VAlign_Fill, FMargin(6.0f));
	}
	PiggyIconBox = EXUi::Sized(Tree, Box, Box, Icon);
	PiggyIconBox->SetRenderTransformPivot(FVector2D(0.5f, 0.5f));

	UOverlay* Spoils = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Spoils, Plate(Tree, TEXT("hud_panel_gold")), HAlign_Fill, VAlign_Fill);
	UVerticalBox* Inside = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* Value = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Value, Art(Tree, TEXT("hud_coin"), 42.0f, 42.0f), FMargin(0.0f, 0.0f, 10.0f, 0.0f), false, VAlign_Center);
	PiggyValue = Figure(Tree, TEXT("0"), 34, Gold());
	EXUi::AddH(Value, PiggyValue, FMargin(0.0f), false, VAlign_Center);
	PiggyGain = Label(Tree, TEXT(""), 15, EXUi::Ok(), 40);
	EXUi::AddH(Value, PiggyGain, FMargin(10.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
	EXUi::AddV(Inside, Value);
	UOverlay* Tab = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Tab, Art(Tree, TEXT("hud_tab"), 190.0f, 40.0f), HAlign_Fill, VAlign_Fill);
	EXUi::AddO(Tab, Label(Tree, TEXT("ESPÓLIOS"), 14, CyanSoft(), 200), HAlign_Center, VAlign_Center, FMargin(0.0f, 0.0f, 0.0f, 2.0f));
	EXUi::AddV(Inside, EXUi::Sized(Tree, 190.0f, 40.0f, Tab), FMargin(0.0f, 2.0f, 0.0f, 0.0f), HAlign_Left);
	PiggySub = Label(Tree, TEXT(""), 10, CyanSoft(0.8f), 60, false);
	EXUi::AddV(Inside, PiggySub, FMargin(4.0f, 4.0f, 0.0f, 0.0f));
	UHorizontalBox* Pips = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	for (int32 Index = 0; Index < MaxRivals; ++Index)
	{
		UBorder* Pip = EXUi::Box(Tree, White(0.8f));
		RivalPips.Add(Pip);
		EXUi::AddH(Pips, EXUi::Sized(Tree, 7.0f, 7.0f, Pip), FMargin(Index > 0 ? 3.0f : 0.0f, 0.0f, 0.0f, 0.0f));
	}
	EXUi::AddV(Inside, Pips, FMargin(4.0f, 5.0f, 0.0f, 0.0f), HAlign_Left);
	EXUi::AddO(Spoils, Inside, HAlign_Left, VAlign_Center, FMargin(66.0f, 10.0f, 20.0f, 14.0f));
	// The plate on the right, the piggy over its left edge (added after it, so it is drawn on top).
	EXUi::AddO(Row, EXUi::Sized(Tree, 300.0f, 176.0f, Spoils), HAlign_Right, VAlign_Top, FMargin(0.0f, 6.0f, 0.0f, 0.0f));
	EXUi::AddO(Row, PiggyIconBox, HAlign_Left, VAlign_Top);
	return EXUi::Sized(Tree, 300.0f + Box - 90.0f, FMath::Max(Box, 182.0f), Row);   // the piggy sits on the plate's corner
}

UWidget* UEXRaceHudWidget::BuildMap(UWidgetTree* Tree)
{
	// The minimap on a plate: the road around the craft, turning with it.
	UOverlay* Box = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Box, Plate(Tree, TEXT("hud_panel")), HAlign_Fill, VAlign_Fill);
	Map = Tree->ConstructWidget<UEXRouteMapWidget>(UEXRouteMapWidget::StaticClass());
	EXUi::AddO(Box, Map, HAlign_Fill, VAlign_Fill, FMargin(18.0f));
	EXUi::AddO(Box, Label(Tree, TEXT("RADAR"), 10, CyanSoft(0.8f), 200), HAlign_Left, VAlign_Top, FMargin(28.0f, 20.0f, 0.0f, 0.0f));
	EXUi::AddO(Box, Art(Tree, TEXT("hud_flag"), 26.0f, 26.0f), HAlign_Right, VAlign_Top, FMargin(0.0f, 16.0f, 24.0f, 0.0f));
	return EXUi::Sized(Tree, MapSize, MapSize, Box);
}

UWidget* UEXRaceHudWidget::BuildWarning(UWidgetTree* Tree)
{
	UOverlay* Box = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Box, Art(Tree, TEXT("hud_warn"), 470.0f, 118.0f), HAlign_Fill, VAlign_Fill);
	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Line, Art(Tree, TEXT("hud_hazard"), 66.0f, 66.0f), FMargin(0.0f, 0.0f, 14.0f, 0.0f), false, VAlign_Center);
	UVerticalBox* Text = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	WarningTitle = Figure(Tree, TEXT("PERIGO!"), 28, EXUi::Hex(255, 150, 60));
	EXUi::AddV(Text, WarningTitle);
	WarningText = Label(Tree, TEXT(""), 15, White(), 40);
	EXUi::AddV(Text, WarningText, FMargin(0.0f, 2.0f, 0.0f, 0.0f));
	EXUi::AddH(Line, Text, FMargin(0.0f), true, VAlign_Center);
	EXUi::AddO(Box, Line, HAlign_Fill, VAlign_Center, FMargin(24.0f, 0.0f, 120.0f, 4.0f));
	WarningBox = EXUi::Sized(Tree, 470.0f, 118.0f, Box);
	WarningBox->SetVisibility(ESlateVisibility::Collapsed);
	return WarningBox;
}

UWidget* UEXRaceHudWidget::BuildToast(UWidgetTree* Tree)
{
	UOverlay* Box = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Box, Art(Tree, TEXT("hud_toast"), 470.0f, 118.0f), HAlign_Fill, VAlign_Fill);
	UHorizontalBox* Line = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Line, Art(Tree, TEXT("hud_trophy"), 62.0f, 62.0f), FMargin(0.0f, 0.0f, 14.0f, 0.0f), false, VAlign_Center);
	UVerticalBox* Text = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	ToastTitle = Figure(Tree, TEXT("CHECKPOINT!"), 24, White());
	EXUi::AddV(Text, ToastTitle);
	UHorizontalBox* Prize = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	ToastPrize = Figure(Tree, TEXT("+40"), 30, Gold());
	EXUi::AddH(Prize, ToastPrize, FMargin(0.0f), false, VAlign_Center);
	EXUi::AddH(Prize, Art(Tree, TEXT("hud_coin"), 30.0f, 30.0f), FMargin(10.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
	EXUi::AddV(Text, Prize, FMargin(0.0f, 0.0f, 0.0f, 0.0f), HAlign_Right);
	EXUi::AddH(Line, Text, FMargin(0.0f), true, VAlign_Center);
	EXUi::AddO(Box, Line, HAlign_Fill, VAlign_Center, FMargin(58.0f, 0.0f, 26.0f, 4.0f));
	ToastBox = EXUi::Sized(Tree, 470.0f, 118.0f, Box);
	ToastBox->SetVisibility(ESlateVisibility::Collapsed);
	return ToastBox;
}

UWidget* UEXRaceHudWidget::BuildSlots(UWidgetTree* Tree)
{
	// The four consumables in hexagons: icon, how many, the key and the d-pad arrow on a tab, the name.
	UHorizontalBox* Row = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	for (int32 Index = 0; Index < 4; ++Index)
	{
		FHexView& Hex = Hexes[Index];
		UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
		UOverlay* Cell = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		UWidget* Frame = Art(Tree, TEXT("hud_hex"), 104.0f, 104.0f);
		UWidget* FrameOn = Art(Tree, TEXT("hud_hex_on"), 104.0f, 104.0f);
		Hex.Frame = Cast<UImage>(Frame);
		Hex.FrameOn = Cast<UImage>(FrameOn);
		EXUi::AddO(Cell, Frame, HAlign_Fill, VAlign_Fill);
		EXUi::AddO(Cell, FrameOn, HAlign_Fill, VAlign_Fill);
		Hex.Icon = EXUi::Image(Tree, nullptr, FLinearColor::White, 52.0f, 52.0f);
		EXUi::AddO(Cell, EXUi::Sized(Tree, 52.0f, 52.0f, Hex.Icon), HAlign_Center, VAlign_Center);
		Hex.Count = Figure(Tree, TEXT(""), 15, White());
		EXUi::AddO(Cell, Hex.Count, HAlign_Right, VAlign_Top, FMargin(0.0f, 10.0f, 12.0f, 0.0f));
		EXUi::AddV(Column, EXUi::Sized(Tree, 104.0f, 104.0f, Cell), FMargin(0.0f), HAlign_Center);
		UOverlay* Key = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		EXUi::AddO(Key, Art(Tree, TEXT("hud_tab"), 70.0f, 26.0f), HAlign_Fill, VAlign_Fill);
		EXUi::AddO(Key, Label(Tree, FString::Printf(TEXT("%d  %s"), Index + 1, QuickArrows[Index]), 11, White(), 60, false), HAlign_Center,
			VAlign_Center, FMargin(0.0f, 0.0f, 0.0f, 1.0f));
		EXUi::AddV(Column, EXUi::Sized(Tree, 70.0f, 26.0f, Key), FMargin(0.0f, -4.0f, 0.0f, 0.0f), HAlign_Center);
		Hex.Name = Label(Tree, TEXT(""), 11, CyanSoft(), 60);
		EXUi::AddV(Column, Hex.Name, FMargin(0.0f, 3.0f, 0.0f, 0.0f), HAlign_Center);
		Hex.Root = Column;
		EXUi::AddH(Row, EXUi::Sized(Tree, 112.0f, 0.0f, Column), FMargin(Index > 0 ? 4.0f : 0.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Bottom);
	}
	return Row;
}

UWidget* UEXRaceHudWidget::BuildSpeed(UWidgetTree* Tree)
{
	// The speed on the plate with its brackets, KM/H, and the boost (the nitro) as a segmented bar with its bolt.
	UOverlay* Box = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Box, Art(Tree, TEXT("hud_speed"), 640.0f, 225.0f), HAlign_Fill, VAlign_Fill);
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	SpeedText = Figure(Tree, TEXT("0"), 70, White());
	EXUi::AddV(Column, SpeedText, FMargin(0.0f), HAlign_Center);
	EXUi::AddV(Column, Label(Tree, TEXT("KM/H"), 16, CyanSoft(), 200), FMargin(0.0f, -6.0f, 0.0f, 6.0f), HAlign_Center);
	UHorizontalBox* Boost = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Boost, Art(Tree, TEXT("hud_bolt"), 26.0f, 26.0f), FMargin(0.0f, 0.0f, 6.0f, 0.0f), false, VAlign_Center);
	EXUi::AddH(Boost, Label(Tree, TEXT("BOOST"), 15, White(), 100), FMargin(0.0f, 0.0f, 10.0f, 0.0f), false, VAlign_Center);
	for (int32 Index = 0; Index < BoostSegmentCount; ++Index)
	{
		UBorder* Segment = EXUi::Box(Tree, White(0.12f));
		BoostSegments.Add(Segment);
		USizeBox* Cell = EXUi::Sized(Tree, 18.0f, 14.0f, Segment);
		Italic(Cell, -20.0f);
		EXUi::AddH(Boost, Cell, FMargin(Index > 0 ? 4.0f : 0.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
	}
	EXUi::AddV(Column, Boost, FMargin(0.0f), HAlign_Center);
	EXUi::AddO(Box, Column, HAlign_Center, VAlign_Center, FMargin(0.0f, 4.0f, 0.0f, 10.0f));
	return EXUi::Sized(Tree, 640.0f, 225.0f, Box);
}

UWidget* UEXRaceHudWidget::BuildStatus(UWidgetTree* Tree)
{
	// The ship's blueprint with a status light per system, then the hull, fuel and heat as bars with their figures,
	// the lives as pips and what is at risk.
	UOverlay* Box = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Box, Plate(Tree, TEXT("hud_panel")), HAlign_Fill, VAlign_Fill);
	UHorizontalBox* Row = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	UVerticalBox* Lights = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	const TCHAR* const StatNames[3] = { TEXT("CASCO"), TEXT("COMBUSTÍVEL"), TEXT("CALOR") };
	for (int32 Index = 0; Index < 3; ++Index)
	{
		Stats[Index].Light = EXUi::Box(Tree, EXUi::Ok());
		USizeBox* Dot = EXUi::Sized(Tree, 12.0f, 12.0f, Stats[Index].Light);
		Dot->SetRenderTransformAngle(45.0f);
		EXUi::AddV(Lights, Dot, FMargin(0.0f, Index > 0 ? 22.0f : 0.0f, 0.0f, 0.0f), HAlign_Center);
	}
	EXUi::AddH(Row, Lights, FMargin(0.0f, 0.0f, 8.0f, 0.0f), false, VAlign_Center);
	Blueprint = EXUi::Image(Tree, nullptr, FLinearColor::White, 132.0f, 132.0f);
	EXUi::AddH(Row, EXUi::Sized(Tree, 132.0f, 132.0f, Blueprint), FMargin(0.0f, 0.0f, 12.0f, 0.0f), false, VAlign_Center);
	UVerticalBox* Bars = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* Three = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	for (int32 Index = 0; Index < 3; ++Index)
	{
		UHorizontalBox* Stat = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		UOverlay* Track = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		EXUi::AddO(Track, EXUi::Sized(Tree, 8.0f, StatBarHeight, EXUi::Box(Tree, Navy(0.85f))), HAlign_Center, VAlign_Bottom);
		Stats[Index].Colour = EXUi::Box(Tree, Cyan());
		Stats[Index].Fill = EXUi::Sized(Tree, 8.0f, StatBarHeight, Stats[Index].Colour);
		EXUi::AddO(Track, Stats[Index].Fill, HAlign_Center, VAlign_Bottom);
		EXUi::AddH(Stat, EXUi::Sized(Tree, 8.0f, StatBarHeight, Track), FMargin(0.0f, 0.0f, 7.0f, 0.0f), false, VAlign_Center);
		UVerticalBox* Text = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
		Stats[Index].Value = Figure(Tree, TEXT("100%"), 20, White());
		EXUi::AddV(Text, Stats[Index].Value);
		EXUi::AddV(Text, Label(Tree, StatNames[Index], 9, CyanSoft(), 80, false), FMargin(0.0f, 1.0f, 0.0f, 0.0f));
		EXUi::AddH(Stat, Text, FMargin(0.0f), false, VAlign_Center);
		EXUi::AddH(Three, Stat, FMargin(Index > 0 ? 12.0f : 0.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
	}
	EXUi::AddV(Bars, Three);
	UHorizontalBox* Lives = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	EXUi::AddH(Lives, Label(Tree, TEXT("VIDAS"), 10, CyanSoft(), 120, false), FMargin(0.0f, 0.0f, 8.0f, 0.0f), false, VAlign_Center);
	for (int32 Index = 0; Index < 6; ++Index)
	{
		UBorder* Pip = EXUi::Box(Tree, EXUi::Ok());
		LifePips.Add(Pip);
		USizeBox* Cell = EXUi::Sized(Tree, 16.0f, 10.0f, Pip);
		Italic(Cell, -20.0f);
		EXUi::AddH(Lives, Cell, FMargin(Index > 0 ? 4.0f : 0.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
	}
	EXUi::AddV(Bars, Lives, FMargin(0.0f, 12.0f, 0.0f, 0.0f));
	UHorizontalBox* Risk = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	RiskText = Label(Tree, TEXT(""), 10, Gold(), 80, false);
	EXUi::AddH(Risk, RiskText, FMargin(0.0f), false, VAlign_Center);
	EXUi::AddH(Risk, EXUi::GemImage(Tree, 9.0f), FMargin(5.0f, 0.0f, 0.0f, 0.0f), false, VAlign_Center);
	EXUi::AddV(Bars, Risk, FMargin(0.0f, 8.0f, 0.0f, 0.0f));
	EXUi::AddH(Row, Bars, FMargin(0.0f), false, VAlign_Center);
	EXUi::AddO(Box, Row, HAlign_Left, VAlign_Center, FMargin(22.0f, 12.0f, 22.0f, 14.0f));
	return EXUi::Sized(Tree, 520.0f, 186.0f, Box);
}

UWidget* UEXRaceHudWidget::BuildStartLights(UWidgetTree* Tree)
{
	UVerticalBox* Column = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UHorizontalBox* Gantry = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	for (int32 Index = 0; Index < 3; ++Index)
	{
		StartLights[Index] = EXUi::Box(Tree, EXUi::Ink(0.8f));
		const EXUi::FFrame Frame = EXUi::Frame(Tree, Cyan(0.6f), EXUi::Ink(0.0f), 2.0f, FMargin(6.0f));
		Frame.Fill->SetContent(StartLights[Index]);
		EXUi::AddH(Gantry, EXUi::Sized(Tree, 74.0f, 74.0f, Frame.Root), FMargin(Index > 0 ? 18.0f : 0.0f, 0.0f, 0.0f, 0.0f));
	}
	UOverlay* Back = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	EXUi::AddO(Back, Plate(Tree, TEXT("hud_panel")), HAlign_Fill, VAlign_Fill);
	EXUi::AddO(Back, Gantry, HAlign_Center, VAlign_Center, FMargin(30.0f, 22.0f));
	EXUi::AddV(Column, Back, FMargin(0.0f), HAlign_Center);
	StartText = Figure(Tree, TEXT(""), 64, White(), 60);
	EXUi::AddV(Column, StartText, FMargin(0.0f, 18.0f, 0.0f, 0.0f), HAlign_Center);
	StartPanel = Column;
	return Column;
}

// ------------------------------------------------------------------------------------------------------------- refresh

void UEXRaceHudWidget::Refresh()
{
	const AEXHoverCraft* Craft = Cast<AEXHoverCraft>(GetOwningPlayerPawn());
	if (!Craft || !RaceDirector)
	{
		return;
	}
	const float Dt = GetWorld() ? GetWorld()->GetDeltaSeconds() : 0.016f;
	const float Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0f;
	RefreshPlace();
	RefreshTimer(Craft);
	RefreshSpoils(Dt);
	RefreshMap(Craft);
	RefreshWarning(Craft, Now);
	RefreshToast();
	RefreshSlots(Craft, Now);
	RefreshSpeed(Craft, Now);
	RefreshStatus(Craft, Now);
	RefreshStart();
}

void UEXRaceHudWidget::RefreshPlace()
{
	const bool bBots = RaceDirector->GetMode() == EEXRaceMode::Bots;
	const TArray<FEXRacer>& Standings = RaceDirector->GetStandings();
	EXUi::SetText(PlaceText, FString::FromInt(bBots ? RaceDirector->GetPlayerPlace() : 1));
	EXUi::SetText(FieldText, FString::Printf(TEXT("/%d"), bBots ? Standings.Num() : 1));
	EXUi::SetText(PlaceLabel, bBots ? FString(TEXT("POSIÇÃO")) : FString(TEXT("EXPEDIÇÃO SOLO")));
	RowsBox->SetVisibility(bBots ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	if (!bBots)
	{
		return;
	}
	// The first eight; if the player is lower down, the last row is the player's.
	int32 Mine = INDEX_NONE;
	for (int32 Index = 0; Index < Standings.Num(); ++Index)
	{
		if (Standings[Index].bPlayer)
		{
			Mine = Index;
			break;
		}
	}
	for (int32 Index = 0; Index < RowCount; ++Index)
	{
		const int32 At = (Index == RowCount - 1 && Mine >= RowCount) ? Mine : Index;
		FRowView& Row = Rows[Index];
		if (!Standings.IsValidIndex(At))
		{
			Row.Root->SetVisibility(ESlateVisibility::Collapsed);
			continue;
		}
		const FEXRacer& Racer = Standings[At];
		Row.Root->SetVisibility(ESlateVisibility::HitTestInvisible);
		if (Row.Back && Row.BackMe)
		{
			Row.Back->SetVisibility(Racer.bPlayer ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
			Row.BackMe->SetVisibility(Racer.bPlayer ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
		}
		EXUi::SetText(Row.Place, FString::FromInt(At + 1));
		EXUi::SetText(Row.Name, Racer.bPlayer ? FString(TEXT("TU")) : Racer.Name);
		const FString Ship = IsValid(Racer.Craft) ? Racer.Craft->GetShipName().ToLower() : FString();
		EXUi::SetImage(Row.Ship, Ship.IsEmpty() ? nullptr : EXUi::Icon(TEXT("hud_ship_") + Ship), Racer.bPlayer ? FLinearColor::White : CyanSoft(0.9f));
		const bool bOut = Racer.bOut || Racer.State == 2;
		EXUi::SetText(Row.Tag, bOut ? FString(TEXT("DESTRUÍDA")) : (Racer.bFinished ? FString(TEXT("EXTRAÍDA")) : FString()));
		Row.Tag->SetColorAndOpacity(FSlateColor(bOut ? Danger() : Gold()));
		Row.Root->SetRenderOpacity(bOut ? 0.55f : 1.0f);
	}
}

void UEXRaceHudWidget::RefreshTimer(const AEXHoverCraft* Craft)
{
	EXUi::SetText(ClockText, HudClock(RaceDirector->GetRaceTime()));
	const int32 Passed = RaceDirector->GetPlayerCheckpoint();
	const int32 Count = RaceDirector->GetCheckpointCount();
	const int32 Missed = RaceDirector->GetMissedGate();
	EXUi::SetText(CheckpointText, Missed > 0 ? FString::Printf(TEXT("VOLTA AO CHECKPOINT %d"), Missed)
		: FString::Printf(TEXT("CHECKPOINT %d / %d"), FMath::Min(Passed + 1, Count), Count));
	CheckpointText->SetColorAndOpacity(FSlateColor(Missed > 0 ? Danger() : CyanSoft()));
	if (CheckpointTab)
	{
		CheckpointTab->SetColorAndOpacity(Missed > 0 ? EXUi::Hex(255, 120, 90) : FLinearColor::White);
	}

	const float RouteM = FMath::Max(1.0f, RaceDirector->GetRouteLengthM());
	const float Mine = FMath::Clamp(Craft->GetRaceProgressM() / RouteM, 0.0f, 1.0f);
	PlayerMarkSlot->SetPadding(FMargin(BarWidth * Mine - 8.0f, 0.0f, 0.0f, 0.0f));
	PassedFill->SetWidthOverride(BarWidth * Mine);
	for (int32 Index = 0; Index < CheckpointTicks.Num(); ++Index)
	{
		CheckpointTicks[Index]->SetBrushColor(Index + 1 <= Passed ? Gold() : (Missed == Index + 1 ? Danger() : CyanSoft(0.45f)));
		if (Index < RaceDirector->GetGateCount() && CheckpointTickSlots.IsValidIndex(Index))
		{
			CheckpointTickSlots[Index]->SetPadding(FMargin(BarWidth * FMath::Clamp(RaceDirector->GetGateAlongM(Index) / RouteM, 0.0f, 1.0f) - 1.5f,
				0.0f, 0.0f, 0.0f));
		}
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
		RivalDots[Dot]->SetBrushColor(Racer.bOut ? Danger(0.5f) : EXUi::Hex(255, 140, 80, 0.9f));
		RivalDots[Dot]->GetParent()->SetVisibility(ESlateVisibility::HitTestInvisible);
		++Dot;
	}
	for (; Dot < RivalSlots.Num(); ++Dot)
	{
		RivalDots[Dot]->GetParent()->SetVisibility(ESlateVisibility::Collapsed);
	}
	EXUi::SetText(DistanceText, FString::Printf(TEXT("%s KM PARA B"), *Km(FMath::Max(0.0f, RouteM - Craft->GetRaceProgressM()))));
}

void UEXRaceHudWidget::RefreshSpoils(float Dt)
{
	const int32 Pool = RaceDirector->GetPool();
	PiggyShown = FMath::Abs(Pool - PiggyShown) < 1.0f ? static_cast<float>(Pool) : PiggyShown + (Pool - PiggyShown) * FMath::Min(1.0f, Dt * 4.0f);
	EXUi::SetText(PiggyValue, EXUi::Thousands(FMath::RoundToInt(PiggyShown)));
	const int32 Total = RaceDirector->GetRivalsTotal();
	const int32 Left = RaceDirector->GetRivalsLeft();
	EXUi::SetText(PiggySub, FString::Printf(TEXT("%d PEÇAS  ·  %d DESTRUÍDAS  ·  %d/%d EM PROVA"), RaceDirector->GetPoolCount(),
		Total - Left, Left, Total));
	// A drop: the gain shows beside the value and the piggy catches the coins.
	const float Since = RaceDirector->GetRaceTime() - RaceDirector->GetLastPoolTime();
	const bool bGain = Since >= 0.0f && Since < 2.5f && RaceDirector->GetLastPoolGain() > 0;
	PiggyGain->SetVisibility(bGain ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	if (bGain)
	{
		EXUi::SetText(PiggyGain, FString::Printf(TEXT("+%s"), *EXUi::Thousands(RaceDirector->GetLastPoolGain())));
		PiggyGain->SetRenderOpacity(FMath::Clamp((2.5f - Since) / 0.6f, 0.0f, 1.0f));
	}
	if (PiggySprite)
	{
		RefreshPiggySprite(Dt);
	}
	else
	{
		const float Jump = bGain ? FMath::Max(0.0f, 1.0f - Since / 0.5f) : 0.0f;
		PiggyIconBox->SetRenderScale(FVector2D(1.0f + 0.35f * Jump * FMath::Abs(FMath::Sin(Since * 18.0f))));
	}
	// One pip per rival: racing (white), extracted (gold), destroyed (red).
	int32 Pip = 0;
	for (const FEXRacer& Racer : RaceDirector->GetStandings())
	{
		if (Racer.bPlayer || Pip >= RivalPips.Num())
		{
			continue;
		}
		RivalPips[Pip]->SetBrushColor(Racer.bOut ? Danger(0.85f) : (Racer.bFinished ? Gold() : White(0.85f)));
		RivalPips[Pip]->GetParent()->SetVisibility(ESlateVisibility::HitTestInvisible);
		++Pip;
	}
	for (; Pip < RivalPips.Num(); ++Pip)
	{
		RivalPips[Pip]->GetParent()->SetVisibility(ESlateVisibility::Collapsed);
	}
}

void UEXRaceHudWidget::RefreshPiggySprite(float Dt)
{
	PiggyTime += Dt;
	// What the player's race has come to: extracted (a jump, then the celebration), destroyed or stranded (tears).
	uint8 PlayerState = 0;
	for (const FEXRacer& Racer : RaceDirector->GetStandings())
	{
		if (Racer.bPlayer)
		{
			PlayerState = Racer.State;
			break;
		}
	}
	auto Play = [this](int32 Anim)
	{
		if (PiggyAnim != Anim)
		{
			PiggyAnim = Anim;
			PiggyTime = 0.0f;
		}
	};
	const FPiggyAnim& Now = PiggyAnims[PiggyAnim];
	const bool bDone = !Now.bLoop && Now.Fps > 0.0f && PiggyTime * Now.Fps >= Now.Frames;
	if (PlayerState == 1)
	{
		if (PiggyAnim != PiggyJump && PiggyAnim != PiggyCelebrate)
		{
			Play(PiggyJump);
		}
		else if (PiggyAnim == PiggyJump && bDone)
		{
			Play(PiggyCelebrate);
		}
	}
	else if (PlayerState >= 2)
	{
		Play(PiggyReaction);
	}
	else
	{
		// A racer destroyed: its pieces fall into the piggy.
		const float PoolTime = RaceDirector->GetLastPoolTime();
		if (RaceDirector->GetLastPoolGain() > 0 && PoolTime != PiggyLastPool && PoolTime > 0.0f)
		{
			PiggyLastPool = PoolTime;
			Play(PiggyCoins);
		}
		else if ((PiggyAnim == PiggyCoins || PiggyAnim == PiggyTeleport || PiggyAnim == PiggyBlink) && bDone)
		{
			Play(PiggyIdle);
			PiggyBlinkAt = FMath::FRandRange(3.0f, 6.0f);
		}
		else if (PiggyAnim == PiggyIdle && PiggyTime >= PiggyBlinkAt)
		{
			Play(PiggyBlink);
		}
	}
	const FPiggyAnim& Anim = PiggyAnims[PiggyAnim];
	int32 Frame = PiggyAnim == PiggyReaction ? PiggyCrying : FMath::FloorToInt(PiggyTime * Anim.Fps);
	Frame = Anim.bLoop ? Frame % Anim.Frames : FMath::Clamp(Frame, 0, Anim.Frames - 1);
	const int32 At = PiggyFirst[PiggyAnim] + Frame;
	UTexture2D* Texture = PiggyFrameAll.IsValidIndex(At) ? PiggyFrameAll[At].Get() : nullptr;
	if (!Texture)
	{
		Texture = PiggyFrameAll[0];
	}
	EXUi::SetImage(PiggySprite, Texture, FLinearColor::White);
	if (PiggyShownAnim != PiggyAnim && PiggySpriteSlot)
	{
		// Every animation has its own canvas: keep the feet on the same spot of the HUD.
		PiggyShownAnim = PiggyAnim;
		PiggySpriteSlot->SetSize(FVector2D(Anim.W, Anim.H) * PiggyScale);
		PiggySpriteSlot->SetPosition(FVector2D(PiggyBox * 0.5f - Anim.PX * PiggyScale, PiggyBox - 8.0f - Anim.PY * PiggyScale));
	}
}

void UEXRaceHudWidget::RefreshMap(const AEXHoverCraft* Craft)
{
	const TArray<FVector2D>& Route = Craft->GetMapRoute();
	if (!Map || Route.Num() < 4)
	{
		return;
	}
	if (!bMapRoute)
	{
		Map->SetRadar(Route, MapWindowM);
		bMapRoute = true;
	}
	TArray<FVector2D> Rivals, Gates;
	for (const FEXRacer& Racer : RaceDirector->GetStandings())
	{
		if (!Racer.bPlayer && !Racer.bOut && IsValid(Racer.Craft))
		{
			Rivals.Add(FVector2D(Racer.Craft->GetActorLocation().X, Racer.Craft->GetActorLocation().Y) / 100.0f);
		}
	}
	for (int32 Index = 0; Index < RaceDirector->GetGateCount(); ++Index)
	{
		Gates.Add(RaceDirector->GetGateCentre(Index));
	}
	const FVector Location = Craft->GetActorLocation();
	Map->SetRadarView(FVector2D(Location.X, Location.Y) / 100.0f, FVector2D(Craft->GetHeading()), Craft->GetRouteIndex(), Rivals, Gates,
		RaceDirector->GetPlayerCheckpoint(), RaceDirector->GetMissedGate());
}

void UEXRaceHudWidget::RefreshWarning(const AEXHoverCraft* Craft, float Now)
{
	// The one danger that matters most now, on the red banner, pulsing.
	FString Title = TEXT("PERIGO!");
	FString Text;
	const int32 Missed = RaceDirector->GetMissedGate();
	const float Hull = Craft->GetHullFrac();
	const TArray<FVector2D>& Route = Craft->GetMapRoute();
	bool bWrongWay = false;
	if (Route.Num() > 8)
	{
		const int32 Index = FMath::Clamp(Craft->GetRouteIndex(), 0, Route.Num() - 5);
		const FVector2D Tangent = (Route[Index + 4] - Route[Index]).GetSafeNormal();
		bWrongWay = (FVector2D(Craft->GetHeading()).GetSafeNormal() | Tangent) < -0.3f && FVector2D(Craft->GetFlightVelocity()).Size() > 1500.0f;
	}
	if (Craft->IsEliminated() || RaceDirector->IsOver() || RaceDirector->GetCountdown() > 0.0f)
	{
		Text.Reset();
	}
	else if (Missed > 0)
	{
		Text = FString::Printf(TEXT("CHECKPOINT %d FALHADO  ·  VOLTA ATRÁS"), Missed);
	}
	else if (bWrongWay)
	{
		Text = TEXT("SENTIDO ERRADO");
	}
	else if (Hull <= 0.25f)
	{
		Text = FString::Printf(TEXT("CASCO CRÍTICO  ·  %d%%"), FMath::RoundToInt(Hull * 100.0f));
	}
	else if (Craft->IsOverheated())
	{
		Text = TEXT("SOBREAQUECIDA  ·  SEM BOOST");
	}
	else if (Craft->GetFuel() <= 0.0f)
	{
		Text = TEXT("SEM COMBUSTÍVEL  ·  METADE DA VELOCIDADE");
	}
	else if (Craft->GetFuel() < 15.0f)
	{
		Title = TEXT("ATENÇÃO!");
		Text = TEXT("COMBUSTÍVEL BAIXO");
	}
	WarningBox->SetVisibility(Text.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
	if (!Text.IsEmpty())
	{
		EXUi::SetText(WarningTitle, Title);
		EXUi::SetText(WarningText, Text);
		WarningBox->SetRenderOpacity(0.78f + 0.22f * FMath::Sin(Now * 7.0f));
	}
}

void UEXRaceHudWidget::RefreshToast()
{
	// 2.4 s after each checkpoint: its number and what it pays on extraction; EXTRAÇÃO at B.
	const int32 Passed = RaceDirector->GetPlayerCheckpoint();
	const float Since = RaceDirector->GetRaceTime() - RaceDirector->GetLastCheckpointTime();
	const bool bShow = Since >= 0.0f && Since < 2.4f && Passed > 0 && !RaceDirector->IsOver();
	ToastBox->SetVisibility(bShow ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	if (!bShow)
	{
		return;
	}
	const float In = FMath::Clamp(Since / 0.18f, 0.0f, 1.0f);
	ToastBox->SetRenderOpacity(FMath::Min(In, FMath::Clamp((2.4f - Since) / 0.5f, 0.0f, 1.0f)));
	ToastBox->SetRenderTranslation(FVector2D((1.0f - In) * 60.0f, 0.0f));
	const bool bLast = Passed >= RaceDirector->GetCheckpointCount();
	EXUi::SetText(ToastTitle, bLast ? FString(TEXT("EXTRAÇÃO!")) : FString::Printf(TEXT("CHECKPOINT %d!"), Passed));
	EXUi::SetText(ToastPrize, FString::Printf(TEXT("+%d"), AEXRaceDirector::GetCheckpointPrize()));
}

void UEXRaceHudWidget::RefreshSlots(const AEXHoverCraft* Craft, float Now)
{
	const TArray<FEXQuickSlot>& Quick = Craft->GetQuickSlots();
	for (int32 Index = 0; Index < 4; ++Index)
	{
		FHexView& Hex = Hexes[Index];
		const bool bAny = Quick.IsValidIndex(Index) && Quick[Index].Kind != 0;
		const int32 Count = bAny ? Quick[Index].Count : 0;
		const EXMeta::FConsumableDef& Def = EXMeta::Consumable(static_cast<EEXConsumable>(bAny ? Quick[Index].Kind : 0));
		EXUi::SetImage(Hex.Icon, bAny ? EXUi::Icon(FString::Printf(TEXT("con_%s"), Def.Id)) : nullptr, Count > 0 ? Def.Colour : White(0.35f));
		EXUi::SetText(Hex.Count, bAny ? FString::Printf(TEXT("×%d"), Count) : FString());
		EXUi::SetText(Hex.Name, bAny ? FString(Def.Name).ToUpper() : FString(TEXT("VAZIO")));
		// Just used: the frame flashes gold for a moment.
		const bool bFlash = Craft->GetLastQuickSlot() == Index && Now - Craft->GetLastQuickTime() < 0.6f;
		if (Hex.FrameOn)
		{
			Hex.FrameOn->SetVisibility(bFlash ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
		}
		Hex.Root->SetRenderOpacity(Count > 0 ? 1.0f : 0.55f);
	}
}

void UEXRaceHudWidget::RefreshSpeed(const AEXHoverCraft* Craft, float Now)
{
	EXUi::SetText(SpeedText, FString::FromInt(FMath::RoundToInt(Craft->GetSpeedKmh())));
	SpeedText->SetColorAndOpacity(FSlateColor(Craft->IsBoosting() ? CyanSoft() : White()));
	// The boost: the nitro left, yellow to orange; bright cyan while it burns; red while the engine is too hot.
	const float Nitro = FMath::Clamp(Craft->GetNitro(), 0.0f, 1.0f);
	const int32 Lit = FMath::CeilToInt(Nitro * BoostSegmentCount - 0.01f);
	const float Pulse = 0.75f + 0.25f * FMath::Sin(Now * 14.0f);
	for (int32 Index = 0; Index < BoostSegments.Num(); ++Index)
	{
		const float At = static_cast<float>(Index) / (BoostSegmentCount - 1);
		FLinearColor On = FMath::Lerp(EXUi::Hex(255, 220, 60), EXUi::Hex(255, 120, 30), At);
		if (Craft->IsBoosting())
		{
			On = Cyan() * Pulse;
		}
		if (Craft->IsOverheated())
		{
			On = Danger() * Pulse;
		}
		BoostSegments[Index]->SetBrushColor(Index < Lit ? On : White(0.12f));
	}
}

void UEXRaceHudWidget::RefreshStatus(const AEXHoverCraft* Craft, float Now)
{
	const FString Ship = Craft->GetShipName().ToLower();
	if (Ship != BlueprintShip)
	{
		BlueprintShip = Ship;
		EXUi::SetImage(Blueprint, EXUi::Icon(TEXT("hud_ship_") + Ship), FLinearColor::White);
	}
	// The hull drains down after a hit; green, yellow, orange, red as it falls (red pulses).
	const float Dt = GetWorld() ? GetWorld()->GetDeltaSeconds() : 0.016f;
	const float Hull = Craft->GetHullFrac();
	HullShown = Hull >= HullShown ? Hull : FMath::Max(Hull, HullShown - Dt * 0.35f);
	const float Fuel = FMath::Clamp(Craft->GetFuel() / 100.0f, 0.0f, 1.0f);
	const float Heat = FMath::Clamp(Craft->GetHeat() / 100.0f, 0.0f, 1.0f);
	const float Pulse = 0.65f + 0.35f * FMath::Sin(Now * 9.0f);
	const FLinearColor HullCol = Hull > 0.75f ? EXUi::Hex(115, 255, 140) : (Hull > 0.5f ? EXUi::Hex(215, 255, 100)
		: (Hull > 0.25f ? EXUi::Hex(255, 190, 75) : EXUi::Hex(255, 75, 60) * Pulse));
	const FLinearColor FuelCol = Fuel < 0.15f ? EXUi::Hex(255, 80, 60) * Pulse : Cyan();
	const FLinearColor HeatCol = Craft->IsOverheated() ? EXUi::Hex(255, 60, 40) * Pulse
		: FMath::Lerp(EXUi::Hex(255, 210, 90), EXUi::Hex(255, 90, 40), Heat);
	const float Values[3] = { HullShown, Fuel, Heat };
	const float Shown[3] = { Hull, Fuel, Heat };
	const FLinearColor Colours[3] = { HullCol, FuelCol, HeatCol };
	const bool bBad[3] = { Hull <= 0.25f, Fuel < 0.15f, Craft->IsOverheated() || Heat > 0.85f };
	const bool bWarn[3] = { Hull <= 0.5f, Fuel < 0.3f, Heat > 0.6f };
	for (int32 Index = 0; Index < 3; ++Index)
	{
		Stats[Index].Fill->SetHeightOverride(StatBarHeight * FMath::Clamp(Values[Index], 0.0f, 1.0f));
		Stats[Index].Colour->SetBrushColor(Colours[Index]);
		EXUi::SetText(Stats[Index].Value, FString::Printf(TEXT("%d%%"), FMath::RoundToInt(Shown[Index] * 100.0f)));
		Stats[Index].Light->SetBrushColor(bBad[Index] ? EXUi::Hex(255, 70, 50) * Pulse : (bWarn[Index] ? EXUi::Hex(255, 200, 70) : EXUi::Ok()));
	}
	for (int32 Index = 0; Index < LifePips.Num(); ++Index)
	{
		LifePips[Index]->GetParent()->SetVisibility(Index < Craft->GetMaxLives() ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
		LifePips[Index]->SetBrushColor(Index < Craft->GetLives() ? EXUi::Ok() : White(0.15f));
	}
	const UEXProfileSave* Profile = Craft->GetProfile();
	EXUi::SetText(RiskText, FString::Printf(TEXT("EM RISCO  %s"), *EXUi::Thousands(Profile ? EXEconomy::RiskValue(Profile, Craft->GetShipName()) : 0)));
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
	const int32 Count = FMath::Min(3, FMath::CeilToInt(Countdown));   // 3, 2, 1 (the craft go at 0)
	const bool bSettle = Countdown > 3.0f;
	for (int32 Index = 0; Index < 3; ++Index)
	{
		const bool bRed = !bGo && !bSettle && Index < 4 - Count;
		StartLights[Index]->SetBrushColor(bGo ? EXUi::Hex(70, 235, 110) : (bRed ? EXUi::Hex(255, 45, 30) : EXUi::Ink(0.8f)));
	}
	EXUi::SetText(StartText, bGo ? FString(TEXT("PARTIDA!")) : (bSettle ? FString() : FString::FromInt(Count)));
	StartText->SetColorAndOpacity(FSlateColor(bGo ? EXUi::Hex(70, 235, 110) : White()));
}
