#include "StardustGameMode.h"
#include "StardustHUD.h"
#include "StardustHoverPawn.h"

AStardustGameMode::AStardustGameMode()
{
	DefaultPawnClass = AStardustHoverPawn::StaticClass();
	HUDClass = AStardustHUD::StaticClass();
}

void AStardustGameMode::BeginPlay()
{
	Super::BeginPlay();

	FString Error;
	ActiveCourse = UStardustCourseGraph::LoadProjectCourse(CourseId, Error);
	if (!ActiveCourse)
	{
		UE_LOG(LogTemp, Error, TEXT("Falha ao carregar o curso %s: %s"), *CourseId.ToString(), *Error);
		return;
	}

	UE_LOG(LogTemp, Log, TEXT("Curso %s carregado: %d percursos, %d obstaculos."),
		*CourseId.ToString(), ActiveCourse->GetPathCount(), ActiveCourse->Obstacles.Num());
}