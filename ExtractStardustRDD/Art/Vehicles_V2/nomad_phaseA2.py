"""
EXTRACT: STARDUST — Naves V2 · NOMAD · Fase A (2.ª ronda): propostas com a CONSTRUÇÃO À VISTA (de dentro para fora).
  blender -b --factory-startup -P nomad_phaseA2.py -- <pasta_renders> <ficheiro.blend>

A 1.ª ronda (cascos lisos de um só molde) foi rejeitada. Aqui cada proposta mostra estrutura tubular, célula com
arcos, módulos presos com grampos/cintas, radiadores com condutas, tubos e cablagens com origem e destino, painéis em
chapa separados (com dobradiças) e emissores hover com suportes. Alvo ~7,4 x 3,3 x 1,45 m ("Dakar futurista").
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_MAIN = False
exec(compile(open(os.path.join(HERE, 'strix_phaseB.py'), encoding='utf-8').read(), 'strix_phaseB.py', 'exec'), globals())


def space_frame(prefix, st, r=0.032):
    """Chassis tubular: longarinas inferiores/superiores, travessas e diagonais entre estações (y, meia-largura, z0, z1)."""
    for s in (1, -1):
        for a, b in zip(st, st[1:]):
            tube(f"{prefix}_LowerRail_{s}_{a[0]}", (s * a[1], a[0], a[2]), (s * b[1], b[0], b[2]), r, M_STRUCT)
            tube(f"{prefix}_UpperRail_{s}_{a[0]}", (s * a[1] * 0.92, a[0], a[3]), (s * b[1] * 0.92, b[0], b[3]), r * 0.85, M_STRUCT)
            tube(f"{prefix}_Diagonal_{s}_{a[0]}", (s * a[1], a[0], a[2]), (s * b[1] * 0.92, b[0], b[3]), r * 0.7, M_STRUCT)
    for y, hw, z0, z1 in st:
        tube(f"{prefix}_Cross_{y}", (-hw, y, z0), (hw, y, z0), r * 0.9, M_STRUCT)
        tube(f"{prefix}_CrossTop_{y}", (-hw * 0.92, y, z1), (hw * 0.92, y, z1), r * 0.75, M_STRUCT)
        for s in (1, -1):
            tube(f"{prefix}_Post_{s}_{y}", (s * hw, y, z0), (s * hw * 0.92, y, z1), r * 0.8, M_STRUCT)
            box(f"{prefix}_Node_{s}_{y}", (s * hw, y, z0), (r * 2.6,) * 3, M_STRUCT, bevel=r * 0.4)


def hoop(prefix, y, hw, z0, z1, r=0.034):
    pts = [(hw, y, z0), (hw * 0.75, y, z1), (-hw * 0.75, y, z1), (-hw, y, z0)]
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        tube(f"{prefix}_{i}", a, b, r, M_STRUCT)


def radiator(prefix, c, size):
    """Radiador: núcleo com alhetas + moldura; refrigeração ligada ao reator por tubos."""
    c = np.array(c, float)
    box(prefix + '_Core', c, size, M_MECH, bevel=0.01)
    n = max(4, int(size[1] / 0.07))
    for k in range(n):
        box(f"{prefix}_Fin{k}", c + np.array([0, -size[1] / 2 + (k + 0.5) * size[1] / n, 0]), (size[0] * 1.06, 0.012, size[2] * 0.92), M_STRUCT, bevel=0.0)
    box(prefix + '_FrameTop', c + np.array([0, 0, size[2] / 2 + 0.02]), (size[0] + 0.06, size[1] + 0.06, 0.04), M_STRUCT, bevel=0.006)


def tank(prefix, c, w, l, h):
    """Tanque Aux/Fuel com cintas e válvula (módulo substituível)."""
    c = np.array(c, float)
    pod(prefix, (c[0], c[1] + l / 2), (c[0], c[1] - l / 2), (w * 0.8, w, w, w * 0.8), (h * 0.8, h, h, h * 0.8), (c[2],) * 4, M_BODY, n=8, chamfer=0.3,
        top=0.85, rake=0.04, intake=False, nozzle=False)
    for k, yy in enumerate(np.linspace(c[1] + l / 2 - 0.2, c[1] - l / 2 + 0.2, 3)):
        box(f"{prefix}_Strap{k}", (c[0], yy, c[2]), (w * 1.08, 0.06, h * 1.08), M_STRUCT, bevel=0.006)
    box(prefix + '_Valve', c + np.array([0, -l / 2 + 0.08, h / 2 + 0.03]), (0.08, 0.08, 0.06), M_SOCK, bevel=0.01)


def prop_unit(prefix, s, x, y0, y1, w, h, z0):
    """Bloco de propulsão segmentado (entrada | núcleo com painel de serviço | bocal com lâminas e junta de vectoring)."""
    sd = 'R' if s > 0 else 'L'
    zc = z0 + h * 0.5
    ya, yb = y0 - (y0 - y1) * 0.18, y0 - (y0 - y1) * 0.80
    pod(f"{prefix}_{sd}_Intake", (s * x, y0), (s * x, ya), (w * 0.72, w), (h * 0.56, h), (z0 + h * 0.42, zc), M_BODY, n=6, chamfer=0.08, top=0.60, rake=0.55, intake=False, nozzle=False)
    pod(f"{prefix}_{sd}_Core", (s * x, ya - 0.03), (s * x, yb), (w, w), (h, h), (zc, zc), M_BODY, n=4, chamfer=0.08, top=0.60, rake=0.0, intake=False, nozzle=False)
    pod(f"{prefix}_{sd}_Nozzle", (s * x, yb - 0.03), (s * x, y1), (w, w * 0.96), (h, h * 0.94), (zc, zc), M_MECH, n=4, chamfer=0.08, top=0.60, rake=0.0, intake=False, nozzle=True)
    for k, dz in enumerate((-0.12, 0.0, 0.12)):
        box(f"{prefix}_{sd}_Vane{k}", (s * x, y1 - 0.07, zc + dz * h), (w * 0.74, 0.10, 0.025), M_STRUCT, bevel=0.004)
    box(f"{prefix}_{sd}_VectorJoint", (s * x, yb - 0.015, zc), (w * 1.05, 0.04, h * 1.02), M_STRUCT, bevel=0.006)
    slab(f"{prefix}_{sd}_ServicePanel", [(s * (x - 0.17), ya - 0.2), (s * (x + 0.17), ya - 0.2), (s * (x + 0.17), yb + 0.2), (s * (x - 0.17), yb + 0.2)],
         z0 + h + 0.004, z0 + h + 0.024, M_BODY, bevel=0.004)
    for k, yy in enumerate((y0 - 0.1, (y0 + y1) / 2, y1 + 0.3)):
        box(f"{prefix}_{sd}_Mount{k}", (s * x, yy, z0 - 0.02), (w * 0.72, 0.09, 0.06), M_STRUCT, bevel=0.008)
    pod(f"{prefix}_{sd}_SideScoop", (s * (x + w * 0.52), ya + 0.05), (s * (x + w * 0.52), ya - 0.75), (0.10, 0.22, 0.22), (0.18, h * 0.6, h * 0.58),
        (z0 + h * 0.52, z0 + h * 0.55, z0 + h * 0.55), M_BODY, n=6, chamfer=0.2, top=0.8, rake=0.12, nozzle=False)


def hover_units(prefix, spots, size=(0.46, 0.64)):
    for k, (x, y, z) in enumerate(spots):
        box(f"{prefix}_HoverBracket{k}", (x, y, z), (size[0] + 0.08, size[1] + 0.08, 0.04), M_STRUCT, bevel=0.008)
        box(f"{prefix}_HoverEmitter{k}", (x, y, z - 0.045), (size[0], size[1], 0.05), M_HOVER, bevel=0.01)
        for q in range(4):
            box(f"{prefix}_HoverCoil{k}_{q}", (x, y - size[1] * 0.36 + q * size[1] * 0.24, z - 0.073), (size[0] * 0.85, 0.05, 0.008), M_OPEN, bevel=0.0)


def long_stabilizers(prefix, x0, y, z):
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        stab_blade(f"{prefix}_Stabilizer_{sd}", s, x0, 1.62, y, 1.45, y - 0.30, 1.05, z, z - 0.04, 0.20, 0.13, endplate=0.20)
        box(f"{prefix}_StabRootClamp_{sd}", (s * x0, y - 0.70, z), (0.08, 0.80, 0.18), M_STRUCT, bevel=0.01)
        tube(f"{prefix}_StabHinge_{sd}", (s * (x0 + 0.02), y - 0.25, z), (s * (x0 + 0.02), y - 1.15, z), 0.02, M_MECH)


def nomad_hauler():
    """A — HAULER: cabine à frente coberta por painéis; atrás, caixa aberta em estrutura tubular com módulo de radiadores,
    dois tanques Aux com cintas, reator na gaiola e dois blocos de propulsão montados no frame traseiro."""
    global BODY
    BODY = dict(y=[3.70, 2.90, 1.60, 0.60], hw=[0.62, 0.86, 0.98, 1.00], hwb=[0.52, 0.74, 0.86, 0.88], hwt=[0.40, 0.58, 0.66, 0.68],
                zb=[0.31, 0.29, 0.28, 0.28], zc=[0.40, 0.46, 0.52, 0.54], zt=[0.54, 0.72, 0.92, 0.98])
    panels('A_Cab', 3.66, 0.62, n=9)
    box('A_SkidPlate', (0.0, 3.20, 0.27), (1.00, 0.90, 0.05), M_STRUCT)
    box('A_CrashBumper', (0.0, 3.74, 0.40), (1.15, 0.12, 0.18), M_STRUCT)
    cockpit_cut('A_Canopy', 2.30, 1.05, 0.46, 0.17, lambda y: B('zt', y))
    hoop('A_RollHoop', 0.85, 0.82, 0.60, 1.30)
    tube('A_CageTopBar', (0.0, 0.85, 1.30), (0.0, 1.80, 1.02), 0.03, M_STRUCT)
    space_frame('A_Bed', [(0.60, 0.98, 0.32, 0.78), (-0.70, 0.98, 0.32, 0.80), (-2.00, 0.95, 0.32, 0.78), (-3.20, 0.90, 0.32, 0.74)])
    radiator('A_RadiatorStack', (0.0, -0.25, 1.05), (1.10, 0.80, 0.42))
    pipe('A_RamAirDuct', [(0.0, 1.10, 1.02), (0.0, 0.62, 1.20), (0.0, 0.20, 1.25)], 0.08, M_MECH)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        tank(f"A_AuxTank_{sd}", (s * 0.70, -1.20, 0.62), 0.42, 1.10, 0.44)
        prop_unit('A_Prop', s, 0.60, -2.00, -3.70, 0.64, 0.60, 0.30)
        pipe(f"A_Coolant_{sd}", [(s * 0.30, -0.65, 0.88), (s * 0.24, -1.20, 0.80), (s * 0.20, -1.65, 0.70)], 0.022, M_COOL, clamps=True)
        harness(f"A_HarnessReactorProp_{sd}", [(s * 0.22, -2.20, 0.62), (s * 0.40, -2.30, 0.62), (s * 0.48, -2.50, 0.66)])
    cage('A_ReactorFrame', -0.26, 0.26, -1.65, -2.35, 0.36, 0.78, 0.024, M_STRUCT)
    loft('A_ReactorCore', [hexsec(y, 0.18, 0.13, 0.13, 0.42, 0.56, 0.72) for y in (-1.75, -2.25)], M_CORE, bevel=0.01)
    long_stabilizers('A', 0.98, -2.15, 0.56)
    hover_units('A', [(0.45, 2.70, 0.28), (-0.45, 2.70, 0.28), (0.45, 0.80, 0.27), (-0.45, 0.80, 0.27), (0.60, -2.80, 0.29), (-0.60, -2.80, 0.29)])
    for nm, p in (('Socket_Utility', (0.0, 3.30, 0.56)), ('Socket_Cooling', (0.0, -0.25, 0.86)), ('Socket_Reactor', (0.0, -2.00, 0.34)),
                  ('Socket_Engine', (0.0, -2.80, 0.42)), ('Socket_Aux_R', (0.70, -1.20, 0.38)), ('Socket_Aux_L', (-0.70, -1.20, 0.38))):
        socket('A_' + nm, p, 0.5)


def nomad_spine():
    """B — SPINE: plataforma hover baixa; espinha em treliça (viga de rede) ao centro; os módulos (cockpit, bancos de
    radiadores, tanque, reator) estão presos à espinha com grampos; propulsão nas pontas traseiras da plataforma."""
    global BODY
    floor = [(-0.70, 3.60), (0.70, 3.60), (1.05, 2.60), (1.08, -2.60), (0.95, -3.45), (-0.95, -3.45), (-1.08, -2.60), (-1.05, 2.60)]
    slab('B_HoverPlatform', floor, 0.24, 0.34, M_STRUCT, bevel=0.03)
    for s in (1, -1):
        box(f"B_EdgeSkirt_{'R' if s > 0 else 'L'}", (s * 1.06, -0.10, 0.30), (0.05, 5.20, 0.14), M_MECH, bevel=0.01)
    ys = np.linspace(2.0, -3.0, 9)
    for s in (1, -1):
        for a, b in zip(ys, ys[1:]):
            tube(f"B_TrussTop_{s}_{a:.2f}", (s * 0.18, a, 1.02), (s * 0.18, b, 1.02), 0.026, M_STRUCT)
            tube(f"B_TrussBot_{s}_{a:.2f}", (s * 0.18, a, 0.40), (s * 0.18, b, 0.40), 0.026, M_STRUCT)
            tube(f"B_TrussWeb_{s}_{a:.2f}", (s * 0.18, a, 0.40), (s * 0.18, b, 1.02), 0.018, M_STRUCT)
    for y in ys:
        for s in (1, -1):
            tube(f"B_TrussPost_{s}_{y:.2f}", (s * 0.18, y, 0.40), (s * 0.18, y, 1.02), 0.02, M_STRUCT)
        tube(f"B_TrussTie_{y:.2f}", (-0.18, y, 1.02), (0.18, y, 1.02), 0.018, M_STRUCT)
    BODY = dict(y=[3.40, 2.80, 2.00, 1.30], hw=[0.40, 0.58, 0.64, 0.60], hwb=[0.34, 0.50, 0.56, 0.52], hwt=[0.24, 0.38, 0.42, 0.40],
                zb=[0.36] * 4, zc=[0.44, 0.52, 0.58, 0.58], zt=[0.56, 0.80, 0.92, 0.90])
    panels('B_CockpitModule', 3.40, 1.30, belly=False, n=7)
    cockpit_cut('B_Canopy', 2.75, 1.45, 0.38, 0.16, lambda y: B('zt', y))
    for k, y in enumerate((2.0, 1.2, 0.2, -0.8, -1.8)):
        box(f"B_ModuleClamp{k}", (0.0, y, 1.06), (0.46, 0.10, 0.08), M_MECH, bevel=0.01)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        radiator(f"B_RadiatorBank_{sd}", (s * 0.56, 0.20, 0.70), (0.52, 1.30, 0.40))
        tube(f"B_RadArm_{sd}", (s * 0.18, 0.20, 0.80), (s * 0.32, 0.20, 0.80), 0.03, M_STRUCT)
        prop_unit('B_Prop', s, 0.62, -1.50, -3.70, 0.62, 0.58, 0.32)
        pipe(f"B_Coolant_{sd}", [(s * 0.40, -0.50, 0.62), (s * 0.24, -1.10, 0.62), (s * 0.20, -2.00, 0.60)], 0.022, M_COOL, clamps=True)
        harness(f"B_Harness_{sd}", [(s * 0.20, -2.40, 0.70), (s * 0.40, -2.55, 0.66), (s * 0.50, -2.70, 0.70)])
    tank('B_AuxTank', (0.0, -0.90, 1.30), 0.56, 1.20, 0.38)
    cage('B_ReactorFrame', -0.16, 0.16, -2.00, -2.80, 0.42, 0.98, 0.022, M_STRUCT)
    loft('B_ReactorCore', [hexsec(y, 0.12, 0.09, 0.09, 0.48, 0.66, 0.90) for y in (-2.10, -2.70)], M_CORE, bevel=0.01)
    long_stabilizers('B', 1.08, -0.40, 0.44)
    hover_units('B', [(0.50, 2.80, 0.24), (-0.50, 2.80, 0.24), (0.55, 0.30, 0.24), (-0.55, 0.30, 0.24), (0.62, -2.60, 0.24), (-0.62, -2.60, 0.24)])
    for nm, p in (('Socket_Cooling', (0.0, 0.20, 1.06)), ('Socket_Aux', (0.0, -0.90, 1.08)), ('Socket_Reactor', (0.0, -2.40, 0.40)),
                  ('Socket_Utility', (0.0, 3.30, 0.60))):
        socket('B_' + nm, p, 0.5)


def nomad_shell():
    """C — SHELL: corpo de expedição feito de muitas chapas separadas (com uma escotilha de serviço ABERTA a mostrar o
    interior), grelhas de radiador com condutas, rack de tejadilho, placas de proteção e frame traseiro de propulsão à vista."""
    global BODY
    BODY = dict(y=[3.70, 3.00, 1.60, 0.00, -1.40], hw=[0.66, 0.88, 1.00, 1.04, 1.04], hwb=[0.56, 0.76, 0.88, 0.92, 0.92],
                hwt=[0.42, 0.60, 0.70, 0.72, 0.72], zb=[0.31, 0.29, 0.28, 0.28, 0.28], zc=[0.40, 0.48, 0.56, 0.58, 0.58],
                zt=[0.56, 0.74, 0.92, 0.98, 0.98])
    panels('C_Nose', 3.66, 2.44, n=6)
    panels('C_FrontDeck', 2.40, 1.80, sides=False, belly=False, n=3)
    panels('C_Mid', 2.40, 0.42, top=False, n=6)
    panels('C_RearBody', 0.38, -1.40, n=6)
    cockpit_cut('C_Canopy', 1.75, 0.50, 0.46, 0.17, lambda y: B('zt', y))
    # escotilha de serviço aberta (lado direito): painel rodado na dobradiça superior, interior visível
    slab('C_ServiceHatch_Open', [(0.0, 0.0), (0.62, 0.0), (0.62, -0.02), (0.0, -0.02)], 0.0, 0.015, M_BODY, bevel=0.003)
    h = bpy.data.objects['C_ServiceHatch_Open']
    h.rotation_euler = (math.radians(90), 0.0, math.radians(90))
    h.location = (1.10, -0.20, 0.95)
    tube('C_HatchHinge', (1.04, -0.20, 0.92), (1.04, -0.84, 0.92), 0.014, M_MECH)
    radiator('C_SideRadiatorCore_R', (0.82, -0.52, 0.66), (0.10, 0.58, 0.40))
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        for k in range(6):
            box(f"C_GrilleSlat_{sd}{k}", (s * 1.05, -0.60 - k * 0.12, 0.66), (0.02, 0.07, 0.30), M_STRUCT, bevel=0.0)
        prop_unit('C_Prop', s, 0.62, -1.30, -3.70, 0.64, 0.62, 0.30)
        tube(f"C_RearFrameArch_{sd}", (s * 0.30, -1.45, 0.34), (s * 0.95, -1.75, 0.34), 0.03, M_STRUCT)
        tube(f"C_RearFrameDiag_{sd}", (s * 0.30, -1.45, 0.34), (s * 0.90, -3.10, 0.34), 0.026, M_STRUCT)
        harness(f"C_Harness_{sd}", [(s * 0.15, -1.50, 0.62), (s * 0.35, -1.80, 0.62), (s * 0.48, -2.10, 0.66)])
    tube('C_RearCross', (-0.95, -3.10, 0.34), (0.95, -3.10, 0.34), 0.03, M_STRUCT)
    cage('C_ReactorFrame', -0.22, 0.22, -1.45, -2.20, 0.36, 0.72, 0.022, M_STRUCT)
    loft('C_ReactorCore', [hexsec(y, 0.15, 0.11, 0.11, 0.42, 0.54, 0.66) for y in (-1.55, -2.10)], M_CORE, bevel=0.01)
    for k, (x, y) in enumerate(((0.48, 0.25), (-0.48, 0.25), (0.48, -1.05), (-0.48, -1.05))):
        tube(f"C_RackPost{k}", (x, y, 0.98), (x, y, 1.16), 0.02, M_STRUCT)
    for a, b in (((0.48, 0.25), (0.48, -1.05)), ((-0.48, 0.25), (-0.48, -1.05)), ((0.48, 0.25), (-0.48, 0.25)), ((0.48, -1.05), (-0.48, -1.05))):
        tube(f"C_RackRail_{a}", (a[0], a[1], 1.16), (b[0], b[1], 1.16), 0.02, M_STRUCT)
    box('C_UtilityModule', (0.0, -0.40, 1.28), (0.66, 0.84, 0.20), M_BODY, bevel=0.03)
    box('C_SkidPlate', (0.0, 3.20, 0.27), (1.10, 0.90, 0.05), M_STRUCT)
    long_stabilizers('C', 1.02, -2.05, 0.56)
    hover_units('C', [(0.48, 2.70, 0.29), (-0.48, 2.70, 0.29), (0.55, 0.20, 0.28), (-0.55, 0.20, 0.28), (0.62, -2.70, 0.29), (-0.62, -2.70, 0.29)])
    for nm, p in (('Socket_Utility', (0.0, -0.40, 1.18)), ('Socket_Reactor', (0.0, -1.80, 0.34)), ('Socket_Engine', (0.0, -2.80, 0.40))):
        socket('C_' + nm, p, 0.5)


SOCKETS_TXT = "Sockets: Engine M/L · Propulsion M ×2 · Wings M/L · Armor M · Reactor M/L · Cooling L · Tail M/L · Utility ×2 · Aux/Fuel (rail + grampo + conector)."
SHIP, TARGET, VIEW_SCALE = 'NOMAD', '7,4 × 3,3 × 1,45', 1.15
TEXTS = {
    'A': ("HAULER · cabine à frente coberta por painéis em chapa, com arco de proteção à vista; atrás, caixa aberta em estrutura tubular "
          "com módulo de radiadores (conduta de ar dinâmico do tejadilho), dois tanques Aux com cintas, reator na gaiola e blocos de propulsão no frame traseiro.",
          "Construção: placa de proteção + para-choques → célula + arco → chassis tubular → reator → radiadores e tubos → tanques → propulsão → painéis. " + SOCKETS_TXT,
          "Força: autonomia, refrigeração e manutenção à vista. Fraqueza: massa e velocidade de ponta. Refrigeração: radiadores sobre a caixa alimentados pelo tejadilho."),
    'B': ("SPINE · plataforma hover baixa e uma espinha em treliça ao centro; o cockpit, os bancos de radiadores, o tanque e o reator estão "
          "presos à espinha com grampos — lê-se como máquina de expedição modular e reparável.",
          "Construção: plataforma hover → treliça → grampos → módulos (cockpit, radiadores, tanque, reator) → propulsão → estabilizadores longos. " + SOCKETS_TXT,
          "Força: trocar módulos em minutos. Fraqueza: módulos expostos a impactos. Refrigeração: bancos laterais sobre a plataforma, tubos até ao reator."),
    'C': ("SHELL · corpo de expedição feito de chapas separadas, com uma escotilha de serviço aberta a mostrar o radiador; grelhas laterais, "
          "rack de tejadilho com módulo de utilidade, placa de proteção e frame traseiro de propulsão à vista.",
          "Construção: placa de proteção → célula → chassis (frame traseiro à vista) → reator → radiadores laterais → painéis com escotilhas → rack. " + SOCKETS_TXT,
          "Força: robustez e proteção. Fraqueza: área frontal e massa. Refrigeração: radiadores atrás das grelhas laterais com escotilha de serviço."),
}
PROPOSALS = [('A', 'HAULER', nomad_hauler), ('B', 'SPINE', nomad_spine), ('C', 'SHELL', nomad_shell)]
if globals().get('RUN_MAIN2', True):
    main()
