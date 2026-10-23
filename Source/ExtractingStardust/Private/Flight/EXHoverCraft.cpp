#include "Flight/EXHoverCraft.h"

#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/InputComponent.h"
#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Flight/EXCraftAudio.h"
#include "Flight/EXCraftFx.h"
#include "GameFramework/PlayerStart.h"
#include "World/EXDesertTerrain.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformMisc.h"
#include "Math/RotationMatrix.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Race/EXRaceDirector.h"
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

	/** Race stats by ship (Docs/MODOS_DE_JOGO.md; a first proposal, to tune with the player): the faster the more
	 *  fragile. Lives; top speed against the tuned handling; the speed into a wall and the landing speed (m/s) that
	 *  cost a life. Looked up by the mesh name (SM_VORTEX -> VORTEX). */
	struct FShipRaceStats
	{
		const TCHAR* Name;
		int32 Lives;
		float SpeedMul;
		float WallHitMps;
		float LandingHitMps;
	};
	const FShipRaceStats ShipRaceStats[] = {
		{ TEXT("VORTEX"), 2, 1.06f, 20.0f, 26.0f },
		{ TEXT("STRIX"), 3, 1.03f, 24.0f, 28.0f },
		{ TEXT("WRAITH"), 3, 1.00f, 24.0f, 28.0f },
		{ TEXT("NOMAD"), 4, 0.96f, 28.0f, 31.0f },
		{ TEXT("BASTION"), 5, 0.93f, 32.0f, 34.0f },
	};

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
	Camera->PostProcessSettings.MotionBlurAmount = 0.55f;
	Camera->PostProcessSettings.bOverride_MotionBlurMax = true;
	Camera->PostProcessSettings.MotionBlurMax = 12.0f;
	Camera->PostProcessSettings.bOverride_SceneFringeIntensity = true;
	Camera->PostProcessSettings.SceneFringeIntensity = 0.0f;
	Camera->PostProcessSettings.bOverride_VignetteIntensity = true;
	Camera->PostProcessSettings.VignetteIntensity = 0.35f;

	Fx = CreateDefaultSubobject<UEXCraftFx>(TEXT("Fx"));
	Audio = CreateDefaultSubobject<UEXCraftAudio>(TEXT("Audio"));
}

void AEXHoverCraft::BeginPlay()
{
	Super::BeginPlay();
	BaseMaxSpeedMps = MaxSpeedMps;
	StartLocation = GetActorLocation();
	LastGroundZCm = StartLocation.Z - 300.0f;
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
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (USplineComponent* Spline = It->ActorHasTag(TEXT("EXRoute")) ? It->FindComponentByClass<USplineComponent>() : nullptr)
		{
			for (float Distance = 0.0f; Distance < Spline->GetSplineLength(); Distance += 5.0f * CmPerM)
			{
				const FVector Point = Spline->GetLocationAtDistanceAlongSpline(Distance, ESplineCoordinateSpace::World);
				MapRoute.Add(FVector2D(Point.X / CmPerM, Point.Y / CmPerM));
			}
			break;
		}
	}
	FString Looks;
	if (FParse::Value(FCommandLine::Get(), TEXT("EXLook="), Looks, false))
	{
		TArray<FString> Views;
		Looks.TrimQuotes().ParseIntoArray(Views, TEXT(";"));
		for (const FString& View : Views)
		{
			TArray<FString> V;
			View.ParseIntoArray(V, TEXT(","));
			if (V.Num() == 5)
			{
				LookViews.Add({ FVector(FCString::Atof(*V[0]), FCString::Atof(*V[1]), FCString::Atof(*V[2])) * CmPerM,
					FRotator(FCString::Atof(*V[4]), FCString::Atof(*V[3]), 0.0f) });
			}
		}
	}
	bTour = bDesertTest && (FParse::Param(FCommandLine::Get(), TEXT("EXTour")) || LookViews.Num() > 0);
	if (bTour)
	{
		bDesertTest = false;
		VisualPivot->SetVisibility(false, true);
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
	PlayerInputComponent->BindAction(TEXT("MedKit"), IE_Pressed, this, &AEXHoverCraft::UseMedKit);
	PlayerInputComponent->BindAction(TEXT("MenuUp"), IE_Pressed, this, &AEXHoverCraft::MenuUp);
	PlayerInputComponent->BindAction(TEXT("MenuDown"), IE_Pressed, this, &AEXHoverCraft::MenuDown);
	PlayerInputComponent->BindAction(TEXT("MenuConfirm"), IE_Pressed, this, &AEXHoverCraft::MenuConfirm);
	PlayerInputComponent->BindAxis(TEXT("HangarPitch"), this, &AEXHoverCraft::InputHangarPitch);
	PlayerInputComponent->BindAction(TEXT("HangarZoomIn"), IE_Pressed, this, &AEXHoverCraft::HangarZoomIn);
	PlayerInputComponent->BindAction(TEXT("HangarZoomOut"), IE_Pressed, this, &AEXHoverCraft::HangarZoomOut);
	PlayerInputComponent->BindAction(TEXT("HangarToggleAuto"), IE_Pressed, this, &AEXHoverCraft::HangarToggleAutoRotate);
	PlayerInputComponent->BindAction(TEXT("HangarBack"), IE_Pressed, this, &AEXHoverCraft::HangarBack);
}

