using System.Collections.Generic;
using UnityEngine;

namespace Stardust
{
    /// <summary>All sound is synthesised at start-up (no audio assets needed).</summary>
    public static class Synth
    {
        public const int Rate = 22050;

        static AudioClip Make(string name, float seconds, System.Func<float, int, float> f)
        {
            int n = Mathf.CeilToInt(seconds * Rate);
            var data = new float[n];
            for (int i = 0; i < n; i++) data[i] = Mathf.Clamp(f(i / (float)Rate, i), -1f, 1f);
            var clip = AudioClip.Create(name, n, 1, Rate, false);
            clip.SetData(data, 0);
            return clip;
        }

        static float Saw(float ph) => 2f * (ph - Mathf.Floor(ph + 0.5f));
        static float Sq(float ph) => ph - Mathf.Floor(ph) < 0.5f ? 1f : -1f;
        static float Tri(float ph) => 1f - 4f * Mathf.Abs(ph - Mathf.Floor(ph + 0.5f));

        static uint seed = 22222;
        static float Rnd() { seed ^= seed << 13; seed ^= seed >> 17; seed ^= seed << 5; return (seed / 4294967295f) * 2f - 1f; }

        /// <summary>Loopable engine tone: 1 s with integer cycles of every partial.</summary>
        public static AudioClip Engine()
        {
            return Make("engine", 1f, (t, i) =>
            {
                float f0 = 55f;
                float s = 0.45f * Saw(t * f0) + 0.25f * Sq(t * f0 * 2f) * 0.5f + 0.2f * Mathf.Sin(t * f0 * 3f * Mathf.PI * 2f)
                          + 0.12f * Saw(t * f0 * 4f + 0.3f) + 0.08f * Mathf.Sin(t * 440f * Mathf.PI * 2f);
                s *= 0.85f + 0.15f * Mathf.Sin(t * 20f * Mathf.PI * 2f);
                return s * 0.5f;
            });
        }

        /// <summary>High turbine whine layered above the engine.</summary>
        public static AudioClip Whine()
        {
            return Make("whine", 1f, (t, i) => 0.3f * Mathf.Sin(t * 880f * Mathf.PI * 2f) + 0.15f * Tri(t * 1320f) + 0.05f * Mathf.Sin(t * 1760f * Mathf.PI * 2f));
        }

        public static AudioClip Wind()
        {
            float lp = 0f, lp2 = 0f;
            var c = Make("wind", 2f, (t, i) =>
            {
                lp += (Rnd() - lp) * 0.08f;
                lp2 += (lp - lp2) * 0.2f;
                return lp2 * 1.6f;
            });
            return Loopify(c);
        }

        public static AudioClip Scrape()
        {
            float hp = 0f, prev = 0f;
            return Loopify(Make("scrape", 1f, (t, i) =>
            {
                float n = Rnd();
                hp = 0.9f * (hp + n - prev);
                prev = n;
                return hp * 0.5f * (0.6f + 0.4f * Mathf.Sin(t * 60f * Mathf.PI * 2f)) + 0.2f * Mathf.Sin(t * 1900f * Mathf.PI * 2f) * (Rnd() * 0.5f + 0.5f);
            }));
        }

        public static AudioClip Boost()
        {
            float lp = 0f;
            return Make("boost", 1.4f, (t, i) =>
            {
                float env = Mathf.Clamp01(t / 0.08f) * Mathf.Exp(-t * 1.8f);
                float cut = Mathf.Lerp(0.05f, 0.5f, Mathf.Clamp01(t / 0.5f));
                lp += (Rnd() - lp) * cut;
                return (lp * 1.4f + 0.3f * Saw(t * (120f + t * 300f))) * env;
            });
        }

        public static AudioClip Impact()
        {
            float lp = 0f;
            return Make("impact", 0.5f, (t, i) =>
            {
                lp += (Rnd() - lp) * 0.3f;
                float thump = Mathf.Sin(t * Mathf.Lerp(140f, 40f, t * 3f) * Mathf.PI * 2f) * Mathf.Exp(-t * 10f);
                return thump * 0.9f + lp * Mathf.Exp(-t * 14f) * 1.2f + Rnd() * Mathf.Exp(-t * 40f) * 0.5f;
            });
        }

        public static AudioClip Explosion()
        {
            float lp = 0f, lp2 = 0f;
            return Make("explosion", 2.4f, (t, i) =>
            {
                lp += (Rnd() - lp) * 0.12f;
                lp2 += (lp - lp2) * 0.1f;
                float boom = Mathf.Sin(t * Mathf.Lerp(80f, 30f, Mathf.Clamp01(t)) * Mathf.PI * 2f) * Mathf.Exp(-t * 3f);
                return (boom * 0.8f + lp2 * 3f * Mathf.Exp(-t * 1.5f) + Rnd() * Mathf.Exp(-t * 18f) * 0.6f);
            });
        }

