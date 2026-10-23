#include "Race/EXRaceDirector.h"

#include "Engine/World.h"
#include "Flight/EXHoverCraft.h"
#include "HAL/PlatformMisc.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace
{
	constexpr float RaceCmPerM = 100.0f;
	constexpr int32 GridRows = 3;
	constexpr int32 GridColumns = 6;
	constexpr float GridFrontM = 80.0f;     // the front row stands this far along the race line from A
	constexpr float RowGapM = 14.0f;
	constexpr float ColumnGapM = 8.0f;      // 6 abreast in 48 m: the road at the start is 60 m wide
	constexpr float FinishMarginM = 25.0f;  // the finish line: this far before the end of the race line (B)
	constexpr float BotsAfterPlayerS = 60.0f;  // Bots mode: the race ends this long after the player is done
	constexpr float TestTimeLimitS = 1500.0f;
	/** Bot pace against the ideal line, by bot (the tuning knob for how good the bots are). */
	constexpr float BotSkills[] = { 0.95f, 0.94f, 0.93f, 0.92f, 0.91f, 0.90f, 0.89f, 0.88f, 0.87f, 0.87f, 0.86f, 0.85f, 0.84f, 0.83f, 0.82f };

	FString DirectorClock(float Seconds)
	{
		const int32 Minutes = FMath::FloorToInt(Seconds / 60.0f);
		return FString::Printf(TEXT("%d:%05.2f"), Minutes, Seconds - Minutes * 60.0f);
	}
}

AEXRaceDirector::AEXRaceDirector()
{
	PrimaryActorTick.bCanEverTick = true;
	bTest = FParse::Param(FCommandLine::Get(), TEXT("EXRaceTest"));
}

void AEXRaceDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bMenu || Mode == EEXRaceMode::Hangar)
	{
		// The craft waits on the start while the player chooses (the ship can be changed from the menu too).
		if (AEXHoverCraft* Player = Cast<AEXHoverCraft>(UGameplayStatics::GetPlayerPawn(this, 0)))
		{
			Player->SetRaceHold(true);
		}
		return;
	}
	if (!bReady)
	{
		Setup();
		return;
	}
	if (!bStarted)
	{
		Countdown -= DeltaSeconds;
		if (Countdown <= 0.0f)
		{
			bStarted = true;
			Countdown = 0.0f;
			for (FEXRacer& Racer : Racers)
			{
				if (IsValid(Racer.Craft))
				{
					Racer.Craft->SetRaceHold(false);
					Racer.Craft->LockShip();
				}
			}
			Post(TEXT("PARTIDA!"));
		}
		UpdateStandings();
		return;
	}
	if (bOver)
	{
		OverTime += DeltaSeconds;
		if (bTest && OverTime > 5.0f)
		{
			FPlatformMisc::RequestExit(false);
		}
		return;
	}

	RaceTime += DeltaSeconds;
	for (FEXRacer& Racer : Racers)
	{
		AEXHoverCraft* Craft = Racer.Craft;
		if (!IsValid(Craft) || Racer.bFinished || Racer.bOut)
		{
			continue;
		}
		if (Craft->IsEliminated())
		{
			Racer.bOut = true;
			Racer.OutAtM = Craft->GetRaceProgressM();
			Post(FString::Printf(TEXT("%s ficou pelo caminho (km %.1f)"), *Racer.Name, Racer.OutAtM / 1000.0f));
		}
		else if (Craft->GetRaceProgressM() >= RouteLengthM - FinishMarginM)
		{
			Racer.bFinished = true;
			Racer.FinishTime = RaceTime;
			Craft->SetRaceHold(true);
			Post(FString::Printf(TEXT("%s chegou a B em %s"), *Racer.Name, *DirectorClock(RaceTime)));
		}
		if (Racer.bPlayer && (Racer.bOut || Racer.bFinished))
		{
			PlayerDoneTime = RaceTime;
		}
	}
	UpdateStandings();

	bool bAllDone = true;
	for (const FEXRacer& Racer : Racers)
	{
		bAllDone &= Racer.bFinished || Racer.bOut;
	}
	const bool bPlayerDone = PlayerDoneTime >= 0.0f;
	// Solo: over when the player is done. Bots: when everyone is done, or a minute after the player.
	if (bAllDone || (bPlayerDone && (Mode == EEXRaceMode::Solo || RaceTime - PlayerDoneTime > BotsAfterPlayerS))
		|| (bTest && RaceTime > TestTimeLimitS))
	{
		Finish();
	}
}

