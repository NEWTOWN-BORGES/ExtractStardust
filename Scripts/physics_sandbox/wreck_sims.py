"""Renders the wreck simulations (Scripts/physics_sandbox/wreck.py) in Blender: the VORTEX's hull and its modules
(wings split left and right, tail, body kit, cooling) charred and flying apart, a strobe of where each piece was every
fraction of a second, the fireball (a procedural volume: Mantaflow does not run in the bpy module), dust where the
pieces hit hard. One image per way of dying. python3 Scripts/physics_sandbox/wreck_sims.py <out_dir> [cause ...]
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy first: it puts bmesh and mathutils on the path)
import bmesh
import numpy as np
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wreck  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else sys.argv[1]
CAUSES = [a for a in (sys.argv[sys.argv.index('--') + 2:] if '--' in sys.argv else sys.argv[2:])] or list(wreck.CAUSES)
SHIP = 'vortex'
PARTS = [('hull', 'TestShips/%s.fbx' % SHIP, 1250), ('wing', 'TestShips/modules/%s_wing_vector.fbx' % SHIP, 220),
         ('tail', 'TestShips/modules/%s_tail_twin.fbx' % SHIP, 60), ('kit', 'TestShips/modules/%s_armor_aegis.fbx' % SHIP, 160),
         ('cooling', 'TestShips/modules/%s_cooling_radiator.fbx' % SHIP, 70)]


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def import_part(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, 'SourceArt', path))
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    for o in [o for o in bpy.data.objects if o not in before and o.type != 'MESH']:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in new:
        o.select_set(True)
    bpy.context.view_layer.objects.active = new[0]
    if len(new) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.parent = None
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # nose from -Y to +X
    o.data.transform(Matrix.Rotation(math.radians(90), 4, 'Z'))
    return o


def split_x(o):
    """A wing mesh holds both wings: split it at the centre line into left (+Y) and right."""
    left = o.copy()
    left.data = o.data.copy()
    bpy.context.scene.collection.objects.link(left)
    for obj, keep_left in ((left, True), (o, False)):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        kill = [v for v in bm.verts if (v.co.y < 0.0) == keep_left]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        bm.to_mesh(obj.data)
        bm.free()
    return left, o


def to_centre(o):
    pts = [v.co for v in o.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2
    o.data.transform(Matrix.Translation(-c))
    return tuple(c), tuple((hi - lo) / 2)


def charred():
    m = bpy.data.materials.new('Charred')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bs.inputs['Base Color'].default_value = lin('#0c0a09')
    bs.inputs['Roughness'].default_value = 0.78
    bs.inputs['Metallic'].default_value = 0.35
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 3.5
    nz.inputs['Detail'].default_value = 10.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].position = 0.64
    cr.color_ramp.elements[0].color = (0, 0, 0, 1)
    cr.color_ramp.elements[1].position = 0.7
    cr.color_ramp.elements[1].color = (1.0, 0.32, 0.04, 1)
    nt.links.new(nz.outputs['Fac'], cr.inputs['Fac'])
    heat = nt.nodes.new('ShaderNodeAttribute')
    heat.attribute_type = 'OBJECT'
    heat.attribute_name = 'heat'
    em = nt.nodes.new('ShaderNodeMath')
    em.operation = 'MULTIPLY'
    em.inputs[1].default_value = 7.0
    nt.links.new(heat.outputs['Fac'], em.inputs[0])
    nt.links.new(cr.outputs['Color'], bs.inputs['Emission Color'])
    nt.links.new(em.outputs[0], bs.inputs['Emission Strength'])
    al = nt.nodes.new('ShaderNodeAttribute')
    al.attribute_type = 'OBJECT'
    al.attribute_name = 'alpha'
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(al.outputs['Fac'], mx.inputs['Fac'])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(bs.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return m


def volume(name, centre, radius, density, heat, scale, smoke=False):
    """A procedural fireball (or smoke cloud): billowing noise inside a sphere, glowing by its temperature."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=centre, segments=48, ring_count=24)
    o = bpy.context.object
    o.name = name
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pv = nt.nodes.new('ShaderNodeVolumePrincipled')
    pv.inputs['Color'].default_value = (0.06, 0.05, 0.045, 1) if not smoke else (0.18, 0.16, 0.15, 1)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = 9.0
    nz.inputs['Roughness'].default_value = 0.62
    nz.inputs['Distortion'].default_value = 0.5
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    ln = nt.nodes.new('ShaderNodeVectorMath')
    ln.operation = 'LENGTH'
    nt.links.new(tc.outputs['Object'], ln.inputs[0])
    # the outline broken by big lumps, so it is never a ball
    bz = nt.nodes.new('ShaderNodeTexNoise')
    bz.inputs['Scale'].default_value = scale * 0.45
    bz.inputs['Detail'].default_value = 3.0
    nt.links.new(tc.outputs['Object'], bz.inputs['Vector'])
    bm = nt.nodes.new('ShaderNodeMapRange')
    bm.inputs['To Min'].default_value = -0.55 * radius
    bm.inputs['To Max'].default_value = 0.55 * radius
    nt.links.new(bz.outputs['Fac'], bm.inputs['Value'])
    ad = nt.nodes.new('ShaderNodeMath')
    ad.operation = 'ADD'
    nt.links.new(ln.outputs['Value'], ad.inputs[0])
    nt.links.new(bm.outputs['Result'], ad.inputs[1])
    fall = nt.nodes.new('ShaderNodeMapRange')
    fall.inputs['From Min'].default_value = radius * 0.35
    fall.inputs['From Max'].default_value = radius * 0.95
    fall.inputs['To Min'].default_value = 1.0
    fall.inputs['To Max'].default_value = 0.0
    nt.links.new(ad.outputs[0], fall.inputs['Value'])
    sub = nt.nodes.new('ShaderNodeMapRange')
    sub.inputs['From Min'].default_value = 0.38
    sub.inputs['From Max'].default_value = 0.6
    nt.links.new(nz.outputs['Fac'], sub.inputs['Value'])
    dm = nt.nodes.new('ShaderNodeMath')
    dm.operation = 'MULTIPLY'
    nt.links.new(sub.outputs['Result'], dm.inputs[0])
    nt.links.new(fall.outputs['Result'], dm.inputs[1])
    dk = nt.nodes.new('ShaderNodeMath')
    dk.operation = 'MULTIPLY'
    dk.inputs[1].default_value = density
    nt.links.new(dm.outputs[0], dk.inputs[0])
    nt.links.new(dk.outputs[0], pv.inputs['Density'])
    if heat > 0:
        hz = nt.nodes.new('ShaderNodeTexNoise')
        hz.inputs['Scale'].default_value = scale * 1.6
        hz.inputs['Detail'].default_value = 6.0
        nt.links.new(tc.outputs['Object'], hz.inputs['Vector'])
        hm = nt.nodes.new('ShaderNodeMath')
        hm.operation = 'MULTIPLY'
        nt.links.new(hz.outputs['Fac'], hm.inputs[0])
        nt.links.new(fall.outputs['Result'], hm.inputs[1])
        tk = nt.nodes.new('ShaderNodeMapRange')
        tk.inputs['From Min'].default_value = 0.15
        tk.inputs['From Max'].default_value = 0.75
        tk.inputs['To Min'].default_value = 1200.0
        tk.inputs['To Max'].default_value = 3300.0
        nt.links.new(hm.outputs[0], tk.inputs['Value'])
        nt.links.new(tk.outputs['Result'], pv.inputs['Temperature'])
        bi = nt.nodes.new('ShaderNodeMath')
        bi.operation = 'MULTIPLY'
        bi.inputs[1].default_value = heat
        nt.links.new(hm.outputs[0], bi.inputs[0])
        nt.links.new(bi.outputs[0], pv.inputs['Blackbody Intensity'])
    nt.links.new(pv.outputs[0], out.inputs['Volume'])
    o.data.materials.append(m)
    return o


