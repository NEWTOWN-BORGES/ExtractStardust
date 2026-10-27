#pragma once

#include "CoreMinimal.h"
#include "Game/EXMeta.h"
#include "UObject/Object.h"
#include "EXHangarModel.generated.h"

class AEXHoverCraft;
class UEXProfileSave;

/** The hangar's tabs (Docs/MODULOS.md sec. 10), in the order Q/E go through them. */
UENUM()
enum class EEXHangarTab : uint8
{
	Ship,
	Equip,
	Quick,
	Shop,
	Vault,
	Count UMETA(Hidden)
};

/** One of the "+9 Manobra" boxes of the mock-ups: Sign +1 green, -1 red, 0 bone (a perk). */
struct FEXHangarChip
{
	FString Text;
	int32 Sign = 0;
};

/** One line of a hangar list or one card of a cache, as the widget shows it (the mock-ups' rows and cards). */
struct FEXHangarRow
{
	/** Small capitals over the title (the family, the quick key, the rarity). */
	FString Label;
	FString Title;
	/** Rolls or effect. */
	FString Sub;
	/** Size class, count or price. */
	FString Right;
	/** "MONTADA", "SEGURO", "NA STRIX"... */
	FString Tag;
	/** The bar on the left: rarity or consumable colour. */
	FLinearColor Colour = FLinearColor::White;
	bool bDim = false;
	/** The icon (EXUi::Icon): fam_<family>, con_<consumable>, cache_<kind>, ship_copy. */
	FString Icon;
	/** The photo of the ship with the module fitted (EXUi::Thumb): <ship>_<piece>, <ship>_engine_<flame>... */
	FString Thumb;
	/** The line under the name: "Vanta Works  ·  classe S  ·  −10 kg" (a row), "Blindagem  ·  M  ·  +90 kg" (a card). */
	FString Maker;
	/** The rarity in small capitals on the right ("ÉPICO"). */
	FString Rarity;
	/** STARDUST shown with the gem (-1: none); bApprox writes "≈" before it. */
	int32 Value = -1;
	bool bApprox = false;
	TArray<FEXHangarChip> Chips;
	/** An engine: the flame bar next to its name (EXMeta::FlameLook). */
	int32 Flame = INDEX_NONE;
	/** The slot's size class badge ("M"), and the insured shield. */
	FString Size;
	bool bInsured = false;
	/** A card worth the "NOVO" ribbon (epic or better, a ship copy). */
	bool bNew = false;
	/** Consumables: how many (the diamonds) of how many at most; the stock line and its buy button. */
	int32 Count = INDEX_NONE;
	int32 MaxCount = 0;
	FString Button;
	/** The roster: the ship's lives and its stars (INDEX_NONE: not a ship). */
	int32 Lives = INDEX_NONE;
	int32 Stars = INDEX_NONE;
};

/** A note pinned next to the ship on the turntable ("ponta dobrada · bordo de ataque luminoso"), at a module. */
struct FEXHangarCallout
{
	FString Text;
	EEXFamily Family = EEXFamily::Wings;
	FLinearColor Colour = FLinearColor::White;
};

/** One hint of the key bar: the keys, then what they do. */
struct FEXHangarHint
{
	TArray<FString> Keys;
	FString Label;
};

/**
 * The hangar's state and rules, between the player's input (AEXHoverCraft forwards it) and the widget (which only
 * shows it): the tab and the row in each, the module looked at in each slot, buying, selling, insuring, the quick slots
 * and the cache being opened. Every change is saved to the profile at once.
 */
UCLASS()
class EXTRACTINGSTARDUST_API UEXHangarModel : public UObject
{
	GENERATED_BODY()

public:
	void Bind(AEXHoverCraft* InCraft);
	/** Entering the hangar: the ship tab, the rows back to the top. */
	void Open();

	// ---- input (W/S Move, A/D Change, Enter Confirm, Backspace Clear, T Insure, Space Alt, Q/E Tab)
	void Tab(int32 Step);
	void Move(int32 Step);
	void Change(int32 Step);
	void Confirm();
	void Clear();
	void Insure();
	void Alt();
	void CloseCache();
	void Tick(float Dt);

