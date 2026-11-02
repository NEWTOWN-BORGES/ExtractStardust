"""Mapa 02, SELVA ESMERALDA: the route plan (player, 2026-11-02: "um mapa novo de 12 a 13 minutos, de sobrevivência,
em florestas, rios, África, Amazónia; muitas bifurcações, muitas curvas, muitos saltos, bifurcações para cima, para
baixo, para a esquerda e para a direita, até chegar a B").

A to B through ten sectors that alternate the Amazon and Africa (Docs/PISTA_SELVA_ESMERALDA.md): the route is drawn
from control points (x, y, ground height) like Red Dust Divide's (Scripts/sculpt_expedition_ab.py): Catmull-Rom,
river-like meanders, bends opened to each sector's tightest radius, the same speed model (550 km/h at most, a 120 m bend
at 200 km/h, 12 m/s2 up, 30 m/s2 braking) for the race time. Eighteen forks leave the road like a fork in a road and
come back to it, each going UP (bridges, the canopy, the tepui's top), DOWN (caves, a riverbed, the gorge floor, off
the waterfall) or to the LEFT or RIGHT (channels, islands, the savanna, a causeway). Jumps are placed by design.

    python3 Scripts/selva/plan_selva.py [out_dir]
Writes SELVA_PLANTA.png (the plan over the biomes) and SELVA_PERFIL.png (heights along the race, the forks above and
below the road) in out_dir (Docs by default), and Scripts/selva/selva_plano.json (route, forks, jumps, sectors) for the
Blender sculpt that comes next.
"""
import json
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Docs")
os.makedirs(OUT, exist_ok=True)
SX, SY = 20000.0, 16000.0
VMAX, ALAT, ACC, BRK = 550 / 3.6, (200 / 3.6) ** 2 / 120.0, 12.0, 30.0


# ---------------------------------------------------------------------------------------------------- polylines
def smooth1d(v, window):
    pad = window // 2
    return np.convolve(np.pad(v, pad, mode="edge"), np.ones(window) / window, "valid")[:len(v)]


def arclen(p):
    return np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])


def resample(p, step=1.0):
    s_ = arclen(p)
    t_ = np.arange(0.0, s_[-1], step)
    q = np.stack([np.interp(t_, s_, p[:, 0]), np.interp(t_, s_, p[:, 1])], 1)
    return np.vstack([q, p[-1:]]) if np.hypot(*(q[-1] - p[-1])) > 0.01 else q


def catmull(ctrl, step=2.0):
    P = np.array(ctrl, np.float64)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out, knots = [], [0]
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        m = max(2, int(np.linalg.norm(p2 - p1) / step))
        t = np.linspace(0.0, 1.0, m, endpoint=False)[:, None]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
        knots.append(knots[-1] + m)
    out.append(Q[-2][None])
    return np.vstack(out), knots


def curvature(p, window=31):
    q_ = np.stack([smooth1d(p[:, 0], window), smooth1d(p[:, 1], window)], 1)
    dx_, dy_ = np.gradient(q_[:, 0]), np.gradient(q_[:, 1])
    ddx_, ddy_ = np.gradient(dx_), np.gradient(dy_)
    return (dx_ * ddy_ - dy_ * ddx_) / (np.hypot(dx_, dy_) ** 3 + 1e-9)


def relax(p, rmin, fixed=None, iters=300, reach=30):
    """Opens bends tighter than rmin (per point), respacing to 1 m every pass; returns the line and, for each new point,
    the index of the input point it came from (as Red Dust Divide's)."""
    a0, a1 = p[0].copy(), p[-1].copy()
    rm0 = np.asarray(rmin, float) if np.ndim(rmin) else np.full(len(p), float(rmin))
    fx0 = np.zeros(len(p), bool) if fixed is None else fixed
    src = np.arange(len(p), dtype=np.float64)
    for _ in range(iters):
        si = np.clip(np.round(src).astype(int), 0, len(rm0) - 1)
        rm, fx_ = rm0[si], fx0[si]
        k_ = curvature(p)
        bad = (np.abs(k_) * rm > 1.0) & ~fx_
        bad[:reach] = bad[-reach:] = False
        if not bad.any():
            break
        ii = np.arange(len(p))
        mid = 0.5 * (p[np.clip(ii - reach, 0, len(p) - 1)] + p[np.clip(ii + reach, 0, len(p) - 1)])
        # spread over the whole bend (opening only its tightest points leaves kinks either side)
        wgt = np.clip(smooth1d(np.clip(np.abs(k_) * rm - 1.0, 0.0, 1.0) * bad, 41) * 2.0, 0.0, 1.0)
        wgt = (wgt * ~fx_)[:, None]
        p = p + 0.4 * wgt * (mid - p)
        sm = np.stack([smooth1d(p[:, 0], 5), smooth1d(p[:, 1], 5)], 1)
        p = np.where(fx_[:, None], p, sm)
        p[0], p[-1] = a0, a1
        s_ = arclen(p)
        t_ = np.arange(0.0, s_[-1], 1.0)
        p = np.stack([np.interp(t_, s_, p[:, 0]), np.interp(t_, s_, p[:, 1])], 1)
        src = np.interp(t_, s_, src)
        if np.hypot(*(p[-1] - a1)) > 0.01:
            p, src = np.vstack([p, a1[None]]), np.append(src, len(rm0) - 1)
    return p, np.clip(np.round(src).astype(int), 0, len(rm0) - 1)


def speed_profile(p, cap=None, v0=0.0):
    r_ = 1.0 / np.maximum(np.abs(curvature(p)), 1e-6)
    v = np.minimum(VMAX, np.sqrt(ALAT * r_))
    if cap is not None:
        v = np.minimum(v, cap)
    out = v.copy()
    out[0] = min(out[0], v0)
    for i in range(1, len(out)):
        out[i] = min(out[i], math.sqrt(out[i - 1] ** 2 + 2 * ACC))
    for i in range(len(out) - 2, -1, -1):
        out[i] = min(out[i], math.sqrt(out[i + 1] ** 2 + 2 * BRK))
    return out, r_


