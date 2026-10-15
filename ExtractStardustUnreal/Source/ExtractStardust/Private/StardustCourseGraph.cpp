#include "StardustCourseGraph.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/MemoryReader.h"

namespace
{
	constexpr float UnityMetersToUnrealCentimeters = 100.0f;
	constexpr int32 MaxPathCount = 128;

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

UStardustCourseGraph* UStardustCourseGraph::ParseRDDG(const TArray<uint8>& Bytes, FString& Error)
{
	Error.Reset();
	FMemoryReader Reader(Bytes, true);
	ANSICHAR Magic[4] = {};
	Reader.Serialize(Magic, 4);
	if (Reader.IsError() || FMemory::Memcmp(Magic, "RDDG", 4) != 0)
	{
		Error = TEXT("A assinatura do ficheiro nao e RDDG.");
		return nullptr;
	}

	int32 Version = 0;
	int32 PathCount = 0;
	Reader << Version;
	Reader << PathCount;
	if (Reader.IsError() || Version != 2 || PathCount < 1 || PathCount > MaxPathCount)
	{
		Error = FString::Printf(TEXT("Cabecalho RDDG invalido (versao %d, percursos %d)."), Version, PathCount);
		return nullptr;
	}

	UStardustCourseGraph* Graph = NewObject<UStardustCourseGraph>();
	Graph->Paths.Reserve(PathCount);
	for (int32 I = 0; I < PathCount; ++I)
	{
		FStardustCoursePath Path;
		Path.Index = I;
		if (!ReadUtf8(Reader, Path.Id))
		{
			Error = FString::Printf(TEXT("Nao foi possivel ler o nome do percurso %d."), I);
			return nullptr;
		}

		Reader << Path.Parent;
		Reader << Path.From;
		Reader << Path.To;
		Reader << Path.Length;
		int32 StationCount = 0;
		int32 RingCount = 0;
		float Step = 0.0f;
		Reader << StationCount;
		Reader << RingCount;
		Reader << Step;
		if (Reader.IsError() || Path.Parent < INDEX_NONE || Path.Parent >= PathCount || Path.Parent == I ||
			!FMath::IsFinite(Path.From) || !FMath::IsFinite(Path.To) || !FMath::IsFinite(Path.Length) ||
			Path.From < 0.0f || Path.To < Path.From || Path.Length <= 0.0f)
		{
			Error = FString::Printf(TEXT("Metadados invalidos no percurso %d."), I);
			return nullptr;
		}

		Path.Data = UStardustCourseData::ParseBody(Reader, StationCount, RingCount, Step, Error);
		if (!Path.Data)
		{
			Error = FString::Printf(TEXT("Percurso %s: %s"), *Path.Id, *Error);
			return nullptr;
		}
		Path.From *= UnityMetersToUnrealCentimeters;
		Path.To *= UnityMetersToUnrealCentimeters;
		Path.Length *= UnityMetersToUnrealCentimeters;
		Graph->Paths.Add(MoveTemp(Path));
	}

	if (Graph->Paths.IsEmpty() || !Graph->Paths[0].IsMain())
	{
		Error = TEXT("O percurso zero do RDDG tem de ser o principal.");
		return nullptr;
	}
	return Graph;
}

UStardustCourseGraph* UStardustCourseGraph::LoadProjectCourse(FName CourseId, FString& Error)
{
	const FString Id = CourseId.ToString().ToLower();
	if (Id != TEXT("red_dust_divide") && Id != TEXT("sandbox"))
	{
		Error = FString::Printf(TEXT("Curso desconhecido: %s"), *Id);
		return nullptr;
	}

	const FString DataDirectory = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Stardust"), TEXT("Data"));
	const FString GraphPath = FPaths::Combine(DataDirectory, Id + TEXT("_graph.bytes"));
	const FString ObstaclesPath = FPaths::Combine(DataDirectory, Id + TEXT("_obstacles.json"));
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *GraphPath))
	{
		Error = FString::Printf(TEXT("Nao foi possivel abrir o grafo do curso: %s"), *GraphPath);
		return nullptr;
	}

	UStardustCourseGraph* Graph = ParseRDDG(Bytes, Error);
	if (!Graph)
	{
		return nullptr;
	}
	FString ObstaclesJson;
	if (!FFileHelper::LoadFileToString(ObstaclesJson, *ObstaclesPath))
	{
		Error = FString::Printf(TEXT("Nao foi possivel abrir os obstaculos do curso: %s"), *ObstaclesPath);
		return nullptr;
	}
	if (!Graph->LoadObstaclesJson(ObstaclesJson, Error))
	{
		return nullptr;
	}
	return Graph;
}

