#include "Arena/EXPhysicsSandbox.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Flight/EXHoverCraft.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float CmPerM = 100.0f;
	constexpr float LaneAY = -300.0f;     // m: the features' straight (out, +X)
	constexpr float LaneBY = 300.0f;      // m: the pack's straight (back, -X)
	constexpr float StraightM = 2600.0f;
	constexpr float TurnRadiusM = 300.0f;
	constexpr float TrackWidthM = 70.0f;
	constexpr int32 BotCount = 7;
	const float BotSkills[BotCount] = { 0.95f, 0.92f, 0.9f, 0.88f, 0.86f, 0.84f, 0.82f };

	/** A ramp of a length and an angle from X0 (m) at the ground: its points; with a drop at the lip when asked. */
	void Ramp(TArray<FVector2D>& P, float X0, float Z0, float LengthM, float Deg, bool bDrop)
	{
		const float R = FMath::DegreesToRadians(Deg);
		const FVector2D Top(X0 + LengthM * FMath::Cos(R), Z0 + LengthM * FMath::Sin(R));
		P.Add(FVector2D(X0, Z0));
		P.Add(Top);
		if (bDrop)
		{
			P.Add(FVector2D(Top.X + 0.05f, 0.0f));
		}
	}

	/** A smooth crest (a cosine hump) of a height over a length, sampled every 4 m. */
	void Crest(TArray<FVector2D>& P, float X0, float LengthM, float HeightM)
	{
		for (float X = 0.0f; X <= LengthM + 0.01f; X += 4.0f)
		{
			P.Add(FVector2D(X0 + X, 0.5f * HeightM * (1.0f - FMath::Cos(2.0f * PI * X / LengthM))));
		}
	}
}

