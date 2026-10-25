# Preview renders of a ship's modules (Docs/MODULOS.md) in the hangar workshop: the stock ship, each module on it,
# the skeleton (x-ray) with the reactor and the engine flames, and a full build. Reads the pieces that ship_modules.py
# writes (<modules_dir>/<ship>_<piece>.fbx and <ship>_modules.json).
# Usage: python3 Scripts/render_modules.py <modules_dir> <ship> <out_dir> [shot ...]
#   shots: stock, wings, armor, cooling, tail, utility, skeleton, flames, build (default: all); and close looks at
#   the body kits: armorclose (the nose), armorside (from the side), armorrear (the tail, from behind and below)
import json
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SRC, SHIP, OUT = argv[0], argv[1].lower(), argv[2]
SHOTS = argv[3:] or ["stock", "wings", "armor", "cooling", "tail", "utility", "skeleton", "flames", "build"]
os.makedirs(OUT, exist_ok=True)
MAN = json.load(open(os.path.join(SRC, "%s_modules.json" % SHIP)))
LIFT = 0.55            # the ship hovers over the turntable
YAW = math.radians(-35)

# Flame styles of the engine modules (the same table drives the game's flames): outer colour, core colour, length (m),
# radius scale, shock diamonds.
FLAMES = {
    "stock": ((1.0, 0.35, 0.08), (1.0, 0.75, 0.4), 0.55, 1.0, 0),
    "sprint": ((0.2, 0.45, 1.0), (0.85, 0.95, 1.0), 1.25, 0.85, 0),          # APEX VK-4: blue jet, white core
    "endurance": ((0.1, 0.8, 1.0), (0.7, 1.0, 1.0), 0.45, 1.1, 0),           # Meridian Longstride: short cyan cone
    "burner": ((1.0, 0.55, 0.12), (1.0, 0.95, 0.7), 1.4, 1.0, 3),            # Vanta HX: scramjet with shock diamonds
    "heavy": ((1.0, 0.25, 0.05), (1.0, 0.6, 0.25), 0.7, 1.35, 0),            # Frontier Ironcore: wide orange
    "relic": ((0.35, 0.6, 1.0), (1.0, 1.0, 1.0), 2.2, 0.45, 0),              # Oryx Relic: thin beam
    "razor": ((0.55, 0.25, 1.0), (0.92, 0.85, 1.0), 1.3, 0.6, 0),           # APEX Razor-S: thin violet jet
    "redline": ((1.0, 0.08, 0.06), (1.0, 0.85, 0.8), 1.6, 0.9, 4),           # REDLINE-X (legendary)
}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def mat(name, col, rough=0.5, metal=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


ROOM = []


def box(c, s, m, rot=0.0):
    bpy.ops.mesh.primitive_cube_add(location=c, rotation=(0, 0, rot))
    o = bpy.context.object
    o.scale = (s[0] / 2, s[1] / 2, s[2] / 2)
    o.data.materials.append(m)
    ROOM.append(o)
    return o


def build_room():
    floor = mat("floor", (0.42, 0.43, 0.45), 0.25)
    line = mat("line", (0.18, 0.18, 0.19), 0.4)
    wall = mat("wall", (0.62, 0.63, 0.65), 0.6)
    rib = mat("rib", (0.36, 0.37, 0.40), 0.4, 0.6)
    dark = mat("dark", (0.08, 0.08, 0.09), 0.35, 0.8)
    plat = mat("plat", (0.16, 0.17, 0.19), 0.3, 0.9)
    steel = mat("steel", (0.5, 0.52, 0.55), 0.3, 0.9)
    ring = mat("ring", (1.0, 0.5, 0.2), 0.3, 0.0, (1.0, 0.45, 0.15), 18.0)
    panel = mat("panel", (1, 1, 1), 0.3, 0.0, (1.0, 0.97, 0.92), 6.0)
    X, Y, H = 32.0, 28.0, 10.0
    box((0, 0, -0.1), (X, Y, 0.2), floor)
    for i in range(-8, 9):
        box((i * 2.0, 0, 0.001), (0.03, Y, 0.002), line)
    for j in range(-7, 8):
        box((0, j * 2.0, 0.001), (X, 0.03, 0.002), line)
    for sx in (-1, 1):
        box((sx * X / 2, 0, H / 2), (0.3, Y, H), wall)
    for sy in (-1, 1):
        box((0, sy * Y / 2, H / 2), (X, 0.3, H), wall)
    box((0, 0, H + 0.1), (X, Y, 0.2), wall)
    for i in range(-7, 8):
        for sy in (-1, 1):
            box((i * 2.2, sy * (Y / 2 - 0.2), H / 2), (0.25, 0.15, H), rib)
    for sy in (-1, 1):
        box((0, sy * (Y / 2 - 0.16), 0.5), (X, 0.05, 1.0), dark)
    for i in range(-3, 4):
        for sy in (-2, -1, 1, 2):
            box((i * 4.4, sy * 3.4, H - 0.05), (3.4, 0.6, 0.08), panel)
    for i in (-1, 0, 1):                       # fewer, bigger lights: the same light, much faster to render
        for sy in (-1, 1):
            bpy.ops.object.light_add(type="AREA", location=(i * 8.8, sy * 5.1, H - 0.2))
            L = bpy.context.object
            L.data.shape, L.data.size, L.data.size_y, L.data.energy = "RECTANGLE", 8.0, 2.0, 900
    bpy.ops.mesh.primitive_cylinder_add(location=(0, 0, 0.12), radius=4.6, depth=0.24, vertices=64)
    bpy.context.object.data.materials.append(plat)
    bpy.ops.mesh.primitive_cylinder_add(location=(0, 0, 0.245), radius=4.5, depth=0.01, vertices=64)
    bpy.context.object.data.materials.append(steel)
    bpy.ops.mesh.primitive_torus_add(location=(0, 0, 0.25), major_radius=4.55, minor_radius=0.04, major_segments=96)
    bpy.context.object.data.materials.append(ring)
    for x, y, e, col in ((7, 7, 600, (1, 0.9, 0.8)), (-7, -6, 450, (0.85, 0.9, 1.0))):
        bpy.ops.object.light_add(type="AREA", location=(x, y, 5.5))
        L = bpy.context.object
        L.data.size, L.data.energy, L.data.color = 3, e, col
        L.rotation_euler = (Vector((0, 0, 1.0)) - L.location).to_track_quat("-Z", "Y").to_euler()
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.3, 0.32, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.15
    sc.world = w


build_room()
ROOT = bpy.data.objects.new("ShipPivot", None)
sc.collection.objects.link(ROOT)
ROOT.location = (0, 0, LIFT)
ROOT.rotation_euler = (0, 0, YAW)
LOADED = {}


def piece(name):
    """The objects of one piece, imported once and parented to the pivot."""
    if name in LOADED:
        return LOADED[name]
    path = os.path.join(SRC, "%s_%s.fbx" % (SHIP, name))
    if not os.path.exists(path):                # e.g. no wing_stock on a ship without wings
        LOADED[name] = []
        return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    objs = [o for o in bpy.data.objects if o not in before]
    for o in objs:
        if o.parent is None:
            o.parent = ROOT
    LOADED[name] = objs
    return objs


def show(names):
    want = set()
    for n in names:
        want.update(piece(n))
    for objs in LOADED.values():
        for o in objs:
            o.hide_render = o not in want


FLAME_OBJS = []


def flame_mat(name, col, strength, sharp):
    """Soft glowing plume: bright on the axis, transparent at the silhouette, fading towards the tail."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out, em, tr, mix = N("ShaderNodeOutputMaterial"), N("ShaderNodeEmission"), N("ShaderNodeBsdfTransparent"), N("ShaderNodeMixShader")
    em.inputs["Color"].default_value = (*col, 1)
    em.inputs["Strength"].default_value = strength
    lw = N("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    centre = N("ShaderNodeMath")
    centre.operation, centre.inputs[0].default_value = "SUBTRACT", 1.0
    L(lw.outputs["Facing"], centre.inputs[1])
    edge = N("ShaderNodeMath")
    edge.operation, edge.inputs[1].default_value = "POWER", sharp
    L(centre.outputs[0], edge.inputs[0])
    tc, sep, fade = N("ShaderNodeTexCoord"), N("ShaderNodeSeparateXYZ"), N("ShaderNodeMapRange")
    L(tc.outputs["Object"], sep.inputs[0])
    L(sep.outputs["Y"], fade.inputs["Value"])
    fade.inputs["From Min"].default_value, fade.inputs["From Max"].default_value = 0.0, 1.0
    fade.inputs["To Min"].default_value, fade.inputs["To Max"].default_value = 1.0, 0.0
    fac = N("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    L(edge.outputs[0], fac.inputs[0])
    L(fade.outputs[0], fac.inputs[1])
    L(fac.outputs[0], mix.inputs["Fac"])
    L(tr.outputs[0], mix.inputs[1])
    L(em.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs["Surface"])
    return m


def blob(loc, scale, m):
    """An ellipsoid centred on the nozzle plane: the front half hides in the engine, the back half is the plume."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0)
    o = bpy.context.object
    o.scale, o.location = scale, loc
    o.data.materials.append(m)
    o.parent = ROOT
    o.visible_shadow = False
    bpy.ops.object.shade_smooth()
    FLAME_OBJS.append(o)
    return o


def flames(style, power=1.0):
    for o in FLAME_OBJS:
        bpy.data.objects.remove(o, do_unlink=True)
    FLAME_OBJS.clear()
    if style is None:
        return
    outer, core, length, rscale, diamonds = FLAMES[style]
    mo = flame_mat("flame_o_" + style, outer, 9.0, 1.6)
    mc = flame_mat("flame_c_" + style, core, 22.0, 2.2)
    md = flame_mat("flame_d_" + style, core, 30.0, 1.4)
    ln = length * power
    for x, y, z, r in MAN["nozzles"]:
        blob((x, y, z), (r * 0.95 * rscale, ln, r * 0.95 * rscale), mo)
        blob((x, y, z), (r * 0.5 * rscale, ln * 0.6, r * 0.5 * rscale), mc)
        for k in range(diamonds):                       # shock diamonds, closer together towards the tail
            yk = y + ln * (0.16 + 0.19 * k)
            blob((x, yk, z), (r * 0.42 * rscale, r * 0.75, r * 0.42 * rscale), md)
        bpy.ops.object.light_add(type="POINT", location=(x, y + 0.25, z))   # the glow on the ship and the floor
        lt = bpy.context.object
        lt.data.color, lt.data.energy, lt.data.shadow_soft_size = outer, 60.0 * power, 0.2
        lt.parent = ROOT
        FLAME_OBJS.append(lt)


cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = int(os.environ.get("MODULE_SAMPLES", "16"))      # fewer for quick looks
sc.cycles.use_denoising = True
sc.cycles.max_bounces, sc.cycles.diffuse_bounces, sc.cycles.glossy_bounces = 4, 2, 2
sc.cycles.transmission_bounces, sc.cycles.transparent_max_bounces = 2, 4
sc.render.resolution_x, sc.render.resolution_y = 1000, 560
sc.render.resolution_percentage = int(os.environ.get("MODULE_RES", "100"))
sc.view_settings.view_transform = "AgX"
sc.view_settings.exposure = -0.3


def ship_frame():
    """How much further the camera stands for a ship longer than the STRIX (6.3 m), from the core's length; and
    where its nose is."""
    ys = [(o.matrix_world @ Vector(c)).y for o in piece("core") if o.type == "MESH" for c in o.bound_box]
    return (max(1.0, (max(ys) - min(ys)) / 6.3), min(ys)) if ys else (1.0, -3.2)


def shot(name, yaw_deg=-80, pitch_deg=14, dist=8.0, target=(0, 0, 1.0), lens=40, ship_yaw=-35):
    """Camera round the target (yaw 0 = the ship's left side, 90 = behind, -90 = in front when ship_yaw is 0)."""
    ROOT.rotation_euler = (0, 0, math.radians(ship_yaw))
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    tgt = Vector(target)
    dist *= FRAME
    cam.location = tgt + Vector((math.cos(yaw) * math.cos(pitch), math.sin(yaw) * math.cos(pitch), math.sin(pitch))) * dist
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (SHIP, name))
    bpy.ops.render.render(write_still=True)
    print("SHOT", sc.render.filepath)


