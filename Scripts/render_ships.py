# Scale shots: STRIX racers (V2, ~5.3 m long) placed on a generated map, to read the size of the washes, walls
# and dunes. A pack of five on the lap wash A, seen from above (close and wider), from the chase camera and low
# from the side; and one craft in the air over a dune crest on the dune loop.
# Usage: blender -b <out_dir>/canyon_field.blend -P render_ships.py -- <out_dir> <strix.fbx>
import bpy
import json
import math
import sys
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
OUT, SHIP = args[0], args[1]
with open(f"{OUT}/canyon_field.json") as f:
    stats = json.load(f)
scene = bpy.context.scene

# Terrain heights from the map mesh (rows of the grid, metres from the map centre).
terrain = bpy.data.objects["CanyonField"]
NX, NY = stats["cells"] if isinstance(stats["cells"], list) else (stats["cells"], stats["cells"])
co = np.empty(len(terrain.data.vertices) * 3, np.float32)
terrain.data.vertices.foreach_get("co", co)
co = co.reshape(NY, NX, 3)
CELL = stats["cell_m"]
X0, Y0 = float(co[0, 0, 0]), float(co[0, 0, 1])


def ground(x, y):
    fx, fy = (x - X0) / CELL, (y - Y0) / CELL
    j, i = int(np.clip(fx, 0, NX - 2)), int(np.clip(fy, 0, NY - 2))
    tx, ty = min(max(fx - j, 0.0), 1.0), min(max(fy - i, 0.0), 1.0)
    h = co[i:i + 2, j:j + 2, 2]
    return float((h[0, 0] * (1 - tx) + h[0, 1] * tx) * (1 - ty) + (h[1, 0] * (1 - tx) + h[1, 1] * tx) * ty)


# ---- The ship as a collection, instanced by empties (one import, many craft).
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=SHIP)
parts = [o for o in bpy.data.objects if o not in before]
ship = bpy.data.collections.new("STRIX")
for o in parts:
    for c in list(o.users_collection):
        c.objects.unlink(o)
    ship.objects.link(o)
meshes = [o for o in parts if o.type == "MESH"]
corners = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
hi = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
ship.instance_offset = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)


def centre_of(name):
    o = bpy.data.objects[name]
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(pts, Vector()) / 8


nose = centre_of("Cockpit") - (centre_of("Propulsion_L") + centre_of("Propulsion_R")) / 2
BASE_YAW = math.atan2(nose.y, nose.x)  # heading of the imported model's nose
print("SHIP size", [round(v, 2) for v in (hi - lo)], "nose yaw", round(math.degrees(BASE_YAW), 1))

# Readable livery: pale body, dark structure, glossy canopy, orange harness, glowing engine openings.
LIVERY = {"V2_Body_Grey": ((0.82, 0.83, 0.86), 0.35, 0.35, 0), "V2_Structure_Grey": ((0.18, 0.19, 0.21), 0.5, 0.45, 0),
          "V2_Canopy_Dark": ((0.02, 0.03, 0.04), 0.2, 0.08, 0), "V2_Harness": ((0.85, 0.32, 0.06), 0.0, 0.5, 0),
          "V2_Hover_Grey": ((0.3, 0.31, 0.33), 0.6, 0.4, 0), "V2_Mechanical": ((0.12, 0.12, 0.13), 0.7, 0.4, 0),
          "V2_Socket": ((0.1, 0.1, 0.1), 0.5, 0.5, 0), "V2_Opening_Dark": ((1.0, 0.45, 0.12), 0.0, 0.5, 12.0),
          "V2_CoolantPipe": ((0.2, 0.5, 0.9), 0.3, 0.4, 0)}
for mat in bpy.data.materials:
    if mat.name.split(".")[0] in LIVERY:
        rgb, metal, rough, glow = LIVERY[mat.name.split(".")[0]]
        mat.use_nodes = True
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        bsdf.inputs["Base Color"].default_value = (*rgb, 1)
        bsdf.inputs["Metallic"].default_value = metal
        bsdf.inputs["Roughness"].default_value = rough
        if glow:
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
            bsdf.inputs["Emission Strength"].default_value = glow


def craft(x, y, heading, hover=1.2, pitch=0.0, z=None):
    e = bpy.data.objects.new("Craft", None)
    e.instance_type = "COLLECTION"
    e.instance_collection = ship
    e.location = (x, y, (ground(x, y) + hover) if z is None else z)
    e.rotation_euler = (0.0, -pitch, heading - BASE_YAW)
    scene.collection.objects.link(e)
    return e


