# Prepares the generated world (sculpt_expansion.py + sculpt_grand_circuit.py) for Unreal:
#  - world.r16: the final heightmap as raw little-endian uint16, north row first (Unreal's Y runs south, as it is the
#    mirror of the world's y), padded with edge values to a landscape size of whole components (2 x 2 sections of
#    63 quads);
#  - world_surface.png: what the ground is made of (R bare rock on the mesa tops, G deep dune sand, B gravel and
#    talus, A green canyon floor), 8-bit RGBA, north row first;
#  - world_unreal.json: sizes, spacing, height range and where it all sits in Unreal (centimetres).
# Coordinates: the world is SX x SY metres; samples sit every CELL m from the south-west corner; Unreal X = x - SX/2,
# Unreal Y = -(y - SY/2) (the world's y is north, Unreal's Y is mirrored by the FBX/handedness conversion).
# Usage: blender -b -P export_world_unreal.py -- <world folder>   (only numpy is needed)
import json
import os
import struct
import sys
import zlib

import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
WD = argv[0]
OUT = os.path.join(WD, "unreal")
os.makedirs(OUT, exist_ok=True)
world = json.load(open(os.path.join(WD, "canyon_field.json")))
SX, SY, CELL = world["size_x_m"], world["size_y_m"], world["cell_m"]
ZLO, ZHI = world["z_m"]


def read_png16(path):
    """The heightmap writer uses one IDAT chunk and filter 0 on every row, so decoding is a reshape."""
    data = open(path, "rb").read()
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, bits, ctype = struct.unpack(">IIBB", body[:10])
            assert bits == 16 and ctype == 0, "expected a 16-bit greyscale PNG"
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    rows = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, 1 + w * 2)
    assert (rows[:, 0] == 0).all(), "expected filter 0 on every row"
    return rows[:, 1:].copy().view(">u2").reshape(h, w).astype(np.uint16)


def write_png(path, data):
    h, w, c = data.shape
    raw = data.astype(np.uint8).reshape(h, w * c).tobytes()
    rows = b"".join(b"\x00" + raw[r * w * c:(r + 1) * w * c] for r in range(h))

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    with open(path, "wb") as f_:
        f_.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ---- Heights: pad to whole landscape components (126 quads each) with the edge values.
heights = read_png16(os.path.join(WD, "world_height16.png"))  # north row first
NY, NX = heights.shape
QUADS = 126
VX = int(np.ceil((NX - 1) / QUADS)) * QUADS + 1
VY = int(np.ceil((NY - 1) / QUADS)) * QUADS + 1
padded = np.pad(heights, ((0, VY - NY), (0, VX - NX)), mode="edge")
padded.astype("<u2").tofile(os.path.join(OUT, "world.r16"))

# ---- Surface: from the fields the world was built with (rows south first, so flipped to north first).
fz = np.load(os.path.join(WD, "world_fields.npz"))
rocky = np.clip(fz["rocky"].astype(np.float32), 0.0, 1.0)
sea = fz["sea"].astype(np.float32)
debris = np.clip(fz["debris"].astype(np.float32) / 3.0, 0.0, 1.0)
badlands = np.clip(fz["badlands"].astype(np.float32), 0.0, 1.0)
G = fz["G"].astype(np.float32)
meadow = np.clip(fz["canyon_floor"].astype(np.float32), 0.0, 1.0) * smoothstep(0.2, 0.5, G)
surface = np.stack([rocky * 0.85 * (1.0 - sea), sea, np.maximum(debris, badlands * 0.8) * (1.0 - sea), meadow * (1.0 - sea)], -1)[::-1]
TW = 2048
TH = int(round(TW * NY / NX))
ri = np.clip(((np.arange(TH) + 0.5) * NY / TH).astype(int), 0, NY - 1)
ci = np.clip(((np.arange(TW) + 0.5) * NX / TW).astype(int), 0, NX - 1)
write_png(os.path.join(OUT, "world_surface.png"), np.round(surface[ri][:, ci] * 255.0))

# ---- Track: where the race lines run (lap and branches, at their floor widths), so the ground shows the way:
# compacted, darker sand worn by the craft. 1 in the middle of the floor, fading to 0 at its edges; same frame as the
# surface map, at 4096 px across (about 2.4 m per pixel).
KW = 4096
KH = int(round(KW * NY / NX))
px = (NX - 1) * CELL / KW  # metres per pixel
track = np.zeros((KH, KW), np.float32)
gc = world["grand_circuit"]
routes = [(gc["lap"]["points"], gc["lap"]["width_m"])] + [(b["points"], b["width_m"]) for b in gc["branches"].values()]
for points, widths in routes:
    for (x, y, _), wd in zip(points, widths):
        c = (x + SX / 2.0) / px  # world-centre metres -> pixel column / row (north row first)
        r = ((NY - 1) * CELL - (y + SY / 2.0)) / px
        half = 0.5 * wd / px
        rad = int(half) + 2
        r0, r1, c0, c1 = max(0, int(r) - rad), min(KH, int(r) + rad + 1), max(0, int(c) - rad), min(KW, int(c) + rad + 1)
        if r0 >= r1 or c0 >= c1:
            continue
        yy, xx = np.mgrid[r0:r1, c0:c1]
        d = np.hypot(yy - r, xx - c) / max(half, 1.0)
        track[r0:r1, c0:c1] = np.maximum(track[r0:r1, c0:c1], np.clip((1.0 - d) / 0.25, 0.0, 1.0))
grey = np.round(track * 255.0)[..., None]
write_png(os.path.join(OUT, "world_track.png"), np.concatenate([grey, grey, grey, np.full_like(grey, 255.0)], -1))

# ---- Placement in Unreal (cm). Sample (row r, column c) of the padded grid: x = c * CELL, y = (NY - 1 - r) * CELL.
x0 = (0.0 - SX / 2.0) * 100.0
y0 = -(((NY - 1) * CELL) - SY / 2.0) * 100.0
zscale = (ZHI - ZLO) * 100.0 * 128.0 / 65535.0
meta = {
    "size": [VX, VY], "data_size": [NX, NY], "spacing_m": CELL, "quads_per_component": QUADS,
    "origin_cm": [x0, y0], "z_m": [ZLO, ZHI], "z_scale": zscale, "actor_z_cm": ZLO * 100.0 + 256.0 * zscale,
    # The surface texture covers the real (unpadded) world: U along Unreal X, V along Unreal Y (north row first).
    "surface_origin_cm": [x0, y0], "surface_size_cm": [(NX - 1) * CELL * 100.0, (NY - 1) * CELL * 100.0],
    "core_tunnel_offset_m": [499.5, -1501.0], "world_size_m": [SX, SY],
}
json.dump(meta, open(os.path.join(OUT, "world_unreal.json"), "w"), indent=1)
print("EXPORT world", NX, "x", NY, "->", VX, "x", VY, "surface", TW, "x", TH, "z", ZLO, ZHI, "zscale", round(zscale, 3))
