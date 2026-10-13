using System.Collections.Generic;
using System.IO;
using System.Linq;
using RedDust.Game;
using RedDust.Meta;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RedDust.EditorTools
{
    /// <summary>Fotografa as naves V2 no Unity (de série e com módulos grandes montados) para verificar orientação,
    /// escala, materiais e peças: Logs/v2_unity/&lt;chassis&gt;_{stock,mod,front}.png.</summary>
    public static class V2Shots
    {
        const int W = 1400, H = 900;

        [MenuItem("Red Dust/7. Fotografar naves V2")]
        public static void Run()
        {
            ProjectSetup.ConfigureUrp();
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene);
            var sun = new GameObject("Sun").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 1.4f;
            sun.shadows = LightShadows.Soft;
            sun.transform.rotation = Quaternion.Euler(42f, -40f, 0f);
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.42f, 0.40f, 0.38f);
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            ground.transform.localScale = Vector3.one * 6f;
            ground.GetComponent<MeshRenderer>().sharedMaterial = ShipBuilder.Mat("RedDust/CraftMetal", new Color(0.55f, 0.47f, 0.40f));
            var cam = new GameObject("ShotCam").AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.80f, 0.78f, 0.76f);
            cam.nearClipPlane = 0.1f;
            var data = cam.gameObject.AddComponent<UniversalAdditionalCameraData>();
            data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;

            string dir = Path.Combine("Logs", "v2_unity");
            Directory.CreateDirectory(dir);
            var rng = new Rng(7);
            EquipmentInstance Pick(Family f, params string[] visuals)
            {
                var def = Catalog.Regular.FirstOrDefault(e => e.family == f && visuals.Contains(e.visual)) ?? Catalog.Regular.FirstOrDefault(e => e.family == f);
                return def == null ? null : ItemFactory.Create(def, Rarity.Rare, rng, "v2shots", "editor");
            }
            var mod = new Dictionary<string, EquipmentInstance>
            {
                ["Propulsion"] = Pick(Family.Propulsion, "prop_large", "prop_heavy"), ["PropulsionC"] = Pick(Family.Propulsion, "prop_large", "prop_heavy"),
                ["Wings"] = Pick(Family.Wings, "wing_long"), ["Armor"] = Pick(Family.Armor, "armor_heavy"), ["Armor2"] = Pick(Family.Armor, "armor_heavy"),
                ["Cooling"] = Pick(Family.Cooling, "cooling_grid"), ["Utility"] = Pick(Family.Utility, "util_mast"), ["Tail"] = Pick(Family.Tail, "tail_long"),
                ["Engine"] = Pick(Family.Engine, "engine_redline"), ["Reactor"] = Pick(Family.Reactor, "reactor_flux"),
            };
            float hover = 1.5f;
            foreach (var c in Catalog.Chassis)
                foreach (var (tag, mounted) in new[] { ("stock", (Dictionary<string, EquipmentInstance>)null), ("mod", mod) })
                {
                    var parent = new GameObject(c.id).transform;
                    parent.position = new Vector3(0f, hover, 0f);
                    var glow = ShipBuilder.GlowFor(mounted != null && mounted.TryGetValue("Reactor", out var re) ? re : null);
                    var vis = V2ShipVisual.BuildOn(parent, hover, null, c, mounted, ShipBuilder.Paint(c.paint), glow);
                    if (vis == null) { Debug.LogError($"[V2 shots] {c.id}: modelo V2 em falta (Resources/V2Chassis/{c.id})"); Object.DestroyImmediate(parent.gameObject); continue; }
                    var b = new Bounds(parent.position, Vector3.zero);
                    foreach (var r in vis.GetComponentsInChildren<Renderer>()) b.Encapsulate(r.bounds);
                    Debug.Log($"[V2 shots] {c.id} {tag}: {b.size.x:0.00} x {b.size.y:0.00} x {b.size.z:0.00} m, chão em {b.min.y:0.00}, renderers {vis.GetComponentsInChildren<Renderer>().Length}");
                    cam.fieldOfView = 32f;
                    cam.transform.position = b.center + new Vector3(6.2f, 3.4f, 8.6f);
                    cam.transform.LookAt(b.center);
                    Shot(cam, Path.Combine(dir, $"{c.id}_{tag}.png"));
                    if (tag == "stock")
                    {
                        cam.fieldOfView = 24f;
                        cam.transform.position = new Vector3(0f, b.center.y + 0.6f, b.max.z + 11f);
                        cam.transform.LookAt(new Vector3(0f, b.center.y, 0f));
                        Shot(cam, Path.Combine(dir, $"{c.id}_front.png"));
                    }
                    Object.DestroyImmediate(parent.gameObject);
                }
            Debug.Log("[V2 shots] OK");
        }

        static void Shot(Camera cam, string path)
        {
            var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 1 };
            rt.Create();
            var req = new RenderPipeline.StandardRequest { destination = rt };
            if (RenderPipeline.SupportsRenderRequest(cam, req)) RenderPipeline.SubmitRenderRequest(cam, req);
            else { cam.targetTexture = rt; cam.Render(); cam.targetTexture = null; }
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            var tex = new Texture2D(W, H, TextureFormat.RGBA32, false, false);
            tex.ReadPixels(new Rect(0, 0, W, H), 0, 0);
            tex.Apply();
            RenderTexture.active = prev;
            File.WriteAllBytes(path, tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
            rt.Release();
            Object.DestroyImmediate(rt);
        }
    }
}
