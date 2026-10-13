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
                cam.transform.position = d.Center[i] - d.Tangent[i] * CommandLine.Float("-camback", 22f) + d.Up[i] * CommandLine.Float("-camup", 9f);
                cam.transform.rotation = Quaternion.LookRotation(d.Center[Mathf.Min(d.StationCount - 1, i + 8)] - cam.transform.position, d.Up[i]);
                var rt = new RenderTexture(1280, 720, 24);
                cr.GetComponent<PropField>()?.DrawAround(cam.transform.position);
                cam.targetTexture = rt; cam.Render(); cam.targetTexture = null;
                RenderTexture.active = rt;
                var tex = new Texture2D(1280, 720, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, 1280, 720), 0, 0); tex.Apply();
                RenderTexture.active = null;
                File.WriteAllBytes(Path.Combine("Logs", $"probe_{tok}.png"), tex.EncodeToPNG());
            }
            Debug.Log("[RDD probe] fotos OK");
        }

        /// <summary>Fotografa as megaestruturas já colocadas na pista (uma de cada tipo): Logs/mega_&lt;tipo&gt;.png.</summary>
        public static void MegaShots()
        {
            string name = CourseImporter.CourseArg;
            ProjectSetup.ConfigureUrp();
            EditorSceneManager.OpenScene(CourseImporter.ScenePathFor(name));
            var cr = Object.FindFirstObjectByType<CourseRuntime>();
            foreach (var t in cr.GetComponentsInChildren<Transform>(true)) t.gameObject.SetActive(true);
            RedDust.Presentation.EnvironmentRig.Apply(Object.FindFirstObjectByType<Light>(), false);
            var cam = new GameObject("MegaCam").AddComponent<Camera>();
            cam.fieldOfView = 55f; cam.nearClipPlane = 0.5f; cam.farClipPlane = 8000f;
            cam.gameObject.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
            var done = new HashSet<string>();
            var d = cr.Graph.Main.Data;
            foreach (var mr in cr.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (!mr.name.StartsWith("MEGA_")) continue;
                string type = mr.name.Substring(5, mr.name.LastIndexOf('_') - 5);
                if (!done.Add(type)) continue;
                var b = mr.bounds;
                // câmara do lado da pista mais próxima, um pouco acima, a enquadrar a estrutura
                int best = 0; float bd = float.MaxValue;
                for (int i = 0; i < d.StationCount; i += 4) { float q = (d.Center[i] - b.center).sqrMagnitude; if (q < bd) { bd = q; best = i; } }
                var from = d.Center[best] + Vector3.up * 6f;
                var dir = (b.center - from); dir.y = 0f;
                float dist = Mathf.Max(b.extents.magnitude * 2.2f, 60f);
                cam.transform.position = b.center - dir.normalized * dist + Vector3.up * (b.extents.y * 0.35f + 8f);
                cam.transform.LookAt(b.center);
                cr.GetComponent<PropField>()?.DrawAround(cam.transform.position);
                var rt = new RenderTexture(1280, 720, 24);
                cam.targetTexture = rt; cam.Render(); cam.targetTexture = null;
                RenderTexture.active = rt;
                var tex = new Texture2D(1280, 720, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, 1280, 720), 0, 0); tex.Apply();
                RenderTexture.active = null;
                File.WriteAllBytes(Path.Combine("Logs", $"mega_{type}.png"), tex.EncodeToPNG());
            }
            Debug.Log($"[RDD probe] megaestruturas fotografadas: {string.Join(", ", done)}");
        }

        /// <summary>Perfil do piso entre -from e -to (km): altura prevista vs malha real e paredes à frente (Logs/track_profile.txt).</summary>
        public static void Profile()
        {
            string name = CourseImporter.CourseArg;
            EditorSceneManager.OpenScene(CourseImporter.ScenePathFor(name));
            var cr = Object.FindFirstObjectByType<CourseRuntime>();
            foreach (var t in cr.GetComponentsInChildren<Transform>(true)) t.gameObject.SetActive(true);
            Physics.SyncTransforms();
            var d = cr.Graph.Main.Data;
            float a = CommandLine.Float("-from", 14.2f) * 1000f, b = CommandLine.Float("-to", 15.1f) * 1000f;
            var lines = new List<string> { "km      prev_y   malha_y  dif    parede_a_frente(m)@altura" };
            for (int i = 0; i < d.StationCount; i++)
            {
                if (d.Dist[i] < a || d.Dist[i] > b || i % 2 != 0) continue;
                var c = d.LanePoint(i, 0f);
                float my = Physics.Raycast(c + d.Up[i] * 40f, -d.Up[i], out var h, 80f, Layers.GroundMask) ? h.point.y : float.NaN;
                string wall = "";
                foreach (float z in new[] { 0.8f, 1.6f, 3f })
                    if (Physics.Raycast(c + d.Up[i] * z, d.Tangent[i], out var w, 25f, Layers.GroundMask) && Vector3.Dot(w.normal, d.Up[i]) < 0.5f)
                        wall += $" {w.distance:0}m@{z:0.0}";
                lines.Add($"{d.Dist[i] / 1000f:0.000}  {c.y,7:0.00}  {my,7:0.00}  {my - c.y,5:0.00}  {wall}");
            }
            File.WriteAllLines(Path.Combine("Logs", "track_profile.txt"), lines);
            Debug.Log("[RDD probe] perfil OK");
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
