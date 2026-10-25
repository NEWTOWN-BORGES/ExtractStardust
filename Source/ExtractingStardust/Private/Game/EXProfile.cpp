#include "Game/EXProfile.h"

#include "Kismet/GameplayStatics.h"

namespace
{
	const TCHAR* ProfileSlot = TEXT("EXProfile");

	// Names and effects in Portuguese (escaped so the compiler reads them the same with any source charset).
	const EXEconomy::FItemDef Items[EXEconomy::ItemCount] = {
		{ TEXT("Kit de repara\u00E7\u00E3o"), TEXT("Devolve 1 vida durante a corrida."), 150, 1, true },
		{ TEXT("Surge"), TEXT("Enche o nitro de uma vez."), 200, 1, true },
		{ TEXT("Escudo"), TEXT("O pr\u00F3ximo embate n\u00E3o tira vida."), 300, 2, true },
		{ TEXT("Combust\u00EDvel extra"), TEXT("Em breve."), 0, 1, false },
	};
}

int32 UEXProfileSave::Count(EEXItem Item) const
{
	const int32 Index = static_cast<int32>(Item);
	return Cargo.IsValidIndex(Index) ? Cargo[Index] : 0;
}

void UEXProfileSave::SetCount(EEXItem Item, int32 Value)
{
	const int32 Index = static_cast<int32>(Item);
	if (Cargo.Num() < EXEconomy::ItemCount)
	{
		Cargo.SetNumZeroed(EXEconomy::ItemCount);
	}
	if (Cargo.IsValidIndex(Index))
	{
		Cargo[Index] = FMath::Max(0, Value);
	}
}

namespace EXEconomy
{
	const FItemDef& Item(EEXItem Which)
	{
		return Items[FMath::Clamp(static_cast<int32>(Which), 0, ItemCount - 1)];
	}

	int32 ShipCapacity(const FString& ShipName)
	{
		if (ShipName.Contains(TEXT("VORTEX")))
		{
			return 3;
		}
		if (ShipName.Contains(TEXT("WRAITH")))
		{
			return 5;
		}
		if (ShipName.Contains(TEXT("NOMAD")))
		{
			return 7;
		}
		if (ShipName.Contains(TEXT("BASTION")))
		{
			return 6;
		}
		return 4;   // STRIX
	}

	int32 CargoWeight(const UEXProfileSave* Profile)
	{
		int32 Weight = 0;
		for (int32 Index = 0; Profile && Index < ItemCount; ++Index)
		{
			Weight += Profile->Count(static_cast<EEXItem>(Index)) * Items[Index].Weight;
		}
		return Weight;
	}

	int32 CargoValue(const UEXProfileSave* Profile)
	{
		int32 Value = 0;
		for (int32 Index = 0; Profile && Index < ItemCount; ++Index)
		{
			Value += Profile->Count(static_cast<EEXItem>(Index)) * Items[Index].Cost;
		}
		return Value;
	}

	UEXProfileSave* Load()
	{
		UEXProfileSave* Profile = nullptr;
		if (UGameplayStatics::DoesSaveGameExist(ProfileSlot, 0))
		{
			Profile = Cast<UEXProfileSave>(UGameplayStatics::LoadGameFromSlot(ProfileSlot, 0));
		}
		if (!Profile)
		{
			Profile = Cast<UEXProfileSave>(UGameplayStatics::CreateSaveGameObject(UEXProfileSave::StaticClass()));
			if (Profile)
			{
				Profile->SetCount(EEXItem::Repair, 2);
				Profile->SetCount(EEXItem::Surge, 1);
			}
		}
		if (Profile && Profile->Cargo.Num() < ItemCount)
		{
			Profile->Cargo.SetNumZeroed(ItemCount);
		}
		return Profile;
	}

	void Save(UEXProfileSave* Profile)
	{
		if (Profile)
		{
			UGameplayStatics::SaveGameToSlot(Profile, ProfileSlot, 0);
		}
	}
}
