using RedDust.Track;
using UnityEngine;

namespace RedDust.Vehicle
{
    /// <summary>
    /// Sensores dos repulsores: 5 raios ao longo do -cima DA NAVE (não do mundo), para seguir leitos, banks,
    /// half-pipes e paredes. Calcula a altura média, a normal média (suavizada no tempo) e uma normal
    /// antecipada à frente (proporcional à velocidade) para entrar em transições côncavas/convexas sem atraso.
    /// </summary>
    public sealed class HoverSensor
    {
        public struct Probe
        {
            public Vector3 local;
            public float weight;
            public bool hit;
            public float height;
            public Vector3 origin, point, normal;
            public Surface surface;
        }

        const float RayLift = 1.0f;   // origem dos raios acima do plano central (dentro do casco)

        public readonly Probe[] probes;
        public int hits;
        public float height;            // altura média do plano central acima da superfície (ao longo de -cima)
        public Vector3 normalRaw;       // normal média instantânea
        public Vector3 normalAhead;     // normal à frente
        public bool aheadHit;
        public Vector3 normal;          // normal filtrada (usada pela física)
        public Vector3 groundPoint;
        public Collider collider;
        public Vector3 aheadOrigin, aheadPoint;
        public SurfaceTraits traits = SurfaceTraits.Of(Surface.Sand);   // mistura ponderada das superfícies tocadas
        public Surface dominant = Surface.Sand;
        readonly float[] surfaceWeight = new float[5];

        public HoverSensor(CraftTuning t)
        {
            float x = t.probeHalfWidth, z = t.probeHalfLength;
            probes = new[]
            {
                new Probe { local = new Vector3(0f, 0f, z), weight = 1f },
                new Probe { local = new Vector3(0f, 0f, -z), weight = 1f },
                new Probe { local = new Vector3(x, 0f, 0f), weight = 1f },
                new Probe { local = new Vector3(-x, 0f, 0f), weight = 1f },
                new Probe { local = Vector3.zero, weight = 2f },
            };
            normal = Vector3.up;
        }

        public void Reset(Vector3 up) { normal = up; normalRaw = up; normalAhead = up; hits = 0; }

        public void Sample(Transform tr, Vector3 position, Quaternion rotation, Vector3 velocity, CraftTuning t, float dt)
        {
            Vector3 up = rotation * Vector3.up;
            float maxDist = RayLift + t.hoverHeight + t.probeReach;
            hits = 0;
            float hsum = 0f, wsum = 0f;
            for (int k = 0; k < surfaceWeight.Length; k++) surfaceWeight[k] = 0f;
            Vector3 nsum = Vector3.zero, psum = Vector3.zero;
            collider = null;
            for (int i = 0; i < probes.Length; i++)
            {
                ref var p = ref probes[i];
                p.origin = position + rotation * p.local + up * RayLift;
                p.hit = Physics.Raycast(p.origin, -up, out var h, maxDist, Layers.GroundMask, QueryTriggerInteraction.Ignore);
                if (!p.hit) continue;
                p.point = h.point;
                p.normal = SurfaceNormals.Smooth(h);
                p.height = Vector3.Dot(p.origin - h.point, up) - RayLift;
                p.surface = SurfaceTypes.At(h);
                surfaceWeight[(int)p.surface] += p.weight;
                hits++;
                hsum += p.height * p.weight;
                nsum += p.normal * p.weight;
                psum += p.point * p.weight;
                wsum += p.weight;
                if (i == 4 || collider == null) collider = h.collider;
            }
            if (hits > 0)
            {
                height = hsum / wsum;
                normalRaw = nsum.normalized;
                groundPoint = psum / wsum;
                // traços da superfície: média ponderada pelos pesos dos sensores
                var mix = new SurfaceTraits();
                float best = -1f;
                for (int k = 0; k < surfaceWeight.Length; k++)
                {
                    float w = surfaceWeight[k] / wsum;
                    if (w <= 0f) continue;
                    var trait = SurfaceTraits.Of((Surface)k);
                    mix.grip += trait.grip * w; mix.topSpeed += trait.topSpeed * w; mix.drag += trait.drag * w; mix.shake += trait.shake * w;
                    if (surfaceWeight[k] > best) { best = surfaceWeight[k]; dominant = (Surface)k; }
                }
                traits = SurfaceTraits.Lerp(traits, mix, MathX.Damp(12f, dt));
            }
            else
            {
                height = float.PositiveInfinity;
            }

            // normal antecipada: primeiro procura superfície a subir à frente (transição côncava), depois o solo à frente
            aheadHit = false;
            float speed = velocity.magnitude;
            Vector3 n0 = hits > 0 ? normalRaw : up;
            Vector3 fwd = Vector3.ProjectOnPlane(rotation * Vector3.forward, n0);
            if (fwd.sqrMagnitude > 1e-4f && hits >= 2 && speed > 8f)
            {
                fwd.Normalize();
                float look = Mathf.Clamp(speed * t.lookAheadTime, 4f, 26f);
                aheadOrigin = position + n0 * 0.4f;
                if (Physics.Raycast(aheadOrigin, fwd, out var hf, look + 2f, Layers.GroundMask, QueryTriggerInteraction.Ignore)
                    && Vector3.Angle(hf.normal, n0) < 70f)
                {
                    aheadHit = true; aheadPoint = hf.point; normalAhead = SurfaceNormals.Smooth(hf);
                }
                else
                {
                    float lift = 2.5f + look * 0.18f;
                    Vector3 o = position + fwd * look + n0 * lift;
                    if (Physics.Raycast(o, -n0, out var hd, lift + t.hoverHeight + t.probeReach, Layers.GroundMask, QueryTriggerInteraction.Ignore)
                        && Vector3.Angle(hd.normal, n0) < 70f)
                    {
                        aheadHit = true; aheadOrigin = o; aheadPoint = hd.point; normalAhead = SurfaceNormals.Smooth(hd);
                    }
                }
            }

            Vector3 target = n0;
            if (aheadHit) target = (n0 + normalAhead * (0.8f * Mathf.Clamp01(speed / t.topSpeed))).normalized;
            normal = Vector3.Slerp(normal, target, MathX.Damp(1f / Mathf.Max(1e-3f, t.normalSmoothing), dt)).normalized;
        }
    }
}
