using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;

namespace Stardust
{
    public partial class GameApp
    {
        Canvas canvas;
        RectTransform uiRoot, hudLayer, screenLayer;
        GameObject screenGO;
        UIBar loadingBar;
        Text loadingText;
        TouchControls touch;
        Text touchA, touchB;
        string reselect;
        bool confirmReset;
        bool garageSplit;
        RectTransform mapRect, mapMarker;
        Vector2 mapCursor;

        void BuildUIRoot()
        {
            canvas = UIKit.MakeCanvas("UI", 10, transform);
            uiRoot = (RectTransform)canvas.transform;
            hudLayer = UIKit.Rect(uiRoot, "HudLayer", Vector2.zero, Vector2.one);
            screenLayer = UIKit.Rect(uiRoot, "Screens", Vector2.zero, Vector2.one);
            hudLayer.gameObject.AddComponent<SafeArea>();
            screenLayer.gameObject.AddComponent<SafeArea>();
            if (EventSystem.current == null)
            {
                var es = new GameObject("EventSystem", typeof(EventSystem), typeof(InputSystemUIInputModule));
                es.transform.SetParent(transform, false);
                es.GetComponent<InputSystemUIInputModule>().AssignDefaultActions();
            }
        }

        void HideAllScreens()
        {
            if (screenGO) Destroy(screenGO);
            screenGO = null;
        }

        RectTransform NewScreen(string name, Color bg)
        {
            HideAllScreens();
            var img = UIKit.Panel(screenLayer, name, bg, Vector2.zero, Vector2.one);
            img.raycastTarget = true;
            screenGO = img.gameObject;
            return img.rectTransform;
        }

        void Select(Button b)
        {
            if (b == null || EventSystem.current == null) return;
            EventSystem.current.SetSelectedGameObject(null);
            EventSystem.current.SetSelectedGameObject(b.gameObject);
        }

        void Click() { if (sfx) sfx.Ui(); }

        // ------------------------------------------------------------------ loading

        void ShowLoading(string text)
        {
            var r = NewScreen("Loading", new Color(0.02f, 0.03f, 0.05f, 1f));
            UIKit.LabelAt(r, "EXTRACT: STARDUST", 64, TextAnchor.MiddleCenter, Color.white, new Vector2(0.5f, 0.5f), new Vector2(0, 80), new Vector2(1000, 90));
            UIKit.LabelAt(r, "RACE. SURVIVE. EXTRACT.", 22, TextAnchor.MiddleCenter, UIKit.Accent, new Vector2(0.5f, 0.5f), new Vector2(0, 25), new Vector2(800, 40));
            loadingBar = UIBar.Make(r, "Bar", new Vector2(0.5f, 0.5f), new Vector2(0, -50), new Vector2(520, 16), UIKit.Accent);
            loadingBar.root.pivot = new Vector2(0.5f, 0.5f);
            loadingText = UIKit.LabelAt(r, text, 18, TextAnchor.MiddleCenter, UIKit.Dim, new Vector2(0.5f, 0.5f), new Vector2(0, -85), new Vector2(800, 30));
        }

        void SetLoading(float p) { if (loadingBar != null) loadingBar.Set(p); }
        void SetLoadingText(string s) { if (loadingText != null) loadingText.text = s + "…"; }
        void HideLoading() => HideAllScreens();

        // ------------------------------------------------------------------ main menu

        void ShowMenu()
        {
            state = State.Menu;
            hudLayer.gameObject.SetActive(false);
            var r = NewScreen("Menu", new Color(0, 0, 0, 0));
            var side = UIKit.Panel(r, "Side", new Color(0.02f, 0.03f, 0.05f, 0.78f), new Vector2(0, 0), new Vector2(0, 1), Vector2.zero, new Vector2(480, 0));
            UIKit.LabelAt(side.rectTransform, "EXTRACT:", 34, TextAnchor.UpperLeft, UIKit.Accent, new Vector2(0, 1), new Vector2(40, -34), new Vector2(420, 50));
            UIKit.LabelAt(side.rectTransform, "STARDUST", 62, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(36, -72), new Vector2(430, 80));
            UIKit.LabelAt(side.rectTransform, "RACE. SURVIVE. EXTRACT.", 18, TextAnchor.UpperLeft, new Color(1f, 0.75f, 0.3f), new Vector2(0, 1), new Vector2(40, -150), new Vector2(420, 30));

            var buttons = new List<Button>();
            float y = -190f;
            Button Add(string label, System.Action a)
            {
                var b = UIKit.Button(side.rectTransform, label, () => { Click(); a(); }, new Vector2(0, 1), new Vector2(40, y), new Vector2(400, 46), 19);
                y -= 53f;
                buttons.Add(b);
                return b;
            }
            Add("EXPEDIÇÃO — GRANDE CORRIDA", () => { garageSplit = false; pendingEventId = "expedicao"; ShowGarage(); });
            Add("CIRCUITOS E RETA DO SAL", () => ShowEvents(false));
            Add("EXPLORAR A ILHA", () => StartEvent(EventDef.Explore(world.data), false));
            if (!Mobile) Add("PVP LOCAL — TELA DIVIDIDA", () => ShowEvents(true));
            Add("MULTIPLAYER WI-FI", ShowLobby);
            Add("GARAGEM E SEGURO", () => { garageSplit = false; pendingEventId = "expedicao"; ShowGarage(); });
            Add("OPÇÕES", ShowOptions);
            Add("CONTROLES", ShowControls);
            if (!Mobile) Add("SAIR", Application.Quit);

            var save = SaveSystem.Current;
            UIKit.LabelAt(r,
                $"Créditos: {UIKit.Cr(save.credits)}   ·   XP: {save.xp}\nCorridas: {save.races}  ·  Extrações: {save.extractions}  ·  Vitórias: {save.wins}" +
                (save.bestTime > 0 ? $"\nMelhor expedição: {UIKit.Time(save.bestTime)}" : ""),
                16, TextAnchor.LowerRight, UIKit.Dim, new Vector2(1, 0), new Vector2(-20, 40), new Vector2(560, 80));
            UIKit.LabelAt(r, "v0.2 · Ilha de 24 km · Unity 6 URP", 14, TextAnchor.LowerRight, new Color(1, 1, 1, 0.6f), new Vector2(1, 0), new Vector2(-20, 14), new Vector2(600, 24));
            Select(buttons[0]);
        }

