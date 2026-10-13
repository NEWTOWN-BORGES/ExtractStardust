using System;
using System.Collections.Generic;
using System.Linq;

namespace RedDust.Meta
{
    [Serializable]
    public class SlotEntry
    {
        public string socket;
        public string item;   // Instance ID ("" = peça de série do chassis)
    }

    [Serializable]
    public class BuildEntry
    {
        public string chassis;
        public List<SlotEntry> slots = new List<SlotEntry>();
    }

    [Serializable]
    public class LedgerEntry
    {
        public long ticks;
        public string kind;    // source/sink: corrida, proeza, contrato, consumivel, componente, cache, venda, pool
        public long amount;
        public string note;
    }

    [Serializable]
    public class ContractState
    {
        public string id;
        public int progress;
        public int completed;
    }

    /// <summary>Linha do relatório de uma expedição (o que levei / perdi / ganhei).</summary>
    [Serializable]
    public class ReportLine
    {
        public string text;
        public Rarity rarity;
        public long value;
        public ReportLine() { }
        public ReportLine(string text, Rarity rarity = Rarity.Common, long value = 0) { this.text = text; this.rarity = rarity; this.value = value; }
    }

    [Serializable]
    public class RaceReport
    {
        public string raceId, course, mode, chassis;
        public RaceState state;
        public int position, racers;
        public float time, hull, fuel;
        public string insured = "";
        public List<ReportLine> carried = new List<ReportLine>();
        public List<ReportLine> lost = new List<ReportLine>();
        public List<ReportLine> gained = new List<ReportLine>();
        public List<ReportLine> stardust = new List<ReportLine>();
        public long stardustTotal;
        public long poolValue;
    }

    /// <summary>
    /// Perfil persistente de um piloto (carteira, garagem, mochila, consumíveis, contratos, último relatório).
    /// Serializável pelo JsonUtility (campos públicos, listas; sem dicionários).
    /// </summary>
    [Serializable]
    public class PlayerProfile
    {
        public int version = 1;
        public string slot = "p1";
        public string name = "Piloto";
        public long stardust = Economy.StartingStardust;
        public int cacheStd, cacheAdv, cacheElite;                              // caixas guardadas no Cofre (por abrir)
        public int Caches(CacheKind k) => k == CacheKind.Standard ? cacheStd : k == CacheKind.Advanced ? cacheAdv : k == CacheKind.Elite ? cacheElite : 0;
        public int CachesTotal => cacheStd + cacheAdv + cacheElite;
        public void AddCaches(CacheKind k, int n)
        {
            if (k == CacheKind.Standard) cacheStd = Math.Max(0, cacheStd + n);
            else if (k == CacheKind.Advanced) cacheAdv = Math.Max(0, cacheAdv + n);
            else if (k == CacheKind.Elite) cacheElite = Math.Max(0, cacheElite + n);
        }
        public bool firstExtractionPaid;
        public string chassis = "strix";
        public List<BuildEntry> builds = new List<BuildEntry>();
        public List<EquipmentInstance> items = new List<EquipmentInstance>();
        public List<ConsumableStack> stock = new List<ConsumableStack>();      // consumíveis guardados (seguros)
        public List<ConsumableStack> loadout = new List<ConsumableStack>();    // levados para a corrida (3 slots)
        public string insured = "";
        public List<string> applied = new List<string>();                      // transações já aplicadas (idempotência)
        public List<LedgerEntry> ledger = new List<LedgerEntry>();
        public List<ContractState> contracts = new List<ContractState>();
        public int races, extractions, streak, noRepairStreak, nextSerial = 1, shopRotation;
        public RaceReport last;

        public EquipmentInstance Item(string id) => string.IsNullOrEmpty(id) ? null : items.Find(i => i.id == id);

        public BuildEntry Build(string chassisId)
        {
            var b = builds.Find(x => x.chassis == chassisId);
            if (b == null) { b = new BuildEntry { chassis = chassisId }; builds.Add(b); }
            var def = Catalog.ChassisOf(chassisId);
            foreach (var s in def.sockets)
                if (!b.slots.Exists(e => e.socket == s.id)) b.slots.Add(new SlotEntry { socket = s.id, item = "" });
            return b;
        }

        public BuildEntry Current => Build(chassis);

        /// <summary>Componentes equipados na nave atual (os que vão para a corrida e ficam em risco).</summary>
        public List<EquipmentInstance> Equipped()
        {
            var list = new List<EquipmentInstance>();
            foreach (var s in Current.slots) { var it = Item(s.item); if (it != null) list.Add(it); }
            return list;
        }

        public bool IsEquippedAnywhere(string itemId) => builds.Any(b => b.slots.Any(s => s.item == itemId));

        public int StockCount(string consId) => stock.Where(s => s.id == consId).Sum(s => s.count);
        public int LoadoutCount(string consId) => loadout.Where(s => s.id == consId).Sum(s => s.count);
        public long BuildValue => Equipped().Sum(i => (long)i.value);
        public long ValueAtRisk => Equipped().Where(i => i.id != insured).Sum(i => (long)i.value);
    }
}