def along(name, frac):
    """Point and heading on a route centreline (every 8 m in the JSON) at a fraction of its length."""
    pts = np.array(stats["network"][name]["centreline"], np.float64)
    i = int(np.clip(frac * (len(pts) - 1), 1, len(pts) - 2))
    d = pts[i + 1, :2] - pts[i - 1, :2]
    return pts[i, 0], pts[i, 1], math.atan2(d[1], d[0])


# Pack of five on wash A: leader, two rows behind, staggered.
ax, ay, ah = along("L" if "L" in stats["network"] else "A", 0.08 if "L" in stats["network"] else 0.3)
fwd, side = Vector((math.cos(ah), math.sin(ah), 0)), Vector((-math.sin(ah), math.cos(ah), 0))
for back, lat in ((0, 0), (14, -6), (14, 6), (28, -10), (30, 3)):
    q = Vector((ax, ay, 0)) - fwd * back + side * lat
    craft(q.x, q.y, ah)

# One craft in the air over a dune crest (dune loop, north leg), nose up a little after the launch.
jump = None
if ("D" in stats["network"] or "L" in stats["network"]) and stats.get("canyon_x_m", 1e9) < stats.get("size_x_m", 0):
    pts = np.array(stats["network"]["L" if "L" in stats["network"] else "D"]["centreline"], np.float64)
    leg = [k for k in range(1, len(pts) - 1) if pts[k, 0] > stats["size_x_m"] * 0.38 and abs(pts[k + 1, 0] - pts[k - 1, 0]) < 4]
    if leg:
        best = max(leg, key=lambda k: ground(pts[k, 0], pts[k, 1]))
        d = pts[best + 1, :2] - pts[best - 1, :2]
        jh = math.atan2(d[1], d[0])
        jx, jy = pts[best, 0] + 18 * math.cos(jh), pts[best, 1] + 18 * math.sin(jh)
        jump = (jx, jy, jh, ground(pts[best, 0], pts[best, 1]) + 9.0)
        craft(jx, jy, jh, z=jump[3], pitch=math.radians(8))

# ---- Light and sky as in the generator previews.
SUN_ELEV, SUN_AZ = math.radians(25), math.radians(-35)
world = bpy.data.worlds.new("Sky")
world.use_nodes = True
sky = world.node_tree.nodes.new("ShaderNodeTexSky")
sky.sky_type = "NISHITA"
sky.sun_elevation, sky.sun_rotation = SUN_ELEV, SUN_AZ + math.pi
sky.air_density, sky.dust_density, sky.sun_disc = 1.4, 3.0, False
world.node_tree.links.new(sky.outputs["Color"], world.node_tree.nodes["Background"].inputs[0])
world.node_tree.nodes["Background"].inputs[1].default_value = 0.12
scene.world = world
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy, sun.data.angle, sun.data.color = 3.6, math.radians(1.5), (1.0, 0.82, 0.62)
sun.rotation_euler = (math.pi / 2 - SUN_ELEV, 0, SUN_AZ)
scene.collection.objects.link(sun)
scene.view_settings.look = "AgX - Punchy"
scene.view_settings.exposure = -0.2
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.clip_end = 40000
cam.data.clip_start = 0.1
scene.collection.objects.link(cam)
scene.camera = cam


def shot(name, eye, target, lens=30, ortho=None, res=(1600, 900)):
    cam.data.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        cam.data.ortho_scale = ortho
    cam.data.lens = lens
    cam.location = eye
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = f"{OUT}/nave_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("SHOT", name)


gz = ground(ax, ay)
lead = Vector((ax, ay, gz + 1.2))
shot("topo_perto", (ax - fwd.x * 12, ay - fwd.y * 12, gz + 300), (ax - fwd.x * 12, ay - fwd.y * 12 + 0.01, gz), ortho=90)
shot("topo_largo", (ax, ay, gz + 600), (ax, ay + 0.01, gz), ortho=450)
chase = lead - fwd * 13 + Vector((0, 0, 3.2))
shot("perseguicao", chase, lead + fwd * 60 + Vector((0, 0, 1.0)), lens=24)
low = lead + side * 26 - fwd * 6 + Vector((0, 0, 1.5))
shot("lateral_baixa", low, lead - fwd * 12 + Vector((0, 0, 3.0)), lens=28)
air = lead - fwd * 90 + side * 55 + Vector((0, 0, 40))
shot("aerea_pelotao", air, lead - fwd * 10, lens=32)
if jump:
    jx, jy, jh, jz = jump
    jf, js = Vector((math.cos(jh), math.sin(jh), 0)), Vector((-math.sin(jh), math.cos(jh), 0))
    eye = Vector((jx, jy, 0)) + js * 70 - jf * 25
    shot("salto_duna", (eye.x, eye.y, jz - 2.0), (jx, jy, jz - 4.0), lens=35)
print("SHIPS DONE")
