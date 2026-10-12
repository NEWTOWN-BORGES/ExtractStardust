using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace Stardust.EditorTools
{
    /// <summary>
    /// Headless race simulation on the real island (batch: -executeMethod Stardust.EditorTools.IslandSimTest.Run):
    /// 16 bots with full physics run an event; reports finish times, crashes, falls, respawns, destructions,
    /// fuel and the item conservation of the piggy bank. Args: -simevent ID, -simtime SECONDS, -simghost (cheap mode).
    /// </summary>
    public static class IslandSimTest
    {
        [MenuItem("Stardust/Island Simulation Test")]
        public static void Run()
        {
            string evId = "expedicao";
            float maxTime = 1800f;
            bool ghosts = false;
            var args = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "-simevent" && i + 1 < args.Length) evId = args[i + 1];
                if (args[i] == "-simtime" && i + 1 < args.Length) float.TryParse(args[i + 1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out maxTime);
                if (args[i] == "-simghost") ghosts = true;
            }
            var sb = new StringBuilder();
            var sw = System.Diagnostics.Stopwatch.StartNew();
            Physics.simulationMode = SimulationMode.Script;
            Physics.autoSyncTransforms = true;
            var root = new GameObject("SimRoot");
            int code = 0;
            try
            {
                var world = IslandWorld.Create(root.transform, 0);
                var it = world.Build(null);
                Drain(it);
                sb.AppendLine($"world built in {sw.ElapsedMilliseconds} ms");
                EventDef def = evId == "expedicao" ? EventDef.Expedition(world.data) : null;
                if (def == null) foreach (var e in world.data.events) if (e.id == evId) def = EventDef.FromWorld(e);
                if (def == null) def = EventDef.Expedition(world.data);
                var rng = new System.Random(4242);
                var pilots = new List<Pilot>();
                int n = Mathf.Max(def.botCount + 1, 4);
                for (int i = 0; i < n; i++)
                {
                    var style = (BotStyle)(i % 3);
                    var p = new Pilot { name = "Bot" + i, persona = BotPersona.Make(style, rng) };
                    for (int s = 0; s < 6; s++) p.equip[s] = Catalog.Create((Slot)s, Catalog.RollRarity(rng), rng, "sim", p.name);
                    p.insuredId = p.equip[0].id;
                    pilots.Add(p);
                }
                var race = new IslandRace(world, def, pilots, 777) { noGhosts = !ghosts };
                // sanity: does every bot route cross every gate (same test as the race)?
                foreach (var r in race.racers)
                {
                    var rt = r.bot.route;
                    int g = 0;
                    for (int i = 0; i + 1 < rt.Length && g < def.sequence.Count; i++)
                        if (IslandRace.CrossedGate(def.sequence[g], rt[i] + Vector3.up * 1.5f, rt[i + 1] + Vector3.up * 1.5f)) g++;
                    if (g < def.sequence.Count)
                    {
                        var gp = def.sequence[g];
                        float best = float.MaxValue;
                        foreach (var q in rt) best = Mathf.Min(best, Vector3.Distance(q, gp.Pos));
                        sb.AppendLine($"  ROUTE {r.pilot.name}: crosses only {g}/{def.sequence.Count} gates; gate {g} at {gp.Pos} dir {gp.Dir} w {gp.w}, nearest route point {best:0} m");
                    }
                }
                world.physicsFoci.Clear();
                foreach (var r in race.racers) { var rr = r; world.physicsFoci.Add(() => rr.craft.position); }
                var counts = new Dictionary<Ev, int>();
                var causes = new Dictionary<string, int>();
                var falls = new List<string>();
                var hits = new Dictionary<string, int>();
                var fallAt = new Dictionary<string, int>();
                float t = 0f;
                float logT = 0f;
                var traces = new Queue<string>[race.racers.Count];
                int fallDumps = 0;
                for (int i = 0; i < traces.Length; i++) traces[i] = new Queue<string>();
                int dumps = 0, frame = 0;
                while (race.phase != RacePhase.Done && t < maxTime)
                {
                    race.Step(IslandRace.Dt);
                    t += IslandRace.Dt;
                    frame++;
                    world.TickColliders(IslandRace.Dt);
                    if (frame % 6 == 0)
                        foreach (var r in race.racers)
                        {
                            var c = r.craft;
                            traces[r.index].Enqueue($"    t={t:0.00} p=({c.position.x:0.0},{c.position.y:0.0},{c.position.z:0.0}) v=({c.vel.x:0.0},{c.vel.y:0.0},{c.vel.z:0.0}) |v|={c.Speed:0} gnd={c.onGround} valid={c.groundValid} gp={c.groundPoint.y:0.0} steer={c.input.steer:0.00} brk={c.input.brake} nit={c.nitroActive} idx={r.bot?.index} lat={r.bot?.dbgLat:0.0} diff={r.bot?.dbgDiff:0.00} slow={r.bot?.dbgSlow} drift={r.bot?.dbgDrift} st={r.state}");
                            while (traces[r.index].Count > 30) traces[r.index].Dequeue();
                        }
                    foreach (var e in race.events)
                    {
                        if (e.type == Ev.Impact && e.value > 45f && dumps < 5 && e.pos.x > -6000f && e.pos.x < -1000f)
                        {
                            dumps++;
                            falls.Add($"  TRACE {race.racers[e.ship].pilot.name} before impact {e.value:0} at {e.pos}:");
                            foreach (var l in traces[e.ship]) falls.Add(l);
                        }
                        counts.TryGetValue(e.type, out int c); counts[e.type] = c + 1;
                        if (e.type == Ev.Destroyed) { causes.TryGetValue(e.text ?? "?", out int k); causes[e.text ?? "?"] = k + 1; }
                        if (e.type == Ev.Respawned && falls.Count < 20) falls.Add($"  respawn {race.racers[e.ship].pilot.name} t={t:0} -> {e.pos.x:0},{e.pos.y:0},{e.pos.z:0} gate {race.racers[e.ship].nextGate} idx {race.racers[e.ship].bot.index}");
                        if (e.type == Ev.Fall) { string fk = $"{Mathf.Round(e.pos.x / 100f) * 100f:0},{Mathf.Round(e.pos.z / 100f) * 100f:0} gate {race.racers[e.ship].nextGate}"; fallAt.TryGetValue(fk, out int fc); fallAt[fk] = fc + 1; }
                        if (e.type == Ev.Fall && fallDumps < 2)
                        {
                            fallDumps++;
                            falls.Add($"  TRACE {race.racers[e.ship].pilot.name} before fall at {e.pos}:");
                            foreach (var l in traces[e.ship]) falls.Add(l);
                        }
                        if (e.type == Ev.Fall && falls.Count < 80) falls.Add($"  fall {race.racers[e.ship].pilot.name} t={t:0} at {e.pos.x:0},{e.pos.y:0},{e.pos.z:0} gate {race.racers[e.ship].nextGate}: {e.text}");
                        if (e.type == Ev.Impact && e.value > 40f)
                        {
                            string key = $"{e.text} @ {Mathf.Round(e.pos.x / 50f) * 50f:0},{Mathf.Round(e.pos.z / 50f) * 50f:0}";
                            hits.TryGetValue(key, out int hk); hits[key] = hk + 1;
                        }
                    }
                    race.events.Clear();
                    if (t - logT >= 60f)
                    {
                        logT = t;
                        var lead = race.Ordered[0];
                        sb.AppendLine($"t={t:0}s leader {lead.pilot.name} gate {lead.nextGate}/{race.GateCount} v={lead.SpeedKmh:0} km/h · racing {race.racers.FindAll(x => x.state == PilotState.Racing).Count} · real {sw.Elapsed.TotalSeconds:0}s");
                    }
                }
                sb.AppendLine($"simulated {t:0}s in {sw.Elapsed.TotalSeconds:0}s real · phase {race.phase}");
                foreach (var kv in counts) sb.AppendLine($"  {kv.Key}: {kv.Value}");
                foreach (var kv in causes) sb.AppendLine($"  destroyed by {kv.Key}: {kv.Value}");
                var hl = new List<KeyValuePair<string, int>>(hits);
                hl.Sort((a, b) => b.Value.CompareTo(a.Value));
                for (int i = 0; i < Mathf.Min(40, hl.Count); i++) sb.AppendLine($"  impacts>40 x{hl[i].Value}: {hl[i].Key}");
                foreach (var kv in fallAt) sb.AppendLine($"  falls x{kv.Value} @ {kv.Key}");
                foreach (var l in falls) sb.AppendLine(l);
                foreach (var r in race.Ordered)
                    sb.AppendLine($"{r.place,2}. {r.pilot.name} {r.pilot.persona.style} skill {r.pilot.persona.skill:0.00} · {r.state} {(r.finishTime > 0 ? UIKit.Time(r.finishTime) : "")} gate {r.nextGate}/{race.GateCount} integrity {r.integrity:0} fuel {r.fuel:0} km {r.distance / 1000f:0.0} drifts {r.drifts}");
                var res = RaceResult.Settle(race);
                var seen = new HashSet<string>();
                bool ok = true;
                foreach (var p in res.pilots) foreach (var item in p.loot) ok &= seen.Add(item.id);
                foreach (var item in res.residual) ok &= seen.Add(item.id);
                ok &= seen.Count == res.pool.Count;
                sb.AppendLine($"pool {res.pool.Count} items ≈{res.poolValue} CR · item conservation {(ok ? "OK" : "FAILED")}");
            }
            catch (System.Exception e)
            {
                sb.AppendLine("EXCEPTION " + e);
                code = 1;
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
            Directory.CreateDirectory("Logs");
            File.WriteAllText($"Logs/islandsim_{evId}.txt", sb.ToString());
            Debug.Log("[IslandSim]\n" + sb);
            if (Application.isBatchMode) EditorApplication.Exit(code);
        }

        static void Drain(IEnumerator it)
        {
            var stack = new Stack<IEnumerator>();
            stack.Push(it);
            while (stack.Count > 0)
            {
                var top = stack.Peek();
                if (!top.MoveNext()) { stack.Pop(); continue; }
                if (top.Current is IEnumerator nested) stack.Push(nested);
            }
        }
    }
}
