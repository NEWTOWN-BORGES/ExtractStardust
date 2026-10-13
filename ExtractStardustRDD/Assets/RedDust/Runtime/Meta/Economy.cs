using System;
using System.Collections.Generic;
using System.Linq;

namespace RedDust.Meta
{
    /// <summary>Combina chassis + módulos em stats finais sem alterar as definições (Doc 02 §12).</summary>
    public static class StatResolver
    {
        public static ShipStats Resolve(ChassisDef c, IEnumerable<EquipmentInstance> equipped)
        {
            var s = new ShipStats { BaseMassKg = c.massKg };
            for (int i = 0; i < StatInfo.CoreCount; i++) s.v[i] = c.stats[i];
            foreach (var it in equipped)
            {
                if (it == null) continue;
                foreach (var r in it.rolls) s.v[(int)r.stat] += r.value;
                if (!string.IsNullOrEmpty(it.perk) && !s.Perks.Contains(it.perk)) s.Perks.Add(it.perk);
            }
            for (int i = 0; i < StatInfo.CoreCount; i++) s.v[i] = Math.Max(0f, Math.Min(100f, s.v[i]));
            return s;
        }

        public static ShipStats Resolve(PlayerProfile p) => Resolve(Catalog.ChassisOf(p.chassis), p.Equipped());
    }

    /// <summary>Rejeita builds ilegais: família/tamanho errados, peça repetida, peça que não é do piloto (Doc 02 §12).</summary>
    public static class BuildValidator
    {
        public static string CanEquip(PlayerProfile p, string chassisId, string socketId, EquipmentInstance it)
        {
            var c = Catalog.ChassisOf(chassisId);
            var sock = c.Socket(socketId);
            if (sock == null) return "Socket inexistente neste chassis.";
            if (it == null) return null;   // esvaziar o socket (peça de série)
            if (p.Item(it.id) == null) return "Esta peça não está na tua garagem.";
            var d = it.Def;
            if (d == null) return "Definição desconhecida.";
            if (d.family != sock.family) return $"{d.name} é {d.family}; este socket aceita {sock.family}.";
            if (!sock.Accepts(d)) return $"Classe {d.size} não encaixa no {c.name} (aceita {string.Join("/", sock.sizes)}).";
            return null;
        }

        public static List<string> Validate(PlayerProfile p, string chassisId)
        {
            var errors = new List<string>();
            var b = p.Build(chassisId);
            var seen = new HashSet<string>();
            foreach (var s in b.slots)
            {
                if (string.IsNullOrEmpty(s.item)) continue;
                if (!seen.Add(s.item)) { errors.Add($"{s.socket}: peça duplicada"); continue; }
                string e = CanEquip(p, chassisId, s.socket, p.Item(s.item));
                if (e != null) errors.Add($"{s.socket}: {e}");
            }
            return errors;
        }
    }

    /// <summary>Peças perdidas na destruição (decisão D7/C8): até 3 componentes não segurados, sorteados com peso pelo valor.</summary>
    public static class LossRules
    {
        public const int MaxLost = 3;

        public static List<EquipmentInstance> SelectLosses(IList<EquipmentInstance> carried, string insuredId, Rng rng, int max = MaxLost)
        {
            var pool = carried.Where(i => i != null && i.id != insuredId).ToList();
            var lost = new List<EquipmentInstance>();
            while (lost.Count < max && pool.Count > 0)
            {
                int k = rng.Weighted(pool.Select(i => (double)Math.Max(1, i.value)).ToList());
                lost.Add(pool[k]);
                pool.RemoveAt(k);
            }
            return lost;
        }
    }

    /// <summary>
    /// Expedition Pool (Doc 03 §10, prompt §37/§39): só recebe instâncias reais perdidas por quem foi destruído.
    /// Nunca cria nem duplica itens; o valor mostrado é avaliação, não moeda. No fim distribui por posição.
    /// </summary>
    public sealed class ExpeditionPool
    {
        public sealed class Entry { public EquipmentInstance item; public string from; }
        readonly List<Entry> entries = new List<Entry>();
        public IReadOnlyList<Entry> Entries => entries;
        public long Valuation => entries.Sum(e => (long)e.item.value);
        public int Count => entries.Count;

        public bool Add(EquipmentInstance it, string fromRacer)
        {
            if (it == null || entries.Any(e => e.item.id == it.id)) return false;
            entries.Add(new Entry { item = it, from = fromRacer });
            return true;
        }

