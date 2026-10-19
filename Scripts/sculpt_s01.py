# Hero geology for sector S01 (Docs/MAPA_01_RED_DUST_DIVIDE_S01.md), sculpted piece by piece: the Arch Mesa
# (a Navajo mesa with an arch fin standing on its south rim, the opening above the mesa top so it reads against
# the sky), the island butte that splits the route, and broken Kayenta slabs with flat driveable tops.
# Navajo and Wingate are massive sandstones: vertical walls split by a few deep joint clefts into broad rounded
# columns, no horizontal ledges. Exports one FBX per piece and sunlit previews. Plants live in sculpt_plants.py.
# Usage: blender -b -P sculpt_s01.py -- <fbx_output_dir> <preview_prefix>
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
PREVIEW = argv[1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rock_lib import cap, column, displace, finish, remesh, sunlit_preview, texture  # noqa: E402

# Alcoves are off for now: as round scoops they read as "eye sockets" in the game.
WALL = dict(ledge=0.0, grooves=0, groove_depth=0.0, alcoves=0.0)


def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_all(obj):
    active(obj)
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def arch_mesa():
    """Navajo mesa (60 m) with a sandstone fin on its south rim rising to about 100 m, tapering to a rounded crest.
    The mesa walls split into columns at joint clefts. The opening (about 56 x 24 m, weathered outline) starts
    above the mesa top, so from the basin it is a window of sky. The fin faces -Y."""
    body = column("SM_MesaArch", 101, 120, 95, 60, segments=256, bulge=0.18, top_dome=0.03, flare=0.03, rim=0.05,
                  joints=24.0, joint_depth=6.0, joint_width=3.5, crenel=0.04, **WALL)
    cap(body)
    fin = column("ArchFin", 103, 54, 8, 48, bulge=0.1, taper=0.3, flare=0.1, top_dome=0.08, top_rough=0.04, rim=0.15, **WALL)
    cap(fin)
    fin.location = (0.0, -60.0, 52.0)
    active(fin)
    bpy.ops.object.transform_apply(location=True)
    # Opening cutter: an elliptical tube with a weathered, irregular outline (a perfect ellipse looks machined).
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1.0, depth=40.0, location=(0.0, -60.0, 77.0), rotation=(math.radians(90), 0.0, 0.0))
    hole = bpy.context.active_object
    hole.scale = (28.0, 12.0, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    displace(hole, texture("OpeningWear", 'CLOUDS', noise_scale=9.0, noise_depth=2), 5.0)
    apply_all(hole)
    active(fin)
    cut = fin.modifiers.new("Opening", 'BOOLEAN')
    cut.operation = 'DIFFERENCE'
    cut.object = hole
    cut.solver = 'EXACT'
    apply_all(fin)
    bpy.data.objects.remove(hole)
    active(body)
    fin.select_set(True)
    bpy.ops.object.join()
    remesh(body, 0.8)
    return finish(body, 120, 40.0, 1.4, 2.0, 0.25, 0.5, levels=0)


def slab(name, seed, length, width):
    """Broken Kayenta slab: flat top at z = 0 (driveable), rough broken edges, buried 3 m deep."""
    noise.seed_set(seed)
    bm = bmesh.new()
    segments = 72
    rings = []
    for depth, wobble in ((0.0, 1.0), (-0.8, 1.04), (-3.0, 1.1)):
        ring = []
        for s in range(segments):
            a = 2.0 * math.pi * s / segments
            c, si = math.cos(a), math.sin(a)
            # Rounded rectangle (superellipse) with broken, wobbling edges.
            r = 1.0 / (abs(c) ** 6 + abs(si) ** 6) ** (1.0 / 6.0)
            r *= wobble * (1.0 + 0.07 * noise.fractal(Vector((c * 2.0, si * 2.0, seed + depth)), 0.7, 2.0, 3))
            ring.append(bm.verts.new((c * r * length * 0.5, si * r * width * 0.5, depth)))
        rings.append(ring)
    centre = bm.verts.new((0.0, 0.0, 0.0))
    inner = []
    for s in range(segments):
        p = rings[0][s].co
        inner.append(bm.verts.new((p.x * 0.6, p.y * 0.6, 0.02 * noise.noise(Vector((p.x * 0.2, p.y * 0.2, seed))))))
    for s in range(segments):
        n = (s + 1) % segments
        bm.faces.new((centre, inner[s], inner[n]))
        bm.faces.new((inner[s], rings[0][s], rings[0][n], inner[n]))
        for level in range(2):
            bm.faces.new((rings[level][n], rings[level][s], rings[level + 1][s], rings[level + 1][n]))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    active(obj)
    bevel = obj.modifiers.new("Bevel", 'BEVEL')
    bevel.width = 0.25
    bevel.segments = 2
    apply_all(obj)
    return obj


pieces = [arch_mesa(),
          finish(column("SM_IslandButte", 202, 70, 60, 95, segments=192, bulge=0.18, taper=0.08, top_dome=0.1,
                        top_rough=0.04, flare=0.03, rim=0.1, joints=18.0, joint_depth=5.0, joint_width=3.0, crenel=0.05,
                        **WALL),
                 70, 24.0, 1.4, 2.0, 0.25, 0.45),
          slab("SM_Slab_A", 301, 34.0, 26.0), slab("SM_Slab_B", 302, 30.0, 24.0)]

for obj in pieces:
    active(obj)
    path = os.path.join(OUT, obj.name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z',
                             axis_up='Y', mesh_smooth_type='FACE', use_mesh_modifiers=True)
    print("PIECE", obj.name, len(obj.data.polygons), [round(d, 1) for d in obj.dimensions])

# Sunlit previews: the pieces in a row, then the arch mesa and the island butte seen low, as from the race line.
x = 0.0
for obj in pieces:
    obj.location = (x + obj.dimensions.x * 0.5, 0.0, 0.0)
    x += obj.dimensions.x + 40.0
arch, butte = pieces[0], pieces[1]
sunlit_preview(pieces, [
    (PREVIEW + "_row.png", (x * 0.5, -x * 0.8, x * 0.1), (x * 0.5, 0.0, 30.0), 35),
    (PREVIEW + "_arch.png", tuple(arch.location + Vector((-260.0, -520.0, 15.0))), tuple(arch.location + Vector((0.0, -60.0, 55.0))), 45),
    (PREVIEW + "_butte.png", tuple(butte.location + Vector((-120.0, -330.0, 4.0))), tuple(butte.location + Vector((0.0, 0.0, 45.0))), 35),
], (1800, 700))
print("S01 DONE")
