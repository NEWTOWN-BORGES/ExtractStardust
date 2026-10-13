using System;
using RedDust.Track;
using UnityEngine;

namespace RedDust.Vehicle
{
    /// <summary>
    /// Nave antigravidade (Rigidbody dinâmico, passo fixo). Forças por passo:
    ///   gravidade do jogo; mola-amortecedor dos repulsores ao longo da normal da superfície, limitada em tração
    ///   pela aderência (que cresce com a velocidade — é o que permite banks extremos e wall ride curto);
    ///   propulsão ao longo da proa projetada na superfície; travagem; arrasto.
    /// Direção arcade: a velocidade é redirecionada para a proa sem perder módulo (limitada por aceleração lateral),
    /// e a derrapagem (travão + direção) reduz essa aderência e aumenta a rotação.
    /// Atitude: alinha progressivamente o "cima" à normal filtrada (taxa máxima em graus/s, sem snap); no ar
    /// alinha para a superfície prevista de aterragem. Rotações por colisão recuperam com a estabilidade.
    /// Step(dt) é chamado pelo FixedUpdate em jogo e diretamente pelos testes do editor.
    /// </summary>
    [RequireComponent(typeof(Rigidbody))]
    [DefaultExecutionOrder(-50)]
    public class CraftController : MonoBehaviour
    {
        public CraftTuning tuning = new CraftTuning();
        public bool autoStep = true;
        [NonSerialized] public CraftInput input = CraftInput.Auto;

        public Rigidbody Body { get; private set; }
        public HoverSensor Sensor { get; private set; }

        // ---- telemetria (leitura)
        public bool Grounded { get; private set; }
        public float Speed { get; private set; }
        public float ForwardSpeed { get; private set; }
        public float LateralSpeed { get; private set; }
        public float AirTime { get; private set; }
        public float LastLandingSpeed { get; private set; }
        public float LastImpactSpeed { get; private set; }
        public Collider LastImpactCollider { get; private set; }
        public bool Drifting { get; private set; }
        public bool Boosting { get; private set; }
        /// <summary>Depósito de nitro (0..1): gasta-se no boost; regenera sozinho, mais depressa a derrapar e no ar.</summary>
        public float Nitro { get; private set; } = 1f;
        public bool NitroLocked => nitroLocked;
        bool nitroLocked;
        public Vector3 SurfaceNormal => Grounded ? Sensor.normal : Vector3.up;
        public float SurfaceAngle => Grounded ? Vector3.Angle(Sensor.normal, Vector3.up) : 0f;
        public float HoverMeasured => Sensor.hits > 0 ? Sensor.height : float.PositiveInfinity;
        public float UpRateDeg { get; private set; }   // velocidade de mudança do "cima" (graus/s) num passo
        public float UpRateSmoothed { get; private set; }   // a mesma, média móvel de ~0,1 s (métrica de "snap")
        public Surface Surface => Sensor.dominant;
        public float SurfaceShake => Grounded ? Sensor.traits.shake : 0f;
        public Vector3 Position => Body.position;
        public Quaternion Rotation => Body.rotation;
        public Vector3 Velocity => Body.linearVelocity;
        public Vector3 Forward => Body.rotation * Vector3.forward;
        public Vector3 Up => Body.rotation * Vector3.up;
        public Vector3 Right => Body.rotation * Vector3.right;

        public event Action<float> Landed;                       // velocidade normal de aterragem (m/s)
        public event Action<float, Vector3, Collider> Impacted;  // velocidade de impacto, normal, collider

        Vector3 lastCommandedSpin;
        Vector3 lastUp;
        float yawRate;
        bool wasGrounded;

        void Awake() => Init();

        public void Init()
        {
            if (Body != null) return;
            Body = GetComponent<Rigidbody>();
            Body.mass = tuning.mass;
            Body.useGravity = false;
            Body.linearDamping = 0f;
            Body.angularDamping = 0f;
            Body.maxAngularVelocity = 30f;
            Body.maxDepenetrationVelocity = 15f;
            Body.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
            Body.centerOfMass = tuning.centerOfMass;
            Sensor = new HoverSensor(tuning);
            Sensor.Reset(transform.up);
            lastUp = transform.up;
        }

