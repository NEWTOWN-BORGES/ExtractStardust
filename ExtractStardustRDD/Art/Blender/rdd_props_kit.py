"""
EXTRACT: STARDUST — kit de adereços da paisagem (low-poly, gerado): árvores secas, saguaros, palmas (prickly pear),
cactos-barril, arbustos secos/verdes, tufos de erva, choupos (zonas verdes), zimbros, árvores-de-josué, pedregulhos
e monumentos de horizonte (mesas, buttes, agulhas) já com as cores de vértice do material de geologia do jogo
(r = classe, g/b = índices da paleta RD_PAL / 15).
  blender -b --factory-startup -P rdd_props_kit.py -- <saida.fbx>
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

OUT = os.path.abspath(sys.argv[sys.argv.index('--') + 1])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
MATS = {}


def mat(name):
    if name not in MATS:
        MATS[name] = bpy.data.materials.new(name)
    return MATS[name]


def pal(i):
    return i / 15.0


class B:
    """Construtor de uma malha: faces com material e (opcional) cor de vértice; suave ou facetada."""

    def __init__(self, name, seed):
        self.name, self.bm, self.mats, self.faces = name, bmesh.new(), [], []
        self.r = np.random.default_rng(seed)

    def face(self, vs, m, col=None, flat=False):
        if m not in self.mats:
            self.mats.append(m)
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self.mats.index(m)
        f.smooth = not flat
        self.faces.append((f, col))
        return f

    def tube(self, pts, sides, m, ribs=0.0, col=None, flat=False):
        rings = []
        for k, (p, rad) in enumerate(pts):
            a = pts[min(k + 1, len(pts) - 1)][0] - pts[max(k - 1, 0)][0]
            d = a.normalized() if a.length > 1e-6 else Vector((0, 0, 1))
            ax = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))
            u = d.cross(ax).normalized()
            v = d.cross(u).normalized()
            ring = []
            for s in range(sides):
                ang = 2 * math.pi * s / sides
                rr = rad * (1.0 - ribs if (ribs and s % 2) else 1.0)
                ring.append(self.bm.verts.new(p + (u * math.cos(ang) + v * math.sin(ang)) * rr))
            rings.append(ring)
        for ra, rb in zip(rings, rings[1:]):
            for s in range(sides):
                self.face([ra[s], ra[(s + 1) % sides], rb[(s + 1) % sides], rb[s]], m, col, flat)
        self.face(list(reversed(rings[0])), m, col, flat)
        tip = self.bm.verts.new(pts[-1][0] + (pts[-1][0] - pts[-2][0]).normalized() * pts[-1][1] * 0.6)
        for s in range(sides):
            self.face([rings[-1][s], rings[-1][(s + 1) % sides], tip], m, col, flat)

    def blob(self, c, radii, m, subdiv=1, noise=0.15, rot=None, col=None, flat=False):
        tmp = bmesh.new()
        bmesh.ops.create_icosphere(tmp, subdivisions=subdiv, radius=1.0)
        R = rot or Matrix.Identity(3)
        vm = {}
        for v in tmp.verts:
            n = v.co.normalized()
            k = 1.0 + noise * self.r.uniform(-1, 1)
            local = Vector((n.x * radii[0] * k, n.y * radii[1] * k, n.z * radii[2] * k))
            vm[v] = self.bm.verts.new(Vector(c) + R @ local)
        for f in tmp.faces:
            self.face([vm[v] for v in f.verts], m, col, flat)
        tmp.free()

    def blade(self, base, h, w, lean, m):
        ang = self.r.uniform(0, 2 * math.pi)
        dx, dy = math.cos(ang), math.sin(ang)
        b = Vector(base)
        tip = b + Vector((dx * lean, dy * lean, h))
        p = [b + Vector((-dy * w, dx * w, 0)), b + Vector((dy * w, -dx * w, 0)), b + Vector((dx * w * 0.7, dy * w * 0.7, 0))]
        vs = [self.bm.verts.new(q) for q in p]
        vt = self.bm.verts.new(tip)
        for a, c in ((0, 1), (1, 2), (2, 0)):
            self.face([vs[a], vs[c], vt], m)

    def finish(self):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        if any(c is not None for _, c in self.faces):
            cl = self.bm.loops.layers.float_color.new('Col')
            for f, c in self.faces:
                if f.is_valid:
                    for lp in f.loops:
                        lp[cl] = c if c is not None else (0.75, pal(8), pal(9), 0.0)
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(mat(m))
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def V(x, y, z):
    return Vector((x, y, z))


# ------------------------------------------------------------------ vegetação e adereços (instanciados no jogo)

def dead_tree(name, seed):
    b = B(name, seed)
    r = b.r
    h = r.uniform(2.6, 4.4)
    pts, x, y = [], 0.0, 0.0
    for k in range(7):
        t = k / 6
        x += r.uniform(-0.18, 0.18)
        y += r.uniform(-0.18, 0.18)
        pts.append((V(x, y, t * h), 0.22 * (1 - t) + 0.04))
    b.tube(pts, 6, 'Prop_DeadWood')
    for _ in range(int(r.integers(3, 7))):
        k = int(r.integers(2, 6))
        p0 = pts[k][0]
        ang = r.uniform(0, 2 * math.pi)
        L = r.uniform(0.7, 1.9)
        d = V(math.cos(ang), math.sin(ang), r.uniform(0.3, 1.2)).normalized()
        q = [(p0, 0.08), (p0 + d * L * 0.5 + V(0, 0, 0.12), 0.05), (p0 + d * L + V(0, 0, r.uniform(0.1, 0.6)), 0.018)]
        b.tube(q, 5, 'Prop_DeadWood')
        if r.random() < 0.6:
            q2 = q[1][0]
            d2 = V(math.cos(ang + 0.9), math.sin(ang + 0.9), 0.8).normalized()
            b.tube([(q2, 0.035), (q2 + d2 * L * 0.45, 0.012)], 4, 'Prop_DeadWood')
    return b.finish()


def saguaro(name, seed):
    b = B(name, seed)
    r = b.r
    h = r.uniform(3.6, 6.2)
    zs = np.linspace(0, 1, 8)
    b.tube([(V(0, 0, z * h), 0.3 * (1.0 if z < 0.88 else max(0.45, 1 - (z - 0.88) * 4.5))) for z in zs], 12, 'Prop_Cactus', ribs=0.12)
    for _ in range(int(r.integers(1, 4))):
        z0 = r.uniform(0.32, 0.62) * h
        ang = r.uniform(0, 2 * math.pi)
        dv = V(math.cos(ang), math.sin(ang), 0)
        out = r.uniform(0.6, 0.95)
        up = r.uniform(0.9, 1.9)
        base = V(0, 0, z0)
        b.tube([(base + dv * 0.1, 0.2), (base + dv * out * 0.7 + V(0, 0, 0.06), 0.2), (base + dv * out + V(0, 0, 0.4), 0.19),
                (base + dv * out + V(0, 0, up), 0.16)], 10, 'Prop_Cactus', ribs=0.12)
    return b.finish()


def prickly_pear(name, seed):
    b = B(name, seed)
    r = b.r
    pads = [(V(0, 0, 0.35), 0.0, 0.0)]
    for k in range(int(r.integers(6, 11))):
        par = pads[int(r.integers(0, len(pads)))]
        ang = r.uniform(0, 2 * math.pi)
        tilt = r.uniform(-0.5, 0.5)
        c = par[0] + V(math.cos(ang) * 0.3, math.sin(ang) * 0.3, r.uniform(0.25, 0.5))
        pads.append((c, ang, tilt))
    for c, ang, tilt in pads:
        rot = (Matrix.Rotation(ang, 3, 'Z') @ Matrix.Rotation(tilt, 3, 'Y'))
        b.blob(c, (0.3, 0.07, 0.38), 'Prop_Cactus', subdiv=1, noise=0.08, rot=rot)
        if r.random() < 0.45:
            b.blob(c + rot @ V(0, 0, 0.4), (0.06, 0.06, 0.07), 'Prop_Fruit', subdiv=1, noise=0.05)
    return b.finish()


def barrel(name, seed):
    b = B(name, seed)
    b.tube([(V(0, 0, 0), 0.32), (V(0, 0, 0.25), 0.38), (V(0, 0, 0.55), 0.34), (V(0, 0, 0.72), 0.2)], 14, 'Prop_Cactus', ribs=0.14)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        b.blob(V(math.cos(a) * 0.1, math.sin(a) * 0.1, 0.8), (0.06, 0.06, 0.05), 'Prop_Flower', subdiv=1, noise=0.05)
    return b.finish()


def bush(name, seed, m):
    b = B(name, seed)
    r = b.r
    for _ in range(int(r.integers(6, 10))):
        a = r.uniform(0, 2 * math.pi)
        d = r.uniform(0, 0.55)
        rad = r.uniform(0.32, 0.62)
        b.blob(V(math.cos(a) * d, math.sin(a) * d, rad * 0.8 + r.uniform(0, 0.25)), (rad, rad, rad * 0.85), m, subdiv=1, noise=0.22)
    return b.finish()


def grass(name, seed, m):
    b = B(name, seed)
    r = b.r
    for _ in range(int(r.integers(12, 18))):
        a = r.uniform(0, 2 * math.pi)
        d = r.uniform(0, 0.28)
        b.blade((math.cos(a) * d, math.sin(a) * d, 0), r.uniform(0.35, 0.9), 0.035, r.uniform(0.05, 0.3), m)
    return b.finish()


def cottonwood(name, seed):
    b = B(name, seed)
    r = b.r
    h = r.uniform(2.2, 3.0)
    trunk = [(V(0, 0, 0), 0.32), (V(r.uniform(-.2, .2), r.uniform(-.2, .2), h * 0.5), 0.26), (V(r.uniform(-.3, .3), r.uniform(-.3, .3), h), 0.2)]
    b.tube(trunk, 8, 'Prop_Bark')
    top = trunk[-1][0]
    for _ in range(3):
        a = r.uniform(0, 2 * math.pi)
        e = top + V(math.cos(a) * 1.2, math.sin(a) * 1.2, r.uniform(1.5, 2.6))
        b.tube([(top, 0.16), ((top + e) / 2 + V(0, 0, 0.3), 0.11), (e, 0.05)], 6, 'Prop_Bark')
    for _ in range(int(r.integers(7, 11))):
        a = r.uniform(0, 2 * math.pi)
        d = r.uniform(0.3, 1.8)
        rad = r.uniform(1.0, 1.7)
        b.blob(top + V(math.cos(a) * d, math.sin(a) * d, r.uniform(1.4, 3.2)), (rad, rad, rad * 0.8), 'Prop_Leaves', subdiv=1, noise=0.2)
    return b.finish()


def juniper(name, seed):
    b = B(name, seed)
    r = b.r
    pts, x = [], 0.0
    for k in range(4):
        x += r.uniform(-0.25, 0.25)
        pts.append((V(x, 0, k * 0.45), 0.18 - k * 0.03))
    b.tube(pts, 6, 'Prop_DeadWood')
    for _ in range(int(r.integers(6, 9))):
        a = r.uniform(0, 2 * math.pi)
        d = r.uniform(0.2, 0.9)
        rad = r.uniform(0.5, 0.95)
        b.blob(V(x + math.cos(a) * d, math.sin(a) * d, r.uniform(0.9, 2.3)), (rad, rad, rad * 0.85), 'Prop_Juniper', subdiv=1, noise=0.25)
    return b.finish()


def joshua(name, seed):
    b = B(name, seed)
    r = b.r
    h = r.uniform(1.8, 2.6)
    b.tube([(V(0, 0, 0), 0.22), (V(0, 0, h * 0.6), 0.18), (V(0.05, 0, h), 0.15)], 7, 'Prop_DeadWood')
    top = V(0.05, 0, h)
    for _ in range(int(r.integers(2, 5))):
        a = r.uniform(0, 2 * math.pi)
        e = top + V(math.cos(a) * r.uniform(0.6, 1.1), math.sin(a) * r.uniform(0.6, 1.1), r.uniform(0.5, 1.2))
        b.tube([(top, 0.12), (e, 0.09)], 6, 'Prop_DeadWood')
        for _ in range(5):
            dv = V(r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0.2, 1.0)).normalized()
            b.tube([(e, 0.08), (e + dv * 0.45, 0.01)], 4, 'Prop_Joshua')
    return b.finish()


def boulder(name, seed, radii):
    b = B(name, seed)
    b.blob(V(0, 0, radii[2] * 0.7), radii, 'Prop_Rock', subdiv=2, noise=0.22, flat=True)
    return b.finish()


# ------------------------------------------------------------------ monumentos de horizonte (material de geologia, cores de vértice)

def monument(name, seed, R, H, n, taper, cap):
    b = B(name, seed)
    r = b.r
    angs = np.sort((np.arange(n) + r.uniform(-0.3, 0.3, n)) / n * 2 * math.pi)
    rad = R * (1.0 + 0.28 * r.uniform(-1, 1, n))
    # anéis: (altura relativa, escala do raio, cor da faixa acima)
    talus = (0.375, pal(2), pal(3), 0.0)
    layers = [(0.0, 1.45, talus), (0.2, 1.06, (0.75, pal(6), pal(7), 0.0)), (0.42, 1.0, (0.75, pal(5), pal(2), 0.0)),
              (0.7, 1.0 - taper * 0.5, (0.75, pal(8), pal(9), 0.0)), (1.0, 1.0 - taper, (0.75, pal(10), pal(11), 0.0)),
              (1.0 + cap, (1.0 - taper) * 0.93, (0.9, pal(10), pal(1), 0.0))]
    rings = []
    for z, s, _ in layers:
        jit = 1.0 + 0.04 * r.uniform(-1, 1, n)
        rings.append([b.bm.verts.new(V(math.cos(a) * rr * s * j, math.sin(a) * rr * s * j, z * H)) for a, rr, j in zip(angs, rad, jit)])
    for k in range(len(rings) - 1):
        col = layers[k + 1][2] if k > 0 else talus
        for s in range(n):
            b.face([rings[k][s], rings[k][(s + 1) % n], rings[k + 1][(s + 1) % n], rings[k + 1][s]], 'Prop_Geology', col, flat=True)
    ctr = b.bm.verts.new(V(0, 0, (1.0 + cap) * H + 1.0))
    for s in range(n):
        b.face([rings[-1][s], rings[-1][(s + 1) % n], ctr], 'Prop_Geology', (0.9, pal(10), pal(11), 0.0), flat=True)
    return b.finish()


objs = []
for k, s in enumerate((11, 12, 13)):
    objs.append(dead_tree(f"P_DeadTree_{'ABC'[k]}", s))
objs += [saguaro('P_Saguaro_A', 21), saguaro('P_Saguaro_B', 22), prickly_pear('P_PricklyPear', 31), barrel('P_Barrel', 32)]
objs += [bush('P_Bush_Dry_A', 41, 'Prop_ShrubDry'), bush('P_Bush_Dry_B', 42, 'Prop_ShrubDry'), bush('P_Bush_Green', 43, 'Prop_ShrubGreen')]
objs += [grass('P_Grass_Dry', 51, 'Prop_GrassDry'), grass('P_Grass_Green', 52, 'Prop_GrassGreen')]
objs += [cottonwood('P_Tree_A', 61), cottonwood('P_Tree_B', 62), juniper('P_Juniper', 71), joshua('P_Joshua', 72)]
objs += [boulder('P_Boulder_A', 81, (1.0, 0.85, 0.6)), boulder('P_Boulder_B', 82, (0.8, 0.7, 0.75)), boulder('P_Boulder_C', 83, (1.3, 0.9, 0.45))]
objs += [monument('P_Mesa_A', 91, 220, 120, 18, 0.06, 0.04), monument('P_Mesa_B', 92, 160, 95, 16, 0.08, 0.05),
         monument('P_Butte_A', 93, 55, 115, 12, 0.12, 0.06), monument('P_Butte_B', 94, 40, 85, 11, 0.15, 0.07),
         monument('P_Spire_A', 95, 13, 70, 9, 0.35, 0.08), monument('P_Spire_B', 96, 9, 52, 8, 0.4, 0.1)]

bpy.ops.export_scene.fbx(filepath=OUT, use_selection=False, object_types={'MESH'}, apply_scale_options='FBX_SCALE_UNITS',
                         axis_forward='-Z', axis_up='Y', bake_space_transform=True, use_mesh_modifiers=True, mesh_smooth_type='FACE',
                         add_leaf_bones=False, bake_anim=False, path_mode='STRIP', colors_type='LINEAR')
for ob in objs:
    print(f"[props] {ob.name}: {len(ob.data.polygons)} faces, materiais {[m.name for m in ob.data.materials]}", flush=True)
print(f"[props] exportado {OUT} ({os.path.getsize(OUT) // 1024} KB)", flush=True)
