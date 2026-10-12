using System;
using System.IO;
using System.Text;
using UnityEngine;

namespace RedDust.Track
{
    /// <summary>
    /// Dados de um percurso gerado pelo construtor de geologia do Blender (ficheiro "RDDC"): eixo invisível
    /// com referencial por estação (tangente, direita, cima com bank), parâmetros de design (largura, bank,
    /// inclinação, ravina/caverna, superfície), limites de corrida e a secção real esculpida (anel de vértices).
    /// É a fonte única para física de teste, IA, checkpoints e telemetria; nunca gera geometria visível.
    /// </summary>
    public sealed class CourseData
    {
        public const int FlagGap = 1, FlagCave = 2;

        public int StationCount { get; private set; }
        public int RingCount { get; private set; }
        public float Step { get; private set; }

        public float[] Dist;
        public Vector3[] Center, Tangent, Right, Up;
        public float[] Width, Bank, Slope, RideLeft, RideRight;
        public int[] Flags, Segment, Surface;
        public Vector3[] Ring;       // StationCount * RingCount, coordenadas do mundo
        public float[] RingArc;      // comprimento de arco (com sinal) desde o eixo, por vértice do anel
        public string[] SegmentIds;

        public float Length => Dist[StationCount - 1];
        public int CenterIndex => RingCount / 2;

        public static CourseData Load(byte[] bytes)
        {
            using var br = new BinaryReader(new MemoryStream(bytes));
            if (Encoding.ASCII.GetString(br.ReadBytes(4)) != "RDDC") throw new InvalidDataException("percurso: assinatura inválida");
            int version = br.ReadInt32();
            if (version != 1) throw new InvalidDataException($"percurso: versão {version} não suportada");
            var c = new CourseData { StationCount = br.ReadInt32(), RingCount = br.ReadInt32(), Step = br.ReadSingle() };
            int S = c.StationCount, N = c.RingCount;
            c.Dist = new float[S]; c.Center = new Vector3[S]; c.Tangent = new Vector3[S]; c.Right = new Vector3[S]; c.Up = new Vector3[S];
            c.Width = new float[S]; c.Bank = new float[S]; c.Slope = new float[S]; c.RideLeft = new float[S]; c.RideRight = new float[S];
            c.Flags = new int[S]; c.Segment = new int[S]; c.Surface = new int[S];
            c.Ring = new Vector3[S * N];
            c.RingArc = new float[S * N];
            Vector3 V() => new Vector3(br.ReadSingle(), br.ReadSingle(), br.ReadSingle());
            for (int i = 0; i < S; i++)
            {
                c.Dist[i] = br.ReadSingle();
                c.Center[i] = V(); c.Tangent[i] = V(); c.Right[i] = V(); c.Up[i] = V();
                c.Width[i] = br.ReadSingle(); c.Bank[i] = br.ReadSingle(); c.Slope[i] = br.ReadSingle();
                c.Flags[i] = br.ReadInt32(); c.Segment[i] = br.ReadInt32(); c.Surface[i] = br.ReadInt32();
                c.RideLeft[i] = br.ReadSingle(); c.RideRight[i] = br.ReadSingle();
                for (int k = 0; k < N; k++) c.Ring[i * N + k] = V();
                // arco com sinal a partir do eixo
                int mid = N / 2;
                c.RingArc[i * N + mid] = 0f;
                for (int k = mid + 1; k < N; k++) c.RingArc[i * N + k] = c.RingArc[i * N + k - 1] + Vector3.Distance(c.Ring[i * N + k], c.Ring[i * N + k - 1]);
                for (int k = mid - 1; k >= 0; k--) c.RingArc[i * N + k] = c.RingArc[i * N + k + 1] - Vector3.Distance(c.Ring[i * N + k], c.Ring[i * N + k + 1]);
            }
            int segs = br.ReadInt32();
            c.SegmentIds = new string[segs];
            for (int i = 0; i < segs; i++) c.SegmentIds[i] = Encoding.UTF8.GetString(br.ReadBytes(br.ReadInt32()));
            return c;
        }

        public bool IsGap(int i) => (Flags[Mathf.Clamp(i, 0, StationCount - 1)] & FlagGap) != 0;
        public bool IsCave(int i) => (Flags[Mathf.Clamp(i, 0, StationCount - 1)] & FlagCave) != 0;
        public string SegmentName(int i) => SegmentIds[Mathf.Clamp(Segment[Mathf.Clamp(i, 0, StationCount - 1)], 0, SegmentIds.Length - 1)];

        public int StationAt(float dist) => Mathf.Clamp(Mathf.RoundToInt(dist / Step), 0, StationCount - 1);

        /// <summary>Estação mais próxima (procura local em torno de hint; global se não houver hint ou ficar longe).</summary>
        public int Nearest(Vector3 p, int hint = -1, int window = 160)
        {
            int best = -1;
            float bd = float.MaxValue;
            if (hint >= 0)
            {
                int a = Mathf.Max(0, hint - window), b = Mathf.Min(StationCount - 1, hint + window);
                for (int i = a; i <= b; i++)
                {
                    float d = (Center[i] - p).sqrMagnitude;
                    if (d < bd) { bd = d; best = i; }
                }
                if (bd < 120f * 120f) return best;
            }
            for (int i = 0; i < StationCount; i += 4)
            {
                float d = (Center[i] - p).sqrMagnitude;
                if (d < bd) { bd = d; best = i; }
            }
            int lo = Mathf.Max(0, best - 4), hi = Mathf.Min(StationCount - 1, best + 4);
            for (int i = lo; i <= hi; i++)
            {
                float d = (Center[i] - p).sqrMagnitude;
                if (d < bd) { bd = d; best = i; }
            }
            return best;
        }

