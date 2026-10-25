# BASTION hover racer (the heaviest: armoured, five lives, slow to push off line), built from the inside out like the
# others: structure (frames and longerons round the body, crash bumper, cockpit cell, engine mounts), systems (cockpit
# and pilot, reactor and its line, one colossal plasma engine, coolant intakes and radiators, hover emitters, four
# stowed impact airbags), then the 12 mm bodywork panels with 5 mm gaps.
# Look: the whole ship is one colossal engine (the opposite of the VORTEX, which is all one wing): a fat faceted body,
# widest at the back, a yellow armoured carapace over a slate lower body, a low hood and the windscreen flush in the
# front of the carapace, a blunt armoured nose with lights and a bumper, side pods along the rear flanks with
# orange-lined coolant intakes in their fronts, the impact airbags stowed in round housings at the lower corners, the
# body tapering round the engine into a heavy collar, a long shark fin on the rear deck, amber ports; yellow, slate
# and orange
# (Docs/BASTION_CATEGORIA.md, Docs/NAVES_REGRAS.md). No wings: the BASTION has no wing slot.
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
                                 "Hover", "Cooling", "Airbags", "Decals", "Sockets")}
B = G["Body"]

# ---------------------------------------------------------------- lines
# A slate body (belly, bottom chamfer, side wall up to zs) under a yellow carapace (shoulder facet up to zh at sh in
# from the side, upper facet up to the top at ct in, the flat top). Widest at the back, where the side pods add to
# it; the tail cone runs from the last station into the collar round the engine.
#        y      w      zb    cb    zs    sh    zh     ct    zt
BODY = [(-3.45, .640, .420, .090, .600, .120, .760, .340, .820),
        (-3.15, .900, .330, .120, .690, .150, .930, .420, 1.020),
        (-2.40, 1.080, .260, .140, .760, .170, 1.100, .470, 1.250),
        (-1.30, 1.200, .240, .150, .820, .180, 1.240, .500, 1.440),
        (0.00, 1.270, .240, .150, .840, .180, 1.290, .520, 1.520),
        (1.30, 1.290, .250, .150, .840, .180, 1.290, .520, 1.520),
        (2.20, 1.180, .280, .140, .840, .170, 1.250, .480, 1.460),
        (2.80, 1.000, .330, .120, .840, .160, 1.170, .420, 1.340)]
BODY_Y = [r[0] for r in BODY]
Y_NOSE, Y_A, Y_B, Y_CONE, Y_CONE1, Y_END = -3.45, -1.30, 1.60, 2.80, 3.20, 3.42
CAN = (-2.35, -1.25)              # the windscreen: the carapace's upper facets and top over the cockpit
ENG_Z = 0.82                      # the colossal engine: a wide rounded box filling the rear of the body
SEC = shape_loop(0.62, 0.52, 0.28, 0.11)
SH_HH = 0.36
SH_OUT = shape_loop(0.78, 0.66, SH_HH, 0.13)        # the collar round its nozzle
SH_IN = shape_loop(0.73, 0.61, SH_HH - 0.04, 0.10)
BAGS = [(-2.05, 0.55, 0.15)]      # front airbags in the side walls: y, z, radius (the rear pair is in the pods)
POD = (-0.05, 2.25, 2.74)         # side pods: front face (the intake), end of the full section, rear tip
POD_Z, POD_SINK = 0.62, 0.10      # pod centre height; how far it sits into the side wall
POD_SEC = shape_loop(0.26, 0.21, 0.33, 0.09)
INTAKE = (0.34, 0.42)             # the intake in each pod front: width, height
POD_BAG = (1.85, 0.20)            # the rear airbag in each pod's outer wall: y, radius
POD_VENT = (0.40, 1.20, 0.50, 0.76)   # a louvred vent in each pod's outer wall: y0, y1, z0, z1


def body(y):
    return dict(zip(("w", "zb", "cb", "zs", "sh", "zh", "ct", "zt"), table(BODY, y)))


