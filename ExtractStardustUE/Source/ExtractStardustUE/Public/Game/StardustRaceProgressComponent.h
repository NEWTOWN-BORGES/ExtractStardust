#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "StardustRaceProgressComponent.generated.h"

class UStardustCourseComponent;
class UStardustCraftMovementComponent;

UENUM(BlueprintType)
enum class EStardustRaceState : uint8
{
	Waiting,
	Racing,
	Extracted,
	Abandoned
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FStardustCheckpointReachedEvent, int32, CheckpointIndex, int32, TotalCheckpoints);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FStardustRaceFinishedEvent, float, FinishTimeSeconds, float, FinishDistanceM);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FStardustRaceRespawnEvent, bool, bPenalty, int32, PathIndex, int32, StationIndex);

UCLASS(ClassGroup = (Stardust), meta = (BlueprintSpawnableComponent))
class EXTRACTSTARDUSTUE_API UStardustRaceProgressComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UStardustRaceProgressComponent();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race")
	TObjectPtr<UStardustCourseComponent> Course;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race", meta = (ClampMin = "0.2", ClampMax = "1.0"))
	float FinishDistanceFraction = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race", meta = (ClampMin = "0", ClampMax = "40"))
	int32 CheckpointCountOverride = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race|Recovery", meta = (ClampMin = "1"))
	float OffTrackToleranceM = 20.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race|Recovery", meta = (ClampMin = "0.1"))
	float OffTrackGraceSeconds = 1.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Race|Recovery", meta = (ClampMin = "1"))
	int32 RespawnRewindStations = 12;

	UPROPERTY(BlueprintReadOnly, Category = "Race")
	EStardustRaceState State = EStardustRaceState::Waiting;

	UPROPERTY(BlueprintReadOnly, Category = "Race")
	float RaceDistanceM = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Race")
	float FinishDistanceM = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Race")
	float ElapsedTimeSeconds = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Race")
	float FinishTimeSeconds = -1.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Race")
	int32 CheckpointCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Race")
	int32 CurrentCheckpoint = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Race")
	int32 CurrentPathIndex = INDEX_NONE;

	UPROPERTY(BlueprintReadOnly, Category = "Race")
	int32 CurrentStationIndex = INDEX_NONE;

	UPROPERTY(BlueprintAssignable, Category = "Race")
	FStardustCheckpointReachedEvent OnCheckpointReached;

	UPROPERTY(BlueprintAssignable, Category = "Race")
	FStardustRaceFinishedEvent OnRaceFinished;

	UPROPERTY(BlueprintAssignable, Category = "Race")
	FStardustRaceRespawnEvent OnRespawned;

	UFUNCTION(BlueprintCallable, Category = "Race")
	bool StartRace();

	UFUNCTION(BlueprintCallable, Category = "Race")
	void ResetRace();

	UFUNCTION(BlueprintCallable, Category = "Race")
	void AbandonRace();

protected:
	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UStardustCraftMovementComponent> CraftMovement;
	float OffTrackSeconds = 0.0f;

	bool RespawnCraft(bool bPenalty);
};
