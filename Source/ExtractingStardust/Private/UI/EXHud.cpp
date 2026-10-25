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
	// The menu takes the mouse (its lines are clicked); the hangar and the race give it to the game.
	const int32 Wanted = bMenu ? 1 : 0;
	if (Wanted != InputScreen)
	{
		InputScreen = Wanted;
		if (bMenu)
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
	const FLinearColor Shield(0.35f, 0.65f, 1.0f);

	// Panel, top left: mode and time, place, lives, the cargo still on board.
	const float X = 24.0f * Scale;
	float Y = 20.0f * Scale;
	DrawRect(FLinearColor(0.0f, 0.0f, 0.0f, 0.45f), X - 10.0f * Scale, Y - 6.0f * Scale, 360.0f * Scale, (bBots ? 170.0f : 146.0f) * Scale);
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
	Y += 24.0f * Scale;
	DrawText(FString::Printf(TEXT("REPARA\u00C7\u00C3O x%d   (H / Quadrado)"), Craft->GetMedKits()), Craft->GetMedKits() > 0 ? White : Grey, X, Y,
		nullptr, 1.05f * Scale);
	Y += 22.0f * Scale;
	DrawText(FString::Printf(TEXT("SURGE x%d   (F / Cima)"), Craft->GetSurgeCharges()), Craft->GetSurgeCharges() > 0 ? White : Grey, X, Y,
		nullptr, 1.05f * Scale);
	Y += 22.0f * Scale;
	DrawText(FString::Printf(TEXT("ESCUDO x%d   (absorve o pr\u00F3ximo embate)"), Craft->GetShieldCharges()), Craft->GetShieldCharges() > 0 ? Shield : Grey,
		X, Y, nullptr, 1.05f * Scale);

	const float Mid = Canvas->ClipX * 0.5f;
	// Countdown: 3, 2, 1, VAI!
	if (Race->GetCountdown() > 0.0f)
	{
		const int32 Count = FMath::CeilToInt(Race->GetCountdown() - 1.0f);
		DrawText(Count > 0 ? FString::FromInt(Count) : FString(TEXT("VAI!")), Count > 0 ? FLinearColor(1.0f, 0.85f, 0.2f)
			: FLinearColor(0.3f, 1.0f, 0.4f), Mid - 40.0f * Scale, Canvas->ClipY * 0.3f, nullptr, 4.0f * Scale);
	}
	// A life lost: red flash. A shield that took the hit: blue flash.
	const float Now = GetWorld()->GetTimeSeconds();
	const float SinceHit = Now - Craft->GetLastHitTime();
	if (Craft->GetLastHitTime() >= 0.0f && SinceHit < 1.5f && !Craft->IsEliminated())
	{
		DrawRect(FLinearColor(1.0f, 0.0f, 0.0f, 0.25f * (1.0f - SinceHit / 1.5f)), 0.0f, 0.0f, Canvas->ClipX, Canvas->ClipY);
		DrawText(TEXT("-1 VIDA"), Red, Mid - 60.0f * Scale, Canvas->ClipY * 0.36f, nullptr, 2.4f * Scale);
	}
	const float SinceShield = Now - Craft->GetLastShieldTime();
	if (Craft->GetLastShieldTime() >= 0.0f && SinceShield < 1.2f)
	{
		DrawRect(FLinearColor(0.2f, 0.5f, 1.0f, 0.22f * (1.0f - SinceShield / 1.2f)), 0.0f, 0.0f, Canvas->ClipX, Canvas->ClipY);
		DrawText(TEXT("ESCUDO!"), Shield, Mid - 70.0f * Scale, Canvas->ClipY * 0.36f, nullptr, 2.4f * Scale);
	}
	if (Craft->IsEliminated() && !Race->IsOver())
	{
		DrawText(TEXT("DESTRU\u00CDDA - A TUA CARGA FICA PARA QUEM EXTRAIR"), Red, Mid - 330.0f * Scale, Canvas->ClipY * 0.36f, nullptr, 1.8f * Scale);
	}
	// Messages of the last 6 s (left, under the panel).
	float FeedY = (bBots ? 200.0f : 176.0f) * Scale;
	for (const TPair<float, FString>& Line : Race->GetFeed())
	{
		if (Race->GetRaceTime() - Line.Key < 6.0f || Race->GetCountdown() > 0.0f)
		{
			DrawText(Line.Value, FLinearColor(1.0f, 0.9f, 0.6f), X, FeedY, nullptr, 1.0f * Scale);
			FeedY += 20.0f * Scale;
		}
	}
	// The extraction: who reached B (EXTRACTED), who was destroyed (their cargo is the pool) and who was still on the way.
	if (Race->IsOver())
	{
		const float W = 660.0f * Scale;
		const float Row = 22.0f * Scale;
		const int32 Lines = Standings.Num() + 4;
		float TY = Canvas->ClipY * 0.5f - Lines * Row * 0.5f;
		const float Left = Mid - W * 0.5f;
		DrawRect(FLinearColor(0.0f, 0.0f, 0.0f, 0.75f), Left, TY - 10.0f * Scale, W, Lines * Row + 20.0f * Scale);
		DrawText(FString::Printf(TEXT("EXTRA\u00C7\u00C3O   \u00B7   esp\u00F3lio dos destru\u00EDdos: %d STARDUST"), Race->GetPool()), FLinearColor(1.0f, 0.55f, 0.2f),
			Left + 16.0f * Scale, TY, nullptr, 1.3f * Scale);
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
			DrawText(State == 1 ? FString::Printf(TEXT("+%d"), Racer.Reward) : (State == 2 ? FString::Printf(TEXT("-%d"), Racer.CargoValue) : FString()),
				State == 2 ? Red : Colour, Left + 540.0f * Scale, TY, nullptr, 1.0f * Scale);
			TY += Row;
		}
		TY += Row * 0.5f;
		DrawText(TEXT("Enter / X: voltar ao menu"), FLinearColor(1.0f, 0.85f, 0.6f), Left + 16.0f * Scale, TY, nullptr, 1.1f * Scale);
	}
}
