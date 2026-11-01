#include "UI/EXRouteMapWidget.h"

#include "Rendering/DrawElements.h"
#include "UI/EXUiStyle.h"

void UEXRouteMapWidget::SetRoute(const TArray<FVector2D>& RouteM)
{
	Points.Reset();
	if (RouteM.Num() < 2)
	{
		return;
	}
	double MinX = RouteM[0].X, MaxX = RouteM[0].X, MinY = RouteM[0].Y, MaxY = RouteM[0].Y;
	for (const FVector2D& Point : RouteM)
	{
		MinX = FMath::Min(MinX, Point.X);
		MaxX = FMath::Max(MaxX, Point.X);
		MinY = FMath::Min(MinY, Point.Y);
		MaxY = FMath::Max(MaxY, Point.Y);
	}
	// North up: the maps flip Blender's y into Unreal's Y, so Unreal X is east and Y grows south, like the screen.
	const double Span = FMath::Max3(MaxX - MinX, MaxY - MinY, 1.0);
	Extent = FVector2f(static_cast<float>((MaxX - MinX) / Span), static_cast<float>((MaxY - MinY) / Span));
	const int32 Step = FMath::Max(1, RouteM.Num() / 400);
	for (int32 Index = 0; Index < RouteM.Num(); Index += Step)
	{
		Points.Add(FVector2f(static_cast<float>((RouteM[Index].X - MinX) / Span), static_cast<float>((RouteM[Index].Y - MinY) / Span)));
	}
	const FVector2D& Last = RouteM.Last();
	Points.Add(FVector2f(static_cast<float>((Last.X - MinX) / Span), static_cast<float>((Last.Y - MinY) / Span)));
}

void UEXRouteMapWidget::SetRadar(const TArray<FVector2D>& RouteM, float WindowM)
{
	bRadar = true;
	RadarRoute = RouteM;
	RadarWindowM = FMath::Max(200.0f, WindowM);
	SetClipping(EWidgetClipping::ClipToBounds);
}

void UEXRouteMapWidget::SetRadarView(const FVector2D& HereM, const FVector2D& Forward, int32 RouteIndex, const TArray<FVector2D>& RivalsM,
	const TArray<FVector2D>& GatesM, int32 GatesPassed, int32 MissedGate)
{
	RadarHere = HereM;
	RadarForward = Forward.IsNearlyZero() ? FVector2D(1.0f, 0.0f) : Forward.GetSafeNormal();
	RadarIndex = RouteIndex;
	RadarRivals = RivalsM;
	RadarGates = GatesM;
	RadarPassed = GatesPassed;
	RadarMissed = MissedGate;
	Invalidate(EInvalidateWidgetReason::Paint);
}

int32 UEXRouteMapWidget::PaintRadar(const FGeometry& Geometry, FSlateWindowElementList& Out, int32 Layer) const
{
	const FVector2f Size(static_cast<float>(Geometry.GetLocalSize().X), static_cast<float>(Geometry.GetLocalSize().Y));
	const FVector2f Centre(Size.X * 0.5f, Size.Y * 0.62f);          // the craft a little low: more of the road ahead
	const float PxPerM = Size.X / RadarWindowM;
	const FVector2D Right(-RadarForward.Y, RadarForward.X);
	auto ToBox = [&](const FVector2D& P)
	{
		const FVector2D D = P - RadarHere;
		return Centre + FVector2f(static_cast<float>(D | Right), static_cast<float>(-(D | RadarForward))) * PxPerM;
	};
	const FPaintGeometry Paint = Geometry.ToPaintGeometry();
	const int32 N = RadarRoute.Num();
	if (N > 2)
	{
		// The road behind (dim) and ahead (bright), each as a wide soft glow, the track and a bright core.
		const int32 Back = FMath::RoundToInt(RadarWindowM * 0.6f / 5.0f);
		const int32 Ahead = FMath::RoundToInt(RadarWindowM * 1.0f / 5.0f);
		TArray<FVector2f> Behind, Front;
		for (int32 I = FMath::Max(0, RadarIndex - Back); I <= RadarIndex && I < N; I += 2)
		{
			Behind.Add(ToBox(RadarRoute[I]));
		}
		for (int32 I = FMath::Clamp(RadarIndex, 0, N - 1); I < N && I <= RadarIndex + Ahead; I += 2)
		{
			Front.Add(ToBox(RadarRoute[I]));
		}
		if (Behind.Num() > 1)
		{
			FSlateDrawElement::MakeLines(Out, Layer + 1, Paint, Behind, ESlateDrawEffect::None, FLinearColor(0.15f, 0.55f, 0.9f, 0.35f), true, 7.0f);
		}
		if (Front.Num() > 1)
		{
			FSlateDrawElement::MakeLines(Out, Layer + 1, Paint, Front, ESlateDrawEffect::None, FLinearColor(0.2f, 0.75f, 1.0f, 0.22f), true, 16.0f);
			FSlateDrawElement::MakeLines(Out, Layer + 2, Paint, Front, ESlateDrawEffect::None, FLinearColor(0.25f, 0.82f, 1.0f, 0.85f), true, 7.0f);
			FSlateDrawElement::MakeLines(Out, Layer + 3, Paint, Front, ESlateDrawEffect::None, FLinearColor(0.85f, 0.97f, 1.0f, 1.0f), true, 2.2f);
		}
	}
	auto Ring = [&](const FVector2f& At, float Radius, const FLinearColor& Colour, float Thick, int32 L)
	{
		TArray<FVector2f> Circle;
		for (int32 K = 0; K <= 16; ++K)
		{
			const float A = K * 2.0f * PI / 16.0f;
			Circle.Add(At + FVector2f(FMath::Cos(A), FMath::Sin(A)) * Radius);
		}
		FSlateDrawElement::MakeLines(Out, L, Paint, Circle, ESlateDrawEffect::None, Colour, true, Thick);
	};
	// The checkpoints: passed gold, the next one big and bright (red while it is missed), the rest blue; B, the finish.
	for (int32 G = 0; G < RadarGates.Num(); ++G)
	{
		const FVector2f At = ToBox(RadarGates[G]);
		const bool bNext = G == RadarPassed;
		const bool bMissed = RadarMissed == G + 1;
		const FLinearColor C = bMissed ? FLinearColor(1.0f, 0.25f, 0.15f) : (G < RadarPassed ? FLinearColor(1.0f, 0.78f, 0.25f)
			: (bNext ? FLinearColor(0.6f, 0.95f, 1.0f) : FLinearColor(0.25f, 0.55f, 1.0f)));
		Ring(At, bNext || bMissed ? 9.0f : 6.0f, C, bNext || bMissed ? 3.5f : 3.0f, Layer + 4);
		Ring(At, 2.5f, C, 3.0f, Layer + 4);
	}
	if (N > 2)
	{
		const FVector2f B = ToBox(RadarRoute.Last());
		for (int32 K = 0; K < 4; ++K)
		{
			const FVector2f O(static_cast<float>(K % 2) * 6.0f - 6.0f, static_cast<float>(K / 2) * 6.0f - 6.0f);
			TArray<FVector2f> Square = { B + O, B + O + FVector2f(6.0f, 0.0f), B + O + FVector2f(6.0f, 6.0f), B + O + FVector2f(0.0f, 6.0f), B + O };
			FSlateDrawElement::MakeLines(Out, Layer + 5, Paint, Square, ESlateDrawEffect::None, (K == 0 || K == 3) ? FLinearColor::White
				: FLinearColor(0.05f, 0.05f, 0.08f), true, 6.0f);
		}
	}
	// The rivals: warm dots.
	for (const FVector2D& R : RadarRivals)
	{
		Ring(ToBox(R), 3.0f, FLinearColor(1.0f, 0.45f, 0.2f), 4.0f, Layer + 6);
	}
	// The craft: a white arrowhead pointing up (the map turns with it), with a soft halo.
	Ring(Centre, 13.0f, FLinearColor(0.4f, 0.85f, 1.0f, 0.25f), 6.0f, Layer + 6);
	const TArray<FVector2f> Arrow = { Centre + FVector2f(0.0f, -11.0f), Centre + FVector2f(8.0f, 8.0f), Centre + FVector2f(0.0f, 4.0f),
		Centre + FVector2f(-8.0f, 8.0f), Centre + FVector2f(0.0f, -11.0f) };
	FSlateDrawElement::MakeLines(Out, Layer + 7, Paint, Arrow, ESlateDrawEffect::None, FLinearColor::White, true, 3.0f);
	return Layer + 7;
}

