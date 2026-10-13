"""
EXTRACT: STARDUST — Naves V2 · NOMAD no ADN da família (STRIX Y1): corpo em diamante levantado + pernas dos ombros ao chão,
com a mescla A+B pedida (cabine à frente com cockpit ABERTO, espinha com módulos presos, radiadores, tanques) e uma quilha
central que também desce ao chão: de frente lê-se M (três apoios = estabilidade de expedição). ~7,4 x 3,3 x 1,45 m.
  blender -b --factory-startup -P nomad_v4.py -- <pasta_renders> <ficheiro.blend>
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_MAIN, RUN_MAIN2, RUN_V3 = False, False, False
exec(compile(open(os.path.join(HERE, 'strix_v3.py'), encoding='utf-8').read(), 'strix_v3.py', 'exec'), globals())

BODY_N = dict(y=[3.70, 2.70, 1.40, 0.00, -1.40, -2.50], hw=[0.34, 0.62, 0.82, 0.88, 0.82, 0.64], hwb=[0.14, 0.18, 0.22, 0.24, 0.22, 0.18],
              hwt=[0.20, 0.34, 0.46, 0.50, 0.46, 0.36], zb=[0.60, 0.50, 0.46, 0.46, 0.48, 0.52], zc=[0.62, 0.68, 0.72, 0.74, 0.74, 0.74],
              zt=[0.66, 0.86, 1.00, 1.04, 1.02, 0.96])


def seat(prefix, y, z):
    box(prefix + '_SeatBase', (0.0, y, z), (0.48, 0.50, 0.12), M_MECH, bevel=0.04)
    box(prefix + '_SeatBack', (0.0, y - 0.26, z + 0.24), (0.48, 0.10, 0.48), M_MECH, bevel=0.04)
    box(prefix + '_Headrest', (0.0, y - 0.29, z + 0.54), (0.30, 0.10, 0.14), M_MECH, bevel=0.03)
    for q in (-1, 1):
        box(f"{prefix}_SeatBolster_{q}", (q * 0.26, y, z + 0.14), (0.06, 0.56, 0.30), M_MECH, bevel=0.02)
        box(f"{prefix}_Strap_{q}", (q * 0.10, y - 0.20, z + 0.30), (0.05, 0.02, 0.40), M_CABLE, bevel=0.0)
    box(prefix + '_Dash', (0.0, y + 0.62, z + 0.26), (0.80, 0.20, 0.14), M_MECH, bevel=0.02)
    box(prefix + '_Yoke', (0.0, y + 0.42, z + 0.30), (0.32, 0.04, 0.09), M_MECH, bevel=0.01)


def louvers(name, c, length, height, count):
    for k in range(count):
        t = (k + 0.5) / count - 0.5
        box(f"{name}_{k}", (c[0], c[1] + t * length, c[2]), (0.03, length / count * 0.6, height), M_STRUCT, bevel=0.0)


def nomad_core(prefix):
    """Corpo comum: diamante com cabine aberta à frente, para-choques, espinha com grampos, radiadores com grelha, tanque."""
    diamond_body(prefix + '_Body', BODY_N, cockpit=(2.15, 0.95))
    box(prefix + '_CrashBumper', (0.0, 3.74, 0.62), (0.90, 0.12, 0.20), M_STRUCT)
    box(prefix + '_SkidPlate', (0.0, 3.10, 0.58), (0.50, 1.00, 0.04), M_STRUCT)
    seat(prefix, 1.55, 0.58)
    hoop(prefix + '_RollHoop', 0.95, 0.46, 0.96, 1.36, r=0.032)
    tube(prefix + '_CageTopBar', (0.0, 0.95, 1.36), (0.0, 1.85, 1.10), 0.028, M_STRUCT)
    slab(prefix + '_WindDeflector', [(-0.42, 2.18), (0.42, 2.18), (0.36, 2.10), (-0.36, 2.10)], 0.90, 1.08, M_GLASS, bevel=0.003)
    # espinha de serviço sobre o dorso, com grampos (B) e tampa parcial
    for s in (1, -1):
        tube(f"{prefix}_SpineRail_{s}", (s * 0.16, 0.80, 1.10), (s * 0.16, -2.20, 1.04), 0.028, M_STRUCT)
    for k, y in enumerate((0.60, -0.40, -1.40)):
        box(f"{prefix}_Clamp{k}", (0.0, y, 1.12), (0.44, 0.10, 0.08), M_MECH, bevel=0.01)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        radiator(f"{prefix}_Radiator_{sd}", (s * 0.46, 0.05, 1.12), (0.34, 1.05, 0.26))
        louvers(f"{prefix}_RadLouver_{sd}", (s * 0.64, 0.05, 1.12), 1.05, 0.22, 8)
        pipe(f"{prefix}_Coolant_{sd}", [(s * 0.40, -0.55, 1.02), (s * 0.24, -1.20, 0.94), (s * 0.18, -1.80, 0.86)], 0.022, M_COOL, clamps=True)
    tank(prefix + '_AuxTank', (0.0, -1.05, 1.30), 0.50, 0.90, 0.30)


def center_keel(prefix):
    """Quilha central que desce ao chão (o traço do meio do M) com placa hover."""
    secs = []
    for y in np.linspace(1.30, -1.70, 6):
        secs.append([(0.07, y, 0.48), (0.07, y, 0.30), (-0.07, y, 0.30), (-0.07, y, 0.48)])
    loft(prefix + '_CenterKeel', secs, M_STRUCT, bevel=0.01)
    hover_ski(prefix + '_KeelPlate', 0.0, 0.40, -0.80, 0.25, w=0.30)


def nomad_m_arch():
    """N1 M-ARCH (Y1): duas pernas longas dos ombros até placas hover + quilha central ao chão (M); propulsores na raiz das pernas."""
    nomad_core('N1')
    center_keel('N1')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"N1_Leg_{sd}", s, (0.80, 0.78), (1.58, 0.30), 2.40, 1.80, 0.70, 0.20, t_root=0.20, t_tip=0.13)
        hover_ski(f"N1_Plate_{sd}", s * 1.60, 0.25, -1.20, 0.27, w=0.34)
        prop_unit('N1_Prop', s, 0.66, -1.60, -3.70, 0.58, 0.56, 0.62)
        harness(f"N1_Harness_{sd}", [(s * 0.14, -1.90, 0.80), (s * 0.40, -2.00, 0.86), (s * 0.55, -2.20, 0.92)])
    for nm, p in (('Socket_Wing_R', (0.82, 0.30, 0.74)), ('Socket_Wing_L', (-0.82, 0.30, 0.74)), ('Socket_Cooling', (0.0, 0.05, 1.14)),
                  ('Socket_Aux', (0.0, -1.05, 1.14)), ('Socket_Utility', (0.0, 3.10, 0.66))):
        socket('N1_' + nm, p, 0.45)


def nomad_m_feet():
    """N2 M-FEET (Y2): pernas traseiras até propulsores junto ao chão (pés) + lâminas dianteiras até placas + quilha central (M)."""
    nomad_core('N2')
    center_keel('N2')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"N2_RearLeg_{sd}", s, (0.70, 0.80), (1.30, 0.62), 1.50, 1.30, -1.30, -1.45, t_root=0.18, t_tip=0.16)
        prop_unit('N2_Prop', s, 1.32, -0.90, -3.70, 0.58, 0.58, 0.30)
        leg_blade(f"N2_FrontLeg_{sd}", s, (0.56, 0.70), (1.20, 0.30), 1.00, 0.70, 2.30, 2.05, t_root=0.14, t_tip=0.10)
        hover_ski(f"N2_FrontPlate_{sd}", s * 1.22, 2.10, 1.20, 0.26, w=0.30)
        harness(f"N2_Harness_{sd}", [(s * 0.14, -1.90, 0.80), (s * 0.70, -2.00, 0.74), (s * 1.20, -2.05, 0.70)])
    for nm, p in (('Socket_Propulsion_R', (1.32, -2.30, 0.26)), ('Socket_Propulsion_L', (-1.32, -2.30, 0.26)), ('Socket_Cooling', (0.0, 0.05, 1.14)),
                  ('Socket_Aux', (0.0, -1.05, 1.14))):
        socket('N2_' + nm, p, 0.45)


def nomad_m_gull():
    """N3 M-GULL (Y3): pernas em gaivota invertida com joelhos hover + pontas com placa terminal + quilha central (M)."""
    nomad_core('N3')
    center_keel('N3')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"N3_LegUpper_{sd}", s, (0.78, 0.78), (1.12, 0.32), 2.00, 1.80, 0.10, -0.10, t_root=0.20, t_tip=0.18)
        leg_blade(f"N3_LegOuter_{sd}", s, (1.10, 0.32), (1.62, 0.44), 1.80, 1.30, -0.10, -0.40, t_root=0.18, t_tip=0.12)
        hover_ski(f"N3_KneePlate_{sd}", s * 1.12, -0.05, -1.75, 0.24, w=0.32)
        box(f"N3_Endplate_{sd}", (s * 1.63, -1.10, 0.40), (0.05, 1.00, 0.26), M_STRUCT, bevel=0.01)
        prop_unit('N3_Prop', s, 0.60, -1.70, -3.70, 0.56, 0.56, 0.66)
    for nm, p in (('Socket_Wing_R', (0.80, -0.40, 0.74)), ('Socket_Wing_L', (-0.80, -0.40, 0.74)), ('Socket_Cooling', (0.0, 0.05, 1.14)),
                  ('Socket_Aux', (0.0, -1.05, 1.14))):
        socket('N3_' + nm, p, 0.45)


SHIP, TARGET, VIEW_SCALE = 'NOMAD', '7,4 × 3,3 × 1,45', 1.15
COMMON = ("Mescla A+B no ADN da STRIX: corpo em diamante levantado (sem convés), cabine à frente com cockpit ABERTO (banco, cintos, painel, "
          "defletor) e arco; espinha de serviço com grampos; radiadores nos ombros com grelha; tanque com cintas; quilha central ao chão → de frente M.")
TEXTS = {
    'N1': ("N1 M-ARCH · pernas longas dos ombros até placas hover, quilha central ao chão, propulsores na raiz das pernas. " + COMMON,
           "Construção: quilha central + para-choques → banco + arco → espinha + grampos → radiadores, tanque, tubos → pernas → placas → propulsão.",
           "Força: três apoios, estabilidade máxima em expedição. Fraqueza: massa e velocidade de ponta. Hover: placas das pernas + quilha."),
    'N2': ("N2 M-FEET · pernas traseiras até propulsores junto ao chão (pés), lâminas dianteiras até placas, quilha central ao chão. " + COMMON,
           "Construção: quilha central → banco + arco → espinha → módulos → pernas traseiras com propulsores → lâminas dianteiras com placas.",
           "Força: centro de massa baixo e tração forte. Fraqueza: propulsores expostos. Hover: placas dianteiras + quilha + pés."),
    'N3': ("N3 M-GULL · pernas em gaivota invertida com joelhos hover e placas terminais, quilha central ao chão. " + COMMON,
           "Construção: quilha central → banco + arco → espinha → módulos → pernas superiores → joelhos com placas → pontas → propulsão.",
           "Força: banking estável nas paredes. Fraqueza: joelhos complexos. Hover: joelhos + quilha."),
}
PROPOSALS = [('N1', 'M-ARCH', nomad_m_arch), ('N2', 'M-FEET', nomad_m_feet), ('N3', 'M-GULL', nomad_m_gull)]
main()
