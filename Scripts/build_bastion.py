# BASTION hover racer (the heaviest: armoured, five lives, slow to push off line), built from the inside out like the
# others: structure (frames and longerons, crash bumper, cockpit cell, engine mounts, wing spars and clamps), systems
# (cockpit and pilot, reactor and its lines, one colossal flat plasma engine, coolant intakes and radiators, hover
# emitters, four stowed impact airbags), then the 12 mm bodywork panels with 5 mm gaps.
# Look (the player's reference, then his call, 2026-10-25: flatter, the ship set inside a wing, wings like the
# VORTEX's): a wide flat slate wing-body with thin edges, widest at the back, and the yellow armoured carapace (cockpit
# and engine) sitting in the middle of it, the windscreen flush in the carapace front; big orange-lined coolant intakes
# in the carapace flanks; the impact airbags stowed under round hatches in the wing surface; swept wings out of the
# wing-body edges with their tips folded up; the carapace tapering round the colossal engine into a heavy collar, a
# long shark fin on top; yellow, slate and orange (Docs/BASTION_CATEGORIA.md, Docs/NAVES_REGRAS.md).
# Front is -Y, up is +Z, metres (the layout of the old SourceArt/TestShips/bastion.fbx; the game centres the bounds).
# Usage: python3 Scripts/build_bastion.py <out_dir> [--no-render]
#    or: blender -b -P Scripts/build_bastion.py -- <out_dir> [--no-render]
# Writes <out_dir>/bastion.blend, bastion.fbx and the preview renders. Shared parts: Scripts/ship_kit.py.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ship_kit import *  # noqa: E402,F401,F403  (bpy, bmesh, math, Matrix, Vector and the helpers)

start("BASTION")
material("Paint_Yellow", "#E9A720", rough=0.34, coat=0.5)
material("Paint_Slate", "#3B4650", rough=0.42, coat=0.3)
material("Paint_Orange", "#E8702A", rough=0.32, coat=0.5)
material("Paint_Red", "#D7262B", rough=0.4)
material("Paint_White", "#EEF0F2", rough=0.32, coat=0.4)
material("Fabric_Tan", "#C9A06A", rough=0.85)
material("Graphite", "#2B2E33", rough=0.6)
material("Black", "#101113", rough=0.35)
material("Metal", "#7E848B", metal=1.0, rough=0.45)
material("Metal_Bright", "#C2C7CC", metal=1.0, rough=0.22)
material("Ceramic", "#BDB6AA", rough=0.8)
material("Glass", "#9FC6DA", rough=0.03, alpha=0.25)
material("Emit_Hover", "#5FE3FF", emit=3.0, rough=0.3)
material("Emit_Hot", "#FF7A2E", emit=6.0, rough=0.3)
material("Emit_Red", "#FF2A2A", emit=4.0, rough=0.3)
material("Emit_Amber", "#FFB43A", emit=4.0, rough=0.3)
material("Emit_Plasma", "#8FDFFF", emit=10.0, rough=0.3)
material("Emit_Light", "#FFF2D0", emit=8.0, rough=0.2)

ROOT = group("ShipRoot")
G = {n: group(n, ROOT) for n in ("Structural_Core", "Nose", "Cockpit_Cell", "Body", "Reactor", "Propulsion",
                                 "Wing_L", "Wing_R", "Hover", "Cooling", "Airbags", "Decals", "Sockets")}
B = G["Body"]

# ---------------------------------------------------------------- lines
# The slate wing-body (belly, bottom chamfer, the thin edge up to zs, the wing surface rising gently to zh at sh in
# from the edge) and the yellow carapace in the middle of it (its flanks up to the top at ct in, the flat top). Widest
# at the back; the tail cone runs from the last station into the collar round the engine.
#        y      w      zb    cb    zs    sh    zh     ct    zt
BODY = [(-3.40, .420, .400, .040, .480, .060, .580, .260, .660),
        (-3.00, .700, .330, .050, .450, .220, .600, .440, .800),
        (-2.20, .960, .280, .050, .420, .380, .620, .600, .940),
        (-1.20, 1.160, .260, .050, .410, .500, .630, .700, 1.050),
        (0.20, 1.300, .260, .050, .410, .600, .640, .780, 1.090),
        (1.40, 1.360, .270, .050, .410, .640, .640, .800, 1.090),
        (2.20, 1.240, .290, .050, .420, .580, .640, .740, 1.050),
        (2.80, 1.000, .330, .045, .430, .420, .630, .580, .970)]
