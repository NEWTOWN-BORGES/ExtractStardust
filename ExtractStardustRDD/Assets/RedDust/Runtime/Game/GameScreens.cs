using System;
using System.Collections.Generic;
using System.Linq;
using RedDust.Meta;
using RedDust.Presentation;
using UnityEngine;
using UnityEngine.InputSystem;

namespace RedDust.Game
{
    /// <summary>
    /// Menus (IMGUI, comando/teclado/rato/toque): principal, Hangar, escolha de peça, Mochila, Mercado e Supply Caches,
    /// relatório da última expedição, opções, briefing e pausa. Cada ecrã é uma lista de itens com cartão de informação.
    /// </summary>
    public partial class GameDirector
    {
        sealed class Card
        {
            public Texture icon;
            public string title = "", subtitle = "", body = "";
            public Color color = Color.white;
            public ShipStats now, then;
        }

        sealed class Item
        {
            public string label = "", value = "", detail = "";
            public Texture icon;
            public Color color = Color.white;
            public bool header, enabled = true;
            public Action ok;
            public Action<int> lr;
            public Card card;
        }

        readonly List<Item> items = new List<Item>();
        readonly Dictionary<Page, int> selMem = new Dictionary<Page, int>();
        int sel;
        string title = "", subtitle = "", toast;
        float toastUntil, armedUntil, cacheOpened;
        string armedKey, pickSocket;
        GameMode briefingMode = GameMode.Extraction;
        Page optionsReturn = Page.Main;
        CacheResult lastCache;
        Vector2 reportScroll;

        void Go(Page p)
        {
            selMem[screen] = sel;
            screen = p;
            sel = selMem.TryGetValue(p, out var s) ? s : 0;
        }

        void Toast(string t) { toast = t; toastUntil = Time.unscaledTime + 3.2f; }

        /// <summary>Ações irreversíveis (vender, abrir caixa, abandonar, apagar perfil) pedem segunda confirmação.</summary>
        bool Armed(string key, string prompt)
        {
            if (armedKey == key && Time.unscaledTime < armedUntil) { armedKey = null; return true; }
            armedKey = key; armedUntil = Time.unscaledTime + 3f;
            Toast(prompt);
            return false;
        }

        void Save(PlayerProfile p) { if (p != null) ProfileStore.Save(p); }

        Item Add(string label, string value = "", Action ok = null, Action<int> lr = null, Texture icon = null, Color? color = null, Card card = null, string detail = "")
        {
            var it = new Item { label = label, value = value, ok = ok, lr = lr, icon = icon, color = color ?? Color.white, card = card, detail = detail };
            items.Add(it);
            return it;
        }

        void Header(string label) => items.Add(new Item { label = label, header = true, enabled = false });

        static string SocketName(string id) => id switch
        {
            "Engine" => "Motor", "Propulsion" => "Propulsão", "PropulsionC" => "Propulsão central", "Wings" => "Asas / estabilizador",
            "Armor" => "Blindagem", "Armor2" => "Blindagem secundária", "Reactor" => "Reator", "Cooling" => "Refrigeração",
            "Tail" => "Cauda", "Utility" => "Navegação / utilidade", "Aux" => "Auxiliar / combustível", _ => id,
        };

        static string Difficulty(int d) => d == 0 ? "Fácil" : d == 1 ? "Normal" : "Difícil";

        // ------------------------------------------------------------------ cartões

        Card ItemCard(EquipmentInstance it, SocketDef socket = null)
        {
            if (it == null)
                return new Card { icon = Icons.Empty(), title = "Peça de série", subtitle = socket != null ? SocketName(socket.id) : "", body = "Componente original do chassis: sem bónus, sem valor em risco." };
            var d = it.Def;
            string body = $"{d.manufacturer} · {d.family} · classe {d.size}\n{d.desc}\n\n{it.RollText()}";
            if (!string.IsNullOrEmpty(it.drawback)) body += $"\n<color=#ff9a7a>{it.drawback}</color>";
            if (!string.IsNullOrEmpty(it.serial)) body += $"\nSerial {it.serial}";
            body += $"\n\nAvaliação {Fmt.Dust(it.value)} · venda {Fmt.Dust(it.SellValue)} · origem: {it.source}";
            return new Card { icon = Icons.Equipment(it), title = it.Name, subtitle = RarityInfo.Name(it.rarity).ToUpperInvariant(), color = Icons.RarityColor(it.rarity), body = body };
        }

