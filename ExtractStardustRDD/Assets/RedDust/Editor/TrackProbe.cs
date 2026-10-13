using System.Collections.Generic;
using System.IO;
using System.Linq;
using RedDust.Track;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace RedDust.EditorTools
{
    /// <summary>
    /// Sonda a zona de corrida de todos os percursos com raios de cima para baixo: DEGRAU = superfície que fica entre
    /// 0,35 m e 3 m acima do chão previsto (a nave bate/prende), BURACO = nada até 2 m abaixo. Agrupa em troços e
    /// escreve Logs/track_probe_&lt;pista&gt;.txt com a malha culpada de cada troço.
    /// </summary>
    public static class TrackProbe
    {
        [MenuItem("Red Dust/8. Sondar pista")]
        public static void Run()
        {
            string name = CourseImporter.CourseArg;
            EditorSceneManager.OpenScene(CourseImporter.ScenePathFor(name));
            var cr = Object.FindFirstObjectByType<CourseRuntime>();
            foreach (var s in Object.FindObjectsByType<SectorStreamer>(FindObjectsInactive.Include, FindObjectsSortMode.None)) s.enabled = false;
            foreach (var t in cr.GetComponentsInChildren<Transform>(true)) t.gameObject.SetActive(true);
            Physics.SyncTransforms();
            var graph = cr.Graph;
            var lines = new List<string>();
            int totalBad = 0, totalHoles = 0, totalSamples = 0;
            foreach (var path in graph.Paths)
            {
                var d = path.Data;
                var events = new List<(float dist, string kind, string mesh, float dy)>();
                int samples = 0;
                for (int i = 1; i < d.StationCount - 1; i++)
                {
                    if (d.IsGap(i)) continue;
                    for (float u = -0.9f; u <= 0.91f; u += 0.15f)
                    {
                        var lp = d.LanePoint(i, u);
                        var up = d.Up[i];
                        samples++;
                        var hits = Physics.RaycastAll(lp + up * 3f, -up, 5f, Layers.GroundMask, QueryTriggerInteraction.Ignore);
                        if (hits.Length == 0) { events.Add((d.Dist[i], "BURACO", "-", 0f)); continue; }
                        var top = hits.OrderBy(h => h.distance).First();
                        float above = 3f - top.distance;
                        if (above > 0.35f) events.Add((d.Dist[i], "DEGRAU", top.collider.name, above));
                    }
                }
                totalSamples += samples;
                int bad = events.Count(e => e.kind == "DEGRAU"), holes = events.Count(e => e.kind == "BURACO");
                totalBad += bad; totalHoles += holes;
                lines.Add($"PERCURSO {path.Id}: {d.Length / 1000f:0.0} km · {samples} amostras · degraus {bad} · buracos {holes}");
                // agrupa em troços (eventos a menos de 60 m uns dos outros)
                foreach (var g in Cluster(events.OrderBy(e => e.dist).ToList(), 60f))
                {
                    var meshes = g.GroupBy(e => e.mesh).OrderByDescending(x => x.Count()).Take(3).Select(x => $"{x.Key}×{x.Count()}");
                    lines.Add($"  {g[0].dist / 1000f:0.000}-{g[g.Count - 1].dist / 1000f:0.000} km · {g.Count(e => e.kind == "DEGRAU")} degraus (máx {g.Max(e => e.dy):0.0} m) · {g.Count(e => e.kind == "BURACO")} buracos · {string.Join(", ", meshes)}");
                }
            }
            lines.Insert(0, $"[RDD probe] {name}: {totalSamples} amostras · degraus {totalBad} ({100f * totalBad / Mathf.Max(1, totalSamples):0.00}%) · buracos {totalHoles}");
            Directory.CreateDirectory("Logs");
            File.WriteAllLines(Path.Combine("Logs", $"track_probe_{name}.txt"), lines);
            Debug.Log(lines[0]);
        }

        /// <summary>Fotografias da pista em distâncias (km) dadas por -at "15.0,39.3": câmara atrás e acima do centro.</summary>
        public static void Shots()
        {
            string name = CourseImporter.CourseArg;
            ProjectSetup.ConfigureUrp();
            EditorSceneManager.OpenScene(CourseImporter.ScenePathFor(name));
            var cr = Object.FindFirstObjectByType<CourseRuntime>();
            foreach (var s in Object.FindObjectsByType<SectorStreamer>(FindObjectsInactive.Include, FindObjectsSortMode.None)) s.enabled = false;
            foreach (var t in cr.GetComponentsInChildren<Transform>(true)) t.gameObject.SetActive(true);
            var sun = Object.FindFirstObjectByType<Light>();
            RedDust.Presentation.EnvironmentRig.Apply(sun, false);
            var d = cr.Graph.Main.Data;
            var cam = new GameObject("ProbeCam").AddComponent<Camera>();
            cam.fieldOfView = 60f; cam.nearClipPlane = 0.2f; cam.farClipPlane = 4000f;
            cam.gameObject.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
            foreach (var tok in CommandLine.Value("-at", "15.0").Split(','))
            {
                float km = float.Parse(tok, System.Globalization.CultureInfo.InvariantCulture);
                int i = 0;
                while (i < d.StationCount - 1 && d.Dist[i] < km * 1000f) i++;
                cam.transform.position = d.Center[i] - d.Tangent[i] * 16f + d.Up[i] * 6f;
                cam.transform.rotation = Quaternion.LookRotation(d.Center[Mathf.Min(d.StationCount - 1, i + 8)] - cam.transform.position, d.Up[i]);
                var rt = new RenderTexture(1280, 720, 24);
                cam.targetTexture = rt; cam.Render(); cam.targetTexture = null;
                RenderTexture.active = rt;
                var tex = new Texture2D(1280, 720, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, 1280, 720), 0, 0); tex.Apply();
                RenderTexture.active = null;
                File.WriteAllBytes(Path.Combine("Logs", $"probe_{tok}.png"), tex.EncodeToPNG());
            }
            Debug.Log("[RDD probe] fotos OK");
        }

        static IEnumerable<List<(float dist, string kind, string mesh, float dy)>> Cluster(List<(float dist, string kind, string mesh, float dy)> ev, float gap)
        {
            var cur = new List<(float, string, string, float)>();
            foreach (var e in ev)
            {
                if (cur.Count > 0 && e.dist - cur[cur.Count - 1].Item1 > gap) { yield return cur; cur = new List<(float, string, string, float)>(); }
                cur.Add(e);
            }
            if (cur.Count > 0) yield return cur;
        }
    }
}
