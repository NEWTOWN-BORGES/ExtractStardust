using System.Collections.Generic;
using UnityEngine;

namespace Stardust
{
    public enum PilotState { Grid, Racing, Respawning, Finished, Destroyed, Stranded, Abandoned }
    public enum BotStyle { Aggressive, Technical, Conservative }

    /// <summary>Personality of an AI pilot: speed, line, risk taste (shortcuts) and how often it errs.</summary>
    public class BotPersona
    {
        public BotStyle style;
        public float skill;        // 0.6 rookie .. 1 ace
        public float aggression;   // nitro use, overtaking pressure
        public float risk;         // preference for short / dangerous variants
        public float lineOffset;   // preferred lateral line on the road

        public static BotPersona Make(BotStyle style, System.Random rng)
        {
            float R(float a, float b) => a + (float)rng.NextDouble() * (b - a);
            var p = new BotPersona { style = style };
            switch (style)
            {
                case BotStyle.Aggressive: p.skill = R(0.78f, 0.95f); p.aggression = R(0.7f, 1f); p.risk = R(0.6f, 1f); break;
                case BotStyle.Technical: p.skill = R(0.86f, 1f); p.aggression = R(0.4f, 0.7f); p.risk = R(0.3f, 0.7f); break;
                default: p.skill = R(0.7f, 0.9f); p.aggression = R(0.1f, 0.4f); p.risk = R(0f, 0.35f); break;
            }
            p.lineOffset = R(-9f, 9f);
            return p;
        }
    }

    public class Pilot
    {
        public string name = "Piloto";
        public string tag = "";
        public bool human;
        public int humanSlot = -1;
        public bool persistent;     // economy is persisted (player 1 only)
        public bool remote;         // another player on the LAN
        public ItemInst[] equip = new ItemInst[6];
        public string insuredId = "";
        public Consumable[] cons = { Consumable.RepairGel, Consumable.FuelCell };
        public int[] consCount = { 2, 2 };
        public Color livery = Color.cyan, livery2 = Color.white;
        public string model = "vespa";
        public BotPersona persona;
        public int number;
        public ItemInst Insured { get { foreach (var it in equip) if (it != null && it.id == insuredId) return it; return null; } }
    }

    /// <summary>Lightning strike announced on the ground before it hits (storm hazards).</summary>
    public class Strike
    {
        public Vector3 world;
        public float timer, age, radius = 12f;
        public bool fired;
    }

    public class PilotResult
    {
        public Racer racer;
        public int place;
        public string status;
        public bool extracted;
        public float time;
        public ItemInst insured;
        public bool insuranceUsed;
        public readonly List<ItemInst> lost = new List<ItemInst>();
        public readonly List<ItemInst> preserved = new List<ItemInst>();
        public readonly List<ItemInst> loot = new List<ItemInst>();
        public readonly List<string> medals = new List<string>();
        public int creditsPlace, creditsMedals, costInsurance, costConsumables, costRepair, net, xp;
        public int LootValue { get { int v = 0; foreach (var it in loot) v += it.value; return v; } }
    }

    public class RaceResult
    {
        public static readonly int[] PlaceCredits = { 1500, 1000, 750, 600, 550, 500, 450, 400, 350, 300, 250 };
        public string matchId;
        public string algorithm = "loot-v1: raridade > valor > id; 1ª ronda por classificação, resto por pesos 1/posição";
        public int poolValue;
        public bool economy = true;      // false in circuits / drag / explore (no losses, no loot)
        public readonly List<PilotResult> pilots = new List<PilotResult>();
        public readonly List<ItemInst> pool = new List<ItemInst>();
        public readonly List<ItemInst> residual = new List<ItemInst>();
        public List<string> grantedBase = new List<string>();
        public bool applied;

        public PilotResult For(Racer r)
        {
            foreach (var p in pilots) if (p.racer == r) return p;
            return null;
        }

