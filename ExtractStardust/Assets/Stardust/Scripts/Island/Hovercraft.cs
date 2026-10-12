using System.Collections.Generic;
using UnityEngine;

namespace Stardust
{
    public struct ShipControls
    {
        public float steer;     // -1 left .. +1 right (analog amplitude preserved)
        public bool brake;      // handbrake: brake + steer = drift
        public bool nitro;
    }

    /// <summary>
    /// Hover-racer physics (port of RACESTARS podracer.gd, the "Vespa"): floats on terrain and water, accelerates by
    /// itself, wider turns at speed, handbrake drifts that charge a boost, walls bounce instead of stopping the race.
    /// Kinematic: support raycasts + a box hull swept against the solid layers (own collide-and-slide).
    /// Unity axes: forward = (sin yaw, 0, cos yaw), steer &gt; 0 turns right.
    /// Layers: Ground (terrain) + Solid collide with the hull; RideOver (low rocks) and Water only hold the suspension.
    /// </summary>
    public class Hovercraft
    {
        public const float MaxSpeed = 125f;        // m/s (450 km/h)
        public const float Accel = 19f;
        public const float TurnLow = 1.9f, TurnHigh = 0.55f;
        public const float Grip = 2.6f, HbTurn = 2.2f, HbGrip = 0.35f, HbDecel = 7f, HbDecelStraight = 14f;
        public const float BoostMax = 16f, PadPush = 18f, SpeedCap = 160f;
        public const float NitroDrain = 25f, NitroExtra = 30f;
        public const float Hover = 1.1f, Spring = 70f, Damp = 16.75f, Gravity = 24f;
        public const float SupportMinY = 0.64f, WaterSpeed = 0.8f;
        public static readonly Vector3 HullHalf = new Vector3(2.7f, 0.6f, 5f);
        public static readonly Vector3 HullOffset = new Vector3(0f, 1.7f, 0f);
        const float Skin = 0.04f;

        // tuning per ship (equipment / bot skill)
        public float topSpeedMul = 1f, accelMul = 1f, gripMul = 1f, nitroMul = 1f, nitroRegen = 2.2f;

        public Vector3 position;
        public Vector3 vel;
        public float yaw;                 // radians
        public bool running;
        public bool controlsBlocked;
        public ShipControls input;
        public float steer;
        public bool onGround, onWater, groundValid, drifting, nitroActive;
        public float slip, driftCharge, boost, nitro = 50f;
        public Vector3 groundNormal = Vector3.up, groundPoint;
        public float airTime;
        public float lastImpact;          // strength of the worst wall impact this step (0 = none)
        public Vector3 lastImpactNormal;
        public Collider lastImpactCollider;
        public float lastLanding;         // landing speed this step (0 = none)
        public bool boostedThisStep;
        public float boostAmount;
        public string nitroReason;        // bonus nitro this step (DERRAPAGEM, SALTO, QUASE BATIDA)
        public float nitroGain;
        public Quaternion hullRot = Quaternion.identity;
        public bool onPad;

        // visual springs (body animation, independent from the physics hull)
        public float visualPitch, roll, heave, steerVisual;
        float pitchV, rollV, heaveV, groundPitch;
        float t;
        Vector3 jumpOrigin;
        bool jumpEligible;
        bool nitroWas;
        // near miss
        float nearClock, nearRewardT = -100f, nearCollisionT = -100f;
        Collider nearId, nearLast;
        Vector3 nearStart;
        bool nearFailed;

        public readonly List<Vector3> contacts = new List<Vector3>();
        public readonly List<Collider> contactColliders = new List<Collider>();
        static readonly Collider[] overlap = new Collider[16];

