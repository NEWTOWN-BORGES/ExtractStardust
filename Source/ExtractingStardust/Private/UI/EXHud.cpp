#include "UI/EXHud.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Flight/EXHoverCraft.h"
#include "Race/EXRaceDirector.h"
#include "GameFramework/PlayerController.h"
#include "UI/EXHangarWidget.h"
#include "UI/EXMainMenuWidget.h"
#include "UI/EXRaceHudWidget.h"
#include "UI/EXResultsWidget.h"

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
	// The menu and the hangar are widgets over the workshop; the race is drawn here.
	const bool bMenu = Race && Race->IsInMenu();
	const bool bHangar = Craft->IsInHangar();
	ShowScreens(Race, bMenu, bHangar);
	// The race panels of the mock-up hud.png are a widget; the minimap, the arrow and the messages stay here.
	const bool bRacing = !bMenu && !bHangar && !Craft->IsInShowroom() && Race && Race->IsReady();
	if (bRacing && !IsValid(RaceHudWidget) && GetOwningPlayerController())
	{
		RaceHudWidget = CreateWidget<UEXRaceHudWidget>(GetOwningPlayerController());
		if (RaceHudWidget)
		{
			RaceHudWidget->InitializeHud(Race);
			RaceHudWidget->AddToViewport(10);
		}
	}
	else if (!bRacing && RaceHudWidget)
	{
		RaceHudWidget->RemoveFromParent();
		RaceHudWidget = nullptr;
	}
	// The results screen, once the race is over.
	const bool bResults = bRacing && Race->IsOver();
	if (bResults && !IsValid(ResultsWidget) && GetOwningPlayerController())
	{
		ResultsWidget = CreateWidget<UEXResultsWidget>(GetOwningPlayerController());
		if (ResultsWidget)
		{
			ResultsWidget->InitializeResults(Race);
			ResultsWidget->AddToViewport(50);
		}
	}
	else if (!bResults && ResultsWidget)
	{
		ResultsWidget->RemoveFromParent();
		ResultsWidget = nullptr;
	}
	if (bMenu || bHangar || Craft->IsInShowroom())
	{
		return;
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
	if (!RaceHudWidget)
	{
		const float LapKm = Route.Num() * 5.0f / 1000.0f;
		DrawText(FString::Printf(TEXT("%.1f / %.1f km"), Index * 5.0f / 1000.0f, LapKm), FLinearColor::White,
			Canvas->ClipX - 200.0f * Scale, 262.0f * Scale, nullptr, 1.1f * Scale);
	}
}

