# Bakes the world's ground and rock textures entirely from code (no photos): every map is computed with numpy and
# tiles seamlessly (noise is shaped in frequency space, so it wraps; waves use whole cycles per tile). Each set gives
# colour (sRGB), DirectX normal and ARM (ambient occlusion, roughness, metal) at 2048 px:
#   sand      fine grain + small wind ripples (gentle windward slope, short steep lee), warm orange
#   dunes     the same sand with larger, sharper ripples
#   gravel    pebbles of many sizes half buried in sand
#   slick     sandstone pavement: cross-bedding lines and cracks
#   cliff     layered sandstone wall: beds of uneven thickness, erosion, vertical cracks
#   green     damp soil with patches of short grass
# Usage: blender -b -P bake_world_textures.py -- <output folder>   (numpy only; Blender's Python has it)
import os
import struct
import sys
import zlib

import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0]
os.makedirs(OUT, exist_ok=True)
N = 2048
rng = np.random.default_rng(7)
ky = np.fft.fftfreq(N)[:, None] * N
kx = np.fft.fftfreq(N)[None, :] * N
K = np.hypot(kx, ky)
U, V = np.meshgrid(np.arange(N) / N, np.arange(N) / N)  # 0..1 across the tile


def noise(lo, hi, slope=1.0):
    """Tileable band-limited noise: features between `hi` and `lo` cycles per tile, pinker with `slope`. -1..1."""
    spectrum = np.fft.fft2(rng.standard_normal((N, N)))
    band = np.exp(-(np.maximum(K - hi, 0) / (0.35 * hi + 1e-6)) ** 2) * (K >= lo) / np.maximum(K, 1.0) ** slope
    out = np.real(np.fft.ifft2(spectrum * band))
    return out / (np.abs(out).max() + 1e-9)


def ridges(n, m, warp, sharp=0.75):
    """Asymmetric ripples: n x m whole cycles per tile, phase warped by noise; long gentle rise, short steep fall."""
    phase = (n * U + m * V) + warp
    f = phase - np.floor(phase)
    return np.where(f < sharp, f / sharp, (1.0 - f) / (1.0 - sharp))


def normal_dx(height, strength):
    gy, gx = np.gradient(np.pad(height, 1, mode="wrap"))
    gx, gy = gx[1:-1, 1:-1] * strength, gy[1:-1, 1:-1] * strength
    n = np.stack([-gx, gy, np.ones_like(gx)], -1)  # DirectX: green points down the image
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (n * 0.5 + 0.5) * 255.0


def write_png(path, rgb):
    h, w, c = rgb.shape
    raw = np.clip(np.round(rgb), 0, 255).astype(np.uint8).reshape(h, w * c).tobytes()
    rows = b"".join(b"\x00" + raw[r * w * c:(r + 1) * w * c] for r in range(h))

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    with open(path, "wb") as f_:
        f_.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def palette(t, stops):
    """Colour ramp in sRGB 0..255: t 0..1 through (position, (r, g, b)) stops."""
    t = np.clip(t, 0.0, 1.0)
    out = np.zeros(t.shape + (3,))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        w = np.clip((t - p0) / (p1 - p0 + 1e-9), 0.0, 1.0)[..., None]
        inside = ((t >= p0) & (t <= p1))[..., None]
        out = np.where(inside, np.array(c0) * (1 - w) + np.array(c1) * w, out)
    return out


def save(name, colour, height, normal_strength, rough, ao=None):
    ao = np.clip(0.75 + 0.5 * (height - height.mean()), 0.45, 1.0) if ao is None else ao
    write_png(f"{OUT}/T_ex_{name}_diff.png", colour)
    write_png(f"{OUT}/T_ex_{name}_nor_dx.png", normal_dx(height, normal_strength))
    write_png(f"{OUT}/T_ex_{name}_arm.png", np.stack([ao * 255.0, np.clip(rough, 0, 1) * 255.0, np.zeros_like(rough)], -1))
    print("BAKED", name)


# ---- Sand: grain everywhere, small ripples (14 per tile, a 4 m tile gives ~30 cm ripples).
grain = noise(400, 900, 0.3)
patches = noise(1, 6, 1.5)
sand_h = 0.55 * ridges(14, 3, 0.35 * noise(1, 5, 1.2) + 0.08 * noise(6, 20)) + 0.08 * grain + 0.25 * patches
sand_c = palette(0.5 + 0.45 * patches + 0.12 * grain + 0.15 * (sand_h - 0.5),
                 [(0.0, (168, 104, 66)), (0.45, (196, 132, 86)), (0.75, (214, 156, 104)), (1.0, (226, 176, 126))])
save("sand", sand_c * (0.92 + 0.08 * grain[..., None]), sand_h, 9.0, 0.93 - 0.05 * grain)

