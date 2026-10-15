using System;
using System.Globalization;
using UnityEngine;

namespace RedDust
{
    /// <summary>Camadas de física do projeto (configuradas pelo setup do editor).</summary>
    public static class Layers
    {
        public const int Ground = 8;       // geologia percorrível: corredor, cavernas, deserto
        public const int Obstacle = 9;     // rochas soltas, pilares, destroços (colisão, sem repulsor)
        public const int Craft = 10;       // naves
        public const int Checkpoint = 11;  // volumes de checkpoint (trigger)

        public const int GroundMask = 1 << Ground;
        public const int SolidMask = (1 << Ground) | (1 << Obstacle);
        public const int CameraMask = (1 << Ground) | (1 << Obstacle);
    }

    public static class Units
    {
        public const float MsToKmh = 3.6f;
        public static float ToKmh(float ms) => ms * MsToKmh;
        public static float FromKmh(float kmh) => kmh / MsToKmh;
    }

    public static class MathX
    {
        public static float Smoothstep(float a, float b, float x)
        {
            float t = Mathf.Clamp01((x - a) / (b - a));
            return t * t * (3f - 2f * t);
        }

        /// <summary>Fator de suavização exponencial independente do frame rate.</summary>
        public static float Damp(float lambda, float dt) => 1f - Mathf.Exp(-lambda * dt);

        public static Vector3 SafeNormalize(Vector3 v, Vector3 fallback)
        {
            float m = v.magnitude;
            return m > 1e-6f ? v / m : fallback;
        }

        /// <summary>Ângulo (graus) entre o "cima" de um referencial e o cima do mundo, com sinal pelo lado direito.</summary>
        public static float RollDegrees(Vector3 up, Vector3 right)
        {
            float a = Vector3.Angle(up, Vector3.up);
            return right.y > 0f ? -a : a;
        }
    }

    /// <summary>Leitura de argumentos da linha de comandos (autotestes, perfis de qualidade).</summary>
    public static class CommandLine
    {
        static string[] args;
        static string[] Args => args ??= Environment.GetCommandLineArgs();

        public static bool Has(string flag) => Array.IndexOf(Args, flag) >= 0;

        public static string Value(string flag, string fallback = null)
        {
            int i = Array.IndexOf(Args, flag);
            return i >= 0 && i + 1 < Args.Length ? Args[i + 1] : fallback;
        }

        public static float Float(string flag, float fallback)
        {
            var v = Value(flag);
            return v != null && float.TryParse(v, NumberStyles.Float, CultureInfo.InvariantCulture, out var f) ? f : fallback;
        }

        public static int Int(string flag, int fallback)
        {
            var v = Value(flag);
            return v != null && int.TryParse(v, out var i) ? i : fallback;
        }
    }
}
