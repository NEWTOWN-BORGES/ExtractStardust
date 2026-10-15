"""
EXTRACT: STARDUST — Expedição 01 RED DUST DIVIDE (Doc 01 §16-19): gera red_dust_divide.json.

  python make_red_dust_divide.py        (depois: python ../Blender/rdd_plan.py red_dust_divide.json)

Nove setores pela ordem e ritmo do documento (~20 min), com as referências reais (NPS) reinterpretadas:
  1 THE BASIN       bacia de slickrock abaixo do planalto, grelha 5×4, ondulações, esses e flow jumps
  2 BROKEN MESA     subida por lajes partidas até ao topo da mesa; 1.ª bifurcação (rota baixa SAFE / lajes RACING)
  3 SHAFER FALL     descida em switchbacks pela falésia (Shafer Trail: ~457 m) até à bancada White Rim
  4 THE RED WALL    curva de ~3 km e 200° na parede de Wingate, bank 8° → 50°; atalho SKILL por salto
  5 HORSESHOE DROP  ferradura de 270° (Horseshoe Bend); SAFE pela borda exterior, SKILL pelo terraço interior + drop
  6 THE WASH        leito seco em half-pipe com meandros, centro com rocha caída, gargalo e bacia natural
  7 ARCHES RUN      subida do desfiladeiro até aos fins; arcos, corredores entre fins, slalom de agulhas, saltos
  8 THE HOLLOW      caverna: entrada ampla, curva, descida, bank, half-pipe, câmara com pilar (bifurcação), salto de saída
  9 WHITE RIM       bancada aberta à escala de Canyonlands, garganta do rio ao lado, hero jump e EXTRAÇÃO

Curvas por ângulo (turn: raio com sinal, + = direita) e altitudes por objetivo (to_y): o integrador calcula a
inclinação. Com esta física, as curvas ≥ 184 m fazem-se a fundo; as técnicas usam 100-130 m (travar ou derrapar).
"""
import json
import math
import os

SEG, MARK, SECTORS = [], {}, []
pos = 0.0


def seg(sid, length, **kw):
    global pos
    # a inclinação calculada para um objetivo de altitude (to_y) não deve continuar nos troços seguintes
    if SEG and 'to_y' in SEG[-1] and 'to_y' not in kw and 'slope' not in kw:
        kw['slope'] = 0.0
    SEG.append(dict(id=sid, len=round(length), **kw))
    pos += round(length)


def turn(sid, radius, deg, **kw):
    """Curva com o ângulo total pedido (o comprimento sai do raio)."""
    seg(sid, abs(radius) * math.radians(deg), radius=radius, **kw)


def mark(name):
    MARK[name] = pos


def sector(name):
    if SECTORS:
        SECTORS[-1]['to'] = pos
    SECTORS.append({'id': name, 'from': pos, 'to': None})


def crest(prefix, base=0.0, up=4.0, down=-3.0):
    """Flow jump natural: laje que sobe e borda viva de ≤ 7° (Doc 01 §17.7)."""
    seg(f"{prefix} crista", 140, ease=60, slope=base + up)
    seg(f"{prefix} borda", 220, ease=12, slope=base + down)
    seg(f"{prefix} receção", 380, ease=200, slope=base)


def canyon_jump(prefix, base=0.0, lip=4.0, gap=48, land=-8.0):
    """Canyon jump sobre uma ravina, com receção inclinada a acompanhar a trajetória (validado no laboratório)."""
    seg(f"{prefix} borda", 90, ease=40, slope=base + lip)
    seg(f"{prefix} ravina", gap, ease=0, slope=base - 3.6, gap=1)
    seg(f"{prefix} receção", 220, ease=40, slope=base + land, gap=0)
    seg(f"{prefix} nivelar", 320, ease=220, slope=base)


