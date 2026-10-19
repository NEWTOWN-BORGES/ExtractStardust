# Grows the Red Dust Divide world around a finished canyon map (sculpt_canyon_field.py), which stays exactly as it is:
#  - west (2 km) and north (3 km): giant canyons after Canyon de Chelly and Monument Valley. They are born from the
#    current map: next to it the mesas have its size, further out they grow into a 230-310 m plateau cut by deep,
#    meandering canyons (9 m deep at their mouths, 300 m further in, as in de Chelly), with green floors, a river,
#    cottonwoods and willows, alcove bays, Spider Rock spires, Monument Valley buttes on an open plain in the
#    south-west, and badlands mesas (dissected skirts) between the dune sea and the plateau in the north-east;
#  - east (1 km): the dune sea carries on and ends in a gravel plain with dark boulders and a cluster of hoodoos.
# Every landmark is placed one by one (LANDMARKS, CANYONS). The core's washes A and B and tributary H continue as giant
# canyons. Output: the whole world as one heightmap and coloured mesh, the core's tunnels and props moved into place,
# new props (rocks and plants), JSON with everything in world coordinates, and views.
# Usage: blender -b <core_dir>/canyon_field.blend -P sculpt_expansion.py -- <core_dir> <out_dir> <kit_fbx_dir> <plant_fbx_dir> [seed]
import bpy
import json
import math
import os
import struct
import sys
import zlib
import numpy as np
from mathutils import Euler, Vector

a = sys.argv[sys.argv.index("--") + 1:]
CORE, OUT, KIT, PLANTS = a[0], a[1], a[2], a[3]
SEED = int(a[4]) if len(a) > 4 else 7
os.makedirs(OUT, exist_ok=True)
with open(f"{CORE}/canyon_field.json") as f:
    core = json.load(f)
rng = np.random.default_rng(SEED + 500)

# ---- World layout (metres, origin at the south-west corner, x east, y north).
SX, SY = 10000.0, 8000.0
OX, OY = 2000.0, 0.0  # where the core map's south-west corner sits
CW, CH = core["size_x_m"], core["size_y_m"]
CELL = core["cell_m"]
NX, NY = int(SX / CELL), int(SY / CELL)
DUNE_X = OX + core["canyon_x_m"]  # the core's sand sea starts here
Y, X = np.mgrid[0:NY, 0:NX].astype(np.float32)
XM, YM = X * CELL, Y * CELL
hx, hy = SX / 2, SY / 2
core_off = Vector((OX + CW / 2 - hx, OY + CH / 2 - hy, 0.0))  # core mesh coordinates -> world mesh coordinates


# ---- Noise (same value noise as the core, with its own seed).
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


# ---- The core map, read back from its mesh: heights and vertex colours.
terrain = bpy.data.objects["CanyonField"]
NCX, NCY = core["cells"]
cco = np.empty(len(terrain.data.vertices) * 3, np.float32)
terrain.data.vertices.foreach_get("co", cco)
Hc = cco.reshape(NCY, NCX, 3)[..., 2].copy()
ccol = np.empty(len(terrain.data.vertices) * 4, np.float32)
terrain.data.color_attributes["Col"].data.foreach_get("color", ccol)
Cc = ccol.reshape(NCY, NCX, 4)[..., :3].copy()
i0, j0 = int(round(OY / CELL)), int(round(OX / CELL))
in_core = np.zeros((NY, NX), bool)
in_core[i0:i0 + NCY, j0:j0 + NCX] = True
# Distance out of the core (0 inside), and the core edge values carried outwards (for the seam).
dxo = np.maximum(np.maximum(OX - XM, XM - (OX + CW)), 0.0)
dyo = np.maximum(np.maximum(OY - YM, YM - (OY + CH)), 0.0)
dcore = np.hypot(dxo, dyo)
ci = np.clip(((YM - OY) / CELL).astype(int), 0, NCY - 1)
cj = np.clip(((XM - OX) / CELL).astype(int), 0, NCX - 1)
H_edge, C_edge = Hc[ci, cj], Cc[ci, cj]


def mirror(k, n):
    """Index reflected back into 0..n-1 (mirror padding)."""
    period = 2 * (n - 1)
    r = np.mod(k, period)
    return np.where(r < n, r, period - r)


# The mirror is warped (up to ~70 m) so it does not read as a symmetric copy.
mw = smoothstep(0.0, 120.0, dcore) * 70.0
mi = mirror(np.round((YM - OY + mw * fbm(XM, YM, 180, 2)) / CELL).astype(np.int64), NCY)
mj = mirror(np.round((XM - OX + mw * fbm(XM + 333, YM, 180, 2)) / CELL).astype(np.int64), NCX)
H_mir, C_mir = Hc[mi, mj], Cc[mi, mj]

# ---- Zones.
east_sea = (XM > OX + CW) & (YM < OY + CH)  # the dune sea's continuation
G = smoothstep(150.0, 1700.0, dcore) * ~east_sea  # giant-canyon growth: 0 next to the core, 1 deep in the expansion
G = np.maximum(G, smoothstep(OY + CH + 900.0, OY + CH + 1900.0, YM) * (XM > DUNE_X - 400))  # plateau north of the dunes
monument = smoothstep(1500.0, 1000.0, YM) * smoothstep(2100.0, 1700.0, XM)  # open Monument Valley plain, south-west
badlands = smoothstep(DUNE_X - 600.0, DUNE_X, XM) * smoothstep(OY + CH - 100.0, OY + CH + 200.0, YM) * \
    (1.0 - smoothstep(OY + CH + 900.0, OY + CH + 1500.0, YM))  # badlands plain between the dunes and the plateau


# ---- Polyline helpers.
def smooth1d(v, window):
    pad = window // 2
    return np.convolve(np.pad(v, pad, mode="edge"), np.ones(window) / window, "valid")[:len(v)]


def resample(pts, step=1.0):
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s_ = np.concatenate([[0.0], np.cumsum(seg)])
    t_ = np.arange(0.0, s_[-1], step)
    return np.stack([np.interp(t_, s_, pts[:, 0]), np.interp(t_, s_, pts[:, 1])], 1)


