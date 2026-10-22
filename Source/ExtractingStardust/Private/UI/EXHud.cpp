#include "UI/EXHud.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Flight/EXHoverCraft.h"
#include "Race/EXRaceDirector.h"
#include "UI/EXMainMenuWidget.h"
#include "GameFramework/PlayerController.h"

namespace
{
	constexpr float MapWindowM = 1600.0f;  // metres shown across the minimap
	constexpr int32 AheadSamples = 30;     // route samples are 5 m apart: the arrow aims ~150 m ahead

	FString HudRaceClock(float Seconds)
	{
		const int32 Minutes = FMath::FloorToInt(Seconds / 60.0f);
		return FString::Printf(TEXT("%d:%05.2f"), Minutes, Seconds - Minutes * 60.0f);
	}
}

void AEXHud::DrawHUD()
{
	Super::DrawHUD();
	const AEXHoverCraft* Craft = Cast<AEXHoverCraft>(GetOwningPawn());
	if (!Craft || !Canvas)
	{
		return;
	}
	AEXRaceDirector* Race = nullptr;
	for (TActorIterator<AEXRaceDirector> It(GetWorld()); It; ++It)
	{
		Race = *It;
		break;
	}
	if (Craft->IsInHangar())
	{
		DrawHangar(Race, Craft);
		return;
	}
	if (Race && Race->IsInMenu())
	{
		APlayerController* PlayerController = GetOwningPlayerController();
		if (PlayerController && !IsValid(MainMenuWidget))
		{
			MainMenuWidget = CreateWidget<UEXMainMenuWidget>(PlayerController);
			if (MainMenuWidget)
			{
				MainMenuWidget->InitializeMenu(Race);
				MainMenuWidget->AddToViewport(100);
			}
		}
		if (MainMenuWidget)
		{
			MainMenuWidget->SetSelectedChoice(Race->GetMenuChoice());
		}
		if (PlayerController && !bMenuInputActive)
		{
			PlayerController->bShowMouseCursor = true;
			FInputModeGameAndUI InputMode;
			InputMode.SetHideCursorDuringCapture(false);
			InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
			PlayerController->SetInputMode(InputMode);
			if (MainMenuWidget)
			{
				MainMenuWidget->SetKeyboardFocus();
			}
			bMenuInputActive = true;
		}
		return;
	}
	if (MainMenuWidget)
	{
		MainMenuWidget->RemoveFromParent();
		MainMenuWidget = nullptr;
	}
	if (bMenuInputActive)
	{
		if (APlayerController* PlayerController = GetOwningPlayerController())
		{
			PlayerController->bShowMouseCursor = false;
			PlayerController->SetInputMode(FInputModeGameOnly());
		}
		bMenuInputActive = false;
	}
	if (Race && Race->IsReady())
	{
		DrawRace(Race, Craft);
	}
	if (Craft->GetMapRoute().Num() < AheadSamples * 2)
	{
		return;
	}
	const TArray<FVector2D>& Route = Craft->GetMapRoute();
	const int32 Index = Craft->GetRouteIndex();
	const FVector Location = Craft->GetActorLocation();
	const FVector2D Here(Location.X / 100.0f, Location.Y / 100.0f);
	FVector2D Forward(Craft->GetHeading());
	Forward = Forward.GetSafeNormal();

	TArray<FVector2D> Others;
	if (Race && Race->IsReady())
	{
		for (const FEXRacer& Racer : Race->GetStandings())
		{
			if (!Racer.bPlayer && !Racer.bOut && IsValid(Racer.Craft))
			{
				Others.Add(FVector2D(Racer.Craft->GetActorLocation().X / 100.0f, Racer.Craft->GetActorLocation().Y / 100.0f));
			}
		}
	}
	DrawMinimap(Route, Here, Forward, Index, Others);

	// Guide arrow: angle from the nose to the race line 150 m ahead (positive: turn right).
	const FVector2D Target = Route[(Index + AheadSamples) % Route.Num()];
	const FVector2D ToTarget = (Target - Here).GetSafeNormal();
	const float AngleDeg = FMath::RadiansToDegrees(FMath::Atan2(Forward ^ ToTarget, Forward | ToTarget));
	const FVector2D Tangent = (Route[(Index + 4) % Route.Num()] - Route[Index]).GetSafeNormal();
	const bool bWrongWay = (Forward | Tangent) < -0.3f && FVector2D(Craft->GetFlightVelocity()).Size() > 1500.0f;
	const float Off = FMath::Abs(AngleDeg);
	const FLinearColor Colour = bWrongWay ? FLinearColor(1.0f, 0.15f, 0.1f) : (Off < 25.0f ? FLinearColor(0.3f, 1.0f, 0.4f)
		: (Off < 70.0f ? FLinearColor(1.0f, 0.85f, 0.2f) : FLinearColor(1.0f, 0.4f, 0.15f)));
	const float Scale = Canvas->ClipY / 720.0f;
	DrawArrow(FVector2D(Canvas->ClipX * 0.5f, 70.0f * Scale), AngleDeg, 34.0f * Scale, Colour);
	if (bWrongWay)
	{
		DrawText(TEXT("SENTIDO ERRADO"), FLinearColor(1.0f, 0.2f, 0.1f), Canvas->ClipX * 0.5f - 80.0f * Scale, 112.0f * Scale, nullptr, 1.6f * Scale);
	}
	const float LapKm = Route.Num() * 5.0f / 1000.0f;
	DrawText(FString::Printf(TEXT("%.1f / %.1f km"), Index * 5.0f / 1000.0f, LapKm), FLinearColor::White,
		Canvas->ClipX - 200.0f * Scale, 262.0f * Scale, nullptr, 1.1f * Scale);
}

