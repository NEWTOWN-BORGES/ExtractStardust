# Prepares the A->B expedition (sculpt_expedition_ab.py) for Unreal, in the same layout the world pipeline uses, so
# import_world.py and UEXDesertBuilder::BuildWorldMap build it unchanged. Writes into <ab folder>/ue/:
#  - unreal/world.r16 (heights, north row first, padded to whole landscape components; the driving floor smoothed:
#    pits filled, bumps down at most 0.5 m, lone sharp samples on steep walls removed), unreal/world_unreal.json;
#  - unreal/world_surface.png: R bare rock on the plateau and mesa tops, G loose sand in the low desert, B gravel and
#    talus on the mid slopes, A green floor (ab_green.png); the shader still decides cliffs by slope;
#  - unreal/world_track.png: the main line and the branches at their floor widths;
#  - canyon_field.json: the main line as "grand_circuit.lap" (points, widths) and the caves as its tunnels;
#  - props.json: ab_props.json (rotation XYZ and per-axis scale kept); tunnels_gc/: the cave roofs (caves/*.fbx).
# Usage: blender -b -P export_ab_unreal.py -- <ab folder>
import json
import os
import shutil
import struct
import sys
import zlib

import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
AB = argv[0]
UE = os.path.join(AB, "ue")
OUT = os.path.join(UE, "unreal")
os.makedirs(OUT, exist_ok=True)
route = json.load(open(os.path.join(AB, "ab_route.json")))
SX, SY = route["size_m"]
CELL = route["cell_m"]
ZLO, ZHI = route["z_m"]


def read_png(path):
    """Writer's format: one IDAT chunk, filter 0 on every row; 16-bit grey or 8-bit grey/RGB."""
    data = open(path, "rb").read()
    pos, idat, w, h, bits, ctype = 8, b"", 0, 0, 8, 0
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, bits, ctype = struct.unpack(">IIBB", body[:10])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    ch = {0: 1, 2: 3, 6: 4}[ctype]
    rows = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, 1 + w * ch * bits // 8)
    assert (rows[:, 0] == 0).all(), "expected filter 0 on every row"
    raw = rows[:, 1:].copy()
    return raw.view(">u2").reshape(h, w).astype(np.uint16) if bits == 16 else raw.reshape(h, w, ch)


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


def route_mask(shape, px, lines, soft=0.25):
    h, w = shape
    m = np.zeros(shape, np.float32)
    for points, widths in lines:
        for (x, y, _), wd in zip(points, widths):
            c = (x + SX / 2.0) / px
            r = ((NY - 1) * CELL - (y + SY / 2.0)) / px
            half = 0.5 * wd / px
            rad = int(half) + 2
            r0, r1, c0, c1 = max(0, int(r) - rad), min(h, int(r) + rad + 1), max(0, int(c) - rad), min(w, int(c) + rad + 1)
            if r0 >= r1 or c0 >= c1:
                continue
            yy, xx = np.mgrid[r0:r1, c0:c1]
            d = np.hypot(yy - r, xx - c) / max(half, 1.0)
            m[r0:r1, c0:c1] = np.maximum(m[r0:r1, c0:c1], np.clip((1.0 - d) / soft, 0.0, 1.0))
    return m


heights = read_png(os.path.join(AB, "ab_height16.png"))  # north row first
NY, NX = heights.shape
main = route["main"]
lines = [(main["points"], [2.0 * v for v in main["half_width_m"]])]
for b in route["branches"].values():
    hw = b["half_width_m"]
    lines.append((b["points"], [2.0 * (hw if np.isscalar(hw) else hw[min(k, len(hw) - 1)]) for k in range(len(b["points"]))]))

# Driving floor smoothed, sharp lone samples on walls removed (as for the world).
H = heights.astype(np.float32)
floor_mask = route_mask((NY, NX), CELL, lines, soft=0.35)
inner = (floor_mask > 0.5).astype(np.float32)
smooth = blur(H * inner, 3) / np.maximum(blur(inner, 3), 1e-3)
half_metre = 0.5 * 65535.0 / (ZHI - ZLO)
H = H + np.maximum(smooth - H, -half_metre) * floor_mask * inner
gy, gx = np.gradient(H * ((ZHI - ZLO) / 65535.0), CELL)
steep = np.clip((np.hypot(gx, gy) - 1.2) / 1.5, 0.0, 1.0) * (1.0 - floor_mask)
H = H + (blur(H, 1) - H) * steep * 0.8
QUADS = 126
VX = int(np.ceil((NX - 1) / QUADS)) * QUADS + 1
VY = int(np.ceil((NY - 1) / QUADS)) * QUADS + 1
np.pad(np.clip(np.round(H), 0, 65535).astype(np.uint16), ((0, VY - NY), (0, VX - NX)), mode="edge").astype("<u2").tofile(os.path.join(OUT, "world.r16"))

