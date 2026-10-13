// Testes da camada de meta-jogo (RedDust.Meta), sem Unity: Tools/test_meta.ps1 compila com o Roslyn do editor e corre.
using System;
using System.Collections.Generic;
using System.Linq;
using RedDust.Meta;

static class MetaTests
{
    static int fails, checks;

    static void Check(bool ok, string what)
    {
        checks++;
        if (!ok) { fails++; Console.WriteLine("FALHA: " + what); }
    }

    static int Main()
    {
        CatalogTests();
        ItemTests();
        CacheTests();
        PoolTests();
        EconomyTests();
        Console.WriteLine($"{checks - fails}/{checks} verificações OK");
        return fails == 0 ? 0 : 1;
    }

    static void CatalogTests()
    {
        Check(Catalog.Chassis.Length == 5, "5 chassis");
        Check(Catalog.Regular.Count() == 31, "31 componentes (28 + 3 propulsão)");
        Check(Catalog.Legendaries.Count() == 3, "3 lendários");
        Check(Catalog.Consumables.Length == 6, "6 consumíveis");
        foreach (var c in Catalog.Chassis)
            foreach (var s in c.sockets)
                Check(Catalog.Regular.Any(s.Accepts), $"{c.name}.{s.id} tem pelo menos um módulo compatível");
        var strix = Catalog.ChassisOf("strix");
        Check(strix.stats.SequenceEqual(new[] { 72, 74, 76, 75, 66, 66, 68, 70 }), "stats STRIX do Doc 02");
        Check(Catalog.ChassisOf("vortex").Socket("PropulsionC") != null, "VORTEX tem propulsor central");
        Check(Catalog.ChassisOf("bastion").Socket("Armor2") != null, "BASTION tem blindagem secundária");
        Check(Catalog.ChassisOf("nomad").Socket("Aux") != null, "NOMAD tem socket auxiliar");
    }

    static void ItemTests()
    {
        var rng = new Rng(7);
        foreach (var d in Catalog.Regular)
            for (int r = 0; r <= (int)Rarity.Epic; r++)
                for (int n = 0; n < 20; n++)
                {
                    var it = ItemFactory.Create(d, (Rarity)r, rng, "teste", "t");
                    int pos = it.rolls.Where(x => x.stat != Stat.Mass && x.value > 0).Sum(x => x.value);
                    int neg = -it.rolls.Where(x => x.stat != Stat.Mass && x.value < 0).Sum(x => x.value);
                    Check(pos <= RarityInfo.Budget[r] + neg, $"{d.id} {(Rarity)r}: budget {pos} <= {RarityInfo.Budget[r]}+{neg}");
                    foreach (var rule in d.stats) Check(it.Roll(rule.stat) <= rule.cap, $"{d.id}: cap de {rule.stat}");
                    var allowed = d.stats.Select(x => x.stat).Concat(d.drawbacks.Select(x => x.stat)).Append(Stat.Mass).ToHashSet();
                    Check(it.rolls.All(x => allowed.Contains(x.stat)), $"{d.id}: só stats da família");
                    Check(it.value > 0 && string.IsNullOrEmpty(it.serial), $"{d.id}: valor e sem serial");
                }
        foreach (var d in Catalog.Legendaries)
        {
            var it = ItemFactory.Create(d, Rarity.Legendary, rng, "teste", "t", pre => pre + "-0001");
            Check(it.rarity == Rarity.Legendary && it.serial == d.serialPrefix + "-0001" && !string.IsNullOrEmpty(it.perk), $"{d.name}: serial e perk");
        }
    }

