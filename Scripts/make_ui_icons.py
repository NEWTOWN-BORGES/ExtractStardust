"""Draws the hangar's icons (the family of each module, the consumables, the caches, a ship copy and the star) and the
interface art of the mock-ups (Docs/MENU_HANGAR.md): the soft glows round the cards, the stripes of a card's back, the
fades, the STARDUST gem, the d-pad, the flame bars of the engines and the menu's logo.

Icons: white on transparent, 128 x 128, so the UI can tint them (the rarity colour for a module, the consumable's
colour...). Drawn with PIL at four times the size and shrunk, so the edges are smooth. Our own drawings: no logo from any
reference. The art (ui_*, flame_*) is drawn in its own colours or in white to be tinted, as noted on each.

    python3 Scripts/make_ui_icons.py [out_dir]          # default SourceArt/UI/Icons

Scripts/import_ui_icons.py brings them into the Unreal project as /Game/UI/Icons/T_Icon_<name>. The names are the ones
UEXHangarModel writes in FEXHangarRow::Icon: fam_0 .. fam_7 (EEXFamily order), con_<consumable id>, cache_0 .. cache_2,
ship_copy and star.
"""
import math
import os
import sys

from PIL import Image, ImageDraw

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SourceArt", "UI", "Icons")
S = 512          # drawing size
FINAL = 128
W = 30           # stroke width
WHITE = (255, 255, 255, 255)


IMG = None


def canvas():
    global IMG
    IMG = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    return IMG, ImageDraw.Draw(IMG)


def line(d, pts, w=W):
    d.line(pts, fill=WHITE, width=w, joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=WHITE)


def ring(d, cx, cy, r, w=W):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=WHITE, width=w)


def disc(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)


def poly(d, pts, outline=False, w=W):
    if outline:
        line(d, list(pts) + [pts[0]], w)
    else:
        d.polygon(pts, fill=WHITE)


