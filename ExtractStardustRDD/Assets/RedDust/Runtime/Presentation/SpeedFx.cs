using RedDust.Track;
using RedDust.Vehicle;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RedDust.Presentation
{
    /// <summary>
    /// Sensação de velocidade (acima de ~230 km/h fica vertiginosa):
    ///  - pós-processamento dinâmico: desfoque de movimento (só PC), aberração cromática, distorção de lente, vinheta;
    ///  - riscos de vento a passar à volta da câmera;
    ///  - rasto de pó do leito (cor e densidade pela superfície; mais forte a derrapar);
    ///  - chama do nitro e faíscas nos impactos.
    /// Intensidade guiada por ChaseCamera.Vertigo e pelo nitro. As partículas são emitidas por código (sem assets).
    /// </summary>
    public class SpeedFx : MonoBehaviour
    {
        CraftController craft;
        ChaseCamera chase;
        bool mobile;
        MotionBlur blur;
        ChromaticAberration chroma;
        LensDistortion lens;
        Vignette vignette;
        ParticleSystem streaks, dust, flame, sparks;
        float streakAcc, dustAcc, flameAcc, boostSmooth, driftSmooth;
        Transform[] exhausts = new Transform[0];

        public static SpeedFx Attach(Camera cam, CraftController craft, ChaseCamera chase, bool mobile)
        {
            var fx = cam.gameObject.AddComponent<SpeedFx>();
            fx.craft = craft; fx.chase = chase; fx.mobile = mobile;
            fx.Build();
            fx.exhausts = System.Array.FindAll(craft.GetComponentsInChildren<Transform>(), t => t.name.StartsWith("ExhaustPoint"));
            craft.Impacted += fx.OnImpact;
            return fx;
        }

        /// <summary>
        /// Ecrã dividido: o volume de pós-processamento e as partículas desta câmera passam para uma camada própria
        /// (a câmera usa essa camada no volumeLayerMask e a outra câmera exclui-a do culling).
        /// </summary>
        public void Isolate(int layer)
        {
            foreach (var t in GetComponentsInChildren<Transform>(true)) if (t != transform) t.gameObject.layer = layer;
            foreach (var ps in new[] { dust, flame, sparks })
                if (ps != null) foreach (var t in ps.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = layer;
        }

        void OnDestroy()
        {
            if (craft != null) craft.Impacted -= OnImpact;
            // as partículas em espaço do mundo não são filhas da câmera: saem com ela (corridas seguidas)
            foreach (var ps in new[] { dust, flame, sparks }) if (ps != null) Destroy(ps.gameObject);
        }

        void Build()
        {
            var add = Resources.Load<Material>("RedDust/FxAdd");
            var soft = Resources.Load<Material>("RedDust/FxDust");

            var go = new GameObject("SpeedFxVolume");
            go.transform.SetParent(transform, false);
            var volume = go.AddComponent<Volume>();
            volume.isGlobal = true;
            volume.priority = 10f;
            var profile = ScriptableObject.CreateInstance<VolumeProfile>();
            if (!mobile)
            {
                blur = profile.Add<MotionBlur>(true);
                blur.mode.Override(MotionBlurMode.CameraOnly);
                blur.quality.Override(MotionBlurQuality.Medium);
                blur.intensity.Override(0f);
                blur.clamp.Override(0.1f);
            }
            chroma = profile.Add<ChromaticAberration>(true);
            chroma.intensity.Override(0f);
            lens = profile.Add<LensDistortion>(true);
            lens.intensity.Override(0f);
            lens.scale.Override(1f);
            vignette = profile.Add<Vignette>(true);
            vignette.intensity.Override(0.2f);
            vignette.smoothness.Override(0.45f);
            volume.profile = profile;

            streaks = MakeSystem("SpeedStreaks", transform, add, ParticleSystemSimulationSpace.Local, ParticleSystemRenderMode.Stretch, 700, 0.035f);
            dust = MakeSystem("DustWake", null, soft, ParticleSystemSimulationSpace.World, ParticleSystemRenderMode.Billboard, mobile ? 300 : 900, 0f);
            var sol = dust.sizeOverLifetime;
            sol.enabled = true;
            sol.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0f, 0.55f, 1f, 2.2f));
            var lv = dust.limitVelocityOverLifetime;
            lv.enabled = true;
            lv.drag = 2.2f;
            lv.multiplyDragByParticleSize = false;
            Fade(dust, 0.15f);
            flame = MakeSystem("NitroFlame", null, add, ParticleSystemSimulationSpace.World, ParticleSystemRenderMode.Stretch, 400, 0.012f);
            sparks = MakeSystem("Sparks", null, add, ParticleSystemSimulationSpace.World, ParticleSystemRenderMode.Stretch, 300, 0.03f);
            var sm = sparks.main;
            sm.gravityModifier = 1.6f;
        }

        static ParticleSystem MakeSystem(string name, Transform parent, Material mat, ParticleSystemSimulationSpace space, ParticleSystemRenderMode mode, int max, float velocityScale)
        {
            var go = new GameObject(name);
            if (parent != null) go.transform.SetParent(parent, false);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.loop = true;
            main.playOnAwake = false;
            main.simulationSpace = space;
            main.maxParticles = max;
            main.startSpeed = 0f;
            var em = ps.emission; em.enabled = false;       // emitidas por código
            var sh = ps.shape; sh.enabled = false;
            Fade(ps, 0f);
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = mat;
            r.renderMode = mode;
            r.velocityScale = velocityScale;
            r.lengthScale = mode == ParticleSystemRenderMode.Stretch ? 1f : 0f;
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            ps.Play();
            return ps;
        }

        static void Fade(ParticleSystem ps, float fadeIn)
        {
            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                      fadeIn > 0f
                          ? new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, fadeIn), new GradientAlphaKey(0f, 1f) }
                          : new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(1f, 0.6f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
        }

        void LateUpdate()
        {
            if (craft == null || chase == null) return;
            float dt = Time.deltaTime;
            if (dt <= 0f) return;
            float v = craft.Speed;
            float V = chase.Vertigo;
            boostSmooth = Mathf.MoveTowards(boostSmooth, craft.Boosting ? 1f : 0f, dt * 3f);
            driftSmooth = Mathf.MoveTowards(driftSmooth, craft.Drifting ? 1f : 0f, dt * 4f);

            // pós-processamento
            // sem motion blur (pedido do jogador: a nave tem de se ver sempre); o resto muito discreto
            if (blur != null) { blur.intensity.value = 0f; blur.active = false; }
            chroma.intensity.value = 0.06f * boostSmooth;
            lens.intensity.value = -(0.02f * V + 0.05f * boostSmooth);
            vignette.intensity.value = 0.14f + 0.04f * V + 0.05f * boostSmooth;

            var ep = new ParticleSystem.EmitParams();

            // riscos de vento: anel à volta do eixo de visão, a passar pela câmera
            streakAcc += ((mobile ? 60f : 120f) * V + 60f * V * boostSmooth) * dt;
            while (streakAcc >= 1f)
            {
                streakAcc -= 1f;
                float ang = Random.value * Mathf.PI * 2f;
                float rad = Random.Range(3.5f, 13f);
                float z = Random.Range(35f, 70f);
                float vz = v * 1.1f + 10f;
                ep.position = new Vector3(Mathf.Cos(ang) * rad * 1.5f, Mathf.Sin(ang) * rad, z);
                ep.velocity = new Vector3(0f, 0f, -vz);
                ep.startLifetime = (z + 4f) / vz;
                ep.startSize = Random.Range(0.035f, 0.07f);
                bool ember = Random.value < 0.12f;              // brasas laranja entre os riscos de vento
                ep.startSize = ember ? Random.Range(0.06f, 0.11f) : ep.startSize;
                ep.startColor = ember ? new Color(1f, 0.55f, 0.18f, 0.9f * Mathf.Max(V, boostSmooth * 0.6f))
                                      : new Color(1f, 0.95f, 0.86f, Random.Range(0.25f, 0.5f) * Mathf.Max(V, boostSmooth * 0.6f));
                streaks.Emit(ep, 1);
            }

            // rasto de pó do leito
            if (craft.Grounded && v > 25f)
            {
                SurfaceDust(craft.Surface, out Color c, out float density);
                float rate = density * Mathf.InverseLerp(25f, 120f, v) * (mobile ? 40f : 95f) * (1f + 0.6f * boostSmooth + 1.8f * driftSmooth);
                dustAcc += rate * dt;
                Vector3 up = craft.Up, fwd = craft.Forward, right = craft.Right;
                Vector3 baseP = craft.Position - up * craft.tuning.hoverHeight;
                while (dustAcc >= 1f)
                {
                    dustAcc -= 1f;
                    float side = Random.Range(-1.8f, 1.8f) * (1f + driftSmooth);
                    ep.position = baseP + right * side - fwd * Random.Range(1f, 3.5f) + up * 0.3f;
                    ep.velocity = craft.Velocity * Random.Range(0.55f, 0.8f) + up * Random.Range(1f, 5f) + right * (side * Random.Range(1.5f, 4f));
                    ep.startLifetime = Random.Range(1.0f, 1.9f);
                    ep.startSize = Random.Range(1.3f, 3.2f);
                    ep.startColor = new Color(c.r, c.g, c.b, Mathf.Clamp01(c.a * (0.7f + 0.6f * driftSmooth)));
                    dust.Emit(ep, 1);
                }
            }

            // escape dos dois motores: chama laranja que cresce com o acelerador; com nitro fica branca-azul e maior
            float thr = Mathf.Clamp01(craft.input.throttle);
            if (thr > 0.02f || craft.Boosting)
            {
                flameAcc += (mobile ? 90f : 220f) * (0.35f + 0.65f * Mathf.Max(thr, boostSmooth)) * dt;
                while (flameAcc >= 1f)
                {
                    flameAcc -= 1f;
                    Vector3 tail = exhausts.Length > 0 ? exhausts[Random.Range(0, exhausts.Length)].position
                                                       : craft.Position - craft.Forward * 2.5f + craft.Up * 0.2f;
                    bool hot = craft.Boosting && Random.value < 0.6f;
                    ep.position = tail + Random.insideUnitSphere * 0.12f;
                    ep.velocity = craft.Velocity - craft.Forward * Random.Range(18f, 30f + 25f * boostSmooth) + Random.insideUnitSphere * 1.5f;
                    ep.startLifetime = Random.Range(0.06f, 0.12f + 0.1f * boostSmooth);
                    ep.startSize = Random.Range(0.3f, 0.55f) * (1f + 0.8f * boostSmooth);
                    ep.startColor = hot ? new Color(0.75f, 0.92f, 1f, 0.95f) : new Color(1f, 0.5f + 0.2f * Random.value, 0.16f, 0.9f);
                    flame.Emit(ep, 1);
                }
            }
        }

        static void SurfaceDust(Surface s, out Color c, out float density)
        {
            switch (s)
            {
                case Surface.DeepSand: c = new Color(0.79f, 0.57f, 0.39f, 0.42f); density = 1.6f; break;
                case Surface.Gravel: c = new Color(0.62f, 0.56f, 0.5f, 0.32f); density = 0.8f; break;
                case Surface.Slickrock: c = new Color(0.87f, 0.68f, 0.58f, 0.2f); density = 0.35f; break;
                case Surface.Rock: c = new Color(0.6f, 0.46f, 0.38f, 0.28f); density = 0.5f; break;
                default: c = new Color(0.82f, 0.6f, 0.42f, 0.36f); density = 1f; break;
            }
        }

        void OnImpact(float s, Vector3 n, Collider c)
        {
            if (sparks == null || craft == null) return;
            int count = Mathf.Clamp(Mathf.RoundToInt(s * 1.6f), 10, 60);
            var ep = new ParticleSystem.EmitParams();
            Vector3 at = craft.Position - n * 1.1f;
            for (int i = 0; i < count; i++)
            {
                ep.position = at + Random.insideUnitSphere * 0.4f;
                ep.velocity = craft.Velocity * 0.6f + (n + Random.insideUnitSphere * 0.9f) * Random.Range(4f, 10f + s * 0.5f);
                ep.startLifetime = Random.Range(0.25f, 0.6f);
                ep.startSize = Random.Range(0.06f, 0.13f);
                ep.startColor = new Color(1f, Random.Range(0.55f, 0.8f), 0.25f, 1f);
                sparks.Emit(ep, 1);
            }
        }
    }
}