        Card ConsumableCard(ConsumableDef c, PlayerProfile p) => new Card
        {
            icon = Icons.Consumable(c.id), title = c.name, subtitle = $"{Fmt.Dust(c.price)}  ·  tens {p.StockCount(c.id)}",
            color = Icons.ConsumableColor(c.kind, c.id),
            body = c.desc + (c.speedPenalty > 0f ? $"\nEnquanto aplica: -{c.speedPenalty:P0} de velocidade máxima (custa tempo)." : "") +
                   "\n\nNa corrida: L1 usa o selecionado (D-pad ↑/↓ escolhe) · teclado 1/2/3.",
        };

        Card ChassisCard(ChassisDef c, PlayerProfile p) => new Card
        {
            title = c.name, subtitle = c.role.ToUpperInvariant(), color = ShipBuilder.Paint(c.paint) * 1.6f,
            body = $"\"{c.fantasy}\"\n\nPASSIVA — {c.passive}\n{c.passiveText}\n\nFraqueza: {c.weakness}\nMassa {c.massKg:0} kg · sockets: {string.Join(", ", c.sockets.Select(s => SocketName(s.id)))}",
            now = StatResolver.Resolve(c, p.Build(c.id).slots.Select(s => p.Item(s.item)).Where(i => i != null)),
        };

        // ------------------------------------------------------------------ construção dos ecrãs

        void BuildScreen()
        {
            items.Clear();
            var p = P;
            switch (screen)
            {
                case Page.Main: BuildMain(); break;
                case Page.Hangar: BuildHangar(p); break;
                case Page.Pick: BuildPick(p); break;
                case Page.Backpack: BuildBackpack(p); break;
                case Page.Market: BuildMarket(p); break;
                case Page.Report: BuildReport(); break;
                case Page.Options: BuildOptions(); break;
                case Page.Briefing: BuildBriefing(); break;
                case Page.Pause: BuildPause(); break;
                case Page.Results: BuildResults(); break;
                case Page.Cache: title = lastCache != null ? Economy.CacheName(lastCache.kind) : ""; subtitle = "10 itens"; Add("CONTINUAR", ok: () => Go(Page.Market)); break;
            }
            if (items.Count > 0)
            {
                sel = Mathf.Clamp(sel, 0, items.Count - 1);
                for (int k = 0; k < items.Count && !Selectable(items[sel]); k++) sel = (sel + 1) % items.Count;
            }
        }

        static bool Selectable(Item it) => !it.header;

