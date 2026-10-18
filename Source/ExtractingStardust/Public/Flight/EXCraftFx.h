#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "EXCraftFx.generated.h"

class UMaterialInstanceDynamic;
class UMaterialInterface;
class UPointLightComponent;
class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;

/** What the effects need from the craft each frame. Positions in cm, velocity in cm/s. */
struct FEXCraftFxInput
{
	FVector Velocity = FVector::ZeroVector;
	FVector Heading = FVector::ForwardVector;
	FVector SurfaceUp = FVector::UpVector;
	FVector GroundPoint = FVector::ZeroVector;
	FVector CameraLocation = FVector::ZeroVector;
	FVector CameraForward = FVector::ForwardVector;
	float SpeedAlpha = 0.0f;
	float Throttle = 0.0f;
	float HeightM = 99.0f;
	bool bGrounded = false;
	bool bBoosting = false;
	bool bDrifting = false;
};

/**
 * Speed effects for the hover craft, built from simple meshes and two FX materials: engine flames that grow
 * with throttle, speed and nitro; sand dust kicked up near the ground (with a burst on landing); and wind
 * streaks that rush past the camera at high speed.
 */
UCLASS(ClassGroup = (Flight), meta = (BlueprintSpawnableComponent))
class EXTRACTINGSTARDUST_API UEXCraftFx : public UActorComponent
{
	GENERATED_BODY()

public:
	UEXCraftFx();

	/** Creates the effect meshes. Flames are attached to ShipAttach so they bank with the ship. */
	void Initialize(USceneComponent* ShipAttach);
	/** Half size of the current ship in the craft's frame (X length, Y width, Z height), in cm. */
	void SetShipHalfSize(const FVector& HalfSizeCm);
	void UpdateFx(float Dt, const FEXCraftFxInput& Input);
	void LandingBurst(const FVector& Point, const FVector& Up, float Strength);

	UPROPERTY(EditAnywhere, Category = "Fx") FLinearColor FlameColor = FLinearColor(1.0f, 0.25f, 0.04f);
	UPROPERTY(EditAnywhere, Category = "Fx") FLinearColor FlameCoreColor = FLinearColor(1.0f, 0.7f, 0.35f);
	/** Unlit, so it is kept darker than the sand it comes from. */
	UPROPERTY(EditAnywhere, Category = "Fx") FLinearColor DustColor = FLinearColor(0.34f, 0.25f, 0.17f);
	/** Dust puffs per second at top speed. */
	UPROPERTY(EditAnywhere, Category = "Fx") float DustRateMax = 16.0f;

private:
	struct FPuff
	{
		FVector Location = FVector::ZeroVector;
		FVector Velocity = FVector::ZeroVector;
		float Age = 0.0f;
		float Life = 1.0f;
		float StartSizeM = 1.0f;
		float EndSizeM = 4.0f;
		float Opacity = 0.3f;
		bool bActive = false;
	};

	UStaticMeshComponent* MakeMesh(UStaticMesh* Mesh, UMaterialInterface* Material, USceneComponent* Parent, bool bWorldSpace);
	void SpawnPuff(const FVector& Location, const FVector& Velocity, float Life, float StartSizeM, float EndSizeM, float Opacity);
	void UpdateFlames(float Dt, const FEXCraftFxInput& Input);
	void UpdateDust(float Dt, const FEXCraftFxInput& Input);
	void UpdateStreaks(float Dt, const FEXCraftFxInput& Input);

	UPROPERTY() TObjectPtr<UStaticMesh> SphereMesh;
	UPROPERTY() TObjectPtr<UStaticMesh> CylinderMesh;
	UPROPERTY() TObjectPtr<UMaterialInterface> GlowMaterial;
	UPROPERTY() TObjectPtr<UMaterialInterface> DustMaterial;
	/** Per engine: outer flame, then core. */
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> FlameMeshes;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> FlameMaterials;
	UPROPERTY(Transient) TArray<TObjectPtr<UPointLightComponent>> EngineLights;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> PuffMeshes;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> PuffMaterials;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> StreakMeshes;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> StreakMaterial;

	TArray<FPuff> Puffs;
	TArray<FVector> StreakLocations;
	TArray<bool> StreakActive;
	FVector EngineAnchors[2] = { FVector::ZeroVector, FVector::ZeroVector };
	FVector ShipHalfSize = FVector(330.0f, 160.0f, 60.0f);
	float FlameRadiusCm = 30.0f;
	float FlamePower = 0.0f;
	float FlickerTime = 0.0f;
	float SpawnAccumulator = 0.0f;
	bool bInitialized = false;
	FRandomStream Random = FRandomStream(1977);
};
