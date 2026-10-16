#include "Course/StardustCourseData.h"

namespace
{
	constexpr int32 MaxCourseStations = 2000000;
	constexpr int32 MaxCourseRings = 4096;
	constexpr int32 MaxCourseSegments = 100000;
	constexpr int32 MaxCoursePaths = 1024;
	constexpr int32 MaxCourseStringBytes = 1024 * 1024;
	constexpr int64 CourseStationBytes = 84;
	constexpr int64 CourseVectorBytes = 12;

	bool IsFiniteVector(const FVector& Value)
	{
		return FMath::IsFinite(Value.X) && FMath::IsFinite(Value.Y) && FMath::IsFinite(Value.Z);
	}

	FVector ReadUnityVector(FMemoryReader& Reader)
	{
		float X = 0.0f;
		float Y = 0.0f;
		float Z = 0.0f;
		Reader << X;
		Reader << Y;
		Reader << Z;
		return FVector(Z, X, Y);
	}

	bool ReadCount(FMemoryReader& Reader, int32& OutValue, int32 MaxValue)
	{
		Reader << OutValue;
		return !Reader.IsError() && OutValue >= 0 && OutValue <= MaxValue;
	}

	bool ReadStation(FMemoryReader& Reader, int32 RingCount, FStardustCourseStation& OutStation)
	{
		Reader << OutStation.DistanceM;
		OutStation.CenterM = ReadUnityVector(Reader);
		OutStation.Tangent = ReadUnityVector(Reader);
		OutStation.Right = ReadUnityVector(Reader);
		OutStation.Up = ReadUnityVector(Reader);
		Reader << OutStation.WidthM;
		Reader << OutStation.BankDegrees;
		Reader << OutStation.Slope;
		Reader << OutStation.Flags;
		Reader << OutStation.SegmentIndex;
		Reader << OutStation.SurfaceIndex;
		Reader << OutStation.RideLeftM;
		Reader << OutStation.RideRightM;

		if (Reader.IsError())
		{
			return false;
		}

		OutStation.RingOffsetsM.Reserve(RingCount);
		for (int32 RingIndex = 0; RingIndex < RingCount; ++RingIndex)
		{
			OutStation.RingOffsetsM.Add(ReadUnityVector(Reader));
			if (Reader.IsError())
			{
				return false;
			}
		}
		return true;
	}
}

void FStardustCourseData::Reset()
{
	Stations.Reset();
	SegmentNames.Reset();
	StepM = 0.0f;
	RingCount = 0;
}

bool FStardustCourseData::Load(const TArray<uint8>& Bytes, FString& OutError)
{
	Reset();
	OutError.Reset();
	FMemoryReader Reader(Bytes, true);
	Reader.SetByteSwapping(false);

	uint8 Signature[4] = {};
	Reader.Serialize(Signature, UE_ARRAY_COUNT(Signature));
	if (Reader.IsError() || FMemory::Memcmp(Signature, "RDDC", UE_ARRAY_COUNT(Signature)) != 0)
	{
		OutError = TEXT("Invalid course signature; expected RDDC.");
		return false;
	}

	int32 Version = 0;
	int32 StationCount = 0;
	Reader << Version;
	if (Reader.IsError() || Version != 1 || !ReadCount(Reader, StationCount, MaxCourseStations) ||
		!ReadCount(Reader, RingCount, MaxCourseRings))
	{
		OutError = TEXT("Unsupported or invalid RDDC header.");
		Reset();
		return false;
	}

	float CourseStepM = 0.0f;
	Reader << CourseStepM;
	if (Reader.IsError())
	{
		OutError = TEXT("Truncated RDDC header.");
		Reset();
		return false;
	}
	if (!LoadBody(Reader, StationCount, RingCount, CourseStepM, OutError))
	{
		Reset();
		return false;
	}
	if (Reader.Tell() != Reader.TotalSize())
	{
		OutError = TEXT("RDDC file contains unexpected trailing bytes.");
		Reset();
		return false;
	}
	return true;
}

