# NOMAD hover racer (expedition endurance), built from the inside out like the STRIX and the WRAITH: structure (hull
# frames and longerons, boom arches, crash bumper, cabin cage, pod pylons, cargo rails, stabilizer spars), systems
# (cockpit and pilot, reactor and its lines, three plasma engines, radiators, tanks, hover emitters), then the 12 mm
# bodywork panels with 5 mm gaps.
# Look: long boxy faceted hull with a blunt armoured nose (grille face, lights, bumper), a raised cabin at the front
# with flush windows and small A-shaped canards, a long boom on top that runs past the tail and ends in a rectangular
# engine, two rectangular engine pods hung from orange A-shaped arms off the boom, a cargo and tank module under the
# rear, long low stabilizers; white, black
# and orange with hazard stripes (Docs/NOMAD_CATEGORIA.md, Docs/NAVES_REGRAS.md).
# Front is -Y, up is +Z, metres (the layout of the old SourceArt/TestShips/nomad.fbx; the game centres the bounds).
# Usage: python3 Scripts/build_nomad.py <out_dir> [--no-render]
#    or: blender -b -P Scripts/build_nomad.py -- <out_dir> [--no-render]
# Writes <out_dir>/nomad.blend, nomad.fbx and the preview renders. Shared parts: Scripts/ship_kit.py.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ship_kit import *  # noqa: E402,F401,F403  (bpy, bmesh, math, Matrix, Vector and the helpers)

start("NOMAD")
material("Paint_White", "#E9EBED", rough=0.35, coat=0.4)
material("Paint_Grey", "#AEB4BA", rough=0.45, coat=0.3)
material("Paint_Black", "#2B2D30", rough=0.4, coat=0.3)
material("Paint_Orange", "#E8702A", rough=0.32, coat=0.5)
material("Graphite", "#2B2E33", rough=0.6)
material("Black", "#101113", rough=0.35)
material("Metal", "#7E848B", metal=1.0, rough=0.45)
material("Metal_Bright", "#C2C7CC", metal=1.0, rough=0.22)
material("Ceramic", "#BDB6AA", rough=0.8)
material("Glass", "#9FC6DA", rough=0.03, alpha=0.25)
material("Emit_Hover", "#5FE3FF", emit=3.0, rough=0.3)
material("Emit_Hot", "#FF7A2E", emit=6.0, rough=0.3)
material("Emit_Red", "#FF2A2A", emit=4.0, rough=0.3)
material("Emit_Plasma", "#8FDFFF", emit=10.0, rough=0.3)
material("Emit_Light", "#FFF2D0", emit=8.0, rough=0.2)

ROOT = group("ShipRoot")
G = {n: group(n, ROOT) for n in ("Structural_Core", "Nose", "Cockpit_Cell", "Body", "Boom", "Reactor", "Propulsion",
                                 "Pod_L", "Pod_R", "Wing_L", "Wing_R", "Hover", "Cooling", "Cargo", "Decals",
                                 "Sockets")}
B = G["Body"]

# ---------------------------------------------------------------- lines
#        y      w     zb    cb    zs    ct    zt       (hull; the bottom steps up over the cargo module at 0.55-0.65)
HULL = [(-3.70, .520, .400, .080, .820, .100, .920),
        (-3.20, .640, .320, .100, .920, .120, 1.020),
        (-1.60, .720, .280, .100, .980, .140, 1.080),
        (0.55, .740, .280, .100, 1.000, .140, 1.100),
        (0.65, .740, .620, .100, 1.000, .140, 1.100),
        (1.80, .740, .620, .100, 1.000, .140, 1.100),
        (2.60, .420, .660, .060, 1.000, .090, 1.080)]
#         y      hb    hs     ht    htop     (cabin and boom stand on the hull top)
CABIN = [(-2.55, .480, 1.080, .380, 1.120),
         (-2.05, .500, 1.300, .360, 1.420),
         (-0.95, .500, 1.300, .360, 1.420)]
BOOM = [(-0.95, .300, 1.360, .200, 1.420),
        (-0.45, .300, 1.580, .200, 1.700),
        (3.45, .300, 1.580, .200, 1.700)]
HULL_Y, CABIN_Y, BOOM_Y = [r[0] for r in HULL], [r[0] for r in CABIN], [r[0] for r in BOOM]
Y_NOSE, Y_CAB, Y_BOOM0, Y_STEP0, Y_STEP1, Y_HULL, Y_END = -3.70, -2.55, -0.95, 0.55, 0.65, 2.60, 3.45
CAB_ST = sorted(set(CABIN_Y + HULL_Y))
BOOM_ST = sorted(set(BOOM_Y + HULL_Y))


def hull(y):
    return dict(zip(("w", "zb", "cb", "zs", "ct", "zt"), table(HULL, y)))


def hull_loop(y):
    h = hull(y)
    return loop10(0, h["w"], h["zb"], h["cb"], h["zs"], h["ct"], h["zt"])


