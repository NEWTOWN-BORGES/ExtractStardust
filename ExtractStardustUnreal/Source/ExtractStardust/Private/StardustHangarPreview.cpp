#include "StardustHangarPreview.h"
#include "StardustProfileSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"

AStardustHangarPreview::AStardustHangarPreview()
{
	PrimaryActorTick.bCanEverTick = true;
	ChassisPreview = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ChassisPreview"));
	SetRootComponent(ChassisPreview);
	ChassisPreview->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	PartPreview = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PartPreview"));
	PartPreview->SetupAttachment(ChassisPreview);
	PartPreview->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	ConfigureSockets(CurrentChassisId);
}

void AStardustHangarPreview::BeginPlay()
{
	Super::BeginPlay();
	if (!IncompatibleMaterial)
	{
		IncompatibleMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Stardust/Materials/M_Incompatible.M_Incompatible"));
	}
	FName ChassisId = CurrentChassisId;
	if (UGameInstance* GameInstance = GetGameInstance())
	{
		if (UStardustProfileSubsystem* Profile = GameInstance->GetSubsystem<UStardustProfileSubsystem>())
		{
			ChassisId = Profile->GetProfile().Chassis;
		}
	}
	SetChassis(ChassisId);
}

void AStardustHangarPreview::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bAutoRotate) AddActorLocalRotation(FRotator(0.0f, 12.0f * DeltaSeconds, 0.0f));
}

const FStardustSocketDefinition* AStardustHangarPreview::FindSocket(FName SocketId) const
{
	return Sockets.FindByPredicate([SocketId](const FStardustSocketDefinition& Socket) { return Socket.Id == SocketId; });
}

TArray<FStardustPartDefinition> AStardustHangarPreview::GetCompatibleParts(FName SocketId, const TArray<FStardustPartDefinition>& Candidates) const
{
	TArray<FStardustPartDefinition> Result;
	const FStardustSocketDefinition* Socket = FindSocket(SocketId);
	if (!Socket) return Result;
	for (const FStardustPartDefinition& Candidate : Candidates)
	{
		if (UStardustProfileSubsystem::IsPartCompatible(*Socket, Candidate)) Result.Add(Candidate);
	}
	return Result;
}

bool AStardustHangarPreview::PreviewPart(FName SocketId, const FStardustPartDefinition& Part)
{
	const FStardustSocketDefinition* Socket = FindSocket(SocketId);
	if (!Socket || !Part.Mesh) return false;
	const bool bCompatible = UStardustProfileSubsystem::IsPartCompatible(*Socket, Part);
	PartPreview->SetStaticMesh(Part.Mesh);
	PartPreview->SetRelativeTransform(Socket->RelativeTransform);
	SetPartMaterial(bCompatible);
	if (!bCompatible && GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 2.0f, FColor::Red, TEXT("MODULO INCOMPATIVEL - nao pode ser instalado"));
	}
	return bCompatible;
}

bool AStardustHangarPreview::InstallPart(FName SocketId, const FStardustPartDefinition& Part)
{
	if (!PreviewPart(SocketId, Part))
	{
		return false;
	}
	InstalledParts.FindOrAdd(SocketId) = Part;
	if (UGameInstance* GameInstance = GetGameInstance())
	{
		if (UStardustProfileSubsystem* Profile = GameInstance->GetSubsystem<UStardustProfileSubsystem>())
		{
			Profile->SetInstalledPart(SocketId, Part.Id);
		}
	}
	return true;
}

void AStardustHangarPreview::RemoveInstalledPart(FName SocketId)
{
	InstalledParts.Remove(SocketId);
	if (UGameInstance* GameInstance = GetGameInstance())
	{
		if (UStardustProfileSubsystem* Profile = GameInstance->GetSubsystem<UStardustProfileSubsystem>())
		{
			Profile->ClearInstalledPart(SocketId);
		}
	}
	if (PartPreview && PartPreview->GetStaticMesh() && PartPreview->GetRelativeTransform().Equals(FindSocket(SocketId) ? FindSocket(SocketId)->RelativeTransform : FTransform()))
	{
		ClearPartPreview();
	}
}

bool AStardustHangarPreview::SetChassis(FName ChassisId)
{
	if (ChassisId.IsNone())
	{
		ChassisId = TEXT("strix");
	}
	const FString AssetPath = FString::Printf(TEXT("/Game/Stardust/Vehicles/%s.%s"), *ChassisId.ToString(), *ChassisId.ToString());
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *AssetPath);
	if (!Mesh && ChassisId != TEXT("strix"))
	{
		ChassisId = TEXT("strix");
		Mesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Stardust/Vehicles/strix.strix"));
	}
	if (!Mesh)
	{
		return false;
	}
	CurrentChassisId = ChassisId;
	ChassisPreview->SetStaticMesh(Mesh);
	ConfigureSockets(CurrentChassisId);
	InstalledParts.Reset();
	if (UGameInstance* GameInstance = GetGameInstance())
	{
		if (UStardustProfileSubsystem* Profile = GameInstance->GetSubsystem<UStardustProfileSubsystem>())
		{
			Profile->SelectChassis(CurrentChassisId);
		}
	}
	ClearPartPreview();
	return true;
}

