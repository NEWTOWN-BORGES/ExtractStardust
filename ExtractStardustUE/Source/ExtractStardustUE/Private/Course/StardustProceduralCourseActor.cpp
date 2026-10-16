#include "Course/StardustProceduralCourseActor.h"

#include "Course/StardustCourseData.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "ProceduralMeshComponent.h"

namespace
{
	constexpr int32 MaxSectionVertices = 60000;
	constexpr double CmPerMeter = 100.0;
}

AStardustProceduralCourseActor::AStardustProceduralCourseActor()
{
	PrimaryActorTick.bCanEverTick = false;
	CourseMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("CourseMesh"));
	SetRootComponent(CourseMesh);
	CourseMesh->SetCollisionProfileName(TEXT("BlockAll"));
	CourseMesh->SetCollisionResponseToChannel(ECC_GameTraceChannel1, ECR_Block);
	CourseMesh->bUseComplexAsSimpleCollision = true;
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

	const int32 StationsPerSection = FMath::Max(2, MaxSectionVertices / RingCount);
	int32 SectionIndex = 0;
	for (int32 FirstStation = 0; FirstStation < Stations.Num() - 1;)
	{
		const int32 SegmentCount = FMath::Min(StationsPerSection - 1, Stations.Num() - 1 - FirstStation);
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
			const int32 StationIndex = FirstStation + LocalStation;
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

		CourseMesh->CreateMeshSection_LinearColor(SectionIndex, Vertices, Triangles, {}, UVs, Colors, Tangents, bCreateCollision);
		if (CourseMaterial)
		{
			CourseMesh->SetMaterial(SectionIndex, CourseMaterial);
		}
		++SectionIndex;
		FirstStation += SegmentCount;
	}

	CourseMesh->SetCollisionEnabled(bCreateCollision ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
	OutError.Reset();
	return true;
}
