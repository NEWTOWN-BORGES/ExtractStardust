using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Stardust
{
    /// <summary>
    /// Dense grass in a ring around the camera: 16 m cells with blade clusters at fixed pseudo-random spots on the
    /// terrain. The shader keeps only the clusters on grassy biome off the roads and fades the ring's edge.
    /// Cells are cached; the visible list is rebuilt only when the camera crosses into another cell.
    /// </summary>
    public class GrassField
    {
        const float Cell = 16f;
        readonly IslandWorld world;
        readonly Mesh mesh;
        readonly Material mat;
        readonly int perCell;
        readonly float radius;
        readonly Dictionary<long, Matrix4x4[]> cache = new Dictionary<long, Matrix4x4[]>();
        readonly List<Matrix4x4> visible = new List<Matrix4x4>(20000);
        Matrix4x4[] buffer = new Matrix4x4[0];
        int lastCx = int.MinValue, lastCz = int.MinValue;
        Bounds bounds;

        public GrassField(IslandWorld w, int quality)
        {
            world = w;
            radius = quality <= 0 ? 45f : quality == 1 ? 70f : 95f;
            perCell = quality <= 0 ? 55 : quality == 1 ? 90 : 120;
            var baseMat = Resources.Load<Material>(IslandData.Root + "Materials/Grass");
            if (baseMat != null)
            {
                mat = new Material(baseMat) { enableInstancing = true };
                mat.SetFloat("_Radius", radius);
            }
            mesh = BuildCluster();
        }

        static Mesh BuildCluster()
        {
            var v = new List<Vector3>();
            var c = new List<Color32>();
            var t = new List<int>();
            var rng = new System.Random(11);
            int blades = 9;
            for (int b = 0; b < blades; b++)
            {
                float a = (float)rng.NextDouble() * Mathf.PI * 2f;
                float r = (float)rng.NextDouble() * 0.45f;
                var root = new Vector3(Mathf.Cos(a) * r, 0f, Mathf.Sin(a) * r);
                float h = 0.55f + (float)rng.NextDouble() * 0.5f;
                float w = 0.05f + (float)rng.NextDouble() * 0.03f;
                float facing = (float)rng.NextDouble() * Mathf.PI;
                var side = new Vector3(Mathf.Cos(facing), 0f, Mathf.Sin(facing)) * w;
                var lean = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a)) * (0.15f + (float)rng.NextDouble() * 0.25f);
                int i0 = v.Count;
                v.Add(root - side); c.Add(new Color32(255, 255, 255, 0));
                v.Add(root + side); c.Add(new Color32(255, 255, 255, 0));
                v.Add(root - side * 0.7f + Vector3.up * h * 0.55f + lean * 0.3f); c.Add(new Color32(255, 255, 255, 140));
                v.Add(root + side * 0.7f + Vector3.up * h * 0.55f + lean * 0.3f); c.Add(new Color32(255, 255, 255, 140));
                v.Add(root + Vector3.up * h + lean); c.Add(new Color32(255, 255, 255, 255));
                t.AddRange(new[] { i0, i0 + 2, i0 + 1, i0 + 1, i0 + 2, i0 + 3, i0 + 2, i0 + 4, i0 + 3 });
            }
            var m = new Mesh { name = "grass_cluster" };
            m.SetVertices(v);
            m.SetColors(c);
            m.SetTriangles(t, 0);
            var n = new Vector3[v.Count];
            for (int i = 0; i < n.Length; i++) n[i] = Vector3.up;
            m.normals = n;
            m.bounds = new Bounds(new Vector3(0, 0.6f, 0), new Vector3(2f, 1.4f, 2f));
            return m;
        }

        static long Key(int x, int z) => ((long)x << 32) ^ (uint)z;

        Matrix4x4[] CellInstances(int cx, int cz)
        {
            long k = Key(cx, cz);
            if (cache.TryGetValue(k, out var arr)) return arr;
            var list = new Matrix4x4[perCell];
            uint seed = (uint)(cx * 73856093) ^ (uint)(cz * 19349663);
            for (int i = 0; i < perCell; i++)
            {
                seed = seed * 1664525u + 1013904223u; float u = (seed >> 8) / 16777216f;
                seed = seed * 1664525u + 1013904223u; float w = (seed >> 8) / 16777216f;
                seed = seed * 1664525u + 1013904223u; float yaw = (seed >> 8) / 16777216f * 360f;
                seed = seed * 1664525u + 1013904223u; float s = 0.7f + (seed >> 8) / 16777216f * 0.7f;
                float x = (cx + u) * Cell, z = (cz + w) * Cell;
                float y = world.HeightAt(x, z);
                list[i] = Matrix4x4.TRS(new Vector3(x, y, z), Quaternion.Euler(0f, yaw, 0f), new Vector3(s, s * (0.8f + w * 0.5f), s));
            }
            if (cache.Count > 2500) cache.Clear();
            cache[k] = list;
            return list;
        }

        public void Draw(Vector3 cam)
        {
            if (mat == null) return;
            int cx = Mathf.FloorToInt(cam.x / Cell), cz = Mathf.FloorToInt(cam.z / Cell);
            if (cx != lastCx || cz != lastCz)
            {
                lastCx = cx; lastCz = cz;
                visible.Clear();
                int r = Mathf.CeilToInt(radius / Cell);
                float lim = (radius + Cell) * (radius + Cell);
                for (int z = cz - r; z <= cz + r; z++)
                    for (int x = cx - r; x <= cx + r; x++)
                    {
                        float dx = (x + 0.5f) * Cell - cam.x, dz = (z + 0.5f) * Cell - cam.z;
                        if (dx * dx + dz * dz > lim) continue;
                        visible.AddRange(CellInstances(x, z));
                    }
                if (buffer.Length < visible.Count) buffer = new Matrix4x4[visible.Count + 2048];
                visible.CopyTo(buffer);
                bounds = new Bounds(new Vector3(cam.x, world.HeightAt(cam.x, cam.z), cam.z), new Vector3(radius * 2f + 40f, 400f, radius * 2f + 40f));
            }
            var rp = new RenderParams(mat) { worldBounds = bounds, shadowCastingMode = ShadowCastingMode.Off, receiveShadows = true };
            for (int start = 0; start < visible.Count; start += 1023)
                Graphics.RenderMeshInstanced(rp, mesh, 0, buffer, Mathf.Min(1023, visible.Count - start), start);
        }
    }
}
