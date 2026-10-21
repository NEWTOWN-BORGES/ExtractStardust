# WRAITH hover racer (light, for skilled pilots), built from the inside out like the STRIX: structure first (frames
# and longerons in each arm, bridge frames, the cross beam in the fork and the braces that hold the cockpit pod), then
# the systems (cockpit and pilot, reactor, three round plasma engines at the rear inside a shroud, the side ones
# cooled through ducts from intakes at the arm tips, radiators, hover emitters), then the 12 mm bodywork panels.
# Look: fork (U) plan - two long arms forward with open space between them, lying (wider than tall, high off the
# ground like wings): flat side towards the cockpit, rounded side out; the cockpit pod at the base of the U with its
# top level with the arms and its glass flush with the body, a rear that tapers into a lying rounded box (the shroud)
# holding three engines, two long shark fins over it, short wings going down; green with white trim and yellow bands
# (Docs/WRAITH_CATEGORIA.md).
# Front is -Y, up is +Z, metres (the layout of the old SourceArt/TestShips/wraith.fbx; the game centres the bounds).
# Usage: python3 Scripts/build_wraith.py <out_dir> [--no-render]
#    or: blender -b -P Scripts/build_wraith.py -- <out_dir> [--no-render]
# Writes <out_dir>/wraith.blend, wraith.fbx and the preview renders. Shared parts: Scripts/ship_kit.py.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ship_kit import *  # noqa: E402,F401,F403  (bpy, bmesh, math, Matrix, Vector and the helpers)

start("WRAITH")
material("Paint_Green", "#2E8F52", rough=0.32, coat=0.5)
material("Paint_Dark", "#33403A", rough=0.35, coat=0.5)
material("Paint_Accent", "#E4EBE6", rough=0.3, coat=0.6)
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
material("Emit_Plasma", "#8FDFFF", emit=10.0, rough=0.3)

ROOT = group("ShipRoot")
G = {n: group(n, ROOT) for n in ("Structural_Core", "Arm_L", "Arm_R", "Cockpit_Cell", "Body", "Reactor",
                                 "Propulsion", "Wing_L", "Wing_R", "Hover", "Cooling", "Decals", "Sockets")}
B = G["Body"]

# ---------------------------------------------------------------- lines
#        y      xi    xo    zb    zt      (arms lying: inner flat wall at xi, rounded outer side reaching xo; high off the
#                                         ground like wings, the tops level with the cockpit pod at the root)
ARM = [(-3.25, .520, .760, .500, .660),
       (-2.60, .470, .800, .510, .720),
       (-1.20, .420, .830, .520, .790),
       (0.40, .400, .840, .540, .840)]
ARM_C = 0.02                        # chamfer of the inner wall's edges
ARM_ROUND = 1.1                     # outer side: half ellipse, horizontal radius = 1.1 x half the height
#         y     w     zb    cb    zs    ct    zt         (the bridge at the base of the U and the rear body)
BODY = [(0.40, .840, .260, .050, .740, .090, .840),
        (1.40, .860, .270, .050, .760, .120, .860),
        (2.20, .840, .300, .050, .760, .140, .860),
        (2.70, .685, .335, .100, .685, .110, .785)]
#        y      w     zb    cb    zs    ct    zt         (cockpit pod; from 0.40 back it is the spine on the bridge)
POD = [(-1.40, .080, .560, .030, .640, .030, .680),
       (-0.90, .200, .470, .060, .740, .080, .840),
       (-0.40, .260, .440, .080, .800, .100, .910),
       (0.00, .280, .430, .080, .830, .110, .940),
       (0.40, .290, .430, .080, .880, .110, .950),
       (1.40, .270, .660, .050, .900, .100, .940),
       (2.00, .220, .700, .040, .875, .060, .885)]
ARM_Y, BODY_Y, POD_Y = [r[0] for r in ARM], [r[0] for r in BODY], [r[0] for r in POD]
Y_JOIN, Y_SPINE, Y_TAIL = 0.40, 2.00, 2.70


def arm(y):
    xi, xo, zb, zt = table(ARM, y)
    rx = ARM_ROUND * (zt - zb) / 2
    return {"xi": xi, "xo": xo, "zb": zb, "zt": zt, "xc": (xi + xo) / 2, "w": (xo - xi) / 2, "zm": (zb + zt) / 2,
            "rx": rx, "xb": (xi + ARM_C + xo - rx) / 2, "wb": (xo - rx - xi - ARM_C) / 2}


