using System;
using System.Collections.Generic;
using RedDust.Meta;
using UnityEngine;

namespace RedDust.Game
{
    /// <summary>
    /// Ícones gerados por código (campos de distância com anti-aliasing): um por consumível e um por família de
    /// equipamento, com moldura na cor da raridade. Sem ficheiros de arte; o passe de UI substitui-os mais tarde.
    /// </summary>
    public static class Icons
    {
        const int N = 96;
        static readonly Dictionary<string, Texture2D> cache = new Dictionary<string, Texture2D>();

        public static Color RarityColor(Rarity r)
        {
            uint c = RarityInfo.Rgb[(int)r];
            return new Color(((c >> 16) & 255) / 255f, ((c >> 8) & 255) / 255f, (c & 255) / 255f);
        }

        public static Color ConsumableColor(ConsumableKind k, string id) => id switch
        {
            "coolant" => new Color(0.35f, 0.88f, 1f),
            "foam" => new Color(0.42f, 1f, 0.5f),
            "fuel" => new Color(1f, 0.68f, 0.18f),
            "stab" => new Color(0.74f, 0.52f, 1f),
            "surge" => new Color(1f, 0.92f, 0.3f),
            "nanogel" => new Color(1f, 0.38f, 0.55f),
            _ => Color.white,
        };

        public static Texture2D Consumable(string id)
        {
            var def = Catalog.Consumable(id);
            if (def == null) return Empty();
            var col = ConsumableColor(def.kind, id);
            return Make("c_" + id, col * 0.85f, col, id switch
            {
                "coolant" => p => Min(Circle(p, new Vector2(0f, -0.18f), 0.42f), Poly(p, new Vector2(0f, 0.72f), new Vector2(-0.37f, 0.02f), new Vector2(0.37f, 0.02f))),
                "foam" => p => Min(Box(p, Vector2.zero, new Vector2(0.17f, 0.56f), 0.05f), Box(p, Vector2.zero, new Vector2(0.56f, 0.17f), 0.05f)),
                "fuel" => p => Min(Box(p, new Vector2(0f, -0.12f), new Vector2(0.38f, 0.56f), 0.08f), Box(p, new Vector2(0.14f, 0.55f), new Vector2(0.14f, 0.1f), 0.03f)),
                "stab" => p => Min(Min(Ring(p, Vector2.zero, 0.5f, 0.07f), Segment(p, new Vector2(-0.78f, 0f), new Vector2(0.78f, 0f), 0.07f)), Circle(p, Vector2.zero, 0.16f)),
                "surge" => p => Poly(p, new Vector2(0.18f, 0.86f), new Vector2(-0.42f, 0.04f), new Vector2(-0.04f, 0.04f), new Vector2(-0.2f, -0.86f), new Vector2(0.44f, -0.02f), new Vector2(0.06f, -0.02f)),
                _ => p => Min(Min(Box(p, new Vector2(-0.12f, -0.1f), new Vector2(0.14f, 0.48f), 0.04f), Box(p, new Vector2(-0.12f, -0.1f), new Vector2(0.48f, 0.14f), 0.04f)),
                                Poly(p, new Vector2(0.55f, 0.82f), new Vector2(0.42f, 0.55f), new Vector2(0.55f, 0.28f), new Vector2(0.68f, 0.55f))),
            });
        }

        public static Texture2D Equipment(EquipmentInstance it) => it == null ? Empty() : Family(it.Def?.family ?? Meta.Family.Utility, it.rarity);

        public static Texture2D Family(Family f, Rarity r)
        {
            var frame = RarityColor(r);
            var fg = r == Rarity.Legendary ? new Color(1f, 0.85f, 0.4f) : new Color(0.92f, 0.94f, 0.97f);
            return Make($"f_{f}_{r}", frame, fg, f switch
            {
                Meta.Family.Engine => p => Min(Min(Box(p, new Vector2(-0.08f, -0.05f), new Vector2(0.5f, 0.32f), 0.06f), Box(p, new Vector2(-0.08f, 0.42f), new Vector2(0.28f, 0.1f), 0.03f)),
                                             Box(p, new Vector2(0.55f, -0.05f), new Vector2(0.14f, 0.2f), 0.03f)),
                Meta.Family.Propulsion => p => Min(Ring(p, new Vector2(0f, 0.25f), 0.32f, 0.09f), Poly(p, new Vector2(-0.22f, -0.1f), new Vector2(0.22f, -0.1f), new Vector2(0f, -0.85f))),
                Meta.Family.Wings => p => Poly(p, new Vector2(0f, 0.75f), new Vector2(0.85f, -0.35f), new Vector2(0.15f, -0.2f), new Vector2(0f, -0.6f), new Vector2(-0.15f, -0.2f), new Vector2(-0.85f, -0.35f)),
                Meta.Family.Tail => p => Min(Poly(p, new Vector2(-0.45f, -0.55f), new Vector2(0.55f, -0.55f), new Vector2(0.25f, 0.8f), new Vector2(0.05f, 0.8f)), Box(p, new Vector2(0f, -0.62f), new Vector2(0.7f, 0.08f), 0.03f)),
                Meta.Family.Armor => p => Poly(p, new Vector2(0f, 0.82f), new Vector2(0.62f, 0.55f), new Vector2(0.55f, -0.15f), new Vector2(0f, -0.85f), new Vector2(-0.55f, -0.15f), new Vector2(-0.62f, 0.55f)),
                Meta.Family.Reactor => p => Min(Circle(p, Vector2.zero, 0.24f), Min(Ring(p, Vector2.zero, 0.5f, 0.06f), Ring(p, Vector2.zero, 0.74f, 0.04f))),
                Meta.Family.Cooling => p => Min(Min(Box(p, new Vector2(0f, 0.45f), new Vector2(0.6f, 0.09f), 0.03f), Box(p, Vector2.zero, new Vector2(0.6f, 0.09f), 0.03f)),
                                              Min(Box(p, new Vector2(0f, -0.45f), new Vector2(0.6f, 0.09f), 0.03f), Box(p, new Vector2(-0.68f, 0f), new Vector2(0.06f, 0.6f), 0.02f))),
                _ => p => Min(Min(Max(Ring(p, new Vector2(0f, -0.3f), 0.5f, 0.06f), -p.y + 0.0f), Max(Ring(p, new Vector2(0f, -0.3f), 0.8f, 0.06f), -p.y + 0.05f)),
                              Segment(p, new Vector2(0f, -0.3f), new Vector2(0f, -0.85f), 0.07f)),
            });
        }