        void BuildMain()
        {
            var p1 = profiles[0];
            title = "EXTRACT: STARDUST";
            subtitle = $"RACE. SURVIVE. EXTRACT.   ·   {courseTitle}   ·   {p1.name} {Fmt.Dust(p1.stardust)}";
            Add("EXPLORAÇÃO", "sozinho", () => StartRace(GameMode.Exploration), card: new Card { title = "EXPLORAÇÃO", subtitle = "SEM RISCO",
                body = "Corre sozinho a pista inteira: treino, linhas, atalhos e paisagens. Sem dano, combustível ou perdas; não dá Stardust." });
            Add("EXTRAÇÃO vs BOTS", $"{botCount} bots · {Difficulty(difficulty)}", () => { briefingMode = GameMode.Extraction; editing = 0; Go(Page.Briefing); },
                card: new Card { title = "EXTRAÇÃO", subtitle = "EQUIPAMENTO EM RISCO", color = new Color(1f, 0.6f, 0.3f),
                    body = "Leva a tua build. Dano, combustível e calor ativos.\n\nEXTRACTED: ✦ pela posição + extração + proezas e peças do Expedition Pool.\nDESTROYED/STRANDED: perdes até 3 peças não seguradas (vão para o Pool) e os consumíveis levados. A peça segurada volta sempre.\n\nO Stardust da carteira nunca se perde." });
            Add("PVP LOCAL + BOTS", "ecrã dividido", () =>
            {
                briefingMode = GameMode.LocalVersus;
                if (profiles[1] == null) profiles[1] = ProfileStore.Load("p2", "Piloto 2");
                Go(Page.Briefing);
            }, card: new Card { title = "PVP LOCAL", subtitle = "2 JOGADORES + BOTS", body = "Ecrã dividido no mesmo PC/telemóvel. Cada jogador tem o seu perfil (carteira, garagem, mochila) e o Pool pode passar peças de um para o outro.\n\nComandos: 2 comandos → um cada · 1 comando → J1 teclado, J2 comando · sem comandos → teclado dividido (WASD / setas)." });
            Add("HANGAR", Catalog.ChassisOf(P.chassis).name, () => Go(Page.Hangar), card: new Card { title = "HANGAR", body = "Escolhe o chassis, monta módulos (a nave muda à vista), escolhe a peça segurada e os consumíveis que levas." });
            Add("MOCHILA", $"{P.items.Count} peças", () => Go(Page.Backpack), card: new Card { title = "MOCHILA", body = "Tudo o que tens: peças (com raridade, rolls e valor) e consumíveis. Vende duplicados a 25% do valor." });
            Add("MERCADO", "consumíveis · peças · caixas", () => Go(Page.Market), card: new Card { title = "MERCADO", body = "Consumíveis, componentes em rotação e Supply Caches de 10 itens aleatórios (Standard, Advanced, Elite)." });
            Add("ÚLTIMA EXPEDIÇÃO", P.last != null ? $"{P.last.state} {P.last.position}/{P.last.racers}" : "—", () => Go(Page.Report),
                card: new Card { title = "RELATÓRIO", body = "O que levaste, o que perdeste e o que ganhaste na última expedição." });
            Add("Pista", $"‹ {courseTitle} ›", () => ChangeCourse(1), ChangeCourse);
            Add("Bots", $"‹ {botCount} ›", null, d => botCount = Mathf.Clamp(botCount + d, 1, 19));
            Add("Dificuldade", $"‹ {Difficulty(difficulty)} ›", null, d => difficulty = (difficulty + d + 3) % 3);
            Add("Opções", "", () => { optionsReturn = Page.Main; Go(Page.Options); });
            Add("Sair", "", () => Application.Quit());
        }

        void SwitchPilot(int d)
        {
            editing = 1 - editing;
            if (profiles[1] == null) profiles[1] = ProfileStore.Load("p2", "Piloto 2");
            RefreshPreview();
        }

