using RedDust.Vehicle;
using UnityEngine;

namespace RedDust.Presentation
{
    /// <summary>
    /// Câmera de perseguição em terceira pessoa.
    ///  - FOV responde à velocidade (e ao boost); recua com a aceleração; lag lateral nas curvas.
    ///  - Compensação de bank: a câmera fica "acima" segundo uma mistura do cima do mundo e da nave, e o horizonte
    ///    só roda uma fração (rollFollow) do roll da nave — mantém leitura sem perder o drama da parede.
    ///  - Salto: segue a trajetória; aterragem: pequeno impulso vertical que recupera.
    ///  - Anticolisão: sphere cast da nave até à posição desejada (paredes, teto de caverna).
    ///  - Acessibilidade: escala do tremor e FOV extra configuráveis.
    /// Tick(dt) é público para os testes do editor.
    /// </summary>
    public class ChaseCamera : MonoBehaviour
    {
        public CraftController target;
        [Header("Enquadramento")]
        public float distance = 6.4f;
        [Tooltip("Negativo: aproxima-se à velocidade máxima (mais sensação de velocidade)")] public float distanceAtSpeed = -1.0f;
        public float height = 1.6f;
        public float heightAtSpeed = -0.35f;
        public float lookAhead = 16f;
        public float lookHeight = 0.8f;
        [Header("Banking")]
        [Range(0f, 1f)] public float upFollow = 0.7f;
        [Range(0f, 1f)] public float rollFollow = 0.4f;
        [Header("Suavização")]
        public float offsetStiffness = 7f;
        public float upSmoothing = 6f;
        public float headingSmoothing = 8f;
        [Header("FOV")]
        public float fovMin = 62f;
        public float fovMax = 100f;
        public float fovBoost = 9f;
        [Tooltip("Velocidades (km/h) entre as quais entra a sensação de vertigem")] public Vector2 vertigoKmh = new Vector2(230f, 450f);
        [Header("Acessibilidade")]
        [Range(0f, 2f)] public float shakeScale = 1f;
        [Range(-10f, 10f)] public float fovOffset = 0f;
        public float collisionRadius = 0.35f;
        [Header("Olhar")]
        [Tooltip("-1..1 (analógico direito): órbita lateral")] public float lookYawInput;
        public bool lookBack;
        public float lookYawMax = 120f;
        float lookYaw;

        public Camera Cam { get; private set; }
        public float CameraRollDeg { get; private set; }
        public float CraftRollDeg { get; private set; }
        public bool Blocked { get; private set; }
        /// <summary>0..1: quanto a velocidade está na zona "vertiginosa" (efeitos, partículas e som usam isto).</summary>
        public float Vertigo { get; private set; }
        float boostPunch, driftSwing;
        bool wasBoosting;

        Vector3 offset;           // posição da câmera relativa à nave (suavizada)
        Vector3 smoothUp = Vector3.up;
        Vector3 smoothHeading = Vector3.forward;
        float fov;
        float kick, kickVel;
        float shakeTime, impactShake;
        float lastSpeed;
        bool initialized;

        void Awake()
        {
            Cam = GetComponent<Camera>();
        }

        public void Attach(CraftController craft)
        {
            if (target != null) { target.Landed -= OnLanded; target.Impacted -= OnImpact; }
            target = craft;
            if (craft != null) { craft.Landed += OnLanded; craft.Impacted += OnImpact; }
            initialized = false;
        }

        void OnLanded(float vn) => kickVel -= Mathf.Min(vn * 0.06f, 1.4f);
        void OnImpact(float s, Vector3 n, Collider c) => impactShake = Mathf.Min(1f, impactShake + s / 40f);

        void LateUpdate()
        {
            if (target != null) Tick(Time.deltaTime);
        }

