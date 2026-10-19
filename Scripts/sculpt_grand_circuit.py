# Grand circuit of the Red Dust Divide world (10 x 8 km, sculpt_expansion.py): one long lap through the whole map,
# past its landmarks, with branches that leave it and come back.
# The dunes must be crossed going north: the windward side of every crest faces south, so driving north the craft
# takes off from the sharp crest; driving south it would meet the 33 degree slip face. Hence the order of the lap:
#   core wash A eastwards (its tunnels and the straight through the mountain) -> south leg of the dune loop D ->
#   slalom through the hoodoos -> north over the dune sea (crest jumps) -> west through the badlands (a tunnel under
#   the middle mesa) -> North_gap -> Chinle westwards past Spider Rock -> Muerto southwards, through the giant arch ->
#   round the Monument Valley buttes -> back to the start of A.
# Branches: B1 the A_west shortcut, B2 the crevices (down the Monument canyon, back up a side canyon), B3 a tunnel
# through the plateau from Chinle to Muerto, B4 the high route (a staircase of flat tops: a sand ramp up, jumps from
# top to top, each 3 m lower, a ramp down), B5 the gravel plain beside the dunes.
# The track never destroys the map: surface routes are driven over the ground as it is; where a route runs through
# rock it goes in a tunnel (the heightfield is opened only under the roof, which is its own mesh); ramps and the
# staircase only add ground.
# Usage: blender -b <world_dir>/world.blend -P sculpt_grand_circuit.py -- <world_dir> [plan]
#   <world_dir> holds world.blend, world_fields.npz, canyon_field.json and props.json (sculpt_expansion.py).
#   plan: routes only; writes gc_plan.png and prints the measurements, changes nothing else.
import heapq
import json
import math
import os
import struct
import sys
import zlib
import numpy as np
import bpy

a = sys.argv[sys.argv.index("--") + 1:]
WD = a[0]
PLAN = len(a) > 1 and a[1] == "plan"
with open(f"{WD}/canyon_field.json") as f_:
    world = json.load(f_)
fz = np.load(f"{WD}/world_fields.npz")
SX, SY, CELL = world["size_x_m"], world["size_y_m"], world["cell_m"]
hx, hy = SX / 2, SY / 2
H = fz["H"].astype(np.float32).copy()
floor = fz["floor"].astype(np.float32)
sea, in_core = fz["sea"], fz["in_core"]
NY, NX = H.shape
Y, X = np.mgrid[0:NY, 0:NX].astype(np.float32)
XM, YM = X * CELL, Y * CELL
rng = np.random.default_rng(world["seed"] + 1300)
LM = world["landmarks"]


# ---- Noise (same value noise as the other generators).
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


# ---- Polyline helpers (as in sculpt_canyon_field.py).
def smooth1d(v, window):
    pad = window // 2
    return np.convolve(np.pad(v, pad, mode="edge"), np.ones(window) / window, "valid")[:len(v)]


def resample(pts, step=1.0):
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s_ = np.concatenate([[0.0], np.cumsum(seg)])
    t_ = np.arange(0.0, s_[-1], step)
    out = np.stack([np.interp(t_, s_, pts[:, 0]), np.interp(t_, s_, pts[:, 1])], 1)
    if np.hypot(*(out[-1] - pts[-1])) > 0.01:  # keep the exact end
        out = np.vstack([out, pts[-1][None]])
    return out


def curvature(p, window=31):
    q_ = np.stack([smooth1d(p[:, 0], window), smooth1d(p[:, 1], window)], 1)
    dx_, dy_ = np.gradient(q_[:, 0]), np.gradient(q_[:, 1])
    ddx_, ddy_ = np.gradient(dx_), np.gradient(dy_)
    return (dx_ * ddy_ - dy_ * ddx_) / (np.hypot(dx_, dy_) ** 3 + 1e-9)


def relax(p, rmin, fixed=None, iters=80, reach=30):
    """Opens every bend tighter than rmin (scalar or per point) a little each pass, pulling its points towards the
    chord between the points reach m before and after. Fixed points (and both ends) stay where they are."""
    a0, a1 = p[0].copy(), p[-1].copy()
    rm = np.asarray(rmin, float) if np.ndim(rmin) else np.full(len(p), float(rmin))
    fx_ = np.zeros(len(p), bool) if fixed is None else fixed
    for _ in range(iters):
        k_ = curvature(p)
        bad = (np.abs(k_) * rm > 1.0) & ~fx_
        bad[:reach] = False
        bad[-reach:] = False
        if not bad.any():
            break
        ii = np.arange(len(p))
        mid = 0.5 * (p[np.clip(ii - reach, 0, len(p) - 1)] + p[np.clip(ii + reach, 0, len(p) - 1)])
        wgt = (np.clip(np.abs(k_) * rm - 1.0, 0.0, 1.0) * bad)[:, None]
        p = p + 0.4 * wgt * (mid - p)
        sm = np.stack([smooth1d(p[:, 0], 5), smooth1d(p[:, 1], 5)], 1)
        p = np.where(fx_[:, None], p, sm)
        p[0], p[-1] = a0, a1
    return p


