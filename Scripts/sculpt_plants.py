# Utah desert plants for sector S01, grown from code: a branching skeleton (tapered tubes that bend and twist as
# they grow, children sprouting on the upper part of each branch) carrying clusters of real leaf shapes. Leaves are
# double-faced and get soft "crown" normals (pointing out of the foliage mass) plus crown occlusion in their vertex
# colours, so a tree lights as a volume instead of a noise of flat cards. Vertex alpha marks leaves (1) for light
# transmission in the material; bark and pads are 0. No textures, so they stay light.
# Fremont cottonwood and coyote willow (wet washes), Utah juniper (slickrock), big sagebrush, dry and green grass,
# prickly pear, narrowleaf yucca and dead brush. Exports one FBX per plant (pivot at ground level).
# Usage: blender -b -P sculpt_plants.py -- <fbx_output_dir> <preview_prefix>
import bpy
import bmesh
import math
import os
import random
import sys
from mathutils import Matrix, Quaternion, Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
PREVIEW = argv[1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

UP = Vector((0.0, 0.0, 1.0))
COTTONWOOD_BARK = (0.42, 0.38, 0.33)
JUNIPER_BARK = (0.5, 0.46, 0.41)
DEAD_WOOD = (0.66, 0.63, 0.58)


def deviate(axis, angle, roll):
    """Direction tilted by angle away from axis, rolled around it."""
    perp = axis.orthogonal().normalized()
    return (Quaternion(axis, roll) @ (Quaternion(perp, angle) @ axis)).normalized()


def jitter(rgb, rng, amount):
    k = 1.0 + rng.uniform(-amount, amount)
    return (min(1.0, rgb[0] * k * rng.uniform(0.94, 1.06)), min(1.0, rgb[1] * k), min(1.0, rgb[2] * k * rng.uniform(0.94, 1.06)))


def random_unit(rng):
    while True:
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if 0.05 < v.length <= 1.0:
            return v.normalized()


class Plant:
    """Accumulates bark tubes, solid parts and leaves in one mesh with a vertex colour layer."""

    def __init__(self, name, seed):
        self.name = name
        self.rng = random.Random(seed)
        self.bm = bmesh.new()
        self.color = self.bm.loops.layers.color.new("Col")
        self.leaves = []  # (faces, centre, colour, fixed normal or None)

    def paint(self, faces, rgb, shade=0.35, alpha=0.0):
        for face in faces:
            face.normal_update()
            k = 1.0 - shade + shade * (face.normal.z * 0.5 + 0.5)  # undersides darker
            for loop in face.loops:
                loop[self.color] = (rgb[0] * k, rgb[1] * k, rgb[2] * k, alpha)

    def tube(self, points, radii, rgb, sides):
        rings = []
        ref = Vector((1.0, 0.0, 0.0))
        for i, p in enumerate(points):
            d = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
            side = ref - d * ref.dot(d)  # parallel transport keeps the rings from twisting
            if side.length < 1e-4:
                side = d.orthogonal()
            side.normalize()
            ref = side
            other = d.cross(side)
            rings.append([self.bm.verts.new(p + (side * math.cos(2 * math.pi * s / sides) + other * math.sin(2 * math.pi * s / sides)) * radii[i])
                          for s in range(sides)])
        faces = []
        for i in range(len(rings) - 1):
            ring_faces = []
            for s in range(sides):
                n = (s + 1) % sides
                ring_faces.append(self.bm.faces.new((rings[i][s], rings[i][n], rings[i + 1][n], rings[i + 1][s])))
            # Bark darkens towards the ground.
            k = 0.75 + 0.25 * min(1.0, max(0.0, points[i].z / 3.0))
            self.paint(ring_faces, (rgb[0] * k, rgb[1] * k, rgb[2] * k), 0.3)
            faces += ring_faces
        cap = self.bm.faces.new(rings[-1])
        self.paint([cap], rgb, 0.3)
        for face in faces + [cap]:
            face.smooth = True

    def blob(self, centre, radius, rgb, squash=1.0, lump=0.3, subdiv=2):
        geom = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=radius, matrix=Matrix.Translation(centre))
        offset = Vector((self.rng.random(), self.rng.random(), self.rng.random())) * 50.0
        for v in geom["verts"]:
            local = v.co - centre
            k = 1.0 + lump * noise.noise(local.normalized() * 1.8 + offset)
            v.co = centre + Vector((local.x * k, local.y * k, local.z * k * squash))
        faces = list({f for v in geom["verts"] for f in v.link_faces})
        for face in faces:
            face.smooth = True
        self.paint(faces, rgb)

    def leaf(self, centre, axis, facing, length, width, rgb, normal=None, shape="broad"):
        """A leaf outline built as two faces back to back, so it shows from both sides with the same shading."""
        side = facing.cross(axis)
        if side.length < 1e-4:
            side = axis.orthogonal()
        side.normalize()
        if shape == "broad":  # cottonwood: triangular-ovate
            outline = [(-0.5, 0.0), (-0.3, 0.45), (0.05, 0.42), (0.5, 0.0), (0.05, -0.42), (-0.3, -0.45)]
        else:  # narrow: willow, juniper sprays, sage, blades
            outline = [(-0.5, 0.0), (-0.2, 0.5), (0.3, 0.32), (0.5, 0.0), (0.3, -0.32), (-0.2, -0.5)]
        droop = Vector((0.0, 0.0, -0.12 * length))
        points = [centre + axis * (u * length) + side * (v * width) + droop * (u + 0.5) ** 2 for u, v in outline]
        front = self.bm.faces.new([self.bm.verts.new(p) for p in points])
        back = self.bm.faces.new([self.bm.verts.new(p) for p in reversed(points)])
        self.leaves.append(((front, back), centre.copy(), rgb, normal))

    def grow(self, start, direction, length, radius, level, cfg, dead=False):
        """One branch as a bent tube; children sprout along its upper part; leaf clusters at the tips."""
        rng = self.rng
        segments = max(3, int(length / cfg["seg"]))
        points, radii = [start.copy()], [radius]
        d = direction.normalized()
        p = start.copy()
        for i in range(1, segments + 1):
            wobble = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * cfg["gnarl"]
            d = (d + wobble + Vector((0.0, 0.0, cfg["up"]))).normalized()
            p = p + d * (length / segments)
            points.append(p.copy())
            radii.append(radius * (1.0 - (i / segments) * (1.0 - cfg["taper"])))
        sides = cfg["sides"][min(level, len(cfg["sides"]) - 1)]
        self.tube(points, radii, DEAD_WOOD if dead else cfg["bark"], sides)
        if level >= cfg["levels"]:
            if not dead:
                self.cluster(points[-1], d, cfg, cfg["leaves"])
            return
        count = cfg["children"][level]
        for c in range(count):
            t = cfg["sprout"] + (1.0 - cfg["sprout"]) * (c + 1) / count
            index = max(1, min(segments, int(round(t * segments))))
            axis = (points[index] - points[index - 1]).normalized()
            child = deviate(axis, math.radians(rng.uniform(*cfg["angle"])), c * 2.39996 + rng.uniform(-0.5, 0.5))
            child_dead = dead or (level >= 1 and rng.random() < cfg.get("dead", 0.0))
            self.grow(points[index], child, length * rng.uniform(*cfg["ratio"]), radii[index] * cfg["child_radius"],
                      level + 1, cfg, child_dead)
        if level >= cfg["levels"] - 1 and not dead:
            for _ in range(cfg.get("inner", 0)):
                self.cluster(points[rng.randint(segments // 2, segments)], d, cfg, cfg["leaves"] // 2)

    def cluster(self, tip, direction, cfg, count):
        rng = self.rng
        centre = tip + direction * cfg["cluster_r"] * 0.5
        for _ in range(count):
            offset = random_unit(rng) * cfg["cluster_r"] * rng.random() ** 0.5
            offset.z *= cfg.get("squash", 0.8)
            axis = (random_unit(rng) + direction * 0.6 - UP * 0.3).normalized()
            facing = (random_unit(rng) + UP * 0.8).normalized()
            self.leaf(centre + offset, axis, facing, rng.uniform(*cfg["leaf_len"]), rng.uniform(*cfg["leaf_w"]),
                      jitter(rng.choice(cfg["colours"]), rng, 0.1), shape=cfg.get("shape", "broad"))

    def finish(self, crown_light=True):
        """Crown normals and occlusion for the leaves, then the mesh object."""
        if self.leaves:
            centres = [c for _, c, _, _ in self.leaves]
            crown = sum(centres, Vector()) / len(centres)
            distances = sorted((c - crown).length for c in centres)
            radius = max(0.05, distances[int(len(distances) * 0.85)])
        normals = {}
        self.bm.faces.index_update()
        for faces, centre, rgb, fixed in self.leaves:
            if fixed is not None:
                normal = fixed
                k = 1.0
            else:
                out = centre - crown
                normal = (out.normalized() * 0.75 + UP * 0.45).normalized() if out.length > 1e-4 else UP
                depth = min(1.0, out.length / radius)
                k = 0.42 + 0.48 * depth + 0.12 * max(-1.0, min(1.0, out.z / radius))
            for face in faces:
                normals[face.index] = normal
                for loop in face.loops:
                    loop[self.color] = (rgb[0] * k, rgb[1] * k, rgb[2] * k, 1.0)
        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        try:
            mesh.color_attributes.active_color = mesh.color_attributes["Col"]
        except (AttributeError, KeyError, TypeError):
            pass
        corner = [n.vector.copy() for n in mesh.corner_normals]
        for poly in mesh.polygons:
            if poly.index in normals:
                for li in poly.loop_indices:
                    corner[li] = normals[poly.index]
        mesh.normals_split_custom_set(corner)
        obj = bpy.data.objects.new(self.name, mesh)
        scene.collection.objects.link(obj)
        return obj


def tree(name, seed, trunks, cfg):
    plant = Plant(name, seed)
    for direction, length, radius in trunks(plant.rng):
        plant.grow(Vector((0.0, 0.0, -0.4)), direction, length, radius, 0, cfg)
    return plant.finish()


def spread_trunks(count, tilt, length, radius):
    def make(rng):
        out = []
        for i in range(count):
            a = 2 * math.pi * i / count + rng.uniform(-0.4, 0.4)
            t = math.radians(rng.uniform(*tilt))
            out.append((Vector((math.cos(a) * math.sin(t), math.sin(a) * math.sin(t), math.cos(t))),
                        rng.uniform(*length), rng.uniform(*radius)))
        return out
    return make


# Fremont cottonwood: one thick trunk forking low into big limbs, broad rounded crown of bright green leaves.
COTTONWOOD = dict(levels=4, children=[4, 3, 2, 2], angle=(28.0, 52.0), ratio=(0.62, 0.8), child_radius=0.62, taper=0.6,
                  gnarl=0.12, up=0.06, seg=0.7, sprout=0.55, sides=[12, 9, 7, 5, 4], bark=COTTONWOOD_BARK, dead=0.04,
                  leaves=95, inner=1, cluster_r=1.05, leaf_len=(0.2, 0.3), leaf_w=(0.15, 0.22), shape="broad",
                  colours=[(0.36, 0.5, 0.17), (0.42, 0.55, 0.2), (0.3, 0.45, 0.14), (0.48, 0.56, 0.22)])
# Utah juniper: several twisted trunks from the base, shaggy grey bark, dense grey-green scale sprays, dead limbs.
JUNIPER = dict(levels=3, children=[3, 3, 2], angle=(30.0, 62.0), ratio=(0.6, 0.82), child_radius=0.6, taper=0.5,
               gnarl=0.38, up=0.1, seg=0.3, sprout=0.4, sides=[8, 6, 5, 4], bark=JUNIPER_BARK, dead=0.12,
               leaves=170, inner=1, cluster_r=0.42, squash=0.7, leaf_len=(0.08, 0.14), leaf_w=(0.03, 0.05), shape="narrow",
               colours=[(0.3, 0.37, 0.26), (0.35, 0.41, 0.29), (0.27, 0.34, 0.24), (0.38, 0.42, 0.3)])
# Coyote willow: a thicket of thin straight stems with narrow leaves on the upper part.
WILLOW = dict(levels=1, children=[2], angle=(15.0, 30.0), ratio=(0.4, 0.6), child_radius=0.6, taper=0.4,
              gnarl=0.05, up=0.12, seg=0.5, sprout=0.5, sides=[5, 4], bark=(0.5, 0.33, 0.22),
              leaves=44, inner=3, cluster_r=0.32, squash=2.2, leaf_len=(0.13, 0.19), leaf_w=(0.04, 0.06), shape="narrow",
              colours=[(0.42, 0.52, 0.2), (0.48, 0.56, 0.24), (0.38, 0.48, 0.18)])
# Big sagebrush: short woody stems, small silver-green leaves.
SAGE = dict(levels=2, children=[3, 2], angle=(25.0, 50.0), ratio=(0.55, 0.75), child_radius=0.6, taper=0.5,
            gnarl=0.25, up=0.12, seg=0.12, sprout=0.4, sides=[5, 4, 3], bark=JUNIPER_BARK,
            leaves=40, cluster_r=0.16, leaf_len=(0.06, 0.09), leaf_w=(0.025, 0.035), shape="narrow",
            colours=[(0.58, 0.62, 0.52), (0.64, 0.67, 0.57), (0.52, 0.57, 0.47)])
DEAD = dict(levels=3, children=[3, 2, 2], angle=(30.0, 65.0), ratio=(0.55, 0.8), child_radius=0.6, taper=0.4,
            gnarl=0.35, up=0.05, seg=0.12, sprout=0.35, sides=[4, 3, 3, 3], bark=(0.6, 0.53, 0.44),
            leaves=0, cluster_r=0.1, leaf_len=(0.1, 0.1), leaf_w=(0.1, 0.1), colours=[(0.5, 0.5, 0.4)])


def grass(name, seed, colours, blades, height):
    plant = Plant(name, seed)
    rng = plant.rng
    for i in range(blades):
        a = rng.uniform(0, 2 * math.pi)
        lean = math.radians(rng.uniform(8, 40))
        direction = Vector((math.cos(a) * math.sin(lean), math.sin(a) * math.sin(lean), math.cos(lean)))
        length = rng.uniform(*height)
        base = Vector((math.cos(a), math.sin(a), 0.0)) * rng.uniform(0.0, 0.08) + direction * length * 0.5 - Vector((0, 0, 0.05))
        facing = direction.cross(Vector((-math.sin(a), math.cos(a), 0.0))).normalized()
        plant.leaf(base, direction, facing, length, rng.uniform(0.02, 0.035), jitter(rng.choice(colours), rng, 0.12),
                   normal=UP, shape="narrow")
    return plant.finish()


def yucca(name, seed):
    plant = Plant(name, seed)
    rng = plant.rng
    for i in range(48):
        a = i * 2.39996
        up = math.radians(rng.uniform(20, 85))
        direction = Vector((math.cos(a) * math.cos(up), math.sin(a) * math.cos(up), math.sin(up)))
        length = rng.uniform(0.45, 0.8)
        facing = direction.cross(Vector((-math.sin(a), math.cos(a), 0.0))).normalized()
        plant.leaf(Vector((0, 0, 0.05)) + direction * length * 0.5, direction, facing, length, rng.uniform(0.03, 0.045),
                   jitter((0.44, 0.5, 0.36), rng, 0.1), normal=(direction + UP).normalized(), shape="narrow")
    # Last season's dry flower stalk with seed pods.
    stalk = [Vector((0, 0, 0.1)), Vector((0.03, 0.02, 0.8)), Vector((0.08, 0.03, 1.5)), Vector((0.1, 0.05, 1.9))]
    plant.tube(stalk, [0.025, 0.02, 0.016, 0.01], (0.62, 0.54, 0.4), 5)
    for k in range(7):
        p = stalk[2].lerp(stalk[3], k / 7.0) + Vector((rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06), 0))
        plant.blob(p, 0.035, (0.58, 0.5, 0.36), 1.6, 0.2, 1)
    return plant.finish()


def prickly_pear(name, seed):
    plant = Plant(name, seed)
    rng = plant.rng

    def pad(centre, yaw, tilt, size, depth):
        geom = bmesh.ops.create_icosphere(plant.bm, subdivisions=2, radius=1.0, matrix=Matrix.Identity(4))
        rot = Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(tilt, 4, 'Y')
        for v in geom["verts"]:
            v.co = centre + (rot @ Vector((v.co.x * size * 0.95, v.co.y * size * 0.22, v.co.z * size * 1.25)))
        faces = list({f for v in geom["verts"] for f in v.link_faces})
        for face in faces:
            face.smooth = True
        colour = (0.38, 0.5, 0.26) if rng.random() < 0.75 else (0.55, 0.45, 0.36)  # some pads stressed purple-brown
        plant.paint(faces, jitter(colour, rng, 0.1), 0.3)
        if depth > 0:
            for k in range(rng.randint(1, 2)):
                # New pads grow from the rim and lean outwards, so the plant sprawls instead of stacking.
                child_size = size * rng.uniform(0.8, 0.95)
                child_yaw = yaw + rng.uniform(-0.9, 0.9)
                child_tilt = tilt + rng.choice((-1.0, 1.0)) * rng.uniform(0.35, 0.75)
                child_rot = Matrix.Rotation(child_yaw, 4, 'Z') @ Matrix.Rotation(child_tilt, 4, 'Y')
                rim = centre + (rot @ Vector((rng.uniform(-0.5, 0.5) * size, 0.0, size * 1.1)))
                pad(rim + (child_rot @ Vector((0.0, 0.0, child_size * 1.05))), child_yaw, child_tilt, child_size, depth - 1)
        elif rng.random() < 0.6:
            for k in range(3):  # ripe fruit on the rim
                plant.blob(centre + (rot @ Vector(((k - 1) * size * 0.5, 0.0, size * 1.3))), 0.03, (0.62, 0.14, 0.24), 1.3, 0.1, 1)

    for i in range(5):
        a = i * 1.26 + rng.uniform(-0.3, 0.3)
        pad(Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 0.14)), a + 1.57, rng.choice((-1.0, 1.0)) * rng.uniform(0.2, 0.5),
            rng.uniform(0.15, 0.19), 2)
    return plant.finish()


