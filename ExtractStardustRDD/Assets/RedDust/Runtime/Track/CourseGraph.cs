using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace RedDust.Track
{
    /// <summary>Um percurso do grafo: o principal, ou um ramo que sai dele em From e volta em To (distâncias do principal).</summary>
    public sealed class CoursePath
    {
        public string Id;
        public int Index, Parent;
        public float From, To, Length;      // Length: comprimento próprio do eixo
        public CourseData Data;
        public bool IsMain => Parent < 0;

        /// <summary>Distância de corrida (no principal) equivalente à distância d deste percurso.</summary>
        public float ToRaceDistance(float d) => IsMain ? d : Mathf.Lerp(From, To, Mathf.InverseLerp(Data.Start, Data.Length, d));
    }

    /// <summary>
    /// Grafo de percursos gerado pelo Blender (ficheiro "RDDG" v2): o principal e os ramos (linhas SAFE / RACING /
    /// SKILL, ilhas, bancadas). Cada ramo sai do principal e volta a ele; a geometria das junções é contínua
    /// (união de vazios). Sem ficheiro de grafo, o grafo tem só o principal.
    /// </summary>
    public sealed class CourseGraph
    {
        public CoursePath[] Paths;
        public CoursePath Main => Paths[0];

        public static CourseGraph Load(byte[] bytes)
        {
            using var br = new BinaryReader(new MemoryStream(bytes));
            if (Encoding.ASCII.GetString(br.ReadBytes(4)) != "RDDG") throw new InvalidDataException("grafo: assinatura inválida");
            int version = br.ReadInt32();
            if (version != 2) throw new InvalidDataException($"grafo: versão {version} não suportada");
            int count = br.ReadInt32();
            var g = new CourseGraph { Paths = new CoursePath[count] };
            for (int k = 0; k < count; k++)
            {
                var p = new CoursePath { Index = k };
                p.Id = Encoding.UTF8.GetString(br.ReadBytes(br.ReadInt32()));
                p.Parent = br.ReadInt32();
                p.From = br.ReadSingle(); p.To = br.ReadSingle(); p.Length = br.ReadSingle();
                int S = br.ReadInt32(), N = br.ReadInt32();
                p.Data = CourseData.ReadBody(br, S, N, br.ReadSingle());
                g.Paths[k] = p;
            }
            return g;
        }

        public static CourseGraph Single(CourseData main) => new CourseGraph
        {
            Paths = new[] { new CoursePath { Id = "main", Index = 0, Parent = -1, From = 0f, To = main.Length, Length = main.Length, Data = main } }
        };

        public int BranchCount => Paths.Length - 1;

        /// <summary>
        /// Em que percurso está o ponto p: o de superfície (secção real) mais próxima. Nas junções as superfícies
        /// coincidem; a histerese mantém o percurso atual até outro estar claramente mais perto.
        /// </summary>
        public void Locate(Vector3 p, ref int path, ref int station, float hysteresis = 4f)
        {
            path = Mathf.Clamp(path, 0, Paths.Length - 1);
            var cur = Paths[path].Data;
            station = cur.Nearest(p, station);
            float best = SurfaceDistance(cur, p, station) - hysteresis;
            int bestPath = path, bestStation = station;
            for (int k = 0; k < Paths.Length; k++)
            {
                if (k == path) continue;
                var d = Paths[k].Data;
                if (!d.Bounds.Contains(p)) continue;
                int s = d.Nearest(p);
                float dist = SurfaceDistance(d, p, s);
                if (dist < best) { best = dist; bestPath = k; bestStation = s; }
            }
            path = bestPath;
            station = bestStation;
        }

        /// <summary>Distância de p à secção real (anel) do percurso nas estações vizinhas de s.</summary>
        public static float SurfaceDistance(CourseData d, Vector3 p, int s)
        {
            int N = d.RingCount;
            float best = float.MaxValue;
            for (int i = Mathf.Max(0, s - 1); i <= Mathf.Min(d.StationCount - 1, s + 1); i++)
            {
                int o = i * N;
                for (int k = 0; k < N; k += 2) best = Mathf.Min(best, (d.Ring[o + k] - p).sqrMagnitude);
            }
            return Mathf.Sqrt(best);
        }

        /// <summary>Ramos que saem do principal entre as distâncias a e b.</summary>
        public IEnumerable<CoursePath> BranchesLeaving(float a, float b)
        {
            foreach (var p in Paths)
                if (!p.IsMain && p.From >= a && p.From < b) yield return p;
        }
    }
}
