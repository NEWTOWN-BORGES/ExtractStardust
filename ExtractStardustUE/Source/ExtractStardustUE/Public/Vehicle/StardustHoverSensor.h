#pragma once

#include "CoreMinimal.h"
#include "Vehicle/StardustCraftTypes.h"
#include "StardustHoverSensor.generated.h"

UENUM(BlueprintType)
enum class EStardustSurface : uint8
{
	Sand,
	DeepSand,
	Slickrock,
	Gravel,
	Rock
};

USTRUCT(BlueprintType)
struct FStardustSurfaceTraits
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Surface")
	float Grip = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Surface")
	float TopSpeed = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Surface")
	float Drag = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Surface")
	float Shake = 0.08f;

	static FStardustSurfaceTraits ForSurface(EStardustSurface Surface);
	static FStardustSurfaceTraits Blend(const FStardustSurfaceTraits& A, const FStardustSurfaceTraits& B, float Alpha);
};

struct FStardustHoverProbe
{
	FVector LocalPositionM = FVector::ZeroVector;
	float Weight = 1.0f;
	bool bHit = false;
	float HeightM = 0.0f;
	FHitResult Hit;
	EStardustSurface Surface = EStardustSurface::Sand;
};

struct FStardustHoverState
{
	FStardustHoverProbe Probes[5];
	int32 Hits = 0;
	float HeightM = TNumericLimits<float>::Infinity();
	FVector NormalRaw = FVector::UpVector;
	FVector NormalAhead = FVector::UpVector;
	bool bAheadHit = false;
	FVector Normal = FVector::UpVector;
	FVector GroundPointCm = FVector::ZeroVector;
	FVector AheadOriginCm = FVector::ZeroVector;
	FVector AheadPointCm = FVector::ZeroVector;
	FStardustSurfaceTraits Traits;
	EStardustSurface Dominant = EStardustSurface::Sand;
};

class FStardustHoverSensor
{
public:
	FStardustHoverSensor();

	void Reset(const FVector& Up);
	void Sample(UWorld* World, const FVector& PositionCm, const FQuat& Rotation, const FVector& VelocityCmPerSecond,
		const FStardustCraftTuning& Tuning, float DeltaSeconds, const AActor* IgnoredActor);

	const FStardustHoverState& GetState() const { return State; }

private:
	FStardustHoverState State;
	float SurfaceWeights[5] = {};

	static EStardustSurface ReadSurface(const FHitResult& Hit);
	static FVector SlerpNormals(const FVector& From, const FVector& To, float Alpha);
	static float Damp(float Lambda, float DeltaSeconds);
};
