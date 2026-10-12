# EXTRACT: STARDUST — anti-gravity rally racer, modelled procedurally in Blender.
# Run:  blender -b -P blender_ship.py -- <out.bytes> [preview.png]
# Output format (little endian): "SDM1", int32 triCount, then per triangle 3 x (pos xyz, normal xyz) float32 + uint8 part id.
# Axes are converted to Unity (Y up, Z forward, left handed): unity = (bx, bz, by). Nose points to +Y in Blender.
import bpy, bmesh, struct, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "racer.bytes"
PREVIEW = argv[1] if len(argv) > 1 else None

# part ids -> colours are applied in Unity (livery aware)
MAIN, ACCENT, DARK, BELLY, GLASS, HOT, GLOW, METAL = range(8)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
mats = []
for i, c in enumerate([(0.1, 0.7, 1), (1, 1, 1), (0.1, 0.1, 0.12), (0.03, 0.03, 0.04), (0.1, 0.4, 0.6), (1, 0.5, 0.15), (0.3, 0.9, 1), (0.5, 0.5, 0.55)]):
    m = bpy.data.materials.new("part%d" % i)
    m.diffuse_color = (c[0], c[1], c[2], 1)
    mats.append(m)


def new_obj(name, bm, subsurf=0, bevel=0.0, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    if bevel > 0:
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = 2
        b.limit_method = "ANGLE"
    if subsurf > 0:
        s = ob.modifiers.new("subsurf", "SUBSURF")
        s.levels = subsurf
        s.render_levels = subsurf
    for p in me.polygons:
        p.use_smooth = smooth
    return ob


def loft(name, stations, part_of, caps=True, subsurf=2, close_front=True):
    """stations: list of (y, rings) where rings is a list of (x, z) points around the section."""
    bm = bmesh.new()
    rings = []
    for y, pts in stations:
        rings.append([bm.verts.new((x, y, z)) for (x, z) in pts])
    n = len(rings[0])
    for i in range(len(rings) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            f.material_index = part_of(i, k)
    if caps:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = part_of(-1, 0)
        f = bm.faces.new(rings[-1])
        f.material_index = part_of(len(rings), 0)
    return new_obj(name, bm, subsurf=subsurf)


def section(hw, zb, zt, chine=0.12, top=0.45):
    return [(-hw, zb + chine), (-hw * 0.72, zb), (hw * 0.72, zb), (hw, zb + chine),
            (hw * 0.93, zb + (zt - zb) * 0.62), (hw * top, zt), (-hw * top, zt), (-hw * 0.93, zb + (zt - zb) * 0.62)]


# ---------------------------------------------------------------- hull
hull_st = [
    (3.45, section(0.10, -0.04, 0.06)),
    (2.9, section(0.30, -0.14, 0.18)),
    (2.0, section(0.58, -0.24, 0.36)),
    (0.8, section(0.84, -0.32, 0.54)),
    (-0.6, section(0.95, -0.33, 0.66)),
    (-1.9, section(0.90, -0.30, 0.6)),
    (-2.7, section(0.74, -0.25, 0.46)),
    (-3.05, section(0.62, -0.2, 0.38)),
]


def hull_part(i, k):
    if i < 0:
        return ACCENT
    if i >= len(hull_st):
        return DARK
    if k == 1:
        return BELLY
    if k in (0, 3) and 1 <= i <= 4:
        return ACCENT
    if k in (5, 6):
        return MAIN if i != 3 else ACCENT
    return MAIN


loft("hull", hull_st, hull_part, subsurf=2)

# canopy bubble
can_st = [(1.6, [(-0.05, 0.42), (0.05, 0.42), (0.05, 0.44), (-0.05, 0.44)]),
          (1.1, [(-0.36, 0.5), (0.36, 0.5), (0.3, 0.74), (-0.3, 0.74)]),
          (0.1, [(-0.44, 0.58), (0.44, 0.58), (0.36, 0.9), (-0.36, 0.9)]),
          (-0.8, [(-0.4, 0.62), (0.4, 0.62), (0.3, 0.84), (-0.3, 0.84)]),
          (-1.4, [(-0.3, 0.64), (0.3, 0.64), (0.2, 0.7), (-0.2, 0.7)])]
loft("canopy", can_st, lambda i, k: GLASS, subsurf=2)

# spine / air intake behind the canopy
spine_st = [(-0.9, [(-0.18, 0.6), (0.18, 0.6), (0.14, 0.82), (-0.14, 0.82)]),
            (-2.6, [(-0.22, 0.42), (0.22, 0.42), (0.16, 0.74), (-0.16, 0.74)])]
loft("spine", spine_st, lambda i, k: DARK if i < 0 else ACCENT, subsurf=1)


# ---------------------------------------------------------------- engine pods
def ring(r, z0, n=12, sx=1.0):
    return [(math.cos(a) * r * sx, z0 + math.sin(a) * r) for a in [2 * math.pi * j / n for j in range(n)]]


for side in (-1, 1):
    x = side * 1.62
    st = []
    for y, r in [(0.9, 0.05), (0.6, 0.32), (0.1, 0.46), (-1.2, 0.5), (-2.7, 0.47), (-3.15, 0.42)]:
        st.append((y, [(x + px, pz) for (px, pz) in ring(r, 0.04, 12, 1.08)]))

    def pod_part(i, k, side=side):
        if i < 0:
            return METAL
        if i >= 5:
            return HOT
        if i == 3 and k in (2, 3, 4, 8, 9, 10):
            return ACCENT
        return MAIN if k in (2, 3, 4) else METAL
    loft("pod%d" % side, st, pod_part, subsurf=1)
    # nozzle glow disc and ring
    bm = bmesh.new()
    rv = [bm.verts.new((x + px * 1.0, -3.18, pz)) for (px, pz) in ring(0.36, 0.04, 12, 1.08)]
    f = bm.faces.new(list(reversed(rv)))
    f.material_index = HOT
    new_obj("nozzle%d" % side, bm, smooth=False)
    # pylon wing joining pod and hull (swept)
    wing_st = [(0.2, [(side * 0.7, -0.05), (side * 1.4, -0.02), (side * 1.4, 0.12), (side * 0.7, 0.16)]),
               (-1.8, [(side * 0.75, -0.05), (side * 1.45, -0.02), (side * 1.45, 0.12), (side * 0.75, 0.2)])]
    loft("wing%d" % side, wing_st, lambda i, k: MAIN if k == 3 else DARK, subsurf=1)
    # tail fin
    fin_st = [(-1.9, [(x - 0.04, 0.4), (x + 0.04, 0.4), (x + 0.03, 0.48), (x - 0.03, 0.48)]),
              (-2.9, [(x - 0.05, 0.42), (x + 0.05, 0.42), (x + 0.03, 1.2), (x - 0.03, 1.2)])]
    loft("fin%d" % side, fin_st, lambda i, k: ACCENT, subsurf=0)
    # hover emitters under the pods
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in [(x - 0.22, 0.2, -0.47), (x + 0.22, 0.2, -0.47), (x + 0.22, -2.6, -0.45), (x - 0.22, -2.6, -0.45)]]
    f = bm.faces.new(vs)
    f.material_index = GLOW
    new_obj("hover%d" % side, bm, smooth=False)

# rear wing
rw_st = [(-2.55, [(-1.35, 0.98), (1.35, 0.98), (1.35, 1.05), (-1.35, 1.05)]),
         (-3.05, [(-1.4, 0.92), (1.4, 0.92), (1.4, 0.98), (-1.4, 0.98)])]
loft("rearwing", rw_st, lambda i, k: ACCENT if k == 2 else MAIN, subsurf=0)
for sx in (-0.55, 0.55):
    st = [(-2.6, [(sx - 0.04, 0.45), (sx + 0.04, 0.45), (sx + 0.04, 1.0), (sx - 0.04, 1.0)]),
          (-2.85, [(sx - 0.04, 0.4), (sx + 0.04, 0.4), (sx + 0.04, 0.95), (sx - 0.04, 0.95)])]
    loft("strut", st, lambda i, k: DARK, subsurf=0)

# nose sensor + belly glow strip + headlights
for (verts, part) in [
    ([(-0.06, 3.3, 0.0), (0.06, 3.3, 0.0), (0.06, 3.0, 0.1), (-0.06, 3.0, 0.1)], GLOW),
    ([(-0.3, 1.4, -0.335), (0.3, 1.4, -0.335), (0.3, -1.6, -0.345), (-0.3, -1.6, -0.345)], GLOW),
    ([(-0.42, 2.25, 0.12), (-0.2, 2.45, 0.1), (-0.2, 2.45, 0.02), (-0.42, 2.25, 0.02)], GLOW),
    ([(0.42, 2.25, 0.12), (0.2, 2.45, 0.1), (0.2, 2.45, 0.02), (0.42, 2.25, 0.02)], GLOW),
    ([(-0.55, -3.06, 0.05), (0.55, -3.06, 0.05), (0.55, -3.06, 0.25), (-0.55, -3.06, 0.25)], HOT),
]:
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    f = bm.faces.new(vs)
    f.material_index = part
    new_obj("detail", bm, smooth=False)

# ---------------------------------------------------------------- export
deps = bpy.context.evaluated_depsgraph_get()
tris = []
for ob in scene.objects:
    if ob.type != "MESH":
        continue
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    mw = ob.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    cn = me.corner_normals
    for lt in me.loop_triangles:
        corners = []
        for li in lt.loops:
            v = mw @ me.vertices[me.loops[li].vertex_index].co
            n = (nm @ cn[li].vector).normalized()
            corners.append((v, n))
        tris.append((corners, lt.material_index))
    ev.to_mesh_clear()

with open(OUT, "wb") as fh:
    fh.write(b"SDM1")
    fh.write(struct.pack("<i", len(tris)))
    for corners, part in tris:
        for v, n in corners:
            fh.write(struct.pack("<6f", v.x, v.z, v.y, n.x, n.z, n.y))
        fh.write(struct.pack("<B", part))
print("wrote", len(tris), "triangles to", OUT)

if PREVIEW:
    for ob in list(scene.objects):
        pass
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (7.5, 7.0, 4.2)
    direction = Vector((0, 0, 0.2)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    light = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    light.rotation_euler = (0.8, 0.2, 0.6)
    scene.collection.objects.link(light)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.light = "STUDIO"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 600
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    print("preview", PREVIEW)
