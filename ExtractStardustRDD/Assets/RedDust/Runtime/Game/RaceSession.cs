using System;
using System.Collections.Generic;
using System.Linq;
using RedDust.Meta;
using RedDust.Presentation;
using RedDust.Track;
using RedDust.Vehicle;
using UnityEngine;

namespace RedDust.Game
{
    /// <summary>
    /// Uma corrida: pilotos, grelha 5 por fila, posições, checkpoints largos (distância de corrida em qualquer linha
    /// ou altura), dano/combustível/calor, Expedition Pool real, estados finais e resultados aplicados aos perfis.
    /// </summary>
    public sealed class RaceSession
    {
        public readonly GameMode mode;
        public readonly CourseGraph graph;
        public readonly CourseData course;
        public readonly string courseTitle, raceId;
        public readonly List<Racer> racers = new List<Racer>();
        public readonly ExpeditionPool pool = new ExpeditionPool();
        public readonly int checkpoints;
        public readonly float referenceSeconds, referenceMinutes, clockReference;
        public float time;
        public bool started, finished;
        public readonly List<RaceReport> reports = new List<RaceReport>();
        public readonly Dictionary<string, List<EquipmentInstance>> poolAwards = new Dictionary<string, List<EquipmentInstance>>();
        readonly Dictionary<Racer, List<EquipmentInstance>> lostBy = new Dictionary<Racer, List<EquipmentInstance>>();
        readonly HashSet<Racer> handled = new HashSet<Racer>();
        readonly Rng rng;

        public struct Note { public string text; public Color color; public float until; public int player; }
        public readonly List<Note> feed = new List<Note>();

        public bool Rules => mode != GameMode.Exploration;
        public IEnumerable<Racer> Humans => racers.Where(r => r.human);
        public int ActiveCount => racers.Count(r => r.Active);
        /// <summary>Distância da meta (duração escolhida: curta, média ou completa).</summary>
        public float FinishDistance { get; private set; }
        public bool HumansDone => racers.Where(r => r.human).All(r => !r.Active);

        static readonly string[] BotNames = { "KESTREL", "MAKO", "RUSTFANG", "DUNE-7", "VEX", "HALCYON", "ORBIT", "CINDER", "NOVA RAE", "TALON", "SABLE", "ZEPHYR",
                                              "GRIT", "MIRAGE", "BRASS", "ECHO-9", "JUNO", "RIFT", "ASHBORN", "QUILL", "STRAY", "BLAZE", "OKKO", "LUMEN" };
        static readonly uint[] BotPaints = { 0x13B5C9, 0x2F5BD9, 0xE09A1A, 0xC0249A, 0xD8D8D8, 0x7BC42A, 0x0E8C7A, 0x6A3FC8, 0xE5561B, 0x8C9196, 0x9E1027, 0xE3C51C };

        public RaceSession(GameMode mode, CourseGraph graph, string title, Rng rng, float lengthFrac = 1f)
        {
            this.mode = mode; this.graph = graph; this.rng = rng;
            course = graph.Main.Data;
            courseTitle = title;
            raceId = $"{title}-{DateTime.UtcNow.Ticks:x}-{rng.NextU() & 0xffff:x}";
            FinishDistance = Mathf.Clamp(course.Length * Mathf.Clamp(lengthFrac, 0.2f, 1f), Mathf.Min(course.Length, 4000f), course.Length);
            checkpoints = Mathf.Clamp(Mathf.RoundToInt(FinishDistance / 2500f), 4, 40);
            referenceSeconds = FinishDistance / 100f;            // ~360 km/h de média
            referenceMinutes = referenceSeconds / 60f;
            clockReference = FinishDistance / 104f;              // "Contra o Relógio": ~375 km/h de média
        }

        public void Notify(string text, Color color, float seconds = 4f, int player = -1)
        {
            feed.Add(new Note { text = text, color = color, until = Time.time + seconds, player = player });
            GameAudio.OnNote(text, player >= 0 || racers.Exists(r => r.human && text.Contains(r.name)));
        }

        // ------------------------------------------------------------------ pilotos

        public Racer AddHuman(PlayerProfile p, int player, PilotInput input, Color paint)
        {
            var c = Catalog.ChassisOf(p.chassis);
            var craft = ShipBuilder.Spawn(p.name, c, ShipBuilder.Mounted(p), paint, out var stats, out var spec);
            var r = new Racer { id = p.slot, name = p.name, human = true, player = player, profile = p, chassis = c, stats = stats, spec = spec, craft = craft, paint = paint, input = input, rules = Rules };
            if (Rules)
            {
                r.carried = p.Equipped();
                r.insured = p.insured;
                r.slots = p.loadout.Select(s => new ConsumableStack(s.id, s.count)).ToList();
            }
            while (r.slots.Count < Economy.LoadoutSlots) r.slots.Add(new ConsumableStack("", 0));
            r.Attach();
            racers.Add(r);
            return r;
        }

