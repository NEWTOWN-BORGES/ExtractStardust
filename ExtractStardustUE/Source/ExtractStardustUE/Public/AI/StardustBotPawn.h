#pragma once

#include "CoreMinimal.h"
#include "Vehicle/StardustHovercraftPawn.h"
#include "StardustBotPawn.generated.h"

class UStardustLineFollowerComponent;

UCLASS()
class EXTRACTSTARDUSTUE_API AStardustBotPawn : public AStardustHovercraftPawn
{
	GENERATED_BODY()

public:
	AStardustBotPawn();
	void StartRacing();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Racing AI")
	TObjectPtr<UStardustLineFollowerComponent> LineFollowerComponent;
};