def boom_z0(y):
    return hull(min(y, Y_HULL))["zt"]


def cabin_loop(y):
    return block_loop(*table(CABIN, y)[:1], boom_z0(y), *table(CABIN, y)[1:])


def boom_loop(y):
    return block_loop(*table(BOOM, y)[:1], boom_z0(y), *table(BOOM, y)[1:])


def deck_t(y, x):     # t on the hull top (segment 4-5) where the deck is at half width x
    h = hull(y)
    wt = h["w"] - h["ct"]
    return 4 + (wt - x) / wt


def xyz(y, x, z):
    return Vector((x, y, z))


def hull_centre(c):
    return Vector((0, c.y, (hull(c.y)["zb"] + hull(c.y)["zt"]) / 2))


def block_centre(c):
    return Vector((0, c.y, boom_z0(c.y) - 0.05))


def panel(name, loop_fn, t0, t1, y0, y1, stations, parent, m_fn, centre, cuts=(), holes=(), gap_s=(True, True)):
    p = Part(name)
    surface(p, loop_fn, t0, t1, y0, y1, stations, xyz, gap_s)
    orient_out(p, centre)
    paint(p, m_fn, cuts)
    return shell(p, parent, holes)


def slab(name, loop, y0, y1, m, parent, holes=()):
    """End cap: a flat plate of the section loop between y0 and y1 (with optional cut-outs)."""
    p = Part(name)
    p.loft([[Vector((x, y, z)) for x, z in loop] for y in (y0, y1)], lambda i, j: m, closed_u=True, cap0=m, cap1=m)
    ob = p.finish(parent, skin=True)
    if holes:
        boolean(ob, holes)
    shade(ob, 0.002)
    return ob


NOSE_BAND = [((0, -3.15, 0), (0.45, 0.89, 0)), ((0, -2.85, 0), (0.45, 0.89, 0))]   # orange diagonal on the nose top
LOW_BAND = [((0, 0, 0.62), (0, 0, 1))]                                             # black lower sides


def hull_paint(c, n):
    if n.z < -0.6:
        return "Graphite"
    if abs(n.x) > 0.25 and n.z > 0.25:
        return "Paint_Black"
    if n.z > 0.6:
        d = [(c - Vector(co)).dot(Vector(no)) for co, no in NOSE_BAND]
        return "Paint_Orange" if d[0] > 0 > d[1] else "Paint_White"
    return "Paint_Black" if c.z < 0.62 else "Paint_White"


CAB_CUTS = [((0, -2.00, 0), (0, 1, 0)), ((0, -1.20, 0), (0, 1, 0)), ((0, 0, 1.16), (0, 0, 1))]


def cabin_paint(c, n):
    if c.y < -2.05 and n.z > 0.2:
        return "Glass"                                          # windscreen
    if abs(n.x) > 0.9 and -2.00 < c.y < -1.20 and c.z > 1.16:
        return "Glass"                                          # side windows
    return "Paint_Black" if abs(n.x) > 0.25 and n.z > 0.25 else "Paint_White"


BOOM_STRIPES = [((0, y, 1.4), (0.25, 0.85, 0.46)) for y in (2.85, 2.97, 3.09, 3.21, 3.33)]


def boom_paint(c, n):
    k = sum((c - Vector(co)).dot(Vector(no)) > 0 for co, no in BOOM_STRIPES)
    if k:
        return "Paint_Orange" if k % 2 else "Paint_Black"     # hazard stripes at the tail of the boom
    return "Paint_Black" if abs(n.x) > 0.25 and n.z > 0.25 else "Paint_White"


def octa(L):
    return [L[i] for i in (1, 2, 3, 4, 6, 7, 8, 9)]


# ================================================================ 1. STRUCTURE
fr = Part("Frames")
for y in (-3.20, -2.40, -1.00, 0.00, 1.20, 2.20):
    oc = octa(hull_loop(y))
    o, i_ = inset(oc, SKIN + CLEAR), inset(oc, SKIN + CLEAR + 0.03)
    fr.loft([[Vector((p.x, y + dy, p.y)) for p in ring] for ring, dy in
             ((o, -0.012), (o, 0.012), (i_, 0.012), (i_, -0.012))], lambda i, j: "Metal", closed_u=True, closed_v=True)
for y in (0.0, 1.0, 2.0, 3.0):                                                         # boom arches
    fr.tube([Vector((p.x, y, p.y)) for p in inset(boom_loop(y), SKIN + CLEAR + 0.015)], 0.015, "Metal", square=True)
for y in (-2.05, -1.00):                                                               # cabin cage
    fr.tube([Vector((p.x, y, p.y)) for p in inset(cabin_loop(y), SKIN + CLEAR + 0.015)], 0.016, "Metal", 10)
for s in (-1, 1):
    fr.tube([(s * 0.33, -2.05, 1.383), (s * 0.33, -1.00, 1.383)], 0.014, "Metal", 10)