        /// <summary>Supply Cache: caixa com tampa e cintas (cinzenta, azul ou roxa conforme o nível).</summary>
        public static Texture2D Cache(CacheKind k)
        {
            var col = k == CacheKind.Elite ? RarityColor(Rarity.Epic) : k == CacheKind.Advanced ? RarityColor(Rarity.Rare) : new Color(0.8f, 0.8f, 0.78f);
            return Make("cache_" + k, col, col, p => Max(Box(p, new Vector2(0f, -0.12f), new Vector2(0.7f, 0.5f), 0.06f),
                -Min(Box(p, new Vector2(0f, 0.22f), new Vector2(0.72f, 0.04f), 0f), Min(Box(p, new Vector2(-0.32f, -0.12f), new Vector2(0.05f, 0.52f), 0f), Box(p, new Vector2(0.32f, -0.12f), new Vector2(0.05f, 0.52f), 0f)))));
        }

        public static Texture2D Empty() => Make("empty", new Color(0.35f, 0.37f, 0.4f), new Color(0.45f, 0.47f, 0.5f), p => Ring(p, Vector2.zero, 0.4f, 0.04f));

        // ------------------------------------------------------------------ rasterização

        static Texture2D Make(string key, Color frame, Color fg, Func<Vector2, float> sdf)
        {
            if (cache.TryGetValue(key, out var t) && t != null) return t;
            t = new Texture2D(N, N, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp, name = "Icon_" + key };
            var px = new Color[N * N];
            float aa = 2.2f / N;
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    var p = new Vector2((x + 0.5f) / N * 2f - 1f, (y + 0.5f) / N * 2f - 1f);
                    // fundo: quadrado arredondado escuro com moldura da raridade
                    float dOuter = Box(p, Vector2.zero, new Vector2(0.94f, 0.94f), 0.2f);
                    float aOuter = 1f - Mathf.Clamp01(dOuter / aa + 0.5f);
                    float dInner = Box(p, Vector2.zero, new Vector2(0.86f, 0.86f), 0.16f);
                    float aInner = 1f - Mathf.Clamp01(dInner / aa + 0.5f);
                    var bg = Color.Lerp(new Color(0.06f, 0.07f, 0.09f), new Color(0.13f, 0.12f, 0.12f), (p.y + 1f) * 0.5f);
                    var c = Color.Lerp(frame * 0.9f, bg, aInner);
                    // símbolo (encolhido para caber dentro da moldura) com brilho suave à volta
                    float d = sdf(p / 0.72f) * 0.72f;
                    float a = 1f - Mathf.Clamp01(d / aa + 0.5f);
                    float glow = Mathf.Exp(-Mathf.Max(0f, d) * 14f) * 0.35f;
                    c = Color.Lerp(c, fg, Mathf.Max(a, glow * aInner));
                    c.a = aOuter;
                    px[y * N + x] = c;
                }
            t.SetPixels(px);
            t.Apply(false, true);
            cache[key] = t;
            return t;
        }

        static float Min(float a, float b) => Mathf.Min(a, b);
        static float Max(float a, float b) => Mathf.Max(a, b);
        static float Circle(Vector2 p, Vector2 c, float r) => (p - c).magnitude - r;
        static float Ring(Vector2 p, Vector2 c, float r, float w) => Mathf.Abs((p - c).magnitude - r) - w;

        static float Box(Vector2 p, Vector2 c, Vector2 half, float round)
        {
            Vector2 q = new Vector2(Mathf.Abs(p.x - c.x), Mathf.Abs(p.y - c.y)) - half + new Vector2(round, round);
            return new Vector2(Mathf.Max(q.x, 0f), Mathf.Max(q.y, 0f)).magnitude + Mathf.Min(Mathf.Max(q.x, q.y), 0f) - round;
        }

        static float Segment(Vector2 p, Vector2 a, Vector2 b, float r)
        {
            Vector2 pa = p - a, ba = b - a;
            float h = Mathf.Clamp01(Vector2.Dot(pa, ba) / Vector2.Dot(ba, ba));
            return (pa - ba * h).magnitude - r;
        }

        /// <summary>Distância com sinal a um polígono simples (negativa dentro).</summary>
        static float Poly(Vector2 p, params Vector2[] v)
        {
            float d = float.MaxValue;
            bool inside = false;
            for (int i = 0, j = v.Length - 1; i < v.Length; j = i++)
            {
                Vector2 e = v[i] - v[j], w = p - v[j];
                float h = Mathf.Clamp01(Vector2.Dot(w, e) / Vector2.Dot(e, e));
                d = Mathf.Min(d, (w - e * h).magnitude);
                if ((v[i].y > p.y) != (v[j].y > p.y) && p.x < (v[j].x - v[i].x) * (p.y - v[i].y) / (v[j].y - v[i].y) + v[i].x) inside = !inside;
            }
            return inside ? -d : d;
        }
    }
}
