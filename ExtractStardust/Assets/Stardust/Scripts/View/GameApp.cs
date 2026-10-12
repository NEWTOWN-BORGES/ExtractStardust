using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace Stardust
{
    /// <summary>
    /// Boots the island (world, atmosphere, audio, effects), runs the menus and the race loop of every mode
    /// (Expedition, circuits, salt drag, Explore, split-screen and Wi-Fi), and turns race events into effects,
    /// audio, HUD messages, rumble and camera work.
    /// </summary>
    public partial class GameApp : MonoBehaviour
    {
        public const float Dt = IslandRace.Dt;
        public enum State { Loading, Menu, Garage, Options, Events, Lobby, Intro, Racing, Paused, Map, Post, Results }

        public static GameApp I;
        public State state;

        // settings (PlayerPrefs)
        public int quality;
        public float volume = 0.9f, musicVol = 0.45f;
        public bool shake = true;
        public int camView;

        public IslandWorld world;
        Atmosphere atmo;
        Transform worldRoot, raceRoot;
        public IslandRace race;
        public EventDef currentEvent;
        GateMarkers gateMarkers;
        readonly List<ChaseCam> rigs = new List<ChaseCam>();
        readonly List<IslandHud> huds = new List<IslandHud>();
        readonly List<Racer> humans = new List<Racer>();
        readonly HashSet<Strike> seenStrikes = new HashSet<Strike>();
        ChaseCam menuRig;
        Hovercraft showCraft;
        ShipVisual showcase;
        GameAudio sfx;
        Fx fx;
        bool twoPlayers;
        float acc, introT, slowmoT;
        int lastCount = 9;
        bool settling;
        RaceResult result;
        float[] humanDoneT;
        string pendingEventId;

        // automated test / screenshot mode (command line)
        bool autotest, autotest2p;
        string autoEvent = "expedicao";
        int botOverride = -1;
        string shotDir;
        float testT;
        int testStage;
        float stageClock;
        bool stageWarped, introShot;
        float stepMs, stepsAvg, presentMs, atmoMs, stageDt, stageMaxDt;
        int stageFrames;

        public static bool Mobile => Application.isMobilePlatform;
        float FarClip => quality == 0 ? 9000f : 15000f;

        void Awake()
        {
            I = this;
            // frame pacing by target rate (vSync made the window run at 20 fps when it was not in front)
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = Mobile ? 60 : Mathf.Clamp(Mathf.RoundToInt((float)Screen.currentResolution.refreshRateRatio.value), 60, 144);
            Screen.sleepTimeout = SleepTimeout.NeverSleep;
            Physics.simulationMode = SimulationMode.Script;
            Physics.autoSyncTransforms = true;
            if (Mobile)
            {
                Screen.orientation = ScreenOrientation.AutoRotation;
                Screen.autorotateToPortrait = false;
                Screen.autorotateToPortraitUpsideDown = false;
                Screen.autorotateToLandscapeLeft = true;
                Screen.autorotateToLandscapeRight = true;
            }
            LoadSettings();
            ParseArgs();
        }

        void Start()
        {
            SaveSystem.TestMode = autotest;
            if (autotest) SaveSystem.Reset();
            SaveSystem.Load();
            BuildUIRoot();
            sfx = GameAudio.Create(transform);
            sfx.master = volume;
            sfx.musicVol = musicVol;
            StartCoroutine(Boot());
        }

        void ParseArgs()
        {
            var args = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "-autotest") autotest = true;
                if (args[i] == "-autotest2p") { autotest = true; autotest2p = true; }
                if (args[i] == "-event" && i + 1 < args.Length) autoEvent = args[i + 1];
                if (args[i] == "-bots" && i + 1 < args.Length && int.TryParse(args[i + 1], out int nb)) botOverride = nb;
                if (args[i] == "-shotdir" && i + 1 < args.Length) shotDir = args[i + 1];
                if (args[i] == "-quality" && i + 1 < args.Length && int.TryParse(args[i + 1], out int q)) quality = Mathf.Clamp(q, 0, 2);
            }
        }

        void LoadSettings()
        {
            quality = PlayerPrefs.GetInt("sd_quality", Mobile ? 0 : 2);
            volume = PlayerPrefs.GetFloat("sd_volume", 0.9f);
            musicVol = PlayerPrefs.GetFloat("sd_music", 0.45f);
            shake = PlayerPrefs.GetInt("sd_shake", 1) == 1;
            camView = PlayerPrefs.GetInt("sd_cam", 0);
        }

        public void SaveSettings()
        {
            PlayerPrefs.SetInt("sd_quality", quality);
            PlayerPrefs.SetFloat("sd_volume", volume);
            PlayerPrefs.SetFloat("sd_music", musicVol);
            PlayerPrefs.SetInt("sd_shake", shake ? 1 : 0);
            PlayerPrefs.SetInt("sd_cam", camView);
            PlayerPrefs.Save();
            if (sfx) { sfx.master = volume; sfx.musicVol = musicVol; }
        }

        IEnumerator Boot()
        {
            state = State.Loading;
            ShowLoading("A preparar a ilha…");
            yield return null;
            worldRoot = new GameObject("WorldRoot").transform;
            atmo = Atmosphere.Create(worldRoot, quality);
            world = IslandWorld.Create(worldRoot, quality);
            yield return world.Build((p, s) => { SetLoading(p); SetLoadingText(s); });
            fx = Fx.Create(worldRoot, quality);
            // menu showcase: a parked racer with an orbiting camera near the expedition start
            var spot = world.data.start;
            showCraft = new Hovercraft();
            var g = world.HeightAt(spot.Pos.x, spot.Pos.z);
            world.EnsureCollidersAt(spot.Pos, 300f);
            showCraft.Place(new Vector3(spot.Pos.x, g, spot.Pos.z), spot.Dir, 0f);
            for (int i = 0; i < 90; i++) showCraft.Step(Dt);
            showcase = ShipVisual.Create(worldRoot, "vespa", PlayerLivery, quality, true);
            menuRig = ChaseCam.Create(transform, "MenuCam", new Rect(0, 0, 1, 1), FarClip, true);
            menuRig.SetTarget(showCraft, showcase);
            menuRig.SetMode(ChaseCam.Mode.Orbit);
            world.viewers.Clear();
            world.viewers.Add(menuRig.transform);
            world.physicsFoci.Clear();
            world.physicsFoci.Add(() => showCraft.position);
            sfx.SetListener(menuRig.transform);
            atmo.Tick(showCraft.position, false, 0f, true);
            atmo.RefreshReflections();
            HideLoading();
            if (autotest) StartCoroutine(AutotestBoot());
            else ShowMenu();
        }

        IEnumerator AutotestBoot()
        {
            ShowMenu();
            yield return new WaitForSecondsRealtime(1.5f);
            Shot("00_menu");
            yield return new WaitForSecondsRealtime(0.5f);
            ShowGarage();
            yield return new WaitForSecondsRealtime(1.2f);
            Shot("01_garage");
            yield return new WaitForSecondsRealtime(0.5f);
            StartEvent(EventById(autoEvent), autotest2p);
        }

        public static Color PlayerLivery => new Color(0.15f, 0.8f, 1f);

        public EventDef EventById(string id)
        {
            if (id == "explorar") return EventDef.Explore(world.data);
            foreach (var e in world.data.events) if (e.id == id) return EventDef.FromWorld(e);
            return EventDef.Expedition(world.data);
        }

        // ------------------------------------------------------------------ pilots

        Pilot MakePlayerPilot()
        {
            var save = SaveSystem.Current;
            var p = new Pilot
            {
                name = "Você", tag = "P1", human = true, humanSlot = 0, persistent = true,
                equip = save.EquippedArray(), insuredId = save.insuredId,
                livery = PlayerLivery, livery2 = new Color(0.95f, 0.95f, 1f), number = 7, model = "vespa",
            };
            p.cons = new[] { (Consumable)save.consA, (Consumable)save.consB };
            p.consCount = new[] { 2, 2 };
            return p;
        }

        static readonly string[] BotNames =
        {
            "Vex Morrow", "Kaia Sunder", "Rook Halden", "Juno Strand", "Taro Quill", "Nyx Ardent", "Bram Kessler", "Sol Varga",
            "Ivo Drax", "Mira Cole", "Dax Orion", "Lena Voss", "Cass Rhee", "Odo Brann", "Zara Kline"
        };

        public static readonly string[] ShipModels = { "vespa", "racer_twin", "racer_hammer", "racer_needle", "racer_ram", "racer_manta" };

        List<Pilot> MakePilots(EventDef def, bool split, int seed)
        {
            var rng = new System.Random(seed);
            var list = new List<Pilot>();
            int botCount = botOverride >= 0 ? Mathf.Min(botOverride, def.botCount) : def.botCount;
            if (split) botCount = Mathf.Min(botCount, quality == 0 ? 6 : 12);
            for (int i = 0; i < botCount; i++)
            {
                var style = (BotStyle)(i % 3);
                var bp = new Pilot
                {
                    name = BotNames[i % BotNames.Length],
                    persona = BotPersona.Make(style, rng),
                    livery = Color.HSVToRGB((float)rng.NextDouble(), Noise.Range(rng, 0.55f, 0.9f), Noise.Range(rng, 0.65f, 0.95f)),
                    livery2 = Color.HSVToRGB((float)rng.NextDouble(), 0.2f, 0.95f),
                    number = 10 + i,
                    model = ShipModels[1 + i % (ShipModels.Length - 1)],
                };
                for (int s = 0; s < 6; s++)
                    bp.equip[s] = Catalog.Create((Slot)s, Catalog.RollRarity(rng, style == BotStyle.Aggressive ? 0.3f : 0f), rng, "Emissão IA", bp.name);
                ItemInst best = null;
                foreach (var it in bp.equip) if (best == null || it.value > best.value) best = it;
                bp.insuredId = best.id;
                bp.cons = new[] { Consumable.RepairGel, Consumable.FuelCell };
                bp.consCount = new[] { 2, style == BotStyle.Conservative ? 2 : 1 };
                list.Add(bp);
            }
            var p1 = MakePlayerPilot();
            int insertAt = Mathf.Min(def.kind == EventKind.Expedition ? 8 : list.Count / 2, list.Count);
            list.Insert(insertAt, p1);
            if (split)
            {
                var guestRng = new System.Random(777);
                var p2 = new Pilot
                {
                    name = "Jogador 2", tag = "P2", human = true, humanSlot = 1, persistent = false,
                    livery = new Color(1f, 0.45f, 0.1f), livery2 = new Color(0.15f, 0.15f, 0.18f), number = 22, model = "vespa",
                };
                for (int s = 0; s < 6; s++) p2.equip[s] = Catalog.Create((Slot)s, s % 2 == 0 ? Rarity.Uncommon : Rarity.Common, guestRng, "Kit convidado", "p2");
                p2.insuredId = p2.equip[0].id;
                list.Insert(insertAt + 1, p2);
                p1.name = "Jogador 1";
            }
            return list;
        }

        // ------------------------------------------------------------------ race setup

        public void StartEvent(EventDef def, bool split)
        {
            StopAllCoroutines();
            ClearRace();
            HideAllScreens();
            currentEvent = def;
            twoPlayers = split && !Mobile;
            mpRace = false;
            int seed = Random.Range(1, 1 << 30);
            var pilots = MakePilots(def, twoPlayers, seed);
            raceRoot = new GameObject("Race").transform;
            race = new IslandRace(world, def, pilots, seed);
            humans.Clear();
            foreach (var r in race.racers)
            {
                if (r.pilot.human)
                {
                    r.input = new IslandInput(twoPlayers ? r.pilot.humanSlot + 1 : 0);
                    if (autotest) { r.bot = MakeAutopilot(r); if (r.bot != null) r.gateRouteIdx = race.GateIndices(r.bot.route); }
                    humans.Add(r);
                }
                r.vis = ShipVisual.Create(raceRoot, r.pilot.model, r.pilot.livery, quality, r.pilot.human);
            }
            FinishRaceSetup(def);
        }

        /// <summary>Gates, cameras, voices and HUDs for the racers of the new race (local or Wi-Fi).</summary>
        void FinishRaceSetup(EventDef def)
        {
            humanDoneT = new float[humans.Count];
            gateMarkers = GateMarkers.Create(raceRoot, world, def, def.kind == EventKind.Explore);
            gateMarkers.Highlight(def.kind == EventKind.Explore ? -1 : 0, def.kind != EventKind.Circuit);

            // cameras
            if (menuRig) menuRig.gameObject.SetActive(false);
            if (showcase) showcase.gameObject.SetActive(false);
            world.viewers.Clear();
            for (int i = 0; i < humans.Count; i++)
            {
                var rect = humans.Count == 1 ? new Rect(0, 0, 1, 1) : (i == 0 ? new Rect(0, 0.5f, 1, 0.5f) : new Rect(0, 0, 1, 0.5f));
                var rig = ChaseCam.Create(raceRoot, "Cam_P" + (i + 1), rect, FarClip, i == 0);
                rig.shakeScale = shake ? 1f : 0.15f;
                rig.SetTarget(humans[i].craft, humans[i].vis);
                rig.SetMode(def.kind == EventKind.Explore ? ChaseCam.Mode.Chase : ChaseCam.Mode.Intro);
                rigs.Add(rig);
                world.viewers.Add(rig.transform);
            }
            world.physicsFoci.Clear();
            foreach (var r in race.racers)
            {
                var rr = r;
                world.physicsFoci.Add(() => rr.ghost ? new Vector3(1e7f, 0f, 1e7f) : rr.craft.position);
            }
            sfx.SetListener(rigs[0].transform);
            sfx.ClearVoices();
            foreach (var h in humans) sfx.AddVoice(h);
            sfx.PlayMusic(def.kind != EventKind.Explore);
            // HUDs
            for (int i = 0; i < humans.Count; i++)
            {
                var region = humans.Count == 1
                    ? UIKit.Rect(hudLayer, "Region", Vector2.zero, Vector2.one)
                    : UIKit.Rect(hudLayer, "Region", i == 0 ? new Vector2(0, 0.5f) : Vector2.zero, i == 0 ? Vector2.one : new Vector2(1, 0.5f));
                huds.Add(new IslandHud(region, race, humans[i], Mobile, humans.Count > 1));
            }
            if (Mobile) BuildTouchControls();
            hudLayer.gameObject.SetActive(true);
            introT = 0f;
            lastCount = 9;
            acc = 0f;
            settling = false;
            result = null;
            slowmoT = 0f;
            Time.timeScale = 1f;
            testT = 0f;
            testStage = 0;
            stageWarped = false;
            introShot = false;
            atmo.Tick(humans[0].craft.position, false, 0f, true);
            if (def.kind == EventKind.Explore)
            {
                race.countdown = 0.01f;
                state = State.Racing;
                foreach (var h in huds) h.Message("EXPLORAR", IslandInput.Hint(humans[0].input.UsingGamepad, Mobile), 7f);
            }
            else
            {
                state = State.Intro;
                foreach (var h in huds) h.Message(def.name.ToUpperInvariant(), def.subtitle, 6.5f);
            }
        }

        BotPilot MakeAutopilot(Racer r)
        {
            var bot = new BotPilot(5) { skill = 1f, neverErr = true, self = r.craft, others = race.crafts, aggression = 0.6f };
            if (race.def.kind == EventKind.Expedition)
            {
                var rt = EventDef.ExpeditionRoute(world.data, new int[world.data.sections.Length], out var jumps);
                bot.SetRoute(rt, jumps);
            }
            else if (race.def.lapRoute != null) { var rt = race.def.LapsRoute(out var jumps); bot.SetRoute(rt, jumps); }
            else return null;
            bot.Resync();
            return bot;
        }

        void ClearRace()
        {
            foreach (var r in rigs) if (r) Destroy(r.gameObject);
            rigs.Clear();
            huds.Clear();
            humans.Clear();
            seenStrikes.Clear();
            if (hudLayer) foreach (Transform c in hudLayer) Destroy(c.gameObject);
            if (raceRoot) Destroy(raceRoot.gameObject);
            gateMarkers = null;
            touch = null;
            race = null;
            if (sfx) { sfx.ClearVoices(); sfx.SetCave(false); }
            if (fx) fx.ResetAll();
        }

        // ------------------------------------------------------------------ main loop

        void Update()
        {
            float dt = Time.unscaledDeltaTime;
            if (state == State.Menu || state == State.Garage || state == State.Options || state == State.Loading || state == State.Events || state == State.Lobby)
            {
                if (sfx) sfx.Tick(null, true);
                UpdateMenus(dt);
                if (menuRig && menuRig.gameObject.activeSelf && showCraft != null)
                {
                    showcase.Pose(showCraft.position, showCraft.Rotation, showCraft, dt);
                    menuRig.Tick(showCraft.position, dt);
                    atmo.Tick(menuRig.transform.position, false, dt);
                }
                return;
            }
            if (race == null) return;

            UpdateNetRace(dt);
            foreach (var h in humans) h.input.Poll(dt);
            bool pause = false, cam = false, map = false;
            for (int i = 0; i < humans.Count; i++)
            {
                var inp = humans[i].input;
                if (inp.pause) pause = true;
                if (inp.map) map = true;
                if (inp.camCycle)
                {
                    cam = true;
                    rigs[i].SetMode(rigs[i].mode == ChaseCam.Mode.Cockpit ? ChaseCam.Mode.Chase : ChaseCam.Mode.Cockpit);
                }
                if (inp.recover && state == State.Racing) race.RequestRecover(humans[i]);
                rigs[i].lookInput = inp.look;
                rigs[i].lookCenter = inp.lookCenter;
            }
            if (cam) { camView = rigs[0].mode == ChaseCam.Mode.Cockpit ? 1 : 0; SaveSettings(); }
            if (state == State.Map) { UpdateMap(dt); return; }
            if (map && (state == State.Racing || state == State.Paused) && race.def.kind == EventKind.Explore) { ShowMap(); return; }
            if (pause && (state == State.Racing || state == State.Intro || state == State.Post)) { Pause(); return; }
            if (state == State.Paused) { UpdatePause(); return; }

            if (state == State.Intro)
            {
                introT += dt;
                if (autotest && !introShot && introT > 1.2f) { introShot = true; Shot("05_intro"); }
                bool skip = introT > 1.2f && (MenuInput.AnyConfirm() || (autotest && introT > 1.6f));
                if (introT > 6.5f || skip)
                {
                    state = State.Racing;
                    foreach (var r in rigs) r.SetMode(camView == 1 ? ChaseCam.Mode.Cockpit : ChaseCam.Mode.Chase);
                    foreach (var h in huds) h.Message("", "", 0.01f);
                }
                // the field idles on the grid while the camera flies in
                acc += Mathf.Min(dt, 0.1f);
                while (acc >= Dt) { foreach (var r in race.racers) { r.prevPos = r.craft.position; r.prevYaw = r.craft.yaw; r.craft.Step(Dt); } acc -= Dt; }
                Present(dt, Mathf.Clamp01(acc / Dt));
                return;
            }

            // time scale for cinematic slow motion (fast in autotest)
            if (slowmoT > 0f) { slowmoT -= dt; Time.timeScale = Mathf.Lerp(1f, 0.3f, Mathf.Clamp01(slowmoT / 0.6f)); }
            else Time.timeScale = 1f;

            // fixed-step simulation
            acc += Mathf.Min(Time.deltaTime, 0.1f);
            int steps = 0;
            var swStep = System.Diagnostics.Stopwatch.StartNew();
            while (acc >= Dt && steps < 8) { race.Step(Dt); acc -= Dt; steps++; }
            stepMs = Mathf.Lerp(stepMs, (float)swStep.Elapsed.TotalMilliseconds, 0.1f);
            stepsAvg = Mathf.Lerp(stepsAvg, steps, 0.1f);
            if (steps >= 8) acc = 0f;
            if (settling) race.FastForward(900);
            float alpha = Mathf.Clamp01(acc / Dt);
            if (settling) race.events.Clear();
            ProcessEvents();
            var swP = System.Diagnostics.Stopwatch.StartNew();
            Present(dt, alpha);
            presentMs = Mathf.Lerp(presentMs, (float)swP.Elapsed.TotalMilliseconds, 0.1f);
            UpdateCountdown();
            UpdatePost(dt);
            if (autotest) UpdateAutotest(dt);
        }

        /// <summary>Ships, cameras, HUDs, light, audio for this frame.</summary>
        void Present(float dt, float alpha)
        {
            foreach (var r in race.racers)
            {
                bool show = r.state != PilotState.Destroyed || race.raceTime - r.destroyTime < 0.1f;
                if (r.vis.gameObject.activeSelf != show) r.vis.gameObject.SetActive(show);
                if (!show) continue;
                var p = r.InterpolatedPos(alpha);
                r.vis.Pose(p, Quaternion.Euler(0f, r.InterpolatedYaw(alpha) * Mathf.Rad2Deg, 0f), r.craft, dt);
            }
            for (int i = 0; i < rigs.Count; i++)
            {
                rigs[i].Tick(humans[i].InterpolatedPos(alpha), dt);
                huds[i].Update(dt, alpha, rigs[i].transform.eulerAngles.y * Mathf.Deg2Rad);
            }
            var swA = System.Diagnostics.Stopwatch.StartNew();
            var view = rigs[0].transform.position;
            bool cave = world.InCave(humans[0].craft.position);
            atmo.Tick(view, cave, dt);
            sfx.SetCave(cave);
            sfx.Tick(race.racers, state == State.Paused);
            atmoMs = Mathf.Lerp(atmoMs, (float)swA.Elapsed.TotalMilliseconds, 0.1f);
            if (gateMarkers != null && race.def.kind != EventKind.Explore)
            {
                var me = humans[0];
                int next = me.nextGate < race.def.sequencePhys.Count ? race.def.sequencePhys[me.nextGate] : -2;
                gateMarkers.Highlight(next, race.def.kind != EventKind.Circuit);
            }
        }

        void UpdateCountdown()
        {
            if (race.phase != RacePhase.Countdown) return;
            int c = Mathf.CeilToInt(race.countdown - 0.6f);
            if (c != lastCount && c >= 1 && c <= 3)
            {
                lastCount = c;
                sfx.CountBeep(false);
                foreach (var h in huds) h.Message(c.ToString(), "", 0.9f);
            }
        }

        void ProcessEvents()
        {
            foreach (var e in race.events)
            {
                Racer r = e.ship >= 0 ? race.racers[e.ship] : null;
                int hi = r != null ? humans.IndexOf(r) : -1;
                IslandHud hud = hi >= 0 ? huds[hi] : null;
                ChaseCam rig = hi >= 0 ? rigs[hi] : null;
                switch (e.type)
                {
                    case Ev.Go:
                        sfx.CountBeep(true);
                        foreach (var h in huds) h.Message("JÁ!", race.def.economy ? "Chegue à extração. Ser o mais rápido é bônus." : race.def.name, 1.4f);
                        break;
                    case Ev.Impact:
                        if (e.value > 14f) fx.Impact(e.pos + Vector3.up * 1.5f, e.value * 0.4f);
                        if (e.value > 20f) sfx.At(e.pos, "impact", Mathf.Clamp01(e.value / 60f) * 0.9f + 0.1f);
                        if (hud != null)
                        {
                            hud.Hit(e.value * 0.4f);
                            rig.Kick(Mathf.Min(1f, e.value / 40f));
                            if (e.value > 45f) rig.Shake(0.35f);
                            Rumble(hi, Mathf.Clamp01(e.value / 60f), 0.15f);
                        }
                        break;
                    case Ev.ShipBump:
                        sfx.At(e.pos, "impact", 0.6f);
                        fx.Impact(e.pos + Vector3.up * 1.5f, e.value * 0.3f);
                        if (hud != null) { hud.Hit(e.value * 0.3f); rig.Shake(0.3f); Rumble(hi, 0.5f, 0.15f); }
                        int ho = e.other >= 0 ? humans.IndexOf(race.racers[e.other]) : -1;
                        if (ho >= 0) { huds[ho].Hit(e.value * 0.3f); rigs[ho].Shake(0.3f); }
                        break;
                    case Ev.Destroyed:
                        fx.Explode(e.pos + Vector3.up * 1.5f);
                        sfx.At(e.pos, "explosion", 1f);
                        foreach (var h in huds)
                            h.Feed(UIKit.Colorize($"{r.pilot.name} DESTRUÍDO", UIKit.Danger) + (race.def.economy ? $" · {e.value:0} peça(s) → porquinho" : ""));
                        if (hud != null)
                        {
                            hud.Message(UIKit.Colorize(race.def.economy ? "EXTRACTION FAILED" : "DESTRUÍDO", UIKit.Danger), $"Nave destruída: {e.text}", 4f);
                            rig.SetMode(ChaseCam.Mode.Wreck);
                            rig.Shake(1.2f);
                            slowmoT = 1.2f;
                            Rumble(hi, 1f, 0.6f);
                        }
                        break;
                    case Ev.PoolAdd:
                        foreach (var h in huds) h.Feed($"  + {e.text} (≈{UIKit.Cr(Mathf.RoundToInt(e.value))})");
                        break;
                    case Ev.Finished:
                        if (hud != null)
                        {
                            string big = race.def.economy ? UIKit.Colorize("EXTRACTED", UIKit.Good) : UIKit.Colorize("CHEGADA!", UIKit.Good);
                            hud.Message(big, $"{r.place}º lugar · {UIKit.Time(e.value)}", 4f);
                            rig.SetMode(ChaseCam.Mode.Finish);
                            slowmoT = 1f;
                            sfx.Chime();
                        }
                        else foreach (var h in huds) h.Feed(UIKit.Colorize($"{r.pilot.name} {(race.def.economy ? "extraiu" : "chegou")} em {r.place}º", UIKit.Good));
                        break;
                    case Ev.Gate:
                        if (hud != null)
                        {
                            int idx = Mathf.RoundToInt(e.value);
                            string zone = race.def.kind == EventKind.Expedition && idx < world.data.sections.Length ? world.data.sections[idx].title : "";
                            hud.Sub($"PORTÃO {idx}/{race.def.gates.Length}  ·  {UIKit.Time(race.raceTime)}  ·  {r.place}º" + (zone != "" ? $"\n{zone}" : ""), 2.2f);
                            sfx.Chime();
                        }
                        break;
                    case Ev.Lap:
                        if (hud != null)
                        {
                            int lap = Mathf.RoundToInt(e.value);
                            hud.Message($"VOLTA {lap}", lap == race.def.laps ? "ÚLTIMA VOLTA!" : UIKit.Time(race.raceTime), 1.6f);
                            sfx.Chime();
                        }
                        break;
                    case Ev.Fall:
                        if (hud != null) { hud.Message(UIKit.Colorize("CAIU!", UIKit.Danger), $"{e.text} · de volta ao caminho…", 2f); rig.Shake(1f); Rumble(hi, 1f, 0.4f); }
                        else foreach (var h in huds) h.Feed($"{r.pilot.name}: {e.text.ToLowerInvariant()}");
                        break;
                    case Ev.Landed:
                        if (e.value > 10f) fx.Land(e.pos);
                        if (rig != null)
                        {
                            rig.Kick(Mathf.Clamp(e.value / 30f, 0.2f, 1f));
                            rig.Shake(Mathf.Clamp(e.value / 35f, 0.1f, 0.8f));
                            if (e.value > 14f) Rumble(hi, Mathf.Clamp01(e.value / 40f), 0.12f);
                        }
                        break;
                    case Ev.Boost:
                        if (rig != null) rig.Kick(Mathf.Clamp(e.value / 12f, 0.3f, 1f));
                        break;
                    case Ev.NitroGain:
                        if (hud != null) hud.NitroGain(e.value, e.text);
                        break;
                    case Ev.Pad:
                        if (hud != null) hud.Sub("PLACA DE ACELERAÇÃO", 1f, new Color(0.5f, 0.96f, 1f));
                        break;
                    case Ev.RepairStart:
                        if (hud != null) hud.Sub("A REPARAR… (um impacto interrompe)", 2f, UIKit.Good);
                        break;
                    case Ev.RepairDone:
                        if (hud != null) hud.Sub("REPARO CONCLUÍDO", 1.5f, UIKit.Good);
                        break;
                    case Ev.RepairInterrupted:
                        if (hud != null) hud.Sub("REPARO INTERROMPIDO", 1.5f, UIKit.Danger);
                        break;
                    case Ev.FuelUsed:
                        if (hud != null) hud.Sub("+30 COMBUSTÍVEL", 1.5f, new Color(1f, 0.8f, 0.3f));
                        break;
                    case Ev.Refuel:
                        if (hud != null) hud.Sub("POSTO DE ABASTECIMENTO  +35 COMBUSTÍVEL", 2f, new Color(1f, 0.8f, 0.3f));
                        break;
                    case Ev.Stranded:
                        if (hud != null) { hud.Message(UIKit.Colorize(r.state == PilotState.Abandoned ? "ABANDONED" : "STRANDED", UIKit.Warn), e.text, 4f); rig.SetMode(ChaseCam.Mode.Orbit); }
                        break;
                    case Ev.LowFuel:
                        if (hud != null) hud.Sub("COMBUSTÍVEL BAIXO", 2f, UIKit.Danger);
                        break;
                    case Ev.Critical:
                        if (hud != null) hud.Sub("INTEGRIDADE CRÍTICA", 2f, UIKit.Danger);
                        break;
                    case Ev.Respawned:
                        if (rig != null) { rig.Snap(); hud.Sub("NAVE RECUPERADA", 1.5f); }
                        break;
                }
            }
            race.events.Clear();
        }

        void Rumble(int humanIndex, float strength, float dur)
        {
            if (humanIndex < 0 || humanIndex >= humans.Count) return;
            var all = UnityEngine.InputSystem.Gamepad.all;
            UnityEngine.InputSystem.Gamepad pad = null;
            int scheme = humans[humanIndex].input.scheme;
            if (scheme == 0) pad = UnityEngine.InputSystem.Gamepad.current;
            else if (scheme == 1 && all.Count >= 2) pad = all[0];
            else if (scheme == 2) pad = all.Count >= 2 ? all[1] : (all.Count == 1 ? all[0] : null);
            if (pad == null)
            {
#if UNITY_ANDROID || UNITY_IOS
                if (strength > 0.4f) Handheld.Vibrate();
#endif
                return;
            }
            pad.SetMotorSpeeds(strength * 0.6f, strength);
            StartCoroutine(StopRumble(pad, dur));
        }

        IEnumerator StopRumble(UnityEngine.InputSystem.Gamepad pad, float dur)
        {
            yield return new WaitForSecondsRealtime(dur);
            if (pad != null) pad.SetMotorSpeeds(0f, 0f);
        }

        void UpdatePost(float dt)
        {
            if (race.def.kind == EventKind.Explore) return;
            bool allDone = true;
            for (int i = 0; i < humans.Count; i++)
            {
                var h = humans[i];
                if (h.Done) humanDoneT[i] += dt; else allDone = false;
            }
            if (!allDone) return;
            float minDone = float.MaxValue;
            foreach (var t in humanDoneT) minDone = Mathf.Min(minDone, t);
            if (state == State.Racing) state = State.Post;
            if (minDone > 4.5f && !settling && race.phase != RacePhase.Done)
            {
                settling = true;
                Debug.Log($"[flow] humans done, settling the rest of the field (race time {race.raceTime:0})");
                foreach (var h in huds) h.Sub("A validar os resultados… a aguardar o fim da prova", 30f, UIKit.Dim);
            }
            if (race.phase == RacePhase.Done && minDone > 4.5f && result == null)
            {
                result = RaceResult.Settle(race);
                Debug.Log($"[flow] settled: pool {result.pool.Count} items, {result.poolValue} CR est.");
                var p1 = humans.Find(x => x.pilot.persistent);
                if (p1 != null)
                {
                    result.ApplyTo(SaveSystem.Current, p1);
                    SaveSystem.Save();
                }
                Time.timeScale = 1f;
                ShowResults();
            }
        }

        void Pause()
        {
            state = State.Paused;
            Time.timeScale = 0f;
            ShowPause();
        }

        public void Resume()
        {
            HideAllScreens();
            Time.timeScale = 1f;
            state = race != null && race.def.kind != EventKind.Explore && humans.TrueForAll(h => h.Done) ? State.Post : State.Racing;
            hudLayer.gameObject.SetActive(true);
        }

        public void QuitToMenu()
        {
            Time.timeScale = 1f;
            if (mpRace) { mpRace = false; net?.Leave(); }
            ClearRace();
            if (menuRig)
            {
                menuRig.gameObject.SetActive(true);
                sfx.SetListener(menuRig.transform);
                world.viewers.Clear();
                world.viewers.Add(menuRig.transform);
                world.physicsFoci.Clear();
                world.physicsFoci.Add(() => showCraft.position);
            }
            if (showcase) showcase.gameObject.SetActive(true);
            sfx.PlayMusic(false);
            ShowMenu();
        }

        /// <summary>Same event again (Wi-Fi: only the host restarts, for everyone).</summary>
        public void Restart()
        {
            Time.timeScale = 1f;
            if (mpRace)
            {
                if (net != null && net.isHost) net.HostStart(currentEvent.id, Random.Range(1, 1 << 30));
                return;
            }
            StartEvent(currentEvent.kind == EventKind.Expedition ? EventDef.Expedition(world.data) : EventById(currentEvent.id), twoPlayers);
        }

        /// <summary>Explore: jump to the road nearest to a point of the map.</summary>
        public void TravelTo(Vector2 xz)
        {
            if (race == null || race.def.kind != EventKind.Explore) return;
            if (!world.NearestSpawn(new Vector3(xz.x, 0f, xz.y), true, out var sp)) return;
            var me = humans[0];
            world.EnsureCollidersAt(sp.pos, 400f);
            me.craft.Place(sp.pos, sp.dir, 0f);
            me.craft.running = true;
            me.craft.controlsBlocked = false;
            me.prevPos = me.craft.position;
            me.prevYaw = me.craft.yaw;
            me.state = PilotState.Racing;
            rigs[0].Snap();
            atmo.Tick(me.craft.position, false, 0f, true);
        }

        // ------------------------------------------------------------------ automated test (screenshots + a full expedition)

        void Shot(string name)
        {
            if (string.IsNullOrEmpty(shotDir)) return;
            System.IO.Directory.CreateDirectory(shotDir);
            ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(shotDir, name + ".png"));
            Debug.Log("[autotest] screenshot " + name);
        }

        /// <summary>Teleports the field to a gate of the event (the bots keep their order around the player).</summary>
        void WarpToGate(int gate)
        {
            var def = race.def;
            gate = Mathf.Clamp(gate, 0, def.sequence.Count - 1);
            var g = gate == 0 ? def.start : def.sequence[gate - 1];
            var me = humans[0];
            int k = 0;
            foreach (var r in race.racers)
            {
                if (r.state != PilotState.Racing) continue;
                var off = g.Dir * (-30f - 18f * (k / 3)) + new Vector3(g.Dir.z, 0f, -g.Dir.x) * ((k % 3) - 1) * 14f;
                if (r == me) off = Vector3.zero;
                else k++;
                world.EnsureCollidersAt(g.Pos + off, 300f);
                r.craft.Place(race.GroundAt(g.Pos + off), g.Dir, 60f);
                r.nextGate = gate;
                r.prevPos = r.craft.position;
                r.prevYaw = r.craft.yaw;
                r.ghost = false;
                if (r.bot != null) r.bot.Resync();
            }
            foreach (var rig in rigs) rig.Snap();
        }

        static readonly FrameTiming[] ft = new FrameTiming[1];
        static string FrameTimes()
        {
            FrameTimingManager.CaptureFrameTimings();
            if (FrameTimingManager.GetLatestTimings(1, ft) < 1) return "(sem timings)";
            var f = ft[0];
            return $"cpu main {f.cpuMainThreadFrameTime:0.0}ms render {f.cpuRenderThreadFrameTime:0.0}ms gpu {f.gpuFrameTime:0.0}ms";
        }

        void UpdateAutotest(float dt)
        {
            testT += dt;
            if (state == State.Results)
            {
                if (testStage < 100) { testStage = 100; testT = 0f; }
                if (testT > 1.5f && testStage == 100) { Shot("90_results"); testStage = 101; }
                if (testT > 3f && testStage == 101)
                {
                    Debug.Log("[autotest] done");
                    Application.Quit();
                }
                return;
            }
            if (race.def.kind == EventKind.Explore)
            {
                stageClock += dt;
                if (stageClock > 3f)
                {
                    Shot($"{10 + testStage * 5:00}_explore{testStage}");
                    testStage++;
                    stageClock = 0f;
                    var spots = new[] { new Vector2(4500f, 4500f), new Vector2(-7600f, 1300f), new Vector2(0f, -9000f), new Vector2(9000f, -6000f), new Vector2(-3700f, 7000f) };
                    if (testStage <= spots.Length) TravelTo(spots[testStage - 1]);
                    else { Debug.Log("[autotest] done"); Application.Quit(); }
                }
                return;
            }
            if (race.phase == RacePhase.Countdown) return;
            var me = humans[0];
            int n = race.def.sequence.Count;
            var stops = race.def.kind == EventKind.Expedition ? new[] { 0, 4, 9, 13, 16, 20, 24, 28, n - 1 } : new[] { 0, n / 2, n - 1 };
            if (testStage < stops.Length)
            {
                if (me.state != PilotState.Racing) { testStage = stops.Length; return; }
                if (!stageWarped)
                {
                    if (stops[testStage] > 0) WarpToGate(stops[testStage]);
                    stageWarped = true;
                    stageClock = 0f;
                }
                stageClock += dt;
                if (stageClock > 0.5f) { stageFrames++; stageDt += dt; stageMaxDt = Mathf.Max(stageMaxDt, dt); }
                if (stageClock > (testStage == stops.Length - 1 ? 0.8f : 2.2f))
                {
                    Shot($"{10 + testStage * 5:00}_gate{stops[testStage]}");
                    Debug.Log($"[autotest] gate {stops[testStage]}: pos {me.craft.position} v={me.SpeedKmh:0} integrity={me.integrity:0} fuel={me.fuel:0} place={me.place} ghosts={race.racers.FindAll(x => x.ghost).Count} fps avg={stageFrames / Mathf.Max(stageDt, 1e-3f):0} worst={stageMaxDt * 1000f:0}ms {FrameTimes()} sim={stepMs:0.0}ms/{stepsAvg:0.0} steps present={presentMs:0.0}ms atmo+audio={atmoMs:0.0}ms dt={Time.unscaledDeltaTime * 1000f:0}ms draws={world.drawer.drawCalls} colCells={world.activeColliderCells}");
                    testStage++;
                    stageWarped = false;
                    stageFrames = 0; stageDt = 0f; stageMaxDt = 0f;
                }
                return;
            }
            if (me.state == PilotState.Finished && testStage == stops.Length)
            {
                stageClock += dt;
                if (stageClock > 1.2f) { Shot("85_extracted"); testStage++; }
            }
        }
    }
}
