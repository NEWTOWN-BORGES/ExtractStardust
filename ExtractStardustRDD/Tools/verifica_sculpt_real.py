"""
Verifica a GEOMETRIA REAL do sculpt com erosao, sem Blender.

Carrega o rdd_route_lib (o ficheiro que o Blender corre) com stubs de bpy/mathutils
e corre o pipeline de geometria — build_ring, natural_floor, frames, sculpt — sobre
uma rota construida a partir dos VALORES REAIS dos segmentos de sandbox.json.

Isto testa a funcao que gera a pista, nao uma reimplementacao. Responde a pergunta
em aberto: o sculpt com erosao produz geometria valida e faz efeito?

Uso:  python Tools/verifica_sculpt_real.py
"""
import importlib.util
import json
import os
import sys
import types

import numpy as np

ART = (r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust"
       r"\ExtractStardustRDD\Art\Blender")
COURSES = (r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust"
           r"\ExtractStardustRDD\Art\Courses")


def stubs():
    """bpy/mathutils falsos: o modulo real so os usa na classe MeshOut."""
    if "bpy" not in sys.modules:
        bpy = types.ModuleType("bpy")
        bpy.data = types.SimpleNamespace(
            meshes=types.SimpleNamespace(new=lambda *a, **k: None),
            materials=types.SimpleNamespace(get=lambda *a, **k: None, new=lambda *a, **k: None),
            objects=types.SimpleNamespace(new=lambda *a, **k: None))
        bpy.ops = types.SimpleNamespace()
        sys.modules["bpy"] = bpy
    if "mathutils" not in sys.modules:
        mu = types.ModuleType("mathutils")
        mu.kdtree = types.ModuleType("mathutils.kdtree")
        sys.modules["mathutils"] = mu
        sys.modules["mathutils.kdtree"] = mu.kdtree


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# chaves de secao que o rdd_build_route propaga (EASED sem curv/slope)
SECAO = ['width', 'bank', 'slope', 'curv', 'wallL', 'wallR', 'filletL', 'filletR',
         'angleL', 'angleR', 'lipL', 'lipR', 'rideL', 'rideR']


def rows_do_sandbox(n_alvo=600):
    """Constroi as estacoes a partir dos segmentos reais de sandbox.json."""
    p = os.path.join(COURSES, "sandbox.json")
    spec = json.load(open(p, encoding="utf-8"))
    dflt = spec.get("defaults", {})
    segs = spec["segments"]

    # comprimento total
    total = 0.0
    for s in segs:
        total += float(s.get("len", dflt.get("len", 0.0)))
    step = total / max(1, n_alvo - 1)

    rows = []
    cur = {k: float(dflt.get(k, 0.0)) for k in SECAO}
    cur['surf'] = dflt.get('surface', 'sand')
    cur['floor'] = dflt.get('floor', 'flat')
    d = 0.0
    si = 0
    s0 = 0.0
    L = float(segs[0].get("len", 0.0)) if segs else 0.0
    for i in range(n_alvo):
        dist = i * step
        # avancar segmentos
        while si < len(segs) - 1 and dist > s0 + float(segs[si].get("len", 0.0)):
            s0 += float(segs[si].get("len", 0.0))
            si += 1
        seg = segs[si]
        L = float(seg.get("len", 0.0))
        # alvo = defaults + overrides do segmento
        tgt = dict(cur)
        for k in SECAO:
            if k in seg:
                tgt[k] = float(seg[k])
        tgt['surf'] = seg.get('surface', cur['surf'])
        tgt['floor'] = seg.get('floor', cur['floor'])
        # ease do segmento (ou 120 m por omissao, como o build_route)
        ease = float(seg.get("ease", 120.0)) or 120.0
        u = min(1.0, (dist - s0) / ease) if ease > 0 else 1.0
        e = u * u * (3 - 2 * u)
        vals = {k: cur[k] + (tgt[k] - cur[k]) * e for k in SECAO}
        rows.append(dict(vals,
                         pos=np.array([0.0, 0.0, dist]),
                         seg=si + 1, gap=int(seg.get("gap", 0)), cave=int(seg.get("cave", 0)),
                         surf=0, dist=dist, natural=True))
        # avancar o estado quando o segmento muda
        if dist >= s0 + L and si < len(segs) - 1:
            cur = dict(tgt)
    return rows, spec


