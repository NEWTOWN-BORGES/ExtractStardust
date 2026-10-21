# WRAITH hover racer (light, for skilled pilots), built from the inside out like the STRIX: structure first (frames
# and longerons in each arm, bridge frames, the cross beam in the fork and the braces that hold the cockpit pod), then
# the systems (cockpit and pilot, reactor, two engines at the rear fed by intakes at the tips of the arms through
# ducts inside them, radiators, hover emitters), then the 12 mm bodywork panels with 5 mm gaps.
# Look: fork (U) plan - two long, low, faceted arms forward with open space between them, a narrow raised cockpit pod
# at the base of the U, a compact rear with two round engines, short wings at the rear going down; light steel blue
# with orange trim (Docs/WRAITH_CATEGORIA.md). No blades, spikes or loose fins.
# Front is -Y, up is +Z, metres (the layout of the old SourceArt/TestShips/wraith.fbx; the game centres the bounds).
# Usage: python3 Scripts/build_wraith.py <out_dir> [--no-render]
#    or: blender -b -P Scripts/build_wraith.py -- <out_dir> [--no-render]
# Writes <out_dir>/wraith.blend, wraith.fbx and the preview renders. Shared parts: Scripts/ship_kit.py.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ship_kit import *  # noqa: E402,F401,F403  (bpy, bmesh, math, Matrix, Vector and the helpers)

start("WRAITH")
material("Paint_Steel", "#AEC2D2", rough=0.32, coat=0.5)
material("Paint_Dark", "#4A5866", rough=0.35, coat=0.5)
material("Paint_Orange", "#E86A2C", rough=0.3, coat=0.6)
material("Paint_White", "#EEF1F3", rough=0.32, coat=0.5)
material("Paint_Yellow", "#F2C230", rough=0.3, coat=0.5)
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
material("Emit_Green", "#8CFF5A", emit=3.0, rough=0.3)

ROOT = group("ShipRoot")
G = {n: group(n, ROOT) for n in ("Structural_Core", "Arm_L", "Arm_R", "Cockpit_Cell", "Body", "Reactor",
                                 "Propulsion", "Wing_L", "Wing_R", "Hover", "Cooling", "Decals", "Sockets")}
B = G["Body"]

# ---------------------------------------------------------------- lines
#        y      xc    w     zb    cb    zs    ct    zt      (arm centre x and half width; low and high chamfers)
ARM = [(-3.25, .645, .095, .310, .025, .410, .040, .460),
       (-2.60, .635, .140, .290, .035, .480, .060, .550),
       (-1.20, .625, .190, .270, .045, .540, .080, .620),
       (0.40, .620, .220, .260, .050, .580, .090, .660)]
#         y     w     zb    cb    zs    ct    zt         (the bridge at the base of the U and the rear body)
BODY = [(0.40, .840, .260, .050, .580, .090, .660),
        (1.40, .860, .270, .050, .660, .130, .780),
        (2.20, .840, .300, .050, .720, .150, .840)]
#        y      w     zb    cb    zs    ct    zt         (cockpit pod; from 0.40 back it is the spine on the bridge)
POD = [(-1.40, .080, .640, .030, .700, .030, .730),
       (-0.90, .200, .560, .060, .760, .070, .840),
       (-0.40, .260, .520, .080, .800, .090, .890),
       (0.00, .280, .500, .080, .820, .090, .920),
       (0.40, .290, .500, .080, .860, .100, .960),
       (1.40, .270, .660, .050, .900, .100, 1.000),
       (2.20, .240, .700, .040, .880, .080, .960)]
ARM_Y, BODY_Y, POD_Y = [r[0] for r in ARM], [r[0] for r in BODY], [r[0] for r in POD]
Y_JOIN, Y_TAIL = 0.40, 2.20


def loop10(xc, w, zb, cb, zs, ct, zt):
    r = [(0, zb), (w - cb, zb), (w, zb + cb), (w, zs), (w - ct, zt), (0, zt)]
    return [(xc + x, z) for x, z in r] + [(xc - x, z) for x, z in reversed(r[1:-1])]


def arm(y):
    return dict(zip(("xc", "w", "zb", "cb", "zs", "ct", "zt"), table(ARM, y)))


def body(y):
    return dict(zip(("w", "zb", "cb", "zs", "ct", "zt"), table(BODY, y)))


def pod(y):
    return dict(zip(("w", "zb", "cb", "zs", "ct", "zt"), table(POD, y)))


def arm_loop(s):      # t 0..5 is the outer half of either arm (the left arm is the mirror of the right)
    def f(y):
        a = arm(y)
        return [(s * x, z) for x, z in loop10(a["xc"], a["w"], a["zb"], a["cb"], a["zs"], a["ct"], a["zt"])]
    return f


def body_loop(y):
    b = body(y)
    return loop10(0, b["w"], b["zb"], b["cb"], b["zs"], b["ct"], b["zt"])


def pod_loop(y):
    p = pod(y)
    return loop10(0, p["w"], p["zb"], p["cb"], p["zs"], p["ct"], p["zt"])


def spine_loop(y):    # the pod behind the cockpit, standing on the bridge deck: open at the base, t 0..6
    p, zd = pod(y), body(y)["zt"]
    r = [(p["w"], zd), (p["w"], p["zs"]), (p["w"] - p["ct"], p["zt"]), (0, p["zt"])]
    return r + [(-x, z) for x, z in reversed(r[:-1])]