def esses(prefix, r=110.0, deg=65.0, bank=10.0, width=None):
    """Esses técnicos (obrigam a travar: ~200 km/h a 110 m de raio)."""
    kw = {} if width is None else {'width': width}
    turn(f"{prefix} esquerda", -r, deg, ease=120, bank=-bank, **kw)
    turn(f"{prefix} direita", r, deg, ease=120, bank=bank)
    seg(f"{prefix} saída", 300, ease=150, radius=0, bank=0)


OPEN = dict(open=1, wallL=3, wallR=3, filletL=14, filletR=14, angleL=22, angleR=22, rideL=0.4, rideR=0.4)
CANYON = dict(open=0, apron=0, wallL=8, wallR=8, filletL=12, filletR=12, angleL=40, angleR=40, lipL=6, lipR=6, rideL=0.3, rideR=0.3)
HALFPIPE = dict(open=0, apron=0, wallL=30, wallR=30, filletL=26, filletR=26, angleL=66, angleR=66, rideL=0.8, rideR=0.8)
FINS = dict(wallL=22, wallR=22, filletL=8, filletR=8, angleL=82, angleR=82, rideL=0.4, rideR=0.4)

# ---------------------------------------------------------------- 1 THE BASIN (0:00-2:00)
sector("THE BASIN")
seg("1 Bacia · grelha 5x4", 600, ease=0, width=56, surface="sand", apron=260, **OPEN)
turn("1 Bacia · saída larga", 2400, 25, ease=500, width=48)
seg("1 Bacia · planície", 900, ease=400, radius=0)
turn("1 Bacia · ondulações de slickrock", -1700, 45, ease=500, width=44, surface="slickrock")
crest("1 Laje 1")
esses("1 Esses da bacia", width=36)
mark("basin_rockfall_from")
turn("1 Campo de lajes caídas", 900, 40, ease=300, width=40)
mark("basin_rockfall_to")
turn("1 Curva cega", -220, 70, ease=200, bank=-10, width=36)
turn("1 Mega arco", 1600, 70, ease=500, width=40, surface="sand", bank=0)
crest("1 Laje 2")
turn("1 Curva rápida", -900, 50, ease=400, width=38)
esses("1 Esses de saída", r=130, deg=55, bank=10)
seg("1 Corredor de saída", 1000, ease=300, radius=0, width=36, apron=60)

# ---------------------------------------------------------------- 2 BROKEN MESA (2:00-4:00)
sector("BROKEN MESA")
mark("mesa_fork_from")
seg("2 Lajes partidas · subida", 1300, ease=300, to_y=285, width=34, surface="slickrock")
crest("2 Laje", base=1.0, up=5.0, down=-2.5)
turn("2 Gancho técnico direita", 120, 75, ease=120, bank=14, width=30, to_y=292)
mark("mesa_rockfall_from")
turn("2 Lajes · degraus", -1000, 55, ease=300, width=32, bank=0, to_y=312)
mark("mesa_rockfall_to")
crest("2 Laje alta", base=1.0, up=5.0, down=-2.5)
turn("2 Gancho técnico esquerda", -115, 80, ease=120, bank=-14, width=30, to_y=322)
mark("mesa_fork_to")
seg("2 Topo da mesa", 1300, ease=400, to_y=335, bank=0, width=36, apron=120)
esses("2 Esses do topo", r=115, deg=60)
crest("2 Laje do topo", base=0.0, up=5.0, down=-3.0)
turn("2 Gancho do topo", 125, 120, ease=150, bank=16, width=32)
turn("2 Borda do Shafer · vista", -1200, 120, ease=400, width=34, to_y=335, bank=0)

# ---------------------------------------------------------------- 3 SHAFER FALL (4:00-6:00)
sector("SHAFER FALL")
y = 328.0
seg("3 Borda · início da descida", 500, ease=200, to_y=y, width=34, apron=0, **OPEN)
for k in range(11):
    y -= 22.0
    seg(f"3 Perna {k + 1}", 450, ease=150, to_y=y, radius=0, bank=0, width=30)
    if k < 10:
        side = 1 if k % 2 == 0 else -1
        y -= 3.0
        turn(f"3 Gancho {k + 1}", 100 * side, 180, ease=80, to_y=y, bank=16 * side, width=34)
