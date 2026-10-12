using System.Collections.Generic;
using UnityEngine;

namespace Stardust
{
    public enum RacePhase { Countdown, Racing, Closing, Done }

    public enum Ev
    {
        Go, Impact, ShipBump, Destroyed, Finished, Gate, Lap, Fall, Landed, Boost, NitroGain, RepairStart, RepairDone,
        RepairInterrupted, FuelUsed, Refuel, PoolAdd, Stranded, LowFuel, Critical, Respawned, Pad
    }

    public struct RaceEvent
    {
        public Ev type;
        public int ship, other;
        public float value;
        public Vector3 pos;
        public string text;
    }

    /// <summary>
    /// An island race (port of race.gd + the EXTRACT STARDUST rules): fixed-step simulation of every racer, gates in
    /// order, integrity (walls, landings, other ships, falls), fuel, consumables, respawn on safe ground, the piggy
    /// bank of lost parts and the closing timer after the first extraction. Bots far from every human run in a cheap
    /// "ghost" mode along their route (no physics) and switch back to full physics when a human comes near.
    /// </summary>
    public class IslandRace
    {
        public const float Dt = 1f / 60f;
        public const int LossCount = 3;
        public const string LossPolicyText = "Destruída = perde até 3 peças NÃO seguradas (sorteadas) para o porquinho. A peça segurada volta à garagem.";

        public readonly IslandWorld world;
        public readonly EventDef def;
        public readonly List<Racer> racers = new List<Racer>();
        public readonly List<ItemInst> pool = new List<ItemInst>();
        public readonly List<RaceEvent> events = new List<RaceEvent>();
        public readonly List<Hovercraft> crafts = new List<Hovercraft>();
        public readonly System.Random rng;
        public readonly string matchId;
        public RacePhase phase = RacePhase.Countdown;
        public float countdown = 4.2f;
        public float raceTime;
        public float firstFinish = -1f;
        public int poolValue;
        public bool settling;
        public bool waitForGo;          // Wi-Fi: the countdown starts when every player has loaded
        public bool noGhosts;           // tests: every bot keeps full physics
        readonly List<Racer> order = new List<Racer>();
        readonly float[] gateLen;
        readonly Vector3[] gatePos;
        float switchClock;
        public const float GhostOn = 1500f, GhostOff = 1000f;

        public List<Racer> Ordered => order;
        public int GateCount => def.sequence.Count;

        public IslandRace(IslandWorld world, EventDef def, List<Pilot> pilots, int seed)
        {
            this.world = world;
            this.def = def;
            rng = new System.Random(seed);
            matchId = Catalog.NewId();
            // distances between consecutive gates (ordering inside a section)
            int n = def.sequence.Count;
            gatePos = new Vector3[n + 1];
            gatePos[0] = def.start.Pos;
            for (int i = 0; i < n; i++) gatePos[i + 1] = def.sequence[i].Pos;
            gateLen = new float[n + 1];
            for (int i = 0; i < n; i++) gateLen[i] = Vector3.Distance(gatePos[i], gatePos[i + 1]);
            gateLen[n] = 1f;

            var grid = GridSlots(pilots.Count, out var gridDir);
            for (int i = 0; i < pilots.Count; i++)
            {
                var p = pilots[i];
                var r = new Racer { index = i, pilot = p, st = ShipStats.From(p.equip) };
                ApplyStats(r);
                r.fuel = r.st.fuelCap;
                r.craft.nitro = 50f;
                if (!p.human && !p.remote)
                {
                    var per = p.persona ?? BotPersona.Make(BotStyle.Technical, rng);
                    r.bot = new BotPilot(seed + i * 31)
                    {
                        skill = per.skill, aggression = per.aggression, lineOffset = per.lineOffset, self = r.craft, others = crafts,
                    };
                    var route = BotRoute(per, out var jumps, out var hws);
                    r.bot.SetRoute(route, jumps, hws);
                    r.gateRouteIdx = GateIndices(route);
                    r.craft.topSpeedMul *= 0.93f + 0.07f * per.skill;
                }
                world.EnsureCollidersAt(grid[i], 250f);
                r.craft.Place(GroundAt(grid[i]), gridDir[i], 0f);
                r.craft.running = false;
                r.craft.controlsBlocked = true;
                r.prevPos = r.craft.position;
                r.prevYaw = r.craft.yaw;
                r.stuckP = r.craft.position;
                if (r.bot != null) r.bot.Resync();
                racers.Add(r);
                crafts.Add(r.craft);
            }
            UpdateOrder();
        }