        void ShowEvents(bool split)
        {
            state = State.Events;
            var r = NewScreen("Events", new Color(0.02f, 0.03f, 0.05f, 0.88f));
            UIKit.LabelAt(r, split ? "PVP LOCAL — ESCOLHA A PROVA" : "PROVAS DA ILHA", 40, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(60, -40), new Vector2(900, 60));
            var buttons = new List<Button>();
            float y = -120f;
            void Row(EventDef e, System.Action go)
            {
                var b = UIKit.Button(r, e.name.ToUpperInvariant(), () => { Click(); go(); }, new Vector2(0, 1), new Vector2(60, y), new Vector2(520, 56), 21);
                UIKit.LabelAt(r, e.subtitle + (e.botCount > 0 ? $"  ·  {e.botCount} bots" : ""), 16, TextAnchor.MiddleLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(600, y), new Vector2(620, 56));
                buttons.Add(b);
                y -= 70f;
            }
            var exp = EventDef.Expedition(world.data);
            Row(exp, () => { garageSplit = split; pendingEventId = exp.id; ShowGarage(); });
            foreach (var ev in world.data.events)
            {
                var def = EventDef.FromWorld(ev);
                Row(def, () => StartEvent(def, split));
            }
            if (!split) Row(EventDef.Explore(world.data), () => StartEvent(EventDef.Explore(world.data), false));
            UIKit.LabelAt(r, "Circuitos e Reta do Sal: corridas de treino — sem perdas de peças, prêmios reduzidos.\nA Expedição é a prova de extração: porquinho, seguro, combustível e 15 bots.",
                16, TextAnchor.UpperLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(60, y - 10), new Vector2(1100, 60));
            var back = UIKit.Button(r, "VOLTAR", () => { Click(); ShowMenu(); }, new Vector2(0, 0), new Vector2(60, 30), new Vector2(240, 54));
            buttons.Add(back);
            Select(buttons[0]);
        }

        void ShowControls()
        {
            state = State.Options;
            var r = NewScreen("Controls", new Color(0.02f, 0.03f, 0.05f, 0.9f));
            UIKit.LabelAt(r, "CONTROLES", 40, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(60, -40), new Vector2(800, 60));
            string txt =
                "<b>A nave acelera sozinha.</b> Travão de mão + virar = DERRAPAR (fecha a curva sem perder velocidade e carrega um impulso).\n" +
                "Nitro ganha-se a derrapar, saltar e passar rente aos obstáculos (e recarrega devagar).\n\n" +
                "<b>Teclado</b>\nA D / ← →: virar · S / ↓ / ESPAÇO: travão de mão · SHIFT / W: nitro · Q E: itens · R: voltar ao caminho\nC: câmera (perseguição / cockpit) · V: centrar câmera · M: mapa (explorar) · ESC: pausa\n\n" +
                "<b>Comando PS4 / PS5 / Xbox</b>\nAnalógico esquerdo / D-pad: virar · L2 ou Quadrado: travão de mão · R2 ou X: nitro · L1 / R1: itens\nTriângulo: voltar ao caminho · Círculo: câmera · analógico direito: olhar à volta (R3 centra) · Options: pausa · Share: mapa\n\n" +
                "<b>PvP local (tela dividida)</b>\nJogador 1: W A S D + SHIFT esq. (ou o 1.º comando) · Jogador 2: setas + SHIFT dir. (ou o 2.º comando)\n\n" +
                "<b>Android (toque)</b>\n< > virar · TRAVAR (derrapar) · NITRO · botões dos itens · aceleração automática\n\n" +
                "<b>Expedição</b>\nChegar à extração = EXTRACTED (preserva a nave). Destruída = perde até 3 peças não seguradas para o PORQUINHO.\nO porquinho é dividido por quem extrai, pela classificação. A peça segurada volta sempre.";
            UIKit.LabelAt(r, txt, 17, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(60, -110), new Vector2(1160, 560));
            var back = UIKit.Button(r, "VOLTAR", () => { Click(); ShowMenu(); }, new Vector2(0, 0), new Vector2(60, 30), new Vector2(240, 54));
            Select(back);
        }

        // ------------------------------------------------------------------ garage