def bilinear(grid, x, y):
    fx, fy = np.clip(np.asarray(x) / CELL, 0, NX - 1.001), np.clip(np.asarray(y) / CELL, 0, NY - 1.001)
    j, i = fx.astype(int), fy.astype(int)
    tx, ty = fx - j, fy - i
    top = grid[i, j] * (1 - tx) + grid[i, j + 1] * tx
    bottom = grid[i + 1, j] * (1 - tx) + grid[i + 1, j + 1] * tx
    return top * (1 - ty) + bottom * ty


def grow(mask, r):
    out = mask.copy()
    for _ in range(r):
        p_ = np.pad(out, 1)
        out = out | p_[:-2, 1:-1] | p_[2:, 1:-1] | p_[1:-1, :-2] | p_[1:-1, 2:]
    return out


def superellipse(cx_, cy_, ax, ay, rot, n=4.0):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    u = ((XM - cx_) * c + (YM - cy_) * s) / ax
    v = (-(XM - cx_) * s + (YM - cy_) * c) / ay
    return (np.abs(u) ** n + np.abs(v) ** n) ** (1.0 / n)


def wc(p):
    """JSON point (metres from the world centre) -> world metres from the south-west corner."""
    return np.array([p[0] + hx, p[1] + hy], np.float64)


H0 = H.copy()  # the world as sculpt_expansion.py left it
added = np.zeros((NY, NX), np.float32)  # 1 where new rock (staircase) was built, 2 where sand (ramps)

# ---- 1. B4 high route: the staircase. A sand ramp climbs north out of the dune sea onto a broad flat top (the
# lookout), the route turns west on it and runs along a row of flat-topped blocks, each 3 m lower than the one before,
# with 35-60 m gaps between them (jumps from top to top), then a sand ramp takes it back down to the badlands floor.
STAIR_Y = 5800.0
LOOK = (9780.0, STAIR_Y, 115.0)  # lookout: centre x, y and half size
STAIR_END_X = 7350.0  # west end of the last block
RAMP_DEG = 9.5


def block(cx_, cy_, ax, ay, top, n=6.0):
    """Flat-topped block: steep walls, a small talus cone; never lowers the ground."""
    global H, added
    e = superellipse(cx_, cy_, ax * (1 + 0.04 * fbm(XM, YM, 40, 2)), ay, 0.0, n)
    body = smoothstep(1.02, 0.97, e)
    ground = np.where(e < 1.6, H, 0)
    z = top + 0.3 * fbm(XM, YM, 9, 2)
    cone = np.maximum(0.0, 0.25 * (top - ground) - (e - 1.0) * min(ax, ay) * 0.7) * (e > 1.0) * (e < 1.6)
    newH = np.maximum(H, np.where(body > 0, ground + (z - ground) * body, H))
    newH = np.maximum(newH, np.where(e < 1.6, ground + cone, newH))
    added = np.where((newH > H + 0.5) & (body > 0.5), 1.0, added)
    H = newH


def ramp(p0, p1, z0, z1, half_w=22.0, side_deg=28.0):
    """Straight sand ramp from (p0, z0) to (p1, z1): flat 2*half_w wide, sand shoulders at side_deg."""
    global H, added
    d = np.subtract(p1, p0).astype(np.float64)
    L = float(np.hypot(*d))
    t = d / L
    s_ = ((XM - p0[0]) * t[0] + (YM - p0[1]) * t[1]) / L
    l_ = np.abs(-(XM - p0[0]) * t[1] + (YM - p0[1]) * t[0])
    z = z0 + (z1 - z0) * np.clip(s_, 0.0, 1.0)
    z = z - np.maximum(l_ - half_w, 0.0) * math.tan(math.radians(side_deg))
    z = z - np.maximum(-s_ * L, 0.0) * 0.5 - np.maximum((s_ - 1.0) * L, 0.0) * 2.0  # toe and head blend
    newH = np.maximum(H, z.astype(np.float32))
    added = np.where(newH > H + 0.3, np.maximum(added, 2.0), added)
    H = newH