void AEXHud::DrawMinimap(const TArray<FVector2D>& Route, const FVector2D& Here, const FVector2D& Forward, int32 Index,
	const TArray<FVector2D>& Others)
{
	const float Scale = Canvas->ClipY / 720.0f;
	const float Half = 110.0f * Scale;
	const FVector2D Centre(Canvas->ClipX - Half - 24.0f * Scale, Half + 24.0f * Scale);
	DrawRect(FLinearColor(0.0f, 0.0f, 0.0f, 0.45f), Centre.X - Half, Centre.Y - Half, Half * 2.0f, Half * 2.0f);
	const FVector2D Right(-Forward.Y, Forward.X);
	const float PxPerM = Half / (MapWindowM * 0.5f);
	auto ToScreen = [&](const FVector2D& P)
	{
		const FVector2D D = P - Here;
		return Centre + FVector2D(D | Right, -(D | Forward)) * PxPerM;
	};
	auto Inside = [&](const FVector2D& S)
	{
		return FMath::Abs(S.X - Centre.X) < Half && FMath::Abs(S.Y - Centre.Y) < Half;
	};
	// The race line: 20 m steps; the next 2 km ahead bright, the rest dimmer.
	const int32 Count = Route.Num();
	for (int32 Step = 0; Step < Count; Step += 4)
	{
		const FVector2D A = ToScreen(Route[Step]);
		const FVector2D B = ToScreen(Route[(Step + 4) % Count]);
		if (!Inside(A) || !Inside(B))
		{
			continue;
		}
		const int32 Ahead = (Step - Index + Count) % Count;
		const FLinearColor Colour = Ahead < 400 ? FLinearColor(1.0f, 0.55f, 0.1f) : FLinearColor(0.75f, 0.6f, 0.45f, 0.7f);
		DrawLine(A.X, A.Y, B.X, B.Y, Colour, Ahead < 400 ? 3.0f * Scale : 2.0f * Scale);
	}
	// The other racers: small red squares.
	for (const FVector2D& Other : Others)
	{
		const FVector2D S = ToScreen(Other);
		if (Inside(S))
		{
			DrawRect(FLinearColor(1.0f, 0.25f, 0.2f), S.X - 3.0f * Scale, S.Y - 3.0f * Scale, 6.0f * Scale, 6.0f * Scale);
		}
	}
	// The craft: a white arrowhead pointing up (the map turns with it).
	const float S = 9.0f * Scale;
	DrawLine(Centre.X, Centre.Y - S * 1.3f, Centre.X - S, Centre.Y + S, FLinearColor::White, 2.0f * Scale);
	DrawLine(Centre.X, Centre.Y - S * 1.3f, Centre.X + S, Centre.Y + S, FLinearColor::White, 2.0f * Scale);
	DrawLine(Centre.X - S, Centre.Y + S, Centre.X + S, Centre.Y + S, FLinearColor::White, 2.0f * Scale);
	DrawText(TEXT("N"), FLinearColor(0.9f, 0.9f, 0.9f), Centre.X - Half + 6.0f * Scale, Centre.Y - Half + 4.0f * Scale, nullptr, 0.9f * Scale);
}