# ---------------------------------------------------------------------------------------------------- 1. the sectors
# name, where it is inspired (shown on the plan), surface kind, road half width m, tightest radius m (1: drawn shape
# kept, the hairpins), meander (amplitude m, wavelength m), control points (x, y, ground height m). World 20 x 16 km,
# origin south-west, x east, y north. A in the south-west delta, B in the north-east delta.
SECTORS = [
    ("S1 Várzea Alagada", "Amazónia", "varzea", 30.0, 170.0, (160.0, 1000.0),
     [(1500, 1200, 22), (2800, 1500, 20), (4200, 1100, 18), (5600, 1600, 20), (6900, 1300, 24)]),
    # Switchbacks up the red laterite ridge: four legs 300 m apart, hairpins of ~150 m.
    ("S2 Serra Vermelha", "Congo", "ridge", 18.0, 1.0, (0.0, 1.0),
     [(7400, 1600, 30), (8900, 1850, 70), (9200, 2050, 85), (8900, 2250, 100), (7500, 2400, 140), (7200, 2600, 152),
      (7500, 2800, 166), (8900, 2950, 206), (9200, 3150, 220), (8900, 3350, 234), (7900, 3500, 250), (7600, 3700, 256),
      (7900, 3900, 260)]),
    # Along the top of the ridge to the lip of the great falls, then the long curving descent beside them.
    ("S3 Salto Kaieteur", "Guiana", "falls", 22.0, 160.0, (40.0, 900.0),
     [(8700, 4200, 262), (9500, 4450, 262), (10200, 4500, 260), (11000, 4750, 235), (11700, 4400, 180), (11950, 3700, 110),
      (12300, 3150, 66)]),
    ("S4 Corredeiras do Congo", "Congo", "rapids", 26.0, 130.0, (140.0, 950.0),
     [(13100, 2700, 58), (14500, 2600, 54), (15800, 2900, 50), (16900, 2350, 46), (17900, 2700, 42), (18800, 3300, 40)]),
    # Under a hill held up by the roots of giant ceibas: a wide cave with skylights.
    ("S5 Gruta das Raízes", "Amazónia", "cave", 24.0, 220.0, (90.0, 650.0),
     [(19000, 4100, 38), (18700, 4900, 30), (18900, 5700, 26), (18600, 6400, 22)]),
    ("S6 Mangue Labirinto", "Delta do Níger / foz do Amazonas", "mangrove", 16.0, 100.0, (150.0, 700.0),
     [(18000, 7000, 14), (16800, 6800, 12), (15600, 7200, 12), (14400, 6800, 12), (13200, 7100, 14)]),
    # Round the base of the tepui (Roraima), climbing to its foot plateau.
    ("S7 Tepui", "Roraima", "tepui", 22.0, 150.0, (110.0, 800.0),
     [(12300, 7400, 40), (11300, 7000, 90), (10000, 6800, 130), (8700, 7100, 150), (7900, 7900, 160), (7800, 8900, 165)]),
    ("S8 Galeria da Savana", "Tanzânia / Zâmbia", "savanna", 34.0, 300.0, (150.0, 1300.0),
     [(7000, 9600, 160), (5500, 9300, 155), (4000, 9800, 160), (2800, 9400, 165), (1700, 10200, 170), (1600, 11300, 172)]),
    # The zigzag gorge below the falls (Batoka, Zambeze), down towards the delta.
    ("S9 Garganta Vitória", "Zâmbia / Zimbabué", "gorge", 18.0, 95.0, (0.0, 1.0),
     [(2200, 12000, 165), (3250, 11650, 152), (3350, 11850, 146), (3650, 12450, 130), (3850, 12500, 126), (4700, 12100, 110),
      (4900, 12150, 106), (5200, 12950, 90), (5400, 12980, 86), (6200, 12600, 70), (6400, 12700, 66), (6800, 13350, 55),
      (7800, 13100, 45)]),
    ("S10 Delta do Okavango", "Botsuana", "delta", 32.0, 150.0, (250.0, 1200.0),
     [(8800, 13600, 30), (10500, 13300, 22), (12200, 13900, 18), (14000, 13500, 15), (15800, 14200, 14), (17500, 13800, 12),
      (18800, 14500, 10)]),
]
CAPS = {"cave": 360 / 3.6, "mangrove": 480 / 3.6}   # the cave: dark, roots overhead

ctrl = np.array([(x, y) for *_r, pts in SECTORS for x, y, _ in pts], float)
zctl = np.array([z for *_r, pts in SECTORS for _, _, z in pts], float)
secctl = np.array([k for k, (*_r, pts) in enumerate(SECTORS) for _ in pts])
spl, knots = catmull(ctrl)
kf = np.interp(np.arange(len(spl)), knots, np.arange(len(knots)))
s_spl = arclen(spl)
t1 = np.arange(0.0, s_spl[-1], 1.0)
main = np.stack([np.interp(t1, s_spl, spl[:, 0]), np.interp(t1, s_spl, spl[:, 1])], 1)
kmain = np.interp(t1, s_spl, kf)
sec = secctl[np.clip(np.round(kmain).astype(int), 0, len(ctrl) - 1)]
# River-like meanders, sector by sector, fading in and out over 300 m.
dx_, dy_ = np.gradient(main[:, 0]), np.gradient(main[:, 1])
nrm = np.stack([-dy_, dx_], 1) / (np.hypot(dx_, dy_)[:, None] + 1e-9)
off = np.zeros(len(main))
for k, (_n, _w, _k, _hw, _r, (amp, wave), _p) in enumerate(SECTORS):
    ii = np.flatnonzero(sec == k)
    if amp <= 0 or len(ii) < 10:
        continue
    sl = np.arange(len(ii), dtype=float)
    ramp = max(300.0, 0.6 * wave)
    env = np.clip(sl / ramp, 0, 1) * np.clip((sl[-1] - sl) / ramp, 0, 1)
    mr = np.random.default_rng(200 + k)
    # never tighter than the sector allows (85 % of its bend budget; relax then only opens the control points' corners):
    # the shorter harmonics, which bend hardest, give way first, then the amplitude
    kb = (2 * np.pi / wave) ** 2 * 1.1 / 1.4
    budget = 0.85 / _r
    h = float(np.clip((budget / (amp * kb) - 1.0) / (0.5 * 1.63 ** 2 + 0.25 * 2.71 ** 2), 0.0, 1.0))
    amp_k = min(amp, budget / kb)
    wig = sum(a_ * np.sin(2 * np.pi * sl * f / wave + mr.uniform(0, 2 * np.pi)) for f, a_ in ((1.0, 1.0), (1.63, 0.5 * h), (2.71, 0.25 * h)))
    wig *= 0.75 + 0.35 * np.sin(2 * np.pi * sl / (wave * 3.7) + mr.uniform(0, 6.3))
    off[ii] = amp_k * wig / 1.4 * env * env * (3 - 2 * env)
    print("  meander %-24s amplitude %3.0f of %3.0f m, harmonics %3.0f %%" % (_n, amp_k, amp, 100 * h))
main = main + nrm * off[:, None]
rmin = np.array([SECTORS[s_][4] for s_ in sec], float)
main, src = relax(main, rmin, fixed=rmin <= 1.0, iters=500)
kmain, sec = kmain[src], sec[src]
half_w = np.array([SECTORS[s_][3] for s_ in sec], float)
kind = np.array([SECTORS[s_][2] for s_ in sec])
zmain = smooth1d(np.interp(kmain, np.arange(len(zctl)), zctl), 301)
N = len(main)

