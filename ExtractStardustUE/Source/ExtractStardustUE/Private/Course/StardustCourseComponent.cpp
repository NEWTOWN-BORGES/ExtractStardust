#include "Course/StardustCourseComponent.h"

#include "HAL/PlatformFileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

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
}

bool UStardustCourseComponent::LoadCourse(FString& OutError)
{
	CourseLengthM = 0.0f;
	StationCount = 0;
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

bool UStardustCourseComponent::SampleAtDistance(float DistanceM, FStardustCoursePoint& OutPoint) const
{
	FStardustCourseSample Sample;
	if (!CourseData.SampleAtDistance(DistanceM, Sample))
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
	FStardustCourseSample Sample;
	if (!CourseData.SampleAtDistance(DistanceM, Sample) || Sample.RingOffsetsM.Num() < 2)
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

float UStardustCourseComponent::GetDistanceAtStation(int32 StationIndex) const
{
	const TArray<FStardustCourseStation>& Stations = CourseData.GetStations();
	return Stations.IsValidIndex(StationIndex) ? Stations[StationIndex].DistanceM : -1.0f;
}