        void ApplyStats(Racer r)
        {
            var s = r.st;
            var c = r.craft;
            c.topSpeedMul = s.topSpeed / ShipStats.Base.topSpeed;
            c.accelMul = s.accel / ShipStats.Base.accel;
            c.gripMul = s.grip / ShipStats.Base.grip;
            c.nitroMul = Mathf.Max(0.5f, (s.boostMult - 1f) / (ShipStats.Base.boostMult - 1f));
            c.nitroRegen = 2.2f * s.nitroRegen / ShipStats.Base.nitroRegen;
        }

        Vector3[] BotRoute(BotPersona per, out List<int> jumps, out List<float> hws)
        {
            if (def.kind == EventKind.Expedition) return EventDef.ExpeditionRoute(world.data, EventDef.ChooseVariants(world.data, per, rng), out jumps, out hws);
            var r = def.LapsRoute(out jumps);
            hws = new List<float>();
            for (int i = 0; i < r.Length; i++) hws.Add(def.halfW);
            return r;
        }

        /// <summary>Grid behind the start line (every route variant begins at the start point): rows of four.</summary>
        Vector3[] GridSlots(int count, out Vector3[] dirs)
        {
            var pos = new Vector3[count];
            dirs = new Vector3[count];
            var d = def.start.Dir;
            var side = new Vector3(d.z, 0f, -d.x);
            float hw = Mathf.Min(def.halfW - 10f, 21f);
            const int perRow = 4;
            for (int i = 0; i < count; i++)
            {
                int row = i / perRow, col = i % perRow;
                float back = 12f + row * 22f;
                float lat = Mathf.Lerp(-hw, hw, col / (float)(perRow - 1)) + (row % 2 == 1 ? 5f : -5f);
                pos[i] = def.start.Pos - d * back + side * lat;
                dirs[i] = d;
            }
            return pos;
        }
        static void SamplePath(Vector3[] path, float dist, out Vector3 p, out Vector3 dir)
        {
            float acc = 0f;
            for (int i = 0; i + 1 < path.Length; i++)
            {
                float seg = Vector3.Distance(path[i], path[i + 1]);
                if (acc + seg >= dist || i + 2 == path.Length)
                {
                    float t = seg > 0f ? Mathf.Clamp01((dist - acc) / seg) : 0f;
                    p = Vector3.Lerp(path[i], path[i + 1], t);
                    dir = path[i + 1] - path[i];
                    dir.y = 0f;
                    dir = dir.sqrMagnitude > 1e-4f ? dir.normalized : Vector3.forward;
                    return;
                }
                acc += seg;
            }
            p = path[0];
            dir = Vector3.forward;
        }

        /// <summary>Ground (or bridge/tunnel floor) under a point.</summary>
        public Vector3 GroundAt(Vector3 p)
        {
            if (Physics.Raycast(p + Vector3.up * 30f, Vector3.down, out var hit, 80f, IslandWorld.ProbeMask, QueryTriggerInteraction.Ignore))
                return hit.point;
            p.y = world.HeightAt(p.x, p.z);
            return p;
        }

        void Emit(Ev type, Racer r, float value = 0f, string text = null, int other = -1)
        {
            events.Add(new RaceEvent { type = type, ship = r != null ? r.index : -1, other = other, value = value, pos = r != null ? r.craft.position : Vector3.zero, text = text });
        }

        // ------------------------------------------------------------------ main step

