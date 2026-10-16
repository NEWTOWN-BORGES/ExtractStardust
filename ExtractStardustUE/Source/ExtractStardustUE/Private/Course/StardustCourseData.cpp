#include "Course/StardustCourseData.h"

namespace
{
	constexpr int32 MaxCourseStations = 2000000;
	constexpr int32 MaxCourseRings = 4096;
	constexpr int32 MaxCourseSegments = 100000;
	constexpr int32 MaxCourseStringBytes = 1024 * 1024;

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

	Reader << StepM;
	if (Reader.IsError() || StationCount < 2 || !FMath::IsFinite(StepM) || StepM <= 0.0f)
	{
		OutError = TEXT("Invalid RDDC station count or sampling step.");
		Reset();
		return false;
	}

	Stations.Reserve(StationCount);
	for (int32 StationIndex = 0; StationIndex < StationCount; ++StationIndex)
	{
		FStardustCourseStation Station;
		if (!ReadStation(Reader, RingCount, Station) || !FMath::IsFinite(Station.DistanceM) ||
			!FMath::IsFinite(Station.WidthM) || (StationIndex > 0 && Station.DistanceM <= Stations.Last().DistanceM))
		{
			OutError = FString::Printf(TEXT("Invalid RDDC station data at index %d."), StationIndex);
			Reset();
			return false;
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

	if (Reader.Tell() != Reader.TotalSize())
	{
		OutError = TEXT("RDDC file contains unexpected trailing bytes.");
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
