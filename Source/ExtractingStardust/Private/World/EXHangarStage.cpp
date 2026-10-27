#include "World/EXHangarStage.h"

#include "Components/RectLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	const FVector HangarOrigin(-1200000.0f, 0.0f, 300000.0f);   // 12 km west of the track, 3 km up
	constexpr float RoomX = 3200.0f;
	constexpr float RoomY = 2800.0f;
	constexpr float RoomH = 1000.0f;
	constexpr float WallT = 60.0f;          // thick, so no light leaks through
	constexpr float PlatformTopZ = 25.0f;
	const FName HangarColorParam(TEXT("Color"));
	const FName HangarIntensityParam(TEXT("Intensity"));
	// Light levels. Sized like the desert maps (sun of 10 lux): the floor gets ~12 lux in the workshop, so the auto
	// exposure that suits the desert suits the hangar too. The menu keeps 6 % of the work lights and a show spot on the ship.
	constexpr float WorkLumens = 1300.0f;      // each ceiling rect light, workshop
	constexpr float WorkMenuShare = 0.06f;     // ... in the menu
	constexpr float PanelGlowWork = 6.0f;      // glowing ceiling panels
	constexpr float PanelGlowMenu = 0.3f;
	constexpr float KeySpotLumens = 600.0f;
	constexpr float FillSpotWork = 400.0f, FillSpotMenu = 250.0f;
	constexpr float TopSpotWork = 300.0f, TopSpotMenu = 750.0f;
	constexpr float SignGlowWork = 8.0f, SignGlowMenu = 3.0f;
	constexpr int32 PanelColumns = 7;
}

AEXHangarStage::AEXHangarStage()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = true;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Root->SetMobility(EComponentMobility::Movable);
	SetRootComponent(Root);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Basic(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Glow(TEXT("/Game/FX/M_FX_Glow.M_FX_Glow"));
	CubeMesh = Cube.Object;
	CylinderMesh = Cylinder.Object;
	ColorMaterial = Basic.Object;
	GlowMaterial = Glow.Object;
}

AEXHangarStage* AEXHangarStage::FindOrSpawn(UWorld* World)
{
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AEXHangarStage> It(World); It; ++It)
	{
		return *It;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	return World->SpawnActor<AEXHangarStage>(HangarOrigin, FRotator::ZeroRotator, Params);
}

FVector AEXHangarStage::GetPlatformTop() const
{
	return GetActorLocation() + FVector(0.0f, 0.0f, PlatformTopZ);
}

void AEXHangarStage::BeginPlay()
{
	Super::BeginPlay();
	Build();
}

void AEXHangarStage::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// Lights on in about 1.4 s (a wave along the ceiling), down in 1 s.
	const float Next = FMath::FInterpConstantTo(LightLevel, LightTarget, DeltaSeconds, LightTarget > LightLevel ? 0.7f : 1.0f);
	if (!bLightsApplied || Next != LightLevel)
	{
		LightLevel = Next;
		bLightsApplied = true;
		ApplyLights();
	}
}

void AEXHangarStage::ApplyLights()
{
	// Each column of the ceiling comes on a little after the one before it.
	auto ColumnLevel = [this](int32 Column)
	{
		return FMath::SmoothStep(0.0f, 1.0f, FMath::Clamp(LightLevel * 1.6f - 0.6f * Column / (PanelColumns - 1.0f), 0.0f, 1.0f));
	};
	for (int32 Column = 0; Column < PanelGlows.Num(); ++Column)
	{
		if (PanelGlows[Column])
		{
			PanelGlows[Column]->SetScalarParameterValue(HangarIntensityParam, FMath::Lerp(PanelGlowMenu, PanelGlowWork, ColumnLevel(Column)));
		}
	}
	for (int32 Index = 0; Index < WorkLights.Num(); ++Index)
	{
		if (WorkLights[Index] && WorkLightColumns.IsValidIndex(Index))
		{
			WorkLights[Index]->SetIntensity(WorkLumens * FMath::Lerp(WorkMenuShare, 1.0f, ColumnLevel(WorkLightColumns[Index])));
		}
	}
	const float Level = FMath::SmoothStep(0.0f, 1.0f, LightLevel);
	if (FillSpot)
	{
		FillSpot->SetIntensity(FMath::Lerp(FillSpotMenu, FillSpotWork, Level));
	}
	if (TopSpot)
	{
		TopSpot->SetIntensity(FMath::Lerp(TopSpotMenu, TopSpotWork, Level));
	}
	if (SignGlow)
	{
		SignGlow->SetScalarParameterValue(HangarIntensityParam, FMath::Lerp(SignGlowMenu, SignGlowWork, Level));
	}
}

