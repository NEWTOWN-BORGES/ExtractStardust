#pragma once

#include "CoreMinimal.h"
#include "EXMeta.generated.h"

/**
 * The modules, rarities, caches and consumables of the old game (the Unity demo with the five old ships: Catalog.cs,
 * Items.cs and Economy.cs on main), brought to the new ships. Docs/MODULOS.md has the tables; the numbers are tuning
 * targets, as in the design documents 02 and 03.
 */

/** The slots of a ship, in the hangar's order. Engine, propulsion and reactor sit inside the hull. */
UENUM()
enum class EEXFamily : uint8
{
	Engine,
	Propulsion,
	Wings,
	Tail,
	Armor,
	Reactor,
	Cooling,
	Utility,
	Count UMETA(Hidden)
};

UENUM()
enum class EEXRarity : uint8
{
	Common,
	Uncommon,
	Rare,
	Epic,
	Legendary,
	Count UMETA(Hidden)
};

/** The eight stats of doc 02 (0-100), then three module attributes: mass (kg), repair support and sensors. */
enum class EEXStat : uint8
{
	Speed,
	Accel,
	Handling,
	Stability,
	Hull,
	Efficiency,
	Cooling,
	Boost,
	Mass,
	Repair,
	Intel,
	Count
};

UENUM()
enum class EEXConsumable : uint8
{
	None,
	Coolant,
	Foam,
	Fuel,
	Stabilizer,
	Surge,
	Nanogel,
	Count UMETA(Hidden)
};

UENUM()
enum class EEXCache : uint8
{
	Standard,
	Advanced,
	Elite,
	Count UMETA(Hidden)
};

/** One module a pilot owns: a catalogue entry with its own rolls (two pieces of the same name can differ). When it
 *  changes hands through the pool it is the same instance: same serial, rolls and value. */
USTRUCT()
struct FEXItem
{
	GENERATED_BODY()

	/** Catalogue id (EXMeta::Find); None means the ship's stock part. */
	UPROPERTY() FName Def;
	UPROPERTY() uint8 Rarity = 0;
	/** Unique in the profile. Legendaries print it as their serial number (RLX-0042). */
	UPROPERTY() int32 Serial = 0;
	/** Rolled values by EEXStat (negative: the drawback that paid for an extreme gain). */
	UPROPERTY() TArray<int32> Rolls;
	/** Valuation in STARDUST, separate from power. */
	UPROPERTY() int32 Value = 0;

	bool IsValid() const { return !Def.IsNone(); }
	int32 Roll(EEXStat Stat) const { return Rolls.IsValidIndex(static_cast<int32>(Stat)) ? Rolls[static_cast<int32>(Stat)] : 0; }
};

/** What a ship carries: the serial of the module in each slot (by EEXFamily, 0 = the stock part) and the insured one. */
USTRUCT()
struct FEXBuild
{
	GENERATED_BODY()

	UPROPERTY() FString Ship;
	UPROPERTY() TArray<int32> Slots;
	/** One module per expedition is insured: it is never lost. */
	UPROPERTY() int32 Insured = 0;
};

/** One of the four quick slots: keys 1-4, d-pad up, down, left and right. */
USTRUCT()
struct FEXQuickSlot
{
	GENERATED_BODY()

	UPROPERTY() uint8 Kind = 0;   // EEXConsumable
	UPROPERTY() int32 Count = 0;  // 0-2
};

namespace EXMeta
{
	constexpr int32 FamilyCount = static_cast<int32>(EEXFamily::Count);
	constexpr int32 RarityCount = static_cast<int32>(EEXRarity::Count);
	constexpr int32 StatCount = static_cast<int32>(EEXStat::Count);
	constexpr int32 CoreStats = 8;
	constexpr int32 ConsumableCount = static_cast<int32>(EEXConsumable::Count);
	constexpr int32 CacheCount = static_cast<int32>(EEXCache::Count);
	constexpr int32 QuickSlots = 4;
	constexpr int32 PerQuickSlot = 2;
	/** A destroyed craft loses everything but its insured module (player, 2026-10-27; Docs/VISAO_JOGO.md). */
	constexpr int32 MaxLost = 1000;
	constexpr int32 FirstExtractionBonus = 500;
	constexpr int32 ExtractedBonus = 250;
	constexpr int32 StartingStardust = 3000;
	/** Ship stars (like the duplicates of Dragon Ball Legends): each copy of a ship adds one, up to seven. */
	constexpr int32 MaxStars = 7;
	/** Chance that an ELITE CACHE holds one copy of a ship. */
	constexpr float ShipCopyChance = 0.06f;
	/** STARDUST a copy is worth when its ship already has all seven stars. */
	constexpr int32 ShipCopyRefund = 8000;

