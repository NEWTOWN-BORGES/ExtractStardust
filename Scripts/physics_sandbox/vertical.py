"""Physics sandbox, side view: the craft over a ramp, a crest, a drop and bumps, with the OLD vertical model (before
2026-11-01) and the NEW one (AEXHoverCraft::StepFlight). The NEW model here mirrors the C++ step by step (same
parameters, 1/60 s steps): keep them in sync when tuning. python3 Scripts/physics_sandbox/vertical.py [out_dir]

NEW model, in short (Docs/FISICA.md):
- four hover pads (nose, tail, two at the sides) push only, never pull: a spring to the hover height that carries the
  weight, damped; beyond their reach they push nothing, so the craft leaves the ground by itself over a crest or a lip
  when the ground falls away faster than gravity (plus a little ground-effect downforce at speed) can follow;
- full gravity at all times (along a slope it slows the climb and speeds the descent);
- the attitude (pitch and roll) has inertia: the pads' push turns it on the ground, and in the air the nose turns
  slowly to follow the flight path (weathervane) instead of snapping level;
- a hard landing compresses the pads, scrubs a little speed and shakes the camera.
"""
import math
import os
import sys

import numpy as np

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
DT = 1.0 / 60.0
G = 22.0                     # GravityMps2 (the game's weight: ~2.2 g)
H0 = 1.5                     # HoverHeightM
REACH = H0 * 3.0             # probe length
PADS = [(1.6, 0.25), (-1.6, 0.25), (0.0, 0.25), (0.0, 0.25)]   # (forward offset m, share): nose, tail, two sides
VMAX = 118.0

# NEW parameters (the C++ UPROPERTY defaults)
P = dict(PadStiffness=45.0, PadDamping=0.75, DownforceMps2=10.0, PitchRadiusM=1.8, AttitudeDamping=3.0,
         AirAlign=5.0, AirAlignDamping=2.2, LandingScrub=0.012, PadSmoothing=0.06, PadMaxG=4.0)


HULL_BOTTOM = 0.45


def hull_contact(ter, x, z, vx, vz):
    """MoveWithCollision on a gentle surface: the hull cannot go into the ground; the velocity into it is removed."""
    gz = ter.z(x)
    if z - gz >= HULL_BOTTOM:
        return z, vx, vz, False
    n = ter.normal(x)
    into = vx * n[0] + vz * n[1]
    if into < 0.0:
        vx -= n[0] * into
        vz -= n[1] * into
    return gz + HULL_BOTTOM, vx, vz, True


class Terrain:
    def __init__(self, xs, zs):
        self.xs = np.asarray(xs, float)
        self.zs = np.asarray(zs, float)

    def z(self, x):
        return float(np.interp(x, self.xs, self.zs))

    def ray(self, ox, oz, dx, dz, reach):
        """Distance along (dx, dz) from (ox, oz) to the ground, or None beyond reach (marched, then refined)."""
        prev = 0.0
        if oz - self.z(ox) <= 0.0:
            return 0.0
        steps = 60
        for k in range(1, steps + 1):
            t = reach * k / steps
            if oz + dz * t - self.z(ox + dx * t) <= 0.0:
                lo, hi = prev, t
                for _ in range(20):
                    mid = 0.5 * (lo + hi)
                    if oz + dz * mid - self.z(ox + dx * mid) <= 0.0:
                        hi = mid
                    else:
                        lo = mid
                return 0.5 * (lo + hi)
            prev = t
        return None

    def normal(self, x):
        e = 0.5
        s = (self.z(x + e) - self.z(x - e)) / (2 * e)
        n = np.array([-s, 1.0])
        return n / np.linalg.norm(n)