BODY_Y = [r[0] for r in BODY]
Y_NOSE, Y_A, Y_B, Y_CONE, Y_CONE1, Y_END = -3.40, -1.20, 1.40, 2.80, 3.12, 3.36
CAN = (-2.25, -1.15)              # the windscreen: the carapace flanks (above 0.70 m) and top over the cockpit
ENG_Z = 0.66                      # the colossal engine: a wide flat rounded box filling the rear of the carapace
SEC = shape_loop(0.58, 0.48, 0.21, 0.09)
SH_HH = 0.28
SH_OUT = shape_loop(0.72, 0.58, SH_HH, 0.11)        # the collar round its nozzle
SH_IN = shape_loop(0.67, 0.53, SH_HH - 0.04, 0.08)
INTAKE = (-0.60, 0.40, 0.72, 0.94)  # coolant intake in each carapace flank: y0, y1, z0, z1
BAGS = [(-1.85, 0.50, 0.15), (1.75, 0.50, 0.17)]   # airbag hatches in the wing surface: y, fraction in, radius


def body(y):
    return dict(zip(("w", "zb", "cb", "zs", "sh", "zh", "ct", "zt"), table(BODY, y)))


def body_loop(y):
    """12 points counter-clockwise from the bottom centre: t 1..2 the bottom chamfer, 2..3 the edge, 3..4 the wing
    surface, 4..5 the carapace flank, 5..7 the carapace top, 11..13 the belly (left side mirrored)."""
    b = body(y)
    r = [(0, b["zb"]), (b["w"] - b["cb"], b["zb"]), (b["w"], b["zb"] + b["cb"]), (b["w"], b["zs"]),
         (b["w"] - b["sh"], b["zh"]), (b["w"] - b["ct"], b["zt"]), (0, b["zt"])]
    return r + [(-x, z) for x, z in reversed(r[1:-1])]


def frame_loop(y):        # the frames' outline: the carapace and the thick inner part of the wing (edges stay clear)
    b = body(y)
    xh, xt = b["w"] - b["sh"], b["w"] - b["ct"]
    fx = max(b["w"] - 0.30, xh + 0.06)
    zf = b["zs"] + (b["zh"] - b["zs"]) * (b["w"] - fx) / b["sh"]
    r = [(fx, b["zb"]), (fx, zf), (xh, b["zh"]), (xt, b["zt"])]
    return r + [(-x, z) for x, z in reversed(r)]


def xyz(y, x, z):
    return Vector((x, y, z))


def body_centre(c):
    return Vector((0, c.y, (body(c.y)["zb"] + body(c.y)["zt"]) / 2))


def facet_point(y, s, i, j, f):       # point at fraction f from corner i to corner j of the section, on side s
    L = body_loop(y)
    (x0, z0), (x1, z1) = L[i], L[j]
    return Vector((s * (x0 + (x1 - x0) * f), y, z0 + (z1 - z0) * f))


def facet_normal(y, s, i, j):          # outward normal of the facet from corner i to corner j (right half), on side s
    L = body_loop(y)
    n = Vector((L[j][1] - L[i][1], L[i][0] - L[j][0])).normalized()
    return Vector((s * n.x, 0, n.y))


def facet_up(y, s, i, j):              # along the facet from corner i to corner j, on side s
    return (facet_point(y, s, i, j, 1.0) - facet_point(y, s, i, j, 0.0)).normalized()


def panel(name, t0, t1, y0, y1, parent, m_fn, cuts=(), holes=(), gap_s=(True, True)):
    p = Part(name)
    surface(p, body_loop, t0, t1, y0, y1, BODY_Y, xyz, gap_s)
    orient_out(p, body_centre)
    paint(p, m_fn, cuts)
    return shell(p, parent, holes)


GLASS_CUTS = [((0, CAN[0], 0), (0, 1, 0)), ((0, CAN[1], 0), (0, 1, 0)), ((0, 0, 0.70), (0, 0, 1))]


def carapace_paint(c, n):
    if CAN[0] < c.y < CAN[1] and c.z > 0.70:
        return "Glass"
    return "Paint_Yellow"


def slate(c, n):
    return "Graphite" if n.z < -0.6 else "Paint_Slate"


# ================================================================ 1. STRUCTURE
fr = Part("Frames")
for y in (-3.00, -2.20, -1.20, -0.30, 0.60, 1.40, 2.20, 2.75):
    o, i_ = inset(frame_loop(y), SKIN + CLEAR), inset(frame_loop(y), SKIN + CLEAR + 0.032)
    fr.loft([[Vector((p.x, y + dy, p.y)) for p in ring] for ring, dy in
             ((o, -0.013), (o, 0.013), (i_, 0.013), (i_, -0.013))], lambda i, j: "Metal", closed_u=True, closed_v=True)
fr.finish(G["Structural_Core"], bevel=0.002)

lon = Part("Longerons")
for k in range(8):
    path = []
    for y in [-3.00] + [s for s in BODY_Y if -3.00 < s < 2.75] + [2.75]:
        p = inset(frame_loop(y), SKIN + CLEAR + 0.016)[k]
        path.append((p.x, y, p.y))
    lon.tube(path, 0.013, "Metal", square=True)
lon.finish(G["Structural_Core"], bevel=0.002)

