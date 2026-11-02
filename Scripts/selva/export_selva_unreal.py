# Mapa 02 Selva Esmeralda for Unreal (player, 2026-11-02: "importe"): joins the 10 sectors that sculpt_selva.py wrote
# into one world, in the layout export_ab_unreal.py gives the Red Dust Divide, so UEXDesertBuilder::BuildWorldMap builds
# it unchanged (Scripts/selva/import_selva.py imports the kit, the data maps and the materials first). Writes <selva>/ue/:
#  - unreal/world.r16 + world_unreal.json: the sectors' heights in one landscape (north row first, padded to whole
#    landscape components); where two boxes overlap they blend towards their middles, where none covers the land is
#    filled from its neighbours. The JSON also names the landscape material (/Game/Selva/M_Selva) and the water planes;
#  - unreal/world_surface.png: A the forest floor (green) except on steep ground (B, rock and gravel);
#  - unreal/world_track.png: the road and the forks at their floor widths (signed distance, as for the desert);
#  - canyon_field.json: the road as "grand_circuit.lap" (points on the ground, widths) and the forks as its branches;
#  - props.json: the jungle of every sector (meshes SM_Selva_<kind>, yaw and uniform scale).
# Usage: blender -b -P Scripts/selva/export_selva_unreal.py -- C:/rdd/selva     (or any Python with numpy)
import json
import os
import struct
import sys
import zlib

import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ROOT = argv[0] if argv else "C:/rdd/selva"
HERE = os.path.dirname(os.path.abspath(__file__))
UE = os.path.join(ROOT, "ue")
OUT = os.path.join(UE, "unreal")
os.makedirs(OUT, exist_ok=True)
plan = json.load(open(os.path.join(HERE, "selva_plano.json"), encoding="utf-8"))
RES = 3.0
WX, WY = plan["world_m"]
NX, NY = int(round(WX / RES)) + 1, int(round(WY / RES)) + 1
SX, SY = (NX - 1) * RES, (NY - 1) * RES


