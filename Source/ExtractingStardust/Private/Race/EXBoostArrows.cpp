#include "Race/EXBoostArrows.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float CmPerM = 100.0f;
	constexpr float StepM = 5.0f;                       // the race line's spacing
	const FName ArrowColorParam(TEXT("Color"));
	const FName ArrowIntensityParam(TEXT("Intensity"));
	const FLinearColor ArrowColour(1.0f, 0.62f, 0.06f);  // dash-panel yellow
}

AEXBoostArrows::AEXBoostArrows()
{
	PrimaryActorTick.bCanEverTick = true;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Glow(TEXT("/Game/FX/M_FX_Glow.M_FX_Glow"));
	for (int32 Row = 0; Row < Rows; ++Row)
	{
		UHierarchicalInstancedStaticMeshComponent* Mesh = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(
			*FString::Printf(TEXT("ArrowRow%d"), Row));
		Mesh->SetupAttachment(GetRootComponent());
		Mesh->SetStaticMesh(Cube.Object);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetCastShadow(false);
		if (Glow.Object)
		{
			Mesh->SetMaterial(0, Glow.Object);
		}
		RowMeshes.Add(Mesh);
	}
}

int32 AEXBoostArrows::Build(const TArray<FVector2D>& Route, const TArray<float>& Heights, const TArray<float>& HalfWidths)
{
	UWorld* World = GetWorld();
	const int32 N = FMath::Min(Route.Num(), Heights.Num());
	if (!World || N < 40)
	{
		return 0;
	}
	for (int32 Row = 0; Row < RowMeshes.Num(); ++Row)
	{
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(RowMeshes[Row]->GetMaterial(0), this);
		if (Material)
		{
			Material->SetVectorParameterValue(ArrowColorParam, ArrowColour);
			RowMeshes[Row]->SetMaterial(0, Material);
		}
		RowMaterials.Add(Material);
	}
	FCollisionQueryParams Query(SCENE_QUERY_STAT(EXArrows), true);
	int32 Jumps = 0;
	for (int32 I = 6; I + 6 < N; ++I)
	{
		// A jump: the ground falls away by more than 3 m within the next 20 m, after an approach that is not already a
		// steep descent (a ramp, a lip, a crest).
		float Ahead = Heights[I];
		for (int32 K = 1; K <= 4; ++K)
		{
			Ahead = FMath::Min(Ahead, Heights[I + K]);
		}
		const float Approach = (Heights[I] - Heights[I - 4]) / (4.0f * StepM);
		if (Heights[I] - Ahead < 3.0f || Approach < -0.08f)
		{
			continue;
		}
		++Jumps;
		for (int32 Row = 0; Row < Rows; ++Row)
		{
			const int32 R = FMath::Max(I - (Rows - Row) * 2, 1);      // every 10 m, the last row just before the lip
			const FVector2D Dir = (Route[FMath::Min(R + 1, N - 1)] - Route[R - 1]).GetSafeNormal();
			const FVector2D Side(-Dir.Y, Dir.X);
			const float HalfW = HalfWidths.IsValidIndex(R) && HalfWidths[R] >= 4.0f ? FMath::Min(HalfWidths[R], 30.0f) : 20.0f;
			for (const float Across : { -0.5f, 0.0f, 0.5f })
			{
				const FVector2D C = Route[R] + Side * Across * HalfW;
				FVector Centre(C.X * CmPerM, C.Y * CmPerM, Heights[R] * CmPerM);
				FVector Up = FVector::UpVector;
				FHitResult Hit;
				if (World->LineTraceSingleByChannel(Hit, Centre + FVector(0.0f, 0.0f, 800.0f), Centre - FVector(0.0f, 0.0f, 3000.0f), ECC_WorldStatic, Query))
				{
					Centre = Hit.ImpactPoint;
					Up = Hit.ImpactNormal;
				}
				Centre += Up * 8.0f;
				const FVector Fwd = FVector::VectorPlaneProject(FVector(Dir.X, Dir.Y, 0.0f), Up).GetSafeNormal();
				const FVector Lat = FVector::CrossProduct(Up, Fwd);
				// A chevron: two arms 5 m long and 1 m wide meeting at a tip pointing down the road.
				const FVector Tip = Centre + Fwd * 200.0f;
				for (const float Arm : { -1.0f, 1.0f })
				{
					const FVector Along = (Fwd * FMath::Cos(FMath::DegreesToRadians(38.0f)) + Lat * Arm * FMath::Sin(FMath::DegreesToRadians(38.0f))).GetSafeNormal();
					const FVector Mid = Tip - Along * 250.0f;
					const FRotator Rotation = FRotationMatrix::MakeFromXZ(Along, Up).Rotator();
					RowMeshes[Row]->AddInstance(FTransform(Rotation, Mid, FVector(5.0f, 1.0f, 0.12f)), true);
				}
			}
		}
		I += 12;   // one set of arrows per jump
	}
	UE_LOG(LogTemp, Display, TEXT("EXRACE boost arrows before %d jumps"), Jumps);
	return Jumps;
}

void AEXBoostArrows::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;
	// The rows light up one after the other towards the lip, like a dash panel.
	for (int32 Row = 0; Row < RowMaterials.Num(); ++Row)
	{
		if (RowMaterials[Row])
		{
			const float Phase = FMath::Frac(Age * 1.6f - Row / static_cast<float>(Rows));
			RowMaterials[Row]->SetScalarParameterValue(ArrowIntensityParam, 3.0f + 14.0f * FMath::Square(1.0f - Phase));
		}
	}
}
