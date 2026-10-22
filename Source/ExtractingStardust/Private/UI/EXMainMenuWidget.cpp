#include "UI/EXMainMenuWidget.h"

#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Flight/EXHoverCraft.h"
#include "Race/EXRaceDirector.h"
#include "Blueprint/WidgetTree.h"
#include "Kismet/GameplayStatics.h"
#include "Styling/CoreStyle.h"

namespace
{
	const FLinearColor MenuInk(0.018f, 0.030f, 0.047f, 1.0f);
	const FLinearColor MenuPanel(0.030f, 0.052f, 0.077f, 1.0f);
	const FLinearColor MenuCard(0.055f, 0.087f, 0.119f, 1.0f);
	const FLinearColor MenuAmber(0.98f, 0.43f, 0.12f, 1.0f);
	const FLinearColor MenuPaper(0.93f, 0.95f, 0.96f, 1.0f);
	const FLinearColor MenuMuted(0.57f, 0.66f, 0.72f, 1.0f);

	FSlateBrush MakeMenuBrush(const FLinearColor& Color)
	{
		FSlateBrush Brush;
		Brush.DrawAs = ESlateBrushDrawType::Box;
		Brush.TintColor = FSlateColor(Color);
		return Brush;
	}

	FSlateFontInfo MenuFont(int32 Size, bool bBold = false)
	{
		return FCoreStyle::GetDefaultFontStyle(bBold ? TEXT("Bold") : TEXT("Regular"), Size);
	}
}

void UEXMainMenuWidget::InitializeMenu(AEXRaceDirector* InRaceDirector)
{
	RaceDirector = InRaceDirector;
	if (RaceDirector)
	{
		SelectedChoice = RaceDirector->GetMenuChoice();
	}
}

