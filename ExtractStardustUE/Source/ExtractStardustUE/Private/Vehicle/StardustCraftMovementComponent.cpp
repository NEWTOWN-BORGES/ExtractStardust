#include "Vehicle/StardustCraftMovementComponent.h"

#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"

namespace
{
	constexpr float CmPerMeter = 100.0f;
}

UStardustCraftMovementComponent::UStardustCraftMovementComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
	PrimaryComponentTick.TickInterval = 1.0f / 90.0f;
	Input.Throttle = 1.0f;
}

void UStardustCraftMovementComponent::BeginPlay()
{
	super::BeginPlay();
	InitializeBody();
}

void UStardustCraftMovementComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (bAutoStep)
	{
		StepCraft(DeltaTime);
	}
}

void UStardustCraftMovementComponent::InitializeBody()
{
	if (!BodyComponent && GetOwner())
	{
		BodyComponent = Cast<UPrimitiveComponent>(GetOwner()->GetRootComponent());
	}
	if (!BodyComponent || !BodyComponent->IsSimulatingPhysics())
	{
		return;
	}

	BodyComponent->SetEnableGravity(false);
	BodyComponent->SetMassOverrideInKg(NAME_None, Tuning.MassKg, true);
	BodyComponent->SetCenterOfMass(ConvertUnityVectorToUnreal(Tuning.CenterOfMassM) * CmPerMeter);
	HoverSensor.Reset(BodyComponent->GetUpVector());
	LastUp = BodyComponent->GetUpVector();
}

void UStardustCraftMovementComponent::SetInput(const FStardustCraftInput& NewInput)
{
	Input = NewInput;
	Input.Steer = FMath::Clamp(Input.Steer, -1.0f, 1.0f);
	Input.Throttle = FMath::Clamp(Input.Throttle, 0.0f, 1.0f);
	Input.AirPitch = FMath::Clamp(Input.AirPitch, -1.0f, 1.0f);
}

void UStardustCraftMovementComponent::SetBodyComponent(UPrimitiveComponent* NewBody)
{
	BodyComponent = NewBody;
	InitializeBody();
}

void UStardustCraftMovementComponent::PlaceCraft(const FVector& PositionCm, const FRotator& Rotation, float SpeedMPerSecond)
{
	InitializeBody();
	if (!BodyComponent)
	{
		return;
	}

	const FQuat SpawnRotation = Rotation.Quaternion();
	if (GetOwner())
	{
		GetOwner()->SetActorLocationAndRotation(PositionCm, SpawnRotation, false, nullptr, ETeleportType::TeleportPhysics);
	}
	else
	{
		BodyComponent->SetWorldLocationAndRotation(PositionCm, SpawnRotation, false, nullptr, ETeleportType::TeleportPhysics);
	}
	BodyComponent->SetPhysicsLinearVelocity(SpawnRotation.RotateVector(FVector::ForwardVector) * SpeedMPerSecond * CmPerMeter);
	BodyComponent->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
	LastCommandedSpin = FVector::ZeroVector;
	YawRate = 0.0f;
	Telemetry.AirTimeSeconds = 0.0f;
	Telemetry.LastLandingSpeedMPerSecond = 0.0f;
	Telemetry.UpRateSmoothed = 0.0f;
	Nitro = 1.0f;
	bNitroLocked = false;
	HoverSensor.Reset(SpawnRotation.RotateVector(FVector::UpVector));
	LastUp = SpawnRotation.RotateVector(FVector::UpVector);
	bWasGrounded = true;
}

void UStardustCraftMovementComponent::AddNitro(float Amount)
{
	Nitro = FMath::Clamp(Nitro + Amount, 0.0f, 1.0f);
	if (Nitro >= Tuning.NitroRestart)
	{
		bNitroLocked = false;
	}
}

