#include "Flight/EXWreck.h"

#include "Components/MaterialBillboardComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "Flight/EXExplosion.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace
{
	// The same numbers as Scripts/physics_sandbox/wreck.py.
	constexpr float WreckGravity = 22.0f;     // m/s^2, the game's
	constexpr float Restitution = 0.32f;
	constexpr float Friction = 0.55f;
	constexpr float LinearDrag = 0.08f;
	constexpr float AngularDrag = 0.25f;
	// A hard hit crumples the bodywork and digs a corner into the sand: it catches much harder than it slides (a nose
	// landing pole-vaults over the nose) and the crumpling soaks up some spin. Without it a box tumbling at 100 m/s
	// rolls like a wheel and spins up towards speed / size.
	constexpr double DigSpeed = 10.0;         // m/s into the ground
	constexpr double DigFriction = 1.7;
	constexpr double Crush = 0.8;             // the spin kept after a hard hit
	constexpr double MaxTipSpeed = 45.0;      // m/s: the far corner never whirls faster round the centre
	constexpr float WreckLife = 15.0f;
	constexpr float BurnSeconds = 11.0f;
	constexpr int32 MaxPuffs = 45;
	const FName TexParam(TEXT("Tex"));
	const FName ColsParam(TEXT("Cols"));
	const FName RowsParam(TEXT("Rows"));
	const FName FrameParam(TEXT("Frame"));
	const FName ColorParam(TEXT("Color"));
	const FName IntensityParam(TEXT("Intensity"));
	const FName OpacityParam(TEXT("Opacity"));
	const FName HeatParam(TEXT("Heat"));

	template <typename T>
	T* LoadFx(const TCHAR* Path)
	{
		return LoadObject<T>(nullptr, Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
	}
}

AEXWreck::AEXWreck()
{
	PrimaryActorTick.bCanEverTick = true;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	GetRootComponent()->SetMobility(EComponentMobility::Movable);
	Fire = CreateDefaultSubobject<UMaterialBillboardComponent>(TEXT("Fire"));
	Fire->SetupAttachment(GetRootComponent());
	Fire->SetUsingAbsoluteLocation(true);
	FireLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("FireLight"));
	FireLight->SetupAttachment(GetRootComponent());
	FireLight->SetUsingAbsoluteLocation(true);
	FireLight->SetMobility(EComponentMobility::Movable);
	FireLight->SetCastShadows(false);
	FireLight->SetIntensityUnits(ELightUnits::Candelas);
	FireLight->SetIntensity(0.0f);
	FireLight->SetAttenuationRadius(2500.0f);   // ~1500 cd: an orange pool on the sand round the wreck (the sun is 10 lux)
	FireLight->SetLightColor(FLinearColor(1.0f, 0.5f, 0.18f));
}