crash = Part("Crash_Bumper")                                                           # the armoured front bumper
crash.box((0, -3.47, 0.44), (0.80, 0.09, 0.08), "Graphite")
crash.box((0, -3.517, 0.44), (0.70, 0.012, 0.035), "Paint_Orange")
for s in (-1, 1):
    crash.box((s * 0.41, -3.45, 0.44), (0.07, 0.12, 0.10), "Graphite")
    crash.cyl((s * 0.25, -3.42, 0.44), (s * 0.25, -3.10, 0.44), 0.03, "Metal", 12)     # crash cans
crash.finish(G["Nose"], bevel=0.003)

mnt = Part("Engine_Mounts")                       # struts from the frames to the engine casing
for y in (1.40, 2.20):
    fl = inset(frame_loop(y), SKIN + CLEAR + 0.03)
    for k, q in ((1, 0.125), (2, 0.375), (5, 0.625), (6, 0.875)):
        p = loop_at(SEC, q) * 1.03 + Vector((0, ENG_Z))
        mnt.tube([(p.x, y, p.y), (fl[k].x, y, fl[k].y)], 0.02, "Metal", square=True)
mnt.finish(G["Structural_Core"], bevel=0.002)

# ================================================================ 2. SYSTEMS
# ---- one colossal flat plasma engine: the casing runs most of the carapace, the coils and the bell in the tail
GE = G["Propulsion"]
eng = Part("Engine")
EXIT = space_engine(eng, (0, ENG_Z), 0.50, 2.75, SEC, coil_len=0.28, bell_len=0.30)
for y in (0.80, 1.65, 2.45):                                                            # casing bands
    eng.sweep((0, ENG_Z), y, y + 0.06, [(0, 1.04), (1, 1.04)], SEC, lambda k: "Graphite", closed=False)
eng.finish(GE)

# ---- reactor behind the cockpit and its lines into the engine and to the coils
rc = Part("Reactor_Core")
rc.lathe((0, -0.80, 0.62), (0, 0.38, 0.62),
         [(0, 0.0), (0.03, 0.10), (0.07, 0.155), (0.16, 0.165), (0.21, 0.15), (0.26, 0.165), (0.48, 0.165),
          (0.53, 0.15), (0.58, 0.165), (0.80, 0.165), (0.85, 0.15), (0.90, 0.165), (0.96, 0.155), (0.99, 0.10),
          (1, 0.0)], lambda k: "Emit_Hot" if k in (3, 4, 7, 8, 11, 12) else "Metal_Bright", 24)
for y in (-0.58, 0.16):
    rc.box((0, y, 0.39), (0.30, 0.05, 0.10), "Metal")                                   # saddles
rc.tube([(0, 0.38, 0.62), (0, 0.44, 0.64), (0, 0.44, ENG_Z)], 0.018, "Metal", 10)
for s in (-1, 1):                                                                       # lines to the coils
    rc.tube([(s * 0.14, 0.30, 0.72), (s * 0.30, 0.65, 0.92), (s * 0.30, 2.55, 0.92), (s * 0.22, 2.80, 0.86)],
            0.013, "Metal", 8)
rc.finish(G["Reactor"])

# ---- coolant intakes in the carapace flanks (orange-lined), radiators inside, ducts to the engine casing
cool = Part("Radiators")
intake_cuts = []
y0, y1, z0, z1 = INTAKE
ym, zm = (y0 + y1) / 2, (z0 + z1) / 2
for s in (-1, 1):
    a, b = facet_point(ym, s, 4, 5, 0.0), facet_point(ym, s, 4, 5, 1.0)
    up, n = facet_up(ym, s, 4, 5), facet_normal(ym, s, 4, 5)
    c = a.lerp(b, (zm - a.z) / (b.z - a.z))                     # the middle of the mouth on the flank
    h = (z1 - z0) / up.z
    R = Matrix((n, Vector((0, 1, 0)), up)).transposed()         # boxes laid on the flank
    cool.box(c - n * 0.11, (0.03, y1 - y0 + 0.02, h + 0.02), "Black", R)                  # radiator face
    for k in range(10):                                                                   # louvres
        yy = y0 + (k + 0.5) * (y1 - y0) / 10
        cool.box(Vector((c.x, yy, c.z)) - n * 0.06, (0.06, 0.012, h - 0.01), "Graphite",
                 R @ Matrix.Rotation(math.radians(30 * s), 3, 'Z'))
    for d in (-1, 1):                                                                     # orange lining inside
        cool.box(c + up * d * (h / 2 - 0.004) - n * 0.05, (0.10, y1 - y0, 0.008), "Paint_Orange", R)
    for yy in (y0 + 0.004, y1 - 0.004):
        cool.box(Vector((c.x, yy, c.z)) - n * 0.05, (0.10, 0.008, h), "Paint_Orange", R)
    for d in (-1, 1):                                                                     # lip round the mouth
        cool.box(c + up * d * (h / 2 + 0.018) + n * 0.01, (0.03, y1 - y0 + 0.072, 0.036), "Paint_Orange", R)
    for yy in (y0 - 0.018, y1 + 0.018):
        cool.box(Vector((c.x, yy, c.z)) + n * 0.01, (0.03, 0.036, h), "Paint_Orange", R)
    cool.tube([c - n * 0.13 + Vector((0, (y1 - y0) / 2 - 0.05, 0)), Vector((s * 0.62, 1.00, 0.74)),
               Vector((s * 0.58, 1.55, ENG_Z))], 0.05, "Metal", 10)                       # duct to the casing
    intake_cuts.append(box_cutter(Vector((c.x, ym, c.z)), (0.30, y1 - y0, h * 0.95)))