def spline(ctrl, step=2.0):
    P = np.array(ctrl, np.float64)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        m = max(2, int(np.linalg.norm(p2 - p1) / step))
        t = np.linspace(0.0, 1.0, m, endpoint=False)[:, None]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(Q[-2][None])
    return resample(np.vstack(out), step)


def meander(p, amp, wave, seed_):
    """Incised meanders: the line swings side to side (amp m, wave m), as de Chelly's canyons do."""
    d = np.gradient(p, axis=0)
    n = np.stack([-d[:, 1], d[:, 0]], 1) / (np.hypot(d[:, 0], d[:, 1])[:, None] + 1e-9)
    s_ = np.arange(len(p)) * 2.0
    off = amp * np.sin(2 * np.pi * s_ / wave + seed_) * smoothstep(0, 400, s_) * smoothstep(0, 400, s_[-1] - s_)
    return p + n * off[:, None]


# ---- 1. Giant canyons (centrelines in world metres). The core's washes A (south) and B (north) carry on west into
# the canyon "Muerto" running north to the main canyon "Chinle", which crosses the whole north; tributary H of the
# core carries on north as "Monument", and a short canyon rises north of the dune sea's edge.
CANYONS = {
    "Chinle": [(150, 6900), (1300, 6650), (2600, 6350), (4000, 6750), (5400, 6300), (6800, 6650), (8200, 6450), (9850, 6750)],
    "Muerto": [(900, 150), (780, 1500), (1050, 3000), (720, 4500), (950, 5800), (1250, 6600)],
    "A_west": [(OX, OY + 1500), (1600, 1520), (1150, 1500)],
    "B_west": [(OX, OY + 3600), (1650, 3650), (1150, 3550)],
    "Monument": [(OX + 1260, OY + CH), (3300, 5600), (3650, 6150), (3800, 6500)],
    "North_gap": [(OX + 4450, OY + CH), (6400, 5600), (6450, 6250), (6500, 6500)],
}
canyon_lines = {}
for k, (name, ctrl) in enumerate(CANYONS.items()):
    p = spline(ctrl)
    if name in ("Chinle", "Muerto"):
        p = meander(p, 110.0, 900.0, k * 1.7)
    canyon_lines[name] = p
cpts = np.concatenate(list(canyon_lines.values()))
# Nearest canyon point on a coarse 8 m grid, then exact distances at full resolution.
R = max(1, int(round(8.0 / CELL)))
cx_c, cy_c = XM[::R, ::R], YM[::R, ::R]
best = np.full(cx_c.shape, -1, np.int64)
ins = (cpts[:, 0] >= 0) & (cpts[:, 0] < SX) & (cpts[:, 1] >= 0) & (cpts[:, 1] < SY)
best[(cpts[ins, 1] / (CELL * R)).astype(int).clip(0, cx_c.shape[0] - 1),
     (cpts[ins, 0] / (CELL * R)).astype(int).clip(0, cx_c.shape[1] - 1)] = np.nonzero(ins)[0]
bestd = np.where(best >= 0, (cx_c - cpts[best, 0]) ** 2 + (cy_c - cpts[best, 1]) ** 2, np.inf)
for _ in range(int(520 / (CELL * R))):
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        cand = np.roll(np.roll(best, dy, 0), dx, 1)
        ok = cand >= 0
        cc_ = np.where(ok, cand, 0)
        dd = np.where(ok, (cx_c - cpts[cc_, 0]) ** 2 + (cy_c - cpts[cc_, 1]) ** 2, np.inf)
        better = dd < bestd
        best, bestd = np.where(better, cand, best), np.where(better, dd, bestd)
bidx = np.repeat(np.repeat(best, R, 0), R, 1)[:NY, :NX]
dcan = np.where(bidx >= 0, np.hypot(XM - cpts[np.maximum(bidx, 0), 0], YM - cpts[np.maximum(bidx, 0), 1]), 1e6).astype(np.float32)
# Floor half-width grows with the canyon (20 m at the mouth by the core, 120-260 m deep in), walls wander, bays open.
half_w = 20.0 + G * (140.0 + 90.0 * fbm(XM, YM, 1200, 2)) + 22.0 * fbm(XM, YM, 140, 2) * G
half_w += 70.0 * np.clip(2.2 * fbm(XM + 50, YM - 80, 260, 1) - 0.6, 0.0, 1.0) * G  # alcove bays in the walls
canyon_floor = 1.0 - smoothstep(half_w - 4.0, half_w + 6.0, dcan)
river = (1.0 - smoothstep(4.0, 9.0 + 6.0 * G, dcan)) * smoothstep(0.25, 0.5, G)

# ---- 2. Rock: the core's mesa field grows into a plateau. A core-like mesa field (420 m features) blends into a
# giant one (1300 m features, mostly rock), canyons and the Monument plain are opened, badlands stay low.
wx = fbm(XM, YM, 300, 3) * 100
wy = fbm(XM + 517, YM + 211, 300, 3) * 100
Fa = fbm(XM + wx, YM + wy, 420, 5, 0.55)
Fb = fbm(XM + 2 * wx, YM + 2 * wy, 1300, 4, 0.55)
Fa = (Fa - np.percentile(Fa, 1)) / (np.percentile(Fa, 99) - np.percentile(Fa, 1))
Fb = (Fb - np.percentile(Fb, 1)) / (np.percentile(Fb, 99) - np.percentile(Fb, 1))
F = (1 - G) * Fa + G * (0.95 * Fb + 0.22)  # deep in: broad plateaus with gaps, buttes and outliers between them
F += 0.12 * smoothstep(0.08, 0.5, G) * (1.0 - smoothstep(0.7, 1.0, G))  # more mountains in the transition
F -= 0.9 * canyon_floor + 0.6 * monument + 0.7 * badlands + 0.8 * east_sea  # the sea itself has no mesas
# Side canyons, crack by crack: a branching network where a ridged noise crosses zero (wide trunks, narrow twigs),
# cutting the plateau into blocks and leading into the main canyons.
# Trunks 20-60 m wide and branches 12-30 m are drivable at speed; the finest twigs (6-12 m) are tight slot canyons.
slot = np.zeros((NY, NX), np.float32)
for period, amp, sharp in ((900.0, 0.55, 7), (380.0, 0.4, 10), (160.0, 0.25, 18)):
    side = 1.0 - np.abs(fbm(XM + period, YM - period, period, 2))
    cutv = amp * side ** sharp * smoothstep(0.05, 0.45, G)
    F -= cutv
    slot = np.maximum(slot, cutv / amp)
