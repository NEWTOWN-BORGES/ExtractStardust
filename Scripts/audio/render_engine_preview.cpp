// Engine v2 preview (2026-11-02): renders the engine v2 (FEngineV2, EXSoundSynth.h), without the Unreal.
//   g++ -O2 -std=c++17 -I Source/ExtractingStardust/Private/Flight Scripts/audio/render_engine_preview.cpp -o render_engine
//   ./render_engine <pasta>    ->  motor_corrida.wav, motores_naves.wav, antes_depois.wav
// A light wind is added so the speed reads (the game has its own, richer one in FMixer).
#include "EXSoundSynth.h"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <string>
#include <vector>

using namespace EXSynth;

static const float Fs = 48000.0f;

struct FWav
{
	std::vector<int16_t> Data;
	float Peak = 0.0f;
	double SumSq = 0.0;
	void Add(float L, float R)
	{
		for (float V : { L, R })
		{
			V = SoftClip(V);
			Peak = std::fmax(Peak, std::fabs(V));
			SumSq += V * V;
			Data.push_back(static_cast<int16_t>(std::lround(V * 32000.0f)));
		}
	}
	bool Write(const std::string& Path) const
	{
		FILE* F = std::fopen(Path.c_str(), "wb");
		if (!F) { return false; }
		const uint32_t Bytes = static_cast<uint32_t>(Data.size() * 2);
		auto U32 = [&](uint32_t V) { std::fwrite(&V, 4, 1, F); };
		auto U16 = [&](uint16_t V) { std::fwrite(&V, 2, 1, F); };
		std::fwrite("RIFF", 1, 4, F); U32(36 + Bytes); std::fwrite("WAVEfmt ", 1, 8, F);
		U32(16); U16(1); U16(2); U32(48000); U32(48000 * 4); U16(4); U16(16);
		std::fwrite("data", 1, 4, F); U32(Bytes);
		std::fwrite(Data.data(), 2, Data.size(), F);
		std::fclose(F);
		std::printf("%s  %.1f s  peak %.2f  rms %.3f\n", Path.c_str(), Data.size() / 2 / Fs, Peak,
			std::sqrt(SumSq / (Data.empty() ? 1 : Data.size())));
		return true;
	}
};

struct FWind
{
	FRng Rng{ 99u };
	FPink PL, PR;
	FSvf BL, BR;
	void Sample(float V, float& L, float& R)
	{
		BL.Run(PL.Next(Rng), 300.0f + 2600.0f * V, 0.6f, Fs);
		BR.Run(PR.Next(Rng), 340.0f + 2700.0f * V, 0.6f, Fs);
		const float G = 0.02f + 0.30f * V * V;
		L = BL.Bp * G;
		R = BR.Bp * G;
	}
};

struct FCtl { float Throttle = 0.0f, Boost = 0.0f, Brake = 0.0f, Grounded = 1.0f; bool bHeld = false; };

// Drives one engine with a script of the pilot's inputs; the speed comes from a tiny craft model.
static void Render(FWav& Wav, EShip Ship, float Seconds, const std::function<FCtl(float)>& Script, bool bOld = false)
{
	FEngineV2 Eng(11u);
	FEngine Old(11u);
	FWind Wind;
	const FEngineTimbre T = EngineTimbreFor(Ship);
	const FShipTimbre TOld = TimbreFor(Ship);
	float V = 0.0f;
	const int N = static_cast<int>(Seconds * Fs);
	for (int I = 0; I < N; ++I)
	{
		const float Tm = I / Fs;
		const FCtl C = Script(Tm);
		if (C.bHeld) { V = 0.0f; }
		else
		{
			V += (C.Throttle * 0.30f * (1.12f - V) * (V < 0.15f ? 1.4f : 1.0f) + C.Boost * 0.35f * (1.25f - V)
				- C.Brake * 0.45f - 0.03f * V) / Fs;
			V = V < 0.0f ? 0.0f : V;
		}
		float L = 0.0f, R = 0.0f;
		if (bOld) { L = R = Old.Sample(TOld, V, C.Throttle, C.Boost, 1.0f, Fs, true); }
		else { Eng.Sample(T, V, C.Throttle, C.Boost, 1.0f, C.Grounded, Fs, true, L, R); }
		if (std::getenv("EX_ENGINE_LOG") && !bOld && I % static_cast<int>(0.5f * Fs) == 0)
		{
			std::printf("t %5.1f v %.2f thr %.1f boost %.0f stage %d rpm %.2f\n", Tm, V, C.Throttle, C.Boost, Eng.GetStage(), Eng.GetRpm());
		}
		float WL = 0.0f, WR = 0.0f;
		Wind.Sample(V, WL, WR);
		const float Fade = std::fmin(1.0f, std::fmin(Tm / 0.05f, (Seconds - Tm) / 0.4f));
		Wav.Add((0.62f * L + WL) * Fade, (0.62f * R + WR) * Fade);
	}
}

