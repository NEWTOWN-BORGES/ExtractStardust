#pragma once

#include "CoreMinimal.h"
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
	/** STARDUST value of the cargo carried (lost to the pool if destroyed). */
	int32 CargoValue = 0;
	/** Extraction result: 0 still racing, 1 EXTRACTED, 2 DESTROYED, 3 STRANDED. */
	uint8 State = 0;
	/** STARDUST earned at the end (bonus + share of the pool). */
	int32 Reward = 0;
	/** Where it dropped out (m along the race line). */
	float OutAtM = 0.0f;
};

/**
 * Runs a race from A to B on a map with a race line (spline tagged EXRoute): the grid (3 rows of 6 at the start of
 * the line), the countdown, lives and the medical kit on every craft (the kit only for the player), the 15 bots in the
 * Bots mode, eliminations, the finish at the end of the line and the standings: the survivors by finishing time, then
 * the ones left on the way by how far they got. Also manages the start menu and the Hangar showroom mode.
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
	/** The pool of lost cargo shared by the extractors (known at the end). */
	int32 GetPool() const { return Pool; }
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
	float GetRouteLengthM() const { return RouteLengthM; }
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
	int32 StartRepair = 0, StartSurge = 0, StartShield = 0;
	EEXRaceMode LastRaceMode = EEXRaceMode::Bots;
	float Countdown = 4.0f, RaceTime = 0.0f, RouteLengthM = 0.0f, PlayerDoneTime = -1.0f, OverTime = 0.0f;
	int32 PlayerPlace = 1;
	TArray<FVector2D> Route;

	UPROPERTY()
	TArray<FEXRacer> Racers;

	UPROPERTY()
	TArray<FEXRacer> Standings;

	TArray<TPair<float, FString>> Feed;
};
