#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXTrackSigns.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;

/**
 * Signs along the race line, so the way can be read in the open sand (player, 2026-11-01: "na areia fica difícil de ver
 * por onde ir"): chevron boards on the outside of every bend, a glowing double chevron pointing into the turn on each,
 * and edge poles with an amber light on both sides of the road wherever there is no wall beside it (the sand, the
 * dunes), none in the canyons or under a roof. Found at the start of a race from the line, so no rebuild of the map is
 * needed. No collision.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXTrackSigns : public AActor
{
	GENERATED_BODY()

public:
	AEXTrackSigns();
	virtual void Tick(float DeltaSeconds) override;

	/** Route: the race line (m, every 5 m); Heights: its height (m); HalfWidths: the road's half width (m). */
	void Build(const TArray<FVector2D>& Route, const TArray<float>& Heights, const TArray<float>& HalfWidths);

private:
	UHierarchicalInstancedStaticMeshComponent* MakeLayer(const TCHAR* Name);
	UPROPERTY() TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Boards;
	UPROPERTY() TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Chevrons;
	UPROPERTY() TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Posts;
	UPROPERTY() TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Lights;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ChevronMaterial;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> LightMaterial;
	float Age = 0.0f;
};
