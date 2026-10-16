#include "Game/StardustRaceProgressComponent.h"

#include "Course/StardustCourseComponent.h"
#include "GameFramework/Actor.h"

UStardustRaceProgressComponent::UStardustRaceProgressComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UStardustRaceProgressComponent::BeginPlay()
{
	Super::BeginPlay();
	if (!Course && GetOwner())
	{
		Course = GetOwner()->FindComponentByClass<UStardustCourseComponent>();
	}
}

bool UStardustRaceProgressComponent::StartRace()
{
	if (State == EStardustRaceState::Racing)
	{
		return true;
	}
	if (State != EStardustRaceState::Waiting || !Course || Course->StationCount < 2 || Course->CourseLengthM <= 0.0f)
	{
		return false;
	}

	ResetRace();
	FinishDistanceM = FMath::Clamp(Course->CourseLengthM * FMath::Clamp(FinishDistanceFraction, 0.2f, 1.0f),
		FMath::Min(Course->CourseLengthM, 4000.0f), Course->CourseLengthM);
	CheckpointCount = CheckpointCountOverride > 0
		? FMath::Clamp(CheckpointCountOverride, 1, 40)
		: FMath::Clamp(FMath::RoundToInt(FinishDistanceM / 2500.0f), 4, 40);
	State = EStardustRaceState::Racing;
	return true;
}

void UStardustRaceProgressComponent::ResetRace()
{
	State = EStardustRaceState::Waiting;
	RaceDistanceM = 0.0f;
	FinishDistanceM = 0.0f;
	ElapsedTimeSeconds = 0.0f;
	FinishTimeSeconds = -1.0f;
	CheckpointCount = 0;
	CurrentCheckpoint = 0;
	CurrentPathIndex = 0;
	CurrentStationIndex = INDEX_NONE;
}

void UStardustRaceProgressComponent::AbandonRace()
{
	if (State == EStardustRaceState::Racing)
	{
		State = EStardustRaceState::Abandoned;
	}
}

void UStardustRaceProgressComponent::TickComponent(float DeltaTime, ELevelTick TickType,
	FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (State != EStardustRaceState::Racing || !Course || !GetOwner() || DeltaTime <= 0.0f)
	{
		return;
	}

	ElapsedTimeSeconds += DeltaTime;
	int32 LocatedPathIndex = INDEX_NONE;
	int32 LocatedStationIndex = INDEX_NONE;
	if (!Course->LocateCoursePath(GetOwner()->GetActorLocation(), CurrentPathIndex, CurrentStationIndex,
		LocatedPathIndex, LocatedStationIndex))
	{
		return;
	}
	CurrentPathIndex = LocatedPathIndex;
	CurrentStationIndex = LocatedStationIndex;
	const float StationDistanceM = Course->GetDistanceAtPathStation(CurrentPathIndex, CurrentStationIndex);
	FStardustCoursePoint CurrentPoint;
	if (StationDistanceM < 0.0f || !Course->SamplePathAtDistance(CurrentPathIndex, StationDistanceM, CurrentPoint))
	{
		return;
	}
	const float PathDistanceM = CurrentPoint.DistanceM + FVector::DotProduct(
		GetOwner()->GetActorLocation() - CurrentPoint.PositionCm, CurrentPoint.Tangent) / 100.0f;
	RaceDistanceM = FMath::Clamp(Course->MapPathDistanceToRaceDistance(CurrentPathIndex, PathDistanceM), 0.0f, FinishDistanceM);

	const int32 ReachedCheckpoint = FMath::Clamp(FMath::FloorToInt(RaceDistanceM / FinishDistanceM * CheckpointCount), 0, CheckpointCount);
	while (CurrentCheckpoint < ReachedCheckpoint)
	{
		++CurrentCheckpoint;
		OnCheckpointReached.Broadcast(CurrentCheckpoint, CheckpointCount);
	}

	const bool bReachedFinishDistance = RaceDistanceM >= FinishDistanceM - 3.0f;
	const bool bReachedMainEnd = CurrentPathIndex == 0 && CurrentStationIndex >= Course->StationCount - 3;
	if (bReachedFinishDistance || bReachedMainEnd)
	{
		RaceDistanceM = FinishDistanceM;
		FinishTimeSeconds = ElapsedTimeSeconds;
		State = EStardustRaceState::Extracted;
		OnRaceFinished.Broadcast(FinishTimeSeconds, FinishDistanceM);
	}
}