        public Vector3 Forward => new Vector3(Mathf.Sin(yaw), 0f, Mathf.Cos(yaw));
        public Vector3 Right => new Vector3(Mathf.Cos(yaw), 0f, -Mathf.Sin(yaw));
        public float Speed => new Vector2(vel.x, vel.z).magnitude;
        public float SpeedFraction => Mathf.Clamp01(Speed / MaxSpeed);
        public Quaternion Rotation => Quaternion.Euler(0f, yaw * Mathf.Rad2Deg, 0f);
        public static float TurnRate(float v) => Mathf.Lerp(TurnLow, TurnHigh, Mathf.Clamp01(v / MaxSpeed));

        public void Place(Vector3 pos, Vector3 dir, float startSpeed)
        {
            position = pos + Vector3.up * (Hover + 0.5f);
            dir.y = 0f;
            if (dir.sqrMagnitude < 1e-6f) dir = Vector3.forward;
            dir.Normalize();
            yaw = Mathf.Atan2(dir.x, dir.z);
            vel = Forward * startSpeed;
            input = default;
            steer = 0f;
            hullRot = Rotation;
            groundNormal = Vector3.up;
            groundValid = onGround = onWater = drifting = nitroActive = nitroWas = jumpEligible = false;
            driftCharge = boost = 0f;
            airTime = 0f;
            visualPitch = pitchV = roll = rollV = heave = heaveV = groundPitch = steerVisual = 0f;
            nearId = null;
        }

        public void PadBoost()
        {
            if (!running) return;
            boost = Mathf.Max(boost, BoostMax * 1.4f);
            var f = Forward;
            float along = Vector3.Dot(new Vector3(vel.x, 0f, vel.z), f);
            float push = Mathf.Clamp(MaxSpeed * topSpeedMul + BoostMax * 1.4f - along, 0f, PadPush);
            vel.x += f.x * push;
            vel.z += f.z * push;
            pitchV += 0.6f;
            boostedThisStep = true;
            boostAmount = boost;
        }

        public void AddNitro(float amount, string reason, bool announce = true)
        {
            float gained = Mathf.Min(Mathf.Max(amount, 0f), 100f - nitro);
            nitro = Mathf.Clamp(nitro + gained, 0f, 100f);
            if (announce && gained > 0.5f) { nitroReason = reason; nitroGain += gained; }
        }

        bool Probe(Vector3 p, float rise, out RaycastHit hit)
        {
            if (Physics.Raycast(p + Vector3.up * rise, Vector3.down, out hit, rise + 14f, IslandWorld.ProbeMask, QueryTriggerInteraction.Ignore))
            {
                // started above a ceiling: search again from the ship
                if (hit.point.y > position.y + 1.5f && !Physics.Raycast(p, Vector3.down, out hit, 14f, IslandWorld.ProbeMask, QueryTriggerInteraction.Ignore))
                    return false;
                return hit.normal.y >= SupportMinY;
            }
            return false;
        }