        void BuildHangar(PlayerProfile p)
        {
            var c = Catalog.ChassisOf(p.chassis);
            title = "HANGAR";
            subtitle = $"{p.name}  ·  {Fmt.Dust(p.stardust)}  ·  build {Fmt.Dust(p.BuildValue)}  ·  em risco {Fmt.Dust(p.ValueAtRisk)}";
            Add("Piloto", $"‹ {p.name} ›", () => SwitchPilot(1), SwitchPilot);
            Add("Chassis", $"‹ {c.name} ›", null, d =>
            {
                int i = Array.IndexOf(Catalog.Chassis, c);
                p.chassis = Catalog.Chassis[(i + d + Catalog.Chassis.Length) % Catalog.Chassis.Length].id;
                p.Build(p.chassis);
                if (!p.Equipped().Exists(x => x.id == p.insured)) Economy.SetInsured(p, p.Equipped().FirstOrDefault()?.id ?? "");
                Save(p); RefreshPreview();
            }, color: ShipBuilder.Paint(c.paint) * 1.6f, card: ChassisCard(c, p));
            Header("MÓDULOS");
            foreach (var s in c.sockets)
            {
                var sock = s;
                var it = p.Item(p.Current.slots.Find(x => x.socket == s.id)?.item);
                Add(SocketName(s.id), it != null ? it.Label : "(de série)", () => { pickSocket = sock.id; Go(Page.Pick); },
                    icon: it != null ? Icons.Equipment(it) : (Texture)Icons.Empty(), color: it != null ? Icons.RarityColor(it.rarity) : new Color(0.7f, 0.72f, 0.75f), card: ItemCard(it, s));
            }
            Header("EXPEDIÇÃO");
            var eq = p.Equipped();
            var ins = p.Item(p.insured);
            Add("Peça segurada", ins != null ? $"‹ {ins.Label} ›" : (eq.Count > 0 ? "‹ nenhuma ›" : "monta uma peça primeiro"), null, d =>
            {
                if (eq.Count == 0) return;
                int i = eq.FindIndex(x => x.id == p.insured);
                Economy.SetInsured(p, eq[((i < 0 ? -1 : i) + d + eq.Count) % eq.Count].id);
                Save(p);
            }, icon: ins != null ? Icons.Equipment(ins) : null, color: new Color(0.55f, 0.95f, 1f),
            card: new Card { title = "SEGURO", subtitle = "1 PEÇA POR EXPEDIÇÃO", body = "Se fores destruído, a peça segurada volta à garagem. Das outras peças montadas, até 3 (sorteadas pelo valor) podem ir para o Expedition Pool e passar para quem extrair." });
            while (p.loadout.Count < Economy.LoadoutSlots) p.loadout.Add(new ConsumableStack("", 0));
            for (int k = 0; k < Economy.LoadoutSlots; k++)
            {
                int slot = k;
                var st = p.loadout[slot];
                var cd = Catalog.Consumable(st.id);
                Add($"Consumível {slot + 1}", cd != null ? $"‹ {cd.name} ×{st.count} ›" : "‹ (vazio) ›", () =>
                {
                    if (cd == null) return;
                    Economy.SetLoadout(p, slot, st.id, st.count >= Economy.UnitsPerSlot ? 0 : st.count + 1);
                    Save(p);
                }, d =>
                {
                    var owned = Catalog.Consumables.Where(x => p.StockCount(x.id) > 0).Select(x => x.id).Prepend("").ToList();
                    int i = owned.IndexOf(st.id);
                    string next = owned[((i < 0 ? 0 : i) + d + owned.Count) % owned.Count];
                    Economy.SetLoadout(p, slot, next, Math.Max(1, st.count));
                    Save(p);
                }, icon: cd != null ? Icons.Consumable(cd.id) : null, color: cd != null ? Icons.ConsumableColor(cd.kind, cd.id) : Color.gray,
                card: cd != null ? ConsumableCard(cd, p) : new Card { title = "SLOT VAZIO", body = "←/→ escolhe um consumível que tenhas em stock; confirmar muda a quantidade (até 2). Compra no Mercado." });
            }
            var errors = BuildValidator.Validate(p, p.chassis);
            if (errors.Count > 0) Header("⚠ " + string.Join(" · ", errors));
            Add("VOLTAR", "", () => Go(Page.Main));
        }

