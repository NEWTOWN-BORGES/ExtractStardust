"""
EXTRACT: STARDUST — Naves V2 · BASTION (Heavy Survival) no ADN da família: corpo em diamante levantado, mas curto, largo e
blindado. De frente lê-se W: perna interior desce do ombro até à placa hover e um ombro blindado sobe dali para fora.
Cockpit fechado e protegido (vidro baixo com grelha de blindagem), nariz curto e grosso, propulsão protegida, pouco vazio.
~6,4 x 3,8 x 1,55 m.
  blender -b --factory-startup -P bastion_v1.py -- <pasta_renders> <ficheiro.blend>
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_MAIN, RUN_MAIN2, RUN_V3 = False, False, False
exec(compile(open(os.path.join(HERE, 'strix_v3.py'), encoding='utf-8').read(), 'strix_v3.py', 'exec'), globals())

BODY_B = dict(y=[3.20, 2.60, 1.60, 0.20, -1.40, -2.60], hw=[0.60, 0.82, 0.94, 0.98, 0.94, 0.82], hwb=[0.28, 0.30, 0.32, 0.34, 0.32, 0.30],
              hwt=[0.40, 0.52, 0.60, 0.62, 0.60, 0.52], zb=[0.50, 0.42, 0.40, 0.40, 0.42, 0.46], zc=[0.62, 0.70, 0.76, 0.78, 0.78, 0.78],
              zt=[0.80, 1.06, 1.22, 1.28, 1.26, 1.16])


def armor_plates(prefix, spans, t=0.07):
    """Blindagem pesada no dorso: placas grossas sobrepostas (cada uma pisa a seguinte), com parafusos de fixação."""
    for k, (ya, yb) in enumerate(spans):
        ha, hb = B('hwt', ya) * 0.94, B('hwt', yb) * 0.94
        z0 = max(B('zt', ya), B('zt', yb)) + 0.005 + (len(spans) - k) * 0.012
        slab(f"{prefix}_TopArmor{k}", [(-ha, ya), (ha, ya), (hb, yb), (-hb, yb)], z0, z0 + t, M_BODY, bevel=0.012)
        for q in (-1, 1):
            box(f"{prefix}_TopArmorBolt{k}_{q}", (q * ha * 0.80, ya - 0.10, z0 + t + 0.008), (0.05, 0.05, 0.02), M_MECH, bevel=0.004)


def bastion_core(prefix):
    """Corpo comum: diamante curto e largo, cockpit fechado com grelha, nariz-aríete com sensores, blindagem do dorso."""
    diamond_body(prefix + '_Body', BODY_B, cockpit=(1.80, 0.50))
    cockpit_cut(prefix + '_Canopy', 1.76, 0.54, 0.62, 0.15, lambda y: B('zt', y))
    for k, y in enumerate((1.50, 1.15, 0.80)):
        box(f"{prefix}_VisorSlat{k}", (0.0, y, B('zt', y) + 0.13), (1.10, 0.07, 0.05), M_STRUCT, bevel=0.008)
    box(prefix + '_VisorSpine', (0.0, 1.15, B('zt', 1.15) + 0.15), (0.08, 1.20, 0.05), M_STRUCT, bevel=0.008)
    for q in (-1, 1):
        box(f"{prefix}_CockpitRail_{q}", (q * 0.64, 1.15, B('zt', 1.15) + 0.04), (0.08, 1.40, 0.12), M_STRUCT, bevel=0.01)
        box(f"{prefix}_Sensor_{q}", (q * 0.50, 3.00, 0.84), (0.24, 0.34, 0.14), M_MECH, bevel=0.02)
        box(f"{prefix}_SensorLens_{q}", (q * 0.50, 3.17, 0.84), (0.16, 0.02, 0.08), M_GLASS, bevel=0.0)
    slab(prefix + '_RamPlate', [(-0.78, 3.36), (0.78, 3.36), (0.94, 3.04), (-0.94, 3.04)], 0.42, 0.70, M_STRUCT, bevel=0.03)
    box(prefix + '_CrushBox', (0.0, 3.20, 0.56), (0.70, 0.24, 0.18), M_MECH, bevel=0.01)
    armor_plates(prefix, [(0.42, -0.62), (-0.52, -1.52), (-1.42, -2.42)])


def prop_cowl(prefix, x0, x1, y0, y1, z):
    """Capota blindada por cima da propulsão + saias laterais (propulsão protegida) com grelhas de calor."""
    slab(prefix + '_PropCowl', [(-x1, y0), (x1, y0), (x1, y1), (-x1, y1)], z, z + 0.08, M_BODY, bevel=0.015)
    for k in range(5):
        box(f"{prefix}_CowlVent{k}", (0.0, y0 - 0.20 - k * (y0 - y1 - 0.4) / 4, z + 0.09), (x1 * 1.2, 0.05, 0.02), M_STRUCT, bevel=0.0)
    for q in (-1, 1):
        slab(f"{prefix}_PropSkirt_{q}", [(q * x0, y0), (q * x1, y0), (q * x1, y1), (q * x0, y1)], z - 0.46, z, M_BODY, bevel=0.015)


def bastion_rampart():
    """B1 W-RAMPART: pernas largas e grossas (paredes) até ao fundo do W, ombros blindados contínuos a subir para fora;
    duas placas hover por lado; propulsão dupla dentro da cauda, debaixo de capota blindada."""
    bastion_core('B1')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"B1_Leg_{sd}", s, (0.88, 0.74), (1.30, 0.30), 3.40, 3.00, 1.70, 1.50, t_root=0.26, t_tip=0.22)
        leg_blade(f"B1_Shoulder_{sd}", s, (1.30, 0.34), (1.86, 0.94), 3.00, 2.60, 1.50, 1.30, t_root=0.24, t_tip=0.18)
        box(f"B1_ShoulderCap_{sd}", (s * 1.87, 0.0, 0.98), (0.12, 2.50, 0.10), M_STRUCT, bevel=0.015)
        box(f"B1_KneeBeam_{sd}", (s * 1.30, 0.05, 0.36), (0.16, 3.00, 0.12), M_STRUCT, bevel=0.015)
        hover_ski(f"B1_PlateF_{sd}", s * 1.30, 1.40, 0.10, 0.24, w=0.40)
        hover_ski(f"B1_PlateR_{sd}", s * 1.30, -0.30, -1.60, 0.24, w=0.40)
        prop_unit('B1_Prop', s, 0.42, -1.70, -3.20, 0.62, 0.56, 0.48)
        harness(f"B1_Harness_{sd}", [(s * 0.20, -1.50, 1.10), (s * 0.60, -1.40, 0.98), (s * 1.00, -1.20, 0.80)])
    prop_cowl('B1', 0.76, 0.86, -1.80, -3.00, 1.08)
    for nm, p in (('Socket_Armor_Secondary_R', (1.60, 0.0, 0.74)), ('Socket_Armor_Secondary_L', (-1.60, 0.0, 0.74)),
                  ('Socket_Propulsion', (0.0, -2.40, 1.20)), ('Socket_Cooling', (0.0, -0.90, 1.40))):
        socket('B1_' + nm, p, 0.45)


def bastion_pods():
    """B2 W-PODS: pernas interiores médias até à placa; escoras curtas sobem até casulos laterais blindados (ombros densos)
    que guardam a propulsão lá dentro — frente facetada de blindagem, bocais atrás."""
    bastion_core('B2')
    pod_ctrl = dict(y=[1.50, 0.90, -0.40], hw=[0.10, 0.22, 0.23], hwb=[0.08, 0.16, 0.17], hwt=[0.06, 0.16, 0.17],
                    zb=[0.56, 0.50, 0.50], zc=[0.66, 0.72, 0.74], zt=[0.74, 0.96, 1.00])
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"B2_Leg_{sd}", s, (0.88, 0.74), (1.24, 0.30), 2.60, 2.20, 1.30, 1.00, t_root=0.24, t_tip=0.20)
        leg_blade(f"B2_Strut_{sd}", s, (1.26, 0.32), (1.54, 0.66), 2.00, 1.80, 0.60, 0.40, t_root=0.20, t_tip=0.18)
        facet(f"B2_ArmorPod_{sd}", pod_ctrl, M_BODY, n=8, xo=s * 1.68)
        prop_unit('B2_Prop', s, 1.68, -0.40, -3.20, 0.44, 0.50, 0.50)
        box(f"B2_PodRail_{sd}", (s * 1.68, -0.90, 1.04), (0.16, 3.80, 0.06), M_STRUCT, bevel=0.01)
        hover_ski(f"B2_Plate_{sd}", s * 1.25, 0.95, -0.35, 0.24, w=0.40)
        harness(f"B2_Harness_{sd}", [(s * 0.70, -1.20, 0.90), (s * 1.10, -1.00, 0.80), (s * 1.48, -0.90, 0.78)])
    radiator('B2_TailRadiator', (0.0, -2.00, 1.30), (0.80, 0.80, 0.18))
    hover_units('B2', [(0.0, -1.90, 0.40)], size=(0.36, 0.60))
    for nm, p in (('Socket_Armor_Secondary_R', (1.68, 0.90, 1.02)), ('Socket_Armor_Secondary_L', (-1.68, 0.90, 1.02)),
                  ('Socket_Propulsion_R', (1.68, -2.20, 1.04)), ('Socket_Propulsion_L', (-1.68, -2.20, 1.04)), ('Socket_Cooling', (0.0, -2.00, 1.42))):
        socket('B2_' + nm, p, 0.45)


def bastion_crab():
    """B3 W-CRAB: quatro pernas curtas e grossas (frente e trás) até placas; um guarda-lamas blindado contínuo sobe para
    fora a todo o comprimento (carapaça); viga inferior liga as pernas; propulsão dupla na cauda sob capota."""
    bastion_core('B3')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"B3_LegF_{sd}", s, (0.84, 0.70), (1.28, 0.30), 1.20, 1.00, 2.20, 2.00, t_root=0.24, t_tip=0.20)
        leg_blade(f"B3_LegR_{sd}", s, (0.88, 0.74), (1.30, 0.30), 1.40, 1.20, -0.60, -0.80, t_root=0.24, t_tip=0.20)
        leg_blade(f"B3_Fender_{sd}", s, (1.30, 0.34), (1.84, 0.86), 4.20, 3.80, 2.20, 2.00, t_root=0.20, t_tip=0.16)
        box(f"B3_FenderCap_{sd}", (s * 1.85, 0.10, 0.90), (0.12, 3.70, 0.10), M_STRUCT, bevel=0.015)
        box(f"B3_LowerBeam_{sd}", (s * 1.30, 0.10, 0.36), (0.16, 4.00, 0.12), M_STRUCT, bevel=0.015)
        hover_ski(f"B3_PlateF_{sd}", s * 1.30, 2.10, 0.90, 0.24, w=0.40)
        hover_ski(f"B3_PlateR_{sd}", s * 1.30, -0.70, -1.95, 0.24, w=0.40)
        prop_unit('B3_Prop', s, 0.40, -1.80, -3.20, 0.58, 0.54, 0.50)
        harness(f"B3_Harness_{sd}", [(s * 0.30, -1.60, 1.10), (s * 0.70, -1.30, 0.96), (s * 1.10, -1.10, 0.74)])
    prop_cowl('B3', 0.70, 0.80, -1.90, -3.05, 1.08)
    for nm, p in (('Socket_Armor_Secondary_R', (1.60, 0.10, 0.70)), ('Socket_Armor_Secondary_L', (-1.60, 0.10, 0.70)),
                  ('Socket_Propulsion', (0.0, -2.40, 1.20)), ('Socket_Cooling', (0.0, -0.90, 1.40))):
        socket('B3_' + nm, p, 0.45)


SHIP, TARGET, VIEW_SCALE = 'BASTION', '6,4 × 3,8 × 1,55', 1.12
COMMON = ("Heavy Survival: corpo em diamante curto e largo; cockpit FECHADO com vidro baixo e grelha de blindagem; nariz-aríete curto e "
          "grosso com sensores; blindagem pesada sobreposta no dorso; propulsão protegida; pouco espaço vazio. De frente lê-se W.")
TEXTS = {
    'B1': ("B1 W-RAMPART · pernas largas e grossas como paredes até ao fundo do W, ombros blindados contínuos a subir para fora, duas placas "
           "hover por lado, propulsão dupla na cauda sob capota blindada. " + COMMON,
           "Construção: quilha → célula fechada → aríete → pernas-parede + viga do joelho → ombros → placas → propulsão → capota → blindagem.",
           "Força: massa e proteção máximas, empurra sem perder linha. Fraqueza: aceleração. Hover: 4 placas no fundo do W."),
    'B2': ("B2 W-PODS · pernas interiores até às placas, escoras curtas até casulos laterais blindados que guardam a propulsão lá dentro "
           "(ombros densos, bocais atrás); radiador na cauda. " + COMMON,
           "Construção: quilha → célula fechada → aríete → pernas → escoras → casulos blindados com propulsão → placas → radiador.",
           "Força: propulsão larga e protegida, estável nas paredes. Fraqueza: largura máxima. Hover: placas + emissor central."),
    'B3': ("B3 W-CRAB · quatro pernas curtas e grossas (frente e trás) até placas, guarda-lamas blindado contínuo a todo o comprimento "
           "(carapaça), viga inferior a ligar as pernas, propulsão dupla na cauda sob capota. " + COMMON,
           "Construção: quilha → célula fechada → aríete → pernas frente/trás + viga → carapaça → placas → propulsão → capota.",
           "Força: aguenta impactos laterais (carapaça). Fraqueza: peso. Hover: 4 placas sob as pernas."),
}
PROPOSALS = [('B1', 'W-RAMPART', bastion_rampart), ('B2', 'W-PODS', bastion_pods), ('B3', 'W-CRAB', bastion_crab)]
main()
