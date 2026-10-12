"""
EXTRACT: STARDUST — RED DUST DIVIDE · biblioteca de geologia (numpy, vetorizada).

Funções de ruído e de formação usadas pelo construtor de pistas no Blender:
  - ruído de gradiente 2D/3D (Perlin), fBm, ridged e domain warp;
  - estratificação de arenito (camadas duras formam saliências, moles recuam), com mergulho e ondulação;
  - fraturas verticais (jointing) ao longo das paredes;
  - terreno de deserto com mesas em patamares (terraced), afastadas do corredor de corrida.

Tudo trabalha em coordenadas Unity (x direita, y cima, z frente), em metros.
"""
import math
import numpy as np

# ------------------------------------------------------------------ ruído de gradiente

_G3 = np.array([[1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0],
                [1, 0, 1], [-1, 0, 1], [1, 0, -1], [-1, 0, -1],
                [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1]], dtype=np.float64)


def _hash(ix, iy, iz, seed):
    """Hash inteiro determinístico por célula da grelha (uint32 com overflow intencional)."""
    with np.errstate(over='ignore'):
        h = (ix.astype(np.uint32) * np.uint32(0x8DA6B343)
             ^ iy.astype(np.uint32) * np.uint32(0xD8163841)
             ^ iz.astype(np.uint32) * np.uint32(0xCB1AB31F)
             ^ np.uint32((seed * 0x9E3779B1) & 0xFFFFFFFF))
        h ^= h >> np.uint32(15)
        h *= np.uint32(0x2C1B3C6D)
        h ^= h >> np.uint32(12)
        h *= np.uint32(0x297A2D39)
        h ^= h >> np.uint32(15)
    return h


