#include "Flight/EXCraftAudio.h"

#include "Components/AudioComponent.h"
#include "Sound/SoundWaveProcedural.h"

namespace
{
	constexpr int32 kRate = 24000;
	constexpr int32 kAhead = kRate / 12;

	float NextNoise(uint32& State)
	{
		State ^= State << 13;
		State ^= State >> 17;
		State ^= State << 5;
		return (State & 0xFFFF) / 32768.0f - 1.0f;
	}
}

UEXCraftAudio::UEXCraftAudio()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UEXCraftAudio::BeginAudio()
{
	if (bReady)
	{
		return;
	}
	Wave = NewObject<USoundWaveProcedural>(this);
	Wave->SetSampleRate(kRate);
	Wave->NumChannels = 1;
	Wave->bLooping = false;
	Wave->SoundGroup = SOUNDGROUP_Default;
	Wave->Volume = 1.0f;
	Voice = NewObject<UAudioComponent>(GetOwner());
	Voice->SetupAttachment(GetOwner()->GetRootComponent());
	Voice->bAutoActivate = false;
	Voice->bAutoDestroy = false;
	Voice->SetSound(Wave);
	Voice->RegisterComponent();
	bReady = true;
	EnsurePlaying();
}

void UEXCraftAudio::EnsurePlaying()
{
	if (Voice && !Voice->IsPlaying())
	{
		Voice->Play();
	}
}

void UEXCraftAudio::Bang(float Strength)
{
	BangEnv = FMath::Max(BangEnv, FMath::Clamp(Strength, 0.0f, 1.0f));
}

void UEXCraftAudio::UpdateAudio(float Dt, const FEXCraftAudioInput& Input)
{
	if (!Input.bViewer)
	{
		if (Voice && Voice->IsPlaying())
		{
			Voice->Stop();
		}
		return;
	}
	BeginAudio();
	EnsurePlaying();
	ScrapeEnv = FMath::FInterpTo(ScrapeEnv, FMath::Clamp(Input.Impact, 0.0f, 1.0f), Dt, 14.0f);
	BoostEnv = FMath::FInterpTo(BoostEnv, Input.bBoosting ? 1.0f : 0.0f, Dt, 8.0f);
	const float Want = (Input.bHangar || Input.bRaceHold) ? 0.22f : 1.0f;
	Master = FMath::FInterpTo(Master, Want, Dt, 3.0f);
	BangEnv = FMath::Max(0.0f, BangEnv - Dt * 4.5f);

	const int32 Queued = Wave ? Wave->GetAvailableAudioByteCount() / 2 : 0;
	int32 Need = kAhead - Queued;
	if (Need < kRate / 40)
	{
		return;
	}
	Need = FMath::Min(Need, kRate / 8);
	Render(Need, Input);
}

void UEXCraftAudio::Render(int32 Frames, const FEXCraftAudioInput& Input)
{
	TArray<int16> Pcm;
	Pcm.SetNumUninitialized(Frames);
	const float Speed01 = FMath::Clamp(Input.SpeedMps / 118.0f, 0.0f, 1.35f);
	const float EngineHz = Input.bHangar ? 28.0f : (34.0f + Speed01 * 72.0f + Input.Throttle * 18.0f + BoostEnv * 22.0f);
	const float HoverHz = 21.0f + Speed01 * 6.0f;
	const float EngineGain = Input.bHangar ? 0.10f : (0.12f + 0.28f * FMath::Max(Input.Throttle, Speed01 * 0.65f));
	const float WindGain = Input.bHangar ? 0.04f : (Speed01 * Speed01 * 0.42f + FMath::Abs(Input.Steer) * Speed01 * 0.08f);
	const float HoverGain = (Input.bGrounded || Input.bHangar) ? (0.07f + 0.04f * Speed01) : 0.02f;
	const float DriftGain = Input.bDrifting ? 0.10f : 0.0f;

	for (int32 I = 0; I < Frames; ++I)
	{
		const float N = NextNoise(Noise);
		EnginePhase = FMath::Fmod(EnginePhase + EngineHz / kRate, 1.0f);
		HoverPhase = FMath::Fmod(HoverPhase + HoverHz / kRate, 1.0f);
		const float TwoPi = 2.0f * PI;
		const float E = FMath::Sin(EnginePhase * TwoPi) * 0.55f
			+ FMath::Sin(EnginePhase * TwoPi * 2.03f) * 0.28f
			+ FMath::Sin(EnginePhase * TwoPi * 3.07f) * 0.12f;
		IntakeHp += 0.18f * (N - IntakeHp);
		const float Intake = (N - IntakeHp) * (0.07f + Input.Throttle * 0.16f);
		WindHp += 0.08f * (N - WindHp);
		const float Wind = (N - WindHp) * WindGain;
		const float Hover = FMath::Sin(HoverPhase * TwoPi) * HoverGain;
		const float Scrape = ScrapeEnv * N * 0.35f;
		const float Bang = BangEnv * N * 0.85f;
		const float Sample = (E * EngineGain + Intake + Wind + Hover + Scrape + Bang + DriftGain * N * 0.2f) * Master * 0.55f;
		Pcm[I] = static_cast<int16>(FMath::Clamp(Sample, -1.0f, 1.0f) * 30000.0f);
	}
	Wave->QueueAudio(reinterpret_cast<uint8*>(Pcm.GetData()), Frames * sizeof(int16));
}
