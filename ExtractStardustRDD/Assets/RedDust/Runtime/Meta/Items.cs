using System;
using System.Collections.Generic;
using System.Linq;

namespace RedDust.Meta
{
    [Serializable]
    public class StatRoll
    {
        public Stat stat;
        public int value;
        public StatRoll() { }
        public StatRoll(Stat s, int v) { stat = s; value = v; }
    }

    /// <summary>
    /// Instância persistente de um componente (Doc 03 §9): identidade única, rolls próprios e dono.
    /// Ao mudar de dono pelo Expedition Pool é a MESMA instância (mesmo id, serial, rolls e perk) — nunca uma cópia.
    /// </summary>
    [Serializable]
    public class EquipmentInstance
    {
        public string id;          // Instance ID
        public string def;         // Definition ID
        public Rarity rarity;
        public List<StatRoll> rolls = new List<StatRoll>();
        public string perk = "";
        public string drawback = "";
        public string owner = "";
        public bool insured;
        public string source = ""; // cache, loja, inicial, pool, bot
        public string serial = ""; // obrigatório nos lendários
        public int value;          // avaliação (✦), separada do poder

        public EquipmentDef Def => Catalog.Def(def);
        public string Name => Def != null ? Def.name : def;
        public string Label => string.IsNullOrEmpty(serial) ? Name : $"{Name} #{serial}";
        public int Roll(Stat s) { int v = 0; foreach (var r in rolls) if (r.stat == s) v += r.value; return v; }
        public int SellValue => Math.Max(10, (int)Math.Round(value * Economy.SellFraction / 10.0) * 10);

        public string RollText()
        {
            var parts = rolls.Where(r => r.value != 0).OrderByDescending(r => r.value)
                .Select(r => $"{(r.value > 0 ? "+" : "")}{r.value} {StatInfo.Short(r.stat)}");
            return string.Join("  ", parts);
        }
    }

    [Serializable]
    public class ConsumableStack
    {
        public string id;
        public int count;
        public ConsumableStack() { }
        public ConsumableStack(string id, int count) { this.id = id; this.count = count; }
    }

    /// <summary>
    /// Criação de instâncias: gasta o stat budget da raridade nos stats permitidos da família (com caps por item);
    /// ganhos extremos podem trazer um drawback que devolve budget (custo 1:1, TARGET). Só a autoridade cria itens.
    /// </summary>
    public static class ItemFactory
    {
        public static EquipmentInstance Create(EquipmentDef def, Rarity rarity, Rng rng, string source, string owner, Func<string, string> serialFor = null)
        {
            if (def.legendary) rarity = Rarity.Legendary;
            else if (rarity > Rarity.Epic) rarity = Rarity.Epic;
            var it = new EquipmentInstance { id = NewId(rng), def = def.id, rarity = rarity, source = source, owner = owner };
            if (def.legendary)
            {
                // rolls controlados: pequena variação (±1) mantendo a identidade da peça
                foreach (var r in def.fixedRolls) it.rolls.Add(new StatRoll(r.stat, r.value + (r.value > 0 ? rng.Range(-1, 2) : 0)));
                it.perk = def.perk;
                it.drawback = def.perkText;
                it.serial = serialFor != null ? serialFor(def.serialPrefix) : $"{def.serialPrefix}-{rng.Range(1, 9999):0000}";
            }
            else RollBudget(def, rarity, rng, it);
            it.value = Valuate(it, rng);
            return it;
        }

        static void RollBudget(EquipmentDef def, Rarity rarity, Rng rng, EquipmentInstance it)
        {
            int budget = RarityInfo.Budget[(int)rarity];
            var got = new Dictionary<Stat, int>();
            // drawback: mais provável nas raridades altas (especialização com custo); devolve budget
            double pDraw = rarity switch { Rarity.Common => 0.0, Rarity.Uncommon => 0.15, Rarity.Rare => 0.35, _ => 0.6 };
            if (def.drawbacks.Length > 0 && rng.Chance(pDraw))
            {
                var d = def.drawbacks[rng.Range(0, def.drawbacks.Length)];
                int pay = rng.Range(2, d.cap + 1);
                got[d.stat] = -pay;
                budget += pay;
                it.drawback = $"-{pay} {StatInfo.Name(d.stat)}";
            }
            var rules = def.stats;
            var weights = new List<double>();
            for (int k = 0; k < budget; k++)
            {
                weights.Clear();
                foreach (var r in rules)
                {
                    got.TryGetValue(r.stat, out int cur);
                    weights.Add(cur >= r.cap ? 0 : r.weight);
                }
                if (weights.Sum() <= 0) break;                                    // caps da família esgotados: o resto perde-se
                var pick = rules[rng.Weighted(weights)];
                got.TryGetValue(pick.stat, out int c0);
                got[pick.stat] = c0 + 1;
            }
            foreach (var kv in got.OrderBy(k => (int)k.Key)) it.rolls.Add(new StatRoll(kv.Key, kv.Value));
            it.rolls.Add(new StatRoll(Stat.Mass, (int)Math.Round(def.massKg * (1.0 + rng.Range(-0.1f, 0.1f)))));
        }

        /// <summary>Avaliação ✦: média da raridade (Doc 03 §10) × qualidade dos rolls (0,9..1,15). Lendários dependem do serial.</summary>
        static int Valuate(EquipmentInstance it, Rng rng)
        {
            double avg = RarityInfo.AvgValue[(int)it.rarity];
            if (it.rarity == Rarity.Legendary) return (int)Math.Round(avg * rng.Range(1.0f, 1.25f) / 100.0) * 100;
            int budget = RarityInfo.Budget[(int)it.rarity];
            int spent = it.rolls.Where(r => r.stat != Stat.Mass && r.value > 0).Sum(r => r.value);
            double q = Math.Min(1.0, spent / (double)Math.Max(1, budget));
            return (int)Math.Round(avg * (0.9 + 0.25 * q) * rng.Range(0.95f, 1.05f) / 10.0) * 10;
        }

        public static string NewId(Rng rng) => $"{rng.NextU():x16}";
    }
}
