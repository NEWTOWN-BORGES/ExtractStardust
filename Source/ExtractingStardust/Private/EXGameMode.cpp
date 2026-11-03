#include "EXGameMode.h"

#include "Arena/EXPhysicsSandbox.h"
#include "Arena/EXTestArena.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/Engine.h"
#include "GameFramework/GameUserSettings.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialParameterCollection.h"
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
	ApplyGraphics(World, false);
	// Full screen, borderless, over the taskbar (player, 2026-10-30: "janela cheia sem barra do Windows ou da janela");
	// -windowed (the tests) keeps a window.
	if (GEngine && !FParse::Param(FCommandLine::Get(), TEXT("windowed")))
	{
		if (UGameUserSettings* Settings = GEngine->GetGameUserSettings())
		{
			if (Settings->GetFullscreenMode() != EWindowMode::WindowedFullscreen)
			{
				Settings->SetFullscreenMode(EWindowMode::WindowedFullscreen);
				Settings->SetScreenResolution(Settings->GetDesktopResolution());
				Settings->ApplySettings(false);
			}
		}
	}
	ApplyStyle(World);
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
	// The physics sandbox (Scripts\jogar.ps1 -Modo Sandbox): its own loop of ramps, crests, drops and a pack of bots,
	// built high above whatever map is open; no race, no menu (Docs/FISICA.md).
	const bool bSandbox = FParse::Param(Line, TEXT("EXSandbox"));
	if (bSandbox)
	{
		World->SpawnActor<AEXPhysicsSandbox>(AEXPhysicsSandbox::Origin(), FRotator::ZeroRotator, Params);
	}
	const bool bAutomated = bSandbox || FParse::Param(Line, TEXT("EXFlightTest")) || FParse::Param(Line, TEXT("EXTour"))
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

void AEXGameMode::ApplyGraphics(UWorld* World, bool bShowroom)
{
	// Graphics profiles (player, 2026-10-27: "otimize, está lento"; then "melhorar o serrilhamento" and "aumentem os
	// gráficos no menu"). Race: Lumen at an 85 % internal resolution upscaled by TSR with a supersampled history (much
	// less shimmer and jaggies), lighter fog grid, cloud and reflection sampling. Showroom (menu, hangar): full
	// resolution, full-resolution Lumen reflections traced on rougher paint too, sharper shadows. -EXUltra: the
	// showroom's quality in the race as well. -EXLow (Jogar Leve.bat): no Lumen, no virtual shadows.
	if (!GEngine || !World)
	{
		return;
	}
	const bool bLow = FParse::Param(FCommandLine::Get(), TEXT("EXLow"));
	const bool bUltra = !bLow && FParse::Param(FCommandLine::Get(), TEXT("EXUltra"));
	TArray<const TCHAR*> Commands;
	if (bLow)
	{
		Commands = { TEXT("r.DynamicGlobalIlluminationMethod 0"), TEXT("r.ReflectionMethod 2"), TEXT("r.Shadow.Virtual.Enable 0"),
			TEXT("r.VolumetricFog.GridPixelSize 16"), TEXT("r.ScreenPercentage 67"), TEXT("r.VolumetricCloud.ViewRaySampleMaxCount 192") };
	}
	else if (bShowroom || bUltra)
	{
		Commands = { TEXT("r.DynamicGlobalIlluminationMethod 1"), TEXT("r.ReflectionMethod 1"), TEXT("r.Shadow.Virtual.Enable 1"),
			TEXT("r.AntiAliasingMethod 4"), TEXT("r.ScreenPercentage 100"), TEXT("r.TSR.History.ScreenPercentage 100"),
			TEXT("r.VolumetricFog.GridPixelSize 12"), TEXT("r.VolumetricCloud.ViewRaySampleMaxCount 256"),
			TEXT("r.Lumen.Reflections.DownsampleFactor 1"), TEXT("r.Lumen.Reflections.MaxRoughnessToTrace 0.6"),
			TEXT("r.Shadow.Virtual.ResolutionLodBiasDirectional 0"), TEXT("r.Shadow.Virtual.ResolutionLodBiasLocal 0") };   // sharper ones stuttered the hangar
	}
	else
	{
		Commands = { TEXT("r.AntiAliasingMethod 4"), TEXT("r.ScreenPercentage 75"), TEXT("r.TSR.History.ScreenPercentage 100"),
			TEXT("r.VolumetricFog.GridPixelSize 12"), TEXT("r.VolumetricCloud.ViewRaySampleMaxCount 256"),
			TEXT("r.Lumen.Reflections.DownsampleFactor 2"), TEXT("r.Lumen.Reflections.MaxRoughnessToTrace 0.4"),
			TEXT("r.Shadow.Virtual.ResolutionLodBiasDirectional 0.5"), TEXT("r.Shadow.Virtual.ResolutionLodBiasLocal 0") };
	}
	for (const TCHAR* Command : Commands)
	{
		GEngine->Exec(World, Command);
	}
}