AEXPhysicsSandbox::AEXPhysicsSandbox()
{
	PrimaryActorTick.bCanEverTick = true;
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

void AEXPhysicsSandbox::BeginPlay()
{
	Super::BeginPlay();
	Build();
}

float AEXPhysicsSandbox::FeatureZ(float XM) const
{
	for (int32 Index = 1; Index < Profile.Num(); ++Index)
	{
		if (XM <= Profile[Index].X)
		{
			const FVector2D& A = Profile[Index - 1];
			const FVector2D& B = Profile[Index];
			const float T = B.X - A.X > KINDA_SMALL_NUMBER ? (XM - A.X) / (B.X - A.X) : 1.0f;
			return FMath::Lerp(A.Y, B.Y, FMath::Clamp(T, 0.0f, 1.0f));
		}
	}
	return 0.0f;
}

void AEXPhysicsSandbox::Build()
{
	const FLinearColor Sand(0.42f, 0.30f, 0.20f);
	const FLinearColor Rock(0.30f, 0.22f, 0.16f);
	const FLinearColor White(0.85f, 0.85f, 0.82f);
	const FLinearColor Red(0.70f, 0.08f, 0.05f);
	const FLinearColor Orange(0.95f, 0.35f, 0.05f);
	const FLinearColor Cyan(0.10f, 0.75f, 1.0f);
	const FLinearColor Steel(0.35f, 0.37f, 0.40f);

	// The features, out along the first straight (metres from its start).
	Profile.Reset();
	Profile.Add(FVector2D(0.0f, 0.0f));
	Ramp(Profile, 200.0f, 0.0f, 30.0f, 10.0f, true);            // a small kicker (5 m)
	Ramp(Profile, 450.0f, 0.0f, 50.0f, 12.0f, false);           // a table top: up, 60 m of top, down
	Profile.Add(FVector2D(Profile.Last().X + 60.0f, Profile.Last().Y));
	{
		const FVector2D Top = Profile.Last();
		const float R = FMath::DegreesToRadians(12.0f);
		Profile.Add(FVector2D(Top.X + 50.0f * FMath::Cos(R), 0.0f));
	}
	Ramp(Profile, 800.0f, 0.0f, 60.0f, 18.0f, true);            // a big kicker (18.5 m)
	Crest(Profile, 1250.0f, 120.0f, 3.0f);                      // three smooth crests
	Crest(Profile, 1450.0f, 160.0f, 6.0f);
	Crest(Profile, 1700.0f, 200.0f, 10.0f);
	Ramp(Profile, 2000.0f, 0.0f, 100.0f, 8.0f, false);          // a climb to a plateau that ends in a 14 m cliff
	Profile.Add(FVector2D(Profile.Last().X + 120.0f, Profile.Last().Y));
	Profile.Add(FVector2D(Profile.Last().X + 0.05f, 0.0f));
	for (float X = 2330.0f; X <= 2530.0f; X += 1.0f)            // a washboard: 0.5 m rollers every 8 m
	{
		Profile.Add(FVector2D(X, 0.25f * (1.0f - FMath::Cos(2.0f * PI * (X - 2330.0f) / 8.0f))));
	}
	Profile.Add(FVector2D(StraightM, 0.0f));

	// The floor (top at 0), closed by walls, and a grid to read the speed.
	const float MinX = -TurnRadiusM - 200.0f;
	const float MaxX = StraightM + TurnRadiusM + 200.0f;
	const float HalfY = TurnRadiusM + 250.0f;
	AddBlock(CubeMesh, FVector((MinX + MaxX) * 0.5f, 0.0f, -1.0f) * CmPerM, FRotator::ZeroRotator,
		FVector(MaxX - MinX, HalfY * 2.0f, 2.0f) * CmPerM, Sand, true);
	for (const float S : { -1.0f, 1.0f })
	{
		AddBlock(CubeMesh, FVector((MinX + MaxX) * 0.5f, S * HalfY, 10.0f) * CmPerM, FRotator::ZeroRotator, FVector(MaxX - MinX, 4.0f, 20.0f) * CmPerM, Rock);
		AddBlock(CubeMesh, FVector(S > 0 ? MaxX : MinX, 0.0f, 10.0f) * CmPerM, FRotator::ZeroRotator, FVector(4.0f, HalfY * 2.0f, 20.0f) * CmPerM, Rock);
	}
	// The features as slabs whose top follows the profile, and the cliff faces.
	AddProfile(Profile, LaneAY, TrackWidthM, White);
	// Speed marks: stripes across both straights every 50 m, pylons on the edges every 100 m.
	for (float X = 0.0f; X <= StraightM; X += 50.0f)
	{
		const bool bRed = FMath::RoundToInt(X / 50.0f) % 2 == 0;
		AddBlock(CubeMesh, FVector(X, LaneBY, 0.03f) * CmPerM, FRotator::ZeroRotator, FVector(2.0f, TrackWidthM, 0.06f) * CmPerM, bRed ? Red : White);
		if (FMath::RoundToInt(X) % 100 == 0)
		{
			for (const float Lane : { LaneAY, LaneBY })
			{
				for (const float S : { -1.0f, 1.0f })
				{
					const float Z = Lane == LaneAY ? FeatureZ(X) : 0.0f;
					AddBlock(CylinderMesh, FVector(X, Lane + S * (TrackWidthM * 0.5f + 3.0f), Z + 3.0f) * CmPerM, FRotator::ZeroRotator,
						FVector(1.0f, 1.0f, 6.0f) * CmPerM, Lane == LaneAY ? Cyan : Orange);
				}
			}
		}
	}
	// The turns are flat; a ring of pylons marks each.
	for (int32 Turn = 0; Turn < 2; ++Turn)
	{
		const FVector2D C(Turn == 0 ? StraightM : 0.0f, 0.0f);
		for (int32 K = 0; K <= 12; ++K)
		{
			const float A = (Turn == 0 ? -90.0f : 90.0f) + 180.0f * K / 12.0f;
			const FVector2D Dir(FMath::Cos(FMath::DegreesToRadians(A)), FMath::Sin(FMath::DegreesToRadians(A)));
			for (const float R : { TurnRadiusM - TrackWidthM * 0.5f - 3.0f, TurnRadiusM + TrackWidthM * 0.5f + 3.0f })
			{
				const FVector2D P = C + Dir * R;
				AddBlock(CylinderMesh, FVector(P.X, P.Y, 3.0f) * CmPerM, FRotator::ZeroRotator, FVector(1.0f, 1.0f, 6.0f) * CmPerM, Steel);
			}
		}
	}

	// The loop the crafts follow (cm): out along the features, round, back along the pack's straight, round.
	Route.Reset();
	const FVector O = Origin();
	for (float X = 0.0f; X < StraightM; X += 5.0f)
	{
		Route.Add(O + FVector(X, LaneAY, FeatureZ(X)) * CmPerM);
	}
	for (float A = -90.0f; A < 90.0f; A += 1.0f)
	{
		Route.Add(O + FVector(StraightM + TurnRadiusM * FMath::Cos(FMath::DegreesToRadians(A)), TurnRadiusM * FMath::Sin(FMath::DegreesToRadians(A)), 0.0f) * CmPerM);
	}
	for (float X = StraightM; X > 0.0f; X -= 5.0f)
	{
		Route.Add(O + FVector(X, LaneBY, 0.0f) * CmPerM);
	}
	for (float A = 90.0f; A < 270.0f; A += 1.0f)
	{
		Route.Add(O + FVector(TurnRadiusM * FMath::Cos(FMath::DegreesToRadians(A)), TurnRadiusM * FMath::Sin(FMath::DegreesToRadians(A)), 0.0f) * CmPerM);
	}
}

void AEXPhysicsSandbox::AddProfile(const TArray<FVector2D>& ProfileM, float LaneY, float WidthM, const FLinearColor& Colour)
{
	constexpr float Thick = 1.0f;
	for (int32 Index = 1; Index < ProfileM.Num(); ++Index)
	{
		const FVector2D A = ProfileM[Index - 1];
		const FVector2D B = ProfileM[Index];
		if (A.Y < 0.01f && B.Y < 0.01f)
		{
			continue;   // on the floor
		}
		const float Dx = B.X - A.X;
		if (Dx < 0.5f)
		{
			// A cliff face (the lip of a kicker, the plateau's edge): a wall from the floor to the top.
			const float H = FMath::Max(A.Y, B.Y);
			AddBlock(CubeMesh, FVector(A.X - 0.5f, LaneY, H * 0.5f) * CmPerM, FRotator::ZeroRotator, FVector(1.0f, WidthM, H) * CmPerM, Colour);
			continue;
		}
		const float Length = FMath::Sqrt(Dx * Dx + FMath::Square(B.Y - A.Y));
		const float Pitch = FMath::RadiansToDegrees(FMath::Atan2(B.Y - A.Y, Dx));
		const FVector2D Mid = (A + B) * 0.5f;
		const FVector2D Normal(-FMath::Sin(FMath::DegreesToRadians(Pitch)), FMath::Cos(FMath::DegreesToRadians(Pitch)));
		const FVector2D Center = Mid - Normal * (Thick * 0.5f);
		// A little longer than the segment, so neighbouring slabs leave no crack at the kinks.
		AddBlock(CubeMesh, FVector(Center.X, LaneY, Center.Y) * CmPerM, FRotator(Pitch, 0.0f, 0.0f), FVector(Length + 0.4f, WidthM, Thick) * CmPerM, Colour);
	}
}

void AEXPhysicsSandbox::AddBlock(UStaticMesh* Mesh, const FVector& CenterCm, const FRotator& Rotation, const FVector& SizeCm, const FLinearColor& Colour,
	bool bGrid)
{
	UStaticMeshComponent* Block = NewObject<UStaticMeshComponent>(this);
	Block->SetMobility(EComponentMobility::Movable);
	Block->SetStaticMesh(Mesh);
	Block->SetRelativeTransform(FTransform(Rotation, CenterCm, SizeCm / 100.0f));
	Block->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	if (bGrid && GridMaterial)
	{
		Block->SetMaterial(0, GridMaterial);
	}
	else if (ColorMaterial)
	{
		TObjectPtr<UMaterialInstanceDynamic>& Material = ColorMaterials.FindOrAdd(Colour.ToString());
		if (!Material)
		{
			Material = UMaterialInstanceDynamic::Create(ColorMaterial, this);
			Material->SetVectorParameterValue(TEXT("Color"), Colour);
		}
		Block->SetMaterial(0, Material);
	}
	Block->SetupAttachment(GetRootComponent());
	Block->RegisterComponent();
}

void AEXPhysicsSandbox::Populate()
{
	AEXHoverCraft* Player = Cast<AEXHoverCraft>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!Player || Route.Num() < 10)
	{
		return;
	}
	bPopulated = true;
	const FVector O = Origin();
	// The player at the start of the features' straight; damage on (race rules), no race.
	Player->SetRaceRules();
	Player->SetRoute(Route);
	Player->PlaceAt(O + FVector(10.0f, LaneAY, 3.0f) * CmPerM, 0.0f);
	Crafts.Add(Player);
	DeadFor.Add(0.0f);
	// The pack, spread along the second straight in lanes, a little slower than the player can go.
	for (int32 Bot = 0; Bot < BotCount; ++Bot)
	{
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		const float Lane = ((Bot % 3) - 1) * 9.0f;
		const FVector At = O + FVector(StraightM - 150.0f - (Bot / 3) * 35.0f, LaneBY - Lane, 3.0f) * CmPerM;
		AEXHoverCraft* Craft = GetWorld()->SpawnActor<AEXHoverCraft>(AEXHoverCraft::StaticClass(), At, FRotator(0.0f, 180.0f, 0.0f), Params);
		if (!Craft)
		{
			continue;
		}
		Craft->SetRaceRules();
		Craft->SetBot(Bot % 5, BotSkills[Bot], Lane);
		Craft->SetRoute(Route);
		Craft->PlaceAt(At, 180.0f);
		Crafts.Add(Craft);
		DeadFor.Add(0.0f);
	}
	UE_LOG(LogTemp, Display, TEXT("EXPHYS sandbox: %d crafts, loop %.1f km"), Crafts.Num(), Route.Num() * 5.0f / 1000.0f);
}

