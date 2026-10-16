#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "StardustLineFollowerComponent.generated.h"

class UStardustCourseComponent;
class UStardustCraftMovementComponent;

UCLASS(ClassGroup = (Stardust), meta = (BlueprintSpawnableComponent))
class EXTRACTSTARDUSTUE_API UStardustLineFollowerComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UStardustLineFollowerComponent();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Racing AI")
	TObjectPtr<UStardustCourseComponent> Course;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Racing AI", meta = (ClampMin = "-1", ClampMax = "1"))
	float LaneU = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Racing AI", meta = (ClampMin = "0"))
	float SpeedLimitMPerSecond = 1000.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Racing AI", meta = (ClampMin = "0.1"))
	float LookAheadBaseM = 16.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Racing AI", meta = (ClampMin = "0"))
	float LookAheadPerSpeed = 0.36f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Racing AI", meta = (ClampMin = "0"))
	float LaneResponse = 1.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Racing AI", meta = (ClampMin = "0"))
	float LateralDamping = 0.02f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Racing AI", meta = (ClampMin = "0.1", ClampMax = "1"))
	float CornerMargin = 0.82f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Racing AI")
	bool bUseBoost = false;

	UPROPERTY(BlueprintReadOnly, Category = "Racing AI")
	int32 CurrentStation = INDEX_NONE;

	UPROPERTY(BlueprintReadOnly, Category = "Racing AI")
	float DistanceM = 0.0f;

	UFUNCTION(BlueprintCallable, Category = "Racing AI")
	void SetCourse(UStardustCourseComponent* NewCourse);

protected:
	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UStardustCraftMovementComponent> CraftMovement;
	float CurrentLaneU = 0.0f;

	float CurvatureAhead(float SpanM, float& OutBankDegrees) const;
};