void AEXHud::DrawArrow(const FVector2D& Center, float AngleDeg, float Size, const FLinearColor& Colour)
{
	// A chevron arrow: tip, two barbs and a short shaft, turned by the angle (0 = straight ahead, up the screen).
	const float Radians = FMath::DegreesToRadians(AngleDeg);
	auto Turn = [&](float X, float Y)
	{
		return Center + FVector2D(X * FMath::Cos(Radians) - Y * FMath::Sin(Radians), X * FMath::Sin(Radians) + Y * FMath::Cos(Radians)) * Size;
	};
	const FVector2D Tip = Turn(0.0f, -1.0f);
	const FVector2D Left = Turn(-0.8f, -0.1f);
	const FVector2D Right = Turn(0.8f, -0.1f);
	const FVector2D Tail = Turn(0.0f, 0.9f);
	const float Width = 5.0f * Size / 34.0f;
	DrawLine(Tip.X, Tip.Y, Left.X, Left.Y, Colour, Width);
	DrawLine(Tip.X, Tip.Y, Right.X, Right.Y, Colour, Width);
	DrawLine(Tip.X, Tip.Y, Tail.X, Tail.Y, Colour, Width);
}

void AEXHud::DrawRace(const AEXRaceDirector* Race, const AEXHoverCraft* Craft)
{
	const float Scale = Canvas->ClipY / 720.0f;
	const bool bBots = Race->GetMode() == EEXRaceMode::Bots;
	const TArray<FEXRacer>& Standings = Race->GetStandings();
	const FLinearColor White = FLinearColor::White;
	const FLinearColor Red(1.0f, 0.2f, 0.15f);

	// Panel, top left: mode and time, place, lives, medical kit.
	const float X = 24.0f * Scale;
	float Y = 20.0f * Scale;
	DrawRect(FLinearColor(0.0f, 0.0f, 0.0f, 0.45f), X - 10.0f * Scale, Y - 6.0f * Scale, 330.0f * Scale, (bBots ? 122.0f : 98.0f) * Scale);
	DrawText(FString::Printf(TEXT("%s   %s"), bBots ? TEXT("SOBREVIVÊNCIA") : TEXT("CONTRA O CRONÓMETRO"), *HudRaceClock(Race->GetRaceTime())), White, X, Y,
		nullptr, 1.3f * Scale);
	Y += 26.0f * Scale;
	if (bBots)
	{
		int32 Alive = 0;
		for (const FEXRacer& Racer : Standings)
		{
			Alive += Racer.bOut ? 0 : 1;
		}
		DrawText(FString::Printf(TEXT("POSICAO %d / %d    em prova: %d"), Race->GetPlayerPlace(), Standings.Num(), Alive), White, X, Y,
			nullptr, 1.1f * Scale);
		Y += 24.0f * Scale;
	}
	DrawText(TEXT("VIDAS"), White, X, Y, nullptr, 1.1f * Scale);
	for (int32 Life = 0; Life < Craft->GetMaxLives(); ++Life)
	{
		DrawRect(Life < Craft->GetLives() ? FLinearColor(0.3f, 1.0f, 0.4f) : FLinearColor(0.25f, 0.25f, 0.25f, 0.8f),
			X + (70.0f + Life * 26.0f) * Scale, Y + 3.0f * Scale, 20.0f * Scale, 14.0f * Scale);
	}
	Y += 24.0f * Scale;
	DrawText(FString::Printf(TEXT("KIT MEDICO x%d   (H / Quadrado)"), Craft->GetMedKits()), Craft->GetMedKits() > 0 ? White
		: FLinearColor(0.6f, 0.6f, 0.6f), X, Y, nullptr, 1.1f * Scale);

	const float Mid = Canvas->ClipX * 0.5f;
	// Countdown: 3, 2, 1, VAI!
	if (Race->GetCountdown() > 0.0f)
	{
		const int32 Count = FMath::CeilToInt(Race->GetCountdown() - 1.0f);
		DrawText(Count > 0 ? FString::FromInt(Count) : FString(TEXT("VAI!")), Count > 0 ? FLinearColor(1.0f, 0.85f, 0.2f)
			: FLinearColor(0.3f, 1.0f, 0.4f), Mid - 40.0f * Scale, Canvas->ClipY * 0.3f, nullptr, 4.0f * Scale);
	}
	// A life lost: red flash.
	const float SinceHit = GetWorld()->GetTimeSeconds() - Craft->GetLastHitTime();
	if (Craft->GetLastHitTime() >= 0.0f && SinceHit < 1.5f && !Craft->IsEliminated())
	{
		DrawRect(FLinearColor(1.0f, 0.0f, 0.0f, 0.25f * (1.0f - SinceHit / 1.5f)), 0.0f, 0.0f, Canvas->ClipX, Canvas->ClipY);
		DrawText(TEXT("-1 VIDA"), Red, Mid - 60.0f * Scale, Canvas->ClipY * 0.36f, nullptr, 2.4f * Scale);
	}
	if (Craft->IsEliminated() && !Race->IsOver())
	{
		DrawText(TEXT("SEM VIDAS - FICASTE PELO CAMINHO"), Red, Mid - 260.0f * Scale, Canvas->ClipY * 0.36f, nullptr, 2.0f * Scale);
	}
	// Messages of the last 6 s (left, under the panel).
	float FeedY = 170.0f * Scale;
	for (const TPair<float, FString>& Line : Race->GetFeed())
	{
		if (Race->GetRaceTime() - Line.Key < 6.0f || Race->GetCountdown() > 0.0f)
		{
			DrawText(Line.Value, FLinearColor(1.0f, 0.9f, 0.6f), X, FeedY, nullptr, 1.0f * Scale);
			FeedY += 20.0f * Scale;
		}
	}
	// Results: the survivors by time, then the ones left on the way.
	if (Race->IsOver())
	{
		const float W = 460.0f * Scale;
		const float Row = 22.0f * Scale;
		float TY = Canvas->ClipY * 0.5f - (Standings.Num() + 2) * Row * 0.5f;
		DrawRect(FLinearColor(0.0f, 0.0f, 0.0f, 0.7f), Mid - W * 0.5f, TY - 10.0f * Scale, W, (Standings.Num() + 2) * Row + 20.0f * Scale);
		DrawText(TEXT("RESULTADOS"), FLinearColor(1.0f, 0.85f, 0.2f), Mid - 70.0f * Scale, TY, nullptr, 1.4f * Scale);
		TY += Row * 1.5f;
		for (int32 Place = 0; Place < Standings.Num(); ++Place)
		{
			const FEXRacer& Racer = Standings[Place];
			const FLinearColor Colour = Racer.bPlayer ? FLinearColor(0.3f, 1.0f, 0.4f) : (Racer.bOut ? FLinearColor(0.6f, 0.6f, 0.6f) : White);
			const FString Result = Racer.bFinished ? HudRaceClock(Racer.FinishTime)
				: (Racer.bOut ? FString::Printf(TEXT("ficou no km %.1f"), Racer.OutAtM / 1000.0f) : FString(TEXT("nao chegou")));
			DrawText(FString::Printf(TEXT("%d"), Place + 1), Colour, Mid - W * 0.5f + 16.0f * Scale, TY, nullptr, 1.0f * Scale);
			DrawText(Racer.Name, Colour, Mid - W * 0.5f + 60.0f * Scale, TY, nullptr, 1.0f * Scale);
			DrawText(Result, Colour, Mid + 40.0f * Scale, TY, nullptr, 1.0f * Scale);
			TY += Row;
		}
	}
}

