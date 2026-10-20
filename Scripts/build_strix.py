# STRIX hover racer, built from the inside out: structure first (frames, longerons, spine rails, crash box, reactor
# cradle, engine and wing mounts), then the systems on it (cockpit cell and pilot, reactor, two engines, cooling,
# hover emitters, sensors), then the bodywork panels that close over them. Every part is its own object and fits the
# one under it: panels are 12 mm shells with 5 mm gaps, the wings go through slots in the side panels onto root
# clamps, the emitters sit in cut-outs of the belly, the side intakes are ducted to the engine.
# Look: long faceted nose that is narrow and low at the front, cockpit set back, a raised spine over the reactor,
# one large engine at the centre rear, swept wings on the last third going down (Docs/STRIX_CATEGORIA.md).
# Front is -Y, up is +Z, metres (the layout of the old SourceArt/TestShips/strix.fbx; the game centres the bounds).
# Usage: python3 Scripts/build_strix.py <out_dir> [--no-render]
#    or: blender -b -P Scripts/build_strix.py -- <out_dir> [--no-render]
# Writes <out_dir>/strix.blend, strix.fbx and the preview renders.
import bpy
import bmesh
import math
import os
import sys
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = os.path.abspath(argv[0] if argv and not argv[0].startswith("--") else ".")
RENDER = "--no-render" not in argv
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(HERE, "..", "SourceArt", "Fonts", "Orbitron-Black.ttf")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
SHIP = bpy.data.collections.new("STRIX")
scene.collection.children.link(SHIP)
GAP = 0.005     # panel gap
SKIN = 0.012    # panel thickness
CLEAR = 0.006   # air between the inner face of a panel and the structure under it


# ---------------------------------------------------------------- materials
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


MAT = {}


def material(name, col, metal=0.0, rough=0.45, emit=0.0, alpha=1.0, coat=0.0):
    m = bpy.data.materials.new("STRIX_" + name)
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


material("Paint_Blue", "#3A9BDC", rough=0.3, coat=0.6)
material("Paint_DarkBlue", "#1D5FA6", rough=0.32, coat=0.6)
material("Paint_Yellow", "#F5C200", rough=0.3, coat=0.6)
material("Paint_White", "#EEF1F3", rough=0.32, coat=0.5)
material("Paint_Red", "#D7262B", rough=0.4)
material("Graphite", "#2B2E33", rough=0.6)
material("Black", "#101113", rough=0.35)
material("Metal", "#7E848B", metal=1.0, rough=0.45)
material("Metal_Bright", "#C2C7CC", metal=1.0, rough=0.22)
material("Ceramic", "#BDB6AA", rough=0.8)
material("Glass", "#9FC6DA", rough=0.03, alpha=0.25)
material("Emit_Hover", "#5FE3FF", emit=3.0, rough=0.3)
material("Emit_Hot", "#FF7A2E", emit=6.0, rough=0.3)
material("Emit_Red", "#FF2A2A", emit=4.0, rough=0.3)


