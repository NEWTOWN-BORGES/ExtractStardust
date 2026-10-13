using System.Collections.Generic;
using RedDust.Meta;
using RedDust.Presentation;
using RedDust.Vehicle;
using UnityEngine;

namespace RedDust.Game
{
    /// <summary>Parâmetros de sobrevivência derivados dos stats (casco, combustível, calor, reparação) — TARGETS.</summary>
    public sealed class VitalsSpec
    {
        public float hullMax = 100f, fuelUse = 1f, coolMul = 1f, heatGain = 1f, repairMul = 1f, impactMul = 1f;
        public float intel;
        public bool redline, helios, aegis;
    }

    /// <summary>
    /// Monta uma nave a partir dos dados: stats → física (CraftTuning) e vitais; módulos → visual por sockets.
    /// A física vem só dos dados (envelope e massa do chassis); o visual nunca altera collider nem centro de massa (Doc 02 §12).
    /// </summary>
    public static class ShipBuilder
    {
        /// <summary>Stats 0..100 → física. Referência: STRIX stock (o CraftTuning por omissão foi afinado com ela).</summary>
        public static CraftTuning Tuning(ChassisDef c, ShipStats s)
        {
            var t = new CraftTuning();
            float D(Stat st, float reference) => s[st] - reference;
            t.mass = s.MassKg;
            t.hullSize = new Vector3(c.hullX, c.hullY, c.hullZ);
            t.topSpeed *= 1f + 0.0057f * D(Stat.Speed, 72);                    // BASTION ~398 km/h … WRAITH ~449 km/h (D3)
            t.accel *= (1f + 0.012f * D(Stat.Accel, 74)) * (1f - s[Stat.Mass] / 4000f);
            float h = D(Stat.Handling, 76);
            t.turnRateLow *= 1f + 0.008f * h;
            t.turnRateHigh *= 1f + 0.008f * h;
            t.gripLateralMax *= 1f + 0.004f * h;
            t.steerResponse *= 1f + 0.006f * h;
            float st = D(Stat.Stability, 75);
            t.stabilityRecover *= 1f + 0.015f * st;
            t.alignRate *= 1f + 0.005f * st;
            t.adhesion *= 1f + 0.008f * st;
            t.gripCap = Mathf.Clamp(t.gripCap + 0.0012f * st, 0.45f, 0.65f);
            float b = D(Stat.Boost, 70);
            t.boostAccel *= 1f + 0.01f * b;
            t.boostTopMul += 0.0015f * b;
            t.nitroSeconds *= 1f + 0.006f * b;
            t.nitroRegen *= 1f + 0.004f * b;
            if (s.Perks.Contains("helios")) { t.nitroRegen *= 1.17f; t.nitroSeconds *= 1.11f; }
            return t;
        }

        public static VitalsSpec Vitals(ShipStats s)
        {
            var v = new VitalsSpec
            {
                hullMax = Mathf.Max(50f, 100f * (1f + 0.01f * (s[Stat.Hull] - 66f))),
                fuelUse = Mathf.Max(0.4f, 1f - 0.008f * (s[Stat.Efficiency] - 66f)),
                coolMul = Mathf.Max(0.5f, 1f + 0.012f * (s[Stat.Cooling] - 68f)),
                heatGain = Mathf.Clamp(1f - 0.004f * (s[Stat.Cooling] - 68f), 0.7f, 1.3f),
                repairMul = 1f + s[Stat.Repair] / 40f,
                intel = s[Stat.Intel],
                redline = s.Perks.Contains("redline"),
                helios = s.Perks.Contains("helios"),
                aegis = s.Perks.Contains("aegis"),
            };
            if (v.helios) v.fuelUse *= 1.06f;
            if (v.aegis) v.impactMul = 0.75f;
            return v;
        }

        public static Color Paint(uint rgb) => new Color(((rgb >> 16) & 255) / 255f, ((rgb >> 8) & 255) / 255f, (rgb & 255) / 255f);

        // ------------------------------------------------------------------ visual modular (provisório, por sockets)

        static readonly Dictionary<string, Material> mats = new Dictionary<string, Material>();

