using System.Collections.Generic;
using UnityEngine;

namespace RedDust.Track
{
    /// <summary>
    /// Percurso ativo na cena: carrega os dados do eixo invisível e desenha gizmos de design no editor
    /// (eixo, limites de corrida, bank, início de segmentos, ravinas e cavernas). Não desenha nada em jogo.
    /// </summary>
    public class CourseRuntime : MonoBehaviour
    {
        public TextAsset courseBytes;
        [Tooltip("Grafo de percursos (principal + ramos); opcional")] public TextAsset graphBytes;
        [Tooltip("Obstáculos dentro das linhas de corrida (pilares, rocha caída) para a IA; opcional")] public TextAsset obstaclesJson;
        public string title = "";
        [Tooltip("Desenhar a cada N estações")] public int gizmoStride = 6;
        public bool drawLanes = true;

        public static CourseRuntime Active { get; private set; }
        CourseGraph graph;

        /// <summary>Grafo de percursos (só o principal quando não há ficheiro de grafo).</summary>
        public CourseGraph Graph
        {
            get
            {
                if (graph == null)
                {
                    if (graphBytes != null) graph = CourseGraph.Load(graphBytes.bytes);
                    else if (courseBytes != null) graph = CourseGraph.Single(CourseData.Load(courseBytes.bytes));
                    if (graph != null && obstaclesJson != null) graph.LoadObstacles(obstaclesJson.text);
                }
                return graph;
            }
        }

        /// <summary>Percurso principal.</summary>
        public CourseData Data => Graph?.Main.Data;

        void OnEnable() => Active = this;
        void OnDisable() { if (Active == this) Active = null; }

        void OnDrawGizmos()
        {
            var g = Graph;
            if (g == null) return;
            foreach (var p in g.Paths) DrawPath(p.Data, p.IsMain);
        }

        void DrawPath(CourseData d, bool main)
        {
            int stride = Mathf.Max(1, gizmoStride);
            for (int i = stride; i < d.StationCount; i += stride)
            {
                int j = i - stride;
                Gizmos.color = d.IsGap(i) ? Color.red : d.IsCave(i) ? new Color(0.6f, 0.4f, 1f) : main ? Color.white : new Color(1f, 0.75f, 0.2f);
                Gizmos.DrawLine(d.Center[j] + d.Up[j] * 0.5f, d.Center[i] + d.Up[i] * 0.5f);
                if (drawLanes)
                {
                    Gizmos.color = new Color(0.2f, 1f, 0.9f, 0.8f);
                    Gizmos.DrawLine(d.LanePoint(j, -1f), d.LanePoint(i, -1f));
                    Gizmos.DrawLine(d.LanePoint(j, 1f), d.LanePoint(i, 1f));
                }
                if (i % (stride * 10) == 0)
                {
                    // bank: traço lateral inclinado
                    float b = Mathf.Clamp01(Mathf.Abs(d.Bank[i]) / 65f);
                    Gizmos.color = Color.Lerp(Color.green, Color.red, b);
                    Gizmos.DrawLine(d.Center[i] - d.Right[i] * 6f, d.Center[i] + d.Right[i] * 6f);
                    Gizmos.DrawLine(d.Center[i], d.Center[i] + d.Up[i] * 6f);
                }
            }
            Gizmos.color = Color.yellow;
            for (int i = 1; i < d.StationCount; i++)
                if (d.Segment[i] != d.Segment[i - 1]) Gizmos.DrawWireSphere(d.Center[i], 4f);
        }
    }

    /// <summary>
    /// Normal suavizada de um impacto de raio numa MeshCollider (interpolação baricêntrica das normais
    /// importadas), para que a atitude das naves não "salte" entre faces da malha a 450 km/h.
    /// </summary>
    public static class SurfaceNormals
    {
        struct MeshData { public Vector3[] normals; public int[] triangles; }
        static readonly Dictionary<EntityId, MeshData> cache = new Dictionary<EntityId, MeshData>();

        public static Vector3 Smooth(in RaycastHit hit)
        {
            if (!(hit.collider is MeshCollider mc) || mc.sharedMesh == null || hit.triangleIndex < 0) return hit.normal;
            var mesh = mc.sharedMesh;
            var id = mesh.GetEntityId();
            if (!cache.TryGetValue(id, out var md))
            {
                if (!mesh.isReadable) { cache[id] = default; return hit.normal; }
                md = new MeshData { normals = mesh.normals, triangles = mesh.triangles };
                cache[id] = md;
            }
            if (md.normals == null || md.normals.Length == 0) return hit.normal;
            int t = hit.triangleIndex * 3;
            if (t + 2 >= md.triangles.Length) return hit.normal;
            Vector3 bc = hit.barycentricCoordinate;
            Vector3 n = md.normals[md.triangles[t]] * bc.x + md.normals[md.triangles[t + 1]] * bc.y + md.normals[md.triangles[t + 2]] * bc.z;
            n = mc.transform.TransformDirection(n);
            float m = n.magnitude;
            if (m < 1e-4f) return hit.normal;
            n /= m;
            return Vector3.Dot(n, hit.normal) > 0.5f ? n : hit.normal;
        }

