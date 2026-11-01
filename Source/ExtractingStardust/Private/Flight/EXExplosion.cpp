#include "Flight/EXExplosion.h"

#include "Components/MaterialBillboardComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	const FName BlastColorParam(TEXT("Color"));
	const FName BlastIntensityParam(TEXT("Intensity"));
	const FName BlastOpacityParam(TEXT("Opacity"));
	const FName TexParam(TEXT("Tex"));
	const FName ColsParam(TEXT("Cols"));
	const FName RowsParam(TEXT("Rows"));
	const FName FrameParam(TEXT("Frame"));
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

	const bool bFlipbooks = LoadFlipbooks();
	Life = bFlipbooks ? 7.0f : 4.5f;
	if (bFlipbooks)
	{
		// Several rolling fireballs round the heart of it, a few hundredths of a second apart, then cooling to smoke.
		for (int32 Index = 0; Index < 5; ++Index)
		{
			const FVector Off = Index == 0 ? FVector::ZeroVector : (Random.VRand() * FVector(1.0, 1.0, 0.5)) * Random.FRandRange(150.0f, 320.0f) * Scale;
			AddSprite(FireballTexture, 8.0f, Origin + Off + FVector(0.0, 0.0, 120.0), Drift * 0.4 + Off * 1.5, Index * 0.04f,
				Random.FRandRange(1.6f, 2.2f), 300.0f * Scale, Random.FRandRange(1100.0f, 1600.0f) * Scale, Random.FRandRange(6.0f, 9.0f), false,
				FLinearColor::White, true);
		}
		// The second burst a moment later, beside the first (with its own flash in Tick).
		SecondaryAt = 0.32f;
		for (int32 Index = 0; Index < 2; ++Index)
		{
			const FVector Side = FVector(Random.FRandRange(-1.0f, 1.0f), Random.FRandRange(-1.0f, 1.0f), 0.2f).GetSafeNormal() * 420.0f * Scale;
			AddSprite(FireballTexture, 8.0f, Origin + Side + FVector(0.0, 0.0, 150.0), Drift * 0.3 + Side, SecondaryAt + Index * 0.05f, 1.6f,
				200.0f * Scale, 850.0f * Scale, 7.0f, false, FLinearColor::White, true);
		}
		// The smoke: dark, billowing up out of the fire and staying a while.
		for (int32 Index = 0; Index < 8; ++Index)
		{
			const FVector Off = Random.VRand() * FVector(1.0, 1.0, 0.3) * Random.FRandRange(100.0f, 450.0f) * Scale;
			AddSprite(SmokeTexture, 8.0f, Origin + Off + FVector(0.0, 0.0, 250.0), Drift * 0.25 + Off * 0.5 + FVector(0.0, 0.0, Random.FRandRange(250.0f, 420.0f)),
				Random.FRandRange(0.25f, 0.6f), Random.FRandRange(4.0f, 5.5f), 700.0f * Scale, Random.FRandRange(1800.0f, 2700.0f) * Scale,
				Random.FRandRange(0.65f, 0.85f), true, FLinearColor(0.22f, 0.2f, 0.19f));   // fuel smoke: near black
		}
		// A ring of dust thrown out along the ground behind the shock ring (it gives the blast its body).
		for (int32 Index = 0; Index < 10; ++Index)
		{
			const float A = 2.0f * PI * Index / 10.0f + Random.FRandRange(-0.2f, 0.2f);
			const FVector Out(FMath::Cos(A), FMath::Sin(A), 0.0f);
			AddSprite(SmokeTexture, 8.0f, Origin + Out * 200.0f - FVector(0.0, 0.0, 60.0), Drift * 0.2 + Out * Random.FRandRange(1800.0f, 2600.0f) * Scale,
				0.05f, Random.FRandRange(1.6f, 2.2f), 350.0f * Scale, 1000.0f * Scale, 0.55f, true, FLinearColor(1.4f, 1.0f, 0.68f));
		}
	}
	// Fireball (the fallback): white-hot core, orange body, red rim; each swells to its size and burns out.
	const FLinearColor FireColours[3] = { FLinearColor(1.0f, 0.92f, 0.7f), FLinearColor(1.0f, 0.45f, 0.08f), FLinearColor(0.9f, 0.12f, 0.03f) };
	const float FireSizes[3] = { 10.0f, 16.0f, 22.0f };      // metres across at the end
	const float FireIntensity[3] = { 60.0f, 28.0f, 12.0f };
	for (int32 Layer = 0; Layer < (bFlipbooks ? 1 : 3); ++Layer)
	{
		FBit Bit;
		Bit.Mesh = MakeMesh(SphereMesh, GlowMaterial, Bit.Material);
		Bit.Size = 0.6f;
		Bit.EndSize = FireSizes[Layer] * Scale;
		Bit.Intensity = FireIntensity[Layer];
		Bit.Life = 0.9f + 0.35f * Layer;
		if (bFlipbooks)
		{
			// With the flipbooks only the white-hot heart is kept: a quick, blinding core under the rolling fire.
			Bit.EndSize = 7.0f * Scale;
			Bit.Intensity = 80.0f;
			Bit.Life = 0.28f;
		}
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
	// Sparks: small and fast, streaking along their flight.
	AddSparks(bFlipbooks ? 60 : 34, Origin, 1.0f, 1.0f);
	// Smoke (the fallback): dark, rising and spreading, lit a little by the fire at first.
	for (int32 Index = 0; Index < (bFlipbooks ? 0 : 14); ++Index)
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

void AEXExplosion::AddSparks(int32 Count, const FVector& Origin, float Speed, float Size)
{
	FRandomStream Random(FMath::Rand());
	for (int32 Index = 0; Index < Count; ++Index)
	{
		FBit Bit;
		Bit.Mesh = MakeMesh(SphereMesh, GlowMaterial, Bit.Material);
		Bit.Velocity = Drift + Random.VRand() * Random.FRandRange(3000.0f, 7500.0f) * Scale * Speed + FVector(0.0f, 0.0f, 1200.0f * Speed);
		Bit.Size = Random.FRandRange(0.08f, 0.16f) * Size;
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
}

bool AEXExplosion::LoadFlipbooks()
{
	// Scripts/make_fx_assets.py (step 3d of casa_tudo.ps1); the flipbooks are rendered by Scripts/make_fx_flipbooks.py.
	FlipbookMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/FX/M_FX_Flipbook.M_FX_Flipbook"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	FireballTexture = LoadObject<UTexture2D>(nullptr, TEXT("/Game/FX/T_FX_Fireball.T_FX_Fireball"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	SmokeTexture = LoadObject<UTexture2D>(nullptr, TEXT("/Game/FX/T_FX_Smoke.T_FX_Smoke"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	return FlipbookMaterial && FireballTexture && SmokeTexture;
}

void AEXExplosion::AddSprite(UTexture2D* Texture, float Cols, const FVector& Pos, const FVector& Velocity, float Delay, float SpriteLife, float Size,
	float EndSize, float Intensity, bool bSmoke, const FLinearColor& Colour, bool bRises)
{
	FSprite S;
	S.Sprite = NewObject<UMaterialBillboardComponent>(this);
	S.Sprite->SetUsingAbsoluteLocation(true);
	S.Sprite->SetupAttachment(GetRootComponent());
	S.Sprite->RegisterComponent();
	S.Material = UMaterialInstanceDynamic::Create(FlipbookMaterial, this);
	S.Material->SetTextureParameterValue(TexParam, Texture);
	S.Material->SetScalarParameterValue(ColsParam, Cols);
	S.Material->SetScalarParameterValue(RowsParam, Cols);
	S.Material->SetVectorParameterValue(BlastColorParam, Colour);
	S.Material->SetScalarParameterValue(BlastIntensityParam, 0.0f);
	S.Material->SetScalarParameterValue(BlastOpacityParam, 0.0f);
	S.Sprite->AddElement(S.Material, nullptr, false, Size, Size, nullptr);
	S.Sprite->SetWorldLocation(Pos);
	S.Sprite->SetVisibility(false);
	S.Pos = Pos;
	S.Velocity = Velocity;
	S.Delay = Delay;
	S.Life = SpriteLife;
	S.Size = Size;
	S.EndSize = EndSize;
	S.Intensity = Intensity;
	S.Frames = Cols * Cols;
	S.bSmoke = bSmoke;
	S.bRises = bRises;
	Sprites.Add(S);
}

void AEXExplosion::IgniteImpact(const FVector& VelocityCmps, float Strength, bool bHot)
{
	Scale = FMath::Clamp(Strength, 0.25f, 1.0f);
	Drift = VelocityCmps;
	Life = 2.4f;
	FlashGain = bHot ? 0.25f : 0.08f;
	const FVector Origin = GetActorLocation();
	FRandomStream Random(FMath::Rand());
	Flash->SetLightColor(FLinearColor(1.0f, 0.7f, 0.4f));
	if (LoadFlipbooks())
	{
		for (int32 Index = 0; Index < 3; ++Index)
		{
			const FVector Off = Random.VRand() * FVector(1.0, 1.0, 0.2) * 80.0f;
			AddSprite(SmokeTexture, 8.0f, Origin + Off + FVector(0.0, 0.0, 60.0), Drift * 0.5 + Off * 3.0 + FVector(0.0, 0.0, 200.0), Index * 0.03f,
				Random.FRandRange(1.4f, 2.0f), 150.0f * Scale, 600.0f * Scale, 0.6f, true, FLinearColor(1.4f, 1.0f, 0.68f));
		}
		if (bHot)
		{
			AddSprite(FireballTexture, 8.0f, Origin + FVector(0.0, 0.0, 80.0), Drift * 0.6, 0.0f, 0.9f, 120.0f * Scale, 380.0f * Scale, 5.0f, false,
				FLinearColor::White, true);
		}
	}
	AddSparks(FMath::RoundToInt(10 + 14 * Scale), Origin, 0.45f, 0.8f);
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
	if (Age > Life)
	{
		Destroy();
		return;
	}
	// The whole blast drifts on with the craft's speed, slowing quickly.
	Drift *= FMath::Exp(-2.5f * DeltaSeconds);
	const FVector Shift = Drift * DeltaSeconds;
	SetActorLocation(GetActorLocation() + Shift);

	// The white flash at once; the second burst flashes again.
	float Light = 90000.0f * Scale * FlashGain * FMath::Exp(-Age * 5.0f);
	if (SecondaryAt > 0.0f && Age >= SecondaryAt)
	{
		Light += 50000.0f * Scale * FMath::Exp(-(Age - SecondaryAt) * 6.0f);
	}
	Flash->SetIntensity(Light);
	for (FSprite& S : Sprites)
	{
		const float Local = Age - S.Delay;
		if (Local < 0.0f)
		{
			continue;
		}
		const float T = FMath::Clamp(Local / S.Life, 0.0f, 1.0f);
		S.Velocity *= FMath::Exp(-(S.bSmoke ? 1.1f : 2.2f) * DeltaSeconds);
		if (S.bRises && Local > 0.4f)
		{
			S.Velocity.Z += 260.0f * DeltaSeconds;   // the hot gas rises
		}
		S.Pos += S.Velocity * DeltaSeconds;
		S.Sprite->SetWorldLocation(S.Pos);
		const float Grow = S.bSmoke ? FMath::Sqrt(T) : 1.0f - FMath::Exp(-Local * 5.0f);
		const float Size = FMath::Lerp(S.Size, S.EndSize, Grow);
		if (S.Sprite->Elements.Num() > 0)
		{
			S.Sprite->Elements[0].BaseSizeX = Size;
			S.Sprite->Elements[0].BaseSizeY = Size;
			S.Sprite->MarkRenderStateDirty();
		}
		S.Material->SetScalarParameterValue(FrameParam, FMath::Min(T * S.Frames, S.Frames - 1.0f));
		if (S.bSmoke)
		{
			S.Material->SetScalarParameterValue(BlastIntensityParam, 1.0f);
			S.Material->SetScalarParameterValue(BlastOpacityParam, S.Intensity * FMath::Clamp(Local / 0.3f, 0.0f, 1.0f) * FMath::Square(1.0f - T));
		}
		else
		{
			S.Material->SetScalarParameterValue(BlastIntensityParam, S.Intensity * (1.0f - 0.6f * T));
			S.Material->SetScalarParameterValue(BlastOpacityParam, FMath::Clamp(1.4f - 1.4f * T, 0.0f, 1.0f));
		}
		S.Sprite->SetVisibility(T < 1.0f);
	}

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