def body_loop(y):
    """12 points counter-clockwise from the bottom centre: t 1..2 the bottom chamfer, 2..3 the side wall, 3..4 the
    shoulder facet, 4..5 the upper facet, 5..7 the top, 11..13 the belly (left side mirrored)."""
    b = body(y)
    r = [(0, b["zb"]), (b["w"] - b["cb"], b["zb"]), (b["w"], b["zb"] + b["cb"]), (b["w"], b["zs"]),
         (b["w"] - b["sh"], b["zh"]), (b["w"] - b["ct"], b["zt"]), (0, b["zt"])]
    return r + [(-x, z) for x, z in reversed(r[1:-1])]


def pod_x(y):            # the pod's centre: on the side wall, sliding in towards the tail as it tapers
    f = min(max((y - POD[1]) / (POD[2] - POD[1]), 0.0), 1.0)
    return body(min(y, Y_CONE))["w"] + 0.26 - POD_SINK - 0.30 * f * f


def pod_scale(y):
    f = min(max((y - POD[1]) / (POD[2] - POD[1]), 0.0), 1.0)
    return 1.0 - 0.72 * f ** 1.5


def pod_wall(y):          # how far out the pod's outer wall is at its centre height
    return pod_x(y) + 0.235 * pod_scale(y)


def frame_loop(y):        # the frames' outline: the eight corners of the body, inside the panels
    L = body_loop(y)
    return [L[i] for i in (1, 2, 3, 4, 5, 7, 8, 9, 10, 11)]


def xyz(y, x, z):
    return Vector((x, y, z))


def body_centre(c):
    return Vector((0, c.y, (body(c.y)["zb"] + body(c.y)["zt"]) / 2))


def facet_point(y, s, i, j, f):       # point at fraction f from corner i to corner j of the section, on side s
    L = body_loop(y)
    (x0, z0), (x1, z1) = L[i], L[j]
    return Vector((s * (x0 + (x1 - x0) * f), y, z0 + (z1 - z0) * f))


def panel(name, t0, t1, y0, y1, parent, m_fn, cuts=(), holes=(), gap_s=(True, True)):
    p = Part(name)
    surface(p, body_loop, t0, t1, y0, y1, BODY_Y, xyz, gap_s)
    orient_out(p, body_centre)
    paint(p, m_fn, cuts)
    return shell(p, parent, holes)


GLASS_CUTS = [((0, CAN[0], 0), (0, 1, 0)), ((0, CAN[1], 0), (0, 1, 0))]


def carapace_paint(c, n):
    if CAN[0] < c.y < CAN[1] and n.z > 0.2:
        return "Glass"
    return "Paint_Yellow"


def slate(c, n):
    return "Graphite" if n.z < -0.6 else "Paint_Slate"


# ================================================================ 1. STRUCTURE
fr = Part("Frames")
for y in (-3.15, -2.40, -1.30, -0.20, 0.60, 1.30, 2.20, 2.75):
    o, i_ = inset(frame_loop(y), SKIN + CLEAR), inset(frame_loop(y), SKIN + CLEAR + 0.035)
    fr.loft([[Vector((p.x, y + dy, p.y)) for p in ring] for ring, dy in
             ((o, -0.014), (o, 0.014), (i_, 0.014), (i_, -0.014))], lambda i, j: "Metal", closed_u=True, closed_v=True)
fr.finish(G["Structural_Core"], bevel=0.002)

lon = Part("Longerons")
for k in (1, 2, 3, 6, 7, 8):
    path = []
    for y in [-3.30] + [s for s in BODY_Y if -3.30 < s < 2.75] + [2.75]:
        p = inset(frame_loop(y), SKIN + CLEAR + 0.018)[k]
        path.append((p.x, y, p.y))
    lon.tube(path, 0.014, "Metal", square=True)
lon.finish(G["Structural_Core"], bevel=0.002)

crash = Part("Crash_Bumper")                                                           # the armoured front bumper
crash.box((0, -3.53, 0.50), (1.06, 0.10, 0.11), "Graphite")
crash.box((0, -3.585, 0.50), (0.96, 0.012, 0.05), "Paint_Orange")
for s in (-1, 1):
    crash.box((s * 0.53, -3.50, 0.50), (0.08, 0.14, 0.13), "Graphite")
    crash.cyl((s * 0.32, -3.48, 0.50), (s * 0.32, -3.20, 0.50), 0.035, "Metal", 12)     # crash cans
