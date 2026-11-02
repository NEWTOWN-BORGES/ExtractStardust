"""Mapa 02 Selva Esmeralda, piece by piece (Docs/PISTA_SELVA_ESMERALDA.md, section 6): the terrain of one sector at a
time from the plan (Scripts/selva/selva_plano.json, made by Scripts/selva/plan_selva.py), with water, the road and its
forks carved in, the jungle scattered from our own plant kit (Scripts/selva/jungle_kit.py), and photos to show.

    blender -b -P Scripts/selva/sculpt_selva.py -- <out> S1 [res=3] [samples=40] [size=1600x900] [noshots] [only=a,b]
    python3 Scripts/selva/sculpt_selva.py <out> S1 ...           (with the bpy module)

Each sector has its own recipe (RECIPES); so far S1 Várzea Alagada: the Amazon floodplain at A. Writes, in <out>:
  selva_S1_height.r16 + selva_S1.json   heightfield (uint16 little-endian, Unreal's raw format) and its box, metres per
                                        pixel, height range, water level, the road's own height profile and the jumps
  selva_S1_props.json                   the jungle: kind, x, y, z, yaw (degrees), scale (no collision in the game)
  selva_S1.blend, selva_S1_*.png        the scene and the photos (pilot and aerial)
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Euler, Vector
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jungle_kit as jk  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0]
SECTOR = next((a for a in argv[1:] if "=" not in a and a.upper().startswith("S")), "S1").upper()
OPTS = dict(a.split("=", 1) for a in argv[1:] if "=" in a)
FLAGS = {a for a in argv[1:] if "=" not in a}
RES = float(OPTS.get("res", 3))
SAMPLES = int(OPTS.get("samples", 40))
SIZE = tuple(int(v) for v in OPTS.get("size", "1600x900").split("x"))
ONLY = set(OPTS["only"].split(",")) if "only" in OPTS else None
os.makedirs(OUT, exist_ok=True)
T0 = time.time()


def log(*a):
    print("SELVA %5.0fs" % (time.time() - T0), *a, flush=True)


# ---------------------------------------------------------------------------------------------------- 1. the plan
plan = json.load(open(os.path.join(HERE, "selva_plano.json"), encoding="utf-8"))
R = plan["route"]
STEP = R["step_m"]
names = [s["name"] for s in plan["sectors"]]
KS = next(i for i, n in enumerate(names) if n.split()[0].upper() == SECTOR)
SNAME = names[KS]


def dense(points, z=None, hw=None, step=1.0):
    """Polyline sampled every 'step' metres (with its z and half width carried along)."""
    p = np.asarray(points, float)
    s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
    t = np.arange(0.0, s[-1], step)
    out = [np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])]
    zz = np.interp(t, s, np.asarray(z, float)) if z is not None else None
    ww = np.interp(t, s, np.broadcast_to(np.asarray(hw, float), (len(p),))) if hw is not None else None
    return np.stack(out, 1), zz, ww, t


road, road_z, road_hw, road_s = dense(R["points"], R["z"], R["half_width"])
road_sec = np.asarray(R["sector"])[np.clip((road_s / STEP).astype(int), 0, len(R["sector"]) - 1)]
in_sec = np.flatnonzero(road_sec == KS)
S0, S1_ = int(in_sec[0]), int(in_sec[-1])
forks = [f for f in plan["forks"] if S0 <= f["leave_m"] <= S1_]
jumps = [j for j in plan["jumps"] if "at_m" in j and S0 <= j["at_m"] <= S1_]
fork_jumps = [j for j in plan["jumps"] if "fork" in j and j["fork"] in [f["name"] for f in forks]]
log(SNAME, "road %d-%d m," % (S0, S1_), "forks", [f["name"] for f in forks], "jumps", [j["what"] for j in jumps])

# the box: the sector's road (with a little of its neighbours) and its forks, plus forest all round
lo_i, hi_i = max(0, S0 - 250), min(len(road) - 1, S1_ + 350)
pts = [road[lo_i:hi_i]] + [np.asarray(f["points"]) for f in forks]
allp = np.vstack(pts)
MARGIN = 650.0
X0, Y0 = np.maximum(allp.min(0) - MARGIN, 0.0)
X1, Y1 = np.minimum(allp.max(0) + MARGIN, plan["world_m"])
NX, NY = int((X1 - X0) / RES) + 1, int((Y1 - Y0) / RES) + 1
X1, Y1 = X0 + (NX - 1) * RES, Y0 + (NY - 1) * RES
XX, YY = np.meshgrid(X0 + RES * np.arange(NX), Y0 + RES * np.arange(NY))
log("box x %.0f-%.0f y %.0f-%.0f, %d x %d at %.1f m" % (X0, X1, Y0, Y1, NX, NY, RES))


# ---------------------------------------------------------------------------------------------------- 2. fields
def line_field(P, reach=5):
    """Exact distance from every cell to the polyline P (dense, ~1 m), the (fractional) index of the nearest point and
    the side (+1 left of the direction of travel)."""
    ij = np.round((P - (X0, Y0)) / RES).astype(int)
    ok = (ij[:, 0] >= 0) & (ij[:, 0] < NX) & (ij[:, 1] >= 0) & (ij[:, 1] < NY)
    mark = np.zeros((NY, NX), bool)
    idxm = np.zeros((NY, NX), np.int64)
    if not ok.any():
        return np.full((NY, NX), 1e9), np.zeros((NY, NX)), np.ones((NY, NX))
    mark[ij[ok, 1], ij[ok, 0]] = True
    idxm[ij[ok, 1], ij[ok, 0]] = np.flatnonzero(ok)
    _d, (iy, ix) = ndimage.distance_transform_edt(~mark, return_indices=True)
    near = idxm[iy, ix]
    best = np.full((NY, NX), np.inf)
    fi = near.astype(float)
    side = np.ones((NY, NX))
    n = len(P)
    for o in range(-reach, reach + 1):
        a = np.clip(near + o, 0, n - 2)
        ax, ay = P[a, 0], P[a, 1]
        bx, by = P[a + 1, 0] - ax, P[a + 1, 1] - ay
        gx, gy = XX - ax, YY - ay
        t = np.clip((gx * bx + gy * by) / np.maximum(bx * bx + by * by, 1e-9), 0, 1)
        dd = np.hypot(gx - t * bx, gy - t * by)
        better = dd < best
        best = np.where(better, dd, best)
        fi = np.where(better, a + t, fi)
        side = np.where(better, np.sign(bx * gy - by * gx + 1e-12), side)
    return best, fi, side


def at(arr, fi):
    """Linear interpolation of a per-point array at fractional indices."""
    i = np.clip(np.floor(fi).astype(int), 0, len(arr) - 2)
    t = fi - i
    return arr[i] * (1 - t) + arr[i + 1] * t


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def vnoise(x, y, scale, seed):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(4096)
    vals = rng.random(4096)
    gx, gy = x / scale + 1000.0, y / scale + 1000.0
    i0, j0 = np.floor(gx).astype(np.int64), np.floor(gy).astype(np.int64)
    fx, fy = gx - i0, gy - j0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)

    def h(i, j):
        return vals[(perm[i & 4095] + j) & 4095]

    return (h(i0, j0) * (1 - fx) + h(i0 + 1, j0) * fx) * (1 - fy) + (h(i0, j0 + 1) * (1 - fx) + h(i0 + 1, j0 + 1) * fx) * fy


def fbm(x, y, scale, seed, octaves=5):
    s, a, tot = 0.0, 1.0, 0.0
    for k in range(octaves):
        s = s + a * vnoise(x, y, scale / 2 ** k, seed + 17 * k)
        tot += a
        a *= 0.5
    return s / tot


def bilinear(H, x, y):
    fx, fy = (np.asarray(x) - X0) / RES, (np.asarray(y) - Y0) / RES
    i, j = np.clip(np.floor(fx).astype(int), 0, NX - 2), np.clip(np.floor(fy).astype(int), 0, NY - 2)
    tx, ty = np.clip(fx - i, 0, 1), np.clip(fy - j, 0, 1)
    return (H[j, i] * (1 - tx) + H[j, i + 1] * tx) * (1 - ty) + (H[j + 1, i] * (1 - tx) + H[j + 1, i + 1] * tx) * ty


# the road near the box (dense, 1 m) and the forks
rlo, rhi = max(0, S0 - 900), min(len(road) - 1, S1_ + 900)
RP, RZ, RW = road[rlo:rhi], road_z[rlo:rhi].copy(), road_hw[rlo:rhi]
FD = []
for f in forks:
    P, z, _w, _s = dense(f["points"], f["z"], f["half_width"])
    FD.append(dict(f=f, P=P, z=z, hw=float(f["half_width"])))
rivers = []
for rv in plan.get("rivers", []):
    P, _z, _w, _s = dense(rv["points"], step=2.0)
    if ((P[:, 0] > X0 - 500) & (P[:, 0] < X1 + 500) & (P[:, 1] > Y0 - 500) & (P[:, 1] < Y1 + 500)).any():
        rivers.append(dict(name=rv["name"], P=P, w=float(rv["width_m"])))
log("fields: road, %d forks, %d rivers" % (len(FD), len(rivers)))


# ---------------------------------------------------------------------------------------------------- 3. recipes
def creek(rng, p0, heading, length, wiggle=0.35):
    """A meandering igarapé from p0: heading drifts smoothly (sine-generated, as rivers meander)."""
    s = np.arange(0.0, length, 2.0)
    ph = rng.uniform(0, 6.3)
    lam = rng.uniform(260, 420)
    ang = heading + wiggle * np.sin(2 * np.pi * s / lam + ph) + 0.12 * np.sin(2 * np.pi * s / (lam * 0.37) + 2 * ph)
    d = np.stack([np.cos(ang), np.sin(ang)], 1) * 2.0
    return np.asarray(p0, float) + np.cumsum(d, 0) - d[0]


def recipe_s1():
    """S1 Várzea Alagada (Amazon floodplain at A): forest a metre above the water, lagoons, the delta river, igarapés
    (creeks) across the forest, natural levees, and toward S2 the first foothills of the red ridge."""
    W = float(np.floor(RZ[S0 - rlo:S1_ - rlo].min() - 1.5))     # the water a metre and a half under the road's lowest point
    rng = np.random.default_rng(101)
    n_lo = fbm(XX, YY, 700.0, 11, 4)
    n_mid = fbm(XX, YY, 160.0, 23, 4)
    n_hi = fbm(XX, YY, 30.0, 37, 3)
    base = W + 0.9 + 1.5 * (n_lo - 0.5) + 0.7 * (n_mid - 0.5) + 0.18 * (n_hi - 0.5)
    base -= 2.8 * smoothstep(0.40, 0.26, n_lo)                     # lagoons where the low noise dips
    base += 7.0 * smoothstep(5400.0, 7600.0, XX) ** 2              # foothills of the Serra Vermelha (S2)
    fields = dict(lagoon=smoothstep(0.40, 0.30, n_lo))
    # the delta river: a parabolic bed 6 m deep, sandy banks, a natural levee beside it
    wet_river = np.zeros_like(base)
    for rv in rivers:
        dr, fi, _sd = line_field(rv["P"], reach=4)
        wr = 0.5 * rv["w"] * (1 + 0.18 * np.sin(fi * 2.0 / 380.0))
        bed = W - 6.5 + 5.0 * np.clip(dr / wr, 0, 1) ** 2
        bank = smoothstep(0.92 * wr, wr + 40.0, dr)
        levee = 1.1 * np.exp(-((dr - wr - 28.0) / 45.0) ** 2)
        base = bed * (1 - bank) + (base + levee) * bank
        wet_river = np.maximum(wet_river, 1 - smoothstep(wr, wr + 25.0, dr))
        fields["river_d"], fields["river_w"] = dr, wr
    # igarapés: creeks wandering across the forest, one of them under the road's 'igarapé' jump
    creeks = []
    for j in jumps:
        if j["what"] == "igarapé":
            i = int(j["at_m"]) - rlo
            t = RP[min(i + 5, len(RP) - 1)] - RP[max(i - 5, 0)]
            hd = math.atan2(t[1], t[0]) + math.pi / 2
            c0 = creek(rng, RP[i], hd, 900, wiggle=0.25)
            c1 = creek(rng, RP[i], hd + math.pi, 900, wiggle=0.25)
            creeks.append(np.vstack([c1[::-1], c0[1:]]))
    for k in range(7):
        p0 = (rng.uniform(X0, X1), rng.uniform(Y0, Y1))
        creeks.append(creek(rng, p0, rng.uniform(0, 2 * np.pi), rng.uniform(900, 1800)))
    for C in creeks:
        dc, fi, _sd = line_field(C, reach=3)
        wc = 9.0 + 4.0 * np.sin(fi * 2.0 / 150.0)
        cut = W - 1.7 + 2.6 * np.clip(dc / wc, 0, 1) ** 2
        base = np.where(dc < wc * 1.6, np.minimum(base, cut + 1.2 * smoothstep(wc, wc * 1.6, dc)), base)
        wet_river = np.maximum(wet_river, 1 - smoothstep(wc, wc + 10.0, dc))
    fields["creek_d"] = np.min([line_field(C, reach=2)[0] for C in creeks], axis=0) if creeks else None
    return W, base, wet_river, fields


RECIPES = {"S1": recipe_s1}
W, H, WET, F = RECIPES[SECTOR]()
log("natural ground %.1f-%.1f m, water at %.1f m" % (H.min(), H.max(), W))


# ---------------------------------------------------------------------------------------------------- 4. the road
def road_profile(P, z, natural, jumps_here):
    """The road's own height along it: the plan's height, across the river as a ford (12 cm under the surface: the
    ships skim it), with the jumps built in. Returns z per point and a list of jump records for the game."""
    z = z.copy()
    # a ford only across the river (over lagoons and creeks the road runs on a sand causeway)
    if "river_d" in F:
        under = bilinear(F["river_d"], P[:, 0], P[:, 1]) < 0.95 * bilinear(F["river_w"], P[:, 0], P[:, 1])
    else:
        under = np.zeros(len(P), bool)
    if under.any():
        under = ndimage.binary_dilation(under, iterations=25)             # a ford starts before the water does
    k = np.hanning(161)
    w8 = ndimage.convolve1d(under.astype(float), k / k.sum(), mode="nearest")
    z = z * (1 - w8) + (W - 0.12) * w8
    recs = []
    for j in jumps_here:
        i = int(j["i"])
        if j["what"] == "igarapé":           # a kicker to the creek's lip, the creek (32 m of water), the far bank
            s = np.arange(len(z)) - i
            kick = 2.6 * smoothstep(-70, -18, s) * (s < -16)
            z = z + kick
            gap = np.abs(s) <= 16
            z = np.where(gap, W - 1.6, z)
            recs.append(dict(what=j["what"], at_m=int(j["at_m"]), lip=float(z[i - 17]), gap_m=32, kicker_m=2.6))
        elif j["what"] == "tronco caído":    # a sand ramp up to a giant fallen trunk, then the drop off its far side
            s = np.arange(len(z)) - i
            ramp = 3.2 * smoothstep(-60, -4, s) * (s <= 4) + 3.2 * (1 - smoothstep(4, 26, s)) * (s > 4)
            z = z + ramp
            recs.append(dict(what=j["what"], at_m=int(j["at_m"]), crest=float(z[i]), ramp_m=3.2))
    return z, recs


def lay_road(H, P, z, hw, color_kind):
    """Carve or build the road: flat across at its height, sand shoulders, banks blending into the ground."""
    d, fi, _sd = line_field(P)
    zr = at(z, fi)
    hwv = at(hw, fi) if np.ndim(hw) else np.full_like(d, hw)
    diff = np.abs(zr - H)
    bankw = 10.0 + 2.2 * np.clip(diff, 0, 8)
    t = smoothstep(hwv + 1.5, hwv + 1.5 + bankw, d)
    H2 = zr * (1 - t) + H * t
    return H2, d, hwv, t


for fd in FD:                        # the flooded forest (igapó) round F1 is ground, before any road is laid on it
    if "Igapó" in fd["f"]["name"]:
        dI, _fi, _s = line_field(fd["P"])
        flood = 1 - smoothstep(60.0, 190.0, dI)
        H = H * (1 - flood) + np.minimum(H, W - 0.5 - 0.6 * fbm(XX, YY, 40.0, 5, 3)) * flood
        F["igapo"] = flood
roadjumps = []
for j in jumps:
    roadjumps.append(dict(j, i=int(j["at_m"]) - rlo))
RZ2, JREC = road_profile(RP, RZ, H, roadjumps)
H_nat = H.copy()
H, D_ROAD, HW_ROAD, T_ROAD = lay_road(H, RP, RZ2, RW, "road")
D_FORK = np.full_like(H, 1e9)
T_FORK = np.ones_like(H)
fork_rec = []
for fd in FD:
    zf = fd["z"].copy()
    name = fd["f"]["name"]
    if "Igapó" in name:              # through the flooded forest, at water level: the ships skim between the trees
        n = len(zf)
        mid = smoothstep(0, 220, np.arange(n)) * smoothstep(0, 220, n - 1 - np.arange(n))
        zf = zf * (1 - mid) + (W - 0.12) * mid
    Hn, dF, _hw, tF = lay_road(H, fd["P"], zf, fd["hw"], "fork")
    H = Hn
    D_FORK = np.minimum(D_FORK, dF - fd["hw"])
    T_FORK = np.minimum(T_FORK, tF)
    fork_rec.append(dict(name=name, z_min=float(zf.min()), z_max=float(zf.max())))
D_EDGE = np.minimum(D_ROAD - HW_ROAD, D_FORK)              # metres from the nearest road or fork edge
log("road laid: %d jumps, forks %s" % (len(JREC), [f["name"] for f in fork_rec]))

# ---------------------------------------------------------------------------------------------------- 5. colours
def srgb(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


SAND, WETSAND = srgb((0.60, 0.50, 0.37)), srgb((0.36, 0.29, 0.21))
MUD, FLOOR, MOSS = srgb((0.30, 0.24, 0.17)), srgb((0.22, 0.17, 0.11)), srgb((0.20, 0.27, 0.11))
MEADOW = srgb((0.42, 0.54, 0.17))
nc = fbm(XX, YY, 25.0, 71, 3)
depth = W - H
col = FLOOR[None, None] * (0.8 + 0.4 * nc[..., None])
col = col * (1 - 0.5 * smoothstep(0.45, 0.7, nc))[..., None] + MOSS[None, None] * (0.5 * smoothstep(0.45, 0.7, nc))[..., None]
edge = smoothstep(1.2, -0.1, H - W)                              # the wet band by the water
col = col * (1 - edge[..., None]) + MUD[None, None] * edge[..., None]
meadow = smoothstep(0.9, 0.3, H - W) * smoothstep(-0.6, -0.1, H - W) * smoothstep(0.35, 0.6, fbm(XX, YY, 90.0, 83, 3))
col = col * (1 - meadow[..., None]) + MEADOW[None, None] * meadow[..., None]
road_k = np.maximum(1 - T_ROAD, 1 - T_FORK)
sand = np.clip(road_k * 1.3, 0, 1)
col = col * (1 - sand[..., None]) + (SAND * (0.9 + 0.2 * nc[..., None]))[...] * sand[..., None]
wsand = sand * smoothstep(0.6, -0.2, H - W)
puddle = sand * smoothstep(0.62, 0.70, fbm(XX, YY, 14.0, 91, 4)) * (1 - T_ROAD)     # rain puddles and wet ruts
wsand = np.maximum(wsand, 0.85 * puddle)
col = col * (1 - wsand[..., None]) + WETSAND[None, None] * wsand[..., None]
ED = np.minimum(np.abs(D_ROAD - HW_ROAD), np.abs(D_FORK))
grass = smoothstep(5.0, 0.0, ED) * smoothstep(0.35, 0.55, fbm(XX, YY, 9.0, 97, 3)) * (H - W > 0.3)
col = col * (1 - 0.8 * grass[..., None]) + MEADOW[None, None] * 0.8 * grass[..., None]
WETNESS = np.clip(np.maximum(np.maximum(edge, wsand), puddle * 1.2), 0, 1)

# ---------------------------------------------------------------------------------------------------- 6. the jungle
rng = np.random.default_rng(KS * 1000 + 7)
SP = 11.0
gx, gy = np.meshgrid(np.arange(X0 + SP / 2, X1, SP), np.arange(Y0 + SP / 2, Y1, SP))
px = (gx + rng.uniform(-0.45, 0.45, gx.shape) * SP).ravel()
py = (gy + rng.uniform(-0.45, 0.45, gy.shape) * SP).ravel()


def grid_at(A, x, y):
    i = np.clip(np.round((x - X0) / RES).astype(int), 0, NX - 1)
    j = np.clip(np.round((y - Y0) / RES).astype(int), 0, NY - 1)
    return A[j, i]


# the forest edge is a wall of green down to the ground: a denser band of understory 9-30 m from the road
bx, by = np.meshgrid(np.arange(X0 + 2.5, X1, 5.0), np.arange(Y0 + 2.5, Y1, 5.0))
bx = (bx + rng.uniform(-2.2, 2.2, bx.shape)).ravel()
by = (by + rng.uniform(-2.2, 2.2, by.shape)).ravel()
band = grid_at(D_EDGE, bx, by)
bsel = (band > 8.0) & (band < 30.0) & (rng.random(len(bx)) < 0.55)
px, py = np.concatenate([px, bx[bsel]]), np.concatenate([py, by[bsel]])
EDGE_BAND = np.concatenate([np.zeros(len(px) - int(bsel.sum()), bool), np.ones(int(bsel.sum()), bool)])
pz = bilinear(H, px, py)
pedge = grid_at(D_EDGE, px, py)
pdepth = W - pz
pig = grid_at(F.get("igapo", np.zeros_like(H)), px, py)
pfar = grid_at(np.minimum(D_ROAD, D_FORK + 30), px, py)
keep = (pedge > 9.0) & ((pdepth < -0.05) | ((pig > 0.3) & (pdepth < 1.6)))
px, py, pz, pedge, pdepth, pig, pfar = px[keep], py[keep], pz[keep], pedge[keep], pdepth[keep], pig[keep], pfar[keep]
EDGE_BAND = EDGE_BAND[keep]
u = rng.random(len(px))
K = {k: i for i, k in enumerate(jk.KINDS)}
kind = np.full(len(px), K["canopy_a"])
interior = np.select([u < 0.36, u < 0.68, u < 0.88, u < 0.95], [K["canopy_a"], K["canopy_c"], K["canopy_b"], K["acai"]],
                     K["shrub_a"])
edgek = np.select([u < 0.30, u < 0.50, u < 0.65, u < 0.85, u < 0.93], [K["shrub_a"], K["cecropia"], K["acai"], K["canopy_b"],
                                                                      K["shrub_b"]], K["canopy_a"])
wetk = np.select([u < 0.30, u < 0.50, u < 0.65, u < 0.90], [K["acai"], K["cecropia"], K["buriti"], K["canopy_b"]], K["shrub_b"])
igk = np.select([u < 0.35, u < 0.60, u < 0.80], [K["canopy_b"], K["acai"], K["buriti"]], K["canopy_a"])
kind = np.where(pdepth > -0.9, wetk, interior)
kind = np.where(pedge < 32.0, edgek, kind)
kind = np.where(pig > 0.3, igk, kind)
bandk = np.select([u < 0.40, u < 0.62, u < 0.78, u < 0.90], [K["shrub_a"], K["shrub_b"], K["acai"], K["canopy_b"]], K["cecropia"])
kind = np.where(EDGE_BAND, bandk, kind)
# emergent kapoks: sparse everywhere, and some heroes standing right by the road
kx = rng.uniform(X0, X1, int((X1 - X0) * (Y1 - Y0) / 150.0 ** 2))
ky = rng.uniform(Y0, Y1, len(kx))
ke = grid_at(D_EDGE, kx, ky)
kd = W - bilinear(H, kx, ky)
okk = (ke > 26.0) & (kd < -0.2)
hero = np.arange(0, len(RP), 420)
hside = np.where(np.arange(len(hero)) % 2 == 0, 1.0, -1.0)
tdir = RP[np.minimum(hero + 5, len(RP) - 1)] - RP[np.maximum(hero - 5, 0)]
tdir = tdir / np.maximum(np.linalg.norm(tdir, axis=1, keepdims=True), 1e-9)
hx = RP[hero, 0] - tdir[:, 1] * hside * (RW[hero] + rng.uniform(34, 55, len(hero)))
hy = RP[hero, 1] + tdir[:, 0] * hside * (RW[hero] + rng.uniform(34, 55, len(hero)))
okh = (grid_at(D_EDGE, hx, hy) > 24.0) & (W - bilinear(H, hx, hy) < -0.2)
kx, ky = np.concatenate([kx[okk], hx[okh]]), np.concatenate([ky[okk], hy[okh]])
# no ordinary tree inside a kapok's crown
if len(kx):
    dk = np.full(len(px), 1e9)
    for a in range(0, len(kx), 200):
        dd = np.hypot(px[:, None] - kx[None, a:a + 200], py[:, None] - ky[None, a:a + 200]).min(1)
        dk = np.minimum(dk, dd)
    clear = dk > 9.0
    px, py, pz, kind, pfar, EDGE_BAND = px[clear], py[clear], pz[clear], kind[clear], pfar[clear], EDGE_BAND[clear]
px = np.concatenate([px, kx])
py = np.concatenate([py, ky])
pz = np.concatenate([pz, bilinear(H, kx, ky)])
kind = np.concatenate([kind, np.full(len(kx), K["kapok"])])
pfar = np.concatenate([pfar, grid_at(np.minimum(D_ROAD, D_FORK + 30), kx, ky)])
# far from the road: blobs instead of leaf cards; the understory there is never seen
FAR = 480.0
far = pfar > FAR
swap = {K["canopy_a"]: K["far_a"], K["canopy_b"]: K["far_b"], K["canopy_c"]: K["far_c"], K["kapok"]: K["far_kapok"]}
small = np.isin(kind, [K["shrub_a"], K["shrub_b"], K["acai"], K["cecropia"], K["buriti"]])
keep = ~(far & small & (rng.random(len(kind)) < 0.85))
EDGE_BAND = np.concatenate([EDGE_BAND, np.zeros(len(kx), bool)])[keep]
px, py, pz, kind, far = px[keep], py[keep], pz[keep], kind[keep], far[keep]
for a, b in swap.items():
    kind = np.where(far & (kind == a), b, kind)
yaw = rng.uniform(0, 360, len(px))
scl = np.where(np.isin(kind, [K["kapok"], K["far_kapok"]]), rng.uniform(0.9, 1.12, len(px)), rng.uniform(0.75, 1.25, len(px)))
young = EDGE_BAND & (kind == K["canopy_b"])
scl = np.where(young, rng.uniform(0.45, 0.7, len(px)), scl)      # young trees at the edge
log("jungle: %d plants (%s)" % (len(px), ", ".join("%s %d" % (k, int((kind == i).sum())) for i, k in enumerate(jk.KINDS))))

# ---------------------------------------------------------------------------------------------------- 7. files for Unreal
zmin, zmax = float(H.min()) - 1.0, float(H.max()) + 1.0
h16 = np.round((H - zmin) / (zmax - zmin) * 65535).astype("<u2")
h16.tofile(os.path.join(OUT, "selva_%s_height.r16" % SECTOR))
meta = dict(sector=SNAME, box=[X0, Y0, X1, Y1], res_m=RES, size=[NX, NY], z_min=zmin, z_max=zmax, water_m=W,
            note="r16: uint16 little-endian, row 0 = south (y = box[1]), height = z_min + v/65535*(z_max-z_min)",
            road=dict(from_m=int(rlo), points=RP[::5].round(2).tolist(), z=RZ2[::5].round(2).tolist()), jumps=JREC,
            forks=fork_rec)
json.dump(meta, open(os.path.join(OUT, "selva_%s.json" % SECTOR), "w", encoding="utf-8"), ensure_ascii=False)
props = [[jk.KINDS[k], round(float(x), 2), round(float(y), 2), round(float(z), 2), round(float(a), 1), round(float(s), 3)]
         for k, x, y, z, a, s in zip(kind, px, py, pz, yaw, scl)]
json.dump(props, open(os.path.join(OUT, "selva_%s_props.json" % SECTOR), "w"))
log("files written: height %d x %d, %d props" % (NX, NY, len(props)))

# ---------------------------------------------------------------------------------------------------- 8. the scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
kit, mats = jk.build_kit(os.path.join(OUT, "kit_tex"))
cx, cy = 0.5 * (X0 + X1), 0.5 * (Y0 + Y1)          # the scene is centred on the box (Blender's float precision)
me = bpy.data.meshes.new("Terrain")
me.vertices.add(NX * NY)
me.vertices.foreach_set("co", np.stack([XX - cx, YY - cy, H], -1).astype(np.float32).ravel())
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
wa = me.attributes.new("Wet", "FLOAT", "POINT")
wa.data.foreach_set("value", WETNESS.astype(np.float32).ravel())
terrain = bpy.data.objects.new("Terrain", me)
scene.collection.objects.link(terrain)


def terrain_material():
    m = bpy.data.materials.new("M_SelvaGround")
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    a = nt.nodes.new("ShaderNodeAttribute"); a.attribute_name = "Col"
    wv = nt.nodes.new("ShaderNodeAttribute"); wv.attribute_name = "Wet"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.35; nz.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[3].default_value, mr.inputs[4].default_value = 0.75, 1.2
    nt.links.new(nz.outputs["Fac"], mr.inputs[0])
    sc = nt.nodes.new("ShaderNodeVectorMath"); sc.operation = "SCALE"
    nt.links.new(a.outputs["Color"], sc.inputs[0])
    nt.links.new(mr.outputs[0], sc.inputs["Scale"])
    rough = nt.nodes.new("ShaderNodeMapRange"); rough.inputs[3].default_value, rough.inputs[4].default_value = 0.92, 0.3
    nt.links.new(wv.outputs["Fac"], rough.inputs[0])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(sc.outputs[0], bs.inputs["Base Color"])
    nt.links.new(rough.outputs[0], bs.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 4.0; nz2.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    nt.links.new(nz2.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bs.inputs["Normal"])
    jk.finish(m, bs.outputs[0])
    return m


def carpet_material():
    """Seen from the air, far away: tree crowns 15-25 m across (voronoi cells), each its own green, in the haze."""
    m = bpy.data.materials.new("M_CanopyCarpet")
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 0.055
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.020, 0.050, 0.012, 1)
    ramp.color_ramp.elements[1].color = (0.065, 0.120, 0.026, 1)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(vor.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs[0], ramp.inputs[0])
    dk = nt.nodes.new("ShaderNodeMapRange"); dk.inputs[3].default_value, dk.inputs[4].default_value = 1.15, 0.45
    nt.links.new(vor.outputs["Distance"], dk.inputs[0])
    mul = nt.nodes.new("ShaderNodeVectorMath"); mul.operation = "SCALE"
    nt.links.new(ramp.outputs[0], mul.inputs[0])
    nt.links.new(dk.outputs[0], mul.inputs["Scale"])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.8
    nt.links.new(mul.outputs[0], bs.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 6.0
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "MULTIPLY"; inv.inputs[1].default_value = -1.0
    nt.links.new(vor.outputs["Distance"], inv.inputs[0])
    nt.links.new(inv.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bs.inputs["Normal"])
    jk.finish(m, bs.outputs[0])
    return m


def water_material():
    m = bpy.data.materials.new("M_SelvaWater")
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Base Color"].default_value = (*srgb((0.36, 0.28, 0.17)), 1)       # várzea 'white water': café com leite
    bs.inputs["Roughness"].default_value = 0.05
    bs.inputs["IOR"].default_value = 1.33
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.08; nz.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bs.inputs["Normal"])
    jk.finish(m, bs.outputs[0])
    return m


me.materials.append(terrain_material())
wme = bpy.data.meshes.new("Water")
wme.from_pydata([(X0 - cx, Y0 - cy, W), (X1 - cx, Y0 - cy, W), (X1 - cx, Y1 - cy, W), (X0 - cx, Y1 - cy, W)], [], [(0, 1, 2, 3)])
# beyond the box, for the photos only: the canopy goes on for ever (a frame at canopy height round the terrain)
BIG, CZ = 40000.0, W + 24.0
fv, ff = [], []
ax_, ay_ = [-BIG, X0 - cx, X1 - cx, BIG], [-BIG, Y0 - cy, Y1 - cy, BIG]
for a in range(3):
    for b in range(3):
        if a == 1 and b == 1:
            continue
        k0 = len(fv)
        fv += [(ax_[a], ay_[b], CZ), (ax_[a + 1], ay_[b], CZ), (ax_[a + 1], ay_[b + 1], CZ), (ax_[a], ay_[b + 1], CZ)]
        ff.append((k0, k0 + 1, k0 + 2, k0 + 3))
cme = bpy.data.meshes.new("CanopyBeyond")
cme.from_pydata(fv, [], ff)
wme.materials.append(water_material())
water = bpy.data.objects.new("Water", wme)
scene.collection.objects.link(water)

cme.materials.append(carpet_material())
beyond = bpy.data.objects.new("CanopyBeyond", cme)
scene.collection.objects.link(beyond)
# the plant kit and the scatter (geometry nodes: one point per plant, instance picked by 'kind')
scene.collection.children.link(kit)
bpy.context.view_layer.layer_collection.children[kit.name].exclude = True
pm = bpy.data.meshes.new("JunglePoints")
pm.vertices.add(len(px))
pm.vertices.foreach_set("co", np.stack([px - cx, py - cy, pz - 0.4], 1).astype(np.float32).ravel())
for nm, typ, val in (("kind", "INT", kind.astype(np.int32)), ("yaw", "FLOAT", np.radians(yaw).astype(np.float32)),
                     ("scl", "FLOAT", scl.astype(np.float32))):
    at_ = pm.attributes.new(nm, typ, "POINT")
    at_.data.foreach_set("value", val)
jungle = bpy.data.objects.new("Jungle", pm)
scene.collection.objects.link(jungle)
ng = bpy.data.node_groups.new("JungleScatter", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
n_, l_ = ng.nodes, ng.links
gi, go = n_.new("NodeGroupInput"), n_.new("NodeGroupOutput")
ci = n_.new("GeometryNodeCollectionInfo")
ci.inputs["Collection"].default_value = kit
ci.inputs["Separate Children"].default_value = True
ci.inputs["Reset Children"].default_value = True
iop = n_.new("GeometryNodeInstanceOnPoints")
iop.inputs["Pick Instance"].default_value = True
na_k = n_.new("GeometryNodeInputNamedAttribute"); na_k.data_type = "INT"; na_k.inputs["Name"].default_value = "kind"
na_y = n_.new("GeometryNodeInputNamedAttribute"); na_y.data_type = "FLOAT"; na_y.inputs["Name"].default_value = "yaw"
na_s = n_.new("GeometryNodeInputNamedAttribute"); na_s.data_type = "FLOAT"; na_s.inputs["Name"].default_value = "scl"
cmb = n_.new("ShaderNodeCombineXYZ")
l_.new(na_y.outputs["Attribute"], cmb.inputs["Z"])
l_.new(gi.outputs[0], iop.inputs["Points"])
l_.new(ci.outputs[0], iop.inputs["Instance"])
l_.new(na_k.outputs["Attribute"], iop.inputs["Instance Index"])
l_.new(cmb.outputs[0], iop.inputs["Rotation"])
l_.new(na_s.outputs["Attribute"], iop.inputs["Scale"])
l_.new(iop.outputs[0], go.inputs[0])
mod = jungle.modifiers.new("Scatter", "NODES")
mod.node_group = ng


def log_object(at_m):
    """The giant fallen trunk across the road (a dead sumaúma, mossy), longer than the road is wide (the root plate in the
    forest), its top a little above the sand ramp's crest."""
    i = int(at_m) - rlo
    t = RP[i + 5] - RP[i - 5]
    hd = math.atan2(t[1], t[0])
    mb = jk.MB()
    L, R0 = 84.0, 2.4
    P = np.stack([np.linspace(-L / 2, L / 2, 9), np.zeros(9), np.zeros(9)], 1)
    mb.tube(P, np.linspace(R0, R0 * 0.72, 9), "bark", seg=14)
    lr = np.random.default_rng(5)
    for k in range(9):                       # the root plate at one end
        a = 2 * math.pi * k / 9
        e = np.array([-L / 2 - 0.5, math.cos(a) * lr.uniform(4.5, 7.0), math.sin(a) * lr.uniform(4.5, 7.0)])
        mb.tube([np.array([-L / 2, 0, 0]), e], [0.9, 0.25], "bark", seg=6)
    o = mb.build("TroncoCaido", {"bark": bpy.data.materials["M_Bark"]})
    o.location = (RP[i, 0] - cx, RP[i, 1] - cy, RZ2[i] - R0 + 1.0)      # 1 m proud of the crest: under a hovering ship
    o.rotation_euler = (0, 0, hd + math.radians(68))
    scene.collection.objects.link(o)