seg("3 Base do Shafer · White Rim", 800, ease=300, to_y=50, radius=0, bank=0, width=32, **CANYON)

# ---------------------------------------------------------------- 4 THE RED WALL (6:00-9:00)
sector("THE RED WALL")
mark("arch_wall_canyon")
seg("4 Canyon de aproximação", 1200, ease=400, to_y=48, width=30)
esses("4 S técnico", r=110, deg=70, bank=12, width=26)
seg("4 Reta do canyon", 600, ease=200, width=30)
mark("wall_rockfall_from")
turn("4 Rocha caída", -1200, 35, ease=300, width=32)
mark("wall_rockfall_to")
seg("4 Gargalo", 700, ease=200, radius=0, width=16, wallL=14, wallR=14, angleL=70, angleR=70, rideL=0.4, rideR=0.4)
seg("4 Abre", 400, ease=300, width=32, wallL=8, wallR=8, angleL=40, angleR=40, rideL=0.3, rideR=0.3)
mark("needles_from")
seg("4 Canyon das agulhas", 1400, ease=300, width=36, radius=0)
mark("needles_to")
esses("4 S antes da parede", r=140, deg=60, bank=14, width=32)
seg("4 Abre para a parede", 400, ease=300, width=32)
turn("4 Red Wall · entrada 8°", 1400, 25, ease=600, bank=8, width=34, wallL=25, filletL=20, angleL=55, rideL=0.6)
turn("4 Red Wall · 15°", 1100, 40, ease=500, bank=15, wallL=40, angleL=62, rideL=0.75)
turn("4 Red Wall · 25°", 850, 45, ease=500, bank=25, wallL=50, angleL=68, rideL=0.85)
mark("wall_skill_from")
turn("4 Red Wall · 35°", 700, 45, ease=400, bank=35, wallL=58, angleL=72, rideL=0.9)
turn("4 Red Wall · 50°", 600, 45, ease=400, bank=50, wallL=60, angleL=74, rideL=0.92)
seg("4 Saída da parede", 700, ease=600, radius=0, bank=0, wallL=8, filletL=12, angleL=40, rideL=0.3, width=30)
mark("wall_skill_to")
turn("4 Gancho de saída", -120, 100, ease=150, bank=-16, width=30)
seg("4 Antes da ravina", 600, ease=200, radius=0, bank=0)
canyon_jump("4 Canyon jump")
turn("4 Canyon médio", -700, 60, ease=400, to_y=40, width=30)
seg("4 Segundo gargalo", 600, ease=200, radius=0, width=18, wallL=16, wallR=16, angleL=72, angleR=72, rideL=0.4, rideR=0.4)
esses("4 Esses do gargalo", r=115, deg=70, bank=14, width=24)
seg("4 Canyon largo", 800, ease=300, width=34, wallL=8, wallR=8, angleL=40, angleR=40, rideL=0.3, rideR=0.3)
turn("4 Curva rápida do canyon", 500, 70, ease=400, bank=10)
seg("4 Reta para o desfiladeiro", 1200, ease=300, radius=0, bank=0, to_y=35)

# ---------------------------------------------------------------- 5 HORSESHOE DROP (9:00-11:00)
sector("HORSESHOE DROP")
seg("5 Descida ao desfiladeiro", 2600, ease=400, to_y=15, width=32)
esses("5 Esses da descida", r=130, deg=60, bank=12)
turn("5 Viragem de entrada", 300, 90, ease=200, bank=10, to_y=5)
mark("shoe_from")
turn("5 Ferradura 270°", -850, 270, ease=400, bank=-10, to_y=-25, width=34, wallR=20, angleR=55, rideR=0.6)
mark("shoe_to")
turn("5 Viragem de saída", 300, 90, ease=300, bank=10, to_y=-30, wallR=8, angleR=40, rideR=0.3)
seg("5 Fundo do desfiladeiro", 900, ease=300, radius=0, bank=0)
turn("5 Meia ferradura", -260, 150, ease=250, bank=-18, width=32)
turn("5 Contra-curva", 400, 60, ease=300, bank=10)
seg("5 Saída do desfiladeiro", 800, ease=300, radius=0, bank=0)

