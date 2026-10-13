"""
EXTRACT: STARDUST — megaestruturas da paisagem (referências de gameplay: naves despenhadas, anéis gigantes, torres,
pórticos e tubagens): low-poly, escala real (dezenas a centenas de metros), materiais Mega_* (metal, ferrugem,
escuro, luz, tecido). Origem no chão (z = 0); o pórtico tem os pilares a ±(vão/2) no eixo X.
  blender -b --factory-startup -P rdd_mega_kit.py -- <saida.fbx>
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


class B:
    def __init__(self, name, seed):
        self.name, self.bm, self.mats = name, bmesh.new(), []
        self.r = np.random.default_rng(seed)

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def box(self, c, size, m, rot=None):
        R = rot or Matrix.Identity(3)
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        vs = [self.bm.verts.new(Vector(c) + R @ Vector((sx * hx, sy * hy, sz * hz))) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            face = self.bm.faces.new([vs[i] for i in f])
            face.material_index = self.mi(m)
            face.smooth = False

    def beam(self, a, b, t, m):
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length
        z = d.normalized()
        x = z.cross(Vector((0, 0, 1)) if abs(z.z) < 0.95 else Vector((1, 0, 0))).normalized()
        y = z.cross(x)
        R = Matrix((x, y, z)).transposed()
        self.box((a + b) / 2, (t, t, L), m, R)

    def prism(self, path, profile, m, cap=True):
        """Extrusão de um perfil 2D (lista (x, z)) ao longo de um caminho (lista de Vector, eixo y local livre)."""
        rings = []
        for k, p in enumerate(path):
            a = path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]
            t = a.normalized()
            x = t.cross(Vector((0, 0, 1)))
            x = x.normalized() if x.length > 1e-6 else Vector((1, 0, 0))
            z = x.cross(t).normalized()
            rings.append([self.bm.verts.new(p + x * px + z * pz) for px, pz in profile])
        n = len(profile)
        for ra, rb in zip(rings, rings[1:]):
            for s in range(n):
                f = self.bm.faces.new([ra[s], ra[(s + 1) % n], rb[(s + 1) % n], rb[s]])
                f.material_index = self.mi(m)
                f.smooth = False
        if cap:
            for rg in (rings[0], list(reversed(rings[-1]))):
                f = self.bm.faces.new(rg)
                f.material_index = self.mi(m)

    def finish(self):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-4)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
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


def ring_wreck(name, seed):
    """Anel de nave (estação/portal) partido, meio enterrado: secção retangular com nervuras e luzes."""
    b = B(name, seed)
    R, n = 62.0, 44
    a0, a1 = math.radians(-20), math.radians(215)
    path = [V(math.cos(a) * R, 0, math.sin(a) * R) for a in np.linspace(a0, a1, n)]
    b.prism(path, [(-5, -7), (5, -7), (6, 0), (5, 7), (-5, 7), (-6, 0)], 'Mega_Metal')
    for k, a in enumerate(np.linspace(a0, a1, 15)):
        c = V(math.cos(a) * R, 0, math.sin(a) * R)
        rot = Matrix.Rotation(-a, 3, 'Y')
        b.box(c, (14, 15, 2.2), 'Mega_Rust' if k % 3 else 'Mega_Dark', rot)
        if k % 2 == 0:
            b.box(c + V(math.cos(a), 0, math.sin(a)) * -7.4, (1.2, 10, 1.0), 'Mega_Glow', rot)
    for k in range(6):                                            # pontas partidas
        a = a1 + math.radians(2 + k * 1.5)
        b.beam(V(math.cos(a1) * R, (k - 2.5) * 2.5, math.sin(a1) * R), V(math.cos(a) * (R + b.r.uniform(-8, 8)), (k - 2.5) * 3.5, math.sin(a) * R + b.r.uniform(-6, 10)), 1.2, 'Mega_Dark')
    return b.finish()


def hull_wreck(name, seed):
    """Casco de cargueiro despenhado: prisma hexagonal afunilado, partido atrás com costelas à vista."""
    b = B(name, seed)
    L = 140.0
    path = [V(0, y, 0) for y in np.linspace(-L / 2, L / 2, 9)]
    prof = [(-16, 0), (-22, 12), (-14, 26), (14, 26), (22, 12), (16, 0)]
    b.prism(path[:7], prof, 'Mega_Metal')
    b.prism([V(0, L / 2 - 36, 0), V(0, L / 2 + 6, 6)], [(x * 0.7, z * 0.75 + 3) for x, z in prof], 'Mega_Rust')   # proa
    for k in range(8):                                            # costelas da parte partida
        y = -L / 2 - 4 - k * 4.0
        h = 26 - k * 2.2
        b.beam(V(-18, y, 0), V(-15, y, h), 1.6, 'Mega_Dark')
        b.beam(V(18, y, 0), V(15, y, h), 1.6, 'Mega_Dark')
        b.beam(V(-15, y, h), V(15, y, h), 1.4, 'Mega_Dark')
    for k in range(10):
        b.box(V(b.r.uniform(-14, 14), b.r.uniform(-60, 60), 26.6), (b.r.uniform(4, 10), b.r.uniform(6, 18), 1.2), 'Mega_Rust')
    for k in range(5):
        b.box(V(22.6, -40 + k * 22, 12), (0.6, 8, 1.2), 'Mega_Glow')
    return b.finish()


def tower(name, seed):
    """Torre industrial: corpo em blocos empilhados, plataformas, antena e luzes de aviso."""
    b = B(name, seed)
    z, w = 0.0, 22.0
    for k in range(5):
        h = b.r.uniform(16, 26)
        b.box(V(0, 0, z + h / 2), (w, w * 0.85, h), 'Mega_Metal' if k % 2 == 0 else 'Mega_Dark')
        b.box(V(0, 0, z + h + 0.8), (w + 8, w * 0.85 + 8, 1.6), 'Mega_Rust')            # plataforma
        b.box(V(w / 2 + 0.3, 0, z + h * 0.6), (0.6, w * 0.6, 1.0), 'Mega_Glow')
        z += h + 1.6
        w *= 0.82
    b.beam(V(0, 0, z), V(0, 0, z + 34), 1.4, 'Mega_Dark')
    b.box(V(0, 0, z + 34.5), (2.2, 2.2, 1.6), 'Mega_Glow')
    for s in (-1, 1):                                             # braços de grua
        b.beam(V(0, 0, z - 10), V(s * 34, 0, z - 4), 1.6, 'Mega_Rust')
        b.beam(V(s * 34, 0, z - 4), V(s * 34, 0, z - 22), 0.5, 'Mega_Dark')
    return b.finish()


def gate(name, seed, span=130.0, height=58.0):
    """Pórtico gigante sobre a pista: dois pilares (fora da pista) ligados por uma viga em treliça com luzes."""
    b = B(name, seed)
    for s in (-1, 1):
        x = s * span / 2
        b.box(V(x, 0, height / 2), (14, 18, height), 'Mega_Metal')
        b.box(V(x, 0, 3), (22, 26, 6), 'Mega_Dark')
        b.box(V(x - s * 7.4, 0, height * 0.55), (0.8, 10, height * 0.6), 'Mega_Glow')
    zt, zb = height + 8, height - 2
    for y in (-6, 6):
        b.beam(V(-span / 2, y, zt), V(span / 2, y, zt), 2.2, 'Mega_Rust')
        b.beam(V(-span / 2, y, zb), V(span / 2, y, zb), 2.2, 'Mega_Rust')
        for k in range(12):
            x0 = -span / 2 + k * span / 12
            b.beam(V(x0, y, zb), V(x0 + span / 12, y, zt), 1.2, 'Mega_Dark')
    b.box(V(0, 0, zb - 3), (span * 0.5, 2, 4), 'Mega_Cloth')
    b.box(V(0, -7.2, zb + 5), (span * 0.8, 0.5, 1.2), 'Mega_Glow')
    return b.finish()


def pipeline(name, seed):
    """Tubagem de 200 m sobre cavaletes."""
    b = B(name, seed)
    L = 200.0
    oct_ = [(math.cos(a) * 2.6, math.sin(a) * 2.6) for a in np.linspace(0, 2 * math.pi, 9)[:-1]]
    b.prism([V(0, y, 7.5) for y in np.linspace(-L / 2, L / 2, 5)], oct_, 'Mega_Rust')
    for y in np.linspace(-L / 2 + 6, L / 2 - 6, 9):
        b.beam(V(-3, y, 0), V(0, y, 7), 1.0, 'Mega_Dark')
        b.beam(V(3, y, 0), V(0, y, 7), 1.0, 'Mega_Dark')
        b.box(V(0, y, 7.5), (6.4, 1.6, 6.4), 'Mega_Metal')
    return b.finish()


objs = [ring_wreck('M_Ring', 1), hull_wreck('M_Hull', 2), tower('M_Tower_A', 3), tower('M_Tower_B', 4), gate('M_Gate', 5), pipeline('M_Pipeline', 6)]
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=False, object_types={'MESH'}, apply_scale_options='FBX_SCALE_UNITS',
                         axis_forward='-Z', axis_up='Y', bake_space_transform=True, use_mesh_modifiers=True, mesh_smooth_type='FACE',
                         add_leaf_bones=False, bake_anim=False, path_mode='STRIP')
for ob in objs:
    dims = ob.dimensions
    print(f"[mega] {ob.name}: {len(ob.data.polygons)} faces · {dims.x:.0f} x {dims.y:.0f} x {dims.z:.0f} m · {[m.name for m in ob.data.materials]}", flush=True)
print(f"[mega] exportado {OUT} ({os.path.getsize(OUT) // 1024} KB)", flush=True)