def willow(name, seed):
    plant = Plant(name, seed)
    rng = plant.rng
    for i in range(13):
        a = rng.uniform(0, 2 * math.pi)
        base = Vector((math.cos(a), math.sin(a), 0.0)) * rng.uniform(0.0, 0.9) + Vector((0, 0, -0.2))
        lean = math.radians(rng.uniform(3, 18))
        direction = Vector((math.cos(a) * math.sin(lean), math.sin(a) * math.sin(lean), math.cos(lean)))
        plant.grow(base, direction, rng.uniform(2.0, 3.4), rng.uniform(0.025, 0.04), 0, WILLOW)
    return plant.finish()


trees = [
    tree("SM_Cottonwood_A", 11, spread_trunks(1, (2, 6), (4.0, 4.4), (0.42, 0.46)), COTTONWOOD),
    tree("SM_Cottonwood_B", 12, spread_trunks(2, (8, 16), (3.2, 3.8), (0.32, 0.36)), COTTONWOOD),
    tree("SM_Juniper_A", 21, spread_trunks(3, (15, 35), (1.4, 2.0), (0.14, 0.2)), JUNIPER),
    tree("SM_Juniper_B", 22, spread_trunks(2, (20, 40), (1.6, 2.2), (0.16, 0.2)), JUNIPER),
    willow("SM_Willow", 31),
]
small = [
    tree("SM_Sagebrush", 41, spread_trunks(5, (25, 50), (0.35, 0.5), (0.03, 0.04)), SAGE),
    tree("SM_DeadBrush", 51, spread_trunks(6, (30, 60), (0.4, 0.6), (0.02, 0.03)), DEAD),
    grass("SM_DryGrass", 61, [(0.74, 0.64, 0.42), (0.8, 0.7, 0.48), (0.68, 0.57, 0.38)], 30, (0.35, 0.6)),
    grass("SM_GreenGrass", 62, [(0.4, 0.52, 0.2), (0.46, 0.57, 0.24), (0.52, 0.58, 0.28)], 36, (0.4, 0.75)),
    prickly_pear("SM_PricklyPear", 71),
    yucca("SM_Yucca", 81),
]