        public void Step(float dt)
        {
            foreach (var r in racers) { r.prevPos = r.craft.position; r.prevYaw = r.craft.yaw; }
            if (phase == RacePhase.Countdown)
            {
                if (!waitForGo) countdown -= dt;
                foreach (var r in racers) if (!r.pilot.remote) r.craft.Step(dt);
                if (countdown <= 0f)
                {
                    phase = RacePhase.Racing;
                    raceTime = 0f;
                    foreach (var r in racers)
                    {
                        r.state = PilotState.Racing;
                        r.craft.running = true;
                        r.craft.controlsBlocked = false;
                    }
                    Emit(Ev.Go, null);
                }
                return;
            }
            raceTime += dt;
            foreach (var r in racers)
            {
                if (r.invulnT > 0f) r.invulnT -= dt;
                if (r.pilot.remote) continue;   // driven by the network
                switch (r.state)
                {
                    case PilotState.Racing:
                        if (r.ghost) GhostStep(r, dt); else DriveStep(r, dt);
                        break;
                    case PilotState.Respawning:
                        r.respawnT -= dt;
                        if (!r.ghost) r.craft.Step(dt);
                        if (r.respawnT <= 0f) Respawn(r);
                        break;
                    default:
                        // finished / out of the race: coast to a stop
                        r.craft.running = false;
                        r.craft.controlsBlocked = true;
                        if (!r.ghost) r.craft.Step(dt);
                        break;
                }
            }
            ShipCollisions();
            switchClock -= dt;
            if (switchClock <= 0f) { switchClock = 0.5f; UpdateGhosts(); }

            if (phase == RacePhase.Closing && raceTime - firstFinish > def.closeTime)
            {
                foreach (var r in racers)
                    if (r.Active) { r.state = PilotState.Abandoned; Emit(Ev.Stranded, r, 0f, "tempo esgotado"); }
            }
            bool anyActive = false;
            foreach (var r in racers) if (r.Active) { anyActive = true; break; }
            if (!anyActive && def.kind != EventKind.Explore) phase = RacePhase.Done;
            UpdateOrder();
        }

        // ------------------------------------------------------------------ physics racers

        void DriveStep(Racer r, float dt)
        {
            var c = r.craft;
            if (r.bot != null)
            {
                c.input = r.bot.Drive(c, dt);
                BotItems(r);
            }
            else if (r.input != null)
            {
                c.input = r.input.ship;
                if (r.input.useA) UseConsumable(r, 0);
                if (r.input.useB) UseConsumable(r, 1);
            }
            Repair(r, dt);
            Fuel(r, dt);
            bool wasPad = c.onPad;
            c.onPad = world.PadAt(c.position) >= 0;
            if (c.onPad && !wasPad) { c.PadBoost(); Emit(Ev.Pad, r); }
            var before = c.position;
            c.Step(dt);
            r.distance += Vector3.Distance(before, c.position);
            if (c.nitroActive) r.nitroUsedSeconds += dt;
            r.CountDrift();
            if (c.boostedThisStep) Emit(Ev.Boost, r, c.boostAmount);
            if (c.nitroGain > 0.5f) Emit(Ev.NitroGain, r, c.nitroGain, c.nitroReason);
            // damage: walls (only the component against the wall counts), hard landings
            r.scrape = Mathf.MoveTowards(r.scrape, 0f, dt * 4f);
            if (c.lastImpact > 6f)
            {
                r.scrape = Mathf.Max(r.scrape, Mathf.Clamp01(c.lastImpact / 30f));
                float dmg = Mathf.Max(0f, c.lastImpact - 28f) * 0.3f * r.st.armor;
                if (dmg > 0f) Damage(r, dmg, c.lastImpact > 45f ? "Colisão violenta" : "Batida na parede");
                Emit(Ev.Impact, r, c.lastImpact, c.lastImpactCollider != null ? c.lastImpactCollider.name : null);
            }
            if (c.lastLanding > 8f)
            {
                Emit(Ev.Landed, r, c.lastLanding);
                if (c.lastLanding > 42f) Damage(r, (c.lastLanding - 42f) * 0.4f * r.st.armor, "Pouso duro");
            }
            if (r.state != PilotState.Racing) return;
            Gates(r, before, c.position);
            if (r.state != PilotState.Racing) return;
            // abyss, sea, outside the island
            float lim = world.Half - 90f;
            if (c.position.y < def.fallFloor)
            {
                Fall(r, "Caiu da cidadela");
                return;
            }
            if (c.position.y < world.data.fallY || Mathf.Abs(c.position.x) > lim || Mathf.Abs(c.position.z) > lim)
            {
                Fall(r, c.position.y < world.data.fallY ? "Caiu no abismo" : "Saiu da ilha");
                return;
            }
            TrackSafe(r, dt);
            CheckStuck(r, dt);
            // a bot that lost its way (missed a gate, wrong road after a respawn): back to the last gate it passed
            if (r.bot != null && raceTime - r.lastGateT > 150f) { r.lastGateT = raceTime; r.lostRecover = true; RequestRecover(r); }
        }

