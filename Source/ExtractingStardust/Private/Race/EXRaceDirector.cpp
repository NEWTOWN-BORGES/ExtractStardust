#include "Race/EXRaceDirector.h"

#include "Engine/World.h"
#include "Flight/EXHoverCraft.h"
#include "Game/EXProfile.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformMisc.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/DateTime.h"
#include "Misc/Parse.h"

namespace
{
	constexpr float RaceCmPerM = 100.0f;
	constexpr int32 GridRows = 3;
	constexpr int32 GridColumns = 6;
	constexpr float GridFrontM = 90.0f;     // the front row stands this far along the race line from A
	constexpr float CheckpointEveryM = 2500.0f;  // checkpoints along the line, as in the Unity version
	constexpr int32 CheckpointPrize = 40;         // STARDUST per checkpoint, paid on extraction
	constexpr int32 AllCheckpointsPrize = 300;    // and this on top for all of them
	constexpr float RowGapM = 14.0f;
	constexpr float ColumnGapM = 8.0f;      // 6 abreast in 48 m: the road at the start is 60 m wide
	constexpr float FinishMarginM = 25.0f;  // the finish line: this far before the end of the race line (B)
	constexpr float BotsAfterPlayerS = 15.0f;  // Bots mode: the race ends this long after the player is done (Enter ends it at once)
	constexpr float FinishRadiusM = 45.0f;      // reaching the last point of the line also counts as the finish
	constexpr float TestTimeLimitS = 1500.0f;
	constexpr int32 MenuItems = 4;          // 0 solo, 1 bots, 2 hangar, 3 quit
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
	TestLimitS = TestTimeLimitS;
	FParse::Value(FCommandLine::Get(), TEXT("EXRaceSeconds="), TestLimitS);
}

void AEXRaceDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bMenu || Mode == EEXRaceMode::Hangar)
	{
		// The menu stands in the workshop: the chosen ship on the turntable, the lights down (the ship can be changed
		// from the menu too). The hangar switches the lights on.
		if (AEXHoverCraft* Player = Cast<AEXHoverCraft>(UGameplayStatics::GetPlayerPawn(this, 0)))
		{
			Player->SetRaceHold(true);
			if (bMenu)
			{
				Player->EnterShowroom();
			}
			else if (!Player->IsInHangar())
			{
				Player->EnterHangar();
			}
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
		const int32 Beep = FMath::CeilToInt(Countdown);   // the lights: 3, 2, 1, then the start
		if (Beep != LastCountdownBeep && Beep >= 1 && Beep <= 3)
		{
			LastCountdownBeep = Beep;
			if (AEXHoverCraft* Me = PlayerCraft())
			{
				Me->PlayChime(10);
			}
		}
		if (Countdown <= 0.0f)
		{
			bStarted = true;
			if (AEXHoverCraft* Me = PlayerCraft())
			{
				Me->PlayChime(11);
			}
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
			DropToPool(Racer);
		}
		else if (Craft->GetRaceProgressM() >= RouteLengthM - FinishMarginM
			|| (Route.Num() > 0 && FVector2D::Distance(FVector2D(Craft->GetActorLocation().X, Craft->GetActorLocation().Y) / 100.0, FVector2D(Route.Last())) < FinishRadiusM))
		{
			Racer.bFinished = true;
			Racer.FinishTime = RaceTime;
			Racer.Checkpoint = CheckpointCount;   // B is the last checkpoint
			if (Racer.bPlayer)
			{
				PlayerCheckpoint = CheckpointCount;
				LastCheckpointTime = RaceTime;
			}
			Craft->SetRaceHold(true);
			Post(FString::Printf(TEXT("%s chegou a B em %s"), *Racer.Name, *DirectorClock(RaceTime)));
		}
		// Checkpoints: any line counts by the distance along the race (as in the Unity version).
		const int32 Reached = FMath::Clamp(FMath::FloorToInt(Craft->GetRaceProgressM() / FMath::Max(1.0f, RouteLengthM) * CheckpointCount), 0, CheckpointCount);
		if (!Racer.bOut && Reached > Racer.Checkpoint)
		{
			Racer.Checkpoint = Reached;
			if (Racer.bPlayer)
			{
				PlayerCheckpoint = Reached;
				LastCheckpointTime = RaceTime;
				if (Reached < CheckpointCount)
				{
					Post(FString::Printf(TEXT("CHECKPOINT %d / %d  ·  %s  ·  +%d STARDUST"), Reached, CheckpointCount, *DirectorClock(RaceTime), CheckpointPrize));
					Craft->PlayChime(12);
				}
			}
		}
		if (Racer.bPlayer && (Racer.bOut || Racer.bFinished))
		{
			PlayerDoneTime = RaceTime;
		}
	}
	UpdateStandings();
	if (RaceTime > 3.0f)
	{
		FpsTime += DeltaSeconds;
		++FpsFrames;
		WorstDt = FMath::Max(WorstDt, DeltaSeconds);
	}

	bool bAllDone = true;
	for (const FEXRacer& Racer : Racers)
	{
		bAllDone &= Racer.bFinished || Racer.bOut;
	}
	const bool bPlayerDone = PlayerDoneTime >= 0.0f;
	// Solo: over when the player is done. Bots: when everyone is done, or a minute after the player.
	if (bAllDone || (bPlayerDone && (Mode == EEXRaceMode::Solo || RaceTime - PlayerDoneTime > BotsAfterPlayerS))
		|| (bTest && RaceTime > TestLimitS))
	{
		Finish();
	}
}