        public Racer AddBot(int index, int difficulty, float lane)
        {
            string name = BotNames[index % BotNames.Length];
            var c = Catalog.Chassis[rng.Range(0, Catalog.Chassis.Length)];
            var p = (Personality)rng.Weighted(difficulty == 0 ? new double[] { 1, 2, 1, 1, 3 } : difficulty == 1 ? new double[] { 2, 2, 2, 2, 1 } : new double[] { 3, 1, 3, 2, 0.3 });
            var loadout = Economy.BotLoadout(c, difficulty, rng, "bot:" + name);
            var mounted = new Dictionary<string, EquipmentInstance>();
            foreach (var (socket, item) in loadout) mounted[socket] = item;
            uint rgb = BotPaints[index % BotPaints.Length];
            var paint = ShipBuilder.Paint(rgb);
            var craft = ShipBuilder.Spawn($"{name} ({c.name})", c, mounted, paint, out var stats, out var spec);
            var r = new Racer
            {
                id = "bot:" + name, name = name, chassis = c, stats = stats, spec = spec, craft = craft, paint = paint, rules = Rules,
                carried = loadout.Select(x => x.item).ToList(),
                brain = new BotBrain(graph, p, difficulty, lane, rng),
            };
            r.insured = r.carried.Count > 0 && rng.Chance(0.7) ? r.carried.OrderByDescending(i => i.value).First().id : "";
            r.slots.Add(new ConsumableStack(rng.Chance(0.5) ? "foam" : "nanogel", 1 + rng.Range(0, 2)));
            r.slots.Add(new ConsumableStack(rng.Chance(0.5) ? "fuel" : "coolant", 1));
            r.slots.Add(new ConsumableStack(rng.Chance(0.5) ? "surge" : "stab", 1));
            r.Attach();
            racers.Add(r);
            return r;
        }

        /// <summary>Grelha da largada: 5 por fila, filas desencontradas (Doc 01 §16.2); o primeiro da lista fica à frente.</summary>
        public void PlaceGrid(IList<Racer> order)
        {
            int rows = Mathf.CeilToInt(order.Count / 5f);
            float front = Mathf.Min(course.Start + 30f + (rows - 1) * 16f, course.Length * 0.25f);
            for (int i = 0; i < order.Count; i++)
            {
                int row = i / 5, col = i % 5;
                int st = course.StationAt(Mathf.Max(course.Start + 5f, front - row * 16f));
                float half = Mathf.Max(6f, 0.5f * (course.RideLeft[st] + course.RideRight[st]));
                float spacing = Mathf.Clamp(2f * half / 5.5f, 4.4f, 7.5f);
                float u = Mathf.Clamp(((col - 2) * spacing + (row % 2 == 1 ? spacing * 0.5f : 0f)) / half, -0.85f, 0.85f);
                var r = order[i];
                Vector3 n = course.LaneNormal(st, u);
                Vector3 pos = course.LanePoint(st, u) + n * (r.craft.tuning.hoverHeight + 0.25f);
                r.craft.Place(pos, Quaternion.LookRotation(Vector3.ProjectOnPlane(course.Tangent[st], n), n), 0f);
                r.pathIdx = 0; r.station = st;
                r.raceDistance = course.Dist[st];
                r.brain?.Reset(0);
            }
        }

        // ------------------------------------------------------------------ passo fixo

