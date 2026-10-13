"""
EXTRACT: STARDUST — Naves V2 · WRAITH · linguagem ⅄ das STRIX Y1/Y2/Y3 (escolha do utilizador), em versão estreita e leve:
nariz em agulha, propulsão compacta, pernas finas/duplas com mais espaço negativo. ~6,5 x 2,4 x 1,10 m.
  blender -b --factory-startup -P wraith_v4.py -- <pasta_renders> <ficheiro.blend>
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_MAIN, RUN_MAIN2, RUN_V3 = False, False, False
exec(compile(open(os.path.join(HERE, 'strix_v3.py'), encoding='utf-8').read(), 'strix_v3.py', 'exec'), globals())

NEEDLE = dict(y=[3.25, 2.20, 1.00, -0.30, -1.50, -2.30], hw=[0.04, 0.30, 0.44, 0.46, 0.40, 0.30], hwb=[0.02, 0.09, 0.13, 0.14, 0.12, 0.10],
              hwt=[0.03, 0.16, 0.24, 0.25, 0.22, 0.16], zb=[0.56, 0.46, 0.42, 0.42, 0.44, 0.48], zc=[0.57, 0.58, 0.62, 0.64, 0.64, 0.64],
              zt=[0.58, 0.72, 0.84, 0.88, 0.86, 0.80])


def open_seat(prefix, y, z):
    box(prefix + '_SeatBase', (0.0, y, z), (0.30, 0.42, 0.10), M_MECH, bevel=0.03)
    box(prefix + '_SeatBack', (0.0, y - 0.22, z + 0.20), (0.30, 0.08, 0.40), M_MECH, bevel=0.03)
    for q in (-1, 1):
        box(f"{prefix}_Strap_{q}", (q * 0.07, y - 0.17, z + 0.26), (0.04, 0.02, 0.32), M_CABLE, bevel=0.0)
    box(prefix + '_Yoke', (0.0, y + 0.42, z + 0.22), (0.24, 0.04, 0.07), M_MECH, bevel=0.01)


def wraith_twinleg():
    """W1 TWIN-LEG (da Y1): agulha em diamante; de cada lado DUAS pernas finas (frente e trás) descem até um esqui esguio —
    o vazio entre pernas dá leveza; propulsores compactos na cauda; escoras da quilha à vista."""
    diamond_body('W1_Needle', NEEDLE, cockpit=(1.00, -0.20))
    cockpit_cut('W1_Canopy', 0.96, -0.16, 0.24, 0.12, lambda y: B('zt', y))
    hoop('W1_RollHoop', -0.25, 0.22, 0.78, 0.98, r=0.024)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"W1_FrontLeg_{sd}", s, (0.40, 0.62), (1.08, 0.28), 0.80, 0.62, 1.30, 1.15, t_root=0.11, t_tip=0.08)
        leg_blade(f"W1_RearLeg_{sd}", s, (0.38, 0.62), (1.08, 0.28), 0.90, 0.70, -0.70, -0.85, t_root=0.11, t_tip=0.08)
        hover_ski(f"W1_Ski_{sd}", s * 1.12, 1.40, -1.80, 0.24, w=0.22, h=0.13)
        tube(f"W1_KeelStrut_{sd}", (s * 0.10, 0.20, 0.42), (s * 0.80, 0.10, 0.42), 0.022, M_STRUCT)
        prop_unit('W1_Prop', s, 0.22, -1.45, -3.25, 0.30, 0.36, 0.56)
        harness(f"W1_Harness_{sd}", [(s * 0.06, -1.40, 0.66), (s * 0.16, -1.60, 0.72)], n=2)
    hover_units('W1', [(0.0, 1.75, 0.38)], size=(0.16, 0.44))
    for nm, p in (('Socket_Wing_R', (0.42, 0.20, 0.62)), ('Socket_Wing_L', (-0.42, 0.20, 0.62)), ('Socket_Engine', (0.0, -2.40, 0.50))):
        socket('W1_' + nm, p, 0.35)


def wraith_feet():
    """W2 FEET (da Y2): agulha com cockpit ABERTO; pernas traseiras finas descem até propulsores compactos junto ao chão (pés);
    lâminas dianteiras finas até emissores; quilha estrutural à vista."""
    ctrl = dict(NEEDLE)
    ctrl['y'] = [3.25, 2.20, 1.00, -0.30, -1.10, -1.60]
    diamond_body('W2_Needle', ctrl, cockpit=(1.05, 0.05))
    open_seat('W2', 0.55, 0.50)
    hoop('W2_RollHoop', 0.02, 0.24, 0.78, 1.02, r=0.024)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"W2_RearLeg_{sd}", s, (0.36, 0.64), (0.98, 0.56), 1.00, 0.85, -0.85, -1.00, t_root=0.11, t_tip=0.10)
        prop_unit('W2_Prop', s, 1.00, -0.45, -3.25, 0.36, 0.42, 0.28)
        leg_blade(f"W2_FrontBlade_{sd}", s, (0.26, 0.52), (0.82, 0.28), 0.60, 0.42, 2.25, 2.05, t_root=0.09, t_tip=0.07)
        box(f"W2_FrontEmitter_{sd}", (s * 0.84, 1.85, 0.24), (0.22, 0.42, 0.05), M_HOVER, bevel=0.008)
        harness(f"W2_Harness_{sd}", [(s * 0.08, -1.30, 0.60), (s * 0.50, -1.45, 0.62), (s * 0.95, -1.50, 0.62)])
    box('W2_Keel', (0.0, -2.10, 0.46), (0.08, 1.60, 0.10), M_STRUCT, bevel=0.01)
    cage('W2_ReactorFrame', -0.14, 0.14, -1.55, -2.30, 0.48, 0.80, 0.02, M_STRUCT)
    hover_units('W2', [(0.0, -0.40, 0.38)], size=(0.16, 0.50))
    for nm, p in (('Socket_Propulsion_R', (1.00, -1.80, 0.24)), ('Socket_Propulsion_L', (-1.00, -1.80, 0.24)), ('Socket_Reactor', (0.0, -1.90, 0.46))):
        socket('W2_' + nm, p, 0.35)


def wraith_gull():
    """W3 GULL (da Y3): agulha; pernas em gaivota invertida finas — descem até joelhos com emissor e abrem curtas até placas
    terminais; propulsão compacta em cima da cauda."""
    diamond_body('W3_Needle', NEEDLE, cockpit=(1.00, -0.20))
    cockpit_cut('W3_Canopy', 0.96, -0.16, 0.24, 0.12, lambda y: B('zt', y))
    hoop('W3_RollHoop', -0.25, 0.22, 0.78, 0.98, r=0.024)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"W3_LegUpper_{sd}", s, (0.40, 0.62), (0.80, 0.30), 1.30, 1.10, -0.40, -0.55, t_root=0.12, t_tip=0.11)
        leg_blade(f"W3_LegOuter_{sd}", s, (0.78, 0.30), (1.16, 0.38), 1.10, 0.80, -0.55, -0.75, t_root=0.11, t_tip=0.08)
        box(f"W3_KneeEmitter_{sd}", (s * 0.80, -1.10, 0.22), (0.24, 1.00, 0.05), M_HOVER, bevel=0.008)
        box(f"W3_KneeJoint_{sd}", (s * 0.80, -1.10, 0.32), (0.12, 0.92, 0.10), M_STRUCT, bevel=0.012)
        box(f"W3_Endplate_{sd}", (s * 1.17, -1.15, 0.32), (0.04, 0.70, 0.20), M_STRUCT, bevel=0.01)
        prop_unit('W3_Prop', s, 0.20, -1.20, -3.25, 0.30, 0.36, 0.60)
    hover_units('W3', [(0.0, 1.75, 0.38)], size=(0.16, 0.44))
    for nm, p in (('Socket_Wing_R', (0.42, -0.90, 0.62)), ('Socket_Wing_L', (-0.42, -0.90, 0.62)), ('Socket_Engine', (0.0, -2.50, 0.54))):
        socket('W3_' + nm, p, 0.35)


SHIP, TARGET, VIEW_SCALE = 'WRAITH', '6,5 × 2,4 × 1,10', 1.05
TEXTS = {
    'W1': ("W1 TWIN-LEG · linguagem Y1: agulha em diamante; de cada lado duas pernas finas (frente e trás) descem até um esqui esguio — "
           "o vazio entre as pernas dá leveza. Propulsores compactos na cauda; escoras da quilha à vista.",
           "Construção: quilha → célula + arco → raízes das pernas → pernas duplas → esquis → propulsores → chapas.",
           "Força: leveza e agilidade. Fraqueza: pernas finas expostas. Hover: esquis + emissor no nariz."),
    'W2': ("W2 FEET · linguagem Y2: agulha com cockpit ABERTO (banco à vista); pernas traseiras finas até propulsores compactos junto ao chão; "
           "lâminas dianteiras finas até emissores; quilha estrutural à vista.",
           "Construção: quilha → banco + arco → reator → pernas traseiras + propulsores → lâminas dianteiras → chapas.",
           "Força: propulsão baixa e nariz muito leve. Fraqueza: piloto e propulsores expostos. Hover: lâminas dianteiras + quilha."),
    'W3': ("W3 GULL · linguagem Y3: agulha; pernas em gaivota invertida finas — joelhos com emissor junto ao chão e pontas curtas com placas "
           "terminais; propulsão compacta em cima da cauda.",
           "Construção: quilha → célula + arco → pernas superiores → joelhos com emissores → pontas com placas → propulsores → chapas.",
           "Força: banking agressivo nas paredes. Fraqueza: joelhos complexos. Hover: emissores nos joelhos + nariz."),
}
PROPOSALS = [('W1', 'TWIN-LEG', wraith_twinleg), ('W2', 'FEET', wraith_feet), ('W3', 'GULL', wraith_gull)]
main()
