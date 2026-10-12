"""
EXTRACT: STARDUST — junta texturas PBR CC0 (ambientCG, WorldGen/textures_src) em tiras verticais que o Unity
importa como Texture2DArray (uma camada por material).

  terrain_albedo.png   cor (RGB) + altura (A)       8 camadas
  terrain_normal.png   normal OpenGL (RGB) + rugosidade (A)
  model_albedo.png / model_normal.png              6 camadas para os modelos (rocha, casca, betão, metal, pintura, folhagem)
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, '..', 'textures_src'))
DST = os.path.normpath(os.path.join(HERE, '..', '..', 'Assets', 'World', 'Textures'))
N = 1024

TERRAIN = ['Ground080',   # 0 areia das dunas
           'Grass004',    # 1 relva
           'Moss001',     # 2 musgo / chão de floresta
           'Ground111',   # 3 areia e rocha vermelhas
           'Ground093C',  # 4 branco: praia, calcário, sal
           'Rock058',     # 5 rocha das encostas
           'Ground054',   # 6 estrada de terra batida
           'Ground095A']  # 7 areia molhada / margens
MODELS = ['Rock058', 'Bark014', 'Concrete034', 'Metal027', 'PaintedMetal004', 'Ground078']

def load(asset, kind, mode):
    p = os.path.join(SRC, asset, f'{asset}_1K-JPG_{kind}.jpg')
    if not os.path.exists(p):
        return None
    return Image.open(p).convert(mode).resize((N, N), Image.Resampling.LANCZOS)

def strip(assets, name_a, name_n):
    alb = Image.new('RGBA', (N, N * len(assets)))
    nrm = Image.new('RGBA', (N, N * len(assets)))
    for k, a in enumerate(assets):
        c = load(a, 'Color', 'RGB')
        h = load(a, 'Displacement', 'L') or Image.new('L', (N, N), 128)
        n = load(a, 'NormalGL', 'RGB')
        r = load(a, 'Roughness', 'L') or Image.new('L', (N, N), 200)
        ca = c.copy(); ca.putalpha(h)
        na = n.copy(); na.putalpha(r)
        # a tira do Unity lê as camadas de cima para baixo (a camada 0 é a primeira linha de cima)
        alb.paste(ca, (0, k * N)); nrm.paste(na, (0, k * N))
    alb.save(os.path.join(DST, name_a)); nrm.save(os.path.join(DST, name_n))
    print(name_a, name_n, len(assets), 'camadas')

def water_normal(size=512, waves=48, seed=5):
    """Normal map de ondas, repetível (vetores de onda inteiros), para a água."""
    import numpy as np
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size
    hx = np.zeros_like(x); hz = np.zeros_like(x)
    for _ in range(waves):
        kx, kz = rng.integers(-9, 10, 2)
        if kx == 0 and kz == 0:
            continue
        k = np.hypot(kx, kz)
        amp = 1.0 / (k ** 1.6)
        ph = rng.uniform(0, 2 * np.pi)
        a = 2 * np.pi * (kx * x + kz * y) + ph
        hx += amp * 2 * np.pi * kx * np.cos(a)
        hz += amp * 2 * np.pi * kz * np.cos(a)
    s = 0.12
    n = np.stack([-hx * s, -hz * s, np.ones_like(x)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    img = ((n * 0.5 + 0.5) * 255).astype(np.uint8)
    Image.fromarray(img, 'RGB').save(os.path.join(DST, 'water_normal.png'))
    print('water_normal.png')

os.makedirs(DST, exist_ok=True)
strip(TERRAIN, 'terrain_albedo.png', 'terrain_normal.png')
strip(MODELS, 'model_albedo.png', 'model_normal.png')
water_normal()
