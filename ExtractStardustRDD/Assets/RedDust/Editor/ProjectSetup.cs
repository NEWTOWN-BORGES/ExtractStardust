using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RedDust.EditorTools
{
    /// <summary>Configuração única do projeto: player (PC/Android), Input System, camadas, física e materiais base.</summary>
    public static class ProjectSetup
    {
        public const string MaterialsDir = "Assets/RedDust/Materials";
        public const string ResourcesDir = "Assets/RedDust/Resources/RedDust";

        [MenuItem("Red Dust/1. Setup do projeto")]
        public static void Setup()
        {
            // ---- player
            PlayerSettings.companyName = "Stardust League";
            PlayerSettings.productName = "EXTRACT STARDUST - Red Dust Divide";
            PlayerSettings.bundleVersion = "0.1.0";
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, "com.stardustleague.reddust");
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Standalone, "com.stardustleague.reddust");
            PlayerSettings.Android.bundleVersionCode = 1;
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel28;
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.Vulkan, GraphicsDeviceType.OpenGLES3 });
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true;
            PlayerSettings.allowedAutorotateToLandscapeRight = true;
            PlayerSettings.allowedAutorotateToPortrait = false;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.runInBackground = true;
            PlayerSettings.SplashScreen.show = false;
            PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow;
            PlayerSettings.resizableWindow = true;
            PlayerSettings.enableFrameTimingStats = true;
            // muito do mundo é criado por código: o IL2CPP não pode remover módulos do motor "não usados"
            // (lição do jogo anterior: TerrainCollider removido = naves a cair no Android)
            PlayerSettings.stripEngineCode = false;

            var ps = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset");
            if (ps.Length > 0)
            {
                var so = new SerializedObject(ps[0]);
                var p = so.FindProperty("activeInputHandler");
                if (p != null) { p.intValue = 1; so.ApplyModifiedPropertiesWithoutUndo(); }   // só o novo Input System
            }

            // ---- camadas
            var tm = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
            var layers = tm.FindProperty("layers");
            void L(int i, string n) { layers.GetArrayElementAtIndex(i).stringValue = n; }
            L(Layers.Ground, "Ground"); L(Layers.Obstacle, "Obstacle"); L(Layers.Craft, "Craft"); L(Layers.Checkpoint, "Checkpoint");
            tm.ApplyModifiedPropertiesWithoutUndo();

            // ---- física: checkpoints só interagem com naves
            for (int i = 0; i < 32; i++)
                Physics.IgnoreLayerCollision(Layers.Checkpoint, i, i != Layers.Craft);
            var dm = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/DynamicsManager.asset")[0]);
            var it = dm.FindProperty("m_DefaultSolverIterations"); if (it != null) it.intValue = 8;
            var itv = dm.FindProperty("m_DefaultSolverVelocityIterations"); if (itv != null) itv.intValue = 2;
            dm.ApplyModifiedPropertiesWithoutUndo();

            // a física corre sozinha no passo fixo (as ferramentas de teste usam modo manual só temporariamente)
            Physics.simulationMode = SimulationMode.FixedUpdate;

            // ---- tempo: passo fixo de 1/90 s (TARGET de tuning do M1)
            Time.fixedDeltaTime = 1f / 90f;
            Time.maximumDeltaTime = 0.1f;
            var time = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TimeManager.asset")[0]);
            var count = time.FindProperty("Fixed Timestep.m_Count");
            var num = time.FindProperty("Fixed Timestep.m_Rate.m_Numerator");
            var den = time.FindProperty("Fixed Timestep.m_Rate.m_Denominator");
            if (count != null && num != null && den != null)
            {
                num.longValue = 141120000; den.longValue = 1; count.longValue = 141120000 / 90;
                time.ApplyModifiedPropertiesWithoutUndo();
            }

            // ---- materiais
            Directory.CreateDirectory(MaterialsDir);
            Directory.CreateDirectory(ResourcesDir);
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            Mat($"{ResourcesDir}/CraftPaint.mat", lit, m => { m.SetColor("_BaseColor", new Color(0.72f, 0.08f, 0.06f)); m.SetFloat("_Metallic", 0.25f); m.SetFloat("_Smoothness", 0.62f); });
            Mat($"{ResourcesDir}/CraftMetal.mat", lit, m => { m.SetColor("_BaseColor", new Color(0.09f, 0.1f, 0.11f)); m.SetFloat("_Metallic", 0.85f); m.SetFloat("_Smoothness", 0.45f); });
            Mat($"{ResourcesDir}/CraftGlass.mat", lit, m => { m.SetColor("_BaseColor", new Color(0.04f, 0.07f, 0.1f)); m.SetFloat("_Metallic", 0.1f); m.SetFloat("_Smoothness", 0.93f); });
            Mat($"{ResourcesDir}/CraftGlow.mat", lit, m =>
            {
                m.SetColor("_BaseColor", Color.black);
                m.EnableKeyword("_EMISSION");
                m.SetColor("_EmissionColor", new Color(0.35f, 0.85f, 1f) * 2.2f);
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            });
            Mat($"{ResourcesDir}/DebugLines.mat", Shader.Find("RedDust/DebugLines"), null);
            // efeitos de velocidade: aditivo (riscos, faíscas, chama) e transparente (pó)
            var fx = Shader.Find("RedDust/FxParticle");
            Mat($"{ResourcesDir}/FxAdd.mat", fx, m => { m.SetFloat("_Src", (float)BlendMode.SrcAlpha); m.SetFloat("_Dst", (float)BlendMode.One); m.SetFloat("_Soft", 1.5f); });
            Mat($"{ResourcesDir}/FxDust.mat", fx, m => { m.SetFloat("_Src", (float)BlendMode.SrcAlpha); m.SetFloat("_Dst", (float)BlendMode.OneMinusSrcAlpha); m.SetFloat("_Soft", 2.2f); });
            Mat($"{MaterialsDir}/Geology.mat", Shader.Find("RedDust/Geology"), null);
            // destroços de naves de extração caídas no canyon (metal escuro gasto)
            Mat($"{MaterialsDir}/WreckMetal.mat", lit, m => { m.SetColor("_BaseColor", new Color(0.36f, 0.25f, 0.18f)); m.SetFloat("_Metallic", 0.55f); m.SetFloat("_Smoothness", 0.28f); });
            Mat($"{MaterialsDir}/SkyRDD.mat", Shader.Find("RedDust/Sky"), null);
            Mat($"{MaterialsDir}/SkyDesert.mat", Shader.Find("Skybox/Procedural"), m =>
            {
                m.SetFloat("_SunSize", 0.035f);
                m.SetFloat("_SunSizeConvergence", 6f);
                m.SetFloat("_AtmosphereThickness", 0.82f);
                m.SetColor("_SkyTint", new Color(0.5f, 0.55f, 0.62f));
                m.SetColor("_GroundColor", new Color(0.42f, 0.3f, 0.24f));
                m.SetFloat("_Exposure", 1.25f);
            });
            ConfigureUrp();
            AssetDatabase.SaveAssets();
            Debug.Log("[RDD] setup concluído");
        }

        /// <summary>Perfis URP: PC com sombras longas (canyons a 450 km/h), Android curto e barato.</summary>
        public static void ConfigureUrp()
        {
            var pc = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>("Assets/Settings/PC_RPAsset.asset");
            if (pc != null)
            {
                pc.shadowDistance = 600f;
                pc.shadowCascadeCount = 4;
                pc.cascade4Split = new Vector3(0.04f, 0.13f, 0.34f);
                pc.mainLightShadowmapResolution = 4096;
                EditorUtility.SetDirty(pc);
            }
            var mobile = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>("Assets/Settings/Mobile_RPAsset.asset");
            if (mobile != null)
            {
                mobile.shadowDistance = 120f;
                mobile.shadowCascadeCount = 2;
                mobile.mainLightShadowmapResolution = 1024;
                EditorUtility.SetDirty(mobile);
            }
            AssetDatabase.SaveAssets();
        }

        static Material Mat(string path, Shader shader, System.Action<Material> init)
        {
            if (shader == null) { Debug.LogError($"[RDD] shader em falta para {path}"); return null; }
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                m = new Material(shader);
                AssetDatabase.CreateAsset(m, path);
            }
            m.shader = shader;
            init?.Invoke(m);
            EditorUtility.SetDirty(m);
            return m;
        }
    }
}
