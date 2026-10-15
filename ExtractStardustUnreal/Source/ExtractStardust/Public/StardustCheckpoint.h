#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "StardustCheckpoint.generated.h"

class AStardustRaceDirector;
class UBoxComponent;

UCLASS(Blueprintable)
class EXTRACTSTARDUST_API AStardustCheckpoint : public AActor
{
	GENERATED_BODY()

public:
	AStardustCheckpoint();

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Checkpoint")
	TObjectPtr<UBoxComponent> Trigger;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Checkpoint", meta=(ClampMin="0"))
	int32 CheckpointIndex = 0;

	UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category="Checkpoint")
	TObjectPtr<AStardustRaceDirector> RaceDirector;

private:
	UFUNCTION()
	void OnOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComponent, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
};
