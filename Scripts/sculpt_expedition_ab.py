# RED DUST DIVIDE - point-to-point expedition (A -> B), 10-12 minutes, after the GDD (Docs: 01_Mapas_Pistas_Expedicoes,
# sections 16-19: geology first, natural surfaces, SAFE / RACING / SKILL routes, natural banks, half-pipes, jumps,
# caves, a memorable moment every 30-60 s) and the lessons of the 10 x 8 km world (seen from the ground it was empty
# and flat: here the track is always framed by rock, every straight ends on a landmark and the horizon is closed).
#
# The world is a Canyonlands-like two-tier canyon country carved into a high plateau (16 x 12 km):
#   TOP plateau (~450 m) -> outer cliffs -> White Rim BENCH (~240 m) -> inner gorge -> canyon FLOOR (~20-40 m),
#   with side slot canyons (fendas) and a desert basin (dunes, arches, hoodoos) closed in by cliffs.
# Sectors of the main (RACING) route, at the timings the speed model gives:
#   S1 The Basin (top, start grid) - S2 Broken Mesa (slabs; first split) - S3 Shafer Fall (switchbacks down the outer
#   cliff to the bench) - S4 The Red Wall (a tributary born on the bench that cuts down to the floor in one long bend,
#   its outer bank steepening) - S5 Fendas (three ways through the slot canyons) - S6 Horseshoe (270 degree bend; SKILL
#   jumps the neck) - S7 The Wash (dry riverbed half-pipe) - S8 The Hollow (cave with a chamber and a split) -
#   S9 Arches Run (desert: dunes, arches, hoodoos) - S10 White Rim (up onto the bench, hero jump, finish B).
#
# Usage: blender -b -P sculpt_expedition_ab.py -- <out_dir> [cell_m] [plan|noshots] kit=<dir> molds=<dir> plants=<dir> ship=<fbx>
#   molds: every rock mold (our kit + SourceArt/Rocks + SourceArt/S01 FBX in one folder; falls back to kit)
#   cell_m: metres between heightfield samples (5 to iterate, 4 at work, 3 at home); plan: route and timing only.
import json
import math
import os
import struct
import sys
import zlib
import numpy as np
import bpy

a = sys.argv[sys.argv.index("--") + 1:]
OUT = a[0]
PLAN = "plan" in a
CELL = float(next((v for v in a[1:] if v.replace(".", "", 1).isdigit()), 5.0))
os.makedirs(OUT, exist_ok=True)
SX, SY = 16000.0, 12000.0
TOP, BENCH, FLOOR = 450.0, 240.0, 30.0
rng = np.random.default_rng(23)


# ---- Polylines.
def smooth1d(v, window):
    pad = window // 2
    return np.convolve(np.pad(v, pad, mode="edge"), np.ones(window) / window, "valid")[:len(v)]


def arclen(p):
    return np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])


def resample(p, step=1.0):
    s_ = arclen(p)
    t_ = np.arange(0.0, s_[-1], step)
    q = np.stack([np.interp(t_, s_, p[:, 0]), np.interp(t_, s_, p[:, 1])], 1)
    return np.vstack([q, p[-1:]]) if np.hypot(*(q[-1] - p[-1])) > 0.01 else q


def catmull(ctrl, step=2.0):
    P = np.array(ctrl, np.float64)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out, knots = [], [0]
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        m = max(2, int(np.linalg.norm(p2 - p1) / step))
        t = np.linspace(0.0, 1.0, m, endpoint=False)[:, None]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
        knots.append(knots[-1] + m)
    out.append(Q[-2][None])
    return np.vstack(out), knots


def curvature(p, window=31):
    q_ = np.stack([smooth1d(p[:, 0], window), smooth1d(p[:, 1], window)], 1)
    dx_, dy_ = np.gradient(q_[:, 0]), np.gradient(q_[:, 1])
    ddx_, ddy_ = np.gradient(dx_), np.gradient(dy_)
    return (dx_ * ddy_ - dy_ * ddx_) / (np.hypot(dx_, dy_) ** 3 + 1e-9)


def relax(p, rmin, fixed=None, iters=300, reach=30):
    """Opens bends tighter than rmin (per point), respacing to 1 m every pass; returns the line and, for each new point,
    the index of the input point it came from."""
    a0, a1 = p[0].copy(), p[-1].copy()
    rm0 = np.asarray(rmin, float) if np.ndim(rmin) else np.full(len(p), float(rmin))
    fx0 = np.zeros(len(p), bool) if fixed is None else fixed
    src = np.arange(len(p), dtype=np.float64)
    for _ in range(iters):
        si = np.clip(np.round(src).astype(int), 0, len(rm0) - 1)
        rm, fx_ = rm0[si], fx0[si]
        k_ = curvature(p)
        bad = (np.abs(k_) * rm > 1.0) & ~fx_
        bad[:reach] = bad[-reach:] = False
        if not bad.any():
            break
        ii = np.arange(len(p))
        mid = 0.5 * (p[np.clip(ii - reach, 0, len(p) - 1)] + p[np.clip(ii + reach, 0, len(p) - 1)])
        wgt = (np.clip(np.abs(k_) * rm - 1.0, 0.0, 1.0) * bad)[:, None]
        p = p + 0.4 * wgt * (mid - p)
        sm = np.stack([smooth1d(p[:, 0], 5), smooth1d(p[:, 1], 5)], 1)
        p = np.where(fx_[:, None], p, sm)
        p[0], p[-1] = a0, a1
        s_ = arclen(p)
        t_ = np.arange(0.0, s_[-1], 1.0)
        p = np.stack([np.interp(t_, s_, p[:, 0]), np.interp(t_, s_, p[:, 1])], 1)
        src = np.interp(t_, s_, src)
        if np.hypot(*(p[-1] - a1)) > 0.01:
            p, src = np.vstack([p, a1[None]]), np.append(src, len(rm0) - 1)
    return p, np.clip(np.round(src).astype(int), 0, len(rm0) - 1)


# ---- 1. The main route, sector by sector. Control points (x, y, ground height m) in world metres (origin south-west,
# x east, y north) give the valley axis; a meander (amplitude m, wavelength m) then makes the rhythmic bends, and the
# line is relaxed to the sector's tightest radius (GDD: tight 60-120 m, medium 120-250, fast 250-500, mega arc 500+).
# Per sector: name, surface kind, floor half width m (GDD widths: open 24-35 m, main 14-24, technical 10-16),
# tightest radius m, meander (amplitude, wavelength), control points.
SECTORS = [
    ("S1 The Basin", "top", 17.0, 180.0, (70.0, 1000.0),
     [(15300, 11300, 452), (14400, 10700, 446), (13300, 10900, 444), (12400, 10300, 448), (12600, 9300, 452),
      (13600, 9000, 455), (14400, 8300, 458), (13900, 7600, 462)]),
    ("S2 Broken Mesa", "top", 12.0, 120.0, (130.0, 650.0),
     [(13000, 7200, 466), (12600, 6300, 470), (13300, 5500, 474), (12700, 4800, 476), (11900, 5000, 478), (11450, 5650, 480),
      (11380, 6450, 478)]),
    # Switchbacks down the outer cliff to the bench: four legs 200 m apart, hairpins of ~100 m radius.
    ("S3 Shafer Fall", "switchback", 10.0, 1.0, (0.0, 1.0),
     [(11300, 6800, 470), (11300, 7500, 440), (11200, 7720, 432), (11100, 7500, 424), (11100, 6500, 382), (11000, 6280, 374),
      (10900, 6500, 366), (10900, 7500, 324), (10800, 7720, 316), (10700, 7500, 308), (10700, 6700, 274), (10550, 6350, 255)]),
    # A tributary born on the bench cuts down to the floor in one long left-hand sweep (radius ~700 -> ~250 m): the
    # Red Wall is its outer bank, steepening from a soft bank to a wall as the gorge deepens.
    ("S4 The Red Wall", "gorge", 20.0, 250.0, (0.0, 1.0),
     [(10300, 5950, 240), (9800, 5450, 230), (9100, 5150, 212), (8400, 5300, 185), (7900, 5900, 150), (7650, 6700, 112),
      (7800, 7500, 78), (8150, 8150, 50), (8000, 8800, 42)]),
    # Down the main canyon past the slot canyons (fendas): the SAFE line; RACING and SKILL take the slots.
    ("S5 Fendas", "floor", 16.0, 140.0, (110.0, 700.0),
     [(7550, 9300, 40), (7400, 9950, 39), (6800, 10350, 39), (6050, 10200, 38), (5650, 9750, 37), (5250, 9300, 36)]),
    # Horseshoe: in heading south, 270 degrees round the rock spur, out heading north; SKILL jumps the neck.
    ("S6 Horseshoe", "floor", 22.0, 1.0, (0.0, 1.0),
     [(5150, 8750, 35), (5150, 8150, 34), (5050, 7650, 33), (4750, 7400, 33), (4400, 7550, 32), (4300, 7950, 31),
      (4450, 8450, 30), (4500, 8800, 30), (4300, 9350, 29), (4000, 9750, 29)]),
    ("S7 The Wash", "wash", 28.0, 200.0, (140.0, 1100.0),
     [(3500, 10000, 28), (2900, 9800, 27), (2250, 9150, 26), (1850, 8250, 25), (1800, 7250, 24), (2100, 6350, 22),
      (2400, 5650, 20)]),
    ("S8 The Hollow", "cave", 14.0, 100.0, (60.0, 450.0),
     [(2650, 5150, 16), (2400, 4800, 12), (2900, 4500, 8), (2600, 4100, 4), (2950, 3700, 8), (2500, 3450, 40),
      (2150, 3350, 70)]),
    ("S9 Arches Run", "desert", 18.0, 160.0, (100.0, 800.0),
     [(1700, 2950, 45), (1150, 2450, 50), (850, 1550, 55), (1450, 750, 60), (2550, 550, 62), (3400, 1250, 64),
      (4350, 1000, 66), (5250, 1450, 64), (5900, 1150, 60)]),
    ("S10 White Rim", "rim", 18.0, 300.0, (40.0, 1200.0),
     [(6500, 1650, 62), (7250, 2150, 150), (7900, 2450, 238), (8650, 2650, 240), (9500, 2450, 238), (10300, 2650, 240),
      (10900, 2700, 241), (11400, 2650, 242)]),
]
ctrl = np.array([(x, y) for *_r, pts in SECTORS for x, y, _ in pts], float)
zctl = np.array([z for *_r, pts in SECTORS for _, _, z in pts], float)
secctl = np.array([k for k, (*_r, pts) in enumerate(SECTORS) for _ in pts])
spl, knots = catmull(ctrl)
# Every spline point remembers which control point it started from; carried to 1 m spacing.
kf = np.interp(np.arange(len(spl)), knots, np.arange(len(knots)))
s_spl = arclen(spl)
t1 = np.arange(0.0, s_spl[-1], 1.0)
main = np.stack([np.interp(t1, s_spl, spl[:, 0]), np.interp(t1, s_spl, spl[:, 1])], 1)
kmain = np.interp(t1, s_spl, kf)
sec = secctl[np.clip(np.round(kmain).astype(int), 0, len(ctrl) - 1)]
# Meanders, sector by sector, fading in and out over 300 m at the sector ends.
dx_, dy_ = np.gradient(main[:, 0]), np.gradient(main[:, 1])
nrm = np.stack([-dy_, dx_], 1) / (np.hypot(dx_, dy_)[:, None] + 1e-9)
off = np.zeros(len(main))
for k, (_n, _k, _w, _r, (amp, wave), _p) in enumerate(SECTORS):
    ii = np.flatnonzero(sec == k)
    if amp <= 0 or len(ii) < 10:
        continue
    sl = np.arange(len(ii), dtype=float)
    env = np.clip(sl / 300.0, 0, 1) * np.clip((sl[-1] - sl) / 300.0, 0, 1)
    # Irregular, like a river: three wavelengths with random phases and a slow swell of the amplitude.
    mr = np.random.default_rng(100 + k)
    wig = sum(a_ * np.sin(2 * np.pi * sl * f / wave + mr.uniform(0, 2 * np.pi)) for f, a_ in ((1.0, 1.0), (1.63, 0.5), (2.71, 0.25)))
    wig *= 0.75 + 0.35 * np.sin(2 * np.pi * sl / (wave * 3.7) + mr.uniform(0, 6.3))
    off[ii] = amp * wig / 1.4 * env * env * (3 - 2 * env)
