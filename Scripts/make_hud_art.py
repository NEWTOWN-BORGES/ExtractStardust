"""The race HUD's art, after the player's concept (2026-11-01: dark navy plates with glowing cyan edges, hexagon slots,
the speedometer with its brackets, the danger banner, the checkpoint toast, the standings rows, the icons, a blueprint
of each ship). Drawn at 4x and scaled down, written to SourceArt/UI/Icons/hud_*.png (Scripts/import_ui_icons.py brings
them into Unreal as T_Icon_hud_*; UEXRaceHudWidget uses them).
The same look for the menu, the hangar, the vault and the results (player, 2026-11-01: "a mesma direção de arte"): the
ui_* plates below are white, 9-sliced and tinted in the game (EXUi::Frame: the fill with the plate colour, the edge with
the outline colour), so one set of art draws every panel, line, card, tab and chip.
python3 Scripts/make_hud_art.py            (the HUD plates and icons and the menu art, numpy + pillow + opencv)
python3 Scripts/make_hud_art.py menu       (only the menu art, ui_*)
python3 Scripts/make_hud_art.py blueprints (also the ships seen from above, needs the bpy module)
"""
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'SourceArt', 'UI', 'Icons')
K = 4                                   # supersampling
NAVY = (8, 18, 38)
NAVY_HI = (18, 40, 74)
CYAN = (70, 220, 255)
BLUE = (40, 120, 255)
GOLD = (255, 200, 60)
ORANGE = (255, 120, 30)
RED = (255, 55, 40)


def poly_mask(w, h, pts):
    m = np.zeros((h * K, w * K), np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts) * K).astype(np.int32)], 255, lineType=cv2.LINE_AA)
    return m.astype(np.float32) / 255.0


def stroke_of(mask, width):
    r = max(1, int(round(width * K)))
    er = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    return np.clip(mask - er, 0, 1)


def blur(a, px):
    s = px * K
    return cv2.GaussianBlur(a, (0, 0), s) if s > 0 else a