bool FStardustCourseData::LoadBody(FMemoryReader& Reader, int32 InStationCount, int32 InRingCount, float InStepM, FString& OutError)
{
	Reset();
	OutError.Reset();
	if (InStationCount < 2 || InStationCount > MaxCourseStations || InRingCount < 2 || InRingCount > MaxCourseRings ||
		!FMath::IsFinite(InStepM) || InStepM <= 0.0f)
	{
		OutError = TEXT("Invalid course station count, ring count, or sampling step.");
		return false;
	}
	const int64 MinimumBodyBytes = static_cast<int64>(InStationCount) *
		(CourseStationBytes + static_cast<int64>(InRingCount) * CourseVectorBytes) + sizeof(int32);
	if (Reader.TotalSize() - Reader.Tell() < MinimumBodyBytes)
	{
		OutError = TEXT("Course data is truncated or exceeds the available file size.");
		return false;
	}
	StepM = InStepM;
	RingCount = InRingCount;

	Stations.Reserve(InStationCount);
	for (int32 StationIndex = 0; StationIndex < InStationCount; ++StationIndex)
	{
		FStardustCourseStation Station;
		if (!ReadStation(Reader, RingCount, Station) || !FMath::IsFinite(Station.DistanceM) ||
			!IsFiniteVector(Station.CenterM) || !IsFiniteVector(Station.Tangent) || !IsFiniteVector(Station.Right) ||
			!IsFiniteVector(Station.Up) || !FMath::IsFinite(Station.WidthM) || !FMath::IsFinite(Station.BankDegrees) ||
			!FMath::IsFinite(Station.Slope) || !FMath::IsFinite(Station.RideLeftM) || !FMath::IsFinite(Station.RideRightM) ||
			(StationIndex > 0 && Station.DistanceM <= Stations.Last().DistanceM))
		{
			OutError = FString::Printf(TEXT("Invalid RDDC station data at index %d."), StationIndex);
			Reset();
			return false;
		}
		for (const FVector& RingPoint : Station.RingOffsetsM)
		{
			if (!IsFiniteVector(RingPoint))
			{
				OutError = FString::Printf(TEXT("Invalid RDDC ring data at station %d."), StationIndex);
				Reset();
				return false;
			}
		}
		Stations.Add(MoveTemp(Station));
	}

	int32 SegmentCount = 0;
	if (!ReadCount(Reader, SegmentCount, MaxCourseSegments))
	{
		OutError = TEXT("Invalid RDDC segment count.");
		Reset();
		return false;
	}

	SegmentNames.Reserve(SegmentCount);
	for (int32 SegmentIndex = 0; SegmentIndex < SegmentCount; ++SegmentIndex)
	{
		int32 StringBytes = 0;
		if (!ReadCount(Reader, StringBytes, MaxCourseStringBytes) || Reader.TotalSize() - Reader.Tell() < StringBytes)
		{
			OutError = FString::Printf(TEXT("Invalid RDDC segment name at index %d."), SegmentIndex);
			Reset();
			return false;
		}
		TArray<uint8> EncodedName;
		EncodedName.SetNumUninitialized(StringBytes);
		if (StringBytes > 0)
		{
			Reader.Serialize(EncodedName.GetData(), StringBytes);
		}
		if (Reader.IsError())
		{
			OutError = FString::Printf(TEXT("Truncated RDDC segment name at index %d."), SegmentIndex);
			Reset();
			return false;
		}
		FUTF8ToTCHAR Converted(reinterpret_cast<const ANSICHAR*>(EncodedName.GetData()), StringBytes);
		SegmentNames.Add(FString(Converted.Length(), Converted.Get()));
	}

	return true;
}

float FStardustCoursePath::ToRaceDistance(float DistanceM) const
{
	if (IsMain())
	{
		return DistanceM;
	}
	const TArray<FStardustCourseStation>& Stations = Data.GetStations();
	if (Stations.Num() < 2)
	{
		return FromM;
	}
	const float PathStartM = Stations[0].DistanceM;
	const float PathEndM = Stations.Last().DistanceM;
	const float Alpha = PathEndM > PathStartM ? FMath::Clamp((DistanceM - PathStartM) / (PathEndM - PathStartM), 0.0f, 1.0f) : 0.0f;
	return FMath::Lerp(FromM, ToM, Alpha);
}

void FStardustCourseGraphData::Reset()
{
	Paths.Reset();
}