void AStardustHangarPreview::ConfigureSockets(FName ChassisId)
{
	Sockets.Reset();
	auto AddSocket = [this](FName Id, FName Family, FName Size, const FVector& Location, TArray<FName> AcceptedSizes = {})
	{
		FStardustSocketDefinition Socket;
		Socket.Id = Id;
		Socket.AcceptedFamilies.Add(Family);
		Socket.Size = Size;
		Socket.AcceptedSizes = MoveTemp(AcceptedSizes);
		Socket.RelativeTransform = FTransform(Location);
		Sockets.Add(Socket);
	};
	const bool bLight = ChassisId == TEXT("wraith");
	const bool bHeavy = ChassisId == TEXT("bastion");
	const bool bNomad = ChassisId == TEXT("nomad");
	FName EngineSize = TEXT("M");
	TArray<FName> EngineAcceptedSizes;
	if (bHeavy) EngineSize = TEXT("L");
	if (bLight) { EngineSize = NAME_None; EngineAcceptedSizes = {TEXT("S"), TEXT("M")}; }
	AddSocket(TEXT("Engine"), TEXT("Engine"), EngineSize, FVector(0, 0, 80), MoveTemp(EngineAcceptedSizes));
	FName PropulsionSize = bHeavy ? FName(TEXT("L")) : (bLight ? FName(TEXT("S")) : FName(TEXT("M")));
	TArray<FName> PropulsionAcceptedSizes;
	if (bLight) PropulsionAcceptedSizes.Add(TEXT("S"));
	AddSocket(TEXT("Propulsion"), TEXT("Propulsion"), PropulsionSize, FVector(0, 0, -65), MoveTemp(PropulsionAcceptedSizes));
	if (ChassisId == TEXT("vortex")) AddSocket(TEXT("PropulsionC"), TEXT("Propulsion"), NAME_None, FVector(0, 65, -45), {TEXT("S"), TEXT("M")});
	FName WingSize = bHeavy ? FName(TEXT("L")) : FName(TEXT("M"));
	TArray<FName> WingAcceptedSizes;
	if (bNomad) WingAcceptedSizes = {TEXT("M"), TEXT("L")};
	AddSocket(TEXT("Wings"), TEXT("Wings"), WingSize, FVector(0, 0, 15), MoveTemp(WingAcceptedSizes));
	FName ArmorSize = bHeavy ? FName(TEXT("L")) : (bLight ? FName(TEXT("S")) : FName(TEXT("M")));
	TArray<FName> ArmorAcceptedSizes;
	if (bLight) ArmorAcceptedSizes.Add(TEXT("S"));
	AddSocket(TEXT("Armor"), TEXT("Armor"), ArmorSize, FVector(0, 0, 5), MoveTemp(ArmorAcceptedSizes));
	if (bHeavy) AddSocket(TEXT("Armor2"), TEXT("Armor"), TEXT("L"), FVector(0, 0, -15));
	FName ReactorSize = bHeavy ? FName(TEXT("L")) : (bLight ? NAME_None : FName(TEXT("M")));
	TArray<FName> ReactorAcceptedSizes;
	if (bLight) ReactorAcceptedSizes = {TEXT("S"), TEXT("M")};
	AddSocket(TEXT("Reactor"), TEXT("Reactor"), ReactorSize, FVector(0, 0, 45), MoveTemp(ReactorAcceptedSizes));
	FName CoolingSize = (bHeavy || bNomad) ? FName(TEXT("L")) : (bLight ? FName(TEXT("S")) : FName(TEXT("M")));
	TArray<FName> CoolingAcceptedSizes;
	if (bLight) CoolingAcceptedSizes.Add(TEXT("S"));
	AddSocket(TEXT("Cooling"), TEXT("Cooling"), CoolingSize, FVector(0, -55, 35), MoveTemp(CoolingAcceptedSizes));
	FName TailSize = bHeavy ? FName(TEXT("L")) : (bLight ? FName(TEXT("S")) : FName(TEXT("M")));
	TArray<FName> TailAcceptedSizes;
	if (bLight) TailAcceptedSizes.Add(TEXT("S"));
	AddSocket(TEXT("Tail"), TEXT("Tail"), TailSize, FVector(0, 0, -95), MoveTemp(TailAcceptedSizes));
	FStardustSocketDefinition Utility;
	Utility.Id = TEXT("Utility"); Utility.AcceptedFamilies.Add(TEXT("Utility")); Utility.Size = NAME_None; Utility.RelativeTransform = FTransform(FVector(0, 80, 35)); Sockets.Add(Utility);
	if (bNomad) { FStardustSocketDefinition Aux = Utility; Aux.Id = TEXT("Aux"); Aux.RelativeTransform = FTransform(FVector(0, -80, 35)); Sockets.Add(Aux); }
}

void AStardustHangarPreview::SetPartMaterial(bool bCompatible)
{
	if (bCompatible || !IncompatibleMaterial)
	{
		PartPreview->SetMaterial(0, nullptr);
	}
	else
	{
		PartPreview->SetMaterial(0, IncompatibleMaterial);
	}
}

void AStardustHangarPreview::ClearPartPreview()
{
	PartPreview->SetStaticMesh(nullptr);
}
