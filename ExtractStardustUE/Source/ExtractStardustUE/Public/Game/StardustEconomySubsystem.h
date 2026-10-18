#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Game/StardustEconomyTypes.h"
#include "StardustEconomySubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FStardustBalanceChangedEvent, int64, NewBalance, int64, Delta, const FString&, Reason);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FStardustRaceReportProcessedEvent, const FStardustRaceReport&, Report);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FStardustContractCompletedEvent, const FString&, ContractId, const FString&, ContractName, int64, Reward);

/**
 * UStardustEconomySubsystem
 *
 * GameInstance subsystem providing the local economic authority migrated from RedDust.Meta.Economy:
 *  - Stardust currency (✦) management and ledger
 *  - Race rewards (position prize, duration scaling, extraction bonus, first extraction bonus)
 *  - Prowess feats (flawless, survivor, pure energy, contra-relogio, capped at 500)
 *  - Career contracts progression and tracking
 *  - Idempotent race outcome processing
 *  - Profile persistence via USaveGame
 */
UCLASS()
class EXTRACTSTARDUSTUE_API UStardustEconomySubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	// Balance / Wallet
	UFUNCTION(BlueprintPure, Category = "Stardust|Economy")
	int64 GetStardustBalance() const { return CurrentBalance; }

	UFUNCTION(BlueprintCallable, Category = "Stardust|Economy")
	bool AddStardust(int64 Amount, const FString& Reason, const FString& Kind = TEXT("credit"));

	UFUNCTION(BlueprintCallable, Category = "Stardust|Economy")
	bool SpendStardust(int64 Amount, const FString& Reason, const FString& Kind = TEXT("debit"));

	// Race Outcome & Rewards
	UFUNCTION(BlueprintCallable, Category = "Stardust|Economy")
	FStardustRaceReport ProcessRaceOutcome(const FStardustRaceOutcome& Outcome);

	UFUNCTION(BlueprintCallable, Category = "Stardust|Economy")
	FStardustRaceReport ProcessRaceFromProgress(const UStardustRaceProgressComponent* ProgressComponent,
		int32 Position, int32 TotalRacers, float ReferenceMinutes,
		float HullFraction, float FuelFraction, bool bUsedBoost);

	// Prowess and Multiplier Helpers
	UFUNCTION(BlueprintPure, Category = "Stardust|Economy")
	static TArray<FStardustProwessReward> CalculateProwess(const FStardustRaceOutcome& Outcome);

	UFUNCTION(BlueprintPure, Category = "Stardust|Economy")
	static float GetDurationMultiplier(float ReferenceMinutes);

	UFUNCTION(BlueprintPure, Category = "Stardust|Economy")
	static int64 GetPositionReward(int32 Position);

	// Contracts & Stats
	UFUNCTION(BlueprintPure, Category = "Stardust|Economy")
	const TArray<FStardustContractState>& GetContracts() const { return Contracts; }

	UFUNCTION(BlueprintPure, Category = "Stardust|Economy")
	int32 GetRacesCompleted() const { return TotalRaces; }

	UFUNCTION(BlueprintPure, Category = "Stardust|Economy")
	int32 GetExtractionsCompleted() const { return TotalExtractions; }

	UFUNCTION(BlueprintPure, Category = "Stardust|Economy")
	int32 GetCurrentExtractionStreak() const { return ExtractionStreak; }

	UFUNCTION(BlueprintPure, Category = "Stardust|Economy")
	const FStardustRaceReport& GetLastRaceReport() const { return LastReport; }

	UFUNCTION(BlueprintPure, Category = "Stardust|Economy")
	const TArray<FStardustLedgerEntry>& GetLedger() const { return Ledger; }

	UFUNCTION(BlueprintCallable, Category = "Stardust|Economy")
	void ResetProfile(int64 InitialBalance = 1000);

	// Save / Load Profile
	UFUNCTION(BlueprintCallable, Category = "Stardust|Economy")
	bool SaveProfile(const FString& SlotName = TEXT("DefaultProfile"), int32 UserIndex = 0);

	UFUNCTION(BlueprintCallable, Category = "Stardust|Economy")
	bool LoadProfile(const FString& SlotName = TEXT("DefaultProfile"), int32 UserIndex = 0);

	// Self-diagnostics / Automated verification
	UFUNCTION(BlueprintCallable, Category = "Stardust|Economy")
	void RunEconomyDiagnostics();

	// Events
	UPROPERTY(BlueprintAssignable, Category = "Stardust|Economy")
	FStardustBalanceChangedEvent OnBalanceChanged;

	UPROPERTY(BlueprintAssignable, Category = "Stardust|Economy")
	FStardustRaceReportProcessedEvent OnRaceReportProcessed;

	UPROPERTY(BlueprintAssignable, Category = "Stardust|Economy")
	FStardustContractCompletedEvent OnContractCompleted;

private:
	UPROPERTY(SaveGame)
	int64 CurrentBalance = 1000;

	UPROPERTY(SaveGame)
	bool bFirstExtractionPaid = false;

	UPROPERTY(SaveGame)
	int32 TotalRaces = 0;

	UPROPERTY(SaveGame)
	int32 TotalExtractions = 0;

	UPROPERTY(SaveGame)
	int32 ExtractionStreak = 0;

	UPROPERTY(SaveGame)
	int32 NoRepairStreak = 0;

	UPROPERTY(SaveGame)
	TArray<FStardustContractState> Contracts;

	UPROPERTY(Transient)
	TArray<FStardustLedgerEntry> Ledger;

	UPROPERTY(Transient)
	TSet<FString> AppliedTransactions;

	UPROPERTY(Transient)
	FStardustRaceReport LastReport;

	void InitDefaultContracts();
	void RecordLedger(const FString& Kind, int64 Amount, const FString& Note);
	bool AlreadyApplied(const FString& TxId);
	void UpdateContractProgress(const FString& ContractId, int32 Increment, TArray<FStardustReportLine>& OutLines, int64& OutExtraStardust);
};