        void Fuel(Racer r, float dt)
        {
            if (!def.economy) return;
            var c = r.craft;
            float v = c.Speed / Hovercraft.MaxSpeed;
            float use = ((0.03f + 0.05f * v * v) * r.st.fuelUse + (c.nitroActive ? 0.25f : 0f)) * dt;
            r.fuel = Mathf.Max(0f, r.fuel - use);
            c.running = r.fuel > 0f;
            if (!r.lowFuelWarned && r.fuel < 20f) { r.lowFuelWarned = true; Emit(Ev.LowFuel, r); }
            if (r.fuel <= 0f && c.Speed < 2f)
            {
                r.lowFuelT += dt;
                if (r.lowFuelT > 2f) { r.state = PilotState.Stranded; Emit(Ev.Stranded, r, 0f, "sem combustível"); }
            }
        }

        void Repair(Racer r, float dt)
        {
            if (r.repairT <= 0f) return;
            r.integrity = Mathf.Min(100f, r.integrity + 4f * dt);
            r.repairT -= dt;
            if (r.repairT <= 0f) { r.repairT = 0f; Emit(Ev.RepairDone, r); }
        }

        void BotItems(Racer r)
        {
            var p = r.pilot;
            for (int k = 0; k < p.cons.Length; k++)
            {
                if (p.consCount[k] <= 0) continue;
                if (p.cons[k] == Consumable.RepairGel && r.integrity < 45f && r.repairT <= 0f) UseConsumable(r, k);
                else if (p.cons[k] == Consumable.FuelCell && r.fuel < 18f) UseConsumable(r, k);
            }
        }

        public void UseConsumable(Racer r, int slot)
        {
            var p = r.pilot;
            if (r.state != PilotState.Racing || slot >= p.consCount.Length || p.consCount[slot] <= 0) return;
            var type = p.cons[slot];
            if (type == Consumable.RepairGel)
            {
                if (r.integrity >= 99f || r.repairT > 0f) return;
                r.repairT = 5f;
                r.usedRepair = true;
                Emit(Ev.RepairStart, r);
            }
            else
            {
                if (!def.economy || r.fuel >= r.st.fuelCap - 1f) return;
                r.fuel = Mathf.Min(r.st.fuelCap, r.fuel + 30f);
                r.usedFuel = true;
                r.lowFuelWarned = r.fuel < 20f;
                Emit(Ev.FuelUsed, r);
            }
            p.consCount[slot]--;
            r.consumedCost += Catalog.ConsumableCost[(int)type];
        }

        // ------------------------------------------------------------------ gates

        public static bool CrossedGate(WGate g, Vector3 a, Vector3 b) => Crossed(g, a, b);

        /// <summary>Route index where each gate of the sequence is passed (first crossing after the previous one).</summary>
        public int[] GateIndices(Vector3[] route)
        {
            var idx = new int[def.sequence.Count];
            int i = 0;
            for (int g = 0; g < idx.Length; g++)
            {
                var gate = def.sequence[g];
                int found = -1;
                for (int k = i; k + 1 < route.Length; k++)
                {
                    if (Crossed(gate, route[k], route[k + 1]) || (route[k] - gate.Pos).sqrMagnitude < 15f * 15f) { found = k + 1; break; }
                }
                if (found < 0) found = route.Length - 1;
                idx[g] = found;
                i = Mathf.Min(found, route.Length - 1);
            }
            return idx;
        }

        static bool Crossed(WGate g, Vector3 a, Vector3 b)
        {
            var gp = g.Pos;
            var n = g.Dir;
            float da = Vector3.Dot(a - gp, n), db = Vector3.Dot(b - gp, n);
            if (!(da < 0f && db >= 0f)) return false;
            float t = da / (da - db);
            var p = Vector3.Lerp(a, b, t);
            var side = new Vector3(n.z, 0f, -n.x);
            float lat = Mathf.Abs(Vector3.Dot(p - gp, side));
            float up = p.y - gp.y;
            return lat < g.w * 0.5f + 40f && up > -60f && up < 200f;
        }

        void Gates(Racer r, Vector3 a, Vector3 b)
        {
            if (r.nextGate >= def.sequence.Count) return;
            var g = def.sequence[r.nextGate];
            // bots: the gate is passed when the pilot's route index passes the gate's index on that route
            bool viaRoute = r.bot != null && r.gateRouteIdx != null && r.nextGate < r.gateRouteIdx.Length && r.bot.index >= r.gateRouteIdx[r.nextGate]
                            && Vector3.Distance(b, g.Pos) < g.w + 200f;
            if (!viaRoute && !Crossed(g, a, b)) return;
            int phys = def.sequencePhys[r.nextGate];
            r.nextGate++;
            r.lastGateT = raceTime;
            if (r.nextGate >= def.sequence.Count)
            {
                Finish(r);
                return;
            }
            int perLap = def.gates.Length;
            if (def.Laps && r.nextGate % perLap == 0) Emit(Ev.Lap, r, r.nextGate / perLap + 1);
            else Emit(Ev.Gate, r, r.nextGate, g.name);
            // fuel stations at the 10th and 20th gate of the expedition
            if (def.economy && (phys == 9 || phys == 19))
            {
                r.fuel = Mathf.Min(r.st.fuelCap, r.fuel + 35f);
                r.lowFuelWarned = r.fuel < 20f;
                Emit(Ev.Refuel, r, 35f);
            }
        }