void AEXRaceDirector::MenuInput(int32 Step)
{
	if (!bMenu)
	{
		// On the results: Enter / X goes back to the menu. Past the line, before the results: it shows them at once.
		if (bOver && Step == 0 && OverTime > 1.5f)
		{
			ReturnToMenu();
		}
		else if (!bOver && Step == 0 && PlayerDoneTime >= 0.0f && RaceTime - PlayerDoneTime > 1.0f)
		{
			Finish();
		}
		return;
	}
	if (Step != 0)
	{
		MenuChoice = (MenuChoice + Step + MenuItems) % MenuItems;
		return;
	}
	if (MenuChoice == 3)
	{
		if (APlayerController* PlayerController = UGameplayStatics::GetPlayerController(this, 0))
		{
			PlayerController->ConsoleCommand(TEXT("quit"));
		}
		return;
	}
	bMenu = false;
	AEXHoverCraft* Player = Cast<AEXHoverCraft>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (MenuChoice == 2)
	{
		Mode = EEXRaceMode::Hangar;
		if (Player)
		{
			Player->EnterHangar();
		}
		return;
	}
	if (Player)
	{
		Player->ExitShowroom();   // back to the start, before Setup puts it on the grid
	}
	Mode = MenuChoice == 0 ? EEXRaceMode::Solo : EEXRaceMode::Bots;
	LastRaceMode = Mode;
	if (Mode == EEXRaceMode::Bots)
	{
		BotCount = 15;
	}
}

void AEXRaceDirector::LaunchExpedition()
{
	if (AEXHoverCraft* Player = Cast<AEXHoverCraft>(UGameplayStatics::GetPlayerPawn(this, 0)))
	{
		Player->ExitShowroom();
	}
	bMenu = false;
	Mode = LastRaceMode;
	if (Mode == EEXRaceMode::Bots)
	{
		BotCount = 15;
	}
}

void AEXRaceDirector::ReturnToMenu()
{
	UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this, true)));
}

void AEXRaceDirector::HoverMenuChoice(int32 Choice)
{
	if (bMenu)
	{
		MenuChoice = FMath::Clamp(Choice, 0, MenuItems - 1);
	}
}

