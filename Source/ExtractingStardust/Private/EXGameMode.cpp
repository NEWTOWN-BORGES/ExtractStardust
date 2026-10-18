#include "EXGameMode.h"

#include "Arena/EXTestArena.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Flight/EXHoverCraft.h"
#include "GameFramework/PlayerStart.h"

AEXGameMode::AEXGameMode()
{
	DefaultPawnClass = AEXHoverCraft::StaticClass();
}

void AEXGameMode::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	Super::InitGame(MapName, Options, ErrorMessage);
	if (UWorld* World = GetWorld())
	{
		// Maps built for the game (e.g. the desert) bring their own world and a start tagged EXWorld.
		for (TActorIterator<APlayerStart> It(World); It; ++It)
		{
			if (It->ActorHasTag(TEXT("EXWorld")))
			{
				ArenaPlayerStart = *It;
				return;
			}
		}
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		World->SpawnActor<AEXTestArena>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
		ArenaPlayerStart = World->SpawnActor<APlayerStart>(FVector(0.0f, 0.0f, 300.0f), FRotator::ZeroRotator, Params);
	}
}

AActor* AEXGameMode::ChoosePlayerStart_Implementation(AController* Player)
{
	return IsValid(ArenaPlayerStart) ? ArenaPlayerStart.Get() : Super::ChoosePlayerStart_Implementation(Player);
}
