"""
EXTRACT: STARDUST — RED DUST DIVIDE · biblioteca do construtor de percursos (Blender).

Usada por rdd_build_route.py (grafo de percursos: principal + ramos). Ver documentação desse ficheiro.

(Documentação original do construtor de percurso único:)

Uso:
  blender -b --factory-startup -P rdd_build_course.py -- <spec.json> <pasta_saida>

A geologia vem primeiro: um planalto estratificado (coluna desenhada em rdd_geology.LAYERS_RDD) onde os canyons
são escavados. O canyon da corrida segue o eixo invisível do percurso; as paredes sobem em escadaria segundo as
camadas (falésias nas duras, encostas nas moles, bancadas no topo das duras), com alcovas e esporões. Canyons
laterais, uma rede de canyons distante, mesas de Entrada e cúpulas de Navajo dão imersão e horizonte.

Passos:
  1. eixo do percurso (clotoides, bank, secções) e secção de corrida esculpida (leito, filete, paredes polidas);
  2. paisagem: linhas de canyon (percurso, afluentes, garganta da ravina, rede distante) + planalto + mesas;
  3. paredes próximas em alta resolução (escadaria + estratos + fraturas) a ligar a secção ao terreno;
  4. caverna sob o planalto (teto irregular + bocas na parede), ravina (garganta transversal + faces de falésia);
  5. terreno multi-resolução (8 / 24 / 64 m) com saias anti-fendas;
  6. FBX (validado por teste de eixos), dados do percurso (.bytes), mapa (.png) e relatório (.json).

Coordenadas internas: Unity (x direita, y cima, z frente). Na conversão para o Blender: (x, z, y).
"""
import bpy
import json
import math
import os
import struct
import sys
import time

import numpy as np
from mathutils import kdtree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rdd_geology as geo  # noqa: E402

T0 = time.time()


def log(msg):
    print(f"[rdd {time.time() - T0:6.1f}s] {msg}", flush=True)


# Resolução da secção transversal (constante para a malha do corredor ser uma grelha contínua)
KF, KW, KL = 30, 26, 3        # segmentos por meia-secção: leito (canal, bancadas, degraus), filete+parede, borda
KS = 64                       # parede próxima (escadaria) por lado, do pé até à borda do planalto
KC = 30                       # teto da caverna
KV = 14                       # faces de falésia (ravina)
RIM_SEARCH = 760.0            # alcance da procura da borda do planalto (m)

EASED = ['width', 'bank', 'slope', 'curv', 'wallL', 'wallR', 'filletL', 'filletR', 'angleL', 'angleR',
         'lipL', 'lipR', 'rideL', 'rideR', 'ceil', 'open', 'apron']
OPEN_FIELDS = []              # percursos à superfície (open > 0): o planalto vem ter com a borda da secção
SURFACES = {'sand': 0, 'slickrock': 1, 'gravel': 2, 'rock': 3, 'deepsand': 4}
PAL_SAND = 12


# ------------------------------------------------------------------ 1. eixo do percurso

def integrate(spec):
    d = spec['defaults']
    step = float(spec.get('step', 3.0))
    cur = {k: float(d.get(k, 0.0)) for k in EASED if k != 'curv'}
    r0 = float(d.get('radius', 0.0))
    cur['curv'] = 0.0 if r0 == 0 else 1.0 / r0
    surface = d.get('surface', 'sand')
    pos = np.array(spec['start']['pos'], dtype=np.float64)
    yaw = math.radians(spec['start'].get('yaw', 0.0))
    rows = []

    def push(vals, seg, gap, cave, surf, dist, natural=True):
        rows.append(dict(vals, pos=pos.copy(), seg=seg, gap=gap, cave=cave, surf=SURFACES.get(surf, 0), dist=dist, natural=natural))

    push(cur, 0, 0, 0, surface, 0.0, spec['segments'][0].get('floor', 'natural') == 'natural')
    dist = 0.0
    for si, seg in enumerate(spec['segments']):
        target = dict(cur)
        for k in EASED:
            if k == 'curv':
                if 'radius' in seg:
                    target['curv'] = 0.0 if float(seg['radius']) == 0 else 1.0 / float(seg['radius'])
            elif k in seg:
                target[k] = float(seg[k])
        surface = seg.get('surface', surface)
        floor_kind = seg.get('floor', 'natural')
        gap, cave = int(seg.get('gap', 0)), int(seg.get('cave', 0))
        ease = float(seg.get('ease', 120.0))
        length = float(seg['len'])
        if 'to_y' in seg:
            # inclinação para chegar à altitude pedida no fim do troço (conta com a suavização da entrada)
            e = min(ease, length) if ease > 0 else 0.0
            s0 = math.radians(cur['slope'])
            sin1 = (float(seg['to_y']) - pos[1] - math.sin(s0) * e * 0.5) / max(1.0, length - e * 0.5)
            target['slope'] = math.degrees(math.asin(max(-0.5, min(0.5, sin1))))
        start = dict(cur)
        n = max(1, int(round(length / step)))
        ds = length / n
        for k in range(n):
            t_mid, t_end = (k + 0.5) * ds, (k + 1) * ds
            e_mid = 1.0 if ease <= 0 else float(geo.smoothstep(0.0, ease, t_mid))
            e_end = 1.0 if ease <= 0 else float(geo.smoothstep(0.0, ease, t_end))
            curv = start['curv'] + (target['curv'] - start['curv']) * e_mid
            slope = start['slope'] + (target['slope'] - start['slope']) * e_mid
            yaw += curv * ds
            pitch = math.radians(slope)
            pos += np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)]) * ds
            dist += ds
            push({kk: start[kk] + (target[kk] - start[kk]) * e_end for kk in EASED}, si, gap, cave, surface, dist, floor_kind == 'natural')
        cur = target
    log(f"eixo: {len(rows)} estações, {dist / 1000.0:.2f} km")
    return rows, step


