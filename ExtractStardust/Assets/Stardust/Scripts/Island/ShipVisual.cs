using UnityEngine;
using UnityEngine.Rendering;

namespace Stardust
{
    /// <summary>
    /// Renders one hover racer: the Blender model (object-space PBR materials, livery tint on painted parts),
    /// engine flames that grow with throttle/nitro, a blob shadow on low quality, and the body animation
    /// (pitch/roll/heave springs from Hovercraft) on top of the interpolated physics pose.
    /// </summary>
    public class ShipVisual : MonoBehaviour
    {
        public Transform body;
        public Renderer[] renderers;
        Transform[] flames;
        Renderer[] flameR;
        Transform blob;
        public Vector3 modelOffset = new Vector3(0f, 0f, -4f);   // the vespa model is born at the cockpit
        public Vector3 cockpit = new Vector3(0f, 2.55f, -0.9f);  // in model space
        float flameLen = 1f;
        MaterialPropertyBlock mpb;
        static Mesh flameMesh, blobMesh;
        static Material flameMat, blobMat;

        public static ShipVisual Create(Transform parent, string model, Color livery, int quality, bool player)
        {
            var go = new GameObject("Ship_" + model);
            go.transform.SetParent(parent, false);
            var v = go.AddComponent<ShipVisual>();
            v.Build(model, livery, quality, player);
            return v;
        }

        void Build(string model, Color livery, int quality, bool player)
        {
            var lib = ModelLibrary.I;
            var e = lib.Get(model) ?? lib.Get("vespa");
            body = new GameObject("Body").transform;
            body.SetParent(transform, false);
            var mg = new GameObject("Model");
            mg.transform.SetParent(body, false);
            mg.transform.localPosition = modelOffset;
            mg.AddComponent<MeshFilter>().sharedMesh = e.mesh;
            var mr = mg.AddComponent<MeshRenderer>();
            mr.sharedMaterials = lib.MaterialsFor(e, true);
            mr.shadowCastingMode = quality >= 1 ? ShadowCastingMode.On : ShadowCastingMode.Off;
            renderers = new Renderer[] { mr };
            mpb = new MaterialPropertyBlock();
            for (int i = 0; i < e.classes.Length; i++)
            {
                if (e.classes[i] != MatClass.Paint) continue;
                mpb.SetColor("_Tint", livery);
                mr.SetPropertyBlock(mpb, i);
            }
            // engine flames at the two exhausts (model space, Godot -> Unity mirrored z)
            if (flameMesh == null) flameMesh = MakeFlame();
            if (flameMat == null) flameMat = Resources.Load<Material>("Stardust/Additive");
            var ex = Exhausts(e.name);
            flames = new Transform[ex.Length];
            flameR = new Renderer[ex.Length];
            for (int i = 0; i < ex.Length; i++)
            {
                var f = new GameObject("Flame");
                f.transform.SetParent(mg.transform, false);
                f.transform.localPosition = ex[i];
                f.transform.localRotation = Quaternion.LookRotation(Vector3.back);
                f.AddComponent<MeshFilter>().sharedMesh = flameMesh;
                var fr = f.AddComponent<MeshRenderer>();
                fr.sharedMaterial = flameMat;
                fr.shadowCastingMode = ShadowCastingMode.Off;
                flames[i] = f.transform;
                flameR[i] = fr;
            }
            if (quality <= 0)
            {
                if (blobMesh == null) blobMesh = MakeBlob();
                if (blobMat == null) blobMat = Resources.Load<Material>("Stardust/AlphaBlend");
                var b = new GameObject("Blob");
                b.transform.SetParent(transform, false);
                b.AddComponent<MeshFilter>().sharedMesh = blobMesh;
                var br = b.AddComponent<MeshRenderer>();
                br.sharedMaterial = blobMat;
                br.shadowCastingMode = ShadowCastingMode.Off;
                blob = b.transform;
            }
        }

        /// <summary>Exhaust points of each podracer model (model space).</summary>
        static Vector3[] Exhausts(string model)
        {
            float x = 2.3f, y = 1.3f, z = 3.27f;
            switch (model)
            {
                case "racer_twin": x = 2.4f; z = 3.3f; break;
                case "racer_hammer": x = 2.6f; y = 1.35f; z = 3.3f; break;
                case "racer_needle": x = 2.3f; y = 1.25f; z = 3.3f; break;
                case "racer_ram": x = 2.5f; y = 1.4f; z = 3.6f; break;
                case "racer_manta": x = 2.5f; z = 3.3f; break;
            }
            return new[] { new Vector3(-x, y, z), new Vector3(x, y, z) };
        }