# ---------------------------------------------------------------- 6 THE WASH (11:00-14:00)
sector("THE WASH")
seg("6 Entrada do wash", 600, ease=400, to_y=-32, width=44, surface="sand", **HALFPIPE)
turn("6 Meandro 1", 420, 60, ease=300, bank=8)
turn("6 Meandro 2 (parede esq. alta)", -380, 110, ease=300, bank=-8, wallL=40)
mark("wash_rockfall_from")
seg("6 Centro congestionado", 1200, ease=300, radius=0, bank=0, width=50, wallL=30)
mark("wash_rockfall_to")
turn("6 Meandro 3 (parede dir. alta)", 450, 100, ease=300, bank=8, wallR=45, angleR=72)
seg("6 Gargalo do wash", 600, ease=200, radius=0, bank=0, width=22, wallL=20, wallR=20, angleL=75, angleR=75)
turn("6 Cotovelo apertado", -160, 85, ease=150, bank=-20, width=40, wallL=30, wallR=30, angleL=66, angleR=66)
turn("6 Meandro 4", 420, 100, ease=300, bank=8, width=46)
crest("6 Laje do leito", base=-0.2)
mark("wash_wreck")
turn("6 Meandro 5", -400, 100, ease=300, bank=-8)
turn("6 Cotovelo 2", 160, 80, ease=150, bank=20)
seg("6 Bacia natural", 700, ease=300, width=90, wallL=12, wallR=12, filletL=30, filletR=30, angleL=40, angleR=40,
    rideL=0.5, rideR=0.5, radius=0, bank=0)
seg("6 Wash inferior · entrada", 500, ease=400, width=40, **HALFPIPE)
turn("6 Meandro 6", -300, 120, ease=250, bank=-12)
turn("6 Meandro 7", 300, 120, ease=250, bank=12)
mark("wash2_rockfall_from")
seg("6 Leito de cascalho", 900, ease=300, radius=0, bank=0, surface="gravel")
mark("wash2_rockfall_to")
turn("6 Cotovelo 3", -150, 90, ease=150, bank=-20, surface="sand")
turn("6 Meandro 8", 350, 110, ease=250, bank=10)
turn("6 Meandro 9", -420, 100, ease=300, bank=-8)
seg("6 Gargalo inferior", 500, ease=200, radius=0, bank=0, width=20, wallL=22, wallR=22, angleL=76, angleR=76)
turn("6 Cotovelo 4", 140, 95, ease=150, bank=22, width=36, wallL=30, wallR=30, angleL=66, angleR=66)
turn("6 Meandro 10", -380, 110, ease=300, bank=-10, width=44)
crest("6 Laje do leito 2", base=-0.2)
turn("6 Meandro 11", 450, 80, ease=300, bank=8)
seg("6 Saída do wash", 600, ease=300, radius=0, bank=0, to_y=-45)

