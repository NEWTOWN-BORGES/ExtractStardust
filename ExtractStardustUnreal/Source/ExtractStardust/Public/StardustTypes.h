#pragma once

#include "CoreMinimal.h"
#include "StardustTypes.generated.h"

class UStaticMesh;

UENUM(BlueprintType)
enum class EStardustConsumableKind : uint8
{
	Repair,
	Fuel,
	Coolant,
	Surge,
	Stabilizer
};

USTRUCT(BlueprintType)
struct FStardustConsumableStack
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame)
	FName Id = NAME_None;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame)
	int32 Count = 0;
};

USTRUCT(BlueprintType)
struct FStardustPartDefinition
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FName Id = NAME_None;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FName Family = NAME_None;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FName Size = TEXT("M");

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	TObjectPtr<UStaticMesh> Mesh = nullptr;
};

USTRUCT(BlueprintType)
struct FStardustSocketDefinition
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FName Id = NAME_None;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	TArray<FName> AcceptedFamilies;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FName Size = TEXT("M");

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FTransform RelativeTransform;
};

USTRUCT(BlueprintType)
struct FStardustProfile
{
	GENERATED_BODY()

	UPROPERTY(SaveGame, BlueprintReadOnly)
	int64 Stardust = 2500;

	UPROPERTY(SaveGame, BlueprintReadOnly)
	int32 Races = 0;

	UPROPERTY(SaveGame, BlueprintReadOnly)
	FName Chassis = TEXT("strix");

	UPROPERTY(SaveGame, BlueprintReadOnly)
	TArray<FStardustConsumableStack> Loadout;
};
