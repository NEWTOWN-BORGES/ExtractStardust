"""
Estudo da VARIACAO MACRO da cor das paredes.

O shader RedDust/Geology ja faz muita variacao, mas toda em escala de metros
(10-40 m): sand pocket, crust, varnish, crevice, gravel. Numa parede de 105 km
isso le-se como cor uniforme — e a critica do jogador ("corredor castanhao com
faixas da mesma cor") esta correta.

O que falta e variacao em escala de 100 m a 3 km: manchas de cascalho, veios de
areia, faces lavadas pelo vento, tufos de vegetacao, zonas mais claras e mais
escuras. E isso que faz uma parede de canyon parecer ter quilometros de historia.

Paleta: RD_PAL de RDGeology.hlsl (14 camadas do Colorado Plateau).
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust\ExtractStardustRDD\Docs"
os.makedirs(OUT, exist_ok=True)

# RD_PAL — os MESMOS valores de RDGeology.hlsl (lineares)
PAL = [
    (0.3050, 0.0482, 0.0212),   # 0  Organ Rock
    (0.7605, 0.6724, 0.5149),   # 1  White Rim
    (0.2623, 0.0648, 0.0319),   # 2  Moenkopi
    (0.3916, 0.1221, 0.0612),   # 3  Moenkopi claro
    (0.4851, 0.4020, 0.2831),   # 4  Moss Back
    (0.4125, 0.0931, 0.0513),   # 5  Chinle vermelho
    (0.2159, 0.1070, 0.1384),   # 6  Chinle purpura
    (0.3050, 0.3050, 0.2232),   # 7  Chinle cinza-esverdeado
    (0.5520, 0.1221, 0.0343),   # 8  Wingate
    (0.3050, 0.0887, 0.0545),   # 9  Kayenta
    (0.7305, 0.5149, 0.3050),   # 10 Navajo
    (0.6724, 0.3515, 0.2159),   # 11 Navajo/Entrada rosado
    (0.6172, 0.3050, 0.1274),   # 12 areia
    (0.0212, 0.0116, 0.0091),   # 13 verniz do deserto
]


def hash1(n, seed=0.0):
    h = np.sin(n * 127.1 + seed * 311.7) * 43758.5453
    return h - np.floor(h)


def noise3(p, seed=0.0):
    x0 = np.floor(p[..., 0]); y0 = np.floor(p[..., 1]); z0 = np.floor(p[..., 2])
    fx = p[..., 0] - x0; fy = p[..., 1] - y0; fz = p[..., 2] - z0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy); fz = fz * fz * (3 - 2 * fz)

    def H(dx, dy, dz):
        return hash1(x0 + dx + (y0 + dy) * 57.1 + (z0 + dz) * 131.7, seed)

    c00 = H(0, 0, 0) * (1 - fx) + H(1, 0, 0) * fx
    c10 = H(0, 1, 0) * (1 - fx) + H(1, 1, 0) * fx
    c01 = H(0, 0, 1) * (1 - fx) + H(0, 0, 1) * fx
    c11 = H(0, 1, 1) * (1 - fx) + H(1, 1, 1) * fx
    return (c00 * (1 - fy) + c10 * fy) * (1 - fz) + (c01 * (1 - fy) + c11 * fy) * fz


def fbm3(p, oct=3, seed=0.0):
    s = np.zeros(p.shape[:-1]); a = 0.5; n = 0.0
    q = p.copy()
    for o in range(oct):
        s = s + a * noise3(q, seed + o * 17)
        n += a
        q = q * 2.03 + np.array([5.2, 1.3, 7.7])
        a *= 0.5
    return s / n


PAL_NP = np.array(PAL)


def pal(i):
    """Cor da paleta; aceita escalar ou array de indices."""
    return PAL_NP[np.asarray(i, dtype=int)]


def macro_albedo(along, height, wall_u, layer_a, seed=3.0):
    """
    Variacao de cor em escala grande (o que falta), aplicada por cima da cor da camada.

    Todas as frequencias sao baixas (100 m a 3 km), para se lerem a distancia e ao
    longo de quilometros de parede.
    """
    base = pal(layer_a)
    q = np.stack([along / 1000.0, height / 160.0, wall_u * 2.0], -1)
    # mascaras sempre com eixo de cor, para o broadcasting funcionar
    m3 = lambda m: m[..., None]

    # 1. manchas de cascalho: as zonas onde a rocha esta desfeita sao mais cinzentas/frias
    grav = fbm3(q * 3.1, 3, seed)
    grav_m = np.clip((grav - 0.45) / 0.30, 0, 1)
    c = base * (1 - m3(grav_m) * 0.55) + pal(4) * (m3(grav_m) * 0.55)

    # 2. veios de areia varrida pelo vento: riscas sub-horizontais mais claras
    streak = fbm3(np.stack([along / 420.0, height / 26.0, wall_u * 3.0], -1), 2, seed + 51)
    streak_m = np.clip((streak - 0.5) / 0.28, 0, 1) ** 1.4
    c = c * (1 - m3(streak_m) * 0.40) + pal(12) * (m3(streak_m) * 0.40)

    # 3. faces lavadas pelo vento (mais escuras, o verniz cobre mais): bandas verticais largas
    wash = fbm3(np.stack([along / 260.0, height / 300.0, wall_u * 1.5], -1), 2, seed + 101)
    wash_m = np.clip((wash - 0.55) / 0.25, 0, 1)
    c = c * (1 - m3(wash_m) * 0.45) + pal(13) * (m3(wash_m) * 0.45)

    # 4. zonas mais claras e mais quentes (arenito fresco exposto)
    fresh = fbm3(np.stack([along / 1800.0, height / 420.0, wall_u * 1.0], -1), 2, seed + 151)
    fresh_m = np.clip((fresh - 0.5) / 0.3, 0, 1)
    c = c * (1 - m3(fresh_m) * 0.35) + pal(11) * (m3(fresh_m) * 0.35)

    # 5. variacao global de contexto: nenhuma parede de 100 km tem a mesma cor no inicio e no fim
    big = fbm3(np.stack([along / 4000.0, np.zeros_like(along), np.zeros_like(along)], -1), 2, seed + 211)
    c = c * (0.80 + 0.40 * m3(big))

    # 6. tufos de vegetacao: manchas pequenas e escuras/esverdeadas perto do fundo e nos patamares
    veg = fbm3(np.stack([along / 55.0, height / 40.0, wall_u * 5.0], -1), 3, seed + 307)
    veg_m = np.clip((veg - 0.62) / 0.20, 0, 1) * np.clip((wall_u - 0.15) * 3.0, 0, 1) * np.clip((0.75 - wall_u) * 4.0, 0, 1)
    c = c * (1 - m3(veg_m) * 0.5) + pal(7) * (m3(veg_m) * 0.5)

    return np.clip(c, 0, 1)


def srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)


def to8(lin):
    """Linear -> 0..255 uint8. O *255 e obrigatorio: astype(uint8) trunca (0.588 -> 0)."""
    return (srgb(lin) * 255.0 + 0.5).astype(np.uint8)


def font(sz):
    for p in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


F, FS = font(19), font(13)
BG, FG, DIM = (16, 18, 24), (232, 236, 244), (140, 148, 166)


def faixa():
    """Parede ao longo de 3 km: antes (cor de camada lisa) vs depois (variacao macro)."""
    nx, ny = 1400, 400
    L, Hh = 3000.0, 220.0
    along = np.linspace(0, L, nx)[None, :] * np.ones((ny, 1))
    height = np.linspace(0, Hh, ny)[:, None] * np.ones((1, nx))
    wall_u = height / Hh

    # camadas: a parede atravessa Organ Rock -> Moenkopi nesta fatia de 220 m
    layer_a = np.full((ny, nx), 0.0)
    layer_a += (height > 200.0) * 1.0        # a partir dos 200 m entra outra camada

    flat = pal(layer_a.astype(int))
    macro = macro_albedo(along, height, wall_u, layer_a.astype(int))

    W, H = 1500, 780
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((54, 18), "PAREDE AO LONGO DE 3 km — o que falta e variacao em escala grande", font=F, fill=FG)
    d.text((54, 44), "em cima: cor da camada lisa (o que se ve hoje) · em baixo: com variacao macro "
                     "de cascalho, areia, verniz e vegetacao", font=FS, fill=DIM)

    px, py, pw = 60, 80, 1380
    ph = 290
    top = to8(flat)
    bot = to8(macro)
    img.paste(Image.fromarray(top, "RGB").resize((pw, ph), Image.BILINEAR), (px, py))
    img.paste(Image.fromarray(bot, "RGB").resize((pw, ph), Image.BILINEAR), (px, py + ph + 40))
    d.rectangle([px - 1, py - 1, px + pw + 1, py + ph + 1], outline=(60, 64, 78))
    d.rectangle([px - 1, py + ph + 39, px + pw + 1, py + 2 * ph + 41], outline=(60, 64, 78))
    d.text((px, py + ph + 12), "ANTES — faixa de cor constante", font=FS, fill=(200, 120, 110))
    d.text((px, py + 2 * ph + 54), "DEPOIS — manchas, veios, faces lavadas, vegetacao", font=FS,
           fill=(150, 220, 170))
    d.text((px, py + 2 * ph + 76), "0 m", font=FS, fill=DIM)
    d.text((px + pw - 60, py + 2 * ph + 76), "3 km", font=FS, fill=DIM)
    img.save(os.path.join(OUT, "paredes_variacao_macro.png"))
    print("->", os.path.join(OUT, "paredes_variacao_macro.png"))


faixa()
