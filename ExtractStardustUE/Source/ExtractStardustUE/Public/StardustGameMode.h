#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "StardustGameMode.generated.h"

class AStardustBotPawn;

UCLASS()
class EXTRACTSTARDUSTUE_API AStardustGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AStardustGameMode();
	void StartTestBots();

protected:
	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;

private:
	UPROPERTY(Transient)
	TArray<TObjectPtr<AStardustBotPawn>> TestBots;
};
