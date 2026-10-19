# Prototype: a mesa-and-butte field as one eroded heightfield, after the study in Docs/ESTUDO_BLENDKIT_CANYONS.md.
# Instead of placing separate rock meshes on a smooth landscape, the ground itself is built from rock layers:
#  1. a domain-warped "rock mass" field decides where rock stands; its contours are the mesa outlines (ragged,
#     with fingers and bays, never circles);
#  2. each layer rises at a fixed level of that field: soft Kayenta ledges (stepped benches), a hard Navajo wall
#     (vertical cliff), rounded Navajo domes on the highest mesas; joint clefts split mesas into blocks;
#  3. fine noise on the contours only shifts each wall in and out, the same at every height: vertical fluting;
#  4. debris falls from every cliff and settles at the angle of repose (33 deg) into talus cones; rock never moves.
# Writes a 16-bit heightmap (Unreal landscape import), a mask (R slope, G debris, B layer), a .blend with the
# coloured mesh and a sunlit preview.
# Usage: blender -b -P sculpt_canyon_field.py -- <out_dir> [seed] [cells]
import bmesh
import bpy
import json
import math
import os
import struct
import sys
import zlib
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
SEED = int(argv[1]) if len(argv) > 1 else 7
N = int(argv[2]) if len(argv) > 2 else 1024
CELL = 2.0  # m between samples, as FEXDesertTerrain
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(SEED)
Y, X = np.mgrid[0:N, 0:N].astype(np.float32)


# ---- Noise: smooth value noise on a wrapping lattice, sampled anywhere (so it can be domain-warped).
def lattice(period):
    m = max(2, int(math.ceil(N / period)) + 2)
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
    total, amp, norm = np.zeros_like(x), 1.0, 0.0
    for o in range(octaves):
        total += amp * sample(lattice(period / (2 ** o)), x, y)
        norm += amp
        amp *= gain
    return total / norm


