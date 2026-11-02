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
 * Scripts/physics_sandbox/wreck.py (renders: wreck_sims.py, Docs/DESTROCOS.md). Every piece flies as a ball of fire
 * (player, 2026-11-01: "peças em bolas de fogo"): flames on it streaming back, a trail of tongues of flame behind it
 * and smoke rising from it, until it burns out (the hull after 11 s, the modules after 4.5-7 s). Every hard
 * strike throws sparks and dust. Gone after 15 s. The video Docs/DESTROCOS_<cause>.mp4 (wreck_video.py) shows it.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXWreck : public AActor
{
	GENERATED_BODY()

public:
	AEXWreck();
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
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
		// burning: the flames on it, how long it burns, its heat (1 -> 0), its size (m) and the trail it leaves
		UMaterialBillboardComponent* Flame = nullptr;
		UMaterialInstanceDynamic* FlameMat = nullptr;
		UMaterialInstanceDynamic* CharMat = nullptr;
		float Burn = 11.0f;
		float Heat = 1.0f;
		float Size = 1.0f;
		float FlamePhase = 0.0f;
		float TrailGap = 0.0f;
		float TrailWait = 0.0f;
		float PuffTimer = 0.0f;
		float FlameQuad = 0.0f;                  // its flame sprite's square now (EXFx::SetSpriteSize)
	};
	/** A tongue of flame left behind a burning piece (the flames flipbook, streaming back the way the piece flew): they
	 *  overlap into one trail of fire, and the smoke puffs carry it on. */
	struct FTrail
	{
		UMaterialBillboardComponent* Sprite = nullptr;
		UMaterialInstanceDynamic* Material = nullptr;
		FVector Pos = FVector::ZeroVector;       // cm, its base
		FVector Vel = FVector::ZeroVector;       // cm/s
		FVector Stream = FVector::UpVector;      // the way its flames point (world)
		float Age = 0.0f;
		float Life = 0.0f;                       // 0: free
		float Size0 = 100.0f;                    // cm
		float Size1 = 130.0f;
		float Glow = 7.0f;
		float FrameShift = 0.0f;                 // where in the flames' loop it starts
		float Quad = 0.0f;
	};
	/** A puff of smoke from a burning piece (the smoke flipbook, dark grey): rising, growing, thinning. */
	struct FPuff
	{
		UMaterialBillboardComponent* Sprite = nullptr;
		UMaterialInstanceDynamic* Material = nullptr;
		FVector Pos = FVector::ZeroVector;       // cm
		float Age = 0.0f;
		float Life = 0.0f;
		float Size0 = 220.0f;                    // cm
		float Size1 = 950.0f;
		float Quad = 0.0f;
	};

	void StepPiece(FPiece& Piece, float Dt);
	void ApplyPose(const FPiece& Piece) const;
	void Strike(const FVector& PointM, float Speed, bool bHull);
	void Puff(const FPiece& Piece, bool bHull);
	void Trail(const FPiece& Piece, const FVector& Stream);
	void UpdateTrails(float Dt, const FVector& CamRight, const FVector& CamUp);
	void UpdatePuffs(float Dt);

	UPROPERTY() TObjectPtr<UMaterialInterface> CharMaterial;
	UPROPERTY() TObjectPtr<UMaterialInterface> FlipbookMaterial;
	UPROPERTY() TObjectPtr<UTexture2D> FireTexture;
	UPROPERTY() TObjectPtr<UTexture2D> SmokeTexture;
	UPROPERTY() TObjectPtr<UPointLightComponent> FireLight;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> CharMaterials;
	TArray<FPiece> Pieces;
	TArray<FPuff> Puffs;
	TArray<FTrail> Trails;
	float Age = 0.0f;
	float StrikeCooldown = 0.0f;
	/** How far the camera is (m): far wrecks burn with fewer trails and no bursts (fps). */
	float CamDistM = 0.0f;
};