bool UStardustCourseGraph::LoadObstaclesJson(const FString& Json, FString& Error)
{
	Error.Reset();
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		Error = TEXT("JSON de obstaculos invalido.");
		return false;
	}

	const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
	if (!Root->TryGetArrayField(TEXT("obstacles"), Values) || !Values)
	{
		Error = TEXT("O JSON nao contem a lista obstacles.");
		return false;
	}

	TArray<FStardustCourseObstacle> Parsed;
	Parsed.Reserve(Values->Num());
	for (int32 I = 0; I < Values->Num(); ++I)
	{
		const TSharedPtr<FJsonObject> Object = (*Values)[I].IsValid() ? (*Values)[I]->AsObject() : nullptr;
		double PathValue = 0.0;
		double DistanceMeters = 0.0;
		double LateralU = 0.0;
		double RadiusMeters = 0.0;
		if (!Object.IsValid() || !Object->TryGetNumberField(TEXT("path"), PathValue) ||
			!Object->TryGetNumberField(TEXT("dist"), DistanceMeters) || !Object->TryGetNumberField(TEXT("u"), LateralU) ||
			!Object->TryGetNumberField(TEXT("r"), RadiusMeters) || !FMath::IsFinite(PathValue) ||
			!FMath::IsFinite(DistanceMeters) || !FMath::IsFinite(LateralU) || !FMath::IsFinite(RadiusMeters))
		{
			Error = FString::Printf(TEXT("Obstaculo JSON invalido na entrada %d."), I);
			return false;
		}

		const int32 PathIndex = FMath::RoundToInt(PathValue);
		if (PathValue != static_cast<double>(PathIndex) || !Paths.IsValidIndex(PathIndex) || DistanceMeters < 0.0 || RadiusMeters < 0.0)
		{
			Error = FString::Printf(TEXT("Valores invalidos no obstaculo %d."), I);
			return false;
		}

		FStardustCourseObstacle Obstacle;
		Obstacle.Path = PathIndex;
		Obstacle.Distance = static_cast<float>(DistanceMeters) * UnityMetersToUnrealCentimeters;
		Obstacle.LateralU = static_cast<float>(LateralU);
		Obstacle.Radius = static_cast<float>(RadiusMeters) * UnityMetersToUnrealCentimeters;
		Parsed.Add(Obstacle);
	}
	Parsed.Sort([](const FStardustCourseObstacle& A, const FStardustCourseObstacle& B)
	{
		return A.Path == B.Path ? A.Distance < B.Distance : A.Path < B.Path;
	});
	Obstacles = MoveTemp(Parsed);
	return true;
}

bool UStardustCourseGraph::GetPath(int32 Index, FStardustCoursePath& OutPath) const
{
	if (!Paths.IsValidIndex(Index))
	{
		return false;
	}
	OutPath = Paths[Index];
	return true;
}

float UStardustCourseGraph::ToRaceDistance(int32 PathIndex, float PathDistance) const
{
	if (!Paths.IsValidIndex(PathIndex))
	{
		return 0.0f;
	}
	const FStardustCoursePath& Path = Paths[PathIndex];
	if (Path.IsMain() || !Path.Data)
	{
		return PathDistance;
	}
	const float Start = Path.Data->GetStart();
	const float End = Path.Data->GetLength();
	const float Alpha = FMath::Clamp((PathDistance - Start) / FMath::Max(1.0f, End - Start), 0.0f, 1.0f);
	return FMath::Lerp(Path.From, Path.To, Alpha);
}