def smoothstep(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# All noise below works in metres (XM, YM), so the shapes keep their real size whatever the cell count.
XM, YM = X * CELL, Y * CELL

# ---- 1. Rock mass field: where rock stands. Large warp for meandering outlines, small warp for fingers and
# bays. Sizes from the BlendKit canyon: mesas 150-300 m across, separated by 50-150 m of floor.
wx = fbm(XM, YM, 260, 3) * 90
wy = fbm(XM + 517, YM + 211, 260, 3) * 90
fx = XM + wx + fbm(XM, YM, 45, 2) * 16
fy = YM + wy + fbm(XM + 91, YM + 37, 45, 2) * 16
F = fbm(fx, fy, 420, 5, 0.55)
lo, hi = np.percentile(F, 1), np.percentile(F, 99)
F = np.clip((F - lo) / (hi - lo), 0, 1)
# Joint clefts: narrow lines where a ridged noise crosses zero cut the mesas into blocks; stretched so most
# clefts follow one joint direction, as in real sandstone.
cleft = 1.0 - np.abs(fbm(XM, YM * 0.35, 150, 2))
F -= 0.08 * cleft ** 16
# Vertical relief on the walls: tiny in/out shifts of each contour, the same at every height of a wall.
# Broad columns (~25 m) between clefts, then flutes (~8 m and ~4 m). Ridged noise gives flutes a sharp edge
# and a rounded hollow; their depth changes from wall to wall, so some faces are smooth and some deeply grooved.
ridge = lambda period: 1.0 - 2.0 * np.abs(fbm(XM, YM, period, 1))
flute_depth = np.clip(0.5 + 0.9 * fbm(XM + 300, YM, 110, 2), 0.0, 1.0)
F += 0.012 * fbm(XM, YM, 25, 1) + flute_depth * (0.008 * ridge(9) + 0.0035 * ridge(4.5))
q = lambda p: float(np.quantile(F, p))

# ---- 2. Layers, bottom to top: (name, level in F, transition width in F, height in m).
#  Kayenta: two soft ledges (benches). Navajo wall: hard and near-vertical, split in two tiers where an upper
#  tier is set back (a mid-wall ledge, only in some places), with a rounded rim. Navajo dome: rounded tops.
rim = 1.0 + 0.2 * fbm(XM, YM, 60, 2)  # each block of wall tops out at its own height: ragged rim
wall_h = 38.0 * rim
wall_at = q(0.55)
setback = 0.035 * np.clip(fbm(XM + 71, YM + 13, 170, 2) * 2.0, 0.0, 1.0)  # 0 where the wall is one sheer face
layers = [
    ("kayenta_1", q(0.40), 0.020, 3.5),
    ("kayenta_2", q(0.47), 0.014, 4.0),
    ("navajo_wall", wall_at, 0.005, 0.55 * wall_h),
    ("navajo_upper", wall_at + setback, 0.005, 0.32 * wall_h),
    ("navajo_rim", wall_at + setback + 0.014, 0.016, 0.13 * wall_h),
    ("navajo_dome", q(0.86), 0.060, 14.0),
]
# Floor: broad swells, hummocks and small slickrock humps.
floor = 5.0 * fbm(XM, YM, 320, 3) + 2.2 * fbm(XM, YM, 60, 2) + 0.9 * fbm(XM, YM, 14, 2)
rock = floor.copy()
layer_id = np.zeros((N, N), np.float32)
for i, (name, level, width, height) in enumerate(layers):
    s = smoothstep(level - width, level + width, F)
    rock += height * s
    layer_id = np.where(s > 0.5, i + 1, layer_id)
tops = smoothstep(q(0.58), q(0.64), F)
rock += 2.0 * fbm(XM, YM, 36, 3) * tops  # lumpy mesa tops
rock -= 2.6 * (1.0 - np.abs(fbm(XM, YM, 28, 2))) ** 10 * tops  # weathered crack network on the tops

# ---- 2b. Drainage network (the race lines), after the BlendKit "Drainage Ditch" scaled up: dry washes with a
# flat gravel floor; on the outside of each bend the water cuts a high, steep bank in ledges (cut bank), on the
# inside it leaves a low, gentle bank (point bar); where a wash crosses a mesa it cuts a narrow gorge.
# The washes form a circuit: south wash (A) and north wash (B), joined in the west by a tributary wash (C) and in
# the east by a shallow swale over open floor (D: the stretch of the lap outside the drainage, with a ramp out of
# and back into the washes). A braid (E) leaves A and rejoins it further on around an island; side tributaries
# (G, H) come in from the map edges.
S = N * CELL
half_tile = S / 2


def smooth1d(a, window):
    pad = window // 2
    return np.convolve(np.pad(a, pad, mode="edge"), np.ones(window) / window, "valid")[:len(a)]


# Routing: water follows the low ground, so each wash is traced by A* over a cost map of the rock (8 m cells):
# open floor is cheap, the band along every mesa wall (both sides, ~24 m) is very expensive, so washes keep off
# the walls and, when they must cross a mesa, go straight through it (a tunnel) instead of grazing its edge.
import heapq
RG = 4  # router cell = 4 samples = 8 m
mesa_r = layer_id[::RG, ::RG] >= 3
NR = mesa_r.shape[0]


def grow(mask, r):
    out = mask.copy()
    for _ in range(r):
        p_ = np.pad(out, 1)
        out = out | p_[:-2, 1:-1] | p_[2:, 1:-1] | p_[1:-1, :-2] | p_[1:-1, 2:]
    return out


band_r = grow(mesa_r, 3) & grow(~mesa_r, 3)  # cells within ~24 m of a mesa outline, inside or out
route_cost = (1.0 + 1.5 * mesa_r + 9.0 * band_r).ravel().tolist()


def astar(a, b):
    """Cheapest 8-connected path between router cells a and b (row, col)."""
    s, g = a[0] * NR + a[1], b[0] * NR + b[1]
    best = [math.inf] * (NR * NR)
    prev = [-1] * (NR * NR)
    best[s] = 0.0
    heap = [(0.0, s)]
    steps = ((-1, -1, 1.4142), (-1, 0, 1.0), (-1, 1, 1.4142), (0, -1, 1.0), (0, 1, 1.0), (1, -1, 1.4142), (1, 0, 1.0), (1, 1, 1.4142))
    while heap:
        f, cur = heapq.heappop(heap)
        if cur == g:
            break
        ci, cj = divmod(cur, NR)
        gc = best[cur]
        if f - math.hypot(ci - b[0], cj - b[1]) > gc + 1e-9:
            continue  # stale entry
        for di, dj, ln in steps:
            ni, nj = ci + di, cj + dj
            if 0 <= ni < NR and 0 <= nj < NR:
                n_ = ni * NR + nj
                ng = gc + ln * route_cost[n_]
                if ng < best[n_]:
                    best[n_] = ng
                    prev[n_] = cur
                    heapq.heappush(heap, (ng + math.hypot(ni - b[0], nj - b[1]), n_))
    path = [g]
    while path[-1] != s:
        path.append(prev[path[-1]])
    return [divmod(c_, NR) for c_ in path[::-1]]


def to_cell(xm, ym):
    return (int(np.clip(ym / (RG * CELL), 0, NR - 1)), int(np.clip(xm / (RG * CELL), 0, NR - 1)))


def snap_to_floor(cell, reach=20):
    """Moves an inner waypoint that falls on a mesa or its wall band to the nearest open floor cell."""
    i, j = cell
    if route_cost[i * NR + j] <= 1.0:
        return cell
    i0, i1, j0, j1 = max(0, i - reach), min(NR, i + reach + 1), max(0, j - reach), min(NR, j + reach + 1)
    win = np.array(route_cost).reshape(NR, NR)[i0:i1, j0:j1] <= 1.0
    if not win.any():
        return cell
    cand = np.argwhere(win) + [i0, j0]
    k_ = np.argmin(((cand - [i, j]) ** 2).sum(1))
    return tuple(cand[k_])


def free_sides(p, nx_, ny_, w):
    """Open distance (m) from each point to the nearest mesa on its left and on its right, looking up to w + 8 m
    out (0 when the point itself is inside a mesa)."""
    offs = np.arange(0.0, w + 8.0, 1.0)
    out = []
    for sgn in (1.0, -1.0):
        xs_ = p[:, 0, None] + sgn * nx_[:, None] * offs[None, :]
        ys_ = p[:, 1, None] + sgn * ny_[:, None] * offs[None, :]
        hit = layer_id[np.clip((ys_ / CELL).astype(int), 0, N - 1), np.clip((xs_ / CELL).astype(int), 0, N - 1)] >= 3
        out.append(np.where(hit.any(1), hit.argmax(1), len(offs)).astype(float))
    return out[0], out[1]


def resample(pts, step=1.0):
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s_ = np.concatenate([[0.0], np.cumsum(seg)])
    t_ = np.arange(0.0, s_[-1], step)
    return np.stack([np.interp(t_, s_, pts[:, 0]), np.interp(t_, s_, pts[:, 1])], 1)


# name: (waypoints, half width of the floor m, depth m). A waypoint is a tile fraction (x, y) or a junction
# ("A", x, y): the point of an already routed wash nearest to (x, y). Inner waypoints only steer the route.
NETWORK = {
    "A": ([(0.0, 0.33), (0.2, 0.30), (0.4, 0.38), (0.6, 0.31), (0.8, 0.37), (1.0, 0.33)], 15.0, 4.0),
    "B": ([(0.0, 0.70), (0.25, 0.74), (0.5, 0.66), (0.75, 0.72), (1.0, 0.68)], 13.0, 3.5),
    "C": ([("A", 0.2, 0.30), (0.16, 0.44), (0.23, 0.58), ("B", 0.25, 0.74)], 12.0, 3.5),
    "D": ([("A", 0.8, 0.37), (0.87, 0.5), (0.81, 0.61), ("B", 0.75, 0.72)], 16.0, 1.0),
    "E": ([("A", 0.4, 0.38), (0.48, 0.47), ("A", 0.6, 0.31)], 10.0, 3.0),
    "G": ([(0.66, 0.0), (0.68, 0.15), ("A", 0.70, 0.34)], 8.0, 2.5),
    "H": ([(0.42, 1.0), (0.43, 0.85), ("B", 0.38, 0.70)], 8.0, 2.5),
}
# The washes never cut the mesas: where a wash runs through one it goes in a tunnel and the mesa stays whole
# above it. Tunnels shorter than TUNNEL_MIN m are not worth a roof.
TUNNEL_MIN = 12
rock_pre = rock.copy()
layer_pre = layer_id.copy()
curves = {}
junctions = {}  # (wash, other wash, waypoint index) -> index on the other wash
for name, (wps, w, d) in NETWORK.items():
    cells = []
    for k_, wp in enumerate(wps):
        if isinstance(wp[0], str):
            other = curves[wp[0]]["p"]
            ji = int(np.argmin((other[:, 0] - wp[1] * S) ** 2 + (other[:, 1] - wp[2] * S) ** 2))
            junctions[(name, wp[0], k_)] = ji
            cells.append(to_cell(*other[ji]))
        else:
            c_ = to_cell(min(wp[0], 0.999) * S, min(wp[1], 0.999) * S)
            cells.append(c_ if k_ in (0, len(wps) - 1) else snap_to_floor(c_))
    path = []
    for a_, b_ in zip(cells, cells[1:]):
        seg_ = astar(a_, b_)
        path += seg_ if not path else seg_[1:]
    pts = (np.array(path, np.float64)[:, ::-1] + 0.5) * RG * CELL
    for wp_i in (0, -1):  # junction ends land exactly on the other wash
        wp = wps[wp_i]
        if isinstance(wp[0], str):
            pts[wp_i] = curves[wp[0]]["p"][junctions[(name, wp[0], 0 if wp_i == 0 else len(wps) - 1)]]
    for _ in range(2):  # smooth the 8 m staircase into a flowing line
        pts = np.stack([smooth1d(pts[:, 0], 9), smooth1d(pts[:, 1], 9)], 1)
    p = resample(pts)
    # Keep off the walls: like water, the wash centres itself in the passage between mesas (ends stay put).
    for _ in range(12):
        ddx_, ddy_ = np.gradient(p[:, 0]), np.gradient(p[:, 1])
        sp_ = np.hypot(ddx_, ddy_) + 1e-9
        nx_, ny_ = -ddy_ / sp_, ddx_ / sp_
        left, right = free_sides(p, nx_, ny_, w)
        reach = w + 8.0
        push = np.clip((left - right) / 2.0, -2.0, 2.0) * ((left > 0) & (right > 0)) * ((left < reach) | (right < reach))
        push[:5] = push[-5:] = 0.0
        p = p + np.stack([nx_ * push, ny_ * push], 1)
        p = np.stack([smooth1d(p[:, 0], 7), smooth1d(p[:, 1], 7)], 1)
    p = resample(p)
    dx, dy = np.gradient(p[:, 0]), np.gradient(p[:, 1])
    ddx, ddy = np.gradient(dx), np.gradient(dy)
    speed = np.hypot(dx, dy) + 1e-9
    k = (dx * ddy - dy * ddx) / speed ** 3  # >0: turning left
    gi = np.clip(np.round(p[:, 1] / CELL).astype(int), 0, N - 1)
    gj = np.clip(np.round(p[:, 0] / CELL).astype(int), 0, N - 1)
    bed_c = smooth1d(floor[gi, gj], 201) - d  # bed follows the surrounding floor, smoothed over ~200 m
    # Tunnels: the whole floor (centre and both edges, a little beyond) inside a mesa. Where the wash only grazes a
    # mesa (part of the floor inside), the floor is cut through as a narrow slot: these are the few cuts.
    nx, ny = -dy / speed, dx / speed
    inside_all = np.ones(len(p), bool)
    inside_any = np.zeros(len(p), bool)
    for off in (-(w + 4.0), 0.0, w + 4.0):
        ei = np.clip(np.round((p[:, 1] + ny * off) / CELL).astype(int), 0, N - 1)
        ej = np.clip(np.round((p[:, 0] + nx * off) / CELL).astype(int), 0, N - 1)
        m = layer_pre[ei, ej] >= 3
        inside_all &= m
        inside_any |= m
    tun = np.zeros(len(p), bool)
    edges = np.flatnonzero(np.diff(np.concatenate([[0], inside_all.astype(int), [0]])))
    for s0, s1 in zip(edges[::2], edges[1::2]):
        if s1 - s0 >= TUNNEL_MIN:
            tun[s0:s1] = True
    # Floor width per point: in a tight passage between mesas the wash narrows (down to 16 m) instead of cutting
    # the walls; only where even that does not fit is the wall cut (a subtle slot cut).
    left, right = free_sides(p, nx, ny, w)
    wi = np.where((left > 0) & (right > 0), np.minimum(left, right) - 1.5, w)
    wi = np.clip(np.minimum(wi, smooth1d(wi, 31)), 8.0, w)
    wi = np.where(tun, w, wi)
    cut = np.zeros(len(p), bool)
    for off in (-1.0, 1.0):
        ei = np.clip(np.round((p[:, 1] + ny * off * wi) / CELL).astype(int), 0, N - 1)
        ej = np.clip(np.round((p[:, 0] + nx * off * wi) / CELL).astype(int), 0, N - 1)
        cut |= layer_pre[ei, ej] >= 3
    cut &= ~tun
    curves[name] = dict(p=p, t=np.stack([dx, dy], 1) / speed[:, None], k=smooth1d(k, 31), bed=bed_c, w=wi, w0=w, d=d,
                        tun=tun, cut=cut)
Px = np.concatenate([c["p"][:, 0] for c in curves.values()])
Py = np.concatenate([c["p"][:, 1] for c in curves.values()])
Tx = np.concatenate([c["t"][:, 0] for c in curves.values()])
Ty = np.concatenate([c["t"][:, 1] for c in curves.values()])
Pk = np.concatenate([c["k"] for c in curves.values()])
Pbed = np.concatenate([c["bed"] for c in curves.values()])
Pw = np.concatenate([c["w"] for c in curves.values()])
Pd = np.concatenate([np.full(len(c["p"]), c["d"]) for c in curves.values()])
Ptun = np.concatenate([c["tun"] for c in curves.values()])


def shift(a, dy, dx, fill):
    """Like np.roll but without wrapping round the tile edges."""
    out = np.full_like(a, fill)
    ys, yd = (slice(dy, None), slice(None, -dy)) if dy > 0 else ((slice(None, dy), slice(-dy, None)) if dy < 0 else (slice(None), slice(None)))
    xs_, xd = (slice(dx, None), slice(None, -dx)) if dx > 0 else ((slice(None, dx), slice(-dx, None)) if dx < 0 else (slice(None), slice(None)))
    out[ys, xs_] = a[yd, xd]
    return out


# Nearest centreline point for every cell within ~110 m: seed the curve points into the grid, then grow outwards.
inside = (Px >= 0) & (Px < S) & (Py >= 0) & (Py < S)
best = np.full((N, N), -1, np.int64)
best[(Py[inside] / CELL).astype(int), (Px[inside] / CELL).astype(int)] = np.nonzero(inside)[0]
bestd = np.where(best >= 0, (XM - Px[best]) ** 2 + (YM - Py[best]) ** 2, np.inf)
for _ in range(int(110 / CELL)):
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        cand = shift(best, dy, dx, -1)
        ok = cand >= 0
        c = np.where(ok, cand, 0)
        dist = np.where(ok, (XM - Px[c]) ** 2 + (YM - Py[c]) ** 2, np.inf)
        better = dist < bestd
        best = np.where(better, cand, best)
        bestd = np.where(better, dist, bestd)
near = best >= 0
b = np.where(near, best, 0)
lateral = (YM - Py[b]) * Tx[b] - (XM - Px[b]) * Ty[b]  # signed distance from the centreline (+ = left)
# Banks wander in and out a few metres, and the ledges change height, so nothing reads as an engineered cut.
u = np.where(near, np.abs(lateral) + 2.5 * fbm(XM, YM, 45, 2), 1e6)
W, D, bedc = Pw[b], Pd[b], Pbed[b]
outer = smoothstep(-0.0006, 0.0006, -lateral * Pk[b])  # 1 on the outside of a bend
CUT_W, BAR_W = 7.0, 20.0  # m: steep cut bank (two ledges) outside a bend, gentle point bar inside
t_cut = np.clip((u - W) / CUT_W, 0.0, 1.0)
step2 = t_cut * 2 + 0.2 * fbm(XM, YM, 60, 1)
ledges = np.clip((np.floor(step2) + smoothstep(0.35, 0.95, step2 - np.floor(step2))) / 2, 0.0, 1.0)
t_bar = np.clip((u - W) / BAR_W, 0.0, 1.0)
bank = (outer * ledges + (1 - outer) * smoothstep(0.0, 1.0, t_bar) ** 1.4) * (D + 2.0)
gravel = 0.3 * fbm(XM, YM, 7, 2) * (u < W)
target = bedc + bank + gravel
# The open floor and the low Kayenta ledges are carved within the banks. Mesas are only ever opened for the race
# floor itself (u < W + 1): under a tunnel roof, or as a narrow slot where a wash grazes a mesa. Nothing wider.
open_ground = (layer_pre <= 2) & (u < W + BAR_W + 2.0) & ~Ptun[b]
carved = near & (target < rock) & (open_ground | (u < W + 1.0))
rock = np.where(carved, target, rock)
layer_id = np.where(carved & (rock < bedc + D * 0.9 + 1.0), 0, layer_id)
wash_floor = np.where(near, smoothstep(W + 3.0, W - 1.0, u), 0.0)  # 1 on the race floor
in_tunnel = near & Ptun[b] & (u < W + 2.0)

# ---- 3. Talus: each cliff sheds debris at its foot, which settles at the angle of repose. Rock stays put.
def neighbours_max(a, r):
    out = a.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out = np.maximum(out, np.roll(np.roll(a, dy, 0), dx, 1))
    return out


wall_above = neighbours_max(rock, 4) - rock
debris = np.where(wall_above > 8.0, 0.3 * wall_above, 0.0).astype(np.float32)
talus = math.tan(math.radians(33.0)) * CELL
dirs = [(0, 1, 1.0), (1, 0, 1.0), (0, -1, 1.0), (-1, 0, 1.0),
        (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
for _ in range(90):
    t = rock + debris
    flows = []
    for dy, dx, d in dirs:
        nb = np.roll(np.roll(t, -dy, 0), -dx, 1)
        flows.append(np.maximum(t - nb - talus * d, 0.0) * 0.12)
    total = np.sum(flows, axis=0)
    scale = np.where(total > 1e-6, np.minimum(1.0, debris / np.maximum(total, 1e-6)), 0.0)
    for (dy, dx, d), f in zip(dirs, flows):
        moved = f * scale
        debris -= moved
        debris += np.roll(np.roll(moved, dy, 0), dx, 1)
# The flood keeps the wash floor swept: debris only reaches its edges.
debris *= (1.0 - 0.85 * wash_floor) * ~in_tunnel
# Fallen blocks: boulders on the talus, the bigger the thicker the debris (none on the race floor).
boulders = np.maximum(fbm(XM, YM, 6, 2) - 0.15, 0.0) * 3.0 * smoothstep(0.5, 2.5, debris) * (1.0 - wash_floor)
H = rock + debris + boulders

# ---- Measurements used by the masks and the colours.
gy, gx = np.gradient(H, CELL)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))
zlo, zhi = float(H.min()), float(H.max())


def write_png(path, data, bits, channels):
    """Minimal PNG writer (greyscale or RGB, 8 or 16 bit); rows top to bottom."""
    h, w = data.shape[:2]
    if bits == 16:
        raw = data.astype(">u2").reshape(h, w * channels).tobytes()
        stride = w * channels * 2
    else:
        raw = data.astype(np.uint8).reshape(h, w * channels).tobytes()
        stride = w * channels
    rows = b"".join(b"\x00" + raw[r * stride:(r + 1) * stride] for r in range(h))
    colour = 0 if channels == 1 else 2

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, bits, colour, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


write_png(f"{OUT}/canyon_field_height16.png", np.round((H - zlo) / (zhi - zlo) * 65535)[::-1], 16, 1)
mask = np.stack([np.clip(slope / 90.0, 0, 1) * 255, np.clip(debris / 6.0, 0, 1) * 255, layer_id / len(layers) * 255], -1)
write_png(f"{OUT}/canyon_field_mask.png", mask[::-1], 8, 3)

# ---- Mesh with vertex colours.
#  Walls: horizontal strata (uneven beds, a bleached band under the rim, darker base) and dark desert-varnish
#  streaks running down from the rim. Floor: pale wind-blown sand with redder slickrock patches. Talus: rockier
#  and darker than the sand. Tops: pale weathered Navajo.
sand = np.array([0.62, 0.31, 0.12]); slick = np.array([0.50, 0.20, 0.08]); kay = np.array([0.42, 0.15, 0.06])
wall = np.array([0.52, 0.17, 0.06]); bleach = np.array([0.66, 0.36, 0.17]); dome = np.array([0.64, 0.35, 0.16])
varnish = np.array([0.22, 0.09, 0.05])
steep = smoothstep(35, 60, slope)[..., None]
lid = layer_id[..., None]
# Height within the wall: 0 at the foot of the Navajo wall, 1 at its rim (approximate: floor + benches below).
in_wall = np.clip((H - 8.0) / np.maximum(wall_h, 1.0), 0.0, 1.0)[..., None]
beds = np.sin(H / 2.2 + 1.5 * fbm(XM, YM, 140, 2)) * 0.5 + 0.5
strata = (0.86 + 0.14 * beds ** 3)[..., None]
wallcol = wall * strata * (0.85 + 0.15 * in_wall)
wallcol = wallcol + (bleach - wallcol) * smoothstep(0.72, 0.9, in_wall) * 0.7
streak = smoothstep(0.15, 0.55, fbm(XM, YM, 7, 2) + 0.3 * fbm(XM, YM, 3, 1))[..., None]
wallcol = wallcol + (varnish - wallcol) * streak * smoothstep(0.25, 0.95, in_wall) * 0.55
rockcol = np.where(lid >= 6, dome, np.where(lid >= 3, wallcol, kay * strata))
patch = smoothstep(0.05, 0.35, fbm(XM + 40, YM + 900, 90, 3))[..., None]
groundcol = sand + (slick - sand) * patch * 0.8
col = groundcol * (1 - steep) + rockcol * steep
col = np.where((lid >= 3) & (steep < 0.5), dome * 0.85 + sand * 0.15, col)  # mesa tops
# Wash floor: pale, greyer gravel and flood-washed sand, with darker damp streaks along the flow.
gravelcol = np.array([0.58, 0.36, 0.20]) * (0.9 + 0.1 * fbm(XM * 0.4, YM * 2.5, 20, 2))[..., None]
col = col + (gravelcol - col) * (wash_floor[..., None] * (1 - steep) * 0.85)
deb = smoothstep(0.3, 2.5, debris)[..., None] * (1 - steep)
col = col * (1 - deb) + (0.45 * sand + 0.55 * wall * 0.8) * deb
col *= (0.92 + 0.08 * fbm(XM, YM, 24, 2) + 0.04 * fbm(XM, YM, 5, 1))[..., None]
# A touch more saturation: the Utah reds read stronger under a low sun.
grey = col.mean(-1, keepdims=True)
col = np.clip(grey + (col - grey) * 1.25, 0.0, 1.0)
# Colour the tunnel roofs take on top: the terrain colour, except over the opened tunnel floor, where the mesa
# top colour is put back (the roof hides that strip of floor).
mesa_top = (dome * 0.85 + sand * 0.15) * (0.92 + 0.08 * fbm(XM, YM, 24, 2))[..., None]
g2 = mesa_top.mean(-1, keepdims=True)
col_pre = np.where(in_tunnel[..., None], np.clip(g2 + (mesa_top - g2) * 1.25, 0.0, 1.0), col)

bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("CanyonField")
co = np.stack([(X - N / 2) * CELL, (Y - N / 2) * CELL, H], -1).astype(np.float32).ravel()
me.vertices.add(N * N)
me.vertices.foreach_set("co", co)
idx = np.arange(N * N, dtype=np.int32).reshape(N, N)
quads = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).ravel()
me.loops.add(len(quads))
me.loops.foreach_set("vertex_index", quads)
me.polygons.add((N - 1) ** 2)
me.polygons.foreach_set("loop_start", np.arange(0, len(quads), 4, dtype=np.int32))
me.update(calc_edges=True)
me.polygons.foreach_set("use_smooth", np.ones((N - 1) ** 2, bool))
attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
attr.data.foreach_set("color", np.concatenate([col.reshape(-1, 3), np.ones((N * N, 1))], 1).astype(np.float32).ravel())
obj = bpy.data.objects.new("CanyonField", me)
bpy.context.scene.collection.objects.link(obj)
mat = bpy.data.materials.new("M_CanyonField")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
attr_node = nt.nodes.new("ShaderNodeAttribute")
attr_node.attribute_name = "Col"
nt.links.new(attr_node.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.92
me.materials.append(mat)

# ---- Tunnel roofs: the heightfield only holds the slot and the floor; each tunnel gets a rock roof mesh laid
# over the slot, its top following the mesa that was there and its underside a rounded natural vault (16 m clear
# in the middle, coming down to the floor edges). Its end faces are the portals. One FBX per roof for Unreal.
def bilinear(grid, x, y):
    fx, fy = np.clip(x / CELL, 0, N - 1.001), np.clip(y / CELL, 0, N - 1.001)
    j, i = fx.astype(int), fy.astype(int)
    tx, ty = fx - j, fy - i
    if grid.ndim == 3:
        tx, ty = tx[..., None], ty[..., None]
    top = grid[i, j] * (1 - tx) + grid[i, j + 1] * tx
    bottom = grid[i + 1, j] * (1 - tx) + grid[i + 1, j + 1] * tx
    return top * (1 - ty) + bottom * ty


def rock_at(x, y):
    return bilinear(rock_pre, x, y)


os.makedirs(f"{OUT}/tunnels", exist_ok=True)
tunnels = []
for cname, c in curves.items():
    edges = np.flatnonzero(np.diff(np.concatenate([[0], c["tun"].astype(int), [0]])))
    for k, (s0, s1) in enumerate(zip(edges[::2], edges[1::2])):
        idx = np.arange(s0, s1, 2)
        if len(idx) < 4:
            continue
        p, t, bedv, w = c["p"][idx], c["t"][idx], c["bed"][idx], c["w0"]
        L = np.linspace(-(w + 5.0), w + 5.0, 41)
        x2 = p[:, None, 0] - L[None, :] * t[:, None, 1]
        y2 = p[:, None, 1] + L[None, :] * t[:, None, 0]
        a = np.clip(np.abs(L) / (w + 1.0), 0.0, 1.0)
        vault = 2.0 + 14.0 * np.sqrt(np.maximum(0.0, 1.0 - a ** 2))
        under = bedv[:, None] + np.where(np.abs(L)[None, :] <= w + 1.0, vault[None, :], -1.0)
        top = np.maximum(rock_at(x2, y2) + 0.15, under + 3.0)
        ns, nl = top.shape
        verts = np.concatenate([np.stack([x2 - half_tile, y2 - half_tile, top], -1).reshape(-1, 3),
                                np.stack([x2 - half_tile, y2 - half_tile, under], -1).reshape(-1, 3)])
        T = lambda i, j: i * nl + j
        B = lambda i, j: ns * nl + i * nl + j
        faces = []
        for i in range(ns - 1):
            for j in range(nl - 1):
                faces.append((T(i, j), T(i + 1, j), T(i + 1, j + 1), T(i, j + 1)))
                faces.append((B(i, j), B(i, j + 1), B(i + 1, j + 1), B(i + 1, j)))
            for j in (0, nl - 1):
                faces.append((T(i, j), B(i, j), B(i + 1, j), T(i + 1, j)))
        for i in (0, ns - 1):
            for j in range(nl - 1):
                faces.append((T(i, j), T(i, j + 1), B(i, j + 1), B(i, j)))
        rme = bpy.data.meshes.new(f"SM_Tunnel_{cname}{k + 1}")
        rme.from_pydata(verts.tolist(), [], faces)
        rbm = bmesh.new()
        rbm.from_mesh(rme)
        bmesh.ops.recalc_face_normals(rbm, faces=rbm.faces)
        rbm.to_mesh(rme)
        rbm.free()
        z = verts[:, 2]
        beds_v = (0.86 + 0.14 * (np.sin(z / 2.2) * 0.5 + 0.5) ** 3)[:, None]
        # Top: the terrain's own colour at that spot (seamless with the mesa); vault: banded wall rock.
        top_col = bilinear(col_pre, x2, y2).reshape(-1, 3)
        rcol = np.concatenate([top_col, (wall * beds_v)[ns * nl:]])
        rattr = rme.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        rattr.data.foreach_set("color", np.concatenate([rcol, np.ones((len(verts), 1))], 1).astype(np.float32).ravel())
        rme.materials.append(mat)
        roof = bpy.data.objects.new(rme.name, rme)
        bpy.context.scene.collection.objects.link(roof)
        bpy.ops.object.select_all(action="DESELECT")
        roof.select_set(True)
        bpy.context.view_layer.objects.active = roof
        bpy.ops.export_scene.fbx(filepath=f"{OUT}/tunnels/{rme.name}.fbx", use_selection=True, object_types={"MESH"})
        tunnels.append({"name": rme.name, "wash": cname, "length_m": int(s1 - s0),
                        "portal_in": [round(float(c["p"][s0, 0] - half_tile), 1), round(float(c["p"][s0, 1] - half_tile), 1)],
                        "portal_out": [round(float(c["p"][s1 - 1, 0] - half_tile), 1), round(float(c["p"][s1 - 1, 1] - half_tile), 1)],
                        "start_index": int(s0)})
print("TUNNELS", [(tt["name"], tt["length_m"]) for tt in tunnels])
# Slot cuts: where a wash grazes a mesa and the floor was cut through it (the only cuts into mesas).
cuts = []
for cname, c in curves.items():
    edges = np.flatnonzero(np.diff(np.concatenate([[0], c["cut"].astype(int), [0]])))
    for s0, s1 in zip(edges[::2], edges[1::2]):
        if s1 - s0 >= 6:
            cuts.append({"wash": cname, "length_m": int(s1 - s0),
                         "at": [round(float(c["p"][s0, 0] - half_tile), 1), round(float(c["p"][s0, 1] - half_tile), 1)]})
print("CUTS", [(cc["wash"], cc["length_m"]) for cc in cuts])
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/canyon_field.blend")

# ---- Preview: low warm sun across the field, camera above one corner looking in.
scene = bpy.context.scene
world = bpy.data.worlds.new("Sky")
world.use_nodes = True
# Physical sky with a late-afternoon sun (25 deg up) from the same side as the sun lamp, plus a little dust haze.
SUN_ELEV, SUN_AZ = math.radians(25), math.radians(-35)
sky = world.node_tree.nodes.new("ShaderNodeTexSky")
sky.sky_type = "NISHITA"
sky.sun_elevation = SUN_ELEV
sky.sun_rotation = SUN_AZ + math.pi
sky.air_density = 1.4
sky.dust_density = 3.0
sky.sun_disc = False
world.node_tree.links.new(sky.outputs["Color"], world.node_tree.nodes["Background"].inputs[0])
world.node_tree.nodes["Background"].inputs[1].default_value = 0.12
scene.world = world
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy = 3.6
sun.data.angle = math.radians(1.5)
sun.data.color = (1.0, 0.82, 0.62)
sun.rotation_euler = (math.pi / 2 - SUN_ELEV, 0, SUN_AZ)
scene.collection.objects.link(sun)
scene.view_settings.look = "AgX - Punchy"
scene.view_settings.exposure = -0.2
half = N * CELL / 2
# Preview only: a wide sand plain under the tile so the horizon is not empty (not in the .blend or heightmap).
bpy.ops.mesh.primitive_plane_add(size=40000, location=(0, 0, float(H.min()) - 1.0))
plain_mat = bpy.data.materials.new("M_Plain")
plain_mat.use_nodes = True
plain_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*(sand * 0.95), 1.0)
plain_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
bpy.context.active_object.data.materials.append(plain_mat)


