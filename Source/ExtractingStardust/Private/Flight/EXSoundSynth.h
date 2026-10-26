#pragma once

// EXSoundSynth: the race sound, synthesised live (no recorded loops), in plain C++ so the same code runs in the game
// (UEXCraftAudio) and in the offline preview renderer (Scripts/audio/render_sound_preview.cpp, which writes WAVs).
//
// One stereo mix for the craft whose camera is on screen:
//  - its plasma engine: a band-limited sawtooth core per engine (detuned, so two or three engines beat), through a
//    resonant low-pass that opens with the throttle; a combustion rasp (noise bursts on every engine cycle, the
//    podrace "growl"); the turbine whine high above; a sub an octave down for weight; the afterburner roar on boost.
//    Pitch follows speed and throttle with inertia; every ship has its own timbre (FShipTimbre);
//  - the air: stereo wind that rises in pitch and level with speed, gusts, the tearing hiss near top speed, and the
//    whoosh of a canyon wall close on one side;
//  - contact: hover hum near the ground, drift skid, wall scrape;
//  - events: impact (thump, crunch, metal clank), landing thump, boost ignition (thump and a rising whoosh);
//  - the other craft (up to kMaxOthers): their engines placed by the game (gain, pan, Doppler pitch, distance
//    muffling), so they pass by on the left and right;
//  - master: soft limiter.
// Units: Hz, seconds, linear gains. Inputs 0..1 unless said otherwise.

#include <cmath>
#include <cstdint>

namespace EXSynth
{
	constexpr float kPi = 3.14159265358979f;
	constexpr int kMaxOthers = 8;

	inline float Clamp01(float X) { return X < 0.0f ? 0.0f : (X > 1.0f ? 1.0f : X); }
	inline float Lerp(float A, float B, float T) { return A + (B - A) * T; }
	/** Per-sample smoothing coefficient for a time constant in seconds. */
	inline float SmoothCoef(float Seconds, float Fs) { return 1.0f - std::exp(-1.0f / (Seconds * Fs)); }

	struct FRng
	{
		uint32_t S = 0x9E3779B9u;
		explicit FRng(uint32_t Seed = 0x9E3779B9u) : S(Seed ? Seed : 1u) {}
		/** White noise -1..1. */
		float Next()
		{
			S ^= S << 13;
			S ^= S >> 17;
			S ^= S << 5;
			return static_cast<float>(S & 0xFFFFFF) / 8388608.0f - 1.0f;
		}
	};

	/** Pink noise (Paul Kellet's economy filter). */
	struct FPink
	{
		float B0 = 0, B1 = 0, B2 = 0;
		float Next(FRng& Rng)
		{
			const float W = Rng.Next();
			B0 = 0.99765f * B0 + W * 0.0990460f;
			B1 = 0.96300f * B1 + W * 0.2965164f;
			B2 = 0.57000f * B2 + W * 1.0526913f;
			return (B0 + B1 + B2 + W * 0.1848f) * 0.25f;
		}
	};

	/** State-variable filter (topology-preserving, safe to sweep every sample). */
	struct FSvf
	{
		float Ic1 = 0, Ic2 = 0;
		float Lp = 0, Bp = 0, Hp = 0;
		void Run(float X, float Fc, float Q, float Fs)
		{
			Fc = Fc < 20.0f ? 20.0f : (Fc > 0.45f * Fs ? 0.45f * Fs : Fc);
			const float G = std::tan(kPi * Fc / Fs);
			const float K = 1.0f / (Q < 0.3f ? 0.3f : Q);
			const float A1 = 1.0f / (1.0f + G * (G + K));
			const float A2 = G * A1;
			const float A3 = G * A2;
			const float V3 = X - Ic2;
			const float V1 = A1 * Ic1 + A2 * V3;
			const float V2 = Ic2 + A2 * Ic1 + A3 * V3;
			Ic1 = 2.0f * V1 - Ic1;
			Ic2 = 2.0f * V2 - Ic2;
			Lp = V2;
			Bp = V1;
			Hp = X - K * V1 - V2;
		}
	};