def xyz(y, x, z):
    return Vector((x, y, z))


def arm_centre(s):
    return lambda c: Vector((s * arm(c.y)["xc"], c.y, (arm(c.y)["zb"] + arm(c.y)["zt"]) / 2))


def body_centre(c):
    return Vector((0, c.y, (body(c.y)["zb"] + body(c.y)["zt"]) / 2))


def pod_centre(c):
    return Vector((0, c.y, (pod(c.y)["zb"] + pod(c.y)["zt"]) / 2))


def spine_centre(c):
    return Vector((0, c.y, body(c.y)["zt"] - 0.05))


def trim(base="Paint_Steel", chamfer="Paint_Orange"):
    def f(c, n):
        if n.z < -0.6:
            return "Graphite"
        if abs(n.x) > 0.25 and n.z > 0.25:
            return chamfer
        return base
    return f


STRIPES = [((0, y, 0.45), (0, 0.9, -0.43)) for y in (-1.24, -1.19, -1.12, -1.07)]   # double yellow band on the arms


def arm_paint(c, n):
    m = trim()(c, n)
    if m == "Graphite":
        return m
    d = [(c - Vector(co)).dot(Vector(no)) for co, no in STRIPES]
    return "Paint_Yellow" if d[0] > 0 > d[1] or d[2] > 0 > d[3] else m


def panel(name, loop_fn, t0, t1, y0, y1, stations, parent, m_fn, centre, cuts=(), holes=(), gap_s=(True, True),
          wrap=False, thick=SKIN):
    p = Part(name)
    surface(p, loop_fn, t0, t1, y0, y1, stations, xyz, gap_s, wrap)
    orient_out(p, centre)
    paint(p, m_fn, cuts)
    return shell(p, parent, holes, thick)


def deck_t(y, x):     # t on the bridge top (segment 4-5) where the deck is at half width x
    b = body(y)
    wt = b["w"] - b["ct"]
    return 4 + (wt - x) / wt


# ================================================================ 1. STRUCTURE
def octa(L):
    return [L[i] for i in (1, 2, 3, 4, 6, 7, 8, 9)]


def ring_frames(part, loop_fn, ys):
    for y in ys:
        oc = octa(loop_fn(y))
        o, i_ = inset(oc, SKIN + CLEAR), inset(oc, SKIN + CLEAR + 0.03)
        rows = [[Vector((p.x, y + dy, p.y)) for p in ring] for ring, dy in
                ((o, -0.012), (o, 0.012), (i_, 0.012), (i_, -0.012))]
        part.loft(rows, lambda i, j: "Metal", closed_u=True, closed_v=True)


def longerons(part, loop_fn, y0, y1, stations, corners, r=0.010):
    for k in corners:
        path = []
        for y in [y0] + [s for s in stations if y0 < s < y1] + [y1]:
            p = inset(octa(loop_fn(y)), SKIN + CLEAR + r + 0.004)[k]
            path.append((p.x, y, p.y))
        part.tube(path, r, "Metal", square=True)


fr = Part("Frames")
for s in (-1, 1):
    ring_frames(fr, arm_loop(s), (-2.90, -2.00, -1.10, -0.20))
ring_frames(fr, body_loop, (0.46, 1.15, 2.14))
ring_frames(fr, pod_loop, (-1.00, -0.40))
fr.finish(G["Structural_Core"], bevel=0.002)

lon = Part("Longerons")
for s in (-1, 1):
    longerons(lon, arm_loop(s), -3.00, Y_JOIN, ARM_Y, (1, 2, 5, 6))
longerons(lon, body_loop, 0.46, 2.14, BODY_Y, (0, 1, 2, 5, 6, 7))
lon.finish(G["Structural_Core"], bevel=0.002)

# the beam across the fork and the braces that hold the front of the cockpit pod (open structure, seen from outside)
fork = Part("Fork_Structure")
xi = arm(0.34)["xc"] - arm(0.34)["w"]
fork.box((0, 0.34, 0.33), (2 * xi, 0.07, 0.07), "Metal")
for s in (-1, 1):
    fork.box((s * (xi - 0.012), 0.34, 0.33), (0.024, 0.12, 0.12), "Metal")             # end plates
    a = arm(-0.85)
    top = Vector((s * 0.12, -0.62, pod(-0.62)["zb"] - 0.006))
    foot = Vector((s * (a["xc"] - a["w"] + 0.006), -0.85, 0.44))
    fork.tube([top, foot], 0.017, "Metal", 10)
    fork.box(top + Vector((0, 0, -0.006)), (0.06, 0.08, 0.012), "Metal")              # brackets
    fork.box(foot + Vector((s * 0.006, 0, 0)), (0.012, 0.08, 0.07), "Metal")
fork.finish(G["Structural_Core"], bevel=0.002)