        /// <summary>
        /// Distribuição automática em serpentina por valor: 1.º recebe a peça mais valiosa, 2.º a seguinte…; na ronda
        /// seguinte a ordem inverte-se. Só recebem os EXTRACTED (ordenados por posição). Itens acabam → acabou.
        /// </summary>
        public Dictionary<string, List<EquipmentInstance>> Distribute(IList<string> extractedByPosition)
        {
            var result = new Dictionary<string, List<EquipmentInstance>>();
            foreach (var r in extractedByPosition) result[r] = new List<EquipmentInstance>();
            if (extractedByPosition.Count == 0) return result;
            var sorted = entries.OrderByDescending(e => e.item.value).Select(e => e.item).ToList();
            int n = extractedByPosition.Count;
            for (int k = 0; k < sorted.Count; k++)
            {
                int round = k / n, idx = k % n;
                if (round % 2 == 1) idx = n - 1 - idx;
                result[extractedByPosition[idx]].Add(sorted[k]);
            }
            return result;
        }
    }

    /// <summary>Resultado de uma corrida enviado à autoridade (num jogo online, validado pelo servidor).</summary>
    public sealed class RaceOutcome
    {
        public string raceId, course;
        public GameMode mode;
        public RaceState state;
        public int position, racers;
        public float time, referenceTime, referenceMinutes;
        public float hullFrac, fuelFrac;
        public bool tookDamage, usedBoost, allCheckpoints;
        public int repairs, penalties, skillRoutes;
        public List<ConsumableStack> consumed = new List<ConsumableStack>();
        public List<string> lostItemIds = new List<string>();
        public List<EquipmentInstance> gained = new List<EquipmentInstance>();
        public long poolValue;
    }

    public enum CacheKind { Standard, Advanced, Elite, Prototype }

    public sealed class CacheResult
    {
        public CacheKind kind;
        public List<EquipmentInstance> components = new List<EquipmentInstance>();
        public List<string> consumables = new List<string>();
        public string error;
    }

    /// <summary>
    /// Autoridade económica LOCAL da demo (decisão C9): carteira ✦, loja, caixas, venda, seguro, consumíveis, resultados
    /// e contratos, com idempotência por id de transação e ledger. Um servidor real substitui esta classe sem mudar o jogo.
    /// </summary>
    public static class Economy
    {
        public const long StartingStardust = 1000;
        public const long FirstExtractionBonus = 500;
        public const long ExtractedBonus = 250;
        public const long ProwessCap = 500;
        public const double SellFraction = 0.25;
        public const int LoadoutSlots = 3, UnitsPerSlot = 2;

        public static readonly int[] PositionReward = { 1600, 1300, 1100, 950, 850, 750, 675, 600, 550, 500, 450, 425, 400, 375, 350, 325, 300, 275, 250, 225 };

        public static int CachePrice(CacheKind k) => k switch { CacheKind.Standard => 2500, CacheKind.Advanced => 6000, CacheKind.Elite => 13500, _ => 0 };
        public static string CacheName(CacheKind k) => k switch { CacheKind.Standard => "STANDARD CACHE", CacheKind.Advanced => "ADVANCED CACHE", CacheKind.Elite => "ELITE CACHE", _ => "PROTOTYPE CACHE" };

        /// <summary>Multiplicador por duração de referência da pista (Doc 03 §5): corridas curtas não podem ser a melhor farm.</summary>
        public static double DurationMultiplier(float minutes) => minutes < 6f ? 0.35 : minutes < 10f ? 0.50 : minutes < 17f ? 0.70 : 1.00;

        // ------------------------------------------------------------------ perfil

        public static PlayerProfile NewProfile(string slot, string name, ulong seed)
        {
            var rng = new Rng(seed);
            var p = new PlayerProfile { slot = slot, name = name };
            void Give(string defId, string socket)
            {
                var it = ItemFactory.Create(Catalog.Def(defId), Rarity.Common, rng, "inicial", slot);
                p.items.Add(it);
                p.Build("strix").slots.Find(s => s.socket == socket).item = it.id;
            }
            Give("eng_vk4", "Engine");
            Give("wing_long", "Wings");
            Give("arm_guard", "Armor");
            Give("cool_radiator", "Cooling");
            p.insured = p.Equipped()[0].id;
            p.stock.Add(new ConsumableStack("foam", 2));
            p.stock.Add(new ConsumableStack("fuel", 1));
            p.stock.Add(new ConsumableStack("coolant", 1));
            p.loadout.Add(new ConsumableStack("foam", 1));
            p.loadout.Add(new ConsumableStack("fuel", 1));
            InitContracts(p);
            Log(p, "inicial", StartingStardust, "Saldo inicial da demo");
            return p;
        }

