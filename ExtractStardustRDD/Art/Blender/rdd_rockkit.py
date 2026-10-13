"""
EXTRACT: STARDUST — RED DUST DIVIDE · kit de rocha e destroços (usado por rdd_build_route.py).

Coisas que passam por cima e ao lado da pista a 450 km/h (parallax = sensação de velocidade):
  - arch:     arco natural (ponte de arenito) de parede a parede por cima da pista, pernas enterradas nas paredes;
  - boulders: pedregulhos caídos ao pé das paredes e nas bancadas, fora das linhas de corrida;
  - wreck:    esqueleto de uma nave de extração caída atravessada no canyon (costelas, algumas partidas, e espinha).

Especificação (no JSON do percurso):
  "features": [
    {"type": "arch", "path": "main", "at": 1300, "clearance": 14, "thick": 9, "depth": 16},
    {"type": "wreck", "path": "main", "from": 13400, "to": 13700, "clearance": 12, "tilt": 14},
  ],
  "boulders": {"every": 14, "chance": 0.55}
"""
import math

import numpy as np

import rdd_geology as geo
from rdd_route_lib import MeshOut, grid_normals, colors, log


def _station(pb, d):
    return int(np.clip(np.searchsorted(pb.dist, d), 1, pb.S - 2))


def _row_profile(pb, i):
    """Perfil lateral da superfície (grelha completa) na estação i: coordenada lateral e altura."""
    G = pb.G[i]
    lat = (G[:, 0] - pb.P[i, 0]) * pb.Rh[i, 0] + (G[:, 2] - pb.P[i, 2]) * pb.Rh[i, 2]
    return lat, G[:, 1]


def _anchor(lat, y, height, side, start):
    """Primeiro ponto (a partir do centro, para o lado) onde a parede atinge a altura pedida."""
    order = np.arange(len(lat))
    sel = order[lat >= start] if side > 0 else order[lat <= start][::-1]
    for k in sel:
        if y[k] >= height:
            return lat[k]
    return lat[sel[-1]] if len(sel) else start


def _tube(centre, normal_dir, depth_dir, half_h, half_d, col, seed, segs=36, rough=0.18):
    """Tubo de rocha ao longo de uma linha: secção superelíptica com erosão (ruído 3D) e estratos."""
    n = len(centre)
    th = np.linspace(0.0, 2.0 * math.pi, segs + 1)
    c, s = np.cos(th), np.sin(th)
    se = np.sign(c) * np.abs(c) ** 0.8, np.sign(s) * np.abs(s) ** 0.8
    pts = (centre[:, None, :]
           + normal_dir[:, None, :] * (se[0][None, :, None] * half_h[:, None, None])
           + depth_dir[:, None, :] * (se[1][None, :, None] * half_d[:, None, None]))
    x, y, z = pts[..., 0], pts[..., 1], pts[..., 2]
    ero = rough * geo.fbm3(x / 11.0, y / 7.0, z / 11.0, 4, seed=seed) + 0.07 * geo.fbm3(x / 3.5, y / 2.5, z / 3.5, 2, seed=seed + 1)
    relief, hard, pa, pbb, mix, _ = col.sample(x, y, z)
    radial = pts - centre[:, None, :]
    pts = pts + radial * (ero + 0.04 * relief)[..., None]
    pts[:, -1] = pts[:, 0]                                    # fecha a secção
    nrm = grid_normals(pts)
    out = np.einsum('ijk,ijk->ij', nrm, pts - centre[:, None, :])
    flip = np.mean(out) < 0
    if flip:
        nrm = -nrm
    uv = np.stack([np.linspace(0, 12, segs + 1)[None, :].repeat(n, 0), pts[..., 1] / 4.0], axis=-1)
    C = colors(np.full(pts.shape[:2], 0.75), pa, pbb, np.zeros(pts.shape[:2]))
    return pts, nrm, C, uv, np.stack([hard, mix], axis=-1), flip