        public void Step(float dt)
        {
            t += dt;
            lastImpact = 0f;
            lastLanding = 0f;
            boostedThisStep = false;
            nitroReason = null;
            nitroGain = 0f;
            UpdateNitro(dt);
            float steerTarget = controlsBlocked ? 0f : Mathf.Clamp(input.steer, -1f, 1f);
            bool braking = controlsBlocked || input.brake;
            steer = Mathf.MoveTowards(steer, steerTarget, dt * 5f);

            groundValid = Probe(position, 3f, out var hit);
            float groundY = float.NegativeInfinity;
            var supportNormal = Vector3.up;
            onWater = false;
            if (groundValid)
            {
                groundPoint = hit.point;
                groundY = hit.point.y;
                supportNormal = hit.normal;
                onWater = hit.collider != null && hit.collider.gameObject.layer == IslandWorld.LayerWater;
                var sum = supportNormal * 2f;
                foreach (float off in new[] { -4f, 4f })
                {
                    var sample = position + Forward * off;
                    if (!Probe(sample, 6f, out var eh)) continue;
                    // a floor above or below does not belong to the same surface
                    float expected = groundY - Vector3.Dot(supportNormal, sample - position) / supportNormal.y;
                    if (Mathf.Abs(eh.point.y - expected) < 2f) sum += eh.normal;
                }
                supportNormal = sum.normalized;
                groundNormal = Vector3.Lerp(groundNormal, supportNormal, 1f - Mathf.Exp(-18f * dt)).normalized;
                groundPitch = Mathf.Atan2(-Vector3.Dot(supportNormal, Forward), supportNormal.y);
            }
            float err = (groundY + Hover) - position.y;

            if (running)
            {
                float v = Speed;
                var vh = new Vector3(vel.x, 0f, vel.z);
                slip = v < 5f ? 0f : Vector3.SignedAngle(Forward, vh, Vector3.up) * Mathf.Deg2Rad;
                bool hbTurning = braking && Mathf.Abs(steer) > 0.1f;
                float turn = steer * TurnRate(v) * (onGround ? 1f : 0.25f) * Mathf.Lerp(1f, gripMul, 0.5f);
                if (hbTurning) turn *= HbTurn;
                yaw += turn * dt;
                var fwd = Forward;
                float along = Vector3.Dot(vh, fwd);
                var side = vh - fwd * along;
                float top = MaxSpeed * topSpeedMul * (onWater ? WaterSpeed : 1f) + boost + (nitroActive ? NitroExtra * nitroMul : 0f);
                float acc = Accel * accelMul;
                if (braking) along = Mathf.MoveTowards(along, 10f, (hbTurning ? HbDecel : HbDecelStraight) * dt);
                else if (onGround)
                {
                    if (along > top) along = Mathf.MoveTowards(along, top, acc * 0.6f * dt);
                    else along = Mathf.MoveTowards(along, top, acc * (1f - 0.5f * Mathf.Clamp01(along / MaxSpeed)) * dt);
                }
                else if (along > top) along = Mathf.MoveTowards(along, top, acc * 0.25f * dt);
                if (nitroActive) along = Mathf.MoveTowards(along, Mathf.Min(top, SpeedCap), 42f * dt);
                along = Mathf.Min(along, SpeedCap);
                // handbrake: the tail lets go and the velocity keeps its direction (drift)
                float grip = (braking ? HbGrip : Grip * gripMul) * (onGround ? 1f : 0.08f);
                side *= Mathf.Exp(-grip * dt);
                // lateral speed lost becomes forward speed, never more than the entry speed
                float lost = side.magnitude * (1f - Mathf.Exp(-grip * dt));
                float alongAcc = along;
                along += lost * (braking ? 0.85f : 0.5f);
                along = Mathf.Min(along, Mathf.Max(alongAcc, Mathf.Sqrt(Mathf.Max(v * v - side.sqrMagnitude, 0f))));
                vh = fwd * along + side;
                vel.x = vh.x;
                vel.z = vh.z;
                drifting = braking && onGround && v > 30f && Mathf.Abs(slip) > 0.18f;
                if (drifting)
                {
                    AddNitro(8f * dt, "DERRAPAGEM", false);
                    driftCharge = Mathf.Min(driftCharge + dt, 2.5f);
                }
                else if (!braking)
                {
                    if (driftCharge > 0.6f)
                    {
                        boost = BoostMax * Mathf.Clamp(driftCharge / 2f, 0.35f, 1f);
                        var f2 = Forward;
                        vel.x += f2.x * boost * 0.6f;
                        vel.z += f2.z * boost * 0.6f;
                        boostedThisStep = true;
                        boostAmount = boost;
                    }
                    driftCharge = 0f;
                }
                boost = Mathf.MoveTowards(boost, 0f, dt * 9f);
            }
            else if (onGround)
            {
                float k = Mathf.Exp(-1.2f * dt);
                vel.x *= k;
                vel.z *= k;
            }
            // gravity takes energy on a climb and gives it back downhill (never turns a fall into free speed)
            if (running && onGround && groundValid && !onWater)
            {
                var gt = Vector3.ProjectOnPlane(Vector3.down, supportNormal) * Gravity;
                vel.x += gt.x * dt;
                vel.z += gt.z * dt;
                float hs = Speed;
                if (hs > SpeedCap) { vel.x *= SpeedCap / hs; vel.z *= SpeedCap / hs; }
            }
            // damped suspension relative to the slope (implicit integration)
            bool wasAir = !onGround;
            float landingSpeed = Mathf.Max(0f, -Vector3.Dot(vel, supportNormal));
            if (groundValid && err > -0.9f && err < 3f)
            {
                float groundVy = -(supportNormal.x * vel.x + supportNormal.z * vel.z) / supportNormal.y;
                float rel = vel.y - groundVy;
                float vy = groundVy + (rel + err * Spring * dt) / (1f + Damp * dt + Spring * dt * dt);
                // the suspension cannot pull the ship down harder than ~3 g: over a crest or off a ramp lip
                // the ground falls away faster and the ship flies (jumps keep their launch speed)
                float minVy = vel.y - (Gravity + 50f) * dt;
                if (vy < minVy && running)
                {
                    vel.y = minVy;
                    onGround = err > -0.25f;
                }
                else
                {
                    vel.y = vy;
                    onGround = true;
                }
            }
            else
            {
                vel.y -= Gravity * dt;
                onGround = false;
            }
            if (wasAir && onGround && jumpEligible)
            {
                float jd = new Vector2(position.x - jumpOrigin.x, position.z - jumpOrigin.z).magnitude;
                if (airTime > 0.4f && jd > 15f) AddNitro(Mathf.Clamp(airTime * 12f, 8f, 24f), "SALTO");
                jumpEligible = false;
            }
            else if (!wasAir && !onGround)
            {
                jumpOrigin = position;
                jumpEligible = running && Speed > 20f;
            }
            if (onGround && wasAir && airTime > 0.35f && landingSpeed > 8f) lastLanding = landingSpeed;
            if (onGround && wasAir)
            {
                heaveV -= Mathf.Clamp(landingSpeed * 0.12f, 0f, 6f);
                pitchV -= Mathf.Clamp(landingSpeed * 0.02f, 0f, 1.2f);
            }
            // water only holds the suspension: never fall through it on a fast drop
            if (onWater && groundValid && vel.y < 0f && position.y >= groundY)
                vel.y = Mathf.Max(vel.y, (groundY + 0.15f - position.y) / dt);
            airTime = onGround ? 0f : airTime + dt;

            // the physics box follows the surface (a level box would bury its nose on ramps)
            bool approach = groundValid && err > -5f && Vector3.Dot(vel, supportNormal) < 2f;
            bool align = onGround || approach;
            Quaternion target;
            if (align)
            {
                var f = Vector3.ProjectOnPlane(Forward, supportNormal);
                target = Quaternion.LookRotation(f.sqrMagnitude > 1e-4f ? f : Forward, supportNormal);
            }
            else
            {
                float p = Mathf.Clamp(Mathf.Atan2(vel.y, Mathf.Max(Speed, 12f)), -0.22f, 0.22f);
                target = Rotation * Quaternion.Euler(-p * Mathf.Rad2Deg, 0f, 0f);
            }
            hullRot = Quaternion.Slerp(hullRot, target, 1f - Mathf.Exp(-18f * dt));
            // keep the yaw of the hull exact (only pitch/roll lag behind)
            var hf = hullRot * Vector3.forward;
            var hu = hullRot * Vector3.up;
            hullRot = Quaternion.LookRotation(Vector3.ProjectOnPlane(Forward, hu).sqrMagnitude > 1e-4f ? Vector3.ProjectOnPlane(Forward, hu) : hf, hu);

            var before = vel;
            MoveAndSlide(dt);
            // sliding on a slope must not turn the fall into forward speed
            float hb = new Vector2(before.x, before.z).magnitude, ha = new Vector2(vel.x, vel.z).magnitude;
            if (ha > hb + 0.05f && ha > 0f)
            {
                float k = (hb + 0.05f) / ha;
                vel.x *= k;
                vel.z *= k;
            }
            if (running) WallImpacts(before);
            UpdateNearMiss(dt);
            UpdateVisual(dt, braking);
        }

