using System.Collections.Generic;
using System.Linq;
using RedDust.Meta;
using RedDust.Presentation;
using UnityEngine;

namespace RedDust.Game
{
    /// <summary>
    /// Desenho (IMGUI escalado a 1080 p): lista de menus com ícones e cartão de informação, HUD de expedição por
    /// jogador (posição, casco, combustível, calor, boost, consumíveis, checkpoint, distância, Pool), revelação das
    /// Supply Caches, relatório "levei / perdi / ganhei" e classificação final. A paisagem continua a ser a prioridade.
    /// </summary>
    public partial class GameDirector
    {
        float W, H = 1080f;
        readonly Dictionary<string, GUIStyle> styles = new Dictionary<string, GUIStyle>();
        static readonly Color Panel = new Color(0.03f, 0.035f, 0.045f, 0.78f);
        static readonly Color Accent = new Color(1f, 0.62f, 0.25f);

        static Font uiFont;
        static bool uiFontTried;

        /// <summary>
        /// Fonte do sistema com cadeia de recurso: a fonte por omissão não tem o símbolo ✦ do Stardust (sai um quadrado);
        /// Segoe UI Symbol (Windows) e Noto Sans Symbols (Android) têm-no.
        /// </summary>
        static Font UiFont
        {
            get
            {
                if (uiFontTried) return uiFont;
                uiFontTried = true;
                try { uiFont = Font.CreateDynamicFontFromOSFont(new[] { "Segoe UI", "Segoe UI Symbol", "Arial", "Roboto", "Noto Sans", "Noto Sans Symbols", "Noto Sans Symbols 2", "Droid Sans" }, 32); }
                catch (System.Exception) { uiFont = null; }
                return uiFont;
            }
        }

        GUIStyle St(int size, FontStyle fs = FontStyle.Normal, TextAnchor a = TextAnchor.MiddleLeft, bool wrap = false)
        {
            string key = $"{size}{fs}{a}{wrap}";
            if (styles.TryGetValue(key, out var s)) return s;
            s = new GUIStyle(GUI.skin.label) { fontSize = size, fontStyle = fs, alignment = a, richText = true, wordWrap = wrap, clipping = TextClipping.Clip };
            if (UiFont != null) s.font = UiFont;
            s.normal.textColor = Color.white;
            styles[key] = s;
            return s;
        }

        static void Fill(Rect r, Color c)
        {
            var old = GUI.color; GUI.color = c;
            GUI.DrawTexture(r, Texture2D.whiteTexture);
            GUI.color = old;
        }

        static void Text(Rect r, string t, GUIStyle s, Color c)
        {
            var old = GUI.color; GUI.color = c;
            GUI.Label(r, t, s);
            GUI.color = old;
        }

        static void Shadowed(Rect r, string t, GUIStyle s, Color c)
        {
            Text(new Rect(r.x + 2, r.y + 2, r.width, r.height), t, s, new Color(0f, 0f, 0f, 0.65f * c.a));
            Text(r, t, s, c);
        }

        static void Bar(Rect r, float frac, Color c, string label = null, GUIStyle s = null)
        {
            Fill(r, new Color(0f, 0f, 0f, 0.55f));
            Fill(new Rect(r.x + 2, r.y + 2, (r.width - 4) * Mathf.Clamp01(frac), r.height - 4), c);
            if (label != null && s != null) Text(new Rect(r.x + 8, r.y, r.width - 16, r.height), label, s, Color.white);
        }