look_e = superellipse(LOOK[0], LOOK[1], LOOK[2], LOOK[2], 0.0, 6.0) < 1.0
T1 = float(max(H[look_e].max() + 20.0, floor[look_e].mean() + 72.0))
block(LOOK[0], LOOK[1], LOOK[2], LOOK[2], T1)
foot_up = (LOOK[0], LOOK[1] - LOOK[2] - (T1 - float(bilinear(H, LOOK[0], LOOK[1] - LOOK[2] - 400))) / math.tan(math.radians(RAMP_DEG)))
ramp(foot_up, (LOOK[0], LOOK[1] - LOOK[2] + 6.0), float(bilinear(H, *foot_up)), T1)
stair = [{"kind": "lookout", "x": LOOK[0], "y": LOOK[1], "half": LOOK[2], "top": T1}]
x_edge, top = LOOK[0] - LOOK[2], T1
while x_edge > STAIR_END_X + 120:
    gap = float(rng.uniform(35.0, 60.0))
    length = float(min(rng.uniform(150.0, 230.0), x_edge - gap - STAIR_END_X))
    x1 = x_edge - gap
    cx_ = x1 - length / 2
    under = (np.abs(XM - cx_) < length / 2 + 4) & (np.abs(YM - STAIR_Y) < 40)
    want = top - 3.0
    least = float(H[under].max()) + 18.0  # each block stands at least 18 m clear of the ground under it
    kick = 0.0
    if want < least:
        kick = max(0.0, least - (top - 1.0))  # an uphill jump: raise the lip of the block before
        want = least
    if kick > 0.0:
        lip = (np.abs(XM - (x_edge + 12.0)) < 12.0) & (np.abs(YM - STAIR_Y) < 36)
        H = np.where(lip, np.maximum(H, top + kick * smoothstep(x_edge + 24.0, x_edge, XM)), H)
    block(cx_, STAIR_Y, length / 2, 36.0, want)
    stair.append({"kind": "block", "x": cx_, "y": STAIR_Y, "half_len": length / 2, "top": want, "gap_before": gap,
                  "kicker_m": kick})
    x_edge, top = x1 - length, want
foot_dn_x = x_edge - (top - float(bilinear(H, x_edge - 300, STAIR_Y))) / math.tan(math.radians(RAMP_DEG))
foot_dn = (foot_dn_x, STAIR_Y)
ramp((x_edge + 6.0, STAIR_Y), foot_dn, top, float(bilinear(H, *foot_dn)))
print("STAIR", len(stair), "blocks, tops", round(stair[0]["top"], 1), "->", round(top, 1), "kickers",
      sum(1 for s_ in stair if s_.get("kicker_m", 0) > 0))

# ---- 2. Rock and the router's cost map (8 m cells). Rock: the plateau and mesa field, anything standing 12 m over the
# floor outside the dune sea, the landmarks that stand in the sand (badlands mesas, hoodoos) and the staircase.
rock = (fz["rocky"] > 0.5) | (((H - floor) > 12.0) & ~sea) | (added == 1.0)
for cx_, cy_, ax, ay, rot, h in LM["badlands_mesas"]:
    rock |= superellipse(cx_, cy_, ax, ay, rot) < 1.02
for cx_, cy_, r, h in LM["hoodoos"]:
    rock |= np.hypot(XM - cx_, YM - cy_) < r * 1.6 + 3.0
rock &= ~(added == 2.0)
RG = max(1, int(round(8.0 / CELL)))
rock_r = rock[::RG, ::RG]
NRY, NRX = rock_r.shape
gyr, gxr = np.gradient(H[::RG, ::RG], RG * CELL)
steep_r = (np.hypot(gxr, gyr) > 0.35) & ~sea[::RG, ::RG]
base_r = 1.0 + 3.0 * steep_r + 30.0 * (in_core[::RG, ::RG] & ~sea[::RG, ::RG]) - 0.15 * (fz["canyon_floor"][::RG, ::RG] > 0.5)
_costs = {}


def cost_for(r):
    if r not in _costs:
        band = grow(rock_r, r) & grow(~rock_r, r)
        _costs[r] = (base_r + 1.5 * rock_r + 12.0 * band).ravel().tolist()
    return _costs[r]


def astar(a_, b_, route_cost):
    s, g = a_[0] * NRX + a_[1], b_[0] * NRX + b_[1]
    best = {s: 0.0}
    prev = {}
    heap = [(0.0, s)]
    steps = ((-1, -1, 1.4142), (-1, 0, 1.0), (-1, 1, 1.4142), (0, -1, 1.0), (0, 1, 1.0), (1, -1, 1.4142), (1, 0, 1.0), (1, 1, 1.4142))
    while heap:
        f, cur = heapq.heappop(heap)
        if cur == g:
            break
        ci, cj = divmod(cur, NRX)
        gc = best[cur]
        if f - 0.85 * math.hypot(ci - b_[0], cj - b_[1]) > gc + 1e-9:
            continue
        for di, dj, ln in steps:
            ni, nj = ci + di, cj + dj
            if 0 <= ni < NRY and 0 <= nj < NRX:
                n_ = ni * NRX + nj
                ng = gc + ln * route_cost[n_]
                if ng < best.get(n_, math.inf):
                    best[n_] = ng
                    prev[n_] = cur
                    heapq.heappush(heap, (ng + 0.85 * math.hypot(ni - b_[0], nj - b_[1]), n_))
    path = [g]
    while path[-1] != s:
        path.append(prev[path[-1]])
    return [divmod(c_, NRX) for c_ in path[::-1]]


def to_cell(p):
    return (int(np.clip(p[1] / (RG * CELL), 0, NRY - 1)), int(np.clip(p[0] / (RG * CELL), 0, NRX - 1)))


