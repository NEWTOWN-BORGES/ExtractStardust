using System;
using System.Collections.Generic;
using RedDust.Track;
using RedDust.Vehicle;

namespace RedDust.AI
{
    /// <summary>
    /// Piloto sobre o grafo de percursos: segue a linha do percurso atual (LineFollower) e, em cada bifurcação,
    /// decide se toma o ramo (chooseBranch). No fim do ramo volta ao principal. A distância de corrida
    /// (RaceDistance) é sempre medida no principal, para posições, checkpoints e chegada.
    /// </summary>
    public sealed class RouteFollower
    {
        public readonly LineFollower line = new LineFollower();
        public readonly CourseGraph graph;
        /// <summary>Em cada bifurcação: true = toma o ramo. Por omissão fica no principal.</summary>
        public Func<CoursePath, bool> chooseBranch = _ => false;

        public int PathIndex { get; private set; }
        public CoursePath Path => graph.Paths[PathIndex];
        public CourseData Data => Path.Data;
        public float RaceDistance => Path.ToRaceDistance(line.Distance);
        public int Station => line.Station;
        public float Distance => line.Distance;

        readonly HashSet<int> decided = new HashSet<int>();

        public RouteFollower(CourseGraph graph) { this.graph = graph; }

        public void Reset(int path, float lane)
        {
            PathIndex = Math.Max(0, Math.Min(path, graph.Paths.Length - 1));
            decided.Clear();
            line.Reset(lane);
            line.obstacles = graph.Obstacles(PathIndex);
        }

        public CraftInput Drive(CraftController c, float dt)
        {
            if (line.Station >= 0)
            {
                float look = line.LookAhead(c.Speed);
                if (Path.IsMain)
                {
                    foreach (var b in graph.Paths)
                    {
                        if (b.IsMain || decided.Contains(b.Index)) continue;
                        if (line.Distance + look < b.From || line.Distance > b.From + 30f) continue;
                        decided.Add(b.Index);
                        if (chooseBranch(b)) { PathIndex = b.Index; line.Rebase(); line.obstacles = graph.Obstacles(PathIndex); break; }
                    }
                }
                else if (line.Distance + look >= Path.Data.Length - 1f)
                {
                    PathIndex = Path.Parent;
                    line.Rebase();
                    line.obstacles = graph.Obstacles(PathIndex);
                }
            }
            return line.Drive(c, Path.Data, dt);
        }
    }
}