# Wall relief in metres (converted to the rock field through its local gradient, so a giant wall and a small one get
# the same metres of in and out). On the big walls:
#  - buttress ribs that stand out and bays that go in (+-18 m, ~45 m apart) and flutes (+-8 m, ~16 m apart);
#  - chimneys: deep narrow vertical cracks (8-15 m wide, 26 m into the rock) from the floor to the rim;
#  - cracks that open at the rim and run part of the way down (applied to the upper tiers only, see the layers).
gyF, gxF = np.gradient(F, CELL)
gF = np.clip(np.hypot(gxF, gyF), 1e-4, 0.02)
Gw = smoothstep(0.2, 0.7, G)
ribs = 5.0 * (1.0 - 2.0 * np.abs(fbm(XM - 11, YM + 7, 45, 1))) + 2.5 * (1.0 - 2.0 * np.abs(fbm(XM + 5, YM, 16, 1)))
chimneys = 6.0 * (1.0 - np.abs(fbm(XM + 200, YM - 90, 110, 1))) ** 14  # small: texture, never slicing the wall
F += (ribs - chimneys) * Gw * gF
rim_cracks = 4.0 * (1.0 - np.abs(fbm(XM + 77, YM, 70, 1))) ** 10 * (0.6 + 0.4 * fbm(XM, YM - 50, 300, 1)) * Gw * gF
top_cracks = 2.5 * (1.0 - np.abs(fbm(XM - 41, YM + 33, 35, 1))) ** 12 * Gw * gF
F += 0.012 * fbm(XM, YM, 30 + 20 * G.mean(), 1) + 0.008 * (1.0 - 2.0 * np.abs(fbm(XM, YM, 14, 1))) + 0.004 * (1.0 - 2.0 * np.abs(fbm(XM, YM, 6, 1)))
LEVEL = 0.55


def dilate(mask, r):
    out = mask.copy()
    for k in range(1, r + 1):
        out |= np.roll(mask, k, 0) | np.roll(mask, -k, 0)
    m2 = out.copy()
    for k in range(1, r + 1):
        out |= np.roll(m2, k, 1) | np.roll(m2, -k, 1)
    return out


# No thin needles pointing at the sky: rock thinner than ~40 m (left between two crevices or on a jagged rim) is
# taken down to the floor; the landmark spires are added later (stout, see SPIRES).
solid = F > LEVEL
opened = dilate(~dilate(~solid, int(round(20.0 / CELL))), int(round(20.0 / CELL)))
F = np.where(solid & ~opened, LEVEL - 0.03, F)
floor = 5.0 * fbm(XM, YM, 320, 3) + 2.2 * fbm(XM, YM, 60, 2) + 0.9 * fbm(XM, YM, 14, 2)
# No dead-flat open ground out here: big swells (20-35 m over ~1 km), medium rolls and small humps, damped in places
# so some flat runs remain, gentler on the main canyon floors (river) and on the dune sea (its own dunes).
flat_runs = 0.3 + 0.7 * smoothstep(-0.25, 0.25, fbm(XM - 900, YM + 300, 1600, 1))
roll = (28.0 * fbm(XM + 41, YM - 17, 1100, 2) + 7.0 * fbm(XM - 5, YM + 9, 180, 2) + 1.8 * fbm(XM, YM + 3, 35, 2)) * flat_runs
floor = floor + roll * (1.0 - 0.7 * canyon_floor) * np.where(east_sea, 0.25, 1.0)
# Heights: the core's variety (low mesas, cuestas, steps, towers) near the core; 230-310 m plateau deep in. Canyon
# depth therefore grows from a few metres at a mouth by the core to 300 m, as at de Chelly.
tilt = np.clip(0.5 + 1.3 * fbm(XM + 1234.0, YM - 777.0, 1100, 2), 0.0, 1.0)
steps = np.floor(np.clip(0.5 + 1.2 * fbm(XM - 321.0, YM + 456.0, 500, 2), 0.0, 0.999) * 4.0) / 3.0
rim = 1.0 + 0.15 * fbm(XM, YM, 80, 2)
wall_h = (1 - G ** 1.1) * 38.0 * rim * (1.5 * tilt ** 1.3 + 0.8 * steps) + G ** 1.1 * (270.0 + 40.0 * fbm(XM, YM, 1500, 2)) * rim
setback = 0.03 * np.clip(fbm(XM + 71, YM + 13, 200, 2) * 2.0, 0.0, 1.0)
rock = floor.copy()
# Tiers bottom to top; the upper ones are notched by the rim cracks (and the rim by finer ones too), so those cracks
# start at the top of the wall and come down only part of the way.
for level, width, frac, notch in ((LEVEL - 0.10, 0.02, 0.06, 0.0), (LEVEL, 0.005, 0.56, 0.0),
                                  (LEVEL + setback, 0.005, 0.28, 1.0), (LEVEL + setback + 0.012, 0.016, 0.10, 2.0)):
    Fl = F - notch * rim_cracks - (notch > 1.5) * top_cracks
    rock += wall_h * frac * smoothstep(level - width, level + width, Fl)
# Giant walls do not drop sheer to the floor: they come down in steps, cliff bands with benches and talus slopes
# between them that stand out 15-40 m (varying along the wall), as in the Grand Canyon. Offsets and widths are in
# metres, turned into the rock field through its gradient; the stepped profile takes over where the walls are big.
step_rock = floor.copy()
off = 0.0
spread = 0.7 + 0.6 * np.clip(0.5 + fbm(XM - 70, YM + 40, 400, 2), 0.0, 1.0)
for steep_frac, bench_m, slope_frac in ((0.22, 20.0, 0.05), (0.20, 30.0, 0.07), (0.20, 15.0, 0.04), (0.18, 35.0, 0.0)):
    lv = LEVEL + off * gF
    step_rock += wall_h * steep_frac * smoothstep(lv - 1.5 * gF, lv + 1.5 * gF, F)  # cliff band
    if slope_frac:
        sl = lv + (bench_m * 0.5 * spread) * gF
        step_rock += wall_h * slope_frac * smoothstep(sl - bench_m * 0.4 * spread * gF, sl + bench_m * 0.4 * spread * gF, F)  # talus slope
    off += bench_m * spread