def frames(rows):
    P = np.array([r['pos'] for r in rows])
    Tc = np.zeros_like(P)
    Tc[1:-1] = P[2:] - P[:-2]; Tc[0] = P[1] - P[0]; Tc[-1] = P[-1] - P[-2]
    Tc /= np.linalg.norm(Tc, axis=1, keepdims=True)
    R0 = np.cross(np.array([0.0, 1.0, 0.0]), Tc)
    R0 /= np.linalg.norm(R0, axis=1, keepdims=True)
    U0 = np.cross(Tc, R0)
    bank = np.radians(np.array([r['bank'] for r in rows]))
    c, s = np.cos(bank)[:, None], np.sin(bank)[:, None]
    return P, Tc, R0 * c - U0 * s, U0 * c + R0 * s


def half_profile(W, H, r, ang, lip):
    half = W * 0.5
    fs = np.linspace(0.0, half, KF + 1)
    th = math.radians(max(1.0, min(ang, 89.0)))
    r = max(r, 0.5)
    h_arc = r * (1.0 - math.cos(th))
    if H <= h_arc:
        phi, straight = math.acos(max(-1.0, 1.0 - H / r)), 0.0
    else:
        phi, straight = th, (H - h_arc) / math.sin(th)
    arc = r * phi
    total = arc + straight
    t = np.linspace(0.0, total, KW + 1)[1:]
    on = t <= arc
    ws = np.where(on, half + r * np.sin(np.minimum(t, arc) / r), half + r * math.sin(phi) + (t - arc) * math.cos(phi))
    wh = np.where(on, r * (1.0 - np.cos(np.minimum(t, arc) / r)), r * (1.0 - math.cos(phi)) + (t - arc) * math.sin(phi))
    ls = ws[-1] + np.linspace(0.0, lip, KL + 1)[1:]
    return np.concatenate([fs, ws, ls]), np.concatenate([np.zeros(KF + 1), wh, np.full(KL, wh[-1])]), total


def build_ring(rows):
    S = len(rows)
    N = 2 * (KF + KW + KL) + 1
    loc = np.zeros((S, N, 2))
    ride = np.zeros((S, 2))
    for i, r in enumerate(rows):
        sR, hR, totR = half_profile(r['width'], r['wallR'], r['filletR'], r['angleR'], r['lipR'])
        sL, hL, totL = half_profile(r['width'], r['wallL'], r['filletL'], r['angleL'], r['lipL'])
        loc[i, :, 0] = np.concatenate([-sL[::-1], sR[1:]])
        loc[i, :, 1] = np.concatenate([hL[::-1], hR[1:]])
        ride[i, 0] = r['width'] * 0.5 + np.clip(r['rideL'], 0, 1) * totL
        ride[i, 1] = r['width'] * 0.5 + np.clip(r['rideR'], 0, 1) * totR
    return loc, ride, N


