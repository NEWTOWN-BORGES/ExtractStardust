#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXBoostArrows.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;

/**
 * Glowing chevrons painted on the ground before every jump of the race line, like the dash panels of the Sonic games
 * (player, 2026-11-01: "os saltos na areia são difíceis de ver; põe setas tipo setas de nitro"). Found at the start of
 * a race from the line's height profile (where the ground drops away ahead), so they need no rebuild of the map. Three
 * chevrons across the road, five rows over the last 50 m before the lip, the rows pulsing one after the other towards
 * the jump. No collision.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXBoostArrows : public AActor
{
	GENERATED_BODY()

public:
	AEXBoostArrows();
	virtual void Tick(float DeltaSeconds) override;

	/** Route: the race line (m, every 5 m); Heights: its height (m); HalfWidths: the road's half width (m). */
	int32 Build(const TArray<FVector2D>& Route, const TArray<float>& Heights, const TArray<float>& HalfWidths);

private:
	static constexpr int32 Rows = 5;
	UPROPERTY() TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> RowMeshes;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> RowMaterials;
	float Age = 0.0f;
};
