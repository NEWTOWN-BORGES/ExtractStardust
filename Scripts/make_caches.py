# The three caches as 3D crates (player, 2026-11-01: "tem de mostrar os ícones 3D"): STANDARD (graphite, cyan light),
# ADVANCED (navy, blue light, more latches) and ELITE (black lacquer, gold trim and gold light). Our own design: a rugged
# supply crate with a glowing seam under the lid, corner guards, handles and the tier's emblem. Photographed on the same
# turntable light as the consumables and the module cards:
#   SourceArt/UI/Thumbs/cache_<n>.jpg     496 x 316, the card photo (Scripts/import_ui_icons.py -> T_Thumb_cache_<n>)
#   SourceArt/Caches/cache_<n>.fbx        the model (front -Y, up +Z, metres)
#   SourceArt/Caches/preview.jpg          the three side by side
# Run: python3 Scripts/make_caches.py   (or blender -b -P Scripts/make_caches.py)
import math
import os

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
THUMBS = os.path.join(ROOT, "SourceArt", "UI", "Thumbs")
MODELS = os.path.join(ROOT, "SourceArt", "Caches")
os.makedirs(THUMBS, exist_ok=True)
os.makedirs(MODELS, exist_ok=True)
SAMPLES = int(os.environ.get("CACHE_SAMPLES", "48"))

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



GOLD = mat("Gold", "#D9A441", metal=1.0, rough=0.24)

# tier: paint, trim, light, latches per side of the lid, strips on the lid, gold edges
TIERS = [
    dict(paint=mat("PaintStd", "#3B424B", metal=0.35, rough=0.42, coat=0.3), trim=DARK, light=mat("LightStd", "#46DCFF", emit=7.0),
         latches=1, strips=1, edges=False),
    dict(paint=mat("PaintAdv", "#1D3A60", metal=0.35, rough=0.32, coat=0.6), trim=STEEL, light=mat("LightAdv", "#4AA3FF", emit=8.0),
         latches=2, strips=2, edges=False),
    dict(paint=mat("PaintElite", "#141518", metal=0.4, rough=0.22, coat=0.9), trim=mat("Gunmetal", "#33363C", metal=0.9, rough=0.3), light=mat("LightElite", "#FFC23D", emit=9.0),
         latches=2, strips=3, edges=True),
]
CW, CD, CH = 0.46, 0.32, 0.27      # the crate: width (X), depth (Y), height (Z)


