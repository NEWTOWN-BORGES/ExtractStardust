# VORTEX hover racer (small and fast, burns a lot of fuel and runs hot), built from the inside out like the others:
# structure (truss frames and longerons in the body, cockpit cell, engine saddles, wing spars and clamps), systems
# (cockpit and pilot, reactor and its line, one big round plasma engine, heat radiators, round hover emitters), then
# the 12 mm bodywork panels with 5 mm gaps.
# Look: the body is a long pointed delta (an A seen from above) with a faceted ridge and the cockpit glass flush in
# it, one big round engine at the rear inside an angular housing of dark plates, big swept wings from the rear sides
# with their tips folded up; red-orange and white (Docs/VORTEX_CATEGORIA.md, Docs/NAVES_REGRAS.md).
# Front is -Y, up is +Z, metres (the layout of the old SourceArt/TestShips/vortex.fbx; the game centres the bounds).
# Usage: python3 Scripts/build_vortex.py <out_dir> [--no-render]
#    or: blender -b -P Scripts/build_vortex.py -- <out_dir> [--no-render]
# Writes <out_dir>/vortex.blend, vortex.fbx and the preview renders. Shared parts: Scripts/ship_kit.py.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ship_kit import *  # noqa: E402,F401,F403  (bpy, bmesh, math, Matrix, Vector and the helpers)

start("VORTEX")
material("Paint_Red", "#E2502E", rough=0.3, coat=0.6)
material("Paint_White", "#EEF0F2", rough=0.32, coat=0.5)
material("Paint_Grey", "#C9CDD1", rough=0.4, coat=0.3)
material("Paint_DarkGrey", "#3A3E44", rough=0.45, coat=0.3)
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

ROOT = group("ShipRoot")
G = {n: group(n, ROOT) for n in ("Structural_Core", "Nose", "Cockpit_Cell", "Body", "Reactor", "Propulsion",
                                 "Wing_L", "Wing_R", "Hover", "Cooling", "Decals", "Sockets")}
B = G["Body"]

# ---------------------------------------------------------------- lines
#        y      w     zb    cb    zs    ct    zt       (delta body: thin edges, steep facets up to a ridge)
BODY = [(-3.20, .050, .400, .010, .430, .030, .460),
        (-2.00, .380, .340, .020, .400, .240, .600),
        (-0.80, .660, .300, .030, .370, .440, .860),
        (0.00, .800, .300, .030, .370, .560, .960),
        (0.80, .920, .300, .030, .370, .680, .900),
        (1.60, .950, .320, .030, .380, .700, .700)]
BODY_Y = [r[0] for r in BODY]
Y_TIP, Y_CAP, Y_BACK, Y_END = -3.20, -2.90, 1.60, 2.65
CAN = (-1.20, 0.40)               # canopy (flush glass in the ridge)
ENG_Z, ENG_R = 0.62, 0.28
COWL_OUT = shape_loop(0.40, 0.34, 0.36, 0.05)        # angular housing round the engine
COWL_IN = shape_loop(0.37, 0.31, 0.33, 0.03)


def body(y):
    return dict(zip(("w", "zb", "cb", "zs", "ct", "zt"), table(BODY, y)))


def body_loop(y):
    b = body(y)
    return loop10(0, b["w"], b["zb"], b["cb"], b["zs"], b["ct"], b["zt"])


def truss(y):     # the frames' outline: a trapezoid inside the body (the thin edges stay clear)
    b = body(y)
    return [(0.85 * b["w"], b["zb"]), (b["w"] - b["ct"], b["zt"]), (-(b["w"] - b["ct"]), b["zt"]),
            (-0.85 * b["w"], b["zb"])]


def xyz(y, x, z):
    return Vector((x, y, z))


def body_centre(c):
    return Vector((0, c.y, (body(c.y)["zb"] + body(c.y)["zt"]) / 2))


CUTS = [((0, CAN[0], 0), (0, 1, 0)), ((0, CAN[1], 0), (0, 1, 0)), ((0, 0, 0.70), (0, 0, 1)), ((0, 0, 0.45), (0, 0, 1))]


def body_paint(c, n):
    if n.z < -0.6:
        return "Paint_Grey"
    if CAN[0] < c.y < CAN[1] and c.z > 0.70 and n.z > 0.3:
        return "Glass"
    if abs(n.x) > 0.9 or c.z < 0.45:
        return "Paint_White"                                   # white rim along the delta edges
    return "Paint_Red"


