using RedDust.Vehicle;
using UnityEngine;

namespace RedDust.Presentation
{
    /// <summary>
    /// Inclinação visual da mota (só o modelo; a física continua alinhada com o chão):
    ///  - curva: deita-se para dentro da curva, mais quanto maior a velocidade e a força lateral;
    ///  - derrapagem: deita-se ainda mais e a traseira sai de lado (o nariz aponta para dentro da curva);
    ///  - nariz sobe ao acelerar/nitro e desce ao travar; no ar volta devagar ao direito.
    /// </summary>
    public class CraftLean : MonoBehaviour
    {
        public CraftController craft;
        public float maxLean = 36f;
        public float driftLean = 58f;
        public float driftYaw = 26f;
        public float response = 9f;
        float roll, yaw, pitch;

        public float LeanDeg => roll;

        void LateUpdate()
        {
            if (craft == null) return;
            float dt = Time.deltaTime;
            if (dt <= 0f) return;
            var inp = craft.input;
            float v = craft.Speed;
            float speedK = Mathf.InverseLerp(4f, 55f, v);
            float steer = Mathf.Clamp(inp.steer, -1f, 1f);
            // força lateral real (velocidade de rotação × velocidade) reforça a inclinação
            float lateral = Mathf.Clamp(craft.LateralSpeed / 25f, -1f, 1f);
            float rollT = -(steer * 0.8f - lateral * 0.35f) * maxLean * speedK;
            float yawT = 0f;
            if (craft.Drifting)
            {
                float dir = Mathf.Abs(steer) > 0.05f ? Mathf.Sign(steer) : -Mathf.Sign(craft.LateralSpeed);
                rollT = -dir * driftLean * speedK;
                yawT = dir * driftYaw * speedK;
            }
            if (!craft.Grounded) rollT *= 0.5f;
            float pitchT = (craft.Boosting ? -5f : 0f) + (inp.throttle > 0.5f ? -2f : 0f) + (inp.brake ? 5f : 0f);
            if (!craft.Grounded) pitchT += inp.airPitch * 10f;
            float k = MathX.Damp(response, dt);
            roll = Mathf.Lerp(roll, rollT, k);
            yaw = Mathf.Lerp(yaw, yawT, MathX.Damp(craft.Drifting ? 6f : 4f, dt));
            pitch = Mathf.Lerp(pitch, pitchT, MathX.Damp(5f, dt));
            transform.localRotation = Quaternion.Euler(pitch, yaw, roll);
        }
    }
}