void AEXWreck::AddPiece(UStaticMesh* Mesh, const TArray<UMaterialInterface*>& Materials, const FTransform& World, float MassKg,
	const FVector& VelocityCmps, const FVector& SpinRad)
{
	if (!Mesh)
	{
		return;
	}
	if (Pieces.Num() == 0)
	{
		// The charred overlay, and the flipbooks of the fire on the hull and its smoke (Scripts/make_fx_assets.py); without
		// them the pieces fly in their own colours and only the light burns.
		CharMaterial = LoadFx<UMaterialInterface>(TEXT("/Game/FX/M_FX_Char.M_FX_Char"));
		FlipbookMaterial = LoadFx<UMaterialInterface>(TEXT("/Game/FX/M_FX_Flipbook.M_FX_Flipbook"));
		FireTexture = LoadFx<UTexture2D>(TEXT("/Game/FX/T_FX_Fire.T_FX_Fire"));
		SmokeTexture = LoadFx<UTexture2D>(TEXT("/Game/FX/T_FX_Smoke.T_FX_Smoke"));
		if (FlipbookMaterial && FireTexture)
		{
			FireMaterial = UMaterialInstanceDynamic::Create(FlipbookMaterial, this);
			FireMaterial->SetTextureParameterValue(TexParam, FireTexture);
			FireMaterial->SetScalarParameterValue(ColsParam, 4.0f);
			FireMaterial->SetScalarParameterValue(RowsParam, 4.0f);
			Fire->AddElement(FireMaterial, nullptr, false, 450.0f, 450.0f, nullptr);
		}
	}
	UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(this);
	Component->SetMobility(EComponentMobility::Movable);
	Component->SetStaticMesh(Mesh);
	Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Component->SetUsingAbsoluteLocation(true);
	Component->SetUsingAbsoluteRotation(true);
	Component->SetUsingAbsoluteScale(true);
	for (int32 Index = 0; Index < Materials.Num(); ++Index)
	{
		Component->SetMaterial(Index, Materials[Index]);
	}
	if (CharMaterial)
	{
		UMaterialInstanceDynamic* Char = UMaterialInstanceDynamic::Create(CharMaterial, this);
		Component->SetOverlayMaterial(Char);
		CharMaterials.Add(Char);
	}
	Component->SetupAttachment(GetRootComponent());
	Component->RegisterComponent();
	Component->SetWorldScale3D(World.GetScale3D());

	FPiece Piece;
	Piece.Mesh = Component;
	const FBoxSphereBounds Bounds = Mesh->GetBounds();
	const FVector Scale = World.GetScale3D();
	Piece.CentreLocal = Bounds.Origin * Scale;
	Piece.Half = (Bounds.BoxExtent * Scale.GetAbs() / 100.0).ComponentMax(FVector(0.06, 0.06, 0.06));
	Piece.Rot = World.GetRotation();
	Piece.Pos = (World.GetLocation() + Piece.Rot.RotateVector(Piece.CentreLocal)) / 100.0;
	Piece.Mass = FMath::Max(20.0f, MassKg);
	const FVector L = Piece.Half * 2.0;
	Piece.InvInertia = FVector(12.0 / (Piece.Mass * (L.Y * L.Y + L.Z * L.Z)), 12.0 / (Piece.Mass * (L.X * L.X + L.Z * L.Z)),
		12.0 / (Piece.Mass * (L.X * L.X + L.Y * L.Y)));
	Piece.Vel = VelocityCmps / 100.0;
	Piece.Spin = SpinRad;
	Pieces.Add(Piece);
	ApplyPose(Pieces.Last());
}

FVector AEXWreck::GetMainLocation() const
{
	return Pieces.Num() > 0 ? Pieces[0].Pos * 100.0 : GetActorLocation();
}

FVector AEXWreck::GetMainVelocity() const
{
	return Pieces.Num() > 0 ? Pieces[0].Vel * 100.0 : FVector::ZeroVector;
}

void AEXWreck::ApplyPose(const FPiece& Piece) const
{
	Piece.Mesh->SetWorldLocationAndRotation(Piece.Pos * 100.0 - Piece.Rot.RotateVector(Piece.CentreLocal), Piece.Rot);
}

