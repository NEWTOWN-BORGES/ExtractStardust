#include "EXGameMode.h"

#include "Arena/EXTestArena.h"
#include "Components/SplineComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Flight/EXHoverCraft.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerStart.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "UI/EXHangarMenuWidget.h"
#include "UI/EXHud.h"
#include "World/EXHangarStage.h"

AEXGameMode::AEXGameMode()
{
	PrimaryActorTick.bCanEverTick = true;
	DefaultPawnClass = AEXHoverCraft::StaticClass();
	HUDClass = AEXHud::StaticClass();
}

void AEXGameMode::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bSurvivalModeSelected || bSurvivalRaceFinished)
	{
		return;
	}
	if (!bSurvivalRaceRunning)
	{
		SurvivalCountdownRemaining = FMath::Max(0.0f, SurvivalCountdownRemaining - DeltaSeconds);
		if (SurvivalCountdownRemaining <= 0.0f)
		{
			bSurvivalRaceRunning = true;
			for (AEXHoverCraft* Racer : SurvivalRacers)
			{
				if (IsValid(Racer)) { Racer->SetSurvivalRaceRunning(true); }
			}
			UE_LOG(LogTemp, Display, TEXT("EX_SURVIVAL started: player plus %d bots"), SurvivalRacers.Num() - 1);
		}
		return;
	}

	SurvivalElapsedSeconds += DeltaSeconds;
	SurvivalAliveCount = 0;
	for (AEXHoverCraft* Racer : SurvivalRacers)
	{
		if (IsValid(Racer) && !Racer->IsSurvivalEliminated())
		{
			++SurvivalAliveCount;
		}
	}
	if (SurvivalAliveCount <= 1)
	{
		bSurvivalRaceFinished = true;
		bPlayerSurvived = IsValid(SurvivalPlayer) && !SurvivalPlayer->IsSurvivalEliminated();
		for (AEXHoverCraft* Racer : SurvivalRacers)
		{
			if (IsValid(Racer) && !Racer->IsSurvivalEliminated()) { Racer->SetSurvivalRaceRunning(false); }
		}
		UE_LOG(LogTemp, Display, TEXT("EX_SURVIVAL finished: player_survived=%d time=%.1f seconds"), bPlayerSurvived ? 1 : 0, SurvivalElapsedSeconds);
	}
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

void AEXGameMode::PostLogin(APlayerController* NewPlayer)
{
	Super::PostLogin(NewPlayer);
	if (NewPlayer && NewPlayer->IsLocalController())
	{
		if (FParse::Param(FCommandLine::Get(), TEXT("EXAutoStartSurvival")))
		{
			StartSurvivalRaceFromHangar();
		}
		else if (ShouldShowHangar())
		{
			OpenHangar(NewPlayer);
		}
	}
}

void AEXGameMode::OpenHangar(APlayerController* PlayerController)
{
	AEXHoverCraft* Craft = PlayerController ? Cast<AEXHoverCraft>(PlayerController->GetPawn()) : nullptr;
	UWorld* World = GetWorld();
	if (!Craft || !World)
	{
		UE_LOG(LogTemp, Warning, TEXT("Hangar menu was not opened because the local hover craft is unavailable."));
		return;
	}

	const FVector HangarOrigin = Craft->GetActorLocation() + FVector(0.0, 0.0, 30000.0);
	FActorSpawnParameters SpawnParameters;
	SpawnParameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	HangarStage = World->SpawnActor<AEXHangarStage>(AEXHangarStage::StaticClass(), HangarOrigin, FRotator::ZeroRotator, SpawnParameters);
	Craft->EnterHangarPreview(HangarOrigin + FVector(0.0, 0.0, 260.0));

	HangarWidget = CreateWidget<UEXHangarMenuWidget>(PlayerController, UEXHangarMenuWidget::StaticClass());
	if (HangarWidget)
	{
		HangarWidget->SetGameMode(this);
		HangarWidget->AddToViewport(100);
		FInputModeGameAndUI InputMode;
		InputMode.SetWidgetToFocus(HangarWidget->TakeWidget());
		InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		PlayerController->SetInputMode(InputMode);
		PlayerController->SetShowMouseCursor(true);
	}
}