for j in JREC:
    if j["what"] == "tronco caído":
        log_object(j["at_m"])

# sky, sun, camera, render (as Red Dust Divide's photos: Scripts/sculpt_expedition_ab.py)
w_ = bpy.data.worlds.new("Sky")
w_.use_nodes = True
sky = w_.node_tree.nodes.new("ShaderNodeTexSky")
for t_name in ("NISHITA", "MULTIPLE_SCATTERING"):
    try:
        sky.sky_type = t_name
        break
    except TypeError:
        pass
SUN_ELEV, SUN_AZ = math.radians(34), math.radians(-35)
sky.sun_elevation, sky.sun_rotation, sky.sun_disc = SUN_ELEV, SUN_AZ + math.pi, False
for attr_, val in (("air_density", 1.2), ("dust_density", 3.5), ("aerosol_density", 3.5)):
    if hasattr(sky, attr_):
        setattr(sky, attr_, val)
w_.node_tree.links.new(sky.outputs["Color"], w_.node_tree.nodes["Background"].inputs[0])
w_.node_tree.nodes["Background"].inputs[1].default_value = 0.14
scene.world = w_
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy, sun.data.angle, sun.data.color = 3.6, math.radians(1.5), (1.0, 0.90, 0.76)
sun.rotation_euler = (math.pi / 2 - SUN_ELEV, 0, SUN_AZ)
scene.collection.objects.link(sun)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.transparent_max_bounces = 24
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces, scene.cycles.glossy_bounces, scene.cycles.transmission_bounces = 2, 2, 2
try:
    scene.view_settings.look = "AgX - Punchy"
