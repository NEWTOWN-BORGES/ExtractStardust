"""
EXTRACT: STARDUST — Naves V2 · STRIX · Fase A (silhueta / greybox), feito do zero segundo a Bíblia v1.1.
  blender -b --factory-startup -P strix_phaseA.py -- <pasta_renders> <ficheiro.blend>

Três propostas de arquitetura (sem materiais, decals nem microdetalhe), alvo ~6,2 x 3,0 x 1,25 m:
  A ARROW     — cunha delta integrada; dois módulos de propulsão traseiros separados por uma ranhura central.
  B BRIDGE    — célula central + dois módulos de propulsão em V ligados por ponte frontal e travessa traseira (janela aberta).
  C PROTOTYPE — corpo de protótipo de motorsport com sponsons de propulsão e túnel traseiro entre os bocais.
Eixos: X direita, Y frente (nariz em +Y), Z cima; chão em z=0.
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:]
OUT, BLEND = os.path.abspath(ARGS[0]), os.path.abspath(ARGS[1])
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.dirname(BLEND), exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene


def material(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    return m


M_BODY = material('V2_Body_Grey', (0.70, 0.71, 0.73))
M_STRUCT = material('V2_Structure_Grey', (0.40, 0.41, 0.43))
M_OPEN = material('V2_Opening_Dark', (0.07, 0.07, 0.08))
M_GLASS = material('V2_Canopy_Dark', (0.14, 0.16, 0.19))
M_HOVER = material('V2_Hover_Grey', (0.28, 0.29, 0.31))
COLL = None


# ---------------------------------------------------------------- construção de malhas (hard-surface limpo)

def finish(name, bm, mat, bevel=0.018, angle=32.0):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(angle):
            e.smooth = False
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    if bevel > 0:
        b = ob.modifiers.new('Bevel', 'BEVEL')
        b.width, b.segments, b.limit_method = bevel, 3, 'ANGLE'
        b.angle_limit = math.radians(angle)
        b.harden_normals = True
    w = ob.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL')
    w.keep_sharp = True
    return ob


def loft(name, secs, mat, caps=(True, True), **kw):
    bm = bmesh.new()
    rings = [[bm.verts.new(Vector(p)) for p in s] for s in secs]
    n = len(secs[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    if caps[0]:
        bm.faces.new(list(reversed(rings[0])))
    if caps[1]:
        bm.faces.new(rings[-1])
    return finish(name, bm, mat, **kw)


def box(name, c, size, mat, bevel=0.02):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((c[0] + v.co.x * size[0], c[1] + v.co.y * size[1], c[2] + v.co.z * size[2]))
    return finish(name, bm, mat, bevel=bevel)


def smooth(a, k=2):
    a = np.asarray(a, float)
    out = a.copy()
    for _ in range(k):
        out[1:-1] = (out[:-2] + 2 * out[1:-1] + out[2:]) / 4.0
    return out


def profile(ys_ctrl, vals, ys):
    """Interpolação suave dos parâmetros da secção ao longo de Y (controlo da frente para trás)."""
    yc, vc = np.asarray(ys_ctrl, float)[::-1], np.asarray(vals, float)[::-1]
    return smooth(np.interp(ys, yc, vc), 3)


def body_loop(y, hw, zb, zc, zs, zt):
    """Secção de casco de corrida: fundo plano, chine vincado, flanco inclinado, ombro, tejadilho baixo."""
    R = [(hw * 0.45, zb), (hw * 0.88, zb + 0.012), (hw, zc), (hw * 0.86, zs),
         (hw * 0.55, zs + (zt - zs) * 0.80), (hw * 0.22, zt - (zt - zs) * 0.02)]
    pts = [(0.0, zb)] + R + [(0.0, zt)] + [(-x, z) for x, z in reversed(R)]
    return [(x, y, z) for x, z in pts]


def hull(name, ctrl, mat, n=34, x_off=0.0, **kw):
    """ctrl: dict com listas y, hw, zb, zc, zs, zt (da frente para trás)."""
    ys = np.linspace(ctrl['y'][0], ctrl['y'][-1], n)
    P = {k: profile(ctrl['y'], ctrl[k], ys) for k in ('hw', 'zb', 'zc', 'zs', 'zt')}
    secs = []
    for i, y in enumerate(ys):
        loop = body_loop(y, max(P['hw'][i], 0.012), P['zb'][i], P['zc'][i], P['zs'][i], P['zt'][i])
        secs.append([(x + x_off, yy, z) for x, yy, z in loop])
    return loft(name, secs, mat, **kw)


def rrect(w, h, c, top=1.0):
    """Secção trapezoidal com chanfros (8 pontos): top < 1 estreita o tejadilho (leitura aerodinâmica, não caixa)."""
    wt = w * top
    return [(w / 2, -h / 2 + c), (wt / 2, h / 2 - c), (wt / 2 - c, h / 2), (-wt / 2 + c, h / 2),
            (-wt / 2, h / 2 - c), (-w / 2, -h / 2 + c), (-w / 2 + c, -h / 2), (w / 2 - c, -h / 2)]


def pod(name, front, back, w_prof, h_prof, zc_prof, mat, n=20, chamfer=0.16, top=0.68, rake=0.30, intake=True, nozzle=True):
    """Módulo de propulsão esculpido: secção trapezoidal que muda ao longo do eixo, entrada de ar com lábio inclinado
    (a parte de cima recua 'rake' m: protege do pó e lê-se como scoop) e bocal retangular com moldura térmica."""
    f, b = np.array(front, float), np.array(back, float)
    d = (b - f) / np.linalg.norm(b - f)
    right = np.array([-d[1], d[0]])
    if right[0] * (1 if front[0] >= 0 else -1) < 0:
        right = -right
    ts = np.linspace(0, 1, n)
    W, H, Z = (np.interp(ts, np.linspace(0, 1, len(p)), p) for p in (w_prof, h_prof, zc_prof))
    W, H, Z = smooth(W, 2), smooth(H, 2), smooth(Z, 2)
    secs = []
    for i, t in enumerate(ts):
        c = f + (b - f) * t
        ring = []
        for u, v in rrect(W[i], H[i], chamfer * min(W[i], H[i]), top):
            back_shift = rake * (v / H[i] + 0.5) * max(0.0, 1.0 - t * 4.0)   # inclina a face da entrada
            ring.append((c[0] + right[0] * u + d[0] * back_shift, c[1] + right[1] * u + d[1] * back_shift, Z[i] + v))
        secs.append(ring)
    parts = [loft(name, secs, mat)]
    if intake:
        ring = [(x - d[0] * 0.004, y - d[1] * 0.004, z) for x, y, z in secs[0]]
        cen = np.mean(np.array(ring), axis=0)
        inner = [tuple(cen + (np.array(p) - cen) * 0.78 + np.array([d[0] * 0.03, d[1] * 0.03, 0])) for p in ring]
        parts.append(loft(name + '_IntakeLip', [ring, inner], M_STRUCT, caps=(False, False), bevel=0.0))
        parts.append(loft(name + '_IntakeDuct', [inner, [(x + d[0] * 0.01, y + d[1] * 0.01, z) for x, y, z in inner]], M_OPEN, caps=(False, True), bevel=0.0))
    if nozzle:
        last = np.array(secs[-1])
        cen = last.mean(axis=0)
        outer = [tuple(cen + (p - cen) * 1.06 + np.array([d[0] * 0.10, d[1] * 0.10, 0])) for p in last]
        parts.append(loft(name + '_HeatShieldFrame', [[tuple(p) for p in last], outer], M_STRUCT, caps=(False, False), bevel=0.0))
        inner = [tuple(cen + (np.array(p) - cen) * 0.80 + np.array([d[0] * 0.09, d[1] * 0.09, 0])) for p in outer]
        parts.append(loft(name + '_NozzleLiner', [outer, inner], M_STRUCT, caps=(False, False), bevel=0.0))
        parts.append(loft(name + '_NozzleCore', [inner, [tuple(np.array(p) - np.array([d[0] * 0.02, d[1] * 0.02, 0])) for p in inner]], M_OPEN, caps=(False, True), bevel=0.0))
    return parts


def fairing(name, ys, inner_x, inner_top, inner_bot, outer_x, outer_top, outer_bot, mat):
    """Carenagem que liga corpo e módulo (ombro inclinado): o módulo fica montado, não colado."""
    secs = []
    for i, y in enumerate(ys):
        secs.append([(inner_x[i], y, inner_top[i]), (outer_x[i], y, outer_top[i]), (outer_x[i], y, outer_bot[i]), (inner_x[i], y, inner_bot[i])])
    return loft(name, secs, mat, bevel=0.014)


def blade(name, root, tip, chord_root, chord_tip, thick, mat, n=6):
    """Estabilizador de corrida: perfil espesso com bordo de ataque arredondado e raiz estrutural (não é placa plana)."""
    root, tip = np.array(root, float), np.array(tip, float)
    secs = []
    for t in np.linspace(0, 1, n):
        p = root + (tip - root) * t
        ch = chord_root + (chord_tip - chord_root) * t
        th = thick * (1 - 0.45 * t)
        prof = [(0.0, 0.0), (-0.12 * ch, th * 0.42), (-0.45 * ch, th * 0.5), (-ch, th * 0.08),
                (-ch, -th * 0.04), (-0.45 * ch, -th * 0.30), (-0.12 * ch, -th * 0.26)]
        secs.append([(p[0], p[1] + dy, p[2] + dz) for dy, dz in prof])
    return loft(name, secs, mat, bevel=0.008)


def canopy(name, y0, y1, w, h, deck, mat):
    """Canopy integrado e baixo: lágrima alongada metida no casco (não é bolha de caça)."""
    secs = []
    for t in np.linspace(0, 1, 16):
        y = y0 + (y1 - y0) * t
        s = math.sin(math.pi * min(1.0, t * 1.15)) ** 0.55 if t < 0.87 else max(0.08, (1 - t) / 0.13 * 0.55)
        hw, hh = max(0.03, w * s), max(0.02, h * (math.sin(math.pi * min(1.0, t * 1.08)) ** 0.7))
        z0 = deck(y) - 0.06
        loop = [(hw * math.cos(a), y, z0 + 0.06 + hh * math.sin(a)) for a in np.linspace(0, math.pi, 9)]
        loop += [(-hw * 0.9, y, z0), (hw * 0.9, y, z0)]
        secs.append(loop)
    return loft(name, secs, mat, bevel=0.0)


def hover_pads(prefix, spots, size=(0.40, 0.58, 0.06)):
    """spots: (x, y, z_fundo) — a placa fica metade metida no fundo do casco/módulo, com o emissor por baixo."""
    for i, (x, y, zb) in enumerate(spots):
        box(f"{prefix}_HoverMount_{i}", (x, y, zb), (size[0] + 0.08, size[1] + 0.08, 0.05), M_STRUCT, bevel=0.012)
        box(f"{prefix}_HoverEmitter_{i}", (x, y, zb - 0.045), size, M_HOVER, bevel=0.012)


def mirror_parts(fn, *args, **kw):
    for s in (1, -1):
        fn(s, *args, **kw)


# ---------------------------------------------------------------- linguagem das referências (R02 cunha longa, R05 pod de corrida,
# R10/R14 garfo com espaço negativo): corpo baixo e facetado, cockpit metido no corpo, propulsão traseira angular.

def hexsec(y, hw, hwb, hwt, zb, zc, zt, xo=0.0):
    """Secção facetada: fundo, chine vincado, ombro chanfrado, tampo plano (painéis grandes e limpos)."""
    return [(xo + hwb, y, zb), (xo + hw, y, zc), (xo + hwt, y, zt), (xo - hwt, y, zt), (xo - hw, y, zc), (xo - hwb, y, zb)]


def facet(name, ctrl, mat, n=16, xo=0.0, bevel=0.010):
    ys = np.linspace(ctrl['y'][0], ctrl['y'][-1], n)
    P = {k: np.interp(ys, ctrl['y'][::-1], ctrl[k][::-1]) for k in ('hw', 'hwb', 'hwt', 'zb', 'zc', 'zt')}
    secs = [hexsec(y, P['hw'][i], P['hwb'][i], P['hwt'][i], P['zb'][i], P['zc'][i], P['zt'][i], xo) for i, y in enumerate(ys)]
    return loft(name, secs, mat, bevel=bevel, angle=18)


def cockpit_cut(name, y0, y1, w, h, deck):
    """Cockpit metido no corpo: vidro facetado baixo, quase à face do tampo (nunca bolha)."""
    secs = []
    for t in np.linspace(0, 1, 9):
        y = y0 + (y1 - y0) * t
        k = math.sin(math.pi * min(1.0, 0.15 + t * 0.9)) ** 0.6
        hw, hh, z = max(0.04, w * k), max(0.015, h * k), deck(y) - 0.02
        secs.append([(hw, y, z), (hw * 0.62, y, z + hh), (-hw * 0.62, y, z + hh), (-hw, y, z)])
    return loft(name, secs, M_GLASS, bevel=0.0)


def stab_blade(name, s, x0, x1, le0, c0, le1, c1, z0, z1, t0, t1, endplate=0.20):
    """Estabilizador de corrida espesso (não é asa de avião): perfil facetado que nasce de dentro do bloco de
    propulsão, afina para fora e termina numa placa terminal virada para o chão (efeito de solo / wall-ride)."""
    secs = []
    for k in np.linspace(0, 1, 5):
        x = s * (x0 + (x1 - x0) * k)
        le, c, z, t = le0 + (le1 - le0) * k, c0 + (c1 - c0) * k, z0 + (z1 - z0) * k, t0 + (t1 - t0) * k
        secs.append([(x, le, z + t * 0.10), (x, le - c * 0.30, z + t * 0.50), (x, le - c, z + t * 0.18),
                     (x, le - c, z - t * 0.32), (x, le - c * 0.35, z - t * 0.50), (x, le, z - t * 0.15)])
    if s < 0:
        secs = [list(reversed(sec)) for sec in secs]
    loft(name, secs, M_BODY, bevel=0.010, angle=18)
    if endplate > 0:
        box(name + '_Endplate', (s * (x1 - 0.02), le1 - c1 * 0.5, z1 - endplate * 0.45), (0.05, c1 * 0.95, endplate), M_STRUCT, bevel=0.012)


def slab(name, outline, z0, z1, mat, bevel=0.02):
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in outline]
    top = [bm.verts.new((x, y, z1)) for x, y in outline]
    bm.faces.new(bot[::-1])
    bm.faces.new(top)
    for i in range(len(outline)):
        j = (i + 1) % len(outline)
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    return finish(name, bm, mat, bevel=bevel, angle=18)


def propulsion_block(prefix, s, x, y0, y1, w, h, z0):
    """Unidade de propulsão traseira angular: frente inclinada para dentro do corpo, scoop lateral com lábio,
    bocal retangular com moldura térmica. Separada da outra por uma ranhura (espaço negativo)."""
    side = 'R' if s > 0 else 'L'
    pod(f"{prefix}_Propulsion_{side}", (s * x, y0), (s * x, y1), (w * 0.70, w, w, w * 0.96), (h * 0.55, h, h, h * 0.94),
        (z0 + h * 0.42, z0 + h * 0.5, z0 + h * 0.5, z0 + h * 0.5), M_BODY, n=12, chamfer=0.08, top=0.60, rake=0.55, intake=False)
    # bocal retangular com lâminas de vectoring (nunca disco/círculo)
    for k, dz in enumerate((-0.12, 0.0, 0.12)):
        box(f"{prefix}_NozzleVane_{side}_{k}", (s * x, y1 - 0.07, z0 + h * 0.5 + dz * h), (w * 0.74, 0.10, 0.025), M_STRUCT, bevel=0.004)
    # scoop lateral (entrada com lábio e separador de pó) no flanco exterior do bloco
    sy0 = y0 - 0.25
    pod(f"{prefix}_SideScoop_{side}", (s * (x + w * 0.52), sy0), (s * (x + w * 0.52), sy0 - 0.85), (0.10, 0.22, 0.22), (0.18, h * 0.62, h * 0.60),
        (z0 + h * 0.52, z0 + h * 0.55, z0 + h * 0.55), M_BODY, n=6, chamfer=0.2, top=0.8, rake=0.12, nozzle=False)


def strix_wedge():
    """A — WEDGE (linguagem R02): cunha longa e baixa; cockpit a meio metido no corpo; dois blocos de propulsão
    traseiros separados por uma ranhura; estabilizadores médios planos nos flancos dos blocos."""
    ctrl = dict(y=[3.10, 2.10, 0.70, -0.60, -1.50], hw=[0.12, 0.44, 0.70, 0.80, 0.80], hwb=[0.08, 0.34, 0.58, 0.68, 0.70],
                hwt=[0.05, 0.24, 0.40, 0.48, 0.50], zb=[0.31, 0.27, 0.26, 0.26, 0.27], zc=[0.33, 0.37, 0.43, 0.47, 0.48],
                zt=[0.35, 0.49, 0.65, 0.76, 0.78])
    facet('A_Body', ctrl, M_BODY)
    deck = lambda y: float(np.interp(y, ctrl['y'][::-1], ctrl['zt'][::-1]))
    cockpit_cut('A_Cockpit', 0.95, -0.45, 0.34, 0.15, deck)
    for s in (1, -1):
        propulsion_block('A', s, 0.56, -0.70, -3.10, 0.62, 0.62, 0.28)
        stab_blade(f"A_Stabilizer_{'R' if s > 0 else 'L'}", s, 0.70, 1.47, -1.60, 1.30, -1.85, 1.00, 0.52, 0.48, 0.20, 0.12)
    box('A_ReactorBridge', (0.0, -1.45, 0.62), (0.50, 0.30, 0.22), M_STRUCT)
    hover_pads('A', [(0.30, 1.70, 0.27), (-0.30, 1.70, 0.27), (0.0, 0.10, 0.26), (0.56, -2.20, 0.28), (-0.56, -2.20, 0.28)])


def strix_split():
    """B — SPLIT (linguagem R10/R14): o nariz são duas lâminas em garfo com espaço negativo entre elas; o cockpit
    fica na junção; dois blocos de propulsão traseiros; estabilizadores médios nos blocos."""
    for s in (1, -1):
        blade_ctrl = dict(y=[3.10, 2.00, 0.80], hw=[0.10, 0.17, 0.20], hwb=[0.06, 0.13, 0.16], hwt=[0.05, 0.10, 0.12],
                          zb=[0.32, 0.29, 0.27], zc=[0.34, 0.38, 0.42], zt=[0.36, 0.46, 0.56])
        xs = np.linspace(0.46, 0.36, 3)
        ctrl_s = dict(blade_ctrl)
        ys = np.linspace(3.10, 0.80, 10)
        secs = []
        for i, y in enumerate(ys):
            P = {k: float(np.interp(y, blade_ctrl['y'][::-1], blade_ctrl[k][::-1])) for k in ('hw', 'hwb', 'hwt', 'zb', 'zc', 'zt')}
            xo = s * float(np.interp(y, [0.8, 3.1], [0.34, 0.50]))
            secs.append(hexsec(y, P['hw'], P['hwb'], P['hwt'], P['zb'], P['zc'], P['zt'], xo))
        loft(f"B_NoseBlade_{'R' if s > 0 else 'L'}", secs, M_BODY, bevel=0.010, angle=18)
    ctrl = dict(y=[1.10, 0.40, -0.60, -1.50], hw=[0.52, 0.70, 0.80, 0.78], hwb=[0.42, 0.58, 0.68, 0.68],
                hwt=[0.30, 0.42, 0.48, 0.48], zb=[0.27, 0.26, 0.26, 0.27], zc=[0.42, 0.45, 0.47, 0.48], zt=[0.58, 0.70, 0.76, 0.76])
    facet('B_Body', ctrl, M_BODY, n=10)
    deck = lambda y: float(np.interp(y, ctrl['y'][::-1], ctrl['zt'][::-1]))
    cockpit_cut('B_Cockpit', 0.75, -0.55, 0.36, 0.16, deck)
    box('B_CrashBeam', (0.0, 1.05, 0.40), (0.62, 0.12, 0.10), M_STRUCT)
    for s in (1, -1):
        propulsion_block('B', s, 0.62, -0.75, -3.10, 0.60, 0.60, 0.28)
        stab_blade(f"B_Stabilizer_{'R' if s > 0 else 'L'}", s, 0.78, 1.47, -1.75, 1.20, -1.98, 0.92, 0.50, 0.46, 0.20, 0.12)
    box('B_ReactorBridge', (0.0, -1.50, 0.60), (0.56, 0.30, 0.22), M_STRUCT)
    hover_pads('B', [(0.42, 2.20, 0.30), (-0.42, 2.20, 0.30), (0.0, 0.0, 0.26), (0.62, -2.20, 0.28), (-0.62, -2.20, 0.28)])


def strix_pod():
    """C — POD (linguagem R05): corpo comprido e plano com o cockpit à frente; o corpo divide-se atrás em dois
    blocos de propulsão; respiros laterais longos; estabilizadores médios dianteiros em diamante."""
    ctrl = dict(y=[3.10, 2.40, 1.20, -0.20, -1.10], hw=[0.26, 0.54, 0.66, 0.70, 0.72], hwb=[0.18, 0.44, 0.56, 0.60, 0.62],
                hwt=[0.12, 0.30, 0.40, 0.42, 0.44], zb=[0.31, 0.27, 0.26, 0.26, 0.27], zc=[0.35, 0.40, 0.44, 0.45, 0.46],
                zt=[0.40, 0.56, 0.68, 0.70, 0.70])
    facet('C_Body', ctrl, M_BODY)
    deck = lambda y: float(np.interp(y, ctrl['y'][::-1], ctrl['zt'][::-1]))
    cockpit_cut('C_Cockpit', 2.05, 0.75, 0.36, 0.17, deck)
    for s in (1, -1):
        propulsion_block('C', s, 0.48, -0.70, -3.10, 0.56, 0.54, 0.28)
        # respiros laterais longos (saída de calor do reator ao longo do corpo)
        box(f"C_SideVent_{'R' if s > 0 else 'L'}", (s * 0.705, -0.30, 0.42), (0.02, 0.90, 0.06), M_OPEN, bevel=0.0)
        stab_blade(f"C_NoseStabilizer_{'R' if s > 0 else 'L'}", s, 0.50, 1.20, 2.05, 1.05, 1.55, 0.55, 0.40, 0.38, 0.16, 0.10, endplate=0.16)
        stab_blade(f"C_RearStabilizer_{'R' if s > 0 else 'L'}", s, 0.66, 1.47, -1.95, 1.05, -2.15, 0.85, 0.52, 0.48, 0.18, 0.11)
    box('C_ReactorBridge', (0.0, -1.30, 0.58), (0.46, 0.30, 0.20), M_STRUCT)
    hover_pads('C', [(0.0, 2.30, 0.29), (0.0, 0.60, 0.26), (0.48, -2.20, 0.28), (-0.48, -2.20, 0.28)])


# ---------------------------------------------------------------- render (Workbench: barro cinzento + silhueta)

def setup_render():
    SC.render.engine = 'BLENDER_WORKBENCH'
    SC.display.render_aa = '16'
    sh = SC.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_cavity = True
    sh.cavity_type = 'WORLD'
    sh.cavity_ridge_factor, sh.cavity_valley_factor = 1.0, 1.2
    sh.show_object_outline = True
    sh.object_outline_color = (0.04, 0.04, 0.05)
    sh.show_shadows = True
    sh.shadow_intensity = 0.38
    sh.show_specular_highlight = True
    SC.display.light_direction = (0.35, 0.45, 0.82)
    SC.render.film_transparent = True
    SC.render.image_settings.file_format = 'PNG'
    SC.render.image_settings.color_mode = 'RGBA'
    SC.view_settings.view_transform = 'Standard'


def camera(name, loc, rot=None, look=None, ortho=None, lens=50.0):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type, cd.ortho_scale = 'ORTHO', ortho
    else:
        cd.lens = lens
    cd.clip_start, cd.clip_end = 0.05, 200.0
    cam = bpy.data.objects.new(name, cd)
    SC.collection.objects.link(cam)
    cam.location = loc
    if look is not None:
        cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    else:
        cam.rotation_euler = [math.radians(a) for a in rot]
    return cam


def render(path, cam, w, h, silhouette=False, ground=None):
    SC.camera = cam
    SC.render.resolution_x, SC.render.resolution_y = w, h
    sh = SC.display.shading
    if ground is not None:
        ground.hide_render = True
    if silhouette:
        sh.light, sh.color_type, sh.single_color = 'FLAT', 'SINGLE', (0.0, 0.0, 0.0)
        sh.show_cavity = sh.show_object_outline = sh.show_shadows = sh.show_specular_highlight = False
    SC.render.filepath = path
    bpy.ops.render.render(write_still=True)
    if silhouette:
        sh.light, sh.color_type = 'STUDIO', 'MATERIAL'
        sh.show_cavity = sh.show_object_outline = sh.show_shadows = sh.show_specular_highlight = True


SHIP, TARGET = 'STRIX', '6,2 × 3,0 × 1,25'
TEXTS = {
    'A': ("WEDGE · linguagem R02 (cunha de corrida longa). Corpo baixo e facetado em cunha; cockpit a meio, metido no corpo; dois blocos de propulsão traseiros separados por uma ranhura; estabilizadores médios nos flancos dos blocos.",
          "Construção: espinha central → célula do cockpit → ponte do reator entre os blocos → blocos de propulsão → hover sob o casco → painéis.",
          "Força: equilíbrio e leitura clara a 50 m. Fraqueza: nenhuma especialidade. Refrigeração: scoops laterais com lábio que alimentam os blocos."),
    'B': ("SPLIT · linguagem R10/R14 (garfo com espaço negativo). O nariz são duas lâminas em garfo com vazio entre elas; o cockpit fica na junção; dois blocos de propulsão traseiros; estabilizadores médios nos blocos.",
          "Construção: duas lâminas de impacto → viga de impacto na junção → célula do cockpit → ponte do reator → blocos de propulsão → painéis.",
          "Força: silhueta inconfundível e nariz leve. Fraqueza: lâminas expostas a impacto frontal. Refrigeração: scoops laterais dos blocos."),
    'C': ("POD · linguagem R05 (pod de corrida). Corpo comprido e plano com o cockpit à frente; o corpo divide-se atrás em dois blocos de propulsão; respiros laterais longos; estabilizadores médios dianteiros.",
          "Construção: espinha longa → célula do cockpit à frente → reator a meio (respiros) → blocos de propulsão → hover → painéis.",
          "Força: estabilidade e visibilidade do piloto. Fraqueza: traseira longa menos ágil. Refrigeração: respiros laterais e scoops dos blocos."),
}
PROPOSALS = None
VIEW_SCALE = 1.0          # naves maiores (NOMAD) afastam as câmeras


def main():
    global COLL
    setup_render()
    proposals = PROPOSALS or [('A', 'WEDGE', strix_wedge), ('B', 'SPLIT', strix_split), ('C', 'POD', strix_pod)]
    colls = {}
    for key, label, fn in proposals:
        COLL = bpy.data.collections.new(f"{SHIP}_{key}_{label}")
        SC.collection.children.link(COLL)
        fn()
        colls[key] = COLL
    gm = material('Ground', (0.86, 0.86, 0.87))
    bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.data.materials.append(gm)

    cams = dict(
        top=(camera('Cam_Top', (0, 0, 20), rot=(0, 0, 90), ortho=7.0 * VIEW_SCALE), 1200, 700),
        side=(camera('Cam_Side', (20, 0, 0.62), rot=(90, 0, 90), ortho=7.0 * VIEW_SCALE), 1200, 420),
        front=(camera('Cam_Front', (0, 20, 0.62), rot=(90, 0, 180), ortho=3.6 * VIEW_SCALE), 900, 450),
        rear=(camera('Cam_Rear', (0, -20, 0.62), rot=(90, 0, 0), ortho=3.6 * VIEW_SCALE), 900, 450),
        f34=(camera('Cam_Front34', (6.4 * VIEW_SCALE, 7.4 * VIEW_SCALE, 3.0 * VIEW_SCALE), look=(0.0, 0.25, 0.50), lens=55), 1600, 1000),
        r34=(camera('Cam_Rear34', (-5.8 * VIEW_SCALE, -7.6 * VIEW_SCALE, 2.9 * VIEW_SCALE), look=(0.0, -0.55, 0.50), lens=55), 1600, 1000),
    )
    info = {}
    for key, label, fn in proposals:
        for k, c in colls.items():
            c.hide_render = k != key
        for view, (cam, w, h) in cams.items():
            render(os.path.join(OUT, f"{SHIP}_{key}_{view}.png"), cam, w, h, ground=ground)
        for view in ('top', 'side', 'front'):
            cam, w, h = cams[view]
            render(os.path.join(OUT, f"{SHIP}_{key}_{view}_silhouette.png"), cam, w, h, silhouette=True, ground=ground)
        # medidas reais da proposta (bounding box dos objetos avaliados)
        dg = bpy.context.evaluated_depsgraph_get()
        pts = []
        for ob in colls[key].objects:
            ev = ob.evaluated_get(dg)
            pts += [ev.matrix_world @ Vector(b) for b in ev.bound_box]
        mn = [min(p[i] for p in pts) for i in range(3)]
        mx = [max(p[i] for p in pts) for i in range(3)]
        info[key] = dict(label=label, length=round(mx[1] - mn[1], 2), width=round(mx[0] - mn[0], 2), height=round(mx[2], 2),
                         objects=len(colls[key].objects), ship=SHIP, target=TARGET, texts=list(TEXTS.get(key, ('', '', ''))))
        print(f"[{SHIP}] {key} {label}: { {k: v for k, v in info[key].items() if k != 'texts'} }", flush=True)
    for c in colls.values():
        c.hide_render = False
    json.dump(info, open(os.path.join(OUT, f'{SHIP.lower()}_info.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


if __name__ == '__main__':
    main()