    static void CacheTests()
    {
        var rng = new Rng(99);
        foreach (CacheKind k in new[] { CacheKind.Standard, CacheKind.Advanced, CacheKind.Elite })
        {
            var counts = new int[5];
            int boxes = k == CacheKind.Elite ? 20000 : 6000, legendaryBoxes = 0;
            bool always10 = true, advRare = true, eliteEpic = true, elite4 = true, noHigh = true;
            for (int b = 0; b < boxes; b++)
            {
                var res = new CacheResult { kind = k };
                Economy.Roll(k, rng, res, p => p + "-0", "t");
                always10 &= res.components.Count + res.consumables.Count == 10;
                foreach (var c in res.components) counts[(int)c.rarity]++;
                if (res.components.Any(c => c.rarity == Rarity.Legendary)) legendaryBoxes++;
                if (k == CacheKind.Advanced) advRare &= res.components.Any(c => c.rarity >= Rarity.Rare);
                if (k == CacheKind.Elite)
                {
                    eliteEpic &= res.components.Any(c => c.rarity >= Rarity.Epic);
                    elite4 &= res.components.Count(c => c.rarity >= Rarity.Rare) >= 4;
                }
                if (k == CacheKind.Standard) noHigh &= res.components.All(c => c.rarity <= Rarity.Rare);
                Check(res.components.Select(c => c.Def.family).Distinct().Count() == res.components.Count, $"{k}: famílias variadas");
            }
            Check(always10, $"{k}: sempre 10 itens");
            int total = counts.Sum();
            string dist = string.Join(" / ", counts.Select(c => $"{100.0 * c / total:0.0}%"));
            Console.WriteLine($"{Economy.CacheName(k)}: {dist} · caixas com Lendário {100.0 * legendaryBoxes / boxes:0.00}%");
            if (k == CacheKind.Standard)
            {
                Check(noHigh, "Standard sem Epic/Legendary");
                Check(Math.Abs(counts[0] / (double)total - 0.70) < 0.02 && Math.Abs(counts[1] / (double)total - 0.27) < 0.02 && Math.Abs(counts[2] / (double)total - 0.03) < 0.01, "Standard 70/27/3");
            }
            if (k == CacheKind.Advanced) Check(advRare, "Advanced: mínimo 1 Rare");
            if (k == CacheKind.Elite)
            {
                Check(eliteEpic && elite4, "Elite: 1 Epic + 4 Rare ou mais");
                double lp = legendaryBoxes / (double)boxes;
                Check(lp > 0.032 && lp < 0.048, $"Elite: 4% de Lendário por CAIXA ({lp:P2})");
            }
        }
    }

    static void PoolTests()
    {
        var rng = new Rng(5);
        var pool = new ExpeditionPool();
        var items = Enumerable.Range(0, 7).Select(i => ItemFactory.Create(rng.Pick(Catalog.Regular.ToList()), (Rarity)(i % 4), rng, "bot", "b")).ToList();
        foreach (var it in items) Check(pool.Add(it, "bot"), "entra no pool");
        Check(!pool.Add(items[0], "bot"), "não duplica a mesma instância");
        Check(pool.Valuation == items.Sum(i => (long)i.value), "avaliação = soma dos itens reais");
        var dist = pool.Distribute(new[] { "p1", "b2", "b3" });
        var all = dist.Values.SelectMany(x => x).ToList();
        Check(all.Count == 7 && all.Select(x => x.id).Distinct().Count() == 7, "distribui exatamente os 7 itens, sem inventar");
        Check(dist["p1"][0].value == items.Max(i => i.value), "1.º recebe a peça mais valiosa");
        Check(new ExpeditionPool().Distribute(new[] { "p1" })["p1"].Count == 0, "ninguém perdeu nada → pool 0");
        var lost = LossRules.SelectLosses(items, items[0].id, rng);
        Check(lost.Count == 3 && lost.All(i => i.id != items[0].id), "perde até 3, nunca a segurada");
    }

