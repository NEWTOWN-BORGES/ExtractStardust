#include "EXDesertBuilder.h"

#include "Async/ParallelFor.h"
#include "FileHelpers.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/Engine.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/PlayerStart.h"
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "Materials/MaterialInterface.h"
#include "Misc/PackageName.h"
#include "RenderingThread.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "World/EXDesertTerrain.h"

namespace
{
	constexpr float CmPerM = 100.0f;
	/** Landscape Z scale 100 maps one height unit to 1/128 m, giving a range of +/-256 m around zero. */
	constexpr float HeightUnitsPerM = 128.0f;
}

bool UEXDesertBuilder::BuildDesertMap()
{
	UWorld* World = UEditorLoadingAndSavingUtils::NewBlankMap(false);
	if (!World)
	{
		UE_LOG(LogTemp, Error, TEXT("EXBUILD could not create a blank map"));
		return false;
	}

	// Height field from the shared terrain description.
	const int32 Size = FEXDesertTerrain::Resolution;
	const float HalfSize = FEXDesertTerrain::HalfSizeM;
	TArray<uint16> Heights;
	Heights.SetNumUninitialized(Size * Size);
	float MinHeight = TNumericLimits<float>::Max();
	float MaxHeight = TNumericLimits<float>::Lowest();
	FCriticalSection RangeLock;
	ParallelFor(Size, [&](int32 Row)
	{
		const float Y = -HalfSize + Row * FEXDesertTerrain::SpacingM;
		float RowMin = TNumericLimits<float>::Max();
		float RowMax = TNumericLimits<float>::Lowest();
		for (int32 Column = 0; Column < Size; ++Column)
		{
			const float Height = FEXDesertTerrain::HeightAt(-HalfSize + Column * FEXDesertTerrain::SpacingM, Y);
			RowMin = FMath::Min(RowMin, Height);
			RowMax = FMath::Max(RowMax, Height);
			Heights[Row * Size + Column] = static_cast<uint16>(FMath::Clamp(FMath::RoundToInt(32768.0f + Height * HeightUnitsPerM), 0, 65535));
		}
		FScopeLock Lock(&RangeLock);
		MinHeight = FMath::Min(MinHeight, RowMin);
		MaxHeight = FMath::Max(MaxHeight, RowMax);
	});
	UE_LOG(LogTemp, Display, TEXT("EXBUILD heights %d x %d, range %.1f m .. %.1f m"), Size, Size, MinHeight, MaxHeight);

	ALandscape* Landscape = World->SpawnActor<ALandscape>(FVector(-HalfSize * CmPerM, -HalfSize * CmPerM, 0.0f), FRotator::ZeroRotator);
	Landscape->SetActorRelativeScale3D(FVector(FEXDesertTerrain::SpacingM * CmPerM, FEXDesertTerrain::SpacingM * CmPerM, 100.0f));
	Landscape->LandscapeMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Desert/M_Desert.M_Desert"));
	UE_LOG(LogTemp, Display, TEXT("EXBUILD landscape material: %s"), *GetNameSafe(Landscape->LandscapeMaterial));
	TMap<FGuid, TArray<uint16>> HeightData;
	HeightData.Add(FGuid(), MoveTemp(Heights));
	TMap<FGuid, TArray<FLandscapeImportLayerInfo>> LayerData;
	LayerData.Add(FGuid(), TArray<FLandscapeImportLayerInfo>());
	Landscape->Import(FGuid::NewGuid(), 0, 0, Size - 1, Size - 1, 2, 63, HeightData, TEXT(""), LayerData,
		ELandscapeImportAlphamapType::Additive, TArrayView<const FLandscapeLayer>());
	if (ULandscapeInfo* Info = Landscape->GetLandscapeInfo())
	{
		Info->UpdateLayerInfoMap(Landscape);
	}
	Landscape->ForceLayersFullUpdate();
	FlushRenderingCommands();

	// Sun, sky and dusty air. Movable lighting only: the project has no baked lighting.
	ADirectionalLight* Sun = World->SpawnActor<ADirectionalLight>(FVector(0.0f, 0.0f, 50000.0f), FRotator(-38.0f, -35.0f, 0.0f));
	if (UDirectionalLightComponent* SunLight = Cast<UDirectionalLightComponent>(Sun->GetLightComponent()))
	{
		SunLight->SetMobility(EComponentMobility::Movable);
		SunLight->SetIntensity(10.0f);
		SunLight->SetLightColor(FLinearColor(1.0f, 0.93f, 0.84f));
		SunLight->SetAtmosphereSunLight(true);
		SunLight->SetDynamicShadowDistanceMovableLight(25000.0f);
	}
	World->SpawnActor<ASkyAtmosphere>(FVector::ZeroVector, FRotator::ZeroRotator);
	ASkyLight* Sky = World->SpawnActor<ASkyLight>(FVector(0.0f, 0.0f, 20000.0f), FRotator::ZeroRotator);
	if (USkyLightComponent* SkyLight = Sky->GetLightComponent())
	{
		SkyLight->SetMobility(EComponentMobility::Movable);
		SkyLight->SetRealTimeCapture(true);
		SkyLight->SetIntensity(1.0f);
	}
	AExponentialHeightFog* Fog = World->SpawnActor<AExponentialHeightFog>(FVector(0.0f, 0.0f, 0.0f), FRotator::ZeroRotator);
	if (UExponentialHeightFogComponent* FogComponent = Fog->GetComponent())
	{
		FogComponent->SetFogDensity(0.012f);
		FogComponent->SetFogHeightFalloff(0.12f);
		FogComponent->SetFogInscatteringColor(FLinearColor(0.62f, 0.47f, 0.36f));
		FogComponent->SetDirectionalInscatteringColor(FLinearColor(1.0f, 0.72f, 0.48f));
		FogComponent->SetStartDistance(4000.0f);
	}
	APostProcessVolume* Post = World->SpawnActor<APostProcessVolume>(FVector::ZeroVector, FRotator::ZeroRotator);
	Post->bUnbound = true;
	Post->Settings.bOverride_BloomIntensity = true;
	Post->Settings.BloomIntensity = 0.45f;
	Post->Settings.bOverride_VignetteIntensity = true;
	Post->Settings.VignetteIntensity = 0.3f;
	Post->Settings.bOverride_WhiteTemp = true;
	Post->Settings.WhiteTemp = 6100.0f;

	// Race start, tagged so the game mode knows this map brings its own world.
	const FVector2D Start = FEXDesertTerrain::StartPoint();
	APlayerStart* PlayerStart = World->SpawnActor<APlayerStart>(
		FVector(Start.X * CmPerM, Start.Y * CmPerM, (FEXDesertTerrain::HeightAt(Start.X, Start.Y) + 3.0f) * CmPerM),
		FRotator(0.0f, FEXDesertTerrain::StartYawDeg(), 0.0f));
	PlayerStart->Tags.Add(TEXT("EXWorld"));

	// Invisible walls just inside the landscape edge: the raised rim is the visible border, these make it absolute.
	if (UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")))
	{
		const float Inner = (HalfSize - 10.0f) * CmPerM;
		const float Length = (HalfSize * 2.0f + 40.0f) * CmPerM;
		const FVector Centers[] = { FVector(Inner, 0, 0), FVector(-Inner, 0, 0), FVector(0, Inner, 0), FVector(0, -Inner, 0) };
		for (int32 Index = 0; Index < 4; ++Index)
		{
			const bool bAlongY = Index < 2;
			AStaticMeshActor* Wall = World->SpawnActor<AStaticMeshActor>(Centers[Index] + FVector(0.0f, 0.0f, 20000.0f), FRotator::ZeroRotator);
			Wall->GetStaticMeshComponent()->SetStaticMesh(Cube);
			Wall->SetActorScale3D(bAlongY ? FVector(10.0f, Length / 100.0f, 600.0f) : FVector(Length / 100.0f, 10.0f, 600.0f));
			Wall->SetActorHiddenInGame(true);
		}
	}

	const bool bSaved = UEditorLoadingAndSavingUtils::SaveMap(World, TEXT("/Game/Maps/DesertCanyon"));
	UE_LOG(LogTemp, Display, TEXT("EXBUILD saved /Game/Maps/DesertCanyon: %s"), bSaved ? TEXT("OK") : TEXT("FAILED"));
	return bSaved;
}
