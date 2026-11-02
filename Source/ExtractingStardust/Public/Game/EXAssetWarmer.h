// Extracting Stardust - keeps the game's own art in memory (player, 2026-11-02: "o jogo trava muito no hangar e no meio
// das outras naves").
#pragma once

#include "CoreMinimal.h"
#include "Engine/StreamableManager.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "EXAssetWarmer.generated.h"

/**
 * The card photos and icons (/Game/UI), the ship pieces (/Game/Ships) and the explosion art (/Game/FX) load in the
 * background when the game starts and stay loaded. Before, each one loaded from the disk on the game thread the first
 * time a card, a piece or an explosion appeared (a hitch), and the garbage collector unloaded it again a minute later.
 */
UCLASS()
class EXTRACTINGSTARDUST_API UEXAssetWarmer : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

private:
	FStreamableManager Streamable;
	TSharedPtr<FStreamableHandle> Handle;
};