except TypeError:
    pass
scene.render.resolution_x, scene.render.resolution_y = SIZE
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.clip_end = 30000
scene.collection.objects.link(cam)
scene.camera = cam
ship = None
ship_path = OPTS.get("ship", os.path.join(HERE, "..", "..", "SourceArt", "TestShips", "strix.fbx"))
if os.path.isfile(ship_path) and "noship" not in FLAGS:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=ship_path)
    parts = [o for o in bpy.data.objects if o not in before]
    ship = bpy.data.objects.new("Ship", None)
    scene.collection.objects.link(ship)
    for o in parts:
        if o.parent is None:
            o.parent = ship
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "selva_%s.blend" % SECTOR))
log("scene saved")
if "noshots" in FLAGS:
    raise SystemExit


def zroad(i):
    return float(RZ2[int(np.clip(i, 0, len(RZ2) - 1))])


def shot(name, eye, tgt, lens, haze=None):
    if ONLY and name not in ONLY:
        return
    jk.FOG.update(haze or dict(start=90.0, dist=2600.0, amount=0.88))
    jk.fog_group()
    cam.data.lens = lens
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(OUT, "selva_%s_%s.png" % (SECTOR, name))
    t = time.time()
    bpy.ops.render.render(write_still=True)
    log("SHOT", name, "%.0fs" % (time.time() - t))


