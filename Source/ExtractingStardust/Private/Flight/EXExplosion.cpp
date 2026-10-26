#include "Flight/EXExplosion.h"

#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	const FName BlastColorParam(TEXT("Color"));
	const FName BlastIntensityParam(TEXT("Intensity"));
	const FName BlastOpacityParam(TEXT("Opacity"));
	constexpr float BlastLife = 4.5f;
	constexpr float GravityCmps2 = 1470.0f;   // debris falls a little faster than real: it reads better at race speed
}

AEXExplosion::AEXExplosion()
{
	PrimaryActorTick.bCanEverTick = true;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Glow(TEXT("/Game/FX/M_FX_Glow.M_FX_Glow"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Dust(TEXT("/Game/FX/M_FX_Dust.M_FX_Dust"));
	SphereMesh = Sphere.Object;
	CubeMesh = Cube.Object;
	CylinderMesh = Cylinder.Object;
	GlowMaterial = Glow.Object;
	DustMaterial = Dust.Object;
	Flash = CreateDefaultSubobject<UPointLightComponent>(TEXT("Flash"));
	Flash->SetupAttachment(GetRootComponent());
	Flash->SetMobility(EComponentMobility::Movable);
	Flash->SetCastShadows(false);
	Flash->SetIntensityUnits(ELightUnits::Candelas);
	Flash->SetIntensity(0.0f);
	Flash->SetAttenuationRadius(9000.0f);
	Flash->SetLightColor(FLinearColor(1.0f, 0.62f, 0.3f));
}

UStaticMeshComponent* AEXExplosion::MakeMesh(UStaticMesh* Mesh, UMaterialInterface* Material, UMaterialInstanceDynamic*& OutMaterial)
{
	UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(this);
	Component->SetStaticMesh(Mesh);
	Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Component->SetCastShadow(false);
	Component->SetUsingAbsoluteLocation(true);
	Component->SetUsingAbsoluteRotation(true);
	Component->SetUsingAbsoluteScale(true);
	Component->SetupAttachment(GetRootComponent());
	Component->RegisterComponent();
	OutMaterial = Material ? UMaterialInstanceDynamic::Create(Material, this) : nullptr;
	if (OutMaterial)
	{
		Component->SetMaterial(0, OutMaterial);
	}
	return Component;
}

void AEXExplosion::Ignite(const FVector& CraftVelocityCmps, float Strength)
{
	Scale = FMath::Clamp(Strength, 0.3f, 1.5f);
	Drift = CraftVelocityCmps * 0.45f;
	const FVector Origin = GetActorLocation();
	FRandomStream Random(FMath::Rand());

	// Fireball: white-hot core, orange body, red rim; each swells to its size and burns out.
	const FLinearColor FireColours[3] = { FLinearColor(1.0f, 0.92f, 0.7f), FLinearColor(1.0f, 0.45f, 0.08f), FLinearColor(0.9f, 0.12f, 0.03f) };
	const float FireSizes[3] = { 10.0f, 16.0f, 22.0f };      // metres across at the end
	const float FireIntensity[3] = { 60.0f, 28.0f, 12.0f };
	for (int32 Layer = 0; Layer < 3; ++Layer)
	{
		FBit Bit;
		Bit.Mesh = MakeMesh(SphereMesh, GlowMaterial, Bit.Material);
		Bit.Size = 0.6f;
		Bit.EndSize = FireSizes[Layer] * Scale;
		Bit.Intensity = FireIntensity[Layer];
		Bit.Life = 0.9f + 0.35f * Layer;
		if (Bit.Material)
		{
			Bit.Material->SetVectorParameterValue(BlastColorParam, FireColours[Layer]);
		}
		Bit.Mesh->SetWorldLocation(Origin);
		Fireball.Add(Bit);
	}
	// The shock ring along the ground.
	{
		FBit Bit;
		Bit.Mesh = MakeMesh(CylinderMesh, GlowMaterial, Bit.Material);
		Bit.Size = 1.0f;
		Bit.EndSize = 46.0f * Scale;
		Bit.Intensity = 9.0f;
		Bit.Life = 0.55f;
		if (Bit.Material)
		{
			Bit.Material->SetVectorParameterValue(BlastColorParam, FLinearColor(1.0f, 0.6f, 0.25f));
		}
		Bit.Mesh->SetWorldLocation(Origin - FVector(0.0f, 0.0f, 120.0f));
		Ring.Add(Bit);
	}
	// Burning debris: hull plates thrown out and up, tumbling, cooling from orange to dark.
	for (int32 Index = 0; Index < 18; ++Index)
	{
		FBit Bit;
		Bit.Mesh = MakeMesh(CubeMesh, GlowMaterial, Bit.Material);
		const FVector Out = (Random.VRand() + FVector(0.0f, 0.0f, 0.9f)).GetSafeNormal();
		Bit.Velocity = Drift * 1.2f + Out * Random.FRandRange(1500.0f, 4200.0f) * Scale;
		Bit.Spin = FRotator(Random.FRandRange(-720.0f, 720.0f), Random.FRandRange(-720.0f, 720.0f), Random.FRandRange(-720.0f, 720.0f));
		Bit.Size = Random.FRandRange(0.25f, 0.8f);
		Bit.EndSize = Bit.Size;
		Bit.Intensity = Random.FRandRange(6.0f, 14.0f);
		Bit.Life = Random.FRandRange(1.6f, 2.8f);
		if (Bit.Material)
		{
			Bit.Material->SetVectorParameterValue(BlastColorParam, FLinearColor(1.0f, 0.4f, 0.1f));
		}
		Bit.Mesh->SetWorldLocationAndRotation(Origin + Out * 150.0f, Random.GetUnitVector().Rotation());
		Bit.Mesh->SetWorldScale3D(FVector(Bit.Size, Bit.Size * 0.6f, Bit.Size * 0.15f));
		Debris.Add(Bit);
	}
	// Sparks: small and fast.
	for (int32 Index = 0; Index < 34; ++Index)
	{
		FBit Bit;
		Bit.Mesh = MakeMesh(SphereMesh, GlowMaterial, Bit.Material);
		Bit.Velocity = Drift + Random.VRand() * Random.FRandRange(3000.0f, 7500.0f) * Scale + FVector(0.0f, 0.0f, 1200.0f);
		Bit.Size = Random.FRandRange(0.08f, 0.16f);
		Bit.EndSize = Bit.Size * 0.3f;
		Bit.Intensity = 40.0f;
		Bit.Life = Random.FRandRange(0.4f, 1.1f);
		if (Bit.Material)
		{
			Bit.Material->SetVectorParameterValue(BlastColorParam, FLinearColor(1.0f, 0.75f, 0.35f));
		}
		Bit.Mesh->SetWorldLocation(Origin);
		Sparks.Add(Bit);
	}
	// Smoke: dark, rising and spreading, lit a little by the fire at first.
	for (int32 Index = 0; Index < 14; ++Index)
	{
		FBit Bit;
		Bit.Mesh = MakeMesh(SphereMesh, DustMaterial, Bit.Material);
		const FVector Out = Random.VRand() * FVector(1.0f, 1.0f, 0.4f);
		Bit.Velocity = Drift * 0.5f + Out * Random.FRandRange(300.0f, 900.0f) + FVector(0.0f, 0.0f, Random.FRandRange(250.0f, 600.0f));
		Bit.Size = Random.FRandRange(2.5f, 4.5f) * Scale;
		Bit.EndSize = Random.FRandRange(11.0f, 18.0f) * Scale;
		Bit.Intensity = Random.FRandRange(0.45f, 0.7f);   // opacity
		Bit.Life = Random.FRandRange(2.8f, 4.3f);
		if (Bit.Material)
		{
			Bit.Material->SetVectorParameterValue(BlastColorParam, FLinearColor(0.05f, 0.04f, 0.035f));
			Bit.Material->SetScalarParameterValue(BlastOpacityParam, 0.0f);
		}
		Bit.Mesh->SetWorldLocation(Origin + Out * 200.0f);
		Smoke.Add(Bit);
	}
	bLit = true;
	Tick(0.0f);
}

void AEXExplosion::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bLit)
	{
		return;
	}
	Age += DeltaSeconds;
	if (Age > BlastLife)
	{
		Destroy();
		return;
	}
	// The whole blast drifts on with the craft's speed, slowing quickly.
	Drift *= FMath::Exp(-2.5f * DeltaSeconds);
	const FVector Shift = Drift * DeltaSeconds;
	SetActorLocation(GetActorLocation() + Shift);

	Flash->SetIntensity(90000.0f * Scale * FMath::Exp(-Age * 5.0f));

	for (FBit& Bit : Fireball)
	{
		const float T = FMath::Clamp(Age / Bit.Life, 0.0f, 1.0f);
		const float Size = FMath::Lerp(Bit.Size, Bit.EndSize, 1.0f - FMath::Exp(-Age * 7.0f));
		Bit.Mesh->SetWorldLocation(Bit.Mesh->GetComponentLocation() + Shift);
		Bit.Mesh->SetWorldScale3D(FVector(Size));   // the engine sphere is 1 m across: the scale is the size in metres
		Bit.Mesh->SetVisibility(T < 1.0f);
		if (Bit.Material)
		{
			Bit.Material->SetScalarParameterValue(BlastIntensityParam, Bit.Intensity * FMath::Square(1.0f - T));
		}
	}
	for (FBit& Bit : Ring)
	{
		const float T = FMath::Clamp(Age / Bit.Life, 0.0f, 1.0f);
		const float Size = FMath::Lerp(Bit.Size, Bit.EndSize, FMath::Sqrt(T));
		Bit.Mesh->SetWorldLocation(Bit.Mesh->GetComponentLocation() + Shift);
		Bit.Mesh->SetWorldScale3D(FVector(Size, Size, 0.03f));
		Bit.Mesh->SetVisibility(T < 1.0f);
		if (Bit.Material)
		{
			Bit.Material->SetScalarParameterValue(BlastIntensityParam, Bit.Intensity * (1.0f - T));
		}
	}
	for (FBit& Bit : Debris)
	{
		const float T = FMath::Clamp(Age / Bit.Life, 0.0f, 1.0f);
		Bit.Velocity.Z -= GravityCmps2 * DeltaSeconds;
		Bit.Velocity *= FMath::Exp(-0.6f * DeltaSeconds);
		Bit.Mesh->SetWorldLocationAndRotation(Bit.Mesh->GetComponentLocation() + Bit.Velocity * DeltaSeconds,
			Bit.Mesh->GetComponentRotation() + Bit.Spin * DeltaSeconds);
		Bit.Mesh->SetVisibility(T < 1.0f);
		if (Bit.Material)
		{
			// Cools from orange-hot to a dull ember.
			Bit.Material->SetScalarParameterValue(BlastIntensityParam, FMath::Max(0.15f, Bit.Intensity * FMath::Exp(-T * 3.0f)));
		}
	}
	for (FBit& Bit : Sparks)
	{
		const float T = FMath::Clamp(Age / Bit.Life, 0.0f, 1.0f);
		Bit.Velocity.Z -= GravityCmps2 * DeltaSeconds;
		Bit.Velocity *= FMath::Exp(-1.5f * DeltaSeconds);
		Bit.Mesh->SetWorldLocation(Bit.Mesh->GetComponentLocation() + Bit.Velocity * DeltaSeconds);
		const float Size = FMath::Lerp(Bit.Size, Bit.EndSize, T);
		Bit.Mesh->SetWorldScale3D(FVector(Size));
		Bit.Mesh->SetVisibility(T < 1.0f);
		if (Bit.Material)
		{
			Bit.Material->SetScalarParameterValue(BlastIntensityParam, Bit.Intensity * (1.0f - T));
		}
	}
	for (FBit& Bit : Smoke)
	{
		const float T = FMath::Clamp(Age / Bit.Life, 0.0f, 1.0f);
		Bit.Velocity *= FMath::Exp(-0.9f * DeltaSeconds);
		Bit.Mesh->SetWorldLocation(Bit.Mesh->GetComponentLocation() + Bit.Velocity * DeltaSeconds);
		const float Size = FMath::Lerp(Bit.Size, Bit.EndSize, 1.0f - FMath::Square(1.0f - T));
		Bit.Mesh->SetWorldScale3D(FVector(Size));
		Bit.Mesh->SetVisibility(T < 1.0f);
		if (Bit.Material)
		{
			// Fades in behind the fireball, then thins out.
			Bit.Material->SetScalarParameterValue(BlastOpacityParam, Bit.Intensity * FMath::Clamp(Age / 0.35f, 0.0f, 1.0f) * FMath::Square(1.0f - T));
			Bit.Material->SetVectorParameterValue(BlastColorParam, FMath::Lerp(FLinearColor(0.35f, 0.14f, 0.05f), FLinearColor(0.05f, 0.04f, 0.035f), FMath::Clamp(Age / 0.8f, 0.0f, 1.0f)));
		}
	}
}