class Layer:
    """Premultiplied RGBA at 4x, painted back to front."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.rgb = np.zeros((h * K, w * K, 3), np.float32)
        self.a = np.zeros((h * K, w * K), np.float32)

    def paint(self, alpha, colour, opacity=1.0):
        al = np.clip(alpha * opacity, 0, 1)
        col = np.array(colour, np.float32) / 255.0
        if col.ndim == 1:
            col = col[None, None, :]
        self.rgb = self.rgb * (1 - al[..., None]) + col * al[..., None]
        self.a = self.a * (1 - al) + al

    def save(self, name):
        rgb = self.rgb / np.maximum(self.a, 1e-4)[..., None]
        img = np.dstack([np.clip(rgb, 0, 1), np.clip(self.a, 0, 1)])
        im = Image.fromarray((img * 255).round().astype(np.uint8), 'RGBA').resize((self.w, self.h), Image.LANCZOS)
        im.save(os.path.join(OUT, name + '.png'))
        print('HUDART', name, im.size)


def vgrad(h, top, bottom):
    t = np.linspace(0, 1, h * K)[:, None, None]
    return np.array(top, np.float32)[None, None, :] * (1 - t) + np.array(bottom, np.float32)[None, None, :] * t


def plate(name, w, h, pts, edge=CYAN, fill_top=NAVY_HI, fill_bottom=NAVY, fill_alpha=0.82, glow=10, edge_w=2.2, inner=0.35,
          extra=None):
    """A plate: outer glow, a navy gradient fill, an inner glow along the edge, the bright edge."""
    L = Layer(w, h)
    m = poly_mask(w, h, pts)
    st = stroke_of(m, edge_w)
    L.paint(blur(st, glow) * (1 - m) * 1.6, edge, 0.75)
    fill = vgrad(h, fill_top, fill_bottom) / 255.0
    L.paint(m * fill_alpha, (fill * 255).astype(np.float32))
    L.paint(blur(st, 6) * m * 1.4, edge, inner)
    if extra:
        extra(L, m)
    L.paint(st, edge)
    L.save(name)


def chamfer(w, h, pad, cut, cut2=None):
    c2 = cut if cut2 is None else cut2
    x0, y0, x1, y1 = pad, pad, w - pad, h - pad
    return [(x0 + cut, y0), (x1, y0), (x1, y1 - c2), (x1 - c2, y1), (x0, y1), (x0, y0 + cut)]


def hexagon(cx, cy, r, flat=False):
    a0 = 0 if flat else -90
    return [(cx + r * math.cos(math.radians(a0 + 60 * i)), cy + r * math.sin(math.radians(a0 + 60 * i))) for i in range(6)]


def icon_layer(size=128):
    return Layer(size, size)


def glow_paint(L, alpha, colour, glow=5, strength=1.0):
    L.paint(blur(alpha, glow) * 1.5, colour, 0.8 * strength)
    L.paint(alpha, colour)


def main_art():
    os.makedirs(OUT, exist_ok=True)
    # plates (9-sliced in the game: the corners stay sharp at any size)
    plate('hud_panel', 256, 256, chamfer(256, 256, 22, 34, 34))
    plate('hud_panel_gold', 256, 256, chamfer(256, 256, 22, 34, 34), edge=GOLD, inner=0.3)
    plate('hud_timer', 512, 128, [(22, 64), (70, 20), (442, 20), (490, 64), (442, 108), (70, 108)])
    plate('hud_tab', 256, 72, [(20, 16), (236, 16), (220, 56), (36, 56)], fill_alpha=0.88, glow=6, edge_w=1.6)
    # hexagon slot and its key tab
    plate('hud_hex', 256, 256, hexagon(128, 128, 104), glow=12, edge_w=3.0)
    plate('hud_hex_on', 256, 256, hexagon(128, 128, 104), edge=GOLD, glow=14, edge_w=3.2, inner=0.45)
    # speedometer: the plate and two brackets either side
    def speed_extra(L, m):
        for side in (-1, 1):
            for k in range(3):
                x = 512 + side * (300 + k * 46)
                p = [(x, 60), (x + side * 34, 60), (x + side * 92, 178), (x + side * 34, 296), (x, 296), (x + side * 58, 178)]
                pm = poly_mask(1024, 360, p)
                L.paint(blur(pm, 8) * 1.4, CYAN, 0.55 - 0.12 * k)
                L.paint(pm, CYAN, 0.85 - 0.22 * k)
    plate('hud_speed', 1024, 360, [(300, 40), (724, 40), (790, 120), (760, 320), (264, 320), (234, 120)], glow=14, edge_w=2.6,
          extra=speed_extra)
    # standings rows: a quiet one and the player's, bright, with an arrow tip
    plate('hud_row', 512, 64, [(8, 8), (480, 8), (500, 32), (480, 56), (8, 56)], edge=(60, 110, 170), fill_alpha=0.62, glow=0,
          edge_w=1.0, inner=0.0)
    def me_extra(L, m):
        t = np.linspace(0, 1, 512 * K)[None, :, None]
        grad = (np.array(CYAN, np.float32) * (1 - t) + np.array(BLUE, np.float32) * t)
        L.paint(m * 0.85, np.broadcast_to(grad, (64 * K, 512 * K, 3)))
    plate('hud_row_me', 512, 64, [(8, 8), (470, 8), (504, 32), (470, 56), (8, 56)], edge=(200, 245, 255), fill_alpha=0.0, glow=3,
          edge_w=1.4, inner=0.2, extra=me_extra)
    # the danger banner: dark red plate, orange edge, hazard stripes at the end
    def warn_extra(L, m):
        stripes = np.zeros_like(m)
        for k in range(4):
            x = 470 + k * 34
            stripes = np.maximum(stripes, poly_mask(640, 160, [(x, 36), (x + 18, 36), (x - 10, 124), (x - 28, 124)]))
        L.paint(stripes * m, ORANGE, 0.95)
    plate('hud_warn', 640, 160, chamfer(640, 160, 18, 26, 26), edge=ORANGE, fill_top=(70, 14, 6), fill_bottom=(34, 6, 4),
          fill_alpha=0.88, glow=12, edge_w=2.4, inner=0.45, extra=warn_extra)
    # the checkpoint toast: navy, pointed at the left, a gold line under the prize
    def toast_extra(L, m):
        L.paint(poly_mask(640, 160, [(330, 118), (600, 118), (596, 124), (326, 124)]), GOLD, 0.9)
    plate('hud_toast', 640, 160, [(18, 80), (70, 22), (622, 22), (622, 138), (70, 138)], glow=12, edge_w=2.4, extra=toast_extra)
    # icons
    L = icon_layer()
    ring = np.zeros((128 * K, 128 * K), np.float32)
    cv2.circle(ring, (64 * K, 70 * K), 40 * K, 1.0, 7 * K, lineType=cv2.LINE_AA)
    cv2.rectangle(ring, ((64 - 8) * K, 14 * K), ((64 + 8) * K, 24 * K), 1.0, -1)
    cv2.line(ring, (64 * K, 70 * K), (64 * K, 44 * K), 1.0, 6 * K, lineType=cv2.LINE_AA)
    cv2.line(ring, (64 * K, 70 * K), (84 * K, 80 * K), 1.0, 6 * K, lineType=cv2.LINE_AA)
    cv2.line(ring, (96 * K, 34 * K), (104 * K, 26 * K), 1.0, 6 * K, lineType=cv2.LINE_AA)
    glow_paint(L, ring, (235, 250, 255))
    L.save('hud_stopwatch')
    L = icon_layer()
    cup = poly_mask(128, 128, [(34, 18), (94, 18), (90, 52), (74, 72), (54, 72), (38, 52)])
    stem = poly_mask(128, 128, [(58, 72), (70, 72), (72, 92), (56, 92)])
    base = poly_mask(128, 128, [(40, 92), (88, 92), (92, 108), (36, 108)])
    handles = np.zeros_like(cup)
    cv2.ellipse(handles, (30 * K, 36 * K), (14 * K, 14 * K), 0, 90, 300, 1.0, 6 * K, lineType=cv2.LINE_AA)
    cv2.ellipse(handles, (98 * K, 36 * K), (14 * K, 14 * K), 0, -120, 90, 1.0, 6 * K, lineType=cv2.LINE_AA)
    body = np.clip(cup + stem + base + handles, 0, 1)
    glow_paint(L, body, GOLD, glow=6)
    L.paint(poly_mask(128, 128, [(46, 24), (56, 24), (52, 56), (46, 50)]), (255, 245, 200), 0.8)
    L.save('hud_trophy')
    L = icon_layer()
    tri = poly_mask(128, 128, [(64, 12), (120, 112), (8, 112)])
    glow_paint(L, tri, RED, glow=7)
    L.paint(poly_mask(128, 128, [(64, 26), (108, 104), (20, 104)]), (255, 90, 40), 1.0)
    mark = poly_mask(128, 128, [(58, 44), (70, 44), (67, 80), (61, 80)])
    dot = np.zeros_like(mark)
    cv2.circle(dot, (64 * K, 92 * K), 6 * K, 1.0, -1, lineType=cv2.LINE_AA)
    L.paint(np.clip(mark + dot, 0, 1), (255, 255, 255))
    L.save('hud_hazard')
    L = icon_layer()
    bolt = poly_mask(128, 128, [(74, 8), (30, 72), (60, 72), (48, 120), (98, 50), (66, 50), (82, 8)])
    glow_paint(L, bolt, (255, 210, 40), glow=6)
    L.save('hud_bolt')
    L = icon_layer()
    pole = poly_mask(128, 128, [(22, 10), (30, 10), (30, 120), (22, 120)])
    L.paint(pole, (230, 235, 240))
    for i in range(5):
        for j in range(4):
            x0, y0 = 30 + i * 17, 14 + j * 14 + 4 * math.sin(i * 0.9)
            sq = poly_mask(128, 128, [(x0, y0), (x0 + 17, y0 + 3), (x0 + 17, y0 + 17), (x0, y0 + 14)])
            L.paint(sq, (245, 248, 250) if (i + j) % 2 == 0 else (20, 24, 30))
    L.save('hud_flag')
    # the spoils' coin, as the piggy's: a gold disc, a rim, a four-point star, a glint
    L = icon_layer()
    disc = np.zeros((128 * K, 128 * K), np.float32)
    cv2.circle(disc, (64 * K, 64 * K), 54 * K, 1.0, -1, lineType=cv2.LINE_AA)
    glow_paint(L, disc, (255, 190, 40), glow=5, strength=0.7)
    yy, xx = np.mgrid[0:128 * K, 0:128 * K] / float(128 * K)
    shade = np.clip(1.15 - 0.9 * np.hypot(xx - 0.38, yy - 0.34), 0.45, 1.0)[..., None]
    L.paint(disc, (np.array([255, 205, 60], np.float32) * shade).astype(np.float32))
    rim = np.zeros_like(disc)
    cv2.circle(rim, (64 * K, 64 * K), 44 * K, 1.0, 4 * K, lineType=cv2.LINE_AA)
    L.paint(rim, (200, 130, 20), 0.85)
    star = poly_mask(128, 128, [(64, 30), (71, 57), (98, 64), (71, 71), (64, 98), (57, 71), (30, 64), (57, 57)])
    L.paint(star, (255, 245, 190), 0.95)
    edge = stroke_of(disc, 2.0)
    L.paint(edge, (150, 90, 10), 0.9)
    L.save('hud_coin')


def blueprints():
    """Each ship seen from above, nose up, as a blueprint: a faint cyan fill, its panel lines, a glowing outline."""
    import bpy
    ships = ('vortex', 'bastion', 'strix', 'wraith', 'nomad')
    tmp = os.path.join(OUT, '_bp')
    os.makedirs(tmp, exist_ok=True)
    for ship in ships:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=os.path.join(HERE, '..', 'SourceArt', 'TestShips', ship + '.fbx'))
        mat = bpy.data.materials.new('N')
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        mul = nt.nodes.new('ShaderNodeVectorMath'); mul.operation = 'MULTIPLY_ADD'
        mul.inputs[1].default_value = (0.5, 0.5, 0.5); mul.inputs[2].default_value = (0.5, 0.5, 0.5)
        em = nt.nodes.new('ShaderNodeEmission')
        outn = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(geo.outputs['Normal'], mul.inputs[0])
        nt.links.new(mul.outputs[0], em.inputs['Color'])
        nt.links.new(em.outputs[0], outn.inputs['Surface'])
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        lo = np.array([1e9, 1e9, 1e9]); hi = -lo
        for o in meshes:
            o.data.materials.clear(); o.data.materials.append(mat)
            for v in o.bound_box:
                p = np.array(o.matrix_world @ __import__('mathutils').Vector(v))
                lo, hi = np.minimum(lo, p), np.maximum(hi, p)
        c = (lo + hi) / 2
        cam_data = bpy.data.cameras.new('C'); cam_data.type = 'ORTHO'
        cam_data.ortho_scale = float(max(hi[0] - lo[0], hi[1] - lo[1]) * 1.08)
        cam = bpy.data.objects.new('C', cam_data)
        bpy.context.scene.collection.objects.link(cam)
        cam.location = (c[0], c[1], hi[2] + 10)
        cam.rotation_euler = (0, 0, math.pi)          # nose (-Y) up in the picture
        sc = bpy.context.scene
        sc.camera = cam
        sc.render.engine = 'CYCLES'
        sc.cycles.samples = 4
        sc.render.film_transparent = True
        sc.render.resolution_x = sc.render.resolution_y = 768
        sc.view_settings.view_transform = 'Standard'
        sc.render.filepath = os.path.join(tmp, ship + '.png')
        bpy.ops.render.render(write_still=True)
        im = np.array(Image.open(sc.render.filepath).convert('RGBA')).astype(np.float32) / 255.0
        a = im[..., 3]
        nrm = im[..., :3]
        g = np.zeros_like(a)
        for ch in range(3):
            gx = cv2.Sobel(nrm[..., ch], cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(nrm[..., ch], cv2.CV_32F, 0, 1, ksize=3)
            g = np.maximum(g, np.hypot(gx, gy))
        lines = np.clip((g - 0.35) / 0.4, 0, 1) * (cv2.erode(a, np.ones((5, 5), np.uint8)) > 0.5)
        sil = (a > 0.5).astype(np.float32)
        outline = np.clip(cv2.dilate(sil, np.ones((5, 5), np.uint8)) - cv2.erode(sil, np.ones((3, 3), np.uint8)), 0, 1)
        S = 768
        L = Layer(S // K, S // K)
        L.rgb = np.zeros((S, S, 3), np.float32); L.a = np.zeros((S, S), np.float32)
        L.paint(cv2.GaussianBlur(outline, (0, 0), 6) * 1.5, CYAN, 0.7)
        L.paint(sil, CYAN, 0.16)
        L.paint(lines, (150, 235, 255), 0.8)
        L.paint(outline, (190, 245, 255), 1.0)
        L.w = L.h = 256
        L.save('hud_ship_' + ship)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


# ---------------------------------------------------------------------------------------------------------------- menu
# White shapes for EXUi (tinted in the game). The chamfer is CUT px at 128 px; the game draws them 9-sliced at
# Corner / CUT of their size, so the corners stay sharp and the edge about 1.5 px at any size.
CUT = 20


def inner_stroke(mask, width):
    r = max(1, int(round(width * K)))
    er = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)),
                   borderType=cv2.BORDER_CONSTANT, borderValue=0)
    return np.clip(mask - er, 0, 1)


def white(name, w, h, alpha):
    L = Layer(w, h)
    L.paint(alpha, (255, 255, 255))
    L.save(name)


def shape_set(prefix, w, h, pts, fill_bottom=0.78, wash=False, inset=False):
    """<prefix> (the fill: white at the top to grey at the bottom), <prefix>_edge (the edge and its inner glow),
    <prefix>_wash (the selection's wash, bright on the left), <prefix>_inset (a soft glow inside the edges), when asked."""
    m = poly_mask(w, h, pts)
    L = Layer(w, h)
    shade = np.linspace(1.0, fill_bottom, h * K)[:, None, None] * 255.0
    L.paint(m, np.broadcast_to(shade, (h * K, w * K, 1)).repeat(3, axis=2).astype(np.float32))
    L.save(prefix)
    st = inner_stroke(m, 2.6)
    white(prefix + '_edge', w, h, np.clip(st + blur(st, 5) * m * 0.55, 0, 1))
    if wash:
        fade = np.clip(1.0 - np.linspace(0, 1, w * K)[None, :] * 1.05, 0, 1)
        white(prefix + '_wash', w, h, m * fade)
    if not inset:
        return
    core = cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * 9 * K + 1, 2 * 9 * K + 1)),
                     borderType=cv2.BORDER_CONSTANT, borderValue=0)
    white(prefix + '_inset', w, h, np.clip(blur(1.0 - core, 7) * m, 0, 1))


