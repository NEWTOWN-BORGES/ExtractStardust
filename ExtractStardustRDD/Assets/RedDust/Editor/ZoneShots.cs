using System.Collections.Generic;
using System.IO;
using RedDust.Presentation;
using RedDust.Track;
using RedDust.Vehicle;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RedDust.EditorTools
{
    /// <summary>
    /// Fotografias das zonas do percurso renderizadas pelo URP em modo batch (sem janela): câmera de perseguição
    /// e vistas de enquadramento (lateral, aérea, boca da caverna...). Grava em Logs/zonas/*.png.
    /// </summary>
    public static class ZoneShots
    {
        const int W = 1600, H = 900;

        [MenuItem("Red Dust/6. Fotografar zonas")]
        public static void Run()
        {
            ProjectSetup.ConfigureUrp();
            EditorSceneManager.OpenScene(CourseImporter.ScenePathFor(CourseImporter.CourseArg));
            var course = Object.FindFirstObjectByType<CourseRuntime>().Data;
            var sun = Object.FindFirstObjectByType<Light>();
            EnvironmentRig.Apply(sun, false);
            var post = EnvironmentRig.CreatePost(null, false);
            Shader.SetGlobalFloat("_RD_Grid", 0f);
            var prevMode = Physics.simulationMode;
            Physics.simulationMode = SimulationMode.Script;

            var craft = CraftFactory.CreateCore("STRIX", new CraftTuning(), false);
            craft.autoStep = false;
            PlaceholderCraft.Build(craft, new Color(0.72f, 0.08f, 0.06f));
            var camGo = new GameObject("ShotCam");
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.3f; cam.farClipPlane = 14000f;
            var data = camGo.AddComponent<UniversalAdditionalCameraData>();
            data.renderPostProcessing = true;
            data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
            data.antialiasingQuality = AntialiasingQuality.High;
            var chase = camGo.AddComponent<ChaseCamera>();

            string outDir = Path.Combine("Logs", "zonas");
            Directory.CreateDirectory(outDir);
            int Mid(string prefix)
            {
                int a = -1, b = -1;
                for (int i = 0; i < course.StationCount; i++) if (course.SegmentName(i).StartsWith(prefix)) { if (a < 0) a = i; b = i; }
                return (a + b) / 2;
            }
            int First(string prefix)
            {
                for (int i = 0; i < course.StationCount; i++) if (course.SegmentName(i).StartsWith(prefix)) return i;
                return 0;
            }

            void PlaceCraft(int s, float u, float lift = 0f)
            {
                Vector3 p = course.LanePoint(s, u);
                Vector3 n = course.LaneNormal(s, u);
                Vector3 f = Vector3.ProjectOnPlane(course.Tangent[s], n).normalized;
                craft.Place(p + n * (craft.tuning.hoverHeight + lift), Quaternion.LookRotation(f, n), craft.tuning.topSpeed);
                Physics.SyncTransforms();
                craft.Body.linearVelocity = f * craft.tuning.topSpeed;
                craft.Step(1f / 90f);      // atualiza telemetria (sem simular movimento)
                craft.Body.linearVelocity = f * craft.tuning.topSpeed;
            }

            void Chase(string name, int s, float u)
            {
                PlaceCraft(s, u);
                chase.enabled = true;
                chase.Attach(craft);
                for (int k = 0; k < 240; k++) chase.Tick(1f / 60f);
                Shot(cam, Path.Combine(outDir, name + ".png"));
            }

            void View(string name, int s, float u, Vector3 camOffsetLocal, float fov = 60f, float lift = 0f, Vector3? lookAt = null)
            {
                PlaceCraft(s, u, lift);
                chase.enabled = false;
                Vector3 c = course.Center[s];
                Vector3 pos = c + course.Right[s] * camOffsetLocal.x + Vector3.up * camOffsetLocal.y + course.Tangent[s] * camOffsetLocal.z;
                Vector3 target = lookAt ?? craft.Position;
                cam.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                cam.fieldOfView = fov;
                Shot(cam, Path.Combine(outDir, name + ".png"));
            }

            int s00 = Mid("S00"), s01 = Mid("S01"), s03 = Mid("S03"), s07 = Mid("S07"), s10 = Mid("S10"), s13 = Mid("S13");
            int gap = Mid("S20"), cave = Mid("S24"), caveIn = First("S24");
            float wallU = course.LaneForAngle(s13, 65f, 1);

            Chase("01_largada_bacia", s00, 0f);
            View("02_reta_lateral", s01, 0.15f, new Vector3(-16f, course.Center[s01].y + 3f, -30f), 55f);
            Chase("03_bank30_perseguicao", s03, 0f);
            View("04_bank50_vista", s07, 0f, new Vector3(-70f, course.Center[s07].y + 22f, -60f), 55f);
            Chase("05_halfpipe_parede_alta", s10, 0.75f);
            View("06_halfpipe_vista", s10, -0.55f, new Vector3(0f, course.Center[s10].y + 60f, -170f), 50f);
            Chase("07_parede65_perseguicao", s13, wallU);
            View("08_parede65_do_leito", s13, wallU, new Vector3(-12f, course.Center[s13].y + 3f, -55f), 62f);
            View("09_ravina_salto", gap, 0f, new Vector3(150f, course.Center[gap].y - 15f, -40f), 50f, 6f);
            View("10_caverna_boca", caveIn - 60, 0f, new Vector3(-30f, course.Center[caveIn].y + 30f, -170f), 55f, 0f, course.Center[caveIn] + Vector3.up * 15f);
            Chase("11_caverna_dentro", cave, 0f);
            View("12_aerea", s10, 0f, new Vector3(-900f, course.Center[s10].y + 650f, -500f), 60f, 0f, course.Center[s10]);

            // ramos (grafo de percursos): saída, dentro do ramo, ilha/fin entre canyons, vista aérea da bifurcação
            var graph = Object.FindFirstObjectByType<CourseRuntime>().Graph;
            int nb = 0;
            foreach (var br in graph.Paths)
            {
                if (br.IsMain) continue;
                nb++;
                var d = br.Data;
                int split = course.StationAt(br.From);
                int bmid = d.StationCount / 2, bq = d.StationCount / 4;
                // à saída: câmera no principal, um pouco antes, a olhar para a boca do ramo
                PlaceCraft(split - 30, 0f);
                chase.enabled = false;
                Vector3 mouth = d.Center[Mathf.Min(d.StationCount - 1, 80)] + Vector3.up * 6f;
                Vector3 camPos = course.Center[split] - course.Tangent[split] * 140f + Vector3.up * 22f;
                cam.transform.SetPositionAndRotation(camPos, Quaternion.LookRotation(mouth - camPos, Vector3.up));
                cam.fieldOfView = 60f;
                Shot(cam, Path.Combine(outDir, $"2{nb}a_ramo_saida.png"));
                // dentro do ramo: perseguição
                PlaceOn(d, bq, 0f);
                chase.enabled = true;
                chase.Attach(craft);
                for (int k = 0; k < 240; k++) chase.Tick(1f / 60f);
                Shot(cam, Path.Combine(outDir, $"2{nb}b_ramo_dentro.png"));
                PlaceOn(d, bmid, 0f);
                for (int k = 0; k < 240; k++) chase.Tick(1f / 60f);
                Shot(cam, Path.Combine(outDir, $"2{nb}c_ramo_meio.png"));
                // vista aérea da bifurcação (de trás e de cima)
                chase.enabled = false;
                Vector3 c0 = course.Center[split];
                Vector3 look = d.Center[bmid];
                Vector3 air = c0 - course.Tangent[split] * 420f + Vector3.up * 260f - d.Right[bmid] * 0f;
                cam.transform.SetPositionAndRotation(air, Quaternion.LookRotation(look - air, Vector3.up));
                cam.fieldOfView = 55f;
                Shot(cam, Path.Combine(outDir, $"2{nb}d_bifurcacao_aerea.png"));
            }

            // kit de rocha do laboratório (posições do sandbox.json): a chegar a arcos e dentro do destroço
            if (course.Length > 13700f)
            {
                Chase("31_arco_wash", course.StationAt(11400f) - 45, 0f);
                Chase("32_arco_reta", course.StationAt(1250f) - 30, 0f);
                Chase("33_destroco", course.StationAt(13420f), 0f);
            }
            if (First("S30") > 0)
            {
                int top = Mid("S30"), climb = Mid("S29");
                Chase("34_planalto", top, 0f);
                Chase("35_subida_planalto", climb, 0f);
                View("36_planalto_aereo", top, 0f, new Vector3(-260f, course.Center[top].y + 140f, -380f), 60f, 0f, course.Center[top]);
            }

            void PlaceOn(CourseData d, int s, float u)
            {
                s = Mathf.Clamp(s, 1, d.StationCount - 2);
                Vector3 p = d.LanePoint(s, u);
                Vector3 n = d.LaneNormal(s, u);
                Vector3 f = Vector3.ProjectOnPlane(d.Tangent[s], n).normalized;
                craft.Place(p + n * craft.tuning.hoverHeight, Quaternion.LookRotation(f, n), craft.tuning.topSpeed);
                Physics.SyncTransforms();
                craft.Body.linearVelocity = f * craft.tuning.topSpeed;
                craft.Step(1f / 90f);
                craft.Body.linearVelocity = f * craft.tuning.topSpeed;
            }

            Object.DestroyImmediate(craft.gameObject);
            Object.DestroyImmediate(camGo);
            if (post != null) Object.DestroyImmediate(post.gameObject);
            Physics.simulationMode = prevMode == SimulationMode.Script ? SimulationMode.FixedUpdate : prevMode;   // nunca deixar o projeto em modo manual
            Debug.Log($"[RDD] fotografias em {Path.GetFullPath(outDir)}");
            if (Application.isBatchMode) EditorApplication.Exit(0);
        }

        static void Shot(Camera cam, string path)
        {
            var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 1 };
            rt.Create();
            var req = new RenderPipeline.StandardRequest { destination = rt };
            if (RenderPipeline.SupportsRenderRequest(cam, req)) RenderPipeline.SubmitRenderRequest(cam, req);
            else { cam.targetTexture = rt; cam.Render(); cam.targetTexture = null; }
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            var tex = new Texture2D(W, H, TextureFormat.RGBA32, false, false);
            tex.ReadPixels(new Rect(0, 0, W, H), 0, 0);
            tex.Apply();
            RenderTexture.active = prev;
            File.WriteAllBytes(path, tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
            rt.Release();
            Object.DestroyImmediate(rt);
            Debug.Log("[RDD] foto " + path);
        }
    }
}
