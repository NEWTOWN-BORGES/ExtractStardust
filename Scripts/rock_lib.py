# Shared sculpting helpers for the desert rock scripts (run inside Blender).
import bpy
import bmesh
import math
import random
from mathutils import Vector, noise

scene = bpy.context.scene

def ledge_profile(t, layers, sharpness):
    """Stepped strata: each layer ends in a small overhang, like eroded sandstone beds."""
    x = t * layers
    frac = x - math.floor(x)
    return frac ** sharpness


def perimeter_angles(rng, rx, ry, spacing, low, high):
    """Angles spaced along the ellipse perimeter by spacing x uniform(low, high) metres."""
    arc = [(0.0, 0.0)]
    previous = Vector((rx, 0.0))
    for i in range(1, 721):
        theta = 2.0 * math.pi * i / 720
        point = Vector((rx * math.cos(theta), ry * math.sin(theta)))
        arc.append((theta, arc[-1][1] + (point - previous).length))
        previous = point
    angles = []
    s = rng.uniform(0.2, 1.0) * spacing
    index = 0
    while s < arc[-1][1]:
        while arc[index + 1][1] < s:
            index += 1
        angles.append(arc[index][0])
        s += spacing * rng.uniform(low, high)
    return angles


def joint_set(seed, rx, ry, spacing, depth, width):
    """Vertical joints around the footprint: where the wall splits into columns. Each cleft has its own depth and
    width and starts at its own height (many only split the upper wall); each column between two clefts rises to
    its own height, so the rim is ragged like a real Wingate cliff."""
    rng = random.Random(seed * 7 + 3)
    joints = [(angle, depth * rng.uniform(0.4, 1.0), width * rng.uniform(0.6, 1.5), rng.choice((0.0, 0.0, 0.25, 0.45, 0.6)))
              for angle in perimeter_angles(rng, rx, ry, spacing, 0.5, 1.7)]
    heights = [rng.uniform(-1.0, 1.0) for _ in joints]
    return joints, heights


def alcove_set(seed, rx, ry, spacing):
    """Shallow arched alcoves where slabs spalled off the wall: angle, centre height (0..1), half width (m),
    half height (0..1), depth (m)."""
    rng = random.Random(seed * 13 + 5)
    return [(angle, rng.uniform(0.25, 0.7), rng.uniform(6.0, 14.0), rng.uniform(0.1, 0.22), rng.uniform(1.5, 4.5))
            for angle in perimeter_angles(rng, rx, ry, spacing, 0.6, 1.8)]


