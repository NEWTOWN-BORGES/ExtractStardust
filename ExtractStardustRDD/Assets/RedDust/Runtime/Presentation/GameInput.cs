using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.DualShock;
using UnityEngine.InputSystem.XInput;

namespace RedDust.Presentation
{
    public enum PadKind { None, DualShock4, DualSense, Xbox, Generic }

    /// <summary>
    /// Entrada unificada: teclado + comandos (PS4/PS5 de primeira classe, Xbox e genéricos também).
    /// Usa o último comando com atividade, mostra nomes de botões certos para cada tipo, vibração com
    /// duração e barra de luz (DualShock 4 / DualSense). Chamar Tick() uma vez por frame.
    ///
    /// Mapa (PS4/PS5): analógico esq. = direção · R2 ou X (cruz) = boost · L2 ou Quadrado = travão/derrapagem ·
    /// Triângulo = reposicionar · analógico dir. = olhar à volta · R3 = olhar para trás · OPTIONS = pausa ·
    /// CREATE/SHARE = painel técnico · X = confirmar, Bola = voltar nos menus.
    /// Teclado: A/D ou ←/→ · W/↑/Shift = boost · S/↓/Espaço = travão · R = reposicionar · C = olhar para trás ·
    /// Esc/P = pausa · Enter = confirmar · F1 = painel técnico.
    /// </summary>
    public static class GameInput
    {
        public static Gamepad Pad { get; private set; }
        public static PadKind Kind { get; private set; }
        public static bool LastUsedPad { get; private set; }
        static float rumbleUntil;
        static float rumbleLow, rumbleHigh, sustainLow, sustainHigh;
        static bool hooked;
        public static bool VibrationEnabled = true;
        static float navRepeat;

        public static void Init()
        {
            if (hooked) return;
            hooked = true;
            foreach (var d in InputSystem.devices) Debug.Log($"[RDD input] dispositivo: {d.layout} · {d.displayName} · {d.description.product}");
            InputSystem.onDeviceChange += (d, change) => Debug.Log($"[RDD input] {change}: {d.layout} · {d.displayName}");
            Application.quitting += StopHaptics;
        }

        public static void Tick()
        {
            var pad = Gamepad.current;
            if (pad != Pad)
            {
                Pad = pad;
                Kind = Classify(pad);
                if (pad != null) Debug.Log($"[RDD input] comando ativo: {Name} ({pad.layout})");
            }
            var kb = Keyboard.current;
            if (pad != null && PadActive(pad)) LastUsedPad = true;
            else if (kb != null && kb.anyKey.wasPressedThisFrame) LastUsedPad = false;

            // vibração: impulso com duração + nível contínuo (boost/derrapagem)
            if (Pad != null)
            {
                float low = sustainLow, high = sustainHigh;
                if (Time.unscaledTime < rumbleUntil) { low = Mathf.Max(low, rumbleLow); high = Mathf.Max(high, rumbleHigh); }
                if (!VibrationEnabled || Time.timeScale == 0f) { low = 0f; high = 0f; }
                Pad.SetMotorSpeeds(low, high);
            }
            sustainLow = sustainHigh = 0f;
        }

        static bool PadActive(Gamepad p) =>
            p.leftStick.ReadValue().sqrMagnitude > 0.04f || p.rightStick.ReadValue().sqrMagnitude > 0.04f ||
            p.leftTrigger.ReadValue() > 0.2f || p.rightTrigger.ReadValue() > 0.2f ||
            p.buttonSouth.isPressed || p.buttonEast.isPressed || p.buttonWest.isPressed || p.buttonNorth.isPressed ||
            p.startButton.isPressed || p.selectButton.isPressed || p.dpad.ReadValue().sqrMagnitude > 0.1f;

        static PadKind Classify(Gamepad p)
        {
            if (p == null) return PadKind.None;
            if (p is DualSenseGamepadHID) return PadKind.DualSense;
            if (p is DualShockGamepad) return PadKind.DualShock4;
            if (p is XInputController) return PadKind.Xbox;
            return PadKind.Generic;
        }

        public static string Name => Kind switch
        {
            PadKind.DualSense => "DualSense (PS5)",
            PadKind.DualShock4 => "DualShock 4 (PS4)",
            PadKind.Xbox => "Comando Xbox",
            PadKind.Generic => Pad != null ? Pad.displayName : "Comando",
            _ => "Teclado",
        };

        public static bool IsPlayStation => Kind == PadKind.DualSense || Kind == PadKind.DualShock4;

        public static void SetLightBar(Color c)
        {
            if (Pad is DualShockGamepad ds) ds.SetLightBarColor(c);
        }

        public static void Rumble(float low, float high, float seconds)
        {
            rumbleLow = Mathf.Clamp01(low); rumbleHigh = Mathf.Clamp01(high);
            rumbleUntil = Time.unscaledTime + seconds;
        }

