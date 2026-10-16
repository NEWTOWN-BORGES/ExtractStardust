#include "Presentation/StardustRaceHudWidget.h"

#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ProgressBar.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Blueprint/WidgetTree.h"
#include "Game/StardustRaceProgressComponent.h"
#include "Styling/CoreStyle.h"
#include "Vehicle/StardustCraftMovementComponent.h"
#include "Vehicle/StardustHovercraftPawn.h"

namespace
{
	FText FormatRaceTime(float TimeSeconds)
	{
		const int32 TotalTenths = FMath::Max(0, FMath::RoundToInt(TimeSeconds * 10.0f));
		const int32 Minutes = TotalTenths / 600;
		const int32 Seconds = (TotalTenths / 10) % 60;
		const int32 Tenths = TotalTenths % 10;
		return FText::FromString(FString::Printf(TEXT("%02d:%02d.%d"), Minutes, Seconds, Tenths));
	}
}

void UStardustRaceHudWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();
	BuildHud();
}

void UStardustRaceHudWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	RefreshHud();
}

void UStardustRaceHudWidget::SetCraft(APawn* InCraft)
{
	CraftPawn = InCraft;
	CraftMovement = InCraft ? InCraft->FindComponentByClass<UStardustCraftMovementComponent>() : nullptr;
	RaceProgress = InCraft ? InCraft->FindComponentByClass<UStardustRaceProgressComponent>() : nullptr;
	RefreshHud();
}

void UStardustRaceHudWidget::BuildHud()
{
	if (!WidgetTree)
	{
		return;
	}

	UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("RaceHudCanvas"));
	WidgetTree->RootWidget = Canvas;
	if (!Canvas)
	{
		return;
	}

	UBorder* Panel = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("RaceHudPanel"));
	Panel->SetPadding(FMargin(18.0f, 14.0f));
	Panel->SetBrushColor(FLinearColor(0.012f, 0.022f, 0.034f, 0.82f));
	UCanvasPanelSlot* PanelSlot = Canvas->AddChildToCanvas(Panel);
	PanelSlot->SetAnchors(FAnchors(0.025f, 0.035f, 0.39f, 0.37f));
	PanelSlot->SetOffsets(FMargin(0.0f));

	USizeBox* SizeBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("RaceHudSize"));
	SizeBox->SetMinDesiredWidth(310.0f);
	Panel->SetContent(SizeBox);

	UVerticalBox* Lines = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("RaceHudLines"));
	SizeBox->SetContent(Lines);

	auto AddLine = [this, Lines](const TCHAR* Name, int32 FontSize, const FLinearColor& Color)
	{
		UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), Name);
		FSlateFontInfo Font = FCoreStyle::GetDefaultFontStyle(TEXT("Bold"), FontSize);
		Text->SetFont(Font);
		Text->SetColorAndOpacity(FSlateColor(Color));
		Text->SetShadowColorAndOpacity(FLinearColor(0.0f, 0.0f, 0.0f, 0.9f));
		Text->SetShadowOffset(FVector2D(1.0f, 1.0f));
		Lines->AddChildToVerticalBox(Text);
		return Text;
	};

	StateText = AddLine(TEXT("RaceState"), 15, FLinearColor(1.0f, 0.73f, 0.30f));
	SpeedText = AddLine(TEXT("RaceSpeed"), 34, FLinearColor(0.88f, 0.96f, 1.0f));
	RaceText = AddLine(TEXT("RaceDistance"), 15, FLinearColor(0.78f, 0.88f, 0.94f));

	RaceProgressBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("RaceProgressBar"));
	RaceProgressBar->SetFillColorAndOpacity(FLinearColor(0.12f, 0.78f, 0.91f, 1.0f));
	RaceProgressBar->SetPercent(0.0f);
	Lines->AddChildToVerticalBox(RaceProgressBar);
	if (UVerticalBoxSlot* BarSlot = Cast<UVerticalBoxSlot>(RaceProgressBar->Slot))
	{
		BarSlot->SetPadding(FMargin(0.0f, 8.0f, 0.0f, 8.0f));
	}

	VitalsText = AddLine(TEXT("RaceVitals"), 13, FLinearColor(0.69f, 0.88f, 0.88f));
	ControlsText = AddLine(TEXT("RaceControls"), 11, FLinearColor(0.64f, 0.71f, 0.76f));
	ControlsText->SetText(FText::FromString(TEXT("W acelerar  |  A/D virar  |  S travão  |  Shift nitro  |  Espaço drift")));
}

