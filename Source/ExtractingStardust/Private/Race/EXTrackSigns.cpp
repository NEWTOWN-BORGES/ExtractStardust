#include "Race/EXTrackSigns.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float CmPerM = 100.0f;
	constexpr float StepM = 5.0f;                          // the race line's spacing
	constexpr float BendRadiusM = 450.0f;                  // tighter than this, a bend gets its chevron boards
	constexpr int32 BoardEvery = 5;                        // a board every 25 m along a bend
	constexpr int32 PoleEvery = 8;                         // edge poles every 40 m
	const FName ColorParam(TEXT("Color"));
	const FName IntensityParam(TEXT("Intensity"));
	const FLinearColor BoardColour(0.05f, 0.03f, 0.02f);   // dark boards, so the chevrons stand out
	const FLinearColor ChevronColour(1.0f, 0.62f, 0.06f);  // the dash-panel yellow of the jump arrows
	const FLinearColor PoleColour(0.10f, 0.09f, 0.08f);
	const FLinearColor LightColour(1.0f, 0.45f, 0.08f);    // amber edge lights
}

AEXTrackSigns::AEXTrackSigns()
{
	PrimaryActorTick.bCanEverTick = true;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	Boards = MakeLayer(TEXT("Boards"));
	Chevrons = MakeLayer(TEXT("Chevrons"));
	Posts = MakeLayer(TEXT("Posts"));
	Lights = MakeLayer(TEXT("Lights"));
}

UHierarchicalInstancedStaticMeshComponent* AEXTrackSigns::MakeLayer(const TCHAR* Name)
{
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Glow(TEXT("/Game/FX/M_FX_Glow.M_FX_Glow"));
	UHierarchicalInstancedStaticMeshComponent* Mesh = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(Name);
	Mesh->SetupAttachment(GetRootComponent());
	Mesh->SetStaticMesh(Cube.Object);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetCastShadow(false);
	if (Glow.Object)
	{
		Mesh->SetMaterial(0, Glow.Object);
	}
	return Mesh;
}