        /// <summary>Coloca a nave num ponto/orientação com velocidade inicial (respawn, grelha, testes).</summary>
        public void Place(Vector3 position, Quaternion rotation, float speed)
        {
            Init();
            Body.position = position;
            Body.rotation = rotation;
            transform.SetPositionAndRotation(position, rotation);
            Body.linearVelocity = rotation * Vector3.forward * speed;
            Body.angularVelocity = Vector3.zero;
            lastCommandedSpin = Vector3.zero;
            yawRate = 0f;
            AirTime = 0f;
            LastLandingSpeed = 0f;
            LastImpactSpeed = 0f;
            UpRateSmoothed = 0f;
            Nitro = 1f; nitroLocked = false;
            Sensor.Reset(rotation * Vector3.up);
            lastUp = rotation * Vector3.up;
            wasGrounded = true;
        }

        /// <summary>Energia de boost extra (consumível Surge Cell): soma ao depósito e desbloqueia-o.</summary>
        public void AddNitro(float amount)
        {
            Nitro = Mathf.Clamp01(Nitro + amount);
            if (Nitro >= tuning.nitroRestart) nitroLocked = false;
        }

        void FixedUpdate()
        {
            if (autoStep) Step(Time.fixedDeltaTime);
        }

        public void Step(float dt)
        {
            var t = tuning;
            Vector3 pos = Body.position;
            Quaternion rot = Body.rotation;
            Vector3 v = Body.linearVelocity;
            Vector3 up = rot * Vector3.up;
            Vector3 fwd = rot * Vector3.forward;
            float speed = v.magnitude;

            Sensor.Sample(transform, pos, rot, v, t, dt);
            bool grounded = Sensor.hits >= 2 && Sensor.height < t.hoverHeight + t.captureRange;
            Vector3 n = grounded ? Sensor.normal : Vector3.up;

            // ---------------- forças lineares (como variação de velocidade)
            Vector3 acc = Vector3.down * t.gravity;
            bool drift = false, braking = false, wasDrifting = Drifting;
            float steer = Mathf.Clamp(input.steer, -1f, 1f);
            // nitro: gasta o depósito; vazio = bloqueado até recuperar nitroRestart
            Boosting = input.boost && Nitro > 0f && !nitroLocked;
            if (Boosting)
            {
                Nitro = Mathf.Max(0f, Nitro - dt / Mathf.Max(0.1f, t.nitroSeconds));
                if (Nitro <= 0f) nitroLocked = true;
            }
            else
            {
                Nitro = Mathf.Min(1f, Nitro + dt * (t.nitroRegen + (wasDrifting ? t.nitroDriftRegen : 0f) + (Grounded ? 0f : t.nitroAirRegen)));
                if (Nitro >= t.nitroRestart) nitroLocked = false;
            }

            if (grounded)
            {
                // repulsor: mola-amortecedor ao longo da normal; tração limitada pela aderência
                float vn = Vector3.Dot(v, n);
                float a = t.SpringK * (t.hoverHeight - Sensor.height) - t.SpringC * vn;
                a = Mathf.Clamp(a, -t.Adhesion(speed), t.maxHoverAccel);
                acc += n * a;

                Vector3 f = Vector3.ProjectOnPlane(fwd, n);
                f = f.sqrMagnitude > 1e-6f ? f.normalized : fwd;
                float vf = Vector3.Dot(v, f);
                ForwardSpeed = vf;

                // travão de mão: com direção = derrapagem; a direito = travagem
                if (input.brake || input.drift)
                {
                    // uma derrapagem iniciada mantém-se com o botão premido (dá para contra-brecar sem travar)
                    if ((wasDrifting && speed > 18f) || (Mathf.Abs(steer) > 0.25f && speed > 25f)) drift = true;
                    else braking = true;
                }

                var st = Sensor.traits;
                float top = t.topSpeed * st.topSpeed * (Boosting ? t.boostTopMul : 1f);
                float thrust;
                if (vf < top)
                {
                    float k = Mathf.Max(0f, vf) / top;
                    thrust = t.accel * (1f - k * k) + (Boosting ? t.boostAccel * (1f - k) : 0f);
                }
                else thrust = -(vf - top) * t.overspeedBleed;
                acc += f * (thrust * Mathf.Clamp01(input.throttle));
                if (braking && vf > 0f) acc -= f * Mathf.Min(t.brakeDecel, vf / dt);
                else if (input.throttle < 0.05f && vf > 0f) acc -= f * Mathf.Min(t.coastDecel, vf / dt);   // travagem do motor
                if (drift) acc -= v.normalized * t.driftDecel;
                // arrasto da superfície (areia funda, cascalho, rocha rugosa)
                if (st.drag > 0f && speed > 1f)
                {
                    float sf = speed / t.topSpeed;
                    acc -= v / speed * Mathf.Min(st.drag * sf * sf + st.drag * 0.25f, speed / dt);
                }
            }
            else
            {
                ForwardSpeed = Vector3.Dot(v, fwd);
                Vector3 fh = fwd; fh.y = Mathf.Min(fh.y, 0.2f);
                float k = Mathf.Clamp01(ForwardSpeed / t.topSpeed);
                acc += fh.normalized * (t.accel * t.airThrust * (1f - k * k) * Mathf.Clamp01(input.throttle));
            }
            acc -= v * (t.aeroDrag * speed);
            v += acc * dt;

            // ---------------- aderência lateral arcade: redirecionar a velocidade para a proa sem perder módulo
            if (grounded)
            {
                Vector3 vt = Vector3.ProjectOnPlane(v, n);
                float sp = vt.magnitude;
                Vector3 f = Vector3.ProjectOnPlane(fwd, n).normalized;
                slipAngle = 0f;
                if (sp > 1f && Vector3.Dot(vt, f) > 0f)
                {
                    float ang = Vector3.SignedAngle(vt, f, n) * Mathf.Deg2Rad;
                    slipAngle = ang;
                    // a aderência volta aos poucos depois de largar a derrapagem (sem estalo)
                    gripBlend = drift ? 0f : Mathf.MoveTowards(gripBlend, 1f, dt / Mathf.Max(0.05f, t.driftRecoverTime));
                    float latMax = Mathf.Lerp(t.driftLateralMax, t.gripLateralMax, gripBlend);
                    float redirect = Mathf.Lerp(t.driftRedirect, t.gripRedirect, gripBlend);
                    // ângulo de deriva acima do máximo: a velocidade alcança a proa mais depressa (desliza, não roda)
                    float over = Mathf.Abs(ang) * Mathf.Rad2Deg - t.driftMaxSlip;
                    if (over > 0f) { redirect *= 1f + over / 8f; latMax *= 1f + over / 15f; }
                    float rateCap = latMax * t.GripFactor(sp) * Sensor.traits.grip / sp;
                    float rate = Mathf.Min(redirect, rateCap);
                    float d = Mathf.Clamp(ang, -rate * dt, rate * dt);
                    Vector3 vtNew = Quaternion.AngleAxis(d * Mathf.Rad2Deg, n) * vt;
                    v += vtNew - vt;
                    // atrito lateral residual (perde alguma velocidade quando desliza)
                    Vector3 r = Vector3.Cross(n, f);
                    float vr = Vector3.Dot(v, r);
                    v -= r * vr * Mathf.Clamp01(Mathf.Lerp(0.18f, 1f, gripBlend) * t.gripFriction * t.GripFactor(sp) * dt);
                }
                LateralSpeed = Vector3.Dot(v, Vector3.Cross(n, f));
            }
            Drifting = drift;

            // ---------------- atitude: alinhar o "cima" e rodar (yaw) pela direção
            Vector3 desiredUp = grounded ? n : AirTargetUp(pos, v, up);
            float rateLimit = (grounded ? t.alignRate : t.airAlignRate) * Mathf.Deg2Rad;
            Vector3 axis = Vector3.Cross(up, desiredUp);
            float sin = axis.magnitude;
            Vector3 spinAlign = Vector3.zero;
            if (sin > 1e-5f)
            {
                float ang = Mathf.Atan2(sin, Vector3.Dot(up, desiredUp));
                spinAlign = axis / sin * Mathf.Min(ang / Mathf.Max(dt, t.alignTime), rateLimit);
            }
            float turn = t.TurnRate(speed) * (drift ? t.driftTurnMul : 1f) * (grounded ? 1f : t.airTurnMul);
            yawRate = Mathf.Lerp(yawRate, steer * turn, MathX.Damp(t.steerResponse, dt));
            if (drift && !wasDrifting) yawRate += Mathf.Sign(steer) * t.driftKick;     // a traseira solta-se
            // sem piões: se a deriva já passou do máximo e a rotação a aumenta, a rotação é travada
            if (grounded && Mathf.Abs(slipAngle) * Mathf.Rad2Deg > t.driftMaxSlip && yawRate * slipAngle > 0f)
                yawRate = Mathf.Lerp(yawRate, 0f, MathX.Damp(8f, dt));
            Vector3 spin = spinAlign + up * yawRate;
            if (!grounded) spin += (rot * Vector3.right) * (input.airPitch * t.airPitchRate);

            // perturbação por colisões desde o último passo: decai com a estabilidade
            Vector3 external = Body.angularVelocity - lastCommandedSpin;
            spin += external * Mathf.Exp(-t.stabilityRecover * dt);
            lastCommandedSpin = spin;

            Body.linearVelocity = v;
            Body.angularVelocity = spin;

            // ---------------- eventos e telemetria
            if (grounded && !wasGrounded && AirTime > 0.08f)
            {
                float vn = -Vector3.Dot(v, n);
                LastLandingSpeed = vn;
                if (vn > t.landingSoft) Landed?.Invoke(vn);
            }
            AirTime = grounded ? 0f : AirTime + dt;
            wasGrounded = grounded;
            Grounded = grounded;
            Speed = v.magnitude;
            UpRateDeg = Vector3.Angle(lastUp, up) / dt;
            UpRateSmoothed = Mathf.Lerp(UpRateSmoothed, UpRateDeg, MathX.Damp(10f, dt));
            lastUp = up;
            preVel = Body.linearVelocity;
        }

