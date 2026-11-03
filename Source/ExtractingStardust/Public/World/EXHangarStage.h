#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXHangarStage.generated.h"

class UMaterialInstanceDynamic;
class UMaterialInterface;
class URectLightComponent;
class USpotLightComponent;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * The hangar: a workshop (32 x 28 x 10 m) built at runtime from engine shapes, so the ships are seen in detail:
 * light grey epoxy floor with a grid, ribbed walls, two rows of ceiling light panels (rect lights behind glowing
 * panels), key and fill spots, a turntable platform with a glowing rim and a safety ring, tool cabinets, crates and gas
 * cylinders. It stands far from the track (12 km west, 3 km up: no fog, no terrain) and closed, so the desert light
 * does not reach in. The craft is moved onto the platform for the menu and the hangar (AEXHoverCraft::EnterShowroom).
 * The lights start off and come on row after row when the stage first opens (the menu and the hangar both show the
 * garage lit: the player turned down a dark menu, 2026-10-25). Same layout as the hangar mock-up render.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXHangarStage : public AActor
{
	GENERATED_BODY()

public:
	AEXHangarStage();

	/** The middle of the turntable's top, in world space. */
	FVector GetPlatformTop() const;
	/** The stage of this world, spawned on first use. */
	static AEXHangarStage* FindOrSpawn(UWorld* World);
	/** Light level to fade to: 0 work lights down (a spot on the ship), 1 the workshop lit. */
	void SetLightTarget(float Target) { LightTarget = FMath::Clamp(Target, 0.0f, 1.0f); }
	/** The mood now, 0..1 (the craft's camera sets its exposure and vignette from it). */
	float GetLightLevel() const { return LightLevel; }

	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

private:
	void Build();
	void ApplyLights();
	UStaticMeshComponent* AddPart(UStaticMesh* Mesh, const FVector& CenterCm, const FRotator& Rotation, const FVector& SizeCm,
		const FLinearColor& Color, float Glow = 0.0f, UMaterialInstanceDynamic* OwnMaterial = nullptr);
	UMaterialInstanceDynamic* MakeGlow(const FLinearColor& Color, float Glow);
	URectLightComponent* AddRectLight(const FVector& Location, float Lumens, float WidthCm, float HeightCm, bool bShadows);
	USpotLightComponent* AddSpot(const FVector& Location, const FVector& Target, float Lumens, const FLinearColor& Color, float OuterDeg);

	UPROPERTY() TObjectPtr<UStaticMesh> CubeMesh;
	UPROPERTY() TObjectPtr<UStaticMesh> CylinderMesh;
	UPROPERTY() TObjectPtr<UMaterialInterface> ColorMaterial;
	UPROPERTY() TObjectPtr<UMaterialInterface> GlowMaterial;
	UPROPERTY(Transient) TMap<FString, TObjectPtr<UMaterialInstanceDynamic>> Materials;
	/** Ceiling: one glow material per column of panels and the rect lights under them, with their column (0..6). */
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> PanelGlows;
	UPROPERTY(Transient) TArray<TObjectPtr<URectLightComponent>> WorkLights;
	TArray<int32> WorkLightColumns;
	UPROPERTY(Transient) TObjectPtr<USpotLightComponent> KeySpot;
	UPROPERTY(Transient) TObjectPtr<USpotLightComponent> FillSpot;
	UPROPERTY(Transient) TObjectPtr<USpotLightComponent> TopSpot;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SignGlow;
	float LightTarget = 0.0f, LightLevel = 0.0f;
	bool bBuilt = false, bLightsApplied = false;
};