fr.finish(G["Structural_Core"], bevel=0.002)

lon = Part("Longerons")
for k in (1, 2, 5, 6):
    path = []
    for y in [-3.40] + [s for s in HULL_Y if -3.40 < s < 2.20] + [2.20]:
        p = inset(octa(hull_loop(y)), SKIN + CLEAR + 0.016)[k]
        path.append((p.x, y, p.y))
    lon.tube(path, 0.012, "Metal", square=True)
lon.finish(G["Structural_Core"], bevel=0.002)

crash = Part("Crash_Bumper")                                                           # front crash structure
crash.box((0, -3.76, 0.46), (0.90, 0.08, 0.10), "Metal")
for s in (-1, 1):
    crash.cyl((s * 0.30, -3.72, 0.46), (s * 0.30, -3.705, 0.46), 0.03, "Metal", 12)
    crash.cyl((s * 0.30, -3.69, 0.46), (s * 0.30, -3.30, 0.46), 0.03, "Metal", 12)
crash.finish(G["Nose"], bevel=0.002)

# ================================================================ 2. SYSTEMS
# ---- three plasma engines: a rectangular one at the end of the boom, a taller rectangular one in each side pod
GE = G["Propulsion"]
BOOM_ENG = ((0, 1.40), shape_loop(0.22, 0.22, 0.20, 0.06), 2.10, 3.10)
POD_X, POD_Z = 1.02, 1.30
POD_SEC = shape_loop(0.15, 0.15, 0.19, 0.05)
eng = Part("Engine_Boom")
c, sec, y0, y1 = BOOM_ENG
EXIT_B = space_engine(eng, c, y0, y1, sec)
eng.box((0, 2.20, 1.13), (0.30, 0.06, 0.16), "Metal")                                  # on the hull frame
eng.box((0, 2.90, 1.15), (0.30, 0.08, 0.12), "Metal")                                  # on the boom floor
eng.finish(GE)
for s, side in ((-1, "L"), (1, "R")):
    eng = Part("Engine_" + side)
    EXIT_P = space_engine(eng, (s * POD_X, POD_Z), -0.10, 1.50, POD_SEC)
    for y in (0.30, 1.20):
        eng.box((s * POD_X, y, 1.09), (0.20, 0.06, 0.05), "Metal")                     # on the pod floor
    eng.finish(G["Pod_" + side])

# ---- reactor in the hull, lines to the boom engine and, through the pylons, to the pod engines
rc = Part("Reactor_Core")
rc.lathe((0, -0.70, 0.72), (0, 0.20, 0.72),
         [(0, 0.0), (0.02, 0.10), (0.06, 0.16), (0.14, 0.17), (0.18, 0.155), (0.22, 0.17), (0.48, 0.17),
          (0.52, 0.155), (0.56, 0.17), (0.82, 0.17), (0.86, 0.155), (0.90, 0.17), (0.96, 0.16), (0.99, 0.10),
          (1, 0.0)], lambda k: "Emit_Hot" if k in (3, 4, 7, 8, 11, 12) else "Metal_Bright", 24)
for y in (-0.45, -0.10):
    rc.box((0, y, 0.43), (0.30, 0.05, 0.26), "Metal")                                   # saddles
rc.tube([(0, 0.22, 0.80), (0, 1.00, 0.95), (0, 1.80, 1.22), (0, 2.12, 1.32)], 0.016, "Metal", 10)
for s in (-1, 1):
    rc.tube([(s * 0.12, 0.20, 0.80), (s * 0.12, 0.22, 1.20), (s * 0.22, 0.25, 1.50), (s * 0.60, 0.25, 1.53),
             (s * 0.92, 0.25, 1.45)], 0.014, "Metal", 10)                         # through the arms to the pods
rc.finish(G["Reactor"])

# ---- cooling: big radiators behind louvred grilles in the hull sides and behind the grille in the nose
VENT = (-0.95, 0.05, 0.64, 0.94)
cool = Part("Radiators")
vent_cuts = []
for s in (-1, 1):
    y0, y1, z0, z1 = VENT
    w = hull((y0 + y1) / 2)["w"]
    cool.box((s * (w - 0.07), (y0 + y1) / 2, (z0 + z1) / 2), (0.05, y1 - y0 + 0.02, z1 - z0 + 0.02), "Black")
    for k in range(6):
        z = z0 + (k + 0.5) * (z1 - z0) / 6
        cool.box((s * (w - 0.025), (y0 + y1) / 2, z), (0.035, y1 - y0 - 0.01, 0.005), "Graphite",
                 Matrix.Rotation(math.radians(-35 * s), 3, 'Y'))
    vent_cuts.append(box_cutter((s * w, (y0 + y1) / 2, (z0 + z1) / 2), (0.12, y1 - y0, z1 - z0)))
