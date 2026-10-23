#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "EXCraftAudio.generated.h"

class UAudioComponent;
class USoundWaveProcedural;

struct FEXCraftAudioInput
{
	float SpeedMps = 0.0f;
	float Throttle = 0.0f;
	float Steer = 0.0f;
	float HeightM = 99.0f;
	float Impact = 0.0f;
	bool bBoosting = false;
	bool bGrounded = false;
	bool bDrifting = false;
	bool bHangar = false;
	bool bRaceHold = false;
	bool bViewer = true;
};

/** Live synthesis (no looping wav). Engine, wind, hover and hits follow the craft each frame. */
UCLASS(ClassGroup = (Flight), meta = (BlueprintSpawnableComponent))
class EXTRACTINGSTARDUST_API UEXCraftAudio : public UActorComponent
{
	GENERATED_BODY()

public:
	UEXCraftAudio();
	void BeginAudio();
	void UpdateAudio(float Dt, const FEXCraftAudioInput& Input);
	void Bang(float Strength);

private:
	void EnsurePlaying();
	void Render(int32 Frames, const FEXCraftAudioInput& Input);

	UPROPERTY() TObjectPtr<UAudioComponent> Voice;
	UPROPERTY() TObjectPtr<USoundWaveProcedural> Wave;

	uint32 Noise = 0xA341316Cu;
	float EnginePhase = 0.0f, HoverPhase = 0.0f, WindHp = 0.0f, IntakeHp = 0.0f;
	float BangEnv = 0.0f, ScrapeEnv = 0.0f, BoostEnv = 0.0f, Master = 0.0f;
	bool bReady = false;
};
