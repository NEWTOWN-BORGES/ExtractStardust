#include "Course/StardustCourseComponent.h"

#include "HAL/PlatformFileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
	int32 FindNearestStationInData(const FStardustCourseData& CourseData, const FVector& PositionCm, int32 HintIndex, int32 SearchWindow)
	{
		const TArray<FStardustCourseStation>& Stations = CourseData.GetStations();
		if (Stations.IsEmpty())
		{
			return INDEX_NONE;
		}

		const FVector PositionM = PositionCm / 100.0;
		int32 BestIndex = INDEX_NONE;
		double BestDistanceSquared = TNumericLimits<double>::Max();
		if (HintIndex >= 0)
		{
			const int32 StartIndex = FMath::Max(0, HintIndex - FMath::Max(0, SearchWindow));
			const int32 EndIndex = FMath::Min(Stations.Num() - 1, HintIndex + FMath::Max(0, SearchWindow));
			for (int32 Index = StartIndex; Index <= EndIndex; ++Index)
			{
				const double DistanceSquared = FVector::DistSquared(Stations[Index].CenterM, PositionM);
				if (DistanceSquared < BestDistanceSquared)
				{
					BestDistanceSquared = DistanceSquared;
					BestIndex = Index;
				}
			}
			if (BestDistanceSquared < FMath::Square(120.0))
			{
				return BestIndex;
			}
		}

		BestDistanceSquared = TNumericLimits<double>::Max();
		for (int32 Index = 0; Index < Stations.Num(); Index += 4)
		{
			const double DistanceSquared = FVector::DistSquared(Stations[Index].CenterM, PositionM);
			if (DistanceSquared < BestDistanceSquared)
			{
				BestDistanceSquared = DistanceSquared;
				BestIndex = Index;
			}
		}
		const int32 RefineStart = FMath::Max(0, BestIndex - 4);
		const int32 RefineEnd = FMath::Min(Stations.Num() - 1, BestIndex + 4);
		for (int32 Index = RefineStart; Index <= RefineEnd; ++Index)
		{
			const double DistanceSquared = FVector::DistSquared(Stations[Index].CenterM, PositionM);
			if (DistanceSquared < BestDistanceSquared)
			{
				BestDistanceSquared = DistanceSquared;
				BestIndex = Index;
			}
		}
		return BestIndex;
	}

	double FindSurfaceDistance(const FStardustCourseData& CourseData, const FVector& PositionM, int32 StationIndex)
	{
		const TArray<FStardustCourseStation>& Stations = CourseData.GetStations();
		const int32 RingCount = CourseData.GetRingCount();
		double BestDistanceSquared = TNumericLimits<double>::Max();
		for (int32 Index = FMath::Max(0, StationIndex - 1); Index <= FMath::Min(Stations.Num() - 1, StationIndex + 1); ++Index)
		{
			for (int32 RingIndex = 0; RingIndex < RingCount; RingIndex += 2)
			{
				BestDistanceSquared = FMath::Min(BestDistanceSquared,
					FVector::DistSquared(Stations[Index].RingOffsetsM[RingIndex], PositionM));
			}
		}
		return FMath::Sqrt(BestDistanceSquared);
	}
}

UStardustCourseComponent::UStardustCourseComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UStardustCourseComponent::BeginPlay()
{
	Super::BeginPlay();
	FString Error;
	if (!LoadCourse(Error) && !CourseFileName.IsEmpty())
	{
		UE_LOG(LogTemp, Warning, TEXT("Course '%s' was not loaded: %s"), *CourseFileName, *Error);
	}
	const FString GraphPath = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Tracks"), CourseGraphFileName);
	if (!CourseGraphFileName.IsEmpty() && FPaths::FileExists(GraphPath) && !LoadCourseGraph(Error))
	{
		UE_LOG(LogTemp, Warning, TEXT("Course graph '%s' was not loaded: %s"), *CourseGraphFileName, *Error);
	}
}

