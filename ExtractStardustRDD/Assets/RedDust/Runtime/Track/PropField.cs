using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

namespace RedDust.Track
{
    /// <summary>
    /// Vegetação e adereços da paisagem (kit Resources/Props/props_kit, gerado por Art/Blender/rdd_props_kit.py):
    /// desenhados com GPU instancing só nas células perto das câmaras e das naves; sem colisão. Os dados (tipo, posição,
    /// rotação, escala) são gerados na importação da pista (CourseImporter.ScatterProps).
    /// </summary>
    public class PropField : MonoBehaviour
    {
        public TextAsset data;
        public float drawRadius = 520f;

        /// <summary>Tipos instanciados (o índice é o que vai nos dados).</summary>
        public static readonly string[] Types =
        {
            "P_DeadTree_A", "P_DeadTree_B", "P_DeadTree_C", "P_Saguaro_A", "P_Saguaro_B", "P_PricklyPear", "P_Barrel",
            "P_Bush_Dry_A", "P_Bush_Dry_B", "P_Bush_Green", "P_Grass_Dry", "P_Grass_Green", "P_Tree_A", "P_Tree_B",
            "P_Juniper", "P_Joshua", "P_Boulder_A", "P_Boulder_B", "P_Boulder_C",
        };

        const float Cell = 100f;

        sealed class Kind
        {
            public Mesh mesh;
            public Material[] mats;
            public Matrix4x4 fix;
            public readonly List<Matrix4x4> frame = new List<Matrix4x4>();
        }

        Kind[] kinds;
        Dictionary<long, List<(int t, Matrix4x4 m)>> cells;
        readonly HashSet<long> drawn = new HashSet<long>();
        Bounds frameBounds;
        public int Count { get; private set; }

        static long Key(int x, int z) => ((long)x << 32) ^ (uint)z;

        void Start() => Load();

        public void Load()
        {
            if (kinds != null || data == null) return;
            if (!SystemInfo.supportsInstancing) { enabled = false; return; }   // testes sem gráficos
            var kit = Resources.Load<GameObject>("Props/props_kit");
            if (kit == null) { enabled = false; return; }
            var baseMat = Resources.Load<Material>("Props/PropLit");
            kinds = new Kind[Types.Length];
            foreach (var mf in kit.GetComponentsInChildren<MeshFilter>(true))
            {
                int t = System.Array.IndexOf(Types, mf.name);
                if (t < 0 || mf.sharedMesh == null) continue;
                var mr = mf.GetComponent<MeshRenderer>();
                var mats = new Material[mf.sharedMesh.subMeshCount];
                for (int s = 0; s < mats.Length; s++)
                    mats[s] = MakeMat(baseMat, mr != null && s < mr.sharedMaterials.Length && mr.sharedMaterials[s] != null ? mr.sharedMaterials[s].name : "");
                kinds[t] = new Kind { mesh = mf.sharedMesh, mats = mats, fix = kit.transform.worldToLocalMatrix * mf.transform.localToWorldMatrix };
            }
            cells = new Dictionary<long, List<(int, Matrix4x4)>>();
            using (var br = new BinaryReader(new MemoryStream(data.bytes)))
            {
                int n = br.ReadInt32();
                for (int i = 0; i < n; i++)
                {
                    int t = br.ReadByte();
                    var p = new Vector3(br.ReadSingle(), br.ReadSingle(), br.ReadSingle());
                    float yaw = br.ReadSingle(), sc = br.ReadSingle();
                    var up = new Vector3(br.ReadSingle(), br.ReadSingle(), br.ReadSingle());
                    if (t >= kinds.Length || kinds[t] == null) continue;
                    var rot = Quaternion.FromToRotation(Vector3.up, up) * Quaternion.Euler(0f, yaw, 0f);
                    var m = Matrix4x4.TRS(p, rot, Vector3.one * sc) * kinds[t].fix;
                    long k = Key(Mathf.FloorToInt(p.x / Cell), Mathf.FloorToInt(p.z / Cell));
                    if (!cells.TryGetValue(k, out var list)) cells[k] = list = new List<(int, Matrix4x4)>();
                    list.Add((t, m));
                    Count++;
                }
            }
        }