        void ShowGarage()
        {
            state = State.Garage;
            hudLayer.gameObject.SetActive(false);
            var save = SaveSystem.Current;
            save.EnsureBaseKit();
            var r = NewScreen("Garage", new Color(0, 0, 0, 0));
            var left = UIKit.Panel(r, "Left", new Color(0.02f, 0.03f, 0.05f, 0.86f), new Vector2(0, 0), new Vector2(0, 1), Vector2.zero, new Vector2(760, 0));
            var L = left.rectTransform;
            UIKit.LabelAt(L, "GARAGEM · STARDUST PORT", 30, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(30, -20), new Vector2(700, 44));
            UIKit.LabelAt(L, $"Créditos {UIKit.Cr(save.credits)}  ·  XP {save.xp}  ·  Inventário {save.inventory.Count} peças", 16, TextAnchor.UpperLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(32, -62), new Vector2(700, 26));

            var allButtons = new List<Button>();
            for (int i = 0; i < 6; i++)
            {
                var slot = (Slot)i;
                float y = -100f - i * 84f;
                var list = save.OfSlot(slot);
                var cur = save.Equipped(slot);
                int idx = Mathf.Max(0, list.IndexOf(cur));
                UIKit.LabelAt(L, Catalog.SlotName[i].ToUpper(), 15, TextAnchor.UpperLeft, UIKit.Accent, new Vector2(0, 1), new Vector2(30, y), new Vector2(160, 24));
                int si = i;
                var prev = UIKit.Button(L, "<", () => { Click(); CycleItem(si, -1); }, new Vector2(0, 1), new Vector2(30, y - 24), new Vector2(44, 44), 22);
                prev.name = $"prev{i}";
                var next = UIKit.Button(L, ">", () => { Click(); CycleItem(si, 1); }, new Vector2(0, 1), new Vector2(470, y - 24), new Vector2(44, 44), 22);
                next.name = $"next{i}";
                var col = cur != null ? Catalog.RarityColor[cur.rarity] : Color.white;
                string nm = cur != null ? $"{cur.DisplayName}  <size=13>[{Catalog.RarityName[cur.rarity]} · ≈{UIKit.Cr(cur.value)}]</size>" : "-";
                UIKit.LabelAt(L, nm, 19, TextAnchor.MiddleLeft, col, new Vector2(0, 1), new Vector2(84, y - 24), new Vector2(380, 26));
                string desc = Catalog.Describe(cur);
                var leg = Catalog.LegendaryEffect(cur);
                if (leg != null) desc += "\n" + UIKit.Colorize(leg, Catalog.RarityColor[4]);
                UIKit.LabelAt(L, desc + $"   <color=#8899AA>({idx + 1}/{list.Count})</color>", 13, TextAnchor.UpperLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(84, y - 50), new Vector2(390, 40));
                bool insured = cur != null && save.insuredId == cur.id;
                var ins = UIKit.Button(L, insured ? "SEGURADA" : "Segurar", () => { Click(); ToggleInsurance(si); }, new Vector2(0, 1), new Vector2(530, y - 24), new Vector2(200, 44), 17);
                ins.name = $"ins{i}";
                if (insured) ins.GetComponent<Image>().color = new Color(0.4f, 1f, 0.55f);
                allButtons.Add(prev); allButtons.Add(next); allButtons.Add(ins);
            }

            // right column
            var right = UIKit.Panel(r, "Right", new Color(0.02f, 0.03f, 0.05f, 0.86f), new Vector2(1, 0), new Vector2(1, 1), new Vector2(-470, 0), Vector2.zero);
            var R = right.rectTransform;
            var eq = save.EquippedArray();
            var st = ShipStats.From(eq);
            UIKit.LabelAt(R, "VESPA — PODRACER", 20, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(24, -20), new Vector2(420, 30));
            void Stat(string name, float v, float y, string val)
            {
                UIKit.LabelAt(R, name, 14, TextAnchor.MiddleLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(24, y), new Vector2(150, 22));
                var b = UIBar.Make(R, name, new Vector2(0, 1), new Vector2(170, y - 2), new Vector2(200, 16), UIKit.Accent, "");
                b.Set(v);
                UIKit.LabelAt(R, val, 13, TextAnchor.MiddleLeft, Color.white, new Vector2(0, 1), new Vector2(376, y), new Vector2(96, 22));
            }
            float top = Hovercraft.MaxSpeed * st.topSpeed / ShipStats.Base.topSpeed;
            Stat("Velocidade", 0.3f + (st.topSpeed - 68f) / 12f, -60f, $"{top * 3.6f:0} km/h");
            Stat("Aceleração", (st.accel - 20f) / 12f, -86f, $"{st.accel / ShipStats.Base.accel * 100f:0}%");
            Stat("Aderência", (st.grip - 3f) / 2f, -112f, $"{st.grip / ShipStats.Base.grip * 100f:0}%");
            Stat("Blindagem", (1.1f - st.armor) / 0.5f, -138f, $"-{(1f - st.armor) * 100f:0}% dano");
            Stat("Nitro", (st.nitroRegen - 9f) / 10f, -164f, $"+{2.2f * st.nitroRegen / ShipStats.Base.nitroRegen:0.0}/s");
            Stat("Combustível", (st.fuelCap - 80f) / 40f, -190f, $"{st.fuelCap:0} · uso {st.fuelUse * 100f:0}%");

            UIKit.LabelAt(R, "ITENS (2 espaços × 2 unidades)", 16, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(24, -228), new Vector2(420, 26));
            for (int k = 0; k < 2; k++)
            {
                int kk = k;
                int type = k == 0 ? save.consA : save.consB;
                string key = k == 0 ? "A (Q / L1)" : "B (E / R1)";
                var b = UIKit.Button(R, $"{key}: {Catalog.ConsumableName[type]}  ({Catalog.ConsumableCost[type]} CR/uso)", () => { Click(); CycleConsumable(kk); },
                    new Vector2(0, 1), new Vector2(24, -258 - k * 52), new Vector2(420, 44), 15);
                b.name = $"cons{k}";
                allButtons.Add(b);
            }

            var insuredItem = save.Find(save.insuredId);
            int riskCount = 0, riskValue = 0;
            foreach (var it in eq) if (it != null && it.id != save.insuredId) { riskCount++; riskValue += it.value; }
            var exp = EventDef.Expedition(world.data);
            var sb = new StringBuilder();
            sb.AppendLine("<b>RESUMO DE ENTRADA — Expedição</b>");
            sb.AppendLine($"Grande Corrida ≈ {exp.lengthKm:0} km · {exp.gates.Length} portões · {world.data.sections.Length} trechos com atalhos · 15 bots");
            sb.AppendLine($"Peça segurada: {(insuredItem != null ? UIKit.Colorize(insuredItem.DisplayName, Catalog.RarityColor[insuredItem.rarity]) + $" (taxa {UIKit.Cr(Mathf.RoundToInt(insuredItem.value * 0.1f))})" : UIKit.Colorize("nenhuma", UIKit.Warn))}");
            sb.AppendLine($"Em risco se destruída: até {Mathf.Min(IslandRace.LossCount, riskCount)} de {riskCount} peças (≈ {UIKit.Cr(riskValue)})");
            sb.AppendLine("Postos de combustível nos portões 10 e 20.");
            UIKit.LabelAt(R, sb.ToString(), 14, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(24, -372), new Vector2(430, 150));

            var start = UIKit.Button(R, garageSplit ? "INICIAR (2 JOGADORES)" : "INICIAR EXPEDIÇÃO", () => { Click(); StartEvent(EventById(pendingEventId ?? "expedicao"), garageSplit); }, new Vector2(0, 0), new Vector2(24, 96), new Vector2(420, 60), 24);
            start.GetComponent<Image>().color = new Color(0.5f, 1f, 0.7f);
            start.name = "start";
            var back = UIKit.Button(R, "VOLTAR", () => { Click(); ShowMenu(); }, new Vector2(0, 0), new Vector2(24, 28), new Vector2(200, 50), 18);
            back.name = "back";
            allButtons.Add(start); allButtons.Add(back);

            Button sel = start;
            if (reselect != null) foreach (var b in allButtons) if (b.name == reselect) sel = b;
            reselect = null;
            Select(sel);
        }