# ================================================================ 2. SYSTEMS
# ---- two engines at the rear, fed through ducts from intakes at the arm tips
ENG_X, ENG_Z, ENG_R = 0.48, 0.56, 0.17
EY0, EY1 = 1.30, 2.80               # compressor face, rear flange
GE = G["Propulsion"]
for s in (-1, 1):
    x = s * ENG_X
    eng = Part("Engine_" + ("R" if s > 0 else "L"))
    eng.lathe((x, EY0, ENG_Z), (x, EY1, ENG_Z),
              [(0, ENG_R), (0.6, ENG_R), (0.6, ENG_R + 0.008), (0.64, ENG_R + 0.008), (0.64, ENG_R), (0.85, ENG_R),
               (0.85, ENG_R + 0.006), (0.97, ENG_R + 0.006), (0.97, ENG_R), (1, ENG_R)],
              lambda k: "Ceramic" if k in (5, 6, 7) else "Metal", 32, cap0="Graphite", cap1="Graphite")   # heat band
    eng.lathe((x, EY0 - 0.12, ENG_Z), (x, EY0, ENG_Z), [(0, 0.0), (0.4, 0.035), (1, 0.06)],
              lambda k: "Metal_Bright", 16, cap1="Metal_Bright")                         # spinner
    for k in range(16):                                                                   # compressor blades
        ang = 2 * math.pi * k / 16
        R = Matrix.Rotation(ang, 3, 'Y') @ Matrix.Rotation(math.radians(35), 3, 'Z')
        eng.box(Vector((x, EY0 - 0.025, ENG_Z)) + Matrix.Rotation(ang, 3, 'Y') @ Vector((0.112, 0, 0)),
                (0.10, 0.05, 0.004), "Metal_Bright", R)
    eng.lathe((x, EY1 - 0.01, ENG_Z), (x, EY1 + 0.06, ENG_Z), [(0, ENG_R + 0.003), (0, ENG_R + 0.016),
              (1, ENG_R + 0.016), (1, ENG_R + 0.003)], lambda k: "Metal", 32, closed=True)   # vectoring joint
    for k in range(12):                                                                   # nozzle petals
        a0_, a1_ = 2 * math.pi * (k + 0.05) / 12, 2 * math.pi * (k + 0.95) / 12
        ring = [Vector((x + r * math.cos(a), y, ENG_Z + r * math.sin(a))) for y, r in ((EY1 + 0.06, .176), (3.17, .150))
                for a in (a0_, a1_)]
        inner = [p + (Vector((x, p.y, ENG_Z)) - p).normalized() * 0.008 for p in ring]
        q = [ring[0], ring[1], ring[3], ring[2], inner[0], inner[1], inner[3], inner[2]]
        vs = [eng.bm.verts.new(v) for v in q]
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            eng.bm.faces.new([vs[i] for i in f]).material_index = eng.mi("Metal_Bright")
    eng.lathe((x, EY1, ENG_Z), (x, 3.13, ENG_Z), [(0, .160), (1, .142)], lambda k: "Black", 32)     # liner
    eng.lathe((x, EY1 + 0.05, ENG_Z), (x, EY1 + 0.051, ENG_Z), [(0, .0), (1, .159)], lambda k: "Emit_Hot", 32)
    eng.lathe((x, EY1 + 0.03, ENG_Z), (x, 3.10, ENG_Z), [(0, .07), (0.6, .05), (1, .015)],
              lambda k: "Metal_Bright", 16, cap1="Metal_Bright")                         # exhaust plug
    for y in (1.62, 2.02):                                                                # saddles on the belly
        zb = body(y)["zb"] + SKIN + CLEAR
        eng.box((x, y, (zb + ENG_Z - ENG_R + 0.01) / 2), (0.14, 0.08, ENG_Z - ENG_R + 0.01 - zb), "Metal")
    eng.finish(GE, bevel=0.0)

# intake mouths at the arm tips, funnels and ducts back to the compressor faces (inner faces point inwards)
DUCT_R = 0.055
duct = Part("Intake_Ducts")
lip = Part("Intakes")
for s in (-1, 1):
    a = arm(-3.25)
    mouth = inset(octa(arm_loop(s)(-3.25)), SKIN + 0.004)
    zc = (a["zb"] + a["zt"]) / 2
    c0 = Vector((s * a["xc"], -3.00, zc))
    circ = [c0 + Vector((math.cos(2 * math.pi * k / 8 + math.pi / 8) * DUCT_R * s, 0,
                         math.sin(2 * math.pi * k / 8 + math.pi / 8) * DUCT_R)) for k in range(8)]
    ring3 = [Vector((p.x, -3.24, p.y)) for p in mouth]
    ang = [math.atan2(p.z - zc, (p.x - s * a["xc"]) * s) for p in ring3]
    order = sorted(range(8), key=lambda k: ang[k] % (2 * math.pi))
    circ_sorted = sorted(circ, key=lambda p: math.atan2(p.z - zc, (p.x - s * a["xc"]) * s) % (2 * math.pi))
    duct.loft([[ring3[k] for k in order], circ_sorted], lambda i, j: "Black", closed_u=True)
    path = [(s * a["xc"], -3.00, zc)]
    for y in (-2.60, -1.20, Y_JOIN):
        q = arm(y)
        path.append((s * q["xc"], y, (q["zb"] + q["zt"]) / 2))
    path += [(s * 0.53, 1.00, 0.53), (s * ENG_X, 1.12, ENG_Z)]
    duct.tube(path, DUCT_R, "Black", 12)
    duct.lathe((s * ENG_X, 1.12, ENG_Z), (s * ENG_X, EY0 - 0.005, ENG_Z), [(0, DUCT_R), (1, ENG_R - 0.004)],
               lambda k: "Black", 16)
    lip.tube([Vector((p.x, -3.247, p.y)) for p in mouth + mouth[:1]], 0.012, "Metal_Bright", 8)
    for dz in (-0.045, 0.0, 0.045):                                                       # dust grille
        h = 2 * (a["w"] - 0.03)
        lip.box((s * a["xc"], -3.235, zc + dz), (h, 0.006, 0.006), "Graphite")
    lip.box((s * a["xc"], -3.235, zc), (0.006, 0.006, a["zt"] - a["zb"] - 0.05), "Graphite")
