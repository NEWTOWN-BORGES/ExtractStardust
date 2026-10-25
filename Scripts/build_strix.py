# STRIX hover racer, built from the inside out: structure first (frames, longerons, spine rails, crash box, reactor
# cradle, engine and wing mounts), then the systems on it (cockpit cell and pilot, reactor, the engine, cooling,
# hover emitters, sensors), then the bodywork panels that close over them. Every part is its own object and fits the
# one under it: panels are 12 mm shells with 5 mm gaps, the wings go through slots in the side panels onto root
# clamps, the emitters sit in cut-outs of the belly, the side intakes are ducted to the engine.
# Look: long faceted nose that is narrow and low at the front, cockpit set back, a raised spine over the reactor,
# two plasma engines one above the other at the centre rear, inside a shroud that runs down to the base (wider at
# the bottom, narrowing upwards), a long dorsal shark fin, swept wings on the last third going down
# (Docs/STRIX_CATEGORIA.md).
# Front is -Y, up is +Z, metres (the layout of the old SourceArt/TestShips/strix.fbx; the game centres the bounds).
# Usage: python3 Scripts/build_strix.py <out_dir> [--no-render]
#    or: blender -b -P Scripts/build_strix.py -- <out_dir> [--no-render]
# Writes <out_dir>/strix.blend, strix.fbx and the preview renders. Shared parts: Scripts/ship_kit.py.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ship_kit import *  # noqa: E402,F401,F403  (bpy, bmesh, math, Matrix, Vector and the helpers)

start("STRIX")
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
material("Emit_Plasma", "#8FDFFF", emit=10.0, rough=0.3)


ROOT = group("ShipRoot")
G = {n: group(n, ROOT) for n in ("Structural_Core", "Nose", "Cockpit_Cell", "Body", "Reactor", "Propulsion",
                                 "Wing_L", "Wing_R", "Hover", "Cooling", "Decals", "Sockets")}


# ---------------------------------------------------------------- hull lines


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
Y_CONE, Y_CONE1, Y_END = 2.30, 2.55, 3.12   # body outline -> shroud round the engines -> end of the shroud


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


def tx(y, x):   # t on the hull deck (segment 4-5, right side) where the deck is at half width x
    wt = hull(y)["wt"]
    return 4 + (wt - x) / wt


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


def octagon(y):
    L = hull_loop(y)
    return [L[i] for i in (1, 2, 3, 4, 6, 7, 8, 9)]


struct = Part("Frames")
FRAME_Y = [-2.40, -1.60, -0.73, 0.29, 1.20, 2.00, 2.20]
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
    path = [(s * 0.17, y, hull(y)["zb"] + SKIN + CLEAR + 0.03) for y in (-2.45, -0.75, 0.30, 1.20, 2.20)]
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
# ---- two plasma engines one above the other at the centre rear: the upper one in the spine (fed with cooling air by
# the side intakes), the lower one in the hull; both narrow upwards like the shroud round them
SH_Z, SH_HH = 0.7725, 0.4725                       # shroud: centre and half height (base at the hull bottom)
SH_OUT = shape_loop(0.54, 0.26, SH_HH, 0.10)        # wider at the base, narrowing upwards
SH_IN = shape_loop(0.51, 0.23, SH_HH - 0.03, 0.07)
UP_Z, UP_SEC = 0.98, shape_loop(0.28, 0.21, 0.16, 0.06)
LO_Z, LO_SEC = 0.54, shape_loop(0.38, 0.32, 0.17, 0.06)
EY1 = 2.78                          # end of both casings, inside the shroud
INTAKE = (1.28, 1.66)               # y range of the side intakes
GE = G["Propulsion"]
eng = Part("Engine_Upper")
EXIT = space_engine(eng, (0, UP_Z), 1.72, EY1, UP_SEC)
eng.box((0, 1.95, (hull(1.95)["zt"] + UP_Z - 0.16 + 0.012) / 2), (0.30, 0.10, UP_Z - 0.16 + 0.012 - hull(1.95)["zt"]),
        "Metal")                                                                       # saddle on the frames
eng.box((0, 2.45, (LO_Z + 0.17 + UP_Z - 0.16) / 2), (0.24, 0.10, UP_Z - 0.16 - LO_Z - 0.17 + 0.02), "Metal")
eng.finish(GE, bevel=0.0)                                                              # (stands on the lower one)
eng = Part("Engine_Lower")
space_engine(eng, (0, LO_Z), 2.30, EY1, LO_SEC)
for y in (2.42, 2.66):                                                                 # saddles on the shroud floor
    zb = SH_Z - SH_HH + 0.03
    eng.box((0, y, (zb + LO_Z - 0.17 + 0.01) / 2), (0.40, 0.08, LO_Z - 0.17 + 0.01 - zb), "Metal")
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
    pipes.tube([(s * 0.05, 1.41, 0.95), (s * 0.07, 1.52, 1.05), (s * 0.08, 1.66, 1.10), (s * 0.08, 1.80, 1.10)],
               0.014, "Metal", 10)