        void BuildPick(PlayerProfile p)
        {
            var c = Catalog.ChassisOf(p.chassis);
            var sock = c.Socket(pickSocket);
            if (sock == null) { Go(Page.Hangar); return; }
            title = SocketName(sock.id).ToUpperInvariant();
            subtitle = $"{c.name} aceita {sock.family} classe {string.Join("/", sock.sizes)}";
            var current = p.Current.slots.Find(x => x.socket == sock.id)?.item;
            var nowStats = StatResolver.Resolve(c, p.Equipped());
            ShipStats With(EquipmentInstance cand)
            {
                var list = p.Current.slots.Where(x => x.socket != sock.id).Select(x => p.Item(x.item)).Where(i => i != null && (cand == null || i.id != cand.id)).ToList();
                if (cand != null) list.Add(cand);
                return StatResolver.Resolve(c, list);
            }
            var stockCard = ItemCard(null, sock); stockCard.now = nowStats; stockCard.then = With(null);
            Add("(peça de série)", string.IsNullOrEmpty(current) ? "MONTADA" : "", () => { Economy.Equip(p, c.id, sock.id, null); Save(p); RefreshPreview(); Go(Page.Hangar); }, icon: Icons.Empty(), card: stockCard);
            foreach (var it in p.items.Where(i => i.Def.family == sock.family).OrderByDescending(i => i.rarity).ThenByDescending(i => i.value))
            {
                var item = it;
                bool fits = sock.Accepts(it.Def);
                var card = ItemCard(it, sock);
                card.now = nowStats; card.then = With(it);
                var row = Add(it.Label, it.id == current ? "MONTADA" : fits ? RarityInfo.Name(it.rarity) : $"classe {it.Def.size} não encaixa", () =>
                {
                    string err = Economy.Equip(p, c.id, sock.id, item);
                    if (err != null) { Toast(err); return; }
                    Save(p); RefreshPreview(); Go(Page.Hangar);
                }, icon: Icons.Equipment(it), color: Icons.RarityColor(it.rarity), card: card);
                row.enabled = fits;
            }
            Add("VOLTAR", "", () => Go(Page.Hangar));
        }

        void BuildBackpack(PlayerProfile p)
        {
            title = "MOCHILA";
            subtitle = $"{p.name}  ·  {Fmt.Dust(p.stardust)}  ·  {p.items.Count} peças  ·  avaliação {Fmt.Dust(p.items.Sum(i => (long)i.value))}";
            Add("Piloto", $"‹ {p.name} ›", () => SwitchPilot(1), SwitchPilot);
            Header("PEÇAS");
            foreach (var it in p.items.OrderByDescending(i => i.rarity).ThenBy(i => i.Def.family).ThenByDescending(i => i.value))
            {
                var item = it;
                bool mounted = p.IsEquippedAnywhere(it.id);
                Add(it.Label, mounted ? (it.id == p.insured ? "MONTADA · SEGURA" : "MONTADA") : $"vender {Fmt.Dust(it.SellValue)}", () =>
                {
                    if (mounted) { Toast("Está montada numa nave: troca-a no Hangar antes de vender."); return; }
                    if (!Armed("sell" + item.id, $"Carrega outra vez para vender {item.Name} por {Fmt.Dust(item.SellValue)}")) return;
                    string err = Economy.Sell(p, item.id);
                    Toast(err ?? $"Vendido: +{Fmt.Dust(item.SellValue)}");
                    Save(p);
                }, icon: Icons.Equipment(it), color: Icons.RarityColor(it.rarity), card: ItemCard(it));
            }
            Header("CONSUMÍVEIS");
            foreach (var c in Catalog.Consumables.Where(c => p.StockCount(c.id) > 0))
                Add(c.name, $"×{p.StockCount(c.id)}" + (p.LoadoutCount(c.id) > 0 ? $" (levas {p.LoadoutCount(c.id)})" : ""), null, icon: Icons.Consumable(c.id), color: Icons.ConsumableColor(c.kind, c.id), card: ConsumableCard(c, p));
            Add("VOLTAR", "", () => Go(Page.Main));
        }

