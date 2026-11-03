"""Mapa 02 Selva Esmeralda, the whole map in one picture (20 x 16 km): the ten sectors' heightfields (from
Scripts/selva/sculpt_selva.py, each in its own folder) put together at 20 m, coloured by biome, cliffs as rock, the
rivers in water, the road in orange and the forks by kind (over: yellow, under: cyan, aside: white), A and B marked,
each sector named. In the style of Red Dust Divide's render_world_3d.py, which the player liked.

    python3 Scripts/selva/render_selva_3d.py <folder with S1..S10 sub-folders, or one folder per sector> <out.jpg>
    blender -b -P Scripts/selva/render_selva_3d.py -- <folder> <out.jpg> [size=2400x1350] [samples=32]
"""
import glob
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from scipy import ndimage

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SRC, OUTF = argv[0], argv[1]
OPTS = dict(a.split("=", 1) for a in argv[2:] if "=" in a)
SIZE = tuple(int(v) for v in OPTS.get("size", "2400x1350").split("x"))
HERE = os.path.dirname(os.path.abspath(__file__))
plan = json.load(open(os.path.join(HERE, "selva_plano.json"), encoding="utf-8"))
SX, SY = plan["world_m"]
G = 20.0
NX, NY = int(SX / G) + 1, int(SY / G) + 1
XX, YY = np.meshgrid(np.arange(NX) * G, np.arange(NY) * G)

# ---- 1. the sectors' heightfields, feathered together
acc, wsum, sec_id = np.zeros((NY, NX)), np.zeros((NY, NX)), np.full((NY, NX), -1)
best_w = np.zeros((NY, NX))
for js in sorted(glob.glob(os.path.join(SRC, "**", "selva_S*.json"), recursive=True)):
    if js.endswith("_props.json"):
        continue
    m = json.load(open(js, encoding="utf-8"))
    r16 = js.replace(".json", "_height.r16")
    if not os.path.isfile(r16):
        continue
    nx, ny = m["size"]
    h = np.fromfile(r16, "<u2").reshape(ny, nx).astype(np.float64) / 65535.0 * (m["z_max"] - m["z_min"]) + m["z_min"]
    x0, y0, x1, y1 = m["box"]
    inb = (XX >= x0) & (XX <= x1) & (YY >= y0) & (YY <= y1)
    fx, fy = (XX[inb] - x0) / m["res_m"], (YY[inb] - y0) / m["res_m"]
    hv = ndimage.map_coordinates(h, [fy, fx], order=1, mode="nearest")
    w = np.minimum.reduce([XX[inb] - x0, x1 - XX[inb], YY[inb] - y0, y1 - YY[inb]])
    w = np.clip(w / 400.0, 0.02, 1.0)
    acc[inb] += hv * w
    wsum[inb] += w
    k = int(os.path.basename(js)[7:].split(".")[0])
    wfull = np.zeros((NY, NX))
    wfull[inb] = w
    upd = wfull > best_w
    sec_id[upd] = k
    best_w = np.maximum(best_w, wfull)
    print("SELVA3D sector S%d from %s" % (k, js), flush=True)
H = np.where(wsum > 0, acc / np.maximum(wsum, 1e-9), np.nan)
covered = ~np.isnan(H)
# outside every sector: the nearest sector's ground, blurred into low rolling forest
_d, (iy, ix) = ndimage.distance_transform_edt(~covered, return_indices=True)
H = np.where(covered, H, H[iy, ix])
sec_id = np.where(covered, sec_id, sec_id[iy, ix])
far = ndimage.gaussian_filter(H, 12.0)
blend = np.clip(_d / 25.0, 0, 1)
H = H * (1 - blend) + far * blend

# ---- 2. colours by biome, cliffs as rock
BIOME = {1: (0.10, 0.20, 0.06), 2: (0.12, 0.20, 0.06), 3: (0.10, 0.19, 0.06), 4: (0.10, 0.20, 0.06), 5: (0.10, 0.21, 0.06),
         6: (0.08, 0.17, 0.07), 7: (0.10, 0.19, 0.06), 8: (0.55, 0.45, 0.22), 9: (0.15, 0.20, 0.08), 10: (0.30, 0.36, 0.15)}