def snap(cell, route_cost, reach=25):
    """Moves a steering waypoint that falls on rock or a wall band to the nearest open cell."""
    i, j = cell
    lim = base_r[i, j] + 0.01
    if route_cost[i * NRX + j] <= lim:
        return cell
    i0, i1, j0, j1 = max(0, i - reach), min(NRY, i + reach + 1), max(0, j - reach), min(NRX, j + reach + 1)
    win = np.array(route_cost).reshape(NRY, NRX)[i0:i1, j0:j1] <= base_r[i0:i1, j0:j1] + 0.01
    if not win.any():
        return cell
    cand = np.argwhere(win) + [i0, j0]
    return tuple(cand[np.argmin(((cand - [i, j]) ** 2).sum(1))])


def route(wps, wmin):
    """Waypoints in world metres; (x, y, "S") starts a dead-straight stretch to the next waypoint (through rock if
    any: a tunnel). Returns the polyline (8 m steps, smoothed)."""
    rc = cost_for(int(math.ceil((wmin + 12.0) / (RG * CELL))))
    cells = []
    straight = [len(w_) > 2 and w_[2] == "S" for w_ in wps]
    for k_, w_ in enumerate(wps):
        c_ = to_cell(w_)
        fixed = k_ in (0, len(wps) - 1) or straight[k_] or (k_ > 0 and straight[k_ - 1])
        cells.append(c_ if fixed else snap(c_, rc))
    path = []
    for k_, (a_, b_) in enumerate(zip(cells, cells[1:])):
        if straight[k_]:
            n_ = max(abs(b_[0] - a_[0]), abs(b_[1] - a_[1])) + 1
            seg = [(int(round(a_[0] + (b_[0] - a_[0]) * t_)), int(round(a_[1] + (b_[1] - a_[1]) * t_))) for t_ in np.linspace(0, 1, n_)]
        else:
            seg = astar(a_, b_, rc)
        path += seg if not path else seg[1:]
    pts = (np.array(path, np.float64)[:, ::-1] + 0.5) * RG * CELL
    pts[0], pts[-1] = np.array(wps[0][:2], float), np.array(wps[-1][:2], float)
    for _ in range(2):
        sm = np.stack([smooth1d(pts[:, 0], 9), smooth1d(pts[:, 1], 9)], 1)
        sm[0], sm[-1] = pts[0], pts[-1]
        pts = sm
    return pts


def free_sides(p, nx_, ny_, w):
    offs = np.arange(0.0, w + 8.0, 1.0)
    out = []
    for sgn in (1.0, -1.0):
        xs_ = p[:, 0, None] + sgn * nx_[:, None] * offs[None, :]
        ys_ = p[:, 1, None] + sgn * ny_[:, None] * offs[None, :]
        hit = rock[np.clip((ys_ / CELL).astype(int), 0, NY - 1), np.clip((xs_ / CELL).astype(int), 0, NX - 1)]
        out.append(np.where(hit.any(1), hit.argmax(1), len(offs)).astype(float))
    return out[0], out[1]


def normals(p):
    dx_, dy_ = np.gradient(p[:, 0]), np.gradient(p[:, 1])
    sp_ = np.hypot(dx_, dy_) + 1e-9
    return -dy_ / sp_, dx_ / sp_


def centre(p, w, fixed=None, iters=12):
    """Like water, the line keeps to the middle of a passage between rock (fixed points and the ends stay)."""
    fx_ = np.zeros(len(p), bool) if fixed is None else fixed
    for _ in range(iters):
        nx_, ny_ = normals(p)
        left, right = free_sides(p, nx_, ny_, w)
        reach = w + 8.0
        push = np.clip((left - right) / 2.0, -1.5, 1.5) * ((left > 0) & (right > 0)) * ((left < reach) | (right < reach))
        push[:5] = push[-5:] = 0.0
        push[fx_] = 0.0
        q_ = p + np.stack([nx_ * push, ny_ * push], 1)
        sm = np.stack([smooth1d(q_[:, 0], 7), smooth1d(q_[:, 1], 7)], 1)
        p = np.where(fx_[:, None], p, sm)
        p[0], p[-1] = q_[0], q_[-1]
    return p


# ---- 3. The lap. Core part (kept exactly as built): wash A west -> east, then the dune loop D's south leg east.
net = world["network"]
A_line = np.array([wc(p_) for p_ in net["A"]["centreline"]])
D_line = np.array([wc(p_) for p_ in net["D"]["centreline"]])
kD = int(np.argmin(np.hypot(D_line[:, 0] - 8300.0, D_line[:, 1] - 1550.0)))
core_part = resample(np.vstack([A_line, D_line[1:kD + 1]]))


def along_line(name, start_xy, end_xy, every=600.0, offset=(0.0, 0.0)):
    """Waypoints every `every` m along a giant canyon's centreline, from the point nearest start to the point
    nearest end."""
    c_ = np.array([wc(p_) for p_ in net["Canyon_" + name]["centreline"]])
    i0 = int(np.argmin(np.hypot(*(c_ - start_xy).T)))
    i1 = int(np.argmin(np.hypot(*(c_ - end_xy).T)))
    seg = c_[i0:i1 + 1] if i1 >= i0 else c_[i1:i0 + 1][::-1]
    s_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(seg, axis=0).T))])
    pick = np.interp(np.arange(0, s_[-1], every), s_, np.arange(len(seg))).astype(int)
    return [tuple(seg[k_] + offset) for k_ in pick[1:]]