wings = MAN["wings"]
FRAME, NOSE = ship_frame()
if "stock" in SHOTS:
    show(["core", "wing_stock"])
    flames(None)
    shot("stock", yaw_deg=-60, pitch_deg=18, dist=8.6, ship_yaw=0)
if "wings" in SHOTS:
    for w in wings:
        show(["core", "wing_" + w])
        shot("wing_" + w, yaw_deg=55, pitch_deg=36, dist=6.8, target=(0, 0.9, 0.9), ship_yaw=0)
if "armor" in SHOTS:                         # the body kits, and the ship without one to compare
    for k in ("none", "light", "guard", "bulwark", "shell", "aegis"):
        show(["core", "wing_stock"] + ([] if k == "none" else ["armor_" + k]))
        shot("armor_" + k, yaw_deg=-32, pitch_deg=12, dist=7.8, target=(0, -0.5, 0.85), ship_yaw=0)
if "armorclose" in SHOTS:                    # close: the nose blade and the skirt from low at the front
    for k in ("light", "guard", "bulwark", "shell", "aegis"):
        show(["core", "wing_stock", "armor_" + k])
        shot("armorclose_" + k, yaw_deg=-55, pitch_deg=6, dist=3.6, target=(0, NOSE + 1.6, 0.85), ship_yaw=0)
