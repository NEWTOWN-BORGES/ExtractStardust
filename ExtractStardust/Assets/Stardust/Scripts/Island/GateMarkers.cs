using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Stardust
{
    /// <summary>
    /// Gates of the current event (port of map.gd _place_checkpoints/_portal): two pylons with lamps, a light beam
    /// and the zone name; a tall light column marks the next gate; start and extraction portals; in Explore the
    /// gates stay as landmarks and every other event shows its start portal.
    /// </summary>
    public class GateMarkers : MonoBehaviour
    {
        class Gate { public GameObject root; public Transform column; public Renderer columnR; }
        readonly List<Gate> gates = new List<Gate>();
        static Mesh pylon, lamp, beam, columnMesh;
        Material mat, colMat;
        int highlighted = -2;

        public static GateMarkers Create(Transform parent, IslandWorld w, EventDef def, bool explore)
        {
            var go = new GameObject("Gates");
            go.transform.SetParent(parent, false);
            var g = go.AddComponent<GateMarkers>();
            g.Build(w, def, explore);
            return g;
        }

        static Mesh Box(Vector3 size, Color c, bool glow, string name)
        {
            var mb = new MeshBuilder();
            var col = glow ? MeshBuilder.Glow(c) : MeshBuilder.Col(c);
            mb.Box(Vector3.zero, size, Quaternion.identity, col, col);
            return IslandWorld.Finish(mb, name, 0.4f, glow ? 3f : 0f);
        }

        void Build(IslandWorld w, EventDef def, bool explore)
        {
            mat = w.plainMat;
            colMat = new Material(Res.Add) { name = "GateColumn" };
            if (pylon == null)
            {
                var mb = new MeshBuilder();
                var body = MeshBuilder.Col(new Color(0.23f, 0.23f, 0.25f));
                var band = MeshBuilder.Glow(new Color(0.32f, 0.95f, 1f));
                mb.Cylinder(Matrix4x4.TRS(Vector3.zero, Quaternion.identity, new Vector3(4.8f, 44f, 4.8f)), 12, 0.66f, body, body);
                for (int k = 0; k < 3; k++)
                    mb.Cylinder(Matrix4x4.TRS(new Vector3(0, 10f + k * 12f, 0), Quaternion.identity, new Vector3(4.4f - k * 0.5f, 0.8f, 4.4f - k * 0.5f)), 12, 1f, band, band);
                pylon = IslandWorld.Finish(mb, "pylon", 0.45f, 2.5f);
                lamp = Box(new Vector3(4f, 4f, 4f), new Color(0.5f, 0.96f, 1f), true, "lamp");
                beam = Box(new Vector3(1f, 0.9f, 0.9f), new Color(0.5f, 0.96f, 1f), true, "beam");
                var cm = new MeshBuilder();
                var c0 = new Color32(90, 240, 255, 120);
                var c1 = new Color32(90, 240, 255, 0);
                int n = 16;
                for (int i = 0; i < n; i++)
                {
                    float a0 = i * Mathf.PI * 2f / n, a1 = (i + 1) * Mathf.PI * 2f / n;
                    var b0 = new Vector3(Mathf.Cos(a0), 0f, Mathf.Sin(a0)) * 9f;
                    var b1 = new Vector3(Mathf.Cos(a1), 0f, Mathf.Sin(a1)) * 9f;
                    cm.Quad(b0, b0 + Vector3.up * 700f, b1 + Vector3.up * 700f, b1, c0, c1, c1, c0);
                }
                columnMesh = cm.ToMesh("column");
            }
            if (def.kind != EventKind.Explore)
            {
                foreach (var g in def.gates) gates.Add(MakeGate(g, true));
                if (def.kind == EventKind.Circuit) Portal(w, def.gates[def.gates.Length - 1], def.name.ToUpperInvariant(), 0f, def.halfW);
                else Portal(w, def.start, "LARGADA", 140f, def.halfW);
                if (def.finish != null) Portal(w, def.finish, def.economy ? "EXTRAÇÃO" : "META", 0f, def.halfW, def.economy);
            }
            else
            {
                // landmarks: the gates of the Grande Corrida and the start portal of every other event
                foreach (var g in w.data.checkpoints) gates.Add(MakeGate(g, false));
                Portal(w, w.data.start, "EXPEDIÇÃO", 0f, 46f);
                Portal(w, w.data.finish, "EXTRAÇÃO", 0f, 46f, true);
                foreach (var e in w.data.events)
                    Portal(w, e.type == "circuit" ? e.gates[e.gates.Length - 1] : e.start, e.name.ToUpperInvariant(), e.type == "circuit" ? 0f : 30f, e.type == "drag" ? 46f : 34f);
            }
        }

        GameObject Part(Transform parent, string name, Mesh mesh, Vector3 pos, Quaternion rot, Vector3 scale, Material m, bool shadows = true)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.SetPositionAndRotation(pos, rot);
            go.transform.localScale = scale;
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = m;
            r.shadowCastingMode = shadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
            return go;
        }

        Gate MakeGate(WGate g, bool withColumn)
        {
            var root = new GameObject("Gate").transform;
            root.SetParent(transform, false);
            var pos = g.Pos;
            var dir = g.Dir;
            var side = new Vector3(dir.z, 0f, -dir.x);
            var rot = Quaternion.LookRotation(dir);
            float w = g.w >= 150f ? g.w * 0.6f : g.w - 20f;
            foreach (float sg in new[] { -1f, 1f })
            {
                var p = pos + side * sg * w * 0.5f;
                Part(root, "Pylon", pylon, p + Vector3.down * 2f, rot, Vector3.one, mat);
                Part(root, "Lamp", lamp, p + Vector3.up * 43f, rot, Vector3.one, mat, false);
            }
            Part(root, "Beam", beam, pos + Vector3.up * 43f, rot, new Vector3(w, 1f, 1f), mat, false);
            Label(root, g.name, pos + Vector3.up * 52f, rot, 0.4f, new Color(1f, 0.95f, 0.84f));
            var gate = new Gate { root = root.gameObject };
            if (withColumn)
            {
                var col = Part(root, "Column", columnMesh, pos, Quaternion.identity, Vector3.one, colMat, false);
                gate.column = col.transform;
                gate.columnR = col.GetComponent<Renderer>();
                col.SetActive(false);
            }
            return gate;
        }

        static void Label(Transform parent, string text, Vector3 pos, Quaternion rot, float size, Color c)
        {
            if (string.IsNullOrEmpty(text)) return;
            foreach (float flip in new[] { 0f })   // faces the racers that arrive (TextMesh draws both sides)
            {
                var go = new GameObject("Label");
                go.transform.SetParent(parent, false);
                go.transform.SetPositionAndRotation(pos, rot * Quaternion.Euler(0f, flip, 0f));
                var tm = go.AddComponent<TextMesh>();
                tm.text = text.ToUpperInvariant();
                tm.font = Res.Font;
                tm.fontSize = 64;
                tm.characterSize = size;
                tm.anchor = TextAnchor.MiddleCenter;
                tm.alignment = TextAlignment.Center;
                tm.color = c;
                var mr = go.GetComponent<MeshRenderer>();
                mr.sharedMaterial = Res.Font.material;
                mr.shadowCastingMode = ShadowCastingMode.Off;
            }
        }

        void Portal(IslandWorld w, WGate d, string text, float ahead, float halfW, bool extraction = false)
        {
            if (d == null || d.p == null || d.p.Length < 3 || d.dir == null || d.dir.Length < 2) return;
            var dir = d.Dir;
            var pos = d.Pos + dir * ahead;
            if (ahead != 0f) pos.y = w.HeightAt(pos.x, pos.z);
            var e = w.lib.Get("gate");
            if (e == null) return;
            float span = (halfW + 6f) / 47f;
            var rot = Quaternion.LookRotation(dir);
            var go = new GameObject("Portal_" + text);
            go.transform.SetParent(transform, false);
            go.transform.SetPositionAndRotation(pos, rot);
            go.transform.localScale = new Vector3(7.6f * span, 3.6f, 3.6f);
            go.layer = IslandWorld.LayerSolid;
            go.AddComponent<MeshFilter>().sharedMesh = e.mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterials = w.lib.MaterialsFor(e);
            // solid feet only (the arch is high above the road)
            var side = new Vector3(dir.z, 0f, -dir.x);
            foreach (float sg in new[] { -1f, 1f })
            {
                var foot = new GameObject("Foot");
                foot.layer = IslandWorld.LayerSolid;
                foot.transform.SetParent(transform, false);
                foot.transform.position = pos + side * sg * 47f * span + Vector3.up * 20f;
                var cc = foot.AddComponent<CapsuleCollider>();
                cc.radius = 6f;
                cc.height = 40f;
            }
            Label(transform, text, pos + Vector3.up * 58f, rot, 1.1f, new Color(1f, 0.83f, 0.43f));
            if (extraction)
            {
                // extraction pad: glowing ring on the ground after the line
                var mb = new MeshBuilder();
                var g0 = MeshBuilder.Glow(new Color(0.35f, 1f, 0.5f));
                int n = 48;
                for (int i = 0; i < n; i++)
                {
                    float a0 = i * Mathf.PI * 2f / n, a1 = (i + 1) * Mathf.PI * 2f / n;
                    var i0 = new Vector3(Mathf.Cos(a0), 0f, Mathf.Sin(a0));
                    var i1 = new Vector3(Mathf.Cos(a1), 0f, Mathf.Sin(a1));
                    mb.Quad(i0 * 38f, i0 * 42f, i1 * 42f, i1 * 38f, g0);
                    mb.Quad(i0 * 18f, i0 * 20f, i1 * 20f, i1 * 18f, g0);
                }
                var ring = IslandWorld.Finish(mb, "extraction", 0.4f, 2.2f);
                var c = pos + dir * 120f;
                c.y = w.HeightAt(c.x, c.z) + 0.3f;
                Part(transform, "ExtractionPad", ring, c, Quaternion.identity, Vector3.one, mat, false);
            }
        }

        /// <summary>Only the next gate gets the light column; passed gates disappear (sprint) or stay (circuit).</summary>
        public void Highlight(int next, bool hidePassed)
        {
            if (next == highlighted) return;
            highlighted = next;
            for (int i = 0; i < gates.Count; i++)
            {
                var g = gates[i];
                if (g.column != null) g.column.gameObject.SetActive(i == next);
                g.root.SetActive(next < 0 || i >= next || !hidePassed);
            }
        }

        void Update()
        {
            if (colMat != null) colMat.SetColor("_Tint", new Color(1f, 1f, 1f, 0.55f + 0.25f * Mathf.Sin(Time.time * 3f)));
        }
    }
}