        public static AudioClip Thunder()
        {
            float lp = 0f;
            return Make("thunder", 2.5f, (t, i) =>
            {
                lp += (Rnd() - lp) * 0.06f;
                float crack = Rnd() * Mathf.Exp(-t * 25f);
                float rumble = lp * 3.5f * Mathf.Exp(-t * 1.2f) * (0.7f + 0.3f * Mathf.Sin(t * 7f));
                return crack * 0.9f + rumble;
            });
        }

        public static AudioClip Zap()
        {
            return Make("zap", 1.3f, (t, i) =>
            {
                float crackle = Rnd() > 0.92f ? Rnd() : 0f;
                return (crackle * 0.8f + 0.2f * Sq(t * (300f + 600f * t))) * Mathf.Clamp01(t * 3f) * 0.6f;
            });
        }

        public static AudioClip Beep(float freq, float dur, float vol = 0.5f)
        {
            return Make("beep" + freq, dur, (t, i) => Mathf.Sin(t * freq * Mathf.PI * 2f) * vol * Mathf.Clamp01(t * 200f) * Mathf.Clamp01((dur - t) * 30f));
        }

        public static AudioClip Chime()
        {
            return Make("chime", 0.6f, (t, i) =>
            {
                float f = t < 0.12f ? 880f : 1320f;
                return (Mathf.Sin(t * f * Mathf.PI * 2f) + 0.3f * Mathf.Sin(t * f * 2f * Mathf.PI * 2f)) * Mathf.Exp(-((t < 0.12f ? t : t - 0.12f)) * 7f) * 0.4f;
            });
        }

        public static AudioClip Alarm()
        {
            return Make("alarm", 1f, (t, i) => (t % 0.5f < 0.18f ? Sq(t * 1040f) * 0.25f : 0f));
        }

        public static AudioClip Repair()
        {
            return Make("repair", 1f, (t, i) => 0.18f * Mathf.Sin(t * 330f * Mathf.PI * 2f) * (0.5f + 0.5f * Mathf.Sin(t * 8f * Mathf.PI * 2f)) + 0.08f * Mathf.Sin(t * 660f * Mathf.PI * 2f));
        }

        /// <summary>16 s driving synth loop: kick, bass, arpeggio in A minor at 128 bpm.</summary>
        public static AudioClip Music()
        {
            float bpm = 128f;
            float beat = 60f / bpm;
            float[] bassNotes = { 55f, 55f, 43.65f, 49f };     // A1 A1 F1 G1
            float[] arp = { 440f, 523.25f, 659.25f, 523.25f, 440f, 659.25f, 783.99f, 659.25f };
            float lp = 0f;
            float len = beat * 32f;
            var clip = Make("music", len, (t, i) =>
            {
                float b = t / beat;
                int bar = (int)(b / 8f) % 4;
                float inBeat = b - Mathf.Floor(b);
                // kick on every beat
                float kick = Mathf.Sin(inBeat * beat * Mathf.Lerp(150f, 45f, Mathf.Clamp01(inBeat * 6f)) * Mathf.PI * 2f) * Mathf.Exp(-inBeat * 9f) * 0.55f;
                // offbeat hat
                float hatPh = b * 2f - Mathf.Floor(b * 2f);
                float hat = ((int)(b * 2f) % 2 == 1) ? Rnd() * Mathf.Exp(-hatPh * 25f) * 0.12f : 0f;
                // rolling 16th bass
                float sixteenth = b * 4f - Mathf.Floor(b * 4f);
                float bf = bassNotes[bar];
                float bass = Saw(t * bf) * Mathf.Exp(-sixteenth * 4f) * 0.35f;
                lp += (bass - lp) * 0.15f;
                // arpeggio
                int ai = (int)(b * 4f) % arp.Length;
                float af = arp[ai] * (bar == 2 ? 0.8909f : bar == 3 ? 0.8909f * 1.1225f : 1f);
                float arpS = Sq(t * af) * Mathf.Exp(-sixteenth * 6f) * 0.06f + Tri(t * af * 0.5f) * Mathf.Exp(-sixteenth * 5f) * 0.05f;
                // pad
                float pad = (Mathf.Sin(t * bf * 4f * Mathf.PI * 2f) + Mathf.Sin(t * bf * 6f * 1.002f * Mathf.PI * 2f)) * 0.03f;
                return (kick + hat + lp + arpS + pad) * 0.8f;
            });
            return clip;
        }

