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

    def sweep(self, c, y0, y1, prof, sec, m_fn, closed=False, cap0=None, cap1=None):
        """Like lathe, along +Y at c = (x, z), round any closed section sec [(x, z)] scaled by s for each (f, s)."""
        x, z = c
        rows = [[Vector((x + px * sc, y0 + (y1 - y0) * f, z + pz * sc)) for px, pz in sec] for f, sc in prof]
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


def loop10(xc, w, zb, cb, zs, ct, zt):
    """Faceted body section round x = xc (bottom chamfer cb, top chamfer ct), counter-clockwise from the bottom centre:
    10 points, t 0..10 (t 2..3 the right side, 3..7 the top with its chamfers, 9..11 the belly)."""
    r = [(0, zb), (w - cb, zb), (w, zb + cb), (w, zs), (w - ct, zt), (0, zt)]
    return [(xc + x, z) for x, z in r] + [(xc - x, z) for x, z in reversed(r[1:-1])]


def block_loop(hb, zd, hs, ht, htop):
    """Raised block standing on a deck at zd (open at the base) - a spine, a cabin, a boom: from the right base round
    the top to the left base, 7 points, t 0..6 (t 0..1 the right side, 1..5 the top with its chamfers)."""
    r = [(hb, zd), (hb, hs), (ht, htop), (0, htop)]
    return r + [(-x, z) for x, z in reversed(r[:-1])]


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
def circle_loop(r, n=32):
    """Round section, counter-clockwise from the bottom centre."""
    return [(r * math.cos(-math.pi / 2 + 2 * math.pi * k / n), r * math.sin(-math.pi / 2 + 2 * math.pi * k / n))
            for k in range(n)]


def shape_loop(hw_bottom, hw_top, hh, r=0.0, n=48):
    """Engine or duct section round (0, 0), counter-clockwise from the bottom centre: a four-sided shape with its own
    bottom and top half widths and half height (a rectangle when they match, narrowing upwards when the top is
    narrower), corners rounded by r; resampled to n points evenly along its length."""
    P = [Vector((hw_bottom, -hh)), Vector((hw_top, hh)), Vector((-hw_top, hh)), Vector((-hw_bottom, -hh))]
    pts = [Vector((0, -hh))]
    for i, p in enumerate(P):
        a, b = P[i - 1] if i else Vector((0, -hh)), P[(i + 1) % 4]
        u1, u2 = (a - p).normalized(), (b - p).normalized()
        th = math.acos(max(-1.0, min(1.0, u1.dot(u2))))
        if r <= 0 or th < 1e-3:
            pts.append(p)
            continue
        d = r / math.tan(th / 2)
        t1, t2 = p + u1 * d, p + u2 * d
        cen = p + (u1 + u2).normalized() * (r / math.sin(th / 2))
        a1, a2 = math.atan2(t1.y - cen.y, t1.x - cen.x), math.atan2(t2.y - cen.y, t2.x - cen.x)
        while a2 < a1:
            a2 += 2 * math.pi
        pts += [cen + Vector((math.cos(a1 + (a2 - a1) * k / 8), math.sin(a1 + (a2 - a1) * k / 8))) * r for k in range(9)]
    L = [0.0]
    for i in range(1, len(pts) + 1):
        L.append(L[-1] + (pts[i % len(pts)] - pts[i - 1]).length)
    out = []
    for k in range(n):
        q = L[-1] * k / n
        i = max(j for j in range(len(pts)) if L[j] <= q)
        seg = L[i + 1] - L[i]
        out.append(tuple(pts[i].lerp(pts[(i + 1) % len(pts)], (q - L[i]) / seg if seg else 0)))
    return out


def loop_at(loop, q):
    """Point at fraction q (0..1) of the length of a closed loop."""
    P = [Vector(p) for p in loop]
    L = [0.0]
    for i in range(1, len(P) + 1):
        L.append(L[-1] + (P[i % len(P)] - P[i - 1]).length)
    t = (q % 1.0) * L[-1]
    i = max(j for j in range(len(P)) if L[j] <= t)
    seg = L[i + 1] - L[i]
    return P[i].lerp(P[(i + 1) % len(P)], (t - L[i]) / seg if seg else 0)


