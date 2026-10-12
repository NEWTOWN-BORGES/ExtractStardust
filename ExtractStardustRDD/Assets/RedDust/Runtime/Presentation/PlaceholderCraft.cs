using System.Collections.Generic;
using RedDust.Vehicle;
using UnityEngine;

namespace RedDust.Presentation
{
    /// <summary>
    /// Visual provisório do STRIX para o laboratório (silhueta em cunha baixa e larga, cockpit central,
    /// dois propulsores integrados no casco, asas médias e cauda curta — Doc 02 §4.1). Não usa motores
    /// separados ligados por cabos (regra de IP). Fica dentro do envelope físico e não tem colliders.
    /// A nave final é modelada no Blender na M4/M7 com sockets de módulos.
    /// </summary>
    public static class PlaceholderCraft
    {
        public static GameObject Build(CraftController craft, Color paint)
        {
            var root = new GameObject("Visual");
            root.transform.SetParent(craft.transform, false);
            var mPaint = Mat("RedDust/CraftPaint", paint);
            var mDark = Mat("RedDust/CraftMetal", new Color(0.09f, 0.1f, 0.11f));
            var mGlass = Mat("RedDust/CraftGlass", new Color(0.05f, 0.08f, 0.12f));
            var mGlow = Mat("RedDust/CraftGlow", new Color(0.35f, 0.85f, 1f));

            // casco: loft de octógonos ao longo de z (nariz baixo e estreito, traseira larga)
            var hull = new MeshBuilder();
            var stations = new (float z, float w, float h, float y)[]
            {
                (3.55f, 0.55f, 0.22f, -0.18f), (2.6f, 1.6f, 0.46f, -0.12f), (1.2f, 2.5f, 0.74f, -0.02f),
                (-0.6f, 2.95f, 0.86f, 0.02f), (-2.4f, 3.1f, 0.82f, 0.0f), (-3.35f, 2.7f, 0.62f, -0.02f),
            };
            hull.Loft(stations, 8);
            Part(root, "Hull", hull.Build(), mPaint);

            // faixa escura inferior (blindagem ventral)
            var belly = new MeshBuilder();
            belly.Loft(new[] { (2.4f, 1.3f, 0.12f, -0.36f), (-0.5f, 2.6f, 0.16f, -0.42f), (-3.1f, 2.4f, 0.14f, -0.36f) }, 8);
            Part(root, "Belly", belly.Build(), mDark);

            // cockpit
            var canopy = new MeshBuilder();
            canopy.Loft(new[] { (1.5f, 0.2f, 0.12f, 0.32f), (0.9f, 0.95f, 0.42f, 0.42f), (-0.3f, 1.05f, 0.46f, 0.44f), (-1.2f, 0.7f, 0.3f, 0.38f) }, 8);
            Part(root, "Canopy", canopy.Build(), mGlass);

            // propulsores integrados (nacelas presas ao casco) + bocais emissivos
            foreach (float side in new[] { -1f, 1f })
            {
                var nac = new MeshBuilder();
                nac.Loft(new[] { (-0.6f, 0.62f, 0.62f, 0.02f), (-1.8f, 0.84f, 0.84f, 0.04f), (-3.3f, 0.86f, 0.86f, 0.04f), (-3.6f, 0.74f, 0.74f, 0.04f) }, 10, new Vector3(1.32f * side, 0f, 0f));
                Part(root, side < 0 ? "Nacelle_L" : "Nacelle_R", nac.Build(), mDark);
                var glow = new MeshBuilder();
                glow.Disc(new Vector3(1.32f * side, 0.04f, -3.62f), 0.33f, 12, Vector3.back);
                Part(root, side < 0 ? "Exhaust_L" : "Exhaust_R", glow.Build(false), mGlow);

                // asa média com ligeiro diedro
                var wing = new MeshBuilder();
                wing.Plate(new Vector3(1.35f * side, -0.02f, -0.4f), new Vector3(2.05f * side, 0.06f, -1.1f),
                           new Vector3(2.05f * side, 0.06f, -2.3f), new Vector3(1.35f * side, -0.02f, -2.6f), 0.07f);
                Part(root, side < 0 ? "Wing_L" : "Wing_R", wing.Build(), mPaint);
            }
            // cauda curta
            var fin = new MeshBuilder();
            fin.Plate(new Vector3(0f, 0.38f, -2.0f), new Vector3(0f, 0.95f, -2.9f), new Vector3(0f, 0.95f, -3.3f), new Vector3(0f, 0.38f, -3.25f), 0.08f, true);
            Part(root, "Tail", fin.Build(), mPaint);
            return root;
        }

        static readonly Dictionary<string, Material> cache = new Dictionary<string, Material>();