void AEXHoverCraft::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bEliminated)
	{
		if (Audio)
		{
			FEXCraftAudioInput Silent;
			Silent.bViewer = false;
			Audio->UpdateAudio(DeltaSeconds, Silent);
		}
		return;
	}
	if (bInHangar)
	{
		UpdateHangar(DeltaSeconds);
		if (Audio)
		{
			FEXCraftAudioInput In;
			In.bHangar = true;
			In.bGrounded = true;
			In.bViewer = true;
			Audio->UpdateAudio(DeltaSeconds, In);
		}
		return;
	}
	HitCooldown = FMath::Max(0.0f, HitCooldown - DeltaSeconds);
	MedKitCooldown = FMath::Max(0.0f, MedKitCooldown - DeltaSeconds);
	const bool bViewer = IsPlayerControlled();
	if (bBot)
	{
		DriveBot(DeltaSeconds);
	}
	else if (bTour)
	{
		RunTour(DeltaSeconds);
	}
	else if (bDesertTest)
	{
		RunDesertTest(DeltaSeconds);
	}
	else if (bFlightTest)
	{
		RunFlightTest(DeltaSeconds);
	}
	if (bRaceHold)
	{
		// On the grid (countdown) or past the finish: the craft hovers where it is.
		ThrottleInput = 0.0f;
		BrakeInput = 1.0f;
		bBoostHeld = false;
		bDriftHeld = false;
	}
	if (!bLost)
	{
		// Fixed small steps keep the hover spring stable through frame hitches.
		float Remaining = FMath::Min(DeltaSeconds, 0.1f);
		while (Remaining > KINDA_SMALL_NUMBER && !bEliminated)
		{
			const float Step = FMath::Min(Remaining, 1.0f / 60.0f);
			StepFlight(Step);
			Remaining -= Step;
		}
		if (GetActorLocation().Z < LostBelowZCm)
		{
			bLost = true;
			VelocityCmps = FVector::ZeroVector;
			if (bRaceRules)
			{
				// In a race a fall out of the world costs a life; the craft comes back on the line.
				HitCooldown = 0.0f;
				LoseLife();
				if (!bEliminated)
				{
					RespawnOnRoute();
				}
			}
		}
	}
	if (bEliminated)
	{
		return;
	}
	if (MapRoute.Num() > 0)
	{
		// Follow the nearest race line point: a short window around the last one, the whole line if lost.
		const FVector2D Here(GetActorLocation().X / CmPerM, GetActorLocation().Y / CmPerM);
		const int32 Count = MapRoute.Num();
		int32 Best = RouteIndex;
		double BestD = TNumericLimits<double>::Max();
		for (int32 Offset = -40; Offset <= 80; ++Offset)
		{
			const int32 I = ((RouteIndex + Offset) % Count + Count) % Count;
			const double D = FVector2D::DistSquared(Here, MapRoute[I]);
			if (D < BestD)
			{
				BestD = D;
				Best = I;
			}
		}
		if (BestD > 150.0 * 150.0)
		{
			for (int32 I = 0; I < Count; ++I)
			{
				const double D = FVector2D::DistSquared(Here, MapRoute[I]);
				if (D < BestD)
				{
					BestD = D;
					Best = I;
				}
			}
		}
		RouteIndex = Best;
		const float ReachedM = RouteIndex * 5.0f;
		if (ReachedM > RaceProgressM && ReachedM - RaceProgressM < 600.0f)
		{
			RaceProgressM = ReachedM;
		}
	}
	UpdateVisuals(DeltaSeconds);
	if (bViewer)
	{
		UpdateCamera(DeltaSeconds);
	}
	if (bTour)
	{
		Camera->SetWorldLocationAndRotation(TourCameraLocation, TourCameraRotation);
		Camera->SetFieldOfView(70.0f);
	}

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
	FxInput.bViewer = bViewer;
	Fx->UpdateFx(DeltaSeconds, FxInput);
	if (Audio)
	{
		FEXCraftAudioInput Sound;
		Sound.SpeedMps = ForwardSpeedMps;
		Sound.Throttle = ThrottleInput;
		Sound.Steer = SteerInput;
		Sound.HeightM = HeightM;
		Sound.Impact = FMath::Max(ImpactShake, WallThreat);
		Sound.bBoosting = bBoosting;
		Sound.bGrounded = bGrounded;
		Sound.bDrifting = bDrifting;
		Sound.bRaceHold = bRaceHold;
		Sound.bViewer = bViewer;
		Audio->UpdateAudio(DeltaSeconds, Sound);
	}
	if (bViewer)
	{
		ShowTelemetry();
	}
}