        public const long WelcomeBonus = 25000;

        /// <summary>
        /// Kit de boas-vindas generoso (pedido do jogador): ✦ extra, STRIX completa com peças Incomuns/Raras nos sockets
        /// vazios, peças extra para experimentar builds e consumíveis de todos os tipos. Idempotente: aplica-se uma vez a
        /// cada perfil, novo ou antigo.
        /// </summary>
        public static bool GrantWelcomeKit(PlayerProfile p, ulong seed)
        {
            if (AlreadyApplied(p, "kit:welcome_v2")) return false;
            var rng = new Rng(seed ^ 0x5EED5EEDUL);
            p.stardust += WelcomeBonus;
            Log(p, "bonus", WelcomeBonus, "Kit de boas-vindas");
            EquipmentInstance Add(string id, Rarity r)
            {
                var def = Catalog.Def(id);
                if (def == null) return null;
                var it = ItemFactory.Create(def, r, rng, "kit", p.slot);
                p.items.Add(it);
                return it;
            }
            var b = p.Build("strix");
            foreach (var (id, sock, r) in new[] { ("prop_vector", "Propulsion", Rarity.Rare), ("rea_steady", "Reactor", Rarity.Rare),
                                                  ("tail_twin", "Tail", Rarity.Uncommon), ("util_scanner", "Utility", Rarity.Uncommon) })
            {
                var it = Add(id, r);
                var s = b?.slots.Find(x => x.socket == sock);
                if (it != null && s != null && string.IsNullOrEmpty(s.item)) s.item = it.id;
            }
            foreach (var (id, r) in new[] { ("eng_hx", Rarity.Rare), ("eng_ironcore", Rarity.Uncommon), ("prop_twin", Rarity.Uncommon), ("prop_heavy", Rarity.Uncommon),
                                            ("wing_blade", Rarity.Rare), ("wing_brace", Rarity.Uncommon), ("arm_plate", Rarity.Uncommon), ("arm_skin", Rarity.Rare),
                                            ("rea_flux", Rarity.Rare), ("cool_vent", Rarity.Uncommon), ("tail_compact", Rarity.Uncommon), ("util_drone", Rarity.Uncommon) })
                Add(id, r);
            foreach (var (id, n) in new[] { ("foam", 6), ("fuel", 5), ("coolant", 5), ("stab", 3), ("surge", 3), ("nanogel", 2) })
                AddStock(p, id, n);
            p.AddCaches(CacheKind.Standard, 2);
            p.AddCaches(CacheKind.Advanced, 1);
            return true;
        }

        /// <summary>Repara perfis antigos ou editados: listas nulas, peças inexistentes, loadout acima do stock.</summary>
        public static void Sanitize(PlayerProfile p)
        {
            p.items ??= new List<EquipmentInstance>(); p.builds ??= new List<BuildEntry>(); p.stock ??= new List<ConsumableStack>();
            p.loadout ??= new List<ConsumableStack>(); p.applied ??= new List<string>(); p.ledger ??= new List<LedgerEntry>();
            p.contracts ??= new List<ContractState>();
            p.cacheStd = Math.Max(0, p.cacheStd); p.cacheAdv = Math.Max(0, p.cacheAdv); p.cacheElite = Math.Max(0, p.cacheElite);
            p.items.RemoveAll(i => i == null || Catalog.Def(i.def) == null);
            foreach (var b in p.builds) foreach (var s in b.slots) if (p.Item(s.item) == null) s.item = "";
            if (p.Item(p.insured) == null) p.insured = "";
            ClampLoadout(p);
            InitContracts(p);
            p.Build(p.chassis);
        }

        static void InitContracts(PlayerProfile p)
        {
            foreach (var c in Contracts) if (!p.contracts.Exists(x => x.id == c.id)) p.contracts.Add(new ContractState { id = c.id });
        }

        static void Log(PlayerProfile p, string kind, long amount, string note)
        {
            p.ledger.Add(new LedgerEntry { ticks = DateTime.UtcNow.Ticks, kind = kind, amount = amount, note = note });
            if (p.ledger.Count > 400) p.ledger.RemoveRange(0, p.ledger.Count - 400);
        }

        static bool AlreadyApplied(PlayerProfile p, string txId)
        {
            if (string.IsNullOrEmpty(txId)) return false;
            if (p.applied.Contains(txId)) return true;
            p.applied.Add(txId);
            if (p.applied.Count > 300) p.applied.RemoveRange(0, p.applied.Count - 300);
            return false;
        }