def pilot(name, i, up=4.0, ahead=200, lens=22, P=RP, Z=None):
    Z = RZ2 if Z is None else Z
    i = int(np.clip(i, 0, len(P) - 2))
    j = int(min(len(P) - 1, i + ahead))
    eye = Vector((P[i, 0] - cx, P[i, 1] - cy, float(Z[i]) + up))
    tgt = Vector((P[j, 0] - cx, P[j, 1] - cy, float(Z[j]) + up * 0.5))
    if ship is not None:
        k = int(min(len(P) - 2, i + 26))
        t = P[k + 1] - P[k - 1]
        ship.location = (P[k, 0] - cx, P[k, 1] - cy, float(Z[k]) + 1.6)
        ship.rotation_euler = Euler((0, 0, math.atan2(t[1], t[0]) - math.pi / 2))
        ship.hide_render = False
    shot(name, eye, tgt, lens)


def side_view(name, i, off=20.0, back=75.0, up=15.0, lens=26):
    """A jump seen from the side of the road, a little before it: the kicker, the gap or the trunk, the landing."""
    i = int(np.clip(i, 10, len(RP) - 11))
    t = RP[i + 10] - RP[i - 10]
    t = t / max(np.linalg.norm(t), 1e-9)
    nrm = np.array([-t[1], t[0]])
    e = RP[i] - t * back + nrm * off
    if ship is not None:
        k = i - 30
        tt = RP[k + 1] - RP[k - 1]
        ship.location = (RP[k, 0] - cx, RP[k, 1] - cy, float(RZ2[k]) + 1.6)
        ship.rotation_euler = Euler((0, 0, math.atan2(tt[1], tt[0]) - math.pi / 2))
        ship.hide_render = False
    base = float(RZ2[i - 60])
    eye = Vector((e[0] - cx, e[1] - cy, base + up))
    tgt = Vector((RP[i, 0] + t[0] * 12 - cx, RP[i, 1] + t[1] * 12 - cy, base))
    shot(name, eye, tgt, lens)


