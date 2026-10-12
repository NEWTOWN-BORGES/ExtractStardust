using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace Stardust
{
    /// <summary>
    /// Visual/physics smoke test of the island (command line: -islandtest [-shotdir DIR] [-quality N]):
    /// builds the world, drops an autopilot ship at several gates of the expedition route, follows it with the
    /// chase camera and saves screenshots + a log line per stop (fps, speed, ground, collider cells).
    /// </summary>
    public class IslandTest : MonoBehaviour
    {
        string shotDir;
        int quality = 2;
        int maxStops = 999;
        string only;
        string atRoute;
        IslandWorld world;
        Atmosphere atmo;
        Hovercraft craft;
        ShipVisual vis;
        BotPilot pilot;
        ChaseCam rig;
        Vector3 prevPos, curPos;
        float acc;
        const float Dt = 1f / 60f;
        readonly List<string> log = new List<string>();

        public static bool Requested
        {
            get
            {
                foreach (var a in System.Environment.GetCommandLineArgs()) if (a == "-islandtest") return true;
                return false;
            }
        }

        void Awake()
        {
            var args = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "-shotdir" && i + 1 < args.Length) shotDir = args[i + 1];
                if (args[i] == "-quality" && i + 1 < args.Length && int.TryParse(args[i + 1], out int q)) quality = Mathf.Clamp(q, 0, 2);
                if (args[i] == "-sddebug" && i + 1 < args.Length && float.TryParse(args[i + 1], out float dbg)) Shader.SetGlobalFloat("_SD_Debug", dbg);
                if (args[i] == "-stops" && i + 1 < args.Length && int.TryParse(args[i + 1], out int ns)) maxStops = ns;
                if (args[i] == "-only" && i + 1 < args.Length) only = args[i + 1];
                if (args[i] == "-atroute" && i + 1 < args.Length) atRoute = args[i + 1];
            }
            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 0;
            Physics.simulationMode = SimulationMode.Script;
            Physics.autoSyncTransforms = true;
        }

        IEnumerator Start()
        {
            float t0 = Time.realtimeSinceStartup;
            atmo = Atmosphere.Create(transform, quality);
            world = IslandWorld.Create(transform, quality);
            yield return world.Build((p, s) => Debug.Log($"[islandtest] loading {p:0.00} {s}"));
            Debug.Log($"[islandtest] world built in {Time.realtimeSinceStartup - t0:0.0}s");
            atmo.RefreshReflections();

            if (!string.IsNullOrEmpty(atRoute)) { yield return DriveRoute(); yield break; }
            // route: variant 0 of every section
            var route = new List<Vector3>();
            foreach (var sec in world.data.sections)
            {
                var pts = sec.variants[0].Points;
                for (int i = route.Count == 0 ? 0 : 1; i < pts.Length; i++) route.Add(pts[i]);
            }
            craft = new Hovercraft();
            pilot = new BotPilot(1) { neverErr = true, skill = 1f, self = craft };
            pilot.SetRoute(route.ToArray());
            vis = ShipVisual.Create(transform, "vespa", new Color(0.15f, 0.8f, 1f), quality, true);
            rig = ChaseCam.Create(transform, "Cam", new Rect(0, 0, 1, 1), quality <= 0 ? 9000f : 15000f, true);
            world.viewers.Add(rig.transform);
            world.physicsFoci.Add(() => craft.position);

            var stops = new List<(string name, Vector3 p, Vector3 d)>();
            stops.Add(("00_start", world.data.start.Pos, world.data.start.Dir));
            int[] gates = { 2, 4, 7, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28 };
            foreach (int g in gates)
                if (g < world.data.checkpoints.Length) stops.Add(($"{g + 1:00}_gate_{Safe(world.data.checkpoints[g].name)}", world.data.checkpoints[g].Pos, world.data.checkpoints[g].Dir));
            foreach (var ev in world.data.events) stops.Add(($"ev_{ev.id}", ev.start.Pos, ev.start.Dir));

            if (!string.IsNullOrEmpty(only)) stops.RemoveAll(s => !s.name.StartsWith(only));
            if (stops.Count > maxStops) stops.RemoveRange(maxStops, stops.Count - maxStops);
            foreach (var s in stops)
            {
                world.EnsureCollidersAt(s.p);
                craft.Place(s.p, s.d, 40f);
                craft.running = true;
                pilot.Resync();
                prevPos = curPos = craft.position;
                rig.SetTarget(craft, vis);
                atmo.Tick(craft.position, world.InCave(craft.position), 0f, true);
                float t = 0f, minFps = 999f;
                int frames = 0;
                float fpsT = 0f;
                while (t < 4.5f)
                {
                    float dt = Time.deltaTime;
                    t += dt;
                    acc += Mathf.Min(dt, 0.1f);
                    while (acc >= Dt)
                    {
                        prevPos = craft.position;
                        craft.input = pilot.Drive(craft, Dt);
                        craft.Step(Dt);
                        if (world.PadAt(craft.position) >= 0) craft.PadBoost();
                        curPos = craft.position;
                        acc -= Dt;
                    }
                    var ip = Vector3.Lerp(prevPos, curPos, acc / Dt);
                    vis.Pose(ip, craft.Rotation, craft, dt);
                    rig.Tick(ip, dt);
                    atmo.Tick(ip, world.InCave(ip), dt);
                    if (t > 1.5f) { frames++; fpsT += dt; minFps = Mathf.Min(minFps, 1f / Mathf.Max(dt, 1e-4f)); }
                    yield return null;
                }
                Shot(s.name);
                string line = $"[islandtest] {s.name}: pos {craft.position.x:0},{craft.position.y:0},{craft.position.z:0} v={craft.Speed * 3.6f:0} km/h ground={craft.onGround} water={craft.onWater} " +
                              $"fps avg {(frames / Mathf.Max(fpsT, 1e-3f)):0} min {minFps:0} draws {world.drawer.drawCalls} inst {world.drawer.instancesDrawn} colCells {world.activeColliderCells}";
                Debug.Log(line);
                log.Add(line);
                yield return null;
            }
            if (!string.IsNullOrEmpty(shotDir)) File.WriteAllLines(Path.Combine(shotDir, "islandtest.txt"), log);
            Debug.Log("[islandtest] done");
            yield return new WaitForSeconds(0.5f);
            Application.Quit();
        }

        /// <summary>-atroute S,V,F[,SECONDS]: autopilot on variant V of section S from fraction F, a shot every second.</summary>
        IEnumerator DriveRoute()
        {
            var a = atRoute.Split(',');
            int sec = int.Parse(a[0]), vi = int.Parse(a[1]);
            float frac = float.Parse(a[2], System.Globalization.CultureInfo.InvariantCulture);
            float secs = a.Length > 3 ? float.Parse(a[3], System.Globalization.CultureInfo.InvariantCulture) : 10f;
            var variants = new int[world.data.sections.Length];
            variants[sec] = vi;
            var route = EventDef.ExpeditionRoute(world.data, variants, out var jumps, out var hws);
            var vpts = world.data.sections[sec].variants[vi].Points;
            int k = Mathf.Clamp((int)(frac * (vpts.Length - 1)), 0, vpts.Length - 2);
            craft = new Hovercraft();
            pilot = new BotPilot(1) { neverErr = true, skill = 1f, self = craft };
            pilot.SetRoute(route, jumps, hws);
            vis = ShipVisual.Create(transform, "vespa", new Color(0.15f, 0.8f, 1f), quality, true);
            rig = ChaseCam.Create(transform, "Cam", new Rect(0, 0, 1, 1), quality <= 0 ? 9000f : 15000f, true);
            world.viewers.Add(rig.transform);
            world.physicsFoci.Add(() => craft.position);
            world.EnsureCollidersAt(vpts[k], 500f);
            craft.Place(vpts[k], vpts[k + 1] - vpts[k], 90f);
            craft.running = true;
            pilot.Resync();
            prevPos = curPos = craft.position;
            rig.SetTarget(craft, vis);
            atmo.Tick(craft.position, world.InCave(craft.position), 0f, true);
            float t = 0f, nextShot = 1f, nextLog = 0f;
            int n = 0;
            while (t < secs)
            {
                float dt = Time.deltaTime;
                t += dt;
                acc += Mathf.Min(dt, 0.1f);
                while (acc >= Dt)
                {
                    prevPos = craft.position;
                    craft.input = pilot.Drive(craft, Dt);
                    craft.Step(Dt);
                    if (world.PadAt(craft.position) >= 0) craft.PadBoost();
                    curPos = craft.position;
                    acc -= Dt;
                    if (craft.lastImpact > 20f) log.Add($"  IMPACT {craft.lastImpact:0} with {(craft.lastImpactCollider ? craft.lastImpactCollider.name : "?")} at {craft.position}");
                }
                var ip = Vector3.Lerp(prevPos, curPos, acc / Dt);
                vis.Pose(ip, craft.Rotation, craft, dt);
                rig.Tick(ip, dt);
                atmo.Tick(ip, world.InCave(ip), dt);
                if (t >= nextLog)
                {
                    nextLog += 0.25f;
                    log.Add($"t={t:0.00} p={craft.position} v={craft.Speed * 3.6f:0} gnd={craft.onGround} steer={craft.input.steer:0.00} brk={craft.input.brake} nit={craft.nitroActive} idx={pilot.index}");
                }
                if (t >= nextShot) { nextShot += 1f; Shot($"route_{n++:00}"); }
                yield return null;
            }
            if (!string.IsNullOrEmpty(shotDir)) File.WriteAllLines(Path.Combine(shotDir, "islandtest.txt"), log);
            Debug.Log("[islandtest] done");
            yield return new WaitForSeconds(0.5f);
            Application.Quit();
        }

        static string Safe(string s)
        {
            var sb = new System.Text.StringBuilder();
            foreach (char c in s.ToLowerInvariant()) sb.Append(char.IsLetterOrDigit(c) && c < 128 ? c : '_');
            return sb.ToString();
        }

        void Shot(string name)
        {
            if (string.IsNullOrEmpty(shotDir)) return;
            Directory.CreateDirectory(shotDir);
            ScreenCapture.CaptureScreenshot(Path.Combine(shotDir, name + ".png"));
        }
    }
}