        /// <summary>Distância ao longo do percurso da projeção de p, a partir da estação i.</summary>
        public float DistanceAlong(Vector3 p, int i)
        {
            i = Mathf.Clamp(i, 0, StationCount - 1);
            float d = Vector3.Dot(p - Center[i], Tangent[i]);
            return Mathf.Clamp(Dist[i] + d, 0f, Length);
        }

        /// <summary>Coordenada lateral normalizada u (-1..1) do ponto p na estação i (via arco da secção real).</summary>
        public float LateralU(Vector3 p, int i)
        {
            int N = RingCount, o = i * N;
            int best = 0; float bd = float.MaxValue;
            for (int k = 0; k < N; k++)
            {
                float d = (Ring[o + k] - p).sqrMagnitude;
                if (d < bd) { bd = d; best = k; }
            }
            float arc = RingArc[o + best];
            return arc < 0f ? Mathf.Max(-1.5f, arc / Mathf.Max(1f, RideLeft[i])) : Mathf.Min(1.5f, arc / Mathf.Max(1f, RideRight[i]));
        }

        /// <summary>Ponto da secção real na estação i para a coordenada lateral u (-1 = limite esq., +1 = limite dir.).</summary>
        public Vector3 LanePoint(int i, float u)
        {
            i = Mathf.Clamp(i, 0, StationCount - 1);
            int N = RingCount, o = i * N;
            float arc = u < 0f ? u * RideLeft[i] : u * RideRight[i];
            // procura binária no arco (monótono crescente)
            int lo = 0, hi = N - 1;
            if (arc <= RingArc[o]) return Ring[o];
            if (arc >= RingArc[o + hi]) return Ring[o + hi];
            while (hi - lo > 1)
            {
                int m = (lo + hi) >> 1;
                if (RingArc[o + m] <= arc) lo = m; else hi = m;
            }
            float t = Mathf.InverseLerp(RingArc[o + lo], RingArc[o + hi], arc);
            return Vector3.Lerp(Ring[o + lo], Ring[o + hi], t);
        }

        public Vector3 LanePoint(float dist, float u)
        {
            float f = Mathf.Clamp(dist / Step, 0f, StationCount - 1.001f);
            int i = (int)f;
            return Vector3.Lerp(LanePoint(i, u), LanePoint(i + 1, u), f - i);
        }

        /// <summary>Normal da superfície (aproximada pelo anel) para a coordenada lateral u na estação i.</summary>
        public Vector3 LaneNormal(int i, float u)
        {
            i = Mathf.Clamp(i, 1, StationCount - 2);
            Vector3 a = LanePoint(i, u - 0.02f), b = LanePoint(i, u + 0.02f);
            Vector3 f = LanePoint(i + 1, u) - LanePoint(i - 1, u);
            return MathX.SafeNormalize(Vector3.Cross(f, b - a), Up[i]);
        }

        public void Frame(float dist, out Vector3 pos, out Vector3 tangent, out Vector3 right, out Vector3 up)
        {
            float f = Mathf.Clamp(dist / Step, 0f, StationCount - 1.001f);
            int i = (int)f;
            float t = f - i;
            pos = Vector3.Lerp(Center[i], Center[i + 1], t);
            tangent = Vector3.Slerp(Tangent[i], Tangent[i + 1], t).normalized;
            right = Vector3.Slerp(Right[i], Right[i + 1], t).normalized;
            up = Vector3.Slerp(Up[i], Up[i + 1], t).normalized;
        }

        /// <summary>Curvatura horizontal média (1/m) do eixo entre dist e dist+span.</summary>
        public float CurvatureAhead(float dist, float span)
        {
            int a = StationAt(dist), b = StationAt(dist + span);
            if (b <= a) return 0f;
            Vector3 t0 = Tangent[a]; t0.y = 0f; Vector3 t1 = Tangent[b]; t1.y = 0f;
            float ang = Vector3.Angle(t0, t1) * Mathf.Deg2Rad;
            return ang / Mathf.Max(1f, Dist[b] - Dist[a]);
        }

        /// <summary>Inclinação (graus) da superfície real na coordenada u da estação i.</summary>
        public float SurfaceAngle(int i, float u) => Vector3.Angle(LaneNormal(i, u), Vector3.up);

        /// <summary>Procura a coordenada u (lado indicado) onde a superfície atinge o ângulo pedido.</summary>
        public float LaneForAngle(int i, float degrees, int side)
        {
            float best = 0f, bd = float.MaxValue;
            for (float u = 0f; u <= 1.0f; u += 0.01f)
            {
                float a = SurfaceAngle(i, u * side);
                float d = Mathf.Abs(a - degrees);
                if (d < bd) { bd = d; best = u * side; }
            }
            return best;
        }
    }
}