def space_engine(part, c, y0, y1, sec, coil_len=0.14, bell_len=0.16, glow="Emit_Plasma"):
    """Plasma thruster along +Y at c = (x, z) with any closed section sec (round, rectangular, narrowing...): chamber
    casing y0..y1 with an injector dome at the front, three magnetic coils with the plasma glowing between them, then
    a flared bell with a bright core. Returns the exit plane y."""
    x, z = c
    part.sweep(c, y0, y1, [(0, 1), (0.55, 1), (0.55, 1.035), (0.6, 1.035), (0.6, 1), (1, 1)], sec,
               lambda k: "Metal", cap0="Graphite", cap1="Graphite")
    part.sweep(c, y0 - 0.06, y0, [(0, 0.0), (0.5, 0.5), (1, 0.8)], sec, lambda k: "Metal_Bright")
    yb = y1 + coil_len
    part.sweep(c, y1, yb, [(0, 0.76), (1, 0.76)], sec, lambda k: glow)                                # plasma sleeve
    for k in range(3):                                                                                 # coils
        ya = y1 + coil_len * (0.04 + 0.33 * k)
        part.sweep(c, ya, ya + coil_len * 0.22, [(0, 0.80), (0, 1.02), (1, 1.02), (1, 0.80)], sec,
                   lambda k_: "Metal_Bright", closed=True)
    for k in range(4):                                                                                 # tie rods
        px, pz = loop_at(sec, 0.125 + 0.25 * k) * 0.97
        part.box((x + px, y1 + coil_len / 2, z + pz), (0.022, coil_len + 0.01, 0.022), "Metal")
    ye = yb + bell_len
    part.sweep(c, yb, ye, [(0, 0.86), (0.5, 0.96), (1, 1.08), (1, 1.0), (0.5, 0.80), (0, 0.62)], sec,
               lambda k: "Ceramic" if k < 2 else "Metal_Bright" if k == 2 else "Graphite", closed=True)    # bell
    part.sweep(c, yb + 0.01, yb + 0.011, [(0, 0.0), (1, 0.63)], sec, lambda k: glow)                    # core
    part.sweep(c, yb + 0.01, yb + 0.6 * bell_len, [(0, 0.35), (1, 0.04)], sec, lambda k: glow)
    return ye


def tail_loop(outline, centre, end, y0, y1, per_m=30, power=2.0):
    """Section loop of a tail cone that runs from a body outline (closed 2D polygon starting at the bottom centre,
    going round counter-clockwise) at y0 to the end section at y1 (a closed loop round centre, from its bottom centre,
    or a radius for a ring). Edges are split in proportion to their length so the corners stay, points meet the end at
    the same fraction of the length, and the blend starts slowly so the cone leaves the body without a crease.
    Returns (loop function of y, loop index of each outline corner)."""
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
    end = circle_loop(end, 64) if isinstance(end, (int, float)) else end
    c = Vector(centre)
    ring = [c + loop_at(end, L[i] / L[-1]) for i in range(len(pts))]

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


# ---------------------------------------------------------------- pilots
# Every ship has a pilot of its own (player, 2026-10-27): a human body of the ship's kind, a face behind the visor and a
# helmet of its own. The body is built from real measurements, the ANSUR II survey of US Army men (means, mm): the
# girths of the neck, upper arm, forearm, wrist, thigh, knee, calf and ankle, the breadths and depths of the shoulders,
# chest, waist and hips, the lengths of the arm and leg bones, the hand and the foot. They are scaled to the cockpit by
# the helmet (a racing helmet is ~290 mm across), then by the pilot's build: g = girth, l = length, sh = shoulders,
# chest, belly. The pose is the cockpit's: hips on the seat, back on the rest, head under the glass, hands on the grips;
# the elbows and knees are placed by two-bone IK from the real bone lengths.
BODY = dict(neck=397, biceps=357, forearm=301, wrist=175, thigh=620, knee=390, calf=392, ankle=228,
            bideltoid=490, chest_b=323, chest_d=255, waist_b=312, waist_d=240, hip_b=347, hip_d=230,
            upper_arm=340, lower_arm=265, thigh_len=430, shin_len=430, hip_joints=170,
            hand_b=89, foot_len=270, foot_b=101, ankle_h=85, helmet=290)

PILOTS = {
    # VORTEX: the ace, tall and slim (long limbs, narrow shoulders, thin girths); a long red teardrop helmet with a
    # crest and a wrap-around visor.
    "vortex": dict(g=0.80, l=1.07, sh=0.94, chest=0.95, belly=0.90, R=1.0, helmet="ace", suit="#ECEDEF",
                   trim="#E2502E", under="#26292D", shell="#E2502E", shell2="#ECEDEF", skin="#E8B898", brow="#6B4528",
                   face=(0.76, 0.94, 1.08)),
    # BASTION: medium height but strong (broad chest and shoulders, thick arms and legs, shoulder pads); a heavy round
    # helmet with a chin bar, a brow ridge, side vents and a narrow visor slit.
    "bastion": dict(g=1.26, l=0.97, sh=1.14, chest=1.10, belly=1.0, R=1.04, helmet="tank", suit="#4A5560",
                    trim="#E9A720", under="#202428", shell="#E9A720", shell2="#3B4650", skin="#6A432E",
                    brow="#1C130E", pads=True, face=(0.86, 0.92, 1.0)),
    # STRIX: the athlete, a classic racer; round full-face helmet with a centre stripe and a small rear spoiler.
    "strix": dict(g=1.0, l=1.0, sh=1.0, chest=1.0, belly=0.95, R=1.0, helmet="racer", suit="#2F6FB8", trim="#F5C200",
                  under="#1C2531", shell="#F5C200", shell2="#1D5FA6", skin="#C98E68", brow="#3A2618",
                  face=(0.80, 0.92, 1.04)),
    # WRAITH: the hunter, lean and quick; an angular faceted helmet, a V visor and two swept-back horns.
    "wraith": dict(g=0.88, l=1.02, sh=0.96, chest=0.97, belly=0.90, R=1.0, helmet="hunter", suit="#2C3A33",
                   trim="#2E8F52", under="#1A201D", shell="#E4EBE6", shell2="#2E8F52", skin="#B98A62",
                   brow="#2A1C12", face=(0.78, 0.92, 1.04)),
    # NOMAD: the veteran, stocky with a belly and a grey beard; a big round helmet, a bubble visor, lamps, an air hose.
    "nomad": dict(g=1.12, l=0.96, sh=1.02, chest=1.04, belly=1.22, R=1.02, helmet="veteran", suit="#D8D2C4",
                  trim="#E8702A", under="#2B2D30", shell="#E8702A", shell2="#E9EBED", skin="#A26D4C", brow="#8E8C88",
                  beard="#A3A19C", face=(0.84, 0.94, 1.0)),
}