crash.finish(G["Nose"], bevel=0.003)

mnt = Part("Engine_Mounts")                       # struts from the frames to the engine casing
for y in (1.30, 2.20):
    fl = inset(frame_loop(y), SKIN + CLEAR + 0.03)
    for k, q in ((1, 0.125), (3, 0.375), (6, 0.625), (8, 0.875)):
        p = loop_at(SEC, q) * 1.03 + Vector((0, ENG_Z))
        mnt.tube([(p.x, y, p.y), (fl[k].x, y, fl[k].y)], 0.022, "Metal", square=True)
mnt.finish(G["Structural_Core"], bevel=0.002)

# ================================================================ 2. SYSTEMS
# ---- one colossal plasma engine: the casing runs most of the body, the coils and the bell in the tail
GE = G["Propulsion"]
eng = Part("Engine")
EXIT = space_engine(eng, (0, ENG_Z), 0.60, 2.80, SEC, coil_len=0.30, bell_len=0.32)
for y in (0.80, 1.70, 2.50):                                                            # casing bands
    eng.sweep((0, ENG_Z), y, y + 0.06, [(0, 1.04), (1, 1.04)], SEC, lambda k: "Graphite", closed=False)
eng.finish(GE)

# ---- reactor behind the cockpit and its line into the engine
rc = Part("Reactor_Core")
rc.lathe((0, -0.85, 0.70), (0, 0.42, 0.70),
         [(0, 0.0), (0.03, 0.12), (0.07, 0.19), (0.16, 0.20), (0.21, 0.185), (0.26, 0.20), (0.48, 0.20),
          (0.53, 0.185), (0.58, 0.20), (0.80, 0.20), (0.85, 0.185), (0.90, 0.20), (0.96, 0.19), (0.99, 0.12),
          (1, 0.0)], lambda k: "Emit_Hot" if k in (3, 4, 7, 8, 11, 12) else "Metal_Bright", 24)
for y in (-0.62, 0.20):
    rc.box((0, y, 0.43), (0.36, 0.06, 0.12), "Metal")                                   # saddles
rc.tube([(0, 0.42, 0.70), (0, 0.48, 0.76), (0, 0.54, ENG_Z)], 0.02, "Metal", 10)
for s in (-1, 1):                                                                       # lines to the coils
    rc.tube([(s * 0.16, 0.30, 0.82), (s * 0.30, 0.70, 1.18), (s * 0.30, 2.60, 1.18), (s * 0.20, 2.86, 1.10)],
            0.014, "Metal", 8)
rc.finish(G["Reactor"])

# ---- side pods along the rear flanks: a coolant intake in each front (orange-lined), radiators inside, a duct to the
# engine; the rear airbags sit in their outer walls. They taper into the tail.
pods = Part("Side_Pods")
pod_cuts = []
for s_ in (-1, 1):
    ys = [POD[0]] + [y for y in BODY_Y if POD[0] < y < POD[1]] + [POD[1]] + \
        [POD[1] + (POD[2] - POD[1]) * k / 6 for k in range(1, 7)]
    rows = []
    for y in ys:
        k, xc = pod_scale(y), s_ * pod_x(y)
        rows.append([Vector((xc + x * k, y, POD_Z + z * k)) for x, z in POD_SEC])
    pods.loft(rows, lambda i, j: "Paint_Slate", closed_u=True, cap0="Paint_Slate", cap1="Paint_Slate")
    xi, (iw, ih) = s_ * pod_x(POD[0]), INTAKE
    pod_cuts.append(box_cutter((xi, POD[0], POD_Z), (iw, 0.16, ih)))
    y0, y1, z0, z1 = POD_VENT
    pod_cuts.append(box_cutter((s_ * pod_wall((y0 + y1) / 2), (y0 + y1) / 2, (z0 + z1) / 2), (0.12, y1 - y0, z1 - z0)))
    yb, rb = POD_BAG
    xo = s_ * pod_wall(yb)
    c = Part("cut")
    c.cyl((xo + s_ * 0.08, yb, POD_Z), (xo - s_ * 0.08, yb, POD_Z), rb + 0.03 + GAP / 2, "Black", 32)
    pod_cuts.append(cutter(c))