if "armorside" in SHOTS:                     # straight from the side: the kit's lines along the whole ship
    for k in ("light", "bulwark", "aegis"):
        show(["core", "wing_stock", "armor_" + k])
        shot("armorside_" + k, yaw_deg=0, pitch_deg=4, dist=7.6, target=(0, 0, 0.75), ship_yaw=0)
if "armorrear" in SHOTS:                     # close: the skirt's back end and the fins under the tail
    for k in ("bulwark", "aegis"):
        show(["core", "wing_stock", "armor_" + k])
        shot("armorrear_" + k, yaw_deg=25, pitch_deg=4, dist=3.8, target=(0, 0.9, 0.75), ship_yaw=0)
        shot("armorunder_" + k, yaw_deg=60, pitch_deg=-5, dist=4.2, target=(0, 1.8, 0.75), ship_yaw=0)
if "cooling" in SHOTS:
    for k in ("vents", "radiator", "grid"):
        show(["core", "wing_stock", "cooling_" + k])
        shot("cooling_" + k, yaw_deg=25, pitch_deg=42, dist=6.2, target=(0, 0.6, 1.0), ship_yaw=0)
if "tail" in SHOTS:
    for k in ("compact", "twin", "keel"):
        show(["core", "wing_stock", "tail_" + k])
        shot("tail_" + k, yaw_deg=60, pitch_deg=-3 if MAN.get("tail") == "below" else 14, dist=6.2,
             target=(0, 1.8, 0.9), ship_yaw=0)
