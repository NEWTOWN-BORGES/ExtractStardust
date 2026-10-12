using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Stardust
{
    /// <summary>
    /// Per-player HUD of an island race (full screen or half for split-screen): place, time, zone, gates and
    /// distance, rotating minimap with the other ships, integrity/fuel/nitro, the piggy bank, consumables,
    /// messages, warnings and speed/damage overlays.
    /// </summary>
    public class IslandHud
    {
        public RectTransform root;
        readonly IslandRace race;
        readonly Racer me;
        readonly bool mobile, split;
        Text posText, posOf, timeText, zoneText, speedText, poolTitle, poolText, msgText, subText, feedText, gateText, distText;
        Text slotAText, slotBText, warnText, nitroGainText;
        UIBar integ, fuel, nitro, repairBar;
        RawImage streaks, damage, mapImg;
        RectTransform mapWindow, mapContent, arrow, nextDot;
        readonly List<RectTransform> dots = new List<RectTransform>();
        float damageFlash, msgT, subT, warnBlink, gainT;
        string lastWarn;
        readonly List<string> feed = new List<string>();
        readonly List<float> feedT = new List<float>();
        float poolPulse;
        int lastPoolCount;
        int zone = -1;
        public float mapSpan = 2600f;     // metres across the minimap window
        static Texture2D mapTex;

        public IslandHud(RectTransform parent, IslandRace race, Racer me, bool mobile, bool split)
        {
            this.race = race;
            this.me = me;
            this.mobile = mobile;
            this.split = split;
            root = UIKit.Rect(parent, "HUD_" + me.pilot.name, Vector2.zero, Vector2.one);
            Build();
        }

        public static Texture2D MapTexture
        {
            get
            {
                if (mapTex == null) mapTex = Resources.Load<Texture2D>(IslandData.Root + "minimap");
                return mapTex;
            }
        }

        void Build()
        {
            float k = split ? 0.8f : 1f;
            int big = Mathf.RoundToInt(64 * k), med = Mathf.RoundToInt(22 * k), small = Mathf.RoundToInt(16 * k);
            bool economy = race.def.economy;

            streaks = Overlay("Streaks", Res.Streaks, new Color(1, 1, 1, 0));
            Overlay("Vignette", Res.Vignette, new Color(0, 0, 0, 0.35f));
            damage = Overlay("Damage", Res.Vignette, new Color(1f, 0.1f, 0.05f, 0f));

            // top-left: place, time, zone
            var tl = UIKit.Box(root, "TL", new Vector2(0, 1), new Vector2(18, -10), new Vector2(380, 140));
            posText = UIKit.LabelAt(tl, "1", big, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), Vector2.zero, new Vector2(110, 80));
            posOf = UIKit.LabelAt(tl, "/16", med, TextAnchor.UpperLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(Mathf.RoundToInt(74 * k), -Mathf.RoundToInt(12 * k)), new Vector2(120, 40));
            timeText = UIKit.LabelAt(tl, "00:00.00", med, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(0, -78 * k), new Vector2(300, 30));
            zoneText = UIKit.LabelAt(tl, "", small, TextAnchor.UpperLeft, UIKit.Accent, new Vector2(0, 1), new Vector2(0, -104 * k), new Vector2(360, 26));
            if (race.def.kind == EventKind.Explore) { posText.text = ""; posOf.text = ""; }

            // top-centre: gate and distance
            gateText = UIKit.LabelAt(root, "", med, TextAnchor.UpperCenter, Color.white, new Vector2(0.5f, 1), new Vector2(0, -14), new Vector2(700, 32));
            distText = UIKit.LabelAt(root, "", small, TextAnchor.UpperCenter, UIKit.Dim, new Vector2(0.5f, 1), new Vector2(0, -44), new Vector2(700, 24));
            arrow = UIKit.LabelAt(root, "▲", Mathf.RoundToInt(34 * k), TextAnchor.MiddleCenter, new Color(0.5f, 0.96f, 1f), new Vector2(0.5f, 1), new Vector2(0, -88), new Vector2(60, 60)).rectTransform;
            arrow.pivot = new Vector2(0.5f, 0.5f);

            // top-right: piggy bank (expedition) and feed
            float feedY = -14f;
            if (economy)
            {
                var pool = UIKit.PanelAt(root, "Pool", UIKit.PanelCol, new Vector2(1, 1), new Vector2(-14, -10), new Vector2(split ? 300 : 340, 66));
                poolTitle = UIKit.LabelAt(pool.rectTransform, "PORQUINHO", small, TextAnchor.UpperLeft, new Color(1f, 0.75f, 0.3f), new Vector2(0, 1), new Vector2(12, -6), new Vector2(320, 22));
                poolText = UIKit.LabelAt(pool.rectTransform, "0 itens · valor estimado 0 CR", small, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(12, -30), new Vector2(320, 40));
                feedY = -84f;
            }
            feedText = UIKit.LabelAt(root, "", Mathf.RoundToInt(14 * k), TextAnchor.UpperRight, Color.white, new Vector2(1, 1), new Vector2(-14, feedY), new Vector2(460, 140));

            // minimap (bottom-right on PC, below the feed on phones)
            float ms = split ? 170f : mobile ? 190f : 230f;
            Vector2 mAnchor = mobile ? new Vector2(1, 1) : new Vector2(1, 0);
            Vector2 mPos = mobile ? new Vector2(-14, -230) : new Vector2(-18, split ? 18 : 92);
            var frame = UIKit.PanelAt(root, "MapFrame", new Color(0.02f, 0.03f, 0.05f, 0.75f), mAnchor, mPos, new Vector2(ms + 8, ms + 8));
            mapWindow = UIKit.Rect(frame.rectTransform, "Window", Vector2.zero, Vector2.one, new Vector2(4, 4), new Vector2(-4, -4));
            mapWindow.gameObject.AddComponent<RectMask2D>();
            mapContent = UIKit.Rect(mapWindow, "Content", new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f));
            mapContent.sizeDelta = new Vector2(ms * 1.5f, ms * 1.5f);
            mapImg = mapContent.gameObject.AddComponent<RawImage>();
            mapImg.texture = MapTexture;
            mapImg.raycastTarget = false;
            mapImg.color = new Color(1f, 1f, 1f, 0.92f);
            for (int i = 0; i < race.racers.Count; i++)
            {
                var r = race.racers[i];
                bool mine = r == me;
                var img = UIKit.PanelAt(mapWindow, "dot", mine ? Color.white : (r.pilot.human ? r.pilot.livery : new Color(1f, 0.45f, 0.3f, 0.95f)), new Vector2(0.5f, 0.5f), Vector2.zero, mine ? new Vector2(10, 14) : new Vector2(7, 7));
                img.rectTransform.pivot = new Vector2(0.5f, 0.5f);
                dots.Add(img.rectTransform);
            }
            nextDot = UIKit.PanelAt(mapWindow, "next", new Color(0.5f, 0.96f, 1f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(12, 12)).rectTransform;
            nextDot.pivot = new Vector2(0.5f, 0.5f);
            nextDot.localEulerAngles = new Vector3(0, 0, 45f);
            dots[me.index].SetAsLastSibling();
            UIKit.LabelAt(frame.rectTransform, "N", 13, TextAnchor.UpperCenter, UIKit.Dim, new Vector2(0.5f, 1), new Vector2(0, -2), new Vector2(20, 18));

            // bars
            Vector2 barAnchor = mobile ? new Vector2(0, 1) : new Vector2(0, 0);
            Vector2 barPos = mobile ? new Vector2(18, -150) : new Vector2(18, 18);
            float bw = split ? 260f : 320f, bh = split ? 20f : 24f;
            var bars = UIKit.Box(root, "Bars", barAnchor, barPos, new Vector2(bw, bh * 4 + 30));
            nitro = UIBar.Make(bars, "Nitro", new Vector2(0, 0), new Vector2(0, 0), new Vector2(bw, bh), new Color(0.3f, 0.75f, 1f), "NITRO");
            float y = bh + 8;
            if (economy)
            {
                fuel = UIBar.Make(bars, "Fuel", new Vector2(0, 0), new Vector2(0, y), new Vector2(bw, bh), new Color(1f, 0.75f, 0.2f), "COMBUSTÍVEL");
                y += bh + 8;
            }
            integ = UIBar.Make(bars, "Integ", new Vector2(0, 0), new Vector2(0, y), new Vector2(bw, bh), new Color(0.35f, 1f, 0.5f), "INTEGRIDADE");
            y += bh + 8;
            repairBar = UIBar.Make(bars, "Repair", new Vector2(0, 0), new Vector2(0, y), new Vector2(bw * 0.7f, bh * 0.75f), new Color(0.4f, 1f, 0.8f), "REPARO");
            repairBar.root.gameObject.SetActive(false);
            if (race.def.kind == EventKind.Explore) integ.root.gameObject.SetActive(false);
            nitroGainText = UIKit.LabelAt(bars, "", small, TextAnchor.LowerLeft, new Color(0.6f, 0.9f, 1f), new Vector2(0, 0), new Vector2(bw + 10, 0), new Vector2(260, 26));

            // speed
            Vector2 spAnchor = mobile ? new Vector2(0.5f, 1) : new Vector2(0.5f, 0);
            Vector2 spPos = mobile ? new Vector2(0, -110) : new Vector2(0, 12);
            var sp = UIKit.Box(root, "Speed", spAnchor, spPos, new Vector2(260, 90));
            speedText = UIKit.LabelAt(sp, "0", Mathf.RoundToInt((mobile ? 44 : 60) * k), TextAnchor.LowerCenter, Color.white, new Vector2(0.5f, 0), new Vector2(0, 22), new Vector2(260, 70));
            UIKit.LabelAt(sp, "km/h", small, TextAnchor.LowerCenter, UIKit.Dim, new Vector2(0.5f, 0), new Vector2(0, 2), new Vector2(200, 24));

            // consumables (desktop: above the minimap; phones: on the touch buttons)
            if (!mobile && race.def.kind != EventKind.Explore)
            {
                var cons = UIKit.Box(root, "Cons", new Vector2(1, 0), new Vector2(-18, split ? 200 : 336), new Vector2(320, 56));
                slotAText = UIKit.LabelAt(cons, "", small, TextAnchor.LowerRight, Color.white, new Vector2(1, 0), new Vector2(0, 28), new Vector2(320, 26));
                slotBText = UIKit.LabelAt(cons, "", small, TextAnchor.LowerRight, Color.white, new Vector2(1, 0), new Vector2(0, 2), new Vector2(320, 26));
            }

            // centre messages
            msgText = UIKit.LabelAt(root, "", Mathf.RoundToInt(56 * k), TextAnchor.MiddleCenter, Color.white, new Vector2(0.5f, 0.5f), new Vector2(0, 90 * k), new Vector2(1000, 90));
            subText = UIKit.LabelAt(root, "", Mathf.RoundToInt(22 * k), TextAnchor.MiddleCenter, UIKit.Accent, new Vector2(0.5f, 0.5f), new Vector2(0, 40 * k), new Vector2(1000, 40));
            warnText = UIKit.LabelAt(root, "", Mathf.RoundToInt(20 * k), TextAnchor.MiddleCenter, UIKit.Warn, new Vector2(0.5f, 0.5f), new Vector2(0, -120 * k), new Vector2(1000, 34));
        }

        RawImage Overlay(string name, Texture tex, Color c)
        {
            var r = UIKit.Rect(root, name, Vector2.zero, Vector2.one);
            var img = r.gameObject.AddComponent<RawImage>();
            img.texture = tex;
            img.color = c;
            img.raycastTarget = false;
            return img;
        }

        public void Message(string big, string sub = null, float dur = 2f)
        {
            msgText.text = big;
            msgT = dur;
            if (sub != null) { subText.text = sub; subText.color = UIKit.Accent; subT = dur; }
        }

        public void Sub(string sub, float dur = 2.5f, Color? col = null)
        {
            subText.text = sub;
            subText.color = col ?? UIKit.Accent;
            subT = dur;
        }

        public void Feed(string line)
        {
            feed.Insert(0, line);
            feedT.Insert(0, 7f);
            if (feed.Count > 5) { feed.RemoveAt(5); feedT.RemoveAt(5); }
        }

        public void NitroGain(float amount, string reason)
        {
            nitroGainText.text = $"+{Mathf.RoundToInt(amount)} NITRO · {reason}";
            gainT = 1.6f;
        }

        public void Hit(float strength) => damageFlash = Mathf.Min(1f, damageFlash + strength / 25f);

        public void Update(float dt, float alpha, float camYaw)
        {
            var def = race.def;
            var c = me.craft;
            // place / time / zone
            bool racing = race.phase != RacePhase.Countdown;
            if (def.kind != EventKind.Explore)
            {
                posText.text = me.place.ToString();
                posOf.text = "/" + race.racers.Count;
                float t = me.state == PilotState.Finished ? me.finishTime : race.raceTime;
                timeText.text = racing ? UIKit.Time(t) : "00:00.00";
            }
            else timeText.text = "";
            int z = race.def.fallFloor > -1e6f && c.position.y > race.def.fallFloor + 40f ? -2 : race.world.ZoneAt(c.position);
            if (z != zone)
            {
                zone = z;
                zoneText.text = z == -2 ? "Cidadela Titã" : race.world.data.zones[z].name;
            }

            // gates
            var target = race.NextTarget(me);
            var to = target - c.position;
            float dist = new Vector2(to.x, to.z).magnitude;
            int total = race.GateCount;
            if (def.kind == EventKind.Explore)
            {
                gateText.text = "EXPLORAR";
                distText.text = "M / Share: mapa e viagem rápida";
                arrow.gameObject.SetActive(false);
            }
            else if (me.state == PilotState.Finished)
            {
                gateText.text = def.economy ? UIKit.Colorize("EXTRAÇÃO CONCLUÍDA", UIKit.Good) : UIKit.Colorize("CHEGADA!", UIKit.Good);
                distText.text = "";
                arrow.gameObject.SetActive(false);
            }
            else
            {
                if (def.Laps)
                {
                    int per = def.gates.Length;
                    int lap = Mathf.Min(me.nextGate / per + 1, def.laps);
                    gateText.text = $"VOLTA {lap}/{def.laps}  ·  PORTÃO {me.nextGate % per + 1}/{per}";
                }
                else if (me.nextGate >= def.gates.Length && def.finish != null)
                    gateText.text = def.economy ? "RUMO À EXTRAÇÃO" : "RETA FINAL";
                else gateText.text = $"PORTÃO {me.nextGate + 1}/{def.gates.Length}";
                distText.text = $"{dist:0} m  ·  faltam {race.RemainingKm(me):0.0} km";
                // arrow: direction of the next gate relative to the camera
                float ang = Mathf.Atan2(to.x, to.z) * Mathf.Rad2Deg - camYaw * Mathf.Rad2Deg;
                ang = Mathf.DeltaAngle(0f, ang);
                arrow.gameObject.SetActive(Mathf.Abs(ang) > 25f || dist < 400f);
                arrow.localEulerAngles = new Vector3(0, 0, -ang);
            }

            // pool
            if (poolText != null)
            {
                int n = race.pool.Count;
                if (n != lastPoolCount) { poolPulse = 1f; lastPoolCount = n; }
                poolPulse = Mathf.MoveTowards(poolPulse, 0f, dt * 1.5f);
                poolText.text = $"{n} {(n == 1 ? "peça" : "peças")} · valor estimado ≈ {UIKit.Cr(race.poolValue)}";
                poolTitle.color = Color.Lerp(new Color(1f, 0.75f, 0.3f), Color.white, poolPulse);
            }

            // feed
            var sb = new System.Text.StringBuilder();
            for (int i = feed.Count - 1; i >= 0; i--)
            {
                feedT[i] -= dt;
                if (feedT[i] <= 0f) { feed.RemoveAt(i); feedT.RemoveAt(i); }
            }
            foreach (var l in feed) sb.AppendLine(l);
            feedText.text = sb.ToString();

            // minimap: north-up texture rotated so the ship points up
            UpdateMap(alpha, camYaw);

            // bars
            integ.Set(me.integrity / 100f);
            integ.label.text = $"INTEGRIDADE {Mathf.CeilToInt(me.integrity)}%" + (me.integrity < 10f ? "  CRÍTICA" : me.integrity < 25f ? "  FALHAS SÉRIAS" : me.integrity < 50f ? "  DANIFICADA" : "");
            integ.fillImg.color = me.integrity < 25f ? (Mathf.Repeat(Time.unscaledTime, 0.5f) < 0.25f ? UIKit.Danger : new Color(0.5f, 0.05f, 0.05f)) : me.integrity < 50f ? UIKit.Warn : UIKit.Good;
            if (fuel != null)
            {
                fuel.Set(me.fuel / me.st.fuelCap);
                fuel.label.text = $"COMBUSTÍVEL {Mathf.CeilToInt(me.fuel)}%";
                fuel.fillImg.color = me.fuel < 20f ? UIKit.Danger : new Color(1f, 0.75f, 0.2f);
            }
            nitro.Set(c.nitro / 100f);
            nitro.label.text = c.nitroActive ? "NITRO  >>>" : c.driftCharge > 0.6f ? "NITRO  · derrapagem carregada" : "NITRO";
            nitro.fillImg.color = c.nitroActive ? Color.white : new Color(0.3f, 0.75f, 1f);
            repairBar.root.gameObject.SetActive(me.repairT > 0f);
            if (me.repairT > 0f) repairBar.Set(1f - me.repairT / 5f);
            if (gainT > 0f) { gainT -= dt; if (gainT <= 0f) nitroGainText.text = ""; }

            // speed
            speedText.text = Mathf.RoundToInt(me.SpeedKmh).ToString();
            speedText.color = c.nitroActive ? new Color(0.6f, 0.9f, 1f) : Color.white;

            // consumables
            var p = me.pilot;
            if (slotAText != null)
            {
                bool pad = me.input != null && me.input.UsingGamepad;
                string SlotTxt(int i, string key) => $"[{key}] {Catalog.ConsumableName[(int)p.cons[i]]} x{p.consCount[i]}";
                slotAText.text = SlotTxt(0, pad ? "L1" : "Q");
                slotBText.text = SlotTxt(1, pad ? "R1" : "E");
                slotAText.color = p.consCount[0] > 0 ? Color.white : UIKit.Dim;
                slotBText.color = p.consCount[1] > 0 ? Color.white : UIKit.Dim;
            }

            // warnings
            string warn = Warning();
            if (warn != lastWarn) { lastWarn = warn; warnBlink = 0f; }
            warnBlink += dt;
            warnText.text = warn ?? "";
            warnText.enabled = warn != null && (warnBlink < 1.5f || Mathf.Repeat(warnBlink, 0.8f) < 0.6f);

            // overlays
            float sp01 = Mathf.Clamp01((c.Speed - 75f) / 60f);
            streaks.color = new Color(1, 1, 1, sp01 * 0.2f + (c.nitroActive ? 0.22f : 0f));
            streaks.rectTransform.localEulerAngles = new Vector3(0, 0, Random.Range(0, 4) * 90f);
            streaks.rectTransform.localScale = Vector3.one * (1.05f + Random.value * 0.05f);
            damageFlash = Mathf.MoveTowards(damageFlash, 0f, dt * 1.8f);
            float critical = me.integrity < 25f && me.state == PilotState.Racing ? 0.25f + 0.15f * Mathf.Sin(Time.unscaledTime * 6f) : 0f;
            damage.color = new Color(1f, 0.1f, 0.05f, Mathf.Max(damageFlash * 0.8f, critical));

            if (msgT > 0f) { msgT -= dt; if (msgT <= 0f) msgText.text = ""; }
            if (subT > 0f) { subT -= dt; if (subT <= 0f) subText.text = ""; }
        }

        void UpdateMap(float alpha, float camYaw)
        {
            float size = race.world.data.size;
            var me3 = me.InterpolatedPos(alpha);
            float win = mapWindow.rect.width;
            float pxPerM = win / mapSpan;
            float contentPx = mapContent.sizeDelta.x;
            float spanContent = contentPx / pxPerM;
            float u = me3.x / size + 0.5f, v = me3.z / size + 0.5f, w = spanContent / size;
            mapImg.uvRect = new Rect(u - w * 0.5f, v - w * 0.5f, w, w);
            float yawDeg = camYaw * Mathf.Rad2Deg;
            mapContent.localEulerAngles = new Vector3(0, 0, yawDeg);
            var rot = Quaternion.Euler(0, 0, yawDeg);
            float half = win * 0.5f - 5f;
            for (int i = 0; i < race.racers.Count; i++)
            {
                var r = race.racers[i];
                var d = r.InterpolatedPos(alpha) - me3;
                var p = rot * new Vector3(d.x * pxPerM, d.z * pxPerM, 0f);
                bool show = r.state != PilotState.Destroyed || r == me;
                if (r != me) { p.x = Mathf.Clamp(p.x, -half, half); p.y = Mathf.Clamp(p.y, -half, half); }
                dots[i].anchoredPosition = p;
                dots[i].localEulerAngles = new Vector3(0, 0, yawDeg - r.InterpolatedYaw(alpha) * Mathf.Rad2Deg);
                dots[i].gameObject.SetActive(show);
            }
            if (race.def.kind != EventKind.Explore && me.state == PilotState.Racing)
            {
                var d = race.NextTarget(me) - me3;
                var p = rot * new Vector3(d.x * pxPerM, d.z * pxPerM, 0f);
                p.x = Mathf.Clamp(p.x, -half, half); p.y = Mathf.Clamp(p.y, -half, half);
                nextDot.anchoredPosition = p;
                nextDot.gameObject.SetActive(true);
            }
            else nextDot.gameObject.SetActive(false);
        }

        string Warning()
        {
            if (me.state != PilotState.Racing) return null;
            var def = race.def;
            if (def.economy && me.fuel < 20f) return UIKit.Colorize("COMBUSTÍVEL BAIXO — postos nos portões 10 e 20", UIKit.Danger);
            if (me.integrity < 25f && def.kind != EventKind.Explore) return UIKit.Colorize("INTEGRIDADE CRÍTICA — repare quando a pista estiver livre", UIKit.Danger);
            if (me.craft.onWater) return UIKit.Colorize("NA ÁGUA — velocidade reduzida", new Color(0.6f, 0.85f, 1f));
            return null;
        }
    }
}
