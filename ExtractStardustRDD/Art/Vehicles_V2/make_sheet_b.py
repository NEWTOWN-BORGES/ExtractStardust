# Folha da Fase B (greybox de engenharia): montada, explodida, cortes, fundo e mapa de sockets.
#   python make_sheet_b.py <pasta_renders> <saida.jpg> <NAVE>
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SRC, OUT, SHIP = sys.argv[1], sys.argv[2], sys.argv[3]
INFO = json.load(open(os.path.join(SRC, f'{SHIP.lower()}_b_info.json'), encoding='utf-8'))
INK, SUB, ACC = (22, 22, 26), (90, 92, 98), (214, 92, 40)


def font(size, bold=False):
    for f in (("segoeuib.ttf" if bold else "segoeui.ttf"), ("arialbd.ttf" if bold else "arial.ttf")):
        try:
            return ImageFont.truetype(os.path.join("C:/Windows/Fonts", f), size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit(im, w, h):
    bb = im.getbbox()
    if bb:
        im = im.crop((max(0, bb[0] - 16), max(0, bb[1] - 16), min(im.width, bb[2] + 16), min(im.height, bb[3] + 16)))
    im = im.copy()
    im.thumbnail((w, h), Image.LANCZOS)
    return im


def panel(sheet, d, name, box, label, labels=None):
    x, y, w, h = box
    d.rectangle((x, y, x + w, y + h), fill=(247, 247, 248), outline=(205, 205, 210))
    d.text((x + 12, y + 8), label, font=font(20, True), fill=SUB)
    src = Image.open(os.path.join(SRC, f"{SHIP}_B_{name}.png")).convert('RGBA')
    if labels:   # rótulos dos sockets desenhados sobre a imagem original antes de encaixar
        dd = ImageDraw.Draw(src)
        for k, (px, py) in labels.items():
            dd.ellipse((px - 9, py - 9, px + 9, py + 9), fill=ACC + (255,))
            dd.text((px + 12, py - 12), k.replace('Socket_', ''), font=font(22, True), fill=INK + (255,))
    im = fit(src, w - 30, h - 46)
    sheet.paste(im, (x + (w - im.width) // 2, y + 36 + (h - 36 - im.height) // 2), im)


W, H = 2560, 1700
sheet = Image.new('RGB', (W, H), (236, 236, 238))
d = ImageDraw.Draw(sheet)
d.rectangle((0, 0, W, 110), fill=INK)
d.text((40, 16), f"{SHIP} · A WEDGE — FASE B · GREYBOX DE ENGENHARIA (de dentro para fora)", font=font(46, True), fill=(255, 255, 255))
d.text((42, 72), "estrutura → célula → espinha → reator → frame de propulsão → hover → refrigeração → sockets → cablagens → painéis em chapa → estabilizadores",
       font=font(22), fill=(200, 200, 205))
panel(sheet, d, 'assembled_f34', (30, 130, 1240, 640), "MONTADA · painéis em chapa separados, dobradiças, entradas com malha")
panel(sheet, d, 'exploded_f34', (1290, 130, 1240, 640), "EXPLODIDA · painéis, blocos, canopy e estabilizadores fora do sítio")
panel(sheet, d, 'cutaway_r34', (30, 790, 830, 520), "CORTE TRASEIRO · reator, radiadores, cablagens, suportes")
panel(sheet, d, 'underside', (880, 790, 830, 520), "FUNDO · emissores hover com suportes e bobinas, sensores")
panel(sheet, d, 'socketmap_top', (1730, 790, 800, 520), "MAPA DE SOCKETS (rail + grampo + conector)", INFO['labels'])
panel(sheet, d, 'cutaway_top', (30, 1330, 1240, 340), "CIMA SEM PAINÉIS · rails, travessas, crash box, célula, tubos")
panel(sheet, d, 'side', (1290, 1330, 1240, 340), "LADO")
leg = [((0.70, 0.71, 0.73), "painéis"), ((0.40, 0.41, 0.43), "estrutura"), ((0.50, 0.51, 0.53), "mecânica"), ((0.10, 0.10, 0.11), "cablagens"),
       ((0.30, 0.42, 0.56), "refrigerante"), ((0.95, 0.50, 0.14), "sockets/conectores"), ((0.98, 0.84, 0.52), "núcleo do reator")]
x = 1720
for c, t in leg:
    d.rectangle((x, 82, x + 18, 100), fill=tuple(int(v * 255) for v in c))
    d.text((x + 24, 78), t, font=font(18), fill=(220, 220, 225))
    x += 24 + int(d.textlength(t, font=font(18))) + 22
sheet.save(OUT, quality=90)
print('ok')
