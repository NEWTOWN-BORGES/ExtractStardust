#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "StardustGameMode.generated.h"

UCLASS()
class EXTRACTSTARDUSTUE_API AStardustGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AStardustGameMode();

protected:
	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;
};