ROCK = {2: (0.45, 0.20, 0.10), 3: (0.30, 0.25, 0.23), 7: (0.27, 0.21, 0.19), 9: (0.16, 0.15, 0.15)}
col = np.zeros((NY, NX, 3))
for k, c in BIOME.items():
    col[sec_id == k] = c
gy, gx = np.gradient(H, G)
slope = np.hypot(gx, gy)
rock = np.clip((slope - 0.55) / 0.5, 0, 1)
for k, c in ROCK.items():
    m_ = (sec_id == k)[..., None] * rock[..., None]
    col = col * (1 - m_) + np.asarray(c) * m_
grey = np.clip((slope - 0.9) / 0.6, 0, 1)[..., None]
col = col * (1 - grey) + np.array([0.24, 0.22, 0.20]) * grey
rng = np.random.default_rng(3)
col *= (0.8 + 0.4 * ndimage.gaussian_filter(rng.random((NY, NX)), 2.0))[..., None]

# ---- 3. the scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
cx, cy = SX / 2, SY / 2
VZ = 1.0                                  # true heights (the map is long and low: the cliffs read by their shadows)
me = bpy.data.meshes.new("Selva")
me.vertices.add(NX * NY)
me.vertices.foreach_set("co", np.stack([XX - cx, YY - cy, H * VZ], -1).astype(np.float32).ravel())
idx = np.arange(NX * NY, dtype=np.int32).reshape(NY, NX)
q = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).ravel()
me.loops.add(len(q))
me.loops.foreach_set("vertex_index", q)
me.polygons.add((NX - 1) * (NY - 1))
me.polygons.foreach_set("loop_start", np.arange(0, len(q), 4, dtype=np.int32))
me.update(calc_edges=True)
me.polygons.foreach_set("use_smooth", np.ones((NX - 1) * (NY - 1), bool))
ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
ca.data.foreach_set("color", np.concatenate([col.reshape(-1, 3), np.ones((NX * NY, 1))], 1).astype(np.float32).ravel())


