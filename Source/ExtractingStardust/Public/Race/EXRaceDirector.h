#pragma once

#include "CoreMinimal.h"
#include "Game/EXMeta.h"
#include "GameFramework/Actor.h"
#include "EXRaceDirector.generated.h"

class AEXHoverCraft;

/** The game modes (Docs/MODOS_DE_JOGO.md): alone against the clock, against 15 bots, or the hangar showroom. */
UENUM()
enum class EEXRaceMode : uint8
{
	Solo,
	Bots,
	Hangar
};

/** One craft in the race, for the standings and the HUD. */
USTRUCT()
struct FEXRacer
{
	GENERATED_BODY()

	UPROPERTY()
	TObjectPtr<AEXHoverCraft> Craft;

	FString Name;
	bool bPlayer = false;
	bool bFinished = false;
	bool bOut = false;
	float FinishTime = 0.0f;
	/** The modules carried, by EEXFamily (an empty item is the stock part): real pieces, for bots too. */
	TArray<FEXItem> Modules;
	/** The insured module (never lost). */
	int32 Insured = 0;
	/** Extraction result: 0 still racing, 1 EXTRACTED, 2 DESTROYED, 3 STRANDED. */
	uint8 State = 0;
	/** STARDUST earned at the end (the reward for the place and the EXTRACTED bonus). */
	int32 Reward = 0;
	/** What a destroyed craft lost to the pool (STARDUST value), and the pieces an extractor won from it. */
	int32 LostValue = 0;
	TArray<FEXItem> Won;
	/** Where it dropped out (m along the race line). */
	float OutAtM = 0.0f;
	/** Checkpoints passed (one every ~2.5 km of the race line). */
	int32 Checkpoint = 0;
	/** Bots still racing when the race ends get a finishing time from their pace (as in the Unity version). */
	bool bProjected = false;
};

/** The player's expedition for the results screen: victory (EXTRACTED) or defeat (DESTROYED / STRANDED), what it paid
 *  and what changed hands. Filled when the race ends. */
struct FEXRaceSummary
{
	bool bValid = false;
	/** 1 EXTRACTED, 2 DESTROYED, 3 STRANDED. */
	uint8 State = 0;
	int32 Place = 0, Field = 0;
	float Time = 0.0f, DistanceM = 0.0f;
	int32 PlaceReward = 0, ExtractBonus = 0, CheckpointReward = 0, FirstBonus = 0, Total = 0;
	int32 Checkpoints = 0, CheckpointCount = 0;
	/** Pieces won from the pool, pieces lost to it, the insured module kept. */
	TArray<FEXItem> Won, Lost;
	FEXItem Saved;
	int32 PoolValue = 0;
};

/**
 * Runs a race from A to B on a map with a race line (spline tagged EXRoute): the grid (3 rows of 6 at the start of
 * the line), the countdown, the modules and quick slots from the hangar on the player's craft and real rolled modules on
 * the 15 bots of the Bots mode, eliminations, the finish at the end of the line, the standings (the survivors by
 * finishing time, then the ones left on the way by how far they got) and the extraction: rewards by place, the pieces
 * the destroyed lose to the pool and the pool shared by the extractors. Also manages the start menu and the hangar mode.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXRaceDirector : public AActor
{
	GENERATED_BODY()

public:
	AEXRaceDirector();

	virtual void Tick(float DeltaSeconds) override;

	void Configure(EEXRaceMode InMode, int32 InBots) { Mode = InMode; BotCount = InBots; }
	/** Start on the menu (the game opened without a mode): SOLO / PELOTÃO 15 / HANGAR / SAIR. */
	void OpenMenu() { bMenu = true; }
	void StartMenuChoice(int32 Choice);
	/** The mouse over a menu line highlights it. */
	void HoverMenuChoice(int32 Choice);
	/** From the hangar: start the expedition (the Bots mode unless the menu picked Solo). */
	void LaunchExpedition();
	/** The mode the hangar's launch button starts. */
	EEXRaceMode GetLaunchMode() const { return LastRaceMode; }
	/** The value of the pool (the real pieces lost by the destroyed, shared by the extractors), known at the end. */
	int32 GetPool() const { return Pool; }
	/** What happened to the player's things at the end (reward, pieces won and lost), for the results. */
	const TArray<FString>& GetPlayerNews() const { return PlayerNews; }
	bool IsInMenu() const { return bMenu; }
	/** The highlighted menu line: 0 solo, 1 bots, 2 hangar, 3 quit. */
	int32 GetMenuChoice() const { return MenuChoice; }
	/** From the player's craft: -1 up, +1 down, 0 confirm. */
	void MenuInput(int32 Step);

	EEXRaceMode GetMode() const { return Mode; }
	bool IsReady() const { return bReady; }
	/** Seconds left before the start (> 0 during the countdown). */
	float GetCountdown() const { return Countdown; }
	float GetRaceTime() const { return RaceTime; }
	bool IsOver() const { return bOver; }
	/** The player is past the line (finished or out) and the results are still to come. */
	bool IsPlayerDone() const { return PlayerDoneTime >= 0.0f; }
	float GetPlayerDoneTime() const { return PlayerDoneTime; }
	float GetRouteLengthM() const { return RouteLengthM; }
	/** Checkpoints along the line (every ~2.5 km) and how many the player has passed; the race time of the last one. */
	int32 GetCheckpointCount() const { return CheckpointCount; }
	int32 GetPlayerCheckpoint() const { return PlayerCheckpoint; }
	float GetLastCheckpointTime() const { return LastCheckpointTime; }
	/** STARDUST each checkpoint is worth on extraction. */
	static int32 GetCheckpointPrize();
	/** The player's expedition, for the results screen (valid once the race is over). */
	const FEXRaceSummary& GetSummary() const { return Summary; }
	/** Racers in race order (index 0 leads); refreshed every frame. */
	const TArray<FEXRacer>& GetStandings() const { return Standings; }
	/** The player's place (1-based) among all racers. */
	int32 GetPlayerPlace() const { return PlayerPlace; }
	/** Recent messages ("VORTEX #7 ficou pelo caminho"), newest last, with the race time they were posted. */
	const TArray<TPair<float, FString>>& GetFeed() const { return Feed; }

private:
	void Setup();
	void PlaceOnGrid(AEXHoverCraft* Craft, int32 Slot);
	void Post(const FString& Message);
	void UpdateStandings();
	void Finish();
	void SettleExtraction();
	void ReturnToMenu();

	EEXRaceMode Mode = EEXRaceMode::Solo;
	int32 BotCount = 15;
	bool bReady = false, bStarted = false, bOver = false, bTest = false, bMenu = false;
	int32 MenuChoice = 1;
	int32 Pool = 0;
	/** Serials for the bots' pieces (far from the player's). */
	int32 BotSerial = 1000000;
	FRandomStream LootRandom;
	TArray<FString> PlayerNews;
	EEXRaceMode LastRaceMode = EEXRaceMode::Bots;
	float Countdown = 4.0f, RaceTime = 0.0f, RouteLengthM = 0.0f, PlayerDoneTime = -1.0f, OverTime = 0.0f;
	int32 PlayerPlace = 1;
	int32 CheckpointCount = 1, PlayerCheckpoint = 0;
	float LastCheckpointTime = -100.0f;
	FEXRaceSummary Summary;
	TArray<FVector2D> Route;

	UPROPERTY()
	TArray<FEXRacer> Racers;

	UPROPERTY()
	TArray<FEXRacer> Standings;

	TArray<TPair<float, FString>> Feed;
};
