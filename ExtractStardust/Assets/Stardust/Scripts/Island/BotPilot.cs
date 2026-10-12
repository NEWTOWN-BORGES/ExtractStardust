using System.Collections.Generic;
using UnityEngine;

namespace Stardust
{
    /// <summary>
    /// Route-following pilot (port of podracer.gd _autopilot + _avoid): steers to a point ahead on its route,
    /// dodges solid obstacles and other ships with forward rays, pulls the handbrake before curves tighter than
    /// the ship can turn and uses nitro on straights. Skill/aggression vary per bot (mistakes, late braking).
    /// </summary>
    public class BotPilot
    {
        public Vector3[] route;
        float[] kappa;
        public int index;
        public float skill = 1f;        // 0.6 rookie .. 1 perfect
        public float aggression = 0.5f;
        public float lineOffset;        // preferred lateral offset on the road (m)
        public bool neverErr;
        readonly System.Random rng;
        float errT, errSteer, errClock;
        float nitroHold;
        public List<Hovercraft> others;   // ships to avoid
        public Hovercraft self;

        public BotPilot(int seed) { rng = new System.Random(seed); errClock = 3f + (float)rng.NextDouble() * 10f; }

        bool[] jumpZone;
        public float dbgLat, dbgDiff; public bool dbgSlow, dbgDrift;                  // approach of a jump: full speed, straight, no braking

        float[] halfWidth;               // road half width at each route point

        public void SetRoute(Vector3[] r, List<int> jumps = null, List<float> hws = null)
        {
            route = r;
            index = 0;
            halfWidth = new float[r.Length];
            for (int i = 0; i < r.Length; i++) halfWidth[i] = hws != null && i < hws.Count ? hws[i] : 30f;
            jumpZone = new bool[r.Length];
            if (jumps != null)
                foreach (int l in jumps)
                    for (int i = Mathf.Max(0, l - 16); i <= Mathf.Min(r.Length - 1, l + 3); i++) jumpZone[i] = true;
            kappa = new float[r.Length];
            for (int i = 0; i < r.Length; i++)
            {
                var a = r[Mathf.Max(i - 2, 0)];
                var b = r[i];
                var c = r[Mathf.Min(i + 2, r.Length - 1)];
                var d1 = new Vector2(b.x - a.x, b.z - a.z);
                var d2 = new Vector2(c.x - b.x, c.z - b.z);
                float ds = (d1.magnitude + d2.magnitude) * 0.5f;
                kappa[i] = d1.magnitude > 0.01f && d2.magnitude > 0.01f ? Mathf.Abs(Vector2.SignedAngle(d1, d2)) * Mathf.Deg2Rad / Mathf.Max(ds, 0.1f) : 0f;
            }
        }

        /// <summary>Nearest route point, searched first around the current one (laps repeat the same points).</summary>
        public int Nearest(Vector3 p)
        {
            if (route == null || route.Length == 0) return 0;
            int best = Scan(p, Mathf.Max(index - 150, 0), Mathf.Min(index + 600, route.Length));
            var r = route[best];
            if (new Vector2(r.x - p.x, r.z - p.z).magnitude > 150f) best = Scan(p, 0, route.Length);
            return best;
        }

        int Scan(Vector3 p, int a, int b)
        {
            int best = a;
            float bd = float.MaxValue;
            for (int i = a; i < b; i++)
            {
                var r = route[i];
                // height counts more: never snap to a route on another level (rim above, tunnel below)
                float d = (r.x - p.x) * (r.x - p.x) + (r.z - p.z) * (r.z - p.z) + 6f * (r.y - p.y) * (r.y - p.y);
                if (d < bd) { bd = d; best = i; }
            }
            return best;
        }

        public void Resync() { index = Nearest(self.position); }

        public float Kappa(int i) => kappa == null || kappa.Length == 0 ? 0f : kappa[Mathf.Clamp(i, 0, kappa.Length - 1)];

        /// <summary>Fraction of the route done (0..1) for ordering.</summary>
        public float Progress => route == null || route.Length < 2 ? 0f : index / (float)(route.Length - 1);

        float Avoid(Hovercraft s, float v)
        {
            var fwd = s.Forward;
            var right = s.Right;
            float reach = 30f + v * 1f;
            float push = 0f;
            foreach (float off in new[] { -8f, -3f, 3f, 8f })
            {
                var from = s.position + Vector3.up * 1.3f + right * off;
                if (!Physics.Raycast(from, fwd, out var hit, reach, IslandWorld.SolidMask, QueryTriggerInteraction.Ignore)) continue;
                if (hit.collider is TerrainCollider && hit.normal.y > 0.6f) continue;   // a slope is not a wall
                float lat = Vector3.Dot(hit.point - s.position, right);
                float k = 1f - hit.distance / reach;
                push += (lat > 0f ? -1f : 1f) * (0.6f + 1.6f * k);
            }
            // other ships: steer around the ones just ahead
            if (others != null)
                foreach (var o in others)
                {
                    if (o == s) continue;
                    var d = o.position - s.position;
                    float ahead = Vector3.Dot(d, fwd);
                    if (ahead < 2f || ahead > 25f + v * 0.35f) continue;
                    float lat = Vector3.Dot(d, right);
                    if (Mathf.Abs(lat) > 7f || Mathf.Abs(d.y) > 4f) continue;
                    float closing = v - Vector3.Dot(o.vel, fwd);
                    if (closing < 2f) continue;
                    push += (lat > 0f ? -1f : 1f) * (0.5f + 0.8f * (1f - ahead / 60f)) * (0.6f + aggression * 0.4f);
                }
            return Mathf.Clamp(push, -2f, 2f);
        }