void AEXWreck::StepPiece(FPiece& Piece, float Dt)
{
	Piece.HitCooldown = FMath::Max(0.0f, Piece.HitCooldown - Dt);
	if (Piece.Asleep > 0.6f)
	{
		return;
	}
	Piece.Vel.Z -= WreckGravity * Dt;
	Piece.Vel *= 1.0f - LinearDrag * Dt;
	Piece.Spin *= 1.0f - AngularDrag * Dt;
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(EXWreck), false, this);
	// The surfaces it can strike this step: a wall or a rock ahead (a sweep along the move), and the ground under it (a
	// plane, under a piece this size).
	FVector PlanePoint[2];
	FVector PlaneNormal[2];
	int32 PlaneCount = 0;
	{
		FHitResult Ahead;
		const float Radius = static_cast<float>(Piece.Half.GetMin()) * 80.0f;
		if (GetWorld()->SweepSingleByObjectType(Ahead, Piece.Pos * 100.0, (Piece.Pos + Piece.Vel * Dt) * 100.0, FQuat::Identity, Objects,
			FCollisionShape::MakeSphere(FMath::Max(10.0f, Radius)), Query) && Ahead.ImpactNormal.Z < 0.5f)
		{
			PlanePoint[PlaneCount] = Ahead.ImpactPoint / 100.0;
			PlaneNormal[PlaneCount++] = Ahead.ImpactNormal;
		}
	}
	Piece.Pos += Piece.Vel * Dt;
	const float SpinSpeed = static_cast<float>(Piece.Spin.Size());
	if (SpinSpeed > 1.0e-4f)
	{
		Piece.Rot = (FQuat(Piece.Spin / SpinSpeed, SpinSpeed * Dt) * Piece.Rot).GetNormalized();
	}
	{
		FHitResult Ground;
		const float Reach = static_cast<float>(Piece.Half.Size()) + 2.0f;
		if (GetWorld()->LineTraceSingleByObjectType(Ground, (Piece.Pos + FVector(0.0, 0.0, Reach)) * 100.0,
			(Piece.Pos - FVector(0.0, 0.0, Reach)) * 100.0, Objects, Query))
		{
			PlanePoint[PlaneCount] = Ground.ImpactPoint / 100.0;
			PlaneNormal[PlaneCount++] = Ground.ImpactNormal;
		}
	}
	// Each corner that is in a surface takes an impulse (a little bounce, friction along it), which spins the piece.
	auto InvInertiaWorld = [&Piece](const FVector& X)
	{
		return Piece.Rot.RotateVector(Piece.Rot.UnrotateVector(X) * Piece.InvInertia);
	};
	double Deepest[2] = { 0.0, 0.0 };
	bool bCrushed = false;
	for (int32 Pass = 0; Pass < 2; ++Pass)
	{
		for (int32 Corner = 0; Corner < 8; ++Corner)
		{
			const FVector Sign((Corner & 1) ? 1.0 : -1.0, (Corner & 2) ? 1.0 : -1.0, (Corner & 4) ? 1.0 : -1.0);
			const FVector C = Piece.Pos + Piece.Rot.RotateVector(Piece.Half * Sign);
			for (int32 Plane = 0; Plane < PlaneCount; ++Plane)
			{
				const FVector& N = PlaneNormal[Plane];
				const double Depth = FVector::DotProduct(PlanePoint[Plane] - C, N);
				if (Depth <= 0.0)
				{
					continue;
				}
				Deepest[Plane] = FMath::Max(Deepest[Plane], Depth);
				const FVector R = C - Piece.Pos;
				const FVector Vc = Piece.Vel + FVector::CrossProduct(Piece.Spin, R);
				const double Vn = FVector::DotProduct(Vc, N);
				if (Vn >= 0.0)
				{
					continue;
				}
				const double E = Vn < -2.0 ? Restitution : 0.0;
				const double Kn = 1.0 / Piece.Mass + FVector::DotProduct(N, FVector::CrossProduct(InvInertiaWorld(FVector::CrossProduct(R, N)), R));
				const double J = -(1.0 + E) * Vn / Kn;
				Piece.Vel += N * (J / Piece.Mass);
				Piece.Spin += InvInertiaWorld(FVector::CrossProduct(R, N * J));
				const FVector Vc2 = Piece.Vel + FVector::CrossProduct(Piece.Spin, R);
				const FVector Vt = Vc2 - N * FVector::DotProduct(Vc2, N);
				const double Slide = Vt.Size();
				if (Slide > 1.0e-4)
				{
					const FVector T = Vt / Slide;
					const double Kt = 1.0 / Piece.Mass + FVector::DotProduct(T, FVector::CrossProduct(InvInertiaWorld(FVector::CrossProduct(R, T)), R));
					const double Jt = FMath::Min((-Vn > DigSpeed ? DigFriction : Friction) * J, Slide / Kt);
					Piece.Vel -= T * (Jt / Piece.Mass);
					Piece.Spin -= InvInertiaWorld(FVector::CrossProduct(R, T * Jt));
				}
				if (-Vn > 6.0 && Piece.HitCooldown <= 0.0f)
				{
					Piece.HitCooldown = 0.08f;
					Strike(C, static_cast<float>(-Vn), &Piece == &Pieces[0]);
				}
				bCrushed = bCrushed || -Vn > DigSpeed;
			}
		}
	}
	if (bCrushed)
	{
		Piece.Spin *= Crush;
	}
	const double SpinCap = MaxTipSpeed / FMath::Max(0.1, Piece.Half.Size());
	if (Piece.Spin.Size() > SpinCap)
	{
		Piece.Spin *= SpinCap / Piece.Spin.Size();
	}
	for (int32 Plane = 0; Plane < PlaneCount; ++Plane)
	{
		Piece.Pos += PlaneNormal[Plane] * (Deepest[Plane] * 0.8);
	}
	const bool bSlow = Piece.Vel.Size() < 0.35 && Piece.Spin.Size() < 0.5;
	Piece.Asleep = bSlow ? Piece.Asleep + Dt : 0.0f;
}

