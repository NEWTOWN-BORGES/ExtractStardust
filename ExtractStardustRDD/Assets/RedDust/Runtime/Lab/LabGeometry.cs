using System;
using System.Collections.Generic;
using UnityEngine;

namespace RedDust.Lab
{
    /// <summary>
    /// Construtor das malhas do laboratório de métricas (Fase 1 da V2).
    ///
    /// Duas regras que não são opcionais:
    ///
    /// 1. Tudo vai para a camada <see cref="Layers.Ground"/> (8) com MeshCollider, porque é a única
    ///    que <c>HoverSensor</c> sonda (Layers.GroundMask). Sem isto a nave cai ao vazio.
    ///
    /// 2. As malhas levam <b>cor de vértice</b>. A aderência em <c>CraftController</c> vem de
    ///    <c>SurfaceTypes.At(hit)</c>, que lê o canal R da cor do vértice e a mapeia para uma
    ///    superfície (grip, topSpeed, drag, shake). Sem cores, a superfície é Rock
    ///    (grip 0,88 · topSpeed 0,95 · drag 4) e <b>todas</b> as medições da Fase 1 ficam
    ///    contaminadas. O laboratório usa um pavimento de referência (Slickrock, R≈0,25)
    ///    para que os números dependam da nave e não do chão.
    ///
    /// A malha é declarada legível por software para que <c>SurfaceTypes</c> consiga ler cores e
    /// triângulos em batchmode, onde não há upload para GPU.
    /// </summary>
    public static class LabGeometry
    {
        public const byte Layer = Layers.Ground;

        /// <summary>Canal R da superfície de referência do laboratório (Slickrock).</summary>
        public const float RefSurfaceR = 0.25f;

        /// <summary>Cor de vértice que corresponde à superfície de referência.</summary>
        public static Color RefColor => new Color(RefSurfaceR, RefSurfaceR, RefSurfaceR, 1f);

        // ------------------------------------------------------------------ utilitários

        static Mesh Finish(Mesh mesh, Vector3[] verts, int[] tris, Color[] cols)
        {
            mesh.indexFormat = verts.Length > 65000
                ? UnityEngine.Rendering.IndexFormat.UInt32
                : UnityEngine.Rendering.IndexFormat.UInt16;
            mesh.vertices = verts;
            mesh.triangles = tris;
            mesh.colors = cols;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            // marcação para leitura por software em batchmode
            mesh.UploadMeshData(false);
            return mesh;
        }

        /// <summary>Objeto de cena com MeshCollider na camada de chão, pronto a ser sondado.</summary>
        public static GameObject Surface(string name, Mesh mesh, bool addCollider = true)
        {
            var go = new GameObject(name) { layer = Layer };
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            if (addCollider)
            {
                var mc = go.AddComponent<MeshCollider>();
                mc.sharedMesh = mesh;
                mc.cookingOptions = MeshColliderCookingOptions.None;
            }
            return go;
        }

        static Vector3[] CircleArc(Vector3 centre, float radius, float a0, float a1, int segs)
        {
            var pts = new Vector3[segs + 1];
            for (int i = 0; i <= segs; i++)
            {
                float a = Mathf.Lerp(a0, a1, (float)i / segs);
                pts[i] = centre + new Vector3(Mathf.Sin(a) * radius, 0f, Mathf.Cos(a) * radius);
            }
            return pts;
        }

        // ------------------------------------------------------------------ pista e bancos

        /// <summary>Placa de chão horizontal. É a base do arranque e do corredor de travagem.</summary>
        public static Mesh Flat(string name, Vector2 size)
        {
            float hx = size.x * 0.5f, hz = size.y * 0.5f;
            var v = new[]
            {
                new Vector3(-hx, 0f, -hz), new Vector3(hx, 0f, -hz),
                new Vector3(hx, 0f, hz), new Vector3(-hx, 0f, hz),
            };
            var t = new[] { 0, 2, 1, 0, 3, 2 };
            return Finish(new Mesh { name = name }, v, t, Fill(v.Length, RefColor));
        }