# ---- Dunes: larger, sharper ripples, a little paler (wind-sorted sand).
dune_h = 0.8 * ridges(9, 2, 0.45 * noise(1, 4, 1.2), 0.82) + 0.06 * grain + 0.2 * patches
dune_c = palette(0.55 + 0.4 * patches + 0.1 * grain + 0.2 * (dune_h - 0.5),
                 [(0.0, (182, 116, 72)), (0.5, (210, 146, 94)), (1.0, (232, 182, 130))])
save("dunes", dune_c, dune_h, 12.0, 0.94 - 0.04 * grain)

# ---- Gravel: pebbles scattered on a torus (they wrap), each a rounded bump, many sizes, half buried in sand.
peb_h = np.zeros((N, N))
peb_id = np.zeros((N, N))
for i in range(2600):
    r = rng.uniform(5, 26)
    cx, cy = rng.uniform(0, N), rng.uniform(0, N)
    x0, x1, y0, y1 = int(cx - r) - 1, int(cx + r) + 2, int(cy - r) - 1, int(cy + r) + 2
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.hypot((xx - cx) / r, (yy - cy) / (r * rng.uniform(0.6, 1.0)))
    bump = np.sqrt(np.clip(1.0 - d * d, 0.0, 1.0)) * r / 26.0
    ys, xs = yy % N, xx % N
    better = bump > peb_h[ys, xs]
    peb_h[ys[better], xs[better]] = bump[better]
    peb_id[ys[better], xs[better]] = rng.uniform(0, 1)
stone = peb_h > 0.02
grav_h = 0.25 * sand_h + 0.9 * peb_h
tones = palette(peb_id, [(0.0, (92, 74, 62)), (0.3, (128, 96, 76)), (0.6, (150, 118, 92)), (0.8, (110, 104, 98)), (1.0, (170, 140, 112))])
grav_c = np.where(stone[..., None], tones * (0.8 + 0.35 * peb_h[..., None]), sand_c * 0.9)
save("gravel", grav_c, grav_h, 14.0, np.where(stone, 0.8, 0.93), ao=np.where(stone, 1.0, 0.72))

# ---- Slickrock: sandstone pavement with cross-bedding (sets of fine curved lines) and cracks.
bed = ridges(40, 9, 0.6 * noise(1, 4, 1.3), 0.5)
cracks = np.abs(noise(3, 18, 0.8))
crack = np.clip((0.06 - cracks) / 0.06, 0.0, 1.0)
slick_h = 0.25 * bed + 0.35 * noise(2, 12, 1.0) + 0.1 * grain - 0.5 * crack
slick_c = palette(0.5 + 0.35 * noise(1, 6, 1.4) + 0.15 * bed,
                  [(0.0, (142, 74, 46)), (0.5, (176, 98, 62)), (1.0, (204, 132, 88))]) * (1.0 - 0.45 * crack[..., None])
save("slick", slick_c, slick_h, 10.0, 0.82 + 0.1 * crack)

# ---- Cliff: horizontal beds of uneven thickness (V runs up the wall), erosion and vertical cracks.
beds = np.sin(2.0 * np.pi * (11 * V + 0.06 * noise(1, 6, 1.2))) + 0.6 * np.sin(2.0 * np.pi * (27 * V + 0.1 * noise(2, 10)))
vcr = np.abs(np.sin(2.0 * np.pi * (6 * U + 0.15 * noise(1, 8, 1.0))))
vcrack = np.clip((0.05 - vcr) / 0.05, 0.0, 1.0) * (noise(2, 8) > -0.2)
cliff_h = 0.3 * beds + 0.45 * noise(3, 40, 0.9) + 0.1 * grain - 0.6 * vcrack
cliff_c = palette(0.5 + 0.18 * beds + 0.3 * noise(1, 10, 1.2),
                  [(0.0, (120, 58, 36)), (0.35, (158, 82, 50)), (0.65, (186, 108, 66)), (1.0, (214, 150, 104))])
cliff_c *= (1.0 - 0.5 * vcrack[..., None]) * (0.9 + 0.1 * grain[..., None])
save("cliff", cliff_c, cliff_h, 12.0, 0.85 + 0.08 * vcrack)

# ---- Green floor: damp darker soil with patches of short grass.
grass = np.clip((noise(4, 40, 0.8) + 0.25) * 2.0, 0.0, 1.0) * (0.7 + 0.3 * np.clip(noise(200, 600, 0.2), 0, 1))
soil = palette(0.5 + 0.4 * patches, [(0.0, (92, 66, 46)), (1.0, (132, 98, 68))])
blade = palette(0.5 + 0.5 * noise(30, 200, 0.6), [(0.0, (74, 92, 40)), (1.0, (122, 134, 62))])
green_c = soil * (1 - grass[..., None]) + blade * grass[..., None]
save("green", green_c, 0.3 * grass + 0.25 * noise(50, 300, 0.5) + 0.1 * sand_h, 8.0, 0.9 - 0.1 * grass)
print("BAKE DONE")
