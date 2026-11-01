# Piggy bank sprite sheets for the HUD: python3 Scripts/piggy_sprites/build.py (needs numpy, pillow, scipy,
# opencv-python-headless). Reads SourceArt/UI/Piggy/source/porquinho_referencia.png, writes the sheets, the frames
# and Piggy_Spritesheet.json to SourceArt/UI/Piggy. PIGGY_PREVIEW=<png> also writes the master on a checkerboard.
import json, os
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import core

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'SourceArt', 'UI', 'Piggy')
os.makedirs(os.path.join(OUT, 'frames'), exist_ok=True)
MARGIN, GAP = int(round(6 * core.S)), int(round(8 * core.S))

def split_2d(rgba, body, n, P=None):
    """The n pigs of a panel, found by their pink bodies (they never touch, unlike the glows and lines between
    them), and for every other visible pixel the pig it belongs to (the nearest in 2D)."""
    h, w = body.shape
    R, G, B = P[..., 0], P[..., 1], P[..., 2]
    pink = (R > 150) & (R - G > 40) & (R - B > 25) & (B > 80)     # the skin, also under a burst's gold light
    pink = ndi.binary_opening(pink, iterations=1)
    lab, k = ndi.label(pink)
    if not k:
        return None
    sizes = ndi.sum(np.ones_like(lab), lab, range(1, k + 1))
    bounds = [int(w * i / n) for i in range(n + 1)]
    best = {}
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        if sizes[i - 1] < 250:
            continue
        ys, xs = np.where(lab == i)
        c = int(np.clip(np.searchsorted(bounds, xs.mean(), side='right') - 1, 0, n - 1))
        if c not in best or sizes[i - 1] > sizes[best[c] - 1]:
            best[c] = i          # one seed per frame: its biggest pink (a snout cut off by ink is grown in later)
    if len(best) < n:
        return None
    cell_of = {i: c for c, i in best.items()}
    seed = np.full((h, w), -1, np.int32)
    for i, c in cell_of.items():
        seed[lab == i] = c
    # the pig = its pink and the solid parts joined to it (backpack, outline), grown through the solid mask so a
    # backpack goes with its own pig, not with the neighbour whose pink is nearer
    owner = seed.copy()
    grow = body | (seed >= 0)
    for _ in range(120):
        moved = False
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.full_like(owner, -1)
            ys = slice(max(dy, 0), h + min(dy, 0)); yd = slice(max(-dy, 0), h + min(-dy, 0))
            xs = slice(max(dx, 0), w + min(dx, 0)); xd = slice(max(-dx, 0), w + min(-dx, 0))
            sh[ys, xs] = owner[yd, xd]
            take = (owner < 0) & grow & (sh >= 0)
            if take.any():
                owner[take] = sh[take]; moved = True
        if not moved:
            break
    # everything else visible goes to the nearest pig pixel
    _, (iy, ix) = ndi.distance_transform_edt(owner < 0, return_indices=True)
    full = np.where(rgba[..., 3] > 0, owner[iy, ix], -1)
    pigs = []
    for c in range(n):
        ys, xs = np.where(owner == c)
        pigs.append(dict(x0=xs.min(), x1=xs.max() + 1, y0=ys.min(), y1=ys.max() + 1, seed=(seed == c)))
    return pigs, full

def even_cells(w, n):
    return [int(w * i / n) for i in range(n + 1)]

def cut_mask(rgba, m, thr=2):
    sub = rgba.copy()
    sub[~m] = 0
    a = sub[..., 3] > thr
    ys, xs = np.where(a)
    if not len(ys):
        return None
    return dict(img=sub, bx0=xs.min(), bx1=xs.max() + 1, by0=ys.min(), by1=ys.max() + 1)

def cut(rgba, x0, x1, thr=2):
    m = np.zeros(rgba.shape[:2], bool)
    m[:, x0:x1] = True
    return cut_mask(rgba, m, thr)

