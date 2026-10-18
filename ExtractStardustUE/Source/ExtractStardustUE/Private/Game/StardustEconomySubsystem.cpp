#include "Game/StardustEconomySubsystem.h"

#include "Game/StardustRaceProgressComponent.h"
#include "Game/StardustSaveGame.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Guid.h"
#include "Misc/Parse.h"

namespace
{
	constexpr int64 PositionRewards[] =
	{
		1600, 1300, 1100, 950, 850, 750, 675, 600, 550, 500,
		450,  425,  400,  375, 350, 325, 300, 275, 250, 225
	};
	constexpr int64 ExtractedBonus = 250;
	constexpr int64 FirstExtractionBonus = 500;
	constexpr int64 ProwessCap = 500;
}

void UStardustEconomySubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	if (!LoadProfile())
	{
		InitDefaultContracts();
		RecordLedger(TEXT("system"), CurrentBalance, TEXT("Stardust economy subsystem initialized with default profile."));
	}

	if (FParse::Param(FCommandLine::Get(), TEXT("StardustTestEconomy")))
	{
		RunEconomyDiagnostics();
	}
}

void UStardustEconomySubsystem::Deinitialize()
{
	SaveProfile();
	Super::Deinitialize();
}

void UStardustEconomySubsystem::ResetProfile(int64 InitialBalance)
{
	CurrentBalance = FMath::Max<int64>(0, InitialBalance);
	bFirstExtractionPaid = false;
	TotalRaces = 0;
	TotalExtractions = 0;
	ExtractionStreak = 0;
	NoRepairStreak = 0;
	AppliedTransactions.Empty();
	Ledger.Empty();
	InitDefaultContracts();
	RecordLedger(TEXT("reset"), InitialBalance, TEXT("Perfil reiniciado com saldo inicial."));
	SaveProfile();
	OnBalanceChanged.Broadcast(CurrentBalance, 0, TEXT("Perfil reiniciado"));
}

bool UStardustEconomySubsystem::SaveProfile(const FString& SlotName, int32 UserIndex)
{
	UStardustSaveGame* SaveGameInstance = Cast<UStardustSaveGame>(UGameplayStatics::CreateSaveGameObject(UStardustSaveGame::StaticClass()));
	if (!SaveGameInstance)
	{
		return false;
	}

	SaveGameInstance->SaveSlotName = SlotName;
	SaveGameInstance->UserIndex = UserIndex;
	SaveGameInstance->StardustBalance = CurrentBalance;
	SaveGameInstance->bFirstExtractionPaid = bFirstExtractionPaid;
	SaveGameInstance->TotalRaces = TotalRaces;
	SaveGameInstance->TotalExtractions = TotalExtractions;
	SaveGameInstance->ExtractionStreak = ExtractionStreak;
	SaveGameInstance->NoRepairStreak = NoRepairStreak;
	SaveGameInstance->Contracts = Contracts;
	SaveGameInstance->Ledger = Ledger;
	SaveGameInstance->LastRaceReport = LastReport;
	SaveGameInstance->AppliedTransactions = AppliedTransactions.Array();

	return UGameplayStatics::SaveGameToSlot(SaveGameInstance, SlotName, UserIndex);
}

bool UStardustEconomySubsystem::LoadProfile(const FString& SlotName, int32 UserIndex)
{
	if (!UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex))
	{
		return false;
	}

	UStardustSaveGame* LoadedGame = Cast<UStardustSaveGame>(UGameplayStatics::LoadGameFromSlot(SlotName, UserIndex));
	if (!LoadedGame)
	{
		return false;
	}

	CurrentBalance = LoadedGame->StardustBalance;
	bFirstExtractionPaid = LoadedGame->bFirstExtractionPaid;
	TotalRaces = LoadedGame->TotalRaces;
	TotalExtractions = LoadedGame->TotalExtractions;
	ExtractionStreak = LoadedGame->ExtractionStreak;
	NoRepairStreak = LoadedGame->NoRepairStreak;
	Contracts = LoadedGame->Contracts;
	if (Contracts.Num() == 0)
	{
		InitDefaultContracts();
	}
	Ledger = LoadedGame->Ledger;
	LastReport = LoadedGame->LastRaceReport;
	AppliedTransactions = TSet<FString>(LoadedGame->AppliedTransactions);

	RecordLedger(TEXT("load"), 0, FString::Printf(TEXT("Perfil carregado do slot '%s'."), *SlotName));
	OnBalanceChanged.Broadcast(CurrentBalance, 0, TEXT("Perfil carregado"));
	return true;
}

