#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "StardustGameMode.generated.h"

class AStardustBotPawn;
class APlayerStart;

UCLASS()
class EXTRACTSTARDUSTUE_API AStardustGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AStardustGameMode();
	void StartTestBots();

protected:
	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;
	virtual AActor* ChoosePlayerStart_Implementation(AController* Player) override;

private:
	UPROPERTY(Transient)
	TObjectPtr<APlayerStart> CoursePlayerStart;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AStardustBotPawn>> TestBots;
};