        void CycleItem(int slot, int dir)
        {
            var save = SaveSystem.Current;
            var list = save.OfSlot((Slot)slot);
            if (list.Count == 0) return;
            var cur = save.Equipped((Slot)slot);
            int idx = list.IndexOf(cur);
            idx = (idx + dir + list.Count) % list.Count;
            bool wasInsured = cur != null && save.insuredId == cur.id;
            save.equipped[slot] = list[idx].id;
            if (wasInsured) save.insuredId = list[idx].id;
            SaveSystem.Save();
            reselect = (dir < 0 ? "prev" : "next") + slot;
            ShowGarage();
        }

        void ToggleInsurance(int slot)
        {
            var save = SaveSystem.Current;
            var cur = save.Equipped((Slot)slot);
            if (cur == null) return;
            save.insuredId = save.insuredId == cur.id ? "" : cur.id;
            SaveSystem.Save();
            reselect = "ins" + slot;
            ShowGarage();
        }

        void CycleConsumable(int k)
        {
            var save = SaveSystem.Current;
            if (k == 0) save.consA = (save.consA + 1) % 2; else save.consB = (save.consB + 1) % 2;
            SaveSystem.Save();
            reselect = "cons" + k;
            ShowGarage();
        }

        // ------------------------------------------------------------------ options

