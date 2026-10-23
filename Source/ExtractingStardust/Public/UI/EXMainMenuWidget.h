#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "EXMainMenuWidget.generated.h"

class AEXRaceDirector;
class AEXHoverCraft;
class UButton;
class UTextBlock;
class UVerticalBox;

/** Briefing overlay: Solo, pelotão de 15, hangar. Voo livre fica só na linha de comandos. */
UCLASS()
class EXTRACTINGSTARDUST_API UEXMainMenuWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void InitializeMenu(AEXRaceDirector* InRaceDirector);
	void SetSelectedChoice(int32 Choice);

protected:
	virtual void NativeConstruct() override;

private:
	UButton* CreateModeButton(UVerticalBox* Parent, const FString& Number, const FString& Title, const FString& Description);
	void ApplyButtonStyle(UButton* Button, const FLinearColor& Normal, const FLinearColor& Hovered, const FLinearColor& Pressed);
	void StartChoice(int32 Choice);
	void RefreshSelection();
	void RefreshShipName();
	AEXHoverCraft* GetPlayerCraft() const;

	UFUNCTION() void OnSoloPressed();
	UFUNCTION() void OnBotsPressed();
	UFUNCTION() void OnHangarPressed();
	UFUNCTION() void OnPreviousShipPressed();
	UFUNCTION() void OnNextShipPressed();

	UPROPERTY() TObjectPtr<AEXRaceDirector> RaceDirector;
	UPROPERTY() TArray<TObjectPtr<UButton>> ModeButtons;
	UPROPERTY() TObjectPtr<UTextBlock> ShipNameText;
	int32 SelectedChoice = 1;
};
