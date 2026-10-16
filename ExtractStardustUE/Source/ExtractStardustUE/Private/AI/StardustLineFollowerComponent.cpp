#include "AI/StardustLineFollowerComponent.h"

#include "Course/StardustCourseComponent.h"
#include "Vehicle/StardustCraftMovementComponent.h"

UStardustLineFollowerComponent::UStardustLineFollowerComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

void UStardustLineFollowerComponent::BeginPlay()
{
	Super::BeginPlay();
	CurrentLaneU = LaneU;
	if (GetOwner())
	{
		CraftMovement = GetOwner()->FindComponentByClass<UStardustCraftMovementComponent>();
	}
}

void UStardustLineFollowerComponent::SetCourse(UStardustCourseComponent* NewCourse)
{
	Course = NewCourse;
	CurrentStation = INDEX_NONE;
	CurrentPathIndex = INDEX_NONE;
	DistanceM = 0.0f;
	RaceDistanceM = 0.0f;
}

float UStardustLineFollowerComponent::CurvatureAhead(int32 PathIndex, float CurrentDistanceM, float SpanM, float& OutBankDegrees) const
{
	OutBankDegrees = 0.0f;
	if (!Course || Course->GetCoursePathLengthM(PathIndex) <= 0.0f)
	{
		return 0.0f;
	}

	FStardustCoursePoint Start;
	FStardustCoursePoint End;
	if (!Course->SamplePathAtDistance(PathIndex, CurrentDistanceM, Start) || !Course->SamplePathAtDistance(PathIndex, CurrentDistanceM + SpanM, End))
	{
		return 0.0f;
	}
	OutBankDegrees = Start.BankDegrees;
	FVector StartTangent(Start.Tangent.X, Start.Tangent.Y, 0.0);
	FVector EndTangent(End.Tangent.X, End.Tangent.Y, 0.0);
	StartTangent = StartTangent.GetSafeNormal();
	EndTangent = EndTangent.GetSafeNormal();
	if (StartTangent.IsNearlyZero() || EndTangent.IsNearlyZero())
	{
		return 0.0f;
	}
	const float ActualSpanM = FMath::Max(1.0f, End.DistanceM - Start.DistanceM);
	return FMath::Acos(FMath::Clamp(FVector::DotProduct(StartTangent, EndTangent), -1.0, 1.0)) / ActualSpanM;
}

void UStardustLineFollowerComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (!Course || !CraftMovement || DeltaTime <= 0.0f || Course->CourseLengthM <= 0.0f || !GetOwner())
	{
		return;
	}

	const FVector PositionCm = GetOwner()->GetActorLocation();
	int32 LocatedPathIndex = INDEX_NONE;
	int32 LocatedStationIndex = INDEX_NONE;
	if (!Course->LocateCoursePath(PositionCm, CurrentPathIndex, CurrentStation, LocatedPathIndex, LocatedStationIndex))
	{
		return;
	}
	CurrentPathIndex = LocatedPathIndex;
	CurrentStation = LocatedStationIndex;
	const float StationDistanceM = Course->GetDistanceAtPathStation(CurrentPathIndex, CurrentStation);
	FStardustCoursePoint CurrentPoint;
	if (StationDistanceM < 0.0f || !Course->SamplePathAtDistance(CurrentPathIndex, StationDistanceM, CurrentPoint))
	{
		return;
	}
	const float PathEndDistanceM = Course->GetCoursePathLengthM(CurrentPathIndex);
	const float PathStartDistanceM = Course->GetDistanceAtPathStation(CurrentPathIndex, 0);
	DistanceM = FMath::Clamp(CurrentPoint.DistanceM + FVector::DotProduct(PositionCm - CurrentPoint.PositionCm, CurrentPoint.Tangent) / 100.0,
		PathStartDistanceM, PathEndDistanceM);
	RaceDistanceM = Course->MapPathDistanceToRaceDistance(CurrentPathIndex, DistanceM);

	const FStardustCraftTelemetry& Telemetry = CraftMovement->Telemetry;
	const float SpeedMPerSecond = Telemetry.SpeedMPerSecond;
	const float LookAheadM = LookAheadBaseM + LookAheadPerSpeed * SpeedMPerSecond;
	CurrentLaneU = FMath::FInterpTo(CurrentLaneU, FMath::Clamp(LaneU, -1.0f, 1.0f), DeltaTime, LaneResponse);
	int32 FollowPathIndex = CurrentPathIndex;
	float FollowDistanceM = DistanceM;
	if (PreferredPathIndex > 0 && PreferredPathIndex < Course->GetCoursePathCount())
	{
		const float BranchEntryM = Course->GetCoursePathEntryDistanceM(PreferredPathIndex);
		const float BranchExitM = Course->GetCoursePathExitDistanceM(PreferredPathIndex);
		if (RaceDistanceM >= BranchEntryM && RaceDistanceM < BranchExitM)
		{
			FollowPathIndex = PreferredPathIndex;
			FollowDistanceM = Course->MapRaceDistanceToPathDistance(FollowPathIndex, RaceDistanceM);
		}
	}
	FVector TargetCm;
	if (!Course->LanePointAtPathDistance(FollowPathIndex, FollowDistanceM + LookAheadM, CurrentLaneU, TargetCm))
	{
		return;
	}

	const FVector Up = Telemetry.bGrounded ? CraftMovement->GetHoverState().Normal : GetOwner()->GetActorUpVector();
	const FVector ToTarget = FVector::VectorPlaneProject(TargetCm - PositionCm, Up).GetSafeNormal();
	const FVector Forward = FVector::VectorPlaneProject(GetOwner()->GetActorForwardVector(), Up).GetSafeNormal();
	const float AngleRadians = FMath::Atan2(FVector::DotProduct(Up, FVector::CrossProduct(Forward, ToTarget)),
		FVector::DotProduct(Forward, ToTarget));
	float DesiredTurnRate = 2.0f * FMath::Max(SpeedMPerSecond, 10.0f) * FMath::Sin(AngleRadians) / FMath::Max(LookAheadM, 1.0f);
	DesiredTurnRate -= Telemetry.LateralSpeedMPerSecond * LateralDamping;
	FStardustCraftInput Input;
	Input.Steer = FMath::Clamp(DesiredTurnRate / FMath::Max(0.05f, CraftMovement->Tuning.GetTurnRate(SpeedMPerSecond)), -1.0f, 1.0f);

	float BankDegrees = 0.0f;
	const float Curvature = CurvatureAhead(FollowPathIndex, FollowDistanceM, 60.0f + SpeedMPerSecond * 1.2f, BankDegrees);
	const float CurveSpeed = CraftMovement->Tuning.GetCornerSpeed(Curvature, BankDegrees, CornerMargin);
	const float MaxSpeed = FMath::Min(CurveSpeed, SpeedLimitMPerSecond);
	Input.Throttle = SpeedMPerSecond > MaxSpeed ? 0.0f : 1.0f;
	Input.bBrake = SpeedMPerSecond > MaxSpeed + 4.0f && FMath::Abs(Input.Steer) < 0.3f;
	Input.bBoost = bUseBoost && SpeedMPerSecond < MaxSpeed - 5.0f;
	CraftMovement->SetInput(Input);
}