void AEXHoverCraft::StepFlight(float Dt)
{
	const FVector Location = GetActorLocation();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(EXHoverProbe), false, this);
	FHitResult GroundHit;
	const bool bHit = GetWorld()->SweepSingleByChannel(GroundHit, Location, Location - SurfaceUp * (HoverHeightM * CmPerM * 3.0f),
		FQuat::Identity, ECC_Visibility, FCollisionShape::MakeSphere(ProbeRadiusCm), Params);
	HeightM = bHit ? (GroundHit.bStartPenetrating ? 0.3f : (GroundHit.Distance + ProbeRadiusCm) / CmPerM) : 99.0f;
	FVector GroundNormal = bHit ? FVector(GroundHit.ImpactNormal) : FVector::UpVector;
	// Four line probes under the hull (nose, tail, both sides): the height is their average and the ground is the
	// plane they span, so single terrain triangles no longer shake the craft. The sphere above stays as the fallback.
	{
		const FVector Fwd = Heading.GetSafeNormal();
		const FVector Side = FVector::CrossProduct(SurfaceUp, Fwd).GetSafeNormal();
		const FVector Offsets[4] = { Fwd * 160.0f, -Fwd * 160.0f, Side * 90.0f, -Side * 90.0f };
		FVector Points[4];
		float HeightSum = 0.0f;
		int32 Count = 0;
		for (int32 Probe = 0; Probe < 4; ++Probe)
		{
			FHitResult ProbeHit;
			const FVector Start = Location + Offsets[Probe];
			if (GetWorld()->LineTraceSingleByChannel(ProbeHit, Start, Start - SurfaceUp * (HoverHeightM * CmPerM * 3.0f), ECC_Visibility, Params))
			{
				Points[Count++] = ProbeHit.ImpactPoint;
				HeightSum += ProbeHit.Distance / CmPerM;
			}
		}
		if (Count == 4 && !GroundHit.bStartPenetrating)
		{
			const FVector Plane = FVector::CrossProduct(Points[0] - Points[1], Points[2] - Points[3]).GetSafeNormal();
			GroundNormal = FVector::DotProduct(Plane, SurfaceUp) < 0.0f ? -Plane : Plane;
			HeightM = FMath::Min(HeightM, HeightSum / 4.0f + 0.25f);  // never above what the sphere sees (walls, lips)
		}
	}
	GroundPointCm = bHit ? FVector(GroundHit.ImpactPoint) : Location - SurfaceUp * (HoverHeightM * CmPerM);
	const bool bWasGrounded = bGrounded;
	const float AirTimeBefore = AirTimeSeconds;
	bGrounded = bHit && FVector::DotProduct(GroundNormal, SurfaceUp) > 0.5f && HeightM < HoverHeightM * 2.5f;
	AirTimeSeconds = bGrounded ? 0.0f : AirTimeSeconds + Dt;
	if (bGrounded)
	{
		LastGroundZCm = GroundPointCm.Z;
	}

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
		if (LandingSpeed > LandingHitMps)
		{
			LoseLife();   // a landing too hard for this ship (race rules only)
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
		const AEXHoverCraft* OtherCraft = Cast<AEXHoverCraft>(Hit.GetActor());
		const FVector OtherVelocity = IsValid(OtherCraft) ? OtherCraft->VelocityCmps : FVector::ZeroVector;
		const float IntoSpeed = FVector::DotProduct(VelocityCmps - OtherVelocity, Normal);
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
			if (bWall || IsValid(OtherCraft))
			{
				const float DamageThresholdMps = IsValid(OtherCraft) ? WallHitMps * 0.6f : WallHitMps;
				if (-IntoSpeed / CmPerM > DamageThresholdMps)
				{
					LoseLife();
				}
			}
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
	const float DriftExtra = bDrifting ? 1.45f : 1.0f;
	const float TargetRoll = SteerVisual * BankMaxDeg * FMath::Lerp(0.45f, 1.0f, SpeedAlpha) * DriftExtra + FMath::Sin(HoverBobTime * 1.7f) * 0.6f;
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
	CamApexYaw = FMath::Lerp(CamApexYaw, SteerVisual * SpeedAlpha * CamLookIntoTurnDeg, Damp(5.0f, Dt));
	const FVector ViewHeading = CamSmoothHeading.RotateAngleAxis(CamLookYaw + CamDriftSwing + CamApexYaw, CamSmoothUp);

	float NearWall = 0.0f;
	{
		FCollisionQueryParams WallParams(SCENE_QUERY_STAT(EXWallThreat), false, this);
		const FVector Side = FVector::CrossProduct(CamSmoothUp, CamSmoothHeading).GetSafeNormal();
		for (int32 Sign : { -1, 1 })
		{
			FHitResult WallHit;
			const FVector Start = CraftLocation + CamSmoothUp * 80.0f;
			if (GetWorld()->SweepSingleByChannel(WallHit, Start, Start + Side * Sign * 900.0f, FQuat::Identity, ECC_Visibility,
				FCollisionShape::MakeSphere(20.0f), WallParams))
			{
				NearWall = FMath::Max(NearWall, 1.0f - FMath::Clamp(WallHit.Distance / 900.0f, 0.0f, 1.0f));
			}
		}
	}
	WallThreat = FMath::FInterpTo(WallThreat, NearWall * SpeedAlpha, Dt, 8.0f);
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
	const FVector Outboard = FVector::CrossProduct(CamSmoothUp, ViewHeading).GetSafeNormal() * (-SteerVisual * CamOutboardM * SpeedAlpha);
	const FVector DesiredOffset = (-ViewHeading * Distance + CamSmoothUp * Height + Outboard) * CmPerM;
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
	const float Shake = ShakeScale * (TopSpeedShakeDeg * FMath::Clamp((SpeedAlpha - 0.72f) / 0.28f, 0.0f, 1.0f) * (bBoosting ? 1.6f : 1.0f)
		+ WallThreat * 0.9f);
	Rotation.Pitch += FMath::Sin(HoverBobTime * 31.0f) * Shake;
	Rotation.Yaw += FMath::Sin(HoverBobTime * 23.0f + 1.3f) * Shake;
	Rotation.Roll += FMath::Sin(HoverBobTime * 19.0f) * WallThreat * 0.7f;
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
	Camera->PostProcessSettings.MotionBlurAmount = 0.45f + 0.55f * Vertigo + 0.25f * CamBoostPunch;
	Camera->PostProcessSettings.SceneFringeIntensity = 0.35f * Vertigo + 0.55f * CamBoostPunch;
	Camera->PostProcessSettings.VignetteIntensity = 0.28f + 0.22f * Vertigo;
}

