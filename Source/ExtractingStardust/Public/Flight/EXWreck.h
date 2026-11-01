#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXWreck.generated.h"

class UMaterialBillboardComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UPointLightComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UTexture2D;

/**
 * What is left of a ship blown up (player, 2026-11-01: "a carcaça das naves destruídas a alta velocidade a voar em frente
 * e a cair dando várias voltas, cambalhotas; os módulos podem voar carbonizados, são peças separadas; a física depende
 * de como a nave é destruída"). The hull and each module are separate charred pieces, each a solid box that flies,
 * spins and strikes the ground (and walls) at its corners: an impulse with a little bounce and friction at every corner
 * that touches, so it tumbles end over end, cartwheels, bounces and comes to rest. The same steps as
 * Scripts/physics_sandbox/wreck.py (renders: wreck_sims.py, Docs/DESTROCOS.md). The hull burns and trails smoke; every
 * hard strike throws sparks and dust. Gone after 15 s.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXWreck : public AActor
{
	GENERATED_BODY()

public:
	AEXWreck();
	virtual void Tick(float DeltaSeconds) override;

	/** A piece: its mesh and materials at a world transform; its box (half extents, cm) round the mesh's bounds, its
	 *  mass (kg), velocity (cm/s) and spin (rad/s, world axis). The first piece added is the hull. */
	void AddPiece(UStaticMesh* Mesh, const TArray<UMaterialInterface*>& Materials, const FTransform& World, float MassKg,
		const FVector& VelocityCmps, const FVector& SpinRad);
	/** The hull's place and velocity (cm, cm/s): the crash camera follows it. */
	FVector GetMainLocation() const;
	FVector GetMainVelocity() const;

private:
	struct FPiece
	{
		UStaticMeshComponent* Mesh = nullptr;
		FVector Pos = FVector::ZeroVector;       // m, the box's centre
		FVector Vel = FVector::ZeroVector;       // m/s
		FVector Spin = FVector::ZeroVector;      // rad/s, world axis
		FQuat Rot = FQuat::Identity;
		FVector Half = FVector(1.0, 1.0, 1.0);   // m
		FVector InvInertia = FVector(1.0, 1.0, 1.0);   // body axes, 1/(kg m^2)
		FVector CentreLocal = FVector::ZeroVector;     // cm, the mesh's bounds centre in its own space (scaled)
		float Mass = 100.0f;
		float Asleep = 0.0f;
		float HitCooldown = 0.0f;
	};
	struct FPuff
	{
		UMaterialBillboardComponent* Sprite = nullptr;
		UMaterialInstanceDynamic* Material = nullptr;
		FVector Pos = FVector::ZeroVector;       // cm
		float Age = 0.0f;
		float Life = 2.5f;
	};

	void StepPiece(FPiece& Piece, float Dt);
	void ApplyPose(const FPiece& Piece) const;
	void Strike(const FVector& PointM, float Speed, bool bHull);
	void Puff(const FVector& PosCm);

	UPROPERTY() TObjectPtr<UMaterialInterface> CharMaterial;
	UPROPERTY() TObjectPtr<UMaterialInterface> FlipbookMaterial;
	UPROPERTY() TObjectPtr<UTexture2D> FireTexture;
	UPROPERTY() TObjectPtr<UTexture2D> SmokeTexture;
	UPROPERTY() TObjectPtr<UMaterialBillboardComponent> Fire;
	UPROPERTY() TObjectPtr<UPointLightComponent> FireLight;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FireMaterial;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> CharMaterials;
	TArray<FPiece> Pieces;
	TArray<FPuff> Puffs;
	float Age = 0.0f;
	float PuffTimer = 0.0f;
	float StrikeCooldown = 0.0f;
};
