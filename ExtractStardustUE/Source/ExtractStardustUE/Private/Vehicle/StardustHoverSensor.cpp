#include "Vehicle/StardustHoverSensor.h"

#include "Engine/World.h"
#include "PhysicalMaterials/PhysicalMaterial.h"

FStardustSurfaceTraits FStardustSurfaceTraits::ForSurface(EStardustSurface Surface)
{
	FStardustSurfaceTraits Result;
	switch (Surface)
	{
	case EStardustSurface::DeepSand:
		Result.Grip = 0.78f;
		Result.TopSpeed = 0.84f;
		Result.Drag = 16.0f;
		Result.Shake = 0.15f;
		break;
	case EStardustSurface::Slickrock:
		Result.Grip = 1.08f;
		Result.TopSpeed = 1.03f;
		Result.Drag = 0.0f;
		Result.Shake = 0.05f;
		break;
	case EStardustSurface::Gravel:
		Result.Grip = 0.72f;
		Result.TopSpeed = 0.97f;
		Result.Drag = 3.0f;
		Result.Shake = 0.4f;
		break;
	case EStardustSurface::Rock:
		Result.Grip = 0.88f;
		Result.TopSpeed = 0.95f;
		Result.Drag = 4.0f;
		Result.Shake = 0.6f;
		break;
	default:
		Result.Grip = 1.0f;
		Result.TopSpeed = 1.0f;
		Result.Drag = 0.0f;
		Result.Shake = 0.08f;
		break;
	}
	return Result;
}

FStardustSurfaceTraits FStardustSurfaceTraits::Blend(const FStardustSurfaceTraits& A, const FStardustSurfaceTraits& B, float Alpha)
{
	FStardustSurfaceTraits Result;
	Result.Grip = FMath::Lerp(A.Grip, B.Grip, Alpha);
	Result.TopSpeed = FMath::Lerp(A.TopSpeed, B.TopSpeed, Alpha);
	Result.Drag = FMath::Lerp(A.Drag, B.Drag, Alpha);
	Result.Shake = FMath::Lerp(A.Shake, B.Shake, Alpha);
	return Result;
}

FStardustHoverSensor::FStardustHoverSensor()
{
	State.Probes[0].Weight = 1.0f;
	State.Probes[1].Weight = 1.0f;
	State.Probes[2].Weight = 1.0f;
	State.Probes[3].Weight = 1.0f;
	State.Probes[4].Weight = 2.0f;
}

void FStardustHoverSensor::Reset(const FVector& Up)
{
	State.Hits = 0;
	State.HeightM = TNumericLimits<float>::Infinity();
	State.Normal = Up.GetSafeNormal(SMALL_NUMBER, FVector::UpVector);
	State.NormalRaw = State.Normal;
	State.NormalAhead = State.Normal;
	State.bAheadHit = false;
}

float FStardustHoverSensor::Damp(float Lambda, float DeltaSeconds)
{
	return 1.0f - FMath::Exp(-Lambda * DeltaSeconds);
}

FVector FStardustHoverSensor::SlerpNormals(const FVector& From, const FVector& To, float Alpha)
{
	const FVector A = From.GetSafeNormal(SMALL_NUMBER, FVector::UpVector);
	const FVector B = To.GetSafeNormal(SMALL_NUMBER, A);
	const FQuat Delta = FQuat::FindBetweenNormals(A, B);
	return FQuat::Slerp(FQuat::Identity, Delta, FMath::Clamp(Alpha, 0.0f, 1.0f)).RotateVector(A).GetSafeNormal(SMALL_NUMBER, A);
}