def material(name, rgb=None, attr=None, emit=0.0, rough=0.8, bump=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    if attr:
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_name = attr
        nt.links.new(a.outputs["Color"], bs.inputs["Base Color"])
    else:
        bs.inputs["Base Color"].default_value = (*rgb, 1)
    bs.inputs["Roughness"].default_value = rough
    if emit:
        bs.inputs["Emission Color"].default_value = (*rgb, 1)
        bs.inputs["Emission Strength"].default_value = emit
    if bump:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        vo = nt.nodes.new("ShaderNodeTexVoronoi")
        vo.inputs["Scale"].default_value = bump
        nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = 0.6
        nt.links.new(vo.outputs["Distance"], b.inputs["Height"])
        nt.links.new(b.outputs[0], bs.inputs["Normal"])
    return m


me.materials.append(material("M_Ground", attr="Col", rough=0.9, bump=0.06))
fl = bpy.data.meshes.new("Beyond")               # the forest goes on round the map
B_ = 120000.0
z0 = float(np.percentile(H, 5)) - 2.0
fl.from_pydata([(-B_, -B_, z0), (B_, -B_, z0), (B_, B_, z0), (-B_, B_, z0)], [], [(0, 1, 2, 3)])
fl.materials.append(material("M_Beyond", (0.07, 0.13, 0.05), rough=0.95))
scene.collection.objects.link(bpy.data.objects.new("Beyond", fl))
scene.collection.objects.link(bpy.data.objects.new("Selva", me))


def ground(x, y):
    r = ndimage.map_coordinates(H, [np.atleast_1d(y) / G, np.atleast_1d(x) / G], order=1, mode="nearest") * VZ
    return r if np.ndim(x) else float(r[0])


def ribbon(name, P, width, mat, lift=4.0, step=4):
    P = np.asarray(P, float)[::step]
    if len(P) < 2:
        return
    t = np.gradient(P, axis=0)
    t = t / np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    nrm = np.stack([-t[:, 1], t[:, 0]], 1)
    z = ground(P[:, 0], P[:, 1]) + lift
    L, R_ = P + nrm * width / 2, P - nrm * width / 2
    v = np.concatenate([np.c_[L - (cx, cy), z], np.c_[R_ - (cx, cy), z]])
    n = len(P)
    f = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    rm = bpy.data.meshes.new(name)
    rm.from_pydata(v.tolist(), [], f)
    rm.materials.append(mat)
    scene.collection.objects.link(bpy.data.objects.new(name, rm))


water = material("M_River", (0.05, 0.12, 0.16), rough=0.08)
for rv in plan.get("rivers", []):
    ribbon("Rio", rv["points"], rv["width_m"], water, lift=1.0, step=1)
ribbon("Estrada", plan["route"]["points"], 70.0, material("M_Road", (1.0, 0.35, 0.03), emit=1.2), lift=6.0, step=1)
FCOL = {"CIMA": (1.0, 0.85, 0.1), "BAIXO": (0.1, 0.85, 1.0)}
for f in plan["forks"]:
    c = FCOL.get(f["type"], (0.95, 0.95, 0.95))
    ribbon(f["name"].split()[0], f["points"], 45.0, material("M_" + f["name"].split()[0], c, emit=1.2), lift=7.0, step=1)


def label(text, x, y, size, col=(1, 1, 1), up=260.0):
    cu = bpy.data.curves.new("T", "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    cu.extrude = size * 0.04
    o = bpy.data.objects.new("T_" + text[:8], cu)
    o.location = (x - cx, y - cy, float(ground(x, y)) + up)
    o.rotation_euler = (math.radians(62), 0, 0)
    o.data.materials.append(material("M_T" + text[:6], col, emit=3.0))
    o.visible_shadow = False
    scene.collection.objects.link(o)


R = np.asarray(plan["route"]["points"])
sec = np.asarray(plan["route"]["sector"])
for k, srow in enumerate(plan["sectors"]):
    ii = np.flatnonzero(sec == k)
    p = R[ii[len(ii) // 2]]
    label(srow["name"].upper(), p[0], p[1] + 700, 300.0)
label("A", R[0][0], R[0][1], 520.0, (1.0, 0.85, 0.2), up=500.0)
label("B  EXTRAÇÃO", R[-1][0], R[-1][1], 520.0, (1.0, 0.85, 0.2), up=500.0)

w_ = bpy.data.worlds.new("Sky")
w_.use_nodes = True
sky = w_.node_tree.nodes.new("ShaderNodeTexSky")
for t_name in ("NISHITA", "MULTIPLE_SCATTERING"):
    try:
        sky.sky_type = t_name
        break
    except TypeError:
        pass
sky.sun_elevation, sky.sun_rotation, sky.sun_disc = math.radians(24), math.radians(150), False
w_.node_tree.links.new(sky.outputs["Color"], w_.node_tree.nodes["Background"].inputs[0])
w_.node_tree.nodes["Background"].inputs[1].default_value = 0.16
scene.world = w_
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy, sun.data.angle = 4.0, math.radians(1.0)
sun.rotation_euler = (math.radians(66), 0, math.radians(-30))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.lens = 26
cam.data.clip_end = 100000
scene.collection.objects.link(cam)
scene.camera = cam
eye, tgt = Vector((0.0, -SY * 0.95, SY * 0.62)), Vector((0.0, SY * 0.05, 0.0))
cam.location = eye
cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = int(OPTS.get("samples", 32))
scene.cycles.use_denoising = True
try:
    scene.view_settings.look = "AgX - Punchy"
except TypeError:
    pass
scene.render.resolution_x, scene.render.resolution_y = SIZE
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 90
scene.render.filepath = OUTF
bpy.ops.render.render(write_still=True)
print("SELVA3D written", OUTF)