void AEXGameMode::CycleHangarShip(int32 Direction)
{
	APlayerController* PlayerController = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	if (AEXHoverCraft* Craft = PlayerController ? Cast<AEXHoverCraft>(PlayerController->GetPawn()) : nullptr)
	{
		Craft->SelectShip(Craft->GetSelectedShipIndex() + Direction);
	}
}

void AEXGameMode::StartFlightFromHangar()
{
	bSurvivalModeSelected = false;
	APlayerController* PlayerController = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	AEXHoverCraft* Craft = PlayerController ? Cast<AEXHoverCraft>(PlayerController->GetPawn()) : nullptr;
	CloseHangar();
	if (Craft)
	{
		Craft->StartFromHangar();
	}
	if (PlayerController)
	{
		PlayerController->SetShowMouseCursor(false);
		PlayerController->SetInputMode(FInputModeGameOnly());
	}
}

void AEXGameMode::StartSurvivalRaceFromHangar()
{
	APlayerController* PlayerController = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	AEXHoverCraft* PlayerCraft = PlayerController ? Cast<AEXHoverCraft>(PlayerController->GetPawn()) : nullptr;
	UWorld* World = GetWorld();
	if (!PlayerCraft || !World)
	{
		UE_LOG(LogTemp, Warning, TEXT("EX_SURVIVAL could not start: player craft or world is missing."));
		return;
	}
	USplineComponent* RaceSpline = nullptr;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (It->ActorHasTag(TEXT("EXRoute")))
		{
			RaceSpline = It->FindComponentByClass<USplineComponent>();
			if (RaceSpline)
			{
				break;
			}
		}
	}
	if (!RaceSpline || RaceSpline->GetSplineLength() <= 0.0f)
	{
		UE_LOG(LogTemp, Error, TEXT("EX_SURVIVAL could not start: EXRoute spline is missing."));
		if (GEngine)
		{
			GEngine->AddOnScreenDebugMessage(9301, 5.0f, FColor::Red,
				TEXT("CORRIDA DE SOBREVIVENCIA: a via nao tem spline EXRoute valida."));
		}
		return;
	}

	CloseHangar();
	PlayerCraft->StartFromHangar();
	const float SplineLengthCm = RaceSpline->GetSplineLength();
	float StartDistanceCm = 0.0f;
	const FVector PlayerStartLocation = PlayerCraft->GetActorLocation();
	float ClosestDistanceSq = TNumericLimits<float>::Max();
	for (float Distance = 0.0f; Distance < SplineLengthCm; Distance += 200.0f)
	{
		const FVector Point = RaceSpline->GetLocationAtDistanceAlongSpline(Distance, ESplineCoordinateSpace::World);
		const float DistanceSq = FVector::DistSquared2D(PlayerStartLocation, Point);
		if (DistanceSq < ClosestDistanceSq)
		{
			ClosestDistanceSq = DistanceSq;
			StartDistanceCm = Distance;
		}
	}
	const auto GetGridPoint = [RaceSpline, SplineLengthCm](float DistanceCm)
	{
		if (RaceSpline && SplineLengthCm > 0.0f)
		{
			if (RaceSpline->IsClosedLoop())
			{
				DistanceCm = FMath::Fmod(DistanceCm, SplineLengthCm);
				if (DistanceCm < 0.0f) { DistanceCm += SplineLengthCm; }
			}
			else
			{
				DistanceCm = FMath::Clamp(DistanceCm, 0.0f, SplineLengthCm);
			}
			return RaceSpline->GetLocationAtDistanceAlongSpline(DistanceCm, ESplineCoordinateSpace::World);
		}
		return FVector::ZeroVector;
	};
	SurvivalRacers.Reset();
	SurvivalRacers.Add(PlayerCraft);
	auto ProjectToRoad = [World, PlayerCraft, this](const FVector& RoutePoint, FVector& GroundPoint, FVector& GroundNormal)
	{
		FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(EXRaceGridSpawn), false, PlayerCraft);
		for (AEXHoverCraft* ExistingRacer : SurvivalRacers)
		{
			if (IsValid(ExistingRacer)) { QueryParams.AddIgnoredActor(ExistingRacer); }
		}
		// Retry above the race line if it sits a little below the road surface.
		// Keep the first trace low to avoid snapping to tunnel ceilings.
		static const float StartOffsetsCm[] = { 300.0f, 800.0f, 1500.0f, 3000.0f };
		for (const float StartOffsetCm : StartOffsetsCm)
		{
			FHitResult Hit;
			const FVector TraceStart = RoutePoint + FVector::UpVector * StartOffsetCm;
			const FVector TraceEnd = RoutePoint - FVector::UpVector * 10000.0f;
			if (!World->LineTraceSingleByChannel(Hit, TraceStart, TraceEnd, ECC_Visibility, QueryParams))
			{
				continue;
			}
			const FVector CandidateNormal = Hit.ImpactNormal.GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
			if (CandidateNormal.Z < 0.2f || FMath::Abs(Hit.ImpactPoint.Z - RoutePoint.Z) > 1500.0f)
			{
				continue;
			}
			GroundPoint = Hit.ImpactPoint;
			GroundNormal = CandidateNormal;
			return true;
		}
		return false;
	};
	const FVector PlayerRoutePoint = GetGridPoint(StartDistanceCm);
	FVector PlayerGroundPoint = PlayerRoutePoint;
	FVector PlayerGroundNormal = FVector::UpVector;
	const bool bPlayerProjectedToRoad = ProjectToRoad(PlayerRoutePoint, PlayerGroundPoint, PlayerGroundNormal);
	if (!bPlayerProjectedToRoad)
	{
		// Never leave the player at the old, potentially elevated PlayerStart when a collision query misses.
		// The spline point is the safe fallback; survival countdown physics stays locked until the race starts.
		UE_LOG(LogTemp, Warning, TEXT("EX_SURVIVAL player road projection missed at %.1f, %.1f, %.1f; using EXRoute fallback."),
			PlayerRoutePoint.X, PlayerRoutePoint.Y, PlayerRoutePoint.Z);
	}
	FVector PlayerForward = RaceSpline->GetTangentAtDistanceAlongSpline(StartDistanceCm, ESplineCoordinateSpace::World).GetSafeNormal2D();
	if (PlayerForward.IsNearlyZero())
	{
		PlayerForward = PlayerCraft->GetActorForwardVector().GetSafeNormal2D();
	}
	const FRotator PlayerGridRotation = FRotationMatrix::MakeFromXZ(PlayerForward, PlayerGroundNormal).Rotator();
	const FVector PlayerGridLocation = PlayerGroundPoint + PlayerGroundNormal * PlayerCraft->HoverHeightM * 100.0f;
	PlayerCraft->SetRaceGridStart(PlayerGridLocation, PlayerGridRotation, PlayerGroundNormal);
	UE_LOG(LogTemp, Display, TEXT("EX_SURVIVAL player grid: projected=%d routeZ=%.1f groundZ=%.1f craftZ=%.1f hover=%.2fm"),
		bPlayerProjectedToRoad ? 1 : 0, PlayerRoutePoint.Z, PlayerGroundPoint.Z, PlayerGridLocation.Z, PlayerCraft->HoverHeightM);
	PlayerCraft->ConfigureSurvivalRacer(false, INDEX_NONE, 1.0f);
	PlayerCraft->SetSurvivalRaceRunning(false);
	SurvivalPlayer = PlayerCraft;

	const FVector Forward = PlayerCraft->GetActorForwardVector().GetSafeNormal2D();
	const FVector Right = FVector::CrossProduct(PlayerGroundNormal, Forward).GetSafeNormal();
	const FVector Start = PlayerCraft->GetActorLocation();
	for (int32 BotIndex = 0; BotIndex < 15; ++BotIndex)
	{
		const int32 Row = BotIndex / 4;
		const int32 Column = BotIndex % 4;
		const float SideOffsetCm = (static_cast<float>(Column) - 1.5f) * 350.0f;
		FVector SpawnLocation = Start - Forward * (900.0f * static_cast<float>(Row + 1)) + Right * SideOffsetCm;
		FVector SpawnForward = Forward;
		FVector GroundNormal = PlayerGroundNormal;
		bool bProjectedToRoad = false;
		float GridDistance = StartDistanceCm - 900.0f * static_cast<float>(Row + 1);
		const FVector RoutePoint = GetGridPoint(GridDistance);
		if (RaceSpline->IsClosedLoop())
		{
			GridDistance = FMath::Fmod(GridDistance, SplineLengthCm);
			if (GridDistance < 0.0f) { GridDistance += SplineLengthCm; }
		}
		else
		{
			GridDistance = FMath::Clamp(GridDistance, 0.0f, SplineLengthCm);
		}
		SpawnForward = RaceSpline->GetTangentAtDistanceAlongSpline(GridDistance, ESplineCoordinateSpace::World).GetSafeNormal2D();
		if (SpawnForward.IsNearlyZero()) { SpawnForward = Forward; }
		const FVector SpawnRight = FVector::CrossProduct(PlayerGroundNormal, SpawnForward).GetSafeNormal();
		FVector BotGroundPoint;
		if (ProjectToRoad(RoutePoint + SpawnRight * SideOffsetCm, BotGroundPoint, GroundNormal)
			|| ProjectToRoad(RoutePoint, BotGroundPoint, GroundNormal))
		{
			SpawnLocation = BotGroundPoint + GroundNormal * PlayerCraft->HoverHeightM * 100.0f;
			bProjectedToRoad = true;
		}
		else
		{
			// Keep every fallback bot on the player's snapped road plane, never at a stale sky position.
			GroundNormal = PlayerGroundNormal;
		}
		FActorSpawnParameters SpawnParameters;
		SpawnParameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		const FRotator BotRotation = FRotationMatrix::MakeFromXZ(SpawnForward, GroundNormal).Rotator();
		AEXHoverCraft* Bot = World->SpawnActor<AEXHoverCraft>(AEXHoverCraft::StaticClass(), SpawnLocation, BotRotation, SpawnParameters);
		if (!Bot)
		{
			UE_LOG(LogTemp, Error, TEXT("EX_SURVIVAL failed to spawn bot %d."), BotIndex + 1);
			continue;
		}
		Bot->SelectShip(BotIndex % 4);
		Bot->SetRaceGridStart(SpawnLocation, BotRotation, GroundNormal);
		Bot->ConfigureSurvivalRacer(true, BotIndex, 0.45f + static_cast<float>((BotIndex * 7) % 10) * 0.055f);
		Bot->SetSurvivalRaceRunning(false);
		SurvivalRacers.Add(Bot);
		UE_LOG(LogTemp, Display, TEXT("EX_SURVIVAL bot %d grid: projected=%d row=%d lane=%.1fm routeZ=%.1f craftZ=%.1f"),
			BotIndex + 1, bProjectedToRoad ? 1 : 0, Row, SideOffsetCm / 100.0f, RoutePoint.Z, SpawnLocation.Z);
	}

	bSurvivalModeSelected = true;
	bSurvivalRaceRunning = false;
	bSurvivalRaceFinished = false;
	bPlayerSurvived = false;
	SurvivalAliveCount = SurvivalRacers.Num();
	SurvivalCountdownRemaining = 3.0f;
	SurvivalElapsedSeconds = 0.0f;
	if (PlayerController)
	{
		PlayerController->SetShowMouseCursor(false);
		PlayerController->SetInputMode(FInputModeGameOnly());
	}
	UE_LOG(LogTemp, Display, TEXT("EX_SURVIVAL grid ready: %d of 16 craft spawned; countdown started."), SurvivalRacers.Num());
}