bmesh.ops.recalc_face_normals(pods.bm, faces=pods.bm.faces[:])
paint(pods, lambda c, n: "Graphite" if n.z < -0.6 else "Paint_Yellow" if n.z > 0.45 else "Paint_Slate")
ob = pods.finish(B, bevel=0.003, recalc=False, skin=True)
boolean(ob, pod_cuts)
shade(ob, 0.003)
drop(pod_cuts)

cool = Part("Radiators")
for s_ in (-1, 1):
    xi, (iw, ih) = s_ * pod_x(POD[0]), INTAKE
    y0 = POD[0]
    cool.box((xi, y0 + 0.09, POD_Z), (iw, 0.03, ih), "Black")                             # radiator face
    for k in range(7):                                                                    # louvres
        cool.box((xi, y0 + 0.05, POD_Z - ih / 2 + (k + 0.5) * ih / 7), (iw - 0.01, 0.05, 0.010), "Graphite",
                 Matrix.Rotation(math.radians(-30), 3, 'X'))
    for dz in (-ih / 2 + 0.004, ih / 2 - 0.004):                                          # orange lining inside
        cool.box((xi, y0 + 0.04, POD_Z + dz), (iw, 0.09, 0.008), "Paint_Orange")
    for dx in (-iw / 2 + 0.004, iw / 2 - 0.004):
        cool.box((xi + dx, y0 + 0.04, POD_Z), (0.008, 0.09, ih), "Paint_Orange")
    for dz in (-ih / 2 - 0.018, ih / 2 + 0.018):                                          # lip round the mouth
        cool.box((xi, y0 - 0.012, POD_Z + dz), (iw + 0.072, 0.03, 0.036), "Paint_Orange")
    for dx in (-iw / 2 - 0.018, iw / 2 + 0.018):
        cool.box((xi + dx, y0 - 0.012, POD_Z), (0.036, 0.03, ih), "Paint_Orange")
    cool.tube([(xi, y0 + 0.12, POD_Z), (s_ * (pod_x(1.2) - 0.10), 1.20, POD_Z + 0.06), (s_ * 0.70, 2.30, 0.80)],
              0.06, "Metal", 10)                                                          # duct to the engine
    v0, v1, z0, z1 = POD_VENT                                                             # the side vent
    xw = pod_wall((v0 + v1) / 2)
    cool.box((s_ * (xw - 0.07), (v0 + v1) / 2, (z0 + z1) / 2), (0.03, v1 - v0, z1 - z0), "Black")
    for k in range(8):
        cool.box((s_ * (xw - 0.035), v0 + (k + 0.5) * (v1 - v0) / 8, (z0 + z1) / 2), (0.05, 0.012, z1 - z0 - 0.01),
                 "Graphite", Matrix.Rotation(math.radians(30 * s_), 3, 'Z'))
    for dz in (z0 - 0.016, z1 + 0.016):
        cool.box((s_ * (xw + 0.008), (v0 + v1) / 2, dz), (0.03, v1 - v0 + 0.064, 0.032), "Paint_Orange")
    for yy in (v0 - 0.016, v1 + 0.016):
        cool.box((s_ * (xw + 0.008), yy, (z0 + z1) / 2), (0.03, 0.032, z1 - z0), "Paint_Orange")
cool.finish(G["Cooling"])

# ---- impact airbags stowed in round housings in the lower side walls (three tan lobes each)
bags = Part("Airbags")
bag_cuts = []
BAG_AT = [(y, z, r, lambda y_: body(y_)["w"], True) for y, z, r in BAGS] + \
    [(POD_BAG[0], POD_Z, POD_BAG[1], pod_wall, False)]
