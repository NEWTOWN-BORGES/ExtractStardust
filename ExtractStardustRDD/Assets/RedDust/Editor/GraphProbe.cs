using System.Text;
using RedDust.Track;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace RedDust.EditorTools
{
    /// <summary>Diagnóstico: raios verticais ao longo de um ramo (args: -probePath N -probeFrom D -probeTo D -probeU U).</summary>
    public static class GraphProbe
    {
        public static void Run()
        {
            EditorSceneManager.OpenScene(CourseImporter.ScenePathFor(CourseImporter.CourseArg));
            var g = Object.FindFirstObjectByType<CourseRuntime>().Graph;
            var p = g.Paths[CommandLine.Int("-probePath", 2)];
            float a = CommandLine.Float("-probeFrom", 16200f), b = CommandLine.Float("-probeTo", 16290f), u = CommandLine.Float("-probeU", -0.6f);
            var d = p.Data;
            var sb = new StringBuilder($"[RDD probe] {p.Id} u={u}\n");
            for (int s = d.StationAt(a); s <= d.StationAt(b); s++)
            {
                Vector3 lp = d.LanePoint(s, u);
                sb.Append($"{d.Dist[s]:0} lane y {lp.y:0.0}: ");
                Vector3 o = lp + Vector3.up * 25f;
                foreach (var h in Physics.RaycastAll(o, Vector3.down, 70f, Layers.GroundMask))
                    sb.Append($"[{h.collider.name} y {h.point.y:0.0} n.y {h.normal.y:0.00}] ");
                sb.Append('\n');
            }
            Debug.Log(sb.ToString());
            if (Application.isBatchMode) EditorApplication.Exit(0);
        }
    }
}
