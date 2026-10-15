#include "StardustCourseData.h"
#include "Misc/FileHelper.h"

namespace
{
	constexpr float UnityMetersToUnrealCentimeters = 100.0f;
	constexpr int32 MaxStationCount = 250000;
	constexpr int32 MaxRingCount = 4096;
	constexpr int64 MaxRingSamples = 8LL * 1024LL * 1024LL;

	FVector ReadUnityVector(FMemoryReader& Reader)
	{
		float X = 0.0f, Y = 0.0f, Z = 0.0f;
		Reader << X;
		Reader << Y;
		Reader << Z;
		return FVector(Z, X, Y) * UnityMetersToUnrealCentimeters;
	}

	bool ReadUtf8(FMemoryReader& Reader, FString& Out)
	{
		int32 Length = 0;
		Reader << Length;
		if (Reader.IsError() || Length < 0 || Length > 1024 * 1024 || Reader.Tell() + Length > Reader.TotalSize())
		{
			return false;
		}

		TArray<ANSICHAR> Buffer;
		Buffer.SetNumUninitialized(Length + 1);
		Reader.Serialize(Buffer.GetData(), Length);
		Buffer[Length] = 0;
		Out = UTF8_TO_TCHAR(Buffer.GetData());
		return !Reader.IsError();
	}
}

UStardustCourseData* UStardustCourseData::LoadRDDCFile(const FString& FilePath, FString& Error)
{
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *FilePath))
	{
		Error = FString::Printf(TEXT("Nao foi possivel abrir o curso: %s"), *FilePath);
		return nullptr;
	}
	return ParseRDDC(Bytes, Error);
}

UStardustCourseData* UStardustCourseData::ParseRDDC(const TArray<uint8>& Bytes, FString& Error)
{
	Error.Reset();
	FMemoryReader Reader(Bytes, true);
	ANSICHAR Magic[4] = {};
	Reader.Serialize(Magic, 4);
	if (Reader.IsError() || FMemory::Memcmp(Magic, "RDDC", 4) != 0)
	{
		Error = TEXT("A assinatura do ficheiro nao e RDDC.");
		return nullptr;
	}

	int32 Version = 0;
	int32 StationCount = 0;
	int32 InRingCount = 0;
	float Step = 0.0f;
	Reader << Version;
	Reader << StationCount;
	Reader << InRingCount;
	Reader << Step;
	if (Reader.IsError() || Version != 1)
	{
		Error = FString::Printf(TEXT("Versao RDDC nao suportada (%d)."), Version);
		return nullptr;
	}
	return ParseBody(Reader, StationCount, InRingCount, Step, Error);
}