step_rock += wall_h * 0.04 * smoothstep(LEVEL - 0.10 - 0.02, LEVEL - 0.10 + 0.02, F)  # the low bench at the foot
rock = rock * (1.0 - Gw) + step_rock * Gw
rocky = smoothstep(LEVEL - 0.01, LEVEL + 0.01, F)
rock += (1.0 + 1.5 * G) * fbm(XM, YM, 90, 3) * rocky  # plateau tops: gently rolling slickrock

# ---- 3. Landmarks, placed one by one.
props_new = []


def superellipse(cx_, cy_, ax, ay, rot, n=4.0):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    u = ((XM - cx_) * c + (YM - cy_) * s) / ax
    v = (-(XM - cx_) * s + (YM - cy_) * c) / ay
    return (np.abs(u) ** n + np.abs(v) ** n) ** (1.0 / n)  # 1 on the outline


def column(cx_, cy_, r, h, lean=0.0, taper=0.15):
    """A spire: fluted, slightly tapering column with a rounded crown, standing on a talus cone."""
    d = np.hypot(XM - cx_, YM - cy_)
    rr = r * (1.0 + 0.12 * fbm(XM, YM, 9, 1))
    body = smoothstep(rr + 3.0, rr - 3.0, d) * h * (1.0 - taper * smoothstep(0, rr, d))
    cone = np.maximum(0.0, 0.22 * h - (d - rr) * 0.65) * smoothstep(rr * 4, rr, d)
    return np.maximum(body, cone)


# Spider Rock: twin towers (200 m and 170 m) where Monument meets Chinle; more towers along the canyons.
# Stout on purpose (the player wants no thin needles pointing at the sky): height at most ~1.6x the diameter.
ch = canyon_lines["Chinle"]
mo_end = canyon_lines["Monument"][-1]
sp = ch[int(np.argmin(np.hypot(ch[:, 0] - mo_end[0], ch[:, 1] - mo_end[1])))]
SPIRES = [(sp[0] + 30, sp[1] + 10, 65, 200), (sp[0] + 170, sp[1] - 40, 52, 170)]
for frac in (0.18, 0.62, 0.86):
    q = ch[int(frac * (len(ch) - 1))]
    SPIRES.append((q[0], q[1] + 15, 45 + 15 * frac, 110 + 40 * frac))
mu = canyon_lines["Muerto"]
q = mu[int(0.72 * (len(mu) - 1))]
SPIRES.append((q[0] + 10, q[1], 50, 150))
# Monument Valley buttes ("Mittens", Merrick) on the open south-west plain: tall blocks on talus cones.
BUTTES = [(500, 650, 150, 70, 20, 165), (1450, 850, 120, 60, -15, 140), (1050, 300, 70, 60, 40, 120), (300, 1200, 60, 35, 5, 150)]
# Badlands mesas (flat tops, dissected skirts) between the dune sea and the plateau.
BAD_MESAS = [(DUNE_X + 700, OY + CH + 350, 260, 110, 10, 70), (DUNE_X + 1550, OY + CH + 520, 170, 140, -20, 60),
             (DUNE_X + 2350, OY + CH + 300, 290, 85, 35, 55)]
# Hoodoos where the dune sea ends (east).
HOODOOS = [(9650 + 120 * math.cos(t), 2100 + 700 * math.sin(t * 1.7), 9 + 6 * abs(math.sin(t * 3)), 25 + 30 * abs(math.cos(t * 2)))
           for t in np.linspace(0.0, 2.6, 9)]
land = np.zeros((NY, NX), np.float32)
for cx_, cy_, r, h in SPIRES:
    land = np.maximum(land, column(cx_, cy_, r, h))
for cx_, cy_, ax, ay, rot, h in BUTTES:
    e = superellipse(cx_, cy_, ax + 6 * fbm(XM, YM, 20, 1), ay, rot, 3.5)
    body = smoothstep(1.03, 0.97, e) * h * (1.0 + 0.03 * fbm(XM, YM, 12, 1))
    cone = np.maximum(0.0, 0.35 * h - (e - 1.0) * min(ax, ay) * 0.62) * smoothstep(3.0, 1.0, e)
    land = np.maximum(land, np.maximum(body, cone))
for cx_, cy_, ax, ay, rot, h in BAD_MESAS:
    e = superellipse(cx_, cy_, ax, ay, rot, 4.0)
    body = smoothstep(1.03, 0.97, e) * h
    # Badland skirt: radiating ridges and gullies falling from the foot of the mesa out to ~2x its size.
    ang = np.arctan2(YM - cy_, XM - cx_)
    gully = np.abs(np.sin(ang * 26.0 + 3.0 * fbm(XM, YM, 60, 2))) ** 0.6 * (0.6 + 0.4 * fbm(XM, YM, 25, 2))
    skirt = 0.45 * h * np.clip((2.3 - e) / 1.3, 0.0, 1.0) ** 1.6 * gully * (e > 0.98)
    land = np.maximum(land, np.maximum(body, skirt))
land_hoodoo = np.zeros((NY, NX), np.float32)
for cx_, cy_, r, h in HOODOOS:
    land_hoodoo = np.maximum(land_hoodoo, column(cx_, cy_, r * 1.6, h, taper=0.06))
H = np.maximum(rock, floor + land)

