#include "StardustGameMode.h"

#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "GameFramework/PlayerStart.h"
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

	GetWorld()->SpawnActor<APlayerStart>(FVector(0.0f, 0.0f, 150.0f), FRotator::ZeroRotator);
}
