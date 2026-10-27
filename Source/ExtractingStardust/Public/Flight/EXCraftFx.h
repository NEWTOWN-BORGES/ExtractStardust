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
	/** The craft whose camera is on screen: only it draws the speed streaks (bots don't). */
	bool bViewer = true;
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
	/** The engine nozzles in the craft's frame (cm), from the ship's module manifest (up to four); an empty list goes
	 *  back to two nozzles estimated from the size. */
	void SetNozzles(const TArray<FVector>& AnchorsCm, float RadiusCm);
	/** The flame of the engine module (EXMeta::Flame): colours, length and width against the stock flame, shock
	 *  diamonds, sparks; and the nitro colour of the propulsion module. */
	void SetFlameStyle(const FLinearColor& Outer, const FLinearColor& Core, float LengthMul, float RadiusMul, int32 Diamonds, bool bSparks,
		const FLinearColor& Nitro);
	/** Hangar: the engines run at this power with the craft standing still (0 switches them off). Call every frame. */
	void TickPreview(float Dt, float Power);
	void UpdateFx(float Dt, const FEXCraftFxInput& Input);
	void LandingBurst(const FVector& Point, const FVector& Up, float Strength);
	/** Sparks thrown off a wall hit or scrape. */
	void ImpactSparks(const FVector& Point, const FVector& Normal, const FVector& CraftVelocity, float Strength);

	UPROPERTY(EditAnywhere, Category = "Fx") FLinearColor FlameColor = FLinearColor(1.0f, 0.25f, 0.04f);
	UPROPERTY(EditAnywhere, Category = "Fx") FLinearColor FlameCoreColor = FLinearColor(1.0f, 0.7f, 0.35f);
	/** Nitro turns the flames blue. */
	UPROPERTY(EditAnywhere, Category = "Fx") FLinearColor BoostFlameColor = FLinearColor(0.25f, 0.45f, 1.0f);
	UPROPERTY(EditAnywhere, Category = "Fx") FLinearColor BoostCoreColor = FLinearColor(0.75f, 0.88f, 1.0f);
	/** Unlit, so it is kept darker than the sand it comes from. */
	UPROPERTY(EditAnywhere, Category = "Fx") FLinearColor DustColor = FLinearColor(0.34f, 0.25f, 0.17f);
	/** Dust puffs per second at top speed. */
	UPROPERTY(EditAnywhere, Category = "Fx") float DustRateMax = 22.0f;

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

	struct FSpark
	{
		FVector Location = FVector::ZeroVector;
		FVector Velocity = FVector::ZeroVector;
		float Age = 0.0f;
		float Life = 0.4f;
		bool bActive = false;
	};

	UStaticMeshComponent* MakeMesh(UStaticMesh* Mesh, UMaterialInterface* Material, USceneComponent* Parent, bool bWorldSpace);
	void UpdateSparks(float Dt);
	void SpawnSpark(const FVector& Location, const FVector& Velocity, float Life);
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
	/** Per engine, the shock diamonds of the burner and the epic flames. */
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> DiamondMeshes;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> DiamondMaterial;
	UPROPERTY(Transient) TObjectPtr<USceneComponent> FlameParent;
	UPROPERTY(Transient) TArray<TObjectPtr<UPointLightComponent>> EngineLights;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> PuffMeshes;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> PuffMaterials;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> StreakMeshes;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> StreakMaterial;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> SparkMeshes;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SparkMaterial;

	TArray<FPuff> Puffs;
	TArray<FSpark> Sparks;
	float BoostBlend = 0.0f;
	TArray<FVector> StreakLocations;
	TArray<bool> StreakActive;
	TArray<FVector> EngineAnchors;
	FVector ShipHalfSize = FVector(330.0f, 160.0f, 60.0f);
	float FlameRadiusCm = 30.0f;
	bool bNozzlesFromManifest = false;
	float StyleLength = 1.0f, StyleRadius = 1.0f, SparkTimer = 0.0f;
	int32 StyleDiamonds = 0;
	bool bStyleSparks = false;
	/** TickPreview's power for this frame (-1: the flames follow the flight input). */
	float PreviewPowerOverride = -1.0f;
	float FlamePower = 0.0f;
	float FlickerTime = 0.0f;
	float SpawnAccumulator = 0.0f;
	bool bInitialized = false;
	FRandomStream Random = FRandomStream(1977);
};