# ---- 4. Canyon floors, river, and the dune sea's continuation and end.
H = np.where(canyon_floor > 0.5, np.minimum(H, floor + land), H)  # canyon floors open (spires stay)
H -= river * 1.5
sea_w = (east_sea | ((XM > DUNE_X) & (YM < OY + CH + 300))).astype(np.float32)
lam = 480.0
phase = (YM + 70.0 * fbm(XM, YM, 650, 2) + 22.0 * fbm(XM, YM, 160, 2)) / lam
f_ = phase - np.floor(phase)
crest = (30.0 + 20.0 * np.clip(0.5 + 1.2 * fbm(XM + 77, YM, 900, 2), 0, 1)) * (1.0 - smoothstep(9300.0, 9900.0, XM))
dunes = crest * np.where(f_ < 0.84, (f_ / 0.84) ** 1.6, (1.0 - f_) / 0.16)
ps = (YM * 0.94 + XM * 0.34 + 12.0 * fbm(XM, YM, 90, 2)) / 48.0
fs_ = ps - np.floor(ps)
small = 2.0 * np.where(fs_ < 0.7, fs_ / 0.7, (1.0 - fs_) / 0.3) * (1.0 - smoothstep(9500.0, 9950.0, XM))
H = np.where(sea_w > 0, np.maximum(H, floor + 2.0 + (dunes + small) * (1.0 - badlands)), H)

# ---- 5. Talus at the feet of the walls (expansion only; giant walls shed more, capped).
def neighbours_max(v, r):
    out = v.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out = np.maximum(out, np.roll(np.roll(v, dy, 0), dx, 1))
    return out