	// ---- what the widget and the craft read
	EEXHangarTab GetTab() const { return CurrentTab; }
	/** Changes whenever the ship on the turntable has to change. */
	int32 GetVersion() const { return Version; }
	/** The build the ship wears now: what it flies with, with the piece the pilot is looking at in its slot. */
	TArray<FEXItem> GetPreviewBuild() const;
	/** The slot looked at (engine, propulsion, reactor and utility show the skeleton with the engine running). */
	EEXFamily GetFocus() const;
	void BuildLeft(FString& Title, TArray<FEXHangarRow>& Out, int32& Selected) const;
	void BuildRight(FString& Title, TArray<FEXHangarRow>& Out, int32& Selected, FString& Detail) const;
	/** Stats with what the ship flies now and with the preview (EEXStat order), and the lives of each. */
	void GetStats(int32 (&Now)[EXMeta::StatCount], int32 (&Next)[EXMeta::StatCount], int32& LivesNow, int32& LivesNext) const;
	bool IsOpening() const { return bOpening; }
	int32 GetRevealed() const { return Revealed; }
	const TArray<FEXHangarRow>& GetCards() const { return Cards; }
	FString GetCacheTitle() const;
	int32 GetCacheValue() const { return CacheValue; }
	int32 GetCachePrice() const;
	const FString& GetNotice() const { return Notice; }
	float GetNoticeTime() const { return NoticeTime; }
	TArray<FEXHangarHint> GetHints() const;
	/** The label under the ship ("PRÉ-VISUALIZAÇÃO · WRAITH GLIDE", "VISTA EM ESQUELETO · MOTOR LIGADO"); empty for none. */
	FString GetPreviewLabel(FLinearColor& OutColour) const;
	/** The notes pinned to the modules on the ship (the equip tab). */
	TArray<FEXHangarCallout> GetCallouts() const;
	/** The card shown in the right panel of the shop and the vault for the module looked at (false: none). */
	bool GetLookedCard(FEXHangarRow& OutCard) const;
	/** The two lines of the summary under the quick slots (CONSUMÍVEIS). */
	FString GetQuickSummary() const;
	FString GetShipName() const;
	UEXProfileSave* GetProfile() const;
	static FString TabName(EEXHangarTab Tab);
	static FString ShipRole(const FString& Ship);
	static FString ShipSubtitle(const FString& Ship);
	/** Seven pips, one filled per star (the empty ones show too), then "3/7 ESTRELAS". */
	static FString StarText(int32 Stars);

private:
	int32& Row() { return Rows[static_cast<int32>(CurrentTab)]; }
	int32 RowOf(EEXHangarTab InTab) const { return Rows[static_cast<int32>(InTab)]; }
	int32 RowCount() const;
	EEXFamily CurrentSlot() const { return static_cast<EEXFamily>(FMath::Clamp(RowOf(EEXHangarTab::Equip), 0, EXMeta::FamilyCount - 1)); }
	/** Serials that fit the current slot of the current ship, the stock part (0) first, best first after it. */
	TArray<int32> Candidates() const;
	int32 CandidateSerial() const;
	void SyncCandidate();
	/** The vault's list: caches first, then the modules, best first. */
	TArray<int32> VaultItems() const;
	/** The shop or vault item under the cursor, if it is a module. */
	const FEXItem* LookedItem() const;
	void Note(const FString& Text);
	void Touch() { ++Version; }
	void SaveProfile();
	void OpenCache(int32 Index);
	void BuyShop(int32 Index);
	void SellItem(int32 Serial);
	FEXHangarRow ItemRow(const FEXItem& Item, bool bWithPlace) const;
	/** The same module as a card of a cache: the photo, short chip names, family and class under the name. */
	FEXHangarRow ItemCard(const FEXItem& Item) const;
	/** Sells the commons of the cache just opened at a quarter of their value (the "VENDER COMUNS" button). */
	void SellCommons();
	int32 QuickAvailable(int32 Slot, EEXConsumable Kind) const;

	UPROPERTY(Transient) TObjectPtr<AEXHoverCraft> Craft;
	EEXHangarTab CurrentTab = EEXHangarTab::Ship;
	int32 Rows[static_cast<int32>(EEXHangarTab::Count)] = {};
	int32 Candidate = 0;
	int32 Version = 0;
	FString ShownShip;
	FString Notice;
	float NoticeTime = -100.0f;
	int32 SellArmed = 0;
	float SellArmedTime = -100.0f;
	// The cache being opened: the cards turn over one after another.
	bool bOpening = false;
	int32 Revealed = 0;
	float RevealTimer = 0.0f;
	int32 CacheValue = 0;
	EEXCache OpenedKind = EEXCache::Standard;
	TArray<FEXHangarRow> Cards;
	/** The serial behind each card (0: a consumable or a ship copy), for selling the commons. */
	TArray<int32> CardSerials;
};
