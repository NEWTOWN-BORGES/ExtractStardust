#include "StardustHoverPawn.h"
#include "StardustProfileSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"

AStardustHoverPawn::AStardustHoverPawn()
{
	PrimaryActorTick.bCanEverTick = true;
	CraftBody = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CraftBody"));
	SetRootComponent(CraftBody);
	CraftBody->SetCollisionProfileName(TEXT("Pawn"));
	CraftBody->SetSimulatePhysics(false);

	CameraArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraArm"));
	CameraArm->SetupAttachment(CraftBody);
	CameraArm->TargetArmLength = 900.0f;
	CameraArm->SetRelativeLocation(FVector(0.0f, 0.0f, 240.0f));
	CameraArm->SetRelativeRotation(FRotator(-12.0f, 0.0f, 0.0f));
	CameraArm->bEnableCameraLag = true;
	CameraArm->CameraLagSpeed = 5.0f;
	CameraArm->bDoCollisionTest = true;

	ChaseCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("ChaseCamera"));
	ChaseCamera->SetupAttachment(CameraArm);
}

void AStardustHoverPawn::BeginPlay()
{
	Super::BeginPlay();
	SpawnLocation = GetActorLocation();
	SpawnRotation = GetActorRotation();
	if (UStaticMesh* ImportedChassis = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Stardust/Vehicles/strix.strix")))
	{
		CraftBody->SetStaticMesh(ImportedChassis);
	}
}

void AStardustHoverPawn::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	PlayerInputComponent->BindAxis(TEXT("Throttle"), this, &AStardustHoverPawn::SetThrottle);
	PlayerInputComponent->BindAxis(TEXT("Steer"), this, &AStardustHoverPawn::SetSteering);
	PlayerInputComponent->BindAxis(TEXT("Brake"), this, &AStardustHoverPawn::SetBrake);
	PlayerInputComponent->BindAxis(TEXT("Nitro"), this, &AStardustHoverPawn::SetNitro);
	PlayerInputComponent->BindAction(TEXT("Consumable1"), IE_Pressed, this, &AStardustHoverPawn::ActivateSlot0);
	PlayerInputComponent->BindAction(TEXT("Consumable2"), IE_Pressed, this, &AStardustHoverPawn::ActivateSlot1);
	PlayerInputComponent->BindAction(TEXT("Consumable3"), IE_Pressed, this, &AStardustHoverPawn::ActivateSlot2);
	PlayerInputComponent->BindAction(TEXT("Consumable4"), IE_Pressed, this, &AStardustHoverPawn::ActivateSlot3);
	PlayerInputComponent->BindAction(TEXT("ResetCraft"), IE_Pressed, this, &AStardustHoverPawn::ResetCraft);
}

void AStardustHoverPawn::SetControlInput(float Throttle, float Steering, float BrakeValue, float NitroValue)
{
	ThrottleInput = FMath::Clamp(Throttle, -1.0f, 1.0f);
	SteeringInput = FMath::Clamp(Steering, -1.0f, 1.0f);
	BrakeInput = FMath::Clamp(BrakeValue, 0.0f, 1.0f);
	NitroInput = FMath::Clamp(NitroValue, 0.0f, 1.0f);
}