bool UStardustCourseComponent::LoadCourse(FString& OutError)
{
	CourseLengthM = 0.0f;
	StationCount = 0;
	BranchCount = 0;
	CourseData.Reset();
	CourseGraph.Reset();
	if (CourseFileName.IsEmpty())
	{
		OutError = TEXT("Course file name is empty.");
		return false;
	}

	const FString CoursePath = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Tracks"), CourseFileName);
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *CoursePath))
	{
		OutError = FString::Printf(TEXT("Could not read '%s'. Place the generated RDDC file in Content/Tracks."), *CoursePath);
		return false;
	}
	if (!CourseData.Load(Bytes, OutError))
	{
		return false;
	}

	const TArray<FStardustCourseStation>& Stations = CourseData.GetStations();
	CourseLengthM = Stations.Last().DistanceM;
	StationCount = Stations.Num();
	return true;
}

bool UStardustCourseComponent::LoadCourseGraph(FString& OutError)
{
	BranchCount = 0;
	CourseGraph.Reset();
	if (CourseGraphFileName.IsEmpty())
	{
		OutError = TEXT("Course graph file name is empty.");
		return false;
	}

	const FString GraphPath = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Tracks"), CourseGraphFileName);
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *GraphPath))
	{
		OutError = FString::Printf(TEXT("Could not read '%s'. Place the generated RDDG file in Content/Tracks."), *GraphPath);
		return false;
	}
	if (!CourseGraph.Load(Bytes, OutError))
	{
		return false;
	}
	BranchCount = CourseGraph.GetBranchCount();
	return true;
}

const FStardustCourseData* UStardustCourseComponent::GetCourseDataForPath(int32 PathIndex) const
{
	const TArray<FStardustCoursePath>& Paths = CourseGraph.GetPaths();
	if (Paths.IsValidIndex(PathIndex))
	{
		return &Paths[PathIndex].Data;
	}
	return PathIndex == 0 && StationCount > 0 ? &CourseData : nullptr;
}

bool UStardustCourseComponent::SampleAtDistance(float DistanceM, FStardustCoursePoint& OutPoint) const
{
	return SamplePathAtDistance(0, DistanceM, OutPoint);
}

bool UStardustCourseComponent::SamplePathAtDistance(int32 PathIndex, float DistanceM, FStardustCoursePoint& OutPoint) const
{
	FStardustCourseSample Sample;
	const FStardustCourseData* PathData = GetCourseDataForPath(PathIndex);
	if (!PathData || !PathData->SampleAtDistance(DistanceM, Sample))
	{
		return false;
	}

	OutPoint.DistanceM = Sample.DistanceM;
	OutPoint.PositionCm = Sample.CenterM * 100.0;
	OutPoint.Tangent = Sample.Tangent;
	OutPoint.Right = Sample.Right;
	OutPoint.Up = Sample.Up;
	OutPoint.WidthM = Sample.WidthM;
	OutPoint.BankDegrees = Sample.BankDegrees;
	OutPoint.Slope = Sample.Slope;
	OutPoint.Flags = Sample.Flags;
	OutPoint.SegmentIndex = Sample.SegmentIndex;
	OutPoint.SurfaceIndex = Sample.SurfaceIndex;
	OutPoint.RideLeftM = Sample.RideLeftM;
	OutPoint.RideRightM = Sample.RideRightM;
	return true;
}

bool UStardustCourseComponent::LanePointAtDistance(float DistanceM, float LaneU, FVector& OutPositionCm) const
{
	return LanePointAtPathDistance(0, DistanceM, LaneU, OutPositionCm);
}

