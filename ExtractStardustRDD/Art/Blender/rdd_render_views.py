"""
EXTRACT: STARDUST — RED DUST DIVIDE · fotografias da pista no Blender (sem o Unity).

  blender -b --factory-startup -P rdd_render_views.py -- <spec.json> <pasta_export> <pasta_fotos> [nome1,nome2,...]

Importa a geometria gerada (todos os setores), reconstrói o aspeto da geologia a partir das cores dos vértices
(classe + paleta das camadas, como o shader do jogo), põe sol, céu e bruma atmosférica e fotografa vistas do jogador:
perseguição (câmera baixa atrás da nave), paisagens e vistas aéreas. Câmeras calculadas a partir do eixo do percurso.
"""
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rdd_geology as geo  # noqa: E402
from rdd_route_lib import integrate, frames  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:]
SPEC, EXPORT, OUT = (os.path.abspath(a) for a in ARGS[:3])
ONLY = set(ARGS[3].split(',')) if len(ARGS) > 3 and ARGS[3] else None
os.makedirs(OUT, exist_ok=True)
T0 = time.time()


def log(m):
    print(f"[fotos {time.time() - T0:6.1f}s] {m}", flush=True)


# ---------------------------------------------------------------- vistas (segmento, fração, modo, parâmetros)
VIEWS = [
    ("01_largada_grelha", dict(seg="1 Bacia · grelha", f=0.3, mode="chase")),
    ("02_bacia_slickrock", dict(seg="1 Bacia · ondulações", f=0.5, mode="vista", yaw=35, h=7, pitch=-2)),
    ("03_bacia_esses", dict(seg="1 Esses da bacia esquerda", f=0.2, mode="chase")),
    ("04_bacia_flow_jump", dict(seg="1 Laje 2 crista", f=0.7, mode="chase")),
    ("05_mesa_rocha_caida", dict(seg="2 Lajes · degraus", f=0.35, mode="chase")),
    ("06_mesa_bifurcacao_aerea", dict(seg="2 Lajes partidas · subida", f=0.4, mode="aerial", up=260, back=420, side=-260, look=900)),
    ("07_topo_da_mesa", dict(seg="2 Borda do Shafer", f=0.6, mode="vista", yaw=55, h=8, pitch=-5)),
    ("08_shafer_vista_da_borda", dict(seg="3 Borda · início", f=0.4, mode="vista", yaw=0, h=12, pitch=-16, lens=20)),
    ("09_shafer_ganchos_aerea", dict(seg="3 Perna 6", f=0.5, mode="aerial", up=480, back=650, side=420, look=0)),
    ("10_shafer_gancho", dict(seg="3 Gancho 7", f=0.1, mode="chase")),
    ("11_red_wall_gargalo", dict(seg="4 Gargalo", f=0.45, mode="chase")),
    ("12_canyon_das_agulhas", dict(seg="4 Canyon das agulhas", f=0.25, mode="chase")),
    ("13_red_wall_25", dict(seg="4 Red Wall · 25°", f=0.5, mode="chase", roll=0.4)),
    ("14_red_wall_50", dict(seg="4 Red Wall · 50°", f=0.45, mode="chase", roll=0.4)),
    ("15_red_wall_aerea", dict(seg="4 Red Wall · 35°", f=0.5, mode="aerial", up=380, back=520, side=-460, look=200)),
    ("16_canyon_jump", dict(seg="4 Canyon jump borda", f=0.0, mode="chase", back=34)),
    ("17_ferradura_aerea", dict(seg="5 Ferradura 270°", f=0.5, mode="aerial", up=1100, back=-200, side=-850, look=0, lens=20)),
    ("18_ferradura_fundo", dict(seg="5 Ferradura 270°", f=0.28, mode="chase")),
    ("19_wash_halfpipe", dict(seg="6 Meandro 2", f=0.45, mode="chase")),
    ("20_wash_destroco", dict(seg="6 Meandro 5", f=0.06, mode="chase")),
    ("21_wash_cotovelo", dict(seg="6 Cotovelo 4", f=0.3, mode="chase")),
    ("22_arches_subida_vista", dict(seg="7 Subida do desfiladeiro 2", f=0.75, mode="vista", yaw=180, h=9, pitch=-6)),
    ("23_arches_corredor_arco", dict(seg="7 Corredor de fins 1", f=0.22, mode="chase")),
    ("24_arches_slalom", dict(seg="7 Slalom de agulhas", f=0.32, mode="chase")),
    ("25_rocha_equilibrada", dict(seg="7 Planície da rocha equilibrada", f=0.5, mode="vista", yaw=-35, h=6, pitch=0)),
    ("26_hollow_boca", dict(seg="8 Boca da caverna", f=0.25, mode="chase")),
    ("27_hollow_camara", dict(seg="8 Caverna · câmara", f=0.25, mode="chase", cave=True)),
    ("28_hollow_saida", dict(seg="8 Caverna · rampa de saída", f=0.1, mode="chase", cave=True)),
    ("29_white_rim_garganta", dict(seg="9 White Rim", f=0.75, mode="vista", yaw=80, h=8, pitch=-5)),
    ("30_white_rim_curva", dict(seg="9 Curva larga", f=0.5, mode="chase")),
    ("31_hero_jump", dict(seg="9 Hero jump borda", f=0.0, mode="chase", back=40)),
    ("32_extracao_aerea", dict(seg="9 Reta final", f=0.6, mode="aerial", up=320, back=650, side=260, look=0)),
    ("33_bacia_aerea", dict(seg="1 Bacia · grelha", f=0.3, mode="aerial", up=350, back=500, side=150, look=300)),
]