def column(name, seed, rx, ry, height, embed=6.0, segments=128, rings=72, cap_rings=20,
           taper=0.0, flare=0.12, layers=5, ledge=0.05, bulge=0.3, top_dome=0.02, top_rough=0.03, spire=0.0,
           grooves=22, groove_depth=0.07, caprock=0.0, rim=0.0, joints=0.0, joint_depth=0.0, joint_width=3.0,
           crenel=0.0, alcoves=0.0):
    """Builds a watertight ringed column. rx/ry: base radii (m); bulge: irregular, angular footprint;
    grooves: vertical erosion channels along the joints; taper/spire: narrowing; caprock: wider hard cap on top;
    rim: rounds the shoulder where wall meets top, as weathered Navajo and Wingate sandstone do;
    joints: spacing (m) of deep vertical clefts that split a massive wall into columns (Wingate cliffs);
    crenel: how much each column's height differs (fraction of the height); alcoves: spacing (m) of spalled
    alcoves on the walls."""
    noise.seed_set(seed)
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rows = []
    clefts, column_heights = joint_set(seed, rx, ry, joints, joint_depth, joint_width) if joints > 0.0 and joint_depth > 0.0 else ([], [])
    hollows = alcove_set(seed, rx, ry, alcoves) if alcoves > 0.0 else []

    def along(theta):
        return math.hypot(rx * math.sin(theta), ry * math.cos(theta))  # perimeter metres per radian

    def gap(theta, angle):
        return abs((theta - angle + math.pi) % (2.0 * math.pi) - math.pi) * along(theta)

    def cleft(t, theta):
        """Depth (m) of the joint clefts and alcoves at this point of the wall."""
        deepest = 0.0
        for angle, depth, width, start in clefts:
            d = gap(theta, angle)
            if d < width * 3.0 and t > start:
                rise = min(1.0, (t - start) / 0.2)
                deepest = max(deepest, depth * math.exp(-(d / width) ** 2) * (0.5 + 0.5 * t ** 0.8) * rise * rise * (3.0 - 2.0 * rise))
        for angle, centre, half_width, half_height, depth in hollows:
            d = gap(theta, angle) / half_width
            v = (t - centre) / half_height
            inside = d * d + v * v * (0.6 if v > 0.0 else 1.6)  # arched top, flatter floor
            if inside < 1.0:
                deepest = max(deepest, depth * (1.0 - inside) ** 0.6)
        return deepest

    def top_factor(theta):
        """Height of the column this angle belongs to, dropping a little into each cleft (rounded column tops)."""
        if not clefts or crenel <= 0.0:
            return 1.0
        index = 0
        while index < len(clefts) and clefts[index][0] < theta:
            index += 1
        own = column_heights[index % len(clefts)]
        nearest = min(gap(theta, angle) / width for angle, _, width, _ in clefts)
        return 1.0 + crenel * own - 0.04 * math.exp(-nearest * nearest * 0.5)

    def radius_scale(t, theta):
        around = Vector((math.cos(theta) * 1.3, math.sin(theta) * 1.3, seed * 0.37))
        # Broad lobed footprint, nearly the same up the whole height so walls stay vertical (no melted bulges).
        # Only two octaves: finer octaves would be extruded up the wall as dense vertical striations.
        r = 1.0 + bulge * noise.fractal(around + Vector((0.0, 0.0, t * 0.5)), 0.55, 2.0, 2)
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
        if rim > 0.0 and t > 0.8:
            r *= 1.0 - rim * ((t - 0.8) / 0.2) ** 2
        if clefts or hollows:
            r *= 1.0 - cleft(t, theta) / max(1.0, math.hypot(rx * math.cos(theta), ry * math.sin(theta)))
        return r

    tops = [height * top_factor(2.0 * math.pi * s / segments) for s in range(segments)]
    for ring in range(rings + 1):
        t = ring / rings
        row = []
        for s in range(segments):
            theta = 2.0 * math.pi * s / segments
            z = -embed + (tops[s] + embed) * t
            k = radius_scale(max(0.0, z) / tops[s], theta)
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
            z = base.z + top_dome * height * (1.0 - f * f) + rough
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