def texture_mat(name, img, scale, tint):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = bpy.data.images.load(os.path.join(ROOT, img))
    t.projection = 'BOX'
    nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.blend_type = 'MULTIPLY'
    mx.inputs['Factor'].default_value = 1.0
    nt.links.new(t.outputs['Color'], mx.inputs[6])
    mx.inputs[7].default_value = tint
    nt.links.new(mx.outputs[2], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.92
    return m


def build_parts():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = []
    for name, path, mass in PARTS:
        o = import_part(path)
        if name == 'wing':
            left, right = split_x(o)
            for side, obj in (('wing_l', left), ('wing_r', right)):
                obj.name = side
                c, h = to_centre(obj)
                objs.append((side, obj, mass / 2, c, h))
            continue
        o.name = name
        c, h = to_centre(o)
        objs.append((name, o, mass, c, h))
    mat = charred()
    for _, o, _, _, _ in objs:
        o.data.materials.clear()
        o.data.materials.append(mat)
        o.hide_render = True
    return objs


def scene_for(cause, objs):
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.name.startswith(('G_', 'S_', 'V_', 'W_', 'Cam', 'Sun')):
            bpy.data.objects.remove(o, do_unlink=True)
    layout = [(n, tuple(max(0.05, x) for x in h), m, c) for n, o, m, c, h in objs]
    pieces = wreck.simulate(wreck.start(cause, layout), 3.2, wreck.planes_for(cause))
    window = {'parede': 3.0, 'lado': 2.2, 'traseira': 2.0, 'aterragem': 2.2, 'desgaste': 2.2}[cause]
    sand = texture_mat('G_Sand', 'SourceArt/Desert/T_Sand_D.png', 0.08, (1.0, 0.8, 0.62, 1))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    g = bpy.context.object
    g.name = 'G_Ground'
    g.scale = (900, 300, 1)
    g.data.materials.append(sand)
    if wreck.CAUSES[cause].get('wall'):
        rock = texture_mat('G_Rock', 'SourceArt/Desert/T_Rock_D.png', 0.05, (0.95, 0.55, 0.38, 1))
        bpy.ops.mesh.primitive_cube_add(location=(1.0 + 6.0, 0, 9.0))
        w = bpy.context.object
        w.name = 'G_Wall'
        w.scale = (6.0, 34.0, 9.0)
        w.data.materials.append(rock)
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 4.0
    sun.angle = math.radians(1.5)
    so = bpy.data.objects.new('Sun', sun)
    sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(55), 0, math.radians(35))
    w = bpy.data.worlds.new('W')
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.62, 0.78, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 40
    sc.cycles.use_denoising = True
    sc.cycles.volume_step_rate = 3.0
    sc.cycles.volume_biased = True        # ray-marched: the unbiased volumes build an octree of every noise first (10x slower)
    sc.render.resolution_x, sc.render.resolution_y = 1600, 800
    sc.view_settings.view_transform = 'AgX'
    hero_t = {'parede': 0.55, 'lado': 0.45, 'traseira': 0.5, 'aterragem': 0.5, 'desgaste': 0.45}[cause]
    p0 = pieces[0].track[0][1]

    def place(t, alpha, tag, pieces_only=None):
        out = []
        for piece, (name, obj, _, _, _) in zip(pieces, objs):
            idx = min(int(t / wreck.DT), len(piece.track) - 1)
            _, p, q = piece.track[idx]
            ghost = obj.copy()
            ghost.name = 'S_%s_%s' % (name, tag)
            ghost.hide_render = False
            ghost.location = Vector(p)
            ghost.rotation_mode = 'QUATERNION'
            ghost.rotation_quaternion = Quaternion((q[0], q[1], q[2], q[3]))
            ghost['alpha'] = alpha
            ghost['heat'] = max(0.15, 1.0 - t / 2.5)
            sc.collection.objects.link(ghost)
            out.append(p)
        return out

    def clear(prefix):
        for o in list(sc.objects):
            if o.name.startswith(prefix):
                bpy.data.objects.remove(o, do_unlink=True)

    speed = wreck.CAUSES[cause]['kmh'] / 3.6

    def blast(t_now):
        # several lumps of fire where it died, swelling, carried on a little by the ship's speed (not into a wall) and
        # rising, cooling into dark smoke; smoke above; dust where pieces hit before now
        grow = min(1.0, 0.45 + t_now * 1.4)
        heat = 16.0 * math.exp(-3.5 * t_now)          # out by ~1.5 s: only smoke is left
        drift = 0.0 if wreck.CAUSES[cause].get('wall') else speed * 0.22 * (1.0 - math.exp(-3.0 * t_now)) / 3.0
        rise = 2.5 * t_now
        for k, (dx, dy, dz, r) in enumerate(((3.0, 0.0, 2.6, 7.5), (7.0, 2.5, 3.6, 5.5), (5.0, -3.0, 1.8, 5.0), (9.5, 0.5, 5.5, 4.2))):
            volume('V_Fire%d' % k, (p0[0] + dx + drift, p0[1] + dy, p0[2] + dz + rise), r * grow, 7.5, heat, 2.4 + 0.3 * k)
        volume('V_Smoke', (p0[0] + 8.0 + drift, p0[1], p0[2] + 12.0 * grow + rise), (11.0 + 4.0 * t_now) * grow, 2.0, 0.0, 1.7,
               smoke=True)
        hits = sorted([h for pc in pieces for h in pc.hits if h[0] <= t_now], key=lambda h: -h[2])[:6]
        for k, (t, c, vn) in enumerate(hits):
            dust = volume('V_Dust%d' % k, (c[0], c[1], 1.0), 1.8 + vn * 0.07, 1.4, 0.0, 2.2, smoke=True)
            dust.data.materials[0].node_tree.nodes['Principled Volume'].inputs['Color'].default_value = (0.6, 0.42, 0.27, 1)

    # A filmstrip: six moments, the camera riding beside the hull (a little ahead, so the blast shows behind it), a faint
    # trail of where the pieces were just before; then one sheet per cause.
    moments = [0.08, 0.35, 0.7, 1.1, 1.6, 2.3]
    offset = Vector((-15.0, -15.0, 6.0)) if cause == 'parede' else Vector((9.0, -19.0, 5.5))
    sc.render.resolution_x, sc.render.resolution_y = 640, 360
    sc.cycles.samples = 32
    frames = []
    for k, t in enumerate(moments):
        for j, tt in enumerate((t - 0.15, t - 0.1, t - 0.05)):
            if tt > 0:
                place(float(tt), 0.12 + 0.08 * j, 'trail%d' % j)
        now = place(t, 1.0, 'now')
        blast(t)
        hull = Vector(now[0])
        cd = bpy.data.cameras.new('Cam')
        cd.lens = 30
        cam = bpy.data.objects.new('Cam', cd)
        sc.collection.objects.link(cam)
        cam.location = Vector((hull.x, hull.y, max(hull.z, 1.0))) + offset
        look = Vector((hull.x - (4.0 if cause != 'parede' else -2.0), hull.y, max(1.2, hull.z * 0.8)))
        cam.rotation_euler = (look - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.camera = cam
        path = os.path.join(OUT, '_%s_%d.png' % (cause, k))
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        frames.append((t, path))
        clear('S_')
        clear('V_')
        bpy.data.objects.remove(cam, do_unlink=True)
    sheet(cause, frames)
    print('WRECK', cause)


def sheet(cause, frames):
    from PIL import Image, ImageDraw, ImageFont
    font_dir = os.path.join(ROOT, 'Content', 'UI', 'Fonts')
    big = ImageFont.truetype(os.path.join(font_dir, 'Orbitron-Black.ttf'), 30)
    small = ImageFont.truetype(os.path.join(font_dir, 'Inter-ExtraBold.otf'), 22)
    W, H = 640, 360
    img = Image.new('RGB', (W * 3, H * 2 + 60), (8, 18, 38))
    d = ImageDraw.Draw(img)
    d.text((20, 14), wreck.CAUSES[cause]['title'].upper(), font=big, fill=(238, 245, 255))
    for k, (t, path) in enumerate(frames):
        tile = Image.open(path).convert('RGB')
        x, y = (k % 3) * W, 60 + (k // 3) * H
        img.paste(tile, (x, y))
        d.rectangle([x + 10, y + 10, x + 110, y + 44], fill=(3, 8, 20))
        d.text((x + 20, y + 13), ('%.2f s' % t).replace('.', ','), font=small, fill=(150, 225, 255))
        os.remove(path)
    img.save(os.path.join(OUT, 'wreck_%s.jpg' % cause), quality=88)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    parts = build_parts()
    for cause in CAUSES:
        scene_for(cause, parts)
