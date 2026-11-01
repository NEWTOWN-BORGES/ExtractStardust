#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXPhysicsSandbox.generated.h"

class AEXHoverCraft;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UStaticMesh;

/**
 * The physics sandbox (player, 2026-11-01: "estudar numa sandbox com saltos, rampas, etc."): a loop of 7 km built in code
 * high above any map (Scripts\jogar.ps1 -Modo Sandbox, -EXSandbox). Out along the first straight: a small kicker, a table
 * top, a big kicker, three smooth crests of growing height, a climb to a plateau that ends in a 14 m cliff, and a
 * washboard; back along the second straight, flat and wide, a pack of bots to rub, shove and spin (Burnout style). The
 * crafts log every jump and every knock (EXPHYS lines) and the screen shows the last ones; a blown-up ship comes back in
 * 3 s, a fall off the edge comes back on the loop. Docs/FISICA.md.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXPhysicsSandbox : public AActor
{
	GENERATED_BODY()

public:
	AEXPhysicsSandbox();
	virtual void Tick(float DeltaSeconds) override;

	/** Where the sandbox stands: far from every map's own world, 2 km up. */
	static FVector Origin() { return FVector(4000000.0, -4000000.0, 200000.0); }

protected:
	virtual void BeginPlay() override;

private:
	void Build();
	void Populate();
	/** A slab whose top follows the profile (metres along X from the straight's start, height), across a width. */
	void AddProfile(const TArray<FVector2D>& ProfileM, float LaneY, float WidthM, const FLinearColor& Colour);
	void AddBlock(UStaticMesh* Mesh, const FVector& CenterCm, const FRotator& Rotation, const FVector& SizeCm, const FLinearColor& Colour,
		bool bGrid = false);
	/** The ground's height (m) along the first straight at X (m): the features' profile. */
	float FeatureZ(float XM) const;

	UPROPERTY() TObjectPtr<UStaticMesh> CubeMesh;
	UPROPERTY() TObjectPtr<UStaticMesh> CylinderMesh;
	UPROPERTY() TObjectPtr<UMaterialInterface> ColorMaterial;
	UPROPERTY() TObjectPtr<UMaterialInterface> GridMaterial;
	UPROPERTY(Transient) TMap<FString, TObjectPtr<UMaterialInstanceDynamic>> ColorMaterials;
	UPROPERTY(Transient) TArray<TObjectPtr<AEXHoverCraft>> Crafts;
	/** The features' profile along the first straight (m) and the loop the crafts follow (cm). */
	TArray<FVector2D> Profile;
	TArray<FVector> Route;
	TArray<float> DeadFor;
	bool bPopulated = false;
};
