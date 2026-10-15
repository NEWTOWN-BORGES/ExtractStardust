#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "StardustHoverPawn.generated.h"

class UCameraComponent;
class USpringArmComponent;
class UStaticMeshComponent;

UCLASS(Blueprintable)
class EXTRACTSTARDUST_API AStardustHoverPawn : public APawn
{
	GENERATED_BODY()

public:
	AStardustHoverPawn();
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Vehicle")
	void ActivateConsumable(int32 Slot);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Vehicle")
	void ResetCraft();

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Vehicle")
	float GetSpeedKmh() const { return Velocity.Size() * 0.036f; }

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Vehicle")
	float GetHull() const { return Hull; }

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Vehicle")
	float GetBoostFuel() const { return BoostFuel; }

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Vehicle")
	float GetHeat() const { return Heat; }

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Vehicle")
	int32 GetLoadoutCount(int32 Slot) const;

	void SetControlInput(float Throttle, float Steering, float BrakeValue, float NitroValue);

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components")
	TObjectPtr<UStaticMeshComponent> CraftBody;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components")
	TObjectPtr<USpringArmComponent> CameraArm;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components")
	TObjectPtr<UCameraComponent> ChaseCamera;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Flight Model", meta=(ClampMin="0"))
	float HoverHeight = 190.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Flight Model", meta=(ClampMin="0"))
	float Acceleration = 2600.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Flight Model", meta=(ClampMin="1"))
	float MaxSpeed = 4200.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Flight Model", meta=(ClampMin="0"))
	float TurnRate = 88.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Flight Model", meta=(ClampMin="0"))
	float HoverSpring = 22.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Flight Model", meta=(ClampMin="0"))
	float HoverDamping = 8.0f;

private:
	void SetThrottle(float Value) { ThrottleInput = Value; }
	void SetSteering(float Value) { SteeringInput = Value; }
	void SetBrake(float Value) { BrakeInput = Value; }
	void SetNitro(float Value) { NitroInput = Value; }
	void ActivateSlot0() { ActivateConsumable(0); }
	void ActivateSlot1() { ActivateConsumable(1); }
	void ActivateSlot2() { ActivateConsumable(2); }
	void ActivateSlot3() { ActivateConsumable(3); }

	FVector Velocity = FVector::ZeroVector;
	FVector SpawnLocation = FVector::ZeroVector;
	FRotator SpawnRotation = FRotator::ZeroRotator;
	float VerticalSpeed = 0.0f;
	float ThrottleInput = 0.0f;
	float SteeringInput = 0.0f;
	float BrakeInput = 0.0f;
	float NitroInput = 0.0f;
	float Hull = 100.0f;
	float BoostFuel = 60.0f;
	float Heat = 0.0f;
	float StabilizerTime = 0.0f;
	float RepairTime = 0.0f;
};