def body(y):
    return dict(zip(("w", "zb", "cb", "zs", "ct", "zt"), table(BODY, y)))


def pod(y):
    return dict(zip(("w", "zb", "cb", "zs", "ct", "zt"), table(POD, y)))


def arm_loop(s):
    """Lying arm section, from the bottom under the arm centre round the outer side (counter-clockwise for the right arm;
    the left arm is its mirror): t 0..1 belly, 1..9 the rounded outer side, 9..11 top, 11..14 the flat inner wall with
    its chamfers, 14..15 belly."""
    def f(y):
        a = arm(y)
        xr, rz = a["xo"] - a["rx"], (a["zt"] - a["zb"]) / 2
        L = [(a["xc"], a["zb"]), (xr, a["zb"])]
        L += [(xr + a["rx"] * math.cos(th), a["zm"] + rz * math.sin(th))
              for th in (math.radians(-90 + 22.5 * k) for k in range(1, 8))]
        L += [(xr, a["zt"]), (a["xc"], a["zt"]), (a["xi"] + ARM_C, a["zt"]), (a["xi"], a["zt"] - ARM_C),
              (a["xi"], a["zb"] + ARM_C), (a["xi"] + ARM_C, a["zb"])]
        return [(s * x, z) for x, z in L]
    return f


def body_loop(y):
    b = body(y)
    return loop10(0, b["w"], b["zb"], b["cb"], b["zs"], b["ct"], b["zt"])


def pod_loop(y):
    p = pod(y)
    return loop10(0, p["w"], p["zb"], p["cb"], p["zs"], p["ct"], p["zt"])


def spine_loop(y):    # the pod behind the cockpit, standing on the bridge deck: open at the base, t 0..6
    p = pod(y)
    return block_loop(p["w"], body(y)["zt"], p["zs"], p["w"] - p["ct"], p["zt"])


def xyz(y, x, z):
    return Vector((x, y, z))


def arm_centre(s):
    return lambda c: Vector((s * arm(c.y)["xc"], c.y, arm(c.y)["zm"]))


def body_centre(c):
    return Vector((0, c.y, (body(c.y)["zb"] + body(c.y)["zt"]) / 2))


def pod_centre(c):
    return Vector((0, c.y, (pod(c.y)["zb"] + pod(c.y)["zt"]) / 2))


def spine_centre(c):
    return Vector((0, c.y, body(c.y)["zt"] - 0.05))


def trim(base="Paint_Green", chamfer="Paint_Accent"):
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


def ring_frames(part, loop_fn, ys, pick=octa):
    for y in ys:
        oc = pick(loop_fn(y))
        o, i_ = inset(oc, SKIN + CLEAR), inset(oc, SKIN + CLEAR + 0.03)
        rows = [[Vector((p.x, y + dy, p.y)) for p in ring] for ring, dy in
                ((o, -0.012), (o, 0.012), (i_, 0.012), (i_, -0.012))]
        part.loft(rows, lambda i, j: "Metal", closed_u=True, closed_v=True)


def longerons(part, loop_fn, y0, y1, stations, corners, r=0.010, pick=octa):
    for k in corners:
        path = []
        for y in [y0] + [s for s in stations if y0 < s < y1] + [y1]:
            p = inset(pick(loop_fn(y)), SKIN + CLEAR + r + 0.004)[k]
            path.append((p.x, y, p.y))
        part.tube(path, r, "Metal", square=True)


fr = Part("Frames")
for s in (-1, 1):
    ring_frames(fr, arm_loop(s), (-2.90, -2.00, -1.10, -0.20), list)
ring_frames(fr, body_loop, (0.46, 1.15, 2.14))
ring_frames(fr, pod_loop, (-1.00, -0.55))
fr.finish(G["Structural_Core"], bevel=0.002)

lon = Part("Longerons")
for s in (-1, 1):
    longerons(lon, arm_loop(s), -3.00, Y_JOIN, ARM_Y, (1, 9, 11, 14), pick=list)
longerons(lon, body_loop, 0.46, 2.14, BODY_Y, (0, 1, 2, 5, 6, 7))
lon.finish(G["Structural_Core"], bevel=0.002)