        // ------------------------------------------------------------------ garagem

        public static string Equip(PlayerProfile p, string chassisId, string socketId, EquipmentInstance it)
        {
            string err = BuildValidator.CanEquip(p, chassisId, socketId, it);
            if (err != null) return err;
            var b = p.Build(chassisId);
            // a mesma instância só pode estar montada num sítio: sai de qualquer outro socket/nave
            if (it != null) foreach (var bb in p.builds) foreach (var s in bb.slots) if (s.item == it.id) s.item = "";
            b.slots.Find(s => s.socket == socketId).item = it != null ? it.id : "";
            if (!p.Equipped().Exists(i => i.id == p.insured)) p.insured = "";
            return null;
        }

        /// <summary>Seguro: exatamente 1 peça equipada (Doc 01 §10.1). Volta à garagem se a nave for destruída.</summary>
        public static string SetInsured(PlayerProfile p, string itemId)
        {
            if (!string.IsNullOrEmpty(itemId) && !p.Equipped().Exists(i => i.id == itemId)) return "Só podes segurar uma peça montada na nave.";
            p.insured = itemId ?? "";
            foreach (var i in p.items) i.insured = i.id == p.insured;
            return null;
        }

        /// <summary>Muda a quantidade levada de um consumível (3 slots, até 2 unidades por slot, limitado ao stock).</summary>
        public static string SetLoadout(PlayerProfile p, int slot, string consId, int count)
        {
            while (p.loadout.Count < LoadoutSlots) p.loadout.Add(new ConsumableStack("", 0));
            if (slot < 0 || slot >= LoadoutSlots) return "Slot inválido.";
            count = Math.Max(0, Math.Min(UnitsPerSlot, count));
            int others = p.loadout.Where((s, i) => i != slot && s.id == consId).Sum(s => s.count);
            if (!string.IsNullOrEmpty(consId)) count = Math.Min(count, Math.Max(0, p.StockCount(consId) - others));
            p.loadout[slot] = new ConsumableStack(count > 0 ? consId : "", count);
            return null;
        }

        static void ClampLoadout(PlayerProfile p)
        {
            var used = new Dictionary<string, int>();
            foreach (var s in p.loadout)
            {
                if (string.IsNullOrEmpty(s.id)) { s.count = 0; continue; }
                used.TryGetValue(s.id, out int u);
                s.count = Math.Max(0, Math.Min(Math.Min(UnitsPerSlot, s.count), p.StockCount(s.id) - u));
                used[s.id] = u + s.count;
                if (s.count == 0) s.id = "";
            }
        }

        static void AddStock(PlayerProfile p, string id, int n)
        {
            var s = p.stock.Find(x => x.id == id);
            if (s == null) p.stock.Add(new ConsumableStack(id, n)); else s.count += n;
        }

        static void TakeStock(PlayerProfile p, string id, int n)
        {
            var s = p.stock.Find(x => x.id == id);
            if (s == null) return;
            s.count = Math.Max(0, s.count - n);
            if (s.count == 0) p.stock.Remove(s);
        }

        // ------------------------------------------------------------------ loja e caixas

        public static string BuyConsumable(PlayerProfile p, string consId, string txId = null)
        {
            var c = Catalog.Consumable(consId);
            if (c == null) return "Consumível desconhecido.";
            if (p.stardust < c.price) return "Stardust insuficiente.";
            if (AlreadyApplied(p, txId)) return null;
            p.stardust -= c.price;
            AddStock(p, consId, 1);
            Log(p, "consumivel", -c.price, c.name);
            return null;
        }

        /// <summary>Preço de loja de um componente: avaliação limitada às faixas do Doc 03 §7.</summary>
        public static int ShopPrice(EquipmentInstance it) => it.rarity switch
        {
            Rarity.Common => Clamp10(it.value, 450, 650),
            Rarity.Uncommon => Clamp10(it.value, 900, 1300),
            Rarity.Rare => Clamp10(it.value, 2400, 3500),
            _ => int.MaxValue,
        };

        static int Clamp10(int v, int a, int b) => (int)Math.Round(Math.Max(a, Math.Min(b, v)) / 10.0) * 10;

