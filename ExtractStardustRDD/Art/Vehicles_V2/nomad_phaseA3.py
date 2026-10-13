"""
EXTRACT: STARDUST — Naves V2 · NOMAD · mescla aprovada pelo utilizador: A HAULER + B SPINE, mais vestida.
  blender -b --factory-startup -P nomad_phaseA3.py -- <pasta_renders> <ficheiro.blend>

Da A: cabine à frente em chapa com arco de proteção e conduta de ar dinâmico. Da B: plataforma hover e espinha em
treliça com módulos presos por grampos. Vestir (Bíblia §2: carroceria cobre 70-85%, 15-30% de estrutura à vista em zonas
técnicas): saias laterais em chapa, tampa dorsal da espinha em dois troços, grelhas de lâminas sobre os radiadores,
deck traseiro com grelha sobre o reator, carenagens nos blocos; tanques com cintas e frame traseiro ficam à vista.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_MAIN, RUN_MAIN2 = False, False
exec(compile(open(os.path.join(HERE, 'nomad_phaseA2.py'), encoding='utf-8').read(), 'nomad_phaseA2.py', 'exec'), globals())


def skirt(name, y0, y1, s, x_bot, x_top, z_bot, z_top, n=6):
    """Saia lateral em chapa (painel inclinado) entre a plataforma e a linha de cintura."""
    secs = [[(s * x_bot, y, z_bot), (s * x_top, y, z_top)] for y in np.linspace(y0, y1, n)]
    return strip(name, secs, M_BODY)


def gable(name, y0, y1, hw, z_edge, z_ridge, n=5):
    """Tampa dorsal em duas águas sobre a espinha (painel em chapa)."""
    secs = [[(hw, y, z_edge), (0.0, y, z_ridge), (-hw, y, z_edge)] for y in np.linspace(y0, y1, n)]
    return strip(name, secs, M_BODY)


def louvers(name, c, along, length, height, count, s=1):
    """Grelha de lâminas inclinadas sobre um radiador (a refrigeração lê-se, o núcleo fica protegido)."""
    c = np.array(c, float)
    for k in range(count):
        t = (k + 0.5) / count - 0.5
        p = c + np.array([0, t * length, 0]) if along == 'y' else c + np.array([t * length, 0, 0])
        box(f"{name}_{k}", p, (0.03, length / count * 0.62, height) if along == 'y' else (length / count * 0.62, 0.03, height), M_STRUCT, bevel=0.0)


def nomad_merge():
    global BODY
    # base B: plataforma hover com saias de borda
    floor = [(-0.72, 3.60), (0.72, 3.60), (1.05, 2.60), (1.08, -2.60), (0.95, -3.45), (-0.95, -3.45), (-1.08, -2.60), (-1.05, 2.60)]
    slab('M_HoverPlatform', floor, 0.24, 0.34, M_STRUCT, bevel=0.03)
    box('M_SkidPlate', (0.0, 3.25, 0.23), (1.05, 0.80, 0.04), M_STRUCT)
    box('M_CrashBumper', (0.0, 3.66, 0.42), (1.20, 0.12, 0.18), M_STRUCT)
    # A: cabine à frente em chapa, canopy, arco de proteção e barra de topo
    BODY = dict(y=[3.62, 2.90, 1.70, 0.62], hw=[0.62, 0.86, 0.98, 1.00], hwb=[0.56, 0.78, 0.90, 0.92], hwt=[0.40, 0.58, 0.66, 0.66],
                zb=[0.34] * 4, zc=[0.42, 0.48, 0.54, 0.56], zt=[0.56, 0.74, 0.94, 0.98])
    # cockpit ABERTO (sem escotilha): tejadilho da cabine interrompido; banco de competição com cintos, volante, painel
    panels('M_Cab', 3.60, 0.64, top=False, belly=False, n=9)
    panels('M_CabFrontDeck', 3.60, 2.30, sides=False, belly=False, n=5)
    panels('M_CabRearDeck', 1.02, 0.64, sides=False, belly=False, n=3)
    slab('M_CockpitFloor', [(-0.62, 2.28), (0.62, 2.28), (0.66, 1.04), (-0.66, 1.04)], 0.40, 0.43, M_STRUCT, bevel=0.006)
    box('M_SeatBase', (0.0, 1.42, 0.52), (0.48, 0.52, 0.14), M_MECH, bevel=0.04)
    box('M_SeatBack', (0.0, 1.16, 0.78), (0.48, 0.10, 0.52), M_MECH, bevel=0.04)
    box('M_Headrest', (0.0, 1.13, 1.08), (0.30, 0.10, 0.16), M_MECH, bevel=0.03)
    for q in (-1, 1):
        box(f"M_SeatBolster_{q}", (q * 0.26, 1.36, 0.70), (0.06, 0.62, 0.36), M_MECH, bevel=0.02)
        box(f"M_HarnessStrap_{q}", (q * 0.10, 1.22, 0.84), (0.05, 0.02, 0.44), M_CABLE, bevel=0.0)
    box('M_HarnessLap', (0.0, 1.40, 0.62), (0.40, 0.04, 0.04), M_CABLE, bevel=0.0)
    box('M_Dashboard', (0.0, 2.10, 0.74), (0.86, 0.22, 0.16), M_MECH, bevel=0.02)
    tube('M_SteeringColumn', (0.0, 2.05, 0.74), (0.0, 1.78, 0.80), 0.022, M_STRUCT)
    box('M_SteeringYoke', (0.0, 1.76, 0.81), (0.34, 0.04, 0.10), M_MECH, bevel=0.01)
    slab('M_WindDeflector', [(-0.50, 2.28), (0.50, 2.28), (0.42, 2.20), (-0.42, 2.20)], 0.80, 1.02, M_GLASS, bevel=0.003)
    hoop('M_RollHoop', 0.86, 0.84, 0.62, 1.24)
    tube('M_CageTopBar', (0.0, 0.86, 1.24), (0.0, 1.75, 1.02), 0.03, M_STRUCT)
    pipe('M_RamAirDuct', [(0.0, 1.20, 1.00), (0.0, 0.70, 1.18), (0.0, 0.30, 1.20)], 0.08, M_MECH, clamps=True)
    # B: espinha em treliça (zona técnica à vista entre os troços da tampa dorsal)
    ys = np.linspace(0.60, -2.80, 7)
    for s in (1, -1):
        for a, b in zip(ys, ys[1:]):
            tube(f"M_TrussTop_{s}_{a:.2f}", (s * 0.18, a, 1.00), (s * 0.18, b, 1.00), 0.026, M_STRUCT)
            tube(f"M_TrussBot_{s}_{a:.2f}", (s * 0.18, a, 0.40), (s * 0.18, b, 0.40), 0.026, M_STRUCT)
            tube(f"M_TrussWeb_{s}_{a:.2f}", (s * 0.18, a, 0.40), (s * 0.18, b, 1.00), 0.018, M_STRUCT)
    for y in ys:
        for s in (1, -1):
            tube(f"M_TrussPost_{s}_{y:.2f}", (s * 0.18, y, 0.40), (s * 0.18, y, 1.00), 0.02, M_STRUCT)
    for k, y in enumerate((0.25, -0.62, -1.50, -2.35)):
        box(f"M_ModuleClamp{k}", (0.0, y, 1.04), (0.44, 0.10, 0.08), M_MECH, bevel=0.01)
    # vestir: tampa dorsal em dois troços (fresta mostra o grampo e a treliça), saias laterais em chapa
    gable('M_DorsalCover_F', 0.58, -0.50, 0.34, 1.02, 1.12)
    gable('M_DorsalCover_R', -0.74, -1.40, 0.34, 1.02, 1.10)
    for s in (1, -1):
        sd = 'R' if s > 0 else 'L'
        skirt(f"M_SideSkirt_{sd}", 0.62, -1.95, s, 1.04, 1.00, 0.36, 0.62)
        # radiadores laterais (B) com grelha de lâminas por cima, alimentados pela conduta do tejadilho
        radiator(f"M_Radiator_{sd}", (s * 0.58, 0.05, 0.84), (0.48, 1.10, 0.34))
        louvers(f"M_RadLouver_{sd}", (s * 0.83, 0.05, 0.84), 'y', 1.10, 0.30, 9)
        tube(f"M_RadArm_{sd}", (s * 0.18, 0.05, 0.88), (s * 0.34, 0.05, 0.88), 0.03, M_STRUCT)
        # tanques Aux com cintas (A) à vista por cima da saia — zona técnica de serviço
        tank(f"M_AuxTank_{sd}", (s * 0.66, -1.20, 0.80), 0.40, 1.05, 0.36)
        # propulsão e frame traseiro à vista
        prop_unit('M_Prop', s, 0.62, -2.00, -3.70, 0.64, 0.60, 0.32)
        tube(f"M_RearFrameArm_{sd}", (s * 0.18, -2.05, 0.40), (s * 0.92, -2.30, 0.36), 0.03, M_STRUCT)
        tube(f"M_RearFrameDiag_{sd}", (s * 0.18, -2.80, 0.40), (s * 0.92, -3.25, 0.36), 0.026, M_STRUCT)
        pipe(f"M_Coolant_{sd}", [(s * 0.40, -0.55, 0.80), (s * 0.24, -1.20, 0.70), (s * 0.20, -1.75, 0.62)], 0.022, M_COOL, clamps=True)
        harness(f"M_Harness_{sd}", [(s * 0.20, -2.30, 0.66), (s * 0.40, -2.42, 0.64), (s * 0.50, -2.60, 0.68)])
    # reator sob o deck traseiro com grelha (o glow só se vê pelas lâminas)
    cage('M_ReactorFrame', -0.17, 0.17, -1.62, -2.42, 0.42, 0.92, 0.022, M_STRUCT)
    loft('M_ReactorCore', [hexsec(y, 0.12, 0.09, 0.09, 0.48, 0.64, 0.86) for y in (-1.72, -2.32)], M_CORE, bevel=0.01)
    slab('M_RearDeck', [(-0.34, -1.55), (0.34, -1.55), (0.34, -2.50), (-0.34, -2.50)], 1.00, 1.02, M_BODY, bevel=0.004)
    louvers('M_RearDeckGrille', (0.0, -2.02, 1.03), 'x', 0.56, 0.02, 7)
    tank('M_TopAuxTank', (0.0, -0.95, 1.30), 0.52, 0.80, 0.30)
    long_stabilizers('M', 1.08, -0.55, 0.44)
    hover_units('M', [(0.50, 2.80, 0.24), (-0.50, 2.80, 0.24), (0.55, 0.30, 0.24), (-0.55, 0.30, 0.24), (0.62, -2.60, 0.24), (-0.62, -2.60, 0.24)])
    for nm, p in (('Socket_Utility', (0.0, 3.30, 0.60)), ('Socket_Cooling', (0.0, 0.05, 1.05)), ('Socket_Aux_Top', (0.0, -0.95, 1.10)),
                  ('Socket_Reactor', (0.0, -2.02, 0.40)), ('Socket_Engine', (0.0, -2.95, 0.44)), ('Socket_Aux_R', (0.66, -1.20, 0.58)),
                  ('Socket_Aux_L', (-0.66, -1.20, 0.58))):
        socket('M_' + nm, p, 0.5)


SHIP, TARGET, VIEW_SCALE = 'NOMAD', '7,4 × 3,3 × 1,45', 1.15
TEXTS = {
    'M': ("MESCLA A+B · cabine à frente em chapa com cockpit aberto (banco, cintos, volante) e arco de proteção (A) sobre a plataforma hover com espinha em treliça e módulos presos "
          "por grampos (B). Vestida: saias laterais, tampa dorsal em dois troços, grelhas de lâminas nos radiadores, deck traseiro com grelha "
          "sobre o reator e carenagens nos blocos; tanques com cintas e frame traseiro à vista nas zonas técnicas.",
          "Construção: plataforma hover + placa de proteção → célula + arco → treliça → grampos → radiadores, tanques, reator → propulsão no frame → painéis. " + SOCKETS_TXT,
          "Força: autonomia, refrigeração e manutenção rápida. Fraqueza: massa e aceleração. Refrigeração: conduta do tejadilho → radiadores laterais → tubos até ao reator."),
}
PROPOSALS = [('M', 'HAULER+SPINE', nomad_merge)]
main()