# the braces that hold the front of the cockpit pod to the arms' inner walls (open structure, seen from outside)
fork = Part("Fork_Structure")
for s in (-1, 1):
    a = arm(-0.85)
    top = Vector((s * 0.12, -0.62, pod(-0.62)["zb"] - 0.006))
    foot = Vector((s * (a["xi"] + 0.006), -0.85, a["zm"]))
    fork.tube([top, foot], 0.017, "Metal", 10)
    fork.box(top + Vector((0, 0, -0.006)), (0.06, 0.08, 0.012), "Metal")              # brackets
    fork.box(foot + Vector((s * 0.006, 0, 0)), (0.012, 0.08, 0.07), "Metal")
fork.finish(G["Structural_Core"], bevel=0.002)

# ================================================================ 2. SYSTEMS
# ---- two plasma engines at the rear; the intakes at the arm tips duct cooling air to their coils
ENG_X, ENG_Z, ENG_R = 0.45, 0.56, 0.17
ENG_SEC = circle_loop(ENG_R)
EY0, EY1 = 1.30, Y_TAIL             # plasma chamber, end of the casing at the tail
GE = G["Propulsion"]
for x, side, y0, saddles in ((-ENG_X, "L", EY0, (1.62, 2.02)), (0.0, "C", 1.62, (1.80, 2.40)),
                             (ENG_X, "R", EY0, (1.62, 2.02))):
    eng = Part("Engine_" + side)
    EXIT = space_engine(eng, (x, ENG_Z), y0, EY1, ENG_SEC)
    for y in saddles:                                                                     # saddles on the belly
        zb = body(y)["zb"] + SKIN + CLEAR
        eng.box((x, y, (zb + ENG_Z - ENG_R + 0.01) / 2), (0.14, 0.08, ENG_Z - ENG_R + 0.01 - zb), "Metal")
    eng.finish(GE, bevel=0.0)

# intake mouths at the arm tips, funnels and ducts back to the compressor faces (inner faces point inwards)
DUCT_R = 0.055
duct = Part("Intake_Ducts")
lip = Part("Intakes")
for s in (-1, 1):
    a = arm(-3.25)
    mouth = inset(arm_loop(s)(-3.25), SKIN + 0.004)
    nm = len(mouth)
    zc = a["zm"]
    c0 = Vector((s * a["xc"], -3.00, zc))
    circ = [c0 + Vector((math.cos(2 * math.pi * k / nm + math.pi / nm) * DUCT_R * s, 0,
                         math.sin(2 * math.pi * k / nm + math.pi / nm) * DUCT_R)) for k in range(nm)]
    ring3 = [Vector((p.x, -3.24, p.y)) for p in mouth]
    ang = [math.atan2(p.z - zc, (p.x - s * a["xc"]) * s) for p in ring3]
    order = sorted(range(nm), key=lambda k: ang[k] % (2 * math.pi))
    circ_sorted = sorted(circ, key=lambda p: math.atan2(p.z - zc, (p.x - s * a["xc"]) * s) % (2 * math.pi))
    duct.loft([[ring3[k] for k in order], circ_sorted], lambda i, j: "Black", closed_u=True)
    path = [(s * a["xc"], -3.00, zc)]
    for y in (-2.60, -1.20, Y_JOIN):
        q = arm(y)
        path.append((s * q["xc"], y, q["zm"]))
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
rc.lathe((0, 0.55, 0.815), (0, 1.08, 0.815),
         [(0, 0.0), (0.02, 0.06), (0.08, 0.095), (0.18, 0.10), (0.24, 0.092), (0.30, 0.10), (0.70, 0.10),
          (0.76, 0.092), (0.82, 0.10), (0.92, 0.095), (0.98, 0.06), (1, 0.0)],
         lambda k: "Emit_Hot" if k in (3, 4, 7, 8) else "Metal_Bright", 24)
for y in (0.65, 0.98):
    rc.box((0, y, 0.695), (0.22, 0.05, 0.04), "Metal")                                     # saddles
for s in (-1, 1):
    rc.tube([(s * 0.04, 1.10, 0.815), (s * 0.20, 1.25, 0.74), (s * 0.34, 1.50, 0.74), (s * 0.42, 1.60, 0.715)],
            0.013, "Metal", 10)