UStardustCourseData* UStardustCourseData::ParseBody(FMemoryReader& Reader, int32 StationCount, int32 InRingCount, float Step, FString& Error)
{
	if (StationCount < 2 || StationCount > MaxStationCount || InRingCount < 3 || InRingCount > MaxRingCount ||
		static_cast<int64>(StationCount) * static_cast<int64>(InRingCount) > MaxRingSamples)
	{
		Error = FString::Printf(TEXT("Dimensoes de curso invalidas (estacoes %d, anel %d)."), StationCount, InRingCount);
		return nullptr;
	}

	const int64 BytesPerStation = 84LL + static_cast<int64>(InRingCount) * 12LL;
	if (Reader.IsError() || Reader.Tell() + BytesPerStation * StationCount > Reader.TotalSize())
	{
		Error = TEXT("Dados RDDC truncados antes das estacoes.");
		return nullptr;
	}

	UStardustCourseData* Course = NewObject<UStardustCourseData>();
	Course->SampleStep = Step * UnityMetersToUnrealCentimeters;
	Course->RingCount = InRingCount;
	Course->Stations.Reserve(StationCount);
	Course->CourseBounds = FBox(ForceInit);

	for (int32 I = 0; I < StationCount; ++I)
	{
		FStardustCourseStation Station;
		Reader << Station.Distance;
		Station.Distance *= UnityMetersToUnrealCentimeters;
		Station.Center = ReadUnityVector(Reader);
		Station.Tangent = ReadUnityVector(Reader).GetSafeNormal();
		Station.Right = ReadUnityVector(Reader).GetSafeNormal();
		Station.Up = ReadUnityVector(Reader).GetSafeNormal();
		Reader << Station.Width;
		Reader << Station.Bank;
		Reader << Station.Slope;
		Station.Width *= UnityMetersToUnrealCentimeters;
		Reader << Station.Flags;
		Reader << Station.Segment;
		Reader << Station.Surface;
		Reader << Station.RideLeft;
		Reader << Station.RideRight;
		Station.RideLeft *= UnityMetersToUnrealCentimeters;
		Station.RideRight *= UnityMetersToUnrealCentimeters;

		Station.Ring.Reserve(InRingCount);
		Station.RingArc.SetNumZeroed(InRingCount);
		for (int32 K = 0; K < InRingCount; ++K)
		{
			Station.Ring.Add(ReadUnityVector(Reader));
		}
		if (Reader.IsError())
		{
			Error = FString::Printf(TEXT("Dados truncados na estacao %d."), I);
			return nullptr;
		}

		for (int32 K = 0; K < InRingCount; ++K)
		{
			const int64 FlattenedRingIndex = static_cast<int64>(I) * InRingCount + K;
			if (FlattenedRingIndex % 7 == 0)
			{
				Course->CourseBounds += Station.Ring[K];
			}
		}

		const int32 Middle = InRingCount / 2;
		for (int32 K = Middle + 1; K < InRingCount; ++K)
		{
			Station.RingArc[K] = Station.RingArc[K - 1] + FVector::Distance(Station.Ring[K], Station.Ring[K - 1]);
		}
		for (int32 K = Middle - 1; K >= 0; --K)
		{
			Station.RingArc[K] = Station.RingArc[K + 1] - FVector::Distance(Station.Ring[K], Station.Ring[K + 1]);
		}
		Course->Stations.Add(MoveTemp(Station));
	}

	int32 SegmentCount = 0;
	Reader << SegmentCount;
	if (Reader.IsError() || SegmentCount < 0 || SegmentCount > 10000)
	{
		Error = TEXT("Contagem de segmentos RDDC invalida.");
		return nullptr;
	}
	Course->SegmentNames.Reserve(SegmentCount);
	for (int32 I = 0; I < SegmentCount; ++I)
	{
		FString Name;
		if (!ReadUtf8(Reader, Name))
		{
			Error = TEXT("Nao foi possivel ler os nomes dos segmentos RDDC.");
			return nullptr;
		}
		Course->SegmentNames.Add(FName(*Name));
	}
	if (Course->Stations.Num() != StationCount || Reader.IsError())
	{
		Error = TEXT("O ficheiro RDDC terminou com erro de leitura.");
		return nullptr;
	}
	Course->CourseBounds = Course->CourseBounds.ExpandBy(8000.0f);

	return Course;
}
bool UStardustCourseData::ContainsPoint(const FVector& Position) const
{
	return !Stations.IsEmpty() && CourseBounds.IsInsideOrOn(Position);
}

int32 UStardustCourseData::FindNearestStation(const FVector& Position, int32 Hint, int32 Window) const
{
	if (Stations.IsEmpty())
	{
		return INDEX_NONE;
	}

	int32 BestIndex = INDEX_NONE;
	float BestDistanceSquared = MAX_flt;
	if (Stations.IsValidIndex(Hint))
	{
		const int32 Begin = FMath::Max(0, Hint - FMath::Max(0, Window));
		const int32 End = FMath::Min(Stations.Num() - 1, Hint + FMath::Max(0, Window));
		for (int32 I = Begin; I <= End; ++I)
		{
			const float DistanceSquared = FVector::DistSquared(Stations[I].Center, Position);
			if (DistanceSquared < BestDistanceSquared)
			{
				BestDistanceSquared = DistanceSquared;
				BestIndex = I;
			}
		}
		if (BestDistanceSquared < FMath::Square(12000.0f))
		{
			return BestIndex;
		}
	}

	for (int32 I = 0; I < Stations.Num(); I += 4)
	{
		const float DistanceSquared = FVector::DistSquared(Stations[I].Center, Position);
		if (DistanceSquared < BestDistanceSquared)
		{
			BestDistanceSquared = DistanceSquared;
			BestIndex = I;
		}
	}
	if (BestIndex == INDEX_NONE)
	{
		return 0;
	}

	const int32 Begin = FMath::Max(0, BestIndex - 4);
	const int32 End = FMath::Min(Stations.Num() - 1, BestIndex + 4);
	for (int32 I = Begin; I <= End; ++I)
	{
		const float DistanceSquared = FVector::DistSquared(Stations[I].Center, Position);
		if (DistanceSquared < BestDistanceSquared)
		{
			BestDistanceSquared = DistanceSquared;
			BestIndex = I;
		}
	}
	return BestIndex;
}