def simulate_new(ter, x0, speed, seconds, throttle_hold=True):
    x, z = x0, ter.z(x0) + H0
    vx, vz = speed, 0.0
    th, om = 0.0, 0.0          # pitch (rad, nose up +) and its rate
    prev_h = [H0] * 4
    smooth_h = [H0] * 4
    out = []
    was_ground = True
    land_events = []
    for i in range(int(seconds / DT)):
        fwd = np.array([math.cos(th), math.sin(th)])
        up = np.array([-math.sin(th), math.cos(th)])
        ax, az = 0.0, -G
        alpha = 0.0
        hits = 0
        hs = []
        kh, ch = P['PadStiffness'], 2.0 * P['PadDamping'] * math.sqrt(P['PadStiffness'])
        preload = G * max(0.0, up[1])
        v = math.hypot(vx, vz)
        for k, (off, share) in enumerate(PADS):
            ox, oz = x + fwd[0] * off, z + fwd[1] * off
            raw = ter.ray(ox, oz, -up[0], -up[1], REACH)
            if raw is None:
                prev_h[k] = smooth_h[k] = REACH
                hs.append(None)
                continue
            # the skirt averages the ground under it: short bumps are smoothed (and the first contact is not)
            a = 1.0 - math.exp(-DT / P['PadSmoothing'])
            h = raw if smooth_h[k] >= REACH else smooth_h[k] + (raw - smooth_h[k]) * a
            smooth_h[k] = h
            hits += 1
            hs.append(h)
            hdot = (h - prev_h[k]) / DT
            prev_h[k] = h
            f = share * min(P['PadMaxG'] * G, max(0.0, kh * (H0 - h) + preload - ch * hdot))
            ax += up[0] * f
            az += up[1] * f
            alpha += f * off / P['PitchRadiusM'] ** 2
        grounded = hits >= 2
        if grounded:
            hav = np.mean([h for h in hs if h is not None])
            fade = max(0.0, min(1.0, 1.0 - (hav - H0) / H0))
            df = P['DownforceMps2'] * (v / VMAX) ** 2 * fade
            ax -= up[0] * df
            az -= up[1] * df
            alpha -= P['AttitudeDamping'] * om
            if throttle_hold:   # hold the speed along the nose (the game's thrust at this speed)
                fv = vx * fwd[0] + vz * fwd[1]
                acc = (speed - fv) * 2.0
                ax += fwd[0] * acc
                az += fwd[1] * acc
        else:
            # the nose follows the flight path, slowly
            vdir = math.atan2(vz, vx)
            err = (vdir - th + math.pi) % (2 * math.pi) - math.pi
            alpha += P['AirAlign'] * err * min(1.0, v / VMAX) - P['AirAlignDamping'] * om
        if grounded and not was_ground:
            n = ter.normal(x)
            vn = -(vx * n[0] + vz * n[1])
            if vn > 6.0:
                scrub = min(0.25, P['LandingScrub'] * (vn - 6.0))
                vx *= 1.0 - scrub
                vz *= 1.0 - scrub
            land_events.append((x, vn))
        was_ground = grounded
        vx += ax * DT
        vz += az * DT
        om += alpha * DT
        x += vx * DT
        z += vz * DT
        z, vx, vz, scraped = hull_contact(ter, x, z, vx, vz)
        th += om * DT
        out.append((x, z, th, grounded, z - ter.z(x)))
    return np.array(out, dtype=object), land_events


def simulate_old(ter, x0, speed, seconds):
    """The model before 2026-11-01: one spring along the craft's up (pulls down up to 1.3 g), 60 % of the slope's
    gravity on the ground, the up vector turned towards the ground at 160 deg/s and back to level at 45 deg/s."""
    K, damp, slope_g = 40.0, 1.25, 0.6
    x, z = x0, ter.z(x0) + H0
    vx, vz = speed, 0.0
    up = np.array([0.0, 1.0])
    out = []
    land_events = []
    was = True
    for i in range(int(seconds / DT)):
        # the sphere probe straight along -up: height
        h = ter.ray(x, z, -up[0], -up[1], REACH)
        n = ter.normal(x)
        grounded = h is not None and h < H0 * 2.5 and np.dot(n, up) > 0.5
        target = n if grounded else np.array([0.0, 1.0])
        rate = math.radians(160 if grounded else 45) * DT
        ang = math.atan2(up[0] * target[1] - up[1] * target[0], np.dot(up, target))
        a = max(-rate, min(rate, ang))
        c, s = math.cos(a), math.sin(a)
        up = np.array([c * up[0] - s * up[1], s * up[0] + c * up[1]])
        up /= np.linalg.norm(up)
        fwd = np.array([up[1], -up[0]])
        if grounded:
            vn = vx * up[0] + vz * up[1]
            acc = max(K * (H0 - h), -G * 1.3) - 2 * math.sqrt(K) * damp * vn
            ax, az = up[0] * acc, up[1] * acc
            g = np.array([0.0, -G])
            gt = g - np.dot(g, up) * up
            ax += gt[0] * slope_g
            az += gt[1] * slope_g
            fv = vx * fwd[0] + vz * fwd[1]
            hold = (speed - fv) * 2.0
            ax += fwd[0] * hold
            az += fwd[1] * hold
        else:
            ax, az = 0.0, -G
        if grounded and not was:
            land_events.append((x, -(vx * n[0] + vz * n[1])))
        was = grounded
        vx += ax * DT
        vz += az * DT
        x += vx * DT
        z += vz * DT
        z, vx, vz, scraped = hull_contact(ter, x, z, vx, vz)
        th = math.atan2(fwd[1], fwd[0])
        out.append((x, z, th, grounded, z - ter.z(x)))
    return np.array(out, dtype=object), land_events


