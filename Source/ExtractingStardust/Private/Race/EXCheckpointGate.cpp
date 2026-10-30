#include "Race/EXCheckpointGate.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	// Solid painted gates, no light (player, 2026-10-29: "portões sólidos sem ser de luz"; the see-through glow on 400 m
	// beams also made the race stutter): the ships' master material, kind 0 (paint under a clear coat).
	const FName GateColorParam(TEXT("Colour"));
	const FName GateKindParam(TEXT("Kind"));
	const FName GateRoughParam(TEXT("Roughness"));
	const FName GateCoatParam(TEXT("Coat"));
	const FName GateEmitParam(TEXT("Emit"));
	constexpr float PylonHeightCm = 2400.0f;
	constexpr float PylonWidthCm = 220.0f;
	const FLinearColor GateNext(0.05f, 0.55f, 0.75f);
	const FLinearColor GatePassed(0.12f, 0.6f, 0.2f);
	const FLinearColor GateMissed(0.75f, 0.06f, 0.03f);
	const FLinearColor GateDark(0.05f, 0.05f, 0.055f);
}

AEXCheckpointGate::AEXCheckpointGate()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	auto Make = [this](const TCHAR* Name, UStaticMesh* Mesh)
	{
		UStaticMeshComponent* Component = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		Component->SetupAttachment(GetRootComponent());
		Component->SetStaticMesh(Mesh);
		Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		return Component;
	};
	// Two square pylons, the bar across their tops, and a dark foot under each pylon.
	PylonL = Make(TEXT("PylonL"), Cube.Object);
	PylonR = Make(TEXT("PylonR"), Cube.Object);
	Bar = Make(TEXT("Bar"), Cube.Object);
	BeamL = Make(TEXT("FootL"), Cube.Object);
	BeamR = Make(TEXT("FootR"), Cube.Object);
	SetActorHiddenInGame(true);
}

void AEXCheckpointGate::Setup(const FVector& Left, const FVector& Right)
{
	// Loaded here, not in the constructor: a class default holding the ships' master material kept it loaded in the
	// editor and Scripts/make_ship_materials.py could no longer rebuild it (it asserted).
	UMaterialInterface* Paint = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Ships/M_ShipPBR.M_ShipPBR"));
	FrameMaterial = Paint ? UMaterialInstanceDynamic::Create(Paint, this) : nullptr;
	BeamMaterial = Paint ? UMaterialInstanceDynamic::Create(Paint, this) : nullptr;
	for (UMaterialInstanceDynamic* Mid : { FrameMaterial.Get(), BeamMaterial.Get() })
	{
		if (Mid)
		{
			Mid->SetScalarParameterValue(GateKindParam, 0.0f);
			Mid->SetScalarParameterValue(GateRoughParam, 0.35f);
			Mid->SetScalarParameterValue(GateCoatParam, 0.6f);
			Mid->SetScalarParameterValue(GateEmitParam, 0.0f);
		}
	}
	if (BeamMaterial)
	{
		BeamMaterial->SetVectorParameterValue(GateColorParam, GateDark);
	}
	for (UStaticMeshComponent* Part : { PylonL.Get(), PylonR.Get(), Bar.Get() })
	{
		Part->SetMaterial(0, FrameMaterial);
	}
	BeamL->SetMaterial(0, BeamMaterial);
	BeamR->SetMaterial(0, BeamMaterial);
	// Pylons from the ground up to a common top (the basic cube is 1 m, centred), the bar between their tops.
	const float TopZ = FMath::Max(Left.Z, Right.Z) + PylonHeightCm;
	const FVector Across = FVector(Right.X - Left.X, Right.Y - Left.Y, 0.0f);
	const FRotator Facing(0.0f, FMath::RadiansToDegrees(FMath::Atan2(Across.Y, Across.X)), 0.0f);
	auto Pylon = [TopZ, &Facing](UStaticMeshComponent* Part, UStaticMeshComponent* Foot, const FVector& Base)
	{
		const float Height = TopZ - Base.Z + 300.0f;   // a little into the ground
		Part->SetWorldLocationAndRotation(FVector(Base.X, Base.Y, Base.Z - 300.0f + Height * 0.5f), Facing);
		Part->SetWorldScale3D(FVector(PylonWidthCm / 100.0f, PylonWidthCm / 100.0f, Height / 100.0f));
		Foot->SetWorldLocationAndRotation(FVector(Base.X, Base.Y, Base.Z + 60.0f), Facing);
		Foot->SetWorldScale3D(FVector(PylonWidthCm / 100.0f + 1.0f, PylonWidthCm / 100.0f + 1.0f, 2.4f));
	};
	Pylon(PylonL, BeamL, Left);
	Pylon(PylonR, BeamR, Right);
	Bar->SetWorldLocationAndRotation(FVector((Left.X + Right.X) * 0.5f, (Left.Y + Right.Y) * 0.5f, TopZ - 120.0f), Facing);
	Bar->SetWorldScale3D(FVector(Across.Size() / 100.0f + PylonWidthCm / 100.0f, 1.6f, 2.4f));
}

void AEXCheckpointGate::SetState(int32 InState)
{
	if (InState == State)
	{
		return;
	}
	State = InState;
	Age = 0.0f;
	SetActorHiddenInGame(State == 0);
	SetActorTickEnabled(State == 2);
	if (FrameMaterial)
	{
		FrameMaterial->SetVectorParameterValue(GateColorParam, State == 2 ? GatePassed : (State == 3 ? GateMissed : GateNext));
	}
}

void AEXCheckpointGate::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// Passed: green for a moment, then the gate goes.
	Age += DeltaSeconds;
	if (State == 2 && Age > 1.5f)
	{
		SetState(0);
	}
}
