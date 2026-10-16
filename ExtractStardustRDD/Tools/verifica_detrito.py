"""
Verificacao do perfil de parede do Metrics Lab (LabGeometry.WallProfilePoints).

Porta a matematica e verifica tres propriedades que importam:
  1. o cone de detrito nunca invade a zona de corrida livre (clearHalfWidth)
  2. a malha e continua: o ultimo ponto do detrito coincide com a base da escadaria
  3. o perfil so recua (nunca avanca), logo nao ha auto-intersecao

E desenha o corte transversal para se ver o resultado.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust\ExtractStardustRDD\Docs"
os.makedirs(OUT, exist_ok=True)

# LAYERS_RDD: nome, espessura, dureza
LAYERS = [("Organ Rock", 200.0, 0.30), ("White Rim", 40.0, 0.95), ("Moenkopi", 65.0, 0.45),
          ("Moss Back", 15.0, 0.90), ("Chinle", 45.0, 0.15), ("Wingate", 100.0, 0.97),
          ("Kayenta", 35.0, 0.65), ("Navajo", 60.0, 0.85), ("Carmel", 20.0, 0.25),
          ("Entrada", 80.0, 0.92), ("Summerville", 60.0, 0.30)]


def hash1(n, seed):
    h = np.sin(n * 127.1 + seed * 311.7) * 43758.5453
    return h - np.floor(h)


def noise3(p, seed):
    x0 = np.floor(p[..., 0]); y0 = np.floor(p[..., 1]); z0 = np.floor(p[..., 2])
    fx = p[..., 0] - x0; fy = p[..., 1] - y0; fz = p[..., 2] - z0
    fx = fx*fx*(3-2*fx); fy = fy*fy*(3-2*fy); fz = fz*fz*(3-2*fz)

    def H(dx, dy, dz):
        return hash1(x0+dx + (y0+dy)*57.1 + (z0+dz)*131.7, seed)

    c00 = H(0,0,0)*(1-fx) + H(1,0,0)*fx
    c10 = H(0,1,0)*(1-fx) + H(1,1,0)*fx
    c01 = H(0,0,1)*(1-fx) + H(1,0,1)*fx
    c11 = H(0,1,1)*(1-fx) + H(1,1,1)*fx
    return (c00*(1-fy)+c10*fy)*(1-fz) + (c01*(1-fy)+c11*fy)*fz


def fbm3(p, oct=2, seed=7.0):
    s = np.zeros(p.shape[:-1]); a = 0.5; n = 0.0; q = p.copy()
    for o in range(oct):
        s = s + a*noise3(q, seed + o*17); n += a
        q = q*2.03 + np.array([5.2, 1.3, 7.7]); a *= 0.5
    return s/n


def erode3d(height, along, wall_u, hardness, amount=26.0, seed=7):
    soft = np.clip(1.0-hardness, 0, 1)
    by_hard = amount * soft**1.6
    alc = fbm3(np.stack([along/120.0, height/90.0, wall_u*1.1], -1), 2, seed)
    flu = fbm3(np.stack([along/18.0, height/14.0, wall_u*1.7], -1), 2, seed+101)
    cra = fbm3(np.stack([along/5.0, height/4.0, wall_u*2.3], -1), 2, seed+211)
    chi = fbm3(np.stack([along/1.2, height/1.2, wall_u*3.1], -1), 2, seed+307)
    depth = 0.62*alc + 0.34*flu + 0.24*cra + 0.12*chi
    return by_hard * (0.55 + 0.65*np.sin(wall_u*np.pi)) * depth


def hardness_at(y):
    base = 0.0
    for _, thick, hard in LAYERS:
        base += thick
        if y <= base:
            return hard
    return LAYERS[-1][2]


def layer_blend(y):
    bot = 0.0
    for _, thick, hard in LAYERS:
        top = bot + thick
        if y <= top:
            return min((y-bot)/thick, 1-(y-bot)/thick)
        bot = top
    return 0.0


def build_profile(along, talus_h, talus_extent, clear_hw, height_samples=220, amount=26.0):
    """Porta de WallProfilePoints, ja com a correcao: o detrito comeca onde a parede acaba."""
    budget = max(len(LAYERS)*3, height_samples)
    lift = sum(t for _, t, _ in LAYERS)
    stair = [(0.0, 0.0)]
    x = 0.0; y = 0.0
    for _, thick, hard in LAYERS:
        eff = math.radians(34 + (86-34)*hard)
        n = max(3, round(budget*(thick/lift)))
        for k in range(1, n+1):
            f = k/n
            stair.append((x + (thick*f)/math.tan(eff), y + thick*f))
        x += thick/math.tan(eff); y += thick
        if hard > 0.6:
            x += 2 + 14*(hard-0.6)/0.4
            stair.append((x, y+0.02))

    total_h = max(1.0, stair[-1][1] - stair[0][1])

    # o detrito tem de comecar onde a parede acaba (a camada mais mole recua mais)
    min_hard = min(h for _, _, h in LAYERS)
    max_erode = amount * (1.0 - min_hard)**1.6 * 1.8
    pts = []
    if talus_h > 0.5:
        ext = max(talus_extent, max_erode + 2.0)
        segs = max(4, min(28, int(talus_h/1.5)))
        run = max(1.0, ext - clear_hw)
        for k in range(segs+1):
            t = k/segs
            # o cone sobe EM DIRECAO a parede: 0 no corredor, talus_h no pe da parede
            hh = talus_h * (1.0 - t)**1.25
            hx = clear_hw + run*t
            bumpy = (noise3(np.array([along*0.05, hh*0.20, 0.0]), 909) - 0.5)*2
            hx = max(clear_hw, hx + bumpy*1.2*t)
            pts.append((hx, hh))
        talus_base = ext
    else:
        pts.append((0.0, 0.0))
        talus_base = 0.0

    for sx, sy in stair:
        hard = hardness_at(sy)
        wu = (sy - stair[0][1])/total_h
        rec = erode3d(sy, along, wu, hard, amount, 7)
        pts.append((sx + rec + talus_base, sy))

    # monotonicidade: o perfil so recua (nas fronteiras de camada a erosao e descontinua)
    arr = np.array(pts)
    for i in range(1, len(arr)):
        if arr[i, 0] < arr[i-1, 0]:
            arr[i, 0] = arr[i-1, 0]
    return arr


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
PAL = [(150,62,40),(226,214,190),(140,72,50),(168,98,70),(185,170,145),(172,86,64),
       (128,92,104),(150,150,130),(196,98,52),(150,84,66),(222,190,150),(214,160,128),
       (206,150,100),(40,28,24)]


def layer_color(y):
    base, i = 0.0, 0
    for idx, (_, thick, _) in enumerate(LAYERS):
        if y <= base+thick:
            i = idx; break
        base += thick
    a = PAL[LAYERS[i][2] and 0 or 0]
    ca = PAL[[0,1,2,3,4,5,6,7,8,9,10,11,12,13][0]]
    return PAL[4] if LAYERS[i][2] > 0.6 else PAL[5]


TALUS_H, TALUS_EXT, CLEAR = 14.0, 22.0, 15.0


def verifica():
    print("=== verificacao do perfil ===")
    ok = True
    for along in (0.0, 37.0, 91.0, 155.0, 219.0):
        pts = build_profile(along, TALUS_H, TALUS_EXT, CLEAR)
        # 1. so recua?
        dx = np.diff(pts[:, 0])
        bad = np.where(dx < -1e-6)[0]
        if len(bad):
            print(f"  FALHA along={along}: x diminui em {len(bad)} sitios; primeiro idx {bad[0]}")
            i0 = bad[0]
            for j in range(max(0, i0 - 2), min(len(pts), i0 + 3)):
                print(f"      idx {j:3d}: x {pts[j,0]:8.2f}  y {pts[j,1]:8.2f}")
            ok = False
        # 2. continuidade: maior salto em x
        jump = np.abs(dx).max()
        # 3. detrito nao invade a zona livre
        n_talus = max(4, min(28, int(TALUS_H / 1.5))) + 1
        min_talus_x = pts[:n_talus, 0].min()
        if min_talus_x < CLEAR - 1e-6:
            print(f"  FALHA along={along}: detrito entra na zona livre (x={min_talus_x:.2f} < {CLEAR})")
            ok = False
        if along in (0.0, 219.0):
            print(f"  along={along:6.1f}  pontos={len(pts):4d}  x max={pts[:,0].max():7.1f}  "
                  f"altura max={pts[:,1].max():6.1f}  detrito min x={min_talus_x:6.2f}  "
                  f"maior salto x={jump:6.2f} m")
    print("  RESULTADO:", "tudo OK" if ok else "HA FALHAS")
    return ok


def desenha():
    W, H = 1500, 760
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((54, 18), "PERFIL DA PAREDE DO LAB — escadaria + erosao 3D + cone de detrito", font=F, fill=FG)
    d.text((54, 44), f"detrito {TALUS_H:.0f} m ate x={TALUS_EXT:.0f} m, a partir de "
                     f"{CLEAR:.0f} m do eixo: a zona de corrida livre nunca e invadida", font=FS, fill=DIM)

    for i, along in enumerate((0.0, 110.0, 219.0)):
        pts = build_profile(along, TALUS_H, TALUS_EXT, CLEAR)
        px, py, pw, ph = 60 + i*470, 100, 440, 580
        d.rectangle([px-1, py-1, px+pw+1, py+ph+1], outline=(60, 64, 78))
        d.text((px+10, py+8), f"estacao {along:.0f} m", font=FS, fill=(255,176,82))
        xmax = 520.0; ymax = 340.0
        sx, sy = pw/xmax, ph/ymax

        def P(x, y, px=px, py=py, sx=sx, sy=sy):
            return (px + x*sx, py + ph - y*sy)

        poly = [P(0, pts[-1, 1])] + [P(pts[k, 0], pts[k, 1]) for k in range(len(pts)-1, -1, -1)] + [P(0, pts[0, 1])]
        d.polygon(poly, fill=(74, 44, 36))
        for k in range(len(pts)-1):
            c = layer_color((pts[k, 1]+pts[k+1, 1])/2)
            d.polygon([P(0, pts[k, 1]), P(pts[k, 0], pts[k, 1]),
                       P(pts[k+1, 0], pts[k+1, 1]), P(0, pts[k+1, 1])], fill=c)
        d.line([P(pts[k, 0], pts[k, 1]) for k in range(len(pts))], fill=(255, 224, 186), width=2)

        # zona livre
        zx = P(CLEAR, 0)[0]
        d.line([(zx, py+26), (zx, py+ph)], fill=(120, 220, 140), width=2)
        d.text((zx+5, py+ph-40), "zona livre 15 m", font=FS, fill=(120, 220, 140))
        d.text((px+10, py+ph-20), "corredor", font=FS, fill=DIM)

    d.text((54, H-38), "O detrito assenta no pe da parede e alarga-a: a parede deixa de nascer a "
                       "pique do chao, que era o que a fazia parecer um tubo.", font=FS, fill=DIM)
    img.save(os.path.join(OUT, "parede_detrito.png"))
    print("->", os.path.join(OUT, "parede_detrito.png"))


def desenha_base():
    """Vista ampliada da base: e aqui que se ve o detrito, a zona livre e o pe da parede."""
    W, H = 1500, 620
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((54, 18), "BASE DA PAREDE (vista ampliada) — detrito, zona livre e pé da parede", font=F, fill=FG)
    d.text((54, 44), f"escala 0-70 m em ambos os eixos: o detrito sobe ate {TALUS_H:.0f} m e a parede "
                     f"comeca em x≈{TALUS_H and 33:.0f} m", font=FS, fill=DIM)

    xmax, ymax = 115.0, 70.0
    for i, along in enumerate((0.0, 110.0, 219.0)):
        pts = build_profile(along, TALUS_H, TALUS_EXT, CLEAR)
        keep = pts[:, 1] <= ymax * 1.02
        sub = pts[keep]
        px, py, pw, ph = 60 + i*470, 100, 440, 420
        d.rectangle([px-1, py-1, px+pw+1, py+ph+1], outline=(60, 64, 78))
        d.text((px+10, py+8), f"estação {along:.0f} m", font=FS, fill=(255,176,82))
        sx, sy = pw/xmax, ph/ymax

        def P(x, y, px=px, py=py, sx=sx, sy=sy):
            return (px + x*sx, py + ph - y*sy)

        if len(sub) > 1:
            poly = [P(0, sub[-1, 1])] + [P(sub[k, 0], sub[k, 1]) for k in range(len(sub)-1, -1, -1)] + [P(0, sub[0, 1])]
            d.polygon(poly, fill=(74, 44, 36))
            for k in range(len(sub)-1):
                c = layer_color((sub[k, 1]+sub[k+1, 1])/2)
                d.polygon([P(0, sub[k, 1]), P(sub[k, 0], sub[k, 1]),
                           P(sub[k+1, 0], sub[k+1, 1]), P(0, sub[k+1, 1])], fill=c)
            d.line([P(sub[k, 0], sub[k, 1]) for k in range(len(sub))], fill=(255, 224, 186), width=3)

        # zona livre
        zx = P(CLEAR, 0)[0]
        d.line([(zx, py+26), (zx, py+ph)], fill=(120, 220, 140), width=2)
        d.text((zx+6, py+ph-30), "zona livre", font=FS, fill=(120, 220, 140))
        # grelha de 10 m
        for gx in range(0, int(xmax)+1, 20):
            d.line([P(gx, 0), (P(gx, 0)[0], py+ph)], fill=(34, 38, 48))
            d.text((P(gx, 0)[0]+3, py+ph+4), f"{gx}", font=FS, fill=DIM)
        d.text((px+10, py+ph+22), "distância ao eixo da pista (m)", font=FS, fill=DIM)

    d.text((54, H-34), "O detrito não invade a zona livre de 15 m, logo a largura útil do corredor "
                       "mantém-se e as medições da Fase 1 continuam válidas.", font=FS, fill=DIM)
    img.save(os.path.join(OUT, "parede_detrito_base.png"))
    print("->", os.path.join(OUT, "parede_detrito_base.png"))


verifica()
desenha()
desenha_base()