# Helmets: racing helmets, not round ones (player, 2026-10-27: "parece astronauta"). Each is built from a side profile
# like a real full-face helmet (helmet radii from the head's centre; ahead is -y): at each height zs the front (chin,
# visor, brow, crown), the back (nape, tail) and the half width, sliced in super-ellipses (p: blunt 2+, pointed <2,
# the front and the back apart). The eye port is cut out of the shell (eye(a, z), a the angle from straight ahead in
# degrees, z in helmet radii) and a smoked visor sits over it; two(a, z) paints the second colour.
HELMET_Z = [-0.95, -0.80, -0.60, -0.35, -0.10, 0.15, 0.40, 0.65, 0.85, 0.97]
HELMETS = {
    # VORTEX: time-trial teardrop, a long pointed tail with a dorsal fin, a narrow wrap-round slit, red iridium visor
    "ace": dict(front=[0.66, 0.96, 1.02, 0.98, 0.90, 0.90, 0.84, 0.66, 0.40, 0.08],
                back=[0.80, 1.00, 1.20, 1.50, 1.72, 1.66, 1.30, 0.90, 0.48, 0.10],
                width=[0.64, 0.74, 0.80, 0.82, 0.82, 0.80, 0.74, 0.62, 0.42, 0.10], pf=2.1, pb=1.35,
                eye=lambda a, z: abs(a) < 76 and 0.0 + abs(a) * 0.0006 < z < 0.17 - abs(a) * 0.0008,
                two=lambda a, z: (abs(a) > 120 and z > 0.25) or z < -0.62, visor="#8A2E14"),
    # STRIX: F1 style, a strong chin, a flat-topped visor, a Gurney spoiler at the back, an air box on top, a stripe
    "racer": dict(front=[0.72, 1.02, 1.08, 1.02, 0.93, 0.93, 0.86, 0.68, 0.42, 0.08],
                  back=[0.82, 0.96, 1.02, 1.05, 1.06, 1.04, 0.96, 0.80, 0.50, 0.10],
                  width=[0.68, 0.80, 0.86, 0.88, 0.88, 0.87, 0.82, 0.70, 0.48, 0.10], pf=1.9, pb=2.2,
                  eye=lambda a, z: abs(a) < 60 and -0.12 < z < 0.22,
                  two=lambda a, z: z > 0.30 and (abs(a) < 9 or abs(a) > 171), visor="#1A2430"),
    # WRAITH: angular aero, faceted, a V visor, a pointed tail with two fins
    "hunter": dict(front=[0.70, 1.00, 1.06, 1.00, 0.92, 0.92, 0.84, 0.64, 0.38, 0.08],
                   back=[0.80, 0.98, 1.08, 1.25, 1.40, 1.34, 1.08, 0.80, 0.46, 0.10],
                   width=[0.64, 0.76, 0.82, 0.84, 0.84, 0.82, 0.76, 0.62, 0.42, 0.10], pf=1.6, pb=1.4, n=(12, 10),
                   eye=lambda a, z: abs(a) < 64 and -0.16 + abs(a) * 0.0025 < z < 0.08 + abs(a) * 0.0035,
                   two=lambda a, z: z < -0.55 or (abs(a) > 120 and z > 0.15), visor="#0F3524"),
    # BASTION: armoured, a big square jaw, a narrow slit under a brow ridge, side vents
    "tank": dict(front=[0.86, 1.16, 1.20, 1.10, 0.98, 0.96, 0.92, 0.76, 0.48, 0.10],
                 back=[0.86, 1.00, 1.04, 1.06, 1.06, 1.04, 0.98, 0.84, 0.54, 0.12],
                 width=[0.82, 0.92, 0.96, 0.96, 0.96, 0.95, 0.90, 0.78, 0.54, 0.12], pf=2.8, pb=2.6,
                 eye=lambda a, z: abs(a) < 46 and 0.02 < z < 0.17,
                 two=lambda a, z: z < -0.42, visor="#141414"),
    # NOMAD: rally/enduro, a long beaked chin with a vent, a peak over the visor, lamps on the sides
    "veteran": dict(front=[0.86, 1.28, 1.26, 1.06, 0.94, 0.94, 0.88, 0.70, 0.44, 0.08],
                    back=[0.84, 0.98, 1.02, 1.04, 1.04, 1.02, 0.96, 0.82, 0.52, 0.10],
                    width=[0.62, 0.74, 0.84, 0.88, 0.88, 0.88, 0.84, 0.72, 0.50, 0.10], pf=1.5, pb=2.2,
                    eye=lambda a, z: abs(a) < 58 and -0.16 < z < 0.25,
                    two=lambda a, z: z > 0.58, visor="#3A2A12"),
}

