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
            int colliders = 0, tris = 0;
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
                    var mc = mf.gameObject.AddComponent<MeshCollider>();
                    mc.sharedMesh = mf.sharedMesh;
                    colliders++;
                    tris += mf.sharedMesh.triangles.Length / 3;
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
            Debug.Log($"[RDD] cena {scenePath}: {parts.Count} ficheiros, {colliders} colliders, {tris / 1000}k triângulos, percurso {course.Data.Length / 1000f:0.00} km, {course.Graph.BranchCount} ramos");
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