        void BuildMarket(PlayerProfile p)
        {
            title = "MERCADO";
            subtitle = $"{p.name}  ·  {Fmt.Dust(p.stardust)}";
            Add("Piloto", $"‹ {p.name} ›", () => SwitchPilot(1), SwitchPilot);
            Header("CONSUMÍVEIS");
            foreach (var c in Catalog.Consumables)
            {
                var cons = c;
                Add(c.name, $"{Fmt.Dust(c.price)}   ·   tens {p.StockCount(c.id)}", () =>
                {
                    string err = Economy.BuyConsumable(p, cons.id, Guid.NewGuid().ToString("N"));
                    Toast(err ?? $"+1 {cons.name}");
                    Save(p);
                }, icon: Icons.Consumable(c.id), color: Icons.ConsumableColor(c.kind, c.id), card: ConsumableCard(c, p));
            }
            Header("COMPONENTES · a rotação muda depois de cada corrida");
            foreach (var o in Economy.ShopOffers(p))
            {
                var offer = o;
                Add(o.Name, Fmt.Dust(Economy.ShopPrice(o)), () =>
                {
                    if (!Armed("buy" + offer.id, $"Carrega outra vez para comprar {offer.Name} por {Fmt.Dust(Economy.ShopPrice(offer))}")) return;
                    string err = Economy.BuyComponent(p, offer);
                    Toast(err ?? $"Comprado: {offer.Name} (está na Mochila)");
                    Save(p);
                }, icon: Icons.Equipment(o), color: Icons.RarityColor(o.rarity), card: ItemCard(o));
            }
            Header("SUPPLY CACHES · 10 itens aleatórios por caixa");
            foreach (var k in new[] { CacheKind.Standard, CacheKind.Advanced, CacheKind.Elite })
            {
                var kind = k;
                string odds = k switch
                {
                    CacheKind.Standard => "70% Comum · 27% Incomum · 3% Raro. Sem Épico/Lendário.",
                    CacheKind.Advanced => "20% Comum · 50% Incomum · 27% Raro · 3% Épico. Mínimo 1 Raro.",
                    _ => "25% Incomum · 55% Raro · 20% Épico. Garante 1 Épico e 4+ Raros. 4% por caixa de um Lendário (HELIOS V-9, REDLINE-X, AEGIS FRAME).",
                };
                Add(Economy.CacheName(k), Fmt.Dust(Economy.CachePrice(k)), () =>
                {
                    if (p.stardust < Economy.CachePrice(kind)) { Toast("Stardust insuficiente. Corre expedições ou vende duplicados."); return; }
                    if (!Armed("cache" + kind, $"Carrega outra vez para abrir por {Fmt.Dust(Economy.CachePrice(kind))}")) return;
                    var res = Economy.OpenCache(p, kind, Guid.NewGuid().ToString("N"), rng);
                    if (res.error != null) { Toast(res.error); return; }
                    Save(p);
                    lastCache = res;
                    cacheOpened = Time.unscaledTime;
                    Go(Page.Cache);
                }, icon: Icons.Cache(k), card: new Card { icon = Icons.Cache(k), title = Economy.CacheName(k), subtitle = Fmt.Dust(Economy.CachePrice(k)),
                    body = $"Abre exatamente 10 itens: 4 a 6 componentes permanentes de famílias diferentes + consumíveis.\n\n{odds}\n\nChassis nunca saem de caixas." });
            }
            Add("VOLTAR", "", () => Go(Page.Main));
        }

        void BuildReport()
        {
            title = "ÚLTIMA EXPEDIÇÃO";
            subtitle = P.name;
            Add("Piloto", $"‹ {P.name} ›", () => SwitchPilot(1), SwitchPilot);
            Add("VOLTAR", "", () => Go(Page.Main));
        }