        void UpdateNitro(float dt)
        {
            nitroActive = running && !controlsBlocked && !input.brake && input.nitro && nitro > 0f;
            if (nitroActive)
            {
                nitro = Mathf.Max(0f, nitro - NitroDrain * dt);
                if (!nitroWas) { boostedThisStep = true; boostAmount = NitroExtra; }
            }
            else if (running) nitro = Mathf.Min(100f, nitro + nitroRegen * dt);
            nitroWas = nitroActive;
        }

        void MoveAndSlide(float dt)
        {
            contacts.Clear();
            contactColliders.Clear();
            var motion = vel * dt;
            for (int iter = 0; iter < 4; iter++)
            {
                float dist = motion.magnitude;
                if (dist < 1e-5f) break;
                var dir = motion / dist;
                var center = position + hullRot * HullOffset;
                if (Physics.BoxCast(center, HullHalf, dir, out var hit, hullRot, dist + Skin, IslandWorld.SolidMask, QueryTriggerInteraction.Ignore))
                {
                    float travel = Mathf.Max(0f, hit.distance - Skin);
                    position += dir * travel;
                    var n = hit.normal;
                    contacts.Add(n);
                    contactColliders.Add(hit.collider);
                    motion = dir * (dist - travel);
                    motion -= n * Vector3.Dot(motion, n);
                    float vn = Vector3.Dot(vel, n);
                    if (vn < 0f) vel -= n * vn;
                }
                else
                {
                    position += motion;
                    break;
                }
            }
            Depenetrate();
        }