def arch(pb, f, col, seed):
    """Arco natural de parede a parede por cima da pista (pernas mais grossas, enterradas 10 m nas paredes)."""
    i = _station(pb, float(f['at']))
    lat, y = _row_profile(pb, i)
    floor = float(pb.P[i, 1])
    clearance = float(f.get('clearance', 14.0))
    thick = float(f.get('thick', 9.0))
    depth = float(f.get('depth', 16.0))
    apex = floor + clearance + thick * 0.5
    spring = apex - float(f.get('sag', 7.0))
    # as pernas tocam nas paredes acima das linhas de corrida (que podem subir pelas paredes) + 7 m de folga
    N = pb.N
    y_ride = floor
    for j in range(max(1, i - 4), min(pb.S - 1, i + 5)):
        ring = pb.Wr[j]
        arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))]
        arc -= arc[N // 2]
        y_ride = max(y_ride, float(np.interp(-pb.ride[j, 0], arc, ring[:, 1])), float(np.interp(pb.ride[j, 1], arc, ring[:, 1])))
    spring = max(spring, y_ride + 7.0 + thick * 0.5)
    apex = max(apex, spring + 2.0)
    half_ring = max(abs(lat[pb.ringL]), abs(lat[pb.ringR]))
    lL = _anchor(lat, y, spring, -1, -half_ring * 0.5)
    lR = _anchor(lat, y, spring, 1, half_ring * 0.5)
    mid = 0.5 * (lL + lR)
    a = (apex - spring) / max(1.0, (lR - mid) ** 2)
    l = np.linspace(lL - 12.0, lR + 12.0, 72)
    yc = apex - a * (l - mid) ** 2
    P0 = pb.P[i].copy(); P0[1] = 0.0
    Rh, Th = pb.Rh[i], np.array([pb.Th[i, 0], 0.0, pb.Th[i, 1]])
    centre = P0[None, :] + Rh[None, :] * l[:, None] + np.array([0.0, 1.0, 0.0])[None, :] * yc[:, None]
    tg = np.gradient(centre, axis=0)
    tg /= np.linalg.norm(tg, axis=1, keepdims=True)
    nd = np.cross(Th[None, :], tg)
    nd /= np.linalg.norm(nd, axis=1, keepdims=True)
    nd *= np.sign(nd[:, 1:2] + 1e-6)                          # para cima
    e = geo.smoothstep(0.92, 1.12, np.abs(l - mid) / max(1.0, (lR - lL) * 0.5))      # só engrossa dentro das paredes
    half_h = thick * 0.5 * (1.0 + 1.6 * e)
    half_d = depth * 0.5 * (1.0 + 1.1 * e)
    mo = MeshOut(f"GEO_Arch_{pb.id[:2]}_{int(f['at'])}")
    pts, nrm, C, uv, uv2, flip = _tube(centre, nd, np.repeat(Th[None, :], len(l), 0), half_h, half_d, col, seed + int(f['at']))
    mo.add_grid(pts, nrm, C, uv, uv2, flip=flip)
    log(f"arco em {pb.id} {f['at']} m: vão {lR - lL:.0f} m, folga {clearance:.0f} m")
    return mo


def boulders(pb, cfg, col, seed):
    """Pedregulhos caídos fora das linhas de corrida (pé das paredes, filetes e bancadas suaves)."""
    rng = np.random.default_rng(seed + 4242)
    every = float(cfg.get('every', 14.0))
    chance = float(cfg.get('chance', 0.55))
    out, mo, count = [], None, 0
    step = max(1, int(round(every / pb.step)))
    N = pb.N
    for i in range(2, pb.S - 2, step):
        if pb.gap[i] or pb.cave[i] or pb.removed[i, pb.ringL:pb.ringR + 1].any():
            continue
        for side in (-1, 1):
            if rng.random() > chance:
                continue
            # ponto do anel um pouco para lá do limite de corrida (arco medido a partir do eixo)
            ring = pb.Wr[i]
            seg = np.linalg.norm(np.diff(ring, axis=0), axis=1)
            arc = np.r_[0.0, np.cumsum(seg)]
            arc -= arc[N // 2]
            ride = pb.ride[i, 0] if side < 0 else pb.ride[i, 1]
            target = side * ride * rng.uniform(1.06, 1.35)
            k = int(np.clip(np.searchsorted(arc, target), 1, N - 2))
            p = ring[k]
            nrm = np.cross(ring[k + 1] - ring[k - 1], pb.P[i + 1] - pb.P[i - 1])
            nrm /= max(np.linalg.norm(nrm), 1e-6)
            if nrm[1] < 0:
                nrm = -nrm
            if nrm[1] < 0.75:
                continue                                       # parede íngreme: não fica pedra pousada
            r = rng.uniform(1.2, 4.5) * (1.0 + 0.8 * (rng.random() < 0.12))
            if mo is None:
                mo = MeshOut(f"GEO_Boulders_{pb.id[:2]}_{i // 400:03d}")
            _boulder(mo, p - nrm * r * 0.35, r, rng, col, seed + i * 3 + side)
            count += 1
        if mo is not None and (i // 400) != ((i + step) // 400):
            out.append(mo); mo = None
    if mo is not None:
        out.append(mo)
    log(f"pedregulhos em {pb.id}: {count}")
    return out


def _boulder(mo, c, r, rng, col, seed, rows=9, segs=14):
    th = np.linspace(0.0, math.pi, rows)[:, None]
    ph = np.linspace(0.0, 2.0 * math.pi, segs + 1)[None, :]
    d = np.stack([np.sin(th) * np.cos(ph), np.cos(th) * np.ones_like(ph), np.sin(th) * np.sin(ph)], axis=-1)
    sx, sy, sz = rng.uniform(0.8, 1.3), rng.uniform(0.45, 0.75), rng.uniform(0.8, 1.3)
    rot = rng.uniform(0, 2 * math.pi)
    cr, sr = math.cos(rot), math.sin(rot)
    d = d * np.array([sx, sy, sz])
    d = np.stack([d[..., 0] * cr - d[..., 2] * sr, d[..., 1], d[..., 0] * sr + d[..., 2] * cr], axis=-1)
    pts = c + d * r
    n = geo.fbm3(pts[..., 0] / (r * 1.3), pts[..., 1] / (r * 1.1), pts[..., 2] / (r * 1.3), 3, seed=seed)
    pts = c + d * r * (1.0 + 0.28 * n)[..., None]
    pts[:, -1] = pts[:, 0]
    nrm = grid_normals(pts)
    if np.mean(np.einsum('ijk,ijk->ij', nrm, pts - c)) < 0:
        nrm = -nrm
        flip = True
    else:
        flip = False
    relief, hard, pa, pbb, mix, _ = col.sample(pts[..., 0], pts[..., 1], pts[..., 2])
    uv = np.stack([ph.repeat(rows, 0) * r, pts[..., 1] / 3.0], axis=-1)
    mo.add_grid(pts, nrm, colors(np.full(pts.shape[:2], 0.75), pa, pbb, np.zeros(pts.shape[:2])), uv, np.stack([hard, mix], axis=-1), flip=flip)


def wreck(pb, f, col, seed):
    """
    Esqueleto de nave de extração caída atravessada no canyon: costelas grossas e irregulares (umas tortas, outras
    partidas ou afundadas na areia), chapas do casco presas entre costelas de um dos lados (com rasgões) e a espinha
    por cima. Objetos GEO_Wreck_* recebem material de metal ferrugento no Unity.
    """
    rng = np.random.default_rng(seed + int(f['from']))
    d0, d1 = float(f['from']), float(f['to'])
    spacing = float(f.get('spacing', 14.0))
    clearance = float(f.get('clearance', 12.0))
    tilt = float(f.get('tilt', 14.0))
    mo = MeshOut(f"GEO_Wreck_{pb.id[:2]}_{int(d0)}")
    up = np.array([0.0, 1.0, 0.0])
    tops, full = [], []
    nrib = max(2, int((d1 - d0) / spacing))
    hull_side = -1 if rng.random() < 0.5 else 1
    for k in range(nrib + 1):
        d = d0 + (d1 - d0) * k / nrib + rng.uniform(-3.0, 3.0)
        i = _station(pb, d)
        lat, y = _row_profile(pb, i)
        floor = float(pb.P[i, 1])
        sink = rng.uniform(0.0, 4.0)
        apex = floor + clearance + 6.0 * math.sin(math.pi * k / nrib) + rng.uniform(-2.5, 2.5) + 2.0 - sink
        half_ring = max(abs(lat[pb.ringL]), abs(lat[pb.ringR]))
        lL = _anchor(lat, y, floor + 7.0, -1, -half_ring * 0.4) - 3.0      # pernas fora das linhas de corrida
        lR = _anchor(lat, y, floor + 7.0, 1, half_ring * 0.4) + 3.0
        mid = 0.5 * (lL + lR)
        broken = rng.random() < 0.3
        lo, hi = (lL, lR) if not broken else ((lL, mid + rng.uniform(-5, 10)) if rng.random() < 0.5 else (mid + rng.uniform(-10, 5), lR))
        l = np.linspace(lo, hi, 40)
        u = (l - mid) / max(1.0, (lR - lL) * 0.5)
        roll = math.tan(math.radians(rng.uniform(-7.0, 7.0)))           # costela torta para um lado
        yc = floor - 3.0 - sink + (apex - floor + 3.0 + sink) * np.clip(1.0 - np.abs(u) ** 4, 0.0, 1.0) ** 0.25 + roll * (l - mid)   # laterais quase verticais
        P0 = pb.P[i].copy(); P0[1] = 0.0
        Rh, Th = pb.Rh[i], np.array([pb.Th[i, 0], 0.0, pb.Th[i, 1]])
        lean = math.tan(math.radians(tilt + rng.uniform(-12.0, 12.0)))   # inclinação do impacto, diferente em cada costela
        centre = P0 + Rh * l[:, None] + up * yc[:, None] + Th * (lean * (yc - floor))[:, None]
        tg = np.gradient(centre, axis=0)
        tg /= np.linalg.norm(tg, axis=1, keepdims=True)
        nd = np.cross(Th[None, :], tg)
        nd /= np.linalg.norm(nd, axis=1, keepdims=True)
        axis_pt = P0 + Rh * mid + up * (floor - 3.0)
        nd *= np.sign(np.einsum('ij,ij->i', nd, centre - axis_pt) + 1e-6)[:, None]     # para fora do casco
        pts, nrm, C, uv, uv2, flip = _tube(centre, nd, np.repeat(Th[None, :], len(l), 0), np.full(len(l), 1.3),
                                           np.full(len(l), 2.3), col, seed + k, segs=10, rough=0.0)
        mo.add_grid(pts, nrm, C, uv, uv2, flip=flip)
        if not broken:
            tops.append(centre[len(l) // 2])
            full.append((centre, nd, u))
    # chapas do casco entre costelas inteiras, de um dos lados, com rasgões
    plates = 0
    for k in range(len(full) - 1):
        if rng.random() < 0.3:
            continue
        (ca, na, ua), (cb, nb, ub) = full[k], full[k + 1]
        lo_u, hi_u = (-1.0, rng.uniform(-0.45, 0.0)) if hull_side < 0 else (rng.uniform(0.0, 0.45), 1.0)
        ia = np.flatnonzero((ua >= lo_u) & (ua <= hi_u))
        ib = np.flatnonzero((ub >= lo_u) & (ub <= hi_u))
        n = min(len(ia), len(ib))
        if n < 3:
            continue
        rowA = ca[ia[:n]] + na[ia[:n]] * 1.4
        rowB = cb[ib[:n]] + nb[ib[:n]] * 1.4
        g = np.stack([rowA, rowB], axis=0)
        g[..., 1] += 0.3 * geo.fbm3(g[..., 0] / 3.0, g[..., 1] / 3.0, g[..., 2] / 3.0, 2, seed=seed + 7 + k)
        nrm = grid_normals(g)
        zero = np.zeros(g.shape[:2])
        Cg = colors(np.full(g.shape[:2], 0.75), zero, zero, zero)
        uvg = np.zeros(g.shape[:2] + (2,))
        mo.add_grid(g, nrm, Cg, uvg, uvg)
        mo.add_grid(g, -nrm, Cg, uvg, uvg, flip=True)              # chapa vista dos dois lados
        plates += 1
    if len(tops) >= 2:
        sp = np.array(tops)
        tg = np.gradient(sp, axis=0)
        tg /= np.linalg.norm(tg, axis=1, keepdims=True)
        side = np.cross(tg, up)
        side /= np.maximum(np.linalg.norm(side, axis=1, keepdims=True), 1e-6)
        upv = np.cross(side, tg)
        pts, nrm, C, uv, uv2, flip = _tube(sp, upv, side, np.full(len(sp), 1.6), np.full(len(sp), 2.6), col, seed + 99, segs=10, rough=0.0)
        mo.add_grid(pts, nrm, C, uv, uv2, flip=flip)
    log(f"destroço em {pb.id} {d0:.0f}-{d1:.0f} m: {nrib + 1} costelas, {plates} chapas")
    return mo
