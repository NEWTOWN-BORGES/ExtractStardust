"""
EXTRACT: STARDUST — RED DUST DIVIDE · construtor de percursos e paisagem (Blender, modo batch).

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

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if len(ARGS) < 2:
    raise SystemExit("uso: blender -b -P rdd_build_course.py -- spec.json pasta_saida")
SPEC_PATH, OUT_DIR = os.path.abspath(ARGS[0]), os.path.abspath(ARGS[1])
os.makedirs(OUT_DIR, exist_ok=True)
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
         'lipL', 'lipR', 'rideL', 'rideR', 'ceil']
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


# ------------------------------------------------------------------ erosão das paredes
#
# Portado de LabGeometry.Erode3D (Assets/RedDust/Runtime/Lab), validado com
# Tools/verifica_detrito.py. Mantido em sincronia com rdd_route_lib.py — este ficheiro tem a
# mesma matemática duplicada e não é importado pelo pipeline atual (o rdd_build_route usa o
# rdd_route_lib), mas alinhar os dois evita divergência silenciosa.
#
# Porque é preciso: o perfil da coluna (rdd_geology.Column) constrói a parede em SEGMENTOS
# RETOS (recuo = espessura / tan(ângulo) + bancada) e o wall_warp só mexe no pé (limitado a
# 70 m). O relief de Column.sample alimentava apenas o micro-relevo do shader (≤ 0,75 m).
# Resultado: paredes lisas ao longo de 105 km.

def erode3d(height, along, wall_u, hardness, amount=26.0, seed=7):
    """
    Recuo de erosão (m) por ponto da parede, na direção da normal da superfície.

    Quatro escalas: alcova ~120 m, fluting ~18 m, rachadura ~5 m, lasca ~1,2 m.
    A dureza da camada controla a amplitude: mole (Chinle 0,15) recua muito, dura
    (Wingate 0,97) resiste e sobressai como cornija.

    ATENÇÃO: `seed` tem de ser INTEIRO. O _hash do rdd_geology faz
    (seed * 0x9E3779B1) & 0xFFFFFFFF e rebenta com TypeError se for float.
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
    # Soma ponderada das quatro escalas. Os pesos somam 1,32 de propósito: dá alcance para o
    # máximo da perturbação chegar perto do fim da escala depois de cortada em zero.
    depth = 0.62 * alcove + 0.34 * flute + 0.24 * crack + 0.12 * chip
    # ATENÇÃO à convenção do ruído: o fbm3 do rdd_geology está centrado em ZERO e vai de
    # -0,67 a +0,69 (usa _G3 e floor, não frac). NÃO é 0..1 como o rd_noise do shader.
    # Logo depth também é bidirecional (medido: -0,553 a +0,599, mediana 0,003).
    #
    # Cortar em zero escolhe só o lado POSITIVO = só recuo: a erosão nunca projeta para dentro
    # do corredor, logo a largura útil da pista jamais diminui. O /0,60 normaliza.
    depth = np.maximum(0.0, depth) / 0.60
    # o recuo acumula pela face: mais fundo a meio da parede do que junto ao pé ou ao topo
    by_face = 0.55 + 0.65 * np.sin(wall_u * np.pi)
    return by_hardness * by_face * depth


def talus_profile(talus_h, talus_extent, clear_half_width, along, seed=909, segs=None):
    """
    Cone de detrito no pé da parede: devolve (run, height) dos pontos do cone.

    Sobe EM DIREÇÃO à parede (0 no corredor, talus_h no pé) e nunca entra na zona livre.
    """
    if talus_h <= 0.5:
        return np.zeros(1), np.zeros(1)
    if segs is None:
        segs = int(np.clip(talus_h / 1.5, 4, 28))
    t = np.linspace(0.0, 1.0, int(segs) + 1)
    run = clear_half_width + np.maximum(1.0, talus_extent - clear_half_width) * t
    height = talus_h * (1.0 - t) ** 0.85
    bumpy = (geo.fbm2(along / 20.0 + np.zeros_like(t), t * 3.0, 2, seed=int(seed)) - 0.5) * 2.0
    run = np.maximum(clear_half_width, run + bumpy * 1.2 * t)
    return run, height


