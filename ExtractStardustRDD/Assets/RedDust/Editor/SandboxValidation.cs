using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using RedDust.AI;
using RedDust.Presentation;
using RedDust.Track;
using RedDust.Vehicle;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace RedDust.EditorTools
{
    /// <summary>
    /// Testes de aceitação do Milestone 1 (laboratório de física e câmera), sem ecrã, com Physics.Simulate.
    /// Cada teste mede valores e compara com o critério do plano (Docs/RDD_00 §L). Escreve Docs/M1_Relatorio_Fisica.md.
    /// </summary>
    public static class SandboxValidation
    {
        const float Dt = 1f / 90f;

        sealed class Result
        {
            public string id, name, criterion, measured;
            public bool pass;
        }

        static CourseData course;
        static CraftController craft;
        static ChaseCamera chase;
        static LineFollower pilot;
        static readonly List<Result> results = new List<Result>();
        static int impacts;
        static float maxCamRollExcess, camInsideFrames, camSamples;

        [MenuItem("Red Dust/3. Validar física (M1)")]
        public static void Run()
        {
            EditorSceneManager.OpenScene(CourseImporter.ScenePath);
            course = UnityEngine.Object.FindFirstObjectByType<CourseRuntime>().Data;
            var prevMode = Physics.simulationMode;
            Physics.simulationMode = SimulationMode.Script;
            results.Clear();
            SurfaceNormals.Clear();
            var tuning = new CraftTuning();
            craft = CraftFactory.CreateCore("TestCraft", tuning, false);
            craft.autoStep = false;
            craft.Impacted += (s, n, c) => impacts++;
            var camGo = new GameObject("TestCam");
            camGo.AddComponent<Camera>();
            chase = camGo.AddComponent<ChaseCamera>();
            chase.Attach(craft);
            pilot = new LineFollower();
            var sw = System.Diagnostics.Stopwatch.StartNew();
            try
            {
                TestHover();
                TestBank("S02", "S04", "T2a", "Bank 30° (entrada, curva, saída)");
                TestBank("S06", "S08", "T2b", "Bank 50° (entrada, curva, saída)");
                foreach (float u in new[] { 0f, 0.45f, 0.8f }) TestHalfPipe(u);
                TestWall();
                TestJumps();
                TestCave();
                TestTunnelling();
                TestNaturalLines();
                TestFullLap();
                // câmera (acumulado em todos os percursos)
                Add("C1", "Câmera: horizonte", "roll da câmera ≤ 40% do roll da nave (+3° de tremor)", $"excesso máx. {maxCamRollExcess:0.0}°", maxCamRollExcess <= 3f);
                Add("C2", "Câmera: nunca dentro da geometria", "0 frames", $"{camInsideFrames:0} de {camSamples:0} frames", camInsideFrames == 0);
            }
            catch (Exception e)
            {
                Add("ERRO", "Exceção", "-", e.ToString(), false);
            }
            finally
            {
                Physics.simulationMode = prevMode == SimulationMode.Script ? SimulationMode.FixedUpdate : prevMode;
                UnityEngine.Object.DestroyImmediate(craft.gameObject);
                UnityEngine.Object.DestroyImmediate(camGo);
            }
            WriteReport(sw.Elapsed.TotalSeconds);
            if (Application.isBatchMode) EditorApplication.Exit(results.All(r => r.pass) ? 0 : 1);
        }

        // ------------------------------------------------------------------ utilitários

        static void Add(string id, string name, string criterion, string measured, bool pass)
        {
            results.Add(new Result { id = id, name = name, criterion = criterion, measured = measured, pass = pass });
            Debug.Log($"[RDD M1] {(pass ? "PASSA" : "FALHA")} {id} {name}: {measured} (critério: {criterion})");
        }

        static (int a, int b) Seg(string prefix)
        {
            int a = -1, b = -1;
            for (int i = 0; i < course.StationCount; i++)
                if (course.SegmentName(i).StartsWith(prefix)) { if (a < 0) a = i; b = i; }
            if (a < 0) throw new Exception("segmento " + prefix + " não existe");
            return (a, b);
        }

        static void Place(int station, float u, float speed)
        {
            station = Mathf.Clamp(station, 1, course.StationCount - 2);
            Vector3 p = course.LanePoint(station, u);
            Vector3 n = course.LaneNormal(station, u);
            Vector3 f = Vector3.ProjectOnPlane(course.Tangent[station], n).normalized;
            craft.Place(p + n * craft.tuning.hoverHeight, Quaternion.LookRotation(f, n), speed);
            Physics.SyncTransforms();
            pilot.Reset(u);
            chase.Attach(craft);
            impacts = 0;
        }

        /// <summary>Simula até 'until' (distância) ou maxSeconds; each(step) devolve false para parar.</summary>
        static int Drive(float until, float maxSeconds, Func<int, bool> each = null, Func<int, float> lane = null, bool useCamera = true)
        {
            int steps = Mathf.CeilToInt(maxSeconds / Dt);
            for (int k = 0; k < steps; k++)
            {
                if (lane != null) pilot.laneU = lane(Mathf.Max(0, pilot.Station));
                craft.input = pilot.Drive(craft, course, Dt);
                craft.Step(Dt);
                Physics.Simulate(Dt);
                if (useCamera) CameraCheck();
                if (each != null && !each(k)) return k;
                if (pilot.Distance >= until) return k;
            }
            return steps;
        }

        static void CameraCheck()
        {
            chase.Tick(Dt);
            camSamples++;
            maxCamRollExcess = Mathf.Max(maxCamRollExcess, chase.CameraRollDeg - 0.4f * chase.CraftRollDeg);
            if (Physics.CheckSphere(chase.transform.position, 0.12f, Layers.CameraMask, QueryTriggerInteraction.Ignore)) camInsideFrames++;
        }

        static float LateralMeters(int station, float u)
        {
            Vector3 target = course.LanePoint(station, u);
            return Mathf.Abs(Vector3.Dot(craft.Position - target, course.Right[station]));
        }

        static string F(float v, string fmt = "0.00") => v.ToString(fmt, CultureInfo.InvariantCulture);

        // ------------------------------------------------------------------ testes

        static void TestHover()
        {
            var (a, b) = Seg("S01");
            Place(a + 100, 0f, craft.tuning.topSpeed);
            float maxDev = 0f, speedSum = 0f; int n = 0, ground = 0;
            int settle = Mathf.CeilToInt(1.5f / Dt);
            Drive(course.Dist[b], 8f, k =>
            {
                if (k < settle) return true;
                n++;
                if (craft.Grounded) ground++;
                if (!float.IsInfinity(craft.HoverMeasured)) maxDev = Mathf.Max(maxDev, Mathf.Abs(craft.HoverMeasured - craft.tuning.hoverHeight));
                speedSum += craft.Speed;
                return true;
            });
            float vAvg = speedSum / Mathf.Max(1, n);
            Add("T1", "Hover em leito plano à velocidade máxima", "desvio de altura ≤ 0,30 m; contacto ≥ 99%",
                $"desvio máx. {F(maxDev)} m · contacto {F(100f * ground / Mathf.Max(1, n), "0.0")}% · {F(Units.ToKmh(vAvg), "0")} km/h",
                maxDev <= 0.30f && ground >= 0.99f * n);
        }

        static void TestBank(string inSeg, string outSeg, string id, string name)
        {
            var (a, _) = Seg(inSeg);
            var (_, b) = Seg(outSeg);
            Place(a - 40, 0f, craft.tuning.topSpeed);
            float maxRate = 0f, maxLat = 0f, maxBank = 0f; int n = 0, ground = 0;
            Drive(course.Dist[b], 40f, k =>
            {
                if (k < 60) return true;
                n++;
                if (craft.Grounded) ground++;
                maxRate = Mathf.Max(maxRate, craft.UpRateSmoothed);
                maxLat = Mathf.Max(maxLat, LateralMeters(pilot.Station, 0f));
                maxBank = Mathf.Max(maxBank, Vector3.Angle(craft.Up, Vector3.up));
                return true;
            });
            Add(id, name, "sem snap (Δcima médio 0,1 s ≤ 90°/s); contacto ≥ 99%; desvio lateral ≤ 5 m; 0 impactos",
                $"Δcima máx. {F(maxRate, "0")}°/s · contacto {F(100f * ground / Mathf.Max(1, n), "0.0")}% · desvio {F(maxLat, "0.0")} m · inclinação máx. {F(maxBank, "0")}° · impactos {impacts}",
                maxRate <= 90f && ground >= 0.99f * n && maxLat <= 5f && impacts == 0);
        }

        static void TestHalfPipe(float u)
        {
            var (a, _) = Seg("S09");
            var (s10a, s10b) = Seg("S10");
            var (_, b) = Seg("S11");
            Place(a - 30, 0f, craft.tuning.topSpeed);
            float maxRate = 0f, uErr = 0f, maxSurf = 0f; int n = 0, ground = 0, nu = 0;
            Drive(course.Dist[b], 40f, k =>
            {
                if (k < 60) return true;
                n++;
                if (craft.Grounded) ground++;
                maxRate = Mathf.Max(maxRate, craft.UpRateSmoothed);
                int s = pilot.Station;
                if (s > s10a + 60 && s < s10b)
                {
                    uErr += Mathf.Abs(pilot.CurrentU - u); nu++;
                    maxSurf = Mathf.Max(maxSurf, craft.SurfaceAngle);
                }
                return true;
            }, s => (s >= a + 40 && s <= s10b) ? u : 0f);
            float mean = uErr / Mathf.Max(1, nu);
            Add($"T3 u={F(u, "0.00")}", $"Half-pipe a {(u < 0.1f ? "fundo" : u < 0.6f ? "meia parede" : "parede alta")}",
                "contacto ≥ 98%; erro médio de linha ≤ 0,12; Δcima médio 0,1 s ≤ 120°/s",
                $"contacto {F(100f * ground / Mathf.Max(1, n), "0.0")}% · erro de linha {F(mean, "0.000")} · Δcima máx. {F(maxRate, "0")}°/s · superfície máx. {F(maxSurf, "0")}°",
                ground >= 0.98f * n && mean <= 0.12f && maxRate <= 120f);
        }

        static void TestWall()
        {
            var (a, _) = Seg("S12");
            var (s13a, s13b) = Seg("S13");
            var (_, b) = Seg("S14");
            float wallU = course.LaneForAngle((s13a + s13b) / 2, 65f, 1);
            Place(a - 30, 0f, craft.tuning.topSpeed);
            float run = 0f, best = 0f, maxSurf = 0f;
            Drive(course.Dist[b], 40f, k =>
            {
                if (craft.Grounded && craft.SurfaceAngle >= 60f) { run += Dt; best = Mathf.Max(best, run); } else run = 0f;
                maxSurf = Mathf.Max(maxSurf, craft.Grounded ? craft.SurfaceAngle : 0f);
                return true;
            }, s => (s >= a + 60 && s <= s13b) ? wallU : 0f);
            Add("T4a", "Wall ride natural a ~65° à velocidade máxima", "≥ 2 s seguidos em superfície ≥ 60° com contacto",
                $"{F(best, "0.0")} s seguidos · superfície máx. {F(maxSurf, "0")}° · linha u={F(wallU, "0.00")}", best >= 2f);

            // abaixo da velocidade mínima: deve perder a parede (escorregar) ou descolar, de forma previsível
            int mid = (s13a + s13b) / 2;
            float a0 = course.SurfaceAngle(mid, wallU);
            Vector3 p = course.LanePoint(mid, wallU);
            Vector3 nrm = course.LaneNormal(mid, wallU);
            Vector3 f = Vector3.ProjectOnPlane(course.Tangent[mid], nrm).normalized;
            craft.Place(p + nrm * craft.tuning.hoverHeight, Quaternion.LookRotation(f, nrm), 30f);
            Physics.SyncTransforms();
            float tLose = -1f, minAngle = a0, slide = 0f;
            Vector3 p0 = p + nrm * craft.tuning.hoverHeight;
            Vector3 downSlope = Vector3.ProjectOnPlane(Vector3.down, nrm).normalized;
            var trace = new StringBuilder();
            for (int k = 0; k < Mathf.CeilToInt(2f / Dt); k++)
            {
                craft.input = new CraftInput();
                craft.Step(Dt);
                Physics.Simulate(Dt);
                if (k % 30 == 0)
                {
                    int st = course.Nearest(craft.Position, mid);
                    trace.Append($" [{F(k * Dt, "0.0")}s u {F(course.LateralU(craft.Position, st), "0.00")} sup {F(craft.SurfaceAngle, "0")}° vlat {F(craft.LateralSpeed, "0.0")} v {F(craft.Speed, "0")} h {F(craft.HoverMeasured, "0.0")} solo {craft.Grounded}]");
                }
                if (craft.Grounded) minAngle = Mathf.Min(minAngle, craft.SurfaceAngle);
                slide = Vector3.Dot(craft.Position - p0, downSlope);
                if (tLose < 0f && (!craft.Grounded || slide >= 3f)) tLose = (k + 1) * Dt;
            }
            Add("T4b", "Parede abaixo da velocidade mínima (30 m/s, sem acelerar)", "escorrega ≥ 3 m parede abaixo ou descola em ≤ 2 s",
                tLose < 0 ? $"segurou-se (escorregou {F(slide, "0.0")} m)" : $"perdeu a linha após {F(tLose, "0.00")} s · escorregou {F(slide, "0.0")} m em 2 s", tLose >= 0f);

            // acima da velocidade mínima (216 km/h): segura a linha de parede com o piloto
            Place(mid - 120, wallU, 60f);
            float hold = 0f, bestHold = 0f;
            pilot.speedLimit = 60f;
            Drive(course.Dist[Mathf.Min(s13b, mid + 400)], 6f, k =>
            {
                if (craft.Grounded && craft.SurfaceAngle >= 58f) { hold += Dt; bestHold = Mathf.Max(bestHold, hold); } else hold = 0f;
                return true;
            }, s => wallU);
            pilot.speedLimit = float.PositiveInfinity;
            Add("T4c", "Parede a 216 km/h (acima da mínima)", "segura ≥ 1,5 s em superfície ≥ 58°", $"{F(bestHold, "0.0")} s", bestHold >= 1.5f);
        }

        static void TestJumps()
        {
            var (a, _) = Seg("S15");
            var (gapA, gapB) = Seg("S20");
            var (_, b) = Seg("S22");
            Place(a, 0f, craft.tuning.topSpeed);
            var airs = new List<(float start, float dur, float landDist, float vn)>();
            float airStart = -1f, t = 0f, hopMax = 0f;
            var (c16, _) = Seg("S16");
            var (gA, _) = Seg("S20");
            int landImpacts = 0;
            Drive(course.Dist[b], 30f, k =>
            {
                t += Dt;
                if (pilot.Station > c16 && pilot.Station < gA - 60 && !float.IsInfinity(craft.HoverMeasured))
                    hopMax = Mathf.Max(hopMax, craft.HoverMeasured - craft.tuning.hoverHeight);
                if (!craft.Grounded && airStart < 0f) airStart = pilot.Distance;
                if (craft.Grounded && airStart >= 0f)
                {
                    airs.Add((airStart, craft.AirTime > 0 ? craft.AirTime : 0f, pilot.Distance, craft.LastLandingSpeed));
                    airStart = -1f;
                }
                return true;
            });
            landImpacts = impacts;
            // AirTime é zerado ao aterrar: medir pela distância percorrida no ar
            var big = airs.Select(x => (x.start, len: x.landDist - x.start, x.landDist, x.vn)).Where(x => x.len > 5f).ToList();
            var crest = big.FirstOrDefault(x => x.start < course.Dist[gapA] - 100f);
            var ravine = big.FirstOrDefault(x => x.start >= course.Dist[gapA] - 100f);
            bool crossed = ravine.len > 0f && ravine.landDist > course.Dist[gapB] + 2f;
            float vnMax = big.Count > 0 ? big.Max(x => x.vn) : 0f;
            Add("T5a", "Flow jump (borda natural de 7°)", "salto visível: ≥ 1 m acima do hover ou voo ≥ 30 m",
                $"altura máx. +{F(hopMax, "0.0")} m sobre o hover · voo {F(crest.len, "0")} m", hopMax >= 1f || crest.len >= 30f);
            Add("T5b", "Canyon jump sobre a ravina", "atravessa a ravina e aterra do outro lado", crossed ? $"voo de {F(ravine.len, "0")} m, aterra {F(ravine.landDist - course.Dist[gapB], "0")} m depois da ravina" : "não atravessou", crossed);
            string list = string.Join(" · ", big.Select(x => $"{F(x.start, "0")} m: voo {F(x.len, "0")} m, {F(x.vn, "0.0")} m/s"));
            Add("T5c", "Receção legível", "flow jump ≤ 12 m/s; canyon jump ≤ 17 m/s; 0 impactos do casco",
                $"{list} · impactos {landImpacts}", (crest.len <= 0f || crest.vn <= 12f) && ravine.vn <= craft.tuning.landingHard && landImpacts == 0);
        }

        static void TestCave()
        {
            var (a, _) = Seg("S23");
            var (s24a, s24b) = Seg("S24");
            Place(a - 20, 0f, craft.tuning.topSpeed);
            float minClear = float.MaxValue; int n = 0, ground = 0;
            Drive(course.Dist[s24b] + 150f, 20f, k =>
            {
                int s = pilot.Station;
                if (s >= s24a && s <= s24b)
                {
                    n++;
                    if (craft.Grounded) ground++;
                    if (Physics.Raycast(craft.Position, craft.Up, out var h, 60f, Layers.GroundMask)) minClear = Mathf.Min(minClear, h.distance);
                }
                return true;
            });
            Add("T6", "Caverna curva (teto irregular)", "contacto ≥ 98%; folga ao teto ≥ 3 m; 0 impactos",
                $"contacto {F(100f * ground / Mathf.Max(1, n), "0.0")}% · folga mín. {F(minClear, "0.0")} m · impactos {impacts}",
                ground >= 0.98f * n && minClear >= 3f && impacts == 0);
        }

        static void TestTunnelling()
        {
            // parede fina num local isolado; 1000 disparos a 1,3-1,5x a velocidade máxima, incidência 0-70°
            var wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wall.name = "TunnelWall";
            wall.layer = Layers.Obstacle;
            wall.transform.position = new Vector3(30000f, 2000f, 0f);
            wall.transform.localScale = new Vector3(60f, 60f, 1f);
            Physics.SyncTransforms();
            var rng = new System.Random(12);
            int fails = 0;
            float top = craft.tuning.topSpeed;
            for (int i = 0; i < 1000; i++)
            {
                float inc = (float)rng.NextDouble() * 70f;
                float yaw = (float)(rng.NextDouble() * 360.0);
                Vector3 dir = Quaternion.AngleAxis(yaw, Vector3.forward) * Quaternion.AngleAxis(inc, Vector3.up) * Vector3.forward;
                float speed = top * (1.3f + 0.2f * (float)rng.NextDouble());
                Vector3 start = wall.transform.position - dir * 20f + new Vector3((float)rng.NextDouble() * 10f - 5f, (float)rng.NextDouble() * 10f - 5f, 0f);
                start.z = wall.transform.position.z - 20f * dir.z;
                craft.Place(start, Quaternion.LookRotation(dir, Vector3.up), speed);
                Physics.SyncTransforms();
                for (int k = 0; k < 40; k++)
                {
                    craft.input = new CraftInput();
                    craft.Step(Dt);
                    Physics.Simulate(Dt);
                }
                if (craft.Position.z > wall.transform.position.z) fails++;
            }
            UnityEngine.Object.DestroyImmediate(wall);

            // chão: quedas violentas sobre o leito
            int floorFails = 0;
            var (a, b) = Seg("S01");
            for (int i = 0; i < 200; i++)
            {
                int s = a + (int)(rng.NextDouble() * (b - a - 20));
                Vector3 p = course.LanePoint(s, (float)rng.NextDouble() * 1.6f - 0.8f) + Vector3.up * 30f;
                Vector3 f = course.Tangent[s];
                craft.Place(p, Quaternion.LookRotation(f, Vector3.up), 0f);
                craft.Body.linearVelocity = f * top * 1.3f + Vector3.down * 70f;
                Physics.SyncTransforms();
                for (int k = 0; k < 90; k++)
                {
                    craft.input = new CraftInput();
                    craft.Step(Dt);
                    Physics.Simulate(Dt);
                }
                Vector3 c = craft.Position;
                if (Physics.Raycast(c + Vector3.up * 200f, Vector3.down, out var h, 400f, Layers.GroundMask) && c.y < h.point.y - 0.3f) floorFails++;
            }
            Add("T7", "Sem tunneling a 1,3-1,5x a velocidade máxima", "0 atravessamentos (1000 paredes + 200 quedas no leito)",
                $"paredes {fails}/1000 · leito {floorFails}/200", fails == 0 && floorFails == 0);
        }

        /// <summary>Leito natural: canal, bancada esquerda e bancada direita têm de ser todas viáveis (cada uma com o seu custo).</summary>
        static void TestNaturalLines()
        {
            var (a, _) = Seg("S22b");
            var (_, b) = Seg("S22d");
            var res = new List<string>();
            var times = new List<float>();
            bool ok = true;
            foreach (float u in new[] { -0.55f, 0f, 0.55f })
            {
                Place(a - 30, 0f, craft.tuning.topSpeed);
                float t = 0f, vnMax = 0f, air = 0f; int falls = 0;
                var surf = new Dictionary<Surface, float>();
                int st0 = pilot.Station;
                Drive(course.Dist[b], 40f, k =>
                {
                    t += Dt;
                    if (!craft.Grounded) air += Dt;
                    vnMax = Mathf.Max(vnMax, craft.LastLandingSpeed);
                    if (craft.Grounded) { surf.TryGetValue(craft.Surface, out float v); surf[craft.Surface] = v + Dt; }
                    if (craft.Position.y < course.Center[pilot.Station].y - 40f) { falls++; return false; }
                    return true;
                }, s => (s >= a + 30) ? u : 0f);
                bool done = pilot.Distance >= course.Dist[b] - 5f && falls == 0;
                ok &= done && impacts == 0;
                times.Add(t);
                string main = string.Join(", ", surf.OrderByDescending(kv => kv.Value).Take(3).Select(kv => $"{kv.Key} {100f * kv.Value / Mathf.Max(0.01f, t):0}%"));
                res.Add($"u={F(u, "0.00")}: {F(t, "0.0")} s, ar {F(air, "0.0")} s, aterragem máx. {F(vnMax, "0.0")} m/s, {main}{(done ? "" : " · NÃO TERMINOU")}");
            }
            float spread = (times.Max() - times.Min()) / Mathf.Max(0.01f, times.Min());
            Add("T9", "Leito natural: três linhas viáveis (canal / bancadas)", "todas terminam sem quedas nem impactos; diferença de tempo ≤ 12%",
                string.Join(" · ", res) + $" · diferença {F(spread * 100f, "0.0")}%", ok && spread <= 0.12f);
        }

        static void TestFullLap()
        {
            int s0 = course.StationAt(30f);
            Place(s0, 0f, 0f);
            var laneOf = new float[course.StationCount];
            for (int i = 0; i < course.StationCount; i++)
            {
                string seg = course.SegmentName(i);
                laneOf[i] = seg.StartsWith("S09") || seg.StartsWith("S10") ? 0.45f : seg.StartsWith("S12") || seg.StartsWith("S13") ? 0.75f : 0f;
            }
            var lane = new Func<int, float>(s => laneOf[Mathf.Clamp(s, 0, laneOf.Length - 1)]);
            float t = 0f, minSpeed = float.MaxValue, groundT = 0f; int falls = 0;
            var csv = new StringBuilder("t;dist;kmh;solo;hover;superficie;dcima\n");
            int k0 = 0;
            Drive(course.Length - 40f, 400f, k =>
            {
                t += Dt;
                if (craft.Grounded) groundT += Dt;
                if (t > 20f) minSpeed = Mathf.Min(minSpeed, craft.Speed);
                int s = pilot.Station;
                if (craft.Position.y < course.Center[s].y - 60f) { falls++; return false; }
                if (k % 9 == 0)
                    csv.Append($"{F(t, "0.0")};{F(pilot.Distance, "0")};{F(Units.ToKmh(craft.Speed), "0")};{(craft.Grounded ? 1 : 0)};{F(float.IsInfinity(craft.HoverMeasured) ? -1f : craft.HoverMeasured)};{F(craft.SurfaceAngle, "0")};{F(craft.UpRateDeg, "0")}\n");
                k0 = k;
                return true;
            }, lane);
            bool done = pilot.Distance >= course.Length - 60f;
            float avg = pilot.Distance / Mathf.Max(1f, t);
            Directory.CreateDirectory("Logs");
            File.WriteAllText("Logs/rdd_m1_volta.csv", csv.ToString());
            Add("T8", "Volta completa automática ao laboratório", "termina; 0 quedas; sem ficar preso (v > 20 m/s após 20 s)",
                $"{(done ? "terminou" : "NÃO terminou")} em {F(t, "0.0")} s · média {F(Units.ToKmh(avg), "0")} km/h · v mín. {F(Units.ToKmh(minSpeed), "0")} km/h · solo {F(100f * groundT / Mathf.Max(0.01f, t), "0.0")}% · quedas {falls} · impactos {impacts}",
                done && falls == 0 && minSpeed > 20f);
        }

        // ------------------------------------------------------------------ relatório

        static void WriteReport(double seconds)
        {
            int pass = results.Count(r => r.pass);
            var sb = new StringBuilder();
            sb.AppendLine("# M1 — Relatório de validação da física e da câmera");
            sb.AppendLine();
            sb.AppendLine($"Gerado automaticamente em {DateTime.Now:yyyy-MM-dd HH:mm} · passo fixo 1/90 s · {seconds:0} s de simulação real.");
            sb.AppendLine($"Percurso: laboratório (`Art/Courses/sandbox.json`), {course.Length / 1000f:0.00} km. Nave: STRIX provisória (CraftTuning por omissão, {Units.ToKmh(new CraftTuning().topSpeed):0} km/h).");
            sb.AppendLine();
            sb.AppendLine($"**Resultado: {pass}/{results.Count} testes passam.**");
            sb.AppendLine();
            sb.AppendLine("| Teste | O que prova | Critério | Medido | Estado |");
            sb.AppendLine("|---|---|---|---|---|");
            foreach (var r in results)
                sb.AppendLine($"| {r.id} | {r.name} | {r.criterion} | {r.measured} | {(r.pass ? "✅ PASSA" : "❌ FALHA")} |");
            Directory.CreateDirectory("Docs");
            File.WriteAllText("Docs/M1_Relatorio_Fisica.md", sb.ToString());
            Directory.CreateDirectory("Logs");
            File.WriteAllText("Logs/rdd_m1_validation.txt", sb.ToString());
            Debug.Log($"[RDD M1] {pass}/{results.Count} testes passam");
        }
    }
}