void AEXGameMode::QuitFromHangar()
{
	if (APlayerController* PlayerController = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr)
	{
		PlayerController->ConsoleCommand(TEXT("quit"));
	}
}

void AEXGameMode::CloseHangar()
{
	if (HangarWidget)
	{
		HangarWidget->RemoveFromParent();
		HangarWidget = nullptr;
	}
	if (HangarStage)
	{
		HangarStage->Destroy();
		HangarStage = nullptr;
	}
}

bool AEXGameMode::ShouldShowHangar() const
{
	const TCHAR* CommandLine = FCommandLine::Get();
	return !IsRunningCommandlet()
		&& !FParse::Param(CommandLine, TEXT("EXNoHangar"))
		&& !FParse::Param(CommandLine, TEXT("EXFlightTest"))
		&& !FParse::Param(CommandLine, TEXT("EXTour"))
		&& !FParse::Param(CommandLine, TEXT("EXDesertTest"));
}

int32 AEXGameMode::GetSurvivalCountdownSeconds() const
{
	return bSurvivalModeSelected && !bSurvivalRaceRunning && !bSurvivalRaceFinished
		? FMath::CeilToInt(SurvivalCountdownRemaining)
		: 0;
}

float AEXGameMode::GetPlayerHullPercent() const
{
	return IsValid(SurvivalPlayer) && !SurvivalPlayer->IsSurvivalEliminated() ? SurvivalPlayer->GetHullPercent() : 0.0f;
}
