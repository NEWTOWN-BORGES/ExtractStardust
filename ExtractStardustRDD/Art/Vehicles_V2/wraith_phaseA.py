"""
EXTRACT: STARDUST — Naves V2 · WRAITH · Fase A (silhueta / greybox), do zero segundo a Bíblia v1.1.
  blender -b --factory-startup -P wraith_phaseA.py -- <pasta_renders> <ficheiro.blend>

Bíblia: lâmina extremamente estreita e baixa, nariz em lâmina, propulsão compacta, estabilizadores curtos,
estrutura e espaço negativo visíveis; tudo o que não é essencial parece removido. Alvo ~6,5 x 2,4 x 1,10 m.
Tem de ser distinta da STRIX aprovada (A · WEDGE, cunha única com cockpit a meio).
Reutiliza as ferramentas de modelação/render de strix_phaseA.py.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
__name__ = 'v2_lib'          # importar só as ferramentas (sem correr o main da STRIX)
exec(compile(open(os.path.join(HERE, 'strix_phaseA.py'), encoding='utf-8').read(), 'strix_phaseA.py', 'exec'), globals())


def wraith_needle():
    """A — NEEDLE: uma única lâmina estreitíssima; propulsão compacta encostada atrás com a espinha estrutural à
    vista na ranhura entre os blocos; estabilizadores curtos; cockpit recuado e minúsculo."""
    ctrl = dict(y=[3.25, 2.00, 0.50, -0.90, -1.75], hw=[0.05, 0.24, 0.40, 0.46, 0.44], hwb=[0.03, 0.18, 0.32, 0.38, 0.38],
                hwt=[0.02, 0.12, 0.22, 0.26, 0.26], zb=[0.30, 0.27, 0.26, 0.26, 0.27], zc=[0.31, 0.34, 0.39, 0.42, 0.43],
                zt=[0.32, 0.42, 0.56, 0.66, 0.66])
    facet('A_Blade', ctrl, M_BODY)
    deck = lambda y: float(np.interp(y, ctrl['y'][::-1], ctrl['zt'][::-1]))
    cockpit_cut('A_Cockpit', 0.20, -0.95, 0.24, 0.13, deck)
    box('A_Spine', (0.0, -2.45, 0.42), (0.10, 1.60, 0.12), M_STRUCT)
    for s in (1, -1):
        propulsion_block('A', s, 0.30, -1.20, -3.25, 0.40, 0.44, 0.27)
        stab_blade(f"A_Stabilizer_{'R' if s > 0 else 'L'}", s, 0.46, 1.18, -2.20, 0.80, -2.38, 0.55, 0.47, 0.46, 0.14, 0.09, endplate=0.14)
    hover_pads('A', [(0.0, 1.60, 0.27), (0.0, -0.20, 0.26), (0.30, -2.30, 0.27), (-0.30, -2.30, 0.27)], size=(0.30, 0.50, 0.05))


def wraith_fork():
    """B — FORK: duas lâminas compridas em garfo ocupam metade do comprimento com espaço negativo entre elas;
    viga estrutural à vista a unir as pontas; cockpit recuado na junção; propulsão compacta e central."""
    for s in (1, -1):
        ys = np.linspace(3.25, -0.30, 12)
        secs = []
        for y in ys:
            k = (3.25 - y) / 3.55
            xo = s * (0.50 - 0.16 * k)
            secs.append(hexsec(y, 0.06 + 0.12 * k, 0.04 + 0.09 * k, 0.03 + 0.06 * k, 0.30 - 0.03 * k, 0.31 + 0.07 * k, 0.32 + 0.20 * k, xo))
        loft(f"B_ForkBlade_{'R' if s > 0 else 'L'}", secs, M_BODY, bevel=0.008, angle=18)
    box('B_ForkBrace', (0.0, 1.30, 0.40), (0.86, 0.10, 0.08), M_STRUCT)
    ctrl = dict(y=[0.40, -0.40, -1.40, -2.10], hw=[0.40, 0.46, 0.44, 0.38], hwb=[0.32, 0.38, 0.38, 0.32], hwt=[0.22, 0.28, 0.28, 0.24],
                zb=[0.27, 0.26, 0.26, 0.27], zc=[0.38, 0.42, 0.43, 0.43], zt=[0.52, 0.66, 0.68, 0.64])
    facet('B_CockpitPod', ctrl, M_BODY, n=10)
    deck = lambda y: float(np.interp(y, ctrl['y'][::-1], ctrl['zt'][::-1]))
    cockpit_cut('B_Cockpit', 0.05, -1.15, 0.26, 0.14, deck)
    for s in (1, -1):
        propulsion_block('B', s, 0.24, -1.60, -3.25, 0.36, 0.42, 0.27)
        stab_blade(f"B_Stabilizer_{'R' if s > 0 else 'L'}", s, 0.40, 1.18, -2.35, 0.72, -2.50, 0.50, 0.46, 0.45, 0.13, 0.08, endplate=0.13)
    hover_pads('B', [(0.42, 2.10, 0.29), (-0.42, 2.10, 0.29), (0.0, -0.60, 0.26), (0.24, -2.50, 0.27), (-0.24, -2.50, 0.27)], size=(0.24, 0.46, 0.05))


def wraith_skeleton():
    """C — SKELETON (linguagem R14): pod de cockpit esguio ao centro e dois rails-lâmina exteriores ligados por
    escoras estruturais à vista; muito espaço negativo; propulsão compacta na ponta traseira dos rails."""
    ctrl = dict(y=[2.90, 1.80, 0.60, -0.60, -1.70], hw=[0.06, 0.24, 0.34, 0.34, 0.26], hwb=[0.04, 0.18, 0.28, 0.28, 0.22],
                hwt=[0.03, 0.12, 0.18, 0.18, 0.14], zb=[0.30, 0.27, 0.26, 0.26, 0.28], zc=[0.31, 0.35, 0.40, 0.42, 0.42],
                zt=[0.33, 0.46, 0.60, 0.64, 0.58])
    facet('C_CockpitPod', ctrl, M_BODY)
    deck = lambda y: float(np.interp(y, ctrl['y'][::-1], ctrl['zt'][::-1]))
    cockpit_cut('C_Cockpit', 1.15, 0.00, 0.22, 0.13, deck)
    box('C_ReactorCore', (0.0, -2.05, 0.46), (0.36, 0.70, 0.26), M_STRUCT)
    for s in (1, -1):
        rail = dict(y=[3.25, 1.50, -0.80], hw=[0.05, 0.12, 0.16], hwb=[0.03, 0.09, 0.12], hwt=[0.02, 0.07, 0.09],
                    zb=[0.30, 0.28, 0.27], zc=[0.31, 0.35, 0.38], zt=[0.32, 0.42, 0.50])
        facet(f"C_BladeRail_{'R' if s > 0 else 'L'}", rail, M_BODY, n=10, xo=s * 0.82)
        for y, z in ((1.40, 0.40), (-0.40, 0.44)):
            box(f"C_Strut_{'R' if s > 0 else 'L'}_{y}", (s * 0.56, y, z), (0.50, 0.10, 0.07), M_STRUCT, bevel=0.01)
        box(f"C_RearStrut_{'R' if s > 0 else 'L'}", (s * 0.48, -2.05, 0.46), (0.62, 0.12, 0.08), M_STRUCT, bevel=0.01)
        propulsion_block('C', s, 0.82, -0.80, -3.25, 0.38, 0.42, 0.27)
        stab_blade(f"C_Stabilizer_{'R' if s > 0 else 'L'}", s, 1.00, 1.19, -1.70, 0.70, -1.80, 0.55, 0.46, 0.45, 0.12, 0.08, endplate=0.12)
    hover_pads('C', [(0.0, 1.70, 0.27), (0.0, -0.40, 0.26), (0.82, -2.30, 0.27), (-0.82, -2.30, 0.27), (0.82, 0.60, 0.27), (-0.82, 0.60, 0.27)],
               size=(0.22, 0.44, 0.05))


SHIP, TARGET = 'WRAITH', '6,5 × 2,4 × 1,10'
TEXTS = {
    'A': ("NEEDLE · uma única lâmina estreitíssima e muito baixa, com nariz em agulha plana. A propulsão compacta encosta atrás e deixa "
          "a espinha estrutural à vista na ranhura entre os blocos; estabilizadores curtos com placa terminal; cockpit minúsculo e recuado.",
          "Construção: espinha (à vista atrás) → célula do cockpit → blocos de propulsão compactos → hover sob a lâmina → painéis mínimos.",
          "Força: área frontal mínima e agilidade. Fraqueza: casco fino, pouca proteção. Refrigeração: scoops laterais curtos dos blocos."),
    'B': ("FORK · duas lâminas compridas em garfo à frente, com espaço negativo até ao cockpit e uma viga estrutural à vista a unir as pontas. "
          "Cockpit recuado na junção; propulsão compacta e central; estabilizadores curtos.",
          "Construção: duas lâminas de impacto + viga de ligação → célula do cockpit na junção → reator → blocos compactos → painéis.",
          "Força: silhueta agressiva e leve na frente. Fraqueza: lâminas expostas, linha de skill exigente. Refrigeração: scoops dos blocos."),
    'C': ("SKELETON · linguagem R14. Pod de cockpit esguio ao centro e dois rails-lâmina exteriores ligados por escoras estruturais à vista: "
          "muito espaço negativo. A propulsão compacta fica na ponta traseira dos rails; o reator fica exposto na travessa traseira.",
          "Construção: pod do cockpit + dois rails → escoras e travessa do reator → blocos de propulsão nos rails → hover nos rails e no pod.",
          "Força: modular e leve, módulos muito acessíveis. Fraqueza: estrutura exposta a impactos laterais. Refrigeração: reator ao ar livre e scoops."),
}
PROPOSALS = [('A', 'NEEDLE', wraith_needle), ('B', 'FORK', wraith_fork), ('C', 'SKELETON', wraith_skeleton)]
main()