rc.tube([(0, 1.075, 0.78), (0, 1.30, 0.70), (0, 1.50, 0.64), (0, 1.60, 0.60)], 0.013, "Metal", 10)  # centre engine
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
for s in (-1, 1):
    y0, y1 = -0.70, -0.20
    a = arm((y0 + y1) / 2)
    z0, z1 = a["zm"] - 0.055, a["zm"] + 0.055
    xo = a["xo"]
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
        x = s * (arm(y)["xb"] if where == "arm" else where)
        if where == "arm":
            sx = min(sx, 2 * arm(y)["wb"] - 0.04)
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
for y, x, zb in ((-3.05, arm(-3.05)["xb"], arm(-3.05)["zb"]), (2.10, 0.74, body(2.10)["zb"])):   # sensors
    for s in (-1, 1):
        hover.cyl((s * x, y, zb + 0.01), (s * x, y, zb - 0.012), 0.02, "Graphite", 12)
        hover.cyl((s * x, y, zb - 0.012), (s * x, y, zb - 0.014), 0.013, "Black", 12)
hover.finish(G["Hover"])

# ---- cockpit: floor, dash, controls, seat and pilot (sitting low, the head level with the tops of the arms)
ck = Part("Cockpit_Parts")
ck.box((0, -0.17, 0.47), (0.30, 0.56, 0.012), "Graphite")                                 # floor
ck.box((0, -0.40, 0.80), (0.32, 0.14, 0.07), "Graphite")                                  # dash
ck.box((0, -0.329, 0.815), (0.22, 0.004, 0.045), "Emit_Hover")                            # display
ck.cyl((0, -0.33, 0.78), (0, -0.20, 0.70), 0.015, "Metal", 10)                            # column
ck.box((0, -0.19, 0.70), (0.22, 0.026, 0.026), "Metal")                                   # handlebar
for s in (-1, 1):
    ck.cyl((s * 0.10, -0.19, 0.70), (s * 0.15, -0.19, 0.70), 0.018, "Graphite", 10)
ck.box((0, 0.13, 0.485), (0.32, 0.22, 0.04), "Graphite")                                  # seat
back = Matrix.Rotation(math.radians(-22), 3, 'X')
ck.box((0, 0.33, 0.65), (0.32, 0.045, 0.30), "Graphite", back)                            # back rest
for s in (-1, 1):
    ck.box((s * 0.15, 0.29, 0.63), (0.03, 0.12, 0.26), "Graphite", back)                 # bolsters
ck.finish(G["Cockpit_Cell"], bevel=0.003)

pilot = Part("Pilot")
pilot.tube([(0, 0.11, 0.53), (0, 0.19, 0.64), (0, 0.26, 0.74)], 0.10, "Paint_White", 12)   # torso
pilot.sphere((0, 0.25, 0.76), 0.068, "Paint_White", (1.6, 1.0, 0.7))                     # shoulders
pilot.sphere((0, 0.29, 0.83), 0.095, "Paint_Accent")                                      # helmet
pilot.sphere((0, 0.22, 0.835), 0.052, "Black", (1.3, 0.7, 0.85))                          # visor
for s in (-1, 1):
    pilot.tube([(s * 0.12, 0.25, 0.74), (s * 0.15, 0.05, 0.63), (s * 0.12, -0.19, 0.70)], 0.032, "Paint_White")
    pilot.sphere((s * 0.125, -0.20, 0.70), 0.03, "Graphite")                               # gloves
    pilot.tube([(s * 0.07, 0.10, 0.52), (s * 0.08, -0.32, 0.575), (s * 0.07, -0.66, 0.575)], 0.044, "Paint_White")
    pilot.sphere((s * 0.07, -0.69, 0.575), 0.04, "Graphite", (1.0, 1.4, 1.0))              # boots
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
        return "Paint_Accent" if (c - Vector((s * 0.8, 1.95, 0))).dot(Vector((s * 0.1, 1, 0))) > 0 else "Paint_Green"

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
# ---- the arms: open intake at the tip, flat top, rounded outer side (white along its upper half), flat inner wall,
# belly
for s, side in ((1, "R"), (-1, "L")):
    ga, L_ = G["Arm_" + side], arm_loop(s)
    cap = Part("Arm_Tip_" + side)
    surface(cap, L_, 0, 15, -3.25, -2.95, ARM_Y, xyz, (False, True), wrap=True)
    orient_out(cap, arm_centre(s))
    paint(cap, trim())
    shell(cap, ga)
    panel("Arm_Top_" + side, L_, 9, 11, -2.95, Y_JOIN, ARM_Y, ga, arm_paint, arm_centre(s), cuts=STRIPES)
    panel("Arm_Outer_" + side, L_, 1, 9, -2.95, Y_JOIN, ARM_Y, ga, arm_paint, arm_centre(s), cuts=STRIPES,
          holes=vent_cuts)
    panel("Arm_Inner_" + side, L_, 11, 14, -2.95, Y_JOIN, ARM_Y, ga, lambda c, n: "Paint_Dark", arm_centre(s))
    panel("Arm_Belly_" + side, L_, 14, 16, -2.95, Y_JOIN, ARM_Y, ga, lambda c, n: "Graphite", arm_centre(s),
          holes=arm_cuts)