void UEXMainMenuWidget::NativeConstruct()
{
	Super::NativeConstruct();
	if (!WidgetTree)
	{
		return;
	}

	ModeButtons.Reset();
	UOverlay* Root = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("MenuRoot"));
	WidgetTree->RootWidget = Root;

	UBorder* Backdrop = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Backdrop"));
	Backdrop->SetBrushColor(MenuInk);
	UOverlaySlot* BackdropSlot = Root->AddChildToOverlay(Backdrop);
	BackdropSlot->SetHorizontalAlignment(HAlign_Fill);
	BackdropSlot->SetVerticalAlignment(VAlign_Fill);

	USizeBox* PanelSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("PanelSize"));
	PanelSize->SetWidthOverride(1210.0f);
	PanelSize->SetHeightOverride(670.0f);
	UBorder* Panel = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Panel"));
	Panel->SetBrushColor(MenuPanel);
	Panel->SetPadding(FMargin(38.0f, 34.0f));
	PanelSize->AddChild(Panel);
	UOverlaySlot* PanelSlot = Root->AddChildToOverlay(PanelSize);
	PanelSlot->SetHorizontalAlignment(HAlign_Center);
	PanelSlot->SetVerticalAlignment(VAlign_Center);

	UHorizontalBox* Columns = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass(), TEXT("Columns"));
	Panel->SetContent(Columns);

	USizeBox* LeftColumnSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("BrandColumnSize"));
	LeftColumnSize->SetWidthOverride(350.0f);
	UVerticalBox* LeftColumn = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("BrandColumn"));
	LeftColumnSize->AddChild(LeftColumn);
	UHorizontalBoxSlot* LeftSlot = Columns->AddChildToHorizontalBox(LeftColumnSize);
	LeftSlot->SetPadding(FMargin(0.0f, 0.0f, 42.0f, 0.0f));

	USizeBox* RightColumnSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("ModeColumnSize"));
	RightColumnSize->SetWidthOverride(700.0f);
	UVerticalBox* RightColumn = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("ModeColumn"));
	RightColumnSize->AddChild(RightColumn);
	Columns->AddChildToHorizontalBox(RightColumnSize);

	auto AddText = [this](UVerticalBox* Parent, const FString& Value, int32 Size, const FLinearColor& Color,
		bool bBold, const FMargin& Padding) -> UTextBlock*
	{
		UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
		Text->SetText(FText::FromString(Value));
		Text->SetFont(MenuFont(Size, bBold));
		Text->SetColorAndOpacity(FSlateColor(Color));
		Text->SetAutoWrapText(true);
		UVerticalBoxSlot* Slot = Parent->AddChildToVerticalBox(Text);
		Slot->SetPadding(Padding);
		return Text;
	};

	AddText(LeftColumn, TEXT("EXTRACTING"), 18, MenuAmber, true, FMargin(0.0f, 6.0f, 0.0f, 0.0f));
	AddText(LeftColumn, TEXT("STARDUST"), 42, MenuPaper, true, FMargin(0.0f, 0.0f, 0.0f, 4.0f));
	AddText(LeftColumn, TEXT("RED DUST DIVIDE"), 13, MenuMuted, true, FMargin(0.0f, 0.0f, 0.0f, 26.0f));

	UBorder* Divider = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Divider"));
	Divider->SetBrushColor(MenuAmber);
	Divider->SetPadding(FMargin(0.0f));
	USizeBox* DividerSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	DividerSize->SetHeightOverride(2.0f);
	DividerSize->SetContent(Divider);
	UVerticalBoxSlot* DividerSlot = LeftColumn->AddChildToVerticalBox(DividerSize);
	DividerSlot->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 24.0f));

	AddText(LeftColumn, TEXT("A TRAVESSIA COMEÇA AQUI"), 19, MenuPaper, true, FMargin(0.0f, 0.0f, 0.0f, 9.0f));
	AddText(LeftColumn, TEXT("Escolhe a tua forma de atravessar o deserto. Cada nave responde de maneira diferente."), 15,
		MenuMuted, false, FMargin(0.0f, 0.0f, 0.0f, 34.0f));
	AddText(LeftColumn, TEXT("NAVE DE PARTIDA"), 12, MenuAmber, true, FMargin(0.0f, 0.0f, 0.0f, 10.0f));

	UHorizontalBox* ShipPicker = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass(), TEXT("ShipPicker"));
	LeftColumn->AddChildToVerticalBox(ShipPicker);
	UButton* PreviousShip = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), TEXT("PreviousShip"));
	PreviousShip->SetIsFocusable(true);
	PreviousShip->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnPreviousShipPressed);
	ApplyButtonStyle(PreviousShip, MenuCard, FLinearColor(0.10f, 0.15f, 0.19f), MenuAmber);
	UTextBlock* PreviousShipText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	PreviousShipText->SetText(FText::FromString(TEXT("‹")));
	PreviousShipText->SetFont(MenuFont(25, true));
	PreviousShipText->SetColorAndOpacity(FSlateColor(MenuPaper));
	PreviousShip->AddChild(PreviousShipText);
	USizeBox* PreviousSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	PreviousSize->SetWidthOverride(48.0f);
	PreviousSize->SetHeightOverride(46.0f);
	PreviousSize->AddChild(PreviousShip);
	ShipPicker->AddChildToHorizontalBox(PreviousSize);

	USizeBox* ShipNameSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("ShipNameSize"));
	ShipNameSize->SetWidthOverride(205.0f);
	UVerticalBox* ShipNameStack = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	ShipNameText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("ShipName"));
	ShipNameText->SetFont(MenuFont(18, true));
	ShipNameText->SetColorAndOpacity(FSlateColor(MenuPaper));
	ShipNameText->SetJustification(ETextJustify::Center);
	ShipNameStack->AddChildToVerticalBox(ShipNameText);
	UTextBlock* ShipHint = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	ShipHint->SetText(FText::FromString(TEXT("TAB OU SETAS PARA TROCAR")));
	ShipHint->SetFont(MenuFont(9));
	ShipHint->SetColorAndOpacity(FSlateColor(MenuMuted));
	ShipHint->SetJustification(ETextJustify::Center);
	ShipNameStack->AddChildToVerticalBox(ShipHint);
	ShipNameSize->AddChild(ShipNameStack);
	UHorizontalBoxSlot* ShipNameSlot = ShipPicker->AddChildToHorizontalBox(ShipNameSize);
	ShipNameSlot->SetVerticalAlignment(VAlign_Center);

	UButton* NextShip = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), TEXT("NextShip"));
	NextShip->SetIsFocusable(true);
	NextShip->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnNextShipPressed);
	ApplyButtonStyle(NextShip, MenuCard, FLinearColor(0.10f, 0.15f, 0.19f), MenuAmber);
	UTextBlock* NextShipText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	NextShipText->SetText(FText::FromString(TEXT("›")));
	NextShipText->SetFont(MenuFont(25, true));
	NextShipText->SetColorAndOpacity(FSlateColor(MenuPaper));
	NextShip->AddChild(NextShipText);
	USizeBox* NextSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	NextSize->SetWidthOverride(48.0f);
	NextSize->SetHeightOverride(46.0f);
	NextSize->AddChild(NextShip);
	ShipPicker->AddChildToHorizontalBox(NextSize);

	AddText(LeftColumn, TEXT("H = KIT MÉDICO DURANTE A CORRIDA"), 11, MenuMuted, false, FMargin(0.0f, 22.0f, 0.0f, 0.0f));

	AddText(RightColumn, TEXT("SELECIONA UM MODO"), 14, MenuAmber, true, FMargin(0.0f, 2.0f, 0.0f, 2.0f));
	AddText(RightColumn, TEXT("A tua próxima corrida"), 28, MenuPaper, true, FMargin(0.0f, 0.0f, 0.0f, 18.0f));

	ModeButtons.Add(CreateModeButton(RightColumn, TEXT("01"), TEXT("CONTRA O CRONÓMETRO"),
		TEXT("Corrida a solo. Faz o melhor tempo e chega vivo à meta."), FLinearColor(0.21f, 0.71f, 0.91f, 1.0f)));
	ModeButtons.Last()->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnSoloPressed);
	ModeButtons.Add(CreateModeButton(RightColumn, TEXT("02"), TEXT("SOBREVIVÊNCIA"),
		TEXT("Tu contra 15 rivais. Colisões, vidas e 3 kits médicos só para ti."), MenuAmber));
	ModeButtons.Last()->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnSurvivalPressed);
	ModeButtons.Add(CreateModeButton(RightColumn, TEXT("03"), TEXT("VOO LIVRE"),
		TEXT("Explora a pista sem cronómetro, adversários ou regras de corrida."), FLinearColor(0.35f, 0.78f, 0.57f, 1.0f)));
	ModeButtons.Last()->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnFreeFlightPressed);

	HangarButton = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), TEXT("HangarButton"));
	HangarButton->SetIsFocusable(true);
	HangarButton->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnHangarPressed);
	ApplyButtonStyle(HangarButton, MenuCard, FLinearColor(0.10f, 0.15f, 0.19f), MenuAmber);
	UTextBlock* HangarText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	HangarText->SetText(FText::FromString(TEXT("HANGAR DE NAVES     ·     INSPECIONAR")));
	HangarText->SetFont(MenuFont(12, true));
	HangarText->SetColorAndOpacity(FSlateColor(MenuPaper));
	HangarText->SetJustification(ETextJustify::Center);
	HangarButton->AddChild(HangarText);
	USizeBox* HangarSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	HangarSize->SetWidthOverride(340.0f);
	HangarSize->SetHeightOverride(44.0f);
	HangarSize->AddChild(HangarButton);
	UVerticalBoxSlot* HangarSlot = RightColumn->AddChildToVerticalBox(HangarSize);
	HangarSlot->SetPadding(FMargin(0.0f, 2.0f, 0.0f, 0.0f));

	AddText(RightColumn, TEXT("ENTER / A CONFIRMA     ·     SETAS / W-S NAVEGAM"), 10, MenuMuted, false,
		FMargin(0.0f, 14.0f, 0.0f, 0.0f));
	RefreshShipName();
	RefreshSelection();
}