# Giant arch on Muerto's floor (the bigger of the two, scale 3.2): the lap threads its opening, which faces along
# the arch's local y (yaw 15 degrees), dead straight for 100 m either side.
arch = [p_ for p_ in json.load(open(f"{WD}/props.json"))["props"] if p_["mesh"] == "SM_Kit_Arch"]
arch = max(arch, key=lambda p_: p_["scale"])
ax_, ay_ = arch["x"] + hx, arch["y"] + hy
ad = (-math.sin(math.radians(arch["yaw"])), math.cos(math.radians(arch["yaw"])))
if ad[1] > 0:  # the lap runs south through it
    ad = (-ad[0], -ad[1])
arch_in = (ax_ - ad[0] * 100.0, ay_ - ad[1] * 100.0, "S")
arch_mid = (ax_, ay_, "S")
arch_out = (ax_ + ad[0] * 100.0, ay_ + ad[1] * 100.0)
A_start = tuple(A_line[0])
# Spider Rock: the lap passes 170 m north of the twin towers (the crevices branch leaves south, past their foot).
tw = np.array(LM["spires"][:2])[:, :2].mean(0)
spider = (float(tw[0]), float(tw[1]) + 170.0)


def chinle(start, end):
    """Chinle westwards between two points, swinging north of Spider Rock when it is on the way."""
    wps = along_line("Chinle", start, end)
    if min(start[0], end[0]) < spider[0] < max(start[0], end[0]):
        wps = [w_ for w_ in wps if abs(w_[0] - spider[0]) > 350.0]
        k_ = next((i for i, w_ in enumerate(wps) if w_[0] < spider[0]), len(wps))
        wps.insert(k_, spider)
    return wps


# Section: (name, waypoints, half width m, narrowest half width m, tightest bend radius m, how it is traced).
# "route": A* between waypoints (steering points snap to open floor), then a high-speed line kept off the walls;
# "spline": a designed line through the waypoints (the hoodoo slalom), left as drawn.
north_loop = [(6080.0, 6950.0), (5900.0, 7060.0), (5350.0, 7020.0), (4950.0, 7180.0), (4600.0, 7450.0), (4250.0, 7350.0),
              (4080.0, 7020.0), (3950.0, 6720.0)]
SECTIONS = [
    ("Hoodoos", [None, (8800.0, 1565.0), (9150.0, 1490.0), (9420.0, 1470.0), (9650.0, 1640.0), (9530.0, 1980.0),
                 (9715.0, 2360.0), (9605.0, 2660.0), (9600.0, 2950.0)], 16.0, 10.0, 90.0, "spline"),
    ("Dunas", [None, (9380.0, 3500.0), (9330.0, 4300.0), (9300.0, 4850.0)], 20.0, 12.0, 200.0, "route"),
    ("Badlands", [None, (9080.0, 5200.0), (9020.0, 5420.0, "S"), (8180.0, 5440.0), (7600.0, 5620.0), (6950.0, 5450.0),
                  (6520.0, 5330.0)], 18.0, 11.0, 150.0, "route"),
    ("North_gap", [None] + along_line("North_gap", (6520, 5330), (6500, 6500), 400.0), 18.0, 11.0, 150.0, "route"),
    ("Fendas_Norte", [None] + chinle((6500, 6500), (6150, 6650)) + north_loop, 18.0, 10.0, 150.0, "route"),
    ("Chinle", [None] + chinle((3950, 6720), (1250, 6600)), 18.0, 11.0, 150.0, "route"),
    ("Muerto", [None] + along_line("Muerto", (1250, 6600), arch_in[:2]) + [arch_in, arch_mid, arch_out] +
     along_line("Muerto", arch_out, (830, 700)), 18.0, 10.0, 150.0, "route"),
    ("Monument", [None, (1250.0, 560.0), (1700.0, 640.0), (1850.0, 1050.0), (1790.0, 1380.0), (1880.0, 1495.0), A_start],
     18.0, 11.0, 120.0, "spline_end"),
]


def spline(ctrl, step=2.0):
    P = np.array([c_[:2] for c_ in ctrl], np.float64)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        m = max(2, int(np.linalg.norm(p2 - p1) / step))
        t = np.linspace(0.0, 1.0, m, endpoint=False)[:, None]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(Q[-2][None])
    return resample(np.vstack(out))


parts = [core_part]
info = [(np.full(len(core_part), 1e-3), np.full(len(core_part), 18.0), np.full(len(core_part), 11.0),
         np.full(len(core_part), -1), np.ones(len(core_part), bool))]
for si, (name, wps, w, wmin, rmin, how) in enumerate(SECTIONS):
    wps = [tuple(parts[-1][-1])] + list(wps[1:])  # sections join end to start
    if how == "spline":
        p = spline(wps)
    elif how == "spline_end":  # routed, but the last 3 waypoints (into the core's wash A) as drawn
        p = np.vstack([resample(route(wps[:-2], wmin)), spline(wps[-3:])[1:]])
        p = resample(p)
    else:
        p = resample(route(wps, wmin))
    n_ = len(p) - 1
    parts.append(p[1:])
    info.append((np.full(n_, rmin), np.full(n_, w), np.full(n_, wmin), np.full(n_, si), np.full(n_, how == "spline")))
    print("SECTION", name, int(len(p)), "m")
