#include "UI/EXHud.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Flight/EXHoverCraft.h"

namespace
{
	constexpr float MapWindowM = 1600.0f;  // metres shown across the minimap
	constexpr int32 AheadSamples = 30;     // route samples are 5 m apart: the arrow aims ~150 m ahead
}

void AEXHud::DrawHUD()
{
	Super::DrawHUD();
	const AEXHoverCraft* Craft = Cast<AEXHoverCraft>(GetOwningPawn());
	if (!Craft || !Canvas || Craft->GetMapRoute().Num() < AheadSamples * 2)
	{
		return;
	}
	const TArray<FVector2D>& Route = Craft->GetMapRoute();
	const int32 Index = Craft->GetRouteIndex();
	const FVector Location = Craft->GetActorLocation();
	const FVector2D Here(Location.X / 100.0f, Location.Y / 100.0f);
	FVector2D Forward(Craft->GetHeading());
	Forward = Forward.GetSafeNormal();

	DrawMinimap(Route, Here, Forward, Index);

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

void AEXHud::DrawMinimap(const TArray<FVector2D>& Route, const FVector2D& Here, const FVector2D& Forward, int32 Index)
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