def natural_floor(rows, loc, seed):
    """
    Leito natural (sem "estrada"): canal de areia com meandros, bancadas de slickrock com degraus que serpenteiam,
    buracos, pequenas quedas transversais nas bancadas, areia funda no canal e cascalho junto às paredes.
    Devolve a secção com o relevo, a classe de superfície por vértice e a máscara do leito.
    """
    S, N, _ = loc.shape
    c = N // 2
    fi = np.arange(c - KF, c + KF + 1)
    dist = np.array([r['dist'] for r in rows])
    nat = np.array([1.0 if r.get('natural', True) else 0.0 for r in rows])
    # transição suave entre leito plano e natural
    k = 30
    nat_s = np.convolve(np.pad(nat, k, mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k]
    W = np.array([r['width'] for r in rows])
    sF = loc[:, fi, 0]
    half = W[:, None] / 2.0
    Wc = np.clip(0.3 * W, 14.0, 34.0)[:, None]
    m = geo.fbm2(dist / 380.0, np.full(S, 0.37), 3, seed=seed + 62)[:, None] * 1.4
    lim = np.maximum(0.0, half - Wc / 2 - 5.0)
    cc = np.clip(m * lim, -lim, lim)
    Dc = 1.0 + 1.2 * (0.5 + 0.5 * geo.fbm2(dist / 260.0, np.full(S, 1.7), 2, seed=seed + 63))[:, None]
    rel = np.abs(sF - cc)
    channel = -Dc * (1.0 - geo.smoothstep(0.55, 1.0, rel / (Wc / 2)))
    e = np.maximum(0.0, rel - Wc / 2)                        # distância à margem do canal (bancadas)
    side = np.sign(sF - cc)
    def nz(sc, sd):
        return 0.5 + 0.5 * geo.fbm2(dist[:, None] / sc + 0.0 * sF, side * 0.73 + sd, 2, seed=seed + int(sd * 10))
    e1 = 4.0 + 10.0 * nz(170.0, 1.1); h1 = 0.5 + 1.2 * nz(240.0, 2.3)
    e2 = e1 + 6.0 + 12.0 * nz(210.0, 3.7); h2 = 0.4 + 1.0 * nz(300.0, 4.1)
    ledges = h1 * geo.smoothstep(e1 - 0.8, e1 + 0.8, e) + h2 * geo.smoothstep(e2 - 0.8, e2 + 0.8, e)
    bench = geo.smoothstep(0.0, 3.0, e)
    # quedas transversais curtas nas bancadas (saltos de ritmo), lado alternado
    drops = np.zeros_like(sF)
    rng = np.random.default_rng(seed + 64)
    d0 = 260.0
    while d0 < dist[-1] - 200.0:
        sd = 1.0 if rng.random() < 0.5 else -1.0
        drop = rng.uniform(1.0, 1.9)
        prof = geo.smoothstep(d0 - 1.2, d0 + 1.2, dist) - geo.smoothstep(d0 + 4.0, d0 + 90.0, dist)
        drops += -drop * prof[:, None] * (side == sd) * bench
        d0 += rng.uniform(280.0, 620.0)
    x = loc[:, fi, 0]
    pot = -0.55 * geo.smoothstep(0.6, 0.85, 0.5 + 0.5 * geo.fbm2(dist[:, None] / 14.0 + 0.0 * x, x / 14.0, 2, seed=seed + 65)) * bench
    # leitos estreitos (fundo de half-pipe, curvas inclinadas) não têm bancadas: só canal suave
    wide = geo.smoothstep(38.0, 60.0, W)[:, None]
    narrow_ch = np.clip((W - 18.0) / 40.0, 0.25, 1.0)[:, None]
    hF = (channel * narrow_ch + (ledges + drops + pot) * wide) * nat_s[:, None]
    # classes de superfície do leito
    deep = (0.5 + 0.5 * geo.fbm2(dist[:, None] / 90.0 + 0.0 * x, x / 22.0, 2, seed=seed + 66) > 0.68) & (rel < Wc / 2 * 0.9)
    near_wall = np.abs(sF) > half - 6.0
    ledge_band = (np.abs(e - e1) < 1.3) | (np.abs(e - e2) < 1.3)
    clsF = np.where(rel < Wc / 2 * 0.95, np.where(deep, 0.125, 0.0), 0.25)
    clsF = np.where(ledge_band & (rel >= Wc / 2) & (wide > 0.5), 0.625, clsF)
    clsF = np.where(near_wall, 0.375, clsF)
    clsF = np.where(nat_s[:, None] < 0.5, np.where(rows_surf(rows)[:, None] == 1, 0.25, 0.0), clsF)
    out = loc.copy()
    out[:, fi, 1] += hF
    # paredes e bordas começam à altura da bancada na margem
    out[:, :c - KF, 1] += hF[:, 0:1]
    out[:, c + KF + 1:, 1] += hF[:, -1:]
    cls = np.full((S, N), 0.5)
    cls[:, fi] = clsF
    floor_mask = np.zeros((S, N), bool)
    floor_mask[:, fi] = True
    return out, cls, floor_mask


def rows_surf(rows):
    return np.array([r['surf'] for r in rows])


def arc_from_center(loc):
    S, N, _ = loc.shape
    seg = np.linalg.norm(np.diff(loc, axis=1), axis=2)
    cum = np.concatenate([np.zeros((S, 1)), np.cumsum(seg, axis=1)], axis=1)
    return cum - cum[:, N // 2:N // 2 + 1]


def sculpt(rows, P, R, U, loc, ride, col, joints, seed, floor_cls=None, floor_mask=None,
           erosion_m=26.0, erosion_seed=7):
    """Secção de corrida: leito (areia/slickrock) e paredes polidas na zona de corrida; rocha estratificada acima.

    erosion_m: amplitude da erosão 3D nas paredes de rocha (0 desliga e volta ao aspeto anterior).
    Ver erode3d() para as escalas e porque é que a dureza da camada controla a amplitude.
    """
    S, N, _ = loc.shape
    W = P[:, None, :] + R[:, None, :] * loc[..., 0:1] + U[:, None, :] * loc[..., 1:2]
    arc = arc_from_center(loc)
    d = np.zeros_like(loc)
    d[:, 1:-1] = loc[:, 2:] - loc[:, :-2]; d[:, 0] = loc[:, 1] - loc[:, 0]; d[:, -1] = loc[:, -1] - loc[:, -2]
    d /= np.maximum(np.linalg.norm(d, axis=2, keepdims=True), 1e-6)
    Nw = R[:, None, :] * (-d[..., 1])[..., None] + U[:, None, :] * d[..., 0][..., None]
    dist = np.array([r['dist'] for r in rows])[:, None] * np.ones((1, N))
    x, y, z = W[..., 0], W[..., 1], W[..., 2]
    surf = np.array([r['surf'] for r in rows])[:, None] * np.ones((1, N))
    lim = np.where(arc < 0, ride[:, 0:1], ride[:, 1:2])
    rock = geo.smoothstep(lim, lim + 7.0, np.abs(arc))
    floor = floor_mask.astype(float) if floor_mask is not None else 1.0 - geo.smoothstep(0.0, 1.5, np.abs(loc[..., 1]))
    swell = geo.fbm2(x / 190.0, z / 190.0, 3, seed=seed + 11)
    disp = floor * (1.0 - rock) * (0.28 + 0.12 * (surf == 1)) * swell
    disp += (1.0 - floor) * (1.0 - rock) * 0.22 * geo.fbm2(x / 70.0 + dist / 300.0, y / 40.0, 2, seed=seed + 12)
    relief, hard, pa, pb, mix, _ = col.sample(x, y, z)
    jr = joints.recess(dist, y)
    rough = geo.fbm3(x / 9.0, y / 6.0, z / 9.0, 3, seed=seed + 13)
    # EROSÃO das paredes: recuo dependente da dureza da camada, em três eixos. Substitui o
    # micro-relevo de 0,45 m por recuos de vários metros a dezenas de metros, que é o que se lê
    # a 100 m/s e ao longo de quilómetros. Aplicado a toda a altura da parede (não só ao pé,
    # que era o limite do wall_warp).
    if erosion_m > 0.0:
        wall_u = np.clip((y - y.min()) / max(1.0, float(y.max() - y.min())), 0.0, 1.0)
        erosion = erode3d(y, dist, wall_u, hard, amount=erosion_m, seed=erosion_seed)
    else:
        erosion = 0.0
    disp += rock * (1.15 * relief - 1.6 * jr + 0.45 * rough + erosion)
    # bordas exteriores sem deslocamento (encaixe com a parede próxima)
    edge = np.ones((1, N)); edge[0, :2] = 0.0; edge[0, -2:] = 0.0
    W = W + Nw * (disp * edge)[..., None]
    # cores: classe, paleta A/B; leito = areia por cima da rocha local
    cls = np.where(rock > 0.5, 0.75, np.where(floor > 0.5, np.where(surf == 1, 0.25, 0.0), 0.5))
    if floor_cls is not None:
        cls = np.where(floor > 0.5, floor_cls, cls)
    pa = np.where((floor > 0.5) & ((cls < 0.2) | (np.abs(cls - 0.375) < 0.05)), PAL_SAND, pa)
    return W, arc, rock, cls, pa, pb, mix, hard


# ------------------------------------------------------------------ 2. paisagem: linhas de canyon

def wall_warp(along, dperp, seed):
    """Deslocamento horizontal das paredes (alcovas e esporões), partilhado entre terreno e paredes próximas."""
    return (45.0 * geo.fbm2(np.asarray(along) / 90.0 + 0.37 * (seed % 97), np.asarray(dperp) / 150.0, 3, seed=seed + 3)
            + 70.0 * geo.fbm2(np.asarray(along) / 420.0, np.full(np.shape(along), 0.5), 2, seed=seed + 4))


# ------------------------------------------------------------------ erosão das paredes
#
# Portado de LabGeometry.Erode3D (Assets/RedDust/Runtime/Lab), onde foi validado com
# Tools/verifica_detrito.py. O laboratório gera malhas planas em C#; aqui a mesma matemática
# corre sobre os anéis 3D da rota, que é o que faz a pista REAL ganhar o mesmo aspeto.
#
# Porque é preciso: o perfil da coluna (rdd_geology.Column) constrói a parede em SEGMENTOS
# RETOS (recuo = espessura / tan(ângulo) + bancada) e o `wall_warp` só mexe no pé (limitado a
# 70 m). O `relief` de Column.sample alimentava apenas o micro-relevo do shader (≤ 0,75 m).
# Resultado: paredes lisas ao longo de 105 km.
#
# As escalas são divididas DIRETAMENTE pelas distâncias em metros. Multiplicar a altura por um
# fator empurrava a coordenada de ruído para valores altos e saturava o ruído — o erro que dava
# riscas verticais uniformes em vez de manchas e fissuras.

def erode3d(height, along, wall_u, hardness, amount=26.0, seed=7):
    """
    Recuo de erosão (m) por ponto da parede, na direção da normal da superfície.

    Quatro escalas, todas a puxar para dentro (positivo = recuo):
      alcova   ~120 m ao longo, ~90 m em altura  — recessos grandes e sombrios
      fluting  ~18 m / ~14 m                     — canais verticais de arenito
      rachadura ~5 m / ~4 m                      — fissuras isoladas
      lasca    ~1,2 m                            — irregularidade fina

    A dureza da camada controla a amplitude: mole (Chinle 0,15) recua muito, dura
    (Wingate 0,97) resiste e sobressai como cornija.

    ATENÇÃO: `seed` tem de ser INTEIRO. O _hash do rdd_geology faz
    `(seed * 0x9E3779B1) & 0xFFFFFFFF` e rebenta com TypeError se for float.
    Por isso é convertido aqui, o que também protege contra `erosion_seed` float vindo
    do spec.json.
    """
    seed = int(seed)
    height = np.asarray(height, dtype=np.float64)
    along = np.asarray(along, dtype=np.float64)
    wall_u = np.asarray(wall_u, dtype=np.float64)
    hardness = np.asarray(hardness, dtype=np.float64)
    soft = np.clip(1.0 - hardness, 0.0, 1.0)
    by_hardness = amount * soft ** 1.6
    alcove = geo.fbm3(along / 120.0, height / 90.0, wall_u * 1.1, 3, seed=seed)
    flute = geo.fbm3(along / 18.0, height / 14.0, wall_u * 1.7, 3, seed=seed + 101)
    crack = geo.fbm3(along / 5.0, height / 4.0, wall_u * 2.3, 3, seed=seed + 211)
    chip = geo.fbm3(along / 1.2, height / 1.2, wall_u * 3.1, 2, seed=seed + 307)
    depth = 0.62 * alcove + 0.34 * flute + 0.24 * crack + 0.12 * chip
    # ATENÇÃO à convenção do ruído: o fbm3 do rdd_geology está centrado em ZERO e vai de
    # -0,67 a +0,69 (usa _G3 e floor, não frac). NÃO é 0..1 como o rd_noise do shader.
    # Logo `depth` também é bidirecional (medido: -0,553 a +0,599, mediana 0,003).
    #
    # Cortar em zero escolhe deliberadamente só o lado POSITIVO = só recuo. Assim a erosão
    # nunca projeta para dentro do corredor e a largura útil da pista jamais diminui — o que
    # importa porque as larguras do design (e as medições da Fase 1) contam com elas.
    # O /0,60 normaliza: depth chega a ~0,599, logo o recuo máximo fica em `amount`.
    depth = np.maximum(0.0, depth) / 0.60
    # o recuo acumula pela face: mais fundo a meio da parede do que junto ao pé (detrito) ou ao topo
    by_face = 0.55 + 0.65 * np.sin(wall_u * np.pi)
    return by_hardness * by_face * depth


def talus_profile(talus_h, talus_extent, clear_half_width, along, seed=909, segs=None):
    """
    Cone de detrito no pé da parede: devolve (run, height) dos pontos do cone.

    Nos canyons reais acumula-se entulho no sopé. Sem ele a parede nasce a pique do chão, o que
    é metade do aspeto de "tubo". O cone sobe EM DIREÇÃO à parede (0 no corredor, talus_h no pé)
    e nunca entra na zona livre, para a largura útil do corredor não diminuir.
    """
    if talus_h <= 0.5:
        return np.zeros(1), np.zeros(1)
    if segs is None:
        segs = int(np.clip(talus_h / 1.5, 4, 28))
    t = np.linspace(0.0, 1.0, int(segs) + 1)
    run = clear_half_width + np.maximum(1.0, talus_extent - clear_half_width) * t
    height = talus_h * (1.0 - t) ** 0.85
    bumpy = (geo.fbm2(along / 20.0 + np.zeros_like(t), t * 3.0, 2, seed=seed) - 0.5) * 2.0
    run = np.maximum(clear_half_width, run + bumpy * 1.2 * t)
    return run, height


class CanyonLine:
    """
    Linha de drenagem/canyon. Para cada ponto: posição (x, z), elevação do pé da parede de cada lado, meia-largura
    de cada lado. kind='course': sob o corredor o terreno fica escondido; 'side'/'gorge': o leito é terreno.
    end_planes: (ponto, normal) — além do plano o canyon termina (boca de caverna / fim abrupto).
    """

    def __init__(self, xz, footL, footR, hwL, hwR, kind, seed, end_planes=(), skirtL=None, skirtR=None, floor=None, along=None,
                 apron=None):
        self.xz = np.asarray(xz, dtype=np.float64)
        n0 = len(self.xz)
        # apron: faixa plana ao nível da borda da pista antes de as falésias começarem (bacias e bancadas abertas)
        self.apron = np.asarray(apron if apron is not None else np.zeros(n0), float)
        self.skirtL = np.asarray(skirtL if skirtL is not None else np.zeros(n0), float)
        self.skirtR = np.asarray(skirtR if skirtR is not None else np.zeros(n0), float)
        self.footL, self.footR = np.asarray(footL, float), np.asarray(footR, float)
        self.hwL, self.hwR = np.asarray(hwL, float), np.asarray(hwR, float)
        self.floor = np.asarray(floor if floor is not None else np.minimum(footL, footR), float)
        self.kind, self.seed = kind, seed
        self.end_planes = list(end_planes)
        t = np.zeros_like(self.xz)
        t[1:-1] = self.xz[2:] - self.xz[:-2]; t[0] = self.xz[1] - self.xz[0]; t[-1] = self.xz[-1] - self.xz[-2]
        self.tan = t / np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
        self.along = np.asarray(along, float) if along is not None else np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(self.xz, axis=0), axis=1))])
        self.kd = kdtree.KDTree(len(self.xz))
        for i, (px, pz) in enumerate(self.xz):
            self.kd.insert((px, pz, 0.0), i)
        self.kd.balance()
        reach = float(np.max(np.maximum(self.hwL, self.hwR))) + 700.0
        self.bbox = (self.xz[:, 0].min() - reach, self.xz[:, 0].max() + reach, self.xz[:, 1].min() - reach, self.xz[:, 1].max() + reach)

    def heights(self, x, z, col, out, lowered):
        """Atualiza out = min(out, altura do canyon) nos pontos dentro da caixa; marca 'lowered' sob o corredor."""
        b = self.bbox
        m = (x >= b[0]) & (x <= b[1]) & (z >= b[2]) & (z <= b[3])
        idx = np.nonzero(m.ravel())[0]
        if len(idx) == 0:
            return
        fx, fz = x.ravel()[idx], z.ravel()[idx]
        near = np.empty(len(idx), np.int64); dist = np.empty(len(idx))
        for k in range(len(idx)):
            co, j, dd = self.kd.find((fx[k], fz[k], 0.0))
            near[k] = j; dist[k] = dd
        dx, dz = fx - self.xz[near, 0], fz - self.xz[near, 1]
        tx, tz = self.tan[near, 0], self.tan[near, 1]
        lateral = tx * dz - tz * dx            # >0: à esquerda do sentido de avanço (x direita, z frente)
        alongoff = dx * tx + dz * tz
        left = lateral > 0
        hw = np.where(left, self.hwL[near], self.hwR[near])
        foot = np.where(left, self.footL[near], self.footR[near])
        dperp = dist
        xoff = dperp - hw
        skirt = np.where(left, self.skirtL[near], self.skirtR[near])
        # alcovas, esporões e reentrâncias ao longo das paredes
        xeff = xoff + wall_warp(self.along[near], dperp, self.seed) * geo.smoothstep(0.0, 70.0, xoff)
        h = col.height_from(foot, xeff)
        if self.kind == 'course' and self.apron.any():
            apr = self.apron[near]
            has = apr > 1.0
            if has.any():
                xa = xoff - apr
                xeff_a = xa + wall_warp(self.along[near], dperp, self.seed) * geo.smoothstep(0.0, 70.0, xa)
                h_out = col.height_from(foot, xeff_a)
                h_ap = foot + 0.9 * geo.fbm2(fx / 70.0, fz / 70.0, 2, seed=self.seed + 5) + 0.4
                h = np.where(has, np.where(xoff < apr, h_ap, h_out), h)
        if self.kind == 'course':
            under = (skirt > 0.0) & (xoff < skirt + 4.0)
            h = np.where(xoff <= 0.0, self.floor[near] - 12.0, h)
            h = np.where(under & (xoff > 0.0), h - 9.0, h)
            low = under
        else:
            h = np.where(xoff <= 0.0, self.floor[near] + 0.3 * geo.fbm2(fx / 40.0, fz / 40.0, 2, seed=self.seed), h)
            low = np.zeros(len(idx), bool)
        # extremidades: além dos planos finais o canyon não existe
        for (pp, nn) in self.end_planes:
            beyond = (fx - pp[0]) * nn[0] + (fz - pp[1]) * nn[1] > 0.0
            h = np.where(beyond, np.inf, h)
            low &= ~beyond
        flat = out.ravel()
        cur = flat[idx]
        better = h < cur
        flat[idx] = np.where(better, h, cur)
        if lowered is not None:
            lf = lowered.ravel()
            lf[idx] = lf[idx] | (low & better)


