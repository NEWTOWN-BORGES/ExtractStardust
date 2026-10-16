#include "Course/StardustProceduralCourseActor.h"

#include "Course/StardustCourseData.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "ProceduralMeshComponent.h"

namespace
{
	constexpr int32 MaxSectionVertices = 60000;
	constexpr double CmPerMeter = 100.0;
	constexpr float CollisionSampleSpacingM = 20.0f;
}

AStardustProceduralCourseActor::AStardustProceduralCourseActor()
{
	PrimaryActorTick.bCanEverTick = false;
	CourseMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("CourseMesh"));
	SetRootComponent(CourseMesh);
	CourseMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	CollisionMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("CollisionMesh"));
	CollisionMesh->SetupAttachment(CourseMesh);
	CollisionMesh->SetVisibility(false, true);
	CollisionMesh->SetHiddenInGame(true, true);
	CollisionMesh->SetCollisionProfileName(TEXT("BlockAll"));
	CollisionMesh->SetCollisionResponseToChannel(ECC_GameTraceChannel1, ECR_Block);
	CollisionMesh->bUseComplexAsSimpleCollision = true;
}

void AStardustProceduralCourseActor::BeginPlay()
{
	Super::BeginPlay();
	FString Error;
	if (!LoadAndBuildCourse(Error))
	{
		UE_LOG(LogTemp, Warning, TEXT("Procedural course '%s' was not built: %s"), *CourseFileName, *Error);
	}
}

bool AStardustProceduralCourseActor::LoadAndBuildCourse(FString& OutError)
{
	const FString CoursePath = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Tracks"), CourseFileName);
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *CoursePath))
	{
		OutError = FString::Printf(TEXT("Could not read '%s'."), *CoursePath);
		return false;
	}

	FStardustCourseData CourseData;
	if (!CourseData.Load(Bytes, OutError))
	{
		return false;
	}
	const TArray<FStardustCourseStation>& Stations = CourseData.GetStations();
	const int32 RingCount = CourseData.GetRingCount();
	if (Stations.Num() < 2 || RingCount < 2)
	{
		OutError = TEXT("Course needs at least two stations and two ring vertices.");
		return false;
	}

	TArray<int32> VisualStationIndices;
	VisualStationIndices.Reserve(Stations.Num());
	for (int32 StationIndex = 0; StationIndex < Stations.Num(); ++StationIndex)
	{
		VisualStationIndices.Add(StationIndex);
	}
	TArray<int32> CollisionStationIndices;
	const int32 CollisionStationStride = FMath::Max(1, FMath::RoundToInt(CollisionSampleSpacingM / CourseData.GetStepM()));
	CollisionStationIndices.Reserve(FMath::DivideAndRoundUp(Stations.Num(), CollisionStationStride) + 1);
	for (int32 StationIndex = 0; StationIndex < Stations.Num(); StationIndex += CollisionStationStride)
	{
		CollisionStationIndices.Add(StationIndex);
	}
	if (CollisionStationIndices.Last() != Stations.Num() - 1)
	{
		CollisionStationIndices.Add(Stations.Num() - 1);
	}

	const int32 StationsPerSection = FMath::Max(2, MaxSectionVertices / RingCount);
	auto BuildSections = [&](UProceduralMeshComponent* Mesh, const TArray<int32>& StationIndices, bool bSectionCollision)
	{
		int32 SectionIndex = 0;
		for (int32 FirstStation = 0; FirstStation < StationIndices.Num() - 1;)
		{
			const int32 SegmentCount = FMath::Min(StationsPerSection - 1, StationIndices.Num() - 1 - FirstStation);
			const int32 SectionStationCount = SegmentCount + 1;
			TArray<FVector> Vertices;
			TArray<FVector2D> UVs;
			TArray<FLinearColor> Colors;
			TArray<FProcMeshTangent> Tangents;
			TArray<int32> Triangles;
			Vertices.Reserve(SectionStationCount * RingCount);
			UVs.Reserve(SectionStationCount * RingCount);
			Colors.Reserve(SectionStationCount * RingCount);
			Triangles.Reserve(SegmentCount * (RingCount - 1) * 6);

			for (int32 LocalStation = 0; LocalStation < SectionStationCount; ++LocalStation)
			{
				const int32 StationIndex = StationIndices[FirstStation + LocalStation];
				const FStardustCourseStation& Station = Stations[StationIndex];
				for (int32 RingIndex = 0; RingIndex < RingCount; ++RingIndex)
				{
					Vertices.Add(Station.RingOffsetsM[RingIndex] * CmPerMeter);
					UVs.Add(FVector2D(Station.DistanceM, static_cast<double>(RingIndex) / (RingCount - 1)));
					Colors.Add(FLinearColor::White);
				}
			}

			for (int32 LocalStation = 0; LocalStation < SegmentCount; ++LocalStation)
			{
				for (int32 RingIndex = 0; RingIndex < RingCount - 1; ++RingIndex)
				{
					const int32 A = LocalStation * RingCount + RingIndex;
					const int32 B = A + RingCount;
					const int32 D = A + 1;
					const int32 C = B + 1;
					Triangles.Append({ A, B, D, B, C, D });
				}
			}

			Mesh->CreateMeshSection_LinearColor(SectionIndex, Vertices, Triangles, {}, UVs, Colors, Tangents, bSectionCollision);
			if (Mesh == CourseMesh && CourseMaterial)
			{
				Mesh->SetMaterial(SectionIndex, CourseMaterial);
			}
			++SectionIndex;
			FirstStation += SegmentCount;
		}
		return SectionIndex;
	};

	const int32 VisualSectionCount = BuildSections(CourseMesh, VisualStationIndices, false);
	const int32 CollisionSectionCount = BuildSections(CollisionMesh, CollisionStationIndices, bCreateCollision);
	CollisionMesh->SetCollisionEnabled(bCreateCollision ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
	UE_LOG(LogTemp, Display, TEXT("Built procedural course '%s': %d stations, %d visual sections, %d collision sections at %.1f m."),
		*CourseFileName, Stations.Num(), VisualSectionCount, bCreateCollision ? CollisionSectionCount : 0,
		CourseData.GetStepM() * CollisionStationStride);
	OutError.Reset();
	return true;
}