# Surface from the expedition's own mask (R slope deg/90, G on a line, B layer) and green layer.
mask = read_png(os.path.join(AB, "ab_mask.png")).astype(np.float32)
green = read_png(os.path.join(AB, "ab_green.png")).astype(np.float32)[..., 0] / 255.0
slope = mask[..., 0] / 255.0 * 90.0
layer = mask[..., 2]
flat = np.clip((25.0 - slope) / 15.0, 0.0, 1.0)
rock_tops = (layer >= 190).astype(np.float32) * flat * 0.8
sand = (layer < 100).astype(np.float32) * flat
gravel = np.clip((slope - 12.0) / 15.0, 0.0, 1.0) * np.clip((45.0 - slope) / 10.0, 0.0, 1.0)
surface = np.stack([rock_tops, sand * (1.0 - green), gravel * (1.0 - green), green], -1)
TW = 2048
TH = int(round(TW * NY / NX))
ri = np.clip(((np.arange(TH) + 0.5) * NY / TH).astype(int), 0, NY - 1)
ci = np.clip(((np.arange(TW) + 0.5) * NX / TW).astype(int), 0, NX - 1)
write_png(os.path.join(OUT, "world_surface.png"), surface[ri][:, ci] * 255.0)
KW = 4096
KH = int(round(KW * NY / NX))
grey = (route_mask((KH, KW), (NX - 1) * CELL / KW, lines) * 255.0)[..., None]
write_png(os.path.join(OUT, "world_track.png"), np.concatenate([grey, grey, grey, np.full_like(grey, 255.0)], -1))

x0 = (0.0 - SX / 2.0) * 100.0
y0 = -(((NY - 1) * CELL) - SY / 2.0) * 100.0
zscale = (ZHI - ZLO) * 100.0 * 128.0 / 65535.0
json.dump({"size": [VX, VY], "data_size": [NX, NY], "spacing_m": CELL, "quads_per_component": QUADS, "origin_cm": [x0, y0],
           "z_m": [ZLO, ZHI], "z_scale": zscale, "actor_z_cm": ZLO * 100.0 + 256.0 * zscale,
           "surface_origin_cm": [x0, y0], "surface_size_cm": [(NX - 1) * CELL * 100.0, (NY - 1) * CELL * 100.0],
           "core_tunnel_offset_m": [0.0, 0.0], "world_size_m": [SX, SY]}, open(os.path.join(OUT, "world_unreal.json"), "w"), indent=1)

# Route, caves and props in the world pipeline's file layout.
caves_dir = os.path.join(AB, "caves")
caves = sorted(f[:-4] for f in os.listdir(caves_dir) if f.endswith(".fbx")) if os.path.isdir(caves_dir) else []
os.makedirs(os.path.join(UE, "tunnels_gc"), exist_ok=True)
for name in caves:
    shutil.copy(os.path.join(caves_dir, name + ".fbx"), os.path.join(UE, "tunnels_gc", name + ".fbx"))
json.dump({"size_x_m": SX, "size_y_m": SY, "cell_m": CELL, "z_m": [ZLO, ZHI], "tunnels": [],
           "grand_circuit": {"closed": False, "lap": {"points": main["points"], "width_m": [2.0 * v for v in main["half_width_m"]]},
                             "tunnels": [{"name": n} for n in caves], "branches": {}},
           "expedition": {k: route[k] for k in ("time_model", "sectors", "jumps", "landmarks", "water", "start_grid") if k in route}},
          open(os.path.join(UE, "canyon_field.json"), "w"))
shutil.copy(os.path.join(AB, "ab_props.json"), os.path.join(UE, "props.json"))
print("EXPORT AB", NX, "x", NY, "->", VX, "x", VY, "caves", len(caves), "track cells", int(inner.sum()))