        void OnGUI()
        {
            if (course == null) return;
            float s = Screen.height / 1080f;
            W = Screen.width / s;
            GUI.matrix = Matrix4x4.TRS(Vector3.zero, Quaternion.identity, new Vector3(s, s, 1f));
            switch (screen)
            {
                case Page.Countdown:
                case Page.Race:
                    DrawHud();
                    break;
                case Page.Pause:
                    DrawHud();
                    Fill(new Rect(0, 0, W, H), new Color(0f, 0f, 0f, 0.45f));
                    DrawMenu(false);
                    break;
                case Page.Results:
                    DrawResults();
                    break;
                case Page.Cache:
                    DrawCache();
                    break;
                case Page.Report:
                    DrawMenu(false);
                    DrawReport(P.last, new Rect(W - 900, 130, 860, H - 200), P.name);
                    break;
                default:
                    DrawMenu(true);
                    break;
            }
            if (!string.IsNullOrEmpty(toast) && Time.unscaledTime < toastUntil)
            {
                var r = new Rect(W * 0.5f - 560, H - 120, 1120, 56);
                Fill(r, new Color(0.08f, 0.06f, 0.04f, 0.92f));
                Fill(new Rect(r.x, r.y, 6, r.height), Accent);
                Text(new Rect(r.x + 24, r.y, r.width - 40, r.height), toast, St(26), Color.white);
            }
        }

        // ------------------------------------------------------------------ menus

        void DrawMenu(bool withCard)
        {
            if (items.Count == 0) BuildScreen();
            Shadowed(new Rect(56, 34, W - 112, 64), title, St(52, FontStyle.Bold), Color.white);
            Shadowed(new Rect(58, 92, W - 116, 34), subtitle, St(24), new Color(1f, 0.86f, 0.66f));

            float x = 48, y = 140, w = 760, rowH = 54, headH = 38;
            float maxH = H - y - 60;
            // janela de itens à volta da seleção (listas longas na Mochila)
            float total = items.Sum(i => i.header ? headH : rowH);
            int first = 0;
            if (total > maxH)
            {
                float acc = 0f;
                for (int i = sel; i >= 0; i--) { acc += items[i].header ? headH : rowH; if (acc > maxH * 0.55f) { first = i + 1; break; } }
            }
            Fill(new Rect(x - 12, y - 12, w + 24, Mathf.Min(total, maxH) + 24), Panel);
            float cy = y;
            for (int i = first; i < items.Count; i++)
            {
                var it = items[i];
                float h = it.header ? headH : rowH;
                if (cy + h > y + maxH) { Text(new Rect(x, cy - 6, w, 24), "▼", St(20, FontStyle.Bold, TextAnchor.MiddleCenter), new Color(1f, 1f, 1f, 0.5f)); break; }
                var row = new Rect(x, cy, w, h - 4);
                if (it.header)
                {
                    Text(new Rect(x + 8, cy + 6, w - 16, h - 8), it.label, St(20, FontStyle.Bold), new Color(1f, 0.75f, 0.45f, 0.9f));
                }
                else
                {
                    bool selected = i == sel;
                    if (selected) { Fill(row, new Color(1f, 0.55f, 0.2f, 0.22f)); Fill(new Rect(x, cy, 6, h - 4), Accent); }
                    float tx = x + 18;
                    if (it.icon != null) { GUI.DrawTexture(new Rect(x + 14, cy + 3, h - 10, h - 10), it.icon); tx += h; }
                    var col = it.enabled ? it.color : new Color(0.5f, 0.5f, 0.52f);
                    Text(new Rect(tx, cy, w * 0.56f - (tx - x), h - 4), it.label, St(27, selected ? FontStyle.Bold : FontStyle.Normal), col);
                    Text(new Rect(x + w * 0.5f, cy, w * 0.5f - 16, h - 4), it.value, St(23, FontStyle.Normal, TextAnchor.MiddleRight), it.enabled ? new Color(0.9f, 0.9f, 0.92f) : col);
                    // rato/toque: clicar seleciona e confirma; setas laterais nos itens com valores
                    if (it.lr != null)
                    {
                        if (GUI.Button(new Rect(x + w * 0.5f - 6, cy, 60, h - 4), "", GUIStyle.none)) { sel = i; it.lr(-1); }
                        if (GUI.Button(new Rect(x + w - 60, cy, 60, h - 4), "", GUIStyle.none)) { sel = i; it.lr(1); }
                    }
                    if (GUI.Button(new Rect(x, cy, it.lr != null ? w * 0.5f - 6 : w, h - 4), "", GUIStyle.none))
                    {
                        if (sel == i && it.enabled) it.ok?.Invoke();
                        sel = i;
                    }
                }
                cy += h;
            }
            Text(new Rect(x, H - 50, W - 100, 30), $"{GameInput.BtnConfirm} escolher · {GameInput.BtnBack} voltar · ←/→ mudar valores · clica para escolher", St(20), new Color(1f, 1f, 1f, 0.55f));
            if (withCard && sel < items.Count && items[sel].card != null) DrawCard(items[sel].card, new Rect(W - 680, 140, 632, H - 220));
        }

