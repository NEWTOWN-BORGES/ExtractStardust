using System;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

namespace Stardust
{
    /// <summary>Code-only uGUI helpers (legacy Text so nothing has to be imported).</summary>
    public static class UIKit
    {
        public static readonly Color Accent = new Color(0.25f, 0.85f, 1f);
        public static readonly Color Warn = new Color(1f, 0.55f, 0.15f);
        public static readonly Color Danger = new Color(1f, 0.25f, 0.2f);
        public static readonly Color Good = new Color(0.35f, 1f, 0.5f);
        public static readonly Color PanelCol = new Color(0.03f, 0.05f, 0.08f, 0.82f);
        public static readonly Color Dim = new Color(0.65f, 0.72f, 0.8f);

        public static Canvas MakeCanvas(string name, int order, Transform parent = null)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            if (parent) go.transform.SetParent(parent, false);
            var c = go.GetComponent<Canvas>();
            c.renderMode = RenderMode.ScreenSpaceOverlay;
            c.sortingOrder = order;
            var sc = go.GetComponent<CanvasScaler>();
            sc.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            sc.referenceResolution = new Vector2(1280, 720);
            sc.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            sc.matchWidthOrHeight = 0.6f;
            return c;
        }

        public static RectTransform Rect(Transform parent, string name, Vector2 aMin, Vector2 aMax, Vector2 oMin = default, Vector2 oMax = default)
        {
            var go = new GameObject(name, typeof(RectTransform));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = aMin; rt.anchorMax = aMax;
            rt.offsetMin = oMin; rt.offsetMax = oMax;
            return rt;
        }

        /// <summary>Rect anchored at a point with a fixed size (pivot = anchor).</summary>
        public static RectTransform Box(Transform parent, string name, Vector2 anchor, Vector2 pos, Vector2 size)
        {
            var rt = Rect(parent, name, anchor, anchor);
            rt.pivot = anchor;
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
            return rt;
        }

        public static Image Panel(Transform parent, string name, Color c, Vector2 aMin, Vector2 aMax, Vector2 oMin = default, Vector2 oMax = default)
        {
            var rt = Rect(parent, name, aMin, aMax, oMin, oMax);
            var img = rt.gameObject.AddComponent<Image>();
            img.color = c;
            img.raycastTarget = false;
            return img;
        }

        public static Image PanelAt(Transform parent, string name, Color c, Vector2 anchor, Vector2 pos, Vector2 size)
        {
            var rt = Box(parent, name, anchor, pos, size);
            var img = rt.gameObject.AddComponent<Image>();
            img.color = c;
            img.raycastTarget = false;
            return img;
        }

        public static Text Label(Transform parent, string text, int size, TextAnchor align, Color c, Vector2 aMin, Vector2 aMax, Vector2 oMin = default, Vector2 oMax = default, bool outline = true)
        {
            var rt = Rect(parent, "T", aMin, aMax, oMin, oMax);
            var t = rt.gameObject.AddComponent<Text>();
            t.font = Res.Font;
            t.text = text;
            t.fontSize = size;
            t.alignment = align;
            t.color = c;
            t.raycastTarget = false;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            t.supportRichText = true;
            if (outline)
            {
                var o = rt.gameObject.AddComponent<Shadow>();
                o.effectColor = new Color(0, 0, 0, 0.8f);
                o.effectDistance = new Vector2(1.5f, -1.5f);
            }
            return t;
        }

        public static Text LabelAt(Transform parent, string text, int size, TextAnchor align, Color c, Vector2 anchor, Vector2 pos, Vector2 boxSize, bool outline = true)
        {
            var rt = Box(parent, "T", anchor, pos, boxSize);
            var t = rt.gameObject.AddComponent<Text>();
            t.font = Res.Font;
            t.text = text;
            t.fontSize = size;
            t.alignment = align;
            t.color = c;
            t.raycastTarget = false;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            t.supportRichText = true;
            if (outline)
            {
                var o = rt.gameObject.AddComponent<Shadow>();
                o.effectColor = new Color(0, 0, 0, 0.8f);
                o.effectDistance = new Vector2(1.5f, -1.5f);
            }
            return t;
        }

        public static Button Button(Transform parent, string label, Action onClick, Vector2 anchor, Vector2 pos, Vector2 size, int fontSize = 22)
        {
            var rt = Box(parent, "B_" + label, anchor, pos, size);
            var img = rt.gameObject.AddComponent<Image>();
            img.color = Color.white;
            var b = rt.gameObject.AddComponent<Button>();
            var cb = b.colors;
            cb.normalColor = new Color(0.08f, 0.14f, 0.2f, 0.92f);
            cb.highlightedColor = new Color(0.12f, 0.45f, 0.6f, 1f);
            cb.selectedColor = new Color(0.15f, 0.55f, 0.75f, 1f);
            cb.pressedColor = new Color(0.3f, 0.85f, 1f, 1f);
            cb.disabledColor = new Color(0.1f, 0.1f, 0.1f, 0.5f);
            cb.colorMultiplier = 1f;
            cb.fadeDuration = 0.08f;
            b.colors = cb;
            b.targetGraphic = img;
            if (onClick != null) b.onClick.AddListener(new UnityAction(onClick));
            var t = Label(rt, label, fontSize, TextAnchor.MiddleCenter, Color.white, Vector2.zero, Vector2.one);
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            var edge = PanelAt(rt, "edge", Accent, new Vector2(0, 0.5f), Vector2.zero, new Vector2(4, size.y));
            edge.raycastTarget = false;
            return b;
        }

        public static void SetLabel(Button b, string text)
        {
            var t = b.GetComponentInChildren<Text>();
            if (t) t.text = text;
        }

        public static string Hex(Color c) => ColorUtility.ToHtmlStringRGB(c);
        public static string Colorize(string s, Color c) => $"<color=#{Hex(c)}>{s}</color>";

        public static string Time(float t)
        {
            if (t < 0f) return "--:--.--";
            int m = (int)(t / 60f);
            float s = t - m * 60f;
            return $"{m:00}:{s:00.00}";
        }

        public static string Cr(int v) => v.ToString("N0", System.Globalization.CultureInfo.GetCultureInfo("pt-BR")) + " CR";
    }

    /// <summary>Horizontal bar made of two rects (no sprites needed).</summary>
    public class UIBar
    {
        public RectTransform root, fill;
        public Image fillImg, back;
        public Text label;

        public static UIBar Make(Transform parent, string name, Vector2 anchor, Vector2 pos, Vector2 size, Color col, string text = "")
        {
            var b = new UIBar();
            b.root = UIKit.Box(parent, name, anchor, pos, size);
            b.back = b.root.gameObject.AddComponent<Image>();
            b.back.color = new Color(0, 0, 0, 0.55f);
            b.back.raycastTarget = false;
            b.fill = UIKit.Rect(b.root, "fill", Vector2.zero, Vector2.one, new Vector2(2, 2), new Vector2(-2, -2));
            b.fillImg = b.fill.gameObject.AddComponent<Image>();
            b.fillImg.color = col;
            b.fillImg.raycastTarget = false;
            b.label = UIKit.Label(b.root, text, Mathf.RoundToInt(size.y * 0.62f), TextAnchor.MiddleLeft, Color.white, Vector2.zero, Vector2.one, new Vector2(8, 0), new Vector2(-6, 0));
            return b;
        }

        public void Set(float f)
        {
            f = Mathf.Clamp01(f);
            fill.anchorMax = new Vector2(f, 1f);
        }
    }
}
