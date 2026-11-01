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
 * The look shared by every screen: the race HUD's (the player's concept, 2026-11-01), carried to the menu, the hangar,
 * the vault and the results ("a mesma direção de arte"): navy plates with their top-left and bottom-right corners cut,
 * glowing cyan edges, gold for STARDUST and prizes, Orbitron figures leaning forward, Inter labels in spaced capitals
 * (Docs/MENU_HANGAR.md). Sizes are Slate units at 1920 x 1080; UMG scales them with the screen.
 */
namespace EXUi
{
	/** An sRGB colour as the mock-ups give it. */
	FLinearColor Hex(uint8 R, uint8 G, uint8 B, float A = 1.0f);
	FLinearColor Accent(float A = 1.0f);    // #46dcff, cyan: edges, highlights, the selection, the primary button
	FLinearColor AccentHot(float A = 1.0f); // #96e1ff, light cyan: titles of panels, secondary highlights
	FLinearColor Fore(float A = 1.0f);      // #eef5ff, text
	FLinearColor Quiet(float A = 1.0f);     // #8ca5c4, quiet text
	FLinearColor Dim(float A = 1.0f);       // #4a5c78
	FLinearColor Ok(float A = 1.0f);        // #6ee68c, lives, gains
	FLinearColor Gold(float A = 1.0f);      // #ffc83c, STARDUST, prizes, stars
	FLinearColor Danger(float A = 1.0f);    // #ff5a28, danger, losses
	FLinearColor Blue(float A = 1.0f);      // #2878ff, the far end of the cyan gradient
	FLinearColor Ink(float A = 1.0f);       // #030814, outlines, dark text on the bright buttons
	FLinearColor Plate(float A = 0.86f);    // #081226, the navy plates

	/** The text font of the mock-ups: Inter, bold or regular (Content/UI/Fonts; the engine's Roboto if it is missing). */
	FSlateFontInfo Font(int32 Size, bool bBold = true, int32 LetterSpacing = 0);
	/** Inter at a weight: 400 regular, 500 medium, 600 semibold, 700 bold, 800 extrabold, 900 black. */
	FSlateFontInfo Inter(int32 Size, int32 Weight, int32 LetterSpacing = 0);
	/** Orbitron Black, the titles of the mock-ups: HANGAR, the ship's name, the cache, the menu's lines, the speed. */
	FSlateFontInfo Orbitron(int32 Size, int32 LetterSpacing = 0);
	/** 3480 -> "3 480". */
	FString Thousands(int32 Value);

