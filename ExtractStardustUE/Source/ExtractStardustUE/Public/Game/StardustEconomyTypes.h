#pragma once

#include "CoreMinimal.h"
#include "Game/StardustRaceProgressComponent.h"
#include "StardustEconomyTypes.generated.h"

UENUM(BlueprintType)
enum class EStardustGameModeType : uint8
{
	Race,
	TimeAttack,
	Exploration
};

USTRUCT(BlueprintType)
struct EXTRACTSTARDUSTUE_API FStardustProwessReward
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	FString Name;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	int64 Value = 0;

	FStardustProwessReward() = default;
	FStardustProwessReward(const FString& InName, int64 InValue) : Name(InName), Value(InValue) {}
};

USTRUCT(BlueprintType)
struct EXTRACTSTARDUSTUE_API FStardustReportLine
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	FString Description;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	int64 Amount = 0;

	FStardustReportLine() = default;
	FStardustReportLine(const FString& InDesc, int64 InAmount = 0) : Description(InDesc), Amount(InAmount) {}
};

USTRUCT(BlueprintType)
struct EXTRACTSTARDUSTUE_API FStardustRaceOutcome
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	FString RaceId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	FString CourseName;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	EStardustGameModeType Mode = EStardustGameModeType::Race;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	EStardustRaceState State = EStardustRaceState::Extracted;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	int32 Position = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	int32 TotalRacers = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	float RaceTimeSeconds = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	float ReferenceTimeSeconds = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	float ReferenceMinutes = 5.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	float HullFraction = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	float FuelFraction = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	bool bTookDamage = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	bool bUsedBoost = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	bool bAllCheckpoints = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	int32 Repairs = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	int32 Penalties = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	int32 SkillRoutes = 0;
};

USTRUCT(BlueprintType)
struct EXTRACTSTARDUSTUE_API FStardustContractState
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	FString Id;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	FString Name;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	FString Description;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	int32 Target = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	int32 Progress = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	int32 CompletedCount = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	int64 Reward = 0;

	FStardustContractState() = default;
	FStardustContractState(const FString& InId, const FString& InName, const FString& InDesc, int32 InTarget, int64 InReward)
		: Id(InId), Name(InName), Description(InDesc), Target(InTarget), Progress(0), CompletedCount(0), Reward(InReward) {}
};

USTRUCT(BlueprintType)
struct EXTRACTSTARDUSTUE_API FStardustLedgerEntry
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	FDateTime Timestamp = FDateTime::UtcNow();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	FString Kind;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	int64 Amount = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	FString Note;
};

USTRUCT(BlueprintType)
struct EXTRACTSTARDUSTUE_API FStardustRaceReport
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	FString RaceId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	FString CourseName;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	EStardustRaceState State = EStardustRaceState::Extracted;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	int32 Position = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	int32 TotalRacers = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	float RaceTimeSeconds = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	float HullFraction = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	float FuelFraction = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	TArray<FStardustReportLine> RewardBreakdown;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Economy")
	int64 TotalStardustEarned = 0;
};