        void BuildOptions()
        {
            title = "OPÇÕES";
            subtitle = "";
            Add("Tremor da câmera", $"‹ {Mathf.RoundToInt(shake * 100)}% ›", null, d => { shake = Mathf.Clamp(shake + 0.25f * d, 0f, 1.5f); ApplyOptions(); });
            Add("Campo de visão extra", $"‹ {fovExtra:+0;-0;0}° ›", null, d => { fovExtra = Mathf.Clamp(fovExtra + 5f * d, -10f, 10f); ApplyOptions(); });
            Add("Vibração do comando", vibration ? "‹ ligada ›" : "‹ desligada ›", () => { vibration = !vibration; ApplyOptions(); }, d => { vibration = !vibration; ApplyOptions(); });
            Add("Bots", $"‹ {botCount} ›", null, d => botCount = Mathf.Clamp(botCount + d, 1, 19));
            Add("Dificuldade", $"‹ {Difficulty(difficulty)} ›", null, d => difficulty = (difficulty + d + 3) % 3);
            Add($"Recomeçar perfil de {P.name}", "apaga carteira e garagem", () =>
            {
                if (!Armed("reset" + editing, "Carrega outra vez: o perfil volta ao início (✦1 000 e kit inicial)")) return;
                profiles[editing] = Economy.NewProfile(P.slot, P.name, (ulong)DateTime.UtcNow.Ticks);
                Save(profiles[editing]); RefreshPreview(); Toast("Perfil recomeçado.");
            }, color: new Color(1f, 0.6f, 0.5f));
            Add("VOLTAR", "", () => { if (optionsReturn == Page.Pause) Go(Page.Pause); else Go(Page.Main); });
        }

        void ApplyOptions()
        {
            PlayerPrefs.SetFloat("rdd_shake", shake);
            PlayerPrefs.SetFloat("rdd_fov", fovExtra);
            PlayerPrefs.SetInt("rdd_vibration", vibration ? 1 : 0);
            foreach (var v in views) { v.chase.shakeScale = shake; v.chase.fovOffset = fovExtra + (views.Count > 1 ? -6f : 0f); }
            if (session != null) foreach (var r in session.Humans) if (r.input != null) r.input.vibration = vibration;
        }

        string InputPlan()
        {
            int pads = Gamepad.all.Count;
            return pads >= 2 ? "J1: comando 1 · J2: comando 2" : pads == 1 ? "J1: teclado · J2: comando" : "J1: teclado WASD · J2: teclado setas";
        }

        void BuildBriefing()
        {
            bool vs = briefingMode == GameMode.LocalVersus;
            title = vs ? "PVP LOCAL + BOTS" : "EXTRAÇÃO vs BOTS";
            subtitle = $"{courseTitle}  ·  {botCount} bots ({Difficulty(difficulty)})" + (vs ? $"  ·  {InputPlan()}" : "");
            bool ok = true;
            for (int k = 0; k < (vs ? 2 : 1); k++)
            {
                var p = profiles[k];
                var c = Catalog.ChassisOf(p.chassis);
                var errs = BuildValidator.Validate(p, p.chassis);
                ok &= errs.Count == 0;
                var ins = p.Item(p.insured);
                string load = string.Join(", ", p.loadout.Where(s => s.count > 0).Select(s => $"{Catalog.Consumable(s.id)?.name} ×{s.count}"));
                Header($"{p.name.ToUpperInvariant()} · {c.name}");
                int kk = k;
                Add("Build", $"{p.Equipped().Count} peças · {Fmt.Dust(p.BuildValue)} · em risco {Fmt.Dust(p.ValueAtRisk)}", () => { editing = kk; RefreshPreview(); Go(Page.Hangar); },
                    color: ShipBuilder.Paint(c.paint) * 1.6f, card: ChassisCard(c, p));
                Add("Segura", ins != null ? ins.Label : "nenhuma (tudo em risco)", () => { editing = kk; RefreshPreview(); Go(Page.Hangar); }, icon: ins != null ? Icons.Equipment(ins) : null);
                Add("Consumíveis", load.Length > 0 ? load : "nenhum", () => { editing = kk; RefreshPreview(); Go(Page.Hangar); });
                if (errs.Count > 0) Header("⚠ " + string.Join(" · ", errs));
            }
            Header("");
            var start = Add(vs ? "INICIAR PVP" : "INICIAR EXPEDIÇÃO", "", () => StartRace(briefingMode), color: new Color(1f, 0.75f, 0.3f), card: new Card
            {
                title = "REGRAS DA EXTRAÇÃO", color = new Color(1f, 0.6f, 0.3f),
                body = "Sem loot na pista: a corrida continua sempre corrida.\n\nSe fores destruído ou ficares sem combustível: perdes até 3 peças não seguradas (vão para o Expedition Pool) e os consumíveis que levas.\n\nNo fim, as peças reais do Pool são distribuídas pelos EXTRACTED, com prioridade às melhores posições. O Pool nunca inventa peças.\n\nNa corrida: L1 / 1-2-3 consumíveis · Triângulo / R reposiciona (penalização).",
            });
            start.enabled = ok;
            Add("Bots", $"‹ {botCount} ›", null, d => botCount = Mathf.Clamp(botCount + d, 1, 19));
            Add("Dificuldade", $"‹ {Difficulty(difficulty)} ›", null, d => difficulty = (difficulty + d + 3) % 3);
            Add("VOLTAR", "", () => Go(Page.Main));
        }

