#include "World/EXHangarStage.h"

#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

AEXHangarStage::AEXHangarStage()
{
	PrimaryActorTick.bCanEverTick = false;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SetRootComponent(SceneRoot);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	CubeMesh = Cube.Object;
}

void AEXHangarStage::BeginPlay()
{
	Super::BeginPlay();

	// A closed 90 x 90 m bay keeps the preview self-contained and clear of the expedition terrain.
	AddBox(TEXT("Floor"), FVector(0.0, 0.0, -120.0), FVector(45.0, 45.0, 1.2));
	AddBox(TEXT("Roof"), FVector(0.0, 0.0, 6200.0), FVector(45.0, 45.0, 1.0));
	AddBox(TEXT("RearWall"), FVector(4400.0, 0.0, 3000.0), FVector(1.0, 45.0, 30.0));
	AddBox(TEXT("LeftWall"), FVector(0.0, -4400.0, 3000.0), FVector(45.0, 1.0, 30.0));
	AddBox(TEXT("RightWall"), FVector(0.0, 4400.0, 3000.0), FVector(45.0, 1.0, 30.0));
	AddBox(TEXT("EntranceLeft"), FVector(-4400.0, -3900.0, 3000.0), FVector(1.0, 6.0, 30.0));
	AddBox(TEXT("EntranceRight"), FVector(-4400.0, 3900.0, 3000.0), FVector(1.0, 6.0, 30.0));
	AddBox(TEXT("EntranceHeader"), FVector(-4400.0, 0.0, 5900.0), FVector(1.0, 34.0, 4.0));

	// A raised display pad and simple runway inlays make the ship readable against the dark bay.
	AddBox(TEXT("DisplayPad"), FVector(0.0, 0.0, 35.0), FVector(700.0, 520.0, 0.35));
	AddBox(TEXT("RunwayLeft"), FVector(-1200.0, -950.0, 8.0), FVector(3100.0, 10.0, 0.08));
	AddBox(TEXT("RunwayRight"), FVector(-1200.0, 950.0, 8.0), FVector(3100.0, 10.0, 0.08));
	AddBox(TEXT("RunwayEnd"), FVector(-4300.0, 0.0, 8.0), FVector(12.0, 950.0, 0.08));

	AddLight(TEXT("KeyLight"), FVector(-900.0, -1100.0, 5200.0), FLinearColor(0.78f, 0.88f, 1.0f), 180000.0f, 9000.0f);
	AddLight(TEXT("WarmRim"), FVector(3000.0, 1800.0, 4300.0), FLinearColor(1.0f, 0.36f, 0.12f), 65000.0f, 7500.0f);
	AddLight(TEXT("CoolRim"), FVector(2500.0, -2000.0, 3800.0), FLinearColor(0.12f, 0.66f, 1.0f), 70000.0f, 7500.0f);
}

void AEXHangarStage::AddBox(const TCHAR* Name, const FVector& Location, const FVector& Scale)
{
	if (!CubeMesh || !SceneRoot)
	{
		return;
	}

	UStaticMeshComponent* Box = NewObject<UStaticMeshComponent>(this, FName(Name));
	if (!Box)
	{
		return;
	}
	AddInstanceComponent(Box);
	Box->SetupAttachment(SceneRoot);
	Box->SetStaticMesh(CubeMesh);
	Box->SetRelativeLocation(Location);
	Box->SetRelativeScale3D(Scale);
	Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Box->SetCastShadow(false);
	Box->RegisterComponent();
}

void AEXHangarStage::AddLight(const TCHAR* Name, const FVector& Location, const FLinearColor& Colour, float Intensity, float Radius)
{
	UPointLightComponent* Light = NewObject<UPointLightComponent>(this, FName(Name));
	if (!Light)
	{
		return;
	}
	AddInstanceComponent(Light);
	Light->SetupAttachment(SceneRoot);
	Light->SetRelativeLocation(Location);
	Light->SetLightColor(Colour);
	Light->SetIntensity(Intensity);
	Light->SetAttenuationRadius(Radius);
	Light->SetCastShadows(false);
	Light->RegisterComponent();
}