int32 UEXRouteMapWidget::NativePaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	const int32 BaseLayer = Super::NativePaint(Args, AllottedGeometry, MyCullingRect, OutDrawElements, LayerId, InWidgetStyle, bParentEnabled);
	if (bRadar)
	{
		return PaintRadar(AllottedGeometry, OutDrawElements, BaseLayer);
	}
	if (Points.Num() < 2)
	{
		return BaseLayer;
	}
	const FVector2f BoxSize(static_cast<float>(AllottedGeometry.GetLocalSize().X), static_cast<float>(AllottedGeometry.GetLocalSize().Y));
	const float Margin = 20.0f;
	const float Scale = FMath::Max(1.0f, FMath::Min((BoxSize.X - 2.0f * Margin) / FMath::Max(Extent.X, 0.01f),
		(BoxSize.Y - 2.0f * Margin) / FMath::Max(Extent.Y, 0.01f)));
	const FVector2f Offset = (BoxSize - Extent * Scale) * 0.5f;
	TArray<FVector2f> Line;
	Line.Reserve(Points.Num());
	for (const FVector2f& Point : Points)
	{
		Line.Add(Offset + Point * Scale);
	}
	// A dark under-stroke, the line in orange, then the ends: A (the start) a light diamond, B (the finish) an orange one.
	FSlateDrawElement::MakeLines(OutDrawElements, BaseLayer + 1, AllottedGeometry.ToPaintGeometry(), Line, ESlateDrawEffect::None,
		EXUi::Ink(0.9f), true, 6.0f);
	FSlateDrawElement::MakeLines(OutDrawElements, BaseLayer + 2, AllottedGeometry.ToPaintGeometry(), Line, ESlateDrawEffect::None,
		EXUi::Accent(), true, 3.0f);
	auto Marker = [&](const FVector2f& At, const FLinearColor& Colour, float Radius)
	{
		TArray<FVector2f> Diamond;
		Diamond.Add(At + FVector2f(0.0f, -Radius));
		Diamond.Add(At + FVector2f(Radius, 0.0f));
		Diamond.Add(At + FVector2f(0.0f, Radius));
		Diamond.Add(At + FVector2f(-Radius, 0.0f));
		Diamond.Add(At + FVector2f(0.0f, -Radius));
		FSlateDrawElement::MakeLines(OutDrawElements, BaseLayer + 3, AllottedGeometry.ToPaintGeometry(), Diamond, ESlateDrawEffect::None,
			Colour, true, 3.0f);
	};
	Marker(Line[0], EXUi::Fore(), 8.0f);
	Marker(Line.Last(), EXUi::AccentHot(), 8.0f);
	Marker(Line.Last(), EXUi::Fore(), 3.0f);
	return BaseLayer + 3;
}
