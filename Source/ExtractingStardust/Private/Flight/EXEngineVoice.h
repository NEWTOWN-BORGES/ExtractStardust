// Extracting Stardust - engine v2 (2026-11-02): a plasma engine built for adrenaline (Docs/SOM.md, "Motor v2").
// Tuned deeper at the player's request ("mais grave"): fundamentals about 6 semitones down, darker body, more sub.
// Pure C++ with the primitives of EXSoundSynth.h, so Scripts/audio/render_engine_preview.cpp renders exactly what the
// game will play. Not wired into the game yet: FMixer keeps FEngine until the player approves the preview.
//
// What makes it addictive:
// - power stages ("gears"): the rpm climbs, drops at each upshift with an ignition cut and a punch, climbs again;
// - afterfire pops when the throttle lifts, on every shift, and rev-matching blips with pops on the downshifts;
// - launch limiter on the grid (hold the throttle: it bangs against the cut);
// - boost: the engine breathes in, a deep thump, then the afterburner roar with a rising whine;
// - fixed nozzle/hull resonances, cycle-to-cycle combustion roughness, turbulent jet roar and a turbine that lags
//   the rpm: it never sounds like a loop or a plain synth.
#pragma once

#include "EXSoundSynth.h"

namespace EXSynth
{
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

	/** One plasma engine, stereo. */
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

			// ---- Core: detuned cores, firings that wander in strength and timing
			const float F0 = (T.BaseHz + T.RangeHz * std::pow(Rpm, 0.95f)) * (1.0f + 0.05f * Boost) * Pitch * (1.0f + 0.003f * Turb2);
			CyclePhase += 0.5f * F0 * Dt * Jit;
			if (CyclePhase >= 1.0f)
			{
				CyclePhase -= 1.0f;
				CycleAmp = 1.0f + 0.6f * T.Grit * Rng.Next();
				Jit = 1.0f + 0.015f * T.Grit * Rng.Next();
			}
			const float Fire = std::exp(-7.0f * CyclePhase);
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

			const float Open = 0.25f * Rpm + 0.75f * Thr;
			BodyLp.Run(Core, 160.0f + T.Bright * Open + 2500.0f * Boost, 0.9f, Fs);
			Fm1.Run(Core, T.F1 * (1.0f + 0.08f * Rpm), T.FormQ, Fs);
			Fm2.Run(Core, T.F2 * (1.0f + 0.08f * Rpm), T.FormQ, Fs);
			Fm3.Run(Core, T.F3, T.FormQ, Fs);
			float X = 0.75f * BodyLp.Lp + (Fm1.Bp + 0.7f * Fm2.Bp + 0.35f * Fm3.Bp) * (0.35f + 0.65f * Thr);
			RaspF.Run(Fire * Fire * Rng.Next(), 900.0f + 2500.0f * Thr + 1200.0f * Rpm, 1.6f, Fs);
			X += RaspF.Bp * T.Rasp * (0.2f + 0.9f * Thr);
			// The throttle drives it into saturation: grit is adrenaline.
			X = 0.8f * SoftClip(X * (1.0f + T.Drive * (0.3f + 0.7f * Thr) + 1.5f * Boost));

			const float SubHz = std::fmax(30.0f, 0.5f * F0);
			SubPhase = Wrap(SubPhase + SubHz * Dt);
			const float SubV = 0.75f * SoftClip(1.8f * std::sin(2.0f * kPi * SubPhase)) * T.Sub * (0.3f + 0.7f * Thr);  // saturated: phones still hear it

