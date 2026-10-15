#include "StardustHangarPreview.h"
#include "StardustProfileSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"

AStardustHangarPreview::AStardustHangarPreview()
{
	PrimaryActorTick.bCanEverTick = true;
	ChassisPreview = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ChassisPreview"));
	SetRootComponent(ChassisPreview);
	ChassisPreview->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	PartPreview = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PartPreview"));
	PartPreview->SetupAttachment(ChassisPreview);
	PartPreview->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	FStardustSocketDefinition EngineSocket;
	EngineSocket.Id = TEXT("engine"); EngineSocket.AcceptedFamilies.Add(TEXT("Engine")); EngineSocket.Size = TEXT("M");
	EngineSocket.RelativeTransform = FTransform(FVector(0.0f, 0.0f, 80.0f));
	Sockets.Add(EngineSocket);
	FStardustSocketDefinition UtilitySocket;
	UtilitySocket.Id = TEXT("utility"); UtilitySocket.AcceptedFamilies.Add(TEXT("Utility")); UtilitySocket.Size = TEXT("M");
	UtilitySocket.RelativeTransform = FTransform(FVector(0.0f, 100.0f, 35.0f));
	Sockets.Add(UtilitySocket);
}

void AStardustHangarPreview::BeginPlay()
{
	Super::BeginPlay();
	if (UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Stardust/Vehicles/strix.strix")))
	{
		ChassisPreview->SetStaticMesh(Mesh);
	}
	if (!IncompatibleMaterial)
	{
		IncompatibleMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Stardust/Materials/M_Incompatible.M_Incompatible"));
	}
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
	if (!bCompatible && IncompatibleMaterial) PartPreview->SetMaterial(0, IncompatibleMaterial);
	else PartPreview->SetMaterial(0, nullptr);
	if (!bCompatible && GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 2.0f, FColor::Red, TEXT("MODULO INCOMPATIVEL - nao pode ser instalado"));
	}
	return bCompatible;
}

void AStardustHangarPreview::ClearPartPreview()
{
	PartPreview->SetStaticMesh(nullptr);
}
