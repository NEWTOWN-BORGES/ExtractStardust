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
        public bool useBoost;

        public int Station { get; private set; } = -1;
        public float Distance { get; private set; }
        public float CurrentU { get; private set; }
        float u;

        public void Reset(float lane)
        {
            laneU = lane; u = lane; Station = -1;
        }

        public CraftInput Drive(CraftController c, CourseData course, float dt)
        {
            var input = CraftInput.Auto;
            Station = course.Nearest(c.Position, Station);
            Distance = course.DistanceAlong(c.Position, Station);
            CurrentU = course.LateralU(c.Position, Station);
            u = Mathf.MoveTowards(u, laneU, laneResponse * dt);

            float speed = c.Speed;
            float look = lookBase + lookPerSpeed * speed;
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
            float vCurve = kappa > 1e-5f ? Mathf.Sqrt(c.tuning.gripLateralMax * 0.82f / kappa) : float.PositiveInfinity;
            float vMax = Mathf.Min(vCurve, speedLimit);
            input.throttle = speed > vMax ? 0f : 1f;
            input.brake = speed > vMax + 4f && Mathf.Abs(input.steer) < 0.3f;
            input.boost = useBoost && speed < vMax - 5f;
            return input;
        }
    }
}
