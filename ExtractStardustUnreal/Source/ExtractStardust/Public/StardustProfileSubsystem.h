#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "StardustTypes.h"
#include "StardustProfileSubsystem.generated.h"

UCLASS()
class EXTRACTSTARDUST_API UStardustProfileSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	UPROPERTY(SaveGame)
	FStardustProfile Profile;
};

UCLASS()
class EXTRACTSTARDUST_API UStardustProfileSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Profile")
	const FStardustProfile& GetProfile() const { return CurrentProfile; }

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Profile")
	bool ConsumeLoadoutSlot(int32 Slot, FName& OutId);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Profile")
	void SetLoadoutSlot(int32 Slot, FName Id, int32 Count);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Profile")
	void AddStardust(int64 Amount);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Profile")
	void RecordRace(int64 Reward);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Hangar")
	static bool IsPartCompatible(const FStardustSocketDefinition& Socket, const FStardustPartDefinition& Part);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Profile")
	void SaveProfile();

private:
	UPROPERTY()
	FStardustProfile CurrentProfile;
	FString SaveSlot = TEXT("ExtractStardust_Profile");
};