cool.box((0, -3.60, 0.61), (0.66, 0.05, 0.25), "Black")                                # nose radiator
for k in range(5):
    cool.box((0, -3.685, 0.50 + k * 0.055), (0.66, 0.03, 0.006), "Graphite",
             Matrix.Rotation(math.radians(30), 3, 'X'))
cool.finish(G["Cooling"])
grille_cut = box_cutter((0, -3.70, 0.61), (0.68, 0.10, 0.26))

# ---- hover: emitters in cut-outs of the front belly, a gravity plate, emitters bolted under the cargo module
hover = Part("Hover_Emitters")
front_cuts = []
mods = [(-2.90, s * 0.38, 0.20, 0.40, True) for s in (-1, 1)] + [(-1.60, s * 0.44, 0.22, 0.44, True) for s in (-1, 1)]
mods += [(-0.55, 0.0, 0.40, 0.70, True)] + [(y, s * 0.40, 0.24, 0.46, False) for y in (1.00, 2.05) for s in (-1, 1)]
for y, x, sx, sy, cut in mods:
    zb = hull(y)["zb"] if cut else 0.26
    plate = sx > 0.3
    zbot = zb - (0.012 if plate else 0.035)
    h = zb + (0.03 if cut else 0.0) - zbot
    for dx, dy, ex, ey in ((0, sy / 2 - 0.012, sx, 0.024), (0, -sy / 2 + 0.012, sx, 0.024),
                           (sx / 2 - 0.012, 0, 0.024, sy), (-sx / 2 + 0.012, 0, 0.024, sy)):
        hover.box((x + dx, y + dy, zbot + h / 2), (ex, ey, h), "Graphite")
    hover.box((x, y, zbot + 0.006), (sx - 0.05, sy - 0.05, 0.004), "Emit_Hover")
    for k in range(1, 4 if plate else 3):
        hover.box((x, y - sy / 2 + k * sy / (4 if plate else 3), zbot + 0.003), (sx - 0.05, 0.008, 0.006), "Metal")
    if cut:
        hover.box((x, y, zb + 0.02), (sx - 0.02, sy - 0.02, 0.02), "Metal")
        front_cuts.append(box_cutter((x, y, zb), (sx + GAP, sy + GAP, 0.08)))
for s in (-1, 1):                                                                       # sensors
    zb = hull(-3.45)["zb"]
    hover.cyl((s * 0.30, -3.45, zb + 0.01), (s * 0.30, -3.45, zb - 0.012), 0.02, "Graphite", 12)
    hover.cyl((s * 0.30, -3.45, zb - 0.012), (s * 0.30, -3.45, zb - 0.014), 0.013, "Black", 12)
hover.finish(G["Hover"])

# ---- cockpit: floor, dash, controls, seat and pilot (head in the cabin, legs down into the nose)
ck = Part("Cockpit_Parts")
ck.box((0, -1.75, 0.80), (0.56, 1.30, 0.012), "Graphite")                               # floor
ck.box((0, -2.12, 1.10), (0.60, 0.14, 0.10), "Graphite")                                # dash
ck.box((0, -2.049, 1.12), (0.36, 0.004, 0.05), "Emit_Hover")                            # display
ck.cyl((0, -2.05, 1.07), (0, -1.90, 1.02), 0.016, "Metal", 10)                          # column
ck.box((0, -1.89, 1.02), (0.30, 0.028, 0.028), "Metal")                                 # handlebar
for s in (-1, 1):
    ck.cyl((s * 0.13, -1.89, 1.02), (s * 0.19, -1.89, 1.02), 0.019, "Graphite", 10)
ck.box((0, -1.42, 0.86), (0.40, 0.26, 0.05), "Graphite")                                # seat
back = Matrix.Rotation(math.radians(-15), 3, 'X')
ck.box((0, -1.23, 1.04), (0.40, 0.05, 0.36), "Graphite", back)                          # back rest
ck.finish(G["Cockpit_Cell"], bevel=0.003)
# the pilot (ship_kit.PILOTS["nomad"]: stocky bearded veteran, bubble visor and lamps), in the pose of this cockpit
pilot(G["Cockpit_Cell"], [(0, -1.40, 0.92), (0, -1.34, 1.04), (0, -1.28, 1.14)], (0, -1.26, 1.24), 0.10,
      [(0.15, -1.30, 1.12), (0.18, -1.55, 1.02), (0.15, -1.89, 1.02)],
      [(0.08, -1.42, 0.90), (0.09, -1.85, 0.98), (0.08, -2.30, 0.92)])

# ================================================================ 3. STABILIZERS (long and low, going down a little)
WING = [(0.58, 0.20, 2.00), (1.65, 1.45, 2.15)]   # x, leading edge y, trailing edge y
ANHEDRAL = math.radians(8)


def wing_at(x):
    le, te = table(WING, x)
    return le, te, 0.80 - (x - 0.62) * math.tan(ANHEDRAL), 0.08 - 0.04 * (x - 0.62) / 1.03


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