        void DrawCard(Card c, Rect r)
        {
            Fill(r, Panel);
            Fill(new Rect(r.x, r.y, r.width, 6), c.color);
            float y = r.y + 22;
            if (c.icon != null) { GUI.DrawTexture(new Rect(r.x + 24, y, 132, 132), c.icon); }
            float tx = c.icon != null ? r.x + 176 : r.x + 24;
            Text(new Rect(tx, y, r.xMax - tx - 20, 50), c.title, St(36, FontStyle.Bold, TextAnchor.UpperLeft, true), Color.white);
            Text(new Rect(tx, y + 54, r.xMax - tx - 20, 34), c.subtitle, St(22, FontStyle.Bold, TextAnchor.UpperLeft), c.color);
            y += c.icon != null ? 150 : 96;
            float bodyH = c.now != null ? r.yMax - y - 330 : r.yMax - y - 20;
            Text(new Rect(r.x + 24, y, r.width - 48, bodyH), c.body, St(22, FontStyle.Normal, TextAnchor.UpperLeft, true), new Color(0.88f, 0.9f, 0.93f));
            if (c.now == null) return;
            // stats: barra atual e diferença do candidato (verde ganha, vermelho perde)
            float by = r.yMax - 316;
            for (int k = 0; k < StatInfo.CoreCount; k++)
            {
                var st = (Stat)k;
                float a = c.now[st], b = c.then != null ? c.then[st] : a;
                var row = new Rect(r.x + 24, by + k * 36, r.width - 48, 28);
                Text(new Rect(row.x, row.y, 170, 28), StatInfo.Name(st), St(20), new Color(0.8f, 0.82f, 0.86f));
                var bar = new Rect(row.x + 176, row.y + 6, row.width - 250, 16);
                Fill(bar, new Color(1f, 1f, 1f, 0.08f));
                Fill(new Rect(bar.x, bar.y, bar.width * Mathf.Min(a, b) / 100f, bar.height), new Color(0.85f, 0.87f, 0.9f));
                if (b > a) Fill(new Rect(bar.x + bar.width * a / 100f, bar.y, bar.width * (b - a) / 100f, bar.height), new Color(0.35f, 1f, 0.45f));
                if (b < a) Fill(new Rect(bar.x + bar.width * b / 100f, bar.y, bar.width * (a - b) / 100f, bar.height), new Color(1f, 0.35f, 0.3f));
                string delta = Mathf.Abs(b - a) >= 0.5f ? $"{b:0} ({(b > a ? "+" : "")}{b - a:0})" : $"{a:0}";
                Text(new Rect(bar.xMax + 8, row.y, 80, 28), delta, St(19, FontStyle.Bold, TextAnchor.MiddleRight), b > a ? new Color(0.5f, 1f, 0.55f) : b < a ? new Color(1f, 0.5f, 0.45f) : Color.white);
            }
        }

        // ------------------------------------------------------------------ Supply Cache

