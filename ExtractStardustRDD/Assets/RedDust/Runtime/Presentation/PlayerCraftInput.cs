using RedDust.Vehicle;
using UnityEngine;
using UnityEngine.InputSystem;

namespace RedDust.Presentation
{
    /// <summary>
    /// Pilotagem do jogador. A nave só acelera com o acelerador (R2 analógico / W); sem acelerar, o motor trava.
    /// Teclado e comando funcionam ao mesmo tempo; os nomes dos botões vêm de GameInput.
    /// Comando PS4/PS5: analógico esq. = direção · R2 = acelerar · L2 = travar (com direção = derrapagem) ·
    /// Quadrado = travão de mão (derrapagem radical) · X ou R1 = nitro · analógico dir. vertical no ar = picar/levantar.
    /// Teclado: A/D ou ←/→ · W/↑ = acelerar · S/↓ = travar · Espaço = travão de mão · Shift = nitro · Q/E = picar no ar.
    /// </summary>
    public class PlayerCraftInput : MonoBehaviour
    {
        public float keyboardSteerRamp = 4.5f;
        [Range(0.05f, 0.4f)] public float stickDeadzone = 0.12f;
        [Range(1f, 2.5f)] public float stickCurve = 1.35f;     // resposta não-linear: precisão perto do centro
        [Tooltip("Ativa o modo experimental: analógico direito vertical controla inclinação e altitude.")]
        public bool flightControlMode = true;
        float kbSteer;

        public CraftInput Read(float dt)
        {
            var input = new CraftInput { flightControlMode = flightControlMode };
            var kb = Keyboard.current;
            var pad = GameInput.Pad;
            float steer = 0f;
            if (kb != null)
            {
                float target = 0f;
                if (kb.aKey.isPressed || kb.leftArrowKey.isPressed) target -= 1f;
                if (kb.dKey.isPressed || kb.rightArrowKey.isPressed) target += 1f;
                kbSteer = Mathf.MoveTowards(kbSteer, target, keyboardSteerRamp * dt * (target == 0f ? 1.6f : 1f));
                steer = kbSteer;
                if (kb.wKey.isPressed || kb.upArrowKey.isPressed) input.throttle = 1f;
                if (kb.sKey.isPressed || kb.downArrowKey.isPressed) input.brake = true;
                if (kb.spaceKey.isPressed) input.drift = true;
                if (kb.leftShiftKey.isPressed || kb.rightShiftKey.isPressed) input.boost = true;
                if (kb.qKey.isPressed) input.airPitch -= 1f;
                if (kb.eKey.isPressed) input.airPitch += 1f;
            }
            if (pad != null)
            {
                float x = pad.leftStick.ReadValue().x;
                if (Mathf.Abs(x) > stickDeadzone)
                    steer = Mathf.Sign(x) * Mathf.Pow(Mathf.InverseLerp(stickDeadzone, 1f, Mathf.Abs(x)), stickCurve);
                else if (pad.dpad.left.isPressed) steer = -1f;
                else if (pad.dpad.right.isPressed) steer = 1f;
                float r2 = Mathf.InverseLerp(0.05f, 0.95f, pad.rightTrigger.ReadValue());
                input.throttle = Mathf.Max(input.throttle, r2);
                if (pad.leftTrigger.ReadValue() > 0.25f) input.brake = true;
                if (pad.buttonWest.isPressed) input.drift = true;
                if (pad.buttonSouth.isPressed || pad.rightShoulder.isPressed) input.boost = true;
                float ry = pad.rightStick.ReadValue().y;
                input.airPitch = Mathf.Abs(ry) > stickDeadzone ? -Mathf.Sign(ry) * Mathf.Pow(Mathf.InverseLerp(stickDeadzone, 1f, Mathf.Abs(ry)), stickCurve) : 0f;
            }
            input.steer = Mathf.Clamp(steer, -1f, 1f);
            return input;
        }

        public static bool AutopilotPressed() => Keyboard.current != null && Keyboard.current.f3Key.wasPressedThisFrame;
        public static bool GridPressed() => Keyboard.current != null && Keyboard.current.gKey.wasPressedThisFrame;
        public static bool SlowMotionPressed() => Keyboard.current != null && Keyboard.current.f2Key.wasPressedThisFrame;
    }
}