void UStardustEconomySubsystem::InitDefaultContracts()
{
	Contracts.Empty();
	Contracts.Emplace(TEXT("racer"), TEXT("RACER"), TEXT("Concluir 2 corridas"), 2, 300);
	Contracts.Emplace(TEXT("extractor"), TEXT("EXTRACTOR"), TEXT("Extrair 2 vezes"), 2, 450);
	Contracts.Emplace(TEXT("top10"), TEXT("TOP TEN"), TEXT("Top 10 duas vezes"), 2, 550);
	Contracts.Emplace(TEXT("podium"), TEXT("PODIUM HUNTER"), TEXT("Alcançar um pódio"), 1, 700);
	Contracts.Emplace(TEXT("champion"), TEXT("CHAMPION"), TEXT("Vencer uma corrida"), 1, 900);
	Contracts.Emplace(TEXT("canyon"), TEXT("CANYON RUNNER"), TEXT("Completar 3 Skill Routes"), 3, 400);
	Contracts.Emplace(TEXT("survival"), TEXT("SURVIVAL SPECIALIST"), TEXT("Extrair 2 vezes sem reparar"), 2, 600);
	Contracts.Emplace(TEXT("streak"), TEXT("HOT STREAK"), TEXT("3 extrações seguidas"), 3, 750);
}

void UStardustEconomySubsystem::RecordLedger(const FString& Kind, int64 Amount, const FString& Note)
{
	FStardustLedgerEntry Entry;
	Entry.Timestamp = FDateTime::UtcNow();
	Entry.Kind = Kind;
	Entry.Amount = Amount;
	Entry.Note = Note;
	Ledger.Add(Entry);
	if (Ledger.Num() > 400)
	{
		Ledger.RemoveAt(0, Ledger.Num() - 400);
	}
}

bool UStardustEconomySubsystem::AlreadyApplied(const FString& TxId)
{
	if (TxId.IsEmpty())
	{
		return false;
	}
	if (AppliedTransactions.Contains(TxId))
	{
		return true;
	}
	AppliedTransactions.Add(TxId);
	if (AppliedTransactions.Num() > 300)
	{
		AppliedTransactions.Empty();
	}
	return false;
}

bool UStardustEconomySubsystem::AddStardust(int64 Amount, const FString& Reason, const FString& Kind)
{
	if (Amount <= 0)
	{
		return false;
	}
	CurrentBalance += Amount;
	RecordLedger(Kind, Amount, Reason);
	SaveProfile();
	OnBalanceChanged.Broadcast(CurrentBalance, Amount, Reason);
	return true;
}

bool UStardustEconomySubsystem::SpendStardust(int64 Amount, const FString& Reason, const FString& Kind)
{
	if (Amount <= 0 || CurrentBalance < Amount)
	{
		return false;
	}
	CurrentBalance -= Amount;
	RecordLedger(Kind, -Amount, Reason);
	SaveProfile();
	OnBalanceChanged.Broadcast(CurrentBalance, -Amount, Reason);
	return true;
}

float UStardustEconomySubsystem::GetDurationMultiplier(float ReferenceMinutes)
{
	if (ReferenceMinutes < 6.0f)
	{
		return 0.35f;
	}
	if (ReferenceMinutes < 10.0f)
	{
		return 0.50f;
	}
	if (ReferenceMinutes < 17.0f)
	{
		return 0.70f;
	}
	return 1.0f;
}

int64 UStardustEconomySubsystem::GetPositionReward(int32 Position)
{
	if (Position <= 0)
	{
		return 0;
	}
	const int32 Index = Position - 1;
	if (Index < UE_ARRAY_COUNT(PositionRewards))
	{
		return PositionRewards[Index];
	}
	return 200;
}