        public static Material Mat(string resource, Color c, float emission = 0f)
        {
            string key = resource + ColorUtility.ToHtmlStringRGB(c) + emission;
            if (mats.TryGetValue(key, out var m) && m != null) return m;
            var src = Resources.Load<Material>(resource);
            m = src != null ? new Material(src) : new Material(Shader.Find("Universal Render Pipeline/Lit"));
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
            if (emission > 0f && m.HasProperty("_EmissionColor")) { m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", c * emission); }
            mats[key] = m;
            return m;
        }

        sealed class Kit
        {
            public GameObject root;
            public Material paint, dark, metal, glass, glow;
            public void Part(string name, Mesh mesh, Material mat, Transform parent = null)
            {
                var go = new GameObject(name);
                go.transform.SetParent(parent != null ? parent : root.transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                go.AddComponent<MeshRenderer>().sharedMaterial = mat;
            }
            public Transform Socket(string id, Vector3 pos)
            {
                var t = new GameObject("Socket_" + id).transform;
                t.SetParent(root.transform, false);
                t.localPosition = pos;
                return t;
            }
        }

        static Mesh Box(Vector3 c, Vector3 size)
        {
            var mb = new MeshBuilder();
            Vector3 h = size * 0.5f;
            mb.Plate(c + new Vector3(-h.x, 0f, h.z), c + new Vector3(h.x, 0f, h.z), c + new Vector3(h.x, 0f, -h.z), c + new Vector3(-h.x, 0f, -h.z), size.y);
            return mb.Build();
        }

        static Mesh Plate(Vector3 a, Vector3 b, Vector3 c, Vector3 d, float thick, bool vertical = false)
        {
            var mb = new MeshBuilder();
            mb.Plate(a, b, c, d, thick, vertical);
            return mb.Build();
        }

        static Mesh Pod(float x, float y, float z0, float z1, float r)
        {
            var mb = new MeshBuilder();
            mb.Loft(new[] { (z0, r * 1.4f, r * 1.4f, 0f), (Mathf.Lerp(z0, z1, 0.4f), r * 2f, r * 2f, 0f), (z1, r * 1.7f, r * 1.7f, 0f) }, 10, new Vector3(x, y, 0f));
            return mb.Build();
        }

        static Mesh Disc(Vector3 c, float r, Vector3 n)
        {
            var mb = new MeshBuilder();
            mb.Disc(c, r, 12, n);
            return mb.Build(false);
        }

        public static Color GlowFor(EquipmentInstance it)
        {
            if (it == null) return new Color(1f, 0.42f, 0.12f);
            switch (it.Def?.visual)
            {
                case "reactor_small": return new Color(0.3f, 0.95f, 1f);
                case "reactor_steady": return new Color(0.35f, 0.55f, 1f);
                case "reactor_flux": return new Color(1f, 0.25f, 0.85f);
                case "reactor_large": return new Color(1f, 0.7f, 0.2f);
                case "reactor_helios": return new Color(1f, 0.93f, 0.6f);
                default: return new Color(1f, 0.42f, 0.12f);
            }
        }

        /// <summary>
        /// Visual da nave: núcleo do chassis (~60% da identidade) + módulos montados nos sockets (~40%).
        /// mounted: socket → instância (null = peça de série do chassis).
        /// </summary>
        public static GameObject BuildVisual(CraftController craft, ChassisDef c, IDictionary<string, EquipmentInstance> mounted, Color paint)
        {
            var old = craft.transform.Find("Visual");
            if (old != null) Object.Destroy(old.gameObject);
            EquipmentInstance M(string socket) => mounted != null && mounted.TryGetValue(socket, out var it) ? it : null;
            string V(string socket) => M(socket)?.Def?.visual ?? "";
            float Sz(string socket, float stock = 1f) { var d = M(socket)?.Def; return d == null ? stock : d.size == SizeClass.S ? 0.8f : d.size == SizeClass.L ? 1.3f : 1f; }

            var v2 = V2ShipVisual.Build(craft, c, mounted, paint, GlowFor(M("Reactor")));   // naves V2 (fase A aprovada)
            if (v2 != null) return v2;

            var k = new Kit { root = new GameObject("Visual") };
            k.root.transform.SetParent(craft.transform, false);
            k.paint = Mat("RedDust/CraftPaint", paint);
            k.dark = Mat("RedDust/CraftMetal", new Color(0.09f, 0.1f, 0.11f));
            k.metal = Mat("RedDust/CraftMetal", new Color(0.32f, 0.33f, 0.35f));
            k.glass = Mat("RedDust/CraftGlass", new Color(0.05f, 0.08f, 0.12f));
            var reactorGlow = GlowFor(M("Reactor"));
            k.glow = Mat("RedDust/CraftGlow", reactorGlow, 1.1f);

            // ---- núcleo do chassis (proporções próprias de cada um; silhuetas distintas)
            float w = c.id == "wraith" ? 0.72f : c.id == "bastion" ? 1.22f : c.id == "nomad" ? 1.06f : 1f;
            float hgt = c.id == "bastion" ? 0.9f : c.id == "nomad" ? 1.15f : c.id == "wraith" ? 0.85f : 1f;
            float len = c.hullZ / 7f;
            var hull = new MeshBuilder();
            if (c.id == "vortex")
                hull.Loft(new[] { (3.3f * len, 0.5f, 0.22f, -0.16f), (2.0f * len, 1.5f, 0.5f, -0.1f), (0.2f * len, 2.4f, 0.8f, 0f), (-1.6f * len, 3.3f, 0.95f, 0.02f), (-3.3f * len, 3.4f, 0.9f, 0f) }, 8);
            else
                hull.Loft(new[] { (3.55f * len, 0.55f * w, 0.22f * hgt, -0.18f), (2.6f * len, 1.6f * w, 0.46f * hgt, -0.12f), (1.2f * len, 2.5f * w, 0.74f * hgt, -0.02f),
                                  (-0.6f * len, 2.95f * w, 0.86f * hgt, 0.02f), (-2.4f * len, 3.1f * w, 0.82f * hgt, 0f), (-3.35f * len, 2.7f * w, 0.62f * hgt, -0.02f) }, 8);
            k.Part("Body_Core", hull.Build(), k.paint);
            var belly = new MeshBuilder();
            belly.Loft(new[] { (2.4f * len, 1.3f * w, 0.12f, -0.36f * hgt), (-0.5f * len, 2.6f * w, 0.16f, -0.42f * hgt), (-3.1f * len, 2.4f * w, 0.14f, -0.36f * hgt) }, 8);
            k.Part("Belly", belly.Build(), k.dark);
            var canopy = new MeshBuilder();
            float cz = c.id == "wraith" ? 1.25f : 1f;
            canopy.Loft(new[] { (1.5f * len * cz, 0.2f, 0.12f, 0.32f * hgt), (0.9f * len, 0.95f * w, 0.42f, 0.42f * hgt), (-0.3f * len, 1.05f * w, 0.46f, 0.44f * hgt), (-1.2f * len, 0.7f * w, 0.3f, 0.38f * hgt) }, 8);
            k.Part("Canopy", canopy.Build(), k.glass);
            if (c.id == "bastion")
                foreach (float side in new[] { -1f, 1f })   // ombros laterais: leitura frontal de massa
                    k.Part("Shoulder", Box(new Vector3(1.75f * side, 0.18f, -0.3f), new Vector3(0.6f, 0.55f, 3.2f)), k.dark);
            if (c.id == "nomad")
                foreach (float side in new[] { -1f, 1f })   // tanques visíveis ("Dakar futurista")
                    k.Part("Tank", Pod(1.55f * side, 0.25f, 0.8f, -1.6f, 0.26f), k.metal);

            // ---- motor (traseira): massa, intakes, exaustão
            var eng = k.Socket("Engine", new Vector3(0f, 0.3f * hgt, -2.4f * len));
            string ev = V("Engine");
            float es = Sz("Engine");
            k.Part("Engine_Block", Box(new Vector3(0f, 0f, 0f), new Vector3(1.1f * es, 0.42f * es, 1.6f * es)), ev == "engine_redline" ? Mat("RedDust/CraftPaint", new Color(0.75f, 0.05f, 0.04f)) : k.dark, eng);
            if (ev == "engine_sprint" || ev == "engine_redline" || ev == "engine_burner")
                foreach (float side in new[] { -1f, 1f }) k.Part("Intake", Box(new Vector3(0.38f * side * es, 0.26f * es, 0.5f), new Vector3(0.22f, 0.18f, 0.7f)), k.metal, eng);
            if (ev == "engine_heavy" || ev == "engine_relic")
                k.Part("Engine_Housing", Box(new Vector3(0f, 0.2f * es, -0.2f), new Vector3(1.5f * es, 0.25f, 1.2f * es)), k.metal, eng);
            if (ev == "engine_redline") k.Part("Redline_Glow", Disc(new Vector3(0f, 0f, -0.82f * es), 0.25f, Vector3.back), Mat("RedDust/CraftGlow", new Color(1f, 0.15f, 0.1f), 1.4f), eng);

            // ---- propulsores: L/R (+ central na VORTEX); o tamanho do kit muda o diâmetro e o comprimento
            float ps = Sz("Propulsion"), r = 0.42f * ps;
            float px = c.id == "wraith" ? 1.0f : c.id == "bastion" ? 1.7f : c.id == "vortex" ? 1.45f : 1.32f * w;
            var exhausts = new List<Vector3>();
            foreach (float side in new[] { -1f, 1f })
            {
                var sp = k.Socket(side < 0 ? "Propulsion_L" : "Propulsion_R", new Vector3(px * side, 0.04f, 0f));
                k.Part("Nacelle", Pod(0f, 0f, -0.6f * len, -3.4f * len * (0.9f + 0.1f * ps), r), k.dark, sp);
                Vector3 noz = new Vector3(px * side, 0.04f, -3.45f * len * (0.9f + 0.1f * ps) - 0.05f);
                k.Part("Nozzle", Disc(noz - sp.localPosition, r * 0.62f, Vector3.back), k.glow, sp);
                exhausts.Add(noz);
            }
            if (c.id == "vortex")
            {
                float pc = Sz("PropulsionC", 0.9f);
                var sc = k.Socket("Propulsion_Center", new Vector3(0f, 0.38f, 0f));
                k.Part("Nacelle_C", Pod(0f, 0f, -0.9f * len, -3.6f * len, 0.48f * pc), k.dark, sc);
                k.Part("Nozzle_C", Disc(new Vector3(0f, 0f, -3.62f * len), 0.3f * pc, Vector3.back), k.glow, sc);
                exhausts.Add(new Vector3(0f, 0.38f, -3.65f * len));
            }
            for (int i = 0; i < exhausts.Count; i++)
            {
                var m = new GameObject("ExhaustPoint_" + i).transform;
                m.SetParent(k.root.transform, false);
                m.localPosition = exhausts[i];
            }

            // ---- asas / estabilizadores: a maior alteração de silhueta
            string wv = V("Wings");
            float span = wv == "wing_short" ? 0.5f : wv == "wing_long" ? 1.25f : wv == "wing_heavy" ? 1.0f : wv == "wing_relic" ? 1.1f : wv == "wing_vector" ? 0.85f : 0.7f;
            float chord = wv == "wing_long" ? 2.6f : wv == "wing_short" ? 1.6f : 2.2f;
            float thick = wv == "wing_heavy" ? 0.16f : 0.07f;
            if (c.id == "wraith") span *= 0.75f;
            foreach (float side in new[] { -1f, 1f })
            {
                var ws = k.Socket(side < 0 ? "Wing_L" : "Wing_R", new Vector3((px + 0.1f) * side, 0f, -0.4f));
                float x0 = 0f, x1 = span * side;
                k.Part("Wing", Plate(new Vector3(x0, -0.02f, 0f), new Vector3(x1, 0.08f, -0.6f), new Vector3(x1, 0.08f, -0.6f - chord * 0.6f), new Vector3(x0, -0.02f, -chord), thick), k.paint, ws);
                if (wv == "wing_vector")   // segunda superfície vectorial
                    k.Part("Wing_Vector", Plate(new Vector3(x0, 0.32f, -0.9f), new Vector3(x1 * 0.7f, 0.42f, -1.2f), new Vector3(x1 * 0.7f, 0.42f, -1.7f), new Vector3(x0, 0.32f, -1.9f), 0.05f), k.metal, ws);
                if (wv == "wing_relic")    // ponta curva
                    k.Part("Wing_Tip", Plate(new Vector3(x1, 0.08f, -0.6f), new Vector3(x1 + 0.15f * side, 0.5f, -0.9f), new Vector3(x1 + 0.15f * side, 0.5f, -1.4f), new Vector3(x1, 0.08f, -1.9f), 0.05f, true), k.paint, ws);
            }

            // ---- cauda: perfil longitudinal
            string tv = V("Tail");
            var ts = k.Socket("Tail", new Vector3(0f, 0.38f * hgt, -2.0f * len));
            if (tv == "tail_twin")
                foreach (float side in new[] { -0.45f, 0.45f })
                    k.Part("Fin", Plate(new Vector3(side, 0f, 0f), new Vector3(side * 1.3f, 0.6f, -0.9f), new Vector3(side * 1.3f, 0.6f, -1.2f), new Vector3(side, 0f, -1.3f), 0.07f, true), k.paint, ts);
            else
            {
                float fh = tv == "tail_long" ? 0.75f : tv == "tail_compact" ? 0.4f : 0.57f;
                float fl = tv == "tail_long" ? 1.9f : 1.3f;
                k.Part("Fin", Plate(new Vector3(0f, 0f, 0f), new Vector3(0f, fh, -0.9f), new Vector3(0f, fh, -fl + 0.05f), new Vector3(0f, 0f, -fl), 0.08f, true), k.paint, ts);
                if (tv == "tail_long") k.Part("Keel_Vent", Box(new Vector3(0f, 0.1f, -1.2f), new Vector3(0.3f, 0.12f, 0.6f)), k.dark, ts);
            }

            // ---- blindagem: volumes físicos (não é só textura)
            void ArmorAt(string socket, float z)
            {
                var a = M(socket);
                if (a == null) return;
                string av = a.Def.visual;
                float th = av == "armor_heavy" ? 0.22f : av == "armor_light" ? 0.06f : 0.12f;
                var mat = av == "armor_aegis" ? Mat("RedDust/CraftMetal", new Color(0.62f, 0.5f, 0.22f)) : k.metal;
                foreach (float side in new[] { -1f, 1f })
                {
                    var asock = k.Socket(socket + (side < 0 ? "_L" : "_R"), new Vector3(1.32f * w * side, 0.1f, z));
                    k.Part("Armor_Plate", Box(Vector3.zero, new Vector3(th + 0.1f, 0.5f, av == "armor_heavy" ? 2.6f : 2.0f)), mat, asock);
                }
            }
            ArmorAt("Armor", 0.4f);
            ArmorAt("Armor2", -1.6f);

            // ---- reator: núcleo com glow atrás do cockpit
            var rs = k.Socket("Reactor", new Vector3(0f, 0.55f * hgt, -1.45f * len));
            float rr = M("Reactor") != null ? 0.28f * Sz("Reactor") : 0.18f;
            k.Part("Reactor_Core", Disc(Vector3.zero, rr, Vector3.up), k.glow, rs);
            k.Part("Reactor_Ring", Box(new Vector3(0f, -0.06f, 0f), new Vector3(rr * 2.6f, 0.08f, rr * 2.6f)), k.dark, rs);

            // ---- refrigeração: radiadores e vents bem visíveis
            string cv = V("Cooling");
            if (cv != "")
            {
                int fins = cv == "cooling_grid" ? 6 : cv == "cooling_radiator" ? 4 : 2;
                foreach (float side in new[] { -1f, 1f })
                {
                    var cs = k.Socket(side < 0 ? "Cooling_L" : "Cooling_R", new Vector3(0.75f * w * side, 0.45f * hgt, -0.6f));
                    for (int f = 0; f < fins; f++)
                        k.Part("Radiator_Fin", Box(new Vector3(0f, 0.08f, -f * 0.22f), new Vector3(0.5f, 0.16f, 0.05f)), k.metal, cs);
                }
            }

            // ---- navegação / utilidade
            string uv = V("Utility") + V("Aux");
            var us = k.Socket("Utility", new Vector3(0f, 0.6f * hgt, 0.2f));
            if (uv.Contains("util_mast")) k.Part("Mast", Box(new Vector3(0.3f, 0.3f, 0f), new Vector3(0.05f, 0.6f, 0.05f)), k.metal, us);
            if (uv.Contains("util_dome")) k.Part("Dome", Disc(new Vector3(0f, 0.05f, 0f), 0.22f, Vector3.up), Mat("RedDust/CraftGlow", new Color(0.4f, 1f, 0.8f), 0.8f), us);
            if (uv.Contains("util_drone")) k.Part("Drone", Box(new Vector3(-0.3f, 0.1f, -0.4f), new Vector3(0.35f, 0.15f, 0.35f)), k.dark, us);

            var lean = k.root.AddComponent<CraftLean>();
            lean.craft = craft;
            lean.maxLean = c.id == "bastion" ? 20f : c.id == "wraith" ? 36f : 30f;
            lean.driftLean = c.id == "bastion" ? 34f : 48f;
            lean.driftYaw = 24f;
            return k.root;
        }

        /// <summary>Cria a nave completa (física + visual) para uma build.</summary>
        public static CraftController Spawn(string name, ChassisDef c, IDictionary<string, EquipmentInstance> mounted, Color paint, out ShipStats stats, out VitalsSpec vitals)
        {
            var items = new List<EquipmentInstance>();
            if (mounted != null) foreach (var kv in mounted) if (kv.Value != null) items.Add(kv.Value);
            stats = StatResolver.Resolve(c, items);
            vitals = Vitals(stats);
            var tuning = Tuning(c, stats);
            var craft = CraftFactory.CreateCore(name, tuning);
            // o Awake do CraftController corre com o tuning por omissão: aplicar a massa do chassis + módulos
            craft.Body.mass = tuning.mass;
            craft.Body.centerOfMass = tuning.centerOfMass;
            BuildVisual(craft, c, mounted, paint);
            craft.gameObject.AddComponent<EngineAudio>().craft = craft;   // motor, boost, vento, impactos
            return craft;
        }

        public static Dictionary<string, EquipmentInstance> Mounted(PlayerProfile p)
        {
            var d = new Dictionary<string, EquipmentInstance>();
            foreach (var s in p.Current.slots) d[s.socket] = p.Item(s.item);
            return d;
        }
    }
}
