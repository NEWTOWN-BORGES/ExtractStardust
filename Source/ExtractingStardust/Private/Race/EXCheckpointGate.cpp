#include "Race/EXCheckpointGate.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	const FName GateColorParam(TEXT("Color"));
	const FName GateIntensityParam(TEXT("Intensity"));
	constexpr float PylonHeightCm = 2200.0f;
	constexpr float BeamHeightCm = 40000.0f;
	const FLinearColor GateNext(0.3f, 0.9f, 1.0f);
	const FLinearColor GatePassed(0.3f, 1.0f, 0.45f);
	const FLinearColor GateMissed(1.0f, 0.18f, 0.1f);
}

AEXCheckpointGate::AEXCheckpointGate()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Glow(TEXT("/Game/FX/M_FX_Glow.M_FX_Glow"));
	UMaterialInterface* GlowMaterial = Glow.Object;
	auto Make = [this, GlowMaterial](const TCHAR* Name, UStaticMesh* Mesh)
	{
		UStaticMeshComponent* Component = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		Component->SetupAttachment(GetRootComponent());
		Component->SetStaticMesh(Mesh);
		Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Component->SetCastShadow(false);
		if (GlowMaterial)
		{
			Component->SetMaterial(0, GlowMaterial);
		}
		return Component;
	};
	PylonL = Make(TEXT("PylonL"), Cylinder.Object);
	PylonR = Make(TEXT("PylonR"), Cylinder.Object);
	Bar = Make(TEXT("Bar"), Cube.Object);
	BeamL = Make(TEXT("BeamL"), Cylinder.Object);
	BeamR = Make(TEXT("BeamR"), Cylinder.Object);
	SetActorHiddenInGame(true);
}

void AEXCheckpointGate::Setup(const FVector& Left, const FVector& Right)
{
	FrameMaterial = UMaterialInstanceDynamic::Create(PylonL->GetMaterial(0), this);
	BeamMaterial = UMaterialInstanceDynamic::Create(BeamL->GetMaterial(0), this);
	for (UStaticMeshComponent* Part : { PylonL.Get(), PylonR.Get(), Bar.Get() })
	{
		Part->SetMaterial(0, FrameMaterial);
	}
	BeamL->SetMaterial(0, BeamMaterial);
	BeamR->SetMaterial(0, BeamMaterial);
	// Pylons from the ground up (the basic cylinder is 1 m across and 1 m tall, centred), the bar between their tops
	// (at the higher one), the beams on top of the pylons.
	const float TopZ = FMath::Max(Left.Z, Right.Z) + PylonHeightCm;
	auto Pylon = [TopZ](UStaticMeshComponent* Part, const FVector& Foot)
	{
		const float Height = TopZ - Foot.Z + 300.0f;   // a little into the ground
		Part->SetWorldLocation(FVector(Foot.X, Foot.Y, Foot.Z - 300.0f + Height * 0.5f));
		Part->SetWorldScale3D(FVector(1.6f, 1.6f, Height / 100.0f));
	};
	Pylon(PylonL, Left);
	Pylon(PylonR, Right);
	const FVector Across = FVector(Right.X - Left.X, Right.Y - Left.Y, 0.0f);
	Bar->SetWorldLocation(FVector((Left.X + Right.X) * 0.5f, (Left.Y + Right.Y) * 0.5f, TopZ - 60.0f));
	Bar->SetWorldRotation(FRotator(0.0f, FMath::RadiansToDegrees(FMath::Atan2(Across.Y, Across.X)), 0.0f));
	Bar->SetWorldScale3D(FVector(Across.Size() / 100.0f, 1.2f, 1.2f));
	for (const TPair<UStaticMeshComponent*, FVector>& Beam : { TPair<UStaticMeshComponent*, FVector>(BeamL, Left), TPair<UStaticMeshComponent*, FVector>(BeamR, Right) })
	{
		Beam.Key->SetWorldLocation(FVector(Beam.Value.X, Beam.Value.Y, TopZ + BeamHeightCm * 0.5f));
		Beam.Key->SetWorldScale3D(FVector(2.2f, 2.2f, BeamHeightCm / 100.0f));
	}
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
	SetActorTickEnabled(State != 0);
	const FLinearColor Colour = State == 2 ? GatePassed : (State == 3 ? GateMissed : GateNext);
	if (FrameMaterial)
	{
		FrameMaterial->SetVectorParameterValue(GateColorParam, Colour);
	}
	if (BeamMaterial)
	{
		BeamMaterial->SetVectorParameterValue(GateColorParam, Colour);
	}
}

void AEXCheckpointGate::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;
	float Frame = 6.0f, Beam = 2.4f;
	if (State == 1)
	{
		Frame *= 0.8f + 0.2f * FMath::Sin(Age * 4.0f);
		Beam *= 0.7f + 0.3f * FMath::Sin(Age * 3.0f);
	}
	else if (State == 2)
	{
		// Passed: a bright flash that fades out in 1.5 s, then the gate goes.
		const float T = FMath::Clamp(Age / 1.5f, 0.0f, 1.0f);
		Frame *= 3.0f * (1.0f - T);
		Beam *= 2.0f * (1.0f - T);
		if (T >= 1.0f)
		{
			SetState(0);
			return;
		}
	}
	else if (State == 3)
	{
		const float Blink = 0.55f + 0.45f * FMath::Sin(Age * 9.0f);
		Frame *= Blink * 1.3f;
		Beam *= Blink * 1.5f;
	}
	if (FrameMaterial)
	{
		FrameMaterial->SetScalarParameterValue(GateIntensityParam, Frame);
	}
	if (BeamMaterial)
	{
		BeamMaterial->SetScalarParameterValue(GateIntensityParam, Beam);
	}
}