        /// <summary>Rotação da loja (muda depois de cada corrida): 3 comuns, 2 incomuns, 1 raro. Epic/Legendary nunca.</summary>
        public static List<EquipmentInstance> ShopOffers(PlayerProfile p)
        {
            ulong seed = 0xC0FFEE ^ (ulong)(p.shopRotation + 1) * 0x9E3779B97F4A7C15UL ^ StableHash(p.slot);
            var rng = new Rng(seed);
            var defs = Catalog.Regular.ToList();
            var list = new List<EquipmentInstance>();
            foreach (var r in new[] { Rarity.Common, Rarity.Common, Rarity.Common, Rarity.Uncommon, Rarity.Uncommon, Rarity.Rare })
                list.Add(ItemFactory.Create(rng.Pick(defs), r, rng, "loja", ""));
            return list.Where(o => p.Item(o.id) == null && !p.applied.Contains("shop:" + o.id)).ToList();
        }

        /// <summary>Hash estável entre plataformas (o string.GetHashCode do .NET muda de processo para processo).</summary>
        public static ulong StableHash(string s)
        {
            ulong h = 1469598103934665603UL;
            foreach (char c in s ?? "") { h ^= c; h *= 1099511628211UL; }
            return h;
        }

        public static string BuyComponent(PlayerProfile p, EquipmentInstance offer)
        {
            if (offer == null || offer.rarity >= Rarity.Epic) return "Não está à venda.";
            if (p.Item(offer.id) != null || p.applied.Contains("shop:" + offer.id)) return null;   // idempotente: já comprado
            int price = ShopPrice(offer);
            if (p.stardust < price) return "Stardust insuficiente.";
            AlreadyApplied(p, "shop:" + offer.id);
            p.stardust -= price;
            offer.owner = p.slot;
            p.items.Add(offer);
            Log(p, "componente", -price, offer.Name);
            return null;
        }

        public static string Sell(PlayerProfile p, string itemId)
        {
            var it = p.Item(itemId);
            if (it == null) return "Peça inexistente.";
            if (p.IsEquippedAnywhere(itemId)) return "Desmonta a peça antes de a vender.";
            p.items.Remove(it);
            p.stardust += it.SellValue;
            Log(p, "venda", it.SellValue, it.Label);
            return null;
        }

        /// <summary>
        /// Supply Cache: exatamente 10 itens (4-6 componentes + consumíveis), famílias variadas, nunca chassis.
        /// Garantias: Advanced ≥1 Rare; Elite 1 Epic + ≥4 Rare+ e UM roll de 4% de Lendário por caixa (Doc 03 §8).
        /// </summary>
        public static CacheResult OpenCache(PlayerProfile p, CacheKind kind, string txId, Rng rng)
        {
            var res = new CacheResult { kind = kind };
            int price = CachePrice(kind);
            if (kind != CacheKind.Prototype && p.stardust < price) { res.error = "Stardust insuficiente."; return res; }
            if (AlreadyApplied(p, txId)) { res.error = "Esta caixa já foi aberta."; return res; }
            p.stardust -= price;
            Log(p, "cache", -price, CacheName(kind));
            Roll(kind, rng, res, prefix => $"{prefix}-{p.nextSerial++:0000}", p.slot);
            foreach (var it in res.components) p.items.Add(it);
            foreach (var c in res.consumables) AddStock(p, c, 1);
            return res;
        }

        /// <summary>Compra uma caixa e guarda-a no Cofre (abre-se lá, quando o jogador quiser). Idempotente por txId.</summary>
        public static string BuyCache(PlayerProfile p, CacheKind kind, string txId)
        {
            int price = CachePrice(kind);
            if (price <= 0) return "Caixa indisponível.";
            if (!string.IsNullOrEmpty(txId) && p.applied.Contains(txId)) return null;   // idempotente: já comprada
            if (p.stardust < price) return "Stardust insuficiente.";
            AlreadyApplied(p, txId);
            p.stardust -= price;
            Log(p, "cache", -price, CacheName(kind) + " → Cofre");
            p.AddCaches(kind, 1);
            return null;
        }

        /// <summary>Abre uma caixa guardada no Cofre: os 10 itens vão para o inventário.</summary>
        public static CacheResult OpenStoredCache(PlayerProfile p, CacheKind kind, string txId, Rng rng)
        {
            var res = new CacheResult { kind = kind };
            if (p.Caches(kind) <= 0) { res.error = "Não tens caixas deste tipo no Cofre."; return res; }
            if (AlreadyApplied(p, txId)) { res.error = "Esta caixa já foi aberta."; return res; }
            p.AddCaches(kind, -1);
            Roll(kind, rng, res, prefix => $"{prefix}-{p.nextSerial++:0000}", p.slot);
            foreach (var it in res.components) p.items.Add(it);
            foreach (var c in res.consumables) AddStock(p, c, 1);
            return res;
        }