	/** Size classes, as a mask: a slot takes the classes it lists. */
	enum : uint8 { SizeS = 1, SizeM = 2, SizeL = 4, SizeAny = 7 };

	/** A stat a module may give, with the family's ceiling per item and the model's preference. */
	struct FStatRule
	{
		EEXStat Stat;
		int32 Cap;
		float Weight;
	};

	/** A fixed roll of a legendary. */
	struct FStatRoll
	{
		EEXStat Stat;
		int32 Value;
	};

	struct FModuleDef
	{
		FName Id;
		FString Name;
		FString Maker;
		FString Description;
		EEXFamily Family = EEXFamily::Engine;
		uint8 Size = SizeM;
		int32 MassKg = 0;
		/** The mesh piece on the ship (wing_blade, armor_guard...): /Game/Ships/<SHIP>/SM_<SHIP>_<piece>. Empty for
		 *  the modules inside the hull. */
		FString Piece;
		/** Wings belong to one ship; everything else fits any ship whose slot takes its size. */
		FString Ship;
		/** Engines: flame style (FFlameStyle index); reactors: glow colour; propulsion: nitro colour. */
		int32 Look = 0;
		TArray<FStatRule> Stats;
		TArray<FStatRule> Drawbacks;
		/** Legendaries: controlled rolls, a perk and a serial prefix; never sold in the shop. */
		bool bLegendary = false;
		FString Perk;
		FString PerkText;
		FString SerialPrefix;
		TArray<FStatRoll> FixedRolls;
	};

	struct FShipDef
	{
		const TCHAR* Name;
		int32 Stats[CoreStats];
		int32 MassKg;
		int32 Lives;
		/** Size classes each slot takes, by EEXFamily (0: the ship has no such slot). */
		uint8 Sizes[FamilyCount];
		const TCHAR* Passive;
		const TCHAR* PassiveText;
	};

	struct FConsumableDef
	{
		const TCHAR* Id;
		const TCHAR* Name;
		const TCHAR* Effect;
		int32 Price;
		FLinearColor Colour;
	};

	struct FCacheDef
	{
		const TCHAR* Name;
		int32 Price;
		/** Common, uncommon, rare, epic. */
		float Odds[4];
		const TCHAR* Promise;
	};

	/** The flame of an engine module (Scripts/render_modules.py draws the same table). */
	struct FFlameStyle
	{
		FLinearColor Outer;
		FLinearColor Core;
		float Length = 1.0f;
		float Radius = 1.0f;
		int32 Diamonds = 0;
		bool bSparks = false;
	};

	// ---- catalogue
	int32 ModuleCount();
	const FModuleDef& ModuleAt(int32 Index);
	const FModuleDef* Find(FName Id);
	const FModuleDef* Find(const FEXItem& Item);
	const FShipDef& Ship(const FString& Name);
	int32 ShipCount();
	const FShipDef& ShipAt(int32 Index);
	/** Points a ship's stars add to each of its eight core stats (the ship alone, before any module): 2 a star, 15 at seven. */
	int32 StarBonus(int32 Stars);
	const FConsumableDef& Consumable(EEXConsumable Kind);
	const FCacheDef& Cache(EEXCache Kind);