        /// <summary>No ar: inclinar para a superfície onde a trajetória balística vai aterrar.</summary>
        Vector3 AirTargetUp(Vector3 pos, Vector3 v, Vector3 up)
        {
            Vector3 g = Vector3.down * tuning.gravity;
            Vector3 prev = pos;
            float tPrev = 0f;
            for (int k = 1; k <= 6; k++)
            {
                float tt = k * 0.25f;
                Vector3 p = pos + v * tt + 0.5f * tt * tt * g;
                Vector3 d = p - prev;
                if (Physics.Raycast(prev, d.normalized, out var h, d.magnitude + tuning.hoverHeight, Layers.GroundMask, QueryTriggerInteraction.Ignore))
                {
                    float tHit = tPrev + (tt - tPrev) * Mathf.Clamp01(h.distance / Mathf.Max(0.01f, d.magnitude));
                    float w = 1f - Mathf.Clamp01(tHit / 1.4f);
                    return Vector3.Slerp(Vector3.up, h.normal, 0.35f + 0.65f * w).normalized;
                }
                prev = p; tPrev = tt;
            }
            return Vector3.up;
        }

        float gripBlend = 1f, slipAngle;   // 0 = aderência de derrapagem, 1 = normal; ângulo velocidade→proa (rad)
        Vector3 preVel;   // velocidade antes da simulação física (para não perder velocidade em degraus/emendas do chão)