cool.finish(G["Cooling"])

# ---- impact airbags stowed under round hatches in the wing surface (three tan lobes each, strapped)
bags = Part("Airbags")
bag_cuts = []
for s in (-1, 1):
    for y, f, r in BAGS:
        p, n = facet_point(y, s, 3, 4, f), facet_normal(y, s, 3, 4)
        bags.lathe(p + n * 0.012, p - n * 0.05, [(0, r + 0.03), (0.3, r + 0.03), (0.3, r), (1, r)],
                   lambda k: "Graphite", 32)                                            # housing ring
        bags.cyl(p - n * 0.05, p - n * 0.06, r, "Metal", 32)                            # back plate
        R = Matrix((facet_up(y, s, 3, 4), Vector((0, 1, 0)), n)).transposed()           # laid on the wing surface
        for k, dy in enumerate((-0.58, 0.0, 0.58)):                                     # the folded bag, bulging a
            ry = r * (0.42 if k != 1 else 0.48)                                         # little out of its hatch
            vs = bmesh.ops.create_uvsphere(bags.bm, u_segments=20, v_segments=10, radius=1.0)["verts"]
            M = Matrix.Translation(p - n * 0.012 + Vector((0, dy * r, 0))) @ R.to_4x4() @ \
                Matrix.Diagonal((r * 0.92, ry, 0.045, 1))
            bmesh.ops.transform(bags.bm, matrix=M, verts=vs)
            for face in {fc for v in vs for fc in v.link_faces}:
                face.material_index = bags.mi("Fabric_Tan")
        for dx in (-0.55 * r, 0.55 * r):                                                # straps
            bags.box(p + n * 0.034 + R @ Vector((dx, 0, 0)), (0.02, 1.7 * r, 0.010), "Graphite", R)
        c = Part("cut")
        c.cyl(p + n * 0.08, p - n * 0.08, r + 0.03 + GAP / 2, "Black", 32)
        bag_cuts.append(cutter(c))
bags.finish(G["Airbags"], bevel=0.0015)

# ---- hover: emitter modules in cut-outs of the belly, a gravity plate in the middle, sensors
hover = Part("Hover_Emitters")
emit_cuts = []
mods = [(y, s * x, sx, sy) for y, x, sx, sy in ((-2.55, 0.36, 0.22, 0.36), (-1.40, 0.62, 0.26, 0.46),
                                                (0.20, 0.88, 0.24, 0.44), (1.40, 0.62, 0.26, 0.46),
                                                (2.40, 0.46, 0.22, 0.36)) for s in (-1, 1)]
mods += [(0.20, 0.0, 0.60, 0.90)]
for y, x, sx, sy in mods:
    zb = body(y)["zb"]
    plate = sx > 0.3
    zbot = zb - (0.012 if plate else 0.035)
    h = zb + 0.03 - zbot
    for dx, dy, ex, ey in ((0, sy / 2 - 0.012, sx, 0.024), (0, -sy / 2 + 0.012, sx, 0.024),
                           (sx / 2 - 0.012, 0, 0.024, sy), (-sx / 2 + 0.012, 0, 0.024, sy)):
        hover.box((x + dx, y + dy, zbot + h / 2), (ex, ey, h), "Graphite")
    hover.box((x, y, zbot + 0.006), (sx - 0.05, sy - 0.05, 0.004), "Emit_Hover")
    for k in range(1, 4 if plate else 3):
        hover.box((x, y - sy / 2 + k * sy / (4 if plate else 3), zbot + 0.003), (sx - 0.05, 0.008, 0.006), "Metal")
    hover.box((x, y, zb + 0.02), (sx - 0.02, sy - 0.02, 0.02), "Metal")
    emit_cuts.append(box_cutter((x, y, zb), (sx + GAP, sy + GAP, 0.08)))
for s in (-1, 1):                                                                       # sensors
    zb = body(-3.20)["zb"]
    hover.cyl((s * 0.26, -3.20, zb + 0.01), (s * 0.26, -3.20, zb - 0.012), 0.02, "Graphite", 12)
    hover.cyl((s * 0.26, -3.20, zb - 0.012), (s * 0.26, -3.20, zb - 0.014), 0.013, "Black", 12)
hover.finish(G["Hover"])

