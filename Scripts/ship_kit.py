# Shared kit for the ship builders (Scripts/build_strix.py, Scripts/build_wraith.py): materials, the Part mesh
# builder, panel surfaces and 12 mm shells with 5 mm gaps, booleans, fitted covers, decals, the report, the FBX export
# and the preview renders. Importing it starts an empty scene; start(name) names the ship (collection, materials,
# files). Front is -Y, up is +Z, metres.
import bpy
import bmesh
import math
import os
import sys
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = os.path.abspath(argv[0] if argv and not argv[0].startswith("--") else ".")
RENDER = "--no-render" not in argv
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SourceArt", "Fonts", "Orbitron-Black.ttf")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
SHIP = bpy.data.collections.new("Ship")
scene.collection.children.link(SHIP)
NAME = "Ship"
GAP = 0.005     # panel gap
SKIN = 0.012    # panel thickness
CLEAR = 0.006   # air between the inner face of a panel and the structure under it
MAT = {}
SKINS = []      # bodywork objects, hidden in the cut-away render


def start(name):
    global NAME
    NAME = name
    SHIP.name = name


# ---------------------------------------------------------------- materials
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def material(name, col, metal=0.0, rough=0.45, emit=0.0, alpha=1.0, coat=0.0):
    m = bpy.data.materials.new(NAME + "_" + name)
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
    m.diffuse_color = lin(col)
    MAT[name] = m


# ---------------------------------------------------------------- objects and groups
def group(name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.15
    e.location = loc
    SHIP.objects.link(e)
    e.parent = parent
    return e


def basis(axis):
    a = axis.normalized()
    t = Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))
    u = a.cross(t).normalized()
    return a, u, a.cross(u)


