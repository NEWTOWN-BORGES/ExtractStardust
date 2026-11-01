"""Mock-ups of the UMG screens (menu, hangar, vault, an opened cache: Scripts/ui_mockups/screens.py) with the same art (SourceArt/UI/Icons) and the EXUi rules: 9-sliced shapes tinted, Slate
point sizes (x 4/3 px), letter spacing in 1/1000 em, the lean of Orbitron titles (-11) and labels (-8)."""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
R = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/'
I = R + 'SourceArt/UI/Icons/'
T = R + 'SourceArt/UI/Thumbs/'
F = R + 'Content/UI/Fonts/'
W, H = 1920, 1080
PT = 4.0 / 3.0
ACCENT = (70, 220, 255); ACCENT_HOT = (150, 225, 255); FORE = (238, 245, 255); QUIET = (140, 165, 196); DIM = (74, 92, 120)
OK = (110, 230, 140); GOLD = (255, 200, 60); DANGER = (255, 90, 40); INK = (3, 8, 20); PLATE = (8, 18, 38); PICK = (14, 44, 78)
RARITY = [(0xE9, 0xE4, 0xDA), (0x5F, 0xD1, 0x7A), (0x4A, 0xA3, 0xFF), (0xB5, 0x6C, 0xFF), (0xFF, 0xC2, 0x3D)]
RARITY_NAME = ['COMUM', 'INCOMUM', 'RARO', 'ÉPICO', 'LENDÁRIO']
_art, _fonts = {}, {}


def art(name, folder=I, ext='.png'):
    k = folder + name + ext
    if k not in _art:
        _art[k] = Image.open(k).convert('RGBA')
    return _art[k]


def tint(img, col, alpha=1.0):
    a = np.array(img).astype(np.float32)
    a[..., :3] *= np.array(col, np.float32) / 255.0
    a[..., 3] *= alpha
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def nine(name, w, h, margin, scale):
    a = art(name); tw, th = a.size
    l, t, r, b = margin
    sx = [0, round(l * tw), tw - round(r * tw), tw]; sy = [0, round(t * th), th - round(b * th), th]
    dl, dt, dr, db = l * tw * scale, t * th * scale, r * tw * scale, b * th * scale
    if dl + dr > w: k = w / (dl + dr); dl *= k; dr *= k
    if dt + db > h: k = h / (dt + db); dt *= k; db *= k
    xs = [0, round(dl), round(w - dr), round(w)]; ys = [0, round(dt), round(h - db), round(h)]
    out = Image.new('RGBA', (max(1, round(w)), max(1, round(h))))
    for j in range(3):
        for i in range(3):
            dw, dh = xs[i + 1] - xs[i], ys[j + 1] - ys[j]
            if dw <= 0 or dh <= 0 or sx[i + 1] <= sx[i] or sy[j + 1] <= sy[j]:
                continue
            out.paste(a.crop((sx[i], sy[j], sx[i + 1], sy[j + 1])).resize((dw, dh), Image.LANCZOS), (xs[i], ys[j]))
    return out


SHAPES = {'plate': ('ui_plate', 20.0, (0.25,) * 4), 'card': ('ui_card', 20.0, (0.25,) * 4), 'tab': ('ui_tab', 48.0, (0.12, 0.5, 0.12, 0.5))}