lap = np.vstack(parts)
lap_rmin, lap_w, lap_wmin, lap_sec, nocentre = [np.concatenate(c_) for c_ in zip(*info)]
fixed = lap_sec < 0
# Arch: the straight through it stays where it is and narrows to its opening.
d_arch = np.hypot(lap[:, 0] - ax_, lap[:, 1] - ay_)
fixed |= d_arch < 90.0
lap_w = np.where(d_arch < 40.0, 10.0, lap_w)
lap_wmin = np.where(d_arch < 40.0, 9.0, lap_wmin)
# High speed line over the whole lap (the core part and the arch stay put), then keep off the walls.
lap = relax(lap, np.maximum(lap_rmin, 1e-3), fixed=fixed)
lap = np.where((fixed | nocentre)[:, None], lap, centre(lap, 18.0, fixed=fixed | nocentre))
lap = relax(lap, np.maximum(lap_rmin, 1e-3), fixed=fixed, iters=40)
print("LAP", int(len(lap)), "m")


def resample_with(p, *arrays):
    """Back to one point per metre, carrying per-point arrays along (nearest)."""
    s_ = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
    t_ = np.arange(0.0, s_[-1], 1.0)
    q_ = np.stack([np.interp(t_, s_, p[:, 0]), np.interp(t_, s_, p[:, 1])], 1)
    k_ = np.clip(np.searchsorted(s_, t_), 0, len(p) - 1)
    return (q_,) + tuple(arr[k_] for arr in arrays)


lap, lap_w, lap_wmin, lap_sec, fixed, nocentre = resample_with(lap, lap_w, lap_wmin, lap_sec, fixed, nocentre)
core_n = int((lap_sec < 0).sum())  # the lap starts with the core part


def at_lap(x, y):
    return int(np.argmin(np.hypot(lap[:, 0] - x, lap[:, 1] - y)))


# ---- 4. Branches. The first and last waypoints ("@", x, y) are junctions: the lap point nearest (x, y).
BRANCHES = [
    ("B1_Atalho_A_west", [("@", 950, 1700), (1300, 1520), ("@", 1850, 1480)], 16.0, 10.0, 120.0, "surface"),
    ("B2_Fendas", [("@", spider[0] + 250, spider[1] - 60)] + along_line("Monument", (3800, 6500), (3420, 5900), 300.0) +
     [(3000, 5780), (2650, 5760), (2520, 5950), ("@", 2450, 6300)], 10.0, 6.0, 60.0, "surface"),
    ("B3_Tunel_Muerto", [("@", 2300, 6330, "S"), ("@", 1000, 5300)], 16.0, 12.0, 150.0, "surface"),
    ("B4_Escadaria", [("@", 9330, 4520), (foot_up[0], foot_up[1], "S"), (LOOK[0], LOOK[1] - 40.0, "S"),
                      (LOOK[0] - 70.0, STAIR_Y, "S"), foot_dn, ("@", 6700, 5420)], 20.0, 14.0, 60.0, "high"),
    ("B5_Planicie", [("@", 9640, 3000), (9870, 3350), (9860, 3800), ("@", 9350, 4200)], 20.0, 12.0, 200.0, "surface"),
]
branches = {}
for name, wps, w, wmin, rmin, kind in BRANCHES:
    i0, i1 = at_lap(*wps[0][1:3]), at_lap(*wps[-1][1:3])
    wq = [tuple(lap[i0]) + (("S",) if len(wps[0]) > 3 else ())] + [tuple(w_) for w_ in wps[1:-1]] + [tuple(lap[i1])]
    p = resample(route(wq, wmin))
    fx_ = np.zeros(len(p), bool)
    fx_[:2] = fx_[-2:] = True
    p = relax(p, rmin, fixed=fx_)
    if kind != "high":
        p = centre(p, w, fixed=fx_)
        p = relax(p, rmin, fixed=fx_, iters=30)
    p = resample_with(p)[0]
    branches[name] = dict(p=p, w0=w, wmin=wmin, rmin=rmin, kind=kind, leave=i0, rejoin=i1)
    print("BRANCH", name, int(len(p)), "m, leaves at", i0, "rejoins at", i1)