# ---------------------------------------------------------------- cena
def srgb_to_linear(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def geology_material():
    m = bpy.data.materials.new("GeologyPhoto")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial')
    bsdf = N.new('ShaderNodeBsdfPrincipled')
    L.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    col = N.new('ShaderNodeVertexColor')
    col.layer_name = 'Col'
    sep = N.new('ShaderNodeSeparateColor')
    L.new(col.outputs['Color'], sep.inputs['Color'])
    pal = srgb_to_linear(geo.PALETTE)

    def ramp(src):
        r = N.new('ShaderNodeValToRGB')
        r.color_ramp.interpolation = 'CONSTANT'
        els = r.color_ramp.elements
        els[0].position = 0.0
        els[0].color = (*pal[0], 1.0)
        els[1].position = 0.5 / 15.0
        els[1].color = (*pal[1], 1.0)
        for i in range(2, len(pal)):
            e = els.new((i - 0.5) / 15.0)
            e.color = (*pal[i], 1.0)
        L.new(src, r.inputs['Fac'])
        return r

    ra, rb = ramp(sep.outputs['Green']), ramp(sep.outputs['Blue'])
    uv2 = N.new('ShaderNodeUVMap')
    uv2.uv_map = 'UV2'
    sxyz = N.new('ShaderNodeSeparateXYZ')
    L.new(uv2.outputs['UV'], sxyz.inputs['Vector'])
    mix = N.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    L.new(sxyz.outputs['Y'], mix.inputs['Factor'])
    L.new(ra.outputs['Color'], mix.inputs[6])
    L.new(rb.outputs['Color'], mix.inputs[7])
    # variação natural: manchas grandes + estratos finos (bandas horizontais pela altura)
    geo_n = N.new('ShaderNodeNewGeometry')
    big = N.new('ShaderNodeTexNoise')
    big.inputs['Scale'].default_value = 0.012
    big.inputs['Detail'].default_value = 3.0
    L.new(geo_n.outputs['Position'], big.inputs['Vector'])
    bands = N.new('ShaderNodeTexWave')
    bands.wave_type = 'BANDS'
    bands.bands_direction = 'Z'
    bands.inputs['Scale'].default_value = 0.35
    bands.inputs['Distortion'].default_value = 3.0
    bands.inputs['Detail'].default_value = 2.0
    L.new(geo_n.outputs['Position'], bands.inputs['Vector'])
    rock = N.new('ShaderNodeMath')                      # classe ≥ 0,5 = rocha (estratos), < 0,5 = leito
    rock.operation = 'GREATER_THAN'
    rock.inputs[1].default_value = 0.45
    L.new(sep.outputs['Red'], rock.inputs[0])
    bmul = N.new('ShaderNodeMapRange')
    bmul.inputs['To Min'].default_value = 0.86
    bmul.inputs['To Max'].default_value = 1.08
    L.new(bands.outputs['Fac'], bmul.inputs['Value'])
    bsel = N.new('ShaderNodeMix')
    bsel.data_type = 'FLOAT'
    L.new(rock.outputs['Value'], bsel.inputs['Factor'])
    bsel.inputs[2].default_value = 1.0
    L.new(bmul.outputs['Result'], bsel.inputs[3])
    vmul = N.new('ShaderNodeMapRange')
    vmul.inputs['To Min'].default_value = 0.82
    vmul.inputs['To Max'].default_value = 1.15
    L.new(big.outputs['Fac'], vmul.inputs['Value'])
    m1 = N.new('ShaderNodeVectorMath')
    m1.operation = 'SCALE'
    L.new(mix.outputs[2], m1.inputs[0])
    L.new(vmul.outputs['Result'], m1.inputs['Scale'])
    m2 = N.new('ShaderNodeVectorMath')
    m2.operation = 'SCALE'
    L.new(m1.outputs['Vector'], m2.inputs[0])
    L.new(bsel.outputs[0], m2.inputs['Scale'])
    L.new(m2.outputs['Vector'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.92
    # relevo fino (grão e pequenas fraturas)
    fine = N.new('ShaderNodeTexNoise')
    fine.inputs['Scale'].default_value = 0.9
    fine.inputs['Detail'].default_value = 6.0
    L.new(geo_n.outputs['Position'], fine.inputs['Vector'])
    bump = N.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.25
    bump.inputs['Distance'].default_value = 0.3
    L.new(fine.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    add_haze(nt, bsdf, out)
    return m


HAZE = (0.66, 0.68, 0.76)


def add_haze(nt, bsdf, out):
    """Perspetiva atmosférica: mistura com a cor do ar pela distância à câmera (1 - e^(-d·k))."""
    N, L = nt.nodes, nt.links
    camd = N.new('ShaderNodeCameraData')
    k = N.new('ShaderNodeMath')
    k.operation = 'MULTIPLY'
    k.inputs[1].default_value = -0.00005
    L.new(camd.outputs['View Distance'], k.inputs[0])
    e = N.new('ShaderNodeMath')
    e.operation = 'EXPONENT'
    L.new(k.outputs['Value'], e.inputs[0])
    f = N.new('ShaderNodeMath')
    f.operation = 'SUBTRACT'
    f.inputs[0].default_value = 0.92
    L.new(e.outputs['Value'], f.inputs[1])
    clamp = N.new('ShaderNodeClamp')
    L.new(f.outputs['Value'], clamp.inputs['Value'])
    em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*HAZE, 1.0)
    em.inputs['Strength'].default_value = 1.0
    mixs = N.new('ShaderNodeMixShader')
    L.new(clamp.outputs['Result'], mixs.inputs['Fac'])
    L.new(bsdf.outputs['BSDF'], mixs.inputs[1])
    L.new(em.outputs['Emission'], mixs.inputs[2])
    L.new(mixs.outputs['Shader'], out.inputs['Surface'])


def metal_material():
    m = bpy.data.materials.new("WreckPhoto")
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.13, 0.075, 0.045, 1.0)
    b.inputs['Metallic'].default_value = 0.6
    b.inputs['Roughness'].default_value = 0.5
    add_haze(m.node_tree, b, m.node_tree.nodes['Material Output'])
    return m


def setup_scene():
    sc = bpy.context.scene
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 90
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Punchy'
    except Exception:
        pass
    ee = sc.eevee
    for attr, val in (('taa_render_samples', 48), ('volumetric_end', 26000.0), ('volumetric_tile_size', '8'),
                      ('volumetric_samples', 48), ('use_shadows', True), ('use_volumetric_shadows', False),
                      ('shadow_ray_count', 2), ('use_gtao', True), ('gtao_distance', 2.0)):
        try:
            setattr(ee, attr, val)
        except Exception:
            pass
    # céu + sol
    world = bpy.data.worlds.new("Deserto")
    sc.world = world
    world.use_nodes = True
    wn, wl = world.node_tree.nodes, world.node_tree.links
    bg = wn['Background']
    sky = wn.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE'):
        try:
            sky.sky_type = t
            break
        except TypeError:
            continue
    for attr, val in (('sun_elevation', math.radians(26.0)), ('sun_rotation', math.radians(210.0)), ('altitude', 1200.0),
                      ('air_density', 1.0), ('dust_density', 2.5), ('sun_intensity', 0.5)):
        try:
            setattr(sky, attr, val)
        except Exception:
            pass
    wl.new(sky.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.22
    sun = bpy.data.lights.new("Sol", 'SUN')
    sun.energy = 3.6
    sun.angle = math.radians(0.6)
    sun.color = (1.0, 0.93, 0.84)
    so = bpy.data.objects.new("Sol", sun)
    sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(90 - 26.0), 0.0, math.radians(210.0))
    return sc


def ship(sc):
    """Nave provisória (cunha vermelha, nacelas e escapes acesos) para dar escala às fotos de perseguição."""
    paint = bpy.data.materials.new("Pintura")
    paint.use_nodes = True
    p = paint.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.5, 0.025, 0.02, 1.0)
    p.inputs['Metallic'].default_value = 0.3
    p.inputs['Roughness'].default_value = 0.35
    dark = bpy.data.materials.new("Metal")
    dark.use_nodes = True
    dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.02, 0.025, 1.0)
    glow = bpy.data.materials.new("Escape")
    glow.use_nodes = True
    g = glow.node_tree.nodes['Principled BSDF']
    g.inputs['Emission Color'].default_value = (1.0, 0.45, 0.12, 1.0)
    g.inputs['Emission Strength'].default_value = 40.0
    root = bpy.data.objects.new("Nave", None)
    sc.collection.objects.link(root)

    def part(name, mesh_fn, mat, loc, scale, rot=(0, 0, 0)):
        mesh_fn()
        ob = bpy.context.active_object
        ob.name = name
        ob.location = loc
        ob.scale = scale
        ob.rotation_euler = rot
        ob.data.materials.append(mat)
        ob.parent = root
        bpy.ops.object.shade_smooth()
        return ob

    part("Casco", lambda: bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8), paint, (0, 0.2, 0), (1.45, 3.4, 0.42))
    for s in (-1, 1):
        part("Nacela", lambda: bpy.ops.mesh.primitive_cylinder_add(vertices=14), dark, (1.35 * s, -1.6, 0.02), (0.42, 0.42, 1.9), (math.radians(90), 0, 0))
        part("Escape", lambda: bpy.ops.mesh.primitive_circle_add(vertices=14, fill_type='NGON'), glow, (1.35 * s, -3.52, 0.02), (0.3, 0.3, 0.3), (math.radians(90), 0, 0))
    part("Cockpit", lambda: bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6), dark, (0, 0.9, 0.3), (0.5, 1.1, 0.28))
    return root