	/** Band-limited sawtooth (PolyBLEP). Phase 0..1. */
	inline float SawBlep(float Phase, float Dt)
	{
		float V = 2.0f * Phase - 1.0f;
		if (Phase < Dt)
		{
			const float T = Phase / Dt;
			V -= T + T - T * T - 1.0f;
		}
		else if (Phase > 1.0f - Dt)
		{
			const float T = (Phase - 1.0f) / Dt;
			V -= T * T + T + T + 1.0f;
		}
		return V;
	}

	inline float Wrap(float Phase) { return Phase - std::floor(Phase); }

	/** What makes each ship sound like itself. */
	struct FShipTimbre
	{
		float BaseHz;      // engine fundamental at rest
		float RangeHz;     // added at full rpm
		int Engines;       // 1-3 detuned cores (they beat)
		float Detune;      // relative spread between the cores
		float WhineRatio;  // turbine whine = fundamental x this
		float WhineGain;
		float Rasp;        // combustion growl
		float Sub;         // octave-down weight
		float Bright;      // how far the low-pass opens
	};

	enum class EShip : int { Strix = 0, Wraith, Nomad, Bastion, Vortex, Count };

	inline FShipTimbre TimbreFor(EShip Ship)
	{
		switch (Ship)
		{
		case EShip::Wraith:  return { 42.0f, 86.0f, 3, 0.009f, 30.0f, 0.11f, 0.26f, 0.32f, 0.90f };   // three cores, smooth beat
		case EShip::Nomad:   return { 33.0f, 62.0f, 3, 0.021f, 24.0f, 0.05f, 0.58f, 0.44f, 0.70f };   // heavy, industrial grit
		case EShip::Bastion: return { 29.0f, 54.0f, 1, 0.000f, 21.0f, 0.04f, 0.46f, 0.52f, 0.60f };   // deep, armoured
		case EShip::Vortex:  return { 58.0f, 120.0f, 1, 0.000f, 40.0f, 0.17f, 0.42f, 0.22f, 1.25f };  // high, screaming
		case EShip::Strix:
		default:             return { 46.0f, 92.0f, 2, 0.013f, 34.0f, 0.10f, 0.36f, 0.30f, 1.00f };   // twin stacked cores
		}
	}

	/** One plasma engine. */
	struct FEngine
	{
		float Rpm = 0.0f, Thr = 0.0f, Boost = 0.0f, Pitch = 1.0f;
		float Phase[3] = { 0.0f, 0.37f, 0.71f };
		float SubPhase = 0.0f, WhinePhase = 0.0f, Whine2Phase = 0.0f, CyclePhase = 0.0f;
		float RaspEnv = 0.0f;
		FSvf Core, Rasp, Roar;
		FRng Rng;

		explicit FEngine(uint32_t Seed = 7u) : Rng(Seed) {}

