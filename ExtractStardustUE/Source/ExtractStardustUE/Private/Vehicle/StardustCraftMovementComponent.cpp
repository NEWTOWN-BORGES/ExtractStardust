#include "Vehicle/StardustCraftMovementComponent.h"

#include "Components/PrimitiveComponent.h"
#include "Course/StardustCourseComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Game/StardustRaceProgressComponent.h"
#include "StardustGameMode.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace
{
	constexpr float CraftCmPerMeter = 100.0f;
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
	Super::BeginPlay();
	InitializeBody();
	if (GetOwner())
	{
		RaceProgressComponent = GetOwner()->FindComponentByClass<UStardustRaceProgressComponent>();
	}
}

void UStardustCraftMovementComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (bAutoStep)
	{
#if !UE_BUILD_SHIPPING
		static const bool bAutoDriveTest = FParse::Param(FCommandLine::Get(), TEXT("StardustAutoDrive"));
		const APawn* OwnerPawn = Cast<APawn>(GetOwner());
		if (bAutoDriveTest && OwnerPawn && OwnerPawn->IsPlayerControlled())
		{
			Input.Throttle = 1.0f;
			static bool bFallInjected = false;
			if (!bFallInjected && GetWorld() && GetWorld()->GetTimeSeconds() > 15.0 && BodyComponent)
			{
				bFallInjected = true;
				UE_LOG(LogTemp, Display, TEXT("Auto-drive test: throwing the craft 800 m off the course to test the fall safety net."));
				PlaceCraft(BodyComponent->GetComponentLocation() + FVector(0.0f, 80000.0f, 20000.0f), BodyComponent->GetComponentRotation(), 0.0f);
			}
			if (RaceProgressComponent && RaceProgressComponent->State == EStardustRaceState::Waiting)
			{
				if (RaceProgressComponent->StartRace() && GetWorld())
				{
					if (AStardustGameMode* GameMode = Cast<AStardustGameMode>(GetWorld()->GetAuthGameMode()))
					{
						GameMode->StartTestBots();
					}
				}
			}
		}
#endif
		// Loading hitches produce multi-second frames; a huge step would throw the craft through the track.
		const float StepSeconds = FMath::Min(DeltaTime, 1.0f / 30.0f);
		StepCraft(StepSeconds);
		UpdateSafetyNet(StepSeconds);
	}
	ImpactCooldownSeconds = FMath::Max(0.0f, ImpactCooldownSeconds - DeltaTime);
	if (GEngine && GetWorld() && GetWorld()->IsGameWorld())
	{
		const FString TelemetryText = FString::Printf(TEXT("EXTRACT: STARDUST  |  %3.0f km/h  |  Nitro %3.0f%%  |  Hull %3.0f%%  |  %s"),
			Telemetry.SpeedMPerSecond * 3.6f, Telemetry.Nitro * 100.0f, Telemetry.HullIntegrity,
			Telemetry.bGrounded ? TEXT("HOVER") : TEXT("AIR"));
		GEngine->AddOnScreenDebugMessage(817430, 0.0f, FColor::White, TelemetryText);
		const FStardustHoverState& HoverState = HoverSensor.GetState();
		const FString ContactText = HoverState.Hits > 0
			? FString::Printf(TEXT("GROUND CONTACT  %d/5  |  %.2f m"), HoverState.Hits, HoverState.HeightM)
			: TEXT("GROUND CONTACT  0/5  |  NO HIT");
		GEngine->AddOnScreenDebugMessage(817434, 0.0f, HoverState.Hits >= 2 ? FColor::Green : FColor::Red, ContactText);
		GEngine->AddOnScreenDebugMessage(817431, 0.0f, FColor::Yellow,
			TEXT("W: acelerar  A-D: virar  S: travar  Shift: boost  Espaco: drift  R: repor nave  Esc: SAIR"));
		if (RaceProgressComponent && RaceProgressComponent->State == EStardustRaceState::Racing)
		{
			const int32 Minutes = FMath::FloorToInt(RaceProgressComponent->ElapsedTimeSeconds / 60.0f);
			const float Seconds = FMath::Fmod(RaceProgressComponent->ElapsedTimeSeconds, 60.0f);
			const FString RaceText = FString::Printf(TEXT("CORRIDA  %02d:%05.2f  |  CP %02d/%02d  |  %0.1f / %0.1f km"),
				Minutes, Seconds, RaceProgressComponent->CurrentCheckpoint, RaceProgressComponent->CheckpointCount,
				RaceProgressComponent->RaceDistanceM / 1000.0f, RaceProgressComponent->FinishDistanceM / 1000.0f);
			GEngine->AddOnScreenDebugMessage(817432, 0.0f, FColor::Cyan, RaceText);
		}
		else if (RaceProgressComponent && RaceProgressComponent->State == EStardustRaceState::Extracted)
		{
			const int32 Minutes = FMath::FloorToInt(RaceProgressComponent->FinishTimeSeconds / 60.0f);
			const float Seconds = FMath::Fmod(RaceProgressComponent->FinishTimeSeconds, 60.0f);
			GEngine->AddOnScreenDebugMessage(817432, 0.0f, FColor::Green,
				FString::Printf(TEXT("EXTRACTED  %02d:%05.2f"), Minutes, Seconds));
		}
		else if (RaceProgressComponent && RaceProgressComponent->State == EStardustRaceState::Abandoned)
		{
			const TCHAR* FailureState = Telemetry.bDestroyed ? TEXT("DESTROYED") : TEXT("STRANDED");
			GEngine->AddOnScreenDebugMessage(817432, 0.0f, FColor::Red, FString::Printf(TEXT("RACE FAILED  |  %s"), FailureState));
		}
		else if (RaceProgressComponent && RaceProgressComponent->Course && RaceProgressComponent->Course->StationCount >= 2)
		{
			GEngine->AddOnScreenDebugMessage(817432, 0.0f, FColor::Cyan, TEXT("CORRIDA PRONTA  |  acelera para iniciar"));
		}
		else
		{
			GEngine->AddOnScreenDebugMessage(817432, 0.0f, FColor::Orange, TEXT("SEM PISTA: coloca o ficheiro RDDC em Content/Tracks"));
		}
		if (RaceProgressComponent && (RaceProgressComponent->State == EStardustRaceState::Racing ||
			RaceProgressComponent->State == EStardustRaceState::Abandoned) && bEnableRaceVitals)
		{
			const TCHAR* VitalState = Telemetry.bDestroyed ? TEXT("DESTROYED") : Telemetry.bStranded ? TEXT("STRANDED")
				: Telemetry.bOverheated ? TEXT("OVERHEAT") : Telemetry.bFuelEmpty ? TEXT("NO FUEL") : TEXT("SYSTEMS NOMINAL");
			GEngine->AddOnScreenDebugMessage(817433, 0.0f, Telemetry.bDestroyed || Telemetry.bStranded ? FColor::Red : FColor::Silver,
				FString::Printf(TEXT("FUEL %02.0f%%  |  HEAT %02.0f%%  |  %s"), Telemetry.FuelFraction * 100.0f, Telemetry.Heat, VitalState));
		}
	}
}