void AEXHoverCraft::SelectShip(int32 Index)
{
	if (ShipMeshes.Num() == 0 || bShipLocked)
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
	if (bRaceRules)
	{
		ApplyShipStats();
	}
}

void AEXHoverCraft::ResetToStart()
{
	if (bRaceRules)
	{
		// In a race there is no going back to the start: the craft is put back on the line where it is.
		if (!bEliminated && !bRaceHold)
		{
			RespawnOnRoute();
		}
		return;
	}
	PlaceAt(StartLocation, StartRotation.Yaw);
	Nitro = 1.0f;
}

void AEXHoverCraft::PlaceAt(const FVector& Location, float YawDeg)
{
	StartLocation = Location;
	StartRotation = FRotator(0.0f, YawDeg, 0.0f);
	SetActorLocationAndRotation(StartLocation, StartRotation, false, nullptr, ETeleportType::TeleportPhysics);
	LastGroundZCm = Location.Z - 300.0f;
	VelocityCmps = FVector::ZeroVector;
	Heading = StartRotation.Vector();
	SurfaceUp = FVector::UpVector;
	YawRate = 0.0f;
	AirTimeSeconds = 0.0f;
	bLost = false;
	bCamInitialized = false;
}

FString AEXHoverCraft::GetShipName() const
{
	return ShipMeshes.IsValidIndex(ShipIndex) && ShipMeshes[ShipIndex]
		? ShipMeshes[ShipIndex]->GetName().Replace(TEXT("SM_"), TEXT("")) : FString(TEXT("?"));
}

void AEXHoverCraft::SetRaceRules(int32 InMedKits)
{
	bRaceRules = true;
	MedKits = InMedKits;
	Collision->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
	Collision->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	ApplyShipStats();
}

void AEXHoverCraft::ApplyShipStats()
{
	const FString Name = GetShipName();
	const FShipRaceStats* Stats = &ShipRaceStats[2];
	for (const FShipRaceStats& Candidate : ShipRaceStats)
	{
		if (Name.Equals(Candidate.Name, ESearchCase::IgnoreCase))
		{
			Stats = &Candidate;
			break;
		}
	}
	MaxLives = Stats->Lives;
	Lives = MaxLives;
	MaxSpeedMps = BaseMaxSpeedMps * Stats->SpeedMul;
	WallHitMps = Stats->WallHitMps;
	LandingHitMps = Stats->LandingHitMps;
}

void AEXHoverCraft::SetBot(int32 InShipIndex, float InSkill, float InLaneM)
{
	bBot = true;
	BotSkill = FMath::Clamp(InSkill, 0.5f, 1.0f);
	BotLaneM = InLaneM;
	BotPhase = FMath::FRandRange(0.0f, 2.0f * PI);
	SelectShip(InShipIndex);
}

