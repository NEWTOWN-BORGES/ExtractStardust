#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXTestArena.generated.h"

class UMaterialInstanceDynamic;
class UMaterialInterface;
class UStaticMesh;
class UStaticMeshComponent;

/** Flight test ground built at runtime: open floor with speed references, a jump ramp, a walled corridor and a half-pipe. */
UCLASS()
class EXTRACTINGSTARDUST_API AEXTestArena : public AActor
{
	GENERATED_BODY()

public:
	AEXTestArena();

protected:
	virtual void BeginPlay() override;

private:
	void BuildArena();
	UStaticMeshComponent* AddBlock(UStaticMesh* Mesh, const FVector& CenterCm, const FRotator& Rotation, const FVector& SizeCm,
		const FLinearColor& Color, bool bGridMaterial = false);

	UPROPERTY() TObjectPtr<UStaticMesh> CubeMesh;
	UPROPERTY() TObjectPtr<UStaticMesh> CylinderMesh;
	UPROPERTY() TObjectPtr<UMaterialInterface> ColorMaterial;
	UPROPERTY() TObjectPtr<UMaterialInterface> GridMaterial;
	UPROPERTY(Transient) TMap<FString, TObjectPtr<UMaterialInstanceDynamic>> ColorMaterials;
};
