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
forks = [f for f in plan["forks"] if S0 <= 0.5 * (f["leave_m"] + f["rejoin_m"]) <= S1_]   # where its middle is
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


def membrane(step=25, blur=45.0):
    """A smooth ground through the road's own heights (each switchback leg lies on its hillside): linear between road
    points of the whole route near the box, then blurred."""
    from scipy.interpolate import griddata
    sel = (road[:, 0] > X0 - 1500) & (road[:, 0] < X1 + 1500) & (road[:, 1] > Y0 - 1500) & (road[:, 1] < Y1 + 1500)
    idx = np.flatnonzero(sel)[::step]
    lin = griddata(road[idx], road_z[idx], (XX, YY), method="linear")
    near = griddata(road[idx], road_z[idx], (XX, YY), method="nearest")
    return ndimage.gaussian_filter(np.where(np.isnan(lin), near, lin), blur / RES)


def recipe_s2():
    """S2 Serra Vermelha (Congo): the switchbacks climb a hillside of red laterite under the forest. The ground is a
    smooth surface through the road's heights (each leg on its terrace), with hills, spurs and gullies away from it."""
    G = membrane()
    d, _fi, _sd = line_field(RP)
    away = smoothstep(30.0, 400.0, d)
    relief = 26.0 * (fbm(XX, YY, 520.0, 211, 4) - 0.5) + 7.0 * (fbm(XX, YY, 110.0, 223, 3) - 0.5)
    gully = smoothstep(0.82, 0.95, 1 - np.abs(2 * fbm(XX, YY, 300.0, 227, 3) - 1))
    return -1000.0, G + away * (relief - 9.0 * gully), np.zeros_like(G), dict()


LIP_S3, W_TOP, W_LOW = np.array([10500.0, 4205.0]), 248.5, 61.5


def recipe_s3():
    """S3 Salto Kaieteur (Guiana): the ridge-top plateau and its river, which leaps ~187 m off the escarpment into a
    plunge pool at the head of a cliff-walled gorge. The road crosses the river on the slab above the lip and goes down
    the long slope beside the gorge; the gorge widens downstream into the Congo's valley (S4)."""
    G = membrane()
    G += 5.0 * (fbm(XX, YY, 420.0, 301, 4) - 0.5) * smoothstep(20.0, 220.0, line_field(RP)[0])
    rv = [r for r in rivers if r["name"] == "Congo"][0]["P"]
    up = rv[rv[:, 1] >= LIP_S3[1]]
    down = rv[rv[:, 1] <= LIP_S3[1]]
    du, fu, _s = line_field(up, reach=3)
    wu = 44.0 + 10.0 * np.sin(fu / 120.0)
    plateau = (du < 700.0) & (YY > LIP_S3[1] - 4.0)
    G = np.where(plateau, np.maximum(G, W_TOP + 2.5 + 3.0 * fbm(XX, YY, 150.0, 303, 3)), G)     # banks above the river
    bed = W_TOP - 3.0
    G = np.where(plateau, np.minimum(G, bed + (G - bed) * smoothstep(0.8 * wu, wu + 30.0, du)), G)
    # the gorge: a floor 90 m wide at the pool, 310 m downstream, between 76-degree cliffs; nothing upstream of the lip
    dg, fg, _s = line_field(down, reach=3)
    sg = fg * 2.0
    wg = 90.0 + np.clip(sg / 1500.0, 0, 1) * 220.0
    floor = W_LOW - 4.0 - 0.0015 * sg
    below = (YY < LIP_S3[1] - 8.0) | (np.hypot(XX - LIP_S3[0], YY - LIP_S3[1]) > 450.0)
    jag = 22.0 * (fbm(XX, YY, 110.0, 311, 4) - 0.5)
    wall = floor + np.maximum(0.0, dg - wg + jag) * 4.0
    wall = wall + 2.5 * np.sin(wall / 7.0)                        # sandstone beds: ledges up the cliff
    G = np.where(below, np.minimum(G, wall), G)
    dp = np.hypot(XX - (LIP_S3[0] + 15.0), YY - (LIP_S3[1] - 150.0))         # the plunge pool
    G = np.where(below, np.minimum(G, W_LOW - 12.0 + np.maximum(0.0, dp - 150.0 + jag) * 4.0), G)
    WLs = np.where((du < wu + 40.0) & (YY > LIP_S3[1] - 2.0) & plateau, W_TOP, W_LOW)
    k = int(np.argmin(np.hypot(RP[:, 0] - up[:, 0].mean(), 0) + np.min(np.hypot(RP[:, None, 0] - up[None, ::20, 0],
                                                                                  RP[:, None, 1] - up[None, ::20, 1]), 1)))
    half = float(bilinear(wu, RP[k, 0], RP[k, 1])) + 12.0
    return WLs, G, np.zeros_like(G), dict(laje_half=half)


def recipe_s4():
    """S4 Corredeiras do Congo: the Congo's valley below the falls, forested hills either side. The river falls from the
    gorge (61.5 m) to ~36 m along the sector; the road runs a few hundred metres from it, over tributaries and rapid
    streams (its jumps); F6 runs down a side arm of the river from island to island; F7 down a dry old bed."""
    G = membrane()
    d, _fi, _sd = line_field(RP)
    G = G + smoothstep(60.0, 450.0, d) * (30.0 * (fbm(XX, YY, 600.0, 411, 4) - 0.35) + 8.0 * (fbm(XX, YY, 120.0, 413, 3) - 0.5))
    lev = lambda x: np.clip(61.5 - (x - 11400.0) * (61.5 - 36.0) / (18800.0 - 11400.0), 34.0, 61.5)
    rv = [r for r in rivers if r["name"] == "Congo"][0]["P"]
    dr, fr, _s = line_field(rv, reach=3)
    lv = lev(XX)
    wr = 85.0 * (1 + 0.15 * np.sin(fr / 190.0))
    near = dr < wr + 260.0
    G = np.where(near & (dr > wr), np.maximum(G, lv + 1.5 + 2.0 * fbm(XX, YY, 90.0, 415, 3) * smoothstep(wr, wr + 80.0, dr)), G)
    G = np.where(dr < wr + 40.0, np.minimum(G, lv - 6.0 + 7.5 * smoothstep(0.85 * wr, wr + 40.0, dr)), G)
    WL = np.where(near, lv, -1000.0)
    # F6: a side arm of the river round its islands (the islands are the fork itself, laid later)
    for fd in FD:
        if "Ilhas" in fd["f"]["name"]:
            df_, fi_, _s = line_field(fd["P"], reach=3)
            zarm = at(fd["z"], fi_) - 3.0
            arm = df_ < 75.0
            G = np.where(arm, np.minimum(G, zarm - 2.5 + 4.0 * smoothstep(55.0, 75.0, df_)), G)
            WL = np.where(df_ < 80.0, zarm, WL)
    # the streams the road leaps (tributaries and rapids), each across the road at its jump
    rng = np.random.default_rng(417)
    for j in jumps:
        if j["what"].startswith(("afluente", "rápido")):
            i = int(j["at_m"]) - rlo
            t = RP[min(i + 5, len(RP) - 1)] - RP[max(i - 5, 0)]
            hd = math.atan2(t[1], t[0]) + math.pi / 2
            C = np.vstack([creek(rng, RP[i], hd + math.pi, 700, 0.3)[::-1], creek(rng, RP[i], hd, 700, 0.3)[1:]])
            dc, _f, _s = line_field(C, reach=3)
            wl_c = float(RZ[i]) - 3.0
            wc = 14.0 if j["what"].startswith("afluente") else 10.0
            G = np.where(dc < wc * 1.8, np.minimum(G, wl_c - 1.8 + 3.0 * smoothstep(wc * 0.6, wc * 1.8, dc)), G)
            WL = np.where(dc < wc * 2.0, wl_c, WL)
    return WL, G, np.zeros_like(G), dict()


def recipe_s5():
    """S5 Gruta das Raízes: a long hill held together by kapok roots. Its crest is F8 (over the top, through the roots);
    under it the road runs through a wide cave, with F9 and the underground river beside it, lower down (section 4b)."""
    G = membrane()
    d, _fi, _sd = line_field(RP)
    G = G + smoothstep(60.0, 450.0, d) * (24.0 * (fbm(XX, YY, 600.0, 511, 4) - 0.35))
    f8 = [fd for fd in FD if "Raízes Gigantes" in fd["f"]["name"]][0]
    d8, f8i, _s = line_field(f8["P"], reach=3)
    G = np.maximum(G, at(f8["z"], f8i) - 1.5 - 0.22 * np.maximum(d8 - 18.0, 0.0) + 3.0 * (fbm(XX, YY, 80.0, 513, 3) - 0.5))
    ib, isd = CAVE_SPAN[0] - rlo, CAVE_SPAN[1] - rlo
    dC, fC, _s = line_field(RP[ib:isd], reach=3)
    cover = at(RZ[ib:isd], fC) + 34.0 + 6.0 * fbm(XX, YY, 120.0, 515, 3) - 0.25 * np.maximum(dC - 70.0, 0.0)
    G = np.maximum(G, np.where((dC < 400.0) & (fC > 2) & (fC < isd - ib - 3), cover, -1e9))
    return -1000.0, G, np.zeros_like(G), dict()


def recipe_s6():
    """S6 Mangue Labirinto (Niger delta / Amazon mouth): tidal mud a hand above or below the water, the plan's big
    channels and a labyrinth of creeks between the mangroves; the road on a mud causeway, canals across it to jump."""
    W = float(np.floor(RZ[S0 - rlo:S1_ - rlo].min() - 1.5))
    rng = np.random.default_rng(611)
    base = W + 0.2 + 1.3 * (fbm(XX, YY, 260.0, 613, 4) - 0.5) + 0.4 * (fbm(XX, YY, 45.0, 617, 3) - 0.5)
    for rv in rivers:
        dr, fr, _s = line_field(rv["P"], reach=3)
        wr = 0.5 * rv["w"] * (1 + 0.2 * np.sin(fr / 150.0))
        base = np.where(dr < wr + 30.0, np.minimum(base, W - 4.0 + 4.5 * smoothstep(0.7 * wr, wr + 30.0, dr)), base)
    creeks = []
    for j in jumps:
        if j["what"].startswith("canal"):
            i = int(j["at_m"]) - rlo
            t = RP[min(i + 5, len(RP) - 1)] - RP[max(i - 5, 0)]
            hd = math.atan2(t[1], t[0]) + math.pi / 2
            creeks.append(np.vstack([creek(rng, RP[i], hd + math.pi, 900, 0.3)[::-1], creek(rng, RP[i], hd, 900, 0.3)[1:]]))
    for k in range(16):
        creeks.append(creek(rng, (rng.uniform(X0, X1), rng.uniform(Y0, Y1)), rng.uniform(0, 2 * np.pi), rng.uniform(700, 1600), 0.45))
    for C in creeks:
        dc, fi, _s = line_field(C, reach=2)
        wc = 9.0 + 5.0 * np.sin(fi / 90.0)
        base = np.where(dc < wc * 1.7, np.minimum(base, W - 2.0 + 3.0 * smoothstep(0.6 * wc, 1.7 * wc, dc)), base)
    return W, base, np.zeros_like(base), dict()


TEPUI = dict(c=(10150.0, 8250.0), a=1300.0, b=750.0, ang=math.radians(20.0), top=520.0)
# Rivers the road runs in (jogador, 2026-11-02, S6: "gostei muito do rio; ver mais disso no mapa: o rio a encontrar com
# a terra, árvores, raízes, as naves andam aí no rio mesmo"): per sector, (from, to) in metres along the route; the
# road is the river's bed, 12 cm under the water, 10 m wider than the road; trees with stilt roots stand at its edges.
RIVER_ROADS = {"S7": [(38440, 40700)]}
FALLS = []                               # (lip xy, direction xy, top z, bottom z, width): waterfalls to build