bmesh.ops.recalc_face_normals(duct.bm, faces=duct.bm.faces[:])
bmesh.ops.reverse_faces(duct.bm, faces=duct.bm.faces[:])
duct.finish(GE, recalc=False)
lip.finish(GE)

# ---- reactor in the spine behind the cockpit, lines to both engines
rc = Part("Reactor_Core")
rc.lathe((0, 0.62, 0.815), (0, 1.20, 0.815),
         [(0, 0.0), (0.02, 0.06), (0.08, 0.095), (0.18, 0.10), (0.24, 0.092), (0.30, 0.10), (0.70, 0.10),
          (0.76, 0.092), (0.82, 0.10), (0.92, 0.095), (0.98, 0.06), (1, 0.0)],
         lambda k: "Emit_Hot" if k in (3, 4, 7, 8) else "Metal_Bright", 24)
for y in (0.75, 1.08):
    rc.box((0, y, 0.695), (0.22, 0.05, 0.04), "Metal")                                     # saddles
for s in (-1, 1):
    rc.tube([(s * 0.04, 1.22, 0.815), (s * 0.20, 1.40, 0.76), (s * 0.36, 1.55, 0.74), (s * 0.44, 1.60, 0.715)],
            0.013, "Metal", 10)
rc.finish(G["Reactor"])

# ---- cooling: radiators behind slot vents in the rear body sides, above the wings
VENT = (1.10, 1.70, 0.55, 0.63)     # y0, y1, z0, z1
cool = Part("Radiators")
vent_cuts = []
for s in (-1, 1):
    y0, y1, z0, z1 = VENT
    w = body((y0 + y1) / 2)["w"]
    cool.box((s * (w - 0.06), (y0 + y1) / 2, (z0 + z1) / 2), (0.04, y1 - y0 + 0.02, z1 - z0 + 0.02), "Black")
    for k in range(3):
        z = z0 + (k + 0.5) * (z1 - z0) / 3
        cool.box((s * (w - 0.02), (y0 + y1) / 2, z), (0.03, y1 - y0 - 0.01, 0.004), "Graphite",
                 Matrix.Rotation(math.radians(-35 * s), 3, 'Y'))
    vent_cuts.append(box_cutter((s * w, (y0 + y1) / 2, (z0 + z1) / 2), (0.10, y1 - y0, z1 - z0)))
ARM_VENT = (-0.70, -0.20, 0.37, 0.53)
for s in (-1, 1):
    y0, y1, z0, z1 = ARM_VENT
    a = arm((y0 + y1) / 2)
    xo = a["xc"] + a["w"]
    cool.box((s * (xo - 0.05), (y0 + y1) / 2, (z0 + z1) / 2), (0.03, y1 - y0 + 0.02, z1 - z0 + 0.02), "Black")
    for k in range(5):
        z = z0 + (k + 0.5) * (z1 - z0) / 5
        cool.box((s * (xo - 0.02), (y0 + y1) / 2, z), (0.03, y1 - y0 - 0.01, 0.004), "Graphite",
                 Matrix.Rotation(math.radians(-35 * s), 3, 'Y'))
    vent_cuts.append(box_cutter((s * xo, (y0 + y1) / 2, (z0 + z1) / 2), (0.10, y1 - y0, z1 - z0)))
cool.finish(G["Cooling"])

# ---- hover system: emitter modules in cut-outs of the arm and body bellies, a gravity plate, sensors
EMIT = [(-2.55, "arm", 0.14, 0.36), (-1.45, "arm", 0.18, 0.40), (0.80, 0.50, 0.20, 0.40), (1.85, 0.50, 0.20, 0.40)]
hover = Part("Hover_Emitters")
arm_cuts, body_cuts = [], []
mods = []
for y, where, sx, sy in EMIT:
    for s in (-1, 1):
        x = s * (arm(y)["xc"] if where == "arm" else where)
        mods.append((y, x, sx, sy, arm(y)["zb"] if where == "arm" else body(y)["zb"], where == "arm"))
mods.append((1.45, 0.0, 0.36, 0.50, body(1.45)["zb"], False))
for y, x, sx, sy, zb, on_arm in mods:
    plate = sx > 0.3
    zbot = zb - (0.012 if plate else 0.035)
    h = zb + 0.03 - zbot
    for dx, dy, ex, ey in ((0, sy / 2 - 0.012, sx, 0.024), (0, -sy / 2 + 0.012, sx, 0.024),
                           (sx / 2 - 0.012, 0, 0.024, sy), (-sx / 2 + 0.012, 0, 0.024, sy)):
        hover.box((x + dx, y + dy, zbot + h / 2), (ex, ey, h), "Graphite")
    hover.box((x, y, zb + 0.02), (sx - 0.02, sy - 0.02, 0.02), "Metal")
    hover.box((x, y, zbot + 0.006), (sx - 0.05, sy - 0.05, 0.004), "Emit_Hover")
    for k in range(1, 4 if plate else 3):
        hover.box((x, y - sy / 2 + k * sy / (4 if plate else 3), zbot + 0.003), (sx - 0.05, 0.008, 0.006), "Metal")
    (arm_cuts if on_arm else body_cuts).append(box_cutter((x, y, zb), (sx + GAP, sy + GAP, 0.08)))
