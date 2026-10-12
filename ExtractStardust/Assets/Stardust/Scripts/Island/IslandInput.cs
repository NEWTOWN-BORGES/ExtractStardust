using UnityEngine;
using UnityEngine.InputSystem;

namespace Stardust
{
    /// <summary>
    /// Controls of the island game (port of controls.gd). Scheme 0 = single player (all keys, any gamepad, touch);
    /// 1 = split-screen player 1 (WASD + first gamepad); 2 = player 2 (arrows + second gamepad).
    /// PS4/PS5: stick/d-pad steer · L2/Square handbrake · R2/Cross nitro · Triangle recover · Circle camera ·
    /// right stick look (R3 centre) · L1/R1 consumables · Options pause · touchpad/Share map.
    /// </summary>
    public class IslandInput
    {
        public int scheme;
        public TouchControls touch;
        public ShipControls ship;
        public Vector2 look;
        public bool lookCenter, useA, useB, recover, camCycle, pause, map;
        float steerSmooth;

        public IslandInput(int scheme) { this.scheme = scheme; }

        Gamepad Pad()
        {
            var all = Gamepad.all;
            if (scheme == 0) return Gamepad.current;
            if (scheme == 1) return all.Count >= 2 ? all[0] : null;
            if (all.Count >= 2) return all[1];
            return all.Count == 1 ? all[0] : null;
        }

        public bool UsingGamepad => Pad() != null;

        public void Poll(float dt)
        {
            float steer = 0f;
            bool brake = false, nitro = false;
            look = Vector2.zero;
            lookCenter = useA = useB = recover = camCycle = pause = map = false;
            var kb = Keyboard.current;
            if (kb != null)
            {
                bool wasd = scheme == 0 || scheme == 1, arrows = scheme == 0 || scheme == 2;
                if (wasd)
                {
                    if (kb.aKey.isPressed) steer -= 1f;
                    if (kb.dKey.isPressed) steer += 1f;
                    if (kb.sKey.isPressed || (scheme == 0 && kb.spaceKey.isPressed)) brake = true;
                    if (kb.leftShiftKey.isPressed || kb.wKey.isPressed) nitro = true;
                    if (kb.qKey.wasPressedThisFrame || (scheme == 0 && kb.digit1Key.wasPressedThisFrame)) useA = true;
                    if (kb.eKey.wasPressedThisFrame || (scheme == 0 && kb.digit2Key.wasPressedThisFrame)) useB = true;
                    if (kb.rKey.wasPressedThisFrame) recover = true;
                    if (kb.cKey.wasPressedThisFrame) camCycle = true;
                    if (kb.vKey.wasPressedThisFrame) lookCenter = true;
                }
                if (arrows)
                {
                    if (kb.leftArrowKey.isPressed) steer -= 1f;
                    if (kb.rightArrowKey.isPressed) steer += 1f;
                    if (kb.downArrowKey.isPressed) brake = true;
                    if (kb.rightShiftKey.isPressed || kb.upArrowKey.isPressed) nitro = true;
                    if (kb.numpad1Key.wasPressedThisFrame || kb.periodKey.wasPressedThisFrame) useA = true;
                    if (kb.numpad2Key.wasPressedThisFrame || kb.slashKey.wasPressedThisFrame) useB = true;
                    if (scheme == 2 && kb.numpad0Key.wasPressedThisFrame) camCycle = true;
                    if (scheme == 2 && kb.numpad3Key.wasPressedThisFrame) recover = true;
                }
                if (scheme == 0 && kb.mKey.wasPressedThisFrame) map = true;
                if (kb.escapeKey.wasPressedThisFrame || kb.pKey.wasPressedThisFrame) pause = true;
            }
            var pad = Pad();
            if (pad != null)
            {
                float sx = pad.leftStick.ReadValue().x;
                if (Mathf.Abs(sx) > 0.12f) steer += Mathf.Sign(sx) * Mathf.InverseLerp(0.12f, 1f, Mathf.Abs(sx));
                if (pad.dpad.left.isPressed) steer -= 1f;
                if (pad.dpad.right.isPressed) steer += 1f;
                if (pad.leftTrigger.ReadValue() > 0.25f || pad.buttonWest.isPressed) brake = true;       // L2 / Square
                if (pad.rightTrigger.ReadValue() > 0.25f || pad.buttonSouth.isPressed) nitro = true;     // R2 / Cross
                if (pad.buttonNorth.wasPressedThisFrame) recover = true;                                 // Triangle
                if (pad.buttonEast.wasPressedThisFrame) camCycle = true;                                 // Circle
                if (pad.rightStickButton.wasPressedThisFrame) lookCenter = true;                         // R3
                if (pad.leftShoulder.wasPressedThisFrame) useA = true;                                   // L1
                if (pad.rightShoulder.wasPressedThisFrame) useB = true;                                  // R1
                if (pad.startButton.wasPressedThisFrame) pause = true;                                   // Options
                if (pad.selectButton.wasPressedThisFrame) map = true;                                    // Share / touchpad
                var rs = pad.rightStick.ReadValue();
                if (rs.sqrMagnitude > 0.04f) look = rs;
            }
            bool touchActive = false;
            if (touch != null && touch.isActiveAndEnabled)
            {
                touch.Read(out float ts, out bool tb, out bool tbr, out bool ta, out bool tbb, out bool tp, out bool tm);
                if (touch.anyTouchSeen)
                {
                    touchActive = true;
                    steer += ts;
                    if (tb) nitro = true;
                    if (tbr) brake = true;
                    if (ta) useA = true;
                    if (tbb) useB = true;
                    if (tp) pause = true;
                    if (tm) map = true;
                }
            }
            steer = Mathf.Clamp(steer, -1f, 1f);
            // digital steering ramps a little (keyboard/touch); analog sticks keep their amplitude
            bool digital = touchActive || (kb != null && Mathf.Abs(steer) == 1f);
            steerSmooth = Mathf.MoveTowards(steerSmooth, steer, dt * (digital ? 6f : 50f));
            if (Mathf.Abs(steer) < 0.01f) steerSmooth = Mathf.MoveTowards(steerSmooth, 0f, dt * 9f);
            ship = new ShipControls { steer = steerSmooth, brake = brake, nitro = nitro };
        }

        public static string Hint(bool gamepad, bool mobile)
        {
            if (gamepad) return "Analógico: virar · L2/Quadrado: travão de mão · R2/X: nitro · L1/R1: itens · Triângulo: recuperar · Círculo: câmera";
            if (mobile) return "Esquerda: virar · TRAVAR + virar = derrapar · NITRO · aceleração automática";
            return "A D / ← →: virar · S / Espaço: travão de mão · Shift: nitro · Q E: itens · R: recuperar · C: câmera · M: mapa";
        }
    }
}
