// Offline preview of the race sound (Source/ExtractingStardust/Private/Flight/EXSoundSynth.h, the same code the game
// runs): writes WAVs of scripted moments so the sound can be heard and tuned without the engine.
// Build and run (any C++17 compiler):
//   g++ -O2 -std=c++17 -I Source/ExtractingStardust/Private/Flight Scripts/audio/render_sound_preview.cpp -o render_sound
//   ./render_sound <out_dir>
// Writes corrida.wav (one run: start, acceleration, boost, drift, wall, scrape, impact, jump, landing),
// passagens.wav (four rivals passing left and right, with Doppler) and naves.wav (the five ships one after another).
#include "EXSoundSynth.h"

#include <cmath>
#include <cstdio>
#include <cstdint>
#include <string>
#include <vector>

using namespace EXSynth;

static const float Fs = 48000.0f;
static const int Block = 256;

struct FWav
{
	std::vector<int16_t> Data;
	float Peak = 0.0f;
	double SumSq = 0.0;
	void Add(const float* Buf, int Frames)
	{
		for (int I = 0; I < 2 * Frames; ++I)
		{
			const float V = Buf[I];
			Peak = std::fmax(Peak, std::fabs(V));
			SumSq += V * V;
			Data.push_back(static_cast<int16_t>(std::lround(std::fmax(-1.0f, std::fmin(1.0f, V)) * 32000.0f)));
		}
	}
	bool Write(const std::string& Path) const
	{
		FILE* F = std::fopen(Path.c_str(), "wb");
		if (!F)
		{
			return false;
		}
		const uint32_t DataBytes = static_cast<uint32_t>(Data.size() * 2);
		auto U32 = [&](uint32_t V) { std::fwrite(&V, 4, 1, F); };
		auto U16 = [&](uint16_t V) { std::fwrite(&V, 2, 1, F); };
		std::fwrite("RIFF", 1, 4, F); U32(36 + DataBytes); std::fwrite("WAVEfmt ", 1, 8, F);
		U32(16); U16(1); U16(2); U32(48000); U32(48000 * 4); U16(4); U16(16);
		std::fwrite("data", 1, 4, F); U32(DataBytes);
		std::fwrite(Data.data(), 2, Data.size(), F);
		std::fclose(F);
		std::printf("%s  %.1f s  peak %.2f  rms %.3f\n", Path.c_str(), Data.size() / 2 / Fs, Peak,
			std::sqrt(SumSq / (Data.empty() ? 1 : Data.size())));
		return true;
	}
};

static float Smooth(float T, float T0, float T1) { const float X = Clamp01((T - T0) / (T1 - T0)); return X * X * (3 - 2 * X); }