for y, x, zb in ((-3.05, arm(-3.05)["xc"], arm(-3.05)["zb"]), (2.10, 0.74, body(2.10)["zb"])):   # sensors
    for s in (-1, 1):
        hover.cyl((s * x, y, zb + 0.01), (s * x, y, zb - 0.012), 0.02, "Graphite", 12)
        hover.cyl((s * x, y, zb - 0.012), (s * x, y, zb - 0.014), 0.013, "Black", 12)
hover.finish(G["Hover"])

# ---- cockpit: tub, dash, controls, seat and pilot
ck = Part("Cockpit_Parts")
ck.box((0, -0.18, 0.565), (0.30, 0.56, 0.012), "Graphite")                                # floor
ck.box((0, -0.38, 0.775), (0.34, 0.14, 0.07), "Graphite")                                 # dash
ck.box((0, -0.309, 0.79), (0.22, 0.004, 0.045), "Emit_Hover")                             # display
ck.cyl((0, -0.31, 0.76), (0, -0.19, 0.725), 0.015, "Metal", 10)                           # column
ck.box((0, -0.18, 0.722), (0.22, 0.026, 0.026), "Metal")                                  # handlebar
for s in (-1, 1):
    ck.cyl((s * 0.10, -0.18, 0.722), (s * 0.15, -0.18, 0.722), 0.018, "Graphite", 10)
ck.box((0, 0.13, 0.555), (0.32, 0.22, 0.05), "Graphite")                                  # seat
back = Matrix.Rotation(math.radians(-15), 3, 'X')
ck.box((0, 0.29, 0.74), (0.32, 0.045, 0.38), "Graphite", back)                            # back rest
for s in (-1, 1):
    ck.box((s * 0.15, 0.25, 0.72), (0.03, 0.12, 0.30), "Graphite", back)                 # bolsters
ck.finish(G["Cockpit_Cell"], bevel=0.003)

pilot = Part("Pilot")
pilot.tube([(0, 0.13, 0.60), (0, 0.20, 0.72), (0, 0.27, 0.83)], 0.105, "Paint_White", 12)   # torso
pilot.sphere((0, 0.26, 0.855), 0.07, "Paint_White", (1.6, 1.0, 0.7))                     # shoulders
pilot.sphere((0, 0.29, 0.935), 0.10, "Paint_Orange")                                      # helmet
pilot.sphere((0, 0.215, 0.94), 0.055, "Black", (1.3, 0.7, 0.85))                           # visor
for s in (-1, 1):
    pilot.tube([(s * 0.13, 0.26, 0.83), (s * 0.15, 0.05, 0.71), (s * 0.12, -0.17, 0.722)], 0.033, "Paint_White")
    pilot.sphere((s * 0.125, -0.18, 0.722), 0.03, "Graphite")                              # gloves
    pilot.tube([(s * 0.07, 0.10, 0.60), (s * 0.08, -0.32, 0.665), (s * 0.07, -0.66, 0.665)], 0.045, "Paint_White")
    pilot.sphere((s * 0.07, -0.69, 0.665), 0.04, "Graphite", (1.0, 1.4, 1.0))              # boots
pilot.finish(G["Cockpit_Cell"])

# ================================================================ 3. WINGS (short, at the rear, going down)
WING = [(0.74, 0.65, 2.16), (1.20, 1.78, 2.22)]   # x, leading edge y, trailing edge y
ANHEDRAL = math.radians(20)


def wing_at(x):
    le, te = table(WING, x)
    f = (x - 0.78) / 0.42
    return le, te, 0.46 - (x - 0.78) * math.tan(ANHEDRAL), 0.075 - 0.04 * f


def wing_top(x):
    le, te, mid, th = wing_at(x)
    return mid + th / 2


def wing_loop(x, grow=0.0):
    le, te, mid, th = wing_at(x)
    th += 2 * grow
    le, te = le - grow, te + grow
    e = min(0.08, 0.08 * (te - le))
    return [(le, mid - th / 6), (le, mid + th / 6), (le + e, mid + th / 2), (te - 0.03, mid + th / 2),
            (te, mid + th / 6), (te, mid - th / 6), (te - 0.03, mid - th / 2), (le + e, mid - th / 2)]