        /// <summary>Rolagem pura de uma caixa (sem carteira): usada pela abertura e pelos testes de probabilidade.</summary>
        public static void Roll(CacheKind kind, Rng rng, CacheResult res, Func<string, string> serialFor, string owner)
        {
            double[] odds = kind switch
            {
                CacheKind.Standard => new[] { 0.70, 0.27, 0.03, 0.0 },
                CacheKind.Advanced => new[] { 0.20, 0.50, 0.27, 0.03 },
                CacheKind.Elite => new[] { 0.0, 0.25, 0.55, 0.20 },
                _ => new[] { 0.0, 0.15, 0.55, 0.30 },
            };
            int comps = kind == CacheKind.Elite ? rng.Range(5, 7) : rng.Range(4, 7);
            var families = Enum.GetValues(typeof(Family)).Cast<Family>().ToList();
            rng.Shuffle(families);
            var rarities = new List<Rarity>();
            for (int k = 0; k < comps; k++) rarities.Add((Rarity)rng.Weighted(odds));
            if (kind == CacheKind.Advanced && !rarities.Any(r => r >= Rarity.Rare)) rarities[0] = Rarity.Rare;
            if (kind == CacheKind.Elite)
            {
                rarities.Sort();
                if (!rarities.Any(r => r == Rarity.Epic)) rarities[rarities.Count - 1] = Rarity.Epic;
                for (int k = 0; k < rarities.Count && rarities.Count(r => r >= Rarity.Rare) < 4; k++)
                    if (rarities[k] < Rarity.Rare) rarities[k] = Rarity.Rare;
            }
            for (int k = 0; k < comps; k++)
            {
                var fam = families[k % families.Count];
                var defs = Catalog.Regular.Where(d => d.family == fam).ToList();
                res.components.Add(ItemFactory.Create(rng.Pick(defs), rarities[k], rng, "cache", owner));
            }
            double legendary = kind == CacheKind.Elite ? 0.04 : kind == CacheKind.Prototype ? 0.10 : 0.0;
            if (legendary > 0 && rng.Chance(legendary))
            {
                // um slot sobe a Lendário: de preferência um componente da mesma família de um lendário (mantém a variedade)
                var legs = Catalog.Legendaries.ToList();
                var same = legs.Where(l => res.components.Any(c => c.Def.family == l.family)).ToList();
                var leg = rng.Pick(same.Count > 0 ? same : legs);
                int slot = res.components.FindIndex(c => c.Def.family == leg.family);
                if (slot < 0)
                {
                    slot = 0;
                    for (int k = 1; k < res.components.Count; k++) if (res.components[k].value > res.components[slot].value) slot = k;
                }
                res.components[slot] = ItemFactory.Create(leg, Rarity.Legendary, rng, "cache", owner, serialFor);
            }
            for (int k = comps; k < 10; k++) res.consumables.Add(rng.Pick(Catalog.Consumables).id);
        }

        // ------------------------------------------------------------------ bots (lobby offline)

        /// <summary>
        /// Garagem de um bot: peças reais (instâncias com dono "bot:...") para o lobby offline. Se o bot for destruído,
        /// são estas peças que entram no Pool — nada é inventado para encher recompensas.
        /// </summary>
        public static List<(string socket, EquipmentInstance item)> BotLoadout(ChassisDef c, int skill, Rng rng, string owner)
        {
            double[] odds = skill switch
            {
                0 => new[] { 0.75, 0.22, 0.03, 0.0 },
                1 => new[] { 0.45, 0.38, 0.15, 0.02 },
                _ => new[] { 0.20, 0.40, 0.32, 0.08 },
            };
            var list = new List<(string, EquipmentInstance)>();
            foreach (var s in c.sockets)
            {
                if (!rng.Chance(0.35 + 0.15 * skill)) continue;
                var fits = Catalog.Regular.Where(s.Accepts).ToList();
                if (fits.Count == 0) continue;
                list.Add((s.id, ItemFactory.Create(rng.Pick(fits), (Rarity)rng.Weighted(odds), rng, "bot", owner)));
            }
            if (skill >= 2 && rng.Chance(0.03))
            {
                var leg = rng.Pick(Catalog.Legendaries.ToList());
                var sock = c.sockets.FirstOrDefault(s => s.Accepts(leg));
                if (sock != null)
                {
                    list.RemoveAll(x => x.Item1 == sock.id);
                    list.Add((sock.id, ItemFactory.Create(leg, Rarity.Legendary, rng, "bot", owner)));
                }
            }
            return list;
        }