        public static void Clear() { cache.Clear(); SurfaceTypes.Clear(); }
    }

    /// <summary>Tipos de superfície natural (codificados no canal R da cor dos vértices pela geologia do Blender).</summary>
    public enum Surface { Sand, DeepSand, Slickrock, Gravel, Rock }

    /// <summary>
    /// Comportamento de cada superfície para as naves (TARGETS DE TUNING): nenhuma linha é a "estrada";
    /// cada uma troca velocidade por risco. Areia funda trava, cascalho escorrega, slickrock é rápido mas
    /// tem degraus e buracos, rocha rugosa abana e magoa.
    /// </summary>
    public struct SurfaceTraits
    {
        public float grip;        // multiplicador da aderência lateral
        public float topSpeed;    // multiplicador da velocidade máxima
        public float drag;        // desaceleração extra (m/s²) à velocidade máxima, proporcional a (v/vmax)²
        public float shake;       // vibração (0..1) para câmera/comando

        public static SurfaceTraits Of(Surface s)
        {
            switch (s)
            {
                case Surface.DeepSand: return new SurfaceTraits { grip = 0.78f, topSpeed = 0.84f, drag = 16f, shake = 0.15f };
                case Surface.Slickrock: return new SurfaceTraits { grip = 1.08f, topSpeed = 1.03f, drag = 0f, shake = 0.05f };
                case Surface.Gravel: return new SurfaceTraits { grip = 0.72f, topSpeed = 0.97f, drag = 3f, shake = 0.4f };
                case Surface.Rock: return new SurfaceTraits { grip = 0.88f, topSpeed = 0.95f, drag = 4f, shake = 0.6f };
                default: return new SurfaceTraits { grip = 1f, topSpeed = 1f, drag = 0f, shake = 0.08f };
            }
        }

        public static SurfaceTraits Lerp(SurfaceTraits a, SurfaceTraits b, float t) => new SurfaceTraits
        {
            grip = Mathf.Lerp(a.grip, b.grip, t), topSpeed = Mathf.Lerp(a.topSpeed, b.topSpeed, t),
            drag = Mathf.Lerp(a.drag, b.drag, t), shake = Mathf.Lerp(a.shake, b.shake, t),
        };
    }

    /// <summary>Leitura do tipo de superfície no ponto de impacto de um raio (cor do vértice mais próximo do triângulo).</summary>
    public static class SurfaceTypes
    {
        struct MeshData { public Color[] colors; public int[] triangles; }
        static readonly Dictionary<EntityId, MeshData> cache = new Dictionary<EntityId, MeshData>();

        public static Surface FromClass(float r)
        {
            if (r < 0.0625f) return Surface.Sand;
            if (r < 0.1875f) return Surface.DeepSand;
            if (r < 0.3125f) return Surface.Slickrock;
            if (r < 0.4375f) return Surface.Gravel;
            if (r < 0.5625f) return Surface.Slickrock;    // parede polida pela água
            if (r < 0.9f) return Surface.Rock;
            return Surface.Sand;                          // topo do planalto
        }

        public static Surface At(in RaycastHit hit)
        {
            if (!(hit.collider is MeshCollider mc) || mc.sharedMesh == null || hit.triangleIndex < 0) return Surface.Rock;
            var mesh = mc.sharedMesh;
            var id = mesh.GetEntityId();
            if (!cache.TryGetValue(id, out var md))
            {
                md = mesh.isReadable ? new MeshData { colors = mesh.colors, triangles = mesh.triangles } : default;
                cache[id] = md;
            }
            if (md.colors == null || md.colors.Length == 0) return Surface.Rock;
            int t = hit.triangleIndex * 3;
            if (t + 2 >= md.triangles.Length) return Surface.Rock;
            Vector3 bc = hit.barycentricCoordinate;
            int k = bc.x >= bc.y && bc.x >= bc.z ? 0 : (bc.y >= bc.z ? 1 : 2);
            return FromClass(md.colors[md.triangles[t + k]].r);
        }

        public static void Clear() => cache.Clear();
    }
}