WING_X = [0.74, 1.20]
for s, side in ((1, "R"), (-1, "L")):
    gw = G["Wing_" + side]

    def w3d(x, y, z, s=s):
        return Vector((s * x, y, z))

    def w_centre(c):
        le, te, mid, th = wing_at(abs(c.x))
        return Vector((c.x, (le + te) / 2, mid))

    spar = Part("Wing_Structure_" + side)
    p0, p1 = wing_at(0.74), wing_at(1.17)
    for f in (0.45, 0.90):
        a = (0.72, p0[0] + f * (p0[1] - p0[0]), p0[2])
        b = (1.17, p1[0] + f * (p1[1] - p1[0]), p1[2])
        spar.tube([(s * a[0], a[1], a[2]), (s * b[0], b[1], b[2])], 0.018 if f < 0.5 else 0.013, "Metal",
                  square=True)
    for x in (0.90, 1.05, 1.17):
        L = inset(wing_loop(x), 0.010)
        spar.loft([[Vector((s * (x + d), p.x, p.y)) for p in L] for d in (-0.005, 0.005)], lambda i, j: "Metal",
                  closed_u=True, cap0="Metal", cap1="Metal")
    zr = wing_at(0.74)[2]
    for f in (0.45, 0.90):
        y = p0[0] + f * (p0[1] - p0[0])
        spar.box((s * 0.74, y, zr), (0.06, 0.10, 0.09), "Metal")                         # root clamps
    spar.finish(gw, bevel=0.002)

    def skin(name, t0, t1, m_fn, cuts=()):
        p = Part(name + "_" + side)
        surface(p, wing_loop, t0, t1, 0.74, 1.20, WING_X, w3d, (False, False))
        orient_out(p, w_centre)
        paint(p, m_fn, cuts)
        return shell(p, gw, thick=0.006, bevel=0.0015)

    def top_paint(c, n, s=s):
        return "Paint_Orange" if (c - Vector((s * 0.8, 1.95, 0))).dot(Vector((s * 0.1, 1, 0))) > 0 else "Paint_Steel"

    skin("Wing_Top", 2, 3, top_paint, [((s * 0.8, 1.95, 0.4), (s * 0.1, 1, 0))])
    skin("Wing_Bottom", 6, 7, lambda c, n: "Graphite")
    skin("Wing_TE", 3, 6, lambda c, n: "Paint_Dark")
    skin("Wing_LE", 7, 10, lambda c, n: "Paint_Dark")
    tip = Part("Wing_Tip_" + side)
    L = wing_loop(1.20 - GAP / 2)
    tip.loft([[Vector((s * (1.20 - GAP / 2 - d), p[0], p[1])) for p in L] for d in (0, 0.01)],
             lambda i, j: "Paint_Dark", closed_u=True, cap0="Paint_Dark", cap1="Paint_Dark")
    tip.finish(gw, bevel=0.002, skin=True)

slots = []
for s in (-1, 1):
    p = Part("cut")
    rows = [[Vector((s * x, a, b)) for a, b in wing_loop(x, GAP / 2)] for x in (0.72, 0.95)]
    p.loft(rows, lambda i, j: "Black", closed_u=True, cap0="Black", cap1="Black")
    slots.append(cutter(p))

# ================================================================ 4. BODYWORK
# ---- the arms: open intake at the tip, top with the orange edges, outer and inner sides, chines, belly
for s, side in ((1, "R"), (-1, "L")):
    ga, L_ = G["Arm_" + side], arm_loop(s)
    cap = Part("Arm_Tip_" + side)
    surface(cap, L_, 0, 10, -3.25, -2.95, ARM_Y, xyz, (False, True), wrap=True)
    orient_out(cap, arm_centre(s))
    paint(cap, trim())
    shell(cap, ga)
    panel("Arm_Top_" + side, L_, 3, 7, -2.95, Y_JOIN, ARM_Y, ga, arm_paint, arm_centre(s), cuts=STRIPES)
    panel("Arm_Outer_" + side, L_, 2, 3, -2.95, Y_JOIN, ARM_Y, ga, arm_paint, arm_centre(s), cuts=STRIPES,
          holes=vent_cuts)
    panel("Arm_Inner_" + side, L_, 7, 8, -2.95, Y_JOIN, ARM_Y, ga, trim(), arm_centre(s))
    panel("Arm_Chine_Out_" + side, L_, 1, 2, -2.95, Y_JOIN, ARM_Y, ga, lambda c, n: "Metal", arm_centre(s))
    panel("Arm_Chine_In_" + side, L_, 8, 9, -2.95, Y_JOIN, ARM_Y, ga, lambda c, n: "Metal", arm_centre(s))
    panel("Arm_Belly_" + side, L_, 9, 11, -2.95, Y_JOIN, ARM_Y, ga, lambda c, n: "Graphite", arm_centre(s),
          holes=arm_cuts)

# ---- the bridge and rear body: sides with the wing slots and vents, chines, belly, deck strips beside the spine
for side, s in (("R", 1), ("L", -1)):
    def span(a, b, s=s):
        return (a, b) if s > 0 else ((lambda y: 10 - b(y)) if callable(b) else 10 - b,
                                     (lambda y: 10 - a(y)) if callable(a) else 10 - a)
    panel("Body_Side_" + side, body_loop, *span(2, 3), Y_JOIN, Y_TAIL, BODY_Y, B, trim(), body_centre, holes=slots + vent_cuts)
    panel("Body_Chine_" + side, body_loop, *span(1, 2), Y_JOIN, Y_TAIL, BODY_Y, B, lambda c, n: "Metal", body_centre)
    panel("Deck_" + side, body_loop, *span(3, lambda y: deck_t(y, pod(y)["w"] + 0.005)), Y_JOIN, Y_TAIL, BODY_Y, B, trim(),
          body_centre)
panel("Body_Belly", body_loop, 9, 11, Y_JOIN, Y_TAIL, BODY_Y, B, lambda c, n: "Graphite", body_centre, holes=body_cuts)
drop(slots + vent_cuts + arm_cuts + body_cuts)