# ---- the bridge and rear body: sides with the wing slots and vents, chines, belly, deck strips beside the spine
for side, s in (("R", 1), ("L", -1)):
    def span(a, b, s=s):
        return (a, b) if s > 0 else ((lambda y: 10 - b(y)) if callable(b) else 10 - b,
                                     (lambda y: 10 - a(y)) if callable(a) else 10 - a)
    panel("Body_Side_" + side, body_loop, *span(2, 3), Y_JOIN, Y_TAIL, BODY_Y, B, trim(), body_centre, holes=slots + vent_cuts)
    panel("Body_Chine_" + side, body_loop, *span(1, 2), Y_JOIN, Y_TAIL, BODY_Y, B, lambda c, n: "Metal", body_centre)
    panel("Deck_" + side, body_loop, *span(3, lambda y: deck_t(y, pod(y)["w"] + 0.005)), Y_JOIN, Y_SPINE, BODY_Y, B, trim(),
          body_centre)
panel("Deck_Rear", body_loop, 3, 7, Y_SPINE, Y_TAIL, BODY_Y, B, trim(), body_centre)
panel("Body_Belly", body_loop, 9, 11, Y_JOIN, Y_TAIL, BODY_Y, B, lambda c, n: "Graphite", body_centre, holes=body_cuts)
drop(slots + vent_cuts + arm_cuts + body_cuts)

# front of the bridge: its whole section (the arms sit high on it), with the opening where the pod goes in and the
# holes for the intake ducts
crotch = Part("Bridge_Front")
ring = [Vector((x, Y_JOIN, z)) for x, z in inset(body_loop(Y_JOIN), GAP / 2)]
crotch.loft([ring, [p + Vector((0, SKIN, 0)) for p in ring]], lambda i, j: "Paint_Dark", closed_u=True,
            cap0="Paint_Dark", cap1="Paint_Dark")
ob = crotch.finish(B, skin=True)
c = Part("cut")
pl = [Vector((x, Y_JOIN - 0.05, z)) for x, z in inset(octa(pod_loop(Y_JOIN)), -GAP / 2)]
c.loft([pl, [p + Vector((0, 0.10, 0)) for p in pl]], lambda i, j: "Black", closed_u=True, cap0="Black", cap1="Black")
cc = [cutter(c)]
for s in (-1, 1):
    c = Part("cut")
    a = arm(Y_JOIN)
    c.cyl((s * a["xc"], Y_JOIN - 0.05, a["zm"]), (s * a["xc"], Y_JOIN + 0.05, a["zm"]), DUCT_R + 0.006, "Black", 16)
    cc.append(cutter(c))
boolean(ob, cc)
drop(cc)
shade(ob, 0.002)

# tail: heat shield across the rear body with the two engines through it
tail = Part("Tail_Cap")
ring = [Vector((x, Y_TAIL - GAP / 2, z)) for x, z in body_loop(Y_TAIL)]
tail.loft([ring, [p + Vector((0, SKIN, 0)) for p in ring]], lambda i, j: "Ceramic", closed_u=True, cap0="Ceramic",
          cap1="Ceramic")