        static AudioClip Loopify(AudioClip c)
        {
            // cross-fade the last 10% into the start for a seamless loop
            var d = new float[c.samples];
            c.GetData(d, 0);
            int fade = d.Length / 10;
            for (int i = 0; i < fade; i++)
            {
                float k = i / (float)fade;
                d[i] = d[i] * k + d[d.Length - fade + i] * (1f - k);
            }
            var o = AudioClip.Create(c.name, d.Length - fade, 1, Rate, false);
            var trimmed = new float[d.Length - fade];
            System.Array.Copy(d, trimmed, trimmed.Length);
            o.SetData(trimmed, 0);
            return o;
        }
    }

    /// <summary>Engine loops for human ships, a few pooled 3D sources for nearby bots, and one-shots.</summary>
    public class GameAudio : MonoBehaviour
    {
        public static GameAudio I;
        public float master = 0.9f, musicVol = 0.45f;
        AudioClip engine, whine, wind, scrape, boost, impact, explosion, thunder, zap, chime, alarm, repair, beepLo, beepHi, uiClick, music;
        readonly List<EngineVoice> voices = new List<EngineVoice>();
        readonly List<AudioSource> oneShots = new List<AudioSource>();
        readonly List<AudioSource> botVoices = new List<AudioSource>();
        AudioSource musicSrc, alarmSrc, uiSrc;
        Transform listener;

        class EngineVoice { public IVoiceShip ship; public AudioSource eng, wh, wnd, scr, rep; public bool wasBoost; }

        public static GameAudio Create(Transform parent)
        {
            var go = new GameObject("Audio");
            go.transform.SetParent(parent, false);
            var a = go.AddComponent<GameAudio>();
            a.Init();
            I = a;
            return a;
        }

        AudioSource Src(string name, AudioClip clip, bool loop, float spatial)
        {
            var go = new GameObject(name);
            go.transform.SetParent(transform, false);
            var s = go.AddComponent<AudioSource>();
            s.clip = clip;
            s.loop = loop;
            s.playOnAwake = false;
            s.spatialBlend = spatial;
            s.dopplerLevel = 0f;
            s.rolloffMode = AudioRolloffMode.Linear;
            s.minDistance = 8f;
            s.maxDistance = 220f;
            return s;
        }

        void Init()
        {
            engine = Synth.Engine(); whine = Synth.Whine(); wind = Synth.Wind(); scrape = Synth.Scrape();
            boost = Synth.Boost(); impact = Synth.Impact(); explosion = Synth.Explosion(); thunder = Synth.Thunder();
            zap = Synth.Zap(); chime = Synth.Chime(); alarm = Synth.Alarm(); repair = Synth.Repair();
            beepLo = Synth.Beep(660f, 0.25f); beepHi = Synth.Beep(1320f, 0.6f); uiClick = Synth.Beep(1500f, 0.05f, 0.3f);
            music = Synth.Music();
            musicSrc = Src("Music", music, true, 0f);
            alarmSrc = Src("Alarm", alarm, true, 0f);
            uiSrc = Src("UI", null, false, 0f);
            for (int i = 0; i < 10; i++) oneShots.Add(Src("OneShot" + i, null, false, 1f));
            for (int i = 0; i < 4; i++) { var b = Src("Bot" + i, engine, true, 1f); b.maxDistance = 120f; botVoices.Add(b); }
        }

        public void SetListener(Transform t) => listener = t;

        AudioReverbZone reverb;
        /// <summary>Echo inside tunnels and under the stone roofs.</summary>
        public void SetCave(bool on)
        {
            if (listener == null) return;
            if (reverb == null || reverb.transform != listener)
            {
                if (reverb != null) Destroy(reverb);
                reverb = listener.gameObject.GetComponent<AudioReverbZone>();
                if (reverb == null) reverb = listener.gameObject.AddComponent<AudioReverbZone>();
                reverb.reverbPreset = AudioReverbPreset.Cave;
                reverb.minDistance = 50f;
                reverb.maxDistance = 100f;
            }
            reverb.enabled = on;
        }

        public void PlayMusic(bool on)
        {
            if (on && !musicSrc.isPlaying) musicSrc.Play();
            if (!on) musicSrc.Stop();
        }

        public void AddVoice(IVoiceShip ship)
        {
            var v = new EngineVoice
            {
                ship = ship,
                eng = Src("Eng", engine, true, 0f),
                wh = Src("Whine", whine, true, 0f),
                wnd = Src("Wind", wind, true, 0f),
                scr = Src("Scrape", scrape, true, 0f),
                rep = Src("Repair", repair, true, 0f),
            };
            v.eng.Play(); v.wh.Play(); v.wnd.Play(); v.scr.Play(); v.rep.Play();
            voices.Add(v);
        }