        public void Tick(float dt)
        {
            if (started && !finished) time += dt;
            foreach (var r in racers)
            {
                if (r.craft == null) continue;
                // onde está (grafo de rotas): bots pelo seguidor, jogadores pelo localizador com histerese
                if (r.brain != null && r.brain.route.Station >= 0)
                {
                    r.pathIdx = r.brain.route.PathIndex; r.station = r.brain.route.Station;
                    r.raceDistance = r.brain.route.RaceDistance;
                }
                else if (r.brain == null)
                {
                    graph.Locate(r.craft.Position, ref r.pathIdx, ref r.station);
                    var path = graph.Paths[r.pathIdx];
                    r.raceDistance = path.ToRaceDistance(path.Data.Dist[r.station]);
                }
                r.NotePath(graph, r.pathIdx);

                if (!started || !r.Active)
                {
                    r.craft.input = new CraftInput();
                    if (!started) r.craft.Body.linearVelocity = Vector3.Lerp(r.craft.Body.linearVelocity, Vector3.zero, 0.2f);
                }
                else if (r.brain != null) r.craft.input = r.Limit(r.brain.Drive(r, racers, dt));
                else r.craft.input = r.Limit(r.input != null ? r.input.Read(dt) : new CraftInput());

                r.Tick(dt, referenceSeconds);
                if (!started) continue;
                r.grace -= dt;

                // queda para fora da geologia: reposiciona (penalização para jogadores)
                var d = graph.Paths[r.pathIdx].Data;
                if (r.Active && r.craft.Position.y < d.Center[Mathf.Clamp(r.station, 0, d.StationCount - 1)].y - 60f) Respawn(r, true);
                // mais de 20 m fora da pista durante 1,5 s: volta à pista sozinho (sem penalização de casco)
                if (r.Active && !d.IsGap(r.station) && d.OutsideRide(r.craft.Position, r.station) > OffTrackMeters)
                {
                    r.offTrack += dt;
                    if (r.offTrack > 1.5f)
                    {
                        r.offTrack = 0f;
                        Respawn(r, false);
                        if (r.human) Notify("Fora da pista · reposicionado", new Color(1f, 0.8f, 0.4f), 2.5f, r.player);
                    }
                }
                else r.offTrack = 0f;

                // checkpoints largos: qualquer linha, altura ou rota conta pela distância de corrida
                int cp = Mathf.Clamp(Mathf.FloorToInt(r.raceDistance / FinishDistance * checkpoints), 0, checkpoints);
                if (r.Active && cp > r.checkpoint)
                {
                    r.checkpoint = cp;
                    if (r.human && cp < checkpoints) Notify($"CHECKPOINT {cp}/{checkpoints}", new Color(0.7f, 0.9f, 1f), 2f, r.player);
                }

                // chegada (EXTRACTED)
                if (r.Active && ((r.pathIdx == 0 && r.station >= course.StationCount - 3) || r.raceDistance >= FinishDistance - 3f))
                {
                    r.state = RaceState.Extracted;
                    r.finishTime = time;
                    r.endDistance = FinishDistance;
                    if (Rules) Notify($"{r.name} EXTRACTED ({RaceHud.FormatTime(time)})", new Color(0.5f, 1f, 0.6f));
                }
                if (!r.Active && !handled.Contains(r)) OnRaceEnded(r);
            }
            // último sobrevivente: se os bots estão todos fora (destruídos, sem combustível, abandonados) e nenhum extraiu,
            // a corrida acaba e quem ainda está em pista extrai (fica com o Expedition Pool)
            if (started && !finished && Rules && racers.Any(x => !x.human) && racers.Where(x => !x.human).All(x => !x.Active && x.state != RaceState.Extracted))
                foreach (var h in racers.Where(x => x.human && x.Active))
                {
                    h.state = RaceState.Extracted;
                    h.finishTime = time;
                    h.endDistance = h.raceDistance;
                    Notify("ÚLTIMO SOBREVIVENTE · EXTRACTED", new Color(0.5f, 1f, 0.6f), 6f, h.player);
                }
            UpdatePositions();
        }

        public const float OffTrackMeters = 20f;

        /// <summary>Ponto do centro da pista ~meters à frente do piloto no percurso atual (para a seta de direção).</summary>
        public Vector3 AheadPoint(Racer r, float meters)
        {
            var d = graph.Paths[r.pathIdx].Data;
            int st = Mathf.Clamp(r.station, 0, d.StationCount - 1);
            float target = d.Dist[st] + meters;
            while (st < d.StationCount - 1 && d.Dist[st] < target) st++;
            return d.Center[st];
        }

        public void Respawn(Racer r, bool penalty)
        {
            var d = graph.Paths[r.pathIdx].Data;
            int st = Mathf.Clamp(r.station - 12, 0, d.StationCount - 2);
            while (st > 0 && d.IsGap(st)) st--;
            r.craft.Place(d.Center[st] + d.Up[st] * (r.craft.tuning.hoverHeight + 0.3f), Quaternion.LookRotation(d.Tangent[st], d.Up[st]), 30f);
            r.station = st;
            r.brain?.route.Reset(r.pathIdx, r.brain.route.line.laneU);
            if (penalty && Rules && r.Active)
            {
                r.penalties++;
                r.Damage(r.spec.hullMax * 0.05f);
                if (r.human) Notify("Reposicionado · penalização", new Color(1f, 0.8f, 0.4f), 2.5f, r.player);
            }
        }

        public void Abandon(Racer r)
        {
            if (!r.Active) return;
            r.state = RaceState.Abandoned;
            r.endDistance = r.raceDistance;
            OnRaceEnded(r);
        }

