# Sculpts the desert rock set in Blender, one piece at a time, each with its own shape, size and seed:
# mesas, buttes, spires, canyon cliff walls and boulders. Shapes come from a ringed column (radius varies with
# height and angle: strata ledges, overhangs, talus flare), then layered displacement (erosion, vertical joints,
# fine grit). Exports one FBX per rock (pivot at ground level) and a preview image of the whole set.
# Usage: blender -b -P sculpt_rocks.py -- <fbx_output_dir> <preview_png>
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


def ledge_profile(t, layers, sharpness):
    """Stepped strata: each layer ends in a small overhang, like eroded sandstone beds."""
    x = t * layers
    frac = x - math.floor(x)
    return frac ** sharpness


def column(name, seed, rx, ry, height, embed=6.0, segments=128, rings=72, cap_rings=20,
           taper=0.0, flare=0.12, layers=5, ledge=0.05, bulge=0.3, top_dome=0.02, top_rough=0.03, spire=0.0,
           grooves=22, groove_depth=0.07, caprock=0.0):
    """Builds a watertight ringed column. rx/ry: base radii (m); bulge: irregular, angular footprint;
    grooves: vertical erosion channels along the joints; taper/spire: narrowing; caprock: wider hard cap on top."""
    noise.seed_set(seed)
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rows = []

    def radius_scale(t, theta):
        around = Vector((math.cos(theta) * 1.3, math.sin(theta) * 1.3, seed * 0.37))
        # Angular, lobed footprint that drifts slowly with height.
        r = 1.0 + bulge * noise.fractal(around + Vector((0.0, 0.0, t * 0.6)), 0.6, 2.2, 4)
        # Vertical grooves (ridged noise around the column), deeper in the middle of the wall.
        groove = 1.0 - abs(noise.noise(Vector((math.cos(theta) * grooves * 0.32, math.sin(theta) * grooves * 0.32, t * 0.8 + seed))))
        r *= 1.0 - groove_depth * groove ** 3 * (0.5 + 0.5 * math.sin(math.pi * min(1.0, t * 1.1)))
        r *= 1.0 - taper * t ** 1.2
        r *= 1.0 + ledge * ledge_profile(t + 0.07 * noise.noise(around * 0.9 + Vector((0.0, 0.0, t))), layers, 3.0)
        if t < 0.12:
            r *= 1.0 + flare * (1.0 + 0.6 * noise.noise(around * 2.0)) * ((0.12 - t) / 0.12) ** 2
        if spire > 0.0 and t > 0.55:
            r *= max(0.12, 1.0 - spire * ((t - 0.55) / 0.45) ** 1.3)
        if caprock > 0.0 and t > 0.88:
            r *= 1.0 + caprock * min(1.0, (t - 0.88) / 0.04)
        return r

    for ring in range(rings + 1):
        t = ring / rings
        z = -embed + (height + embed) * t
        row = []
        for s in range(segments):
            theta = 2.0 * math.pi * s / segments
            k = radius_scale(max(0.0, z) / height, theta)
            row.append(bm.verts.new((rx * k * math.cos(theta), ry * k * math.sin(theta), z)))
        rows.append(row)
    for ring in range(rings):
        for s in range(segments):
            a, b = rows[ring][s], rows[ring][(s + 1) % segments]
            c, d = rows[ring + 1][(s + 1) % segments], rows[ring + 1][s]
            bm.faces.new((a, b, c, d))

    # Top cap: concentric rings with a gentle, rough dome (weathered caprock).
    previous = rows[-1]
    for cap in range(1, cap_rings):
        f = 1.0 - cap / cap_rings
        row = []
        for s in range(segments):
            outer = previous[s].co if cap == 1 else rows[-1][s].co
            base = rows[-1][s].co
            x, y = base.x * f, base.y * f
            rough = top_rough * height * noise.fractal(Vector((x * 0.05, y * 0.05, seed)), 0.7, 2.0, 4)
            z = height + top_dome * height * (1.0 - f * f) + rough
            row.append(bm.verts.new((x, y, z)))
        for s in range(segments):
            bm.faces.new((previous[s], previous[(s + 1) % segments], row[(s + 1) % segments], row[s]))
        previous = row
    centre = bm.verts.new((0.0, 0.0, height + top_dome * height))
    for s in range(segments):
        bm.faces.new((previous[s], previous[(s + 1) % segments], centre))
    # Bottom stays open below the ground (never seen).
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def texture(name, kind, **props):
    t = bpy.data.textures.new(name, kind)
    for key, value in props.items():
        setattr(t, key, value)
    return t


def displace(obj, tex, strength, stretch=(1.0, 1.0, 1.0), mid=0.5):
    space = bpy.data.objects.new(obj.name + "_" + tex.name, None)
    scene.collection.objects.link(space)
    space.scale = stretch
    mod = obj.modifiers.new(tex.name, 'DISPLACE')
    mod.texture = tex
    mod.strength = strength
    mod.mid_level = mid
    mod.texture_coords = 'OBJECT'
    mod.texture_coords_object = space
    return space


