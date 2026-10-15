using RedDust.Track;
using RedDust.Vehicle;
using UnityEngine;

namespace RedDust.AI
{
    /// <summary>
    /// Seguidor de linha (pure pursuit) sobre a secção real do percurso: o alvo é um ponto à frente na
    /// coordenada lateral u (-1..1), o que permite correr no fundo, a meio ou no alto de um half-pipe/parede.
    /// Usa exatamente o mesmo CraftInput que o jogador (sem batota de velocidade). É a base da IA da M3.
    /// </summary>
    public sealed class LineFollower
    {
        public float laneU;
        public float laneResponse = 1.5f;          // 1/s: rapidez a mudar de linha
        public float lookBase = 16f;
        public float lookPerSpeed = 0.36f;
        public float steerGain = 1.0f;
        public float lateralDamping = 0.02f;
        public float speedLimit = float.PositiveInfinity;
        [Tooltip("Margem de aderência nas curvas (personalidade/dificuldade dos bots): mais alto = mais perto do limite")]
        public float cornerMargin = 0.82f;
        public bool useBoost;
        /// <summary>Obstáculos do percurso atual (pilares, rocha caída), ordenados pela distância.</summary>
        public CourseObstacle[] obstacles;
        public float obstacleMargin = 4.5f;        // m livres entre a nave e o obstáculo

        public int Station { get; private set; } = -1;
        public float Distance { get; private set; }
        public float CurrentU { get; private set; }
        float u;

        public void Reset(float lane)
        {
            laneU = lane; u = lane; Station = -1;
        }

        /// <summary>Mudança de percurso (bifurcação): mantém a linha lateral, procura de novo a estação.</summary>
        public void Rebase() => Station = -1;

        /// <summary>Distância de antecipação do alvo à velocidade v.</summary>
        public float LookAhead(float v) => lookBase + lookPerSpeed * v;

        /// <summary>
        /// Linha desejada com os obstáculos à frente contornados: se a linha passa a menos de r + margem de um pilar ou
        /// bloco, desvia para o lado livre mais próximo (dentro dos limites de corrida).
        /// </summary>
        float AvoidObstacles(CourseData course, float lane, float look)
        {
            if (obstacles == null || obstacles.Length == 0) return lane;
            float a = Distance - 6f, b = Distance + look + 140f;
            int lo = 0, hi = obstacles.Length;
            while (lo < hi) { int m = (lo + hi) >> 1; if (obstacles[m].dist < a) lo = m + 1; else hi = m; }
            float target = lane;
            for (int k = lo; k < obstacles.Length && obstacles[k].dist <= b; k++)
            {
                var o = obstacles[k];
                int st = course.StationAt(o.dist);
                float ride = Mathf.Max(6f, 0.5f * (course.RideLeft[st] + course.RideRight[st]));
                float half = (o.r + obstacleMargin) / ride;
                if (Mathf.Abs(target - o.u) >= half) continue;
                float left = o.u - half, right = o.u + half;
                bool leftOk = left > -0.95f, rightOk = right < 0.95f;
                if (leftOk && (!rightOk || Mathf.Abs(left - target) <= Mathf.Abs(right - target))) target = left;
                else if (rightOk) target = right;
            }
            return target;
        }

        public CraftInput Drive(CraftController c, CourseData course, float dt)
        {
            var input = CraftInput.Auto;
            Station = course.Nearest(c.Position, Station);
            Distance = course.DistanceAlong(c.Position, Station);
            CurrentU = course.LateralU(c.Position, Station);
            float laneTarget = AvoidObstacles(course, laneU, LookAhead(c.Speed));
            u = Mathf.MoveTowards(u, laneTarget, (laneTarget != laneU ? 3.5f : laneResponse) * dt);

            float speed = c.Speed;
            float look = LookAhead(speed);
            Vector3 target = course.LanePoint(Distance + look, u);
            Vector3 up = c.Grounded ? c.SurfaceNormal : c.Up;
            Vector3 to = Vector3.ProjectOnPlane(target - c.Position, up);
            Vector3 f = Vector3.ProjectOnPlane(c.Forward, up);
            float ang = Vector3.SignedAngle(f, to, up) * Mathf.Deg2Rad;
            // velocidade angular necessária (pure pursuit): w = 2 v sin(a) / L ; amortecer deslizamento lateral
            float w = 2f * Mathf.Max(speed, 10f) * Mathf.Sin(ang) / Mathf.Max(look, 1f);
            w -= c.LateralSpeed * lateralDamping;
            input.steer = Mathf.Clamp(steerGain * w / Mathf.Max(0.05f, c.tuning.TurnRate(speed)), -1f, 1f);

            // controlo de velocidade: curvatura à frente e limite pedido
            float kappa = course.CurvatureAhead(Distance, 60f + speed * 1.2f);
            float vCurve = c.tuning.CornerSpeed(kappa, course.Bank[Mathf.Clamp(Station, 0, course.StationCount - 1)], cornerMargin);
            float vMax = Mathf.Min(vCurve, speedLimit);
            input.throttle = speed > vMax ? 0f : 1f;
            input.brake = speed > vMax + 4f && Mathf.Abs(input.steer) < 0.3f;
            input.boost = useBoost && speed < vMax - 5f;
            return input;
        }
    }
}