        public ShipControls Drive(Hovercraft s, float dt)
        {
            var c = new ShipControls();
            if (route == null || route.Length == 0) return c;
            var p = s.position;
            for (int k = 0; k < 40; k++)
            {
                int n = Mathf.Min(index + 1, route.Length - 1);
                var r0 = route[index];
                var r1 = route[n];
                if (n != index && new Vector2(r1.x - p.x, r1.z - p.z).magnitude <= new Vector2(r0.x - p.x, r0.z - p.z).magnitude + 0.5f) index = n;
                else break;
            }
            // lost the route (respawn, big detour)
            var cur = route[index];
            if (new Vector2(cur.x - p.x, cur.z - p.z).sqrMagnitude > 200f * 200f) index = Nearest(p);

            float v = s.Speed;
            bool jz = jumpZone != null && jumpZone.Length == route.Length && jumpZone[index];
            int ahead = Mathf.Max(2, (int)((18f + v * 0.4f) / 8f));
            int ti = Mathf.Min(index + ahead, route.Length - 1);
            var target = route[ti];
            // racing line offset, perpendicular to the route direction at the target
            float hwHere = halfWidth != null && halfWidth.Length == route.Length ? halfWidth[index] : 30f;
            float offset = lineOffset * Mathf.Clamp01((hwHere - 10f) / 20f);
            if (offset != 0f && !jz && ti + 1 < route.Length)
            {
                var dir = route[ti + 1] - route[ti];
                dir.y = 0f;
                if (dir.sqrMagnitude > 0.01f)
                {
                    dir.Normalize();
                    target += new Vector3(dir.z, 0f, -dir.x) * offset;
                }
            }
            var to = new Vector2(target.x - p.x, target.z - p.z);
            float want = Mathf.Atan2(to.x, to.y);
            float diff = Mathf.DeltaAngle(s.yaw * Mathf.Rad2Deg, want * Mathf.Rad2Deg) * Mathf.Deg2Rad;
            float steer = diff * 3f + Avoid(s, v);
            // drifting towards the edge of the road: steer back to the middle
            bool nearEdge = false;
            {
                var a0 = route[index];
                var d0 = route[Mathf.Min(index + 1, route.Length - 1)] - a0;
                d0.y = 0f;
                if (d0.sqrMagnitude > 0.01f)
                {
                    d0.Normalize();
                    float lat = Vector3.Dot(p - a0, new Vector3(d0.z, 0f, -d0.x));
                    dbgLat = lat;
                    if (Mathf.Abs(lat) > hwHere - 7f)
                    {
                        nearEdge = true;
                        float latVel = Vector3.Dot(s.vel, new Vector3(d0.z, 0f, -d0.x)) * Mathf.Sign(lat);
                        if (latVel > 0f) steer -= Mathf.Sign(lat) * 0.8f;
                    }
                }
            }
            // human-like mistakes: a short wrong input now and then (rookies more often)
            if (!neverErr && !jz)
            {
                errClock -= dt;
                if (errClock <= 0f)
                {
                    errClock = Mathf.Lerp(8f, 45f, skill) * (0.5f + (float)rng.NextDouble());
                    errT = Mathf.Lerp(0.5f, 0.12f, skill);
                    errSteer = ((float)rng.NextDouble() * 2f - 1f) * Mathf.Lerp(0.6f, 0.2f, skill);
                }
                if (errT > 0f) { errT -= dt; steer += errSteer; }
            }
            c.steer = Mathf.Clamp(steer, -1f, 1f);
            // handbrake = drift (2.2x the turn, keeps the speed): before curves tighter than the ship can turn at
            // this speed (port of the RACESTARS autopilot; skilled bots drift later)
            float margin = Mathf.Lerp(0.78f, 0.9f, skill);
            dbgDiff = diff; dbgSlow = false; dbgDrift = false;
            for (int j = 1; !jz && j < 10 + (int)(v / 12f); j++)
            {
                int idx = Mathf.Min(index + j, route.Length - 1);
                if (v * kappa[idx] > Hovercraft.TurnRate(v) * margin && Mathf.Abs(diff) > 0.04f) { c.brake = true; dbgDrift = true; break; }
            }
            if (!jz && nearEdge && v > 80f && Mathf.Abs(diff) > 0.05f) { c.brake = true; dbgDrift = true; }
            // nitro only on long clear straights, never into a corner
            if (!c.brake && !jz && s.onGround && s.nitro > 30f && v < 118f)
            {
                float maxK = 0f;
                int span = Mathf.Min(route.Length - 1 - index, 70);
                for (int j = 1; j <= span; j += 2) maxK = Mathf.Max(maxK, kappa[index + j]);
                if (maxK < 0.0022f && span > 50 && Mathf.Abs(diff) < 0.06f) nitroHold = 0.8f + aggression * 0.8f;
            }
            if (nitroHold > 0f) { nitroHold -= dt; c.nitro = !c.brake && v < 132f; }
            // jump ahead: full speed, and nitro if a bit slow (the long jumps need ~350-430 km/h)
            if (jz && s.onGround) { c.brake = false; if (v < 110f && s.nitro > 2f) c.nitro = true; }
            return c;
        }
    }
}