def panel(name, t0, t1, y0, y1, parent, m_fn, cuts=(), holes=(), gap_s=(True, True)):
    p = Part(name)
    surface(p, body_loop, t0, t1, y0, y1, BODY_Y, xyz, gap_s)
    orient_out(p, body_centre)
    paint(p, m_fn, cuts)
    return shell(p, parent, holes)


# ================================================================ 1. STRUCTURE
fr = Part("Frames")
for y in (-2.40, -1.50, -0.95, 0.45, 1.30):
    o, i_ = inset(truss(y), 0.016), inset(truss(y), 0.046)
    fr.loft([[Vector((p.x, y + dy, p.y)) for p in ring] for ring, dy in
             ((o, -0.012), (o, 0.012), (i_, 0.012), (i_, -0.012))], lambda i, j: "Metal", closed_u=True, closed_v=True)
fr.finish(G["Structural_Core"], bevel=0.002)
lon = Part("Longerons")
for k in range(4):
    lon.tube([(inset(truss(y), 0.03)[k].x, y, inset(truss(y), 0.03)[k].y)
              for y in [-2.60] + [s for s in BODY_Y if -2.60 < s < 1.50] + [1.50]], 0.012, "Metal", square=True)
lon.finish(G["Structural_Core"], bevel=0.002)

# ================================================================ 2. SYSTEMS
# ---- one big round plasma engine in an angular housing at the rear
GE = G["Propulsion"]
eng = Part("Engine")
EXIT = space_engine(eng, (0, ENG_Z), 1.68, 2.30, circle_loop(ENG_R, 40))
for y in (1.85, 2.20):                                                                 # saddles on the housing floor
    eng.box((0, y, (ENG_Z - 0.33 + ENG_Z - ENG_R + 0.01) / 2), (0.30, 0.08, 0.33 - ENG_R + 0.01), "Metal")
eng.finish(GE)
cw = Part("Engine_Housing")
cw.loft([[Vector((x, y, ENG_Z + z)) for x, z in sec] for y, sec in
         ((Y_BACK + SKIN, COWL_OUT), (Y_END, COWL_OUT), (Y_END, COWL_IN), (Y_BACK + SKIN, COWL_IN))],
        lambda i, j: "Paint_DarkGrey", closed_u=True, closed_v=True)
bmesh.ops.recalc_face_normals(cw.bm, faces=cw.bm.faces[:])
paint(cw, lambda c, n: ("Metal_Bright" if c.y > Y_END - 0.004 and abs(n.y) > 0.9 else
                        "Graphite" if (c - Vector((0, c.y, ENG_Z))).dot(n) < 0 else "Paint_DarkGrey"))
cw.box((0, Y_END - 0.002, ENG_Z - 0.345), (0.16, 0.004, 0.012), "Emit_Red")              # tail light
cw.finish(GE, bevel=0.002, recalc=False, skin=True)
sm = Part("Housing_Seams")                                                              # bands between the plates
for y in (2.00, 2.42):
    sm.loft([[Vector((x * sc, y + dy, ENG_Z + z * sc)) for x, z in COWL_OUT] for sc, dy in
             ((1.012, -0.012), (1.012, 0.012), (1.0, 0.012), (1.0, -0.012))], lambda i, j: "Metal", closed_u=True,
            closed_v=True)
sm.finish(GE, skin=True)

# ---- reactor behind the cockpit and its line into the engine (through a grommet in the body's rear wall)
rc = Part("Reactor_Core")
rc.lathe((0, 0.50, 0.52), (0, 1.20, 0.52),
         [(0, 0.0), (0.03, 0.08), (0.08, 0.125), (0.18, 0.13), (0.24, 0.12), (0.30, 0.13), (0.70, 0.13),
          (0.76, 0.12), (0.82, 0.13), (0.92, 0.125), (0.97, 0.08), (1, 0.0)],
         lambda k: "Emit_Hot" if k in (3, 4, 7, 8) else "Metal_Bright", 24)
for y in (0.62, 1.08):
    rc.box((0, y, 0.355), (0.24, 0.05, 0.06), "Metal")                                  # saddles
rc.tube([(0, 1.20, 0.52), (0, 1.45, 0.55), (0, 1.59, 0.55), (0, 1.66, 0.58)], 0.016, "Metal", 10)
rc.lathe((0, Y_BACK - 0.005, 0.55), (0, Y_BACK + SKIN + 0.005, 0.55), [(0, 0.02), (0, 0.03), (1, 0.03), (1, 0.02)],
         lambda k: "Graphite", 12, closed=True)