        static Color[] Fill(int n, Color c)
        {
            var a = new Color[n];
            for (int i = 0; i < n; i++) a[i] = c;
            return a;
        }

        /// <summary>
        /// Banco plano e inclinado: uma faixa de largura <paramref name="width"/> com o bordo interior
        /// elevado, formando um plano a <paramref name="bankDeg"/> graus. Comprimento em Z.
        /// </summary>
        public static Mesh BankStraight(string name, float length, float width, float bankDeg)
        {
            float rad = bankDeg * Mathf.Deg2Rad;
            float c = Mathf.Cos(rad), s = Mathf.Sin(rad);
            float hx = width * 0.5f;
            // bordo interior (-X) sobe; o exterior fica no chão
            Vector3 In(float z) => new Vector3(-hx * c, hx * s, z);
            Vector3 Out(float z) => new Vector3(hx * c, -hx * s, z);
            var v = new[] { In(0f), Out(0f), Out(length), In(length) };
            var t = new[] { 0, 1, 2, 0, 2, 3 };
            return Finish(new Mesh { name = name }, v, t, Fill(4, RefColor));
        }

        /// <summary>
        /// Piso plano fechado, formado por dois arcos concêntricos. Serve de base à referência
        /// plana (R sem bank) e ao miolo de um half-pipe.
        /// </summary>
        public static Mesh CircleFlat(string name, Vector3 centre, float radius, float width, int segs = 96)
        {
            float hw = width * 0.5f;
            var v = new List<Vector3>();
            var c = new List<Color>();
            var t = new List<int>();
            for (int i = 0; i < segs; i++)
            {
                float a0 = Mathf.PI * 2f * i / segs;
                float a1 = Mathf.PI * 2f * (i + 1) / segs;
                int b = v.Count;
                v.Add(centre + new Vector3(Mathf.Sin(a0) * (radius - hw), 0f, Mathf.Cos(a0) * (radius - hw)));
                v.Add(centre + new Vector3(Mathf.Sin(a0) * (radius + hw), 0f, Mathf.Cos(a0) * (radius + hw)));
                v.Add(centre + new Vector3(Mathf.Sin(a1) * (radius + hw), 0f, Mathf.Cos(a1) * (radius + hw)));
                v.Add(centre + new Vector3(Mathf.Sin(a1) * (radius - hw), 0f, Mathf.Cos(a1) * (radius - hw)));
                for (int k = 0; k < 4; k++) c.Add(RefColor);
                t.AddRange(new[] { b, b + 1, b + 2, b, b + 2, b + 3 });
            }
            return Finish(new Mesh { name = name }, v.ToArray(), t.ToArray(), c.ToArray());
        }

        /// <summary>
        /// Arco com o piso inclinado a <paramref name="bankDeg"/> graus. A normal do plano aponta para
        /// dentro da curva, que é o que permite fazer o raio a velocidade.
        /// </summary>
        public static Mesh CircleBanked(string name, Vector3 centre, float radius, float width,
                                        float bankDeg, int segs = 128)
        {
            float hw = width * 0.5f;
            float rad = bankDeg * Mathf.Deg2Rad;
            float c = Mathf.Cos(rad), s = Mathf.Sin(rad);
            var v = new List<Vector3>();
            var col = new List<Color>();
            var t = new List<int>();
            for (int i = 0; i < segs; i++)
            {
                float a0 = Mathf.PI * 2f * i / segs;
                float a1 = Mathf.PI * 2f * (i + 1) / segs;
                var rIn0 = new Vector3(Mathf.Sin(a0), 0f, Mathf.Cos(a0));
                var rIn1 = new Vector3(Mathf.Sin(a1), 0f, Mathf.Cos(a1));
                // interior mais alto: a normal inclina-se para o centro
                Vector3 pIn0 = centre + rIn0 * (radius - hw * c) + Vector3.up * (hw * s);
                Vector3 pOut0 = centre + rIn0 * (radius + hw * c) - Vector3.up * (hw * s);
                Vector3 pOut1 = centre + rIn1 * (radius + hw * c) - Vector3.up * (hw * s);
                Vector3 pIn1 = centre + rIn1 * (radius - hw * c) + Vector3.up * (hw * s);
                int b = v.Count;
                v.Add(pIn0); v.Add(pOut0); v.Add(pOut1); v.Add(pIn1);
                for (int k = 0; k < 4; k++) col.Add(RefColor);
                // ordem escolhida para a normal apontar para cima/dentro
                t.AddRange(new[] { b, b + 1, b + 2, b, b + 2, b + 3 });
            }
            return Finish(new Mesh { name = name }, v.ToArray(), t.ToArray(), col.ToArray());
        }