def plateau(x, z, col, course_dist, seed):
    """Topo do planalto: cúpulas de Navajo, planícies de areia, mesas de Entrada ao longe."""
    x = np.asarray(x, float); z = np.asarray(z, float)
    base = 318.0 + 9.0 * geo.fbm2(x / 1400.0, z / 1400.0, 4, seed=seed + 31)
    domes = 34.0 * np.clip(geo.fbm2(x / 230.0, z / 230.0, 3, seed=seed + 32) * 1.6, 0.0, 1.0) ** 1.6
    sandflat = -4.0 * geo.smoothstep(0.1, 0.5, geo.fbm2(x / 500.0, z / 500.0, 2, seed=seed + 33))
    h = base + domes + sandflat
    wx = x + 600.0 * geo.fbm2(x / 3500.0, z / 3500.0, 3, seed=seed + 34)
    wz = z + 600.0 * geo.fbm2(x / 3500.0 + 3.3, z / 3500.0, 3, seed=seed + 35)
    m = geo.fbm2(wx / 5200.0, wz / 5200.0, 4, seed=seed + 36)
    inset = (m - 0.16) * 3200.0
    mesa = col.height_from(np.full(np.shape(x), 330.0), inset)
    keep = geo.smoothstep(1100.0, 1900.0, course_dist)
    out = np.where(inset > 0.0, h + (np.maximum(mesa, h) - h) * keep, h)
    for fld in OPEN_FIELDS:
        out = fld.apply(x, z, out)
    return out


