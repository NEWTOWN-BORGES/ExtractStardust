using System.Collections.Generic;
using RedDust.AI;
using RedDust.Meta;
using RedDust.Track;
using RedDust.Vehicle;
using UnityEngine;

namespace RedDust.Game
{
    public enum Personality { Aggressive, Survivor, Technical, Speedster, Rookie }

    /// <summary>
    /// Piloto bot (Doc 01 §12.2): segue o grafo de rotas com a sua altura de linha (fundo/meio/alto das paredes),
    /// escolhe SAFE/SKILL conforme a personalidade e o casco, ultrapassa mudando de linha, gere boost, calor,
    /// combustível e reparações. Fica melhor por linhas, boost e decisões — nunca por velocidade escondida.
    /// </summary>
    public sealed class BotBrain
    {
        public readonly RouteFollower route;
        public readonly Personality personality;
        readonly float baseLane, baseMargin;
        readonly Rng rng;
        float laneOffset, offsetTimer, lateBrake, noiseSeed;

        public BotBrain(CourseGraph graph, Personality p, int difficulty, float lane, Rng rng)
        {
            personality = p;
            this.rng = rng;
            baseLane = lane;
            noiseSeed = rng.Range(0f, 1000f);
            float diff = difficulty == 0 ? 0.74f : difficulty == 1 ? 0.80f : 0.85f;
            baseMargin = Mathf.Min(0.9f, diff + p switch
            {
                Personality.Aggressive => 0.04f, Personality.Technical => 0.03f, Personality.Speedster => 0.01f,
                Personality.Survivor => -0.03f, _ => -0.06f,
            });
            route = new RouteFollower(graph);
            route.chooseBranch = Choose;
        }

        public static string Label(Personality p) => p switch
        {
            Personality.Aggressive => "Agressivo", Personality.Survivor => "Sobrevivente", Personality.Technical => "Técnico",
            Personality.Speedster => "Velocista", _ => "Novato",
        };

        Racer self;

        bool Choose(CoursePath b)
        {
            string id = (b.Id ?? "").ToUpperInvariant();
            bool skill = id.Contains("SKILL"), safe = id.Contains("SAFE");
            float hullFrac = self != null ? self.HullFrac : 1f;
            double p = personality switch
            {
                Personality.Technical => skill ? 0.85 : safe ? 0.1 : 0.5,
                Personality.Aggressive => skill ? 0.6 : safe ? 0.15 : 0.5,
                Personality.Speedster => skill ? 0.35 : safe ? 0.2 : 0.4,
                Personality.Survivor => skill ? 0.1 : safe ? 0.85 : 0.4,
                _ => 0.5,
            };
            if (safe && hullFrac < 0.4f) p = Mathf.Max((float)p, 0.8f);   // danificado: prefere a rota segura
            if (skill && hullFrac < 0.3f) p *= 0.3;
            return rng.Chance(p);
        }

        public void Reset(int path) => route.Reset(path, baseLane);

        public CraftInput Drive(Racer me, IList<Racer> all, float dt)
        {
            self = me;
            var line = route.line;
            line.cornerMargin = baseMargin + lateBrake;
            if (lateBrake > 0f) lateBrake = Mathf.Max(0f, lateBrake - dt * 0.1f);
            if (personality == Personality.Rookie && rng.Chance(0.04 * dt)) lateBrake = 0.12f;     // erro controlado: trava tarde

            // tráfego: rival lento à frente na mesma linha → mudar de altura/linha para ultrapassar
            offsetTimer -= dt;
            if (offsetTimer <= 0f) laneOffset = Mathf.MoveTowards(laneOffset, 0f, dt * 0.5f);
            Racer ahead = null; float best = 40f, aheadU = 0f;
            int st = Mathf.Max(0, route.Station);
            foreach (var o in all)
            {
                if (o == me || o.craft == null || !o.Active) continue;
                float d = o.raceDistance - me.raceDistance;
                if (d <= 2f || d >= best) continue;
                float ou = route.Data.LateralU(o.craft.Position, st);
                if (Mathf.Abs(ou - line.CurrentU) < 0.3f) { ahead = o; best = d; aheadU = ou; }
            }
            if (ahead != null && ahead.Speed < me.Speed + 3f && offsetTimer <= 0f)
            {
                float side = aheadU > line.CurrentU ? -1f : 1f;
                if (Mathf.Abs(baseLane + laneOffset + side * 0.35f) > 0.85f) side = -side;
                laneOffset += side * (personality == Personality.Aggressive ? 0.28f : 0.38f);
                laneOffset = Mathf.Clamp(laneOffset, -0.8f, 0.8f);
                offsetTimer = 2f;
            }
            line.laneU = Mathf.Clamp(baseLane + laneOffset, -0.85f, 0.85f);

            // boost: conforme personalidade, calor e combustível
            float heatLimit = personality == Personality.Survivor ? 55f : personality == Personality.Speedster || personality == Personality.Aggressive ? 88f : 75f;
            line.useBoost = personality == Personality.Rookie ? rng.Chance(0.3 * dt) : me.heat < heatLimit && me.fuel > 0.18f;

            // consumíveis: reparar, combustível, refrigeração, energia
            float repairAt = personality == Personality.Survivor ? 0.45f : personality == Personality.Aggressive ? 0.2f : 0.3f;
            for (int i = 0; i < me.slots.Count; i++)
            {
                var c = Catalog.Consumable(me.slots[i].id);
                if (c == null || me.slots[i].count <= 0) continue;
                bool want = c.kind switch
                {
                    ConsumableKind.Repair => me.HullFrac < repairAt,
                    ConsumableKind.Fuel => me.fuel < 0.12f,
                    ConsumableKind.Coolant => me.heat > 85f,
                    ConsumableKind.Surge => me.craft.Nitro < 0.2f && personality != Personality.Survivor,
                    _ => me.HullFrac < 0.5f && route.Data.Bank[Mathf.Clamp(route.Station, 0, route.Data.StationCount - 1)] > 30f,
                };
                if (want && me.Use(i) != null) break;
            }

            var input = route.Drive(me.craft, dt);
            if (personality == Personality.Rookie)
                input.steer = Mathf.Clamp(input.steer + (Mathf.PerlinNoise(noiseSeed, Time.time * 0.7f) - 0.5f) * 0.25f, -1f, 1f);
            return input;
        }
    }
}
