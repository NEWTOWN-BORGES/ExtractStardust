#include "Game/EXProfile.h"

#include "Kismet/GameplayStatics.h"
#include "Misc/DateTime.h"

namespace
{
	const TCHAR* ProfileSlotName = TEXT("EXProfile");
	constexpr int32 ProfileVersion = 2;

	void SetStarterQuick(UEXProfileSave* Profile, int32 Slot, EEXConsumable Kind, int32 Count)
	{
		Profile->Quick[Slot].Kind = static_cast<uint8>(Kind);
		Profile->Quick[Slot].Count = Count;
	}

	/** Docs/MODULOS.md sec. 8: a STANDARD CACHE to open and the old game's starting consumables, in the quick slots. */
	void GrantStarterKit(UEXProfileSave* Profile)
	{
		Profile->Caches.Add(static_cast<uint8>(EEXCache::Standard));
		Profile->AddStock(EEXConsumable::Foam, 2);
		Profile->AddStock(EEXConsumable::Fuel, 1);
		Profile->AddStock(EEXConsumable::Coolant, 1);
		Profile->Quick.SetNum(EXMeta::QuickSlots);
		SetStarterQuick(Profile, 0, EEXConsumable::Foam, 2);
		SetStarterQuick(Profile, 1, EEXConsumable::Coolant, 1);
		SetStarterQuick(Profile, 2, EEXConsumable::Fuel, 1);
		SetStarterQuick(Profile, 3, EEXConsumable::None, 0);
	}

	void SanitizeProfile(UEXProfileSave* Profile)
	{
		Profile->Stock.SetNumZeroed(EXMeta::ConsumableCount);
		for (int32& Count : Profile->Stock)
		{
			Count = FMath::Max(0, Count);
		}
		// Items of unknown modules (a catalogue change) go; serials stay unique.
		Profile->Items.RemoveAll([](const FEXItem& Item) { return EXMeta::Find(Item) == nullptr; });
		for (FEXItem& Item : Profile->Items)
		{
			Item.Rolls.SetNumZeroed(EXMeta::StatCount);
			Profile->NextSerial = FMath::Max(Profile->NextSerial, Item.Serial + 1);
		}
		for (FEXBuild& Build : Profile->Builds)
		{
			Build.Slots.SetNumZeroed(EXMeta::FamilyCount);
			for (int32 Slot = 0; Slot < EXMeta::FamilyCount; ++Slot)
			{
				const FEXItem* Item = Profile->FindItem(Build.Slots[Slot]);
				const EXMeta::FModuleDef* Def = Item ? EXMeta::Find(*Item) : nullptr;
				if (!Def || !EXMeta::Fits(*Def, Build.Ship, static_cast<EEXFamily>(Slot)))
				{
					Build.Slots[Slot] = 0;
				}
			}
			if (!Build.Slots.Contains(Build.Insured))
			{
				Build.Insured = 0;
			}
		}
		EXEconomy::SanitizeQuick(Profile);
	}
}

FEXBuild& UEXProfileSave::BuildFor(const FString& Ship)
{
	for (FEXBuild& Build : Builds)
	{
		if (Build.Ship.Equals(Ship, ESearchCase::IgnoreCase))
		{
			Build.Slots.SetNumZeroed(EXMeta::FamilyCount);
			return Build;
		}
	}
	FEXBuild& Build = Builds.AddDefaulted_GetRef();
	Build.Ship = Ship;
	Build.Slots.SetNumZeroed(EXMeta::FamilyCount);
	return Build;
}

const FEXBuild* UEXProfileSave::FindBuild(const FString& Ship) const
{
	return Builds.FindByPredicate([&Ship](const FEXBuild& Build) { return Build.Ship.Equals(Ship, ESearchCase::IgnoreCase); });
}

FEXItem* UEXProfileSave::FindItem(int32 Serial)
{
	return Serial == 0 ? nullptr : Items.FindByPredicate([Serial](const FEXItem& Item) { return Item.Serial == Serial; });
}

