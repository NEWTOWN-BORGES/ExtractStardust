#include "Arena/EXTestArena.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

AEXTestArena::AEXTestArena()
{
	PrimaryActorTick.bCanEverTick = false;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Root->SetMobility(EComponentMobility::Movable);
	SetRootComponent(Root);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Basic(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Grid(TEXT("/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial"));
	CubeMesh = Cube.Object;
	CylinderMesh = Cylinder.Object;
	ColorMaterial = Basic.Object;
	GridMaterial = Grid.Object;
}

void AEXTestArena::BeginPlay()
{
	Super::BeginPlay();
	// The template map ships with a small floor of its own; the arena replaces it.
	for (TActorIterator<AStaticMeshActor> It(GetWorld()); It; ++It)
	{
		It->Destroy();
	}
	BuildArena();
}

void AEXTestArena::BuildArena()
{
	const FLinearColor Sand(0.42f, 0.30f, 0.20f);
	const FLinearColor Rock(0.30f, 0.22f, 0.16f);
	const FLinearColor White(0.85f, 0.85f, 0.82f);
	const FLinearColor Red(0.70f, 0.08f, 0.05f);
	const FLinearColor Orange(0.95f, 0.35f, 0.05f);
	const FLinearColor Steel(0.35f, 0.37f, 0.40f);

	// Ground: 6 km x 3 km, top at Z = 0, closed by 30 m walls.
	AddBlock(CubeMesh, FVector(250000.0f, 0.0f, -100.0f), FRotator::ZeroRotator, FVector(600000.0f, 300000.0f, 200.0f), Sand, true);
	for (const float Side : { -1.0f, 1.0f })
	{
		AddBlock(CubeMesh, FVector(250000.0f, Side * 150000.0f, 1500.0f), FRotator::ZeroRotator, FVector(600000.0f, 1000.0f, 3000.0f), Rock);
		AddBlock(CubeMesh, FVector(250000.0f + Side * 300000.0f, 0.0f, 1500.0f), FRotator::ZeroRotator, FVector(1000.0f, 300000.0f, 3000.0f), Rock);
	}

	// Speed references along the main line: cross stripes every 25 m, pylons every 50 m.
	for (int32 Index = 0; Index < 160; ++Index)
	{
		AddBlock(CubeMesh, FVector(2500.0f * Index, 0.0f, 1.0f), FRotator::ZeroRotator, FVector(250.0f, 6000.0f, 4.0f), Index % 2 ? White : Red);
	}
	for (int32 Index = 0; Index < 80; ++Index)
	{
		for (const float Side : { -1.0f, 1.0f })
		{
			AddBlock(CylinderMesh, FVector(5000.0f * Index, Side * 4500.0f, 600.0f), FRotator::ZeroRotator, FVector(150.0f, 150.0f, 1200.0f), Orange);
		}
	}

	// Jump ramp: 60 m long at 14 degrees, its leading edge on the ground at X = 400 m.
	{
		const float Pitch = 14.0f;
		const float Length = 6000.0f;
		const float Radians = FMath::DegreesToRadians(Pitch);
		const FVector Center(40000.0f + 0.5f * Length * FMath::Cos(Radians) + 50.0f * FMath::Sin(Radians), 0.0f,
			0.5f * Length * FMath::Sin(Radians) - 50.0f * FMath::Cos(Radians));
		AddBlock(CubeMesh, Center, FRotator(Pitch, 0.0f, 0.0f), FVector(Length, 3000.0f, 100.0f), White);
	}

	// Walled corridor (50 m wide, 15 m high) from 1.2 km to 2.2 km, like the canyon in the reference video.
	for (const float Side : { -1.0f, 1.0f })
	{
		AddBlock(CubeMesh, FVector(170000.0f, Side * 2600.0f, 750.0f), FRotator::ZeroRotator, FVector(100000.0f, 200.0f, 1500.0f), Rock);
	}

	// Half-pipe from 2.5 km to 3.3 km: 30 m flat floor with 35 degree banks, each 30 m wide.
	{
		const float BankDeg = 35.0f;
		const float BankWidth = 3000.0f;
		const float HalfFloor = 1500.0f;
		const float Radians = FMath::DegreesToRadians(BankDeg);
		for (const float Side : { -1.0f, 1.0f })
		{
			const FRotator Rotation(0.0f, 0.0f, -Side * BankDeg);
			const FVector TopCenter(290000.0f, Side * (HalfFloor + 0.5f * BankWidth * FMath::Cos(Radians)), 0.5f * BankWidth * FMath::Sin(Radians));
			AddBlock(CubeMesh, TopCenter - Rotation.RotateVector(FVector::UpVector) * 50.0f, Rotation, FVector(80000.0f, BankWidth, 100.0f), Steel);
		}
	}
}

UStaticMeshComponent* AEXTestArena::AddBlock(UStaticMesh* Mesh, const FVector& CenterCm, const FRotator& Rotation, const FVector& SizeCm,
	const FLinearColor& Color, bool bGridMaterial)
{
	UStaticMeshComponent* Block = NewObject<UStaticMeshComponent>(this);
	Block->SetMobility(EComponentMobility::Movable);
	Block->SetStaticMesh(Mesh);
	Block->SetRelativeTransform(FTransform(Rotation, CenterCm, SizeCm / 100.0f));
	Block->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	if (bGridMaterial && GridMaterial)
	{
		Block->SetMaterial(0, GridMaterial);
	}
	else if (ColorMaterial)
	{
		TObjectPtr<UMaterialInstanceDynamic>& Material = ColorMaterials.FindOrAdd(Color.ToString());
		if (!Material)
		{
			Material = UMaterialInstanceDynamic::Create(ColorMaterial, this);
			Material->SetVectorParameterValue(TEXT("Color"), Color);
		}
		Block->SetMaterial(0, Material);
	}
	Block->SetupAttachment(GetRootComponent());
	Block->RegisterComponent();
	return Block;
}
