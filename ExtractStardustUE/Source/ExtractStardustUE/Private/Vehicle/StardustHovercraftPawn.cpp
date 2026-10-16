#include "Vehicle/StardustHovercraftPawn.h"

#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/SpringArmComponent.h"
#include "UObject/ConstructorHelpers.h"
#include "Vehicle/StardustCraftMovementComponent.h"

AStardustHovercraftPawn::AStardustHovercraftPawn()
{
	PrimaryActorTick.bCanEverTick = false;
	HullMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Hull"));
	SetRootComponent(HullMesh);
	HullMesh->SetCollisionProfileName(TEXT("PhysicsActor"));
	HullMesh->SetSimulatePhysics(true);
	HullMesh->SetNotifyRigidBodyCollision(true);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		HullMesh->SetStaticMesh(CubeMesh.Object);
	}

	MovementComponent = CreateDefaultSubobject<UStardustCraftMovementComponent>(TEXT("CraftMovement"));
	MovementComponent->Input.Throttle = 0.0f;
	const FVector HullSize = MovementComponent->Tuning.HullSizeM;
	HullMesh->SetRelativeScale3D(FVector(HullSize.Z, HullSize.X, HullSize.Y));

	CameraArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraArm"));
	CameraArm->SetupAttachment(HullMesh);
	CameraArm->TargetArmLength = 900.0f;
	CameraArm->SetRelativeLocation(FVector(0.0f, 0.0f, 110.0f));
	CameraArm->SetRelativeRotation(FRotator(-12.0f, 0.0f, 0.0f));
	CameraArm->bEnableCameraLag = true;
	CameraArm->CameraLagSpeed = 8.0f;

	ChaseCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("ChaseCamera"));
	ChaseCamera->SetupAttachment(CameraArm);
	ChaseCamera->bUsePawnControlRotation = false;

	AutoPossessPlayer = EAutoReceiveInput::Player0;
}

void AStardustHovercraftPawn::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	PlayerInputComponent->BindAxis(TEXT("Throttle"), this, &AStardustHovercraftPawn::SetThrottle);
	PlayerInputComponent->BindAxis(TEXT("Steer"), this, &AStardustHovercraftPawn::SetSteer);
	PlayerInputComponent->BindAxis(TEXT("AirPitch"), this, &AStardustHovercraftPawn::SetAirPitch);
	PlayerInputComponent->BindAction(TEXT("Brake"), IE_Pressed, this, &AStardustHovercraftPawn::PressBrake);
	PlayerInputComponent->BindAction(TEXT("Brake"), IE_Released, this, &AStardustHovercraftPawn::ReleaseBrake);
	PlayerInputComponent->BindAction(TEXT("Boost"), IE_Pressed, this, &AStardustHovercraftPawn::PressBoost);
	PlayerInputComponent->BindAction(TEXT("Boost"), IE_Released, this, &AStardustHovercraftPawn::ReleaseBoost);
	PlayerInputComponent->BindAction(TEXT("Drift"), IE_Pressed, this, &AStardustHovercraftPawn::PressDrift);
	PlayerInputComponent->BindAction(TEXT("Drift"), IE_Released, this, &AStardustHovercraftPawn::ReleaseDrift);
}

void AStardustHovercraftPawn::ApplyInput()
{
	if (MovementComponent)
	{
		MovementComponent->SetInput(PendingInput);
	}
}

void AStardustHovercraftPawn::SetThrottle(float Value)
{
	PendingInput.Throttle = FMath::Clamp(Value, 0.0f, 1.0f);
	ApplyInput();
}

void AStardustHovercraftPawn::SetSteer(float Value)
{
	PendingInput.Steer = FMath::Clamp(Value, -1.0f, 1.0f);
	ApplyInput();
}

void AStardustHovercraftPawn::SetAirPitch(float Value)
{
	PendingInput.AirPitch = FMath::Clamp(Value, -1.0f, 1.0f);
	ApplyInput();
}

void AStardustHovercraftPawn::PressBrake()
{
	PendingInput.bBrake = true;
	ApplyInput();
}

void AStardustHovercraftPawn::ReleaseBrake()
{
	PendingInput.bBrake = false;
	ApplyInput();
}

void AStardustHovercraftPawn::PressBoost()
{
	PendingInput.bBoost = true;
	ApplyInput();
}

void AStardustHovercraftPawn::ReleaseBoost()
{
	PendingInput.bBoost = false;
	ApplyInput();
}

void AStardustHovercraftPawn::PressDrift()
{
	PendingInput.bDrift = true;
	ApplyInput();
}

void AStardustHovercraftPawn::ReleaseDrift()
{
	PendingInput.bDrift = false;
	ApplyInput();
}