for s in (-1, 1):
    for y, z, r, wall, in_body in BAG_AT:
        w = wall(y)
        bags.lathe((s * (w + 0.012), y, z), (s * (w - 0.05), y, z), [(0, r + 0.03), (0.3, r + 0.03), (0.3, r),
                                                                      (1, r)], lambda k: "Graphite", 32)
        bags.cyl((s * (w - 0.05), y, z), (s * (w - 0.06), y, z), r, "Metal", 32)       # back plate
        for k, dz in enumerate((-0.58, 0.0, 0.58)):                                     # the folded bag
            rz = r * (0.42 if k != 1 else 0.48)
            bags.sphere((s * (w - 0.005), y, z + dz * r), 1.0, "Fabric_Tan", (0.07, r * 0.92, rz), 20, 10)
        for dy in (-0.55 * r, 0.55 * r):                                                # straps
            bags.box((s * (w + 0.06), y + dy, z), (0.012, 0.02, 1.7 * r), "Graphite")
        if in_body:
            c = Part("cut")
            c.cyl((s * (w + 0.08), y, z), (s * (w - 0.08), y, z), r + 0.03 + GAP / 2, "Black", 32)
            bag_cuts.append(cutter(c))
bags.finish(G["Airbags"], bevel=0.0015)

# ---- hover: emitter modules in cut-outs of the belly, a gravity plate in the middle, sensors
hover = Part("Hover_Emitters")
emit_cuts = []
mods = [(y, s * x, sx, sy) for y, x, sx, sy in ((-2.70, 0.42, 0.24, 0.40), (-1.40, 0.56, 0.26, 0.48),
                                                (1.30, 0.56, 0.26, 0.48), (2.45, 0.42, 0.22, 0.36)) for s in (-1, 1)]
mods += [(-0.10, 0.0, 0.62, 0.90)]
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
    zb = body(-3.25)["zb"]
    hover.cyl((s * 0.36, -3.25, zb + 0.01), (s * 0.36, -3.25, zb - 0.012), 0.022, "Graphite", 12)
    hover.cyl((s * 0.36, -3.25, zb - 0.012), (s * 0.36, -3.25, zb - 0.014), 0.014, "Black", 12)
hover.finish(G["Hover"])

# ---- cockpit: floor, dash, controls, side consoles, seat and pilot (sitting low, the head under the glass)
ck = Part("Cockpit_Parts")
ck.box((0, -1.70, 0.42), (0.70, 1.35, 0.014), "Graphite")                               # floor
ck.box((0, -2.05, 0.96), (0.66, 0.16, 0.12), "Graphite")                                # dash
ck.box((0, -1.97, 0.99), (0.40, 0.004, 0.06), "Emit_Hover")                            # display
ck.cyl((0, -1.97, 0.92), (0, -1.77, 0.86), 0.018, "Metal", 10)                          # column
ck.box((0, -1.76, 0.86), (0.34, 0.03, 0.03), "Metal")                                   # handlebar
for s in (-1, 1):
    ck.cyl((s * 0.15, -1.76, 0.86), (s * 0.22, -1.76, 0.86), 0.021, "Graphite", 10)
    ck.box((s * 0.33, -1.60, 0.62), (0.10, 0.60, 0.24), "Graphite")                     # side consoles
    ck.box((s * 0.33, -1.75, 0.745), (0.06, 0.12, 0.004), "Emit_Amber")
ck.box((0, -1.37, 0.50), (0.46, 0.30, 0.06), "Graphite")                                # seat
back = Matrix.Rotation(math.radians(-14), 3, 'X')
ck.box((0, -1.17, 0.74), (0.46, 0.06, 0.48), "Graphite", back)                          # back rest
ck.finish(G["Cockpit_Cell"], bevel=0.003)
pilot = Part("Pilot")
pilot.tube([(0, -1.35, 0.58), (0, -1.30, 0.74), (0, -1.25, 0.90)], 0.12, "Paint_White", 12)   # torso
pilot.sphere((0, -1.26, 0.93), 0.08, "Paint_White", (1.6, 1.0, 0.7))                   # shoulders
pilot.sphere((0, -1.24, 1.03), 0.105, "Paint_Yellow")                                  # helmet
pilot.sphere((0, -1.32, 1.035), 0.058, "Black", (1.3, 0.7, 0.85))                      # visor
for s in (-1, 1):
    pilot.tube([(s * 0.16, -1.27, 0.90), (s * 0.20, -1.53, 0.84), (s * 0.17, -1.76, 0.86)], 0.037, "Paint_White")
    pilot.sphere((s * 0.17, -1.77, 0.86), 0.034, "Graphite")                             # gloves
    pilot.tube([(s * 0.09, -1.37, 0.56), (s * 0.10, -1.75, 0.66), (s * 0.09, -2.17, 0.52)], 0.054, "Paint_White")
    pilot.sphere((s * 0.09, -2.20, 0.52), 0.048, "Graphite", (1.0, 1.4, 1.0))           # boots