        /// <summary>
        /// Half-pipe: corte transversal curvo entre dois bordos elevados. Gerado por varrimento de
        /// secção ao longo de um arco, como manda a secção E do plano.
        /// </summary>
        public static Mesh HalfPipe(string name, Vector3 centre, float radius, float width,
                                    float wallDeg, int segs = 128, int across = 14)
        {
            float hw = width * 0.5f;
            float wall = wallDeg * Mathf.Deg2Rad;
            var v = new List<Vector3>();
            var col = new List<Color>();
            var t = new List<int>();
            for (int i = 0; i < segs; i++)
            {
                float a0 = Mathf.PI * 2f * i / segs;
                float a1 = Mathf.PI * 2f * (i + 1) / segs;
                var r0 = new Vector3(Mathf.Sin(a0), 0f, Mathf.Cos(a0));
                var r1 = new Vector3(Mathf.Sin(a1), 0f, Mathf.Cos(a1));
                int b = v.Count;
                for (int k = 0; k <= across; k++)
                {
                    // -1 (bordo esquerdo) .. +1 (bordo direito)
                    float u = Mathf.Lerp(-1f, 1f, (float)k / across);
                    // perfil: parábola que sobe até wallDeg nos bordos
                    float lift = Mathf.Abs(u) * hw * Mathf.Tan(wall);
                    float off = u * hw;
                    v.Add(centre + r0 * (radius + off) + Vector3.up * lift);
                }
                for (int k = 0; k <= across; k++)
                {
                    float u = Mathf.Lerp(-1f, 1f, (float)k / across);
                    float lift = Mathf.Abs(u) * hw * Mathf.Tan(wall);
                    float off = u * hw;
                    v.Add(centre + r1 * (radius + off) + Vector3.up * lift);
                }
                int stride = across + 1;
                for (int k = 0; k < across; k++)
                {
                    int a = b + k, bb = b + k + 1, cc = b + stride + k + 1, dd = b + stride + k;
                    t.AddRange(new[] { a, dd, cc, a, cc, bb });
                }
                for (int k = 0; k < v.Count - b; k++) col.Add(RefColor);
            }
            return Finish(new Mesh { name = name }, v.ToArray(), t.ToArray(), col.ToArray());
        }

        /// <summary>
        /// Parede inclinada para testes de wall-ride. Devolve a malha e, por referência, os pontos
        /// de entrada e de saída no plano médio da parede.
        /// </summary>
        public static Mesh Wall(string name, float length, float height, float angleDeg, out Vector3 entry, out Vector3 exit)
        {
            float rad = angleDeg * Mathf.Deg2Rad;
            float run = height / Mathf.Tan(rad);       // avanço horizontal
            var v = new[]
            {
                new Vector3(0f, 0f, 0f),
                new Vector3(run, 0f, 0f),
                new Vector3(run, height, 0f),
                new Vector3(0f, height, 0f),
                new Vector3(0f, 0f, length),
                new Vector3(run, 0f, length),
                new Vector3(run, height, length),
                new Vector3(0f, height, length),
            };
            var t = new[]
            {
                0, 1, 2, 0, 2, 3,       // triângulo lateral
                4, 6, 5, 4, 7, 6,       // lateral oposto
                3, 2, 6, 3, 6, 7,       // face inclinada (a superfície de corrida)
                0, 4, 5, 0, 5, 1,       // base
            };
            entry = new Vector3(0f, height * 0.5f, 0f);
            exit = new Vector3(0f, height * 0.5f, length);
            return Finish(new Mesh { name = name }, v, t, Fill(8, RefColor));
        }

