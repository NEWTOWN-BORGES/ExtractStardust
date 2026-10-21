#include "EXGameMode.h"

#include "Arena/EXTestArena.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Flight/EXHoverCraft.h"
#include "GameFramework/PlayerStart.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Race/EXRaceDirector.h"
#include "UI/EXHud.h"

AEXGameMode::AEXGameMode()
{
	DefaultPawnClass = AEXHoverCraft::StaticClass();
	HUDClass = AEXHud::StaticClass();
}

void AEXGameMode::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	Super::InitGame(MapName, Options, ErrorMessage);
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	// Maps built for the game (e.g. the desert) bring their own world and a start tagged EXWorld.
	for (TActorIterator<APlayerStart> It(World); It; ++It)
	{
		if (It->ActorHasTag(TEXT("EXWorld")))
		{
			ArenaPlayerStart = *It;
			break;
		}
	}
	if (!ArenaPlayerStart)
	{
		World->SpawnActor<AEXTestArena>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
		ArenaPlayerStart = World->SpawnActor<APlayerStart>(FVector(0.0f, 0.0f, 300.0f), FRotator::ZeroRotator, Params);
	}
	// Game modes (Docs/MODOS_DE_JOGO.md): ?Mode=Solo or ?Mode=Bots on the map URL, or -EXMode=Solo / Bots on the
	// command line. Without one the game opens on the menu (the tests stay in free flight).
	FString ModeName = UGameplayStatics::ParseOption(Options, TEXT("Mode"));
	FParse::Value(FCommandLine::Get(), TEXT("EXMode="), ModeName);
	const TCHAR* Line = FCommandLine::Get();
	const bool bAutomated = FParse::Param(Line, TEXT("EXFlightTest")) || FParse::Param(Line, TEXT("EXTour"))
		|| FParse::Param(Line, TEXT("EXNoMenu")) || FCString::Strifind(Line, TEXT("EXLook=")) != nullptr;
	if (ModeName.IsEmpty() && !bAutomated)
	{
		// Opened without a mode: the menu chooses (SOLO / CONTRA BOTS / VOO LIVRE).
		if (AEXRaceDirector* Race = World->SpawnActor<AEXRaceDirector>(FVector::ZeroVector, FRotator::ZeroRotator, Params))
		{
			Race->Configure(EEXRaceMode::Bots, 15);
			Race->OpenMenu();
		}
	}
	else if (!ModeName.IsEmpty())
	{
		if (AEXRaceDirector* Race = World->SpawnActor<AEXRaceDirector>(FVector::ZeroVector, FRotator::ZeroRotator, Params))
		{
			int32 Bots = 15;
			FParse::Value(FCommandLine::Get(), TEXT("EXBots="), Bots);
			Race->Configure(ModeName.Equals(TEXT("Bots"), ESearchCase::IgnoreCase) ? EEXRaceMode::Bots : EEXRaceMode::Solo,
				FMath::Clamp(Bots, 0, 17));
		}
	}
}

AActor* AEXGameMode::ChoosePlayerStart_Implementation(AController* Player)
{
	return IsValid(ArenaPlayerStart) ? ArenaPlayerStart.Get() : Super::ChoosePlayerStart_Implementation(Player);
}
