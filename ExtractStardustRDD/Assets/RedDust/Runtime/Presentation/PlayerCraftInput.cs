using RedDust.Vehicle;
using UnityEngine;
using UnityEngine.InputSystem;

namespace RedDust.Presentation
{
    /// <summary>
    /// Pilotagem do jogador (aceleração automática, como no jogo anterior). Teclado e comando funcionam ao
    /// mesmo tempo; os nomes dos botões vêm de GameInput.
    /// Comando PS4/PS5: analógico esq. = direção · R2 ou X = boost · L2 ou Quadrado = travão/derrapagem ·
    /// analógico dir. vertical no ar = picar/levantar.
    /// Teclado: A/D ou ←/→ · W/↑/Shift = boost · S/↓/Espaço = travão · Q/E = picar no ar.
    /// </summary>
    public class PlayerCraftInput : MonoBehaviour
    {
        public float keyboardSteerRamp = 4.5f;
        [Range(0.05f, 0.4f)] public float stickDeadzone = 0.12f;
        [Range(1f, 2.5f)] public float stickCurve = 1.35f;     // resposta não-linear: precisão perto do centro
        float kbSteer;

        public CraftInput Read(float dt)
        {
            var input = CraftInput.Auto;
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
                if (kb.sKey.isPressed || kb.downArrowKey.isPressed || kb.spaceKey.isPressed) input.brake = true;
                if (kb.wKey.isPressed || kb.upArrowKey.isPressed || kb.leftShiftKey.isPressed) input.boost = true;
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
                if (pad.leftTrigger.ReadValue() > 0.25f || pad.buttonWest.isPressed) input.brake = true;
                if (pad.rightTrigger.ReadValue() > 0.25f || pad.buttonSouth.isPressed) input.boost = true;
                float ry = pad.rightStick.ReadValue().y;
                if (Mathf.Abs(ry) > 0.2f) input.airPitch = -ry;
            }
            input.steer = Mathf.Clamp(steer, -1f, 1f);
            return input;
        }

        public static bool AutopilotPressed() => Keyboard.current != null && Keyboard.current.f3Key.wasPressedThisFrame;
        public static bool GridPressed() => Keyboard.current != null && Keyboard.current.gKey.wasPressedThisFrame;
        public static bool SlowMotionPressed() => Keyboard.current != null && Keyboard.current.f2Key.wasPressedThisFrame;
    }
}