def finish(obj, size, joint_scale, joint_strength, erosion_strength, grit_strength, ratio):
    """Detail passes: subdivide, erosion, vertical joints, grit; then decimate and give it simple UVs."""
    sub = obj.modifiers.new("Sub", 'SUBSURF')
    sub.subdivision_type = 'SIMPLE'
    sub.levels = 2
    sub.render_levels = 2
    erosion = texture(obj.name + "Erosion", 'CLOUDS', noise_scale=size * 0.2, noise_depth=3)
    joints = texture(obj.name + "Joints", 'VORONOI', noise_scale=joint_scale, distance_metric='DISTANCE',
                     weight_1=-1.0, weight_2=1.0, noise_intensity=1.0)
    grit = texture(obj.name + "Grit", 'STUCCI', noise_scale=1.5, turbulence=3.0)
    displace(obj, erosion, erosion_strength)
    # Joints stretched strongly upward: tall blocky columns instead of popcorn bumps.
    displace(obj, joints, joint_strength, stretch=(1.0, 1.0, 8.0), mid=0.0)
    displace(obj, grit, grit_strength * 0.5)
    dec = obj.modifiers.new("Dec", 'DECIMATE')
    dec.ratio = ratio
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=size * 0.25)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    return obj


def boulder(name, seed, radius, flatten):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=radius)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (1.0 + 0.2 * (seed % 3), 1.0, flatten)
    bpy.ops.object.transform_apply(scale=True)
    facets = texture(name + "Facets", 'VORONOI', noise_scale=radius * 0.6, distance_metric='DISTANCE',
                     weight_1=1.0, weight_2=0.0, noise_intensity=1.0)
    lumps = texture(name + "Lumps", 'CLOUDS', noise_scale=radius * 0.8, noise_depth=3)
    displace(obj, lumps, radius * 0.35)
    displace(obj, facets, radius * 0.25)
    obj.location.z = -radius * flatten * 0.3
    bpy.ops.object.transform_apply(location=True)
    dec = obj.modifiers.new("Dec", 'DECIMATE')
    dec.ratio = 0.35
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=radius)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


rocks = []
# Mesas: wide, flat-topped, angular footprint, strata ledges and deep joint grooves (Wadi Rum style).
rocks.append(finish(column("SM_Mesa_A", 11, 50, 42, 55, layers=5, ledge=0.05, bulge=0.32, grooves=26, groove_depth=0.08), 50, 9.0, 3.0, 3.0, 0.35, 0.45))
rocks.append(finish(column("SM_Mesa_B", 23, 60, 38, 40, layers=7, ledge=0.07, bulge=0.36, top_dome=0.05, grooves=30), 60, 7.0, 2.6, 3.5, 0.35, 0.45))
# Butte: tall, rounded weathered top (jebel), grooved walls.
rocks.append(finish(column("SM_Butte_A", 37, 24, 18, 65, layers=6, ledge=0.04, bulge=0.34, taper=0.12, top_dome=0.12, top_rough=0.05, grooves=18, groove_depth=0.12), 24, 5.0, 2.0, 1.8, 0.25, 0.5))
# Hoodoos: narrow necks under a wider hard caprock, stacked uneven beds.
rocks.append(finish(column("SM_Spire_A", 41, 8, 7, 42, segments=96, rings=80, cap_rings=8, layers=8, ledge=0.12, bulge=0.3, taper=0.3, spire=0.35, caprock=0.9, top_dome=0.04, grooves=10, groove_depth=0.1), 8, 2.5, 0.8, 0.9, 0.15, 0.55))
rocks.append(finish(column("SM_Spire_B", 53, 6, 5, 30, segments=96, rings=64, cap_rings=8, layers=5, ledge=0.16, bulge=0.35, taper=0.15, spire=0.8, grooves=8, groove_depth=0.12), 6, 2.0, 0.7, 0.7, 0.12, 0.55))
# Canyon cliff walls: long slabs with buttresses and gullies; the back is buried in the terrain.
rocks.append(finish(column("SM_Cliff_A", 61, 45, 12, 60, layers=6, ledge=0.03, bulge=0.25, grooves=34, groove_depth=0.12), 45, 8.0, 3.0, 2.5, 0.35, 0.45))
rocks.append(finish(column("SM_Cliff_B", 73, 40, 14, 45, layers=9, ledge=0.05, bulge=0.3, top_dome=0.04, grooves=28, groove_depth=0.1), 40, 6.0, 2.4, 2.8, 0.3, 0.45))
rocks.append(finish(column("SM_Cliff_C", 89, 55, 10, 75, layers=4, ledge=0.02, bulge=0.22, grooves=40, groove_depth=0.14), 55, 11.0, 3.4, 2.2, 0.35, 0.45))
# Boulders for scattering.
rocks.append(boulder("SM_Boulder_A", 3, 3.0, 0.7))
rocks.append(boulder("SM_Boulder_B", 5, 5.5, 0.55))
rocks.append(boulder("SM_Boulder_C", 7, 1.8, 0.8))

for obj in rocks:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(OUT, obj.name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_scale_options='FBX_SCALE_UNITS',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', use_mesh_modifiers=True)
    print("ROCK", obj.name, len(obj.data.polygons), "faces", round(obj.dimensions.x), round(obj.dimensions.y), round(obj.dimensions.z))

# Preview: the set in a row, clay shading with cavity so the forms read clearly.
x = 0.0
for obj in rocks:
    width = obj.dimensions.x
    obj.location.x = x + width * 0.5
    x += width + 8.0
centre = Vector((x * 0.5, 0.0, 20.0))
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 35
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
cam.location = (centre.x, -x * 0.95, x * 0.1)
direction = centre - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam
scene.render.engine = 'BLENDER_WORKBENCH'
shading = scene.display.shading
shading.light = 'STUDIO'
shading.color_type = 'SINGLE'
shading.single_color = (0.55, 0.28, 0.18)
shading.show_cavity = True
shading.show_shadows = True
scene.render.resolution_x = 1800
scene.render.resolution_y = 650
scene.render.filepath = PREVIEW
bpy.ops.render.render(write_still=True)
print("SCULPT DONE")