def menu_art():
    os.makedirs(OUT, exist_ok=True)
    # panels, lines, chips: the top-left and bottom-right corners cut, as the HUD's plates
    shape_set('ui_plate', 128, 128, [(CUT, 0), (128, 0), (128, 128 - CUT), (128 - CUT, 128), (0, 128), (0, CUT)], wash=True)
    # cards: only the bottom-right corner cut (the photo fills the top)
    shape_set('ui_card', 128, 128, [(0, 0), (128, 0), (128, 128 - CUT), (128 - CUT, 128), (0, 128)], inset=True)
    # tabs: leaning forward like the figures (drawn at their own height: 9-sliced across only)
    shape_set('ui_tab', 128, 48, [(10, 0), (128, 0), (118, 48), (0, 48)], fill_bottom=0.86)
    # the primary button in its own colours: cyan to blue, a sheen on the top, a light edge
    w, h, c = 256, 72, 16
    m = poly_mask(w, h, [(c, 0), (w, 0), (w, h - c), (w - c, h), (0, h), (0, c)])
    L = Layer(w, h)
    t = np.linspace(0, 1, w * K)[None, :, None]
    grad = np.array(CYAN, np.float32) * (1 - t) + np.array(BLUE, np.float32) * t
    L.paint(m, np.broadcast_to(grad, (h * K, w * K, 3)))
    sheen = np.clip(1.0 - np.linspace(0, 1, h * K)[:, None] / 0.45, 0, 1) * np.ones((1, w * K))
    L.paint(m * sheen, (255, 255, 255), 0.22)
    st = inner_stroke(m, 2.0)
    L.paint(blur(st, 4) * m, (220, 250, 255), 0.5)
    L.paint(st, (215, 248, 255), 0.95)
    L.save('ui_btn')


if __name__ == '__main__':
    if 'menu' not in sys.argv:
        main_art()
    menu_art()
    if 'blueprints' in sys.argv:
        blueprints()
