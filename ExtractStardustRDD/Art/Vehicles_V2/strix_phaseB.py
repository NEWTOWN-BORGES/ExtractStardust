"""
EXTRACT: STARDUST — Naves V2 · STRIX (A · WEDGE aprovada) · Fase B: greybox de engenharia, construída de dentro para fora.
  blender -b --factory-startup -P strix_phaseB.py -- <pasta_renders> <ficheiro.blend>

Ordem (Bíblia §2 / Prompt §2): crash structure → célula do cockpit → espinha (rails + travessas) → reator e frame →
suportes do motor e frame de propulsão → hover → refrigeração → sockets (rail + grampo + conector) → cablagens/tubos →
painéis em chapa separados (com folgas e dobradiças) → estabilizadores com raiz estrutural.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
__name__ = 'v2_lib'
exec(compile(open(os.path.join(HERE, 'strix_phaseA.py'), encoding='utf-8').read(), 'strix_phaseA.py', 'exec'), globals())
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402

M_MECH = material('V2_Mechanical', (0.50, 0.51, 0.53))
M_CABLE = material('V2_Harness', (0.10, 0.10, 0.11))
M_COOL = material('V2_CoolantPipe', (0.30, 0.42, 0.56))
M_SOCK = material('V2_Socket', (0.95, 0.50, 0.14))
M_CORE = material('V2_ReactorCore', (0.98, 0.84, 0.52))
GROUPS, EXPLODE, SOCKETS = {}, {}, {}


def group(name):
    global COLL
    COLL = bpy.data.collections.new(name)
    SC.collection.children.link(COLL)
    GROUPS[name] = COLL
    return COLL


def tube(name, a, b, r, mat, sides=8):
    a, b = np.array(a, float), np.array(b, float)
    d = (b - a) / np.linalg.norm(b - a)
    up = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(d, up); u /= np.linalg.norm(u)
    v = np.cross(u, d)
    angs = np.linspace(0, 2 * math.pi, sides, endpoint=False) + math.pi / sides
    ring = lambda c: [tuple(c + (u * math.cos(t) + v * math.sin(t)) * r) for t in angs]
    return loft(name, [ring(a), ring(b)], mat, bevel=r * 0.2)


def pipe(name, pts, r, mat, clamps=False):
    """Tubo/cablagem com origem e destino: segmentos + juntas; grampos estruturais opcionais."""
    pts = [np.array(p, float) for p in pts]
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        tube(f"{name}_{i}", a, b, r, mat)
        if i:
            box(f"{name}_J{i}", a, (r * 2.2, r * 2.2, r * 2.2), mat, bevel=r * 0.5)
        if clamps:
            box(f"{name}_Clamp{i}", (a + b) / 2, (r * 3.2, r * 3.2, r * 3.2), M_STRUCT, bevel=r * 0.4)


def harness(name, pts, n=3, r=0.011, spread=0.026):
    """Feixe de cabos agrupados (3 condutores) com conectores nas pontas."""
    pts = [np.array(p, float) for p in pts]
    for k in range(n):
        off = np.array([0.0, 0.0, (k - (n - 1) / 2) * spread])
        pipe(f"{name}_C{k}", [p + off for p in pts], r, M_CABLE)
    box(name + '_ConnA', pts[0], (0.06, 0.05, 0.09), M_SOCK, bevel=0.008)
    box(name + '_ConnB', pts[-1], (0.06, 0.05, 0.09), M_SOCK, bevel=0.008)


def cage(name, x0, x1, y0, y1, z0, z1, r, mat):
    c = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    edges = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    for i, (a, b) in enumerate(edges):
        tube(f"{name}_{i}", c[a], c[b], r, mat)
    for i, p in enumerate(c):
        box(f"{name}_N{i}", p, (r * 2.6,) * 3, mat, bevel=r * 0.4)


def strip(name, secs, mat, thick=0.018):
    """Painel em chapa: superfície aberta com espessura (Solidify) — a carroceria é feita de painéis, não de um molde."""
    bm = bmesh.new()
    rings = [[bm.verts.new(Vector(p)) for p in s] for s in secs]
    for a, b in zip(rings, rings[1:]):
        for i in range(len(a) - 1):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    ob = finish(name, bm, mat, bevel=0.0)
    ob.modifiers.clear()
    so = ob.modifiers.new('Solidify', 'SOLIDIFY')
    so.thickness, so.offset = thick, -1.0
    be = ob.modifiers.new('Bevel', 'BEVEL')
    be.width, be.segments, be.limit_method = 0.004, 2, 'ANGLE'
    ob.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL').keep_sharp = True
    return ob


def lerp(a, b, t):
    return tuple(np.array(a) + (np.array(b) - np.array(a)) * t)


def socket(name, p, size, rail_axis='y'):
    """Socket físico: rail duplo + grampo de fecho rápido + conector de energia/dados; o Empty é o ponto do Unity."""
    p = np.array(p, float)
    off = np.array([0.06, 0, 0]) if rail_axis == 'y' else np.array([0, 0.06, 0])
    ln = np.array([0.02, size, 0.025]) if rail_axis == 'y' else np.array([size, 0.02, 0.025])
    for k in (-1, 1):
        box(f"{name}_Rail{k}", p + off * k, ln, M_STRUCT, bevel=0.004)
    box(name + '_Clamp', p + np.array([0, 0, 0.025]), (0.08, 0.06, 0.03), M_MECH, bevel=0.006)
    box(name + '_Connector', p + np.array([0, 0, 0.05]), (0.05, 0.04, 0.03), M_SOCK, bevel=0.006)
    e = bpy.data.objects.new(name, None)
    e.empty_display_type, e.empty_display_size = 'ARROWS', 0.25
    e.location = Vector(p)
    COLL.objects.link(e)
    SOCKETS[name] = tuple(p)


# ---------------------------------------------------------------- casco aprovado (A · WEDGE) como referência de envelope
BODY = dict(y=[3.10, 2.10, 0.70, -0.60, -1.50], hw=[0.12, 0.44, 0.70, 0.80, 0.80], hwb=[0.08, 0.34, 0.58, 0.68, 0.70],
            hwt=[0.05, 0.24, 0.40, 0.48, 0.50], zb=[0.31, 0.27, 0.26, 0.26, 0.27], zc=[0.33, 0.37, 0.43, 0.47, 0.48],
            zt=[0.35, 0.49, 0.65, 0.76, 0.78])


def B(k, y):
    return float(np.interp(y, BODY['y'][::-1], BODY[k][::-1]))


def sec(y):
    return hexsec(y, B('hw', y), B('hwb', y), B('hwt', y), B('zb', y), B('zc', y), B('zt', y))


def panels(prefix, y0, y1, top=True, sides=True, belly=True, n=8, explode=(0.0, 0.0, 0.0)):
    ys = np.linspace(y0, y1, n)
    S = [sec(y) for y in ys]
    made = []
    if top:
        made.append(strip(prefix + '_Top', [[lerp(s[2], s[1], 0.02), s[2], s[3], lerp(s[3], s[4], 0.02)] for s in S], M_BODY))
        EXPLODE[made[-1].name] = (explode[0], explode[1], explode[2] + 0.55)
    if sides:
        made.append(strip(prefix + '_SideR', [[lerp(s[0], s[1], 0.03), s[1], lerp(s[1], s[2], 0.94)] for s in S], M_BODY))
        EXPLODE[made[-1].name] = (explode[0] + 0.45, explode[1], explode[2] + 0.10)
        made.append(strip(prefix + '_SideL', [[lerp(s[4], s[3], 0.06), s[4], lerp(s[5], s[4], 0.03)] for s in S], M_BODY))
        EXPLODE[made[-1].name] = (explode[0] - 0.45, explode[1], explode[2] + 0.10)
    if belly:
        made.append(strip(prefix + '_Belly', [[lerp(s[5], s[0], 0.03), lerp(s[0], s[5], 0.03)] for s in S], M_STRUCT, thick=0.014))
        EXPLODE[made[-1].name] = (explode[0], explode[1], explode[2] - 0.30)
    return made


def build():
    # 1 crash structure + espinha estrutural (rails + travessas)
    group('1_Structure')
    for s in (1, -1):
        box(f"Spine_Rail_{'R' if s > 0 else 'L'}", (s * 0.27, -0.05, 0.36), (0.08, 5.70, 0.09), M_STRUCT, bevel=0.01)
        tube(f"Crash_Tube_{'R' if s > 0 else 'L'}", (s * 0.27, 2.75, 0.36), (s * 0.07, 3.02, 0.34), 0.03, M_STRUCT)
    box('Crash_HoneycombBox', (0.0, 2.80, 0.36), (0.30, 0.34, 0.10), M_MECH, bevel=0.01)
    for k in range(4):
        box(f"Crash_Cell{k}", (0.0, 2.66 + k * 0.09, 0.415), (0.28, 0.012, 0.012), M_STRUCT, bevel=0.0)
    for i, y in enumerate((2.40, 1.45, 0.98, -0.48, -1.05, -2.05, -2.95)):
        xw = 0.27 if y > -0.6 else 0.86
        tube(f"Crossmember_{i}", (-xw, y, 0.36), (xw, y, 0.36), 0.032, M_STRUCT)
    for s in (1, -1):     # braços de montagem: blindagem lateral, rail de cada bloco de propulsão, raiz dos estabilizadores
        sd = 'R' if s > 0 else 'L'
        tube(f"Armor_Outrigger_{sd}_F", (s * 0.27, 0.55, 0.36), (s * 0.72, 0.45, 0.42), 0.024, M_STRUCT)
        tube(f"Armor_Outrigger_{sd}_R", (s * 0.27, -0.30, 0.36), (s * 0.72, -0.25, 0.42), 0.024, M_STRUCT)
        box(f"PropMountRail_{sd}", (s * 0.56, -1.85, 0.30), (0.10, 1.75, 0.07), M_STRUCT, bevel=0.01)
        tube(f"Wing_RootStrut_{sd}", (s * 0.86, -2.05, 0.36), (s * 0.90, -2.15, 0.50), 0.026, M_STRUCT)
    for s in (1, -1):     # braços do frame traseiro de propulsão (dos rails para os blocos)
        tube(f"PropFrame_Arm_{'R' if s > 0 else 'L'}_F", (s * 0.27, -0.75, 0.36), (s * 0.86, -1.05, 0.36), 0.03, M_STRUCT)
        tube(f"PropFrame_Arm_{'R' if s > 0 else 'L'}_D", (s * 0.27, -2.05, 0.36), (s * 0.86, -2.95, 0.36), 0.026, M_STRUCT)

    # 2 célula de segurança do cockpit: floor pan, proteções laterais, arcos, assento, moldura e vidro do canopy
    group('2_CockpitCell')
    slab('Cell_FloorPan', [(-0.36, 0.96), (0.36, 0.96), (0.40, -0.46), (-0.40, -0.46)], 0.40, 0.43, M_STRUCT, bevel=0.006)
    for s in (1, -1):
        slab(f"Cell_SideProtection_{'R' if s > 0 else 'L'}", [(s * 0.40, 0.96), (s * 0.44, 0.96), (s * 0.46, -0.46), (s * 0.42, -0.46)], 0.43, 0.66, M_MECH, bevel=0.006)
    frame_pts = lambda y, h: [(0.40, y, 0.62), (0.22, y, h), (-0.22, y, h), (-0.40, y, 0.62)]
    for nm, y, h in (('Cell_FrontHoop', 0.96, 0.78), ('Cell_RollHoop', -0.46, 0.90)):
        pts = frame_pts(y, h)
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            tube(f"{nm}_{i}", a, b, 0.03, M_STRUCT)
    box('Cell_Seat', (0.0, -0.10, 0.52), (0.42, 0.62, 0.16), M_MECH, bevel=0.04)
    box('Cell_SeatBack', (0.0, -0.36, 0.66), (0.40, 0.10, 0.36), M_MECH, bevel=0.03)
    box('Cell_ControlYoke', (0.0, 0.52, 0.62), (0.26, 0.06, 0.08), M_MECH, bevel=0.01)
    cockpit_cut('Canopy_Glass', 0.95, -0.45, 0.34, 0.15, lambda y: B('zt', y))
    tube('Canopy_Hinge', (-0.24, 0.98, 0.70), (0.24, 0.98, 0.70), 0.022, M_MECH)
    for s in (1, -1):
        tube(f"Canopy_FrameRail_{'R' if s > 0 else 'L'}", (s * 0.30, 0.94, B('zt', 0.94)), (s * 0.30, -0.42, B('zt', -0.42)), 0.018, M_STRUCT)

    # 3 reator: gaiola estrutural + núcleo protegido (o glow só se vê pelas aberturas)
    group('3_Reactor')
    cage('Reactor_Frame', -0.24, 0.24, -1.05, -1.95, 0.40, 0.72, 0.022, M_STRUCT)
    loft('Reactor_Core', [hexsec(y, 0.17, 0.12, 0.12, 0.44, 0.56, 0.68) for y in (-1.15, -1.85)], M_CORE, bevel=0.01)
    for k, y in enumerate((-1.20, -1.50, -1.80)):
        box(f"Reactor_ShieldBand{k}", (0.0, y, 0.56), (0.40, 0.05, 0.30), M_MECH, bevel=0.01)

    # 4 propulsão: blocos segmentados (entrada | núcleo com painel de serviço | bocal), montados no frame
    group('4_Propulsion')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        x, z0, w, h = 0.56, 0.28, 0.62, 0.62
        zc = z0 + h * 0.5
        pod(f"Prop_{sd}_IntakeSection", (s * x, -0.70), (s * x, -1.08), (w * 0.70, w), (h * 0.55, h), (z0 + h * 0.42, zc), M_BODY, n=6, chamfer=0.08, top=0.60, rake=0.55, intake=False, nozzle=False)
        pod(f"Prop_{sd}_CoreSection", (s * x, -1.11), (s * x, -2.58), (w, w), (h, h), (zc, zc), M_BODY, n=4, chamfer=0.08, top=0.60, rake=0.0, intake=False, nozzle=False)
        pod(f"Prop_{sd}_NozzleSection", (s * x, -2.61), (s * x, -3.04), (w, w * 0.96), (h, h * 0.94), (zc, zc), M_MECH, n=4, chamfer=0.08, top=0.60, rake=0.0, intake=False, nozzle=True)
        for k, dz in enumerate((-0.12, 0.0, 0.12)):
            box(f"Prop_{sd}_NozzleVane{k}", (s * x, -3.07, zc + dz * h), (w * 0.74, 0.10, 0.025), M_STRUCT, bevel=0.004)
        box(f"Prop_{sd}_VectoringJoint", (s * x, -2.595, zc), (w * 1.05, 0.04, h * 1.02), M_STRUCT, bevel=0.006)
        # painel de serviço do núcleo com dobradiças (removível para manutenção)
        slab(f"Prop_{sd}_ServicePanel", [(s * (x - 0.17), -1.30), (s * (x + 0.17), -1.30), (s * (x + 0.17), -2.30), (s * (x - 0.17), -2.30)], z0 + h + 0.004, z0 + h + 0.024, M_BODY, bevel=0.004)
        EXPLODE[f"Prop_{sd}_ServicePanel"] = (s * 0.15, 0.0, 0.55)
        for k, yy in enumerate((-1.42, -2.18)):
            tube(f"Prop_{sd}_PanelHinge{k}", (s * (x - 0.18), yy - 0.06, z0 + h + 0.02), (s * (x - 0.18), yy + 0.06, z0 + h + 0.02), 0.014, M_MECH)
        # entrada lateral: lábio, conduta, separador de pó (malha) e lâminas
        scoop = pod(f"Prop_{sd}_SideScoop", (s * (x + w * 0.52), -0.95), (s * (x + w * 0.52), -1.80), (0.10, 0.22, 0.22), (0.18, h * 0.62, h * 0.60),
                    (z0 + h * 0.52, z0 + h * 0.55, z0 + h * 0.55), M_BODY, n=6, chamfer=0.2, top=0.8, rake=0.12, nozzle=False)
        for k in range(4):
            box(f"Prop_{sd}_DustMesh{k}", (s * (x + w * 0.52), -0.97, z0 + h * (0.36 + k * 0.08)), (0.16, 0.012, 0.008), M_STRUCT, bevel=0.0)
        # suportes do motor com isoladores de vibração
        for k, yy in enumerate((-1.05, -2.40)):
            box(f"Prop_{sd}_Mount{k}", (s * x, yy, z0 - 0.02), (w * 0.72, 0.09, 0.06), M_STRUCT, bevel=0.008)
            for q in (-1, 1):
                box(f"Prop_{sd}_Isolator{k}{q}", (s * x + q * w * 0.30, yy, z0 + 0.02), (0.07, 0.07, 0.05), M_CABLE, bevel=0.012)
    # módulo motor central (Socket_Engine) entre os blocos, baixo: deixa o espaço negativo por cima
    box('Engine_PowerConverter', (0.0, -2.30, 0.42), (0.34, 0.80, 0.22), M_MECH, bevel=0.03)

    # 5 hover: emissores com suporte e grelha de bobinas + sensores de superfície
    group('5_Hover')
    for k, (x, y, z) in enumerate(((0.30, 1.70, 0.27), (-0.30, 1.70, 0.27), (0.0, 0.10, 0.26), (0.56, -2.20, 0.28), (-0.56, -2.20, 0.28))):
        box(f"Hover_Bracket{k}", (x, y, z), (0.48, 0.66, 0.04), M_STRUCT, bevel=0.008)
        box(f"Hover_Emitter{k}", (x, y, z - 0.045), (0.40, 0.58, 0.05), M_HOVER, bevel=0.01)
        for q in range(4):
            box(f"Hover_Coil{k}_{q}", (x, y - 0.21 + q * 0.14, z - 0.073), (0.34, 0.05, 0.008), M_OPEN, bevel=0.0)
    for k, (x, y) in enumerate(((0.0, 3.00), (0.62, 0.40), (-0.62, 0.40), (0.86, -2.90), (-0.86, -2.90))):
        box(f"Hover_SurfaceSensor{k}", (x, y, 0.29), (0.07, 0.07, 0.04), M_SOCK, bevel=0.008)

    # 6 refrigeração: tomadas de ar no tejadilho → radiadores → tubos de refrigerante até ao reator
    group('6_Cooling')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        box(f"Cool_Radiator_{sd}", (s * 0.40, -0.78, 0.56), (0.16, 0.42, 0.26), M_MECH, bevel=0.01)
        for k in range(6):
            box(f"Cool_RadFin_{sd}{k}", (s * 0.40, -0.62 - k * 0.064, 0.56), (0.17, 0.012, 0.24), M_STRUCT, bevel=0.0)
        pipe(f"Cool_PipeFeed_{sd}", [(s * 0.40, -0.98, 0.50), (s * 0.30, -1.05, 0.50), (s * 0.24, -1.20, 0.50)], 0.022, M_COOL, clamps=True)
        pipe(f"Cool_PipeReturn_{sd}", [(s * 0.24, -1.80, 0.62), (s * 0.34, -1.10, 0.66), (s * 0.40, -0.98, 0.64)], 0.018, M_COOL)

    # 7 sockets dos módulos (Doc 02): rail + grampo + conector; os Empty dão o ponto de montagem no Unity
    group('7_Sockets')
    socket('Socket_Engine', (0.0, -2.30, 0.54), 0.6)
    socket('Socket_Propulsion_R', (0.56, -1.80, 0.27), 0.9)
    socket('Socket_Propulsion_L', (-0.56, -1.80, 0.27), 0.9)
    socket('Socket_Wing_R', (0.90, -2.15, 0.52), 0.6)
    socket('Socket_Wing_L', (-0.90, -2.15, 0.52), 0.6)
    socket('Socket_Tail', (0.0, -2.98, 0.50), 0.3, rail_axis='x')
    socket('Socket_Armor_R', (0.72, 0.10, 0.44), 0.9)
    socket('Socket_Armor_L', (-0.72, 0.10, 0.44), 0.9)
    socket('Socket_Cooling', (0.0, -0.78, 0.44), 0.4, rail_axis='x')
    socket('Socket_Reactor', (0.0, -1.50, 0.40), 0.7)
    socket('Socket_Utility', (0.0, 2.35, 0.44), 0.4)

    # 8 cablagens e tubos com origem e destino (reator → blocos; reator → cockpit; atuadores dos estabilizadores)
    group('8_Harness')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        harness(f"Harness_ReactorToProp_{sd}", [(s * 0.20, -1.95, 0.52), (s * 0.30, -2.05, 0.52), (s * 0.40, -2.10, 0.50), (s * 0.40, -2.30, 0.50)])
        pipe(f"Actuator_Stabilizer_{sd}", [(s * 0.86, -1.95, 0.46), (s * 1.02, -2.05, 0.50)], 0.016, M_MECH)
    harness('Harness_ReactorToCockpit', [(0.0, -1.05, 0.66), (0.0, -0.70, 0.66), (0.0, -0.48, 0.60)], n=2)

    # 9 carroceria: painéis em chapa separados (tejadilho, flancos, fundo) com folgas; portas de respiro com dobradiça
    group('9_Panels')
    panels('Panel_Nose', 3.06, 1.66, explode=(0.0, 0.55, 0.0))
    panels('Panel_FrontDeck', 1.62, 1.00, sides=False, belly=False, n=4)
    panels('Panel_Mid', 1.62, -0.42, top=False, n=8)
    panels('Panel_RearDeck', -0.46, -1.48, n=5, explode=(0.0, -0.25, 0.25))
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        slab(f"Panel_VentDoor_{sd}", [(s * 0.22, -0.62), (s * 0.46, -0.62), (s * 0.46, -0.94), (s * 0.22, -0.94)], 0.785, 0.80, M_BODY, bevel=0.004)
        EXPLODE[f"Panel_VentDoor_{sd}"] = (s * 0.2, 0.0, 0.85)
        tube(f"Panel_VentHinge_{sd}", (s * 0.22, -0.62, 0.80), (s * 0.46, -0.62, 0.80), 0.010, M_MECH)
    # estabilizadores com raiz estrutural (grampo + dobradiça), não penetram no casco
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        stab_blade(f"Stabilizer_{sd}", s, 0.86, 1.47, -1.60, 1.30, -1.85, 1.00, 0.52, 0.48, 0.20, 0.12)
        EXPLODE[f"Stabilizer_{sd}"] = (s * 0.55, 0.0, 0.0)
        EXPLODE[f"Stabilizer_{sd}_Endplate"] = (s * 0.55, 0.0, 0.0)
        box(f"Stabilizer_{sd}_RootClamp", (s * 0.88, -2.15, 0.52), (0.08, 0.70, 0.18), M_STRUCT, bevel=0.01)
        tube(f"Stabilizer_{sd}_Hinge", (s * 0.90, -1.75, 0.52), (s * 0.90, -2.55, 0.52), 0.02, M_MECH)


# ---------------------------------------------------------------- vistas de engenharia

def show(groups=None, hide_names=()):
    for n, c in GROUPS.items():
        c.hide_render = groups is not None and n not in groups
    for c in GROUPS.values():
        for ob in c.objects:
            ob.hide_render = any(ob.name.startswith(h) for h in hide_names) or c.hide_render


def explode(on):
    for name, off in EXPLODE.items():
        ob = bpy.data.objects.get(name)
        if ob is not None:
            ob.location = Vector(off) if on else Vector((0, 0, 0))
    for c in GROUPS.values():   # módulos/blocos também saem do sítio no explodido
        for ob in c.objects:
            if ob.name.startswith('Prop_') and ob.name not in EXPLODE:
                s = 1 if '_R_' in ob.name else -1
                ob.location = Vector((s * 0.35, 0.0, 0.12)) if on else Vector((0, 0, 0))
            if ob.name.startswith('Canopy_'):
                ob.location = Vector((0, 0.1, 0.75)) if on else Vector((0, 0, 0))


def main_b():
    setup_render()
    build()
    cams = dict(
        f34=(camera('Cam_F34', (5.6, 6.4, 2.9), look=(0.0, 0.0, 0.50), lens=50), 1600, 1000),
        r34=(camera('Cam_R34', (-5.2, -6.6, 3.2), look=(0.0, -0.8, 0.50), lens=50), 1600, 1000),
        top=(camera('Cam_Top', (0, 0, 20), rot=(0, 0, 90), ortho=7.0), 1400, 820),
        side=(camera('Cam_Side', (20, 0, 0.6), rot=(90, 0, 90), ortho=7.0), 1400, 480),
        under=(camera('Cam_Under', (3.8, 4.6, -2.6), look=(0.0, -0.2, 0.35), lens=45), 1400, 900),
    )
    shots = [
        ('assembled_f34', 'f34', None, (), False),
        ('assembled_r34', 'r34', None, (), False),
        ('exploded_f34', 'f34', None, (), True),
        ('cutaway_r34', 'r34', None, ('Panel_RearDeck', 'Panel_Mid_SideR', 'Prop_R_CoreSection', 'Prop_R_ServicePanel', 'Panel_VentDoor'), False),
        ('cutaway_top', 'top', None, ('Panel_', 'Prop_R_CoreSection', 'Prop_L_CoreSection', 'Prop_R_ServicePanel', 'Prop_L_ServicePanel', 'Canopy_Glass'), False),
        ('underside', 'under', None, (), False),
        ('socketmap_top', 'top', ['1_Structure', '7_Sockets', '3_Reactor'], (), False),
        ('side', 'side', None, (), False),
    ]
    labels = {}
    for name, cam_key, groups, hide, exploded in shots:
        cam, w, h = cams[cam_key]
        show(groups, hide)
        explode(exploded)
        render(os.path.join(OUT, f"STRIX_B_{name}.png"), cam, w, h)
        if name == 'socketmap_top':
            SC.render.resolution_x, SC.render.resolution_y = w, h
            for sname, p in SOCKETS.items():
                v = world_to_camera_view(SC, cam, Vector(p))
                labels[sname] = (v.x * w, (1 - v.y) * h)
    explode(False)
    show(None)
    json.dump(dict(labels=labels, size=list(cams['top'][1:])), open(os.path.join(OUT, 'strix_b_info.json'), 'w'), indent=1)
    counts = {n: len(c.objects) for n, c in GROUPS.items()}
    print('[STRIX B] peças por sistema:', counts, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


main_b()