ob = tail.finish(B, skin=True)
holes = []
for x in (-ENG_X, 0.0, ENG_X):
    c = Part("cut")
    c.cyl((x, Y_TAIL - 0.05, ENG_Z), (x, Y_TAIL + 0.05, ENG_Z), ENG_R + 0.012, "Black", 32)
    holes.append(cutter(c))
boolean(ob, holes)
drop(holes)
shade(ob, 0.002)

# shroud: plates round the three engines, a lying box with rounded corners that carries the body on and holds the
# engines inside (outer skin tapers a little; orange band and bright lip at the exit)
sh = Part("Engine_Shroud")
b1 = body(Y_TAIL)
hw0, hh0, zc = b1["w"], (b1["zt"] - b1["zb"]) / 2, (b1["zt"] + b1["zb"]) / 2
rows = []
for y, hw, hh, r in ((Y_TAIL + GAP / 2, hw0, hh0, 0.10), (2.98, hw0 - 0.010, hh0 - 0.006, 0.098),
                     (3.06, hw0 - 0.015, hh0 - 0.009, 0.096), (3.06, hw0 - 0.03, hh0 - 0.03, 0.07),
                     (Y_TAIL + GAP / 2, hw0 - 0.03, hh0 - 0.03, 0.07)):
    rows.append([Vector((x, y, zc + z)) for x, z in shape_loop(hw, hw, hh, r)])
sh.loft(rows, lambda i, j: ("Paint_Green", "Paint_Accent", "Metal_Bright", "Graphite", "Graphite")[i], closed_u=True,
        closed_v=True)
sh.box((0, 3.062, zc - hh0 + 0.02), (0.12, 0.004, 0.012), "Emit_Red")                    # tail light
sh.finish(B, bevel=0.002, skin=True)

# two long shark fins on the deck, over the engines, leaning out
fin = Part("Shark_Fins")
for s in (-1, 1):
    shark_fin(fin, lambda y: body(y)["zt"], s * ENG_X, (1.55, 2.68), (2.30, 2.92), 0.22, 0.03, "Paint_Accent",
              "Paint_Dark", math.radians(12), s)
fin.finish(B, bevel=0.0015, smooth_angle=60, skin=True)

# ---- the cockpit pod: nose, orange sides, chines, belly, flush glass on top, then the spine behind it
P = G["Cockpit_Cell"]
nose = Part("Pod_Nose")
rows = surface(nose, pod_loop, 0, 10, -1.40, -0.90, POD_Y, xyz, (False, True), wrap=True)
nose.poly(rows[0][::-1], "Paint_Dark")
orient_out(nose, lambda c: Vector((0, -0.85, 0.65)))
paint(nose, lambda c, n: "Paint_Dark" if n.y < -0.7 else trim()(c, n))
shell(nose, P)
lens = Part("Pod_Sensor")
lens.cyl((0, -1.39, 0.62), (0, -1.415, 0.62), 0.022, "Graphite", 16)
lens.cyl((0, -1.415, 0.62), (0, -1.418, 0.62), 0.015, "Black", 16)
lens.finish(P)
for side, s in (("R", 1), ("L", -1)):
    a, b = (2, 3) if s > 0 else (7, 8)
    panel("Pod_Side_" + side, pod_loop, a, b, -0.90, Y_JOIN, POD_Y, P, trim("Paint_Accent"), pod_centre)
    a, b = (1, 2) if s > 0 else (8, 9)
    panel("Pod_Chine_" + side, pod_loop, a, b, -0.90, Y_JOIN, POD_Y, P, lambda c, n: "Paint_Dark", pod_centre)
panel("Pod_Belly", pod_loop, 9, 11, -0.90, Y_JOIN, POD_Y, P, lambda c, n: "Graphite", pod_centre)

spine_top = panel("Spine_Top", spine_loop, 1, 5, Y_JOIN, Y_SPINE, POD_Y, B, lambda c, n: "Paint_Green", spine_centre)
split_out(spine_top, (0, 0.82, pod(0.82)["zt"]), (0.20, 0.44, 0.30), "Reactor_Cover", 2)
for side, (a, b) in (("R", (0, 1)), ("L", (5, 6))):
    panel("Spine_Side_" + side, spine_loop, a, b, Y_JOIN, Y_SPINE, POD_Y, B, lambda c, n: "Paint_Accent",
          spine_centre)
