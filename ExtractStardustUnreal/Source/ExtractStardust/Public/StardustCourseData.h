#pragma once

#include "CoreMinimal.h"
#include "Serialization/MemoryReader.h"
#include "UObject/Object.h"
#include "StardustCourseData.generated.h"

USTRUCT(BlueprintType)
struct FStardustCourseStation
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category="Course") float Distance = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course") FVector Center = FVector::ZeroVector;
	UPROPERTY(BlueprintReadOnly, Category="Course") FVector Tangent = FVector::ForwardVector;
	UPROPERTY(BlueprintReadOnly, Category="Course") FVector Right = FVector::RightVector;
	UPROPERTY(BlueprintReadOnly, Category="Course") FVector Up = FVector::UpVector;
	UPROPERTY(BlueprintReadOnly, Category="Course") float Width = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course") float Bank = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course") float Slope = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course") int32 Flags = 0;
	UPROPERTY(BlueprintReadOnly, Category="Course") int32 Segment = 0;
	UPROPERTY(BlueprintReadOnly, Category="Course") int32 Surface = 0;
	UPROPERTY(BlueprintReadOnly, Category="Course") float RideLeft = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course") float RideRight = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course") TArray<FVector> Ring;
	UPROPERTY(BlueprintReadOnly, Category="Course") TArray<float> RingArc;
};

USTRUCT(BlueprintType)
struct FStardustCourseFrame
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category="Course") FVector Position = FVector::ZeroVector;
	UPROPERTY(BlueprintReadOnly, Category="Course") FVector Tangent = FVector::ForwardVector;
	UPROPERTY(BlueprintReadOnly, Category="Course") FVector Right = FVector::RightVector;
	UPROPERTY(BlueprintReadOnly, Category="Course") FVector Up = FVector::UpVector;
	UPROPERTY(BlueprintReadOnly, Category="Course") int32 StationIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category="Course") float Alpha = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course") float Distance = 0.0f;
};
UCLASS(BlueprintType)
class EXTRACTSTARDUST_API UStardustCourseData : public UObject
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Course")
	static UStardustCourseData* ParseRDDC(const TArray<uint8>& Bytes, FString& Error);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Course")
	static UStardustCourseData* LoadRDDCFile(const FString& FilePath, FString& Error);

	static UStardustCourseData* ParseBody(FMemoryReader& Reader, int32 StationCount, int32 RingCount, float Step, FString& Error);

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	float GetStart() const { return Stations.IsEmpty() ? 0.0f : Stations[0].Distance; }

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	float GetLength() const { return Stations.IsEmpty() ? 0.0f : Stations.Last().Distance; }

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	int32 GetStationCount() const { return Stations.Num(); }

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	int32 GetRingCount() const { return RingCount; }
	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	bool ContainsPoint(const FVector& Position) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	int32 FindNearestStation(const FVector& Position, int32 Hint = -1, int32 Window = 160) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	float DistanceAlong(const FVector& Position, int32 StationIndex) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	float OutsideRide(const FVector& Position, int32 StationIndex) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	float LateralU(const FVector& Position, int32 StationIndex) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	FVector LanePointAtStation(int32 StationIndex, float U) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	FVector LanePointAtDistance(float Distance, float U) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	FVector LaneNormal(int32 StationIndex, float U) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	FStardustCourseFrame FrameAtDistance(float Distance) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	float CurvatureAhead(float Distance, float Span) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	float SurfaceAngle(int32 StationIndex, float U) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	float LaneForAngle(int32 StationIndex, float Degrees, int32 Side) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	bool IsGap(int32 StationIndex) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	bool IsCave(int32 StationIndex) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	FName GetSegmentName(int32 StationIndex) const;

	const FStardustCourseStation* GetStation(int32 StationIndex) const { return Stations.IsValidIndex(StationIndex) ? &Stations[StationIndex] : nullptr; }
	int32 FindStationAtDistance(float Distance) const;
	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	int32 StationAtDistance(float Distance) const;

	UPROPERTY(BlueprintReadOnly, Category="Course")
	TArray<FStardustCourseStation> Stations;

	UPROPERTY(BlueprintReadOnly, Category="Course")
	TArray<FName> SegmentNames;

	UPROPERTY(BlueprintReadOnly, Category="Course")
	float SampleStep = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category="Course")
	int32 RingCount = 0;
	FBox CourseBounds;
};