int32 UStardustCourseData::FindStationAtDistance(float Distance) const
{
	if (Stations.Num() < 2)
	{
		return INDEX_NONE;
	}
	if (Distance <= Stations[0].Distance)
	{
		return 0;
	}
	if (Distance >= Stations.Last().Distance)
	{
		return Stations.Num() - 2;
	}

	int32 Low = 0;
	int32 High = Stations.Num() - 1;
	while (High - Low > 1)
	{
		const int32 Middle = (Low + High) >> 1;
		if (Stations[Middle].Distance <= Distance)
		{
			Low = Middle;
		}
		else
		{
			High = Middle;
		}
	}
	return Low;
}

int32 UStardustCourseData::StationAtDistance(float Distance) const
{
	const int32 Index = FindStationAtDistance(Distance);
	if (Index == INDEX_NONE)
	{
		return INDEX_NONE;
	}
	const float Span = Stations[Index + 1].Distance - Stations[Index].Distance;
	const float Alpha = FMath::Abs(Span) > SMALL_NUMBER
		? FMath::Clamp((Distance - Stations[Index].Distance) / Span, 0.0f, 1.0f)
		: 0.0f;
	return FMath::Clamp(Alpha < 0.5f ? Index : Index + 1, 0, Stations.Num() - 1);
}
float UStardustCourseData::DistanceAlong(const FVector& Position, int32 StationIndex) const
{
	if (Stations.IsEmpty())
	{
		return 0.0f;
	}
	const FStardustCourseStation& Station = Stations[FMath::Clamp(StationIndex, 0, Stations.Num() - 1)];
	const float Along = Station.Distance + FVector::DotProduct(Position - Station.Center, Station.Tangent);
	return FMath::Clamp(Along, GetStart(), GetLength());
}

float UStardustCourseData::OutsideRide(const FVector& Position, int32 StationIndex) const
{
	if (!Stations.IsValidIndex(StationIndex))
	{
		return 0.0f;
	}
	const FStardustCourseStation& Station = Stations[StationIndex];
	if (Station.Ring.IsEmpty() || Station.RingArc.Num() != Station.Ring.Num())
	{
		return 0.0f;
	}

	int32 BestIndex = 0;
	float BestDistanceSquared = MAX_flt;
	for (int32 K = 0; K < Station.Ring.Num(); ++K)
	{
		const float DistanceSquared = FVector::DistSquared(Station.Ring[K], Position);
		if (DistanceSquared < BestDistanceSquared)
		{
			BestDistanceSquared = DistanceSquared;
			BestIndex = K;
		}
	}
	const float Arc = Station.RingArc[BestIndex];
	const float Beyond = Arc < 0.0f
		? FMath::Max(0.0f, -Arc - Station.RideLeft)
		: FMath::Max(0.0f, Arc - Station.RideRight);
	const FVector Delta = Position - Station.Ring[BestIndex];
	const FVector PlanarDelta = Delta - FVector::DotProduct(Delta, Station.Up) * Station.Up;
	const float Away = PlanarDelta.Size();
	return Beyond + FMath::Max(0.0f, Away - 300.0f);
}

float UStardustCourseData::LateralU(const FVector& Position, int32 StationIndex) const
{
	if (!Stations.IsValidIndex(StationIndex))
	{
		return 0.0f;
	}
	const FStardustCourseStation& Station = Stations[StationIndex];
	if (Station.Ring.IsEmpty() || Station.RingArc.Num() != Station.Ring.Num())
	{
		return 0.0f;
	}

	int32 BestIndex = 0;
	float BestDistanceSquared = MAX_flt;
	for (int32 K = 0; K < Station.Ring.Num(); ++K)
	{
		const float DistanceSquared = FVector::DistSquared(Station.Ring[K], Position);
		if (DistanceSquared < BestDistanceSquared)
		{
			BestDistanceSquared = DistanceSquared;
			BestIndex = K;
		}
	}
	const float Arc = Station.RingArc[BestIndex];
	return Arc < 0.0f
		? FMath::Max(-1.5f, Arc / FMath::Max(1.0f, Station.RideLeft))
		: FMath::Min(1.5f, Arc / FMath::Max(1.0f, Station.RideRight));
}

