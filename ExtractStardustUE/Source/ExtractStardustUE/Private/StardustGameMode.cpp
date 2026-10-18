#include "StardustGameMode.h"

#include "AI/StardustBotPawn.h"
#include "AI/StardustLineFollowerComponent.h"
#include "Course/StardustCourseData.h"
#include "Course/StardustProceduralCourseActor.h"
#include "Engine/PlayerStartPIE.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerStart.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Math/RotationMatrix.h"
#include "UObject/UObjectGlobals.h"
#include "Vehicle/StardustHovercraftPawn.h"

namespace
{
	// Position (in metres) on the cross-section ring at LaneU, measured along the surface arc
	// exactly like UStardustCourseComponent::LanePointAtPathDistance.
	FVector LanePointOnStation(const FStardustCourseStation& Station, float LaneU)
	{
		const TArray<FVector>& Ring = Station.RingOffsetsM;
		if (Ring.Num() < 2)
		{
			return Station.CenterM;
		}
		const int32 CenterIndex = Ring.Num() / 2;
		TArray<float> ArcM;
		ArcM.SetNumZeroed(Ring.Num());
		for (int32 Index = CenterIndex + 1; Index < Ring.Num(); ++Index)
		{
			ArcM[Index] = ArcM[Index - 1] + FVector::Distance(Ring[Index], Ring[Index - 1]);
		}
		for (int32 Index = CenterIndex - 1; Index >= 0; --Index)
		{
			ArcM[Index] = ArcM[Index + 1] - FVector::Distance(Ring[Index], Ring[Index + 1]);
		}
		const float TargetArcM = LaneU < 0.0f ? LaneU * Station.RideLeftM : LaneU * Station.RideRightM;
		for (int32 Index = 0; Index + 1 < Ring.Num(); ++Index)
		{
			if (TargetArcM >= ArcM[Index] && TargetArcM <= ArcM[Index + 1])
			{
				const float Span = ArcM[Index + 1] - ArcM[Index];
				const float Alpha = Span > UE_SMALL_NUMBER ? (TargetArcM - ArcM[Index]) / Span : 0.0f;
				return FMath::Lerp(Ring[Index], Ring[Index + 1], Alpha);
			}
		}
		return Ring[CenterIndex];
	}
}

AStardustGameMode::AStardustGameMode()
{
	DefaultPawnClass = AStardustHovercraftPawn::StaticClass();
}

void AStardustGameMode::StartTestBots()
{
	for (AStardustBotPawn* Bot : TestBots)
	{
		if (IsValid(Bot))
		{
			Bot->StartRacing();
		}
	}
}

AActor* AStardustGameMode::ChoosePlayerStart_Implementation(AController* Player)
{
	if (GetWorld())
	{
		for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
		{
			if (It->IsA<APlayerStartPIE>())
			{
				return *It;
			}
		}
	}

	if (IsValid(CoursePlayerStart))
	{
		UE_LOG(LogTemp, Display, TEXT("Using course PlayerStart at %s."), *CoursePlayerStart->GetActorLocation().ToCompactString());
		return CoursePlayerStart;
	}

	return Super::ChoosePlayerStart_Implementation(Player);
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
		UE_LOG(LogTemp, Display, TEXT("Loaded course data: %d stations, %.2f km."), CourseData.GetStations().Num(), CourseData.GetStations().Last().DistanceM / 1000.0f);
		// The collision mesh begins exactly at station 0, so a craft parked there has its rear hover probes over
		// nothing and falls. Put the starting grid a few metres into the course instead.
		constexpr float StartGridOffsetM = 8.0f;
		const int32 StartGridIndex = FMath::Clamp(FMath::CeilToInt(StartGridOffsetM / FMath::Max(0.1f, CourseData.GetStepM())),
			0, CourseData.GetStations().Num() - 1);
		const FStardustCourseStation& StartStation = CourseData.GetStations()[StartGridIndex];
		StartLocation = StartStation.CenterM * 100.0 + StartStation.Up * 150.0;
		StartRotation = FRotationMatrix::MakeFromXZ(StartStation.Tangent, StartStation.Up).Rotator();
		GetWorld()->SpawnActor<AStardustProceduralCourseActor>();
		const float BotLaneOffsets[] = { -0.55f, 0.55f };
		for (const float LaneU : BotLaneOffsets)
		{
			const FVector BotLocation = (LanePointOnStation(StartStation, LaneU) + StartStation.Up * 1.5f) * 100.0;
			UE_LOG(LogTemp, Display, TEXT("Bot grid slot LaneU %.2f at %s."), LaneU, *BotLocation.ToCompactString());
			const FTransform BotTransform(StartRotation, BotLocation);
			AStardustBotPawn* Bot = GetWorld()->SpawnActorDeferred<AStardustBotPawn>(AStardustBotPawn::StaticClass(),
				BotTransform, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
			if (Bot)
			{
				Bot->LineFollowerComponent->LaneU = LaneU;
				Bot->FinishSpawning(BotTransform);
				TestBots.Add(Bot);
			}
		}
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("Course data '%s' is unavailable; starting with the test platform. %s"), *CoursePath, *CourseError);
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

	CoursePlayerStart = GetWorld()->SpawnActor<APlayerStart>(StartLocation, StartRotation);
}
