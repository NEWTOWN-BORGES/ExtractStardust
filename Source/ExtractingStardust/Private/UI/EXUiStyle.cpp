#include "UI/EXUiStyle.h"

#include "Blueprint/WidgetTree.h"
#include "Brushes/SlateColorBrush.h"
#include "Components/Border.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Styling/CoreStyle.h"

namespace EXUi
{
	FLinearColor Hex(uint8 R, uint8 G, uint8 B, float A)
	{
		FLinearColor Colour = FLinearColor(FColor(R, G, B));
		Colour.A = A;
		return Colour;
	}

	FLinearColor Rust(float A) { return Hex(235, 87, 26, A); }
	FLinearColor RustHot(float A) { return Hex(255, 122, 58, A); }
	FLinearColor Bone(float A) { return Hex(242, 230, 204, A); }
	FLinearColor Sand(float A) { return Hex(168, 140, 106, A); }
	FLinearColor Dim(float A) { return Hex(111, 90, 68, A); }
	FLinearColor Ok(float A) { return Hex(123, 224, 138, A); }
	FLinearColor Ink(float A) { return Hex(10, 6, 4, A); }
	FLinearColor Plate(float A) { return Hex(22, 12, 7, A); }

	FSlateFontInfo Font(int32 Size, bool bBold, int32 LetterSpacing)
	{
		FSlateFontInfo Info = FCoreStyle::GetDefaultFontStyle(bBold ? TEXT("Bold") : TEXT("Regular"), Size);
		Info.LetterSpacing = LetterSpacing;
		return Info;
	}

	FString Thousands(int32 Value)
	{
		const FString Digits = FString::FromInt(FMath::Abs(Value));
		FString Grouped;
		for (int32 Index = 0; Index < Digits.Len(); ++Index)
		{
			if (Index > 0 && (Digits.Len() - Index) % 3 == 0)
			{
				Grouped.AppendChar(TEXT(' '));
			}
			Grouped.AppendChar(Digits[Index]);
		}
		return Value < 0 ? FString(TEXT("-")) + Grouped : Grouped;
	}

	UTextBlock* Text(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, bool bBold, int32 Spacing)
	{
		UTextBlock* Block = Tree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
		Block->SetText(FText::FromString(Value));
		Block->SetFont(Font(Size, bBold, Spacing));
		Block->SetColorAndOpacity(FSlateColor(Color));
		return Block;
	}

	UTextBlock* OutlinedText(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, int32 Spacing, int32 OutlineSize,
		const FLinearColor& OutlineColor)
	{
		UTextBlock* Block = Text(Tree, Value, Size, Color, true, Spacing);
		FSlateFontInfo Info = Font(Size, true, Spacing);
		Info.OutlineSettings.OutlineSize = OutlineSize;
		Info.OutlineSettings.OutlineColor = OutlineColor;
		Block->SetFont(Info);
		return Block;
	}

	void SetText(UTextBlock* Block, const FString& Value)
	{
		if (Block && !Block->GetText().ToString().Equals(Value, ESearchCase::CaseSensitive))
		{
			Block->SetText(FText::FromString(Value));
		}
	}

	UBorder* Box(UWidgetTree* Tree, const FLinearColor& Color, const FMargin& Padding, UWidget* Content)
	{
		UBorder* Border = Tree->ConstructWidget<UBorder>(UBorder::StaticClass());
		Border->SetBrush(FSlateColorBrush(FLinearColor::White));
		Border->SetBrushColor(Color);
		Border->SetPadding(Padding);
		if (Content)
		{
			Border->SetContent(Content);
		}
		return Border;
	}

	USizeBox* Sized(UWidgetTree* Tree, float Width, float Height, UWidget* Content)
	{
		USizeBox* Holder = Tree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
		if (Width > 0.0f)
		{
			Holder->SetWidthOverride(Width);
		}
		if (Height > 0.0f)
		{
			Holder->SetHeightOverride(Height);
		}
		if (Content)
		{
			Holder->AddChild(Content);
		}
		return Holder;
	}

	void FFrame::SetOutline(const FLinearColor& Color) const
	{
		for (UBorder* Edge : Edges)
		{
			if (Edge)
			{
				Edge->SetBrushColor(Color);
			}
		}
	}