        void BuildPause()
        {
            title = "PAUSA";
            subtitle = mode == GameMode.Exploration ? "Exploração" : $"Expedition Pool {Fmt.Dust(session.pool.Valuation)}";
            Add("Continuar", "", ClosePause);
            if (mode == GameMode.Exploration)
            {
                Add("Recomeçar", "", () => StartRace(GameMode.Exploration));
                Add("Menu principal", "", () => BackToMenu());
            }
            else
                Add("Abandonar expedição", "ABANDONED: sem ✦ e peças em risco", () =>
                {
                    if (!Armed("abandon", "Carrega outra vez: abandonar NÃO protege as peças em risco")) return;
                    foreach (var r in session.Humans.ToList()) session.Abandon(r);
                    ClosePause();
                }, color: new Color(1f, 0.55f, 0.45f));
            Add("Opções", "", () => { optionsReturn = Page.Pause; Go(Page.Options); });
        }

        void BuildResults()
        {
            title = mode == GameMode.Exploration ? "EXPLORAÇÃO" : "RESULTADOS";
            subtitle = $"{courseTitle}  ·  Expedition Pool final {Fmt.Dust(session.pool.Valuation)} ({session.pool.Count} peças)";
            if (mode == GameMode.Exploration) Add("REPETIR", "", () => StartRace(GameMode.Exploration));
            Add("CONTINUAR", "", () => BackToMenu());
        }

        // ------------------------------------------------------------------ navegação

        void MenuInput()
        {
            BuildScreen();
            if (screen == Page.Cache && lastCache != null)
            {
                int total = lastCache.components.Count + lastCache.consumables.Count;
                bool all = (Time.unscaledTime - cacheOpened) / 0.32f >= total;
                if (GameInput.Confirm()) { if (!all) cacheOpened = -100f; else Go(Page.Market); }
                else if (GameInput.Back()) Go(Page.Market);
                return;
            }
            if (items.Count == 0) return;
            int ny = GameInput.NavY();
            if (ny != 0) GameAudio.Play("ui_move", 0.6f);
            if (ny != 0)
                for (int k = 0; k < items.Count; k++)
                {
                    sel = (sel + ny + items.Count) % items.Count;
                    if (Selectable(items[sel])) break;
                }
            var it = items[sel];
            int nx = GameInput.NavX();
            if (nx != 0 && it.lr != null && it.enabled) { GameAudio.Play("ui_move", 0.6f, 1.2f); it.lr(nx); }
            if (GameInput.Confirm() && it.enabled) { GameAudio.Play("ui_ok", 0.7f); it.ok?.Invoke(); }
            else if (GameInput.Back() || (screen == Page.Pause && GameInput.Pause())) { GameAudio.Play("ui_back", 0.7f); Back(); }
        }

        void Back()
        {
            switch (screen)
            {
                case Page.Pick: Go(Page.Hangar); break;
                case Page.Pause: ClosePause(); break;
                case Page.Options: Go(optionsReturn == Page.Pause ? Page.Pause : Page.Main); break;
                case Page.Results: case Page.Main: break;
                default: Go(Page.Main); break;
            }
        }
    }
}