def ground(x, y):
    i = int(np.clip(round(y / CELL + N / 2), 0, N - 1))
    j = int(np.clip(round(x / CELL + N / 2), 0, N - 1))
    return float(H[i, j])


# Racer views: in the washes, 4 m up, looking along them; and the braid from above.
def wash_at(name, fraction, ahead=160.0):
    """A point on a wash centreline (mesh coordinates) and the point `ahead` metres further along it."""
    p = curves[name]["p"]
    i = int(fraction * (len(p) - 1))
    j = min(len(p) - 1, i + int(ahead))
    return (float(p[i, 0] - half), float(p[i, 1] - half)), (float(p[j, 0] - half), float(p[j, 1] - half))


def pilot(name, fraction):
    a, b = wash_at(name, fraction)
    return ((a[0], a[1], ground(*a) + 4.0), (b[0], b[1], ground(*b) + 5.0), 22)


ea, eb = wash_at("E", 0.0, 250.0)
shots = {"oblique": ((-half * 0.55, -half * 0.55, 160.0), (0.0, 0.0, 10.0), 32),
         "wash_A": pilot("A", 0.3),
         "wash_C": pilot("C", 0.35),
         "swale_D": pilot("D", 0.2),
         "wash_B": pilot("B", 0.55),
         "braid_aerial": ((ea[0] - 150.0, ea[1] - 260.0, ground(*ea) + 160.0), (eb[0], eb[1], ground(*eb)), 26)}
