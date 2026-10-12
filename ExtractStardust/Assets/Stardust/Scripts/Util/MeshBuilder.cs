using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Stardust
{
    /// <summary>
    /// Procedural mesh helper. Vertex colours carry albedo; alpha = 1 lit, alpha = 0 emissive.
    /// The shaders render both faces, so winding mistakes never make faces vanish.
    /// </summary>
    public class MeshBuilder
    {
        public readonly List<Vector3> V = new List<Vector3>(4096);
        public readonly List<Color32> C = new List<Color32>(4096);
        public readonly List<int> T = new List<int>(8192);
        public readonly List<Vector2> UV = new List<Vector2>();
        public int Count => V.Count;

        /// <summary>Quad with 0..1 UVs (for textured transparent meshes; use only these in such builders).</summary>
        public void QuadUV(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Color32 ca, Color32 cb, Color32 cc, Color32 cd)
        {
            Quad(a, b, c, d, ca, cb, cc, cd);
            UV.Add(new Vector2(0, 0)); UV.Add(new Vector2(0, 1)); UV.Add(new Vector2(1, 1)); UV.Add(new Vector2(1, 0));
        }

        /// <summary>Camera-independent glow: two crossed quads centred at p.</summary>
        public void Halo(Vector3 p, Vector3 up, Vector3 right, float size, Color32 col)
        {
            var fwd = Vector3.Cross(right, up).normalized;
            float h = size * .5f;
            QuadUV(p - right * h - up * h, p - right * h + up * h, p + right * h + up * h, p + right * h - up * h, col, col, col, col);
            QuadUV(p - fwd * h - up * h, p - fwd * h + up * h, p + fwd * h + up * h, p + fwd * h - up * h, col, col, col, col);
        }

        static readonly Vector3[] CubeCorners =
        {
            new Vector3(-.5f, -.5f, -.5f), new Vector3(.5f, -.5f, -.5f), new Vector3(.5f, .5f, -.5f), new Vector3(-.5f, .5f, -.5f),
            new Vector3(-.5f, -.5f, .5f), new Vector3(.5f, -.5f, .5f), new Vector3(.5f, .5f, .5f), new Vector3(-.5f, .5f, .5f),
        };

        public void Clear() { V.Clear(); C.Clear(); T.Clear(); UV.Clear(); }

        public int Vert(Vector3 p, Color32 c) { V.Add(p); C.Add(c); return V.Count - 1; }

        public void Tri(Vector3 a, Vector3 b, Vector3 c, Color32 col)
        {
            int i = V.Count;
            V.Add(a); V.Add(b); V.Add(c);
            C.Add(col); C.Add(col); C.Add(col);
            T.Add(i); T.Add(i + 1); T.Add(i + 2);
        }

        public void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Color32 col) => Quad(a, b, c, d, col, col, col, col);

        public void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Color32 ca, Color32 cb, Color32 cc, Color32 cd)
        {
            int i = V.Count;
            V.Add(a); V.Add(b); V.Add(c); V.Add(d);
            C.Add(ca); C.Add(cb); C.Add(cc); C.Add(cd);
            T.Add(i); T.Add(i + 1); T.Add(i + 2);
            T.Add(i); T.Add(i + 2); T.Add(i + 3);
        }

        public void Box(Vector3 center, Vector3 size, Quaternion rot, Color32 col) => Box(Matrix4x4.TRS(center, rot, size), col, col);
        public void Box(Vector3 center, Vector3 size, Quaternion rot, Color32 side, Color32 top) => Box(Matrix4x4.TRS(center, rot, size), side, top);

        public void Box(Matrix4x4 m, Color32 side, Color32 top)
        {
            var p = new Vector3[8];
            for (int i = 0; i < 8; i++) p[i] = m.MultiplyPoint3x4(CubeCorners[i]);
            Quad(p[0], p[3], p[2], p[1], side); // back (-z)
            Quad(p[5], p[6], p[7], p[4], side); // front (+z)
            Quad(p[4], p[7], p[3], p[0], side); // left
            Quad(p[1], p[2], p[6], p[5], side); // right
            Quad(p[3], p[7], p[6], p[2], top);  // top
            Quad(p[0], p[1], p[5], p[4], side); // bottom
        }

        /// <summary>Tapered box: base square [-.5,.5] at y=0, top at y=1 scaled by (tx,tz) and offset.</summary>
        public void Frustum(Matrix4x4 m, float tx, float tz, Vector2 topOffset, Color32 side, Color32 top, bool bottom = false)
        {
            var b0 = m.MultiplyPoint3x4(new Vector3(-.5f, 0, -.5f));
            var b1 = m.MultiplyPoint3x4(new Vector3(.5f, 0, -.5f));
            var b2 = m.MultiplyPoint3x4(new Vector3(.5f, 0, .5f));
            var b3 = m.MultiplyPoint3x4(new Vector3(-.5f, 0, .5f));
            var t0 = m.MultiplyPoint3x4(new Vector3(-.5f * tx + topOffset.x, 1, -.5f * tz + topOffset.y));
            var t1 = m.MultiplyPoint3x4(new Vector3(.5f * tx + topOffset.x, 1, -.5f * tz + topOffset.y));
            var t2 = m.MultiplyPoint3x4(new Vector3(.5f * tx + topOffset.x, 1, .5f * tz + topOffset.y));
            var t3 = m.MultiplyPoint3x4(new Vector3(-.5f * tx + topOffset.x, 1, .5f * tz + topOffset.y));
            Quad(b0, t0, t1, b1, side);
            Quad(b1, t1, t2, b2, side);
            Quad(b2, t2, t3, b3, side);
            Quad(b3, t3, t0, b0, side);
            Quad(t0, t3, t2, t1, top);
            if (bottom) Quad(b0, b1, b2, b3, side);
        }

        /// <summary>N-sided prism/cone: radius .5 at y=0, top radius .5*topScale at y=1.</summary>
        public void Cylinder(Matrix4x4 m, int sides, float topScale, Color32 side, Color32 top, bool caps = true)
        {
            var bot = new Vector3[sides];
            var tp = new Vector3[sides];
            for (int i = 0; i < sides; i++)
            {
                float a = i * Mathf.PI * 2f / sides;
                float x = Mathf.Cos(a) * .5f, z = Mathf.Sin(a) * .5f;
                bot[i] = m.MultiplyPoint3x4(new Vector3(x, 0, z));
                tp[i] = m.MultiplyPoint3x4(new Vector3(x * topScale, 1, z * topScale));
            }
            for (int i = 0; i < sides; i++)
            {
                int j = (i + 1) % sides;
                if (topScale < 0.001f) Tri(bot[i], tp[i], bot[j], side);
                else Quad(bot[i], tp[i], tp[j], bot[j], side);
            }
            if (caps)
            {
                var ct = m.MultiplyPoint3x4(new Vector3(0, 1, 0));
                var cb = m.MultiplyPoint3x4(Vector3.zero);
                for (int i = 0; i < sides; i++)
                {
                    int j = (i + 1) % sides;
                    if (topScale >= 0.001f) Tri(tp[i], ct, tp[j], top);
                    Tri(bot[j], cb, bot[i], side);
                }
            }
        }

        /// <summary>Tube along a path with per-point radius (parallel transport frames).</summary>
        public void Tube(IList<Vector3> pts, IList<float> radii, int sides, Color32 col, Color32 col2)
        {
            int n = pts.Count;
            if (n < 2) return;
            var rings = new Vector3[n, sides];
            Vector3 prevT = (pts[1] - pts[0]).normalized;
            Vector3 normal = Vector3.Cross(prevT, Mathf.Abs(prevT.y) < 0.9f ? Vector3.up : Vector3.right).normalized;
            for (int i = 0; i < n; i++)
            {
                Vector3 t;
                if (i == 0) t = (pts[1] - pts[0]).normalized;
                else if (i == n - 1) t = (pts[n - 1] - pts[n - 2]).normalized;
                else t = (pts[i + 1] - pts[i - 1]).normalized;
                var q = Quaternion.FromToRotation(prevT, t);
                normal = (q * normal).normalized;
                prevT = t;
                var bin = Vector3.Cross(t, normal);
                for (int k = 0; k < sides; k++)
                {
                    float a = k * Mathf.PI * 2f / sides;
                    rings[i, k] = pts[i] + (normal * Mathf.Cos(a) + bin * Mathf.Sin(a)) * radii[i];
                }
            }
            for (int i = 0; i < n - 1; i++)
            {
                var c = (i & 1) == 0 ? col : col2;
                for (int k = 0; k < sides; k++)
                {
                    int k2 = (k + 1) % sides;
                    Quad(rings[i, k], rings[i + 1, k], rings[i + 1, k2], rings[i, k2], c);
                }
            }
        }

        static readonly Vector3[] Ico;
        static readonly int[] IcoTris =
        {
            0, 11, 5, 0, 5, 1, 0, 1, 7, 0, 7, 10, 0, 10, 11, 1, 5, 9, 5, 11, 4, 11, 10, 2, 10, 7, 6, 7, 1, 8,
            3, 9, 4, 3, 4, 2, 3, 2, 6, 3, 6, 8, 3, 8, 9, 4, 9, 5, 2, 4, 11, 6, 2, 10, 8, 6, 7, 9, 8, 1
        };

        static MeshBuilder()
        {
            float t = (1f + Mathf.Sqrt(5f)) / 2f;
            Ico = new[]
            {
                new Vector3(-1, t, 0), new Vector3(1, t, 0), new Vector3(-1, -t, 0), new Vector3(1, -t, 0),
                new Vector3(0, -1, t), new Vector3(0, 1, t), new Vector3(0, -1, -t), new Vector3(0, 1, -t),
                new Vector3(t, 0, -1), new Vector3(t, 0, 1), new Vector3(-t, 0, -1), new Vector3(-t, 0, 1),
            };
            for (int i = 0; i < Ico.Length; i++) Ico[i] = Ico[i].normalized * .5f;
        }

        /// <summary>Faceted boulder: displaced icosahedron (20 faces).</summary>
        public void Rock(Matrix4x4 m, System.Random rng, float jag, Color32 a, Color32 b)
        {
            var p = new Vector3[12];
            for (int i = 0; i < 12; i++)
            {
                float k = 1f + ((float)rng.NextDouble() * 2f - 1f) * jag;
                p[i] = m.MultiplyPoint3x4(Ico[i] * k);
            }
            for (int i = 0; i < IcoTris.Length; i += 3)
            {
                var c = ((i / 3) % 3 == 0) ? b : a;
                Tri(p[IcoTris[i]], p[IcoTris[i + 1]], p[IcoTris[i + 2]], c);
            }
        }

        /// <summary>Low-poly hemisphere of radius .5 resting on y=0.</summary>
        public void Dome(Matrix4x4 m, int seg, int rings, Color32 col, Color32 band)
        {
            for (int r = 0; r < rings; r++)
            {
                float a0 = r * Mathf.PI * .5f / rings, a1 = (r + 1) * Mathf.PI * .5f / rings;
                for (int s = 0; s < seg; s++)
                {
                    float b0 = s * Mathf.PI * 2f / seg, b1 = (s + 1) * Mathf.PI * 2f / seg;
                    Vector3 P(float a, float b) => m.MultiplyPoint3x4(new Vector3(Mathf.Cos(a) * Mathf.Cos(b), Mathf.Sin(a), Mathf.Cos(a) * Mathf.Sin(b)) * .5f);
                    var c = (r == 0) ? band : col;
                    if (r == rings - 1) Tri(P(a0, b0), P(a1, b0), P(a0, b1), c);
                    else Quad(P(a0, b0), P(a1, b0), P(a1, b1), P(a0, b1), c);
                }
            }
        }

        public void Append(MeshBuilder o)
        {
            int baseIndex = V.Count;
            V.AddRange(o.V);
            C.AddRange(o.C);
            for (int i = 0; i < o.T.Count; i++) T.Add(o.T[i] + baseIndex);
        }

        public void Append(MeshBuilder o, Matrix4x4 m)
        {
            int baseIndex = V.Count;
            for (int i = 0; i < o.V.Count; i++) V.Add(m.MultiplyPoint3x4(o.V[i]));
            C.AddRange(o.C);
            for (int i = 0; i < o.T.Count; i++) T.Add(o.T[i] + baseIndex);
        }

        public Mesh ToMesh(string name)
        {
            var mesh = new Mesh { name = name };
            if (V.Count > 65000) mesh.indexFormat = IndexFormat.UInt32;
            mesh.SetVertices(V);
            mesh.SetColors(C);
            if (UV.Count == V.Count) mesh.SetUVs(0, UV);
            mesh.SetTriangles(T, 0, true);
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }

        public static Color32 Col(float r, float g, float b, float emissive = 0f)
        {
            return new Color32((byte)(Mathf.Clamp01(r) * 255), (byte)(Mathf.Clamp01(g) * 255), (byte)(Mathf.Clamp01(b) * 255), (byte)((1f - Mathf.Clamp01(emissive)) * 255));
        }

        public static Color32 Col(Color c, float emissive = 0f) => Col(c.r, c.g, c.b, emissive);

        public static Color32 Glow(Color c) => Col(c.r, c.g, c.b, 1f);
    }

    public static class Noise
    {
        public static float Fbm(float x, float y, int oct = 4)
        {
            float sum = 0, amp = .5f, f = 1f;
            for (int i = 0; i < oct; i++)
            {
                sum += amp * Mathf.PerlinNoise(x * f + 31.7f * i, y * f - 17.3f * i);
                f *= 2.03f; amp *= .5f;
            }
            return sum / (1f - Mathf.Pow(.5f, oct)); // ~0..1
        }

        public static float Ridged(float x, float y, int oct = 4)
        {
            float sum = 0, amp = .5f, f = 1f;
            for (int i = 0; i < oct; i++)
            {
                float n = 1f - Mathf.Abs(Mathf.PerlinNoise(x * f + 11.1f * i, y * f + 5.3f * i) * 2f - 1f);
                sum += amp * n * n;
                f *= 2.1f; amp *= .5f;
            }
            return sum;
        }

        public static float Smooth01(float t) { t = Mathf.Clamp01(t); return t * t * (3f - 2f * t); }

        public static float Range(System.Random r, float a, float b) => a + (float)r.NextDouble() * (b - a);
    }
}
