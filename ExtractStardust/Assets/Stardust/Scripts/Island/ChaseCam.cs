using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Stardust
{
    /// <summary>
    /// Follow camera (port of camera_rig.gd): lagged anchor above the ship, spring arm that never goes through
    /// walls, pitch that anticipates jumps, slight banking, speed FOV, right-stick look-around, cockpit view,
    /// landing suspension, shake and kick. Also a free "intro/orbit/finish" mode for cinematics.
    /// </summary>
    public class ChaseCam : MonoBehaviour
    {
        public enum Mode { Chase, Cockpit, Orbit, Intro, Finish, Wreck }

        public Camera cam;
        public Mode mode = Mode.Chase;
        public float shakeScale = 1f;
        const float FollowHeight = 2.4f, ArmMargin = 0.35f;

        Hovercraft h;
        ShipVisual vis;
        Vector3 shipPos;
        float yaw, pitch, roll, shake, kick, t, suspension, suspensionV, armLen = 19f;
        Vector3 followPos, lastVel;
        bool wasGrounded;
        float lookYaw, lookPitch, lookIdle;
        float orbitAngle;
        Vector3 smoothPos;
        public Vector2 lookInput;
        public bool lookCenter;

        public static ChaseCam Create(Transform parent, string name, Rect rect, float far, bool listener)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var c = go.AddComponent<ChaseCam>();
            c.cam = go.AddComponent<Camera>();
            c.cam.rect = rect;
            c.cam.nearClipPlane = 0.3f;
            c.cam.farClipPlane = far;
            c.cam.fieldOfView = 72f;
            var data = c.cam.GetUniversalAdditionalCameraData();
            data.renderPostProcessing = true;
            data.antialiasing = AntialiasingMode.None;
            if (listener) go.AddComponent<AudioListener>();
            return c;
        }

        public void SetTarget(Hovercraft target, ShipVisual visual)
        {
            h = target;
            vis = visual;
            Snap();
        }

        public void Shake(float amount = 0.8f) => shake = Mathf.Max(shake, Mathf.Clamp(amount, 0f, 1.5f) * shakeScale);
        public void Kick(float amount = 1f) => kick = Mathf.Max(kick, Mathf.Clamp(amount, 0f, 1.5f));

        float TargetPitch()
        {
            float p = h.visualPitch * 0.65f;
            if (!h.onGround)
            {
                float hs = new Vector2(h.vel.x, h.vel.z).magnitude;
                p = h.visualPitch * 0.45f + Mathf.Atan2(h.vel.y, Mathf.Max(hs, 12f)) * 0.18f;
            }
            return Mathf.Clamp(-6f * Mathf.Deg2Rad + p, -28f * Mathf.Deg2Rad, 25f * Mathf.Deg2Rad);
        }

        float TargetRoll()
        {
            float bank = h.steer * 3f * Mathf.Deg2Rad;
            if (h.onGround && h.groundValid)
            {
                var n = Quaternion.Inverse(h.Rotation) * h.groundNormal;
                bank += Mathf.Atan2(n.x, Mathf.Max(n.y, 0.2f)) * 0.16f;
            }
            else bank *= 0.4f;
            return Mathf.Clamp(bank, -5f * Mathf.Deg2Rad, 5f * Mathf.Deg2Rad) * shakeScale;
        }

        float TargetFov()
        {
            float curve = Mathf.Pow(h.SpeedFraction, 2.4f);
            float boostRatio = Mathf.Clamp01(h.boost / Hovercraft.BoostMax + (h.nitroActive ? 1f : 0f));
            if (mode == Mode.Cockpit) return Mathf.Clamp(78f + 14f * curve + 3f * boostRatio + kick, 78f, 95f);
            return Mathf.Clamp(72f + 16f * curve + 5f * boostRatio + 2f * kick, 72f, 93f);
        }

        public void Snap()
        {
            if (h == null) return;
            shipPos = h.position;
            yaw = h.yaw;
            pitch = TargetPitch();
            roll = shake = kick = t = 0f;
            lookYaw = lookPitch = lookIdle = 0f;
            suspension = suspensionV = 0f;
            lastVel = h.vel;
            wasGrounded = h.onGround;
            followPos = shipPos + Vector3.up * FollowHeight;
            armLen = Mathf.Lerp(19f, 17f, h.SpeedFraction);
            cam.fieldOfView = TargetFov();
            Place(0f);
        }

        void UpdateLook(float dt)
        {
            if (lookCenter) { lookYaw = lookPitch = lookIdle = 0f; }
            else if (lookInput.sqrMagnitude > 0.001f)
            {
                lookYaw = Mathf.Clamp(lookYaw + lookInput.x * 2.6f * dt, -Mathf.PI, Mathf.PI);
                lookPitch = Mathf.Clamp(lookPitch + lookInput.y * 1.7f * dt, -0.6f, 0.6f);
                lookIdle = 0f;
            }
            else
            {
                lookIdle += dt;
                if (lookIdle > 1.5f)
                {
                    lookYaw = Mathf.Lerp(lookYaw, 0f, 1f - Mathf.Exp(-3f * dt));
                    lookPitch = Mathf.Lerp(lookPitch, 0f, 1f - Mathf.Exp(-3f * dt));
                }
            }
        }

        void UpdateSuspension(float dt)
        {
            if (h.onGround && !wasGrounded)
            {
                float impact = Mathf.Max(0f, -Vector3.Dot(lastVel, h.groundNormal));
                suspensionV -= Mathf.Min(impact * 0.22f, 4.5f);
            }
            else if (!h.onGround && wasGrounded) suspensionV += Mathf.Clamp(h.vel.y * 0.08f, 0f, 1.1f);
            wasGrounded = h.onGround;
            lastVel = h.vel;
            // exact critically damped spring: same response at any frame rate
            float omega = 10f, decay = Mathf.Exp(-omega * dt);
            float c = suspensionV + omega * suspension;
            suspension = (suspension + c * dt) * decay;
            suspensionV = (suspensionV - omega * c * dt) * decay;
            suspension = Mathf.Clamp(suspension, -0.25f, 0.12f);
        }

        /// <summary>Call every rendered frame with the interpolated ship position.</summary>
        public void Tick(Vector3 interpolatedPos, float dt)
        {
            if (h == null) return;
            shipPos = interpolatedPos;
            t += dt;
            shake = Mathf.MoveTowards(shake, 0f, 1.8f * dt);
            kick = Mathf.MoveTowards(kick, 0f, 2.5f * dt);
            UpdateLook(dt);
            UpdateSuspension(dt);
            Place(dt);
        }

        void Place(float dt)
        {
            float k(float rate) => dt <= 0f ? 1f : 1f - Mathf.Exp(-rate * dt);
            switch (mode)
            {
                case Mode.Cockpit:
                {
                    var rot = vis != null ? vis.body.rotation : h.Rotation;
                    var pos = vis != null ? vis.CockpitPoint : shipPos + Vector3.up * 2.5f;
                    transform.SetPositionAndRotation(pos, rot * Quaternion.Euler((0.06f - lookPitch) * Mathf.Rad2Deg, lookYaw * Mathf.Rad2Deg, 0f));
                    break;
                }
                case Mode.Orbit:
                case Mode.Intro:
                case Mode.Finish:
                case Mode.Wreck:
                {
                    orbitAngle += dt * (mode == Mode.Intro ? 0.22f : 0.12f);
                    float dist = mode == Mode.Intro ? Mathf.Lerp(60f, 22f, Mathf.Clamp01(t / 6f)) : mode == Mode.Wreck ? 28f : 16f;
                    float height = mode == Mode.Intro ? Mathf.Lerp(30f, 5f, Mathf.Clamp01(t / 6f)) : mode == Mode.Wreck ? 14f : 4f;
                    float a = h.yaw + Mathf.PI + Mathf.Sin(orbitAngle) * (mode == Mode.Intro ? 1.2f : 2.4f);
                    var want = shipPos + new Vector3(Mathf.Sin(a) * dist, height, Mathf.Cos(a) * dist);
                    want = ResolveArm(shipPos + Vector3.up * 2f, want);
                    smoothPos = dt <= 0f ? want : Vector3.Lerp(smoothPos, want, k(3f));
                    transform.SetPositionAndRotation(smoothPos, Quaternion.LookRotation(shipPos + Vector3.up * 1.5f - smoothPos));
                    break;
                }
                default:
                {
                    followPos = Vector3.Lerp(followPos, shipPos + Vector3.up * FollowHeight, k(10f));
                    if (dt <= 0f) followPos = shipPos + Vector3.up * FollowHeight;
                    var anchor = followPos + Vector3.up * suspension * shakeScale;
                    yaw = Mathf.LerpAngle(yaw * Mathf.Rad2Deg, h.yaw * Mathf.Rad2Deg, k(5f)) * Mathf.Deg2Rad;
                    pitch = Mathf.Lerp(pitch, TargetPitch(), k(4.5f));
                    roll = Mathf.Lerp(roll, TargetRoll(), k(6f));
                    float p = Mathf.Clamp(pitch + lookPitch, -1.1f, 0.8f);
                    var rot = Quaternion.Euler(-p * Mathf.Rad2Deg, (yaw + lookYaw) * Mathf.Rad2Deg, -roll * Mathf.Rad2Deg);
                    armLen = Mathf.Lerp(armLen, Mathf.Lerp(19f, 17f, h.SpeedFraction), k(5f));
                    var want = anchor + rot * new Vector3(0f, 0f, -armLen);
                    var pos = ResolveArm(anchor, want);
                    smoothPos = pos;
                    transform.SetPositionAndRotation(pos, rot);
                    break;
                }
            }
            if (dt > 0f) cam.fieldOfView = Mathf.Lerp(cam.fieldOfView, mode == Mode.Chase || mode == Mode.Cockpit ? TargetFov() : 60f, k(5f));
            ApplyShake();
        }

        Vector3 ResolveArm(Vector3 anchor, Vector3 want)
        {
            var d = want - anchor;
            float len = d.magnitude;
            if (len < 0.01f) return want;
            var dir = d / len;
            if (Physics.SphereCast(anchor, ArmMargin, dir, out var hit, len, IslandWorld.ViewBlockMask, QueryTriggerInteraction.Ignore))
                return anchor + dir * Mathf.Max(0.5f, hit.distance - 0.05f);
            return want;
        }

        void ApplyShake()
        {
            float hum = 0f;
            if (h.running) hum = 0.034f * h.SpeedFraction * (h.onGround ? 1f : 0.25f);
            float amount = (hum + shake * 0.045f) * shakeScale * (mode == Mode.Cockpit ? 0.35f : 1f);
            if (amount <= 0f) return;
            float nx = (Mathf.PerlinNoise(t * 14f, 0.3f) - 0.5f) * 2f;
            float ny = (Mathf.PerlinNoise(t * 14f + 73f, 0.7f) - 0.5f) * 2f;
            float nr = (Mathf.PerlinNoise(t * 11f + 191f, 0.1f) - 0.5f) * 2f;
            transform.position += transform.right * Mathf.Clamp(nx * amount, -0.08f, 0.08f) + transform.up * Mathf.Clamp(ny * amount, -0.08f, 0.08f);
            transform.rotation *= Quaternion.Euler(0f, 0f, nr * amount * 0.14f * Mathf.Rad2Deg);
        }

        public void SetMode(Mode m)
        {
            if (mode == m) return;
            mode = m;
            t = 0f;
            orbitAngle = 0f;
            smoothPos = transform.position;
            if (m == Mode.Chase || m == Mode.Cockpit) Snap();
        }
    }
}