for k, tt in enumerate(tunnels[:2]):  # pilot view 80 m before each portal, looking into the tunnel
    pc = curves[tt["wash"]]["p"]
    i0 = max(0, tt["start_index"] - 80)
    i1 = min(len(pc) - 1, tt["start_index"] + 40)
    a, b2 = (pc[i0, 0] - half, pc[i0, 1] - half), (pc[i1, 0] - half, pc[i1, 1] - half)
    bz = float(curves[tt["wash"]]["bed"][i0])
    shots[f"tunnel_{k + 1}"] = ((a[0], a[1], bz + 4.0), (b2[0], b2[1], bz + 8.0), 22)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.clip_end = 20000
scene.collection.objects.link(cam)
scene.camera = cam
# Cycles on the CPU: Eevee crashes in background mode on machines where Blender sees no OpenGL device.
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
from mathutils import Vector
for name, (eye, target, lens) in shots.items():
    cam.location = eye
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    scene.render.filepath = f"{OUT}/canyon_field_{name}.png"
    bpy.ops.render.render(write_still=True)

def stretch(name, i0, i1):
    """Points of a wash from index i0 to i1 (either direction), as [x, y, bed] in metres from the tile centre."""
    p, z = curves[name]["p"], curves[name]["bed"]
    idx = range(i0, i1 + 1) if i1 >= i0 else range(i0, i1 - 1, -1)
    return [[round(float(p[i, 0] - half), 1), round(float(p[i, 1] - half), 1), round(float(z[i]), 1)] for i in idx]


