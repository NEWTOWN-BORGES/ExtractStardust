"""
EXTRACT: STARDUST — Naves V2 · NOMAD · Fase A (silhueta / greybox), do zero segundo a Bíblia v1.1.
  blender -b --factory-startup -P nomad_phaseA.py -- <pasta_renders> <ficheiro.blend>

Bíblia: casco longo, refrigeração grande, volumes auxiliares, escotilhas de serviço, tanques e estabilizadores mais
longos — "Dakar futurista"; nariz longo, robusto e reparável. Alvo ~7,4 x 3,3 x 1,45 m.
Distinta da STRIX A·WEDGE (cunha) e da WRAITH C·SKELETON (pod + rails).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
__name__ = 'v2_lib'          # importar só as ferramentas (sem correr o main da STRIX)
exec(compile(open(os.path.join(HERE, 'strix_phaseA.py'), encoding='utf-8').read(), 'strix_phaseA.py', 'exec'), globals())


def grille(name, c, size, axis, slats, mat_open=None):
    """Grelha de radiador: abertura escura com lâminas estruturais (refrigeração ligada à fonte de calor)."""
    box(name + '_Core', c, size, mat_open or M_OPEN, bevel=0.0)
    for k in range(slats):
        t = (k + 0.5) / slats - 0.5
        if axis == 'z':      # lâminas horizontais numa face vertical
            box(f"{name}_Slat{k}", (c[0], c[1], c[2] + t * size[2]), (size[0] * 1.04 + 0.01, size[1] * 1.04 + 0.01, 0.02), M_STRUCT, bevel=0.0)
        else:                # lâminas ao longo de y (tampo)
            box(f"{name}_Slat{k}", (c[0], c[1] + t * size[1], c[2]), (size[0] * 1.04, 0.02, size[2] + 0.02), M_STRUCT, bevel=0.0)


def tank(name, s, x, y0, y1, w, h, z):
    """Tanque auxiliar facetado com cintas de fixação (módulo Aux/Fuel substituível)."""
    pod(name, (s * x, y0), (s * x, y1), (w * 0.8, w, w, w * 0.8), (h * 0.8, h, h, h * 0.8), (z, z, z, z), M_BODY, n=8, chamfer=0.28, top=0.85,
        rake=0.06, intake=False, nozzle=False)
    for k, yy in enumerate(np.linspace(y0 - 0.25, y1 + 0.25, 3)):
        box(f"{name}_Strap{k}", (s * x, yy, z), (w * 1.08, 0.06, h * 1.08), M_STRUCT, bevel=0.008)


def nomad_hauler():
    """A — HAULER: casco longo e robusto com nariz de impacto reparável; cockpit à frente; torre de refrigeração
    dorsal atrás do piloto; tanques auxiliares laterais com cintas; estabilizadores longos; propulsão traseira."""
    ctrl = dict(y=[3.70, 2.90, 1.60, 0.00, -1.60, -2.40], hw=[0.60, 0.84, 0.96, 1.00, 0.96, 0.90], hwb=[0.50, 0.72, 0.84, 0.88, 0.84, 0.80],
                hwt=[0.40, 0.56, 0.64, 0.66, 0.64, 0.60], zb=[0.30, 0.28, 0.27, 0.27, 0.28, 0.28], zc=[0.38, 0.44, 0.50, 0.52, 0.52, 0.52],
                zt=[0.52, 0.66, 0.80, 0.86, 0.86, 0.84])
    facet('A_Hull', ctrl, M_BODY)
    deck = lambda y: float(np.interp(y, ctrl['y'][::-1], ctrl['zt'][::-1]))
    box('A_CrashNose', (0.0, 3.72, 0.40), (1.20, 0.16, 0.20), M_STRUCT)
    cockpit_cut('A_Cockpit', 2.15, 0.95, 0.42, 0.17, deck)
    # torre de refrigeração: carenagem facetada que nasce do tejadilho (não é caixa pousada), sobre trilhos de montagem
    facet('A_CoolingTower', dict(y=[0.62, 0.00, -0.70], hw=[0.40, 0.46, 0.44], hwb=[0.52, 0.58, 0.56], hwt=[0.34, 0.40, 0.38],
                                  zb=[0.80] * 3, zc=[0.92, 0.94, 0.94], zt=[1.34, 1.40, 1.36]), M_BODY, n=8)
    for s in (1, -1):
        box(f"A_TowerMountRail_{'R' if s > 0 else 'L'}", (s * 0.56, -0.05, 0.86), (0.08, 1.40, 0.08), M_STRUCT, bevel=0.01)
    grille('A_TowerGrilleFront', (0.0, 0.625, 1.13), (0.62, 0.02, 0.36), 'z', 5)
    for s in (1, -1):
        grille(f"A_TowerVent_{'R' if s > 0 else 'L'}", (s * 0.455, -0.10, 1.12), (0.02, 0.90, 0.30), 'z', 4)
        tank(f"A_AuxTank_{'R' if s > 0 else 'L'}", s, 1.10, 0.90, -1.50, 0.38, 0.40, 0.56)
        propulsion_block('A', s, 0.56, -1.40, -3.70, 0.62, 0.60, 0.28)
        stab_blade(f"A_Stabilizer_{'R' if s > 0 else 'L'}", s, 0.86, 1.62, -1.90, 1.45, -2.20, 1.05, 0.56, 0.52, 0.20, 0.13, endplate=0.20)
    hover_pads('A', [(0.45, 2.60, 0.28), (-0.45, 2.60, 0.28), (0.45, 0.20, 0.27), (-0.45, 0.20, 0.27), (0.56, -2.60, 0.28), (-0.56, -2.60, 0.28)])


def nomad_spine():
    """B — SPINE: plataforma longa e baixa com uma espinha estrutural de serviço à vista no tejadilho onde os módulos
    estão presos com grampos: cockpit à frente, bancos de radiadores, tanque auxiliar; propulsão traseira."""
    ctrl = dict(y=[3.70, 2.80, 1.20, -0.60, -2.20, -2.90], hw=[0.50, 0.80, 0.94, 0.98, 0.94, 0.88], hwb=[0.40, 0.68, 0.82, 0.86, 0.82, 0.78],
                hwt=[0.30, 0.52, 0.62, 0.64, 0.62, 0.58], zb=[0.30, 0.28, 0.27, 0.27, 0.28, 0.28], zc=[0.36, 0.42, 0.46, 0.48, 0.48, 0.48],
                zt=[0.46, 0.58, 0.66, 0.68, 0.68, 0.66])
    facet('B_Platform', ctrl, M_BODY)
    box('B_ServiceSpine', (0.0, -0.20, 0.76), (0.22, 4.80, 0.14), M_STRUCT)
    for k, yy in enumerate((1.6, 0.6, -0.4, -1.4)):
        box(f"B_SpineClamp{k}", (0.0, yy, 0.78), (0.40, 0.10, 0.20), M_STRUCT, bevel=0.01)
    ctrl_c = dict(y=[2.95, 2.30, 1.40, 1.00], hw=[0.40, 0.56, 0.60, 0.56], hwb=[0.34, 0.48, 0.52, 0.50], hwt=[0.24, 0.36, 0.40, 0.38],
                  zb=[0.58] * 4, zc=[0.62, 0.68, 0.72, 0.72], zt=[0.70, 0.86, 0.94, 0.92])
    facet('B_CockpitModule', ctrl_c, M_BODY, n=8)
    deck = lambda y: float(np.interp(y, ctrl_c['y'][::-1], ctrl_c['zt'][::-1]))
    cockpit_cut('B_Cockpit', 2.55, 1.20, 0.36, 0.16, deck)
    for s in (1, -1):
        box(f"B_RadiatorBank_{'R' if s > 0 else 'L'}", (s * 0.52, 0.0, 0.92), (0.56, 1.30, 0.44), M_BODY, bevel=0.03)
        grille(f"B_RadiatorGrille_{'R' if s > 0 else 'L'}", (s * 0.52, 0.0, 1.145), (0.48, 1.18, 0.02), 'y', 7)
        propulsion_block('B', s, 0.60, -1.50, -3.70, 0.62, 0.58, 0.28)
        stab_blade(f"B_Stabilizer_{'R' if s > 0 else 'L'}", s, 0.90, 1.63, -0.55, 1.40, -0.85, 1.00, 0.46, 0.42, 0.18, 0.12, endplate=0.18)
    tank('B_AuxTank', 1, 0.0, -0.85, -1.85, 0.62, 0.40, 0.92)
    hover_pads('B', [(0.40, 2.70, 0.28), (-0.40, 2.70, 0.28), (0.50, 0.40, 0.27), (-0.50, 0.40, 0.27), (0.60, -2.60, 0.28), (-0.60, -2.60, 0.28)])


def nomad_expedition():
    """C — EXPEDITION: monocoque longo e alto para um NOMAD, com grandes tomadas de radiador nos flancos (grelhas),
    rack de utilidade no tejadilho, placa de proteção sob o nariz e ancas de propulsão integradas."""
    ctrl = dict(y=[3.70, 3.00, 1.60, 0.00, -1.20, -2.20], hw=[0.66, 0.88, 1.00, 1.04, 1.04, 0.98], hwb=[0.56, 0.76, 0.88, 0.92, 0.92, 0.88],
                hwt=[0.42, 0.60, 0.70, 0.72, 0.72, 0.68], zb=[0.31, 0.29, 0.28, 0.28, 0.28, 0.29], zc=[0.40, 0.48, 0.56, 0.58, 0.58, 0.58],
                zt=[0.56, 0.74, 0.92, 0.98, 0.98, 0.94])
    facet('C_Monocoque', ctrl, M_BODY)
    deck = lambda y: float(np.interp(y, ctrl['y'][::-1], ctrl['zt'][::-1]))
    box('C_SkidPlate', (0.0, 3.30, 0.29), (1.10, 0.90, 0.06), M_STRUCT)
    cockpit_cut('C_Cockpit', 1.85, 0.55, 0.44, 0.17, deck)
    for s in (1, -1):
        grille(f"C_SideRadiator_{'R' if s > 0 else 'L'}", (s * 1.035, -0.30, 0.66), (0.02, 1.60, 0.30), 'z', 6)
        box(f"C_ServiceHatch_{'R' if s > 0 else 'L'}", (s * 0.70, 1.00, 0.95), (0.30, 0.70, 0.02), M_STRUCT, bevel=0.0)
        propulsion_block('C', s, 0.62, -1.20, -3.70, 0.66, 0.62, 0.28)
        stab_blade(f"C_Stabilizer_{'R' if s > 0 else 'L'}", s, 0.96, 1.62, -2.05, 1.35, -2.30, 1.00, 0.56, 0.52, 0.19, 0.12, endplate=0.20)
    for k, (x, y) in enumerate(((0.45, -0.10), (-0.45, -0.10), (0.45, -1.10), (-0.45, -1.10))):
        box(f"C_RackPost{k}", (x, y, 1.06), (0.05, 0.05, 0.16), M_STRUCT, bevel=0.0)
    box('C_RackFrame', (0.0, -0.60, 1.15), (1.00, 1.15, 0.05), M_STRUCT, bevel=0.01)
    box('C_UtilityModule', (0.0, -0.60, 1.27), (0.70, 0.80, 0.20), M_BODY, bevel=0.03)
    hover_pads('C', [(0.48, 2.70, 0.29), (-0.48, 2.70, 0.29), (0.55, 0.20, 0.28), (-0.55, 0.20, 0.28), (0.62, -2.60, 0.28), (-0.62, -2.60, 0.28)])


SOCKETS = "Sockets NOMAD (Doc 02): Engine M/L · Propulsion M ×2 · Wings M/L · Armor M · Reactor M/L · Cooling L · Tail M/L · Utility ×2 · Aux/Fuel."
SHIP, TARGET, VIEW_SCALE = 'NOMAD', '7,4 × 3,3 × 1,45', 1.15
TEXTS = {
    'A': ("HAULER · casco longo e robusto com nariz de impacto reparável; cockpit à frente; torre de refrigeração dorsal atrás do piloto "
          "(grelha frontal e respiros); tanques auxiliares laterais com cintas; estabilizadores longos; dois blocos de propulsão traseiros.",
          "Construção: nariz de impacto → célula do cockpit → espinha → torre do reator/radiadores → tanques Aux nas cintas → propulsão → painéis. " + SOCKETS,
          "Força: autonomia e refrigeração enormes. Fraqueza: velocidade de ponta e aceleração. Refrigeração: torre dorsal com ar dinâmico."),
    'B': ("SPINE · plataforma longa e baixa com uma espinha de serviço à vista no tejadilho; os módulos (cockpit, bancos de radiadores, "
          "tanque auxiliar) estão presos à espinha com grampos — leitura de máquina de expedição reparável.",
          "Construção: plataforma/chão hover → espinha de serviço → grampos → módulos (cockpit, radiadores, tanque) → propulsão → estabilizadores. " + SOCKETS,
          "Força: manutenção rápida e módulos visíveis. Fraqueza: módulos expostos a impactos. Refrigeração: radiadores horizontais sobre a espinha."),
    'C': ("EXPEDITION · monocoque longo e mais alto, com grandes radiadores nos flancos (grelhas), escotilhas de serviço, rack de utilidade no "
          "tejadilho e placa de proteção sob o nariz; propulsão integrada nas ancas traseiras.",
          "Construção: placa de proteção + nariz → célula → monocoque → radiadores laterais → rack Utility → ancas de propulsão → painéis. " + SOCKETS,
          "Força: robustez e proteção do piloto. Fraqueza: massa e área frontal. Refrigeração: radiadores laterais grandes alimentados de frente."),
}
PROPOSALS = [('A', 'HAULER', nomad_hauler), ('B', 'SPINE', nomad_spine), ('C', 'EXPEDITION', nomad_expedition)]
main()
