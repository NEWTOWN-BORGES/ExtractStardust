using System;
using UnityEngine;

namespace RedDust.Vehicle
{
    /// <summary>Comandos de pilotagem de um frame de física (jogador ou IA usam exatamente o mesmo canal).</summary>
    public struct CraftInput
    {
        public float steer;      // -1..1
        public float throttle;   // 0..1 (aceleração automática = 1)
        public bool brake;       // travão de mão: com direção = derrapagem, a direito = travagem
        public bool boost;
        public float airPitch;   // -1..1 (controlo aéreo limitado)

        public static CraftInput Auto => new CraftInput { throttle = 1f };
    }

    /// <summary>
    /// Parâmetros físicos de uma nave. Valores por omissão = STRIX stock (TARGETS DE TUNING do laboratório M1).
    /// Na M4 estes valores passam a ser calculados pelo StatResolver a partir do chassis + módulos; aqui não há
    /// dependência de malhas visuais: a física vem só destes dados.
    /// </summary>
    [Serializable]
    public class CraftTuning
    {
        [Header("Massa e envelope físico")]
        public float mass = 1450f;
        public Vector3 hullSize = new Vector3(3.4f, 1.0f, 7.0f);
        public Vector3 centerOfMass = new Vector3(0f, -0.15f, 0f);

        [Header("Repulsores")]
        [Tooltip("Altura do plano central da nave acima da superfície (m)")] public float hoverHeight = 1.5f;
        [Tooltip("Alcance de captura acima da altura de hover (m)")] public float captureRange = 2.6f;
        [Tooltip("Alcance dos sensores acima da altura de hover (m)")] public float probeReach = 6f;
        public float springHz = 3.0f;
        public float dampingRatio = 0.72f;
        public float maxHoverAccel = 280f;
        [Tooltip("Gravidade do jogo (m/s²)")] public float gravity = 22f;
        [Tooltip("Aderência máxima à superfície a alta velocidade (m/s²)")] public float adhesion = 9f;
        public float adhesionMinSpeed = 45f;
        public float adhesionFullSpeed = 90f;
        public float probeHalfWidth = 1.45f;
        public float probeHalfLength = 2.9f;
        [Tooltip("Antecipação da normal à frente (s de viagem)")] public float lookAheadTime = 0.14f;
        [Tooltip("Constante de tempo da suavização da normal (s)")] public float normalSmoothing = 0.035f;

        [Header("Propulsão")]
        [Tooltip("Velocidade máxima sem boost (m/s). 118 m/s = 425 km/h")] public float topSpeed = 118f;
        [Tooltip("Aceleração a baixa velocidade (m/s²)")] public float accel = 36f;
        public float boostTopMul = 1.14f;
        public float boostAccel = 26f;
        public float brakeDecel = 38f;
        [Tooltip("Fração da propulsão disponível no ar")] public float airThrust = 0.3f;
        [Tooltip("Arrasto aerodinâmico (a = k·v²)")] public float aeroDrag = 0.00012f;
        [Tooltip("Travagem de excesso de velocidade acima da máxima (1/s)")] public float overspeedBleed = 0.6f;

        [Header("Direção e aderência lateral")]
        public float turnRateLow = 2.1f;
        public float turnRateHigh = 0.62f;
        public float steerResponse = 10f;
        [Tooltip("Rapidez máxima a alinhar a velocidade com a proa (rad/s)")] public float gripRedirect = 5.5f;
        [Tooltip("Aceleração lateral máxima (m/s²)")] public float gripLateralMax = 85f;
        [Tooltip("Atrito lateral residual (1/s)")] public float gripFriction = 1.2f;
        [Tooltip("Fração da aderência lateral parado (repulsores); o resto cresce com v² (superfícies aerodinâmicas)")] public float gripBase = 0.10f;
        [Tooltip("Velocidade (m/s) a que a aderência lateral fica completa")] public float gripSpeedRef = 125f;
        public float driftRedirect = 1.1f;
        public float driftLateralMax = 30f;
        public float driftTurnMul = 1.75f;
        public float driftDecel = 6f;

        [Header("Atitude")]
        [Tooltip("Correção máxima de atitude no solo (graus/s)")] public float alignRate = 160f;
        [Tooltip("Constante de tempo do alinhamento (s)")] public float alignTime = 0.07f;
        public float airAlignRate = 45f;
        public float airTurnMul = 0.35f;
        public float airPitchRate = 0.9f;
        [Tooltip("Recuperação de rotação provocada por colisões (1/s)")] public float stabilityRecover = 9f;

        [Header("Eventos de dano")]
        public float landingSoft = 9f;
        public float landingHard = 17f;
        public float impactMin = 12f;

        public float TurnRate(float speed) => Mathf.Lerp(turnRateLow, turnRateHigh, Mathf.Clamp01(speed / topSpeed));
        public float SpringK => Mathf.Pow(2f * Mathf.PI * springHz, 2f);
        public float SpringC => 2f * dampingRatio * 2f * Mathf.PI * springHz;
        public float Adhesion(float speed) => adhesion * MathX.Smoothstep(adhesionMinSpeed, adhesionFullSpeed, speed);
        /// <summary>0..1: aderência lateral disponível (parado só a dos repulsores; a alta velocidade a aerodinâmica).</summary>
        public float GripFactor(float speed) => Mathf.Clamp01(gripBase + (speed / gripSpeedRef) * (speed / gripSpeedRef));

        public CraftTuning Clone() => (CraftTuning)MemberwiseClone();
    }
}