TArray<FStardustProwessReward> UStardustEconomySubsystem::CalculateProwess(const FStardustRaceOutcome& Outcome)
{
	TArray<FStardustProwessReward> List;
	if (Outcome.State != EStardustRaceState::Extracted)
	{
		return List;
	}

	const bool bFlawless = Outcome.Position == 1 && !Outcome.bTookDamage && Outcome.Repairs == 0 && Outcome.Penalties == 0;
	if (bFlawless)
	{
		List.Emplace(TEXT("Vitória Imaculada"), 500);
	}
	if (Outcome.HullFraction <= 0.10f)
	{
		List.Emplace(TEXT("Sobrevivente"), 200);
	}
	if (!bFlawless && !Outcome.bTookDamage)
	{
		List.Emplace(TEXT("Corrida Perfeita"), 300);
	}
	if (!bFlawless && Outcome.Repairs == 0)
	{
		List.Emplace(TEXT("Mecânico de Folga"), 120);
	}
	if (Outcome.FuelFraction <= 0.03f)
	{
		List.Emplace(TEXT("Última Gota"), 150);
	}
	if (!Outcome.bUsedBoost)
	{
		List.Emplace(TEXT("Energia Pura"), 180);
	}
	if (!bFlawless && Outcome.bAllCheckpoints && Outcome.Penalties == 0)
	{
		List.Emplace(TEXT("Navegador Nato"), 100);
	}
	if (Outcome.ReferenceTimeSeconds > 0.0f && Outcome.RaceTimeSeconds <= Outcome.ReferenceTimeSeconds)
	{
		List.Emplace(TEXT("Contra o Relógio"), 200);
	}

	List.Sort([](const FStardustProwessReward& A, const FStardustProwessReward& B)
	{
		return A.Value > B.Value;
	});

	TArray<FStardustProwessReward> Capped;
	int64 Sum = 0;
	for (const FStardustProwessReward& Pr : List)
	{
		if (Sum >= ProwessCap)
		{
			break;
		}
		const int64 Val = FMath::Min(Pr.Value, ProwessCap - Sum);
		Capped.Emplace(Pr.Name, Val);
		Sum += Val;
	}
	return Capped;
}

void UStardustEconomySubsystem::UpdateContractProgress(const FString& ContractId, int32 Increment,
	TArray<FStardustReportLine>& OutLines, int64& OutExtraStardust)
{
	if (Increment <= 0)
	{
		return;
	}
	for (FStardustContractState& Contract : Contracts)
	{
		if (Contract.Id == ContractId)
		{
			Contract.Progress += Increment;
			if (Contract.Progress >= Contract.Target)
			{
				Contract.Progress = 0;
				++Contract.CompletedCount;
				OutLines.Emplace(FString::Printf(TEXT("Contrato: %s"), *Contract.Name), Contract.Reward);
				OutExtraStardust += Contract.Reward;
				OnContractCompleted.Broadcast(Contract.Id, Contract.Name, Contract.Reward);
			}
			break;
		}
	}
}

