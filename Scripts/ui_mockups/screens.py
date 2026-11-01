"""The menu and hangar screens as the code lays them out (EXMainMenuWidget, EXHangarWidget), in the HUD's look, over a render
of the workshop (hangar_scene.py). python3 Scripts/ui_mockups/screens.py [menu nave equipar cofre caixa resultados logos]; UI_MOCK_OUT sets
the folder (default Docs/UI_MAQUETAS), UI_MOCK_BG the workshop (default <folder>/hangar_bg.png), UI_MOCK_RACE_BG the race
behind the results (default <folder>/race_bg.png, e.g. the HUD mock-up's scene).
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
def menu(logo=None, out='ui_menu.png'):
    S = Screen(BG)
    shade_left(S)
    S.label(58, 29, 'EXPEDIÇÃO 01  ·  RED DUST DIVIDE', 11, ACCENT_HOT, 220)
    S.wallet(W - 58, 17, '12 750')
    if logo is not None:
        S.comp(logo.resize((624, 182), Image.LANCZOS), 77, 115 + 19)
    else:
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
    S.save(D + out)
    return S


# ------------------------------------------------------------------------------------------------------------- hangar: equip
def equipar():
    S = Screen(BG)
    topbar(S, 1)
    x, y, w = 43, 110, 420
    slots = [('MOTOR', 'Vanta Ion Mk II', 2, 'M', True, 'vortex_engine_2'), ('PROPULSÃO', 'Nitro Coil', 1, 'S', False, 'vortex_prop_1'),
             ('ASAS', 'Vector Blade', 2, 'M', False, 'vortex_wing_vector'), ('CAUDA', 'Twin Keel', 1, 'S', False, 'vortex_tail_twin'),
             ('BLINDAGEM', 'Aegis Kit', 2, 'L', False, 'vortex_armor_aegis'), ('REATOR', 'De série', None, 'M', False, 'vortex_ship'),
             ('REFRIGERAÇÃO', 'Radiador NACA', 1, 'M', False, 'vortex_cooling_radiator'), ('UTILIDADE', 'Scanner', 0, 'S', False, 'vortex_utility_dome')]
    h = 17 + 20 + 12 + 8 * 66 + 4 + 17 + 12
    panel(S, x, y, w, h)
    S.label(x + 17, y + 17, 'SLOTS DA VORTEX', 12, ACCENT_HOT, 220)
    sy = y + 17 + 20 + 12
    for k, (fam, name, rar, size, ins, thumb) in enumerate(slots):
        on = k == 2
        col = RARITY[rar] if rar is not None else QUIET
        S.plate(x + 17, sy, w - 34, 60, fill=(PICK, 0.92) if on else (PLATE, 0.55), edge=(ACCENT, 0.95) if on else (ACCENT_HOT, 0.14), corner=8)
        S.rect(x + 17 + 2, sy + 10, 3, 60 - 14, col)
        S.rect(x + 17 + 17, sy + 9, 66, 42, ACCENT_HOT, 0.3)
        S.photo(thumb, x + 17 + 18, sy + 10, 64, 40)
        S.text(x + 17 + 95, sy + 12, fam, 9, QUIET, 'i700', 180)
        S.text(x + 17 + 95, sy + 28, name, 13, col if rar else FORE, 'i700', alpha=1 if rar else 0.8)
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
             (None, 'De série', 'sem bónus, nunca se perde', [], None, 'vortex_ship', False)]
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
            S.card(cx, cy, s, 4 if it[3] == 2 else 2, it[1], it[2], [], 10000 if it[3] == 2 else 6000, 'cache_%d' % it[3], fs=1.0, label='CAIXA POR ABRIR')
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


# ------------------------------------------------------------------------------------------------------------- hangar: consumables
def consumiveis():
    S = Screen(BG)
    topbar(S, 2)
    x, y, w = 43, 110, 504
    h = 17 + 20 + 14 + 446 + 14 + 29 + 4 + 12
    panel(S, x, y, w, h)
    S.label(x + 17, y + 17, '4 SLOTS RÁPIDOS  ·  ATÉ 2 DE CADA', 12, ACCENT_HOT, 220)
    ox, oy = x + 17 + (w - 34 - 446) / 2, y + 17 + 20 + 14
    tiles = [('Surge', 'con_surge', 2, (255, 170, 60)), ('Foam', 'con_foam', 1, (240, 240, 240)), ('Coolant', 'con_coolant', 2, (90, 200, 255)),
             ('Fuel', 'con_fuel', 1, (255, 120, 60))]
    cells = [(152, 0), (152, 304), (0, 152), (304, 152)]
    arrows = ['▲', '▼', '◀', '▶']
    for k, ((name, thumb, count, col), (cx, cy)) in enumerate(zip(tiles, cells)):
        tx, ty = ox + cx, oy + cy
        on = k == 0
        S.plate(tx, ty, 142, 142, fill=(PICK, 0.92) if on else (PLATE, 0.6), edge=(ACCENT, 0.95) if on else (ACCENT_HOT, 0.2), corner=12)
        S.photo(thumb, tx + 17, ty + 16 + 6, 108, 69)
        S.text(tx + 71, ty + 16 + 6 + 69 + 6, name, 11, FORE, 'i700', align='c')
        for p in range(2):
            c = ACCENT if p < count else FORE
            a = 1.0 if p < count else 0.15
            dia = Image.new('RGBA', (13, 13)); ImageDraw.Draw(dia).polygon([(6.5, 0.5), (12.5, 6.5), (6.5, 12.5), (0.5, 6.5)], fill=c + (int(255 * a),))
            S.comp(dia, tx + 71 - 13 + p * 16 - 1, ty + 16 + 6 + 69 + 6 + 21)
        S.plate(tx + 9, ty + 9, 22, 22, fill=(INK, 0.0), edge=(ACCENT_HOT, 0.7), corner=4)
        S.text(tx + 20, ty + 11, str(k + 1), 10, FORE, 'i800', align='c')
        S.text(tx + 142 - 10, ty + 8, arrows[k], 10, ACCENT, 'i700', align='r')
    S.icon('ui_dpad', ox + 152 + 29, oy + 152 + 29, 84, 84)
    kx, ky = x + 17, oy + 446 + 14
    kx += S.text(kx, ky + 5, 'Teclado', 12, QUIET, 'i400') + 8
    for k in range(4):
        kx += S.keycap(kx, ky, str(k + 1)) + 7
    kx += S.text(kx + 4, ky + 5, '·  Comando', 12, QUIET, 'i400') + 12
    for a in arrows:
        kx += S.keycap(kx, ky, a) + 7
    # right: the stock as cards with the 3D photos
    sw = 3 * (CW * 0.66 + 16) + 34
    rx = W - 43 - sw
    stock = [('Surge', 'con_surge', '+30% nitro', 4, 150), ('Foam', 'con_foam', 'apaga o fogo', 3, 120),
             ('Coolant', 'con_coolant', '−60% calor', 2, 140), ('Fuel', 'con_fuel', '+35% comb.', 5, 110),
             ('Nanogel', 'con_nanogel', '+25% casco', 1, 260)]
    cell_w, cell_h = CW * 0.66 + 16, CH * 0.66 + 16
    sh = 17 + 20 + 12 + 2 * cell_h + 12
    panel(S, rx, y, sw, sh)
    S.label(rx + 17, y + 17, 'STOCK SEGURO  ·  CLICA PARA PÔR NO SLOT', 12, ACCENT_HOT, 220)
    for k, (name, thumb, eff, n, price) in enumerate(stock):
        cx = rx + 17 + (k % 3) * cell_w + 8
        cy = y + 17 + 20 + 12 + (k // 3) * cell_h + 8
        S.card(cx, cy, 0.66, None, name, 'Consumível  ·  ×%d' % n, [(eff, 1 if '+' in eff else 0)], price, thumb, picked=k == 0,
               fs=0.66 / 0.74)
    # the summary under the slots
    qw = 756; qx = (W - qw) / 2; qy = H - 74 - 64
    S.plate(qx, qy, qw, 64, fill=(PLATE, 0.82), edge=(ACCENT, 0.5), corner=16)
    S.text(qx + 22, qy + 13, 'Levas para a expedição: Surge ×2, Foam ×1, Coolant ×2, Fuel ×1.', 12, FORE, 'i400', alpha=0.9)
    S.text(qx + 22, qy + 34, 'Se fores destruído perdes os consumíveis que levas; o stock seguro fica no cofre.', 12, FORE, 'i400', alpha=0.9)
    S.keybar([(['W', 'S'], 'Slot'), (['A', 'D'], 'Consumível'), (['Enter'], 'Pôr no slot'), (['⌫'], 'Tirar'), (['Q', 'E'], 'Separador')],
             (['Esc'], 'Voltar'))
    S.save(D + 'ui_consumiveis.png')


# ------------------------------------------------------------------------------------------------------------- results
RACE_BG = os.environ.get('UI_MOCK_RACE_BG', D + 'race_bg.png')


def resultados():
    """UEXResultsWidget after an extraction in 1st place: the race blurred and darkened, the verdict, the ledger, the cards
    from the piggy bank and the classification."""
    S = Screen(None)
    S.im = Image.open(RACE_BG).convert('RGBA').resize((W, H)).filter(ImageFilter.GaussianBlur(9))
    S.rect(0, 0, W, H, INK, 0.66)
    win = (95, 230, 130)
    g = np.zeros((H, W, 4), np.uint8); g[..., :3] = win
    g[..., 3] = (np.linspace(0.16, 0, W)[None, :] * 255).astype(np.uint8)
    S.comp(Image.fromarray(g, 'RGBA'), 0, 0)
    S.rect(0, 0, W, 6, win)
    top = 222
    # left: the verdict
    x = 70
    S.label(x, top, 'EXPEDIÇÃO  ·  RED DUST DIVIDE', 11, ACCENT_HOT, 300)
    tw = S.title(x, top + 26, 'EXTRAÍDO', 52, win, 60)
    mx, my = x + tw + 24, top + 26
    S.plate(mx, my, 92, 74, fill=((255, 205, 70), 1.0), edge=None, corner=10)
    S.title(mx + 46, my + 4, '1.º', 34, INK, 0, align='c')
    S.text(mx + 46, my + 52, 'OURO', 10, INK, 'i800', 250, align='c')
    S.title(x, top + 22 + 92, 'VITÓRIA  ·  1.º DE 16', 18, FORE, 60)
    sy = top + 22 + 92 + 30 + 22
    for k, (cap, val, col) in enumerate((('TEMPO', '9:46,3', FORE), ('CHECKPOINTS', '8 / 8', OK), ('DISTÂNCIA', '59,0 km', FORE))):
        sx = x + [0, 170, 380][k]
        S.label(sx, sy, cap, 10, QUIET, 200)
        S.title(sx, sy + 20, val, 22, col, 20)
    # left: the ledger
    ly = sy + 58 + 26
    lines = [('Lugar  ·  1.º', '+2 100', OK), ('Bónus de extração', '+250', OK), ('Checkpoints  ·  8 × 40  +  todos', '+620', OK),
             ('Primeira extração', '+500', OK), ('Do porquinho  ·  3 peças (valor)', '+9 800', GOLD)]
    lh = 20 + 18 + 14 + len(lines) * 24 + (len(lines) - 1) * 10 + 14 + 1 + 12 + 46 + 22
    S.plate(x, ly, 520, lh, fill=(PLATE, 0.9), edge=(ACCENT, 0.5), corner=16)
    S.rect(x + 2, ly + 20, 4, lh - 26, OK)
    yy = ly + 20
    S.label(x + 26, yy, 'GANHOS', 11, ACCENT_HOT, 300)
    yy += 18 + 14
    for what, amount, col in lines:
        S.text(x + 26, yy, what, 13, QUIET, 'i600')
        S.text(x + 520 - 26, yy - 1, amount, 14, col, 'i800', align='r')
        yy += 34
    yy += 14 - 10
    S.rect(x + 26, yy, 520 - 52, 1, FORE, 0.15)
    yy += 13
    S.text(x + 26, yy + 13, 'TOTAL EM STARDUST', 13, FORE, 'i800', 120)
    cw_ = 14 * 1.3
    S.coin(x + 520 - 26 - cw_, yy + 13, 14)
    S.title(x + 520 - 26 - cw_ - 8, yy + 2, '+13 270', 28, OK, 20, align='r')
    # middle: the cards from the piggy bank
    px = x + 520 + 36
    S.icon('Celebrate_00', px, top - 16, 56, 54, folder=R + 'SourceArt/UI/Piggy/HD2x/frames/')
    S.text(px + 66, top + 4, 'ESPÓLIO GANHO  ·  PORQUINHO', 11, GOLD, 'i800', 300)
    cards = [(3, 'vortex_engine_ep', 'Regen Ion Core', 7600, 'PORQUINHO', ACCENT), (2, 'vortex_wing_vector', 'Vector Blade', 2400, 'PORQUINHO', ACCENT),
             (1, 'vortex_cooling_radiator', 'Radiador NACA', 900, 'PORQUINHO', ACCENT), (2, 'vortex_armor_aegis', 'Aegis Kit', 3100, 'SEGURA', (80, 230, 255))]
    for k, (rar, thumb, name, val, tag, tcol) in enumerate(cards):
        cx, cy = px + k * (168 + 12), top + 26 + 14
        col = RARITY[rar]
        S.shape('card', '', cx, cy, 168, 236, 12, PLATE, 0.95)
        S.shape('card', '_inset', cx, cy, 168, 236, 12, col, 0.25)
        S.rect(cx, cy, 168, 6, col)
        S.photo(thumb, cx + 12, cy + 16, 144, 92)
        S.rect(cx + 12, cy + 16 + 92, 144, 2, col)
        S.shape('card', '_edge', cx, cy, 168, 236, 12, col, 1.0)
        yy0 = cy + 16 + 92 + 2 + 9
        S.text(cx + 84, yy0, RARITY_NAME[rar], 10, col, 'i800', 200, align='c')
        S.text(cx + 84, yy0 + 21, name, 13, FORE, 'i700', align='c')
        S.text(cx + 84, yy0 + 21 + 25, '{:,}'.format(val).replace(',', ' '), 14, GOLD, 'i800', align='c')
        tw = S.text(0, 0, tag, 9, INK, 'i800', 150, measure=True) + 20
        ty = yy0 + 21 + 25 + 27
        S.plate(cx + 84 - tw / 2, ty, tw, 19, fill=(tcol, 0.9), edge=None, corner=4)
        S.text(cx + 84 - tw / 2 + 10, ty + 2, tag, 9, INK, 'i800', 150)
    S.text(px, top + 26 + 14 + 236 + 14, 'Porquinho da expedição: 24 600 STARDUST em peças dos destruídos, repartido por quem extraiu', 11, QUIET, 'i600')
    # right: the classification
    rx, rw = W - 70 - 470, 470
    racers = [('TU', 1, '9:46,3', '+3 470'), ('WRAITH #4', 1, '9:51,8', '+2 720'), ('STRIX #7', 1, '9:58,0', '+2 380'),
              ('NOMAD #2', 1, '10:04,6', '+2 110'), ('BASTION #9', 1, '10:12,9', '+1 870'), ('VORTEX #3', 1, '~10:20,4', '+1 650'),
              ('STRIX #5', 2, 'km 41,2', '-6 200'), ('WRAITH #8', 1, '~10:31,7', '+1 430'), ('NOMAD #6', 2, 'km 33,9', '-3 900'),
              ('BASTION #1', 0, 'a caminho', ''), ('VORTEX #12', 2, 'km 27,5', '-8 100'), ('STRIX #11', 0, 'a caminho', ''),
              ('WRAITH #13', 2, 'km 18,0', '-2 600'), ('NOMAD #10', 0, 'a caminho', ''), ('BASTION #14', 2, 'km 9,4', '-3 800'),
              ('VORTEX #15', 0, 'a caminho', '')]
    rowh = 27
    rh = 18 + 18 + 12 + len(racers) * rowh + (len(racers) - 1) * 2 + 18
    S.plate(rx, top, rw, rh, fill=(PLATE, 0.9), edge=(ACCENT, 0.5), corner=16)
    S.rect(rx + 2, top + 20, 4, rh - 26, ACCENT)
    S.label(rx + 22, top + 18, 'CLASSIFICAÇÃO', 11, ACCENT_HOT, 300)
    yy = top + 18 + 18 + 12
    for k, (name, state, res, money) in enumerate(racers):
        me = name == 'TU'
        col = (80, 230, 255) if me else DANGER if state == 2 else FORE if state == 1 else QUIET
        if me:
            S.plate(rx + 22, yy, rw - 40, rowh, fill=(ACCENT, 0.16), edge=None, corner=6)
        bx = rx + 22 + 8
        S.title(bx, yy + 3, str(k + 1), 14, col)
        S.text(bx + 34 + 6, yy + 3, name, 13, col, 'i800' if me else 'i600')
        right = rx + rw - 18 - 8
        mxx = right - 64
        txx = mxx - 8 - 92
        rxx = txx - 8 - 80
        S.text(rxx, yy + 4, res, 12, col, 'i700')
        S.text(txx, yy + 6, ['ENCALHADO', 'EXTRAÍDO', 'DESTRUÍDO'][state], 10, DANGER if state == 2 else OK if state == 1 else QUIET, 'i800', 100)
        S.text(mxx, yy + 4, money, 12, DANGER if state == 2 else GOLD, 'i800')
        yy += rowh + 2
    # the key, bottom right of the page
    kw = S.text(0, 0, 'RECOLHER E CONTINUAR', 12, QUIET, 'i400', measure=True)
    S.hint(W - 70 - kw - 2 - (max(31, S.text(0, 0, 'Enter', 11, FORE, measure=True) + 16) + 7) - (31 + 7), top + rh + 30,
           ['Enter', 'X'], 'RECOLHER E CONTINUAR')
    S.save(D + 'ui_resultados.png')


def logos():
    """The menu with the logo in three colours, side by side: orange (now), cyan and white (to choose)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('icons', R + 'Scripts/make_ui_icons.py')
    src = open(R + 'Scripts/make_ui_icons.py').read()
    fn = src[src.index('def art_logo():'):src.index('def art_fade_h():')]
    ns = {'os': os, 'Image': Image, 'ImageDraw': __import__('PIL.ImageDraw', fromlist=['x']), 'ImageFont': __import__('PIL.ImageFont', fromlist=['x']),
          'ImageFilter': ImageFilter, 'FONTS': R + 'Content/UI/Fonts'}
    variants = [('LARANJA (AGORA)', None),
                ('CIANO', {'(242, 230, 204, 255)': '(238, 245, 255, 255)', '(255, 176, 103)': '(190, 245, 255)', '(226, 85, 28)': '(40, 150, 255)',
                           '(120, 30, 6, 0)': '(2, 16, 44, 0)', '(235, 87, 26, 255)': '(70, 220, 255, 255)'}),
                ('BRANCO', {'(242, 230, 204, 255)': '(150, 225, 255, 255)', '(255, 176, 103)': '(255, 255, 255)', '(226, 85, 28)': '(176, 204, 236)',
                            '(120, 30, 6, 0)': '(3, 8, 20, 0)', '(235, 87, 26, 255)': '(70, 220, 255, 255)'})]
    tiles = []
    for name, swap in variants:
        code = fn
        for a, b in (swap or {}).items():
            code = code.replace(a, b)
        exec(code, ns)
        S = menu(ns['art_logo'](), 'ui_logo_tmp.png')
        tile = S.im.crop((0, 0, 820, 900)).resize((492, 540), Image.LANCZOS)
        Sx = Screen(None); Sx.im = Image.new('RGBA', (492, 590), (6, 10, 18, 255)); Sx.comp(tile, 0, 50)
        Sx.label(16, 14, name, 13, FORE if swap else GOLD, 200)
        tiles.append(Sx.im)
    out = Image.new('RGBA', (492 * 3 + 24, 590), (6, 10, 18, 255))
    for k, t in enumerate(tiles):
        out.alpha_composite(t, (k * (492 + 12), 0))
    out.convert('RGB').save(D + 'ui_logos.png')
    os.remove(D + 'ui_logo_tmp.png')


if __name__ == '__main__':
    which = sys.argv[1:] or ['menu', 'nave', 'equipar', 'consumiveis', 'cofre', 'caixa', 'resultados']
    for n in which:
        r = globals()[n]()
        print(n, 'ok', r if r else '')
    # small copies for the docs
    for n in which:
        if os.path.exists(D + 'ui_%s.png' % n) and n != 'logos':
            Image.open(D + 'ui_%s.png' % n).convert('RGB').save(D + '%s.jpg' % n, quality=90)
