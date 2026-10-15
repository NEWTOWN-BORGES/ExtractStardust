using System;
using System.Collections.Generic;

namespace RedDust.Meta
{
    // Camada de meta-jogo (Doc 02 + Doc 03): C# puro, sem UnityEngine, para poder correr num servidor e ser testada fora do Unity.

    public enum Rarity { Common, Uncommon, Rare, Epic, Legendary }
    public enum Family { Engine, Propulsion, Wings, Tail, Armor, Reactor, Cooling, Utility }
    public enum SizeClass { S, M, L }

    /// <summary>Os 8 stats do Doc 02 §2 (escala 0..100) e três atributos de módulo (massa em kg, suporte de reparação, sensores).</summary>
    public enum Stat { Speed, Accel, Handling, Stability, Hull, Efficiency, Cooling, Boost, Mass, Repair, Intel }

    public enum RaceState { Racing, Extracted, Destroyed, Stranded, Abandoned }
    public enum GameMode { Exploration, Extraction, LocalVersus }

    public static class StatInfo
    {
        public const int CoreCount = 8;
        public const int Count = 11;
        static readonly string[] names = { "Velocidade", "Aceleração", "Manobra", "Estabilidade", "Casco", "Eficiência", "Refrigeração", "Boost", "Massa", "Reparação", "Sensores" };
        static readonly string[] shorts = { "VEL", "ACE", "MAN", "EST", "CAS", "EFI", "REF", "BST", "kg", "REP", "SEN" };
        public static string Name(Stat s) => names[(int)s];
        public static string Short(Stat s) => shorts[(int)s];
    }

    public static class RarityInfo
    {
        /// <summary>Stat budget inicial por raridade (Doc 02 §7, TARGET).</summary>
        public static readonly int[] Budget = { 10, 13, 16, 20, 23 };
        /// <summary>Avaliação média para o HUD e o Pool (Doc 03 §10).</summary>
        public static readonly int[] AvgValue = { 500, 1100, 3000, 7000, 18000 };
        static readonly string[] names = { "Comum", "Incomum", "Raro", "Épico", "Lendário" };
        /// <summary>Cores de UI (Doc 02 §7): branco, verde, azul, roxo, dourado.</summary>
        public static readonly uint[] Rgb = { 0xE6E6E6, 0x5CD36B, 0x4C9DFF, 0xB46BFF, 0xFFC23A };
        public static string Name(Rarity r) => names[(int)r];
    }

    public static class Fmt
    {
        /// <summary>✦12 500 (separador de milhares fixo: não depende das culturas instaladas no Android).</summary>
        public static string Dust(long v) => "✦" + v.ToString("N0", System.Globalization.CultureInfo.InvariantCulture).Replace(',', ' ');
    }

    /// <summary>
    /// Gerador determinístico (xorshift64). As rolagens da economia usam-no em vez do UnityEngine.Random,
    /// para serem reproduzíveis e poderem ser feitas pela autoridade (servidor) com a mesma lógica.
    /// </summary>
    public sealed class Rng
    {
        ulong s;
        public Rng(ulong seed) { s = seed == 0 ? 0x9E3779B97F4A7C15UL : seed; NextU(); }
        public static Rng FromTime() => new Rng((ulong)DateTime.UtcNow.Ticks ^ ((ulong)(uint)Guid.NewGuid().GetHashCode() << 32));

        public ulong NextU() { s ^= s << 13; s ^= s >> 7; s ^= s << 17; return s; }
        /// <summary>[0, 1)</summary>
        public double Next() => (NextU() >> 11) * (1.0 / (1UL << 53));
        /// <summary>[a, b)</summary>
        public int Range(int a, int b) => b <= a ? a : a + (int)(Next() * (b - a));
        public float Range(float a, float b) => a + (float)Next() * (b - a);
        public bool Chance(double p) => Next() < p;
        public T Pick<T>(IList<T> list) => list[Range(0, list.Count)];

        public void Shuffle<T>(IList<T> list)
        {
            for (int i = list.Count - 1; i > 0; i--) { int j = Range(0, i + 1); (list[i], list[j]) = (list[j], list[i]); }
        }

        /// <summary>Índice escolhido com pesos (todos ≥ 0).</summary>
        public int Weighted(IList<double> weights)
        {
            double sum = 0; foreach (var w in weights) sum += Math.Max(0, w);
            if (sum <= 0) return 0;
            double r = Next() * sum;
            for (int i = 0; i < weights.Count; i++) { r -= Math.Max(0, weights[i]); if (r < 0) return i; }
            return weights.Count - 1;
        }
    }

    /// <summary>Stats finais de uma nave (chassis + módulos). Valores core 0..100; massa em kg acrescentados.</summary>
    public sealed class ShipStats
    {
        public readonly float[] v = new float[StatInfo.Count];
        public float this[Stat s] { get => v[(int)s]; set => v[(int)s] = value; }
        public float BaseMassKg;
        public float MassKg => BaseMassKg + v[(int)Stat.Mass];
        /// <summary>Perks lendários ativos nesta build (ids).</summary>
        public readonly List<string> Perks = new List<string>();
    }
}