def write_png(path, data):
    h, w, c = data.shape
    raw = np.clip(np.round(data), 0, 255).astype(np.uint8).reshape(h, w * c).tobytes()
    rows = b"".join(b"\x00" + raw[r * w * c:(r + 1) * w * c] for r in range(h))

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    with open(path, "wb") as f_:
        f_.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def blur(a, r):
    for _ in range(3):
        for axis in (0, 1):
            p = np.pad(a, [((r + 1, r) if ax == axis else (0, 0)) for ax in (0, 1)], mode="edge")
            c = np.cumsum(p, axis=axis, dtype=np.float64)
            hi = np.take(c, np.arange(2 * r + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
            a = ((hi - lo) / (2 * r + 1)).astype(np.float32)
    return a


# ---- 1. heights: every sector into one grid (row 0 = south, as the sectors write them)
acc = np.zeros((NY, NX), np.float64)
wsum = np.zeros((NY, NX), np.float64)
metas, props, water = [], [], []
# Every road point of the ten sectors (x, y, z): the water must never sit over a road (the water tiles below).
ROAD_XYZ = []
for n_ in range(1, 11):
    m_ = json.load(open(os.path.join(ROOT, "S%d" % n_, "selva_S%d.json" % n_), encoding="utf-8"))
    ROAD_XYZ += [(p_[0], p_[1], z_) for p_, z_ in zip(m_["road"]["points"], m_["road"]["z"])]
ROAD_XYZ = np.array(ROAD_XYZ, float)
for n in range(1, 11):
    s = "S%d" % n
    folder = os.path.join(ROOT, s)
    meta = json.load(open(os.path.join(folder, "selva_%s.json" % s), encoding="utf-8"))
    metas.append(meta)
    nx, ny = meta["size"]
    h = np.fromfile(os.path.join(folder, "selva_%s_height.r16" % s), "<u2").reshape(ny, nx).astype(np.float32)
    h = meta["z_min"] + h / 65535.0 * (meta["z_max"] - meta["z_min"])
    x0, y0, x1, y1 = meta["box"]
    c0, r0 = int(round(x0 / RES)), int(round(y0 / RES))
    # weight: 1 inside, falling to 0.05 over the last 90 m to each edge, so overlaps blend
    ii, jj = np.mgrid[0:ny, 0:nx]
    edge = np.minimum(np.minimum(ii, ny - 1 - ii), np.minimum(jj, nx - 1 - jj)) * meta["res_m"]
    w = np.clip(edge / 90.0, 0.05, 1.0)
    ra, rb = max(0, r0), min(NY, r0 + ny)
    ca, cb = max(0, c0), min(NX, c0 + nx)
    if ra >= rb or ca >= cb:
        print("SELVA %s outside the world box" % s)
        continue
    hs, ws = h[ra - r0:rb - r0, ca - c0:cb - c0], w[ra - r0:rb - r0, ca - c0:cb - c0]
    acc[ra:rb, ca:cb] += hs * ws
    wsum[ra:rb, ca:cb] += ws
    if meta["water_m"] > meta["z_min"] + 0.5:
        # Water in tiles of 400 m (2026-11-02). One flat, solid sheet per sector sat up to 10 m over the road where a
        # river descends (S1 at 2.07 km, S3/S4 at 21-22 km, S6, most of S10) and the craft hit it from below: the race
        # test was destroyed at 35 s. A tile that a road of any sector crosses below the sector's level now sits 12 cm
        # over that road (fords and the river roads keep their film of water); a tile with no ground under the water is
        # left out. The water has no collision (EXDesertBuilder): the craft ride on the riverbed, as in Blender.
        wl, T = meta["water_m"], 400.0
        for ty in np.arange(y0, y1, T):
            for tx in np.arange(x0, x1, T):
                bx, by = min(tx + T, x1), min(ty + T, y1)
                on = ((ROAD_XYZ[:, 0] >= tx) & (ROAD_XYZ[:, 0] < bx) & (ROAD_XYZ[:, 1] >= ty) & (ROAD_XYZ[:, 1] < by)
                      & (ROAD_XYZ[:, 2] < wl - 0.12))
                z = float(ROAD_XYZ[on, 2].min()) + 0.12 if on.any() else wl
                rs, cs = int((ty - y0) / meta["res_m"]), int((tx - x0) / meta["res_m"])
                re_, ce = int(np.ceil((by - y0) / meta["res_m"])), int(np.ceil((bx - x0) / meta["res_m"]))
                if not (h[rs:re_, cs:ce] < z).any():
                    continue
                water.append({"x": round((tx + bx) * 0.5 - SX / 2.0, 1), "y": round((ty + by) * 0.5 - SY / 2.0, 1), "z": round(z, 2),
                              "sx": round(bx - tx, 1), "sy": round(by - ty, 1), "sector": s})
    for kind, x, y, z, yaw, scl in json.load(open(os.path.join(folder, "selva_%s_props.json" % s))):
        props.append({"mesh": "SM_Selva_" + kind, "x": round(x - SX / 2.0, 2), "y": round(y - SY / 2.0, 2), "z": z, "yaw": yaw, "scale": scl})
    print("SELVA %s box %s, %d x %d, water %.1f m" % (s, meta["box"], nx, ny, meta["water_m"]))
# Thinning for the frame rate (~1.5 million plants in the ten sectors): every big tree stays; the small ones (shrubs,
# ferns, stones, branches) keep a third; then at most 350 000 in all, at random.
rng_ = np.random.default_rng(7)
SMALL = {"SM_Selva_" + k_ for k_ in ("shrub_a", "shrub_b", "fern", "stone_a", "stone_b", "branch")}
props = [p_ for p_ in props if p_["mesh"] not in SMALL or rng_.random() < 0.34]
if len(props) > 350000:
    keep_ = rng_.random(len(props)) < 350000.0 / len(props)
    props = [p_ for p_, k_ in zip(props, keep_) if k_]
cover = wsum > 0
H = np.where(cover, acc / np.maximum(wsum, 1e-9), 0.0).astype(np.float32)
# land no sector covers: grown in from its neighbours
fill = cover.astype(np.float32)
for r_ in (8, 32, 128):
    if fill.min() > 0.5:
        break
    est = blur(H * fill, r_) / np.maximum(blur(fill, r_), 1e-6)
    H = np.where(fill > 0.5, H, est)
    fill = np.maximum(fill, (blur(fill, r_) > 1e-3).astype(np.float32))
print("SELVA covered %.1f %% of the world" % (cover.mean() * 100.0))
ZLO, ZHI = float(H.min()) - 2.0, float(H.max()) + 2.0


def ground(x, y):
    """Height at world metres (x east, y north from the world's south-west corner), bilinear."""
    fx, fy = np.clip(x / RES, 0, NX - 1.001), np.clip(y / RES, 0, NY - 1.001)
    i0, j0 = np.floor(fy).astype(int), np.floor(fx).astype(int)
    ty, tx = fy - i0, fx - j0
    return (H[i0, j0] * (1 - tx) * (1 - ty) + H[i0, j0 + 1] * tx * (1 - ty) + H[i0 + 1, j0] * (1 - tx) * ty
            + H[i0 + 1, j0 + 1] * tx * ty)


# ---- 2. the road and the forks, on the ground
route = plan["route"]
rp = np.asarray(route["points"], float)
rz = ground(rp[:, 0], rp[:, 1]) + 0.5
lap = [[round(x - SX / 2.0, 2), round(y - SY / 2.0, 2), round(float(z), 2)] for (x, y), z in zip(rp, rz)]
widths = [round(2.0 * float(w_), 1) for w_ in route["half_width"]]
branches = {}
lines = [(rp, np.asarray(route["half_width"], float) * 2.0)]
for fork in plan["forks"]:
    fp = np.asarray(fork.get("points") or [], float)
    if len(fp) < 2:
        continue
    fz = ground(fp[:, 0], fp[:, 1]) + 0.5
    branches[fork["name"]] = {"points": [[round(x - SX / 2.0, 2), round(y - SY / 2.0, 2), round(float(z), 2)] for (x, y), z in zip(fp, fz)]}
    hw = fork.get("half_width", 8.0)
    lines.append((fp, np.full(len(fp), 2.0 * (hw if np.isscalar(hw) else float(np.mean(hw))))))

# ---- 3. landscape heights (north row first, padded to whole components)
QUADS = 126
VX = int(np.ceil((NX - 1) / QUADS)) * QUADS + 1
VY = int(np.ceil((NY - 1) / QUADS)) * QUADS + 1
h16 = np.round((H[::-1] - ZLO) / (ZHI - ZLO) * 65535.0)
np.pad(np.clip(h16, 0, 65535).astype(np.uint16), ((0, VY - NY), (0, VX - NX)), mode="edge").astype("<u2").tofile(os.path.join(OUT, "world.r16"))

# ---- 4. data maps: the forest floor, rock on the steep; the road's signed distance
gy, gx = np.gradient(H, RES)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))[::-1]
steep = np.clip((slope - 18.0) / 20.0, 0.0, 1.0)
surface = np.stack([np.zeros_like(steep), np.zeros_like(steep), steep, 1.0 - steep], -1)
TW = 2048
TH = int(round(TW * NY / NX))
ri = np.clip(((np.arange(TH) + 0.5) * NY / TH).astype(int), 0, NY - 1)
ci = np.clip(((np.arange(TW) + 0.5) * NX / TW).astype(int), 0, NX - 1)
write_png(os.path.join(OUT, "world_surface.png"), surface[ri][:, ci] * 255.0)
KW = 4096
KH = int(round(KW * NY / NX))
px = (NX - 1) * RES / KW
edge = np.full((KH, KW), 32.0, np.float32)
for points, wds in lines:
    for (x, y), wd in zip(points[::2], wds[::2]):
        c = x / px
        r = ((NY - 1) * RES - y) / px
        half = 0.5 * wd
        rad = int((half + 32.0) / px) + 1
        r0_, r1_, c0_, c1_ = max(0, int(r) - rad), min(KH, int(r) + rad + 1), max(0, int(c) - rad), min(KW, int(c) + rad + 1)
        if r0_ >= r1_ or c0_ >= c1_:
            continue
        yy, xx = np.mgrid[r0_:r1_, c0_:c1_]
        edge[r0_:r1_, c0_:c1_] = np.minimum(edge[r0_:r1_, c0_:c1_], np.hypot(yy - r, xx - c) * px - half)