rc.finish(G["Reactor"])

# ---- heat: radiators under louvred vents in the upper facets behind the cockpit
cool = Part("Radiators")
vent_cuts = []
for s in (-1, 1):
    b = body(0.85)
    cool.box((s * 0.60, 0.85, 0.46), (0.20, 0.62, 0.10), "Black")
    for x in (0.55, 0.60, 0.65):
        z = b["zs"] + (b["w"] - x) / b["ct"] * (b["zt"] - b["zs"]) - 0.02
        cool.box((s * x, 0.85, z), (0.02, 0.58, 0.006), "Graphite")
    vent_cuts.append(box_cutter((s * 0.60, 0.85, 0.615), (0.20, 0.60, 0.33)))
cool.finish(G["Cooling"])

# ---- hover: round emitters (grav-caps) in cut-outs of the belly
hover = Part("Hover_Emitters")
emit_cuts = []
for y, x, r in [(-2.00, 0.0, 0.12)] + [(y, s * x, r) for y, x, r in ((-0.70, 0.32, 0.14), (0.70, 0.45, 0.15))
                                       for s in (-1, 1)] + [(1.45, 0.0, 0.12)]:
    zb = body(y)["zb"]
    hover.lathe((x, y, zb + 0.03), (x, y, zb - 0.035), [(0, r), (1, r), (1, r - 0.025), (0, r - 0.025)],
                lambda k: "Graphite", 32, closed=True)                                   # housing ring
    hover.cyl((x, y, zb - 0.025), (x, y, zb - 0.029), r - 0.025, "Emit_Hover", 32)        # emitter face
    hover.cyl((x, y, zb - 0.02), (x, y, zb - 0.034), 0.035, "Metal", 16)                  # hub
    hover.cyl((x, y, zb + 0.03), (x, y, zb + 0.01), r - 0.02, "Metal", 32)                # back plate
    c = Part("cut")
    c.cyl((x, y, zb - 0.05), (x, y, zb + 0.05), r + GAP / 2, "Black", 32)
    emit_cuts.append(cutter(c))
hover.finish(G["Hover"])

# ---- cockpit: floor, dash, controls, seat and pilot (reclined, the head under the ridge glass)
ck = Part("Cockpit_Parts")
ck.box((0, -0.43, 0.34), (0.50, 0.94, 0.012), "Graphite")                               # floor
ck.box((0, -0.75, 0.66), (0.40, 0.14, 0.08), "Graphite")                                # dash
ck.box((0, -0.679, 0.68), (0.26, 0.004, 0.045), "Emit_Hover")                           # display
ck.cyl((0, -0.68, 0.64), (0, -0.34, 0.62), 0.015, "Metal", 10)                          # column
ck.box((0, -0.33, 0.62), (0.24, 0.026, 0.026), "Metal")                                 # handlebar
for s in (-1, 1):
    ck.cyl((s * 0.11, -0.33, 0.62), (s * 0.16, -0.33, 0.62), 0.018, "Graphite", 10)
ck.box((0, 0.12, 0.38), (0.34, 0.24, 0.05), "Graphite")                                 # seat
back = Matrix.Rotation(math.radians(-28), 3, 'X')
ck.box((0, 0.30, 0.56), (0.34, 0.045, 0.34), "Graphite", back)                          # back rest
ck.finish(G["Cockpit_Cell"], bevel=0.003)
pilot = Part("Pilot")
pilot.tube([(0, 0.05, 0.46), (0, 0.14, 0.58), (0, 0.22, 0.70)], 0.10, "Paint_White", 12)   # torso
pilot.sphere((0, 0.21, 0.72), 0.068, "Paint_White", (1.6, 1.0, 0.7))                    # shoulders
pilot.sphere((0, 0.25, 0.80), 0.09, "Paint_Red")                                        # helmet
pilot.sphere((0, 0.18, 0.805), 0.05, "Black", (1.3, 0.7, 0.85))                          # visor
for s in (-1, 1):
    pilot.tube([(s * 0.12, 0.21, 0.70), (s * 0.15, -0.05, 0.60), (s * 0.12, -0.33, 0.62)], 0.032, "Paint_White")
    pilot.sphere((s * 0.125, -0.34, 0.62), 0.03, "Graphite")                              # gloves
    pilot.tube([(s * 0.07, 0.04, 0.44), (s * 0.08, -0.40, 0.52), (s * 0.07, -0.85, 0.50)], 0.044, "Paint_White")
    pilot.sphere((s * 0.07, -0.88, 0.50), 0.04, "Graphite", (1.0, 1.4, 1.0))              # boots
