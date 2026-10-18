#include "Flight/EXHoverCraft.h"

#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Flight/EXCraftFx.h"
#include "GameFramework/PlayerStart.h"
#include "World/EXDesertTerrain.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformMisc.h"
#include "Math/RotationMatrix.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UObject/ConstructorHelpers.h"
#include "UnrealClient.h"

namespace
{
	constexpr float CmPerM = 100.0f;
	constexpr float ProbeRadiusCm = 60.0f;
	constexpr float LostBelowZCm = -20000.0f;

	float Damp(float Lambda, float Dt)
	{
		return 1.0f - FMath::Exp(-Lambda * Dt);
	}

	FVector BlendNormal(const FVector& From, const FVector& To, float Alpha)
	{
		return FMath::Lerp(From, To, Alpha).GetSafeNormal(UE_SMALL_NUMBER, From);
	}

	float ViewportAspect()
	{
		if (GEngine && GEngine->GameViewport)
		{
			FVector2D Size;
			GEngine->GameViewport->GetViewportSize(Size);
			if (Size.Y > 1.0f)
			{
				return Size.X / Size.Y;
			}
		}
		return 16.0f / 9.0f;
	}

	/** The previous game used vertical FOV; Unreal cameras take horizontal FOV. */
	float HorizontalFov(float VerticalDeg)
	{
		return FMath::RadiansToDegrees(2.0f * FMath::Atan(FMath::Tan(FMath::DegreesToRadians(VerticalDeg) * 0.5f) * ViewportAspect()));
	}
}

