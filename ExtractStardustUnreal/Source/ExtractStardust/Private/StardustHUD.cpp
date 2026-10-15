#include "StardustHUD.h"
#include "StardustHoverPawn.h"
#include "StardustProfileSubsystem.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"

void AStardustHUD::DrawHUD()
{
	Super::DrawHUD();
	const AStardustHoverPawn* Craft = Cast<AStardustHoverPawn>(GetOwningPawn());
	if (!Craft || !Canvas || !GEngine) return;
	UFont* Font = GEngine->GetSmallFont();
	const FLinearColor White(0.85f, 0.93f, 1.0f, 1.0f);
	Canvas->DrawText(Font, TEXT("EXTRACT STARDUST  |  PILOTO"), 30.0f, 30.0f, 1.35f, 1.35f, FLinearColor(0.2f, 0.85f, 1.0f));
	Canvas->DrawText(Font, FString::Printf(TEXT("VEL  %03.0f km/h    CASCO  %03.0f%%    BOOST  %03.0f%%    CALOR  %03.0f%%"), Craft->GetSpeedKmh(), Craft->GetHull(), Craft->GetBoostFuel(), Craft->GetHeat()), 30.0f, 62.0f, 1.15f, 1.15f, White);
	Canvas->DrawText(Font, FString::Printf(TEXT("1  Nitro x%d     2  Reparacao x%d     3  Refrigeracao x%d     4  Estabilizador x%d"), Craft->GetLoadoutCount(0), Craft->GetLoadoutCount(1), Craft->GetLoadoutCount(2), Craft->GetLoadoutCount(3)), 30.0f, 95.0f, 1.0f, 1.0f, White);
	Canvas->DrawText(Font, TEXT("W / SETA CIMA: acelerar    A/D / SETAS: direcao    SHIFT: nitro    R: reposicionar"), 30.0f, 124.0f, 0.9f, 0.9f, FLinearColor(0.65f, 0.72f, 0.8f));
}