pilot.finish(G["Cockpit_Cell"])

# ================================================================ 3. WINGS (big, swept, tips folded up)
WING = [(0.70, 0.40, 1.60), (1.62, 1.72, 2.18)]   # x, leading edge y, trailing edge y


def wing_at(x):
    le, te = table(WING, x)
    f = (x - 0.70) / 0.92
    return le, te, 0.36 - 0.04 * f, 0.07 - 0.03 * f


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
    p0, p1 = wing_at(0.70), wing_at(1.60)
    for f in (0.40, 0.85):
        a = (0.68, p0[0] + f * (p0[1] - p0[0]), p0[2])
        b = (1.60, p1[0] + f * (p1[1] - p1[0]), p1[2])
        spar.tube([(s * a[0], a[1], a[2]), (s * b[0], b[1], b[2])], 0.018 if f < 0.5 else 0.013, "Metal",
                  square=True)
        spar.box((s * 0.70, a[1], p0[2]), (0.06, 0.10, 0.08), "Metal")                  # root clamps
    for x in (1.00, 1.30, 1.58):
        L = inset(wing_loop(x), 0.010)
        spar.loft([[Vector((s * (x + d), q.x, q.y)) for q in L] for d in (-0.005, 0.005)], lambda i, j: "Metal",
                  closed_u=True, cap0="Metal", cap1="Metal")
    spar.finish(gw, bevel=0.002)

    def skin(name, t0, t1, m_fn, cuts=()):
        p = Part(name + "_" + side)
        surface(p, wing_loop, t0, t1, 0.70, 1.62, [r[0] for r in WING], w3d, (False, False))
        orient_out(p, w_centre)
        paint(p, m_fn, cuts)
        return shell(p, gw, thick=0.006, bevel=0.0015)

    skin("Wing_Top", 2, 3, lambda c, n: "Paint_Red" if abs(c.x) > 1.40 else "Paint_White",
         [((1.40, 0, 0), (1, 0, 0)), ((-1.40, 0, 0), (1, 0, 0))])
    skin("Wing_Bottom", 6, 7, lambda c, n: "Paint_Grey")
    skin("Wing_TE", 3, 6, lambda c, n: "Paint_DarkGrey")
    skin("Wing_LE", 7, 10, lambda c, n: "Paint_DarkGrey")
    tip = Part("Wing_Tip_" + side)
    L = wing_loop(1.62 - GAP / 2)
    tip.loft([[Vector((s * (1.62 - GAP / 2 - d), q[0], q[1])) for q in L] for d in (0, 0.01)],
             lambda i, j: "Paint_DarkGrey", closed_u=True, cap0="Paint_DarkGrey", cap1="Paint_DarkGrey")
    tip.finish(gw, bevel=0.002, skin=True)
    fold = Part("Wing_Fold_" + side)                                                     # the tip folded up
    shark_fin(fold, lambda y: wing_top(1.58), s * 1.58, (1.74, 2.18), (1.98, 2.22), 0.36, 0.035, "Paint_Red",
              "Paint_White", math.radians(12), s)
    fold.finish(gw, bevel=0.0015, smooth_angle=60, skin=True)

slots = []
for s in (-1, 1):
    p = Part("cut")
    p.loft([[Vector((s * x, a, b)) for a, b in wing_loop(x, GAP / 2)] for x in (0.66, 1.02)], lambda i, j: "Black",
           closed_u=True, cap0="Black", cap1="Black")
    slots.append(cutter(p))

# ================================================================ 4. BODYWORK
cap = Part("Nose_Cap")
rows = surface(cap, body_loop, 0, 10, Y_TIP, Y_CAP, BODY_Y, xyz, (False, True), wrap=True)
cap.poly(rows[0][::-1], "Paint_White")
orient_out(cap, lambda c: Vector((0, -2.80, 0.45)))
paint(cap, lambda c, n: "Paint_Grey" if n.z < -0.6 else "Paint_White")
shell(cap, G["Nose"])
panel("Body_Top", 4, 6, Y_CAP, Y_BACK, B, body_paint, CUTS)
for side, s in (("R", 1), ("L", -1)):
    def span(a, b):
        return (a, b) if s > 0 else (10 - b, 10 - a)
    panel("Body_Facet_" + side, *span(3, 4), Y_CAP, Y_BACK, B, body_paint, CUTS, slots + vent_cuts)
    panel("Body_Edge_" + side, *span(2, 3), Y_CAP, Y_BACK, B, body_paint, (), slots)
    panel("Body_Chine_" + side, *span(1, 2), Y_CAP, Y_BACK, B, lambda c, n: "Paint_Grey", (), slots)