        /// <summary>Fim de corrida de um piloto: destruído/encalhado/abandonado → até 3 peças não seguradas vão para o Pool.</summary>
        void OnRaceEnded(Racer r)
        {
            handled.Add(r);
            if (r.state == RaceState.Extracted) return;
            r.endDistance = r.raceDistance;
            if (r.state == RaceState.Destroyed)
            {
                r.Destroyed();
                Notify($"RACER DESTROYED · {r.name}", new Color(1f, 0.45f, 0.35f));
                r.input?.Rumble(1f, 1f, 0.6f);
            }
            else if (r.state == RaceState.Stranded) Notify($"STRANDED · {r.name} sem combustível", new Color(1f, 0.75f, 0.35f));
            if (!Rules) return;
            var lost = LossRules.SelectLosses(r.carried, r.insured, rng);
            lostBy[r] = lost;
            long added = 0;
            foreach (var it in lost)
            {
                if (!pool.Add(it, r.id)) continue;
                added += it.value;
                if (it.rarity == Rarity.Legendary) Notify($"LEGENDARY ITEM ADDED · {it.Label}", Icons.RarityColor(Rarity.Legendary), 6f);
                else if (it.rarity >= Rarity.Rare) Notify($"{RarityInfo.Name(it.rarity).ToUpperInvariant()} no Pool · {it.Name}", Icons.RarityColor(it.rarity), 4.5f);
            }
            if (added > 0) Notify($"POOL +{Fmt.Dust(added)}", new Color(1f, 0.85f, 0.45f));
        }

        void UpdatePositions()
        {
            int i = 1;
            foreach (var r in Classification()) r.position = i++;
        }

        /// <summary>Classificação: extraídos por tempo; a correr por distância; destruídos/encalhados/abandonados no fim.</summary>
        public List<Racer> Classification() =>
            racers.OrderBy(r => r.state == RaceState.Extracted ? 0 : r.Active ? 1 : 2)
                  .ThenBy(r => r.state == RaceState.Extracted ? r.finishTime : 0f)
                  .ThenByDescending(r => r.Active ? r.raceDistance : r.endDistance)
                  .ToList();

        // ------------------------------------------------------------------ fim da corrida

        /// <summary>
        /// Quando todos os jogadores acabaram: os bots ainda em pista recebem tempo projetado (ritmo médio até agora),
        /// distribui-se o Pool real pelos EXTRACTED e aplicam-se os resultados aos perfis (idempotente pelo raceId).
        /// </summary>
        public void Finish()
        {
            if (finished) return;
            finished = true;
            foreach (var r in racers.Where(r => r.Active && !r.human))
            {
                float pace = Mathf.Max(60f, r.raceDistance / Mathf.Max(1f, time));
                r.finishTime = time + Mathf.Max(0f, FinishDistance - r.raceDistance) / pace;
                r.state = RaceState.Extracted;
                r.endDistance = FinishDistance;
            }
            UpdatePositions();
            var order = Classification();
            if (Rules)
            {
                var extracted = order.Where(r => r.state == RaceState.Extracted).Select(r => r.id).ToList();
                foreach (var kv in pool.Distribute(extracted)) poolAwards[kv.Key] = kv.Value;
            }
            foreach (var r in order.Where(r => r.human))
            {
                var o = new RaceOutcome
                {
                    raceId = raceId + "-" + r.id, course = courseTitle, mode = mode, state = r.state, position = r.position, racers = racers.Count,
                    time = r.state == RaceState.Extracted ? r.finishTime : time, referenceTime = clockReference, referenceMinutes = referenceMinutes,
                    hullFrac = r.HullFrac, fuelFrac = r.fuel, tookDamage = r.tookDamage, usedBoost = r.usedBoost, repairs = r.repairs,
                    penalties = r.penalties, allCheckpoints = r.checkpoint >= checkpoints - 1, skillRoutes = r.skillRoutes,
                    consumed = r.consumed, poolValue = pool.Valuation,
                };
                if (lostBy.TryGetValue(r, out var lost)) o.lostItemIds = lost.Select(i => i.id).ToList();
                if (poolAwards.TryGetValue(r.id, out var won)) o.gained = won;
                if (mode == GameMode.Exploration)
                {
                    // exploração: sem risco nem prémios; o relatório só mostra o tempo (não substitui a última expedição)
                    reports.Add(new RaceReport { raceId = o.raceId, course = courseTitle, mode = mode.ToString(), chassis = r.chassis.name, state = r.state,
                        position = 1, racers = 1, time = o.time, hull = 1f, fuel = 1f });
                    continue;
                }
                var rep = Economy.ApplyRace(r.profile, o);
                ProfileStore.Save(r.profile);
                reports.Add(rep);
            }
        }

        public void Dispose()
        {
            foreach (var r in racers)
            {
                r.Detach();
                r.input?.Stop();
                if (r.craft != null) UnityEngine.Object.Destroy(r.craft.gameObject);
            }
            racers.Clear();
        }
    }
}
