using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using RedDust.AI;
using RedDust.Track;
using RedDust.Vehicle;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace RedDust.Presentation
{
    /// <summary>
    /// Laboratório jogável (M1): título → contagem → corrida cronometrada até ao fim do percurso → resultado.
    /// Pausa (OPTIONS/Esc) com Continuar · Recomeçar · Opções (tremor, FOV, vibração, painel técnico) · Sair.
    /// Comando PS4/PS5 e teclado (ver GameInput). Reposicionar: Triângulo/R; queda: reposiciona sozinho.
    /// Linha de comandos: -rddtest (volta automática com capturas), -shotdir DIR, -quality 0.
    /// </summary>
    public class SandboxDirector : MonoBehaviour
    {
        public Light sun;
        public Color paint = new Color(0.72f, 0.08f, 0.06f);

        enum Phase { Title, Countdown, Racing, Finished }

        public CraftController Craft { get; private set; }
        CourseGraph graph;
        CourseData course;                 // percurso principal (largada, chegada, progresso)
        ChaseCamera chase;
        DebugOverlay overlay;
        PlayerCraftInput player;
        RaceHud hud;
        RouteFollower pilot;
        Phase phase = Phase.Title;
        bool paused, optionsOpen, autopilot, autotest, mobile;
        int menuIndex;
        float raceTime, bestTime, countdown, hintTimer;
        int station, pathIdx;              // onde a nave está: percurso do grafo e estação nele
        CourseData Here => graph.Paths[pathIdx].Data;
        string shotDir, bestKey;
        float wallLane = 0.8f;
        static readonly int GridId = Shader.PropertyToID("_RD_Grid");

        // opções (PlayerPrefs: conveniência por jogador)
        float shake = 1f, fovExtra;
        bool vibration = true, techPanel;

        void Awake()
        {
            QualitySettings.vSyncCount = 0;
            mobile = Application.isMobilePlatform || CommandLine.Int("-quality", -1) == 0;
            Application.targetFrameRate = mobile ? 60 : Mathf.Clamp((int)Screen.currentResolution.refreshRateRatio.value, 60, 144);
            Time.fixedDeltaTime = 1f / 90f;
            Time.maximumDeltaTime = 0.1f;
            Physics.simulationMode = SimulationMode.FixedUpdate;    // garantia: a física corre sempre em jogo
            autotest = CommandLine.Has("-rddtest");
            shotDir = CommandLine.Value("-shotdir", Path.Combine(Application.persistentDataPath, "shots"));
            shake = PlayerPrefs.GetFloat("rdd_shake", 1f);
            fovExtra = PlayerPrefs.GetFloat("rdd_fov", 0f);
            vibration = PlayerPrefs.GetInt("rdd_vibration", 1) == 1;
            techPanel = PlayerPrefs.GetInt("rdd_tech", 0) == 1;
            bestKey = "rdd_best_" + SceneManager.GetActiveScene().name;
            bestTime = PlayerPrefs.GetFloat(bestKey, 0f);
            GameInput.Init();
        }

        IEnumerator Start()
        {
            graph = CourseRuntime.Active != null ? CourseRuntime.Active.Graph : null;
            course = graph?.Main.Data;
            if (course == null) { Debug.LogError("[RDD] percurso em falta"); yield break; }
            // piloto automático: em cada bifurcação escolhe ao acaso (o autoteste fotografa o principal)
            pilot = new RouteFollower(graph) { chooseBranch = _ => !autotest && Random.value < 0.5f };
            EnvironmentRig.Apply(sun, mobile);
            EnvironmentRig.CreatePost(transform, mobile);
            Shader.SetGlobalFloat(GridId, 0f);

            Craft = CraftFactory.CreateCore("STRIX (provisória)", new CraftTuning());
            PlaceholderCraft.Build(Craft, paint);
            SectorStreamer.Focus.Add(Craft.transform);
            Craft.Landed += vn => GameInput.Rumble(0.25f + vn / 40f, 0.2f + vn / 30f, 0.18f);
            Craft.Impacted += (s, n, c) => GameInput.Rumble(Mathf.Min(1f, s / 30f), Mathf.Min(1f, s / 22f), 0.28f);
            player = gameObject.AddComponent<PlayerCraftInput>();

            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.3f;
            cam.farClipPlane = 16000f;
            var data = camGo.AddComponent<UniversalAdditionalCameraData>();
            data.renderPostProcessing = true;
            data.antialiasing = mobile ? AntialiasingMode.None : AntialiasingMode.SubpixelMorphologicalAntiAliasing;
            camGo.AddComponent<AudioListener>();
            chase = camGo.AddComponent<ChaseCamera>();
            chase.Attach(Craft);
            SpeedFx.Attach(cam, Craft, chase, mobile);
            ApplyOptions();

            overlay = gameObject.AddComponent<DebugOverlay>();
            overlay.craft = Craft;
            overlay.chase = chase;
            overlay.visible = techPanel;
            hud = RaceHud.Create();
            hud.SetCourse(CourseRuntime.Active.title, SceneManager.sceneCountInBuildSettings > 1);

            int wi = 0;
            for (int i = 0; i < course.StationCount; i++) if (course.SegmentName(i).StartsWith("S13")) { wi = i + 60; break; }
            wallLane = course.LaneForAngle(wi, 65f, 1);

            Respawn(0, course.StationAt(30f), 0f);
            if (CommandLine.Has("-rddsmoke"))
            {
                StartCoroutine(Smoke());
            }
            else if (autotest)
            {
                hud.ShowTitle(false);
                phase = Phase.Racing;
                StartCoroutine(AutoTest());
            }
            else
            {
                phase = Phase.Title;
                hud.ShowTitle(true);
                hud.ShowRaceHud(false);
            }
        }

        void ApplyOptions()
        {
            chase.shakeScale = shake;
            chase.fovOffset = fovExtra;
            GameInput.VibrationEnabled = vibration;
            if (overlay != null) overlay.visible = techPanel;
            PlayerPrefs.SetFloat("rdd_shake", shake);
            PlayerPrefs.SetFloat("rdd_fov", fovExtra);
            PlayerPrefs.SetInt("rdd_vibration", vibration ? 1 : 0);
            PlayerPrefs.SetInt("rdd_tech", techPanel ? 1 : 0);
        }

        float LaneFor(int st)
        {
            string seg = course.SegmentName(st);
            if (seg.StartsWith("S10") || seg.StartsWith("S09")) return 0.45f;
            if (seg.StartsWith("S13") || seg.StartsWith("S12")) return wallLane;
            return 0f;
        }

        void Respawn(int path, int st, float speed)
        {
            var d = graph.Paths[path].Data;
            st = Mathf.Clamp(st, 0, d.StationCount - 2);
            while (st > 0 && d.IsGap(st)) st--;
            Vector3 p = d.Center[st] + d.Up[st] * (Craft.tuning.hoverHeight + 0.2f);
            Craft.Place(p, Quaternion.LookRotation(d.Tangent[st], d.Up[st]), speed);
            pathIdx = path;
            station = st;
            pilot.Reset(path, path == 0 ? LaneFor(st) : 0f);
        }

        void Update()
        {
            if (Craft == null || hud == null) return;
            GameInput.Tick();
            hud.Device(GameInput.Pad != null ? $"{GameInput.Name} ligado" : "Teclado (ligue um comando PS4/PS5 por USB ou Bluetooth)");
            if (GameInput.Pad != null) GameInput.SetLightBar(paint);

            if (paused) { UpdatePause(); return; }

            if (GameInput.Overlay()) { techPanel = !techPanel; ApplyOptions(); }
            if (PlayerCraftInput.AutopilotPressed()) autopilot = !autopilot;
            if (PlayerCraftInput.GridPressed()) Shader.SetGlobalFloat(GridId, Shader.GetGlobalFloat(GridId) > 0.5f ? 0f : 1f);
            if (PlayerCraftInput.SlowMotionPressed()) Time.timeScale = Time.timeScale < 1f ? 1f : 0.25f;

            switch (phase)
            {
                case Phase.Title:
                    hud.ShowTitle(true);
                    if (GameInput.Confirm()) StartCountdown();
                    int nx = GameInput.NavX(), count = SceneManager.sceneCountInBuildSettings;
                    if (nx != 0 && count > 1) SceneManager.LoadScene((SceneManager.GetActiveScene().buildIndex + nx + count) % count);
                    break;
                case Phase.Countdown:
                    countdown -= Time.deltaTime;
                    if (countdown <= 0f)
                    {
                        phase = Phase.Racing;
                        raceTime = 0f;
                        hud.Center("VAI!", "", 0.8f);
                        GameInput.Rumble(0.5f, 0.6f, 0.25f);
                    }
                    else hud.Center(Mathf.CeilToInt(countdown).ToString(), "", 0f);
                    break;
                case Phase.Racing:
                    raceTime += Time.deltaTime;
                    if (GameInput.Reset()) { Respawn(pathIdx, Mathf.Max(0, station - 10), 40f); hud.Center("", "Reposicionado", 1.2f); }
                    if (GameInput.Pause()) OpenPause();
                    break;
                case Phase.Finished:
                    if (GameInput.Confirm()) { Respawn(0, course.StationAt(30f), 0f); StartCountdown(); }
                    if (GameInput.Pause()) OpenPause();
                    break;
            }

            // câmera: olhar à volta / para trás
            chase.lookYawInput = GameInput.Look();
            chase.lookBack = GameInput.LookBack();

            // vibração contínua: boost e derrapagem
            if (phase == Phase.Racing)
            {
                if (Craft.Boosting && Craft.Grounded) GameInput.Sustain(0.06f, 0.12f);
                if (Craft.Drifting) GameInput.Sustain(0.12f, 0.05f);
            }

            hud.Race(Units.ToKmh(Craft.Speed), raceTime, bestTime, Here.SegmentName(station), Craft.Boosting, Craft.Drifting, !Craft.Grounded && Craft.AirTime > 0.2f);
            hud.NitroBar(Craft.Nitro, Craft.Boosting, Craft.NitroLocked);
            hud.Progress(graph.Paths[pathIdx].ToRaceDistance(Here.Dist[station]) / course.Length);
            hintTimer -= Time.deltaTime;
            hud.Hints(hintTimer > 0f || phase != Phase.Racing ? HintText() : "");
            overlay.extra = autopilot ? "PILOTO AUTOMÁTICO (F3)" : "F3 piloto automático · G grelha · F2 câmera lenta";
        }

        string HintText() =>
            $"Acelerar: <b>{GameInput.BtnThrottle}</b>    Direção: <b>{GameInput.BtnSteer}</b>    Nitro: <b>{GameInput.BtnBoost}</b> (regenera; mais depressa a derrapar)\n" +
            $"Travar: <b>{GameInput.BtnBrake}</b> (+ direção = derrapagem)    Travão de mão: <b>{GameInput.BtnDrift}</b>    Reposicionar: <b>{GameInput.BtnReset}</b>    Câmera: <b>{GameInput.BtnLook}</b>    Pausa: <b>{GameInput.BtnPause}</b>";

        void StartCountdown()
        {
            hud.ShowTitle(false);
            hud.ShowRaceHud(true);
            phase = Phase.Countdown;
            countdown = 3f;
            hintTimer = 14f;
            raceTime = 0f;
        }

        // ------------------------------------------------------------------ pausa

        void OpenPause()
        {
            paused = true;
            optionsOpen = false;
            menuIndex = 0;
            Time.timeScale = 0f;
            GameInput.StopHaptics();
            RefreshPause();
        }

        void ClosePause()
        {
            paused = false;
            Time.timeScale = 1f;
            hud.Pause(false, null, 0, "");
        }

        List<string> PauseItems()
        {
            if (!optionsOpen) return new List<string> { "Continuar", "Recomeçar", "Opções", "Sair do jogo" };
            return new List<string>
            {
                $"Tremor da câmera: {Mathf.RoundToInt(shake * 100)}%",
                $"Campo de visão extra: {(fovExtra >= 0 ? "+" : "")}{fovExtra:0}°",
                $"Vibração do comando: {(vibration ? "ligada" : "desligada")}",
                $"Painel técnico: {(techPanel ? "visível" : "escondido")}",
                "Voltar",
            };
        }

        void RefreshPause()
        {
            string foot = $"{GameInput.BtnConfirm} escolher  ·  {GameInput.BtnBack} voltar  ·  ←/→ mudar valores\n{HintText()}";
            hud.Pause(true, PauseItems(), menuIndex, foot);
        }

        void UpdatePause()
        {
            var items = PauseItems();
            int ny = GameInput.NavY();
            if (ny != 0) { menuIndex = (menuIndex + ny + items.Count) % items.Count; RefreshPause(); }
            int nx = GameInput.NavX();
            if (optionsOpen && nx != 0) { ChangeOption(menuIndex, nx); RefreshPause(); }
            if (GameInput.Confirm())
            {
                if (!optionsOpen)
                {
                    switch (menuIndex)
                    {
                        case 0: ClosePause(); return;
                        case 1: ClosePause(); Respawn(0, course.StationAt(30f), 0f); StartCountdown(); return;
                        case 2: optionsOpen = true; menuIndex = 0; break;
                        case 3: Application.Quit(); break;
                    }
                }
                else if (menuIndex == items.Count - 1) { optionsOpen = false; menuIndex = 2; }
                else ChangeOption(menuIndex, 1);
                RefreshPause();
            }
            else if (GameInput.Back() || GameInput.Pause())
            {
                if (optionsOpen) { optionsOpen = false; menuIndex = 2; RefreshPause(); }
                else ClosePause();
            }
        }

        void ChangeOption(int i, int dir)
        {
            switch (i)
            {
                case 0: shake = Mathf.Clamp(Mathf.Round((shake + 0.5f * dir) * 2f) / 2f, 0f, 1.5f); break;
                case 1: fovExtra = Mathf.Clamp(fovExtra + 5f * dir, -10f, 10f); break;
                case 2: vibration = !vibration; break;
                case 3: techPanel = !techPanel; break;
            }
            ApplyOptions();
        }

        // ------------------------------------------------------------------ física

        void FixedUpdate()
        {
            if (Craft == null) return;
            float dt = Time.fixedDeltaTime;
            graph.Locate(Craft.Position, ref pathIdx, ref station);
            if (autopilot || autotest)
            {
                pilot.line.laneU = pilot.Path.IsMain ? LaneFor(Mathf.Max(0, pilot.Station)) : 0f;
                Craft.input = pilot.Drive(Craft, dt);
            }
            else if (phase == Phase.Racing) Craft.input = player.Read(dt);
            else Craft.input = new CraftInput();     // título, contagem, fim: nave parada a pairar

            if (phase == Phase.Countdown || phase == Phase.Title)
            {
                Craft.Body.linearVelocity = Vector3.Lerp(Craft.Body.linearVelocity, Vector3.zero, 0.2f);
            }
            bool fell = Craft.Position.y < Here.Center[station].y - 60f;
            if (fell && !autotest) { Respawn(pathIdx, Mathf.Max(0, station - 15), 30f); hud.Center("", "Reposicionado", 1.2f); }
            if (phase == Phase.Racing && !autotest && pathIdx == 0 && station >= course.StationCount - 3) Finish();
        }

        void Finish()
        {
            phase = Phase.Finished;
            bool record = bestTime <= 0f || raceTime < bestTime;
            if (record) { bestTime = raceTime; PlayerPrefs.SetFloat(bestKey, bestTime); }
            hud.Center(RaceHud.FormatTime(raceTime), (record ? "NOVO RECORDE!  " : "") + $"Prima {GameInput.BtnConfirm} para repetir", 0f);
            GameInput.Rumble(0.4f, 0.4f, 0.4f);
        }

        void OnApplicationQuit() => GameInput.StopHaptics();

        /// <summary>Teste de fumo sem janela: título → contagem → corrida (piloto automático) → pausa → opções → fim.</summary>
        IEnumerator Smoke()
        {
            int errors = 0;
            Application.logMessageReceived += (msg, stack, type) => { if (type == LogType.Exception || type == LogType.Error) errors++; };
            hud.ShowTitle(true);
            yield return new WaitForSeconds(1f);
            StartCountdown();
            yield return new WaitForSeconds(3.5f);
            autopilot = true;
            for (int k = 0; k < 12; k++)
            {
                yield return new WaitForSeconds(1f);
                Debug.Log($"[RDD smoke] t={k + 1}s fase {phase} pos {Craft.Position} solo {Craft.Grounded} sensores {Craft.Sensor.hits} hover {Craft.HoverMeasured:0.0} v {Units.ToKmh(Craft.Speed):0} estação {station} dist {pilot.RaceDistance:0} timeScale {Time.timeScale} fixedDt {Time.fixedDeltaTime:0.0000}");
            }
            float d = pilot.RaceDistance;
            OpenPause();
            optionsOpen = true; ChangeOption(0, 1); ChangeOption(1, 1); ChangeOption(2, 1); ChangeOption(3, 1); RefreshPause();
            optionsOpen = false; RefreshPause();
            ClosePause();
            yield return new WaitForSeconds(2f);
            Finish();
            yield return new WaitForSeconds(0.5f);
            Debug.Log($"[RDD smoke] {(errors == 0 && d > 500f ? "OK" : "FALHA")} · erros {errors} · distância {d:0} m · velocidade {Units.ToKmh(Craft.Speed):0} km/h · comando: {GameInput.Name}");
            Application.Quit(errors == 0 && d > 500f ? 0 : 1);
        }

        // ------------------------------------------------------------------ autoteste

        IEnumerator AutoTest()
        {
            Directory.CreateDirectory(shotDir);
            var log = new StringBuilder();
            var marks = new List<(float dist, string name)>();
            int segStart = 0;
            for (int i = 1; i <= course.StationCount; i++)
            {
                if (i < course.StationCount && course.Segment[i] == course.Segment[segStart]) continue;
                float mid = course.Dist[(segStart + i - 1) / 2];
                if (course.IsGap(segStart)) mid = course.Dist[i - 1] + 10f;
                var clean = new StringBuilder();
                foreach (char ch in course.SegmentIds[course.Segment[segStart]]) clean.Append(char.IsLetterOrDigit(ch) ? ch : '_');
                marks.Add((mid, $"{marks.Count:00}_{clean}"));
                segStart = i;
            }
            int next = 0;
            float t0 = Time.time, fpsAcc = 0f; int fpsN = 0; float worst = 0f;
            var timing = new FrameStats();
            while (next < marks.Count)
            {
                timing.Tick(Time.unscaledDeltaTime);
                fpsAcc += 1f / Mathf.Max(1e-4f, Time.unscaledDeltaTime); fpsN++; worst = Mathf.Max(worst, Time.unscaledDeltaTime);
                if (pilot.RaceDistance >= marks[next].dist)
                {
                    yield return new WaitForEndOfFrame();
                    ScreenCapture.CaptureScreenshot(Path.Combine(shotDir, marks[next].name + ".png"));
                    log.AppendLine($"{marks[next].name}: dist {pilot.RaceDistance:0} m  v {Units.ToKmh(Craft.Speed):0} km/h  solo {Craft.Grounded}  {timing.Summary}");
                    next++;
                }
                if (Time.time - t0 > 240f) { log.AppendLine("TIMEOUT"); break; }
                yield return null;
            }
            log.AppendLine($"tempo {Time.time - t0:0.0} s · fps médio {fpsAcc / Mathf.Max(1, fpsN):0} · pior frame {worst * 1000f:0.0} ms");
            File.WriteAllText(Path.Combine(shotDir, "autotest.txt"), log.ToString());
            Debug.Log("[RDD autotest] " + log);
            yield return new WaitForSeconds(0.5f);
            Application.Quit();
        }
    }
}