TArray<FStardustCourseObstacle> UStardustCourseGraph::GetObstaclesForPath(int32 PathIndex) const
{
	TArray<FStardustCourseObstacle> Result;
	for (const FStardustCourseObstacle& Obstacle : Obstacles)
	{
		if (Obstacle.Path == PathIndex)
		{
			Result.Add(Obstacle);
		}
	}
	return Result;
}
float UStardustCourseGraph::Locate(const FVector& Position, int32& PathIndex, int32& StationIndex, float Hysteresis) const
{
	if (Paths.IsEmpty())
	{
		PathIndex = INDEX_NONE;
		StationIndex = INDEX_NONE;
		return MAX_flt;
	}

	PathIndex = FMath::Clamp(PathIndex, 0, Paths.Num() - 1);
	if (!Paths[PathIndex].Data)
	{
		PathIndex = 0;
		StationIndex = INDEX_NONE;
		while (PathIndex < Paths.Num() && !Paths[PathIndex].Data)
		{
			++PathIndex;
		}
		if (PathIndex >= Paths.Num())
		{
			PathIndex = INDEX_NONE;
			return MAX_flt;
		}
	}

	const UStardustCourseData* CurrentData = Paths[PathIndex].Data;
	StationIndex = CurrentData->FindNearestStation(Position, StationIndex);
	float BestDistance = SurfaceDistance(*CurrentData, Position, StationIndex) - FMath::Max(0.0f, Hysteresis);
	int32 BestPath = PathIndex;
	int32 BestStation = StationIndex;

	for (int32 I = 0; I < Paths.Num(); ++I)
	{
		if (I == PathIndex || !Paths[I].Data || !Paths[I].Data->ContainsPoint(Position))
		{
			continue;
		}
		const UStardustCourseData* CandidateData = Paths[I].Data;
		const int32 CandidateStation = CandidateData->FindNearestStation(Position);
		const float CandidateDistance = SurfaceDistance(*CandidateData, Position, CandidateStation);
		if (CandidateDistance < BestDistance)
		{
			BestDistance = CandidateDistance;
			BestPath = I;
			BestStation = CandidateStation;
		}
	}

	PathIndex = BestPath;
	StationIndex = BestStation;
	return SurfaceDistance(*Paths[BestPath].Data, Position, BestStation);
}

float UStardustCourseGraph::SurfaceDistance(const UStardustCourseData& Data, const FVector& Position, int32 StationIndex)
{
	const int32 Count = Data.GetStationCount();
	if (Count == 0 || Data.GetRingCount() == 0)
	{
		return MAX_flt;
	}
	const int32 Begin = FMath::Max(0, StationIndex - 1);
	const int32 End = FMath::Min(Count - 1, StationIndex + 1);
	float BestDistanceSquared = MAX_flt;
	for (int32 I = Begin; I <= End; ++I)
	{
		const FStardustCourseStation* Station = Data.GetStation(I);
		if (!Station)
		{
			continue;
		}
		for (int32 K = 0; K < Station->Ring.Num(); K += 2)
		{
			BestDistanceSquared = FMath::Min(BestDistanceSquared, FVector::DistSquared(Station->Ring[K], Position));
		}
	}
	return BestDistanceSquared == MAX_flt ? MAX_flt : FMath::Sqrt(BestDistanceSquared);
}

TArray<FStardustCoursePath> UStardustCourseGraph::BranchesLeaving(float FromDistance, float ToDistance) const
{
	TArray<FStardustCoursePath> Result;
	if (ToDistance <= FromDistance)
	{
		return Result;
	}
	for (const FStardustCoursePath& Path : Paths)
	{
		if (!Path.IsMain() && Path.From >= FromDistance && Path.From < ToDistance)
		{
			Result.Add(Path);
		}
	}
	return Result;
}