        static readonly Dictionary<string, Material> matCache = new Dictionary<string, Material>();

        static Material MakeMat(Material baseMat, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (matCache.TryGetValue(name, out var m) && m != null) return m;
            m = baseMat != null ? new Material(baseMat) : new Material(Shader.Find("Universal Render Pipeline/Lit"));
            m.enableInstancing = true;
            m.name = name;
            Color c = name.Contains("DeadWood") ? new Color(0.52f, 0.46f, 0.40f) : name.Contains("Bark") ? new Color(0.36f, 0.28f, 0.21f)
                    : name.Contains("Leaves") ? new Color(0.36f, 0.53f, 0.19f) : name.Contains("Juniper") ? new Color(0.22f, 0.34f, 0.20f)
                    : name.Contains("Joshua") ? new Color(0.30f, 0.40f, 0.20f) : name.Contains("ShrubGreen") ? new Color(0.32f, 0.50f, 0.20f)
                    : name.Contains("ShrubDry") ? new Color(0.55f, 0.57f, 0.42f) : name.Contains("GrassGreen") ? new Color(0.45f, 0.64f, 0.22f)
                    : name.Contains("GrassDry") ? new Color(0.80f, 0.69f, 0.42f) : name.Contains("Cactus") ? new Color(0.30f, 0.50f, 0.30f)
                    : name.Contains("Flower") ? new Color(0.98f, 0.78f, 0.18f) : name.Contains("Fruit") ? new Color(0.78f, 0.16f, 0.36f)
                    : name.Contains("Rock") ? new Color(0.66f, 0.38f, 0.25f) : new Color(0.6f, 0.5f, 0.4f);
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
            if (m.HasProperty("_Color")) m.SetColor("_Color", c);
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", name.Contains("Cactus") || name.Contains("Leaves") ? 0.25f : 0.1f);
            if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", 0f);
            matCache[name] = m;
            return m;
        }

        void LateUpdate()
        {
            if (kinds == null) return;
            drawn.Clear();
            var cam = Camera.main;
            bool any = false;
            if (cam != null) { Gather(cam.transform.position, ref any); }
            foreach (var f in SectorStreamer.Focus) if (f != null) Gather(f.position, ref any);
            if (any) Flush();
        }

        /// <summary>Desenha os adereços à volta de p (fotos no editor: chamar antes de Camera.Render).</summary>
        public void DrawAround(Vector3 p)
        {
            Load();
            if (kinds == null) return;
            drawn.Clear();
            bool any = false;
            Gather(p, ref any);
            if (any) Flush();
        }

        void Gather(Vector3 p, ref bool any)
        {
            int r = Mathf.CeilToInt(drawRadius / Cell);
            int cx = Mathf.FloorToInt(p.x / Cell), cz = Mathf.FloorToInt(p.z / Cell);
            float r2 = drawRadius * drawRadius;
            for (int dx = -r; dx <= r; dx++)
                for (int dz = -r; dz <= r; dz++)
                {
                    long k = Key(cx + dx, cz + dz);
                    if (!drawn.Add(k) || !cells.TryGetValue(k, out var list)) continue;
                    foreach (var (t, m) in list)
                    {
                        Vector3 q = m.GetColumn(3);
                        float ddx = q.x - p.x, ddz = q.z - p.z;
                        if (ddx * ddx + ddz * ddz > r2) continue;
                        kinds[t].frame.Add(m);
                        if (!any) { frameBounds = new Bounds(q, Vector3.one * 10f); any = true; } else frameBounds.Encapsulate(q);
                    }
                }
        }

        void Flush()
        {
            frameBounds.Expand(60f);
            foreach (var k in kinds)
            {
                if (k == null || k.frame.Count == 0) continue;
                for (int s = 0; s < k.mats.Length; s++)
                {
                    var rp = new RenderParams(k.mats[s]) { shadowCastingMode = ShadowCastingMode.On, receiveShadows = true, worldBounds = frameBounds };
                    for (int start = 0; start < k.frame.Count; start += 1023)
                        Graphics.RenderMeshInstanced(rp, k.mesh, s, k.frame, Mathf.Min(1023, k.frame.Count - start), start);
                }
                k.frame.Clear();
            }
        }
    }
}