        /// <summary>Pushes the hull out of anything it overlaps (starts inside a collider, moving geometry, spawns).</summary>
        void Depenetrate()
        {
            var center = position + hullRot * HullOffset;
            int n = Physics.OverlapBoxNonAlloc(center, HullHalf, overlap, hullRot, IslandWorld.SolidMask, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < n; i++)
            {
                var c = overlap[i];
                if (c is TerrainCollider) continue;
                if (c is MeshCollider mc && !mc.convex && mc.sharedMesh == null) continue;
                if (Physics.ComputePenetration(HullCollider, center, hullRot, c, c.transform.position, c.transform.rotation, out var dir, out float d) && d > 0f)
                {
                    position += dir * (d + 0.01f);
                    center += dir * (d + 0.01f);
                    contacts.Add(dir);
                    contactColliders.Add(c);
                    float vn = Vector3.Dot(vel, dir);
                    if (vn < 0f) vel -= dir * vn;
                }
            }
        }

        static BoxCollider hullCollider;
        /// <summary>A disabled box used only as the shape for ComputePenetration.</summary>
        static BoxCollider HullCollider
        {
            get
            {
                if (hullCollider == null)
                {
                    var go = new GameObject("HullShape") { hideFlags = HideFlags.HideAndDontSave };
                    go.SetActive(false);
                    hullCollider = go.AddComponent<BoxCollider>();
                    hullCollider.size = HullHalf * 2f;
                    hullCollider.center = Vector3.zero;
                }
                return hullCollider;
            }
        }