bool FStardustCourseGraphData::Load(const TArray<uint8>& Bytes, FString& OutError)
{
	Reset();
	OutError.Reset();
	FMemoryReader Reader(Bytes, true);
	Reader.SetByteSwapping(false);
	uint8 Signature[4] = {};
	Reader.Serialize(Signature, UE_ARRAY_COUNT(Signature));
	int32 Version = 0;
	int32 PathCount = 0;
	Reader << Version;
	if (Reader.IsError() || FMemory::Memcmp(Signature, "RDDG", UE_ARRAY_COUNT(Signature)) != 0 ||
		Version != 2 || !ReadCount(Reader, PathCount, MaxCoursePaths) || PathCount < 1)
	{
		OutError = TEXT("Unsupported or invalid RDDG v2 header.");
		return false;
	}

	Paths.Reserve(PathCount);
	for (int32 PathIndex = 0; PathIndex < PathCount; ++PathIndex)
	{
		int32 IdBytes = 0;
		if (!ReadCount(Reader, IdBytes, MaxCourseStringBytes) || IdBytes < 1 || Reader.TotalSize() - Reader.Tell() < IdBytes)
		{
			OutError = FString::Printf(TEXT("Invalid RDDG path id at index %d."), PathIndex);
			Reset();
			return false;
		}
		TArray<uint8> EncodedId;
		EncodedId.SetNumUninitialized(IdBytes);
		if (IdBytes > 0)
		{
			Reader.Serialize(EncodedId.GetData(), IdBytes);
		}
		if (Reader.IsError())
		{
			OutError = FString::Printf(TEXT("Truncated RDDG path id at index %d."), PathIndex);
			Reset();
			return false;
		}

		FStardustCoursePath Path;
		Path.Index = PathIndex;
		FUTF8ToTCHAR ConvertedId(reinterpret_cast<const ANSICHAR*>(EncodedId.GetData()), IdBytes);
		Path.Id = FString(ConvertedId.Length(), ConvertedId.Get());
		int32 StationCount = 0;
		int32 RingCount = 0;
		float StepM = 0.0f;
		Reader << Path.ParentIndex;
		Reader << Path.FromM;
		Reader << Path.ToM;
		Reader << Path.LengthM;
		if (!ReadCount(Reader, StationCount, MaxCourseStations) || !ReadCount(Reader, RingCount, MaxCourseRings))
		{
			OutError = FString::Printf(TEXT("Invalid RDDG course dimensions at path %d."), PathIndex);
			Reset();
			return false;
		}
		Reader << StepM;
		const bool bValidParent = PathIndex == 0 ? Path.ParentIndex == INDEX_NONE : Path.ParentIndex >= 0 && Path.ParentIndex < PathIndex;
		if (Reader.IsError() || !bValidParent || !FMath::IsFinite(Path.FromM) || !FMath::IsFinite(Path.ToM) ||
			!FMath::IsFinite(Path.LengthM) || Path.ToM < Path.FromM || Path.LengthM <= 0.0f ||
			!Path.Data.LoadBody(Reader, StationCount, RingCount, StepM, OutError))
		{
			if (OutError.IsEmpty())
			{
				OutError = FString::Printf(TEXT("Invalid RDDG metadata at path %d."), PathIndex);
			}
			Reset();
			return false;
		}
		Paths.Add(MoveTemp(Path));
	}

	if (Reader.IsError() || Reader.Tell() != Reader.TotalSize())
	{
		OutError = TEXT("RDDG file is truncated or contains unexpected trailing bytes.");
		Reset();
		return false;
	}
	return true;
}

bool FStardustCourseData::SampleAtDistance(float DistanceM, FStardustCourseSample& OutSample) const
{
	if (Stations.Num() < 2 || !FMath::IsFinite(DistanceM))
	{
		return false;
	}

	const int32 LastIndex = Stations.Num() - 1;
	const float ClampedDistance = FMath::Clamp(DistanceM, Stations[0].DistanceM, Stations[LastIndex].DistanceM);
	int32 LowerIndex = 0;
	int32 UpperIndex = LastIndex;
	while (LowerIndex + 1 < UpperIndex)
	{
		const int32 MiddleIndex = (LowerIndex + UpperIndex) / 2;
		if (Stations[MiddleIndex].DistanceM <= ClampedDistance)
		{
			LowerIndex = MiddleIndex;
		}
		else
		{
			UpperIndex = MiddleIndex;
		}
	}

	const FStardustCourseStation& Start = Stations[LowerIndex];
	const FStardustCourseStation& End = Stations[UpperIndex];
	const float SegmentLength = End.DistanceM - Start.DistanceM;
	const float Alpha = SegmentLength > UE_SMALL_NUMBER ? (ClampedDistance - Start.DistanceM) / SegmentLength : 0.0f;
	OutSample.StationIndex = LowerIndex;
	OutSample.Alpha = Alpha;
	OutSample.DistanceM = ClampedDistance;
	OutSample.CenterM = FMath::Lerp(Start.CenterM, End.CenterM, Alpha);
	OutSample.Tangent = FMath::Lerp(Start.Tangent, End.Tangent, Alpha).GetSafeNormal(UE_SMALL_NUMBER, Start.Tangent);
	OutSample.Right = FMath::Lerp(Start.Right, End.Right, Alpha).GetSafeNormal(UE_SMALL_NUMBER, Start.Right);
	OutSample.Up = FMath::Lerp(Start.Up, End.Up, Alpha).GetSafeNormal(UE_SMALL_NUMBER, Start.Up);
	OutSample.WidthM = FMath::Lerp(Start.WidthM, End.WidthM, Alpha);
	OutSample.BankDegrees = FMath::Lerp(Start.BankDegrees, End.BankDegrees, Alpha);
	OutSample.Slope = FMath::Lerp(Start.Slope, End.Slope, Alpha);
	OutSample.Flags = Alpha < 0.5f ? Start.Flags : End.Flags;
	OutSample.SegmentIndex = Alpha < 0.5f ? Start.SegmentIndex : End.SegmentIndex;
	OutSample.SurfaceIndex = Alpha < 0.5f ? Start.SurfaceIndex : End.SurfaceIndex;
	OutSample.RideLeftM = FMath::Lerp(Start.RideLeftM, End.RideLeftM, Alpha);
	OutSample.RideRightM = FMath::Lerp(Start.RideRightM, End.RideRightM, Alpha);
	OutSample.RingOffsetsM.SetNumUninitialized(RingCount);
	for (int32 RingIndex = 0; RingIndex < RingCount; ++RingIndex)
	{
		OutSample.RingOffsetsM[RingIndex] = FMath::Lerp(Start.RingOffsetsM[RingIndex], End.RingOffsetsM[RingIndex], Alpha);
	}
	return true;
}
