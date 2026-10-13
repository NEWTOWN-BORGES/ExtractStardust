"""
EXTRACT: STARDUST — RED DUST DIVIDE · rochas de todos os tamanhos (usado por rdd_build_route.py).

Dá vida ao canyon e parallax a 450 km/h, sem tocar nas linhas de corrida:
  - seixos e pedras (0,3–1 m) em grupos na borda do leito e nos filetes;
  - pedregulhos (1–5 m) ao pé das paredes e cones de cascalho (talus) por baixo das falésias;
  - blocos angulosos caídos (5–15 m) e lajes partidas inclinadas;
  - nas bancadas das paredes, pedregulhos e blocos a várias alturas;
  - gigantes (15–45 m): pilares, hoodoos e rochas equilibradas nas bancadas altas e na borda do planalto.

Formas: elipsoide com erosão (redonda), superelipsoide (bloco anguloso), laje achatada e pilar com chapéu.
Cores: as camadas da coluna geológica no sítio onde a rocha está (col.sample), como o resto da geologia.

Especificação: "rocks": {"density": 1.0}
"""
import math

import numpy as np

import rdd_geology as geo
from rdd_route_lib import MeshOut, grid_normals, colors, log

UP = np.array([0.0, 1.0, 0.0])


def _rot(rng, tilt_deg):
    """Rotação aleatória: guinada livre + inclinação até tilt_deg."""
    yaw = rng.uniform(0.0, 2.0 * math.pi)
    t1, t2 = math.radians(rng.uniform(-tilt_deg, tilt_deg)), math.radians(rng.uniform(-tilt_deg, tilt_deg))
    cy, sy = math.cos(yaw), math.sin(yaw)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    c1, s1 = math.cos(t1), math.sin(t1)
    Rx = np.array([[1, 0, 0], [0, c1, -s1], [0, s1, c1]])
    c2, s2 = math.cos(t2), math.sin(t2)
    Rz = np.array([[c2, -s2, 0], [s2, c2, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def _shape(mo, c, scale, R, exp, rough, rows, segs, col, seed):
    """Superelipsoide (exp < 1 = anguloso) rodado, com erosão por ruído 3D e estratos."""
    th = np.linspace(0.0, math.pi, rows)[:, None]
    ph = np.linspace(0.0, 2.0 * math.pi, segs + 1)[None, :]
    st, ct = np.sin(th), np.cos(th)
    sp, cp = np.sin(ph), np.cos(ph)

    def sp_(v):
        return np.sign(v) * np.abs(v) ** exp

    d = np.stack([sp_(st) * sp_(cp), sp_(ct) * np.ones_like(ph), sp_(st) * sp_(sp)], axis=-1) * scale
    d = d @ R.T
    pts = c + d
    k = max(float(np.max(scale)), 0.3)
    n = geo.fbm3(pts[..., 0] / (k * 1.1), pts[..., 1] / (k * 0.9), pts[..., 2] / (k * 1.1), 3, seed=seed)
    pts = c + d * (1.0 + rough * n)[..., None]
    pts[:, -1] = pts[:, 0]
    nrm = grid_normals(pts)
    flip = np.mean(np.einsum('ijk,ijk->ij', nrm, pts - c)) < 0
    if flip:
        nrm = -nrm
    relief, hard, pa, pb, mix, _ = col.sample(pts[..., 0], pts[..., 1], pts[..., 2])
    uv = np.stack([np.repeat(ph, rows, 0) * k, pts[..., 1] / 3.0], axis=-1)
    mo.add_grid(pts, nrm, colors(np.full(pts.shape[:2], 0.75), pa, pb, np.zeros(pts.shape[:2])), uv,
                np.stack([hard, mix], axis=-1), flip=flip)
    return 2 * (rows - 1) * segs


def rock(mo, p, size, kind, rng, col, seed):
    """Uma rocha pousada em p (meio enterrada). Devolve o número de triângulos."""
    if kind == 'pebble':
        s = size * np.array([rng.uniform(0.8, 1.3), rng.uniform(0.45, 0.7), rng.uniform(0.8, 1.3)])
        return _shape(mo, p - UP * s[1] * 0.35, s, _rot(rng, 25), 0.85, 0.25, 4, 6, col, seed)
    if kind == 'boulder':
        s = size * np.array([rng.uniform(0.8, 1.3), rng.uniform(0.5, 0.8), rng.uniform(0.8, 1.3)])
        return _shape(mo, p - UP * s[1] * 0.3, s, _rot(rng, 15), 0.8, 0.28, 8, 12, col, seed)
    if kind == 'block':
        s = size * np.array([rng.uniform(0.9, 1.4), rng.uniform(0.6, 1.0), rng.uniform(0.7, 1.2)])
        return _shape(mo, p - UP * s[1] * 0.25, s, _rot(rng, 22), 0.35, 0.12, 8, 12, col, seed)
    if kind == 'slab':
        s = size * np.array([rng.uniform(1.2, 1.8), rng.uniform(0.18, 0.3), rng.uniform(0.8, 1.2)])
        return _shape(mo, p - UP * s[1] * 0.2, s, _rot(rng, 35), 0.3, 0.1, 8, 12, col, seed)
    # pilar / hoodoo / rocha equilibrada: coluna + chapéu
    h = size
    w = h * rng.uniform(0.16, 0.26)
    R = _rot(rng, 4)
    n = _shape(mo, p + UP * (h * 0.42), np.array([w, h * 0.5, w * rng.uniform(0.8, 1.2)]), R, 0.45, 0.16, 10, 12, col, seed)
    cap = w * rng.uniform(1.4, 2.2)
    n += _shape(mo, p + UP * (h * 0.92 + cap * 0.3), np.array([cap, cap * rng.uniform(0.45, 0.7), cap * rng.uniform(0.8, 1.2)]),
                _rot(rng, 12), 0.4, 0.14, 8, 12, col, seed + 1)
    return n


def scatter(pb, cfg, col, seed, terrain, ksp):
    """Espalha rochas ao longo de um percurso. Devolve a lista de MeshOut (um por troço de ~600 m)."""
    rng = np.random.default_rng(seed + 9100)
    dens = float(cfg.get('density', 1.0))
    N, M = pb.N, pb.M
    out, mo, tris, count = [], None, 0, {}
    chunk = 200
    step = max(1, int(round(9.0 / pb.step)))

    def put(p, size, kind):
        nonlocal tris
        tris += rock(mo, p, size, kind, rng, col, int(rng.integers(1 << 30)))
        count[kind] = count.get(kind, 0) + 1

    for i in range(2, pb.S - 2, step):
        if mo is None:
            mo = MeshOut(f"GEO_Rocks_{pb.id[:2]}_{i // chunk:03d}")
        ok_ring = not (pb.gap[i] or pb.cave[i])
        ring = pb.Wr[i]
        arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))]
        arc -= arc[N // 2]
        for side in (-1, 1):
            ride = pb.ride[i, 0] if side < 0 else pb.ride[i, 1]

            lip = abs(arc[0]) if side < 0 else abs(arc[-1])
            width = float(pb.rows[i]['width'])

            def ring_point(size, extra=0.0):
                """Ponto no anel com a borda interior da rocha ≥ 1 m para lá do limite de corrida (None se não cabe)."""
                reach = ride + 1.0 + size + extra
                if reach + size * 0.5 > lip:
                    return None
                k = int(np.clip(np.searchsorted(arc, side * reach), 1, N - 2))
                col_k = pb.ringL + k
                if pb.removed[i, col_k] or abs(pb.Ng[i, col_k, 1]) < 0.72:
                    return None
                return ring[k]

            if ok_ring:
                # seixos e pedras em grupos, logo fora das linhas de corrida (espalham-se para fora e ao longo)
                if rng.random() < 0.55 * dens:
                    p = ring_point(0.9, rng.uniform(0.0, 1.5))
                    if p is not None:
                        out_dir = pb.Rh[i] * side
                        for _ in range(int(rng.integers(2, 6))):
                            q = p + out_dir * rng.uniform(0.0, 2.5) + pb.T[i] * rng.uniform(-3.0, 3.0)
                            put(q, rng.uniform(0.25, 0.9), 'pebble')
                if rng.random() < 0.15 * dens:
                    size = rng.uniform(1.2, 4.5)
                    p = ring_point(size, rng.uniform(0.0, 4.0))
                    if p is not None:
                        put(p, size, 'boulder')
                if width >= 45.0 and rng.random() < 0.04 * dens:
                    size = rng.uniform(5.0, 13.0)
                    p = ring_point(size * 1.3, rng.uniform(0.0, 6.0))
                    if p is not None:
                        put(p, size, 'block' if rng.random() < 0.7 else 'slab')
            # paredes: cone de cascalho ao pé e rochas pousadas nas bancadas
            cols = np.arange(2, ksp - 2) if side < 0 else np.arange(pb.ringR + 3, M - 3)
            if rng.random() < 0.025 * dens and not pb.cave[i]:
                foot = ksp - 3 if side < 0 else pb.ringR + 3
                if not pb.removed[i, foot]:
                    c0 = pb.G[i, foot]
                    for _ in range(int(rng.integers(6, 15))):
                        q = c0 + pb.Rh[i] * side * rng.uniform(1.0, 7.0) + pb.T[i] * rng.uniform(-6.0, 6.0)
                        put(q, rng.uniform(0.6, 3.2), 'boulder' if rng.random() < 0.6 else 'block')
            if rng.random() < 0.08 * dens and not pb.cave[i]:
                k = int(rng.choice(cols))
                if not pb.removed[i, k] and abs(pb.Ng[i, k, 1]) > 0.8:
                    put(pb.G[i, k], rng.uniform(2.0, 8.0), 'boulder' if rng.random() < 0.5 else 'block')
            # gigantes: bancadas altas e borda do planalto
            if i % 70 < step and rng.random() < 0.45 * dens and not pb.cave[i]:
                floor = pb.P[i, 1]
                high = [k for k in cols if pb.G[i, k, 1] > floor + 35.0 and abs(pb.Ng[i, k, 1]) > 0.8 and not pb.removed[i, k]]
                if high and rng.random() < 0.6:
                    p = pb.G[i, int(rng.choice(high))]
                else:
                    kk = 0 if side < 0 else M - 1
                    edge = pb.G[i, kk]
                    out_dir = pb.Rh[i] * side
                    q = edge + out_dir * rng.uniform(25.0, 160.0)
                    q[1] = float(terrain(np.array([q[0]]), np.array([q[2]]))[0])
                    # borda cortada por outro canyon, ou terreno muito abaixo dela (dentro de um canyon): não
                    p = None if pb.removed[i, kk] or q[1] < edge[1] - 12.0 else q
                if p is not None:
                    put(p, rng.uniform(15.0, 45.0), 'pillar' if rng.random() < 0.65 else 'block')
        # planalto (troços abertos): hoodoos, blocos e grupos de pedregulhos até 400 m da pista, para parallax
        op = float(pb.rows[i].get('open', 0.0))
        if op > 0.4 and rng.random() < 0.5 * op * dens:
            side = -1 if rng.random() < 0.5 else 1
            ride = pb.ride[i, 0] if side < 0 else pb.ride[i, 1]
            off = ride + 12.0 + rng.uniform(0.0, 1.0) ** 1.8 * 390.0          # mais rochas perto da pista
            q = pb.P[i] + pb.Rh[i] * side * off + pb.T[i] * rng.uniform(-4.0, 4.0)
            q[1] = float(terrain(np.array([q[0]]), np.array([q[2]]))[0])
            r = rng.random() if q[1] > pb.P[i, 1] - 12.0 else 9.0          # abaixo do planalto = dentro de um canyon
            if r > 1.0:
                pass
            elif r < 0.25:
                put(q, rng.uniform(10.0, 32.0), 'pillar')
            elif r < 0.55:
                put(q, rng.uniform(4.0, 14.0), 'block' if rng.random() < 0.7 else 'slab')
            else:
                for _ in range(int(rng.integers(2, 6))):
                    put(q + np.array([rng.uniform(-8, 8), 0.0, rng.uniform(-8, 8)]), rng.uniform(1.0, 4.5), 'boulder')
        if i // chunk != (i + step) // chunk or i + step >= pb.S - 2:
            if not mo.empty():
                out.append(mo)
            mo = None
    log(f"rochas em {pb.id}: {sum(count.values())} ({', '.join(f'{k} {v}' for k, v in sorted(count.items()))}), {tris // 1000}k triângulos")
    return out
