#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "EXGameMode.generated.h"

/** Flight test mode: builds the test arena and spawns the hover craft at its start line. */
UCLASS()
class EXTRACTINGSTARDUST_API AEXGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AEXGameMode();

	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;
	virtual AActor* ChoosePlayerStart_Implementation(AController* Player) override;
	/** The graphics profile: the race's, or the showroom's (menu and hangar: one craft on screen, so all at full quality). */
	static void ApplyGraphics(UWorld* World, bool bShowroom);

private:
	UPROPERTY(Transient)
	TObjectPtr<AActor> ArenaPlayerStart;
};
