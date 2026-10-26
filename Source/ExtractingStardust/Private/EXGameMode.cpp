#include "EXGameMode.h"

#include "Arena/EXTestArena.h"
#include "Engine/Engine.h"
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
	// Nothing on the screen but the game (player, 2026-10-26: the engine's small red warnings polluted it): the
	// engine's on-screen messages are off; -EXDebugText brings them back for testing.
	if (GEngine && !FParse::Param(FCommandLine::Get(), TEXT("EXDebugText")))
	{
		GEngine->bEnableOnScreenDebugMessages = false;
		GEngine->Exec(World, TEXT("DisableAllScreenMessages"));
	}
	// Lumen is the default (Config/DefaultEngine.ini). -EXLow turns it off for more fps on a weak GPU (Jogar Leve.bat);
	// -EXUltra still forces it on.
	if (GEngine)
	{
		if (FParse::Param(FCommandLine::Get(), TEXT("EXLow")))
		{
			for (const TCHAR* Command : { TEXT("r.DynamicGlobalIlluminationMethod 0"), TEXT("r.ReflectionMethod 2"), TEXT("r.Shadow.Virtual.Enable 0"),
				TEXT("r.VolumetricFog.GridPixelSize 16") })
			{
				GEngine->Exec(World, Command);
			}
		}
		else if (FParse::Param(FCommandLine::Get(), TEXT("EXUltra")))
		{
			for (const TCHAR* Command : { TEXT("r.DynamicGlobalIlluminationMethod 1"), TEXT("r.ReflectionMethod 1"), TEXT("r.Shadow.Virtual.Enable 1") })
			{
				GEngine->Exec(World, Command);
			}
		}
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
		// Opened without a mode: the menu chooses (SOLO / PELOTÃO 15 / HANGAR).
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
			if (ModeName.Equals(TEXT("Hangar"), ESearchCase::IgnoreCase))
			{
				Race->Configure(EEXRaceMode::Hangar, 0);
				if (AEXHoverCraft* Player = Cast<AEXHoverCraft>(UGameplayStatics::GetPlayerPawn(World, 0)))
				{
					Player->EnterHangar();
				}
			}
			else
			{
				int32 Bots = 15;
				FParse::Value(FCommandLine::Get(), TEXT("EXBots="), Bots);
				Race->Configure(ModeName.Equals(TEXT("Bots"), ESearchCase::IgnoreCase) ? EEXRaceMode::Bots : EEXRaceMode::Solo,
					FMath::Clamp(Bots, 0, 17));
			}
		}
	}
}

AActor* AEXGameMode::ChoosePlayerStart_Implementation(AController* Player)
{
	return IsValid(ArenaPlayerStart) ? ArenaPlayerStart.Get() : Super::ChoosePlayerStart_Implementation(Player);
}