FVector UStardustCourseData::LanePointAtStation(int32 StationIndex, float U) const
{
	if (Stations.IsEmpty())
	{
		return FVector::ZeroVector;
	}
	const FStardustCourseStation& Station = Stations[FMath::Clamp(StationIndex, 0, Stations.Num() - 1)];
	const int32 Count = Station.Ring.Num();
	if (Count == 0 || Station.RingArc.Num() != Count)
	{
		return Station.Center;
	}

	const float Arc = U < 0.0f ? U * Station.RideLeft : U * Station.RideRight;
	int32 Low = 0;
	int32 High = Count - 1;
	if (Arc <= Station.RingArc[0])
	{
		return Station.Ring[0];
	}
	if (Arc >= Station.RingArc[High])
	{
		return Station.Ring[High];
	}
	while (High - Low > 1)
	{
		const int32 Middle = (Low + High) >> 1;
		if (Station.RingArc[Middle] <= Arc)
		{
			Low = Middle;
		}
		else
		{
			High = Middle;
		}
	}
	const float ArcRange = Station.RingArc[High] - Station.RingArc[Low];
	const float Alpha = FMath::Abs(ArcRange) > SMALL_NUMBER
		? FMath::Clamp((Arc - Station.RingArc[Low]) / ArcRange, 0.0f, 1.0f)
		: 0.0f;
	return FMath::Lerp(Station.Ring[Low], Station.Ring[High], Alpha);
}

FVector UStardustCourseData::LanePointAtDistance(float Distance, float U) const
{
	const int32 Index = FindStationAtDistance(Distance);
	if (Index == INDEX_NONE)
	{
		return FVector::ZeroVector;
	}
	const float Delta = Stations[Index + 1].Distance - Stations[Index].Distance;
	const float Alpha = FMath::Abs(Delta) > SMALL_NUMBER
		? FMath::Clamp((Distance - Stations[Index].Distance) / Delta, 0.0f, 1.0f)
		: 0.0f;
	return FMath::Lerp(LanePointAtStation(Index, U), LanePointAtStation(Index + 1, U), Alpha);
}

FVector UStardustCourseData::LaneNormal(int32 StationIndex, float U) const
{
	if (Stations.Num() < 3)
	{
		return Stations.IsEmpty() ? FVector::UpVector : Stations[0].Up;
	}
	const int32 Index = FMath::Clamp(StationIndex, 1, Stations.Num() - 2);
	const FVector A = LanePointAtStation(Index, U - 0.02f);
	const FVector B = LanePointAtStation(Index, U + 0.02f);
	const FVector Forward = Stations[Index + 1].Center - Stations[Index - 1].Center;
	const FVector Normal = FVector::CrossProduct(Forward, B - A).GetSafeNormal();
	return Normal.IsNearlyZero() ? Stations[Index].Up : Normal;
}

namespace
{
	FVector SlerpDirection(const FVector& InA, const FVector& InB, float Alpha)
	{
		const FVector A = InA.GetSafeNormal();
		const FVector B = InB.GetSafeNormal();
		const float Dot = FMath::Clamp(FVector::DotProduct(A, B), -1.0f, 1.0f);
		if (Dot > 0.9995f)
		{
			return FMath::Lerp(A, B, Alpha).GetSafeNormal();
		}
		if (Dot < -0.9995f)
		{
			FVector Axis = FVector::CrossProduct(A, FVector::UpVector).GetSafeNormal();
			if (Axis.IsNearlyZero())
			{
				Axis = FVector::CrossProduct(A, FVector::RightVector).GetSafeNormal();
			}
			const float Angle = PI * Alpha;
			return (A * FMath::Cos(Angle) + Axis * FMath::Sin(Angle)).GetSafeNormal();
		}
		const float Angle = FMath::Acos(Dot);
		const float SinAngle = FMath::Sin(Angle);
		return (A * FMath::Sin((1.0f - Alpha) * Angle) + B * FMath::Sin(Alpha * Angle)).GetSafeNormal();
	}
}

