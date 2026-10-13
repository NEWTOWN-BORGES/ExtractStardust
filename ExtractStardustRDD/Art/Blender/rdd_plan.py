"""
EXTRACT: STARDUST — RED DUST DIVIDE · planeador rápido de percursos (Python normal, sem Blender).

  python rdd_plan.py ../Courses/red_dust_divide.json [pasta_saida]

Integra o eixo exatamente como o construtor, estima a largura real do canyon (escadaria da coluna geológica até ao
planalto), procura sobreposições do canyon consigo próprio, desenha o mapa de cima e o perfil de altitude por
setores e estima o tempo com o modelo de aderência da nave (aderência ∝ 0,10 + (v/125)²; travagem e aceleração).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rdd_geology as geo  # noqa: E402

EASED = ['width', 'bank', 'slope', 'curv', 'wallL', 'wallR', 'filletL', 'filletR', 'angleL', 'angleR',
         'lipL', 'lipR', 'rideL', 'rideR', 'ceil', 'open']
PLATEAU = 318.0
TOP, BOOST, ACC, BRAKE, GRAV = 118.0, 133.0, 26.0, 44.0, 22.0


def integrate(spec):
    """Mesmo cálculo que rdd_route_lib.integrate (posições, distância, parâmetros por estação)."""
    d = spec['defaults']
    step = float(spec.get('step', 3.0))
    cur = {k: float(d.get(k, 0.0)) for k in EASED if k != 'curv'}
    r0 = float(d.get('radius', 0.0))
    cur['curv'] = 0.0 if r0 == 0 else 1.0 / r0
    pos = np.array(spec['start']['pos'], dtype=np.float64)
    yaw = math.radians(spec['start'].get('yaw', 0.0))
    rows = [dict(cur, pos=pos.copy(), dist=0.0, seg=0, gap=0, cave=0)]
    dist = 0.0
    for si, seg in enumerate(spec['segments']):
        target = dict(cur)
        for k in EASED:
            if k == 'curv':
                if 'radius' in seg:
                    target['curv'] = 0.0 if float(seg['radius']) == 0 else 1.0 / float(seg['radius'])
            elif k in seg:
                target[k] = float(seg[k])
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
            pos = pos + np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)]) * ds
            dist += ds
            row = {kk: start[kk] + (target[kk] - start[kk]) * e_end for kk in EASED}
            row['curv'] = curv
            rows.append(dict(row, pos=pos.copy(), dist=dist, seg=si, gap=int(seg.get('gap', 0)), cave=int(seg.get('cave', 0))))
        cur = target
    return rows, step


GRIP_LAT, GRIP_BASE, GRIP_REF, GRIP_CAP = 85.0, 0.10, 125.0, 0.55


def speed_limit(r, bank_deg, margin=0.82):
    """Igual a CraftTuning.CornerSpeed (aderência com teto + bank)."""
    if r <= 0 or not math.isfinite(r):
        return TOP
    kappa = 1.0 / r
    tb = GRAV * math.tan(math.radians(min(abs(bank_deg), 60.0)))
    a = GRIP_LAT * margin
    v_cap = math.sqrt((a * GRIP_CAP + tb) / kappa)
    v_knee = GRIP_REF * math.sqrt(max(0.0, GRIP_CAP - GRIP_BASE))
    if v_cap >= v_knee:
        return min(TOP, v_cap)
    k2 = a / GRIP_REF ** 2
    return min(TOP, math.sqrt((a * GRIP_BASE + tb) / (kappa - k2)) if kappa > k2 else v_cap)


def main():
    spec_path = os.path.abspath(sys.argv[1])
    spec = json.load(open(spec_path, encoding='utf-8'))
    out_dir = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(HERE, '..', 'Export', spec['name'])
    os.makedirs(out_dir, exist_ok=True)
    rows, step = integrate(spec)
    P = np.array([r['pos'] for r in rows])
    dist = np.array([r['dist'] for r in rows])
    seg = np.array([r['seg'] for r in rows])
    width = np.array([r['width'] for r in rows])
    opn = np.array([r['open'] for r in rows])
    curv = np.array([r['curv'] for r in rows])
    bank = np.array([r['bank'] for r in rows])
    col = geo.Column(int(spec.get('seed', 1)))
    # largura do canyon: escadaria das camadas desde o pé da parede até ao planalto (troços abertos: quase nada)
    foot = P[:, 1] + np.array([max(r['wallL'], r['wallR']) for r in rows])
    ext = np.where(opn > 0.5, 25.0, np.maximum(0.0, col.X(np.full(len(rows), PLATEAU)) - col.X(np.minimum(foot, PLATEAU - 1.0))))
    half = width * 0.5 + np.array([max(r['filletL'], r['filletR']) for r in rows]) + ext
    # sobreposição do canyon consigo próprio (pares afastados > 2,5 km ao longo do percurso)
    xz = P[:, [0, 2]]
    sub = np.arange(0, len(rows), max(1, int(40 / step)))
    warn = []
    for a in sub:
        far = sub[np.abs(dist[sub] - dist[a]) > 2500.0]
        if len(far) == 0:
            continue
        dd = np.linalg.norm(xz[far] - xz[a], axis=1)
        need = (half[far] + half[a]) * 0.85
        bad = far[dd < need]
        if len(bad):
            b = bad[np.argmin(dd[dd < need])]
            warn.append((dist[a], dist[b], float(np.linalg.norm(xz[b] - xz[a])), float((half[a] + half[b]) * 0.85)))
    # tempo estimado: limite por curva, aceleração para a frente, travagem para trás
    vlim = np.array([speed_limit(1.0 / abs(c) if abs(c) > 1e-6 else float('inf'), b) for c, b in zip(curv, bank)])
    v = vlim.copy()
    v[0] = 0.0
    for i in range(1, len(v)):
        v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2.0 * ACC * step))
    for i in range(len(v) - 2, -1, -1):
        v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2.0 * BRAKE * step))
    dt = step / np.maximum(v[1:], 5.0)
    t = np.r_[0.0, np.cumsum(dt)]
    names = [s['id'] for s in spec['segments']]
    sectors = spec.get('sectors', [])
    print(f"{spec['name']}: {dist[-1] / 1000:.1f} km · {len(rows)} estações · tempo estimado {t[-1] / 60:.1f} min "
          f"(média {dist[-1] / t[-1] * 3.6:.0f} km/h) · caixa {np.ptp(P[:, 0]) / 1000:.1f} × {np.ptp(P[:, 2]) / 1000:.1f} km · "
          f"altitude {P[:, 1].min():.0f}..{P[:, 1].max():.0f} m")
    for sc in sectors:
        a, b = np.searchsorted(dist, sc['from']), np.searchsorted(dist, sc['to'])
        b = min(b, len(t) - 1)
        print(f"  {sc['id']:<22} {sc['from'] / 1000:6.1f}-{sc['to'] / 1000:6.1f} km  {t[a] / 60:5.2f}-{t[b] / 60:5.2f} min  "
              f"v mín {v[a:b + 1].min() * 3.6:4.0f} km/h  alt {P[a:b + 1, 1].min():4.0f}..{P[a:b + 1, 1].max():4.0f}")
    slow = []
    for i in range(1, len(v) - 1):
        if v[i] < 0.75 * TOP and v[i] < v[i - 1] - 1e-6 and v[i] <= v[i + 1]:
            slow.append((dist[i], names[seg[i]], v[i] * 3.6))
        elif v[i] < 0.75 * TOP and v[i] <= v[i - 1] + 1e-6 and v[i] < v[i + 1] - 1e-6 and (not slow or dist[i] - slow[-1][0] > 150):
            slow.append((dist[i], names[seg[i]], v[i] * 3.6))
    print(f"  travagens fortes (mínimos locais < 320 km/h): {len(slow)}")
    for d_, n_, k_ in slow[:40]:
        print(f"    {d_ / 1000:6.2f} km  {k_:4.0f} km/h  {n_}")
    print(f"  sobreposições do canyon consigo próprio: {len(warn)}")
    for a, b, dd, need in warn[:25]:
        print(f"    {a / 1000:6.2f} km <-> {b / 1000:6.2f} km: {dd:5.0f} m (precisa {need:5.0f} m)")
    draw(spec, out_dir, P, dist, sectors, half, t)


def draw(spec, out_dir, P, dist, sectors, half, t):
    from PIL import Image, ImageDraw
    size = 1400
    pad = 1200.0
    x0, x1 = P[:, 0].min() - pad, P[:, 0].max() + pad
    z0, z1 = P[:, 2].min() - pad, P[:, 2].max() + pad
    span = max(x1 - x0, z1 - z0)
    sc = size / span
    im = Image.new('RGB', (size, size + 260), (24, 20, 18))
    dr = ImageDraw.Draw(im)
    cols = [(230, 120, 70), (240, 190, 90), (120, 200, 230), (220, 80, 60), (170, 120, 220), (90, 200, 140),
            (240, 150, 200), (200, 200, 200), (250, 230, 120)]

    def px(x, z):
        return ((x - x0) * sc, size - (z - z0) * sc)

    def sector_of(dv):
        for k, s in enumerate(sectors):
            if s['from'] <= dv < s['to']:
                return k
        return len(sectors) - 1 if sectors else 0

    for i in range(0, len(P) - 1, 3):
        k = sector_of(dist[i])
        c = cols[k % len(cols)]
        w = max(1, int(half[i] * 2 * sc))
        dr.line([px(P[i, 0], P[i, 2]), px(P[i + 3 if i + 3 < len(P) else -1, 0], P[i + 3 if i + 3 < len(P) else -1, 2])],
                fill=tuple(int(v * 0.35) for v in c), width=w)
    for i in range(0, len(P) - 1, 2):
        k = sector_of(dist[i])
        dr.line([px(P[i, 0], P[i, 2]), px(P[i + 1, 0], P[i + 1, 2])], fill=cols[k % len(cols)], width=2)
    for k, s in enumerate(sectors):
        i = int(np.searchsorted(dist, s['from']))
        x, y = px(P[i, 0], P[i, 2])
        dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(255, 255, 255))
        dr.text((x + 8, y - 6), f"{k + 1} {s['id']}", fill=(255, 255, 255))
    x, y = px(P[0, 0], P[0, 2])
    dr.rectangle([x - 6, y - 6, x + 6, y + 6], fill=(60, 255, 90))
    dr.text((10, 10), f"{spec['name']} · {dist[-1] / 1000:.1f} km · {t[-1] / 60:.1f} min · escala {span / 1000:.1f} km", fill=(255, 255, 255))
    # perfil de altitude
    y0 = size + 20
    h = 220
    ymin, ymax = min(P[:, 1].min(), -100), max(P[:, 1].max(), PLATEAU + 40)
    dr.line([(0, y0 + h - (PLATEAU - ymin) / (ymax - ymin) * h), (size, y0 + h - (PLATEAU - ymin) / (ymax - ymin) * h)], fill=(90, 80, 70))
    for i in range(0, len(P) - 1, 4):
        k = sector_of(dist[i])
        xa = dist[i] / dist[-1] * size
        ya = y0 + h - (P[i, 1] - ymin) / (ymax - ymin) * h
        dr.point((xa, ya), fill=cols[k % len(cols)])
    im.save(os.path.join(out_dir, 'plan.png'))
    print(f"  mapa: {os.path.join(out_dir, 'plan.png')}")


if __name__ == '__main__':
    main()