        /// <summary>Vibração contínua deste frame (chamar todos os frames enquanto durar).</summary>
        public static void Sustain(float low, float high)
        {
            sustainLow = Mathf.Max(sustainLow, low); sustainHigh = Mathf.Max(sustainHigh, high);
        }

        public static void StopHaptics()
        {
            if (Pad != null) Pad.SetMotorSpeeds(0f, 0f);
            InputSystem.ResetHaptics();
        }

        // ------------------------------------------------------------------ ações

        static Keyboard Kb => Keyboard.current;

        public static float Look()
        {
            float x = 0f;
            if (Pad != null) { var r = Pad.rightStick.ReadValue(); if (Mathf.Abs(r.x) > 0.15f) x = r.x; }
            return x;
        }

        public static bool LookBack() =>
            (Pad != null && Pad.rightStickButton.isPressed) || (Kb != null && Kb.cKey.isPressed);

        public static bool Reset() =>
            (Pad != null && Pad.buttonNorth.wasPressedThisFrame) || (Kb != null && Kb.rKey.wasPressedThisFrame);

        public static bool Pause() =>
            (Pad != null && Pad.startButton.wasPressedThisFrame) || (Kb != null && (Kb.escapeKey.wasPressedThisFrame || Kb.pKey.wasPressedThisFrame));

        public static bool Confirm() =>
            (Pad != null && Pad.buttonSouth.wasPressedThisFrame) || (Kb != null && (Kb.enterKey.wasPressedThisFrame || Kb.numpadEnterKey.wasPressedThisFrame || Kb.spaceKey.wasPressedThisFrame));

        public static bool Back() =>
            (Pad != null && Pad.buttonEast.wasPressedThisFrame) || (Kb != null && (Kb.escapeKey.wasPressedThisFrame || Kb.backspaceKey.wasPressedThisFrame));

        public static bool Overlay() =>
            (Pad != null && Pad.selectButton.wasPressedThisFrame) || (Kb != null && Kb.f1Key.wasPressedThisFrame);

        /// <summary>Navegação vertical nos menus (cruz direcional, analógico ou setas), com repetição.</summary>
        public static int NavY()
        {
            int dir = 0;
            if (Kb != null)
            {
                if (Kb.upArrowKey.wasPressedThisFrame || Kb.wKey.wasPressedThisFrame) return -1;
                if (Kb.downArrowKey.wasPressedThisFrame || Kb.sKey.wasPressedThisFrame) return 1;
            }
            if (Pad != null)
            {
                if (Pad.dpad.up.wasPressedThisFrame) return -1;
                if (Pad.dpad.down.wasPressedThisFrame) return 1;
                float y = Pad.leftStick.ReadValue().y;
                if (Mathf.Abs(y) > 0.6f)
                {
                    dir = y > 0 ? -1 : 1;
                    if (Time.unscaledTime < navRepeat) return 0;
                    navRepeat = Time.unscaledTime + 0.28f;
                    return dir;
                }
                navRepeat = 0f;
            }
            return 0;
        }

        /// <summary>Navegação horizontal nos menus (mudar valores).</summary>
        public static int NavX()
        {
            if (Kb != null)
            {
                if (Kb.leftArrowKey.wasPressedThisFrame || Kb.aKey.wasPressedThisFrame) return -1;
                if (Kb.rightArrowKey.wasPressedThisFrame || Kb.dKey.wasPressedThisFrame) return 1;
            }
            if (Pad != null)
            {
                if (Pad.dpad.left.wasPressedThisFrame) return -1;
                if (Pad.dpad.right.wasPressedThisFrame) return 1;
            }
            return 0;
        }

        // ------------------------------------------------------------------ nomes dos botões para as dicas

        public static string BtnBoost => LastUsedPad && Pad != null ? (IsPlayStation ? "R2 / X" : "RT / A") : "W / Shift";
        public static string BtnBrake => LastUsedPad && Pad != null ? (IsPlayStation ? "L2 / Quadrado" : "LT / X") : "S / Espaço";
        public static string BtnReset => LastUsedPad && Pad != null ? (IsPlayStation ? "Triângulo" : "Y") : "R";
        public static string BtnPause => LastUsedPad && Pad != null ? (IsPlayStation ? "OPTIONS" : "Menu") : "Esc";
        public static string BtnConfirm => LastUsedPad && Pad != null ? (IsPlayStation ? "X" : "A") : "Enter";
        public static string BtnBack => LastUsedPad && Pad != null ? (IsPlayStation ? "Bola" : "B") : "Esc";
        public static string BtnSteer => LastUsedPad && Pad != null ? "analógico esquerdo" : "A / D";
        public static string BtnLook => LastUsedPad && Pad != null ? "analógico direito · R3 olhar para trás" : "C olhar para trás";
    }
}
