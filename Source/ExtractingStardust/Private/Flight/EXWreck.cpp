#include "Flight/EXWreck.h"

#include "Components/MaterialBillboardComponent.h"
#include "Components/PointLightComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "Flight/EXExplosion.h"
#include "Flight/EXFxSprite.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Kismet/GameplayStatics.h"

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
	// Every piece a ball of fire (player, 2026-11-01: "peças em bolas de fogo"); the same numbers as
	// Scripts/physics_sandbox/wreck_video.py, which renders them.
	constexpr int32 MaxTrails = 100;          // tongues of flame alive per wreck (the oldest is reused)
	constexpr int32 MaxSmoke = 80;            // puffs of smoke alive per wreck
	// Keeping the frame rate (player, 2026-11-02: "cuidado com as quedas de fps"): the wreck the camera is on burns in
	// full; from 120 m it leaves half the trail and smoke and no bursts where it strikes, from 300 m only its own flames;
	// and with several wrecks burning at once each one leaves less (the rates shared out).
	constexpr float NearM = 120.0f;
	constexpr float FarM = 300.0f;
	int32 LiveWrecks = 0;
	constexpr float TrailLife = 0.45f;        // s, a tongue of flame (x 0.8-1.2, shorter as the piece cools)
	constexpr float HullTrailRate = 60.0f;    // tongues a second at most, the hull and the modules
	constexpr float ModuleTrailRate = 40.0f;
	constexpr float FireLightCd = 60.0f;      // the burning hull's light: an orange tint on the sand round it (the sun is 10 lux)
	const FName TexParam(TEXT("Tex"));
	const FName ColsParam(TEXT("Cols"));
	const FName RowsParam(TEXT("Rows"));
	const FName FrameParam(TEXT("Frame"));
	const FName ColorParam(TEXT("Color"));
	const FName IntensityParam(TEXT("Intensity"));
	const FName OpacityParam(TEXT("Opacity"));
	const FName HeatParam(TEXT("Heat"));
	const FName RotationParam(TEXT("Rotation"));   // M_FX_Flipbook: turns the picture clockwise on screen (radians)

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
	FireLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("FireLight"));
	FireLight->SetupAttachment(GetRootComponent());
	FireLight->SetUsingAbsoluteLocation(true);
	FireLight->SetMobility(EComponentMobility::Movable);
	FireLight->SetCastShadows(false);
	FireLight->SetIntensityUnits(ELightUnits::Candelas);
	FireLight->SetIntensity(0.0f);
	FireLight->SetAttenuationRadius(2500.0f);
	FireLight->SetLightColor(FLinearColor(1.0f, 0.5f, 0.18f));
}

void AEXWreck::BeginPlay()
{
	Super::BeginPlay();
	++LiveWrecks;
}

