#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "Game/StardustEconomyTypes.h"
#include "StardustSaveGame.generated.h"

/**
 * UStardustSaveGame
 *
 * Persists the player's profile data, wallet balance, career contracts,
 * race statistics, and ledger to disk using Unreal Engine's SaveGame architecture.
 */
UCLASS()
class EXTRACTSTARDUSTUE_API UStardustSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	FString SaveSlotName = TEXT("DefaultProfile");

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	int32 UserIndex = 0;

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	FString PlayerName = TEXT("Piloto");

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	int64 StardustBalance = 1000;

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	bool bFirstExtractionPaid = false;

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	int32 TotalRaces = 0;

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	int32 TotalExtractions = 0;

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	int32 ExtractionStreak = 0;

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	int32 NoRepairStreak = 0;

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	TArray<FStardustContractState> Contracts;

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	TArray<FStardustLedgerEntry> Ledger;

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	FStardustRaceReport LastRaceReport;

	UPROPERTY(VisibleAnywhere, Category = "SaveGame")
	TArray<FString> AppliedTransactions;
};