        void Finish(Racer r)
        {
            r.state = PilotState.Finished;
            r.finishTime = raceTime;
            r.repairT = 0f;
            r.craft.running = false;
            if (firstFinish < 0f) { firstFinish = raceTime; phase = RacePhase.Closing; }
            Emit(Ev.Finished, r, raceTime);
        }

        // ------------------------------------------------------------------ damage, destruction, falls

        /// <summary>AI hulls take less damage from crashes than a human (their driving is far from perfect).</summary>
        public float botDamage = 0.22f;

        public void Damage(Racer r, float amount, string cause, bool raw = false)
        {
            if (amount <= 0f || r.state != PilotState.Racing || r.invulnT > 0f) return;
            if (r.bot != null && !r.pilot.human && !raw) amount *= botDamage;
            if (def.kind == EventKind.Explore) return;
            r.integrity -= amount;
            if (amount > 0.5f) r.tookDamage = true;
            r.minIntegrity = Mathf.Min(r.minIntegrity, r.integrity);
            if (r.repairT > 0f && amount > 2f) { r.repairT = 0f; Emit(Ev.RepairInterrupted, r); }
            if (!r.criticalWarned && r.integrity < 25f && r.integrity > 0f) { r.criticalWarned = true; Emit(Ev.Critical, r); }
            if (r.integrity <= 0f) Destroy(r, cause);
        }

        void Destroy(Racer r, string cause)
        {
            r.integrity = 0f;
            r.state = PilotState.Destroyed;
            r.destroyTime = raceTime;
            r.destroyCause = cause;
            r.repairT = 0f;
            r.craft.running = false;
            int n = 0;
            if (def.economy)
            {
                // loss selection (GDD 11.2, demo policy): only real, non-insured equipped instances
                var cand = new List<ItemInst>();
                foreach (var it in r.pilot.equip) if (it != null && it.id != r.pilot.insuredId) cand.Add(it);
                for (int i = cand.Count - 1; i > 0; i--) { int j = rng.Next(i + 1); (cand[i], cand[j]) = (cand[j], cand[i]); }
                n = Mathf.Min(LossCount, cand.Count);
                for (int i = 0; i < n; i++)
                {
                    var it = cand[i];
                    if (pool.Contains(it)) continue;
                    pool.Add(it);
                    r.lost.Add(it);
                    poolValue += it.value;
                    Emit(Ev.PoolAdd, r, it.value, it.DisplayName);
                }
            }
            Emit(Ev.Destroyed, r, n, cause);
        }

        void Fall(Racer r, string cause)
        {
            Emit(Ev.Fall, r, 0f, cause);
            Damage(r, 15f * Mathf.Lerp(1f, r.st.armor, 0.5f), cause);
            if (r.state == PilotState.Destroyed) return;
            r.state = PilotState.Respawning;
            r.respawnT = 1.2f;
            r.repairT = 0f;
            r.craft.running = false;
        }

        /// <summary>The player asked to go back to the road (R / Triangle).</summary>
        public void RequestRecover(Racer r)
        {
            if (r.state != PilotState.Racing) return;
            r.state = PilotState.Respawning;
            r.respawnT = 0.35f;
            r.craft.running = false;
        }