		/** One mono sample. Speed01 and Throttle 0..1 (speed may pass 1 on boost), Boost 0..1, PitchMul = Doppler. */
		float Sample(const FShipTimbre& T, float Speed01, float Throttle, float BoostTarget, float PitchMul, float Fs, bool bFull)
		{
			// Inertia: the rpm follows speed and throttle in ~0.35 s, the throttle itself in ~40 ms.
			Thr += (Throttle - Thr) * SmoothCoef(0.04f, Fs);
			Boost += (BoostTarget - Boost) * SmoothCoef(0.12f, Fs);
			const float RpmTarget = Clamp01(0.62f * Speed01 + 0.38f * Throttle + 0.12f * BoostTarget);
			Rpm += (RpmTarget - Rpm) * SmoothCoef(0.35f, Fs);
			Pitch += (PitchMul - Pitch) * SmoothCoef(0.05f, Fs);

			const float F0 = (T.BaseHz + T.RangeHz * std::pow(Rpm, 0.9f)) * (1.0f + 0.06f * Boost) * Pitch;
			// Core: one sawtooth per engine, detuned around the fundamental.
			float CoreSum = 0.0f;
			for (int E = 0; E < T.Engines; ++E)
			{
				const float F = F0 * (1.0f + T.Detune * (E - 0.5f * (T.Engines - 1)));
				const float Dt = F / Fs;
				Phase[E] = Wrap(Phase[E] + Dt);
				CoreSum += SawBlep(Phase[E], Dt);
			}
			CoreSum /= static_cast<float>(T.Engines);
			const float Cutoff = (160.0f + 3200.0f * (0.25f * Rpm + 0.75f * Thr) + 1800.0f * Boost) * T.Bright;
			Core.Run(CoreSum, Cutoff, 1.1f, Fs);
			float Out = Core.Lp * (0.30f + 0.25f * Thr);

			// Combustion rasp: a noise burst at the start of every engine cycle, band-passed.
			CyclePhase = Wrap(CyclePhase + F0 / Fs);
			const float Burst = std::exp(-CyclePhase * 9.0f) * Rng.Next();
			Rasp.Run(Burst, 700.0f + 2600.0f * Thr + 900.0f * Rpm, 1.4f, Fs);
			Out += Rasp.Bp * T.Rasp * (0.25f + 0.9f * Thr) * 1.6f;

			if (bFull)
			{
				// Turbine whine (two partials) and the sub.
				WhinePhase = Wrap(WhinePhase + F0 * T.WhineRatio / Fs);
				Whine2Phase = Wrap(Whine2Phase + F0 * T.WhineRatio * 1.498f / Fs);
				const float Whine = std::sin(2.0f * kPi * WhinePhase) + 0.35f * std::sin(2.0f * kPi * Whine2Phase);
				Out += Whine * T.WhineGain * (0.15f + 0.85f * std::pow(Rpm, 1.5f)) * 0.5f;
				SubPhase = Wrap(SubPhase + 0.5f * F0 / Fs);
				Out += std::sin(2.0f * kPi * SubPhase) * T.Sub * (0.35f + 0.65f * Thr) * 0.6f;
			}
			// Afterburner roar while boosting.
			Roar.Run(Rng.Next(), 500.0f + 900.0f * Boost, 0.7f, Fs);
			Out += Roar.Lp * Boost * 0.9f;
			return Out;
		}
	};

	/** The craft whose camera is on screen. */
	struct FListener
	{
		EShip Ship = EShip::Strix;
		float Speed01 = 0.0f;   // forward speed / tuned top speed (may pass 1)
		float Throttle = 0.0f;
		float Boost = 0.0f;
		float Grounded = 1.0f;
		float Drift = 0.0f;
		float HeightM = 1.5f;
		float WallLeft = 0.0f;  // how close a wall is on that side (0 far, 1 touching)
		float WallRight = 0.0f;
		float Scrape = 0.0f;    // sliding along a wall
		float Master = 1.0f;    // overall level (menus, countdown duck)
		float Music = 0.0f;     // menu and hangar music level (0 in the race)
	};

	/** Another craft, placed by the game. */
	struct FOther
	{
		bool bActive = false;
		EShip Ship = EShip::Strix;
		float Speed01 = 0.0f, Throttle = 0.0f, Boost = 0.0f;
		float Gain = 0.0f;      // distance attenuation
		float Pan = 0.0f;       // -1 left .. 1 right (seen from the camera)
		float PitchMul = 1.0f;  // Doppler
		float Muffle = 0.0f;    // 0 close and clear, 1 far (air absorption)
	};