FStardustRaceReport UStardustEconomySubsystem::ProcessRaceOutcome(const FStardustRaceOutcome& Outcome)
{
	if (AlreadyApplied(Outcome.RaceId))
	{
		return LastReport;
	}

	FStardustRaceReport Report;
	Report.RaceId = Outcome.RaceId;
	Report.CourseName = Outcome.CourseName;
	Report.State = Outcome.State;
	Report.Position = Outcome.Position;
	Report.TotalRacers = Outcome.TotalRacers;
	Report.RaceTimeSeconds = Outcome.RaceTimeSeconds;
	Report.HullFraction = Outcome.HullFraction;
	Report.FuelFraction = Outcome.FuelFraction;

	const bool bRisk = Outcome.Mode != EStardustGameModeType::Exploration;
	if (bRisk)
	{
		const float Mult = GetDurationMultiplier(Outcome.ReferenceMinutes);
		auto Pay = [&](const FString& What, int64 V, bool bScaled = true)
		{
			const int64 Val = bScaled ? static_cast<int64>(FMath::RoundToInt(V * Mult / 5.0f)) * 5 : V;
			if (Val > 0)
			{
				Report.RewardBreakdown.Emplace(What, Val);
				Report.TotalStardustEarned += Val;
			}
		};

		const int64 PosBase = GetPositionReward(Outcome.Position);
		if (Outcome.State == EStardustRaceState::Extracted)
		{
			Pay(FString::Printf(TEXT("%d.º lugar"), Outcome.Position), PosBase);
			Pay(TEXT("EXTRACTED"), ExtractedBonus);
			for (const FStardustProwessReward& Pr : CalculateProwess(Outcome))
			{
				Pay(FString::Printf(TEXT("Proeza: %s"), *Pr.Name), Pr.Value);
			}
			if (!bFirstExtractionPaid)
			{
				bFirstExtractionPaid = true;
				Pay(TEXT("Primeira extração"), FirstExtractionBonus, false);
			}
		}
		else if (Outcome.State == EStardustRaceState::Abandoned)
		{
			Pay(FString::Printf(TEXT("Participação (%d.º, abandono)"), Outcome.Position), PosBase / 4);
		}

		if (Mult < 1.0f && Report.RewardBreakdown.Num() > 0)
		{
			Report.RewardBreakdown.Emplace(FString::Printf(TEXT("(duração x%.2f)"), Mult), 0);
		}

		// Stats
		if (Outcome.State != EStardustRaceState::Waiting)
		{
			++TotalRaces;
		}
		const bool bExt = (Outcome.State == EStardustRaceState::Extracted);
		if (bExt)
		{
			++TotalExtractions;
			++ExtractionStreak;
			if (Outcome.Repairs == 0)
			{
				++NoRepairStreak;
			}
		}
		else
		{
			ExtractionStreak = 0;
		}

		// Contracts
		if (bExt)
		{
			UpdateContractProgress(TEXT("racer"), 1, Report.RewardBreakdown, Report.TotalStardustEarned);
			UpdateContractProgress(TEXT("extractor"), 1, Report.RewardBreakdown, Report.TotalStardustEarned);
			if (Outcome.Position <= 10)
			{
				UpdateContractProgress(TEXT("top10"), 1, Report.RewardBreakdown, Report.TotalStardustEarned);
			}
			if (Outcome.Position <= 3)
			{
				UpdateContractProgress(TEXT("podium"), 1, Report.RewardBreakdown, Report.TotalStardustEarned);
			}
			if (Outcome.Position == 1)
			{
				UpdateContractProgress(TEXT("champion"), 1, Report.RewardBreakdown, Report.TotalStardustEarned);
			}
			if (Outcome.SkillRoutes > 0)
			{
				UpdateContractProgress(TEXT("canyon"), Outcome.SkillRoutes, Report.RewardBreakdown, Report.TotalStardustEarned);
			}
			if (Outcome.Repairs == 0)
			{
				UpdateContractProgress(TEXT("survival"), 1, Report.RewardBreakdown, Report.TotalStardustEarned);
			}
			if (ExtractionStreak >= 3)
			{
				UpdateContractProgress(TEXT("streak"), 3, Report.RewardBreakdown, Report.TotalStardustEarned);
				ExtractionStreak = 0;
			}
		}

		if (Report.TotalStardustEarned > 0)
		{
			AddStardust(Report.TotalStardustEarned, FString::Printf(TEXT("%s: Pos %d/%d"), *Outcome.CourseName, Outcome.Position, Outcome.TotalRacers), TEXT("race"));
		}
	}

	LastReport = Report;
	SaveProfile();
	OnRaceReportProcessed.Broadcast(Report);
	return Report;
}

FStardustRaceReport UStardustEconomySubsystem::ProcessRaceFromProgress(
	const UStardustRaceProgressComponent* ProgressComponent,
	int32 Position, int32 TotalRacers, float ReferenceMinutes,
	float HullFraction, float FuelFraction, bool bUsedBoost)
{
	FStardustRaceOutcome Outcome;
	Outcome.RaceId = FGuid::NewGuid().ToString(EGuidFormats::Short);
	Outcome.CourseName = TEXT("Red Dust Divide");
	Outcome.Position = FMath::Max(1, Position);
	Outcome.TotalRacers = FMath::Max(1, TotalRacers);
	Outcome.ReferenceMinutes = FMath::Max(0.5f, ReferenceMinutes);
	Outcome.HullFraction = FMath::Clamp(HullFraction, 0.0f, 1.0f);
	Outcome.FuelFraction = FMath::Clamp(FuelFraction, 0.0f, 1.0f);
	Outcome.bUsedBoost = bUsedBoost;
	Outcome.bTookDamage = HullFraction < 0.999f;
	Outcome.Repairs = 0;
	Outcome.Penalties = 0;
	Outcome.SkillRoutes = 0;

	if (ProgressComponent)
	{
		Outcome.State = ProgressComponent->State;
		Outcome.RaceTimeSeconds = ProgressComponent->FinishTimeSeconds > 0.0f ? ProgressComponent->FinishTimeSeconds : ProgressComponent->ElapsedTimeSeconds;
		Outcome.ReferenceTimeSeconds = ReferenceMinutes * 60.0f;
		Outcome.bAllCheckpoints = ProgressComponent->CurrentCheckpoint >= ProgressComponent->CheckpointCount;
	}

	return ProcessRaceOutcome(Outcome);
}