void AEXTrackSigns::Build(const TArray<FVector2D>& Route, const TArray<float>& Heights, const TArray<float>& HalfWidths)
{
	UWorld* World = GetWorld();
	const int32 N = FMath::Min(Route.Num(), Heights.Num());
	if (!World || N < 40)
	{
		return;
	}
	auto Paint = [this](UHierarchicalInstancedStaticMeshComponent* Mesh, const FLinearColor& Colour, float Intensity)
	{
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Mesh->GetMaterial(0), this);
		if (Material)
		{
			Material->SetVectorParameterValue(ColorParam, Colour);
			Material->SetScalarParameterValue(IntensityParam, Intensity);
			Mesh->SetMaterial(0, Material);
		}
		return Material;
	};
	Paint(Boards, BoardColour, 0.4f);
	ChevronMaterial = Paint(Chevrons, ChevronColour, 10.0f);
	Paint(Posts, PoleColour, 0.3f);
	LightMaterial = Paint(Lights, LightColour, 8.0f);

	FCollisionQueryParams Query(SCENE_QUERY_STAT(EXSigns), true);
	auto Ground = [&](const FVector2D& P, float GuessM, FVector& OutAt) -> bool
	{
		const FVector Guess(P.X * CmPerM, P.Y * CmPerM, GuessM * CmPerM);
		FHitResult Hit;
		if (World->LineTraceSingleByChannel(Hit, Guess + FVector(0.0f, 0.0f, 3000.0f), Guess - FVector(0.0f, 0.0f, 6000.0f), ECC_WorldStatic, Query))
		{
			OutAt = Hit.ImpactPoint;
			return true;
		}
		return false;
	};
	auto Dir = [&](int32 I)
	{
		return (Route[FMath::Min(I + 1, N - 1)] - Route[FMath::Max(I - 1, 0)]).GetSafeNormal();
	};
	auto UnderRoof = [&](int32 I)
	{
		const FVector At(Route[I].X * CmPerM, Route[I].Y * CmPerM, (Heights[I] + 4.0f) * CmPerM);
		FHitResult Hit;
		return World->LineTraceSingleByChannel(Hit, At, At + FVector(0.0f, 0.0f, 6000.0f), ECC_WorldStatic, Query);
	};
	auto HalfWidth = [&](int32 I)
	{
		return HalfWidths.IsValidIndex(I) && HalfWidths[I] >= 4.0f ? FMath::Clamp(HalfWidths[I], 8.0f, 60.0f) : 28.0f;
	};

	// Chevron boards on the outside of the bends, facing the ships coming in, pointing into the turn.
	int32 Signs = 0;
	for (int32 I = 8; I + 8 < N; I += BoardEvery)
	{
		const FVector2D In = (Route[I] - Route[I - 6]).GetSafeNormal();
		const FVector2D Out = (Route[I + 6] - Route[I]).GetSafeNormal();
		const float Turn = FMath::Atan2(In.X * Out.Y - In.Y * Out.X, FVector2D::DotProduct(In, Out));   // + turns towards +Y
		const float Radius = FMath::Abs(Turn) > KINDA_SMALL_NUMBER ? (12.0f * StepM) / FMath::Abs(Turn) : 1.0e6f;
		if (Radius > BendRadiusM || UnderRoof(I))
		{
			continue;
		}
		const FVector2D D = Dir(I);
		const FVector2D Side(-D.Y, D.X);
		const float Into = Turn > 0.0f ? 1.0f : -1.0f;
		const FVector2D Spot = Route[I] - Side * Into * (HalfWidth(I) + 8.0f);
		FVector Foot;
		if (!Ground(Spot, Heights[I], Foot))
		{
			continue;
		}
		const FVector Face = -FVector(D.X, D.Y, 0.0f);                   // towards the ships coming
		const FVector Point = FVector(Side.X, Side.Y, 0.0f) * Into;       // into the turn
		const FRotator Board = FRotationMatrix::MakeFromXZ(Face, FVector::UpVector).Rotator();
		const FVector Centre = Foot + FVector(0.0f, 0.0f, 350.0f);
		Boards->AddInstance(FTransform(Board, Centre, FVector(0.15f, 6.0f, 3.0f)), true);
		for (const float Leg : { -2.4f, 2.4f })
		{
			Posts->AddInstance(FTransform(Board, Foot + Point * Leg * CmPerM + FVector(0.0f, 0.0f, 100.0f), FVector(0.25f, 0.25f, 2.0f)), true);
		}
		// Two chevrons (») on the face, their tips into the turn.
		for (const float Shift : { -0.9f, 0.9f })
		{
			const FVector Tip = Centre + Face * 10.0f + Point * (Shift + 0.55f) * CmPerM;
			for (const float Arm : { -1.0f, 1.0f })
			{
				const FVector Along = (Point * FMath::Cos(FMath::DegreesToRadians(50.0f)) + FVector::UpVector * Arm * FMath::Sin(FMath::DegreesToRadians(50.0f))).GetSafeNormal();
				const FRotator Rotation = FRotationMatrix::MakeFromXZ(Along, Face).Rotator();
				Chevrons->AddInstance(FTransform(Rotation, Tip - Along * 75.0f, FVector(1.5f, 0.32f, 0.06f)), true);
			}
		}
		++Signs;
	}

	// Edge poles where nothing walls the road in (the sand), an amber light on top.
	int32 Poles = 0;
	for (int32 I = 4; I + 4 < N; I += PoleEvery)
	{
		if (UnderRoof(I))
		{
			continue;
		}
		const FVector2D D = Dir(I);
		const FVector2D Side(-D.Y, D.X);
		const float HalfW = HalfWidth(I);
		for (const float S : { -1.0f, 1.0f })
		{
			const FVector From(Route[I].X * CmPerM, Route[I].Y * CmPerM, (Heights[I] + 3.0f) * CmPerM);
			const FVector To = From + FVector(Side.X, Side.Y, 0.0f) * S * (HalfW + 15.0f) * CmPerM;
			FHitResult Wall;
			if (World->LineTraceSingleByChannel(Wall, From, To, ECC_WorldStatic, Query))
			{
				continue;   // a wall or a bank beside the road: it shows the way already
			}
			FVector Foot;
			if (!Ground(Route[I] + Side * S * (HalfW + 3.0f), Heights[I], Foot))
			{
				continue;
			}
			Posts->AddInstance(FTransform(FRotator::ZeroRotator, Foot + FVector(0.0f, 0.0f, 110.0f), FVector(0.2f, 0.2f, 2.2f)), true);
			Lights->AddInstance(FTransform(FRotator::ZeroRotator, Foot + FVector(0.0f, 0.0f, 240.0f), FVector(0.32f, 0.32f, 0.4f)), true);
			++Poles;
		}
	}
	UE_LOG(LogTemp, Display, TEXT("EXRACE signs: %d chevron boards, %d edge poles"), Signs, Poles);
}

void AEXTrackSigns::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;
	// The chevrons breathe a little, so they read as lit from far away; the edge lights stay steady.
	if (ChevronMaterial)
	{
		ChevronMaterial->SetScalarParameterValue(IntensityParam, 8.0f + 4.0f * (0.5f + 0.5f * FMath::Sin(Age * 3.0f)));
	}
}