# ---- 5. Tunnels, floor widths, pinches and jumps along every route.
def analyse(p, w, wmin, kind, skip=None):
    n = len(p)
    w = np.broadcast_to(np.asarray(w, float), (n,)).copy()
    wmin = np.broadcast_to(np.asarray(wmin, float), (n,)).copy()
    sk = np.zeros(n, bool) if skip is None else skip
    nx_, ny_ = normals(p)
    bed = smooth1d(bilinear(floor, p[:, 0], p[:, 1]), 201)
    tun = np.zeros(n, bool)
    if kind != "high":
        inside_all = np.ones(n, bool)
        for sgn in (-1.0, 0.0, 1.0):
            off = sgn * (w + 4.0)
            ex, ey = p[:, 0] + nx_ * off, p[:, 1] + ny_ * off
            ii = np.clip((ey / CELL).astype(int), 0, NY - 1)
            jj = np.clip((ex / CELL).astype(int), 0, NX - 1)
            inside_all &= rock[ii, jj] & (H[ii, jj] - bed > 20.0)  # a tunnel needs 20 m of rock overhead
        inside_all &= ~sk
        # The tunnel runs from portal to portal: wherever the centre line is inside rock, once somewhere along that
        # stretch the whole floor is under at least 20 m of it.
        cin = rock[np.clip((p[:, 1] / CELL).astype(int), 0, NY - 1), np.clip((p[:, 0] / CELL).astype(int), 0, NX - 1)] & ~sk
        for s0, s1 in runs(cin, 12):
            if inside_all[s0:s1].any():
                tun[s0:s1] = True
    left, right = free_sides(p, nx_, ny_, float(w.max()))
    wi = np.where((left > 0) & (right > 0), np.minimum(left, right) - 1.5, w)
    wi = np.clip(np.minimum(wi, smooth1d(wi, 31)), wmin, w)
    wi = np.where(tun | sk, w, wi)
    pinch = np.zeros(n, bool)
    if kind != "high":
        for sgn in (-1.0, 1.0):
            ex, ey = p[:, 0] + nx_ * sgn * wi, p[:, 1] + ny_ * sgn * wi
            pinch |= rock[np.clip((ey / CELL).astype(int), 0, NY - 1), np.clip((ex / CELL).astype(int), 0, NX - 1)]
        pinch &= ~tun & ~sk
    return dict(p=p, w=wi, tun=tun, pinch=pinch, bed=bed)


def runs(mask, minlen=1):
    e = np.flatnonzero(np.diff(np.concatenate([[0], mask.astype(int), [0]])))
    return [(int(s0), int(s1)) for s0, s1 in zip(e[::2], e[1::2]) if s1 - s0 >= minlen]


def find_jumps(p, tun, v=100.0, g=20.0):
    """Where the ground falls away from under a craft at ~360 km/h: flight until it meets the ground again (the
    craft's hover pulls it down harder than gravity alone: g 20 m/s2)."""
    z = bilinear(H, p[:, 0], p[:, 1])
    n, out, i = len(z), [], 10
    while i < n - 10:
        if tun[i]:
            i += 1
            continue
        sl = float(np.clip((z[i] - z[i - 10]) / 10.0, -0.3, 0.3))
        if z[i] + sl * 6.0 - z[i + 6] > 2.5:
            j = i + 1
            while j < n:
                t = (j - i) / v
                if z[i] + v * sl * t - 0.5 * g * t * t <= z[j] or tun[j]:
                    break
                j += 1
            if j - i >= 20:
                k_ = min(j, n - 1)
                tt = np.arange(j - i) / v
                out.append({"s": int(i), "at": [round(float(p[i, 0] - hx), 1), round(float(p[i, 1] - hy), 1)],
                            "length_m": int(j - i), "air_s": round((j - i) / v, 2), "drop_m": round(float(z[i] - z[k_]), 1),
                            "height_m": round(float(np.max(z[i] + v * sl * tt - 0.5 * g * tt * tt - z[i:j])), 1)})
            i = j + 1
        else:
            i += 1
    return out


skip_core = np.arange(len(lap)) < core_n
LAPI = analyse(lap, lap_w, lap_wmin, "surface", skip=skip_core)
LAPI["jumps"] = find_jumps(lap, LAPI["tun"] | skip_core)
for name, b in branches.items():
    b.update(analyse(b["p"], b["w0"], b["wmin"], b["kind"]))
    b["jumps"] = find_jumps(b["p"], b["tun"])


def radius_stats(p, skip=None):
    k_ = np.abs(curvature(p))
    if skip is not None:
        k_ = k_[~skip]
    r_ = 1.0 / np.maximum(k_[40:-40], 1e-6)
    return {"min_bend_radius_m": round(float(r_.min()), 1), "share_under_210m_radius": round(float((r_ < 210).mean()), 3)}


def tight_spots(p, skip=None, under=120.0):
    """Where the bends are tighter than `under` m and where rock pinches the floor (for tuning the waypoints)."""
    k_ = np.abs(curvature(p))
    if skip is not None:
        k_ = np.where(skip, 0.0, k_)
    k_[:40] = k_[-40:] = 0.0
    out = []
    for s0, s1 in runs(k_ > 1.0 / under, 3):
        i = s0 + int(np.argmax(k_[s0:s1]))
        out.append((int(p[i, 0]), int(p[i, 1]), int(1.0 / k_[i])))
    return out