# ---------------------------------------------------------------- objects and groups
def group(name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.15
    e.location = loc
    SHIP.objects.link(e)
    e.parent = parent
    return e


ROOT = group("ShipRoot")
G = {n: group(n, ROOT) for n in ("Structural_Core", "Nose", "Cockpit_Cell", "Body", "Reactor", "Propulsion",
                                 "Wing_L", "Wing_R", "Hover", "Cooling", "Decals", "Sockets")}
SKINS = []   # bodywork objects, hidden in the cut-away render


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


# ---------------------------------------------------------------- hull lines
def table(T, s):
    if s <= T[0][0]:
        return list(T[0][1:])
    for a, b in zip(T, T[1:]):
        if s <= b[0]:
            f = (s - a[0]) / (b[0] - a[0])
            return [p + (q - p) * f for p, q in zip(a[1:], b[1:])]
    return list(T[-1][1:])


#        y      w     zb    cb    zs    wt    zt        (half widths; zb belly, zs top of side, zt deck)
HULL = [(-3.15, .200, .300, .020, .360, .120, .400),
        (-2.75, .250, .292, .029, .433, .150, .505),
        (-0.75, .500, .250, .050, .600, .300, .780),
        (0.30, .560, .250, .050, .660, .360, .820),
        (1.20, .580, .250, .050, .660, .440, .740),
        (2.75, .540, .320, .040, .600, .420, .700)]
HULL_Y = [r[0] for r in HULL]
#        y     hb    hs    ht    htop      (spine over the reactor: base half width, top of side, top)
HUMP = [(0.30, .270, .930, .180, .990),
        (0.80, .300, 1.000, .200, 1.100),
        (1.20, .340, 1.060, .230, 1.190),
        (1.70, .340, 1.090, .240, 1.245),
        (2.75, .340, 1.090, .240, 1.245)]
HUMP_Y = [r[0] for r in HUMP]


def hull(y):
    return dict(zip(("w", "zb", "cb", "zs", "wt", "zt"), table(HULL, y)))


def hump(y):
    return dict(zip(("hb", "hs", "ht", "htop"), table(HUMP, y)))


def hull_loop(y):
    h = hull(y)
    r = [(0, h["zb"]), (h["w"] - h["cb"], h["zb"]), (h["w"], h["zb"] + h["cb"]), (h["w"], h["zs"]),
         (h["wt"], h["zt"]), (0, h["zt"])]
    return r + [(-x, z) for x, z in reversed(r[1:-1])]          # 10 points, t 0..10 round the section


def hump_loop(y):
    h, zd = hump(y), hull(y)["zt"]
    r = [(h["hb"], zd), (h["hb"], h["hs"]), (h["ht"], h["htop"]), (0, h["htop"])]
    return r + [(-x, z) for x, z in reversed(r[:-1])]          # 7 points, t 0..6 (open at the base)


def pt(L, t):
    n = len(L)
    i = math.floor(t + 1e-9)
    f = t - i
    a, b = L[i % n], L[(i + 1) % n]
    return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f


def shift(L, t, d):
    i = math.floor(t + (1e-9 if d > 0 else -1e-9))
    a, b = Vector(L[i % len(L)]), Vector(L[(i + 1) % len(L)])
    return t + d / max((b - a).length, 1e-6)


def tx(y, x):   # t on the hull deck (segment 4-5, right side) where the deck is at half width x
    wt = hull(y)["wt"]
    return 4 + (wt - x) / wt


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
    part.loft(rows, lambda i, j: "Paint_Blue", closed_u=wrap)
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
    """Panel surface -> 12 mm shell (inwards), then the cut-outs, then the edge bevel."""
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


def hull3d(y, x, z):
    return Vector((x, y, z))


def hull_centre(c):
    h = hull(c.y)
    return Vector((0, c.y, (h["zb"] + h["zt"]) / 2))


def hump_centre(c):
    return Vector((0, c.y, hull(c.y)["zt"] - 0.05))


def hull_paint(base="Paint_Blue"):
    def f(c, n):
        if n.z < -0.6:
            return "Graphite"
        if abs(n.x) > 0.25 and n.z > 0.25:
            return "Paint_DarkBlue"
        return base
    return f


def hull_panel(name, t0, t1, y0, y1, parent, m_fn, cuts=(), holes=(), gap_s=(True, True), wrap=False):
    p = Part(name)
    surface(p, hull_loop, t0, t1, y0, y1, HULL_Y, hull3d, gap_s, wrap)
    orient_out(p, hull_centre)
    paint(p, m_fn, cuts)
    return shell(p, parent, holes)


def mirror_t(t, n=10):
    return (lambda y: n - t(y)) if callable(t) else n - t


# ================================================================ 1. STRUCTURE
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


def octagon(y):
    L = hull_loop(y)
    return [L[i] for i in (1, 2, 3, 4, 6, 7, 8, 9)]


struct = Part("Frames")
FRAME_Y = [-2.40, -1.60, -0.73, 0.29, 1.20, 2.00, 2.72]
for y in FRAME_Y:
    oc = octagon(y)
    o, i_ = inset(oc, SKIN + CLEAR), inset(oc, SKIN + CLEAR + 0.035)
    rows = [[Vector((p.x, y + dy, p.y)) for p in ring] for ring, dy in
            ((o, -0.015), (o, 0.015), (i_, 0.015), (i_, -0.015))]
    struct.loft(rows, lambda i, j: "Metal", closed_u=True, closed_v=True)
struct.finish(G["Structural_Core"], bevel=0.002)

lon = Part("Longerons")
for k in (1, 2, 3, 4, 5, 6):
    path = []
    for y in [FRAME_Y[0]] + [s for s in HULL_Y if FRAME_Y[0] < s < FRAME_Y[-1]] + [FRAME_Y[-1]]:
        p = inset(octagon(y), SKIN + CLEAR + 0.018)[k]
        path.append((p.x, y, p.y))
    lon.tube(path, 0.012, "Metal", square=True)
# twin spine rails along the floor, from the crash box to the rear frame
for s in (-1, 1):
    path = [(s * 0.17, y, hull(y)["zb"] + SKIN + CLEAR + 0.03) for y in (-2.45, -0.75, 0.30, 1.20, 2.72)]
    lon.tube(path, 0.03, "Metal", square=True)
lon.finish(G["Structural_Core"], bevel=0.002)

crash = Part("Crash_Structure")
for s in (-1, 1):
    crash.cyl((s * 0.08, -2.40, 0.40), (s * 0.08, -2.93, 0.37), 0.03, "Metal_Bright", 12)
crash.box((0, -2.985, 0.365), (0.20, 0.11, 0.07), "Metal_Bright")
crash.finish(G["Nose"], bevel=0.002)

# floor pan of the cockpit cell, on the rails
cell = Part("Cockpit_Tub")
cell.box((0, -0.22, 0.335), (0.50, 0.98, 0.02), "Graphite")
for s in (-1, 1):
    cell.box((s * 0.252, -0.22, 0.56), (0.012, 0.98, 0.44), "Graphite")             # side protection
cell.box((0, 0.265, 0.56), (0.50, 0.012, 0.44), "Graphite")                          # rear bulkhead
cell.box((0, -0.725, 0.70), (0.50, 0.012, 0.16), "Graphite")                         # front bulkhead (top part)
for s in (-1, 1):
    cell.box((s * 0.215, -0.17, 0.50), (0.06, 0.56, 0.08), "Graphite")               # side consoles
cell.finish(G["Cockpit_Cell"], bevel=0.002)

# reactor cradle on the rails, and the reactor core it holds (in front of the engine)
rc = Part("Reactor_Cradle")
for y in (0.84, 1.30):
    zd = hull(y)["zt"]
    rc.box((0, y, zd + 0.02), (0.30, 0.05, 0.04), "Metal")
    for s in (-1, 1):
        rc.box((s * 0.13, y, (zd + 0.92) / 2), (0.03, 0.05, 0.92 - zd), "Metal")
rc.finish(G["Reactor"], bevel=0.002)
core = Part("Reactor_Core")
core.lathe((0, 0.72, 0.90), (0, 1.40, 0.90),
           [(0, 0.0), (0.01, 0.07), (0.05, 0.11), (0.12, 0.115), (0.16, 0.105), (0.2, 0.115), (0.45, 0.115),
            (0.5, 0.105), (0.55, 0.115), (0.8, 0.115), (0.84, 0.105), (0.88, 0.115), (0.95, 0.11), (0.99, 0.07),
            (1, 0.0)],
           lambda k: "Emit_Hot" if k in (3, 4, 7, 8, 11, 12) else "Metal_Bright", 24)
core.finish(G["Reactor"])

# ================================================================ 2. SYSTEMS
# ---- one large engine at the centre rear, inside the spine, fed by two side intakes
ENG_Z, ENG_R = 0.98, 0.235
EY0, EY1 = 1.72, 2.74               # compressor face, rear flange
INTAKE = (1.28, 1.66)               # y range of the side intakes
GE = G["Propulsion"]
eng = Part("Engine_Core")
eng.lathe((0, EY0, ENG_Z), (0, EY1, ENG_Z),
          [(0, ENG_R), (0.22, ENG_R), (0.22, ENG_R + 0.01), (0.26, ENG_R + 0.01), (0.26, ENG_R), (0.66, ENG_R),
           (0.66, ENG_R + 0.01), (0.70, ENG_R + 0.01), (0.70, ENG_R), (1, ENG_R)],
          lambda k: "Metal", 40, cap0="Graphite", cap1="Graphite")
eng.lathe((0, EY0 - 0.17, ENG_Z), (0, EY0, ENG_Z), [(0, 0.0), (0.4, 0.05), (1, 0.08)], lambda k: "Metal_Bright",
          20, cap1="Metal_Bright")                                                     # spinner
for k in range(20):                                                                   # compressor blades
    ang = 2 * math.pi * k / 20
    R = Matrix.Rotation(ang, 3, 'Y') @ Matrix.Rotation(math.radians(35), 3, 'Z')
    eng.box(Vector((0, EY0 - 0.03, ENG_Z)) + Matrix.Rotation(ang, 3, 'Y') @ Vector((0.152, 0, 0)),
            (0.145, 0.06, 0.005), "Metal_Bright", R)
eng.lathe((0, EY1 - 0.01, ENG_Z), (0, EY1 + 0.07, ENG_Z), [(0, ENG_R + 0.003), (0, ENG_R + 0.02),
          (1, ENG_R + 0.02), (1, ENG_R + 0.003)], lambda k: "Metal", 40, closed=True)   # vectoring joint ring
for k in range(16):                                                                   # nozzle petals
    a0_, a1_ = 2 * math.pi * (k + 0.05) / 16, 2 * math.pi * (k + 0.95) / 16
    ring = [Vector((r * math.cos(a), y, ENG_Z + r * math.sin(a))) for y, r in ((EY1 + 0.07, .246), (3.21, .212))
            for a in (a0_, a1_)]
    inner = [p + (Vector((0, p.y, ENG_Z)) - p).normalized() * 0.009 for p in ring]
    q = [ring[0], ring[1], ring[3], ring[2], inner[0], inner[1], inner[3], inner[2]]
    vs = [eng.bm.verts.new(v) for v in q]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        eng.bm.faces.new([vs[i] for i in f]).material_index = eng.mi("Metal_Bright")
eng.lathe((0, EY1, ENG_Z), (0, 3.17, ENG_Z), [(0, .226), (1, .200)], lambda k: "Black", 40)    # liner
eng.lathe((0, EY1 + 0.06, ENG_Z), (0, EY1 + 0.061, ENG_Z), [(0, .0), (1, .225)], lambda k: "Emit_Hot", 40)
eng.lathe((0, EY1 + 0.04, ENG_Z), (0, 3.14, ENG_Z), [(0, .10), (0.6, .075), (1, .02)], lambda k: "Metal_Bright",
          24, cap1="Metal_Bright")                                                     # exhaust plug
for y in (2.00, 2.55):                                                                # saddles on the frames
    zd = hull(y)["zt"]
    eng.box((0, y, (zd + ENG_Z - ENG_R + 0.012) / 2), (0.30, 0.10, ENG_Z - ENG_R + 0.012 - zd), "Metal")
eng.finish(GE, bevel=0.0)

# side intakes: lip, dust grille and a duct recess going in towards the compressor face
ink = Part("Intakes")
intake_cuts = []
iy = (INTAKE[0] + INTAKE[1]) / 2
il = INTAKE[1] - INTAKE[0]
hb = hump(iy)["hb"]
z0, z1 = hull(iy)["zt"] + 0.05, hump(iy)["hs"] - 0.03
zc, ih = (z0 + z1) / 2, z1 - z0
for s in (-1, 1):
    intake_cuts.append(box_cutter((s * hb, iy, zc), (0.12, il, ih)))
    ink.box((s * (hb - 0.06), iy, zc), (0.012, il, ih), "Black")                          # duct back wall
    for dz in (-1, 1):
        ink.box((s * (hb - 0.035), iy, zc + dz * (ih / 2 - 0.006)), (0.05, il, 0.012), "Black")
    for dy in (-1, 1):
        ink.box((s * (hb - 0.035), iy + dy * (il / 2 - 0.006), zc), (0.05, 0.012, ih), "Black")
    for dz in (-1, 1):                                                                    # lip
        ink.box((s * (hb + 0.002), iy, zc + dz * (ih / 2 + 0.008)), (0.012, il + 0.04, 0.016), "Metal_Bright")
    for dy in (-1, 1):
        ink.box((s * (hb + 0.002), iy + dy * (il / 2 + 0.012), zc), (0.012, 0.016, ih), "Metal_Bright")
    for k in range(1, 6):                                                                 # dust grille
        ink.box((s * (hb - 0.015), iy, z0 + k * ih / 6), (0.008, il, 0.008), "Graphite")
    ink.box((s * (hb - 0.015), iy, zc), (0.008, 0.008, ih), "Graphite")
ink.finish(GE, bevel=0.0)

# power and coolant lines from the reactor to the engine
pipes = Part("Reactor_Lines")
for s in (-1, 1):
    pipes.tube([(s * 0.05, 1.41, 0.95), (s * 0.07, 1.52, 1.05), (s * 0.08, 1.66, 1.17), (s * 0.08, 1.80, 1.205)],
               0.014, "Metal", 10)
pipes.finish(G["Reactor"])

# ---- cooling: radiators behind louvred vents in the hull sides, ducted to the reactor bay
VENT = (0.55, 1.15, 0.44, 0.60)   # y0, y1, z0, z1
cool = Part("Radiators")
for s in (-1, 1):
    y0, y1, z0, z1 = VENT
    w = hull((y0 + y1) / 2)["w"]
    cool.box((s * (w - 0.075), (y0 + y1) / 2, (z0 + z1) / 2), (0.05, y1 - y0 + 0.02, z1 - z0 + 0.02), "Black")
    for k in range(5):                                                                # louvres
        z = z0 + (k + 0.5) * (z1 - z0) / 5
        R = Matrix.Rotation(math.radians(-35 * s), 3, 'Y')
        cool.box((s * (w - 0.022), (y0 + y1) / 2, z), (0.035, y1 - y0 - 0.01, 0.004), "Graphite", R)
    cool.box((s * (w - 0.12), (y0 + y1) / 2, (z0 + z1) / 2 + 0.06), (0.04, 0.30, 0.04), "Metal")  # duct
cool.finish(G["Cooling"], bevel=0.0)

# ---- hover system: discrete emitter modules in cut-outs of the belly, a gravity plate, sensors, skids
EMIT = [(-2.05, 0.13, 0.16, 0.34), (-0.15, 0.28, 0.20, 0.40), (1.85, 0.30, 0.22, 0.44)]   # y, |x|, size x, y
GRAV = (0.85, 0.36, 0.70)
hover = Part("Hover_Emitters")
emit_cuts = []
mods = [(y, s * x, sx, sy) for y, x, sx, sy in EMIT for s in (-1, 1)] + [(GRAV[0], 0.0, GRAV[1], GRAV[2])]
for y, x, sx, sy in mods:
    zb = hull(y)["zb"]
    zbot = zb - (0.012 if sx > 0.3 else 0.035)
    h = zb + 0.03 - zbot
    for dx, dy, ex, ey in ((0, sy / 2 - 0.012, sx, 0.024), (0, -sy / 2 + 0.012, sx, 0.024),
                           (sx / 2 - 0.012, 0, 0.024, sy), (-sx / 2 + 0.012, 0, 0.024, sy)):
        hover.box((x + dx, y + dy, zbot + h / 2), (ex, ey, h), "Graphite")             # housing frame
    hover.box((x, y, zb + 0.02), (sx - 0.02, sy - 0.02, 0.02), "Metal")                 # back plate
    hover.box((x, y, zbot + 0.006), (sx - 0.05, sy - 0.05, 0.004), "Emit_Hover")        # emitter face
    for k in range(1, 4 if sx > 0.3 else 3):                                            # coil ribs
        hover.box((x, y - sy / 2 + k * sy / (4 if sx > 0.3 else 3), zbot + 0.003), (sx - 0.05, 0.008, 0.006),
                  "Metal")
    emit_cuts.append(box_cutter((x, y, zb), (sx + GAP, sy + GAP, 0.08)))
for y, x in ((-2.85, 0.10), (2.62, 0.40)):                                             # surface sensors
    for s in (-1, 1):
        zb = hull(y)["zb"]
        hover.cyl((s * x, y, zb + 0.01), (s * x, y, zb - 0.012), 0.022, "Graphite", 12)
        hover.cyl((s * x, y, zb - 0.012), (s * x, y, zb - 0.014), 0.015, "Black", 12)
hover.finish(G["Hover"], bevel=0.0)

# ---- cockpit: dash, controls, seat and pilot
ck = Part("Cockpit_Parts")
ck.box((0, -0.61, 0.69), (0.46, 0.18, 0.10), "Graphite")                               # dash
ck.box((0, -0.518, 0.70), (0.30, 0.004, 0.06), "Emit_Hover")                          # display
ck.cyl((0, -0.52, 0.66), (0, -0.39, 0.63), 0.018, "Metal", 10)                         # column
ck.box((0, -0.38, 0.63), (0.26, 0.03, 0.03), "Metal")                                  # handlebar
for s in (-1, 1):
    ck.cyl((s * 0.13, -0.38, 0.63), (s * 0.20, -0.38, 0.63), 0.02, "Graphite", 10)
ck.box((0, 0.05, 0.37), (0.38, 0.26, 0.06), "Graphite")                                 # seat
back = Matrix.Rotation(math.radians(-15), 3, 'X')
ck.box((0, 0.20, 0.62), (0.38, 0.05, 0.50), "Graphite", back)                          # back rest
for s in (-1, 1):
    ck.box((s * 0.18, 0.15, 0.58), (0.04, 0.14, 0.40), "Graphite", back)               # bolsters
ck.finish(G["Cockpit_Cell"], bevel=0.003)

pilot = Part("Pilot")
pilot.tube([(0, 0.10, 0.45), (0, 0.13, 0.60), (0, 0.16, 0.72)], 0.12, "Paint_White", 12)   # torso
pilot.sphere((0, 0.15, 0.76), 0.08, "Paint_White", (1.6, 1.0, 0.7))                    # shoulders
pilot.sphere((0, 0.17, 0.835), 0.11, "Paint_Yellow")                                    # helmet
pilot.sphere((0, 0.085, 0.84), 0.06, "Black", (1.35, 0.7, 0.85))                         # visor
for s in (-1, 1):
    pilot.tube([(s * 0.15, 0.15, 0.73), (s * 0.18, -0.07, 0.60), (s * 0.165, -0.37, 0.63)], 0.037, "Paint_White")
    pilot.sphere((s * 0.165, -0.38, 0.63), 0.033, "Graphite")                           # gloves
    pilot.tube([(s * 0.08, 0.05, 0.43), (s * 0.09, -0.45, 0.52), (s * 0.08, -1.00, 0.40)], 0.05, "Paint_White")
    pilot.sphere((s * 0.08, -1.03, 0.40), 0.045, "Graphite", (1.0, 1.4, 1.0))            # boots
pilot.finish(G["Cockpit_Cell"])

# ================================================================ 3. WINGS (spar and ribs, root clamps, skins)
WING = [(0.40, -0.43, 2.605), (1.38, 1.70, 2.53), (1.50, 1.98, 2.42)]   # x, leading edge y, trailing edge y
ANHEDRAL = math.radians(15)   # the wings go down from the root to the tips


def wing_at(x):
    le, te = table(WING, x)
    f = (x - 0.46) / 1.04
    return le, te, 0.385 - (x - 0.46) * math.tan(ANHEDRAL), 0.09 - 0.055 * f      # LE, TE, mid-plane z, thickness


def wing_top(x):
    le, te, mid, th = wing_at(x)
    return mid + th / 2


def wing_loop(x, grow=0.0):
    le, te, mid, th = wing_at(x)
    th += 2 * grow
    le, te = le - grow, te + grow
    e = min(0.10, 0.08 * (te - le))
    return [(le, mid - th / 6), (le, mid + th / 6), (le + e, mid + th / 2), (te - 0.03, mid + th / 2),
            (te, mid + th / 6), (te, mid - th / 6), (te - 0.03, mid - th / 2), (le + e, mid - th / 2)]


WING_X = [0.40, 1.38, 1.50]
for s, side in ((1, "R"), (-1, "L")):
    gw = G["Wing_" + side]

    def w3d(x, y, z, s=s):
        return Vector((s * x, y, z))

    def w_centre(c, s=s):
        le, te, mid, th = wing_at(abs(c.x))
        return Vector((c.x, (le + te) / 2, mid))

    spar = Part("Wing_Structure_" + side)
    p0, p1 = wing_at(0.40), wing_at(1.46)
    for f in (0.45, 0.93):                                                              # main and rear spar
        a = (0.38, p0[0] + f * (p0[1] - p0[0]), p0[2])
        b = (1.46, p1[0] + f * (p1[1] - p1[0]), p1[2])
        spar.tube([(s * a[0], a[1], a[2]), (s * b[0], b[1], b[2])], 0.022 if f < 0.5 else 0.015, "Metal",
                  square=True)
    for x in (0.55, 0.95, 1.35):                                                        # ribs
        L = inset(wing_loop(x), 0.012)
        spar.loft([[Vector((s * (x + d), p.x, p.y)) for p in L] for d in (-0.006, 0.006)], lambda i, j: "Metal",
                  closed_u=True, cap0="Metal", cap1="Metal")
    zr = wing_at(0.40)[2]
    for y in (0.94, 2.42):                                                              # root clamps on the hull
        spar.box((s * 0.40, y, zr), (0.07, 0.12, 0.10), "Metal")
        spar.box((s * 0.34, y, zr), (0.08, 0.04, 0.04), "Metal")
    spar.finish(gw, bevel=0.002)

    def skin(name, t0, t1, m_fn):
        p = Part(name + "_" + side)
        surface(p, wing_loop, t0, t1, 0.40, 1.50, WING_X, w3d, (False, False))
        orient_out(p, w_centre)
        paint(p, m_fn, [((s * 0.6, 2.25, 0.4), (s * 0.25, 0.9, 0))] if name == "Wing_Top" else ())
        return shell(p, gw, thick=0.006, bevel=0.0015)

    def top_paint(c, n, s=s):
        return "Paint_Yellow" if (c - Vector((s * 0.6, 2.25, 0))).dot(Vector((s * 0.25, 0.9, 0))) > 0 else "Paint_Blue"

    skin("Wing_Top", 2, 3, top_paint)
    skin("Wing_Bottom", 6, 7, lambda c, n: "Graphite")
    skin("Wing_TE", 3, 6, lambda c, n: "Paint_DarkBlue")
    skin("Wing_LE", 7, 10, lambda c, n: "Paint_DarkBlue")
    tip = Part("Wing_Tip_" + side)
    L = wing_loop(1.50 - GAP / 2)
    tip.loft([[Vector((s * (1.50 - GAP / 2 - d), p[0], p[1])) for p in L] for d in (0, 0.01)],
             lambda i, j: "Paint_DarkBlue", closed_u=True, cap0="Paint_DarkBlue", cap1="Paint_DarkBlue")
    tip.finish(gw, bevel=0.002, skin=True)
    plate = Part("Wing_Root_Plate_" + side)                                              # quick-release plate
    R = Matrix.Rotation(s * ANHEDRAL, 3, 'Y')      # lies on the sloping wing top
    c = Vector((s * 0.66, 0.94, wing_top(0.66)))
    plate.box(c + R @ Vector((0, 0, 0.004)), (0.09, 0.42, 0.008), "Metal", R)
    for by in (-0.17, -0.06, 0.06, 0.17):
        plate.cyl(c + R @ Vector((0, by, 0.008)), c + R @ Vector((0, by, 0.014)), 0.012, "Metal_Bright", 8)
    plate.finish(gw, bevel=0.0015)

# slot cutters: the wing section near the hull, grown by half a gap
slots = []
for s in (-1, 1):
    p = Part("cut")
    rows = [[Vector((s * x, a, b)) for a, b in wing_loop(x, GAP / 2)] for x in (0.36, 0.72)]
    p.loft(rows, lambda i, j: "Black", closed_u=True, cap0="Black", cap1="Black")
    slots.append(cutter(p))

# ================================================================ 4. BODYWORK
B = G["Body"]
BAND = [((0, -1.42, 0.45), (0, 0.8, -0.6)), ((0, -1.32, 0.45), (0, 0.8, -0.6)), ((0, -0.84, 0.45), (0, 0.8, -0.6))]


def nose_side_paint(c, n):
    d = [(c - Vector(co)).dot(Vector(no)) for co, no in BAND]
    if d[1] > 0 and d[2] < 0:
        return "Paint_White"
    if d[0] > 0 and d[1] < 0:
        return "Paint_Yellow"
    return "Paint_Blue"


nose_cap = Part("Nose_Cap")
rows = surface(nose_cap, hull_loop, 0, 10, -3.15, -2.75, HULL_Y, hull3d, (False, True), wrap=True)
nose_cap.poly(rows[0][::-1], "Graphite")
orient_out(nose_cap, lambda c: Vector((0, -2.7, (hull(-2.9)["zb"] + hull(-2.9)["zt"]) / 2)))
paint(nose_cap, lambda c, n: "Graphite" if n.y < -0.7 or n.z < -0.6 else hull_paint()(c, n))
shell(nose_cap, G["Nose"])
chin = Part("Nose_Chin")                                                                # black sole under the tip
y0, y1 = -3.19, -2.42
pts = []
for y in (y0, -3.15, -2.75, y1):
    h = hull(max(y, -3.15))
    pts.append((y, h["w"] - h["cb"] + 0.006, h["zb"]))
vt = [chin.bm.verts.new(Vector((sx * w, y, z))) for y, w, z in pts for sx in (-1, 1)]
vb = [chin.bm.verts.new(Vector((sx * (w - 0.01), y + (0.015 if y == y0 else 0), z - 0.022)))
      for y, w, z in pts for sx in (-1, 1)]
for i in range(len(pts) - 1):
    a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2
    chin.bm.faces.new([vt[a], vt[b], vt[c], vt[d]])
    chin.bm.faces.new([vb[d], vb[c], vb[b], vb[a]])
    chin.bm.faces.new([vt[a], vt[d], vb[d], vb[a]])
    chin.bm.faces.new([vt[c], vt[b], vb[b], vb[c]])
chin.bm.faces.new([vt[1], vt[0], vb[0], vb[1]])
chin.bm.faces.new([vt[-2], vt[-1], vb[-1], vb[-2]])
for f in chin.bm.faces:
    f.material_index = chin.mi("Black")
chin.finish(G["Nose"], bevel=0.002, skin=True)
lens = Part("Nose_Sensor")
hz = hull(-3.15)
lens.cyl((0, -3.14, (hz["zb"] + hz["zt"]) / 2), (0, -3.165, (hz["zb"] + hz["zt"]) / 2), 0.03, "Graphite", 16)
lens.cyl((0, -3.165, (hz["zb"] + hz["zt"]) / 2), (0, -3.168, (hz["zb"] + hz["zt"]) / 2), 0.02, "Black", 16)
lens.finish(G["Nose"])

hull_panel("Nose_Top", 3, 7, -2.75, -0.75, B, hull_paint())
hull_panel("Belly_Front", 9, 11, -2.75, -0.75, B, lambda c, n: "Graphite", holes=emit_cuts)
hull_panel("Belly_Mid", 9, 11, -0.75, 1.20, B, lambda c, n: "Graphite", holes=emit_cuts)
hull_panel("Belly_Rear", 9, 11, 1.20, 2.75, B, lambda c, n: "Graphite", holes=emit_cuts)
vent_cuts = []
for s in (-1, 1):
    y0, y1, z0, z1 = VENT
    vent_cuts.append(box_cutter((s * hull((y0 + y1) / 2)["w"], (y0 + y1) / 2, (z0 + z1) / 2),
                                (0.12, y1 - y0, z1 - z0)))
for side, s in (("R", 1), ("L", -1)):
    def T(t):
        return t if s > 0 else mirror_t(t)

    def span(a, b):
        return (T(a), T(b)) if s > 0 else (T(b), T(a))
    hull_panel("Nose_Side_" + side, *span(2, 3), -2.75, -0.75, B, nose_side_paint, cuts=BAND)
    hull_panel("Chine_" + side, *span(1, 2), -2.75, 2.75, B, lambda c, n: "Metal")
    hull_panel("Cockpit_Side_" + side, *span(2, 3), -0.75, 0.30, B, hull_paint(), holes=slots)
    hull_panel("Cowl_" + side, *span(3, lambda y: tx(y, 0.26)), -0.75, 0.30, B, hull_paint())
    hull_panel("Side_" + side, *span(2, 3), 0.30, 2.75, B, hull_paint(), holes=slots + vent_cuts)
    hull_panel("Deck_" + side, *span(3, lambda y: tx(y, hump(min(y, 2.75))["hb"] + 0.005)), 0.30, 2.75, B,
               hull_paint())
drop(slots + vent_cuts + emit_cuts)

tail = Part("Tail_Cap")
L = hull_loop(2.75)
ring = [Vector((x, 2.75 - GAP / 2, z)) for x, z in L]
tail.loft([ring, [p + Vector((0, SKIN, 0)) for p in ring]], lambda i, j: "Ceramic", closed_u=True,
          cap0="Ceramic", cap1="Ceramic")
tail.box((0, 2.7495 + SKIN, 0.47), (0.56, 0.008, 0.03), "Emit_Red")
tail.finish(B, bevel=0.002, skin=True)

# ---- the spine over the reactor: yellow top with the reactor cover, sides with service hatch, end caps
H = G["Reactor"]


def hump_panel(name, t0, t1, m_fn, holes=()):
    p = Part(name)
    surface(p, hump_loop, t0, t1, 0.30, 2.75, HUMP_Y, hull3d)
    orient_out(p, hump_centre)
    paint(p, m_fn)
    return shell(p, B, holes)


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


top = hump_panel("Spine_Top", 1, 5, lambda c, n: "Paint_Yellow")
slit_cut = box_cutter((0, 1.48, hump(1.48)["htop"]), (0.20, 0.07, 0.10))
cover = split_out(top, (0, 1.08, hump(1.08)["htop"]), (0.26, 0.60, 0.30), "Reactor_Cover", 2)
boolean(top, [slit_cut])
shade(top, 0.0025)
drop([slit_cut])
latch = Part("Reactor_Cover_Latches")
for y in (0.81, 1.35):
    for s in (-1, 1):
        latch.box((s * 0.08, y, hump(y)["htop"] + 0.003), (0.05, 0.025, 0.006), "Metal")
z = hump(1.48)["htop"]
for k in range(-2, 3):
    latch.box((k * 0.04, 1.48, z - 0.004), (0.008, 0.07, 0.012), "Black")             # slit grille
latch.box((0, 1.48, z - 0.05), (0.20, 0.07, 0.01), "Emit_Hot")                        # reactor glow under it
latch.finish(H)

for side, s in (("R", 1), ("L", -1)):
    span = (0, 1) if s > 0 else (5, 6)
    sp = hump_panel("Spine_Side_" + side, span[0], span[1], lambda c, n: "Paint_Blue",
                    [intake_cuts[0 if s < 0 else 1]])
    hb, zd = hump(0.78)["hb"], hull(0.78)["zt"]
    split_out(sp, (s * hb, 0.78, zd + 0.12), (0.10, 0.34, 0.13), "Service_Hatch_" + side, 0)
    hl = Part("Service_Hatch_Latches_" + side)
    for zz in (zd + 0.08, zd + 0.16):
        hl.box((s * (hump(0.60)["hb"] + 0.003), 0.60, zz), (0.006, 0.03, 0.04), "Metal")
    hl.finish(H)

drop(intake_cuts)
for name, y, d, m in (("Spine_Front", 0.30 + GAP / 2, -1, "Graphite"), ("Spine_Rear", 2.75 - GAP / 2, 1, "Ceramic")):
    L = hump_loop(y)
    cap = Part(name)
    ring = [Vector((x, y, z)) for x, z in L]
    cap.loft([ring, [p + Vector((0, -d * SKIN, 0)) for p in ring]], lambda i, j: m, closed_u=True, cap0=m, cap1=m)
    ob = cap.finish(B, skin=True)
    if d > 0:                                                  # the rear cap is the heat shield round the nozzle
        c = Part("cut")
        c.cyl((0, y - 0.05, ENG_Z), (0, y + 0.05, ENG_Z), ENG_R + 0.022, "Black", 40)
        cc = cutter(c)
        boolean(ob, [cc])
        drop([cc])
    shade(ob, 0.002)

# ---- canopy: glass on a sill frame, middle bow, roll hoop behind the pilot
CAN = [(-0.745, .020), (-0.60, .090), (-0.45, .150), (-0.25, .180), (0.0, .185), (0.15, .170), (0.265, .140)]
CAN_W = 0.265


def canopy_loop(y, grow=0.0, n=14):
    h = table(CAN, y)[0] + grow
    zb = hull(y)["zt"] + 0.012
    return [(CAN_W * math.cos(math.pi * k / n) * (1 + grow), zb + h * math.sin(math.pi * k / n) ** 0.55)
            for k in range(n + 1)]


glass = Part("Canopy")
ys = [-0.745, -0.70, -0.65, -0.60, -0.52, -0.45, -0.35, -0.25, -0.12, 0.0, 0.08, 0.15, 0.21, 0.265]
glass.loft([[Vector((x, y, z)) for x, z in canopy_loop(y)] for y in ys], lambda i, j: "Glass")
orient_out(glass, lambda c: Vector((0, c.y, hull(c.y)["zt"])))
g = shell(glass, G["Cockpit_Cell"], thick=0.008, bevel=0.0)
SKINS.remove(g)
frame = Part("Canopy_Frame")
for s in (-1, 1):
    frame.tube([(s * (CAN_W + 0.004), y, hull(y)["zt"] + 0.008) for y in ys], 0.011, "Graphite", 8)
for y, r, m in ((-0.745, 0.012, "Graphite"), (-0.20, 0.010, "Graphite")):
    frame.tube([Vector((x, y, z + 0.006)) for x, z in canopy_loop(y, 0.01)], r, m, 8)
frame.finish(G["Cockpit_Cell"])
hoop = Part("Roll_Hoop")
hp = [Vector((x, 0.283, z)) for x, z in canopy_loop(0.265, 0.035)]
hp = [Vector((hp[0].x, 0.283, hull(0.29)["zt"] - 0.08))] + hp + [Vector((hp[-1].x, 0.283, hull(0.29)["zt"] - 0.08))]
hoop.tube(hp, 0.022, "Metal", 12)
hoop.finish(G["Cockpit_Cell"])

# ================================================================ 5. DECALS (our own marks; no third-party logos)
font = bpy.data.fonts.load(FONT_PATH) if os.path.exists(FONT_PATH) else None


def text_mesh(body, size):
    cu = bpy.data.curves.new("txt", 'FONT')
    cu.body, cu.size, cu.align_x, cu.align_y = body, size, 'CENTER', 'CENTER'
    if font:
        cu.font = font
    ob = bpy.data.objects.new("txt", cu)
    SHIP.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return me


def frame_on(origin, u, v, lift=0.0025):
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


dec = Part("Decals")
for s in (-1, 1):
    # STRIX on the nose sides (reads front to back on both sides)
    y0, y1 = -2.75, -0.75
    a, b = hull(y0), hull(y1)
    slope = (b["w"] - a["w"]) / (y1 - y0)
    yc = -2.13
    hc = hull(yc)
    zc = (hc["zb"] + hc["cb"] + hc["zs"]) / 2
    u = Vector((slope * s, 1.0, 0)) * (1 if s > 0 else -1)
    M = frame_on((s * hc["w"], yc, zc), u, (0, 0, 1))
    dec.add_mesh(text_mesh("STRIX", 0.15), M, "Paint_White")
    # race number on a white roundel on the spine sides
    yn = 2.18
    hn, zd = hump(yn), hull(yn)["zt"]
    zn = zd + (hn["hs"] - zd) / 2
    u = Vector((0, 1, 0)) * (1 if s > 0 else -1)
    M = frame_on((s * hn["hb"], yn, zn), u, (0, 0, 1))
    dec.flat(disc2d(0.115), M, "Paint_White")
    dec.add_mesh(text_mesh("07", 0.14), frame_on((s * hn["hb"], yn, zn), u, (0, 0, 1), 0.004), "Black")
    # rescue marking: yellow arrow pointing at the canopy, on the cockpit sides
    yr = -0.25
    hr = hull(yr)
    slope_c = (hull(0.30)["w"] - hull(-0.75)["w"]) / 1.05
    u = Vector((slope_c * s, 1.0, 0)) * (1 if s > 0 else -1)
    M = frame_on((s * hr["w"], yr, hr["zs"] - 0.10), u, (0, 0, 1))
    arrow = [(-0.10, -0.018), (0.04, -0.018), (0.04, -0.04), (0.10, 0.0), (0.04, 0.04), (0.04, 0.018),
             (-0.10, 0.018)]
    R = Matrix.Rotation(math.radians(35 if s > 0 else 145), 4, 'Z')
    dec.poly([M @ R @ Vector((x, y, 0)) for x, y in arrow], "Paint_Yellow")
    # hazard stripes at the rear edge of the cooling vent
    y0v, y1v, z0v, z1v = VENT
    hv = hull(y1v + 0.03)
    M = frame_on((s * hv["w"], y1v + 0.035, (z0v + z1v) / 2), Vector((0, 1, 0)) * (1 if s > 0 else -1), (0, 0, 1))
    for k in range(6):
        z0 = -0.075 + k * 0.025
        dec.poly([M @ Vector(p) for p in ((-0.02, z0, 0), (0.02, z0 + 0.02, 0), (0.02, z0 + 0.0325, 0),
                                          (-0.02, z0 + 0.0125, 0))], "Paint_Yellow" if k % 2 else "Black")
    # emblem on the wing tops: ring and four-point star
    xc, yc = 0.98, 1.62
    le, te, mid, th = wing_at(xc)
    d = (wing_top(xc + 0.05) - wing_top(xc - 0.05)) / 0.1      # slope of the wing top along the span
    M = frame_on((s * xc, yc, wing_top(xc) + 0.0005), (s, 0, d), (0, s, 0))
    o, i_ = ring2d(0.165, 0.20)
    dec.flat(o, M, "Paint_White", holes=[i_])
    star = []
    for k in range(8):
        r = 0.14 if k % 2 == 0 else 0.035
        a_ = math.pi / 2 + k * math.pi / 4
        star.append((r * math.cos(a_), r * math.sin(a_)))
    dec.poly([M @ Vector((x, y, 0)) for x, y in star], "Paint_White")
    # warning triangles on the nose top ahead of the canopy
    yw = -0.95
    a, b = hull(-2.75), hull(-0.75)
    dz = (b["zt"] - a["zt"]) / 2.0
    M = frame_on((s * 0.12, yw, hull(yw)["zt"]), (1, 0, 0), (0, -1, -dz))
    outer = [(0, 0.04), (-0.035, -0.02), (0.035, -0.02)]
    inner = [(0, 0.024), (-0.021, -0.012), (0.021, -0.012)]
    dec.loft([[M @ Vector((x, y, 0)) for x, y in outer], [M @ Vector((x, y, 0)) for x, y in inner]],
             lambda i, j: "Paint_Red", closed_u=True)
dec.finish(G["Decals"], recalc=False, smooth_angle=10)

# ================================================================ sockets (where modules bolt on)
for name, loc in (("Socket_Engine", (0, 2.20, ENG_Z)), ("Socket_Reactor", (0, 1.06, 0.90)),
                  ("Socket_Propulsion", (0, EY1 + 0.04, ENG_Z)),
                  ("Socket_Wing_L", (-0.40, 0.94, wing_at(0.40)[2])), ("Socket_Wing_R", (0.40, 0.94, wing_at(0.40)[2])),
                  ("Socket_Tail", (0, 2.76, 0.47)), ("Socket_Armor_L", (-0.56, 0.30, 0.45)),
                  ("Socket_Armor_R", (0.56, 0.30, 0.45)), ("Socket_Cooling", (0, 0.85, 0.52)),
                  ("Socket_Utility", (0, -2.40, 0.30))):
    group(name, G["Sockets"], loc)

# ================================================================ report, save, export
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
print("STRIX objects %d  tris %d  size %.2f x %.2f x %.2f m  z %.2f..%.2f" % (
    sum(1 for o in SHIP.objects if o.type == 'MESH'), tris, *(hi - lo), lo.z, hi.z))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "strix.blend"), compress=True)
