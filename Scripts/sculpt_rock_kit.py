# Rock kit for dressing the canyon map, after the BlendKit study (Docs/ESTUDO_BLENDKIT_CANYONS.md, section 6):
# loose stones and a broken slab (small), an overhanging flake, a fractured bedded block and a huge boulder
# (giant), an arch, a stacked tower, a capped table rock and a sandstone fin (mega), and dry wood: a fallen log
# and a standing dead snag. Each piece is blocked out from simple volumes, voxel-remeshed into one solid, broken
# along joint planes (rock_lib.fracture), given sandstone beds where the rock is bedded, then weathered
# (rock_lib.finish). Exports one FBX per piece (pivot at ground level) and Cycles previews by size class.
# Usage: blender -b -P sculpt_rock_kit.py -- <fbx_output_dir> <preview_prefix>
import bpy
import bmesh
import math
import os
import random
import sys
from mathutils import Matrix, Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, PREVIEW = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rock_lib import displace, fracture, remesh, texture  # noqa: E402
import rock_lib  # noqa: E402

rock_lib.scene = scene


def blockout(name, parts):
    """One mesh from simple volumes: ("box", centre, size, z-rotation deg, tilt-x deg) or
    ("cyl", centre, bottom radius, top radius, height)."""
    bm = bmesh.new()
    for part in parts:
        if part[0] == "box":
            _, c, s, rz, *rest = part
            rx = rest[0] if rest else 0.0
            m = Matrix.Translation(c) @ Matrix.Rotation(math.radians(rz), 4, "Z") @ Matrix.Rotation(math.radians(rx), 4, "X") \
                @ Matrix.Diagonal((s[0], s[1], s[2], 1.0))
            bmesh.ops.create_cube(bm, size=1.0, matrix=m)
        else:
            _, c, r1, r2, h = part
            bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=28, radius1=r1, radius2=r2, depth=h,
                                  matrix=Matrix.Translation(c))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    scene.collection.objects.link(obj)
    return obj