void AEXRaceDirector::MenuInput(int32 Step)
{
	if (!bMenu)
	{
		return;
	}
	if (Step != 0)
	{
		MenuChoice = (MenuChoice + Step + 3) % 3;
		return;
	}
	bMenu = false;
	if (MenuChoice == 2)
	{
		Mode = EEXRaceMode::Hangar;
		if (AEXHoverCraft* Player = Cast<AEXHoverCraft>(UGameplayStatics::GetPlayerPawn(this, 0)))
		{
			Player->EnterHangar();
		}
		return;
	}
	Mode = MenuChoice == 0 ? EEXRaceMode::Solo : EEXRaceMode::Bots;
	if (Mode == EEXRaceMode::Bots)
	{
		BotCount = 15;
	}
}

void AEXRaceDirector::StartMenuChoice(int32 Choice)
{
	if (!bMenu)
	{
		return;
	}
	MenuChoice = FMath::Clamp(Choice, 0, 2);
	MenuInput(0);
}

void AEXRaceDirector::Setup()
{
	// The player's craft and its race line exist from its BeginPlay on; until then, wait.
	AEXHoverCraft* Player = Cast<AEXHoverCraft>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!Player || Player->GetMapRoute().Num() < 100)
	{
		return;
	}
	Route = Player->GetMapRoute();
	RouteLengthM = (Route.Num() - 1) * 5.0f;

	// Solo: the front row, in the middle. Bots: the back row (the player has to fight through).
	const int32 PlayerSlot = Mode == EEXRaceMode::Bots ? (GridRows - 1) * GridColumns + 2 : 2;
	Player->SetRaceRules(3);
	if (bTest)
	{
		Player->SetBot(Player->GetShipIndex(), 0.95f, 0.0f);
	}
	Player->SetRaceHold(true);
	PlaceOnGrid(Player, PlayerSlot);
	FEXRacer& Me = Racers.AddDefaulted_GetRef();
	Me.Craft = Player;
	Me.Name = TEXT("TU");
	Me.bPlayer = true;

	if (Mode == EEXRaceMode::Bots)
	{
		int32 Slot = 0;
		for (int32 Bot = 0; Bot < BotCount && Slot < GridRows * GridColumns; ++Bot, ++Slot)
		{
			if (Slot == PlayerSlot)
			{
				++Slot;
			}
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			AEXHoverCraft* Craft = GetWorld()->SpawnActor<AEXHoverCraft>(AEXHoverCraft::StaticClass(),
				Player->GetActorLocation() + FVector(0.0f, 0.0f, 1000.0f * (Bot + 1)), FRotator::ZeroRotator, Params);
			if (!Craft)
			{
				continue;
			}
			// BeginPlay has run inside SpawnActor: the bot has the race line already. Player, 2026-10-21: "not dumb, but
			// not too clever" - no bot drives the ideal line flat out: three tiers (5, 6 and 4 bots) from 95 % down to
			// 82 % of the ideal pace; the weaker wander more in their lane and misjudge more bends. Each keeps roughly
			// to its grid column (lanes 4 m apart round the line).
			const float Skill = BotSkills[Bot % static_cast<int32>(UE_ARRAY_COUNT(BotSkills))];
			const float Lane = ((Slot % GridColumns) - (GridColumns - 1) * 0.5f) * 4.0f;
			Craft->SetRaceRules(0);
			Craft->SetBot(Bot % 5, Skill, Lane);
			Craft->SetRaceHold(true);
			PlaceOnGrid(Craft, Slot);
			FEXRacer& Racer = Racers.AddDefaulted_GetRef();
			Racer.Craft = Craft;
			Racer.Name = FString::Printf(TEXT("%s #%d"), *Craft->GetShipName(), Bot + 2);
		}
	}
	bReady = true;
	Countdown = 4.0f;
	UpdateStandings();
	UE_LOG(LogTemp, Display, TEXT("EXRACE READY mode=%s racers=%d route=%.1f km"), Mode == EEXRaceMode::Bots ? TEXT("Bots") : TEXT("Solo"),
		Racers.Num(), RouteLengthM / 1000.0f);
}