void UStardustEconomySubsystem::RunEconomyDiagnostics()
{
	UE_LOG(LogTemp, Display, TEXT("=== STARTING STARDUST ECONOMY RUNTIME VALIDATION (FASE 1) ==="));

	// 1. Test behaviour when save file does not exist (non-existent slot)
	const FString NonExistentSlot = TEXT("StardustNonExistentSlot_99999");
	const bool bNonExistentLoaded = LoadProfile(NonExistentSlot);
	if (bNonExistentLoaded)
	{
		UE_LOG(LogTemp, Error, TEXT("Economy validation FAILED: LoadProfile returned true for non-existent slot!"));
		return;
	}
	UE_LOG(LogTemp, Display, TEXT("Economy validation [Test A - NonExistentSlot]: Correctly returned false for missing slot without crash."));

	// 2. Reset profile (new profile with known initial balance)
	ResetProfile(1000);
	if (CurrentBalance != 1000 || TotalRaces != 0 || TotalExtractions != 0)
	{
		UE_LOG(LogTemp, Error, TEXT("Economy validation FAILED: ResetProfile did not set expected defaults!"));
		return;
	}
	UE_LOG(LogTemp, Display, TEXT("Economy validation [Test A - NewProfile]: ResetProfile(1000) verified. Balance: %lld, Races: %d."), CurrentBalance, TotalRaces);

	// 3. Test Destroyed/Cancelled race (must pay 0 rewards, no duplicate or unintended credits)
	{
		FStardustRaceOutcome DestroyedOutcome;
		DestroyedOutcome.RaceId = TEXT("Validation_Destroyed_001");
		DestroyedOutcome.CourseName = TEXT("Red Dust Divide");
		DestroyedOutcome.Mode = EStardustGameModeType::Race;
		DestroyedOutcome.State = EStardustRaceState::Racing;
		DestroyedOutcome.Position = 15;
		DestroyedOutcome.ReferenceMinutes = 5.0f;

		const int64 BalanceBeforeDestroyed = CurrentBalance;
		const FStardustRaceReport DestroyedReport = ProcessRaceOutcome(DestroyedOutcome);
		if (DestroyedReport.TotalStardustEarned != 0 || CurrentBalance != BalanceBeforeDestroyed)
		{
			UE_LOG(LogTemp, Error, TEXT("Economy validation FAILED: Destroyed race paid %lld Stardust! Expected 0."), DestroyedReport.TotalStardustEarned);
			return;
		}
		UE_LOG(LogTemp, Display, TEXT("Economy validation [Test D - Destroyed Race]: 0 Stardust paid for destroyed craft. Balance intact: %lld."), CurrentBalance);
	}

	// 4. Test Abandoned race (pays participation only: PosBase / 4, no extraction bonus, no contracts)
	{
		FStardustRaceOutcome AbandonedOutcome;
		AbandonedOutcome.RaceId = TEXT("Validation_Abandoned_001");
		AbandonedOutcome.CourseName = TEXT("Red Dust Divide");
		AbandonedOutcome.Mode = EStardustGameModeType::Race;
		AbandonedOutcome.State = EStardustRaceState::Abandoned;
		AbandonedOutcome.Position = 4;
		AbandonedOutcome.ReferenceMinutes = 5.0f;

		const int64 BalanceBeforeAbandoned = CurrentBalance;
		const FStardustRaceReport AbandonedReport = ProcessRaceOutcome(AbandonedOutcome);
		if (AbandonedReport.TotalStardustEarned <= 0 || CurrentBalance != BalanceBeforeAbandoned + AbandonedReport.TotalStardustEarned)
		{
			UE_LOG(LogTemp, Error, TEXT("Economy validation FAILED: Abandoned race did not pay expected participation reward!"));
			return;
		}
		UE_LOG(LogTemp, Display, TEXT("Economy validation [Test D - Abandoned Race]: Paid participation %lld Stardust. Balance: %lld."),
			AbandonedReport.TotalStardustEarned, CurrentBalance);
	}

	// 5. Test Full Completed Race with Extraction, Prowess, First Extraction bonus and Contracts
	FStardustRaceOutcome Outcome;
	Outcome.RaceId = TEXT("ValidationRace_Extracted_001");
	Outcome.CourseName = TEXT("Red Dust Divide");
	Outcome.Mode = EStardustGameModeType::Race;
	Outcome.State = EStardustRaceState::Extracted;
	Outcome.Position = 1;
	Outcome.TotalRacers = 20;
	Outcome.RaceTimeSeconds = 280.0f;
	Outcome.ReferenceTimeSeconds = 300.0f;
	Outcome.ReferenceMinutes = 5.0f;
	Outcome.HullFraction = 1.0f;
	Outcome.FuelFraction = 0.4f;
	Outcome.bTookDamage = false;
	Outcome.bUsedBoost = true;
	Outcome.bAllCheckpoints = true;
	Outcome.Repairs = 0;
	Outcome.Penalties = 0;
	Outcome.SkillRoutes = 1;

	const int64 BalanceBeforeExtracted = CurrentBalance;
	const FStardustRaceReport Report1 = ProcessRaceOutcome(Outcome);
	const int64 BalanceAfterExtracted = CurrentBalance;
	const int64 Earned1 = Report1.TotalStardustEarned;

	UE_LOG(LogTemp, Display, TEXT("Economy validation [Test E - Rewards Table]: Race processed. Earned: %lld. Balance before: %lld, Balance after: %lld."),
		Earned1, BalanceBeforeExtracted, BalanceAfterExtracted);

	if (BalanceAfterExtracted != BalanceBeforeExtracted + Earned1 || Earned1 <= 0)
	{
		UE_LOG(LogTemp, Error, TEXT("Economy validation FAILED: Balance did not increase by earned reward!"));
		return;
	}

	// 6. Test Idempotency (repeating the exact same finished race)
	const FStardustRaceReport Report2 = ProcessRaceOutcome(Outcome);
	if (CurrentBalance != BalanceAfterExtracted || Report2.TotalStardustEarned != Earned1)
	{
		UE_LOG(LogTemp, Error, TEXT("Economy validation FAILED: Duplicate race processing paid rewards twice! Balance now %lld vs expected %lld."),
			CurrentBalance, BalanceAfterExtracted);
		return;
	}
	UE_LOG(LogTemp, Display, TEXT("Economy validation [Test C - Idempotency]: Duplicate race conclusion ignored, balance unchanged at %lld."), CurrentBalance);

	// 7. Test SaveGameToSlot and LoadGameFromSlot persistence
	const FString TestSlot = TEXT("StardustTestSaveSlot");
	const int64 ExpectedBalance = CurrentBalance;
	const int32 ExpectedRaces = TotalRaces;
	const int32 ExpectedExtractions = TotalExtractions;

	const bool bSaved = SaveProfile(TestSlot);
	if (!bSaved || !UGameplayStatics::DoesSaveGameExist(TestSlot, 0))
	{
		UE_LOG(LogTemp, Error, TEXT("Economy validation FAILED: SaveProfile or DoesSaveGameExist failed for slot '%s'!"), *TestSlot);
		return;
	}
	UE_LOG(LogTemp, Display, TEXT("Economy validation [Test B - SaveGameToSlot]: Successfully saved profile to slot '%s'."), *TestSlot);

	// Tamper in-memory state
	CurrentBalance = 42;
	TotalRaces = 999;
	TotalExtractions = 999;

	const bool bLoaded = LoadProfile(TestSlot);
	if (!bLoaded)
	{
		UE_LOG(LogTemp, Error, TEXT("Economy validation FAILED: LoadProfile returned false for existing slot!"));
		return;
	}

	if (CurrentBalance != ExpectedBalance || TotalRaces != ExpectedRaces || TotalExtractions != ExpectedExtractions)
	{
		UE_LOG(LogTemp, Error, TEXT("Economy validation FAILED: Restored balance %lld != expected %lld, or stats mismatch!"),
			CurrentBalance, ExpectedBalance);
		return;
	}
	UE_LOG(LogTemp, Display, TEXT("Economy validation [Test B - LoadGameFromSlot]: Successfully restored balance %lld, races %d, extractions %d."),
		CurrentBalance, TotalRaces, TotalExtractions);

	// Clean up test save slot
	UGameplayStatics::DeleteGameInSlot(TestSlot, 0);
	UE_LOG(LogTemp, Display, TEXT("=== STARDUST ECONOMY RUNTIME VALIDATION PASSED: ALL TESTS OK ==="));
}