# ---- cockpit: floor, dash, controls, seat and pilot (reclined, the head under the carapace glass)
ck = Part("Cockpit_Parts")
ck.box((0, -1.55, 0.33), (0.62, 1.10, 0.012), "Graphite")                               # floor
ck.box((0, -1.88, 0.68), (0.46, 0.14, 0.09), "Graphite")                                # dash
ck.box((0, -1.809, 0.70), (0.30, 0.004, 0.05), "Emit_Hover")                            # display
ck.cyl((0, -1.81, 0.66), (0, -1.50, 0.61), 0.016, "Metal", 10)                          # column
ck.box((0, -1.49, 0.61), (0.28, 0.026, 0.026), "Metal")                                 # handlebar
for s in (-1, 1):
    ck.cyl((s * 0.12, -1.49, 0.61), (s * 0.18, -1.49, 0.61), 0.019, "Graphite", 10)
    ck.box((s * 0.28, -1.40, 0.46), (0.08, 0.50, 0.18), "Graphite")                     # side consoles
    ck.box((s * 0.28, -1.50, 0.552), (0.05, 0.10, 0.004), "Emit_Amber")
ck.box((0, -1.08, 0.37), (0.38, 0.26, 0.05), "Graphite")                                # seat
back = Matrix.Rotation(math.radians(-30), 3, 'X')
ck.box((0, -0.90, 0.55), (0.38, 0.05, 0.36), "Graphite", back)                          # back rest
ck.finish(G["Cockpit_Cell"], bevel=0.003)
pilot = Part("Pilot")
pilot.tube([(0, -1.11, 0.44), (0, -1.02, 0.57), (0, -0.94, 0.69)], 0.11, "Paint_White", 12)   # torso
pilot.sphere((0, -0.95, 0.71), 0.072, "Paint_White", (1.6, 1.0, 0.7))                  # shoulders
pilot.sphere((0, -0.91, 0.80), 0.095, "Paint_Yellow")                                  # helmet
pilot.sphere((0, -0.985, 0.805), 0.052, "Black", (1.3, 0.7, 0.85))                     # visor
for s in (-1, 1):
    pilot.tube([(s * 0.13, -0.95, 0.69), (s * 0.17, -1.22, 0.60), (s * 0.13, -1.49, 0.61)], 0.034, "Paint_White")
    pilot.sphere((s * 0.13, -1.50, 0.61), 0.031, "Graphite")                             # gloves
    pilot.tube([(s * 0.08, -1.12, 0.42), (s * 0.09, -1.55, 0.50), (s * 0.08, -1.98, 0.46)], 0.047, "Paint_White")
    pilot.sphere((s * 0.08, -2.01, 0.46), 0.043, "Graphite", (1.0, 1.4, 1.0))           # boots
pilot.finish(G["Cockpit_Cell"])

# ================================================================ 3. WINGS (swept out of the wing-body edges, tips folded up)
WING = [(1.20, 0.50, 2.05), (1.98, 1.62, 2.38)]   # x, leading edge y, trailing edge y


def wing_at(x):
    le, te = table(WING, x)
    f = (x - 1.20) / 0.78
    return le, te, 0.365 - 0.035 * f, 0.075 - 0.035 * f


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


for s, side in ((1, "R"), (-1, "L")):
    gw = G["Wing_" + side]

    def w3d(x, y, z, s=s):
        return Vector((s * x, y, z))

    def w_centre(c):
        le, te, mid, th = wing_at(abs(c.x))
        return Vector((c.x, (le + te) / 2, mid))

    spar = Part("Wing_Structure_" + side)
    p0, p1 = wing_at(1.20), wing_at(1.96)
    for f in (0.40, 0.85):
        a = (1.18, p0[0] + f * (p0[1] - p0[0]), p0[2])
        b = (1.96, p1[0] + f * (p1[1] - p1[0]), p1[2])
        spar.tube([(s * a[0], a[1], a[2]), (s * b[0], b[1], b[2])], 0.018 if f < 0.5 else 0.013, "Metal",
                  square=True)
        spar.box((s * 1.20, a[1], p0[2]), (0.06, 0.10, 0.06), "Metal")                  # root clamps
    for x in (1.45, 1.70, 1.94):
        L = inset(wing_loop(x), 0.010)
        spar.loft([[Vector((s * (x + d), q.x, q.y)) for q in L] for d in (-0.005, 0.005)], lambda i, j: "Metal",
                  closed_u=True, cap0="Metal", cap1="Metal")
    spar.finish(gw, bevel=0.002)

    def skin(name, t0, t1, m_fn, cuts=()):
        p = Part(name + "_" + side)
        surface(p, wing_loop, t0, t1, 1.20, 1.98, [r[0] for r in WING], w3d, (False, False))
        orient_out(p, w_centre)
        paint(p, m_fn, cuts)
        return shell(p, gw, thick=0.006, bevel=0.0015)

    skin("Wing_Top", 2, 3, lambda c, n: "Paint_Yellow" if abs(c.x) > 1.66 else "Paint_Slate",
         [((1.66, 0, 0), (1, 0, 0)), ((-1.66, 0, 0), (1, 0, 0))])
    skin("Wing_Bottom", 6, 7, lambda c, n: "Graphite")
    skin("Wing_TE", 3, 6, lambda c, n: "Paint_Slate")
    skin("Wing_LE", 7, 10, lambda c, n: "Paint_Orange")
    tip = Part("Wing_Tip_" + side)
    L = wing_loop(1.98 - GAP / 2)
    tip.loft([[Vector((s * (1.98 - GAP / 2 - d), q[0], q[1])) for q in L] for d in (0, 0.01)],
             lambda i, j: "Paint_Slate", closed_u=True, cap0="Paint_Slate", cap1="Paint_Slate")
    tip.finish(gw, bevel=0.002, skin=True)
    fold = Part("Wing_Fold_" + side)                                                     # the tip folded up
    shark_fin(fold, lambda y: wing_top(1.94), s * 1.94, (1.66, 2.38), (1.94, 2.42), 0.30, 0.034, "Paint_Yellow",
              "Paint_Slate", math.radians(12), s)
    fold.finish(gw, bevel=0.0015, smooth_angle=60, skin=True)