main = main + nrm * off[:, None]
rmin = np.array([SECTORS[s_][3] for s_ in sec], float)
# Designed sectors (switchbacks, horseshoe) keep their drawn shape: opening a hairpin would only shorten it.
main, src = relax(main, rmin, fixed=rmin <= 1.0, iters=500)
kmain, sec = kmain[src], sec[src]
rmin = np.array([SECTORS[s_][3] for s_ in sec], float)
half_w = np.array([SECTORS[s_][2] for s_ in sec], float)
kind = np.array([SECTORS[s_][1] for s_ in sec])
_cv = np.flatnonzero(kind == "cave")
if len(_cv):  # The Hollow: a wide entrance, then the chamber where the pack opens up again before the split
    _f = np.linspace(0, 1, len(_cv))
    half_w[_cv] += 18.0 * np.exp(-((_f - 0.02) / 0.05) ** 2) + 26.0 * np.exp(-((_f - 0.22) / 0.07) ** 2)
# Ground height along the route: piecewise linear between control points, smoothed over ~300 m.
zmain = smooth1d(np.interp(kmain, np.arange(len(zctl)), zctl), 301)
N = len(main)


# ---- 2. Speed model: 550 km/h at most, cornering grip so that a 120 m bend is taken at 200 km/h, anti-grav
# acceleration 12 m/s2 and braking 30 m/s2; standing start. Gives the race time per sector.
VMAX, ALAT, ACC, BRK = 550 / 3.6, (200 / 3.6) ** 2 / 120.0, 12.0, 30.0


def speed_profile(p, cap=None):
    r_ = 1.0 / np.maximum(np.abs(curvature(p)), 1e-6)
    v = np.minimum(VMAX, np.sqrt(ALAT * r_))
    if cap is not None:
        v = np.minimum(v, cap)
    out = v.copy()
    out[0] = 0.0
    for i in range(1, len(out)):
        out[i] = min(out[i], math.sqrt(out[i - 1] ** 2 + 2 * ACC))
    for i in range(len(out) - 2, -1, -1):
        out[i] = min(out[i], math.sqrt(out[i + 1] ** 2 + 2 * BRK))
    return out, r_


