#include "Flight/EXCraftAudio.h"

#include "Components/AudioComponent.h"
#include "Flight/EXSoundSynth.h"
#include "Sound/SoundWaveProcedural.h"

namespace
{
	constexpr int32 SynthRate = 48000;
	constexpr int32 FramesAhead = SynthRate / 12;   // ~83 ms queued: low latency, no gaps on a frame hitch

	EXSynth::EShip ShipFromName(const FString& Name)
	{
		if (Name.Contains(TEXT("WRAITH")))
		{
			return EXSynth::EShip::Wraith;
		}
		if (Name.Contains(TEXT("NOMAD")))
		{
			return EXSynth::EShip::Nomad;
		}
		if (Name.Contains(TEXT("BASTION")))
		{
			return EXSynth::EShip::Bastion;
		}
		if (Name.Contains(TEXT("VORTEX")))
		{
			return EXSynth::EShip::Vortex;
		}
		return EXSynth::EShip::Strix;
	}
}

UEXCraftAudio::UEXCraftAudio()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UEXCraftAudio::BeginDestroy()
{
	delete Mixer;
	Mixer = nullptr;
	Super::BeginDestroy();
}

void UEXCraftAudio::BeginAudio()
{
	if (bReady)
	{
		return;
	}
	Mixer = new EXSynth::FMixer(static_cast<float>(SynthRate));
	Wave = NewObject<USoundWaveProcedural>(this);
	Wave->SetSampleRate(SynthRate);
	Wave->NumChannels = 2;
	Wave->bLooping = false;
	Wave->SoundGroup = SOUNDGROUP_Default;
	Wave->Volume = 1.0f;
	Voice = NewObject<UAudioComponent>(GetOwner());
	Voice->SetupAttachment(GetOwner()->GetRootComponent());
	Voice->bAutoActivate = false;
	Voice->bAutoDestroy = false;
	Voice->bAllowSpatialization = false;   // the mix is already stereo (pan, Doppler and distance done in the synth)
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
	if (Mixer)
	{
		Mixer->Impact(Strength);
	}
}

void UEXCraftAudio::Landing(float Strength)
{
	if (Mixer)
	{
		Mixer->Landing(Strength);
	}
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

	EXSynth::FListener& Me = Mixer->Me;
	Me.Ship = ShipFromName(Input.ShipName);
	Me.Speed01 = Input.bHangar ? 0.0f : FMath::Max(0.0f, Input.SpeedMps) / FMath::Max(1.0f, Input.TopSpeedMps);
	Me.Throttle = Input.bHangar ? 0.0f : Input.Throttle;
	Me.Boost = Input.bBoosting ? 1.0f : 0.0f;
	Me.Grounded = (Input.bGrounded || Input.bHangar) ? 1.0f : 0.0f;
	Me.Drift = Input.bDrifting ? 1.0f : 0.0f;
	Me.HeightM = Input.HeightM;
	Me.WallLeft = Input.WallLeft;
	Me.WallRight = Input.WallRight;
	Me.Scrape = FMath::Clamp(Input.Impact, 0.0f, 1.0f);
	Me.Music = Input.Music;
	Me.Master = Input.bHangar ? 0.35f : (Input.bRaceHold ? 0.6f : 1.0f);
	if (Input.bBoosting && !bWasBoosting)
	{
		Mixer->BoostKick(1.0f);
	}
	bWasBoosting = Input.bBoosting;
	for (int32 K = 0; K < EXSynth::kMaxOthers; ++K)
	{
		EXSynth::FOther& O = Mixer->Others[K];
		O.bActive = K < Input.Others.Num();
		if (!O.bActive)
		{
			continue;
		}
		const FEXCraftAudioOther& In = Input.Others[K];
		O.Ship = ShipFromName(In.ShipName);
		O.Speed01 = In.Speed01;
		O.Throttle = In.Throttle;
		O.Boost = In.bBoosting ? 1.0f : 0.0f;
		O.Gain = In.Gain;
		O.Pan = In.Pan;
		O.PitchMul = In.PitchMul;
		O.Muffle = In.Muffle;
	}

	const int32 Queued = Wave ? Wave->GetAvailableAudioByteCount() / (2 * sizeof(int16)) : 0;
	int32 Need = FramesAhead - Queued;
	if (Need < SynthRate / 60)
	{
		return;
	}
	Need = FMath::Min(Need, SynthRate / 6);
	Scratch.SetNumUninitialized(Need * 2, EAllowShrinking::No);
	Pcm.SetNumUninitialized(Need * 2, EAllowShrinking::No);
	Mixer->Render(Scratch.GetData(), Need);
	for (int32 I = 0; I < Need * 2; ++I)
	{
		Pcm[I] = static_cast<int16>(FMath::Clamp(Scratch[I], -1.0f, 1.0f) * 32000.0f);
	}
	Wave->QueueAudio(reinterpret_cast<const uint8*>(Pcm.GetData()), Need * 2 * sizeof(int16));
}