        void ShowOptions()
        {
            state = State.Options;
            var r = NewScreen("Options", new Color(0.02f, 0.03f, 0.05f, 0.9f));
            UIKit.LabelAt(r, "OPÇÕES", 40, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(60, -40), new Vector2(600, 60));
            var buttons = new List<Button>();
            float y = -120f;
            Button Row(string label, string value, System.Action act)
            {
                UIKit.LabelAt(r, label, 20, TextAnchor.MiddleLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(60, y), new Vector2(360, 50));
                var b = UIKit.Button(r, value, () => { Click(); act(); }, new Vector2(0, 1), new Vector2(430, y), new Vector2(420, 50), 20);
                b.name = "opt" + buttons.Count;
                buttons.Add(b);
                y -= 62f;
                return b;
            }
            string[] q = { "Leve (celulares)", "Equilibrada", "Alta (PC)" };
            Row("Qualidade gráfica", q[quality], () => { quality = (quality + 1) % 3; SaveSettings(); ApplyQuality(); ReShowOptions(0); });
            Row("Volume geral", $"{Mathf.RoundToInt(volume * 100)}%", () => { volume = volume >= 0.99f ? 0f : Mathf.Min(1f, volume + 0.1f); SaveSettings(); ReShowOptions(1); });
            Row("Música", $"{Mathf.RoundToInt(musicVol * 100)}%", () => { musicVol = musicVol >= 0.99f ? 0f : Mathf.Min(1f, musicVol + 0.15f); SaveSettings(); ReShowOptions(2); });
            Row("Tremor de câmera", shake ? "Ligado" : "Reduzido", () => { shake = !shake; SaveSettings(); ReShowOptions(3); });
            string[] cams = { "Perseguição", "Cockpit" };
            Row("Câmera inicial", cams[Mathf.Clamp(camView, 0, 1)], () => { camView = (camView + 1) % 2; SaveSettings(); ReShowOptions(4); });
            Row("Progresso", confirmReset ? "CONFIRMAR: apagar tudo?" : "Apagar progresso", () =>
            {
                if (confirmReset) { SaveSystem.Reset(); confirmReset = false; }
                else confirmReset = true;
                ReShowOptions(5);
            });
            UIKit.LabelAt(r, "A qualidade muda as sombras, a distância de visão, a relva e a resolução. A Leve é a indicada para o Galaxy A15.",
                15, TextAnchor.UpperLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(60, y - 6), new Vector2(900, 50));
            var back = UIKit.Button(r, "VOLTAR", () => { Click(); confirmReset = false; ShowMenu(); }, new Vector2(0, 0), new Vector2(60, 30), new Vector2(240, 54));
            buttons.Add(back);
            Button sel = buttons[0];
            if (reselect != null) foreach (var b in buttons) if (b.name == reselect) sel = b;
            reselect = null;
            Select(sel);
        }

        void ReShowOptions(int i)
        {
            reselect = "opt" + i;
            ShowOptions();
        }

        void ApplyQuality()
        {
            if (world != null) { world.quality = quality; world.ApplyQuality(); }
            if (atmo != null) atmo.SetQuality(quality);
            foreach (var rig in rigs) if (rig) rig.cam.farClipPlane = FarClip;
            if (menuRig) menuRig.cam.farClipPlane = FarClip;
        }

        void UpdateMenus(float dt)
        {
            if (state == State.Garage || state == State.Options || state == State.Events || state == State.Lobby)
            {
                if (MenuInput.AnyBack()) { Click(); confirmReset = false; if (state == State.Lobby) LeaveLobby(); ShowMenu(); }
            }
            if (state == State.Lobby) UpdateLobby(dt);
            if (EventSystem.current != null && EventSystem.current.currentSelectedGameObject == null && screenGO != null)
            {
                // keep gamepad navigation alive after a mouse click on empty space
                if (UnityEngine.InputSystem.Gamepad.current != null && UnityEngine.InputSystem.Gamepad.current.wasUpdatedThisFrame)
                {
                    var b = screenGO.GetComponentInChildren<Button>();
                    if (b) Select(b);
                }
            }
        }

        // ------------------------------------------------------------------ pause

        void ShowPause()
        {
            hudLayer.gameObject.SetActive(false);
            var r = NewScreen("Pause", new Color(0, 0, 0, 0.7f));
            UIKit.LabelAt(r, "PAUSA", 52, TextAnchor.MiddleCenter, Color.white, new Vector2(0.5f, 0.5f), new Vector2(0, 210), new Vector2(600, 70));
            float y = 110f;
            Button B(string label, System.Action a)
            {
                var b = UIKit.Button(r, label, () => { Click(); a(); }, new Vector2(0.5f, 0.5f), new Vector2(-190, y), new Vector2(380, 54));
                b.GetComponent<RectTransform>().pivot = new Vector2(0, 0.5f);
                y -= 64f;
                return b;
            }
            var c = B("CONTINUAR", Resume);
            B("VOLTAR AO CAMINHO", () => { Resume(); foreach (var h in humans) if (h.state == PilotState.Racing) race.RequestRecover(h); });
            if (race != null && race.def.kind == EventKind.Explore) B("MAPA E VIAGEM RÁPIDA", ShowMap);
            if (!mpRace || (net != null && net.isHost)) B("REINICIAR", Restart);
            B("SAIR PARA O MENU", QuitToMenu);
            if (race != null && race.def.economy)
                UIKit.LabelAt(r, "Sair a meio = ABANDONED: sem perdas e sem prêmios.", 16, TextAnchor.MiddleCenter, UIKit.Dim, new Vector2(0.5f, 0.5f), new Vector2(0, y - 20), new Vector2(900, 30));
            Select(c);
        }

        void UpdatePause()
        {
            foreach (var h in humans)
                if (h.input.pause) { Resume(); return; }
        }

        // ------------------------------------------------------------------ map (Explore: travel)