void AEXPhysicsSandbox::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bPopulated)
	{
		Populate();
		return;
	}
	const FVector O = Origin();
	for (int32 Index = 0; Index < Crafts.Num(); ++Index)
	{
		AEXHoverCraft* Craft = Crafts[Index];
		if (!IsValid(Craft))
		{
			continue;
		}
		// Endless running: fuel and heat stay full; a blown-up ship comes back in 3 s, a fall off the edge at once.
		Craft->Fuel = 100.0f;
		Craft->Heat = 0.0f;
		if (Craft->bEliminated)
		{
			DeadFor[Index] += DeltaSeconds;
			if (DeadFor[Index] > 3.0f)
			{
				DeadFor[Index] = 0.0f;
				Craft->Revive();
			}
			continue;
		}
		if (Craft->GetActorLocation().Z < O.Z - 4000.0f)
		{
			Craft->RespawnOnRoute();
		}
	}
	// The readout for the player: hull, speed, height, the air and the upset of a knock (the full numbers are in the log).
	if (GEngine && Crafts.Num() > 0 && IsValid(Crafts[0]))
	{
		const AEXHoverCraft* Me = Crafts[0];
		GEngine->AddOnScreenDebugMessage(7301, 0.0f, FColor(150, 225, 255), FString::Printf(
			TEXT("SANDBOX DA FÍSICA  ·  casco %.0f%%  ·  %.0f km/h  ·  altura %.1f m  ·  %s  ·  no ar %.1f s  ·  abanão %.0f%%  ·  rotação %.1f rad/s"),
			100.0f * Me->Hull / FMath::Max(1.0f, Me->HullMax), Me->ForwardSpeedMps * 3.6f, Me->HeightM, Me->bGrounded ? TEXT("no chão") : TEXT("no ar"),
			Me->AirTimeSeconds, 100.0f * Me->CrashWobble, Me->CrashSpin));
	}
}
