#include "AI/StardustBotPawn.h"

#include "AI/StardustLineFollowerComponent.h"

AStardustBotPawn::AStardustBotPawn()
{
	AutoPossessPlayer = EAutoReceiveInput::Disabled;
	LineFollowerComponent = CreateDefaultSubobject<UStardustLineFollowerComponent>(TEXT("LineFollower"));
	LineFollowerComponent->Course = CourseComponent;
	LineFollowerComponent->PrimaryComponentTick.bStartWithTickEnabled = false;
}

void AStardustBotPawn::StartRacing()
{
	if (LineFollowerComponent)
	{
		LineFollowerComponent->SetComponentTickEnabled(true);
	}
}
