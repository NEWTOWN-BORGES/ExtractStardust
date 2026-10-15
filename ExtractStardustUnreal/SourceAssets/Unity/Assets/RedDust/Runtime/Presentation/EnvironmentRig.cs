using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RedDust.Presentation
{
    /// <summary>
    /// Atmosfera da RED DUST DIVIDE (uma única fonte de verdade para sol, céu, névoa e luz ambiente):
    ///  - sol quente a ~42° (sombras longas, mas o fundo dos canyons continua legível);
    ///  - luz ambiente integrada a partir de um gradiente céu → horizonte → chão de arenito (ressalto quente);
    ///  - perspetiva aérea própria (shader RedDust/Geology e RedDust/Sky): horizonte quente, sombras distantes
    ///    azul-violeta (Doc 01: "cool blue/violet distant canyon shadows");
    ///  - pós-processamento contido (ACES, bloom baixo). PC e Android mudam a qualidade, não o aspeto base.
    /// </summary>
    public static class EnvironmentRig
    {
        public static readonly Color Horizon = new Color(0.80f, 0.68f, 0.57f);
        public static readonly Color SunScatter = new Color(1.0f, 0.80f, 0.55f);
        public static readonly Color DistantShadow = new Color(0.42f, 0.47f, 0.64f);

        public static void Apply(Light sun, bool mobile)
        {
            if (sun != null)
            {
                sun.transform.rotation = Quaternion.Euler(42f, 228f, 0f);
                sun.color = new Color(1f, 0.89f, 0.76f);
                sun.intensity = 2.3f;
                sun.shadows = LightShadows.Soft;
                sun.shadowStrength = 0.95f;
                RenderSettings.sun = sun;
            }
            Vector3 toSun = sun != null ? -sun.transform.forward : new Vector3(0.5f, 0.67f, 0.55f).normalized;

            // perspetiva aérea (shaders RedDust)
            Shader.SetGlobalVector("_RD_FogColor", new Vector4(Horizon.r, Horizon.g, Horizon.b, mobile ? 0.00022f : 0.00016f));
            Shader.SetGlobalVector("_RD_FogSun", new Vector4(SunScatter.r, SunScatter.g, SunScatter.b, 7f));
            Shader.SetGlobalVector("_RD_FogShadow", new Vector4(DistantShadow.r, DistantShadow.g, DistantShadow.b, 0f));
            Shader.SetGlobalVector("_RD_FogParams", new Vector4(0.0016f, 0.93f, 0f, 0f));
            Shader.SetGlobalVector("_RD_SunDir", new Vector4(toSun.x, toSun.y, toSun.z, 0f));
            if (mobile) Shader.EnableKeyword("RD_LOW"); else Shader.DisableKeyword("RD_LOW");

            // névoa Unity para shaders padrão (nave): cor e alcance equivalentes
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = mobile ? 0.00018f : 0.00013f;
            RenderSettings.fogColor = Color.Lerp(Horizon, DistantShadow, 0.25f);
            if (RenderSettings.skybox != null && RenderSettings.skybox.HasProperty("_Zenith"))
                RenderSettings.skybox.SetColor("_Zenith", new Color(0.2f, 0.38f, 0.72f));

            // luz ambiente: gradiente integrado em SH (céu azul em cima, horizonte quente, ressalto do arenito em baixo)
            var sky = new Color(0.28f, 0.40f, 0.62f);
            var horizon = new Color(0.62f, 0.52f, 0.44f);
            var ground = new Color(0.50f, 0.28f, 0.16f);
            RenderSettings.ambientMode = AmbientMode.Custom;
            RenderSettings.ambientProbe = GradientSH(sky, horizon, ground);
            RenderSettings.ambientIntensity = 1f;
        }

        /// <summary>Integra um ambiente em gradiente vertical numa SH (soma de luzes direcionais em esfera de Fibonacci).</summary>
        public static SphericalHarmonicsL2 GradientSH(Color sky, Color horizon, Color ground)
        {
            var sh = new SphericalHarmonicsL2();
            const int n = 512;
            float golden = Mathf.PI * (3f - Mathf.Sqrt(5f));
            for (int i = 0; i < n; i++)
            {
                float y = 1f - 2f * (i + 0.5f) / n;
                float r = Mathf.Sqrt(Mathf.Max(0f, 1f - y * y));
                float th = golden * i;
                var dir = new Vector3(Mathf.Cos(th) * r, y, Mathf.Sin(th) * r);
                Color c = y >= 0f ? Color.Lerp(horizon, sky, Mathf.Pow(y, 0.6f)) : Color.Lerp(horizon, ground, Mathf.Pow(-y, 0.5f));
                sh.AddDirectionalLight(dir, c, 4f / n);
            }
            return sh;
        }

        public static Volume CreatePost(Transform parent, bool mobile)
        {
            var go = new GameObject("Post");
            if (parent != null) go.transform.SetParent(parent, false);
            var vol = go.AddComponent<Volume>();
            vol.isGlobal = true;
            vol.priority = 10;
            var profile = ScriptableObject.CreateInstance<VolumeProfile>();
            var tone = profile.Add<Tonemapping>(true);
            tone.mode.Override(TonemappingMode.ACES);
            var bloom = profile.Add<Bloom>(true);
            bloom.threshold.Override(1.2f);
            bloom.intensity.Override(mobile ? 0.12f : 0.22f);
            bloom.scatter.Override(0.55f);
            var color = profile.Add<ColorAdjustments>(true);
            color.postExposure.Override(0.25f);
            color.contrast.Override(12f);
            color.saturation.Override(4f);
            if (!mobile)
            {
                var vig = profile.Add<Vignette>(true);
                vig.intensity.Override(0.16f);
                vig.smoothness.Override(0.5f);
            }
            vol.sharedProfile = profile;
            return vol;
        }
    }
}
