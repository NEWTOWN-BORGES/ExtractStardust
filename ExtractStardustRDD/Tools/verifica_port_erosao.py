"""
Verifica o erode3d portado (rdd_route_lib.py) contra o geo.fbm3 REAL do projeto.

Os meus diagramas anteriores usavam uma reimplementacao do ruido em Python. Isto aqui
importa o rdd_geology do proprio projeto (numpy puro, sem bpy) e testa a funcao que vai
correr no Blender — para garantir que o comportamento e o esperado antes de gerar 1,4 GB
de geometria em casa.
"""
import importlib.util
import sys

import numpy as np

ART = (r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust"
       r"\ExtractStardustRDD\Art\Blender")
sys.path.insert(0, ART)

spec = importlib.util.spec_from_file_location("rdd_geology", ART + r"\rdd_geology.py")
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)
print("rdd_geology importado; tem fbm3:", hasattr(geo, "fbm3"), "| fbm2:", hasattr(geo, "fbm2"))

LAYERS_RDD = geo.LAYERS_RDD


def erode3d(height, along, wall_u, hardness, amount=26.0, seed=7):
    """Copia fiel de rdd_route_lib.erode3d (mantida em sincronia a mao)."""
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
    depth = np.maximum(0.0, depth) / 0.60
    by_face = 0.55 + 0.65 * np.sin(wall_u * np.pi)
    return by_hardness * by_face * depth


def hardness_at(y):
    base, out = 0.0, []
    for l in LAYERS_RDD:
        base += l[1]
        out.append((base, l[2]))
    for yv in np.atleast_1d(y):
        idx = 0
        for i, (top, _) in enumerate(out):
            if yv <= top:
                idx = i
                break
        else:
            idx = len(out) - 1
        yield out[idx][1]


print()
print("=== 1. amplitude por camada (o que o jogador ve) ===")
for l in LAYERS_RDD:
    name, thick, hard = l[0], l[1], l[2]
    if hard > 0.9 or hard < 0.35:
        h = np.linspace(0, thick, 200)
        rec = erode3d(h, np.full_like(h, 1000.0), np.clip(h / thick, 0, 1), np.full_like(h, hard))
        print(f"  {name:12s} dureza {hard:.2f}  recuo {rec.min():6.2f} .. {rec.max():6.2f} m")

print()
print("=== 2. sanidade ===")
h = np.linspace(0, 330, 400)
a = np.full_like(h, 500.0)
u = h / 330.0
hard = np.array(list(hardness_at(h)))
rec = erode3d(h, a, u, hard)
print(f"  NaN/inf: {np.isnan(rec).any() or np.isinf(rec).any()}")
print(f"  minimo: {rec.min():.3f} m   maximo: {rec.max():.2f} m")
print(f"  sempre >= 0: {bool((rec >= -1e-9).all())}")
print(f"  media: {rec.mean():.2f} m")

print()
print("=== 3. variacao ao LONGO da rota (tem de mudar, nao ser constante) ===")
h2 = np.full(300, 300.0)
a2 = np.linspace(0, 3000, 300)
u2 = np.full(300, 0.5)
hard2 = np.array(list(hardness_at(h2)))
rec2 = erode3d(h2, a2, u2, hard2)
print(f"  min {rec2.min():.2f}  max {rec2.max():.2f}  desvio {rec2.std():.2f} m")
print(f"  variacao ao longo de 3 km: {rec2.max() - rec2.min():.2f} m")

print()
print("=== 4. dureza manda? (correlacao recuo vs moleza) ===")
hs = np.linspace(0.05, 1.0, 60)
rr = []
for hv in hs:
    h3 = np.linspace(0, 50, 120)
    r3 = erode3d(h3, np.full_like(h3, 800.0), np.clip(h3 / 50, 0, 1), np.full_like(h3, hv))
    rr.append(r3.mean())
rr = np.array(rr)
corr = np.corrcoef(1.0 - hs, rr)[0, 1]
print(f"  correlacao (moleza vs recuo medio): {corr:.3f}  (esperado ~1.0)")
print(f"  dureza 0,05 -> {rr[0]:.2f} m   dureza 1,00 -> {rr[-1]:.4f} m")
