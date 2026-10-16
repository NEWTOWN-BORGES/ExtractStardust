#include "StardustGameMode.h"

#include "AI/StardustBotPawn.h"
#include "AI/StardustLineFollowerComponent.h"
#include "Course/StardustCourseData.h"
#include "Course/StardustProceduralCourseActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "GameFramework/PlayerStart.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Math/RotationMatrix.h"
#include "UObject/UObjectGlobals.h"
#include "Vehicle/StardustHovercraftPawn.h"

AStardustGameMode::AStardustGameMode()
{
	DefaultPawnClass = AStardustHovercraftPawn::StaticClass();
}

void AStardustGameMode::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	Super::InitGame(MapName, Options, ErrorMessage);
	if (!GetWorld())
	{
		return;
	}

	FVector StartLocation(0.0f, 0.0f, 150.0f);
	FRotator StartRotation = FRotator::ZeroRotator;
	const FString CoursePath = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Tracks"), TEXT("sandbox_course.bytes"));
	TArray<uint8> CourseBytes;
	FString CourseError;
	FStardustCourseData CourseData;
	const bool bHasCourse = FFileHelper::LoadFileToArray(CourseBytes, *CoursePath) && CourseData.Load(CourseBytes, CourseError);
	if (bHasCourse)
	{
		const FStardustCourseStation& StartStation = CourseData.GetStations()[0];
		StartLocation = StartStation.CenterM * 100.0 + StartStation.Up * 150.0;
		StartRotation = FRotationMatrix::MakeFromXZ(StartStation.Tangent, StartStation.Up).Rotator();
		GetWorld()->SpawnActor<AStardustProceduralCourseActor>();
		const float BotLaneOffsets[] = { -0.55f, 0.55f };
		for (const float LaneU : BotLaneOffsets)
		{
			const float LaneDistanceM = LaneU < 0.0f ? LaneU * StartStation.RideLeftM : LaneU * StartStation.RideRightM;
			const FVector BotLocation = (StartStation.CenterM + StartStation.Right * LaneDistanceM + StartStation.Up * 1.5f) * 100.0;
			const FTransform BotTransform(StartRotation, BotLocation);
			AStardustBotPawn* Bot = GetWorld()->SpawnActorDeferred<AStardustBotPawn>(AStardustBotPawn::StaticClass(),
				BotTransform, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
			if (Bot)
			{
				Bot->LineFollowerComponent->LaneU = LaneU;
				Bot->FinishSpawning(BotTransform);
			}
		}
	}
	else
	{
		UStaticMesh* CubeMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		if (CubeMesh)
		{
			AStaticMeshActor* TestGround = GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0.0f, 0.0f, -10.0f), FRotator::ZeroRotator);
			if (TestGround)
			{
				UStaticMeshComponent* GroundMesh = TestGround->GetStaticMeshComponent();
				GroundMesh->SetStaticMesh(CubeMesh);
				GroundMesh->SetCollisionProfileName(TEXT("BlockAll"));
				TestGround->SetActorScale3D(FVector(400.0f, 400.0f, 0.2f));
			}
		}
	}

	GetWorld()->SpawnActor<APlayerStart>(StartLocation, StartRotation);
}
