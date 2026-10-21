#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXRaceDirector.generated.h"

class AEXHoverCraft;

/** The two game modes (Docs/MODOS_DE_JOGO.md): alone against the clock, or against 15 bots. */
UENUM()
enum class EEXRaceMode : uint8
{
	Solo,
	Bots
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
	/** Where it dropped out (m along the race line). */
	float OutAtM = 0.0f;
};

/**
 * Runs a race from A to B on a map with a race line (spline tagged EXRoute): the grid (3 rows of 6 at the start of
 * the line), the countdown, lives and the medical kit on every craft (the kit only for the player), the 15 bots in the
 * Bots mode, eliminations, the finish at the end of the line and the standings: the survivors by finishing time, then
 * the ones left on the way by how far they got.
 * Spawned by AEXGameMode when the map URL has ?Mode=Solo or ?Mode=Bots (or the command line -EXMode=Solo / Bots).
 * With -EXRaceTest the player's craft drives itself too and the game quits after the results (log lines EXRACE).
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXRaceDirector : public AActor
{
	GENERATED_BODY()

public:
	AEXRaceDirector();

	virtual void Tick(float DeltaSeconds) override;

	void Configure(EEXRaceMode InMode, int32 InBots) { Mode = InMode; BotCount = InBots; }
	/** Start on the menu (the game opened without a mode): SOLO / CONTRA BOTS / VOO LIVRE. */
	void OpenMenu() { bMenu = true; }
	bool IsInMenu() const { return bMenu; }
	/** The highlighted menu line: 0 solo, 1 bots, 2 free flight. */
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

	EEXRaceMode Mode = EEXRaceMode::Solo;
	int32 BotCount = 15;
	bool bReady = false, bStarted = false, bOver = false, bTest = false, bMenu = false;
	int32 MenuChoice = 1;
	float Countdown = 4.0f, RaceTime = 0.0f, RouteLengthM = 0.0f, PlayerDoneTime = -1.0f, OverTime = 0.0f;
	int32 PlayerPlace = 1;
	TArray<FVector2D> Route;

	UPROPERTY()
	TArray<FEXRacer> Racers;

	UPROPERTY()
	TArray<FEXRacer> Standings;

	TArray<TPair<float, FString>> Feed;
};