        void ShowMap()
        {
            state = State.Map;
            Time.timeScale = 0f;
            hudLayer.gameObject.SetActive(false);
            var r = NewScreen("Map", new Color(0.01f, 0.02f, 0.03f, 0.92f));
            float size = Mathf.Min(Screen.height / canvas.scaleFactor - 80f, 680f);
            var img = UIKit.PanelAt(r, "Map", Color.white, new Vector2(0.5f, 0.5f), new Vector2(-size * 0.5f - 120f, -size * 0.5f), new Vector2(size, size));
            img.gameObject.SetActive(false);
            var raw = UIKit.Rect(r, "MapImg", new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f));
            raw.sizeDelta = new Vector2(size, size);
            raw.anchoredPosition = new Vector2(-120f, 0f);
            var ri = raw.gameObject.AddComponent<RawImage>();
            ri.texture = IslandHud.MapTexture;
            ri.raycastTarget = true;
            mapRect = raw;
            var half = world.data.size * 0.5f;
            foreach (var z in world.data.zones)
            {
                var p = new Vector2(z.c[0] / world.data.size, z.c[1] / world.data.size) * size;
                UIKit.LabelAt(raw, z.name, 13, TextAnchor.MiddleCenter, new Color(1f, 1f, 1f, 0.85f), new Vector2(0.5f, 0.5f), p - new Vector2(80, 10), new Vector2(160, 20));
            }
            var me = humans[0];
            var mp = new Vector2(me.craft.position.x / world.data.size, me.craft.position.z / world.data.size) * size;
            var dot = UIKit.PanelAt(raw, "Me", Color.white, new Vector2(0.5f, 0.5f), mp - new Vector2(7, 7), new Vector2(14, 14));
            mapCursor = mp;
            mapMarker = UIKit.PanelAt(raw, "Cursor", UIKit.Warn, new Vector2(0.5f, 0.5f), mp - new Vector2(9, 9), new Vector2(18, 18)).rectTransform;
            mapMarker.localEulerAngles = new Vector3(0, 0, 45f);
            UIKit.LabelAt(r, "MAPA DA ILHA", 34, TextAnchor.UpperLeft, Color.white, new Vector2(1, 1), new Vector2(-440, -40), new Vector2(420, 50));
            UIKit.LabelAt(r, "Toque / clique no mapa, ou mova o cursor com o analógico e carregue em X / Enter para viajar para a estrada mais próxima.\n\nCírculo / Esc: voltar.",
                16, TextAnchor.UpperLeft, UIKit.Dim, new Vector2(1, 1), new Vector2(-440, -100), new Vector2(400, 200));
            var back = UIKit.Button(r, "VOLTAR", () => { Click(); CloseMap(); }, new Vector2(1, 0), new Vector2(-300, 30), new Vector2(240, 54));
            Select(back);
        }

        void CloseMap()
        {
            mapRect = null;
            Resume();
        }

        void UpdateMap(float dt)
        {
            if (mapRect == null) { CloseMap(); return; }
            if (MenuInput.AnyBack()) { CloseMap(); return; }
            float size = mapRect.sizeDelta.x;
            var pad = UnityEngine.InputSystem.Gamepad.current;
            if (pad != null)
            {
                var s = pad.leftStick.ReadValue();
                if (s.sqrMagnitude > 0.02f) mapCursor += s * dt * size * 0.45f;
            }
            var kb = UnityEngine.InputSystem.Keyboard.current;
            if (kb != null)
            {
                var k = Vector2.zero;
                if (kb.leftArrowKey.isPressed || kb.aKey.isPressed) k.x -= 1f;
                if (kb.rightArrowKey.isPressed || kb.dKey.isPressed) k.x += 1f;
                if (kb.upArrowKey.isPressed || kb.wKey.isPressed) k.y += 1f;
                if (kb.downArrowKey.isPressed || kb.sKey.isPressed) k.y -= 1f;
                mapCursor += k * dt * size * 0.45f;
            }
            // mouse / touch
            Vector2 screen = default;
            bool press = false;
            var m = UnityEngine.InputSystem.Mouse.current;
            if (m != null && m.leftButton.wasPressedThisFrame) { screen = m.position.ReadValue(); press = true; }
            var ts = UnityEngine.InputSystem.Touchscreen.current;
            if (ts != null && ts.primaryTouch.press.wasPressedThisFrame) { screen = ts.primaryTouch.position.ReadValue(); press = true; }
            bool go = false;
            if (press && RectTransformUtility.ScreenPointToLocalPointInRectangle(mapRect, screen, null, out var local) && mapRect.rect.Contains(local))
            {
                mapCursor = local;
                go = true;
            }
            mapCursor.x = Mathf.Clamp(mapCursor.x, -size * 0.5f, size * 0.5f);
            mapCursor.y = Mathf.Clamp(mapCursor.y, -size * 0.5f, size * 0.5f);
            mapMarker.anchoredPosition = mapCursor - new Vector2(9, 9);
            if ((pad != null && pad.buttonSouth.wasPressedThisFrame) || (kb != null && kb.enterKey.wasPressedThisFrame)) go = true;
            if (go)
            {
                var w = mapCursor / size * world.data.size;
                CloseMap();
                TravelTo(w);
            }
        }

        // ------------------------------------------------------------------ results