pilot.finish(G["Cockpit_Cell"])

# ================================================================ 3. BODYWORK
# ---- the blunt armoured nose: a two-tone face plate with the lights, a sensor window, the bumper below
bn = body(Y_NOSE)
face = Part("Nose_Front")
face.loft([[Vector((x, y, z)) for x, z in body_loop(Y_NOSE)] for y in (Y_NOSE - SKIN, Y_NOSE)],
          lambda i, j: "Paint_Slate", closed_u=True, cap0="Paint_Slate", cap1="Paint_Slate")
paint(face, lambda c, n: "Paint_Yellow" if c.z > bn["zs"] else "Paint_Slate", [((0, 0, bn["zs"]), (0, 0, 1))])
face.finish(G["Nose"], bevel=0.002, recalc=True, skin=True)
lamps = Part("Nose_Lights")
for s in (-1, 1):
    lamps.cyl((s * 0.32, Y_NOSE - SKIN, 0.71), (s * 0.32, Y_NOSE - SKIN - 0.035, 0.71), 0.07, "Graphite", 20)
    lamps.cyl((s * 0.32, Y_NOSE - SKIN - 0.035, 0.71), (s * 0.32, Y_NOSE - SKIN - 0.038, 0.71), 0.055,
              "Emit_Light", 20)
    lamps.box((s * 0.47, Y_NOSE - SKIN - 0.006, 0.585), (0.10, 0.012, 0.03), "Emit_Amber")      # indicators
lamps.box((0, Y_NOSE - SKIN - 0.008, 0.70), (0.26, 0.016, 0.09), "Black")              # sensor window
lamps.box((0, Y_NOSE - SKIN - 0.006, 0.70), (0.30, 0.012, 0.13), "Graphite")
lamps.finish(G["Nose"])

# ---- the body in three stretches: carapace (top, upper facets, shoulders), slate side walls, chines, belly
for pre, a, b, g in (("Front", Y_NOSE, Y_A, (False, True)), ("Mid", Y_A, Y_B, (True, True)),
                     ("Rear", Y_B, Y_CONE, (True, True))):
    panel(pre + "_Top", 5, 7, a, b, B, carapace_paint, GLASS_CUTS, gap_s=g)
    for side, s in (("R", 1), ("L", -1)):
        def span(t0, t1):
            return (t0, t1) if s > 0 else (12 - t1, 12 - t0)
        panel(pre + "_Upper_" + side, *span(4, 5), a, b, B, carapace_paint, GLASS_CUTS, gap_s=g)
        panel(pre + "_Shoulder_" + side, *span(3, 4), a, b, B, lambda c, n: "Paint_Yellow", gap_s=g)
        panel(pre + "_Side_" + side, *span(2, 3), a, b, B, slate, holes=bag_cuts, gap_s=g)
        panel(pre + "_Chine_" + side, *span(1, 2), a, b, B, slate, gap_s=g)
    panel(pre + "_Belly", 11, 13, a, b, B, lambda c, n: "Graphite", holes=emit_cuts, gap_s=g)
drop(bag_cuts + emit_cuts)

frame = Part("Canopy_Frame")                                     # frame round the flush glass, a strut down the middle
ys = [CAN[0]] + [y for y in BODY_Y if CAN[0] < y < CAN[1]] + [CAN[1]]
lift = Vector((0, 0, 0.006))
for s in (-1, 1):
    frame.tube([facet_point(y, s, 4, 4, 0) + lift for y in ys], 0.012, "Graphite", 8)
for y in CAN:
    frame.tube([facet_point(y, -1, 4, 4, 0) + lift, facet_point(y, -1, 5, 5, 0) + lift,
                facet_point(y, 1, 5, 5, 0) + lift, facet_point(y, 1, 4, 4, 0) + lift], 0.012, "Graphite", 8)