        static Mesh MakeFlame()
        {
            var mb = new MeshBuilder();
            var hot = new Color32(255, 230, 190, 0);
            var tip = new Color32(255, 90, 30, 0);
            int sides = 8;
            for (int i = 0; i < sides; i++)
            {
                float a0 = i * Mathf.PI * 2f / sides, a1 = (i + 1) * Mathf.PI * 2f / sides;
                var p0 = new Vector3(Mathf.Cos(a0) * 0.45f, Mathf.Sin(a0) * 0.45f, 0f);
                var p1 = new Vector3(Mathf.Cos(a1) * 0.45f, Mathf.Sin(a1) * 0.45f, 0f);
                int b = mb.V.Count;
                mb.V.Add(p0); mb.C.Add(hot);
                mb.V.Add(p1); mb.C.Add(hot);
                mb.V.Add(new Vector3(0f, 0f, 1f)); mb.C.Add(tip);
                mb.T.Add(b); mb.T.Add(b + 1); mb.T.Add(b + 2);
            }
            return mb.ToMesh("flame");
        }

        static Mesh MakeBlob()
        {
            var mb = new MeshBuilder();
            int n = 24;
            var c0 = new Color32(13, 16, 19, 90);
            var c1 = new Color32(13, 16, 19, 0);
            for (int i = 0; i < n; i++)
            {
                float a0 = i * Mathf.PI * 2f / n, a1 = (i + 1) * Mathf.PI * 2f / n;
                int b = mb.V.Count;
                mb.V.Add(Vector3.zero); mb.C.Add(c0);
                mb.V.Add(new Vector3(Mathf.Cos(a1) * 3.2f, 0f, Mathf.Sin(a1) * 6.5f)); mb.C.Add(c1);
                mb.V.Add(new Vector3(Mathf.Cos(a0) * 3.2f, 0f, Mathf.Sin(a0) * 6.5f)); mb.C.Add(c1);
                mb.T.Add(b); mb.T.Add(b + 1); mb.T.Add(b + 2);
            }
            return mb.ToMesh("blob");
        }

        /// <summary>Places the ship from the physics pose (interpolated) and animates the body.</summary>
        public void Pose(Vector3 pos, Quaternion yawRot, Hovercraft h, float dt)
        {
            transform.SetPositionAndRotation(pos, yawRot);
            body.localRotation = Quaternion.Euler(-h.visualPitch * Mathf.Rad2Deg, 0f, -h.roll * Mathf.Rad2Deg);
            body.localPosition = new Vector3(0f, h.heave + h.Bob, 0f);
            float target = h.running ? (h.nitroActive ? 3.2f : h.boost > 1f ? 2.2f : 0.9f + h.SpeedFraction * 0.8f) : 0.35f;
            if (h.input.brake) target *= 0.5f;
            flameLen = Mathf.Lerp(flameLen, target, 1f - Mathf.Exp(-dt * 10f));
            float flick = 1f + Mathf.Sin(Time.time * 47f) * 0.08f + Mathf.Sin(Time.time * 83f) * 0.05f;
            for (int i = 0; i < flames.Length; i++)
                flames[i].localScale = new Vector3(1f + (h.nitroActive ? 0.25f : 0f), 1f + (h.nitroActive ? 0.25f : 0f), flameLen * 3.2f * flick);
            if (blob != null)
            {
                bool show = h.groundValid && h.position.y - h.groundPoint.y < 12f;
                blob.gameObject.SetActive(show);
                if (show)
                {
                    var n = h.groundNormal;
                    var f = Vector3.ProjectOnPlane(h.Forward, n).normalized;
                    blob.SetPositionAndRotation(h.groundPoint + n * 0.08f, Quaternion.LookRotation(f, n));
                }
            }
        }

        /// <summary>World position of the cockpit camera.</summary>
        public Vector3 CockpitPoint => body.TransformPoint(modelOffset + cockpit);
    }
}