def aerial(name, eye_xy, up, tgt_xy, lens=26):
    if ship is not None:
        ship.hide_render = True
    eye = Vector((eye_xy[0] - cx, eye_xy[1] - cy, float(bilinear(H, *eye_xy)) + up))
    tgt = Vector((tgt_xy[0] - cx, tgt_xy[1] - cy, float(bilinear(H, *tgt_xy))))
    shot(name, eye, tgt, lens, haze=dict(start=900.0, dist=14000.0, amount=0.6))


# the photos: the start at A, along the floodplain, the jumps, the forks, and the whole sector from the air
si = lambda m: int(m) - rlo
pilot("piloto_partida", si(S0 + 25))
for j in JREC:
    tag = "piloto_" + j["what"].replace(" ", "_").replace("í", "i").replace("é", "e")
    pilot(tag, si(j["at_m"]) - 115, ahead=170)
    side_view(tag.replace("piloto_", "salto_"), si(j["at_m"]))
for fd in FD:
    nm = fd["f"]["name"].split()[0]
    zf = bilinear(H, fd["P"][:, 0], fd["P"][:, 1])
    pilot("piloto_" + nm, int(0.35 * len(fd["P"])), P=fd["P"], Z=zf)
pilot("piloto_reta", si(S0 + int(0.55 * (S1_ - S0))))
mid = RP[si((S0 + S1_) // 2)]
aerial("aerea", (mid[0] - 600, mid[1] - 1500), 620, (mid[0] + 400, mid[1] + 250), lens=24)
aerial("aerea_partida", (RP[si(S0)][0] - 700, RP[si(S0)][1] - 900), 380, (RP[si(S0 + 900)][0], RP[si(S0 + 900)][1]), lens=28)
log("DONE")
