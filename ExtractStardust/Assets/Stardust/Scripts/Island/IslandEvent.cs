using System.Collections.Generic;
using UnityEngine;

namespace Stardust
{
    public enum EventKind { Expedition, Circuit, Drag, Explore }

    /// <summary>
    /// One race of the island in a common format (port of race.gd _make_event): the Expedition is the Grande Corrida
    /// from A to B through every zone (30 gates, several variants per section) with the extraction economy;
    /// circuits have laps; the drag is a straight; Explore is free roaming without a clock.
    /// </summary>
    public class EventDef
    {
        public string id, name, subtitle;
        public EventKind kind;
        public int laps = 1;
        public WGate start;
        public WGate[] gates;
        public WGate finish;              // null: circuits finish on their last gate
        public float halfW = 46f;
        public Vector3[] lapRoute;        // circuits and drag (bots follow it)
        public float[] lapJumps;
        public bool economy;              // losses, pool and insurance
        public float rewardScale = 1f;
        public float referenceTime = 1200f;
        public float closeTime = 240f;
        public int botCount = 15;
        public float lengthKm;
        public float fallFloor = float.NegativeInfinity;   // suspended tracks: below this height the racer fell off

        /// <summary>Gates in the order they are passed (circuits repeat them every lap).</summary>
        public readonly List<WGate> sequence = new List<WGate>();
        public readonly List<int> sequencePhys = new List<int>();

        void BuildSequence()
        {
            sequence.Clear();
            sequencePhys.Clear();
            for (int lap = 0; lap < Mathf.Max(1, laps); lap++)
                for (int i = 0; i < gates.Length; i++) { sequence.Add(gates[i]); sequencePhys.Add(i); }
            if (finish != null && finish.Valid) { sequence.Add(finish); sequencePhys.Add(-1); }
        }

        public static EventDef Expedition(WorldJson w)
        {
            var e = new EventDef
            {
                id = "expedicao", name = "Expedição — Grande Corrida", subtitle = "De A a B por todas as zonas da ilha · 30 portões · extração",
                kind = EventKind.Expedition, start = w.start, gates = w.checkpoints, finish = w.finish, halfW = 46f,
                economy = true, rewardScale = 1f, referenceTime = 20f * 60f, closeTime = 240f, botCount = 15,
            };
            float len = 0f;
            foreach (var s in w.sections) len += s.variants[0].length;
            e.lengthKm = len / 1000f;
            e.BuildSequence();
            return e;
        }

        public static EventDef FromWorld(WEvent ev)
        {
            var e = new EventDef
            {
                id = ev.id, name = ev.name, laps = Mathf.Max(1, ev.laps), start = ev.start, gates = ev.gates,
                finish = ev.finish != null && ev.finish.Valid ? ev.finish : null,
                lapRoute = WVariant.Flat(ev.route), lapJumps = ev.jumps, economy = false, lengthKm = ev.length * Mathf.Max(1, ev.laps) / 1000f,
            };
            if (ev.type == "drag")
            {
                e.kind = EventKind.Drag; e.halfW = 46f; e.botCount = 3; e.rewardScale = 0.25f; e.referenceTime = 32f; e.closeTime = 20f;
                e.subtitle = "Arranque na Planície de Sal · 3 km a direito";
            }
            else
            {
                e.kind = EventKind.Circuit; e.halfW = 34f; e.botCount = 7; e.rewardScale = 0.45f; e.closeTime = 60f;
                e.referenceTime = ev.length * e.laps / 95f;
                e.subtitle = $"{e.laps} voltas · {ev.length / 1000f:0.0} km por volta";
                if (ev.id == "titan")
                {
                    e.halfW = 40f; e.fallFloor = TitanCircuit.FallLimit;
                    e.subtitle = $"Circuito suspenso a 440 m · {e.laps} voltas · 2 saltos com desvio";
                }
            }
            e.BuildSequence();
            return e;
        }

        public static EventDef Explore(WorldJson w)
        {
            var e = new EventDef
            {
                id = "explorar", name = "Explorar a ilha", subtitle = "Sem relógio · MAPA para viajar · 24 km de ilha",
                kind = EventKind.Explore, start = w.start, gates = new WGate[0], finish = null, economy = false, botCount = 0,
            };
            e.BuildSequence();
            return e;
        }

        public bool Laps => kind == EventKind.Circuit;

        /// <summary>Route of the Expedition through the chosen variant of every section.</summary>
        public static Vector3[] ExpeditionRoute(WorldJson w, int[] variant) => ExpeditionRoute(w, variant, out _, out _);
        public static Vector3[] ExpeditionRoute(WorldJson w, int[] variant, out List<int> jumps) => ExpeditionRoute(w, variant, out jumps, out _);

        public static Vector3[] ExpeditionRoute(WorldJson w, int[] variant, out List<int> jumps, out List<float> halfWidths)
        {
            var route = new List<Vector3>();
            jumps = new List<int>();
            halfWidths = new List<float>();
            for (int s = 0; s < w.sections.Length; s++)
            {
                var vs = w.sections[s].variants;
                var v = vs[Mathf.Clamp(variant[s], 0, vs.Length - 1)];
                var pts = v.Points;
                int offset = route.Count == 0 ? 0 : route.Count - 1;
                foreach (int j in WVariant.JumpIndices(pts, v.jumps)) jumps.Add(offset + j);
                for (int i = route.Count == 0 ? 0 : 1; i < pts.Length; i++) { route.Add(pts[i]); halfWidths.Add(v.hw); }   // the 1st point repeats the gate
            }
            return route.ToArray();
        }

        /// <summary>Variant choice per section for a bot: risky pilots like short tunnels/heights, careful ones the ground road.</summary>
        public static int[] ChooseVariants(WorldJson w, BotPersona p, System.Random rng)
        {
            var pick = new int[w.sections.Length];
            for (int s = 0; s < w.sections.Length; s++)
            {
                var vs = w.sections[s].variants;
                float minLen = float.MaxValue;
                foreach (var v in vs) minLen = Mathf.Min(minLen, v.length);
                float best = float.MinValue;
                for (int i = 0; i < vs.Length; i++)
                {
                    var v = vs[i];
                    float shortness = (minLen / v.length - 0.85f) * 6f;        // shorter is better
                    float danger = v.level == 2 ? 1.6f : v.level == 0 ? 0.5f : v.level == 3 ? 0.4f : 0f;
                    float score = shortness * (0.5f + p.risk) - danger * (1f - p.risk) * 1.2f + (float)rng.NextDouble() * 0.9f;
                    if (score > best) { best = score; pick[s] = i; }
                }
            }
            return pick;
        }

        /// <summary>A circuit/drag route repeated for every lap.</summary>
        public Vector3[] LapsRoute() => LapsRoute(out _);

        public Vector3[] LapsRoute(out List<int> jumps)
        {
            jumps = new List<int>();
            if (lapRoute == null || lapRoute.Length == 0) return lapRoute;
            var lapJ = WVariant.JumpIndices(lapRoute, lapJumps);
            var r = new List<Vector3>(lapRoute.Length * Mathf.Max(1, laps));
            for (int lap = 0; lap < Mathf.Max(1, laps); lap++)
            {
                int offset = r.Count == 0 ? 0 : r.Count - 1;
                foreach (int j in lapJ) jumps.Add(offset + j);
                for (int i = lap == 0 ? 0 : 1; i < lapRoute.Length; i++) r.Add(lapRoute[i]);
            }
            return r.ToArray();
        }
    }
}