lc = bpy.context.view_layer.layer_collection.children["STRIX"]
bpy.context.view_layer.active_layer_collection = lc
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "strix.fbx"), use_active_collection=True,
                         object_types={'EMPTY', 'MESH'}, use_mesh_modifiers=True, mesh_smooth_type='FACE',
                         add_leaf_bones=False, apply_unit_scale=True, use_custom_props=False)

if not RENDER:
    sys.exit(0)

# ================================================================ preview renders (studio, not exported)
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
fl = Part("Floor")
fl.poly([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], "Black")
floor = fl.finish(None)
floor.data.materials[0] = gm
SHIP.objects.unlink(floor)
studio.objects.link(floor)


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


def shot(name, loc, target, lens=50, ortho=None):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam_d.type = 'ORTHO' if ortho else 'PERSP'
    if ortho:
        cam_d.ortho_scale = ortho
    cam_d.lens = lens
    r.filepath = os.path.join(OUT, "strix_" + name + ".jpg")
    bpy.ops.render.render(write_still=True)


shot("34_front", (-6.2, -7.4, 4.0), (0, -0.2, 0.55), 55)
shot("34_rear", (5.8, 6.8, 3.2), (0, 0.4, 0.6), 55)
shot("side", (-12, 0, 0.62), (0, 0, 0.62), ortho=7.0)
cam_d.type = 'ORTHO'
cam_d.ortho_scale = 7.0
cam.location, cam.rotation_euler = (0, 0, 12), (0, 0, math.radians(90))
r.filepath = os.path.join(OUT, "strix_top.jpg")
bpy.ops.render.render(write_still=True)
shot("front", (0, -12, 0.65), (0, 0, 0.65), ortho=3.6)
shot("cockpit", (-1.6, -2.2, 1.7), (0, -0.1, 0.80), 45)
for o in SKINS + [o for o in SHIP.objects if o.parent == G["Decals"]]:
    o.hide_render = True
shot("inside", (-6.2, -7.4, 4.0), (0, -0.2, 0.55), 55)
