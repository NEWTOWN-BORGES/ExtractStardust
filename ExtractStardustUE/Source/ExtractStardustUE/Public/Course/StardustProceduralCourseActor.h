#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "StardustProceduralCourseActor.generated.h"

class UMaterialInterface;
class UProceduralMeshComponent;

UCLASS()
class EXTRACTSTARDUSTUE_API AStardustProceduralCourseActor : public AActor
{
	GENERATED_BODY()

public:
	AStardustProceduralCourseActor();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Course")
	TObjectPtr<UProceduralMeshComponent> CourseMesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Course")
	FString CourseFileName = TEXT("sandbox_course.bytes");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Course")
	TObjectPtr<UMaterialInterface> CourseMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Course")
	bool bCreateCollision = true;

	UFUNCTION(BlueprintCallable, Category = "Course")
	bool LoadAndBuildCourse(FString& OutError);

protected:
	virtual void BeginPlay() override;
};