pipes.tube([(0, 1.41, 0.84), (0, 1.95, 0.76), (0, 2.16, 0.76), (0, 2.27, 0.60)], 0.014, "Metal", 10)  # lower engine
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
for y, x in ((-2.85, 0.10), (2.22, 0.40)):                                             # surface sensors
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


WING_X = [0.44, 1.38, 1.50]
for s, side in ((1, "R"), (-1, "L")):
    gw = G["Wing_" + side]

    def w3d(x, y, z, s=s):
        return Vector((s * x, y, z))

    def w_centre(c, s=s):
        le, te, mid, th = wing_at(abs(c.x))
        return Vector((c.x, (le + te) / 2, mid))

    spar = Part("Wing_Structure_" + side)
    p0, p1 = wing_at(0.40), wing_at(1.46)
    for f in (0.45, 0.85):                                                              # main and rear spar
        a = (0.38, p0[0] + f * (p0[1] - p0[0]), p0[2])
        b = (1.46, p1[0] + f * (p1[1] - p1[0]), p1[2])
        spar.tube([(s * a[0], a[1], a[2]), (s * b[0], b[1], b[2])], 0.022 if f < 0.5 else 0.015, "Metal",
                  square=True)
    for x in (0.55, 0.95, 1.35):                                                        # ribs
        L = inset(wing_loop(x), 0.012)
        spar.loft([[Vector((s * (x + d), p.x, p.y)) for p in L] for d in (-0.006, 0.006)], lambda i, j: "Metal",
                  closed_u=True, cap0="Metal", cap1="Metal")
    zr = wing_at(0.40)[2]
    for y in (0.94, 2.15):                                                              # root clamps on the hull
        spar.box((s * 0.40, y, zr), (0.07, 0.12, 0.10), "Metal")
        spar.box((s * 0.34, y, zr), (0.08, 0.04, 0.04), "Metal")
    spar.finish(gw, bevel=0.002)

    def skin(name, t0, t1, m_fn):
        p = Part(name + "_" + side)
        surface(p, wing_loop, t0, t1, 0.44, 1.50, WING_X, w3d, (False, False))
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
hull_panel("Belly_Rear", 9, 11, 1.20, Y_CONE, B, lambda c, n: "Graphite", holes=emit_cuts)
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
    hull_panel("Chine_" + side, *span(1, 2), -2.75, Y_CONE, B, lambda c, n: "Metal")
    hull_panel("Cockpit_Side_" + side, *span(2, 3), -0.75, 0.30, B, hull_paint(), holes=slots)
    hull_panel("Cowl_" + side, *span(3, lambda y: tx(y, 0.26)), -0.75, 0.30, B, hull_paint())
    hull_panel("Side_" + side, *span(2, 3), 0.30, Y_CONE, B, hull_paint(), holes=slots + vent_cuts)
    hull_panel("Deck_" + side, *span(3, lambda y: tx(y, hump(min(y, 2.75))["hb"] + 0.005)), 0.30, Y_CONE, B,
               hull_paint())
drop(vent_cuts + emit_cuts)

# ---- the hull and the spine run into the shroud round the two engines; the shroud keeps the base line to the end
def tail_outline(y):
    h, p = hull(y), hump(y)
    right = [(h["w"] - h["cb"], h["zb"]), (h["w"], h["zb"] + h["cb"]), (h["w"], h["zs"]), (h["wt"], h["zt"]),
             (p["hb"], h["zt"]), (p["hb"], p["hs"]), (p["ht"], p["htop"])]
    return [(0, h["zb"])] + right + [(0, p["htop"])] + [(-x, z) for x, z in reversed(right)]


cone, ci = tail_loop(tail_outline(Y_CONE), (0, SH_Z), SH_OUT, Y_CONE, Y_CONE1, power=1.6)
CONE_Y = [Y_CONE + k * (Y_CONE1 - Y_CONE) / 4 for k in range(5)]
nc = len(cone(Y_CONE))
for name, t0, t1, m_fn in (("Tail_Belly", ci[14], nc + ci[2], lambda c, n: "Graphite"),
                           ("Tail_Side_R", ci[2], ci[6], hull_paint()),
                           ("Tail_Top", ci[6], ci[10], lambda c, n: "Paint_Yellow"),
                           ("Tail_Side_L", ci[10], ci[14], hull_paint())):
    p = Part(name)
    surface(p, cone, t0, t1, Y_CONE, Y_CONE1, CONE_Y, hull3d, (True, False))
    orient_out(p, lambda c: Vector((0, c.y, SH_Z)))
    paint(p, m_fn)
    shell(p, B, slots if "Side" in name else ())