void AEXRaceDirector::PlaceOnGrid(AEXHoverCraft* Craft, int32 Slot)
{
	const int32 Row = Slot / GridColumns;
	const int32 Column = Slot % GridColumns;
	const float AlongM = FMath::Max(10.0f, GridFrontM - Row * RowGapM);
	const int32 I = FMath::Clamp(FMath::RoundToInt(AlongM / 5.0f), 1, Route.Num() - 3);
	const FVector2D Dir = (Route[I + 2] - Route[I - 1]).GetSafeNormal();
	const FVector2D Spot = Route[I] + FVector2D(-Dir.Y, Dir.X) * ((Column - (GridColumns - 1) * 0.5f) * ColumnGapM);
	FVector Location(Spot.X * RaceCmPerM, Spot.Y * RaceCmPerM, Craft->GetActorLocation().Z);
	// The ground under the slot (the craft ignore the Visibility channel once the race rules are on).
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(EXRaceGrid), true);
	if (GetWorld()->LineTraceSingleByChannel(Hit, FVector(Location.X, Location.Y, 200000.0f), FVector(Location.X, Location.Y, -100000.0f),
		ECC_Visibility, Params))
	{
		Location.Z = Hit.ImpactPoint.Z + 250.0f;
	}
	Craft->PlaceAt(Location, FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X)));
}

void AEXRaceDirector::Post(const FString& Message)
{
	Feed.Add(TPair<float, FString>(RaceTime, Message));
	if (Feed.Num() > 8)
	{
		Feed.RemoveAt(0);
	}
	UE_LOG(LogTemp, Display, TEXT("EXRACE t=%s %s"), *DirectorClock(RaceTime), *Message);
}

void AEXRaceDirector::UpdateStandings()
{
	// Finished first (by time), then the ones still racing (by distance), then the ones left on the way (by distance).
	Standings = Racers;
	Standings.Sort([](const FEXRacer& A, const FEXRacer& B)
	{
		const int32 RankA = A.bFinished ? 0 : (A.bOut ? 2 : 1);
		const int32 RankB = B.bFinished ? 0 : (B.bOut ? 2 : 1);
		if (RankA != RankB)
		{
			return RankA < RankB;
		}
		if (RankA == 0)
		{
			return A.FinishTime < B.FinishTime;
		}
		if (RankA == 2)
		{
			return A.OutAtM > B.OutAtM;
		}
		const float ProgressA = IsValid(A.Craft) ? A.Craft->GetRaceProgressM() : 0.0f;
		const float ProgressB = IsValid(B.Craft) ? B.Craft->GetRaceProgressM() : 0.0f;
		return ProgressA > ProgressB;
	});
	PlayerPlace = 1 + FMath::Max(0, Standings.IndexOfByPredicate([](const FEXRacer& Racer) { return Racer.bPlayer; }));
}

void AEXRaceDirector::Finish()
{
	bOver = true;
	for (FEXRacer& Racer : Racers)
	{
		if (IsValid(Racer.Craft))
		{
			Racer.Craft->SetRaceHold(true);
		}
	}
	UpdateStandings();
	Post(TEXT("FIM DA CORRIDA"));
	for (int32 Place = 0; Place < Standings.Num(); ++Place)
	{
		const FEXRacer& Racer = Standings[Place];
		const FString Result = Racer.bFinished ? DirectorClock(Racer.FinishTime)
			: (Racer.bOut ? FString::Printf(TEXT("ficou no km %.1f"), Racer.OutAtM / 1000.0f)
				: FString::Printf(TEXT("ainda no km %.1f"), IsValid(Racer.Craft) ? Racer.Craft->GetRaceProgressM() / 1000.0f : 0.0f));
		UE_LOG(LogTemp, Display, TEXT("EXRACE RESULT %2d %s %s"), Place + 1, *Racer.Name, *Result);
	}
}