for s, side in ((1, "R"), (-1, "L")):
    gw = G["Wing_" + side]

    def w3d(x, y, z, s=s):
        return Vector((s * x, y, z))

    def w_centre(c):
        le, te, mid, th = wing_at(abs(c.x))
        return Vector((c.x, (le + te) / 2, mid))

    spar = Part("Stabilizer_Structure_" + side)
    p0, p1 = wing_at(0.58), wing_at(1.62)
    for f in (0.45, 0.85):
        a = (0.56, p0[0] + f * (p0[1] - p0[0]), p0[2])
        b = (1.62, p1[0] + f * (p1[1] - p1[0]), p1[2])
        spar.tube([(s * a[0], a[1], a[2]), (s * b[0], b[1], b[2])], 0.02 if f < 0.5 else 0.015, "Metal", square=True)
        spar.box((s * 0.58, a[1], p0[2]), (0.07, 0.12, 0.10), "Metal")                  # root clamps
    for x in (0.80, 1.20, 1.55):
        L = inset(wing_loop(x), 0.012)
        spar.loft([[Vector((s * (x + d), q.x, q.y)) for q in L] for d in (-0.006, 0.006)], lambda i, j: "Metal",
                  closed_u=True, cap0="Metal", cap1="Metal")
    spar.finish(gw, bevel=0.002)

    def skin(name, t0, t1, m_fn, cuts=()):
        p = Part(name + "_" + side)
        surface(p, wing_loop, t0, t1, 0.58, 1.65, [r[0] for r in WING], w3d, (False, False))
        orient_out(p, w_centre)
        paint(p, m_fn, cuts)
        return shell(p, gw, thick=0.007, bevel=0.0015)

    skin("Stabilizer_Top", 2, 3, lambda c, n: "Paint_Orange" if abs(c.x) > 1.35 else "Paint_White",
         [((1.35, 0, 0), (1, 0, 0)), ((-1.35, 0, 0), (1, 0, 0))])
    skin("Stabilizer_Bottom", 6, 7, lambda c, n: "Graphite")
    skin("Stabilizer_TE", 3, 6, lambda c, n: "Paint_Black")
    skin("Stabilizer_LE", 7, 10, lambda c, n: "Paint_Black")
    tip = Part("Stabilizer_Tip_" + side)
    L = wing_loop(1.65 - GAP / 2)
    tip.loft([[Vector((s * (1.65 - GAP / 2 - d), q[0], q[1])) for q in L] for d in (0, 0.01)],
             lambda i, j: "Paint_Black", closed_u=True, cap0="Paint_Black", cap1="Paint_Black")
    tip.finish(gw, bevel=0.002, skin=True)

slots = []
for s in (-1, 1):
    p = Part("cut")
    p.loft([[Vector((s * x, a, b)) for a, b in wing_loop(x, GAP / 2)] for x in (0.54, 0.90)], lambda i, j: "Black",
           closed_u=True, cap0="Black", cap1="Black")
    slots.append(cutter(p))


def a_wing(name, s, x0, x1, root, tip, z0, z1, th0, th1, parent, m="Paint_Orange"):
    """Small wing shaped like an uneven A seen from above: the leading edge straight out from the body, the trailing
    edge swept back to it. Spar inside; returns the cutter for its slot in the body panel at x0."""
    def sec(x, grow=0.0):
        f = (x - x0) / (x1 - x0)
        le = root[0] + (tip[0] - root[0]) * f - grow
        te = root[1] + (tip[1] - root[1]) * f + grow
        mid, th = z0 + (z1 - z0) * f, th0 + (th1 - th0) * f + 2 * grow
        e = min(0.06, 0.15 * (te - le))
        return [(le, mid - th / 6), (le, mid + th / 6), (le + e, mid + th / 2), (te - 0.02, mid + th / 2),
                (te, mid + th / 6), (te, mid - th / 6), (te - 0.02, mid - th / 2), (le + e, mid - th / 2)]
    p = Part(name)
    p.loft([[Vector((s * x, a, b)) for a, b in sec(x)] for x in (x0, x1)], lambda i, j: m, closed_u=True, cap0=m,
           cap1=m)
    p.tube([(s * x0, root[0] + 0.35 * (root[1] - root[0]), z0),
            (s * (x1 - 0.03), tip[0] + 0.35 * (tip[1] - tip[0]), z1)], min(th0, th1) * 0.25, "Metal", 8)
    p.finish(parent, bevel=0.002, skin=True)
    c = Part("cut")
    c.loft([[Vector((s * x, a, b)) for a, b in sec(x, GAP / 2)] for x in (x0 - 0.02, x0 + 0.12)],
           lambda i, j: "Black", closed_u=True, cap0="Black", cap1="Black")
    return cutter(c)


# small canards on the nose sides shaped like an A with both legs swept to the tip, and the orange arms the pods
# hang from (off the boom sides), shaped like an uneven A: straight leading edge, swept trailing edge
canard_cuts = [a_wing("Canard_" + side, s, 0.63, 1.10, (-3.10, -2.50), (-2.88, -2.72), 0.66, 0.62, 0.06, 0.03,
                      G["Nose"]) for s, side in ((-1, "L"), (1, "R"))]