void AStardustHoverPawn::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const float Dt = FMath::Min(DeltaSeconds, 0.05f);
	const FVector Forward = GetActorForwardVector();
	const float NitroFactor = (NitroInput > 0.1f && BoostFuel > 0.0f) ? 1.65f : 1.0f;
	Velocity += Forward * (ThrottleInput * Acceleration * NitroFactor * Dt);
	if (NitroFactor > 1.0f)
	{
		BoostFuel = FMath::Max(0.0f, BoostFuel - 18.0f * Dt);
		Heat = FMath::Min(100.0f, Heat + 10.0f * Dt);
	}
	else
	{
		BoostFuel = FMath::Min(100.0f, BoostFuel + 4.0f * Dt);
		Heat = FMath::Max(0.0f, Heat - 7.0f * Dt);
	}

	const float Drag = BrakeInput > 0.1f ? 2.8f : 0.34f;
	Velocity *= FMath::Max(0.0f, 1.0f - Drag * Dt);
	Velocity = Velocity.GetClampedToMaxSize(MaxSpeed * NitroFactor);
	const float SpeedFactor = FMath::Clamp(Velocity.Size() / 900.0f, 0.18f, 1.0f);
	const float StabilityFactor = StabilizerTime > 0.0f ? 0.72f : 1.0f;
	AddActorWorldRotation(FRotator(0.0f, SteeringInput * TurnRate * SpeedFactor * StabilityFactor * Dt, 0.0f));
	StabilizerTime = FMath::Max(0.0f, StabilizerTime - Dt);

	FHitResult GroundHit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(StardustHoverTrace), false, this);
	const FVector TraceStart = GetActorLocation() + FVector(0.0f, 0.0f, 30.0f);
	const FVector TraceEnd = TraceStart - FVector(0.0f, 0.0f, HoverHeight + 450.0f);
	const bool bGrounded = GetWorld()->LineTraceSingleByChannel(GroundHit, TraceStart, TraceEnd, ECC_Visibility, Params);
	if (bGrounded)
	{
		const float CurrentHeight = GroundHit.Distance - 30.0f;
		const float Error = HoverHeight - CurrentHeight;
		VerticalSpeed += (Error * HoverSpring * 100.0f - VerticalSpeed * HoverDamping) * Dt;
		const FVector DesiredForward = FVector::VectorPlaneProject(GetActorForwardVector(), GroundHit.ImpactNormal).GetSafeNormal();
		if (!DesiredForward.IsNearlyZero())
		{
			const FRotator AlignedRotation = FRotationMatrix::MakeFromXZ(DesiredForward, GroundHit.ImpactNormal).Rotator();
			SetActorRotation(FMath::RInterpTo(GetActorRotation(), AlignedRotation, Dt, 3.0f));
		}
	}
	else
	{
		VerticalSpeed -= 980.0f * Dt;
	}
	VerticalSpeed = FMath::Clamp(VerticalSpeed, -1600.0f, 1600.0f);
	FVector FrameVelocity = Velocity;
	FrameVelocity.Z = VerticalSpeed;
	FHitResult MoveHit;
	AddActorWorldOffset(FrameVelocity * Dt, true, &MoveHit);
	if (MoveHit.IsValidBlockingHit())
	{
		Velocity = FVector::VectorPlaneProject(Velocity, MoveHit.ImpactNormal) * 0.72f;
		VerticalSpeed = FMath::Max(0.0f, VerticalSpeed);
		Hull = FMath::Max(0.0f, Hull - FMath::Clamp(MoveHit.ImpactNormal.IsNearlyZero() ? 2.0f : Velocity.Size() / 180.0f, 1.0f, 15.0f));
	}
	if (RepairTime > 0.0f)
	{
		Hull = FMath::Min(100.0f, Hull + 3.125f * Dt);
		RepairTime = FMath::Max(0.0f, RepairTime - Dt);
	}
}

void AStardustHoverPawn::ActivateConsumable(int32 Slot)
{
	if (Slot < 0 || Slot >= 4 || !GetGameInstance()) return;
	UStardustProfileSubsystem* Profile = GetGameInstance()->GetSubsystem<UStardustProfileSubsystem>();
	FName ItemId;
	if (!Profile || !Profile->ConsumeLoadoutSlot(Slot, ItemId))
	{
		if (GEngine) GEngine->AddOnScreenDebugMessage(-1, 1.5f, FColor::Red, FString::Printf(TEXT("Consumível %d vazio"), Slot + 1));
		return;
	}
	if (ItemId == FName(TEXT("repair")) || ItemId == FName(TEXT("foam"))) RepairTime = 8.0f;
	else if (ItemId == FName(TEXT("fuel"))) BoostFuel = FMath::Min(100.0f, BoostFuel + 30.0f);
	else if (ItemId == FName(TEXT("coolant"))) Heat = FMath::Max(0.0f, Heat - 45.0f);
	else if (ItemId == FName(TEXT("surge"))) { BoostFuel = FMath::Min(100.0f, BoostFuel + 70.0f); Heat = FMath::Min(100.0f, Heat + 12.0f); }
	else if (ItemId == FName(TEXT("stabilizer")) || ItemId == FName(TEXT("stab"))) StabilizerTime = 8.0f;
	Profile->SaveProfile();
	if (GEngine) GEngine->AddOnScreenDebugMessage(-1, 1.2f, FColor::Green, FString::Printf(TEXT("Slot %d: %s"), Slot + 1, *ItemId.ToString()));
}

void AStardustHoverPawn::ResetCraft()
{
	SetActorLocation(SpawnLocation);
	SetActorRotation(SpawnRotation);
	Velocity = FVector::ZeroVector;
	VerticalSpeed = 0.0f;
	Hull = 100.0f;
}

int32 AStardustHoverPawn::GetLoadoutCount(int32 Slot) const
{
	if (!GetGameInstance()) return 0;
	const UStardustProfileSubsystem* Profile = GetGameInstance()->GetSubsystem<UStardustProfileSubsystem>();
	return Profile && Profile->GetProfile().Loadout.IsValidIndex(Slot) ? Profile->GetProfile().Loadout[Slot].Count : 0;
}