# front of the bridge between the arms, with the opening where the pod goes in
xi = arm(Y_JOIN)["xc"] - arm(Y_JOIN)["w"]
b0 = body(Y_JOIN)
crotch = Part("Bridge_Front")
pts = [(-xi + GAP / 2, b0["zb"]), (xi - GAP / 2, b0["zb"]), (xi - GAP / 2, b0["zt"]), (-xi + GAP / 2, b0["zt"])]
ring = [Vector((x, Y_JOIN, z)) for x, z in pts]
crotch.loft([ring, [p + Vector((0, SKIN, 0)) for p in ring]], lambda i, j: "Paint_Dark", closed_u=True,
            cap0="Paint_Dark", cap1="Paint_Dark")
ob = crotch.finish(B, skin=True)
c = Part("cut")
pl = [Vector((x, Y_JOIN - 0.05, z)) for x, z in inset(octa(pod_loop(Y_JOIN)), -GAP / 2)]
c.loft([pl, [p + Vector((0, 0.10, 0)) for p in pl]], lambda i, j: "Black", closed_u=True, cap0="Black", cap1="Black")
cc = cutter(c)
boolean(ob, [cc])
drop([cc])
shade(ob, 0.002)

# tail: heat shield across the rear body with the two engines through it
tail = Part("Tail_Cap")
ring = [Vector((x, Y_TAIL - GAP / 2, z)) for x, z in body_loop(Y_TAIL)]
tail.loft([ring, [p + Vector((0, SKIN, 0)) for p in ring]], lambda i, j: "Ceramic", closed_u=True, cap0="Ceramic",
          cap1="Ceramic")
tail.box((0, Y_TAIL + SKIN, 0.40), (0.30, 0.008, 0.025), "Emit_Red")
ob = tail.finish(B, skin=True)
holes = []
for s in (-1, 1):
    c = Part("cut")
    c.cyl((s * ENG_X, Y_TAIL - 0.05, ENG_Z), (s * ENG_X, Y_TAIL + 0.05, ENG_Z), ENG_R + 0.012, "Black", 32)
    holes.append(cutter(c))
boolean(ob, holes)
drop(holes)
shade(ob, 0.002)

# ---- the cockpit pod: nose, sides, chines, belly, orange cowls round the canopy, then the spine behind it
P = G["Cockpit_Cell"]
nose = Part("Pod_Nose")
rows = surface(nose, pod_loop, 0, 10, -1.40, -0.90, POD_Y, xyz, (False, True), wrap=True)
nose.poly(rows[0][::-1], "Paint_Dark")
orient_out(nose, lambda c: Vector((0, -0.85, 0.72)))
paint(nose, lambda c, n: "Paint_Dark" if n.y < -0.7 else trim()(c, n))
shell(nose, P)
lens = Part("Pod_Sensor")
lens.cyl((0, -1.39, 0.685), (0, -1.415, 0.685), 0.022, "Graphite", 16)
lens.cyl((0, -1.415, 0.685), (0, -1.418, 0.685), 0.015, "Black", 16)
lens.finish(P)
for side, s in (("R", 1), ("L", -1)):
    a, b = (2, 3) if s > 0 else (7, 8)
    panel("Pod_Side_" + side, pod_loop, a, b, -0.90, Y_JOIN, POD_Y, P, trim(), pod_centre)
    a, b = (1, 2) if s > 0 else (8, 9)
    panel("Pod_Chine_" + side, pod_loop, a, b, -0.90, Y_JOIN, POD_Y, P, lambda c, n: "Paint_Dark", pod_centre)
    a, b = (3, 4) if s > 0 else (6, 7)
    panel("Pod_Cowl_" + side, pod_loop, a, b, -0.90, Y_JOIN, POD_Y, P, lambda c, n: "Paint_Orange", pod_centre)
panel("Pod_Belly", pod_loop, 9, 11, -0.90, Y_JOIN, POD_Y, P, lambda c, n: "Graphite", pod_centre)

spine_top = panel("Spine_Top", spine_loop, 1, 5, Y_JOIN, Y_TAIL, POD_Y, B, lambda c, n: "Paint_Steel", spine_centre)
split_out(spine_top, (0, 0.92, pod(0.92)["zt"]), (0.20, 0.50, 0.30), "Reactor_Cover", 2)
for side, (a, b) in (("R", (0, 1)), ("L", (5, 6))):
    panel("Spine_Side_" + side, spine_loop, a, b, Y_JOIN, Y_TAIL, POD_Y, B, lambda c, n: "Paint_Orange",
          spine_centre)
L = spine_loop(Y_TAIL - GAP / 2)
cap = Part("Spine_Rear")
ring = [Vector((x, Y_TAIL - GAP / 2, z)) for x, z in L]
cap.loft([ring, [p + Vector((0, SKIN, 0)) for p in ring]], lambda i, j: "Graphite", closed_u=True,
         cap0="Graphite", cap1="Graphite")
cap.finish(B, bevel=0.002, skin=True)
lat = Part("Reactor_Cover_Latches")
for y in (0.69, 1.15):
    for s in (-1, 1):
        lat.box((s * 0.06, y, pod(y)["zt"] + 0.003), (0.04, 0.02, 0.006), "Metal")
lat.finish(G["Reactor"])

# ---- canopy on the pod top, frame, roll hoop behind the pilot
CAN = [(-0.90, .020), (-0.75, .055), (-0.55, .090), (-0.30, .115), (0.0, .130), (0.20, .135), (0.32, .130),
       (0.40, .115)]


def canopy_loop(y, grow=0.0, n=14):
    p = pod(y)
    w = p["w"] - p["ct"] - 0.004
    h = table(CAN, y)[0] + grow
    zb = p["zt"] + 0.004
    return [(w * math.cos(math.pi * k / n) * (1 + grow), zb + h * math.sin(math.pi * k / n) ** 0.55)
            for k in range(n + 1)]