slots = []
for s in (-1, 1):
    p = Part("cut")
    p.loft([[Vector((s * x, a, b)) for a, b in wing_loop(x, GAP / 2)] for x in (1.16, 1.42)], lambda i, j: "Black",
           closed_u=True, cap0="Black", cap1="Black")
    slots.append(cutter(p))

# ================================================================ 4. BODYWORK
# ---- the nose of the wing-body: a small two-tone face with the lights and a sensor window, the bumper below
bn = body(Y_NOSE)
face = Part("Nose_Front")
face.loft([[Vector((x, y, z)) for x, z in body_loop(Y_NOSE)] for y in (Y_NOSE - SKIN, Y_NOSE)],
          lambda i, j: "Paint_Slate", closed_u=True, cap0="Paint_Slate", cap1="Paint_Slate")
paint(face, lambda c, n: "Paint_Yellow" if c.z > bn["zh"] else "Paint_Slate", [((0, 0, bn["zh"]), (0, 0, 1))])
face.finish(G["Nose"], bevel=0.002, recalc=True, skin=True)
lamps = Part("Nose_Lights")
for s in (-1, 1):
    lamps.cyl((s * 0.24, Y_NOSE - SKIN, 0.53), (s * 0.24, Y_NOSE - SKIN - 0.03, 0.53), 0.05, "Graphite", 20)
    lamps.cyl((s * 0.24, Y_NOSE - SKIN - 0.03, 0.53), (s * 0.24, Y_NOSE - SKIN - 0.033, 0.53), 0.038,
              "Emit_Light", 20)
lamps.box((0, Y_NOSE - SKIN - 0.008, 0.535), (0.16, 0.016, 0.06), "Black")              # sensor window
lamps.box((0, Y_NOSE - SKIN - 0.006, 0.535), (0.20, 0.012, 0.09), "Graphite")
lamps.finish(G["Nose"])

# ---- the body in three stretches: carapace (top, flanks), wing surface, edges, chines, belly
for pre, a, b, g in (("Front", Y_NOSE, Y_A, (False, True)), ("Mid", Y_A, Y_B, (True, True)),
                     ("Rear", Y_B, Y_CONE, (True, True))):
    panel(pre + "_Top", 5, 7, a, b, B, carapace_paint, GLASS_CUTS, gap_s=g)
    for side, s in (("R", 1), ("L", -1)):
        def span(t0, t1):
            return (t0, t1) if s > 0 else (12 - t1, 12 - t0)
        panel(pre + "_Flank_" + side, *span(4, 5), a, b, B, carapace_paint, GLASS_CUTS, intake_cuts, gap_s=g)
        panel(pre + "_Wing_" + side, *span(3, 4), a, b, B, slate, holes=bag_cuts, gap_s=g)
        panel(pre + "_Edge_" + side, *span(2, 3), a, b, B, slate, holes=slots, gap_s=g)
        panel(pre + "_Chine_" + side, *span(1, 2), a, b, B, slate, holes=slots, gap_s=g)
    panel(pre + "_Belly", 11, 13, a, b, B, lambda c, n: "Graphite", holes=emit_cuts, gap_s=g)
drop(intake_cuts + bag_cuts + emit_cuts + slots)

frame = Part("Canopy_Frame")                                     # frame round the flush glass, a strut down the middle
ys = [CAN[0]] + [y for y in BODY_Y if CAN[0] < y < CAN[1]] + [CAN[1]]
lift = Vector((0, 0, 0.006))


def glass_edge(y, s):      # where the glass starts on the flank (0.70 m up), on side s
    a, b = facet_point(y, s, 4, 5, 0.0), facet_point(y, s, 4, 5, 1.0)
    return a.lerp(b, min(1.0, max(0.0, (0.70 - a.z) / (b.z - a.z)))) + facet_normal(y, s, 4, 5) * 0.006