def cap(obj):
    """Closes the (normally buried, open) base so cuts and voxel remeshing see a solid volume."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.holes_fill(bm, edges=bm.edges, sides=0)
    bm.to_mesh(obj.data)
    bm.free()


def fracture(obj, seed, walls, chamfers, depth=(1.5, 6.0), tilt=(-3.0, 8.0), chamfer_depth=(1.0, 4.0)):
    """Breaks a capped rock with planar cuts, the way Wingate and Navajo walls break off along vertical joints:
    near-vertical joint faces all around (leaning back a little, rarely overhanging) and a few chamfers across
    the rim. Gives crisp planes and edges instead of soft, melted bulges."""
    rng = random.Random(seed)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    plans = [(rng.uniform(*tilt), rng.uniform(*depth)) for _ in range(walls)]
    plans += [(rng.uniform(30.0, 55.0), rng.uniform(*chamfer_depth)) for _ in range(chamfers)]
    for index, (tilt_deg, cut) in enumerate(plans):
        azimuth = index * 2.39996 + rng.uniform(-0.6, 0.6)  # golden angle: cuts spread all around the rock
        t = math.radians(tilt_deg)
        normal = Vector((math.cos(azimuth) * math.cos(t), math.sin(azimuth) * math.cos(t), math.sin(t)))
        reach = max(v.co.dot(normal) for v in bm.verts)
        result = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=0.001,
                                        plane_co=normal * (reach - cut), plane_no=normal, clear_outer=True)
        edges = [e for e in result["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bm.to_mesh(obj.data)
    bm.free()


def remesh(obj, voxel):
    mod = obj.modifiers.new("Remesh", 'REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = voxel
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)


def massive(name, seed, rx, ry, height, walls, chamfers, voxel, size, depth=(1.5, 6.0), detail=1.0, ratio=0.5, **shape):
    """A massive sandstone body (mesa, butte, cliff): column footprint, fractured into joint planes, remeshed,
    then only light weathering so the planes stay crisp."""
    shape.setdefault("ledge", 0.0)
    shape.setdefault("grooves", 0)
    shape.setdefault("groove_depth", 0.0)
    obj = column(name, seed, rx, ry, height, **shape)
    cap(obj)
    fracture(obj, seed, walls, chamfers, depth=depth)
    remesh(obj, voxel)
    return finish(obj, size, size * 0.45, 0.7 * detail, 1.0 * detail, 0.15 * detail, ratio, levels=0)


def sunlit_preview(rocks, shots, resolution=(1800, 600)):
    """Renders the rocks the way the game shows them: low sun, blue sky, sand ground, red sandstone (EEVEE).
    shots: [(png path, camera location, target, lens)]."""
    scene = bpy.context.scene
    for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    world = bpy.data.worlds.new("PreviewSky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.3, 0.45, 0.75, 1.0)
    scene.world = world

    def material(name, dark, light, scale):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        coords = nodes.new("ShaderNodeTexCoord")
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Detail"].default_value = 8.0
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = dark + (1.0,)
        ramp.color_ramp.elements[1].color = light + (1.0,)
        bsdf = nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = 0.9
        mat.node_tree.links.new(coords.outputs["Object"], tex.inputs["Vector"])
        mat.node_tree.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        mat.node_tree.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        return mat

    stone = material("PreviewRock", (0.2, 0.065, 0.03), (0.5, 0.2, 0.09), 0.08)
    for obj in rocks:
        obj.data.materials.clear()
        obj.data.materials.append(stone)
    bpy.ops.mesh.primitive_plane_add(size=20000.0, location=(0.0, 0.0, -1.0))
    bpy.context.active_object.data.materials.append(material("PreviewSand", (0.42, 0.22, 0.12), (0.6, 0.36, 0.21), 0.02))
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 5.0
    sun_data.color = (1.0, 0.92, 0.8)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(58.0), 0.0, math.radians(-35.0))
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    cam.data.clip_end = 30000.0
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = resolution
    for path, camera_location, target, lens in shots:
        cam.data.lens = lens
        cam.location = camera_location
        cam.rotation_euler = (Vector(target) - Vector(camera_location)).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)


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


def finish(obj, size, joint_scale, joint_strength, erosion_strength, grit_strength, ratio, levels=2, joint_stretch=2.5):
    """Detail passes: subdivide, erosion, joints, grit; then decimate and give it simple UVs.
    Massive sandstone wants large joint cells (a few big blocky faces and cracks tens of metres apart) and a
    small joint_stretch; only banded rocks such as hoodoos use tall, thin joint columns."""
    if levels > 0:
        sub = obj.modifiers.new("Sub", 'SUBSURF')
        sub.subdivision_type = 'SIMPLE'
        sub.levels = levels
        sub.render_levels = levels
    erosion = texture(obj.name + "Erosion", 'CLOUDS', noise_scale=size * 0.3, noise_depth=3)
    joints = texture(obj.name + "Joints", 'VORONOI', noise_scale=joint_scale, distance_metric='DISTANCE',
                     weight_1=-1.0, weight_2=1.0, noise_intensity=1.0)
    grit = texture(obj.name + "Grit", 'STUCCI', noise_scale=1.5, turbulence=3.0)
    displace(obj, erosion, erosion_strength)
    displace(obj, joints, joint_strength, stretch=(1.0, 1.0, joint_stretch), mid=0.0)
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