        void OnCollisionEnter(Collision c) { if (!GroundGraze(c)) ReportImpact(c); }
        void OnCollisionStay(Collision c) => GroundGraze(c);

        /// <summary>
        /// Toques do casco no chão (barriga, degraus, emendas e falhas da malha): não são batidas. Mantém a velocidade ao
        /// longo da superfície, dá um pequeno impulso para cima e não conta impacto. Paredes e rochas de frente contam.
        /// </summary>
        bool GroundGraze(Collision c)
        {
            if (c.contactCount == 0 || ((1 << c.gameObject.layer) & Layers.GroundMask) == 0) return false;
            var cp = c.GetContact(0);
            Vector3 n = cp.normal;
            float upDot = Vector3.Dot(n, Up);
            bool low = Vector3.Dot(cp.point - Position, Up) < -tuning.hullSize.y * 0.2f;
            bool facing = Vector3.Dot(n, Forward) < -0.75f && upDot < 0.35f;   // parede/rocha mesmo à frente
            if (facing || (upDot < 0.35f && !low)) return false;
            Vector3 v = Vector3.ProjectOnPlane(preVel, n);
            if (Vector3.Dot(preVel, n) < 0f) Body.linearVelocity = v + Up * 0.8f;
            return true;
        }

        void ReportImpact(Collision c)
        {
            if (c.contactCount == 0) return;
            Vector3 n = c.GetContact(0).normal;
            float s = Mathf.Abs(Vector3.Dot(c.relativeVelocity, n));
            if (s < tuning.impactMin) return;
            LastImpactSpeed = s;
            LastImpactCollider = c.collider;
            Impacted?.Invoke(s, n, c.collider);
        }
    }
}