panel("Body_Belly", 9, 11, Y_CAP, Y_BACK, B, lambda c, n: "Paint_Grey", (), emit_cuts)
c = Part("cut")
c.cyl((0, Y_BACK - 0.05, 0.55), (0, Y_BACK + 0.05, 0.55), 0.03, "Black", 12)
gc = cutter(c)
rear = Part("Body_Rear")
rear.loft([[Vector((x, y, z)) for x, z in body_loop(Y_BACK)] for y in (Y_BACK, Y_BACK + SKIN)],
          lambda i, j: "Paint_DarkGrey", closed_u=True, cap0="Paint_DarkGrey", cap1="Paint_DarkGrey")
ob = rear.finish(B, skin=True)
boolean(ob, [gc])
shade(ob, 0.002)
drop(slots + vent_cuts + emit_cuts + [gc])

frame = Part("Canopy_Frame")                                                            # frame round the flush glass
ys = [CAN[0]] + [y for y in BODY_Y if CAN[0] < y < CAN[1]] + [CAN[1]]


def ridge(y, side):          # where the 0.70 m line crosses the facet, on one side
    b = body(y)
    x = b["w"] - (0.70 - b["zs"]) / (b["zt"] - b["zs"]) * b["ct"]
    return Vector((side * x, y, 0.70 + 0.004))


for sd in (-1, 1):
    frame.tube([ridge(y, sd) for y in ys], 0.009, "Graphite", 8)
for y in (CAN[0], -0.40, CAN[1]):
    b = body(y)
    pts = [ridge(y, -1), Vector((-(b["w"] - b["ct"]), y, b["zt"] + 0.004)),
           Vector((b["w"] - b["ct"], y, b["zt"] + 0.004)), ridge(y, 1)]
    frame.tube(pts, 0.009, "Graphite", 8)
frame.finish(G["Cockpit_Cell"])

# ================================================================ 5. DECALS (our own marks)
dec = Part("Decals")
for s in (-1, 1):
    rd = 1 if s > 0 else -1
    u = Vector((0, rd, 0))
    v = Vector((-s * 0.06, 0, 0.72))
    xs = s * 0.372
    dec.flat(disc2d(0.10), frame_on((xs, 1.82, ENG_Z), u, v, 0.006), "Paint_White")
    dec.add_mesh(text_mesh("11", 0.12), frame_on((xs, 1.82, ENG_Z), u, v, 0.009), "Black")
    dec.add_mesh(text_mesh("VORTEX", 0.09), frame_on((xs, 2.32, ENG_Z), u, v, 0.006), "Paint_White")
    xc, yc = 1.18, 1.62
    d = (wing_top(xc + 0.05) - wing_top(xc - 0.05)) / 0.1
    M = frame_on((s * xc, yc, wing_top(xc) + 0.0005), (s, 0, d), (0, s, 0))
    o, i_ = ring2d(0.10, 0.12)
    dec.flat(o, M, "Paint_DarkGrey", holes=[i_])
    dec.poly([M @ Vector(((0.085 if k % 2 == 0 else 0.022) * math.cos(math.pi / 2 + k * math.pi / 4),
                          (0.085 if k % 2 == 0 else 0.022) * math.sin(math.pi / 2 + k * math.pi / 4), 0))
              for k in range(8)], "Paint_DarkGrey")
dec.finish(G["Decals"], recalc=False, smooth_angle=10)

# ================================================================ sockets
for name, loc in (("Socket_Reactor", (0, 0.85, 0.52)), ("Socket_Propulsion", (0, EXIT, ENG_Z)),
                  ("Socket_Wing_L", (-0.70, 1.00, 0.36)), ("Socket_Wing_R", (0.70, 1.00, 0.36)),
                  ("Socket_Tail", (0, Y_END, ENG_Z - 0.36)), ("Socket_Armor_L", (-0.66, -0.80, 0.50)),
                  ("Socket_Armor_R", (0.66, -0.80, 0.50)), ("Socket_Cooling", (0, 0.85, 0.62)),
                  ("Socket_Utility", (0, -3.20, 0.43))):
    group(name, G["Sockets"], loc)

finish_ship(G["Decals"], cockpit=((-1.4, -1.7, 1.5), (0, -0.2, 0.72)))
