using System.Collections.Generic;
using RedDust.Meta;
using RedDust.Presentation;
using RedDust.Vehicle;
using UnityEngine;

namespace RedDust.Game
{
    /// <summary>
    /// Visual V2 das naves (fase A aprovada; Blender → FBX em Resources/V2Chassis/&lt;chassis&gt;): o chassis novo por cima da
    /// física antiga (o visual nunca mexe em colliders nem no centro de massa). Os módulos montados mudam peças reais do
    /// modelo (propulsores, pernas/asas) e acrescentam volumes presos nos sockets (blindagem, refrigeração, utilidade, cauda,
    /// motor); o reator dá a cor ao glow dos emissores hover. "-naveslegacy" na linha de comandos volta às naves antigas.
    /// </summary>
    public static class V2ShipVisual
    {
        static readonly Dictionary<string, GameObject> cache = new Dictionary<string, GameObject>();
        static readonly bool legacy = System.Environment.CommandLine.Contains("-naveslegacy");

        public static GameObject Build(CraftController craft, ChassisDef c, IDictionary<string, EquipmentInstance> mounted, Color paint, Color reactorGlow) =>
            BuildOn(craft.transform, craft.tuning.hoverHeight, craft, c, mounted, paint, reactorGlow);

        /// <summary>Monta o visual debaixo de parent (craft pode ser null: hangar/fotos no editor).</summary>
        public static GameObject BuildOn(Transform parent, float hoverHeight, CraftController craft, ChassisDef c, IDictionary<string, EquipmentInstance> mounted, Color paint, Color reactorGlow)
        {
            if (legacy) return null;
            if (!cache.TryGetValue(c.id, out var src)) { src = Resources.Load<GameObject>("V2Chassis/" + c.id); cache[c.id] = src; }
            if (src == null) return null;
            EquipmentInstance M(string socket) => mounted != null && mounted.TryGetValue(socket, out var it) ? it : null;
            string V(string socket) => M(socket)?.Def?.visual ?? "";

            var root = new GameObject("Visual");
            root.transform.SetParent(parent, false);
            var model = Object.Instantiate(src, root.transform, false);
            model.name = "V2_" + c.id;
            var anim = model.GetComponent<Animator>();
            if (anim != null) Kill(anim);
            var rt = root.transform;

            // ---- orientação, escala e altura: nariz em +Z, comprimento plausível, placas hover logo acima do chão
            var parts = new Dictionary<string, Transform>();
            foreach (var t in model.GetComponentsInChildren<Transform>(true)) if (!parts.ContainsKey(t.name)) parts[t.name] = t;
            Bounds Part(string n) => parts.TryGetValue(n, out var t) ? LocalBounds(rt, t) : new Bounds();
            if (parts.ContainsKey("Cockpit") && parts.ContainsKey("Propulsion_R") && Part("Cockpit").center.z < Part("Propulsion_R").center.z)
                model.transform.localRotation = Quaternion.Euler(0f, 180f, 0f) * model.transform.localRotation;
            var all = LocalBounds(rt, model.transform);
            if (all.size.z > 40f) model.transform.localScale *= 0.01f;
            else if (all.size.z < 0.4f) model.transform.localScale *= 100f;
            all = LocalBounds(rt, model.transform);
            float ground = -hoverHeight;
            model.transform.localPosition += new Vector3(-all.center.x, ground + 0.12f - all.min.y, -all.center.z);

            // ---- materiais por nome (pintura do chassis nas chapas; estrutura escura; glow do reator nos emissores)
            var paintM = ShipBuilder.Mat("RedDust/CraftPaint", paint);
            var structM = ShipBuilder.Mat("RedDust/CraftMetal", new Color(0.15f, 0.16f, 0.17f));
            var metalM = ShipBuilder.Mat("RedDust/CraftMetal", new Color(0.36f, 0.37f, 0.39f));
            var darkM = ShipBuilder.Mat("RedDust/CraftMetal", new Color(0.04f, 0.04f, 0.045f));
            var glassM = ShipBuilder.Mat("RedDust/CraftGlass", new Color(0.05f, 0.08f, 0.12f));
            var hoverM = ShipBuilder.Mat("RedDust/CraftGlow", reactorGlow, 1.2f);
            var coreM = ShipBuilder.Mat("RedDust/CraftGlow", reactorGlow, 1.8f);
            var coolM = ShipBuilder.Mat("RedDust/CraftMetal", new Color(0.22f, 0.32f, 0.45f));
            var sockM = ShipBuilder.Mat("RedDust/CraftMetal", new Color(0.85f, 0.45f, 0.12f));
            foreach (var r in model.GetComponentsInChildren<Renderer>(true))
            {
                var ms = r.sharedMaterials;
                for (int i = 0; i < ms.Length; i++)
                {
                    string n = ms[i] != null ? ms[i].name.ToLowerInvariant() : "";
                    ms[i] = n.Contains("body") ? paintM : n.Contains("structure") ? structM : n.Contains("canopy") ? glassM : n.Contains("hover") ? hoverM
                          : n.Contains("reactorcore") ? coreM : n.Contains("opening") || n.Contains("harness") ? darkM : n.Contains("coolant") ? coolM
                          : n.Contains("socket") ? sockM : metalM;
                }
                r.sharedMaterials = ms;
            }

            // ---- módulos que mudam peças do modelo
            float pS(EquipmentInstance it) { var d = it?.Def; return d == null ? 1f : d.size == SizeClass.S ? 0.86f : d.size == SizeClass.L ? 1.16f : 1f; }
            float ps = pS(M("Propulsion"));
            foreach (var n in new[] { "Propulsion_R", "Propulsion_L" })
                if (parts.TryGetValue(n, out var p) && ps != 1f) { var b = Part(n); ScaleAbout(rt, p, new Vector3(b.center.x, b.center.y, b.max.z), Vector3.one * ps); }
            if (parts.TryGetValue("Propulsion_C", out var pc) && M("PropulsionC") != null)
            { var b = Part("Propulsion_C"); ScaleAbout(rt, pc, new Vector3(b.center.x, b.center.y, b.max.z), Vector3.one * pS(M("PropulsionC"))); }

            string wv = V("Wings");
            float span = wv == "wing_short" ? 0.84f : wv == "wing_long" ? 1.16f : wv == "wing_glide" ? 1.1f : wv == "wing_relic" ? 1.08f : wv == "wing_blade" ? 0.94f : 1f;
            float wThick = wv == "wing_heavy" || wv == "wing_brace" ? 1.3f : 1f;
            foreach (var (n, side) in new[] { ("Wings_R", 1f), ("Wings_L", -1f) })
                if (parts.TryGetValue(n, out var wpart) && (span != 1f || wThick != 1f))
                {
                    var b = Part(n);
                    float rootX = side > 0 ? Mathf.Min(b.min.x, b.max.x) : Mathf.Max(b.min.x, b.max.x);
                    ScaleAbout(rt, wpart, new Vector3(rootX, b.max.y, b.center.z), new Vector3(span, 1f, wThick));
                }

            // ---- módulos que acrescentam volumes presos ao corpo (com suportes; nada de caixas soltas)
            var body = Part("Body");
            var cock = parts.ContainsKey("Cockpit") ? Part("Cockpit") : body;
            float topY = Mathf.Max(body.max.y - 0.08f, cock.min.y + 0.2f);
            // flanco superior do diamante (Blender: meia-largura e altura do ombro → topo), por chassis
            var fl = c.id == "wraith" ? (0.46f, 0.64f, 0.25f, 0.88f) : c.id == "nomad" ? (0.88f, 0.74f, 0.50f, 1.04f)
                   : c.id == "bastion" ? (0.98f, 0.78f, 0.62f, 1.28f) : c.id == "vortex" ? (0.72f, 0.66f, 0.38f, 0.92f) : (0.66f, 0.66f, 0.34f, 0.94f);
            float baseY = model.transform.localPosition.y;   // z=0 do Blender (chão) no espaço do Visual
            void Armor(string socket, float z)
            {
                var a = M(socket);
                if (a == null) return;
                string av = a.Def.visual;
                float th = av == "armor_heavy" ? 0.10f : av == "armor_light" ? 0.035f : 0.065f;
                var mat = av == "armor_aegis" || av == "armor_relic" ? ShipBuilder.Mat("RedDust/CraftMetal", new Color(0.62f, 0.5f, 0.22f)) : ShipBuilder.Mat("RedDust/CraftMetal", new Color(0.27f, 0.28f, 0.30f));
                float len = av == "armor_heavy" ? 2.0f : 1.6f;
                float dx = fl.Item1 - fl.Item3, dy = fl.Item4 - fl.Item2, flank = Mathf.Sqrt(dx * dx + dy * dy);
                float ang = Mathf.Atan2(dx, dy) * Mathf.Rad2Deg;
                foreach (float side in new[] { -1f, 1f })
                {
                    // centro do flanco, afastado na normal para pousar por cima das chapas
                    var nrm = new Vector2(side * dy, dx).normalized;
                    var mid = new Vector2(side * (fl.Item1 + fl.Item3) * 0.5f, baseY + (fl.Item2 + fl.Item4) * 0.5f) + nrm * (th * 0.5f + 0.015f);
                    var plate = Box(rt, "Armor_" + socket, new Vector3(mid.x, mid.y, z), new Vector3(th, flank * 0.85f, len), mat);
                    plate.localRotation = Quaternion.Euler(0f, 0f, side * ang);
                    for (int k = -1; k <= 1; k += 2)
                        Box(rt, "Armor_Bolt", new Vector3(mid.x + nrm.x * th * 0.5f, mid.y + nrm.y * th * 0.5f, z + k * len * 0.38f), new Vector3(0.05f, 0.05f, 0.05f), structM);
                }
            }
            Armor("Armor", body.center.z + body.extents.z * 0.25f);
            Armor("Armor2", body.center.z - body.extents.z * 0.25f);

            string cv = V("Cooling");
            if (cv != "")
            {
                int fins = cv == "cooling_grid" ? 7 : cv == "cooling_radiator" ? 5 : 3;
                float zc = body.center.z - body.extents.z * 0.35f;
                Box(rt, "Cooling_Frame", new Vector3(0f, topY + 0.02f, zc), new Vector3(0.62f, 0.05f, fins * 0.12f + 0.1f), structM);
                for (int f = 0; f < fins; f++)
                    Box(rt, "Cooling_Fin", new Vector3(0f, topY + 0.10f, zc + (f - (fins - 1) * 0.5f) * 0.12f), new Vector3(0.56f, 0.12f, 0.03f), coolM);
            }

            string ev = V("Engine");
            if (ev != "")
            {
                float ze = body.min.z + 0.9f;
                var engMat = ev == "engine_redline" ? ShipBuilder.Mat("RedDust/CraftPaint", new Color(0.75f, 0.05f, 0.04f)) : ev == "engine_relic" ? ShipBuilder.Mat("RedDust/CraftMetal", new Color(0.62f, 0.5f, 0.22f)) : metalM;
                float es = ev == "engine_heavy" ? 1.25f : ev == "engine_sprint" ? 0.85f : 1f;
                Box(rt, "Engine_Converter", new Vector3(0f, topY + 0.07f * es, ze), new Vector3(0.40f * es, 0.14f * es, 0.70f * es), engMat);
                foreach (float side in new[] { -1f, 1f })
                    Box(rt, "Engine_Clamp", new Vector3(side * 0.16f * es, topY + 0.01f, ze), new Vector3(0.05f, 0.04f, 0.74f * es), structM);
                if (ev == "engine_redline" || ev == "engine_burner")
                    Box(rt, "Engine_Glow", new Vector3(0f, topY + 0.15f * es, ze - 0.3f * es), new Vector3(0.24f, 0.03f, 0.08f), ShipBuilder.Mat("RedDust/CraftGlow", new Color(1f, 0.25f, 0.1f), 1.5f));
            }

            string tv = V("Tail");
            if (tv != "")
            {
                float zt = body.min.z + 0.35f, w = tv == "tail_long" ? 1.0f : tv == "tail_compact" ? 0.55f : 0.8f;
                foreach (float side in tv == "tail_twin" ? new[] { -0.3f, 0.3f } : new[] { 0f })
                {
                    Box(rt, "Tail_Flap", new Vector3(side, topY + 0.22f, zt), new Vector3(tv == "tail_twin" ? 0.45f : w, 0.04f, 0.32f), paintM);
                    foreach (float q in new[] { -1f, 1f })
                        Box(rt, "Tail_Pylon", new Vector3(side + q * (tv == "tail_twin" ? 0.12f : w * 0.3f), topY + 0.11f, zt), new Vector3(0.04f, 0.2f, 0.14f), structM);
                }
            }

            string uv = V("Utility") + V("Aux");
            float zu = cock.min.z - 0.15f;
            if (uv.Contains("util_mast") || uv.Contains("util_scanner")) { Box(rt, "Util_Mast", new Vector3(0.18f, topY + 0.3f, zu), new Vector3(0.04f, 0.6f, 0.04f), metalM); Box(rt, "Util_MastHead", new Vector3(0.18f, topY + 0.6f, zu), new Vector3(0.14f, 0.05f, 0.05f), sockM); }
            if (uv.Contains("util_dome") || uv.Contains("util_routeintel")) Box(rt, "Util_Dome", new Vector3(-0.15f, topY + 0.06f, zu), new Vector3(0.24f, 0.10f, 0.24f), ShipBuilder.Mat("RedDust/CraftGlow", new Color(0.4f, 1f, 0.8f), 0.8f));
            if (uv.Contains("util_drone")) Box(rt, "Util_Drone", new Vector3(0f, topY + 0.08f, zu - 0.45f), new Vector3(0.34f, 0.12f, 0.34f), darkM);

            // ---- pontos de escape (SpeedFx) atrás de cada propulsor
            int e = 0;
            foreach (var n in new[] { "Propulsion_R", "Propulsion_L", "Propulsion_C" })
                if (parts.ContainsKey(n))
                {
                    var b = Part(n);
                    var m = new GameObject("ExhaustPoint_" + e++).transform;
                    m.SetParent(rt, false);
                    m.localPosition = new Vector3(b.center.x, b.center.y, b.min.z - 0.05f);
                }

            if (craft == null) return root;
            var lean = root.AddComponent<CraftLean>();
            lean.craft = craft;
            lean.maxLean = c.id == "bastion" ? 20f : c.id == "wraith" ? 36f : 30f;
            lean.driftLean = c.id == "bastion" ? 34f : 48f;
            lean.driftYaw = 24f;
            return root;
        }