        /// <summary>Safe spot check (port of safe_respawn.gd): wide flat floor and room for the hull.</summary>
        public static bool SafeSpot(Vector3 floor, Vector3 dir, out Vector3 center)
        {
            center = floor;
            dir.y = 0f;
            if (dir.sqrMagnitude < 0.25f) return false;
            dir.Normalize();
            var right = new Vector3(dir.z, 0f, -dir.x);
            var normal = Vector3.up;
            var offsets = new[] { Vector3.zero, dir * 5.5f, -dir * 5.5f, right * 3.2f, -right * 3.2f };
            for (int k = 0; k < offsets.Length; k++)
            {
                var p = floor + offsets[k];
                if (!Physics.Raycast(p + Vector3.up * 3f, Vector3.down, out var hit, 7f, IslandWorld.ProbeMask, QueryTriggerInteraction.Ignore)) return false;
                if (hit.normal.y < 0.92f) return false;
                if (k == 0) { center = hit.point; normal = hit.normal; }
                else if (Mathf.Abs(Vector3.Dot(hit.point - center, normal)) > 0.65f) return false;
            }
            var rot = Quaternion.LookRotation(dir);
            return !Physics.CheckBox(center + Vector3.up * 3.3f, new Vector3(2.9f, 0.8f, 5.4f), rot, IslandWorld.SolidMask, QueryTriggerInteraction.Ignore);
        }

        void TrackSafe(Racer r, float dt)
        {
            r.safeT -= dt;
            if (r.safeT > 0f) return;
            r.safeT = 0.5f;
            var c = r.craft;
            if (!c.onGround || c.Speed < 12f || r.stuckT > 1f || c.onWater) return;
            if (SafeSpot(c.groundPoint, c.Forward, out var center))
            {
                r.safe.Add((center, c.yaw));
                if (r.safe.Count > 16) r.safe.RemoveAt(0);
            }
        }

        void Respawn(Racer r)
        {
            var cands = new List<(Vector3, Vector3)>();
            bool lost = r.lostRecover;
            r.lostRecover = false;
            // at least two seconds back: never respawn on the obstacle that caused the fall
            for (int i = lost ? -1 : r.safe.Count - 5; i >= 0; i--)
                cands.Add((r.safe[i].pos, new Vector3(Mathf.Sin(r.safe[i].yaw), 0f, Mathf.Cos(r.safe[i].yaw))));
            for (int gi = r.nextGate - 1; gi >= -1; gi--)
            {
                var g = gi >= 0 ? def.sequence[gi] : def.start;
                foreach (float back in new[] { 0f, 12f, 24f }) cands.Add((g.Pos - g.Dir * back, g.Dir));
            }
            if (!lost && r.bot != null && r.bot.route != null && r.bot.route.Length > 1)
            {
                int i = Mathf.Clamp(r.bot.Nearest(r.craft.position) - 4, 0, r.bot.route.Length - 2);
                cands.Insert(0, (r.bot.route[i], r.bot.route[i + 1] - r.bot.route[i]));
            }
            Vector3 pos = def.start.Pos, dir = def.start.Dir;
            bool found = false;
            foreach (var (p, d) in cands)
            {
                world.EnsureCollidersAt(p, 200f);
                var g = GroundAt(p);
                if (SafeSpot(g, d, out var center)) { pos = center; dir = d; found = true; break; }
            }
            if (!found && cands.Count > 0) { pos = GroundAt(cands[0].Item1); dir = cands[0].Item2; }
            r.safe.Clear();
            r.craft.Place(pos, dir, 12f);
            r.craft.running = r.fuel > 0f || !def.economy;
            r.craft.controlsBlocked = false;
            r.prevPos = r.craft.position;
            r.prevYaw = r.craft.yaw;
            r.state = PilotState.Racing;
            r.invulnT = 2f;
            r.stuckT = 0f;
            r.stuckP = r.craft.position;
            if (r.bot != null) r.bot.Resync();
            Emit(Ev.Respawned, r);
        }

        void CheckStuck(Racer r, float dt)
        {
            // progress in the world, not declared speed: walls can hold a fast ship in place
            if (r.craft.input.brake && r.bot == null) { r.stuckT = 0f; r.stuckP = r.craft.position; return; }
            if ((r.craft.position - r.stuckP).sqrMagnitude > 81f) { r.stuckT = 0f; r.stuckP = r.craft.position; return; }
            r.stuckT += dt;
            if (r.bot != null && r.stuckT >= 6f) { r.stuckT = 0f; RequestRecover(r); }
        }

        // ------------------------------------------------------------------ ghosts (bots far away)

