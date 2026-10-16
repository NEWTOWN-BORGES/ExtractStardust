#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Course/StardustCourseData.h"
#include "StardustCourseComponent.generated.h"

USTRUCT(BlueprintType)
struct FStardustCoursePoint
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	float DistanceM = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	FVector PositionCm = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	FVector Tangent = FVector::ForwardVector;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	FVector Right = FVector::RightVector;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	FVector Up = FVector::UpVector;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	float WidthM = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	float BankDegrees = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	float Slope = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	int32 Flags = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	int32 SegmentIndex = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	int32 SurfaceIndex = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	float RideLeftM = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	float RideRightM = 0.0f;
};

UCLASS(ClassGroup = (Stardust), meta = (BlueprintSpawnableComponent))
class EXTRACTSTARDUSTUE_API UStardustCourseComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UStardustCourseComponent();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Course")
	FString CourseFileName = TEXT("sandbox_course.bytes");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Course")
	FString CourseGraphFileName = TEXT("sandbox_graph.bytes");

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	float CourseLengthM = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	int32 StationCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Course")
	int32 BranchCount = 0;

	UFUNCTION(BlueprintCallable, Category = "Course")
	bool LoadCourse(FString& OutError);

	UFUNCTION(BlueprintCallable, Category = "Course")
	bool LoadCourseGraph(FString& OutError);

	UFUNCTION(BlueprintPure, Category = "Course")
	bool SampleAtDistance(float DistanceM, FStardustCoursePoint& OutPoint) const;

	UFUNCTION(BlueprintPure, Category = "Course")
	bool LanePointAtDistance(float DistanceM, float LaneU, FVector& OutPositionCm) const;

	UFUNCTION(BlueprintPure, Category = "Course")
	int32 FindNearestStation(const FVector& PositionCm, int32 HintIndex = -1, int32 SearchWindow = 160) const;

	UFUNCTION(BlueprintPure, Category = "Course")
	float GetDistanceAtStation(int32 StationIndex) const;

	UFUNCTION(BlueprintPure, Category = "Course")
	int32 GetCoursePathCount() const;

	UFUNCTION(BlueprintPure, Category = "Course")
	FString GetCoursePathName(int32 PathIndex) const;

	UFUNCTION(BlueprintPure, Category = "Course")
	float GetRaceDistanceAtStation(int32 PathIndex, int32 StationIndex) const;

	UFUNCTION(BlueprintCallable, Category = "Course")
	bool LocateCoursePath(const FVector& PositionCm, int32 HintPathIndex, int32 HintStationIndex,
		int32& OutPathIndex, int32& OutStationIndex, float HysteresisM = 4.0f) const;

protected:
	virtual void BeginPlay() override;

private:
	FStardustCourseData CourseData;
	FStardustCourseGraphData CourseGraph;
};