void AEXHoverCraft::LoseLife()
{
	if (!bRaceRules || bEliminated || bRaceHold || HitCooldown > 0.0f)
	{
		return;
	}
	HitCooldown = 1.5f;   // one hit is one life, however many frames it scrapes
	if (Audio)
	{
		Audio->Bang(1.0f);
	}
	Lives = FMath::Max(0, Lives - 1);
	LastHitTime = GetWorld()->GetTimeSeconds();
	UE_LOG(LogTemp, Display, TEXT("EXRACE HIT %s%s lives=%d at %.1f km"), *GetShipName(), bBot ? TEXT("") : TEXT(" (jogador)"), Lives,
		RaceProgressM / 1000.0f);
	if (Lives == 0)
	{
		Eliminate();
	}
}

void AEXHoverCraft::Eliminate()
{
	bEliminated = true;
	VelocityCmps = FVector::ZeroVector;
	ThrottleInput = 0.0f;
	SetActorHiddenInGame(true);
	SetActorEnableCollision(false);
}

void AEXHoverCraft::SendMenu(int32 Step)
{
	if (bInHangar)
	{
		if (Step == 0)
		{
			HangarConfirm();
		}
		return;
	}
	for (TActorIterator<AEXRaceDirector> It(GetWorld()); It; ++It)
	{
		It->MenuInput(Step);
		break;
	}
}

void AEXHoverCraft::UseMedKit()
{
	// The medical kit: the player's only (bots get no charges), one life back, never above the ship's maximum.
	if (!bRaceRules || bEliminated || MedKits <= 0 || Lives >= MaxLives || MedKitCooldown > 0.0f)
	{
		return;
	}
	--MedKits;
	++Lives;
	MedKitCooldown = 5.0f;
	UE_LOG(LogTemp, Display, TEXT("EXRACE MEDKIT lives=%d kits=%d"), Lives, MedKits);
}

void AEXHoverCraft::RespawnOnRoute()
{
	if (MapRoute.Num() < 3)
	{
		PlaceAt(StartLocation, StartRotation.Yaw);
		return;
	}
	const int32 I = FMath::Clamp(RouteIndex, 0, MapRoute.Num() - 2);
	const FVector2D Dir = (MapRoute[I + 1] - MapRoute[I]).GetSafeNormal();
	const FVector2D Spot = MapRoute[I] + FVector2D(-Dir.Y, Dir.X) * BotLaneM;
	// The ground is found from just above the last floor the craft stood on (not from the sky: the cave has a roof).
	FVector Location(Spot.X * CmPerM, Spot.Y * CmPerM, LastGroundZCm + 300.0f);
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(EXRespawn), true, this);
	if (GetWorld()->LineTraceSingleByChannel(Hit, FVector(Location.X, Location.Y, LastGroundZCm + 1500.0f),
		FVector(Location.X, Location.Y, LastGroundZCm - 20000.0f), ECC_Visibility, Params))
	{
		Location.Z = Hit.ImpactPoint.Z + HoverHeightM * CmPerM + 100.0f;
	}
	PlaceAt(Location, FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X)));
	HitCooldown = 2.0f;
}

void AEXHoverCraft::DriveBot(float Dt)
{
	// A bot drives like the desert test's autopilot: aims ~35 m ahead on its lane, slows for the tightest bend in the
	// next 250 m (about 2.2 g of side grip, less for weaker bots), boosts on long straights if it is a good one.
	BotTime += Dt;
	const int32 Count = MapRoute.Num();
	if (Count < 20)
	{
		ThrottleInput = 0.0f;
		BrakeInput = 1.0f;
		return;
	}
	const FVector Location = GetActorLocation();
	const int32 Aim = FMath::Min(RouteIndex + 7, Count - 2);
	const FVector2D Dir = (MapRoute[Aim + 1] - MapRoute[Aim]).GetSafeNormal();
	const float Lane = BotLaneM + (1.1f - BotSkill) * 25.0f * FMath::Sin(BotTime * 0.15f + BotPhase);  // weaker bots wander
	const FVector2D Target = MapRoute[Aim] + FVector2D(-Dir.Y, Dir.X) * Lane;
	const FVector ToTarget = FVector(Target.X * CmPerM - Location.X, Target.Y * CmPerM - Location.Y, 0.0f).GetSafeNormal();
	const FVector Flat = Heading.GetSafeNormal2D();
	const float AngleDeg = FMath::RadiansToDegrees(FMath::Atan2(FVector::CrossProduct(Flat, ToTarget).Z, FVector::DotProduct(Flat, ToTarget)));
	SteerInput = FMath::Clamp(AngleDeg / 18.0f, -1.0f, 1.0f);
	float TightestM = 10000.0f;
	for (int32 Look = RouteIndex; Look + 10 < FMath::Min(RouteIndex + 50, Count); Look += 2)
	{
		const FVector2D A = MapRoute[Look];
		const FVector2D B = MapRoute[Look + 5];
		const FVector2D C = MapRoute[Look + 10];
		const double Cross = FMath::Abs((B - A) ^ (C - B));
		if (Cross > KINDA_SMALL_NUMBER)
		{
			TightestM = FMath::Min(TightestM, static_cast<float>(FVector2D::Distance(A, B) * FVector2D::Distance(B, C) * FVector2D::Distance(C, A) / (2.0 * Cross)));
		}
	}
	// Weaker bots misjudge bends now and then: a slow swell of their cornering speed, up to 8 % too fast.
	const float Misjudge = 1.0f + (1.0f - BotSkill) * 0.45f * FMath::Max(0.0f, FMath::Sin(BotTime * 0.31f + 2.0f * BotPhase));
	const float TargetSpeed = FMath::Min(MaxSpeedMps * BotSkill, FMath::Sqrt(22.0f * TightestM) * (0.8f + 0.2f * BotSkill) * Misjudge);
	ThrottleInput = ForwardSpeedMps < TargetSpeed ? 1.0f : 0.0f;
	BrakeInput = (ForwardSpeedMps > TargetSpeed + 6.0f || (FMath::Abs(AngleDeg) > 50.0f && ForwardSpeedMps > 30.0f)) ? 1.0f : 0.0f;
	bBoostHeld = BotSkill > 0.91f && TightestM > 900.0f && FMath::Abs(AngleDeg) < 8.0f;
	bDriftHeld = false;
	// Stuck against a wall or in a hole: back on the line after 3 s, as a player would press R.
	BotStuckSeconds = !bRaceHold && BotTime > 8.0f && ForwardSpeedMps < 5.0f ? BotStuckSeconds + Dt : 0.0f;
	if (BotStuckSeconds > 3.0f)
	{
		BotStuckSeconds = 0.0f;
		RespawnOnRoute();
	}
}

