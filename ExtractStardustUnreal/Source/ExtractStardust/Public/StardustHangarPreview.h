#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "StardustTypes.h"
#include "StardustHangarPreview.generated.h"

class UStaticMeshComponent;
class UMaterialInterface;

UCLASS(Blueprintable)
class EXTRACTSTARDUST_API AStardustHangarPreview : public AActor
{
	GENERATED_BODY()

public:
	AStardustHangarPreview();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Hangar")
	TArray<FStardustPartDefinition> GetCompatibleParts(FName SocketId, const TArray<FStardustPartDefinition>& Candidates) const;

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Hangar")
	bool PreviewPart(FName SocketId, const FStardustPartDefinition& Part);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Hangar")
	void ClearPartPreview();

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hangar")
	TObjectPtr<UStaticMeshComponent> ChassisPreview;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hangar")
	TObjectPtr<UStaticMeshComponent> PartPreview;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hangar")
	TArray<FStardustSocketDefinition> Sockets;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hangar")
	TObjectPtr<UMaterialInterface> IncompatibleMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hangar")
	bool bAutoRotate = true;

private:
	const FStardustSocketDefinition* FindSocket(FName SocketId) const;
};