def kicker():
    a = math.radians(14)
    L = 60.0
    xs = [-200, 0, L * math.cos(a), L * math.cos(a) + 0.01, 900]
    zs = [0, 0, L * math.sin(a), 0, 0]
    return Terrain(xs, zs), -60.0, 90.0, 4.0, 'Rampa de 14° (60 m) a 324 km/h'


def crest():
    # a smooth hump, 8 m high over 160 m (radius ~160 m at the top, 9° at its steepest)
    xs = np.linspace(0, 160, 200)
    zs = 4.0 * (1 - np.cos(2 * math.pi * xs / 160.0))
    xs = np.concatenate([[-400], xs, [900]])
    zs = np.concatenate([[0], zs, [0]])
    return Terrain(xs, zs), -100.0, 110.0, 3.0, 'Lomba suave (8 m em 160 m) a 396 km/h'


def drop():
    xs = [-200, 60, 60.01, 800]
    zs = [12, 12, 0, 0]
    return Terrain(xs, zs), -40.0, 70.0, 3.0, 'Queda de 12 m a 252 km/h'


def bumps():
    xs = np.linspace(-100, 400, 2000)
    zs = np.where((xs > 40) & (xs < 200), 0.4 * np.sin((xs - 40) * 2 * math.pi / 8.0), 0.0)
    return Terrain(xs, zs), -60.0, 80.0, 3.5, 'Costelas (0,4 m a cada 8 m) a 288 km/h'


def draw(scenarios, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(16, 5.6 * len(scenarios)), facecolor='#0a1426')
    grid = fig.add_gridspec(len(scenarios) * 2, 1, height_ratios=[3, 1.1] * len(scenarios), hspace=0.35)
    rows = []
    for k, make in enumerate(scenarios):
        ter, x0, speed, secs, title = make()
        new, land_new = simulate_new(ter, x0, speed, secs)
        old, land_old = simulate_old(ter, x0, speed, secs)
        ax = fig.add_subplot(grid[2 * k])
        axp = fig.add_subplot(grid[2 * k + 1], sharex=ax)
        xmin = min(ter.xs[1] - 80, x0)
        xmax = max(float(new[-1][0]), float(old[-1][0]))
        gx = np.linspace(xmin, xmax, 800)
        for a in (ax, axp):
            a.set_facecolor('#0a1426')
            a.tick_params(colors='#8ca5c4')
            for sp in a.spines.values():
                sp.set_color('#2a3a55')
        ax.fill_between(gx, [ter.z(v) for v in gx], min(ter.zs) - 30, color='#7a4a2c')
        for run, col, lab in ((old, '#ff7a3a', 'ANTES'), (new, '#46dcff', 'AGORA')):
            xs = [float(p[0]) for p in run]
            ax.plot(xs, [float(p[1]) for p in run], color=col, lw=2.2, label=lab)
            axp.plot(xs, [math.degrees(float(p[2])) for p in run], color=col, lw=1.8)
            air = [i for i, p in enumerate(run) if not p[3]]
            if air:
                ax.plot([xs[i] for i in air], [float(run[i][1]) for i in air], '.', color=col, ms=3, alpha=0.5)
        air_new = sum(1 for p in new if not p[3]) * DT
        air_old = sum(1 for p in old if not p[3]) * DT
        top_new = max(float(p[4]) for p in new)
        top_old = max(float(p[4]) for p in old)
        ln = max([v for _, v in land_new], default=0.0)
        lo = max([v for _, v in land_old], default=0.0)
        rows.append((title, air_old, air_new, top_old, top_new, lo, ln))
        ax.set_title('%s   |   no ar: antes %.2f s, agora %.2f s   ·   altura máx.: %.1f → %.1f m   ·   aterragem: %.0f → %.0f m/s'
                     % (title, air_old, air_new, top_old, top_new, lo, ln), color='white', fontsize=12, loc='left')
        ax.set_xlim(xmin, xmax)
        zmax = max(max(float(p[1]) for p in new), max(float(p[1]) for p in old)) + 6
        ax.set_ylim(min(ter.zs) - 4, zmax)
        ax.legend(loc='upper right', facecolor='#081226', edgecolor='#46dcff', labelcolor='white')
        ax.set_ylabel('altura (m)', color='#8ca5c4')
        axp.set_ylabel('nariz (°)', color='#8ca5c4')
        axp.axhline(0, color='#2a3a55', lw=0.8)
        axp.set_xlabel('metros', color='#8ca5c4')
    fig.savefig(path, dpi=80, facecolor=fig.get_facecolor(), bbox_inches='tight')
    return rows


if __name__ == '__main__':
    rows = draw([kicker, crest, drop, bumps], os.path.join(OUT, 'fisica_vertical.png'))
    for r in rows:
        print('%-42s air %.2f -> %.2f s  top %.1f -> %.1f m  land %.0f -> %.0f m/s' % r)
