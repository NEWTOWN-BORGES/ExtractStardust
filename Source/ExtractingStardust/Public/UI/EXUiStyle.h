#pragma once

#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"
#include "Layout/Margin.h"
#include "Types/SlateEnums.h"

class UBorder;
class UHorizontalBox;
class UHorizontalBoxSlot;
class UOverlay;
class UOverlaySlot;
class USizeBox;
class UTextBlock;
class UVerticalBox;
class UVerticalBoxSlot;
class UWidget;
class UWidgetTree;

/**
 * The look shared by the menu and the hangar (the mock-ups the player approved, Docs/MENU_HANGAR.md): dark rust plates,
 * an orange accent and bone text. Sizes are Slate units at 1920 x 1080; UMG scales them with the screen.
 */
namespace EXUi
{
	/** An sRGB colour as the mock-ups give it. */
	FLinearColor Hex(uint8 R, uint8 G, uint8 B, float A = 1.0f);
	FLinearColor Rust(float A = 1.0f);      // #eb571a, the accent
	FLinearColor RustHot(float A = 1.0f);   // #ff7a3a
	FLinearColor Bone(float A = 1.0f);      // #f2e6cc, text
	FLinearColor Sand(float A = 1.0f);      // #a88c6a, quiet text
	FLinearColor Dim(float A = 1.0f);       // #6f5a44
	FLinearColor Ok(float A = 1.0f);        // #7be08a, lives
	FLinearColor Ink(float A = 1.0f);       // #0a0604
	FLinearColor Plate(float A = 0.86f);    // #160c07, panels

	FSlateFontInfo Font(int32 Size, bool bBold = true, int32 LetterSpacing = 0);
	/** 3480 -> "3 480". */
	FString Thousands(int32 Value);

	UTextBlock* Text(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, bool bBold = true, int32 Spacing = 0);
	/** Text with a dark outline round the letters: readable over the bright workshop and the dark one alike. */
	UTextBlock* OutlinedText(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, int32 Spacing, int32 OutlineSize,
		const FLinearColor& OutlineColor);
	/** Sets the text only when it changed (no repaint otherwise). */
	void SetText(UTextBlock* Block, const FString& Value);
	/** A filled box with padding round its content; recolour it with SetBrushColor. */
	UBorder* Box(UWidgetTree* Tree, const FLinearColor& Color, const FMargin& Padding = FMargin(0.0f), UWidget* Content = nullptr);
	/** A box of fixed size (a size of 0 or less is left free). */
	USizeBox* Sized(UWidgetTree* Tree, float Width, float Height, UWidget* Content = nullptr);
	/** A filled box with a thin outline on top of its edges (so a see-through fill is not tinted by the outline). */
	struct FFrame
	{
		UOverlay* Root = nullptr;     // add this to the parent
		UBorder* Fill = nullptr;      // the inside, which holds the content
		UBorder* Edges[4] = {};       // top, bottom, left, right
		void SetOutline(const FLinearColor& Color) const;
	};
	/** TopWidth < 0: the top edge as thick as the others (the briefing card has a thicker accent on top). */
	FFrame Frame(UWidgetTree* Tree, const FLinearColor& Outline, const FLinearColor& Fill, float OutlineWidth, const FMargin& Padding,
		float TopWidth = -1.0f);
	/** A key cap: the key's name in an outlined box. */
	UWidget* KeyCap(UWidgetTree* Tree, const FString& Key, bool bDark = false);
	/** One hint of the key bar: key caps, then what they do. */
	UHorizontalBox* Hint(UWidgetTree* Tree, const TArray<FString>& Keys, const FString& Label);
	/** The STARDUST gem: a small orange diamond (a square turned 45 degrees). */
	UWidget* Gem(UWidgetTree* Tree, float Size, const FLinearColor& Color);
	/** A horizontal fade from LeftAlpha to RightAlpha of a colour, made of strips. */
	UHorizontalBox* Fade(UWidgetTree* Tree, const FLinearColor& Color, float LeftAlpha, float RightAlpha, int32 Strips);

	UHorizontalBoxSlot* AddH(UHorizontalBox* Box, UWidget* Child, const FMargin& Padding = FMargin(0.0f), bool bFill = false,
		EVerticalAlignment VAlign = VAlign_Center);
	UVerticalBoxSlot* AddV(UVerticalBox* Box, UWidget* Child, const FMargin& Padding = FMargin(0.0f), EHorizontalAlignment HAlign = HAlign_Fill);
	UOverlaySlot* AddO(UOverlay* Box, UWidget* Child, EHorizontalAlignment HAlign, EVerticalAlignment VAlign,
		const FMargin& Padding = FMargin(0.0f));
}