UButton* UEXMainMenuWidget::CreateModeButton(UVerticalBox* Parent, const FString& Number, const FString& Title,
	const FString& Description, const FLinearColor& Accent)
{
	UButton* Button = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass());
	Button->SetIsFocusable(true);
	ApplyButtonStyle(Button, MenuCard, FLinearColor(0.09f, 0.14f, 0.18f), Accent);

	USizeBox* ButtonSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	ButtonSize->SetWidthOverride(660.0f);
	ButtonSize->SetHeightOverride(112.0f);
	UHorizontalBox* Content = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	ButtonSize->AddChild(Content);
	Button->AddChild(ButtonSize);

	USizeBox* AccentSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	AccentSize->SetWidthOverride(6.0f);
	AccentSize->SetHeightOverride(112.0f);
	UBorder* AccentBar = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass());
	AccentBar->SetBrushColor(Accent);
	AccentSize->AddChild(AccentBar);
	Content->AddChildToHorizontalBox(AccentSize);

	USizeBox* NumberSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	NumberSize->SetWidthOverride(72.0f);
	UTextBlock* NumberText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	NumberText->SetText(FText::FromString(Number));
	NumberText->SetFont(MenuFont(25, true));
	NumberText->SetColorAndOpacity(FSlateColor(Accent));
	NumberText->SetJustification(ETextJustify::Center);
	NumberSize->AddChild(NumberText);
	UHorizontalBoxSlot* NumberSlot = Content->AddChildToHorizontalBox(NumberSize);
	NumberSlot->SetVerticalAlignment(VAlign_Center);

	UVerticalBox* Copy = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UTextBlock* TitleText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	TitleText->SetText(FText::FromString(Title));
	TitleText->SetFont(MenuFont(17, true));
	TitleText->SetColorAndOpacity(FSlateColor(MenuPaper));
	Copy->AddChildToVerticalBox(TitleText);
	UTextBlock* DescriptionText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	DescriptionText->SetText(FText::FromString(Description));
	DescriptionText->SetFont(MenuFont(13));
	DescriptionText->SetColorAndOpacity(FSlateColor(MenuMuted));
	DescriptionText->SetAutoWrapText(true);
	UVerticalBoxSlot* DescriptionSlot = Copy->AddChildToVerticalBox(DescriptionText);
	DescriptionSlot->SetPadding(FMargin(0.0f, 5.0f, 0.0f, 0.0f));
	UHorizontalBoxSlot* CopySlot = Content->AddChildToHorizontalBox(Copy);
	CopySlot->SetVerticalAlignment(VAlign_Center);
	CopySlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

	UVerticalBoxSlot* ParentSlot = Parent->AddChildToVerticalBox(Button);
	ParentSlot->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 10.0f));
	return Button;
}