        void WallImpacts(Vector3 before)
        {
            // only the component against the wall bounces: a scrape keeps the momentum
            float worst = 0f;
            var wallVel = new Vector3(before.x, 0f, before.z);
            bool touchedWall = false, touchedSupport = false;
            for (int ci = 0; ci < contacts.Count; ci++)
            {
                var n = contacts[ci];
                if (n.y > SupportMinY) { touchedSupport = true; continue; }
                if (n.y < -SupportMinY) { touchedSupport = true; vel.y = Mathf.Min(vel.y, 0f); continue; }
                var hn = new Vector3(n.x, 0f, n.z).normalized;
                float impact = Mathf.Max(-Vector3.Dot(wallVel, hn), 0f);
                if (impact > worst) { worst = impact; lastImpactNormal = hn; lastImpactCollider = ci < contactColliders.Count ? contactColliders[ci] : null; }
                if (impact > 0f)
                {
                    touchedWall = true;
                    wallVel += hn * (impact + Mathf.Min(impact * 0.18f, 10f));
                }
            }
            if (touchedWall)
            {
                vel.x = wallVel.x;
                vel.z = wallVel.z;
                if (!touchedSupport) vel.y = before.y;
                if (wallVel.magnitude > 4f && worst > 20f)
                    yaw = Mathf.LerpAngle(yaw * Mathf.Rad2Deg, Mathf.Atan2(wallVel.x, wallVel.z) * Mathf.Rad2Deg, 0.35f) * Mathf.Deg2Rad;
            }
            if (worst > 1f) { nearFailed = true; nearCollisionT = t; }
            if (worst > 10f) jumpEligible = false;
            if (worst > 6f)
            {
                driftCharge = 0f;
                lastImpact = worst;
            }
        }

        void FinishNearMiss()
        {
            if (nearId == null) return;
            if (!nearFailed && t - nearCollisionT > 0.5f && Vector3.Distance(position, nearStart) > 6f && (nearId != nearLast || t - nearRewardT > 8f))
            {
                AddNitro(12f, "QUASE BATIDA");
                nearLast = nearId;
                nearRewardT = t;
            }
            nearId = null;
        }

        void UpdateNearMiss(float dt)
        {
            if (!running || controlsBlocked || Speed < 50f) { nearId = null; return; }
            nearClock -= dt;
            if (nearClock > 0f) return;
            nearClock = 0.1f;
            var from = position + Vector3.up * 1.7f;
            Collider found = null;
            foreach (float side in new[] { -1f, 1f })
            {
                if (Physics.Raycast(from, Right * side, out var h, 7f, IslandWorld.SolidMask, QueryTriggerInteraction.Ignore) && Mathf.Abs(h.normal.y) < 0.6f)
                {
                    found = h.collider;
                    break;
                }
            }
            if (found != nearId)
            {
                FinishNearMiss();
                nearId = found;
                nearStart = position;
                nearFailed = false;
            }
        }

        void UpdateVisual(float dt, bool braking)
        {
            float lat = Vector3.Dot(vel, Right);
            steerVisual = Mathf.Lerp(steerVisual, Mathf.Clamp(steer * 0.7f - lat / 40f, -1f, 1f), 1f - Mathf.Exp(-dt * 6f));
            float hs = Speed;
            float tp = onGround ? groundPitch : Mathf.Atan2(vel.y, Mathf.Max(hs, 12f)) * 0.9f;
            if (braking && running) tp -= 0.045f;
            tp = Mathf.Clamp(tp, -0.75f, 0.75f);
            pitchV = (pitchV + (tp - visualPitch) * 90f * dt) / (1f + 15f * dt + 90f * dt * dt);
            visualPitch += pitchV * dt;
            // lean into turns and follow the side slope
            var lup = onGround ? Quaternion.Inverse(Rotation) * groundNormal : Vector3.up;
            float tr = steerVisual * 0.4f + Mathf.Atan2(lup.x, lup.y);
            rollV = (rollV + (tr - roll) * 55f * dt) / (1f + 12f * dt + 55f * dt * dt);
            roll += rollV * dt;
            heaveV = (heaveV - heave * 90f * dt) / (1f + 14f * dt + 90f * dt * dt);
            heave = Mathf.Clamp(heave + heaveV * dt, -1.2f, 0.8f);
        }

        /// <summary>Body pose for the renderer: pitch (nose up +), roll (right wing down +), heave and bob.</summary>
        public Quaternion VisualRotation => Rotation * Quaternion.Euler(-visualPitch * Mathf.Rad2Deg, 0f, -roll * Mathf.Rad2Deg);

        public float Bob => onGround ? Mathf.Sin(t * 9f) * 0.05f + Mathf.Sin(t * 23f) * 0.02f * SpeedFraction : Mathf.Sin(t * 4f) * 0.08f;
    }
}
