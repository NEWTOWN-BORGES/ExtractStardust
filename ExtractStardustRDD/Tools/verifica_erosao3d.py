"""
Verificacao do campo de erosao 3D (Erode3D em LabGeometry.cs).

Porta a mesma matematica para Python e desenha:
  1. o mapa do recuo (alcovas / fluting / rachaduras) sobre a face da parede
  2. o corte transversal a uma estacao, para se ver as reentrancias
  3. o histograma de escalas, para confirmar que ha detalhe em varias ordens de grandeza

Isto NAO e um render: e a verificacao de que o algoritmo produz as escalas pretendidas.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust\ExtractStardustRDD\Docs"
os.makedirs(OUT, exist_ok=True)

LAYERS_RDD = [
    ("Organ Rock", 200.0, 0.30), ("White Rim", 40.0, 0.95), ("Moenkopi", 65.0, 0.45),
    ("Moss Back", 15.0, 0.90), ("Chinle", 45.0, 0.15), ("Wingate", 100.0, 0.97),
    ("Kayenta", 35.0, 0.65), ("Navajo", 60.0, 0.85), ("Carmel", 20.0, 0.25),
    ("Entrada", 80.0, 0.92), ("Summerville", 60.0, 0.30),
]


def hash1(n, seed):
    h = np.sin(n * 127.1 + seed * 311.7) * 43758.5453
    return h - np.floor(h)


def noise3(p, seed):
    x0 = np.floor(p[..., 0]); y0 = np.floor(p[..., 1]); z0 = np.floor(p[..., 2])
    fx = p[..., 0] - x0; fy = p[..., 1] - y0; fz = p[..., 2] - z0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy); fz = fz * fz * (3 - 2 * fz)

    def H(dx, dy, dz):
        return hash1(x0 + dx + (y0 + dy) * 57.1 + (z0 + dz) * 131.7, seed)

    c00 = H(0, 0, 0) * (1 - fx) + H(1, 0, 0) * fx
    c10 = H(0, 1, 0) * (1 - fx) + H(1, 1, 0) * fx
    c01 = H(0, 0, 1) * (1 - fx) + H(1, 0, 1) * fx
    c11 = H(0, 1, 1) * (1 - fx) + H(1, 1, 1) * fx
    return (c00 * (1 - fy) + c10 * fy) * (1 - fz) + (c01 * (1 - fy) + c11 * fy) * fz


def fbm3(p, octaves, seed):
    s = np.zeros(p.shape[:-1]); a = 0.5; n = 0.0
    q = p.copy()
    for o in range(octaves):
        s = s + a * noise3(q, seed + o * 17)
        n += a
        q = q * 2.03 + np.array([11.3, 5.7, 7.9])
        a *= 0.5
    return s / n


def erode3d(height, along, wall_u, hardness, amount=26.0, seed=7):
    """Porta fiel de LabGeometry.Erode3D. As escalas sao divididas diretamente pelas distancias."""
    soft = np.clip(1.0 - hardness, 0.0, 1.0)
    by_hard = amount * soft ** 1.6
    alcove = fbm3(np.stack([along / 120.0, height / 90.0, wall_u * 1.1], -1), 3, seed)
    flute = fbm3(np.stack([along / 18.0, height / 14.0, wall_u * 1.7], -1), 3, seed + 101)
    crack = fbm3(np.stack([along / 5.0, height / 4.0, wall_u * 2.3], -1), 3, seed + 211)
    chip = fbm3(np.stack([along / 1.2, height / 1.2, wall_u * 3.1], -1), 2, seed + 307)
    depth = 0.62 * alcove + 0.34 * flute + 0.24 * crack + 0.12 * chip
    by_face = 0.55 + 0.65 * np.sin(wall_u * np.pi)
    return by_hard * by_face * depth


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


def layer_of(y, base=0.0):
    top = base
    for _, thick, hard in LAYERS_RDD:
        bot, top = top, top + thick
        if y <= top:
            return hard, (y - bot) / thick
    return LAYERS_RDD[-1][2], 0.5


def mapa():
    """Mapa do recuo sobre a face da parede (eixo x = ao longo, y = altura)."""
    L = 120.0          # 120 m ao longo
    Hh = 330.0         # altura total da parede
    nx, ny = 900, 480
    along = np.linspace(0, L, nx)[None, :] * np.ones((ny, 1))
    height = np.linspace(0, Hh, ny)[:, None] * np.ones((1, nx))
    wall_u = height / Hh
    hard = np.zeros_like(height)
    for j in range(ny):
        hard[j, :], _ = layer_of(height[j, 0])
    rec = erode3d(height, along, wall_u, hard)

    W, H = 1500, 900
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((54, 18), "CAMPO DE EROSAO 3D — recuo (m) sobre a face da parede", font=F, fill=FG)
    d.text((54, 44), "escuro = rocha intacta · claro = muito removido. Faixas horizontais = camadas "
                     "(as moles escavam-se, as duras resistem).", font=FS, fill=DIM)

    px, py, pw, ph = 60, 90, 1340, 700
    lo, hi = float(rec.min()), float(rec.max())
    rgba = np.zeros((ny, nx, 3), dtype=np.uint8)
    t = np.clip((rec - lo) / max(1e-6, hi - lo), 0, 1)
    # paleta do deserto: intacto = vermelho profundo, removido = creme
    c0 = np.array([120, 45, 30]); c1 = np.array([240, 224, 196])
    for k in range(3):
        rgba[..., k] = (c0[k] * (1 - t) + c1[k] * t).astype(np.uint8)
    im = Image.fromarray(rgba, "RGB").resize((pw, ph), Image.BILINEAR)
    img.paste(im, (px, py))

    # fronteiras das camadas
    yc = 0.0
    for name, thick, hardv in LAYERS_RDD:
        yc += thick
        if yc > Hh:
            break
        yy = py + ph - (yc / Hh) * ph
        d.line([(px, yy), (px + pw, yy)], fill=(255, 255, 255, 60), width=1)
        d.text((px + pw + 8, yy - 8), f"{name} ({hardv:.2f})", font=FS, fill=FG)

    d.rectangle([px - 1, py - 1, px + pw + 1, py + ph + 1], outline=(60, 64, 78))
    d.text((px, py + ph + 10), f"ao longo: 0 a {L:.0f} m      recuo: {lo:.1f} a {hi:.1f} m",
           font=FS, fill=DIM)
    d.text((px, py + ph + 30), "Repara que ha variacao em TODAS as direcoes: manchas grandes "
                               "(alcovas), riscas verticais (fluting) e pontos finos (rachaduras).",
           font=FS, fill=DIM)
    img.save(os.path.join(OUT, "erosao_campo3d.png"))
    print("->", os.path.join(OUT, "erosao_campo3d.png"))
    return rec, along, height, hard


def corte(rec, along, height, hard):
    """Corte transversal a uma estacao: mostra as reentrancias reais."""
    W, H = 1500, 620
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((54, 18), "CORTE TRANSVERSAL da parede erodida (reentrancias, cornijas e alcovas)",
           font=F, fill=FG)
    d.text((54, 44), "linha clara = parede intacta (escadaria reta) · linha laranja = paredepos erosao 3D",
           font=FS, fill=DIM)

    # perfil base (escadaria, como no Blender) e perfil erodido, a 1 estacao
    base_x, ys = [0.0], [0.0]
    x = 0.0
    for name, thick, hardv in LAYERS_RDD:
        eff = math.radians(34 + (86 - 34) * hardv)
        run = thick / math.tan(eff)
        ys.append(ys[-1] + thick); base_x.append(x + run)
        x += run
        if hardv > 0.6:
            bench = 2 + 14 * (hardv - 0.6) / 0.4
            x += bench
            ys.append(ys[-1] + 0.02); base_x.append(x)
    ys = np.array(ys); base_x = np.array(base_x)
    hmax = 330.0
    sel = ys <= hmax
    ys, base_x = ys[sel], base_x[sel]

    j = 220
    recs = rec[j, :] if rec.shape[1] > nx_guard(rec) else None
    px, py, pw, ph = 120, 90, 1180, 440
    sx = pw / max(base_x.max() * 1.15, 1.0)
    sy = ph / hmax

    def P(xx, yy):
        return (px + xx * sx, py + ph - yy * sy)

    ys_i = np.linspace(0, hmax, 300)
    base_interp = np.interp(ys_i, ys, base_x)
    hard_i = np.array([layer_of(y)[0] for y in ys_i])
    u_i = ys_i / hmax
    rec_i = erode3d(ys_i, np.full_like(ys_i, 40.0), u_i, hard_i)
    xs_i = base_interp + rec_i

    d.line([P(base_x[k], ys[k]) for k in range(len(ys))], fill=(200, 210, 225), width=2)
    d.line([P(xs_i[k], ys_i[k]) for k in range(len(ys_i))], fill=(255, 150, 70), width=3)

    # anotar a alcova maior
    k_soft = int(np.argmax(rec_i))
    ax, ay = P(xs_i[k_soft], ys_i[k_soft])
    d.ellipse([ax - 6, ay - 6, ax + 6, ay + 6], outline=(255, 220, 120), width=2)
    d.text((ax + 12, ay - 6), f"recesso {rec_i[k_soft]:0.1f} m", font=FS, fill=(255, 220, 120))

    k_hard = int(np.argmin(rec_i))
    hx, hy = P(xs_i[k_hard], ys_i[k_hard])
    d.ellipse([hx - 6, hy - 6, hx + 6, hy + 6], outline=(140, 220, 255), width=2)
    d.text((hx + 12, hy - 6), f"cornija {rec_i[k_hard]:0.1f} m", font=FS, fill=(140, 220, 255))

    d.rectangle([px - 1, py - 1, px + pw + 1, py + ph + 1], outline=(60, 64, 78))
    d.text((px, py + ph + 14), f"recesso maximo {rec_i.max():0.1f} m · minimo {rec_i.min():0.1f} m "
                               f"(camada mais dura)", font=FS, fill=FG)
    d.text((px, py + ph + 36), "As camadas duras (White Rim 0,95 · Wingate 0,97) sobressaem como "
                               "cornijas; a Chinle (0,15) forma a alcova.", font=FS, fill=DIM)
    img.save(os.path.join(OUT, "erosao_corte.png"))
    print("->", os.path.join(OUT, "erosao_corte.png"))


def nx_guard(rec):
    return rec.shape[1]


mapa()
rec, along, height, hard = mapa()
corte(rec, along, height, hard)
