#include "Game/EXAssetWarmer.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Modules/ModuleManager.h"

void UEXAssetWarmer::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	IAssetRegistry& Registry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();
	const TArray<FString> Folders = { TEXT("/Game/UI"), TEXT("/Game/Ships"), TEXT("/Game/FX") };
#if WITH_EDITOR
	// The editor may still be scanning the project; a packaged game reads the registry it was cooked with.
	Registry.ScanPathsSynchronous(Folders);
#endif
	TArray<FSoftObjectPath> Paths;
	for (const FString& Folder : Folders)
	{
		TArray<FAssetData> Assets;
		Registry.GetAssetsByPath(FName(*Folder), Assets, true);
		for (const FAssetData& Asset : Assets)
		{
			Paths.Add(Asset.GetSoftObjectPath());
		}
	}
	if (Paths.Num() > 0)
	{
		Handle = Streamable.RequestAsyncLoad(Paths, FStreamableDelegate(), FStreamableManager::AsyncLoadHighPriority);
	}
	UE_LOG(LogTemp, Display, TEXT("EXPERF a carregar em fundo %d recursos (UI, pecas das naves, explosao)"), Paths.Num());
}

void UEXAssetWarmer::Deinitialize()
{
	if (Handle.IsValid())
	{
		Handle->ReleaseHandle();
		Handle.Reset();
	}
	Super::Deinitialize();
}