cap = np.where(kind == "cave", 420 / 3.6, VMAX)  # inside the cave a little slower (visibility)
vel, radius = speed_profile(main, cap)
dt = 1.0 / np.maximum(vel, 5.0)
t_cum = np.cumsum(dt)
print("ROUTE length %.1f km, time %d:%02d, mean %.0f km/h" % (N / 1000, t_cum[-1] // 60, t_cum[-1] % 60, N / t_cum[-1] * 3.6))
for k, (name, *_r) in enumerate(SECTORS):
    ii = np.flatnonzero(sec == k)
    if len(ii):
        t0, t1_ = t_cum[ii[0]] - dt[ii[0]], t_cum[ii[-1]]
        im = ii[np.argmin(radius[ii])]
        print("  %-16s %5.1f km  %d:%02d-%d:%02d  min radius %4.0f m at (%d, %d)  top %3.0f km/h  slowest %3.0f km/h" % (
            name, len(ii) / 1000, t0 // 60, t0 % 60, t1_ // 60, t1_ % 60, radius[ii].min(), main[im, 0], main[im, 1], vel[ii].max() * 3.6, vel[ii][5:].min() * 3.6))


# ---- 3. Plan (10 m per pixel, north up): the route coloured by sector, start white, finish black.
SECTOR_COLS = [(0.95, 0.85, 0.30), (0.95, 0.55, 0.15), (0.90, 0.25, 0.10), (0.75, 0.10, 0.10), (0.55, 0.25, 0.75),
               (0.20, 0.45, 0.95), (0.15, 0.75, 0.85), (0.10, 0.10, 0.10), (0.95, 0.75, 0.55), (0.35, 0.80, 0.30)]


def plan_image(path, background=None, extra=()):
    mpp = 10.0
    wid, hgt = int(SX / mpp), int(SY / mpp)
    img = np.zeros((hgt, wid, 3), np.float32)
    img[:] = (0.87, 0.76, 0.58) if background is None else background

    def draw(pts, col, r):
        ix, iy = (pts[:, 0] / mpp).astype(int), (pts[:, 1] / mpp).astype(int)
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                ok = (ix + dx >= 0) & (ix + dx < wid) & (iy + dy >= 0) & (iy + dy < hgt)
                img[iy[ok] + dy, ix[ok] + dx] = col

    for pts, col, r in extra:
        draw(pts, col, r)
    for k in range(len(SECTORS)):
        draw(main[sec == k][::3], SECTOR_COLS[k], 2)
    draw(main[:1], (1, 1, 1), 7)
    draw(main[-1:], (0, 0, 0), 7)
    for k in range(0, 10001, 1000):
        pass
    out = bpy.data.images.new("plan", wid, hgt)
    out.pixels.foreach_set(np.concatenate([img, np.ones((hgt, wid, 1))], -1).astype(np.float32).ravel())
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()


if PLAN:
    plan_image(f"{OUT}/ab_plan.png")
    print("PLAN", f"{OUT}/ab_plan.png")
    raise SystemExit

# ---- 4. Branches. Each leaves the main route and rejoins it: ("@", x, y) = the main route point nearest (x, y).
# kind: "slot" (a narrow slot canyon carved to the bed), "slabs" (over slab tops: route jumps), "cave" (second cave
# arm), "surface" (the ground as it is). Bed heights run linearly between the two junctions unless given.
BRANCHES = [
    ("S2 SKILL Lajes", "slabs", 9.0, 90.0, [("@", 12650, 6100), (12950, 5700), (12950, 5250), ("@", 12500, 4850)]),
    ("S5 RACING Fenda Larga", "slot", 14.0, 160.0, [("@", 7450, 9600), (6900, 9600), (6300, 9700), ("@", 5800, 9850)]),
    ("S5 SKILL Fenda Estreita", "slot", 6.0, 60.0, [("@", 7520, 9420), (7000, 9250), (6400, 9200), (5900, 9300), ("@", 5450, 9500)]),
    ("S6 SKILL Istmo", "slot", 7.0, 50.0, [("@", 5150, 8400), (4850, 8500), ("@", 4500, 8600)]),
    ("S8 Braço da Caverna", "cave", 10.0, 80.0, [("@", 2420, 4780), (2150, 4350), (2350, 3900), ("@", 2700, 3600)]),
    ("S9 SKILL Arcos", "surface", 9.0, 90.0, [("@", 2500, 560), (3000, 300), (3700, 650), ("@", 4300, 980)]),
    ("S10 SAFE Contorno", "surface", 16.0, 200.0, [("@", 8350, 2560), (8700, 3050), (9200, 2950), ("@", 9450, 2480)]),
]


def at_main(x, y):
    return int(np.argmin(np.hypot(main[:, 0] - x, main[:, 1] - y)))


branches = {}
for name, bkind, bw, brmin, wps in BRANCHES:
    i0, i1 = at_main(*wps[0][1:3]), at_main(*wps[-1][1:3])
    pts = [main[i0]] + [np.array(w_[:2], float) for w_ in wps[1:-1]] + [main[i1]]
    p, _k = catmull(pts)
    p = resample(p)
    fx = np.zeros(len(p), bool)
    fx[:3] = fx[-3:] = True
    p, _s = relax(p, brmin, fixed=fx, iters=300)
    z = np.interp(np.arange(len(p)), [0, len(p) - 1], [zmain[i0], zmain[i1]])
    branches[name] = dict(p=p, z=z, w=bw, kind=bkind, leave=i0, rejoin=i1)
    print("BRANCH %-26s %5.0f m (main %5.0f m)" % (name, len(p), i1 - i0))

# ---- 5. Terrain. Grid, noise.
NX, NY = int(SX / CELL), int(SY / CELL)
Yi, Xi = np.mgrid[0:NY, 0:NX].astype(np.float32)
XM, YM = Xi * CELL, Yi * CELL


def lattice(period):
    m = max(2, int(math.ceil(max(SX, SY) / period)) + 2)
    return rng.random((m, m)).astype(np.float32) * 2.0 - 1.0, period


def sample(lat, x, y):
    g, period = lat
    m = g.shape[0]
    fx, fy = x / period, y / period
    ix, iy = np.floor(fx).astype(np.int64), np.floor(fy).astype(np.int64)
    tx, ty = fx - ix, fy - iy
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    x0, y0, x1, y1 = ix % m, iy % m, (ix + 1) % m, (iy + 1) % m
    top = g[y0, x0] + (g[y0, x1] - g[y0, x0]) * tx
    bottom = g[y1, x0] + (g[y1, x1] - g[y1, x0]) * tx
    return top + (bottom - top) * ty


def fbm(x, y, period, octaves, gain=0.5):
    total, amp, norm = np.zeros_like(x, dtype=np.float32), 1.0, 0.0
    for o in range(octaves):
        total += amp * sample(lattice(period / (2 ** o)), x, y)
        norm += amp
        amp *= gain
    return total / norm


def smoothstep(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def shift(arr, dy, dx, fill):
    out = np.full_like(arr, fill)
    ys = slice(max(dy, 0), arr.shape[0] + min(dy, 0))
    yd = slice(max(-dy, 0), arr.shape[0] + min(-dy, 0))
    xs = slice(max(dx, 0), arr.shape[1] + min(dx, 0))
    xd = slice(max(-dx, 0), arr.shape[1] + min(-dx, 0))
    out[ys, xs] = arr[yd, xd]
    return out


def nearest(pts, reach):
    """Distance from every cell to a polyline (points <= 10 m apart) and the index of the nearest point, out to `reach`
    m (1e6 beyond): nearest point grown on a 20 m grid, exact distance at full resolution."""
    C = 20.0
    nyc, nxc = int(SY / C) + 1, int(SX / C) + 1
    cy, cx = np.mgrid[0:nyc, 0:nxc].astype(np.float32)
    cx, cy = (cx + 0.5) * C, (cy + 0.5) * C
    best = np.full((nyc, nxc), -1, np.int64)
    ins = (pts[:, 0] >= 0) & (pts[:, 0] < SX) & (pts[:, 1] >= 0) & (pts[:, 1] < SY)
    best[(pts[ins, 1] / C).astype(int), (pts[ins, 0] / C).astype(int)] = np.flatnonzero(ins)
    bd = np.where(best >= 0, (cx - pts[np.maximum(best, 0), 0]) ** 2 + (cy - pts[np.maximum(best, 0), 1]) ** 2, np.inf)
    for _ in range(int(reach / C) + 2):
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            cand = shift(best, dy, dx, -1)
            ok = cand >= 0
            cc = np.maximum(cand, 0)
            dd = np.where(ok, (cx - pts[cc, 0]) ** 2 + (cy - pts[cc, 1]) ** 2, np.inf)
            better = dd < bd
            best, bd = np.where(better, cand, best), np.where(better, dd, bd)
    idx = best[np.clip((YM / C).astype(int), 0, nyc - 1), np.clip((XM / C).astype(int), 0, nxc - 1)]
    d = np.where(idx >= 0, np.hypot(XM - pts[np.maximum(idx, 0), 0], YM - pts[np.maximum(idx, 0), 1]), 1e6).astype(np.float32)
    # The 20 m grid can be ~14 m out: near the line, search the neighbouring points along it for the true nearest.
    band = np.flatnonzero((idx.ravel() >= 0) & (d.ravel() < reach + 40.0))
    if len(band):
        spacing = float(np.median(np.hypot(*np.diff(pts, axis=0).T))) if len(pts) > 1 else 1.0
        R = int(30.0 / max(spacing, 0.5)) + 2
        bi, bx, by = idx.ravel()[band], XM.ravel()[band], YM.ravel()[band]
        bestd, besti = d.ravel()[band].copy(), bi.copy()
        for o in range(-R, R + 1):
            j = np.clip(bi + o, 0, len(pts) - 1)
            dd = np.hypot(bx - pts[j, 0], by - pts[j, 1])
            better = dd < bestd
            bestd, besti = np.where(better, dd, bestd), np.where(better, j, besti)
        d.ravel()[band] = bestd
        idx.ravel()[band] = besti
    return d, idx


def stepped(f):
    """Cliff profile 0..1 -> 0..1 height: three steep cliff bands with talus benches between (Grand Canyon style)."""
    knots_x = np.array([0.0, 0.06, 0.30, 0.42, 0.66, 0.76, 1.0])
    knots_y = np.array([0.0, 0.10, 0.42, 0.50, 0.80, 0.86, 1.0])
    return np.interp(np.clip(f, 0, 1), knots_x, knots_y)


def lateral(pts, idx):
    """Signed distance to the left of a polyline, for cells whose nearest point is idx."""
    t = np.gradient(pts, axis=0)
    t /= np.hypot(t[:, 0], t[:, 1])[:, None] + 1e-9
    i = np.maximum(idx, 0)
    return (YM - pts[i, 1]) * t[i, 0] - (XM - pts[i, 0]) * t[i, 1]


# 5a. The high plateau (Island in the Sky): broad swells, Navajo domes and the odd low butte; ranges of higher mesas
# along the world edge close the horizon.
H = TOP + 22.0 * fbm(XM, YM, 2600, 3) + 7.0 * fbm(XM + 91, YM, 420, 3) + 1.5 * fbm(XM, YM - 7, 45, 2)
domes = np.clip(fbm(XM - 300, YM + 120, 520, 2) - 0.25, 0, 1)
H += 55.0 * domes ** 1.6
edge = np.minimum(np.minimum(XM, SX - XM), np.minimum(YM, SY - YM))
ranges = smoothstep(900.0, 150.0, edge + 750.0 * fbm(XM, YM, 1700, 3) + 160.0 * fbm(XM - 9, YM, 300, 2))
H += ranges * (120.0 + 90.0 * np.clip(0.5 + fbm(XM + 5, YM, 1500, 2), 0, 1))

# Navajo domes crowd the plateau lines (S1-S2): 25-70 m slickrock domes 60-400 m from the line, never on it.
top_line = main[np.isin(kind, ["top"])][::8]
d_top, _it = nearest(top_line, 700)
dome_f = np.clip(fbm(XM + 1300, YM - 900, 300, 3) - 0.05, 0, 1)
dome_near = smoothstep(700.0, 250.0, d_top) * smoothstep(55.0, 110.0, d_top)
dome_near *= smoothstep(350.0, 650.0, np.hypot(XM - 11320.0, YM - 6700.0))  # the rim before Shafer Fall stays open
dome_h = 1.0 - (1.0 - np.clip(dome_f / 0.32, 0, 1)) ** 2.2  # rounded crowns (Navajo domes), never points
H += (68.0 * dome_h * dome_near).astype(np.float32)

# 5b. The canyon system. Main canyon M: from the north-east edge down to the confluence J, then the route (S5-S7),
# ending in a box canyon at the cave mouth. Tributary T1: the Red Wall (S4), born on the bench.
sec_of = lambda k: np.flatnonzero(sec == k)
J = main[sec_of(4)[0]]
up = resample(catmull([(10200, 12100), (9800, 10800), (9300, 9900), (8700, 9200), tuple(J)])[0], 8.0)
zup = np.interp(np.arange(len(up)), [0, len(up) - 1], [130.0, zmain[sec_of(4)[0]]])
down = main[sec_of(4)[0]:sec_of(6)[-1] + 1][::8]
zdown = zmain[sec_of(4)[0]:sec_of(6)[-1] + 1][::8]
M_pts = np.vstack([up, down[1:]])
M_z = np.concatenate([zup, zdown[1:]])
M_hw = np.concatenate([np.full(len(up), 60.0), np.maximum(half_w[sec_of(4)[0]:sec_of(6)[-1] + 1][::8][1:] + 18.0, 42.0)])
T_pts = main[sec_of(3)][::8]
T_z = zmain[sec_of(3)][::8]
T_hw = np.full(len(T_pts), 34.0)
dM, iM = nearest(M_pts, 1600)
dT, iT = nearest(T_pts, 1600)
# Rim wander and alcoves, then bench extent.
wander = 22.0 * fbm(XM, YM, 160, 2) + 45.0 * np.clip(2.0 * fbm(XM + 50, YM - 80, 300, 1) - 0.5, 0, 1)
# The bench edge is ragged at every scale: promontories and alcoves from ~100 m to ~1100 m wide.
bench_w = np.clip(520.0 + 620.0 * fbm(XM - 200, YM + 300, 1600, 3) + 220.0 * fbm(XM + 17, YM, 380, 2), 90.0, 1300.0)
gorge_w = 150.0  # horizontal run of the inner gorge walls (floor edge -> bench rim)
cliff_w = 170.0  # outer cliffs (bench -> plateau)
benchz = BENCH + 6.0 * fbm(XM, YM, 600, 2) + 1.2 * fbm(XM, YM, 40, 2)
d_rim = np.minimum(dM - M_hw[np.maximum(iM, 0)], dT - T_hw[np.maximum(iT, 0)]) - wander
# The White Rim bench (S10) and the switchback slope (S3) are part of the bench country too.
s10 = main[sec_of(9)]
d10, i10 = nearest(s10[::8], 1200)
lat10 = lateral(s10[::8], i10)
lat10 = np.where((i10 > 3) & (i10 < len(s10[::8]) - 4), lat10, 0.0)  # past the ends of the line: neither side
bench_zone = (d_rim < gorge_w + bench_w) | ((d10 < 900) & (lat10 > -60))
d_bench_edge = np.where(bench_zone, 0.0, np.minimum(d_rim - gorge_w - bench_w, np.where(lat10 > -60, d10 - 900, 1e6)))
outer = benchz + (H - benchz) * stepped(np.clip(d_bench_edge / cliff_w, 0, 1))
H = np.where(d_bench_edge < cliff_w * 1.05, np.minimum(H, outer), H)
# Shafer slope (S3): a wide talus apron from the plateau edge down to the bench, where the switchbacks run.
# An oval apron with a ragged edge round the switchbacks.
shafer_e = np.hypot((XM - 10930.0) / 640.0, (YM - 7020.0) / 1000.0) + 0.12 * fbm(XM, YM, 260, 2)
shafer = shafer_e < 1.0
apron = BENCH + (TOP + 30.0 - BENCH) * smoothstep(10500.0, 11450.0, XM + 40 * fbm(XM, YM, 300, 2)) + 4.0 * fbm(XM, YM, 80, 2)
fade = smoothstep(1.0, 0.8, shafer_e)
H = np.where(shafer, H * (1 - fade) + np.minimum(H, apron) * fade, H)


def gorge(d, hw, floor_z, rim_z):
    """Canyon cross-section: floor (with a concave half-pipe rise at its edges), stepped walls up to the rim."""
    e = d - hw
    depth = np.maximum(rim_z - floor_z, 0.0)
    lip = np.minimum(8.0, depth)
    inside = lip * np.clip(d / np.maximum(hw, 1.0), 0, 1) ** 2  # the floor curls up 8 m at its edges (half-pipe)
    wall = lip + (depth - lip) * stepped(np.clip(e / gorge_w, 0, 1))
    return floor_z + np.where(e < 0, inside, wall)


fM = M_z[np.maximum(iM, 0)]
H = np.where(dM < M_hw[np.maximum(iM, 0)] + gorge_w + 40, np.minimum(H, gorge(dM + wander * 0.5, M_hw[np.maximum(iM, 0)], fM, benchz)), H)
fT = T_z[np.maximum(iT, 0)]
H = np.where(dT < T_hw[np.maximum(iT, 0)] + gorge_w + 40, np.minimum(H, gorge(dT + wander * 0.5, T_hw[np.maximum(iT, 0)], fT, benchz)), H)

# Remnants: mesas and buttes left standing on the bench and in the basin (never on a line: 150 m clear).
d_any, _i = nearest(main[::8], 400)
def dilate(mask, r):
    out = mask.copy()
    for k in range(1, r + 1):
        out |= np.roll(mask, k, 0) | np.roll(mask, -k, 0)
    m2 = out.copy()
    for k in range(1, r + 1):
        out |= np.roll(m2, k, 1) | np.roll(m2, -k, 1)
    return out


def broad(mask, width_m):
    """Keeps only the parts of a mask at least width_m across (morphological opening): no thin needles."""
    r = max(1, int(round(width_m / 2.0 / CELL)))
    return dilate(~dilate(~mask, r), r) & mask


rem = np.clip(fbm(XM + 700, YM - 300, 650, 3) - 0.18, 0, 1) * (d_any > 150)
on_bench = (H < benchz + 20) & (H > benchz - 20)
rem_ok = broad((rem > 0.02) & on_bench, 70.0)
H = np.where(rem_ok, np.maximum(H, benchz + (TOP - BENCH) * stepped(np.clip(rem / 0.12, 0, 1))), H)

# 5c. Slot canyons (fendas) cut into the bench and plateau beside the canyons: a branching network where a ridged
# noise crosses zero, floors stepping down to the canyon floor (scenery; the slot branches are carved below).
near_canyon = smoothstep(1400.0, 300.0, np.minimum(dM, dT)) * (YM > 6800)
slot = np.zeros((NY, NX), np.float32)
for period, amp, sharp in ((700.0, 1.0, 9), (300.0, 0.7, 14)):
    side = 1.0 - np.abs(fbm(XM + period, YM - period, period, 2))
    slot = np.maximum(slot, amp * side ** sharp)
slot *= near_canyon
slot_floor = fM + (np.minimum(dM, dT) - 60.0).clip(0) * 0.06 + 10.0
H = np.where(slot > 0.45, np.minimum(H, slot_floor + (H - slot_floor) * smoothstep(0.75, 0.45, slot)), H)

# 5d. The desert basin (S9) and the low ground under the White Rim (S10), closed in by cliffs.
s9 = main[sec_of(8)]
d9, i9 = nearest(s9[::8], 1300)
basin_r = np.clip(700.0 + 650.0 * fbm(XM + 33, YM - 21, 1700, 3) + 180.0 * fbm(XM, YM, 420, 2), 220.0, 1500.0)
basin = (d9 < basin_r) | ((d10 < 1300 + 400.0 * fbm(XM, YM, 1200, 2)) & (lat10 < -215))
d_basin = np.where(basin, 0.0, np.minimum(d9 - basin_r, np.where(lat10 < -215, d10 - 1300, 1e6)))
basin_z = 58.0 + 14.0 * fbm(XM, YM, 1800, 2) + 3.0 * fbm(XM, YM, 120, 2)
H = np.where(d_basin < cliff_w * 1.2, np.minimum(H, basin_z + (H - basin_z) * stepped(np.clip(d_basin / (cliff_w * 1.2), 0, 1))), H)
# Buttes in the basin (Monument Valley style blocks on talus cones), clear of the lines.
in_basin = d_basin <= 0
bm = np.clip(fbm(XM - 900, YM + 450, 520, 3) - 0.22, 0, 1) * (d_any > 160) * in_basin
H = np.where(broad(bm > 0.02, 70.0), np.maximum(H, basin_z + 150.0 * stepped(np.clip(bm / 0.10, 0, 1))), H)
# Rim edge: south of the S10 route the bench drops at once (the rim is 45-70 m from the line).
rim_drop = (d10 < 1300) & (lat10 < -45 - 25 * fbm(XM, YM, 300, 1))
H = np.where(rim_drop, np.minimum(H, basin_z + (benchz - basin_z) * stepped(np.clip(1.0 - (-lat10 - 45) / 170.0, 0, 1))), H)
print("TERRAIN base done", round(float(H.min()), 1), round(float(H.max()), 1))

# 5e. Features the route needs before its bed is cut.
# Start basin (S1): a wide shallow slickrock bowl round the grid (GDD: 30-38 m wide start, rows of 5).
A = main[0]
dA = np.hypot(XM - A[0], YM - A[1])
H -= 14.0 * smoothstep(650.0, 150.0, dA)
# Broken Mesa (S2): tilted sandstone slabs, broken into blocks; along the SKILL branch they are a chain to jump.
s2 = main[sec_of(1)]
d2, i2 = nearest(s2[::8], 700)
# Broken slabs: plates on a jittered 130 m grid (each the nearest seed's), each raised 3-9 m and tilted its own way
# (3-9 %), split by 3 m cracks where two plates meet; none on the line itself, none at the rim before the drop.
PL = 130.0
gyp, gxp = np.floor(YM / PL).astype(np.int64), np.floor(XM / PL).astype(np.int64)
prng_s = np.random.default_rng(31)
ny_p, nx_p = int(SY / PL) + 3, int(SX / PL) + 3
jit = prng_s.uniform(0.15, 0.85, (ny_p, nx_p, 2))
lift = prng_s.uniform(3.0, 9.0, (ny_p, nx_p))
ang = prng_s.uniform(0, 2 * np.pi, (ny_p, nx_p))
grade = prng_s.uniform(0.03, 0.09, (ny_p, nx_p))
d1 = np.full((NY, NX), np.inf, np.float32)
d2s = np.full((NY, NX), np.inf, np.float32)
own = np.zeros((NY, NX, 2), np.int64)
for oy in (-1, 0, 1):
    for ox in (-1, 0, 1):
        cy_, cx_ = np.clip(gyp + oy, 0, ny_p - 1), np.clip(gxp + ox, 0, nx_p - 1)
        sx_ = (cx_ + jit[cy_, cx_, 0]) * PL
        sy_ = (cy_ + jit[cy_, cx_, 1]) * PL
        dd = np.hypot(XM - sx_, YM - sy_)
        closer = dd < d1
        d2s = np.where(closer, d1, np.minimum(d2s, dd))
        own[..., 0] = np.where(closer, cy_, own[..., 0])
        own[..., 1] = np.where(closer, cx_, own[..., 1])
        d1 = np.where(closer, dd, d1)
oy_, ox_ = own[..., 0], own[..., 1]
sxo, syo = (ox_ + jit[oy_, ox_, 0]) * PL, (oy_ + jit[oy_, ox_, 1]) * PL
plate = lift[oy_, ox_] + grade[oy_, ox_] * ((XM - sxo) * np.cos(ang[oy_, ox_]) + (YM - syo) * np.sin(ang[oy_, ox_]))
crack = (d2s - d1) < 4.0
rim_clear = np.hypot(XM - main[sec_of(2)[0], 0], YM - main[sec_of(2)[0], 1]) > 450
slab_zone = (d2 > 45) & (d2 < 650) & (fbm(XM + 13, YM - 7, 400, 2) > -0.15) & rim_clear
H = np.where(slab_zone, H + np.where(crack, -3.0, np.maximum(plate, 1.0)), H)
del d1, d2s, own
sk = branches["S2 SKILL Lajes"]
sp_ = sk["p"]
blocks = []
s_at, top_z = 60.0, None
while s_at < len(sp_) - 80:
    ln = float(rng.uniform(60, 110))
    i0_, i1_ = int(s_at), int(min(len(sp_) - 60, s_at + ln))
    blocks.append((i0_, i1_))
    s_at = i1_ + float(rng.uniform(25, 40))
dS, iS = nearest(sp_[::4], 80)
latS = lateral(sp_[::4], iS)
along = iS * 4
sk_z = np.interp(np.arange(len(sp_)), [0, len(sp_) - 1], [sk["z"][0], sk["z"][-1]])
for b0, b1 in blocks:
    on = (along >= b0) & (along <= b1) & (dS < sk["w"] + 6) & (iS >= 0)
    rise = 5.0 + 7.0 * (along - b0) / max(1, b1 - b0)  # each slab tilts up towards its far edge: a ramp, then the gap
    H = np.where(on, np.maximum(H, sk_z[np.clip(along, 0, len(sp_) - 1)] + rise), H)
print("SLABS", len(blocks))

def bilinear(grid, x, y):
    fx, fy = np.clip(np.asarray(x) / CELL, 0, NX - 1.001), np.clip(np.asarray(y) / CELL, 0, NY - 1.001)
    j, i = fx.astype(int), fy.astype(int)
    tx, ty = fx - j, fy - i
    return (grid[i, j] * (1 - tx) + grid[i, j + 1] * tx) * (1 - ty) + (grid[i + 1, j] * (1 - tx) + grid[i + 1, j + 1] * tx) * ty


# 5g. Dunes in the eastern basin, crests across the eastbound line (wind from the west: the windward side faces the
# craft, the slip face drops away: jumps).
dune_zone = smoothstep(2300.0, 2900.0, XM) * smoothstep(6200.0, 5600.0, XM) * smoothstep(1900.0, 1500.0, YM) * \
    smoothstep(150.0, 600.0, d_basin * 0 + YM) * basin
lam = 260.0
ph = (XM + 60.0 * fbm(XM, YM, 500, 2)) / lam
fr = ph - np.floor(ph)
dune = (14.0 + 10.0 * np.clip(0.5 + fbm(XM + 77, YM, 700, 2), 0, 1)) * np.where(fr < 0.82, (fr / 0.82) ** 1.5, (1.0 - fr) / 0.18)
H = np.maximum(H, np.where(dune_zone > 0, basin_z + dune * dune_zone, H))

# 5h. Landmarks, placed one by one (stout: height at most ~1.6x the diameter; no thin needles).
def column(cx_, cy_, r, h, base):
    d = np.hypot(XM - cx_, YM - cy_)
    rr = r * (1.0 + 0.1 * fbm(XM, YM, 12, 1))
    body = smoothstep(rr + 3.0, rr - 3.0, d) * h * (1.0 - 0.12 * smoothstep(0, rr, d))
    cone = np.maximum(0.0, 0.25 * h - (d - rr) * 0.6) * smoothstep(rr * 3, rr, d)
    rise = np.maximum(body, cone)
    return np.where(rise > 0.01, base + rise, -1e9)  # only where the column stands


LANDMARKS = []
# The Sentinels: twin towers at the confluence J, seen from the Shafer rim and down the Red Wall.
for (ox, oy), r, h in (((260, -180), 90, 270), ((430, -40), 70, 220)):
    cx_, cy_ = J[0] + ox, J[1] + oy
    H = np.maximum(H, column(cx_, cy_, r, h, float(bilinear(H, cx_, cy_))))
    LANDMARKS.append({"name": "Sentinel", "x": cx_, "y": cy_, "r": r, "h": h})
# Buttes on the plateau, ahead of the long S1 straights.
for cx_, cy_, r, h in ((12900, 9700, 160, 140), (14700, 9200, 120, 110), (12100, 8300, 200, 90)):
    H = np.maximum(H, column(cx_, cy_, r, h, float(bilinear(H, cx_, cy_)) - 5))
    LANDMARKS.append({"name": "Butte", "x": cx_, "y": cy_, "r": r, "h": h})
# Hoodoo slalom in the desert (S9): stout columns alternating sides of the line.
s9i = sec_of(8)
for k_, frac in enumerate(np.linspace(0.12, 0.32, 7)):
    i = s9i[int(frac * (len(s9i) - 1))]
    t_ = np.gradient(main, axis=0)[i]
    n_ = np.array([-t_[1], t_[0]]) / (np.linalg.norm(t_) + 1e-9)
    cx_, cy_ = main[i] + n_ * (half_w[i] + 28.0) * (1 if k_ % 2 else -1)
    H = np.maximum(H, column(cx_, cy_, 16, 30 + 6 * (k_ % 3), float(bilinear(H, cx_, cy_)) - 2))
    LANDMARKS.append({"name": "Hoodoo", "x": float(cx_), "y": float(cy_), "r": 16, "h": 30 + 6 * (k_ % 3)})

# 5f. The route bed. Design heights on the canyon sectors; on the plateau and in the desert the bed follows the
# ground (smoothed), so the plateau rolls and the dunes throw the craft.
follow = np.isin(kind, ["top", "desert"])
ground = bilinear(H, main[:, 0], main[:, 1])
bed = np.where(follow, smooth1d(ground, 301) - np.where(kind == "top", 8.0, 0.0), zmain)
# Where a designed sector follows a ground-following one (plateau -> Shafer, desert -> White Rim), its heights are
# shifted to start where the other ends, the shift fading out over 700 m.
for k in range(1, len(SECTORS)):
    ii = np.flatnonzero(sec == k)
    jj = np.flatnonzero(sec == k - 1)
    if len(ii) and len(jj) and follow[jj[-1]] and not follow[ii[0]]:
        delta = bed[jj[-1]] - bed[ii[0]]
        bed[ii] += delta * smoothstep(700.0, 0.0, np.arange(len(ii), dtype=float))
bed = smooth1d(bed, 151)
cave_end = sec_of(7)[-1]
bed[cave_end - 40:cave_end + 1] = zmain[cave_end - 40:cave_end + 1]  # the cave mouth stands above the basin: exit jump
# Designed jumps on the main line (GDD 17.7, all natural): slab lips on the plateau (flow jumps), broken-slab steps on
# Broken Mesa, dry waterfalls (pour-offs) in the Red Wall gorge and the Wash. The bed rises gently over `ramp` m to
# the lip and drops by `drop` m there; each is put where the line runs nearly straight, so the landing is in view.
JUMPS_DESIGN = [(0, 0.22, 2.0, 120), (0, 0.50, 2.5, 140), (0, 0.78, 3.0, 160), (1, 0.35, 5.0, 220), (1, 0.70, 6.0, 240),
                (3, 0.42, 10.0, 300), (3, 0.72, 12.0, 320), (6, 0.30, 4.0, 200), (6, 0.55, 5.0, 220), (6, 0.80, 4.0, 200)]
k_abs = np.abs(curvature(main, 61))
lips = []
for k, frac, drop, ramp in JUMPS_DESIGN:
    ii = sec_of(k)
    c = ii[int(frac * (len(ii) - 1))]
    win = np.arange(max(ii[0] + ramp, c - 200), min(ii[-1] - 150, c + 200))
    if len(win):
        c = int(win[np.argmin(k_abs[win])])
    rise = drop * smoothstep(c - ramp, c, np.arange(N, dtype=float)) * (np.arange(N) <= c)
    rise[max(0, c - 15):c + 1] += 1.0  # a 1 m kicker on the lip
    bed = bed + rise
    lips.append(c)
# Red Wall bank: on the outside of the long left-hand sweep the floor banks up, 8 -> 50 degrees along the sector.
curv = curvature(main, 61)
s4 = sec_of(3)
bank = np.zeros(N)
bank[s4] = np.radians(8.0 + 42.0 * smoothstep(0.0, 1.0, np.linspace(0, 1, len(s4))))
# Hero jump (S10): a ravine across the line, the far lip 6 m lower; a 3 m kicker before it.
i_hero = at_main(9000, 2600)
hero_t = np.gradient(main, axis=0)[i_hero]
hero_t /= np.linalg.norm(hero_t)
hero_n = np.array([-hero_t[1], hero_t[0]])
rv_s = (XM - main[i_hero, 0]) * hero_t[0] + (YM - main[i_hero, 1]) * hero_t[1]
rv_l = (XM - main[i_hero, 0]) * hero_n[0] + (YM - main[i_hero, 1]) * hero_n[1]
ravine = (np.abs(rv_s) < 45 * smoothstep(380, 150, rv_l) + 8 * fbm(XM, YM, 40, 1)) & (rv_l > -400) & (rv_l < 380)
H = np.where(ravine, np.minimum(H, basin_z + 4.0 + (np.maximum(rv_l, 0) * 0.15)), H)
bed[i_hero - 60:i_hero - 45] += np.linspace(0, 3.0, 15)
bed[i_hero - 45:i_hero - 40] += 3.0
bed[i_hero + 45:i_hero + 260] -= 6.0 * smoothstep(0, 1, np.linspace(1, 0, 215))
gap = (np.arange(N) > i_hero - 40) & (np.arange(N) < i_hero + 45)


def section(lat, idx, bed_, w_, kinds_, bank_, curv_):
    """Target ground across the route: floor shape by surface kind (GDD profiles)."""
    u = np.abs(lat)
    t = np.clip(u / w_, 0, 1.5)
    z = bed_.copy()
    z += np.where(kinds_ == "top", 6.0 * t ** 2, 0.0)  # a natural wash between the domes
    z += np.where(kinds_ == "floor", 4.0 * t ** 2, 0.0)
    z += np.where(kinds_ == "wash", 16.0 * t ** 2, 0.0)  # the Wash: a half-pipe riverbed
    z += np.where(kinds_ == "rim", 1.0 * t ** 2, 0.0)
    outer = np.sign(lat) == -np.sign(curv_)  # outside of the bend
    z += np.where((bank_ > 0) & outer, u * np.tan(bank_), 0.0)
    return z


def carve(pts, bed_, w_, kinds_, bank_, curv_, skip=None, margin=30.0, fill=True):
    global H
    sub = pts[::2]
    d, idx = nearest(sub, float(np.max(w_)) + margin + 20)
    ok = idx >= 0
    i = np.maximum(idx, 0) * 2
    i = np.clip(i, 0, len(pts) - 1)
    lat = lateral(sub, idx)
    wv = w_[i]
    tgt = section(lat, i, bed_[i], wv, kinds_[i], bank_[i], curv_[i])
    sk_ = np.zeros(d.shape, bool) if skip is None else skip[i]
    inside = ok & (d <= wv) & ~sk_
    H = np.where(inside, tgt, H)
    if fill:
        shoulder = tgt - (d - wv) * math.tan(math.radians(34.0))
        rim_ = ok & (d > wv) & (d < wv + margin) & ~sk_ & (H < shoulder)
        H = np.where(rim_, shoulder, H)


skip = gap | (kind == "desert")  # the hero gap stays open; the desert is driven as it is
H_rock = H.copy()  # the ground before any line was cut (cave roofs follow it)
for name, b in branches.items():
    n_ = len(b["p"])
    bk = np.full(n_, {"slot": "floor", "slabs": "top", "cave": "floor", "surface": "rim"}[b["kind"]])
    if b["kind"] == "surface":
        continue
    bz = b["z"].copy()
    if name == "S6 SKILL Istmo":  # up through the neck in a slot, then off its wall onto the floor beyond (drop jump)
        bz = np.where(np.arange(n_) < 0.85 * n_, np.interp(np.arange(n_), [0, 0.85 * n_], [b["z"][0], 62.0]), b["z"][-1])
    if name == "S5 SKILL Fenda Estreita":  # a 7 m step down halfway along the slot
        bz = bz + np.where(np.arange(n_) < n_ // 2, 7.0, 0.0)
    if b["kind"] == "slabs":
        continue
    carve(b["p"], bz, np.full(n_, b["w"]), bk, np.zeros(n_), curvature(b["p"], 61), fill=False)
    b["z"] = bz
    if b["kind"] == "slot":  # slot walls: near vertical from the floor edge up to the ground
        d, idx = nearest(b["p"][::2], b["w"] + 40)
        wall = b["z"][np.clip(np.maximum(idx, 0) * 2, 0, n_ - 1)] + (d - b["w"]) * math.tan(math.radians(80.0))
        H = np.where((idx >= 0) & (d > b["w"]) & (d < b["w"] + 40), np.minimum(H, wall), H)
carve(main, bed, half_w, kind, bank, curv, skip=skip)  # last, so no branch lifts the main line at a junction
print("ROUTE CARVED", "lips", len(lips))

# 5i. Lone spikes go (they render as sharp cones).
# Three passes: a small cluster of spikes loses its outer cells first, then the rest.
n_spk = 0
for _ in range(3):
    nb = np.sort(np.stack([np.roll(np.roll(H, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]), axis=0)
    spk = H - nb[-2] > 6.0
    n_spk += int(spk.sum())
    H = np.where(spk, nb[-2] + 1.0, H)
    del nb
print("TERRAIN DONE", round(float(H.min()), 1), round(float(H.max()), 1), "spikes", n_spk)

# ---- 6. Jumps along every route (flight of a craft at ~400 km/h whose hover pulls it down at 20 m/s2).
def find_jumps(p, speed=None, g=20.0, skip=None):
    """Where the ground falls away from under the craft at its race speed (speed model; 110 m/s if none): it flies
    from the slope of the last 30 m until it meets the ground again."""
    z = bilinear(H, p[:, 0], p[:, 1])
    out, i, n = [], 30, len(z)
    while i < n - 10:
        if skip is not None and skip[i]:
            i += 1
            continue
        v = float(speed[i]) if speed is not None else 110.0
        sl = float(np.clip((z[i] - z[i - 30]) / 30.0, -0.3, 0.2))
        if z[i] + sl * 6.0 - z[i + 6] > 2.5:
            j = i + 1
            while j < n:
                t = (j - i) / v
                if z[i] + v * sl * t - 0.5 * g * t * t <= z[j]:
                    break
                j += 1
            if j - i >= 20:
                tt = np.arange(j - i) / v
                out.append({"s": int(i), "at": [round(float(p[i, 0]), 1), round(float(p[i, 1]), 1)], "length_m": int(j - i),
                            "drop_m": round(float(z[i] - z[min(j, n - 1)]), 1),
                            "height_m": round(float(np.max(z[i] + v * sl * tt - 0.5 * g * tt * tt - z[i:j])), 1)})
            i = j + 1
        else:
            i += 1
    return out


cave_main = kind == "cave"
jumps = find_jumps(main, speed=vel, skip=cave_main)
for b in branches.values():
    b["jumps"] = find_jumps(b["p"], skip=np.full(len(b["p"]), b["kind"] == "cave"))
for k, (nm, *_r) in enumerate(SECTORS):
    js_ = [j_ for j_ in jumps if sec[j_["s"]] == k]
    print("  JUMPS %-16s %2d  %s" % (nm, len(js_), sorted([(j_["length_m"], j_["drop_m"]) for j_ in js_], reverse=True)[:6]))
prof = bilinear(H, main[:, 0], main[:, 1])
off_bed = np.abs(prof - bed)
for k, (nm, *_r) in enumerate(SECTORS):
    ii = np.flatnonzero((sec == k) & (kind != "desert") & ~gap)
    if len(ii):
        bad = ii[off_bed[ii] > 3.0]
        print("  BED %-16s off>3m: %5d pts, max %.1f m %s" % (nm, len(bad), off_bed[ii].max(),
              [(int(main[b_, 0]), int(main[b_, 1]), round(float(prof[b_] - bed[b_]), 1)) for b_ in bad[::max(1, len(bad) // 5)][:5]]))
for j_ in sorted(jumps, key=lambda j_: -j_["length_m"])[:6]:
    print("  BIGJUMP", SECTORS[sec[j_["s"]]][0], j_)
np.savez_compressed(f"{OUT}/ab_profile.npz", main=main, bed=bed, prof=prof, sec=sec, vel=vel)
print("JUMPS main", len(jumps), "longest", max([j_["length_m"] for j_ in jumps] or [0]),
      {n_: len(b["jumps"]) for n_, b in branches.items()})


# ---- 7. Plan with relief (10 m per pixel, north up): floor sand, White Rim bench pale, plateau Navajo, cliffs red;
# the route by sector, branches white, jumps as white dots, start white square, finish black.
def relief_plan(path, mpp=10.0):
    s_ = int(round(mpp / CELL)) or 1
    Hs = H[::s_, ::s_]
    gy, gx = np.gradient(Hs, s_ * CELL)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    stops = [(0, (0.86, 0.68, 0.46)), (90, (0.84, 0.64, 0.42)), (200, (0.80, 0.52, 0.34)), (235, (0.88, 0.82, 0.70)),
             (260, (0.86, 0.78, 0.64)), (400, (0.82, 0.58, 0.40)), (470, (0.90, 0.74, 0.56)), (700, (0.70, 0.50, 0.38))]
    zs = np.array([t[0] for t in stops], float)
    col = np.stack([np.interp(Hs, zs, [t[1][c] for t in stops]) for c in range(3)], -1)
    col = np.where((slope > 35)[..., None], np.array([0.62, 0.26, 0.12]) * (0.8 + 0.2 * (Hs / 500.0))[..., None], col)
    shade = 0.55 + 0.45 * np.clip(0.5 + (-gx + gy) * 0.6, 0, 1)
    img = np.clip(col * shade[..., None], 0, 1).astype(np.float32)
    hgt, wid = Hs.shape

    def draw(pts, c, r):
        ix, iy = (pts[:, 0] / (s_ * CELL)).astype(int), (pts[:, 1] / (s_ * CELL)).astype(int)
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                ok = (ix + dx >= 0) & (ix + dx < wid) & (iy + dy >= 0) & (iy + dy < hgt)
                img[iy[ok] + dy, ix[ok] + dx] = c

    for b in branches.values():
        draw(b["p"][::3], (1.0, 1.0, 1.0), 1)
    for k in range(len(SECTORS)):
        draw(main[sec == k][::3], SECTOR_COLS[k], 2)
    for j_ in jumps + [jj for b in branches.values() for jj in b["jumps"]]:
        draw(np.array([j_["at"]]), (1.0, 1.0, 1.0), 4)
    draw(main[:1], (1, 1, 1), 8)
    draw(main[-1:], (0, 0, 0), 8)
    out = bpy.data.images.new("relief", wid, hgt)
    out.pixels.foreach_set(np.concatenate([img, np.ones((hgt, wid, 1), np.float32)], -1).ravel())
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()


relief_plan(f"{OUT}/ab_relief.png")


def write_png(path, data, bits, channels):
    h_, w_ = data.shape[:2]
    raw = (data.astype(">u2") if bits == 16 else data.astype(np.uint8)).reshape(h_, w_ * channels).tobytes()
    stride = w_ * channels * (2 if bits == 16 else 1)
    rows = b"".join(b"\x00" + raw[r * stride:(r + 1) * stride] for r in range(h_))

    def chunk(kind_, payload):
        return struct.pack(">I", len(payload)) + kind_ + payload + struct.pack(">I", zlib.crc32(kind_ + payload) & 0xFFFFFFFF)

    with open(path, "wb") as f_:
        f_.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w_, h_, bits, 0 if channels == 1 else 2, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


zlo, zhi = float(H.min()), float(H.max())
write_png(f"{OUT}/ab_height16.png", np.round((H - zlo) / (zhi - zlo) * 65535)[::-1], 16, 1)
print("RELIEF", f"{OUT}/ab_relief.png", "z", round(zlo, 1), round(zhi, 1))
# Route for Unreal (metres from the world centre; one point every 4 m): position, ground, floor half width, bank on the
# outside of the bend (degrees), sector, model speed; branches, jumps, designed lips, landmarks; and a mask for the
# landscape material: R slope (0-90 deg), G on a line, B layer (64 basin/floor, 128 bench, 192 plateau, 255 cliff).
def pts4(p, z):
    return [[round(float(x_ - SX / 2), 1), round(float(y_ - SY / 2), 1), round(float(z_), 1)] for (x_, y_), z_ in zip(p[::4], z[::4])]


route_json = {
    "note": "RED DUST DIVIDE expedition A->B. Metres from the world centre, x east, y north; heightmap " + "ab_height16.png "
            "spans z_m; Unreal Z scale (%) = (z_max - z_min) * 100 / 512.",
    "cell_m": CELL, "size_m": [SX, SY], "z_m": [round(zlo, 1), round(zhi, 1)],
    "time_model": {"vmax_kmh": 550, "corner_200kmh_radius_m": 120, "ideal_time_s": round(float(t_cum[-1]), 1),
                   "length_m": int(N)},
    "sectors": [{"name": nm, "kind": kd, "from_m": int(sec_of(k)[0]), "to_m": int(sec_of(k)[-1]),
                 "start_s": round(float(t_cum[sec_of(k)[0]]), 1)} for k, (nm, kd, *_r) in enumerate(SECTORS)],
    "main": {"points": pts4(main, bilinear(H, main[:, 0], main[:, 1])), "half_width_m": [round(float(v_), 1) for v_ in half_w[::4]],
             "bank_deg": [round(float(np.degrees(v_)), 1) for v_ in bank[::4]], "sector": [int(v_) for v_ in sec[::4]],
             "speed_kmh": [int(v_ * 3.6) for v_ in vel[::4]]},
    "branches": {nm: {"kind": b["kind"], "half_width_m": b["w"], "leaves_main_at_m": int(b["leave"]), "rejoins_main_at_m": int(b["rejoin"]),
                      "points": pts4(b["p"], bilinear(H, b["p"][:, 0], b["p"][:, 1])), "jumps": b["jumps"]} for nm, b in branches.items()},
    "jumps": jumps, "lips_m": [int(c) for c in lips], "hero_jump_m": int(i_hero), "landmarks": LANDMARKS,
    "start_grid": {"at": [round(float(main[0, 0] - SX / 2), 1), round(float(main[0, 1] - SY / 2), 1)], "rows": 4, "per_row": 5},
}
with open(f"{OUT}/ab_route.json", "w") as f_:
    json.dump(route_json, f_, default=float)
gy_m, gx_m = np.gradient(H, CELL)
slope_m = np.degrees(np.arctan(np.hypot(gx_m, gy_m)))
d_l, i_l = nearest(main[::4], 60)
line_m = (i_l >= 0) & (d_l < half_w[np.clip(np.maximum(i_l, 0) * 4, 0, N - 1)] + 2)
layer = np.where(H < 160, 64, np.where(H < 330, 128, 192))
layer = np.where(slope_m > 40, 255, layer)
mask = np.stack([np.clip(slope_m / 90 * 255, 0, 255), line_m * 255, layer], -1)
write_png(f"{OUT}/ab_mask.png", mask[::-1], 8, 3)
print("UNREAL ab_height16.png ab_mask.png ab_route.json")
if "noshots" in a:
    raise SystemExit

# ---- 8. Into Blender: the terrain with colours, cave roofs, rocks and plants, the craft for scale, then pictures.
import bmesh
from mathutils import Euler, Vector

opts = dict(v.split("=", 1) for v in a if "=" in v)
KIT, PLANTS, SHIP = opts.get("kit", ""), opts.get("plants", ""), opts.get("ship", "")
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
hx, hy = SX / 2, SY / 2
gy_, gx_ = np.gradient(H, CELL)
slope = np.degrees(np.arctan(np.hypot(gx_, gy_)))
d_tr, i_tr = nearest(main[::4], 80)
on_track = (i_tr >= 0) & (d_tr < half_w[np.clip(np.maximum(i_tr, 0) * 4, 0, N - 1)] + 1.0)
for b in branches.values():
    d_b, i_b = nearest(b["p"][::4], 60)
    on_track |= (i_b >= 0) & (d_b < b["w"] + 1.0)


def punch(c):
    c = np.asarray(c, np.float32)
    return np.clip(c.mean() + (c - c.mean()) * 1.25, 0, 1)


sand, bench_c, navajo = punch((0.80, 0.55, 0.33)), punch((0.80, 0.72, 0.58)), punch((0.84, 0.58, 0.38))
wall, varnish, dune_c = punch((0.60, 0.24, 0.10)), punch((0.30, 0.13, 0.07)), punch((0.86, 0.60, 0.34))
track_c = punch((0.66, 0.44, 0.28))
steep = smoothstep(32, 55, slope)[..., None]
beds = (0.82 + 0.18 * (np.sin(H / 3.1 + 1.4 * fbm(XM, YM, 160, 2)) * 0.5 + 0.5) ** 3)[..., None]
band_w = smoothstep(150, 200, H) * smoothstep(300, 260, H)  # the White Rim layer
ground_c = sand * (1 - smoothstep(380, 430, H))[..., None] + navajo * smoothstep(380, 430, H)[..., None]
ground_c = ground_c * (1 - band_w[..., None]) + bench_c * band_w[..., None]
ground_c = np.where(((d_basin <= 0) & (H < basin_z + 40))[..., None], dune_c * (0.9 + 0.1 * fbm(XM, YM, 60, 2))[..., None], ground_c)
streak = smoothstep(0.2, 0.6, fbm(XM, YM, 9, 2))[..., None]
wall_col = wall * beds
wall_col = wall_col * (1 - band_w[..., None] * 0.5) + bench_c * band_w[..., None] * 0.5
wall_col = wall_col + (varnish - wall_col) * streak * 0.45
col = ground_c * (1 - steep) + wall_col * steep
col = np.where(on_track[..., None] & (steep < 0.5), col * 0.6 + track_c * 0.4, col)
col *= (0.92 + 0.08 * fbm(XM, YM, 20, 2))[..., None]
col = np.clip(col, 0, 1)

me = bpy.data.meshes.new("Expedition")
me.vertices.add(NX * NY)
me.vertices.foreach_set("co", np.stack([XM - hx, YM - hy, H], -1).astype(np.float32).ravel())
idx_ = np.arange(NX * NY, dtype=np.int32).reshape(NY, NX)
quads = np.stack([idx_[:-1, :-1], idx_[:-1, 1:], idx_[1:, 1:], idx_[1:, :-1]], -1).ravel()
me.loops.add(len(quads))
me.loops.foreach_set("vertex_index", quads)
me.polygons.add((NX - 1) * (NY - 1))
me.polygons.foreach_set("loop_start", np.arange(0, len(quads), 4, dtype=np.int32))
me.update(calc_edges=True)
me.polygons.foreach_set("use_smooth", np.ones((NX - 1) * (NY - 1), bool))
del quads, idx_
ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
ca.data.foreach_set("color", np.concatenate([col.reshape(-1, 3), np.ones((NX * NY, 1), np.float32)], 1).ravel())
mat = bpy.data.materials.new("M_Expedition")
mat.use_nodes = True
at_ = mat.node_tree.nodes.new("ShaderNodeAttribute")
at_.attribute_name = "Col"
mat.node_tree.links.new(at_.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.92
me.materials.append(mat)
terrain = bpy.data.objects.new("Expedition", me)
scene.collection.objects.link(terrain)
print("MESH", NX, NY)

# Cave roofs (The Hollow): rock over the opened cave floor, its top following the ground that was there, its
# underside a rough vault 14-26 m clear; skylights (gaps in the roof) every ~250 m let shafts of sun in.
os.makedirs(f"{OUT}/caves", exist_ok=True)
caves = []


def cave_roof(name, p, w, bedv):
    w = np.broadcast_to(np.asarray(w, float), (len(p),))
    t = np.gradient(p, axis=0)
    t /= np.hypot(t[:, 0], t[:, 1])[:, None] + 1e-9
    nx_, ny_ = -t[:, 1], t[:, 0]
    q = np.arange(0, len(p), 3)
    L = np.linspace(-1.0, 1.0, 41)
    ww = w[q][:, None] + 4.0
    x2 = p[q, None, 0] + L[None, :] * ww * nx_[q, None]
    y2 = p[q, None, 1] + L[None, :] * ww * ny_[q, None]
    rough = 6.0 * fbm(x2.astype(np.float32), y2.astype(np.float32), 30, 2)
    vault = 14.0 + 8.0 * np.clip(w[q] / 30.0, 0, 1)[:, None] + rough
    under = bedv[q, None] + np.where(np.abs(L)[None, :] < 0.95, vault * np.sqrt(np.maximum(0.0, 1.0 - L[None, :] ** 2)) + 2.0, -1.0)
    top = np.maximum(bilinear(H_rock, x2, y2) + 0.15, under + 4.0)
    ns, nl = top.shape
    verts = np.concatenate([np.stack([x2 - hx, y2 - hy, top], -1).reshape(-1, 3), np.stack([x2 - hx, y2 - hy, under], -1).reshape(-1, 3)])
    sky = (np.arange(ns) * 3 % 150) < 12  # skylight rows
    faces = []
    T = lambda i, j: i * nl + j
    B = lambda i, j: ns * nl + i * nl + j
    for i in range(ns - 1):
        for j in range(nl - 1):
            if sky[i] and 14 <= j <= 26:
                continue
            faces.append((T(i, j), T(i + 1, j), T(i + 1, j + 1), T(i, j + 1)))
            faces.append((B(i, j), B(i, j + 1), B(i + 1, j + 1), B(i + 1, j)))
        for j in (0, nl - 1):
            faces.append((T(i, j), B(i, j), B(i + 1, j), T(i + 1, j)))
    rme = bpy.data.meshes.new(name)
    rme.from_pydata(verts.tolist(), [], faces)
    bm = bmesh.new()
    bm.from_mesh(rme)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(rme)
    bm.free()
    rcol = np.concatenate([np.stack([bilinear(col[..., c_], x2, y2).ravel() for c_ in range(3)], 1),
                           np.tile(wall * 0.8, (ns * nl, 1))])
    rattr = rme.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    rattr.data.foreach_set("color", np.concatenate([rcol, np.ones((len(verts), 1))], 1).astype(np.float32).ravel())
    rme.materials.append(mat)
    ob = bpy.data.objects.new(name, rme)
    scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=f"{OUT}/caves/{name}.fbx", use_selection=True, object_types={"MESH"})
    caves.append({"name": name, "length_m": int(len(p))})


cv = sec_of(7)
cave_roof("SM_Cave_Hollow", main[cv], half_w[cv], bilinear(H, main[cv, 0], main[cv, 1]))
cb = branches["S8 Braço da Caverna"]
cave_roof("SM_Cave_Hollow_Arm", cb["p"], cb["w"], bilinear(H, cb["p"][:, 0], cb["p"][:, 1]))
print("CAVES", caves)


# Props. The molds we have (our kit, the Phase 2b sculpted rocks, the S01 pieces) dress the map by zone, each copy
# with its own size, yaw, tilt and slightly uneven scale, sunk a little into the ground, never on a line:
#  - cliff faces (SM_Cliff_*) at the foot of every wall seen from the line, facing it: the walls stop reading smooth;
#  - talus clusters: one big block with smaller ones round it, on the debris slopes under the walls;
#  - loose stones on the floors; slickrock slabs lying with the ground on the bench and the plateau;
#  - fins and towers in the desert; mesas, buttes and spires as landmarks further off (spires widened: no needles);
#  - the kit's arches over the Arches Run line, a balanced rock at the head of the Red Wall, Mesa Arch at the finish;
#  - plants as before (no collision in the game).
MOLDS = opts.get("molds", KIT)


def load(folder, name):
    path_ = os.path.join(folder, name + ".fbx")
    if not folder or not os.path.exists(path_):
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path_)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    for o in [o for o in bpy.data.objects if o not in before]:
        if o not in new[:1]:
            bpy.data.objects.remove(o)
    if not new:
        return None
    o = new[0]
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    data = o.data
    bpy.data.objects.remove(o)
    return data


# Preview materials: banded sandstone for the rocks (by object), vertex colours for the plants.
rockmat = bpy.data.materials.new("M_RockPreview")
rockmat.use_nodes = True
rnt = rockmat.node_tree
rbs = rnt.nodes["Principled BSDF"]
tc = rnt.nodes.new("ShaderNodeTexCoord")
nz = rnt.nodes.new("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 0.6
ramp = rnt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (*(wall * 0.85), 1)
ramp.color_ramp.elements[1].color = (*(np.array(navajo) * 0.95), 1)
rnt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
rnt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
rnt.links.new(ramp.outputs["Color"], rbs.inputs["Base Color"])
rbs.inputs["Roughness"].default_value = 0.9
woodmat = bpy.data.materials.new("M_Wood")
woodmat.use_nodes = True
woodmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.32, 0.24, 0.18, 1)
plantmat = bpy.data.materials.new("M_Plant")
plantmat.use_nodes = True
pat = plantmat.node_tree.nodes.new("ShaderNodeAttribute")
pat.attribute_name = "Col"
plantmat.node_tree.links.new(pat.outputs["Color"], plantmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
props = []
src = {}
HEIGHT_OF = {}  # mold height (m), for fitting cliff faces to walls


def mold(name):
    if name not in src:
        is_plant = name in ("SM_Juniper_A", "SM_Juniper_B", "SM_Sagebrush", "SM_DryGrass", "SM_DeadBrush", "SM_Yucca",
                            "SM_PricklyPear", "SM_Cottonwood_A", "SM_Cottonwood_B", "SM_GreenGrass", "SM_Willow",
                            "SM_Saguaro_A", "SM_Saguaro_B", "SM_BarrelCactus", "SM_Cholla", "SM_JoshuaTree",
                            "SM_DeadTree_A", "SM_DeadTree_B")
        data = load(PLANTS if is_plant else MOLDS, name) or (None if is_plant else load(KIT, name))
        if data is not None:
            data.materials.clear()
            data.materials.append(plantmat if is_plant else (woodmat if "Dead" in name else rockmat))
            zs_ = [v.co.z for v in data.vertices]
            HEIGHT_OF[name] = max(zs_) - min(zs_)
        src[name] = data
    return src[name]


def place(name, x, y, z, rot_deg, scale_xyz, group):
    """rot_deg: (x, y, z) Euler in degrees; scale_xyz: per-axis scale."""
    data = mold(name)
    sx, sy, sz = scale_xyz
    props.append({"mesh": name, "group": group, "x": round(float(x - hx), 2), "y": round(float(y - hy), 2), "z": round(float(z), 2),
                  "rot": [round(float(r), 1) for r in rot_deg], "scale": [round(float(sx), 3), round(float(sy), 3), round(float(sz), 3)],
                  "yaw": round(float(rot_deg[2]), 1)})
    if data is not None:
        o = bpy.data.objects.new(f"Prop_{group}_{len(props)}", data)
        o.location = (x - hx, y - hy, z)
        o.rotation_euler = Euler([math.radians(r) for r in rot_deg])
        o.scale = (sx, sy, sz)
        scene.collection.objects.link(o)


def heading(i, p=main):
    t = np.gradient(p, axis=0)[i]
    return math.degrees(math.atan2(t[1], t[0]))


def ground_tilt(x, y, yaw_deg, follow=1.0, jitter=0.0):
    """Euler (deg) that lays an object on the ground's slope (follow 0..1) with some random tilt, then turns it."""
    i = int(np.clip(y / CELL, 1, NY - 2))
    j = int(np.clip(x / CELL, 1, NX - 2))
    nrm = Vector((-float(gx_[i, j]) * follow, -float(gy_[i, j]) * follow, 1.0)).normalized()
    q = Vector((0, 0, 1)).rotation_difference(nrm) @ Euler((math.radians(prng.normal(0, jitter)), math.radians(prng.normal(0, jitter)),
                                                            math.radians(yaw_deg))).to_quaternion()
    e = q.to_euler()
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


prng = np.random.default_rng(77)
# Distance to every line (main and branches) and the floor half width there: nothing is put on a line.
d_main, i_main = nearest(main[::4], 400)
w_main = np.where(i_main >= 0, half_w[np.clip(np.maximum(i_main, 0) * 4, 0, N - 1)], 20.0)
free_d = d_main - w_main
for b in branches.values():
    d_b, i_b = nearest(b["p"][::4], 120)
    free_d = np.minimum(free_d, np.where(i_b >= 0, d_b - b["w"], 1e6))


def clear_at(x, y, need):
    return float(free_d[int(np.clip(y / CELL, 0, NY - 1)), int(np.clip(x / CELL, 0, NX - 1))]) > need


# 1. Signature pieces on the line.
s9 = sec_of(8)
arch_at = []
for frac in (0.46, 0.60, 0.74):  # the line runs through each opening (the arch's local y along the line)
    i = s9[int(frac * (len(s9) - 1))]
    place("SM_Kit_Arch", main[i, 0], main[i, 1], float(bilinear(H, main[i, 0], main[i, 1])) - 1.0, (0, 0, heading(i) - 90.0), (4.5,) * 3, "arch")
    arch_at.append(i)
i_br = sec_of(3)[0] + 260
t_ = np.gradient(main, axis=0)[i_br]
n_ = np.array([-t_[1], t_[0]]) / np.linalg.norm(t_)
bx, by = main[i_br] + n_ * (half_w[i_br] + 45.0)
place("SM_Kit_TableRock", bx, by, float(bilinear(H, bx, by)) - 1.0, (0, 0, 30.0), (3.4, 3.4, 3.6), "landmark")
fx_, fy_ = main[N - 40]
place("SM_Kit_Arch", fx_, fy_, float(bilinear(H, fx_, fy_)) - 1.0, (0, 0, heading(N - 40) - 90.0), (6.5,) * 3, "finish")

# 2. Cliff faces at the foot of the walls seen from the line, facing it, sunk into the wall and the ground.
CLIFFS = ["SM_Cliff_A", "SM_Cliff_B", "SM_Cliff_C"]
walled = np.isin(kind, ["gorge", "floor", "wash", "switchback", "rim", "desert"])
n_cliff = 0
step_i = 70
tg = np.gradient(main, axis=0)
tg /= np.hypot(tg[:, 0], tg[:, 1])[:, None]
for i in range(60, N - 60, step_i):
    if not walled[i]:
        continue
    nrm2 = np.array([-tg[i, 1], tg[i, 0]])
    for side in (1.0, -1.0):
        if prng.random() < 0.25:
            continue
        foot = None
        for l in np.arange(half_w[i] + 12.0, 320.0, 5.0):
            q = main[i] + nrm2 * side * l
            if not (0 < q[0] < SX and 0 < q[1] < SY):
                break
            if slope[int(q[1] / CELL), int(q[0] / CELL)] > 48.0:
                foot = (q, l)
                break
        if foot is None:
            continue
        q, l = foot
        zf = float(bilinear(H, q[0], q[1]))
        rim_ = max(float(bilinear(H, *(q + nrm2 * side * k))) for k in range(0, 200, 10))
        wall_h = rim_ - zf
        if wall_h < 25.0:
            continue
        name = CLIFFS[int(prng.integers(3))]
        mold(name)
        mh = HEIGHT_OF.get(name, 70.0)
        sz = float(np.clip(wall_h * prng.uniform(0.55, 0.9) / mh, 0.5, 2.6))
        sxy = float(prng.uniform(0.75, 1.35))
        yaw = math.degrees(math.atan2(tg[i, 1], tg[i, 0])) + (0.0 if side > 0 else 180.0) + float(prng.normal(0, 8))
        c = q + nrm2 * side * (10.0 * sxy)  # into the wall: its face stands at the foot
        if not clear_at(c[0], c[1], 18.0):
            continue
        place(name, c[0], c[1], zf - 6.0 * sz, (float(prng.normal(0, 3)), float(prng.normal(0, 3)), yaw), (sxy, sxy * prng.uniform(0.8, 1.1), sz), "cliff")
        n_cliff += 1


# 3. Talus clusters: one big block, smaller ones round it; on the debris slopes under the walls, near the line.
def scatter(mask_, gap_m, count):
    cand = np.argwhere(mask_)
    prng.shuffle(cand)
    used, g_, out = set(), max(1, int(round(gap_m / CELL))), []
    for i, j in cand:
        key = (i // g_, j // g_)
        if key in used:
            continue
        used.add(key)
        out.append((float(XM[i, j]), float(YM[i, j])))
        if len(out) >= count:
            break
    return out


BIG = ["SM_Kit_Boulder_Giant", "SM_Boulder_A", "SM_Boulder_B", "SM_Kit_FracturedBlock", "SM_Kit_Overhang", "SM_Kit_TableRock"]
SMALL = ["SM_Kit_Stone_1", "SM_Kit_Stone_2", "SM_Kit_Stone_3", "SM_Kit_Stone_4", "SM_Boulder_C", "SM_Kit_FlatSlab"]
talus_mask = (slope > 16) & (slope < 38) & (free_d > 10) & (d_main < 420)
for x, y in scatter(talus_mask, 34.0, 1800):
    big = BIG[int(prng.integers(len(BIG)))]
    s = float(prng.uniform(0.8, 2.6)) * (0.6 if big == "SM_Boulder_B" else 1.0)
    jit = prng.uniform(0.85, 1.18, 3)
    if clear_at(x, y, 8.0 + 4.0 * s):
        place(big, x, y, float(bilinear(H, x, y)) - 0.25 * s, ground_tilt(x, y, prng.uniform(0, 360), 0.6, 10.0), tuple(s * jit), "talus")
    for _k in range(int(prng.integers(2, 7))):
        a_, r_ = prng.uniform(0, 2 * np.pi), prng.uniform(4.0, 16.0)
        x2, y2 = x + r_ * math.cos(a_), y + r_ * math.sin(a_)
        if not clear_at(x2, y2, 4.0):
            continue
        s2 = float(prng.uniform(0.6, 2.2))
        place(SMALL[int(prng.integers(len(SMALL)))], x2, y2, float(bilinear(H, x2, y2)) - 0.15 * s2,
              ground_tilt(x2, y2, prng.uniform(0, 360), 0.8, 14.0), tuple(s2 * prng.uniform(0.85, 1.2, 3)), "talus")

# 4. Loose stones on the floors near the line.
floor_mask = (slope < 12) & (free_d > 6) & (d_main < 260) & (H < 300)
for x, y in scatter(floor_mask, 22.0, 2600):
    s = float(prng.uniform(0.5, 2.0))
    place(SMALL[int(prng.integers(4))], x, y, float(bilinear(H, x, y)) - 0.15 * s, ground_tilt(x, y, prng.uniform(0, 360), 0.9, 10.0),
          tuple(s * prng.uniform(0.85, 1.2, 3)), "stone")

# 5. Slickrock slabs lying with the ground on the bench and the plateau.
slab_mask = (slope < 10) & (H > 200) & (free_d > 12) & (d_main < 600)
for x, y in scatter(slab_mask, 60.0, 650):
    name = ["SM_Slab_A", "SM_Slab_B", "SM_Kit_FlatSlab"][int(prng.integers(3))]
    s = float(prng.uniform(0.4, 1.1)) if name != "SM_Kit_FlatSlab" else float(prng.uniform(2.0, 5.0))
    if clear_at(x, y, 6.0 + 18.0 * s * (name != "SM_Kit_FlatSlab")):
        place(name, x, y, float(bilinear(H, x, y)) - 0.6, ground_tilt(x, y, prng.uniform(0, 360), 1.0, 3.0),
              (s, s * prng.uniform(0.8, 1.2), s * prng.uniform(0.6, 1.4)), "slab")

# 6. Fins and towers: rows of fins in the desert (Arches), towers on the bench.
fin_mask = (d_basin <= 0) & (slope < 14) & (free_d > 25) & (d_main < 500)
for x, y in scatter(fin_mask, 90.0, 160):
    yaw = 35.0 + float(prng.normal(0, 12))  # fins run in rows, as the joints in the sandstone do
    s = float(prng.uniform(1.6, 3.6))
    place("SM_Kit_Fin", x, y, float(bilinear(H, x, y)) - 0.6 * s, (float(prng.normal(0, 3)), float(prng.normal(0, 3)), yaw),
          (s, s * prng.uniform(0.9, 1.3), s * prng.uniform(0.9, 1.2)), "fin")
tower_mask = (slope < 12) & (H > 200) & (free_d > 30) & (d_main < 700)
for x, y in scatter(tower_mask, 160.0, 110):
    name = ["SM_Kit_StackedTower", "SM_Kit_TableRock"][int(prng.integers(2))]
    s = float(prng.uniform(1.4, 3.2))
    place(name, x, y, float(bilinear(H, x, y)) - 0.4 * s, ground_tilt(x, y, prng.uniform(0, 360), 0.3, 3.0),
          (s, s * prng.uniform(0.9, 1.15), s * prng.uniform(0.85, 1.1)), "tower")

# 7. Landmarks further off: mesas, buttes and spires on the bench and in the basin (spires widened, no needles).
GIANT = ["SM_Mesa_A", "SM_Mesa_B", "SM_Butte_A", "SM_IslandButte", "SM_Spire_A", "SM_Spire_B"]
giant_mask = (slope < 10) & (free_d > 200) & (d_main < 1300) & (H < 300)
for x, y in scatter(giant_mask, 520.0, 60):
    name = GIANT[int(prng.integers(len(GIANT)))]
    s = float(prng.uniform(0.8, 1.5))
    sz = s * prng.uniform(0.85, 1.15)
    sxy = s * (1.7 if "Spire" in name else 1.0)  # a spire's height stays within ~1.5x its width
    place(name, x, y, float(bilinear(H, x, y)) - 5.0 * sz, (0, 0, float(prng.uniform(0, 360))), (sxy, sxy * prng.uniform(0.9, 1.1), sz), "giant")

# 8. Plants (no collision in the game): the desert basin gets the cacti, Joshua trees, dead trees and logs; the
# bench and plateau junipers and dead trees; the canyon floors cottonwoods by the wash, logs and brush.
desert_ = d_basin <= 0
low_ = (H < 90) & ~desert_
high_ = H > 200
PLANTS_G = [
    ("saguaro", ["SM_Saguaro_A", "SM_Saguaro_B"], desert_ & (slope < 12) & (free_d > 10) & (d_main < 700), 260, 55, (0.8, 1.25)),
    ("joshua", ["SM_JoshuaTree"], desert_ & (slope < 10) & (free_d > 10) & (d_main < 700), 260, 45, (0.9, 1.6)),
    ("cholla", ["SM_Cholla"], desert_ & (slope < 14) & (free_d > 5) & (d_main < 500), 600, 20, (0.8, 1.5)),
    ("barrel", ["SM_BarrelCactus"], (desert_ | low_) & (slope < 16) & (free_d > 4) & (d_main < 400), 500, 18, (0.8, 1.4)),
    ("pear", ["SM_PricklyPear"], (slope < 16) & (free_d > 4) & (d_main < 350), 900, 14, (0.9, 1.8)),
    ("yucca", ["SM_Yucca"], (slope < 14) & (free_d > 4) & (d_main < 350), 900, 14, (0.9, 1.6)),
    ("deadtree", ["SM_DeadTree_A", "SM_DeadTree_B"], (slope < 12) & (free_d > 10) & (d_main < 500), 380, 60, (0.8, 1.5)),
    ("juniper", ["SM_Juniper_A", "SM_Juniper_B"], high_ & (slope < 12) & (free_d > 8) & (d_main < 400), 1100, 26, (0.8, 1.6)),
    ("scrub", ["SM_Sagebrush", "SM_DryGrass", "SM_DeadBrush"], (slope < 14) & (free_d > 4) & (d_main < 250), 2600, 9, (0.8, 1.6)),
    ("deadwood", ["SM_Kit_DeadSnag", "SM_Kit_DeadLog"], (slope < 10) & (free_d > 6) & (d_main < 300), 420, 35, (0.8, 1.5)),
    ("cottonwood", ["SM_Cottonwood_A", "SM_Cottonwood_B"], low_ & (slope < 8) & (H < 40) & (free_d > 10) & (d_main < 120), 140, 30, (0.9, 1.4)),
]
for group, names, mask_, count, gap_m, (s0, s1) in PLANTS_G:
    for x, y in scatter(mask_, gap_m, count):
        sc = float(prng.uniform(s0, s1))
        lean = 4.0 if group in ("deadtree", "deadwood", "joshua") else 1.5
        place(names[int(prng.integers(len(names)))], x, y, float(bilinear(H, x, y)) - 0.1 * sc,
              ground_tilt(x, y, prng.uniform(0, 360), 0.4 if group != "deadwood" else 1.0, lean),
              (sc, sc, sc * prng.uniform(0.9, 1.15)), group)
counts = {}
for p_ in props:
    counts[p_["group"]] = counts.get(p_["group"], 0) + 1
print("PROPS", counts, "total", len(props), "molds", sorted(k for k, v in src.items() if v is not None))
with open(f"{OUT}/ab_props.json", "w") as f_:
    json.dump({"units": "metres from the world centre; rot = Euler XYZ in degrees (Unreal: roll = x, pitch = -y, yaw = -z for a "
               "left-handed swap of y); scale per axis; yaw kept for older importers", "props": props}, f_)

# The craft (STRIX, 6.4 m) for scale in the pilot shots.
ship = None
if SHIP and os.path.exists(SHIP):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=SHIP)
    parts = [o for o in bpy.data.objects if o not in before]
    ship = bpy.data.objects.new("Craft", None)
    scene.collection.objects.link(ship)
    for o in parts:
        if o.parent is None:
            o.parent = ship
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/expedition.blend")

# ---- 9. Pictures: the pilot's view along the line (craft 24 m ahead), from the start to the finish.
w_ = bpy.data.worlds.new("Sky")
w_.use_nodes = True
sky = w_.node_tree.nodes.new("ShaderNodeTexSky")
for t_name in ("NISHITA", "MULTIPLE_SCATTERING"):
    try:
        sky.sky_type = t_name
        break
    except TypeError:
        pass
SUN_ELEV, SUN_AZ = math.radians(28), math.radians(-40)
sky.sun_elevation, sky.sun_rotation, sky.sun_disc = SUN_ELEV, SUN_AZ + math.pi, False
for attr_, val in (("air_density", 1.3), ("dust_density", 2.5), ("aerosol_density", 2.5)):
    if hasattr(sky, attr_):
        setattr(sky, attr_, val)
w_.node_tree.links.new(sky.outputs["Color"], w_.node_tree.nodes["Background"].inputs[0])
w_.node_tree.nodes["Background"].inputs[1].default_value = 0.13
scene.world = w_
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy, sun.data.angle, sun.data.color = 3.8, math.radians(1.2), (1.0, 0.84, 0.66)
sun.rotation_euler = (math.pi / 2 - SUN_ELEV, 0, SUN_AZ)
scene.collection.objects.link(sun)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
scene.cycles.use_denoising = True
try:
    scene.view_settings.look = "AgX - Punchy"
except TypeError:
    pass
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.clip_end = 40000
scene.collection.objects.link(cam)
scene.camera = cam


def zline(p, i):
    return float(bilinear(H, p[i, 0], p[i, 1]))


def pilot(name, i, p=main, up=4.0, ahead=200, lens=22, look_up=0.0, craft=True):
    i = int(np.clip(i, 0, len(p) - 2))
    j = int(min(len(p) - 1, i + ahead))
    eye = Vector((p[i, 0] - hx, p[i, 1] - hy, zline(p, i) + up))
    tgt = Vector((p[j, 0] - hx, p[j, 1] - hy, zline(p, j) + up * 0.5 + look_up))
    cam.data.lens = lens
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    if ship is not None:
        ship.hide_render = not craft
        k = int(min(len(p) - 2, i + 24))
        ship.location = (p[k, 0] - hx, p[k, 1] - hy, zline(p, k) + 1.6)
        ship.rotation_euler = Euler((0, 0, math.radians(heading(k, p)) - math.pi / 2))
    scene.render.filepath = f"{OUT}/ab_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("SHOT", name)


def aerial(name, eye_xy, up, tgt_xy, lens=28, tgt_up=0.0):
    if ship is not None:
        ship.hide_render = True
    ex, ey = eye_xy
    tx, ty = tgt_xy
    eye = Vector((ex - hx, ey - hy, float(bilinear(H, ex, ey)) + up))
    tgt = Vector((tx - hx, ty - hy, float(bilinear(H, tx, ty)) + tgt_up))
    cam.data.lens = lens
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = f"{OUT}/ab_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("SHOT", name)


at = lambda k, f: int(sec_of(k)[int(f * (len(sec_of(k)) - 1))])
# Warm fill lights along the cave (in Unreal Lumen bounces the skylights; Cycles here needs help) and per-shot
# exposure for the dark places.
for k_ in range(0, len(cv), 70):
    lp = bpy.data.objects.new(f"CaveLight{k_}", bpy.data.lights.new(f"CaveLight{k_}", "POINT"))
    lp.data.energy, lp.data.color, lp.data.shadow_soft_size = 2.5e4, (1.0, 0.75, 0.5), 6.0
    i_ = cv[k_]
    lp.location = (main[i_, 0] - hx, main[i_, 1] - hy, float(bilinear(H, main[i_, 0], main[i_, 1])) + 12.0)
    scene.collection.objects.link(lp)


def exposure(ev):
    scene.view_settings.exposure = ev


pilot("01_partida", 40, ahead=320, lens=24)
pilot("02_broken_mesa", lips[3] - 160, ahead=220)
s3_0 = sec_of(2)[0]
# On the rim before the drop: the whole canyon country opens below, the Sentinels at the confluence far off.
aerial("03_borda_shafer", tuple(main[s3_0 - 40]), 28.0, tuple(main[at(3, 0.45)]), lens=24, tgt_up=40.0)
aerial("03b_ziguezague", (11600, 6300), 260, (10950, 7050), lens=30)
pilot("04_red_wall", at(3, 0.62), ahead=240, lens=22, look_up=10)
sk5 = branches["S5 SKILL Fenda Estreita"]["p"]
exposure(1.6)
pilot("05_fenda_skill", len(sk5) // 3, p=sk5, up=3, ahead=120, lens=20, look_up=15)
exposure(0.0)
pilot("06_ferradura", at(5, 0.30), ahead=300, lens=22, look_up=30)
pilot("07_wash", at(6, 0.42), ahead=220, lens=22)
exposure(0.4)
pilot("08_caverna", at(7, 0.22), up=4, ahead=110, lens=20)
exposure(0.0)
pilot("09_arcos", arch_at[0] - 160, ahead=170, lens=24, look_up=8)
pilot("10_salto_heroi", i_hero - 230, up=5, ahead=330, lens=24)
# From the landing side, looking back across the ravine at the lip, the craft in the air over the gap.
if ship is not None:
    ship.hide_render = False
    ship.location = (main[i_hero, 0] - hx, main[i_hero, 1] - hy, float(bed[i_hero]) + 14.0)
    ship.rotation_euler = Euler((math.radians(-8), 0, math.radians(heading(i_hero)) - math.pi / 2))
he = main[i_hero + 170] + hero_n * 70.0
eye = Vector((he[0] - hx, he[1] - hy, float(bilinear(H, he[0], he[1])) + 22.0))
tgt = Vector((main[i_hero - 60, 0] - hx, main[i_hero - 60, 1] - hy, float(bed[i_hero - 60]) + 6.0))
cam.data.lens = 24
cam.location = eye
cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = f"{OUT}/ab_10b_salto_heroi_lado.png"
bpy.ops.render.render(write_still=True)
print("SHOT", "10b_salto_heroi_lado")
pilot("11_meta", N - 300, ahead=280, lens=24, look_up=12)
pilot("12_deserto", at(8, 0.2), ahead=220, lens=24, look_up=6)
print("EXPEDITION DONE")
