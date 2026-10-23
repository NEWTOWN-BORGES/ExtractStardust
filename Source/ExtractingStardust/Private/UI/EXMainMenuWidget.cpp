#include "UI/EXMainMenuWidget.h"

#include "Blueprint/WidgetTree.h"
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
#include "Kismet/GameplayStatics.h"
#include "Race/EXRaceDirector.h"
#include "Styling/CoreStyle.h"

namespace
{
	const FLinearColor Dust(0.035f, 0.020f, 0.012f, 0.88f);
	const FLinearColor Plate(0.070f, 0.038f, 0.018f, 0.92f);
	const FLinearColor PlateHot(0.16f, 0.055f, 0.018f, 0.96f);
	const FLinearColor Rust(0.92f, 0.34f, 0.10f, 1.0f);
	const FLinearColor Bone(0.95f, 0.90f, 0.80f, 1.0f);
	const FLinearColor Sand(0.62f, 0.50f, 0.36f, 1.0f);

	FSlateBrush Solid(const FLinearColor& Color)
	{
		FSlateBrush Brush;
		Brush.DrawAs = ESlateBrushDrawType::Box;
		Brush.TintColor = FSlateColor(Color);
		return Brush;
	}

	FSlateFontInfo Type(int32 Size, bool bBold = false)
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

	UOverlay* Root = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("Root"));
	WidgetTree->RootWidget = Root;

	auto AddText = [this](UVerticalBox* Parent, const FString& Value, int32 Size, const FLinearColor& Color,
		bool bBold, const FMargin& Pad, ETextJustify::Type Align = ETextJustify::Left) -> UTextBlock*
	{
		UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
		Text->SetText(FText::FromString(Value));
		Text->SetFont(Type(Size, bBold));
		Text->SetColorAndOpacity(FSlateColor(Color));
		Text->SetAutoWrapText(true);
		Text->SetJustification(Align);
		UVerticalBoxSlot* Slot = Parent->AddChildToVerticalBox(Text);
		Slot->SetPadding(Pad);
		return Text;
	};

	USizeBox* DockSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("Dock"));
	DockSize->SetWidthOverride(520.0f);
	UBorder* Dock = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("DockFill"));
	Dock->SetBrushColor(Dust);
	Dock->SetPadding(FMargin(36.0f, 40.0f, 32.0f, 28.0f));
	DockSize->AddChild(Dock);
	UOverlaySlot* DockSlot = Root->AddChildToOverlay(DockSize);
	DockSlot->SetHorizontalAlignment(HAlign_Left);
	DockSlot->SetVerticalAlignment(VAlign_Fill);

	UVerticalBox* Col = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Brief"));
	Dock->SetContent(Col);

	AddText(Col, TEXT("EXPEDIÇÃO  ·  RED DUST DIVIDE"), 11, Rust, true, FMargin(0, 0, 0, 8));
	AddText(Col, TEXT("EXTRACT"), 14, Sand, true, FMargin(0, 0, 0, 0));
	AddText(Col, TEXT("STARDUST"), 36, Bone, true, FMargin(0, -4, 0, 6));
	AddText(Col, TEXT("RACE.  SURVIVE.  EXTRACT."), 12, Rust, true, FMargin(0, 0, 0, 10));
	AddText(Col, TEXT("A → B. Quem cai perde o que levava. Quem corta a meta extrai."), 13, Sand, false,
		FMargin(0, 0, 0, 22));

	ModeButtons.Add(CreateModeButton(Col, TEXT("01"), TEXT("SOLO"),
		TEXT("Tu sozinho contra o deserto. Chega vivo a B.")));
	ModeButtons.Last()->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnSoloPressed);
	ModeButtons.Add(CreateModeButton(Col, TEXT("02"), TEXT("PELOTÃO 15"),
		TEXT("Quinze rivais. Só quem sobrevive extrai.")));
	ModeButtons.Last()->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnBotsPressed);
	ModeButtons.Add(CreateModeButton(Col, TEXT("03"), TEXT("HANGAR"),
		TEXT("Inspecciona as naves. Rato ou sticks para orbitar.")));
	ModeButtons.Last()->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnHangarPressed);

	AddText(Col, TEXT("NAVE"), 10, Rust, true, FMargin(0, 18, 0, 8));
	UHorizontalBox* ShipRow = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass(), TEXT("ShipRow"));
	Col->AddChildToVerticalBox(ShipRow);

	auto MakeChevron = [this](const FString& Label) -> UButton*
	{
		UButton* Btn = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass());
		Btn->SetIsFocusable(true);
		ApplyButtonStyle(Btn, Plate, PlateHot, Rust);
		UTextBlock* Txt = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
		Txt->SetText(FText::FromString(Label));
		Txt->SetFont(Type(22, true));
		Txt->SetColorAndOpacity(FSlateColor(Bone));
		Txt->SetJustification(ETextJustify::Center);
		Btn->AddChild(Txt);
		USizeBox* Box = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
		Box->SetWidthOverride(44.0f);
		Box->SetHeightOverride(44.0f);
		Box->AddChild(Btn);
		return Btn;
	};

	UButton* PrevShip = MakeChevron(TEXT("‹"));
	PrevShip->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnPreviousShipPressed);
	ShipRow->AddChildToHorizontalBox(PrevShip->GetParent());
	USizeBox* NameBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	NameBox->SetWidthOverride(280.0f);
	ShipNameText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("ShipName"));
	ShipNameText->SetFont(Type(18, true));
	ShipNameText->SetColorAndOpacity(FSlateColor(Bone));
	ShipNameText->SetJustification(ETextJustify::Center);
	NameBox->AddChild(ShipNameText);
	UHorizontalBoxSlot* NameSlot = ShipRow->AddChildToHorizontalBox(NameBox);
	NameSlot->SetVerticalAlignment(VAlign_Center);
	UButton* NextShip = MakeChevron(TEXT("›"));
	NextShip->OnClicked.AddDynamic(this, &UEXMainMenuWidget::OnNextShipPressed);
	ShipRow->AddChildToHorizontalBox(NextShip->GetParent());

	AddText(Col, TEXT("ENTER confirma   ·   W/S navega   ·   Tab troca nave"), 10, Sand, false, FMargin(0, 20, 0, 0));
	RefreshShipName();
	RefreshSelection();
}

