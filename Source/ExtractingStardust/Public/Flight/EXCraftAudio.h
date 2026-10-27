#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "EXCraftAudio.generated.h"

class UAudioComponent;
class USoundWaveProcedural;
namespace EXSynth { class FMixer; }

/** Another craft as heard from the camera (placed by AEXHoverCraft). */
struct FEXCraftAudioOther
{
	FString ShipName;
	float Speed01 = 0.0f;
	float Throttle = 0.0f;
	bool bBoosting = false;
	float Gain = 0.0f;      // distance attenuation
	float Pan = 0.0f;       // -1 left .. 1 right
	float PitchMul = 1.0f;  // Doppler
	float Muffle = 0.0f;    // 0 close, 1 far
};

struct FEXCraftAudioInput
{
	FString ShipName;
	float SpeedMps = 0.0f;
	float TopSpeedMps = 118.0f;
	float Throttle = 0.0f;
	float Steer = 0.0f;
	float HeightM = 99.0f;
	float Impact = 0.0f;      // scraping / shaking against something (0..1)
	float WallLeft = 0.0f;    // wall close on that side (0 far, 1 touching)
	float WallRight = 0.0f;
	bool bBoosting = false;
	bool bGrounded = false;
	bool bDrifting = false;
	bool bHangar = false;
	float Music = 0.0f;       // menu and hangar music (0..1)
	bool bRaceHold = false;
	bool bViewer = true;
	TArray<FEXCraftAudioOther, TInlineAllocator<8>> Others;
};

/**
 * The race sound, synthesised live (no recorded loops): EXSoundSynth.h does the DSP (the plasma engine with its own
 * timbre per ship, wind, wall whoosh, hover hum, drift and scrape, impacts, landings, boost, the rivals passing with
 * Doppler and pan). This component feeds it every frame and streams its stereo output (48 kHz) to a 2D sound.
 * Only the craft whose camera is on screen plays; the others are heard through it.
 * Offline preview of the same code: Scripts/audio/render_sound_preview.cpp.
 */
UCLASS(ClassGroup = (Flight), meta = (BlueprintSpawnableComponent))
class EXTRACTINGSTARDUST_API UEXCraftAudio : public UActorComponent
{
	GENERATED_BODY()

public:
	UEXCraftAudio();
	virtual void BeginDestroy() override;

	void BeginAudio();
	void UpdateAudio(float Dt, const FEXCraftAudioInput& Input);
	/** A hit (wall, craft, life lost): thump, crunch and clank, 0..1. */
	void Bang(float Strength);
	/** Touchdown after a jump, 0..1. */
	void Landing(float Strength);
	/** A call-out: 0-4 a piece picked up (rarity), 10 countdown beep, 11 start, 12 checkpoint, 13 a rival's pieces spill. */
	void Chime(int32 Kind);

private:
	void EnsurePlaying();

	UPROPERTY() TObjectPtr<UAudioComponent> Voice;
	UPROPERTY() TObjectPtr<USoundWaveProcedural> Wave;

	/** Owned; plain pointer so this header needs only the forward declaration (freed in BeginDestroy). */
	EXSynth::FMixer* Mixer = nullptr;
	TArray<float> Scratch;
	TArray<int16> Pcm;
	bool bReady = false, bWasBoosting = false;
};