void AEXHud::DrawMinimap(const TArray<FVector2D>& Route, const FVector2D& Here, const FVector2D& Forward, int32 Index,
	const TArray<FVector2D>& Others)
{
	const float Scale = Canvas->ClipY / 720.0f;
	const float Half = 110.0f * Scale;
	// Under the lives plate of the race widget (top right).
	const FVector2D Centre(Canvas->ClipX - Half - 24.0f * Scale, Half + (RaceHudWidget ? 104.0f : 24.0f) * Scale);
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

void AEXHud::ShowScreens(AEXRaceDirector* Race, bool bMenu, bool bHangar)
{
	APlayerController* PlayerController = GetOwningPlayerController();
	if (!PlayerController)
	{
		return;
	}
	if (bMenu && !IsValid(MainMenuWidget))
	{
		MainMenuWidget = CreateWidget<UEXMainMenuWidget>(PlayerController);
		if (MainMenuWidget)
		{
			MainMenuWidget->InitializeMenu(Race);
			MainMenuWidget->AddToViewport(100);
		}
	}
	else if (!bMenu && MainMenuWidget)
	{
		MainMenuWidget->RemoveFromParent();
		MainMenuWidget = nullptr;
	}
	if (bHangar && !IsValid(HangarWidget))
	{
		HangarWidget = CreateWidget<UEXHangarWidget>(PlayerController);
		if (HangarWidget)
		{
			HangarWidget->InitializeHangar(Race);
			HangarWidget->AddToViewport(90);
		}
	}
	else if (!bHangar && HangarWidget)
	{
		HangarWidget->RemoveFromParent();
		HangarWidget = nullptr;
	}
	// The menu and the hangar take the mouse (their lines, tabs and pieces are clicked); the race gives it to the game.
	const int32 Wanted = (bMenu || bHangar) ? 1 : 0;
	if (Wanted != InputScreen)
	{
		InputScreen = Wanted;
		if (bMenu || bHangar)
		{
			PlayerController->bShowMouseCursor = true;
			FInputModeGameAndUI InputMode;
			InputMode.SetHideCursorDuringCapture(false);
			InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
			PlayerController->SetInputMode(InputMode);
		}
		else
		{
			PlayerController->bShowMouseCursor = false;
			PlayerController->SetInputMode(FInputModeGameOnly());
		}
	}
}

void AEXHud::DrawRace(const AEXRaceDirector* Race, const AEXHoverCraft* Craft)
{
	const float Scale = Canvas->ClipY / 720.0f;
	const bool bBots = Race->GetMode() == EEXRaceMode::Bots;
	const TArray<FEXRacer>& Standings = Race->GetStandings();
	const FLinearColor White = FLinearColor::White;
	const FLinearColor Red(1.0f, 0.2f, 0.15f);
	const FLinearColor Grey(0.6f, 0.6f, 0.6f);
	const FLinearColor Sand(0.66f, 0.55f, 0.42f);
	const float Now = GetWorld()->GetTimeSeconds();

	const float X = 24.0f * Scale;
	if (!RaceHudWidget)
	{
		// Panel, top left: mode and time, place, lives.
		float Y = 20.0f * Scale;
		DrawRect(FLinearColor(0.0f, 0.0f, 0.0f, 0.45f), X - 10.0f * Scale, Y - 6.0f * Scale, 360.0f * Scale, (bBots ? 100.0f : 76.0f) * Scale);
		DrawText(FString::Printf(TEXT("%s   %s"), bBots ? TEXT("PELOT\u00C3O 15") : TEXT("EXPEDI\u00C7\u00C3O SOLO"), *HudRaceClock(Race->GetRaceTime())), White, X, Y,
			nullptr, 1.3f * Scale);
		Y += 26.0f * Scale;
		if (bBots)
		{
			int32 Alive = 0;
			for (const FEXRacer& Racer : Standings)
			{
				Alive += Racer.bOut ? 0 : 1;
			}
			DrawText(FString::Printf(TEXT("POSI\u00C7\u00C3O %d / %d    em prova: %d"), Race->GetPlayerPlace(), Standings.Num(), Alive), White, X, Y,
				nullptr, 1.1f * Scale);
			Y += 24.0f * Scale;
		}
		DrawText(TEXT("VIDAS"), White, X, Y, nullptr, 1.1f * Scale);
		for (int32 Life = 0; Life < Craft->GetMaxLives(); ++Life)
		{
			DrawRect(Life < Craft->GetLives() ? FLinearColor(0.3f, 1.0f, 0.4f) : FLinearColor(0.25f, 0.25f, 0.25f, 0.8f),
				X + (70.0f + Life * 26.0f) * Scale, Y + 3.0f * Scale, 20.0f * Scale, 14.0f * Scale);
		}

		DrawGauges(Craft, Scale);
		DrawQuickSlots(Craft, Scale);

	}
	const float Mid = Canvas->ClipX * 0.5f;
	auto Centred = [this, Mid](const FString& Text, const FLinearColor& Colour, float AtY, float TextScale)
	{
		float W = 0.0f, H = 0.0f;
		GetTextSize(Text, W, H, nullptr, TextScale);
		DrawRect(FLinearColor(0.03f, 0.02f, 0.01f, 0.6f), Mid - W * 0.5f - 12.0f, AtY - 4.0f, W + 24.0f, H + 8.0f);
		DrawText(Text, Colour, Mid - W * 0.5f, AtY, nullptr, TextScale);
	};
	// Countdown: 3, 2, 1, VAI! (the race widget shows the start lights instead)
	if (Race->GetCountdown() > 0.0f && !RaceHudWidget)
	{
		const int32 Count = FMath::CeilToInt(Race->GetCountdown() - 1.0f);
		DrawText(Count > 0 ? FString::FromInt(Count) : FString(TEXT("VAI!")), Count > 0 ? FLinearColor(1.0f, 0.85f, 0.2f)
			: FLinearColor(0.3f, 1.0f, 0.4f), Mid - 40.0f * Scale, Canvas->ClipY * 0.3f, nullptr, 4.0f * Scale);
	}
	// What the craft is doing with its consumables, fuel and heat (under the guide arrow).
	float ToastY = 150.0f * Scale;
	const int32 LastSlot = Craft->GetLastQuickSlot();
	if (LastSlot >= 0 && Now - Craft->GetLastQuickTime() < 2.0f && Craft->GetQuickSlots().IsValidIndex(LastSlot))
	{
		const EXMeta::FConsumableDef& Def = EXMeta::Consumable(static_cast<EEXConsumable>(Craft->GetQuickSlots()[LastSlot].Kind));
		Centred(FString::Printf(TEXT("%s  \u00B7  %s"), *FString(Def.Name).ToUpper(), Def.Effect), Def.Colour, ToastY, 1.2f * Scale);
		ToastY += 30.0f * Scale;
	}
	if (Craft->GetRepairProgress() >= 0.0f)
	{
		Centred(FString::Printf(TEXT("A REPARAR  %d%%  \u00B7  +1 VIDA"), FMath::RoundToInt(Craft->GetRepairProgress() * 100.0f)),
			FLinearColor(0.48f, 0.88f, 0.54f), ToastY, 1.1f * Scale);
		ToastY += 28.0f * Scale;
	}
	if (Craft->IsOverheated())
	{
		const float Blink = 0.6f + 0.4f * FMath::Sin(Now * 10.0f);
		Centred(TEXT("SOBREAQUECIDA  \u00B7  SEM NITRO AT\u00C9 ARREFECER"), FLinearColor(1.0f, 0.25f * Blink, 0.1f), ToastY, 1.2f * Scale);
		ToastY += 30.0f * Scale;
	}
	if (Craft->GetFuel() <= 0.0f)
	{
		Centred(TEXT("SEM COMBUST\u00CDVEL  \u00B7  METADE DA VELOCIDADE"), Red, ToastY, 1.2f * Scale);
		ToastY += 30.0f * Scale;
	}
	else if (Craft->GetFuel() < 15.0f)
	{
		Centred(TEXT("COMBUST\u00CDVEL BAIXO"), FLinearColor(1.0f, 0.71f, 0.28f), ToastY, 1.0f * Scale);
		ToastY += 26.0f * Scale;
	}
	if (Craft->GetStabilizerLeft() > 0.0f)
	{
		Centred(FString::Printf(TEXT("ESTABILIZADOR  %.0f s"), Craft->GetStabilizerLeft()), FLinearColor(0.79f, 0.61f, 1.0f), ToastY, 1.0f * Scale);
	}
	// A life lost: red flash.
	const float SinceHit = Now - Craft->GetLastHitTime();
	if (Craft->GetLastHitTime() >= 0.0f && SinceHit < 1.5f && !Craft->IsEliminated())
	{
		DrawRect(FLinearColor(1.0f, 0.0f, 0.0f, 0.25f * (1.0f - SinceHit / 1.5f)), 0.0f, 0.0f, Canvas->ClipX, Canvas->ClipY);
		DrawText(TEXT("-1 VIDA"), Red, Mid - 60.0f * Scale, Canvas->ClipY * 0.36f, nullptr, 2.4f * Scale);
	}
	if (Craft->IsEliminated() && !Race->IsOver())
	{
		DrawText(TEXT("Enter / X: ver o resultado"), FLinearColor(1.0f, 0.85f, 0.6f), Mid - 120.0f * Scale, Canvas->ClipY * 0.36f + 44.0f * Scale, nullptr, 1.2f * Scale);
		DrawText(TEXT("DESTRU\u00CDDA - AT\u00C9 3 M\u00D3DULOS V\u00C3O PARA QUEM EXTRAIR"), Red, Mid - 330.0f * Scale, Canvas->ClipY * 0.36f, nullptr, 1.8f * Scale);
	}
	// Messages of the last 6 s (left, under the panel).
	float FeedY = (RaceHudWidget ? 128.0f : (bBots ? 130.0f : 106.0f)) * Scale;
	for (const TPair<float, FString>& Line : Race->GetFeed())
	{
		if (Race->GetRaceTime() - Line.Key < 6.0f || Race->GetCountdown() > 0.0f)
		{
			DrawText(Line.Value, FLinearColor(1.0f, 0.9f, 0.6f), X, FeedY, nullptr, 1.0f * Scale);
			FeedY += 20.0f * Scale;
		}
	}
	// Past the line, before the results: the finish banner, and the results come on their own (or with Enter / X).
	if (!Race->IsOver() && Race->IsPlayerDone() && !Craft->IsEliminated())
	{
		DrawRect(FLinearColor(0.0f, 0.0f, 0.0f, 0.55f), Mid - 330.0f * Scale, Canvas->ClipY * 0.30f, 660.0f * Scale, 120.0f * Scale);
		DrawText(FString::Printf(TEXT("META!   %s   \u00B7   %d.\u00BA LUGAR"), *HudRaceClock(Race->GetPlayerDoneTime()), Race->GetPlayerPlace()),
			FLinearColor(0.3f, 1.0f, 0.4f), Mid - 300.0f * Scale, Canvas->ClipY * 0.30f + 18.0f * Scale, nullptr, 2.0f * Scale);
		DrawText(TEXT("Enter / X: ver o esp\u00F3lio e os resultados"), FLinearColor(1.0f, 0.85f, 0.6f), Mid - 210.0f * Scale, Canvas->ClipY * 0.30f + 78.0f * Scale, nullptr, 1.2f * Scale);
	}
	// The extraction: who reached B (EXTRACTED), who was destroyed (up to three of its modules are the pool) and who
	// was still on the way; then what the player won and lost.
	if (Race->IsOver() && !ResultsWidget)
	{
		const TArray<FString>& News = Race->GetPlayerNews();
		const float W = 700.0f * Scale;
		const float Row = 22.0f * Scale;
		const int32 Lines = Standings.Num() + 4 + News.Num();
		float TY = Canvas->ClipY * 0.5f - Lines * Row * 0.5f;
		const float Left = Mid - W * 0.5f;
		DrawRect(FLinearColor(0.0f, 0.0f, 0.0f, 0.78f), Left, TY - 10.0f * Scale, W, Lines * Row + 20.0f * Scale);
		DrawText(FString::Printf(TEXT("EXTRA\u00C7\u00C3O   \u00B7   esp\u00F3lio dos destru\u00EDdos: %d STARDUST em pe\u00E7as"), Race->GetPool()),
			FLinearColor(1.0f, 0.55f, 0.2f), Left + 16.0f * Scale, TY, nullptr, 1.3f * Scale);
		TY += Row * 1.5f;
		static const TCHAR* const StateNames[4] = { TEXT("-"), TEXT("EXTRACTED"), TEXT("DESTROYED"), TEXT("STRANDED") };
		for (int32 Place = 0; Place < Standings.Num(); ++Place)
		{
			const FEXRacer& Racer = Standings[Place];
			const int32 State = FMath::Clamp<int32>(Racer.State, 0, 3);
			const FLinearColor Colour = Racer.bPlayer ? FLinearColor(0.3f, 1.0f, 0.4f) : (State == 1 ? White : Grey);
			const FString Result = Racer.bFinished ? HudRaceClock(Racer.FinishTime)
				: (Racer.bOut ? FString::Printf(TEXT("km %.1f"), Racer.OutAtM / 1000.0f) : FString(TEXT("a caminho")));
			DrawText(FString::Printf(TEXT("%d"), Place + 1), Colour, Left + 16.0f * Scale, TY, nullptr, 1.0f * Scale);
			DrawText(Racer.Name, Colour, Left + 56.0f * Scale, TY, nullptr, 1.0f * Scale);
			DrawText(Result, Colour, Left + 250.0f * Scale, TY, nullptr, 1.0f * Scale);
			DrawText(StateNames[State], State == 2 ? Red : Colour, Left + 380.0f * Scale, TY, nullptr, 1.0f * Scale);
			const FString Money = State == 1 ? FString::Printf(TEXT("+%d%s"), Racer.Reward, Racer.Won.Num() > 0 ? *FString::Printf(TEXT("  +%d pe\u00E7as"), Racer.Won.Num()) : TEXT(""))
				: (State == 2 && Racer.LostValue > 0 ? FString::Printf(TEXT("-%d em pe\u00E7as"), Racer.LostValue) : FString());
			DrawText(Money, State == 2 ? Red : Colour, Left + 520.0f * Scale, TY, nullptr, 1.0f * Scale);
			TY += Row;
		}
		TY += Row * 0.5f;
		for (const FString& Line : News)
		{
			DrawText(Line, FLinearColor(0.48f, 0.88f, 0.54f), Left + 16.0f * Scale, TY, nullptr, 1.05f * Scale);
			TY += Row;
		}
		DrawText(TEXT("Enter / X: voltar ao menu"), FLinearColor(1.0f, 0.85f, 0.6f), Left + 16.0f * Scale, TY, nullptr, 1.1f * Scale);
	}
}

void AEXHud::DrawGauges(const AEXHoverCraft* Craft, float Scale)
{
	// Bottom left: the speed, then the nitro, the heat and the fuel (Docs/MODULOS.md sec. 6).
	const float GX = 24.0f * Scale;
	const float GW = 300.0f * Scale;
	const float GY = Canvas->ClipY - 150.0f * Scale;
	DrawRect(FLinearColor(0.03f, 0.02f, 0.01f, 0.6f), GX - 10.0f * Scale, GY - 8.0f * Scale, GW + 20.0f * Scale, 132.0f * Scale);
	DrawRect(FLinearColor(0.92f, 0.34f, 0.10f), GX - 10.0f * Scale, GY - 8.0f * Scale, 3.0f * Scale, 132.0f * Scale);
	DrawText(FString::FromInt(FMath::RoundToInt(Craft->GetSpeedKmh())), FLinearColor::White, GX, GY - 4.0f * Scale, nullptr, 2.6f * Scale);
	DrawText(TEXT("KM/H"), FLinearColor(0.66f, 0.55f, 0.42f), GX + 118.0f * Scale, GY + 20.0f * Scale, nullptr, 1.0f * Scale);
	const float Blink = 0.6f + 0.4f * FMath::Sin(GetWorld()->GetTimeSeconds() * 10.0f);
	struct FGauge
	{
		const TCHAR* Label;
		float Value;
		FLinearColor Colour;
	};
	const float Heat = Craft->GetHeat();
	const FGauge Gauges[3] = {
		{ TEXT("NITRO"), Craft->GetNitro() * 100.0f, FLinearColor(1.0f, 0.5f, 0.15f) },
		{ TEXT("CALOR"), Heat, Craft->IsOverheated() ? FLinearColor(1.0f, 0.15f * Blink, 0.08f) : FMath::Lerp(FLinearColor(1.0f, 0.8f, 0.3f), FLinearColor(1.0f, 0.25f, 0.12f), Heat / 100.0f) },
		{ TEXT("COMBUST\u00CDVEL"), Craft->GetFuel(), Craft->GetFuel() < 15.0f ? FLinearColor(1.0f, 0.3f, 0.2f) : FLinearColor(0.42f, 0.86f, 0.5f) },
	};
	const float BarX = GX + 110.0f * Scale;
	const float BarW = GW - 160.0f * Scale;
	for (int32 Index = 0; Index < 3; ++Index)
	{
		const float RowY = GY + (60.0f + Index * 22.0f) * Scale;
		DrawText(Gauges[Index].Label, FLinearColor(0.66f, 0.55f, 0.42f), GX, RowY - 2.0f * Scale, nullptr, 0.8f * Scale);
		DrawRect(FLinearColor(1.0f, 1.0f, 1.0f, 0.12f), BarX, RowY, BarW, 8.0f * Scale);
		DrawRect(Gauges[Index].Colour, BarX, RowY, BarW * FMath::Clamp(Gauges[Index].Value / 100.0f, 0.0f, 1.0f), 8.0f * Scale);
		DrawText(FString::Printf(TEXT("%d"), FMath::RoundToInt(Gauges[Index].Value)), FLinearColor::White, BarX + BarW + 10.0f * Scale, RowY - 3.0f * Scale,
			nullptr, 0.85f * Scale);
	}
}

void AEXHud::DrawQuickSlots(const AEXHoverCraft* Craft, float Scale)
{
	// Bottom right: the four quick slots as a cross, like the d-pad (1 up, 2 down, 3 left, 4 right), the key in a corner.
	const TArray<FEXQuickSlot>& Slots = Craft->GetQuickSlots();
	const float Size = 62.0f * Scale;
	const float Gap = 6.0f * Scale;
	const FVector2D Centre(Canvas->ClipX - Size * 1.5f - Gap - 28.0f * Scale, Canvas->ClipY - Size * 1.5f - Gap - 28.0f * Scale);
	const FVector2D Offsets[EXMeta::QuickSlots] = { FVector2D(0.0f, -1.0f), FVector2D(0.0f, 1.0f), FVector2D(-1.0f, 0.0f), FVector2D(1.0f, 0.0f) };
	const float ArrowDeg[EXMeta::QuickSlots] = { 0.0f, 180.0f, -90.0f, 90.0f };
	const float Now = GetWorld()->GetTimeSeconds();
	for (int32 Slot = 0; Slot < EXMeta::QuickSlots; ++Slot)
	{
		const FEXQuickSlot Quick = Slots.IsValidIndex(Slot) ? Slots[Slot] : FEXQuickSlot();
		const EEXConsumable Kind = static_cast<EEXConsumable>(Quick.Kind);
		const EXMeta::FConsumableDef& Def = EXMeta::Consumable(Kind);
		const bool bHas = Kind != EEXConsumable::None && Quick.Count > 0;
		const bool bRecent = Craft->GetLastQuickSlot() == Slot && Now - Craft->GetLastQuickTime() < 0.6f;
		const FVector2D TopLeft = Centre + Offsets[Slot] * (Size + Gap) - FVector2D(Size * 0.5f, Size * 0.5f);
		DrawRect(bRecent ? FLinearColor(Def.Colour.R, Def.Colour.G, Def.Colour.B, 0.45f) : FLinearColor(0.03f, 0.02f, 0.01f, bHas ? 0.66f : 0.4f),
			TopLeft.X, TopLeft.Y, Size, Size);
		const FLinearColor Edge = bHas ? FLinearColor(Def.Colour.R, Def.Colour.G, Def.Colour.B, 0.8f) : FLinearColor(1.0f, 1.0f, 1.0f, 0.2f);
		DrawLine(TopLeft.X, TopLeft.Y, TopLeft.X + Size, TopLeft.Y, Edge, 1.5f);
		DrawLine(TopLeft.X, TopLeft.Y + Size, TopLeft.X + Size, TopLeft.Y + Size, Edge, 1.5f);
		DrawLine(TopLeft.X, TopLeft.Y, TopLeft.X, TopLeft.Y + Size, Edge, 1.5f);
		DrawLine(TopLeft.X + Size, TopLeft.Y, TopLeft.X + Size, TopLeft.Y + Size, Edge, 1.5f);
		DrawText(FString::FromInt(Slot + 1), FLinearColor::White, TopLeft.X + 5.0f * Scale, TopLeft.Y + 3.0f * Scale, nullptr, 0.9f * Scale);
		DrawArrow(FVector2D(TopLeft.X + Size - 11.0f * Scale, TopLeft.Y + 11.0f * Scale), ArrowDeg[Slot], 6.0f * Scale, FLinearColor(1.0f, 0.48f, 0.23f));
		if (!bHas)
		{
			DrawText(TEXT("vazio"), FLinearColor(1.0f, 1.0f, 1.0f, 0.35f), TopLeft.X + 12.0f * Scale, TopLeft.Y + Size * 0.5f - 6.0f * Scale, nullptr, 0.75f * Scale);
			continue;
		}
		// A gem in the consumable's colour, its short name and the count.
		DrawRect(Def.Colour, TopLeft.X + Size * 0.5f - 8.0f * Scale, TopLeft.Y + 16.0f * Scale, 16.0f * Scale, 16.0f * Scale);
		DrawText(FString(Def.Id).ToUpper(), FLinearColor(0.95f, 0.9f, 0.8f), TopLeft.X + 5.0f * Scale, TopLeft.Y + Size - 18.0f * Scale, nullptr, 0.68f * Scale);
		DrawText(FString::Printf(TEXT("x%d"), Quick.Count), FLinearColor::White, TopLeft.X + Size - 20.0f * Scale, TopLeft.Y + 34.0f * Scale, nullptr, 0.85f * Scale);
	}
}
