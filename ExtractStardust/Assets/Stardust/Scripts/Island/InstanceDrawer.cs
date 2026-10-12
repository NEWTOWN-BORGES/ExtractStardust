using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Stardust
{
    /// <summary>
    /// GPU-instanced static decoration (rocks, trees, grass, herds...): instances are grouped in square cells per
    /// model; each frame the cells inside the view range are submitted with Graphics.RenderMeshInstanced
    /// (Unity culls each submission against every camera with the cell bounds).
    /// </summary>
    public class InstanceDrawer
    {
        class Cell
        {
            public Vector3 center;
            public float radius;
            public Bounds bounds;
            public Matrix4x4[] m;
            public int count;      // drawn instances (density budget)
            // near/far split for the detailed mesh (rebuilt when the viewer moves)
            public Matrix4x4[] near, far;
            public int nNear, nFar;
            public Vector3 splitAt;
            public bool split;
        }

        class Batch
        {
            public string name;
            public Mesh mesh;
            public Material[] mats;
            public float range;
            public bool shadows;
            public float density = 1f;
            public bool decor;      // affected by the density budget
            public Mesh hd;         // detailed mesh drawn within hdRange
            public Material[] hdMats;
            public float hdRange;
            public readonly List<Cell> cells = new List<Cell>();
        }

        readonly List<Batch> batches = new List<Batch>();
        public float rangeScale = 1f;
        public float decorDensity = 1f;
        public bool allowShadows = true;
        public float hdScale = 1f;   // 0: never use the detailed meshes
        public int drawCalls, instancesDrawn;

        /// <summary>Adds a model with its instance transforms, grouped in cells of `cellSize` metres.</summary>
        public void Add(string name, Mesh mesh, Material[] mats, List<Matrix4x4> xs, float cellSize, float range, bool shadows, bool decor = false)
        {
            if (mesh == null || xs == null || xs.Count == 0) return;
            var b = new Batch { name = name, mesh = mesh, mats = mats, range = range, shadows = shadows, decor = decor };
            var groups = new Dictionary<long, List<Matrix4x4>>();
            foreach (var x in xs)
            {
                long key = ((long)Mathf.FloorToInt(x.m03 / cellSize) << 32) ^ (uint)Mathf.FloorToInt(x.m23 / cellSize);
                if (!groups.TryGetValue(key, out var l)) groups[key] = l = new List<Matrix4x4>();
                l.Add(x);
            }
            var mb = mesh.bounds;
            float meshRadius = mb.extents.magnitude + mb.center.magnitude;
            foreach (var g in groups.Values)
            {
                // shuffle so a reduced density budget removes instances evenly
                var rng = new System.Random(g.Count * 7919 + name.GetHashCode());
                for (int i = g.Count - 1; i > 0; i--) { int j = rng.Next(i + 1); (g[i], g[j]) = (g[j], g[i]); }
                var c = new Cell { m = g.ToArray(), count = g.Count };
                Vector3 mn = Vector3.one * float.MaxValue, mx = Vector3.one * float.MinValue;
                foreach (var x in g)
                {
                    Vector3 p = new Vector3(x.m03, x.m13, x.m23);
                    float s = new Vector3(x.m00, x.m10, x.m20).magnitude;
                    float r = meshRadius * s;
                    mn = Vector3.Min(mn, p - Vector3.one * r);
                    mx = Vector3.Max(mx, p + Vector3.one * r);
                }
                c.bounds = new Bounds((mn + mx) * 0.5f, mx - mn);
                c.center = c.bounds.center;
                c.radius = new Vector2(c.bounds.extents.x, c.bounds.extents.z).magnitude;
                b.cells.Add(c);
            }
            batches.Add(b);
            ApplyDensity(b);
        }

        /// <summary>Detailed mesh for the instances of `name` closer than `range` metres.</summary>
        public void SetDetail(string name, Mesh hd, Material[] mats, float range)
        {
            foreach (var b in batches)
                if (b.name == name && hd != null) { b.hd = hd; b.hdMats = mats; b.hdRange = range; }
        }

        void ApplyDensity(Batch b)
        {
            float d = b.decor ? decorDensity : 1f;
            foreach (var c in b.cells) { c.count = Mathf.Max(d > 0f ? 1 : 0, Mathf.RoundToInt(c.m.Length * d)); c.split = false; }
        }

        public void SetBudget(float range, float density, bool shadows)
        {
            rangeScale = range;
            decorDensity = density;
            allowShadows = shadows;
            foreach (var b in batches) ApplyDensity(b);
        }

        /// <summary>Submits every cell within range of the viewer. Call once per frame (from Update/LateUpdate).</summary>
        public void Draw(Vector3 viewer)
        {
            drawCalls = 0;
            instancesDrawn = 0;
            foreach (var b in batches)
            {
                float range = b.range * rangeScale;
                var shadow = b.shadows && allowShadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
                foreach (var c in b.cells)
                {
                    if (c.count <= 0) continue;
                    float dx = c.center.x - viewer.x, dz = c.center.z - viewer.z;
                    float lim = range + c.radius;
                    if (dx * dx + dz * dz > lim * lim) continue;
                    float hdR = b.hdRange * hdScale;
                    float hdLim = hdR + c.radius;
                    if (b.hd != null && hdR > 0f && dx * dx + dz * dz < hdLim * hdLim)
                    {
                        if (!c.split || (c.splitAt - viewer).sqrMagnitude > 20f * 20f) Split(c, viewer, hdR);
                        Submit(b.mesh, b.mats, c, c.far, c.nFar, shadow);
                        Submit(b.hd, b.hdMats, c, c.near, c.nNear, shadow);
                    }
                    else
                    {
                        c.split = false;
                        Submit(b.mesh, b.mats, c, c.m, c.count, shadow);
                    }
                    instancesDrawn += c.count;
                }
            }
        }

        static void Split(Cell c, Vector3 viewer, float range)
        {
            if (c.near == null) { c.near = new Matrix4x4[c.m.Length]; c.far = new Matrix4x4[c.m.Length]; }
            c.nNear = c.nFar = 0;
            float r2 = range * range;
            for (int i = 0; i < c.count; i++)
            {
                var x = c.m[i];
                float dx = x.m03 - viewer.x, dz = x.m23 - viewer.z;
                if (dx * dx + dz * dz < r2) c.near[c.nNear++] = x; else c.far[c.nFar++] = x;
            }
            c.splitAt = viewer;
            c.split = true;
        }

        void Submit(Mesh mesh, Material[] mats, Cell c, Matrix4x4[] xs, int count, ShadowCastingMode shadow)
        {
            if (count <= 0) return;
            for (int s = 0; s < mats.Length && s < mesh.subMeshCount; s++)
            {
                var rp = new RenderParams(mats[s])
                {
                    worldBounds = c.bounds,
                    shadowCastingMode = shadow,
                    receiveShadows = true,
                };
                for (int start = 0; start < count; start += 1023)
                {
                    Graphics.RenderMeshInstanced(rp, mesh, s, xs, Mathf.Min(1023, count - start), start);
                    drawCalls++;
                }
            }
        }

        public int InstanceCount
        {
            get
            {
                int n = 0;
                foreach (var b in batches) foreach (var c in b.cells) n += c.m.Length;
                return n;
            }
        }
    }
}