def extract_char(name, align):
    x0, y0, x1, y1, n, kind, top = core.PANELS[name]
    P, valid = core.panel_valid(name)
    rgba, body = core.matte(P, valid, kind)
    res = split_2d(rgba, body, n, P)
    frames = []
    if res:
        pigs, full = res
        solids = []
        for i, p in enumerate(pigs):
            # the pig itself is opaque paint: its silhouette from the pink skin (the ink-only body can have gaps)
            core.drop_dark_pockets.P = P
            solid = core.pig_solid(p['seed'], full == i, core.matte.ink, core.matte.lights, core.matte.navy, body)
            soft = cv2.GaussianBlur(solid.astype(np.float32), (0, 0), 0.7)
            ring = (~solid) & (soft * 255 > rgba[..., 3]) & (full == i)
            rgba[solid] = np.dstack([P, np.full(P.shape[:2], 255.0)])[solid]
            if ring.any():
                dil = cv2.dilate(np.where(solid[..., None], P, 0).astype(np.float32), np.ones((3, 3), np.uint8))
                rgba[ring, :3] = dil[ring]
                rgba[ring, 3] = soft[ring] * 255
            ys, xs = np.where(solid)
            p['x0'], p['x1'], p['y1'] = xs.min(), xs.max() + 1, ys.max() + 1
        # full resolution: the same frames, pivots and feet, scaled
        rgba4 = core.render_hi(name, rgba)
        full4 = core.owner_hi(name, full, rgba4)
        for i, p in enumerate(pigs):
            c = cut_mask(rgba4, full4 == i)
            frames.append(dict(c=c, px=(p['x0'] + p['x1']) / 2 * core.S, feet=p['y1'] * core.S))
    else:  # no solid pigs (holograms): even cells, centred on what is strong there
        rgba4 = core.render_hi(name, rgba)
        b = even_cells(rgba.shape[1], n)
        for i in range(n):
            strong = cut(rgba, b[i], b[i + 1], thr=60)
            c = cut(rgba4, int(round(b[i] * core.S)), int(round(b[i + 1] * core.S)))
            frames.append(dict(c=c, px=(strong['bx0'] + strong['bx1']) / 2 * core.S, feet=strong['by1'] * core.S))
    ground = max(f['feet'] for f in frames)
    for f in frames:
        f['dy'] = (ground - f['feet']) if align == 'feet' else 0   # move down so the feet sit on the ground
    return frames, ground

def normalise(frames, ground):
    L = R = U = D = 0
    for f in frames:
        c = f['c']
        L = max(L, f['px'] - c['bx0']); R = max(R, c['bx1'] - f['px'])
        U = max(U, ground - (c['by0'] + f['dy'])); D = max(D, (c['by1'] + f['dy']) - ground)
    half = int(np.ceil(max(L, R))) + MARGIN
    W, H = 2 * half, int(np.ceil(U + D)) + 2 * MARGIN
    piv = (half, MARGIN + int(np.ceil(U)))
    out = []
    for f in frames:
        c = f['c']
        canvas = np.zeros((H, W, 4), np.float32)
        sx = int(round(piv[0] - f['px'])); sy = int(round(piv[1] - ground + f['dy']))
        src = c['img']
        h, w = src.shape[:2]
        ax0, ay0 = max(0, sx), max(0, sy)
        ax1, ay1 = min(W, sx + w), min(H, sy + h)
        canvas[ay0:ay1, ax0:ax1] = src[ay0 - sy:ay1 - sy, ax0 - sx:ax1 - sx]
        out.append(canvas)
    return out, (W, H), piv

def fx_items():
    """ELEMENTOS: each coin (a solid gold disc), each sparkle and star, the energy ring and the pad, split by colour
    (gold or blue) and by piece; the glow round each goes with the nearest piece of its colour."""
    P, valid = core.panel_valid('ELEMENTS')
    rgba, body = core.matte(P, valid, 'fx')
    R, G, B = rgba[..., 0], rgba[..., 1], rgba[..., 2]
    # effects are light: dark pixels only belong to the coins' outlines
    lab0, k0 = ndi.label(body)
    coinish = np.zeros_like(body)
    for i in range(1, k0 + 1):
        m = lab0 == i
        if m.sum() > 150 and (rgba[..., 0][m] > rgba[..., 2][m] + 40).mean() > 0.3:
            coinish |= m
    dark = (rgba[..., :3].max(axis=2) < 70) & ~ndi.binary_dilation(coinish, iterations=2)
    rgba[dark] = 0
    body = coinish
    A = rgba[..., 3]
    vis = A > 2
    gold = vis & (R >= B)
    blue = vis & (B > R)
    pieces = []          # (mask, class)
    lab, k = ndi.label(body & gold)
    coins = np.zeros_like(body)
    for i in range(1, k + 1):
        m = lab == i
        if m.sum() > 150:
            pieces.append((m, 'coin')); coins |= m
    bright = rgba[..., :3].max(axis=2) > 120
    lab, k = ndi.label(ndi.binary_dilation((A > 140) & gold & bright & ~ndi.binary_dilation(coins, iterations=4), iterations=4))
    for i in range(1, k + 1):
        m = (lab == i) & (A > 140) & bright
        if m.sum() >= 20:
            ys, xs = np.where(m)
            small = (xs.max() - xs.min()) * (ys.max() - ys.min()) < 900
            pieces.append((m, 'coin_sparkle' if small and xs.mean() < 180 else 'star'))
    lab, k = ndi.label(ndi.binary_dilation((A > 100) & blue & bright, iterations=6))
    for i in range(1, k + 1):
        m = (lab == i) & (A > 100) & bright
        if m.sum() >= 80:
            ys, xs = np.where(m)
            bw, bh = xs.max() - xs.min(), ys.max() - ys.min()
            pieces.append((m, 'energy_ring' if bw > 2.4 * bh else 'energy_pad'))
    items = []
    for cls_mask, colour in ((gold, ('coin', 'coin_sparkle', 'star')), (blue, ('energy_ring', 'energy_pad'))):
        idx = [j for j, (m, c) in enumerate(pieces) if c in colour]
        if not idx:
            continue
        seed = np.full(A.shape, -1, np.int32)
        for j in idx:
            seed[pieces[j][0]] = j
        _, (iy, ix) = ndi.distance_transform_edt(seed < 0, return_indices=True)
        near = seed[iy, ix]
        for j in idx:
            m = (near == j) & cls_mask
            c = cut_mask(rgba, m)
            if c is None:
                continue
            mm = m & (rgba[..., 3] > 2)
            l2, k2 = ndi.label(mm)
            for q in range(1, k2 + 1):
                mq = l2 == q
                if (rgba[..., :3].max(axis=2)[mq] > 120).sum() < 4:
                    mm[mq] = False
            if (rgba[..., :3].max(axis=2)[mm] > 120).sum() < 15:
                continue
            items.append(dict(cls=pieces[j][1], mask=mm, x=(c['bx0'] + c['bx1']) / 2, y=(c['by0'] + c['by1']) / 2))
    rgba4 = core.render_hi('ELEMENTS', rgba)
    h4, w4 = rgba4.shape[:2]
    for t in items:
        m4 = core.up(cv2.dilate(t['mask'].astype(np.uint8), np.ones((3, 3), np.uint8)), (w4, h4), nearest=True).astype(bool)
        c = cut_mask(rgba4, m4)
        t['img'] = c['img'][c['by0']:c['by1'], c['bx0']:c['bx1']]
    items.sort(key=lambda t: (round(t['y'] / 60), t['x']))
    return items

