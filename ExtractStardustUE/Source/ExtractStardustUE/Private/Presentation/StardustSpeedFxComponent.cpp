#include "Presentation/StardustSpeedFxComponent.h"

#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Vehicle/StardustCraftMovementComponent.h"

namespace
{
	constexpr float CmPerMeter = 100.0f;
	constexpr float AccelerationForFullPitchMPerSecondSquared = 12.0f;
	constexpr float LateralSpeedForFullDriftMPerSecond = 20.0f;
	constexpr float ImpactShakeFrequencyHz = 18.0f;
}

UStardustSpeedFxComponent::UStardustSpeedFxComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UStardustSpeedFxComponent::BeginPlay()
{
	Super::BeginPlay();

	if (AActor* Owner = GetOwner())
	{
		CraftMovement = Owner->FindComponentByClass<UStardustCraftMovementComponent>();
		CameraArm = Owner->FindComponentByClass<USpringArmComponent>();
		ChaseCamera = Owner->FindComponentByClass<UCameraComponent>();
		LastVelocityMPerSecond = Owner->GetVelocity() / CmPerMeter;
	}

	if (CameraArm)
	{
		BaseArmLengthCm = CameraArm->TargetArmLength;
		BaseArmRotation = CameraArm->GetRelativeRotation();
		BaseCameraLagSpeed = CameraArm->CameraLagSpeed;
	}

	if (ChaseCamera)
	{
		ChaseCamera->SetFieldOfView(BaseFOV);
		ChaseCamera->PostProcessBlendWeight = 1.0f;
	}

	if (CraftMovement)
	{
		CraftMovement->OnDamaged.AddDynamic(this, &UStardustSpeedFxComponent::HandleCraftDamaged);
	}
}

void UStardustSpeedFxComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (CraftMovement)
	{
		CraftMovement->OnDamaged.RemoveDynamic(this, &UStardustSpeedFxComponent::HandleCraftDamaged);
	}

	Super::EndPlay(EndPlayReason);
}

void UStardustSpeedFxComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	if (DeltaTime <= 0.0f || !GetOwner())
	{
		return;
	}

	const FVector VelocityMPerSecond = GetOwner()->GetVelocity() / CmPerMeter;
	const float ForwardAcceleration = FVector::DotProduct(
		(VelocityMPerSecond - LastVelocityMPerSecond) / DeltaTime,
		GetOwner()->GetActorForwardVector());
	LastVelocityMPerSecond = VelocityMPerSecond;

	const float SpeedMPerSecond = CraftMovement ? CraftMovement->Telemetry.SpeedMPerSecond : VelocityMPerSecond.Size();
	const float SpeedRatio = FMath::Clamp(SpeedMPerSecond / FMath::Max(1.0f, MaxSpeedForEffectsMPerSecond), 0.0f, 1.0f);
	const float BoostTarget = CraftMovement && CraftMovement->Telemetry.bBoosting ? 1.0f : 0.0f;
	const float LateralSpeed = CraftMovement ? CraftMovement->Telemetry.LateralSpeedMPerSecond : 0.0f;
	const float DriftTarget = CraftMovement
		? FMath::Max(CraftMovement->Telemetry.bDrifting ? 0.35f : 0.0f,
			FMath::Clamp(FMath::Abs(LateralSpeed) / LateralSpeedForFullDriftMPerSecond, 0.0f, 1.0f))
		: 0.0f;
	const float AccelerationTarget = FMath::Clamp(
		ForwardAcceleration / AccelerationForFullPitchMPerSecondSquared, -1.0f, 1.0f);

	SmoothedSpeedRatio = FMath::FInterpTo(SmoothedSpeedRatio, SpeedRatio, DeltaTime, 3.0f);
	SmoothedBoostStrength = FMath::FInterpTo(SmoothedBoostStrength, BoostTarget, DeltaTime, 5.0f);
	SmoothedDriftStrength = FMath::FInterpTo(SmoothedDriftStrength, DriftTarget, DeltaTime, 4.0f);
	SmoothedAccelerationRatio = FMath::FInterpTo(SmoothedAccelerationRatio, AccelerationTarget, DeltaTime, 3.0f);

	float ImpactPitchOffset = 0.0f;
	float ImpactRollOffset = 0.0f;
	const float ShakeDuration = FMath::Max(0.05f, ImpactShakeDurationSeconds);
	if (CameraArm && ImpactShakeElapsedSeconds < ShakeDuration)
	{
		ImpactShakeElapsedSeconds += DeltaTime;
		const float Remaining = 1.0f - FMath::Clamp(ImpactShakeElapsedSeconds / ShakeDuration, 0.0f, 1.0f);
		ImpactPitchOffset = FMath::Sin(ImpactShakeElapsedSeconds * 2.0f * PI * ImpactShakeFrequencyHz)
			* MaxImpactShakeDegrees * ImpactShakeStrength * Remaining;
		ImpactRollOffset = FMath::Sin(ImpactShakeElapsedSeconds * 2.0f * PI * 13.0f + 1.2f)
			* MaxImpactShakeDegrees * 0.65f * ImpactShakeStrength * Remaining;
	}

	if (CameraArm)
	{
		const float TargetArmLength = BaseArmLengthCm
			+ MaxArmExtensionCm * SmoothedSpeedRatio
			+ BoostArmExtensionCm * SmoothedBoostStrength
			- DriftArmCompressionCm * SmoothedDriftStrength;
		CameraArm->TargetArmLength = FMath::FInterpTo(CameraArm->TargetArmLength, TargetArmLength, DeltaTime, 2.5f);

		FRotator TargetRotation = BaseArmRotation;
		TargetRotation.Pitch -= MaxSpeedPitchOffsetDegrees * SmoothedSpeedRatio;
		TargetRotation.Pitch -= AccelerationPitchOffsetDegrees * SmoothedAccelerationRatio;
		TargetRotation.Roll += FMath::Sign(LateralSpeed) * MaxDriftRollDegrees * SmoothedDriftStrength;
		TargetRotation.Pitch += ImpactPitchOffset;
		TargetRotation.Roll += ImpactRollOffset;
		CameraArm->SetRelativeRotation(FMath::RInterpTo(CameraArm->GetRelativeRotation(), TargetRotation, DeltaTime, 3.5f));

		const float TargetLagSpeed = FMath::Max(1.0f, BaseCameraLagSpeed - MaxSpeedCameraLagReduction * SmoothedSpeedRatio);
		CameraArm->CameraLagSpeed = FMath::FInterpTo(CameraArm->CameraLagSpeed, TargetLagSpeed, DeltaTime, 2.0f);
	}

	if (ChaseCamera)
	{
		const float TargetFOV = FMath::Clamp(
			BaseFOV + (MaxFOV - BaseFOV) * SmoothedSpeedRatio + BoostFOVBonus * SmoothedBoostStrength,
			BaseFOV, 120.0f);
		ChaseCamera->SetFieldOfView(FMath::FInterpTo(ChaseCamera->FieldOfView, TargetFOV, DeltaTime, 3.0f));

		FPostProcessSettings& PostProcess = ChaseCamera->PostProcessSettings;
		PostProcess.bOverride_SceneFringeIntensity = true;
		PostProcess.SceneFringeIntensity = BoostChromaticIntensity * SmoothedBoostStrength;
		PostProcess.bOverride_VignetteIntensity = true;
		PostProcess.VignetteIntensity = FMath::Clamp(
			BaseVignetteIntensity + SpeedVignetteIntensity * SmoothedSpeedRatio + BoostVignetteIntensity * SmoothedBoostStrength,
			0.0f, 1.0f);
		PostProcess.bOverride_MotionBlurAmount = true;
		PostProcess.MotionBlurAmount = FMath::Clamp(
			MaxSpeedMotionBlur * FMath::Square(SmoothedSpeedRatio) + BoostMotionBlur * SmoothedBoostStrength,
			0.0f, 1.0f);
	}
}

void UStardustSpeedFxComponent::HandleCraftDamaged(float Damage)
{
	ImpactShakeStrength = FMath::Clamp(Damage / 30.0f, 0.15f, 1.0f);
	ImpactShakeElapsedSeconds = 0.0f;
}
