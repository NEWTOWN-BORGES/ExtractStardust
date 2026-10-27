#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXExplosion.generated.h"

class UMaterialInstanceDynamic;
class UMaterialInterface;
class UPointLightComponent;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * A craft blowing up when its hull is gone (player, 2026-10-26: "uma explosão quando a nave bate e perde toda a vida").
 * Built from the same shapes and FX materials as the engine flames (no particle assets): a fireball in three layers
 * (white core, orange, red) that swells and fades, a flash of light, a shock ring along the ground, burning debris thrown
 * out and falling, sparks, and dark smoke that rises and spreads. Carried on by the craft's speed; gone after ~4.5 s.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXExplosion : public AActor
{
	GENERATED_BODY()

public:
	AEXExplosion();
	virtual void Tick(float DeltaSeconds) override;

	/** Starts it: the craft's velocity (cm/s) carries the blast on; Strength 0..1 scales it. */
	void Ignite(const FVector& CraftVelocityCmps, float Strength);

private:
	struct FBit
	{
		UStaticMeshComponent* Mesh = nullptr;
		UMaterialInstanceDynamic* Material = nullptr;
		FVector Velocity = FVector::ZeroVector;
		FRotator Spin = FRotator::ZeroRotator;
		float Life = 1.0f;
		float Size = 1.0f;
		float EndSize = 1.0f;
		float Intensity = 1.0f;
	};

	UStaticMeshComponent* MakeMesh(UStaticMesh* Mesh, UMaterialInterface* Material, UMaterialInstanceDynamic*& OutMaterial);

	UPROPERTY() TObjectPtr<UStaticMesh> SphereMesh;
	UPROPERTY() TObjectPtr<UStaticMesh> CubeMesh;
	UPROPERTY() TObjectPtr<UStaticMesh> CylinderMesh;
	UPROPERTY() TObjectPtr<UMaterialInterface> GlowMaterial;
	UPROPERTY() TObjectPtr<UMaterialInterface> DustMaterial;
	UPROPERTY() TObjectPtr<UPointLightComponent> Flash;

	TArray<FBit> Fireball, Ring, Debris, Sparks, Smoke;
	FVector Drift = FVector::ZeroVector;
	float Age = 0.0f;
	float Scale = 1.0f;
	bool bLit = false;
};
