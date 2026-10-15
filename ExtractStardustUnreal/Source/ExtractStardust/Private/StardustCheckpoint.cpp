#include "StardustCheckpoint.h"
#include "StardustRaceDirector.h"
#include "StardustHoverPawn.h"
#include "Components/BoxComponent.h"
#include "EngineUtils.h"

AStardustCheckpoint::AStardustCheckpoint()
{
	PrimaryActorTick.bCanEverTick = false;
	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	SetRootComponent(Trigger);
	Trigger->SetBoxExtent(FVector(500.0f, 1200.0f, 600.0f));
	Trigger->SetCollisionProfileName(TEXT("Trigger"));
	Trigger->OnComponentBeginOverlap.AddDynamic(this, &AStardustCheckpoint::OnOverlap);
}

void AStardustCheckpoint::BeginPlay()
{
	Super::BeginPlay();
	if (!RaceDirector)
	{
		for (TActorIterator<AStardustRaceDirector> It(GetWorld()); It; ++It)
		{
			RaceDirector = *It;
			break;
		}
	}
	if (RaceDirector && CheckpointIndex == 0 && !RaceDirector->IsRaceActive()) RaceDirector->StartRace(1, 3);
}

void AStardustCheckpoint::OnOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComponent, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	if (RaceDirector && Cast<AStardustHoverPawn>(OtherActor)) RaceDirector->PassCheckpoint(Cast<APawn>(OtherActor), CheckpointIndex);
}
