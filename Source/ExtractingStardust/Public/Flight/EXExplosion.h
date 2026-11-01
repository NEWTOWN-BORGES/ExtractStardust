#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXExplosion.generated.h"

class UMaterialBillboardComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UPointLightComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UTexture2D;

/**
 * A craft blowing up when its hull is gone (player, 2026-10-26; better on 2026-11-01: "melhore a explosão, veja exemplos").
 * After real blasts and the practice of game effects (Docs/DESTROCOS.md): a white flash, then several rolling fireballs
 * (flipbooks rendered in Blender, T_FX_Fireball) that swell and cool to smoke, a second, delayed burst beside them (it
 * makes the blast feel bigger), a shock ring along the ground and a ring of dust thrown out behind it, burning debris and
 * streaking sparks, and a column of dark smoke that rises and lingers. Carried on by the craft's speed; the wreck itself
 * (AEXWreck) flies on separately. Without the flipbooks it falls back to the shapes it was first built with.
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
	/** A small burst where a wreck strikes the ground: sparks and a puff of dust, a lick of fire when it is still hot. */
	void IgniteImpact(const FVector& VelocityCmps, float Strength, bool bHot);

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

	/** A camera-facing flipbook (M_FX_Flipbook): it waits Delay, then plays its frames over Life while it grows from Size to
	 *  EndSize (cm) and moves at Velocity (cm/s); Intensity is its glow (fire) or its opacity (smoke). */
	struct FSprite
	{
		UMaterialBillboardComponent* Sprite = nullptr;
		UMaterialInstanceDynamic* Material = nullptr;
		FVector Pos = FVector::ZeroVector;
		FVector Velocity = FVector::ZeroVector;
		float Delay = 0.0f;
		float Life = 1.0f;
		float Size = 100.0f;
		float EndSize = 100.0f;
		float Intensity = 1.0f;
		float Frames = 64.0f;
		bool bSmoke = false;
		bool bRises = false;
	};

	UStaticMeshComponent* MakeMesh(UStaticMesh* Mesh, UMaterialInterface* Material, UMaterialInstanceDynamic*& OutMaterial);
	bool LoadFlipbooks();
	void AddSprite(UTexture2D* Texture, float Cols, const FVector& Pos, const FVector& Velocity, float Delay, float SpriteLife, float Size, float EndSize,
		float Intensity, bool bSmoke, const FLinearColor& Colour, bool bRises = false);
	void AddSparks(int32 Count, const FVector& Origin, float Speed, float Size);

	UPROPERTY() TObjectPtr<UStaticMesh> SphereMesh;
	UPROPERTY() TObjectPtr<UStaticMesh> CubeMesh;
	UPROPERTY() TObjectPtr<UStaticMesh> CylinderMesh;
	UPROPERTY() TObjectPtr<UMaterialInterface> GlowMaterial;
	UPROPERTY() TObjectPtr<UMaterialInterface> DustMaterial;
	UPROPERTY() TObjectPtr<UPointLightComponent> Flash;
	UPROPERTY() TObjectPtr<UMaterialInterface> FlipbookMaterial;
	UPROPERTY() TObjectPtr<UTexture2D> FireballTexture;
	UPROPERTY() TObjectPtr<UTexture2D> SmokeTexture;
	TArray<FSprite> Sprites;
	/** The delayed second burst (a flash of its own), the life of this blast. */
	float SecondaryAt = -1.0f;
	float Life = 7.0f;
	/** The flash's strength (a wreck's strike flashes only a little). */
	float FlashGain = 1.0f;

	TArray<FBit> Fireball, Ring, Debris, Sparks, Smoke;
	FVector Drift = FVector::ZeroVector;
	float Age = 0.0f;
	float Scale = 1.0f;
	bool bLit = false;
};