void AEXWreck::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	LiveWrecks = FMath::Max(0, LiveWrecks - 1);
	Super::EndPlay(EndPlayReason);
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
		// The charred overlay, and the flipbooks of the flames on the pieces, their trails and the smoke
		// (Scripts/make_fx_assets.py); without them the pieces fly in their own colours and only the light burns.
		CharMaterial = LoadFx<UMaterialInterface>(TEXT("/Game/FX/M_FX_Char.M_FX_Char"));
		FlipbookMaterial = LoadFx<UMaterialInterface>(TEXT("/Game/FX/M_FX_Flipbook.M_FX_Flipbook"));
		FireTexture = LoadFx<UTexture2D>(TEXT("/Game/FX/T_FX_Fire.T_FX_Fire"));
		SmokeTexture = LoadFx<UTexture2D>(TEXT("/Game/FX/T_FX_Smoke.T_FX_Smoke"));
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
	UMaterialInstanceDynamic* Char = nullptr;
	if (CharMaterial)
	{
		Char = UMaterialInstanceDynamic::Create(CharMaterial, this);
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
	// It burns like a ball of fire while it flies: the hull for 11 s, a module for 4.5-7 s (thinner, it burns out sooner).
	Piece.CharMat = Char;
	Piece.Burn = Pieces.Num() == 0 ? BurnSeconds : FMath::FRandRange(4.5f, 7.0f);
	Piece.Size = static_cast<float>(Piece.Half.GetMax()) * 2.0f;
	Piece.FlamePhase = FMath::FRandRange(0.0f, 16.0f);
	if (FlipbookMaterial && FireTexture)
	{
		Piece.Flame = NewObject<UMaterialBillboardComponent>(this);
		Piece.Flame->SetUsingAbsoluteLocation(true);
		Piece.Flame->SetupAttachment(GetRootComponent());
		Piece.Flame->RegisterComponent();
		Piece.FlameMat = UMaterialInstanceDynamic::Create(FlipbookMaterial, this);
		Piece.FlameMat->SetTextureParameterValue(TexParam, FireTexture);
		Piece.FlameMat->SetScalarParameterValue(ColsParam, 4.0f);
		Piece.FlameMat->SetScalarParameterValue(RowsParam, 4.0f);
		Piece.Flame->AddElement(Piece.FlameMat, nullptr, false, 100.0f, 100.0f, nullptr);
	}
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
	if ((!bHull && Speed < 9.0f) || CamDistM > NearM)
	{
		return;   // a wing landing flat, or a wreck far from the camera: no burst for that (fps)
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

void AEXWreck::Puff(const FPiece& Piece, bool bHull)
{
	if (!FlipbookMaterial || !SmokeTexture)
	{
		return;
	}
	FPuff* Slot = nullptr;
	for (FPuff& P : Puffs)
	{
		if (P.Age >= P.Life)
		{
			Slot = &P;
			break;
		}
	}
	if (!Slot && Puffs.Num() >= MaxSmoke)
	{
		Slot = &Puffs[0];
		for (FPuff& P : Puffs)
		{
			Slot = P.Age / P.Life > Slot->Age / Slot->Life ? &P : Slot;
		}
	}
	if (!Slot)
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
	// The hull's thick smoke column; a module's puffs as big as the module.
	const float SizeCm = Piece.Size * 100.0f;
	Slot->Pos = Piece.Pos * 100.0 + FVector(FMath::FRandRange(-0.1f, 0.1f) * SizeCm, FMath::FRandRange(-0.1f, 0.1f) * SizeCm, 0.2f * SizeCm);
	Slot->Age = 0.0f;
	Slot->Life = bHull ? FMath::FRandRange(2.2f, 3.0f) : FMath::FRandRange(1.6f, 2.4f);
	Slot->Size0 = bHull ? 220.0f : FMath::Max(100.0f, 0.8f * SizeCm);
	Slot->Size1 = bHull ? 950.0f : FMath::Clamp(2.5f * SizeCm, 300.0f, 700.0f);
	Slot->Material->SetScalarParameterValue(RotationParam, FMath::FRandRange(-0.6f, 0.6f));
	Slot->Sprite->SetWorldLocation(Slot->Pos);
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
	// Every piece burns like a ball of fire while it flies: flames on it streaming back from the way it flies (up when
	// it slows down), a trail of tongues of flame behind it and smoke rising from it; its charred skin cools from glowing
	// embers to soot as it burns out. The flames are turned on screen, so the camera's axes are needed.
	FVector CamRight = FVector::RightVector;
	FVector CamUp = FVector::UpVector;
	if (const APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(this, 0))
	{
		const FQuat CamQ = Cam->GetCameraRotation().Quaternion();
		CamRight = CamQ.GetRightVector();
		CamUp = CamQ.GetUpVector();
		CamDistM = static_cast<float>(FVector::Dist(Cam->GetCameraLocation(), Pieces[0].Pos * 100.0)) / 100.0f;
	}
	// how much of the trail and smoke to leave: all near the camera, half from NearM, none from FarM, shared out when
	// several wrecks burn at once
	const float Share = (CamDistM < NearM ? 1.0f : (CamDistM < FarM ? 0.5f : 0.0f)) / FMath::Max(1.0f, LiveWrecks * 0.5f);
	for (int32 Index = 0; Index < Pieces.Num(); ++Index)
	{
		FPiece& Piece = Pieces[Index];
		const bool bHull = Index == 0;
		Piece.Heat = FMath::Clamp(1.0f - Age / Piece.Burn, 0.0f, 1.0f);
		if (Piece.CharMat)
		{
			Piece.CharMat->SetScalarParameterValue(HeatParam, Piece.Heat);
		}
		// the way the flames stream (m/s: the wind of its flight and 4 m/s of rising heat)
		const FVector Stream = (FVector(0.0, 0.0, 4.0) - Piece.Vel).GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
		if (Piece.FlameMat)
		{
			// the flipbook's flames stand a third of the picture below its middle: the sprite sits that far along the stream
			const float FlameSize = Piece.Size * (1.1f + 1.2f * Piece.Heat) * 100.0f;   // the flames fill half the picture
			const float Angle = FMath::Atan2(static_cast<float>(FVector::DotProduct(Stream, CamRight)),
				static_cast<float>(FVector::DotProduct(Stream, CamUp)));
			Piece.FlameMat->SetScalarParameterValue(RotationParam, Angle);
			Piece.Flame->SetWorldLocation(Piece.Pos * 100.0 + Stream * (0.33f * FlameSize));
			EXFx::SetSpriteSize(Piece.Flame, Piece.FlameMat, Piece.FlameQuad, FlameSize);
			Piece.FlameMat->SetScalarParameterValue(FrameParam, FMath::Fmod(Age * 16.0f + Piece.FlamePhase, 16.0f));
			Piece.FlameMat->SetScalarParameterValue(IntensityParam, 5.0f * Piece.Heat);
			Piece.FlameMat->SetScalarParameterValue(OpacityParam, FMath::Clamp(Piece.Heat * 1.6f, 0.0f, 1.0f));
			Piece.Flame->SetVisibility(Piece.Heat > 0.02f);
		}
		// The trail: a tongue of flame every fifth of its size along the way while it is hot and moving (so many a second
		// at most), close enough to run together into one trail of fire.
		const float Speed = static_cast<float>(Piece.Vel.Size());
		Piece.TrailGap += Speed * DeltaSeconds;
		Piece.TrailWait -= DeltaSeconds;
		if (Share > 0.0f && Piece.Heat > 0.12f && Speed > 4.0f && Piece.TrailGap >= FMath::Max(0.45f, 0.2f * Piece.Size) / FMath::Sqrt(Share)
			&& Piece.TrailWait <= 0.0f)
		{
			Trail(Piece, Stream);
			Piece.TrailGap = 0.0f;
			Piece.TrailWait = 1.0f / ((bHull ? HullTrailRate : ModuleTrailRate) * Share);
		}
		// Smoke from every piece that burns (more as it burns harder); flying, it strings out into a smoke trail.
		Piece.PuffTimer -= DeltaSeconds;
		if (Share > 0.0f && Piece.Heat > 0.05f && Piece.PuffTimer <= 0.0f)
		{
			Piece.PuffTimer = (bHull ? FMath::Lerp(0.16f, 0.06f, Piece.Heat) : FMath::Lerp(0.2f, 0.08f, Piece.Heat)) / Share;
			Puff(Piece, bHull);
		}
	}
	UpdateTrails(DeltaSeconds, CamRight, CamUp);
	UpdatePuffs(DeltaSeconds);
	// The hull lights the sand round it while it burns.
	const FVector Hull = Pieces[0].Pos * 100.0;
	FireLight->SetWorldLocation(Hull + FVector(0.0, 0.0, 250.0));
	FireLight->SetIntensity(FireLightCd * Pieces[0].Heat * (0.8f + 0.2f * FMath::Sin(Age * 23.0f) * FMath::Sin(Age * 7.3f)));
}

void AEXWreck::Trail(const FPiece& Piece, const FVector& Stream)
{
	if (!FlipbookMaterial || !FireTexture)
	{
		return;
	}
	FTrail* Slot = nullptr;
	for (FTrail& Each : Trails)
	{
		if (Each.Life <= 0.0f)
		{
			Slot = &Each;
			break;
		}
	}
	if (!Slot && Trails.Num() >= MaxTrails)
	{
		// all of them burning: the oldest goes
		Slot = &Trails[0];
		for (FTrail& Each : Trails)
		{
			Slot = Each.Age / Each.Life > Slot->Age / Slot->Life ? &Each : Slot;
		}
	}
	if (!Slot)
	{
		FTrail& New = Trails.AddDefaulted_GetRef();
		New.Sprite = NewObject<UMaterialBillboardComponent>(this);
		New.Sprite->SetUsingAbsoluteLocation(true);
		New.Sprite->SetupAttachment(GetRootComponent());
		New.Sprite->RegisterComponent();
		New.Material = UMaterialInstanceDynamic::Create(FlipbookMaterial, this);
		New.Material->SetTextureParameterValue(TexParam, FireTexture);
		New.Material->SetScalarParameterValue(ColsParam, 4.0f);
		New.Material->SetScalarParameterValue(RowsParam, 4.0f);
		New.Sprite->AddElement(New.Material, nullptr, false, 100.0f, 100.0f, nullptr);
		Slot = &New;
	}
	// Left where the piece is (it flies on, so the tongues string out behind it), drifting a little; at least as big as
	// the gap since the last one, so they run together.
	const float SizeCm = Piece.Size * 100.0f;
	Slot->Pos = Piece.Pos * 100.0 + FMath::VRand() * (0.12f * SizeCm);
	Slot->Vel = Piece.Vel * 100.0 * 0.12 + FMath::VRand() * 60.0f;
	Slot->Stream = Stream;
	Slot->Age = 0.0f;
	Slot->Life = TrailLife * FMath::FRandRange(0.8f, 1.2f) * (0.7f + 0.3f * Piece.Heat);
	Slot->Size0 = FMath::Min(800.0f, FMath::Max(1.1f * SizeCm, 250.0f * Piece.TrailGap)) * FMath::FRandRange(0.85f, 1.15f);
	Slot->Size1 = Slot->Size0 * 1.3f;
	Slot->Glow = 3.5f * Piece.Heat;   // several overlap: their light adds up
	Slot->FrameShift = FMath::FRandRange(0.0f, 16.0f);
	Slot->Sprite->SetVisibility(true);
}

void AEXWreck::UpdateTrails(float Dt, const FVector& CamRight, const FVector& CamUp)
{
	for (FTrail& Each : Trails)
	{
		if (Each.Life <= 0.0f)
		{
			continue;
		}
		Each.Age += Dt;
		const float T = Each.Age / Each.Life;
		if (T >= 1.0f)
		{
			Each.Life = 0.0f;
			Each.Sprite->SetVisibility(false);
			continue;
		}
		Each.Pos += Each.Vel * Dt;
		Each.Vel *= FMath::Exp(-2.0f * Dt);
		Each.Vel.Z += 100.0f * Dt;   // the flames rise a little
		const float Size = FMath::Lerp(Each.Size0, Each.Size1, T);
		// standing on its base, its flames along the stream, turned so on screen
		Each.Sprite->SetWorldLocation(Each.Pos + Each.Stream * (0.33f * Size));
		EXFx::SetSpriteSize(Each.Sprite, Each.Material, Each.Quad, Size);
		const float Angle = FMath::Atan2(static_cast<float>(FVector::DotProduct(Each.Stream, CamRight)),
			static_cast<float>(FVector::DotProduct(Each.Stream, CamUp)));
		Each.Material->SetScalarParameterValue(RotationParam, Angle);
		Each.Material->SetScalarParameterValue(FrameParam, FMath::Fmod(Each.FrameShift + Each.Age * 16.0f, 16.0f));
		Each.Material->SetScalarParameterValue(IntensityParam, Each.Glow * (1.0f - T));
		Each.Material->SetScalarParameterValue(OpacityParam, FMath::Pow(1.0f - T, 1.5f) * FMath::Clamp(Each.Age / 0.03f, 0.0f, 1.0f));
	}
}

void AEXWreck::UpdatePuffs(float Dt)
{
	for (FPuff& P : Puffs)
	{
		if (P.Age >= P.Life)
		{
			continue;
		}
		P.Age += Dt;
		const float T = FMath::Clamp(P.Age / P.Life, 0.0f, 1.0f);
		P.Pos += FVector(0.0, 0.0, 160.0f * Dt);
		P.Sprite->SetWorldLocation(P.Pos);
		EXFx::SetSpriteSize(P.Sprite, P.Material, P.Quad, FMath::Lerp(P.Size0, P.Size1, FMath::Sqrt(T)));
		P.Material->SetScalarParameterValue(FrameParam, T * 63.0f);
		P.Material->SetScalarParameterValue(IntensityParam, 1.0f);
		P.Material->SetScalarParameterValue(OpacityParam, 0.7f * FMath::Clamp(P.Age / 0.2f, 0.0f, 1.0f) * FMath::Square(1.0f - T));
		P.Sprite->SetVisibility(T < 1.0f);
	}
}
