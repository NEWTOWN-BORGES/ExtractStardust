# Plan of the race routes over a generated canyon field: top-down render of the terrain with the circuit lap
# (red), the other washes (blue), tunnels (purple), slot cuts (yellow), wash letters and the lap start.
# Usage: blender -b <out_dir>/canyon_field.blend -P render_route_plan.py -- <out_dir>
import bpy
import json
import math
import sys

OUT = sys.argv[sys.argv.index("--") + 1]
with open(f"{OUT}/canyon_field.json") as f:
    stats = json.load(f)
scene = bpy.context.scene
SXp = stats.get("size_x_m", stats["size_m"])
SYp = stats.get("size_y_m", stats["size_m"])
K = max(SXp, SYp) / 2048.0  # line and letter sizes grow with the map
Z = 300.0  # draw height: above all terrain (orthographic top view, so it only orders the layers)


def emit(name, rgb, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])
    return mat


def line(name, pts, width, mat, z):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = width / 2
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p_, (x, y, *_) in zip(sp.points, pts):
        p_.co = (x, y, z, 1.0)
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(mat)
    scene.collection.objects.link(ob)
    return ob


def label(text, x, y, size, mat, z=Z + 20):
    cu = bpy.data.curves.new("T_" + text, "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.5
    ob = bpy.data.objects.new("T_" + text, cu)
    ob.location = (x, y, z)
    ob.data.materials.append(mat)
    scene.collection.objects.link(ob)
    return ob


red, blue = emit("Red", (1.0, 0.05, 0.03), 3.0), emit("Blue", (0.1, 0.45, 1.0), 2.5)
purple, yellow = emit("Purple", (0.6, 0.1, 1.0), 3.0), emit("Yellow", (1.0, 0.85, 0.05), 3.0)
white, black = emit("White", (1, 1, 1), 2.5), emit("Black", (0.0, 0.0, 0.0), 0.0)

net = stats["network"]
for name, wash in net.items():
    line(f"Wash_{name}", wash["centreline"], 9.0 * K, blue, Z)
lap = stats["circuit"]["points"]
line("Lap", lap + lap[:1], 16.0 * K, red, Z + 2)
for t in stats["tunnels"]:  # tunnel stretch: centreline points between the portals (centreline is every 8 m)
    pts = net[t["wash"]]["centreline"][t["start_index"] // 8: (t["start_index"] + t["length_m"]) // 8 + 1]
    if len(pts) >= 2:
        line(t["name"], pts, 22.0 * K, purple, Z + 4)
for c in stats["cuts"]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=18.0 * K, location=(c["at"][0], c["at"][1], Z + 6))
    bpy.context.active_object.data.materials.append(yellow)
for name, wash in net.items():
    pts = wash["centreline"]
    x, y = pts[len(pts) // 2][:2]
    x, y = max(-SXp / 2 + 60 * K, min(SXp / 2 - 60 * K, x)), max(-SYp / 2 + 60 * K, min(SYp / 2 - 60 * K, y))
    bpy.ops.mesh.primitive_cylinder_add(radius=42.0 * K, depth=1.0, location=(x, y, Z + 10))
    bpy.context.active_object.data.materials.append(black)
    label(name, x, y, 60.0 * K, white)
# Lap start: a white bar across the lap at its first point, and the word LARGADA.
x0, y0 = lap[0][:2]
x1, y1 = lap[2][:2]
ang = math.atan2(y1 - y0, x1 - x0)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x0, y0, Z + 8))
bar = bpy.context.active_object
bar.scale = (8.0 * K, 60.0 * K, 1.0)
bar.rotation_euler = (0, 0, ang)
bar.data.materials.append(white)
label("LARGADA", x0, y0 + 70 * K, 40.0 * K, white)
if stats.get("canyon_x_m", SXp) < SXp:  # name the sand sea
    label("MAR DE DUNAS", (stats["canyon_x_m"] + SXp) / 2 - SXp / 2, -SYp * 0.42, 70.0 * K, white)
# Legend, bottom-left.
legend = [("Circuito %.1f km" % (stats["circuit"]["length_m"] / 1000), red), ("Outros washes", blue),
          ("Tuneis (%d)" % len(stats["tunnels"]), purple), ("Cortes (%d)" % len(stats["cuts"]), yellow)]
bpy.ops.mesh.primitive_plane_add(size=1.0, location=(-SXp / 2 + 260 * K, -SYp / 2 + 150 * K, Z + 9))
bg = bpy.context.active_object
bg.scale = (500 * K, 280 * K, 1)
bg.data.materials.append(black)
for k, (text, mat) in enumerate(legend):
    yy = -SYp / 2 + (240 - k * 60) * K
    bpy.ops.mesh.primitive_plane_add(size=36.0 * K, location=(-SXp / 2 + 50 * K, yy, Z + 12))
    bpy.context.active_object.data.materials.append(mat)
    t = label(text, -SXp / 2 + 90 * K, yy, 34.0 * K, white)
    t.data.align_x = "LEFT"

# Overlays cast no shadows on the terrain.
terrain_names = {"CanyonField"}
for ob in scene.objects:
    if ob.type in ("MESH", "CURVE", "FONT") and ob.name not in terrain_names and not ob.name.startswith(("SM_Tunnel", "Prop_")):
        ob.visible_shadow = False
# Top-down orthographic camera, sun high enough for the relief to read.
for ob in scene.objects:
    if ob.type == "LIGHT":
        ob.rotation_euler = (math.radians(40), 0, math.radians(-35))
cam = scene.camera or bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
if cam.name not in scene.objects:
    scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = max(SXp, SYp)
cam.data.clip_end = 5000
cam.location = (0, 0, 1500)
cam.rotation_euler = (0, 0, 0)
if scene.world is None:
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    scene.world = w
if not any(ob.type == "LIGHT" for ob in scene.objects):
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(40), 0, math.radians(-35))
    scene.collection.objects.link(sun)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 12
scene.cycles.use_denoising = True
scene.view_settings.look = "AgX - Punchy"
scene.render.resolution_x = int(1600 * SXp / max(SXp, SYp))
scene.render.resolution_y = int(1600 * SYp / max(SXp, SYp))
scene.render.filepath = f"{OUT}/planta_trajetos.png"
bpy.ops.render.render(write_still=True)
print("PLAN", scene.render.filepath)
