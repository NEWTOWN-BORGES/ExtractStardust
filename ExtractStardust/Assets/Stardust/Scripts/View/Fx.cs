using System.Collections.Generic;
using UnityEngine;

namespace Stardust
{
    /// <summary>Particle factories and pooled one-shot effects (explosions, impacts, lightning).</summary>
    public class Fx : MonoBehaviour
    {
        public static Fx I;
        ParticleSystem explosion, fire, debris, impact, landing;
        readonly List<Bolt> bolts = new List<Bolt>();
        readonly List<Ring> rings = new List<Ring>();
        readonly List<Flash> flashes = new List<Flash>();
        int quality;

        class Bolt { public LineRenderer lr; public float t; }
        class Ring { public Transform tr; public Material mat; public Strike strike; }
        class Flash { public Transform tr; public Material mat; public float t, dur, size; public Color col; }

        public static Fx Create(Transform parent, int quality)
        {
            var go = new GameObject("Fx");
            go.transform.SetParent(parent, false);
            var fx = go.AddComponent<Fx>();
            fx.quality = quality;
            fx.Build();
            I = fx;
            return fx;
        }

        static ParticleSystem Base(Transform parent, string name, Material mat, int max)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = max;
            main.playOnAwake = false;
            main.scalingMode = ParticleSystemScalingMode.Hierarchy;
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
            return ps;
        }

