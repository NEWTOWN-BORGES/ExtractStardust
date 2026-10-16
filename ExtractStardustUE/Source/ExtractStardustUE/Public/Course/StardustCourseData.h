#pragma once

#include "CoreMinimal.h"

struct FStardustCourseStation
{
	float DistanceM = 0.0f;
	FVector CenterM = FVector::ZeroVector;
	FVector Tangent = FVector::ForwardVector;
	FVector Right = FVector::RightVector;
	FVector Up = FVector::UpVector;
	float WidthM = 0.0f;
	float BankDegrees = 0.0f;
	float Slope = 0.0f;
	int32 Flags = 0;
	int32 SegmentIndex = 0;
	int32 SurfaceIndex = 0;
	float RideLeftM = 0.0f;
	float RideRightM = 0.0f;
	TArray<FVector> RingOffsetsM;
};

struct FStardustCourseSample
{
	int32 StationIndex = INDEX_NONE;
	float Alpha = 0.0f;
	float DistanceM = 0.0f;
	FVector CenterM = FVector::ZeroVector;
	FVector Tangent = FVector::ForwardVector;
	FVector Right = FVector::RightVector;
	FVector Up = FVector::UpVector;
	float WidthM = 0.0f;
	float BankDegrees = 0.0f;
	float Slope = 0.0f;
	int32 Flags = 0;
	int32 SegmentIndex = 0;
	int32 SurfaceIndex = 0;
	float RideLeftM = 0.0f;
	float RideRightM = 0.0f;
	TArray<FVector> RingOffsetsM;
};

class FStardustCourseData
{
public:
	bool Load(const TArray<uint8>& Bytes, FString& OutError);
	bool SampleAtDistance(float DistanceM, FStardustCourseSample& OutSample) const;
	void Reset();

	const TArray<FStardustCourseStation>& GetStations() const { return Stations; }
	const TArray<FString>& GetSegmentNames() const { return SegmentNames; }
	float GetStepM() const { return StepM; }
	int32 GetRingCount() const { return RingCount; }

private:
	TArray<FStardustCourseStation> Stations;
	TArray<FString> SegmentNames;
	float StepM = 0.0f;
	int32 RingCount = 0;
};
