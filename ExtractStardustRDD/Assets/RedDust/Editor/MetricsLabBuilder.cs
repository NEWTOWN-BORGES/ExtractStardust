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
{
    /// <summary>
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

        [MenuItem("Red Dust/9. Gerar Metrics Lab (V2)")]
        public static void Build()
        {
            var zones = Layout();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            var root = new GameObject("MetricsLab");
            foreach (var z in zones) BuildZone(root.transform, z);

            var dir = Path.GetDirectoryName(ScenePath);
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
            EditorSceneManager.SaveScene(scene, ScenePath);

            WriteManifest(zones);

            Debug.Log($"[RDD lab] cena gerada: {ScenePath} ({zones.Count} zonas)");
            if (Application.isBatchMode) EditorApplication.Exit(0);
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

            switch (z.Kind)
            {
                case ZoneKind.Flat:
                {
                    var m = LabGeometry.Flat($"{z.Name}_piso", new Vector2(z.Width, z.Length));
                    LabGeometry.Surface($"{z.Name}_piso", m).transform.SetParent(go.transform, false);
                    break;
                }

                case ZoneKind.Circle:
                {
                    // a malha do arco plano já usa o raio como eixo do percurso
                    var m = z.BankDeg <= 0.01f
                        ? LabGeometry.CircleFlat($"{z.Name}_piso", Vector3.zero, z.Radius, z.Width)
                        : LabGeometry.CircleBanked($"{z.Name}_piso", Vector3.zero, z.Radius, z.Width, z.BankDeg);
                    LabGeometry.Surface($"{z.Name}_piso", m).transform.SetParent(go.transform, false);
                    if (z.BankDeg > 0.01f)
                    {
                        // referência plana no interior, para comparação direta no mesmo raio
                        var flat = LabGeometry.CircleFlat($"{z.Name}_referenciaPlana", Vector3.zero, z.Radius, z.Width);
                        var fgo = LabGeometry.Surface($"{z.Name}_referenciaPlana", flat);
                        fgo.transform.SetParent(go.transform, false);
                        fgo.transform.localPosition = new Vector3(0f, -12f, 0f);
                    }
                    break;
                }

                case ZoneKind.HalfPipe:
                {
                    var m = LabGeometry.HalfPipe($"{z.Name}_piso", Vector3.zero, z.Radius, z.Width, z.WallDeg);
                    LabGeometry.Surface($"{z.Name}_piso", m).transform.SetParent(go.transform, false);
                    break;
                }

                case ZoneKind.Wall:
                {
                    var m = LabGeometry.Wall($"{z.Name}_parede", z.Length, 50f, z.WallDeg, out var entry, out var exit);
                    LabGeometry.Surface($"{z.Name}_parede", m).transform.SetParent(go.transform, false);
                    // piso de aproximação e de saída, para a nave chegar à parede já com velocidade
                    var ap = LabGeometry.Flat($"{z.Name}_aproximacao", new Vector2(z.Width, 260f));
                    var ago = LabGeometry.Surface($"{z.Name}_aproximacao", ap);
                    ago.transform.SetParent(go.transform, false);
                    ago.transform.localPosition = new Vector3(-130f, 0f, z.Length * 0.5f);
                    break;
                }

                case ZoneKind.Lip:
                {
                    var m = LabGeometry.Lip($"{z.Name}_labio", z.Length, z.Width, z.AngleDeg, out var top);
                    LabGeometry.Surface($"{z.Name}_labio", m).transform.SetParent(go.transform, false);
                    // rampa de aterragem a jusante, para receção legível
                    var land = LabGeometry.BankStraight($"{z.Name}_aterragem", 90f, z.Width, 0f);
                    var lgo = LabGeometry.Surface($"{z.Name}_aterragem", land);
                    lgo.transform.SetParent(go.transform, false);
                    lgo.transform.localPosition = new Vector3(0f, 0f, 60f);
                    break;
                }

                case ZoneKind.BankTransition:
                {
                    var m = LabGeometry.BankTransition($"{z.Name}_piso", z.Length, z.Width, z.FromBankDeg, z.ToBankDeg);
                    LabGeometry.Surface($"{z.Name}_piso", m).transform.SetParent(go.transform, false);
                    break;
                }

                case ZoneKind.Drop:
                {
                    // plataforma elevada + zona de aterragem plana e baixa
                    var pad = LabGeometry.Flat($"{z.Name}_plataforma", new Vector2(z.Width, z.Length));
                    var pgo = LabGeometry.Surface($"{z.Name}_plataforma", pad);
                    pgo.transform.SetParent(go.transform, false);
                    pgo.transform.localPosition = new Vector3(0f, -z.Centre.y, 0f);   // topo na cota da zona
                    var land = LabGeometry.Flat($"{z.Name}_aterragem", new Vector2(z.Width * 2f, z.Length * 2f));
                    LabGeometry.Surface($"{z.Name}_aterragem", land).transform.SetParent(go.transform, false);
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
