"""The menu and hangar screens as the code lays them out (EXMainMenuWidget, EXHangarWidget), in the HUD's look, over a render
of the workshop (hangar_scene.py). python3 Scripts/ui_mockups/screens.py [menu nave equipar cofre caixa]; UI_MOCK_OUT sets
the folder (default Docs/UI_MAQUETAS), UI_MOCK_BG the background (default <folder>/hangar_bg.png).
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from uimock import *
D = os.environ.get('UI_MOCK_OUT', R + 'Docs/UI_MAQUETAS') + '/'
BG = os.environ.get('UI_MOCK_BG', D + 'hangar_bg.png')
CW, CH, CA = 248.0, 331.0, 158.0
FAM = ['MOTOR', 'PROPULSÃO', 'ASAS', 'CAUDA', 'BLINDAGEM', 'REATOR', 'REFRIGERAÇÃO', 'UTILIDADE']


def shade_left(S, width=900, a0=0.45):
    g = np.zeros((H, width, 4), np.uint8)
    g[..., :3] = INK
    g[..., 3] = (np.linspace(a0, 0, width)[None, :] * 255).astype(np.uint8)
    S.comp(Image.fromarray(g, 'RGBA'), 0, 0)


def topbar(S, tab):
    g = np.zeros((77, W, 4), np.uint8); g[..., :3] = INK
    g[..., 3] = (np.linspace(0.85, 0, 77)[:, None] * 255).astype(np.uint8)
    S.comp(Image.fromarray(g, 'RGBA'), 0, 0)
    x = 48
    x += S.title(x, 20, 'HANGAR', 24, FORE, 160) + 38
    for k, name in enumerate(['NAVE', 'EQUIPAR', 'CONSUMÍVEIS', 'LOJA', 'COFRE']):
        tw = S.text(0, 0, name, 11, QUIET, 'i800', 180, measure=True)
        w = tw + 52
        on = k == tab
        S.plate(x, 19, w, 38, fill=(ACCENT, 0.95) if on else (PLATE, 0.6), edge=(FORE, 0.9) if on else (ACCENT_HOT, 0.25), corner=38, kind='tab')
        S.label(x + 26, 28, name, 11, INK if on else QUIET, 180)
        x += w + 2
    S.wallet(W - 48, 17, '12 750')


def panel(S, x, y, w, h, top=False):
    S.plate(x, y, w, h, fill=(PLATE, 0.82), edge=(ACCENT, 0.9 if top else 0.5), corner=16, top=(ACCENT, 0.9, 3) if top else None)


def stats(S, deltas=None):
    x0, w = (W - 50 - 910) / 2, 910
    h = 14 + 56 + 8 + 56 + 4 + 18 + 12
    y0 = H - 55 - h
    panel(S, x0, y0, w, h)
    names = ['VELOCIDADE', 'ACELERAÇÃO', 'MANOBRA', 'ESTABILIDADE', 'CASCO  ·  VIDAS', 'EFICIÊNCIA', 'REFRIGERAÇÃO', 'NITRO']
    vals = [78, 64, 71, 58, 66, 52, 60, 74]
    deltas = deltas or {}
    for i in range(8):
        cx = x0 + 20 + (i % 4) * (206 + 12)
        cy = y0 + 14 + (i // 4) * (56 + 8)
        S.label(cx, cy, names[i], 9, QUIET, 160)
        vw = S.title(cx, cy + 14, str(vals[i]), 15, FORE, 20)
        dv = deltas.get(i)
        if dv:
            S.text(cx + vw + 7, cy + 18, ('+%d' % dv) if dv > 0 else str(dv), 10, OK if dv > 0 else (255, 96, 80), 'i800')
        S.rect(cx, cy + 44, 196, 6, FORE, 0.08)
        fw = 196 * vals[i] / 100.0
        S.rect(cx, cy + 44, fw, 6, ACCENT)
        if dv:
            S.rect(cx + fw, cy + 44, 196 * abs(dv) / 100.0, 6, OK if dv > 0 else (255, 96, 80), 1.0 if dv > 0 else 0.85)
    S.text(x0 + 20, y0 + h - 12 - 18, '♥ 4 VIDAS NESTA NAVE', 10, OK, 'i800', 100)
    return y0


def callout(S, x, y, s, col):
    tw = S.text(0, 0, s, 10, FORE, 'i500', measure=True)
    S.rect(x, y, 2, 26, col)
    S.rect(x + 2, y, tw + 20, 26, PLATE, 0.8)
    S.text(x + 12, y + 5, s, 10, FORE, 'i500')


# ------------------------------------------------------------------------------------------------------------- menu
def menu():
    S = Screen(BG)
    shade_left(S)
    S.label(58, 29, 'EXPEDIÇÃO 01  ·  RED DUST DIVIDE', 11, ACCENT_HOT, 220)
    S.wallet(W - 58, 17, '12 750')
    S.icon('ui_logo', 77, 115 + 19, 624, 182)
    titles = ['EXPEDIÇÃO SOLO', 'PELOTÃO 15', 'HANGAR', 'SAIR']
    desc = ['Tu contra o deserto. Chega vivo a B.', 'Quinze rivais na grelha. Só quem chega vivo a B extrai.',
            'Módulos, consumíveis, loja e cofre. As luzes acendem-se.', 'Fechar o jogo. O perfil fica guardado.']
    y = 115 + 19 + 228 + 46
    for k in range(4):
        on = k == 1
        h = 16 + 45 + (6 + 22 if on else 0) + 16
        if on:
            S.plate(77, y, 624, h, fill=(PLATE, 0.86), edge=(ACCENT, 0.95), corner=12, wash=(ACCENT, 0.3))
            S.rect(77 + 3, y + 15, 4, h - 21, ACCENT)
        S.title(77 + 26, y + 16 + 14, '%02d' % (k + 1), 12, ACCENT if on else DIM, 60)
        S.title(77 + 26 + 53, y + 16 + 2, titles[k], 27, FORE if on else QUIET, 80)
        if on:
            S.text(77 + 26 + 53, y + 16 + 45 + 6, desc[k], 13, FORE, 'i400', 20, alpha=0.85)
        y += h + 8
    # briefing
    bx, by, bw = W - 67 - 564, 115, 564
    bh = 762
    S.plate(bx, by, bw, bh, fill=(PLATE, 0.88), edge=(ACCENT, 0.85), corner=18, top=(ACCENT, 0.85, 3))
    x, y = bx + 29, by + 26
    S.label(x, y, 'BRIEFING DA EXPEDIÇÃO', 11, ACCENT_HOT, 220)
    S.title(x, y + 22, 'RED DUST DIVIDE', 23, FORE, 60)
    S.text(x, y + 60, 'Canyonlands  ·  de A (The Basin) a B (Mesa Arch)  ·  16 naves', 12, QUIET, 'i400')
    my = y + 60 + 17 + 17
    mw = bw - 58
    S.plate(x, my, mw, 300, fill=(INK, 0.55), edge=(ACCENT_HOT, 0.3), corner=10)
    t = np.linspace(0, 1, 400)
    px = x + 40 + t * (mw - 80) + 30 * np.sin(t * 9.0) + 18 * np.sin(t * 23.0)
    py = my + 250 - t * 200 + 40 * np.sin(t * 6.5 + 0.4) + 14 * np.cos(t * 17.0)
    lay = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(lay)
    pts = list(zip(px, py))
    d.line(pts, fill=INK + (230,), width=6, joint='curve')
    g = Image.new('RGBA', (W, H)); ImageDraw.Draw(g).line(pts, fill=ACCENT + (200,), width=7, joint='curve')
    lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(5)))
    d.line(pts, fill=ACCENT + (255,), width=3, joint='curve')
    for (qx, qy), r, c in (((px[0], py[0]), 8, FORE), ((px[-1], py[-1]), 8, ACCENT_HOT), ((px[-1], py[-1]), 3, FORE)):
        d.ellipse([qx - r, qy - r, qx + r, qy + r], fill=c + (255,))
    S.comp(lay, 0, 0)
    S.label(px[0] + 12, py[0] - 6, 'A', 10, FORE); S.label(px[-1] + 12, py[-1] - 6, 'B', 10, ACCENT_HOT)
    sy = my + 300 + 7 + 7
    tw = (mw - 20) / 3
    for k, (v, lab) in enumerate((('59,0 km', 'DISTÂNCIA'), ('~10:24', 'DURAÇÃO'), ('7', 'ATALHOS'))):
        tx = x + k * (tw + 10)
        S.plate(tx, sy, tw, 72, fill=(PLATE, 0.7), edge=None, corner=8)
        S.title(tx + 14, sy + 12, v, 20, FORE, 20)
        S.label(tx + 14, sy + 48, lab, 9, QUIET, 140)
    cy = sy + 72 + 7
    for row in (('Túnel The Hollow', 'Lajes partidas', 'Salto-herói'), ('Dunas', 'Fendas', '19 saltos')):
        cx = x
        for c in row:
            w = S.text(0, 0, c, 11, ACCENT_HOT, 'i400', measure=True) + 20
            S.plate(cx, cy, w, 24, fill=(ACCENT, 0.12), edge=(ACCENT, 0.45), corner=6)
            S.text(cx + 10, cy + 3, c, 11, ACCENT_HOT, 'i400')
            cx += w + 7
        cy += 24 + 7
    ry = cy + 14
    S.rect(x, ry, mw, 1, FORE, 0.1); ry += 11
    for lab, val, col, line in (('A tua nave', 'VORTEX', FORE, False), ('Módulos e consumíveis', '8 módulos  ·  Surge ×2  ·  Foam ×1', FORE, False),
                                ('Em risco se fores destruído', '18 420 STARDUST', GOLD, True), ('Última expedição', '+2 340 STARDUST', OK, False)):
        if line:
            ry += 14 - 6; S.rect(x, ry, mw, 1, FORE, 0.1); ry += 11
        S.text(x, ry, lab, 13, FORE, 'i400', alpha=0.9)
        S.text(x + mw, ry, val, 13, col, 'i700', 120 if val == 'VORTEX' else 0, align='r')
        ry += 24
    S.keybar([(['W', 'S'], 'Navegar'), (['Enter', 'X'], 'Confirmar'), (['Tab'], 'Nave')], (['Esc'], 'Sair'))
    S.save(D + 'ui_menu.png')


# ------------------------------------------------------------------------------------------------------------- hangar: equip
def equipar():
    S = Screen(BG)
    topbar(S, 1)
    x, y, w = 43, 110, 420
    slots = [('MOTOR', 'Vanta Ion Mk II', 2, 'M', True), ('PROPULSÃO', 'Nitro Coil', 1, 'S', False), ('ASAS', 'Slipstream Fold', 3, 'M', False),
             ('CAUDA', 'Twin Keel', 1, 'S', False), ('BLINDAGEM', 'Aegis Kit', 2, 'L', False), ('REATOR', 'Flux Cell', 0, 'M', False),
             ('REFRIGERAÇÃO', 'Radiador NACA', 1, 'M', False), ('UTILIDADE', 'Scanner', 0, 'S', False)]
    h = 17 + 20 + 12 + 8 * 66 + 4 + 17 + 12
    panel(S, x, y, w, h)
    S.label(x + 17, y + 17, 'SLOTS DA VORTEX', 12, ACCENT_HOT, 220)
    sy = y + 17 + 20 + 12
    for k, (fam, name, rar, size, ins) in enumerate(slots):
        on = k == 2
        S.plate(x + 17, sy, w - 34, 60, fill=(PICK, 0.92) if on else (PLATE, 0.55), edge=(ACCENT, 0.95) if on else (ACCENT_HOT, 0.14), corner=8)
        S.rect(x + 17 + 2, sy + 10, 3, 60 - 14, RARITY[rar])
        S.plate(x + 17 + 17, sy + 9.5, 41, 41, fill=(INK, 0.45), edge=(ACCENT_HOT, 0.25), corner=6)
        S.icon('fam_%d' % ['MOTOR', 'PROPULSÃO', 'ASAS', 'CAUDA', 'BLINDAGEM', 'REATOR', 'REFRIGERAÇÃO', 'UTILIDADE'].index(fam),
               x + 17 + 26, sy + 18.5, 23, 23, ACCENT_HOT if on else FORE, 1.0 if on else 0.85)
        S.text(x + 17 + 70, sy + 12, fam, 9, QUIET, 'i700', 180)
        S.text(x + 17 + 70, sy + 28, name, 13, RARITY[rar] if rar else FORE, 'i700', alpha=1 if rar else 0.8)
        bw = S.text(0, 0, size, 9, QUIET, 'i800', measure=True) + 12
        S.plate(x + w - 17 - 12 - bw, sy + 21, bw, 18, fill=(INK, 0.0), edge=(ACCENT_HOT, 0.35), corner=4)
        S.text(x + w - 17 - 12 - bw + 6, sy + 22, size, 9, QUIET, 'i800')
        if ins:
            S.icon('fam_4', x + w - 17 - 12 - bw - 27, sy + 22, 15, 15, OK)
        sy += 66
    S.icon('fam_4', x + 19, sy + 6, 13, 13, OK)
    S.text(x + 40, sy + 4, 'Seguro: nunca se perde (1 por expedição)', 10, QUIET, 'i400')
    # candidates
    rx, rw = W - 43 - 470, 470
    s = 0.80
    cw, chh = CW * s, CH * s
    rh = 17 + 20 + 12 + 2 * (chh + 16) + 20 + 12
    panel(S, rx, y, rw, rh)
    S.label(rx + 17, y + 17, 'ASAS  ·  4 PEÇAS', 12, ACCENT_HOT, 220)
    cards = [(3, 'Slipstream Fold', 'Asas  ·  M  ·  −10 kg', [('+9 Manobra', 1), ('+4 Estab.', 1), ('−2 Veloc.', -1)], 7200, 'vortex_wing_ep', True),
             (2, 'Vector Blade', 'Asas  ·  M  ·  −4 kg', [('+6 Manobra', 1), ('+2 Veloc.', 1)], 2400, 'vortex_wing_vector', False),
             (1, 'Glide Wing', 'Asas  ·  S  ·  −2 kg', [('+3 Estab.', 1)], 900, 'vortex_wing_glide', False),
             (0, 'Asas de série', 'Asas  ·  M', [], None, 'vortex_wing_blade', False)]
    for k, (rar, t, m, ch, v, th, picked) in enumerate(cards):
        cx = rx + 17 + (k % 2) * (cw + 16) + 8
        cy = y + 17 + 20 + 12 + (k // 2) * (chh + 16) + 8
        S.card(cx, cy, s, rar, t, m, ch, v, th, tag='MONTADA' if k == 1 else None, picked=picked, fs=s / 0.74)
    S.text(rx + 19, y + rh - 12 - 18, '1 / 4', 10, QUIET, 'i700', 120)
    # preview label and notes on the ship
    pv = '◆  PRÉ-VISUALIZAÇÃO  ·  SLIPSTREAM FOLD'
    tw = S.text(0, 0, 'PRÉ-VISUALIZAÇÃO  ·  SLIPSTREAM FOLD', 11, FORE, 'i800', 140, measure=True) + 22
    pw = tw + 34; px = (W - pw) / 2; py = H - 326 - 34
    S.plate(px, py, pw, 34, fill=(PLATE, 0.82), edge=(RARITY[3], 1.0), corner=8)
    dia = Image.new('RGBA', (16, 16)); ImageDraw.Draw(dia).polygon([(8, 0), (16, 8), (8, 16), (0, 8)], fill=RARITY[3] + (255,))
    S.comp(dia, px + 16, py + 9)
    S.text(px + 16 + 22, py + 8, 'PRÉ-VISUALIZAÇÃO  ·  SLIPSTREAM FOLD', 11, FORE, 'i800', 140)
    callout(S, 1210, 520, 'asa com fenda  ·  bordo de ataque com fluxo', RARITY[3])
    callout(S, 560, 470, 'ponta dobrada  ·  +9 manobra', RARITY[3])
    stats(S, {2: 9, 3: 4, 0: -2})
    S.button(rx, H - 74 - 62, 470, 62, 'MONTAR')
    S.keybar([(['W', 'S'], 'Slot'), (['A', 'D'], 'Peça'), (['Enter'], 'Montar'), (['T'], 'Seguro'), (['Q', 'E'], 'Separador')], (['Esc'], 'Voltar'))
    S.save(D + 'ui_equipar.png')


# ------------------------------------------------------------------------------------------------------------- hangar: vault
def cofre():
    S = Screen(BG)
    topbar(S, 4)
    x, y = 43, 110
    s = 0.74
    cw, chh = CW * s, CH * s
    cell_w, cell_h = cw + 16, chh + 16
    inner = 4 * cell_w
    w = inner + 34
    chips = ['TUDO', 'NÃO MONTADOS', 'MONTADOS', 'CAIXAS', 'CONSUMÍVEIS', 'FAMÍLIA ›', 'POR RARIDADE ›', 'VENDER NÃO MONTADOS C/I']
    # chip rows (wrap)
    rows, cx, cy = [], 0, 0
    for c in chips:
        cw2 = S.text(0, 0, c, 10, QUIET, 'i700', 120, measure=True) + 22
        if cx + cw2 > inner:
            cx = 0; cy += 25 + 6
        rows.append((c, cx, cy, cw2)); cx += cw2 + 6
    chip_h = cy + 25
    h = 17 + 20 + 10 + chip_h + 10 + 3 * cell_h + 12
    panel(S, x, y, w, h)
    S.label(x + 17, y + 17, 'COFRE  ·  23 ITENS', 12, ACCENT_HOT, 220)
    by = y + 17 + 20 + 10
    for k, (c, ox, oy, cw2) in enumerate(rows):
        on = k == 0; sell = k == 7
        S.plate(x + 17 + ox, by + oy, cw2, 25, fill=(ACCENT, 0.95) if on else ((80, 20, 12), 0.75) if sell else (PLATE, 0.6), edge=None, corner=6)
        S.text(x + 17 + ox + 11, by + oy + 4, c, 10, INK if on else (255, 150, 120) if sell else QUIET, 'i700', 120)
    gy = by + chip_h + 10
    items = [('cache', 'ELITE CACHE', 'Caixa  ·  10 cartas', 2, 'cache_2', None), ('cache', 'ADVANCED CACHE', 'Caixa  ·  8 cartas', 1, 'cache_1', None),
             (4, 'Aurora Streamliner', 'Blindagem  ·  L  ·  +60 kg', None, None, 'vortex_armor_lg'),
             (3, 'Slipstream Fold', 'Asas  ·  M  ·  −10 kg', None, None, 'vortex_wing_ep'),
             (3, 'Regen Ion Core', 'Motor  ·  M', None, None, 'vortex_engine_ep'), (2, 'Vector Blade', 'Asas  ·  M  ·  −4 kg', None, None, 'vortex_wing_vector'),
             (2, 'Twin Keel', 'Cauda  ·  S', None, None, 'vortex_tail_twin'), (1, 'Radiador NACA', 'Refrigeração  ·  M', None, None, 'vortex_cooling_radiator'),
             (1, 'Glide Wing', 'Asas  ·  S  ·  −2 kg', None, None, 'vortex_wing_glide'), (0, 'Guard Kit', 'Blindagem  ·  S', None, None, 'vortex_armor_guard'),
             ('con', 'Surge', 'Consumível  ·  ×3', None, 'con_surge', None), ('con', 'Foam', 'Consumível  ·  ×2', None, 'con_foam', None)]
    chipsets = {4: [('+12 Veloc.', 1), ('+6 Estab.', 1), ('−4 Manobra', -1)], 3: [('+9 Manobra', 1), ('+4 Estab.', 1)], 2: [('+6 Manobra', 1)], 1: [('+3 Estab.', 1)], 0: [('+1 Casco', 1)]}
    values = {4: 18400, 3: 7200, 2: 2400, 1: 900, 0: 300}
    for k, it in enumerate(items):
        cx = x + 17 + (k % 4) * cell_w + 8
        cy = gy + (k // 4) * cell_h + 8
        kind = it[0]
        if kind == 'cache':
            S.card(cx, cy, s, it[3], it[1], it[2], [], 6000 if it[3] == 2 else 2500, None, icon=it[4], fs=1.0, label='CAIXA')
        elif kind == 'con':
            S.card(cx, cy, s, None, it[1], it[2], [('+30% nitro', 1)] if it[1] == 'Surge' else [('apaga fogo', 0)], 150, 'con_' + it[1].lower(), fs=1.0)
        else:
            S.card(cx, cy, s, kind, it[1], it[2], chipsets[kind], values[kind], it[5], tag='MONTADA' if k in (3, 6) else None, picked=k == 2, fs=1.0)
    S.text(x + w - 17, y + 19, '3 / 23', 10, QUIET, 'i700', 120, align='r')
    # right: the module looked at
    rx, rw = W - 43 - 470, 470
    ls = 1.2
    ih = 17 + 20 + 12 + CH * ls + 12 + 3 * (60 + 6) + 40 + 12
    panel(S, rx, y, rw, ih, top=True)
    S.label(rx + 17, y + 17, 'MÓDULO', 12, ACCENT_HOT, 220)
    S.card(rx + (rw - CW * ls) / 2, y + 17 + 20 + 12, ls, 4, 'Aurora Streamliner', 'Blindagem  ·  L  ·  +60 kg', chipsets[4], 18400, 'vortex_armor_lg', new=True, fs=1.0)
    iy = y + 17 + 20 + 12 + CH * ls + 12
    for lab, t, sub, col in (('ESTADO', 'Não montado', 'Pode ser vendido', QUIET), ('VALOR', '18 400 STARDUST', 'Venda: 4 600 (25%)', GOLD),
                             ('NAVE', 'Só VORTEX', 'Kit de carroçaria (design próprio)', RARITY[4])):
        S.plate(rx + 17, iy, rw - 34, 60, fill=(PLATE, 0.55), edge=(ACCENT_HOT, 0.14), corner=8)
        S.rect(rx + 17 + 2, iy + 10, 4, 46, col)
        S.text(rx + 17 + 18, iy + 9, lab, 9, col, 'i700', 180)
        S.text(rx + 17 + 18, iy + 23, t, 14, FORE, 'i700')
        S.text(rx + 17 + 18 + 220, iy + 26, sub, 10, QUIET, 'i400')
        iy += 66
    S.text(rx + 17, iy + 4, 'Enter vende  ·  T segura  ·  ⌫ vende os não montados C/I', 11, FORE, 'i400', alpha=0.85)
    S.keybar([(['W', 'S'], 'Linha'), (['A', 'D'], 'Carta'), (['Espaço'], 'Filtro'), (['T'], 'Ordem'), (['⌫'], 'Vender C/I'), (['Q', 'E'], 'Separador')],
             (['Esc'], 'Voltar'))
    S.save(D + 'ui_cofre.png')
    return h


# ------------------------------------------------------------------------------------------------------------- an opened cache
def caixa():
    S = Screen(BG)
    topbar(S, 4)
    S.rect(0, 0, W, H, (4, 10, 26), 0.62)
    S.comp(tint(nine('ui_vignette', W, H, (0.0,) * 4, 1.0), INK, 0.9), 0, 0)
    S.title(W / 2, 101, 'ELITE CACHE', 31, FORE, 140, align='c')
    S.text(W / 2, 101 + 52, '10 CARTAS  ·  2 ÉPICAS  ·  1 LENDÁRIA  ·  ENTER REVELA UMA, ESPAÇO TODAS', 12, QUIET, 'i600', 120, align='c')
    gx, gy = (W - 1360) / 2, 214 - 22 - 10
    cards = [(4, 'Aurora Streamliner', 'Blindagem  ·  L  ·  +60 kg', [('+12 Veloc.', 1), ('+6 Estab.', 1)], 18400, 'vortex_armor_lg', True),
             (1, 'Glide Wing', 'Asas  ·  S  ·  −2 kg', [('+3 Estab.', 1)], 900, 'vortex_wing_glide', False),
             (3, 'Regen Ion Core', 'Motor  ·  M', [('+8 Veloc.', 1), ('+5 Acel.', 1)], 7600, 'vortex_engine_ep', True),
             (0, 'Guard Kit', 'Blindagem  ·  S', [('+1 Casco', 1)], 300, 'vortex_armor_guard', False),
             (2, 'Twin Keel', 'Cauda  ·  S', [('+5 Estab.', 1)], 2400, 'vortex_tail_twin', False),
             (None, 'Surge', 'Consumível  ·  ×2', [('+30% nitro', 1)], 150, 'con_surge', False),
             (3, 'Slipstream Fold', 'Asas  ·  M  ·  −10 kg', [('+9 Manobra', 1), ('+4 Estab.', 1)], 7200, 'vortex_wing_ep', True),
             None, None, None]
    for k, c in enumerate(cards):
        hx = gx + 22 + (k % 5) * (CW + 19)
        hy = gy + 22 + 10 + (k // 5) * (CH + 19)
        if c is None:
            S.glow(hx, hy, CW, CH, ACCENT, 0.3, 22)
            S.card(hx, hy, 1.0, None, '', '', back=True)
            continue
        rar, t, m, ch, v, th, shine = c
        if shine:
            hy -= 10
        col = RARITY[rar] if rar is not None else ACCENT
        S.glow(hx, hy, CW, CH, col, 0.75 if shine else 0.45, 35 if shine else 22)
        S.card(hx, hy, 1.0, rar, t, m, ch, v, th, new=shine)
    sw = 1360 - 44; sx = (W - sw) / 2; sy = 924
    S.plate(sx, sy, sw, 68, fill=(PLATE, 0.82), edge=(ACCENT, 0.5), corner=16)
    xx = sx + 22
    xx += S.text(xx, sy + 24, 'Até agora: ', 12, QUIET, 'i400')
    xx += S.title(xx, sy + 20, '37 350', 15, GOLD, 20) + 5
    xx += S.coin(xx, sy + 23, 10)
    xx += S.text(xx, sy + 24, '  ·  custou ', 12, QUIET, 'i400')
    xx += S.text(xx, sy + 24, '6 000', 12, QUIET, 'i400') + 5
    S.coin(xx, sy + 24, 9)
    kw = S.text(0, 0, 'GUARDAR TUDO', 11, INK, 'i900', 160, measure=True) + 44
    vw = S.text(0, 0, 'VENDER COMUNS (25%)', 11, FORE, 'i900', 160, measure=True) + 44
    kx = sx + sw - 22 - kw
    S.comp(nine('ui_btn', kw, 40, (0.125, 0.3, 0.125, 0.3), 40 / 72.0), kx, sy + 14)
    S.text(kx + 22, sy + 24, 'GUARDAR TUDO', 11, INK, 'i900', 160)
    vx = kx - 12 - vw
    S.plate(vx, sy + 14, vw, 40, fill=((80, 20, 12), 0.7), edge=(DANGER, 0.9), corner=8)
    S.text(vx + 22, sy + 24, 'VENDER COMUNS (25%)', 11, FORE, 'i900', 160)
    S.keybar([(['Enter'], 'Revelar'), (['Espaço'], 'Revelar todas'), (['⌫'], 'Vender comuns')], (['Esc'], 'Fechar'))
    S.save(D + 'ui_caixa.png')


# ------------------------------------------------------------------------------------------------------------- hangar: ship
def nave():
    S = Screen(BG)
    topbar(S, 0)
    x, y, w = 43, 110, 504
    ships = [('VORTEX', 'Velocista  ·  asas de ponta dobrada', 4, 3), ('BASTION', 'Tanque  ·  airbags de impacto', 5, 1),
             ('STRIX', 'Equilibrada  ·  motor central', 4, 0), ('WRAITH', 'Furtiva  ·  forquilha dupla', 3, 2), ('NOMAD', 'Veterana  ·  cápsulas nas asas', 4, 0)]
    rowh = 14 + 26 + 4 + 17 + 14
    h = 17 + 20 + 12 + 5 * (rowh + 10) + 12
    panel(S, x, y, w, h)
    S.label(x + 17, y + 17, 'NAVES  ·  5', 12, ACCENT_HOT, 220)
    ry = y + 17 + 20 + 12
    for k, (n, role, lives, stars) in enumerate(ships):
        on = k == 0
        S.plate(x + 17, ry, w - 34, rowh, fill=(PICK, 0.92) if on else (PLATE, 0.62), edge=(ACCENT, 0.95) if on else (ACCENT_HOT, 0.14), corner=8)
        if on:
            S.rect(x + 17 + 2, ry + 10, 5, rowh - 14, ACCENT)
        S.title(x + 17 + 22, ry + 12, n, 16, FORE, 80)
        S.text(x + 17 + 22, ry + 14 + 26 + 4, role, 10, QUIET, 'i600', 100)
        for i in range(5):
            c = OK if i < lives else (FORE)
            a = 1.0 if i < lives else 0.12
            dia = Image.new('RGBA', (16, 16)); ImageDraw.Draw(dia).polygon([(8, 1), (15, 8), (8, 15), (1, 8)], fill=c + (int(255 * a),))
            S.comp(dia, x + w - 17 - 17 - (5 - i) * 15, ry + 14)
        for i in range(7):
            c = GOLD if i < stars else FORE
            a = 1.0 if i < stars else 0.1
            dia = Image.new('RGBA', (11, 11)); ImageDraw.Draw(dia).polygon([(5.5, 0.5), (10.5, 5.5), (5.5, 10.5), (0.5, 5.5)], fill=c + (int(255 * a),))
            S.comp(dia, x + w - 17 - 17 - (7 - i) * 12, ry + 38)
        ry += rowh + 10
    # the ship's name over the turntable
    S.title(W / 2, 110, 'VORTEX', 52, FORE, 100, align='c', shadow=True)
    S.label(W / 2, 110 + 82, 'VELOCISTA  ·  ASAS DE PONTA DOBRADA', 12, ACCENT_HOT, 300, align='c')
    sx = W / 2 - 140
    for i in range(7):
        c = GOLD if i < 3 else FORE; a = 1.0 if i < 3 else 0.18
        dia = Image.new('RGBA', (17, 17)); ImageDraw.Draw(dia).polygon([(8.5, 1), (16, 8.5), (8.5, 16), (1, 8.5)], fill=c + (int(255 * a),))
        S.comp(dia, sx + i * 18.5, 110 + 112)
    S.label(sx + 7 * 18.5 + 12, 110 + 112, '3/7 ESTRELAS', 11, GOLD, 160)
    # right: the ship's info
    rx, rw = W - 43 - 470, 470
    rows = [('PASSIVA', 'Corrente de ar', 'Ganha velocidade colado a outra nave (vácuo).', ACCENT),
            ('CARGA', '8 módulos montados', 'Asas épicas, motor raro, blindagem incomum.', RARITY[3]),
            ('EM RISCO', '18 420 STARDUST', 'O que fica no porquinho se fores destruído.', GOLD),
            ('SEGURO', 'Vanta Ion Mk II', 'Nunca se perde nesta expedição.', OK)]
    ih = 17 + 20 + 12 + len(rows) * (66 + 6) + 12
    panel(S, rx, y, rw, ih, top=True)
    S.label(rx + 17, y + 17, 'A NAVE', 12, ACCENT_HOT, 220)
    iy = y + 17 + 20 + 12
    for lab, t, sub, col in rows:
        S.plate(rx + 17, iy, rw - 34, 66, fill=(PLATE, 0.55), edge=(ACCENT_HOT, 0.14), corner=8)
        S.rect(rx + 17 + 2, iy + 10, 4, 52, col)
        S.text(rx + 17 + 18, iy + 9, lab, 9, col, 'i700', 180)
        S.text(rx + 17 + 18, iy + 23, t, 14, FORE, 'i700')
        S.text(rx + 17 + 18, iy + 44, sub, 10, QUIET, 'i400')
        iy += 72
    stats(S)
    S.text(W - 43 - 22 + 0, H - 74 - 62 - 26, 'PELOTÃO 15  ·  16 naves', 11, FORE, 'i700', 140, outline=1, align='r')
    S.button(rx, H - 74 - 62, 470, 62, 'LANÇAR EXPEDIÇÃO')
    S.keybar([(['W', 'S'], 'Nave'), (['Enter'], 'Lançar'), (['Q', 'E'], 'Separador'), (['Tab'], 'Trocar nave')], (['Esc'], 'Voltar'))
    S.save(D + 'ui_nave.png')


if __name__ == '__main__':
    which = sys.argv[1:] or ['menu', 'nave', 'equipar', 'cofre', 'caixa']
    for n in which:
        r = globals()[n]()
        print(n, 'ok', r if r else '')
    # small copies for the docs
    for n in which:
        Image.open(D + 'ui_%s.png' % n).convert('RGB').save(D + '%s.jpg' % n, quality=90)
