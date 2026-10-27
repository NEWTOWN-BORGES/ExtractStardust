#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXGuideArrow.generated.h"

class UMaterialInstanceDynamic;
class UStaticMeshComponent;

/**
 * The guide arrow in 3D (player, 2026-10-27: "a seta em 3D, tipo a do Need for Speed"): a flat glowing arrow floating
 * over the player's craft, turning to point along the race line 150 m ahead (or back to a missed checkpoint), green
 * when the nose is on it, yellow, orange, red the wrong way. AEXHud points it every frame; it hides itself when it is
 * not pointed (menu, hangar, results). No collision, no shadow.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXGuideArrow : public AActor
{
	GENERATED_BODY()

public:
	AEXGuideArrow();
	virtual void Tick(float DeltaSeconds) override;

	/** The craft's place (cm) and heading, the target on the ground (m), the colour. */
	void Point(const FVector& CraftLocation, const FVector2D& Heading, const FVector2D& TargetM, const FLinearColor& Colour);

private:
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Shaft;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> HeadL;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> HeadR;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Material;
	float LastPointTime = -100.0f;
	float Yaw = 0.0f;
	float Age = 0.0f;
	bool bHasYaw = false;
};