static bool In(float T, float A, float B) { return T >= A && T < B; }

int main(int Argc, char** Argv)
{
	const std::string Out = Argc > 1 ? Argv[1] : ".";

	// A race for the STRIX: grid blips, launch limiter, stages, a lift, drift, boost, a jump, top speed, braking
	// with downshifts, a second run and a final boost.
	{
		FWav Wav;
		Render(Wav, EShip::Strix, 38.0f, [](float T)
		{
			FCtl C;
			C.bHeld = T < 4.0f;
			if (T < 4.0f) { C.Throttle = (In(T, 0.6f, 0.85f) || In(T, 1.5f, 1.75f) || In(T, 2.4f, 2.65f)) ? 0.9f : (T >= 3.0f ? 1.0f : 0.0f); }
			else if (T < 11.0f) { C.Throttle = 1.0f; }
			else if (T < 11.6f) { C.Brake = 0.3f; }
			else if (T < 14.0f) { C.Throttle = 0.65f; }
			else if (T < 27.0f) { C.Throttle = 1.0f; C.Boost = In(T, 14.0f, 17.0f) ? 1.0f : 0.0f; C.Grounded = In(T, 18.5f, 19.8f) ? 0.0f : 1.0f; }
			else if (T < 29.5f) { C.Brake = 0.4f; }
			else if (T < 36.5f) { C.Throttle = 1.0f; C.Boost = In(T, 34.0f, 36.5f) ? 1.0f : 0.0f; }
			return C;
		});
		Wav.Write(Out + "/motor_corrida.wav");
	}

	// The five ships: two blips, launch limiter, run through the stages, boost, lift.
	{
		FWav Wav;
		for (EShip Ship : { EShip::Strix, EShip::Wraith, EShip::Nomad, EShip::Bastion, EShip::Vortex })
		{
			Render(Wav, Ship, 9.5f, [](float T)
			{
				FCtl C;
				C.bHeld = T < 2.2f;
				C.Throttle = (In(T, 0.3f, 0.55f) || In(T, 0.9f, 1.15f) || In(T, 1.4f, 8.0f)) ? 1.0f : 0.0f;
				C.Boost = In(T, 6.0f, 7.6f) ? 1.0f : 0.0f;
				return C;
			});
		}
		Wav.Write(Out + "/motores_naves.wav");
	}

	// Before and after, same run (STRIX): the old engine, a short silence, the new one.
	{
		FWav Wav;
		auto Run = [](float T)
		{
			FCtl C;
			C.bHeld = T < 1.0f;
			C.Throttle = In(T, 1.0f, 8.5f) ? 1.0f : 0.0f;
			C.Boost = In(T, 6.0f, 7.5f) ? 1.0f : 0.0f;
			return C;
		};
		Render(Wav, EShip::Strix, 10.0f, Run, true);
		for (int I = 0; I < static_cast<int>(0.8f * Fs); ++I) { Wav.Add(0.0f, 0.0f); }
		Render(Wav, EShip::Strix, 10.0f, Run, false);
		Wav.Write(Out + "/antes_depois.wav");
	}
	return 0;
}
