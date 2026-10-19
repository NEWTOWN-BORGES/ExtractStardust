# Debug map of the world fields (world_fields.npz from sculpt_expansion.py) for choosing grand-circuit waypoints:
# 8 m per pixel, north up, grid every 500 m (black every 1 km). Rock brown, canyon floors green, side-canyon floors blue,
# dune sea yellow, core greyed with its washes (red), circuit (orange), tunnels (black), landmarks (purple/magenta).
# blender -b -P debug_world_fields.py -- <world_fields.npz> <world canyon_field.json> <out.png>
import bpy, numpy as np, json, sys

a = sys.argv[sys.argv.index("--") + 1:]
f = np.load(a[0])
js = json.load(open(a[1]))
S = 2  # 4 m cells -> 8 m px
H, floor = f["H"][::S, ::S], f["floor"][::S, ::S]
rock = (f["rocky"][::S, ::S] > 0.5) | ((H - floor) > 12)
img = np.zeros(H.shape + (3,), np.float32)
img[:] = (0.86, 0.74, 0.55)
t = np.clip((H - floor) / 300.0, 0, 1)[..., None]
img = np.where(rock[..., None], (0.55, 0.30, 0.15) * (0.6 + 0.6 * t), img)
img = np.where((f["canyon_floor"][::S, ::S] > 0.5)[..., None] & ~rock[..., None], (0.55, 0.70, 0.40), img)
img = np.where(f["slot_floor"][::S, ::S][..., None] & ~rock[..., None], (0.35, 0.55, 0.95), img)
img = np.where(f["sea"][::S, ::S][..., None] & ~rock[..., None], (0.95, 0.85, 0.45), img)
core = f["in_core"][::S, ::S]
img = np.where(core[..., None], img * 0.75 + 0.25 * np.array([0.9, 0.9, 0.9]), img)
gy, gx = np.gradient(H, 8.0)
img *= (0.75 + 0.25 * np.clip((-gx + gy) / 2 + 0.5, 0, 1))[..., None]
hgt, wid = H.shape
SX, SY = js["size_x_m"], js["size_y_m"]


def draw(pts, col, r=1, centred=True):
    pts = np.asarray(pts, float)[:, :2]
    if centred:
        pts = pts + [SX / 2, SY / 2]
    ix, iy = (pts[:, 0] / 8).astype(int), (pts[:, 1] / 8).astype(int)
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            ok = (ix + dx >= 0) & (ix + dx < wid) & (iy + dy >= 0) & (iy + dy < hgt)
            img[iy[ok] + dy, ix[ok] + dx] = col


for n, w in js["network"].items():
    pts = np.array(w["centreline"], float)
    draw(pts, (0.1, 0.8, 0.9) if w.get("giant_canyon") else (0.85, 0.1, 0.1), 0 if w.get("giant_canyon") else 1)
draw(js["circuit"]["points"], (1.0, 0.5, 0.0), 0)
for t_ in js["tunnels"]:
    draw([t_["portal_in"], t_["portal_out"]], (0, 0, 0), 2)
L = js["landmarks"]
for x, y, r, h in L["spires"]:
    draw([[x, y]], (0.9, 0.1, 0.9), 4, centred=False)
for b in L["buttes"] + L["badlands_mesas"]:
    draw([[b[0], b[1]]], (0.4, 0.0, 0.6), 4, centred=False)
for x, y, r, h in L["hoodoos"]:
    draw([[x, y]], (0.2, 0.2, 0.2), 2, centred=False)
for k in range(0, int(SX) + 1, 500):
    j = min(k // 8, wid - 1)
    img[:, j] = img[:, j] * 0.5 if k % 1000 else (0, 0, 0)
for k in range(0, int(SY) + 1, 500):
    i = min(k // 8, hgt - 1)
    img[i, :] = img[i, :] * 0.5 if k % 1000 else (0, 0, 0)
out = bpy.data.images.new("dbg", wid, hgt)
out.pixels.foreach_set(np.concatenate([img, np.ones(H.shape + (1,))], -1).astype(np.float32).ravel())
out.filepath_raw = a[2]
out.file_format = "PNG"
out.save()
print("DBG", wid, hgt)