def recipe_s7():
    """S7 Tepui (Roraima): a table mountain 520 m high, its rim wandering, 80-degree cliffs of dark sandstone down to a
    scree apron, blocks and fissures on its top. A tall thin waterfall leaves its south face; from its pool a creek
    runs down to the river the road follows upstream at the start of the sector (RIVER_ROADS)."""
    G = membrane()
    d, _fi, _sd = line_field(RP)
    G = G + smoothstep(60.0, 450.0, d) * (26.0 * (fbm(XX, YY, 600.0, 711, 4) - 0.4))
    (tx, ty), a, b, ang, top = TEPUI["c"], TEPUI["a"], TEPUI["b"], TEPUI["ang"], TEPUI["top"]
    u = (XX - tx) * math.cos(ang) + (YY - ty) * math.sin(ang)
    v = -(XX - tx) * math.sin(ang) + (YY - ty) * math.cos(ang)
    rr = (np.sqrt((u / a) ** 2 + (v / b) ** 2) + 0.24 * (fbm(XX, YY, 520.0, 713, 3) - 0.5)
          + 0.08 * (fbm(XX, YY, 140.0, 714, 2) - 0.5))                       # bays and promontories round the rim
    inside = rr < 1.0
    dout = ndimage.distance_transform_edt(~inside) * RES
    blocks = 14.0 * np.floor(fbm(XX, YY, 160.0, 717, 2) * 4.0) / 4.0 + 5.0 * (fbm(XX, YY, 40.0, 719, 2) - 0.5)
    ledge = 18.0 + 14.0 * fbm(XX, YY, 260.0, 721, 2)                            # a ledge half way down, 18-32 m wide
    cliff = top - 5.5 * np.minimum(dout, 25.0) - 5.5 * np.maximum(0.0, dout - 25.0 - ledge)
    tep = np.where(inside, top - 10.0 + blocks, np.maximum(cliff, G + np.maximum(0.0, 110.0 - dout) * 0.7))
    G = np.maximum(G, tep)
    # F12's ramp: a natural spur of rock up to the top and down again (Roraima's "La Rampa"), not a bridge
    f12 = [fd for fd in FD if "Topo do Tepui" in fd["f"]["name"]]
    if f12:
        d12, f12i, _s = line_field(f12[0]["P"], reach=3)
        G = np.maximum(G, at(f12[0]["z"], f12i) - 1.5 - 1.0 * np.maximum(d12 - 18.0, 0.0))
    WL = np.full_like(G, -1000.0)
    # the waterfall: on the south rim, nearest the river's upstream end
    end = RP[RIVER_ROADS["S7"][0][1] - rlo]
    rim = np.argwhere(inside & (dout == 0) & ~ndimage.binary_erosion(inside))
    if len(rim):
        rx, ry = X0 + rim[:, 1] * RES, Y0 + rim[:, 0] * RES
        k = int(np.argmin(np.hypot(rx - end[0], ry - end[1])))
        lip = np.array([rx[k], ry[k]])
        dirv = (end - lip) / np.linalg.norm(end - lip)
        pool = lip + dirv * 75.0
        zp = float(bilinear(G, pool[0], pool[1])) - 4.0
        dpo = np.hypot(XX - pool[0], YY - pool[1])
        G = np.where(dpo < 70.0, np.minimum(G, zp - 3.0 + np.maximum(0.0, dpo - 45.0) * 0.4), G)
        WL = np.where(dpo < 60.0, zp, WL)
        # the creek from the pool to the river (its water falling evenly to the river's level)
        C = np.stack([np.linspace(pool[0], end[0], 400), np.linspace(pool[1], end[1], 400)], 1)
        C = C + np.stack([-dirv[1], dirv[0]])[None] * (35.0 * np.sin(np.linspace(0, 3 * np.pi, 400)))[:, None]
        dc, fc, _s = line_field(C, reach=3)
        zr_end = float(RZ[RIVER_ROADS["S7"][0][1] - rlo])
        lvl = zp + (zr_end + 0.12 - zp) * np.clip(fc / 399.0, 0, 1)
        G = np.where(dc < 22.0, np.minimum(G, lvl - 1.6 + 1.8 * smoothstep(9.0, 22.0, dc)), G)
        WL = np.where(dc < 18.0, lvl, WL)
        FALLS.append((lip, dirv, top - 12.0, zp, 26.0))
    return WL, G, np.zeros_like(G), dict()


def recipe_s8():
    """S8 Galeria da Savana: an open savanna plateau (~160 m), wide and fast, baobabs, acacias and termite mounds; along
    the river a band of gallery forest, dense, which F15 runs in on the water itself."""
    G = membrane()
    d, _fi, _sd = line_field(RP)
    G = G + smoothstep(80.0, 600.0, d) * (14.0 * (fbm(XX, YY, 900.0, 811, 3) - 0.4))
    rv = [r for r in rivers if r["name"] == "Rio da galeria"][0]["P"]
    dr, fr, _s = line_field(rv, reach=3)
    lv = np.minimum.accumulate(smooth_line(bilinear(G, rv[:, 0], rv[:, 1]) - 7.0, 301))
    lvl = at(lv, fr)
    wr = 55.0 * (1 + 0.2 * np.sin(fr / 140.0))
    G = np.where(dr < wr + 30.0, np.minimum(G, lvl - 2.5 + 3.0 * smoothstep(0.7 * wr, wr + 30.0, dr)), G)
    WL = np.where(dr < wr + 60.0, lvl, -1000.0)
    return WL, G, np.zeros_like(G), dict(savanna=smoothstep(150.0, 330.0, dr))


