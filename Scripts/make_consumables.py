# The consumables as 3D objects (player, 2026-11-01: "os consumíveis já não são desenhos de linhas 2D: cada um com um
# design em 3D feito no Blender, foto num card como os módulos"). Each one modelled, photographed on the hangar's
# turntable light like the module cards, and exported:
#   SourceArt/UI/Thumbs/con_<id>.jpg      496 x 316, the card photo (Scripts/import_ui_icons.py -> T_Thumb_con_<id>)
#   SourceArt/Consumables/<id>.fbx        the model (front -Y, up +Z, metres)
#   SourceArt/Consumables/preview.jpg     the six side by side
# Run: python3 Scripts/make_consumables.py   (or blender -b -P Scripts/make_consumables.py)
import math
import os

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
THUMBS = os.path.join(ROOT, "SourceArt", "UI", "Thumbs")
MODELS = os.path.join(ROOT, "SourceArt", "Consumables")
os.makedirs(THUMBS, exist_ok=True)
os.makedirs(MODELS, exist_ok=True)
SAMPLES = int(os.environ.get("CON_SAMPLES", "48"))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


MATS = {}


def mat(name, col, metal=0.0, rough=0.4, emit=0.0, alpha=1.0, coat=0.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(col)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = lin(col)
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        b.inputs["Transmission Weight"].default_value = 1.0
    MATS[name] = m
    return m


STEEL = mat("Steel", "#9AA1A8", metal=1.0, rough=0.28)
DARK = mat("DarkMetal", "#2A2D32", metal=0.8, rough=0.45)
RUBBER = mat("Rubber", "#17181A", rough=0.75)
GLASS = mat("Glass", "#CFE6F2", rough=0.04, alpha=0.18)
WHITE = mat("White", "#E8EAEC", rough=0.35, coat=0.4)


def add(op, m, bevel=0.0, smooth=True, **kw):
    op(**kw)
    o = bpy.context.object
    o.data.materials.append(m)
    if bevel:
        bv = o.modifiers.new("b", "BEVEL")
        bv.width, bv.segments, bv.limit_method = bevel, 3, "ANGLE"
    if smooth:
        bpy.ops.object.shade_smooth()
    return o


def cyl(m, r, depth, z, x=0.0, y=0.0, verts=48, bevel=0.0, rot=None):
    o = add(bpy.ops.mesh.primitive_cylinder_add, m, bevel, radius=r, depth=depth, location=(x, y, z), vertices=verts)
    if rot:
        o.rotation_euler = rot
    return o


def box(m, size, loc, bevel=0.01, rot=None):
    o = add(bpy.ops.mesh.primitive_cube_add, m, bevel, smooth=False, size=1.0, location=loc)
    o.scale = size
    if rot:
        o.rotation_euler = rot
    return o


def torus(m, R, r, z, x=0.0, y=0.0, rot=None):
    o = add(bpy.ops.mesh.primitive_torus_add, m, major_radius=R, minor_radius=r, location=(x, y, z), major_segments=64,
            minor_segments=16)
    if rot:
        o.rotation_euler = rot
    return o


def sphere(m, r, loc, scale=(1, 1, 1)):
    o = add(bpy.ops.mesh.primitive_uv_sphere_add, m, radius=r, location=loc, segments=32, ring_count=16)
    o.scale = scale
    return o


# ---------------------------------------------------------------- the six consumables (Docs/MODULOS.md sec. 7)
def coolant():
    """Coolant Cell: a cryo canister, frosted cyan core behind a ribbed glass, steel caps and cooling rings."""
    ice = mat("Coolant_Core", "#5FE3FF", rough=0.2, emit=4.0)
    cyl(ice, 0.075, 0.30, 0.25)
    cyl(GLASS, 0.092, 0.30, 0.25)
    for z in (0.08, 0.42):
        cyl(STEEL, 0.105, 0.06, z, bevel=0.008)
    for z in (0.15, 0.20, 0.25, 0.30, 0.35):
        torus(DARK, 0.098, 0.006, z)
    cyl(DARK, 0.045, 0.05, 0.475, bevel=0.005)
    cyl(ice, 0.02, 0.01, 0.503)
    for a in range(3):                                    # side clamps
        ang = a * 2 * math.pi / 3
        box(DARK, (0.018, 0.03, 0.30), (0.1 * math.cos(ang), 0.1 * math.sin(ang), 0.25), rot=(0, 0, ang))


def foam():
    """Repair Foam: a pressurised foam can with a pistol nozzle, hazard bands and a blob of foam on the tip."""
    orange = mat("Foam_Can", "#E8702A", rough=0.3, coat=0.6)
    stripe = mat("Foam_Stripe", "#111214", rough=0.5)
    cyl(orange, 0.085, 0.34, 0.20, bevel=0.01)
    for z in (0.12, 0.28):
        cyl(stripe, 0.0865, 0.035, z)
    cyl(WHITE, 0.07, 0.05, 0.395, bevel=0.01)
    sphere(WHITE, 0.07, (0, 0, 0.42), (1, 1, 0.45))
    box(DARK, (0.04, 0.16, 0.035), (0, -0.07, 0.46), bevel=0.008)     # trigger head and nozzle
    cyl(STEEL, 0.012, 0.09, 0.465, y=-0.17, rot=(math.pi / 2, 0, 0))
    box(RUBBER, (0.03, 0.03, 0.07), (0, 0.0, 0.41), bevel=0.006)
    goo = mat("Foam_Goo", "#F4F1E8", rough=0.6)
    for k, (dx, dz, r) in enumerate(((0, 0, 0.022), (0.015, 0.012, 0.016), (-0.012, 0.01, 0.015), (0.0, 0.025, 0.013))):
        sphere(goo, r, (dx, -0.225 - k * 0.006, 0.465 + dz))
    cyl(mat("Foam_Gauge", "#7CFF8A", emit=3.0), 0.022, 0.01, 0.30, y=-0.083, rot=(math.pi / 2, 0, 0))


def fuel():
    """Fuel Cell: a hexagonal armoured cell with a carrying handle and an amber window on the fuel inside."""
    yellow = mat("Fuel_Shell", "#F2C230", rough=0.35, coat=0.5)
    amber = mat("Fuel_Liquid", "#FF9A1F", rough=0.2, emit=3.5)
    o = cyl(yellow, 0.13, 0.30, 0.20, verts=6, bevel=0.012)
    o.rotation_euler = (0, 0, math.pi / 6)
    for z in (0.06, 0.34):
        cyl(DARK, 0.135, 0.03, z, verts=6, bevel=0.006).rotation_euler = (0, 0, math.pi / 6)
    box(amber, (0.10, 0.012, 0.18), (0, -0.112, 0.20), bevel=0.004)                    # window
    box(GLASS, (0.11, 0.014, 0.19), (0, -0.114, 0.20), bevel=0.004)
    for x in (-0.07, 0.07):                                                             # handle
        box(DARK, (0.02, 0.03, 0.08), (x, 0, 0.39), bevel=0.005)
    box(RUBBER, (0.17, 0.035, 0.025), (0, 0, 0.44), bevel=0.01)
    cyl(STEEL, 0.03, 0.05, 0.37, x=0.07, y=0.04, bevel=0.004)                         # filler cap
    hazard = mat("Fuel_Hazard", "#111214", rough=0.5)
    for k in range(4):
        box(hazard, (0.02, 0.006, 0.07), (-0.045 + k * 0.03, -0.114, 0.08), rot=(0, 0.6, 0))


def stabilizer():
    """Stabilizer Shot: an auto-injector pen inside two gyroscope rings, green glow in the window."""
    green = mat("Stab_Glow", "#8CFF5A", rough=0.2, emit=4.0)
    body = mat("Stab_Body", "#2E8F52", rough=0.3, coat=0.5)
    pen = cyl(body, 0.035, 0.34, 0.25, bevel=0.006)
    cyl(green, 0.025, 0.14, 0.27)
    cyl(GLASS, 0.037, 0.15, 0.27)
    cyl(STEEL, 0.038, 0.04, 0.42, bevel=0.004)
    cyl(WHITE, 0.03, 0.03, 0.065, bevel=0.004)
    cyl(STEEL, 0.004, 0.04, 0.035)                                                      # needle guard
    pen.name = "pen"
    torus(STEEL, 0.15, 0.008, 0.25, rot=(math.pi / 2, 0, 0.5))
    torus(DARK, 0.13, 0.007, 0.25, rot=(0.0, math.pi / 2, 0.9))
    torus(green, 0.15, 0.0035, 0.25, rot=(math.pi / 2, 0, 0.5))


def surge():
    """Surge Cell: a capacitor bank, three violet coils round a crackling core, copper terminals on top."""
    violet = mat("Surge_Glow", "#B06CFF", rough=0.2, emit=6.0)
    copper = mat("Copper", "#C8743A", metal=1.0, rough=0.3)
    cyl(DARK, 0.12, 0.06, 0.04, bevel=0.01)
    cyl(DARK, 0.12, 0.06, 0.42, bevel=0.01)
    cyl(violet, 0.03, 0.34, 0.23)
    cyl(GLASS, 0.05, 0.34, 0.23)
    for a in range(3):
        ang = a * 2 * math.pi / 3
        x, y = 0.085 * math.cos(ang), 0.085 * math.sin(ang)
        cyl(DARK, 0.022, 0.34, 0.23, x=x, y=y)
        for z in range(9):
            torus(copper, 0.026, 0.004, 0.10 + z * 0.032, x=x, y=y)
    for x in (-0.05, 0.05):
        cyl(copper, 0.016, 0.05, 0.475, x=x, bevel=0.004)
        cyl(violet if x > 0 else STEEL, 0.01, 0.01, 0.502, x=x)
    bolt = mat("Surge_Bolt", "#E3D2FF", emit=10.0)
    pts = [(0.0, -0.06, 0.13), (0.02, -0.07, 0.19), (-0.015, -0.068, 0.24), (0.015, -0.07, 0.30), (0.0, -0.06, 0.35)]
    for p0, p1 in zip(pts, pts[1:]):
        v = Vector(p1) - Vector(p0)
        c = (Vector(p0) + Vector(p1)) / 2
        o = cyl(bolt, 0.0035, v.length, c.z, x=c.x, y=c.y, verts=8)
        o.rotation_euler = v.to_track_quat("Z", "Y").to_euler()


def nanogel():
    """Rapid Nanogel: a glass ampoule of glowing teal gel in a steel cage, a medical cross on the cap."""
    gel = mat("Nanogel_Gel", "#3CF2C8", rough=0.1, emit=3.0)
    cross = mat("Nanogel_Cross", "#FF3B3B", rough=0.3, emit=1.5)
    sphere(gel, 0.075, (0, 0, 0.2), (1, 1, 1.5))
    sphere(GLASS, 0.085, (0, 0, 0.21), (1, 1, 1.55))
    cyl(STEEL, 0.06, 0.05, 0.065, bevel=0.006)
    cyl(STEEL, 0.05, 0.06, 0.36, bevel=0.006)
    cyl(WHITE, 0.055, 0.03, 0.405, bevel=0.006)
    box(cross, (0.05, 0.016, 0.004), (0, 0, 0.422), bevel=0.002)
    box(cross, (0.016, 0.05, 0.004), (0, 0, 0.422), bevel=0.002)
    for a in range(4):                                                                  # the cage
        ang = a * math.pi / 2 + math.pi / 4
        cyl(DARK, 0.007, 0.30, 0.21, x=0.098 * math.cos(ang), y=0.098 * math.sin(ang), verts=12)
    for z in (0.11, 0.31):
        torus(DARK, 0.098, 0.007, z)
    for k in range(5):                                                                  # bubbles in the gel
        sphere(mat("Nanogel_Bubble", "#D8FFF6", emit=2.0), 0.008 - k * 0.0008, (0.02 * math.sin(k * 2.1), -0.03, 0.14 + k * 0.03))


ITEMS = [("coolant", coolant), ("foam", foam), ("fuel", fuel), ("stab", stabilizer), ("surge", surge), ("nanogel", nanogel)]


# ---------------------------------------------------------------- studio: the hangar's turntable light, like the module cards
def studio():
    plat = mat("Platform", "#3A3D42", metal=0.6, rough=0.35)
    ring = mat("PlatformRing", "#5FE3FF", emit=2.5)
    floor = mat("Floor", "#26282C", rough=0.6)
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.001))
    bpy.context.object.data.materials.append(floor)
    cyl(plat, 0.34, 0.03, -0.015 + 0.0, verts=96, bevel=0.004)
    torus(ring, 0.335, 0.004, 0.0)
    for x, y, z, e, col, size in ((1.4, -1.2, 1.6, 120, (1, 0.92, 0.82), 1.2), (-1.5, -0.9, 1.0, 60, (0.8, 0.88, 1.0), 1.5),
                                  (0.2, 1.6, 1.4, 90, (0.9, 0.95, 1.0), 1.0)):
        bpy.ops.object.light_add(type="AREA", location=(x, y, z))
        L = bpy.context.object
        L.data.size, L.data.energy, L.data.color = size, e, col
        L.rotation_euler = (Vector((0, 0, 0.22)) - L.location).to_track_quat("-Z", "Y").to_euler()
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.3, 0.32, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.15
    sc.world = w
    cam_d = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def render_setup(w, h):
    r = sc.render
    r.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
    r.image_settings.file_format = "JPEG"
    r.image_settings.quality = 90
    sc.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    sc.view_settings.exposure = 0.3