	UTextBlock* Text(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, bool bBold = true, int32 Spacing = 0);
	/** Leans a widget forward, as the HUD's figures. */
	void Lean(UWidget* Widget, float Degrees = -11.0f);
	/** Text with a dark outline round the letters: readable over the bright workshop and the dark one alike. */
	UTextBlock* OutlinedText(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, int32 Spacing, int32 OutlineSize,
		const FLinearColor& OutlineColor);
	/** Text in Orbitron (see Orbitron), leaning forward with a dark outline round the letters: the titles and figures of
	 *  every screen, as the HUD's. */
	UTextBlock* TitleText(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, int32 Spacing = 0);
	/** A label as the HUD's: Inter extra bold in spaced capitals, a thin dark outline, leaning a little. */
	UTextBlock* LabelText(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, int32 Spacing = 160);
	/** Text in Inter at a weight (see Inter). */
	UTextBlock* WeightText(UWidgetTree* Tree, const FString& Value, int32 Size, const FLinearColor& Color, int32 Weight, int32 Spacing = 0);
	/** Sets the text only when it changed (no repaint otherwise). */
	void SetText(UTextBlock* Block, const FString& Value);
	/** A filled box with padding round its content; recolour it with SetBrushColor. */
	UBorder* Box(UWidgetTree* Tree, const FLinearColor& Color, const FMargin& Padding = FMargin(0.0f), UWidget* Content = nullptr);
	/** A box of fixed size (a size of 0 or less is left free). */
	USizeBox* Sized(UWidgetTree* Tree, float Width, float Height, UWidget* Content = nullptr);
	/** The shapes of the plates (Scripts/make_hud_art.py, ui_*): white art, 9-sliced and tinted.
	 *  Plate: the top-left and bottom-right corners cut (panels, lines, chips, keys); Card: only the bottom-right corner
	 *  (the photo fills the top); Tab: leaning forward like the figures (drawn at its own height). */
	enum class EShape : uint8
	{
		Plate,
		Card,
		Tab,
	};
	/** Gives a border the shape's art (9-sliced; Corner: the cut corner in Slate units, for a Tab its height; Part as in
	 *  ShapeImage, "_edge" for a glowing outline round its content). The border's brush colour tints it. A flat box while
	 *  the art is not imported. */
	void SetShapeBrush(UBorder* Border, EShape Shape, float Corner, const TCHAR* Part = TEXT(""));
	/** A part of the shape's art as an image ("" the fill, "_edge" the glowing edge, "_wash" the selection's wash fading
	 *  to the right, "_inset" a glow inside the edges), 9-sliced at a corner, tinted. Collapsed while it is missing. */
	UImage* ShapeImage(UWidgetTree* Tree, EShape Shape, const TCHAR* Part, float Corner, const FLinearColor& Tint);
	/** A plate: the fill tinted with the fill colour, its glowing edge tinted with the outline colour on top. */
	struct FFrame
	{
		UOverlay* Root = nullptr;     // add this to the parent
		UBorder* Fill = nullptr;      // the plate, which holds the content
		UImage* Edge = nullptr;       // the edge (none when OutlineWidth <= 0)
		UBorder* Accent = nullptr;    // the bar along the top, past the cut corner (TopWidth > 0)
		void SetOutline(const FLinearColor& Color) const;
	};
	/** TopWidth > 0: a bar of that height along the top, in the outline colour (the briefing card, the info panel). */
	FFrame Frame(UWidgetTree* Tree, const FLinearColor& Outline, const FLinearColor& Fill, float OutlineWidth, const FMargin& Padding,
		float TopWidth = -1.0f, float Corner = 10.0f, EShape Shape = EShape::Plate);
	/** A key cap: the key's name in an outlined box. */
	UWidget* KeyCap(UWidgetTree* Tree, const FString& Key, bool bDark = false);
	/** One hint of the key bar: key caps, then what they do. */
	UHorizontalBox* Hint(UWidgetTree* Tree, const TArray<FString>& Keys, const FString& Label);
	/** The drawn STARDUST mark while the art is not imported: a small gold diamond (a square turned 45 degrees). */
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
	/** STARDUST: the gold coin of the HUD's piggy bank (hud_coin), the same on every screen; the drawn diamond while the
	 *  art is not imported. */
	UWidget* GemImage(UWidgetTree* Tree, float Size);
	/** A soft glow of a colour round a box: put it behind the box, Spread larger on every side. */
	UImage* Glow(UWidgetTree* Tree, const FLinearColor& Color);
	/** The primary button: cyan to blue with a sheen and a light edge, its corners cut (ui_btn), a cyan glow round it, the
	 *  content on top (dark text reads on it). Width and Height are the button's; the glow spreads 22 more on every side. */
	UWidget* PrimaryButton(UWidgetTree* Tree, UWidget* Content, const FMargin& Padding, float Width, float Height);
	/** Just the primary button's face (ui_btn, 9-sliced for a button Height tall), for the small buy buttons. */
	UWidget* ButtonFace(UWidgetTree* Tree, float Height);

	// ---- Chips (the "+9 Manobra" boxes of the mock-ups)
	struct FChipView
	{
		UWidget* Root = nullptr;
		UTextBlock* Label = nullptr;
	};
	/** A chip: a small navy plate, a faint edge, bold text (green up, red down, white for a perk). */
	FChipView Chip(UWidgetTree* Tree, int32 Size);
	/** Shows a chip: Sign +1 green, -1 red, 0 bone; an empty text hides it. */
	void SetChip(const FChipView& View, const FString& Text, int32 Sign);

	UHorizontalBoxSlot* AddH(UHorizontalBox* Box, UWidget* Child, const FMargin& Padding = FMargin(0.0f), bool bFill = false,
		EVerticalAlignment VAlign = VAlign_Center);
	UVerticalBoxSlot* AddV(UVerticalBox* Box, UWidget* Child, const FMargin& Padding = FMargin(0.0f), EHorizontalAlignment HAlign = HAlign_Fill);
	UOverlaySlot* AddO(UOverlay* Box, UWidget* Child, EHorizontalAlignment HAlign, EVerticalAlignment VAlign,
		const FMargin& Padding = FMargin(0.0f));
}