        void UpdateGhosts()
        {
            if (noGhosts) return;
            foreach (var r in racers)
            {
                if (r.bot == null) continue;
                float d = HumanDistance(r.craft.position);
                if (!r.ghost && d > GhostOn && r.craft.onGround && r.state != PilotState.Respawning)
                {
                    r.ghost = true;
                    r.ghostSpeed = r.craft.Speed;
                    r.bot.Resync();
                }
                else if (r.ghost && d < GhostOff)
                {
                    r.ghost = false;
                    if (r.state == PilotState.Racing && r.bot.route != null)
                    {
                        world.EnsureCollidersAt(r.craft.position, 300f);
                        var g = GroundAt(r.craft.position);
                        r.craft.Place(g, r.craft.Forward, r.ghostSpeed);
                        r.craft.running = true;
                        r.craft.controlsBlocked = false;
                        r.prevPos = r.craft.position;
                        r.bot.Resync();
                    }
                }
            }
        }

        float HumanDistance(Vector3 p)
        {
            float best = float.MaxValue;
            foreach (var h in racers)
                if (h.pilot.human) best = Mathf.Min(best, Vector3.Distance(h.craft.position, p));
            return settling ? float.MaxValue : best;
        }

        void GhostStep(Racer r, float dt)
        {
            var b = r.bot;
            var route = b.route;
            if (route == null || route.Length < 2) return;
            var c = r.craft;
            // target speed from the curvature ahead (same braking rule as the pilot)
            float v = r.ghostSpeed;
            float maxK = 0f;
            for (int j = 1; j < 10 + (int)(v / 12f); j++) maxK = Mathf.Max(maxK, b.Kappa(Mathf.Min(b.index + j, route.Length - 1)));
            float top = Hovercraft.MaxSpeed * c.topSpeedMul * Mathf.Lerp(0.78f, 0.87f, b.skill);
            float curveV = maxK > 1e-4f ? Hovercraft.TurnRate(v) * Mathf.Lerp(0.75f, 0.92f, b.skill) / maxK * 1.35f : top;
            float want = Mathf.Min(top, Mathf.Max(curveV, 35f));
            v = Mathf.MoveTowards(v, want, (want > v ? Hovercraft.Accel * 0.8f : 18f) * dt);
            r.ghostSpeed = v;
            // advance along the polyline
            var before = c.position;
            float move = v * dt;
            var pos = c.position - Vector3.up * Hovercraft.Hover;
            int i = b.index;
            while (move > 0f && i + 1 < route.Length)
            {
                var to = route[i + 1] - pos;
                float d = to.magnitude;
                if (d <= move) { pos = route[i + 1]; move -= d; i++; }
                else { pos += to / d * move; move = 0f; }
            }
            b.index = Mathf.Min(i, route.Length - 1);
            var dir = route[Mathf.Min(b.index + 1, route.Length - 1)] - pos;
            dir.y = 0f;
            if (dir.sqrMagnitude > 1e-4f) c.yaw = Mathf.Atan2(dir.x, dir.z);
            c.position = pos + Vector3.up * Hovercraft.Hover;
            c.vel = c.Forward * v;
            c.onGround = true;
            r.distance += v * dt;
            Fuel(r, dt);
            // rare incidents, more frequent for rookies and on the dangerous levels
            if (rng.NextDouble() < (1.1f - b.skill) * 0.00024f * (v / 80f))
            {
                float dmg = 5f + (float)rng.NextDouble() * 17f;
                Damage(r, dmg * r.st.armor, "Colisão", true);
                r.ghostSpeed *= 0.55f;
            }
            if (r.state != PilotState.Racing) return;
            BotItems(r);
            Repair(r, dt);
            Gates(r, before, c.position);
            if (b.index >= route.Length - 1 && r.state == PilotState.Racing)
            {
                // end of the route without the finish line (should not happen): force it
                while (r.state == PilotState.Racing && r.nextGate < def.sequence.Count) Gates(r, def.sequence[r.nextGate].Pos - def.sequence[r.nextGate].Dir * 5f, def.sequence[r.nextGate].Pos + def.sequence[r.nextGate].Dir * 5f);
            }
        }

        // ------------------------------------------------------------------ ships touching each other