arm_cuts = [a_wing("Pod_Arm_" + side, s, 0.29, 1.16, (-0.30, 1.60), (-0.30, 0.60), 1.52, 1.60, 0.09, 0.06,
                   G["Pod_" + side]) for s, side in ((-1, "L"), (1, "R"))]

# ================================================================ 4. BODYWORK
# ---- hull: nose face with the grille, top, sides (grilles, stabilizer slots, black lower band), chines, belly, decks
slab("Nose_Front", hull_loop(Y_NOSE), Y_NOSE - SKIN, Y_NOSE, "Paint_Black", G["Nose"], [grille_cut])
lamps = Part("Nose_Lights")
for x in (-0.30, -0.12, 0.12, 0.30):
    lamps.cyl((x, Y_NOSE - SKIN, 0.84), (x, Y_NOSE - SKIN - 0.03, 0.84), 0.045, "Graphite", 16)
    lamps.cyl((x, Y_NOSE - SKIN - 0.03, 0.84), (x, Y_NOSE - SKIN - 0.033, 0.84), 0.035, "Emit_Light", 16)
lamps.finish(G["Nose"])
panel("Nose_Top", hull_loop, 3, 7, Y_NOSE, Y_CAB, HULL_Y, G["Nose"], hull_paint, hull_centre, NOSE_BAND,
      gap_s=(False, True))
for side, s in (("R", 1), ("L", -1)):
    def span(a, b):
        return (a, b) if s > 0 else ((lambda y: 10 - b(y)) if callable(b) else 10 - b,
                                     (lambda y: 10 - a(y)) if callable(a) else 10 - a)
    panel("Side_Front_" + side, hull_loop, *span(2, 3), Y_NOSE, -1.00, HULL_Y, B, hull_paint, hull_centre, LOW_BAND,
          canard_cuts, gap_s=(False, True))
    panel("Side_Mid_" + side, hull_loop, *span(2, 3), -1.00, 1.00, HULL_Y, B, hull_paint, hull_centre, LOW_BAND,
          slots + vent_cuts)
    panel("Side_Rear_" + side, hull_loop, *span(2, 3), 1.00, Y_HULL, HULL_Y, B, hull_paint, hull_centre, LOW_BAND,
          slots)
    for y0, y1, g in ((Y_NOSE, Y_STEP0, (False, True)), (Y_STEP1, Y_HULL, (True, True))):
        panel("Chine_" + side, hull_loop, *span(1, 2), y0, y1, HULL_Y, B, lambda c, n: "Metal", hull_centre,
              gap_s=g)
    panel("Deck_Cabin_" + side, hull_loop, *span(3, lambda y: deck_t(y, table(CABIN, y)[0] + 0.005)), Y_CAB,
          Y_BOOM0, HULL_Y, B, hull_paint, hull_centre)
    panel("Deck_Boom_" + side, hull_loop, *span(3, lambda y: deck_t(y, 0.305)), Y_BOOM0, Y_HULL, HULL_Y, B,
          hull_paint, hull_centre)
panel("Belly_Front", hull_loop, 9, 11, Y_NOSE, Y_STEP0, HULL_Y, B, lambda c, n: "Graphite", hull_centre,
      holes=front_cuts, gap_s=(False, True))
panel("Belly_Rear", hull_loop, 9, 11, Y_STEP1, Y_HULL, HULL_Y, B, lambda c, n: "Graphite", hull_centre)
slab("Hull_Rear", hull_loop(Y_HULL), Y_HULL, Y_HULL + SKIN, "Ceramic", B)
drop(slots + vent_cuts + front_cuts + canard_cuts + [grille_cut])

# ---- cabin with flush windows; boom with the hazard-striped tail, its engine inside, shark fin on top
C = G["Cockpit_Cell"]
panel("Cabin_Top", cabin_loop, 1, 5, Y_CAB, Y_BOOM0, CAB_ST, C, cabin_paint, block_centre, CAB_CUTS)
panel("Cabin_Side_R", cabin_loop, 0, 1, Y_CAB, Y_BOOM0, CAB_ST, C, cabin_paint, block_centre, CAB_CUTS)
panel("Cabin_Side_L", cabin_loop, 5, 6, Y_CAB, Y_BOOM0, CAB_ST, C, cabin_paint, block_centre, CAB_CUTS)
slab("Cabin_Front", cabin_loop(Y_CAB), Y_CAB - SKIN, Y_CAB, "Paint_Black", C)
c = Part("cut")
c.loft([[Vector((x, y, z)) for x, z in inset(boom_loop(Y_BOOM0), -GAP / 2)] for y in (Y_BOOM0 - 0.05, Y_BOOM0 + 0.05)],
       lambda i, j: "Black", closed_u=True, cap0="Black", cap1="Black")