void AEXHoverCraft::QuitPressed()
{
	if (bInHangar)
	{
		HangarBack();
		return;
	}
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
		TEXT("Comando PS: R2 acelerar  L2 travar  analogico esq. virar  X nitro  R1/L1 drift  analogico dir. olhar  R3 olhar atras  Triangulo recomecar  Circulo camara  Setas nave  Quadrado kit medico"));
	GEngine->AddOnScreenDebugMessage(9104, 0.0f, FColor::Silver,
		TEXT("Teclado: W acelerar  S travar  A-D virar  Shift nitro  Espaco drift  Q-E olhar  B olhar atras  R recomecar  C camara  1-5 nave  H kit medico  Esc sair"));
	if (bLost)
	{
		GEngine->AddOnScreenDebugMessage(9103, 0.0f, FColor::Red, TEXT("NAVE PERDIDA - carrega R / Triangulo para recomecar"));
	}
}

void AEXHoverCraft::RunDesertTest(float Dt)
{
	// Drives the whole sector along the RACING line (or the SAFE line with -EXRouteSafe) at -EXTestSpeed=<m/s>.
	TestTime += Dt;
	const bool bSafeRoute = FParse::Param(FCommandLine::Get(), TEXT("EXRouteSafe"));
	float TestSpeed = 65.0f;
	FParse::Value(FCommandLine::Get(), TEXT("EXTestSpeed="), TestSpeed);
	const TArray<FVector2D>& Path = MapRoute.Num() > 0 ? MapRoute
		: FEXDesertTerrain::RoutePath(bSafeRoute ? FEXDesertTerrain::ERoute::Safe : FEXDesertTerrain::ERoute::Racing);
	// Long enough to finish the route at the test speed, with a screenshot spread over it (at most 30).
	const float TimeLimit = FMath::Max(140.0f, Path.Num() * 5.0f / TestSpeed * 1.3f);
	const float ShotEvery = FMath::Max(6.0f, TimeLimit / 30.0f);
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
	// Like a driver: the tightest bend in the next ~200 m sets the speed (about 2.2 g of side grip).
	float TightestM = 10000.0f;
	for (int32 Look = TestPathIndex; Look + 10 < FMath::Min(TestPathIndex + 40, Path.Num()); Look += 2)
	{
		const FVector2D A = Path[Look];
		const FVector2D B = Path[Look + 5];
		const FVector2D C = Path[Look + 10];
		const double Cross = FMath::Abs((B - A) ^ (C - B));
		if (Cross > KINDA_SMALL_NUMBER)
		{
			TightestM = FMath::Min(TightestM, static_cast<float>(FVector2D::Distance(A, B) * FVector2D::Distance(B, C) * FVector2D::Distance(C, A) / (2.0 * Cross)));
		}
	}
	const float TargetSpeed = FMath::Min(TestSpeed, FMath::Sqrt(22.0f * TightestM));
	ThrottleInput = TestTime > 1.5f && ForwardSpeedMps < TargetSpeed ? 1.0f : 0.0f;
	BrakeInput = (ForwardSpeedMps > TargetSpeed + 6.0f || (FMath::Abs(AngleDeg) > 50.0f && ForwardSpeedMps > 30.0f)) ? 1.0f : 0.0f;
	bBoostHeld = false;
	bDriftHeld = false;

	TestStuckSeconds = TestTime > 4.0f && ForwardSpeedMps < 5.0f ? TestStuckSeconds + Dt : 0.0f;
	if (TestStuckSeconds > 3.0f && TestPathIndex + 8 < Path.Num())
	{
		// Logged so the spot can be fixed, then the test carries on a little further along the route.
		UE_LOG(LogTemp, Warning, TEXT("EXDESERT STUCK at (%.0f, %.0f) path=%d"), Here.X, Here.Y, TestPathIndex);
		TestPathIndex += 8;
		const FVector2D Next = Path[TestPathIndex];
		const FVector2D Dir = (Path[FMath::Min(TestPathIndex + 2, Path.Num() - 1)] - Next).GetSafeNormal();
		SetActorLocation(FVector(Next.X * CmPerM, Next.Y * CmPerM, Location.Z + 2000.0f), false, nullptr, ETeleportType::TeleportPhysics);
		Heading = FVector(Dir.X, Dir.Y, 0.0f);
		VelocityCmps = FVector::ZeroVector;
		TestStuckSeconds = 0.0f;
	}
	const int32 ShotIndex = FMath::FloorToInt(TestTime / ShotEvery);
	if (TestTime > 2.0f && ShotIndex < 30 && !(TestShotMask & (1 << ShotIndex)))
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
	if (TestTime > TimeLimit || TestPathIndex >= Path.Num() - 1 || bLost)
	{
		UE_LOG(LogTemp, Display, TEXT("EXDESERT DONE t=%.0f path=%d/%d lost=%d"), TestTime, TestPathIndex, Path.Num(), bLost ? 1 : 0);
		FPlatformMisc::RequestExit(false);
	}
}

