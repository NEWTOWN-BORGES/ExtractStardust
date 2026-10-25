#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "EXGameMode.generated.h"

class AEXHangarStage;
class AEXHoverCraft;
class APlayerController;
class UEXHangarMenuWidget;

/** Flight test mode: builds the test arena and spawns the hover craft at its start line. */
UCLASS()
class EXTRACTINGSTARDUST_API AEXGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AEXGameMode();

	virtual void Tick(float DeltaSeconds) override;
	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;
	virtual void PostLogin(APlayerController* NewPlayer) override;
	virtual AActor* ChoosePlayerStart_Implementation(AController* Player) override;

	void CycleHangarShip(int32 Direction);
	void StartFlightFromHangar();
	void StartSurvivalRaceFromHangar();
	void QuitFromHangar();
	bool IsSurvivalModeSelected() const { return bSurvivalModeSelected; }
	bool IsSurvivalRaceFinished() const { return bSurvivalRaceFinished; }
	bool DidPlayerSurvive() const { return bPlayerSurvived; }
	int32 GetSurvivalCountdownSeconds() const;
	int32 GetSurvivorCount() const { return SurvivalAliveCount; }
	float GetSurvivalElapsedSeconds() const { return SurvivalElapsedSeconds; }
	float GetPlayerHullPercent() const;

private:
	void OpenHangar(APlayerController* PlayerController);
	void CloseHangar();
	bool ShouldShowHangar() const;

	UPROPERTY(Transient)
	TObjectPtr<AActor> ArenaPlayerStart;

	UPROPERTY(Transient)
	TObjectPtr<AEXHangarStage> HangarStage;

	UPROPERTY(Transient)
	TObjectPtr<UEXHangarMenuWidget> HangarWidget;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AEXHoverCraft>> SurvivalRacers;

	UPROPERTY(Transient)
	TObjectPtr<AEXHoverCraft> SurvivalPlayer;

	bool bSurvivalModeSelected = false;
	bool bSurvivalRaceRunning = false;
	bool bSurvivalRaceFinished = false;
	bool bPlayerSurvived = false;
	int32 SurvivalAliveCount = 0;
	float SurvivalCountdownRemaining = 0.0f;
	float SurvivalElapsedSeconds = 0.0f;
};