bc = cutter(c)
slab("Cabin_Rear", cabin_loop(Y_BOOM0), Y_BOOM0, Y_BOOM0 + SKIN, "Paint_White", C, [bc])
drop([bc])

M = G["Boom"]
slab("Boom_Front", boom_loop(Y_BOOM0), Y_BOOM0 - SKIN, Y_BOOM0, "Paint_Black", M)
panel("Boom_Top", boom_loop, 1, 5, Y_BOOM0, Y_END, BOOM_ST, M, boom_paint, block_centre, BOOM_STRIPES,
      gap_s=(True, False))
panel("Boom_Side_R", boom_loop, 0, 1, Y_BOOM0, Y_END, BOOM_ST, M, boom_paint, block_centre, BOOM_STRIPES, arm_cuts,
      gap_s=(True, False))
panel("Boom_Side_L", boom_loop, 5, 6, Y_BOOM0, Y_END, BOOM_ST, M, boom_paint, block_centre, BOOM_STRIPES, arm_cuts,
      gap_s=(True, False))
drop(arm_cuts)
bb = Part("Boom_Belly")
bb.box((0, (Y_HULL + Y_END) / 2 + GAP / 2, boom_z0(Y_END) + SKIN / 2), (0.59, Y_END - Y_HULL - GAP, SKIN), "Graphite")
bb.box((0, Y_END - 0.004, boom_z0(Y_END) + SKIN + 0.01), (0.16, 0.008, 0.012), "Emit_Red")   # tail light
bb.finish(M, bevel=0.002, skin=True)
hole = Part("cut")
hole.sweep(BOOM_ENG[0], 3.05, 3.15, [(0, 1.04), (1, 1.04)], BOOM_ENG[1], lambda k: "Black", cap0="Black",
           cap1="Black")
hc = cutter(hole)
bl = [(x, z) for x, z in inset(boom_loop(3.10), SKIN + 0.002)]
ob = slab("Boom_Bulkhead", bl, 3.094, 3.106, "Ceramic", M, [hc])
SKINS.remove(ob)
drop([hc])
fin = Part("Shark_Fin")
shark_fin(fin, lambda y: 1.70, 0.0, (2.25, 3.35), (3.00, 3.48), 0.20, 0.03, "Paint_Orange", "Paint_Black")
fin.finish(M, bevel=0.0015, smooth_angle=60, skin=True)

# ---- side pods: rectangular shrouds round the pod engines, grille at the front, on two pylons each
POD_OUT = shape_loop(0.22, 0.22, 0.26, 0.07)
POD_IN = shape_loop(0.19, 0.19, 0.23, 0.05)
for s, side in ((-1, "L"), (1, "R")):
    gp = G["Pod_" + side]
    x0 = s * POD_X

    def pod_paint(c, n, x0=x0):
        if c.y > 1.855 and abs(n.y) > 0.9:
            return "Metal_Bright"
        if c.y < -0.445 and abs(n.y) > 0.9:
            return "Paint_Black"
        if (c - Vector((x0, c.y, POD_Z))).dot(n) < 0:
            return "Graphite"
        return "Paint_Orange" if c.y < -0.15 else "Paint_White"

    sh = Part("Pod_Shroud_" + side)
    sh.loft([[Vector((x0 + x, y, POD_Z + z)) for x, z in sec] for y, sec in
             ((-0.45, POD_OUT), (1.86, POD_OUT), (1.86, POD_IN), (-0.45, POD_IN))], lambda i, j: "Paint_White",
            closed_u=True, closed_v=True)
    bmesh.ops.recalc_face_normals(sh.bm, faces=sh.bm.faces[:])
    paint(sh, pod_paint, [((0, -0.15, 0), (0, 1, 0))])
    sh.finish(gp, bevel=0.002, recalc=False, skin=True)
    gr = Part("Pod_Grille_" + side)
    gr.loft([[Vector((x0 + x * 0.98, y, POD_Z + z * 0.98)) for x, z in POD_IN] for y in (-0.31, -0.29)],
            lambda i, j: "Black", closed_u=True, cap0="Black", cap1="Black")
    for k in range(7):
        gr.box((x0, -0.43, POD_Z - 0.20 + k * 0.066), (0.38, 0.03, 0.006), "Graphite",
               Matrix.Rotation(math.radians(30), 3, 'X'))
    gr.finish(gp)
    cl = Part("Pod_Clamp_" + side)                                                     # the pod hangs from the arm
    cl.box((x0, 0.10, POD_Z + 0.265), (0.26, 0.70, 0.012), "Metal")
    for y in (-0.15, 0.35):
        for dx in (-0.09, 0.09):
            cl.cyl((x0 + dx, y, POD_Z + 0.271), (x0 + dx, y, POD_Z + 0.279), 0.012, "Metal_Bright", 8)
    cl.finish(gp)

