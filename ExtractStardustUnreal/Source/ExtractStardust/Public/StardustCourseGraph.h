#pragma once

#include "CoreMinimal.h"
#include "StardustCourseData.h"
#include "UObject/Object.h"
#include "StardustCourseGraph.generated.h"

USTRUCT(BlueprintType)
struct FStardustCoursePath
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category="Course Graph") FString Id;
	UPROPERTY(BlueprintReadOnly, Category="Course Graph") int32 Index = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category="Course Graph") int32 Parent = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category="Course Graph") float From = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course Graph") float To = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course Graph") float Length = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course Graph") TObjectPtr<UStardustCourseData> Data = nullptr;

	bool IsMain() const { return Parent < 0; }
};

USTRUCT(BlueprintType)
struct FStardustCourseObstacle
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category="Course Graph") int32 Path = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category="Course Graph") float Distance = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course Graph") float LateralU = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category="Course Graph") float Radius = 0.0f;
};

UCLASS(BlueprintType)
class EXTRACTSTARDUST_API UStardustCourseGraph : public UObject
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Course")
	static UStardustCourseGraph* ParseRDDG(const TArray<uint8>& Bytes, FString& Error);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Course")
	static UStardustCourseGraph* LoadProjectCourse(FName CourseId, FString& Error);

	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Course")
	bool LoadObstaclesJson(const FString& Json, FString& Error);

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	int32 GetPathCount() const { return Paths.Num(); }

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	int32 GetBranchCount() const { return FMath::Max(0, Paths.Num() - 1); }

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	bool GetPath(int32 Index, FStardustCoursePath& OutPath) const;
	UFUNCTION(BlueprintCallable, Category="Extract Stardust|Course")
	float Locate(const FVector& Position, UPARAM(ref) int32& PathIndex, UPARAM(ref) int32& StationIndex, float Hysteresis = 400.0f) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	TArray<FStardustCoursePath> BranchesLeaving(float FromDistance, float ToDistance) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	float ToRaceDistance(int32 PathIndex, float PathDistance) const;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	TArray<FStardustCourseObstacle> GetObstaclesForPath(int32 PathIndex) const;
	static float SurfaceDistance(const UStardustCourseData& Data, const FVector& Position, int32 StationIndex);

	UPROPERTY(BlueprintReadOnly, Category="Course Graph")
	TArray<FStardustCoursePath> Paths;

	UPROPERTY(BlueprintReadOnly, Category="Course Graph")
	TArray<FStardustCourseObstacle> Obstacles;
};