def _fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def perlin3(x, y, z, seed=0):
    """Ruído de gradiente 3D em ~[-1, 1]."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    x0 = np.floor(x); y0 = np.floor(y); z0 = np.floor(z)
    fx = x - x0; fy = y - y0; fz = z - z0
    x0 = x0.astype(np.int64); y0 = y0.astype(np.int64); z0 = z0.astype(np.int64)
    u = _fade(fx); v = _fade(fy); w = _fade(fz)

    def g(ix, iy, iz, dx, dy, dz):
        gr = _G3[_hash(ix, iy, iz, seed) % np.uint32(12)]
        return gr[..., 0] * dx + gr[..., 1] * dy + gr[..., 2] * dz

    n000 = g(x0, y0, z0, fx, fy, fz)
    n100 = g(x0 + 1, y0, z0, fx - 1, fy, fz)
    n010 = g(x0, y0 + 1, z0, fx, fy - 1, fz)
    n110 = g(x0 + 1, y0 + 1, z0, fx - 1, fy - 1, fz)
    n001 = g(x0, y0, z0 + 1, fx, fy, fz - 1)
    n101 = g(x0 + 1, y0, z0 + 1, fx - 1, fy, fz - 1)
    n011 = g(x0, y0 + 1, z0 + 1, fx, fy - 1, fz - 1)
    n111 = g(x0 + 1, y0 + 1, z0 + 1, fx - 1, fy - 1, fz - 1)
    nx00 = n000 + u * (n100 - n000)
    nx10 = n010 + u * (n110 - n010)
    nx01 = n001 + u * (n101 - n001)
    nx11 = n011 + u * (n111 - n011)
    nxy0 = nx00 + v * (nx10 - nx00)
    nxy1 = nx01 + v * (nx11 - nx01)
    return (nxy0 + w * (nxy1 - nxy0)) * 1.1


def perlin2(x, z, seed=0):
    return perlin3(x, np.zeros_like(np.asarray(x, dtype=np.float64)) + 0.5, z, seed)


def fbm2(x, z, octaves=5, lacunarity=2.0, gain=0.5, seed=0):
    """fBm 2D normalizado para ~[-1, 1]."""
    total = np.zeros_like(np.asarray(x, dtype=np.float64))
    amp, freq, norm = 1.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * perlin2(np.asarray(x) * freq, np.asarray(z) * freq, seed + o * 101)
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / norm


def fbm3(x, y, z, octaves=4, lacunarity=2.0, gain=0.5, seed=0):
    total = np.zeros_like(np.asarray(x, dtype=np.float64))
    amp, freq, norm = 1.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * perlin3(np.asarray(x) * freq, np.asarray(y) * freq, np.asarray(z) * freq, seed + o * 131)
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / norm


def ridged2(x, z, octaves=4, seed=0):
    """Ruído 'ridged' (cristas finas) em [0, 1]."""
    total = np.zeros_like(np.asarray(x, dtype=np.float64))
    amp, freq, norm = 1.0, 1.0, 0.0
    for o in range(octaves):
        n = 1.0 - np.abs(perlin2(np.asarray(x) * freq, np.asarray(z) * freq, seed + o * 71))
        total += amp * n * n
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ------------------------------------------------------------------ estratificação do arenito

class Strata:
    """
    Pilha de camadas sedimentares (do Colorado Plateau, reinterpretado): espessuras de 1,5 a 9 m com bancos
    maciços ocasionais de 10-16 m (formadores de falésia). Cada camada tem dureza 0..1: duras projetam-se como
    saliências, moles recuam em alcovas. As camadas mergulham ligeiramente e ondulam no plano horizontal.
    """

    def __init__(self, seed, y_min=-300.0, y_max=900.0):
        rng = np.random.default_rng(seed)
        tops, hard, tone = [], [], []
        y = y_min
        while y < y_max:
            if rng.random() < 0.12:
                t = rng.uniform(10.0, 16.0); h = rng.uniform(0.82, 1.0)
            else:
                t = rng.uniform(1.5, 9.0); h = rng.uniform(0.0, 0.85)
            y += t
            tops.append(y); hard.append(h); tone.append(rng.random())
        self.tops = np.array(tops)
        self.bottoms = np.concatenate([[y_min], self.tops[:-1]])
        self.hard = np.array(hard)
        self.tone = np.array(tone)
        self.seed = seed
        self.dip = np.array([rng.uniform(-0.012, 0.012), rng.uniform(-0.012, 0.012)])   # mergulho regional

    def local_y(self, x, y, z):
        """Altura estratigráfica: mergulho + ondulação suave das camadas."""
        warp = 3.0 * fbm2(np.asarray(x) / 700.0, np.asarray(z) / 700.0, 3, seed=self.seed + 5)
        return np.asarray(y) + self.dip[0] * np.asarray(x) + self.dip[1] * np.asarray(z) + warp

    def sample(self, x, y, z):
        """Devolve (relevo -1..1, dureza 0..1, tom 0..1, índice) por ponto."""
        ly = self.local_y(x, y, z)
        idx = np.clip(np.searchsorted(self.tops, ly), 0, len(self.tops) - 1)
        h = self.hard[idx]
        bot = self.bottoms[idx]; top = self.tops[idx]
        thick = np.maximum(top - bot, 1e-3)
        f = np.clip((ly - bot) / thick, 0.0, 1.0)
        # perfil dentro da camada: camadas duras têm aresta viva no topo e base (saliência), moles côncavas
        edge = np.minimum(f, 1.0 - f) * thick
        rim = smoothstep(0.0, 0.7, edge)               # 0 nas juntas entre camadas, 1 no interior
        relief = (h - 0.45) * 2.0 * (0.55 + 0.45 * rim)
        relief -= (1.0 - rim) * 0.35                   # junta entre camadas: pequena reentrância
        return relief, h, self.tone[idx], idx


# ------------------------------------------------------------------ fraturas verticais

class Joints:
    """Famílias de fraturas verticais ao longo de uma coordenada (distância ao longo da parede)."""

    def __init__(self, seed, length, spacing=(7.0, 24.0)):
        rng = np.random.default_rng(seed + 991)
        pos, s = [], -50.0
        while s < length + 100.0:
            s += rng.uniform(*spacing)
            pos.append(s)
        self.pos = np.array(pos)
        self.width = rng.uniform(0.8, 2.6, size=len(pos))
        self.depth = rng.uniform(0.4, 1.0, size=len(pos))

    def recess(self, s, y):
        """0..1: quanto o ponto está dentro de uma fratura (com leve inclinação/ondulação vertical)."""
        s = np.asarray(s, dtype=np.float64) + 1.2 * perlin2(np.asarray(y) / 9.0, np.asarray(s) / 40.0, 17)
        i = np.clip(np.searchsorted(self.pos, s), 1, len(self.pos) - 1)
        d0 = np.abs(s - self.pos[i - 1]); d1 = np.abs(self.pos[i] - s)
        near = np.where(d0 < d1, i - 1, i)
        d = np.minimum(d0, d1)
        w = self.width[near]
        return (1.0 - smoothstep(0.0, w, d)) * self.depth[near]


# ------------------------------------------------------------------ terreno envolvente

def terraced(h, steps, sharp=0.75):
    """Patamares de mesa: degraus com falésia (quanto maior sharp, mais vertical)."""
    k = h * steps
    base = np.floor(k)
    f = k - base
    f = smoothstep(sharp * 0.5, 1.0, f)
    return (base + f) / steps


def desert_terrain(x, z, course_dist, seed):
    """
    Deserto com dunas baixas perto do corredor e mesas em patamares ao longe (silhueta de horizonte).
    course_dist: distância horizontal ao eixo da pista (m) — as mesas só nascem a > 700 m.
    """
    x = np.asarray(x, dtype=np.float64); z = np.asarray(z, dtype=np.float64)
    swell = 5.0 * fbm2(x / 1100.0, z / 1100.0, 4, seed=seed + 1)
    dunes = 1.6 * fbm2(x / 160.0 + 0.3 * swell, z / 240.0, 3, seed=seed + 2)
    wash = -4.0 * ridged2(x / 1800.0, z / 1800.0, 3, seed=seed + 3)            # leitos secos
    # domínio deformado para mesas com contornos orgânicos
    wx = x + 450.0 * fbm2(x / 3000.0, z / 3000.0, 3, seed=seed + 4)
    wz = z + 450.0 * fbm2(x / 3000.0 + 7.1, z / 3000.0, 3, seed=seed + 5)
    m = fbm2(wx / 4200.0, wz / 4200.0, 5, seed=seed + 6) * 0.5 + 0.5
    m = np.clip((m - 0.48) / 0.32, 0.0, 1.0)
    mesa = 230.0 * terraced(m, 5, 0.8)
    mask = smoothstep(700.0, 1600.0, course_dist)
    return 6.0 + swell + dunes + wash + mesa * mask


# ------------------------------------------------------------------ coluna estratigráfica desenhada (RED DUST DIVIDE)
#
# Reinterpretação ficcional da sequência do Colorado Plateau (Island in the Sky): camadas duras formam falésias
# e bancadas (White Rim, Moss Back, topo do Wingate, Kayenta), as moles formam encostas de detrito (Chinle,
# Organ Rock, Carmel). As mesmas camadas aparecem à mesma altitude em todo o mapa — é isso que dá leitura e
# imersão às paredes "em escadaria". Escala de referência: falésias de ~300 m (Island in the Sky, NPS).
#
# Paleta (índices partilhados com o shader RedDust/Geology, sRGB):
PALETTE = [
    (150, 62, 40),    # 0  vermelho-castanho profundo (Organ Rock)
    (226, 214, 190),  # 1  creme esbranquiçado (White Rim)
    (140, 72, 50),    # 2  chocolate (Moenkopi)
    (168, 98, 70),    # 3  castanho-claro (bancos do Moenkopi)
    (185, 170, 145),  # 4  cinza-camurça (Moss Back)
    (172, 86, 64),    # 5  vermelho (Chinle)
    (128, 92, 104),   # 6  púrpura (Chinle)
    (150, 150, 130),  # 7  cinza-esverdeado (Chinle)
    (196, 98, 52),    # 8  laranja-avermelhado (Wingate)
    (150, 84, 66),    # 9  púrpura-castanho (Kayenta)
    (222, 190, 150),  # 10 creme (Navajo)
    (214, 160, 128),  # 11 rosado (Navajo / Entrada)
    (206, 150, 100),  # 12 areia
    (40, 28, 24),     # 13 verniz do deserto
]

# nome, espessura (m), dureza, ângulo da parede (°), bancada no topo (m), cor A, cor B
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


class Column:
    """Coluna estratigráfica em elevações absolutas (de baixo para cima) com perfil de parede em escadaria."""

    def __init__(self, seed, base_y=-200.0, layers=LAYERS_RDD):
        self.seed = seed
        self.layers = layers
        th = np.array([l[1] for l in layers])
        self.bottoms = base_y + np.concatenate([[0.0], np.cumsum(th)[:-1]])
        self.tops = self.bottoms + th
        self.hard = np.array([l[2] for l in layers])
        self.slope = np.array([l[3] for l in layers])
        self.bench = np.array([l[4] for l in layers])
        self.palA = np.array([l[5] for l in layers])
        self.palB = np.array([l[6] for l in layers])
        # perfil x(y): para cada camada, recuo horizontal = espessura / tan(ângulo); bancada no topo
        ys, xs = [base_y], [0.0]
        for i, l in enumerate(layers):
            run = l[1] / math.tan(math.radians(l[3]))
            ys.append(self.tops[i]); xs.append(xs[-1] + run)
            if l[4] > 0:
                ys.append(self.tops[i] + 0.05); xs.append(xs[-1] + l[4])   # bancada (quase plana, estritamente crescente)
        self.Yb = np.array(ys)
        self.Xb = np.array(xs)
        rng = np.random.default_rng(seed + 77)
        self.dip = np.array([rng.uniform(-0.004, 0.004), rng.uniform(-0.004, 0.004)])

    def X(self, y):
        return np.interp(y, self.Yb, self.Xb)

    def height_from(self, y0, x):
        """Altura da parede em escadaria a uma distância horizontal x (m) do pé, começando à elevação y0."""
        return np.interp(self.X(y0) + np.maximum(x, 0.0), self.Xb, self.Yb)

    def local_y(self, x, y, z):
        warp = 2.0 * fbm2(np.asarray(x) / 900.0, np.asarray(z) / 900.0, 3, seed=self.seed + 5)
        return np.asarray(y) + self.dip[0] * np.asarray(x) + self.dip[1] * np.asarray(z) + warp

    def sample(self, x, y, z):
        """(relevo -1..1, dureza 0..1, cor A, cor B, mistura 0..1, índice da camada) por ponto."""
        x = np.asarray(x, dtype=np.float64); y = np.asarray(y, dtype=np.float64); z = np.asarray(z, dtype=np.float64)
        ly = self.local_y(x, y, z)
        idx = np.clip(np.searchsorted(self.tops, ly), 0, len(self.tops) - 1)
        h = self.hard[idx]
        bot, top = self.bottoms[idx], self.tops[idx]
        thick = np.maximum(top - bot, 1e-3)
        f = np.clip((ly - bot) / thick, 0.0, 1.0)
        edge = np.minimum(f, 1.0 - f) * thick
        rim = smoothstep(0.0, 0.9, edge)
        relief = (h - 0.45) * 2.0 * (0.55 + 0.45 * rim) - (1.0 - rim) * 0.35
        # camadas "ledgy" (dureza intermédia): bancos finos alternados de 1,5-3 m
        ledgy = np.clip(1.0 - np.abs(h - 0.55) * 3.0, 0.0, 1.0)
        bed = np.sin(ly / 2.2 * 2.0 * np.pi + 2.0 * perlin2(x / 60.0, z / 60.0, self.seed + 9))
        relief += ledgy * 0.45 * np.sign(bed) * np.abs(bed) ** 0.5
        # mistura das duas cores da camada: manchas + bandas finas
        mix = np.clip(0.5 + 0.5 * fbm3(x / 35.0, ly / 6.0, z / 35.0, 3, seed=self.seed + 11) + 0.25 * np.sin(ly * 1.3), 0.0, 1.0)
        return relief, h, self.palA[idx], self.palB[idx], mix, idx

    def layer_of(self, y):
        return int(np.clip(np.searchsorted(self.tops, y), 0, len(self.tops) - 1))