def sculpt(rows, P, R, U, loc, ride, col, joints, seed, floor_cls=None, floor_mask=None,
           erosion_m=26.0, erosion_seed=7):
    """Secção de corrida: leito (areia/slickrock) e paredes polidas na zona de corrida; rocha estratificada acima.

    erosion_m: amplitude da erosão 3D nas paredes de rocha (0 desliga e volta ao aspeto anterior).
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
    # a 100 m/s e ao longo de quilómetros. Aplicado a toda a altura (não só ao pé, que era o
    # limite do wall_warp).
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


class CanyonLine:
    """
    Linha de drenagem/canyon. Para cada ponto: posição (x, z), elevação do pé da parede de cada lado, meia-largura
    de cada lado. kind='course': sob o corredor o terreno fica escondido; 'side'/'gorge': o leito é terreno.
    end_planes: (ponto, normal) — além do plano o canyon termina (boca de caverna / fim abrupto).
    """

    def __init__(self, xz, footL, footR, hwL, hwR, kind, seed, end_planes=(), skirtL=None, skirtR=None, floor=None, along=None):
        self.xz = np.asarray(xz, dtype=np.float64)
        n0 = len(self.xz)
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
    return np.where(inset > 0.0, h + (np.maximum(mesa, h) - h) * keep, h)


# ------------------------------------------------------------------ 3. malhas

class MeshOut:
    """Malha em coordenadas Unity com normais, cores (RGBA) e duas UVs; triangulada antes de exportar."""

    def __init__(self, name):
        self.name = name
        self.v, self.n, self.c, self.uv, self.uv2, self.f = [], [], [], [], [], []
        self.count = 0

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
        return self.count == 0 or sum(len(f) for f in self.f) == 0

    def to_object(self, collection):
        V = np.concatenate(self.v); Nn = np.concatenate(self.n); C = np.concatenate(self.c)
        UV = np.concatenate(self.uv); UV2 = np.concatenate(self.uv2); F = np.concatenate(self.f)
        used = np.zeros(len(V), bool); used[F.ravel()] = True
        remap = -np.ones(len(V), np.int64); remap[used] = np.arange(used.sum())
        V, Nn, C, UV, UV2 = V[used], Nn[used], C[used], UV[used], UV2[used]
        F = remap[F]
        F = np.concatenate([F[:, [0, 1, 2]], F[:, [0, 2, 3]]], axis=0)    # triangulação própria (preserva normais)
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


# ------------------------------------------------------------------ 4. construção

def main():
    spec = json.load(open(SPEC_PATH, encoding='utf-8'))
    name = spec['name']
    seed = int(spec.get('seed', 1))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    col_corr = bpy.data.collections.new("Corridor"); scene.collection.children.link(col_corr)
    col_terr = bpy.data.collections.new("Terrain"); scene.collection.children.link(col_terr)

    rows, step = integrate(spec)
    S = len(rows)
    P, T, R, U = frames(rows)
    loc, ride, N = build_ring(rows)
    loc, floor_cls, floor_mask = natural_floor(rows, loc, seed)
    col = geo.Column(seed)
    joints = geo.Joints(seed, rows[-1]['dist'])
    gap = np.array([r['gap'] for r in rows], bool)
    cave = np.array([r['cave'] for r in rows], bool)
    dist_st = np.array([r['dist'] for r in rows])

    log("secção de corrida")
    Wr, arc, rockmask, cls_r, pa_r, pb_r, mix_r, hard_r = sculpt(rows, P, R, U, loc, ride, col, joints, seed, floor_cls, floor_mask)

    # ---------------- paredes próximas: do pé (borda da secção) até à borda do planalto, em escadaria com alcovas
    log("paredes próximas (escadaria até ao planalto)")
    Rh = R.copy(); Rh[:, 1] = 0.0
    Rh /= np.maximum(np.linalg.norm(Rh, axis=1, keepdims=True), 1e-9)
    WARP_SEED = seed + 100
    sk = {}
    skirt_extent = {}
    centre_xz = P[:, [0, 2]]
    for side, ci in ((-1, 0), (1, N - 1)):
        lip = Wr[:, ci, :]
        y0 = lip[:, 1]
        out = Rh * side
        hw_side = np.linalg.norm(lip[:, [0, 2]] - centre_xz, axis=1)
        # 1) borda do planalto: primeiro x onde a escadaria (com warp) alcança o planalto
        xs = np.linspace(0.0, RIM_SEARCH, 153)
        px = lip[:, 0][:, None] + out[:, 0][:, None] * xs[None, :]
        pz = lip[:, 2][:, None] + out[:, 2][:, None] * xs[None, :]
        wp = wall_warp(dist_st[:, None] * np.ones_like(xs)[None, :], hw_side[:, None] + xs[None, :], WARP_SEED) * geo.smoothstep(0.0, 70.0, xs)[None, :]
        stair = col.height_from(y0[:, None] * np.ones_like(xs)[None, :], xs[None, :] + wp)
        plat = plateau(px, pz, col, np.zeros_like(px), seed)
        reach = stair >= plat
        first = np.where(reach.any(axis=1), reach.argmax(axis=1), len(xs) - 1)
        rim_x = xs[first]
        y_rim = np.maximum(plat[np.arange(S), first], y0 + 4.0)
        # 2) elevações das amostras: cantos da escadaria (topos das camadas e bancadas) + preenchimento por arco
        ys = np.zeros((S, KS + 1))
        for i in range(S):
            br = col.Yb[(col.Yb > y0[i] + 0.2) & (col.Yb < y_rim[i] - 0.2)]
            knots = np.concatenate([[y0[i]], br, [y_rim[i]]])
            kx = col.X(knots)
            seglen = np.hypot(np.diff(kx), np.diff(knots)) + 1e-6
            n_seg = len(seglen)
            if n_seg > KS:
                ys[i] = np.interp(np.linspace(0, 1, KS + 1), np.linspace(0, 1, len(knots)), knots)
                continue
            cnt = np.maximum(1, np.floor(seglen / seglen.sum() * KS).astype(int))
            while cnt.sum() > KS:
                cnt[np.argmax(cnt)] -= 1
            while cnt.sum() < KS:
                cnt[np.argmax(seglen / cnt)] += 1
            out_y = [knots[0]]
            for k_ in range(n_seg):
                t_ = np.arange(1, cnt[k_] + 1) / cnt[k_]
                # amostragem uniforme no comprimento de arco do segmento (falésia vertical ou bancada)
                out_y.extend(list(knots[k_] + (knots[k_ + 1] - knots[k_]) * t_))
            ys[i] = np.array(out_y[:KS + 1])
        # nas bancadas a elevação é quase constante: distribuir em x usando o perfil x(y) exato
        xst = col.X(ys) - col.X(y0)[:, None]
        xw = xst - wall_warp(dist_st[:, None] * np.ones_like(ys), hw_side[:, None] + xst, WARP_SEED) * geo.smoothstep(0.0, 70.0, xst)
        xw = np.maximum.accumulate(np.maximum(xw, 0.0), axis=1)          # sem dobras
        prof = np.stack([xw, ys], axis=-1)
        skirt_extent[side] = prof[:, -1, 0]
        pts = lip[:, None, :] + out[:, None, :] * prof[..., 0:1]
        pts[..., 1] = prof[..., 1]
        top = pts[:, -1, :]
        flap1 = top + out * 6.0; flap1[:, 1] += 0.3
        flap2 = top + out * 14.0; flap2[:, 1] -= 6.0
        near_gap = np.convolve((gap | cave).astype(float), np.ones(5), mode='same') > 0
        flap1[near_gap] = top[near_gap]; flap2[near_gap] = top[near_gap]
        pts = np.concatenate([pts, flap1[:, None, :], flap2[:, None, :]], axis=1)
        tt = np.concatenate([np.linspace(0.0, 1.0, KS + 1), [1.0, 1.0]])
        relief, hard, pa, pb, mix, _ = col.sample(pts[..., 0], pts[..., 1], pts[..., 2])
        jr = joints.recess(dist_st[:, None] + 2500.0 * side, pts[..., 1])
        rough = geo.fbm3(pts[..., 0] / 8.0, pts[..., 1] / 5.0, pts[..., 2] / 8.0, 3, seed=seed + 21 + side)
        g1 = np.gradient(pts, axis=1)
        steep = np.clip(np.abs(g1[..., 1]) / np.maximum(1e-3, np.linalg.norm(g1, axis=2)), 0, 1)
        face = (-1.6 * relief + 2.2 * jr + 0.8 * rough) * (0.3 + 0.7 * steep)
        fade = geo.smoothstep(0.0, 0.03, tt) * (1.0 - geo.smoothstep(0.96, 1.0, tt))
        pts = pts + out[:, None, :] * (face * fade[None, :])[..., None]
        cls = np.where(steep > 0.35, 0.75, 1.0)
        pa = np.where((steep <= 0.35) & (pts[..., 1] < 300.0), PAL_SAND, pa)     # areia nas bancadas
        sk[side] = (pts, cls, pa, pb, mix, hard)

    # grelha completa: parede esq. (topo -> borda) + secção + parede dir. (borda -> topo)
    pL, cL, paL, pbL, mxL, hdL = sk[-1]
    pR, cR, paR, pbR, mxR, hdR = sk[1]
    G = np.concatenate([pL[:, ::-1][:, :-1], Wr, pR[:, 1:]], axis=1)
    M = G.shape[1]
    KSP = KS + 2                              # pontos de parede por lado sem a borda
    Ng = grid_normals(G)
    C = np.concatenate([
        colors(cL[:, ::-1][:, :-1], paL[:, ::-1][:, :-1], pbL[:, ::-1][:, :-1], np.zeros((S, KSP))),
        colors(cls_r, pa_r, pb_r, 1.0 - rockmask),
        colors(cR[:, 1:], paR[:, 1:], pbR[:, 1:], np.zeros((S, KSP))),
    ], axis=1)
    UV2 = np.concatenate([
        np.stack([hdL[:, ::-1][:, :-1], mxL[:, ::-1][:, :-1]], axis=-1),
        np.stack([hard_r, mix_r], axis=-1),
        np.stack([hdR[:, 1:], mxR[:, 1:]], axis=-1),
    ], axis=1)
    seglen = np.linalg.norm(np.diff(G, axis=1), axis=2)
    across = np.concatenate([np.zeros((S, 1)), np.cumsum(seglen, axis=1)], axis=1)
    UVg = np.stack([across / 4.0, dist_st[:, None] * np.ones((1, M)) / 4.0], axis=-1)

    # ---------------- linhas de canyon
    log("paisagem: linhas de canyon")
    lines = []
    lipL_xz, lipR_xz = G[:, KSP, [0, 2]], G[:, KSP + N - 1, [0, 2]]
    centre = P[:, [0, 2]]
    hwL = np.linalg.norm(lipL_xz - centre, axis=1)
    hwR = np.linalg.norm(lipR_xz - centre, axis=1)
    footL, footR = Wr[:, 0, 1], Wr[:, -1, 1]
    floor = P[:, 1]
    skL_ext, skR_ext = skirt_extent[-1].copy(), skirt_extent[1].copy()
    skL_ext[cave] = 0.0; skR_ext[cave] = 0.0
    skL_ext[gap] = 0.0; skR_ext[gap] = 0.0
    # segmentos do canyon do percurso (a caverna interrompe: canyon termina num plano = boca)
    runs, i = [], 0
    while i < S:
        if not cave[i]:
            j = i
            while j + 1 < S and not cave[j + 1]:
                j += 1
            runs.append((i, j)); i = j + 1
        else:
            i += 1
    for (a, b) in runs:
        planes = []
        if a > 0 and cave[a - 1]:
            planes.append((centre[a], -T[a, [0, 2]] / np.linalg.norm(T[a, [0, 2]])))
        if b < S - 1 and cave[b + 1]:
            planes.append((centre[b], T[b, [0, 2]] / np.linalg.norm(T[b, [0, 2]])))
        xz, fL, fR, wL, wR, fl = centre[a:b + 1], footL[a:b + 1], footR[a:b + 1], hwL[a:b + 1], hwR[a:b + 1], floor[a:b + 1]
        sL, sR = skL_ext[a:b + 1], skR_ext[a:b + 1]
        # prolongamento virtual no início/fim do percurso: o canyon continua para lá da pista (leito visível)
        if a == 0:
            tdir = T[0, [0, 2]] / np.linalg.norm(T[0, [0, 2]])
            ext = np.array([centre[0] - tdir * k for k in np.linspace(1500.0, 30.0, 50)])
            xz = np.concatenate([ext, xz]); fL = np.r_[np.full(50, footL[0]), fL]; fR = np.r_[np.full(50, footR[0]), fR]
            wL = np.r_[np.full(50, hwL[0]), wL]; wR = np.r_[np.full(50, hwR[0]), wR]; fl = np.r_[np.full(50, floor[0] + 11.5), fl]
            sL = np.r_[np.zeros(50), sL]; sR = np.r_[np.zeros(50), sR]
        if b == S - 1:
            tdir = T[-1, [0, 2]] / np.linalg.norm(T[-1, [0, 2]])
            ext = np.array([centre[-1] + tdir * k for k in np.linspace(30.0, 1500.0, 50)])
            xz = np.concatenate([xz, ext]); fL = np.r_[fL, np.full(50, footL[-1])]; fR = np.r_[fR, np.full(50, footR[-1])]
            wL = np.r_[wL, np.full(50, hwL[-1])]; wR = np.r_[wR, np.full(50, hwR[-1])]; fl = np.r_[fl, np.full(50, floor[-1] + 11.5)]
            sL = np.r_[sL, np.zeros(50)]; sR = np.r_[sR, np.zeros(50)]
        al = dist_st[a:b + 1]
        if a == 0:
            al = np.r_[-np.linspace(1500.0, 30.0, 50), al]
        if b == S - 1:
            al = np.r_[al, dist_st[-1] + np.linspace(30.0, 1500.0, 50)]
        lines.append(CanyonLine(xz, fL, fR, wL, wR, 'course', WARP_SEED, planes, skirtL=sL, skirtR=sR, floor=fl, along=al))

    # distância ao percurso (afluentes, rede distante e mesas afastadas)
    kd_course = kdtree.KDTree(S)
    for i in range(S):
        kd_course.insert((P[i, 0], P[i, 2], 0.0), i)
    kd_course.balance()

    def course_dist(x, z):
        x = np.atleast_1d(x); z = np.atleast_1d(z)
        out = np.empty(x.size)
        fx, fz = x.ravel(), z.ravel()
        for kk in range(fx.size):
            out[kk] = kd_course.find((fx[kk], fz[kk], 0.0))[2]
        return out.reshape(x.shape)

    def meander(p, heading, length, n, rng, keep_away=0.0, wiggle=0.035):
        """Canyon sinuoso: meandros regulares (comprimento de onda 1,8-3,2 km) + pouco ruído; foge do percurso."""
        pts = []
        wl = rng.uniform(1800.0, 3200.0)
        amp = min(0.75, wiggle * 16.0)
        ph = rng.uniform(0.0, 2.0 * math.pi)
        base = heading
        drift = 0.0
        step = length / n
        for k in range(n):
            drift += rng.normal(0.0, wiggle * 0.12)
            hd = base + drift + amp * math.sin(2.0 * math.pi * (k * step) / wl + ph)
            q = p + np.array([math.sin(hd), math.cos(hd)]) * step
            if keep_away > 0.0:
                co, j, dd = kd_course.find((q[0], q[1], 0.0))
                if dd < keep_away:
                    away = math.atan2(q[0] - co[0], q[1] - co[1])
                    base = base + 0.25 * math.atan2(math.sin(away - base), math.cos(away - base))
                    if dd < keep_away * 0.7:
                        break
            p = q
            pts.append(p.copy())
        return np.array(pts), base

    rng = np.random.default_rng(seed + 500)
    # afluentes suspensos: nascem atrás da borda do canyon (pour-off) e sobem pelo planalto em meandros
    k = 0
    for i0 in range(300, S - 300, 480):
        if cave[max(0, i0 - 100):i0 + 100].any() or gap[max(0, i0 - 150):i0 + 150].any():
            continue
        side = 1 if k % 2 == 0 else -1
        k += 1
        hw0 = hwR[i0] if side > 0 else hwL[i0]
        ext0 = (skR_ext[i0] if side > 0 else skL_ext[i0]) + 45.0
        foot0 = footR[i0] if side > 0 else footL[i0]
        start = centre[i0] + Rh[i0, [0, 2]] * side * (hw0 + ext0)
        heading = math.atan2(Rh[i0, 0] * side, Rh[i0, 2] * side) + rng.uniform(-0.5, 0.5)
        pts, _ = meander(start, heading, rng.uniform(1200, 2600), 110, rng, wiggle=0.05)
        if len(pts) < 10:
            continue
        tt = np.linspace(0, 1, len(pts))
        f0 = float(col.height_from(foot0, ext0)) - 6.0
        fl = f0 + (300.0 - f0) * tt ** 1.3
        hw = 28.0 * (1.0 - tt) + 7.0
        lines.append(CanyonLine(pts, fl, fl, hw, hw, 'side', seed + 700 + k))
    # garganta transversal em cada ravina
    gi = 0
    while gi < S:
        if gap[gi]:
            gj = gi
            while gj + 1 < S and gap[gj + 1]:
                gj += 1
            mid = (gi + gj) // 2
            across_dir = Rh[mid, [0, 2]]
            pts = np.array([centre[mid] + across_dir * t for t in np.linspace(-900.0, 900.0, 120)])
            gorge_wiggle = np.array([T[mid, [0, 2]] * 25.0 * geo.fbm2(t / 300.0, 0.1, 2, seed=seed + 9) for t in np.linspace(-900, 900, 120)])
            fl = np.full(120, float(P[gi:gj + 1, 1].min()) - 72.0)
            hw = np.full(120, (dist_st[gj] - dist_st[gi]) * 0.5 + 3.0)
            lines.append(CanyonLine(pts + gorge_wiggle, fl, fl, hw, hw, 'gorge', seed + 900))
            gi = gj + 1
        else:
            gi += 1
    # rede de canyons distante: canyons principais (bancada do White Rim ou garganta funda) com afluentes
    bx0, bx1 = P[:, 0].min(), P[:, 0].max()
    bz0, bz1 = P[:, 2].min(), P[:, 2].max()
    cx, cz = (bx0 + bx1) / 2, (bz0 + bz1) / 2
    for km in range(6):
        a0 = km / 6.0 * 2.0 * math.pi + rng.uniform(-0.3, 0.3)
        r0 = rng.uniform(5200, 7600)
        p0 = np.array([cx + math.cos(a0) * r0, cz + math.sin(a0) * r0])
        heading = math.atan2(-math.sin(a0), math.cos(a0)) + rng.uniform(-0.4, 0.4)
        main, _ = meander(p0, heading, rng.uniform(7000, 11000), 220, rng, keep_away=1900.0, wiggle=0.03)
        if len(main) < 20:
            continue
        deep = km % 3 == 0
        floor_y = -60.0 if deep else 40.0
        hwm = rng.uniform(25, 40) if deep else rng.uniform(55, 95)
        lines.append(CanyonLine(main, np.full(len(main), floor_y), np.full(len(main), floor_y),
                                np.full(len(main), hwm), np.full(len(main), hwm), 'side', seed + 1100 + km))
        for kb in range(int(len(main) / 45)):
            j = int(rng.integers(15, len(main) - 15))
            t = main[min(j + 1, len(main) - 1)] - main[j - 1]
            base_h = math.atan2(t[0], t[1]) + (1 if rng.random() < 0.5 else -1) * rng.uniform(0.7, 1.4)
            br, _ = meander(main[j], base_h, rng.uniform(1500, 3500), 90, rng, keep_away=1700.0, wiggle=0.05)
            if len(br) < 10:
                continue
            tt = np.linspace(0, 1, len(br))
            fl = floor_y + 4.0 + (290.0 - floor_y) * tt ** 1.4
            hw = (30.0 if not deep else 18.0) * (1.0 - tt) + 6.0
            lines.append(CanyonLine(br, fl, fl, hw, hw, 'side', seed + 1300 + km * 10 + kb))
    log(f"linhas de canyon: {len(lines)}")

    def terrain(x, z, want_lowered=False):
        x = np.asarray(x, float); z = np.asarray(z, float)
        h = plateau(x, z, col, course_dist(x, z), seed)
        h = np.array(h, dtype=np.float64)
        low = np.zeros(h.shape, bool) if want_lowered else None
        for ln in lines:
            ln.heights(x, z, col, h, low)
        h = np.where(np.isfinite(h), h, 318.0)
        return (h, low) if want_lowered else h

    # ---------------- malhas do corredor
    log("malhas do corredor")
    chunk = int(spec.get('chunk', 64))
    stats = dict(tris=0, verts=0, objects=0)
    objs_corr = []

    def emit(mo, collection, bucket):
        if mo.empty():
            return
        ob, nv, nf = mo.to_object(collection)
        bucket.append(ob)
        stats['verts'] += nv; stats['tris'] += nf; stats['objects'] += 1

    ringL, ringR = KSP, KSP + N - 1
    for c0 in range(0, S - 1, chunk):
        c1 = min(S - 1, c0 + chunk)
        sl = slice(c0, c1 + 1)
        skip_ring = gap[sl].copy(); skip_ring[:-1] |= gap[c0 + 1:c1 + 1]
        skip_wall = skip_ring | cave[sl]
        skip_wall[:-1] |= cave[c0 + 1:c1 + 1]
        mo = MeshOut(f"GEO_Corridor_{c0 // chunk:03d}")
        mo.add_grid(G[sl, ringL:ringR + 1], Ng[sl, ringL:ringR + 1], C[sl, ringL:ringR + 1], UVg[sl, ringL:ringR + 1], UV2[sl, ringL:ringR + 1], skip=skip_ring)
        mo.add_grid(G[sl, :ringL + 1], Ng[sl, :ringL + 1], C[sl, :ringL + 1], UVg[sl, :ringL + 1], UV2[sl, :ringL + 1], skip=skip_wall)
        mo.add_grid(G[sl, ringR:], Ng[sl, ringR:], C[sl, ringR:], UVg[sl, ringR:], UV2[sl, ringR:], skip=skip_wall)
        emit(mo, col_corr, objs_corr)

    def band(label, inner, outer, facing_dir, depth=2.0):
        """Face de rocha entre dois contornos (boca de caverna / falésia de ravina), com relevo estratificado."""
        Q = max(len(inner), len(outer), 160)
        pin, pout = resample(inner, Q), resample(outer, Q)
        rows_ = 22
        t = np.linspace(0, 1, rows_)
        pts = pin[None, :, :] * (1 - t)[:, None, None] + pout[None, :, :] * t[:, None, None]
        relief, hard, pa, pb, mix, _ = col.sample(pts[..., 0], pts[..., 1], pts[..., 2])
        rough = geo.fbm3(pts[..., 0] / 7.0, pts[..., 1] / 5.0, pts[..., 2] / 7.0, 3, seed=seed + 31)
        amp = np.sin(np.pi * t)[:, None] * depth
        pts = pts + facing_dir[None, None, :] * ((1.2 * relief + 0.6 * rough) * amp)[..., None]
        nrm = grid_normals(pts)
        flip = False
        if np.mean(np.sum(nrm * facing_dir, axis=-1)) < 0:
            nrm = -nrm; flip = True
        uv = np.stack([np.linspace(0, 40, Q)[None, :].repeat(rows_, 0), pts[..., 1] / 4.0], axis=-1)
        mo = MeshOut(label)
        mo.add_grid(pts, nrm, colors(np.full(pts.shape[:2], 0.75), pa, pb, np.zeros(pts.shape[:2])), uv, np.stack([hard, mix], axis=-1), flip=flip)
        emit(mo, col_corr, objs_corr)

    # ---------------- caverna: teto irregular + bocas na parede do canyon
    cruns, i = [], 0
    while i < S:
        if cave[i]:
            j = i
            while j + 1 < S and cave[j + 1]:
                j += 1
            cruns.append((i, j)); i = j + 1
        else:
            i += 1
    cmid = N // 2
    wt = KF + KW
    for kc, (a, b) in enumerate(cruns):
        idx = np.arange(max(0, a - 1), min(S, b + 2))
        L = len(idx)
        iL, iR = KSP + cmid - wt, KSP + cmid + wt
        ceil_h = np.array([rows[i]['ceil'] for i in idx])
        tt = np.linspace(0.0, 1.0, KC + 1)
        pL, pR = G[idx, iL], G[idx, iR]
        lin = pL[:, None, :] * (1 - tt)[None, :, None] + pR[:, None, :] * tt[None, :, None]
        hmid = (np.einsum('ij,ij->i', pL - P[idx], U[idx]) + np.einsum('ij,ij->i', pR - P[idx], U[idx])) * 0.5
        lift = np.maximum(ceil_h - hmid, 2.0)[:, None] * np.sin(np.pi * tt)[None, :] ** 0.7
        ceil = lin + U[idx][:, None, :] * lift[..., None]
        bumps = geo.fbm3(ceil[..., 0] / 6.0, ceil[..., 1] / 4.0, ceil[..., 2] / 6.0, 4, seed=seed + 41)
        ceil = ceil - U[idx][:, None, :] * (np.maximum(bumps, -0.2) * 2.4 * np.sin(np.pi * tt)[None, :] ** 0.5)[..., None]
        relief, hard, pa, pb, mix, _ = col.sample(ceil[..., 0], ceil[..., 1], ceil[..., 2])
        uvc = np.stack([tt[None, :].repeat(L, 0) * 12.0, dist_st[idx][:, None].repeat(KC + 1, 1) / 4.0], axis=-1)
        mo = MeshOut(f"GEO_CaveCeiling_{kc}")
        mo.add_grid(ceil, -grid_normals(ceil), colors(np.full((L, KC + 1), 0.75), pa, pb, np.zeros((L, KC + 1))), uvc, np.stack([hard, mix], axis=-1), flip=True)
        emit(mo, col_corr, objs_corr)
        # bocas: contorno interior (borda esq. -> topo da parede -> teto -> topo dir. -> borda dir.)
        #        contorno exterior (perfil do terreno na secção da boca: paredes do canyon até ao planalto)
        for end, row, facing in (("In", 0, -1), ("Out", L - 1, 1)):
            si = idx[row]
            inner = np.concatenate([G[si, ringL:iL + 1], ceil[row, 1:-1], G[si, iR:ringR + 1]], axis=0)
            left_up = G[si, KSP:1:-1]                          # borda esq. -> topo da parede esq.
            right_down = G[si, ringR:ringR + KSP - 1][::-1]       # topo da parede dir. -> borda dir.
            outer = np.concatenate([left_up, right_down], axis=0)
            band(f"GEO_CaveMouth_{kc}_{end}", inner, outer, T[si] * facing, depth=2.5)
    log(f"cavernas: {len(cruns)}")

    # ---------------- ravina: faces de falésia nas duas bordas até ao fundo da garganta
    gi = 0
    kg = 0
    while gi < S:
        if gap[gi]:
            gj = gi
            while gj + 1 < S and gap[gj + 1]:
                gj += 1
            for si, facing in ((gi - 1, 1), (gj + 1, -1)):
                if si < 0 or si >= S:
                    continue
                top = G[si]
                bot = top.copy()
                bot[:, 1] = terrain(top[:, 0], top[:, 2]) - 3.0
                inner = top
                t = np.linspace(0.0, 1.0, KV + 1)
                pts = top[None, :, :] * (1 - t)[:, None, None] + bot[None, :, :] * t[:, None, None]
                relief, hard, pa, pb, mix, _ = col.sample(pts[..., 0], pts[..., 1], pts[..., 2])
                rough = geo.fbm3(pts[..., 0] / 7.0, pts[..., 1] / 5.0, pts[..., 2] / 7.0, 3, seed=seed + 51)
                fdir = T[si] * facing
                pts = pts + fdir[None, None, :] * ((1.4 * relief + 0.6 * rough) * (np.sin(np.pi * t)[:, None] * 0.9 + 0.1))[..., None]
                nrm = grid_normals(pts)
                flip = False
                if np.mean(np.sum(nrm * fdir, axis=-1)) < 0:
                    nrm = -nrm; flip = True
                uv = np.stack([np.cumsum(np.r_[0, np.linalg.norm(np.diff(pts, axis=1), axis=2)[0]])[None, :].repeat(KV + 1, 0) / 4.0, pts[..., 1] / 4.0], axis=-1)
                mo = MeshOut(f"GEO_Ravine{kg}_{'A' if facing > 0 else 'B'}")
                mo.add_grid(pts, nrm, colors(np.full(pts.shape[:2], 0.75), pa, pb, np.zeros(pts.shape[:2])), uv, np.stack([hard, mix], axis=-1), flip=flip)
                emit(mo, col_corr, objs_corr)
            kg += 1
            gi = gj + 1
        else:
            gi += 1

    # ---------------- terreno multi-resolução
    log("terreno multi-resolução")
    pad = 9000.0
    X0, X1 = P[:, 0].min() - pad, P[:, 0].max() + pad
    Z0, Z1 = P[:, 2].min() - pad, P[:, 2].max() + pad
    big = 2048.0
    tiles = []

    def tile_dist(x0, z0, size):
        xs = np.linspace(x0, x0 + size, 5); zs = np.linspace(z0, z0 + size, 5)
        XX, ZZ = np.meshgrid(xs, zs)
        return course_dist(XX, ZZ).min()

    def subdivide(x0, z0, size):
        d = tile_dist(x0, z0, size)
        if size > 512.0 and d < (900.0 if size <= 1024.0 else 2600.0):
            half = size / 2
            for ox in (0, half):
                for oz in (0, half):
                    subdivide(x0 + ox, z0 + oz, half)
        else:
            res = 8.0 if size <= 512.0 else (24.0 if size <= 1024.0 else 64.0)
            tiles.append((x0, z0, size, res))

    gx = int(math.ceil((X1 - X0) / big)); gz = int(math.ceil((Z1 - Z0) / big))
    for ix in range(gx):
        for iz in range(gz):
            subdivide(X0 + ix * big, Z0 + iz * big, big)
    log(f"terreno: {len(tiles)} blocos")
    objs_terr = []
    tverts = 0
    hmin, hmax = 1e9, -1e9
    for ti, (x0, z0, size, res) in enumerate(tiles):
        n = int(round(size / res)) + 1
        xs = x0 + np.arange(n) * res
        zs = z0 + np.arange(n) * res
        ZZ, XX = np.meshgrid(zs, xs, indexing='ij')
        HH = terrain(XX, ZZ)
        hmin, hmax = min(hmin, HH.min()), max(hmax, HH.max())
        TG = np.stack([XX, HH, ZZ], axis=-1)
        TN = grid_normals(TG)
        relief, hard, pa, pb, mix, _ = col.sample(XX, HH, ZZ)
        steep = 1.0 - np.clip(TN[..., 1], 0, 1)
        TC = colors(np.where(steep > 0.3, 0.75, 1.0), np.where(steep > 0.3, pa, np.where(HH > 300, pa, PAL_SAND)), pb, np.zeros_like(HH))
        TUV = np.stack([XX / 4.0, ZZ / 4.0], axis=-1)
        TUV2 = np.stack([hard, mix], axis=-1)
        mo = MeshOut(f"GEO_Terrain_{ti:03d}_{int(res)}m")
        skipq = None
        if len(cruns) and tile_dist(x0, z0, size) < 600.0:
            # quads que atravessam o túnel junto às bocas (a face de rocha da boca cobre o resto)
            near = np.empty(XX.size, np.int64); dd = np.empty(XX.size)
            fx, fz = XX.ravel(), ZZ.ravel()
            for kk in range(fx.size):
                co, j, dist_ = kd_course.find((fx[kk], fz[kk], 0.0))
                near[kk] = j; dd[kk] = dist_
            near = near.reshape(XX.shape); dd = dd.reshape(XX.shape)
            zone = np.zeros(XX.shape, bool)
            low = np.zeros(XX.shape, bool)
            nc = np.clip(near, 0, S - 1)
            canyon_w = np.maximum(hwL[nc] + skirt_extent[-1][nc], hwR[nc] + skirt_extent[1][nc]) + 18.0
            for (ca, cb) in cruns:
                for m0 in (ca, cb):
                    inz = (near >= m0 - 6) & (near <= m0 + 6)
                    zone |= inz & (dd <= canyon_w)
                    rim = plateau(XX, ZZ, col, np.zeros_like(XX), seed) - 12.0
                    low |= inz & (HH < rim)
            zq = zone[:-1, :-1] | zone[1:, :-1] | zone[:-1, 1:] | zone[1:, 1:]
            lq = low[:-1, :-1] | low[1:, :-1] | low[:-1, 1:] | low[1:, 1:]
            skipq = zq & lq
        mo.add_grid(TG, TN, TC, TUV, TUV2, adaptive=True, skipq=skipq)
        # saias anti-fendas nas 4 bordas (descem 14 m)
        for edge in (TG[0, :], TG[-1, :], TG[:, 0], TG[:, -1]):
            e2 = edge.copy(); e2[:, 1] -= 14.0
            strip = np.stack([edge, e2], axis=0)
            nrm = np.repeat(np.array([[0.0, 1.0, 0.0]]), strip.shape[1], 0)[None].repeat(2, 0)
            cc = colors(np.full(strip.shape[:2], 0.75), np.full(strip.shape[:2], 0), np.full(strip.shape[:2], 0), np.zeros(strip.shape[:2]))
            mo.add_grid(strip, nrm, cc, np.zeros(strip.shape[:2] + (2,)), np.zeros(strip.shape[:2] + (2,)))
            mo.add_grid(strip, nrm, cc, np.zeros(strip.shape[:2] + (2,)), np.zeros(strip.shape[:2] + (2,)), flip=True)
        tverts += n * n
        emit(mo, col_terr, objs_terr)
        if ti % 40 == 0:
            log(f"  bloco {ti}/{len(tiles)}")
    log(f"terreno: {tverts} vértices, alturas {hmin:.0f}..{hmax:.0f} m")

    # ---------------- exportação
    def export(objs, path):
        bpy.ops.object.select_all(action='DESELECT')
        for ob in objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.export_scene.fbx(
            filepath=path, use_selection=True, object_types={'MESH'},
            apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', global_scale=1.0,
            axis_forward='-Z', axis_up='Y', bake_space_transform=True,
            mesh_smooth_type='OFF', use_mesh_modifiers=False, use_triangles=False, use_tspace=False,
            colors_type='LINEAR', add_leaf_bones=False, use_custom_props=False, path_mode='STRIP', embed_textures=False)
        log(f"exportado {os.path.basename(path)} ({len(objs)} objetos)")

    export(objs_corr, os.path.join(OUT_DIR, f"{name}_corridor.fbx"))
    export(objs_terr, os.path.join(OUT_DIR, f"{name}_terrain.fbx"))
    ax = MeshOut("AXIS_TEST")
    ap = np.array([[[1.0, 2.0, 3.0], [11.0, 2.0, 3.0]], [[1.0, 2.0, 13.0], [11.0, 12.0, 13.0]]])
    ax.add_grid(ap, np.tile([0.0, 1.0, 0.0], (2, 2, 1)), np.ones((2, 2, 4)), np.zeros((2, 2, 2)), np.zeros((2, 2, 2)))
    axo, _, _ = ax.to_object(col_corr)
    export([axo], os.path.join(OUT_DIR, "axis_test.fbx"))

    # ---------------- dados do percurso
    segs = [s['id'] for s in spec['segments']]
    path = os.path.join(OUT_DIR, f"{name}_course.bytes")
    with open(path, 'wb') as f:
        f.write(b'RDDC')
        f.write(struct.pack('<iiif', 1, S, N, step))
        for i in range(S):
            r = rows[i]
            flags = (1 if r['gap'] else 0) | (2 if r['cave'] else 0)
            f.write(struct.pack('<f3f3f3f3f', r['dist'], *P[i], *T[i], *R[i], *U[i]))
            f.write(struct.pack('<fffiiiff', r['width'], r['bank'], r['slope'], flags, r['seg'], r['surf'], ride[i, 0], ride[i, 1]))
            f.write(Wr[i].astype('<f4').tobytes())
        f.write(struct.pack('<i', len(segs)))
        for sid in segs:
            b = sid.encode('utf-8')
            f.write(struct.pack('<i', len(b)))
            f.write(b)
    log("dados do percurso gravados")

    preview(name, P, Wr, terrain, X0, X1, Z0, Z1, rows)
    report = dict(name=name, stations=S, length_km=round(rows[-1]['dist'] / 1000.0, 3), ring=N, grid=M,
                  tris=stats['tris'], verts=stats['verts'], objects=stats['objects'], terrain_tiles=len(tiles),
                  terrain_heights=[round(float(hmin), 1), round(float(hmax), 1)],
                  elevation=[round(float(P[:, 1].min()), 1), round(float(P[:, 1].max()), 1)],
                  seconds=round(time.time() - T0, 1))
    json.dump(report, open(os.path.join(OUT_DIR, f"{name}_report.json"), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    log(f"relatório: {report}")


def preview(name, P, Wr, terrain, X0, X1, Z0, Z1, rows):
    """Mapa de cima (relevo sombreado com a paleta das camadas) com o percurso."""
    size = 1000
    span = max(X1 - X0, Z1 - Z0)
    xs = X0 + (np.arange(size) + 0.5) / size * span
    zs = Z0 + (np.arange(size) + 0.5) / size * span
    ZZ, XX = np.meshgrid(zs, xs, indexing='ij')
    HH = terrain(XX, ZZ)
    gz, gx = np.gradient(HH, span / size)
    shade = np.clip(0.62 - 0.55 * gx + 0.35 * gz, 0.15, 1.25)
    col = geo.Column(1)
    idx = np.clip(np.searchsorted(col.tops, HH), 0, len(col.tops) - 1)
    pal = np.array(geo.PALETTE, float) / 255.0
    img = pal[col.palA[idx]] * shade[..., None]
    img = np.clip(img, 0, 1)

    def plot(pts, color, r=0):
        px = ((pts[:, 0] - X0) / span * size).astype(int)
        pz = ((pts[:, 2] - Z0) / span * size).astype(int)
        ok = (px >= r) & (px < size - r) & (pz >= r) & (pz < size - r)
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                img[pz[ok] + dz, px[ok] + dx] = color

    plot(Wr.reshape(-1, 3), (0.95, 0.88, 0.7))
    plot(P, (1, 1, 1), 0)
    plot(P[[0]], (0.1, 0.9, 0.2), 4)
    im = bpy.data.images.new(f"{name}_preview", size, size, alpha=False)
    im.pixels.foreach_set(np.concatenate([img, np.ones((size, size, 1))], axis=-1).astype(np.float32).ravel())
    im.filepath_raw = os.path.join(OUT_DIR, f"{name}_preview.png")
    im.file_format = 'PNG'
    im.save()
    log("mapa gravado")


main()