        public void ClearVoices()
        {
            foreach (var v in voices) { Destroy(v.eng.gameObject); Destroy(v.wh.gameObject); Destroy(v.wnd.gameObject); Destroy(v.scr.gameObject); Destroy(v.rep.gameObject); }
            voices.Clear();
            foreach (var b in botVoices) b.Stop();
            alarmSrc.Stop();
        }

        public void Ui() => uiSrc.PlayOneShot(uiClick, master * 0.6f);
        public void CountBeep(bool go) => uiSrc.PlayOneShot(go ? beepHi : beepLo, master * 0.8f);
        public void Chime() => uiSrc.PlayOneShot(chime, master * 0.7f);

        public void At(Vector3 pos, string what, float vol = 1f)
        {
            AudioClip c = null;
            switch (what)
            {
                case "impact": c = impact; break;
                case "explosion": c = explosion; break;
                case "thunder": c = thunder; break;
                case "zap": c = zap; break;
                case "boost": c = boost; break;
            }
            if (c == null) return;
            AudioSource src = null;
            foreach (var s in oneShots) if (!s.isPlaying) { src = s; break; }
            if (src == null) src = oneShots[0];
            src.transform.position = pos;
            src.clip = c;
            src.volume = vol * master;
            src.pitch = Random.Range(0.92f, 1.08f);
            src.spatialBlend = listener != null && (pos - listener.position).sqrMagnitude < 4f ? 0f : 0.85f;
            src.maxDistance = what == "thunder" || what == "explosion" ? 600f : 200f;
            src.Play();
        }

        public void Tick(IEnumerable<IVoiceShip> all, bool paused)
        {
            float dt = Time.unscaledDeltaTime;
            musicSrc.volume = musicVol * master * 0.6f;
            bool anyCritical = false;
            foreach (var v in voices)
            {
                var sh = v.ship;
                bool alive = !paused && sh.Alive;
                float sp = sh.Speed01;
                float target = alive ? 1f : 0f;
                v.eng.pitch = Mathf.Lerp(v.eng.pitch, 0.55f + sp * 1.25f + (sh.Boosting ? 0.25f : 0f) + sh.Throttle * 0.1f, dt * 6f);
                v.eng.volume = Mathf.Lerp(v.eng.volume, target * master * (0.3f + 0.25f * sh.Throttle), dt * 6f);
                v.wh.pitch = 0.7f + sp * 0.8f + (sh.Boosting ? 0.3f : 0f);
                v.wh.volume = Mathf.Lerp(v.wh.volume, target * master * (0.05f + sp * 0.12f + (sh.Boosting ? 0.1f : 0f)), dt * 6f);
                v.wnd.pitch = 0.6f + sp * 0.9f;
                v.wnd.volume = Mathf.Lerp(v.wnd.volume, target * master * sp * sp * 0.5f, dt * 4f);
                v.scr.volume = Mathf.Lerp(v.scr.volume, target * master * sh.Scrape * 0.5f, dt * 12f);
                v.rep.volume = Mathf.Lerp(v.rep.volume, target * master * (sh.Repairing ? 0.4f : 0f), dt * 8f);
                if (alive && sh.Boosting && !v.wasBoost) uiSrc.PlayOneShot(boost, master * 0.5f);
                v.wasBoost = sh.Boosting;
                if (alive && sh.Critical) anyCritical = true;
            }
            if (anyCritical && !alarmSrc.isPlaying) alarmSrc.Play();
            if (!anyCritical && alarmSrc.isPlaying) alarmSrc.Stop();
            alarmSrc.volume = master * 0.35f;

            // nearest bots get the pooled 3D engine voices
            if (listener == null || all == null) return;
            var lp = listener.position;
            for (int k = 0; k < botVoices.Count; k++)
            {
                IVoiceShip best = null;
                float bd = 140f * 140f;
                foreach (var sh in all)
                {
                    if (sh.IsHuman || !sh.IsRacing) continue;
                    bool taken = false;
                    for (int j = 0; j < k; j++) if (botVoices[j].isPlaying && botVoices[j].transform.position == sh.Pos) taken = true;
                    if (taken) continue;
                    float d = (sh.Pos - lp).sqrMagnitude;
                    if (d < bd) { bd = d; best = sh; }
                }
                var src = botVoices[k];
                if (best == null || paused) { if (src.isPlaying) src.Stop(); continue; }
                src.transform.position = best.Pos;
                src.pitch = 0.6f + best.Speed01 * 1.2f + k * 0.03f;
                src.volume = master * 0.45f;
                if (!src.isPlaying) src.Play();
            }
        }
    }
}