        // ------------------------------------------------------------------ proezas, contratos e resultados

        public sealed class ContractDef
        {
            public string id, name, desc; public int target; public long reward;
            public ContractDef(string id, string name, string desc, int target, long reward) { this.id = id; this.name = name; this.desc = desc; this.target = target; this.reward = reward; }
        }

        public static readonly ContractDef[] Contracts =
        {
            new ContractDef("racer", "RACER", "Concluir 2 corridas", 2, 300),
            new ContractDef("extractor", "EXTRACTOR", "Extrair 2 vezes", 2, 450),
            new ContractDef("top10", "TOP TEN", "Top 10 duas vezes", 2, 550),
            new ContractDef("podium", "PODIUM HUNTER", "Alcançar um pódio", 1, 700),
            new ContractDef("champion", "CHAMPION", "Vencer uma corrida", 1, 900),
            new ContractDef("canyon", "CANYON RUNNER", "Completar 3 Skill Routes", 3, 400),
            new ContractDef("survival", "SURVIVAL SPECIALIST", "Extrair 2 vezes sem reparar", 2, 600),
            new ContractDef("streak", "HOT STREAK", "3 extrações seguidas", 3, 750),
        };

        /// <summary>Proezas (Doc 03 §4): teto de ✦500; Vitória Imaculada substitui Corrida Perfeita, Mecânico de Folga e Navegador Nato.</summary>
        public static List<(string name, long value)> Prowess(RaceOutcome o)
        {
            var list = new List<(string, long)>();
            if (o.state != RaceState.Extracted) return list;
            bool flawless = o.position == 1 && !o.tookDamage && o.repairs == 0 && o.penalties == 0;
            if (flawless) list.Add(("Vitória Imaculada", 500));
            if (o.hullFrac <= 0.10f) list.Add(("Sobrevivente", 200));
            if (!flawless && !o.tookDamage) list.Add(("Corrida Perfeita", 300));
            if (!flawless && o.repairs == 0) list.Add(("Mecânico de Folga", 120));
            if (o.fuelFrac <= 0.03f) list.Add(("Última Gota", 150));
            if (!o.usedBoost) list.Add(("Energia Pura", 180));
            if (!flawless && o.allCheckpoints && o.penalties == 0) list.Add(("Navegador Nato", 100));
            if (o.referenceTime > 0f && o.time <= o.referenceTime) list.Add(("Contra o Relógio", 200));
            // teto: as mais valiosas primeiro até ✦500
            var paid = new List<(string, long)>();
            long sum = 0;
            foreach (var pr in list.OrderByDescending(x => x.Item2))
            {
                if (sum >= ProwessCap) break;
                long v = Math.Min(pr.Item2, ProwessCap - sum);
                paid.Add((pr.Item1, v));
                sum += v;
            }
            return paid;
        }