frame.tube([Vector((0, y, body(y)["zt"])) + lift for y in ys], 0.010, "Graphite", 8)
frame.finish(G["Cockpit_Cell"])

# ---- details on the carapace: the roof hatch, grab handles, amber ports in the side walls
det = Part("Hull_Details")
yh = -0.70
zt = body(yh)["zt"]
det.lathe((0, yh, zt - 0.004), (0, yh, zt + 0.012), [(0, 0.27), (1, 0.27), (1, 0.24), (0, 0.24)],
          lambda k: "Graphite", 40, closed=True)                                       # hatch ring
for dx in (-0.10, 0.10):
    det.tube([(dx, yh - 0.07, zt + 0.004), (dx, yh - 0.07, zt + 0.04), (dx, yh + 0.07, zt + 0.04),
              (dx, yh + 0.07, zt + 0.004)], 0.008, "Metal_Bright", 8)                  # handles
for s in (-1, 1):
    for y in (-1.05, -0.55):                                                           # grab handles on the shoulder
        a, c = facet_point(y - 0.10, s, 3, 4, 0.55), facet_point(y + 0.10, s, 3, 4, 0.55)
        n = Vector((s * 0.85, 0, 0.53)).normalized()
        det.tube([a, a + n * 0.035, c + n * 0.035, c], 0.009, "Metal_Bright", 8)
    for y in (-1.20, -0.90, -0.60, -0.30):                                             # amber ports
        w = body(y)["w"]
        det.cyl((s * w, y, 0.70), (s * (w + 0.018), y, 0.70), 0.034, "Graphite", 16)
        det.cyl((s * (w + 0.018), y, 0.70), (s * (w + 0.021), y, 0.70), 0.024, "Emit_Amber", 16)
det.finish(B)

# ---- the tail cone round the engine, then the collar with its lip, a heat shield inside, the shark fin on top
cone, ci = tail_loop(body_loop(Y_CONE), (0, ENG_Z), SH_OUT, Y_CONE, Y_CONE1, power=1.6)
CONE_Y = [Y_CONE + k * (Y_CONE1 - Y_CONE) / 4 for k in range(5)]
nc = len(cone(Y_CONE))
for name, t0, t1, m_fn in (("Tail_Belly", ci[10], nc + ci[2], lambda c, n: "Graphite" if n.z < -0.6 else
                            "Paint_Slate"),
                           ("Tail_Side_R", ci[2], ci[3], slate),
                           ("Tail_Carapace", ci[3], ci[9], lambda c, n: "Paint_Yellow"),
                           ("Tail_Side_L", ci[9], ci[10], slate)):
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
    cl.box((0, Y_END - 0.035, ENG_Z + dz), (0.42, 0.04, 0.006), "Emit_Red")              # tail lights
cl.finish(GE, bevel=0.002, recalc=False, skin=True)
sh = Part("Collar_Bulkhead")                                     # heat shield across the collar, round the bell
ring_in = [loop_at(SEC, k / 48) * 1.06 for k in range(48)]
ring_out = [loop_at(SH_IN, k / 48) * 0.995 for k in range(48)]
sh.loft([[Vector((p.x, y, ENG_Z + p.y)) for p in ring] for ring, y in
         ((ring_out, Y_CONE1 + 0.004), (ring_in, Y_CONE1 + 0.004), (ring_in, Y_CONE1 + 0.016),
          (ring_out, Y_CONE1 + 0.016))], lambda i, j: "Ceramic", closed_u=True, closed_v=True)
sh.finish(GE)


def top_z(y):              # the top of the body, the cone and the collar along the centre line
    if y <= Y_CONE:
        return body(y)["zt"]
    if y < Y_CONE1:
        return cone(y)[ci[6]][1]
    return ENG_Z + SH_HH


fin = Part("Shark_Fin")
shark_fin(fin, top_z, 0.0, (1.15, 3.28), (2.65, 3.42), 0.40, 0.055, "Paint_Slate", "Paint_Yellow")
fin.finish(B, bevel=0.0015, smooth_angle=60, skin=True)