void UStardustCraftMovementComponent::UpdateSafetyNet(float DeltaSeconds)
{
	if (!BodyComponent || !BodyComponent->IsSimulatingPhysics())
	{
		return;
	}
	const FVector PositionCm = BodyComponent->GetComponentLocation();
	if (!bHasSafePoint)
	{
		bHasSafePoint = true;
		SafePositionCm = PositionCm;
		SafeRotation = BodyComponent->GetComponentQuat();
	}
	if (HoverSensor.GetState().Hits >= 3)
	{
		UngroundedSeconds = 0.0f;
		SafePositionCm = PositionCm;
		SafeRotation = BodyComponent->GetComponentQuat();
		return;
	}
	UngroundedSeconds += DeltaSeconds;
	constexpr float MaxFallBelowSafeCm = 8000.0f;
	constexpr float MaxUngroundedSeconds = 12.0f;
	if (PositionCm.Z < SafePositionCm.Z - MaxFallBelowSafeCm || UngroundedSeconds > MaxUngroundedSeconds)
	{
		UE_LOG(LogTemp, Display, TEXT("Safety net trigger: now %s (Z %.1f m), ungrounded %.1f s, last safe Z %.1f m, t=%.1f s."),
			*PositionCm.ToCompactString(), PositionCm.Z / CraftCmPerMeter, UngroundedSeconds, SafePositionCm.Z / CraftCmPerMeter,
			GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0);
		RecoverToSafePoint();
	}
}