        /// <summary>Rampa/lábio de salto: plano inclinado que termina numa aresta viva.</summary>
        public static Mesh Lip(string name, float length, float width, float angleDeg, out Vector3 topEdge)
        {
            float rad = angleDeg * Mathf.Deg2Rad;
            float rise = length * Mathf.Tan(rad);
            float hx = width * 0.5f;
            var v = new[]
            {
                new Vector3(-hx, 0f, 0f), new Vector3(hx, 0f, 0f),
                new Vector3(hx, rise, length), new Vector3(-hx, rise, length),
            };
            var t = new[] { 0, 1, 2, 0, 2, 3 };
            topEdge = new Vector3(0f, rise, length);
            return Finish(new Mesh { name = name }, v, t, Fill(4, RefColor));
        }

        /// <summary>
        /// Corredor: dois muros laterais ao longo de Z, com o chão entre eles. Devolve o chão e as
        /// paredes em malhas separadas para o relatório poder nomeá-las.
        /// </summary>
        public static void Corridor(string name, float length, float width, float wallHeight,
                                    out Mesh floor, out Mesh wallLeft, out Mesh wallRight)
        {
            floor = Flat(name + "_floor", new Vector2(width, length));
            wallLeft = WallFace(name + "_wallL", length, width * 0.5f, wallHeight);
            wallRight = WallFace(name + "_wallR", length, -width * 0.5f, wallHeight);
        }

        static Mesh WallFace(string name, float length, float x, float height)
        {
            float y0 = 0f, y1 = height;
            var v = new[]
            {
                new Vector3(x, y0, 0f), new Vector3(x, y0, length),
                new Vector3(x, y1, length), new Vector3(x, y1, 0f),
            };
            var t = x < 0f ? new[] { 0, 1, 2, 0, 2, 3 } : new[] { 0, 2, 1, 0, 3, 2 };
            return Finish(new Mesh { name = name }, v, t, Fill(4, RefColor));
        }

        /// <summary>Transição de bank: interpola a inclinação de <paramref name="fromDeg"/> a
        ///  <paramref name="toDeg"/> ao longo de Z, para medir a taxa de mudança admissível.</summary>
        public static Mesh BankTransition(string name, float length, float width,
                                          float fromDeg, float toDeg, int steps = 64)
        {
            var v = new List<Vector3>();
            var col = new List<Color>();
            var t = new List<int>();
            float hx = width * 0.5f;
            for (int i = 0; i <= steps; i++)
            {
                float f = (float)i / steps;
                float bank = Mathf.Lerp(fromDeg, toDeg, f) * Mathf.Deg2Rad;
                float c = Mathf.Cos(bank), s = Mathf.Sin(bank);
                float z = length * f;
                v.Add(new Vector3(-hx * c, hx * s, z));
                v.Add(new Vector3(hx * c, -hx * s, z));
                col.Add(RefColor); col.Add(RefColor);
            }
            for (int i = 0; i < steps; i++)
            {
                int a = i * 2;
                t.AddRange(new[] { a, a + 1, a + 3, a, a + 3, a + 2 });
            }
            return Finish(new Mesh { name = name }, v.ToArray(), t.ToArray(), col.ToArray());
        }
    }
}