void AEXHoverCraft::RunTour(float Dt)
{
	// Viewpoints of the S01 geology (metres): where the camera stands, its eye height, what it looks at and how high.
	struct FView
	{
		FVector2D From;
		float EyeM;
		FVector2D To;
		float TargetM;
	};
	static const FView Views[] = {
		{ FVector2D(-2150, -1400), 3.0f, FVector2D(-700, -350), 60.0f },  // the grid: arch mesa on the horizon
		{ FVector2D(-650, -1000), 3.0f, FVector2D(-700, -350), 50.0f },   // approach wash, closest to the arch
		{ FVector2D(-835, -640), 5.0f, FVector2D(-700, -350), 70.0f },    // arch mesa from the south-west
		{ FVector2D(223, -711), 3.0f, FVector2D(175, -590), 40.0f },      // island butte from the RACING line
		{ FVector2D(101, -404), 3.0f, FVector2D(175, -590), 40.0f },      // island butte from the SAFE wash
		{ FVector2D(-160, -790), 2.5f, FVector2D(95, -748), 0.0f },       // slab field and its jumps
		{ FVector2D(520, -470), 2.5f, FVector2D(650, -400), 2.0f },       // the seep in the rejoin bowl
		{ FVector2D(850, -430), 3.0f, FVector2D(1250, -380), -10.0f },    // into the canyon head
		{ FVector2D(1450, -400), 3.0f, FVector2D(1700, -450), -40.0f },   // along the canyon
		{ FVector2D(1600, -420), 3.0f, FVector2D(1600, -480), -15.0f },   // Wingate wall close up
		{ FVector2D(2100, -560), 3.0f, FVector2D(2250, -600), -45.0f },   // box canyon head
		{ FVector2D(-500, 800), 3.0f, FVector2D(-500, 1700), 80.0f },     // Navajo escarpment to the north
		{ FVector2D(-2300, -1700), 120.0f, FVector2D(-500, -700), 0.0f }, // aerial over the basin
		{ FVector2D(-2300, -2000), 3.0f, FVector2D(-2500, -2400), 5.0f }, // dune sea
	};
	constexpr float SecondsPerView = 3.5f;
	TestTime += Dt;
	const int32 Index = FMath::FloorToInt(TestTime / SecondsPerView);
	const int32 ViewCount = LookViews.Num() > 0 ? LookViews.Num() : UE_ARRAY_COUNT(Views);
	if (Index >= ViewCount)
	{
		UE_LOG(LogTemp, Display, TEXT("EXTOUR DONE"));
		FPlatformMisc::RequestExit(false);
		return;
	}
	if (LookViews.Num() > 0)
	{
		TourCameraLocation = LookViews[Index].Key;
		TourCameraRotation = LookViews[Index].Value;
	}
	else
	{
		const FView& View = Views[Index];
		const FVector Eye(View.From.X * CmPerM, View.From.Y * CmPerM, (FEXDesertTerrain::HeightAt(View.From.X, View.From.Y) + View.EyeM) * CmPerM);
		const FVector Target(View.To.X * CmPerM, View.To.Y * CmPerM, (FEXDesertTerrain::HeightAt(View.To.X, View.To.Y) + View.TargetM) * CmPerM);
		TourCameraLocation = Eye;
		TourCameraRotation = (Target - Eye).Rotation();
	}
	ThrottleInput = 0.0f;
	if (TestTime - Index * SecondsPerView > 2.8f && !(TestShotMask & (1 << Index)))
	{
		TestShotMask |= 1 << Index;
		FScreenshotRequest::RequestScreenshot(FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Tour"), FString::Printf(TEXT("tour_%02d.png"), Index)), false, false);
		UE_LOG(LogTemp, Display, TEXT("EXTOUR shot %d fps=%.0f"), Index, Dt > 0.0f ? 1.0f / Dt : 0.0f);
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


void AEXHoverCraft::EnterHangar()
{
	bInHangar = true;
	bRaceHold = true;
	bShipLocked = false;
	VelocityCmps = FVector::ZeroVector;
	ForwardSpeedMps = 0.0f;
	LateralSpeedMps = 0.0f;
	HangarOrbitYaw = 40.0f;
	HangarOrbitPitch = 14.0f;
	HangarOrbitDist = 680.0f;
	bHangarAutoRotate = true;
	HangarIdleTime = 0.0f;
	HoverBobTime = 0.0f;
	if (Camera)
	{
		Camera->SetUsingAbsoluteLocation(true);
		Camera->SetUsingAbsoluteRotation(true);
	}
}

void AEXHoverCraft::ExitHangar()
{
	bInHangar = false;
	bCamInitialized = false;
	if (VisualPivot)
	{
		VisualPivot->SetRelativeLocation(FVector::ZeroVector);
		VisualPivot->SetRelativeRotation(FRotator::ZeroRotator);
	}
}

void AEXHoverCraft::UpdateHangar(float Dt)
{
	const float YawDelta = SteerInput * 90.0f + LookYawInput * 120.0f;
	const float PitchDelta = (ThrottleInput - BrakeInput + HangarPitchInput) * 50.0f;
	if (!FMath::IsNearlyZero(YawDelta) || !FMath::IsNearlyZero(PitchDelta))
	{
		bHangarAutoRotate = false;
		HangarIdleTime = 0.0f;
		HangarOrbitYaw += YawDelta * Dt;
		HangarOrbitPitch = FMath::Clamp(HangarOrbitPitch + PitchDelta * Dt, -10.0f, 75.0f);
	}
	else
	{
		HangarIdleTime += Dt;
		if (HangarIdleTime > 4.0f)
		{
			bHangarAutoRotate = true;
		}
	}

	if (bHangarAutoRotate)
	{
		HangarOrbitYaw += 16.0f * Dt;
	}
	HangarOrbitYaw = FMath::Fmod(HangarOrbitYaw, 360.0f);

	HoverBobTime += Dt;
	const float BobZ = FMath::Sin(HoverBobTime * 1.6f) * 4.0f;
	VisualRoll = FMath::FInterpTo(VisualRoll, 0.0f, Dt, 6.0f);
	VisualPitch = FMath::FInterpTo(VisualPitch, 0.0f, Dt, 6.0f);
	VisualYaw = FMath::FInterpTo(VisualYaw, 0.0f, Dt, 6.0f);
	if (VisualPivot)
	{
		VisualPivot->SetRelativeLocation(FVector(0.0f, 0.0f, BobZ));
		VisualPivot->SetRelativeRotation(FRotator::ZeroRotator);
	}

	const FRotator OrbitRot(HangarOrbitPitch, HangarOrbitYaw, 0.0f);
	const FVector TargetFocus = GetActorLocation() + FVector(0.0f, 0.0f, 35.0f);
	const FVector CamLoc = TargetFocus - OrbitRot.Vector() * HangarOrbitDist;
	Camera->SetWorldLocationAndRotation(CamLoc, OrbitRot);
	Camera->SetFieldOfView(58.0f);
}

void AEXHoverCraft::HangarZoomIn()
{
	if (bInHangar)
	{
		HangarOrbitDist = FMath::Clamp(HangarOrbitDist - 40.0f, 320.0f, 1400.0f);
	}
}

void AEXHoverCraft::HangarZoomOut()
{
	if (bInHangar)
	{
		HangarOrbitDist = FMath::Clamp(HangarOrbitDist + 40.0f, 320.0f, 1400.0f);
	}
}

void AEXHoverCraft::HangarToggleAutoRotate()
{
	if (bInHangar)
	{
		bHangarAutoRotate = !bHangarAutoRotate;
		HangarIdleTime = 0.0f;
	}
}

void AEXHoverCraft::HangarBack()
{
	if (!bInHangar)
	{
		return;
	}
	ExitHangar();
	for (TActorIterator<AEXRaceDirector> It(GetWorld()); It; ++It)
	{
		It->OpenMenu();
		break;
	}
}

void AEXHoverCraft::HangarConfirm()
{
	if (!bInHangar)
	{
		return;
	}
	ExitHangar();
	for (TActorIterator<AEXRaceDirector> It(GetWorld()); It; ++It)
	{
		It->OpenMenu();
		break;
	}
}