        public void Tick(float dt)
        {
            if (target == null) return;
            if (Cam == null) Cam = GetComponent<Camera>();
            var t = target;
            Vector3 p = t.Body.interpolation != RigidbodyInterpolation.None ? t.transform.position : t.Position;
            Quaternion r = t.Body.interpolation != RigidbodyInterpolation.None ? t.transform.rotation : t.Rotation;
            Vector3 craftUp = r * Vector3.up;
            Vector3 craftFwd = r * Vector3.forward;
            float speed = t.Speed;
            float top = t.tuning.topSpeed;

            // direção de referência: proa, com um pouco da velocidade (deixa ver a derrapagem)
            Vector3 vel = t.Velocity;
            Vector3 heading = craftFwd;
            if (speed > 10f) heading = Vector3.Slerp(craftFwd, vel / speed, 0.3f);
            Vector3 upPos = Vector3.Slerp(Vector3.up, craftUp, upFollow).normalized;
            Vector3 upRoll = Vector3.Slerp(Vector3.up, craftUp, rollFollow).normalized;

            if (!initialized)
            {
                smoothUp = upPos; smoothHeading = heading; fov = fovMin; initialized = true;
                offset = -heading * distance + upPos * height;
            }
            smoothUp = Vector3.Slerp(smoothUp, upPos, MathX.Damp(upSmoothing, dt)).normalized;
            smoothHeading = Vector3.Slerp(smoothHeading, heading, MathX.Damp(headingSmoothing, dt)).normalized;
            // olhar à volta (analógico direito) / para trás (R3): roda o enquadramento à volta do "cima"
            float yawTarget = lookBack ? 180f : lookYawInput * lookYawMax;
            lookYaw = Mathf.Lerp(lookYaw, yawTarget, MathX.Damp(lookBack ? 18f : 7f, dt));
            // derrapagem: a câmera abre para fora e mostra a nave de lado
            driftSwing = Mathf.Lerp(driftSwing, t.Drifting ? Mathf.Clamp(-t.LateralSpeed * 0.7f, -20f, 20f) : 0f, MathX.Damp(t.Drifting ? 3f : 2f, dt));
            Vector3 viewHeading = Quaternion.AngleAxis(lookYaw + driftSwing, smoothUp) * smoothHeading;
            float kmh = speed * 3.6f;
            Vertigo = MathX.Smoothstep(vertigoKmh.x, vertigoKmh.y, kmh);
            if (t.Boosting && !wasBoosting) boostPunch = 1f;       // ao acender o nitro: "soco" de FOV
            wasBoosting = t.Boosting;
            boostPunch = Mathf.MoveTowards(boostPunch, 0f, dt * 1.8f);

            // recuo com a aceleração
            float accel = dt > 0f ? (speed - lastSpeed) / dt : 0f;
            lastSpeed = speed;
            float pull = Mathf.Clamp(accel * 0.03f, -0.6f, 1.2f);
            float dist = distance + distanceAtSpeed * Mathf.Clamp01(speed / top) + pull;
            Vector3 desiredOffset = -viewHeading * dist + smoothUp * (height + heightAtSpeed * Mathf.Clamp01(speed / top));
            offset = Vector3.Lerp(offset, desiredOffset, MathX.Damp(offsetStiffness, dt));

            // impulso de aterragem (mola)
            kickVel += (-kick * 60f - kickVel * 12f) * dt;
            kick += kickVel * dt;

            Vector3 pivot = p + craftUp * 1.2f;
            Vector3 desired = p + offset + smoothUp * kick;
            Vector3 dir = desired - pivot;
            float len = dir.magnitude;
            Blocked = false;
            Vector3 camPos = desired;
            if (len > 0.01f && Physics.SphereCast(pivot, collisionRadius, dir / len, out var hit, len, Layers.CameraMask, QueryTriggerInteraction.Ignore))
            {
                camPos = pivot + dir / len * Mathf.Max(0.3f, hit.distance - 0.15f);
                Blocked = true;
            }

            Vector3 look = p + viewHeading * lookAhead + smoothUp * lookHeight;
            Quaternion rot = Quaternion.LookRotation(look - camPos, upRoll);

            // tremor de alta frequência: cresce com a vertigem e com o chão (areia, cascalho, rocha); nitro, derrapagem
            // e impactos somam. Escalado pela opção de acessibilidade.
            shakeTime += dt * (8f + 34f * Mathf.Clamp01(speed / top));
            impactShake = Mathf.MoveTowards(impactShake, 0f, dt * 2.5f);
            float ground = t.Grounded ? t.SurfaceShake : 0f;
            float amp = shakeScale * (Vertigo * (0.3f + 1.7f * ground) + (t.Boosting ? 0.45f * Mathf.Max(Vertigo, 0.3f) : 0f)
                                      + (t.Drifting ? 0.35f : 0f) + 1.6f * impactShake);
            if (amp > 0f)
            {
                float n1 = Mathf.PerlinNoise(shakeTime, 0.3f) - 0.5f + 0.5f * (Mathf.PerlinNoise(shakeTime * 2.7f, 5.1f) - 0.5f);
                float n2 = Mathf.PerlinNoise(0.7f, shakeTime) - 0.5f + 0.5f * (Mathf.PerlinNoise(9.3f, shakeTime * 2.7f) - 0.5f);
                rot *= Quaternion.Euler(n1 * amp, n2 * amp, 0f);
                camPos += (rot * Vector3.up) * (n2 * 0.06f * amp) + (rot * Vector3.right) * (n1 * 0.05f * amp);
            }
            transform.SetPositionAndRotation(camPos, rot);

            float targetFov = Mathf.Lerp(fovMin, fovMax, 0.3f * Mathf.Clamp01(speed / top) + 0.7f * Vertigo) + (t.Boosting ? fovBoost : 0f) + fovOffset;
            fov = Mathf.Lerp(fov, targetFov, MathX.Damp(3f, dt)) ;
            float fovNow = fov + 7f * boostPunch * boostPunch;
            if (Cam != null) Cam.fieldOfView = fovNow;

            // métricas para os testes de aceitação
            CraftRollDeg = Vector3.Angle(craftUp, Vector3.up);
            Vector3 camRight = rot * Vector3.right;
            CameraRollDeg = Mathf.Abs(Mathf.Asin(Mathf.Clamp(camRight.y, -1f, 1f)) * Mathf.Rad2Deg);
        }
    }
}