cam = studio()
studio_objs = set(sc.objects)
render_setup(496, 316)
done = []
for idx, (key, build) in enumerate(ITEMS):
    before = set(sc.objects)
    build()
    made = [o for o in sc.objects if o not in before]
    for o in made:                                    # each item stands on the turntable
        o.location.z += 0.0
    # the card photo: three-quarter from the front, a little above
    target = Vector((0, 0, 0.27))
    loc = Vector((0.74, -1.16, 0.58))
    cam.location = loc
    cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    sc.render.filepath = os.path.join(THUMBS, "con_%s.jpg" % key)
    bpy.ops.render.render(write_still=True)
    # the model on its own
    bpy.ops.object.select_all(action="DESELECT")
    for o in made:
        o.select_set(True)
    bpy.context.view_layer.objects.active = made[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(MODELS, key + ".fbx"), use_selection=True, object_types={"MESH"},
                             use_mesh_modifiers=True, apply_unit_scale=True, add_leaf_bones=False)
    done.append((key, made))
    for o in made:
        o.hide_render = True
    print("CONSUMABLE", key, len(made), "parts")

# the six side by side
render_setup(1400, 420)
for k, (key, made) in enumerate(done):
    for o in made:
        o.hide_render = False
        o.location.x += (k - 2.5) * 0.42
for o in studio_objs:
    if o.type == "MESH" and o.name.startswith(("Cylinder", "Torus")):
        o.hide_render = True
target = Vector((0, 0, 0.24))
cam.location = Vector((0.0, -3.2, 0.95))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 50
sc.render.filepath = os.path.join(MODELS, "preview.jpg")
bpy.ops.render.render(write_still=True)
print("CONSUMABLES DONE")