void UStardustCraftMovementComponent::StepCraft(float DeltaSeconds)
{
	if (!BodyComponent || !BodyComponent->IsSimulatingPhysics() || !GetWorld() || DeltaSeconds <= 0.0f)
	{
		return;
	}

	const FVector PositionCm = BodyComponent->GetComponentLocation();
	const FQuat Rotation = BodyComponent->GetComponentQuat();
	FVector VelocityMPerSecond = BodyComponent->GetPhysicsLinearVelocity() / CmPerMeter;
	const FVector Up = Rotation.RotateVector(FVector::UpVector);
	const FVector Forward = Rotation.RotateVector(FVector::ForwardVector);
	const float SpeedMPerSecond = VelocityMPerSecond.Size();
	HoverSensor.Sample(GetWorld(), PositionCm, Rotation, VelocityMPerSecond * CmPerMeter, Tuning, DeltaSeconds, GetOwner());
	const FStardustHoverState& Sensor = HoverSensor.GetState();
	const bool bGrounded = Sensor.Hits >= 2 && Sensor.HeightM < Tuning.HoverHeightM + Tuning.CaptureRangeM;
	const FVector SurfaceNormal = bGrounded ? Sensor.Normal : FVector::UpVector;
	const float Steer = FMath::Clamp(Input.Steer, -1.0f, 1.0f);
	const bool bWasDrifting = Telemetry.bDrifting;
	FVector Acceleration = FVector::DownVector * Tuning.Gravity;
	bool bDrifting = false;
	bool bBraking = false;

	Telemetry.bBoosting = Input.bBoost && Nitro > 0.0f && !bNitroLocked;
	if (Telemetry.bBoosting)
	{
		Nitro = FMath::Max(0.0f, Nitro - DeltaSeconds / FMath::Max(0.1f, Tuning.NitroSeconds));
		if (Nitro <= 0.0f)
		{
			bNitroLocked = true;
		}
	}
	else
	{
		Nitro = FMath::Min(1.0f, Nitro + DeltaSeconds * (Tuning.NitroRegen + (bWasDrifting ? Tuning.NitroDriftRegen : 0.0f) + (Telemetry.bGrounded ? 0.0f : Tuning.NitroAirRegen)));
		if (Nitro >= Tuning.NitroRestart)
		{
			bNitroLocked = false;
		}
	}

	FVector SurfaceForward = FVector::ZeroVector;
	if (bGrounded)
	{
		const float NormalVelocity = FVector::DotProduct(VelocityMPerSecond, SurfaceNormal);
		const float HoverAcceleration = FMath::Clamp(Tuning.GetSpringK() * (Tuning.HoverHeightM - Sensor.HeightM) - Tuning.GetSpringC() * NormalVelocity,
			-Tuning.GetAdhesion(SpeedMPerSecond), Tuning.MaxHoverAccel);
		Acceleration += SurfaceNormal * HoverAcceleration;
		SurfaceForward = ProjectOnPlane(Forward, SurfaceNormal).GetSafeNormal(SMALL_NUMBER, Forward);
		const float ForwardSpeed = FVector::DotProduct(VelocityMPerSecond, SurfaceForward);
		Telemetry.ForwardSpeedMPerSecond = ForwardSpeed;

		if (Input.bDrift && ((bWasDrifting && SpeedMPerSecond > 18.0f) || (FMath::Abs(Steer) > 0.25f && SpeedMPerSecond > 25.0f)))
		{
			bDrifting = true;
		}
		else if (Input.bBrake || Input.bDrift)
		{
			bBraking = true;
		}

		const float TopSpeed = Tuning.TopSpeed * Sensor.Traits.TopSpeed * (Telemetry.bBoosting ? Tuning.BoostTopMul : 1.0f);
		float Thrust = 0.0f;
		if (ForwardSpeed < TopSpeed)
		{
			const float SpeedRatio = FMath::Max(0.0f, ForwardSpeed) / TopSpeed;
			Thrust = Tuning.Accel * (1.0f - SpeedRatio * SpeedRatio)
				+ (Telemetry.bBoosting ? Tuning.BoostAccel * (1.0f - SpeedRatio) : 0.0f);
		}
		else
		{
			Thrust = -(ForwardSpeed - TopSpeed) * Tuning.OverspeedBleed;
		}
		Acceleration += SurfaceForward * (Thrust * FMath::Clamp(Input.Throttle, 0.0f, 1.0f));
		if (bBraking && ForwardSpeed > 0.0f)
		{
			Acceleration -= SurfaceForward * FMath::Min(Tuning.BrakeDecel, ForwardSpeed / DeltaSeconds);
		}
		else if (Input.Throttle < 0.05f && ForwardSpeed > 0.0f)
		{
			Acceleration -= SurfaceForward * FMath::Min(Tuning.CoastDecel, ForwardSpeed / DeltaSeconds);
		}
		if (bDrifting && SpeedMPerSecond > 1.0f)
		{
			Acceleration -= VelocityMPerSecond.GetSafeNormal() * Tuning.DriftDecel;
		}
		if (Sensor.Traits.Drag > 0.0f && SpeedMPerSecond > 1.0f)
		{
			const float SpeedFactor = SpeedMPerSecond / Tuning.TopSpeed;
			const float SurfaceDecel = FMath::Min(Sensor.Traits.Drag * SpeedFactor * SpeedFactor + Sensor.Traits.Drag * 0.25f, SpeedMPerSecond / DeltaSeconds);
			Acceleration -= VelocityMPerSecond / SpeedMPerSecond * SurfaceDecel;
		}
	}
	else
	{
		Telemetry.ForwardSpeedMPerSecond = FVector::DotProduct(VelocityMPerSecond, Forward);
		FVector AirForward = Forward;
		AirForward.Z = FMath::Min(AirForward.Z, 0.2f);
		const float SpeedRatio = FMath::Clamp(Telemetry.ForwardSpeedMPerSecond / Tuning.TopSpeed, 0.0f, 1.0f);
		Acceleration += AirForward.GetSafeNormal(SMALL_NUMBER, Forward) * (Tuning.Accel * Tuning.AirThrust * (1.0f - SpeedRatio * SpeedRatio) * FMath::Clamp(Input.Throttle, 0.0f, 1.0f));
	}

	Acceleration -= VelocityMPerSecond * (Tuning.AeroDrag * SpeedMPerSecond);
	VelocityMPerSecond += Acceleration * DeltaSeconds;

	if (bGrounded)
	{
		FVector TangentialVelocity = ProjectOnPlane(VelocityMPerSecond, SurfaceNormal);
		const float TangentialSpeed = TangentialVelocity.Size();
		SurfaceForward = ProjectOnPlane(Forward, SurfaceNormal).GetSafeNormal(SMALL_NUMBER, Forward);
		SlipAngleRadians = 0.0f;
		if (TangentialSpeed > 1.0f && FVector::DotProduct(TangentialVelocity, SurfaceForward) > 0.0f)
		{
			const float SignedAngle = FMath::Atan2(FVector::DotProduct(SurfaceNormal, FVector::CrossProduct(TangentialVelocity, SurfaceForward)),
				FVector::DotProduct(TangentialVelocity, SurfaceForward));
			SlipAngleRadians = SignedAngle;
			GripBlend = bDrifting ? 0.0f : FMath::Min(1.0f, GripBlend + DeltaSeconds / FMath::Max(0.05f, Tuning.DriftRecoverTime));
			float LateralMax = FMath::Lerp(Tuning.DriftLateralMax, Tuning.GripLateralMax, GripBlend) * (bBraking ? Tuning.BrakeGripMul : 1.0f);
			float Redirect = FMath::Lerp(Tuning.DriftRedirect, Tuning.GripRedirect, GripBlend);
			const float SlipOverDegrees = FMath::Abs(SignedAngle) * (180.0f / PI) - Tuning.DriftMaxSlip;
			if (SlipOverDegrees > 0.0f)
			{
				Redirect *= 1.0f + SlipOverDegrees / 8.0f;
				LateralMax *= 1.0f + SlipOverDegrees / 15.0f;
			}
			const float RateCap = LateralMax * Tuning.GetGripFactor(TangentialSpeed) * Sensor.Traits.Grip / TangentialSpeed;
			const float Rate = FMath::Min(Redirect, RateCap);
			const float AppliedAngle = FMath::Clamp(SignedAngle, -Rate * DeltaSeconds, Rate * DeltaSeconds);
			const FVector RedirectedVelocity = FQuat(SurfaceNormal, AppliedAngle).RotateVector(TangentialVelocity);
			VelocityMPerSecond += RedirectedVelocity - TangentialVelocity;
			const FVector SurfaceRight = FVector::CrossProduct(SurfaceNormal, SurfaceForward);
			const float LateralVelocity = FVector::DotProduct(VelocityMPerSecond, SurfaceRight);
			VelocityMPerSecond -= SurfaceRight * LateralVelocity * FMath::Clamp(FMath::Lerp(0.18f, 1.0f, GripBlend) * Tuning.GripFriction * Tuning.GetGripFactor(TangentialSpeed) * DeltaSeconds, 0.0f, 1.0f);
		}
		Telemetry.LateralSpeedMPerSecond = FVector::DotProduct(VelocityMPerSecond, FVector::CrossProduct(SurfaceNormal, SurfaceForward));
	}

	Telemetry.bDrifting = bDrifting;
	Telemetry.bMiniTurbo = false;
	if (bDrifting && bGrounded && SpeedMPerSecond > 30.0f && FMath::Abs(SlipAngleRadians) > 0.15f)
	{
		DriftChargeSeconds = FMath::Min(DriftChargeSeconds + DeltaSeconds, 2.5f);
	}
	else if (!bDrifting)
	{
		if (DriftChargeSeconds > 0.6f && bGrounded)
		{
			const FVector BoostForward = ProjectOnPlane(Forward, SurfaceNormal).GetSafeNormal(SMALL_NUMBER, Forward);
			VelocityMPerSecond += BoostForward * (Tuning.DriftBoost * FMath::Clamp(DriftChargeSeconds / 2.0f, 0.35f, 1.0f));
			Telemetry.bMiniTurbo = true;
		}
		DriftChargeSeconds = 0.0f;
	}

	const FVector DesiredUp = bGrounded ? SurfaceNormal : FindAirTargetUp(PositionCm, VelocityMPerSecond, Up);
	const float RateLimitRadians = FMath::DegreesToRadians(bGrounded ? Tuning.AlignRate : Tuning.AirAlignRate);
	const FVector AlignAxis = FVector::CrossProduct(Up, DesiredUp);
	const float AlignSin = AlignAxis.Size();
	FVector SpinAlign = FVector::ZeroVector;
	if (AlignSin > 1.0e-5f)
	{
		const float AlignAngle = FMath::Atan2(AlignSin, FVector::DotProduct(Up, DesiredUp));
		SpinAlign = AlignAxis / AlignSin * FMath::Min(AlignAngle / FMath::Max(DeltaSeconds, Tuning.AlignTime), RateLimitRadians);
	}
	const float TurnMultiplier = bDrifting ? Tuning.DriftTurnMul : bBraking ? Tuning.BrakeTurnMul : 1.0f;
	const float TurnRate = Tuning.GetTurnRate(SpeedMPerSecond) * TurnMultiplier * (bGrounded ? 1.0f : Tuning.AirTurnMul);
	YawRate = FMath::Lerp(YawRate, Steer * TurnRate, Damp(Tuning.SteerResponse, DeltaSeconds));
	if (bDrifting && !bWasDrifting)
	{
		YawRate += FMath::Sign(Steer) * Tuning.DriftKick;
	}
	if (bGrounded && FMath::Abs(SlipAngleRadians) * (180.0f / PI) > Tuning.DriftMaxSlip && YawRate * SlipAngleRadians > 0.0f)
	{
		YawRate = FMath::Lerp(YawRate, 0.0f, Damp(8.0f, DeltaSeconds));
	}
	FVector Spin = SpinAlign + Up * YawRate;
	if (!bGrounded)
	{
		Spin += Rotation.RotateVector(FVector::RightVector) * (Input.AirPitch * Tuning.AirPitchRate);
	}
	const FVector ExternalSpin = BodyComponent->GetPhysicsAngularVelocityInRadians() - LastCommandedSpin;
	Spin += ExternalSpin * FMath::Exp(-Tuning.StabilityRecover * DeltaSeconds);
	LastCommandedSpin = Spin;

	BodyComponent->SetPhysicsLinearVelocity(VelocityMPerSecond * CmPerMeter);
	BodyComponent->SetPhysicsAngularVelocityInRadians(Spin);
	if (bGrounded && !bWasGrounded && Telemetry.AirTimeSeconds > 0.08f)
	{
		Telemetry.LastLandingSpeedMPerSecond = -FVector::DotProduct(VelocityMPerSecond, SurfaceNormal);
		if (Telemetry.LastLandingSpeedMPerSecond > Tuning.LandingSoft)
		{
			OnLanded.Broadcast(Telemetry.LastLandingSpeedMPerSecond);
		}
	}
	Telemetry.AirTimeSeconds = bGrounded ? 0.0f : Telemetry.AirTimeSeconds + DeltaSeconds;
	bWasGrounded = bGrounded;
	Telemetry.bGrounded = bGrounded;
	Telemetry.SpeedMPerSecond = VelocityMPerSecond.Size();
	Telemetry.UpRateDegreesPerSecond = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(LastUp, Up), -1.0f, 1.0f))) / DeltaSeconds;
	Telemetry.UpRateSmoothed = FMath::Lerp(Telemetry.UpRateSmoothed, Telemetry.UpRateDegreesPerSecond, Damp(10.0f, DeltaSeconds));
	Telemetry.Nitro = Nitro;
	Telemetry.bNitroLocked = bNitroLocked;
	LastUp = Up;
	PreVelocityCmPerSecond = VelocityMPerSecond * CmPerMeter;
}