void AEXHangarStage::Build()
{
	if (bBuilt)
	{
		return;
	}
	bBuilt = true;
	const FLinearColor Floor(0.42f, 0.43f, 0.45f);
	const FLinearColor Line(0.16f, 0.16f, 0.17f);
	const FLinearColor Yellow(0.85f, 0.62f, 0.05f);
	const FLinearColor Wall(0.62f, 0.63f, 0.65f);
	const FLinearColor Rib(0.36f, 0.37f, 0.40f);
	const FLinearColor Dark(0.08f, 0.08f, 0.09f);
	const FLinearColor PlatformDark(0.16f, 0.17f, 0.19f);
	const FLinearColor Steel(0.50f, 0.52f, 0.55f);
	const FLinearColor Panel(1.0f, 0.97f, 0.92f);
	const FLinearColor Rim(1.0f, 0.45f, 0.15f);
	const FLinearColor Cabinet(0.60f, 0.06f, 0.04f);
	const FLinearColor Crate(0.90f, 0.32f, 0.06f);
	const FRotator None = FRotator::ZeroRotator;

	// Floor, grid lines every 2 m, the yellow safety ring round the platform.
	AddPart(CubeMesh, FVector(0.0f, 0.0f, -WallT * 0.5f), None, FVector(RoomX + 2.0f * WallT, RoomY + 2.0f * WallT, WallT), Floor);
	for (int32 I = -8; I <= 8; ++I)
	{
		AddPart(CubeMesh, FVector(I * 200.0f, 0.0f, 0.2f), None, FVector(3.0f, RoomY, 0.4f), Line);
	}
	for (int32 J = -7; J <= 7; ++J)
	{
		AddPart(CubeMesh, FVector(0.0f, J * 200.0f, 0.2f), None, FVector(RoomX, 3.0f, 0.4f), Line);
	}
	for (int32 K = 0; K < 16; ++K)
	{
		const float Angle = 360.0f * K / 16.0f;
		const FVector Dir = FRotator(0.0f, Angle, 0.0f).Vector();
		AddPart(CubeMesh, Dir * 620.0f + FVector(0.0f, 0.0f, 0.5f), FRotator(0.0f, Angle, 0.0f), FVector(15.0f, 245.0f, 0.6f), Yellow);
	}

	// Walls and ceiling (overlapping at the corners), ribs, a dark band along the foot of the walls.
	for (const float Side : { -1.0f, 1.0f })
	{
		AddPart(CubeMesh, FVector(Side * (RoomX + WallT) * 0.5f, 0.0f, RoomH * 0.5f), None, FVector(WallT, RoomY + 2.0f * WallT, RoomH), Wall);
		AddPart(CubeMesh, FVector(0.0f, Side * (RoomY + WallT) * 0.5f, RoomH * 0.5f), None, FVector(RoomX + 2.0f * WallT, WallT, RoomH), Wall);
		for (int32 I = -7; I <= 7; ++I)
		{
			AddPart(CubeMesh, FVector(I * 220.0f, Side * (RoomY * 0.5f - 8.0f), RoomH * 0.5f), None, FVector(25.0f, 16.0f, RoomH), Rib);
		}
		for (int32 J = -5; J <= 5; ++J)
		{
			AddPart(CubeMesh, FVector(Side * (RoomX * 0.5f - 8.0f), J * 240.0f, RoomH * 0.5f), None, FVector(16.0f, 25.0f, RoomH), Rib);
		}
		AddPart(CubeMesh, FVector(0.0f, Side * (RoomY * 0.5f - 3.0f), 50.0f), None, FVector(RoomX, 6.0f, 100.0f), Dark);
		AddPart(CubeMesh, FVector(Side * (RoomX * 0.5f - 3.0f), 0.0f, 50.0f), None, FVector(6.0f, RoomY, 100.0f), Dark);
	}
	AddPart(CubeMesh, FVector(0.0f, 0.0f, RoomH + WallT * 0.5f), None, FVector(RoomX + 2.0f * WallT, RoomY + 2.0f * WallT, WallT), Wall);

	// Ceiling: two double rows of glowing panels with a rect light under every other one (each column of panels has its
	// own glow material, so the lights can come on one column after another); the crane rail.
	for (int32 I = -3; I <= 3; ++I)
	{
		UMaterialInstanceDynamic* ColumnGlow = MakeGlow(Panel, PanelGlowWork);
		PanelGlows.Add(ColumnGlow);
		for (const int32 Row : { -2, -1, 1, 2 })
		{
			const FVector At(I * 440.0f, Row * 340.0f, RoomH - 6.0f);
			AddPart(CubeMesh, At, None, FVector(340.0f, 60.0f, 8.0f), Panel, PanelGlowWork, ColumnGlow);
			if ((I + 3) % 2 == 0 && (Row == -1 || Row == 1))
			{
				WorkLights.Add(AddRectLight(At - FVector(0.0f, 0.0f, 12.0f), WorkLumens, 340.0f, 60.0f, false));   // the spots cast the shadows
				WorkLightColumns.Add(I + 3);
			}
		}
	}
	AddPart(CubeMesh, FVector(0.0f, 0.0f, RoomH - 60.0f), None, FVector(RoomX, 40.0f, 50.0f), Dark);

	// Key and fill light on the ship, and the show spot straight above it (the pool of light of the menu).
	KeySpot = AddSpot(FVector(700.0f, 700.0f, 650.0f), FVector(0.0f, 0.0f, 100.0f), KeySpotLumens, FLinearColor(1.0f, 0.92f, 0.82f), 34.0f);
	FillSpot = AddSpot(FVector(-700.0f, -600.0f, 650.0f), FVector(0.0f, 0.0f, 100.0f), FillSpotWork, FLinearColor(0.86f, 0.9f, 1.0f), 34.0f);
	TopSpot = AddSpot(FVector(0.0f, 0.0f, RoomH - 70.0f), FVector(0.0f, 0.0f, 0.0f), TopSpotWork, FLinearColor(1.0f, 0.95f, 0.88f), 26.0f);

	// Turntable: base, glowing rim, steel top.
	AddPart(CylinderMesh, FVector(0.0f, 0.0f, 11.0f), None, FVector(920.0f, 920.0f, 22.0f), PlatformDark);
	AddPart(CylinderMesh, FVector(0.0f, 0.0f, 22.0f), None, FVector(926.0f, 926.0f, 5.0f), Rim, 10.0f);
	AddPart(CylinderMesh, FVector(0.0f, 0.0f, 24.0f), None, FVector(900.0f, 900.0f, 2.0f), Steel);

	// Workshop: tool cabinets on the north wall, crates in the south-east corner, gas cylinders, a cart, a lit sign.
	for (int32 I = 0; I < 5; ++I)
	{
		const FVector At(-850.0f + I * 130.0f, RoomY * 0.5f - 70.0f, 55.0f);
		AddPart(CubeMesh, At, None, FVector(120.0f, 70.0f, 110.0f), Cabinet);
		AddPart(CubeMesh, At + FVector(0.0f, 0.0f, 57.0f), None, FVector(120.0f, 72.0f, 4.0f), Steel);
	}
	const FVector Crates[4] = { FVector(1200.0f, -1120.0f, 50.0f), FVector(1320.0f, -1120.0f, 50.0f), FVector(1260.0f, -1120.0f, 150.0f),
		FVector(1360.0f, -990.0f, 50.0f) };
	for (int32 I = 0; I < 4; ++I)
	{
		AddPart(CubeMesh, Crates[I], None, FVector(100.0f, 100.0f, 100.0f), I % 2 == 0 ? Crate : Dark);
	}
	for (int32 K = 0; K < 4; ++K)
	{
		AddPart(CylinderMesh, FVector(-1460.0f, -1050.0f + K * 60.0f, 80.0f), None, FVector(44.0f, 44.0f, 160.0f), Steel);
	}
	AddPart(CubeMesh, FVector(1100.0f, 900.0f, 45.0f), None, FVector(140.0f, 80.0f, 90.0f), Dark);
	SignGlow = MakeGlow(Rim, SignGlowWork);
	AddPart(CubeMesh, FVector(0.0f, RoomY * 0.5f - 20.0f, 720.0f), None, FVector(900.0f, 6.0f, 100.0f), Rim, SignGlowWork, SignGlow);

	// Start in the mood asked for (the menu, unless the hangar opened first).
	ApplyLights();
	bLightsApplied = true;
}

