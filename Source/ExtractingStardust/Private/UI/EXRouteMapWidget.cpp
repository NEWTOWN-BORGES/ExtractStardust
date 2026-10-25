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

int32 UEXRouteMapWidget::NativePaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	const int32 BaseLayer = Super::NativePaint(Args, AllottedGeometry, MyCullingRect, OutDrawElements, LayerId, InWidgetStyle, bParentEnabled);
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
		EXUi::Rust(), true, 3.0f);
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
	Marker(Line[0], EXUi::Bone(), 8.0f);
	Marker(Line.Last(), EXUi::RustHot(), 8.0f);
	Marker(Line.Last(), EXUi::Bone(), 3.0f);
	return BaseLayer + 3;
}