L = spine_loop(Y_SPINE - GAP / 2)
cap = Part("Spine_Rear")
ring = [Vector((x, Y_SPINE - GAP / 2, z)) for x, z in L]
cap.loft([ring, [p + Vector((0, SKIN, 0)) for p in ring]], lambda i, j: "Graphite", closed_u=True,
         cap0="Graphite", cap1="Graphite")
cap.finish(B, bevel=0.002, skin=True)
lat = Part("Reactor_Cover_Latches")
for y in (0.62, 1.02):
    for s in (-1, 1):
        lat.box((s * 0.06, y, pod(y)["zt"] + 0.003), (0.04, 0.02, 0.006), "Metal")
lat.finish(G["Reactor"])

# ---- canopy: glass flush with the pod top (no bubble), framed; the roll hoop is inside, behind the pilot
CAN_Y = (-0.90, Y_JOIN)
panel("Canopy", pod_loop, 3, 7, CAN_Y[0], CAN_Y[1], POD_Y, P, lambda c, n: "Glass", pod_centre, thick=0.008)
frame = Part("Canopy_Frame")
ys = [CAN_Y[0]] + [y for y in POD_Y if CAN_Y[0] < y < CAN_Y[1]] + [CAN_Y[1]]
for t in (3, 7):
    frame.tube([Vector((pt(pod_loop(y), t)[0], y, pt(pod_loop(y), t)[1] + 0.002)) for y in ys], 0.009, "Graphite", 8)
for y in (CAN_Y[0] + 0.004, -0.25, CAN_Y[1] - 0.004):
    L = pod_loop(y)
    frame.tube([Vector((pt(L, t)[0], y, pt(L, t)[1] + 0.003)) for t in (3, 3.5, 4, 5, 6, 6.5, 7)], 0.009, "Graphite",
               8)
frame.finish(P)
hoop = Part("Roll_Hoop")
L = inset(octa(pod_loop(0.43)), SKIN + CLEAR + 0.015)
hoop.tube([Vector((q.x, 0.43, q.y)) for q in L[2:6]], 0.015, "Metal", 10)
hoop.finish(P)

# ================================================================ 5. DECALS (our own marks)
dec = Part("Decals")
for s in (-1, 1):
    rd = 1 if s > 0 else -1                 # text reads from the front to the back on both sides

    def top_frame(y, lift=0.0025, s=s):      # on the flat arm top, reading from that side of the ship
        def P(y_):
            a = arm(y_)
            return Vector((s * (a["xi"] + ARM_C + a["xo"] - a["rx"]) / 2, y_, a["zt"]))
        return frame_on(P(y), (P(y + 0.05) - P(y - 0.05)) * -s, (s, 0, 0), lift)

    dec.add_mesh(text_mesh("WRAITH", 0.12), top_frame(-1.80), "Paint_White")
    for dy in (-0.07, 0.07):                                                                # warning triangles
        M = top_frame(-2.80 + dy)
        dec.poly([M @ Vector(p) for p in ((0, 0.035, 0), (-0.03, -0.018, 0), (0.03, -0.018, 0))], "Paint_Red")
    M = top_frame(0.10)                                                                     # status light
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
for name, loc in (("Socket_Reactor", (0, 0.91, 0.815)), ("Socket_Propulsion_L", (-ENG_X, EXIT, ENG_Z)),
                  ("Socket_Propulsion_R", (ENG_X, EXIT, ENG_Z)), ("Socket_Propulsion_C", (0, EXIT, ENG_Z)), ("Socket_Wing_L", (-0.74, 1.40, wing_at(0.74)[2])),
                  ("Socket_Wing_R", (0.74, 1.40, wing_at(0.74)[2])), ("Socket_Tail", (0, 3.06, zc - hh0)),
                  ("Socket_Armor_L", (-arm(-0.80)["xo"], -0.80, arm(-0.80)["zm"])),
                  ("Socket_Armor_R", (arm(-0.80)["xo"], -0.80, arm(-0.80)["zm"])),
                  ("Socket_Cooling", (0, 1.40, 0.58)), ("Socket_Utility", (0, -1.40, 0.62))):
    group(name, G["Sockets"], loc)

finish_ship(G["Decals"], cockpit=((-1.5, -1.7, 1.75), (0, 0.0, 0.92)))