        static Transform Box(Transform root, string name, Vector3 c, Vector3 size, Material mat)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            Kill(go.GetComponent<Collider>());
            go.name = name;
            go.transform.SetParent(root, false);
            go.transform.localPosition = c;
            go.transform.localScale = size;
            go.GetComponent<MeshRenderer>().sharedMaterial = mat;
            return go.transform;
        }

        static void Kill(Object o) { if (Application.isPlaying) Object.Destroy(o); else Object.DestroyImmediate(o); }

        /// <summary>Escala uma peça à volta de um ponto (no espaço do Visual): pivot alinhado com a nave.</summary>
        static void ScaleAbout(Transform root, Transform part, Vector3 anchorLocal, Vector3 scale)
        {
            var pivot = new GameObject(part.name + "_Pivot").transform;
            pivot.SetParent(root, false);
            pivot.localPosition = anchorLocal;
            part.SetParent(pivot, true);
            pivot.localScale = scale;
        }

        /// <summary>Caixa envolvente das malhas de uma peça (e filhos) no espaço local de root.</summary>
        static Bounds LocalBounds(Transform root, Transform part)
        {
            bool any = false;
            var b = new Bounds();
            foreach (var mf in part.GetComponentsInChildren<MeshFilter>(true))
            {
                if (mf.sharedMesh == null) continue;
                var mb = mf.sharedMesh.bounds;
                var m = root.worldToLocalMatrix * mf.transform.localToWorldMatrix;
                for (int i = 0; i < 8; i++)
                {
                    var p = m.MultiplyPoint3x4(mb.center + Vector3.Scale(mb.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1)));
                    if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
                }
            }
            return b;
        }
    }
}
