#include "UI/EXHangarMenuWidget.h"

#include "EXGameMode.h"
#include "Flight/EXHoverCraft.h"
#include "GameFramework/PlayerController.h"
#include "Styling/CoreStyle.h"
#include "Widgets/SWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"

namespace
{
	FSlateFontInfo HangarFont(const TCHAR* Style, int32 Size)
	{
		return FCoreStyle::GetDefaultFontStyle(Style, Size);
	}

	FSlateColor HangarTextColour()
	{
		return FSlateColor(FLinearColor(0.91f, 0.94f, 0.98f));
	}
}

void UEXHangarMenuWidget::SetGameMode(AEXGameMode* InGameMode)
{
	GameMode = InGameMode;
	RefreshShipLabel();
}

TSharedRef<SWidget> UEXHangarMenuWidget::RebuildWidget()
{
	const TWeakObjectPtr<UEXHangarMenuWidget> WeakThis(this);
	const FSlateColor MainText = HangarTextColour();
	const FSlateColor MutedText(FLinearColor(0.56f, 0.68f, 0.77f));

	TSharedRef<SVerticalBox> Content = SNew(SVerticalBox);
	Content->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, 8.0f)
	[
		SNew(STextBlock)
		.Text(FText::FromString(TEXT("EXTRACTING / STARDUST")))
		.Font(HangarFont(TEXT("Bold"), 12))
		.ColorAndOpacity(FSlateColor(FLinearColor(0.96f, 0.43f, 0.16f)))
	];
	Content->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, 4.0f)
	[
		SNew(STextBlock)
		.Text(FText::FromString(TEXT("HANGAR")))
		.Font(HangarFont(TEXT("Bold"), 34))
		.ColorAndOpacity(MainText)
	];
	Content->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, 22.0f)
	[
		SNew(STextBlock)
		.Text(FText::FromString(TEXT("ESCOLHE A NAVE PARA A EXPEDICAO")))
		.Font(HangarFont(TEXT("Regular"), 12))
		.ColorAndOpacity(MutedText)
	];

	TSharedRef<SHorizontalBox> ShipPicker = SNew(SHorizontalBox);
	ShipPicker->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0.0f, 0.0f, 10.0f, 0.0f)
	[
		SNew(SButton)
		.OnClicked_Lambda([WeakThis]()
		{
			if (UEXHangarMenuWidget* Widget = WeakThis.Get())
			{
				if (AEXGameMode* Mode = Widget->GameMode.Get()) { Mode->CycleHangarShip(-1); }
				Widget->RefreshShipLabel();
			}
			return FReply::Handled();
		})
		[
			SNew(STextBlock).Text(FText::FromString(TEXT("<"))).Font(HangarFont(TEXT("Bold"), 24)).ColorAndOpacity(MainText)
		]
	];
	ShipPicker->AddSlot().FillWidth(1.0f).VAlign(VAlign_Center)
	[
		SAssignNew(ShipNameLabel, STextBlock)
		.Text(FText::FromString(TEXT("STRIX")))
		.Justification(ETextJustify::Center)
		.Font(HangarFont(TEXT("Bold"), 22))
		.ColorAndOpacity(MainText)
	];
	ShipPicker->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(10.0f, 0.0f, 0.0f, 0.0f)
	[
		SNew(SButton)
		.OnClicked_Lambda([WeakThis]()
		{
			if (UEXHangarMenuWidget* Widget = WeakThis.Get())
			{
				if (AEXGameMode* Mode = Widget->GameMode.Get()) { Mode->CycleHangarShip(1); }
				Widget->RefreshShipLabel();
			}
			return FReply::Handled();
		})
		[
			SNew(STextBlock).Text(FText::FromString(TEXT(">"))).Font(HangarFont(TEXT("Bold"), 24)).ColorAndOpacity(MainText)
		]
	];
	Content->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, 24.0f)
	[
		ShipPicker
	];
	Content->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, 4.0f)
	[
		SNew(SButton)
		.ButtonColorAndOpacity(FLinearColor(0.82f, 0.28f, 0.10f))
		.OnClicked_Lambda([WeakThis]()
		{
			if (UEXHangarMenuWidget* Widget = WeakThis.Get())
			{
				if (AEXGameMode* Mode = Widget->GameMode.Get()) { Mode->StartSurvivalRaceFromHangar(); }
			}
			return FReply::Handled();
		})
		[
			SNew(SBox).MinDesiredHeight(58.0f).HAlign(HAlign_Center).VAlign(VAlign_Center)
			[
				SNew(STextBlock).Text(FText::FromString(TEXT("CORRIDA DE SOBREVIVENCIA"))).Font(HangarFont(TEXT("Bold"), 15)).ColorAndOpacity(MainText)
			]
		]
	];
	Content->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, 16.0f)
	[
		SNew(STextBlock)
		.Text(FText::FromString(TEXT("Tu + 15 rivais  |  colisao e casco  |  ultimo a voar vence")))
		.Justification(ETextJustify::Center)
		.Font(HangarFont(TEXT("Regular"), 10))
		.ColorAndOpacity(MutedText)
		.AutoWrapText(true)
	];

	Content->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, 6.0f)
	[
		SNew(SButton)
		.ButtonColorAndOpacity(FLinearColor(0.13f, 0.28f, 0.38f))
		.OnClicked_Lambda([WeakThis]()
		{
			if (UEXHangarMenuWidget* Widget = WeakThis.Get())
			{
				if (AEXGameMode* Mode = Widget->GameMode.Get()) { Mode->StartFlightFromHangar(); }
			}
			return FReply::Handled();
		})
		[
			SNew(SBox).MinDesiredHeight(52.0f).HAlign(HAlign_Center).VAlign(VAlign_Center)
			[
				SNew(STextBlock).Text(FText::FromString(TEXT("INICIAR VOO"))).Font(HangarFont(TEXT("Bold"), 16)).ColorAndOpacity(MainText)
			]
		]
	];
	Content->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, 20.0f)
	[
		SNew(STextBlock)
		.Text(FText::FromString(TEXT("W / S acelerar e travar   |   A / D virar   |   Shift nitro")))
		.Font(HangarFont(TEXT("Regular"), 10))
		.ColorAndOpacity(MutedText)
		.AutoWrapText(true)
	];
	Content->AddSlot().AutoHeight()
	[
		SNew(SButton)
		.OnClicked_Lambda([WeakThis]()
		{
			if (UEXHangarMenuWidget* Widget = WeakThis.Get())
			{
				if (AEXGameMode* Mode = Widget->GameMode.Get()) { Mode->QuitFromHangar(); }
			}
			return FReply::Handled();
		})
		[
			SNew(STextBlock).Text(FText::FromString(TEXT("SAIR DO JOGO"))).Font(HangarFont(TEXT("Bold"), 11)).ColorAndOpacity(MutedText)
		]
	];

	return SNew(SOverlay)
		+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Center).Padding(FMargin(48.0f))
		[
			SNew(SBorder)
			.BorderBackgroundColor(FLinearColor(0.025f, 0.04f, 0.065f, 0.94f))
			.Padding(FMargin(28.0f))
			[
				SNew(SBox).WidthOverride(390.0f)
			[
				Content
			]
			]
		];
}

void UEXHangarMenuWidget::RefreshShipLabel()
{
	if (!ShipNameLabel.IsValid())
	{
		return;
	}
	const APlayerController* PlayerController = GameMode.IsValid() && GameMode->GetWorld()
		? GameMode->GetWorld()->GetFirstPlayerController()
		: nullptr;
	const AEXHoverCraft* Craft = PlayerController ? Cast<AEXHoverCraft>(PlayerController->GetPawn()) : nullptr;
	ShipNameLabel->SetText(FText::FromString(Craft ? Craft->GetSelectedShipName() : FString(TEXT("STRIX"))));
}