	// ---- names and colours for the interface
	FString FamilyName(EEXFamily Family);
	FString StatName(EEXStat Stat);
	FString StatShort(EEXStat Stat);
	/** The stat's name on a card's chip: "Manobra", "Estab.", "Refrig." (mock-up cofre.png). */
	FString StatCard(EEXStat Stat);
	FString RarityName(EEXRarity Rarity);
	FLinearColor RarityColour(EEXRarity Rarity);
	FString SizeText(uint8 Sizes);
	/** "APEX VK-4 Sprint", or "REDLINE-X RLX-0042" for a legendary. */
	FString ItemLabel(const FEXItem& Item);
	/** "+9 VEL  +7 ACE  -3 EFI" (mass and zero rolls left out). */
	FString RollText(const FEXItem& Item);
	/** STARDUST the store pays: a quarter of the value. */
	int32 SellValue(const FEXItem& Item);
	/** Shop price by rarity band (epics and legendaries are never sold). */
	int32 ShopPrice(const FEXItem& Item);

	// ---- rules
	/** Whether a module goes in that slot of that ship: family, size class, and the ship for wings. */
	bool Fits(const FModuleDef& Def, const FString& ShipName, EEXFamily Slot);
	/** A new instance: the rarity's budget spread over the family's stats under their ceilings, sometimes with a
	 *  drawback that returns budget; legendaries get their controlled rolls. */
	FEXItem Roll(const FModuleDef& Def, EEXRarity Rarity, FRandomStream& Random, int32 Serial);
	/** Final stats (EEXStat order): the ship's (plus its stars' bonus) and every module's rolls, core stats held to 0-100. */
	void Resolve(const FString& ShipName, const TArray<const FEXItem*>& Modules, int32 (&Out)[StatCount], int32 Stars = 0);
	/** The ship's lives, plus one per 10 hull above its own (6 at most). */
	int32 Lives(const FString& ShipName, int32 HullStat);
	bool HasPerk(const TArray<const FEXItem*>& Modules, const TCHAR* Perk);
	FFlameStyle Flame(const FEXItem* Engine);
	/** The engine's flame style (0 stock, 1 sprint, 2 endurance, 3 burner, 4 razor, 5 heavy, 6 relic, 7 redline): the flame
	 *  bar of the hangar and the engine photo. */
	int32 FlameLook(const FEXItem* Engine);
	FLinearColor NitroColour(const FEXItem* Propulsion);
	FLinearColor ReactorGlow(const FEXItem* Reactor);

	// ---- caches, shop, bots, rewards
	/** Ten things: 4-6 components (5-6 in an ELITE) under the cache's odds and promises, the rest consumables. Only an
	 *  ELITE can also hold a copy of a ship (rarely): its index in the ship table goes to OutShipCopy, else INDEX_NONE. */
	void OpenCache(EEXCache Kind, FRandomStream& Random, int32& NextSerial, TArray<FEXItem>& OutItems, TArray<EEXConsumable>& OutConsumables,
		int32* OutShipCopy = nullptr);
	/** The shop's rotation after each expedition: three commons, two uncommons, one rare. */
	void RollShop(FRandomStream& Random, int32& NextSerial, TArray<FEXItem>& Out);
	/** A bot's garage: real pieces (skill 0-2), so what a destroyed bot loses is real loot. Out is by EEXFamily. */
	void RollBotBuild(const FString& ShipName, int32 Skill, FRandomStream& Random, int32& NextSerial, TArray<FEXItem>& Out);
	/** A bot's cargo (player, 2026-10-26: "os bots têm de estar cheios de espólio"): Count loose modules of any family,
	 *  a little richer than what the bots fit (skill 0-2). It goes to the piggy bank if the bot is destroyed, and the top
	 *  three extractors take the best of it from the racers they beat. */
	void RollBotCargo(int32 Skill, FRandomStream& Random, int32& NextSerial, int32 Count, TArray<FEXItem>& Out);
	/** STARDUST for a finishing place (1-based), already scaled for a 10-15 minute expedition. */
	int32 PlaceReward(int32 Place);
	/** Losses of a destroyed craft: every module but the insured one. */
	TArray<int32> SelectLosses(const TArray<FEXItem>& Carried, int32 InsuredSerial, FRandomStream& Random);
}
