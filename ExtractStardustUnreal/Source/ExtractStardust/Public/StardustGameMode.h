#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "StardustCourseGraph.h"
#include "StardustGameMode.generated.h"

UCLASS()
class EXTRACTSTARDUST_API AStardustGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AStardustGameMode();
	virtual void BeginPlay() override;

	UFUNCTION(BlueprintPure, Category="Extract Stardust|Course")
	UStardustCourseGraph* GetCourseGraph() const { return ActiveCourse; }

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Extract Stardust|Course")
	FName CourseId = TEXT("red_dust_divide");

protected:
	UPROPERTY(Transient, BlueprintReadOnly, Category="Extract Stardust|Course")
	TObjectPtr<UStardustCourseGraph> ActiveCourse;
};