def polar(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def star(d, cx, cy, ro, ri, points=5, rot=-90):
    pts = []
    for k in range(points * 2):
        pts.append(polar(cx, cy, ro if k % 2 == 0 else ri, rot + k * 180.0 / points))
    d.polygon(pts, fill=WHITE)


def engine(d):
    ring(d, 256, 256, 190)
    disc(d, 256, 256, 38)
    for k in range(6):  # six curved blades, drawn as thin wedges
        a = k * 60
        poly(d, [polar(256, 256, 40, a - 8), polar(256, 256, 170, a + 8), polar(256, 256, 170, a + 36), polar(256, 256, 60, a + 26)])


def propulsion(d):
    poly(d, [(70, 170), (250, 170), (250, 342), (70, 342)], outline=True)   # the nozzle
    poly(d, [(250, 170), (330, 120), (330, 392), (250, 342)], outline=True)
    poly(d, [(360, 200), (470, 256), (360, 312), (396, 256)])               # the jet


def wings(d):
    for sx in (1, -1):  # two swept blades and the fuselage between them
        poly(d, [(256 + sx * 26, 70), (256 + sx * 200, 360), (256 + sx * 200, 440), (256 + sx * 26, 300)])
    poly(d, [(236, 60), (276, 60), (276, 440), (236, 440)])


def tail(d):
    poly(d, [(110, 420), (180, 90), (250, 90), (330, 300), (440, 330), (440, 420)], outline=True)
    line(d, [(110, 420), (440, 420)])


def armor(d):
    poly(d, [(256, 52), (440, 112), (440, 262), (256, 462), (72, 262), (72, 112)], outline=True)
    line(d, [(256, 52), (256, 462)], 22)
    line(d, [(72, 190), (440, 190)], 22)


def reactor(d):
    disc(d, 256, 256, 52)
    for a in (0, 60, 120):
        e = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ed = ImageDraw.Draw(e)
        ed.ellipse([256 - 205, 256 - 78, 256 + 205, 256 + 78], outline=WHITE, width=22)
        e = e.rotate(a, resample=Image.BICUBIC, center=(256, 256))
        IMG.alpha_composite(e)


def cooling(d):
    for a in range(0, 360, 60):  # six arms, each with two little branches
        tip = polar(256, 256, 205, a)
        base = polar(256, 256, 120, a)
        line(d, [(256, 256), tip], 26)
        for off in (-42, 42):
            end = (base[0] + 70 * math.cos(math.radians(a + off)), base[1] + 70 * math.sin(math.radians(a + off)))
            line(d, [base, end], 20)


def utility(d):
    line(d, [(256, 440), (256, 230)], 30)           # the mast
    line(d, [(160, 440), (352, 440)], 30)
    d.arc([96, 70, 416, 390], 205, 335, fill=WHITE, width=30)   # the dish
    disc(d, 256, 150, 26)
    for r in (110, 170):
        d.arc([256 - r, 150 - r, 256 + r, 150 + r], 300, 345, fill=WHITE, width=18)


def battery(d, glyph):
    poly(d, [(150, 110), (362, 110), (362, 460), (150, 460)], outline=True, w=28)
    poly(d, [(210, 52), (302, 52), (302, 110), (210, 110)])
    glyph(d)


def snow(d):
    for a in (90, 150, 210):
        line(d, [polar(256, 290, 110, a), polar(256, 290, -110, a)], 18)


def plus(d):
    line(d, [(256, 220), (256, 370)], 34)
    line(d, [(181, 295), (331, 295)], 34)


def drop_shape(d):
    d.polygon([(256, 40), (150, 270), (362, 270)], fill=WHITE)
    disc(d, 256, 330, 130)


def drop(d):
    drop_shape(d)
    d.ellipse([196, 300, 236, 370], fill=(0, 0, 0, 0))  # a highlight


def bolt(d):
    poly(d, [(300, 40), (130, 290), (240, 290), (200, 472), (390, 214), (276, 214)])


def stabilizer(d):
    ring(d, 256, 256, 170)
    ring(d, 256, 256, 70, 24)
    for a in (0, 90, 180, 270):
        line(d, [polar(256, 256, 170, a), polar(256, 256, 236, a)], 26)


def nanogel(d):
    drop_shape(d)
    d.rectangle([236, 270, 276, 390], fill=(0, 0, 0, 0))
    d.rectangle([196, 310, 316, 350], fill=(0, 0, 0, 0))


def crate(d, bands):
    poly(d, [(256, 60), (440, 150), (256, 240), (72, 150)], outline=True, w=26)
    poly(d, [(72, 150), (256, 240), (256, 452), (72, 362)], outline=True, w=26)
    poly(d, [(440, 150), (256, 240), (256, 452), (440, 362)], outline=True, w=26)
    if bands >= 2:   # a strap across the lid
        line(d, [(164, 105), (348, 195)], 20)
    if bands >= 3:   # and a star on it
        star(d, 256, 150, 46, 20)


def ship_copy(d):
    poly(d, [(256, 60), (440, 400), (256, 330), (72, 400)], outline=True, w=26)
    star(d, 256, 210, 70, 30, 4, -90)


def star_icon(d):
    star(d, 256, 262, 220, 92)


ICONS = {
    "fam_0": engine, "fam_1": propulsion, "fam_2": wings, "fam_3": tail, "fam_4": armor, "fam_5": reactor, "fam_6": cooling,
    "fam_7": utility,
    "con_coolant": lambda d: battery(d, snow), "con_foam": lambda d: battery(d, plus), "con_fuel": drop, "con_stab": stabilizer,
    "con_surge": bolt, "con_nanogel": nanogel,
    "cache_0": lambda d: crate(d, 1), "cache_1": lambda d: crate(d, 2), "cache_2": lambda d: crate(d, 3),
    "ship_copy": ship_copy, "star": star_icon,
}

# ---- Interface art --------------------------------------------------------------------------------------------------
from PIL import ImageFilter, ImageFont

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SourceArt", "Fonts")


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def alpha_image(w, h, fn):
    """White image whose alpha is fn(x, y) in 0..1."""
    im = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    px = im.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (255, 255, 255, int(round(255 * max(0.0, min(1.0, fn(x, y))))))
    return im


def art_glow():
    """Outer glow (tinted, drawn 9-sliced behind a card or a button, larger than it by the glow's size)."""
    im = Image.new("L", (128, 128), 0)
    ImageDraw.Draw(im).rectangle([34, 34, 93, 93], fill=255)
    im = im.filter(ImageFilter.GaussianBlur(11))
    out = Image.new("RGBA", (128, 128), (255, 255, 255, 0))
    out.putalpha(im)
    return out


def art_inset():
    """Inner glow (tinted, 9-sliced over a card): bright at the edges, clear in the middle."""
    im = Image.new("L", (128, 128), 255)
    ImageDraw.Draw(im).rectangle([22, 22, 105, 105], fill=0)
    im = im.filter(ImageFilter.GaussianBlur(9))
    out = Image.new("RGBA", (128, 128), (255, 255, 255, 0))
    out.putalpha(im)
    return out


def art_stripes():
    """Diagonal stripes, tiled on a card's back (tinted rust, faint): 10 px stripe, 10 px gap at 45 degrees."""
    big = alpha_image(128, 128, lambda x, y: 1.0 if ((x + y) % 80) < 40 else 0.0)
    return big.resize((32, 32), Image.LANCZOS)


def art_vignette():
    """Clear in the middle, dark at the edges (tinted near-black behind an open cache)."""
    w, h = 320, 180
    return alpha_image(w, h, lambda x, y: smooth((math.hypot((x - w / 2) / (w / 2), (y - h / 2) / (h / 2)) - 0.25) / 0.85))


def art_radial():
    """A soft round glow (tinted): the halo behind an icon or a selected tile."""
    return alpha_image(128, 128, lambda x, y: (1.0 - smooth(math.hypot(x - 63.5, y - 63.5) / 63.5)) ** 1.6)


def art_gem():
    """The STARDUST gem in its own colours: a diamond, gold at the top-left, rust at the bottom-right, with a glow."""
    s, c = 256, 128
    glow = Image.new("L", (s, s), 0)
    ImageDraw.Draw(glow).polygon([(c, 40), (s - 40, c), (c, s - 40), (40, c)], fill=200)
    glow = glow.filter(ImageFilter.GaussianBlur(26))
    im = Image.new("RGBA", (s, s), (255, 160, 80, 0))
    im.putalpha(glow)
    gem = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gp = gem.load()
    a0, a1 = (255, 210, 122), (235, 87, 26)
    for y in range(s):
        for x in range(s):
            if abs(x - c) + abs(y - c) <= 64:
                t = max(0.0, min(1.0, ((x - (c - 64)) + (y - (c - 64))) / 256.0))
                gp[x, y] = tuple(int(a0[k] + (a1[k] - a0[k]) * t) for k in range(3)) + (255,)
    im.alpha_composite(gem)
    return im.resize((64, 64), Image.LANCZOS)


def art_dpad():
    """The d-pad between the four quick slots, in its own colours: a dark cross with rust arrows."""
    s = 480
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark, edge, rust = (26, 18, 13, 235), (242, 230, 204, 60), (235, 87, 26, 255)
    for rect in ((170, 30, 310, 450), (30, 170, 450, 310)):
        d.rectangle(rect, fill=dark, outline=edge, width=6)
    d.rectangle((176, 176, 304, 304), fill=dark)
    for tri in (((240, 60), (200, 120), (280, 120)), ((240, 420), (200, 360), (280, 360)),
                ((60, 240), (120, 200), (120, 280)), ((420, 240), (360, 200), (360, 280))):
        d.polygon(tri, fill=rust)
    return im.resize((120, 120), Image.LANCZOS)


FLAME_COLOURS = [  # EXMeta::Flames: outer, core
    ((1.0, 0.30, 0.06), (1.0, 0.72, 0.38)), ((0.20, 0.45, 1.0), (0.85, 0.95, 1.0)), ((0.10, 0.80, 1.0), (0.70, 1.0, 1.0)),
    ((1.0, 0.55, 0.12), (1.0, 0.95, 0.70)), ((0.55, 0.25, 1.0), (0.92, 0.85, 1.0)), ((1.0, 0.25, 0.05), (1.0, 0.60, 0.25)),
    ((0.35, 0.60, 1.0), (1.0, 1.0, 1.0)), ((1.0, 0.08, 0.06), (1.0, 0.85, 0.80)),
]


def art_flame(i):
    """The little flame bar next to an engine's name (mock-up equip_engine.png), in the flame's colours."""
    outer, core = FLAME_COLOURS[i]
    w, h = 184, 36
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for y in range(h):
        for x in range(w):
            # a capsule: hot core on the left fading into the outer colour, soft at the tip
            dy = abs(y - (h - 1) / 2) / ((h - 1) / 2)
            r = (h - 1) / 2
            inside = (x >= r and x <= w - 1 - r and dy <= 1) or math.hypot(min(x - r, 0), y - r) <= r or math.hypot(max(x - (w - 1 - r), 0), y - r) <= r
            if not inside:
                continue
            t = x / (w - 1)
            col = [core[k] + (outer[k] - core[k]) * smooth(t * 1.3) for k in range(3)]
            a = 1.0 - smooth((t - 0.75) / 0.25) * 0.85
            px[x, y] = tuple(int(255 * min(1.0, c)) for c in col) + (int(255 * a),)
    return im.resize((92, 18), Image.LANCZOS)


def art_logo():
    """The menu's logo (mock-up menu2.png) in its own colours: EXTRACT spaced out, STARDUST in Orbitron with a gradient
    from light to deep orange and a soft shadow, RACE . SURVIVE . EXTRACT under it in rust. 2x the size it is shown at."""
    orb = os.path.join(FONTS, "Orbitron-Black.ttf")
    W, H = 1300, 380
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    def spaced(d, xy, text, font, fill, gap):
        x, y = xy
        for ch in text:
            d.text((x, y), ch, font=font, fill=fill)
            x += d.textlength(ch, font=font) + gap
        return x

    d = ImageDraw.Draw(im)
    spaced(d, (6, 6), "EXTRACT", ImageFont.truetype(orb, 46), (242, 230, 204, 255), 34)
    big = ImageFont.truetype(orb, 170)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).text((0, 70), "STARDUST", font=big, fill=255)
    bbox = mask.getbbox()
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gp = grad.load()
    top, bottom = (255, 176, 103), (226, 85, 28)
    for y in range(H):
        t = max(0.0, min(1.0, (y - bbox[1]) / max(1, bbox[3] - bbox[1])))
        col = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
        for x in range(W):
            gp[x, y] = col + (255,)
    shadow = Image.new("RGBA", (W, H), (120, 30, 6, 0))
    shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.8)))
    im.alpha_composite(shadow, (0, 6))
    letters = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    letters.paste(grad, (0, 0), mask)
    im.alpha_composite(letters)
    tag = ImageFont.truetype(orb, 30)
    x = 6
    for k, word in enumerate(("RACE", "SURVIVE", "EXTRACT")):   # Orbitron has no middle dot: the dots are drawn
        if k:
            d.ellipse([x + 22, 312, x + 31, 321], fill=(235, 87, 26, 255))
            x += 62
        x = spaced(d, (x, 300), word, tag, (235, 87, 26, 255), 15)
    return im.crop((0, 0, W, H))