def smooth_line(v, w):
    k = np.ones(w) / w
    return np.convolve(np.pad(v, w // 2, mode="edge"), k, mode="valid")[:len(v)]


RECIPES = {"S1": recipe_s1, "S2": recipe_s2, "S3": recipe_s3, "S4": recipe_s4, "S5": recipe_s5, "S6": recipe_s6, "S7": recipe_s7,
           "S8": recipe_s8}
RIVER_FORKS = ("Floresta de Galeria", "Fundo da Garganta")   # forks that run on the river itself
WET_TREES = {"S6"}                       # mangroves stand in the water
NO_KAPOK = {"S6"}
CAVE_SPAN = None
if SECTOR == "S5":                       # from the mouth to the way out (the jumps 'boca' and 'saída' of the plan)
    CAVE_SPAN = (int(next(j["at_m"] for j in jumps if j["what"].startswith("boca"))) + 12,
                 int(next(j["at_m"] for j in jumps if j["what"].startswith("saída"))) - 12)
# Oval roads (jogador, 2026-11-02, S4: "acabou com as estradas artificiais; quero ovais que permitem ultrapassar pelas
# paredes a alta velocidade; as paredes ficam pequenas à medida que se avança, vales pequenos"): a quarter-oval wall on
# both sides, tangent to the floor and steepening towards the top (Red Dust Divide's curve walls), its height falling
# along the sector; beyond it the hillside never rises faster than Red Dust's oval bank (25 -> 70 degrees), so even
# where the walls are small the road runs in an oval valley. Per sector: (wall height at its start, at its end).
OVAL = {"S4": (14.0, 4.0), "S5": (4.0, 3.0)}
# S5 (jogador: "estrada mista"): small oval walls up to the cave, the cave's own arch inside, a natural road after it
# per sector: semi-oval walls on the outside of the hairpins (jogador, 2026-11-02: "retas, com algumas partes
# semi-ovais"), the road and bank colours (sRGB), the jungle's mix, and how far hills roll beyond the box
WALLS = {"S2": (12.0, 16.0)}
STEEP_FORKS = ("Névoa",)                 # ledges: steep banks like the ravines (BAIXO)
PAL = {"S1": dict(road=(0.60, 0.50, 0.37), wet=(0.36, 0.29, 0.21), bank=None),
       "S2": dict(road=(0.64, 0.31, 0.16), wet=(0.42, 0.20, 0.10), bank=(0.56, 0.25, 0.12)),
       "S4": dict(road=(0.50, 0.30, 0.18), wet=(0.30, 0.18, 0.11), bank=(0.34, 0.33, 0.19)),
       "S3": dict(road=(0.52, 0.43, 0.34), wet=(0.30, 0.25, 0.20), bank=(0.46, 0.38, 0.31), rock=(0.33, 0.27, 0.26))}
MIXES = {"S1": dict(interior=(("canopy_a", .36), ("canopy_c", .32), ("canopy_b", .20), ("acai", .07), ("shrub_a", .05)),
                    edge=(("shrub_a", .30), ("cecropia", .20), ("acai", .15), ("canopy_b", .20), ("shrub_b", .08), ("canopy_a", .07)),
                    band=(("shrub_a", .40), ("shrub_b", .22), ("acai", .16), ("canopy_b", .12), ("cecropia", .10))),
         "S2": dict(interior=(("canopy_a", .38), ("canopy_c", .36), ("canopy_b", .20), ("shrub_a", .06)),
                    edge=(("shrub_a", .30), ("cecropia", .25), ("canopy_b", .25), ("shrub_b", .12), ("canopy_a", .08)),
                    band=(("shrub_a", .40), ("shrub_b", .25), ("canopy_b", .20), ("cecropia", .15)))}
HILLS = {"S1": 0.3, "S2": 1.0, "S3": 1.0, "S4": 1.0}
MIXES["S4"] = MIXES["S2"]
MIXES["S5"] = MIXES["S1"]
HILLS["S5"] = 1.0
PAL["S8"] = dict(road=(0.62, 0.40, 0.24), wet=(0.40, 0.25, 0.15), bank=(0.55, 0.42, 0.26))
HILLS["S8"] = 0.6
MIXES["S8"] = dict(interior=(("canopy_a", .30), ("canopy_c", .25), ("canopy_b", .20), ("acai", .10), ("shrub_a", .15)),
                   edge=(("shrub_a", .30), ("mangrove", .25), ("canopy_b", .25), ("cecropia", .20)),
                   band=(("shrub_a", .35), ("shrub_b", .30), ("canopy_b", .20), ("mangrove", .15)),
                   savanna=(("acacia", .50), ("baobab", .12), ("shrub_b", .26), ("termite", .12)))
PAL["S7"] = dict(road=(0.40, 0.33, 0.27), wet=(0.23, 0.19, 0.16), bank=(0.30, 0.27, 0.21), rock=(0.30, 0.23, 0.21))
HILLS["S7"] = 1.0
MIXES["S7"] = dict(interior=(("canopy_a", .32), ("canopy_c", .28), ("canopy_b", .20), ("acai", .10), ("shrub_a", .10)),
                   edge=(("mangrove", .30), ("shrub_a", .25), ("cecropia", .15), ("acai", .15), ("canopy_b", .15)),
                   band=(("shrub_a", .30), ("mangrove", .25), ("shrub_b", .20), ("acai", .15), ("canopy_b", .10)))
PAL["S6"] = dict(road=(0.40, 0.35, 0.28), wet=(0.24, 0.21, 0.17), bank=(0.31, 0.28, 0.22))
HILLS["S6"] = 0.3
MIXES["S6"] = dict(interior=(("mangrove", .75), ("canopy_b", .08), ("acai", .07), ("shrub_b", .05), ("buriti", .05)),
                   edge=(("mangrove", .62), ("shrub_b", .20), ("acai", .09), ("cecropia", .09)),
                   band=(("mangrove", .58), ("shrub_b", .30), ("acai", .12)),
                   wet=(("mangrove", .86), ("acai", .05), ("buriti", .03), ("shrub_b", .06)))
CANOPY_H = {"S6": 12.0, "S8": 0.5}       # savanna: grass beyond the box, not canopy                  # the canopy's height beyond the box (mangroves are low)
PAL["S5"] = dict(road=(0.46, 0.36, 0.26), wet=(0.27, 0.21, 0.15), bank=(0.30, 0.30, 0.17), rock=(0.30, 0.25, 0.21))
MIXES["S3"] = dict(interior=(("canopy_a", .30), ("canopy_b", .25), ("canopy_c", .15), ("acai", .12), ("shrub_a", .10), ("buriti", .08)),
                   edge=(("shrub_a", .30), ("cecropia", .20), ("acai", .20), ("canopy_b", .20), ("shrub_b", .10)),
                   band=(("shrub_a", .35), ("shrub_b", .25), ("acai", .20), ("canopy_b", .20)))
W, H, WET, F = RECIPES[SECTOR]()
WLG = np.full_like(H, float(W)) if np.ndim(W) == 0 else np.asarray(W, float)
W = WLG                                   # the water level, cell by cell


def wl_at(P):
    P = np.asarray(P, float)
    return bilinear(WLG, P[:, 0], P[:, 1])


log("natural ground %.1f-%.1f m, water at %.1f m" % (H.min(), H.max(), float(np.median(WLG))))
# The road's own relief (jogador, 2026-11-02: "estrada muito plana; ondulações de lama, não em toda a estrada, natural,
# não esculpido; sem as naves andarem aos saltos"): long, low swells everywhere (+-8 cm over ~30 m), and in muddy
# patches (about 40 % of the road) deeper swells (+-22 cm) with mud undulations (+-9 cm over ~11 m). The steepest is a
# few percent: the hover pads ride it. The edges wander +-1.2 m.
MUD = smoothstep(0.42, 0.62, fbm(XX, YY, 90.0, 401, 3))
SWELL = (fbm(XX, YY, 32.0, 403, 3) - 0.5) * 2.0
RELIEF = SWELL * (0.08 + 0.14 * MUD) + MUD * (fbm(XX, YY, 11.0, 407, 2) - 0.5) * 0.18
EDGE_WOBBLE = (fbm(XX, YY, 25.0, 409, 2) - 0.5) * 2.4


# ---------------------------------------------------------------------------------------------------- 4. the road
def runs(mask):
    """(start, end) of each run of True."""
    m = np.diff(np.r_[0, np.asarray(mask, int), 0])
    return list(zip(np.flatnonzero(m == 1), np.flatnonzero(m == -1)))


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
    z = z * (1 - w8) + (wl_at(P) - 0.12) * w8
    recs = []
    for j in jumps_here:
        i = int(j["i"])
        if j["what"] == "igarapé" or j["what"].startswith(("afluente", "rápido", "canal", "último canal")):   # water gap
            s = np.arange(len(z)) - i
            g2 = 16 if j["what"] != "rápido" else 12
            kick = 2.6 * smoothstep(-70, -g2 - 2, s) * (s < -g2)
            z = z + kick
            gap = np.abs(s) <= g2
            z = np.where(gap, wl_at(P) - 1.6, z)
            recs.append(dict(what=j["what"], at_m=int(j["at_m"]), lip=float(z[i - 17]), gap_m=32, kicker_m=2.6))
        elif j["what"] == "tronco caído":    # a sand ramp up to a giant fallen trunk, then the drop off its far side
            s = np.arange(len(z)) - i
            ramp = 3.2 * smoothstep(-60, -4, s) * (s <= 4) + 3.2 * (1 - smoothstep(4, 26, s)) * (s > 4)
            z = z + ramp
            recs.append(dict(what=j["what"], at_m=int(j["at_m"]), crest=float(z[i]), ramp_m=3.2))
        elif j["what"].startswith("laje"):        # a kicker on the rock slab, and the river under the leap
            s = np.arange(len(z)) - i
            half = float(F.get("laje_half", 45.0))
            z = z + 3.0 * smoothstep(-95, -half - 2, s) * (s < -half)
            z = np.where(np.abs(s) <= half, wl_at(P) - 2.5, z)
            recs.append(dict(what=j["what"], at_m=int(j["at_m"]), lip=float(z[i - int(half) - 1]), gap_m=int(2 * half), kicker_m=3.0))
        elif j["what"].startswith(("degrau", "ressalto", "talude")):   # a step: up to a lip, then 6 m down
            s = np.arange(len(z)) - i
            z = z + 6.0 * smoothstep(-160, -10, s) * (s < 0)
            recs.append(dict(what=j["what"], at_m=int(j["at_m"]), lip=float(z[i - 1]), drop_m=6.0))
        elif j["what"].startswith("rio de areia"):   # a kicker over a dry sand river (a gap 2.5 m deep)
            s = np.arange(len(z)) - i
            z = z + 2.6 * smoothstep(-70, -18, s) * (s < -16)
            z = np.where(np.abs(s) <= 16, z - 2.5, z)
            recs.append(dict(what=j["what"], at_m=int(j["at_m"]), gap_m=32, kicker_m=2.6))
        elif j["what"].startswith(("crista", "lomba", "rampa", "ilha", "raiz", "rochedo", "boca", "saída", "termiteira")):   # a crest
            s = np.arange(len(z)) - i
            z = z + 4.0 * smoothstep(-90, -4, s) * (s <= 4) + 4.0 * (1 - smoothstep(4, 50, s)) * (s > 4)
            recs.append(dict(what=j["what"], at_m=int(j["at_m"]), crest=float(z[i]), ramp_m=4.0))
    return z, recs


def curvature(P, w=21):
    q = np.stack([ndimage.uniform_filter1d(P[:, 0], w), ndimage.uniform_filter1d(P[:, 1], w)], 1)
    d1 = np.gradient(q, axis=0)
    d2 = np.gradient(d1, axis=0)
    return (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / (np.hypot(d1[:, 0], d1[:, 1]) ** 3 + 1e-9)


def bends(P, rmax=260.0, rfull=140.0):
    """Per point: how much of a hairpin it is (0 on the straights, 1 in a bend of rfull or tighter, growing into it and
    dying away after it) and which way it turns (+1 left)."""
    k = curvature(P)
    b = ndimage.uniform_filter1d(smoothstep(1 / rmax, 1 / rfull, np.abs(k)), 60)
    return np.clip(b * 1.6, 0, 1), np.sign(ndimage.uniform_filter1d(k, 60))


WALL_MASK = None
BANK_E, BANK_A, BANK_B = 24.0, math.radians(25.0), math.radians(45.0) / 24.0


def bank_rise(e):
    """Red Dust Divide's oval bank: 25 degrees at the road edge, steepening evenly to 70 at 24 m, then 70."""
    e1 = np.clip(e, 0.0, BANK_E)
    return ((math.log(math.cos(BANK_A)) - np.log(np.cos(BANK_A + BANK_B * e1))) / BANK_B
            + np.maximum(e - BANK_E, 0.0) * math.tan(math.radians(70.0)))


def lay_road(H, P, z, hw, color_kind, walls=None, steep=False, oval=None):
    """Carve or build the road: flat across at its height, sand shoulders, banks blending into the ground; with
    walls=(height, width), a semi-oval wall rises on the outside of each hairpin (like a velodrome)."""
    global WALL_MASK
    d, fi, _sd = line_field(P)
    zr = at(z, fi)
    hwv = at(hw, fi) if np.ndim(hw) else np.full_like(d, hw)
    diff = np.abs(zr - H)
    bankw = 4.0 + 0.9 * np.clip(diff, 0, 30) if steep else 10.0 + 2.2 * np.clip(diff, 0, 8)   # a ravine's walls are steep
    hwe = hwv + EDGE_WOBBLE
    t = smoothstep(hwe + 1.5, hwe + 1.5 + bankw, d)
    surf = zr + RELIEF * smoothstep(0.3, 1.0, zr - WLG)             # no relief where it runs through water (fords)
    H2 = surf * (1 - t) + H * t
    if oval is not None:                  # (h at i_a, h at i_b, i_a, i_b): the oval valley over that stretch
        h0, h1, i_a, i_b = oval
        hh = (h0 + (h1 - h0) * np.clip((fi - i_a) / max(i_b - i_a, 1), 0, 1)) * smoothstep(i_a - 150, i_a, fi) * smoothstep(i_b + 150, i_b, fi)
        e = d - hwe
        run = 1.3 * hh
        tq = np.clip(e / np.maximum(run, 1e-3), 0, 1)
        wall = zr + np.where(e <= run, hh * (1 - np.sqrt(1 - tq * tq)),
                             np.maximum(hh - np.maximum(e - run - 6.0, 0.0) * math.tan(math.radians(40.0)), 0.0))
        zone = (e > 0) & (hh > 0.5) & (e < run + 6.0 + hh / math.tan(math.radians(40.0)))
        side = (e > 0) & (smoothstep(i_a - 150, i_a, fi) * smoothstep(i_b + 150, i_b, fi) > 0.01)
        H2 = np.where(side, np.minimum(H2, zr + bank_rise(np.maximum(e, 0.0))), H2)   # the hillside: an oval bank
        H2 = np.where(zone & (e <= run + 6.0), wall, np.where(zone, np.maximum(H2, wall), H2))
        WALL_MASK = zone if WALL_MASK is None else (WALL_MASK | zone)
    if walls:
        wh, ww = walls
        b, sg = bends(P)
        bw, sgn = at(b, fi), at(sg, fi)
        outside = (_sd * sgn < 0) & (d > hwv) & (bw > 0.01)
        e = d - hwv
        u = np.clip(e / ww, 0, 1)
        top = np.where(e <= ww, wh * (1 - np.sqrt(np.clip(1 - u * u, 0, 1))), wh - np.maximum(0, e - ww - 5.0) / 1.3)
        H2 = np.where(outside, np.maximum(H2, zr + bw * np.maximum(top, 0)), H2)
        WALL_MASK = outside & (e < ww + 5.0 + wh * 1.3)
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
RIVER_ALONG = np.zeros(len(RP))
for a_, b_ in RIVER_ROADS.get(SECTOR, []):
    RIVER_ALONG[max(0, a_ - rlo):max(0, b_ - rlo)] = 1.0
if RIVER_ALONG.any():
    RW = RW + 10.0 * ndimage.uniform_filter1d(RIVER_ALONG, 60)
    RZ2 = RZ2 - 0.0 * RIVER_ALONG
    _dr, _fr, _s = line_field(RP[RIVER_ALONG > 0.5], reach=3)
    _zr = at(RZ2[RIVER_ALONG > 0.5], _fr) + 0.12
    WLG = np.where(_dr < at(RW[RIVER_ALONG > 0.5], _fr) + 40.0, np.maximum(WLG, _zr), WLG)
    W = WLG
H_nat = H.copy()
H, D_ROAD, HW_ROAD, T_ROAD = lay_road(H, RP, RZ2, RW, "road", WALLS.get(SECTOR),
                                       oval=(*OVAL[SECTOR], S0 - rlo, (CAVE_SPAN[0] - 70 if CAVE_SPAN else S1_) - rlo)
                                       if SECTOR in OVAL else None)
if CAVE_SPAN:                            # under the hill the road is not cut in: the cave is (section 4b)
    _dz, _f, _s = line_field(RP[CAVE_SPAN[0] - rlo:CAVE_SPAN[1] - rlo], reach=3)
    H = np.where((_dz < RW[CAVE_SPAN[0] - rlo] + 90.0) & (_f > 2) & (_f < CAVE_SPAN[1] - CAVE_SPAN[0] - 3), H_nat, H)
D_FORK = np.full_like(H, 1e9)
D_GFORK = np.full_like(H, 1e9)          # the forks on the ground only (no bridges): nothing may stand on them
T_FORK = np.ones_like(H)
fork_rec = []
for fd in FD:
    zf = fd["z"].copy()
    name = fd["f"]["name"]
    if CAVE_SPAN and "Subterrâneo" in name:
        fd["zs"] = zf
        fork_rec.append(dict(name=name, z_min=float(zf.min()), z_max=float(zf.max()), cave=True))
        continue
    if "Igapó" in name or "Canal Estreito" in name:   # at water level: the ships skim between the trees
        n = len(zf)
        mid = smoothstep(0, 220, np.arange(n)) * smoothstep(0, 220, n - 1 - np.arange(n))
        zf = zf * (1 - mid) + (wl_at(fd["P"]) - 0.12) * mid
    high = np.zeros(len(zf), bool)
    if fd["f"]["type"] == "CIMA" or "Palafitas" in name:   # a bridge where it runs more than 6 m above the ground
                                         # (the tepui's ramp is a spur of rock, recipe_s7: a bridge only off the river)
        high = ndimage.binary_closing((zf - bilinear(H, fd["P"][:, 0], fd["P"][:, 1])) > 6.0, iterations=40)
    gaps = []
    for fj in [j for j in fork_jumps if j["fork"] == name]:
        i, s_ = int(fj["at"]), np.arange(len(zf)) - int(fj["at"])
        if fj["what"] in ("ponte partida", "cais"):   # the broken bridge / the quay's end: a kick, 26 m of nothing
            zf = zf + 1.5 * smoothstep(-60, -14, s_) * (s_ < -13)
            gaps.append((i - 13, i + 13))
        elif fj["what"] == "tronco":              # a giant trunk across: the deck humps over it
            zf = zf + 2.2 * smoothstep(-45, -2, s_) * (s_ <= 2) + 2.2 * (1 - smoothstep(2, 24, s_)) * (s_ > 2)
            fd.setdefault("logs", []).append(i)
        elif fj["what"] == "fenda":            # a crevasse across the tepui's top: a kick and 30 m of void
            zf = zf + 2.0 * smoothstep(-55, -16, s_) * (s_ < -15)
            zf = np.where(np.abs(s_) <= 15, zf - 55.0, zf)
        elif fj["what"] in ("descida", "mergulho"):   # off the hill / the tepui: up to a lip, 6 m down
            zf = zf + 6.0 * smoothstep(-160, -10, s_) * (s_ < 0)
        elif fj["what"] == "ilha":             # from one island to the next: a kick and 36 m of rapids
            zf = zf + 2.4 * smoothstep(-60, -20, s_) * (s_ < -18)
            zf = np.where(np.abs(s_) <= 18, wl_at(fd["P"]) - 1.6, zf)
        elif fj["what"].startswith("raiz") or fj["what"].startswith("raíz"):   # a giant root across: a crest
            zf = zf + 3.0 * smoothstep(-70, -3, s_) * (s_ <= 3) + 3.0 * (1 - smoothstep(3, 40, s_)) * (s_ > 3)
            fd.setdefault("roots", []).append(i)
    ground = ~high
    if "Cascata" in name:                 # off the lip: no road in the air, the gorge opens under the leap
        drop = zf[np.minimum(np.arange(len(zf)) + 60, len(zf) - 1)] - zf
        cand = np.flatnonzero(drop < -15.0)
        if len(cand):
            lip = int(cand[0]) + 8
            land = int(np.flatnonzero((np.arange(len(zf)) > lip) & (zf < zf.min() + 4.0))[0])
            fd["lip"], fd["land"] = lip, land
            ground[lip:land] = False
            dA, _fa, _sa = line_field(fd["P"][lip:land])
            H = np.minimum(H, wl_at(fd["P"][land:land + 1])[0] - 3.0 + np.maximum(0.0, dA - 110.0) * 3.5)
    if any(k_ in name for k_ in RIVER_FORKS):   # the fork is the river's bed: water 12 cm over it
        dRf, fRf, _sR = line_field(fd["P"], reach=3)
        WLG = np.where(dRf < fd["hw"] + 22.0, np.maximum(WLG, at(zf, fRf) + 0.12), WLG)
        W = WLG
        fd["river"] = True
    for a, b in runs(ground):
        if b - a > 5:
            ov = (8.0, 8.0, 0, b - a) if (SECTOR in OVAL and "Leito" in name) else None
            H, dF, _hw, tF = lay_road(H, fd["P"][a:b], zf[a:b], fd["hw"] + (10.0 if fd.get("river") else 0.0), "fork", oval=ov,
                                      steep=(fd["f"]["type"] == "BAIXO" or any(k_ in name for k_ in STEEP_FORKS)) and ov is None)
            D_FORK = np.minimum(D_FORK, dF - fd["hw"])
            D_GFORK = np.minimum(D_GFORK, dF - fd["hw"])
            T_FORK = np.minimum(T_FORK, tF)
    for a, b in runs(high):
        dF, _fi, _sd = line_field(fd["P"][a:b])
        D_FORK = np.minimum(D_FORK, dF - fd["hw"] + 2.0)        # a corridor through the canopy for the bridge
        fd.setdefault("decks", []).append((a, b, gaps))
    fd["zs"] = zf
    fork_rec.append(dict(name=name, z_min=float(zf.min()), z_max=float(zf.max()), bridge_m=int(high.sum())))
CAVE = SKY = None
H_TOP = H
if CAVE_SPAN:
    # 4b. The cave: under the hill (H_TOP, with F8 laid on it) a wide hall: the road's floor, and beside it, lower, F9
    # and the underground river. The ceiling is an arch up to 24 m, never closer than 5 m under the hill's surface;
    # where the hill is too thin there is no roof (open sinkholes), and skylights every ~230 m let the sun in.
    ib, isd = CAVE_SPAN[0] - rlo, CAVE_SPAN[1] - rlo
    dC, fC, _sC = line_field(RP[ib:isd], reach=3)
    f9 = [fd for fd in FD if "Subterrâneo" in fd["f"]["name"]][0]
    d9, f9i, s9 = line_field(f9["P"], reach=3)
    hw0 = float(RW[ib])
    CAVE = (dC < hw0 + 12.0) | (d9 < f9["hw"] + 34.0)
    H_TOP = H.copy()
    Hc = at(RZ2[ib:isd], fC) + RELIEF
    Hc, d9b, _h9, t9 = lay_road(Hc, f9["P"], f9["zs"], f9["hw"], "fork")
    T9 = f9["P"][np.minimum(np.arange(len(f9["P"])) + 5, len(f9["P"]) - 1)] - f9["P"][np.maximum(np.arange(len(f9["P"])) - 5, 0)]
    T9 = T9 / np.maximum(np.linalg.norm(T9, axis=1, keepdims=True), 1e-9)
    N9 = np.stack([-T9[:, 1], T9[:, 0]], 1)
    mid9 = len(f9["P"]) // 2
    road_side = np.sign(np.dot(RP[ib + int(np.argmin(np.hypot(*(RP[ib:isd] - f9["P"][mid9]).T)))] - f9["P"][mid9], N9[mid9]))
    rivP = f9["P"] - N9 * road_side * (f9["hw"] + 16.0)
    dR, fR, _sR = line_field(rivP, reach=3)
    zR = at(f9["zs"], fR) - 2.0
    Hc = np.where(dR < 10.0, np.minimum(Hc, zR - 2.5 + 2.5 * smoothstep(5.0, 10.0, dR)), Hc)
    WLG = np.where(CAVE & (dR < 12.0), zR, WLG)
    W = WLG
    H = np.where(CAVE, Hc, H_TOP)
    din = ndimage.distance_transform_edt(CAVE) * RES
    CEIL = np.minimum(ndimage.gaussian_filter(np.where(CAVE, Hc, 0.0), 4.0) / np.maximum(ndimage.gaussian_filter(CAVE.astype(float), 4.0), 1e-3)
                      + 24.0 * np.sqrt(np.clip(din / 22.0, 0, 1))
                      + np.clip(din / 6.0, 0, 1) * (5.0 * (fbm(XX, YY, 28.0, 531, 3) - 0.5) + 2.0 * (fbm(XX, YY, 7.0, 533, 2) - 0.5)),
                      H_TOP - 5.0)
    ROOF = CAVE & (H_TOP - Hc > 12.0)
    SKY = np.zeros_like(CAVE)
    for k in range(ib + 160, isd - 100, 230):
        SKY |= np.hypot(XX - RP[k, 0], YY - RP[k, 1]) < 11.0
    ROOF &= ~SKY
    T_ROAD = np.where(CAVE & (dC < hw0 + 1.0), 0.0, T_ROAD)
    log("cave: %.0f m of roof cover, %d skylights, lower level and river beside it" % (ROOF.sum() * RES * RES / (2 * hw0 + 30),
                                                                                       len(range(ib + 160, isd - 100, 230))))
GROUND = np.where(CAVE, H_TOP, H) if CAVE is not None else H     # where plants stand (on the hill over the cave)
D_EDGE = np.minimum(D_ROAD - HW_ROAD, D_FORK)              # metres from the nearest road or fork edge
log("road laid: %d jumps, forks %s" % (len(JREC), [f["name"] for f in fork_rec]))

# ---------------------------------------------------------------------------------------------------- 5. colours
def srgb(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


PALS = PAL.get(SECTOR, PAL["S1"])
SAND, WETSAND = srgb(PALS["road"]), srgb(PALS["wet"])
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
puddle = sand * smoothstep(-0.05, -0.15, RELIEF) * (1 - T_ROAD)       # rain water in the dips of the mud
wsand = np.maximum(wsand, 0.85 * puddle)
col = col * (1 - wsand[..., None]) + WETSAND[None, None] * wsand[..., None]
ED = np.minimum(np.abs(D_ROAD - HW_ROAD), np.abs(D_FORK))
grass = smoothstep(5.0, 0.0, ED) * smoothstep(0.35, 0.55, fbm(XX, YY, 9.0, 97, 3)) * (H - W > 0.3) * (1 - sand)
col = col * (1 - 0.8 * grass[..., None]) + MEADOW[None, None] * 0.8 * grass[..., None]
WETNESS = np.clip(np.maximum(np.maximum(edge, wsand), puddle * 1.2), 0, 1)
gy_, gx_ = np.gradient(H, RES)
SLOPE = np.hypot(gx_, gy_)
if PALS.get("rock"):
    rk = smoothstep(0.75, 1.3, SLOPE) * (1 - sand)
    rc = srgb(PALS["rock"]) * ((0.55 + 0.6 * fbm(XX, YY * 0.25, 8.0, 141, 3)) * (0.8 + 0.2 * np.sin(H / 5.5)))[..., None]
    col = col * (1 - rk[..., None]) + rc * rk[..., None]
if "savanna" in F:                       # golden grass between the trees
    sv = (F["savanna"] * (1 - sand) * (1 - edge))[..., None]
    col = col * (1 - sv) + srgb((0.60, 0.50, 0.27)) * (0.8 + 0.4 * nc[..., None]) * sv
if PALS["bank"]:
    bare = np.clip(np.abs(H - H_nat) - 0.8, 0, 1) * (1 - sand)
    col = col * (1 - bare[..., None]) + (srgb(PALS["bank"]) * (0.85 + 0.3 * nc[..., None])) * bare[..., None]

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
pz = bilinear(GROUND, px, py)
pedge = grid_at(D_EDGE, px, py)
pdepth = wl_at(np.c_[px, py]) - pz
pig = grid_at(F.get("igapo", np.zeros_like(H)), px, py)
pfar = grid_at(np.minimum(D_ROAD, D_FORK + 30), px, py)
keep = (pedge > 9.0) & ((pdepth < -0.05) | ((pig > 0.3) & (pdepth < 1.6)) | ((SECTOR in WET_TREES) & (pdepth < 1.8))) \
    & (grid_at(SLOPE, px, py) < 0.85)
if WALL_MASK is not None:
    keep &= ~grid_at(WALL_MASK, px, py)
if "savanna" in F:                       # the savanna is open: one tree in ~25
    keep &= rng.random(len(px)) < 1.0 - 0.96 * grid_at(F["savanna"], px, py)
if CAVE is not None:                     # over the cave: the hill's forest, away from F8 and the skylights
    inc = grid_at(CAVE, px, py)
    keep = np.where(inc, (grid_at(D_FORK, px, py) > 9.0) & ~grid_at(SKY, px, py) & (grid_at(H_TOP - H, px, py) > 12.0), keep)
px, py, pz, pedge, pdepth, pig, pfar = px[keep], py[keep], pz[keep], pedge[keep], pdepth[keep], pig[keep], pfar[keep]
EDGE_BAND = EDGE_BAND[keep]
u = rng.random(len(px))
K = {k: i for i, k in enumerate(jk.KINDS)}
kind = np.full(len(px), K["canopy_a"])
def pick(u, spec):
    edges = np.cumsum([p for _k, p in spec])
    return np.select([u < e for e in edges[:-1]], [K[k] for k, _p in spec[:-1]], K[spec[-1][0]])


MIX = MIXES.get(SECTOR, MIXES["S1"])
interior = pick(u, MIX["interior"])
edgek = pick(u, MIX["edge"])
wetk = pick(u, MIX["wet"]) if "wet" in MIX else \
    np.select([u < 0.30, u < 0.50, u < 0.65, u < 0.90], [K["acai"], K["cecropia"], K["buriti"], K["canopy_b"]], K["shrub_b"])
igk = np.select([u < 0.35, u < 0.60, u < 0.80], [K["canopy_b"], K["acai"], K["buriti"]], K["canopy_a"])
kind = np.where(pdepth > -0.9, wetk, interior)
kind = np.where(pedge < 32.0, edgek, kind)
kind = np.where(pig > 0.3, igk, kind)
bandk = pick(u, MIX["band"])
kind = np.where(EDGE_BAND, bandk, kind)
if "savanna" in MIX and "savanna" in F:   # in the savanna: acacias, baobabs, shrubs and termite mounds
    kind = np.where(grid_at(F["savanna"], px, py) > 0.5, pick(u, MIX["savanna"]), kind)
# emergent kapoks: sparse everywhere, and some heroes standing right by the road
kx = rng.uniform(X0, X1, int((X1 - X0) * (Y1 - Y0) / 150.0 ** 2))
ky = rng.uniform(Y0, Y1, len(kx))
ke = grid_at(D_EDGE, kx, ky)
kd = wl_at(np.c_[kx, ky]) - bilinear(GROUND, kx, ky)
okk = (ke > 26.0) & (kd < -0.2)
hero = np.arange(0, len(RP), 420)
hside = np.where(np.arange(len(hero)) % 2 == 0, 1.0, -1.0)
tdir = RP[np.minimum(hero + 5, len(RP) - 1)] - RP[np.maximum(hero - 5, 0)]
tdir = tdir / np.maximum(np.linalg.norm(tdir, axis=1, keepdims=True), 1e-9)
hx = RP[hero, 0] - tdir[:, 1] * hside * (RW[hero] + rng.uniform(34, 55, len(hero)))
hy = RP[hero, 1] + tdir[:, 0] * hside * (RW[hero] + rng.uniform(34, 55, len(hero)))
okh = (grid_at(D_EDGE, hx, hy) > 24.0) & (wl_at(np.c_[hx, hy]) - bilinear(GROUND, hx, hy) < -0.2)
kx, ky = np.concatenate([kx[okk], hx[okh]]), np.concatenate([ky[okk], hy[okh]])
if SECTOR in NO_KAPOK:
    kx, ky = kx[:0], ky[:0]
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
pz = np.concatenate([pz, bilinear(GROUND, kx, ky)])
kind = np.concatenate([kind, np.full(len(kx), K["kapok"])])
pfar = np.concatenate([pfar, grid_at(np.minimum(D_ROAD, D_FORK + 30), kx, ky)])
# far from the road: blobs instead of leaf cards; the understory there is never seen
FAR = 480.0
far = pfar > FAR
swap = {K["canopy_a"]: K["far_a"], K["canopy_b"]: K["far_b"], K["canopy_c"]: K["far_c"], K["kapok"]: K["far_kapok"],
        K["mangrove"]: K["far_mangrove"]}
small = np.isin(kind, [K["shrub_a"], K["shrub_b"], K["acai"], K["cecropia"], K["buriti"]])
keep = ~(far & small & (rng.random(len(kind)) < 0.85))
EDGE_BAND = np.concatenate([EDGE_BAND, np.zeros(len(kx), bool)])[keep]
px, py, pz, kind, far = px[keep], py[keep], pz[keep], kind[keep], far[keep]
for a, b in swap.items():
    kind = np.where(far & (kind == a), b, kind)
if SECTOR == "S7":                       # the tepui's top is bare rock with low shrubs
    ontop = pz > TEPUI["top"] - 45.0
    kind = np.where(ontop, np.where(rng.random(len(px)) < 0.5, K["shrub_a"], K["shrub_b"]), kind)
    thin = ~ontop | (rng.random(len(px)) < 0.35)
    px, py, pz, kind = px[thin], py[thin], pz[thin], kind[thin]
    EDGE_BAND = EDGE_BAND[thin[:len(EDGE_BAND)]] if len(EDGE_BAND) == len(thin) else EDGE_BAND
yaw = rng.uniform(0, 360, len(px))
# the canopy bridges hang between pairs of kapoks every 70 m: their crowns spread just above the deck
tw = []
for fd in FD:
    for a, b, _g in (fd.get("decks", []) if "Copa" in fd["f"]["name"] else []):
        P_, Z_ = fd["P"][a:b], fd["zs"][a:b]
        T_ = np.gradient(P_, axis=0)
        T_ = T_ / np.maximum(np.linalg.norm(T_, axis=1, keepdims=True), 1e-9)
        for i in range(30, len(P_) - 30, 70):
            for side in (1, -1):
                q = P_[i] + np.array([-T_[i, 1], T_[i, 0]]) * side * (fd["hw"] + 3.4)
                g = float(bilinear(GROUND, q[0], q[1]))
                if (grid_at(np.minimum(D_ROAD - HW_ROAD, D_GFORK), q[0], q[1]) < 8.0
                        or (WALL_MASK is not None and grid_at(WALL_MASK, q[0], q[1]))):
                    continue                      # never on the road or a fork on the ground (where the bridge crosses
                                                  # over them: the ravine), nor on a wall
                tw.append((q[0], q[1], g, float(np.clip((Z_[i] - g + 5.0) / (0.74 * 51.0), 0.9, 1.45))))
for fd in FD:
    if "Sapopemas" in fd["f"]["name"] or "Raízes Gigantes" in fd["f"]["name"]:
        P_ = fd["P"]
        T_ = np.gradient(P_, axis=0)
        T_ = T_ / np.maximum(np.linalg.norm(T_, axis=1, keepdims=True), 1e-9)
        for k, i in enumerate(range(700, len(P_) - 700, 42)):
            side = 1 if k % 2 else -1
            q = P_[i] + np.array([-T_[i, 1], T_[i, 0]]) * side * (fd["hw"] + rng.uniform(5.0, 8.0))
            if grid_at(np.minimum(D_ROAD - HW_ROAD, D_GFORK), q[0], q[1]) > 3.0:
                tw.append((q[0], q[1], float(bilinear(GROUND, q[0], q[1])), float(rng.uniform(0.85, 1.1))))
RIVERS_DRIVEN = ([(RP[RIVER_ALONG > 0.5], RW[RIVER_ALONG > 0.5])] if RIVER_ALONG.any() else []) + \
    [(fd["P"][300:-300], np.full(max(len(fd["P"]) - 600, 0), fd["hw"] + 10.0)) for fd in FD if fd.get("river")]
for Pr, hwr in RIVERS_DRIVEN:            # the river meets the land: stilt-rooted trees at its edges
    if len(Pr) < 40:
        continue
    Tr = np.gradient(Pr, axis=0)
    Tr = Tr / np.maximum(np.linalg.norm(Tr, axis=1, keepdims=True), 1e-9)
    for k, i in enumerate(range(10, len(Pr) - 10, 9)):
        side = 1 if k % 2 else -1
        q = Pr[i] + np.array([-Tr[i, 1], Tr[i, 0]]) * side * (hwr[i] + rng.uniform(1.0, 6.0))
        tw.append((q[0], q[1], float(bilinear(GROUND, q[0], q[1])), float(rng.uniform(0.8, 1.25)), "mangrove"))
if tw:
    tw_k = np.array([K[t_[4]] if len(t_) > 4 else K["kapok"] for t_ in tw])
    tw = np.array([t_[:4] for t_ in tw])
    px, py, pz = np.r_[px, tw[:, 0]], np.r_[py, tw[:, 1]], np.r_[pz, tw[:, 2]]
    kind = np.r_[kind, tw_k]
    yaw = np.r_[yaw, rng.uniform(0, 360, len(tw))]
scl = np.where(np.isin(kind, [K["kapok"], K["far_kapok"]]), rng.uniform(0.9, 1.12, len(px)), rng.uniform(0.75, 1.25, len(px)))
if len(tw):
    scl[-len(tw):] = tw[:, 3]
young = np.r_[EDGE_BAND, np.zeros(len(px) - len(EDGE_BAND), bool)] & (kind == K["canopy_b"])
scl = np.where(young, rng.uniform(0.45, 0.7, len(px)), scl)      # young trees at the edge
# road debris (jogador, 2026-11-02: "galhos, arbustos pequenos, pedras no meio da estrada; não podem atrapalhar na
# condução, as naves passam por cima"): stones, branches and ferns under 0.6 m, in patches, more towards the edges,
# never in water; no collision
SINK = np.full(len(px), 0.4)
gx_d, gy_d = np.meshgrid(np.arange(X0 + 2.0, X1, 4.0), np.arange(Y0 + 2.0, Y1, 4.0))
dxs = (gx_d + rng.uniform(-1.8, 1.8, gx_d.shape)).ravel()
dys = (gy_d + rng.uniform(-1.8, 1.8, gy_d.shape)).ravel()
onr = (grid_at(np.minimum(T_ROAD, T_FORK), dxs, dys) < 0.05) & (bilinear(H, dxs, dys) > wl_at(np.c_[dxs, dys]) + 0.3)
ef = np.clip(grid_at(D_ROAD / np.maximum(HW_ROAD, 1.0), dxs, dys), 0, 1)
pd = (0.012 + 0.08 * ef ** 2) * (0.3 + 1.4 * smoothstep(0.45, 0.62, fbm(dxs, dys, 60.0, 521, 2)))
dsel = onr & (rng.random(len(dxs)) < pd)
dxs, dys, ef = dxs[dsel], dys[dsel], ef[dsel]
ud = rng.random(len(dxs))
dk = np.where(ud < 0.28, K["stone_a"], np.where(ud < 0.45, K["stone_b"], np.where(ud < 0.72, K["branch"], K["fern"])))
dk = np.where((dk == K["fern"]) & (ef < 0.6), K["stone_a"], dk)        # ferns only near the edges
px, py = np.r_[px, dxs], np.r_[py, dys]
pz = np.r_[pz, bilinear(H, dxs, dys)]
kind = np.r_[kind, dk]
yaw = np.r_[yaw, rng.uniform(0, 360, len(dxs))]
scl = np.r_[scl, rng.uniform(0.7, 1.3, len(dxs))]
SINK = np.r_[SINK, np.full(len(dxs), 0.03)]
log("jungle: %d plants (%s)" % (len(px), ", ".join("%s %d" % (k, int((kind == i).sum())) for i, k in enumerate(jk.KINDS))))

# ---------------------------------------------------------------------------------------------------- 7. files for Unreal
zmin, zmax = float(H.min()) - 1.0, float(H.max()) + 1.0
h16 = np.round((H - zmin) / (zmax - zmin) * 65535).astype("<u2")
h16.tofile(os.path.join(OUT, "selva_%s_height.r16" % SECTOR))
meta = dict(sector=SNAME, box=[X0, Y0, X1, Y1], res_m=RES, size=[NX, NY], z_min=zmin, z_max=zmax, water_m=float(np.median(WLG)),
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
    base_col = sc.outputs[0]
    if PALS.get("rock"):                 # cliffs: sandstone in beds, dark streaks where water runs down
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sn = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], sn.inputs[0])
        steep = nt.nodes.new("ShaderNodeMapRange")
        steep.inputs[1].default_value, steep.inputs[2].default_value = 0.8, 0.5
        nt.links.new(sn.outputs["Z"], steep.inputs[0])
        sp = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sp.inputs[0])
        nzr = nt.nodes.new("ShaderNodeTexNoise"); nzr.inputs["Scale"].default_value = 0.02
        nt.links.new(geo.outputs["Position"], nzr.inputs["Vector"])
        warp = nt.nodes.new("ShaderNodeMath"); warp.operation = "MULTIPLY_ADD"
        warp.inputs[1].default_value, warp.inputs[2].default_value = 18.0, 0.0
        nt.links.new(nzr.outputs["Fac"], warp.inputs[0])
        zw = nt.nodes.new("ShaderNodeMath"); zw.operation = "ADD"
        nt.links.new(sp.outputs["Z"], zw.inputs[0]); nt.links.new(warp.outputs[0], zw.inputs[1])
        dv = nt.nodes.new("ShaderNodeMath"); dv.operation = "DIVIDE"; dv.inputs[1].default_value = 4.5
        nt.links.new(zw.outputs[0], dv.inputs[0])
        sinn = nt.nodes.new("ShaderNodeMath"); sinn.operation = "SINE"
        nt.links.new(dv.outputs[0], sinn.inputs[0])
        beds = nt.nodes.new("ShaderNodeMapRange")
        beds.inputs[1].default_value, beds.inputs[2].default_value = -1.0, 1.0
        beds.inputs[3].default_value, beds.inputs[4].default_value = 0.7, 1.08
        nt.links.new(sinn.outputs[0], beds.inputs[0])
        mpz = nt.nodes.new("ShaderNodeMapping"); mpz.inputs["Scale"].default_value = (1.0, 1.0, 0.06)
        nt.links.new(geo.outputs["Position"], mpz.inputs["Vector"])
        nzs = nt.nodes.new("ShaderNodeTexNoise"); nzs.inputs["Scale"].default_value = 0.35; nzs.inputs["Detail"].default_value = 6
        nt.links.new(mpz.outputs[0], nzs.inputs["Vector"])
        strk = nt.nodes.new("ShaderNodeMapRange")
        strk.inputs[3].default_value, strk.inputs[4].default_value = 0.45, 1.25
        nt.links.new(nzs.outputs["Fac"], strk.inputs[0])
        rc1 = nt.nodes.new("ShaderNodeVectorMath"); rc1.operation = "SCALE"
        rc1.inputs[0].default_value = tuple(float(v) for v in srgb(PALS["rock"]))
        nt.links.new(beds.outputs[0], rc1.inputs["Scale"])
        rc2 = nt.nodes.new("ShaderNodeVectorMath"); rc2.operation = "SCALE"
        nt.links.new(rc1.outputs[0], rc2.inputs[0]); nt.links.new(strk.outputs[0], rc2.inputs["Scale"])
        mixr = nt.nodes.new("ShaderNodeMix"); mixr.data_type = "RGBA"
        nt.links.new(steep.outputs[0], mixr.inputs[0])
        nt.links.new(sc.outputs[0], mixr.inputs[6]); nt.links.new(rc2.outputs[0], mixr.inputs[7])
        base_col = mixr.outputs[2]
    nt.links.new(base_col, bs.inputs["Base Color"])
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
WX, WY = np.meshgrid(np.arange(X0, X1 + 1e-6, 6.0), np.arange(Y0, Y1 + 1e-6, 6.0))
WLw, Hw = bilinear(WLG, WX, WY), bilinear(H, WX, WY)
wv = Hw < WLw + 0.4
iw = np.arange(WX.size).reshape(WX.shape)
qw = np.stack([iw[:-1, :-1], iw[:-1, 1:], iw[1:, 1:], iw[1:, :-1]], -1)
lw = np.stack([WLw[:-1, :-1], WLw[:-1, 1:], WLw[1:, 1:], WLw[1:, :-1]], -1)
kq = (wv[:-1, :-1] | wv[:-1, 1:] | wv[1:, 1:] | wv[1:, :-1]) & (lw.max(-1) - lw.min(-1) < 0.5)
qw = qw[kq]
wme.vertices.add(WX.size)
wme.vertices.foreach_set("co", np.stack([WX - cx, WY - cy, WLw], -1).astype(np.float32).ravel())
wme.loops.add(qw.size)
wme.loops.foreach_set("vertex_index", qw.astype(np.int32).ravel())
wme.polygons.add(len(qw))
wme.polygons.foreach_set("loop_start", np.arange(0, qw.size, 4, dtype=np.int32))
wme.update(calc_edges=True)
# beyond the box, for the photos only: the canopy goes on for ever, over hills that roll on (a coarse ring of terrain
# at canopy height round the box, its inner edge just inside it)
STEP_B, PAD_B = 40.0, 7000.0
GXb, GYb = np.meshgrid(np.arange(X0 - PAD_B, X1 + PAD_B + 1, STEP_B), np.arange(Y0 - PAD_B, Y1 + PAD_B + 1, STEP_B))
hxb, hyb = np.clip(GXb, X0, X1), np.clip(GYb, Y0, Y1)
farb = np.hypot(GXb - hxb, GYb - hyb)
ZB = bilinear(H_nat, hxb, hyb) + CANOPY_H.get(SECTOR, 24.0) + HILLS.get(SECTOR, 1.0) * (fbm(GXb, GYb, 1800.0, 61, 3) - 0.5) * np.minimum(farb * 0.04, 90.0)
nyb, nxb = GXb.shape
vb = np.stack([GXb - cx, GYb - cy, ZB], -1).reshape(-1, 3)
inner = (GXb > X0 + STEP_B) & (GXb < X1 - STEP_B) & (GYb > Y0 + STEP_B) & (GYb < Y1 - STEP_B)
ib = np.arange(nxb * nyb).reshape(nyb, nxb)
qb = np.stack([ib[:-1, :-1], ib[:-1, 1:], ib[1:, 1:], ib[1:, :-1]], -1)
inq = inner[:-1, :-1] & inner[:-1, 1:] & inner[1:, 1:] & inner[1:, :-1]
cme = bpy.data.meshes.new("CanopyBeyond")
cme.from_pydata(vb.tolist(), [], qb[~inq].tolist())
wme.materials.append(water_material())
water = bpy.data.objects.new("Water", wme)
scene.collection.objects.link(water)

cme.materials.append(carpet_material() if "savanna" not in F else terrain_material())
if "savanna" in F:                       # golden grass beyond the box
    gca = cme.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    gca.data.foreach_set("color", np.tile(np.r_[srgb((0.55, 0.46, 0.25)), 1.0].astype(np.float32), len(cme.vertices)))
beyond = bpy.data.objects.new("CanopyBeyond", cme)
scene.collection.objects.link(beyond)
# the plant kit and the scatter (geometry nodes: one point per plant, instance picked by 'kind')
scene.collection.children.link(kit)
bpy.context.view_layer.layer_collection.children[kit.name].exclude = True
pm = bpy.data.meshes.new("JunglePoints")
pm.vertices.add(len(px))
pm.vertices.foreach_set("co", np.stack([px - cx, py - cy, pz - SINK], 1).astype(np.float32).ravel())
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


def deck_material():
    m = bpy.data.materials.new("M_Deck")
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Y"
    wv.inputs["Scale"].default_value = 1.0; wv.inputs["Distortion"].default_value = 2.0
    nt.links.new(tc.outputs["UV"], wv.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.06, 0.035, 0.018, 1)
    ramp.color_ramp.elements[1].color = (0.24, 0.15, 0.08, 1)
    nt.links.new(wv.outputs["Fac"], ramp.inputs[0])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.inputs["Roughness"].default_value = 0.8
    nt.links.new(ramp.outputs[0], bs.inputs["Base Color"])
    jk.finish(m, bs.outputs[0])
    return m


def thatch_material():
    m = bpy.data.materials.get("M_Thatch")
    if m:
        return m
    m = bpy.data.materials.new("M_Thatch")
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, 12.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 8
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.06, 0.04, 0.015, 1)
    ramp.color_ramp.elements[1].color = (0.30, 0.21, 0.08, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs[0])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.inputs["Roughness"].default_value = 0.95
    nt.links.new(ramp.outputs[0], bs.inputs["Base Color"])
    jk.finish(m, bs.outputs[0])
    return m


def hut(mb, c, ang, zf, g):
    """A stilt house (S6 Palafitas): 6 x 5 m on posts, plank walls, a thatched roof with eaves."""
    ux, uy = np.array([math.cos(ang), math.sin(ang)]), np.array([-math.sin(ang), math.cos(ang)])

    def P3(x, y, z):
        q = c + ux * x + uy * y
        return np.array([q[0] - cx, q[1] - cy, z])

    def quad(a, b, c_, d, mat):
        base = len(mb.v)
        mb.v += [a, b, c_, d]
        mb._face((base, base + 1, base + 2, base + 3), ((0, 0), (1, 0), (1, 1), (0, 1)), mat)
    for x in (-3.0, 3.0):
        for y in (-2.5, 2.5):
            mb.tube([P3(x, y, g - 1.0), P3(x, y, zf)], 0.18, "deck", seg=4)
    zt = zf + 3.0
    cs = [(-3.0, -2.5), (3.0, -2.5), (3.0, 2.5), (-3.0, 2.5)]
    quad(*[P3(x, y, zf) for x, y in cs], "deck")
    for k in range(4):
        (x0, y0), (x1, y1) = cs[k], cs[(k + 1) % 4]
        quad(P3(x0, y0, zf), P3(x1, y1, zf), P3(x1, y1, zt), P3(x0, y0, zt), "deck")
    o = 0.8
    quad(P3(-3 - o, -2.5 - o, zt - 0.4), P3(3 + o, -2.5 - o, zt - 0.4), P3(3 + o, 0, zt + 2.2), P3(-3 - o, 0, zt + 2.2), "thatch")
    quad(P3(3 + o, 2.5 + o, zt - 0.4), P3(-3 - o, 2.5 + o, zt - 0.4), P3(-3 - o, 0, zt + 2.2), P3(3 + o, 0, zt + 2.2), "thatch")
    for x in (-3.0, 3.0):
        quad(P3(x, -2.5, zt), P3(x, 2.5, zt), P3(x, 0, zt + 2.2), P3(x, 0.01, zt + 2.2), "deck")


def deck_object(name, P, Z, hw, gaps, style="copa"):
    """A canopy bridge: plank deck (1.2 m thick) with rope rails on posts, hung between pairs of giant trunks every
    ~70 m, a cross-beam under each pair; 'gaps' (index ranges) are left open (the broken bridge)."""
    mb = jk.MB()
    mats_d = {"deck": deck_material(), "bark": bpy.data.materials["M_Bark_Kapok"], "rope": bpy.data.materials["M_Bark_Cecropia"]}
    T = np.gradient(P, axis=0)
    T = T / np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    N = np.stack([-T[:, 1], T[:, 0]], 1)
    idx = np.arange(0, len(P), 3)
    ok = np.ones(len(idx), bool)
    for a, b in gaps:
        ok &= ~((idx >= a) & (idx <= b))

    def pt(i, side, dz):
        q = P[i] + N[i] * side
        return np.array([q[0] - cx, q[1] - cy, Z[i] + dz])
    for k in range(len(idx) - 1):
        if not (ok[k] and ok[k + 1]):
            continue
        i0, i1 = idx[k], idx[k + 1]
        v0, v1 = i0 / 1.6, i1 / 1.6
        for (sa, za), (sb, zb) in (((hw, 0), (-hw, 0)), ((-hw, -1.2), (hw, -1.2)), ((hw, -1.2), (hw, 0)), ((-hw, 0), (-hw, -1.2))):
            base = len(mb.v)
            mb.v += [pt(i0, sa, za), pt(i0, sb, zb), pt(i1, sb, zb), pt(i1, sa, za)]
            mb._face((base, base + 1, base + 2, base + 3), ((0, v0), (1, v0), (1, v1), (0, v1)), "deck")
    for a, b in runs(ok):
        seg = idx[a:b]
        if len(seg) < 3:
            continue
        for side in (hw - 0.3, -(hw - 0.3)):
            mb.tube([pt(i, side, 1.3) for i in seg], 0.07, "rope", seg=5)
            for i in seg[::2]:
                mb.tube([pt(i, side, 0.0), pt(i, side, 1.4)], 0.11, "deck", seg=4)
    if style == "palafita":                       # a boardwalk on stilts, stilt houses beside it with a plank to each
        mats_d["thatch"] = thatch_material()
        for i in range(0, len(P), 8):
            if not ok[min(i // 3, len(ok) - 1)]:
                continue
            for sd_ in (hw - 0.4, -(hw - 0.4)):
                q = P[i] + N[i] * sd_
                mb.tube([np.array([q[0] - cx, q[1] - cy, float(bilinear(H, q[0], q[1])) - 1.0]), pt(i, sd_, -1.2)], 0.22, "deck", seg=5)
        for k, i in enumerate(range(40, len(P) - 40, 55)):
            if not ok[min(i // 3, len(ok) - 1)]:
                continue
            side = 1 if k % 2 else -1
            c_ = P[i] + N[i] * side * (hw + 9.0)
            hut(mb, c_, math.atan2(N[i, 1], N[i, 0]), float(Z[i]), float(bilinear(H, c_[0], c_[1])))
            mb.tube([pt(i, side * hw, -0.4), pt(i, side * (hw + 6.0), -0.4)], 0.45, "deck", seg=4)
    for i in (range(30, len(P) - 30, 70) if style == "copa" else []):   # cross-beams between each pair of kapoks
        ends = [P[i] + N[i] * sd_ * (hw + 3.4) for sd_ in (1, -1)]
        if ok[min(i // 3, len(ok) - 1)] and all(grid_at(np.minimum(D_ROAD - HW_ROAD, D_GFORK), e_[0], e_[1]) >= 8.0 for e_ in ends):
            mb.tube([pt(i, hw + 3.4, -1.3), pt(i, -(hw + 3.4), -1.3)], 0.45, "bark", seg=6)
    mats_d["bark"] = bpy.data.materials["M_Bark"]
    o = mb.build(name, mats_d)
    scene.collection.objects.link(o)
    return o


def falls_objects(lip=None, d=None, ztop=None, zbot=None, width=100.0):
    """The water leaving the lip and falling into the pool: a curtain bowed out by its own speed, streaked white;
    the spray: a cloud over the pool. Defaults: S3's Kaieteur."""
    lip = LIP_S3 if lip is None else np.asarray(lip, float)
    d = np.array([0.08, -1.0]) / np.hypot(0.08, 1.0) if d is None else np.asarray(d, float)
    ztop = W_TOP if ztop is None else ztop
    zbot = W_LOW if zbot is None else zbot
    acr = np.array([-d[1], d[0]])
    Hf = ztop - zbot
    nu, nv = 26, 44
    verts, faces = [], []
    for j in range(nv + 1):
        v = j / nv
        out = 4.5 * math.sqrt(2 * Hf * v / 9.8)
        for i in range(nu + 1):
            u = i / nu - 0.5
            q = lip + acr * u * width * (1 + 0.2 * v) + d * (out + 2.0)
            verts.append((q[0] - cx, q[1] - cy, ztop + 0.3 - Hf * v))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    me_ = bpy.data.meshes.new("Falls")
    me_.from_pydata(verts, [], faces)
    uvl = me_.uv_layers.new(name="UVMap")
    uv = []
    for fc in faces:
        for vi in fc:
            uv += [(vi % (nu + 1)) / nu, 1 - (vi // (nu + 1)) / nv]
    uvl.data.foreach_set("uv", np.asarray(uv, np.float32))
    m = bpy.data.materials.new("M_Falls")
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (40.0, 1.5, 1.0)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 8
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    al = nt.nodes.new("ShaderNodeMapRange"); al.inputs[1].default_value, al.inputs[2].default_value = 0.35, 0.65
    al.inputs[3].default_value, al.inputs[4].default_value = 0.45, 1.0
    nt.links.new(nz.outputs["Fac"], al.inputs[0])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Base Color"].default_value = (0.85, 0.88, 0.90, 1)
    bs.inputs["Roughness"].default_value = 0.35
    bs.inputs["Emission Color"].default_value = (0.75, 0.80, 0.85, 1)
    bs.inputs["Emission Strength"].default_value = 0.35
    jk.finish(m, bs.outputs[0], al.outputs[0])
    me_.materials.append(m)
    o = bpy.data.objects.new("Falls", me_)
    scene.collection.objects.link(o)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0,
                                         location=(*(lip + d * 140.0 * width / 100.0 - (cx, cy)), zbot + 45.0 * max(width / 100.0, 0.5)))
    mist = bpy.context.active_object
    mist.name = "Spray"
    k_ = max(width / 100.0, 0.45)
    mist.scale = (210.0 * k_, 190.0 * k_, 95.0 * k_)
    mm = bpy.data.materials.new("M_Spray")
    mm.use_nodes = True
    nt = mm.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    vs = nt.nodes.new("ShaderNodeVolumePrincipled")
    tco = nt.nodes.new("ShaderNodeTexCoord")
    ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"
    nt.links.new(tco.outputs["Object"], ln.inputs[0])
    fall = nt.nodes.new("ShaderNodeMapRange")
    fall.inputs[1].default_value, fall.inputs[2].default_value = 0.2, 1.0
    fall.inputs[3].default_value, fall.inputs[4].default_value = 0.007, 0.0
    nt.links.new(ln.outputs["Value"], fall.inputs[0])
    nzv = nt.nodes.new("ShaderNodeTexNoise"); nzv.inputs["Scale"].default_value = 3.0
    nt.links.new(tco.outputs["Object"], nzv.inputs["Vector"])
    mulv = nt.nodes.new("ShaderNodeMath"); mulv.operation = "MULTIPLY"
    nt.links.new(fall.outputs[0], mulv.inputs[0])
    nt.links.new(nzv.outputs["Fac"], mulv.inputs[1])
    nt.links.new(mulv.outputs[0], vs.inputs["Density"])
    vs.inputs["Color"].default_value = (0.92, 0.94, 0.96, 1)
    vs.inputs["Anisotropy"].default_value = 0.35
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(vs.outputs[0], out.inputs["Volume"])
    mist.data.materials.append(mm)


def haze_box(name, P, Z, width=110.0, height=40.0, density=0.008):
    """A low, broken haze along a stretch of track (the mist trail)."""
    c = P.mean(0)
    d = P[-1] - P[0]
    L = float(np.linalg.norm(d))
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(c[0] - cx, c[1] - cy, float(np.mean(Z)) + height * 0.6))
    o = bpy.context.active_object
    o.name = name
    o.scale = (L / 2 + 60.0, width, height)
    o.rotation_euler = (0, 0, math.atan2(d[1], d[0]))
    m = bpy.data.materials.new("M_" + name)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    vs = nt.nodes.new("ShaderNodeVolumePrincipled")
    vs.inputs["Color"].default_value = (0.92, 0.94, 0.96, 1)
    tco = nt.nodes.new("ShaderNodeTexCoord")
    nzv = nt.nodes.new("ShaderNodeTexNoise"); nzv.inputs["Scale"].default_value = 4.0
    nt.links.new(tco.outputs["Object"], nzv.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs[1].default_value, mr.inputs[2].default_value = 0.4, 0.7
    mr.inputs[3].default_value, mr.inputs[4].default_value = 0.0, density
    nt.links.new(nzv.outputs["Fac"], mr.inputs[0])
    nt.links.new(mr.outputs[0], vs.inputs["Density"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(vs.outputs[0], out.inputs["Volume"])
    o.data.materials.append(m)


def cave_objects():
    """The hill over the cave (its surface, coloured as the forest floor) and the cave's ceiling (an arch); root pillars
    along the walls, curtains of roots high over the mouths, warm lights under the ceiling (in the game Lumen bounces
    the skylights' sun round the cave; Cycles here needs help)."""
    idx = -np.ones(H.shape, np.int64)
    cells = np.argwhere(ROOF)
    idx[cells[:, 0], cells[:, 1]] = np.arange(len(cells))
    q = []
    for dj, di in ((0, 0),):
        a = idx[:-1, :-1]; b = idx[:-1, 1:]; c = idx[1:, 1:]; d = idx[1:, :-1]
        ok = (a >= 0) & (b >= 0) & (c >= 0) & (d >= 0)
        q = np.stack([a[ok], b[ok], c[ok], d[ok]], 1)
    n = len(cells)
    xs, ys = X0 + cells[:, 1] * RES - cx, Y0 + cells[:, 0] * RES - cy
    vt = np.stack([xs, ys, H_TOP[cells[:, 0], cells[:, 1]]], 1)
    vb = np.stack([xs, ys, CEIL[cells[:, 0], cells[:, 1]]], 1)
    me_ = bpy.data.meshes.new("CaveRoof")
    me_.from_pydata(np.vstack([vt, vb]).tolist(), [], np.vstack([q, q[:, ::-1] + n]).tolist())
    ca_ = me_.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    floor_c = (FLOOR[None] * (0.8 + 0.4 * nc[cells[:, 0], cells[:, 1]])[:, None]).astype(np.float32)
    ca_.data.foreach_set("color", np.c_[np.vstack([floor_c, floor_c * 0.5]), np.ones(2 * n, np.float32)].ravel())
    wa_ = me_.attributes.new("Wet", "FLOAT", "POINT")
    wa_.data.foreach_set("value", np.zeros(2 * n, np.float32))
    me_.materials.append(me.materials[0])
    cm = bpy.data.materials.new("M_CaveCeiling")
    cm.use_nodes = True
    nt = cm.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.4; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.025, 0.02, 0.015, 1)
    ramp.color_ramp.elements[1].color = (0.11, 0.085, 0.06, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs[0])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.inputs["Roughness"].default_value = 0.9
    nt.links.new(ramp.outputs[0], bs.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs[0], bs.inputs["Normal"])
    jk.finish(cm, bs.outputs[0])
    me_.materials.append(cm)
    me_.polygons.foreach_set("material_index", np.r_[np.zeros(len(q), np.int32), np.ones(len(q), np.int32)])
    me_.polygons.foreach_set("use_smooth", np.ones(2 * len(q), bool))
    scene.collection.objects.link(bpy.data.objects.new("CaveRoof", me_))
    mb = jk.MB()
    ib, isd = CAVE_SPAN[0] - rlo, CAVE_SPAN[1] - rlo
    hw0 = float(RW[ib])
    f9 = [fd for fd in FD if "Subterrâneo" in fd["f"]["name"]][0]
    d9g = line_field(f9["P"], reach=3)[0]
    for k, i in enumerate(range(ib + 60, isd - 60, 90)):           # root pillars along the walls, never on F9
        t = RP[i + 5] - RP[i - 5]
        t = t / np.linalg.norm(t)
        best = None
        for side in (1, -1):
            q_ = RP[i] + np.array([-t[1], t[0]]) * side * (hw0 + 8.0)
            if grid_at(ROOF, q_[0], q_[1]) and grid_at(d9g, q_[0], q_[1]) > f9["hw"] + 30.0:
                best = q_
        if best is None:
            continue
        q_ = best
        z0, z1 = float(bilinear(H, q_[0], q_[1])) - 1.0, float(bilinear(CEIL, q_[0], q_[1])) + 1.0
        P0 = np.array([q_[0] - cx, q_[1] - cy, z0])
        mb.tube([P0, P0 + (0, 0, (z1 - z0) * 0.5), P0 + (0, 0, z1 - z0)], [1.5, 0.9, 1.3], "bark", seg=10)
        for a in range(3):
            ang = 2 * math.pi * a / 3 + k
            mb.tube([P0 + (0, 0, 4.0), P0 + (3.2 * math.cos(ang), 3.2 * math.sin(ang), 0.2)], [0.5, 0.2], "bark", seg=6)
    for k in range(ib + 160, isd - 100, 230):                     # root bundles hanging round each skylight
        for a in range(10):
            ang = 2 * math.pi * a / 10 + k
            q_ = RP[k] + np.array([math.cos(ang), math.sin(ang)]) * 15.0
            if not grid_at(ROOF, q_[0], q_[1]):
                continue
            top = float(bilinear(CEIL, q_[0], q_[1]))
            L = max(1.0, (top - float(RZ2[k])) - 10.0) * (0.4 + 0.5 * abs(math.sin(a * 2.3)))
            mb.tube([np.array([q_[0] - cx, q_[1] - cy, top + 1.0]), np.array([q_[0] - cx, q_[1] - cy, top + 1.0 - L])],
                    [0.3, 0.08], "bark", seg=5)
    for i in (ib + 4, isd - 4):                                    # curtains of roots, high over the mouths
        t = RP[i + 5] - RP[i - 5]
        t = t / np.linalg.norm(t)
        nrm = np.array([-t[1], t[0]])
        top = float(bilinear(CEIL, RP[i, 0], RP[i, 1]))
        flo = float(RZ2[i])
        for u in np.linspace(-1, 1, 22):
            q_ = RP[i] + nrm * u * (hw0 + 6.0)
            L = max(1.0, (top - flo) - 9.0) * (0.35 + 0.3 * abs(math.sin(u * 7.0)))
            mb.tube([np.array([q_[0] - cx, q_[1] - cy, top + 1.0]), np.array([q_[0] - cx, q_[1] - cy, top + 1.0 - L])],
                    [0.18, 0.06], "bark", seg=5)
    o = mb.build("CaveRoots", {"bark": bpy.data.materials["M_Bark_Kapok"]})
    scene.collection.objects.link(o)
    for i in range(ib + 40, isd - 20, 110):                        # warm light under the ceiling
        lt = bpy.data.lights.new("CaveLight", "POINT")
        lt.energy, lt.color, lt.shadow_soft_size = 6000.0, (1.0, 0.78, 0.55), 6.0
        lo = bpy.data.objects.new("CaveLight", lt)
        lo.location = (RP[i, 0] - cx, RP[i, 1] - cy, float(bilinear(CEIL, RP[i, 0], RP[i, 1])) - 4.0)
        scene.collection.objects.link(lo)


if CAVE_SPAN:
    cave_objects()
if SECTOR == "S3":
    falls_objects()
for lip_, d_, zt_, zb_, w_ in FALLS:
    falls_objects(lip_, d_, zt_, zb_, w_)
    for fd in FD:
        if "Névoa" in fd["f"]["name"]:
            n_ = len(fd["P"])
            haze_box("NevoaTrilho", fd["P"][int(0.2 * n_):int(0.85 * n_)], fd["zs"][int(0.2 * n_):int(0.85 * n_)])
for fd in FD:
    for k, (a, b, gaps) in enumerate(fd.get("decks", [])):
        deck_object("Ponte_%s_%d" % (fd["f"]["name"].split()[0], k), fd["P"][a:b], fd["zs"][a:b], fd["hw"],
                    [(g0 - a, g1 - a) for g0, g1 in gaps], style="palafita" if "Palafitas" in fd["f"]["name"] else "copa")
    for i in fd.get("roots", []):       # a buttress root arching across the trail at the crest
        t = fd["P"][i + 5] - fd["P"][i - 5]
        t = t / np.linalg.norm(t)
        nv = np.array([-t[1], t[0]])
        L = fd["hw"] + 14.0
        u = np.linspace(-1, 1, 9)
        pts = [np.array([*(fd["P"][i] + nv * L * a_ - cx_c), fd["zs"][i] - 0.4 + 1.2 * (1 - a_ * a_) - 2.5 * a_ * a_])
               for a_, cx_c in zip(u, [np.array([cx, cy])] * 9)]
        mb = jk.MB()
        mb.tube(pts, np.linspace(1.1, 0.8, 9), "bark", seg=10)
        o = mb.build("Raiz_%d" % i, {"bark": bpy.data.materials["M_Bark_Kapok"]})
        scene.collection.objects.link(o)
    for i in fd.get("logs", []):        # a trunk lying across the fork, under the hump
        t = fd["P"][i + 5] - fd["P"][i - 5]
        mb = jk.MB()
        L = 2 * fd["hw"] + 10.0
        mb.tube(np.stack([np.linspace(-L / 2, L / 2, 6), np.zeros(6), np.zeros(6)], 1), np.linspace(1.6, 1.3, 6), "bark", seg=12)
        o = mb.build("Tronco_%d" % i, {"bark": bpy.data.materials["M_Bark"]})
        o.location = (fd["P"][i, 0] - cx, fd["P"][i, 1] - cy, fd["zs"][i] - 1.6 + 0.9)
        o.rotation_euler = (0, 0, math.atan2(t[1], t[0]) + math.pi / 2)
        scene.collection.objects.link(o)

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


EXPO = {"piloto_gruta": 1.4, "piloto_F9": 1.4, "piloto_F13": 1.3}


def shot(name, eye, tgt, lens, haze=None):
    if ONLY and name not in ONLY:
        return
    jk.FOG.update(haze or dict(start=90.0, dist=2600.0, amount=0.88))
    jk.fog_group()
    scene.view_settings.exposure = EXPO.get(name, 0.0)
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
    zf = fd.get("zs", bilinear(H, fd["P"][:, 0], fd["P"][:, 1]))
    at_f = int(0.35 * len(fd["P"]))
    if "Sapopemas" in fd["f"]["name"]:     # in the ravine, coming up to where the bridge crosses over it
        dk = [g for g in FD if g.get("decks")]
        if dk:
            Q = np.vstack([g["P"][a:b] for g in dk for a, b, _x in g["decks"]])[::4]
            dd = np.min(np.hypot(fd["P"][::4, None, 0] - Q[None, :, 0], fd["P"][::4, None, 1] - Q[None, :, 1]), axis=1)
            at_f = max(0, 4 * int(np.argmin(dd)) - 130)
    if "lip" in fd:                        # just off the lip, over the void, the ship falling ahead
        lip, land, P_ = fd["lip"], fd["land"], fd["P"]
        i1, i2 = min(lip + 35, len(P_) - 1), min(lip + 95, len(P_) - 1)
        if ship is not None:
            t = P_[i2 + 1] - P_[i2 - 1]
            ship.location = (P_[i2, 0] - cx, P_[i2, 1] - cy, float(zf[lip]) - 14.0)
            ship.rotation_euler = Euler((math.radians(-14), 0, math.atan2(t[1], t[0]) - math.pi / 2))
            ship.hide_render = False
        shot("piloto_" + nm, Vector((P_[i1, 0] - cx, P_[i1, 1] - cy, float(zf[lip]) + 4.0)),
             Vector((P_[land, 0] - cx, P_[land, 1] - cy, float(zf[land]))), 20)
        continue
    if "Tepui" in fd["f"]["name"]:         # on the ramp, the cliff beside it
        at_f = int(0.22 * len(fd["P"]))
    elif fd.get("decks"):                 # on the bridge, a little before its middle
        a, b, _g = max(fd["decks"], key=lambda r: r[1] - r[0])
        at_f = a + int(0.3 * (b - a))
    pilot("piloto_" + nm, at_f, P=fd["P"], Z=zf)
if SECTOR in WALLS:                      # into a hairpin, its wall on the outside
    bb, _sg = bends(RP)
    inside = np.zeros(len(RP), bool)
    inside[si(S0) + 300:si(S1_) - 300] = True
    apex = int(np.argmax(np.where(inside, bb, 0)))
    pilot("piloto_gancho", apex - 160, ahead=150)
    t_ = RP[apex + 10] - RP[apex - 10]
    t_ = t_ / np.linalg.norm(t_)
    out_ = -_sg[apex] * np.array([-t_[1], t_[0]])
    if ship is not None:
        ship.hide_render = True
    e_ = RP[apex] - t_ * 150 + out_ * 110
    shot("gancho_ar", Vector((e_[0] - cx, e_[1] - cy, float(RZ2[apex]) + 95)),
         Vector((RP[apex, 0] - cx, RP[apex, 1] - cy, float(RZ2[apex]))), 24)
pilot("piloto_reta", si(S0 + int(0.55 * (S1_ - S0))))
for a_, b_ in RIVER_ROADS.get(SECTOR, []):   # in the river, upstream
    pilot("piloto_rio", si((a_ + b_) // 2), ahead=180)
if CAVE_SPAN:                            # in the cave, coming up to a skylight
    pilot("piloto_gruta", si(CAVE_SPAN[0]) + 330, ahead=170)
if SECTOR in OVAL:                       # the oval valley, from just above it, near the start (tallest walls)
    i_ = si(S0 + 700)
    t_ = RP[i_ + 10] - RP[i_ - 10]
    t_ = t_ / np.linalg.norm(t_)
    if ship is not None:
        ship.location = (RP[i_ + 60, 0] - cx, RP[i_ + 60, 1] - cy, float(RZ2[i_ + 60]) + 9.0)
        ship.rotation_euler = Euler((0, math.radians(-35), math.atan2(t_[1], t_[0]) - math.pi / 2))
        ship.hide_render = False
    e_ = RP[i_] - t_ * 60
    shot("oval_ar", Vector((e_[0] - cx, e_[1] - cy, float(RZ2[i_]) + 30)),
         Vector((RP[i_ + 160, 0] - cx, RP[i_ + 160, 1] - cy, float(RZ2[i_ + 160]))), 24)
if SECTOR == "S7" and FALLS:             # the tepui and its waterfall, from over the river
    lip_, d_, zt_, zb_, w_ = FALLS[0]
    if ship is not None:
        ship.hide_render = True
    e_ = lip_ + d_ * 1500.0 + np.array([-d_[1], d_[0]]) * 500.0
    shot("aerea_tepui", Vector((e_[0] - cx, e_[1] - cy, zb_ + 160.0)), Vector((lip_[0] - cx, lip_[1] - cy, zb_ + 170.0)), 24,
         haze=dict(start=900.0, dist=14000.0, amount=0.6))
if SECTOR == "S3":                       # the falls, from down the gorge
    if ship is not None:
        ship.hide_render = True
    shot("aerea_cascata", Vector((LIP_S3[0] + 120 - cx, LIP_S3[1] - 900 - cy, W_LOW + 260)),
         Vector((LIP_S3[0] - cx, LIP_S3[1] - cy, W_LOW + 120)), 28, haze=dict(start=900.0, dist=14000.0, amount=0.6))
mid = RP[si((S0 + S1_) // 2)]
aerial("aerea", (mid[0] - 600, mid[1] - 1500), 620, (mid[0] + 400, mid[1] + 250), lens=24)
aerial("aerea_partida", (RP[si(S0)][0] - 700, RP[si(S0)][1] - 900), 380, (RP[si(S0 + 900)][0], RP[si(S0 + 900)][1]), lens=28)
log("DONE")
