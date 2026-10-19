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
# Fallen blocks: boulders on the talus, the bigger the thicker the debris.
boulders = np.maximum(fbm(XM, YM, 6, 2) - 0.15, 0.0) * 3.0 * smoothstep(0.5, 2.5, debris)
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
deb = smoothstep(0.3, 2.5, debris)[..., None] * (1 - steep)
col = col * (1 - deb) + (0.45 * sand + 0.55 * wall * 0.8) * deb
col *= (0.92 + 0.08 * fbm(XM, YM, 24, 2) + 0.04 * fbm(XM, YM, 5, 1))[..., None]
# A touch more saturation: the Utah reds read stronger under a low sun.
grey = col.mean(-1, keepdims=True)
col = np.clip(grey + (col - grey) * 1.25, 0.0, 1.0)

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


# Racer view: on open floor near the middle (the floor cell farthest from any rock), 4 m up, looking along +X.
open_floor = np.where(layer_id == 0, 1.0, 0.0)
for _ in range(25):  # erode the floor mask: what survives longest is farthest from the walls
    shrunk = open_floor * np.roll(open_floor, 1, 0) * np.roll(open_floor, -1, 0) * np.roll(open_floor, 1, 1) * np.roll(open_floor, -1, 1)
    if shrunk[N // 4:3 * N // 4, N // 4:3 * N // 4].sum() == 0:
        break
    open_floor = shrunk
cy, cx = np.argwhere(open_floor[N // 4:3 * N // 4, N // 4:3 * N // 4] > 0)[0] + N // 4
lx, ly = (cx - N / 2) * CELL, (cy - N / 2) * CELL
shots = {"oblique": ((-half * 0.55, -half * 0.55, 160.0), (0.0, 0.0, 10.0), 32),
         "low": ((lx, ly, ground(lx, ly) + 4.0), (lx + 300.0, ly + 40.0, ground(lx, ly) + 12.0), 24)}
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

stats = {"seed": SEED, "cells": N, "cell_m": CELL, "size_m": N * CELL, "z_m": [round(zlo, 1), round(zhi, 1)],
         "heightmap_note": "16-bit PNG spans z_m; Unreal Z scale (%) = (z_max - z_min) * 100 / 512",
         "engine": scene.render.engine}
with open(f"{OUT}/canyon_field.json", "w") as f:
    json.dump(stats, f, indent=1)
print("CANYON FIELD", json.dumps(stats))