# ---------------------------------------------------------------------------------------------------- 2. time
cap = np.array([CAPS.get(k_, VMAX) for k_ in kind])
vel, radius = speed_profile(main, cap)
dt = 1.0 / np.maximum(vel, 5.0)
t_cum = np.cumsum(dt)
TOTAL = t_cum[-1]
print("ROUTE length %.1f km, time %d:%02d, mean %.0f km/h" % (N / 1000, TOTAL // 60, TOTAL % 60, N / TOTAL * 3.6))
sector_rows = []
for k, (name, where, *_r) in enumerate(SECTORS):
    ii = np.flatnonzero(sec == k)
    t0, t1_ = t_cum[ii[0]] - dt[ii[0]], t_cum[ii[-1]]
    row = dict(name=name, where=where, km=len(ii) / 1000, t0=float(t0), t1=float(t1_), rmin=float(radius[ii].min()),
               top=float(vel[ii].max() * 3.6), slow=float(vel[ii][5:].min() * 3.6), z0=float(zmain[ii[0]]), z1=float(zmain[ii[-1]]))
    sector_rows.append(row)
    print("  %-26s %5.1f km  %d:%02d-%d:%02d  min radius %4.0f m  top %3.0f km/h  slowest %3.0f km/h  z %3.0f->%3.0f" % (
        name, row["km"], t0 // 60, t0 % 60, t1_ // 60, t1_ % 60, row["rmin"], row["top"], row["slow"], row["z0"], row["z1"]))


# ---------------------------------------------------------------------------------------------------- 3. the forks
def at_main(x, y):
    return int(np.argmin(np.hypot(main[:, 0] - x, main[:, 1] - y)))


def side_of(i, toward):
    """+1 if a point is to the left of the road at i (counter-clockwise), -1 to the right."""
    t = main[min(i + 8, N - 1)] - main[max(i - 8, 0)]
    rel = np.asarray(toward, float) - main[i]
    return 1.0 if t[0] * rel[1] - t[1] * rel[0] >= 0 else -1.0


def fork_lane(i, side, sign_dir, length, sep):
    """The Y where a fork leaves (+1) or rejoins (-1) the road, like a motorway exit (player, 2026-11-02: "as entradas e
    saídas estão muito brutas: têm de abrir e fechar em Y; que se possa entrar sem querer a alta velocidade"). The fork is
    born against the road, running with it, and drifts away smoothly over `length` m (about 4 s of the race): no angle
    where it starts, and only a slight one (a few degrees) where it is fully apart, so it can be taken flat out. The divider
    starts as a painted line between the two lanes, so nobody hits its nose."""
    out = []
    for k in range(0, int(length) + 1, 4):
        j = int(np.clip(i + sign_dir * k, 0, N - 1))
        t = main[min(j + 6, N - 1)] - main[max(j - 6, 0)]
        t = t / max(np.linalg.norm(t), 1e-6)
        u = k / length
        out.append(main[j] + np.array([-t[1], t[0]]) * side * sep * u * u)   # opens like a parabola: tangent at the start
    return out if sign_dir > 0 else out[::-1]


# name, type (CIMA, BAIXO, ESQUERDA, DIREITA: shown on the plan and checked against the geometry), style (SAFE, RACING,
# SKILL), what it is, half width m, tightest radius m, waypoints: ("@", x, y) on the road, (x, y, dz) dz metres above
# (+) or below (-) the road's height there, or (x, y, "z", z) an absolute height (the waterfall, the tepui's top).
FORKS = [
    ("F1 Igapó", "DIREITA", "RACING", "pelo igapó: entre árvores dentro de água, rente à água", 12.0, 140.0,
     [("@", 2500, 1450), (3200, 750, 0), (4100, 650, 0), ("@", 4800, 1250)]),
    ("F2 Banco de Areia", "ESQUERDA", "SAFE", "banco de areia largo e rápido", 26.0, 300.0,
     [("@", 4700, 1450), (5300, 2150, 2), (6100, 2150, 2), ("@", 6800, 1350)]),
    ("F3 Pontes da Copa", "CIMA", "SKILL", "pontes suspensas e troncos gigantes a 35 m do chão, sobe a serra a direito", 8.0, 120.0,
     [("@", 8700, 1880), (9550, 2350, 30), (9650, 2900, 35), ("@", 8800, 3360)]),
    # (jogador, 2026-11-02: "um na ponte e outro por baixo") the third way up the ridge: the floor of a ravine under
    # the canopy bridges, between the kapoks' buttress roots, round the outside of the hairpins (it never crosses the road)
    ("F3b Ravina das Sapopemas", "BAIXO", "SAFE", "o fundo de uma ravina por baixo das Pontes da Copa, entre as raízes das sumaúmas",
     9.0, 140.0, [("@", 8300, 1780), (9260, 1715, -4), (9620, 1990, -8), (9660, 2500, -10), (9640, 3100, -10), (9500, 3600, -8),
                 ("@", 8450, 3440)]),
    ("F4 Salto da Cascata", "BAIXO", "RACING", "pela beira do salto e lá para baixo: queda de 190 m para o lago do salto", 16.0, 140.0,
     [("@", 9900, 4480), (10400, 4280, "z", 259), (10500, 3950, "z", 70), (10700, 3600, "z", 64), (11400, 3350, "z", 64),
      ("@", 12250, 3200)]),
    ("F5 Trilho da Névoa", "DIREITA", "SKILL", "patamar estreito na névoa da cascata, corta por dentro da descida", 8.0, 160.0,
     [("@", 10300, 4520), (11000, 4350, "z", 230), (11450, 3900, "z", 150), ("@", 12250, 3200)]),
    ("F6 Ilhas das Corredeiras", "DIREITA", "SKILL", "saltos de ilha em ilha no meio das corredeiras", 9.0, 110.0,
     [("@", 13500, 2650), (14100, 2100, -4), (15200, 2150, -4), ("@", 15900, 2850)]),
    ("F7 Leito Seco", "BAIXO", "RACING", "leito seco do rio, 18 m abaixo da margem", 14.0, 200.0,
     [("@", 16500, 2600), (17000, 3000, -18), (17600, 3100, -18), ("@", 18300, 3000)]),
    ("F8 Raízes Gigantes", "CIMA", "SKILL", "por cima do monte da gruta, pelas raízes das sumaúmas", 10.0, 220.0,
     [("@", 18950, 4050), (19100, 4700, 45), (19000, 5600, 45), ("@", 18700, 6350)]),
    ("F9 Rio Subterrâneo", "BAIXO", "RACING", "o andar de baixo da gruta, ao lado do rio subterrâneo", 14.0, 260.0,
     [("@", 18800, 4550), (18800, 5100, -20), (18750, 5800, -20), ("@", 18650, 6250)]),
    ("F10 Canal Estreito", "ESQUERDA", "SKILL", "canais apertados entre o mangue", 7.0, 60.0,
     [("@", 17300, 6900), (16700, 6300, 0), (15500, 6350, 0), ("@", 14800, 6750)]),
    ("F11 Palafitas", "DIREITA", "SAFE", "passadiço por cima da aldeia de palafitas, 12 m acima da água", 12.0, 160.0,
     [("@", 16300, 6950), (15500, 7700, 12), (14300, 7700, 12), ("@", 13600, 7100)]),
    ("F12 Topo do Tepui", "CIMA", "SKILL", "rampa até ao topo (520 m), saltos entre blocos de rocha e mergulho de volta", 12.0, 150.0,
     [("@", 12900, 7250), (11700, 7950, "z", 380), (10600, 8350, "z", 520), (9600, 8750, "z", 520), (8700, 9100, "z", 300),
      ("@", 7200, 9500)]),
    ("F13 Fenda do Tepui", "BAIXO", "RACING", "uma fenda dentro da base do tepui, 30 m abaixo", 10.0, 120.0,
     [("@", 10100, 6800), (9600, 7450, -30), (8800, 7650, -30), ("@", 7950, 7950)]),
    ("F14 Savana Aberta", "ESQUERDA", "RACING", "savana aberta, a mais de 500 km/h, termiteiras para saltar", 30.0, 500.0,
     [("@", 6300, 9450), (5400, 8650, 0), (4300, 8850, 0), ("@", 3500, 9550)]),
    ("F15 Floresta de Galeria", "DIREITA", "SKILL", "dentro da floresta de galeria, junto ao rio", 9.0, 150.0,
     [("@", 4300, 9750), (3700, 10450, 0), (2700, 10450, 0), ("@", 1900, 10650)]),
    ("F16 Ponte do Comboio", "CIMA", "RACING", "a velha ponte do comboio por cima da garganta, 60-70 m acima: corta os zigue-zagues", 14.0, 220.0,
     [("@", 2800, 11850), (3400, 12800, 60), (5000, 13350, 70), ("@", 6600, 13250)]),
    ("F17 Fundo da Garganta", "BAIXO", "SKILL", "o fundo da garganta, ao lado dos rápidos do Zambeze", 10.0, 110.0,
     [("@", 3500, 12150), (4300, 11800, -35), (5500, 12200, -35), ("@", 6000, 12700)]),
    ("F18 Calçada do Lago", "DIREITA", "RACING", "calçada a direito por cima do lago", 14.0, 400.0,
     [("@", 11400, 13450), (12500, 12900, 1), (14000, 12900, 1), ("@", 15000, 13650)]),
]

# What a fork is worth against the road (s gained): the risk pays (SKILL), the racing line pays a little (RACING), the
# safe way costs a little (SAFE); off the waterfall pays most. Each fork is stretched or pulled in (its middle waypoints
# moved away from or towards the straight line between its ends) until it is worth that (+-1.5 s).
TARGET_GAIN = {"SKILL": 5.0, "RACING": 2.5, "SAFE": -4.0}
SPECIAL_GAIN = {"F4 Salto da Cascata": 10.0, "F12 Topo do Tepui": 8.0}
# Forks whose shape is the point (across the tepui's top): drawn as they are; only their speed limit is tuned (the
# model does not count the 440 m climb, so the tepui's top aims at +8 s rather than a SKILL fork's +5).
FIXED_SHAPE = {"F12 Topo do Tepui", "F3b Ravina das Sapopemas"}
# Narrow, built or underground ways are slower whatever their bends (km/h).
FORK_CAPS = {"F3 Pontes da Copa": 330, "F8 Raízes Gigantes": 480, "F9 Rio Subterrâneo": 480, "F10 Canal Estreito": 400,
             "F11 Palafitas": 380, "F13 Fenda do Tepui": 440, "F15 Floresta de Galeria": 430, "F17 Fundo da Garganta": 420,
             "F16 Ponte do Comboio": 450}


KMAIN = curvature(main)


def hermite_rmin(p0, h0, p1, h1):
    """Tightest radius of the cubic from p0 (heading h0) to p1 (heading h1) that joins a fork into its exit Y."""
    D = float(np.linalg.norm(p1 - p0))
    m0, m1 = h0 * D * 0.9, h1 * D * 0.9
    t = np.linspace(0.0, 1.0, 64)[:, None]
    d1_ = (6 * t ** 2 - 6 * t) * p0 + (3 * t ** 2 - 4 * t + 1) * m0 + (-6 * t ** 2 + 6 * t) * p1 + (3 * t ** 2 - 2 * t) * m1
    d2_ = (12 * t - 6) * p0 + (6 * t - 4) * m0 + (-12 * t + 6) * p1 + (6 * t - 2) * m1
    k = np.abs(d1_[:, 0] * d2_[:, 1] - d1_[:, 1] * d2_[:, 0]) / (np.hypot(d1_[:, 0], d1_[:, 1]) ** 3 + 1e-9)
    return float(1.0 / max(k.max(), 1e-9))


def y_place(i, toward, sign_dir, bw):
    """Moves a Y back along the road (forward, for the closing one) until its lane can be taken at the road's own speed
    all along it: on the inside of a road bend the lane is tighter than the road by its offset (a Y inside a hairpin
    would be a trap for whoever goes in by mistake)."""
    best, best_m = i, -1e9
    for sh in [0] + [d_ * k_ for k_ in range(25, 1201, 25) for d_ in (1, -1)]:   # nearest first, either way
        j0 = int(np.clip(i - sign_dir * sh, 0, N - 1))
        side = side_of(j0, toward)
        L = float(np.clip(vel[j0] * 4.0, 250.0, 650.0))
        ks = np.arange(0, int(L) + 1, 4)
        js = np.clip(j0 + sign_dir * ks, 0, N - 1)
        off = (float(half_w[j0]) + bw + 4.0) * (ks / L) ** 2 * np.where(KMAIN[js] * side > 0, 1.0, -1.0)
        r_lane = 1.0 / np.maximum(np.abs(KMAIN[js]), 1e-6) - off
        m = float(np.min(r_lane / np.maximum(0.92 * vel[js] ** 2 / ALAT, 1.0)))
        if m >= 0.85:                      # at most ~8 % slower than the road there
            return j0
        if m > best_m:
            best, best_m = j0, m
    return best


def build_fork(name, wps, bw, brmin, scale, ext=0):
    i0, i1 = max(0, at_main(*wps[0][1:3]) - ext), min(N - 1, at_main(*wps[-1][1:3]) + ext)
    a, b = main[i0], main[i1]
    mids = []
    for w_ in wps[1:-1]:
        q = np.array(w_[:2], float)
        ab = b - a
        t_ = float(np.clip(np.dot(q - a, ab) / max(np.dot(ab, ab), 1e-6), 0.0, 1.0))
        foot = a + ab * t_
        mids.append(foot + (q - foot) * scale)
    wp_of = {id(m_): w_ for m_, w_ in zip(mids, wps[1:-1])}
    i0, i1 = y_place(i0, mids[0], 1, bw), y_place(i1, mids[-1], -1, bw)
    # the two Ys: about 4 s of the race each (250-650 m), shorter only if the fork is short
    v_in, v_out = float(vel[i0]), float(vel[i1])
    L0, L1 = float(np.clip(v_in * 4.0, 250.0, 650.0)), float(np.clip(v_out * 4.0, 250.0, 650.0))
    room = 0.7 * (i1 - i0)
    if L0 + L1 > room:
        L0, L1 = L0 * room / (L0 + L1), L1 * room / (L0 + L1)
    sep = float(half_w[i0]) + bw + 4.0
    side0, side1 = side_of(i0, mids[0]), side_of(i1, mids[-1])
    # the Ys do the first and last part of the way apart: waypoints inside them go (the path would double back to them);
    # a short fork keeps its middle waypoint and shortens its Ys to fit
    along = [at_main(*m_) for m_ in mids]
    keep = [m_ for m_, j_ in zip(mids, along) if i0 + 1.15 * L0 < j_ < i1 - 1.15 * L1]
    if not keep:
        mid = mids[len(mids) // 2]
        j_ = at_main(*mid)
        L0 = float(min(L0, max(150.0, 0.6 * (j_ - i0))))
        L1 = float(min(L1, max(150.0, 0.6 * (i1 - j_))))
        keep = [mid]
    mids = keep
    lane0 = fork_lane(i0, side0, 1, L0, sep)
    lane1 = fork_lane(i1, side1, -1, L1, float(half_w[i1]) + bw + 4.0)
    # and only waypoints well ahead of where the first Y ends and well before the second begins, seen along the Ys
    # themselves (a waypoint off to the side of a bend can be "ahead" on the road yet beside or behind the Y's end)
    e0, d0 = np.array(lane0[-1]), np.array(lane0[-1]) - np.array(lane0[-2])
    e1, d1 = np.array(lane1[0]), np.array(lane1[1]) - np.array(lane1[0])
    d0, d1 = d0 / max(np.linalg.norm(d0), 1e-6), d1 / max(np.linalg.norm(d1), 1e-6)
    def ahead(q, e, d, L):     # well ahead of a Y's end, or far off to its side (not behind it: no doubling back)
        v = q - e
        dist = float(np.linalg.norm(v))
        return float(np.dot(v, d)) > 0.5 * L or (dist > 2.0 * L + 400.0 and float(np.dot(v, d)) > -0.17 * dist)
    mids = [m_ for m_ in mids if ahead(m_, e0, d0, L0) and ahead(m_, e1, -d1, L1)]
    # Between the Ys the fork is driven, not drawn: from the end of the first Y it steers towards each waypoint, then
    # lines up behind the second Y, never turning tighter than the speed allows (the road's speed near the Ys, the fork's
    # own radius further in): every bend is one that can be taken.
    r_in, r_out = max(brmin, 0.92 * v_in ** 2 / ALAT), max(brmin, 0.92 * v_out ** 2 / ALAT)
    pos, hd, path, s_, ti = e0.copy(), d0.copy(), [], 0.0, 0
    limit = 3.0 * float(np.linalg.norm(e1 - e0)) + 2000.0
    goals = mids + [e1 - d1 * max(250.0, 0.7 * r_out)]          # last, a point lined up behind the exit Y
    r_join = max(brmin, 0.5 * r_out)
    while ti < len(goals) and s_ < limit:
        # once past every waypoint, into the exit Y as soon as the curve there is wide enough
        if ti >= len(mids) and int(s_) % 5 == 0 and hermite_rmin(pos, hd, e1, d1) >= r_join:
            break
        to = goals[ti] - pos
        dist = float(np.linalg.norm(to))
        rr = max(r_in * max(0.0, 1.0 - s_ / 500.0), brmin)
        ang = math.atan2(hd[0] * to[1] - hd[1] * to[0], float(np.dot(hd, to)))
        if dist < 30.0 or (dist < 2.0 * rr and abs(ang) > 1.0):   # reached, or inside the turning circle: next one
            ti += 1
            continue
        turn = float(np.clip(ang, -1.0 / rr, 1.0 / rr))
        c_, sn = math.cos(turn), math.sin(turn)
        hd = np.array([hd[0] * c_ - hd[1] * sn, hd[0] * sn + hd[1] * c_])
        pos = pos + hd
        path.append(pos.copy())
        s_ += 1.0
    # and into the second Y along a smooth curve that arrives in its direction (a cubic: it cannot loop)
    D = float(np.linalg.norm(e1 - pos))
    for k in range(1, max(2, int(D))):
        t = k / max(2, int(D))
        path.append((2 * t ** 3 - 3 * t ** 2 + 1) * pos + (t ** 3 - 2 * t ** 2 + t) * hd * D * 0.9
                    + (-2 * t ** 3 + 3 * t ** 2) * e1 + (t ** 3 - t ** 2) * d1 * D * 0.9)
    p = resample(np.vstack([np.array(lane0), np.array(path), np.array(lane1)]))
    s_b = arclen(p)
    # heights: the road's at both ends, the waypoints' in between (relative to a straight line between the ends, or
    # absolute), smoothed so a ramp is a ramp and a drop stays a drop
    s_b = arclen(p)
    marks_s, marks_z = [0.0], [float(zmain[i0])]
    for mq in mids:
        w_ = wp_of[id(mq)]
        j = int(np.argmin(np.hypot(p[:, 0] - mq[0], p[:, 1] - mq[1])))
        zb = float(np.interp(s_b[j], [0, s_b[-1]], [zmain[i0], zmain[i1]]))
        marks_s.append(float(s_b[j]))
        marks_z.append(float(w_[3]) if len(w_) == 4 else zb + float(w_[2]))
    marks_s.append(float(s_b[-1]))
    marks_z.append(float(zmain[i1]))
    order = np.argsort(marks_s)
    z_b = np.interp(s_b, np.array(marks_s)[order], np.array(marks_z)[order])
    z_b = smooth1d(z_b, 41 if "Cascata" in name else 151)
    capb = FORK_CAPS.get(name, 550) / 3.6
    vel_b, _rb = speed_profile(p, cap=capb, v0=min(float(vel[i0]), capb))   # entered at the road's speed there
    gain = float(t_cum[i1] - t_cum[i0]) - float(np.sum(1.0 / np.maximum(vel_b, 5.0)))
    # the Ys: the speed through the first and last stretch, against what the road itself allows there
    n0 = min(len(p) - 1, int(L0 + 300))
    road_in = float(vel[i0:min(N, i0 + n0)].min())
    loss_in = max(0.0, 1.0 - float(vel_b[:n0].min()) / max(min(road_in, capb), 1.0))
    rad_ = 1.0 / np.maximum(np.abs(curvature(p)), 1e-6)
    radius_in, radius_at = float(rad_[:n0].min()), int(np.argmin(rad_[:n0]))
    radius_out = float(rad_[-min(len(p) - 1, int(L1 + 300)):].min())
    return dict(p=p, z=z_b, leave=i0, rejoin=i1, km=s_b[-1] / 1000, gain=gain, lane_in=L0, lane_out=L1,
                loss_in=loss_in, radius_in=radius_in, radius_at=radius_at, radius_out=radius_out, v_in=v_in * 3.6)


forks = []
ONLY = os.environ.get("FORKS_ONLY", "")          # to tune a few forks quickly: FORKS_ONLY=F3,F15 (prints them and stops)
for name, ftype, style, what, bw, brmin, wps in FORKS:
    if ONLY and name.split()[0] not in ONLY.split(","):
        continue
    want = SPECIAL_GAIN.get(name, TARGET_GAIN[style])
    f, best_scale = None, 1.0
    for ext in ((0,) if name in FIXED_SHAPE else (0, 300, 600, 900)):
        # 1. stretch or pull in its middle; 2. its speed limit; 3. if still too slow, it replaces a longer stretch of road
        lo, hi = (1.0, 1.0) if name in FIXED_SHAPE else (0.25, 3.5)
        for _it in range(12):
            scale = math.sqrt(lo * hi)
            g_ = build_fork(name, wps, bw, brmin, scale, ext)
            if f is None or abs(g_["gain"] - want) < abs(f["gain"] - want):
                f, best_scale, best_ext = g_, scale, ext
            if abs(g_["gain"] - want) < 1.5:
                break
            if g_["gain"] > want:
                lo = scale
            else:
                hi = scale
        if abs(f["gain"] - want) >= 1.5 and f["gain"] > want:
            lo_c, hi_c = 200.0, 550.0
            for _it in range(10):
                FORK_CAPS[name] = 0.5 * (lo_c + hi_c)
                g_ = build_fork(name, wps, bw, brmin, best_scale, best_ext)
                if abs(g_["gain"] - want) < abs(f["gain"] - want):
                    f = g_
                if abs(g_["gain"] - want) < 1.0:
                    break
                if g_["gain"] > want:
                    hi_c = FORK_CAPS[name]
                else:
                    lo_c = FORK_CAPS[name]
        if abs(f["gain"] - want) < 1.5:
            break
    tdir = main[min(f["leave"] + 40, N - 1)] - main[f["leave"]]
    rel = f["p"][len(f["p"]) // 2] - main[(f["leave"] + f["rejoin"]) // 2]
    side = "ESQUERDA" if tdir[0] * rel[1] - tdir[1] * rel[0] > 0 else "DIREITA"
    f.update(name=name, type=ftype, side=side, style=style, what=what, w=bw)
    forks.append(f)
    print("FORK %-24s %-8s %-6s %4.1f km (road %4.1f)  %+5.1f s  Y %3.0f/%3.0f m  in at %3.0f km/h, bends >= %4.0f/%4.0f m, loses %2.0f %%" % (
        name, ftype, style, f["km"], (f["rejoin"] - f["leave"]) / 1000, f["gain"], f["lane_in"], f["lane_out"], f["v_in"],
        f["radius_in"], f["radius_out"], 100 * f["loss_in"]))
if ONLY:
    sys.exit(0)

# ---------------------------------------------------------------------------------------------------- 4. the jumps
# On the road: (sector, fraction of the sector, what); on the forks: (fork name, fraction, what).
JUMPS = [
    (0, 0.33, "igarapé"), (0, 0.70, "tronco caído"), (1, 0.95, "crista da serra"), (2, 0.30, "laje da cascata"),
    (2, 0.78, "degrau da descida"), (3, 0.15, "afluente"), (3, 0.38, "rápido"), (3, 0.62, "afluente"), (3, 0.86, "rápido"),
    (4, 0.08, "boca da gruta"), (4, 0.90, "saída da gruta"), (5, 0.28, "canal"), (5, 0.55, "canal"), (5, 0.84, "raiz"),
    (6, 0.35, "talude"), (6, 0.80, "rampa de basalto"), (7, 0.18, "termiteira"), (7, 0.42, "rio de areia"),
    (7, 0.68, "termiteira"), (7, 0.90, "lomba"), (8, 0.22, "ressalto"), (8, 0.50, "ressalto"), (8, 0.78, "ressalto"),
    (9, 0.25, "canal do delta"), (9, 0.50, "canal do delta"), (9, 0.72, "ilha"), (9, 0.92, "último canal"),
]
FORK_JUMPS = [
    ("F1 Igapó", 0.5, "raízes"), ("F3 Pontes da Copa", 0.35, "ponte partida"), ("F3 Pontes da Copa", 0.7, "tronco"), ("F3b Ravina das Sapopemas", 0.55, "raiz"),
    ("F4 Salto da Cascata", 0.45, "SALTO DE 190 m"), ("F6 Ilhas das Corredeiras", 0.3, "ilha"),
    ("F6 Ilhas das Corredeiras", 0.5, "ilha"), ("F6 Ilhas das Corredeiras", 0.7, "ilha"), ("F8 Raízes Gigantes", 0.4, "raiz"),
    ("F8 Raízes Gigantes", 0.75, "descida"), ("F11 Palafitas", 0.5, "cais"), ("F12 Topo do Tepui", 0.45, "fenda"),
    ("F12 Topo do Tepui", 0.6, "fenda"), ("F12 Topo do Tepui", 0.85, "mergulho"), ("F14 Savana Aberta", 0.5, "termiteira"),
    ("F16 Ponte do Comboio", 0.9, "fim da ponte"), ("F17 Fundo da Garganta", 0.5, "rochedo"),
]
jumps_main = []
for s_i, frac, what in JUMPS:
    ii = np.flatnonzero(sec == s_i)
    j = int(ii[int(frac * (len(ii) - 1))])
    jumps_main.append((j, what))
fork_by = {f["name"]: f for f in forks}
jumps_fork = []
for fname, frac, what in FORK_JUMPS:
    f = fork_by[fname]
    j = int(frac * (len(f["p"]) - 1))
    jumps_fork.append((fname, j, what))
print("JUMPS road %d, forks %d" % (len(jumps_main), len(jumps_fork)))

# ---------------------------------------------------------------------------------------------------- 5. the plan
SECTOR_COLS = ["#f2d64c", "#e0702a", "#5fd0ff", "#3f7fe0", "#8a5cd6", "#2fb59a", "#c9a46a", "#f0b23a", "#e04f3a", "#f7f0d0"]
TYPE_COLS = {"CIMA": "#ff9a2e", "BAIXO": "#38c8ff", "ESQUERDA": "#ffffff", "DIREITA": "#ffe24a"}


def biome_map(res=25.0):
    """A stylised map of the land: rainforest, the red ridge, the tepui, savanna, mangroves, rivers and lakes."""
    nx, ny = int(SX / res), int(SY / res)
    X, Y = np.meshgrid((np.arange(nx) + 0.5) * res, (np.arange(ny) + 0.5) * res)
    rr = np.random.default_rng(5)

    def noise(scale, oct_=4):
        acc = np.zeros_like(X)
        amp, tot = 1.0, 0.0
        for o in range(oct_):
            g = rr.normal(size=(int(SY / scale * 2 ** o) + 3, int(SX / scale * 2 ** o) + 3))
            gy = Y / scale * 2 ** o
            gx = X / scale * 2 ** o
            x0, y0 = np.floor(gx).astype(int), np.floor(gy).astype(int)
            fx_, fy_ = gx - x0, gy - y0
            fx_, fy_ = fx_ * fx_ * (3 - 2 * fx_), fy_ * fy_ * (3 - 2 * fy_)
            v = (g[y0, x0] * (1 - fx_) * (1 - fy_) + g[y0, x0 + 1] * fx_ * (1 - fy_) + g[y0 + 1, x0] * (1 - fx_) * fy_
                 + g[y0 + 1, x0 + 1] * fx_ * fy_)
            acc += amp * v
            tot += amp
            amp *= 0.5
        return acc / tot

    n1, n2 = noise(1600.0), noise(380.0, 3)
    img = np.zeros((ny, nx, 3))
    forest = np.array([0.09, 0.27, 0.12])
    img[:] = forest * (0.8 + 0.25 * n1[..., None] + 0.18 * n2[..., None])

    def blend(mask, col, amt=1.0):
        m = np.clip(mask, 0, 1)[..., None] * amt
        img[:] = img * (1 - m) + np.array(col) * m * (0.88 + 0.2 * n2[..., None])

    def ellipse(cx, cy, rx, ry, soft):
        d = np.hypot((X - cx) / rx, (Y - cy) / ry)
        return np.clip((1.0 - d + 0.35 * n1) / soft, 0, 1)

    blend(ellipse(8600, 2900, 2600, 1700, 0.25), [0.42, 0.20, 0.12], 0.75)         # the red ridge
    blend(ellipse(4300, 9800, 3900, 1700, 0.3), [0.62, 0.55, 0.30], 0.85)           # savanna
    blend(ellipse(15800, 6900, 3300, 900, 0.25), [0.16, 0.30, 0.25], 0.8)           # mangroves
    blend(ellipse(10000, 8500, 1500, 1200, 0.06), [0.36, 0.30, 0.26], 1.0)          # the tepui's top
    blend(ellipse(3600, 1400, 3200, 900, 0.3), [0.12, 0.32, 0.30], 0.6)             # flooded forest
    blend(ellipse(13800, 13800, 5200, 1100, 0.3), [0.18, 0.38, 0.28], 0.6)          # delta
    blend(ellipse(13000, 13000, 900, 380, 0.2), [0.10, 0.28, 0.45], 0.9)            # the lake (F18)
    blend(ellipse(10550, 3800, 380, 260, 0.2), [0.12, 0.35, 0.55], 0.9)             # the falls' pool
    return img


def river(ax, pts, w, col="#2f8fd8", alpha=0.9):
    p, _k = catmull(pts, step=10.0)
    ax.plot(p[:, 0] / 1000, p[:, 1] / 1000, color=col, lw=w, alpha=alpha, solid_capstyle="round", zorder=2)


fig, ax = plt.subplots(figsize=(16, 13.2), dpi=120)
fig.patch.set_facecolor("#081226")
ax.set_facecolor("#081226")
ax.imshow(biome_map(), origin="lower", extent=(0, SX / 1000, 0, SY / 1000), zorder=0)
# rivers (name, width m, control points): the delta at A, the Congo along the rapids, the falls, the mangrove channels,
# the gallery river, the Zambezi in the gorge, the Okavango at B (also in the JSON, for the terrain: Scripts/selva/sculpt_selva.py)
RIVERS = [
    ("Delta de A", 180.0, [(0, 900), (1800, 900), (3600, 1800), (5200, 1100), (7000, 900)]),
    ("Congo", 170.0, [(10400, 6200), (10450, 5000), (10500, 4200), (10600, 3600), (11400, 3000), (13200, 2150), (14800, 2550),
                      (16300, 2050), (18000, 2450), (20000, 2600)]),
    ("Canais do mangue", 130.0, [(19500, 6900), (17600, 7300), (16000, 6600), (14400, 7300), (12600, 6900), (11800, 6300)]),
    ("Rio da galeria", 110.0, [(7600, 10300), (5600, 10100), (3800, 10300), (2600, 9900), (1000, 10700), (300, 11300)]),
    ("Zambeze", 130.0, [(1500, 12000), (3000, 11950), (3550, 12600), (4650, 12350), (5100, 13150), (6250, 12850), (6900, 13550),
                        (8600, 13350)]),
    ("Okavango", 145.0, [(8600, 14300), (11000, 14100), (13000, 14500), (15500, 14700), (18000, 14600), (20000, 15200)]),
]
for _rn, wid, pts in RIVERS:
    river(ax, pts, wid / 55.0)
ax.annotate("salto de 190 m", (10.48, 4.05), color="white", fontsize=9, ha="right", xytext=(9.0, 5.3),
            arrowprops=dict(arrowstyle="->", color="white", lw=1.0), zorder=9)
ax.text(10.55, 7.75, "TEPUI 520 m", color="#f3e3cf", fontsize=11, ha="center", va="center", fontweight="bold", zorder=9)
ax.text(4.2, 10.75, "savana", color="#3b2f12", fontsize=11, ha="center", style="italic", zorder=9)
ax.text(15.8, 6.15, "mangue", color="#cfe9dc", fontsize=10, ha="center", style="italic", zorder=9)
# the road, sector by sector (the cave dashed)
for k in range(len(SECTORS)):
    ii = np.flatnonzero(sec == k)
    seg = main[ii[0]:ii[-1] + 2]
    style = (0, (2, 1.4)) if SECTORS[k][2] == "cave" else "solid"
    ax.plot(seg[:, 0] / 1000, seg[:, 1] / 1000, color="#0b0b0b", lw=6.2, zorder=4, solid_capstyle="round")
    ax.plot(seg[:, 0] / 1000, seg[:, 1] / 1000, color=SECTOR_COLS[k], lw=3.6, zorder=5, linestyle=style, solid_capstyle="round")
    mid = main[ii[len(ii) // 2]]
    ax.text(mid[0] / 1000, mid[1] / 1000 + 0.32, SECTORS[k][0].split(" ")[0], color=SECTOR_COLS[k], fontsize=13,
            fontweight="bold", ha="center", zorder=10)
# the forks
for f in forks:
    p = f["p"]
    col = TYPE_COLS[f["type"]]
    ax.plot(p[:, 0] / 1000, p[:, 1] / 1000, color="#0b0b0b", lw=4.2, zorder=6, solid_capstyle="round")
    ax.plot(p[:, 0] / 1000, p[:, 1] / 1000, color=col, lw=2.1, zorder=7, solid_capstyle="round",
            linestyle=(0, (4, 1.6)) if f["type"] == "BAIXO" else "solid")
    m = p[len(p) // 2]
    ax.text(m[0] / 1000, m[1] / 1000, f["name"].split(" ")[0], color="#081226", fontsize=8.5, fontweight="bold", ha="center",
            va="center", zorder=11, bbox=dict(boxstyle="round,pad=0.18", fc=col, ec="#081226", lw=0.8))
# the jumps
for j, _w in jumps_main:
    ax.plot(main[j, 0] / 1000, main[j, 1] / 1000, marker="^", ms=8.5, color="#fff35a", mec="#081226", mew=1.0, zorder=12)
for fname, j, _w in jumps_fork:
    p = fork_by[fname]["p"]
    big = "190" in _w
    ax.plot(p[j, 0] / 1000, p[j, 1] / 1000, marker="^", ms=14 if big else 7, color="#ff5a3c" if big else "#fff35a", mec="#081226",
            mew=1.0, zorder=12)
ax.plot(main[0, 0] / 1000, main[0, 1] / 1000, "o", ms=17, color="white", mec="#081226", mew=2, zorder=13)
ax.text(main[0, 0] / 1000, main[0, 1] / 1000, "A", color="#081226", fontsize=11, fontweight="bold", ha="center", va="center", zorder=14)
ax.plot(main[-1, 0] / 1000, main[-1, 1] / 1000, "*", ms=26, color="#ffcf3a", mec="#081226", mew=1.5, zorder=13)
ax.text(main[-1, 0] / 1000 - 0.1, main[-1, 1] / 1000 + 0.45, "B extração", color="#ffcf3a", fontsize=12, fontweight="bold",
        ha="right", zorder=14)
ax.set_xlim(0, SX / 1000)
ax.set_ylim(0, SY / 1000)
ax.set_aspect("equal")
ax.tick_params(colors="#9fb6d8", labelsize=9)
for s_ in ax.spines.values():
    s_.set_color("#2a4a7a")
ax.set_xlabel("km", color="#9fb6d8")
ax.set_title("MAPA 02 · SELVA ESMERALDA · de A a B: %.1f km, %d:%02d na linha ideal (média %.0f km/h) · %d bifurcações · %d saltos"
             % (N / 1000, TOTAL // 60, TOTAL % 60, N / TOTAL * 3.6, len(forks), len(jumps_main) + len(jumps_fork)),
             color="#eef5ff", fontsize=14, fontweight="bold", loc="left", pad=12)
legend = [Line2D([0], [0], color=TYPE_COLS["CIMA"], lw=3, label="bifurcação por CIMA"),
          Line2D([0], [0], color=TYPE_COLS["BAIXO"], lw=3, linestyle=(0, (4, 1.6)), label="bifurcação por BAIXO"),
          Line2D([0], [0], color=TYPE_COLS["ESQUERDA"], lw=3, label="à ESQUERDA"),
          Line2D([0], [0], color=TYPE_COLS["DIREITA"], lw=3, label="à DIREITA"),
          Line2D([0], [0], marker="^", color="none", mfc="#fff35a", mec="#081226", ms=9, label="salto"),
          Line2D([0], [0], marker="^", color="none", mfc="#ff5a3c", mec="#081226", ms=13, label="salto da cascata (190 m)")]
leg = ax.legend(handles=legend, loc="upper left", fontsize=9.5, facecolor="#0d1c38", edgecolor="#2a4a7a", labelcolor="#eef5ff",
                framealpha=0.92)
leg.set_zorder(20)
rows = ["%s  %s  %4.1f km  %d:%02d" % (r["name"].split(" ")[0], " ".join(r["name"].split(" ")[1:]), r["km"],
                                       (r["t1"] - r["t0"]) // 60, (r["t1"] - r["t0"]) % 60) for r in sector_rows]
ax.text(19.85, 0.25, "\n".join(rows), color="#eef5ff", fontsize=8.6, family="monospace", ha="right", va="bottom", zorder=20,
        bbox=dict(boxstyle="round,pad=0.5", fc="#0d1c38", ec="#2a4a7a", alpha=0.92))
fig.tight_layout()
fig.savefig(os.path.join(OUT, "SELVA_PLANTA.png"), facecolor=fig.get_facecolor())
plt.close(fig)

# ---------------------------------------------------------------------------------------------------- 6. the profile
fig, ax = plt.subplots(figsize=(16, 6.2), dpi=120)
fig.patch.set_facecolor("#081226")
ax.set_facecolor("#0d1c38")
dist = np.arange(N) / 1000.0
for k in range(len(SECTORS)):
    ii = np.flatnonzero(sec == k)
    ax.axvspan(dist[ii[0]], dist[ii[-1]], color=SECTOR_COLS[k], alpha=0.10, lw=0)
    ax.text((dist[ii[0]] + dist[ii[-1]]) / 2, 585, SECTORS[k][0].split(" ")[0], color=SECTOR_COLS[k], ha="center", fontsize=11,
            fontweight="bold")
for f in forks:
    m = np.linspace(f["leave"], f["rejoin"], len(f["p"])) / 1000.0
    ax.plot(m, f["z"], color=TYPE_COLS[f["type"]], lw=1.8, linestyle=(0, (4, 1.6)) if f["type"] == "BAIXO" else "solid", zorder=3)
    jx = np.argmax(np.abs(f["z"] - np.interp(np.linspace(f["leave"], f["rejoin"], len(f["p"])), np.arange(N), zmain)))
    ax.text(m[jx], f["z"][jx] + (12 if f["type"] != "BAIXO" else -26), f["name"].split(" ")[0], color=TYPE_COLS[f["type"]],
            fontsize=8.5, ha="center", fontweight="bold")
ax.plot(dist, zmain, color="#eef5ff", lw=2.6, zorder=4, label="estrada principal")
for j, _w in jumps_main:
    ax.plot(dist[j], zmain[j] + 8, marker="v", color="#fff35a", ms=6, zorder=5)
ax.set_xlim(0, dist[-1])
ax.set_ylim(-60, 620)
ax.set_xlabel("km desde A", color="#9fb6d8")
ax.set_ylabel("altitude (m)", color="#9fb6d8")
ax.tick_params(colors="#9fb6d8")
for s_ in ax.spines.values():
    s_.set_color("#2a4a7a")
ax.grid(color="#1f3a66", lw=0.6)
ax.set_title("PERFIL · a estrada (branco) e as bifurcações por cima (laranja) e por baixo (azul) · ▼ saltos", color="#eef5ff",
             fontsize=13, fontweight="bold", loc="left")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "SELVA_PERFIL.png"), facecolor=fig.get_facecolor())
plt.close(fig)

# ---------------------------------------------------------------------------------------------------- 7. the data
data = dict(
    name="Selva Esmeralda", world_m=[SX, SY], length_m=N, time_s=float(TOTAL),
    route=dict(points=main[::5].round(1).tolist(), z=zmain[::5].round(1).tolist(), half_width=half_w[::5].tolist(),
               sector=sec[::5].tolist(), kind=kind[::5].tolist(), step_m=5),
    sectors=sector_rows,
    forks=[dict(name=f["name"], type=f["type"], side=f["side"], style=f["style"], what=f["what"], half_width=f["w"],
                leave_m=int(f["leave"]), rejoin_m=int(f["rejoin"]), length_m=round(f["km"] * 1000), gain_s=round(f["gain"], 1),
                points=f["p"][::5].round(1).tolist(), z=f["z"][::5].round(1).tolist()) for f in forks],
    jumps=[dict(at_m=int(j), what=w) for j, w in jumps_main] + [dict(fork=fn, at=int(j), what=w) for fn, j, w in jumps_fork],
    rivers=[dict(name=rn, width_m=wid, points=catmull(pts, step=10.0)[0].round(1).tolist()) for rn, wid, pts in RIVERS],
)
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "selva_plano.json"), "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False)
print("PLAN written to", OUT)
