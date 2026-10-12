using UnityEngine;
using UnityEngine.Rendering;

namespace Stardust
{
    /// <summary>Shared materials and procedural textures (no imported art required).</summary>
    public static class Res
    {
        static Material lit, add, alpha, addSoft, alphaSoft, addRing;
        static Texture2D soft, ring, streaks, vignette;
        static Font font;

        public static Font Font => font ? font : (font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"));

        static Material Load(string path, string shaderName)
        {
            var m = Resources.Load<Material>(path);
            if (m == null)
            {
                var sh = Shader.Find(shaderName);
                if (sh == null) { Debug.LogError("Shader em falta: " + shaderName); sh = Shader.Find("Hidden/InternalErrorShader"); }
                m = new Material(sh);
            }
            return m;
        }

        public static Material Lit => lit ? lit : (lit = Load("Stardust/VertexLit", "Stardust/VertexLit"));

        public static Material Add
        {
            get
            {
                if (add) return add;
                add = new Material(Load("Stardust/Additive", "Stardust/Particle")) { name = "AddWhite" };
                add.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                add.SetFloat("_DstBlend", (float)BlendMode.One);
                add.SetFloat("_FogToBlack", 1f);
                add.mainTexture = Texture2D.whiteTexture;
                return add;
            }
        }

        public static Material AddSoft
        {
            get
            {
                if (addSoft) return addSoft;
                addSoft = new Material(Add) { name = "AddSoft", mainTexture = SoftDot };
                return addSoft;
            }
        }

        public static Material AddRing
        {
            get
            {
                if (addRing) return addRing;
                addRing = new Material(Add) { name = "AddRing", mainTexture = Ring };
                return addRing;
            }
        }

        public static Material Alpha
        {
            get
            {
                if (alpha) return alpha;
                alpha = new Material(Load("Stardust/AlphaBlend", "Stardust/Particle")) { name = "Alpha" };
                alpha.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                alpha.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                alpha.SetFloat("_FogToBlack", 0f);
                alpha.mainTexture = Texture2D.whiteTexture;
                return alpha;
            }
        }

        public static Material AlphaSoft
        {
            get
            {
                if (alphaSoft) return alphaSoft;
                alphaSoft = new Material(Alpha) { name = "AlphaSoft", mainTexture = SoftDot };
                return alphaSoft;
            }
        }

        public static Texture2D SoftDot
        {
            get
            {
                if (soft) return soft;
                const int n = 64;
                soft = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "SoftDot" };
                var px = new Color32[n * n];
                for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float dx = (x + .5f) / n * 2f - 1f, dy = (y + .5f) / n * 2f - 1f;
                    float d = Mathf.Sqrt(dx * dx + dy * dy);
                    float a = Mathf.Clamp01(1f - d);
                    a = a * a * (3f - 2f * a);
                    px[y * n + x] = new Color32(255, 255, 255, (byte)(a * 255));
                }
                soft.SetPixels32(px);
                soft.Apply(false, true);
                return soft;
            }
        }

        public static Texture2D Ring
        {
            get
            {
                if (ring) return ring;
                const int n = 128;
                ring = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "Ring" };
                var px = new Color32[n * n];
                for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float dx = (x + .5f) / n * 2f - 1f, dy = (y + .5f) / n * 2f - 1f;
                    float d = Mathf.Sqrt(dx * dx + dy * dy);
                    float a = Mathf.Clamp01(1f - Mathf.Abs(d - 0.85f) / 0.12f) + Mathf.Clamp01(0.25f - d * 0.3f);
                    px[y * n + x] = new Color32(255, 255, 255, (byte)(Mathf.Clamp01(a) * 255));
                }
                ring.SetPixels32(px);
                ring.Apply(false, true);
                return ring;
            }
        }

        /// <summary>Radial streaks used as a full-screen speed overlay.</summary>
        public static Texture2D Streaks
        {
            get
            {
                if (streaks) return streaks;
                const int n = 256;
                streaks = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "Streaks" };
                var px = new Color32[n * n];
                var rng = new System.Random(7);
                var rays = new float[180];
                for (int i = 0; i < rays.Length; i++) rays[i] = rng.NextDouble() < 0.35 ? (float)rng.NextDouble() : 0f;
                for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float dx = (x + .5f) / n * 2f - 1f, dy = (y + .5f) / n * 2f - 1f;
                    float d = Mathf.Sqrt(dx * dx + dy * dy);
                    float ang = (Mathf.Atan2(dy, dx) / (Mathf.PI * 2f) + .5f) * rays.Length;
                    int ai = Mathf.Clamp((int)ang, 0, rays.Length - 1);
                    float ray = rays[ai] * Mathf.Clamp01(1f - Mathf.Abs(ang - ai - .5f) * 2.2f);
                    float a = ray * Mathf.Clamp01((d - 0.45f) / 0.5f);
                    px[y * n + x] = new Color32(255, 255, 255, (byte)(Mathf.Clamp01(a) * 200));
                }
                streaks.SetPixels32(px);
                streaks.Apply(false, true);
                return streaks;
            }
        }

        public static Texture2D Vignette
        {
            get
            {
                if (vignette) return vignette;
                const int n = 128;
                vignette = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "Vignette" };
                var px = new Color32[n * n];
                for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float dx = (x + .5f) / n * 2f - 1f, dy = (y + .5f) / n * 2f - 1f;
                    float d = Mathf.Sqrt(dx * dx + dy * dy) / 1.414f;
                    float a = Mathf.Clamp01((d - 0.45f) / 0.55f);
                    px[y * n + x] = new Color32(255, 255, 255, (byte)(a * a * 255));
                }
                vignette.SetPixels32(px);
                vignette.Apply(false, true);
                return vignette;
            }
        }

        public static void SetLighting(Vector3 sunDir, Color sun, Color sky, Color ground)
        {
            Shader.SetGlobalVector("_SD_SunDir", sunDir.normalized);
            Shader.SetGlobalColor("_SD_SunColor", sun);
            Shader.SetGlobalColor("_SD_SkyAmb", sky);
            Shader.SetGlobalColor("_SD_GroundAmb", ground);
        }
    }
}