        void DrawCache()
        {
            Fill(new Rect(0, 0, W, H), new Color(0.02f, 0.02f, 0.03f, 0.88f));
            if (lastCache == null) return;
            Shadowed(new Rect(0, 40, W, 70), Economy.CacheName(lastCache.kind), St(56, FontStyle.Bold, TextAnchor.MiddleCenter), Color.white);
            var cards = new List<(Texture icon, string name, string sub, Color col, bool big)>();
            foreach (var c in lastCache.consumables)
            {
                var d = Catalog.Consumable(c);
                cards.Add((Icons.Consumable(c), d.name, "Consumível", Icons.ConsumableColor(d.kind, c), false));
            }
            foreach (var it in lastCache.components.OrderBy(i => i.rarity).ThenBy(i => i.value))
                cards.Add((Icons.Equipment(it), it.Label, $"{RarityInfo.Name(it.rarity)} · {it.Def.family} · {Fmt.Dust(it.value)}", Icons.RarityColor(it.rarity), it.rarity >= Rarity.Epic));
            int shown = Mathf.FloorToInt((Time.unscaledTime - cacheOpened) / 0.32f);
            float cw = 300, ch = 330, gap = 24;
            float x0 = (W - (5 * cw + 4 * gap)) * 0.5f, y0 = 150;
            for (int i = 0; i < cards.Count; i++)
            {
                var r = new Rect(x0 + (i % 5) * (cw + gap), y0 + (i / 5) * (ch + gap), cw, ch);
                if (i >= shown) { Fill(r, new Color(1f, 1f, 1f, 0.05f)); Text(r, "?", St(80, FontStyle.Bold, TextAnchor.MiddleCenter), new Color(1f, 1f, 1f, 0.2f)); continue; }
                var c = cards[i];
                Fill(r, Panel);
                if (c.big) Fill(new Rect(r.x - 4, r.y - 4, r.width + 8, r.height + 8), new Color(c.col.r, c.col.g, c.col.b, 0.25f + 0.15f * Mathf.Sin(Time.unscaledTime * 6f)));
                Fill(new Rect(r.x, r.y, r.width, 6), c.col);
                GUI.DrawTexture(new Rect(r.x + (cw - 150) / 2, r.y + 26, 150, 150), c.icon);
                Text(new Rect(r.x + 12, r.y + 190, cw - 24, 70), c.name, St(24, FontStyle.Bold, TextAnchor.UpperCenter, true), Color.white);
                Text(new Rect(r.x + 12, r.y + 262, cw - 24, 60), c.sub, St(19, FontStyle.Normal, TextAnchor.UpperCenter, true), c.col);
            }
            bool legendary = lastCache.components.Any(i => i.rarity == Rarity.Legendary);
            if (shown >= cards.Count && legendary)
                Shadowed(new Rect(0, y0 + 2 * (ch + gap) + 4, W, 60), "LENDÁRIO!", St(46, FontStyle.Bold, TextAnchor.MiddleCenter), Icons.RarityColor(Rarity.Legendary));
            Text(new Rect(0, H - 70, W, 40), shown >= cards.Count ? $"{GameInput.BtnConfirm} continuar · as peças estão na Mochila" : $"{GameInput.BtnConfirm} revelar tudo",
                St(24, FontStyle.Normal, TextAnchor.MiddleCenter), new Color(1f, 1f, 1f, 0.7f));
            if (GUI.Button(new Rect(0, 0, W, H), "", GUIStyle.none)) { if (shown < cards.Count) cacheOpened = -100f; else Go(Page.Market); }
        }

        // ------------------------------------------------------------------ relatório (levei / perdi / ganhei)