	/**
	 * Menu and hangar music (player, 2026-10-25): a slow desert ambience made by the same synth, no recording. Four
	 * detuned-saw voices through a breathing low-pass play a chord loop (Dm9, Bb maj7, F maj7, C add9) at 60 BPM, each
	 * chord taking 8 beats and gliding into the next; a soft sine bass under them; sparse bell notes from the D minor
	 * pentatonic that fade into a stereo echo; and a thin wind. Stereo, about -1..1 before the mixer's level.
	 */
	struct FAmbientMusic
	{
		static constexpr int kVoices = 4;
		float Fs = 48000.0f;
		float BeatLen = 1.0f;             // seconds per beat
		float Clock = 0.0f;               // seconds
		int Chord = 0;
		float Voice[kVoices] = { 220.0f, 220.0f, 220.0f, 220.0f };
		float P1[kVoices] = {}, P2[kVoices] = {};
		float Swell[kVoices] = { 0.0f, 1.7f, 3.1f, 4.6f };
		FSvf Pad[kVoices];
		float BassHz = 73.4f, BassPh = 0.0f;
		float BellHz = 0.0f, BellPh = 0.0f, BellEnv = 0.0f, NextBell = 0.0f;

		FRng Rng{ 0xA11CE5u };
		FPink Pink;
		FSvf Wind;
		float EchoL[40000] = {}, EchoR[40000] = {};
		int EchoPos = 0;
		float EchoLpL = 0.0f, EchoLpR = 0.0f;

		static float Hz(float Midi) { return 440.0f * std::pow(2.0f, (Midi - 69.0f) / 12.0f); }

		void Init(float SampleRate) { Fs = SampleRate; BeatLen = 1.0f; Clock = 0.0f; NextBell = 2.0f; }

		void Sample(float& L, float& R)
		{
			// Chords: bass, then four voices (MIDI notes).
			static const float Chords[4][5] = {
				{ 38, 53, 57, 60, 64 },   // Dm9: D2 / F3 A3 C4 E4
				{ 34, 50, 53, 57, 62 },   // Bb maj7: Bb1 / D3 F3 A3 D4
				{ 41, 48, 52, 57, 60 },   // F maj7: F2 / C3 E3 A3 C4
				{ 36, 55, 60, 62, 64 },   // C add9: C2 / G3 C4 D4 E4
			};
			static const float Bells[7] = { 74, 77, 79, 81, 84, 86, 89 };   // D5 F5 G5 A5 C6 D6 F6
			Clock += 1.0f / Fs;
			const int Now = static_cast<int>(Clock / (BeatLen * 8.0f)) & 3;
			const float Glide = SmoothCoef(2.2f, Fs);
			Chord = Now;
			float PadL = 0.0f, PadR = 0.0f;
			for (int V = 0; V < kVoices; ++V)
			{
				Voice[V] += (Hz(Chords[Chord][1 + V]) - Voice[V]) * Glide;
				Swell[V] += 1.0f / Fs * (0.11f + 0.03f * V);
				const float Breath = 0.65f + 0.35f * std::sin(2.0f * kPi * Swell[V]);
				const float Dt1 = Voice[V] * 0.9965f / Fs, Dt2 = Voice[V] * 1.0035f / Fs;
				P1[V] += Dt1; P1[V] -= std::floor(P1[V]);
				P2[V] += Dt2; P2[V] -= std::floor(P2[V]);
				const float Saw = 0.5f * (SawBlep(P1[V], Dt1) + SawBlep(P2[V], Dt2));
				Pad[V].Run(Saw, 380.0f + 520.0f * Breath, 0.8f, Fs);
				const float X = Pad[V].Lp * 0.075f * Breath;
				const float Pan = -0.7f + 1.4f * V / (kVoices - 1);
				PadL += X * (1.0f - 0.5f * (Pan + 1.0f) * 0.7f);
				PadR += X * (1.0f - 0.5f * (1.0f - Pan) * 0.7f);
			}
			BassHz += (Hz(Chords[Chord][0]) - BassHz) * Glide;
			BassPh += BassHz / Fs; BassPh -= std::floor(BassPh);
			const float Bass = std::sin(2.0f * kPi * BassPh) * 0.16f + std::sin(4.0f * kPi * BassPh) * 0.03f;

			// Bells: now and then, a note of the pentatonic with a long tail, sent to the echo.
			if (Clock >= NextBell)
			{
				BellHz = Hz(Bells[static_cast<int>((Rng.Next() * 0.5f + 0.5f) * 6.99f)]);
				BellEnv = 1.0f;
				NextBell = Clock + BeatLen * (1.0f + 3.0f * (Rng.Next() * 0.5f + 0.5f));
			}
			BellEnv *= std::exp(-1.0f / (1.6f * Fs));
			BellPh += BellHz / Fs; BellPh -= std::floor(BellPh);
			const float Bell = (std::sin(2.0f * kPi * BellPh) + 0.25f * std::sin(6.0f * kPi * BellPh)) * BellEnv * 0.06f;

			// Echo: 0.43 s left, 0.61 s right, damped feedback.
			const int DL = static_cast<int>(0.43f * Fs), DR = static_cast<int>(0.61f * Fs);
			const int N = 40000;
			const float EchoInL = EchoL[(EchoPos + N - DL) % N], EchoInR = EchoR[(EchoPos + N - DR) % N];
			EchoLpL += (EchoInL - EchoLpL) * 0.25f;
			EchoLpR += (EchoInR - EchoLpR) * 0.25f;
			EchoL[EchoPos] = Bell + EchoLpR * 0.55f;
			EchoR[EchoPos] = Bell * 0.8f + EchoLpL * 0.55f;
			EchoPos = (EchoPos + 1) % N;

			Wind.Run(Pink.Next(Rng), 420.0f + 160.0f * std::sin(2.0f * kPi * Clock * 0.05f), 0.9f, Fs);
			const float Air = Wind.Bp * 0.10f;

			L = PadL + Bass + Bell * 0.7f + EchoLpL * 0.8f + Air;
			R = PadR + Bass + Bell * 0.7f + EchoLpR * 0.8f + Air * 0.9f;
		}
	};

