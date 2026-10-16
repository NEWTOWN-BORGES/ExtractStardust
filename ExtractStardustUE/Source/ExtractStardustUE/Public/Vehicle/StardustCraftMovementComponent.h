#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Vehicle/StardustCraftTypes.h"
#include "Vehicle/StardustHoverSensor.h"
#include "StardustCraftMovementComponent.generated.h"

class UPrimitiveComponent;

USTRUCT(BlueprintType)
struct FStardustCraftTelemetry
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	bool bGrounded = false;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	float SpeedMPerSecond = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	float ForwardSpeedMPerSecond = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	float LateralSpeedMPerSecond = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	float AirTimeSeconds = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	float LastLandingSpeedMPerSecond = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	float Nitro = 1.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	bool bNitroLocked = false;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	bool bDrifting = false;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	bool bBoosting = false;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	bool bMiniTurbo = false;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	float UpRateDegreesPerSecond = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	float UpRateSmoothed = 0.0f;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FStardustCraftSpeedEvent, float, SpeedMPerSecond);

UCLASS(ClassGroup = (Stardust), meta = (BlueprintSpawnableComponent))
class EXTRACTSTARDUSTUE_API UStardustCraftMovementComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UStardustCraftMovementComponent();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Craft")
	FStardustCraftTuning Tuning;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Craft")
	bool bAutoStep = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Craft")
	FStardustCraftInput Input;

	UPROPERTY(BlueprintReadOnly, Category = "Craft|Telemetry")
	FStardustCraftTelemetry Telemetry;

	UPROPERTY(BlueprintAssignable, Category = "Craft|Events")
	FStardustCraftSpeedEvent OnLanded;

	UFUNCTION(BlueprintCallable, Category = "Craft")
	void SetInput(const FStardustCraftInput& NewInput);

	UFUNCTION(BlueprintCallable, Category = "Craft")
	void SetBodyComponent(UPrimitiveComponent* NewBody);

	UFUNCTION(BlueprintCallable, Category = "Craft")
	void PlaceCraft(const FVector& PositionCm, const FRotator& Rotation, float SpeedMPerSecond);

	UFUNCTION(BlueprintCallable, Category = "Craft")
	void AddNitro(float Amount);

	UFUNCTION(BlueprintCallable, Category = "Craft")
	void StepCraft(float DeltaSeconds);

	const FStardustHoverState& GetHoverState() const { return HoverSensor.GetState(); }

protected:
	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UPrimitiveComponent> BodyComponent;

	FStardustHoverSensor HoverSensor;
	FVector LastCommandedSpin = FVector::ZeroVector;
	FVector LastUp = FVector::UpVector;
	FVector PreVelocityCmPerSecond = FVector::ZeroVector;
	float YawRate = 0.0f;
	float GripBlend = 1.0f;
	float SlipAngleRadians = 0.0f;
	float DriftChargeSeconds = 0.0f;
	bool bWasGrounded = false;
	float Nitro = 1.0f;
	bool bNitroLocked = false;

	void InitializeBody();
	FVector FindAirTargetUp(const FVector& PositionCm, const FVector& VelocityMPerSecond, const FVector& CurrentUp) const;
	static FVector ConvertUnityVectorToUnreal(const FVector& UnityVector);
	static FVector ProjectOnPlane(const FVector& Vector, const FVector& PlaneNormal);
	static float Damp(float Lambda, float DeltaSeconds);
};