void UStardustRaceHudWidget::RefreshHud()
{
	if (!StateText || !SpeedText || !RaceText || !VitalsText || !RaceProgressBar)
	{
		return;
	}

	const FStardustCraftTelemetry EmptyTelemetry;
	const FStardustCraftTelemetry& Telemetry = CraftMovement ? CraftMovement->Telemetry : EmptyTelemetry;
	const float SpeedKmh = Telemetry.SpeedMPerSecond * 3.6f;
	SpeedText->SetText(FText::FromString(FString::Printf(TEXT("%03.0f  km/h%s"), SpeedKmh,
		Telemetry.bBoosting ? TEXT("  NITRO") : TEXT(""))));

	float Progress = 0.0f;
	if (RaceProgress && RaceProgress->FinishDistanceM > 0.0f)
	{
		Progress = FMath::Clamp(RaceProgress->RaceDistanceM / RaceProgress->FinishDistanceM, 0.0f, 1.0f);
	}
	RaceProgressBar->SetPercent(Progress);
	const int32 Percent = FMath::RoundToInt(Progress * 100.0f);
	const int32 Checkpoint = RaceProgress ? RaceProgress->CurrentCheckpoint : 0;
	const int32 CheckpointCount = RaceProgress ? RaceProgress->CheckpointCount : 0;
	const float ElapsedSeconds = RaceProgress ? RaceProgress->ElapsedTimeSeconds : 0.0f;
	RaceText->SetText(FText::FromString(FString::Printf(TEXT("CORRIDA  %02d%%   ·   PONTO %d/%d   ·   %s"),
		Percent, Checkpoint, CheckpointCount, *FormatRaceTime(ElapsedSeconds).ToString())));

	FLinearColor StateColor(1.0f, 0.73f, 0.30f);
	FString StateLabel = TEXT("PRONTO  —  W para arrancar");
	if (RaceProgress)
	{
		switch (RaceProgress->State)
		{
		case EStardustRaceState::Racing:
			StateColor = FLinearColor(0.28f, 0.88f, 1.0f);
			StateLabel = TEXT("A CORRER");
			break;
		case EStardustRaceState::Extracted:
			StateColor = FLinearColor(0.35f, 1.0f, 0.58f);
			StateLabel = FString::Printf(TEXT("EXTRAÍDO  —  %s"), *FormatRaceTime(RaceProgress->FinishTimeSeconds).ToString());
			break;
		case EStardustRaceState::Abandoned:
			StateColor = FLinearColor(1.0f, 0.39f, 0.32f);
			StateLabel = TEXT("EXPEDIÇÃO ABANDONADA");
			break;
		default:
			break;
		}
	}
	StateText->SetText(FText::FromString(StateLabel));
	StateText->SetColorAndOpacity(FSlateColor(StateColor));

	VitalsText->SetText(FText::FromString(FString::Printf(TEXT("CASCO %3.0f%%   ·   COMBUSTÍVEL %3.0f%%   ·   NITRO %3.0f%%"),
		FMath::Clamp(Telemetry.HullIntegrity, 0.0f, 100.0f),
		FMath::Clamp(Telemetry.FuelFraction, 0.0f, 1.0f) * 100.0f,
		FMath::Clamp(Telemetry.Nitro, 0.0f, 1.0f) * 100.0f)));
	if (Telemetry.bDestroyed || Telemetry.bStranded)
	{
		VitalsText->SetColorAndOpacity(FSlateColor(FLinearColor(1.0f, 0.3f, 0.22f)));
	}
	else
	{
		VitalsText->SetColorAndOpacity(FSlateColor(FLinearColor(0.69f, 0.88f, 0.88f)));
	}
}
