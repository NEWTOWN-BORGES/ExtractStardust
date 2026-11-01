# Piggy bank sprites (Porquinho Mealheiro) cut from the player's reference sheet, keyed, not redrawn.
# Matting: a navy background model, solid ink-enclosed paint kept opaque, glows keyed as light added over the
# background (true RGBA), the stage ellipse under the feet dropped. Used by build.py.
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi

import os
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'SourceArt', 'UI', 'Piggy', 'source', 'porquinho_referencia.png')
# The decisions (what is ink, glow, background, which frame) are made at the layout's own scale (1536 wide); the
# colours and the transparency are then worked out at the reference's full resolution (render_hi).
# The layout-scale copy is the first version the player sent (1536 x 1024, the same art), on which the thresholds were
# tuned; without it, the full-resolution sheet is scaled down.
_SRC = np.array(Image.open(SRC).convert('RGB'))
HI = _SRC.astype(np.float32)
S = HI.shape[1] / 1536.0
_LO = SRC.replace('.png', '_1536.png')
IM = (np.array(Image.open(_LO).convert('RGB')).astype(np.float32) if os.path.exists(_LO) and S > 1.01 else
      cv2.resize(_SRC, (1536, int(round(_SRC.shape[0] / S))), interpolation=cv2.INTER_AREA).astype(np.float32)
      if S > 1.01 else HI)

# panel inner rects (x0, y0, x1, y1, frames, kind); top border y for the tab band
PANELS = {
    'IDLE':          (11, 82, 909, 237, 6, 'char', 80),
    'BLINK':         (921, 82, 1524, 237, 4, 'char', 80),
    'RECEIVE_COINS': (11, 252, 959, 446, 8, 'char', 249),
    'REWARD_JUMP':   (973, 252, 1525, 446, 4, 'char', 249),
    'CELEBRATE':     (11, 462, 952, 648, 6, 'char', 459),
    'FEEDBACK':      (965, 462, 1525, 648, 4, 'char', 459),
    'REACTIONS':     (11, 663, 969, 818, 8, 'char', 660),
    'MOVE':          (982, 663, 1525, 818, 3, 'char', 660),
    'TELEPORT':      (11, 833, 430, 997, 3, 'tele', 830),
    'ICONS':         (442, 833, 858, 997, 4, 'icon', 830),
    'ELEMENTS':      (870, 833, 1227, 997, 0, 'fx', 830),
}

def panel_valid(name):
    x0, y0, x1, y1, n, kind, top = PANELS[name]
    P = IM[y0:y1, x0:x1]
    h, w = P.shape[:2]
    valid = np.ones((h, w), bool)
    # the title tab: white text and its box in the top band, from the left edge
    band = P[: max(1, top + 30 - y0)]
    white = (band.min(axis=2) > 185)
    cols = np.where(white.any(axis=0))[0]
    if len(cols):
        tr = min(w, cols.max() + 26)
        valid[: top + 30 - y0, :tr] = False
    # thin lines across the panel near the top (the tab bar's underline)
    blue = (P[:, :, 2] > 110) & (P[:, :, 2] - P[:, :, 0] > 50)
    for y in range(min(h, 40)):
        if blue[y].mean() > 0.45:
            valid[max(0, y - 1): y + 2] = False
    return P, valid

def background(P):
    R, G, B = P[..., 0], P[..., 1], P[..., 2]
    navy = (R <= 14) & (B >= 16) & (B - G >= 12) & (B > 1.5 * G) & (B < 115)
    m = navy.astype(np.float32)
    k = (0, 0)
    num = cv2.GaussianBlur(P * m[..., None], k, 14)
    den = cv2.GaussianBlur(m, k, 14)[..., None]
    Bg = num / np.maximum(den, 1e-4)
    # where no navy is near, a wider blur
    num2 = cv2.GaussianBlur(P * m[..., None], k, 40)
    den2 = cv2.GaussianBlur(m, k, 40)[..., None]
    Bg2 = num2 / np.maximum(den2, 1e-4)
    wgt = np.clip(den / 0.25, 0, 1)
    return Bg * wgt + Bg2 * (1 - wgt), navy

