#include "Vehicle/StardustCraftTypes.h"

float FStardustCraftTuning::GetTurnRate(float Speed) const
{
	return FMath::Lerp(TurnRateLow, TurnRateHigh, FMath::Clamp(Speed / TopSpeed, 0.0f, 1.0f));
}

float FStardustCraftTuning::GetSpringK() const
{
	return FMath::Square(2.0f * PI * SpringHz);
}

float FStardustCraftTuning::GetSpringC() const
{
	return 2.0f * DampingRatio * 2.0f * PI * SpringHz;
}

float FStardustCraftTuning::GetAdhesion(float Speed) const
{
	const float Alpha = AdhesionFullSpeed > AdhesionMinSpeed
		? FMath::Clamp((Speed - AdhesionMinSpeed) / (AdhesionFullSpeed - AdhesionMinSpeed), 0.0f, 1.0f)
		: 1.0f;
	return Adhesion * Alpha * Alpha * (3.0f - 2.0f * Alpha);
}

float FStardustCraftTuning::GetGripFactor(float Speed) const
{
	const float NormalizedSpeed = Speed / GripSpeedRef;
	return FMath::Min(GripCap, GripBase + NormalizedSpeed * NormalizedSpeed);
}

float FStardustCraftTuning::GetCornerSpeed(float Curvature, float BankDegrees, float Margin) const
{
	if (Curvature < 1.0e-5f)
	{
		return TNumericLimits<float>::Max();
	}

	const float BankRadians = FMath::DegreesToRadians(FMath::Min(FMath::Abs(BankDegrees), 60.0f));
	const float BankAcceleration = Gravity * FMath::Tan(BankRadians);
	const float LateralAcceleration = GripLateralMax * Margin;
	const float CapSpeed = FMath::Sqrt((LateralAcceleration * GripCap + BankAcceleration) / Curvature);
	const float KneeSpeed = GripSpeedRef * FMath::Sqrt(FMath::Max(0.0f, GripCap - GripBase));
	if (CapSpeed >= KneeSpeed)
	{
		return CapSpeed;
	}

	const float CurvatureSquaredTerm = LateralAcceleration / (GripSpeedRef * GripSpeedRef);
	return Curvature > CurvatureSquaredTerm
		? FMath::Sqrt((LateralAcceleration * GripBase + BankAcceleration) / (Curvature - CurvatureSquaredTerm))
		: CapSpeed;
}