void AEXHud::DrawStatBar(float X, float Y, float Width, float Height, float Percent, const FLinearColor& BarColor, const FString& Label, const FString& ValueStr)
{
	const float Scale = Canvas->ClipY / 720.0f;
	DrawText(Label, FLinearColor(0.85f, 0.85f, 0.9f), X, Y - 18.0f * Scale, nullptr, 0.9f * Scale);
	DrawText(ValueStr, FLinearColor(1.0f, 0.9f, 0.5f), X + Width - 75.0f * Scale, Y - 18.0f * Scale, nullptr, 0.9f * Scale);
	DrawRect(FLinearColor(0.08f, 0.1f, 0.14f, 0.9f), X, Y, Width, Height);
	const float ClampedPct = FMath::Clamp(Percent, 0.0f, 1.0f);
	DrawRect(BarColor, X + 2.0f * Scale, Y + 2.0f * Scale, (Width - 4.0f * Scale) * ClampedPct, Height - 4.0f * Scale);
}

void AEXHud::DrawHangar(const AEXRaceDirector* Race, const AEXHoverCraft* Craft)
{
	const float Scale = Canvas->ClipY / 720.0f;
	const FString ShipName = Craft->GetShipName().ToUpper();

	// Top Title Bar
	DrawRect(FLinearColor(0.015f, 0.02f, 0.035f, 0.85f), 0.0f, 0.0f, Canvas->ClipX, 56.0f * Scale);
	DrawRect(FLinearColor(1.0f, 0.82f, 0.2f, 0.9f), 0.0f, 54.0f * Scale, Canvas->ClipX, 2.0f * Scale);
	DrawText(TEXT("EXTRACTING STARDUST"), FLinearColor(1.0f, 0.85f, 0.2f), 30.0f * Scale, 12.0f * Scale, nullptr, 1.6f * Scale);
	DrawText(TEXT("HANGAR SHOWROOM - INSPECAO TECNICA 360"), FLinearColor(0.85f, 0.85f, 0.85f), 280.0f * Scale, 18.0f * Scale, nullptr, 1.05f * Scale);

	// Right Tech Sheet Card
	const float CardW = 360.0f * Scale;
	const float CardX = Canvas->ClipX - CardW - 30.0f * Scale;
	const float CardY = 76.0f * Scale;
	const float CardH = 570.0f * Scale;
	DrawRect(FLinearColor(0.02f, 0.03f, 0.05f, 0.82f), CardX, CardY, CardW, CardH);
	DrawRect(FLinearColor(0.25f, 0.45f, 0.7f, 0.6f), CardX, CardY, CardW, 2.0f * Scale);

	float Y = CardY + 16.0f * Scale;
	DrawText(TEXT("FICHA TECNICA DA NAVE"), FLinearColor(0.4f, 0.8f, 1.0f), CardX + 20.0f * Scale, Y, nullptr, 1.0f * Scale);
	Y += 28.0f * Scale;
	DrawText(ShipName, FLinearColor(1.0f, 0.9f, 0.3f), CardX + 20.0f * Scale, Y, nullptr, 1.9f * Scale);
	Y += 36.0f * Scale;

	FString RoleStr, EngineStr, SizeStr, ArmorStr;
	float TopSpeedPct = 0.85f, AccelPct = 0.80f, ArmorPct = 0.70f, AgilityPct = 0.85f;
	FString SpeedVal = TEXT("440 km/h"), AccelVal = TEXT("4.6 G"), ArmorVal = TEXT("3 VIDAS"), AgilityVal = TEXT("85%");

	if (ShipName.Contains(TEXT("STRIX")))
	{
		RoleStr = TEXT("Interceptor de Linha - Equilibrado");
		EngineStr = TEXT("2x Plasma Vectorial sobrepostos");
		SizeStr = TEXT("6.31 m x 3.00 m x 1.39 m");
		ArmorStr = TEXT("Carrocaria 12mm / Juntas 5mm");
		TopSpeedPct = 0.88f; AccelPct = 0.85f; ArmorPct = 0.70f; AgilityPct = 0.88f;
		SpeedVal = TEXT("450 km/h"); AccelVal = TEXT("4.8 G"); ArmorVal = TEXT("3 VIDAS"); AgilityVal = TEXT("88%");
	}
	else if (ShipName.Contains(TEXT("WRAITH")))
	{
		RoleStr = TEXT("Caca Pesado em U - Rapido");
		EngineStr = TEXT("3x Plasma em capa transversal");
		SizeStr = TEXT("6.45 m x 3.20 m x 1.42 m");
		ArmorStr = TEXT("Quilhas de tubarao reforcadas");
		TopSpeedPct = 0.92f; AccelPct = 0.82f; ArmorPct = 0.70f; AgilityPct = 0.80f;
		SpeedVal = TEXT("470 km/h"); AccelVal = TEXT("4.5 G"); ArmorVal = TEXT("3 VIDAS"); AgilityVal = TEXT("80%");
	}
	else if (ShipName.Contains(TEXT("NOMAD")))
	{
		RoleStr = TEXT("Dropship Pesado - Alta Robustez");
		EngineStr = TEXT("4x Capsulas plasma em bracos A");
		SizeStr = TEXT("7.10 m x 3.80 m x 1.65 m");
		ArmorStr = TEXT("Modulo de carga blindado");
		TopSpeedPct = 0.78f; AccelPct = 0.72f; ArmorPct = 0.88f; AgilityPct = 0.72f;
		SpeedVal = TEXT("390 km/h"); AccelVal = TEXT("4.0 G"); ArmorVal = TEXT("4 VIDAS"); AgilityVal = TEXT("72%");
	}
	else if (ShipName.Contains(TEXT("VORTEX")))
	{
		RoleStr = TEXT("Delta Ultra-Leve - Aceleracao Maxima");
		EngineStr = TEXT("1x Plasma macico embutido na cauda");
		SizeStr = TEXT("5.86 m x 3.32 m x 0.73 m");
		ArmorStr = TEXT("Asa fina ultraleve (fragil)");
		TopSpeedPct = 0.98f; AccelPct = 0.98f; ArmorPct = 0.45f; AgilityPct = 0.96f;
		SpeedVal = TEXT("500 km/h"); AccelVal = TEXT("5.4 G"); ArmorVal = TEXT("2 VIDAS"); AgilityVal = TEXT("96%");
	}
	else // BASTION
	{
		RoleStr = TEXT("Blindado de Choque - Inquebravel");
		EngineStr = TEXT("1x Motor Colossal de Fusao");
		SizeStr = TEXT("6.80 m x 3.60 m x 1.80 m");
		ArmorStr = TEXT("Placas de aco militar reforcado");
		TopSpeedPct = 0.74f; AccelPct = 0.65f; ArmorPct = 1.0f; AgilityPct = 0.62f;
		SpeedVal = TEXT("370 km/h"); AccelVal = TEXT("3.6 G"); ArmorVal = TEXT("5 VIDAS"); AgilityVal = TEXT("62%");
	}

	DrawText(RoleStr, FLinearColor(0.85f, 0.85f, 0.85f), CardX + 20.0f * Scale, Y, nullptr, 0.95f * Scale);
	Y += 34.0f * Scale;

	const float BarW = CardW - 40.0f * Scale;
	const float BarH = 12.0f * Scale;
	DrawStatBar(CardX + 20.0f * Scale, Y, BarW, BarH, TopSpeedPct, FLinearColor(0.2f, 0.7f, 1.0f), TEXT("VELOCIDADE DE PONTA"), SpeedVal);
	Y += 46.0f * Scale;
	DrawStatBar(CardX + 20.0f * Scale, Y, BarW, BarH, AccelPct, FLinearColor(0.3f, 1.0f, 0.5f), TEXT("ACELERACAO"), AccelVal);
	Y += 46.0f * Scale;
	DrawStatBar(CardX + 20.0f * Scale, Y, BarW, BarH, ArmorPct, FLinearColor(1.0f, 0.4f, 0.3f), TEXT("BLINDAGEM / VIDAS"), ArmorVal);
	Y += 46.0f * Scale;
	DrawStatBar(CardX + 20.0f * Scale, Y, BarW, BarH, AgilityPct, FLinearColor(1.0f, 0.8f, 0.2f), TEXT("MANOBRABILIDADE / DRIFT"), AgilityVal);
	Y += 56.0f * Scale;

	// Technical Details Box
	DrawRect(FLinearColor(0.06f, 0.08f, 0.12f, 0.7f), CardX + 16.0f * Scale, Y, CardW - 32.0f * Scale, 140.0f * Scale);
	DrawText(TEXT("ESPECIFICACOES DE ENGENHARIA"), FLinearColor(0.5f, 0.75f, 0.95f), CardX + 26.0f * Scale, Y + 10.0f * Scale, nullptr, 0.85f * Scale);
	DrawText(FString::Printf(TEXT("Propulsao:  %s"), *EngineStr), FLinearColor(0.85f, 0.85f, 0.85f), CardX + 26.0f * Scale, Y + 34.0f * Scale, nullptr, 0.85f * Scale);
	DrawText(FString::Printf(TEXT("Dimensoes:  %s"), *SizeStr), FLinearColor(0.85f, 0.85f, 0.85f), CardX + 26.0f * Scale, Y + 60.0f * Scale, nullptr, 0.85f * Scale);
	DrawText(FString::Printf(TEXT("Blindagem:  %s"), *ArmorStr), FLinearColor(0.85f, 0.85f, 0.85f), CardX + 26.0f * Scale, Y + 86.0f * Scale, nullptr, 0.85f * Scale);
	DrawText(TEXT("Suspensao:  Emissores Hover + Placa Gravitica"), FLinearColor(0.85f, 0.85f, 0.85f), CardX + 26.0f * Scale, Y + 112.0f * Scale, nullptr, 0.85f * Scale);

	// Center Selector Bar
	const float SelW = 340.0f * Scale;
	const float SelX = (Canvas->ClipX - SelW) * 0.5f;
	const float SelY = Canvas->ClipY - 110.0f * Scale;
	DrawRect(FLinearColor(0.02f, 0.03f, 0.05f, 0.75f), SelX, SelY, SelW, 44.0f * Scale);
	DrawText(FString::Printf(TEXT("<   %s   >"), *ShipName), FLinearColor(1.0f, 0.9f, 0.3f), SelX + 40.0f * Scale, SelY + 10.0f * Scale, nullptr, 1.4f * Scale);

	// Bottom Controls Bar
	DrawRect(FLinearColor(0.015f, 0.02f, 0.035f, 0.92f), 0.0f, Canvas->ClipY - 48.0f * Scale, Canvas->ClipX, 48.0f * Scale);
	DrawRect(FLinearColor(0.2f, 0.5f, 0.8f, 0.7f), 0.0f, Canvas->ClipY - 48.0f * Scale, Canvas->ClipX, 1.5f * Scale);
	DrawText(TEXT("A/D ou Rato: Girar 360    W/S: Inclinar    Roda: Zoom    Espaco: Auto-Rotacao    Tab / 1-5: Nave    Enter / X: Menu Principal    Esc: Voltar"),
		FLinearColor(0.85f, 0.85f, 0.85f), 30.0f * Scale, Canvas->ClipY - 32.0f * Scale, nullptr, 0.88f * Scale);
}
