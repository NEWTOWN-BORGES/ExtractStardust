using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using RedDust.Presentation;
using RedDust.Track;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace RedDust.EditorTools
{
    /// <summary>Configura a importação das malhas de geologia exportadas do Blender.</summary>
    class GeologyImportProcessor : AssetPostprocessor
    {
        void OnPreprocessModel()
        {
            if (!assetPath.StartsWith(CourseImporter.GeneratedRoot + "/")) return;
            var mi = (ModelImporter)assetImporter;
            mi.globalScale = 1f;
            mi.useFileScale = true;
            mi.bakeAxisConversion = true;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.None;
            mi.isReadable = true;                                   // normais suavizadas dos repulsores
            mi.materialImportMode = ModelImporterMaterialImportMode.None;
            mi.importAnimation = false;
            mi.animationType = ModelImporterAnimationType.None;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importBlendShapes = false;
            mi.importVisibility = false;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.indexFormat = ModelImporterIndexFormat.Auto;
            mi.addCollider = false;
            mi.generateSecondaryUV = false;
            mi.sortHierarchyByName = true;
            mi.preserveHierarchy = true;
        }
    }

    /// <summary>
    /// Importa um percurso exportado pelo construtor de geologia (Art/Export/&lt;nome&gt;), valida o pipeline FBX
    /// (eixos, escala, orientação das faces) e monta a cena com colliders, material de geologia, sol e atmosfera.
    /// </summary>
    public static class CourseImporter
    {
        public const string GeneratedRoot = "Assets/RedDust/Generated";
        public const string ScenePath = "Assets/RedDust/Scenes/RDD_Sandbox.unity";
        /// <summary>Pistas conhecidas, pela ordem do jogo (a expedição primeiro).</summary>
        public static readonly string[] Courses = { "red_dust_divide", "sandbox" };

        public static string ScenePathFor(string name) => name == "sandbox" ? ScenePath : $"Assets/RedDust/Scenes/RDD_{name}.unity";

        /// <summary>Pista pedida na linha de comandos (-course nome); por omissão o laboratório.</summary>
        public static string CourseArg => CommandLine.Value("-course", "sandbox");

        /// <summary>Cenas das pistas que já existem, pela ordem do jogo.</summary>
        public static string[] AllScenes() => Courses.Select(ScenePathFor).Where(File.Exists).ToArray();

        [MenuItem("Red Dust/2. Importar laboratório (sandbox)")]
        public static void ImportSandbox()
        {
            ImportAndBuild("sandbox");
            if (Application.isBatchMode) EditorApplication.Exit(0);
        }

        [MenuItem("Red Dust/2b. Importar expedição RED DUST DIVIDE")]
        public static void ImportExpedition()
        {
            ImportAndBuild("red_dust_divide");
            if (Application.isBatchMode) EditorApplication.Exit(0);
        }

        /// <summary>Modo batch: importa a pista indicada por -course.</summary>
        public static void ImportCourse()
        {
            ImportAndBuild(CourseArg);
            if (Application.isBatchMode) EditorApplication.Exit(0);
        }

        public static void ImportAndBuild(string name)
        {
            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            string src = Path.Combine(projectRoot, "Art", "Export", name);
            string dst = $"{GeneratedRoot}/{name}";
            if (!Directory.Exists(src)) throw new DirectoryNotFoundException(src);
            Directory.CreateDirectory(dst);
            // a geometria pode vir dividida em setores com nomes diferentes: apagar a anterior para não duplicar
            foreach (var f in Directory.GetFiles(dst, "*.fbx")) AssetDatabase.DeleteAsset(f.Replace('\\', '/'));
            foreach (var f in Directory.GetFiles(src))
            {
                string ext = Path.GetExtension(f).ToLowerInvariant();
                if (ext == ".fbx" || ext == ".bytes" || ext == ".png" || ext == ".json")
                    File.Copy(f, Path.Combine(dst, Path.GetFileName(f)), true);
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var f in Directory.GetFiles(dst, "*.fbx"))
                AssetDatabase.ImportAsset(f.Replace('\\', '/'), ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);

            if (!ValidateAxes($"{dst}/axis_test.fbx", out string report))
                throw new Exception("[RDD] pipeline FBX inválido: " + report);
            Debug.Log("[RDD] " + report);
            BuildScene(name, dst);
        }

        /// <summary>Teste de eixos/escala/faces: o Blender exportou vértices em coordenadas Unity conhecidas.</summary>
        public static bool ValidateAxes(string path, out string report)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (model == null) { report = "axis_test.fbx em falta"; return false; }
            var go = (GameObject)UnityEngine.Object.Instantiate(model);
            try
            {
                var mf = go.GetComponentsInChildren<MeshFilter>().FirstOrDefault(m => m.name.Contains("AXIS_TEST"));
                if (mf == null) { report = "malha AXIS_TEST não encontrada"; return false; }
                var mesh = mf.sharedMesh;
                var world = mesh.vertices.Select(v => mf.transform.localToWorldMatrix.MultiplyPoint3x4(v)).ToList();
                var expected = new[] { new Vector3(1, 2, 3), new Vector3(11, 2, 3), new Vector3(1, 2, 13), new Vector3(11, 12, 13) };
                bool posOk = expected.All(e => world.Any(w => (w - e).sqrMagnitude < 1e-4f)) && world.Count == 4;
                var tris = mesh.triangles;
                bool faceOk = true;
                for (int i = 0; i + 2 < tris.Length; i += 3)
                {
                    Vector3 a = world[tris[i]], b = world[tris[i + 1]], c = world[tris[i + 2]];
                    if (Vector3.Cross(b - a, c - a).y <= 0f) faceOk = false;   // faces da frente viradas para +y
                }
                var nrm = mesh.normals.Select(n => mf.transform.TransformDirection(n)).ToArray();
                bool nrmOk = nrm.All(n => n.y > 0.99f);
                report = $"teste de eixos FBX: posições {(posOk ? "OK" : "FALHA")} · faces {(faceOk ? "OK" : "FALHA")} · normais {(nrmOk ? "OK" : "FALHA")} · vértices {string.Join(" ", world.Select(w => $"({w.x:0.##},{w.y:0.##},{w.z:0.##})"))} · normais {string.Join(" ", nrm.Select(n => $"({n.x:0.##},{n.y:0.##},{n.z:0.##})"))}";
                return posOk && faceOk && nrmOk;
            }
            finally { UnityEngine.Object.DestroyImmediate(go); }
        }

        static void BuildScene(string name, string dst)
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var geo = AssetDatabase.LoadAssetAtPath<Material>($"{ProjectSetup.MaterialsDir}/Geology.mat");
            var wreck = AssetDatabase.LoadAssetAtPath<Material>($"{ProjectSetup.MaterialsDir}/WreckMetal.mat");
            var sky = AssetDatabase.LoadAssetAtPath<Material>($"{ProjectSetup.MaterialsDir}/SkyRDD.mat");
            var root = new GameObject("Course_" + name);
            int colliders = 0, tris = 0, rocksOff = 0, rocksKept = 0, rocksGone = 0, terrainCut = 0;
            var graphAsset = AssetDatabase.LoadAssetAtPath<TextAsset>($"{dst}/{name}_graph.bytes");
            var courseAsset = AssetDatabase.LoadAssetAtPath<TextAsset>($"{dst}/{name}_course.bytes");
            var ride = new RideIndex(graphAsset != null ? CourseGraph.Load(graphAsset.bytes) : CourseGraph.Single(CourseData.Load(courseAsset.bytes)));
            // pedras pequenas não colidem (pedido do jogador): só objetos grandes (pilares, blocos grandes, paredes) batem
            string genDir = $"Assets/RedDust/Generated/{name}_colliders";
            if (AssetDatabase.IsValidFolder(genDir)) AssetDatabase.DeleteAsset(genDir);
            Directory.CreateDirectory(genDir);
            AssetDatabase.Refresh();
            // corredor e terreno, num ficheiro ou em vários setores (<nome>_corridor_00.fbx, ...)
            var parts = Directory.GetFiles(dst, "*.fbx").Select(f => f.Replace('\\', '/'))
                .Where(f => Path.GetFileName(f).StartsWith(name + "_corridor") || Path.GetFileName(f).StartsWith(name + "_terrain"))
                .OrderBy(f => f).ToList();
            if (parts.Count == 0) throw new FileNotFoundException($"{dst}/{name}_corridor*.fbx");
            foreach (var path in parts)
            {
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (model == null) throw new FileNotFoundException(path);
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(model, scene);
                inst.transform.SetParent(root.transform, false);
                foreach (var mf in inst.GetComponentsInChildren<MeshFilter>())
                {
                    mf.gameObject.layer = Layers.Ground;
                    var mr = mf.GetComponent<MeshRenderer>();
                    mr.sharedMaterial = mf.name.StartsWith("GEO_Wreck") && wreck != null ? wreck : geo;
                    mr.shadowCastingMode = ShadowCastingMode.On;
                    mr.receiveShadows = true;
                    if (mf.name.StartsWith("GEO_Terrain"))
                    {
                        // terreno que entra na zona de corrida (acima do chão da pista) sai: a pista nunca fica enterrada
                        var carved = CarveTerrain(mf.sharedMesh, mf.transform.localToWorldMatrix, ride, out int cut);
                        terrainCut += cut;
                        if (carved != mf.sharedMesh)
                        {
                            if (carved != null) AssetDatabase.CreateAsset(carved, $"{genDir}/{mf.name}_{colliders}_t.asset");
                            mf.sharedMesh = carved;
                            if (carved == null) { mr.enabled = false; continue; }
                        }
                    }
                    var colMesh = mf.sharedMesh;
                    bool scatter = mf.name.StartsWith("GEO_Rocks"), onTrack = mf.name.StartsWith("GEO_Obstacles");
                    if (scatter || onTrack)
                    {
                        // rochas: as que entram na zona de corrida saem; pequenas sem colisão; no traçado só ficam os pilares
                        var (render, col) = SplitRocks(mf.sharedMesh, mf.transform.localToWorldMatrix, BigRock, scatter ? ride.Intrudes : null, onTrack,
                                                       out int off, out int kept, out int gone);
                        rocksOff += off; rocksKept += kept; rocksGone += gone;
                        if (render != mf.sharedMesh)
                        {
                            if (render != null) AssetDatabase.CreateAsset(render, $"{genDir}/{mf.name}_{colliders}_r.asset");
                            mf.sharedMesh = render;
                            if (render == null) mr.enabled = false;
                        }
                        if (col != null && col != render && col != colMesh) AssetDatabase.CreateAsset(col, $"{genDir}/{mf.name}_{colliders}_c.asset");
                        colMesh = col;
                    }
                    if (colMesh != null)
                    {
                        var mc = mf.gameObject.AddComponent<MeshCollider>();
                        mc.sharedMesh = colMesh;
                        colliders++;
                    }
                    if (mf.sharedMesh != null) tris += mf.sharedMesh.triangles.Length / 3;
                }
            }
            var course = root.AddComponent<CourseRuntime>();
            course.courseBytes = AssetDatabase.LoadAssetAtPath<TextAsset>($"{dst}/{name}_course.bytes");
            course.graphBytes = AssetDatabase.LoadAssetAtPath<TextAsset>($"{dst}/{name}_graph.bytes");
            course.obstaclesJson = AssetDatabase.LoadAssetAtPath<TextAsset>($"{dst}/{name}_obstacles.json");
            course.title = ReadTitle(name);
            root.AddComponent<SectorStreamer>();

            var sunGo = new GameObject("Sun");
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sunGo.transform.rotation = Quaternion.Euler(42f, 228f, 0f);
            RenderSettings.skybox = sky;
            EnvironmentRig.Apply(sun, false);

            var dir = new GameObject("SandboxDirector").AddComponent<SandboxDirector>();
            dir.sun = sun;

            string scenePath = ScenePathFor(name);
            Directory.CreateDirectory(Path.GetDirectoryName(scenePath));
            EditorSceneManager.SaveScene(scene, scenePath);
            EditorBuildSettings.scenes = AllScenes().Select(s => new EditorBuildSettingsScene(s, true)).ToArray();
            AssetDatabase.SaveAssets();
            Debug.Log($"[RDD] terreno: {terrainCut} triângulos retirados de cima da pista");
            Debug.Log($"[RDD] pedras: {rocksGone} retiradas da zona de corrida · {rocksOff} pequenas sem colisão (< {BigRock} m) · {rocksKept} grandes com colisão");
            Debug.Log($"[RDD] cena {scenePath}: {parts.Count} ficheiros, {colliders} colliders, {tris / 1000}k triângulos, percurso {course.Data.Length / 1000f:0.00} km, {course.Graph.BranchCount} ramos");
        }

        /// <summary>Tamanho mínimo (maior dimensão, m) para uma pedra/obstáculo ter colisão.</summary>
        const float BigRock = 8f;

        /// <summary>
        /// Separa uma malha de pedras em ilhas (vértices soldados por posição, para juntar as costuras do FBX).
        /// Saem por completo: as ilhas que entram na zona de corrida (intrudes) e, no traçado (dropSmall), as pequenas
        /// soltas. Colisão: só ilhas grandes (maior dimensão >= minSize) e as peças encostadas a elas (chapéu dos pilares).
        /// Devolve (malha visível, malha de colisão): a própria src quando não muda e null quando fica vazia.
        /// </summary>
        static (Mesh render, Mesh col) SplitRocks(Mesh src, Matrix4x4 toWorld, float minSize, System.Func<Bounds, bool> intrudes, bool dropSmall,
                                                  out int dropped, out int kept, out int gone)
        {
            var v = src.vertices;
            var t = src.triangles;
            var keyOf = new Dictionary<Vector3Int, int>();
            var id = new int[v.Length];
            for (int i = 0; i < v.Length; i++)
            {
                var k = new Vector3Int(Mathf.RoundToInt(v[i].x * 200f), Mathf.RoundToInt(v[i].y * 200f), Mathf.RoundToInt(v[i].z * 200f));
                if (!keyOf.TryGetValue(k, out int j)) { j = keyOf.Count; keyOf[k] = j; }
                id[i] = j;
            }
            var parent = Enumerable.Range(0, keyOf.Count).ToArray();
            int Find(int x) { while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; }
            void Union(int a, int b) { a = Find(a); b = Find(b); if (a != b) parent[b] = a; }
            for (int i = 0; i + 2 < t.Length; i += 3) { Union(id[t[i]], id[t[i + 1]]); Union(id[t[i]], id[t[i + 2]]); }
            var bounds = new Dictionary<int, Bounds>();
            for (int i = 0; i < v.Length; i++)
            {
                int r = Find(id[i]);
                var w = toWorld.MultiplyPoint3x4(v[i]);
                if (bounds.TryGetValue(r, out var b)) { b.Encapsulate(w); bounds[r] = b; } else bounds[r] = new Bounds(w, Vector3.zero);
            }
            var big = new HashSet<int>();
            foreach (var kv in bounds)
            {
                var sz = kv.Value.size;
                if (Mathf.Max(sz.x, Mathf.Max(sz.y, sz.z)) >= minSize) big.Add(kv.Key);
            }
            var bigBounds = big.Select(k => { var b = bounds[k]; b.Expand(1f); return b; }).ToList();
            foreach (var kv in bounds)
                if (!big.Contains(kv.Key) && bigBounds.Any(b => b.Intersects(kv.Value))) big.Add(kv.Key);
            var removed = new HashSet<int>();
            foreach (var kv in bounds)
                if ((intrudes != null && intrudes(kv.Value)) || (dropSmall && !big.Contains(kv.Key))) removed.Add(kv.Key);
            big.ExceptWith(removed);
            gone = intrudes != null ? removed.Count : 0;
            kept = big.Count;
            dropped = bounds.Count - big.Count - removed.Count;
            Mesh Sub(System.Func<int, bool> keep, string suffix)
            {
                var idx = new List<int>(t.Length);
                for (int i = 0; i + 2 < t.Length; i += 3)
                    if (keep(Find(id[t[i]]))) { idx.Add(t[i]); idx.Add(t[i + 1]); idx.Add(t[i + 2]); }
                if (idx.Count == t.Length) return src;
                if (idx.Count == 0) return null;
                var m = new Mesh { name = src.name + suffix, indexFormat = v.Length > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                m.vertices = v;
                m.normals = src.normals;
                if (src.colors32 != null && src.colors32.Length == v.Length) m.colors32 = src.colors32;
                if (src.uv != null && src.uv.Length == v.Length) m.uv = src.uv;
                m.SetTriangles(idx, 0);
                m.RecalculateBounds();
                return m;
            }
            var render = removed.Count == 0 ? src : Sub(k => !removed.Contains(k), "_vis");
            bool sameSet = big.Count == bounds.Count - removed.Count;
            var col = sameSet ? render : Sub(k => big.Contains(k), "_col");
            return (render, col);
        }

        /// <summary>
        /// Tira do terreno os triângulos com algum vértice dentro da zona de corrida e acima do chão da pista
        /// (0,3 a 60 m): onde o relevo cobria o corredor, a pista volta a ficar livre. Mesma malha se nada muda.
        /// </summary>
        static Mesh CarveTerrain(Mesh src, Matrix4x4 toWorld, RideIndex ride, out int cut)
        {
            cut = 0;
            var wb = GeometryUtility.CalculateBounds(new[] { src.bounds.min, src.bounds.max }, toWorld);
            if (!ride.Near(wb, 40f)) return src;
            var v = src.vertices;
            var t = src.triangles;
            var bad = new bool[v.Length];
            bool any = false;
            for (int i = 0; i < v.Length; i++)
            {
                bad[i] = ride.Covers(toWorld.MultiplyPoint3x4(v[i]));
                any |= bad[i];
            }
            if (!any) return src;
            var keep = new List<int>(t.Length);
            for (int i = 0; i + 2 < t.Length; i += 3)
            {
                if (bad[t[i]] || bad[t[i + 1]] || bad[t[i + 2]]) { cut++; continue; }
                keep.Add(t[i]); keep.Add(t[i + 1]); keep.Add(t[i + 2]);
            }
            if (keep.Count == 0) return null;
            var m = new Mesh { name = src.name + "_carved", indexFormat = v.Length > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            m.vertices = v;
            m.normals = src.normals;
            if (src.colors32 != null && src.colors32.Length == v.Length) m.colors32 = src.colors32;
            if (src.uv != null && src.uv.Length == v.Length) m.uv = src.uv;
            if (src.uv2 != null && src.uv2.Length == v.Length) m.uv2 = src.uv2;
            m.SetTriangles(keep, 0);
            m.RecalculateBounds();
            return m;
        }

        /// <summary>
        /// Índice espacial das estações de todos os percursos: diz se uma caixa (rocha) entra na zona de corrida
        /// (lateralmente dentro das linhas de corrida e à altura do chão).
        /// </summary>
        sealed class RideIndex
        {
            const float Cell = 40f;
            readonly Dictionary<long, List<(CourseData d, int i)>> cells = new Dictionary<long, List<(CourseData d, int i)>>();

            public RideIndex(CourseGraph g)
            {
                foreach (var p in g.Paths)
                    for (int i = 0; i < p.Data.StationCount; i++)
                    {
                        var c = p.Data.Center[i];
                        long k = Key(Mathf.FloorToInt(c.x / Cell), Mathf.FloorToInt(c.z / Cell));
                        if (!cells.TryGetValue(k, out var list)) cells[k] = list = new List<(CourseData d, int i)>();
                        list.Add((p.Data, i));
                    }
            }

            static long Key(int x, int z) => ((long)x << 32) ^ (uint)z;

            /// <summary>Há alguma estação a menos de margin da caixa (no plano)?</summary>
            public bool Near(Bounds b, float margin)
            {
                int x0 = Mathf.FloorToInt((b.min.x - margin) / Cell), x1 = Mathf.FloorToInt((b.max.x + margin) / Cell);
                int z0 = Mathf.FloorToInt((b.min.z - margin) / Cell), z1 = Mathf.FloorToInt((b.max.z + margin) / Cell);
                for (int x = x0; x <= x1; x++)
                    for (int z = z0; z <= z1; z++)
                        if (cells.ContainsKey(Key(x, z))) return true;
                return false;
            }

            /// <summary>O ponto está por cima da zona de corrida (dentro das linhas + 2 m) entre 0,3 m e 60 m acima do chão?</summary>
            public bool Covers(Vector3 p)
            {
                int cx = Mathf.FloorToInt(p.x / Cell), cz = Mathf.FloorToInt(p.z / Cell);
                for (int dx = -1; dx <= 1; dx++)
                    for (int dz = -1; dz <= 1; dz++)
                    {
                        if (!cells.TryGetValue(Key(cx + dx, cz + dz), out var list)) continue;
                        foreach (var (d, i) in list)
                        {
                            var o = p - d.Center[i];
                            if (Mathf.Abs(Vector3.Dot(o, d.Tangent[i])) > 3.5f) continue;
                            float lat = Vector3.Dot(o, d.Right[i]);
                            if (lat < -d.RideLeft[i] - 2f || lat > d.RideRight[i] + 2f) continue;
                            float u = lat < 0f ? lat / Mathf.Max(1f, d.RideLeft[i]) : lat / Mathf.Max(1f, d.RideRight[i]);
                            float h = Vector3.Dot(p - d.LanePoint(i, Mathf.Clamp(u, -1f, 1f)), d.Up[i]);
                            if (h > 0.3f && h < 60f) return true;
                        }
                    }
                return false;
            }

            public bool Intrudes(Bounds b)
            {
                float y = b.min.y + Mathf.Min(0.8f, b.size.y * 0.5f);
                var pts = new[] { new Vector3(b.center.x, y, b.center.z), new Vector3(b.min.x, y, b.min.z), new Vector3(b.max.x, y, b.min.z),
                                  new Vector3(b.min.x, y, b.max.z), new Vector3(b.max.x, y, b.max.z) };
                int cx = Mathf.FloorToInt(b.center.x / Cell), cz = Mathf.FloorToInt(b.center.z / Cell);
                int r = 1 + Mathf.CeilToInt(Mathf.Max(b.extents.x, b.extents.z) / Cell);
                for (int dx = -r; dx <= r; dx++)
                    for (int dz = -r; dz <= r; dz++)
                    {
                        if (!cells.TryGetValue(Key(cx + dx, cz + dz), out var list)) continue;
                        foreach (var (d, i) in list)
                            foreach (var p in pts)
                            {
                                if (Mathf.Abs(Vector3.Dot(p - d.Center[i], d.Tangent[i])) > 3.5f) continue;
                                float h = Vector3.Dot(p - d.LanePoint(i, 0f), d.Up[i]);
                                if (h < -3f || h > 8f) continue;
                                if (d.OutsideRide(p, i) <= 0.5f) return true;
                            }
                    }
                return false;
            }
        }

        /// <summary>Título da pista (campo "title" do JSON em Art/Courses).</summary>
        static string ReadTitle(string name)
        {
            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            string spec = Path.Combine(projectRoot, "Art", "Courses", name + ".json");
            if (!File.Exists(spec)) return name;
            var t = JsonUtility.FromJson<SpecTitle>(File.ReadAllText(spec));
            return string.IsNullOrEmpty(t?.title) ? name : t.title;
        }

        [Serializable] class SpecTitle { public string title; }
    }
}
