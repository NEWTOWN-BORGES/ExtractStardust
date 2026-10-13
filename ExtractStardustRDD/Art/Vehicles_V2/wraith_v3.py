"""
EXTRACT: STARDUST — Naves V2 · WRAITH · linguagem Λ (V invertido): o corpo é o vértice e as pernas descem direitas
ao chão. Lâmina estreita e baixa, propulsão compacta, estrutura e espaço negativo à vista. ~6,5 x 2,4 x 1,10 m.
  blender -b --factory-startup -P wraith_v3.py -- <pasta_renders> <ficheiro.blend>
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_MAIN, RUN_MAIN2, RUN_V3 = False, False, False
exec(compile(open(os.path.join(HERE, 'strix_v3.py'), encoding='utf-8').read(), 'strix_v3.py', 'exec'), globals())

POD = dict(y=[3.25, 2.30, 1.00, -0.40, -1.60, -2.40], hw=[0.05, 0.24, 0.32, 0.34, 0.30, 0.20], hwb=[0.03, 0.08, 0.10, 0.10, 0.09, 0.07],
           hwt=[0.03, 0.13, 0.18, 0.18, 0.16, 0.11], zb=[0.64, 0.58, 0.54, 0.54, 0.56, 0.60], zc=[0.66, 0.72, 0.76, 0.78, 0.78, 0.76],
           zt=[0.68, 0.84, 0.95, 0.99, 0.95, 0.88])


def open_seat(prefix, y, z):
    """Cockpit aberto: banco de competição com cintos e volante (o utilizador quer ver os bancos às vezes)."""
    box(prefix + '_SeatBase', (0.0, y, z), (0.30, 0.42, 0.10), M_MECH, bevel=0.03)
    box(prefix + '_SeatBack', (0.0, y - 0.22, z + 0.20), (0.30, 0.08, 0.40), M_MECH, bevel=0.03)
    for q in (-1, 1):
        box(f"{prefix}_Strap_{q}", (q * 0.07, y - 0.17, z + 0.26), (0.04, 0.02, 0.32), M_CABLE, bevel=0.0)
    box(prefix + '_Yoke', (0.0, y + 0.42, z + 0.22), (0.24, 0.04, 0.07), M_MECH, bevel=0.01)


def wraith_skeleton_lambda():
    """Λ1 SKELETON: pod esguio no vértice; duas pernas longas e finas descem até esquis hover; três escoras à vista ligam a
    quilha às pernas — esqueleto e espaço negativo dentro do Λ. Propulsão compacta e central na cauda do pod."""
    diamond_body('L1_Pod', POD, cockpit=(1.10, -0.20))
    cockpit_cut('L1_Canopy', 1.06, -0.16, 0.24, 0.12, lambda y: B('zt', y))
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"L1_Leg_{sd}", s, (0.30, 0.82), (1.06, 0.30), 2.70, 2.40, 1.70, 1.45, t_root=0.12, t_tip=0.09)
        hover_ski(f"L1_Ski_{sd}", s * 1.10, 1.85, -2.95, 0.24, w=0.24, h=0.14)
        for k, y in enumerate((1.20, -0.30, -1.70)):
            tube(f"L1_Strut_{sd}{k}", (s * 0.06, y, 0.54), (s * 0.74, y, 0.52), 0.024, M_STRUCT)
        prop_unit('L1_Prop', s, 0.20, -1.55, -3.25, 0.30, 0.34, 0.62)
        harness(f"L1_Harness_{sd}", [(s * 0.06, -1.50, 0.70), (s * 0.14, -1.70, 0.76)], n=2)
    hover_units('L1', [(0.0, 1.80, 0.56), (0.0, -0.90, 0.52)], size=(0.16, 0.44))
    for nm, p in (('Socket_Wing_R', (0.30, 0.20, 0.80)), ('Socket_Wing_L', (-0.30, 0.20, 0.80)), ('Socket_Engine', (0.0, -2.40, 0.56))):
        socket('L1_' + nm, p, 0.4)


def wraith_roof_lambda():
    """Λ2 ROOF: pod de nariz com cockpit aberto; atrás dele, o corpo é um telhado em Λ em dois troços (frente e trás) que
    descem de uma viga-cumeeira até ao chão; no intervalo entre troços vêem-se as costelas e o reator; propulsores nos pés."""
    global BODY
    nose = dict(y=[3.25, 2.60, 1.80, 1.20], hw=[0.05, 0.24, 0.30, 0.28], hwb=[0.03, 0.08, 0.10, 0.10], hwt=[0.03, 0.13, 0.16, 0.15],
                zb=[0.60, 0.56, 0.54, 0.56], zc=[0.62, 0.70, 0.76, 0.78], zt=[0.64, 0.84, 0.94, 0.96])
    BODY = nose
    panels('L2_NosePod', 3.25, 1.20, top=False, n=6)
    open_seat('L2', 2.05, 0.62)
    tube('L2_RidgeSpine', (0.0, 1.30, 0.96), (0.0, -2.60, 0.98), 0.05, M_STRUCT)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"L2_RoofFront_{sd}", s, (0.04, 0.96), (1.04, 0.30), 1.70, 1.50, 1.40, 1.10, t_root=0.10, t_tip=0.08)
        leg_blade(f"L2_RoofRear_{sd}", s, (0.04, 0.98), (1.06, 0.30), 1.90, 1.70, -0.75, -0.95, t_root=0.10, t_tip=0.08)
        for k, y in enumerate((-0.15, -0.45)):
            tube(f"L2_Rib_{sd}{k}", (s * 0.02, y, 0.92), (s * 0.95, y, 0.34), 0.026, M_STRUCT)
        tube(f"L2_LowerRail_{sd}", (s * 1.00, 1.40, 0.30), (s * 1.02, -2.70, 0.30), 0.03, M_STRUCT)
        prop_unit('L2_Prop', s, 1.02, -1.30, -3.25, 0.34, 0.36, 0.26)
        box(f"L2_FootEmitter_{sd}", (s * 1.02, 0.40, 0.24), (0.26, 1.60, 0.05), M_HOVER, bevel=0.008)
        harness(f"L2_Harness_{sd}", [(s * 0.10, -0.40, 0.62), (s * 0.55, -0.45, 0.48), (s * 0.95, -0.50, 0.40)])
    cage('L2_ReactorFrame', -0.15, 0.15, -0.10, -0.55, 0.40, 0.70, 0.02, M_STRUCT)
    loft('L2_ReactorCore', [hexsec(y, 0.10, 0.08, 0.08, 0.46, 0.56, 0.64) for y in (-0.15, -0.50)], M_CORE, bevel=0.01)
    for nm, p in (('Socket_Propulsion_R', (1.02, -2.20, 0.22)), ('Socket_Propulsion_L', (-1.02, -2.20, 0.22)), ('Socket_Reactor', (0.0, -0.32, 0.38))):
        socket('L2_' + nm, p, 0.4)


def wraith_dart_lambda():
    """Λ3 DART: agulha alta (o vértice) com pernas traseiras curtas a descer até aos propulsores (pés) e duas lâminas
    dianteiras finas até emissores hover; quilha estrutural à vista entre as pernas."""
    diamond_body('L3_Dart', POD, cockpit=(1.10, -0.20))
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"L3_RearLeg_{sd}", s, (0.16, 0.92), (0.98, 0.58), 1.30, 1.10, -1.05, -1.20, t_root=0.12, t_tip=0.10)
        prop_unit('L3_Prop', s, 1.00, -0.85, -3.25, 0.34, 0.40, 0.30)
        leg_blade(f"L3_FrontBlade_{sd}", s, (0.12, 0.80), (0.82, 0.30), 0.70, 0.45, 2.30, 2.05, t_root=0.09, t_tip=0.07)
        box(f"L3_FrontEmitter_{sd}", (s * 0.84, 1.85, 0.24), (0.22, 0.42, 0.05), M_HOVER, bevel=0.008)
        harness(f"L3_Harness_{sd}", [(s * 0.08, -1.40, 0.70), (s * 0.50, -1.55, 0.74), (s * 0.95, -1.60, 0.70)])
    box('L3_Keel', (0.0, -1.80, 0.48), (0.08, 1.80, 0.10), M_STRUCT, bevel=0.01)
    open_seat('L3', 0.55, 0.64)
    hover_units('L3', [(0.0, -0.40, 0.52)], size=(0.16, 0.50))
    for nm, p in (('Socket_Propulsion_R', (1.00, -2.00, 0.26)), ('Socket_Propulsion_L', (-1.00, -2.00, 0.26)), ('Socket_Engine', (0.0, -2.40, 0.56))):
        socket('L3_' + nm, p, 0.4)


SHIP, TARGET, VIEW_SCALE = 'WRAITH', '6,5 × 2,4 × 1,10', 1.05
TEXTS = {
    'L1': ("Λ1 SKELETON · pod esguio no vértice do Λ; duas pernas longas e finas descem até esquis hover; três escoras à vista ligam a quilha "
           "às pernas — esqueleto e espaço negativo dentro do Λ. Propulsão compacta e central na cauda.",
           "Construção: quilha + pod → célula → raízes das pernas (longarina + grampo) → pernas → escoras → esquis → propulsão → chapas.",
           "Força: leveza e mudança de linha instantânea. Fraqueza: pernas finas expostas. Hover: esquis longos + emissores na quilha."),
    'L2': ("Λ2 ROOF · pod de nariz com cockpit ABERTO (banco à vista); atrás, o corpo é um telhado em Λ em dois troços que descem de uma "
           "viga-cumeeira até ao chão; no intervalo vêem-se costelas e reator. Propulsores nos pés do Λ.",
           "Construção: viga-cumeeira → costelas → reator na gaiola → lâminas-telhado → propulsores nos pés → tubo do cockpit + banco.",
           "Força: silhueta única e centro de massa baixo. Fraqueza: piloto exposto. Hover: emissores ao longo dos pés."),
    'L3': ("Λ3 DART · agulha alta com pernas traseiras curtas até aos propulsores (pés) e duas lâminas dianteiras finas até emissores hover; "
           "cockpit ABERTO; quilha estrutural à vista entre as pernas.",
           "Construção: quilha → agulha → banco → pernas traseiras + propulsores → lâminas dianteiras + emissores → cablagens → chapas.",
           "Força: agulha muito baixa à frente, ideal para skill routes. Fraqueza: pouca proteção. Hover: lâminas dianteiras + quilha."),
}
PROPOSALS = [('L1', 'SKELETON', wraith_skeleton_lambda), ('L2', 'ROOF', wraith_roof_lambda), ('L3', 'DART', wraith_dart_lambda)]
main()
