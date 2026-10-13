"""
Verifica se o eixo da pista passa por cima/baixo de si mesmo (só a integração do traçado, sem gerar geometria).
Testa variantes de segmentos: blender -b --factory-startup -P rdd_overlap_check.py -- <spec.json>
"""
import copy
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SPEC = os.path.abspath(sys.argv[sys.argv.index('--') + 1])
import rdd_route_lib as lib  # noqa: E402

base = json.load(open(SPEC, encoding='utf-8'))
H = '2 Gancho técnico esquerda'
VARIANTS = {
    'atual': {},
    'raio -300': {H: {'radius': -300}},
    'raio -500': {H: {'radius': -500}},
    'direita +115': {H: {'radius': 115, 'bank': 14}},
    'direita +200': {H: {'radius': 200, 'bank': 12}},
}


def overlaps(spec):
    rows, step = lib.integrate(spec)
    P, T, R, U = lib.frames(rows)
    dist = np.array([r['dist'] for r in rows])
    width = np.array([r.get('width', 40.0) for r in rows])
    idx = np.arange(0, len(rows), 4)
    pts = P[idx]
    cells = {}
    for k, i in enumerate(idx):
        cells.setdefault((int(pts[k, 0] // 50), int(pts[k, 2] // 50)), []).append(i)
    found = []
    for i in idx:
        cx, cz = int(P[i, 0] // 50), int(P[i, 2] // 50)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for j in cells.get((cx + dx, cz + dz), []):
                    if dist[j] - dist[i] < 300:
                        continue
                    dh = np.hypot(P[j, 0] - P[i, 0], P[j, 2] - P[i, 2])
                    if dh < (width[i] + width[j]) * 0.5 + 15:
                        found.append((dist[i], dist[j], P[j, 1] - P[i, 1]))
    return found


for name, mods in VARIANTS.items():
    spec = copy.deepcopy(base)
    for seg in spec['segments']:
        if seg['id'] in mods:
            seg.update(mods[seg['id']])
    f = overlaps(spec)
    if f:
        a = np.array(f)
        print(f"[overlap] {name}: {len(f)} pares · troços {a[:, 0].min() / 1000:.2f}-{a[:, 0].max() / 1000:.2f} km sob {a[:, 1].min() / 1000:.2f}-{a[:, 1].max() / 1000:.2f} km · desnível {np.abs(a[:, 2]).min():.1f}-{np.abs(a[:, 2]).max():.1f} m", flush=True)
    else:
        print(f"[overlap] {name}: SEM sobreposições", flush=True)
