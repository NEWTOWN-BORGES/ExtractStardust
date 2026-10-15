#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "StardustCourseGraph.h"
#include "StardustRaceDirector.generated.h"

class APawn;

UCLASS(Blueprintable)
class EXTRACTSTARDUST_API AStardustRaceDirector : public AActor
{
	GENERATED_BODY()
public:
	AStardustRaceDirector();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Race")
	void StartRace(int32 CheckpointsPerLap, int32 Laps);
	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Race")
	void PassCheckpoint(APawn* Racer, int32 CheckpointIndex);
	UFUNCTION(BlueprintPure, Category="Extract Stardust|Race")
	float GetElapsedSeconds() const;
	UFUNCTION(BlueprintPure, Category="Extract Stardust|Race")
	int32 GetCurrentLap() const { return CurrentLap; }
	UFUNCTION(BlueprintPure, Category="Extract Stardust|Race")
	int32 GetNextCheckpoint() const { return NextCheckpoint; }
	UFUNCTION(BlueprintPure, Category="Extract Stardust|Race")
	bool IsRaceActive() const { return bRaceActive; }

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Course")
	void SetCourseGraph(UStardustCourseGraph* InCourseGraph);
	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Course")
	bool StartCourseRun(APawn* Racer, float LengthFraction = 1.0f);
	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Course")
	bool UpdateCourseProgress(APawn* Racer);
	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	float GetCourseProgress() const;

	UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Extract Stardust|Course")
	TObjectPtr<UStardustCourseGraph> CourseGraph = nullptr;

private:
	UPROPERTY(EditAnywhere, Category="Race", meta=(ClampMin="1"))
	int32 TargetLaps = 3;
	int32 CheckpointCount = 1;
	int32 CurrentLap = 1;
	int32 NextCheckpoint = 0;
	float StartTime = 0.0f;
	bool bRaceActive = false;
	bool bCourseRun = false;
	bool bCourseExtracted = false;
	TWeakObjectPtr<APawn> CourseRacer;
	int32 CoursePathIndex = INDEX_NONE;
	int32 CourseStationIndex = INDEX_NONE;
	int32 CourseCheckpointProgress = 0;
	int32 CourseCheckpointCount = 0;
	float CourseRaceDistance = 0.0f;
	float CourseFinishDistance = 0.0f;
};