        void DrawReport(RaceReport rep, Rect r, string pilot)
        {
            Fill(r, Panel);
            if (rep == null) { Text(new Rect(r.x + 24, r.y + 20, r.width - 48, 40), "Ainda sem expedições.", St(26), Color.white); return; }
            Color stateCol = rep.state == RaceState.Extracted ? new Color(0.45f, 1f, 0.55f) : new Color(1f, 0.45f, 0.38f);
            string state = rep.state switch
            {
                RaceState.Extracted => rep.position == 1 ? "VICTORY / EXTRACTED" : "EXTRACTED",
                RaceState.Destroyed => "EXTRACTION FAILED · DESTROYED",
                RaceState.Stranded => "EXTRACTION FAILED · STRANDED",
                RaceState.Abandoned => "ABANDONED",
                _ => rep.state.ToString(),
            };
            Fill(new Rect(r.x, r.y, r.width, 6), stateCol);
            Text(new Rect(r.x + 24, r.y + 16, r.width - 48, 44), $"{pilot} — {state}", St(30, FontStyle.Bold), stateCol);
            Text(new Rect(r.x + 24, r.y + 58, r.width - 48, 30),
                $"{rep.position}.º de {rep.racers} · {RaceHud.FormatTime(rep.time)} · {rep.chassis} · casco {rep.hull:P0} · combustível {rep.fuel:P0} · {rep.course}", St(21), new Color(0.85f, 0.87f, 0.9f));
            var lines = new List<(string text, Color col, bool head)>();
            void Section(string head, List<ReportLine> list, Color baseCol, string empty)
            {
                lines.Add((head, Accent, true));
                if (list == null || list.Count == 0) lines.Add(("   " + empty, new Color(1f, 1f, 1f, 0.5f), false));
                else foreach (var l in list) lines.Add(("   " + l.text + (l.value > 0 ? $"   {Fmt.Dust(l.value)}" : ""), l.rarity > Rarity.Common ? Icons.RarityColor(l.rarity) : baseCol, false));
            }
            if (!string.IsNullOrEmpty(rep.insured)) lines.Add(($"Peça segurada: {rep.insured} — SALVA", new Color(0.55f, 0.95f, 1f), false));
            Section("LEVEI", rep.carried, Color.white, "nada");
            Section("PERDI", rep.lost, new Color(1f, 0.55f, 0.5f), "nada");
            Section("GANHEI (Expedition Pool)", rep.gained, new Color(0.5f, 1f, 0.6f), "nenhuma peça");
            Section("STARDUST", rep.stardust, new Color(1f, 0.85f, 0.5f), "—");
            lines.Add(($"TOTAL  +{Fmt.Dust(rep.stardustTotal)}   ·   Pool final {Fmt.Dust(rep.poolValue)}", new Color(1f, 0.85f, 0.45f), true));
            var view = new Rect(r.x + 16, r.y + 98, r.width - 32, r.height - 110);
            float lh = 32f;
            reportScroll = GUI.BeginScrollView(view, reportScroll, new Rect(0, 0, view.width - 24, lines.Count * lh + 10));
            for (int i = 0; i < lines.Count; i++)
                Text(new Rect(8, i * lh, view.width - 40, lh), lines[i].text, St(lines[i].head ? 23 : 21, lines[i].head ? FontStyle.Bold : FontStyle.Normal), lines[i].col);
            GUI.EndScrollView();
        }

        // ------------------------------------------------------------------ resultados

        void DrawResults()
        {
            Fill(new Rect(0, 0, W, H), new Color(0.02f, 0.02f, 0.03f, 0.7f));
            DrawMenu(false);
            var order = session.Classification();
            var table = new Rect(48, 300, 800, H - 360);
            if (mode != GameMode.Exploration)
            {
                Fill(table, Panel);
                float rh = Mathf.Min(34f, (table.height - 50) / Mathf.Max(1, order.Count));
                Text(new Rect(table.x + 16, table.y + 8, 760, 30), "POS   PILOTO              NAVE        ESTADO            TEMPO", St(19, FontStyle.Bold), Accent);
                for (int i = 0; i < order.Count; i++)
                {
                    var r = order[i];
                    float y = table.y + 44 + i * rh;
                    if (r.human) Fill(new Rect(table.x + 6, y, table.width - 12, rh - 2), new Color(1f, 0.6f, 0.2f, 0.18f));
                    var col = r.state == RaceState.Extracted ? Color.white : new Color(1f, 0.5f, 0.45f);
                    string t = r.state == RaceState.Extracted ? RaceHud.FormatTime(r.finishTime) : $"{r.endDistance / 1000f:0.0} km";
                    int won = session.poolAwards.TryGetValue(r.id, out var w) ? w.Count : 0;
                    Text(new Rect(table.x + 16, y, 60, rh), $"{r.position}", St(20, FontStyle.Bold), col);
                    Text(new Rect(table.x + 76, y, 210, rh), r.name, St(20, r.human ? FontStyle.Bold : FontStyle.Normal), r.human ? Accent : col);
                    Text(new Rect(table.x + 290, y, 120, rh), r.chassis.name, St(19), col);
                    Text(new Rect(table.x + 412, y, 190, rh), r.state.ToString().ToUpperInvariant(), St(19), col);
                    Text(new Rect(table.x + 600, y, 190, rh), t + (won > 0 ? $"  +{won} peça{(won > 1 ? "s" : "")}" : ""), St(19), col);
                }
            }
            int n = session.reports.Count;
            float rw = n > 1 ? (W - 940) / 2f - 12 : W - 940;
            for (int i = 0; i < n; i++)
            {
                var rep = session.reports[i];
                var pilot = session.Humans.ElementAtOrDefault(i);
                if (mode == GameMode.Exploration)
                {
                    var rr = new Rect(900, 140, W - 948, 220);
                    Fill(rr, Panel);
                    Text(new Rect(rr.x + 24, rr.y + 20, rr.width - 48, 60), $"Tempo: {RaceHud.FormatTime(rep.time)}", St(44, FontStyle.Bold), Color.white);
                    Text(new Rect(rr.x + 24, rr.y + 90, rr.width - 48, 100), "Exploração não tem risco nem prémios. Experimenta a EXTRAÇÃO para ganhar Stardust e peças.", St(24, FontStyle.Normal, TextAnchor.UpperLeft, true), new Color(0.9f, 0.9f, 0.92f));
                    continue;
                }
                DrawReport(rep, new Rect(900 + i * (rw + 24), 140, rw, H - 200), pilot != null ? pilot.name : "");
            }
        }