def beds(obj, period, depth, seed, sharp=4.0):
    """Sandstone beds: each bed recedes towards its base, so the side walls step in horizontal ledges.
    Only walls are affected (not tops). Bed thickness wanders, each bed has its own lip depth and whole stretches
    of wall stay massive (no lips), so the rock never reads as a stack of equal plates."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    for v in bm.verts:
        wall = max(0.0, 1.0 - abs(v.normal.z) * 1.4)
        t = v.co.z / period + 0.35 * noise.noise(v.co * 0.12 + off) + 0.25 * math.sin(v.co.z * 0.37 + seed)
        bed = math.floor(t)
        lip = 0.35 + 0.65 * (0.5 + 0.5 * noise.noise(Vector((bed * 1.7, seed * 0.3, 0.0))))
        massive = max(0.0, min(1.0, 0.5 + 1.6 * noise.noise(v.co * 0.07 + off * 2.0)))
        f = (t - bed) ** sharp
        v.co -= v.normal * depth * f * wall * lip * massive
    bm.to_mesh(obj.data)
    bm.free()


def weather(obj, size, ratio, detail=1.0, joint_stretch=2.5):
    """Erosion, joint cracks and grit scaled to the piece, then decimate and box-project UVs."""
    erosion = texture(obj.name + "Erosion", "CLOUDS", noise_scale=size * 0.3, noise_depth=3)
    joints = texture(obj.name + "Joints", "VORONOI", noise_scale=size * 0.35, distance_metric="DISTANCE",
                     weight_1=-1.0, weight_2=1.0, noise_intensity=1.0)
    grit = texture(obj.name + "Grit", "STUCCI", noise_scale=max(0.3, size * 0.06), turbulence=3.0)
    displace(obj, erosion, 0.05 * size * detail)
    displace(obj, joints, 0.03 * size * detail, stretch=(1.0, 1.0, joint_stretch), mid=0.0)
    displace(obj, grit, 0.006 * size * detail)
    dec = obj.modifiers.new("Dec", "DECIMATE")
    dec.ratio = ratio
    apply_all(obj)
    uv(obj, size * 0.25)


def apply_all(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)


def uv(obj, cube):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=cube)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)


def ground(obj, embed):
    """Pivot at ground level: lowest point at -embed (buried a little so it sits in the sand)."""
    zmin = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
    for v in obj.data.vertices:
        v.co.z -= zmin + embed
    return obj


def rock(name, seed, parts, size, voxel, walls, chamfers, depth, ratio, bed=None, detail=1.0, embed=0.05, rounding=0.0):
    """rounding: how far the blockout is pulled towards a sphere first (worn, rolled blocks), before the fresh
    joint faces are cut."""
    obj = blockout(name, parts)
    remesh(obj, voxel)
    if rounding > 0.0:
        cast = obj.modifiers.new("Cast", "CAST")
        cast.factor = rounding
        lumps = texture(name + "Lumps", "CLOUDS", noise_scale=size * 0.4, noise_depth=2)
        displace(obj, lumps, 0.08 * size)
        apply_all(obj)
        remesh(obj, voxel)
    fracture(obj, seed, walls, chamfers, depth=depth, tilt=(-4.0, 10.0), chamfer_depth=(depth[0] * 0.5, depth[1] * 0.6))
    remesh(obj, voxel)
    if bed:
        beds(obj, bed[0], bed[1], seed)
    weather(obj, size, ratio, detail)
    return ground(obj, size * embed)


def wood(name, seed, skeleton, radii, size, ratio):
    """Dry wood from a skeleton of points and edges with a radius per point (Skin modifier), smoothed, then split
    along the grain (Voronoi stretched along the branches) and cracked."""
    me = bpy.data.meshes.new(name)
    pts = [p for p, _ in skeleton]
    edges = [(i, parent) for i, (_, parent) in enumerate(skeleton) if parent is not None]
    me.from_pydata(pts, edges, [])
    obj = bpy.data.objects.new(name, me)
    scene.collection.objects.link(obj)
    obj.modifiers.new("Skin", "SKIN")
    for i, r in enumerate(radii):
        obj.data.skin_vertices[0].data[i].radius = (r, r)
    obj.data.skin_vertices[0].data[0].use_root = True
    sub = obj.modifiers.new("Sub", "SUBSURF")
    sub.levels = 2
    apply_all(obj)
    grain = texture(name + "Grain", "VORONOI", noise_scale=0.12, distance_metric="DISTANCE", weight_1=-1.0, weight_2=1.0,
                    noise_intensity=1.0)
    knots = texture(name + "Knots", "CLOUDS", noise_scale=0.6, noise_depth=2)
    displace(obj, grain, 0.05, stretch=(1.0, 1.0, 6.0), mid=0.0)
    displace(obj, knots, 0.06)
    dec = obj.modifiers.new("Dec", "DECIMATE")
    dec.ratio = ratio
    apply_all(obj)
    uv(obj, 0.5)
    return ground(obj, 0.05)


def branch(skel, rad, start, direction, length, r0, r1, steps, rng, bend=0.25):
    """Adds a tapering, wandering branch to a skeleton; returns the index of its tip."""
    parent = start
    p = Vector(skel[start][0])
    d = Vector(direction).normalized()
    for k in range(1, steps + 1):
        d = (d + Vector((rng.uniform(-bend, bend), rng.uniform(-bend, bend), rng.uniform(-bend * 0.5, bend * 0.5)))).normalized()
        p = p + d * (length / steps)
        skel.append((tuple(p), parent))
        rad.append(r0 + (r1 - r0) * k / steps)
        parent = len(skel) - 1
    return parent


pieces = {"small": [], "giant": [], "mega": [], "wood": []}

# ---- Small: loose stones (0.4-1.4 m) and a broken slab in two beds ("Rocks", "Big Flat Rock").
# Stones are broken blocks (fresh joint faces, chipped edges), not pebbles: fractured boxes, lightly weathered.
for k, (r, flat) in enumerate(((0.4, 0.7), (0.65, 0.55), (0.95, 0.6), (1.4, 0.5))):
    sx, sy, sz = 2.0 * r * (1.0 + 0.15 * k % 2), 1.6 * r, 2.0 * r * flat
    pieces["small"].append(rock(f"SM_Kit_Stone_{k + 1}", 11 + k * 7, [("box", (0, 0, sz / 2), (sx, sy, sz), 17 * k, 6 * k)],
                                2.0 * r, max(0.03, r * 0.06), 6, 4, (0.08 * r, 0.35 * r), 0.5, detail=1.0, embed=0.12, rounding=0.45))
pieces["small"].append(rock("SM_Kit_FlatSlab", 21, [
    ("box", (0, 0, 0.3), (3.9, 2.7, 0.6), 0),
    ("box", (0.5, 0.3, 0.85), (2.6, 2.0, 0.5), 12, 3)], 4.0, 0.06, 6, 2, (0.2, 0.6), 0.5, bed=(0.28, 0.06)))

# ---- Giant: overhanging flake ("Rock Cliff Overhang"), fractured bedded block ("Rugged Coastal Rock"),
# huge boulder.
pieces["giant"].append(rock("SM_Kit_Overhang", 31, [
    ("box", (0, 0, 1.6), (3.4, 2.4, 3.2), 0),
    ("box", (0.5, 0.4, 4.3), (3.8, 2.6, 2.6), 6, -8)], 6.0, 0.08, 7, 3, (0.3, 1.0), 0.45, bed=(0.9, 0.12), detail=1.3))
pieces["giant"].append(rock("SM_Kit_FracturedBlock", 37, [
    ("box", (0, 0, 2.4), (5.0, 5.8, 4.8), 0),
    ("box", (1.2, -1.0, 4.9), (2.4, 2.8, 1.4), 18)], 6.0, 0.08, 9, 4, (0.4, 1.4), 0.45, bed=(0.7, 0.18), detail=1.3, rounding=0.15))
pieces["giant"].append(rock("SM_Kit_Boulder_Giant", 41, [
    ("box", (0, 0, 2.6), (8.5, 6.5, 5.2), 0, 4),
    ("box", (1.5, 0.5, 4.6), (5.0, 4.4, 2.2), 25)], 9.0, 0.12, 8, 6, (0.6, 2.0), 0.45, detail=1.3, embed=0.08, rounding=0.5))

# ---- Mega: arch, stacked tower, capped table rock, fin (paid BlendKit arches/formation as inspiration).
pieces["mega"].append(rock("SM_Kit_Arch", 51, [
    ("cyl", (-6.0, 0, 4.5), 2.6, 2.0, 9.0),
    ("cyl", (6.2, 0.3, 4.2), 2.4, 1.9, 8.4),
    ("box", (0, 0.1, 10.2), (17.0, 3.8, 3.4), 0),
    ("box", (-6.5, 0, 12.4), (3.6, 3.4, 1.6), 8)], 17.0, 0.22, 8, 3, (0.5, 2.0), 0.4, bed=(1.2, 0.35), detail=1.4))
pieces["mega"].append(rock("SM_Kit_StackedTower", 57, [
    ("box", (0, 0, 1.6), (7.0, 9.5, 3.2), 0),
    ("box", (0.4, -0.3, 4.6), (6.2, 8.4, 2.8), 7),
    ("box", (-0.3, 0.4, 7.3), (5.4, 7.2, 2.6), -6),
    ("box", (0.2, 0, 9.8), (4.6, 5.8, 2.4), 10),
    ("box", (0, 0.3, 12.0), (3.4, 4.2, 2.0), -4)], 13.0, 0.18, 10, 3, (0.4, 1.6), 0.4, bed=(0.8, 0.3), detail=1.4))
pieces["mega"].append(rock("SM_Kit_TableRock", 63, [
    ("cyl", (0, 0, 2.8), 4.2, 3.2, 5.6),
    ("box", (0, 0, 6.3), (12.8, 6.4, 1.8), 4)], 13.0, 0.18, 9, 4, (0.4, 1.8), 0.4, bed=(1.0, 0.25), detail=1.4))
pieces["mega"].append(rock("SM_Kit_Fin", 71, [
    ("box", (0, 0, 6.0), (16.0, 3.2, 12.0), 0),
    ("box", (-3.5, 0.2, 12.8), (7.0, 2.6, 2.2), 0)], 16.0, 0.2, 8, 4, (0.5, 2.2), 0.4, bed=(1.4, 0.3), detail=1.4))

# ---- Dry wood: fallen log with branch stubs and root flare; standing dead snag with bare twisting branches.
rng = random.Random(81)
skel, rad = [((-3.6, 0.0, 0.45), None)], [0.55]
tip = branch(skel, rad, 0, (1, 0.05, 0.02), 7.2, 0.42, 0.18, 10, rng, bend=0.06)
for at, d, ln in ((3, (0.3, 1, 0.5), 1.1), (6, (0.2, -1, 0.7), 0.8), (8, (0.6, 0.8, 0.4), 1.4)):
    branch(skel, rad, at, d, ln, rad[at] * 0.45, 0.04, 3, rng)
for d in ((-0.4, 1, -0.3), (-0.5, -1, -0.2), (-0.6, 0.2, -0.8)):
    branch(skel, rad, 0, d, 0.9, 0.3, 0.08, 2, rng, bend=0.1)  # root flare
pieces["wood"].append(wood("SM_Kit_DeadLog", 81, skel, rad, 7.0, 0.35))
rng = random.Random(87)
skel, rad = [((0, 0, 0), None)], [0.32]
trunk = branch(skel, rad, 0, (0.05, 0.02, 1), 4.6, 0.26, 0.09, 8, rng, bend=0.12)
for at, d in ((4, (1, 0.3, 0.9)), (6, (-0.8, 0.5, 1)), (7, (0.2, -1, 0.8)), (5, (-0.4, -0.9, 0.5))):
    end = branch(skel, rad, at, d, rng.uniform(1.4, 2.2), rad[at] * 0.6, 0.03, 4, rng, bend=0.3)
for d in ((1, 0, -0.4), (-0.7, 0.7, -0.4), (-0.3, -1, -0.4)):
    branch(skel, rad, 0, d, 0.8, 0.22, 0.06, 2, rng, bend=0.1)
pieces["wood"].append(wood("SM_Kit_DeadSnag", 87, skel, rad, 5.0, 0.4))

# ---- Export, one FBX per piece.
for group in pieces.values():
    for obj in group:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, obj.name + ".fbx"), use_selection=True, apply_unit_scale=True,
                                 bake_space_transform=True, object_types={"MESH"})
        print("PIECE", obj.name, len(obj.data.polygons), [round(d, 1) for d in obj.dimensions])

# ---- Previews (Cycles on the CPU): sandstone with beds by height, grey-brown dry wood, sand ground, low sun.
def sandstone(name, base, dark):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    coords = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 0.45
    wave.inputs["Distortion"].default_value = 4.0
    wave.inputs["Detail"].default_value = 3.0
    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 3.0
    grain.inputs["Detail"].default_value = 10.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*dark, 1)
    mix.inputs["B"].default_value = (*base, 1)
    ramp = nt.nodes.new("ShaderNodeMath")
    ramp.operation = "MULTIPLY_ADD"
    ramp.inputs[1].default_value = 0.18
    nt.links.new(coords.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(coords.outputs["Object"], grain.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs[0])
    nt.links.new(grain.outputs["Fac"], ramp.inputs[2])
    nt.links.new(ramp.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.92
    return mat


stone = sandstone("M_KitSandstone", (0.62, 0.27, 0.11), (0.36, 0.12, 0.05))
drywood = sandstone("M_KitDryWood", (0.42, 0.36, 0.30), (0.20, 0.16, 0.13))
for name, group in pieces.items():
    for obj in group:
        obj.data.materials.clear()
        obj.data.materials.append(drywood if name == "wood" else stone)

world = bpy.data.worlds.new("Sky")
world.use_nodes = True
sky = world.node_tree.nodes.new("ShaderNodeTexSky")
sky.sky_type = "NISHITA"
sky.sun_elevation = math.radians(28)
sky.sun_rotation = math.radians(-35) + math.pi
sky.dust_density = 2.5
sky.sun_disc = False
world.node_tree.links.new(sky.outputs["Color"], world.node_tree.nodes["Background"].inputs[0])
world.node_tree.nodes["Background"].inputs[1].default_value = 0.12
scene.world = world
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy = 3.6
sun.data.color = (1.0, 0.84, 0.66)
sun.rotation_euler = (math.radians(62), 0, math.radians(-35))
scene.collection.objects.link(sun)
bpy.ops.mesh.primitive_plane_add(size=4000)
sand = bpy.data.materials.new("M_KitSand")
sand.use_nodes = True
sand.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.31, 0.13, 1)
sand.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
bpy.context.active_object.data.materials.append(sand)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.view_settings.look = "AgX - Punchy"
scene.render.resolution_x, scene.render.resolution_y = 1800, 900
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.clip_end = 5000
scene.collection.objects.link(cam)
scene.camera = cam

# Lay each class out in a row and frame it.
for name, group in pieces.items():
    gap = max(o.dimensions.x for o in group) * 0.35 + 0.5
    x = 0.0
    for obj in group:
        obj.location = (x + obj.dimensions.x / 2, 0, 0)
        x += obj.dimensions.x + gap
    for other, og in pieces.items():
        for obj in og:
            obj.hide_render = other != name
    width = x - gap
    height = max(o.dimensions.z for o in group)
    centre = Vector((width / 2, 0, height * 0.4))
    dist = max(width * 0.95, height * 2.4)
    cam.data.lens = 35
    cam.location = centre + Vector((0.0, -dist * 1.05, dist * 0.32))
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = f"{PREVIEW}_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("PREVIEW", name)
print("KIT DONE")
