"""
Estudo da EROSAO DAS PAREDES do RED DUST DIVIDE.

Reimplementa a matematica de `Art/Blender/rdd_geology.py` (class Column) e de
`Art/Blender/rdd_build_route.py` (linhas 274-302, o corte transversal da parede)
para poder mostrar o antes/depois SEM abrir o Blender.

Estados:
  1. ATUAL    - parede em escadaria com segmentos RETOS (o que se ve hoje)
  2. EROSIONADA - a mesma escadaria com recuo de erosao dependente da dureza da camada

A erosao so ACTUA PARA DENTRO (recuo), nunca para fora: assim a largura do
corredor nunca diminui e as linhas de corrida ficam garantidamente livres.

Saidas:
  parede_antes_depois.png  - corte transversal comparado, 3 estilos de parede
  parede_variacao.png      - plano da mesma parede em varias estacoes (nao e um tubo liso)
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust\ExtractStardustRDD\Docs"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- camadas reais
# nome, espessura (m), dureza, angulo da parede (graus), bancada no topo (m), corA, corB
LAYERS_RDD = [
    ("Organ Rock", 200.0, 0.30, 42.0, 0.0, 0, 2),
    ("White Rim", 40.0, 0.95, 84.0, 26.0, 1, 4),
    ("Moenkopi", 65.0, 0.45, 48.0, 4.0, 2, 3),
    ("Moss Back", 15.0, 0.90, 82.0, 10.0, 4, 7),
    ("Chinle", 45.0, 0.15, 34.0, 0.0, 5, 6),
    ("Wingate", 100.0, 0.97, 86.0, 6.0, 8, 8),
    ("Kayenta", 35.0, 0.65, 62.0, 12.0, 9, 5),
    ("Navajo", 60.0, 0.85, 70.0, 0.0, 10, 11),
    ("Carmel", 20.0, 0.25, 40.0, 0.0, 2, 5),
    ("Entrada", 80.0, 0.92, 84.0, 8.0, 11, 8),
    ("Summerville", 60.0, 0.30, 45.0, 0.0, 5, 7),
]

PALETTE = [
    (150, 62, 40), (226, 214, 190), (140, 72, 50), (168, 98, 70), (185, 170, 145),
    (172, 86, 64), (128, 92, 104), (150, 150, 130), (196, 98, 52), (150, 84, 66),
    (222, 190, 150), (214, 160, 128), (206, 150, 100), (40, 28, 24),
]


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Column:
    """Mesma logica de rdd_geology.Column (perfil x(y) em escadaria)."""

    def __init__(self, base_y=-200.0, layers=LAYERS_RDD):
        self.layers = layers
        th = np.array([l[1] for l in layers])
        self.bottoms = base_y + np.concatenate([[0.0], np.cumsum(th)[:-1]])
        self.tops = self.bottoms + th
        self.hard = np.array([l[2] for l in layers])
        self.slope = np.array([l[3] for l in layers])
        self.bench = np.array([l[4] for l in layers])
        self.palA = np.array([l[5] for l in layers])
        self.palB = np.array([l[6] for l in layers])
        ys, xs = [base_y], [0.0]
        for i, l in enumerate(layers):
            run = l[1] / math.tan(math.radians(l[3]))
            ys.append(self.tops[i]); xs.append(xs[-1] + run)
            if l[4] > 0:
                ys.append(self.tops[i] + 0.05); xs.append(xs[-1] + l[4])
        self.Yb = np.array(ys)
        self.Xb = np.array(xs)

    def X(self, y):
        return np.interp(y, self.Yb, self.Xb)


# ---------------------------------------------------------------- ruido (mesmo espirito do projeto)
def _hash(ix, seed=0):
    h = np.sin(ix * 127.1 + seed * 311.7) * 43758.5453
    return h - np.floor(h)


def vnoise1(t, seed=0):
    i = np.floor(t); f = t - i
    f = f * f * (3.0 - 2.0 * f)
    return _hash(i, seed) * (1 - f) + _hash(i + 1, seed) * f


def fbm1(t, octaves=4, seed=0):
    s, a, n = 0.0, 0.5, 0.0
    f = t.copy()
    for o in range(octaves):
        s += a * vnoise1(f, seed + o * 13)
        n += a
        f = f * 2.03 + 11.3
        a *= 0.5
    return s / n


def ridged1(t, octaves=3, seed=0):
    s, a, n = 0.0, 0.5, 0.0
    f = t.copy()
    for o in range(octaves):
        s += a * (1.0 - np.abs(2.0 * vnoise1(f, seed + o * 7) - 1.0))
        n += a
        f = f * 2.07 + 5.1
        a *= 0.5
    return s / n


# ---------------------------------------------------------------- erosao
def erosion(y, dist_along, style):
    """
    Recuo horizontal (m, >= 0) a aplicar na parede, para dentro.

    Tres efeitos, todos dependentes da dureza da camada (0 mole .. 1 dura):
      - camadas MOLES: recuam muito (alcovas, encostas de detrito)
      - camadas DURAS: recuam pouco (formam cornijas salientes)
      - ruido ao longo da rota e da altura: variacao de estacao para estacao
    """
    hard = style["hard"]
    soft = 1.0 - hard
    base = style["amount"]

    # 1. recuo por dureza: mole recua, dura resiste
    by_hardness = base * (soft ** 1.6)

    # 2. variacao ao longo da rota (alcovas maiores e mais fundas de vez em quando)
    route_n = fbm1(np.atleast_1d(np.asarray(dist_along, dtype=float)) / style["scale_along"],
                   4, seed=style["seed"])
    route_n = np.asarray(route_n).ravel()[0] if np.asarray(route_n).size == 1 else route_n
    alcove = smoothstep(style["alcove_lo"], style["alcove_hi"], route_n)
    by_route = 0.35 + 0.65 * alcove

    # 3. variacao fina em altura: cornijas, laminacoes, reentrancias
    fine = ridged1(y / style["scale_height"], 3, seed=style["seed"] + 31)
    by_height = 0.55 + 0.45 * fine

    return by_hardness * by_route * by_height


def wall_profile(col, y0, y_rim, dist_along, style, ks=260, erode=True):
    """Perfil da parede: devolve (y, x) do corte transversal a partir do pe (x=0)."""
    brk = col.Yb[(col.Yb > y0 + 0.2) & (col.Yb < y_rim - 0.2)]
    knots = np.concatenate([[y0], brk, [y_rim]])
    kx = col.X(knots)
    seglen = np.hypot(np.diff(kx), np.diff(knots)) + 1e-6
    cnt = np.maximum(1, np.floor(seglen / seglen.sum() * ks).astype(int))
    while cnt.sum() > ks:
        cnt[int(np.argmax(cnt))] -= 1
    while cnt.sum() < ks:
        cnt[int(np.argmax(seglen / cnt))] += 1
    ys = [knots[0]]
    for k in range(len(seglen)):
        t = np.arange(1, cnt[k] + 1) / cnt[k]
        ys.extend(list(knots[k] + (knots[k + 1] - knots[k]) * t))
    y = np.array(ys[:ks + 1])
    x = col.X(y) - col.X(y0)
    if erode:
        yc = np.clip(y, col.tops.min(), col.tops.max() - 0.01)
        hard = col.hard[np.clip(np.searchsorted(col.tops, yc), 0, len(col.tops) - 1)]
        x = x + erosion(y, dist_along, {**style, "hard": hard})
    x = np.maximum.accumulate(np.maximum(x, 0.0))
    return y, x


def layer_color(y, hard=None):
    """Cor da camada que contem a elevacao y (paleta de 2 cores por camada)."""
    idx = int(np.clip(np.searchsorted(Column().tops, y), 0, len(LAYERS_RDD) - 1))
    a = PALETTE[LAYERS_RDD[idx][5]]
    b = PALETTE[LAYERS_RDD[idx][6]]
    t = 0.5
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def font(sz):
    for p in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


F, FS, FT = font(19), font(13), font(26)
BG = (16, 18, 24)
FG = (232, 236, 244)
DIM = (140, 148, 166)
GRID = (40, 44, 56)

STYLES = [
    ("atual (parede reta)", dict(amount=0.0, scale_along=900.0, scale_height=40.0,
                                 alcove_lo=0.4, alcove_hi=0.75, seed=1, hard=None), False),
    ("erosao suave", dict(amount=26.0, scale_along=520.0, scale_height=26.0,
                          alcove_lo=0.42, alcove_hi=0.72, seed=7, hard=None), True),
    ("erosao forte", dict(amount=64.0, scale_along=300.0, scale_height=16.0,
                          alcove_lo=0.36, alcove_hi=0.66, seed=23, hard=None), True),
]


def antes_depois():
    W, H = 1500, 950
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((54, 20), "PAREDE DO CANYON — corte transversal (escadaria estratigrafica)", font=F, fill=FG)
    d.text((54, 46), "recuo = espessura / tan(angulo). A erosao depende da DUREZA de cada camada: "
                     "mole recua (alcova), dura resiste (cornija).", font=FS, fill=DIM)

    col = Column()
    y0 = -200.0 + 150.0
    y_rim = y0 + 330.0

    # escala comum aos tres paineis, para serem comparaveis
    profs = []
    for title, style, erode in STYLES:
        profs.append(wall_profile(col, y0, y_rim, 0.0, style, erode=erode))
    xs_max = max(p[1].max() for p in profs) * 1.06

    pw, ph = 430, 700
    for i, ((title, style, erode), (y, x)) in enumerate(zip(STYLES, profs)):
        px, py = 60 + i * (pw + 40), 110
        d.rectangle([px - 1, py - 1, px + pw + 1, py + ph + 1], outline=GRID)
        d.text((px + 12, py + 10), title, font=FS, fill=(255, 176, 82))

        sx = pw / xs_max
        sy = ph / (y_rim - y0)

        def P(xx, yy, px=px, py=py, sx=sx, sy=sy):
            # topo da parede no canto superior esquerdo; parede cresce para a direita
            return (px + xx * sx, py + ph - (yy - y0) * sy)

        d.rectangle([px, py + 26, px + pw, py + ph], fill=(24, 26, 32))

        # rocha: do topo (y alto) para baixo
        poly = [P(0.0, y[-1])] + [P(x[k], y[k]) for k in range(len(y) - 1, -1, -1)] + [P(0.0, y[0])]
        d.polygon(poly, fill=(70, 42, 34))

        for k in range(len(y) - 1):
            c = layer_color((y[k] + y[k + 1]) / 2)
            d.polygon([P(0.0, y[k]), P(x[k], y[k]), P(x[k + 1], y[k + 1]), P(0.0, y[k + 1])], fill=c)

        d.line([P(x[k], y[k]) for k in range(len(y))], fill=(255, 224, 186), width=2)

        d.text((px + 10, py + ph - 20), "corredor", font=FS, fill=DIM)
        d.text((px + pw - 44, py + 30), "topo", font=FS, fill=DIM)
        d.text((px + 12, py + ph - 42), f"recuo maximo {x.max():0} m", font=FS, fill=FG)

    # legenda das camadas com a dureza, a partir do perfil do painel do meio
    y_mid = profs[1][0]
    d.text((60, 830), "camadas atravessadas (dureza 0 = mole, 1 = dura):", font=FS, fill=FG)
    seen, lx = set(), 60
    for yy in np.linspace(y0, y_rim, 400):
        idx = int(np.clip(np.searchsorted(col.tops, yy), 0, len(LAYERS_RDD) - 1))
        if idx in seen:
            continue
        seen.add(idx)
        name, _, hard, ang, bench, ca, cb = LAYERS_RDD[idx]
        txt = f"{name} · dureza {hard:.2f}"
        d.text((lx, 852), txt, font=FS, fill=layer_color(yy))
        lx += 236
        if lx > W - 250:
            lx = 60

    d.text((54, H - 30), "A erosao so recua (nunca avanca): a largura do corredor no eixo mantem-se, "
                         "logo as linhas de corrida ficam livres.", font=FS, fill=DIM)
    img.save(os.path.join(OUT, "parede_antes_depois.png"))
    print("->", os.path.join(OUT, "parede_antes_depois.png"))


def variacao():
    """Varias estacoes ao longo da rota: mostra que a parede deixa de ser um tubo constante."""
    W, H = 1500, 760
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((54, 20), "A MESMA PAREDE AO LONGO DA ROTA (erosao forte)", font=F, fill=FG)
    d.text((54, 46), "estacoes a 0 / 120 / 240 / 360 / 480 m: o perfil muda de sitio para sitio",
           font=FS, fill=DIM)

    col = Column()
    y0 = -200.0 + 150.0
    y_rim = y0 + 330.0
    style = dict(STYLES[2][1])

    pw, ph = 280, 620
    for i, dist in enumerate([0.0, 120.0, 240.0, 360.0, 480.0]):
        px, py = 60 + i * (pw + 12), 100
        d.rectangle([px - 1, py - 1, px + pw + 1, py + ph + 1], outline=GRID)
        d.text((px + 10, py + 8), f"{dist:0.0} m", font=FS, fill=(255, 176, 82))
        sx = pw / 520.0
        sy = ph / (y_rim - y0)

        def P(x, y, px=px, py=py, sx=sx, sy=sy):
            return (px + x * sx, py + ph - (y - y0) * sy)

        y, x = wall_profile(col, y0, y_rim, dist, style, erode=True)
        poly = [P(0.0, y_rim)] + [P(x[k], y[k]) for k in range(len(y))] + [P(0.0, y0)]
        d.polygon(poly, fill=(92, 52, 40))
        for k in range(len(y) - 1):
            c = layer_color((y[k] + y[k + 1]) / 2)
            d.polygon([P(0.0, y[k]), P(x[k], y[k]), P(x[k + 1], y[k + 1]), P(0.0, y[k + 1])], fill=c)
        d.line([P(x[k], y[k]) for k in range(len(y))], fill=(255, 220, 180), width=2)

    d.text((54, H - 44), "Sem isto, a parede e a mesma em todo o lado — e e isso que faz parecer um tubo liso.",
           font=FS, fill=DIM)
    img.save(os.path.join(OUT, "parede_variacao.png"))
    print("->", os.path.join(OUT, "parede_variacao.png"))


antes_depois()
variacao()