FStardustCourseFrame UStardustCourseData::FrameAtDistance(float Distance) const
{
	FStardustCourseFrame Frame;
	const int32 Index = FindStationAtDistance(Distance);
	if (Index == INDEX_NONE)
	{
		return Frame;
	}
	const FStardustCourseStation& A = Stations[Index];
	const FStardustCourseStation& B = Stations[Index + 1];
	const float Delta = B.Distance - A.Distance;
	const float Alpha = FMath::Abs(Delta) > SMALL_NUMBER
		? FMath::Clamp((Distance - A.Distance) / Delta, 0.0f, 1.0f)
		: 0.0f;
	Frame.Position = FMath::Lerp(A.Center, B.Center, Alpha);
	Frame.Tangent = SlerpDirection(A.Tangent, B.Tangent, Alpha);
	Frame.Right = SlerpDirection(A.Right, B.Right, Alpha);
	Frame.Up = SlerpDirection(A.Up, B.Up, Alpha);
	Frame.StationIndex = Index;
	Frame.Alpha = Alpha;
	Frame.Distance = FMath::Lerp(A.Distance, B.Distance, Alpha);
	return Frame;
}

float UStardustCourseData::CurvatureAhead(float Distance, float Span) const
{
	const int32 AIndex = StationAtDistance(Distance);
	const int32 BIndex = StationAtDistance(Distance + Span);
	if (AIndex == INDEX_NONE || BIndex <= AIndex)
	{
		return 0.0f;
	}
	FVector A = Stations[AIndex].Tangent;
	FVector B = Stations[BIndex].Tangent;
	A.Z = 0.0f;
	B.Z = 0.0f;
	A = A.GetSafeNormal();
	B = B.GetSafeNormal();
	const float AngleRadians = FMath::Acos(FMath::Clamp(FVector::DotProduct(A, B), -1.0f, 1.0f));
	const float DistanceMeters = (Stations[BIndex].Distance - Stations[AIndex].Distance) / 100.0f;
	return AngleRadians / FMath::Max(1.0f, DistanceMeters);
}

float UStardustCourseData::SurfaceAngle(int32 StationIndex, float U) const
{
	const FVector Normal = LaneNormal(StationIndex, U).GetSafeNormal();
	const float Dot = FMath::Clamp(FVector::DotProduct(Normal, FVector::UpVector), -1.0f, 1.0f);
	return FMath::RadiansToDegrees(FMath::Acos(Dot));
}

float UStardustCourseData::LaneForAngle(int32 StationIndex, float Degrees, int32 Side) const
{
	float BestU = 0.0f;
	float BestDelta = MAX_flt;
	if (Side == 0)
	{
		return 0.0f;
	}
	const int32 Direction = Side < 0 ? -1 : 1;
	for (int32 StepIndex = 0; StepIndex <= 100; ++StepIndex)
	{
		const float U = static_cast<float>(StepIndex) * 0.01f * Direction;
		const float Delta = FMath::Abs(SurfaceAngle(StationIndex, U) - Degrees);
		if (Delta < BestDelta)
		{
			BestDelta = Delta;
			BestU = U;
		}
	}
	return BestU;
}

bool UStardustCourseData::IsGap(int32 StationIndex) const
{
	return Stations.IsValidIndex(StationIndex) && (Stations[StationIndex].Flags & 1) != 0;
}

bool UStardustCourseData::IsCave(int32 StationIndex) const
{
	return Stations.IsValidIndex(StationIndex) && (Stations[StationIndex].Flags & 2) != 0;
}

FName UStardustCourseData::GetSegmentName(int32 StationIndex) const
{
	if (!Stations.IsValidIndex(StationIndex) || SegmentNames.IsEmpty())
	{
		return NAME_None;
	}
	const int32 SegmentIndex = FMath::Clamp(Stations[StationIndex].Segment, 0, SegmentNames.Num() - 1);
	return SegmentNames[SegmentIndex];
}