def art_fade_h():
    """White, opaque on the left and clear on the right (tinted: a highlight that fades out)."""
    return alpha_image(256, 4, lambda x, y: 1.0 - x / 255.0)


def art_fade_v():
    """White, opaque at the top and clear at the bottom (tinted: the dark top band)."""
    return alpha_image(4, 256, lambda x, y: 1.0 - y / 255.0)


def art_button():
    """The orange buttons of the mock-ups in their own colours: #eb571a on the left to #ff7a3a on the right."""
    a0, a1 = (235, 87, 26), (255, 122, 58)
    im = Image.new("RGBA", (256, 4))
    px = im.load()
    for x in range(256):
        for y in range(4):
            px[x, y] = tuple(int(a0[k] + (a1[k] - a0[k]) * x / 255.0) for k in range(3)) + (255,)
    return im


ART = {
    "ui_fade_h": art_fade_h, "ui_fade_v": art_fade_v, "ui_button": art_button,
    "ui_glow": art_glow, "ui_inset": art_inset, "ui_stripes": art_stripes, "ui_vignette": art_vignette, "ui_radial": art_radial,
    "ui_gem": art_gem, "ui_dpad": art_dpad, "ui_logo": art_logo,
}
for _i in range(len(FLAME_COLOURS)):
    ART["flame_%d" % _i] = (lambda i: (lambda: art_flame(i)))(_i)

os.makedirs(OUT, exist_ok=True)
for name, fn in ART.items():
    fn().save(os.path.join(OUT, name + ".png"))
for name, fn in ICONS.items():
    im, d = canvas()
    fn(d)
    im.resize((FINAL, FINAL), Image.LANCZOS).save(os.path.join(OUT, name + ".png"))
print("icons:", len(ICONS), "art:", len(ART), "->", os.path.abspath(OUT))
