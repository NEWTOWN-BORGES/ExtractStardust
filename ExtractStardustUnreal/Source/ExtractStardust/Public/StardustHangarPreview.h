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
	bool InstallPart(FName SocketId, const FStardustPartDefinition& Part);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Hangar")
	void RemoveInstalledPart(FName SocketId);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Hangar")
	bool SetChassis(FName ChassisId);

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Hangar")
	FName GetChassis() const { return CurrentChassisId; }

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Hangar")
	TArray<FStardustSocketDefinition> GetSockets() const { return Sockets; }

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

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hangar")
	FName CurrentChassisId = TEXT("strix");

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hangar")
	TMap<FName, FStardustPartDefinition> InstalledParts;

private:
	const FStardustSocketDefinition* FindSocket(FName SocketId) const;
	void ConfigureSockets(FName ChassisId);
	void SetPartMaterial(bool bCompatible);
};
