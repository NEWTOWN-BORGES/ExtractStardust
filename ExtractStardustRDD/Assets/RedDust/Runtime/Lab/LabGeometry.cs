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

        /// <summary>
        /// Aparência de uma malha do laboratório, no formato que o shader <c>RedDust/Geology</c> espera.
        /// O shader empacota quatro canais na cor do vértice e dois valores em UV2:
        ///   R = classe de superfície (0 areia · 0,125 areia funda · 0,25 slickrock · 0,375 cascalho ·
        ///       0,5 parede polida · 0,625 rocha rugosa · 0,75 falésia · ≥0,875 planalto)
        ///   G = índice da paleta A (÷15)   B = índice da paleta B (÷15)
        ///   A = máscara da zona de corrida (1 = percorrível)
        ///   UV2.x = dureza da camada   UV2.y = mistura A/B
        ///
        /// A mesma banda de R serve à física: <c>SurfaceTypes.FromClass</c> usa as mesmas classes
        /// (passo 1/16) para decidir grip, topSpeed e drag. Por isso <see cref="SurfaceClass"/> não é
        /// decoração — trocá-lo muda o comportamento da nave.
        /// </summary>
        public struct MeshStyle
        {
            public float SurfaceClass;
            public int LayerA;
            public int LayerB;
            public float RideMask;
            public float Hardness;
            public float Blend;

            /// <summary>Pavimento de referência do laboratório: slickrock claro e uniforme.</summary>
            public static MeshStyle Reference => new MeshStyle
            {
                SurfaceClass = RefSurfaceR,
                LayerA = LayerWhiteRim,        // 1 arenito claro
                LayerB = LayerNavajo,          // 10 areia quente
                RideMask = 1f,
                Hardness = 0.55f,
                Blend = 0.5f,
            };
        }

        // Índices da paleta de RDGeology.hlsl (RD_PAL, 14 camadas do Colorado Plateau).
        public const int LayerOrganRock = 0;
        public const int LayerWhiteRim = 1;
        public const int LayerMoenkopi = 2;
        public const int LayerMoenkopiClaro = 3;
        public const int LayerMossBack = 4;
        public const int LayerChinleVermelho = 5;
        public const int LayerChinlePurpura = 6;
        public const int LayerChinleCinza = 7;
        public const int LayerWingate = 8;
        public const int LayerKayenta = 9;
        public const int LayerNavajo = 10;
        public const int LayerNavajoRosado = 11;
        public const int LayerAreia = 12;
        public const int LayerVerniz = 13;

        // ------------------------------------------------------------------ utilitários

        /// <summary>Constrói a malha com o empacotamento de cor e UV2 que o shader de geologia espera.</summary>
        /// <param name="colors">
        /// Cores por vértice. Quando não é dado, todos os vértices recebem a cor uniforme do estilo —
        /// que é o correto para as superfícies de medição, mas não para uma parede com detrito, onde
        /// o cone tem de ler como material solto e não como a camada do topo.
        /// </param>
        static Mesh Finish(Mesh mesh, Vector3[] verts, int[] tris, MeshStyle style, Vector2[] uv = null,
                           Color[] colors = null)
        {
            mesh.indexFormat = verts.Length > 65000
                ? UnityEngine.Rendering.IndexFormat.UInt32
                : UnityEngine.Rendering.IndexFormat.UInt16;
            mesh.vertices = verts;
            mesh.triangles = tris;
            var u2 = new Vector2(Mathf.Clamp01(style.Hardness), Mathf.Clamp01(style.Blend));
            var uv2 = new Vector2[verts.Length];
            for (int i = 0; i < verts.Length; i++) uv2[i] = u2;
            if (colors != null && colors.Length == verts.Length)
            {
                mesh.colors = colors;
            }
            else
            {
                var cols = new Color[verts.Length];
                var c = ClassColor(style);
                for (int i = 0; i < verts.Length; i++) cols[i] = c;
                mesh.colors = cols;
            }
            mesh.uv2 = uv2;
            bool hasUv = uv != null && uv.Length == verts.Length;
            if (hasUv) mesh.uv = uv;
            mesh.RecalculateNormals();
            // Tangentes a partir das UVs: sem elas o normal map em espaço tangente não funciona
            // (a luz não reage à direção do relevo). Só faz sentido quando há UVs.
            if (hasUv) mesh.RecalculateTangents();
            mesh.RecalculateBounds();
            // 'false' = a malha continua legível por software, para o SurfaceTypes ler
            // cores e triângulos em batchmode (onde não há upload para GPU).
            mesh.UploadMeshData(false);
            return mesh;
        }

        /// <summary>
        /// Cor empacotada para o shader RedDust/Geology a partir de uma classe e de duas camadas
        /// da paleta. A classe (canal R) é lida pela física (SurfaceTypes): areia 0, cascalho 0,375,
        /// parede polida 0,5, rocha rugosa 0,625, falésia 0,75.
        /// </summary>
        public static Color ClassColor(float surfaceClass, int layerA, int layerB, float rideMask)
            => new Color(Mathf.Clamp01(surfaceClass),
                         Mathf.Clamp01(layerA / 15f),
                         Mathf.Clamp01(layerB / 15f),
                         Mathf.Clamp01(rideMask));

        /// <summary>Cor empacotada a partir de um <see cref="MeshStyle"/>.</summary>
        public static Color ClassColor(MeshStyle s)
            => ClassColor(s.SurfaceClass, s.LayerA, s.LayerB, s.RideMask);

        /// <summary>Objeto de cena com MeshCollider na camada de chão, pronto a ser sondado.</summary>
        public static GameObject Surface(string name, Mesh mesh, Material material = null, bool addCollider = true)
        {
            var go = new GameObject(name) { layer = Layer };
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            if (material != null) mr.sharedMaterial = material;
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
        public static Mesh Flat(string name, Vector2 size, MeshStyle? style = null)
        {
            float hx = size.x * 0.5f, hz = size.y * 0.5f;
            var v = new[]
            {
                new Vector3(-hx, 0f, -hz), new Vector3(hx, 0f, -hz),
                new Vector3(hx, 0f, hz), new Vector3(-hx, 0f, hz),
            };
            var t = new[] { 0, 2, 1, 0, 3, 2 };
            return Finish(new Mesh { name = name }, v, t, style ?? MeshStyle.Reference);
        }

        /// <summary>
        /// Banco plano e inclinado: uma faixa de largura <paramref name="width"/> com o bordo interior
        /// elevado, formando um plano a <paramref name="bankDeg"/> graus. Comprimento em Z.
        /// </summary>
        public static Mesh BankStraight(string name, float length, float width, float bankDeg, MeshStyle? style = null)
        {
            float rad = bankDeg * Mathf.Deg2Rad;
            float c = Mathf.Cos(rad), s = Mathf.Sin(rad);
            float hx = width * 0.5f;
            // bordo interior (-X) sobe; o exterior fica no chão
            Vector3 In(float z) => new Vector3(-hx * c, hx * s, z);
            Vector3 Out(float z) => new Vector3(hx * c, -hx * s, z);
            var v = new[] { In(0f), Out(0f), Out(length), In(length) };
            var t = new[] { 0, 1, 2, 0, 2, 3 };
            return Finish(new Mesh { name = name }, v, t, style ?? MeshStyle.Reference);
        }

        /// <summary>
        /// Piso plano fechado, formado por dois arcos concêntricos. Serve de base à referência
        /// plana (R sem bank) e ao miolo de um half-pipe.
        /// </summary>
        public static Mesh CircleFlat(string name, Vector3 centre, float radius, float width, int segs = 96,
                                      MeshStyle? style = null)
        {
            float hw = width * 0.5f;
            var v = new List<Vector3>();
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
                t.AddRange(new[] { b, b + 1, b + 2, b, b + 2, b + 3 });
            }
            return Finish(new Mesh { name = name }, v.ToArray(), t.ToArray(), style ?? MeshStyle.Reference);
        }

        /// <summary>
        /// Arco com o piso inclinado a <paramref name="bankDeg"/> graus. A normal do plano aponta para
        /// dentro da curva, que é o que permite fazer o raio a velocidade.
        /// </summary>
        public static Mesh CircleBanked(string name, Vector3 centre, float radius, float width,
                                        float bankDeg, int segs = 128, MeshStyle? style = null)
        {
            float hw = width * 0.5f;
            float rad = bankDeg * Mathf.Deg2Rad;
            float c = Mathf.Cos(rad), s = Mathf.Sin(rad);
            var v = new List<Vector3>();
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
                // ordem escolhida para a normal apontar para cima/dentro
                t.AddRange(new[] { b, b + 1, b + 2, b, b + 2, b + 3 });
            }
            return Finish(new Mesh { name = name }, v.ToArray(), t.ToArray(), style ?? MeshStyle.Reference);
        }

        /// <summary>
        /// Half-pipe: corte transversal curvo entre dois bordos elevados. Gerado por varrimento de
        /// secção ao longo de um arco, como manda a secção E do plano.
        /// </summary>
        public static Mesh HalfPipe(string name, Vector3 centre, float radius, float width,
                                    float wallDeg, int segs = 128, int across = 14, MeshStyle? style = null)
        {
            float hw = width * 0.5f;
            float wall = wallDeg * Mathf.Deg2Rad;
            var v = new List<Vector3>();
            var t = new List<int>();
            int stride = across + 1;
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
                    // perfil: sobe até wallDeg nos bordos
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
                for (int k = 0; k < across; k++)
                {
                    int a = b + k, bb = b + k + 1, cc = b + stride + k + 1, dd = b + stride + k;
                    t.AddRange(new[] { a, dd, cc, a, cc, bb });
                }
            }
            return Finish(new Mesh { name = name }, v.ToArray(), t.ToArray(), style ?? MeshStyle.Reference);
        }

        /// <summary>Rampa/lábio de salto: plano inclinado que termina numa aresta viva.</summary>
        public static Mesh Lip(string name, float length, float width, float angleDeg,
                               out Vector3 topEdge, MeshStyle? style = null)
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
            return Finish(new Mesh { name = name }, v, t, style ?? MeshStyle.Reference);
        }

        /// <summary>
        /// Corredor: dois muros laterais ao longo de Z, com o chão entre eles. Devolve o chão e as
        /// paredes em malhas separadas para o relatório poder nomeá-las.
        /// </summary>
        public static void Corridor(string name, float length, float width, float wallHeight,
                                    out Mesh floor, out Mesh wallLeft, out Mesh wallRight, MeshStyle? style = null)
        {
            var st = style ?? MeshStyle.Reference;
            floor = Flat(name + "_floor", new Vector2(width, length), st);
            wallLeft = WallFace(name + "_wallL", length, width * 0.5f, wallHeight, st);
            wallRight = WallFace(name + "_wallR", length, -width * 0.5f, wallHeight, st);
        }

        static Mesh WallFace(string name, float length, float x, float height, MeshStyle style)
        {
            float y0 = 0f, y1 = height;
            var v = new[]
            {
                new Vector3(x, y0, 0f), new Vector3(x, y0, length),
                new Vector3(x, y1, length), new Vector3(x, y1, 0f),
            };
            var t = x < 0f ? new[] { 0, 1, 2, 0, 2, 3 } : new[] { 0, 2, 1, 0, 3, 2 };
            return Finish(new Mesh { name = name }, v, t, style);
        }

        /// <summary>Transição de bank: interpola a inclinação de <paramref name="fromDeg"/> a
        ///  <paramref name="toDeg"/> ao longo de Z, para medir a taxa de mudança admissível.</summary>
        public static Mesh BankTransition(string name, float length, float width,
                                          float fromDeg, float toDeg, int steps = 64, MeshStyle? style = null)
        {
            var v = new List<Vector3>();
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
            }
            for (int i = 0; i < steps; i++)
            {
                int a = i * 2;
                t.AddRange(new[] { a, a + 1, a + 3, a, a + 3, a + 2 });
            }
            return Finish(new Mesh { name = name }, v.ToArray(), t.ToArray(), style ?? MeshStyle.Reference);
        }

        // ================================================================== erosão das paredes
        //
        // O gerador do Blender constrói o perfil da parede em segmentos RETOS
        // (recuo = espessura / tan(ângulo da camada)) mais uma bancada no topo. O `wall_warp`
        // existente está limitado a smoothstep(0, 70, x): só mexe no pé. O campo `relief` de
        // Column.sample (≤0,75 m) alimenta apenas o micro-relevo do shader, não a forma.
        // Resultado: paredes lisas, que foi exatamente a crítica do jogador.
        //
        // A erosão abaixo devolve recuo (m, ≥0) em função da dureza da camada e do ruído, e é a
        // versão C# do patch proposto para Art/Blender/rdd_route_lib.py (função `erode`).
        // Regra de segurança: o recuo é SOMADO à distância lateral, nunca subtraído, logo a
        // largura do corredor no eixo nunca diminui e as linhas de corrida ficam livres.

        /// <summary>Parâmetros da erosão da parede (valores por omissão = a coluna RED DUST DIVIDE).</summary>
        public struct ErosionStyle
        {
            public float Amount;        // recuo máximo das camadas mais moles (m)
            public float ScaleAlong;    // comprimento de onda ao longo da rota (m) — alcovas
            public float ScaleHeight;   // comprimento de onda em altura (m) — cornijas e laminações
            public int Seed;

            public static ErosionStyle Default => new ErosionStyle
            {
                Amount = 26f, ScaleAlong = 520f, ScaleHeight = 26f, Seed = 7,
            };

            public static ErosionStyle None => new ErosionStyle { Amount = 0f, ScaleAlong = 520f, ScaleHeight = 26f, Seed = 7 };
        }

        static float Hash1(float n, int seed)
        {
            float h = Mathf.Sin(n * 127.1f + seed * 311.7f) * 43758.5453f;
            return h - Mathf.Floor(h);
        }

        static float Noise1(float t, int seed)
        {
            float i = Mathf.Floor(t), f = t - i;
            f = f * f * (3f - 2f * f);
            return Mathf.Lerp(Hash1(i, seed), Hash1(i + 1f, seed), f);
        }

        /// <summary>
        /// Ruído 3D barato (valor + interpolação trilinear), para o campo de erosão variar em todas
        /// as direções e não só em duas.
        /// </summary>
        static float Noise3(Vector3 p, int seed)
        {
            float x0 = Mathf.Floor(p.x), y0 = Mathf.Floor(p.y), z0 = Mathf.Floor(p.z);
            float fx = p.x - x0, fy = p.y - y0, fz = p.z - z0;
            fx = fx * fx * (3f - 2f * fx);
            fy = fy * fy * (3f - 2f * fy);
            fz = fz * fz * (3f - 2f * fz);
            float H(float dx, float dy, float dz) =>
                Hash1(x0 + dx + (y0 + dy) * 57.1f + (z0 + dz) * 131.7f, seed);
            float c00 = Mathf.Lerp(H(0, 0, 0), H(1, 0, 0), fx);
            float c10 = Mathf.Lerp(H(0, 1, 0), H(1, 1, 0), fx);
            float c01 = Mathf.Lerp(H(0, 0, 1), H(1, 0, 1), fx);
            float c11 = Mathf.Lerp(H(0, 1, 1), H(1, 1, 1), fx);
            return Mathf.Lerp(Mathf.Lerp(c00, c10, fy), Mathf.Lerp(c01, c11, fy), fz);
        }

        static float Fbm3(Vector3 p, int octaves, int seed)
        {
            float s = 0f, a = 0.5f, n = 0f;
            var q = p;
            for (int o = 0; o < octaves; o++)
            {
                s += a * Noise3(q, seed + o * 17);
                n += a;
                q = q * 2.03f + new Vector3(11.3f, 5.7f, 7.9f);
                a *= 0.5f;
            }
            return s / n;
        }

        /// <summary>
        /// Recuo de erosão 3D (m, ≥0): é isto que dá alcovas, fluting e rachaduras de vários tamanhos.
        ///
        /// Combina quatro escalas, todas a puxar para dentro:
        ///   - alcova   : ~120 m ao longo, ~90 m em altura — recessos grandes e sombrios
        ///   - fluting  : ~18 m ao longo, ~14 m em altura — canais verticais de parede de arenito
        ///   - rachadura: ~5 m ao longo, ~4 m em altura — fissuras isoladas
        ///   - lasca    : ~1,2 m — irregularidade fina da superfície
        ///
        /// As escalas são divididas DIRETAMENTE pelas distâncias em metros. A primeira versão
        /// multiplicava a altura por 3 e isso empurrava a coordenada de ruído para valores muito
        /// altos (y/3,8 chegava a 260), o que saturava o ruído: o resultado eram riscas verticais
        /// uniformes em vez de manchas e fissuras.
        ///
        /// A dureza da camada controla a amplitude: uma camada mole (Chinle, 0,15) fica com o
        /// recesso cheio, uma dura (Wingate, 0,97) mantém-se quase intacta e sobressai como cornija.
        /// <paramref name="wallU"/> é a posição pela face da parede (0 = pé, 1 = topo) — é o que faz
        /// o recuo variar pela face e não apenas ao longo.
        /// </summary>
        public static float Erode3D(float height, float along, float wallU, float hardness,
                                    ErosionStyle e, float layerBlend = 0.5f)
        {
            if (e.Amount <= 0f) return 0f;

            float soft = Mathf.Clamp01(1f - hardness);
            float byHardness = e.Amount * Mathf.Pow(soft, 1.6f);

            float alcove = Fbm3(new Vector3(along / 120f, height / 90f, wallU * 1.1f), 3, e.Seed);
            float flute = Fbm3(new Vector3(along / 18f, height / 14f, wallU * 1.7f), 3, e.Seed + 101);
            float crack = Fbm3(new Vector3(along / 5f, height / 4f, wallU * 2.3f), 3, e.Seed + 211);
            float chip = Fbm3(new Vector3(along / 1.2f, height / 1.2f, wallU * 3.1f), 2, e.Seed + 307);

            float depth = 0.62f * alcove + 0.34f * flute + 0.24f * crack + 0.12f * chip;

            // o recuo acumula pela face: reentrâncias mais fundas a meio da parede, menos junto ao
            // pé (onde há detrito acumulado) e menos no topo (onde a rocha é mais sã)
            float byFace = 0.55f + 0.65f * Mathf.Sin(wallU * Mathf.PI);

            // nas transições entre camadas há reentrância extra: a mole escava-se mais depressa
            float atBoundary = 1f + 0.5f * (1f - Mathf.Abs(2f * layerBlend - 1f));

            return byHardness * byFace * atBoundary * depth;
        }

        /// <summary>
        /// Perfil 2D da parede: escadaria estratigráfica + <b>cone de detrito no pé</b>.
        ///
        /// O entulho é o que falta numa parede de canyon: nos canyons reais acumulam-se cones de
        /// talus e blocos caídos no sopé, e é isso que faz a parede "assentar" no chão em vez de
        /// nascer a pique. Devolve o perfil e a coordenada U (0 no topo, 1 na ponta do detrito),
        /// já com a erosão aplicada.
        ///
        /// A ponta do detrito NUNCA entra na zona de corrida: é limitada a
        /// <paramref name="clearHalfWidth"/>, para a largura útil do corredor não diminuir.
        /// </summary>
        static List<Vector3> WallProfilePoints(float baseHeight, (float y, float hardness)[] layers,
                                               int heightSamples, ErosionStyle erosion,
                                               float along, float talusHeight, float talusExtent,
                                               float clearHalfWidth, List<Color> colors)
        {
            colors.Clear();
            // ---- escadaria estratigráfica
            float lift = Mathf.Max(1f, layers.Length > 0 ? layers[layers.Length - 1].y - baseHeight : 1f);
            int budget = Mathf.Max(layers.Length * 3, heightSamples);
            var stair = new List<Vector2>();
            float x = 0f, y = baseHeight;
            stair.Add(new Vector2(0f, y));
            for (int i = 0; i < layers.Length; i++)
            {
                float top = layers[i].y;
                float hard = Mathf.Clamp01(layers[i].hardness);
                float effTan = Mathf.Tan(Mathf.Lerp(34f, 86f, hard) * Mathf.Deg2Rad);
                float thick = Mathf.Max(0.5f, top - y);
                int n = Mathf.Max(3, Mathf.RoundToInt(budget * (thick / lift)));
                for (int k = 1; k <= n; k++)
                {
                    float f = (float)k / n;
                    stair.Add(new Vector2(x + (thick * f) / effTan, y + thick * f));
                }
                x += thick / effTan;
                y = top;
                if (hard > 0.6f)
                {
                    x += Mathf.Lerp(2f, 16f, (hard - 0.6f) / 0.4f);
                    stair.Add(new Vector2(x, y + 0.02f));
                }
            }

            float totalH = Mathf.Max(1f, stair[stair.Count - 1].y - stair[0].y);
            var outp = new List<Vector3>(stair.Count + 16);

            // ---- cone de detrito, do chão até à base da parede
            //
            // O detrito tem de começar ONDE A PAREDE ACABA. A camada mais mole (Chinle, dureza 0,15)
            // recua uns 39 m com a erosão por omissão; se o detrito ficasse a menos do que isso, a
            // parede passaria para trás do cone e a malha auto-intersectava.
            float maxErode = erosion.Amount * Mathf.Pow(1f - MinHardness(layers), 1.6f) * 1.8f;
            float talusBase = 0f;
            if (talusHeight > 0.5f)
            {
                float ext = Mathf.Max(talusExtent, maxErode + 2f);
                int segs = Mathf.Clamp((int)(talusHeight / 1.5f), 4, 28);
                float run = Mathf.Max(1f, ext - clearHalfWidth);
                for (int k = 0; k <= segs; k++)
                {
                    float t = (float)k / segs;                          // 0 = ponta do detrito, 1 = base da parede
                    // O cone sobe EM DIREÇÃO à parede: 0 no corredor, talusHeight no pé da parede.
                    // Expoente 0,85: um cone de talus é quase reto, com uma leve convexidade.
                    // (A primeira versão tinha o expoente ao contrário e desenhava uma ponta de
                    // seta virada ao contrário, com um pico a meio e um precipício antes da parede.)
                    float hh = talusHeight * Mathf.Pow(1f - t, 0.85f);
                    float hx = clearHalfWidth + run * t;
                    // irregularidade do cone, mais forte junto à parede e sempre fora da zona livre
                    float bumpy = (Noise3(new Vector3(along * 0.05f, hh * 0.20f, 0f), 909) - 0.5f) * 2f;
                    hx = Mathf.Max(clearHalfWidth, hx + bumpy * 1.2f * t);
                    outp.Add(new Vector3(baseHeight + hh, hx, 0f));     // z preenchido depois
                    // Detrito: material SOLTO, logo classe de cascalho (0,375 → grip 0,72) e as
                    // camadas de pedra desfeita. Antes herdava a camada do topo da parede, o que o
                    // fazia ler como rocha firme e não como entulho.
                    colors.Add(ClassColor(0.375f, LayerMoenkopiClaro, LayerChinleCinza, 0f));
                }
                talusBase = ext;
            }
            else
            {
                outp.Add(new Vector3(baseHeight, 0f, 0f));
                colors.Add(ClassColor(0.375f, LayerMoenkopiClaro, LayerChinleCinza, 0f));
            }

            for (int i = 0; i < stair.Count; i++)
            {
                float hard = HardnessAt(stair[i].y, layers, baseHeight);
                float wallU = (stair[i].y - stair[0].y) / totalH;
                float blend = LayerBlend(stair[i].y, layers);
                float rec = Erode3D(stair[i].y - baseHeight, along, wallU, hard, erosion, blend);
                outp.Add(new Vector3(stair[i].y, stair[i].x + rec + talusBase, 0f));
                // Parede: cor pela dureza da camada atravessada, como no gerador do Blender — uma
                // camada mole lê como tom de Chinle, uma dura como arenito claro. Dá leitura às
                // faixas sem trabalho extra.
                colors.Add(WallLayerColor(hard));
            }

            // Monotonicidade: o perfil só pode recuar. Nas fronteiras de camada a erosão é
            // descontínua (a mole recua mais que a dura), o que fazia a distância lateral CAIR —
            // por exemplo 13 m em Organ Rock -> White Rim — e a malha auto-intersectava. Forçar o
            // máximo acumulado transforma esse degrau numa parede vertical, que é como a geologia
            // se comporta: uma cornija sobre uma camada mole.
            //
            // Nota de eixos: nesta lista o Vector3 guarda (x = ALTURA, y = distância lateral).
            for (int i = 1; i < outp.Count; i++)
            {
                float prevLat = outp[i - 1].y;
                if (outp[i].y < prevLat)
                    outp[i] = new Vector3(outp[i].x, prevLat, 0f);
            }
            return outp;
        }

        static float MinHardness((float y, float hardness)[] layers)
        {
            float m = 1f;
            for (int i = 0; i < layers.Length; i++) m = Mathf.Min(m, layers[i].hardness);
            return m;
        }

        /// <summary>
        /// Cor de uma camada da parede a partir da sua dureza, usando as camadas reais da paleta:
        /// mole (Chinle, Organ Rock) → tons escuros; dura (Wingate, White Rim, Entrada) → arenito
        /// claro. Classe 0,75 = falésia, que é o que a parede é.
        /// </summary>
        static Color WallLayerColor(float hardness)
        {
            float h = Mathf.Clamp01(hardness);
            int a, b;
            if (h < 0.30f) { a = LayerOrganRock; b = LayerChinleVermelho; }        // muito mole
            else if (h < 0.50f) { a = LayerMoenkopi; b = LayerChinleCinza; }       // mole
            else if (h < 0.70f) { a = LayerKayenta; b = LayerMossBack; }           // média
            else if (h < 0.90f) { a = LayerNavajo; b = LayerNavajoRosado; }        // dura
            else { a = LayerWingate; b = LayerWhiteRim; }                          // muito dura
            return ClassColor(0.75f, a, b, 0f);
        }

        /// <summary>
        /// Parede de canyon com perfil estratificado, erosão 3D e cone de detrito no pé,
        /// para os testes de wall-ride.
        ///
        /// <paramref name="layers"/> é (topo em y, dureza 0..1) de baixo para cima, na mesma ordem e
        /// com os mesmos valores que <c>LAYERS_RDD</c> do Blender, para o laboratório e a pista
        /// partilharem a mesma linguagem geológica.
        ///
        /// <paramref name="clearHalfWidth"/> é a meia-largura do corredor que fica garantidamente
        /// livre: o detrito começa fora dela.
        /// </summary>
        public static Mesh WallProfile(string name, float length, float baseHeight,
                                       (float y, float hardness)[] layers, float angleDeg,
                                       ErosionStyle erosion, float alongOffset = 0f,
                                       int alongSamples = 26, int heightSamples = 56,
                                       MeshStyle? style = null,
                                       float talusHeight = 0f, float talusExtent = 0f,
                                       float clearHalfWidth = 15f)
        {
            var st = style ?? MeshStyle.Reference;
            var verts = new List<Vector3>();
            var tris = new List<int>();
            var cols = new List<Color>();

            for (int s = 0; s <= alongSamples; s++)
            {
                float along = alongOffset + length * s / alongSamples;
                float z = length * (float)s / alongSamples;
                var stationCols = new List<Color>();
                var prof = WallProfilePoints(baseHeight, layers, heightSamples, erosion,
                                             along, talusHeight, talusExtent, clearHalfWidth, stationCols);
                for (int p = 0; p < prof.Count; p++)
                {
                    verts.Add(new Vector3(prof[p].x, prof[p].y, z));
                    cols.Add(stationCols[p]);
                }
            }

            if (alongSamples < 1) return Finish(new Mesh { name = name }, verts.ToArray(), tris.ToArray(), st);
            int stride = verts.Count / (alongSamples + 1);
            for (int s = 0; s < alongSamples; s++)
                for (int p = 0; p < stride - 1; p++)
                {
                    int a = s * stride + p, b = a + 1, c = a + stride + 1, d = a + stride;
                    tris.AddRange(new[] { a, b, c, a, c, d });
                }

            // UVs: U ao longo da parede (metros / 12), V vertical — necessárias para texturas de
            // detalhe (normal map). O laboratório não tinha UVs nenhumas.
            var uv = new Vector2[verts.Count];
            int total = verts.Count;
            var minY = float.MaxValue; var maxY = float.MinValue;
            for (int i = 0; i < total; i++) { minY = Mathf.Min(minY, verts[i].y); maxY = Mathf.Max(maxY, verts[i].y); }
            float ySpan = Mathf.Max(1f, maxY - minY);
            for (int i = 0; i < total; i++)
                uv[i] = new Vector2(verts[i].z / 12f, (verts[i].y - minY) / ySpan * (ySpan / 12f));

            return Finish(new Mesh { name = name }, verts.ToArray(), tris.ToArray(), st, uv, cols.ToArray());
        }

        /// <summary>Onde a elevação está dentro da sua camada: 0 no centro, 0,5 na fronteira.</summary>
        static float LayerBlend(float y, (float y, float hardness)[] layers)
        {
            float bot = 0f;
            for (int i = 0; i < layers.Length; i++)
            {
                if (y <= layers[i].y)
                {
                    float top = layers[i].y;
                    if (top - bot < 1e-3f) return 0f;
                    float f = Mathf.Clamp01((y - bot) / (top - bot));
                    return Mathf.Min(f, 1f - f);            // 0 no centro, 0.5 nas bordas
                }
                bot = layers[i].y;
            }
            return 0f;
        }

        static float HardnessAt(float y, (float y, float hardness)[] layers, float baseHeight)
        {
            for (int i = 0; i < layers.Length; i++)
                if (y <= layers[i].y) return layers[i].hardness;
            return layers.Length > 0 ? layers[layers.Length - 1].hardness : 0.6f;
        }

        /// <summary>
        /// As onze camadas de RED DUST DIVIDE, com a mesma ordem e durezas de <c>LAYERS_RDD</c>
        /// (rdd_geology.py). Só a elevação do topo e a dureza interessam ao perfil de parede.
        /// </summary>
        public static (float y, float hardness)[] RedDustLayers(float baseHeight = 0f)
        {
            // nome, espessura, dureza  (LAYERS_RDD)
            var src = new (string name, float thick, float hard)[]
            {
                ("Organ Rock", 200f, 0.30f),
                ("White Rim",   40f, 0.95f),
                ("Moenkopi",    65f, 0.45f),
                ("Moss Back",   15f, 0.90f),
                ("Chinle",      45f, 0.15f),
                ("Wingate",    100f, 0.97f),
                ("Kayenta",     35f, 0.65f),
                ("Navajo",      60f, 0.85f),
                ("Carmel",      20f, 0.25f),
                ("Entrada",     80f, 0.92f),
                ("Summerville", 60f, 0.30f),
            };
            var outp = new (float y, float hardness)[src.Length];
            float y = baseHeight;
            for (int i = 0; i < src.Length; i++)
            {
                y += src[i].thick;
                outp[i] = (y, src[i].hard);
            }
            return outp;
        }
    }
}