glass = Part("Canopy")
ys = [-0.90, -0.84, -0.78, -0.70, -0.60, -0.48, -0.36, -0.22, -0.10, 0.0, 0.10, 0.20, 0.30, 0.36, 0.40]
glass.loft([[Vector((x, y, z)) for x, z in canopy_loop(y)] for y in ys], lambda i, j: "Glass")
orient_out(glass, lambda c: Vector((0, c.y, pod(c.y)["zt"])))
g = shell(glass, P, thick=0.008, bevel=0.0)
SKINS.remove(g)
frame = Part("Canopy_Frame")
for s in (-1, 1):
    frame.tube([(s * (pod(y)["w"] - pod(y)["ct"]), y, pod(y)["zt"] + 0.006) for y in ys], 0.010, "Graphite", 8)
for y in (-0.90, -0.30):
    frame.tube([Vector((x, y, z + 0.005)) for x, z in canopy_loop(y, 0.01)], 0.010, "Graphite", 8)
frame.finish(P)
hoop = Part("Roll_Hoop")
hoop.tube([Vector((x, 0.415, z)) for x, z in canopy_loop(0.40, 0.03)], 0.018, "Metal", 12)
hoop.finish(P)

# ================================================================ 5. DECALS (our own marks)
dec = Part("Decals")
for s in (-1, 1):
    rd = 1 if s > 0 else -1                 # text reads from the front to the back on both sides

    def outer(y, s=s):
        a = arm(y)
        return s * (a["xc"] + a["w"])

    def side_frame(y, z, y0, y1, lift=0.0025, s=s):
        slope = (outer(y1) - outer(y0)) / (y1 - y0)
        return frame_on((outer(y), y, z), Vector((slope, 1.0, 0)) * rd, (0, 0, 1), lift)

    a = arm(-1.80)
    zc = (a["zb"] + a["cb"] + a["zs"]) / 2
    dec.add_mesh(text_mesh("WRAITH", 0.12), side_frame(-1.80, zc, -2.60, -1.20), "Paint_White")
    a = arm(-2.80)
    zt_ = (a["zb"] + a["cb"] + a["zs"]) / 2
    for dy in (-0.07, 0.07):                                                                # warning triangles
        M = side_frame(-2.80 + dy * rd, zt_, -3.25, -2.60)
        dec.poly([M @ Vector(p) for p in ((0, 0.035, 0), (-0.03, -0.018, 0), (0.03, -0.018, 0))], "Paint_Red")
    M = side_frame(0.10, zc + 0.02, -1.20, Y_JOIN)                                          # status light
    dec.poly([M @ Vector(p) for p in ((-0.06, -0.008, 0), (0.06, -0.008, 0), (0.06, 0.008, 0), (-0.06, 0.008, 0))],
             "Emit_Green")
    # race number on a white roundel on the pod sides
    y, p = -0.62, pod(-0.62)
    zn = (p["zb"] + p["cb"] + p["zs"]) / 2
    slope = (pod(-0.40)["w"] - pod(-0.90)["w"]) / 0.50
    u = Vector((slope * s, 1.0, 0)) * rd
    dec.flat(disc2d(0.075), frame_on((s * p["w"], y, zn), u, (0, 0, 1)), "Paint_White")
    dec.add_mesh(text_mesh("13", 0.09), frame_on((s * p["w"], y, zn), u, (0, 0, 1), 0.004), "Black")
    # league emblem on the wing tops
    xc, yc = 1.00, 1.66
    d = (wing_top(xc + 0.05) - wing_top(xc - 0.05)) / 0.1
    M = frame_on((s * xc, yc, wing_top(xc) + 0.0005), (s, 0, d), (0, s, 0))
    o, i_ = ring2d(0.09, 0.11)
    dec.flat(o, M, "Paint_White", holes=[i_])
    star = [((0.08 if k % 2 == 0 else 0.02) * math.cos(math.pi / 2 + k * math.pi / 4),
             (0.08 if k % 2 == 0 else 0.02) * math.sin(math.pi / 2 + k * math.pi / 4)) for k in range(8)]
    dec.poly([M @ Vector((x, y_, 0)) for x, y_ in star], "Paint_White")
dec.finish(G["Decals"], recalc=False, smooth_angle=10)

# ================================================================ sockets
for name, loc in (("Socket_Reactor", (0, 0.91, 0.815)), ("Socket_Propulsion_L", (-ENG_X, EY1, ENG_Z)),
                  ("Socket_Propulsion_R", (ENG_X, EY1, ENG_Z)), ("Socket_Wing_L", (-0.74, 1.40, wing_at(0.74)[2])),
                  ("Socket_Wing_R", (0.74, 1.40, wing_at(0.74)[2])), ("Socket_Tail", (0, Y_TAIL + 0.01, 0.40)),
                  ("Socket_Armor_L", (-0.83, -0.80, 0.42)), ("Socket_Armor_R", (0.83, -0.80, 0.42)),
                  ("Socket_Cooling", (0, 1.40, 0.58)), ("Socket_Utility", (0, -1.40, 0.685))):
    group(name, G["Sockets"], loc)

finish_ship(G["Decals"], cockpit=((-1.5, -1.7, 1.75), (0, 0.0, 0.92)))
