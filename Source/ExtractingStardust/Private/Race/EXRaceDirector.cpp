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
	constexpr float GridFrontM = 80.0f;     // the front row stands this far along the race line from A
	constexpr float RowGapM = 14.0f;
	constexpr float ColumnGapM = 8.0f;      // 6 abreast in 48 m: the road at the start is 60 m wide
	constexpr float FinishMarginM = 25.0f;  // the finish line: this far before the end of the race line (B)
	constexpr float BotsAfterPlayerS = 60.0f;  // Bots mode: the race ends this long after the player is done
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
		// On the results: Enter / X goes back to the menu.
		if (bOver && Step == 0 && OverTime > 1.5f)
		{
			ReturnToMenu();
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
			const float Lane = ((Slot % GridColumns) - (GridColumns - 1) * 0.5f) * 4.0f;
			Craft->SetRaceRules();
			Craft->SetBot(Bot % 5, Skill, Lane);
			// Real pieces (doc 03): what a destroyed bot loses is real loot for the extractors. Better bots, better gear.
			TArray<FEXItem> BotModules;
			EXMeta::RollBotBuild(Craft->GetShipName(), Skill >= 0.92f ? 2 : (Skill >= 0.87f ? 1 : 0), LootRandom, BotSerial, BotModules);
			Craft->SetModules(BotModules);
			Craft->SetRaceHold(true);
			PlaceOnGrid(Craft, Slot);
			FEXRacer& Racer = Racers.AddDefaulted_GetRef();
			Racer.Craft = Craft;
			Racer.Name = FString::Printf(TEXT("%s #%d"), *Craft->GetShipName(), Bot + 2);
			Racer.Modules = BotModules;
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
	SettleExtraction();
	UpdateStandings();
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

void AEXRaceDirector::SettleExtraction()
{
	// EXTRACTED: reached B alive. DESTROYED: no lives left (up to three of its modules go to the pool, never the insured
	// one). STRANDED: still on the way (keeps everything, wins nothing).
	Pool = 0;
	PlayerNews.Reset();
	TArray<FEXItem> Loot;
	TArray<int32> Extracted;
	for (int32 Index = 0; Index < Racers.Num(); ++Index)
	{
		FEXRacer& Racer = Racers[Index];
		Racer.State = Racer.bFinished ? 1 : (Racer.bOut ? 2 : 3);
		Racer.Reward = 0;
		Racer.LostValue = 0;
		Racer.Won.Reset();
		if (Racer.State == 2)
		{
			for (const int32 Lost : EXMeta::SelectLosses(Racer.Modules, Racer.Insured, LootRandom))
			{
				Loot.Add(Racer.Modules[Lost]);
				Racer.LostValue += Racer.Modules[Lost].Value;
			}
			Pool += Racer.LostValue;
		}
		else if (Racer.State == 1)
		{
			Extracted.Add(Index);
		}
	}
	Extracted.Sort([this](int32 A, int32 B) { return Racers[A].FinishTime < Racers[B].FinishTime; });
	for (int32 K = 0; K < Extracted.Num(); ++K)
	{
		Racers[Extracted[K]].Reward = EXMeta::PlaceReward(K + 1) + EXMeta::ExtractedBonus;
	}
	// The pool in serpentine by value: the first extractor takes the most valuable piece, the second the next...; the
	// order turns round every round. The pieces run out, the sharing stops.
	Loot.Sort([](const FEXItem& A, const FEXItem& B) { return A.Value > B.Value; });
	const int32 Count = Extracted.Num();
	for (int32 K = 0; K < Loot.Num() && Count > 0; ++K)
	{
		const int32 Round = K / Count;
		const int32 Turn = Round % 2 == 0 ? K % Count : Count - 1 - K % Count;
		Racers[Extracted[Turn]].Won.Add(Loot[K]);
	}

	// The player's profile: not in the automated test.
	const int32 MeIndex = Racers.IndexOfByPredicate([](const FEXRacer& Racer) { return Racer.bPlayer; });
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
		for (const FEXItem& Item : Me.Modules)
		{
			if (Item.IsValid() && Loot.ContainsByPredicate([&Item](const FEXItem& L) { return L.Serial == Item.Serial; }))
			{
				PlayerNews.Add(FString::Printf(TEXT("Perdeste: %s"), *EXMeta::ItemLabel(Item)));
				Profile->RemoveItem(Item.Serial);
			}
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
			PlayerNews.Add(FString::Printf(TEXT("Primeira extra\u00E7\u00E3o: +%d STARDUST"), EXMeta::FirstExtractionBonus));
		}
		for (const FEXItem& Won : Me.Won)
		{
			// The piece changes hands with its rolls and value; it takes a serial of this profile.
			FEXItem Item = Won;
			Item.Serial = Profile->NextSerial++;
			Profile->Items.Add(Item);
			PlayerNews.Add(FString::Printf(TEXT("Esp\u00F3lio: %s (%s)"), *EXMeta::ItemLabel(Item), *EXMeta::RarityName(static_cast<EEXRarity>(Item.Rarity))));
		}
		++Profile->Extractions;
		Profile->BestPlace = Profile->BestPlace == 0 ? Place : FMath::Min(Profile->BestPlace, Place);
	}
	else if (bDestroyed)
	{
		PlayerNews.Insert(FString(TEXT("DESTRU\u00CDDA: as pe\u00E7as perdidas foram para quem extraiu")), 0);
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