for s in (-1, 1):
    frame.tube([glass_edge(y, s) for y in ys], 0.011, "Graphite", 8)
    frame.tube([facet_point(y, s, 5, 5, 0) + lift for y in ys], 0.011, "Graphite", 8)
for y in CAN:
    frame.tube([glass_edge(y, -1), facet_point(y, -1, 5, 5, 0) + lift, facet_point(y, 1, 5, 5, 0) + lift,
                glass_edge(y, 1)], 0.011, "Graphite", 8)
frame.tube([Vector((0, y, body(y)["zt"])) + lift for y in ys], 0.009, "Graphite", 8)
frame.finish(G["Cockpit_Cell"])

# ---- details: the roof hatch, grab handles, amber marker lights in the edges
det = Part("Hull_Details")
yh = -0.45
zt = body(yh)["zt"]
det.lathe((0, yh, zt - 0.004), (0, yh, zt + 0.012), [(0, 0.24), (1, 0.24), (1, 0.21), (0, 0.21)],
          lambda k: "Graphite", 40, closed=True)                                       # hatch ring
for dx in (-0.09, 0.09):
    det.tube([(dx, yh - 0.06, zt + 0.004), (dx, yh - 0.06, zt + 0.035), (dx, yh + 0.06, zt + 0.035),
              (dx, yh + 0.06, zt + 0.004)], 0.008, "Metal_Bright", 8)                  # handles
for s in (-1, 1):
    for y in (0.75, 1.15):                                                             # grab handles on the flank
        n = facet_normal(y, s, 4, 5)
        a, c = facet_point(y - 0.09, s, 4, 5, 0.75), facet_point(y + 0.09, s, 4, 5, 0.75)
        det.tube([a, a + n * 0.032, c + n * 0.032, c], 0.008, "Metal_Bright", 8)
    for y in (-2.40, -2.10, 2.30, 2.55):                                               # marker lights
        b = body(y)
        z = (b["zb"] + b["cb"] + b["zs"]) / 2
        det.cyl((s * b["w"], y, z), (s * (b["w"] + 0.014), y, z), 0.022, "Graphite", 16)
        det.cyl((s * (b["w"] + 0.014), y, z), (s * (b["w"] + 0.017), y, z), 0.015, "Emit_Amber", 16)
det.finish(B)

# ---- the tail cone round the engine, then the collar with its lip, a heat shield inside, the shark fin on top
cone, ci = tail_loop(body_loop(Y_CONE), (0, ENG_Z), SH_OUT, Y_CONE, Y_CONE1, power=1.6)
CONE_Y = [Y_CONE + k * (Y_CONE1 - Y_CONE) / 4 for k in range(5)]
nc = len(cone(Y_CONE))
for name, t0, t1, m_fn in (("Tail_Belly", ci[10], nc + ci[2], slate),
                           ("Tail_Side_R", ci[2], ci[4], slate),
                           ("Tail_Carapace", ci[4], ci[8], lambda c, n: "Paint_Yellow"),
                           ("Tail_Side_L", ci[8], ci[10], slate)):
    p = Part(name)
    surface(p, cone, t0, t1, Y_CONE, Y_CONE1, CONE_Y, xyz, (True, False))
    orient_out(p, lambda c: Vector((0, c.y, ENG_Z)))
    paint(p, m_fn)
    shell(p, B)


def collar_paint(c, n):
    if c.y > Y_END - 0.004 and abs(n.y) > 0.9:
        return "Metal_Bright"                                  # lip at the exit
    if (c - Vector((0, c.y, ENG_Z))).dot(n) < 0:
        return "Graphite"                                      # inside
    return "Paint_Orange" if c.y > Y_END - 0.07 else "Paint_Slate"


cl = Part("Engine_Collar")
cl.loft([[Vector((x, y, ENG_Z + z)) for x, z in sec] for y, sec in
         ((Y_CONE1, SH_OUT), (Y_END, SH_OUT), (Y_END, SH_IN), (Y_CONE1, SH_IN))],
        lambda i, j: "Paint_Slate", closed_u=True, closed_v=True)
bmesh.ops.recalc_face_normals(cl.bm, faces=cl.bm.faces[:])
paint(cl, collar_paint, [((0, Y_END - 0.07, 0), (0, 1, 0))])
for dz in (SH_HH + 0.002, -SH_HH - 0.002):
    cl.box((0, Y_END - 0.035, ENG_Z + dz), (0.40, 0.04, 0.006), "Emit_Red")              # tail lights
cl.finish(GE, bevel=0.002, recalc=False, skin=True)
sh = Part("Collar_Bulkhead")                                     # heat shield across the collar, round the bell
ring_in = [loop_at(SEC, k / 48) * 1.06 for k in range(48)]
ring_out = [loop_at(SH_IN, k / 48) * 0.995 for k in range(48)]
sh.loft([[Vector((p.x, y, ENG_Z + p.y)) for p in ring] for ring, y in
         ((ring_out, Y_CONE1 + 0.004), (ring_in, Y_CONE1 + 0.004), (ring_in, Y_CONE1 + 0.016),
          (ring_out, Y_CONE1 + 0.016))], lambda i, j: "Ceramic", closed_u=True, closed_v=True)