UStaticMeshComponent* AEXHangarStage::AddPart(UStaticMesh* Mesh, const FVector& CenterCm, const FRotator& Rotation, const FVector& SizeCm,
	const FLinearColor& Color, float Glow, UMaterialInstanceDynamic* OwnMaterial)
{
	UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this);
	Part->SetMobility(EComponentMobility::Movable);
	Part->SetStaticMesh(Mesh);
	Part->SetRelativeTransform(FTransform(Rotation, CenterCm, SizeCm / 100.0f));
	Part->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	UMaterialInterface* Base = Glow > 0.0f && GlowMaterial ? GlowMaterial.Get() : ColorMaterial.Get();
	if (OwnMaterial)
	{
		Part->SetMaterial(0, OwnMaterial);
	}
	else if (Base)
	{
		const FString Key = FString::Printf(TEXT("%s_%.1f"), *Color.ToString(), Glow);
		TObjectPtr<UMaterialInstanceDynamic>& Material = Materials.FindOrAdd(Key);
		if (!Material)
		{
			Material = UMaterialInstanceDynamic::Create(Base, this);
			Material->SetVectorParameterValue(HangarColorParam, Color);
			if (Glow > 0.0f)
			{
				Material->SetScalarParameterValue(HangarIntensityParam, Glow);
			}
		}
		Part->SetMaterial(0, Material);
	}
	Part->SetupAttachment(GetRootComponent());
	Part->RegisterComponent();
	return Part;
}