# Torso stations along the spine (0 = hips on the seat, 1 = base of the neck): half width, front and back depth, as
# fractions of the measured hip, waist, chest and shoulder sizes (the pecs and the lats out, the waist in, the
# trapezius sloping to the neck).
TORSO = [  # u, width source, width, front source, front, back
    (-0.14, "hip_b", 0.42, "hip_d", 0.40, 0.44),
    (0.00, "hip_b", 0.50, "hip_d", 0.48, 0.54),
    (0.24, "waist_b", 0.50, "waist_d", 0.50, 0.42),
    (0.44, "chest_b", 0.50, "chest_d", 0.48, 0.44),
    (0.60, "chest_b", 0.53, "chest_d", 0.54, 0.46),
    (0.76, "bideltoid", 0.40, "chest_d", 0.47, 0.44),
    (0.89, "bideltoid", 0.30, "chest_d", 0.33, 0.36),
    (1.00, "neck", 0.21, "neck", 0.15, 0.16),
]
ARM_PROFILE = [(0.0, 1.12), (0.10, 1.13), (0.22, 1.0), (0.32, 1.03), (0.42, 0.86), (0.50, 0.80), (0.58, 0.88),
               (0.67, 0.90), (0.80, 0.72), (0.94, 0.54), (1.0, 0.50)]           # x the biceps radius
LEG_PROFILE = [(0.0, 1.0), (0.10, 1.02), (0.25, 0.93), (0.40, 0.74), (0.50, 0.66), (0.58, 0.64), (0.68, 0.66),
               (0.80, 0.55), (0.93, 0.40), (1.0, 0.38)]                           # x the thigh radius


def _prof(P, t):
    for (t0, v0), (t1, v1) in zip(P, P[1:]):
        if t <= t1:
            f = (t - t0) / max(1e-6, t1 - t0)
            f = f * f * (3 - 2 * f)
            return v0 + (v1 - v0) * f
    return P[-1][1]


def _catmull(pts, t):
    """Point at t (0..1) on a Catmull-Rom curve through pts (ends repeated); each span is an equal share of t."""
    n = len(pts) - 1
    i = min(int(t * n), n - 1)
    f = t * n - i
    p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n)]
    return 0.5 * (2 * p1 + (p2 - p0) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f
                  + (3 * p1 - p0 - 3 * p2 + p3) * f ** 3)


def _ik(a, b, l1, l2, pole):
    """Middle joint of a two-bone chain from a to b (bone lengths l1, l2), bent towards pole."""
    d = (b - a).length
    if d >= (l1 + l2) * 0.995:
        s = d / ((l1 + l2) * 0.995)
        l1, l2 = l1 * s, l2 * s
    x = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(l1 * l1 - x * x, 0.0))
    u = (b - a) / d
    p = (pole - u * pole.dot(u)).normalized()
    return a + u * x + p * h


def _limb(part, ctrl, prof, r, m, flat=0.93, steps=26, n=16, side=None):
    """A limb lofted along a Catmull-Rom curve through ctrl, its radius r x prof(t), slightly flattened sideways."""
    pts = [_catmull(ctrl, i / steps) for i in range(steps + 1)]
    tans = [(pts[min(i + 1, steps)] - pts[max(i - 1, 0)]).normalized() for i in range(steps + 1)]
    nrm = side or Vector((1, 0, 0))
    rows = []
    for i, p in enumerate(pts):
        nrm = (nrm - tans[i] * nrm.dot(tans[i])).normalized()
        bi = tans[i].cross(nrm)
        rr = r * _prof(prof, i / steps)
        rows.append([p + nrm * math.cos(2 * math.pi * k / n) * rr * flat + bi * math.sin(2 * math.pi * k / n) * rr
                     for k in range(n)])
    part.loft(rows, lambda i, j: m if isinstance(m, str) else m(i / steps, j), closed_u=True, cap0=None, cap1=None)
    return pts, tans


