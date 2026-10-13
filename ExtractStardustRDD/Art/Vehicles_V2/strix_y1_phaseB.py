"""
EXTRACT: STARDUST — Naves V2 · STRIX Y1 ARCH (aprovada na fase A) · Fase B: greybox de engenharia, de dentro para fora.
  blender -b --factory-startup -P strix_y1_phaseB.py -- <pasta_renders> <ficheiro.blend>

Ordem (Bíblia §2 / Prompt §2): quilha + longarinas + cavernas → crash box → célula do cockpit → reator → propulsão com
pilões → pernas hover (longarina, grampo, atuador, placa) → refrigeração → sockets do Doc 02 (rail + grampo + conector)
→ cablagens/tubos com origem e destino → chapas separadas (folgas, dobradiças, portas de serviço).
Sockets da STRIX (Catalog.cs): Engine, Propulsion, Wings, Armor, Reactor, Cooling, Tail, Utility.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_MAIN, RUN_MAIN2, RUN_V3 = False, False, False
exec(compile(open(os.path.join(HERE, 'strix_v3.py'), encoding='utf-8').read(), 'strix_v3.py', 'exec'), globals())

BODY = STRIX_CTRL


def bulkhead(name, y, k=0.84, r=0.022):
    """Caverna: anel estrutural com a forma da secção em diamante, recolhido para dentro das chapas."""
    pts = sec(y)
    zm = (B('zb', y) + B('zt', y)) / 2
    pts = [(x * k, y, zm + (z - zm) * k) for x, _, z in pts]
    for i in range(len(pts)):
        tube(f"{name}_{i}", pts[i], pts[(i + 1) % len(pts)], r, M_STRUCT)


def build_y1():
    # 1 estrutura: quilha dupla, longarinas dos ombros, cavernas, crash box, pontos de fixação das pernas
    group('1_Structure')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        box(f"Keel_Rail_{sd}", (s * 0.10, 0.10, 0.50), (0.06, 4.90, 0.07), M_STRUCT, bevel=0.008)
        tube(f"Longeron_{sd}", (s * 0.40, 2.10, 0.66), (s * 0.40, -2.00, 0.68), 0.028, M_STRUCT)
        tube(f"Crash_Tube_{sd}", (s * 0.10, 2.50, 0.50), (s * 0.03, 2.95, 0.58), 0.026, M_STRUCT)
        for k, y in enumerate((0.40, -0.90)):
            tube(f"LegHardpoint_{sd}{k}", (s * 0.10, y, 0.50), (s * 0.56, y, 0.66), 0.03, M_STRUCT)
        box(f"LegHardpoint_{sd}_Plate", (s * 0.56, -0.25, 0.66), (0.06, 1.50, 0.14), M_MECH, bevel=0.01)
        tube(f"KeelStrut_{sd}", (s * 0.16, -0.40, 0.44), (s * 1.00, -0.60, 0.46), 0.03, M_STRUCT)
    for i, y in enumerate((2.30, 1.10, -0.25, -1.30, -2.05)):
        bulkhead(f"Bulkhead{i}", y)
    box('Crash_HoneycombBox', (0.0, 2.62, 0.56), (0.18, 0.40, 0.10), M_MECH, bevel=0.01)
    for k in range(4):
        box(f"Crash_Cell{k}", (0.0, 2.47 + k * 0.10, 0.615), (0.16, 0.012, 0.012), M_STRUCT, bevel=0.0)

    # 2 célula de segurança: piso, proteções laterais, arcos, banco, comandos, vidro baixo com dobradiça
    group('2_CockpitCell')
    slab('Cell_FloorPan', [(-0.24, 1.00), (0.24, 1.00), (0.28, -0.24), (-0.28, -0.24)], 0.52, 0.55, M_STRUCT, bevel=0.006)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        slab(f"Cell_SideProtection_{sd}", [(s * 0.28, 1.00), (s * 0.32, 1.00), (s * 0.34, -0.24), (s * 0.30, -0.24)], 0.55, 0.78, M_MECH, bevel=0.006)
        tube(f"Canopy_FrameRail_{sd}", (s * 0.27, 1.00, B('zt', 1.00) + 0.01), (s * 0.27, -0.20, B('zt', -0.20) + 0.01), 0.016, M_STRUCT)
    hoop('Cell_FrontHoop', 1.00, 0.28, 0.55, 0.88, r=0.026)
    hoop('Cell_RollHoop', -0.30, 0.30, 0.55, 1.10, r=0.028)
    box('Cell_Seat', (0.0, 0.10, 0.62), (0.36, 0.52, 0.12), M_MECH, bevel=0.04)
    box('Cell_SeatBack', (0.0, -0.14, 0.78), (0.34, 0.09, 0.32), M_MECH, bevel=0.03)
    box('Cell_ControlYoke', (0.0, 0.66, 0.74), (0.22, 0.05, 0.07), M_MECH, bevel=0.01)
    box('Cell_Dash', (0.0, 0.88, 0.80), (0.42, 0.14, 0.08), M_MECH, bevel=0.01)
    cockpit_cut('Canopy_Glass', 1.02, -0.22, 0.30, 0.14, lambda y: B('zt', y))
    tube('Canopy_Hinge', (-0.20, 1.04, B('zt', 1.04) + 0.02), (0.20, 1.04, B('zt', 1.04) + 0.02), 0.018, M_MECH)

    # 3 reator: gaiola + núcleo blindado (só se vê pelas aberturas)
    group('3_Reactor')
    cage('Reactor_Frame', -0.16, 0.16, -1.30, -2.00, 0.50, 0.82, 0.02, M_STRUCT)
    loft('Reactor_Core', [hexsec(y, 0.12, 0.08, 0.08, 0.54, 0.66, 0.78) for y in (-1.38, -1.92)], M_CORE, bevel=0.01)
    for k, y in enumerate((-1.45, -1.65, -1.85)):
        box(f"Reactor_ShieldBand{k}", (0.0, y, 0.66), (0.28, 0.04, 0.26), M_MECH, bevel=0.01)

    # 4 propulsão nos ombros traseiros, com pilões até às longarinas e isoladores
    group('4_Propulsion')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        prop_unit('Prop', s, 0.62, -1.20, -3.10, 0.50, 0.50, 0.70)
        for k, y in enumerate((-1.35, -2.00)):
            tube(f"Prop_{sd}_Pylon{k}", (s * 0.40, y, 0.68), (s * 0.58, y, 0.70), 0.026, M_STRUCT)
            for q in (-1, 1):
                box(f"Prop_{sd}_Isolator{k}{q}", (s * 0.62 + q * 0.14, y, 0.70), (0.06, 0.06, 0.04), M_CABLE, bevel=0.01)
    box('Engine_PowerConverter', (0.0, -2.05, 0.86), (0.30, 0.50, 0.14), M_MECH, bevel=0.02)

    # 5 pernas hover: longarina, grampo, atuador hidráulico, placa com emissores; emissores da quilha
    group('5_LegsHover')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"Leg_{sd}", s, (0.58, 0.68), (1.36, 0.30), 2.0, 1.6, 0.70, 0.50)
        hover_ski(f"Ski_{sd}", s * 1.38, 0.55, -0.85, 0.26, w=0.26)
        pipe(f"Leg_{sd}_Actuator", [(s * 0.30, 0.10, 0.52), (s * 0.70, 0.05, 0.50), (s * 0.98, 0.00, 0.44)], 0.022, M_MECH)
    hover_units('Keel', [(0.0, 1.60, 0.40), (0.0, -0.50, 0.40)], size=(0.24, 0.50))
    for k, (x, y, z) in enumerate(((0.0, 2.70, 0.50), (1.38, 0.30, 0.32), (-1.38, 0.30, 0.32), (0.0, -1.10, 0.43))):
        box(f"Hover_SurfaceSensor{k}", (x, y, z), (0.07, 0.07, 0.04), M_SOCK, bevel=0.008)

    # 6 refrigeração: radiadores no ombro traseiro, sob portas de serviço; tubos até ao reator
    group('6_Cooling')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        box(f"Cool_Radiator_{sd}", (s * 0.22, -0.75, 0.80), (0.16, 0.40, 0.16), M_MECH, bevel=0.01)
        for k in range(6):
            box(f"Cool_RadFin_{sd}{k}", (s * 0.22, -0.60 - k * 0.06, 0.80), (0.17, 0.012, 0.15), M_STRUCT, bevel=0.0)
        pipe(f"Cool_PipeFeed_{sd}", [(s * 0.22, -0.95, 0.76), (s * 0.20, -1.10, 0.72), (s * 0.14, -1.35, 0.70)], 0.020, M_COOL, clamps=True)
        pipe(f"Cool_PipeReturn_{sd}", [(s * 0.12, -1.90, 0.78), (s * 0.26, -1.30, 0.82), (s * 0.24, -0.95, 0.84)], 0.016, M_COOL)

    # 7 sockets do Doc 02 (Catalog.cs: Engine, Propulsion, Wings, Armor, Reactor, Cooling, Tail, Utility)
    group('7_Sockets')
    socket('Socket_Engine', (0.0, -2.05, 0.95), 0.40)
    socket('Socket_Propulsion_R', (0.62, -2.10, 0.68), 0.80)
    socket('Socket_Propulsion_L', (-0.62, -2.10, 0.68), 0.80)
    socket('Socket_Wings_R', (0.60, -0.25, 0.75), 0.80)
    socket('Socket_Wings_L', (-0.60, -0.25, 0.75), 0.80)
    socket('Socket_Armor_R', (0.52, 1.60, 0.60), 0.70)
    socket('Socket_Armor_L', (-0.52, 1.60, 0.60), 0.70)
    socket('Socket_Reactor', (0.0, -1.50, 0.48), 0.60)
    socket('Socket_Cooling', (0.0, -0.75, 0.90), 0.30, rail_axis='x')
    socket('Socket_Tail', (0.0, -2.55, 0.62), 0.30, rail_axis='x')
    socket('Socket_Utility', (0.0, 2.40, 0.48), 0.40)

    # 8 cablagens e tubos com origem e destino
    group('8_Harness')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        harness(f"Harness_ReactorToProp_{sd}", [(s * 0.14, -1.60, 0.80), (s * 0.30, -1.70, 0.86), (s * 0.45, -1.90, 0.92)])
        harness(f"Harness_HoverLeg_{sd}", [(s * 0.14, -0.20, 0.56), (s * 0.56, -0.20, 0.64), (s * 1.00, -0.10, 0.48), (s * 1.34, 0.00, 0.34)], n=2)
    harness('Harness_ReactorToCockpit', [(0.0, -1.30, 0.80), (0.0, -0.80, 0.70), (0.0, -0.32, 0.62)], n=2)

    # 9 chapas separadas com folgas (nariz, frente, cockpit sem tejadilho, traseira) + portas de serviço com dobradiça
    group('9_Panels')
    panels('Panel_Nose', 3.10, 2.24, n=5, explode=(0.0, 0.30, 0.0))
    panels('Panel_Front', 2.20, 1.07, n=5, explode=(0.0, 0.25, 0.10))
    panels('Panel_Cockpit', 1.03, -0.23, top=False, n=6)
    panels('Panel_Rear', -0.27, -2.20, n=6, explode=(0.0, -0.25, 0.20))
    loft('Panel_NoseCap', [sec(3.10), [(x * 0.2, 3.14, z) for x, _, z in sec(3.10)]], M_BODY, bevel=0.0)
    EXPLODE['Panel_NoseCap'] = (0.0, 0.30, 0.0)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        y0, y1 = -0.52, -0.98
        slab(f"Panel_ServiceDoor_{sd}", [(s * 0.06, y0), (s * 0.30, y0), (s * 0.30, y1), (s * 0.06, y1)], B('zt', y0) + 0.008, B('zt', y0) + 0.024, M_BODY, bevel=0.004)
        EXPLODE[f"Panel_ServiceDoor_{sd}"] = (s * 0.15, 0.0, 0.85)
        tube(f"Panel_DoorHinge_{sd}", (s * 0.06, y0, B('zt', y0) + 0.02), (s * 0.30, y0, B('zt', y0) + 0.02), 0.010, M_MECH)

    # explodido: propulsores para fora/trás, pernas para fora, vidro para cima
    for ob in GROUPS['4_Propulsion'].objects:
        if ob.name.startswith('Prop_'):
            s = 1 if '_R_' in ob.name or ob.name.endswith('_R') else -1
            EXPLODE[ob.name] = (s * 0.40, -0.35, 0.30)
    for ob in GROUPS['5_LegsHover'].objects:
        for sd, s in (('_R', 1), ('_L', -1)):
            if ob.name.startswith(('Leg' + sd, 'Ski' + sd)):
                EXPLODE[ob.name] = (s * 0.60, 0.0, -0.05)
    for nm in ('Canopy_Glass', 'Canopy_Hinge', 'Canopy_FrameRail_R', 'Canopy_FrameRail_L'):
        EXPLODE[nm] = (0.0, 0.10, 0.70)


def main_y1():
    setup_render()
    build_y1()
    cams = dict(
        f34=(camera('Cam_F34', (6.0, 6.6, 3.1), look=(0.0, -0.1, 0.55), lens=50), 1600, 1000),
        r34=(camera('Cam_R34', (-5.4, -6.8, 3.3), look=(0.0, -0.8, 0.60), lens=50), 1600, 1000),
        top=(camera('Cam_Top', (0, 0, 20), rot=(0, 0, 90), ortho=7.0), 1400, 820),
        side=(camera('Cam_Side', (20, 0, 0.6), rot=(90, 0, 90), ortho=7.0), 1400, 480),
        under=(camera('Cam_Under', (3.9, 4.8, -2.4), look=(0.0, -0.2, 0.40), lens=45), 1400, 900),
    )
    shots = [
        ('assembled_f34', 'f34', None, (), False),
        ('exploded_f34', 'f34', None, (), True),
        ('cutaway_r34', 'r34', None, ('Panel_Rear', 'Panel_Cockpit_SideL', 'Prop_L_Core', 'Prop_L_ServicePanel', 'Panel_ServiceDoor'), False),
        ('cutaway_top', 'top', None, ('Panel_', 'Prop_R_Core', 'Prop_L_Core', 'Prop_R_ServicePanel', 'Prop_L_ServicePanel', 'Canopy_Glass'), False),
        ('underside', 'under', None, (), False),
        ('socketmap_top', 'top', ['1_Structure', '3_Reactor', '7_Sockets'], (), False),
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
    info = dict(labels=labels, size=list(cams['top'][1:]), title="STRIX · Y1 ARCH — FASE B · GREYBOX DE ENGENHARIA (de dentro para fora)",
                order="quilha + longarinas + cavernas → crash box → célula → reator → propulsão com pilões → pernas hover → refrigeração → sockets → cablagens → chapas")
    json.dump(info, open(os.path.join(OUT, 'strix_b_info.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('[STRIX Y1 B] peças por sistema:', {n: len(c.objects) for n, c in GROUPS.items()}, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


main_y1()
