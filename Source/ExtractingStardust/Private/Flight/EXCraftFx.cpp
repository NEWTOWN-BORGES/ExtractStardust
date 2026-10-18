#include "Flight/EXCraftFx.h"

#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Math/RotationMatrix.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr int32 PuffCount = 44;
	constexpr int32 StreakCount = 48;
	const FName ColorParam(TEXT("Color"));
	const FName IntensityParam(TEXT("Intensity"));
	const FName OpacityParam(TEXT("Opacity"));
}

UEXCraftFx::UEXCraftFx()
{
	PrimaryComponentTick.bCanEverTick = false;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Glow(TEXT("/Game/FX/M_FX_Glow.M_FX_Glow"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Dust(TEXT("/Game/FX/M_FX_Dust.M_FX_Dust"));
	SphereMesh = Sphere.Object;
	CylinderMesh = Cylinder.Object;
	GlowMaterial = Glow.Object;
	DustMaterial = Dust.Object;
}

UStaticMeshComponent* UEXCraftFx::MakeMesh(UStaticMesh* Mesh, UMaterialInterface* Material, USceneComponent* Parent, bool bWorldSpace)
{
	UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(GetOwner());
	Component->SetStaticMesh(Mesh);
	Component->SetMaterial(0, Material);
	Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Component->SetCastShadow(false);
	Component->SetGenerateOverlapEvents(false);
	if (bWorldSpace)
	{
		Component->SetUsingAbsoluteLocation(true);
		Component->SetUsingAbsoluteRotation(true);
		Component->SetUsingAbsoluteScale(true);
	}
	Component->SetupAttachment(Parent);
	Component->RegisterComponent();
	return Component;
}

void UEXCraftFx::Initialize(USceneComponent* ShipAttach)
{
	if (bInitialized || !ShipAttach || !GetOwner() || !SphereMesh || !CylinderMesh || !GlowMaterial || !DustMaterial)
	{
		return;
	}
	bInitialized = true;

	for (int32 Engine = 0; Engine < 2; ++Engine)
	{
		for (int32 Layer = 0; Layer < 2; ++Layer)
		{
			UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(GlowMaterial, this);
			Material->SetVectorParameterValue(ColorParam, Layer == 0 ? FlameColor : FlameCoreColor);
			FlameMeshes.Add(MakeMesh(SphereMesh, Material, ShipAttach, false));
			FlameMaterials.Add(Material);
		}
		UPointLightComponent* Light = NewObject<UPointLightComponent>(GetOwner());
		Light->SetIntensityUnits(ELightUnits::Candelas);
		Light->SetLightColor(FlameColor);
		Light->SetAttenuationRadius(250.0f);
		Light->SetCastShadows(false);
		Light->SetupAttachment(ShipAttach);
		Light->RegisterComponent();
		EngineLights.Add(Light);
	}

	USceneComponent* Root = GetOwner()->GetRootComponent();
	Puffs.SetNum(PuffCount);
	for (int32 Index = 0; Index < PuffCount; ++Index)
	{
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(DustMaterial, this);
		Material->SetVectorParameterValue(ColorParam, DustColor);
		Material->SetScalarParameterValue(OpacityParam, 0.0f);
		UStaticMeshComponent* Puff = MakeMesh(SphereMesh, Material, Root, true);
		Puff->SetVisibility(false);
		PuffMeshes.Add(Puff);
		PuffMaterials.Add(Material);
	}

	StreakMaterial = UMaterialInstanceDynamic::Create(GlowMaterial, this);
	StreakMaterial->SetVectorParameterValue(ColorParam, FLinearColor(0.85f, 0.9f, 1.0f));
	StreakMaterial->SetScalarParameterValue(IntensityParam, 0.0f);
	StreakLocations.SetNumZeroed(StreakCount);
	StreakActive.SetNumZeroed(StreakCount);
	for (int32 Index = 0; Index < StreakCount; ++Index)
	{
		UStaticMeshComponent* Streak = MakeMesh(CylinderMesh, StreakMaterial, Root, true);
		Streak->SetVisibility(false);
		StreakMeshes.Add(Streak);
	}
	SetShipHalfSize(ShipHalfSize);
}

void UEXCraftFx::SetShipHalfSize(const FVector& HalfSizeCm)
{
	ShipHalfSize = HalfSizeCm;
	// Two engines at the tail; the test models do not mark their nozzles.
	EngineAnchors[0] = FVector(-HalfSizeCm.X * 0.92f, -HalfSizeCm.Y * 0.42f, -HalfSizeCm.Z * 0.1f);
	EngineAnchors[1] = FVector(-HalfSizeCm.X * 0.92f, HalfSizeCm.Y * 0.42f, -HalfSizeCm.Z * 0.1f);
	FlameRadiusCm = FMath::Clamp(HalfSizeCm.Y * 0.12f, 14.0f, 24.0f);
}

void UEXCraftFx::UpdateFx(float Dt, const FEXCraftFxInput& Input)
{
	if (!bInitialized || Dt <= 0.0f)
	{
		return;
	}
	UpdateFlames(Dt, Input);
	UpdateDust(Dt, Input);
	UpdateStreaks(Dt, Input);
}

void UEXCraftFx::UpdateFlames(float Dt, const FEXCraftFxInput& Input)
{
	FlickerTime += Dt;
	// Flames follow throttle and grow with speed; nitro stretches them further.
	const float TargetPower = FMath::Clamp((0.2f + 0.8f * Input.Throttle) * (0.45f + 0.55f * Input.SpeedAlpha), 0.0f, 1.0f) * (Input.bBoosting ? 1.7f : 1.0f);
	FlamePower = FMath::FInterpTo(FlamePower, TargetPower, Dt, 8.0f);
	const float Power = FMath::Min(FlamePower, 1.0f);
	for (int32 Engine = 0; Engine < 2; ++Engine)
	{
		const float Flicker = 1.0f + 0.12f * FMath::Sin(FlickerTime * 37.0f + Engine * 1.7f) + 0.08f * FMath::Sin(FlickerTime * 61.0f + Engine * 0.9f);
		// Short, hot flames like the tail glow in the reference video (the close chase camera sits only 2-3 m
		// behind the tail): ~0.25 m idle, ~0.7 m flat out, ~1.2 m on nitro.
		const float OuterLength = (FMath::Lerp(25.0f, 70.0f, Power) + (Input.bBoosting ? 50.0f : 0.0f)) * Flicker;
		for (int32 Layer = 0; Layer < 2; ++Layer)
		{
			const float Length = Layer == 0 ? OuterLength : OuterLength * 0.55f;
			const float Radius = Layer == 0 ? FlameRadiusCm : FlameRadiusCm * 0.5f;
			UStaticMeshComponent* Flame = FlameMeshes[Engine * 2 + Layer];
			// The sphere is stretched into a flame along -X, starting at the nozzle.
			Flame->SetRelativeLocation(EngineAnchors[Engine] - FVector(Length * 0.5f, 0.0f, 0.0f));
			Flame->SetRelativeScale3D(FVector(Length / 100.0f, Radius / 50.0f, Radius / 50.0f));
			const float Intensity = FMath::Lerp(0.6f, 2.6f, Power) * Flicker * (Input.bBoosting ? 1.3f : 1.0f) * (Layer == 0 ? 1.0f : 1.4f);
			FlameMaterials[Engine * 2 + Layer]->SetScalarParameterValue(IntensityParam, Intensity);
		}
		EngineLights[Engine]->SetRelativeLocation(EngineAnchors[Engine] - FVector(60.0f, 0.0f, 0.0f));
		EngineLights[Engine]->SetIntensity(FMath::Lerp(3.0f, 18.0f, FlamePower) * Flicker);
	}
}

void UEXCraftFx::SpawnPuff(const FVector& Location, const FVector& Velocity, float Life, float StartSizeM, float EndSizeM, float Opacity)
{
	int32 Slot = INDEX_NONE;
	float OldestAge = -1.0f;
	for (int32 Index = 0; Index < Puffs.Num(); ++Index)
	{
		if (!Puffs[Index].bActive)
		{
			Slot = Index;
			break;
		}
		const float AgeFraction = Puffs[Index].Age / Puffs[Index].Life;
		if (AgeFraction > OldestAge)
		{
			OldestAge = AgeFraction;
			Slot = Index;
		}
	}
	if (Slot == INDEX_NONE)
	{
		return;
	}
	FPuff& Puff = Puffs[Slot];
	Puff.Location = Location;
	Puff.Velocity = Velocity;
	Puff.Age = 0.0f;
	Puff.Life = Life;
	Puff.StartSizeM = StartSizeM;
	Puff.EndSizeM = EndSizeM;
	Puff.Opacity = Opacity;
	Puff.bActive = true;
	PuffMeshes[Slot]->SetVisibility(true);
}

void UEXCraftFx::LandingBurst(const FVector& Point, const FVector& Up, float Strength)
{
	if (!bInitialized)
	{
		return;
	}
	const int32 Count = FMath::RoundToInt(6.0f + 8.0f * Strength);
	const FVector Side = FVector::CrossProduct(Up, FVector::ForwardVector).GetSafeNormal(UE_SMALL_NUMBER, FVector::RightVector);
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const FVector Outward = Side.RotateAngleAxis(360.0f * Index / Count + Random.FRandRange(-15.0f, 15.0f), Up);
		SpawnPuff(Point + Up * 60.0f + Outward * 150.0f, Outward * Random.FRandRange(400.0f, 1000.0f) * Strength + Up * Random.FRandRange(100.0f, 300.0f),
			Random.FRandRange(1.1f, 1.7f), Random.FRandRange(1.5f, 2.5f), Random.FRandRange(5.5f, 9.0f), 0.55f);
	}
}

void UEXCraftFx::UpdateDust(float Dt, const FEXCraftFxInput& Input)
{
	const float Speed = Input.Velocity.Size() / 100.0f;
	if (Input.bGrounded && Input.HeightM < 3.0f && Speed > 8.0f)
	{
		SpawnAccumulator += Dt * DustRateMax * FMath::Clamp(Speed / 90.0f, 0.15f, 1.0f) * (Input.bDrifting ? 1.5f : 1.0f);
	}
	const FVector Right = FVector::CrossProduct(Input.SurfaceUp, Input.Heading).GetSafeNormal();
	while (SpawnAccumulator >= 1.0f)
	{
		SpawnAccumulator -= 1.0f;
		// Dust hugs the ground on both flanks of the ship, never in the camera's line behind it, and is dragged a
		// little by the wake so it rolls past the lower corners of the screen like in the reference video.
		const float Side = (Random.FRand() < 0.5f ? -1.0f : 1.0f) * Random.FRandRange(0.7f, 1.4f);
		const FVector Point = Input.GroundPoint + Input.Heading * (ShipHalfSize.X * Random.FRandRange(-0.6f, 0.4f))
			+ Right * (ShipHalfSize.Y * Side) + Input.SurfaceUp * 20.0f;
		const FVector Velocity = Input.Velocity * 0.35f + Right * (Side * Random.FRandRange(200.0f, 500.0f)) + Input.SurfaceUp * Random.FRandRange(30.0f, 120.0f);
		SpawnPuff(Point, Velocity, Random.FRandRange(0.7f, 1.2f), Random.FRandRange(1.2f, 2.0f), Random.FRandRange(4.0f, 7.0f), Random.FRandRange(0.22f, 0.32f));
	}

	for (int32 Index = 0; Index < Puffs.Num(); ++Index)
	{
		FPuff& Puff = Puffs[Index];
		if (!Puff.bActive)
		{
			continue;
		}
		Puff.Age += Dt;
		if (Puff.Age >= Puff.Life)
		{
			Puff.bActive = false;
			PuffMeshes[Index]->SetVisibility(false);
			continue;
		}
		const float T = Puff.Age / Puff.Life;
		Puff.Velocity *= FMath::Exp(-2.2f * Dt);
		Puff.Location += Puff.Velocity * Dt;
		// Grows quickly then slows; fades in fast and out slowly.
		const float SizeCm = FMath::Lerp(Puff.StartSizeM, Puff.EndSizeM, 1.0f - FMath::Square(1.0f - T)) * 100.0f;
		PuffMeshes[Index]->SetWorldLocation(Puff.Location);
		PuffMeshes[Index]->SetWorldScale3D(FVector(SizeCm, SizeCm, SizeCm * 0.45f) / 100.0f);
		PuffMaterials[Index]->SetScalarParameterValue(OpacityParam, Puff.Opacity * FMath::Min(1.0f, T / 0.1f) * FMath::Pow(1.0f - T, 1.5f));
	}
}

void UEXCraftFx::UpdateStreaks(float Dt, const FEXCraftFxInput& Input)
{
	const float Speed = Input.Velocity.Size() / 100.0f;
	const float Strength = FMath::SmoothStep(35.0f, 110.0f, Speed) * (Input.bBoosting ? 1.4f : 1.0f);
	StreakMaterial->SetScalarParameterValue(IntensityParam, 0.6f * Strength);
	const bool bVisible = Strength > 0.01f;
	const FVector Direction = Speed > 1.0f ? Input.Velocity / (Speed * 100.0f) : Input.Heading;
	// Each streak is as long as 0.06 s of travel, so faster flight draws longer lines.
	const float LengthCm = FMath::Clamp(Speed * 6.0f, 50.0f, 900.0f);
	const FQuat Orientation = FRotationMatrix::MakeFromZ(Direction).ToQuat();
	const FVector ViewSide = FVector::CrossProduct(Input.CameraForward, FVector::UpVector).GetSafeNormal(UE_SMALL_NUMBER, FVector::RightVector);
	const FVector ViewUp = FVector::CrossProduct(ViewSide, Input.CameraForward).GetSafeNormal();
	for (int32 Index = 0; Index < StreakMeshes.Num(); ++Index)
	{
		const FVector Relative = StreakLocations[Index] - Input.CameraLocation;
		const float Ahead = FVector::DotProduct(Relative, Input.CameraForward);
		if (!StreakActive[Index] || Ahead < -300.0f || Relative.SizeSquared() > FMath::Square(12000.0f))
		{
			// Respawn ahead of the camera, in a tube around the view axis that leaves the ship clear.
			const float Angle = Random.FRandRange(0.0f, 2.0f * PI);
			FVector Location = Input.CameraLocation + Input.CameraForward * Random.FRandRange(1500.0f, 9000.0f)
				+ (ViewSide * FMath::Cos(Angle) + ViewUp * FMath::Sin(Angle)) * Random.FRandRange(600.0f, 2000.0f);
			Location.Z = FMath::Max(Location.Z, Input.GroundPoint.Z + 100.0f);
			StreakLocations[Index] = Location;
			StreakActive[Index] = true;
		}
		UStaticMeshComponent* Streak = StreakMeshes[Index];
		Streak->SetVisibility(bVisible);
		if (bVisible)
		{
			Streak->SetWorldLocationAndRotation(StreakLocations[Index], Orientation);
			Streak->SetWorldScale3D(FVector(0.02f, 0.02f, LengthCm / 100.0f));
		}
	}
}
