#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "EXHangarMenuWidget.generated.h"

class AEXGameMode;
class STextBlock;
class SWidget;

/** Native Slate/UMG hangar menu. No browser or HTML assets are involved. */
UCLASS()
class EXTRACTINGSTARDUST_API UEXHangarMenuWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void SetGameMode(AEXGameMode* InGameMode);

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;

private:
	void RefreshShipLabel();

	TWeakObjectPtr<AEXGameMode> GameMode;
	TSharedPtr<STextBlock> ShipNameLabel;
};