EStardustSurface FStardustHoverSensor::ReadSurface(const FHitResult& Hit)
{
	const EPhysicalSurface SurfaceType = Hit.PhysMaterial.IsValid()
		? UPhysicalMaterial::DetermineSurfaceType(Hit.PhysMaterial.Get())
		: SurfaceType_Default;

	switch (SurfaceType)
	{
	case SurfaceType1: return EStardustSurface::DeepSand;
	case SurfaceType2: return EStardustSurface::Slickrock;
	case SurfaceType3: return EStardustSurface::Gravel;
	case SurfaceType4: return EStardustSurface::Rock;
	default: return EStardustSurface::Sand;
	}
}

void FStardustHoverSensor::Sample(UWorld* World, const FVector& PositionCm, const FQuat& Rotation,
	const FVector& VelocityCmPerSecond, const FStardustCraftTuning& Tuning, float DeltaSeconds, const AActor* IgnoredActor)
{
	if (!World)
	{
		return;
	}

	constexpr float CmPerMeter = 100.0f;
	constexpr float RayLiftM = 1.0f;
	const FVector Up = Rotation.RotateVector(FVector::UpVector);
	const FVector LocalProbes[5] =
	{
		FVector(Tuning.ProbeHalfLengthM, 0.0, 0.0),
		FVector(-Tuning.ProbeHalfLengthM, 0.0, 0.0),
		FVector(0.0, Tuning.ProbeHalfWidthM, 0.0),
		FVector(0.0, -Tuning.ProbeHalfWidthM, 0.0),
		FVector::ZeroVector
	};

	FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(StardustHoverProbe), true);
	if (IgnoredActor)
	{
		QueryParams.AddIgnoredActor(IgnoredActor);
	}

	FVector NormalSum = FVector::ZeroVector;
	FVector PointSum = FVector::ZeroVector;
	float HeightSum = 0.0f;
	float WeightSum = 0.0f;
	FMemory::Memzero(SurfaceWeights, sizeof(SurfaceWeights));
	State.Hits = 0;

	for (int32 Index = 0; Index < UE_ARRAY_COUNT(State.Probes); ++Index)
	{
		FStardustHoverProbe& Probe = State.Probes[Index];
		Probe.LocalPositionM = LocalProbes[Index];
		const FVector Start = PositionCm + Rotation.RotateVector(LocalProbes[Index] * CmPerMeter) + Up * RayLiftM * CmPerMeter;
		const FVector End = Start - Up * (RayLiftM + Tuning.HoverHeightM + Tuning.ProbeReachM) * CmPerMeter;
		Probe.bHit = World->LineTraceSingleByChannel(Probe.Hit, Start, End, ECC_GameTraceChannel1, QueryParams);
		if (!Probe.bHit)
		{
			continue;
		}

		Probe.HeightM = FVector::DotProduct(Start - Probe.Hit.ImpactPoint, Up) / CmPerMeter - RayLiftM;
		Probe.Surface = ReadSurface(Probe.Hit);
		const int32 SurfaceIndex = static_cast<int32>(Probe.Surface);
		SurfaceWeights[SurfaceIndex] += Probe.Weight;
		++State.Hits;
		HeightSum += Probe.HeightM * Probe.Weight;
		NormalSum += Probe.Hit.ImpactNormal * Probe.Weight;
		PointSum += Probe.Hit.ImpactPoint * Probe.Weight;
		WeightSum += Probe.Weight;
	}

	if (State.Hits > 0 && WeightSum > 0.0f)
	{
		State.HeightM = HeightSum / WeightSum;
		State.NormalRaw = NormalSum.GetSafeNormal(SMALL_NUMBER, Up);
		State.GroundPointCm = PointSum / WeightSum;
		FStardustSurfaceTraits MixedTraits;
		MixedTraits.Grip = 0.0f;
		MixedTraits.TopSpeed = 0.0f;
		MixedTraits.Drag = 0.0f;
		MixedTraits.Shake = 0.0f;
		float BestWeight = -1.0f;
		for (int32 SurfaceIndex = 0; SurfaceIndex < UE_ARRAY_COUNT(SurfaceWeights); ++SurfaceIndex)
		{
			const float Weight = SurfaceWeights[SurfaceIndex];
			if (Weight <= 0.0f)
			{
				continue;
			}
			const EStardustSurface Surface = static_cast<EStardustSurface>(SurfaceIndex);
			const FStardustSurfaceTraits Traits = FStardustSurfaceTraits::ForSurface(Surface);
			const float Fraction = Weight / WeightSum;
			MixedTraits.Grip += Traits.Grip * Fraction;
			MixedTraits.TopSpeed += Traits.TopSpeed * Fraction;
			MixedTraits.Drag += Traits.Drag * Fraction;
			MixedTraits.Shake += Traits.Shake * Fraction;
			if (Weight > BestWeight)
			{
				BestWeight = Weight;
				State.Dominant = Surface;
			}
		}
		State.Traits = FStardustSurfaceTraits::Blend(State.Traits, MixedTraits, Damp(12.0f, DeltaSeconds));
	}
	else
	{
		State.HeightM = TNumericLimits<float>::Infinity();
	}

	State.bAheadHit = false;
	const float SpeedMPerSecond = VelocityCmPerSecond.Size() / CmPerMeter;
	const FVector BaseNormal = State.Hits > 0 ? State.NormalRaw : Up;
	FVector Forward = FVector::VectorPlaneProject(Rotation.RotateVector(FVector::ForwardVector), BaseNormal);
	if (!Forward.IsNearlyZero() && State.Hits >= 2 && SpeedMPerSecond > 8.0f)
	{
		Forward.Normalize();
		const float LookM = FMath::Clamp(SpeedMPerSecond * Tuning.LookAheadTime, 4.0f, 26.0f);
		State.AheadOriginCm = PositionCm + BaseNormal * 40.0f;
		FHitResult AheadHit;
		if (World->LineTraceSingleByChannel(AheadHit, State.AheadOriginCm,
			State.AheadOriginCm + Forward * (LookM + 2.0f) * CmPerMeter, ECC_GameTraceChannel1, QueryParams)
			&& FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(AheadHit.ImpactNormal, BaseNormal), -1.0f, 1.0f))) < 70.0f)
		{
			State.bAheadHit = true;
			State.AheadPointCm = AheadHit.ImpactPoint;
			State.NormalAhead = AheadHit.ImpactNormal.GetSafeNormal(SMALL_NUMBER, BaseNormal);
		}
		else
		{
			const float LiftM = 2.5f + LookM * 0.18f;
			const FVector Start = PositionCm + Forward * LookM * CmPerMeter + BaseNormal * LiftM * CmPerMeter;
			const FVector End = Start - BaseNormal * (LiftM + Tuning.HoverHeightM + Tuning.ProbeReachM) * CmPerMeter;
			if (World->LineTraceSingleByChannel(AheadHit, Start, End, ECC_GameTraceChannel1, QueryParams)
				&& FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(AheadHit.ImpactNormal, BaseNormal), -1.0f, 1.0f))) < 70.0f)
			{
				State.bAheadHit = true;
				State.AheadOriginCm = Start;
				State.AheadPointCm = AheadHit.ImpactPoint;
				State.NormalAhead = AheadHit.ImpactNormal.GetSafeNormal(SMALL_NUMBER, BaseNormal);
			}
		}
	}

	FVector TargetNormal = BaseNormal;
	if (State.bAheadHit)
	{
		TargetNormal = (BaseNormal + State.NormalAhead * (0.8f * FMath::Clamp(SpeedMPerSecond / Tuning.TopSpeed, 0.0f, 1.0f))).GetSafeNormal(SMALL_NUMBER, BaseNormal);
	}
	const float NormalLambda = 1.0f / FMath::Max(1.0e-3f, Tuning.NormalSmoothing);
	State.Normal = SlerpNormals(State.Normal, TargetNormal, Damp(NormalLambda, DeltaSeconds));
}