class Part:
    """bmesh being built for one object, with its own material list."""

    def __init__(self, name):
        self.name, self.bm, self.mats = name, bmesh.new(), []

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def poly(self, pts, m):
        f = self.bm.faces.new([self.bm.verts.new(p) for p in pts])
        f.material_index = self.mi(m)
        return f

    def loft(self, rows, m_fn, closed_u=False, closed_v=False, cap0=None, cap1=None):
        """Quads between rows of points (all rows the same length); m_fn(i, j) names each face's material."""
        V = [[self.bm.verts.new(p) for p in row] for row in rows]
        nu, nv = len(rows[0]), len(rows)
        for i in range(nv if closed_v else nv - 1):
            for j in range(nu if closed_u else nu - 1):
                i2, j2 = (i + 1) % nv, (j + 1) % nu
                f = self.bm.faces.new([V[i][j], V[i][j2], V[i2][j2], V[i2][j]])
                f.material_index = self.mi(m_fn(i, j))
        if cap0:
            self.bm.faces.new(V[0][::-1]).material_index = self.mi(cap0)
        if cap1:
            self.bm.faces.new(V[-1]).material_index = self.mi(cap1)
        return V

    def box(self, c, s, m, rot=None):
        vs = bmesh.ops.create_cube(self.bm, size=1.0)["verts"]
        M = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot else Matrix()) @ Matrix.Diagonal((*s, 1))
        bmesh.ops.transform(self.bm, matrix=M, verts=vs)
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = self.mi(m)

    def sphere(self, c, r, m, scale=(1, 1, 1), segs=16, rings=10):
        vs = bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=rings, radius=1.0)["verts"]
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Diagonal(
            (r * scale[0], r * scale[1], r * scale[2], 1)), verts=vs)
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = self.mi(m)

    def lathe(self, p0, p1, prof, m_fn, segs=32, closed=False, cap0=None, cap1=None, phase=0.0):
        """Surface of revolution about p0->p1; prof is [(f along the axis, radius)], m_fn(k) per band."""
        p0, p1 = Vector(p0), Vector(p1)
        ax, u, v = basis(p1 - p0)
        rows = []
        for f, r in prof:
            c = p0.lerp(p1, f)
            rows.append([c + (u * math.cos(phase + 2 * math.pi * i / segs) +
                              v * math.sin(phase + 2 * math.pi * i / segs)) * r for i in range(segs)])
        return self.loft(rows, lambda i, j: m_fn(i), closed_u=True, closed_v=closed, cap0=cap0, cap1=cap1)

    def cyl(self, p0, p1, r, m, segs=16, r1=None):
        self.lathe(p0, p1, [(0, r), (1, r if r1 is None else r1)], lambda k: m, segs, cap0=m, cap1=m)

    def tube(self, pts, r, m, segs=10, square=False):
        """Swept round (or square) tube through pts, with parallel-transport frames."""
        pts = [Vector(p) for p in pts]
        n = len(pts)
        tans = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
        _, nrm, _ = basis(tans[0])
        rows = []
        for i in range(n):
            nrm = (nrm - tans[i] * nrm.dot(tans[i])).normalized()
            bi = tans[i].cross(nrm)
            k = 4 if square else segs
            ph = math.pi / 4 if square else 0.0
            rr = r * (math.sqrt(2) if square else 1.0)
            rows.append([pts[i] + (nrm * math.cos(ph + 2 * math.pi * j / k) +
                                   bi * math.sin(ph + 2 * math.pi * j / k)) * rr for j in range(k)])
        self.loft(rows, lambda i, j: m, closed_u=True, cap0=m, cap1=m)

    def flat(self, outline_2d, M, m, holes=()):
        """Planar shape (2D outline, optional same-length hole rings) placed by matrix M."""
        if not holes:
            return self.poly([M @ Vector((x, y, 0)) for x, y in outline_2d], m)
        for h in holes:   # ring between outline and hole (both with the same point count)
            o = [M @ Vector((x, y, 0)) for x, y in outline_2d]
            i_ = [M @ Vector((x, y, 0)) for x, y in h]
            self.loft([o, i_], lambda i, j: m, closed_u=True)

    def add_mesh(self, me, M, m):
        tmp = bmesh.new()
        tmp.from_mesh(me)
        bmesh.ops.transform(tmp, matrix=M, verts=tmp.verts[:])
        vmap = [self.bm.verts.new(v.co) for v in tmp.verts]
        for f in tmp.faces:
            try:
                self.bm.faces.new([vmap[v.index] for v in f.verts]).material_index = self.mi(m)
            except ValueError:
                pass
        tmp.free()

    def finish(self, parent, bevel=0.0, recalc=True, smooth_angle=32, skin=False):
        if recalc:
            bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(MAT[m])
        ob = bpy.data.objects.new(self.name, me)
        SHIP.objects.link(ob)
        ob.parent = parent
        shade(ob, bevel, smooth_angle)
        if skin:
            SKINS.append(ob)
        return ob


def shade(ob, bevel=0.0, angle=32):
    ob.data.shade_smooth()
    ob.data.set_sharp_from_angle(angle=math.radians(angle))
    if bevel:
        b = ob.modifiers.new("Bevel", 'BEVEL')
        b.width, b.segments, b.limit_method = bevel, 2, 'ANGLE'
        b.angle_limit = math.radians(angle)
        b.harden_normals = True
        b.use_clamp_overlap = True


