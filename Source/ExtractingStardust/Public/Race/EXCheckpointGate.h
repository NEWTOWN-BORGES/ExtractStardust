#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXCheckpointGate.generated.h"

class UMaterialInstanceDynamic;
class UStaticMeshComponent;

/**
 * A checkpoint gate (player, 2026-10-27: "deixa o checkpoint visível no horizonte quando estivermos a aproximar; os
 * checkpoints são obrigatórios para evitar batotas"; then "portões sólidos sem ser de luz"): two tall painted pylons
 * either side of the floor and a bar across their tops, seen from far away. Only the player's next gate shows (cyan);
 * a passed one turns green and goes; a missed one turns red until the player flies back through it.
 * AEXRaceDirector places them (at the apex of a bend or on the straight between two bends) and says which is which.
 * No collision.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXCheckpointGate : public AActor
{
	GENERATED_BODY()

public:
	AEXCheckpointGate();
	virtual void Tick(float DeltaSeconds) override;

	/** The feet of the two pylons (on the ground), in world space. */
	void Setup(const FVector& Left, const FVector& Right);
	/** 0 hidden, 1 the next one, 2 just passed, 3 missed. */
	void SetState(int32 InState);

private:
	UPROPERTY() TObjectPtr<UStaticMeshComponent> PylonL;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> PylonR;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Bar;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> BeamL;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> BeamR;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FrameMaterial;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> BeamMaterial;
	int32 State = 0;
	float Age = 0.0f;
};
