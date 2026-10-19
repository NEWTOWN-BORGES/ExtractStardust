# Side-by-side, same scale: our 10 x 8 km world and the Phase 2c S01 map (6.05 km square, ported from
# Source/ExtractingStardust/Private/World/EXDesertTerrain.cpp; value noise stands in for Unreal's Perlin, and the
# sculpted mesas / arch / island are drawn as flat-topped blocks of the size the builder gives them).
# blender -b -P compare_maps.py -- <dir with world_height16.png + canyon_field.json> [topo]
import bpy, numpy as np, json, sys, math

CMP = sys.argv[sys.argv.index("--") + 1:][0]
P = 8.0  # metres per pixel in the top view

# ---------------- our world ----------------
js = json.load(open(f"{CMP}/canyon_field.json"))
zlo, zhi = js["z_m"]
img = bpy.data.images.load(f"{CMP}/world_height16.png")
img.colorspace_settings.name = "Non-Color"
w, h = img.size
px = np.empty(w * h * 4, np.float32)
img.pixels.foreach_get(px)
step = int(round(P / js["cell_m"]))
OURS = (zlo + px.reshape(h, w, 4)[:, :, 0] * (zhi - zlo))[::step, ::step]  # row 0 = south
circ = np.array(js["circuit"]["points"], float)[:, :2]

