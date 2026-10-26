#pragma once

#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"
#include "Layout/Margin.h"
#include "Types/SlateEnums.h"

class UBorder;
class UHorizontalBox;
class UImage;
class UTexture2D;
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

	/** The text font of the mock-ups: Inter, bold or regular (Content/UI/Fonts; the engine's Roboto if it is missing). */
	FSlateFontInfo Font(int32 Size, bool bBold = true, int32 LetterSpacing = 0);
	/** Inter at a weight: 400 regular, 500 medium, 600 semibold, 700 bold, 800 extrabold, 900 black. */
	FSlateFontInfo Inter(int32 Size, int32 Weight, int32 LetterSpacing = 0);
	/** Orbitron Black, the titles of the mock-ups: HANGAR, the ship's name, the cache, the menu's lines, the speed. */
	FSlateFontInfo Orbitron(int32 Size, int32 LetterSpacing = 0);
	/** 3480 -> "3 480". */
	FString Thousands(int32 Value);

	UTextBlock* Text(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, bool bBold = true, int32 Spacing = 0);
	/** Text with a dark outline round the letters: readable over the bright workshop and the dark one alike. */
	UTextBlock* OutlinedText(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, int32 Spacing, int32 OutlineSize,
		const FLinearColor& OutlineColor);
	/** Text in Orbitron (see Orbitron). */
	UTextBlock* TitleText(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, int32 Spacing = 0);
	/** Text in Inter at a weight (see Inter). */
	UTextBlock* WeightText(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, int32 Weight, int32 Spacing = 0);
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

	// ---- Art (Scripts/make_ui_icons.py, the card photos of Scripts/render_modules.py; Scripts/import_ui_icons.py imports them)
	/** An icon or a piece of interface art: /Game/UI/Icons/T_Icon_<Name> (nullptr until it is imported). */
	UTexture2D* Icon(const FString& Name);
	/** The photo of a ship with a module fitted: /Game/UI/Thumbs/T_Thumb_<Key> (nullptr until it is imported). */
	UTexture2D* Thumb(const FString& Key);
	/** An image of a texture at a size (0: the texture's own), tinted. */
	UImage* Image(UWidgetTree* Tree, UTexture2D* Texture, const FLinearColor& Tint = FLinearColor::White, float Width = 0.0f, float Height = 0.0f);
	/** Soft art stretched to any size without blurring its edges (9-sliced): the glows, the vignette. */
	UImage* Sliced(UWidgetTree* Tree, const FString& IconName, const FLinearColor& Tint, float Margin = 0.5f);
	/** Art repeated across the image (the stripes of a card's back). */
	UImage* Tiled(UWidgetTree* Tree, const FString& IconName, const FLinearColor& Tint, float TileSize);
	/** Shows a texture in an image, tinted; collapses the image when the texture is missing. Cheap when nothing changed. */
	void SetImage(UImage* Target, UTexture2D* Texture, const FLinearColor& Tint = FLinearColor::White);
	/** The STARDUST gem (the art), or the drawn diamond while the art is not imported. */
	UWidget* GemImage(UWidgetTree* Tree, float Size);
	/** A soft glow of a colour round a box: put it behind the box, Spread larger on every side. */
	UImage* Glow(UWidgetTree* Tree, const FLinearColor& Color);
	/** The orange gradient of the mock-ups' buttons (#eb571a to #ff7a3a), round some content, with a glow. */
	UWidget* OrangeButton(UWidgetTree* Tree, UWidget* Content, const FMargin& Padding, float Width, float Height);

	// ---- Chips (the "+9 Manobra" boxes of the mock-ups)
	struct FChipView
	{
		UWidget* Root = nullptr;
		UTextBlock* Label = nullptr;
	};
	/** A chip: dark box, faint outline, bold text (green up, red down, bone for a perk). */
	FChipView Chip(UWidgetTree* Tree, int32 Size);
	/** Shows a chip: Sign +1 green, -1 red, 0 bone; an empty text hides it. */
	void SetChip(const FChipView& View, const FString& Text, int32 Sign);

	UHorizontalBoxSlot* AddH(UHorizontalBox* Box, UWidget* Child, const FMargin& Padding = FMargin(0.0f), bool bFill = false,
		EVerticalAlignment VAlign = VAlign_Center);
	UVerticalBoxSlot* AddV(UVerticalBox* Box, UWidget* Child, const FMargin& Padding = FMargin(0.0f), EHorizontalAlignment HAlign = HAlign_Fill);
	UOverlaySlot* AddO(UOverlay* Box, UWidget* Child, EHorizontalAlignment HAlign, EVerticalAlignment VAlign,
		const FMargin& Padding = FMargin(0.0f));
}
