using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace Stardust.EditorTools
{
    public static class StardustTools
    {
        const string ScenePath = "Assets/Stardust/Scenes/Main.unity";

        static void Folder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            var parent = Path.GetDirectoryName(path).Replace('\\', '/');
            Folder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }

        static Material Mat(string path, string shader, System.Action<Material> cfg)
        {
            var sh = Shader.Find(shader);
            if (sh == null) { Debug.LogError("Shader not found: " + shader); return null; }
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                m = new Material(sh);
                AssetDatabase.CreateAsset(m, path);
            }
            m.shader = sh;
            cfg?.Invoke(m);
            EditorUtility.SetDirty(m);
            return m;
        }

        [MenuItem("Stardust/1. Setup Project")]
        public static void Setup()
        {
            Folder("Assets/Resources/Stardust");
            Folder("Assets/Stardust/Scenes");
            Mat("Assets/Resources/Stardust/VertexLit.mat", "Stardust/VertexLit", null);
            Mat("Assets/Resources/Stardust/Additive.mat", "Stardust/Particle", m => { m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.One); m.SetFloat("_FogToBlack", 1f); });
            Mat("Assets/Resources/Stardust/AlphaBlend.mat", "Stardust/Particle", m => { m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha); m.SetFloat("_FogToBlack", 0f); });
            var sky = Mat("Assets/Resources/Stardust/Sky.mat", "Stardust/Sky", null);

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogStartDistance = 120f;
            RenderSettings.fogEndDistance = 700f;
            RenderSettings.fogColor = new Color(0.9f, 0.68f, 0.48f);
            RenderSettings.skybox = sky;
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = Color.gray;
            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };

            PlayerSettings.companyName = "Stardust Port";
            PlayerSettings.productName = "EXTRACT STARDUST";
            PlayerSettings.bundleVersion = "0.1.0";
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, "com.stardustport.extract");
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Standalone, "com.stardustport.extract");
            PlayerSettings.Android.bundleVersionCode = 1;
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = (AndroidSdkVersions)26;
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true;
            PlayerSettings.allowedAutorotateToLandscapeRight = true;
            PlayerSettings.allowedAutorotateToPortrait = false;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow;
            PlayerSettings.resizableWindow = true;
            PlayerSettings.runInBackground = true;
            PlayerSettings.SplashScreen.show = false;
            PlayerSettings.colorSpace = ColorSpace.Linear;

            // new Input System only
            var assets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset");
            if (assets.Length > 0)
            {
                var so = new SerializedObject(assets[0]);
                var p = so.FindProperty("activeInputHandler");
                if (p != null) { p.intValue = 1; so.ApplyModifiedPropertiesWithoutUndo(); }
            }
            AssetDatabase.SaveAssets();
            Debug.Log("[Stardust] Setup complete");
        }

        static int Finish(BuildReport report, string what)
        {
            var s = report.summary;
            Debug.Log($"[Stardust] {what}: {s.result} · {s.totalSize / (1024f * 1024f):0.0} MB · {s.totalTime} · errors {s.totalErrors}");
            return s.result == BuildResult.Succeeded ? 0 : 1;
        }

        [MenuItem("Stardust/2. Build Windows")]
        public static void BuildWindows()
        {
            PlayerSettings.enableFrameTimingStats = true;
            var opts = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = "Builds/Windows/ExtractStardust.exe",
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None,
            };
            int code = Finish(BuildPipeline.BuildPlayer(opts), "Windows");
            if (Application.isBatchMode) EditorApplication.Exit(code);
        }

        [MenuItem("Stardust/3. Build Android APK")]
        public static void BuildAndroid()
        {
            PlayerSettings.Android.forceInternetPermission = true;   // Wi-Fi multiplayer (UDP)
            // o terreno é criado por código: sem isto o IL2CPP remove o módulo TerrainPhysics (TerrainCollider)
            // e as naves atravessam o chão no Android
            PlayerSettings.stripEngineCode = false;
            PlayerSettings.bundleVersion = "0.2.1";
            PlayerSettings.Android.bundleVersionCode = 3;
            EditorUserBuildSettings.buildAppBundle = false;
            var opts = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = "Builds/Android/ExtractStardust.apk",
                target = BuildTarget.Android,
                options = BuildOptions.None,
            };
            int code = Finish(BuildPipeline.BuildPlayer(opts), "Android");
            if (Application.isBatchMode) EditorApplication.Exit(code);
        }

    }
}