        static Material Mat(string resource, Color c)
        {
            string key = resource + ColorUtility.ToHtmlStringRGB(c);
            if (cache.TryGetValue(key, out var m)) return m;
            var src = Resources.Load<Material>(resource);
            m = src != null ? new Material(src) : new Material(Shader.Find("Universal Render Pipeline/Lit"));
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
            if (resource.EndsWith("Glow") && m.HasProperty("_EmissionColor"))
            {
                m.EnableKeyword("_EMISSION");
                m.SetColor("_EmissionColor", c * 2.2f);
            }
            cache[key] = m;
            return m;
        }

        static void Part(GameObject root, string name, Mesh mesh, Material mat)
        {
            var go = new GameObject(name);
            go.transform.SetParent(root.transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
        }
    }

    /// <summary>Construtor mínimo de malhas facetadas (lofts, discos, placas) para visuais provisórios.</summary>
    public sealed class MeshBuilder
    {
        readonly List<Vector3> v = new List<Vector3>();
        readonly List<int> t = new List<int>();

        void Tri(Vector3 a, Vector3 b, Vector3 c)
        {
            int i = v.Count;
            v.Add(a); v.Add(b); v.Add(c);
            t.Add(i); t.Add(i + 1); t.Add(i + 2);
        }

        void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d) { Tri(a, b, c); Tri(a, c, d); }

        /// <summary>Loft de secções octogonais (z, largura, altura, y) da frente para trás, com tampas.</summary>
        public void Loft(IList<(float z, float w, float h, float y)> st, int sides, Vector3 offset = default)
        {
            Vector3[][] rings = new Vector3[st.Count][];
            for (int s = 0; s < st.Count; s++)
            {
                rings[s] = new Vector3[sides];
                for (int k = 0; k < sides; k++)
                {
                    float a = (k + 0.5f) / sides * Mathf.PI * 2f;
                    rings[s][k] = offset + new Vector3(Mathf.Cos(a) * st[s].w * 0.5f, st[s].y + Mathf.Sin(a) * st[s].h * 0.5f, st[s].z);
                }
            }
            for (int s = 0; s + 1 < st.Count; s++)
                for (int k = 0; k < sides; k++)
                {
                    int k1 = (k + 1) % sides;
                    Quad(rings[s][k], rings[s][k1], rings[s + 1][k1], rings[s + 1][k]);
                }
            Vector3 cf = offset + new Vector3(0f, st[0].y, st[0].z + 0.05f);
            Vector3 cb = offset + new Vector3(0f, st[st.Count - 1].y, st[st.Count - 1].z - 0.02f);
            for (int k = 0; k < sides; k++)
            {
                int k1 = (k + 1) % sides;
                Tri(cf, rings[0][k1], rings[0][k]);
                Tri(cb, rings[st.Count - 1][k], rings[st.Count - 1][k1]);
            }
        }

        public void Disc(Vector3 c, float r, int sides, Vector3 normal)
        {
            var rot = Quaternion.LookRotation(normal);
            for (int k = 0; k < sides; k++)
            {
                float a0 = k / (float)sides * Mathf.PI * 2f, a1 = (k + 1) / (float)sides * Mathf.PI * 2f;
                Tri(c, c + rot * new Vector3(Mathf.Cos(a0), Mathf.Sin(a0), 0f) * r, c + rot * new Vector3(Mathf.Cos(a1), Mathf.Sin(a1), 0f) * r);
            }
        }

        /// <summary>Placa com espessura (asas, cauda). vertical = espessura em x em vez de y.</summary>
        public void Plate(Vector3 a, Vector3 b, Vector3 c, Vector3 d, float thick, bool vertical = false)
        {
            Vector3 o = (vertical ? Vector3.right : Vector3.up) * (thick * 0.5f);
            Quad(a + o, b + o, c + o, d + o);
            Quad(d - o, c - o, b - o, a - o);
            Quad(a - o, b - o, b + o, a + o);
            Quad(b - o, c - o, c + o, b + o);
            Quad(c - o, d - o, d + o, c + o);
            Quad(d - o, a - o, a + o, d + o);
        }

        /// <summary>Orienta cada triângulo para fora do centróide (peças convexas, incluindo as espelhadas).</summary>
        void FixOutward()
        {
            Vector3 c = Vector3.zero;
            foreach (var p in v) c += p;
            c /= Mathf.Max(1, v.Count);
            for (int i = 0; i + 2 < t.Count; i += 3)
            {
                Vector3 a = v[t[i]], b = v[t[i + 1]], d = v[t[i + 2]];
                if (Vector3.Dot(Vector3.Cross(b - a, d - a), (a + b + d) / 3f - c) < 0f) { int k = t[i + 1]; t[i + 1] = t[i + 2]; t[i + 2] = k; }
            }
        }

        public Mesh Build(bool outward = true)
        {
            if (outward) FixOutward();
            var m = new Mesh();
            m.SetVertices(v);
            m.SetTriangles(t, 0);
            m.RecalculateNormals();
            m.RecalculateBounds();
            return m;
        }
    }
}