void UEXMainMenuWidget::ApplyButtonStyle(UButton* Button, const FLinearColor& Normal, const FLinearColor& Hovered,
	const FLinearColor& Pressed)
{
	if (!Button)
	{
		return;
	}
	FButtonStyle Style;
	Style.SetNormal(MakeMenuBrush(Normal));
	Style.SetHovered(MakeMenuBrush(Hovered));
	Style.SetPressed(MakeMenuBrush(Pressed));
	Style.ContentPadding = FMargin(0.0f);
	Button->SetStyle(Style);
}

void UEXMainMenuWidget::SetSelectedChoice(int32 Choice)
{
	const int32 NewChoice = FMath::Clamp(Choice, 0, 3);
	if (NewChoice != SelectedChoice)
	{
		SelectedChoice = NewChoice;
		RefreshSelection();
	}
	RefreshShipName();
}

void UEXMainMenuWidget::RefreshSelection()
{
	for (int32 Index = 0; Index < ModeButtons.Num(); ++Index)
	{
		const bool bSelected = SelectedChoice == Index;
		const FLinearColor Accent = Index == 0 ? FLinearColor(0.21f, 0.71f, 0.91f, 1.0f)
			: Index == 1 ? MenuAmber : FLinearColor(0.35f, 0.78f, 0.57f, 1.0f);
		ApplyButtonStyle(ModeButtons[Index], bSelected ? FLinearColor(0.18f, 0.10f, 0.07f, 1.0f) : MenuCard,
			bSelected ? FLinearColor(0.24f, 0.13f, 0.08f, 1.0f) : FLinearColor(0.09f, 0.14f, 0.18f), Accent);
	}
	if (HangarButton)
	{
		ApplyButtonStyle(HangarButton, SelectedChoice == 3 ? FLinearColor(0.18f, 0.10f, 0.07f, 1.0f) : MenuCard,
			FLinearColor(0.10f, 0.15f, 0.19f), MenuAmber);
	}
}

void UEXMainMenuWidget::RefreshShipName()
{
	if (ShipNameText)
	{
		if (const AEXHoverCraft* Craft = GetPlayerCraft())
		{
			ShipNameText->SetText(FText::FromString(Craft->GetShipName().ToUpper()));
		}
	}
}

AEXHoverCraft* UEXMainMenuWidget::GetPlayerCraft() const
{
	return Cast<AEXHoverCraft>(UGameplayStatics::GetPlayerPawn(this, 0));
}

void UEXMainMenuWidget::StartChoice(int32 Choice)
{
	if (RaceDirector)
	{
		RaceDirector->StartMenuChoice(Choice);
	}
}

void UEXMainMenuWidget::OnSoloPressed() { StartChoice(0); }
void UEXMainMenuWidget::OnSurvivalPressed() { StartChoice(1); }
void UEXMainMenuWidget::OnFreeFlightPressed() { StartChoice(2); }
void UEXMainMenuWidget::OnHangarPressed() { StartChoice(3); }

void UEXMainMenuWidget::OnPreviousShipPressed()
{
	if (AEXHoverCraft* Craft = GetPlayerCraft())
	{
		Craft->SelectShip(Craft->GetShipIndex() - 1);
		RefreshShipName();
	}
}

void UEXMainMenuWidget::OnNextShipPressed()
{
	if (AEXHoverCraft* Craft = GetPlayerCraft())
	{
		Craft->SelectShip(Craft->GetShipIndex() + 1);
		RefreshShipName();
	}
}
