using RedDust.Vehicle;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.DualShock;

namespace RedDust.Game
{
    public enum KeyScheme { None, Full, Left, Right }

    /// <summary>
    /// Comandos de UM piloto (ecrã dividido: cada jogador tem o seu comando, ou metade do teclado).
    /// Comando PS4/PS5: analógico esq. = direção · analógico dir. vertical = inclinação/altitude experimental · R2 acelerar · L2 travar · Quadrado derrapagem · X/R1 nitro ·
    /// L1 usar consumível · D-pad ↑/↓ escolher consumível · Triângulo reposicionar.
    /// Teclado inteiro: A/D ou setas · W acelerar · S travar · Espaço derrapagem · Shift nitro · 1/2/3 consumíveis · R reposicionar.
    /// Metade esquerda (2 jogadores sem comandos): WASD · Espaço · Shift esq. · 1/2/3 · R.
    /// Metade direita: setas · Ctrl dir. derrapagem · Shift dir. nitro · 8/9/0 consumíveis · Backspace reposicionar.
    /// </summary>
    public sealed class PilotInput
    {
        public Gamepad pad;
        public KeyScheme keys;
        float kbSteer, rumbleLow, rumbleHigh, rumbleUntil;
        public bool vibration = true;

        public PilotInput(Gamepad pad, KeyScheme keys) { this.pad = pad; this.keys = keys; }

        public string Describe => pad != null ? (pad is DualShockGamepad ? (pad.displayName ?? "Comando PlayStation") : pad.displayName) :
            keys == KeyScheme.Left ? "Teclado (WASD)" : keys == KeyScheme.Right ? "Teclado (setas)" : "Teclado";

        static bool K(Key k) => Keyboard.current != null && Keyboard.current[k].isPressed;
        static bool KDown(Key k) => Keyboard.current != null && Keyboard.current[k].wasPressedThisFrame;

        public CraftInput Read(float dt)
        {
            var input = new CraftInput { flightControlMode = true };
            float steer = 0f;
            if (keys != KeyScheme.None && Keyboard.current != null)
            {
                bool left = keys == KeyScheme.Left ? K(Key.A) : keys == KeyScheme.Right ? K(Key.LeftArrow) : K(Key.A) || K(Key.LeftArrow);
                bool right = keys == KeyScheme.Left ? K(Key.D) : keys == KeyScheme.Right ? K(Key.RightArrow) : K(Key.D) || K(Key.RightArrow);
                float target = (right ? 1f : 0f) - (left ? 1f : 0f);
                kbSteer = Mathf.MoveTowards(kbSteer, target, 4.5f * dt * (target == 0f ? 1.6f : 1f));
                steer = kbSteer;
                switch (keys)
                {
                    case KeyScheme.Left:
                        if (K(Key.W)) input.throttle = 1f;
                        input.brake = K(Key.S); input.drift = K(Key.Space); input.boost = K(Key.LeftShift);
                        break;
                    case KeyScheme.Right:
                        if (K(Key.UpArrow)) input.throttle = 1f;
                        input.brake = K(Key.DownArrow); input.drift = K(Key.RightCtrl); input.boost = K(Key.RightShift);
                        break;
                    default:
                        if (K(Key.W) || K(Key.UpArrow)) input.throttle = 1f;
                        input.brake = K(Key.S) || K(Key.DownArrow); input.drift = K(Key.Space);
                        input.boost = K(Key.LeftShift) || K(Key.RightShift);
                        if (K(Key.Q)) input.airPitch -= 1f;
                        if (K(Key.E)) input.airPitch += 1f;
                        break;
                }
            }
            if (pad != null)
            {
                float x = pad.leftStick.ReadValue().x;
                if (Mathf.Abs(x) > 0.12f) steer = Mathf.Sign(x) * Mathf.Pow(Mathf.InverseLerp(0.12f, 1f, Mathf.Abs(x)), 1.35f);
                else if (pad.dpad.left.isPressed) steer = -1f;
                else if (pad.dpad.right.isPressed) steer = 1f;
                input.throttle = Mathf.Max(input.throttle, Mathf.InverseLerp(0.05f, 0.95f, pad.rightTrigger.ReadValue()));
                if (pad.leftTrigger.ReadValue() > 0.25f) input.brake = true;
                if (pad.buttonWest.isPressed) input.drift = true;
                if (pad.buttonSouth.isPressed || pad.rightShoulder.isPressed) input.boost = true;
                float ry = pad.rightStick.ReadValue().y;
                input.airPitch = Mathf.Abs(ry) > 0.12f ? -Mathf.Sign(ry) * Mathf.Pow(Mathf.InverseLerp(0.12f, 1f, Mathf.Abs(ry)), 1.35f) : 0f;
            }
            input.steer = Mathf.Clamp(steer, -1f, 1f);
            return input;
        }

        /// <summary>Consumível pedido neste frame: -1 nenhum, 0..2 slot direto, 9 = slot selecionado (L1).</summary>
        public int ConsumablePressed()
        {
            if (pad != null && pad.leftShoulder.wasPressedThisFrame) return 9;
            switch (keys)
            {
                case KeyScheme.Right:
                    if (KDown(Key.Digit8)) return 0; if (KDown(Key.Digit9)) return 1; if (KDown(Key.Digit0)) return 2; break;
                case KeyScheme.Left:
                case KeyScheme.Full:
                    if (KDown(Key.Digit1)) return 0; if (KDown(Key.Digit2)) return 1; if (KDown(Key.Digit3)) return 2; break;
            }
            return -1;
        }

        public int SelectDelta()
        {
            if (pad != null) { if (pad.dpad.up.wasPressedThisFrame) return -1; if (pad.dpad.down.wasPressedThisFrame) return 1; }
            return 0;
        }

        public bool ResetPressed() =>
            (pad != null && pad.buttonNorth.wasPressedThisFrame) ||
            (keys == KeyScheme.Right ? KDown(Key.Backspace) : keys != KeyScheme.None && KDown(Key.R));

        public bool PausePressed() =>
            (pad != null && pad.startButton.wasPressedThisFrame) || (keys != KeyScheme.None && KDown(Key.Escape));

        public float Look() => pad != null && Mathf.Abs(pad.rightStick.ReadValue().x) > 0.15f ? pad.rightStick.ReadValue().x : 0f;
        public float FlightPitch() => pad != null ? -pad.rightStick.ReadValue().y : 0f;
        public bool LookBack() => (pad != null && pad.rightStickButton.isPressed) || (keys == KeyScheme.Full && K(Key.C));

        public void Rumble(float low, float high, float seconds)
        {
            rumbleLow = Mathf.Max(rumbleLow, low); rumbleHigh = Mathf.Max(rumbleHigh, high);
            rumbleUntil = Time.unscaledTime + seconds;
        }

        public void Tick(Color light)
        {
            if (pad == null) return;
            bool on = vibration && Time.timeScale > 0f && Time.unscaledTime < rumbleUntil;
            pad.SetMotorSpeeds(on ? rumbleLow : 0f, on ? rumbleHigh : 0f);
            if (!on) { rumbleLow = rumbleHigh = 0f; }
            if (pad is DualShockGamepad ds) ds.SetLightBarColor(light);
        }

        public void Stop() { if (pad != null) pad.SetMotorSpeeds(0f, 0f); }
    }
}