def matte(P, valid, kind):
    Bg, navy = background(P)
    R, G, B = P[..., 0], P[..., 1], P[..., 2]
    # dark outline: near black, or darker than the background without being navy (warm dark tones near a burst are
    # its glow over the navy, not ink)
    lum = P @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    lumB = Bg @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    mx = P.max(axis=2)
    strong = ((mx < 24) | ((lum < lumB - 4) & (mx < 52))) & ~navy
    glowdark = (R >= B - 8) & (R > 14) & (R - G < 22)   # a burst's faint gold over the navy: brownish grey
    weak = (mx < 60) & ~navy & ~glowdark & (lum < lumB + 10)
    maroon = (R > G + 22) & (R < 125) & (G < 60) & (lum < 48) & (B >= G - 4)   # dark red ink (gold fringes have B < G)
    # a red aura (the alert) is dark red too, but thick: only thin dark red is ink
    maroon &= ~cv2.morphologyEx(maroon.astype(np.uint8), cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))).astype(bool)
    lights = (B > 170) & (B - R > 70)            # the backpack's blue lights close the outline where they sit on it
    outline = (strong | weak | maroon | lights) & valid
    oc = cv2.morphologyEx(outline.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))).astype(bool)
    oc3 = cv2.morphologyEx(outline.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
    oc7 = cv2.morphologyEx(outline.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(bool)
    filled = ndi.binary_fill_holes(oc) | ndi.binary_fill_holes(oc3) | (ndi.binary_fill_holes(oc7) & ~(oc7 & ~outline))
    # ink is the outline of something: keep the enclosed areas and only the outline next to them (a dark band that
    # encloses nothing, like the edge of the dark backdrop round a burst, is background)
    interior = filled & ~(oc | oc3)
    near = cv2.dilate(interior.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))).astype(bool)
    body = interior | (filled & near)
    # background seen through loops inside a body: big navy pockets stay transparent (not in the icons' badges)
    lab, n = ndi.label(body & navy) if kind != 'icon' else (None, 0)
    if n:
        sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
        for i, s in enumerate(sizes, 1):
            if s > 80:
                body[lab == i] = False
    # drop specks of 'body' and dark blobs with no paint in them (the black backdrop round a burst is not ink)
    lab, n = ndi.label(body)
    if n:
        idx = range(1, n + 1)
        sizes = ndi.sum(np.ones_like(lab), lab, idx)
        paint = ndi.sum((mx >= 90).astype(np.float32), lab, idx)
        for i, (sz, pt) in enumerate(zip(sizes, paint), 1):
            if sz < 12 or (sz < 600 and pt < 0.10 * sz):
                body[lab == i] = False
    body &= valid
    body = drop_dark_pockets(body, P, lights)
    # thin dark lines that enclose nothing (between a burst's rays) are not ink: keep the solid cores and only the
    # thin parts within 2 px of them (outline detail)
    core_ = cv2.morphologyEx(body.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    body = core_ | (body & cv2.dilate(core_.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool))
    lab, n = ndi.label(body)
    if n:
        sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
        for i, sz in enumerate(sizes, 1):
            if sz < 12:
                body[lab == i] = False
    # light added over the background (glows, rays, sparkles, beams): additive key
    D = P - Bg
    a = np.max(D / np.maximum(255.0 - Bg, 1.0), axis=2)
    a = np.clip(a, 0, 1)
    dist = np.linalg.norm(D, axis=2)
    a[dist < 16] = 0
    ag = np.clip((a - 0.07) / 0.93, 0, 1)
    F = np.clip(Bg + D / np.maximum(a, 1e-3)[..., None], 0, 255)
    if kind == 'char':
        # the stage under the feet: a dim steel-blue ellipse (decor), not an effect; only in a band at each pig's feet
        steel = (B - R > 40) & (G - R > 18) & (P.max(axis=2) < 175) & (R < 95) & (B > G)
        band = np.zeros_like(body)
        lab, n = ndi.label(body)
        for sl in ndi.find_objects(lab):
            if sl is None:
                continue
            ys, xs = sl
            if (ys.stop - ys.start) * (xs.stop - xs.start) < 1500:
                continue
            band[max(0, ys.stop - 16): ys.stop + 16, max(0, xs.start - 30): xs.stop + 30] = True
        ag[steel & band] = 0
    ag[~valid] = 0
    alpha = np.where(body, 1.0, ag)
    rgb = np.where(body[..., None], P, F)
    # soft outer edge on the bodies (no navy halo): feather outward with the edge colour
    soft = cv2.GaussianBlur(body.astype(np.float32), (0, 0), 0.7)
    ring = (~body) & (soft > alpha)
    if ring.any():
        dil = cv2.dilate(np.where(body[..., None], P, 0).astype(np.float32), np.ones((3, 3), np.uint8))
        rgb[ring] = dil[ring]
        alpha[ring] = soft[ring]
    matte.ag = np.where(body, 1.0, ag)
    matte.ink = (strong | weak | maroon) & valid
    matte.lights = lights & valid
    matte.navy = navy
    return np.dstack([rgb, alpha * 255]).astype(np.float32), body

def checker(rgba, s=8):
    h, w = rgba.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    c = np.where(((yy // s + xx // s) % 2) == 0, 200, 150)[..., None].astype(np.float32)
    bgc = np.dstack([c, c * 0.6, c])  # pinkish checker so dark halos show
    a = rgba[..., 3:4] / 255.0
    return (rgba[..., :3] * a + bgc * (1 - a)).astype(np.uint8)


def pig_solid(pink_seed, region, ink, lights, navy, body):
    """A pig's opaque silhouette from its pink skin: the skin with the ink round it and its holes filled (eyes,
    mouth), then the backpack and anything else its outline closes against that solid body (within 45 px)."""
    ell = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r))
    near_pink = cv2.dilate(pink_seed.astype(np.uint8), ell(9)).astype(bool)
    s0 = pink_seed | (ink & near_pink & region)
    s0 = cv2.morphologyEx(s0.astype(np.uint8), cv2.MORPH_CLOSE, ell(5)).astype(bool)
    s0 = ndi.binary_fill_holes(s0)
    near = cv2.dilate(s0.astype(np.uint8), ell(91)).astype(bool) & region
    ag = matte.ag
    # bright light drawn over the pig (a ring round its legs) closes its outline too
    cand = ((ink | lights | body | (ag > 0.6)) & near) | s0
    lab, n = ndi.label(cand)
    keep = np.unique(lab[s0 & (lab > 0)])
    cand = np.isin(lab, keep) & (lab > 0)           # only what is joined to the pig (a falling coin is not)
    s1 = s0 | cand
    s1 = cv2.morphologyEx(s1.astype(np.uint8), cv2.MORPH_CLOSE, ell(5)).astype(bool)
    s1 = ndi.binary_fill_holes(s1) & (near | s0)
    s1 = drop_dark_pockets(s1, drop_dark_pockets.P, lights, keep=s0)
    # what that closes but is only faint glow over the background (inside a ring, between rays) stays light
    faint = s1 & ~s0 & (ag < 0.5) & ~ink & ~lights
    lab, n = ndi.label(faint)
    if n:
        sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
        for i, sz in enumerate(sizes, 1):
            if sz > 40:
                s1[lab == i] = False
    # what the outline closes but is plain background (between legs, in a loop) stays out
    lab, n = ndi.label(s1 & ~s0 & navy)
    if n:
        sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
        for i, sz in enumerate(sizes, 1):
            if sz > 40:
                s1[lab == i] = False
    return s1


def drop_dark_pockets(mask, P, lights, keep=None):
    """Thick dark areas inside a mask that touch no backpack light are backdrop (round a falling coin, a burst),
    not ink: take them out. Thin dark ink (outlines) is left alone."""
    dark = mask & (P.max(axis=2) < 45)
    thick = cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))).astype(bool)
    near_l = cv2.dilate(lights.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    lab, n = ndi.label(thick)
    out = mask.copy()
    for i in range(1, n + 1):
        m = lab == i
        if m.sum() > 60 and not (m & near_l).any() and (keep is None or not (m & keep).any()):
            out[cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & dark] = False
    return out


def hi_rect(name):
    x0, y0, x1, y1 = PANELS[name][:4]
    return [int(round(v * S)) for v in (x0, y0, x1, y1)]

def up(a, size, nearest=False):
    return cv2.resize(a, size, interpolation=cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR)

def render_hi(name, rgba1):
    """The panel at full resolution: opaque where the layout-scale result is opaque (edges smoothed), and the glows
    keyed again from the full-resolution pixels over the background model, only where the layout-scale result kept
    something."""
    x0, y0, x1, y1 = PANELS[name][:4]
    X0, Y0, X1, Y1 = hi_rect(name)
    P4 = HI[Y0:Y1, X0:X1]
    h4, w4 = P4.shape[:2]
    if S <= 1.01:
        return rgba1.copy()
    Bg1, _ = background(IM[y0:y1, x0:x1])
    Bg4 = up(Bg1, (w4, h4))
    D = P4 - Bg4
    a = np.clip(np.max(D / np.maximum(255.0 - Bg4, 1.0), axis=2), 0, 1)
    a[np.linalg.norm(D, axis=2) < 16] = 0
    g4 = np.clip((a - 0.07) / 0.93, 0, 1)
    F4 = np.clip(Bg4 + D / np.maximum(a, 1e-3)[..., None], 0, 255)
    A1 = rgba1[..., 3] / 255.0
    op4 = np.clip((up((A1 >= 0.999).astype(np.float32), (w4, h4)) - 0.35) / 0.3, 0, 1)
    g4 *= (up((A1 > 0.004).astype(np.float32), (w4, h4)) > 0.5).astype(np.float32)
    alpha = op4 + (1 - op4) * g4
    prem = op4[..., None] * P4 + ((1 - op4) * g4)[..., None] * F4
    rgb = prem / np.maximum(alpha, 1e-4)[..., None]
    return np.dstack([rgb, alpha * 255]).astype(np.float32)

def owner_hi(name, full1, rgba4):
    """The frame each full-resolution pixel belongs to (the layout-scale map, filled out to the new soft edges)."""
    h4, w4 = rgba4.shape[:2]
    f = up((full1 + 1).astype(np.float32), (w4, h4), nearest=True).astype(np.int32) - 1
    vis = rgba4[..., 3] > 0
    if (f >= 0).any():
        _, (iy, ix) = ndi.distance_transform_edt(f < 0, return_indices=True)
        f = np.where(vis, f[iy, ix], -1)
    return f