def crate(t):
    paint, trim, light = t["paint"], t["trim"], t["light"]
    low = CH * 0.60
    parts = []
    parts.append(box(paint, (CW, CD, low), (0, 0, low / 2), bevel=0.012))                              # the body
    parts.append(box(light, (CW - 0.01, CD - 0.01, 0.008), (0, 0, low + 0.004), bevel=0.0))               # the glowing seam
    lid_h = CH - low - 0.008
    parts.append(box(paint, (CW + 0.014, CD + 0.014, lid_h), (0, 0, low + 0.008 + lid_h / 2), bevel=0.018))  # the lid
    top = CH
    # the raised panel on the lid and its light strips
    parts.append(box(trim, (CW * 0.62, CD * 0.56, 0.012), (0, 0, top + 0.004), bevel=0.004))
    for k in range(t["strips"]):
        y = (k - (t["strips"] - 1) / 2) * 0.034
        parts.append(box(light, (CW * 0.5, 0.008, 0.006), (0, y, top + 0.012), bevel=0.0))
    # corner guards, full height, a little proud of the body
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box(trim, (0.052, 0.052, CH + 0.012), (sx * (CW / 2 - 0.018), sy * (CD / 2 - 0.018), (CH + 0.012) / 2), bevel=0.01))
    # ribs round the body and bolts on the guards (the crate is built, not moulded)
    for z in (low * 0.22, low * 0.78):
        parts.append(box(trim, (CW + 0.004, CD + 0.004, 0.012), (0, 0, z), bevel=0.003))
    for sx in (-1, 1):
        for sy in (-1, 1):
            for z in (0.035, CH - 0.03):
                parts.append(cyl(STEEL, 0.007, 0.006, z, x=sx * (CW / 2 - 0.018), y=sy * (CD / 2 + 0.009), verts=16,
                                 rot=(math.radians(90), 0, 0)))
            parts.append(box(RUBBER, (0.06, 0.06, 0.012), (sx * (CW / 2 - 0.022), sy * (CD / 2 - 0.022), 0.0), bevel=0.004))
    # handles on the sides
    for sx in (-1, 1):
        x = sx * (CW / 2 + 0.014)
        for y in (-0.06, 0.06):
            parts.append(box(trim, (0.022, 0.016, 0.03), (x, y, low * 0.62), bevel=0.004))
        parts.append(box(trim, (0.016, 0.15, 0.016), (x + sx * 0.012, 0, low * 0.62), bevel=0.006))
    # the front: an inset panel, the emblem (a diamond in the light), the latches on the lid's edge
    fy = -CD / 2 - 0.004
    parts.append(box(trim, (CW * 0.5, 0.008, low * 0.62), (0, fy, low * 0.48), bevel=0.004))
    if t["edges"]:
        parts.append(box(GOLD, (CW * 0.5 + 0.012, 0.006, low * 0.62 + 0.012), (0, fy + 0.002, low * 0.48), bevel=0.003))
    em = box(light, (0.05, 0.006, 0.05), (0, fy - 0.006, low * 0.48), bevel=0.0)
    em.rotation_euler = (0, math.radians(45), 0)
    parts.append(em)
    parts.append(box(paint, (0.034, 0.008, 0.034), (0, fy - 0.009, low * 0.48), bevel=0.0, rot=(0, math.radians(45), 0)))
    n = t["latches"]
    for k in range(n):
        x = (k - (n - 1) / 2) * 0.16 if n > 1 else 0.0
        x = x if n > 1 else 0.0
        for side in ((x - 0.11, x + 0.11) if n == 1 else (x,)):
            parts.append(box(STEEL if trim is not STEEL else DARK, (0.05, 0.016, 0.05), (side, fy - 0.006, low + 0.002), bevel=0.006))
            parts.append(box(light, (0.03, 0.004, 0.006), (side, fy - 0.015, low + 0.012), bevel=0.0))
    # gold edges along the lid (the elite)
    if t["edges"]:
        lz = low + 0.008 + lid_h
        for sy in (-1, 1):
            parts.append(box(GOLD, (CW + 0.02, 0.008, 0.008), (0, sy * (CD / 2 + 0.008), lz - 0.004), bevel=0.002))
        for sx in (-1, 1):
            parts.append(box(GOLD, (0.008, CD + 0.02, 0.008), (sx * (CW / 2 + 0.008), 0, lz - 0.004), bevel=0.002))
        parts.append(box(GOLD, (CW + 0.02, 0.008, 0.008), (0, -(CD / 2 + 0.008), 0.006), bevel=0.002))
    return parts


cam = studio()
studio_objs = set(sc.objects)
render_setup(496, 316)
done = []
for idx, t in enumerate(TIERS):
    made = crate(t)
    root = bpy.data.objects.new("cache_%d" % idx, None)
    sc.collection.objects.link(root)
    for o in made:
        o.parent = root
    root.rotation_euler = (0, 0, math.radians(-22))
    target = Vector((0, 0, 0.13))
    loc = Vector((0.66, -1.12, 0.62))
    cam.location = loc
    cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    sc.render.filepath = os.path.join(THUMBS, "cache_%d.jpg" % idx)
    bpy.ops.render.render(write_still=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in made:
        o.select_set(True)
    bpy.context.view_layer.objects.active = made[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(MODELS, "cache_%d.fbx" % idx), use_selection=True, object_types={"MESH"},
                             use_mesh_modifiers=True, apply_unit_scale=True, add_leaf_bones=False)
    done.append((root, made))
    for o in made:
        o.hide_render = True
    print("CACHE", idx, len(made), "parts")

render_setup(1200, 420)
for k, (root, made) in enumerate(done):
    for o in made:
        o.hide_render = False
    root.location.x = (k - 1) * 0.62
for o in studio_objs:
    if o.type == "MESH" and o.name.startswith(("Cylinder", "Torus")):
        o.hide_render = True
target = Vector((0, 0, 0.14))
cam.location = Vector((0.0, -2.9, 1.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = os.path.join(MODELS, "preview.jpg")
bpy.ops.render.render(write_still=True)
print("CACHES DONE")