    static void EconomyTests()
    {
        var p = Economy.NewProfile("p1", "Teste", 1234);
        Check(p.stardust == 1000, "saldo inicial ✦1000");
        Check(p.Equipped().Count == 4 && p.insured == p.Equipped()[0].id, "kit inicial montado e segurado");
        Check(BuildValidator.Validate(p, "strix").Count == 0, "build inicial válida");
        {   // kit de boas-vindas: generoso, válido e só uma vez
            var k = Economy.NewProfile("pk", "Kit", 77);
            long kb = k.stardust; int ki = k.items.Count;
            Check(Economy.GrantWelcomeKit(k, 5), "kit de boas-vindas aplicado");
            Check(k.stardust == kb + Economy.WelcomeBonus && k.items.Count == ki + 16, "kit: ✦ e 16 peças");
            Check(k.Build("strix").slots.TrueForAll(sl => !string.IsNullOrEmpty(sl.item)), "kit: STRIX com todos os sockets");
            Check(BuildValidator.Validate(k, "strix").Count == 0, "kit: build da STRIX válida");
            Check(!Economy.GrantWelcomeKit(k, 6) && k.stardust == kb + Economy.WelcomeBonus, "kit: idempotente");
        }
        Check(Economy.BuyConsumable(p, "foam") == null && p.stardust == 900 && p.StockCount("foam") == 3, "comprar Repair Foam");
        var bastionArmor = p.items.First(i => i.Def.family == Family.Armor);
        Check(Economy.Equip(p, "bastion", "Armor", bastionArmor) != null, "armadura M recusada no BASTION (L)");
        Check(Economy.Sell(p, bastionArmor.id) != null, "não vende peça montada");

        // 8.º lugar numa expedição de 20 min, com dano, reparação e boost: 600 + 250 + primeira extração 500
        var o = new RaceOutcome { raceId = "r1", course = "teste", mode = GameMode.Extraction, state = RaceState.Extracted, position = 8, racers = 16,
            time = 1300, referenceTime = 1200, referenceMinutes = 20, hullFrac = 0.6f, fuelFrac = 0.2f, tookDamage = true, repairs = 1, usedBoost = true };
        var rep = Economy.ApplyRace(p, o);
        Check(rep.stardustTotal == 1350, $"8.º extraído = 600+250+500 (obtido {rep.stardustTotal})");
        long after = p.stardust;
        Economy.ApplyRace(p, o);
        Check(p.stardust == after, "resultado idempotente (não paga duas vezes)");

        // destruído: perde até 3 peças não seguradas e o que levava; a segurada fica
        var insured = p.insured;
        var carried = p.Equipped();
        var lost = LossRules.SelectLosses(carried, insured, new Rng(3));
        var d = new RaceOutcome { raceId = "r2", course = "teste", mode = GameMode.Extraction, state = RaceState.Destroyed, position = 14, racers = 16,
            referenceMinutes = 20, lostItemIds = lost.Select(i => i.id).ToList() };
        int before = p.items.Count;
        rep = Economy.ApplyRace(p, d);
        Check(p.items.Count == before - lost.Count && p.Item(insured) != null, "destruído: perde as sorteadas, a segurada volta");
        Check(rep.lost.Count >= lost.Count && rep.carried.Count >= carried.Count, "relatório: levei / perdi");

        // vitória imaculada: substitui as sobrepostas e respeita o teto de ✦500
        var w = new RaceOutcome { raceId = "r3", mode = GameMode.Extraction, state = RaceState.Extracted, position = 1, racers = 16, referenceMinutes = 20,
            hullFrac = 1f, fuelFrac = 0.5f, usedBoost = false, allCheckpoints = true, time = 900, referenceTime = 1000 };
        var pr = Economy.Prowess(w);
        Check(pr.Sum(x => x.value) == 500 && pr.Any(x => x.name == "Vitória Imaculada") && !pr.Any(x => x.name == "Corrida Perfeita"), "proezas: Imaculada substitui e teto ✦500");

        // pool: o ganho é a mesma instância (id e serial)
        var leg = ItemFactory.Create(Catalog.Legendaries.First(), Rarity.Legendary, new Rng(1), "bot", "bot:X", pre => pre + "-0042");
        var g = new RaceOutcome { raceId = "r4", mode = GameMode.Extraction, state = RaceState.Extracted, position = 2, racers = 8, referenceMinutes = 4, gained = { leg } };
        rep = Economy.ApplyRace(p, g);
        var got = p.Item(leg.id);
        Check(got != null && got.serial.EndsWith("0042") && got.owner == "p1", "lendário do pool mantém serial e muda de dono");
        Check(rep.stardust.Any(l => l.text.Contains("×0.35")) || rep.stardust.Any(l => l.text.Contains("×0,35")), "lab curto: multiplicador ×0,35");

        // caixa: idempotente pelo id da transação
        p.stardust = 20000;
        var c1 = Economy.OpenCache(p, CacheKind.Standard, "tx-1", new Rng(11));
        var c2 = Economy.OpenCache(p, CacheKind.Standard, "tx-1", new Rng(11));
        Check(c1.error == null && c2.error != null && p.stardust == 17500, "abrir a mesma caixa duas vezes só cobra uma");
        var offers = Economy.ShopOffers(p);
        Check(offers.Count == 6 && offers.All(x => x.rarity <= Rarity.Rare), "loja: 6 ofertas sem Epic/Legendary");
        Check(Economy.BuyComponent(p, offers[0]) == null && !Economy.ShopOffers(p).Any(x => x.id == offers[0].id), "comprado sai da loja");
    }
}