# ---------------- Phase 2c terrain (port) ----------------
def _hash(ix, iy):
    n = (ix * 374761393 + iy * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 32767.5 - 1.0

def noise(x, y):
    x, y = np.broadcast_arrays(np.asarray(x, np.float64), np.asarray(y, np.float64))
    fx, fy = np.floor(x), np.floor(y)
    ix, iy = fx.astype(np.int64), fy.astype(np.int64)
    u, v = x - fx, y - fy
    u, v = u * u * (3 - 2 * u), v * v * (3 - 2 * v)
    a, b, c, d = _hash(ix, iy), _hash(ix + 1, iy), _hash(ix, iy + 1), _hash(ix + 1, iy + 1)
    return 0.7 * (a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v)

def fbm(x, y, octaves):
    s, amp, f = 0.0, 0.5, 1.0
    for o in range(octaves):
        s = s + amp * noise(np.asarray(x) * f + o * 17.13, np.asarray(y) * f - o * 9.71)
        f *= 2.03
        amp *= 0.5
    return s

def Step(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)

def spline(keys):
    keys = [np.array(k, float) for k in keys]
    n, out = len(keys), []
    for k in range(n - 1):
        p0, p1, p2, p3 = keys[max(k - 1, 0)], keys[k], keys[k + 1], keys[min(k + 2, n - 1)]
        steps = max(2, math.ceil(np.linalg.norm(p2 - p1) / 5.0))
        for s in range(steps):
            t = s / steps
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(keys[-1])
    return np.array(out)

def nearest(X, Y, pts):
    xf, yf = X.ravel(), Y.ravel()
    dist, idx = np.empty(xf.size), np.empty(xf.size, np.int64)
    for i in range(0, xf.size, 20000):
        d2 = (xf[i:i + 20000, None] - pts[None, :, 0]) ** 2 + (yf[i:i + 20000, None] - pts[None, :, 1]) ** 2
        j = d2.argmin(1)
        idx[i:i + 20000] = j
        dist[i:i + 20000] = np.sqrt(d2[np.arange(j.size), j])
    return dist.reshape(X.shape), idx.reshape(X.shape)

HALF = 3025.0
BASIN, FORK, BOWL = np.array([-1850.0, -1400.0]), np.array([-250.0, -760.0]), np.array([600.0, -420.0])
APPROACH = [(-2150, -1400), (-1800, -1400), (-1400, -1340), (-1000, -1200), (-600, -1000), (-250, -760)]
CANYON = [((600, -420), 60, -3), ((900, -430), 30, -6), ((1250, -380), 24, -20), ((1600, -420), 20, -45),
          ((1950, -520), 26, -60), ((2250, -600), 14, -62)]
DOMES = [((-1950, -1060), 110, 24), ((-1640, -990), 90, 18), ((-1980, -1760), 120, 28), ((-1560, -1740), 95, 20),
         ((-1150, -1520), 80, 16), ((-820, -1390), 70, 14)]
ARCH, ISLAND = ((-700, -350), 130, 70), ((175, -590), 80, 95)
BOUNDARY = [((-2250, 2050), 300, 140), ((-1250, 1950), 260, 120), ((-250, 2050), 320, 150), ((800, 1950), 280, 130),
            ((1850, 2050), 300, 140), ((2700, 1300), 280, 130), ((2700, 200), 300, 140), ((2750, -1250), 280, 130)]

def branch(off):
    d = (BOWL - FORK) / np.linalg.norm(BOWL - FORK)
    left = np.array([-d[1], d[0]])
    return [FORK + (BOWL - FORK) * (i / 6) + left * off * math.sin(math.pi * i / 6) for i in range(7)]

approach, safe_b, racing_b = spline(APPROACH), spline(branch(200.0)), spline(branch(-130.0))
canyon = spline([k[0] for k in CANYON])
exit_ = spline([k[0] for k in CANYON[:5]])
racing, safe = np.vstack([approach, racing_b, exit_]), np.vstack([approach, safe_b, exit_])

def bench(X, Y):
    return 1.2 * fbm(X / 450, Y / 450, 4) + 0.4 * fbm(X / 90, Y / 90, 3)

def theirs(X, Y):
    base = bench(X, Y)
    H = base.copy()
    for (cx, cy), r, hh in DOMES:
        t = np.hypot(X - cx, Y - cy) / r
        H = np.maximum(H, np.where(t < 1, base + hh * np.clip(1 - t * t, 0, 1) ** 1.5, H))
    for (cx, cy), r, hh in [ARCH, ISLAND] + BOUNDARY:
        H = np.maximum(H, base + Step(1.35, 0.75, np.hypot(X - cx, Y - cy) / r) * 0.18 * hh)
    north = Step(1550, 1800, Y + 120 * fbm(X / 600, 0.3, 3))
    east = Step(2450, 2700, X + 120 * fbm(0.7, Y / 600, 3))
    H = np.maximum(H, np.maximum(north, east) * (110 + 10 * fbm(X / 300, Y / 300, 3)))
    mask = np.maximum(Step(-2200, -2550, X + 80 * fbm(0.1, Y / 400, 3)), Step(-2100, -2450, Y + 80 * fbm(X / 400, 0.9, 3)))
    ph = (X * 0.7 + Y * 0.7) / 120 + fbm(X / 300, Y / 300, 3) * 1.2
    p = ph - np.floor(ph)
    prof = np.where(p < 0.78, (p / 0.78) ** 1.6, (1 - (p - 0.78) / 0.22) ** 2)
    H = H + mask * (8 + 14 * mask) * prof * (1.0 + 0.25 * fbm(X / 220, Y / 220, 2))
    edge = np.maximum(np.abs(X), np.abs(Y)) - 2750
    H = H + np.where(edge > 0, (np.maximum(edge, 0) / 274) ** 1.6 * 90, 0)
    b = np.sqrt(((X - BASIN[0]) / 480) ** 2 + ((Y - BASIN[1]) / 280) ** 2)
    H = H - 6 * Step(1.0, 0.55, b) - 5 * Step(75, 15, np.hypot(X - BOWL[0], Y - BOWL[1]))
    d, _ = nearest(X, Y, approach)
    H = H - 1.5 * Step(28, 16, d)
    d, _ = nearest(X, Y, safe_b)
    H = H - 2.5 * Step(24, 12, d)
    # Canyon head cut through the bench.
    along = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(canyon, axis=0), axis=1))])
    kal = np.concatenate([[0], np.cumsum([np.linalg.norm(np.subtract(CANYON[k][0], CANYON[k - 1][0])) for k in range(1, len(CANYON))])])
    s = along / (along[-1] / kal[-1])
    key = np.clip(np.searchsorted(kal, s, side="right") - 1, 0, len(CANYON) - 2)
    t = Step(kal[key], kal[key + 1], s)
    hw = np.array([CANYON[k][1] for k in key]) * (1 - t) + np.array([CANYON[k + 1][1] for k in key]) * t
    fl = np.array([CANYON[k][2] for k in key]) * (1 - t) + np.array([CANYON[k + 1][2] for k in key]) * t
    d, j = nearest(X, Y, canyon)
    half, floor = hw[j], fl[j] + 0.3 * fbm(X / 40, Y / 40, 2)
    ww = 6 + 0.4 * np.maximum(0, H - floor)
    H = np.where(d < half, np.minimum(H, floor),
                 np.where(d < half + ww, np.minimum(H, floor + (H - floor) * Step(half, half + ww, d)), H))
    # Sculpted meshes on top: boundary mesas, arch mesa, island butte (footprint radius, top at ground + height).
    for (cx, cy), r, hh in BOUNDARY + [ARCH, ISLAND]:
        rr = r * (1 + 0.08 * fbm(X / 60 + cx, Y / 60 + cy, 2))
        top = float(theirs_ground_at(cx, cy)) + hh
        H = np.maximum(H, np.where(np.hypot(X - cx, Y - cy) < rr * 0.97, top, H))
    return H