        void ShowResults()
        {
            state = State.Results;
            hudLayer.gameObject.SetActive(false);
            foreach (var rig in rigs) rig.SetMode(ChaseCam.Mode.Orbit);
            var r = NewScreen("Results", new Color(0, 0, 0, 0.35f));
            var me = humans[0];
            var pr = result.For(me);
            bool eco = result.economy;
            var left = UIKit.Panel(r, "Left", new Color(0.02f, 0.03f, 0.05f, 0.9f), new Vector2(0, 0), new Vector2(0, 1), new Vector2(20, 20), new Vector2(700, -20)).rectTransform;
            var col = pr.extracted ? UIKit.Good : pr.status == "EXTRACTION FAILED" ? UIKit.Danger : UIKit.Warn;
            UIKit.LabelAt(left, $"{pr.place}º de {race.racers.Count}  |  {UIKit.Colorize(pr.status, col)}", 38, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(24, -16), new Vector2(640, 54));
            string sub = pr.extracted
                ? $"{currentEvent.name} · Tempo {UIKit.Time(pr.time)}  ·  Integridade {Mathf.CeilToInt(me.integrity)}%" + (eco ? $"  ·  Combustível {Mathf.CeilToInt(me.fuel)}%" : "")
                : me.state == PilotState.Destroyed ? $"Destruída: {me.destroyCause}  ·  {me.distance / 1000f:0.0} km percorridos" : $"Não chegou ao fim ({me.distance / 1000f:0.0} km)";
            UIKit.LabelAt(left, sub, 16, TextAnchor.UpperLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(26, -70), new Vector2(640, 24));

            var sb = new StringBuilder();
            if (eco)
            {
                sb.AppendLine("<b>DESTINO DO EQUIPAMENTO</b>");
                if (pr.insured != null)
                    sb.AppendLine(pr.insuranceUsed ? $"Seguro: {Item(pr.insured)} voltou para a garagem (mesma instância)." : $"Seguro: {Item(pr.insured)} protegida (não foi necessária).");
                if (pr.lost.Count > 0)
                {
                    sb.Append(UIKit.Colorize("Perdido para o porquinho: ", UIKit.Danger));
                    for (int i = 0; i < pr.lost.Count; i++) sb.Append((i > 0 ? ", " : "") + Item(pr.lost[i]));
                    sb.AppendLine();
                }
                int keep = 0;
                foreach (var it in pr.preserved) if (pr.insured == null || it.id != pr.insured.id) keep++;
                sb.AppendLine($"Preservado: {keep + (pr.insured != null ? 1 : 0)} peça(s).");
                sb.AppendLine();
                sb.AppendLine("<b>LOOT DO PORQUINHO</b>");
                if (!pr.extracted) sb.AppendLine("Sem acesso à distribuição: só quem extrai recebe peças.");
                else if (pr.loot.Count == 0) sb.AppendLine(result.pool.Count == 0 ? "Porquinho vazio — ninguém perdeu peças elegíveis." : "Não sobraram peças para a sua posição (sem duplicação).");
                else
                {
                    foreach (var it in pr.loot) sb.AppendLine($"+ {Item(it)}  <color=#AABBCC>(≈{UIKit.Cr(it.value)}, de {it.owner})</color>");
                    sb.AppendLine($"Valor estimado recebido ≈ {UIKit.Cr(pr.LootValue)} <color=#8899AA>(estimativa, não é saldo)</color>");
                }
                sb.AppendLine();
            }
            else sb.AppendLine("<b>CORRIDA DE TREINO</b> — sem perdas de peças nem porquinho.\n");
            sb.AppendLine("<b>BALANÇO DE CRÉDITOS</b>");
            sb.AppendLine($"Prêmio de classificação  {Sign(pr.creditsPlace)}");
            sb.AppendLine($"Proezas  {Sign(pr.creditsMedals)}" + (pr.medals.Count > 0 ? $"  <color=#FFD27A>({string.Join(", ", pr.medals)})</color>" : ""));
            if (eco) sb.AppendLine($"Seguro  {Sign(-pr.costInsurance)}   ·   Itens  {Sign(-pr.costConsumables)}   ·   Reparo  {Sign(-pr.costRepair)}");
            else sb.AppendLine($"Itens  {Sign(-pr.costConsumables)}");
            sb.AppendLine($"<b>Total  {Sign(pr.net)}</b>   ·   XP +{pr.xp}");
            if (me.pilot.persistent) sb.AppendLine($"Saldo atual: {UIKit.Cr(SaveSystem.Current.credits)}");
            else sb.AppendLine("<color=#8899AA>Jogador convidado: sem persistência.</color>");
            foreach (var g in result.grantedBase) sb.AppendLine(UIKit.Colorize(g, UIKit.Accent));
            if (humans.Count > 1)
            {
                var p2 = result.For(humans[1]);
                sb.AppendLine();
                sb.AppendLine($"<b>Jogador 2:</b> {p2.place}º · {p2.status} · loot {p2.loot.Count} itens · {Sign(p2.net)}");
            }
            UIKit.LabelAt(left, sb.ToString(), 16, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(26, -104), new Vector2(640, 520));

            var right = UIKit.Panel(r, "Right", new Color(0.02f, 0.03f, 0.05f, 0.9f), new Vector2(1, 0), new Vector2(1, 1), new Vector2(-540, 20), new Vector2(-20, -20)).rectTransform;
            UIKit.LabelAt(right, "CLASSIFICAÇÃO", 22, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(20, -14), new Vector2(480, 30));
            var tb = new StringBuilder();
            foreach (var p in result.pilots)
            {
                string st = p.extracted ? UIKit.Colorize(eco ? "EXTRACTED" : "CHEGOU", UIKit.Good) : p.status == "EXTRACTION FAILED" ? UIKit.Colorize("DESTRUÍDO", UIKit.Danger) : UIKit.Colorize(p.status, UIKit.Warn);
                string t = p.extracted ? UIKit.Time(p.time) : "";
                string nm = p.racer.pilot.human ? UIKit.Colorize(p.racer.pilot.name, UIKit.Accent) : p.racer.pilot.name;
                string loot = p.loot.Count > 0 ? $" +{p.loot.Count}" : "";
                tb.AppendLine($"{p.place,2}. {nm}  {st} {t}{loot}");
            }
            UIKit.LabelAt(right, tb.ToString(), 14, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(20, -48), new Vector2(500, 420));
            if (eco)
            {
                int distributed = 0;
                foreach (var p in result.pilots) distributed += p.loot.Count;
                UIKit.LabelAt(right,
                    $"<b>PORQUINHO</b>: {result.pool.Count} peças reais perdidas · valor estimado ≈ {UIKit.Cr(result.poolValue)}\nDistribuídas: {distributed} · Em custódia: {result.residual.Count}\n<color=#8899AA>{result.algorithm}</color>",
                    13, TextAnchor.LowerLeft, Color.white, new Vector2(0, 0), new Vector2(20, 90), new Vector2(500, 90));
            }
            var g1 = UIKit.Button(right, "GARAGEM", () => { Click(); QuitToMenu(); ShowGarage(); }, new Vector2(0, 0), new Vector2(20, 22), new Vector2(150, 52), 18);
            if (!mpRace || (net != null && net.isHost)) UIKit.Button(right, "CORRER DE NOVO", () => { Click(); Restart(); }, new Vector2(0, 0), new Vector2(180, 22), new Vector2(190, 52), 18);
            UIKit.Button(right, "MENU", () => { Click(); QuitToMenu(); }, new Vector2(0, 0), new Vector2(380, 22), new Vector2(120, 52), 18);
            Select(g1);
        }