# ---- cargo and tank module under the rear: grey box with straps, latches, tanks inside, mounted on rails
CG = G["Cargo"]
z0, z1, hw, ch = 0.26, 0.615, 0.70, 0.05
sec = [(0, z0), (hw - ch, z0), (hw, z0 + ch), (hw, z1 - ch), (hw - ch, z1), (-(hw - ch), z1), (-hw, z1 - ch),
       (-hw, z0 + ch), (-(hw - ch), z0)]
ins = inset(sec, ch)
box = Part("Cargo_Module")
box.loft([[Vector((q[0], y, q[1])) for q in L] for y, L in
          ((0.55, ins), (0.60, sec), (2.45, sec), (2.50, ins))], lambda i, j: "Paint_Grey", closed_u=True,
         cap0="Paint_Grey", cap1="Paint_Grey")
bmesh.ops.recalc_face_normals(box.bm, faces=box.bm.faces[:])
paint(box, lambda c, n: "Graphite" if n.z < -0.6 else "Paint_Grey")
box.finish(CG, bevel=0.003, recalc=False, skin=True)
det = Part("Cargo_Fittings")
for y in (0.95, 2.15):                                                                  # straps
    for s in (-1, 1):
        det.box((s * (hw + 0.004), y, (z0 + z1) / 2), (0.008, 0.08, z1 - z0 - 0.02), "Paint_Black")
    det.box((0, y, z0 - 0.004), (2 * hw - 0.1, 0.08, 0.008), "Paint_Black")
for y in (0.75, 1.35, 1.75, 2.35):                                                      # latches
    for s in (-1, 1):
        det.box((s * (hw + 0.006), y, z1 - 0.07), (0.012, 0.06, 0.03), "Metal")
for s in (-1, 1):
    det.cyl((s * 0.33, 0.70, 0.44), (s * 0.33, 2.35, 0.44), 0.13, "Metal", 16)           # tanks
    det.box((s * 0.40, 1.52, z1 + 0.003), (0.06, 1.80, 0.006), "Metal")                 # rails
det.finish(CG)

# ================================================================ 5. DECALS
dec = Part("Decals")
for s in (-1, 1):
    rd = 1 if s > 0 else -1
    u = Vector((0, 1, 0)) * rd
    dec.add_mesh(text_mesh("NOMAD", 0.17), frame_on((s * hw, 1.55, (z0 + z1) / 2), u, (0, 0, 1)), "Paint_Black")
    xo = s * (POD_X + 0.22)
    dec.flat(disc2d(0.10), frame_on((xo, 0.55, POD_Z), u, (0, 0, 1)), "Paint_White")
    dec.add_mesh(text_mesh("21", 0.12), frame_on((xo, 0.55, POD_Z), u, (0, 0, 1), 0.004), "Black")
    xc, yc = 1.05, 1.40                                                                  # league emblem
    d = (wing_top(xc + 0.05) - wing_top(xc - 0.05)) / 0.1
    M2 = frame_on((s * xc, yc, wing_top(xc) + 0.0005), (s, 0, d), (0, s, 0))
    o, i_ = ring2d(0.12, 0.14)
    dec.flat(o, M2, "Paint_Black", holes=[i_])
    dec.poly([M2 @ Vector(((0.10 if k % 2 == 0 else 0.025) * math.cos(math.pi / 2 + k * math.pi / 4),
                           (0.10 if k % 2 == 0 else 0.025) * math.sin(math.pi / 2 + k * math.pi / 4), 0))
              for k in range(8)], "Paint_Black")
dec.finish(G["Decals"], recalc=False, smooth_angle=10)

# ================================================================ sockets
for name, loc in (("Socket_Reactor", (0, -0.25, 0.72)), ("Socket_Propulsion_Boom", (0, EXIT_B, 1.40)),
                  ("Socket_Propulsion_L", (-POD_X, EXIT_P, POD_Z)), ("Socket_Propulsion_R", (POD_X, EXIT_P, POD_Z)),
                  ("Socket_Wing_L", (-0.58, 1.10, 0.80)), ("Socket_Wing_R", (0.58, 1.10, 0.80)),
                  ("Socket_Cargo", (0, 1.52, 0.44)), ("Socket_Tail", (0, Y_END, 1.08)),
                  ("Socket_Armor_L", (-0.74, -1.80, 0.65)), ("Socket_Armor_R", (0.74, -1.80, 0.65)),
                  ("Socket_Cooling", (0, -0.45, 0.80)), ("Socket_Utility", (0, -3.78, 0.46))):
    group(name, G["Sockets"], loc)

finish_ship(G["Decals"], cockpit=((-1.7, -3.2, 2.1), (0, -1.6, 1.10)), scale=1.15)

# ================================================================ modules (Docs/MODULOS.md): the split for the game and the variants
from ship_modules import build_modules  # noqa: E402
build_modules(globals(), wings=("longspan", "brace", "glide"), palette=("Paint_White", "Paint_Orange", "Paint_Black"),
              tail="below", scale=1.15, nozzle_r=0.16)
