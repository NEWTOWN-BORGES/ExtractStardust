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


def rodar(erosion_m, rows, lib, geo, seed=1, talus_h=9.0):
    loc, ride, N = lib.build_ring(rows)
    loc, floor_cls, floor_mask = lib.natural_floor(rows, loc, seed)
    P, T, R, U = lib.frames(rows)
    col = geo.Column(seed)
    joints = geo.Joints(seed, rows[-1]['dist'])
    W, arc, rock, cls, pa, pb, mix, hard = lib.sculpt(
        rows, P, R, U, loc, ride, col, joints, seed,
        floor_cls, floor_mask, erosion_m=erosion_m, erosion_seed=7, talus_h=talus_h)
    return W, cls, hard, arc, loc, floor_mask


def metricas(nome, W, floor_mask=None):
    nans = int(np.isnan(W).sum())
    infs = int(np.isinf(W).sum())
    print(f"  {nome:12s} NaN={nans:5d} inf={infs:5d}")
    if floor_mask is not None:
        # LARGURA ÚTIL = extensao do CHÃO, nao a extensao total do anel. A extensao total inclui
        # as paredes e o lip, e a erosao move-a legitimamente — medir por ai dava falsos alarmes.
        fl = floor_mask > 0.5
        span = np.zeros(W.shape[0])
        for i in range(W.shape[0]):
            row = W[i, fl[i], 0]
            span[i] = row.max() - row.min() if row.size else 0.0
        print(f"               largura do chao (util) {span.min():7.1f}..{span.max():7.1f} m")
        return nans + infs, span
    span = W[..., 0].max(axis=1) - W[..., 0].min(axis=1)
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

    # limites da faixa percorrivel por estacao (para o teste do detrito)
    ride0 = None
    loc0_b, ride0, N0 = lib.build_ring(rows)

    W0, cls0, hard0, arc0, loc0, floor0 = rodar(0.0, rows, lib, geo, talus_h=0.0)
    # os mesmos valores por omissao que o rdd_build_route usa (EROSION_M, TALUS_H)
    EROS = 70.0
    TALUS = 9.0
    W1, cls1, hard1, arc1, loc1, floor1 = rodar(EROS, rows, lib, geo, talus_h=TALUS)
    print(f"\nvalores testados: erosao {EROS:.0f} m   detrito {TALUS:.0f} m")

    # ---- 1. a geometria e valida?
    print()
    print("=== 1) a geometria e valida? ===")
    b0, span0 = metricas("sem erosao", W0, floor0)
    b1, span1 = metricas("com erosao", W1, floor1)
    ok_geom = (b0 + b1) == 0
    print(f"  -> NaN/inf: {b0 + b1}  ({'OK' if ok_geom else 'FALHA'})")

    # ---- 2. a largura UTIL (chao) mantem-se?
    print()
    print("=== 2) a largura UTIL do corredor mantem-se? ===")
    d = span1 - span0
    estreitou = int((d < -0.5).sum())
    print(f"  largura do chao: {span0.mean():.1f} -> {span1.mean():.1f} m "
          f"(variacao media {d.mean():+.4f} m, max {np.abs(d).max():.4f} m)")
    print(f"  estacoes com o chao mais estreito: {estreitou} de {len(d)}")
    ok_largura = estreitou == 0
    print(f"  -> {'OK' if ok_largura else 'FALHA'}")

    # ---- 3. a erosao faz efeito?
    print()
    print("=== 3) a erosao faz efeito? ===")
    mag = np.linalg.norm(W1 - W0, axis=-1)
    print(f"  deslocamento por vertice: min {mag.min():.3f}  media {mag.mean():.3f}  max {mag.max():.2f} m")
    ok_efeito = mag.max() > 5.0
    print(f"  -> {'SIM' if ok_efeito else 'NAO (fraco demais para se ler a 100 m/s)'}")

    # ---- 4. o detrito: chao intacto e ride line livre
    print()
    print("=== 4) o detrito respeita a jogabilidade? ===")
    # IMPORTANTE: isolar o detrito. Comparar 'com detrito' contra 'sem detrito' com a MESMA
    # erosao isola-o; mas a erosao tambem desloca a parede na banda, logo a comparacao directa
    # (ambos vs nenhum) atribuiria a erosao ao detrito. Aqui testa-se o detrito SOZINHO
    # (erosao a 0) para julgar o que ELE faz, e mede-se a erosao em separado.
    Wa, _, _, arca, loca, fla = rodar(0.0, rows, lib, geo, talus_h=0.0)
    Wb, _, _, _, _, flb = rodar(0.0, rows, lib, geo, talus_h=TALUS)
    dl = np.linalg.norm(Wb - Wa, axis=-1)

    fl = flb > 0.5
    desloc_chao = dl[fl].max() if fl.any() else 0.0
    print(f"  deslocamento no CHAO (largura util): max {desloc_chao:.6f} m")
    ok_chao = desloc_chao < 1e-6
    print(f"    -> chao intacto: {'OK' if ok_chao else 'FALHA'}")

    lat = loca[..., 0]
    lim = np.where(arca < 0, ride0[:, 0:1], ride0[:, 1:2])
    acima = np.abs(lat) - lim
    banda = (acima > 0) & (acima < 5.0)          # a banda onde a ride line da parede vive
    desloc_banda = dl[banda].max() if banda.any() else 0.0
    print(f"  deslocamento do DETRITO na banda da ride line (0-5 m): max {desloc_banda:.3f} m")
    ok_banda = desloc_banda < 1.0
    print(f"    -> ride line livre: {'OK' if ok_banda else 'FALHA'}")
    parede = acima > 5.0
    print(f"  deslocamento maximo do detrito na parede: {dl[parede].max() if parede.any() else 0.0:.2f} m")

    # a erosao desloca a parede de forma diferente — medir e REPORTAR (nao falhar), porque e
    # esperado: a erosao existe para mudar o aspeto da parede. O efeito real na fisica do
    # wall-ride mede-se no validador do Unity (M1 T4), nao aqui.
    We, *_, loce, fle = rodar(EROS, rows, lib, geo, talus_h=0.0)
    de = np.linalg.norm(We - Wa, axis=-1)
    lime = np.where(arca < 0, ride0[:, 0:1], ride0[:, 1:2])
    bandae = (np.abs(loce[..., 0]) - lime > 0) & (np.abs(loce[..., 0]) - lime < 8.0)
    print(f"  [informativo] erosao sozinha na banda da ride line: "
          f"media {de[bandae].mean():.2f} m, max {de[bandae].max():.2f} m")
    print(f"    o efeito na fisica do wall-ride tem de ser reconfirmado em casa com o "
          f"validador do M1 (Red Dust / 3. Validar fisica)")

    # ---- 5. camadas duras resistem
    print()
    print("=== 5) camadas duras resistem e moles recuam? ===")
    for lo, hi, rot in ((0.0, 0.4, "mole"), (0.4, 0.75, "media"), (0.75, 1.01, "dura")):
        sel = (hard1 >= lo) & (hard1 < hi)
        if sel.sum() == 0:
            print(f"  {rot:6s}: sem vertices")
            continue
        print(f"  {rot:6s} (dureza {lo:.2f}-{hi:.2f}): {sel.sum():7d} vertices, "
              f"deslocamento medio {mag[sel].mean():6.3f} m")

    print()
    print("=" * 78)
    falhas = (0 if ok_geom else 1) + (0 if ok_largura else 1) + (0 if ok_efeito else 1) \
             + (0 if ok_chao else 1) + (0 if ok_banda else 1)
    print("RESULTADO:", "geometria valida" if falhas == 0 else f"{falhas} problema(s)")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