        /// <summary>
        /// Aplica o resultado de uma corrida ao perfil (idempotente pelo raceId): consumíveis gastos/perdidos, peças perdidas
        /// para o Pool, peças ganhas do Pool, ✦ por posição × duração, extração, proezas, contratos e relatório.
        /// </summary>
        public static RaceReport ApplyRace(PlayerProfile p, RaceOutcome o)
        {
            if (AlreadyApplied(p, o.raceId)) return p.last ?? new RaceReport { raceId = o.raceId };
            var rep = new RaceReport
            {
                raceId = o.raceId, course = o.course, mode = o.mode.ToString(), chassis = Catalog.ChassisOf(p.chassis).name, state = o.state,
                position = o.position, racers = o.racers, time = o.time, hull = o.hullFrac, fuel = o.fuelFrac, poolValue = o.poolValue,
            };
            var ins = p.Item(p.insured);
            rep.insured = ins != null ? ins.Label : "";
            bool risk = o.mode != GameMode.Exploration;

            // LEVEI: peças montadas + consumíveis carregados
            foreach (var it in p.Equipped())
                rep.carried.Add(new ReportLine((it.id == p.insured ? "[SEGURO] " : "") + $"{it.Label} ({RarityInfo.Name(it.rarity)})", it.rarity, it.value));
            foreach (var s in p.loadout.Where(s => s.count > 0))
                rep.carried.Add(new ReportLine($"{Catalog.Consumable(s.id)?.name} ×{s.count}"));

            // consumíveis: gastos saem sempre do stock; se a extração falhar, o resto do que levava também se perde
            foreach (var c in o.consumed) { TakeStock(p, c.id, c.count); rep.lost.Add(new ReportLine($"{Catalog.Consumable(c.id)?.name} ×{c.count} (usado)")); }
            if (risk && o.state != RaceState.Extracted)
            {
                foreach (var s in p.loadout.Where(s => s.count > 0))
                {
                    int usedN = o.consumed.Where(c => c.id == s.id).Sum(c => c.count);
                    int left = Math.Max(0, s.count - usedN);
                    if (left > 0) { TakeStock(p, s.id, left); rep.lost.Add(new ReportLine($"{Catalog.Consumable(s.id)?.name} ×{left} (perdido)")); }
                }
            }

            // PERDI: peças que entraram no Pool (nunca a segurada)
            if (risk)
            {
                foreach (var id in o.lostItemIds)
                {
                    var it = p.Item(id);
                    if (it == null || id == p.insured) continue;
                    p.items.Remove(it);
                    foreach (var b in p.builds) foreach (var s in b.slots) if (s.item == id) s.item = "";
                    rep.lost.Add(new ReportLine($"{it.Label} ({RarityInfo.Name(it.rarity)}) → Expedition Pool", it.rarity, it.value));
                }
            }

            // GANHEI: peças do Pool (a mesma instância muda de dono) e Stardust
            foreach (var it in o.gained)
            {
                if (p.Item(it.id) != null) continue;
                it.owner = p.slot; it.insured = false;
                p.items.Add(it);
                rep.gained.Add(new ReportLine($"{it.Label} ({RarityInfo.Name(it.rarity)})", it.rarity, it.value));
                Log(p, "pool", 0, $"Recebido do Pool: {it.Label} ({Fmt.Dust(it.value)} avaliação)");
            }

            if (risk)
            {
                double mult = DurationMultiplier(o.referenceMinutes);
                void Pay(string what, long v, bool scaled = true)
                {
                    long val = scaled ? (long)Math.Round(v * mult / 5.0) * 5 : v;
                    if (val <= 0) return;
                    rep.stardust.Add(new ReportLine(what, Rarity.Common, val));
                    rep.stardustTotal += val;
                }
                int pos = Math.Max(1, Math.Min(PositionReward.Length, o.position));
                if (o.state == RaceState.Extracted)
                {
                    Pay($"{o.position}.º lugar", PositionReward[pos - 1]);
                    Pay("EXTRACTED", ExtractedBonus);
                    foreach (var pr in Prowess(o)) Pay($"Proeza: {pr.name}", pr.value);
                    if (!p.firstExtractionPaid) { p.firstExtractionPaid = true; Pay("Primeira extração", FirstExtractionBonus, false); }
                }
                else if (o.state == RaceState.Destroyed || o.state == RaceState.Stranded)
                    Pay($"Participação ({o.position}.º, extração falhada)", PositionReward[pos - 1] / 4);
                if (mult < 1.0 && rep.stardust.Count > 0) rep.stardust.Add(new ReportLine($"(duração ×{mult:0.00})"));

                // estatísticas e contratos
                if (o.state != RaceState.Abandoned) p.races++;
                bool ext = o.state == RaceState.Extracted;
                if (ext) { p.extractions++; p.streak++; if (o.repairs == 0) p.noRepairStreak++; } else p.streak = 0;
                void Progress(string id, int add)
                {
                    if (add <= 0) return;
                    var cs = p.contracts.Find(c => c.id == id); var def = Array.Find(Contracts, c => c.id == id);
                    if (cs == null || def == null) return;
                    cs.progress += add;
                    if (cs.progress >= def.target) { cs.progress = 0; cs.completed++; Pay($"Contrato {def.name}", def.reward); }
                }
                if (ext)
                {
                    Progress("racer", 1); Progress("extractor", 1);
                    if (o.position <= 10) Progress("top10", 1);
                    if (o.position <= 3) Progress("podium", 1);
                    if (o.position == 1) Progress("champion", 1);
                    Progress("canyon", o.skillRoutes);
                    if (o.repairs == 0) Progress("survival", 1);
                    if (p.streak >= 3) { Progress("streak", 3); p.streak = 0; }
                }
                p.stardust += rep.stardustTotal;
                if (rep.stardustTotal > 0) Log(p, "corrida", rep.stardustTotal, $"{o.course}: {o.state} {o.position}/{o.racers}");
                p.shopRotation++;
            }
            ClampLoadout(p);
            p.last = rep;
            return rep;
        }
    }
}