        // ------------------------------------------------------------------ HUD de expedição

        void DrawHud()
        {
            if (session == null) return;
            foreach (var v in views)
            {
                var n = v.norm;
                var vr = new Rect(n.x * W, (1f - n.y - n.height) * H, n.width * W, n.height * H);
                DrawPilotHud(v.racer, vr, views.Count > 1);
            }
            if (views.Count > 1) Fill(new Rect(0, H * 0.5f - 2, W, 4), new Color(0f, 0f, 0f, 0.8f));
        }

        void DrawPilotHud(Racer r, Rect vr, bool split)
        {
            float k = split ? 0.62f : 1f;
            int F(float size) => Mathf.RoundToInt(size * k);
            float pad = 40 * k;
            bool rules = session.Rules;

            // posição e pilotos ativos (canto superior esquerdo)
            if (mode != GameMode.Exploration)
            {
                Shadowed(new Rect(vr.x + pad, vr.y + pad * 0.6f, 400, 90 * k), $"P{r.position}<size={F(40)}>/{session.racers.Count}</size>", St(F(78), FontStyle.Bold), Color.white);
                Shadowed(new Rect(vr.x + pad + 4, vr.y + pad * 0.6f + 86 * k, 500, 34 * k), $"{session.ActiveCount} em pista", St(F(24)), new Color(1f, 1f, 1f, 0.8f));
            }
            // tempo, checkpoint, distância (topo ao centro)
            float t = r.state == RaceState.Extracted && r.finishTime >= 0f ? r.finishTime : session.time;
            Shadowed(new Rect(vr.center.x - 300, vr.y + pad * 0.5f, 600, 60 * k), RaceHud.FormatTime(t), St(F(48), FontStyle.Bold, TextAnchor.MiddleCenter), Color.white);
            float left = Mathf.Max(0f, course.Length - r.raceDistance) / 1000f;
            Shadowed(new Rect(vr.center.x - 400, vr.y + pad * 0.5f + 58 * k, 800, 34 * k), $"CHECKPOINT {r.checkpoint}/{session.checkpoints}   ·   faltam {left:0.0} km   ·   {r.chassis.name}",
                St(F(22), FontStyle.Normal, TextAnchor.MiddleCenter), new Color(1f, 1f, 1f, 0.85f));

            // velocidade e boost (canto inferior esquerdo)
            Shadowed(new Rect(vr.x + pad, vr.yMax - 170 * k, 420, 110 * k), $"{Units.ToKmh(r.Speed):0}<size={F(30)}> km/h</size>", St(F(96), FontStyle.Bold, TextAnchor.LowerLeft), Color.white);
            var c = r.craft;
            Color nitroCol = c.NitroLocked ? new Color(0.6f, 0.6f, 0.6f) : c.Boosting ? new Color(0.4f, 0.85f, 1f) : new Color(1f, 0.6f, 0.2f);
            Bar(new Rect(vr.x + pad, vr.yMax - 56 * k, 380 * k, 26 * k), c.Nitro, nitroCol, "BOOST", St(F(18), FontStyle.Bold));
            string passive = r.PassiveState;
            if (passive.Length > 0) Shadowed(new Rect(vr.x + pad, vr.yMax - 200 * k, 500, 30 * k), passive, St(F(20), FontStyle.Bold), new Color(0.6f, 0.95f, 1f));

            if (rules)
            {
                // casco / combustível / calor (canto inferior direito) e consumíveis
                float bw = 360 * k, bh = 26 * k, bx = vr.xMax - pad - bw, by = vr.yMax - 150 * k;
                float hf = r.HullFrac;
                Color hullCol = hf > 0.75f ? new Color(0.45f, 1f, 0.55f) : hf > 0.5f ? new Color(0.85f, 1f, 0.4f) : hf > 0.25f ? new Color(1f, 0.75f, 0.3f) : new Color(1f, 0.3f, 0.25f);
                string stage = hf > 0.75f ? "" : hf > 0.5f ? " · desgaste" : hf > 0.25f ? " · dano significativo" : hf > 0.1f ? " · CRÍTICO" : " · SOBREVIVÊNCIA";
                Bar(new Rect(bx, by, bw, bh), hf, hullCol, $"CASCO {hf * 100f:0}%{stage}", St(F(18), FontStyle.Bold));
                Bar(new Rect(bx, by + bh + 8 * k, bw, bh), r.fuel, r.fuel < 0.15f ? new Color(1f, 0.35f, 0.25f) : new Color(1f, 0.82f, 0.35f), $"COMBUSTÍVEL {r.fuel * 100f:0}%", St(F(18), FontStyle.Bold));
                Bar(new Rect(bx, by + 2 * (bh + 8 * k), bw, bh), r.heat / 100f, r.heat >= 85f ? new Color(1f, 0.3f, 0.2f) : new Color(1f, 0.5f, 0.3f), $"CALOR {r.heat:0}", St(F(18), FontStyle.Bold));
                float iw = 70 * k;
                for (int i = 0; i < r.slots.Count; i++)
                {
                    var s = r.slots[i];
                    var ir = new Rect(bx + bw - (r.slots.Count - i) * (iw + 10 * k), by - iw - 16 * k, iw, iw);
                    if (i == r.selected) Fill(new Rect(ir.x - 4, ir.y - 4, ir.width + 8, ir.height + 8), new Color(1f, 0.65f, 0.25f, 0.8f));
                    if (string.IsNullOrEmpty(s.id) || s.count <= 0) { Fill(ir, new Color(0f, 0f, 0f, 0.4f)); continue; }
                    GUI.DrawTexture(ir, Icons.Consumable(s.id));
                    Shadowed(new Rect(ir.x, ir.yMax - 26 * k, ir.width - 4, 26 * k), $"×{s.count}", St(F(20), FontStyle.Bold, TextAnchor.LowerRight), Color.white);
                    string key = r.input != null && r.input.pad != null ? (i == r.selected ? "L1" : "") : r.input != null && r.input.keys == KeyScheme.Right ? $"{(i + 8) % 10}" : $"{i + 1}";
                    if (key.Length > 0) Shadowed(new Rect(ir.x + 4, ir.y, ir.width, 24 * k), key, St(F(18), FontStyle.Bold), new Color(1f, 0.85f, 0.5f));
                }

                // Expedition Pool (avaliação) e notificações (canto superior direito)
                Shadowed(new Rect(vr.xMax - pad - 600, vr.y + pad * 0.6f, 600, 44 * k), $"EXPEDITION POOL {Fmt.Dust(session.pool.Valuation)}", St(F(30), FontStyle.Bold, TextAnchor.MiddleRight), new Color(1f, 0.85f, 0.45f));
                Text(new Rect(vr.xMax - pad - 600, vr.y + pad * 0.6f + 40 * k, 600, 26 * k), "avaliação das peças reais perdidas · distribuídas no fim", St(F(17), FontStyle.Normal, TextAnchor.MiddleRight), new Color(1f, 1f, 1f, 0.55f));
                // sensores (Nav/Utility): distância ao rival da frente e de trás — ajuda a decidir, não conduz
                if (r.spec.intel >= 5f)
                {
                    var ahead = session.racers.Where(o => o.Active && o != r && o.raceDistance > r.raceDistance).OrderBy(o => o.raceDistance).FirstOrDefault();
                    var behind = session.racers.Where(o => o.Active && o != r && o.raceDistance < r.raceDistance).OrderByDescending(o => o.raceDistance).FirstOrDefault();
                    string intel = $"SENSORES  ▲ {(ahead != null ? $"{ahead.name} +{ahead.raceDistance - r.raceDistance:0} m" : "—")}   ▼ {(behind != null ? $"{behind.name} -{r.raceDistance - behind.raceDistance:0} m" : "—")}";
                    Shadowed(new Rect(vr.center.x - 400, vr.y + pad * 0.5f + 92 * k, 800, 30 * k), intel, St(F(19), FontStyle.Normal, TextAnchor.MiddleCenter), new Color(0.55f, 1f, 0.85f));
                }
            }
            // notificações
            float fy = vr.y + pad * 0.6f + (rules ? 74 : 0) * k;
            int shown = 0;
            for (int i = session.feed.Count - 1; i >= 0 && shown < 5; i--)
            {
                var note = session.feed[i];
                if (Time.time > note.until || (note.player >= 0 && note.player != r.player)) continue;
                float a = Mathf.Clamp01((note.until - Time.time) / 0.6f);
                Shadowed(new Rect(vr.xMax - pad - 700, fy + shown * 34 * k, 700, 32 * k), note.text, St(F(22), FontStyle.Bold, TextAnchor.MiddleRight), new Color(note.color.r, note.color.g, note.color.b, a));
                shown++;
            }

            // centro: contagem, alertas e estados finais
            if (screen == Page.Countdown)
                Shadowed(new Rect(vr.x, vr.center.y - 120 * k, vr.width, 200 * k), Mathf.CeilToInt(Mathf.Max(0.01f, countdown)).ToString(), St(F(160), FontStyle.Bold, TextAnchor.MiddleCenter), Color.white);
            string alert = r.Alert();
            if (alert.Length > 0 && Mathf.Repeat(Time.time, 0.8f) < 0.55f)
                Shadowed(new Rect(vr.x, vr.center.y + 60 * k, vr.width, 60 * k), alert, St(F(40), FontStyle.Bold, TextAnchor.MiddleCenter), new Color(1f, 0.35f, 0.28f));
            if (!r.Active)
            {
                string big = r.state switch
                {
                    RaceState.Extracted => mode == GameMode.Exploration ? "CHEGADA" : r.position == 1 ? "VICTORY · EXTRACTED" : "EXTRACTED",
                    RaceState.Destroyed => "EXTRACTION FAILED",
                    RaceState.Stranded => "STRANDED",
                    _ => "ABANDONED",
                };
                Color col = r.state == RaceState.Extracted ? new Color(0.45f, 1f, 0.55f) : new Color(1f, 0.38f, 0.3f);
                Shadowed(new Rect(vr.x, vr.center.y - 110 * k, vr.width, 110 * k), big, St(F(88), FontStyle.Bold, TextAnchor.MiddleCenter), col);
                if (session.HumansDone)
                    Shadowed(new Rect(vr.x, vr.center.y + 10 * k, vr.width, 40 * k), $"{GameInput.BtnConfirm} resultados", St(F(26), FontStyle.Normal, TextAnchor.MiddleCenter), Color.white);
            }
        }
    }
}
