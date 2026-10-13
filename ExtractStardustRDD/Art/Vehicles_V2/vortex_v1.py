"""
EXTRACT: STARDUST — Naves V2 · VORTEX (Burst Propulsion) no ADN da família: corpo em diamante que engorda para trás
(massa traseira), três zonas de propulsão com espaço vazio entre elas, entradas de ar grandes e grelhas de calor.
De frente lê-se X: pernas descem até às placas hover e braços sobem para fora até à propulsão/entradas.
~6,8 x 3,4 x 1,30 m.
  blender -b --factory-startup -P vortex_v1.py -- <pasta_renders> <ficheiro.blend>
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_MAIN, RUN_MAIN2, RUN_V3 = False, False, False
exec(compile(open(os.path.join(HERE, 'strix_v3.py'), encoding='utf-8').read(), 'strix_v3.py', 'exec'), globals())

BODY_V = dict(y=[3.40, 2.40, 1.00, -0.40, -1.60, -2.60], hw=[0.06, 0.36, 0.56, 0.70, 0.80, 0.78], hwb=[0.03, 0.10, 0.16, 0.20, 0.24, 0.24],
              hwt=[0.04, 0.20, 0.30, 0.38, 0.44, 0.42], zb=[0.50, 0.42, 0.38, 0.38, 0.40, 0.42], zc=[0.52, 0.58, 0.62, 0.66, 0.70, 0.72],
              zt=[0.54, 0.70, 0.84, 0.92, 0.98, 0.96])


def heat_vents(prefix, y0, y1, n=7):
    """Grelha de calor no dorso: lâminas inclinadas numa moldura (o calor da propulsão sai por cima)."""
    hw = B('hwt', (y0 + y1) / 2) * 0.80
    for k in range(n):
        y = y0 - (y0 - y1) * (k + 0.5) / n
        box(f"{prefix}_HeatVent{k}", (0.0, y, B('zt', y) + 0.035), (hw * 1.6, (y0 - y1) / n * 0.55, 0.03), M_STRUCT, bevel=0.0)
    for q in (-1, 1):
        box(f"{prefix}_VentFrame_{q}", (q * hw, (y0 + y1) / 2, B('zt', (y0 + y1) / 2) + 0.04), (0.05, y0 - y1, 0.05), M_STRUCT, bevel=0.006)


def big_intake(name, s, x, y0, y1, z, w, h):
    """Entrada de ar grande com lábio inclinado e separador de pó (alimenta a propulsão lá atrás)."""
    pod(name, (s * x, y0), (s * x, y1), (w * 0.75, w, w), (h * 0.70, h, h), (z, z, z), M_BODY, n=6, chamfer=0.16, top=0.80, rake=0.30, nozzle=False)
    box(name + '_Splitter', (s * x, y0 - 0.05, z), (0.03, 0.20, h * 0.9), M_STRUCT, bevel=0.0)


def vortex_core(prefix, cockpit=(1.70, 0.40)):
    diamond_body(prefix + '_Body', BODY_V, cockpit=cockpit)
    cockpit_cut(prefix + '_Canopy', cockpit[0] - 0.04, cockpit[1] + 0.04, 0.30, 0.13, lambda y: B('zt', y))
    hoop(prefix + '_RollHoop', cockpit[1] - 0.05, 0.30, 0.86, 1.06, r=0.026)
    heat_vents(prefix, -0.90, -2.30)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        prop_unit(prefix + '_Core', s, 0.30, -1.80, -3.40, 0.50, 0.50, 0.46)
        harness(f"{prefix}_Harness_{sd}", [(s * 0.10, -0.80, 0.98), (s * 0.30, -1.30, 1.00), (s * 0.34, -1.80, 0.98)])
    box(prefix + '_CoreGap', (0.0, -2.70, 0.70), (0.06, 1.20, 0.40), M_STRUCT, bevel=0.0)


def vortex_arms():
    """V1 X-ARMS (de cima Y): pernas da frente até placas; braços varridos para trás sobem até dois propulsores exteriores
    no alto; propulsão central dupla na cauda; entradas grandes nos flancos sob as raízes dos braços."""
    vortex_core('V1')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"V1_Leg_{sd}", s, (0.62, 0.62), (1.30, 0.26), 1.60, 1.20, 1.20, 0.80, t_root=0.16, t_tip=0.12)
        hover_ski(f"V1_Plate_{sd}", s * 1.32, 1.00, -0.30, 0.24, w=0.30)
        leg_blade(f"V1_Arm_{sd}", s, (0.50, 0.90), (1.36, 1.14), 1.80, 1.40, -0.40, -1.20, t_root=0.16, t_tip=0.14)
        prop_unit('V1_Outer', s, 1.42, -1.00, -3.40, 0.40, 0.38, 0.92)
        big_intake(f"V1_Intake_{sd}", s, 0.80, 0.50, -0.90, 0.62, 0.30, 0.34)
    hover_units('V1', [(0.0, -2.00, 0.38)], size=(0.30, 0.60))
    for nm, p in (('Socket_Propulsion_R', (1.42, -2.20, 1.32)), ('Socket_Propulsion_L', (-1.42, -2.20, 1.32)), ('Socket_Propulsion_C', (0.0, -2.60, 0.98)),
                  ('Socket_Cooling', (0.0, -1.60, 1.04))):
        socket('V1_' + nm, p, 0.40)


def vortex_boom():
    """V2 V-BOOM (de cima V): duas vigas saem do nariz e abrem para trás e para cima até aos propulsores exteriores — o V
    deixa vazio entre vigas e corpo; pernas descem das vigas até às placas; propulsão central dupla na cauda."""
    vortex_core('V2')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        pod(f"V2_Boom_{sd}", (s * 0.40, 2.00), (s * 1.38, -1.10), (0.10, 0.16, 0.18), (0.12, 0.16, 0.18), (0.76, 0.96, 1.10), M_BODY,
            n=10, chamfer=0.20, top=0.70, rake=0.0, intake=False, nozzle=False)
        prop_unit('V2_Outer', s, 1.42, -1.00, -3.40, 0.40, 0.38, 0.92)
        leg_blade(f"V2_Leg_{sd}", s, (0.95, 0.92), (1.34, 0.26), 1.10, 1.00, 0.10, -0.10, t_root=0.14, t_tip=0.12)
        hover_ski(f"V2_Plate_{sd}", s * 1.36, 0.30, -0.95, 0.24, w=0.30)
        tube(f"V2_CrossTie_{sd}", (s * 0.70, -0.60, 0.84), (s * 1.20, -0.70, 1.00), 0.028, M_STRUCT)
        big_intake(f"V2_Intake_{sd}", s, 1.42, -0.20, -1.05, 1.11, 0.28, 0.30)
    hover_units('V2', [(0.0, 1.80, 0.42), (0.0, -2.00, 0.38)], size=(0.24, 0.50))
    for nm, p in (('Socket_Propulsion_R', (1.42, -2.20, 1.32)), ('Socket_Propulsion_L', (-1.42, -2.20, 1.32)), ('Socket_Propulsion_C', (0.0, -2.60, 0.98)),
                  ('Socket_Cooling', (0.0, -1.60, 1.04))):
        socket('V2_' + nm, p, 0.40)


def vortex_intake():
    """V3 X-INTAKE: braços curtos sobem até duas entradas gigantes (os traços de cima do X) com condutas à vista até à
    propulsão central; pernas traseiras descem até dois propulsores junto ao chão (pés); lâminas dianteiras até placas."""
    vortex_core('V3')
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"V3_Arm_{sd}", s, (0.50, 0.88), (1.05, 1.08), 1.10, 0.90, 0.40, 0.20, t_root=0.14, t_tip=0.12)
        big_intake(f"V3_Intake_{sd}", s, 1.12, 0.45, -0.75, 1.06, 0.40, 0.42)
        pipe(f"V3_Duct_{sd}", [(s * 1.12, -0.75, 1.06), (s * 0.80, -1.30, 1.02), (s * 0.40, -1.80, 0.98)], 0.07, M_MECH, clamps=True)
        leg_blade(f"V3_RearLeg_{sd}", s, (0.66, 0.66), (1.30, 0.56), 1.40, 1.20, -1.20, -1.40, t_root=0.16, t_tip=0.14)
        prop_unit('V3_Foot', s, 1.36, -0.90, -3.20, 0.44, 0.44, 0.22)
        leg_blade(f"V3_FrontLeg_{sd}", s, (0.48, 0.60), (1.04, 0.26), 0.90, 0.70, 2.10, 1.90, t_root=0.12, t_tip=0.10)
        hover_ski(f"V3_Plate_{sd}", s * 1.06, 2.00, 0.80, 0.24, w=0.28)
    for nm, p in (('Socket_Propulsion_R', (1.36, -2.20, 0.68)), ('Socket_Propulsion_L', (-1.36, -2.20, 0.68)), ('Socket_Propulsion_C', (0.0, -2.60, 0.98)),
                  ('Socket_Intake_R', (1.12, 0.0, 1.30)), ('Socket_Intake_L', (-1.12, 0.0, 1.30))):
        socket('V3_' + nm, p, 0.40)


SHIP, TARGET, VIEW_SCALE = 'VORTEX', '6,8 × 3,4 × 1,30', 1.10
COMMON = ("Burst Propulsion: corpo em diamante que engorda para trás (massa traseira); três zonas de propulsão separadas por vazio; "
          "entradas de ar grandes; grelha de calor no dorso; cockpit baixo fechado com arco. De frente lê-se X.")
TEXTS = {
    'V1': ("V1 X-ARMS · de cima Y: pernas da frente até placas, braços varridos para trás sobem até dois propulsores exteriores no alto, "
           "propulsão central dupla, entradas grandes nos flancos. " + COMMON,
           "Construção: quilha → célula + arco → propulsão central → braços + propulsores exteriores → entradas → pernas → placas → grelhas.",
           "Força: aceleração brutal (3 zonas). Fraqueza: calor e propulsores altos expostos. Hover: placas da frente + emissor traseiro."),
    'V2': ("V2 V-BOOM · de cima V: duas vigas saem do nariz e abrem para trás e para cima até aos propulsores exteriores, com vazio entre "
           "vigas e corpo; pernas descem das vigas até às placas; propulsão central dupla. " + COMMON,
           "Construção: quilha → célula → vigas do nariz → propulsores exteriores + entradas → pernas + tirantes → placas → propulsão central.",
           "Força: silhueta única, rígida em torção. Fraqueza: vigas expostas a impactos. Hover: placas + emissores no nariz e cauda."),
    'V3': ("V3 X-INTAKE · braços curtos sobem até duas entradas gigantes com condutas à vista até à propulsão central; pernas traseiras "
           "descem até propulsores junto ao chão (pés); lâminas dianteiras até placas. " + COMMON,
           "Construção: quilha → célula → propulsão central → braços + entradas + condutas → pernas traseiras + pés → lâminas + placas.",
           "Força: muito ar = burst longo. Fraqueza: entradas grandes sujas de pó. Hover: placas da frente + pés."),
}
PROPOSALS = [('V1', 'X-ARMS', vortex_arms), ('V2', 'V-BOOM', vortex_boom), ('V3', 'X-INTAKE', vortex_intake)]
main()