void AEXWreck::Strike(const FVector& PointM, float Speed, bool bHull)
{
	// Sparks and a burst of dust where a piece hits hard (a lick of fire while the hull is still hot).
	if (StrikeCooldown > 0.0f)
	{
		return;
	}
	if (!bHull && Speed < 9.0f)
	{
		return;   // a wing landing flat: no burst for that
	}
	StrikeCooldown = 0.1f;   // at most ten bursts a second per wreck (each is a few sprites and sparks)
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	if (AEXExplosion* Burst = GetWorld()->SpawnActor<AEXExplosion>(PointM * 100.0, FRotator::ZeroRotator, Params))
	{
		Burst->IgniteImpact(Pieces.Num() > 0 ? Pieces[0].Vel * 100.0 * 0.3 : FVector::ZeroVector, FMath::Clamp(Speed / 20.0f, 0.25f, 1.0f),
			bHull && Age < 3.0f);
	}
}

void AEXWreck::Puff(const FVector& PosCm)
{
	if (!FlipbookMaterial || !SmokeTexture)
	{
		return;
	}
	FPuff* Slot = nullptr;
	if (Puffs.Num() >= MaxPuffs)
	{
		Slot = &Puffs[0];
		for (FPuff& P : Puffs)
		{
			Slot = P.Age / P.Life > Slot->Age / Slot->Life ? &P : Slot;
		}
	}
	else
	{
		FPuff& New = Puffs.AddDefaulted_GetRef();
		New.Sprite = NewObject<UMaterialBillboardComponent>(this);
		New.Sprite->SetUsingAbsoluteLocation(true);
		New.Sprite->SetupAttachment(GetRootComponent());
		New.Sprite->RegisterComponent();
		New.Material = UMaterialInstanceDynamic::Create(FlipbookMaterial, this);
		New.Material->SetTextureParameterValue(TexParam, SmokeTexture);
		New.Material->SetScalarParameterValue(ColsParam, 8.0f);
		New.Material->SetScalarParameterValue(RowsParam, 8.0f);
		New.Material->SetVectorParameterValue(ColorParam, FLinearColor(0.32f, 0.3f, 0.29f));
		New.Sprite->AddElement(New.Material, nullptr, false, 200.0f, 200.0f, nullptr);
		Slot = &New;
	}
	Slot->Pos = PosCm;
	Slot->Age = 0.0f;
	Slot->Life = FMath::FRandRange(2.2f, 3.0f);
	Slot->Sprite->SetWorldLocation(PosCm);
	Slot->Sprite->SetVisibility(true);
}