nC, nD = len(NETWORK["C"][0]) - 1, len(NETWORK["D"][0]) - 1
lap = (stretch("A", junctions[("C", "A", 0)], junctions[("D", "A", 0)])
       + stretch("D", 0, len(curves["D"]["p"]) - 1)
       + stretch("B", junctions[("D", "B", nD)], junctions[("C", "B", nC)])
       + stretch("C", len(curves["C"]["p"]) - 1, 0))
lap_m = float(sum(math.dist(a[:2], b[:2]) for a, b in zip(lap, lap[1:])))
circuit = {"length_m": round(lap_m), "points": lap[::8]}
stats = {"seed": SEED, "cells": N, "cell_m": CELL, "size_m": N * CELL, "z_m": [round(zlo, 1), round(zhi, 1)],
         "heightmap_note": "16-bit PNG spans z_m; Unreal Z scale (%) = (z_max - z_min) * 100 / 512",
         "engine": scene.render.engine,
         # Drainage network and the circuit lap, every 8 m, in metres from the tile centre (x east, y north,
         # z bed level). Lap: A west->east, swale D north, B east->west, tributary C south back onto A.
         "network": {name: {"floor_width_m": 2 * c["w0"], "narrowest_m": round(2 * float(c["w"].min()), 1), "depth_m": c["d"],
                            "centreline": [[round(float(x - half), 1), round(float(y - half), 1), round(float(z), 1)]
                                           for (x, y), z in zip(c["p"][::8], c["bed"][::8])]}
                     for name, c in curves.items()},
         "circuit": circuit,
         "tunnels": tunnels,
         "cuts": cuts}
with open(f"{OUT}/canyon_field.json", "w") as f:
    json.dump(stats, f, indent=1)
print("CANYON FIELD", json.dumps({k: v for k, v in stats.items() if k not in ("network", "circuit", "tunnels", "cuts")}),
      "lap_m", circuit["length_m"], "tunnels", len(tunnels))
