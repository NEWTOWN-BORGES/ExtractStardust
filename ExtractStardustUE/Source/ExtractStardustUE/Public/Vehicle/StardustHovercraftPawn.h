#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "Vehicle/StardustCraftTypes.h"
#include "StardustHovercraftPawn.generated.h"

class UCameraComponent;
class UStardustSpeedFxComponent;
class UPrimitiveComponent;
class UStardustCourseComponent;
class UStardustCraftMovementComponent;
class UStardustRaceProgressComponent;
class USpringArmComponent;
class UStaticMeshComponent;

UCLASS()
class EXTRACTSTARDUSTUE_API AStardustHovercraftPawn : public APawn
{
	GENERATED_BODY()

public:
	AStardustHovercraftPawn();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Craft")
	TObjectPtr<UStaticMeshComponent> HullMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Craft")
	TObjectPtr<UStardustCraftMovementComponent> MovementComponent;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Race")
	TObjectPtr<UStardustCourseComponent> CourseComponent;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Race")
	TObjectPtr<UStardustRaceProgressComponent> RaceProgressComponent;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<USpringArmComponent> CameraArm;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<UCameraComponent> ChaseCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<UStardustSpeedFxComponent> SpeedFxComponent;

protected:
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

private:
	FStardustCraftInput PendingInput;

	void ApplyInput();
	void SetThrottle(float Value);
	void SetSteer(float Value);
	void SetAirPitch(float Value);
	void PressBrake();
	void ReleaseBrake();
	void PressBoost();
	void ReleaseBoost();
	void PressDrift();
	void ReleaseDrift();

	UFUNCTION()
	void OnHullHit(UPrimitiveComponent* HitComponent, AActor* OtherActor, UPrimitiveComponent* OtherComponent,
		FVector NormalImpulse, const FHitResult& Hit);
};