        void ShipCollisions()
        {
            const float R = 2.7f, Half = 3.6f;
            for (int i = 0; i < racers.Count; i++)
            {
                var a = racers[i];
                if (a.ghost || a.pilot.remote || a.state != PilotState.Racing || a.invulnT > 0f) continue;
                for (int j = i + 1; j < racers.Count; j++)
                {
                    var b = racers[j];
                    if (b.ghost || b.pilot.remote || b.state != PilotState.Racing || b.invulnT > 0f) continue;
                    var ca = a.craft; var cb = b.craft;
                    var d0 = cb.position - ca.position;
                    if (d0.sqrMagnitude > 16f * 16f || Mathf.Abs(d0.y) > 3f) continue;
                    ClosestOnSegments(ca.position - ca.Forward * Half, ca.position + ca.Forward * Half,
                                      cb.position - cb.Forward * Half, cb.position + cb.Forward * Half, out var pa, out var pb);
                    var d = pb - pa;
                    d.y = 0f;
                    float dist = d.magnitude;
                    if (dist >= 2f * R) continue;
                    var nrm = dist > 1e-3f ? d / dist : ca.Right;
                    float push = (2f * R - dist) * 0.5f;
                    ca.position -= nrm * push;
                    cb.position += nrm * push;
                    float va = Vector3.Dot(ca.vel, nrm), vb = Vector3.Dot(cb.vel, nrm);
                    float rel = va - vb;
                    if (rel > 0f)
                    {
                        // inelastic exchange along the contact normal (a little bounce)
                        float avg = (va + vb) * 0.5f, e = 0.25f;
                        float na = avg - (va - avg) * e, nb = avg - (vb - avg) * e;
                        ca.vel += nrm * (na - va);
                        cb.vel += nrm * (nb - vb);
                    }
                    if (rel > 9f && raceTime - a.lastBumpT > 0.7f && raceTime - b.lastBumpT > 0.7f)
                    {
                        a.lastBumpT = b.lastBumpT = raceTime;
                        float dmg = Mathf.Min(10f, (rel - 9f) * 0.45f);
                        Emit(Ev.ShipBump, a, rel, null, b.index);
                        Damage(a, dmg * a.st.armor, "Colisão com " + b.pilot.name);
                        Damage(b, dmg * b.st.armor, "Colisão com " + a.pilot.name);
                    }
                }
            }
        }

        static void ClosestOnSegments(Vector3 p1, Vector3 q1, Vector3 p2, Vector3 q2, out Vector3 c1, out Vector3 c2)
        {
            var d1 = q1 - p1; var d2 = q2 - p2; var r = p1 - p2;
            float a = Vector3.Dot(d1, d1), e = Vector3.Dot(d2, d2), f = Vector3.Dot(d2, r);
            float s, t;
            float c = Vector3.Dot(d1, r), b = Vector3.Dot(d1, d2);
            float den = a * e - b * b;
            s = den > 1e-6f ? Mathf.Clamp01((b * f - c * e) / den) : 0f;
            t = (b * s + f) / e;
            if (t < 0f) { t = 0f; s = Mathf.Clamp01(-c / a); }
            else if (t > 1f) { t = 1f; s = Mathf.Clamp01((b - c) / a); }
            c1 = p1 + d1 * s;
            c2 = p2 + d2 * t;
        }

        // ------------------------------------------------------------------ ordering

        void UpdateOrder()
        {
            foreach (var r in racers)
            {
                if (r.state == PilotState.Finished) { r.progress = 1e6f - r.finishTime; continue; }
                int g = Mathf.Min(r.nextGate, gatePos.Length - 2);
                var target = gatePos[Mathf.Min(r.nextGate + 1, gatePos.Length - 1)];
                float d = Vector3.Distance(r.craft.position, target);
                float frac = Mathf.Clamp(1f - d / Mathf.Max(gateLen[Mathf.Min(r.nextGate, gateLen.Length - 1)], 1f), 0f, 0.99f);
                r.progress = r.nextGate + frac;
                if (r.state == PilotState.Destroyed) r.progress = -1e6f + r.destroyTime;
            }
            order.Clear();
            order.AddRange(racers);
            order.Sort((a, b) => b.progress.CompareTo(a.progress));
            for (int i = 0; i < order.Count; i++) order[i].place = i + 1;
        }

        public Vector3 NextTarget(Racer r)
        {
            if (r.nextGate < def.sequence.Count) return def.sequence[r.nextGate].Pos;
            return def.finish != null ? def.finish.Pos : def.start.Pos;
        }

        public float RemainingKm(Racer r)
        {
            float d = Vector3.Distance(r.craft.position, NextTarget(r));
            for (int i = r.nextGate + 1; i < gateLen.Length - 1; i++) d += gateLen[i];
            return d / 1000f;
        }

        /// <summary>Humans are done: every bot runs as a ghost, many steps per frame, until the race closes.</summary>
        public void FastForward(int steps)
        {
            settling = true;
            foreach (var r in racers) if (r.bot != null) r.ghost = true;
            for (int i = 0; i < steps && phase != RacePhase.Done; i++) Step(Dt);
        }
    }
}