def _ell(part, c, ax, ay, az, m, segs=16, rings=10):
    """Ellipsoid at c with half-axes the vectors ax, ay, az."""
    vs = bmesh.ops.create_uvsphere(part.bm, u_segments=segs, v_segments=rings, radius=1.0)["verts"]
    M = Matrix((ax, ay, az)).transposed().to_4x4()
    M.translation = Vector(c)
    bmesh.ops.transform(part.bm, matrix=M, verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = part.mi(m)


def pilot(parent, torso, head, helmet_r, arm, leg, kind=None, max_w=None):
    """The ship's pilot in the pose its cockpit was laid out for. torso: hips, chest, base of the neck; head: centre of
    the helmet; arm: shoulder, elbow, hand on the grip; leg: hip, knee, foot (right side, +x; mirrored). The hips, the
    neck, the head and the grips are kept; elbows, knees and feet come from the real bone lengths. max_w: the half
    width the shoulders may take in the seat."""
    P = PILOTS[kind or NAME.lower()]
    for nm, col, kw in (("Pilot_Suit", P["suit"], dict(rough=0.6)), ("Pilot_Trim", P["trim"], dict(rough=0.45)),
                        ("Pilot_Under", P["under"], dict(rough=0.75)), ("Pilot_Skin", P["skin"], dict(rough=0.55)),
                        ("Pilot_Brow", P["brow"], dict(rough=0.85)), ("Pilot_Eye", "#16120F", dict(rough=0.15)),
                        ("Pilot_EyeWhite", "#EDE8E2", dict(rough=0.3)),
                        ("Pilot_Beard", P.get("beard", P["brow"]), dict(rough=0.9)),
                        ("Pilot_Metal", "#B9BEC4", dict(metal=1.0, rough=0.3)),
                        ("Pilot_Helmet", P["shell"], dict(rough=0.22, coat=0.7)),
                        ("Pilot_Helmet2", P["shell2"], dict(rough=0.28, coat=0.6)),
                        ("Pilot_Visor", HELMETS[P["helmet"]]["visor"], dict(metal=0.4, rough=0.05, alpha=0.62)),
                        ("Pilot_Lamp", "#FFF2D0", dict(emit=6.0, rough=0.2))):
        if nm not in MAT:
            material(nm, col, **kw)
    X, UP, FWD = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0))
    k = helmet_r / (BODY["helmet"] / 2000.0)            # the cockpit's scale of a real man
    g, ln = P["g"], P["l"]

    def mm(key, girth=True):
        """A measurement in metres at this pilot's scale; girths become radii."""
        v = BODY[key] / 1000.0 * k
        return v / (2 * math.pi) * g if girth else v

    body = Part("Pilot")

    # ---- torso: a loft through the stations, super-elliptic sections (the suit over a muscled body)
    hip, chest, neck = (Vector(p) for p in torso)
    spine = [hip - (chest - hip).normalized() * 0.001, hip, chest, neck, neck + (neck - chest).normalized() * 0.001]

    def sp(u):
        """Point on the spine at u (0 hips, 1 neck; below 0 and above 1 straight on)."""
        if u < 0:
            return hip + (hip - chest).normalized() * (-u) * (neck - hip).length
        if u > 1:
            return neck + (neck - chest).normalized() * (u - 1) * (neck - hip).length
        return _catmull(spine[1:4], u)

    def size(src, frac, widen=1.0):
        v = BODY[src] / 1000.0 * k * frac
        if src == "neck":
            return v / math.pi * g
        return v * widen

    wmul = {"bideltoid": g ** 0.6 * P["sh"], "chest_b": g ** 0.7 * P["chest"], "waist_b": g ** 0.8 * P["belly"],
            "hip_b": g ** 0.6, "chest_d": g ** 0.8 * P["chest"], "waist_d": g ** 0.8 * P["belly"] ** 1.4,
            "hip_d": g ** 0.6, "neck": 1.0}
    st = [(u, size(ws, w, wmul[ws]), size(ds, f, wmul[ds]), size(ds, b, wmul[ds]))
          for u, ws, w, ds, f, b in TORSO]
    if max_w:
        st = [(u, min(w, max_w * 0.93), f, b) for u, w, f, b in st]
    NT, NS, PX = 22, 28, 2.5
    rows, frames = [], []
    for i in range(NT + 1):
        u = st[0][0] + (st[-1][0] - st[0][0]) * i / NT
        c = sp(u)
        t = (sp(u + 0.02) - sp(u - 0.02)).normalized()
        fr = X.cross(t).normalized()                  # the chest side (ahead and a little up on a reclined pilot)
        w, df, db = (_prof([(s[0], s[j]) for s in st], u) for j in (1, 2, 3))
        frames.append((u, c, fr, w, df, db))
        row = []
        for j in range(NS):
            a = 2 * math.pi * j / NS
            ca, sa = math.cos(a), math.sin(a)
            x = math.copysign(abs(ca) ** (2 / PX), ca) * w
            y = math.copysign(abs(sa) ** (2 / PX), sa) * (df if sa > 0 else db)
            row.append(c + X * x + fr * y)
        rows.append(row)
    body.loft(rows, lambda i, j: "Pilot_Suit", closed_u=True, cap0="Pilot_Suit", cap1="Pilot_Under")

    def at(u):
        best = min(frames, key=lambda f: abs(f[0] - u))
        return best

    def front(u, xf, out=0.004):
        """Point on the front of the torso at u, xf of the half width out to the side."""
        _, c, fr, w, df, _ = at(u)
        y = (max(0.0, 1 - abs(xf) ** PX)) ** (1 / PX) * df
        return c + X * xf * w + fr * (y + out)

    def side(u, s, out=0.004):
        _, c, fr, w, _, _ = at(u)
        return c + X * s * (w + out)

    # suit details: harness, side stripes, belt and buckle, zipper, collar, chest patch
    for s in (-1, 1):
        body.tube([front(u, s * x) for u, x in ((0.95, 0.55), (0.86, 0.50), (0.72, 0.42), (0.58, 0.36),
                                               (0.42, 0.32), (0.26, 0.30))], 0.010 * k, "Pilot_Under", 6)
        body.tube([side(u, s) for u in (0.02, 0.2, 0.4, 0.6, 0.76)], 0.012 * k, "Pilot_Trim", 6)
    body.tube([front(0.20, x / 10, 0.006) for x in range(-10, 11, 2)], 0.016 * k, "Pilot_Under", 6)
    _, c, fr, _, df, _ = at(0.20)
    body.box(front(0.20, 0.0, 0.016), (0.06 * k, 0.02 * k, 0.04 * k), "Pilot_Metal",
             Matrix((X, fr, X.cross(fr))).transposed())
    body.tube([front(u, 0.0, 0.003) for u in (0.26, 0.45, 0.65, 0.85, 0.97)], 0.004 * k, "Pilot_Metal", 5)
    _, c, fr, w, df, _ = at(1.0)
    body.tube([c + X * w * 1.05 * math.cos(2 * math.pi * q / 14) + fr * df * 1.1 * math.sin(2 * math.pi * q / 14)
               for q in range(15)], 0.014 * k, "Pilot_Trim", 6)
    _, c, fr, _, _, _ = at(0.62)
    up_on = X.cross(fr)
    body.box(front(0.62, 0.45, 0.002), (0.07 * k, 0.045 * k, 0.004), "Pilot_Trim", Matrix((X, up_on, fr)).transposed())

    # ---- head and neck: a face behind the visor (eyes, brows, nose, mouth; a beard on the veteran)
    hc, R = Vector(head), helmet_r * P["R"]
    neck_r = mm("neck")
    body.cyl(sp(0.97), hc - UP * R * 0.35, neck_r, "Pilot_Under", 14, neck_r * 0.92)
    hh, hr = hc + FWD * R * 0.06 - UP * R * 0.06, R * 0.70
    body.sphere(hh, hr, "Pilot_Skin", P["face"], 20, 12)
    fx, fyy, fz = P["face"]
    fy = hh.y - hr * 0.80 * fyy / 0.92
    for s in (-1, 1):
        body.sphere((s * 0.30 * hr, fy + 0.02 * hr, hh.z + 0.12 * hr), 0.13 * hr, "Pilot_EyeWhite", (1.0, 0.6, 0.8),
                    12, 8)
        body.sphere((s * 0.30 * hr, fy - 0.035 * hr, hh.z + 0.12 * hr), 0.07 * hr, "Pilot_Eye", segs=10, rings=6)
        body.box((s * 0.30 * hr, fy - 0.03 * hr, hh.z + 0.27 * hr),
                 (0.30 * hr, 0.06 * hr, (0.10 if P.get("pads") else 0.06) * hr), "Pilot_Brow")
    body.sphere((0, fy - 0.10 * hr, hh.z - 0.03 * hr), 0.14 * hr, "Pilot_Skin", (0.6, 0.9, 1.0), 10, 6)
    body.box((0, fy - 0.07 * hr, hh.z - 0.33 * hr), (0.28 * hr, 0.04 * hr, 0.035 * hr), "Pilot_Brow")
    if "beard" in P:
        body.sphere((0, hh.y - 0.52 * hr, hh.z - 0.46 * hr), 0.52 * hr, "Pilot_Beard", (0.86, 0.80, 0.62), 14, 8)

    # ---- helmet: the shell from its side profile, the eye port cut out, the smoked visor, the neck rim, the pieces
    H = HELMETS[P["helmet"]]
    ZP = list(zip(HELMET_Z, H["front"])), list(zip(HELMET_Z, H["back"])), list(zip(HELMET_Z, H["width"]))

    def hp(a, z, grow=1.0):
        """Point on the helmet: a round the head (0 straight ahead, degrees), z up (helmet radii from the centre)."""
        fe, be, we = (_prof(q, z) for q in ZP)
        ar = math.radians(a)
        c, s_ = math.cos(ar), math.sin(ar)
        pp = H["pf"] if c > 0 else H["pb"]
        y = -math.copysign(abs(c) ** (2 / pp), c) * (fe if c > 0 else be)
        x = math.copysign(abs(s_) ** (2 / pp), s_) * we
        return hc + Vector((x * grow, y * grow, z)) * R

    nseg, nring = H.get("n", (40, 26))
    azs = [-180 + 360 * j / nseg for j in range(nseg)]
    zs = [HELMET_Z[0] + (HELMET_Z[-1] - HELMET_Z[0]) * i / nring for i in range(nring + 1)]
    V = [[body.bm.verts.new(hp(a, z)) for a in azs] for z in zs]
    for i in range(nring):
        for j in range(nseg):
            j2 = (j + 1) % nseg
            a = (azs[j] + 180 / nseg + 180) % 360 - 180
            z = (zs[i] + zs[i + 1]) / 2
            if H["eye"](a, z):
                continue
            f = body.bm.faces.new([V[i][j], V[i][j2], V[i + 1][j2], V[i + 1][j]])
            f.material_index = body.mi("Pilot_Helmet2" if H["two"](a, z) else "Pilot_Helmet")
    body.bm.faces.new(V[-1]).material_index = body.mi("Pilot_Helmet2" if H["two"](0, 0.99) else "Pilot_Helmet")
    # the visor: a smoked shield just over the eye port, a little bigger than it, with its pivots at the sides
    cells = [(a, z / 100) for a in range(-90, 91, 2) for z in range(-30, 40) if H["eye"](a, z / 100)]
    a1 = max(abs(a) for a, _ in cells) + 6
    z0, z1 = min(z for _, z in cells) - 0.05, max(z for _, z in cells) + 0.06
    body.loft([[hp(-a1 + 2 * a1 * q / 22, z0 + (z1 - z0) * r / 6, 1.035) for q in range(23)] for r in range(7)],
              lambda i, j: "Pilot_Visor")
    for s in (-1, 1):
        pv = hp(s * (a1 + 3), (z0 + z1) / 2, 1.0)
        out = Vector((s, 0, 0))
        body.cyl(pv, pv + out * R * 0.05, R * 0.075, "Pilot_Helmet2", 12)                       # visor pivots
    body.tube([hp(a, HELMET_Z[0] + 0.02, 0.97) for a in range(-180, 181, 12)], R * 0.07, "Pilot_Under", 8)  # rim
    style = P["helmet"]
    if style == "ace":                                          # dorsal fin along the tail
        f0, f1 = hp(180, 0.80, 1.0), hp(180, 0.15, 1.0)
        fin_d = (f1 - f0).normalized()
        body.box(f0.lerp(f1, 0.5) + UP * R * 0.06, (0.010, (f1 - f0).length * 0.95, R * 0.16), "Pilot_Helmet2",
                 Matrix((X, fin_d, X.cross(fin_d))).transposed())
    elif style == "racer":                                      # Gurney spoiler and the air box on top
        body.box(hp(180, 0.42, 1.0) + UP * R * 0.06, (R * 1.15, R * 0.06, R * 0.16), "Pilot_Helmet2")
        body.box(hp(0, 0.80, 1.0) + UP * R * 0.04, (R * 0.30, R * 0.36, R * 0.08), "Pilot_Under")
    elif style == "hunter":                                     # two fins on the tail
        for s in (-1, 1):
            b0 = hp(s * 150, 0.42, 0.98)
            out = (X * s * 0.6 + UP * 0.8).normalized()
            d_ = (hp(s * 172, 0.25, 1.0) - b0).normalized()
            body.box(b0 + out * R * 0.10, (0.010, R * 0.60, R * 0.20), "Pilot_Helmet2",
                     Matrix((out.cross(d_), d_, out)).transposed())
    elif style == "tank":
        body.tube([hp(a, 0.24, 1.05) for a in range(-62, 63, 12)], R * 0.08, "Pilot_Helmet", 8)    # brow ridge
        for q in (-1, 0, 1):
            body.box(hp(q * 12, -0.55, 1.03), (R * 0.07, R * 0.05, R * 0.24), "Pilot_Under")       # chin grille
        for s in (-1, 1):
            body.cyl(hp(s * 90, 0.0, 0.98), hp(s * 90, 0.0, 1.12), R * 0.20, "Pilot_Helmet2", 14)   # side vents
            body.cyl(hp(s * 90, 0.0, 1.12), hp(s * 90, 0.0, 1.14), R * 0.13, "Pilot_Under", 14)
    elif style == "veteran":
        angs = list(range(-60, 61, 10))
        base = [hp(a, 0.34, 1.0) for a in angs]
        tip = [p + FWD * R * 0.50 * math.cos(math.radians(a)) ** 0.5 + UP * R * 0.10 for p, a in zip(base, angs)]
        down = -UP * R * 0.025
        body.loft([base, tip, [p + down for p in tip], [p + down for p in base]], lambda i, j: "Pilot_Helmet2",
                  closed_v=True)                                                                     # peak
        body.box(hp(0, -0.62, 1.04), (R * 0.26, R * 0.10, R * 0.16), "Pilot_Under")                # chin vent
        for s in (-1, 1):
            p = hp(s * 84, 0.25, 0.98)
            body.cyl(p, p + FWD * R * 0.20, R * 0.09, "Pilot_Helmet2", 12)                           # lamps
            body.cyl(p + FWD * R * 0.20, p + FWD * R * 0.22, R * 0.07, "Pilot_Lamp", 12)
        c0 = hp(25, -0.80, 0.98)
        c2 = front(0.66, 0.35, 0.02)
        body.tube([c0, c0.lerp(c2, 0.5) + FWD * 0.05, c2], R * 0.07, "Pilot_Under", 8)               # air hose

    # ---- arms: deltoid, upper arm, elbow, forearm (IK from the real bone lengths), glove gripping the bar
    rb, rt = mm("biceps"), mm("thigh")
    a2 = Vector(arm[2])
    l0, l2 = Vector(leg[0]), Vector(leg[2])
    bar_r = 0.019
    for s in (-1, 1):
        m = Vector((s, 1, 1))
        _, c, fr, w, df, db = at(0.80)
        S = c + X * s * (w - rb * 0.55) - fr * df * 0.10
        if max_w:                                                   # the deltoids stay inside the seat's bolsters
            S.x = s * min(abs(S.x), max_w - rb * 1.5)
        G = a2 * m                                                 # the grip's centre
        back = Vector((0, 1, 0))

        def v(th):                                                 # round the bar: 0 = on top, +90 = ahead of it
            return UP * math.cos(math.radians(th)) + FWD * math.sin(math.radians(th))

        Wr = G + v(-78) * (bar_r + 0.060 * k) + UP * 0.006
        e_pole = X * s * 0.75 - UP * 0.45 + back * 0.3
        E = _ik(S, Wr, mm("upper_arm", False) * ln, mm("lower_arm", False) * ln, e_pole)
        _limb(body, [S + (S - E).normalized() * rb * 0.3, E, Wr], ARM_PROFILE, rb, "Pilot_Suit",
              side=X * s)
        _ell(body, S + X * s * rb * 0.25, X * rb * 1.25, back * rb * 1.2, UP * rb * 1.15, "Pilot_Suit")   # deltoid
        if P.get("pads"):
            _ell(body, S + X * s * rb * 0.45 + UP * rb * 0.75, X * rb * 1.45, back * rb * 1.5, UP * rb * 0.6,
                 "Pilot_Helmet2", 16, 8)                                                                  # shoulder pad
        ax = (Wr - S).normalized()
        e_out = (e_pole - ax * e_pole.dot(ax)).normalized()                     # the outside of the bend
        _ell(body, E + e_out * rb * 0.55, ax.cross(e_out) * rb * 0.62, ax * rb * 0.7, e_out * rb * 0.3,
             "Pilot_Trim", 12, 8)                                                                          # elbow pad
        wd = (Wr - E).normalized()
        body.cyl(Wr - wd * 0.022 * k, Wr + wd * 0.012 * k, rb * 0.62, "Pilot_Under", 14, rb * 0.66)       # glove cuff
        # glove: palm over the top and back of the grip, four fingers wrapped round it, the thumb under it
        hb = mm("hand_b", False) * g ** 0.5
        fr_ = hb * 0.11
        ra = bar_r + fr_
        palm_c = G + v(-40) * (ra + fr_ * 0.6)
        _ell(body, palm_c, X * hb * 0.52, (v(50)) * hb * 0.55, v(-40) * fr_ * 1.6, "Pilot_Under", 14, 8)
        for q, (dx, ln_) in enumerate(((-1.5, 0.88), (-0.5, 1.0), (0.5, 0.96), (1.5, 0.80))):
            x0 = G + X * (dx * hb * 0.235)
            arc = [x0 + v(th) * ra for th in range(0, int(150 * ln_) + 1, 25)]
            body.tube(arc, fr_, "Pilot_Under", 8)
            body.sphere(arc[-1], fr_, "Pilot_Under", segs=8, rings=6)
        tx = G - X * s * hb * 0.55
        body.tube([tx + v(th) * ra for th in (-60, -100, -140, -175)], fr_ * 1.15, "Pilot_Under", 8)

        # ---- legs: thigh, knee (pad), calf, ankle (IK from the real bone lengths, the knees up), the boot
        Hj = Vector((s * mm("hip_joints", False) / 2 * g ** 0.3, l0.y, l0.z))
        Lt, Ls = mm("thigh_len", False) * ln, mm("shin_len", False) * ln
        F0 = l2 * m
        dvec = F0 - Hj
        A = Hj + dvec.normalized() * min(dvec.length, (Lt + Ls) * 0.965)
        K = _ik(Hj, A, Lt, Ls, UP + X * s * 0.12)
        _limb(body, [Hj + (Hj - K).normalized() * rt * 0.4, K, A], LEG_PROFILE, rt, "Pilot_Suit", flat=0.97,
              side=X * s)
        kd = (K - Hj).normalized()
        ax = (A - Hj).normalized()
        kup = (UP - ax * UP.dot(ax)).normalized()                         # the outside of the bend (the knee cap)
        _ell(body, K + kup * rt * 0.50, X * rt * (0.62 if P.get("pads") else 0.52), kd * rt * 0.62,
             kup * rt * 0.24, "Pilot_Trim", 14, 8)                                                        # knee pad
        sd = (A - K).normalized()                                  # down the shin
        toe = (kup - sd * kup.dot(sd)).normalized() * math.cos(math.radians(25)) + sd * math.sin(math.radians(25))
        toe.normalize()
        sole_n = sd                                                # the sole faces down the shin
        flen, fb, ah = mm("foot_len", False), mm("foot_b", False) * g ** 0.4, mm("ankle_h", False)
        heel = A + sole_n * ah * 0.95 - toe * flen * 0.22
        bpts = []
        for i in range(13):
            t = i / 12
            wv = _prof([(0, 0.55), (0.25, 0.8), (0.7, 1.0), (0.9, 0.8), (1.0, 0.45)], t) * fb * 0.62
            hv = _prof([(0, 0.95), (0.3, 1.05), (0.6, 0.75), (0.9, 0.55), (1.0, 0.40)], t) * ah * 1.1
            cc = heel + toe * flen * 1.06 * t - sole_n * hv * 0.5
            bpts.append([cc + X * math.cos(2 * math.pi * j / 16) * wv
                         + sole_n * math.sin(2 * math.pi * j / 16) * hv * 0.5 for j in range(16)])
        body.loft(bpts, lambda i, j: "Pilot_Eye" if math.sin(2 * math.pi * (j + 0.5) / 16) > 0.55 else "Pilot_Under",
                  closed_u=True, cap0="Pilot_Under", cap1="Pilot_Under")
        body.cyl(A - sd * 0.06 * k, A + sd * 0.03 * k, mm("ankle") * 1.35, "Pilot_Under", 14,
                 mm("ankle") * 1.25)                                                                       # boot shaft
        body.cyl(A - sd * 0.075 * k, A - sd * 0.06 * k, mm("ankle") * 1.42, "Pilot_Trim", 14)             # boot cuff
    return body.finish(parent, smooth_angle=50)


# ---------------------------------------------------------------- report, save, export, renders
def finish_ship(decals=None, cockpit=((-1.6, -2.2, 1.7), (0, -0.1, 0.80)), scale=1.0):
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
        loc = Vector(loc) * scale
        target = Vector(target) * scale if target else None
        ortho = ortho * scale if ortho else None
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
