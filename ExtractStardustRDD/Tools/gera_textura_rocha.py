"""
Gera uma textura de normal map de rocha (arenito com fissuras e granulado).

Nao posso compilar shaders nem renderizar aqui, mas POSSO gerar a textura — e ela
fica pronta a usar no Unity. E o complemento da erosao geometrica: a erosao 3D
resolvе ate ~4 m; abaixo disso (rachaduras finas, lascas, grao) o custo em
geometria seria absurdo (~1 M de triangulos por parede), logo vai em textura.

Padrao salvo em Assets/RedDust/Materials/Textures/rock_normal.png
(seamless: o ruido e periodico em ambas as direcoes).
"""
import math
import os

import numpy as np
from PIL import Image

OUT = (r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust"
       r"\ExtractStardustRDD\Assets\RedDust\Materials\Textures")
os.makedirs(OUT, exist_ok=True)

RES = 1024          # 1024x1024 e suficiente para detalhe fino repetido


def hash2(ix, iy, seed=0.0):
    """Hash periodico (modulo 256): o resultado e seamless em ambas as direcoes."""
    ix = np.asarray(ix, dtype=np.int64)
    iy = np.asarray(iy, dtype=np.int64)
    s = np.int64(int(seed * 1000))
    n = (ix % 256) * np.int64(374761393) + (iy % 256) * np.int64(668265263) + s * np.int64(1442695041)
    n = (n ^ (n >> np.int64(13))) * np.int64(1274126177)
    n = n ^ (n >> np.int64(16))
    return (n & np.int64(0xFFFFFF)).astype(np.float64) / float(0xFFFFFF)


def value_noise2(x, y, seed=0.0):
    x0 = np.floor(x); y0 = np.floor(y)
    fx = x - x0; fy = y - y0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    c00 = hash2(x0, y0, seed); c10 = hash2(x0 + 1, y0, seed)
    c01 = hash2(x0, y0 + 1, seed); c11 = hash2(x0 + 1, y0 + 1, seed)
    return (c00 * (1 - fx) + c10 * fx) * (1 - fy) + (c01 * (1 - fx) + c11 * fx) * fy


def fbm2(x, y, octaves, seed=0.0, gain=0.5, period=1.0):
    """fBm periodico numa grelha de `period` celulas base (mantem seamless)."""
    s = np.zeros_like(x); a = 1.0; n = 0.0; f = 1.0
    for o in range(octaves):
        s = s + a * value_noise2(x * f * period, y * f * period, seed + o * 17)
        n += a
        f *= 2.0
        a *= gain
    return s / n


def ridged2(x, y, octaves, seed=0.0, period=1.0):
    s = np.zeros_like(x); a = 1.0; n = 0.0; f = 1.0
    for o in range(octaves):
        v = value_noise2(x * f * period, y * f * period, seed + o * 23)
        s = s + a * (1.0 - np.abs(2.0 * v - 1.0))
        n += a
        f *= 2.0
        a *= 0.5
    return s / n


def height_field(res):
    """Campo de altura da rocha: grao grosso, fissuras finas e granulado."""
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float64) / res

    # grao grosso: a ondulacao da superficie da rocha
    coarse = fbm2(xx, yy, 4, seed=1.0, period=6.0)
    # fissuras: cristas finas (ridged) — sao as rachaduras
    crack = ridged2(xx * 1.7 + 0.3, yy * 1.7, 3, seed=5.0, period=14.0)
    crack = np.clip((crack - 0.62) / 0.30, 0, 1)          # so as cristas mais altas viram fissura
    # granulado: areia / grao fino
    grain = fbm2(xx, yy, 3, seed=9.0, period=48.0)

    h = 0.55 * coarse + 0.30 * grain
    h = h - 0.55 * crack                                   # as fissuras sao reentrancias
    return h


def to_normal(h, strength=2.4):
    """Campo de altura -> normal map (formato tangente, +Y verde, OpenGL)."""
    gy, gx = np.gradient(h)
    nx = -gx * strength
    ny = -gy * strength
    nz = np.ones_like(h)
    ln = np.sqrt(nx*nx + ny*ny + nz*nz)
    nx /= ln; ny /= ln; nz /= ln
    rgb = np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5], axis=-1)
    return (rgb * 255.0 + 0.5).astype(np.uint8)


def albedo_tint(h):
    """Variacao de albedo a acompanhar o relevo (opcional, para o Unity)."""
    t = (h - h.min()) / max(1e-6, h.max() - h.min())
    base = np.array([196, 168, 138], dtype=np.float64)
    dark = np.array([120, 96, 74], dtype=np.float64)
    rgb = base[None, None, :] * (1 - t[..., None]) + dark[None, None, :] * t[..., None]
    return (rgb * 255.0 + 0.5).clip(0, 255).astype(np.uint8)


h = height_field(RES)
nm = to_normal(h)
Image.fromarray(nm, "RGB").save(os.path.join(OUT, "rock_normal.png"))
Image.fromarray(albedo_tint(h), "RGB").save(os.path.join(OUT, "rock_albedo.png"))

print("rock_normal.png ->", os.path.join(OUT, "rock_normal.png"))
print("rock_albedo.png ->", os.path.join(OUT, "rock_albedo.png"))
print(f"resolucao {RES}x{RES}")
print(f"normal: R {nm[...,0].mean():.1f}  G {nm[...,1].mean():.1f}  B {nm[...,2].mean():.1f} "
      f"(media esperada ~128/128/255)")

# verificacao de seamless: comparar as bordas opostas
edge_lr = np.abs(nm[:, 0].astype(int) - nm[:, -1].astype(int)).mean()
edge_tb = np.abs(nm[0, :].astype(int) - nm[-1, :].astype(int)).mean()
inner = np.abs(nm[:, 0].astype(int) - nm[:, RES // 2].astype(int)).mean()
print(f"seamless: |borda esq - dir| = {edge_lr:.1f}  |topo - fundo| = {edge_tb:.1f}  "
      f"(comparacao: |borda - centro| = {inner:.1f})")
print("  -> quanto mais perto do valor do centro, menos costura visivel")