def rodar(erosion_m, rows, lib, geo, seed=1):
    loc, ride, N = lib.build_ring(rows)
    loc, floor_cls, floor_mask = lib.natural_floor(rows, loc, seed)
    P, T, R, U = lib.frames(rows)
    col = geo.Column(seed)
    joints = geo.Joints(seed, rows[-1]['dist'])
    W, arc, rock, cls, pa, pb, mix, hard = lib.sculpt(
        rows, P, R, U, loc, ride, col, joints, seed,
        floor_cls, floor_mask, erosion_m=erosion_m, erosion_seed=7)
    return W, cls, hard, arc, loc


def metricas(nome, W):
    nans = int(np.isnan(W).sum())
    infs = int(np.isinf(W).sum())
    # largura lateral por estacao: extensao em X (o eixo lateral e X numa reta ao longo de Z)
    span = W[..., 0].max(axis=1) - W[..., 0].min(axis=1)
    print(f"  {nome:12s} NaN={nans:5d} inf={infs:5d}  "
          f"largura lateral {span.min():7.1f}..{span.max():7.1f} m")
    return nans + infs, span


def main():
    print("=" * 78)
    print("VERIFICACAO DA GEOMETRIA REAL DO sculpt  (rdd_route_lib, sem Blender)")
    print("=" * 78)

    stubs()
    if ART not in sys.path:
        sys.path.insert(0, ART)
    lib = carregar("rdd_route_lib", ART + r"\rdd_route_lib.py")
    geo = carregar("rdd_geology", ART + r"\rdd_geology.py")

    rows, spec = rows_do_sandbox(600)
    print(f"\npista: {spec.get('name')}  estacoes {len(rows)}  "
          f"comprimento {rows[-1]['dist'] / 1000.0:.2f} km")
    print(f"largura: {min(r['width'] for r in rows):.0f} .. {max(r['width'] for r in rows):.0f} m")
    print(f"paredes: {min(r['wallL'] for r in rows):.0f} .. {max(r['wallL'] for r in rows):.0f} m")

    W0, cls0, hard0, arc0, loc0 = rodar(0.0, rows, lib, geo)
    # o mesmo valor por omissao que o rdd_build_route usa (EROSION_M)
    EROS = 70.0
    W1, cls1, hard1, arc1, loc1 = rodar(EROS, rows, lib, geo)
    print(f"\namplitude de erosao testada: {EROS:.0f} m")

    print()
    print("=== 1) a geometria e valida? ===")
    b0, span0 = metricas("sem erosao", W0)
    b1, span1 = metricas("com erosao", W1)
    print(f"  -> NaN/inf: {b0 + b1}  ({'OK' if b0 + b1 == 0 else 'FALHA'})")

    print()
    print("=== 2) a erosao faz efeito? ===")
    mag = np.linalg.norm(W1 - W0, axis=-1)
    print(f"  deslocamento por vertice: min {mag.min():.3f}  media {mag.mean():.3f}  max {mag.max():.2f} m")
    print(f"  vertices inalterados: {int((mag < 1e-6).sum())} de {mag.size}")
    ok_efeito = mag.max() > 0.5
    print(f"  -> altera a malha: {'SIM' if ok_efeito else 'NAO (erro)'}")

    print()
    print("=== 3) a erosao nunca estreita a pista? ===")
    d = span1 - span0
    print(f"  largura media: {span0.mean():.1f} m -> {span1.mean():.1f} m  ({d.mean():+.2f} m)")
    estreitou = int((d < -0.5).sum())
    print(f"  estacoes mais estreitas: {estreitou} de {len(d)}")
    if estreitou:
        for i in np.argsort(d)[:5]:
            print(f"      estacao {i} (dist {rows[i]['dist']:.0f} m): {d[i]:+.2f} m")
    ok_largura = estreitou == 0
    print(f"  -> {'OK' if ok_largura else 'FALHA'}")

    print()
    print("=== 4) camadas duras resistem e moles recuam? ===")
    for lo, hi, rot in ((0.0, 0.4, "mole"), (0.4, 0.75, "media"), (0.75, 1.01, "dura")):
        sel = (hard1 >= lo) & (hard1 < hi)
        if sel.sum() == 0:
            print(f"  {rot:6s}: sem vertices")
            continue
        print(f"  {rot:6s} (dureza {lo:.2f}-{hi:.2f}): {sel.sum():7d} vertices, "
              f"deslocamento medio {mag[sel].mean():6.3f} m")
    print("  -> esperado: mole > media > dura")

    print()
    print("=" * 78)
    falhas = b0 + b1 + (0 if ok_efeito else 1) + (0 if ok_largura else 1)
    print("RESULTADO:", "geometria valida" if falhas == 0 else f"{falhas} problema(s)")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
