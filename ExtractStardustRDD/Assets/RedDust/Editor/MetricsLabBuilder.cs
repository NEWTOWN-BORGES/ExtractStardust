using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using RedDust.Lab;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace RedDust.EditorTools
{    /// <summary>
    /// Gera a cena <b>Metrics Lab</b> da Fase 1 da V2 (tarefa 3 de RDD_V2_Plano_Fase0.md, secção I).
    ///
    /// A cena é uma grelha de zonas independentes, cada uma com um piso de referência, para medir
    /// o que a secção C do plano pede: velocidade, travagem, raio mínimo por velocidade, banking
    /// máximo, taxa de transição, saltos e quedas.
    ///
    /// Cada zona tem um comprimento de referência (o eixo do percurso) gravado no manifesto
    /// <c>Docs/V2_MetricsLab_Zonas.md</c>; o executor lê esse manifesto para saber onde colocar a
    /// nave, em vez de ter as coordenadas duplicadas no código.
    ///
    /// Uso no editor:  menu <b>Red Dust / 9. Gerar Metrics Lab (V2)</b>
    /// Uso em batch:   Unity -batchmode -executeMethod RedDust.EditorTools.MetricsLabBuilder.Build
    /// </summary>
    public static class MetricsLabBuilder
    {
        public const string ScenePath = "Assets/RedDust/Scenes/RDD_MetricsLab.unity";
        public const string ManifestPath = "Docs/V2_MetricsLab_Zonas.md";

        /// <summary>Zona do laboratório: tipo, centro no plano e parâmetros de geometria.</summary>
        public sealed class Zone
        {
            public string Name;
            public ZoneKind Kind;
            public Vector3 Centre;
            public float Radius;
            public float Width;
            public float Length;
            public float BankDeg;
            public float WallDeg;
            public float AngleDeg;
            public float FromBankDeg;
            public float ToBankDeg;
            public bool FlatFloor;          // acrescenta um piso plano por baixo (referência plana)
            public string Notes;
        }

        public enum ZoneKind
        {
            Flat,           // arranque, aceleração, travagem
            Circle,         // raio constante, com ou sem bank
            HalfPipe,       // varrimento de secção curvo
            Wall,           // wall-ride
            Lip,            // lábio de salto
            BankTransition, // taxa de mudança de bank
            Drop,           // plataforma elevada + zona de aterragem
        }

        // ------------------------------------------------------------------ comando

        static Material geo;

        /// <summary>
        /// Prepara a textura de rocha: marca-a como Normal map no importador e liga-a ao material
        /// de geologia. Feito por código para não ser preciso configurar nada à mão no Unity.
        ///
        /// O normal map cobre o que a geometria não deve resolver: abaixo de ~4 m as fissuras
        /// exigiriam ~1 M de triângulos por parede. Detalhe fino em textura mantém o jogo leve.
        /// </summary>
        public static void ConfigureRockTextures()
        {
            const string texDir = "Assets/RedDust/Materials/Textures";
            const string nmPath = texDir + "/rock_normal.png";

            var importer = AssetImporter.GetAtPath(nmPath) as TextureImporter;
            if (importer != null)
            {
                importer.textureType = TextureImporterType.NormalMap;
                importer.wrapMode = TextureWrapMode.Repeat;
                importer.filterMode = FilterMode.Bilinear;
                importer.mipmapEnabled = true;
                importer.SaveAndReimport();
                Debug.Log($"[RDD lab] {nmPath} marcado como Normal map");
            }
            else
            {
                Debug.LogWarning($"[RDD lab] normal map nao encontrado em {nmPath}");
                return;
            }

            var mat = AssetDatabase.LoadAssetAtPath<Material>($"{ProjectSetup.MaterialsDir}/Geology.mat");
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(nmPath);
            if (mat == null || tex == null)
            {
                Debug.LogWarning("[RDD lab] Geology.mat ou a textura nao existem; correr 'Red Dust/1. Setup do projeto'");
                return;
            }
            mat.SetTexture("_NormalMap", tex);
            // UVs do laboratorio estao em metros; 12 m por repeticao da textura
            mat.SetTextureScale("_NormalMap", new Vector2(1f / 12f, 1f / 12f));
            if (!mat.HasProperty("_NormalScale")) mat.SetFloat("_NormalScale", 1f);
            EditorUtility.SetDirty(mat);
            AssetDatabase.SaveAssets();
            Debug.Log("[RDD lab] normal map de rocha ligado ao Geology.mat");
        }

        [MenuItem("Red Dust/9. Gerar Metrics Lab (V2)")]
        public static void Build()
        {
            ConfigureRockTextures();
            var zones = Layout();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // Mesmo material de geologia que o CourseImporter usa nas pistas reais
            // (paleta de 14 camadas + verniz do deserto + perspetiva aérea).
            // Sem isto, as malhas ficam com o material por omissão e aparecem magenta.
            geo = AssetDatabase.LoadAssetAtPath<Material>($"{ProjectSetup.MaterialsDir}/Geology.mat");
            if (geo == null)
                Debug.LogWarning($"[RDD lab] Geology.mat nao encontrado em {ProjectSetup.MaterialsDir}; " +
                                 "correr 'Red Dust/1. Setup do projeto'. As malhas ficam sem material.");

            var root = new GameObject("MetricsLab");
            foreach (var z in zones) BuildZone(root.transform, z);

            var dir = Path.GetDirectoryName(ScenePath);
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
            EditorSceneManager.SaveScene(scene, ScenePath);

            WriteManifest(zones);

            Debug.Log($"[RDD lab] cena gerada: {ScenePath} ({zones.Count} zonas, {(geo != null ? "material de geologia" : "SEM material")})");
            if (Application.isBatchMode) EditorApplication.Exit(0);
        }

        /// <summary>Cria o objeto de superfície com o material de geologia aplicado.</summary>
        static GameObject Geo(string name, Mesh mesh) => LabGeometry.Surface(name, mesh, geo);

        /// <summary>
        /// Estilo de cada zona, ligado às camadas reais da paleta do projeto.
        ///
        /// O canal R (classe) não é decoração: é a mesma banda que <c>SurfaceTypes.FromClass</c> lê
        /// para decidir grip, topSpeed e drag. Por isso o pavimento de medição é sempre classe 0,25
        /// (slickrock, grip 1,08, drag 0) — o resultado tem de depender da nave, não do chão.
        /// A variedade visual vive nas restantes zonas, onde nada é medido.
        /// </summary>
        static LabGeometry.MeshStyle StyleFor(string name)
        {
            // pavimento de medição: slickrock claro, duro e uniforme
            if (name.StartsWith("B0")) return new LabGeometry.MeshStyle
            {
                SurfaceClass = 0.5f, LayerA = LabGeometry.LayerWhiteRim, LayerB = LabGeometry.LayerNavajo,
                RideMask = 0f, Hardness = 1f, Blend = 0.35f,
            };
            if (name.StartsWith("C0")) return new LabGeometry.MeshStyle
            {
                SurfaceClass = 0.5f, LayerA = LabGeometry.LayerNavajo, LayerB = LabGeometry.LayerNavajoRosado,
                RideMask = 0f, Hardness = 0.9f, Blend = 0.4f,
            };
            if (name.StartsWith("D0")) return new LabGeometry.MeshStyle
            {
                SurfaceClass = 0.75f, LayerA = LabGeometry.LayerWingate, LayerB = LabGeometry.LayerKayenta,
                RideMask = 0f, Hardness = 1f, Blend = 0.5f,       // falésia: a parede vermelha de verdade
            };
            if (name.StartsWith("E0")) return new LabGeometry.MeshStyle
            {
                SurfaceClass = 0.5f, LayerA = LabGeometry.LayerKayenta, LayerB = LabGeometry.LayerWingate,
                RideMask = 0f, Hardness = 0.85f, Blend = 0.45f,
            };
            if (name.StartsWith("F0")) return new LabGeometry.MeshStyle
            {
                SurfaceClass = 0.5f, LayerA = LabGeometry.LayerMossBack, LayerB = LabGeometry.LayerKayenta,
                RideMask = 0f, Hardness = 0.9f, Blend = 0.5f,
            };
            if (name.StartsWith("G0")) return new LabGeometry.MeshStyle
            {
                SurfaceClass = 0.25f, LayerA = LabGeometry.LayerChinleVermelho, LayerB = LabGeometry.LayerChinlePurpura,
                RideMask = 1f, Hardness = 0.6f, Blend = 0.55f,     // as camadas mais escuras do plateau
            };
            // A: retas de arranque, aceleração e travagem — o pavimento de referência
            return LabGeometry.MeshStyle.Reference;
        }

        // ------------------------------------------------------------------ layout

        /// <summary>
        /// Grelha de zonas. Coordenadas explícitas e afastadas entre si para nunca haver
        /// sobreposição de geometria entre testes (o defeito que o TrackProbe apanhou no mapa legado).
        /// </summary>
        public static List<Zone> Layout()
        {
            var z = new List<Zone>();
            void Add(Zone x) => z.Add(x);

            // Linha A — aceleração, travagem e bank reto (eixo +Z), a oeste da origem
            Add(new Zone
            {
                Name = "A01_Arranque_Aceleracao", Kind = ZoneKind.Flat,
                Centre = new Vector3(-400f, 0f, 2100f), Width = 60f, Length = 4000f,
                Notes = "Reta plana de 4 km: 0→300 km/h, velocidade máxima com e sem boost, velocidade média.",
            });
            Add(new Zone
            {
                Name = "A02_Corredor_Travagem", Kind = ZoneKind.Flat,
                Centre = new Vector3(-250f, 0f, 600f), Width = 40f, Length = 1200f,
                Notes = "Travagem 400→250 km/h e distância de paragem.",
            });

            // Linha B — curvas à velocidade (leste da origem)
            Add(Circle("B01_Raio060_Bank25", new Vector3(1200f, 0f, 1400f), 60f, 30f, 25f,
                "Velocidade máxima estável com aderência e com derrapagem."));
            Add(Circle("B02_Raio120_Bank35", new Vector3(1600f, 0f, 1800f), 120f, 34f, 35f,
                "Aceleração lateral máxima (g) e raio mínimo por velocidade."));
            Add(Circle("B03_Raio250_Bank45", new Vector3(2100f, 0f, 2400f), 250f, 40f, 45f,
                "Banking sustentável e ângulo máximo antes de perder contacto."));
            Add(Circle("B04_Raio500_Bank55", new Vector3(3100f, 0f, 1500f), 500f, 44f, 55f,
                "Velocidade máxima estável com bank alto."));
            Add(Circle("B05_Raio060_Plano", new Vector3(900f, 0f, 2400f), 60f, 30f, 0f,
                "Referência PLANa no mesmo raio: mede exatamente o ganho que o bank dá."));

            // Linha C — half-pipes
            Add(new Zone
            {
                Name = "C01_HalfPipe_Largo", Kind = ZoneKind.HalfPipe,
                Centre = new Vector3(-1200f, 0f, 1000f), Radius = 180f, Width = 40f, WallDeg = 45f,
                Notes = "Half-pipe largo a 45°: percurso a 3 alturas, contacto e erro de linha.",
            });
            Add(new Zone
            {
                Name = "C02_HalfPipe_Apertado", Kind = ZoneKind.HalfPipe,
                Centre = new Vector3(-1200f, 0f, 2400f), Radius = 90f, Width = 24f, WallDeg = 60f,
                Notes = "Half-pipe apertado a 60°: velocidade mínima para aguentar a parede.",
            });

            // Linha D — wall rides
            Add(WallZone("D01_Wall45", new Vector3(-2000f, 0f, 700f), 45f));
            Add(WallZone("D02_Wall55", new Vector3(-2000f, 0f, 1100f), 55f));
            Add(WallZone("D03_Wall65", new Vector3(-2000f, 0f, 1500f), 65f));

            // Linha E — transições de bank
            Add(new Zone
            {
                Name = "E01_Transicao_0a30", Kind = ZoneKind.BankTransition,
                Centre = new Vector3(-600f, 0f, -600f), Width = 34f, Length = 400f,
                FromBankDeg = 0f, ToBankDeg = 30f,
                Notes = "Taxa de transição (°/m): 30° em 400 m.",
            });
            Add(new Zone
            {
                Name = "E02_Transicao_0a50", Kind = ZoneKind.BankTransition,
                Centre = new Vector3(-600f, 0f, -1100f), Width = 34f, Length = 400f,
                FromBankDeg = 0f, ToBankDeg = 50f,
                Notes = "Taxa de transição (°/m): 50° em 400 m (mais agressiva).",
            });

            // Linha F — saltos: lábio, vão e rampa de aterragem
            Add(new Zone
            {
                Name = "F01_Salto_7deg", Kind = ZoneKind.Lip,
                Centre = new Vector3(500f, 0f, -500f), Width = 30f, Length = 40f, AngleDeg = 7f,
                Notes = "Flow jump: lábio natural de 7°, mede altura e tempo no ar.",
            });
            Add(new Zone
            {
                Name = "F02_Salto_15deg", Kind = ZoneKind.Lip,
                Centre = new Vector3(500f, 0f, -1100f), Width = 30f, Length = 46f, AngleDeg = 15f,
                Notes = "Salto médio: distância e velocidade de aterragem.",
            });
            Add(new Zone
            {
                Name = "F03_Salto_25deg", Kind = ZoneKind.Lip,
                Centre = new Vector3(500f, 0f, -1700f), Width = 30f, Length = 52f, AngleDeg = 25f,
                Notes = "Salto máximo: velocidade de aterragem que provoca dano (landingHard = 17 m/s).",
            });

            // Linha G — quedas
            for (int i = 0; i < 4; i++)
            {
                float h = 5f + i * 10f;
                Add(new Zone
                {
                    Name = $"G{i + 1:00}_Queda_{h:0}m", Kind = ZoneKind.Drop,
                    Centre = new Vector3(1900f, h, -400f - i * 400f), Width = 40f, Length = 60f,
                    Notes = $"Plataforma a {h:0} m acima de uma zona de aterragem plana: altura máxima sem dano.",
                });
            }

            return z;
        }

        static Zone Circle(string name, Vector3 c, float radius, float width, float bank, string notes) => new Zone
        {
            Name = name, Kind = ZoneKind.Circle, Centre = c, Radius = radius, Width = width,
            BankDeg = bank, Notes = notes,
        };

        static Zone WallZone(string name, Vector3 c, float angle) => new Zone
        {
            Name = name, Kind = ZoneKind.Wall, Centre = c, Length = 220f, Width = 40f,
            WallDeg = angle, AngleDeg = angle,
            Notes = $"Wall ride a {angle:0}°: segundos em contacto acima da velocidade mínima, e queda previsível abaixo dela.",
        };

        // ------------------------------------------------------------------ construção

        static void BuildZone(Transform parent, Zone z)
        {
            var go = new GameObject(z.Name);
            go.transform.SetParent(parent, false);
            go.transform.position = z.Centre;

            var st = StyleFor(z.Name);

            switch (z.Kind)
            {
                case ZoneKind.Flat:
                {
                    var m = LabGeometry.Flat($"{z.Name}_piso", new Vector2(z.Width, z.Length), st);
                    Geo($"{z.Name}_piso", m).transform.SetParent(go.transform, false);
                    break;
                }

                case ZoneKind.Circle:
                {
                    // a malha do arco plano já usa o raio como eixo do percurso
                    var m = z.BankDeg <= 0.01f
                        ? LabGeometry.CircleFlat($"{z.Name}_piso", Vector3.zero, z.Radius, z.Width, 96, st)
                        : LabGeometry.CircleBanked($"{z.Name}_piso", Vector3.zero, z.Radius, z.Width, z.BankDeg, 128, st);
                    Geo($"{z.Name}_piso", m).transform.SetParent(go.transform, false);
                    if (z.BankDeg > 0.01f)
                    {
                        // referência plana no interior, para comparação direta no mesmo raio
                        var flat = LabGeometry.CircleFlat($"{z.Name}_referenciaPlana", Vector3.zero, z.Radius, z.Width, 96, st);
                        var fgo = Geo($"{z.Name}_referenciaPlana", flat);
                        fgo.transform.SetParent(go.transform, false);
                        fgo.transform.localPosition = new Vector3(0f, -12f, 0f);
                    }
                    break;
                }

                case ZoneKind.HalfPipe:
                {
                    var m = LabGeometry.HalfPipe($"{z.Name}_piso", Vector3.zero, z.Radius, z.Width, z.WallDeg, 128, 14, st);
                    Geo($"{z.Name}_piso", m).transform.SetParent(go.transform, false);
                    break;
                }

                case ZoneKind.Wall:
                {
                    // Paredes de canyon com perfil estratificado e EROSÃO (LabGeometry.WallProfile):
                    // as onze camadas de LAYERS_RDD, com o recuo dependente da dureza de cada uma.
                    // É o mesmo algoritmo proposto para o gerador do Blender, aqui já executável em C#.
                    var layers = LabGeometry.RedDustLayers(0f);
                    var erosion = LabGeometry.ErosionStyle.Default;
                    const float wallHeight = 330f;

                    // Densidade: o campo de erosão 3D tem detalhe até ~1 m. A estação tem de ser mais
                    // fina do que o detalhe mais fino, senão as rachaduras caem entre vértices:
                    //   ao longo : 0,5 m  (440 amostras em 220 m)
                    //   em altura: 1,5 m  (220 amostras em 330 m)
                    // A malha fica com ~97 mil vértices por parede, que é o custo de ter erosão real.
                    const int along = 440;
                    const int height = 220;

                    // parede do lado +X, com a face virada para -X (onde a nave corre)
                    // O detrito (cone de talus) assenta no pé a partir de 16 m do eixo, para a largura
                    // útil do corredor não diminuir — é meia-largura livre de 15 m.
                    var mR = LabGeometry.WallProfile($"{z.Name}_paredeR", z.Length, 0f, layers,
                        z.WallDeg, erosion, 0f, along, height, st,
                        talusHeight: 14f, talusExtent: 22f, clearHalfWidth: 15f);
                    var wR = Geo($"{z.Name}_paredeR", mR);
                    wR.transform.SetParent(go.transform, false);
                    wR.transform.localRotation = Quaternion.Euler(0f, -90f, 0f);
                    wR.transform.localPosition = new Vector3(wallHeight * 0.5f, 0f, -z.Length * 0.5f);

                    // parede oposta, fechando o corredor (deslocamento de erosão diferente, para
                    // as duas paredes não saírem iguais)
                    var mL = LabGeometry.WallProfile($"{z.Name}_paredeL", z.Length, 0f, layers,
                        z.WallDeg, erosion, 137f, along, height, st,
                        talusHeight: 11f, talusExtent: 19f, clearHalfWidth: 15f);
                    var wL = Geo($"{z.Name}_paredeL", mL);
                    wL.transform.SetParent(go.transform, false);
                    wL.transform.localRotation = Quaternion.Euler(0f, 90f, 0f);
                    wL.transform.localPosition = new Vector3(-wallHeight * 0.5f, 0f, z.Length * 0.5f);

                    // piso do corredor, para a nave chegar à parede já com velocidade
                    var ap = LabGeometry.Flat($"{z.Name}_aproximacao", new Vector2(40f, z.Length), st);
                    var ago = Geo($"{z.Name}_aproximacao", ap);
                    ago.transform.SetParent(go.transform, false);
                    ago.transform.localRotation = Quaternion.Euler(0f, 90f, 0f);
                    break;
                }

                case ZoneKind.Lip:
                {
                    var m = LabGeometry.Lip($"{z.Name}_labio", z.Length, z.Width, z.AngleDeg, out var top, st);
                    Geo($"{z.Name}_labio", m).transform.SetParent(go.transform, false);
                    // rampa de aterragem a jusante, para receção legível
                    var land = LabGeometry.BankStraight($"{z.Name}_aterragem", 90f, z.Width, 0f, st);
                    var lgo = Geo($"{z.Name}_aterragem", land);
                    lgo.transform.SetParent(go.transform, false);
                    lgo.transform.localPosition = new Vector3(0f, 0f, 60f);
                    break;
                }

                case ZoneKind.BankTransition:
                {
                    var m = LabGeometry.BankTransition($"{z.Name}_piso", z.Length, z.Width, z.FromBankDeg, z.ToBankDeg, 64, st);
                    Geo($"{z.Name}_piso", m).transform.SetParent(go.transform, false);
                    break;
                }

                case ZoneKind.Drop:
                {
                    // plataforma elevada + zona de aterragem plana e baixa
                    var pad = LabGeometry.Flat($"{z.Name}_plataforma", new Vector2(z.Width, z.Length), st);
                    var pgo = Geo($"{z.Name}_plataforma", pad);
                    pgo.transform.SetParent(go.transform, false);
                    pgo.transform.localPosition = new Vector3(0f, -z.Centre.y, 0f);   // topo na cota da zona
                    var land = LabGeometry.Flat($"{z.Name}_aterragem", new Vector2(z.Width * 2f, z.Length * 2f), st);
                    Geo($"{z.Name}_aterragem", land).transform.SetParent(go.transform, false);
                    break;
                }
            }
        }

        // ------------------------------------------------------------------ manifesto

        /// <summary>
        /// Grava a lista de zonas com o comprimento de referência de cada uma. O executor lê daqui
        /// as coordenadas, para não haver duas fontes de verdade.
        /// </summary>
        static void WriteManifest(List<Zone> zones)
        {
            var dir = Path.GetDirectoryName(ManifestPath);
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);

            var sb = new StringBuilder();
            sb.AppendLine("# Metrics Lab — zonas geradas");
            sb.AppendLine();
            sb.AppendLine("Gerado por `RedDust.EditorTools.MetricsLabBuilder`. Não editar à mão.");
            sb.AppendLine();
            sb.AppendLine("Cada zona é independente e tem um piso de referência **Slickrock**");
            sb.AppendLine("(grip 1,08 · topSpeed 1,03 · drag 0), para que as medições dependam da nave");
            sb.AppendLine("e não do chão. Ver `LabGeometry` para a razão de isto ser obrigatório.");
            sb.AppendLine();
            sb.AppendLine("Cena: `" + ScenePath + "`");
            sb.AppendLine();
            sb.AppendLine("| Zona | Tipo | Centro (x, y, z) | Raio | Largura | Comprimento | Bank | Parede | Ângulo | Notas |");
            sb.AppendLine("|---|---|---|---|---|---|---|---|---|---|");
            var ci = CultureInfo.InvariantCulture;
            foreach (var z in zones)
            {
                sb.AppendLine(string.Format(ci,
                    "| {0} | {1} | {2:0}, {3:0}, {4:0} | {5} | {6} | {7} | {8} | {9} | {10} | {11} |",
                    z.Name, z.Kind, z.Centre.x, z.Centre.y, z.Centre.z,
                    Num(z.Radius), Num(z.Width), Num(z.Length),
                    Num(z.BankDeg), Num(z.WallDeg), Num(z.AngleDeg), z.Notes));
            }
            sb.AppendLine();
            sb.AppendLine("## O que falta medir nesta cena");
            sb.AppendLine();
            sb.AppendLine("As 8 famílias de métricas da secção C do plano são recolhidas pelo executor:");
            sb.AppendLine();
            sb.AppendLine("```");
            sb.AppendLine("Unity -batchmode -projectPath . -executeMethod RedDust.EditorTools.MetricsLabRunner.Run -metricsDir Temp/Metrics");
            sb.AppendLine("```");
            sb.AppendLine();
            sb.AppendLine("Escreve um CSV por chassis em `Temp/Metrics/`.");
            File.WriteAllText(ManifestPath, sb.ToString());
            AssetDatabase.Refresh();
            Debug.Log($"[RDD lab] manifesto: {ManifestPath}");
        }

        static string Num(float v) => Mathf.Approximately(v, 0f) ? "—" : v.ToString("0.##", CultureInfo.InvariantCulture);
    }
}