for obj in trees + small:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, obj.name + ".fbx"), use_selection=True, apply_scale_options='FBX_SCALE_UNITS',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', colors_type='LINEAR')
    print("PLANT", obj.name, len(obj.data.polygons), [round(d, 2) for d in obj.dimensions])

# Previews at true scale on sand-coloured ground against a pale sky: the trees, then a close-up of the small plants.
world = bpy.data.worlds.new("Sky")
world.color = (0.55, 0.65, 0.78)
scene.world = world
bpy.ops.mesh.primitive_plane_add(size=1.0)
ground = bpy.context.active_object
ground.scale = (400.0, 400.0, 1.0)
layer = ground.data.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
for item in layer.data:
    item.color = (0.62, 0.45, 0.32, 1.0)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.lens = 40
cam.data.clip_end = 5000.0
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.engine = 'BLENDER_WORKBENCH'
shading = scene.display.shading
shading.light = 'STUDIO'
shading.color_type = 'VERTEX'
shading.show_cavity = True
shading.show_shadows = True
shading.show_backface_culling = True  # like the game: each leaf face shows only from its own side
scene.render.resolution_x = 1800
scene.render.resolution_y = 700


def shoot(group, gap, distance, height, path):
    for obj in trees + small:
        obj.hide_render = obj not in group
    x = 0.0
    for obj in group:
        width = max(obj.dimensions.x, 0.8)
        obj.location = (x + width * 0.5, 0.0, 0.0)
        x += width + gap
    target = Vector((x * 0.5, 0.0, height))
    cam.location = (x * 0.5, -x * distance, height * 1.3)
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


shoot(trees, 1.5, 1.05, 5.0, PREVIEW + "_trees.png")
shoot(small, 0.4, 0.75, 0.6, PREVIEW + "_small.png")
print("PLANTS DONE")
