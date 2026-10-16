#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "StardustSpeedFxComponent.generated.h"

class UCameraComponent;
class UStardustCraftMovementComponent;
class USpringArmComponent;

UCLASS(ClassGroup = (Stardust), meta = (BlueprintSpawnableComponent))
class EXTRACTSTARDUSTUE_API UStardustSpeedFxComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UStardustSpeedFxComponent();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "1.0"))
	float MaxSpeedForEffectsMPerSecond = 118.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "0.0"))
	float BaseFOV = 90.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "1.0", ClampMax = "179.0"))
	float MaxFOV = 118.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "0.0"))
	float BoostFOVBonus = 2.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "0.0"))
	float MaxArmExtensionCm = 180.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "0.0"))
	float BoostArmExtensionCm = 55.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "0.0"))
	float DriftArmCompressionCm = 60.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "0.0"))
	float MaxSpeedPitchOffsetDegrees = 3.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "0.0"))
	float AccelerationPitchOffsetDegrees = 2.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "0.0"))
	float MaxDriftRollDegrees = 6.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Camera", meta = (ClampMin = "0.0"))
	float MaxSpeedCameraLagReduction = 3.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Post Process", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float BaseVignetteIntensity = 0.14f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Post Process", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float SpeedVignetteIntensity = 0.04f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Post Process", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float BoostVignetteIntensity = 0.05f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Post Process", meta = (ClampMin = "0.0"))
	float BoostChromaticIntensity = 0.06f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Post Process", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float MaxSpeedMotionBlur = 0.30f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Post Process", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float BoostMotionBlur = 0.45f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Impact", meta = (ClampMin = "0.05"))
	float ImpactShakeDurationSeconds = 0.45f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Speed FX|Impact", meta = (ClampMin = "0.0"))
	float MaxImpactShakeDegrees = 4.0f;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UStardustCraftMovementComponent> CraftMovement;

	UPROPERTY(Transient)
	TObjectPtr<USpringArmComponent> CameraArm;

	UPROPERTY(Transient)
	TObjectPtr<UCameraComponent> ChaseCamera;

	FRotator BaseArmRotation = FRotator::ZeroRotator;
	FVector LastVelocityMPerSecond = FVector::ZeroVector;
	float BaseArmLengthCm = 900.0f;
	float BaseCameraLagSpeed = 8.0f;
	float SmoothedSpeedRatio = 0.0f;
	float SmoothedBoostStrength = 0.0f;
	float SmoothedDriftStrength = 0.0f;
	float SmoothedAccelerationRatio = 0.0f;
	float ImpactShakeStrength = 0.0f;
	float ImpactShakeElapsedSeconds = 0.0f;

	UFUNCTION()
	void HandleCraftDamaged(float Damage);
};
