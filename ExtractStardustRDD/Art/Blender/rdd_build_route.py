"""
EXTRACT: STARDUST — RED DUST DIVIDE · construtor de rotas (grafo de percursos) e paisagem (Blender, modo batch).

Uso:
  blender -b --factory-startup -P rdd_build_route.py -- <spec.json> <pasta_saida>

Especificação (Art/Courses/*.json):
  - percurso principal: "start" + "segments" (comprimento, raio, inclinação, bank, largura, secção...);
  - "branches" (opcional): ramos que saem do principal à distância "from" e voltam a ele em "to". O eixo passa por
    pontos de passagem relativos ao principal ("via": t 0..1 ao longo do troço, side ±1, offset lateral em m, dy
    altura em m); "params" muda a secção do ramo; "sections" (frac 0..1 + parâmetros, como nos segmentos) muda-a ao
    longo do ramo. Nas pontas ("blend" m) o ramo herda a secção e o leito do principal: encaixe sem costura.

Junções — união de vazios: o "vazio" de um percurso é o ar por cima da sua superfície (leito, paredes, falésias até
ao planalto). Um ponto da superfície de um percurso só fica se não estiver dentro do vazio de outro. As malhas são
recortadas na linha em que as superfícies se cruzam; o percurso prioritário prolonga-se um pouco além do corte, por
isso as costuras sobrepõem-se e nunca abrem fendas. Onde dois canyons se afastam nasce uma ilha/fin; um ramo que sobe fica escavado como rampa na
parede do principal.

Saída: <nome>_corridor.fbx, <nome>_terrain.fbx, axis_test.fbx, <nome>_course.bytes (percurso principal, RDDC v1),
<nome>_graph.bytes (todos os percursos, RDDG v2), <nome>_preview.png e <nome>_report.json.
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
from rdd_route_lib import (T0, KF, KW, KS, KC, KV, RIM_SEARCH, EASED, SURFACES, PAL_SAND, log, integrate,  # noqa: E402
                           frames, build_ring, natural_floor, sculpt, wall_warp, CanyonLine, plateau, MeshOut,
                           grid_normals, colors, resample, OPEN_FIELDS)

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if len(ARGS) < 2:
    raise SystemExit("uso: blender -b -P rdd_build_route.py -- spec.json pasta_saida")
SPEC_PATH, OUT_DIR = os.path.abspath(ARGS[0]), os.path.abspath(ARGS[1])
os.makedirs(OUT_DIR, exist_ok=True)
KSP = KS + 2                     # pontos de parede próxima por lado (sem a borda da secção)
SECTION_KEYS = [k for k in EASED if k not in ('curv', 'slope')]
VOID_TOL = 0.15                  # superfícies a menos disto contam como coincidentes (cede o percurso de menor prioridade)
VOID_MARGIN = 0.8                # o percurso prioritário prolonga-se até estar isto acima do outro, mas essa faixa é
                                 # puxada para 8 cm abaixo da outra superfície: costuras sem fendas e sem lancis
TUCK = 0.08

# Erosão 3D das paredes (ver rdd_route_lib.erode3d). Valores por omissão iguais aos do laboratório,
# onde foram validados. Sobrepõem-se por spec.json com "erosion_m" (0 desliga) e "erosion_seed".
# Variáveis globais pelo mesmo motivo que KS/KSP: sculpt() é chamado sem o spec à mão.
# A seed tem de ser INTEIRA (o _hash do rdd_geology rebenta com float).
EROSION_M = 26.0
EROSION_SEED = 7


# ------------------------------------------------------------------ percursos

class OpenField:
    """
    Troços à superfície (open > 0): o planalto à volta vem ter com a borda da secção (a pista passa a ser um wash
    raso na planície de slickrock, com vista aberta) e afasta-se de volta ao relevo natural em ~420 m.
    """

    def __init__(self, P, Wr, open_st, seed, col):
        self.col = col
        idx = np.flatnonzero(open_st > 0.01)
        self.ok = len(idx) > 0
        if not self.ok:
            return
        self.o = open_st[idx]
        self.xz = P[idx][:, [0, 2]]
        self.target = np.maximum(Wr[idx, 0, 1], Wr[idx, -1, 1]) + 0.5
        self.r0 = np.maximum(np.linalg.norm(Wr[idx, 0][:, [0, 2]] - self.xz, axis=1),
                             np.linalg.norm(Wr[idx, -1][:, [0, 2]] - self.xz, axis=1)) + 20.0
        self.kd = kdtree.KDTree(len(idx))
        for i, (px, pz) in enumerate(self.xz):
            self.kd.insert((px, pz, 0.0), i)
        self.kd.balance()
        self.seed = seed
        r = 700.0
        self.bbox = (self.xz[:, 0].min() - r, self.xz[:, 0].max() + r, self.xz[:, 1].min() - r, self.xz[:, 1].max() + r)

    def apply(self, x, z, h):
        if not self.ok:
            return h
        x = np.asarray(x, float); z = np.asarray(z, float)
        b = self.bbox
        m = (x >= b[0]) & (x <= b[1]) & (z >= b[2]) & (z <= b[3])
        if not m.any():
            return h
        out = np.array(h, dtype=np.float64, copy=True)
        fx, fz = x[m], z[m]
        j = np.empty(fx.size, np.int64); d = np.empty(fx.size)
        for k in range(fx.size):
            _, j[k], d[k] = self.kd.find((fx[k], fz[k], 0.0))
        r0 = self.r0[j]
        swell = 3.0 * geo.fbm2(fx / 350.0, fz / 350.0, 3, seed=self.seed + 77) * geo.smoothstep(r0, r0 + 200.0, d)
        # a partir da borda da pista o terreno sobe pela escadaria das camadas (encostas nas moles, falésias nas
        # duras) até encontrar o relevo natural: bacias e bancadas abertas ficam cercadas de falésias reais
        edge = d - r0 + 60.0 * geo.fbm2(fx / 420.0, fz / 420.0, 3, seed=self.seed + 78)
        x = np.maximum(edge, 0.0)
        natural = out[m]
        # pista acima do relevo natural: o terreno sobe até à borda e desce em encosta (as falésias de quando a pista
        # está abaixo do relevo vêm das linhas de canyon do percurso, compostas pelo mínimo)
        down = self.target[j] + swell + (natural - self.target[j]) * geo.smoothstep(0.0, 350.0, x)
        tgt = np.where(natural < self.target[j], down, natural)
        out[m] = out[m] + (tgt - out[m]) * self.o[j]
        return out


class PathBuild:
    """Percurso construído: eixo, secção esculpida, paredes até ao planalto e grelha completa (estações × colunas)."""


def path_point(pb, d):
    """Posição, tangente e direita horizontal do eixo à distância d."""
    i = int(np.clip(np.searchsorted(pb.dist, d) - 1, 0, pb.S - 2))
    t = float(np.clip((d - pb.dist[i]) / max(pb.dist[i + 1] - pb.dist[i], 1e-9), 0.0, 1.0))
    p = pb.P[i] * (1 - t) + pb.P[i + 1] * t
    tg = pb.T[i] * (1 - t) + pb.T[i + 1] * t
    rh = pb.Rh[i] * (1 - t) + pb.Rh[i + 1] * t
    return p, tg / np.linalg.norm(tg), rh / np.linalg.norm(rh)


def row_at(pb, key, d):
    return float(np.interp(d, pb.dist, np.array([r[key] for r in pb.rows], float)))


def hermite_path(ctrl, t_start, t_end, samples=400):
    """Curva pelos pontos de controlo: tangentes do principal nas pontas, Catmull-Rom no meio (sem laçadas)."""
    n = len(ctrl)
    dirs = [t_start / np.linalg.norm(t_start)]
    for i in range(1, n - 1):
        v = ctrl[i + 1] - ctrl[i - 1]
        dirs.append(v / max(np.linalg.norm(v), 1e-9))
    dirs.append(t_end / np.linalg.norm(t_end))
    u = np.linspace(0.0, 1.0, samples, endpoint=False)[:, None]
    h00, h10 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u
    h01, h11 = -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    out = []
    for i in range(n - 1):
        c = np.linalg.norm(ctrl[i + 1] - ctrl[i])
        out.append(h00 * ctrl[i] + h10 * dirs[i] * c + h01 * ctrl[i + 1] + h11 * dirs[i + 1] * c)
    out.append(ctrl[-1][None, :])
    return np.concatenate(out)


def branch_rows(spec, br, parent, step):
    """Eixo e secções de um ramo. dist do ramo começa em 'from' (distância de corrida no ponto de saída)."""
    f, t_ = float(br['from']), float(br['to'])
    p0, t0, _ = path_point(parent, f)
    p1, t1, _ = path_point(parent, t_)
    ctrl = [p0]
    for v in br.get('via', []):
        d = f + (t_ - f) * float(v['t'])
        pp, _, rh = path_point(parent, d)
        ctrl.append(pp + rh * float(v.get('side', 1)) * float(v.get('offset', 0.0)) + np.array([0.0, float(v.get('dy', 0.0)), 0.0]))
    ctrl.append(p1)
    dense = hermite_path(ctrl, t0, t1)
    cum = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))]
    L = cum[-1]
    n = max(3, int(round(L / step)) + 1)
    ds = np.linspace(0.0, L, n)
    pos = np.stack([np.interp(ds, cum, dense[:, k]) for k in range(3)], axis=1)
    # secção própria: omissões + params do ramo; cada secção entra em 'ease' m (como os segmentos)
    dflt = spec['defaults']
    prm = br.get('params', {})
    base = {k: float(prm.get(k, dflt.get(k, 0.0))) for k in SECTION_KEYS}
    surf0, floor0 = prm.get('surface', dflt.get('surface', 'sand')), prm.get('floor', 'natural')
    secs = sorted(br.get('sections', []), key=lambda s_: float(s_['frac']))
    blend = float(br.get('blend', 150.0))
    par_a = {k: row_at(parent, k, f) for k in SECTION_KEYS}
    par_b = {k: row_at(parent, k, t_) for k in SECTION_KEYS}
    nat_a = parent.rows[int(np.clip(np.searchsorted(parent.dist, f), 0, parent.S - 1))]['natural']
    nat_b = parent.rows[int(np.clip(np.searchsorted(parent.dist, t_), 0, parent.S - 1))]['natural']
    names = [br['id']] + [s_.get('id', f"{br['id']} {i + 1}") for i, s_ in enumerate(secs)]
    rows = []
    for k in range(n):
        s = ds[k]
        cur = dict(base)
        surf, floor_kind, gap, cave, seg = surf0, floor0, 0, 0, 0
        for j, sct in enumerate(secs):
            s0 = float(sct['frac']) * L
            if s < s0:
                break
            e = float(geo.smoothstep(0.0, float(sct.get('ease', 120.0)), s - s0))
            cur = {kk: cur[kk] + (float(sct[kk]) - cur[kk]) * e if kk in sct else cur[kk] for kk in SECTION_KEYS}
            surf, floor_kind = sct.get('surface', surf), sct.get('floor', floor_kind)
            gap, cave, seg = int(sct.get('gap', 0)), int(sct.get('cave', 0)), j + 1
        w = float(geo.smoothstep(0.0, blend, s) * geo.smoothstep(0.0, blend, L - s))
        par = par_a if s < L / 2 else par_b
        vals = {kk: par[kk] + (cur[kk] - par[kk]) * w for kk in SECTION_KEYS}
        vals['curv'] = 0.0
        vals['slope'] = 0.0
        natural = (floor_kind == 'natural') if w >= 0.5 else (nat_a if s < L / 2 else nat_b)
        rows.append(dict(vals, pos=pos[k], seg=seg, gap=gap, cave=cave, surf=SURFACES.get(surf, 0), dist=f + s, natural=natural))
    log(f"ramo {br['id']}: {L / 1000.0:.2f} km ({f:.0f} → {t_:.0f} m do principal), {n} estações")
    return rows, names, L


def build_path(pid, rows, step, col, seed, names, warp_seed, joint_seed, floor_variants=None):
    """
    Constrói um percurso. floor_variants: [(rows com outra 'dist' para o ruído do leito, peso por estação)] — os
    ramos misturam o leito do principal (nas pontas) com o seu próprio (no meio).
    """
    pb = PathBuild()
    pb.id, pb.rows, pb.step, pb.names = pid, rows, step, names
    S = pb.S = len(rows)
    P, T, R, U = frames(rows)
    pb.P, pb.T, pb.R, pb.U = P, T, R, U
    loc, ride, N = build_ring(rows)
    if floor_variants:
        acc, cls_best, w_best, floor_mask = None, None, None, None
        for vrows, wv in floor_variants:
            l_, c_, m_ = natural_floor(vrows, loc, seed)
            acc = l_ * wv[:, None, None] if acc is None else acc + l_ * wv[:, None, None]
            if w_best is None:
                cls_best, w_best, floor_mask = c_.copy(), wv.copy(), m_
            else:
                better = wv > w_best
                cls_best[better] = c_[better]
                w_best = np.maximum(w_best, wv)
        loc, floor_cls = acc, cls_best
    else:
        loc, floor_cls, floor_mask = natural_floor(rows, loc, seed)
    pb.ride, pb.N = ride, N
    joints = geo.Joints(joint_seed, rows[-1]['dist'])
    gap = pb.gap = np.array([r['gap'] for r in rows], bool)
    cave = pb.cave = np.array([r['cave'] for r in rows], bool)
    dist_st = pb.dist = np.array([r['dist'] for r in rows])
    Wr, arc, rockmask, cls_r, pa_r, pb_r, mix_r, hard_r = sculpt(rows, P, R, U, loc, ride, col, joints, seed, floor_cls, floor_mask,
                                                                erosion_m=EROSION_M, erosion_seed=EROSION_SEED)
    pb.Wr = Wr
    Rh = R.copy(); Rh[:, 1] = 0.0
    Rh /= np.maximum(np.linalg.norm(Rh, axis=1, keepdims=True), 1e-9)
    pb.Rh = Rh
    pb.warp_seed = warp_seed
    open_st = np.array([r.get('open', 0.0) for r in rows])
    pb.open_field = OpenField(P, Wr, open_st, seed, col)
    if pb.open_field.ok:
        OPEN_FIELDS.append(pb.open_field)        # o planalto (borda, terreno) passa a respeitar este percurso

    # paredes próximas: do pé (borda da secção) até à borda do planalto, em escadaria com alcovas
    sk, ext = {}, {}
    centre_xz = P[:, [0, 2]]
    # curvas apertadas: do lado de dentro a parede não pode passar o centro da curva (senão dobra e faz abas por
    # cima da pista). Curvatura horizontal por estação; limite suavizado ao longo do percurso.
    Th = T.copy(); Th[:, 1] = 0.0
    Th /= np.maximum(np.linalg.norm(Th, axis=1, keepdims=True), 1e-9)
    dTh = np.gradient(Th, axis=0)
    kap = np.linalg.norm(dTh, axis=1) / np.maximum(np.abs(np.gradient(dist_st)), 1e-3)
    r_turn = 1.0 / np.maximum(kap, 1e-6)

    def run_min(a, w=15):
        o = a.copy()
        for k in range(1, w + 1):
            o[:-k] = np.minimum(o[:-k], a[k:])
            o[k:] = np.minimum(o[k:], a[:-k])
        return o
    for side, ci in ((-1, 0), (1, N - 1)):
        lip = Wr[:, ci, :]
        y0 = lip[:, 1]
        out = Rh * side
        hw_side = np.linalg.norm(lip[:, [0, 2]] - centre_xz, axis=1)
        xs = np.linspace(0.0, RIM_SEARCH, 153)
        px = lip[:, 0][:, None] + out[:, 0][:, None] * xs[None, :]
        pz = lip[:, 2][:, None] + out[:, 2][:, None] * xs[None, :]
        wp = wall_warp(dist_st[:, None] * np.ones_like(xs)[None, :], hw_side[:, None] + xs[None, :], warp_seed) * geo.smoothstep(0.0, 70.0, xs)[None, :]
        stair = col.height_from(y0[:, None] * np.ones_like(xs)[None, :], xs[None, :] + wp)
        plat = plateau(px, pz, col, np.zeros_like(px), seed)
        reach = stair >= plat
        first = np.where(reach.any(axis=1), reach.argmax(axis=1), len(xs) - 1)
        y_rim = np.maximum(plat[np.arange(S), first], y0 + 4.0 - 3.5 * open_st)
        y_rim = np.where(open_st > 0.5, np.minimum(y_rim, y0 + 6.0), y_rim)
        apron_st = np.array([r.get('apron', 0.0) for r in rows])
        y_rim = np.where(apron_st > 1.0, np.minimum(y_rim, y0 + 1.0), y_rim)
        ys = np.zeros((S, KS + 1))
        for i in range(S):
            brk = col.Yb[(col.Yb > y0[i] + 0.2) & (col.Yb < y_rim[i] - 0.2)]
            knots = np.concatenate([[y0[i]], brk, [y_rim[i]]])
            kx = col.X(knots)
            seglen = np.hypot(np.diff(kx), np.diff(knots)) + 1e-6
            if len(seglen) > KS:
                ys[i] = np.interp(np.linspace(0, 1, KS + 1), np.linspace(0, 1, len(knots)), knots)
                continue
            cnt = np.maximum(1, np.floor(seglen / seglen.sum() * KS).astype(int))
            while cnt.sum() > KS:
                cnt[np.argmax(cnt)] -= 1
            while cnt.sum() < KS:
                cnt[np.argmax(seglen / cnt)] += 1
            out_y = [knots[0]]
            for k_ in range(len(seglen)):
                t_ = np.arange(1, cnt[k_] + 1) / cnt[k_]
                out_y.extend(list(knots[k_] + (knots[k_ + 1] - knots[k_]) * t_))
            ys[i] = np.array(out_y[:KS + 1])
        xst = col.X(ys) - col.X(y0)[:, None]
        xw = xst - wall_warp(dist_st[:, None] * np.ones_like(ys), hw_side[:, None] + xst, warp_seed) * geo.smoothstep(0.0, 70.0, xst)
        xw = np.maximum.accumulate(np.maximum(xw, 0.0), axis=1)
        inner = np.einsum('ij,ij->i', dTh, out) > 0.0
        lim = run_min(np.where(inner, np.maximum(4.0, 0.8 * (r_turn - hw_side) - 14.0), 1e9))
        xw = np.minimum(xw, lim[:, None])
        ext[side] = xw[:, -1]
        pts = lip[:, None, :] + out[:, None, :] * xw[..., None]
        pts[..., 1] = ys
        top = pts[:, -1, :]
        flap1 = top + out * 6.0; flap1[:, 1] += 0.3
        flap2 = top + out * 14.0; flap2[:, 1] -= 6.0
        near_gap = np.convolve((gap | cave).astype(float), np.ones(5), mode='same') > 0
        flap1[near_gap] = top[near_gap]; flap2[near_gap] = top[near_gap]
        pts = np.concatenate([pts, flap1[:, None, :], flap2[:, None, :]], axis=1)
        tt = np.concatenate([np.linspace(0.0, 1.0, KS + 1), [1.0, 1.0]])
        relief, hard, pa, pbb, mix, _ = col.sample(pts[..., 0], pts[..., 1], pts[..., 2])
        jr = joints.recess(dist_st[:, None] + 2500.0 * side, pts[..., 1])
        rough = geo.fbm3(pts[..., 0] / 8.0, pts[..., 1] / 5.0, pts[..., 2] / 8.0, 3, seed=seed + 21 + side)
        g1 = np.gradient(pts, axis=1)
        steep = np.clip(np.abs(g1[..., 1]) / np.maximum(1e-3, np.linalg.norm(g1, axis=2)), 0, 1)
        face = (-1.6 * relief + 2.2 * jr + 0.8 * rough) * (0.3 + 0.7 * steep)
        fade = geo.smoothstep(0.0, 0.03, tt) * (1.0 - geo.smoothstep(0.96, 1.0, tt))
        pts = pts + out[:, None, :] * (face * fade[None, :])[..., None]
        cls = np.where(steep > 0.35, 0.75, 1.0)
        pa = np.where((steep <= 0.35) & (pts[..., 1] < 300.0), PAL_SAND, pa)     # areia nas bancadas
        sk[side] = (pts, cls, pa, pbb, mix, hard)
    pb.skirt_extent = ext

    # grelha completa: parede esq. (topo -> borda) + secção + parede dir. (borda -> topo)
    pL, cL, paL, pbL, mxL, hdL = sk[-1]
    pR, cR, paR, pbR, mxR, hdR = sk[1]
    G = np.concatenate([pL[:, ::-1][:, :-1], Wr, pR[:, 1:]], axis=1)
    M = pb.M = G.shape[1]
    pb.G = G
    pb.Ng = grid_normals(G)
    pb.C = np.concatenate([
        colors(cL[:, ::-1][:, :-1], paL[:, ::-1][:, :-1], pbL[:, ::-1][:, :-1], np.zeros((S, KSP))),
        colors(cls_r, pa_r, pb_r, 1.0 - rockmask),
        colors(cR[:, 1:], paR[:, 1:], pbR[:, 1:], np.zeros((S, KSP))),
    ], axis=1)
    pb.UV2 = np.concatenate([
        np.stack([hdL[:, ::-1][:, :-1], mxL[:, ::-1][:, :-1]], axis=-1),
        np.stack([hard_r, mix_r], axis=-1),
        np.stack([hdR[:, 1:], mxR[:, 1:]], axis=-1),
    ], axis=1)
    seglen = np.linalg.norm(np.diff(G, axis=1), axis=2)
    across = np.concatenate([np.zeros((S, 1)), np.cumsum(seglen, axis=1)], axis=1)
    pb.UVg = np.stack([across / 4.0, dist_st[:, None] * np.ones((1, M)) / 4.0], axis=-1)
    pb.ringL, pb.ringR = KSP, KSP + N - 1
    pb.centre = P[:, [0, 2]]
    pb.hwL = np.linalg.norm(G[:, KSP, [0, 2]] - pb.centre, axis=1)
    pb.hwR = np.linalg.norm(G[:, KSP + N - 1, [0, 2]] - pb.centre, axis=1)
    pb.footL, pb.footR = Wr[:, 0, 1], Wr[:, -1, 1]
    pb.floorY = P[:, 1]

    # superfície como função da posição (para a união de vazios): coordenada lateral e desvio longitudinal de cada
    # ponto da grelha em relação ao centro da sua estação
    Th = T[:, [0, 2]] / np.maximum(np.linalg.norm(T[:, [0, 2]], axis=1, keepdims=True), 1e-9)
    pb.Th = Th
    rel = G[..., [0, 2]] - pb.centre[:, None, :]
    pb.lat = np.maximum.accumulate(np.einsum('smk,sk->sm', rel, Rh[:, [0, 2]]), axis=1)
    pb.aoff = np.einsum('smk,sk->sm', rel, Th)
    pb.void_ok = ~cave
    pb.sp = np.maximum(np.diff(dist_st), 1e-3)
    pb.d = np.full((S, M), -np.inf)
    pb.who = np.full((S, M), -1, np.int64)
    pb.removed = np.zeros((S, M), bool)
    pb.pull = np.full((S, M), np.inf)        # altura máxima (faixa de sobreposição escondida por baixo de outro percurso)
    pb.kd = kdtree.KDTree(S)
    for i in range(S):
        pb.kd.insert((P[i, 0], P[i, 2], 0.0), i)
    pb.kd.balance()
    pb.bbox = (G[..., 0].min() - 20, G[..., 0].max() + 20, G[..., 2].min() - 20, G[..., 2].max() + 20)
    log(f"percurso {pid}: {S} estações, {(dist_st[-1] - dist_st[0]) / 1000.0:.2f} km")
    return pb


# ------------------------------------------------------------------ união de vazios

def row_interp(pb, st, x, z, field, void_only=False):
    """Valor de field[st, :] interpolado na coordenada lateral de cada ponto em relação à estação st (inf fora)."""
    out = np.full(x.size, np.inf)
    if x.size == 0:
        return out
    order = np.argsort(st, kind='stable')
    ss = st[order]
    cut = np.flatnonzero(np.diff(ss)) + 1
    for a, b in zip(np.r_[0, cut], np.r_[cut, len(ss)]):
        s_ = ss[a]
        if void_only and not pb.void_ok[s_]:
            continue
        sel = order[a:b]
        l = (x[sel] - pb.centre[s_, 0]) * pb.Rh[s_, 0] + (z[sel] - pb.centre[s_, 1]) * pb.Rh[s_, 2]
        lat = pb.lat[s_]
        v = np.interp(l, lat, field[s_])
        v[(l < lat[0]) | (l > lat[-1])] = np.inf
        out[sel] = v
    return out


def surface_height(pb, x, z):
    """Altura da superfície do percurso (leito, paredes, falésias) por cima de (x, z); +inf fora dela."""
    x = np.asarray(x, float).ravel(); z = np.asarray(z, float).ravel()
    n = x.size
    if n == 0:
        return np.full(0, np.inf)
    st = np.empty(n, np.int64)
    for k in range(n):
        st[k] = pb.kd.find((x[k], z[k], 0.0))[1]
    res = np.zeros(n)
    for _ in range(4):
        along = (x - pb.centre[st, 0]) * pb.Th[st, 0] + (z - pb.centre[st, 1]) * pb.Th[st, 1]
        a_row = row_interp(pb, st, x, z, pb.aoff)
        res = along - np.where(np.isfinite(a_row), a_row, 0.0)
        shift = np.round(res / pb.step).astype(np.int64)
        moved = np.clip(st + shift, 0, pb.S - 1)
        if np.array_equal(moved, st):
            break
        st = moved
    j = np.clip(st + np.where(res >= 0.0, 1, -1), 0, pb.S - 1)
    sp = pb.sp[np.clip(np.minimum(st, j), 0, pb.S - 2)]
    f = np.where(j != st, np.clip(np.abs(res) / sp, 0.0, 1.0), 0.0)
    hi = row_interp(pb, st, x, z, pb.G[..., 1], void_only=True)
    hj = row_interp(pb, j, x, z, pb.G[..., 1], void_only=True)
    ok = np.isfinite(hi) & np.isfinite(hj)
    h = np.full(n, np.inf)
    h[ok] = hi[ok] * (1.0 - f[ok]) + hj[ok] * f[ok]
    beyond = ((st == 0) & (res < -pb.sp[0])) | ((st == pb.S - 1) & (res > pb.sp[-1]))
    h[beyond] = np.inf
    return h


def union_of_voids(paths):
    """
    d = altura acima da superfície do outro percurso (o maior entre todos); d > 0: o ponto está no ar de outro
    percurso e sai. Em superfícies coincidentes cede o percurso de menor prioridade (ordem: principal, ramos...).
    """
    for xi, X in enumerate(paths):
        for yi, Y in enumerate(paths):
            if xi == yi:
                continue
            b = Y.bbox
            G = X.G
            m = (G[..., 0] >= b[0]) & (G[..., 0] <= b[1]) & (G[..., 2] >= b[2]) & (G[..., 2] <= b[3])
            m[X.cave, :] = False
            if not m.any():
                continue
            pts = G[m]
            h = surface_height(Y, pts[:, 0], pts[:, 2])
            s = VOID_TOL if xi > yi else -(VOID_TOL + VOID_MARGIN)
            dv = pts[:, 1] - h + s
            if xi < yi:
                band = (dv > -VOID_MARGIN) & (dv <= 0.0)
                pl = X.pull[m]
                pl[band] = np.minimum(pl[band], h[band] - TUCK)
                X.pull[m] = pl
            cur = X.d[m]
            better = dv > cur
            X.d[m] = np.where(better, dv, cur)
            w = X.who[m]
            w[better] = yi
            X.who[m] = w
        X.removed = X.d > 0.0
        log(f"união de vazios {X.id}: {int(X.removed.sum())} pontos dentro de outros canyons, {int(np.isfinite(X.pull).sum())} na faixa de sobreposição")
    for X in paths:                                   # só depois de todas as comparações (a ordem não importa)
        X.G[..., 1] = np.minimum(X.G[..., 1], X.pull)


def clip_grid(pts, nrm, col, uv, uv2, d, who, skip, paths, xi=0):
    """
    Quads totalmente fora dos outros vazios ficam; totalmente dentro saem; os mistos são recortados em triângulos na
    linha d = 0. Devolve (skipq, extra ou None).
    """
    A, B = d.shape
    ia, ib = np.meshgrid(np.arange(A - 1), np.arange(B - 1), indexing='ij')
    q = np.stack([ia * B + ib, ia * B + ib + 1, (ia + 1) * B + ib + 1, (ia + 1) * B + ib], axis=-1)
    D = np.clip(d.ravel(), -60.0, 60.0)
    pos = D[q] > 0.0
    npos = pos.sum(-1)
    rows_ok = ~skip[:A - 1][:, None] if skip is not None else np.ones((A - 1, 1), bool)
    full = npos == 0
    mixed = (npos > 0) & (npos < 4) & rows_ok
    if not mixed.any():
        return ~full, None
    V = pts.reshape(-1, 3); Nn = nrm.reshape(-1, 3); Cc = col.reshape(-1, 4)
    U1 = uv.reshape(-1, 2); U2 = uv2.reshape(-1, 2); Wh = who.ravel()
    vmap, src, tris = {}, [], []

    def orig(a):
        k = (a, a)
        r = vmap.get(k)
        if r is None:
            r = vmap[k] = len(src); src.append((a, a, 0.0))
        return r

    def cut(a, b):
        k = (a, b) if a < b else (b, a)
        r = vmap.get(k)
        if r is None:
            r = vmap[k] = len(src); src.append((a, b, D[a] / (D[a] - D[b])))
        return r

    for qq in q[mixed]:
        for tri in ((qq[0], qq[1], qq[2]), (qq[0], qq[2], qq[3])):
            poly = []
            for e in range(3):
                u_, v_ = tri[e], tri[(e + 1) % 3]
                iu, iv = D[u_] <= 0.0, D[v_] <= 0.0
                if iu:
                    poly.append(orig(u_))
                if iu != iv:
                    poly.append(cut(u_, v_))
            for k in range(1, len(poly) - 1):
                tris.append((poly[0], poly[k], poly[k + 1]))
    if not tris:
        return ~full, None
    src = np.array(src)
    a = src[:, 0].astype(np.int64); b = src[:, 1].astype(np.int64); t = src[:, 2][:, None]
    P = V[a] + (V[b] - V[a]) * t
    Nv = Nn[a] + (Nn[b] - Nn[a]) * t
    Nv /= np.maximum(np.linalg.norm(Nv, axis=1, keepdims=True), 1e-9)
    Cv = Cc[a] + (Cc[b] - Cc[a]) * t
    UVv = U1[a] + (U1[b] - U1[a]) * t
    UV2v = U2[a] + (U2[b] - U2[a]) * t
    new = a != b
    wv = Wh[np.where(D[a] > 0.0, a, b)]
    for yi in np.unique(wv[new]):
        if yi <= xi:
            continue                                  # este percurso cede: o corte fica onde está
        m = new & (wv == yi)
        h = surface_height(paths[yi], P[m, 0], P[m, 2])
        P[m, 1] = np.where(np.isfinite(h), np.minimum(P[m, 1], h - TUCK), P[m, 1])
    return ~full, (P, Nv, Cv, UVv, UV2v, np.array(tris, np.int64))


# ------------------------------------------------------------------ construção

def main():
    global KS, KSP, EROSION_M, EROSION_SEED
    spec = json.load(open(SPEC_PATH, encoding='utf-8'))
    # interruptores de jogabilidade: ramos (junções em camadas ainda por resolver) e features desligadas uma a uma
    if not spec.get('branches_enabled', True):
        spec['branches'] = []
    spec['features'] = [f for f in spec.get('features', []) if f.get('enabled', True)]
    KS = int(spec.get('wall_samples', KS))             # amostras das paredes próximas (percursos longos: menos)
    KSP = KS + 2
    EROSION_M = float(spec.get('erosion_m', 26.0))     # 0 desliga a erosão 3D das paredes
    EROSION_SEED = int(spec.get('erosion_seed', 7))   # inteiro: o _hash do geology exige-o
    log(f"erosao das paredes: {EROSION_M:.1f} m (seed {EROSION_SEED})")
    name = spec['name']
    seed = int(spec.get('seed', 1))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    col_corr = bpy.data.collections.new("Corridor"); scene.collection.children.link(col_corr)
    col_terr = bpy.data.collections.new("Terrain"); scene.collection.children.link(col_terr)
    col = geo.Column(seed)

    log("percurso principal")
    rows, step = integrate(spec)
    main_pb = build_path('main', rows, step, col, seed, [s_['id'] for s_ in spec['segments']], seed + 100, seed)
    main_pb.parent, main_pb.from_d, main_pb.to_d, main_pb.length = None, 0.0, float(main_pb.dist[-1]), float(main_pb.dist[-1])
    paths = [main_pb]
    for bi, br in enumerate(spec.get('branches', [])):
        brows, names, L = branch_rows(spec, br, main_pb, step)
        f, t_ = float(br['from']), float(br['to'])
        blend = float(br.get('blend', 150.0))
        s = np.array([r['dist'] for r in brows]) - f
        w_own = geo.smoothstep(0.0, 2.0 * blend, s) * geo.smoothstep(0.0, 2.0 * blend, L - s)
        rows_par = [dict(r, dist=f + (r['dist'] - f) * (t_ - f) / L) for r in brows]       # ruído do leito do principal
        rows_own = [dict(r, dist=r['dist'] + 7777.0 * (bi + 1)) for r in brows]           # ruído próprio
        pb = build_path(br['id'], brows, step, col, seed, names, seed + 100 + 37 * (bi + 1), seed + 37 * (bi + 1),
                        floor_variants=[(rows_par, 1.0 - w_own), (rows_own, w_own)])
        T = pb.T
        for i, r in enumerate(brows):
            r['slope'] = math.degrees(math.asin(float(np.clip(T[i, 1], -1.0, 1.0))))
        pb.parent, pb.from_d, pb.to_d, pb.length = 'main', f, t_, L
        paths.append(pb)
    if len(paths) > 1:
        log("união de vazios (junções)")
        union_of_voids(paths)

    # ---------------- paisagem: linhas de canyon de todos os percursos
    log("paisagem: linhas de canyon")
    lines = []
    for pb in paths:
        S = pb.S
        skL, skR = pb.skirt_extent[-1].copy(), pb.skirt_extent[1].copy()
        skL[pb.cave | pb.gap] = 0.0; skR[pb.cave | pb.gap] = 0.0
        runs, i = [], 0
        while i < S:
            if not pb.cave[i]:
                j = i
                while j + 1 < S and not pb.cave[j + 1]:
                    j += 1
                runs.append((i, j)); i = j + 1
            else:
                i += 1
        is_main = pb is main_pb
        for (a, b) in runs:
            start_planes = [(pb.centre[a], -pb.Th[a])] if a > 0 and pb.cave[a - 1] else []
            end_planes = [(pb.centre[b], pb.Th[b])] if b < S - 1 and pb.cave[b + 1] else []
            apron = np.array([r.get('apron', 0.0) for r in pb.rows])
            sl = slice(a, b + 1)
            xz, fL, fR, wL, wR, fl = pb.centre[sl], pb.footL[sl], pb.footR[sl], pb.hwL[sl], pb.hwR[sl], pb.floorY[sl]
            sL, sR, al, ap = skL[sl], skR[sl], pb.dist[sl], apron[sl]
            # prolongamento virtual no início/fim do percurso principal: o canyon continua para lá da pista
            if is_main and a == 0:
                ext = np.array([pb.centre[0] - pb.Th[0] * k for k in np.linspace(1500.0, 30.0, 50)])
                xz = np.concatenate([ext, xz]); fL = np.r_[np.full(50, pb.footL[0]), fL]; fR = np.r_[np.full(50, pb.footR[0]), fR]
                wL = np.r_[np.full(50, pb.hwL[0]), wL]; wR = np.r_[np.full(50, pb.hwR[0]), wR]; fl = np.r_[np.full(50, pb.floorY[0] + 11.5), fl]
                sL = np.r_[np.zeros(50), sL]; sR = np.r_[np.zeros(50), sR]; al = np.r_[-np.linspace(1500.0, 30.0, 50), al]
                ap = np.r_[np.full(50, ap[0]), ap]
            if is_main and b == S - 1:
                ext = np.array([pb.centre[-1] + pb.Th[-1] * k for k in np.linspace(30.0, 1500.0, 50)])
                xz = np.concatenate([xz, ext]); fL = np.r_[fL, np.full(50, pb.footL[-1])]; fR = np.r_[fR, np.full(50, pb.footR[-1])]
                wL = np.r_[wL, np.full(50, pb.hwL[-1])]; wR = np.r_[wR, np.full(50, pb.hwR[-1])]; fl = np.r_[fl, np.full(50, pb.floorY[-1] + 11.5)]
                sL = np.r_[sL, np.zeros(50)]; sR = np.r_[sR, np.zeros(50)]; al = np.r_[al, pb.dist[-1] + np.linspace(30.0, 1500.0, 50)]
                ap = np.r_[ap, np.full(50, ap[-1])]
            n_all = len(xz)
            cn = max(20, int(float(spec.get('line_chunk', 600.0)) / max(pb.step, 1.0)))
            ov = max(4, int(40.0 / max(pb.step, 1.0)))
            starts = list(range(0, n_all, cn))
            if len(starts) > 1 and n_all - starts[-1] < cn // 3:
                starts.pop()                                       # cauda curta junta-se ao pedaço anterior
            for ci, c0 in enumerate(starts):
                c1 = n_all if ci == len(starts) - 1 else min(n_all, c0 + cn + ov)
                cs = slice(max(0, c0 - ov), c1)
                pl = (start_planes if ci == 0 else []) + (end_planes if ci == len(starts) - 1 else [])
                lines.append(CanyonLine(xz[cs], fL[cs], fR[cs], wL[cs], wR[cs], 'course', pb.warp_seed, pl,
                                        skirtL=sL[cs], skirtR=sR[cs], floor=fl[cs], along=al[cs], apron=ap[cs]))

    allP = np.concatenate([pb.P for pb in paths])
    kd_course = kdtree.KDTree(len(allP))
    for i in range(len(allP)):
        kd_course.insert((allP[i, 0], allP[i, 2], 0.0), i)
    kd_course.balance()

    def course_dist(x, z):
        x = np.atleast_1d(x); z = np.atleast_1d(z)
        out = np.empty(x.size)
        fx, fz = x.ravel(), z.ravel()
        for kk in range(fx.size):
            out[kk] = kd_course.find((fx[kk], fz[kk], 0.0))[2]
        return out.reshape(x.shape)

    def branch_dist(pts2):
        """Distância mínima de pontos (x, z) aos eixos dos ramos (inf sem ramos)."""
        best = np.full(len(pts2), np.inf)
        for pb in paths[1:]:
            for kk in range(len(pts2)):
                best[kk] = min(best[kk], pb.kd.find((pts2[kk, 0], pts2[kk, 1], 0.0))[2])
        return best

    def meander(p, heading, length, n, rng, keep_away=0.0, wiggle=0.035):
        """Canyon sinuoso: meandros regulares (comprimento de onda 1,8-3,2 km) + pouco ruído; foge do percurso."""
        pts = []
        wl = rng.uniform(1800.0, 3200.0)
        amp = min(0.75, wiggle * 16.0)
        ph = rng.uniform(0.0, 2.0 * math.pi)
        base = heading
        drift = 0.0
        stp = length / n
        for k in range(n):
            drift += rng.normal(0.0, wiggle * 0.12)
            hd = base + drift + amp * math.sin(2.0 * math.pi * (k * stp) / wl + ph)
            q = p + np.array([math.sin(hd), math.cos(hd)]) * stp
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
    mp = main_pb
    # afluentes suspensos do principal: nascem atrás da borda (pour-off) e sobem pelo planalto em meandros
    k = 0
    for i0 in range(300, mp.S - 300, 480):
        if mp.cave[max(0, i0 - 100):i0 + 100].any() or mp.gap[max(0, i0 - 150):i0 + 150].any():
            continue
        if mp.rows[i0].get('open', 0.0) > 0.3:
            continue                      # à superfície não há borda de canyon de onde cair
        side = 1 if k % 2 == 0 else -1
        k += 1
        hw0 = mp.hwR[i0] if side > 0 else mp.hwL[i0]
        ext0 = (mp.skirt_extent[1][i0] if side > 0 else mp.skirt_extent[-1][i0]) + 45.0
        foot0 = mp.footR[i0] if side > 0 else mp.footL[i0]
        start = mp.centre[i0] + mp.Rh[i0, [0, 2]] * side * (hw0 + ext0)
        heading = math.atan2(mp.Rh[i0, 0] * side, mp.Rh[i0, 2] * side) + rng.uniform(-0.5, 0.5)
        pts, _ = meander(start, heading, rng.uniform(1200, 2600), 110, rng, wiggle=0.05)
        if len(pts) < 10:
            continue
        if len(paths) > 1 and (mp.removed[max(0, i0 - 40):i0 + 40].any() or branch_dist(pts).min() < 450.0):
            continue                      # não atravessar o canyon de um ramo
        tt = np.linspace(0, 1, len(pts))
        f0 = float(col.height_from(foot0, ext0)) - 6.0
        fl = f0 + (300.0 - f0) * tt ** 1.3
        hw = 28.0 * (1.0 - tt) + 7.0
        lines.append(CanyonLine(pts, fl, fl, hw, hw, 'side', seed + 700 + k))
    # garganta transversal em cada ravina
    for pb in paths:
        gi = 0
        while gi < pb.S:
            if pb.gap[gi]:
                gj = gi
                while gj + 1 < pb.S and pb.gap[gj + 1]:
                    gj += 1
                mid = (gi + gj) // 2
                across_dir = pb.Rh[mid, [0, 2]]
                pts = np.array([pb.centre[mid] + across_dir * t for t in np.linspace(-900.0, 900.0, 120)])
                gorge_wiggle = np.array([pb.T[mid, [0, 2]] * 25.0 * geo.fbm2(t / 300.0, 0.1, 2, seed=seed + 9) for t in np.linspace(-900, 900, 120)])
                fl = np.full(120, float(pb.P[gi:gj + 1, 1].min()) - 72.0)
                hw = np.full(120, (pb.dist[gj] - pb.dist[gi]) * 0.5 + 3.0)
                lines.append(CanyonLine(pts + gorge_wiggle, fl, fl, hw, hw, 'gorge', seed + 900))
                gi = gj + 1
            else:
                gi += 1
    # rede de canyons distante: canyons principais (bancada do White Rim ou garganta funda) com afluentes
    bx0, bx1 = mp.P[:, 0].min(), mp.P[:, 0].max()
    bz0, bz1 = mp.P[:, 2].min(), mp.P[:, 2].max()
    cx, cz = (bx0 + bx1) / 2, (bz0 + bz1) / 2
    for km in range(6):
        a0 = km / 6.0 * 2.0 * math.pi + rng.uniform(-0.3, 0.3)
        r0 = rng.uniform(5200, 7600)
        p0 = np.array([cx + math.cos(a0) * r0, cz + math.sin(a0) * r0])
        heading = math.atan2(-math.sin(a0), math.cos(a0)) + rng.uniform(-0.4, 0.4)
        mline, _ = meander(p0, heading, rng.uniform(7000, 11000), 220, rng, keep_away=1900.0, wiggle=0.03)
        if len(mline) < 20:
            continue
        deep = km % 3 == 0
        floor_y = -60.0 if deep else 40.0
        hwm = rng.uniform(25, 40) if deep else rng.uniform(55, 95)
        lines.append(CanyonLine(mline, np.full(len(mline), floor_y), np.full(len(mline), floor_y),
                                np.full(len(mline), hwm), np.full(len(mline), hwm), 'side', seed + 1100 + km))
        for kb in range(int(len(mline) / 45)):
            j = int(rng.integers(15, len(mline) - 15))
            t = mline[min(j + 1, len(mline) - 1)] - mline[j - 1]
            base_h = math.atan2(t[0], t[1]) + (1 if rng.random() < 0.5 else -1) * rng.uniform(0.7, 1.4)
            brl, _ = meander(mline[j], base_h, rng.uniform(1500, 3500), 90, rng, keep_away=1700.0, wiggle=0.05)
            if len(brl) < 10:
                continue
            tt = np.linspace(0, 1, len(brl))
            fl = floor_y + 4.0 + (290.0 - floor_y) * tt ** 1.4
            hw = (30.0 if not deep else 18.0) * (1.0 - tt) + 6.0
            lines.append(CanyonLine(brl, fl, fl, hw, hw, 'side', seed + 1300 + km * 10 + kb))
    for fi, ft in enumerate(spec.get('features', [])):
        if ft['type'] != 'gorge_along':
            continue
        gp = next((p for p in paths if p.id == ft.get('path', 'main') or p.id.startswith(ft.get('path', 'main') + ' ')), main_pb)
        a = int(np.searchsorted(gp.dist, float(ft['from'])))
        b = int(np.searchsorted(gp.dist, float(ft['to'])))
        side = float(ft.get('side', 1))
        off = float(ft.get('offset', 320.0))
        xz = gp.centre[a:b] + gp.Rh[a:b][:, [0, 2]] * side * off
        xz += gp.Th[a:b] * (40.0 * geo.fbm2(gp.dist[a:b] / 900.0, np.full(b - a, 0.3), 2, seed=seed + 1601))[:, None]
        fl = gp.floorY[a:b] - float(ft.get('depth', 180.0))
        hw = np.full(b - a, float(ft.get('half_width', 45.0)))
        lines.append(CanyonLine(xz[::4], fl[::4], fl[::4], hw[::4], hw[::4], 'side', seed + 1600 + fi))
        log(f"garganta ao longo de {gp.id} {ft['from']}-{ft['to']} m, a {off:.0f} m, {ft.get('depth', 180)} m abaixo")
    log(f"linhas de canyon: {len(lines)}")

    def terrain(x, z):
        x = np.asarray(x, float); z = np.asarray(z, float)
        h = np.array(plateau(x, z, col, course_dist(x, z), seed), dtype=np.float64)
        for ln in lines:
            ln.heights(x, z, col, h, None)
        return np.where(np.isfinite(h), h, 318.0)

    # ---------------- malhas dos percursos (recortadas nas junções)
    log("malhas dos percursos")
    chunk = int(spec.get('chunk', 64))
    stats = dict(tris=0, verts=0, objects=0, clipped_tris=0)
    objs_corr = []

    def emit(mo, collection, bucket):
        if mo.empty():
            return
        ob, nv, nf = mo.to_object(collection)
        bucket.append(ob)
        stats['verts'] += nv; stats['tris'] += nf; stats['objects'] += 1

    def add_clipped(mo, pb, sl, cs, skip):
        sub = (pb.G[sl, cs], pb.Ng[sl, cs], pb.C[sl, cs], pb.UVg[sl, cs], pb.UV2[sl, cs])
        skipq, extra = clip_grid(*sub, pb.d[sl, cs], pb.who[sl, cs], skip, paths, paths.index(pb))
        mo.add_grid(*sub, skip=skip, skipq=skipq)
        if extra is not None:
            mo.add_tris(*extra)
            stats['clipped_tris'] += len(extra[5])

    for pi, pb in enumerate(paths):
        S = pb.S
        tag = "Corridor" if pi == 0 else f"Branch{pi}"
        L_, R_ = pb.ringL, pb.ringR
        for c0 in range(0, S - 1, chunk):
            c1 = min(S - 1, c0 + chunk)
            sl = slice(c0, c1 + 1)
            skip_ring = pb.gap[sl].copy(); skip_ring[:-1] |= pb.gap[c0 + 1:c1 + 1]
            skip_wall = skip_ring | pb.cave[sl]
            skip_wall[:-1] |= pb.cave[c0 + 1:c1 + 1]
            mo = MeshOut(f"GEO_{tag}_{c0 // chunk:03d}")
            add_clipped(mo, pb, sl, slice(L_, R_ + 1), skip_ring)
            add_clipped(mo, pb, sl, slice(0, L_ + 1), skip_wall)
            add_clipped(mo, pb, sl, slice(R_, pb.M), skip_wall)
            emit(mo, col_corr, objs_corr)

    def band(label, inner, outer, facing_dir, depth=2.0):
        """Face de rocha entre dois contornos (boca de caverna), com relevo estratificado."""
        Q = max(len(inner), len(outer), 160)
        pin, pout = resample(inner, Q), resample(outer, Q)
        rows_ = 22
        t = np.linspace(0, 1, rows_)
        pts = pin[None, :, :] * (1 - t)[:, None, None] + pout[None, :, :] * t[:, None, None]
        relief, hard, pa, pbb, mix, _ = col.sample(pts[..., 0], pts[..., 1], pts[..., 2])
        rough = geo.fbm3(pts[..., 0] / 7.0, pts[..., 1] / 5.0, pts[..., 2] / 7.0, 3, seed=seed + 31)
        amp = np.sin(np.pi * t)[:, None] * depth
        pts = pts + facing_dir[None, None, :] * ((1.2 * relief + 0.6 * rough) * amp)[..., None]
        nrm = grid_normals(pts)
        flip = False
        if np.mean(np.sum(nrm * facing_dir, axis=-1)) < 0:
            nrm = -nrm; flip = True
        uv = np.stack([np.linspace(0, 40, Q)[None, :].repeat(rows_, 0), pts[..., 1] / 4.0], axis=-1)
        mo = MeshOut(label)
        mo.add_grid(pts, nrm, colors(np.full(pts.shape[:2], 0.75), pa, pbb, np.zeros(pts.shape[:2])), uv, np.stack([hard, mix], axis=-1), flip=flip)
        emit(mo, col_corr, objs_corr)

    # ---------------- cavernas: teto irregular + bocas na parede do canyon
    cave_mouths = {}
    ncaves = 0
    for pi, pb in enumerate(paths):
        S, G, N = pb.S, pb.G, pb.N
        cruns, i = [], 0
        while i < S:
            if pb.cave[i]:
                j = i
                while j + 1 < S and pb.cave[j + 1]:
                    j += 1
                cruns.append((i, j)); i = j + 1
            else:
                i += 1
        cmid = N // 2
        wt = KF + KW
        pfx = "" if pi == 0 else f"B{pi}_"
        for kc, (a, b) in enumerate(cruns):
            idx = np.arange(max(0, a - 1), min(S, b + 2))
            L = len(idx)
            iL, iR = KSP + cmid - wt, KSP + cmid + wt
            ceil_h = np.array([pb.rows[i]['ceil'] for i in idx])
            tt = np.linspace(0.0, 1.0, KC + 1)
            pL, pR = G[idx, iL], G[idx, iR]
            lin = pL[:, None, :] * (1 - tt)[None, :, None] + pR[:, None, :] * tt[None, :, None]
            hmid = (np.einsum('ij,ij->i', pL - pb.P[idx], pb.U[idx]) + np.einsum('ij,ij->i', pR - pb.P[idx], pb.U[idx])) * 0.5
            lift = np.maximum(ceil_h - hmid, 2.0)[:, None] * np.sin(np.pi * tt)[None, :] ** 0.7
            ceil = lin + pb.U[idx][:, None, :] * lift[..., None]
            bumps = geo.fbm3(ceil[..., 0] / 6.0, ceil[..., 1] / 4.0, ceil[..., 2] / 6.0, 4, seed=seed + 41)
            ceil = ceil - pb.U[idx][:, None, :] * (np.maximum(bumps, -0.2) * 2.4 * np.sin(np.pi * tt)[None, :] ** 0.5)[..., None]
            relief, hard, pa, pbb, mix, _ = col.sample(ceil[..., 0], ceil[..., 1], ceil[..., 2])
            uvc = np.stack([tt[None, :].repeat(L, 0) * 12.0, pb.dist[idx][:, None].repeat(KC + 1, 1) / 4.0], axis=-1)
            mo = MeshOut(f"GEO_CaveCeiling_{pfx}{kc}")
            mo.add_grid(ceil, -grid_normals(ceil), colors(np.full((L, KC + 1), 0.75), pa, pbb, np.zeros((L, KC + 1))), uvc, np.stack([hard, mix], axis=-1), flip=True)
            emit(mo, col_corr, objs_corr)
            # bocas: contorno interior (borda esq. -> topo da parede -> teto -> topo dir. -> borda dir.)
            #        contorno exterior (perfil do terreno na secção da boca: paredes do canyon até ao planalto)
            for end, row, facing in (("In", 0, -1), ("Out", L - 1, 1)):
                si = idx[row]
                inner = np.concatenate([G[si, pb.ringL:iL + 1], ceil[row, 1:-1], G[si, iR:pb.ringR + 1]], axis=0)
                left_up = G[si, KSP:1:-1]
                right_down = G[si, pb.ringR:pb.ringR + KSP - 1][::-1]
                outer = np.concatenate([left_up, right_down], axis=0)
                band(f"GEO_CaveMouth_{pfx}{kc}_{end}", inner, outer, pb.T[si] * facing, depth=2.5)
            cave_mouths.setdefault(pi, []).extend([a, b])
            ncaves += 1
    log(f"cavernas: {ncaves}")

    # ---------------- ravinas: faces de falésia nas duas bordas até ao fundo da garganta
    for pi, pb in enumerate(paths):
        gi, kg = 0, 0
        pfx = "" if pi == 0 else f"B{pi}_"
        while gi < pb.S:
            if pb.gap[gi]:
                gj = gi
                while gj + 1 < pb.S and pb.gap[gj + 1]:
                    gj += 1
                for si, facing in ((gi - 1, 1), (gj + 1, -1)):
                    if si < 0 or si >= pb.S:
                        continue
                    top = pb.G[si]
                    bot = top.copy()
                    bot[:, 1] = terrain(top[:, 0], top[:, 2]) - 3.0
                    t = np.linspace(0.0, 1.0, KV + 1)
                    pts = top[None, :, :] * (1 - t)[:, None, None] + bot[None, :, :] * t[:, None, None]
                    relief, hard, pa, pbb, mix, _ = col.sample(pts[..., 0], pts[..., 1], pts[..., 2])
                    rough = geo.fbm3(pts[..., 0] / 7.0, pts[..., 1] / 5.0, pts[..., 2] / 7.0, 3, seed=seed + 51)
                    fdir = pb.T[si] * facing
                    pts = pts + fdir[None, None, :] * ((1.4 * relief + 0.6 * rough) * (np.sin(np.pi * t)[:, None] * 0.9 + 0.1))[..., None]
                    nrm = grid_normals(pts)
                    flip = False
                    if np.mean(np.sum(nrm * fdir, axis=-1)) < 0:
                        nrm = -nrm; flip = True
                    uv = np.stack([np.cumsum(np.r_[0, np.linalg.norm(np.diff(pts, axis=1), axis=2)[0]])[None, :].repeat(KV + 1, 0) / 4.0, pts[..., 1] / 4.0], axis=-1)
                    mo = MeshOut(f"GEO_Ravine{pfx}{kg}_{'A' if facing > 0 else 'B'}")
                    mo.add_grid(pts, nrm, colors(np.full(pts.shape[:2], 0.75), pa, pbb, np.zeros(pts.shape[:2])), uv, np.stack([hard, mix], axis=-1), flip=flip)
                    emit(mo, col_corr, objs_corr)
                kg += 1
                gi = gj + 1
            else:
                gi += 1

    # ---------------- kit de rocha e destroços: arcos por cima da pista, pedregulhos, esqueletos de naves
    import rdd_rockkit as kit
    obstacles = []

    def path_by(key):
        return next((p for p in paths if p.id == key or p.id.startswith(key + ' ')), main_pb)

    for fi, ft in enumerate(spec.get('features', [])):
        pb = path_by(ft.get('path', 'main'))
        if ft['type'] == 'arch':
            emit(kit.arch(pb, ft, col, seed + 3000 + fi), col_corr, objs_corr)
        elif ft['type'] == 'wreck':
            emit(kit.wreck(pb, ft, col, seed + 3100 + fi), col_corr, objs_corr)
        elif ft['type'] in ('pillars', 'rockfall'):
            mo, obs = kit.obstacles(pb, ft, col, seed + 3300 + fi)
            emit(mo, col_corr, objs_corr)
            obstacles.extend(dict(o, path=paths.index(pb)) for o in obs)
    rcfg = spec.get('rocks')
    if rcfg:
        import rdd_rockscatter as rs                  # rochas de todos os tamanhos (seixos a pilares de 45 m)
        for k, pb in enumerate(paths):
            for mo in rs.scatter(pb, rcfg, col, seed + 3200 + k, terrain, KSP):
                emit(mo, col_corr, objs_corr)

    # ---------------- terreno multi-resolução
    log("terreno multi-resolução")
    pad = 9000.0
    X0, X1 = allP[:, 0].min() - pad, allP[:, 0].max() + pad
    Z0, Z1 = allP[:, 2].min() - pad, allP[:, 2].max() + pad
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
            res = float(spec.get('terrain_res', 8.0)) if size <= 512.0 else (24.0 if size <= 1024.0 else 64.0)
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
        relief, hard, pa, pbb, mix, _ = col.sample(XX, HH, ZZ)
        steep = 1.0 - np.clip(TN[..., 1], 0, 1)
        TC = colors(np.where(steep > 0.3, 0.75, 1.0), np.where(steep > 0.3, pa, np.where(HH > 300, pa, PAL_SAND)), pbb, np.zeros_like(HH))
        TUV = np.stack([XX / 4.0, ZZ / 4.0], axis=-1)
        TUV2 = np.stack([hard, mix], axis=-1)
        mo = MeshOut(f"GEO_Terrain_{ti:03d}_{int(res)}m")
        skipq = None
        if cave_mouths and tile_dist(x0, z0, size) < 600.0:
            # quads que atravessam o túnel junto às bocas (a face de rocha da boca cobre o resto)
            zone = np.zeros(XX.shape, bool)
            low = np.zeros(XX.shape, bool)
            rim = plateau(XX, ZZ, col, np.zeros_like(XX), seed) - 12.0
            fx, fz = XX.ravel(), ZZ.ravel()
            for pi, mouths in cave_mouths.items():
                pb = paths[pi]
                near = np.empty(XX.size, np.int64); dd = np.empty(XX.size)
                for kk in range(fx.size):
                    co, j, dist_ = pb.kd.find((fx[kk], fz[kk], 0.0))
                    near[kk] = j; dd[kk] = dist_
                near = near.reshape(XX.shape); dd = dd.reshape(XX.shape)
                nc = np.clip(near, 0, pb.S - 1)
                canyon_w = np.maximum(pb.hwL[nc] + pb.skirt_extent[-1][nc], pb.hwR[nc] + pb.skirt_extent[1][nc]) + 18.0
                for m0 in mouths:
                    inz = (near >= m0 - 6) & (near <= m0 + 6)
                    zone |= inz & (dd <= canyon_w)
                    low |= inz & (HH < rim)
            zq = zone[:-1, :-1] | zone[1:, :-1] | zone[:-1, 1:] | zone[1:, 1:]
            lq = low[:-1, :-1] | low[1:, :-1] | low[:-1, 1:] | low[1:, 1:]
            skipq = zq & lq
        mo.add_grid(TG, TN, TC, TUV, TUV2, adaptive=True, skipq=skipq)
        # saias anti-fendas nas 4 bordas (descem 14 m)
        for edge, ecol in ((TG[0, :], TC[0, :]), (TG[-1, :], TC[-1, :]), (TG[:, 0], TC[:, 0]), (TG[:, -1], TC[:, -1])):
            e2 = edge.copy(); e2[:, 1] -= 14.0
            strip = np.stack([edge, e2], axis=0)
            nrm = np.repeat(np.array([[0.0, 1.0, 0.0]]), strip.shape[1], 0)[None].repeat(2, 0)
            cc = np.stack([ecol, ecol], axis=0)
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

    # setores (Doc 01 §20.3): um FBX de corredor e um de terreno por troço de sector_km do percurso principal
    import glob
    for old in glob.glob(os.path.join(OUT_DIR, f"{name}_corridor*.fbx")) + glob.glob(os.path.join(OUT_DIR, f"{name}_terrain*.fbx")):
        os.remove(old)
    sector_len = float(spec.get('sector_km', 15.0)) * 1000.0
    kd_main = kdtree.KDTree(main_pb.S)
    for i in range(main_pb.S):
        kd_main.insert((main_pb.P[i, 0], main_pb.P[i, 2], 0.0), i)
    kd_main.balance()

    def sector_of(ob):
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get('co', co)
        c = co.reshape(-1, 3).mean(axis=0)                     # Blender (x, z, y) = Unity (x, y, z) trocado
        _, j, _ = kd_main.find((float(c[0]), float(c[1]), 0.0))
        return int(main_pb.dist[j] // sector_len)

    groups = {}
    for kind, objs in (('corridor', objs_corr), ('terrain', objs_terr)):
        for ob in objs:
            groups.setdefault((kind, sector_of(ob)), []).append(ob)
    for (kind, k), objs in sorted(groups.items()):
        export(objs, os.path.join(OUT_DIR, f"{name}_{kind}_{k:02d}.fbx"))
    with open(os.path.join(OUT_DIR, f"{name}_obstacles.json"), 'w', encoding='utf-8') as fo:
        json.dump({'obstacles': [{'path': int(o['path']), 'dist': round(float(o['dist']), 2), 'u': round(float(o['u']), 4),
                                  'r': round(float(o['r']), 2)} for o in obstacles]}, fo)
    log(f"setores: {len(set(k for _, k in groups))} · obstáculos no traçado: {len(obstacles)}")
    ax = MeshOut("AXIS_TEST")
    ap = np.array([[[1.0, 2.0, 3.0], [11.0, 2.0, 3.0]], [[1.0, 2.0, 13.0], [11.0, 12.0, 13.0]]])
    ax.add_grid(ap, np.tile([0.0, 1.0, 0.0], (2, 2, 1)), np.ones((2, 2, 4)), np.zeros((2, 2, 2)), np.zeros((2, 2, 2)))
    axo, _, _ = ax.to_object(col_corr)
    export([axo], os.path.join(OUT_DIR, "axis_test.fbx"))

    # ---------------- dados: percurso principal (RDDC v1) e grafo de percursos (RDDG v2)
    def write_stations(f, pb):
        for i in range(pb.S):
            r = pb.rows[i]
            flags = (1 if r['gap'] else 0) | (2 if r['cave'] else 0)
            f.write(struct.pack('<f3f3f3f3f', r['dist'], *pb.P[i], *pb.T[i], *pb.R[i], *pb.U[i]))
            f.write(struct.pack('<fffiiiff', r['width'], r['bank'], r['slope'], flags, r['seg'], r['surf'], pb.ride[i, 0], pb.ride[i, 1]))
            f.write(pb.Wr[i].astype('<f4').tobytes())

    def write_names(f, names):
        f.write(struct.pack('<i', len(names)))
        for sid in names:
            b = sid.encode('utf-8')
            f.write(struct.pack('<i', len(b))); f.write(b)

    with open(os.path.join(OUT_DIR, f"{name}_course.bytes"), 'wb') as f:
        f.write(b'RDDC')
        f.write(struct.pack('<iiif', 1, main_pb.S, main_pb.N, main_pb.step))
        write_stations(f, main_pb)
        write_names(f, main_pb.names)
    ids = [pb.id for pb in paths]
    with open(os.path.join(OUT_DIR, f"{name}_graph.bytes"), 'wb') as f:
        f.write(b'RDDG')
        f.write(struct.pack('<ii', 2, len(paths)))
        for pb in paths:
            b = pb.id.encode('utf-8')
            f.write(struct.pack('<i', len(b))); f.write(b)
            f.write(struct.pack('<ifff', ids.index(pb.parent) if pb.parent else -1, pb.from_d, pb.to_d, pb.length))
            f.write(struct.pack('<iif', pb.S, pb.N, pb.step))
            write_stations(f, pb)
            write_names(f, pb.names)
    log(f"dados gravados: percurso principal + grafo ({len(paths)} percursos)")

    preview(name, paths, terrain, X0, X1, Z0, Z1)
    report = dict(name=name, stations=main_pb.S, length_km=round(main_pb.dist[-1] / 1000.0, 3), ring=main_pb.N, grid=main_pb.M,
                  paths=[dict(id=pb.id, km=round((pb.dist[-1] - pb.dist[0]) / 1000.0, 3), stations=pb.S,
                              inside_other=int(pb.removed.sum())) for pb in paths],
                  tris=stats['tris'], verts=stats['verts'], objects=stats['objects'], clipped_tris=stats['clipped_tris'],
                  terrain_tiles=len(tiles), terrain_heights=[round(float(hmin), 1), round(float(hmax), 1)],
                  elevation=[round(float(main_pb.P[:, 1].min()), 1), round(float(main_pb.P[:, 1].max()), 1)],
                  seconds=round(time.time() - T0, 1))
    json.dump(report, open(os.path.join(OUT_DIR, f"{name}_report.json"), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    log(f"relatório: {report}")


def preview(name, paths, terrain, X0, X1, Z0, Z1):
    """Mapa de cima (relevo sombreado com a paleta das camadas) com os percursos."""
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
    img = np.clip(pal[col.palA[idx]] * shade[..., None], 0, 1)

    def plot(pts, color, r=0):
        px = ((pts[:, 0] - X0) / span * size).astype(int)
        pz = ((pts[:, 2] - Z0) / span * size).astype(int)
        ok = (px >= r) & (px < size - r) & (pz >= r) & (pz < size - r)
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                img[pz[ok] + dz, px[ok] + dx] = color

    tints = [(0.95, 0.88, 0.7), (0.45, 0.85, 1.0), (1.0, 0.6, 0.9), (0.7, 1.0, 0.5)]
    for k, pb in enumerate(paths):
        plot(pb.Wr.reshape(-1, 3), tints[k % len(tints)])
    for pb in paths:
        plot(pb.P, (1, 1, 1), 0)
    plot(paths[0].P[[0]], (0.1, 0.9, 0.2), 4)
    for pb in paths[1:]:
        plot(pb.P[[0, -1]], (1.0, 0.3, 0.2), 3)
    im = bpy.data.images.new(f"{name}_preview", size, size, alpha=False)
    im.pixels.foreach_set(np.concatenate([img, np.ones((size, size, 1))], axis=-1).astype(np.float32).ravel())
    im.filepath_raw = os.path.join(OUT_DIR, f"{name}_preview.png")
    im.file_format = 'PNG'
    im.save()
    log("mapa gravado")


main()