def pad_center(imgs):
    W = max(i.shape[1] for i in imgs) + 2 * MARGIN
    H = max(i.shape[0] for i in imgs) + 2 * MARGIN
    out = []
    for i in imgs:
        c = np.zeros((H, W, 4), np.float32)
        y, x = (H - i.shape[0]) // 2, (W - i.shape[1]) // 2
        c[y:y + i.shape[0], x:x + i.shape[1]] = i
        out.append(c)
    return out, (W, H), (W // 2, H // 2)

ANIMS = []
def add(name, frames, size, piv, fps, loop, names=None, note=None, file=None):
    ANIMS.append(dict(name=name, frames=frames, size=size, pivot=piv, fps=fps, loop=loop, names=names, note=note,
                      file=file or name.title().replace('_', '_') + '.png'))

spec = [('IDLE', 'IDLE', 'feet', 8, True, None),
        ('BLINK', 'BLINK', 'feet', 10, True, 'Tocar de vez em quando por cima do IDLE.'),
        ('RECEIVE_COINS', 'RECEIVE_COINS', 'feet', 12, False, None),
        ('REWARD_JUMP', 'REWARD_JUMP', 'panel', 10, False,
         'Falta um frame de descida: o 3.º é o ápice e o 4.º já é a aterragem (não foi desenhado).'),
        ('CELEBRATE', 'CELEBRATE', 'panel', 12, True, None)]
for anim, panel, align, fps, loop, note in spec:
    fr, g = extract_char(panel, align)
    imgs, size, piv = normalise(fr, g)
    add(anim, imgs, size, piv, fps, loop, note=note)

# REACTION: the 4 feedback states and the 8 expressions, one canvas for all
f1, g1 = extract_char('FEEDBACK', 'feet')
f2, g2 = extract_char('REACTIONS', 'feet')
for f in f2:
    f['dy'] += 0
allf = f1 + f2
# each set has its own ground: put both on one ground line
for f in f1:
    f['feet_rel'] = g1
for f in f2:
    f['feet_rel'] = g2
G = max(g1, g2)
for f in allf:
    f['dy'] += G - f['feet_rel']
imgs, size, piv = normalise(allf, G)
add('REACTION', imgs, size, piv, 0, False,
    names=['surpresa_exclamacao', 'duvida_interrogacao', 'alerta_aviso', 'sono_zz',
           'neutro_sorriso', 'alegria_olhos_fechados', 'choque_exclamacoes', 'choro', 'zanga_fumo', 'tonto_espiral',
           'amor_coracoes', 'contente_sonolento'],
    note='Estados (um frame cada), não uma sequência: escolher o frame pelo nome.')

fr, g = extract_char('MOVE', 'feet')
imgs, size, piv = normalise(fr, g)
add('MOVE', imgs, size, piv, 12, True, note='Só 3 frames no original: ciclo curto.')

fr, g = extract_char('TELEPORT', 'panel')
imgs, size, piv = normalise(fr, g)
add('TELEPORT', imgs, size, piv, 10, False, names=['entrada_feixe', 'materializado', 'saida_feixe'],
    note='Só 3 frames no original: não há frame de desaparecimento completo nem de reaparecimento separado; '
         'para a saída tocar ao contrário.')

items = fx_items()
coins = [t for t in items if t['cls'] in ('coin', 'coin_sparkle')]
glows = [t for t in items if t['cls'] not in ('coin', 'coin_sparkle')]
imgs, size, piv = pad_center([t['img'] for t in coins])
add('FX_COINS', imgs, size, piv, 0, False, names=[t['cls'] for t in coins], note='Peças soltas para partículas.')
imgs, size, piv = pad_center([t['img'] for t in glows])
add('FX_GLOW', imgs, size, piv, 0, False, names=[t['cls'] for t in glows], note='Peças soltas para efeitos.')

# extra: the 4 UI icons
P, valid = core.panel_valid('ICONS')
rgba, body = core.matte(P, valid, 'icon')
rgba4 = core.render_hi('ICONS', rgba)
b = even_cells(rgba.shape[1], 4)
icons = []
for i in range(4):
    c = cut(rgba4, int(round(b[i] * core.S)), int(round(b[i + 1] * core.S)), thr=40)
    icons.append(c['img'][c['by0']:c['by1'], c['bx0']:c['bx1']])
imgs, size, piv = pad_center(icons)
add('ICONS', imgs, size, piv, 0, False, names=['normal', 'moeda', 'coroa', 'escudo'], note='Extra: ícones de UI do original.')

FILES = {'IDLE': 'Idle.png', 'BLINK': 'Blink.png', 'RECEIVE_COINS': 'Receive_Coins.png', 'REWARD_JUMP': 'Reward_Jump.png',
         'CELEBRATE': 'Celebrate.png', 'REACTION': 'Reaction.png', 'MOVE': 'Move.png', 'TELEPORT': 'Teleport.png',
         'FX_COINS': 'FX_Coins.png', 'FX_GLOW': 'FX_Glow.png', 'ICONS': 'Icons.png'}

def to_img(a):
    return Image.fromarray(np.clip(np.round(a), 0, 255).astype(np.uint8), 'RGBA')

meta = {'source': 'reference sheet supplied by the player (%dx%d), cut and keyed, not redrawn' % (core.HI.shape[1], core.HI.shape[0]),
        'master': 'Piggy_Master_Spritesheet.png', 'gap_px': GAP, 'animations': []}
rows = []
for A in ANIMS:
    W, H = A['size']
    sheet = np.zeros((H, len(A['frames']) * (W + GAP) - GAP, 4), np.float32)
    for i, fimg in enumerate(A['frames']):
        sheet[:, i * (W + GAP): i * (W + GAP) + W] = fimg
        to_img(fimg).save(os.path.join(OUT, 'frames', '%s_%02d.png' % (FILES[A['name']][:-4], i)))
    to_img(sheet).save(os.path.join(OUT, FILES[A['name']]))
    rows.append(sheet)
MW = max(r.shape[1] for r in rows)
MH = sum(r.shape[0] for r in rows) + GAP * (len(rows) - 1)
master = np.zeros((MH, MW, 4), np.float32)
y = 0
for A, r in zip(ANIMS, rows):
    master[y:y + r.shape[0], :r.shape[1]] = r
    W, H = A['size']
    meta['animations'].append({
        'name': A['name'], 'file': FILES[A['name']], 'frames': len(A['frames']), 'frame_width': W, 'frame_height': H,
        'fps': A['fps'], 'loop': A['loop'],
        'pivot_px': list(A['pivot']), 'pivot_norm': [round(A['pivot'][0] / W, 4), round(A['pivot'][1] / H, 4)],
        'frame_names': A['names'],
        'rects_master': [[i * (W + GAP), y, W, H] for i in range(len(A['frames']))],
        'rects_own_sheet': [[i * (W + GAP), 0, W, H] for i in range(len(A['frames']))],
        'note': A['note']})
    y += r.shape[0] + GAP
to_img(master).save(os.path.join(OUT, 'Piggy_Master_Spritesheet.png'))
with open(os.path.join(OUT, 'Piggy_Spritesheet.json'), 'w') as f:
    json.dump(meta, f, indent=1, ensure_ascii=False)
for A in meta['animations']:
    print(A['name'], A['frames'], A['frame_width'], 'x', A['frame_height'], 'pivot', A['pivot_px'], A['frame_names'] if A['name'].startswith('FX') else '')
print('master', master.shape)
# preview on a checker for the review
if os.environ.get('PIGGY_PREVIEW'):
    Image.fromarray(core.checker(master)).save(os.environ['PIGGY_PREVIEW'])