# ------------------------------------------------------------------ 3. malhas

class MeshOut:
    """Malha em coordenadas Unity com normais, cores (RGBA) e duas UVs; triangulada antes de exportar."""

    def __init__(self, name):
        self.name = name
        self.v, self.n, self.c, self.uv, self.uv2, self.f, self.t = [], [], [], [], [], [], []
        self.count = 0

    def add_tris(self, pts, nrm, col, uv, uv2, tris):
        """Triângulos soltos (recortes das junções): vértices (n, …) e índices locais (m, 3)."""
        if len(tris) == 0:
            return
        base = self.count
        self.v.append(np.asarray(pts).reshape(-1, 3)); self.n.append(np.asarray(nrm).reshape(-1, 3))
        self.c.append(np.asarray(col).reshape(-1, 4)); self.uv.append(np.asarray(uv).reshape(-1, 2)); self.uv2.append(np.asarray(uv2).reshape(-1, 2))
        self.count += len(pts)
        self.t.append(np.asarray(tris, np.int64).reshape(-1, 3) + base)

    def add_grid(self, pts, nrm, col, uv, uv2, skip=None, flip=False, adaptive=False, skipq=None):
        A, B, _ = pts.shape
        base = self.count
        self.v.append(pts.reshape(-1, 3)); self.n.append(nrm.reshape(-1, 3))
        self.c.append(col.reshape(-1, 4)); self.uv.append(uv.reshape(-1, 2)); self.uv2.append(uv2.reshape(-1, 2))
        self.count += A * B
        ia, ib = np.meshgrid(np.arange(A - 1), np.arange(B - 1), indexing='ij')
        q = np.stack([ia * B + ib, ia * B + ib + 1, (ia + 1) * B + ib + 1, (ia + 1) * B + ib], axis=-1)
        if adaptive:
            # diagonal que liga os cantos de altura mais parecida: os triângulos seguem as curvas de nível
            yv = pts[..., 1].reshape(-1)
            d02 = np.abs(yv[q[..., 0]] - yv[q[..., 2]])
            d13 = np.abs(yv[q[..., 1]] - yv[q[..., 3]])
            rot = d13 < d02
            q = np.where(rot[..., None], np.roll(q, -1, axis=-1), q)
        keep = np.ones(q.shape[:2], bool)
        if skip is not None:
            keep &= ~skip[:A - 1][:, None]
        if skipq is not None:
            keep &= ~skipq
        q = q[keep]
        q = q.reshape(-1, 4) + base
        if flip:
            q = q[:, ::-1]
        self.f.append(q)

    def empty(self):
        return self.count == 0 or sum(len(f) for f in self.f) + sum(len(t) for t in self.t) == 0

    def to_object(self, collection):
        V = np.concatenate(self.v); Nn = np.concatenate(self.n); C = np.concatenate(self.c)
        UV = np.concatenate(self.uv); UV2 = np.concatenate(self.uv2)
        F = np.concatenate(self.f) if self.f else np.zeros((0, 4), np.int64)
        Tt = np.concatenate(self.t) if self.t else np.zeros((0, 3), np.int64)
        used = np.zeros(len(V), bool); used[F.ravel()] = True; used[Tt.ravel()] = True
        remap = -np.ones(len(V), np.int64); remap[used] = np.arange(used.sum())
        V, Nn, C, UV, UV2 = V[used], Nn[used], C[used], UV[used], UV2[used]
        F = remap[F]; Tt = remap[Tt]
        F = np.concatenate([F[:, [0, 1, 2]], F[:, [0, 2, 3]], Tt], axis=0)    # triangulação própria (preserva normais)
        Vb, Nb = V[:, [0, 2, 1]], Nn[:, [0, 2, 1]]
        me = bpy.data.meshes.new(self.name)
        me.vertices.add(len(Vb))
        me.vertices.foreach_set("co", Vb.astype(np.float32).ravel())
        nf = len(F)
        me.loops.add(nf * 3)
        me.loops.foreach_set("vertex_index", F.astype(np.int32).ravel())
        me.polygons.add(nf)
        me.polygons.foreach_set("loop_start", (np.arange(nf) * 3).astype(np.int32))
        me.update(calc_edges=True)
        li = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get("vertex_index", li)
        for name, data in (("UVMap", UV), ("UV2", UV2)):
            uvl = me.uv_layers.new(name=name)
            uvl.data.foreach_set("uv", data[li].astype(np.float32).ravel())
        ca = me.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')
        ca.data.foreach_set("color", C.astype(np.float32).ravel())
        me.polygons.foreach_set("use_smooth", np.ones(nf, dtype=bool))
        nn = Nb / np.maximum(np.linalg.norm(Nb, axis=1, keepdims=True), 1e-9)
        me.normals_split_custom_set_from_vertices(nn.astype(np.float32).tolist())
        mat = bpy.data.materials.get("Geology") or bpy.data.materials.new("Geology")
        me.materials.append(mat)
        ob = bpy.data.objects.new(self.name, me)
        collection.objects.link(ob)
        return ob, len(Vb), nf


def grid_normals(G):
    da = np.zeros_like(G); db = np.zeros_like(G)
    da[1:-1] = G[2:] - G[:-2]; da[0] = G[1] - G[0]; da[-1] = G[-1] - G[-2]
    db[:, 1:-1] = G[:, 2:] - G[:, :-2]; db[:, 0] = G[:, 1] - G[:, 0]; db[:, -1] = G[:, -1] - G[:, -2]
    n = np.cross(da, db)
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)


def colors(cls, pa, pb, ride):
    return np.stack([cls, np.asarray(pa, float) / 15.0, np.asarray(pb, float) / 15.0, ride], axis=-1)


def resample(poly, n):
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    cum = np.r_[0, np.cumsum(seg)]
    tq = np.linspace(0, cum[-1], n)
    return np.stack([np.interp(tq, cum, poly[:, k]) for k in range(poly.shape[1])], axis=1)