# ---------------------------------------------------------------- 7 ARCHES RUN (14:00-16:00)
sector("ARCHES RUN")
seg("7 Subida do desfiladeiro 1", 1500, ease=400, to_y=40, width=30, **CANYON)
turn("7 Gancho da subida", -120, 80, ease=120, bank=-14, to_y=46)
seg("7 Subida do desfiladeiro 2", 1500, ease=400, to_y=130, bank=0, radius=0)
turn("7 Gancho da subida 2", 120, 80, ease=120, bank=14, to_y=136)
seg("7 Saída para os fins", 700, ease=300, to_y=168, bank=0, radius=0)
mark("arch_1")
seg("7 Corredor de fins 1", 1000, ease=300, to_y=170, width=24, **FINS)
mark("arches_slalom_from")
seg("7 Slalom de agulhas", 1300, ease=300, width=34, wallL=6, wallR=6, angleL=40, angleR=40, rideL=0.3, rideR=0.3)
mark("arches_slalom_to")
mark("arch_2")
turn("7 Corredor de fins 2", 300, 90, ease=300, width=22, **FINS)
canyon_jump("7 Salto pequeno", gap=30, lip=3.0, land=-5.0)
turn("7 Gancho entre fins", -130, 110, ease=150, bank=-14, width=26, **FINS)
mark("arches_slalom2_from")
seg("7 Slalom 2", 1100, ease=300, width=34, radius=0, bank=0, wallL=6, wallR=6, angleL=40, angleR=40, rideL=0.3, rideR=0.3)
mark("arches_slalom2_to")
mark("arch_3")
turn("7 Planície da rocha equilibrada", -800, 60, ease=400, width=40, to_y=170, apron=150, **OPEN)
seg("7 Saída da planície", 800, ease=300, radius=0)

# ---------------------------------------------------------------- 8 THE HOLLOW (16:00-18:00)
sector("THE HOLLOW")
seg("8 Aproximação à mesa", 900, ease=400, to_y=160, width=34, radius=0, **CANYON)
turn("8 Canyon da mesa", 600, 60, ease=400, bank=8)
turn("8 Gancho da mesa", -125, 110, ease=150, bank=-16, width=30)
seg("8 Reta da mesa", 900, ease=300, radius=0, bank=0, width=34)
esses("8 Esses da aproximação", r=120, deg=65, bank=12)
seg("8 Boca da caverna", 400, ease=200, to_y=150)
seg("8 Caverna · entrada ampla", 300, ease=150, cave=1, ceil=34, to_y=148, width=44,
    wallL=16, wallR=16, filletL=10, filletR=10, angleL=70, angleR=70, rideL=0.5, rideR=0.5)
turn("8 Caverna · curva larga", 320, 70, ease=200)
seg("8 Caverna · descida", 500, ease=200, to_y=118, radius=0)
turn("8 Caverna · bank natural", -260, 80, ease=250, bank=-22, to_y=112)
seg("8 Caverna · half-pipe", 500, ease=200, radius=0, bank=0, slope=0, width=30, wallL=22, wallR=22, angleL=74, angleR=74, rideL=0.8, rideR=0.8)
mark("hollow_chamber")
seg("8 Caverna · câmara", 400, ease=200, width=70, ceil=48, wallL=16, wallR=16, angleL=70, angleR=70, rideL=0.5, rideR=0.5)
turn("8 Caverna · curva apertada", 140, 80, ease=150, bank=14, width=32, ceil=30)
seg("8 Caverna · segunda câmara", 400, ease=200, radius=0, bank=0, width=56, ceil=42)
turn("8 Caverna · curva final", -300, 60, ease=200, width=32, ceil=30)
seg("8 Caverna · estreita", 400, ease=150, width=30, ceil=28, radius=0, bank=0)
seg("8 Caverna · rampa de saída", 120, ease=60, slope=4)
seg("8 Salto de saída", 70, ease=0, slope=-6, gap=1, cave=0)
seg("8 Receção", 260, ease=40, slope=-12, gap=0)
seg("8 Nivelar", 400, ease=250, slope=-3, width=34, wallL=8, wallR=8, angleL=40, angleR=40, rideL=0.3, rideR=0.3)
turn("8 Descida à White Rim", 1000, 70, ease=400, to_y=60)
esses("8 Esses da descida", r=125, deg=60, bank=12)
seg("8 Chegada à White Rim", 600, ease=300, to_y=48)

