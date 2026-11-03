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
#include <initializer_list>
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
		/** The coefficient Run computes from Fc. tan() is the costly part, so a caller may compute it at control rate. */
		static float Coef(float Fc, float Fs)
		{
			Fc = Fc < 20.0f ? 20.0f : (Fc > 0.45f * Fs ? 0.45f * Fs : Fc);
			return std::tan(kPi * Fc / Fs);
		}
		/** Run with a precomputed coefficient (Coef) and damping K = 1/Q. */
		void RunCoef(float X, float G, float K)
		{
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

	// Extracting Stardust - engine v2 (2026-11-02): a plasma engine built for adrenaline (Docs/SOM.md, "Motor v2").
	// Tuned deeper at the player's request ("mais grave"): fundamentals about 6 semitones down, darker body, more sub.
	// Scripts/audio/render_engine_preview.cpp renders it without the Unreal (EX_ENGINE_LOG=1 prints stage and rpm).
	// Approved by the player (2026-11-02) and used by FMixer for the own engine and the rivals; FEngine is the old one.
	//
	// What makes it addictive:
	// - power stages ("gears"): the rpm climbs, drops at each upshift with an ignition cut and a punch, climbs again;
	// - afterfire pops when the throttle lifts, on every shift, and rev-matching blips with pops on the downshifts;
	// - launch limiter on the grid (hold the throttle: it bangs against the cut);
	// - boost: the engine breathes in, a deep thump, then the afterburner roar with a rising whine;
	// - fixed nozzle/hull resonances, cycle-to-cycle combustion roughness, turbulent jet roar and a turbine that lags
	//   the rpm: it never sounds like a loop or a plain synth.
	/** What makes each ship's engine sound like itself. */
	struct FEngineTimbre
	{
		float BaseHz, RangeHz;    // fundamental at the bottom of the rpm and what full rpm adds
		int Engines;              // 1-3 cores, detuned so they beat
		float Detune;
		float Pulse;              // 0 sawtooth .. 1 hollow pulse
		float F1, F2, F3, FormQ;  // fixed nozzle/hull resonances (they stay put while the pitch moves)
		float Bright;             // low-pass opening at full throttle, Hz
		float Drive;              // saturation on the throttle
		float Grit;               // cycle-to-cycle combustion roughness
		float Rasp;               // noise burst at each firing
		float W1, W2, Whine;      // turbine whine partials (x fundamental) and level
		float Roar;               // broadband jet roar
		float Sub;                // octave-down weight
		int Stages;               // power stages
		float Drop;               // rpm drop at each upshift
		float Crackle, CrackleHz; // afterfire pops: amount and ring
		float Vent;               // blow-off flutter on shifts and lifts
	};

	inline FEngineTimbre EngineTimbreFor(EShip Ship)
	{
		switch (Ship)
		{
		//                     Base Range Eng Detune  Pulse   F1    F2    F3   Q     Bright Drive  Grit   Rasp   W1     W2     Whine  Roar   Sub St Drop    Crk   CrkHz Vent
		case EShip::Wraith:  return { 32,  79, 3, 0.007f, 0.10f, 350, 1040, 2320, 3.5f, 5500, 1.3f, 0.16f, 0.20f, 11.3f, 16.9f, 0.20f, 0.85f, 0.53f, 6, 0.15f, 0.25f, 1360, 0.80f };  // smooth turbine, seamless stages
		case EShip::Nomad:   return { 24.5f, 60, 3, 0.019f, 0.35f, 240,  760, 1760, 4.0f, 3600, 2.6f, 0.60f, 0.55f,  7.2f, 10.9f, 0.06f, 0.75f, 0.75f, 4, 0.33f, 1.00f,  880, 0.35f };  // rough, industrial, bangs
		case EShip::Bastion: return { 20,  49, 1, 0.000f, 0.45f, 176,  560, 1440, 4.0f, 3100, 2.0f, 0.42f, 0.40f,  6.1f,  9.2f, 0.05f, 0.80f, 1.00f, 4, 0.30f, 0.70f,  600, 0.40f };  // deep, armoured, thumps
		case EShip::Vortex:  return { 50, 126, 1, 0.000f, 0.05f, 640, 1920, 3840, 3.0f, 7600, 2.2f, 0.28f, 0.35f, 12.5f, 18.8f, 0.16f, 0.70f, 0.38f, 6, 0.24f, 0.80f, 1840, 0.60f };  // high, screaming
		case EShip::Strix:
		default:             return { 37.5f, 86, 2, 0.011f, 0.20f, 415, 1320, 2720, 3.2f, 6000, 1.8f, 0.34f, 0.40f,  9.1f, 13.7f, 0.12f, 0.80f, 0.45f, 5, 0.27f, 0.60f, 1440, 0.50f };  // twin stacked cores
		}
	}

	/** Pade tanh: soft saturation, exact enough up to |x| = 3. */
	inline float SoftClip(float X)
	{
		if (X > 3.0f) { return 1.0f; }
		if (X < -3.0f) { return -1.0f; }
		const float X2 = X * X;
		return X * (27.0f + X2) / (27.0f + 9.0f * X2);
	}

	/** sin(2 pi P) for a phase P in [0, 1): parabola plus one refinement, error about 0.001. */
	inline float FastSin01(float P)
	{
		const float X = 2.0f * (P < 0.5f ? P : P - 1.0f);
		const float Y = 4.0f * X * (1.0f - std::fabs(X));
		return Y * (0.775f + 0.225f * std::fabs(Y));
	}

	/** One plasma engine, stereo. Filters run on coefficients updated every 32 samples (tan() is the costly part). */
	struct FEngineV2
	{
		explicit FEngineV2(uint32_t Seed = 7u) : Rng(Seed) {}

		/** Speed01, Throttle and BoostTarget 0..1 (speed may pass 1 on boost), PitchMul = Doppler, Grounded 0 in the air.
		 *  bFull adds what only the player's own engine needs (second whine, hiss, flutter, bus compressor). */
		void Sample(const FEngineTimbre& T, float Speed01, float Throttle, float BoostTarget, float PitchMul, float Grounded,
			float Fs, bool bFull, float& OutL, float& OutR)
		{
			if (Fs != CoefFs || T.Stages != TopsN) { Prepare(T, Fs); }
			const float Dt = 1.0f / Fs;

			// ---- Controls and events
			Thr += (Throttle - Thr) * (Throttle > Thr ? CThrUp : CThrDown);
			Boost += (BoostTarget - Boost) * CBoost;
			Pitch += (PitchMul - Pitch) * CPitch;
			ShiftT += Dt;
			IgniteT += Dt;
			CutT -= Dt;
			if (Throttle > 0.6f) { bArmed = true; }
			else if (bArmed && Throttle < 0.25f)
			{
				bArmed = false;
				if (Rpm > 0.4f) { Afterfire(T, 0.45f); }
			}
			if (BoostTarget > 0.5f && PrevBoost <= 0.5f) { IgniteT = 0.0f; }
			PrevBoost = BoostTarget;

			// ---- Power stages: where the speed puts the rpm
			const float V = Speed01 > 0.0f ? Speed01 : 0.0f;
			while (Gear < TopsN && V > Tops[Gear]) { ++Gear; Shift(T, 1.0f); }
			while (Gear > 1 && V < Tops[Gear - 1] - 0.035f) { --Gear; Shift(T, -1.0f); }
			const float Lo = Tops[Gear - 1];
			float InGear = (V - Lo) / (Tops[Gear] - Lo);
			InGear = InGear < 0.0f ? 0.0f : (InGear > 1.25f ? 1.25f : InGear);
			const float RMin = Gear == 1 ? 0.24f : 1.0f - T.Drop;
			float Target = (RMin + (1.0f - RMin) * InGear) * (0.9f + 0.1f * Thr);
			const float Free = 1.0f - Clamp01(V / 0.08f);  // on the grid the throttle alone spins it up
			Target = std::fmax(Target, Free * (0.16f + 0.76f * Thr));
			Target += (1.0f - Grounded) * 0.09f * Thr + 0.06f * Boost;  // unloaded in the air; boost pushes it
			if (ShiftDir < 0.0f && ShiftT < 0.11f) { Target += 0.14f; }  // rev-matching blip on a downshift
			// Launch hold: the limiter bangs against the cut.
			Hold = (Free > 0.5f && Thr > 0.85f) ? Hold + Dt : 0.0f;
			if (Hold > 0.3f)
			{
				LimClock += 13.0f * Dt;
				if (LimClock >= 1.0f)
				{
					LimClock -= 1.0f;
					CutT = 0.028f;
					Pop(T, 0.7f);
				}
				Target = CutT > 0.0f ? 0.70f : 0.84f;
			}
			Target = Target > 1.15f ? 1.15f : Target;
			const float K = Target > Rpm ? (Free > 0.5f ? CRevUp : CRpmUp) : ((ShiftDir > 0.0f && ShiftT < 0.12f) ? CShiftDrop : CRpmDown);
			Rpm += (Target - Rpm) * K;
			Spool += (Rpm - Spool) * CSpool;  // the turbine lags: it keeps singing through the shifts

			// Ignition cut on the upshift and the boost inhale, then the punch.
			float DuckTarget = 1.0f;
			if (ShiftDir > 0.0f && ShiftT < 0.05f) { DuckTarget = 0.35f; }
			if (IgniteT < 0.07f) { DuckTarget = 0.45f; }
			if (CutT > 0.0f) { DuckTarget = 0.4f; }
			Duck += (DuckTarget - Duck) * CDuck;
			if (IgniteT >= 0.07f && IgniteT - Dt < 0.07f) { Punch = 0.5f; }
			Punch *= CPunch;

			// Turbulence: two random wanderers that keep the roar alive.
			TurbClock1 += 6.0f * Dt;
			if (TurbClock1 >= 1.0f) { TurbClock1 -= 1.0f; TurbTarget1 = Rng.Next(); }
			TurbClock2 += 17.0f * Dt;
			if (TurbClock2 >= 1.0f) { TurbClock2 -= 1.0f; TurbTarget2 = Rng.Next(); }
			Turb1 += (TurbTarget1 - Turb1) * CTurb1;
			Turb2 += (TurbTarget2 - Turb2) * CTurb2;

			if (--CtlLeft <= 0)
			{
				CtlLeft = 32;
				GBody = FSvf::Coef(160.0f + T.Bright * (0.25f * Rpm + 0.75f * Thr) + 2500.0f * Boost, Fs);
				GF1 = FSvf::Coef(T.F1 * (1.0f + 0.08f * Rpm), Fs);
				GF2 = FSvf::Coef(T.F2 * (1.0f + 0.08f * Rpm), Fs);
				GF3 = FSvf::Coef(T.F3, Fs);
				GRasp = FSvf::Coef(900.0f + 2500.0f * Thr + 1200.0f * Rpm, Fs);
				const float RoarHz = 160.0f + 1000.0f * Rpm + 1300.0f * Boost;
				GRoar = FSvf::Coef(RoarHz, Fs);
				GRoarR = FSvf::Coef(1.07f * RoarHz, Fs);
				GVent = FSvf::Coef(2600.0f + 1800.0f * VentEnv, Fs);
				FireDecay = std::exp(-3.5f * F0Last * Dt);
			}

			// ---- Core: detuned cores, firings that wander in strength and timing
			const float F0 = (T.BaseHz + T.RangeHz * Rpm) * (1.0f + 0.05f * Boost) * Pitch * (1.0f + 0.003f * Turb2);
			F0Last = F0;
			CyclePhase += 0.5f * F0 * Dt * Jit;
			if (CyclePhase >= 1.0f)
			{
				CyclePhase -= 1.0f;
				CycleAmp = 1.0f + 0.6f * T.Grit * Rng.Next();
				Jit = 1.0f + 0.015f * T.Grit * Rng.Next();
				Fire = 1.0f;
			}
			Fire *= FireDecay;  // exp(-7 x cycle phase)
			float Core = 0.0f;
			for (int E = 0; E < T.Engines; ++E)
			{
				const float F = F0 * Jit * (1.0f + T.Detune * (E - 0.5f * (T.Engines - 1)));
				const float D = F * Dt;
				Phase[E] = Wrap(Phase[E] + D);
				const float Saw = SawBlep(Phase[E], D);
				const float Saw2 = SawBlep(Wrap(Phase[E] + 0.5f), D);
				Core += (1.0f - T.Pulse) * Saw + T.Pulse * 0.5f * (Saw - Saw2);
			}
			Core *= (1.0f + T.Grit * (Fire * CycleAmp - 0.3f)) / static_cast<float>(T.Engines);

			const float KForm = 1.0f / T.FormQ;
			BodyLp.RunCoef(Core, GBody, 1.0f / 0.9f);
			Fm1.RunCoef(Core, GF1, KForm);
			Fm2.RunCoef(Core, GF2, KForm);
			if (bFull) { Fm3.RunCoef(Core, GF3, KForm); }  // the rivals skip the top resonance
			float X = 0.75f * BodyLp.Lp + (Fm1.Bp + 0.7f * Fm2.Bp + (bFull ? 0.35f * Fm3.Bp : 0.0f)) * (0.35f + 0.65f * Thr);
			RaspF.RunCoef(Fire * Fire * Rng.Next(), GRasp, 1.0f / 1.6f);
			X += RaspF.Bp * T.Rasp * (0.2f + 0.9f * Thr);
			// The throttle drives it into saturation: grit is adrenaline.
			X = 0.8f * SoftClip(X * (1.0f + T.Drive * (0.3f + 0.7f * Thr) + 1.5f * Boost));

			const float SubHz = std::fmax(30.0f, 0.5f * F0);
			SubPhase = Wrap(SubPhase + SubHz * Dt);
			const float SubV = 0.75f * SoftClip(1.8f * FastSin01(SubPhase)) * T.Sub * (0.3f + 0.7f * Thr);  // saturated: phones still hear it

			// ---- Turbine whine, on the lagging spool
			const float Fs0 = (T.BaseHz + T.RangeHz * Spool) * (1.0f + 0.08f * Boost) * Pitch;
			const float Fw1 = Fs0 * T.W1;
			W1Phase = Wrap(W1Phase + Fw1 * Dt);
			float WhineV = FastSin01(W1Phase) * Clamp01((11000.0f - Fw1) / 3000.0f);
			if (bFull)
			{
				const float Fw2 = Fs0 * T.W2;
				W2Phase = Wrap(W2Phase + Fw2 * Dt);
				WhineV += 0.4f * FastSin01(W2Phase) * Clamp01((11000.0f - Fw2) / 3000.0f);
			}
			WhineV *= T.Whine * (0.1f + 0.9f * Spool * Spool) * (0.6f + 0.4f * Thr);

			// ---- Jet roar: decorrelated left/right, turbulent
			RoarL.RunCoef(PinkL.Next(Rng), GRoar, 1.0f / 0.75f);
			if (bFull) { RoarR.RunCoef(PinkR.Next(Rng), GRoarR, 1.0f / 0.75f); }  // the rivals are mono anyway
			const float RoarOutR = bFull ? RoarR.Bp : RoarL.Bp;
			const float RoarAmp = 2.2f * T.Roar * (0.12f + 0.6f * Thr * Thr + 0.25f * Rpm + 1.2f * Boost) * (1.0f + 0.35f * Turb1 + 0.2f * Turb2);

			// ---- Afterfire pops
			if (CrackleLeft > 0.0f)
			{
				CrackleLeft -= Dt;
				if (0.5f + 0.5f * Rng.Next() < CrackleRate * Dt) { Pop(T, 0.5f + 0.5f * std::fabs(Rng.Next())); }
			}
			float PopV = 0.0f;
			if (PopEnv > 1e-5f || std::fabs(PopHi.Ic1) + std::fabs(PopHi.Ic2) + std::fabs(PopLo.Ic1) + std::fabs(PopLo.Ic2) > 1e-6f)
			{
				PopEnv *= CPop;
				const float Exc = Rng.Next() * PopEnv;
				PopHi.RunCoef(Exc, GPopHi, 1.0f / 1.8f);
				PopLo.RunCoef(Exc, GPopLo, 1.0f / 0.8f);
				PopV = (1.4f * PopHi.Bp + 2.2f * PopLo.Lp) * T.Crackle;
			}

			// ---- Boost ignition: a deep falling thump and a burst of fire
			float Ign = 0.0f;
			if (IgniteT >= 0.07f && IgniteT < 0.8f)
			{
				const float Tt = IgniteT - 0.07f;
				IgnPhase = Wrap(IgnPhase + (32.0f + 100.0f * std::exp(-Tt / 0.07f)) * Dt);
				IgnF.RunCoef(Rng.Next(), GIgn, 1.0f / 0.7f);
				Ign = (1.2f * FastSin01(IgnPhase) + 1.5f * IgnF.Lp * std::exp(-Tt / 0.05f)) * std::exp(-Tt / 0.2f);
			}

			// ---- Blow-off flutter and hiss (own engine only)
			float VentV = 0.0f, HissV = 0.0f;
			VentEnv *= CVent;
			if (bFull)
			{
				VentPhase = Wrap(VentPhase + 21.0f * Dt);
				const float Wob = 0.5f + 0.5f * FastSin01(VentPhase);
				VentF.RunCoef(Rng.Next(), GVent, 1.0f / 1.3f);
				VentV = 0.9f * VentF.Bp * VentEnv * (0.35f + 0.65f * Wob * Wob * Wob);
				Hiss.RunCoef(Rng.Next(), GHiss, 1.0f / 0.7f);
				HissV = Hiss.Hp * (0.03f * Rpm * Rpm + 0.12f * Boost);
			}

			// ---- Mix
			const float Gain = Duck * (1.0f + Punch);
			const float Mono = (X + SubV + WhineV) * Gain + Ign;
			float L = Mono + RoarL.Bp * RoarAmp * Gain + PopV * (1.0f - PopPan) + VentV + HissV;
			float R = Mono + RoarOutR * RoarAmp * Gain + PopV * (1.0f + PopPan) + VentV + HissV;
			// DC blocker (the firing envelope correlates with the waveform).
			DcL = L - DcXL + CDc * DcL;
			DcXL = L;
			DcR = R - DcXR + CDc * DcR;
			DcXR = R;
			L = DcL;
			R = DcR;
			if (bFull)
			{
				// Bus compressor: dense and loud without clipping.
				const float Lev = std::fmax(std::fabs(L), std::fabs(R));
				CompEnv += (Lev - CompEnv) * (Lev > CompEnv ? CCompAtk : CCompRel);
				if (CompEnv > 0.45f)
				{
					const float G = std::pow(0.45f / CompEnv, 0.6f);
					L *= G;
					R *= G;
				}
			}
			OutL = SoftClip(0.9f * L);
			OutR = SoftClip(0.9f * R);
		}

		/** For the HUD and the preview log. */
		int GetStage() const { return Gear; }
		float GetRpm() const { return Rpm; }

	private:
		void Prepare(const FEngineTimbre& T, float Fs)
		{
			CoefFs = Fs;
			CThrUp = SmoothCoef(0.025f, Fs);
			CThrDown = SmoothCoef(0.06f, Fs);
			CBoost = SmoothCoef(0.08f, Fs);
			CPitch = SmoothCoef(0.05f, Fs);
			CRevUp = SmoothCoef(0.09f, Fs);
			CRpmUp = SmoothCoef(0.16f, Fs);
			CRpmDown = SmoothCoef(0.24f, Fs);
			CShiftDrop = SmoothCoef(0.045f, Fs);
			CSpool = SmoothCoef(0.5f, Fs);
			CDuck = SmoothCoef(0.004f, Fs);
			CTurb1 = SmoothCoef(0.06f, Fs);
			CTurb2 = SmoothCoef(0.025f, Fs);
			CCompAtk = SmoothCoef(0.003f, Fs);
			CCompRel = SmoothCoef(0.12f, Fs);
			CPunch = std::exp(-1.0f / (0.16f * Fs));
			CPop = std::exp(-1.0f / (0.006f * Fs));
			CVent = std::exp(-1.0f / (0.32f * Fs));
			CDc = 1.0f - 2.0f * kPi * 20.0f / Fs;
			GPopLo = FSvf::Coef(110.0f, Fs);
			GHiss = FSvf::Coef(6500.0f, Fs);
			GIgn = FSvf::Coef(900.0f, Fs);
			GPopHi = FSvf::Coef(PopHz, Fs);
			CtlLeft = 0;
			// Stage tops: short low stages (quick shifts off the line), long high ones.
			TopsN = T.Stages < 1 ? 1 : (T.Stages > 7 ? 7 : T.Stages);
			Tops[0] = 0.0f;
			for (int S = 1; S <= TopsN; ++S) { Tops[S] = 1.05f * std::pow(static_cast<float>(S) / TopsN, 1.2f); }
			Gear = Gear > TopsN ? TopsN : Gear;
		}

		void Pop(const FEngineTimbre& T, float Amp)
		{
			PopEnv = Amp;
			PopHz = T.CrackleHz * (0.75f + 0.25f * (Rng.Next() + 1.0f));
			PopPan = 0.35f * Rng.Next();
			GPopHi = FSvf::Coef(PopHz, CoefFs);
		}

		void Afterfire(const FEngineTimbre& T, float Seconds)
		{
			CrackleLeft = Seconds * (0.4f + T.Crackle);
			CrackleRate = 18.0f + 40.0f * T.Crackle;
			VentEnv = std::fmax(VentEnv, T.Vent);
		}

		void Shift(const FEngineTimbre& T, float Dir)
		{
			const bool bEffects = ShiftT > 0.08f;  // a jump of several stages at once makes one event
			ShiftT = 0.0f;
			ShiftDir = Dir;
			if (!bEffects) { return; }
			if (Dir > 0.0f)
			{
				Punch = 0.3f;
				VentEnv = std::fmax(VentEnv, 0.9f * T.Vent);
				CrackleLeft = 0.12f + 0.2f * T.Crackle;
				CrackleRate = 30.0f + 40.0f * T.Crackle;
			}
			else
			{
				CrackleLeft = 0.2f + 0.25f * T.Crackle;
				CrackleRate = 25.0f + 35.0f * T.Crackle;
			}
		}

		float Thr = 0.0f, Boost = 0.0f, Pitch = 1.0f, Rpm = 0.16f, Spool = 0.16f;
		int Gear = 1;
		float ShiftT = 9.0f, ShiftDir = 0.0f, IgniteT = 9.0f, CutT = 0.0f, Hold = 0.0f, LimClock = 0.0f;
		bool bArmed = false;
		float PrevBoost = 0.0f, Duck = 1.0f, Punch = 0.0f;
		float Phase[3] = { 0.0f, 0.37f, 0.71f };
		float CyclePhase = 0.0f, CycleAmp = 1.0f, Jit = 1.0f;
		float SubPhase = 0.0f, W1Phase = 0.0f, W2Phase = 0.0f, IgnPhase = 0.0f, VentPhase = 0.0f, VentEnv = 0.0f;
		float PopEnv = 0.0f, PopHz = 1800.0f, PopPan = 0.0f, CrackleLeft = 0.0f, CrackleRate = 0.0f;
		float Turb1 = 0.0f, Turb2 = 0.0f, TurbTarget1 = 0.0f, TurbTarget2 = 0.0f, TurbClock1 = 0.0f, TurbClock2 = 0.0f;
		float CompEnv = 0.0f, DcL = 0.0f, DcR = 0.0f, DcXL = 0.0f, DcXR = 0.0f;
		float Tops[8] = { 0.0f };
		int TopsN = 0;
		float CoefFs = 0.0f, CThrUp = 0, CThrDown = 0, CBoost = 0, CPitch = 0, CRevUp = 0, CRpmUp = 0, CRpmDown = 0;
		float CShiftDrop = 0, CSpool = 0, CDuck = 0, CTurb1 = 0, CTurb2 = 0, CCompAtk = 0, CCompRel = 0;
		float CPunch = 0, CPop = 0, CVent = 0, CDc = 0;
		int CtlLeft = 0;
		float Fire = 1.0f, FireDecay = 0.99f, F0Last = 50.0f;
		float GBody = 0.1f, GF1 = 0.03f, GF2 = 0.08f, GF3 = 0.2f, GRasp = 0.1f, GRoar = 0.03f, GRoarR = 0.03f, GVent = 0.2f;
		float GPopHi = 0.1f, GPopLo = 0.007f, GHiss = 0.5f, GIgn = 0.06f;
		FSvf BodyLp, Fm1, Fm2, Fm3, RaspF, RoarL, RoarR, Hiss, PopHi, PopLo, VentF, IgnF;
		FPink PinkL, PinkR;
		FRng Rng;
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

	/**
	 * The game's call-outs, synthesised like the rest (player, 2026-10-27: "o som dá para melhorar"; the loot must be
	 * adrenaline): bell-like notes (a sine and its octave and twelfth, a soft attack and a ringing decay) scheduled in
	 * short phrases. Kinds: 0-4 a piece picked up, by rarity (the rarer, the longer and brighter the run; a legendary
	 * ends on a held chord); 10 a countdown beep, 11 the start, 12 a checkpoint, 13 a rival destroyed (its pieces spill:
	 * a falling run of coins).
	 */
	struct FChimes
	{
		static constexpr int kNotes = 24;
		struct FNote
		{
			float Freq = 0.0f, Delay = 0.0f, Amp = 0.0f, Decay = 0.3f, Phase = 0.0f, Age = -1.0f;
		};
		FNote Notes[kNotes];
		int Next = 0;
		float Fs = 48000.0f;

		void Add(float Freq, float Delay, float Amp, float Decay)
		{
			FNote& N = Notes[Next];
			Next = (Next + 1) % kNotes;
			N.Freq = Freq;
			N.Delay = Delay;
			N.Amp = Amp;
			N.Decay = Decay;
			N.Phase = 0.0f;
			N.Age = 0.0f;
		}
		static float Hz(float Midi) { return 440.0f * std::pow(2.0f, (Midi - 69.0f) / 12.0f); }

		void Play(int Kind)
		{
			static const float Up[8] = { 0, 4, 7, 12, 16, 19, 24, 28 };   // major arpeggio
			if (Kind >= 0 && Kind <= 4)
			{
				const int Count = 3 + Kind;
				const float Step = 0.075f - 0.008f * Kind;
				const float Root = 72.0f + 2.0f * Kind;
				for (int K = 0; K < Count; ++K)
				{
					Add(Hz(Root + Up[K]), K * Step, 0.16f + 0.02f * Kind, 0.35f + 0.08f * Kind);
				}
				if (Kind >= 3)   // epic and legendary: a held chord under the run
				{
					for (float Semi : { 0.0f, 7.0f, 12.0f, 16.0f })
					{
						Add(Hz(Root - 12.0f + Semi), Count * Step, Kind == 4 ? 0.12f : 0.08f, Kind == 4 ? 2.4f : 1.2f);
					}
				}
			}
			else if (Kind == 10)
			{
				Add(880.0f, 0.0f, 0.22f, 0.16f);
			}
			else if (Kind == 11)
			{
				Add(1318.5f, 0.0f, 0.24f, 0.7f);
				Add(659.3f, 0.0f, 0.2f, 0.7f);
				Add(987.8f, 0.0f, 0.16f, 0.7f);
			}
			else if (Kind == 12)
			{
				Add(987.8f, 0.0f, 0.18f, 0.25f);
				Add(1318.5f, 0.09f, 0.2f, 0.45f);
			}
			else if (Kind == 13)
			{
				for (int K = 0; K < 7; ++K)
				{
					Add(Hz(96.0f - 2.0f * K), K * 0.045f, 0.09f, 0.22f);
				}
			}
		}

		void Sample(float& Out)
		{
			Out = 0.0f;
			for (FNote& N : Notes)
			{
				if (N.Age < 0.0f)
				{
					continue;
				}
				N.Age += 1.0f / Fs;
				const float T = N.Age - N.Delay;
				if (T < 0.0f)
				{
					continue;
				}
				if (T > N.Decay * 6.0f)
				{
					N.Age = -1.0f;
					continue;
				}
				N.Phase += N.Freq / Fs;
				N.Phase -= std::floor(N.Phase);
				const float Env = Clamp01(T / 0.004f) * std::exp(-T / N.Decay);
				const float W = 2.0f * kPi * N.Phase;
				Out += N.Amp * Env * (std::sin(W) + 0.35f * std::sin(2.0f * W) + 0.12f * std::sin(3.0f * W));
			}
		}
	};

	class FMixer
	{
	public:
		explicit FMixer(float SampleRate = 48000.0f) : Fs(SampleRate) { Ambient.Init(SampleRate); Calls.Fs = SampleRate; }
		/** A call-out (FChimes kinds). */
		void Chime(int Kind) { Calls.Play(Kind); }

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
			WhooshT = 0.0f;  // the thump is the engine's own boost ignition now (FEngineV2)
		}

		/** Interleaved stereo float, Frames samples per channel, about -1..1 after the limiter. */
		void Render(float* Out, int Frames)
		{
			const FEngineTimbre MyTimbre = EngineTimbreFor(Me.Ship);
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
				float EngL = 0.0f, EngR = 0.0f;
				MyEngine.Sample(MyTimbre, Speed, Me.Throttle, Me.Boost, 1.0f, Grounded, Fs, true, EngL, EngR);
				float L = EngL * 0.62f, R = EngR * 0.62f;

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
					float VL = 0.0f, VR = 0.0f;
					OtherEngine[K].Sample(EngineTimbreFor(O.Ship), O.Speed01, O.Throttle, O.Boost, O.PitchMul, 1.0f, Fs, false, VL, VR);
					float V = 0.5f * (VL + VR) * kOtherEngineGain;
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
				float Call = 0.0f;
				Calls.Sample(Call);
				L += Call;
				R += Call;
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
		FEngineV2 MyEngine{ 11u };
		FEngineV2 OtherEngine[kMaxOthers]{ FEngineV2(21u), FEngineV2(22u), FEngineV2(23u), FEngineV2(24u), FEngineV2(25u), FEngineV2(26u), FEngineV2(27u), FEngineV2(28u) };
		/** Rivals' engines against the old ones' level (render_sound_preview passagens). */
		static constexpr float kOtherEngineGain = 0.5f;
		float OtherGain[kMaxOthers] = {};
		float OtherPan[kMaxOthers] = {};
		float OtherAir[kMaxOthers] = {};
		FRng Rng{ 0x51F15EEDu };
		FAmbientMusic Ambient;
		FChimes Calls;
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
