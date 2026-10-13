# Folhas de conceito da Fase A (STRIX): 7 vistas por proposta + comparação de silhuetas.
#   python make_sheets.py <pasta_renders> <pasta_saida>
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
INFO = json.load(open(os.path.join(SRC, 'strix_info.json'), encoding='utf-8'))
BG, INK, SUB, ACC = (236, 236, 238), (22, 22, 26), (90, 92, 98), (214, 92, 40)

TEXT = {
    'A': ("WEDGE · linguagem R02 (cunha de corrida longa). Corpo baixo e facetado em cunha; cockpit a meio, metido no corpo; "
          "dois blocos de propulsão traseiros separados por uma ranhura; estabilizadores médios planos nos flancos dos blocos.",
          "Construção: espinha central → célula do cockpit → ponte do reator entre os blocos → blocos de propulsão → hover sob o casco → painéis.",
          "Força: equilíbrio e leitura clara a 50 m. Fraqueza: nenhuma especialidade. Refrigeração: scoops laterais com lábio que alimentam os blocos."),
    'B': ("SPLIT · linguagem R10/R14 (garfo com espaço negativo). O nariz são duas lâminas em garfo com vazio entre elas; "
          "o cockpit fica na junção; dois blocos de propulsão traseiros; estabilizadores médios nos blocos.",
          "Construção: duas lâminas de impacto → viga de impacto na junção → célula do cockpit → ponte do reator → blocos de propulsão → painéis.",
          "Força: silhueta inconfundível e nariz leve. Fraqueza: lâminas expostas a impacto frontal. Refrigeração: scoops laterais dos blocos."),
    'C': ("POD · linguagem R05 (pod de corrida). Corpo comprido e plano com o cockpit à frente; o corpo divide-se atrás em dois "
          "blocos de propulsão; respiros laterais longos; estabilizadores médios dianteiros.",
          "Construção: espinha longa → célula do cockpit à frente → reator a meio (respiros) → blocos de propulsão → hover → painéis.",
          "Força: estabilidade e visibilidade do piloto. Fraqueza: traseira longa menos ágil. Refrigeração: respiros laterais e scoops dos blocos."),
}


def font(size, bold=False):
    for f in (("segoeuib.ttf" if bold else "segoeui.ttf"), ("arialbd.ttf" if bold else "arial.ttf")):
        try:
            return ImageFont.truetype(os.path.join("C:/Windows/Fonts", f), size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit(im, w, h):
    im = im.copy()
    bb = im.getbbox()
    if bb:
        pad = 18
        im = im.crop((max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.width, bb[2] + pad), min(im.height, bb[3] + pad)))
    im.thumbnail((w, h), Image.LANCZOS)
    return im


def panel(sheet, d, im, box, label, white=False):
    x, y, w, h = box
    d.rectangle((x, y, x + w, y + h), fill=(255, 255, 255) if white else (246, 246, 247), outline=(205, 205, 210))
    d.text((x + 14, y + 10), label, font=font(20, True), fill=SUB)
    im = fit(im, w - 40, h - 56)
    sheet.paste(im, (x + (w - im.width) // 2, y + 40 + (h - 40 - im.height) // 2), im)


def wrap(d, text, f, width):
    out, cur = [], ''
    for word in text.split():
        t = (cur + ' ' + word).strip()
        if d.textlength(t, font=f) <= width:
            cur = t
        else:
            out.append(cur)
            cur = word
    return out + [cur]


def load(key, view):
    return Image.open(os.path.join(SRC, f"STRIX_{key}_{view}.png")).convert('RGBA')


for key, meta in INFO.items():
    W, H = 2560, 1600
    sheet = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.rectangle((0, 0, W, 118), fill=INK)
    d.text((40, 18), f"STRIX — PROPOSTA {key} · {meta['label']}", font=font(52, True), fill=(255, 255, 255))
    d.text((42, 80), f"Fase A · silhueta / greybox · sem materiais, decals ou microdetalhe · {meta['length']:.2f} × {meta['width']:.2f} × {meta['height']:.2f} m "
                     f"(alvo 6,2 × 3,0 × 1,25)", font=font(24), fill=(200, 200, 205))
    d.rectangle((W - 330, 30, W - 40, 88), outline=ACC, width=3)
    d.text((W - 185, 59), "PARA APROVAÇÃO", font=font(24, True), fill=ACC, anchor='mm')
    panel(sheet, d, load(key, 'f34'), (40, 140, 1230, 720), "3/4 FRENTE")
    panel(sheet, d, load(key, 'r34'), (1290, 140, 1230, 720), "3/4 TRÁS")
    panel(sheet, d, load(key, 'top'), (40, 880, 760, 440), "CIMA")
    panel(sheet, d, load(key, 'side'), (820, 880, 760, 440), "LADO")
    panel(sheet, d, load(key, 'front'), (1600, 880, 450, 215), "FRENTE")
    panel(sheet, d, load(key, 'rear'), (1600, 1105, 450, 215), "TRÁS")
    sil = Image.new('RGBA', (900, 900), (0, 0, 0, 0))
    a, b = fit(load(key, 'top_silhouette'), 880, 480), fit(load(key, 'side_silhouette'), 880, 300)
    sil.paste(a, ((900 - a.width) // 2, 10), a)
    sil.paste(b, ((900 - b.width) // 2, 560), b)
    panel(sheet, d, sil, (2070, 880, 450, 440), "SILHUETA PRETA", white=True)
    y = 1345
    for i, t in enumerate(TEXT[key]):
        for line in wrap(d, t, font(25, i == 0), W - 80):
            d.text((40, y), line, font=font(25, i == 0), fill=INK if i == 0 else SUB)
            y += 34
        y += 6
    sheet.save(os.path.join(OUT, f"STRIX_{key}_{meta['label']}.jpg"), quality=90)

# comparação: as três silhuetas lado a lado (escolha rápida)
W, H = 2560, 1440
sheet = Image.new('RGB', (W, H), (255, 255, 255))
d = ImageDraw.Draw(sheet)
d.rectangle((0, 0, W, 110), fill=INK)
d.text((40, 22), "STRIX — FASE A · 3 PROPOSTAS · ESCOLHE UMA", font=font(50, True), fill=(255, 255, 255))
for i, (key, meta) in enumerate(INFO.items()):
    x = 40 + i * 840
    d.text((x + 400, 150), f"{key} · {meta['label']}", font=font(42, True), fill=INK, anchor='mm')
    for view, (yy, hh) in (('top_silhouette', (190, 420)), ('side_silhouette', (630, 200)), ('front_silhouette', (850, 200))):
        im = fit(load(key, view), 780, hh)
        sheet.paste(im, (x + (800 - im.width) // 2, yy + (hh - im.height) // 2), im)
    im = fit(load(key, 'f34'), 800, 360)
    sheet.paste(im, (x + (800 - im.width) // 2, 1070), im)
sheet.save(os.path.join(OUT, "STRIX_comparacao_silhuetas.jpg"), quality=90)
print('ok')