# ---------------------------------------------------------------- 9 WHITE RIM FINALE (18:00-20:00)
sector("WHITE RIM FINALE")
mark("rim_from")
turn("9 White Rim", 2000, 40, ease=500, to_y=46, width=44, surface="slickrock", apron=200, **OPEN)
turn("9 Curva larga", -1400, 70, ease=500, width=48)
crest("9 Ondulação 1")
seg("9 Reta longa", 1800, ease=400, radius=0)
turn("9 Curva larga 2", 1200, 60, ease=500)
crest("9 Ondulação 2")
turn("9 Curva da borda", -350, 70, ease=300, bank=-12)
seg("9 Reta da borda", 1200, ease=300, radius=0, bank=0)
mark("rim_to")
seg("9 Aproximação ao hero jump", 800, ease=300, radius=0, width=40)
canyon_jump("9 Hero jump", lip=4.5, gap=60, land=-9.0)
mark("arch_rim")
seg("9 Reta final · EXTRAÇÃO", 1200, ease=300, width=50)
SECTORS[-1]['to'] = pos

M = MARK
spec = {
    "name": "red_dust_divide",
    "title": "RED DUST DIVIDE · Expedição (≈20 min)",
    "seed": 11,
    "step": 5.0,
    "wall_samples": 40,
    "chunk": 48,
    "sector_km": 13,
    "terrain_res": 10,
    "line_chunk": 600,
    "start": {"pos": [0.0, 262.0, 0.0], "yaw": 0.0},
    "defaults": {"width": 30, "bank": 0, "slope": 0, "radius": 0, "wallL": 8, "wallR": 8, "filletL": 12, "filletR": 12,
                 "angleL": 40, "angleR": 40, "lipL": 6, "lipR": 6, "rideL": 0.3, "rideR": 0.3, "surface": "sand",
                 "cave": 0, "ceil": 28, "gap": 0, "open": 0},
    "sectors": SECTORS,
    "segments": SEG,
    "features": [
        {"type": "rockfall", "path": "main", "from": M["basin_rockfall_from"], "to": M["basin_rockfall_to"], "every": 220, "gap_m": 18},
        {"type": "rockfall", "path": "main", "from": M["wash2_rockfall_from"], "to": M["wash2_rockfall_to"], "every": 180, "gap_m": 16},
        {"type": "pillars", "path": "main", "from": M["needles_from"] + 100, "to": M["needles_to"] - 100, "every": 170,
         "pattern": "random", "u": 0.5, "radius": [2.6, 3.8], "height": [18, 38]},
        {"type": "pillars", "path": "main", "from": M["arches_slalom2_from"] + 100, "to": M["arches_slalom2_to"] - 100, "every": 140,
         "pattern": "slalom", "u": 0.45, "radius": [2.4, 3.2], "height": [14, 30]},
        {"type": "rockfall", "path": "main", "from": M["mesa_rockfall_from"], "to": M["mesa_rockfall_to"], "every": 240, "gap_m": 16},
        {"type": "rockfall", "path": "main", "from": M["wall_rockfall_from"], "to": M["wall_rockfall_to"], "every": 200, "gap_m": 15},
        {"type": "rockfall", "path": "main", "from": M["wash_rockfall_from"], "to": M["wash_rockfall_to"], "every": 200, "gap_m": 18},
        {"type": "pillars", "path": "main", "from": M["arches_slalom_from"] + 100, "to": M["arches_slalom_to"] - 100, "every": 150,
         "pattern": "slalom", "u": 0.42, "radius": [2.4, 3.4], "height": [16, 34]},
        {"type": "pillars", "path": "main", "from": M["hollow_chamber"] + 150, "to": M["hollow_chamber"] + 260, "every": 400,
         "pattern": "slalom", "u": 0.0, "radius": [6.0, 7.0], "height": [30, 34]},
        {"type": "arch", "path": "main", "at": M["arch_1"] + 400, "clearance": 16, "thick": 12, "depth": 18, "sag": 8},
        {"type": "arch", "path": "main", "at": M["arch_2"] + 200, "clearance": 14, "thick": 10, "depth": 14, "sag": 6},
        {"type": "arch", "path": "main", "at": M["arch_3"] + 500, "clearance": 22, "thick": 16, "depth": 26, "sag": 14},
        {"type": "arch", "path": "main", "at": M["arch_wall_canyon"] + 700, "clearance": 18, "thick": 14, "depth": 22, "sag": 10},
        {"type": "arch", "path": "main", "at": M["arch_rim"] + 500, "clearance": 24, "thick": 18, "depth": 30, "sag": 18},
        {"type": "wreck", "path": "main", "from": M["wash_wreck"] + 150, "to": M["wash_wreck"] + 450, "clearance": 14, "tilt": 18},
        {"type": "gorge_along", "path": "main", "from": M["rim_from"], "to": M["rim_to"], "side": 1, "offset": 340,
         "depth": 170, "half_width": 50},
    ],
    "rocks": {"density": 0.5},
    "branches": [
        {"id": "SAFE Rota baixa da mesa", "from": M["mesa_fork_from"] + 150, "to": M["mesa_fork_to"] + 100, "blend": 220,
         "via": [{"t": 0.2, "side": -1, "offset": 120, "dy": 0},
                 {"t": 0.5, "side": -1, "offset": 190, "dy": -14},
                 {"t": 0.8, "side": -1, "offset": 120, "dy": 0}],
         "params": {"width": 36, "surface": "sand", "open": 1, "wallL": 3, "wallR": 3, "filletL": 14, "filletR": 14,
                    "angleL": 22, "angleR": 22, "rideL": 0.4, "rideR": 0.4}},
        {"id": "SKILL Salto da Red Wall", "from": M["wall_skill_from"] + 150, "to": M["wall_skill_to"] - 80, "blend": 160,
         "via": [{"t": 0.22, "side": 1, "offset": 70, "dy": 0},
                 {"t": 0.45, "side": 1, "offset": 115, "dy": 16},
                 {"t": 0.75, "side": 1, "offset": 90, "dy": 6}],
         "params": {"width": 14, "wallL": 12, "wallR": 12, "filletL": 8, "filletR": 8, "angleL": 70, "angleR": 70,
                    "rideL": 0.4, "rideR": 0.4, "surface": "slickrock"},
         "sections": [{"frac": 0.5, "id": "SKILL Salto da Red Wall · fenda", "gap": 1, "ease": 0},
                      {"frac": 0.53, "id": "SKILL Salto da Red Wall · receção", "gap": 0, "ease": 60}]},
        {"id": "SAFE Borda exterior da ferradura", "from": M["shoe_from"] + 100, "to": M["shoe_to"] - 100, "blend": 250,
         "via": [{"t": 0.25, "side": 1, "offset": 140, "dy": 10},
                 {"t": 0.5, "side": 1, "offset": 170, "dy": 18},
                 {"t": 0.75, "side": 1, "offset": 140, "dy": 10}],
         "params": {"width": 34, "surface": "sand"}},
        {"id": "SKILL Terraço interior da ferradura", "from": M["shoe_from"] + 300, "to": M["shoe_to"] - 400, "blend": 200,
         "via": [{"t": 0.3, "side": -1, "offset": 150, "dy": 14},
                 {"t": 0.6, "side": -1, "offset": 170, "dy": 16},
                 {"t": 0.85, "side": -1, "offset": 90, "dy": 14}],
         "params": {"width": 18, "wallL": 10, "wallR": 10, "angleL": 66, "angleR": 66, "surface": "slickrock"},
         "sections": [{"frac": 0.88, "id": "SKILL Terraço interior · drop", "gap": 1, "ease": 0},
                      {"frac": 0.92, "id": "SKILL Terraço interior · receção", "gap": 0, "ease": 60}]},
    ],
}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'red_dust_divide.json')
json.dump(spec, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"{out}: {len(SEG)} segmentos, {pos / 1000:.1f} km, {len(SECTORS)} setores, {len(spec['branches'])} ramos, {len(spec['features'])} elementos")
