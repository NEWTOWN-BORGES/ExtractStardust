#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "StardustHUD.generated.h"

UCLASS()
class EXTRACTSTARDUST_API AStardustHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;
};
