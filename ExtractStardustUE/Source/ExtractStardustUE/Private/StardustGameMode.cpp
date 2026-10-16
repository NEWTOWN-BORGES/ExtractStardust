#include "StardustGameMode.h"

#include "Vehicle/StardustHovercraftPawn.h"

AStardustGameMode::AStardustGameMode()
{
	DefaultPawnClass = AStardustHovercraftPawn::StaticClass();
}
