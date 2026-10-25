#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EXHangarStage.generated.h"

class UStaticMesh;
class USceneComponent;

/** A lightweight, engine-native preview bay assembled from built-in meshes at runtime. */
UCLASS()
class EXTRACTINGSTARDUST_API AEXHangarStage : public AActor
{
	GENERATED_BODY()

public:
	AEXHangarStage();

protected:
	virtual void BeginPlay() override;

private:
	void AddBox(const TCHAR* Name, const FVector& Location, const FVector& Scale);
	void AddLight(const TCHAR* Name, const FVector& Location, const FLinearColor& Colour, float Intensity, float Radius);

	UPROPERTY(Transient)
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> CubeMesh;
};
