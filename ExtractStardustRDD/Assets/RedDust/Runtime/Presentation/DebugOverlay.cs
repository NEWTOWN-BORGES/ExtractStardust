using System.Text;
using RedDust.Track;
using RedDust.Vehicle;
using UnityEngine;
using UnityEngine.Rendering;

namespace RedDust.Presentation
{
    /// <summary>
    /// Overlay de debug (F1 / Share): velocidade, altura de hover, sensores, bank, inclinação da superfície,
    /// tempo no ar, aterragem, segmento/estação do percurso, FPS e tempos de CPU/GPU. Linhas no mundo:
    /// raios dos sensores (verde = contacto, vermelho = sem contacto), normal filtrada (azul), velocidade
    /// (amarelo) e sensor antecipado (magenta).
    /// </summary>
    public class DebugOverlay : MonoBehaviour
    {
        public CraftController craft;
        public ChaseCamera chase;
        public bool visible = true;
        public string extra;

        Material lineMat;
        readonly FrameStats stats = new FrameStats();
        readonly StringBuilder sb = new StringBuilder(512);
        GUIStyle style;
        int station = -1;

        void OnEnable() => RenderPipelineManager.endCameraRendering += DrawLines;
        void OnDisable() => RenderPipelineManager.endCameraRendering -= DrawLines;

        void Update()
        {
            stats.Tick(Time.unscaledDeltaTime);
        }

        void OnGUI()
        {
            if (!visible || craft == null) return;
            style ??= new GUIStyle(GUI.skin.label) { fontSize = Mathf.Max(13, Screen.height / 52), richText = true };
            var c = craft;
            var course = CourseRuntime.Active != null ? CourseRuntime.Active.Data : null;
            sb.Clear();
            sb.Append($"<b>{Units.ToKmh(c.Speed):0} km/h</b>   frente {Units.ToKmh(c.ForwardSpeed):0}   lateral {c.LateralSpeed:0.0} m/s\n");
            sb.Append($"hover {(float.IsInfinity(c.HoverMeasured) ? "--" : c.HoverMeasured.ToString("0.00"))} m   sensores {c.Sensor.hits}/5   {(c.Grounded ? "<color=#7f7>SOLO</color>" : $"<color=#fc6>AR {c.AirTime:0.00}s</color>")}\n");
            sb.Append($"bank nave {Vector3.Angle(c.Up, Vector3.up):0}°   superfície {c.SurfaceAngle:0}°   Δcima {c.UpRateDeg:0}°/s\n");
            sb.Append($"aterragem {c.LastLandingSpeed:0.0} m/s   impacto {c.LastImpactSpeed:0.0} m/s   {(c.Drifting ? "DERRAPAGEM " : "")}{(c.Boosting ? "BOOST" : "")}\n");
            if (course != null)
            {
                station = course.Nearest(c.Position, station);
                sb.Append($"{course.SegmentName(station)}   {course.Dist[station] / 1000f:0.00}/{course.Length / 1000f:0.00} km   u {course.LateralU(c.Position, station):0.00}\n");
            }
            if (chase != null) sb.Append($"câmera roll {chase.CameraRollDeg:0}° (nave {chase.CraftRollDeg:0}°)\n");
            sb.Append(stats.Summary);
            if (!string.IsNullOrEmpty(extra)) sb.Append('\n').Append(extra);
            GUI.color = new Color(0f, 0f, 0f, 0.55f);
            GUI.DrawTexture(new Rect(8, 8, Screen.width * 0.42f, style.fontSize * 9.6f), Texture2D.whiteTexture);
            GUI.color = Color.white;
            GUI.Label(new Rect(16, 12, Screen.width * 0.41f, style.fontSize * 9.4f), sb.ToString(), style);
        }

        void DrawLines(ScriptableRenderContext ctx, Camera cam)
        {
            if (!visible || craft == null || craft.Sensor == null) return;
            if (lineMat == null)
            {
                var src = Resources.Load<Material>("RedDust/DebugLines");
                if (src == null) return;
                lineMat = new Material(src);
            }
            lineMat.SetPass(0);
            GL.PushMatrix();
            GL.MultMatrix(Matrix4x4.identity);
            GL.Begin(GL.LINES);
            var s = craft.Sensor;
            foreach (var p in s.probes)
            {
                GL.Color(p.hit ? Color.green : Color.red);
                GL.Vertex(p.origin);
                GL.Vertex(p.hit ? p.point : p.origin - craft.Up * 8f);
            }
            Vector3 c = craft.Position;
            GL.Color(new Color(0.3f, 0.5f, 1f));
            GL.Vertex(c); GL.Vertex(c + craft.SurfaceNormal * 5f);
            GL.Color(Color.yellow);
            GL.Vertex(c); GL.Vertex(c + craft.Velocity * 0.1f);
            if (s.aheadHit)
            {
                GL.Color(Color.magenta);
                GL.Vertex(s.aheadOrigin); GL.Vertex(s.aheadPoint);
                GL.Vertex(s.aheadPoint); GL.Vertex(s.aheadPoint + s.normalAhead * 4f);
            }
            GL.End();
            GL.PopMatrix();
        }
    }

    /// <summary>FPS médio/pior e tempos de frame (FrameTimingManager quando disponível).</summary>
    public sealed class FrameStats
    {
        readonly FrameTiming[] timings = new FrameTiming[1];
        float acc, worst, cpu, gpu;
        int frames;
        public float Fps { get; private set; }
        public float WorstMs { get; private set; }
        public string Summary { get; private set; } = "";

        public void Tick(float dt)
        {
            acc += dt; frames++; worst = Mathf.Max(worst, dt);
            FrameTimingManager.CaptureFrameTimings();
            if (FrameTimingManager.GetLatestTimings(1, timings) > 0)
            {
                cpu = Mathf.Lerp(cpu, (float)timings[0].cpuFrameTime, 0.1f);
                gpu = Mathf.Lerp(gpu, (float)timings[0].gpuFrameTime, 0.1f);
            }
            if (acc >= 0.5f)
            {
                Fps = frames / acc; WorstMs = worst * 1000f;
                Summary = $"{Fps:0} fps (pior {WorstMs:0.0} ms)   CPU {cpu:0.0} ms   GPU {gpu:0.0} ms";
                acc = 0f; frames = 0; worst = 0f;
            }
        }
    }
}