        /// <summary>Builds the settlement: statuses, automatic pool distribution, credits, medals (GDD 11-12).</summary>
        public static RaceResult Settle(IslandRace race)
        {
            var res = new RaceResult { matchId = race.matchId, poolValue = race.poolValue, economy = race.def.economy };
            res.pool.AddRange(race.pool);
            var ext = new List<PilotResult>();
            foreach (var r in race.Ordered)
            {
                var pr = new PilotResult { racer = r, place = r.place, time = r.finishTime };
                pr.extracted = r.state == PilotState.Finished;
                pr.status = pr.extracted ? (race.def.economy ? "EXTRACTED" : "CHEGOU") : r.state == PilotState.Destroyed ? "EXTRACTION FAILED" : r.state == PilotState.Stranded ? "STRANDED" : "ABANDONED";
                pr.lost.AddRange(r.lost);
                pr.insured = r.pilot.Insured;
                pr.insuranceUsed = r.state == PilotState.Destroyed && pr.insured != null;
                foreach (var it in r.pilot.equip) if (it != null && !r.lost.Contains(it)) pr.preserved.Add(it);
                res.pilots.Add(pr);
                if (pr.extracted) ext.Add(pr);
            }
            ext.Sort((a, b) => a.time.CompareTo(b.time));

            // automatic pool distribution (GDD 11.4, proposed algorithm v1)
            var items = new List<ItemInst>(race.pool);
            items.Sort((a, b) =>
            {
                if (a.rarity != b.rarity) return b.rarity.CompareTo(a.rarity);
                if (a.value != b.value) return b.value.CompareTo(a.value);
                return string.CompareOrdinal(a.id, b.id);
            });
            if (ext.Count == 0) res.residual.AddRange(items);
            else
            {
                int idx = 0;
                foreach (var pr in ext) if (idx < items.Count) pr.loot.Add(items[idx++]);
                while (idx < items.Count)
                {
                    PilotResult best = null;
                    float bestScore = -1f;
                    for (int r = 0; r < ext.Count; r++)
                    {
                        float score = (1f / (r + 1)) / (1 + ext[r].loot.Count);
                        if (score > bestScore) { bestScore = score; best = ext[r]; }
                    }
                    best.loot.Add(items[idx++]);
                }
            }

            // credits, XP and medals (separate from the pool, GDD 12)
            float scale = race.def.rewardScale;
            foreach (var pr in res.pilots)
            {
                var r = pr.racer;
                if (pr.extracted)
                {
                    int i = pr.place - 1;
                    pr.creditsPlace = Mathf.RoundToInt((i < PlaceCredits.Length ? PlaceCredits[i] : 200) * scale);
                    pr.xp = Mathf.RoundToInt((150 + 12 * Mathf.Max(0, 17 - pr.place)) * scale);
                    void Medal(bool cond, string name, int cr) { if (cond) { pr.medals.Add(name); pr.creditsMedals += Mathf.RoundToInt(cr * scale); } }
                    Medal(!r.tookDamage, "Corrida perfeita", 750);
                    Medal(!r.usedRepair, "Mecânico de folga", 300);
                    Medal(!r.usedFuel, "Última gota", 350);
                    Medal(r.nitroUsedSeconds < 1f, "Energia pura", 400);
                    Medal(r.minIntegrity <= 10f, "Sobrevivente", 500);
                    Medal(pr.time < race.def.referenceTime, "Contra o relógio", 400);
                    Medal(r.drifts >= 25, "Rei da derrapagem", 300);
                    Medal(pr.place == 1 && !r.tookDamage && !r.usedRepair, "Vitória imaculada", 1500);
                    pr.creditsMedals = Mathf.Min(pr.creditsMedals, Mathf.RoundToInt(2000 * scale));
                    pr.costRepair = race.def.economy ? Mathf.RoundToInt((100f - r.integrity) * 3f) : 0;
                }
                else
                {
                    pr.xp = r.state == PilotState.Destroyed ? 60 + Mathf.RoundToInt(r.distance / 1000f * 5f) : 80;
                    pr.xp = Mathf.RoundToInt(pr.xp * scale);
                }
                pr.costConsumables = r.consumedCost;
                pr.costInsurance = race.def.economy && pr.insured != null ? Mathf.RoundToInt(pr.insured.value * 0.1f) : 0;
                pr.net = pr.creditsPlace + pr.creditsMedals - pr.costConsumables - pr.costInsurance - pr.costRepair;
            }
            return res;
        }

        /// <summary>Applies the confirmed settlement to the persistent save exactly once (idempotent by matchId).</summary>
        public void ApplyTo(SaveData save, Racer player)
        {
            if (applied || save == null || player == null) return;
            if (save.history.Exists(h => h.StartsWith(matchId))) { applied = true; return; }
            var pr = For(player);
            if (pr == null) return;
            foreach (var it in pr.lost)
            {
                save.inventory.RemoveAll(x => x.id == it.id);
                for (int i = 0; i < save.equipped.Count; i++) if (save.equipped[i] == it.id) save.equipped[i] = "";
            }
            foreach (var it in pr.loot)
            {
                if (save.inventory.Exists(x => x.id == it.id)) continue; // never duplicate an instance
                it.owner = "player";
                it.origin = $"Porquinho da expedição {matchId.Substring(0, 6)}";
                save.inventory.Add(it);
            }
            save.credits = Mathf.Max(0, save.credits + pr.net);
            save.xp += pr.xp;
            save.races++;
            if (pr.extracted && economy) save.extractions++;
            if (pr.extracted && pr.place == 1) save.wins++;
            if (pr.racer.state == PilotState.Destroyed) save.destroyed++;
            if (pr.extracted && economy && (save.bestTime <= 0f || pr.time < save.bestTime)) save.bestTime = pr.time;
            foreach (var m in pr.medals) if (!save.medals.Contains(m)) save.medals.Add(m);
            int granted = save.EnsureBaseKit();
            if (granted > 0) grantedBase.Add($"{granted} peça(s) padrão entregues pela proteção base");
            save.history.Insert(0, $"{matchId} | {pr.place}º | {pr.status} | {pr.net:+0;-0} CR | {pr.loot.Count} itens");
            if (save.history.Count > 30) save.history.RemoveAt(save.history.Count - 1);
            applied = true;
        }
    }
}