UButton* UEXMainMenuWidget::CreateModeButton(UVerticalBox* Parent, const FString& Number, const FString& Title,
	const FString& Description)
{
	UButton* Button = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass());
	Button->SetIsFocusable(true);
	ApplyButtonStyle(Button, Plate, PlateHot, Rust);

	USizeBox* Size = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	Size->SetWidthOverride(452.0f);
	Size->SetHeightOverride(86.0f);
	UHorizontalBox* Row = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	Size->AddChild(Row);
	Button->AddChild(Size);

	USizeBox* BarSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	BarSize->SetWidthOverride(5.0f);
	BarSize->SetHeightOverride(86.0f);
	UBorder* Bar = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass());
	Bar->SetBrushColor(Rust);
	BarSize->AddChild(Bar);
	Row->AddChildToHorizontalBox(BarSize);

	USizeBox* NumSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	NumSize->SetWidthOverride(56.0f);
	UTextBlock* Num = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	Num->SetText(FText::FromString(Number));
	Num->SetFont(Type(18, true));
	Num->SetColorAndOpacity(FSlateColor(Rust));
	Num->SetJustification(ETextJustify::Center);
	NumSize->AddChild(Num);
	UHorizontalBoxSlot* NumSlot = Row->AddChildToHorizontalBox(NumSize);
	NumSlot->SetVerticalAlignment(VAlign_Center);

	UVerticalBox* Copy = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UTextBlock* TitleText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	TitleText->SetText(FText::FromString(Title));
	TitleText->SetFont(Type(16, true));
	TitleText->SetColorAndOpacity(FSlateColor(Bone));
	Copy->AddChildToVerticalBox(TitleText);
	UTextBlock* Desc = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	Desc->SetText(FText::FromString(Description));
	Desc->SetFont(Type(12));
	Desc->SetColorAndOpacity(FSlateColor(Sand));
	Desc->SetAutoWrapText(true);
	UVerticalBoxSlot* DescSlot = Copy->AddChildToVerticalBox(Desc);
	DescSlot->SetPadding(FMargin(0, 4, 8, 0));
	UHorizontalBoxSlot* CopySlot = Row->AddChildToHorizontalBox(Copy);
	CopySlot->SetVerticalAlignment(VAlign_Center);
	CopySlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

	UVerticalBoxSlot* ParentSlot = Parent->AddChildToVerticalBox(Button);
	ParentSlot->SetPadding(FMargin(0, 0, 0, 8));
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
	Style.SetNormal(Solid(Normal));
	Style.SetHovered(Solid(Hovered));
	Style.SetPressed(Solid(Pressed));
	Style.ContentPadding = FMargin(0.0f);
	Button->SetStyle(Style);
}

void UEXMainMenuWidget::SetSelectedChoice(int32 Choice)
{
	const int32 NewChoice = FMath::Clamp(Choice, 0, 2);
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
		const bool bOn = SelectedChoice == Index;
		ApplyButtonStyle(ModeButtons[Index], bOn ? PlateHot : Plate, PlateHot, Rust);
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
void UEXMainMenuWidget::OnBotsPressed() { StartChoice(1); }
void UEXMainMenuWidget::OnHangarPressed() { StartChoice(2); }

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
