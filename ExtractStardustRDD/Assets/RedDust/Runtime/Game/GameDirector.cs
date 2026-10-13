using System.Collections.Generic;
using System.Linq;
using RedDust.Meta;
using RedDust.Presentation;
using RedDust.Track;
using RedDust.Vehicle;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace RedDust.Game
{
    /// <summary>
    /// Fluxo do jogo (Doc 01 §4.3): Hangar/menus → briefing → contagem → corrida → EXTRACTED/DESTROYED/… → resultados
    /// e distribuição do Pool → regresso ao Hangar. Modos: EXPLORAÇÃO (sozinho, sem risco), EXTRAÇÃO vs bots e
    /// PVP LOCAL (2 jogadores em ecrã dividido + bots). Substitui o diretor do laboratório (ver GameBoot).
    /// </summary>
    public partial class GameDirector : MonoBehaviour
    {
        public Light sun;

        enum Page { Main, Hangar, Pick, Backpack, Market, Cache, Report, Options, Briefing, Countdown, Race, Pause, Results }
        Page screen = Page.Main;

        CourseGraph graph;
        CourseData course;
        string courseTitle;
        bool mobile;
        readonly PlayerProfile[] profiles = new PlayerProfile[2];
        int editing;                    // perfil em edição no Hangar/Mochila (0 = jogador 1, 1 = jogador 2)
        GameMode mode;
        RaceSession session;
        Rng rng;

        sealed class View { public Camera cam; public ChaseCamera chase; public SpeedFx fx; public Racer racer; public Rect norm; }
        readonly List<View> views = new List<View>();
        Camera menuCam;
        CraftController preview;
        float orbitYaw = 200f, orbitDist = 13f, countdown, endTimer = -1f;
        bool autoExtract;

        // escolhas que sobrevivem à troca de pista (cena)
        static int botCount = -1, difficulty = 1;
        // opções (conveniência por máquina)
        float shake = 1f, fovExtra;
        bool vibration = true;

        PlayerProfile P => profiles[editing] ?? profiles[0];

        static bool sceneArgUsed;

        void Start()
        {
            // -pista sandbox|red_dust_divide: escolhe a pista inicial (testes automáticos)
            string want = CommandLine.Value("-pista");
            if (!sceneArgUsed && !string.IsNullOrEmpty(want))
            {
                sceneArgUsed = true;
                for (int i = 0; i < SceneManager.sceneCountInBuildSettings; i++)
                {
                    string path = SceneUtility.GetScenePathByBuildIndex(i);
                    if (path.ToLowerInvariant().Contains(want.ToLowerInvariant()) && i != SceneManager.GetActiveScene().buildIndex) { SceneManager.LoadScene(i); return; }
                }
            }
            graph = CourseRuntime.Active != null ? CourseRuntime.Active.Graph : null;
            course = graph?.Main.Data;
            if (course == null) { Debug.LogError("[RDD] percurso em falta"); enabled = false; return; }
            courseTitle = CourseRuntime.Active.title;
            mobile = Application.isMobilePlatform || CommandLine.Int("-quality", -1) == 0;
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = mobile ? 60 : Mathf.Clamp((int)Screen.currentResolution.refreshRateRatio.value, 60, 144);
            Time.fixedDeltaTime = 1f / 90f;
            EnvironmentRig.Apply(sun, mobile);
            EnvironmentRig.CreatePost(transform, mobile);
            GameInput.Init();
            if (botCount < 0) botCount = mobile ? 7 : 11;
            shake = PlayerPrefs.GetFloat("rdd_shake", 1f);
            fovExtra = PlayerPrefs.GetFloat("rdd_fov", 0f);
            vibration = PlayerPrefs.GetInt("rdd_vibration", 1) == 1;
            rng = Rng.FromTime();
            profiles[0] = ProfileStore.Load("p1", "Piloto 1");
            menuCam = MakeCamera("Menu Camera", true);
            RefreshPreview();
            if (CommandLine.Has("-rddextract"))
            {
                autoExtract = true;
                botCount = Mathf.Clamp(CommandLine.Int("-bots", 7), 1, 19);
                StartRace(GameMode.Extraction);
                Time.timeScale = Mathf.Clamp(CommandLine.Float("-timescale", 1f), 0.5f, 8f);
            }
        }

        // ------------------------------------------------------------------ câmeras

        Camera MakeCamera(string name, bool listener)
        {
            var go = new GameObject(name);
            if (listener) go.tag = "MainCamera";
            var cam = go.AddComponent<Camera>();
            cam.nearClipPlane = 0.3f;
            cam.farClipPlane = 16000f;
            var data = go.AddComponent<UniversalAdditionalCameraData>();
            data.renderPostProcessing = true;
            data.antialiasing = mobile ? AntialiasingMode.None : AntialiasingMode.SubpixelMorphologicalAntiAliasing;
            if (listener) go.AddComponent<AudioListener>();
            return cam;
        }

        void CreateViews(List<Racer> humans)
        {
            bool split = humans.Count > 1;
            for (int i = 0; i < humans.Count; i++)
            {
                var v = new View { racer = humans[i] };
                v.cam = MakeCamera($"Camera P{i + 1}", i == 0);
                v.norm = split ? new Rect(0f, i == 0 ? 0.5f : 0f, 1f, 0.5f) : new Rect(0f, 0f, 1f, 1f);
                v.cam.rect = v.norm;
                v.chase = v.cam.gameObject.AddComponent<ChaseCamera>();
                v.chase.Attach(humans[i].craft);
                v.chase.shakeScale = shake;
                v.chase.fovOffset = fovExtra + (split ? -6f : 0f);
                v.fx = SpeedFx.Attach(v.cam, humans[i].craft, v.chase, mobile || split);
                if (split)
                {
                    // cada câmera só vê o seu pós-processamento e as suas partículas
                    int layer = i == 0 ? 30 : 31, other = i == 0 ? 31 : 30;
                    v.fx.Isolate(layer);
                    v.cam.cullingMask = ~(1 << other);
                    v.cam.GetComponent<UniversalAdditionalCameraData>().volumeLayerMask = 1 | (1 << layer);
                }
                views.Add(v);
            }
        }

        void DestroyViews()
        {
            foreach (var v in views) if (v.cam != null) Destroy(v.cam.gameObject);
            views.Clear();
        }

        // ------------------------------------------------------------------ Hangar (nave em 3D)

        void RefreshPreview()
        {
            if (preview != null) Destroy(preview.gameObject);
            var p = P;
            var c = Catalog.ChassisOf(p.chassis);
            preview = ShipBuilder.Spawn("Hangar", c, ShipBuilder.Mounted(p), PaintFor(editing, c), out _, out _);
            preview.autoStep = false;
            int st = course.StationAt(course.Start + 40f);
            Vector3 n = course.Up[st];
            preview.Place(course.Center[st] + n * 1.6f, Quaternion.LookRotation(course.Tangent[st], n), 0f);
            preview.Body.isKinematic = true;          // só visual: não paira nem cai enquanto se monta a build
            SectorStreamer.Focus.Clear();
            SectorStreamer.Focus.Add(preview.transform);
        }

        Color PaintFor(int player, ChassisDef c) => player == 1 ? new Color(0.1f, 0.55f, 0.95f) : ShipBuilder.Paint(c.paint);

        void LateUpdate()
        {
            if (menuCam == null || !menuCam.gameObject.activeSelf || preview == null) return;
            // órbita do Hangar: roda sozinha; analógico direito / rato com botão direito para rodar; gatilhos / roda para zoom
            float dt = Time.unscaledDeltaTime;
            float spin = 9f;
            var pad = Gamepad.current;
            if (pad != null) { spin += pad.rightStick.ReadValue().x * 120f; orbitDist -= (pad.rightTrigger.ReadValue() - pad.leftTrigger.ReadValue()) * 6f * dt; }
            var mouse = Mouse.current;
            if (mouse != null)
            {
                if (mouse.rightButton.isPressed) spin += mouse.delta.ReadValue().x * 12f;
                orbitDist -= mouse.scroll.ReadValue().y * 0.004f;
            }
            orbitDist = Mathf.Clamp(orbitDist, 6f, 18f);
            orbitYaw += spin * dt;
            Vector3 target = preview.transform.position + preview.transform.up * 0.4f;
            Quaternion q = preview.transform.rotation * Quaternion.Euler(14f, orbitYaw, 0f);
            Vector3 pos = target + q * new Vector3(0f, 0f, -orbitDist);
            // nave ao centro, entre a lista (esquerda) e o cartão de informação (direita): é a protagonista do Hangar
            menuCam.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, preview.transform.up));
            menuCam.fieldOfView = 50f;
        }

        // ------------------------------------------------------------------ corrida

        void StartRace(GameMode m)
        {
            mode = m;
            if (m == GameMode.LocalVersus && profiles[1] == null) profiles[1] = ProfileStore.Load("p2", "Piloto 2");
            if (preview != null) Destroy(preview.gameObject);
            CleanupRace();
            session = new RaceSession(m, graph, courseTitle, rng);

            // comandos: 2 comandos → um cada; 1 comando → J1 teclado, J2 comando; nenhum → teclado dividido
            var pads = Gamepad.all;
            PilotInput in1, in2 = null;
            if (m == GameMode.LocalVersus)
            {
                if (pads.Count >= 2) { in1 = new PilotInput(pads[0], KeyScheme.Full); in2 = new PilotInput(pads[1], KeyScheme.None); }
                else if (pads.Count == 1) { in1 = new PilotInput(null, KeyScheme.Full); in2 = new PilotInput(pads[0], KeyScheme.None); }
                else { in1 = new PilotInput(null, KeyScheme.Left); in2 = new PilotInput(null, KeyScheme.Right); }
            }
            else in1 = new PilotInput(Gamepad.current, KeyScheme.Full);
            in1.vibration = vibration;
            if (in2 != null) in2.vibration = vibration;

            var humans = new List<Racer> { session.AddHuman(profiles[0], 0, in1, PaintFor(0, Catalog.ChassisOf(profiles[0].chassis))) };
            if (m == GameMode.LocalVersus) humans.Add(session.AddHuman(profiles[1], 1, in2, PaintFor(1, Catalog.ChassisOf(profiles[1].chassis))));
            if (autoExtract) humans[0].brain = new BotBrain(graph, Personality.Technical, 1, 0f, rng);

            var order = new List<Racer>();
            if (m != GameMode.Exploration)
            {
                int n = Mathf.Clamp(botCount, 1, 20 - humans.Count);
                var bots = new List<Racer>();
                for (int i = 0; i < n; i++) bots.Add(session.AddBot(i, difficulty, ((i % 5) - 2) * 0.3f));
                rng.Shuffle(bots);
                order.AddRange(bots);
                // jogadores a meio do pelotão (2.ª/3.ª fila): a largada é uma decisão, não um passeio
                int slot = Mathf.Min(order.Count, 7);
                order.InsertRange(slot, humans);
            }
            else order.AddRange(humans);
            session.PlaceGrid(order);

            SectorStreamer.Focus.Clear();
            foreach (var r in session.racers) SectorStreamer.Focus.Add(r.craft.transform);
            menuCam.gameObject.SetActive(false);
            CreateViews(humans);
            countdown = 3.2f;
            endTimer = -1f;
            screen = Page.Countdown;
        }

        void CleanupRace()
        {
            Time.timeScale = 1f;
            DestroyViews();
            session?.Dispose();
            session = null;
        }

        void BackToMenu(Page to = Page.Main)
        {
            CleanupRace();
            menuCam.gameObject.SetActive(true);
            RefreshPreview();
            Go(to);
        }

        void FixedUpdate()
        {
            if (session == null) return;
            session.Tick(Time.fixedDeltaTime);
        }

        void Update()
        {
            if (profiles[0] == null) return;   // cena a ser trocada por -pista: ainda sem perfil (evita NullReference no 1.º frame)
            GameInput.Tick();
            GameAudio.Music(screen == Page.Race || screen == Page.Countdown || screen == Page.Pause);
            switch (screen)
            {
                case Page.Countdown:
                    int beepBefore = Mathf.CeilToInt(countdown);
                    countdown -= Time.deltaTime;
                    if (Mathf.CeilToInt(countdown) != beepBefore && countdown > 0f && beepBefore <= 3) GameAudio.Play("beep", 0.8f);
                    if (countdown <= 0f)
                    {
                        GameAudio.Play("go", 0.9f);
                        session.started = true;
                        screen = Page.Race;
                        foreach (var r in session.Humans) r.input?.Rumble(0.5f, 0.6f, 0.25f);
                    }
                    RaceInput(false);
                    break;
                case Page.Race:
                    RaceInput(true);
                    if (session.HumansDone)
                    {
                        if (endTimer < 0f) endTimer = autoExtract ? 0.5f : 3f;
                        endTimer -= Time.deltaTime;
                        if (endTimer <= 0f || (GameInput.Confirm() && endTimer < 2.5f)) EndRace();
                    }
                    break;
                default:
                    MenuInput();
                    break;
            }
            if (session != null) foreach (var r in session.Humans) r.input?.Tick(r.paint);
        }

        void RaceInput(bool live)
        {
            foreach (var v in views)
            {
                var r = v.racer;
                if (r.input == null) continue;
                v.chase.lookYawInput = r.input.Look();
                v.chase.lookBack = r.input.LookBack();
                if (r.input.PausePressed() || (views.Count == 1 && GameInput.Pause())) { OpenPause(); return; }
                if (!live || !r.Active) continue;
                int c = r.input.ConsumablePressed();
                string used = c == 9 ? r.Use(r.selected) : c >= 0 ? r.Use(c) : null;
                if (used != null) session.Notify(used, new Color(0.6f, 1f, 0.8f), 2f, r.player);
                int sd = r.input.SelectDelta();
                if (sd != 0) r.selected = (r.selected + sd + Economy.LoadoutSlots) % Economy.LoadoutSlots;
                if (r.input.ResetPressed()) session.Respawn(r, true);
                if (r.craft.Boosting && r.craft.Grounded) r.input.Rumble(0.06f, 0.12f, 0.05f);
                if (r.craft.Drifting) r.input.Rumble(0.12f, 0.05f, 0.05f);
            }
        }

        void EndRace()
        {
            session.Finish();
            foreach (var r in session.Humans) r.input?.Stop();
            Go(Page.Results);
            if (autoExtract) AutoExtractReport();
        }

        void OpenPause()
        {
            Time.timeScale = 0f;
            foreach (var r in session.Humans) r.input?.Stop();
            Go(Page.Pause);
        }

        void ClosePause()
        {
            Time.timeScale = 1f;
            screen = session.started ? Page.Race : Page.Countdown;
        }

        void OnApplicationQuit()
        {
            if (session != null) foreach (var r in session.Humans) r.input?.Stop();
            foreach (var p in profiles) if (p != null) ProfileStore.Save(p);
        }

        /// <summary>Autoteste sem janela (-rddextract): extração com o jogador em piloto automático, verifica o Pool e sai.</summary>
        void AutoExtractReport()
        {
            var poolIds = session.pool.Entries.Select(e => e.item.id).ToList();
            var awarded = session.poolAwards.Values.SelectMany(x => x).Select(i => i.id).ToList();
            bool noDup = awarded.Distinct().Count() == awarded.Count;
            bool noInvent = awarded.All(poolIds.Contains);
            var rep = session.reports.FirstOrDefault();
            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"[RDD extract] {courseTitle} · {session.racers.Count} pilotos · tempo {RaceHud.FormatTime(session.time)}");
            foreach (var r in session.Classification())
                sb.AppendLine($"  {r.position,2}. {r.name,-10} {r.chassis.name,-8} {r.state,-10} casco {r.HullFrac:P0} comb. {r.fuel:P0} {(r.brain != null ? BotBrain.Label(r.brain.personality) : "")}");
            sb.AppendLine($"  Pool: {session.pool.Count} peças, {Fmt.Dust(session.pool.Valuation)} · distribuídas {awarded.Count} · sem duplicar {noDup} · sem inventar {noInvent}");
            if (rep != null) sb.AppendLine($"  Jogador: {rep.state} {rep.position}/{rep.racers} · ✦ +{rep.stardustTotal} · perdeu {rep.lost.Count} · ganhou {rep.gained.Count}");
            bool ok = noDup && noInvent && rep != null;
            sb.AppendLine(ok ? "[RDD extract] OK" : "[RDD extract] FALHA");
            Debug.Log(sb.ToString());
            Application.Quit(ok ? 0 : 1);
        }

        void ChangeCourse(int dir)
        {
            int count = SceneManager.sceneCountInBuildSettings;
            if (count < 2) { Toast("Só há uma pista nesta build."); return; }
            foreach (var p in profiles) if (p != null) ProfileStore.Save(p);
            SceneManager.LoadScene((SceneManager.GetActiveScene().buildIndex + dir + count) % count);
        }
    }
}