        static void Gradient(ParticleSystem ps, Color a, Color b, float a0 = 1f)
        {
            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(a, 0), new GradientColorKey(b, 1) }, new[] { new GradientAlphaKey(a0, 0), new GradientAlphaKey(a0 * 0.6f, 0.4f), new GradientAlphaKey(0, 1) });
            col.color = g;
        }

        public static ParticleSystem MakeSmoke(Transform parent, int max)
        {
            var ps = Base(parent, "Smoke", Res.AlphaSoft, max);
            var m = ps.main;
            m.startLifetime = new ParticleSystem.MinMaxCurve(1.2f, 2.2f);
            m.startSpeed = new ParticleSystem.MinMaxCurve(1f, 3f);
            m.startSize = new ParticleSystem.MinMaxCurve(1.5f, 3f);
            m.startColor = new Color(0.15f, 0.14f, 0.14f, 0.7f);
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 0.6f;
            var sz = ps.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0, 0.6f, 1, 2.2f));
            Gradient(ps, new Color(0.3f, 0.28f, 0.27f), new Color(0.1f, 0.1f, 0.1f), 0.7f);
            var e = ps.emission; e.rateOverTime = 0f;
            ps.transform.localPosition = new Vector3(0, 0.5f, -1.5f);
            ps.Play();
            return ps;
        }

        public static ParticleSystem MakeSparks(Transform parent, int max)
        {
            var ps = Base(parent, "Sparks", Res.AddSoft, max);
            var m = ps.main;
            m.startLifetime = new ParticleSystem.MinMaxCurve(0.25f, 0.6f);
            m.startSpeed = new ParticleSystem.MinMaxCurve(6f, 16f);
            m.startSize = new ParticleSystem.MinMaxCurve(0.15f, 0.35f);
            m.startColor = new Color(1f, 0.75f, 0.3f, 1f);
            m.gravityModifier = 1.2f;
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 1f;
            var r = ps.GetComponent<ParticleSystemRenderer>();
            r.renderMode = ParticleSystemRenderMode.Stretch;
            r.velocityScale = 0.06f;
            r.lengthScale = 1f;
            Gradient(ps, new Color(1f, 0.9f, 0.5f), new Color(1f, 0.3f, 0.1f));
            var e = ps.emission; e.rateOverTime = 0f;
            ps.Play();
            return ps;
        }

        public static ParticleSystem MakeDust(Transform parent)
        {
            var ps = Base(parent, "Dust", Res.AlphaSoft, 120);
            var m = ps.main;
            m.startLifetime = new ParticleSystem.MinMaxCurve(0.8f, 1.6f);
            m.startSpeed = new ParticleSystem.MinMaxCurve(1f, 4f);
            m.startSize = new ParticleSystem.MinMaxCurve(2f, 4.5f);
            m.startColor = new Color(0.85f, 0.65f, 0.45f, 0.35f);
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = new Vector3(4f, 0.2f, 1f);
            var sz = ps.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0, 0.7f, 1, 2f));
            Gradient(ps, new Color(0.9f, 0.72f, 0.5f), new Color(0.8f, 0.6f, 0.45f), 0.35f);
            var e = ps.emission; e.rateOverTime = 0f;
            ps.transform.localPosition = new Vector3(0, -1.2f, -3f);
            ps.Play();
            return ps;
        }

        void Build()
        {
            explosion = Base(transform, "Explosion", Res.AddSoft, 200);
            {
                var m = explosion.main;
                m.startLifetime = new ParticleSystem.MinMaxCurve(0.4f, 1.1f);
                m.startSpeed = new ParticleSystem.MinMaxCurve(8f, 30f);
                m.startSize = new ParticleSystem.MinMaxCurve(3f, 8f);
                m.startColor = new Color(1f, 0.6f, 0.25f, 1f);
                var sh = explosion.shape; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 1.5f;
                var sz = explosion.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0, 1f, 1, 0.2f));
                Gradient(explosion, new Color(1f, 0.85f, 0.5f), new Color(0.9f, 0.2f, 0.05f));
                var e = explosion.emission; e.rateOverTime = 0;
                explosion.Play();
            }
            fire = Base(transform, "Fireball", Res.AlphaSoft, 120);
            {
                var m = fire.main;
                m.startLifetime = new ParticleSystem.MinMaxCurve(1.5f, 3f);
                m.startSpeed = new ParticleSystem.MinMaxCurve(2f, 8f);
                m.startSize = new ParticleSystem.MinMaxCurve(5f, 10f);
                m.startColor = new Color(0.12f, 0.1f, 0.1f, 0.8f);
                var sh = fire.shape; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 2f;
                var sz = fire.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0, 0.6f, 1, 2.2f));
                Gradient(fire, new Color(0.25f, 0.2f, 0.18f), new Color(0.08f, 0.08f, 0.08f), 0.8f);
                var e = fire.emission; e.rateOverTime = 0;
                fire.Play();
            }
            debris = Base(transform, "Debris", Res.AddSoft, 150);
            {
                var m = debris.main;
                m.startLifetime = new ParticleSystem.MinMaxCurve(0.6f, 1.6f);
                m.startSpeed = new ParticleSystem.MinMaxCurve(10f, 35f);
                m.startSize = new ParticleSystem.MinMaxCurve(0.2f, 0.5f);
                m.startColor = new Color(1f, 0.8f, 0.4f, 1f);
                m.gravityModifier = 2f;
                var sh = debris.shape; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 1f;
                var r = debris.GetComponent<ParticleSystemRenderer>();
                r.renderMode = ParticleSystemRenderMode.Stretch; r.velocityScale = 0.05f;
                Gradient(debris, new Color(1f, 0.9f, 0.5f), new Color(1f, 0.3f, 0.05f));
                var e = debris.emission; e.rateOverTime = 0;
                debris.Play();
            }
            impact = Base(transform, "Impact", Res.AddSoft, 160);
            {
                var m = impact.main;
                m.startLifetime = new ParticleSystem.MinMaxCurve(0.2f, 0.5f);
                m.startSpeed = new ParticleSystem.MinMaxCurve(8f, 22f);
                m.startSize = new ParticleSystem.MinMaxCurve(0.15f, 0.4f);
                m.startColor = new Color(1f, 0.85f, 0.5f, 1f);
                m.gravityModifier = 1.5f;
                var sh = impact.shape; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 0.8f;
                var r = impact.GetComponent<ParticleSystemRenderer>();
                r.renderMode = ParticleSystemRenderMode.Stretch; r.velocityScale = 0.05f;
                Gradient(impact, new Color(1f, 1f, 0.7f), new Color(1f, 0.4f, 0.1f));
                var e = impact.emission; e.rateOverTime = 0;
                impact.Play();
            }
            landing = Base(transform, "Landing", Res.AlphaSoft, 80);
            {
                var m = landing.main;
                m.startLifetime = new ParticleSystem.MinMaxCurve(0.8f, 1.5f);
                m.startSpeed = new ParticleSystem.MinMaxCurve(3f, 9f);
                m.startSize = new ParticleSystem.MinMaxCurve(2f, 5f);
                m.startColor = new Color(0.85f, 0.7f, 0.5f, 0.45f);
                var sh = landing.shape; sh.shapeType = ParticleSystemShapeType.Circle; sh.radius = 3f;
                sh.rotation = new Vector3(-90f, 0, 0);
                Gradient(landing, new Color(0.9f, 0.75f, 0.55f), new Color(0.8f, 0.65f, 0.5f), 0.45f);
                var e = landing.emission; e.rateOverTime = 0;
                landing.Play();
            }
        }

        static void Burst(ParticleSystem ps, Vector3 pos, int count)
        {
            if (!ps) return;
            var ep = new ParticleSystem.EmitParams { position = pos, applyShapeToPosition = true };
            ps.Emit(ep, count);
        }

        public void Explode(Vector3 pos)
        {
            int k = quality == 0 ? 1 : 2;
            Burst(explosion, pos, 30 * k);
            Burst(fire, pos, 10 * k);
            Burst(debris, pos, 25 * k);
            FlashAt(pos, new Color(1f, 0.6f, 0.25f), 40f, 0.5f);
        }

        public void Impact(Vector3 pos, float strength)
        {
            Burst(impact, pos, Mathf.Clamp(Mathf.RoundToInt(strength * 2f), 6, 40));
            if (strength > 10f) FlashAt(pos, new Color(1f, 0.8f, 0.5f), 10f, 0.15f);
        }

        public void Land(Vector3 pos) => Burst(landing, pos, quality == 0 ? 6 : 14);

        public void StrikeWarn(Strike s)
        {
            Ring ring = null;
            foreach (var r in rings) if (r.strike == null) { ring = r; break; }
            if (ring == null)
            {
                ring = new Ring();
                var go = new GameObject("StrikeRing");
                go.transform.SetParent(transform, false);
                var mb = new MeshBuilder();
                var c = new Color32(255, 255, 255, 255);
                mb.QuadUV(new Vector3(-.5f, 0, -.5f), new Vector3(-.5f, 0, .5f), new Vector3(.5f, 0, .5f), new Vector3(.5f, 0, -.5f), c, c, c, c);
                go.AddComponent<MeshFilter>().sharedMesh = mb.ToMesh("ring");
                ring.mat = new Material(Res.AddRing);
                go.AddComponent<MeshRenderer>().sharedMaterial = ring.mat;
                ring.tr = go.transform;
                rings.Add(ring);
            }
            ring.strike = s;
            ring.tr.gameObject.SetActive(true);
        }

        public void Lightning(Vector3 ground)
        {
            Bolt b = null;
            foreach (var x in bolts) if (x.t <= 0f) { b = x; break; }
            if (b == null)
            {
                b = new Bolt();
                var go = new GameObject("Bolt");
                go.transform.SetParent(transform, false);
                b.lr = go.AddComponent<LineRenderer>();
                b.lr.sharedMaterial = Res.Add;
                b.lr.positionCount = 12;
                b.lr.widthMultiplier = 1.4f;
                b.lr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                bolts.Add(b);
            }
            var top = ground + Vector3.up * 160f + Random.insideUnitSphere * 20f;
            for (int i = 0; i < 12; i++)
            {
                float t = i / 11f;
                var p = Vector3.Lerp(top, ground, t);
                if (i > 0 && i < 11) p += Random.insideUnitSphere * 6f * (1f - t * 0.5f);
                b.lr.SetPosition(i, p);
            }
            b.t = 0.28f;
            b.lr.enabled = true;
            FlashAt(ground + Vector3.up * 3f, new Color(0.7f, 0.85f, 1f), 50f, 0.3f);
            Burst(impact, ground, 30);
        }

        void FlashAt(Vector3 pos, Color col, float size, float dur)
        {
            Flash f = null;
            foreach (var x in flashes) if (x.t <= 0f) { f = x; break; }
            if (f == null)
            {
                f = new Flash();
                var go = new GameObject("Flash");
                go.transform.SetParent(transform, false);
                var mb = new MeshBuilder();
                mb.Halo(Vector3.zero, Vector3.up, Vector3.right, 1f, new Color32(255, 255, 255, 255));
                mb.Halo(Vector3.zero, Vector3.forward, Vector3.right, 1f, new Color32(255, 255, 255, 255));
                go.AddComponent<MeshFilter>().sharedMesh = mb.ToMesh("flash");
                f.mat = new Material(Res.AddSoft);
                go.AddComponent<MeshRenderer>().sharedMaterial = f.mat;
                f.tr = go.transform;
                flashes.Add(f);
            }
            f.tr.position = pos;
            f.t = dur; f.dur = dur; f.size = size; f.col = col;
            f.tr.gameObject.SetActive(true);
        }

        public void ResetAll()
        {
            foreach (var r in rings) { r.strike = null; r.tr.gameObject.SetActive(false); }
            foreach (var b in bolts) { b.t = 0f; b.lr.enabled = false; }
            foreach (var f in flashes) { f.t = 0f; f.tr.gameObject.SetActive(false); }
            foreach (var ps in new[] { explosion, fire, debris, impact, landing }) if (ps) ps.Clear();
        }

        void Update()
        {
            float dt = Time.deltaTime;
            foreach (var b in bolts)
            {
                if (b.t <= 0f) continue;
                b.t -= dt;
                b.lr.widthMultiplier = 1.8f * Mathf.Clamp01(b.t / 0.28f) * (0.7f + Random.value * 0.6f);
                if (b.t <= 0f) b.lr.enabled = false;
            }
            foreach (var f in flashes)
            {
                if (f.t <= 0f) continue;
                f.t -= dt;
                float k = Mathf.Clamp01(f.t / f.dur);
                f.tr.localScale = Vector3.one * f.size * (1.4f - k * 0.4f);
                var c = f.col; c.a = k;
                f.mat.SetColor("_Tint", c);
                if (f.t <= 0f) f.tr.gameObject.SetActive(false);
            }
            foreach (var r in rings)
            {
                if (r.strike == null) continue;
                var s = r.strike;
                if (s.fired || s.age > 3f)
                {
                    r.strike = null;
                    r.tr.gameObject.SetActive(false);
                    continue;
                }
                float k = 1f - Mathf.Clamp01(s.timer / 1.3f);
                r.tr.position = s.world + Vector3.up * 0.15f;
                r.tr.localScale = Vector3.one * s.radius * 2f * (1.15f - 0.15f * k);
                float pulse = 0.55f + 0.45f * Mathf.Sin(Time.time * (10f + k * 25f));
                r.mat.SetColor("_Tint", new Color(1f, 0.25f + 0.4f * (1f - k), 0.15f, pulse));
            }
        }
    }
}