sh.finish(GE)


def top_z(y):              # the top of the carapace, the cone and the collar along the centre line
    if y <= Y_CONE:
        return body(y)["zt"]
    if y < Y_CONE1:
        return cone(y)[ci[6]][1]
    return ENG_Z + SH_HH


fin = Part("Shark_Fin")
shark_fin(fin, top_z, 0.0, (1.25, 3.22), (2.70, 3.36), 0.34, 0.05, "Paint_Slate", "Paint_Yellow")
fin.finish(B, bevel=0.0015, smooth_angle=60, skin=True)

# ================================================================ 5. DECALS (our own marks)
dec = Part("Decals")
yn = 0.75                                                                               # big number on the roof
dec.add_mesh(text_mesh("05", 0.36), frame_on((0, yn, body(yn)["zt"]), (1, 0, 0), (0, 1, 0), 0.002), "Black")
tri = [(0, 0.10), (-0.087, -0.05), (0.087, -0.05)]
yt = -0.45                                                                              # warning on the hatch
dec.poly([frame_on((0, yt - 0.215, body(yt)["zt"]), (-1, 0, 0), (0, -1, 0), 0.004) @ Vector((x, y, 0))
          for x, y in tri], "Paint_Red")
for s in (-1, 1):
    rd = 1 if s > 0 else -1
    y = 1.55                                                                            # name on the flank
    u = facet_point(y + 0.05, s, 4, 5, 0.5) - facet_point(y - 0.05, s, 4, 5, 0.5)
    dec.add_mesh(text_mesh("BASTION", 0.11), frame_on(facet_point(y, s, 4, 5, 0.42), u * rd, facet_up(y, s, 4, 5),
                                                      0.004), "Black")
    y0, y1, z0, z1 = INTAKE                                                             # hazard stripes ahead of
    for k in range(4):                                                                  # the intake
        yy = y0 - 0.09 - k * 0.05
        a, b = facet_point(yy, s, 4, 5, 0.0), facet_point(yy, s, 4, 5, 1.0)
        Mh = frame_on(a.lerp(b, ((z0 + z1) / 2 - a.z) / (b.z - a.z)), Vector((0, rd, 0)), b - a, 0.004)
        dec.poly([Mh @ Vector(q) for q in ((-0.010, -0.10, 0), (0.014, -0.10, 0), (0.038, 0.10, 0),
                                           (0.014, 0.10, 0))], "Black")
    for yb, f, r in BAGS:                                                               # airbag warnings
        Mt = frame_on(facet_point(yb - r - 0.08, s, 3, 4, f), Vector((0, rd, 0)), facet_up(yb, s, 3, 4), 0.003)
        dec.poly([Mt @ Vector((x * 0.6, yy * 0.6, 0)) for x, yy in tri], "Paint_Red")
    xc, yc = 1.62, 1.95                                                                 # league emblem on the wing
    d = (wing_top(xc + 0.05) - wing_top(xc - 0.05)) / 0.1
    M2 = frame_on((s * xc, yc, wing_top(xc) + 0.0005), (s, 0, d), (0, s, 0))
    o, i_ = ring2d(0.085, 0.10)
    dec.flat(o, M2, "Black", holes=[i_])
    dec.poly([M2 @ Vector(((0.072 if k % 2 == 0 else 0.018) * math.cos(math.pi / 2 + k * math.pi / 4),
                           (0.072 if k % 2 == 0 else 0.018) * math.sin(math.pi / 2 + k * math.pi / 4), 0))
              for k in range(8)], "Black")
dec.finish(G["Decals"], recalc=False, smooth_angle=10)

# ================================================================ sockets
for name, loc in (("Socket_Reactor", (0, -0.20, 0.62)), ("Socket_Propulsion", (0, EXIT, ENG_Z)),
                  ("Socket_Wing_L", (-1.20, 1.25, 0.365)), ("Socket_Wing_R", (1.20, 1.25, 0.365)),
                  ("Socket_Tail", (0, Y_END, ENG_Z - SH_HH)), ("Socket_Armor_L", (-1.30, -0.60, 0.36)),
                  ("Socket_Armor_R", (1.30, -0.60, 0.36)), ("Socket_Cooling", (0, 1.30, 1.09)),
                  ("Socket_Utility", (0, -2.90, 0.55))):
    group(name, G["Sockets"], loc)

finish_ship(G["Decals"], cockpit=((-1.5, -3.2, 1.6), (0, -1.30, 0.78)), scale=1.15)

# ================================================================ modules (Docs/MODULOS.md): the split for the game and the variants
from ship_modules import build_modules  # noqa: E402
build_modules(globals(), wings=("longspan", "brace", "glide"), palette=("Paint_Slate", "Paint_Yellow", "Paint_Orange"),
              tail="below", scale=1.1, nozzle_r=0.30)