	class FMixer
	{
	public:
		explicit FMixer(float SampleRate = 48000.0f) : Fs(SampleRate) { Ambient.Init(SampleRate); }

		FListener Me;
		FOther Others[kMaxOthers];

		// Events (strength 0..1).
		void Impact(float S)
		{
			S = Clamp01(S);
			ThumpEnv = std::fmax(ThumpEnv, S);
			ThumpFreq = 95.0f;
			CrunchEnv = std::fmax(CrunchEnv, S);
			ClankEnv = std::fmax(ClankEnv, S * 0.8f);
		}
		void Landing(float S)
		{
			S = Clamp01(S);
			ThumpEnv = std::fmax(ThumpEnv, 0.7f * S);
			ThumpFreq = 70.0f;
			CrunchEnv = std::fmax(CrunchEnv, 0.25f * S);
		}
		void BoostKick(float S)
		{
			S = Clamp01(S);
			WhooshEnv = std::fmax(WhooshEnv, S);
			WhooshT = 0.0f;
			ThumpEnv = std::fmax(ThumpEnv, 0.45f * S);
			ThumpFreq = 110.0f;
		}

		/** Interleaved stereo float, Frames samples per channel, about -1..1 after the limiter. */
		void Render(float* Out, int Frames)
		{
			const FShipTimbre MyTimbre = TimbreFor(Me.Ship);
			const float Sm = SmoothCoef(0.05f, Fs);
			const float EnvDecayThump = std::exp(-1.0f / (0.30f * Fs));
			const float EnvDecayCrunch = std::exp(-1.0f / (0.12f * Fs));
			const float EnvDecayClank = std::exp(-1.0f / (0.45f * Fs));
			for (int I = 0; I < Frames; ++I)
			{
				// Smoothed listener controls.
				Speed += (Me.Speed01 - Speed) * Sm;
				Grounded += (Me.Grounded - Grounded) * Sm;
				Drift += (Me.Drift - Drift) * Sm;
				WallL += (Me.WallLeft - WallL) * Sm;
				WallR += (Me.WallRight - WallR) * Sm;
				Scrape += (Me.Scrape - Scrape) * SmoothCoef(0.02f, Fs);
				Master += (Me.Master - Master) * SmoothCoef(0.4f, Fs);
				const float S01 = Clamp01(Speed);

				// Own engine, in the middle, a little wide.
				const float Engine = MyEngine.Sample(MyTimbre, Speed, Me.Throttle, Me.Boost, 1.0f, Fs, true) * 0.62f;
				float L = Engine, R = Engine;

				// Wind: stereo, rising with speed, with slow gusts; the tearing hiss near top speed.
				GustTarget += (Rng.Next() * 0.5f - GustTarget) * 0.00002f;
				Gust += (GustTarget - Gust) * 0.0005f;
				const float WindFc = 260.0f + 2700.0f * std::pow(S01, 1.2f);
				const float WindGain = 0.75f * S01 * S01 * (1.0f + Gust);
				WindL.Run(PinkL.Next(Rng), WindFc * 0.92f, 0.7f, Fs);
				WindR.Run(PinkR.Next(Rng), WindFc * 1.08f, 0.7f, Fs);
				L += WindL.Bp * WindGain * 1.8f;
				R += WindR.Bp * WindGain * 1.8f;
				if (S01 > 0.6f)
				{
					Tear.Run(Rng.Next(), 5200.0f, 0.6f, Fs);
					const float Hiss = Tear.Hp * 0.10f * (S01 - 0.6f) / 0.4f;
					L += Hiss;
					R += Hiss;
				}
				// A wall close on one side: its own whoosh, mostly on that side.
				const float WallFc = 900.0f + 2600.0f * S01;
				WallBandL.Run(Rng.Next(), WallFc, 1.3f, Fs);
				WallBandR.Run(Rng.Next(), WallFc * 1.05f, 1.3f, Fs);
				const float WL = WallBandL.Bp * WallL * S01 * 0.9f;
				const float WR = WallBandR.Bp * WallR * S01 * 0.9f;
				L += 0.85f * WL + 0.15f * WR;
				R += 0.15f * WL + 0.85f * WR;

				// Hover hum near the ground.
				HumPhase = Wrap(HumPhase + (48.0f + 6.0f * S01) / Fs);
				const float HumGain = 0.07f * Grounded * (1.0f - Clamp01((Me.HeightM - 1.5f) / 3.0f));
				const float Hum = (std::sin(2.0f * kPi * HumPhase) + 0.4f * std::sin(4.0f * kPi * HumPhase)) * HumGain;
				L += Hum;
				R += Hum;

				// Drift skid and wall scrape: grainy band-passed noise.
				GrainT += 1.0f / Fs;
				if (GrainT > 1.0f / 55.0f)
				{
					GrainT = 0.0f;
					Grain = 0.4f + 0.6f * (0.5f + 0.5f * Rng.Next());
				}
				Skid.Run(Rng.Next(), 1400.0f + 600.0f * S01, 2.0f, Fs);
				const float SkidOut = Skid.Bp * Drift * S01 * 0.35f * Grain;
				Grind.Run(Rng.Next(), 2600.0f, 1.5f, Fs);
				const float GrindOut = Grind.Bp * Scrape * 0.9f * Grain;
				L += SkidOut + GrindOut;
				R += SkidOut + GrindOut;

				// Events.
				float Ev = 0.0f;
				if (ThumpEnv > 0.0005f)
				{
					ThumpFreq = 35.0f + (ThumpFreq - 35.0f) * 0.99985f;
					ThumpPhase = Wrap(ThumpPhase + ThumpFreq / Fs);
					Ev += std::sin(2.0f * kPi * ThumpPhase) * ThumpEnv * 0.9f;
					ThumpEnv *= EnvDecayThump;
				}
				if (CrunchEnv > 0.0005f)
				{
					Crunch.Run(Rng.Next(), 1800.0f, 0.9f, Fs);
					Ev += Crunch.Bp * CrunchEnv * 1.6f;
					CrunchEnv *= EnvDecayCrunch;
				}
				if (ClankEnv > 0.0005f)
				{
					static const float Ratios[3] = { 1.0f, 1.83f, 3.11f };
					float C = 0.0f;
					for (int K = 0; K < 3; ++K)
					{
						ClankPhase[K] = Wrap(ClankPhase[K] + 610.0f * Ratios[K] / Fs);
						C += std::sin(2.0f * kPi * ClankPhase[K]) / (1.0f + K);
					}
					Ev += C * ClankEnv * 0.22f;
					ClankEnv *= EnvDecayClank;
				}
				if (WhooshEnv > 0.0005f)
				{
					WhooshT += 1.0f / Fs;
					const float Rise = Clamp01(WhooshT / 0.6f);
					Whoosh.Run(Rng.Next(), 400.0f + 2400.0f * Rise, 1.2f, Fs);
					Ev += Whoosh.Bp * WhooshEnv * (0.4f + 0.6f * Rise) * 1.4f;
					if (WhooshT > 0.6f)
					{
						WhooshEnv *= std::exp(-1.0f / (0.25f * Fs));
					}
				}
				L += Ev;
				R += Ev;

				// The others: engine, distance muffling, pan (equal power), Doppler pitch.
				for (int K = 0; K < kMaxOthers; ++K)
				{
					FOther& O = Others[K];
					OtherGain[K] += ((O.bActive ? O.Gain : 0.0f) - OtherGain[K]) * Sm;
					OtherPan[K] += (O.Pan - OtherPan[K]) * Sm;
					if (OtherGain[K] < 0.0005f)
					{
						continue;
					}
					float V = OtherEngine[K].Sample(TimbreFor(O.Ship), O.Speed01, O.Throttle, O.Boost, O.PitchMul, Fs, false);
					const float A = 0.03f + 0.97f * (1.0f - Clamp01(O.Muffle));
					OtherAir[K] += (V - OtherAir[K]) * A;
					V = OtherAir[K] * OtherGain[K];
					const float Angle = (OtherPan[K] + 1.0f) * 0.25f * kPi;
					L += V * std::cos(Angle) * 1.2f;
					R += V * std::sin(Angle) * 1.2f;
				}

				// Master and soft limiter.
				L = std::tanh(L * Master * 0.9f);
				R = std::tanh(R * Master * 0.9f);
				MusicLevel += (Me.Music - MusicLevel) * SmoothCoef(1.5f, Fs);
				if (MusicLevel > 0.0005f)
				{
					float ML, MR;
					Ambient.Sample(ML, MR);
					L += ML * MusicLevel * 0.85f;
					R += MR * MusicLevel * 0.85f;
				}
				Out[2 * I] = L;
				Out[2 * I + 1] = R;
			}
		}