const FEXItem* UEXProfileSave::FindItem(int32 Serial) const
{
	return Serial == 0 ? nullptr : Items.FindByPredicate([Serial](const FEXItem& Item) { return Item.Serial == Serial; });
}

TArray<const FEXItem*> UEXProfileSave::Equipped(const FString& Ship) const
{
	TArray<const FEXItem*> Out;
	Out.Init(nullptr, EXMeta::FamilyCount);
	if (const FEXBuild* Build = FindBuild(Ship))
	{
		for (int32 Slot = 0; Slot < EXMeta::FamilyCount && Slot < Build->Slots.Num(); ++Slot)
		{
			Out[Slot] = FindItem(Build->Slots[Slot]);
		}
	}
	return Out;
}

int32 UEXProfileSave::StarsOf(const FString& Ship) const
{
	const int32* Stars = ShipStars.Find(Ship.ToUpper());
	return Stars ? FMath::Clamp(*Stars, 0, EXMeta::MaxStars) : 0;
}

bool UEXProfileSave::AddStar(const FString& Ship)
{
	const int32 Stars = StarsOf(Ship);
	if (Stars >= EXMeta::MaxStars)
	{
		return false;
	}
	ShipStars.Add(Ship.ToUpper(), Stars + 1);
	return true;
}

TArray<FEXItem> UEXProfileSave::EquippedCopy(const FString& Ship) const
{
	TArray<FEXItem> Out;
	Out.SetNum(EXMeta::FamilyCount);
	const TArray<const FEXItem*> Fitted = Equipped(Ship);
	for (int32 Slot = 0; Slot < EXMeta::FamilyCount; ++Slot)
	{
		if (Fitted[Slot])
		{
			Out[Slot] = *Fitted[Slot];
		}
	}
	return Out;
}

FString UEXProfileSave::EquippedOn(int32 Serial) const
{
	if (Serial != 0)
	{
		for (const FEXBuild& Build : Builds)
		{
			if (Build.Slots.Contains(Serial))
			{
				return Build.Ship;
			}
		}
	}
	return FString();
}

void UEXProfileSave::Equip(const FString& Ship, EEXFamily Slot, int32 Serial)
{
	if (Serial != 0)
	{
		for (FEXBuild& Other : Builds)
		{
			for (int32& Fitted : Other.Slots)
			{
				Fitted = Fitted == Serial ? 0 : Fitted;
			}
			Other.Insured = Other.Insured == Serial && !Other.Ship.Equals(Ship, ESearchCase::IgnoreCase) ? 0 : Other.Insured;
		}
	}
	FEXBuild& Build = BuildFor(Ship);
	Build.Slots[static_cast<int32>(Slot)] = Serial;
	if (Build.Insured != 0 && !Build.Slots.Contains(Build.Insured))
	{
		Build.Insured = 0;
	}
}

void UEXProfileSave::RemoveItem(int32 Serial)
{
	if (Serial == 0)
	{
		return;
	}
	for (FEXBuild& Build : Builds)
	{
		for (int32& Fitted : Build.Slots)
		{
			Fitted = Fitted == Serial ? 0 : Fitted;
		}
		Build.Insured = Build.Insured == Serial ? 0 : Build.Insured;
	}
	Items.RemoveAll([Serial](const FEXItem& Item) { return Item.Serial == Serial; });
}

int32 UEXProfileSave::StockOf(EEXConsumable Kind) const
{
	const int32 Index = static_cast<int32>(Kind);
	return Kind != EEXConsumable::None && Stock.IsValidIndex(Index) ? Stock[Index] : 0;
}

void UEXProfileSave::AddStock(EEXConsumable Kind, int32 Delta)
{
	if (Kind == EEXConsumable::None)
	{
		return;
	}
	Stock.SetNumZeroed(FMath::Max(Stock.Num(), EXMeta::ConsumableCount));
	Stock[static_cast<int32>(Kind)] = FMath::Max(0, Stock[static_cast<int32>(Kind)] + Delta);
}