# ---------------------------------------------------------------- importação
def import_all(sc):
    geo_mat, metal = geology_material(), metal_material()
    files = sorted(f for f in os.listdir(EXPORT) if f.endswith('.fbx') and f != 'axis_test.fbx')
    for f in files:
        t = time.time()
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(EXPORT, f), colors_type='LINEAR')
        new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
        for o in new:
            o.data.materials.clear()
            o.data.materials.append(metal if o.name.startswith('GEO_Wreck') else geo_mat)
        log(f"importado {f}: {len(new)} objetos em {time.time() - t:.1f}s")


def unity_to_blender_matrix():
    """Descobre a conversão Unity → mundo do Blender com o teste de eixos (vértices conhecidos em coordenadas Unity)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(EXPORT, 'axis_test.fbx'))
    ob = next(o for o in bpy.data.objects if o not in before and o.type == 'MESH')
    pts = np.array([ob.matrix_world @ v.co for v in ob.data.vertices])
    U = np.array([[1, 2, 3], [11, 2, 3], [1, 2, 13], [11, 12, 13]], float)
    best = None
    import itertools
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            M = np.zeros((3, 3))
            for row in range(3):
                M[row, perm[row]] = signs[row]
            mapped = U @ M.T
            err = sum(min(np.linalg.norm(pts - m, axis=1)) for m in mapped)
            if best is None or err < best[0]:
                best = (err, M)
    bpy.data.objects.remove(ob, do_unlink=True)
    log(f"conversão Unity→Blender: {best[1].tolist()} (erro {best[0]:.3f})")
    return best[1]


# ---------------------------------------------------------------- câmeras
def main():
    import json
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = setup_scene()
    spec = json.load(open(SPEC, encoding='utf-8'))
    rows, step = integrate(spec)
    P, T, R, U = frames(rows)
    dist = np.array([r['dist'] for r in rows])
    seg_start, seg_len = {}, {}
    acc = 0.0
    for sgm in spec['segments']:
        seg_start[sgm['id']] = acc
        seg_len[sgm['id']] = float(sgm['len'])
        acc += float(sgm['len'])
    M = unity_to_blender_matrix()

    def B(v):
        return Vector((M @ np.asarray(v, float)).tolist())

    import_all(sc)
    nave = ship(sc)
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.clip_start, cam_data.clip_end = 0.3, 60000.0
    cam = bpy.data.objects.new("Camera", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cave_lights = []

    def station(seg_prefix, f, extra=0.0):
        sid = next(k for k in seg_start if k.startswith(seg_prefix))
        d = seg_start[sid] + seg_len[sid] * f + extra
        return int(np.clip(np.searchsorted(dist, d), 1, len(dist) - 2))

    def look_at(pos, target, up):
        fwd = (target - pos).normalized()
        right = fwd.cross(up).normalized()
        upv = right.cross(fwd).normalized()
        rot = Matrix((right, upv, -fwd)).transposed()
        cam.matrix_world = Matrix.Translation(pos) @ rot.to_4x4()

    # 1) câmeras de todas as vistas pedidas (antes de renderizar)
    shots = []
    for name, v in VIEWS:
        if ONLY and name not in ONLY:
            continue
        i = station(v['seg'], v['f'])
        p, t, r, u = (B(a) for a in (P[i], T[i], R[i], U[i]))
        world_up = B([0.0, 1.0, 0.0])
        ship_m = None
        if v['mode'] == 'chase':
            back = v.get('back', 0.0)
            j = int(np.clip(np.searchsorted(dist, dist[i] - back), 1, len(dist) - 2))
            p, t, r, u = (B(a) for a in (P[j], T[j], R[j], U[j]))
            up_mix = (world_up * (1 - v.get('roll', 0.0)) + u * v.get('roll', 0.0)).normalized()
            craft = p + u * 1.7
            fwd = t.normalized()
            right = fwd.cross(u).normalized()
            ship_m = Matrix.Translation(craft) @ Matrix((right, fwd, u)).transposed().to_4x4()
            k = int(np.clip(np.searchsorted(dist, dist[j] + 45.0), 1, len(dist) - 2))
            target = B(P[k]) + B(U[k]) * 1.5
            pos = craft - fwd * 7.2 + up_mix * 2.4
            up = up_mix
        elif v['mode'] == 'vista':
            yaw = math.radians(v.get('yaw', 0.0))
            fwd = (t * math.cos(yaw) + r * math.sin(yaw)).normalized()
            pos = p + world_up * v.get('h', 6.0)
            pitch = math.radians(v.get('pitch', 0.0))
            target = pos + fwd * 100.0 + world_up * (100.0 * math.tan(pitch))
            up = world_up
        else:
            k = int(np.clip(np.searchsorted(dist, dist[i] + v.get('look', 0.0)), 1, len(dist) - 2))
            target = B(P[k])
            pos = p - t * v.get('back', 400.0) + r * v.get('side', 0.0) + world_up * v.get('up', 300.0)
            up = world_up
        shots.append(dict(name=name, v=v, i=i, pos=pos, target=target, up=up, ship=ship_m))
    if not shots:
        return

    # 2) a placa gráfica só tem 4 GB: tirar a geometria longe destas câmeras (o terreno grosso fica para o horizonte)
    cams = [sh['pos'] for sh in shots]
    removed = 0
    for ob in list(bpy.data.objects):
        if ob.type != 'MESH' or ob.parent is not None and ob.parent.name == "Nave":
            continue
        if ob.name.startswith('GEO_Terrain') and (ob.name.endswith('_64m') or ob.name.endswith('_24m')):
            continue
        c = ob.matrix_world @ (sum((Vector(b) for b in ob.bound_box), Vector()) / 8.0)
        if min((c - q).length for q in cams) > 9000.0:
            bpy.data.objects.remove(ob, do_unlink=True)
            removed += 1
    log(f"geometria longe das câmeras retirada: {removed} objetos")

    # 3) renderizar
    for sh in shots:
        v = sh['v']
        cam_data.lens = v.get('lens', 18.0)
        for lo in cave_lights:
            bpy.data.objects.remove(lo, do_unlink=True)
        cave_lights.clear()
        nave.hide_render = sh['ship'] is None
        if sh['ship'] is not None:
            nave.matrix_world = sh['ship']
        look_at(sh['pos'], sh['target'], sh['up'])
        if v.get('cave'):
            # luzes da nave e fissuras de luz no teto (a caverna não tem sol)
            for kk in range(-2, 8):
                q = int(np.clip(sh['i'] + kk * int(25 / step), 1, len(dist) - 2))
                ld = bpy.data.lights.new(f"Fissura{kk}", 'POINT')
                ld.energy = 2.5e5
                ld.color = (1.0, 0.78, 0.55)
                ld.shadow_soft_size = 3.0
                lo = bpy.data.objects.new(f"Fissura{kk}", ld)
                lo.location = B(P[q]) + B(U[q]) * 16.0
                sc.collection.objects.link(lo)
                cave_lights.append(lo)
        sc.render.filepath = os.path.join(OUT, sh['name'] + '.jpg')
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        log(f"{sh['name']}: {time.time() - t0:.1f}s")


main()
