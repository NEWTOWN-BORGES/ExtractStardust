#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "EXProfile.generated.h"

/**
 * What a pilot brings to an expedition. Docs/VISAO_JOGO.md: there are no pickups on the track; everything is chosen in
 * the hangar, used on the way, lost if the craft is destroyed (it feeds the pool the extractors share at B) and kept if
 * the pilot extracts.
 */
UENUM()
enum class EEXItem : uint8
{
	Repair,  // one life back (H / Square)
	Surge,   // the nitro filled at once (F / D-pad up)
	Shield,  // the next hit costs no life
	Fuel,    // later
	Count UMETA(Hidden)
};

/** The pilot's profile, kept between games: the STARDUST wallet, the chosen ship, the cargo for the next expedition. */
UCLASS()
class EXTRACTINGSTARDUST_API UEXProfileSave : public USaveGame
{
	GENERATED_BODY()

public:
	UPROPERTY() int32 Stardust = 3000;
	UPROPERTY() int32 ShipIndex = 1;
	/** Items in the cargo, indexed by EEXItem. */
	UPROPERTY() TArray<int32> Cargo;
	UPROPERTY() int32 Expeditions = 0;
	UPROPERTY() int32 Extractions = 0;
	UPROPERTY() int32 BestPlace = 0;
	/** STARDUST won (or lost) in the last expedition, for the menu. */
	UPROPERTY() int32 LastReward = 0;

	int32 Count(EEXItem Item) const;
	void SetCount(EEXItem Item, int32 Value);
};

/** The item and ship tables, and the profile on disk (save slot "EXProfile"). */
namespace EXEconomy
{
	constexpr int32 ItemCount = static_cast<int32>(EEXItem::Count);

	struct FItemDef
	{
		const TCHAR* Name;
		const TCHAR* Effect;
		int32 Cost;      // STARDUST per unit
		int32 Weight;    // cargo units per item
		bool bAvailable;
	};

	const FItemDef& Item(EEXItem Which);
	/** Cargo units a ship carries (VORTEX 3 ... NOMAD 7). */
	int32 ShipCapacity(const FString& ShipName);
	int32 CargoWeight(const UEXProfileSave* Profile);
	/** STARDUST value of the cargo: what is at risk on the track. */
	int32 CargoValue(const UEXProfileSave* Profile);
	/** The profile from disk, or a new one (3000 STARDUST, two repair kits and one surge). */
	UEXProfileSave* Load();
	void Save(UEXProfileSave* Profile);
}
