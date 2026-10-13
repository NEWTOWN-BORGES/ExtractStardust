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
                        colMesh = scatter ? null : col;   // rochas de decoração nunca colidem (só pilares, paredes e megaestruturas)
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
            ScatterProps(name, genDir, root, ride, course.Graph, geo);

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
        // ------------------------------------------------------------------ paisagem: vegetação, adereços e monumentos

        /// <summary>Zonas da paisagem: densidade e pesos por tipo (nomes de PropField.Types).</summary>
        static readonly Dictionary<string, (float dens, (string t, float w)[] mix)> Zones = new Dictionary<string, (float, (string, float)[])>
        {
            ["desert"] = (1.0f, new[] { ("P_DeadTree_A", 1f), ("P_DeadTree_B", 1f), ("P_DeadTree_C", 1f), ("P_Saguaro_A", 1.5f), ("P_Saguaro_B", 1.5f), ("P_PricklyPear", 2f),
                                        ("P_Barrel", 1f), ("P_Bush_Dry_A", 3f), ("P_Bush_Dry_B", 3f), ("P_Grass_Dry", 5f), ("P_Boulder_A", 1f), ("P_Boulder_B", 1f), ("P_Boulder_C", 1f), ("P_Joshua", 1f) }),
            ["rocky"] = (0.8f, new[] { ("P_DeadTree_A", 1f), ("P_DeadTree_C", 1f), ("P_PricklyPear", 1.5f), ("P_Barrel", 1.5f), ("P_Bush_Dry_A", 2f), ("P_Bush_Dry_B", 2f),
                                       ("P_Grass_Dry", 2f), ("P_Boulder_A", 3f), ("P_Boulder_B", 3f), ("P_Boulder_C", 3f) }),
            ["canyon"] = (0.9f, new[] { ("P_DeadTree_A", 1.5f), ("P_DeadTree_B", 1.5f), ("P_DeadTree_C", 1.5f), ("P_Bush_Dry_A", 2.5f), ("P_Bush_Dry_B", 2.5f), ("P_Grass_Dry", 3f),
                                        ("P_Boulder_A", 2f), ("P_Boulder_B", 2f), ("P_Boulder_C", 2f), ("P_Juniper", 2f), ("P_PricklyPear", 1f) }),
            ["green"] = (1.9f, new[] { ("P_Tree_A", 3f), ("P_Tree_B", 3f), ("P_Bush_Green", 6f), ("P_Grass_Green", 10f), ("P_Juniper", 1f), ("P_Boulder_A", 1f),
                                       ("P_Boulder_B", 1f), ("P_DeadTree_A", 0.5f) }),
            ["wash"] = (1.3f, new[] { ("P_DeadTree_A", 2f), ("P_DeadTree_B", 2f), ("P_DeadTree_C", 2f), ("P_Tree_A", 1f), ("P_Bush_Dry_A", 3f), ("P_Bush_Dry_B", 3f),
                                      ("P_Bush_Green", 2f), ("P_Grass_Dry", 5f), ("P_Grass_Green", 2f), ("P_Boulder_A", 1.5f), ("P_Boulder_C", 1.5f) }),
            ["arches"] = (1.0f, new[] { ("P_Juniper", 5f), ("P_PricklyPear", 2f), ("P_Bush_Dry_A", 2f), ("P_Bush_Dry_B", 2f), ("P_Grass_Dry", 3f), ("P_Boulder_A", 1.5f),
                                        ("P_Boulder_B", 1.5f), ("P_DeadTree_B", 1f), ("P_Barrel", 1f) }),
            ["rim"] = (0.7f, new[] { ("P_Bush_Dry_A", 3f), ("P_Bush_Dry_B", 3f), ("P_Grass_Dry", 4f), ("P_Boulder_A", 2f), ("P_Boulder_B", 2f), ("P_Boulder_C", 2f),
                                     ("P_DeadTree_C", 1f), ("P_Saguaro_A", 0.5f) }),
        };

        static string ZoneOfSector(string id)
        {
            id = id.ToUpperInvariant();
            if (id.Contains("BASIN")) return "desert";
            if (id.Contains("MESA")) return "rocky";
            if (id.Contains("SHAFER") || id.Contains("RED WALL")) return "canyon";
            if (id.Contains("HORSESHOE") || id.Contains("HOLLOW")) return "green";
            if (id.Contains("WASH")) return "wash";
            if (id.Contains("ARCH")) return "arches";
            if (id.Contains("RIM")) return "rim";
            return "desert";
        }

        static readonly string[] ZoneCycle = { "desert", "green", "wash", "arches", "rocky", "canyon" };

        static (float lo, float hi) ScaleRange(string t, bool far) => t.StartsWith("P_Boulder") ? (far ? (1.5f, 4.2f) : (0.4f, 1.5f))
            : t.StartsWith("P_Grass") ? (0.7f, 1.4f) : t.StartsWith("P_Bush") ? (0.6f, 1.4f) : t.StartsWith("P_Tree") ? (0.85f, 1.35f)
            : t.StartsWith("P_Barrel") || t.StartsWith("P_Prickly") ? (0.8f, 1.5f) : (0.8f, 1.3f);

        /// <summary>
        /// Espalha a paisagem: bermas (2 a 32 m para lá das linhas de corrida) e terreno (45 a 350 m) com a mistura da zona do
        /// sector; monumentos (mesas, buttes, agulhas) no horizonte. Nada entra na zona de corrida; adereços sem colisão.
        /// </summary>
        static void ScatterProps(string name, string genDir, GameObject root, RideIndex ride, CourseGraph g, Material geo)
        {
            const string matPath = "Assets/RedDust/Resources/Props/PropLit.mat";
            if (AssetDatabase.LoadAssetAtPath<Material>(matPath) == null)
                AssetDatabase.CreateAsset(new Material(Shader.Find("Universal Render Pipeline/Lit")) { enableInstancing = true }, matPath);
            var kit = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/RedDust/Resources/Props/props_kit.fbx");
            if (kit == null) { Debug.LogWarning("[RDD] paisagem: kit de adereços em falta"); return; }
            Physics.SyncTransforms();

            // sectores (id, de, até) a partir do JSON da pista
            var sectors = new List<(string id, float a, float b)>();
            string spec = Path.Combine(Directory.GetParent(Application.dataPath).FullName, "Art", "Courses", name + ".json");
            if (File.Exists(spec))
                foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(File.ReadAllText(spec),
                         "\\{\\s*\"id\":\\s*\"([^\"]+)\",\\s*\"from\":\\s*([0-9.]+),\\s*\"to\":\\s*([0-9.]+)\\s*\\}"))
                    if (!m.Groups[1].Value.StartsWith("SAFE") && !m.Groups[1].Value.StartsWith("SKILL"))
                        sectors.Add((m.Groups[1].Value, float.Parse(m.Groups[2].Value, System.Globalization.CultureInfo.InvariantCulture),
                                     float.Parse(m.Groups[3].Value, System.Globalization.CultureInfo.InvariantCulture)));
            string ZoneAt(float dist)
            {
                foreach (var sc in sectors) if (dist >= sc.a && dist < sc.b) return ZoneOfSector(sc.id);
                return ZoneCycle[Mathf.FloorToInt(dist / 4000f) % ZoneCycle.Length];
            }

            var rnd = new System.Random(4242 + name.Length * 97);
            float R01() => (float)rnd.NextDouble();
            float Rng(float a, float b) => a + (b - a) * R01();
            string Pick(string zone)
            {
                var mix = Zones[zone].mix;
                float tot = 0f;
                foreach (var e in mix) tot += e.w;
                float x = R01() * tot;
                foreach (var e in mix) { x -= e.w; if (x <= 0f) return e.t; }
                return mix[mix.Length - 1].t;
            }
            var recs = new List<(byte t, Vector3 p, float yaw, float s, Vector3 up)>();
            void Put(string type, RaycastHit hit, bool far)
            {
                int t = System.Array.IndexOf(PropField.Types, type);
                if (t < 0) return;
                bool upright = type.StartsWith("P_Tree") || type.StartsWith("P_Saguaro") || type.StartsWith("P_DeadTree") || type.StartsWith("P_Joshua");
                var up = Vector3.Slerp(Vector3.up, hit.normal, upright ? 0.1f : 0.6f).normalized;
                var (lo, hi) = ScaleRange(type, far);
                recs.Add(((byte)t, hit.point - up * 0.05f, Rng(0f, 360f), Rng(lo, hi), up));
            }

            foreach (var path in g.Paths)
            {
                var d = path.Data;
                for (int i = 2; i < d.StationCount - 2; i += 2)
                {
                    if (d.IsGap(i) || d.IsCave(i)) continue;
                    string zone = ZoneAt(d.Dist[i]);
                    float dens = Zones[zone].dens;
                    for (int side = -1; side <= 1; side += 2)
                    {
                        // bermas: grupos com manchas (ruído) para não ficar uniforme
                        float clump = 0.25f + 1.5f * Mathf.PerlinNoise(d.Dist[i] * 0.004f + side * 17.3f, 3.7f);
                        float want = 1.5f * dens * clump;
                        int n = Mathf.FloorToInt(want) + (R01() < want - Mathf.Floor(want) ? 1 : 0);
                        float rideSide = Mathf.Max(4f, side < 0 ? d.RideLeft[i] : d.RideRight[i]);
                        for (int k = 0; k < n; k++)
                        {
                            float extra = 2f + 30f * Mathf.Pow(R01(), 1.6f);
                            var p0 = d.LanePoint(i, side * (1f + extra / rideSide)) + d.Tangent[i] * Rng(-5f, 5f);
                            if (!Physics.Raycast(p0 + d.Up[i] * 8f, -d.Up[i], out var hit, 30f, Layers.GroundMask, QueryTriggerInteraction.Ignore)) continue;
                            string type = Pick(zone);
                            if (hit.normal.y < (type.StartsWith("P_Boulder") ? 0.4f : 0.6f)) continue;
                            if (ride.Intrudes(new Bounds(hit.point + Vector3.up, Vector3.one * 3f))) continue;
                            Put(type, hit, false);
                        }
                        // zonas verdes: tapete de erva extra nas bermas
                        if (zone == "green")
                            for (int k = 0; k < 3; k++)
                            {
                                float extra = 1.5f + 22f * R01();
                                var p0 = d.LanePoint(i, side * (1f + extra / rideSide)) + d.Tangent[i] * Rng(-5f, 5f);
                                if (!Physics.Raycast(p0 + d.Up[i] * 8f, -d.Up[i], out var hit, 30f, Layers.GroundMask, QueryTriggerInteraction.Ignore)) continue;
                                if (hit.normal.y < 0.6f || ride.Intrudes(new Bounds(hit.point + Vector3.up, Vector3.one * 3f))) continue;
                                Put(R01() < 0.8f ? "P_Grass_Green" : "P_Bush_Green", hit, false);
                            }
                        // terreno: mais esparso, peças maiores (sem erva), até 700 m
                        if (i % 4 == 0 && R01() < 0.75f * dens)
                        {
                            float lat = 45f + 650f * Mathf.Pow(R01(), 1.5f);
                            var p0 = d.Center[i] + d.Right[i] * side * lat + d.Tangent[i] * Rng(-15f, 15f);
                            if (!Physics.Raycast(p0 + Vector3.up * 500f, Vector3.down, out var hit, 1400f, Layers.GroundMask, QueryTriggerInteraction.Ignore)) continue;
                            if (hit.normal.y < 0.6f) continue;
                            string type = Pick(zone);
                            if (type.StartsWith("P_Grass")) type = zone == "green" ? "P_Tree_A" : "P_Bush_Dry_A";
                            if (ride.Intrudes(new Bounds(hit.point + Vector3.up, Vector3.one * 6f))) continue;
                            Put(type, hit, true);
                        }
                    }
                }
            }

            // dados para o PropField (binário: tipo, posição, yaw, escala, cima)
            string dataPath = $"{genDir}/{name}_props.bytes";
            using (var bw = new BinaryWriter(File.Create(dataPath)))
            {
                bw.Write(recs.Count);
                foreach (var r in recs)
                {
                    bw.Write(r.t);
                    bw.Write(r.p.x); bw.Write(r.p.y); bw.Write(r.p.z);
                    bw.Write(r.yaw); bw.Write(r.s);
                    bw.Write(r.up.x); bw.Write(r.up.y); bw.Write(r.up.z);
                }
            }
            AssetDatabase.ImportAsset(dataPath);
            var field = root.AddComponent<PropField>();
            field.data = AssetDatabase.LoadAssetAtPath<TextAsset>(dataPath);

            // monumentos de horizonte: mesas, buttes e agulhas com o material de geologia (relevo e skyline variados)
            var main = g.Main.Data;
            var mons = new[] { ("P_Mesa_A", 330f), ("P_Mesa_B", 240f), ("P_Butte_A", 85f), ("P_Butte_B", 62f), ("P_Spire_A", 22f), ("P_Spire_B", 16f) };
            int placed = 0;
            var holder = new GameObject("LANDMARKS").transform;
            holder.SetParent(root.transform, false);
            var giants = new[] { ("P_Mesa_A", 330f), ("P_Mesa_B", 240f) };
            float nextGiant = 1500f;
            for (float dist = 400f; dist < main.Length; dist += Rng(450f, 1100f))
            {
                main.Locate(dist, out int i, out _);
                int side = R01() < 0.5f ? -1 : 1;
                bool giant = dist >= nextGiant;
                if (giant) nextGiant = dist + Rng(3500f, 6000f);
                var (type, rad) = giant ? giants[rnd.Next(giants.Length)] : mons[rnd.Next(mons.Length)];
                float sc = giant ? Rng(2.5f, 4f) : type.StartsWith("P_Spire") ? Rng(1f, 2.2f) : Rng(1.2f, 3f);
                float lat = giant ? Rng(2600f, 3800f) : Rng(Mathf.Max(350f, rad * sc * 1.6f), 2400f);
                var c = main.Center[i] + main.Right[i] * side * lat + main.Tangent[i] * Rng(-200f, 200f);
                bool clear = true;
                foreach (var path in g.Paths)
                {
                    var pd = path.Data;
                    for (int j = 0; j < pd.StationCount && clear; j += 8)
                    {
                        var o = pd.Center[j] - c; o.y = 0f;
                        if (o.magnitude < rad * sc * 1.3f + 160f) clear = false;
                    }
                }
                if (!clear) continue;
                float y = Physics.Raycast(new Vector3(c.x, main.Center[i].y + 3000f, c.z), Vector3.down, out var gh, 7000f, Layers.GroundMask) ? gh.point.y - 8f : main.Center[i].y - 40f;
                var src = kit.transform.Find(type);
                if (src == null) continue;
                var go = (GameObject)UnityEngine.Object.Instantiate(src.gameObject, holder);
                go.name = $"LANDMARK_{type}_{placed}";
                go.transform.position = new Vector3(c.x, y, c.z);
                go.transform.rotation = Quaternion.Euler(0f, Rng(0f, 360f), 0f) * src.localRotation;
                go.transform.localScale = src.localScale * sc;
                var mr = go.GetComponent<MeshRenderer>();
                if (mr != null) { mr.sharedMaterial = geo; mr.shadowCastingMode = ShadowCastingMode.On; }
                placed++;
            }
            int rivers = Rivers(name, spec, root, holder, g, recs, ride, Put, Rng, R01);
            int megas = Megastructures(g, holder, ZoneAt, Rng, R01);
            // reescreve os dados com a vegetação das margens dos rios
            using (var bw = new BinaryWriter(File.Create(dataPath)))
            {
                bw.Write(recs.Count);
                foreach (var r in recs)
                {
                    bw.Write(r.t);
                    bw.Write(r.p.x); bw.Write(r.p.y); bw.Write(r.p.z);
                    bw.Write(r.yaw); bw.Write(r.s);
                    bw.Write(r.up.x); bw.Write(r.up.y); bw.Write(r.up.z);
                }
            }
            AssetDatabase.ImportAsset(dataPath);
            field.data = AssetDatabase.LoadAssetAtPath<TextAsset>(dataPath);
            Debug.Log($"[RDD] paisagem: {recs.Count} adereços (vegetação, cactos, pedregulhos) · {placed} monumentos no horizonte · {rivers} rios · {megas} megaestruturas · zonas: {string.Join(", ", sectors.Select(x => x.id + "=" + ZoneOfSector(x.id)))}");
        }

        /// <summary>
        /// Rios no fundo das gargantas (features "gorge_along" do JSON): fita de água que segue o fundo, com o nível
        /// suavizado, e margens verdes (choupos, arbustos e erva verde) dos dois lados.
        /// </summary>
        static int Rivers(string name, string spec, GameObject root, Transform holder, CourseGraph g, List<(byte t, Vector3 p, float yaw, float s, Vector3 up)> recs,
                          RideIndex ride, System.Action<string, RaycastHit, bool> put, System.Func<float, float, float> rng, System.Func<float> r01)
        {
            if (!File.Exists(spec)) return 0;
            const string waterPath = "Assets/RedDust/Resources/Props/Water.mat";
            var water = AssetDatabase.LoadAssetAtPath<Material>(waterPath);
            if (water == null)
            {
                water = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                water.SetColor("_BaseColor", new Color(0.16f, 0.34f, 0.32f));
                water.SetFloat("_Smoothness", 0.93f);
                water.SetFloat("_Metallic", 0f);
                AssetDatabase.CreateAsset(water, waterPath);
            }
            var d = g.Main.Data;
            int made = 0;
            foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(File.ReadAllText(spec),
                     "\"type\":\\s*\"gorge_along\"[^}]*?\"from\":\\s*([0-9.]+),\\s*\"to\":\\s*([0-9.]+),\\s*\"side\":\\s*(-?[0-9]+),\\s*\"offset\":\\s*([0-9.]+),\\s*\"depth\":\\s*([0-9.]+),\\s*\"half_width\":\\s*([0-9.]+)"))
            {
                var ci = System.Globalization.CultureInfo.InvariantCulture;
                float a = float.Parse(m.Groups[1].Value, ci), b = float.Parse(m.Groups[2].Value, ci);
                int side = int.Parse(m.Groups[3].Value, ci);
                float off = float.Parse(m.Groups[4].Value, ci), half = float.Parse(m.Groups[6].Value, ci);
                var pts = new List<Vector3>();
                var rights = new List<Vector3>();
                for (float dist = a + 60f; dist < b - 60f; dist += 18f)
                {
                    d.Locate(dist, out int i, out _);
                    var c = d.Center[i] + d.Right[i] * side * off;
                    if (!Physics.Raycast(c + Vector3.up * 600f, Vector3.down, out var hit, 1500f, Layers.GroundMask, QueryTriggerInteraction.Ignore)) continue;
                    pts.Add(hit.point);
                    var rh = d.Right[i]; rh.y = 0f;
                    rights.Add(rh.normalized);
                }
                if (pts.Count < 8) continue;
                // nível da água: mínimo local suavizado + 1,2 m (a água não sobe encostas)
                var lvl = new float[pts.Count];
                for (int k = 0; k < pts.Count; k++)
                {
                    float mn = float.MaxValue;
                    for (int q = Mathf.Max(0, k - 4); q <= Mathf.Min(pts.Count - 1, k + 4); q++) mn = Mathf.Min(mn, pts[q].y);
                    lvl[k] = mn + 1.2f;
                }
                var verts = new List<Vector3>();
                var tris = new List<int>();
                float w = half * 0.75f;
                for (int k = 0; k < pts.Count; k++)
                {
                    var c = new Vector3(pts[k].x, lvl[k], pts[k].z);
                    verts.Add(c - rights[k] * w);
                    verts.Add(c + rights[k] * w);
                    if (k > 0)
                    {
                        int o = verts.Count - 4;
                        tris.AddRange(new[] { o, o + 2, o + 1, o + 1, o + 2, o + 3 });
                    }
                }
                var mesh = new Mesh { name = $"River_{name}_{made}", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
                mesh.SetVertices(verts);
                mesh.SetTriangles(tris, 0);
                mesh.RecalculateNormals();
                mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, $"Assets/RedDust/Generated/{name}_colliders/river_{made}.asset");
                var go = new GameObject($"RIVER_{made}");
                go.transform.SetParent(holder, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = water;
                mr.shadowCastingMode = ShadowCastingMode.Off;
                // margens verdes
                for (int k = 0; k < pts.Count; k++)
                    for (int sd = -1; sd <= 1; sd += 2)
                        for (int n = 0; n < 3; n++)
                        {
                            var p0 = new Vector3(pts[k].x, lvl[k], pts[k].z) + rights[k] * sd * (w + rng(0.5f, 18f)) + new Vector3(rng(-8f, 8f), 0f, rng(-8f, 8f));
                            if (!Physics.Raycast(p0 + Vector3.up * 40f, Vector3.down, out var hit, 90f, Layers.GroundMask, QueryTriggerInteraction.Ignore)) continue;
                            if (hit.normal.y < 0.55f || hit.point.y < lvl[k] - 0.3f) continue;
                            float x = r01();
                            put(x < 0.25f ? "P_Tree_A" : x < 0.4f ? "P_Tree_B" : x < 0.65f ? "P_Bush_Green" : "P_Grass_Green", hit, false);
                        }
                made++;
            }
            return made;
        }

        static Material MegaMat(string n)
        {
            string path = $"Assets/RedDust/Resources/Props/{n}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m != null) return m;
            m = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            (Color c, float met, float sm) = n == "Mega_Metal" ? (new Color(0.42f, 0.44f, 0.47f), 0.6f, 0.45f) : n == "Mega_Rust" ? (new Color(0.47f, 0.25f, 0.14f), 0.2f, 0.25f)
                : n == "Mega_Dark" ? (new Color(0.12f, 0.12f, 0.13f), 0.5f, 0.35f) : n == "Mega_Cloth" ? (new Color(0.62f, 0.08f, 0.06f), 0f, 0.1f) : (new Color(1f, 0.55f, 0.2f), 0f, 0.5f);
            m.SetColor("_BaseColor", c);
            m.SetFloat("_Metallic", met);
            m.SetFloat("_Smoothness", sm);
            if (n == "Mega_Glow") { m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", new Color(1f, 0.55f, 0.2f) * 3f); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None; }
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        /// <summary>
        /// Megaestruturas (referências de gameplay): pórticos gigantes sobre a pista no início de cada sector (pilares fora
        /// da pista, com colisão), anéis de naves e cascos despenhados, torres industriais e tubagens ao lado da pista.
        /// </summary>
        static int Megastructures(CourseGraph g, Transform holder, System.Func<float, string> zoneAt, System.Func<float, float, float> rng, System.Func<float> r01)
        {
            var kit = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/RedDust/Resources/Props/mega_kit.fbx");
            if (kit == null) return 0;
            var d = g.Main.Data;
            int made = 0;
            GameObject Spawn(string type, Vector3 pos, Quaternion rot, Vector3 scale, bool collide)
            {
                var src = kit.transform.Find(type);
                if (src == null) return null;
                var go = (GameObject)UnityEngine.Object.Instantiate(src.gameObject, holder);
                go.name = $"MEGA_{type}_{made++}";
                go.transform.position = pos;
                go.transform.rotation = rot * src.localRotation;
                go.transform.localScale = Vector3.Scale(src.localScale, scale);
                var mr = go.GetComponent<MeshRenderer>();
                if (mr != null)
                {
                    var mats = mr.sharedMaterials;
                    for (int i = 0; i < mats.Length; i++) mats[i] = MegaMat(mats[i] != null ? mats[i].name.Replace(" (Instance)", "") : "Mega_Metal");
                    mr.sharedMaterials = mats;
                    mr.shadowCastingMode = ShadowCastingMode.On;
                }
                if (collide) go.AddComponent<MeshCollider>().sharedMesh = go.GetComponent<MeshFilter>().sharedMesh;
                return go;
            }
            bool Clear(Vector3 c, float rad)
            {
                foreach (var path in g.Paths)
                    for (int j = 0; j < path.Data.StationCount; j += 6)
                    {
                        var o = path.Data.Center[j] - c; o.y = 0f;
                        if (o.magnitude < rad) return false;
                    }
                return true;
            }
            float Ground(Vector3 c, float fallback) => Physics.Raycast(c + Vector3.up * 2000f, Vector3.down, out var h, 5000f, Layers.GroundMask) ? h.point.y : fallback;

            // pórticos sobre a pista: de 7 em 7 km, num troço quase a direito
            for (float dist = 3000f; dist < d.Length - 2000f; dist += rng(6000f, 8500f))
            {
                for (float t = 0f; t < 1200f; t += 60f)
                {
                    d.Locate(dist + t, out int i, out _);
                    d.Locate(dist + t + 120f, out int j, out _);
                    if (d.IsGap(i) || d.IsCave(i) || Vector3.Angle(d.Tangent[i], d.Tangent[j]) > 6f) continue;
                    float span = d.RideLeft[i] + d.RideRight[i] + 50f;
                    if (span > 220f) continue;
                    var right = d.Right[i]; right.y = 0f; right.Normalize();
                    var fwd = Vector3.Cross(right, Vector3.up);
                    var mid = d.Center[i] + right * ((d.RideRight[i] - d.RideLeft[i]) * 0.5f);
                    Spawn("M_Gate", new Vector3(mid.x, d.Center[i].y - 4f, mid.z), Quaternion.LookRotation(fwd, Vector3.up), new Vector3(span / 130f, 1f, 1f), true);
                    break;
                }
            }
            // ao lado da pista: anéis, cascos, torres e tubagens (longe das linhas de corrida)
            for (float dist = 1500f; dist < d.Length; dist += rng(2200f, 3800f))
            {
                d.Locate(dist, out int i, out _);
                string zone = zoneAt(dist);
                int side = r01() < 0.5f ? -1 : 1;
                var right = d.Right[i]; right.y = 0f; right.Normalize();
                float x = r01();
                string type = zone == "green" ? (x < 0.6f ? "M_Tower_A" : "M_Pipeline") : x < 0.28f ? "M_Ring" : x < 0.52f ? "M_Hull" : x < 0.8f ? (r01() < 0.5f ? "M_Tower_A" : "M_Tower_B") : "M_Pipeline";
                float rad = type == "M_Ring" ? 90f : type == "M_Hull" ? 110f : type == "M_Pipeline" ? 120f : 50f;
                float lat = type == "M_Pipeline" ? rng(70f, 160f) : rng(170f, 650f);
                var c = d.Center[i] + right * side * lat;
                if (!Clear(c, rad + 40f)) continue;
                float gy = Ground(c, d.Center[i].y);
                var tang = d.Tangent[i]; tang.y = 0f; tang.Normalize();
                var yaw = Quaternion.LookRotation(type == "M_Pipeline" ? tang : Quaternion.Euler(0f, rng(0f, 360f), 0f) * tang, Vector3.up);
                if (type == "M_Ring") Spawn(type, new Vector3(c.x, gy - 18f, c.z), yaw, Vector3.one * rng(0.9f, 1.3f), false);
                else if (type == "M_Hull") Spawn(type, new Vector3(c.x, gy - 7f, c.z), yaw * Quaternion.Euler(rng(-6f, 6f), 0f, rng(8f, 20f)), Vector3.one * rng(0.8f, 1.2f), false);
                else Spawn(type, new Vector3(c.x, gy - 1f, c.z), yaw, Vector3.one * rng(0.8f, 1.2f), false);
            }
            return made;
        }

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
