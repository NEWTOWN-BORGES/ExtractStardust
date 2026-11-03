#include "UI/EXGuideArrow.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	const FName ArrowColorParam(TEXT("Color"));
	const FName ArrowIntensityParam(TEXT("Intensity"));
	constexpr float ArrowScale = 2.2f;
	constexpr float ArrowUpCm = 420.0f;       // over the craft (player, 2026-10-27: "mais para cima, não para a frente")
	constexpr float ArrowAheadCm = 200.0f;    // over its middle
	constexpr float ArrowTiltDeg = 70.0f;     // nearly upright, face to the camera: straight on reads as an arrow up the screen
}

AEXGuideArrow::AEXGuideArrow()
{
	PrimaryActorTick.bCanEverTick = true;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
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
	// Flat, pointing along +X: a shaft and the two barbs of the head, bars of the 1 m cube meeting at the tip (+75 cm).
	Shaft = Make(TEXT("Shaft"), Cube.Object);
	Shaft->SetRelativeLocation(FVector(-25.0f, 0.0f, 0.0f) * ArrowScale);
	Shaft->SetRelativeScale3D(FVector(1.15f, 0.3f, 0.14f) * ArrowScale);
	HeadL = Make(TEXT("HeadL"), Cube.Object);
	HeadR = Make(TEXT("HeadR"), Cube.Object);
	for (const float Side : { 1.0f, -1.0f })
	{
		UStaticMeshComponent* Barb = Side > 0.0f ? HeadL.Get() : HeadR.Get();
		const float Angle = FMath::DegreesToRadians(140.0f * Side);
		Barb->SetRelativeLocation(FVector(75.0f + 38.0f * FMath::Cos(Angle), 38.0f * FMath::Sin(Angle), 0.0f) * ArrowScale);
		Barb->SetRelativeRotation(FRotator(0.0f, 140.0f * Side, 0.0f));
		Barb->SetRelativeScale3D(FVector(0.9f, 0.3f, 0.14f) * ArrowScale);
	}
	SetActorHiddenInGame(true);
}

void AEXGuideArrow::Point(const FVector& CraftLocation, const FVector2D& Heading, const FVector2D& TargetM, const FLinearColor& Colour)
{
	if (!Material)
	{
		Material = UMaterialInstanceDynamic::Create(Shaft->GetMaterial(0), this);
		Shaft->SetMaterial(0, Material);
		HeadL->SetMaterial(0, Material);
		HeadR->SetMaterial(0, Material);
	}
	LastPointTime = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0f;
	SetActorHiddenInGame(false);
	const FVector2D HereM(CraftLocation.X / 100.0f, CraftLocation.Y / 100.0f);
	const FVector2D To = (TargetM - HereM).GetSafeNormal();
	const float Want = FMath::RadiansToDegrees(FMath::Atan2(To.Y, To.X));
	// Turns quickly but smoothly (no jitter from the line's samples).
	const float Dt = GetWorld() ? GetWorld()->GetDeltaSeconds() : 0.016f;
	Yaw = bHasYaw ? Yaw + FMath::FindDeltaAngleDegrees(Yaw, Want) * FMath::Min(1.0f, Dt * 10.0f) : Want;
	bHasYaw = true;
	const FVector Bob(0.0f, 0.0f, 15.0f * FMath::Sin(Age * 3.0f));
	// The arrow turns in its own plane, and that plane leans towards the camera (behind the craft and below the arrow).
	const float CamYaw = FMath::RadiansToDegrees(FMath::Atan2(Heading.Y, Heading.X));
	const FQuat Turn = FQuat(FRotator(ArrowTiltDeg, CamYaw, 0.0f)) * FQuat(FRotator(0.0f, Yaw - CamYaw, 0.0f));
	SetActorLocationAndRotation(CraftLocation + FVector(Heading.X, Heading.Y, 0.0f) * ArrowAheadCm + FVector(0.0f, 0.0f, ArrowUpCm) + Bob, Turn);
	if (Material)
	{
		Material->SetVectorParameterValue(ArrowColorParam, Colour);
		Material->SetScalarParameterValue(ArrowIntensityParam, 2.6f + 0.6f * FMath::Sin(Age * 5.0f));
	}
}

void AEXGuideArrow::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;
	if (GetWorld() && GetWorld()->GetTimeSeconds() - LastPointTime > 0.2f && !IsHidden())
	{
		SetActorHiddenInGame(true);
		bHasYaw = false;
	}
}