	private:
		float Fs;
		FEngine MyEngine{ 11u };
		FEngine OtherEngine[kMaxOthers]{ FEngine(21u), FEngine(22u), FEngine(23u), FEngine(24u), FEngine(25u), FEngine(26u), FEngine(27u), FEngine(28u) };
		float OtherGain[kMaxOthers] = {};
		float OtherPan[kMaxOthers] = {};
		float OtherAir[kMaxOthers] = {};
		FRng Rng{ 0x51F15EEDu };
		FAmbientMusic Ambient;
		float MusicLevel = 0.0f;
		FPink PinkL, PinkR;
		FSvf WindL, WindR, Tear, WallBandL, WallBandR, Skid, Grind, Crunch, Whoosh;
		float Speed = 0.0f, Grounded = 1.0f, Drift = 0.0f, WallL = 0.0f, WallR = 0.0f, Scrape = 0.0f, Master = 1.0f;
		float Gust = 0.0f, GustTarget = 0.0f, HumPhase = 0.0f, GrainT = 0.0f, Grain = 1.0f;
		float ThumpEnv = 0.0f, ThumpFreq = 90.0f, ThumpPhase = 0.0f, CrunchEnv = 0.0f, ClankEnv = 0.0f;
		float ClankPhase[3] = { 0.0f, 0.0f, 0.0f };
		float WhooshEnv = 0.0f, WhooshT = 0.0f;
	};
}