AEXHoverCraft::AEXHoverCraft()
{
	PrimaryActorTick.bCanEverTick = true;

	Collision = CreateDefaultSubobject<UBoxComponent>(TEXT("Collision"));
	Collision->SetBoxExtent(FVector(260.0f, 150.0f, 45.0f));
	Collision->SetCollisionProfileName(TEXT("Pawn"));
	SetRootComponent(Collision);

	VisualPivot = CreateDefaultSubobject<USceneComponent>(TEXT("VisualPivot"));
	VisualPivot->SetupAttachment(Collision);

	ShipMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ShipMesh"));
	ShipMesh->SetupAttachment(VisualPivot);
	ShipMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Strix(TEXT("/Game/TestShips/SM_STRIX.SM_STRIX"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Wraith(TEXT("/Game/TestShips/SM_WRAITH.SM_WRAITH"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Nomad(TEXT("/Game/TestShips/SM_NOMAD.SM_NOMAD"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Bastion(TEXT("/Game/TestShips/SM_BASTION.SM_BASTION"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Vortex(TEXT("/Game/TestShips/SM_VORTEX.SM_VORTEX"));
	for (UStaticMesh* Mesh : { Strix.Object, Wraith.Object, Nomad.Object, Bastion.Object, Vortex.Object })
	{
		if (Mesh)
		{
			ShipMeshes.Add(Mesh);
		}
	}

	// The chase camera is placed in world space every frame (see UpdateCamera).
	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Collision);
	Camera->SetUsingAbsoluteLocation(true);
	Camera->SetUsingAbsoluteRotation(true);
	// Blur mostly smears nearby scenery (as in the reference video); kept moderate because heavy full-screen
	// blur measurably lowers the perceived speed.
	Camera->PostProcessSettings.bOverride_MotionBlurAmount = true;
	Camera->PostProcessSettings.MotionBlurAmount = 0.5f;
	Camera->PostProcessSettings.bOverride_MotionBlurMax = true;
	Camera->PostProcessSettings.MotionBlurMax = 8.0f;

	Fx = CreateDefaultSubobject<UEXCraftFx>(TEXT("Fx"));
}

void AEXHoverCraft::BeginPlay()
{
	Super::BeginPlay();
	StartLocation = GetActorLocation();
	StartRotation = FRotator(0.0f, GetActorRotation().Yaw, 0.0f);
	Heading = StartRotation.Vector();
	Fx->Initialize(VisualPivot);
	SelectShip(0);
	bFlightTest = FParse::Param(FCommandLine::Get(), TEXT("EXFlightTest"));
	for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
	{
		bDesertTest = bFlightTest && It->ActorHasTag(TEXT("EXWorld"));
		if (bDesertTest)
		{
			break;
		}
	}
}

void AEXHoverCraft::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	PlayerInputComponent->BindAxis(TEXT("Throttle"), this, &AEXHoverCraft::InputThrottle);
	PlayerInputComponent->BindAxis(TEXT("Brake"), this, &AEXHoverCraft::InputBrake);
	PlayerInputComponent->BindAxis(TEXT("Steer"), this, &AEXHoverCraft::InputSteer);
	PlayerInputComponent->BindAxis(TEXT("LookYaw"), this, &AEXHoverCraft::InputLookYaw);
	PlayerInputComponent->BindAction(TEXT("LookBack"), IE_Pressed, this, &AEXHoverCraft::LookBackPressed);
	PlayerInputComponent->BindAction(TEXT("LookBack"), IE_Released, this, &AEXHoverCraft::LookBackReleased);
	PlayerInputComponent->BindAction(TEXT("Boost"), IE_Pressed, this, &AEXHoverCraft::BoostPressed);
	PlayerInputComponent->BindAction(TEXT("Boost"), IE_Released, this, &AEXHoverCraft::BoostReleased);
	PlayerInputComponent->BindAction(TEXT("Drift"), IE_Pressed, this, &AEXHoverCraft::DriftPressed);
	PlayerInputComponent->BindAction(TEXT("Drift"), IE_Released, this, &AEXHoverCraft::DriftReleased);
	PlayerInputComponent->BindAction(TEXT("ResetCraft"), IE_Pressed, this, &AEXHoverCraft::ResetToStart);
	PlayerInputComponent->BindAction(TEXT("QuitGame"), IE_Pressed, this, &AEXHoverCraft::QuitPressed);
	PlayerInputComponent->BindAction(TEXT("NextShip"), IE_Pressed, this, &AEXHoverCraft::NextShip);
	PlayerInputComponent->BindAction(TEXT("PrevShip"), IE_Pressed, this, &AEXHoverCraft::PrevShip);
	PlayerInputComponent->BindAction(TEXT("Ship1"), IE_Pressed, this, &AEXHoverCraft::Ship1);
	PlayerInputComponent->BindAction(TEXT("Ship2"), IE_Pressed, this, &AEXHoverCraft::Ship2);
	PlayerInputComponent->BindAction(TEXT("Ship3"), IE_Pressed, this, &AEXHoverCraft::Ship3);
	PlayerInputComponent->BindAction(TEXT("Ship4"), IE_Pressed, this, &AEXHoverCraft::Ship4);
	PlayerInputComponent->BindAction(TEXT("Ship5"), IE_Pressed, this, &AEXHoverCraft::Ship5);
	PlayerInputComponent->BindAction(TEXT("ToggleCamera"), IE_Pressed, this, &AEXHoverCraft::CycleCamera);
}

void AEXHoverCraft::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bDesertTest)
	{
		RunDesertTest(DeltaSeconds);
	}
	else if (bFlightTest)
	{
		RunFlightTest(DeltaSeconds);
	}
	if (!bLost)
	{
		// Fixed small steps keep the hover spring stable through frame hitches.
		float Remaining = FMath::Min(DeltaSeconds, 0.1f);
		while (Remaining > KINDA_SMALL_NUMBER)
		{
			const float Step = FMath::Min(Remaining, 1.0f / 60.0f);
			StepFlight(Step);
			Remaining -= Step;
		}
		if (GetActorLocation().Z < LostBelowZCm)
		{
			bLost = true;
			VelocityCmps = FVector::ZeroVector;
		}
	}
	UpdateVisuals(DeltaSeconds);
	UpdateCamera(DeltaSeconds);

	FEXCraftFxInput FxInput;
	FxInput.Velocity = VelocityCmps;
	FxInput.Heading = Heading;
	FxInput.SurfaceUp = SurfaceUp;
	FxInput.GroundPoint = GroundPointCm;
	FxInput.CameraLocation = Camera->GetComponentLocation();
	FxInput.CameraForward = Camera->GetForwardVector();
	FxInput.SpeedAlpha = FMath::Clamp(ForwardSpeedMps / MaxSpeedMps, 0.0f, 1.2f);
	FxInput.Throttle = ThrottleInput;
	FxInput.HeightM = HeightM;
	FxInput.bGrounded = bGrounded;
	FxInput.bBoosting = bBoosting;
	FxInput.bDrifting = bDrifting;
	Fx->UpdateFx(DeltaSeconds, FxInput);
	ShowTelemetry();
}

void AEXHoverCraft::StepFlight(float Dt)
{
	const FVector Location = GetActorLocation();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(EXHoverProbe), false, this);
	FHitResult GroundHit;
	const bool bHit = GetWorld()->SweepSingleByChannel(GroundHit, Location, Location - SurfaceUp * (HoverHeightM * CmPerM * 3.0f),
		FQuat::Identity, ECC_Visibility, FCollisionShape::MakeSphere(ProbeRadiusCm), Params);
	HeightM = bHit ? (GroundHit.bStartPenetrating ? 0.3f : (GroundHit.Distance + ProbeRadiusCm) / CmPerM) : 99.0f;
	const FVector GroundNormal = bHit ? FVector(GroundHit.ImpactNormal) : FVector::UpVector;
	GroundPointCm = bHit ? FVector(GroundHit.ImpactPoint) : Location - SurfaceUp * (HoverHeightM * CmPerM);
	const bool bWasGrounded = bGrounded;
	const float AirTimeBefore = AirTimeSeconds;
	bGrounded = bHit && FVector::DotProduct(GroundNormal, SurfaceUp) > 0.5f && HeightM < HoverHeightM * 2.5f;
	AirTimeSeconds = bGrounded ? 0.0f : AirTimeSeconds + Dt;

	SurfaceUp = FMath::VInterpNormalRotationTo(SurfaceUp, bGrounded ? GroundNormal : FVector::UpVector, Dt,
		bGrounded ? SurfaceAlignDegPerSec : AirLevelDegPerSec);
	Heading = FVector::VectorPlaneProject(Heading, SurfaceUp).GetSafeNormal(UE_SMALL_NUMBER, Heading);

	FVector V = VelocityCmps / CmPerM;
	const float Speed = V.Size();
	const float Forward = FVector::DotProduct(V, Heading);
	const bool bWasDrifting = bDrifting;
	// As in the previous game: the drift button drifts when steering at speed, otherwise it brakes.
	bDrifting = bGrounded && bDriftHeld && ((bWasDrifting && Speed > 18.0f) || (FMath::Abs(SteerInput) > 0.25f && Speed > 25.0f));
	bBraking = bGrounded && !bDrifting && (BrakeInput > 0.05f || bDriftHeld);
	const float BrakeStrength = FMath::Max(BrakeInput, bDriftHeld ? 1.0f : 0.0f);

	bBoosting = bBoostHeld && Nitro > 0.0f && ThrottleInput > 0.1f;
	Nitro = bBoosting ? FMath::Max(0.0f, Nitro - Dt / NitroSeconds)
		: FMath::Min(1.0f, Nitro + Dt * (NitroRegen + (bWasDrifting ? NitroDriftRegen : 0.0f) + (bGrounded ? 0.0f : NitroAirRegen)));

	FVector Acceleration = FVector::ZeroVector;
	if (bGrounded)
	{
		const float TopSpeed = MaxSpeedMps * (bBoosting ? BoostTopMul : 1.0f);
		float Thrust = 0.0f;
		if (Forward < TopSpeed)
		{
			const float Ratio = FMath::Max(0.0f, Forward) / TopSpeed;
			Thrust = AccelerationMps2 * (1.0f - Ratio * Ratio) + (bBoosting ? BoostAccelerationMps2 * (1.0f - Ratio) : 0.0f);
		}
		else
		{
			Thrust = -(Forward - TopSpeed) * OverspeedBleed;
		}
		Acceleration += Heading * (Thrust * ThrottleInput);
		if (bBraking && Forward > 0.0f)
		{
			Acceleration -= Heading * FMath::Min(BrakeMps2 * BrakeStrength, Forward / Dt);
		}
		else if (bBraking && BrakeInput > 0.05f && Forward > -ReverseMaxSpeedMps)
		{
			Acceleration -= Heading * (AccelerationMps2 * 0.5f * BrakeInput);
		}
		else if (ThrottleInput < 0.05f && Forward > 0.0f)
		{
			Acceleration -= Heading * FMath::Min(CoastDecelMps2, Forward / Dt);
		}
		if (bDrifting && Speed > 1.0f)
		{
			Acceleration -= V / Speed * DriftDecel;
		}
		// Critically damped hover spring along the surface normal. It never pulls down harder than about
		// gravity, so the craft can fly off crests and ramps instead of being glued to the ground.
		const float NormalSpeed = FVector::DotProduct(V, SurfaceUp);
		Acceleration += SurfaceUp * (FMath::Max(HoverStiffness * (HoverHeightM - HeightM), -GravityMps2 * 1.3f)
			- 2.0f * FMath::Sqrt(HoverStiffness) * HoverDamping * NormalSpeed);
		Acceleration += FVector::VectorPlaneProject(FVector(0.0f, 0.0f, -GravityMps2), SurfaceUp) * SlopeGravityScale;
	}
	else
	{
		FVector AirForward = Heading;
		AirForward.Z = FMath::Min(AirForward.Z, 0.2f);
		const float Ratio = FMath::Clamp(Forward / MaxSpeedMps, 0.0f, 1.0f);
		Acceleration += AirForward.GetSafeNormal(UE_SMALL_NUMBER, Heading) * (AccelerationMps2 * AirThrust * (1.0f - Ratio * Ratio) * ThrottleInput);
		Acceleration.Z -= GravityMps2;
	}
	Acceleration -= V * (AeroDrag * Speed);
	V += Acceleration * Dt;

	// Grip: turn the sliding velocity towards the nose at a limited rate. Drifting lowers the grip, and slip
	// beyond DriftMaxSlipDeg is pulled back harder so a drift holds its angle instead of spinning out.
	const FVector Right = FVector::CrossProduct(SurfaceUp, Heading).GetSafeNormal();
	SlipRad = 0.0f;
	if (bGrounded)
	{
		const FVector Tangential = FVector::VectorPlaneProject(V, SurfaceUp);
		const float TangentialSpeed = Tangential.Size();
		if (TangentialSpeed > 1.0f && FVector::DotProduct(Tangential, Heading) > 0.0f)
		{
			const float SignedAngle = FMath::Atan2(FVector::DotProduct(SurfaceUp, FVector::CrossProduct(Tangential, Heading)),
				FVector::DotProduct(Tangential, Heading));
			SlipRad = SignedAngle;
			GripBlend = bDrifting ? 0.0f : FMath::Min(1.0f, GripBlend + Dt / FMath::Max(0.05f, DriftRecoverTime));
			float LateralMax = FMath::Lerp(DriftLateralMax, GripLateralMax, GripBlend) * (bBraking ? BrakeGripMul : 1.0f);
			float Redirect = FMath::Lerp(DriftRedirect, GripRedirect, GripBlend);
			const float SlipOverDeg = FMath::RadiansToDegrees(FMath::Abs(SignedAngle)) - DriftMaxSlipDeg;
			if (SlipOverDeg > 0.0f)
			{
				Redirect *= 1.0f + SlipOverDeg / 8.0f;
				LateralMax *= 1.0f + SlipOverDeg / 15.0f;
			}
			const float GripFactor = FMath::Min(GripCap, GripBase + FMath::Square(TangentialSpeed / GripSpeedRef));
			const float Rate = FMath::Min(Redirect, LateralMax * GripFactor / TangentialSpeed);
			const float Applied = FMath::Clamp(SignedAngle, -Rate * Dt, Rate * Dt);
			V += FQuat(SurfaceUp, Applied).RotateVector(Tangential) - Tangential;
			const float Lateral = FVector::DotProduct(V, Right);
			V -= Right * Lateral * FMath::Clamp(FMath::Lerp(0.18f, 1.0f, GripBlend) * GripFriction * GripFactor * Dt, 0.0f, 1.0f);
		}
		else if (TangentialSpeed > 0.5f)
		{
			// Reversing: plain sideways friction.
			V -= Right * FVector::DotProduct(V, Right) * FMath::Clamp(4.0f * Dt, 0.0f, 1.0f);
		}
	}

	// Mini turbo: holding a drift charges it, releasing it fires a boost along the nose.
	MiniTurboFlash = FMath::Max(0.0f, MiniTurboFlash - Dt * 2.0f);
	if (bDrifting && Speed > 30.0f && FMath::Abs(SlipRad) > 0.15f)
	{
		DriftCharge = FMath::Min(DriftCharge + Dt, 2.5f);
	}
	else if (!bDrifting)
	{
		if (DriftCharge > 0.6f && bGrounded)
		{
			V += Heading * (DriftBoost * FMath::Clamp(DriftCharge / 2.0f, 0.35f, 1.0f));
			MiniTurboFlash = 1.0f;
		}
		DriftCharge = 0.0f;
	}

	// Steering builds a yaw rate; entering a drift kicks the nose in, and the kick stops at the slip limit.
	const float TurnMul = bDrifting ? DriftTurnMul : bBraking ? BrakeTurnMul : 1.0f;
	const float TurnRate = FMath::Lerp(TurnRateLow, TurnRateHigh, FMath::Clamp(Speed / MaxSpeedMps, 0.0f, 1.0f)) * TurnMul * (bGrounded ? 1.0f : AirTurnMul);
	YawRate = FMath::Lerp(YawRate, SteerInput * (Forward < -0.5f ? -1.0f : 1.0f) * TurnRate, Damp(SteerResponse, Dt));
	if (bDrifting && !bWasDrifting)
	{
		YawRate += FMath::Sign(SteerInput) * DriftKick;
	}
	if (bGrounded && FMath::RadiansToDegrees(FMath::Abs(SlipRad)) > DriftMaxSlipDeg && YawRate * SlipRad > 0.0f)
	{
		YawRate = FMath::Lerp(YawRate, 0.0f, Damp(8.0f, Dt));
	}
	Heading = Heading.RotateAngleAxis(FMath::RadiansToDegrees(YawRate * Dt), SurfaceUp);

	if (bGrounded && !bWasGrounded && AirTimeBefore > 0.08f)
	{
		// Touchdown: the camera dips and jolts, and the sand bursts out around the craft.
		const float LandingSpeed = FMath::Max(0.0f, -FVector::DotProduct(V, SurfaceUp));
		CamKickVel -= FMath::Min(LandingSpeed * 0.06f, 1.4f);
		CamJolt = FMath::Max(CamJolt, FMath::Clamp(LandingSpeed / 14.0f, 0.15f, 1.0f));
		if (LandingSpeed > 3.0f)
		{
			Fx->LandingBurst(GroundPointCm, SurfaceUp, FMath::Clamp(LandingSpeed / 15.0f, 0.3f, 1.0f));
		}
	}

	const float PreviousForward = ForwardSpeedMps;
	VelocityCmps = V * CmPerM;
	ForwardSpeedMps = FVector::DotProduct(V, Heading);
	LateralSpeedMps = FVector::DotProduct(V, FVector::CrossProduct(SurfaceUp, Heading));
	LongAccelMps2 = FMath::FInterpTo(LongAccelMps2, (ForwardSpeedMps - PreviousForward) / Dt, Dt, 4.0f);

	MoveWithCollision(Dt);
	SetActorRotation(FRotationMatrix::MakeFromXZ(Heading, SurfaceUp).ToQuat());
}

void AEXHoverCraft::MoveWithCollision(float Dt)
{
	SparkCooldown -= Dt;
	FVector Delta = VelocityCmps * Dt;
	for (int32 Iteration = 0; Iteration < 4 && !Delta.IsNearlyZero(0.01); ++Iteration)
	{
		FHitResult Hit;
		AddActorWorldOffset(Delta, true, &Hit);
		if (!Hit.bBlockingHit)
		{
			break;
		}
		if (Hit.bStartPenetrating)
		{
			AddActorWorldOffset(Hit.Normal * (Hit.PenetrationDepth + 1.0f), false, nullptr, ETeleportType::TeleportPhysics);
			continue;
		}
		const FVector Normal = Hit.Normal;
		const float IntoSpeed = FVector::DotProduct(VelocityCmps, Normal);
		if (IntoSpeed < 0.0f)
		{
			// Steep surfaces are walls: bounce a little and lose speed. Gentle ones just redirect the craft.
			const bool bWall = FVector::DotProduct(Normal, SurfaceUp) < 0.6f;
			VelocityCmps -= Normal * IntoSpeed * (1.0f + (bWall ? WallBounce : 0.0f));
			if (bWall)
			{
				VelocityCmps *= 1.0f - FMath::Clamp(WallScrapeLoss * (-IntoSpeed / CmPerM) / 20.0f, 0.0f, 0.5f);
			}
			ImpactShake = FMath::Max(ImpactShake, FMath::Clamp(-IntoSpeed / CmPerM / 25.0f, 0.0f, 1.0f));
			if (bWall)
			{
				CamJolt = FMath::Max(CamJolt, FMath::Clamp(-IntoSpeed / CmPerM / 20.0f, 0.0f, 1.0f));
				if (SparkCooldown <= 0.0f)
				{
					SparkCooldown = 0.05f;
					Fx->ImpactSparks(Hit.ImpactPoint, Normal, VelocityCmps, FMath::Clamp(-IntoSpeed / CmPerM / 15.0f, 0.2f, 1.0f));
				}
			}
		}
		Delta = FVector::VectorPlaneProject(Delta * (1.0f - Hit.Time), Normal);
	}
}

void AEXHoverCraft::UpdateVisuals(float Dt)
{
	HoverBobTime += Dt;
	SteerVisual = FMath::FInterpTo(SteerVisual, SteerInput, Dt, 6.0f);
	const float SpeedAlpha = FMath::Clamp(FMath::Abs(ForwardSpeedMps) / MaxSpeedMps, 0.0f, 1.0f);
	const float DriftExtra = bDrifting ? 1.35f : 1.0f;
	const float TargetRoll = SteerVisual * BankMaxDeg * FMath::Lerp(0.35f, 1.0f, SpeedAlpha) * DriftExtra + FMath::Sin(HoverBobTime * 1.7f) * 0.6f;
	const float TargetPitch = FMath::Clamp(LongAccelMps2 * PitchFromAccel, -6.0f, 5.0f);
	const float TargetYaw = SteerVisual * NoseLeadMaxDeg * DriftExtra;
	VisualRoll = FMath::FInterpTo(VisualRoll, TargetRoll, Dt, VisualResponse);
	VisualPitch = FMath::FInterpTo(VisualPitch, TargetPitch, Dt, VisualResponse);
	VisualYaw = FMath::FInterpTo(VisualYaw, TargetYaw, Dt, VisualResponse);
	FVector Shake = FVector::ZeroVector;
	if (ImpactShake > 0.0f)
	{
		Shake = FMath::VRand() * 12.0f * ImpactShake;
		ImpactShake = FMath::Max(0.0f, ImpactShake - Dt * 3.0f);
	}
	VisualPivot->SetRelativeLocationAndRotation(FVector(0.0f, 0.0f, FMath::Sin(HoverBobTime * 2.3f) * 4.0f) + Shake,
		FRotator(VisualPitch, VisualYaw, VisualRoll));
}

void AEXHoverCraft::UpdateCamera(float Dt)
{
	const FVector CraftLocation = GetActorLocation();
	const FVector CraftUp = GetActorUpVector();
	const FVector CraftForward = GetActorForwardVector();
	const FVector V = VelocityCmps / CmPerM;
	const float Speed = V.Size();
	const float SpeedAlpha = FMath::Clamp(Speed / MaxSpeedMps, 0.0f, 1.0f);

	if (CameraMode >= 2)
	{
		// Inspection views: side (2) and front (3).
		const FVector Side = CameraMode == 2 ? GetActorRightVector() : CraftForward;
		const FVector Position = CraftLocation + Side * 1300.0f + CraftUp * 150.0f;
		Camera->SetWorldLocationAndRotation(Position, FRotationMatrix::MakeFromXZ(CraftLocation - Position, FVector::UpVector).ToQuat());
		Camera->SetFieldOfView(HorizontalFov(FovMinV));
		bCamInitialized = false;
		return;
	}

	// Chase framing ported from the previous game. Mode 1 is the far view of the reference video.
	const bool bFar = CameraMode == 1;
	const float BaseDistance = bFar ? 14.0f : CamDistanceM;
	const float BaseHeight = bFar ? 3.8f : CamHeightM;
	const FVector HeadingDir = Speed > 10.0f ? BlendNormal(CraftForward, V / Speed, 0.3f) : CraftForward;
	const FVector UpPosition = BlendNormal(FVector::UpVector, CraftUp, CamUpFollow);
	const FVector UpRoll = BlendNormal(FVector::UpVector, CraftUp, CamRollFollow);
	if (!bCamInitialized)
	{
		CamSmoothUp = UpPosition;
		CamSmoothHeading = HeadingDir;
		CamFovV = FovMinV;
		CamOffsetCm = (-HeadingDir * BaseDistance + UpPosition * BaseHeight) * CmPerM;
		bCamInitialized = true;
	}
	CamSmoothUp = BlendNormal(CamSmoothUp, UpPosition, Damp(CamUpSmoothing, Dt));
	CamSmoothHeading = BlendNormal(CamSmoothHeading, HeadingDir, Damp(CamHeadingSmoothing, Dt));

	// Right stick orbits the camera; the look-back button turns it around. While drifting the camera
	// swings to the outside of the slide.
	CamLookYaw = FMath::Lerp(CamLookYaw, bLookBack ? 180.0f : LookYawInput * LookYawMaxDeg, Damp(bLookBack ? 18.0f : 7.0f, Dt));
	CamDriftSwing = FMath::Lerp(CamDriftSwing, bDrifting ? FMath::Clamp(-LateralSpeedMps * 0.7f, -20.0f, 20.0f) : 0.0f, Damp(bDrifting ? 3.0f : 2.0f, Dt));
	const FVector ViewHeading = CamSmoothHeading.RotateAngleAxis(CamLookYaw + CamDriftSwing, CamSmoothUp);
	if (bBoosting && !bCamWasBoosting)
	{
		CamBoostPunch = 1.0f;
	}
	bCamWasBoosting = bBoosting;
	CamBoostPunch = FMath::Max(0.0f, CamBoostPunch - Dt * 1.8f);

	// The camera drops back under acceleration and closes in under braking.
	const float Pull = Dt > 0.0f ? FMath::Clamp((Speed - CamLastSpeed) / Dt * 0.03f, -0.6f, 1.2f) : 0.0f;
	CamLastSpeed = Speed;
	const float Distance = BaseDistance + CamDistanceAtSpeedM * SpeedAlpha + Pull;
	const float Height = BaseHeight + CamHeightAtSpeedM * SpeedAlpha;
	const FVector DesiredOffset = (-ViewHeading * Distance + CamSmoothUp * Height) * CmPerM;
	CamOffsetCm = FMath::Lerp(CamOffsetCm, DesiredOffset, Damp(CamOffsetStiffness, Dt));

	// Landing kick: a small spring that dips the camera when the craft touches down.
	CamKickVel += (-CamKick * 60.0f - CamKickVel * 12.0f) * Dt;
	CamKick += CamKickVel * Dt;

	const FVector Pivot = CraftLocation + CraftUp * 120.0f;
	const FVector Desired = CraftLocation + CamOffsetCm + CamSmoothUp * (CamKick * CmPerM);
	FVector Position = Desired;
	const FVector ToDesired = Desired - Pivot;
	const float Length = ToDesired.Size();
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(EXChaseCamera), false, this);
	if (Length > 1.0f && GetWorld()->SweepSingleByChannel(Hit, Pivot, Desired, FQuat::Identity, ECC_Camera, FCollisionShape::MakeSphere(35.0f), Params))
	{
		Position = Pivot + ToDesired / Length * FMath::Max(30.0f, Hit.Distance - 15.0f);
	}
	const FVector Look = CraftLocation + (ViewHeading * CamLookAheadM + CamSmoothUp * CamLookHeightM) * CmPerM;
	FRotator Rotation = FRotationMatrix::MakeFromXZ(Look - Position, UpRoll).Rotator();

	// The camera leans a little with the craft's bank, and vibrates lightly near top speed.
	Rotation.Roll += VisualRoll * CameraBankFollow;
	const float Shake = ShakeScale * TopSpeedShakeDeg * FMath::Clamp((SpeedAlpha - 0.85f) / 0.15f, 0.0f, 1.0f) * (bBoosting ? 1.6f : 1.0f);
	Rotation.Pitch += FMath::Sin(HoverBobTime * 31.0f) * Shake;
	Rotation.Yaw += FMath::Sin(HoverBobTime * 23.0f + 1.3f) * Shake;
	// Short, sharp jolt after a hard landing or a wall hit.
	CamJoltTime += Dt;
	if (CamJolt > 0.0f)
	{
		const float Jolt = CamJolt * LandingShakeDeg * ShakeScale;
		Rotation.Pitch += FMath::Sin(CamJoltTime * 47.0f) * Jolt;
		Rotation.Roll += FMath::Sin(CamJoltTime * 39.0f + 0.7f) * Jolt * 0.6f;
		Rotation.Yaw += FMath::Sin(CamJoltTime * 53.0f + 1.9f) * Jolt * 0.4f;
		CamJolt = FMath::Max(0.0f, CamJolt - Dt * 2.8f);
	}
	Camera->SetWorldLocationAndRotation(Position, Rotation);

	const float Vertigo = FMath::SmoothStep(VertigoKmhMin, VertigoKmhMax, Speed * 3.6f);
	const float TargetFovV = FMath::Lerp(FovMinV, FovMaxV, 0.3f * SpeedAlpha + 0.7f * Vertigo) + (bBoosting ? FovBoostV : 0.0f);
	CamFovV = FMath::Lerp(CamFovV, TargetFovV, Damp(3.0f, Dt));
	Camera->SetFieldOfView(HorizontalFov(CamFovV + 7.0f * CamBoostPunch * CamBoostPunch));
}

void AEXHoverCraft::SelectShip(int32 Index)
{
	if (ShipMeshes.Num() == 0)
	{
		return;
	}
	ShipIndex = (Index % ShipMeshes.Num() + ShipMeshes.Num()) % ShipMeshes.Num();
	UStaticMesh* Mesh = ShipMeshes[ShipIndex];
	const FRotator ModelRotation(0.0f, ModelYawOffsetDeg, 0.0f);
	ShipMesh->SetStaticMesh(Mesh);
	ShipMesh->SetRelativeRotation(ModelRotation);
	// Centre the model's bounds on the pivot so every ship hovers and banks around its middle.
	ShipMesh->SetRelativeLocation(-ModelRotation.RotateVector(Mesh ? Mesh->GetBounds().Origin : FVector::ZeroVector));
	if (Mesh)
	{
		Fx->SetShipHalfSize(ModelRotation.RotateVector(Mesh->GetBounds().BoxExtent).GetAbs());
	}
}

void AEXHoverCraft::ResetToStart()
{
	SetActorLocationAndRotation(StartLocation, StartRotation, false, nullptr, ETeleportType::TeleportPhysics);
	VelocityCmps = FVector::ZeroVector;
	Heading = StartRotation.Vector();
	SurfaceUp = FVector::UpVector;
	YawRate = 0.0f;
	Nitro = 1.0f;
	AirTimeSeconds = 0.0f;
	bLost = false;
	bCamInitialized = false;
}

void AEXHoverCraft::QuitPressed()
{
	if (APlayerController* PlayerController = Cast<APlayerController>(GetController()))
	{
		PlayerController->ConsoleCommand(TEXT("quit"));
	}
}

void AEXHoverCraft::ShowTelemetry() const
{
	if (!GEngine)
	{
		return;
	}
	static const TCHAR* CameraNames[] = { TEXT("perto"), TEXT("longe"), TEXT("lado"), TEXT("frente") };
	const FString ShipName = ShipMeshes.IsValidIndex(ShipIndex) && ShipMeshes[ShipIndex]
		? ShipMeshes[ShipIndex]->GetName().Replace(TEXT("SM_"), TEXT("")) : FString(TEXT("?"));
	GEngine->AddOnScreenDebugMessage(9101, 0.0f, FColor::White, FString::Printf(TEXT("%s   %4.0f km/h   %s   nitro %3.0f%%   camara %s%s%s"),
		*ShipName, FMath::Abs(ForwardSpeedMps) * 3.6f, bGrounded ? TEXT("HOVER") : TEXT("NO AR"), Nitro * 100.0f,
		CameraNames[FMath::Clamp(CameraMode, 0, 3)], bDrifting ? TEXT("   DRIFT") : TEXT(""), MiniTurboFlash > 0.0f ? TEXT("   MINI-TURBO!") : TEXT("")));
	GEngine->AddOnScreenDebugMessage(9102, 0.0f, FColor::Yellow,
		TEXT("Comando PS: R2 acelerar  L2 travar  analogico esq. virar  X nitro  R1/L1 drift  analogico dir. olhar  R3 olhar atras  Triangulo recomecar  Circulo camara  Setas nave"));
	GEngine->AddOnScreenDebugMessage(9104, 0.0f, FColor::Silver,
		TEXT("Teclado: W acelerar  S travar  A-D virar  Shift nitro  Espaco drift  Q-E olhar  B olhar atras  R recomecar  C camara  1-5 nave  Esc sair"));
	if (bLost)
	{
		GEngine->AddOnScreenDebugMessage(9103, 0.0f, FColor::Red, TEXT("NAVE PERDIDA - carrega R / Triangulo para recomecar"));
	}
}

void AEXHoverCraft::RunDesertTest(float Dt)
{
	// Drives the whole canyon route: from the start to the canyon entry, then along its centre line.
	TestTime += Dt;
	const TArray<FVector2D>& Path = FEXDesertTerrain::CanyonPath();
	const FVector Location = GetActorLocation();
	const FVector2D Here(Location.X / CmPerM, Location.Y / CmPerM);
	while (TestPathIndex < Path.Num() - 1 && FVector2D::Distance(Here, Path[TestPathIndex]) < 45.0f)
	{
		++TestPathIndex;
	}
	const FVector2D Target = Path[FMath::Min(TestPathIndex + 2, Path.Num() - 1)];
	const FVector ToTarget = FVector(Target.X * CmPerM - Location.X, Target.Y * CmPerM - Location.Y, 0.0f).GetSafeNormal();
	const FVector Flat = Heading.GetSafeNormal2D();
	const float AngleDeg = FMath::RadiansToDegrees(FMath::Atan2(FVector::CrossProduct(Flat, ToTarget).Z, FVector::DotProduct(Flat, ToTarget)));
	SteerInput = FMath::Clamp(AngleDeg / 20.0f, -1.0f, 1.0f);
	ThrottleInput = TestTime > 1.5f && ForwardSpeedMps < 65.0f ? 1.0f : 0.0f;
	BrakeInput = FMath::Abs(AngleDeg) > 50.0f && ForwardSpeedMps > 30.0f ? 1.0f : 0.0f;
	bBoostHeld = false;
	bDriftHeld = false;

	TestStuckSeconds = TestTime > 4.0f && ForwardSpeedMps < 5.0f ? TestStuckSeconds + Dt : 0.0f;
	const int32 ShotIndex = FMath::FloorToInt(TestTime / 9.0f);
	if (TestTime > 2.0f && ShotIndex < 8 && !(TestShotMask & (1 << ShotIndex)))
	{
		TestShotMask |= 1 << ShotIndex;
		FScreenshotRequest::RequestScreenshot(FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("DesertTest"), FString::Printf(TEXT("desert_%02d.png"), ShotIndex)), true, false);
	}
	if (TestTime >= NextTestLog)
	{
		NextTestLog = TestTime + 2.0f;
		UE_LOG(LogTemp, Display, TEXT("EXDESERT t=%.0f pos=(%.0f, %.0f, %.1f) m path=%d/%d speed=%.0f height=%.2f grounded=%d lost=%d stuck=%.1f fps=%.0f"),
			TestTime, Here.X, Here.Y, Location.Z / CmPerM, TestPathIndex, Path.Num(), ForwardSpeedMps, HeightM, bGrounded ? 1 : 0, bLost ? 1 : 0,
			TestStuckSeconds, Dt > 0.0f ? 1.0f / Dt : 0.0f);
	}
	if (TestTime > 70.0f || TestPathIndex >= Path.Num() - 1 || bLost)
	{
		UE_LOG(LogTemp, Display, TEXT("EXDESERT DONE t=%.0f path=%d/%d lost=%d"), TestTime, TestPathIndex, Path.Num(), bLost ? 1 : 0);
		FPlatformMisc::RequestExit(false);
	}
}

void AEXHoverCraft::RunFlightTest(float Dt)
{
	TestTime += Dt;
	auto Shot = [this](int32 Bit, const TCHAR* Name)
	{
		if (TestShotMask & (1 << Bit))
		{
			return;
		}
		TestShotMask |= 1 << Bit;
		FScreenshotRequest::RequestScreenshot(FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("FlightTest"), FString(Name) + TEXT(".png")), true, false);
		UE_LOG(LogTemp, Display, TEXT("EXFLIGHT shot %s at t=%.1f"), Name, TestTime);
	};

	ThrottleInput = 0.0f;
	BrakeInput = 0.0f;
	SteerInput = 0.0f;
	bBoostHeld = false;
	if (TestTime < 1.5f)
	{
		if (TestTime > 1.2f) { Shot(0, TEXT("01_chase_idle")); }
	}
	else if (TestTime < 2.3f)
	{
		CameraMode = 2;
		if (TestTime > 2.0f) { Shot(1, TEXT("02_side")); }
	}
	else if (TestTime < 3.1f)
	{
		CameraMode = 3;
		if (TestTime > 2.8f) { Shot(2, TEXT("03_front")); }
	}
	else
	{
		CameraMode = 0;
		ThrottleInput = 1.0f;
		bBoostHeld = TestTime > 6.0f && TestTime < 9.0f;
		const FVector Location = GetActorLocation();
		if (Location.X < 80000.0f)
		{
			// Follow the centre line towards the jump ramp.
			const FVector ToTarget = (FVector(Location.X + 6000.0f, 0.0f, Location.Z) - Location).GetSafeNormal2D();
			const FVector Flat = Heading.GetSafeNormal2D();
			const float AngleDeg = FMath::RadiansToDegrees(FMath::Atan2(FVector::CrossProduct(Flat, ToTarget).Z, FVector::DotProduct(Flat, ToTarget)));
			SteerInput = FMath::Clamp(AngleDeg / 20.0f, -1.0f, 1.0f);
		}
		else
		{
			// Hard drifting right turn, then release for the mini turbo.
			if (TestDriftStart < 0.0f) { TestDriftStart = TestTime; }
			const float DriftTime = TestTime - TestDriftStart;
			SteerInput = DriftTime < 3.5f ? 1.0f : 0.0f;
			bDriftHeld = DriftTime < 2.5f;
			if (DriftTime > 1.2f) { Shot(5, TEXT("06_drift")); }
		}
		if (TestTime > 7.5f) { Shot(3, TEXT("04_speed")); }
		if (AirTimeSeconds > 0.35f) { Shot(4, TEXT("05_jump")); }
		if (TestTime > 9.0f && TestTime < 17.0f && CamJolt > 0.4f) { Shot(6, TEXT("07_landing")); }
		if (TestTime > 17.0f)
		{
			// Wall scrape: drop the craft into the walled corridor heading slightly into its right wall, on nitro.
			if (!bTestWallPlaced)
			{
				bTestWallPlaced = true;
				const FRotator Rotation(0.0f, 12.0f, 0.0f);
				SetActorLocationAndRotation(FVector(150000.0f, 1700.0f, 160.0f), Rotation, false, nullptr, ETeleportType::TeleportPhysics);
				Heading = Rotation.Vector();
				SurfaceUp = FVector::UpVector;
				VelocityCmps = Heading * 8500.0f;
				bCamInitialized = false;
			}
			bDriftHeld = false;
			bBoostHeld = true;
			SteerInput = 0.3f;
			if (CamJolt > 0.25f) { Shot(7, TEXT("08_wall")); }
		}
	}

	if (TestTime >= NextTestLog)
	{
		NextTestLog = TestTime + 0.5f;
		UE_LOG(LogTemp, Display, TEXT("EXFLIGHT t=%.1f pos=%s speed=%.1f lat=%.1f slip=%.0f drift=%d charge=%.1f height=%.2f grounded=%d air=%.2f fps=%.0f"),
			TestTime, *GetActorLocation().ToCompactString(), ForwardSpeedMps, LateralSpeedMps, FMath::RadiansToDegrees(SlipRad),
			bDrifting ? 1 : 0, DriftCharge, HeightM, bGrounded ? 1 : 0, AirTimeSeconds, Dt > 0.0f ? 1.0f / Dt : 0.0f);
	}
	if (TestTime > 22.0f)
	{
		UE_LOG(LogTemp, Display, TEXT("EXFLIGHT DONE"));
		FPlatformMisc::RequestExit(false);
	}
}