void AEXWreck::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;
	StrikeCooldown = FMath::Max(0.0f, StrikeCooldown - DeltaSeconds);
	if (Age > WreckLife || Pieces.Num() == 0)
	{
		Destroy();
		return;
	}
	// Small fixed steps: the corner impulses stay stable at any frame rate.
	float Remaining = FMath::Min(DeltaSeconds, 0.05f);
	while (Remaining > KINDA_SMALL_NUMBER)
	{
		const float Step = FMath::Min(Remaining, 1.0f / 120.0f);
		for (FPiece& Piece : Pieces)
		{
			StepPiece(Piece, Step);
		}
		Remaining -= Step;
	}
	// The last second: the pieces shrink away.
	const float Fade = FMath::Clamp(WreckLife - Age, 0.0f, 1.0f);
	for (const FPiece& Piece : Pieces)
	{
		ApplyPose(Piece);
		if (Fade < 1.0f)
		{
			Piece.Mesh->SetWorldScale3D(Piece.Mesh->GetComponentScale() * FMath::Max(0.05f, 1.0f - (1.0f - Fade) * DeltaSeconds * 4.0f));
		}
	}
	// The hull burns and trails smoke while it is hot; the charred skin cools from glowing embers to soot.
	const float Heat = FMath::Clamp(1.0f - Age / BurnSeconds, 0.0f, 1.0f);
	for (UMaterialInstanceDynamic* Char : CharMaterials)
	{
		Char->SetScalarParameterValue(HeatParam, Heat);
	}
	const FVector Hull = Pieces[0].Pos * 100.0;
	FireLight->SetWorldLocation(Hull + FVector(0.0, 0.0, 120.0));
	FireLight->SetIntensity(1500.0f * Heat * (0.8f + 0.2f * FMath::Sin(Age * 23.0f) * FMath::Sin(Age * 7.3f)));
	if (FireMaterial)
	{
		Fire->SetWorldLocation(Hull + FVector(0.0, 0.0, 160.0));
		FireMaterial->SetScalarParameterValue(FrameParam, FMath::Fmod(Age * 16.0f, 16.0f));
		FireMaterial->SetScalarParameterValue(IntensityParam, 7.0f * Heat);
		FireMaterial->SetScalarParameterValue(OpacityParam, FMath::Clamp(Heat * 1.5f, 0.0f, 1.0f));
		Fire->SetVisibility(Heat > 0.02f);
	}
	PuffTimer -= DeltaSeconds;
	if (Heat > 0.05f && PuffTimer <= 0.0f)
	{
		PuffTimer = FMath::Lerp(0.16f, 0.06f, Heat);
		Puff(Hull + FVector(FMath::FRandRange(-60.0f, 60.0f), FMath::FRandRange(-60.0f, 60.0f), 120.0f));
	}
	for (FPuff& P : Puffs)
	{
		if (P.Age >= P.Life)
		{
			continue;
		}
		P.Age += DeltaSeconds;
		const float T = FMath::Clamp(P.Age / P.Life, 0.0f, 1.0f);
		P.Pos += FVector(0.0, 0.0, 160.0f * DeltaSeconds);
		P.Sprite->SetWorldLocation(P.Pos);
		const float Size = FMath::Lerp(220.0f, 950.0f, FMath::Sqrt(T));
		if (P.Sprite->Elements.Num() > 0)
		{
			P.Sprite->Elements[0].BaseSizeX = Size;
			P.Sprite->Elements[0].BaseSizeY = Size;
			P.Sprite->MarkRenderStateDirty();
		}
		P.Material->SetScalarParameterValue(FrameParam, T * 63.0f);
		P.Material->SetScalarParameterValue(IntensityParam, 1.0f);
		P.Material->SetScalarParameterValue(OpacityParam, 0.7f * FMath::Clamp(P.Age / 0.2f, 0.0f, 1.0f) * FMath::Square(1.0f - T));
		P.Sprite->SetVisibility(T < 1.0f);
	}
}
