#pragma once

#include "CoreMinimal.h"
#include "Game/EXMeta.h"
#include "GameFramework/SaveGame.h"
#include "EXProfile.generated.h"

/**
 * The pilot's profile, kept between games (Docs/MODULOS.md): the STARDUST wallet, the modules owned and what each ship
 * carries, the consumables in stock and in the four quick slots, the caches not yet opened and the shop's rotation.
 * Everything is chosen in the hangar (no pickups on the track), lost if the craft is destroyed and kept on extraction.
 */
UCLASS()
class EXTRACTINGSTARDUST_API UEXProfileSave : public USaveGame
{
	GENERATED_BODY()

public:
	/** 2: modules and caches. Older profiles keep their STARDUST and get the starter kit. */
	UPROPERTY() int32 Version = 0;
	UPROPERTY() int32 Stardust = EXMeta::StartingStardust;
	UPROPERTY() int32 ShipIndex = 1;
	UPROPERTY() int32 Expeditions = 0;
	UPROPERTY() int32 Extractions = 0;
	UPROPERTY() int32 BestPlace = 0;
	/** STARDUST won in the last expedition, for the menu. */
	UPROPERTY() int32 LastReward = 0;
	/** What happened to the pilot's things in the last expedition (won, lost), for the menu. */
	UPROPERTY() TArray<FString> LastNews;
	UPROPERTY() TArray<FEXItem> Items;
	UPROPERTY() TArray<FEXBuild> Builds;
	/** Consumables in the hangar, safe (by EEXConsumable). */
	UPROPERTY() TArray<int32> Stock;
	/** The four quick slots for the next expedition, taken out of the stock at the start. */
	UPROPERTY() TArray<FEXQuickSlot> Quick;
	/** Caches bought or won, not yet opened (EEXCache). */
	UPROPERTY() TArray<uint8> Caches;
	/** Components on sale until the next expedition. */
	UPROPERTY() TArray<FEXItem> Shop;
	UPROPERTY() int32 NextSerial = 1;
	UPROPERTY() int32 Seed = 0;
	UPROPERTY() bool bFirstExtractionPaid = false;
	/** Stars of each ship (by upper-case name, 0-7): a copy of a ship from an ELITE CACHE adds one. They raise the ship's
	 *  own stats, before any module (EXMeta::StarBonus). A ship missing here has none. */
	UPROPERTY() TMap<FString, int32> ShipStars;

	int32 StarsOf(const FString& Ship) const;
	/** Adds a star; false (and nothing changes) when the ship already has all seven. */
	bool AddStar(const FString& Ship);

	FEXBuild& BuildFor(const FString& Ship);
	const FEXBuild* FindBuild(const FString& Ship) const;
	FEXItem* FindItem(int32 Serial);
	const FEXItem* FindItem(int32 Serial) const;
	/** The module in each slot of a ship, by EEXFamily (nullptr: the stock part). */
	TArray<const FEXItem*> Equipped(const FString& Ship) const;
	/** The same, copied (an empty FEXItem is the stock part): what a craft flies with. */
	TArray<FEXItem> EquippedCopy(const FString& Ship) const;
	/** The ship an item is fitted to, or an empty string. */
	FString EquippedOn(int32 Serial) const;
	/** Fits an item (0: back to the stock part). A piece is on one ship at a time: it leaves any other. */
	void Equip(const FString& Ship, EEXFamily Slot, int32 Serial);
	void RemoveItem(int32 Serial);
	int32 StockOf(EEXConsumable Kind) const;
	void AddStock(EEXConsumable Kind, int32 Delta);
	/** A fresh random stream for this profile (caches, shop, bots) that never repeats. */
	FRandomStream NextRandom();
};

/** The profile on disk (save slot "EXProfile") and what the hangar and the menu read from it. */
namespace EXEconomy
{
	/** The profile from disk, or a new one: 3000 STARDUST, a STANDARD CACHE and the old game's consumables. */
	UEXProfileSave* Load();
	void Save(UEXProfileSave* Profile);
	/** STARDUST of the consumables in the quick slots. */
	int32 QuickValue(const UEXProfileSave* Profile);
	/** STARDUST at risk with this ship: the three most valuable modules that can be lost, and the consumables carried. */
	int32 RiskValue(const UEXProfileSave* Profile, const FString& Ship);
	/** Puts the quick slots right: four of them, known kinds, 0-2 each and never more than the stock. */
	void SanitizeQuick(UEXProfileSave* Profile);
	/** A new shop rotation (after each expedition). */
	void RollShop(UEXProfileSave* Profile);
}