def theirs_ground_at(x, y):
    return bench(np.array(x, float), np.array(y, float))

g = np.arange(-HALF, HALF + 0.1, P)
TX, TY = np.meshgrid(g, g)
THEIRS = theirs(TX, TY)

# ---------------- colour, shade, routes ----------------
STOPS = [(-70, (0.55, 0.40, 0.28)), (0, (0.88, 0.68, 0.45)), (25, (0.86, 0.60, 0.38)), (60, (0.78, 0.42, 0.22)),
         (150, (0.66, 0.30, 0.15)), (330, (0.84, 0.58, 0.40))]

def colour(Hm, cellm):
    zs = np.array([s[0] for s in STOPS], float)
    rgb = np.stack([np.interp(Hm, zs, [s[1][c] for s in STOPS]) for c in range(3)], -1)
    gy, gx = np.gradient(Hm, cellm)
    n = np.stack([-gx, -gy, np.ones_like(Hm)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    sun = np.array([-0.55, 0.55, 0.63])
    shade = 0.38 + 0.62 * np.clip((n * sun).sum(-1), 0, 1) / 0.63
    return np.clip(rgb * shade[..., None], 0, 1)

def draw(rgb, pts, x0, y0, col, r=1):
    hgt, wid = rgb.shape[:2]
    dense = []
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(np.linalg.norm(b - a) / (P * 0.5)))
        dense.append(a + (b - a) * np.linspace(0, 1, n, endpoint=False)[:, None])
    q = np.vstack(dense)
    ix, iy = np.round((q[:, 0] - x0) / P).astype(int), np.round((q[:, 1] - y0) / P).astype(int)
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            ok = (ix + dx >= 0) & (ix + dx < wid) & (iy + dy >= 0) & (iy + dy < hgt)
            rgb[iy[ok] + dy, ix[ok] + dx] = col

A = colour(OURS, P)
draw(A, circ, -js["size_x_m"] / 2, -js["size_y_m"] / 2, (1.0, 0.45, 0.05))  # JSON is centred on the world
B = colour(THEIRS, P)
draw(B, safe, -HALF, -HALF, (1.0, 0.85, 0.15))
draw(B, racing, -HALF, -HALF, (1.0, 0.45, 0.05))

M, GAP, TOP, BOT = 40, 120, 90, 90
W = M + A.shape[1] + GAP + B.shape[1] + M
Hc = BOT + A.shape[0] + TOP
canvas = np.ones((Hc, W, 4), np.float32)
canvas[..., :3] = (0.96, 0.94, 0.90)
canvas[BOT:BOT + A.shape[0], M:M + A.shape[1], :3] = A
bx = M + A.shape[1] + GAP
canvas[BOT:BOT + B.shape[0], bx:bx + B.shape[1], :3] = B
out = bpy.data.images.new("cmp", W, Hc, alpha=True)
out.pixels.foreach_set(canvas.ravel())
out.filepath_raw = f"{CMP}/lado_a_lado_topo.png"
out.file_format = "PNG"
out.save()
print("TOPO", W, Hc, "ours", A.shape, "theirs", B.shape, "theirs z", round(float(THEIRS.min()), 1), round(float(THEIRS.max()), 1))

if "topo" in sys.argv: raise SystemExit
# ---------------- 3D oblique view, both side by side ----------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def terrain(name, Hm, cellm, x0, y0):
    ny, nx = Hm.shape
    xs, ys = np.meshgrid(x0 + np.arange(nx) * cellm, y0 + np.arange(ny) * cellm)
    co = np.stack([xs, ys, Hm], -1).reshape(-1, 3).astype(np.float32)
    i = np.arange(ny * nx).reshape(ny, nx)
    quads = np.stack([i[:-1, :-1], i[:-1, 1:], i[1:, 1:], i[1:, :-1]], -1).reshape(-1, 4)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(co))
    me.vertices.foreach_set("co", co.ravel())
    me.loops.add(quads.size)
    me.loops.foreach_set("vertex_index", quads.ravel().astype(np.int32))
    me.polygons.add(len(quads))
    me.polygons.foreach_set("loop_start", (np.arange(len(quads)) * 4).astype(np.int32))
    me.update(calc_edges=True)
    me.shade_smooth()
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    zs = np.array([s[0] for s in STOPS], float)
    rgb = np.stack([np.interp(Hm.ravel(), zs, [s[1][c] for s in STOPS]) for c in range(3)] + [np.ones(Hm.size)], -1)
    ca.data.foreach_set("color", rgb.astype(np.float32).ravel())
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "Col"
    nt.links.new(at.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)