int main(int Argc, char** Argv)
{
	const std::string Out = Argc > 1 ? Argv[1] : ".";
	float Buf[2 * Block];

	// ---- 1. One run with the WRAITH.
	{
		FMixer Mix(Fs);
		FWav Wav;
		Mix.Me.Ship = EShip::Wraith;
		bool bKick = false, bHit = false, bLand = false;
		for (float T = 0.0f; T < 30.0f; T += Block / Fs)
		{
			FListener& M = Mix.Me;
			const bool bGo = T > 3.0f;
			M.Master = bGo ? 1.0f : 0.55f;
			M.Throttle = !bGo ? 0.0f : (T < 26.0f ? 1.0f : 0.3f);
			float V = bGo ? 1.0f - std::exp(-(T - 3.0f) / 4.0f) : 0.0f;
			V += 0.14f * Smooth(T, 13.0f, 14.5f) * (1.0f - Smooth(T, 16.0f, 18.0f));
			V *= 1.0f - 0.45f * Smooth(T, 26.0f, 30.0f);
			M.Speed01 = V;
			M.Boost = (T > 13.0f && T < 16.0f) ? 1.0f : 0.0f;
			if (T > 13.0f && !bKick) { Mix.BoostKick(1.0f); bKick = true; }
			M.Drift = (T > 17.0f && T < 19.2f) ? 1.0f : 0.0f;
			M.WallRight = Smooth(T, 20.0f, 22.5f) * (1.0f - Smooth(T, 23.6f, 24.0f)) * 0.9f;
			M.Scrape = (T > 23.0f && T < 23.6f) ? 0.7f : 0.0f;
			if (T > 23.6f && !bHit) { Mix.Impact(1.0f); bHit = true; }
			const bool bAir = T > 24.2f && T < 25.5f;
			M.Grounded = bAir ? 0.0f : 1.0f;
			M.HeightM = bAir ? 8.0f : 1.5f;
			if (T > 25.5f && !bLand) { Mix.Landing(0.8f); bLand = true; }
			Mix.Render(Buf, Block);
			Wav.Add(Buf, Block);
		}
		Wav.Write(Out + "/corrida.wav");
	}

	// ---- 2. Rivals passing (the STRIX cruising at ~400 km/h).
	{
		FMixer Mix(Fs);
		FWav Wav;
		Mix.Me.Ship = EShip::Strix;
		struct FPass { EShip Ship; float X0, Vrel, Y, T0; float Boost; };
		const FPass Pass[4] = { { EShip::Vortex, -70.0f, 38.0f, -9.0f, 1.0f, 0.0f }, { EShip::Nomad, -60.0f, 22.0f, 11.0f, 5.0f, 0.0f },
			{ EShip::Bastion, 90.0f, -26.0f, -12.0f, 9.0f, 0.0f }, { EShip::Wraith, -80.0f, 45.0f, 8.0f, 13.0f, 1.0f } };
		const float C = 420.0f;
		float PrevD[4] = { 0, 0, 0, 0 };
		for (float T = 0.0f; T < 20.0f; T += Block / Fs)
		{
			Mix.Me.Speed01 = 0.85f;
			Mix.Me.Throttle = 0.8f;
			for (int K = 0; K < 4; ++K)
			{
				const FPass& P = Pass[K];
				FOther& O = Mix.Others[K];
				const float Tl = T - P.T0;
				O.bActive = Tl > -1.0f && Tl < 7.0f;
				const float X = P.X0 + P.Vrel * Tl;
				const float D = std::sqrt(X * X + P.Y * P.Y) + 1.0f;
				const float Radial = Tl > -0.99f ? (D - PrevD[K]) / (Block / Fs) : 0.0f;
				PrevD[K] = D;
				O.Ship = P.Ship;
				O.Speed01 = 0.85f + P.Vrel / 118.0f;
				O.Throttle = 0.9f;
				O.Boost = P.Boost;
				O.Gain = 1.0f / (1.0f + std::pow(D / 15.0f, 1.4f));
				O.Pan = P.Y / D;
				O.PitchMul = std::fmax(0.6f, std::fmin(1.7f, C / (C + Radial)));
				O.Muffle = Clamp01(D / 250.0f);
			}
			Mix.Render(Buf, Block);
			Wav.Add(Buf, Block);
		}
		Wav.Write(Out + "/passagens.wav");
	}

	// ---- 3. The five ships: idle, acceleration, boost, release.
	{
		FMixer Mix(Fs);
		FWav Wav;
		const EShip Ships[5] = { EShip::Strix, EShip::Wraith, EShip::Nomad, EShip::Bastion, EShip::Vortex };
		for (int S = 0; S < 5; ++S)
		{
			Mix = FMixer(Fs);
			Mix.Me.Ship = Ships[S];
			bool bKick = false;
			for (float T = 0.0f; T < 9.5f; T += Block / Fs)
			{
				FListener& M = Mix.Me;
				M.Throttle = (T > 1.0f && T < 8.0f) ? 1.0f : 0.0f;
				M.Speed01 = T < 1.0f ? 0.0f : (1.0f - std::exp(-(T - 1.0f) / 2.2f)) * (1.0f - 0.5f * Smooth(T, 8.0f, 9.5f));
				M.Boost = (T > 6.0f && T < 8.0f) ? 1.0f : 0.0f;
				if (T > 6.0f && !bKick) { Mix.BoostKick(0.8f); bKick = true; }
				M.Master = T > 9.2f ? 0.0f : 1.0f;
				Mix.Render(Buf, Block);
				Wav.Add(Buf, Block);
			}
		}
		Wav.Write(Out + "/naves.wav");
	}
	return 0;
}