grey = (np.clip((edge + 32.0) / 64.0, 0.0, 1.0) * 255.0)[..., None]
write_png(os.path.join(OUT, "world_track.png"), np.concatenate([grey, grey, grey, np.full_like(grey, 255.0)], -1))

# ---- 5. the JSON the builder reads
x0c = (0.0 - SX / 2.0) * 100.0
y0c = -(((NY - 1) * RES) - SY / 2.0) * 100.0
zscale = (ZHI - ZLO) * 100.0 * 128.0 / 65535.0
json.dump({"size": [VX, VY], "data_size": [NX, NY], "spacing_m": RES, "quads_per_component": QUADS, "origin_cm": [x0c, y0c],
           "z_m": [ZLO, ZHI], "z_scale": zscale, "actor_z_cm": ZLO * 100.0 + 256.0 * zscale,
           "surface_origin_cm": [x0c, y0c], "surface_size_cm": [(NX - 1) * RES * 100.0, (NY - 1) * RES * 100.0],
           "core_tunnel_offset_m": [0.0, 0.0], "world_size_m": [SX, SY],
           "landscape_material": "/Game/Selva/M_Selva.M_Selva", "water_material": "/Game/Selva/M_SelvaWater.M_SelvaWater",
           "water_planes": water}, open(os.path.join(OUT, "world_unreal.json"), "w"), indent=1)
json.dump({"size_x_m": SX, "size_y_m": SY, "cell_m": RES, "z_m": [ZLO, ZHI], "tunnels": [],
           "grand_circuit": {"closed": False, "lap": {"points": lap, "width_m": widths}, "tunnels": [], "branches": branches},
           "expedition": {"name": plan["name"], "length_m": plan["length_m"], "jumps": plan["jumps"]}},
          open(os.path.join(UE, "canyon_field.json"), "w"))
json.dump({"units": "m", "props": props}, open(os.path.join(UE, "props.json"), "w"))
kinds = {}
for p_ in props:
    kinds[p_["mesh"]] = kinds.get(p_["mesh"], 0) + 1
print("SELVA EXPORT %d x %d (landscape %d x %d), z %.0f-%.0f m, road %d points, %d forks, %d water planes, %d props %s"
      % (NX, NY, VX, VY, ZLO, ZHI, len(lap), len(branches), len(water), len(props), kinds))