terrain("ours", OURS[::2, ::2], 2 * P, 0.0, 0.0)
terrain("theirs", THEIRS[::2, ::2], 2 * P, 11000.0, 4000.0 - HALF)

def label(text, x, y, z, size):
    cu = bpy.data.curves.new(text, "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    ob = bpy.data.objects.new(text, cu)
    ob.location = (x, y, z)
    ob.rotation_euler = (math.radians(65), 0, 0)
    m = bpy.data.materials.new(text)
    m.use_nodes = True
    em = m.node_tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    em.inputs["Strength"].default_value = 3.0
    m.node_tree.links.new(em.outputs[0], m.node_tree.nodes["Material Output"].inputs[0])
    cu.materials.append(m)
    sc.collection.objects.link(ob)

label("NOSSO MUNDO 10 x 8 km", 5000, 8600, 900, 520)
label("FASE 2C (S01) 6 x 6 km", 14025, 7300, 900, 520)

sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(55), 0, math.radians(-135))
sc.collection.objects.link(sun)
wd = bpy.data.worlds.new("w")
wd.use_nodes = True
wd.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.68, 0.85, 1)
wd.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
sc.world = wd
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 30
cam.data.clip_end = 100000
cam.location = (8525, -9500, 7500)
cam.rotation_euler = (math.radians(62), 0, 0)
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 16
sc.render.resolution_x, sc.render.resolution_y = 1800, 900
sc.view_settings.view_transform = "Standard"
sc.render.filepath = f"{CMP}/lado_a_lado_3d.png"
bpy.ops.render.render(write_still=True)
print("CMP DONE")
