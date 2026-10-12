using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Stardust
{
    /// <summary>
    /// "Cidadela Titã" (port of RACESTARS titan_circuit.gd): a floating circuit 440 m above the island — deck,
    /// rails, two ramp jumps with emergency bypasses, an orbital ring, towers and gantries — and its event data.
    /// The geometry is computed in the original Godot coordinates and mirrored (z) into Unity space.
    /// </summary>
    public class TitanCircuit : MonoBehaviour
    {
        static readonly Vector3 Center = new Vector3(9500f, 440f, 1000f);   // Godot space
        const float HalfWidth = 42f, RampLength = 100f, GapLength = 36f, RampRise = 14.054f, Step = 20f;
        public const float FallLimit = 360f;

        struct Jump { public Vector3 origin, dir; public float rampStart; }
        static Jump[] Jumps => new[]
        {
            new Jump { origin = Center + new Vector3(-500, 0, -640), dir = Vector3.right, rampStart = 240f },
            new Jump { origin = Center + new Vector3(760, 0, -420), dir = new Vector3(0, 0, 1), rampStart = 220f },
        };

        static Vector3 U(Vector3 g) => new Vector3(g.x, g.y, -g.z);   // Godot -> Unity

        static void Line(List<Vector3> pts, Vector3 a, Vector3 b, float rampStart = -1f)
        {
            float length = Vector3.Distance(a, b);
            var samples = new List<float>();
            for (int i = 1; i <= Mathf.CeilToInt(length / Step); i++) samples.Add(Mathf.Min(i * Step, length));
            if (rampStart >= 0f)
                foreach (var s in new[] { rampStart, rampStart + RampLength, rampStart + RampLength + GapLength })
                    if (!samples.Contains(s)) samples.Add(s);
            samples.Sort();
            foreach (var s in samples)
            {
                var p = Vector3.Lerp(a, b, s / length);
                if (rampStart >= 0f)
                {
                    if (s >= rampStart && s <= rampStart + RampLength) p.y += (s - rampStart) / RampLength * RampRise;
                    else if (s > rampStart + RampLength && s < rampStart + RampLength + GapLength) p.y += RampRise * (1f - (s - rampStart - RampLength) / GapLength);
                }
                pts.Add(p);
            }
        }

        static void Arc(List<Vector3> pts, Vector3 c, float radius, float begin, float end)
        {
            int count = Mathf.CeilToInt(Mathf.Abs(end - begin) * radius / Step);
            for (int i = 1; i <= count; i++)
            {
                float a = Mathf.Lerp(begin, end, i / (float)count);
                pts.Add(c + new Vector3(Mathf.Cos(a) * radius, 0f, Mathf.Sin(a) * radius));
            }
        }

        /// <summary>The closed lap in Godot space.</summary>
        static List<Vector3> PathG()
        {
            float PI = Mathf.PI;
            var p = new List<Vector3> { Center + new Vector3(-500, 0, -640) };
            Line(p, p[p.Count - 1], Center + new Vector3(540, 0, -640), 240f);
            Arc(p, Center + new Vector3(540, 0, -420), 220, -PI / 2, 0);
            Line(p, p[p.Count - 1], Center + new Vector3(760, 0, 420), 220f);
            Arc(p, Center + new Vector3(540, 0, 420), 220, 0, PI / 2);
            Line(p, p[p.Count - 1], Center + new Vector3(-540, 0, 640));
            Arc(p, Center + new Vector3(-540, 0, 480), 160, PI / 2, PI * 1.5f);
            Line(p, p[p.Count - 1], Center + new Vector3(300, 0, 320));
            Arc(p, Center + new Vector3(300, 0, 160), 160, PI / 2, -PI / 2);
            Line(p, p[p.Count - 1], Center + new Vector3(-500, 0, 0));
            Arc(p, Center + new Vector3(-500, 0, -220), 220, PI / 2, PI);
            Line(p, p[p.Count - 1], Center + new Vector3(-720, 0, -420));
            Arc(p, Center + new Vector3(-500, 0, -420), 220, PI, PI * 1.5f);
            p[p.Count - 1] = p[0];
            return p;
        }

        static bool IsGap(Vector3 p)
        {
            foreach (var j in Jumps)
            {
                var delta = p - j.origin;
                float along = Vector3.Dot(delta, j.dir);
                var side = delta - j.dir * along;
                if (new Vector2(side.x, side.z).magnitude < HalfWidth + 1f && along > j.rampStart + RampLength + 0.01f && along < j.rampStart + RampLength + GapLength - 0.01f)
                    return true;
            }
            return false;
        }

        static bool BypassOpen(Vector3 p)
        {
            foreach (var j in Jumps)
            {
                var delta = p - j.origin;
                float along = Vector3.Dot(delta, j.dir);
                var side = delta - j.dir * along;
                if (new Vector2(side.x, side.z).magnitude < 2f)
                {
                    float s = j.rampStart;
                    if ((along >= s - 150f && along <= s - 35f) || (along >= s + 345f && along <= s + 475f)) return true;
                }
            }
            return false;
        }

        static WGate Gate(Vector3 g, Vector3 dirG, float w, string name)
        {
            var p = U(g);
            var d = new Vector3(dirG.x, 0f, -dirG.z).normalized;
            return new WGate { p = new[] { p.x, p.y, p.z }, dir = new[] { d.x, d.z }, w = w, name = name };
        }

        /// <summary>Event of the circuit in the island's format (route, gates, jumps along the route).</summary>
        public static WEvent EventData()
        {
            var pts = PathG();
            var route = new List<float>();
            var gates = new List<WGate>();
            float length = 0f, since = 0f;
            for (int i = 0; i < pts.Count; i++)
            {
                var u = U(pts[i]);
                route.Add(u.x); route.Add(u.y); route.Add(u.z);
                if (i == 0) continue;
                float seg = Vector3.Distance(pts[i], pts[i - 1]);
                length += seg;
                since += seg;
                if (since > 440f && i < pts.Count - 14 && !IsGap(pts[i]) && pts[i].y < Center.y + 1f)
                {
                    var d = (pts[Mathf.Min(i + 1, pts.Count - 1)] - pts[i - 1]).normalized;
                    gates.Add(Gate(pts[i], d, 128f, $"TITÃ {gates.Count + 1:00}"));
                    since = 0f;
                }
            }
            gates.Add(Gate(pts[0], Vector3.right, 128f, "CIDADELA TITÃ"));
            // jump lips as distances along the route (bots: full speed, no braking)
            var jumps = new List<float>();
            float acc = 0f;
            for (int i = 1; i < pts.Count; i++)
            {
                acc += new Vector2(pts[i].x - pts[i - 1].x, pts[i].z - pts[i - 1].z).magnitude;
                foreach (var j in Jumps)
                {
                    var lip = j.origin + j.dir * (j.rampStart + RampLength);
                    if (new Vector2(pts[i].x - lip.x, pts[i].z - lip.z).magnitude < 1f) jumps.Add(acc);
                }
            }
            return new WEvent
            {
                id = "titan", name = "Cidadela Titã", type = "circuit", laps = 2, length = length, route = route.ToArray(),
                gates = gates.ToArray(), start = Gate(pts[0], Vector3.right, 0f, "Partida"), finish = new WGate { p = new[] { 0f, 0f, 0f }, dir = new[] { 0f, 1f }, w = 0f, name = "" },
                jumps = jumps.ToArray(),
            };
        }

        // ------------------------------------------------------------------ geometry

        readonly Dictionary<string, List<Matrix4x4>> batches = new Dictionary<string, List<Matrix4x4>>();
        readonly List<(Matrix4x4 m, int layer)> solids = new List<(Matrix4x4, int)>();
        readonly Dictionary<string, Material> mats = new Dictionary<string, Material>();
        Mesh cube, glowCube;
        InstanceDrawer drawer;

        static readonly Matrix4x4 Mirror = Matrix4x4.Scale(new Vector3(1f, 1f, -1f));

        void Box(string key, Vector3 posG, Vector3 size, Matrix4x4 basisG, bool solid = false)
        {
            var g = Matrix4x4.Translate(posG) * basisG * Matrix4x4.Scale(size);
            var u = Mirror * g * Mirror;
            if (!batches.TryGetValue(key, out var l)) batches[key] = l = new List<Matrix4x4>();
            l.Add(u);
            if (solid) solids.Add((u, key == "deck" ? IslandWorld.LayerRide : IslandWorld.LayerSolid));
        }

        static Matrix4x4 Basis(Vector3 x, Vector3 y, Vector3 z)
        {
            var m = Matrix4x4.identity;
            m.SetColumn(0, x); m.SetColumn(1, y); m.SetColumn(2, z);
            return m;
        }

        void Beam(string key, Vector3 a, Vector3 b, float width, float height, bool solid = false, float overlap = 0.6f)
        {
            var f = (b - a).normalized;
            var side = new Vector3(f.z, 0f, -f.x).normalized;
            var up = Vector3.Cross(f, side).normalized;
            // Godot's cross is right-handed like Unity's formula; keep the up vector pointing up
            if (up.y < 0f) up = -up;
            Box(key, (a + b) * 0.5f, new Vector3(width, height, Vector3.Distance(a, b) + overlap), Basis(side, up, f), solid);
        }

        void Road(Vector3 a, Vector3 b, float width, bool rails, int index)
        {
            var f = (b - a).normalized;
            var side = new Vector3(f.z, 0f, -f.x).normalized;
            var up = Vector3.Cross(f, side).normalized;
            if (up.y < 0f) up = -up;
            float overlap = Mathf.Abs(f.x) > 0.001f && Mathf.Abs(f.z) > 0.001f && Mathf.Abs(f.y) < 0.001f ? 7f : 0.6f;
            Beam("deck", a - up * 5f, b - up * 5f, width, 10f, true, overlap);
            foreach (float sg in new[] { -1f, 1f })
            {
                var edge = side * sg * (width * 0.5f - 1f);
                Beam("cyan", a + edge + up * 0.18f, b + edge + up * 0.18f, 1.4f, 0.25f);
                if (rails && !(sg > 0f && BypassOpen((a + b) * 0.5f)))
                {
                    Beam(index % 6 == 0 ? "orange" : "structure", a + edge + up * 2.3f, b + edge + up * 2.3f, 2.4f, 4.6f, true, overlap);
                    Beam("dark", a + edge - up * 12f, b + edge - up * 12f, 6f, 12f);
                }
            }
            if (index % 3 == 0) Beam("white", a + up * 0.18f, Vector3.Lerp(a, b, 0.45f) + up * 0.18f, 0.9f, 0.22f);
        }

        void BypassRoad(Jump j)
        {
            var forward = j.dir;
            var side = new Vector3(forward.z, 0f, -forward.x);
            var pts = new List<Vector3>();
            for (int i = 0; i <= 30; i++)
            {
                float t = i / 30f;
                pts.Add(j.origin + forward * (j.rampStart - 140f + t * 600f) + side * (100f * Mathf.Sin(Mathf.PI * t)));
            }
            for (int i = 0; i + 1 < pts.Count; i++)
            {
                Road(pts[i], pts[i + 1], 32f, false, i);
                if (i > 4 && i < 25) Beam("orange", pts[i] + side * 15f + Vector3.up * 2.3f, pts[i + 1] + side * 15f + Vector3.up * 2.3f, 2.4f, 4.6f, true);
            }
            var lip = j.origin + forward * (j.rampStart + RampLength) + Vector3.up * RampRise;
            Beam("orange", lip - side * 40f + Vector3.up * 0.3f, lip + side * 40f + Vector3.up * 0.3f, 2f, 0.4f);
            foreach (float sg in new[] { -1f, 1f })
            {
                Box("orange", j.origin + forward * (j.rampStart - 65f) + side * sg * 54f + Vector3.up * 16f, new Vector3(8, 32, 8), Matrix4x4.identity);
                Box("cyan", j.origin + forward * (j.rampStart - 65f) + side * sg * 54f + Vector3.up * 33f, new Vector3(11, 3, 11), Matrix4x4.identity);
            }
        }

        void Architecture()
        {
            var ringCenter = Center + new Vector3(0, 480, 160);
            for (int i = 0; i < 96; i++)
            {
                float a = Mathf.PI * 2f * i / 96f, b = Mathf.PI * 2f * (i + 1) / 96f;
                var p = ringCenter + new Vector3(Mathf.Cos(a) * 370f, Mathf.Sin(a) * 370f, 0);
                var q = ringCenter + new Vector3(Mathf.Cos(b) * 370f, Mathf.Sin(b) * 370f, 0);
                var tangent = (q - p).normalized;
                var radial = new Vector3(tangent.y, -tangent.x, 0);
                var basis = Basis(radial, new Vector3(0, 0, -1), tangent);
                Box("structure", (p + q) * 0.5f, new Vector3(26, 38, Vector3.Distance(p, q) + 1f), basis);
                Box("cyan", (p + q) * 0.5f + new Vector3(0, 0, -20), new Vector3(5, 2, Vector3.Distance(p, q) + 1f), basis);
                if (i % 8 == 0) Box("orange", (p + q) * 0.5f, new Vector3(37, 48, 11), basis);
            }
            foreach (float x in new[] { -860f, 900f })
                foreach (float z in new[] { -590f, -120f, 390f, 790f })
                {
                    var p = Center + new Vector3(x, 0, z);
                    Box("dark", p + new Vector3(0, 123, 0), new Vector3(38, 286, 38), Matrix4x4.identity, true);
                    for (int tier = 0; tier < 7; tier++)
                    {
                        Box("structure", p + new Vector3(0, 12 + tier * 42, 0), new Vector3(66 - tier * 4, 24, 66 - tier * 4), Matrix4x4.identity);
                        Box("cyan", p + new Vector3(0, 25 + tier * 42, 0), new Vector3(69 - tier * 4, 2.4f, 69 - tier * 4), Matrix4x4.identity);
                    }
                    Box("orange", p + new Vector3(0, 291, 0), new Vector3(52, 18, 52), Matrix4x4.identity);
                }
            foreach (float x in new[] { -300f, 160f, 600f })
            {
                var a = Center + new Vector3(x, 110, -735);
                var b = Center + new Vector3(x, 110, 735);
                Beam("structure", a, b, 22, 24);
                Beam("orange", a + Vector3.up * 20, b + Vector3.up * 20, 8, 6);
                foreach (float z in new[] { -735f, 735f }) Box("structure", Center + new Vector3(x, 50, z), new Vector3(22, 120, 30), Matrix4x4.identity, true);
                foreach (float z in new[] { -420f, -80f, 300f })
                {
                    Box("dark", Center + new Vector3(x, 91, z), new Vector3(110, 16, 130), Matrix4x4.identity);
                    Box("cyan", Center + new Vector3(x, 81, z), new Vector3(112, 2, 6), Matrix4x4.identity);
                }
            }
            foreach (float z in new[] { -640f, 640f })
                foreach (float x in new[] { -250f, 180f, 560f })
                {
                    Box("structure", Center + new Vector3(x, -20, z), new Vector3(135, 26, 72), Matrix4x4.identity);
                    Box("orange", Center + new Vector3(x, -34, z), new Vector3(78, 7, 58), Matrix4x4.identity);
                }
        }

        static Mesh MakeCube(float emission)
        {
            var mb = new MeshBuilder();
            mb.Box(Vector3.zero, Vector3.one, Quaternion.identity, new Color32(255, 255, 255, 255), new Color32(255, 255, 255, 255));
            return IslandWorld.Finish(mb, emission > 0f ? "titan_glow" : "titan_cube", 0.45f, 0f);
        }

        public static TitanCircuit Create(Transform parent, IslandWorld world)
        {
            var go = new GameObject("TitanCircuit");
            go.transform.SetParent(parent, false);
            var t = go.AddComponent<TitanCircuit>();
            t.Build(world);
            return t;
        }

        void Build(IslandWorld world)
        {
            var route = PathG();
            for (int i = 0; i + 1 < route.Count; i++)
            {
                if (IsGap((route[i] + route[i + 1]) * 0.5f)) continue;
                Road(route[i], route[i + 1], HalfWidth * 2f, true, i);
            }
            foreach (var j in Jumps) BypassRoad(j);
            Architecture();

            cube = MakeCube(0f);
            glowCube = MakeCube(1f);
            var surf = new Vector2[glowCube.vertexCount];
            for (int i = 0; i < surf.Length; i++) surf[i] = new Vector2(0.3f, 1.8f);
            glowCube.uv2 = surf;
            var metal = world.lib.materials[(int)MatClass.Metal];
            var plain = world.lib.materials[(int)MatClass.Plain];
            Material M(Material src, Color c, float metallic)
            {
                var m = new Material(src) { enableInstancing = true };
                m.SetColor("_Tint", c);
                m.SetFloat("_Metallic", metallic);
                m.SetFloat("_Tiling", 9f);
                m.SetFloat("_GroundAO", 0f);
                return m;
            }
            mats["deck"] = M(metal, new Color(0.2f, 0.28f, 0.34f), 0.3f);
            mats["structure"] = M(metal, new Color(0.53f, 0.59f, 0.62f), 0.55f);
            mats["dark"] = M(metal, new Color(0.09f, 0.14f, 0.18f), 0.5f);
            mats["orange"] = M(plain, new Color(0.93f, 0.54f, 0.22f), 0.3f);
            mats["white"] = M(plain, new Color(0.89f, 0.94f, 0.93f), 0.2f);
            mats["cyan"] = M(plain, new Color(0.39f, 0.91f, 0.94f), 0.1f);
            drawer = new InstanceDrawer();
            foreach (var kv in batches)
                drawer.Add("titan_" + kv.Key, kv.Key == "cyan" ? glowCube : cube, new[] { mats[kv.Key] }, kv.Value, 4096f, 9000f, kv.Key != "cyan");
            // solid parts: oriented box colliders
            var col = new GameObject("TitanColliders");
            col.transform.SetParent(transform, false);
            foreach (var (m, layer) in solids)
            {
                var c = new GameObject("b") { layer = layer };
                c.transform.SetParent(col.transform, false);
                c.transform.SetPositionAndRotation(m.GetColumn(3), m.rotation);
                c.transform.localScale = m.lossyScale;
                c.AddComponent<BoxCollider>();
            }
            Debug.Log($"[Titan] {route.Count - 1} segments, {solids.Count} solid boxes");
        }

        void LateUpdate()
        {
            var w = IslandWorld.I;
            if (w != null && w.viewers.Count > 0 && w.viewers[0] != null) drawer?.Draw(w.viewers[0].position);
        }
    }
}