void AEXGameMode::ApplyStyle(UWorld* World)
{
	// Player, 2026-10-27: "uma versão gráfica tipo Rocket League". The photoreal look stays the default; -EXStyle=Arcade
	// (Jogar Arcade.bat) turns the materials clean and saturated (MPC_Style, see Scripts/style_mpc.py), lifts the sun and
	// the sky (softer, brighter shadows) and grades livelier, with more bloom and no film grain.
	// A build of its own (Builds\JogoArcade) carries an Arcade.txt beside the game's folder, so it opens arcade.
	FString Style;
	FParse::Value(FCommandLine::Get(), TEXT("EXStyle="), Style);
	const bool bArcadeBuild = FPaths::FileExists(FPaths::Combine(FPaths::RootDir(), TEXT("Arcade.txt")));
	if (!World || !(bArcadeBuild || Style.Equals(TEXT("Arcade"), ESearchCase::IgnoreCase)))
	{
		return;
	}
	if (UMaterialParameterCollection* Collection = LoadObject<UMaterialParameterCollection>(nullptr, TEXT("/Game/World/MPC_Style.MPC_Style")))
	{
		UKismetMaterialLibrary::SetScalarParameterValue(World, Collection, TEXT("Stylize"), 1.0f);
	}
	for (TActorIterator<ADirectionalLight> It(World); It; ++It)
	{
		if (ULightComponent* Sun = It->GetLightComponent())
		{
			Sun->SetIntensity(Sun->Intensity * 1.25f);
		}
	}
	for (TActorIterator<ASkyLight> It(World); It; ++It)
	{
		if (USkyLightComponent* Sky = It->GetLightComponent())
		{
			Sky->SetIntensity(Sky->Intensity * 1.6f);
		}
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	if (APostProcessVolume* Post = World->SpawnActor<APostProcessVolume>(FVector::ZeroVector, FRotator::ZeroRotator, Params))
	{
		Post->bUnbound = true;
		Post->Priority = 50.0f;
		FPostProcessSettings& Settings = Post->Settings;
		Settings.bOverride_ColorSaturation = true;
		Settings.ColorSaturation = FVector4(1.2f, 1.2f, 1.2f, 1.0f);
		Settings.bOverride_ColorContrast = true;
		Settings.ColorContrast = FVector4(1.08f, 1.08f, 1.08f, 1.0f);
		Settings.bOverride_BloomIntensity = true;
		Settings.BloomIntensity = 1.3f;
		Settings.bOverride_FilmGrainIntensity = true;
		Settings.FilmGrainIntensity = 0.0f;
		Settings.bOverride_AutoExposureBias = true;
		Settings.AutoExposureBias = 0.25f;
	}
}

AActor* AEXGameMode::ChoosePlayerStart_Implementation(AController* Player)
{
	return IsValid(ArenaPlayerStart) ? ArenaPlayerStart.Get() : Super::ChoosePlayerStart_Implementation(Player);
}