FRandomStream UEXProfileSave::NextRandom()
{
	FRandomStream Advance(Seed);
	Seed = static_cast<int32>(Advance.GetUnsignedInt());
	return FRandomStream(static_cast<int32>(Advance.GetUnsignedInt()));
}

namespace EXEconomy
{
	UEXProfileSave* Load()
	{
		UEXProfileSave* Profile = nullptr;
		if (UGameplayStatics::DoesSaveGameExist(ProfileSlotName, 0))
		{
			Profile = Cast<UEXProfileSave>(UGameplayStatics::LoadGameFromSlot(ProfileSlotName, 0));
		}
		if (!Profile)
		{
			Profile = Cast<UEXProfileSave>(UGameplayStatics::CreateSaveGameObject(UEXProfileSave::StaticClass()));
		}
		if (!Profile)
		{
			return nullptr;
		}
		if (Profile->Version < ProfileVersion)
		{
			// A new pilot, or one from the cargo prototype: the wallet stays, the starter kit comes in.
			Profile->Seed = static_cast<int32>(FDateTime::Now().GetTicks() & 0x7fffffff) | 1;
			Profile->Items.Reset();
			Profile->Builds.Reset();
			Profile->Caches.Reset();
			Profile->Stock.Init(0, EXMeta::ConsumableCount);
			GrantStarterKit(Profile);
			RollShop(Profile);
			Profile->Version = ProfileVersion;
		}
		SanitizeProfile(Profile);
		if (Profile->Shop.Num() == 0)
		{
			RollShop(Profile);
		}
		return Profile;
	}

	void Save(UEXProfileSave* Profile)
	{
		if (Profile)
		{
			UGameplayStatics::SaveGameToSlot(Profile, ProfileSlotName, 0);
		}
	}

	int32 QuickValue(const UEXProfileSave* Profile)
	{
		int32 Value = 0;
		for (int32 Slot = 0; Profile && Slot < Profile->Quick.Num(); ++Slot)
		{
			Value += Profile->Quick[Slot].Count * EXMeta::Consumable(static_cast<EEXConsumable>(Profile->Quick[Slot].Kind)).Price;
		}
		return Value;
	}

	int32 RiskValue(const UEXProfileSave* Profile, const FString& Ship)
	{
		if (!Profile)
		{
			return 0;
		}
		const FEXBuild* Build = Profile->FindBuild(Ship);
		TArray<int32> Values;
		for (const FEXItem* Item : Profile->Equipped(Ship))
		{
			if (Item && (!Build || Item->Serial != Build->Insured))
			{
				Values.Add(Item->Value);
			}
		}
		Values.Sort([](int32 A, int32 B) { return A > B; });
		int32 Risk = QuickValue(Profile);
		for (int32 Index = 0; Index < Values.Num() && Index < EXMeta::MaxLost; ++Index)
		{
			Risk += Values[Index];
		}
		return Risk;
	}

	void SanitizeQuick(UEXProfileSave* Profile)
	{
		if (!Profile)
		{
			return;
		}
		Profile->Quick.SetNum(EXMeta::QuickSlots);
		TArray<int32> Left = Profile->Stock;
		Left.SetNumZeroed(EXMeta::ConsumableCount);
		for (FEXQuickSlot& Slot : Profile->Quick)
		{
			if (Slot.Kind >= EXMeta::ConsumableCount)
			{
				Slot.Kind = 0;
			}
			Slot.Count = Slot.Kind == 0 ? 0 : FMath::Clamp(Slot.Count, 0, FMath::Min(EXMeta::PerQuickSlot, Left[Slot.Kind]));
			Left[Slot.Kind] -= Slot.Count;
		}
	}

	void RollShop(UEXProfileSave* Profile)
	{
		if (Profile)
		{
			FRandomStream Random = Profile->NextRandom();
			EXMeta::RollShop(Random, Profile->NextSerial, Profile->Shop);
		}
	}
}
