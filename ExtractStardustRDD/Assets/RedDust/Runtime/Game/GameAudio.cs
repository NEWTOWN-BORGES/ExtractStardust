using System.Collections.Generic;
using RedDust.Vehicle;
using UnityEngine;

namespace RedDust.Game
{
    /// <summary>
    /// Som do jogo (clips gerados por Tools/gen_audio.py em Resources/Audio): efeitos 2D da interface e da corrida,
    /// música ambiente em loop e garantia de que existe sempre um AudioListener. Desligado em batchmode (testes).
    /// </summary>
    public sealed class GameAudio : MonoBehaviour
    {
        static GameAudio inst;
        static readonly Dictionary<string, AudioClip> clips = new Dictionary<string, AudioClip>();
        public static bool Off => Application.isBatchMode;
        AudioSource fx, music;
        AudioListener ownListener;
        float nextCheck;

        public static AudioClip Clip(string n)
        {
            if (!clips.TryGetValue(n, out var c)) { c = Resources.Load<AudioClip>("Audio/" + n); clips[n] = c; }
            return c;
        }

        static GameAudio I
        {
            get
            {
                if (inst == null && !Off)
                {
                    var go = new GameObject("GameAudio");
                    DontDestroyOnLoad(go);
                    inst = go.AddComponent<GameAudio>();
                }
                return inst;
            }
        }

        public static void Ensure() { var _ = I; }

        void Awake()
        {
            fx = gameObject.AddComponent<AudioSource>();
            fx.playOnAwake = false;
            fx.spatialBlend = 0f;
            music = gameObject.AddComponent<AudioSource>();
            music.clip = Clip("music_menu");
            music.loop = true;
            music.volume = 0.26f;
            if (music.clip != null) music.Play();
        }

        void Update()
        {
            if (Time.unscaledTime < nextCheck) return;
            nextCheck = Time.unscaledTime + 0.5f;
            // um AudioListener sempre: o da câmara do jogo se existir; senão o nosso
            var all = FindObjectsByType<AudioListener>(FindObjectsSortMode.None);
            int others = 0;
            foreach (var l in all) if (l != ownListener && l.enabled && l.gameObject.activeInHierarchy) others++;
            if (others == 0 && ownListener == null) ownListener = gameObject.AddComponent<AudioListener>();
            if (ownListener != null) ownListener.enabled = others == 0;
        }

        /// <summary>Efeito 2D (interface, avisos).</summary>
        public static void Play(string n, float vol = 1f, float pitch = 1f)
        {
            var a = I;
            var c = Clip(n);
            if (a == null || c == null) return;
            a.fx.pitch = pitch;
            a.fx.PlayOneShot(c, vol);
        }

        /// <summary>Efeito 3D num ponto (impactos, explosões).</summary>
        public static void PlayAt(string n, Vector3 p, float vol = 1f)
        {
            if (Off) return;
            var c = Clip(n);
            if (c != null) AudioSource.PlayClipAtPoint(c, p, vol);
        }

        /// <summary>Música: faixa calma nos menus, faixa de corrida (120 BPM) em corrida; troca de faixa e volume suave.</summary>
        public static void Music(bool race)
        {
            var a = I;
            if (a == null) return;
            var want = Clip(race ? "music_race" : "music_menu");
            if (want != null && a.music.clip != want) { a.music.clip = want; a.music.Play(); }
            a.music.volume = Mathf.MoveTowards(a.music.volume, race ? 0.17f : 0.26f, 0.02f);
        }

        /// <summary>Som a partir das notificações da corrida (feed): extração, destruição, checkpoints, avisos.</summary>
        public static void OnNote(string text, bool mine)
        {
            if (Off || string.IsNullOrEmpty(text)) return;
            if (text.Contains("DESTROYED")) Play("explosion", mine ? 1f : 0.5f);
            else if (text.Contains("EXTRACTED")) Play("extract", mine ? 0.9f : 0.35f);
            else if (text.StartsWith("CHECKPOINT")) Play("checkpoint", 0.7f);
            else if (text.Contains("STRANDED") || text.Contains("Reposicionado") || text.Contains("penaliza")) Play("warning", 0.7f);
            else if (mine) Play("loot", 0.6f);
        }
    }

    /// <summary>Motor, boost e vento de uma nave (3D) + impactos e aterragens.</summary>
    public sealed class EngineAudio : MonoBehaviour
    {
        public CraftController craft;
        AudioSource eng, boost, wind, slide;

        void Start()
        {
            if (GameAudio.Off || craft == null) { enabled = false; return; }
            GameAudio.Ensure();
            eng = Loop("engine_loop", 0.4f);
            boost = Loop("boost_loop", 0f);
            wind = Loop("wind_loop", 0f);
            slide = Loop("drift_loop", 0f);
            craft.Impacted += (v, n, c) => { if (v > 4f) GameAudio.PlayAt("impact", craft.Position, Mathf.Clamp(v / 30f, 0.2f, 1f)); };
            craft.Landed += v => { if (v > 6f) GameAudio.PlayAt("land", craft.Position, Mathf.Clamp(v / 20f, 0.2f, 0.8f)); };
        }

        AudioSource Loop(string n, float vol)
        {
            var c = GameAudio.Clip(n);
            if (c == null) return null;
            var s = gameObject.AddComponent<AudioSource>();
            s.clip = c;
            s.loop = true;
            s.volume = vol;
            s.spatialBlend = 0.85f;
            s.rolloffMode = AudioRolloffMode.Linear;
            s.minDistance = 8f;
            s.maxDistance = 140f;
            s.dopplerLevel = 0.25f;
            s.time = Random.value * c.length * 0.9f;
            s.Play();
            return s;
        }

        void Update()
        {
            float sp = Mathf.Clamp01(craft.Speed / 125f);
            if (eng != null) { eng.pitch = 0.62f + sp * 1.05f + (craft.Boosting ? 0.12f : 0f); eng.volume = 0.28f + sp * 0.32f; }
            if (boost != null) boost.volume = Mathf.MoveTowards(boost.volume, craft.Boosting ? 0.5f : 0f, Time.deltaTime * 3f);
            if (slide != null) { slide.volume = Mathf.MoveTowards(slide.volume, craft.Drifting ? 0.25f + sp * 0.3f : 0f, Time.deltaTime * 5f); slide.pitch = 0.85f + sp * 0.35f; }
            if (wind != null) { wind.volume = sp * sp * 0.4f; wind.pitch = 0.8f + sp * 0.5f; }
        }
    }
}