def shroud_paint(c, n):
    if c.y > Y_END - 0.004 and abs(n.y) > 0.9:
        return "Metal_Bright"                                  # lip at the exit
    if (c - Vector((0, c.y, SH_Z))).dot(n) < 0:
        return "Graphite"                                      # inside
    if c.y > Y_END - 0.08:
        return "Paint_DarkBlue"                                # band at the exit
    return "Paint_Yellow" if n.z > 0.6 else "Graphite" if n.z < -0.6 else "Paint_Blue"


sh = Part("Engine_Shroud")
sh.loft([[Vector((x, y, SH_Z + z)) for x, z in sec] for y, sec in
         ((Y_CONE1, SH_OUT), (Y_END, SH_OUT), (Y_END, SH_IN), (Y_CONE1, SH_IN))],
        lambda i, j: "Paint_Blue", closed_u=True, closed_v=True)
bmesh.ops.recalc_face_normals(sh.bm, faces=sh.bm.faces[:])
paint(sh, shroud_paint, [((0, Y_END - 0.08, 0), (0, 1, 0))])
sh.box((0, Y_END + 0.002, SH_Z - SH_HH + 0.015), (0.16, 0.004, 0.012), "Emit_Red")       # tail light
ob = sh.finish(B, bevel=0.002, recalc=False, skin=True)
boolean(ob, slots)
shade(ob, 0.002)
drop(slots)

# heat shield across the inside of the shroud, the engines through it
bh = Part("Shroud_Bulkhead")
bh.loft([[Vector((x, y, SH_Z + z)) for x, z in SH_IN] for y in (EY1 - 0.006, EY1 + 0.006)], lambda i, j: "Ceramic",
        closed_u=True, cap0="Ceramic", cap1="Ceramic")
ob = bh.finish(B)
holes = []
for z, sec in ((UP_Z, UP_SEC), (LO_Z, LO_SEC)):
    c = Part("cut")
    c.sweep((0, z), EY1 - 0.05, EY1 + 0.05, [(0, 1.04), (1, 1.04)], sec, lambda k: "Black", cap0="Black", cap1="Black")
    holes.append(cutter(c))
boolean(ob, holes)
drop(holes)
shade(ob, 0.002)

# ---- the spine over the reactor: yellow top with the reactor cover, sides with service hatch, end caps
H = G["Reactor"]


def hump_panel(name, t0, t1, m_fn, holes=()):
    p = Part(name)
    surface(p, hump_loop, t0, t1, 0.30, Y_CONE, HUMP_Y, hull3d)
    orient_out(p, hump_centre)
    paint(p, m_fn)
    return shell(p, B, holes)


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
L = hump_loop(0.30 + GAP / 2)
cap = Part("Spine_Front")
ring = [Vector((x, 0.30 + GAP / 2, z)) for x, z in L]
cap.loft([ring, [p + Vector((0, SKIN, 0)) for p in ring]], lambda i, j: "Graphite", closed_u=True, cap0="Graphite",
         cap1="Graphite")
cap.finish(B, bevel=0.002, skin=True)

# ---- long dorsal shark fin on the spine and the tail cone, its tip over the engine coils
fin = Part("Dorsal_Fin")
shark_fin(fin, lambda y: hump(y)["htop"] if y <= Y_CONE else SH_Z + SH_HH, 0.0, (1.62, 2.90), (2.50, 3.08),
          0.24, 0.036, "Paint_Yellow", "Paint_DarkBlue")
fin.finish(B, bevel=0.0015, smooth_angle=60, skin=True)

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
for name, loc in (("Socket_Engine", (0, 2.20, SH_Z)), ("Socket_Reactor", (0, 1.06, 0.90)),
                  ("Socket_Propulsion_Upper", (0, EXIT, UP_Z)), ("Socket_Propulsion_Lower", (0, EXIT, LO_Z)),
                  ("Socket_Wing_L", (-0.40, 0.94, wing_at(0.40)[2])), ("Socket_Wing_R", (0.40, 0.94, wing_at(0.40)[2])),
                  ("Socket_Tail", (0, Y_END, SH_Z - SH_HH)), ("Socket_Armor_L", (-0.56, 0.30, 0.45)),
                  ("Socket_Armor_R", (0.56, 0.30, 0.45)), ("Socket_Cooling", (0, 0.85, 0.52)),
                  ("Socket_Utility", (0, -2.40, 0.30))):
    group(name, G["Sockets"], loc)

finish_ship(G["Decals"])

# ================================================================ modules (Docs/MODULOS.md): the split for the game and the variants
from ship_modules import build_modules  # noqa: E402
build_modules(globals(), wings=("blade", "longspan", "vector"), palette=("Paint_Blue", "Paint_Yellow", "Paint_DarkBlue"),
              tail="below", scale=1.0, nozzle_r=0.16)
