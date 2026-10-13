"""
EXTRACT: STARDUST — fotos das naves modulares no Blender (sem o Unity).

  blender -b --factory-startup -P rdd_render_ships.py -- <spec.json> <pasta_export> <pasta_fotos>

Reconstrói as naves com a MESMA geometria do jogo (tradução direta de ShipBuilder.BuildVisual / MeshBuilder: núcleo do
chassis + módulos nos sockets) e fotografa-as na grelha da bacia da RED DUST DIVIDE (setor 1 exportado).
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, 'rdd_render_views.py'), encoding='utf-8').read()
_src = _src[:_src.rindex('main()')]          # reaproveitar céu, sol, materiais da geologia e conversão de eixos
_ns = {'__file__': os.path.join(HERE, 'rdd_render_views.py'), '__name__': 'rdd_render_views'}
exec(compile(_src, 'rdd_render_views.py', 'exec'), _ns)
setup_scene, geology_material, unity_to_blender_matrix = _ns['setup_scene'], _ns['geology_material'], _ns['unity_to_blender_matrix']
integrate, frames, log, srgb = _ns['integrate'], _ns['frames'], _ns['log'], _ns['srgb_to_linear']
SPEC, EXPORT, OUT = _ns['SPEC'], _ns['EXPORT'], _ns['OUT']

# ---------------------------------------------------------------- MeshBuilder (igual ao C#)


class MB:
    def __init__(self):
        self.v, self.t = [], []

    def tri(self, a, b, c):
        i = len(self.v)
        self.v += [np.asarray(a, float), np.asarray(b, float), np.asarray(c, float)]
        self.t.append((i, i + 1, i + 2))

    def quad(self, a, b, c, d):
        self.tri(a, b, c)
        self.tri(a, c, d)

    def loft(self, st, sides, off=(0, 0, 0)):
        off = np.asarray(off, float)
        rings = []
        for (z, w, h, y) in st:
            ring = []
            for k in range(sides):
                a = (k + 0.5) / sides * math.pi * 2
                ring.append(off + np.array([math.cos(a) * w * 0.5, y + math.sin(a) * h * 0.5, z]))
            rings.append(ring)
        for s in range(len(st) - 1):
            for k in range(sides):
                k1 = (k + 1) % sides
                self.quad(rings[s][k], rings[s][k1], rings[s + 1][k1], rings[s + 1][k])
        cf = off + np.array([0, st[0][3], st[0][0] + 0.05])
        cb = off + np.array([0, st[-1][3], st[-1][0] - 0.02])
        for k in range(sides):
            k1 = (k + 1) % sides
            self.tri(cf, rings[0][k1], rings[0][k])
            self.tri(cb, rings[-1][k], rings[-1][k1])

    def disc(self, c, r, sides, n):
        c, n = np.asarray(c, float), np.asarray(n, float)
        u = np.cross(n, [0, 1, 0] if abs(n[1]) < 0.9 else [1, 0, 0]); u /= np.linalg.norm(u)
        w = np.cross(n, u)
        for k in range(sides):
            a0, a1 = k / sides * math.pi * 2, (k + 1) / sides * math.pi * 2
            self.tri(c, c + (u * math.cos(a0) + w * math.sin(a0)) * r, c + (u * math.cos(a1) + w * math.sin(a1)) * r)
        self.disc_normal = n

    def plate(self, a, b, c, d, thick, vertical=False):
        a, b, c, d = (np.asarray(x, float) for x in (a, b, c, d))
        o = np.array([1, 0, 0] if vertical else [0, 1, 0]) * thick * 0.5
        self.quad(a + o, b + o, c + o, d + o)
        self.quad(d - o, c - o, b - o, a - o)
        self.quad(a - o, b - o, b + o, a + o)
        self.quad(b - o, c - o, c + o, b + o)
        self.quad(c - o, d - o, d + o, c + o)
        self.quad(d - o, a - o, a + o, d + o)


def box(c, size):
    m = MB()
    c, h = np.asarray(c, float), np.asarray(size, float) * 0.5
    m.plate(c + [-h[0], 0, h[2]], c + [h[0], 0, h[2]], c + [h[0], 0, -h[2]], c + [-h[0], 0, -h[2]], size[1])
    return m


def plate(a, b, c, d, thick, vertical=False):
    m = MB(); m.plate(a, b, c, d, thick, vertical); return m


def pod(x, y, z0, z1, r):
    m = MB()
    m.loft([(z0, r * 1.4, r * 1.4, 0), (z0 + (z1 - z0) * 0.4, r * 2, r * 2, 0), (z1, r * 1.7, r * 1.7, 0)], 10, (x, y, 0))
    return m


def disc(c, r, n):
    m = MB(); m.disc(c, r, 12, n); return m


# ---------------------------------------------------------------- materiais

MATS = {}


def mat(name, rgb, metallic=0.35, rough=0.38, emit=0.0):
    key = (name, tuple(round(x, 3) for x in rgb), emit)
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    lin = tuple(float(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in rgb)   # sRGB 0..1 → linear
    b.inputs['Base Color'].default_value = (*lin, 1.0)
    b.inputs['Metallic'].default_value = metallic
    b.inputs['Roughness'].default_value = rough
    if emit > 0:
        b.inputs['Emission Color'].default_value = (*lin, 1.0)
        b.inputs['Emission Strength'].default_value = emit
    MATS[key] = m
    return m


def hexrgb(h):
    return ((h >> 16 & 255) / 255, (h >> 8 & 255) / 255, (h & 255) / 255)


GLOW = {'reactor_small': (0.3, 0.95, 1), 'reactor_steady': (0.35, 0.55, 1), 'reactor_flux': (1, 0.25, 0.85),
        'reactor_large': (1, 0.7, 0.2), 'reactor_helios': (1, 0.93, 0.6)}

# ---------------------------------------------------------------- ShipBuilder.BuildVisual (tradução direta)


def build_visual(cid, hull_z, mounted, paint):
    """mounted: socket -> (visual, tamanho 'S'|'M'|'L'). Devolve [(nome, MB, material, offset do socket)]."""
    parts = []
    V = lambda s: mounted.get(s, ('', 'M'))[0]
    def Sz(s, stock=1.0):
        if s not in mounted: return stock
        return {'S': 0.8, 'M': 1.0, 'L': 1.3}[mounted[s][1]]
    m_paint = mat('Pintura', paint, 0.25, 0.32)
    m_dark = mat('Escuro', (0.09, 0.1, 0.11), 0.6, 0.45)
    m_metal = mat('Metal', (0.32, 0.33, 0.35), 0.9, 0.32)
    m_glass = mat('Vidro', (0.05, 0.08, 0.12), 0.2, 0.05)
    glow_rgb = GLOW.get(V('Reactor'), (1, 0.42, 0.12))
    m_glow = mat('Brilho', glow_rgb, 0, 0.5, 18.0)
    P = lambda name, mb, m, off=(0, 0, 0): parts.append((name, mb, m, np.asarray(off, float)))

    w = 0.72 if cid == 'wraith' else 1.22 if cid == 'bastion' else 1.06 if cid == 'nomad' else 1.0
    hgt = 0.9 if cid == 'bastion' else 1.15 if cid == 'nomad' else 0.85 if cid == 'wraith' else 1.0
    ln = hull_z / 7.0
    hull = MB()
    if cid == 'vortex':
        hull.loft([(3.3 * ln, 0.5, 0.22, -0.16), (2.0 * ln, 1.5, 0.5, -0.1), (0.2 * ln, 2.4, 0.8, 0), (-1.6 * ln, 3.3, 0.95, 0.02), (-3.3 * ln, 3.4, 0.9, 0)], 8)
    else:
        hull.loft([(3.55 * ln, 0.55 * w, 0.22 * hgt, -0.18), (2.6 * ln, 1.6 * w, 0.46 * hgt, -0.12), (1.2 * ln, 2.5 * w, 0.74 * hgt, -0.02),
                   (-0.6 * ln, 2.95 * w, 0.86 * hgt, 0.02), (-2.4 * ln, 3.1 * w, 0.82 * hgt, 0), (-3.35 * ln, 2.7 * w, 0.62 * hgt, -0.02)], 8)
    P('Body_Core', hull, m_paint)
    belly = MB(); belly.loft([(2.4 * ln, 1.3 * w, 0.12, -0.36 * hgt), (-0.5 * ln, 2.6 * w, 0.16, -0.42 * hgt), (-3.1 * ln, 2.4 * w, 0.14, -0.36 * hgt)], 8)
    P('Belly', belly, m_dark)
    cz = 1.25 if cid == 'wraith' else 1.0
    canopy = MB(); canopy.loft([(1.5 * ln * cz, 0.2, 0.12, 0.32 * hgt), (0.9 * ln, 0.95 * w, 0.42, 0.42 * hgt), (-0.3 * ln, 1.05 * w, 0.46, 0.44 * hgt), (-1.2 * ln, 0.7 * w, 0.3, 0.38 * hgt)], 8)
    P('Canopy', canopy, m_glass)
    if cid == 'bastion':
        for side in (-1, 1): P('Shoulder', box((1.75 * side, 0.18, -0.3), (0.6, 0.55, 3.2)), m_dark)
    if cid == 'nomad':
        for side in (-1, 1): P('Tank', pod(1.55 * side, 0.25, 0.8, -1.6, 0.26), m_metal)

    # motor
    eng = (0, 0.3 * hgt, -2.4 * ln)
    ev, es = V('Engine'), Sz('Engine')
    P('Engine_Block', box((0, 0, 0), (1.1 * es, 0.42 * es, 1.6 * es)), mat('Redline', (0.75, 0.05, 0.04), 0.5, 0.3) if ev == 'engine_redline' else m_dark, eng)
    if ev in ('engine_sprint', 'engine_redline', 'engine_burner'):
        for side in (-1, 1): P('Intake', box((0.38 * side * es, 0.26 * es, 0.5), (0.22, 0.18, 0.7)), m_metal, eng)
    if ev in ('engine_heavy', 'engine_relic'):
        P('Engine_Housing', box((0, 0.2 * es, -0.2), (1.5 * es, 0.25, 1.2 * es)), m_metal, eng)
    if ev == 'engine_redline':
        P('Redline_Glow', disc((0, 0, -0.82 * es), 0.25, (0, 0, -1)), mat('RedGlow', (1, 0.15, 0.1), 0, 0.5, 22.0), eng)

    # propulsão
    ps = Sz('Propulsion'); r = 0.42 * ps
    px = 1.0 if cid == 'wraith' else 1.7 if cid == 'bastion' else 1.45 if cid == 'vortex' else 1.32 * w
    for side in (-1, 1):
        sp = np.array([px * side, 0.04, 0])
        P('Nacelle', pod(0, 0, -0.6 * ln, -3.4 * ln * (0.9 + 0.1 * ps), r), m_dark, sp)
        noz = np.array([px * side, 0.04, -3.45 * ln * (0.9 + 0.1 * ps) - 0.05])
        P('Nozzle', disc(noz - sp, r * 0.62, (0, 0, -1)), m_glow, sp)
    if cid == 'vortex':
        pc = Sz('PropulsionC', 0.9)
        sc_ = (0, 0.38, 0)
        P('Nacelle_C', pod(0, 0, -0.9 * ln, -3.6 * ln, 0.48 * pc), m_dark, sc_)
        P('Nozzle_C', disc((0, 0, -3.62 * ln), 0.3 * pc, (0, 0, -1)), m_glow, sc_)

    # asas
    wv = V('Wings')
    span = {'wing_short': 0.5, 'wing_long': 1.25, 'wing_heavy': 1.0, 'wing_relic': 1.1, 'wing_vector': 0.85}.get(wv, 0.7)
    chord = 2.6 if wv == 'wing_long' else 1.6 if wv == 'wing_short' else 2.2
    thick = 0.16 if wv == 'wing_heavy' else 0.07
    if cid == 'wraith': span *= 0.75
    for side in (-1, 1):
        ws = ((px + 0.1) * side, 0, -0.4)
        x0, x1 = 0, span * side
        P('Wing', plate((x0, -0.02, 0), (x1, 0.08, -0.6), (x1, 0.08, -0.6 - chord * 0.6), (x0, -0.02, -chord), thick), m_paint, ws)
        if wv == 'wing_vector':
            P('Wing_Vector', plate((x0, 0.32, -0.9), (x1 * 0.7, 0.42, -1.2), (x1 * 0.7, 0.42, -1.7), (x0, 0.32, -1.9), 0.05), m_metal, ws)
        if wv == 'wing_relic':
            P('Wing_Tip', plate((x1, 0.08, -0.6), (x1 + 0.15 * side, 0.5, -0.9), (x1 + 0.15 * side, 0.5, -1.4), (x1, 0.08, -1.9), 0.05, True), m_paint, ws)

    # cauda
    tv = V('Tail'); ts = (0, 0.38 * hgt, -2.0 * ln)
    if tv == 'tail_twin':
        for side in (-0.45, 0.45):
            P('Fin', plate((side, 0, 0), (side * 1.3, 0.6, -0.9), (side * 1.3, 0.6, -1.2), (side, 0, -1.3), 0.07, True), m_paint, ts)
    else:
        fh = 0.75 if tv == 'tail_long' else 0.4 if tv == 'tail_compact' else 0.57
        fl = 1.9 if tv == 'tail_long' else 1.3
        P('Fin', plate((0, 0, 0), (0, fh, -0.9), (0, fh, -fl + 0.05), (0, 0, -fl), 0.08, True), m_paint, ts)
        if tv == 'tail_long': P('Keel_Vent', box((0, 0.1, -1.2), (0.3, 0.12, 0.6)), m_dark, ts)

    # blindagem
    def armor_at(socket, z):
        if socket not in mounted: return
        av = mounted[socket][0]
        th = 0.22 if av == 'armor_heavy' else 0.06 if av == 'armor_light' else 0.12
        mm = mat('Aegis', (0.62, 0.5, 0.22), 0.9, 0.3) if av == 'armor_aegis' else m_metal
        for side in (-1, 1):
            P('Armor_Plate', box((0, 0, 0), (th + 0.1, 0.5, 2.6 if av == 'armor_heavy' else 2.0)), mm, (1.32 * w * side, 0.1, z))
    armor_at('Armor', 0.4)
    armor_at('Armor2', -1.6)

    # reator
    rs = (0, 0.55 * hgt, -1.45 * ln)
    rr = 0.28 * Sz('Reactor') if 'Reactor' in mounted else 0.18
    P('Reactor_Core', disc((0, 0, 0), rr, (0, 1, 0)), m_glow, rs)
    P('Reactor_Ring', box((0, -0.06, 0), (rr * 2.6, 0.08, rr * 2.6)), m_dark, rs)

    # refrigeração
    cv = V('Cooling')
    if cv:
        fins = 6 if cv == 'cooling_grid' else 4 if cv == 'cooling_radiator' else 2
        for side in (-1, 1):
            for f in range(fins):
                P('Radiator_Fin', box((0, 0.08, -f * 0.22), (0.5, 0.16, 0.05)), m_metal, (0.75 * w * side, 0.45 * hgt, -0.6))

    # navegação / utilidade
    uv = V('Utility') + V('Aux'); us = (0, 0.6 * hgt, 0.2)
    if 'util_mast' in uv: P('Mast', box((0.3, 0.3, 0), (0.05, 0.6, 0.05)), m_metal, us)
    if 'util_dome' in uv: P('Dome', disc((0, 0.05, 0), 0.22, (0, 1, 0)), mat('Dome', (0.4, 1, 0.8), 0, 0.5, 10.0), us)
    if 'util_drone' in uv: P('Drone', box((-0.3, 0.1, -0.4), (0.35, 0.15, 0.35)), m_dark, us)
    return parts


def spawn_ship(sc, name, cid, hull_z, mounted, paint, pos_u, Rv, Uv, Tv, M):
    """Cria os objetos da nave no mundo do Blender: local Unity (x dir., y cima, z frente) → mundo Unity → Blender."""
    objs = []
    for pname, mb, m, off in build_visual(cid, hull_z, mounted, paint):
        if not mb.v: continue
        world = []
        for p in mb.v:
            q = p + off
            wu = pos_u + Rv * q[0] + Uv * q[1] + Tv * q[2]
            world.append(M @ wu)
        world = np.array(world)
        me = bpy.data.meshes.new(f"{name}_{pname}")
        me.from_pydata([tuple(x) for x in world], [], [tuple(t) for t in mb.t])
        me.update()
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bm.normal_update()
        cen = sum((v.co for v in bm.verts), Vector()) / max(1, len(bm.verts))
        disc_n = getattr(mb, 'disc_normal', None)
        want = Vector((M @ (Rv * disc_n[0] + Uv * disc_n[1] + Tv * disc_n[2])).tolist()) if disc_n is not None else None
        for f in bm.faces:
            out = (f.calc_center_median() - cen) if want is None else want
            if f.normal.dot(out) < 0: f.normal_flip()
        bm.to_mesh(me); bm.free()
        for poly in me.polygons: poly.use_smooth = False
        ob = bpy.data.objects.new(f"{name}_{pname}", me)
        ob.data.materials.append(m)
        sc.collection.objects.link(ob)
        objs.append(ob)
    return objs


# ---------------------------------------------------------------- builds das fotos (visual, tamanho) por socket

CHASSIS = {
    'strix': dict(name='STRIX', z=7.0, paint=0xB8150F),
    'wraith': dict(name='WRAITH', z=7.2, paint=0x1C2733),
    'nomad': dict(name='NOMAD', z=7.8, paint=0xC9A25A),
    'bastion': dict(name='BASTION', z=7.4, paint=0x5E6A4C),
    'vortex': dict(name='VORTEX', z=7.0, paint=0x2A55C8),
}
BUILDS = {
    'strix': {'Engine': ('engine_sprint', 'M'), 'Propulsion': ('prop_medium', 'M'), 'Wings': ('wing_vector', 'M'), 'Armor': ('armor_medium', 'M'),
              'Reactor': ('reactor_steady', 'M'), 'Cooling': ('cooling_radiator', 'M'), 'Tail': ('tail_twin', 'M'), 'Utility': ('util_mast', 'M')},
    'wraith': {'Engine': ('engine_burner', 'S'), 'Propulsion': ('prop_small', 'S'), 'Wings': ('wing_vector', 'M'), 'Armor': ('armor_light', 'S'),
               'Reactor': ('reactor_small', 'S'), 'Cooling': ('cooling_vents', 'S'), 'Tail': ('tail_compact', 'S'), 'Utility': ('util_dome', 'M')},
    'nomad': {'Engine': ('engine_relic', 'L'), 'Propulsion': ('prop_medium', 'M'), 'Wings': ('wing_long', 'M'), 'Armor': ('armor_medium', 'M'),
              'Reactor': ('reactor_large', 'L'), 'Cooling': ('cooling_grid', 'L'), 'Tail': ('tail_long', 'L'), 'Utility': ('util_drone', 'M'), 'Aux': ('util_mast', 'M')},
    'bastion': {'Engine': ('engine_heavy', 'L'), 'Propulsion': ('prop_large', 'L'), 'Wings': ('wing_heavy', 'L'), 'Armor': ('armor_heavy', 'L'),
                'Armor2': ('armor_heavy', 'L'), 'Reactor': ('reactor_large', 'L'), 'Cooling': ('cooling_grid', 'L'), 'Tail': ('tail_long', 'L'), 'Utility': ('util_mast', 'M')},
    'vortex': {'Engine': ('engine_redline', 'M'), 'Propulsion': ('prop_medium', 'M'), 'PropulsionC': ('prop_medium', 'M'), 'Wings': ('wing_vector', 'M'),
               'Armor': ('armor_aegis', 'M'), 'Reactor': ('reactor_flux', 'M'), 'Cooling': ('cooling_radiator', 'M'), 'Tail': ('tail_twin', 'M'), 'Utility': ('util_dome', 'M')},
}


def main():
    import json
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = setup_scene()
    spec = json.load(open(SPEC, encoding='utf-8'))
    rows, step = integrate(spec)
    Pp, Tt, Rr, Uu = frames(rows)
    dist = np.array([r['dist'] for r in rows])
    M = unity_to_blender_matrix()
    B = lambda v: Vector((M @ np.asarray(v, float)).tolist())

    geo_mat = geology_material()
    name = os.path.basename(os.path.normpath(EXPORT))
    for f in (f'{name}_corridor_00.fbx', f'{name}_terrain_00.fbx'):
        path = os.path.join(EXPORT, f)
        if not os.path.exists(path): continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=path, colors_type='LINEAR')
        for o in [o for o in bpy.data.objects if o not in before and o.type == 'MESH']:
            o.data.materials.clear(); o.data.materials.append(geo_mat)
        log(f"importado {f}")

    def frame_at(d):
        i = int(np.clip(np.searchsorted(dist, d), 1, len(dist) - 2))
        return Pp[i], Tt[i], Rr[i], Uu[i]

    # grelha: as 5 naves lado a lado (8 m), a STRIX de série uma fila atrás para comparar com a STRIX modificada
    order = ['wraith', 'nomad', 'strix', 'bastion', 'vortex']
    d0 = 150.0
    p, t, r, u = frame_at(d0)
    ships = {}
    for k, cid in enumerate(order):
        c = CHASSIS[cid]
        pos = p + r * ((k - 2) * 8.0) + u * 1.6
        ships[cid] = (pos, spawn_ship(sc, c['name'], cid, c['z'], BUILDS[cid], hexrgb(c['paint']), pos, r, u, t, M))
    # comparação num sítio livre mais à frente: STRIX de série (esq.) ao lado da STRIX com módulos (dir.)
    p2, t2, r2, u2 = frame_at(d0 + 140.0)
    stock_pos = p2 - r2 * 4.5 + u2 * 1.6
    mod_pos = p2 + r2 * 4.5 + u2 * 1.6
    spawn_ship(sc, 'STRIX_serie', 'strix', 7.0, {}, hexrgb(0xB8150F), stock_pos, r2, u2, t2, M)
    spawn_ship(sc, 'STRIX_mod', 'strix', 7.0, BUILDS['strix'], hexrgb(0xB8150F), mod_pos, r2, u2, t2, M)

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.clip_start, cam_data.clip_end = 0.1, 60000.0
    cam = bpy.data.objects.new("Camera", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam

    def shoot(fname, pos_u, target_u, lens):
        pos, target = B(pos_u), B(target_u)
        up = B(u)
        fwd = (target - pos).normalized()
        right = fwd.cross(up).normalized()
        upv = right.cross(fwd)
        cam.matrix_world = Matrix.Translation(pos) @ Matrix((right, upv, -fwd)).transposed().to_4x4()
        cam_data.lens = lens
        sc.render.filepath = os.path.join(OUT, fname)
        bpy.ops.render.render(write_still=True)
        log(f"foto {fname}")

    mid = p + u * 1.6
    shoot('naves_01_grelha_frente.jpg', mid + t * 26 + u * 2.6 + r * 3, mid - t * 4 + r * 1.5, 26)
    shoot('naves_02_grelha_traseira.jpg', mid - t * 30 + u * 4.5 - r * 4, mid + t * 10, 24)
    pair = (stock_pos + mod_pos) * 0.5
    shoot('naves_03_strix_serie_vs_modulos.jpg', pair + t2 * 15 + u2 * 3.4 - r2 * 2, pair - t2 * 1.5, 32)
    shoot('naves_03b_strix_serie_vs_modulos_tras.jpg', pair - t2 * 15 + u2 * 3.8 + r2 * 2, pair + t2 * 1.0, 32)
    for cid in order:
        pos = ships[cid][0]
        shoot(f'naves_{cid}_frente.jpg', pos + t * 9 + r * 6 + u * 1.6, pos + u * 0.2, 38)
        shoot(f'naves_{cid}_traseira.jpg', pos - t * 9.5 - r * 5 + u * 2.4, pos + u * 0.3, 38)
    shoot('naves_04_aerea.jpg', mid - t * 18 + u * 26 + r * 2, mid + t * 6, 28)


main()
