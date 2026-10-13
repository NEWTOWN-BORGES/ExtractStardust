"""
EXTRACT: STARDUST — Naves V2 · STRIX · 3.ª linguagem: Y INVERTIDO (⅄) — nada de cara de barco.
  blender -b --factory-startup -P strix_v3.py -- <pasta_renders> <ficheiro.blend>

Regras novas (feedback do utilizador): o corpo NÃO é um casco com convés. Fica levantado do chão, com secção em
diamante (quilha estreita, ombros largos, tejadilho estreito). Os estabilizadores descem dos ombros até perto do chão e
terminam em esquis/emissores hover: vista de frente = Y invertido. Construção à vista (longarinas, escoras, chapas, sockets).
STRIX (Bíblia): cunha limpa e equilibrada, cockpit central, dois propulsores separados, estabilizadores médios. ~6,2 x 3,0 x 1,25 m.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_MAIN, RUN_MAIN2 = False, False
exec(compile(open(os.path.join(HERE, 'nomad_phaseA2.py'), encoding='utf-8').read(), 'nomad_phaseA2.py', 'exec'), globals())


def diamond_body(prefix, ctrl, n=10, cockpit=None):
    """Fuselagem em diamante feita de chapas: tejadilho, ombros e quilha (separados, com folgas). Nada de convés."""
    global BODY
    BODY = ctrl
    y0, y1 = ctrl['y'][0], ctrl['y'][-1]
    if cockpit:
        panels(prefix + '_Front', y0, cockpit[0] + 0.02, n=max(4, n // 2))
        panels(prefix + '_Cockpit', cockpit[0] - 0.02, cockpit[1] + 0.02, top=False, n=6)
        panels(prefix + '_Rear', cockpit[1] - 0.02, y1, n=max(4, n // 2))
    else:
        panels(prefix + '_Body', y0, y1, n=n)
    # tampas de fecho das pontas (nariz e cauda) para o corpo não ficar oco à vista
    loft(prefix + '_NoseCap', [sec(y0 + 0.0), [(x * 0.2, y0 + 0.04, z) for x, _, z in sec(y0)]], M_BODY, bevel=0.0)


def leg_blade(name, s, root, tip, c_root, c_tip, le_root, le_tip, t_root=0.18, t_tip=0.11, n=6):
    """Estabilizador-perna: desce do ombro do corpo até perto do chão (anédrico forte) — o braço do Y invertido."""
    root, tip = np.array([s * root[0], root[1]], float), np.array([s * tip[0], tip[1]], float)   # (x, z)
    d = (tip - root) / np.linalg.norm(tip - root)
    nrm = np.array([-d[1], d[0]])
    if nrm[1] < 0:
        nrm = -nrm
    secs = []
    for t in np.linspace(0, 1, n):
        p = root + (tip - root) * t
        c, le, th = c_root + (c_tip - c_root) * t, le_root + (le_tip - le_root) * t, t_root + (t_tip - t_root) * t
        prof = [(0.0, 0.10), (-0.30, 0.50), (-1.0, 0.18), (-1.0, -0.32), (-0.35, -0.50), (0.0, -0.15)]
        secs.append([(p[0] + nrm[0] * v * th, le + u * c, p[1] + nrm[1] * v * th) for u, v in prof])
    if s < 0:
        secs = [list(reversed(q)) for q in secs]
    loft(name, secs, M_BODY, bevel=0.01, angle=18)
    # longarina estrutural à vista na raiz + junta de articulação
    tube(name + '_RootSpar', (root[0], le_root - c_root * 0.45, root[1]), (root[0] + (tip[0] - root[0]) * 0.25, le_root - c_root * 0.45, root[1] + (tip[1] - root[1]) * 0.25), 0.035, M_STRUCT)
    box(name + '_RootClamp', (root[0], le_root - c_root * 0.45, root[1]), (0.10, c_root * 0.7, 0.16), M_STRUCT, bevel=0.01)


def hover_ski(name, x, y0, y1, z, w=0.30, h=0.16):
    """Esqui hover na ponta da perna: corpo baixo com emissores por baixo e sensor de superfície à frente."""
    pod(name, (x, y0), (x, y1), (w * 0.6, w, w, w * 0.8), (h * 0.6, h, h, h * 0.8), (z, z, z, z), M_MECH, n=8, chamfer=0.25, top=0.8,
        rake=0.10, intake=False, nozzle=False)
    for k, yy in enumerate(np.linspace(y0 - 0.35, y1 + 0.35, 3)):
        box(f"{name}_Emitter{k}", (x, yy, z - h / 2 - 0.02), (w * 0.8, 0.42, 0.03), M_HOVER, bevel=0.006)
    box(name + '_Sensor', (x, y0 + 0.02, z), (0.06, 0.05, 0.05), M_SOCK, bevel=0.006)


STRIX_CTRL = dict(y=[3.10, 2.30, 1.10, -0.20, -1.40, -2.20], hw=[0.06, 0.40, 0.62, 0.66, 0.60, 0.46], hwb=[0.03, 0.12, 0.18, 0.20, 0.18, 0.14],
                  hwt=[0.04, 0.22, 0.32, 0.34, 0.30, 0.24], zb=[0.58, 0.46, 0.42, 0.42, 0.44, 0.48], zc=[0.60, 0.62, 0.64, 0.66, 0.66, 0.66],
                  zt=[0.62, 0.78, 0.90, 0.94, 0.92, 0.86])


def strix_y_arch():
    """Y1 ARCH: corpo-diamante levantado; duas pernas longas descem dos ombros até esquis hover que correm quase todo o
    comprimento; propulsores na raiz das pernas, atrás; escora diagonal à vista entre a quilha e cada perna."""
    diamond_body('Y1_Fuselage', STRIX_CTRL, cockpit=(1.05, -0.25))
    cockpit_cut('Y1_Canopy', 1.02, -0.22, 0.30, 0.14, lambda y: B('zt', y))
    hoop('Y1_RollHoop', -0.30, 0.30, 0.86, 1.10, r=0.028)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"Y1_Leg_{sd}", s, (0.58, 0.68), (1.36, 0.30), 2.0, 1.6, 0.70, 0.50)
        hover_ski(f"Y1_Ski_{sd}", s * 1.40, 0.95, -2.75, 0.26)
        tube(f"Y1_KeelStrut_{sd}", (s * 0.16, -0.40, 0.44), (s * 1.00, -0.60, 0.46), 0.03, M_STRUCT)
        prop_unit('Y1_Prop', s, 0.62, -1.20, -3.10, 0.50, 0.50, 0.70)
        harness(f"Y1_Harness_{sd}", [(s * 0.10, -1.60, 0.70), (s * 0.30, -1.70, 0.86), (s * 0.45, -1.90, 0.92)])
    cage('Y1_ReactorFrame', -0.16, 0.16, -1.30, -2.00, 0.48, 0.84, 0.02, M_STRUCT)
    hover_units('Y1', [(0.0, 1.60, 0.40), (0.0, -0.50, 0.40)], size=(0.24, 0.50))
    for nm, p in (('Socket_Wing_R', (0.62, 0.0, 0.66)), ('Socket_Wing_L', (-0.62, 0.0, 0.66)), ('Socket_Reactor', (0.0, -1.65, 0.46))):
        socket('Y1_' + nm, p, 0.4)


def strix_y_feet():
    """Y2 FEET: as pernas traseiras descem até aos dois propulsores, que ficam junto ao chão como 'pés'; à frente, duas
    lâminas pequenas descem do nariz até emissores hover (⅄ também à frente); reator exposto entre as pernas."""
    ctrl = dict(STRIX_CTRL)
    ctrl['y'] = [3.10, 2.30, 1.10, -0.20, -1.10, -1.70]
    diamond_body('Y2_Fuselage', ctrl, cockpit=(1.05, -0.25))
    cockpit_cut('Y2_Canopy', 1.02, -0.22, 0.30, 0.14, lambda y: B('zt', y))
    hoop('Y2_RollHoop', -0.30, 0.30, 0.86, 1.10, r=0.028)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"Y2_RearLeg_{sd}", s, (0.50, 0.72), (1.08, 0.62), 1.30, 1.10, -0.70, -0.85, t_root=0.16, t_tip=0.14)
        prop_unit('Y2_Prop', s, 1.10, -0.40, -3.10, 0.56, 0.54, 0.30)
        leg_blade(f"Y2_FrontLeg_{sd}", s, (0.34, 0.56), (0.80, 0.28), 0.80, 0.55, 2.20, 2.00, t_root=0.12, t_tip=0.09)
        box(f"Y2_FrontEmitter_{sd}", (s * 0.82, 1.75, 0.24), (0.28, 0.46, 0.05), M_HOVER, bevel=0.008)
        tube(f"Y2_LegStrut_{sd}", (s * 0.12, -1.20, 0.46), (s * 0.86, -1.70, 0.40), 0.03, M_STRUCT)
        harness(f"Y2_Harness_{sd}", [(s * 0.10, -1.55, 0.66), (s * 0.40, -1.70, 0.70), (s * 0.85, -1.75, 0.66)])
    cage('Y2_ReactorFrame', -0.20, 0.20, -1.55, -2.35, 0.46, 0.86, 0.022, M_STRUCT)
    loft('Y2_ReactorCore', [hexsec(y, 0.13, 0.10, 0.10, 0.52, 0.66, 0.80) for y in (-1.65, -2.25)], M_CORE, bevel=0.01)
    hover_units('Y2', [(0.0, 0.40, 0.40)], size=(0.24, 0.60))
    for nm, p in (('Socket_Propulsion_R', (1.10, -1.60, 0.84)), ('Socket_Propulsion_L', (-1.10, -1.60, 0.84)), ('Socket_Reactor', (0.0, -1.95, 0.44))):
        socket('Y2_' + nm, p, 0.4)


def strix_y_gull():
    """Y3 GULL: pernas em 'asa de gaivota invertida' — descem a pique do ombro até um joelho junto ao chão e depois abrem
    para fora; o joelho leva o emissor hover e a placa terminal; propulsores no corpo, por cima das pernas."""
    diamond_body('Y3_Fuselage', STRIX_CTRL, cockpit=(1.05, -0.25))
    cockpit_cut('Y3_Canopy', 1.02, -0.22, 0.30, 0.14, lambda y: B('zt', y))
    hoop('Y3_RollHoop', -0.30, 0.30, 0.86, 1.10, r=0.028)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        leg_blade(f"Y3_LegUpper_{sd}", s, (0.56, 0.70), (0.92, 0.32), 1.60, 1.40, -0.30, -0.45, t_root=0.18, t_tip=0.16)
        leg_blade(f"Y3_LegOuter_{sd}", s, (0.90, 0.32), (1.46, 0.42), 1.40, 1.00, -0.45, -0.70, t_root=0.16, t_tip=0.10)
        box(f"Y3_KneeEmitter_{sd}", (s * 0.92, -1.15, 0.22), (0.30, 1.20, 0.05), M_HOVER, bevel=0.008)
        box(f"Y3_KneeJoint_{sd}", (s * 0.92, -1.15, 0.33), (0.14, 1.10, 0.12), M_STRUCT, bevel=0.012)
        box(f"Y3_Endplate_{sd}", (s * 1.47, -1.20, 0.34), (0.05, 0.85, 0.24), M_STRUCT, bevel=0.01)
        prop_unit('Y3_Prop', s, 0.48, -1.10, -3.10, 0.46, 0.48, 0.66)
    cage('Y3_ReactorFrame', -0.18, 0.18, -1.35, -2.05, 0.46, 0.80, 0.02, M_STRUCT)
    hover_units('Y3', [(0.0, 1.70, 0.42)], size=(0.24, 0.50))
    for nm, p in (('Socket_Wing_R', (0.62, -0.95, 0.66)), ('Socket_Wing_L', (-0.62, -0.95, 0.66)), ('Socket_Engine', (0.0, -2.60, 0.62))):
        socket('Y3_' + nm, p, 0.4)


SHIP, TARGET, VIEW_SCALE = 'STRIX', '6,2 × 3,0 × 1,25', 1.0
TEXTS = {
    'Y1': ("Y1 ARCH · corpo em diamante levantado do chão (sem convés); duas pernas longas descem dos ombros até esquis hover que "
           "correm quase todo o comprimento — de frente lê-se um Y invertido. Propulsores na raiz das pernas; escoras à vista da quilha às pernas.",
           "Construção: quilha + rails → célula com arco → reator na gaiola → raízes das pernas (longarina + grampo) → pernas → esquis hover → chapas.",
           "Força: estabilidade e leitura fortíssima de frente. Fraqueza: pernas longas expostas em zonas estreitas. Hover: esquis + emissores na quilha."),
    'Y2': ("Y2 FEET · as pernas traseiras descem até aos propulsores, que ficam junto ao chão como pés; à frente, duas lâminas pequenas descem do "
           "nariz até emissores hover — Y invertido à frente e atrás. Reator exposto entre as pernas.",
           "Construção: quilha → célula → reator → pernas traseiras com propulsores nos pés → lâminas dianteiras com emissores → escoras → chapas.",
           "Força: propulsão baixa e estável, centro de massa baixo. Fraqueza: propulsores mais expostos a impactos. Hover: emissores nas lâminas e na quilha."),
    'Y3': ("Y3 GULL · pernas em 'gaivota invertida': descem a pique do ombro até um joelho junto ao chão (emissor hover e junta estrutural) e "
           "depois abrem para fora até à placa terminal. Propulsores no corpo, por cima das pernas.",
           "Construção: quilha → célula → reator → pernas superiores → joelhos com emissores → pernas exteriores com placas terminais → chapas.",
           "Força: silhueta mais agressiva e banking forte. Fraqueza: mecanismo do joelho mais complexo. Hover: emissores nos joelhos e na quilha."),
}
PROPOSALS = [('Y1', 'ARCH', strix_y_arch), ('Y2', 'FEET', strix_y_feet), ('Y3', 'GULL', strix_y_gull)]
if globals().get('RUN_V3', True):
    main()