class Screen:
    def __init__(self, bg=None, dim=0.0):
        self.im = Image.open(bg).convert('RGBA').resize((W, H)) if bg else Image.new('RGBA', (W, H), (10, 14, 22, 255))
        if dim:
            self.rect(0, 0, W, H, INK, dim)

    def comp(self, layer, x, y):
        self.im.alpha_composite(layer, (int(round(x)), int(round(y))))

    def rect(self, x, y, w, h, col, alpha=1.0):
        if w > 0 and h > 0:
            self.comp(Image.new('RGBA', (max(1, round(w)), max(1, round(h))), tuple(col) + (int(255 * alpha),)), x, y)

    def shape(self, kind, part, x, y, w, h, corner, col, alpha):
        name, cut, m = SHAPES[kind]
        self.comp(tint(nine(name + part, w, h, m, corner / cut), col, alpha), x, y)

    def plate(self, x, y, w, h, fill=(PLATE, 0.82), edge=(ACCENT, 0.5), corner=10, kind='plate', wash=None, top=None):
        self.shape(kind, '', x, y, w, h, corner, *fill)
        if wash:
            self.shape(kind, '_wash', x, y, w, h, corner, *wash)
        if edge:
            self.shape(kind, '_edge', x, y, w, h, corner, *edge)
        if top:
            inset = corner + 4 if kind == 'plate' else 0
            self.rect(x + inset, y, w - inset - 8, top[2], top[0], top[1])

    def glow(self, x, y, w, h, col, alpha, spread=22):
        self.comp(tint(nine('ui_glow', w + 2 * spread, h + 2 * spread, (0.45,) * 4, 1.0), col, alpha), x - spread, y - spread)

    def icon(self, name, x, y, w, h, col=None, alpha=1.0, folder=I, ext='.png'):
        a = art(name, folder, ext).resize((max(1, round(w)), max(1, round(h))), Image.LANCZOS)
        if col is not None or alpha < 1:
            a = tint(a, col or (255, 255, 255), alpha)
        self.comp(a, x, y)

    def photo(self, key, x, y, w, h):
        self.comp(art(key, T, '.jpg').resize((round(w), round(h)), Image.LANCZOS), x, y)

    def text(self, x, y, s, size, col, key='i700', spacing=0, outline=0, lean=0.0, alpha=1.0, align='l', measure=False):
        """Slate size in points; returns the width in px. align: l, c, r (x is the left, centre or right)."""
        f = font(key, size)
        px = size * PT
        gap = spacing / 1000.0 * px
        widths = [f.getlength(c) for c in s]
        tw = sum(widths) + gap * max(0, len(s) - 1)
        if measure:
            return tw
        asc, desc = f.getmetrics()
        pad = int(outline + 4 + abs(math.tan(math.radians(lean))) * (asc + desc))
        layer = Image.new('RGBA', (int(tw) + 2 * pad + 4, asc + desc + 2 * pad))
        d = ImageDraw.Draw(layer)
        cx = pad
        fill = tuple(col) + (int(255 * alpha),)
        for c, cw in zip(s, widths):
            d.text((cx, pad), c, font=f, fill=fill, stroke_width=int(outline), stroke_fill=INK + (int(220 * alpha),))
            cx += cw + gap
        if lean:
            k = math.tan(math.radians(-lean))
            cy = layer.size[1] / 2
            layer = layer.transform(layer.size, Image.AFFINE, (1, k, -k * cy, 0, 1, 0), Image.BICUBIC)
        ox = x - pad - (tw / 2 if align == 'c' else tw if align == 'r' else 0)
        self.comp(layer, ox, y - pad)
        return tw

    def title(self, x, y, s, size, col, spacing=0, align='l', alpha=1.0, shadow=False):
        if shadow:
            self.text(x, y + 3, s, size, INK, 'orb', spacing, max(1, size // 18), -11, 0.45, align)
        return self.text(x, y, s, size, col, 'orb', spacing, max(1, size // 18), -11, alpha, align)

    def label(self, x, y, s, size, col, spacing=160, align='l', alpha=1.0):
        return self.text(x, y, s, size, col, 'i800', spacing, 1, -8, alpha, align)

    def coin(self, x, y, size):
        self.icon('hud_coin', x, y, size * 1.3, size * 1.3)
        return size * 1.3

    def keycap(self, x, y, key, dark=False):
        tw = self.text(0, 0, key, 11, FORE, 'i700', measure=True)
        w = max(31, tw + 16)
        self.plate(x, y, w, 29, fill=(INK, 0.0) if dark else (PLATE, 0.7), edge=(INK, 0.85) if dark else (ACCENT_HOT, 0.6), corner=5)
        self.text(x + w / 2, y + 5, key, 11, INK if dark else FORE, 'i700', align='c')
        return w

    def hint(self, x, y, keys, label):
        for k in keys:
            x += self.keycap(x, y, k) + 7
        return x + 2 + self.text(x + 2, y + 5, label, 12, QUIET, 'i400')

    def keybar(self, hints, right=None):
        self.rect(0, H - 56, W, 1, ACCENT, 0.5)
        self.rect(0, H - 55, W, 55, INK, 0.9)
        x = 58
        for keys, label in hints:
            x = self.hint(x, H - 42, keys, label) + 34
        if right:
            tw = self.text(0, 0, right[1], 12, QUIET, 'i400', measure=True)
            kw = sum(max(31, self.text(0, 0, k, 11, FORE, measure=True) + 16) + 7 for k in right[0])
            self.hint(W - 58 - tw - kw - 2, H - 42, right[0], right[1])

    def button(self, x, y, w, h, label, key='ENTER'):
        self.glow(x, y, w, h, ACCENT, 0.45)
        self.comp(nine('ui_btn', w, h, (0.125, 0.3, 0.125, 0.3), h / 72.0), x, y)
        tw = self.title(0, 0, label, 16, INK, 200) if False else self.text(0, 0, label, 16, INK, 'orb', 200, measure=True)
        kw = self.text(0, 0, key, 10, INK, 'i800', 100, measure=True) + 14
        x0 = x + (w - tw - 14 - kw) / 2
        self.title(x0, y + h / 2 - 14, label, 16, INK, 200)
        kx = x0 + tw + 14
        self.plate(kx, y + h / 2 - 11, kw, 22, fill=(INK, 0.12), edge=(INK, 0.8), corner=4)
        self.text(kx + 7, y + h / 2 - 8, key, 10, INK, 'i800', 100)

    def chip(self, x, y, s, size, col, plate=(PLATE, 0.6), edge=(ACCENT_HOT, 0.2)):
        tw = self.text(0, 0, s, size, col, 'i800', measure=True)
        w, h = tw + 16, size * PT + 7
        self.plate(x, y, w, h, fill=plate, edge=edge, corner=5)
        self.text(x + 8, y + 2, s, size, col, 'i800')
        return w, h

    def wallet(self, right_x, y, value):
        vw = self.text(0, 0, value, 20, GOLD, 'orb', 40, measure=True)
        lw = self.text(0, 0, 'STARDUST', 10, QUIET, 'i800', 200, measure=True)
        w = 18 + 18 * 1.3 + 10 + vw + 12 + lw + 22
        x = right_x - w
        self.plate(x, y, w, 42, fill=(PLATE, 0.8), edge=(GOLD, 0.85), corner=10)
        self.coin(x + 18, y + 9, 18)
        self.title(x + 18 + 23.4 + 10, y + 7, value, 20, GOLD, 40)
        self.label(x + 18 + 23.4 + 10 + vw + 12, y + 13, 'STARDUST', 10, QUIET, 200)

    def card(self, x, y, s, rarity, title, maker, chips=(), value=None, thumb=None, icon=None, tag=None, new=False, picked=False,
             back=False, glow=0.0, fs=None, label=None):
        """MakeCard at scale s of a full card (248 x 331, art 158); fs: the scale of its text (the code builds the vault's
        cards smaller with full-size text, and the mini cards scale the vault's)."""
        w, h, ah = 248 * s, 331 * s, 158 * s
        g = s
        s = fs if fs is not None else s
        col = RARITY[rarity] if rarity is not None else ACCENT
        if glow:
            self.glow(x, y, w, h, col, glow, 22)
        if picked:
            self.shape('card', '_edge', x - 3, y - 3, w + 6, h + 6, 14, ACCENT, 1.0)
        corner = 14 * (g / 0.74) if g < 1 else 14
        if back:
            self.shape('card', '', x, y, w, h, corner, (10, 24, 50), 0.98)
            self.shape('card', '_inset', x, y, w, h, corner, ACCENT, 0.22)
            self.icon('ui_radial', x + w / 2 - 60 * s, y + h / 2 - 70 * s, 120 * s, 120 * s, ACCENT, 0.45)
            d = 84 * s
            dia = Image.new('RGBA', (int(d * 1.5), int(d * 1.5)))
            dd = ImageDraw.Draw(dia); c = d * 0.75; r = d * 0.7
            dd.polygon([(c, c - r), (c + r, c), (c, c + r), (c - r, c)], fill=ACCENT + (255,))
            dd.polygon([(c, c - r + 3), (c + r - 3, c), (c, c + r - 3), (c - r + 3, c)], fill=(10, 26, 54, 255))
            self.comp(dia, x + w / 2 - c, y + h / 2 - 10 * s - c)
            self.text(x + w / 2, y + h / 2 - 30 * s, '?', 27 * s, ACCENT_HOT, 'i900', align='c')
            self.text(x + w / 2, y + h / 2 + 52 * s, 'ESPAÇO', 10 * s, QUIET, 'i700', 200, align='c')
            self.shape('card', '_edge', x, y, w, h, corner, ACCENT, 0.7)
            return
        self.shape('card', '', x, y, w, h, corner, PLATE, 0.97)
        self.rect(x, y, w, ah, (6, 12, 26))
        if thumb:
            self.photo(thumb, x, y, w, ah)
        elif icon:
            self.icon('ui_radial', x + w / 2 - ah / 2, y, ah, ah, col, 0.35)
            self.icon(icon, x + w / 2 - 38 * s, y + ah / 2 - 38 * s, 77 * s, 77 * s, col)
        if tag:
            tw = self.text(0, 0, tag, 9 * s, FORE, 'i800', 160, measure=True)
            self.rect(x + 8 * s, y + ah - 8 * s - 17 * s, tw + 14 * s, 17 * s, INK, 0.78)
            self.text(x + 15 * s, y + ah - 8 * s - 15.5 * s, tag, 9 * s, FORE, 'i800', 160)
        self.rect(x, y + ah, w, max(1, 2 * s), col)
        yy = y + ah + 2 * s + 11 * s
        self.text(x + 13 * s, yy, label or (RARITY_NAME[rarity] if rarity is not None else 'CONSUMÍVEL'), 9 * s, col, 'i900', 200)
        yy += 9 * s * PT * 1.25 + 3 * s
        self.text(x + 13 * s, yy, title, 13 * s, FORE, 'i700')
        yy += 13 * s * PT * 1.25 + 3 * s
        self.text(x + 13 * s, yy, maker, 10 * s, QUIET, 'i400')
        yy += 10 * s * PT * 1.25 + 7 * s
        cx = x + 13 * s
        for t, sign in chips:
            cw = self.text(0, 0, t, 9 * s, FORE, 'i800', measure=True) + 16 * s
            if cx + cw > x + w - 13 * s:
                cx = x + 13 * s; yy += 9 * s * PT + 13 * s
            self.plate(cx, yy, cw, 9 * s * PT + 7 * s, fill=(PLATE, 0.6), edge=(ACCENT_HOT, 0.2), corner=5 * s)
            self.text(cx + 8 * s, yy + 2 * s, t, 9 * s, OK if sign > 0 else (255, 96, 80) if sign < 0 else FORE, 'i800')
            cx += cw + 6 * s
        if value is not None:
            vt = '{:,}'.format(value).replace(',', ' ')
            vw = self.text(0, 0, vt, 10 * s, GOLD, 'i600', measure=True)
            right = x + w - 16 * s - 10 * s * 1.3
            self.text(right - 4 * s - vw, y + h - 11 * s - 16 * s, vt, 10 * s, GOLD, 'i600', alpha=0.9)
            self.coin(right, y + h - 11 * s - 15 * s, 10 * s)
        self.shape('card', '_inset', x, y, w, h, corner, col, 0.18 if not new else 0.25)
        self.shape('card', '_edge', x, y, w, h, corner, col, 1.0)
        if new:
            rib = Image.new('RGBA', (int(150 * s), int(22 * s)), col + (255,))
            ImageDraw.Draw(rib)
            rl = Image.new('RGBA', rib.size); rl.alpha_composite(rib)
            d = ImageDraw.Draw(rl)
            f = font('i900', 9 * s)
            tw = f.getlength('NOVO') + 3 * 0.2 * 9 * s * PT
            cx = (rib.size[0] - tw) / 2
            for c in 'NOVO':
                d.text((cx, 3 * s), c, font=f, fill=INK + (255,)); cx += f.getlength(c) + 0.2 * 9 * s * PT
            rl = rl.rotate(-38, expand=True, resample=Image.BICUBIC)
            mask = Image.new('L', (int(w), int(h)), 0)
            ImageDraw.Draw(mask).rectangle([0, 0, w, h], fill=255)
            layer = Image.new('RGBA', (int(w), int(h)))
            layer.alpha_composite(rl, (int(w - rl.size[0] + 38 * s), int(-14 * s)))
            self.comp(layer, x, y)

    def save(self, path):
        self.im.convert('RGB').save(path)


def font(key, size):
    px = max(4, int(round(size * PT)))
    k = (key, px)
    if k not in _fonts:
        fn = {'orb': 'Orbitron-Black.ttf', 'i400': 'Inter-Regular.otf', 'i500': 'Inter-Medium.otf', 'i600': 'Inter-SemiBold.otf',
              'i700': 'Inter-Bold.otf', 'i800': 'Inter-ExtraBold.otf', 'i900': 'Inter-Black.otf'}[key]
        _fonts[k] = ImageFont.truetype(F + fn, px)
    return _fonts[k]