UMaterialInstanceDynamic* AEXHangarStage::MakeGlow(const FLinearColor& Color, float Glow)
{
	UMaterialInterface* Base = GlowMaterial ? GlowMaterial.Get() : ColorMaterial.Get();
	if (!Base)
	{
		return nullptr;
	}
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Base, this);
	Material->SetVectorParameterValue(HangarColorParam, Color);
	Material->SetScalarParameterValue(HangarIntensityParam, Glow);
	return Material;
}

URectLightComponent* AEXHangarStage::AddRectLight(const FVector& Location, float Lumens, float WidthCm, float HeightCm, bool bShadows)
{
	URectLightComponent* Light = NewObject<URectLightComponent>(this);
	Light->SetMobility(EComponentMobility::Movable);
	Light->SetRelativeLocation(Location);
	Light->SetRelativeRotation(FRotator(-90.0f, 0.0f, 0.0f));   // facing the floor
	Light->SetIntensityUnits(ELightUnits::Lumens);
	Light->SetIntensity(Lumens);
	Light->SetSourceWidth(WidthCm);
	Light->SetSourceHeight(HeightCm);
	Light->SetAttenuationRadius(2600.0f);
	Light->SetLightColor(FLinearColor(1.0f, 0.97f, 0.92f));
	Light->SetCastShadows(bShadows);
	Light->SetupAttachment(GetRootComponent());
	Light->RegisterComponent();
	return Light;
}

USpotLightComponent* AEXHangarStage::AddSpot(const FVector& Location, const FVector& Target, float Lumens, const FLinearColor& Color, float OuterDeg)
{
	USpotLightComponent* Light = NewObject<USpotLightComponent>(this);
	Light->SetMobility(EComponentMobility::Movable);
	Light->SetRelativeLocation(Location);
	Light->SetRelativeRotation((Target - Location).Rotation());
	Light->SetIntensityUnits(ELightUnits::Lumens);
	Light->SetIntensity(Lumens);
	Light->SetInnerConeAngle(OuterDeg * 0.55f);
	Light->SetOuterConeAngle(OuterDeg);
	Light->SetAttenuationRadius(2500.0f);
	Light->SetLightColor(Color);
	Light->SetCastShadows(true);
	Light->SetupAttachment(GetRootComponent());
	Light->RegisterComponent();
	return Light;
}