	FFrame Frame(UWidgetTree* Tree, const FLinearColor& Outline, const FLinearColor& Fill, float OutlineWidth, const FMargin& Padding,
		float TopWidth)
	{
		FFrame Result;
		Result.Root = Tree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
		Result.Fill = Box(Tree, Fill, Padding);
		AddO(Result.Root, Result.Fill, HAlign_Fill, VAlign_Fill);
		const float Top = TopWidth > 0.0f ? TopWidth : OutlineWidth;
		const float Thickness[4] = { Top, OutlineWidth, OutlineWidth, OutlineWidth };
		for (int32 Side = 0; Side < 4; ++Side)
		{
			Result.Edges[Side] = Box(Tree, Outline);
			const bool bHorizontal = Side < 2;
			USizeBox* Holder = Sized(Tree, bHorizontal ? 0.0f : Thickness[Side], bHorizontal ? Thickness[Side] : 0.0f, Result.Edges[Side]);
			AddO(Result.Root, Holder, bHorizontal ? HAlign_Fill : (Side == 2 ? HAlign_Left : HAlign_Right),
				bHorizontal ? (Side == 0 ? VAlign_Top : VAlign_Bottom) : VAlign_Fill);
		}
		return Result;
	}

	UWidget* KeyCap(UWidgetTree* Tree, const FString& Key, bool bDark)
	{
		const FFrame Cap = Frame(Tree, bDark ? Ink(0.8f) : Sand(), bDark ? Ink(0.0f) : Bone(0.04f), 1.0f, FMargin(8.0f, 2.0f));
		UTextBlock* Label = Text(Tree, Key, 11, bDark ? Ink() : Bone(), true);
		Label->SetJustification(ETextJustify::Center);
		Cap.Fill->SetContent(Label);
		Cap.Fill->SetHorizontalAlignment(HAlign_Center);
		Cap.Fill->SetVerticalAlignment(VAlign_Center);
		USizeBox* Holder = Sized(Tree, 0.0f, 29.0f, Cap.Root);
		Holder->SetMinDesiredWidth(31.0f);
		return Holder;
	}

	UHorizontalBox* Hint(UWidgetTree* Tree, const TArray<FString>& Keys, const FString& Label)
	{
		UHorizontalBox* Row = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		for (const FString& Key : Keys)
		{
			AddH(Row, KeyCap(Tree, Key), FMargin(0.0f, 0.0f, 7.0f, 0.0f));
		}
		AddH(Row, Text(Tree, Label, 12, Sand(), false), FMargin(2.0f, 0.0f, 0.0f, 0.0f));
		return Row;
	}

	UWidget* Gem(UWidgetTree* Tree, float Size, const FLinearColor& Color)
	{
		USizeBox* Holder = Sized(Tree, Size, Size, Box(Tree, Color));
		Holder->SetRenderTransformAngle(45.0f);
		return Holder;
	}

	UHorizontalBox* Fade(UWidgetTree* Tree, const FLinearColor& Color, float LeftAlpha, float RightAlpha, int32 Strips)
	{
		UHorizontalBox* Row = Tree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		for (int32 Strip = 0; Strip < Strips; ++Strip)
		{
			FLinearColor StripColor = Color;
			StripColor.A = FMath::Lerp(LeftAlpha, RightAlpha, (Strip + 0.5f) / Strips);
			AddH(Row, Box(Tree, StripColor), FMargin(0.0f), true, VAlign_Fill);
		}
		return Row;
	}

	UHorizontalBoxSlot* AddH(UHorizontalBox* Parent, UWidget* Child, const FMargin& Padding, bool bFill, EVerticalAlignment VAlign)
	{
		UHorizontalBoxSlot* ChildSlot = Parent->AddChildToHorizontalBox(Child);
		ChildSlot->SetPadding(Padding);
		ChildSlot->SetVerticalAlignment(VAlign);
		if (bFill)
		{
			ChildSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
		}
		return ChildSlot;
	}

	UVerticalBoxSlot* AddV(UVerticalBox* Parent, UWidget* Child, const FMargin& Padding, EHorizontalAlignment HAlign)
	{
		UVerticalBoxSlot* ChildSlot = Parent->AddChildToVerticalBox(Child);
		ChildSlot->SetPadding(Padding);
		ChildSlot->SetHorizontalAlignment(HAlign);
		return ChildSlot;
	}

	UOverlaySlot* AddO(UOverlay* Parent, UWidget* Child, EHorizontalAlignment HAlign, EVerticalAlignment VAlign, const FMargin& Padding)
	{
		UOverlaySlot* ChildSlot = Parent->AddChildToOverlay(Child);
		ChildSlot->SetHorizontalAlignment(HAlign);
		ChildSlot->SetVerticalAlignment(VAlign);
		ChildSlot->SetPadding(Padding);
		return ChildSlot;
	}
}