FVector UStardustCraftMovementComponent::FindAirTargetUp(const FVector& PositionCm, const FVector& VelocityMPerSecond, const FVector& CurrentUp) const
{
	const FVector Gravity = FVector::DownVector * Tuning.Gravity;
	FVector PreviousPointCm = PositionCm;
	float PreviousTime = 0.0f;
	FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(StardustLandingPrediction), true);
	QueryParams.AddIgnoredActor(GetOwner());
	for (int32 Index = 1; Index <= 6; ++Index)
	{
		const float SampleTime = Index * 0.25f;
		const FVector BallisticOffsetM = VelocityMPerSecond * SampleTime + 0.5f * SampleTime * SampleTime * Gravity;
		const FVector CurrentPointCm = PositionCm + BallisticOffsetM * CmPerMeter;
		const FVector Segment = CurrentPointCm - PreviousPointCm;
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, PreviousPointCm, CurrentPointCm + CurrentUp * Tuning.HoverHeightM * CmPerMeter,
			ECC_GameTraceChannel1, QueryParams))
		{
			const float HitFraction = FMath::Clamp(Hit.Distance / FMath::Max(1.0f, Segment.Size()), 0.0f, 1.0f);
			const float HitTime = PreviousTime + (SampleTime - PreviousTime) * HitFraction;
			const float Weight = 1.0f - FMath::Clamp(HitTime / 1.4f, 0.0f, 1.0f);
			return FStardustHoverSensor::SlerpNormals(FVector::UpVector, Hit.ImpactNormal, 0.35f + 0.65f * Weight);
		}
		PreviousPointCm = CurrentPointCm;
		PreviousTime = SampleTime;
	}
	return FVector::UpVector;
}

FVector UStardustCraftMovementComponent::ConvertUnityVectorToUnreal(const FVector& UnityVector)
{
	return FVector(UnityVector.Z, UnityVector.X, UnityVector.Y);
}

FVector UStardustCraftMovementComponent::ProjectOnPlane(const FVector& Vector, const FVector& PlaneNormal)
{
	return Vector - FVector::DotProduct(Vector, PlaneNormal) * PlaneNormal;
}

float UStardustCraftMovementComponent::Damp(float Lambda, float DeltaSeconds)
{
	return 1.0f - FMath::Exp(-Lambda * DeltaSeconds);
}
