using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace Stardust
{
    /// <summary>
    /// Light and air of the island (port of environment_controller.gd): sun with cascaded shadows, sky, fog and
    /// ambient blended between the biome regions, darker light inside tunnels, sky reflections and the post stack.
    /// </summary>
    public class Atmosphere : MonoBehaviour
    {
        public const float SunAzimuth = 35f, SunElevation = 32f;

        public Light sun;
        public Material sky;
        public int quality = 2;
        Volume volume;
        ReflectionProbe probe;
        Color fogCol = new Color(0.68f, 0.73f, 0.75f), targetFog;
        float fogBegin = 350f, fogEnd = 5700f, ambient = 0.56f;
        float tBegin, tEnd, tAmbient;
        float clock;
        float caveK;
        Bloom bloom;
        ColorAdjustments color;
        public Vector3 ToSun { get; private set; }

        public static Atmosphere Create(Transform parent, int quality)
        {
            var go = new GameObject("Atmosphere");
            go.transform.SetParent(parent, false);
            var a = go.AddComponent<Atmosphere>();
            a.quality = quality;
            a.Setup();
            return a;
        }

        void Setup()
        {
            float az = SunAzimuth * Mathf.Deg2Rad, el = SunElevation * Mathf.Deg2Rad;
            ToSun = new Vector3(Mathf.Sin(az) * Mathf.Cos(el), Mathf.Sin(el), Mathf.Cos(az) * Mathf.Cos(el)).normalized;

            var sg = new GameObject("Sun");
            sg.transform.SetParent(transform, false);
            sg.transform.rotation = Quaternion.LookRotation(-ToSun);
            sun = sg.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = new Color(1f, 0.89f, 0.74f);
            sun.intensity = 1.65f;
            sun.shadows = quality >= 1 ? LightShadows.Soft : LightShadows.None;
            sun.shadowStrength = 0.92f;
            sun.shadowBias = 0.25f;
            sun.shadowNormalBias = 0.6f;
            RenderSettings.sun = sun;

            var baseSky = Resources.Load<Material>(IslandData.Root + "Materials/Sky");
            sky = baseSky != null ? new Material(baseSky) : null;
            if (sky != null)
            {
                sky.SetVector("_SunDir", ToSun);
                sky.SetColor("_SunCol", new Color(1f, 0.9f, 0.76f));
                sky.SetFloat("_Quality", quality >= 1 ? 1f : 0f);
                RenderSettings.skybox = sky;
            }
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Skybox;
            RenderSettings.reflectionIntensity = 0.85f;

            if (GraphicsSettings.currentRenderPipeline is UniversalRenderPipelineAsset urp)
            {
                urp.shadowDistance = quality >= 2 ? 320f : quality == 1 ? 140f : 0f;
                urp.shadowCascadeCount = quality >= 2 ? 4 : quality == 1 ? 2 : 1;
                if (quality >= 2) urp.cascade4Split = new Vector3(0.06f, 0.18f, 0.45f);
                else if (quality == 1) urp.cascade2Split = 0.3f;
                urp.renderScale = quality <= 0 ? 0.8f : quality == 1 ? 0.9f : 1f;
                urp.msaaSampleCount = quality >= 2 ? 4 : quality == 1 ? 2 : 1;
                urp.supportsCameraDepthTexture = quality >= 2;
                urp.supportsHDR = true;
            }

            // reflections of the sky (rendered once: only the skybox)
            var pg = new GameObject("SkyReflection");
            pg.transform.SetParent(transform, false);
            probe = pg.AddComponent<ReflectionProbe>();
            probe.mode = ReflectionProbeMode.Realtime;
            probe.refreshMode = ReflectionProbeRefreshMode.ViaScripting;
            probe.timeSlicingMode = ReflectionProbeTimeSlicingMode.NoTimeSlicing;
            probe.cullingMask = 0;
            probe.size = new Vector3(60000f, 6000f, 60000f);
            probe.resolution = quality >= 2 ? 128 : 64;
            probe.hdr = true;
            probe.importance = 0;
            probe.clearFlags = ReflectionProbeClearFlags.Skybox;

            // post-processing stack
            var vg = new GameObject("PostFX");
            vg.transform.SetParent(transform, false);
            volume = vg.AddComponent<Volume>();
            volume.isGlobal = true;
            var prof = ScriptableObject.CreateInstance<VolumeProfile>();
            var tm = prof.Add<Tonemapping>(true);
            tm.mode.Override(TonemappingMode.ACES);
            color = prof.Add<ColorAdjustments>(true);
            color.postExposure.Override(quality <= 0 ? 0.35f : 0.3f);
            color.contrast.Override(12f);
            color.saturation.Override(-4f);
            if (quality >= 1)
            {
                bloom = prof.Add<Bloom>(true);
                bloom.intensity.Override(quality >= 2 ? 0.4f : 0.3f);
                bloom.threshold.Override(1.25f);
                bloom.scatter.Override(0.65f);
                bloom.highQualityFiltering.Override(quality >= 2);
                var vig = prof.Add<Vignette>(true);
                vig.intensity.Override(0.2f);
                vig.smoothness.Override(0.5f);
                var wb = prof.Add<WhiteBalance>(true);
                wb.temperature.Override(4f);
                var sm = prof.Add<ShadowsMidtonesHighlights>(true);
                sm.shadows.Override(new Vector4(0.97f, 0.99f, 1.04f, 0f));
                sm.highlights.Override(new Vector4(1.03f, 1.0f, 0.96f, 0f));
            }
            volume.profile = prof;
            Apply(true);
        }

        /// <summary>Live quality change from the options (shadows, resolution, bloom, sky detail).</summary>
        public void SetQuality(int q)
        {
            quality = q;
            if (sun != null) sun.shadows = q >= 1 ? LightShadows.Soft : LightShadows.None;
            if (sky != null) sky.SetFloat("_Quality", q >= 1 ? 1f : 0f);
            if (GraphicsSettings.currentRenderPipeline is UniversalRenderPipelineAsset urp)
            {
                urp.shadowDistance = q >= 2 ? 320f : q == 1 ? 140f : 0f;
                urp.shadowCascadeCount = q >= 2 ? 4 : q == 1 ? 2 : 1;
                urp.renderScale = q <= 0 ? 0.8f : q == 1 ? 0.9f : 1f;
                urp.msaaSampleCount = q >= 2 ? 4 : q == 1 ? 2 : 1;
                urp.supportsCameraDepthTexture = q >= 2;
            }
            if (bloom != null) bloom.active = q >= 1;
        }

        public void RefreshReflections()
        {
            if (probe != null) probe.RenderProbe();
        }

        /// <summary>Region look per biome: fog colour, fog start, fog end, ambient energy.</summary>
        static void Biome(string b, out Color c, out float begin, out float end, out float energy)
        {
            switch (b)
            {
                case "sandstone": case "red": case "desert": case "arches": case "savanna":
                    c = new Color(0.78f, 0.69f, 0.56f); begin = 320f; end = 5800f; energy = 0.54f; break;
                case "jungle": case "forest": case "oasis":
                    c = new Color(0.56f, 0.69f, 0.68f); begin = 180f; end = 4400f; energy = 0.57f; break;
                case "coast": case "lagoon": case "salt":
                    c = new Color(0.67f, 0.78f, 0.83f); begin = 460f; end = 6500f; energy = 0.6f; break;
                default:
                    c = new Color(0.64f, 0.72f, 0.79f); begin = 380f; end = 5700f; energy = 0.56f; break;
            }
        }

        /// <summary>Blends the region look around the viewer (call every frame).</summary>
        public void Tick(Vector3 viewer, bool inCave, float dt, bool immediate = false)
        {
            var w = IslandWorld.I;
            clock -= dt;
            if ((clock <= 0f || immediate) && w != null && w.data != null)
            {
                clock = 0.5f;
                Color c = Color.clear;
                float b = 0f, e = 0f, en = 0f, total = 0f;
                foreach (var z in w.data.zones)
                {
                    float dx = viewer.x - z.c[0], dz = viewer.z - z.c[1];
                    float weight = 1f / Mathf.Pow(1f + (dx * dx + dz * dz) / 1600000f, 2f);
                    Biome(z.biome, out var zc, out var zb, out var ze, out var zen);
                    c += zc * weight; b += zb * weight; e += ze * weight; en += zen * weight;
                    total += weight;
                }
                total = Mathf.Max(total, 1e-6f);
                targetFog = c / total;
                tBegin = b / total;
                tEnd = e / total;
                tAmbient = en / total;
                if (quality <= 0) tEnd = Mathf.Min(tEnd, 3200f);
            }
            float k = immediate ? 1f : 1f - Mathf.Exp(-dt * 1.5f);
            fogCol = Color.Lerp(fogCol, targetFog, k);
            fogBegin = Mathf.Lerp(fogBegin, tBegin, k);
            fogEnd = Mathf.Lerp(fogEnd, tEnd, k);
            ambient = Mathf.Lerp(ambient, tAmbient, k);
            caveK = Mathf.MoveTowards(caveK, inCave ? 1f : 0f, dt * (immediate ? 100f : 1.8f));
            Apply(false);
        }

        void Apply(bool first)
        {
            if (first)
            {
                targetFog = fogCol; tBegin = fogBegin; tEnd = fogEnd; tAmbient = ambient;
            }
            RenderSettings.fogColor = fogCol;
            RenderSettings.fogStartDistance = fogBegin;
            RenderSettings.fogEndDistance = fogEnd;
            float amb = Mathf.Lerp(ambient, 0.3f, caveK) * 1.9f;
            var skyC = new Color(0.57f, 0.67f, 0.79f) * amb;
            var eqC = Color.Lerp(fogCol, new Color(0.6f, 0.6f, 0.6f), 0.3f) * amb * 0.8f;
            var grC = new Color(0.36f, 0.31f, 0.26f) * amb * 0.55f;
            RenderSettings.ambientSkyColor = skyC;
            RenderSettings.ambientEquatorColor = eqC;
            RenderSettings.ambientGroundColor = grC;
            // the shaders read the ambient probe (SH): build it from the three colours
            var sh = new SphericalHarmonicsL2();
            sh.AddAmbientLight(eqC);
            sh.AddDirectionalLight(Vector3.up, skyC - eqC, 1f);
            sh.AddDirectionalLight(Vector3.down, grC - eqC, 1f);
            RenderSettings.ambientProbe = sh;
            if (sun != null) sun.intensity = Mathf.Lerp(1.65f, 0.9f, caveK);
            if (sky != null)
            {
                sky.SetColor("_Horizon", fogCol);
                sky.SetColor("_Ground", fogCol * 0.8f);
            }
            if (color != null) color.postExposure.value = Mathf.Lerp(quality <= 0 ? 0.35f : 0.3f, 0.75f, caveK);
        }

        public Color FogColor => fogCol;
    }
}