        static string Item(ItemInst it) => UIKit.Colorize(it.DisplayName, Catalog.RarityColor[it.rarity]) + $" <size=12>[{Catalog.RarityTag[it.rarity]}]</size>";
        static string Sign(int v) => v > 0 ? UIKit.Colorize("+" + UIKit.Cr(v), UIKit.Good) : v < 0 ? UIKit.Colorize("-" + UIKit.Cr(-v), UIKit.Danger) : "0 CR";

        // ------------------------------------------------------------------ touch controls (Android)

        void BuildTouchControls()
        {
            var layer = UIKit.Rect(hudLayer, "Touch", Vector2.zero, Vector2.one);
            touch = layer.gameObject.AddComponent<TouchControls>();
            RectTransform Btn(string label, Vector2 anchor, Vector2 pos, Vector2 size, Color c, out Text t)
            {
                var img = UIKit.PanelAt(layer, label, c, anchor, pos, size);
                t = UIKit.Label(img.rectTransform, label, 26, TextAnchor.MiddleCenter, Color.white, Vector2.zero, Vector2.one);
                return img.rectTransform;
            }
            var dim = new Color(1, 1, 1, 0.12f);
            touch.left = Btn("<", new Vector2(0, 0), new Vector2(24, 24), new Vector2(170, 170), dim, out _);
            touch.right = Btn(">", new Vector2(0, 0), new Vector2(210, 24), new Vector2(170, 170), dim, out _);
            touch.boost = Btn("NITRO", new Vector2(1, 0), new Vector2(-24, 24), new Vector2(190, 170), new Color(0.3f, 0.75f, 1f, 0.25f), out _);
            touch.brake = Btn("TRAVAR", new Vector2(1, 0), new Vector2(-228, 24), new Vector2(160, 130), new Color(1f, 0.3f, 0.2f, 0.2f), out _);
            if (race.def.kind != EventKind.Explore)
            {
                touch.slotA = Btn("A", new Vector2(1, 0), new Vector2(-24, 212), new Vector2(150, 84), new Color(0.4f, 1f, 0.6f, 0.2f), out touchA);
                touch.slotB = Btn("B", new Vector2(1, 0), new Vector2(-184, 212), new Vector2(150, 84), new Color(1f, 0.8f, 0.3f, 0.2f), out touchB);
                touchA.fontSize = touchB.fontSize = 17;
            }
            else touch.map = Btn("MAPA", new Vector2(1, 0), new Vector2(-24, 212), new Vector2(150, 84), dim, out _);
            touch.pause = Btn("II", new Vector2(1, 1), new Vector2(-24, -90), new Vector2(84, 64), dim, out _);
            if (humans.Count > 0) humans[0].input.touch = touch;
        }

        void LateUpdate()
        {
            if (touch != null && touchA != null && humans.Count > 0)
            {
                var p = humans[0].pilot;
                touchA.text = $"{(p.cons[0] == Consumable.RepairGel ? "REPARAR" : "COMBUST.")}\nx{p.consCount[0]}";
                touchB.text = $"{(p.cons[1] == Consumable.RepairGel ? "REPARAR" : "COMBUST.")}\nx{p.consCount[1]}";
            }
        }
    }
}
