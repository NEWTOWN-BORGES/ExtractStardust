using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace RedDust.EditorTools
{
    /// <summary>Builds Windows/Android e o pipeline completo do M1 em modo batch.</summary>
    public static class BuildTools
    {
        [MenuItem("Red Dust/4. Build Windows")]
        public static void BuildWindows()
        {
            int code = Build(BuildTarget.StandaloneWindows64, CommandLine.Value("-buildDir", "Builds/Windows").TrimEnd('/', '\\') + "/RedDustDivide.exe");
            if (Application.isBatchMode) EditorApplication.Exit(code);
        }

        [MenuItem("Red Dust/5. Build Android (APK)")]
        public static void BuildAndroid()
        {
            EditorUserBuildSettings.buildAppBundle = false;
            int code = Build(BuildTarget.Android, "Builds/Android/RedDustDivide.apk", AndroidScenes());
            if (Application.isBatchMode) EditorApplication.Exit(code);
        }

        /// <summary>
        /// Android: só o laboratório (26 km). A expedição completa (~106 km, ~730 MB de geologia) precisa de uma versão
        /// móvel com menos resolução antes de caber na memória de um telemóvel; -androidAll força todas as pistas.
        /// </summary>
        static string[] AndroidScenes() =>
            CommandLine.Has("-androidAll") ? CourseImporter.AllScenes() : CourseImporter.AllScenes().Where(s => s.EndsWith("RDD_Sandbox.unity")).ToArray();

        static int Build(BuildTarget target, string path, string[] scenes = null)
        {
            var opts = new BuildPlayerOptions
            {
                scenes = scenes ?? CourseImporter.AllScenes(),
                locationPathName = path,
                target = target,
                options = BuildOptions.None,
            };
            var report = BuildPipeline.BuildPlayer(opts);
            var s = report.summary;
            Debug.Log($"[RDD] build {target}: {s.result} · {s.totalSize / (1024f * 1024f):0.0} MB · {s.totalTime} · erros {s.totalErrors}");
            return s.result == BuildResult.Succeeded ? 0 : 1;
        }

        /// <summary>Pipeline do laboratório: importa a geologia, monta a cena e compila o Windows.</summary>
        public static void ImportAndBuildWindows()
        {
            CourseImporter.ImportAndBuild("sandbox");
            int code = Build(BuildTarget.StandaloneWindows64, "Builds/Windows/RedDustDivide.exe");
            if (Application.isBatchMode) EditorApplication.Exit(code);
        }
    }
}