def bake(ob):
    """Apply the modifier stack (kept materials)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    if not me.materials:
        for m in old.materials:
            me.materials.append(m)
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def cutter(part):
    ob = part.finish(None)
    ob.hide_render = True
    return ob


def boolean(ob, cutters, op='DIFFERENCE'):
    for c in cutters:
        b = ob.modifiers.new("Bool", 'BOOLEAN')
        b.operation, b.object = op, c
        try:
            b.solver = 'EXACT'
        except TypeError:
            pass
    bake(ob)


def box_cutter(c, s, rot=None):
    p = Part("cut")
    p.box(c, s, "Black", rot)
    return cutter(p)


def drop(obs):
    for o in obs:
        me = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(me)


# ---------------------------------------------------------------- lines, sections and panels
def table(T, s):
    """Linear interpolation of the rows of T (first column the station) at station s."""
    if s <= T[0][0]:
        return list(T[0][1:])
    for a, b in zip(T, T[1:]):
        if s <= b[0]:
            f = (s - a[0]) / (b[0] - a[0])
            return [p + (q - p) * f for p, q in zip(a[1:], b[1:])]
    return list(T[-1][1:])


def pt(L, t):
    """Point at parameter t round a section loop L (integer t = key point)."""
    n = len(L)
    i = math.floor(t + 1e-9)
    f = t - i
    a, b = L[i % n], L[(i + 1) % n]
    return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f


def shift(L, t, d):
    i = math.floor(t + (1e-9 if d > 0 else -1e-9))
    a, b = Vector(L[i % len(L)]), Vector(L[(i + 1) % len(L)])
    return t + d / max((b - a).length, 1e-6)


def surface(part, loop_fn, t0, t1, s0, s1, stations, to3d, gap_s=(True, True), wrap=False):
    """Rows of points over the station range, each the stretch t0..t1 of the section loop (gaps at the ends)."""
    ss = [s0 + (GAP / 2 if gap_s[0] else 0)] + [s for s in stations if s0 + GAP < s < s1 - GAP] + \
         [s1 - (GAP / 2 if gap_s[1] else 0)]
    rows = []
    for s in ss:
        L = loop_fn(s)
        if wrap:
            ts = list(range(len(L)))
        else:
            a = t0(s) if callable(t0) else t0
            b = t1(s) if callable(t1) else t1
            ts = [shift(L, a, GAP / 2)] + list(range(math.floor(a) + 1, math.ceil(b))) + [shift(L, b, -GAP / 2)]
        rows.append([to3d(s, *pt(L, t)) for t in ts])
    part.loft(rows, lambda i, j: next(iter(MAT)), closed_u=wrap)
    return rows


def orient_out(part, centre_fn):
    bm = part.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    score = sum((f.calc_center_median() - centre_fn(f.calc_center_median())).dot(f.normal) for f in bm.faces)
    if score < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.normal_update()


def paint(part, m_fn, cuts=()):
    bm = part.bm
    for co, no in cuts:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    bm.normal_update()
    for f in bm.faces:
        f.material_index = part.mi(m_fn(f.calc_center_median(), f.normal))


def shell(part, parent, holes=(), thick=SKIN, bevel=0.0025):
    """Panel surface -> shell (inwards), then the cut-outs, then the edge bevel."""
    ob = part.finish(parent, recalc=False)
    ob.modifiers.clear()
    s = ob.modifiers.new("Skin", 'SOLIDIFY')
    s.thickness, s.offset, s.use_even_offset = thick, -1.0, True
    bake(ob)
    if holes:
        boolean(ob, holes)
    shade(ob, bevel)
    SKINS.append(ob)
    return ob


def inset(P, d):
    """Offset a closed 2D polygon inwards by d (handles either winding)."""
    area = sum(P[i - 1][0] * P[i][1] - P[i][0] * P[i - 1][1] for i in range(len(P)))
    s = 1 if area > 0 else -1
    out = []
    for i in range(len(P)):
        a, b, c = Vector(P[i - 1]), Vector(P[i]), Vector(P[(i + 1) % len(P)])
        e1, e2 = (b - a).normalized(), (c - b).normalized()
        n1, n2 = Vector((-e1.y, e1.x)) * s, Vector((-e2.y, e2.x)) * s
        p1, p2 = b + n1 * d, b + n2 * d
        den = e1.x * e2.y - e1.y * e2.x
        if abs(den) < 1e-9:
            out.append(p1)
            continue
        t = ((p2.x - p1.x) * e2.y - (p2.y - p1.y) * e2.x) / den
        out.append(p1 + e1 * t)
    return out


def split_out(ob, c, size, name, normal_axis):
    """Cut a fitted access cover out of a panel: the cover keeps a gap all round."""
    big = box_cutter(c, size)
    small_size = [v - (0 if i == normal_axis else 2 * GAP) for i, v in enumerate(size)]
    small = box_cutter(c, small_size)
    cover = ob.copy()
    cover.data = ob.data.copy()
    cover.modifiers.clear()
    cover.name = name
    SHIP.objects.link(cover)
    cover.parent = ob.parent
    boolean(cover, [small], 'INTERSECT')
    ob.modifiers.clear()
    boolean(ob, [big])
    for o in (ob, cover):
        shade(o, 0.0025)
    SKINS.append(cover)
    drop([big, small])
    return cover


# ---------------------------------------------------------------- spacecraft engine, tail cone, shark fin
def space_engine(part, c, y0, y1, r, coil_len=0.14, bell_len=0.16, glow="Emit_Plasma"):
    """Plasma thruster along +Y at c = (x, z): chamber casing y0..y1 (radius r) with an injector dome at the front,
    three magnetic coil rings with the plasma glowing between them, then a flared bell with a bright core.
    Returns the exit plane y."""
    x, z = c
    part.lathe((x, y0, z), (x, y1, z), [(0, r), (0.55, r), (0.55, r + 0.008), (0.6, r + 0.008), (0.6, r), (1, r)],
               lambda k: "Metal", 32, cap0="Graphite", cap1="Graphite")
    part.lathe((x, y0 - 0.06, z), (x, y0, z), [(0, 0.0), (0.5, 0.5 * r), (1, 0.8 * r)], lambda k: "Metal_Bright", 24)
    yb = y1 + coil_len
    part.lathe((x, y1, z), (x, yb, z), [(0, 0.76 * r), (1, 0.76 * r)], lambda k: glow, 32)          # plasma sleeve
    for k in range(3):                                                                                  # coils
        ya = y1 + coil_len * (0.04 + 0.33 * k)
        part.lathe((x, ya, z), (x, ya + coil_len * 0.22, z), [(0, 0.80 * r), (0, 1.02 * r), (1, 1.02 * r),
                   (1, 0.80 * r)], lambda k_: "Metal_Bright", 32, closed=True)
    for k in range(4):                                                                                  # tie rods
        a = math.pi / 4 + k * math.pi / 2
        part.box((x + 0.97 * r * math.cos(a), y1 + coil_len / 2, z + 0.97 * r * math.sin(a)),
                 (0.022, coil_len + 0.01, 0.022), "Metal", Matrix.Rotation(-a, 3, 'Y'))
    ye = yb + bell_len
    part.lathe((x, yb, z), (x, ye, z), [(0, 0.86 * r), (0.5, 0.96 * r), (1, 1.08 * r), (1, 1.0 * r), (0.5, 0.80 * r),
               (0, 0.62 * r)], lambda k: "Ceramic" if k < 2 else "Metal_Bright" if k == 2 else "Graphite", 32,
               closed=True)                                                                             # bell
    part.lathe((x, yb + 0.01, z), (x, yb + 0.011, z), [(0, 0.0), (1, 0.63 * r)], lambda k: glow, 32)   # core
    part.lathe((x, yb + 0.01, z), (x, yb + 0.6 * bell_len, z), [(0, 0.35 * r), (1, 0.04 * r)], lambda k: glow, 16)
    return ye


def tail_loop(outline, centre, r_end, y0, y1, per_m=30, power=2.0):
    """Section loop of a tail cone that runs from a body outline (closed 2D polygon starting at the bottom centre,
    going round counter-clockwise) at y0 to a ring of radius r_end round centre at y1. Edges are split in proportion
    to their length so the corners stay, the ring angles follow the arc length, and the blend starts slowly so the
    cone leaves the body without a crease. Returns (loop function of y, loop index of each outline corner)."""
    P = [Vector(p) for p in outline]
    pts, idx = [], []
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        idx.append(len(pts))
        k = max(1, round((b - a).length * per_m))
        pts += [a.lerp(b, j / k) for j in range(k)]
    L = [0.0]
    for i in range(1, len(pts) + 1):
        L.append(L[-1] + (pts[i % len(pts)] - pts[i - 1]).length)
    c = Vector(centre)
    ring = [c + Vector((math.cos(-math.pi / 2 + 2 * math.pi * L[i] / L[-1]),
                        math.sin(-math.pi / 2 + 2 * math.pi * L[i] / L[-1]))) * r_end for i in range(len(pts))]

    def f(y):
        e = min(max((y - y0) / (y1 - y0), 0.0), 1.0) ** power
        return [tuple(p.lerp(q, e)) for p, q in zip(pts, ring)]
    return f, idx


def shark_fin(part, base_fn, x0, root, tip, height, thick, m_skin, m_edge, cant=0.0, side=1, rows=7):
    """Long swept fin standing on the surface z = base_fn(y) at x = x0: root and tip are (y_le, y_te). Lens section
    thinning to the top, convex leading edge, concave trailing edge, small semi-pointed tip; canted outwards."""
    up = Vector((side * math.sin(cant), 0, math.cos(cant)))
    across = Vector((math.cos(cant), 0, -side * math.sin(cant)))
    secs = []
    for j in range(rows):
        f = j / (rows - 1)
        le = root[0] + (tip[0] - root[0]) * f ** 0.8
        te = root[1] + (tip[1] - root[1]) * f ** 1.5
        if j == rows - 1:
            le, te = le + 0.4 * (te - le), te - 0.35 * (te - le)
        c, t = te - le, thick * (1 - 0.65 * f)
        sec = [(le, 0), (le + .06 * c, .3 * t), (le + .35 * c, .5 * t), (te - .15 * c, .15 * t), (te, 0),
               (te - .15 * c, -.15 * t), (le + .35 * c, -.5 * t), (le + .06 * c, -.3 * t)]
        secs.append([Vector((x0, y, base_fn(y) - 0.01)) + up * (height * f) + across * v for y, v in sec])
    part.loft(secs, lambda i, j: m_edge if j in (0, 7) else m_skin, closed_u=True, cap0=m_skin, cap1=m_edge)
    sp = (root[0] + 0.4 * (root[1] - root[0]), tip[0] + 0.4 * (tip[1] - tip[0]))                     # spar
    part.tube([Vector((x0, sp[0], base_fn(sp[0]) - 0.05)), Vector((x0, sp[1], base_fn(sp[1]))) + up * height * 0.8],
              thick * 0.18, "Metal", 8)


# ---------------------------------------------------------------- decals
_font = []


def text_mesh(body, size):
    if not _font:
        _font.append(bpy.data.fonts.load(FONT_PATH) if os.path.exists(FONT_PATH) else None)
    cu = bpy.data.curves.new("txt", 'FONT')
    cu.body, cu.size, cu.align_x, cu.align_y = body, size, 'CENTER', 'CENTER'
    if _font[0]:
        cu.font = _font[0]
    ob = bpy.data.objects.new("txt", cu)
    SHIP.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return me


def frame_on(origin, u, v, lift=0.0025):
    """Matrix placing 2D decal geometry on a surface: x along u, y along v, lifted along the normal."""
    u, v = Vector(u).normalized(), Vector(v).normalized()
    n = u.cross(v).normalized()
    v = n.cross(u)
    M = Matrix((u, v, n)).transposed().to_4x4()
    M.translation = Vector(origin) + n * lift
    return M


def ring2d(r0, r1, n=40):
    return ([(r1 * math.cos(2 * math.pi * k / n), r1 * math.sin(2 * math.pi * k / n)) for k in range(n)],
            [(r0 * math.cos(2 * math.pi * k / n), r0 * math.sin(2 * math.pi * k / n)) for k in range(n)])


def disc2d(r, n=40):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---------------------------------------------------------------- report, save, export, renders
def finish_ship(decals=None, cockpit=((-1.6, -2.2, 1.7), (0, -0.1, 0.80))):
    """Print the size, save <name>.blend, export <name>.fbx and (unless --no-render) the preview renders."""
    stem = NAME.lower()
    dg = bpy.context.evaluated_depsgraph_get()
    tris, lo, hi = 0, Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in SHIP.objects:
        if o.type == 'MESH' and not o.hide_render:
            me = o.evaluated_get(dg).to_mesh()
            tris += sum(len(p.vertices) - 2 for p in me.polygons)
            for v in me.vertices:
                w = o.matrix_world @ v.co
                lo = Vector(map(min, lo, w))
                hi = Vector(map(max, hi, w))
            o.evaluated_get(dg).to_mesh_clear()
    print("%s objects %d  tris %d  size %.2f x %.2f x %.2f m  z %.2f..%.2f" % (
        NAME, sum(1 for o in SHIP.objects if o.type == 'MESH'), tris, *(hi - lo), lo.z, hi.z))

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, stem + ".blend"), compress=True)
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[SHIP.name]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, stem + ".fbx"), use_active_collection=True,
                             object_types={'EMPTY', 'MESH'}, use_mesh_modifiers=True, mesh_smooth_type='FACE',
                             add_leaf_bones=False, apply_unit_scale=True, use_custom_props=False)
    if not RENDER:
        return

    studio = bpy.data.collections.new("Studio")
    scene.collection.children.link(studio)
    r = scene.render
    r.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    r.resolution_x, r.resolution_y = 1400, 800
    r.image_settings.file_format = 'JPEG'
    r.image_settings.quality = 90
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.exposure = -1.1
    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.64, 0.67, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    scene.world = world
    gm = bpy.data.materials.new("Floor")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.30, 0.31, 0.33, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.7
    fme = bpy.data.meshes.new("Floor")
    fme.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
    fme.materials.append(gm)
    studio.objects.link(bpy.data.objects.new("Floor", fme))

    def light(name, loc, power, size):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy, ld.size = power, size
        lo_ = bpy.data.objects.new(name, ld)
        lo_.location = loc
        lo_.rotation_euler = (Vector((0, 0, 0.5)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        studio.objects.link(lo_)

    light("Key", (-5, -6, 7), 2600, 5)
    light("Fill", (6, -3, 3), 900, 6)
    light("Rim", (2, 8, 5), 1600, 4)
    cam_d = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_d)
    studio.objects.link(cam)
    scene.camera = cam

    def shot(name, loc, target=None, lens=50, ortho=None, rot=None):
        cam.location = loc
        cam.rotation_euler = rot or (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        cam_d.type = 'ORTHO' if ortho else 'PERSP'
        if ortho:
            cam_d.ortho_scale = ortho
        cam_d.lens = lens
        r.filepath = os.path.join(OUT, "%s_%s.jpg" % (stem, name))
        bpy.ops.render.render(write_still=True)

    shot("34_front", (-6.2, -7.4, 4.0), (0, -0.2, 0.55), 55)
    shot("34_rear", (5.8, 6.8, 3.2), (0, 0.4, 0.6), 55)
    shot("side", (-12, 0, 0.62), (0, 0, 0.62), ortho=7.0)
    shot("top", (0, 0, 12), ortho=7.0, rot=(0, 0, math.radians(90)))
    shot("front", (0, -12, 0.65), (0, 0, 0.65), ortho=3.6)
    shot("cockpit", cockpit[0], cockpit[1], 45)
    for o in SKINS + [o for o in SHIP.objects if decals and o.parent == decals]:
        o.hide_render = True
    shot("inside", (-6.2, -7.4, 4.0), (0, -0.2, 0.55), 55)
