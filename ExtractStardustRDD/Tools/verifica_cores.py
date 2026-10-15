"""
Mostra o empacotamento de cor por vertice da parede e do detrito
(LabGeometry.WallLayerColor e o trecho do cone em WallProfilePoints).

Cada vertice leva 4 canais: R = classe de superficie (a fisica le isto),
G/B = duas camadas da paleta RD_PAL, A = mascara da zona de corrida.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust\ExtractStardustRDD\Docs"
os.makedirs(OUT, exist_ok=True)

PAL = [(150,62,40),(226,214,190),(140,72,50),(168,98,70),(185,170,145),(172,86,64),
       (128,92,104),(150,150,130),(196,98,52),(150,84,66),(222,190,150),(214,160,128),
       (206,150,100),(40,28,24)]
L = {n: i for i, n in enumerate([
    "OrganRock","WhiteRim","Moenkopi","MoenkopiClaro","MossBack","ChinleVermelho",
    "ChinlePurpura","ChinleCinza","Wingate","Kayenta","Navajo","NavajoRosado","Areia","Verniz"])}


def wall_layer_color(hard):
    """Porta de WallLayerColor."""
    if hard < 0.30: a, b = L["OrganRock"], L["ChinleVermelho"]
    elif hard < 0.50: a, b = L["Moenkopi"], L["ChinleCinza"]
    elif hard < 0.70: a, b = L["Kayenta"], L["MossBack"]
    elif hard < 0.90: a, b = L["Navajo"], L["NavajoRosado"]
    else: a, b = L["Wingate"], L["WhiteRim"]
    return a, b


def talus_color():
    return L["MoenkopiClaro"], L["ChinleCinza"]


def mix(a, b, t=0.5):
    return tuple(int(PAL[a][k]*(1-t) + PAL[b][k]*t) for k in range(3))


def font(sz):
    for p in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


F, FS = font(19), font(13)
BG, FG, DIM = (16, 18, 24), (232, 236, 244), (140, 148, 166)

# camadas reais da coluna
LAYERS = [("Organ Rock",200.0,0.30),("White Rim",40.0,0.95),("Moenkopi",65.0,0.45),
          ("Moss Back",15.0,0.90),("Chinle",45.0,0.15),("Wingate",100.0,0.97),
          ("Kayenta",35.0,0.65),("Navajo",60.0,0.85),("Carmel",20.0,0.25),
          ("Entrada",80.0,0.92),("Summerville",60.0,0.30)]

W, H = 1500, 820
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
d.text((54, 18), "COR POR VÉRTICE — parede (por dureza da camada) e detrito (material solto)", font=F, fill=FG)
d.text((54, 44), "antes o detrito herdava a cor do topo da parede e lia como rocha firme; "
                 "agora é cascalho, e a física também muda (grip 0,72 em vez de 0,88)", font=FS, fill=DIM)

px, py, pw = 60, 100, 560
total = sum(t for _, t, _ in LAYERS)
BLOCK = 560
ys = py + BLOCK
for name, thick, hard in reversed(LAYERS):
    h = max(10, int(BLOCK * thick / total))
    a, b = wall_layer_color(hard)
    c = mix(a, b)
    d.rectangle([px, ys - h, px + pw, ys], fill=c)
    d.text((px + pw + 12, ys - h + max(0, (h - 14) // 2)), f"{name}  dureza {hard:.2f}  ->  "
           f"paleta {a}/{b}", font=FS, fill=FG)
    ys -= h + 2

# detrito
d.rectangle([px, ys - 40, px + pw, ys], fill=mix(*talus_color()))
d.text((px + pw + 12, ys - 26), "DETRITO  classe 0,375 (cascalho)  ->  paleta "
       f"{talus_color()[0]}/{talus_color()[1]}", font=FS, fill=(255, 200, 120))
d.rectangle([px - 60, ys - 40, px - 48, ys], fill=mix(*talus_color()))

# legenda dos canais
lx, ly = 700, 120
d.text((lx, ly), "O que cada canal faz", font=F, fill=(255, 176, 82))
rows = [
    ("R", "classe de superfície", "A FÍSICA lê isto: grip, topSpeed, drag", (255, 120, 120)),
    ("G", "camada A da paleta (÷15)", "cor da rocha, mistura A/B", (120, 255, 140)),
    ("B", "camada B da paleta (÷15)", "a segunda cor da mistura", (120, 160, 255)),
    ("A", "máscara de corrida", "1 nas superfícies de medição", (255, 220, 120)),
]
for i, (ch, nome, desc, cor) in enumerate(rows):
    yy = ly + 40 + i * 74
    d.rectangle([lx, yy, lx + 34, yy + 34], fill=cor)
    d.text((lx + 46, yy - 2), f"{ch} · {nome}", font=FS, fill=FG)
    d.text((lx + 46, yy + 16), desc, font=FS, fill=DIM)

d.text((lx, ly + 40 + 4*74), "Classes usadas", font=F, fill=(255, 176, 82))
cls = [("0", "areia"), ("0,375", "cascalho (detrito)"), ("0,5", "parede polida (lab)"),
       ("0,75", "falésia (parede)"), ("1,0", "planalto")]
for i, (v, nome) in enumerate(cls):
    d.text((lx, ly + 82 + 4*74 + i*24), f"  {v:6s} {nome}", font=FS, fill=FG)

d.text((54, H - 30), "A classe do detrito (0,375) não é só estética: a aderência naquele ponto "
                     "passa de 0,88 a 0,72. Corre no Metrics Lab, que é de medição.", font=FS, fill=DIM)
img.save(os.path.join(OUT, "cores_parede_detrito.png"))
print("->", os.path.join(OUT, "cores_parede_detrito.png"))