void AEXRaceDirector::StartMenuChoice(int32 Choice)
{
	if (!bMenu)
	{
		return;
	}
	MenuChoice = FMath::Clamp(Choice, 0, MenuItems - 1);
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
	CheckpointCount = FMath::Clamp(FMath::RoundToInt(RouteLengthM / CheckpointEveryM), 4, 40);
	Pool = 0;
	PoolItems.Reset();
	LastPoolGain = 0;
	LastPoolTime = -100.0f;
	PlayerCheckpoint = 0;
	LastCheckpointTime = -100.0f;
	Summary = FEXRaceSummary();

	// Solo: the front row, in the middle. Bots: the back row (the player has to fight through).
	const int32 PlayerSlot = Mode == EEXRaceMode::Bots ? (GridRows - 1) * GridColumns + 2 : 2;
	LootRandom.Initialize(static_cast<int32>(FDateTime::Now().GetTicks() & 0x7fffffff));
	// What the hangar fitted (Docs/MODULOS.md): the modules and the four quick slots, at risk until B. The consumables
	// carried leave the safe stock; the ones not used come back on extraction.
	Player->SetRaceRules();
	TArray<FEXItem> MyModules;
	int32 MyInsured = 0;
	if (UEXProfileSave* Profile = Player->EnsureProfile())
	{
		const FString Ship = Player->GetShipName();
		MyModules = Profile->EquippedCopy(Ship);
		const FEXBuild* Build = Profile->FindBuild(Ship);
		MyInsured = Build ? Build->Insured : 0;
		EXEconomy::SanitizeQuick(Profile);
		Player->SetQuickSlots(Profile->Quick);
		for (const FEXQuickSlot& Quick : Profile->Quick)
		{
			Profile->AddStock(static_cast<EEXConsumable>(Quick.Kind), -Quick.Count);
		}
	}
	Player->SetModules(MyModules);
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
	Me.Modules = MyModules;
	Me.Insured = MyInsured;

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
			const float Lane = ((Slot % GridColumns) - (GridColumns - 1) * 0.5f) * ColumnGapM;   // its grid column
			Craft->SetRaceRules();
			Craft->SetBot(Bot % 5, Skill, Lane);
			// Real pieces (doc 03): what a destroyed bot loses is real loot for the extractors. Better bots, better gear.
			TArray<FEXItem> BotModules;
			EXMeta::RollBotBuild(Craft->GetShipName(), Skill >= 0.92f ? 2 : (Skill >= 0.87f ? 1 : 0), LootRandom, BotSerial, BotModules);
			Craft->SetModules(BotModules);
			const int32 Tier = Skill >= 0.92f ? 2 : (Skill >= 0.87f ? 1 : 0);
			TArray<FEXItem> BotCargo;
			EXMeta::RollBotCargo(Tier, LootRandom, BotSerial, 2 + Tier + LootRandom.RandRange(0, 2), BotCargo);
			Craft->SetRaceHold(true);
			PlaceOnGrid(Craft, Slot);
			FEXRacer& Racer = Racers.AddDefaulted_GetRef();
			Racer.Craft = Craft;
			Racer.Name = FString::Printf(TEXT("%s #%d"), *Craft->GetShipName(), Bot + 2);
			Racer.Modules = BotModules;
			Racer.Cargo = BotCargo;
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
	// Player, 2026-10-26: the grid in straight rows, every craft facing the same way. The rows stand behind the front
	// row along the direction of the line there (not along its curve), the columns square to it.
	const int32 Row = Slot / GridColumns;
	const int32 Column = Slot % GridColumns;
	const int32 I = FMath::Clamp(FMath::RoundToInt(GridFrontM / 5.0f), 4, Route.Num() - 5);
	const FVector2D Dir = (Route[I + 4] - Route[I - 4]).GetSafeNormal();
	const FVector2D Spot = Route[I] - Dir * (Row * RowGapM) + FVector2D(-Dir.Y, Dir.X) * ((Column - (GridColumns - 1) * 0.5f) * ColumnGapM);
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

int32 AEXRaceDirector::GetCheckpointPrize()
{
	return CheckpointPrize;
}

void AEXRaceDirector::Finish()
{
	bOver = true;
	// The bots still racing get a finishing time from their pace so far (as in the Unity version): a full classification.
	for (FEXRacer& Racer : Racers)
	{
		if (Racer.bPlayer || Racer.bFinished || Racer.bOut || !IsValid(Racer.Craft))
		{
			continue;
		}
		const float Progress = Racer.Craft->GetRaceProgressM();
		const float Pace = FMath::Max(60.0f, Progress / FMath::Max(1.0f, RaceTime));
		Racer.FinishTime = RaceTime + FMath::Max(0.0f, RouteLengthM - Progress) / Pace;
		Racer.bFinished = true;
		Racer.bProjected = true;
		Racer.Checkpoint = CheckpointCount;
	}
	for (FEXRacer& Racer : Racers)
	{
		if (IsValid(Racer.Craft))
		{
			Racer.Craft->SetRaceHold(true);
		}
	}
	UpdateStandings();
	SettleExtraction();
	UpdateStandings();
	Summary.Place = PlayerPlace;
	if (FpsFrames > 0)
	{
		UE_LOG(LogTemp, Display, TEXT("EXRACE FPS average %.1f worst %.1f over %.0f s"), FpsFrames / FMath::Max(0.01f, FpsTime),
			1.0f / FMath::Max(0.001f, WorstDt), FpsTime);
	}
	Post(FString::Printf(TEXT("FIM DA EXPEDI\u00C7\u00C3O  \u00B7  esp\u00F3lio %d STARDUST"), Pool));
	for (int32 Place = 0; Place < Standings.Num(); ++Place)
	{
		const FEXRacer& Racer = Standings[Place];
		const FString Result = Racer.bFinished ? DirectorClock(Racer.FinishTime)
			: (Racer.bOut ? FString::Printf(TEXT("ficou no km %.1f"), Racer.OutAtM / 1000.0f)
				: FString::Printf(TEXT("ainda no km %.1f"), IsValid(Racer.Craft) ? Racer.Craft->GetRaceProgressM() / 1000.0f : 0.0f));
		static const TCHAR* States[4] = { TEXT("-"), TEXT("EXTRACTED"), TEXT("DESTROYED"), TEXT("STRANDED") };
		UE_LOG(LogTemp, Display, TEXT("EXRACE RESULT %2d %s %s %s +%d"), Place + 1, *Racer.Name, *Result, States[FMath::Min<int32>(Racer.State, 3)],
			Racer.Reward);
	}
}

int32 AEXRaceDirector::GetRivalsTotal() const
{
	return FMath::Max(0, Racers.Num() - 1);
}

int32 AEXRaceDirector::GetRivalsLeft() const
{
	int32 Left = 0;
	for (const FEXRacer& Racer : Racers)
	{
		Left += !Racer.bPlayer && !Racer.bOut ? 1 : 0;
	}
	return Left;
}

int32 AEXRaceDirector::GetCargoInPlay() const
{
	int32 Value = 0;
	for (const FEXRacer& Racer : Racers)
	{
		if (!Racer.bPlayer && !Racer.bOut)
		{
			for (const FEXItem& Item : Racer.Cargo)
			{
				Value += Item.Value;
			}
		}
	}
	return Value;
}

void AEXRaceDirector::DropToPool(FEXRacer& Racer)
{
	// Destroyed: all its modules but the insured one and all its cargo fall into the piggy bank.
	if (Racer.bDropped)
	{
		return;
	}
	Racer.bDropped = true;
	Racer.Dropped.Reset();
	for (const int32 Lost : EXMeta::SelectLosses(Racer.Modules, Racer.Insured, LootRandom))
	{
		Racer.Dropped.Add(Racer.Modules[Lost]);
	}
	Racer.Dropped.Append(Racer.Cargo);
	Racer.Cargo.Reset();
	int32 Value = 0;
	for (const FEXItem& Item : Racer.Dropped)
	{
		Value += Item.Value;
	}
	Racer.LostValue = Value;
	PoolItems.Append(Racer.Dropped);
	Pool += Value;
	if (!Racer.bPlayer && Value > 0)
	{
		if (AEXHoverCraft* Me = PlayerCraft())
		{
			Me->PlayChime(13);   // coins falling into the piggy bank
		}
	}
	LastPoolGain = Value;
	LastPoolTime = RaceTime;
	Post(Value > 0 ? FString::Printf(TEXT("%s DESTRU\u00CDDO  \u00B7  +%s no porquinho (%d pe\u00E7as)"), *Racer.Name, *FString::FromInt(Value), Racer.Dropped.Num())
		: FString::Printf(TEXT("%s DESTRU\u00CDDO (km %.1f)"), *Racer.Name, Racer.OutAtM / 1000.0f));
}

AEXHoverCraft* AEXRaceDirector::PlayerCraft() const
{
	for (const FEXRacer& Racer : Racers)
	{
		if (Racer.bPlayer && IsValid(Racer.Craft))
		{
			return Racer.Craft;
		}
	}
	return nullptr;
}

void AEXRaceDirector::SettleExtraction()
{
	// EXTRACTED: reached B alive. DESTROYED: dropped all but the insured module and its cargo into the piggy bank (never the
	// insured module). STRANDED: still on the way (keeps everything, wins nothing).
	PlayerNews.Reset();
	TArray<int32> Extracted;
	for (int32 Index = 0; Index < Racers.Num(); ++Index)
	{
		FEXRacer& Racer = Racers[Index];
		Racer.State = Racer.bFinished ? 1 : (Racer.bOut ? 2 : 3);
		Racer.Reward = 0;
		Racer.Won.Reset();
		Racer.Spoils.Reset();
		if (Racer.State == 2)
		{
			DropToPool(Racer);
		}
		else if (Racer.State == 1)
		{
			Extracted.Add(Index);
		}
	}
	Extracted.Sort([this](int32 A, int32 B) { return Racers[A].FinishTime < Racers[B].FinishTime; });
	for (int32 K = 0; K < Extracted.Num(); ++K)
	{
		FEXRacer& Racer = Racers[Extracted[K]];
		Racer.Reward = EXMeta::PlaceReward(K + 1) + EXMeta::ExtractedBonus + CheckpointPrize * Racer.Checkpoint
			+ (Racer.Checkpoint >= CheckpointCount ? AllCheckpointsPrize : 0);
	}
	// The piggy bank by order of arrival (Docs/VISAO_JOGO.md): every round the first extractor picks first, so it gets the
	// best pieces; then the second, and so on. The pieces run out, the sharing stops.
	TArray<FEXItem> Loot = PoolItems;
	Loot.Sort([](const FEXItem& A, const FEXItem& B) { return A.Value > B.Value; });
	const int32 Count = Extracted.Num();
	for (int32 K = 0; K < Loot.Num() && Count > 0; ++K)
	{
		Racers[Extracted[K % Count]].Won.Add(Loot[K]);
	}

	// The player's profile: not in the automated test.
	const int32 MeIndex = Racers.IndexOfByPredicate([](const FEXRacer& Racer) { return Racer.bPlayer; });
	// The results screen's summary: what the expedition paid and what changed hands.
	Summary = FEXRaceSummary();
	if (Racers.IsValidIndex(MeIndex))
	{
		const FEXRacer& Mine = Racers[MeIndex];
		Summary.bValid = true;
		Summary.State = Mine.State;
		Summary.Field = Racers.Num();
		Summary.Time = Mine.bFinished ? Mine.FinishTime : RaceTime;
		Summary.DistanceM = Mine.bFinished ? RouteLengthM : (Mine.bOut ? Mine.OutAtM : (IsValid(Mine.Craft) ? Mine.Craft->GetRaceProgressM() : 0.0f));
		Summary.Checkpoints = Mine.Checkpoint;
		Summary.CheckpointCount = CheckpointCount;
		Summary.PoolValue = Pool;
		Summary.Won = Mine.Won;
		Summary.Spoils = Mine.Spoils;
		const int32 Place = Extracted.IndexOfByKey(MeIndex);
		if (Mine.State == 1 && Place != INDEX_NONE)
		{
			Summary.PlaceReward = EXMeta::PlaceReward(Place + 1);
			Summary.ExtractBonus = EXMeta::ExtractedBonus;
			Summary.CheckpointReward = CheckpointPrize * Mine.Checkpoint + (Mine.Checkpoint >= CheckpointCount ? AllCheckpointsPrize : 0);
		}
		if (Mine.State == 2)
		{
			Summary.Lost = Mine.Dropped;
		}
		for (const FEXItem& Item : Mine.Modules)
		{
			if (Item.IsValid() && Item.Serial == Mine.Insured)
			{
				Summary.Saved = Item;
			}
		}
		Summary.Total = Mine.Reward;
	}
	if (bTest || !Racers.IsValidIndex(MeIndex) || !IsValid(Racers[MeIndex].Craft))
	{
		return;
	}
	const FEXRacer& Me = Racers[MeIndex];
	AEXHoverCraft* Player = Me.Craft;
	UEXProfileSave* Profile = Player->GetProfile();
	if (!Profile)
	{
		return;
	}
	const bool bDestroyed = Me.State == 2;
	int32 Gained = Me.Reward;
	if (bDestroyed)
	{
		// The lost pieces leave the profile; the consumables carried are gone (they left the stock at the start).
		for (const FEXItem& Item : Me.Dropped)
		{
			PlayerNews.Add(FString::Printf(TEXT("Perdeste: %s"), *EXMeta::ItemLabel(Item)));
			Profile->RemoveItem(Item.Serial);
		}
	}
	else
	{
		for (const FEXQuickSlot& Quick : Player->GetQuickSlots())
		{
			Profile->AddStock(static_cast<EEXConsumable>(Quick.Kind), Quick.Count);
		}
	}
	if (Me.State == 1)
	{
		const int32 Place = 1 + Extracted.IndexOfByKey(MeIndex);
		PlayerNews.Insert(FString::Printf(TEXT("EXTRACTED em %d.\u00BA lugar: +%d STARDUST"), Place, Me.Reward), 0);
		if (!Profile->bFirstExtractionPaid)
		{
			Profile->bFirstExtractionPaid = true;
			Gained += EXMeta::FirstExtractionBonus;
			Summary.FirstBonus = EXMeta::FirstExtractionBonus;
			Summary.Total = Gained;
			PlayerNews.Add(FString::Printf(TEXT("Primeira extra\u00E7\u00E3o: +%d STARDUST"), EXMeta::FirstExtractionBonus));
		}
		// The pieces change hands with their rolls and value; each takes a serial of this profile.
		for (const TArray<FEXItem>* List : { &Me.Spoils, &Me.Won })
		{
			for (const FEXItem& Got : *List)
			{
				FEXItem Item = Got;
				Item.Serial = Profile->NextSerial++;
				Profile->Items.Add(Item);
				PlayerNews.Add(FString::Printf(TEXT("%s: %s (%s)"), List == &Me.Spoils ? TEXT("Esp\u00F3lio de vit\u00F3ria") : TEXT("Do porquinho"),
					*EXMeta::ItemLabel(Item), *EXMeta::RarityName(static_cast<EEXRarity>(Item.Rarity))));
			}
		}
		++Profile->Extractions;
		Profile->BestPlace = Profile->BestPlace == 0 ? Place : FMath::Min(Profile->BestPlace, Place);
	}
	else if (bDestroyed)
	{
		PlayerNews.Insert(FString(TEXT("DESTRU\u00CDDA: as pe\u00E7as perdidas foram para o porquinho")), 0);
	}
	else
	{
		PlayerNews.Insert(FString(TEXT("STRANDED: ainda a caminho de B, ficas com tudo e n\u00E3o ganhas nada")), 0);
	}
	Profile->Stardust += Gained;
	Profile->LastReward = bDestroyed ? -Me.LostValue : Gained;
	Profile->LastNews = PlayerNews;
	++Profile->Expeditions;
	EXEconomy::RollShop(Profile);
	EXEconomy::SanitizeQuick(Profile);
	EXEconomy::Save(Profile);
}
