using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace RedDust.Presentation
{
    /// <summary>
    /// HUD de corrida contido (o terreno é a prioridade visual): velocidade, cronómetro, zona, comando detetado,
    /// dicas de controlos, mensagens centrais (contagem, fim), ecrã de título e menu de pausa navegável.
    /// </summary>
    public class RaceHud : MonoBehaviour
    {
        Text speed, speedUnit, timer, best, zone, device, hints, center, sub, state, titleMain, titleSub, titlePrompt;
        GameObject titlePanel, pausePanel;
        readonly List<Text> pauseItems = new List<Text>();
        Text pauseTitle, pauseFoot;
        float centerUntil;
        Font font;

        public static RaceHud Create()
        {
            var go = new GameObject("RaceHud");
            var hud = go.AddComponent<RaceHud>();
            hud.Build();
            return hud;
        }

        void Build()
        {
            font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            var canvas = gameObject.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;
            var scaler = gameObject.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = 0.5f;

            speed = Label("Speed", new Vector2(0.5f, 0f), new Vector2(0, 70), 104, TextAnchor.LowerCenter, FontStyle.Bold);
            speedUnit = Label("Unit", new Vector2(0.5f, 0f), new Vector2(0, 40), 26, TextAnchor.LowerCenter);
            speedUnit.text = "km/h";
            state = Label("State", new Vector2(0.5f, 0f), new Vector2(0, 190), 28, TextAnchor.LowerCenter, FontStyle.Bold);
            timer = Label("Timer", new Vector2(0.5f, 1f), new Vector2(0, -40), 48, TextAnchor.UpperCenter, FontStyle.Bold);
            best = Label("Best", new Vector2(0.5f, 1f), new Vector2(0, -100), 24, TextAnchor.UpperCenter);
            zone = Label("Zone", new Vector2(0f, 1f), new Vector2(40, -40), 26, TextAnchor.UpperLeft);
            device = Label("Device", new Vector2(1f, 1f), new Vector2(-40, -40), 22, TextAnchor.UpperRight);
            hints = Label("Hints", new Vector2(0f, 0f), new Vector2(40, 40), 22, TextAnchor.LowerLeft);
            center = Label("Center", new Vector2(0.5f, 0.5f), new Vector2(0, 80), 128, TextAnchor.MiddleCenter, FontStyle.Bold);
            sub = Label("Sub", new Vector2(0.5f, 0.5f), new Vector2(0, -40), 34, TextAnchor.MiddleCenter);

            titlePanel = Panel("Title", new Color(0.05f, 0.02f, 0.01f, 0.62f));
            titleMain = Label("TitleMain", new Vector2(0.5f, 0.5f), new Vector2(0, 150), 110, TextAnchor.MiddleCenter, FontStyle.Bold, titlePanel.transform);
            titleMain.text = "EXTRACT: STARDUST";
            titleSub = Label("TitleSub", new Vector2(0.5f, 0.5f), new Vector2(0, 50), 36, TextAnchor.MiddleCenter, FontStyle.Normal, titlePanel.transform);
            titleSub.text = "RED DUST DIVIDE  ·  Laboratório de física (M1)\nRACE. SURVIVE. EXTRACT.";
            titlePrompt = Label("TitlePrompt", new Vector2(0.5f, 0.5f), new Vector2(0, -110), 34, TextAnchor.MiddleCenter, FontStyle.Bold, titlePanel.transform);

            pausePanel = Panel("Pause", new Color(0.03f, 0.02f, 0.02f, 0.72f));
            pauseTitle = Label("PauseTitle", new Vector2(0.5f, 0.5f), new Vector2(0, 260), 64, TextAnchor.MiddleCenter, FontStyle.Bold, pausePanel.transform);
            pauseTitle.text = "PAUSA";
            for (int i = 0; i < 8; i++)
                pauseItems.Add(Label("Item" + i, new Vector2(0.5f, 0.5f), new Vector2(0, 150 - i * 62), 38, TextAnchor.MiddleCenter, FontStyle.Normal, pausePanel.transform));
            pauseFoot = Label("PauseFoot", new Vector2(0.5f, 0f), new Vector2(0, 80), 24, TextAnchor.LowerCenter, FontStyle.Normal, pausePanel.transform);
            pausePanel.SetActive(false);
        }

        Text Label(string name, Vector2 anchor, Vector2 pos, int size, TextAnchor align, FontStyle style = FontStyle.Normal, Transform parent = null)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent != null ? parent : transform, false);
            var rt = go.AddComponent<RectTransform>();
            rt.anchorMin = rt.anchorMax = anchor;
            rt.pivot = new Vector2(anchor.x, anchor.y);
            rt.anchoredPosition = pos;
            rt.sizeDelta = new Vector2(1500, size * 4.2f);
            var t = go.AddComponent<Text>();
            t.font = font;
            t.fontSize = size;
            t.fontStyle = style;
            t.alignment = align;
            t.color = new Color(1f, 0.96f, 0.9f);
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            t.supportRichText = true;
            var sh = go.AddComponent<Shadow>();
            sh.effectColor = new Color(0f, 0f, 0f, 0.75f);
            sh.effectDistance = new Vector2(2f, -2f);
            return t;
        }

        GameObject Panel(string name, Color c)
        {
            var go = new GameObject(name);
            go.transform.SetParent(transform, false);
            var rt = go.AddComponent<RectTransform>();
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
            go.AddComponent<Image>().color = c;
            return go;
        }

        // ------------------------------------------------------------------ API

        public void ShowTitle(bool on)
        {
            titlePanel.SetActive(on);
            if (on) titlePrompt.text = $"Prima <color=#ffcf6a>{GameInput.BtnConfirm}</color> para começar";
        }

        public void ShowRaceHud(bool on)
        {
            speed.gameObject.SetActive(on); speedUnit.gameObject.SetActive(on); timer.gameObject.SetActive(on);
            best.gameObject.SetActive(on); zone.gameObject.SetActive(on); state.gameObject.SetActive(on);
        }

        public void Center(string big, string small, float seconds)
        {
            center.text = big; sub.text = small;
            centerUntil = seconds > 0f ? Time.unscaledTime + seconds : float.MaxValue;
        }

        public void ClearCenter() { center.text = ""; sub.text = ""; }

        public void Race(float kmh, float time, float bestTime, string zoneName, bool boosting, bool drifting, bool airborne)
        {
            speed.text = $"{kmh:0}";
            timer.text = FormatTime(time);
            best.text = bestTime > 0f ? $"melhor {FormatTime(bestTime)}" : "";
            zone.text = zoneName;
            state.text = boosting ? "<color=#7fe8ff>BOOST</color>" : drifting ? "<color=#ffcf6a>DERRAPAGEM</color>" : airborne ? "<color=#ffffff>NO AR</color>" : "";
        }

        public void Device(string text) => device.text = text;
        public void Hints(string text) => hints.text = text;

        public void Pause(bool on, IList<string> items, int selected, string foot)
        {
            pausePanel.SetActive(on);
            if (!on) return;
            for (int i = 0; i < pauseItems.Count; i++)
            {
                bool used = i < items.Count;
                pauseItems[i].gameObject.SetActive(used);
                if (!used) continue;
                pauseItems[i].text = i == selected ? $"<color=#ffcf6a>›  {items[i]}  ‹</color>" : items[i];
                pauseItems[i].fontStyle = i == selected ? FontStyle.Bold : FontStyle.Normal;
            }
            pauseFoot.text = foot;
        }

        void Update()
        {
            if (Time.unscaledTime > centerUntil) ClearCenter();
        }

        public static string FormatTime(float t)
        {
            int m = (int)(t / 60f);
            float s = t - m * 60f;
            return $"{m:00}:{s:00.00}";
        }
    }
}
