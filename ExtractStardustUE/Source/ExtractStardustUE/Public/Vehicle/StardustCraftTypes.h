#pragma once

#include "CoreMinimal.h"
#include "StardustCraftTypes.generated.h"

USTRUCT(BlueprintType)
struct FStardustCraftInput
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Input", meta = (ClampMin = "-1", ClampMax = "1"))
	float Steer = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Input", meta = (ClampMin = "0", ClampMax = "1"))
	float Throttle = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Input")
	bool bBrake = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Input")
	bool bBoost = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Input")
	bool bDrift = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Input", meta = (ClampMin = "-1", ClampMax = "1"))
	float AirPitch = 0.0f;
};

USTRUCT(BlueprintType)
struct FStardustCraftTuning
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mass and Hull")
	float MassKg = 1450.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mass and Hull")
	FVector HullSizeM = FVector(3.4, 1.0, 7.0);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mass and Hull")
	FVector CenterOfMassM = FVector(0.0, -0.15, 0.0);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float HoverHeightM = 1.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float CaptureRangeM = 2.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float ProbeReachM = 6.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float SpringHz = 3.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float DampingRatio = 0.72f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float MaxHoverAccel = 280.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float Gravity = 22.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float Adhesion = 9.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float AdhesionMinSpeed = 45.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float AdhesionFullSpeed = 90.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float ProbeHalfWidthM = 1.45f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float ProbeHalfLengthM = 2.9f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float LookAheadTime = 0.14f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Repulsors")
	float NormalSmoothing = 0.035f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Propulsion")
	float TopSpeed = 118.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Propulsion")
	float Accel = 36.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Propulsion")
	float BoostTopMul = 1.16f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Propulsion")
	float BoostAccel = 34.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Propulsion")
	float BrakeDecel = 44.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Propulsion")
	float AirThrust = 0.3f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Propulsion")
	float AeroDrag = 0.00012f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Propulsion")
	float OverspeedBleed = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float TurnRateLow = 2.4f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float TurnRateHigh = 0.8f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float SteerResponse = 10.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float GripRedirect = 5.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float GripLateralMax = 85.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float GripFriction = 1.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float GripBase = 0.10f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float GripSpeedRef = 125.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float GripCap = 0.55f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float DriftRedirect = 2.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float DriftLateralMax = 62.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float DriftTurnMul = 1.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float DriftDecel = 3.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float DriftKick = 0.45f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float DriftMaxSlip = 32.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float DriftRecoverTime = 0.35f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float BrakeTurnMul = 1.35f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float BrakeGripMul = 1.25f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float DriftBoost = 10.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Steering and Grip")
	float CoastDecel = 6.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Nitro")
	float NitroSeconds = 3.4f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Nitro")
	float NitroRegen = 0.20f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Nitro")
	float NitroDriftRegen = 0.30f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Nitro")
	float NitroAirRegen = 0.15f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Nitro")
	float NitroRestart = 0.18f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Attitude")
	float AlignRate = 160.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Attitude")
	float AlignTime = 0.09f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Attitude")
	float AirAlignRate = 45.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Attitude")
	float AirTurnMul = 0.35f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Attitude")
	float AirPitchRate = 0.9f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Attitude")
	float StabilityRecover = 9.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Damage Events")
	float LandingSoft = 9.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Damage Events")
	float LandingHard = 17.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Damage Events")
	float ImpactMin = 12.0f;

	float GetTurnRate(float Speed) const;
	float GetSpringK() const;
	float GetSpringC() const;
	float GetAdhesion(float Speed) const;
	float GetGripFactor(float Speed) const;
	float GetCornerSpeed(float Curvature, float BankDegrees, float Margin = 0.82f) const;
};