bool UStardustCourseComponent::LanePointAtPathDistance(int32 PathIndex, float DistanceM, float LaneU, FVector& OutPositionCm) const
{
	FStardustCourseSample Sample;
	const FStardustCourseData* PathData = GetCourseDataForPath(PathIndex);
	if (!PathData || !PathData->SampleAtDistance(DistanceM, Sample) || Sample.RingOffsetsM.Num() < 2)
	{
		return false;
	}

	const int32 RingCount = Sample.RingOffsetsM.Num();
	const int32 CenterIndex = RingCount / 2;
	TArray<float> RingArcM;
	RingArcM.SetNumZeroed(RingCount);
	for (int32 RingIndex = CenterIndex + 1; RingIndex < RingCount; ++RingIndex)
	{
		RingArcM[RingIndex] = RingArcM[RingIndex - 1] + FVector::Distance(Sample.RingOffsetsM[RingIndex], Sample.RingOffsetsM[RingIndex - 1]);
	}
	for (int32 RingIndex = CenterIndex - 1; RingIndex >= 0; --RingIndex)
	{
		RingArcM[RingIndex] = RingArcM[RingIndex + 1] - FVector::Distance(Sample.RingOffsetsM[RingIndex], Sample.RingOffsetsM[RingIndex + 1]);
	}

	const float LaneArcM = LaneU < 0.0f ? LaneU * Sample.RideLeftM : LaneU * Sample.RideRightM;
	int32 LowerIndex = 0;
	int32 UpperIndex = RingCount - 1;
	if (LaneArcM <= RingArcM[LowerIndex])
	{
		OutPositionCm = Sample.RingOffsetsM[LowerIndex] * 100.0;
		return true;
	}
	if (LaneArcM >= RingArcM[UpperIndex])
	{
		OutPositionCm = Sample.RingOffsetsM[UpperIndex] * 100.0;
		return true;
	}
	while (LowerIndex + 1 < UpperIndex)
	{
		const int32 MiddleIndex = (LowerIndex + UpperIndex) / 2;
		if (RingArcM[MiddleIndex] <= LaneArcM)
		{
			LowerIndex = MiddleIndex;
		}
		else
		{
			UpperIndex = MiddleIndex;
		}
	}
	const float SegmentLengthM = RingArcM[UpperIndex] - RingArcM[LowerIndex];
	const float Alpha = SegmentLengthM > UE_SMALL_NUMBER ? (LaneArcM - RingArcM[LowerIndex]) / SegmentLengthM : 0.0f;
	OutPositionCm = FMath::Lerp(Sample.RingOffsetsM[LowerIndex], Sample.RingOffsetsM[UpperIndex], Alpha) * 100.0;
	return true;
}

int32 UStardustCourseComponent::FindNearestStation(const FVector& PositionCm, int32 HintIndex, int32 SearchWindow) const
{
	return FindNearestStationInData(CourseData, PositionCm, HintIndex, SearchWindow);
}

float UStardustCourseComponent::GetDistanceAtStation(int32 StationIndex) const
{
	return GetDistanceAtPathStation(0, StationIndex);
}

int32 UStardustCourseComponent::GetCoursePathCount() const
{
	return CourseGraph.GetPaths().IsEmpty() ? (StationCount > 0 ? 1 : 0) : CourseGraph.GetPaths().Num();
}

FString UStardustCourseComponent::GetCoursePathName(int32 PathIndex) const
{
	const TArray<FStardustCoursePath>& Paths = CourseGraph.GetPaths();
	if (Paths.IsValidIndex(PathIndex))
	{
		return Paths[PathIndex].Id;
	}
	return PathIndex == 0 && StationCount > 0 ? TEXT("main") : FString();
}

float UStardustCourseComponent::GetRaceDistanceAtStation(int32 PathIndex, int32 StationIndex) const
{
	const float PathDistanceM = GetDistanceAtPathStation(PathIndex, StationIndex);
	return PathDistanceM >= 0.0f ? MapPathDistanceToRaceDistance(PathIndex, PathDistanceM) : -1.0f;
}

float UStardustCourseComponent::GetCoursePathLengthM(int32 PathIndex) const
{
	const FStardustCourseData* PathData = GetCourseDataForPath(PathIndex);
	if (!PathData)
	{
		return -1.0f;
	}
	const TArray<FStardustCourseStation>& Stations = PathData->GetStations();
	return Stations.Num() > 0 ? Stations.Last().DistanceM : -1.0f;
}

float UStardustCourseComponent::GetDistanceAtPathStation(int32 PathIndex, int32 StationIndex) const
{
	const FStardustCourseData* PathData = GetCourseDataForPath(PathIndex);
	if (!PathData)
	{
		return -1.0f;
	}
	const TArray<FStardustCourseStation>& Stations = PathData->GetStations();
	return Stations.IsValidIndex(StationIndex) ? Stations[StationIndex].DistanceM : -1.0f;
}

float UStardustCourseComponent::GetCoursePathEntryDistanceM(int32 PathIndex) const
{
	const TArray<FStardustCoursePath>& Paths = CourseGraph.GetPaths();
	if (Paths.IsValidIndex(PathIndex))
	{
		return Paths[PathIndex].FromM;
	}
	return PathIndex == 0 && StationCount > 0 ? 0.0f : -1.0f;
}

