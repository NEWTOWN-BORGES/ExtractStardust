#include "StardustProfileSubsystem.h"
#include "Kismet/GameplayStatics.h"

void UStardustProfileSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	if (UStardustProfileSaveGame* Saved = Cast<UStardustProfileSaveGame>(UGameplayStatics::LoadGameFromSlot(SaveSlot, 0)))
	{
		CurrentProfile = Saved->Profile;
	}
	if (CurrentProfile.Loadout.Num() != 4)
	{
		CurrentProfile.Loadout.SetNum(4);
		CurrentProfile.Loadout[0].Id = TEXT("surge"); CurrentProfile.Loadout[0].Count = 2;
		CurrentProfile.Loadout[1].Id = TEXT("repair"); CurrentProfile.Loadout[1].Count = 2;
		CurrentProfile.Loadout[2].Id = TEXT("coolant"); CurrentProfile.Loadout[2].Count = 2;
		CurrentProfile.Loadout[3].Id = TEXT("stabilizer"); CurrentProfile.Loadout[3].Count = 2;
	}
}

void UStardustProfileSubsystem::Deinitialize()
{
	SaveProfile();
	Super::Deinitialize();
}

bool UStardustProfileSubsystem::ConsumeLoadoutSlot(int32 Slot, FName& OutId)
{
	if (!CurrentProfile.Loadout.IsValidIndex(Slot) || CurrentProfile.Loadout[Slot].Count <= 0)
	{
		return false;
	}
	FStardustConsumableStack& Stack = CurrentProfile.Loadout[Slot];
	OutId = Stack.Id;
	--Stack.Count;
	return true;
}

void UStardustProfileSubsystem::SetLoadoutSlot(int32 Slot, FName Id, int32 Count)
{
	if (!CurrentProfile.Loadout.IsValidIndex(Slot))
	{
		CurrentProfile.Loadout.SetNum(4);
	}
	if (CurrentProfile.Loadout.IsValidIndex(Slot))
	{
		CurrentProfile.Loadout[Slot].Id = Id;
		CurrentProfile.Loadout[Slot].Count = FMath::Max(0, Count);
	}
}

void UStardustProfileSubsystem::AddStardust(int64 Amount)
{
	CurrentProfile.Stardust = FMath::Max<int64>(0, CurrentProfile.Stardust + Amount);
}

void UStardustProfileSubsystem::RecordRace(int64 Reward)
{
	++CurrentProfile.Races;
	AddStardust(Reward);
	SaveProfile();
}

bool UStardustProfileSubsystem::IsPartCompatible(const FStardustSocketDefinition& Socket, const FStardustPartDefinition& Part)
{
	const bool bFamilyFits = Socket.AcceptedFamilies.IsEmpty() || Socket.AcceptedFamilies.Contains(Part.Family);
	const bool bSizeFits = Socket.Size.IsNone() || Socket.Size == Part.Size;
	return bFamilyFits && bSizeFits;
}

void UStardustProfileSubsystem::SaveProfile()
{
	UStardustProfileSaveGame* Save = Cast<UStardustProfileSaveGame>(UGameplayStatics::CreateSaveGameObject(UStardustProfileSaveGame::StaticClass()));
	if (Save)
	{
		Save->Profile = CurrentProfile;
		UGameplayStatics::SaveGameToSlot(Save, SaveSlot, 0);
	}
}