# ================================================================ 4. DECALS (our own marks)
dec = Part("Decals")
yn = 0.55                                                                               # big number on the roof
M = frame_on((0, yn, body(yn)["zt"]), (1, 0, 0), (0, 1, 0), 0.002)
dec.add_mesh(text_mesh("05", 0.46), M, "Black")
yt = -0.65                                                                              # warning on the hatch
tri = [(0, 0.10), (-0.087, -0.05), (0.087, -0.05)]
dec.poly([frame_on((0, yt - 0.24, body(yt)["zt"]), (1, 0, 0), (0, -1, 0), 0.016) @ Vector((x, y, 0))
          for x, y in tri], "Paint_Red")
for s in (-1, 1):
    rd = 1 if s > 0 else -1
    y = -0.45                                                                           # name on the shoulder
    a, b = facet_point(y - 0.05, s, 3, 4, 0.5), facet_point(y + 0.05, s, 3, 4, 0.5)
    v = facet_point(y, s, 3, 4, 1.0) - facet_point(y, s, 3, 4, 0.0)
    dec.add_mesh(text_mesh("BASTION", 0.13), frame_on(facet_point(y, s, 3, 4, 0.5), (b - a) * rd, v, 0.004),
                 "Black")
    yc = 1.40                                                                           # league emblem
    a, b = facet_point(yc - 0.05, s, 3, 4, 0.5), facet_point(yc + 0.05, s, 3, 4, 0.5)
    v = facet_point(yc, s, 3, 4, 1.0) - facet_point(yc, s, 3, 4, 0.0)
    M2 = frame_on(facet_point(yc, s, 3, 4, 0.5), (b - a) * rd, v, 0.004)
    o, i_ = ring2d(0.085, 0.10)
    dec.flat(o, M2, "Black", holes=[i_])
    dec.poly([M2 @ Vector(((0.072 if k % 2 == 0 else 0.018) * math.cos(math.pi / 2 + k * math.pi / 4),
                           (0.072 if k % 2 == 0 else 0.018) * math.sin(math.pi / 2 + k * math.pi / 4), 0))
              for k in range(8)], "Black")
    for y, z, r, wall, _ in BAG_AT:                                                     # airbag warnings
        w = wall(y)
        Mt = frame_on((s * w, y, z + r + 0.10), (0, rd, 0), (0, 0, 1), 0.003)
        dec.poly([Mt @ Vector((x * 0.6, -yy * 0.6, 0)) for x, yy in tri], "Paint_Red")
    v0, v1, z0, z1 = POD_VENT                                                           # hazard stripes ahead
    for k in range(4):                                                                  # of the side vent
        y = v0 - 0.10 - k * 0.055
        Mh = frame_on((s * pod_wall(y), y, (z0 + z1) / 2), (0, rd, 0), (0, 0, 1), 0.003)
        dec.poly([Mh @ Vector(q) for q in ((-0.012, -0.13, 0), (0.016, -0.13, 0), (0.046, 0.13, 0),
                                           (0.018, 0.13, 0))], "Paint_White")
dec.finish(G["Decals"], recalc=False, smooth_angle=10)

# ================================================================ sockets
for name, loc in (("Socket_Reactor", (0, -0.40, 0.70)), ("Socket_Propulsion", (0, EXIT, ENG_Z)),
                  ("Socket_Tail", (0, Y_END, ENG_Z - SH_HH)), ("Socket_Armor_L", (-1.25, -0.60, 0.55)),
                  ("Socket_Armor_R", (1.25, -0.60, 0.55)), ("Socket_Cooling", (0, 1.30, 1.54)),
                  ("Socket_Utility", (0, -3.00, 0.70))):
    group(name, G["Sockets"], loc)

finish_ship(G["Decals"], cockpit=((-1.9, -3.7, 2.3), (0, -1.65, 1.05)), scale=1.1)

# ================================================================ modules (Docs/MODULOS.md): the split for the game and the variants
from ship_modules import build_modules  # noqa: E402
build_modules(globals(), wings=(), palette=("Paint_Slate", "Paint_Yellow", "Paint_Orange"), tail="below", scale=1.15,
              nozzle_r=0.34)
