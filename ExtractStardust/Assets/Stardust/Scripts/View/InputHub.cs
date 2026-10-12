using UnityEngine;
using UnityEngine.InputSystem;

namespace Stardust
{
    /// <summary>Menu-level input shared by every device (confirm / back).</summary>
    public static class MenuInput
    {
        public static bool AnyConfirm()
        {
            var kb = Keyboard.current;
            if (kb != null && (kb.enterKey.wasPressedThisFrame || kb.spaceKey.wasPressedThisFrame)) return true;
            foreach (var p in Gamepad.all) if (p.buttonSouth.wasPressedThisFrame || p.startButton.wasPressedThisFrame) return true;
            var ts = Touchscreen.current;
            if (ts != null && ts.primaryTouch.press.wasPressedThisFrame) return true;
            var m = Mouse.current;
            if (m != null && m.leftButton.wasPressedThisFrame) return true;
            return false;
        }

        public static bool AnyBack()
        {
            var kb = Keyboard.current;
            if (kb != null && kb.escapeKey.wasPressedThisFrame) return true;
            foreach (var p in Gamepad.all) if (p.buttonEast.wasPressedThisFrame) return true;
            return false;
        }
    }

    /// <summary>On-screen touch controls for Android: steer left/right, handbrake, nitro, two consumables, pause, map.</summary>
    public class TouchControls : MonoBehaviour
    {
        public bool anyTouchSeen;
        public RectTransform left, right, brake, boost, slotA, slotB, pause, map;
        readonly bool[] prev = new bool[4];

        public void Read(out float steer, out bool boostOn, out bool brakeOn, out bool aDown, out bool bDown, out bool pauseDown)
        {
            Read(out steer, out boostOn, out brakeOn, out aDown, out bDown, out pauseDown, out _);
        }

        public void Read(out float steer, out bool boostOn, out bool brakeOn, out bool aDown, out bool bDown, out bool pauseDown, out bool mapDown)
        {
            steer = 0f; boostOn = brakeOn = aDown = bDown = pauseDown = mapDown = false;
            var ts = Touchscreen.current;
            if (ts == null) return;
            bool a = false, b = false, p = false, m = false;
            foreach (var t in ts.touches)
            {
                if (!t.press.isPressed) continue;
                anyTouchSeen = true;
                var pos = t.position.ReadValue();
                if (Hit(left, pos)) steer -= 1f;
                else if (Hit(right, pos)) steer += 1f;
                else if (Hit(brake, pos)) brakeOn = true;
                else if (Hit(boost, pos)) boostOn = true;
                else if (Hit(slotA, pos)) a = true;
                else if (Hit(slotB, pos)) b = true;
                else if (Hit(pause, pos)) p = true;
                else if (Hit(map, pos)) m = true;
            }
            aDown = a && !prev[0];
            bDown = b && !prev[1];
            pauseDown = p && !prev[2];
            mapDown = m && !prev[3];
            prev[0] = a; prev[1] = b; prev[2] = p; prev[3] = m;
        }

        static bool Hit(RectTransform r, Vector2 screen)
        {
            if (r == null || !r.gameObject.activeInHierarchy) return false;
            return RectTransformUtility.RectangleContainsScreenPoint(r, screen, null);
        }
    }
}
