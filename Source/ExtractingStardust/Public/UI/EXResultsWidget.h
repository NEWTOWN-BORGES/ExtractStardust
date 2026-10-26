#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "EXResultsWidget.generated.h"

class AEXRaceDirector;
class UVerticalBox;
class UWidget;
class UWidgetTree;
struct FEXItem;

/**
 * The end of an expedition (player, 2026-10-26: "janelas de vitória com os ganhos e de derrota com o espólio perdido,
 * um jogo de corrida a sério"). Victory (EXTRACTED) in green and gold, defeat (DESTROYED) in red, STRANDED in amber:
 * the verdict and the place, the time, the checkpoints and the distance; what it paid line by line (place, extraction,
 * checkpoints, first extraction) or what it cost; the pieces won from the pool or lost to it as cards in their rarity's
 * colour, and the insured module kept; the classification of the whole field. Enter / X goes on (AEXRaceDirector).
 * Built in code from AEXRaceDirector::GetSummary when the race is over.
 */
UCLASS()
class EXTRACTINGSTARDUST_API UEXResultsWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void InitializeResults(AEXRaceDirector* InRaceDirector);

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	void BuildTree();
	UWidget* BuildVerdict(UWidgetTree* Tree);
	UWidget* BuildLedger(UWidgetTree* Tree);
	UWidget* BuildPieces(UWidgetTree* Tree);
	UWidget* BuildStandings(UWidgetTree* Tree);
	UWidget* MakeCard(UWidgetTree* Tree, const FEXItem& Item, bool bLost, bool bSaved);

	/** Shows Widget from Delay seconds on: a short fade and slide up. */
	void Reveal(UWidget* Widget, float Delay);

	struct FReveal
	{
		UWidget* Widget = nullptr;
		float Delay = 0.0f;
	};

	UPROPERTY(Transient) TObjectPtr<AEXRaceDirector> RaceDirector;
	TArray<FReveal> Reveals;
	/** The total counts up (or down, a loss) once the ledger is in. */
	class UTextBlock* TotalText = nullptr;
	int32 TotalTarget = 0;
	bool bTotalLoss = false;
	float Age = 0.0f;
};