wall_above = neighbours_max(H, 3) - H
debris = np.where((wall_above > 8.0) & ~in_core, np.minimum(0.3 * wall_above, 25.0), 0.0).astype(np.float32)
debris *= 1.0 - canyon_floor * 0.6
talus = math.tan(math.radians(33.0)) * CELL
dirs = [(0, 1, 1.0), (1, 0, 1.0), (0, -1, 1.0), (-1, 0, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
for _ in range(60):
    t = H + debris
    flows = [np.maximum(t - np.roll(np.roll(t, -dy, 0), -dx, 1) - talus * d, 0.0) * 0.12 for dy, dx, d in dirs]
    total = np.sum(flows, axis=0)
    scale = np.where(total > 1e-6, np.minimum(1.0, debris / np.maximum(total, 1e-6)), 0.0)
    for (dy, dx, d), fl in zip(dirs, flows):
        moved = fl * scale
        debris -= moved
        debris += np.roll(np.roll(moved, dy, 0), dx, 1)
slot_floor = (slot > 0.35) & (G > 0.3)  # side-canyon floors: kept clear of talus so they stay drivable
H = H + debris * (river < 0.5) * np.where(slot_floor, 0.15, 1.0)

# ---- 6. Seam: inside, the core is untouched. Around it the core is mirrored (continuous at the edge) and that mirror
# turns into the expansion over 450 m. East, the dune sea is the mirror of the core's last kilometre of dunes (crests
# run east-west, so they carry straight on), flattening into the gravel plain from 9.3 km.
seam = np.where(east_sea, smoothstep(9300.0, 9900.0, XM), smoothstep(0.0, 300.0, dcore + 110.0 * fbm(XM, YM, 220, 2)) * smoothstep(0.0, 60.0, dcore))  # irregular seam line, 0 at the edge
H = np.where(in_core, Hc[ci, cj], H_mir * (1 - seam) + H * seam)
H = np.maximum(H, floor + land_hoodoo)


def despike(Hh, keep):
    """Lone spikes (one or two samples standing over 6 m above the rest of their neighbours, left where thin rock
    was taken down) drop to their neighbours; they render as sharp cones. `keep` is left untouched."""
    nb = np.sort(np.stack([np.roll(np.roll(Hh, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]), axis=0)
    spike = (Hh - nb[-2] > 6.0) & ~keep
    return np.where(spike, nb[-2] + 1.0, Hh), int(spike.sum())


H, n_spikes = despike(H, in_core)
print("SPIKES removed", n_spikes)
# Fields for the grand circuit (sculpt_grand_circuit.py): where rock stands, the open floor, the side canyons.
np.savez_compressed(f"{OUT}/world_fields.npz", H=H, floor=floor, rocky=rocky * seam, slot=slot * seam, G=G, seam=seam,
                    canyon_floor=canyon_floor, in_core=in_core, sea=(sea_w > 0) | east_sea, badlands=badlands,
                    debris=debris, slot_floor=slot_floor & (seam > 0.5))
if os.environ.get("FIELDS_ONLY"):
    raise SystemExit

# ---- 7. Colours: the core's palette, plus green canyon floors, a muddy river, juniper-dotted plateaus, golden dunes
# and a grey gravel plain where the dune sea ends.
gy_, gx_ = np.gradient(H, CELL)
slope = np.degrees(np.arctan(np.hypot(gx_, gy_)))
steep = smoothstep(35, 60, slope)[..., None]
sand = np.array([0.62, 0.31, 0.12]); wall = np.array([0.52, 0.17, 0.06]); bleach = np.array([0.66, 0.36, 0.17])
dome = np.array([0.64, 0.35, 0.16]); varnish = np.array([0.22, 0.09, 0.05]); slick = np.array([0.50, 0.20, 0.08])
height_in = np.clip((H - floor) / np.maximum(wall_h, 1.0), 0.0, 1.0)[..., None]
beds = np.sin(H / (2.2 + 4.0 * G) + 1.5 * fbm(XM, YM, 140, 2)) * 0.5 + 0.5
wallcol = wall * (0.86 + 0.14 * beds ** 3)[..., None] * (0.85 + 0.15 * height_in)
wallcol = wallcol + (bleach - wallcol) * smoothstep(0.72, 0.9, height_in) * 0.7
streak = smoothstep(0.15, 0.55, fbm(XM, YM, 7 + 10 * G.mean(), 2) + 0.3 * fbm(XM, YM, 3, 1))[..., None]
wallcol = wallcol + (varnish - wallcol) * streak * smoothstep(0.2, 0.95, height_in) * 0.6
patch = smoothstep(0.05, 0.35, fbm(XM + 40, YM + 900, 90, 3))[..., None]
col = (sand + (slick - sand) * patch * 0.8) * (1 - steep) + wallcol * steep
top = (rocky[..., None] > 0.5) & (steep < 0.5)
col = np.where(top, dome * 0.85 + sand * 0.15, col)
juniper_dots = (smoothstep(0.55, 0.75, fbm(XM, YM, 9, 2)) * smoothstep(0.2, 0.6, G))[..., None]
col = np.where(top, col + (np.array([0.18, 0.24, 0.10]) - col) * juniper_dots * 0.7, col)
meadow = (canyon_floor * smoothstep(0.2, 0.5, G))[..., None] * (1 - steep)
green = np.array([0.36, 0.44, 0.17]) * (0.85 + 0.3 * fbm(XM, YM, 40, 2))[..., None]
col = col + (green - col) * meadow * smoothstep(-0.2, 0.3, fbm(XM, YM, 120, 2))[..., None] * 0.85
col = col + (np.array([0.36, 0.27, 0.18]) - col) * river[..., None]  # muddy water and wet sand
dune_col = np.array([0.74, 0.43, 0.18]) * (1.0 - 0.15 * smoothstep(15, 30, slope))[..., None]
col = np.where((sea_w > 0)[..., None] & (steep < 0.5), col + (dune_col - col) * (1 - badlands)[..., None], col)
reg = smoothstep(9300.0, 9800.0, XM)[..., None] * east_sea[..., None]
col = col + (np.array([0.42, 0.33, 0.25]) * (0.9 + 0.2 * fbm(XM, YM, 6, 1))[..., None] - col) * reg * 0.8
deb = smoothstep(0.3, 2.5, debris)[..., None] * (1 - steep)
col = col * (1 - deb) + (0.45 * sand + 0.44 * wall) * deb
col *= (0.92 + 0.08 * fbm(XM, YM, 24, 2))[..., None]
grey = col.mean(-1, keepdims=True)
col = np.clip(grey + (col - grey) * 1.25, 0.0, 1.0)
col = np.where(in_core[..., None], Cc[ci, cj], C_mir * (1 - seam[..., None]) + col * seam[..., None])

# ---- 8. The world mesh replaces the core's; the core's tunnels and props move into place.
mat = terrain.data.materials[0]
bpy.data.objects.remove(terrain)
me = bpy.data.meshes.new("CanyonField")
me.vertices.add(NX * NY)
me.vertices.foreach_set("co", np.stack([XM - hx, YM - hy, H], -1).astype(np.float32).ravel())
idx = np.arange(NX * NY, dtype=np.int32).reshape(NY, NX)
quads = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).ravel()
me.loops.add(len(quads))
me.loops.foreach_set("vertex_index", quads)
me.polygons.add((NX - 1) * (NY - 1))
me.polygons.foreach_set("loop_start", np.arange(0, len(quads), 4, dtype=np.int32))
me.update(calc_edges=True)
me.polygons.foreach_set("use_smooth", np.ones((NX - 1) * (NY - 1), bool))
attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
attr.data.foreach_set("color", np.concatenate([col.reshape(-1, 3), np.ones((NX * NY, 1))], 1).astype(np.float32).ravel())
me.materials.append(mat)
world_obj = bpy.data.objects.new("CanyonField", me)
bpy.context.scene.collection.objects.link(world_obj)
for o in bpy.data.objects:
    if o is not world_obj and o.parent is None and o.type in ("MESH", "EMPTY"):
        o.location += core_off


# ---- 9. New props: rocks from the kit (dark basalt boulders at the dune end) and plants from sculpt_plants.py.
def ground(xm, ym):
    i = int(np.clip(ym / CELL, 0, NY - 1)); j = int(np.clip(xm / CELL, 0, NX - 1))
    return float(H[i, j])


prng = np.random.default_rng(SEED + 909)
free = ~in_core & (seam > 0.6)
GROUPS = {  # name: (meshes, mask, count, min gap m, scale range, sink)
    "cottonwood": (["SM_Cottonwood_A", "SM_Cottonwood_B"], free & (canyon_floor > 0.5) & (dcan > 12) & (dcan < half_w * 0.7) & (G > 0.3), 1400, 18, (0.9, 1.5), 0.2),
    "willow": (["SM_Willow"], free & (river < 0.2) & (dcan < 30) & (dcan > 9) & (G > 0.3), 1200, 8, (0.8, 1.3), 0.1),
    "meadow": (["SM_GreenGrass", "SM_Sagebrush"], free & (canyon_floor > 0.5) & (G > 0.25) & (slope < 10), 2500, 6, (1.0, 2.0), 0.05),
    "juniper": (["SM_Juniper_A", "SM_Juniper_B"], free & (rocky > 0.5) & (slope < 15) & (G > 0.2), 2500, 20, (0.8, 1.6), 0.2),
    "scrub": (["SM_Sagebrush", "SM_Yucca", "SM_PricklyPear", "SM_DryGrass", "SM_DeadBrush"], free & (slope < 18) & (canyon_floor < 0.5) & (rocky < 0.5) & ~east_sea, 3000, 10, (0.8, 1.6), 0.05),
    "boulder_dark": (["SM_Kit_Stone_2", "SM_Kit_Stone_3", "SM_Kit_Stone_4", "SM_Kit_Boulder_Giant"], free & east_sea & (XM > 9350) & (slope < 15), 450, 14, (0.6, 1.8), 0.15),
    "stone": (["SM_Kit_Stone_1", "SM_Kit_Stone_2", "SM_Kit_Stone_3", "SM_Kit_FlatSlab"], free & (debris > 0.8) & (slope < 34) & ~slot_floor, 2500, 8, (0.8, 2.0), 0.1),
    "giant": (["SM_Kit_Overhang", "SM_Kit_FracturedBlock", "SM_Kit_Boulder_Giant"], free & (debris > 3.0) & (slope < 34) & ~slot_floor, 500, 40, (1.0, 2.5), 0.08),
    "dead_wood": (["SM_Kit_DeadLog", "SM_Kit_DeadSnag"], free & (canyon_floor > 0.5) & (G < 0.5) & (river < 0.2), 300, 30, (0.8, 1.3), 0.04),
}
for group, (names, mask_, count, gap, (s0, s1), sink) in GROUPS.items():
    cand = np.argwhere(mask_)
    prng.shuffle(cand)
    used, g_ = set(), max(1, int(round(gap / CELL)))
    n_ = 0
    for i, j in cand:
        key = (i // g_, j // g_)
        if key in used:
            continue
        used.add(key)
        sc = float(prng.uniform(s0, s1))
        props_new.append({"mesh": names[int(prng.integers(len(names)))], "group": group, "x": float(XM[i, j] - hx),
                          "y": float(YM[i, j] - hy), "z": float(H[i, j]) - sink * sc, "yaw": float(prng.uniform(0, 360)), "scale": sc})
        n_ += 1
        if n_ >= count:
            break
# Hand-placed: a giant double arch on Muerto's floor and a huge fin on the Monument plain.
q = mu[int(0.35 * (len(mu) - 1))]
props_new += [{"mesh": "SM_Kit_Arch", "group": "landmark", "x": q[0] - hx, "y": q[1] - hy, "z": ground(q[0], q[1]) - 1, "yaw": 15.0, "scale": 3.2},
              {"mesh": "SM_Kit_Arch", "group": "landmark", "x": q[0] + 25 - hx, "y": q[1] + 18 - hy, "z": ground(q[0] + 25, q[1] + 18) - 1, "yaw": 85.0, "scale": 2.3},
              {"mesh": "SM_Kit_Fin", "group": "landmark", "x": 1700 - hx, "y": 450 - hy, "z": ground(1700, 450) - 2, "yaw": 60.0, "scale": 4.0}]
print("NEW PROPS", {g: sum(1 for p_ in props_new if p_["group"] == g) for g in list(GROUPS) + ["landmark"]})


def material(name, base, dark=None, attribute=None):
    m_ = bpy.data.materials.new(name)
    m_.use_nodes = True
    nt = m_.node_tree
    bs = nt.nodes["Principled BSDF"]
    if attribute:
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = attribute
        nt.links.new(at.outputs["Color"], bs.inputs["Base Color"])
    else:
        bs.inputs["Base Color"].default_value = (*base, 1)
    bs.inputs["Roughness"].default_value = 0.9
    return m_


plant_mat = material("M_PlantCol", None, attribute="Col")
basalt = material("M_Basalt", (0.07, 0.065, 0.06))
src = {}
for o in bpy.data.objects:  # kit meshes already in the core file (from its KitSource collection)
    if o.type == "MESH" and o.data and o.data.name.startswith("SM_Kit_"):
        src.setdefault(o.data.name.split(".")[0], o.data)
for name_ in sorted({p_["mesh"] for p_ in props_new}):
    if name_ in src:
        continue
    for folder in (KIT, PLANTS):
        path_ = os.path.join(folder, name_ + ".fbx")
        if os.path.exists(path_):
            before = set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=path_)
            new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
            if new:
                o = new[0]
                bpy.ops.object.select_all(action="DESELECT")
                o.select_set(True)
                bpy.context.view_layer.objects.active = o
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
                if folder == PLANTS:
                    o.data.materials.clear()
                    o.data.materials.append(plant_mat)
                o.hide_render = o.hide_viewport = True
                src[name_] = o.data
            break
dark_copies = {}
col_new = bpy.data.collections.new("PropsExpansion")
bpy.context.scene.collection.children.link(col_new)
for k, p_ in enumerate(props_new):
    data = src.get(p_["mesh"])
    if data is None:
        continue
    if p_["group"] == "boulder_dark":  # dark basalt version of the kit boulders
        if p_["mesh"] not in dark_copies:
            dc = data.copy()
            dc.materials.clear()
            dc.materials.append(basalt)
            dark_copies[p_["mesh"]] = dc
        data = dark_copies[p_["mesh"]]
    o = bpy.data.objects.new(f"PropX_{p_['group']}_{k}", data)
    o.location = (p_["x"], p_["y"], p_["z"])
    o.rotation_euler = Euler((0, 0, math.radians(p_["yaw"])))
    o.scale = (p_["scale"],) * 3
    col_new.objects.link(o)
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/world.blend")


# ---- 10. Heightmap, JSON (core content moved to world coordinates) and props.
def write_png(path, data, bits, channels):
    h, w = data.shape[:2]
    raw = (data.astype(">u2") if bits == 16 else data.astype(np.uint8)).reshape(h, w * channels).tobytes()
    stride = w * channels * (2 if bits == 16 else 1)
    rows = b"".join(b"\x00" + raw[r * stride:(r + 1) * stride] for r in range(h))

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    with open(path, "wb") as f_:
        f_.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, bits, 0 if channels == 1 else 2, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


zlo, zhi = float(H.min()), float(H.max())
write_png(f"{OUT}/world_height16.png", np.round((H - zlo) / (zhi - zlo) * 65535)[::-1], 16, 1)


def shift_pt(pt):
    return [round(pt[0] + core_off.x, 1), round(pt[1] + core_off.y, 1)] + list(pt[2:])


world = dict(core)
world.update({"size_x_m": SX, "size_y_m": SY, "size_m": max(SX, SY), "cells": [NX, NY], "canyon_x_m": DUNE_X,
              "z_m": [round(zlo, 1), round(zhi, 1)], "core_origin_m": [OX, OY], "core_size_m": [CW, CH]})
world["network"] = {n: dict(w_, centreline=[shift_pt(p_) for p_ in w_["centreline"]]) for n, w_ in core["network"].items()}
world["circuit"] = dict(core["circuit"], points=[shift_pt(p_) for p_ in core["circuit"]["points"]])
world["tunnels"] = [dict(t, portal_in=shift_pt(t["portal_in"]), portal_out=shift_pt(t["portal_out"])) for t in core["tunnels"]]
world["cuts"] = [dict(c_, at=shift_pt(c_["at"])) for c_ in core["cuts"]]
for name, p in canyon_lines.items():  # giant canyons join the network (blue in the route plan)
    world["network"]["Canyon_" + name] = {"giant_canyon": True, "centreline": [[round(x - hx, 1), round(y - hy, 1), 0.0] for x, y in p[::4]]}
world["landmarks"] = {"spires": SPIRES, "buttes": BUTTES, "badlands_mesas": BAD_MESAS, "hoodoos": HOODOOS}
with open(f"{OUT}/canyon_field.json", "w") as f_:
    json.dump(world, f_, indent=1, default=float)
with open(f"{CORE}/props.json") as f_:
    core_props = json.load(f_)["props"]
for p_ in core_props:
    p_["x"] += core_off.x
    p_["y"] += core_off.y
with open(f"{OUT}/props.json", "w") as f_:
    json.dump({"units": "m from the world centre, yaw in degrees", "props": core_props + props_new}, f_, default=float)
print("WORLD", NX, NY, "z", round(zlo, 1), round(zhi, 1), "props", len(core_props) + len(props_new))

# ---- 11. Views.
scene = bpy.context.scene
w_ = bpy.data.worlds.new("Sky")
w_.use_nodes = True
sky = w_.node_tree.nodes.new("ShaderNodeTexSky")
sky.sky_type = "NISHITA"
SUN_ELEV, SUN_AZ = math.radians(25), math.radians(-35)
sky.sun_elevation, sky.sun_rotation, sky.air_density, sky.dust_density, sky.sun_disc = SUN_ELEV, SUN_AZ + math.pi, 1.4, 3.0, False
w_.node_tree.links.new(sky.outputs["Color"], w_.node_tree.nodes["Background"].inputs[0])
w_.node_tree.nodes["Background"].inputs[1].default_value = 0.12
scene.world = w_
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy, sun.data.angle, sun.data.color = 3.6, math.radians(1.5), (1.0, 0.82, 0.62)
sun.rotation_euler = (math.pi / 2 - SUN_ELEV, 0, SUN_AZ)
scene.collection.objects.link(sun)
bpy.ops.mesh.primitive_plane_add(size=80000, location=(0, 0, zlo - 1.0))
bpy.context.active_object.data.materials.append(material("M_Plain", (0.59, 0.29, 0.11)))
scene.view_settings.look = "AgX - Punchy"
scene.view_settings.exposure = -0.2
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
scene.cycles.use_denoising = True
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.clip_end = 60000
scene.collection.objects.link(cam)
scene.camera = cam


def shot(name, eye, target, lens=28, ortho=None, res=(1600, 900)):
    cam.data.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        cam.data.ortho_scale = ortho
    cam.data.lens = lens
    cam.location = eye
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = f"{OUT}/world_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("SHOT", name)


def at(x, y, up):
    return (x - hx, y - hy, ground(x, y) + up)


sun.rotation_euler = (math.radians(30), 0, SUN_AZ)
shot("topo", (0, 0, 3000), (0, 0.01, 0), ortho=SX, res=(1600, 1280))
sun.rotation_euler = (math.pi / 2 - SUN_ELEV, 0, SUN_AZ)
shot("geral", (-hx * 0.9, -hy * 1.35, 2600), (0, hy * 0.15, 0), lens=26)
sx_, sy_ = SPIRES[0][0], SPIRES[0][1]
shot("spider_rock_aerea", at(sx_ - 650, sy_ - 520, 420), at(sx_, sy_ + 80, 60), lens=30)
shot("spider_rock_fundo", at(sx_ - 420, sy_ - 60, 4), at(sx_, sy_, 140), lens=24)
cq = ch[int(0.42 * (len(ch) - 1))]
cq2 = ch[int(0.42 * (len(ch) - 1)) + 150]
shot("canyon_gigante_fundo", at(cq[0], cq[1], 5), at(cq2[0], cq2[1], 30), lens=22)
shot("canyon_gigante_aerea", at(cq[0] - 500, cq[1] - 700, 520), at(cq2[0], cq2[1], 0), lens=28)
shot("monument_valley", at(1350, 80, 6), at(450, 700, 70), lens=35)
bm = BAD_MESAS[0]
shot("badlands_aerea", at(bm[0] - 900, bm[1] - 900, 650), at(bm[0] + 600, bm[1] + 150, 0), lens=30)
shot("fim_das_dunas", at(9350, 2000, 3), at(9700, 2150, 15), lens=26)
# A giant wall close up: from the canyon floor square on, and grazing along it (shows the in-and-out relief).
for frac, tag in ((0.3, "a"), (0.55, "b")):
    i_c = int(frac * (len(ch) - 1))
    pc, dv = ch[i_c], ch[i_c + 6] - ch[i_c - 6]
    dv = dv / (np.linalg.norm(dv) + 1e-9)
    nv = np.array([-dv[1], dv[0]])
    hw = float(half_w[int(np.clip(pc[1] / CELL, 0, NY - 1)), int(np.clip(pc[0] / CELL, 0, NX - 1))])
    eye = pc + nv * hw * 0.5
    wallp = pc - nv * (hw + 4.0)
    shot(f"parede_gigante_frente_{tag}", at(eye[0], eye[1], 6), at(wallp[0], wallp[1], 110), lens=24)
    eye2 = pc - nv * (hw - 18.0)
    tgt2 = pc - nv * (hw - 4.0) + dv * 320.0
    shot(f"parede_gigante_rasante_{tag}", at(eye2[0], eye2[1], 8), at(tgt2[0], tgt2[1], 70), lens=26)
# Inside a side canyon at craft height, looking along it (direction from the slot cells around), and the maze from above.
cand = np.argwhere(slot_floor & (G > 0.8) & (dcan > 400) & (slope < 8) & (np.abs(XM - 2500) < 1500) & (YM > 6000))
if len(cand):
    i_, j_ = cand[len(cand) // 2]
    near_ = cand[(np.abs(cand[:, 0] - i_) < 20) & (np.abs(cand[:, 1] - j_) < 20)].astype(np.float64)
    vals, vecs = np.linalg.eigh(np.cov((near_ - near_.mean(0)).T))
    di, dj = vecs[:, -1]
    x0_, y0_ = XM[i_, j_], YM[i_, j_]
    shot("fenda_piloto", at(x0_, y0_, 4), at(x0_ + dj * 120, y0_ + di * 120, 10), lens=22)
    shot("fendas_aerea", at(x0_ - 500, y0_ - 600, 650), at(x0_, y0_, 0), lens=30)
shot("transicao_core_gigante", at(OX + 600, OY + CH - 600, 60), at(OX + 600, OY + CH + 1800, 120), lens=26)
print("EXPANSION DONE")