			// ---- Turbine whine, on the lagging spool
			const float Fs0 = (T.BaseHz + T.RangeHz * std::pow(Spool, 0.95f)) * (1.0f + 0.08f * Boost) * Pitch;
			const float Fw1 = Fs0 * T.W1;
			W1Phase = Wrap(W1Phase + Fw1 * Dt);
			float WhineV = std::sin(2.0f * kPi * W1Phase) * Clamp01((11000.0f - Fw1) / 3000.0f);
			if (bFull)
			{
				const float Fw2 = Fs0 * T.W2;
				W2Phase = Wrap(W2Phase + Fw2 * Dt);
				WhineV += 0.4f * std::sin(2.0f * kPi * W2Phase) * Clamp01((11000.0f - Fw2) / 3000.0f);
			}
			WhineV *= T.Whine * (0.1f + 0.9f * Spool * Spool) * (0.6f + 0.4f * Thr);

			// ---- Jet roar: decorrelated left/right, turbulent
			const float RoarHz = 160.0f + 1000.0f * Rpm + 1300.0f * Boost;
			RoarL.Run(PinkL.Next(Rng), RoarHz, 0.75f, Fs);
			RoarR.Run(PinkR.Next(Rng), RoarHz * 1.07f, 0.75f, Fs);
			const float RoarAmp = 2.2f * T.Roar * (0.12f + 0.6f * Thr * Thr + 0.25f * Rpm + 1.2f * Boost) * (1.0f + 0.35f * Turb1 + 0.2f * Turb2);

			// ---- Afterfire pops
			if (CrackleLeft > 0.0f)
			{
				CrackleLeft -= Dt;
				if (0.5f + 0.5f * Rng.Next() < CrackleRate * Dt) { Pop(T, 0.5f + 0.5f * std::fabs(Rng.Next())); }
			}
			PopEnv *= CPop;
			const float Exc = Rng.Next() * PopEnv;
			PopHi.Run(Exc, PopHz, 1.8f, Fs);
			PopLo.Run(Exc, 110.0f, 0.8f, Fs);
			const float PopV = (1.4f * PopHi.Bp + 2.2f * PopLo.Lp) * T.Crackle;

			// ---- Boost ignition: a deep falling thump and a burst of fire
			float Ign = 0.0f;
			if (IgniteT >= 0.07f && IgniteT < 0.8f)
			{
				const float Tt = IgniteT - 0.07f;
				IgnPhase = Wrap(IgnPhase + (32.0f + 100.0f * std::exp(-Tt / 0.07f)) * Dt);
				IgnF.Run(Rng.Next(), 900.0f, 0.7f, Fs);
				Ign = (1.2f * std::sin(2.0f * kPi * IgnPhase) + 1.5f * IgnF.Lp * std::exp(-Tt / 0.05f)) * std::exp(-Tt / 0.2f);
			}

			// ---- Blow-off flutter and hiss (own engine only)
			float VentV = 0.0f, HissV = 0.0f;
			VentEnv *= CVent;
			if (bFull)
			{
				VentPhase = Wrap(VentPhase + 21.0f * Dt);
				const float Wob = 0.5f + 0.5f * std::sin(2.0f * kPi * VentPhase);
				VentF.Run(Rng.Next(), 2600.0f + 1800.0f * VentEnv, 1.3f, Fs);
				VentV = 0.9f * VentF.Bp * VentEnv * (0.35f + 0.65f * Wob * Wob * Wob);
				Hiss.Run(Rng.Next(), 6500.0f, 0.7f, Fs);
				HissV = Hiss.Hp * (0.03f * Rpm * Rpm + 0.12f * Boost);
			}

			// ---- Mix
			const float Gain = Duck * (1.0f + Punch);
			const float Mono = (X + SubV + WhineV) * Gain + Ign;
			float L = Mono + RoarL.Bp * RoarAmp * Gain + PopV * (1.0f - PopPan) + VentV + HissV;
			float R = Mono + RoarR.Bp * RoarAmp * Gain + PopV * (1.0f + PopPan) + VentV + HissV;
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
		FSvf BodyLp, Fm1, Fm2, Fm3, RaspF, RoarL, RoarR, Hiss, PopHi, PopLo, VentF, IgnF;
		FPink PinkL, PinkR;
		FRng Rng;
	};
}