core_tunnels = [t_ for t_ in world["tunnels"] if t_["wash"] in ("A", "D")]
print("TIGHT lap", tight_spots(lap, skip_core))
print("PINCH lap", [(int(lap[s0, 0]), int(lap[s0, 1]), s1 - s0) for s0, s1 in runs(LAPI["pinch"], 4)])
for name, b in branches.items():
    print("TIGHT", name, tight_spots(b["p"], under=b["rmin"] * 0.8), "PINCH", [(int(b["p"][s0, 0]), int(b["p"][s0, 1]), s1 - s0) for s0, s1 in runs(b["pinch"], 4)])
print("LAP LENGTH", len(lap), "m  core", core_n, "m")
print("LAP tunnels", [(s1 - s0) for s0, s1 in runs(LAPI["tun"])], "+ core A/D tunnels", len(core_tunnels),
      "pinches", [(s1 - s0) for s0, s1 in runs(LAPI["pinch"], 4)], "jumps", len(LAPI["jumps"]),
      "longest jump", max([j_["length_m"] for j_ in LAPI["jumps"]] or [0]), radius_stats(lap, skip_core),
      "min width", round(float(LAPI["w"][~skip_core].min() * 2), 1))
for name, b in branches.items():
    print(name, len(b["p"]), "m tunnels", [(s1 - s0) for s0, s1 in runs(b["tun"])], "pinches",
          [(s1 - s0) for s0, s1 in runs(b["pinch"], 4)], "jumps", [(j_["length_m"], j_["drop_m"]) for j_ in b["jumps"]],
          radius_stats(b["p"]), "min width", round(float(b["w"].min() * 2), 1))


# ---- 6. Plan (8 m per pixel, north up): relief, the lap (orange), branches, tunnels (black), pinches (red),
# jumps (white dots), the start (white square).
BRANCH_COLS = {"B1_Atalho_A_west": (0.1, 0.85, 0.95), "B2_Fendas": (0.2, 0.35, 1.0), "B3_Tunel_Muerto": (0.9, 0.2, 0.9),
               "B4_Escadaria": (1.0, 1.0, 1.0), "B5_Planicie": (0.2, 0.75, 0.25)}


def plan_image(path, x0=0.0, y0=0.0, x1=None, y1=None, mpp=8.0):
    S = max(1, int(round(mpp / CELL)))
    mpp = S * CELL
    x1, y1 = x1 or SX, y1 or SY
    reg = (slice(int(y0 / CELL), int(y1 / CELL), S), slice(int(x0 / CELL), int(x1 / CELL), S))
    Hs, fl = H[reg], floor[reg]
    rel = Hs - fl
    img = np.zeros(Hs.shape + (3,), np.float32)
    img[:] = (0.86, 0.72, 0.52)
    rk = rock[reg]
    img = np.where(rk[..., None], np.array([0.62, 0.34, 0.18]) * (0.6 + 0.6 * np.clip(rel / 250, 0, 1))[..., None], img)
    img = np.where(sea[reg][..., None] & ~rk[..., None], np.array([0.93, 0.80, 0.45]), img)
    img = np.where((fz["canyon_floor"][reg] > 0.5)[..., None] & ~rk[..., None], np.array([0.62, 0.70, 0.45]), img)
    gy, gx = np.gradient(Hs, mpp)
    img *= (0.55 + 0.45 * np.clip(0.5 + (-gx + gy) * 0.8, 0, 1))[..., None]
    hgt, wid = Hs.shape

    def draw(pts, col, r):
        ix, iy = ((pts[:, 0] - x0) / mpp).astype(int), ((pts[:, 1] - y0) / mpp).astype(int)
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                ok = (ix + dx >= 0) & (ix + dx < wid) & (iy + dy >= 0) & (iy + dy < hgt)
                img[iy[ok] + dy, ix[ok] + dx] = col

    for name, b in branches.items():
        draw(b["p"][::2], BRANCH_COLS[name], 1)
    draw(lap[::2], (1.0, 0.42, 0.0), 2)
    for name, b in list(branches.items()) + [("lap", LAPI)]:
        for s0, s1 in runs(b["tun"]):
            draw(b["p"][s0:s1:2], (0.0, 0.0, 0.0), 2)
        for s0, s1 in runs(b["pinch"], 4):
            draw(b["p"][s0:s1:2], (1.0, 0.0, 0.0), 2)
        for j_ in b["jumps"]:
            draw(b["p"][j_["s"]:j_["s"] + 1], (1.0, 1.0, 1.0), 3)
    for t_ in core_tunnels:
        draw(np.array([wc(t_["portal_in"]), wc(t_["portal_out"])]), (0.0, 0.0, 0.0), 2)
    draw(lap[:1], (1.0, 1.0, 1.0), 6)
    out = bpy.data.images.new("gc_plan", wid, hgt)
    out.pixels.foreach_set(np.concatenate([img, np.ones(Hs.shape + (1,))], -1).astype(np.float32).ravel())
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()


plan_image(f"{WD}/gc_plan.png")
for k_, reg_ in enumerate(os.environ.get("GC_CROPS", "").split(";")):
    if reg_:
        plan_image(f"{WD}/gc_crop{k_}.png", *[float(v_) for v_ in reg_.split(",")], mpp=2.0)
print("PLAN", f"{WD}/gc_plan.png")
if PLAN:
    raise SystemExit
