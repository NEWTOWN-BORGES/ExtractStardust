using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Stardust
{
    /// <summary>
    /// The 24 km island (port of RACESTARS terrain.gd + map.gd): terrain tiles, ocean and lakes, tunnels, bridges,
    /// aqueduct, stone roofs, colossi, instanced props/vegetation/ground cover/herds, route posts, boost pads and
    /// banners. Collisions: terrain + set pieces always on; prop and trunk colliders are streamed in 512 m cells
    /// around the ships that use physics.
    /// </summary>
    public class IslandWorld : MonoBehaviour
    {
        public static IslandWorld I;

        // physics layers (see the class comment in Hovercraft)
        public const int LayerGround = 8, LayerSolid = 9, LayerRide = 10, LayerWater = 11;
        public const int SolidMask = (1 << LayerGround) | (1 << LayerSolid);
        public const int ProbeMask = SolidMask | (1 << LayerRide) | (1 << LayerWater);
        public const int ViewBlockMask = SolidMask;

        public const float HMin = -80f, TileSize = 4096f;
        public const int Tiles = 6;
        public const float ColliderCell = 512f;

        public WorldJson data;
        public ModelLibrary lib;
        public int quality = 2;
        public float Half => data.size * 0.5f;
        public readonly List<Transform> viewers = new List<Transform>();
        public readonly List<Func<Vector3>> physicsFoci = new List<Func<Vector3>>();
        public readonly InstanceDrawer drawer = new InstanceDrawer();
        public GrassField grass;
        public TitanCircuit titan;
        public Terrain[,] terrains;
        public Material terrainMat, oceanMat, lakeMat, plainMat, glowMat;
        Transform root, staticRoot, colliderRoot;
        public bool ready;

        // ------------------------------------------------------------------ collision rules (map.gd)
        enum ShapeKind { None, Convex, Trimesh, Capsule }
        struct ShapeRule { public ShapeKind kind; public float r, h; }

        static readonly Dictionary<string, ShapeRule> Collide = new Dictionary<string, ShapeRule>();
        static readonly HashSet<string> RideOver = new HashSet<string> { "boulder_a", "boulder_b", "crystals_cyan", "crystals_mag", "pebbles" };
        static readonly HashSet<string> RockProps = new HashSet<string> { "rock_spire_a", "rock_spire_b", "rock_spire_c", "boulder_a", "boulder_b", "mesa", "arch", "arch_giant", "arch_twin", "rock_ring", "rock_fin", "butte", "canyon_roof" };
        static readonly Dictionary<string, float> VisRange = new Dictionary<string, float>
        {
            {"butte", 4200f}, {"mesa", 3400f}, {"arch_giant", 3400f}, {"arch_twin", 2800f}, {"rock_ring", 2600f}, {"rock_fin", 3000f},
            {"ruin_tower", 4200f}, {"arch", 2400f}, {"rock_spire_c", 2600f}, {"rock_spire_a", 2200f}, {"tower_pod", 1800f},
            {"tree_giant", 2600f}, {"crystals_cyan_big", 1800f}, {"crystals_mag_big", 1800f}, {"bush", 700f}, {"cactus", 1000f}, {"dead_tree", 1000f},
        };
        static readonly Dictionary<string, float> VegRange = new Dictionary<string, float>
        {
            {"pine", 1100f}, {"tree_acacia", 1100f}, {"tree_acacia_b", 1000f}, {"tree_giant", 2600f}, {"palm", 1000f}, {"cactus", 800f},
            {"bush", 420f}, {"tree_mushroom", 1600f}, {"dead_tree", 800f}, {"fern", 320f}, {"boulder_a", 700f}, {"crystals_cyan", 900f}, {"crystals_mag", 900f},
        };
        public static readonly Color[] LevelColors =
        {
            new Color(0.32f, 0.95f, 1f), new Color(1f, 0.54f, 0.24f), new Color(1f, 0.82f, 0.24f), new Color(1f, 1f, 1f)
        };

        static IslandWorld()
        {
            void C(ShapeKind k, params string[] names) { foreach (var n in names) Collide[n] = new ShapeRule { kind = k }; }
            void Cyl(string n, float r, float h) { Collide[n] = new ShapeRule { kind = ShapeKind.Capsule, r = r, h = h }; }
            C(ShapeKind.Convex, "rock_spire_a", "rock_spire_b", "rock_spire_c", "boulder_a", "boulder_b", "rock_fin", "butte", "tower_pod",
                "crystals_cyan_big", "crystals_mag_big", "piramide", "obelisco");
            C(ShapeKind.Trimesh, "mesa", "arch", "arch_giant", "arch_twin", "rock_ring", "ruin_wall", "colosso_estatua", "colosso_costelas", "colosso_nave");
            Cyl("pillar", 1.3f, 13f); Cyl("tree_acacia", 0.6f, 6f); Cyl("tree_acacia_b", 0.5f, 5f); Cyl("tree_mushroom", 1.1f, 12f);
            Cyl("crystals_cyan", 2.2f, 4f); Cyl("crystals_mag", 2.2f, 4f); Cyl("ruin_column", 1.6f, 12f); Cyl("ruin_tower", 9.5f, 70f);
            Cyl("cactus", 0.8f, 7f); Cyl("palm", 0.6f, 7f); Cyl("pine", 0.7f, 8f); Cyl("tree_giant", 3.8f, 30f); Cyl("dead_tree", 0.5f, 8f);
        }

        // ------------------------------------------------------------------ streamed colliders
        struct ColSpec
        {
            public string name;
            public ShapeKind kind;
            public Mesh mesh;
            public Vector3 pos;
            public Quaternion rot;
            public float scale, r, h;
            public int layer;
        }

        class ColCell
        {
            public readonly List<ColSpec> specs = new List<ColSpec>();
            public GameObject go;
            public bool active;
            public Vector2 min;
        }

        readonly Dictionary<long, ColCell> colCells = new Dictionary<long, ColCell>();
        readonly List<ColCell> colCellList = new List<ColCell>();
        readonly Queue<ColCell> buildQueue = new Queue<ColCell>();
        float colTimer;
        public float colliderRadius = 420f;
        public int activeColliderCells;

        static long CellKey(int x, int z) => ((long)x << 32) ^ (uint)z;

        void AddCollider(ColSpec s)
        {
            int cx = Mathf.FloorToInt(s.pos.x / ColliderCell), cz = Mathf.FloorToInt(s.pos.z / ColliderCell);
            long k = CellKey(cx, cz);
            if (!colCells.TryGetValue(k, out var c))
            {
                c = new ColCell { min = new Vector2(cx * ColliderCell, cz * ColliderCell) };
                colCells[k] = c;
                colCellList.Add(c);
            }
            c.specs.Add(s);
        }

        // ------------------------------------------------------------------ queries / bookkeeping
        public struct CaveBox { public Vector3 origin, fwd; public float len, halfW, top; }
        public readonly List<CaveBox> caves = new List<CaveBox>();
        public struct Spawn { public Vector3 pos; public Vector3 dir; public int level; }
        public readonly List<Spawn> spawns = new List<Spawn>();
        public struct Pad { public Vector3 pos; public Quaternion rot; }
        public readonly List<Pad> pads = new List<Pad>();

        // ------------------------------------------------------------------ build

        public static IslandWorld Create(Transform parent, int quality)
        {
            var go = new GameObject("Island");
            go.transform.SetParent(parent, false);
            var w = go.AddComponent<IslandWorld>();
            w.quality = quality;
            I = w;
            return w;
        }

        Material LoadMat(string name)
        {
            var m = Resources.Load<Material>(IslandData.Root + "Materials/" + name);
            if (m == null) Debug.LogError("[Island] missing material " + name);
            return m;
        }

        public IEnumerator Build(Action<float, string> progress)
        {
            data = IslandData.Load();
            lib = ModelLibrary.I;
            if (data == null || lib == null) { Debug.LogError("[Island] world data missing"); yield break; }
            // the suspended "Cidadela Titã" circuit (RACESTARS) joins the island's events
            var evs = new System.Collections.Generic.List<WEvent>(data.events ?? new WEvent[0]);
            if (!evs.Exists(e => e.id == "titan")) evs.Add(TitanCircuit.EventData());
            data.events = evs.ToArray();
            root = transform;
            staticRoot = new GameObject("Static").transform;
            staticRoot.SetParent(root, false);
            colliderRoot = new GameObject("Colliders").transform;
            colliderRoot.SetParent(root, false);
            terrainMat = new Material(LoadMat("Terrain"));
            terrainMat.SetFloat("_Quality", quality >= 1 ? 1f : 0f);
            oceanMat = new Material(LoadMat("Ocean"));
            if (quality >= 2) oceanMat.EnableKeyword("_SD_DEPTH_FOAM"); else oceanMat.DisableKeyword("_SD_DEPTH_FOAM");
            oceanMat.SetFloat("_Quality", quality >= 1 ? 1f : 0f);
            lakeMat = new Material(LoadMat("Lake"));
            if (quality >= 2) lakeMat.EnableKeyword("_SD_DEPTH_FOAM"); else lakeMat.DisableKeyword("_SD_DEPTH_FOAM");
            plainMat = new Material(lib.materials[(int)MatClass.Plain]) { name = "Generated" };
            plainMat.SetFloat("_Cull", (float)CullMode.Off);
            plainMat.enableInstancing = true;
            glowMat = Resources.Load<Material>("Stardust/Additive");

            progress?.Invoke(0.05f, "Terreno");
            yield return null;
            BuildTerrain();
            progress?.Invoke(0.2f, "Água");
            yield return null;
            BuildOcean();
            BuildLakes();
            progress?.Invoke(0.3f, "Túneis e pontes");
            yield return null;
            BuildSetPieces();
            BuildColossi();
            progress?.Invoke(0.45f, "Rochas e ruínas");
            yield return null;
            BuildProps();
            progress?.Invoke(0.6f, "Floresta");
            yield return null;
            BuildVegetation();
            progress?.Invoke(0.75f, "Relva e flores");
            yield return null;
            BuildCover();
            BuildIslands();
            BuildHerds();
            BuildBanners();
            BuildPads();
            BuildRoutePosts();
            progress?.Invoke(0.9f, "Colisões");
            yield return null;
            BakeColliderMeshes();
            titan = TitanCircuit.Create(transform, this);
            grass = new GrassField(this, quality);
            ApplyQuality();
            ready = true;
            Debug.Log($"[Island] built: {drawer.InstanceCount} instances, {colCellList.Count} collider cells, {caves.Count} caves, {spawns.Count} spawn points");
        }

        public void ApplyQuality()
        {
            // range scale, ground cover density, instanced shadows
            if (quality <= 0) drawer.SetBudget(0.6f, 0.35f, false);
            else if (quality == 1) drawer.SetBudget(0.8f, 0.7f, true);
            else drawer.SetBudget(1f, 1f, true);
            drawer.hdScale = quality <= 0 ? 0f : quality == 1 ? 0.6f : 1f;
            if (terrains != null)
                foreach (var t in terrains)
                {
                    t.heightmapPixelError = quality <= 0 ? 9f : quality == 1 ? 6f : 4f;
                    t.shadowCastingMode = quality >= 2 ? ShadowCastingMode.On : ShadowCastingMode.Off;
                }
        }

        void BuildTerrain()
        {
            terrains = new Terrain[Tiles, Tiles];
            var tr = new GameObject("Terrain").transform;
            tr.SetParent(root, false);
            for (int j = 0; j < Tiles; j++)
                for (int i = 0; i < Tiles; i++)
                {
                    var td = Resources.Load<TerrainData>($"{IslandData.Root}Terrain/t_{i}_{j}");
                    if (td == null) { Debug.LogError($"[Island] missing terrain t_{i}_{j}"); continue; }
                    var go = Terrain.CreateTerrainGameObject(td);
                    go.name = $"Terrain_{i}_{j}";
                    go.layer = LayerGround;
                    go.transform.SetParent(tr, false);
                    go.transform.position = new Vector3(-Half + i * TileSize, HMin, -Half + j * TileSize);
                    var t = go.GetComponent<Terrain>();
                    t.materialTemplate = terrainMat;
                    t.drawInstanced = false;
                    t.drawTreesAndFoliage = false;
                    t.basemapDistance = 100000f;
                    t.treeDistance = 0f;
                    t.detailObjectDistance = 0f;
                    t.groupingID = 7;
                    t.allowAutoConnect = true;
                    t.reflectionProbeUsage = ReflectionProbeUsage.BlendProbesAndSkybox;
                    terrains[i, j] = t;
                }
            Terrain.SetConnectivityDirty();
        }

        /// <summary>Terrain height (metres) at a world point, interpolated like the heightfield collider.</summary>
        public float HeightAt(float x, float z)
        {
            int i = Mathf.Clamp(Mathf.FloorToInt((x + Half) / TileSize), 0, Tiles - 1);
            int j = Mathf.Clamp(Mathf.FloorToInt((z + Half) / TileSize), 0, Tiles - 1);
            var t = terrains[i, j];
            if (t == null) return 0f;
            return t.SampleHeight(new Vector3(x, 0f, z)) + HMin;
        }

        public Vector3 GroundNormal(float x, float z)
        {
            int i = Mathf.Clamp(Mathf.FloorToInt((x + Half) / TileSize), 0, Tiles - 1);
            int j = Mathf.Clamp(Mathf.FloorToInt((z + Half) / TileSize), 0, Tiles - 1);
            var t = terrains[i, j];
            if (t == null) return Vector3.up;
            var lp = new Vector2((x - t.transform.position.x) / TileSize, (z - t.transform.position.z) / TileSize);
            return t.terrainData.GetInterpolatedNormal(lp.x, lp.y);
        }

        GameObject Child(string name, Transform parent, int layer = 0)
        {
            var go = new GameObject(name);
            go.layer = layer;
            go.transform.SetParent(parent, false);
            return go;
        }

        static Mesh PlaneGrid(float sx, float sz, int nx, int nz)
        {
            var v = new List<Vector3>();
            var t = new List<int>();
            for (int j = 0; j <= nz; j++)
                for (int i = 0; i <= nx; i++)
                    v.Add(new Vector3(-sx * 0.5f + sx * i / nx, 0f, -sz * 0.5f + sz * j / nz));
            for (int j = 0; j < nz; j++)
                for (int i = 0; i < nx; i++)
                {
                    int a = j * (nx + 1) + i;
                    t.Add(a); t.Add(a + nx + 1); t.Add(a + 1);
                    t.Add(a + 1); t.Add(a + nx + 1); t.Add(a + nx + 2);
                }
            var m = new Mesh { name = "WaterGrid" };
            m.SetVertices(v);
            m.SetTriangles(t, 0);
            var n = new Vector3[v.Count];
            for (int i = 0; i < n.Length; i++) n[i] = Vector3.up;
            m.normals = n;
            m.RecalculateBounds();
            return m;
        }

        void BuildOcean()
        {
            var go = Child("Ocean", root);
            go.transform.position = new Vector3(0f, data.oceanY, 0f);
            go.AddComponent<MeshFilter>().sharedMesh = PlaneGrid(data.oceanSize, data.oceanSize, 24, 24);
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = oceanMat;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            // support surfaces (only the suspension probe sees the water layer)
            var sup = Child("OceanSupport", root, LayerWater);
            var r = data.oceanRects;
            for (int i = 0; i + 3 < r.Length; i += 4)
            {
                var bc = sup.AddComponent<BoxCollider>();
                bc.center = new Vector3(r[i], data.oceanY - 0.05f, r[i + 1]);
                bc.size = new Vector3(r[i + 2], 0.1f, r[i + 3]);
            }
        }

        void BuildLakes()
        {
            var parent = Child("Lakes", root).transform;
            foreach (var w in data.waters)
            {
                var go = Child("Lake", parent);
                go.transform.SetPositionAndRotation(new Vector3(w.c[0], w.y, w.c[1]), Quaternion.Euler(0f, w.yaw, 0f));
                int nx = Mathf.Clamp((int)(w.sx * 2f / 120f), 2, 24), nz = Mathf.Clamp((int)(w.sz * 2f / 120f), 2, 24);
                go.AddComponent<MeshFilter>().sharedMesh = PlaneGrid(w.sx * 2f, w.sz * 2f, nx, nz);
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = lakeMat;
                mr.shadowCastingMode = ShadowCastingMode.Off;
                var sup = Child("Support", go.transform, LayerWater);
                var bc = sup.AddComponent<BoxCollider>();
                bc.center = new Vector3(0f, -0.05f, 0f);
                bc.size = new Vector3(w.sx * 2f, 0.1f, w.sz * 2f);
            }
        }

        /// <summary>A static model with renderer and exact collider (set pieces, colossi, portals).</summary>
        GameObject PlaceStatic(string model, Vector3 pos, Quaternion rot, float scale, Transform parent, bool twoSidedShadows, ShapeKind shape = ShapeKind.Trimesh, int layer = LayerSolid)
        {
            var e = lib.Get(model);
            if (e == null) { Debug.LogWarning("[Island] missing model " + model); return null; }
            var go = Child(model, parent, layer);
            go.transform.SetPositionAndRotation(pos, rot);
            go.transform.localScale = Vector3.one * scale;
            go.AddComponent<MeshFilter>().sharedMesh = e.mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterials = lib.MaterialsFor(e);
            mr.shadowCastingMode = twoSidedShadows ? ShadowCastingMode.TwoSided : ShadowCastingMode.On;
            if (shape == ShapeKind.Trimesh || shape == ShapeKind.Convex)
            {
                var mc = go.AddComponent<MeshCollider>();
                mc.convex = shape == ShapeKind.Convex;
                mc.sharedMesh = e.mesh;
            }
            return go;
        }

        void AddCave(Vector3 origin, Vector3 fwd, float len, float halfW, float top)
        {
            caves.Add(new CaveBox { origin = origin, fwd = fwd, len = len, halfW = halfW, top = top });
        }

        void BuildSetPieces()
        {
            var parent = Child("SetPieces", staticRoot).transform;
            foreach (var t in data.tunnels)
            {
                var rot = Quaternion.Euler(0f, t.yaw, 0f);
                PlaceStatic(t.name, t.Pos, rot, 1f, parent, true);
                AddCave(t.Pos, rot * Vector3.forward, t.len, (t.thw > 0 ? t.thw : 18f) + 1f, t.Pos.y + 16f);
            }
            foreach (var b in data.bridges)
                PlaceStatic(b.name, b.Pos, Quaternion.Euler(0f, b.yaw, 0f), 1f, parent, false);
            foreach (var a in data.aqueducts)
            {
                var rot = Quaternion.Euler(0f, a.yaw, 0f);
                var fwd = rot * Vector3.forward;
                var missing = new HashSet<int>(a.missing ?? new int[0]);
                for (int i = 0; i < a.n; i++)
                {
                    if (missing.Contains(i)) continue;
                    PlaceStatic("aqueduct_seg", a.Pos + fwd * (i * a.seg), rot, 1f, parent, false);
                }
            }
            foreach (var r in data.roofs)
            {
                var rot = Quaternion.Euler(0f, r.yaw, 0f);
                var fwd = rot * Vector3.forward;
                var go = PlaceStatic("canyon_roof", r.Pos - fwd * 90f, rot, 1f, parent, true);
                if (go != null)
                {
                    var mr = go.GetComponent<MeshRenderer>();
                    var block = new MaterialPropertyBlock();
                    block.SetColor("_Tint", new Color(0.75f, 0.75f, 0.75f));
                    mr.SetPropertyBlock(block);
                }
                AddCave(r.Pos - fwd * 90f, fwd, 180f, 40f, r.Pos.y + 24f);
            }
        }

        void BuildColossi()
        {
            var parent = Child("Colossi", staticRoot).transform;
            foreach (var c in data.colossi)
            {
                Collide.TryGetValue(c.name, out var rule);
                var kind = c.name == "float_island" ? ShapeKind.None : rule.kind;
                var go = PlaceStatic(c.name, c.Pos, c.Rot, c.sc, parent, false, kind == ShapeKind.Capsule ? ShapeKind.None : kind);
                if (go == null) continue;
                if (kind == ShapeKind.Capsule)
                {
                    var cc = go.AddComponent<CapsuleCollider>();
                    cc.radius = rule.r;
                    cc.height = Mathf.Max(rule.h, rule.r * 2f);
                    cc.center = new Vector3(0f, rule.h * 0.5f, 0f);
                }
                var mr = go.GetComponent<MeshRenderer>();
                mr.shadowCastingMode = quality >= 1 ? ShadowCastingMode.On : ShadowCastingMode.Off;
            }
        }

        static Matrix4x4 TRS(Vector3 p, float yawDeg, float s) => Matrix4x4.TRS(p, Quaternion.Euler(0f, yawDeg, 0f), Vector3.one * s);

        void BuildProps()
        {
            var byName = new Dictionary<string, List<Matrix4x4>>();
            foreach (var p in data.props)
            {
                if (!byName.TryGetValue(p.name, out var l)) byName[p.name] = l = new List<Matrix4x4>();
                l.Add(TRS(p.Pos, p.yaw, p.sc));
                if (Collide.TryGetValue(p.name, out var rule))
                {
                    var e = lib.Get(p.name);
                    AddCollider(new ColSpec
                    {
                        name = p.name, kind = rule.kind, mesh = e?.mesh, pos = p.Pos, rot = p.Rot, scale = p.sc, r = rule.r, h = rule.h,
                        layer = RideOver.Contains(p.name) ? LayerRide : LayerSolid,
                    });
                }
            }
            foreach (var kv in byName)
            {
                var e = lib.Get(kv.Key);
                if (e == null) { Debug.LogWarning("[Island] missing prop model " + kv.Key); continue; }
                VisRange.TryGetValue(kv.Key, out float range);
                if (range <= 0f) range = 1500f;
                bool decor = (kv.Key == "fern" || kv.Key == "bush" || kv.Key == "pebbles") && !Collide.ContainsKey(kv.Key);
                drawer.Add(kv.Key, e.mesh, lib.MaterialsFor(e), kv.Value, 1024f, range, true, decor);
            }
        }

        void BuildVegetation()
        {
            var veg = IslandData.LoadVeg();
            var types = data.vegTypes;
            var lists = new List<Matrix4x4>[types.Length];
            for (int i = 0; i < lists.Length; i++) lists[i] = new List<Matrix4x4>();
            foreach (var v in veg)
            {
                if (v.type >= types.Length) continue;
                string name = types[v.type];
                lists[v.type].Add(TRS(v.pos, v.yaw, v.scale));
                // trunks are solid; bushes, ferns, boulders and crystals are not (they are ridden over)
                if (Collide.TryGetValue(name, out var rule) && rule.kind == ShapeKind.Capsule && !RideOver.Contains(name))
                    AddCollider(new ColSpec { name = name, kind = ShapeKind.Capsule, pos = v.pos, rot = Quaternion.Euler(0f, v.yaw, 0f), scale = v.scale, r = rule.r, h = rule.h, layer = LayerSolid });
            }
            for (int t = 0; t < types.Length; t++)
            {
                var e = lib.Get(types[t]);
                if (e == null) continue;
                VegRange.TryGetValue(types[t], out float range);
                if (range <= 0f) range = 900f;
                bool small = types[t] == "fern" || types[t] == "bush";
                bool decor = small || RideOver.Contains(types[t]);
                drawer.Add(types[t], e.mesh, lib.MaterialsFor(e), lists[t], 512f, range, !small, decor);
                // detailed model near the camera (Blender "<name>_hd")
                var hd = lib.Get(types[t] + "_hd");
                if (hd != null) drawer.SetDetail(types[t], hd.mesh, lib.MaterialsFor(hd), types[t] == "tree_giant" ? 320f : 200f);
            }
        }

        void BuildCover()
        {
            void Cover(WPlaced[] rows, string model, float range)
            {
                var e = lib.Get(model);
                if (e == null || rows == null) return;
                var xs = new List<Matrix4x4>(rows.Length);
                foreach (var g in rows) xs.Add(TRS(g.Pos, g.yaw, g.sc));
                drawer.Add(model, e.mesh, lib.MaterialsFor(e), xs, 256f, range, false, true);
            }
            Cover(data.grass, "grass_tuft", 300f);
            Cover(data.flowers, "flowers", 260f);
            Cover(data.ferns, "fern", 280f);
        }

        void BuildIslands()
        {
            var e = lib.Get("float_island");
            if (e == null) return;
            var xs = new List<Matrix4x4>();
            foreach (var i in data.islands) xs.Add(TRS(i.Pos, i.yaw, i.sc));
            drawer.Add("float_island", e.mesh, lib.MaterialsFor(e), xs, 4096f, 6000f, true);
        }

        void BuildHerds()
        {
            var by = new Dictionary<string, List<Matrix4x4>>();
            foreach (var h in data.herds)
            {
                if (!by.TryGetValue(h.name, out var l)) by[h.name] = l = new List<Matrix4x4>();
                l.Add(TRS(h.Pos, h.yaw, h.sc));
            }
            foreach (var kv in by)
            {
                var e = lib.Get(kv.Key);
                if (e != null) drawer.Add(kv.Key, e.mesh, lib.MaterialsFor(e), kv.Value, 1024f, 1300f, true);
            }
        }

        // ------------------------------------------------------------------ generated decoration

        /// <summary>Generated mesh with per-vertex roughness/emission (alpha 0 in MeshBuilder colours = emissive).</summary>
        public static Mesh Finish(MeshBuilder mb, string name, float rough, float emission)
        {
            var m = mb.ToMesh(name);
            var surf = new Vector2[mb.V.Count];
            for (int i = 0; i < surf.Length; i++) surf[i] = new Vector2(rough, mb.C[i].a < 128 ? emission : 0f);
            m.uv2 = surf;
            var cols = new Color32[mb.C.Count];
            for (int i = 0; i < cols.Length; i++) { var c = mb.C[i]; c.a = 255; cols[i] = c; }
            m.colors32 = cols;
            return m;
        }

        Mesh BannerMesh(float span)
        {
            var mb = new MeshBuilder();
            var colors = new[] { new Color(0.9f, 0.28f, 0.23f), new Color(1f, 0.82f, 0.24f), new Color(0.25f, 0.71f, 0.9f), new Color(0.96f, 0.93f, 0.89f), new Color(0.48f, 0.76f, 0.35f) };
            float top = 22f;
            int n = Mathf.Max(1, (int)(span / 4f));
            for (int k = 0; k < n; k++)
            {
                float x0 = -span * 0.5f + k * span / n, x1 = x0 + span / n * 0.8f;
                float s0 = top - 5f * (1f - Mathf.Pow(2f * (x0 / span), 2f)), s1 = top - 5f * (1f - Mathf.Pow(2f * (x1 / span), 2f));
                var c = MeshBuilder.Col(colors[k % colors.Length]);
                mb.Tri(new Vector3(x0, s0, 0), new Vector3(x1, s1, 0), new Vector3((x0 + x1) * 0.5f, (s0 + s1) * 0.5f - 2.6f, 0), c);
            }
            var pole = MeshBuilder.Col(new Color(0.35f, 0.25f, 0.22f));
            foreach (float sg in new[] { -1f, 1f })
                mb.Cylinder(Matrix4x4.TRS(new Vector3(sg * span * 0.5f, 0f, 0f), Quaternion.identity, new Vector3(0.6f, top + 1f, 0.6f)), 6, 0.7f, pole, pole);
            return Finish(mb, "banner_" + span, 0.8f, 0f);
        }

        void BuildBanners()
        {
            var by = new Dictionary<float, List<Matrix4x4>>();
            foreach (var b in data.banners)
            {
                float span = Mathf.Round(b.sc / 10f) * 10f;
                if (!by.TryGetValue(span, out var l)) by[span] = l = new List<Matrix4x4>();
                l.Add(Matrix4x4.TRS(b.Pos + Vector3.down * 0.5f, b.Rot, Vector3.one));
            }
            foreach (var kv in by) drawer.Add("banner", BannerMesh(kv.Key), new[] { plainMat }, kv.Value, 1024f, 1600f, true);
        }

        void BuildPads()
        {
            var mb = new MeshBuilder();
            var plate = MeshBuilder.Col(new Color(0.11f, 0.16f, 0.23f));
            mb.Quad(new Vector3(-7, 0.15f, -9), new Vector3(-7, 0.15f, 9), new Vector3(7, 0.15f, 9), new Vector3(7, 0.15f, -9), plate);
            for (int k = 0; k < 3; k++)   // three chevrons pointing forward (+Z)
            {
                float z0 = -5f + k * 6f;
                var c = MeshBuilder.Glow(k != 1 ? new Color(0.5f, 0.96f, 1f) : new Color(1f, 0.83f, 0.43f));
                mb.Quad(new Vector3(-6, 0.3f, z0), new Vector3(0, 0.3f, z0 + 4.5f), new Vector3(0, 0.3f, z0 + 2f), new Vector3(-6, 0.3f, z0 - 2.5f), c);
                mb.Quad(new Vector3(6, 0.3f, z0), new Vector3(6, 0.3f, z0 - 2.5f), new Vector3(0, 0.3f, z0 + 2f), new Vector3(0, 0.3f, z0 + 4.5f), c);
            }
            var mesh = Finish(mb, "pad", 0.35f, 2.2f);
            var xs = new List<Matrix4x4>();
            foreach (var p in data.pads)
            {
                var pos = p.Pos + Vector3.up * 0.1f;
                xs.Add(Matrix4x4.TRS(pos, p.Rot, Vector3.one));
                pads.Add(new Pad { pos = pos, rot = p.Rot });
            }
            drawer.Add("pad", mesh, new[] { plainMat }, xs, 1024f, 1200f, false);
        }

        /// <summary>Pad under a point (box 16 x 8 x 20 above the plate), or -1.</summary>
        public int PadAt(Vector3 p)
        {
            for (int i = 0; i < pads.Count; i++)
            {
                var l = Quaternion.Inverse(pads[i].rot) * (p - pads[i].pos);
                if (Mathf.Abs(l.x) < 8f && Mathf.Abs(l.y - 3f) < 4f && Mathf.Abs(l.z) < 10f) return i;
            }
            return -1;
        }

        void BuildRoutePosts()
        {
            var by = new List<Matrix4x4>[4];
            for (int i = 0; i < 4; i++) by[i] = new List<Matrix4x4>();
            foreach (var sec in data.sections)
                foreach (var v in sec.variants)
                {
                    var r = v.Points;
                    int lvl = Mathf.Clamp(v.level, 0, 3);
                    for (int k = 2; k < r.Length - 1; k += 3)
                    {
                        var d = r[k + 1] - r[k];
                        d.y = 0f;
                        spawns.Add(new Spawn { pos = r[k], dir = d.normalized, level = lvl });
                    }
                    float off = v.hw + 4f;
                    for (int k = 8; k < r.Length - 8; k += 15)
                    {
                        var d = r[k + 1] - r[k];
                        d.y = 0f;
                        d.Normalize();
                        var side = new Vector3(d.z, 0f, -d.x);
                        foreach (float sg in new[] { -1f, 1f })
                        {
                            float o = lvl == 0 ? Mathf.Min(off, 15f) : off;
                            var p = r[k] + side * sg * o;
                            p.y = (lvl == 0 || lvl == 2 || lvl == 3) ? r[k].y : HeightAt(p.x, p.z);
                            by[lvl].Add(Matrix4x4.TRS(p + Vector3.up * 2f, Quaternion.identity, Vector3.one));
                        }
                    }
                }
            for (int lvl = 0; lvl < 4; lvl++)
            {
                var mb = new MeshBuilder();
                var body = MeshBuilder.Col(new Color(0.18f, 0.18f, 0.2f));
                var glow = MeshBuilder.Glow(LevelColors[lvl]);
                mb.Cylinder(Matrix4x4.TRS(new Vector3(0, -2.5f, 0), Quaternion.identity, new Vector3(1f, 3.6f, 1f)), 6, 0.85f, body, body);
                mb.Cylinder(Matrix4x4.TRS(new Vector3(0, 1.1f, 0), Quaternion.identity, new Vector3(0.85f, 1.4f, 0.85f)), 6, 1f, glow, glow);
                var mesh = Finish(mb, "post_" + lvl, 0.5f, lvl == 0 ? 2.4f : 1.6f);
                drawer.Add("post", mesh, new[] { plainMat }, by[lvl], 1024f, 900f, false);
            }
        }

        // ------------------------------------------------------------------ colliders

        void BakeColliderMeshes()
        {
            var done = new HashSet<(int, bool)>();
            foreach (var c in colCellList)
                foreach (var s in c.specs)
                {
                    if (s.mesh == null || (s.kind != ShapeKind.Convex && s.kind != ShapeKind.Trimesh)) continue;
                    var key = (s.mesh.GetInstanceID(), s.kind == ShapeKind.Convex);
                    if (done.Add(key)) Physics.BakeMesh(key.Item1, key.Item2);
                }
        }

        void BuildCell(ColCell c)
        {
            c.go = new GameObject($"Col_{c.min.x:0}_{c.min.y:0}");
            c.go.transform.SetParent(colliderRoot, false);
            foreach (var s in c.specs)
            {
                var go = new GameObject(s.name ?? "c");
                go.layer = s.layer;
                go.transform.SetParent(c.go.transform, false);
                go.transform.SetPositionAndRotation(s.pos, s.rot);
                go.transform.localScale = Vector3.one * s.scale;
                switch (s.kind)
                {
                    case ShapeKind.Capsule:
                        var cc = go.AddComponent<CapsuleCollider>();
                        cc.radius = s.r;
                        cc.height = Mathf.Max(s.h, s.r * 2f);
                        cc.center = new Vector3(0f, s.h * 0.5f, 0f);
                        break;
                    case ShapeKind.Convex:
                    case ShapeKind.Trimesh:
                        if (s.mesh == null) break;
                        var mc = go.AddComponent<MeshCollider>();
                        mc.convex = s.kind == ShapeKind.Convex;
                        mc.sharedMesh = s.mesh;
                        break;
                }
            }
        }

        /// <summary>Activates the collider cells near every physics focus (ships), builds new ones a few per frame.</summary>
        void UpdateColliders(float dt)
        {
            colTimer -= dt;
            if (colTimer <= 0f)
            {
                colTimer = 0.2f;
                activeColliderCells = 0;
                float on = colliderRadius, off = colliderRadius + 250f;
                foreach (var c in colCellList)
                {
                    float best = float.MaxValue;
                    foreach (var f in physicsFoci)
                    {
                        var p = f();
                        float dx = Mathf.Max(0f, Mathf.Max(c.min.x - p.x, p.x - (c.min.x + ColliderCell)));
                        float dz = Mathf.Max(0f, Mathf.Max(c.min.y - p.z, p.z - (c.min.y + ColliderCell)));
                        best = Mathf.Min(best, dx * dx + dz * dz);
                    }
                    bool want = c.active ? best < off * off : best < on * on;
                    if (want && !c.active)
                    {
                        c.active = true;
                        if (c.go == null) buildQueue.Enqueue(c);
                        else c.go.SetActive(true);
                    }
                    else if (!want && c.active)
                    {
                        c.active = false;
                        if (c.go != null) c.go.SetActive(false);
                    }
                    if (c.active) activeColliderCells++;
                }
            }
            // build at most a few cells per frame (each has up to a few hundred colliders)
            int budget = 3;
            while (buildQueue.Count > 0 && budget-- > 0)
            {
                var c = buildQueue.Dequeue();
                if (c.go != null) continue;
                BuildCell(c);
                c.go.SetActive(c.active);
            }
        }

        /// <summary>Collider streaming step (called by Update; tools call it directly).</summary>
        public void TickColliders(float dt) => UpdateColliders(dt);

        /// <summary>Builds every collider cell near a point right now (before placing a ship there).</summary>
        public void EnsureCollidersAt(Vector3 p, float radius = 400f)
        {
            foreach (var c in colCellList)
            {
                float dx = Mathf.Max(0f, Mathf.Max(c.min.x - p.x, p.x - (c.min.x + ColliderCell)));
                float dz = Mathf.Max(0f, Mathf.Max(c.min.y - p.z, p.z - (c.min.y + ColliderCell)));
                if (dx * dx + dz * dz > radius * radius) continue;
                if (c.go == null) BuildCell(c);
                c.go.SetActive(true);
                c.active = true;
            }
        }

        // ------------------------------------------------------------------ queries

        /// <summary>Inside a tunnel or under a stone roof (echo, darker light).</summary>
        public bool InCave(Vector3 p)
        {
            foreach (var t in caves)
            {
                var rel = p - t.origin;
                if (rel.sqrMagnitude > (t.len + 60f) * (t.len + 60f)) continue;
                float a = Vector3.Dot(rel, t.fwd);
                if (a > 0f && a < t.len && p.y < t.top)
                {
                    var side = new Vector3(t.fwd.z, 0f, -t.fwd.x);
                    if (Mathf.Abs(Vector3.Dot(rel, side)) < t.halfW) return true;
                }
            }
            return false;
        }

        public int ZoneAt(Vector3 p)
        {
            int best = 0;
            float bd = float.MaxValue;
            for (int i = 0; i < data.zones.Length; i++)
            {
                var c = data.zones[i].c;
                float d = Mathf.Max(Mathf.Abs(p.x - c[0]), Mathf.Abs(p.z - c[1]));
                if (d < bd) { bd = d; best = i; }
            }
            return best;
        }

        /// <summary>Nearest route point: in 3D (respawn after a fall) or flat, outside tunnels (map travel).</summary>
        public bool NearestSpawn(Vector3 p, bool flat, out Spawn result)
        {
            result = default;
            float bd = float.MaxValue;
            bool found = false;
            foreach (var s in spawns)
            {
                float dx = s.pos.x - p.x, dz = s.pos.z - p.z;
                float d = dx * dx + dz * dz;
                if (!flat) d += 9f * (s.pos.y - p.y) * (s.pos.y - p.y);
                if (d < bd && !(flat && InCave(s.pos + Vector3.up * 2f)))
                {
                    bd = d;
                    result = s;
                    found = true;
                }
            }
            return found;
        }

        // ------------------------------------------------------------------ per frame

        void Update()
        {
            if (!ready) return;
            UpdateColliders(Time.unscaledDeltaTime);
        }

        void LateUpdate()
        {
            if (!ready) return;
            // instanced decoration: submit cells near the first viewer (other split-screen viewers are close by)
            if (viewers.Count > 0 && viewers[0] != null)
            {
                drawer.Draw(viewers[0].position);
                grass?.Draw(viewers[0].position);
            }
        }
    }
}