bool UStardustCraftMovementComponent::RecoverToSafePoint()
{
	if (!bHasSafePoint || !BodyComponent)
	{
		return false;
	}
	FRotator Level = SafeRotation.Rotator();
	Level.Roll = 0.0f;
	Level.Pitch = 0.0f;
	PlaceCraft(SafePositionCm + FVector(0.0f, 0.0f, 150.0f), Level, 15.0f);
	UngroundedSeconds = 0.0f;
	UE_LOG(LogTemp, Display, TEXT("Safety net: craft recovered to last grounded point %s."), *SafePositionCm.ToCompactString());
	return true;
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
	BodyComponent->SetCenterOfMass(ConvertUnityVectorToUnreal(Tuning.CenterOfMassM) * CraftCmPerMeter);
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
	BodyComponent->SetPhysicsLinearVelocity(SpawnRotation.RotateVector(FVector::ForwardVector) * SpeedMPerSecond * CraftCmPerMeter);
	BodyComponent->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
	LastCommandedSpin = FVector::ZeroVector;
	YawRate = 0.0f;
	Telemetry.AirTimeSeconds = 0.0f;
	Telemetry.LastLandingSpeedMPerSecond = 0.0f;
	Telemetry.LastImpactSpeedMPerSecond = 0.0f;
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

void UStardustCraftMovementComponent::ApplyRaceVitalLimits(float DeltaSeconds, float SpeedMPerSecond)
{
	const bool bRaceActive = bEnableRaceVitals && RaceProgressComponent && RaceProgressComponent->State == EStardustRaceState::Racing;
	if (!bRaceActive)
	{
		return;
	}

	const float HeatGain = (Telemetry.bBoosting ? 14.0f : 0.0f) + (Telemetry.bDrifting ? 3.0f : 0.0f);
	const float HeatLoss = 6.0f * (Telemetry.bBoosting ? 0.3f : 1.0f);
	Telemetry.Heat = FMath::Clamp(Telemetry.Heat + (HeatGain - HeatLoss) * DeltaSeconds, 0.0f, 120.0f);
	Telemetry.bOverheated = Telemetry.Heat >= 100.0f;
	if (Telemetry.bOverheated)
	{
		Input.bBoost = false;
		const float Damage = 2.0f * DeltaSeconds;
		Telemetry.HullIntegrity = FMath::Max(0.0f, Telemetry.HullIntegrity - Damage);
	}

	Telemetry.bFuelEmpty = Telemetry.FuelFraction <= 0.0f;
	if (Telemetry.bFuelEmpty || Telemetry.bDestroyed || Telemetry.bStranded)
	{
		Input.Throttle = 0.0f;
		Input.bBoost = false;
	}

	Telemetry.bDestroyed = Telemetry.HullIntegrity <= 0.0f;
	if (Telemetry.bDestroyed)
	{
		Input.Throttle = 0.0f;
		Input.bBoost = false;
		Input.bBrake = true;
	}

	if (Telemetry.bFuelEmpty && SpeedMPerSecond < 4.0f)
	{
		StrandedSeconds += DeltaSeconds;
		Telemetry.bStranded = StrandedSeconds > 3.0f;
	}
	else
	{
		StrandedSeconds = 0.0f;
		Telemetry.bStranded = false;
	}
	if ((Telemetry.bDestroyed || Telemetry.bStranded) && RaceProgressComponent->State == EStardustRaceState::Racing)
	{
		RaceProgressComponent->AbandonRace();
	}
}

void UStardustCraftMovementComponent::UpdateRaceFuel(float DeltaSeconds, float SpeedMPerSecond)
{
	if (!bEnableRaceVitals || !RaceProgressComponent || RaceProgressComponent->State != EStardustRaceState::Racing)
	{
		return;
	}

	const float ReferenceSeconds = FMath::Max(60.0f, RaceProgressComponent->FinishDistanceM / 100.0f * 0.92f);
	const float SpeedRatio = FMath::Clamp(SpeedMPerSecond / FMath::Max(1.0f, Tuning.TopSpeed), 0.0f, 1.0f);
	const float BoostMultiplier = Telemetry.bBoosting ? 2.2f : 1.0f;
	const float FuelUse = FMath::Clamp(Input.Throttle, 0.0f, 1.0f) * (0.55f + 0.45f * SpeedRatio) * BoostMultiplier;
	Telemetry.FuelFraction = FMath::Max(0.0f, Telemetry.FuelFraction - FuelUse * DeltaSeconds / ReferenceSeconds);
}

void UStardustCraftMovementComponent::ApplyImpactSpeed(float ImpactSpeedMPerSecond)
{
	if (!FMath::IsFinite(ImpactSpeedMPerSecond) || ImpactSpeedMPerSecond < Tuning.ImpactMin || ImpactCooldownSeconds > 0.0f)
	{
		return;
	}

	Telemetry.LastImpactSpeedMPerSecond = ImpactSpeedMPerSecond;
	const float Damage = (ImpactSpeedMPerSecond - Tuning.ImpactMin) * 1.1f;
	ApplyDamage(Damage);
	ImpactCooldownSeconds = 0.25f;
}

void UStardustCraftMovementComponent::ApplyDamage(float Damage)
{
	if (!FMath::IsFinite(Damage) || Damage <= 0.0f)
	{
		return;
	}
	const float AppliedDamage = FMath::Min(Damage, Telemetry.HullIntegrity);
	Telemetry.HullIntegrity = FMath::Max(0.0f, Telemetry.HullIntegrity - AppliedDamage);
	if (AppliedDamage > 0.0f)
	{
		OnDamaged.Broadcast(AppliedDamage);
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
	FVector VelocityMPerSecond = BodyComponent->GetPhysicsLinearVelocity() / CraftCmPerMeter;
	const FVector Up = Rotation.RotateVector(FVector::UpVector);
	const FVector Forward = Rotation.RotateVector(FVector::ForwardVector);
	const float SpeedMPerSecond = VelocityMPerSecond.Size();
	ApplyRaceVitalLimits(DeltaSeconds, SpeedMPerSecond);
	HoverSensor.Sample(GetWorld(), PositionCm, Rotation, VelocityMPerSecond * CraftCmPerMeter, Tuning, DeltaSeconds, GetOwner());
	const FStardustHoverState& Sensor = HoverSensor.GetState();
	#if !UE_BUILD_SHIPPING
	if (const APawn* PlayerPawn = Cast<APawn>(GetOwner()))
	{
		const double WorldTime = GetWorld()->GetTimeSeconds();
		if (WorldTime >= NextGroundDiagnosticTime)
		{
			UE_LOG(LogTemp, Display, TEXT("Hover contact [%s]: %d/5 probes, height %.2f m, pos %s cm, speed %.1f m/s, vertical %.2f m/s, steer %.2f."),
				*PlayerPawn->GetName(), Sensor.Hits, Sensor.Hits > 0 ? Sensor.HeightM : -1.0f, *PositionCm.ToCompactString(),
				SpeedMPerSecond, VelocityMPerSecond.Z, Input.Steer);
			NextGroundDiagnosticTime = WorldTime + 1.0;
		}
	}
	#endif
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
	UpdateRaceFuel(DeltaSeconds, SpeedMPerSecond);

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

	const FVector DesiredUp = bGrounded ? SurfaceNormal : FindAirTargetUp(PositionCm, VelocityMPerSecond);
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

	BodyComponent->SetPhysicsLinearVelocity(VelocityMPerSecond * CraftCmPerMeter);
	BodyComponent->SetPhysicsAngularVelocityInRadians(Spin);
	if (bGrounded && !bWasGrounded && Telemetry.AirTimeSeconds > 0.08f)
	{
		Telemetry.LastLandingSpeedMPerSecond = -FVector::DotProduct(VelocityMPerSecond, SurfaceNormal);
		if (Telemetry.LastLandingSpeedMPerSecond > Tuning.LandingHard)
		{
			const float LandingDamage = (Telemetry.LastLandingSpeedMPerSecond - Tuning.LandingHard) * 1.4f;
			Telemetry.HullIntegrity = FMath::Max(0.0f, Telemetry.HullIntegrity - LandingDamage);
			OnDamaged.Broadcast(LandingDamage);
		}
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
	PreVelocityCmPerSecond = VelocityMPerSecond * CraftCmPerMeter;
}

FVector UStardustCraftMovementComponent::FindAirTargetUp(const FVector& PositionCm, const FVector& VelocityMPerSecond) const
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
		const FVector CurrentPointCm = PositionCm + BallisticOffsetM * CraftCmPerMeter;
		const FVector Segment = CurrentPointCm - PreviousPointCm;
		const FVector SegmentDirection = Segment.GetSafeNormal();
		const FVector TraceEndCm = PreviousPointCm + SegmentDirection * (Segment.Size() + Tuning.HoverHeightM * CraftCmPerMeter);
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, PreviousPointCm, TraceEndCm,
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
