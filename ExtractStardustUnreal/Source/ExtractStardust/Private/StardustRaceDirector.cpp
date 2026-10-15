#include "StardustRaceDirector.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "StardustGameMode.h"
#include "StardustProfileSubsystem.h"

AStardustRaceDirector::AStardustRaceDirector()
{
	PrimaryActorTick.bCanEverTick = true;
}

void AStardustRaceDirector::BeginPlay()
{
	Super::BeginPlay();
	if (!CourseGraph && GetWorld())
	{
		if (const AStardustGameMode* GameMode = GetWorld()->GetAuthGameMode<AStardustGameMode>())
		{
			CourseGraph = GameMode->GetCourseGraph();
		}
	}
}

void AStardustRaceDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bCourseRun && bRaceActive)
	{
		UpdateCourseProgress(CourseRacer.Get());
	}
}

void AStardustRaceDirector::SetCourseGraph(UStardustCourseGraph* InCourseGraph)
{
	CourseGraph = InCourseGraph;
}

void AStardustRaceDirector::StartRace(int32 CheckpointsPerLap, int32 Laps)
{
	CheckpointCount = FMath::Max(1, CheckpointsPerLap);
	TargetLaps = FMath::Max(1, Laps);
	CurrentLap = 1;
	NextCheckpoint = 0;
	StartTime = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0f;
	bCourseRun = false;
	bCourseExtracted = false;
	bRaceActive = true;
}

void AStardustRaceDirector::PassCheckpoint(APawn* Racer, int32 CheckpointIndex)
{
	if (!bRaceActive || bCourseRun || !Racer || CheckpointIndex != NextCheckpoint)
	{
		return;
	}
	++NextCheckpoint;
	if (NextCheckpoint >= CheckpointCount)
	{
		NextCheckpoint = 0;
		++CurrentLap;
		if (CurrentLap > TargetLaps)
		{
			bRaceActive = false;
			if (UGameInstance* GI = GetGameInstance())
			{
				if (UStardustProfileSubsystem* Profile = GI->GetSubsystem<UStardustProfileSubsystem>())
				{
					Profile->RecordRace(500);
				}
			}
			if (GEngine)
			{
				GEngine->AddOnScreenDebugMessage(-1, 7.0f, FColor::Green,
					FString::Printf(TEXT("CORRIDA CONCLUIDA  |  %.2f s  |  +500 Stardust"), GetElapsedSeconds()));
			}
		}
		else if (GEngine)
		{
			GEngine->AddOnScreenDebugMessage(-1, 2.0f, FColor::Cyan,
				FString::Printf(TEXT("VOLTA %d / %d"), CurrentLap, TargetLaps));
		}
	}
}

float AStardustRaceDirector::GetElapsedSeconds() const
{
	return GetWorld() ? FMath::Max(0.0f, GetWorld()->GetTimeSeconds() - StartTime) : 0.0f;
}

bool AStardustRaceDirector::StartCourseRun(APawn* Racer, float LengthFraction)
{
	if (!CourseGraph || !CourseGraph->Paths.IsValidIndex(0) || !CourseGraph->Paths[0].Data || !Racer)
	{
		return false;
	}
	const float CourseLength = CourseGraph->Paths[0].Data->GetLength();
	if (CourseLength <= 0.0f)
	{
		return false;
	}
	const float ClampedFraction = FMath::Clamp(LengthFraction, 0.2f, 1.0f);
	CourseFinishDistance = FMath::Clamp(CourseLength * ClampedFraction,
		FMath::Min(CourseLength, 400000.0f), CourseLength);
	CourseCheckpointCount = FMath::Clamp(FMath::RoundToInt(CourseFinishDistance / 250000.0f), 4, 40);
	CourseRacer = Racer;
	CoursePathIndex = 0;
	CourseStationIndex = 0;
	CourseRaceDistance = 0.0f;
	CourseCheckpointProgress = 0;
	CheckpointCount = CourseCheckpointCount;
	TargetLaps = 1;
	CurrentLap = 1;
	NextCheckpoint = 0;
	StartTime = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0f;
	bCourseRun = true;
	bCourseExtracted = false;
	bRaceActive = true;
	return true;
}

bool AStardustRaceDirector::UpdateCourseProgress(APawn* Racer)
{
	if (!bCourseRun || !bRaceActive || !Racer || Racer != CourseRacer.Get() || !CourseGraph)
	{
		return false;
	}
	const float LateralDistance = CourseGraph->Locate(Racer->GetActorLocation(), CoursePathIndex, CourseStationIndex);
	if (LateralDistance == MAX_flt || !CourseGraph->Paths.IsValidIndex(CoursePathIndex) ||
		!CourseGraph->Paths[CoursePathIndex].Data)
	{
		return false;
	}
	const FStardustCoursePath& Path = CourseGraph->Paths[CoursePathIndex];
	const FStardustCourseStation* Station = Path.Data->GetStation(CourseStationIndex);
	if (!Station)
	{
		return false;
	}
	CourseRaceDistance = CourseGraph->ToRaceDistance(CoursePathIndex, Station->Distance);
	const int32 Checkpoint = FMath::Clamp(
		FMath::FloorToInt(CourseRaceDistance / FMath::Max(1.0f, CourseFinishDistance) * CourseCheckpointCount),
		0, CourseCheckpointCount);
	CourseCheckpointProgress = FMath::Max(CourseCheckpointProgress, Checkpoint);
	NextCheckpoint = FMath::Min(CourseCheckpointProgress, CourseCheckpointCount - 1);

	const bool bAtMainFinish = CoursePathIndex == 0 &&
		CourseStationIndex >= CourseGraph->Paths[0].Data->GetStationCount() - 3;
	if (!bCourseExtracted && (CourseRaceDistance >= CourseFinishDistance - 300.0f || bAtMainFinish))
	{
		bCourseExtracted = true;
		bRaceActive = false;
		if (UGameInstance* GI = GetGameInstance())
		{
			if (UStardustProfileSubsystem* Profile = GI->GetSubsystem<UStardustProfileSubsystem>())
			{
				Profile->RecordRace(500);
			}
		}
		if (GEngine)
		{
			GEngine->AddOnScreenDebugMessage(-1, 7.0f, FColor::Green,
				FString::Printf(TEXT("EXTRACTED  |  %.2f s  |  +500 Stardust"), GetElapsedSeconds()));
		}
	}
	return true;
}

float AStardustRaceDirector::GetCourseProgress() const
{
	return CourseFinishDistance > 0.0f
		? FMath::Clamp(CourseRaceDistance / CourseFinishDistance, 0.0f, 1.0f)
		: 0.0f;
}