if "utility" in SHOTS:                       # inside the nose: the x-ray view, the engine idling
    bay = MAN.get("utility_bay", [0, -1.5, 0.5])
    for k in ("mast", "dome", "drone"):
        show(["skeleton", "utility_" + k])
        flames("stock", 0.35)
        shot("utility_" + k, yaw_deg=-48, pitch_deg=30, dist=3.6, target=(bay[0], bay[1] + 0.3, bay[2] + LIFT),
             ship_yaw=0)
    flames(None)
if "skeleton" in SHOTS:
    show(["skeleton"])
    flames("sprint")
    shot("skeleton", yaw_deg=-50, pitch_deg=34, dist=7.2, ship_yaw=0)
    flames(None)
if "flames" in SHOTS:
    show(["core", "wing_stock"])
    for style in FLAMES:
        flames(style)
        shot("flame_" + style, yaw_deg=65, pitch_deg=12, dist=7.0, target=(0, 2.2, 1.0), ship_yaw=0)
    flames(None)
if "build" in SHOTS:
    show(["core", "wing_" + wings[1] if wings else "wing_stock", "armor_guard", "cooling_radiator", "tail_twin"])
    flames("burner")
    shot("build", yaw_deg=-60, pitch_deg=18, dist=8.6, ship_yaw=0)
    flames(None)
print("RENDERS DONE")