float UStardustCourseComponent::GetCoursePathExitDistanceM(int32 PathIndex) const
{
	const TArray<FStardustCoursePath>& Paths = CourseGraph.GetPaths();
	if (Paths.IsValidIndex(PathIndex))
	{
		return Paths[PathIndex].ToM;
	}
	return PathIndex == 0 ? CourseLengthM : -1.0f;
}

float UStardustCourseComponent::MapPathDistanceToRaceDistance(int32 PathIndex, float DistanceM) const
{
	const TArray<FStardustCoursePath>& Paths = CourseGraph.GetPaths();
	if (Paths.IsValidIndex(PathIndex))
	{
		return Paths[PathIndex].ToRaceDistance(DistanceM);
	}
	return PathIndex == 0 ? DistanceM : -1.0f;
}

float UStardustCourseComponent::MapRaceDistanceToPathDistance(int32 PathIndex, float RaceDistanceM) const
{
	const TArray<FStardustCoursePath>& Paths = CourseGraph.GetPaths();
	if (!Paths.IsValidIndex(PathIndex))
	{
		return PathIndex == 0 ? RaceDistanceM : -1.0f;
	}
	const FStardustCoursePath& Path = Paths[PathIndex];
	if (Path.IsMain())
	{
		return RaceDistanceM;
	}
	const TArray<FStardustCourseStation>& Stations = Path.Data.GetStations();
	if (Stations.Num() < 2 || Path.ToM <= Path.FromM)
	{
		return -1.0f;
	}
	const float Alpha = FMath::Clamp((RaceDistanceM - Path.FromM) / (Path.ToM - Path.FromM), 0.0f, 1.0f);
	return FMath::Lerp(Stations[0].DistanceM, Stations.Last().DistanceM, Alpha);
}

bool UStardustCourseComponent::LocateCoursePath(const FVector& PositionCm, int32 HintPathIndex, int32 HintStationIndex,
	int32& OutPathIndex, int32& OutStationIndex, float HysteresisM) const
{
	const TArray<FStardustCoursePath>& Paths = CourseGraph.GetPaths();
	OutPathIndex = INDEX_NONE;
	OutStationIndex = INDEX_NONE;
	if (Paths.IsEmpty())
	{
		OutStationIndex = FindNearestStation(PositionCm, HintPathIndex == 0 ? HintStationIndex : INDEX_NONE, 160);
		OutPathIndex = OutStationIndex == INDEX_NONE ? INDEX_NONE : 0;
		return OutPathIndex != INDEX_NONE;
	}

	const FVector PositionM = PositionCm / 100.0;
	const int32 CurrentPathIndex = FMath::Clamp(HintPathIndex, 0, Paths.Num() - 1);
	const FStardustCourseData& CurrentData = Paths[CurrentPathIndex].Data;
	int32 CurrentStationIndex = FindNearestStationInData(CurrentData, PositionCm,
		CurrentPathIndex == HintPathIndex ? HintStationIndex : INDEX_NONE, 160);
	if (CurrentStationIndex == INDEX_NONE)
	{
		return false;
	}

	OutPathIndex = CurrentPathIndex;
	OutStationIndex = CurrentStationIndex;
	double BestDistanceM = FindSurfaceDistance(CurrentData, PositionM, CurrentStationIndex) - FMath::Max(0.0f, HysteresisM);
	for (int32 PathIndex = 0; PathIndex < Paths.Num(); ++PathIndex)
	{
		if (PathIndex == CurrentPathIndex)
		{
			continue;
		}
		const FStardustCourseData& CandidateData = Paths[PathIndex].Data;
		const int32 CandidateStationIndex = FindNearestStationInData(CandidateData, PositionCm, INDEX_NONE, 160);
		if (CandidateStationIndex == INDEX_NONE)
		{
			continue;
		}
		const double CandidateDistanceM = FindSurfaceDistance(CandidateData, PositionM, CandidateStationIndex);
		if (CandidateDistanceM < BestDistanceM)
		{
			BestDistanceM = CandidateDistanceM;
			OutPathIndex = PathIndex;
			OutStationIndex = CandidateStationIndex;
		}
	}
	return true;
}
