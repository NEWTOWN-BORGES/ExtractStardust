"""
EXTRACT: STARDUST — converte o mundo gerado (WorldGen/out, formato RACESTARS/Godot) para o importador do Unity.

Uso:  python WorldGen/tools/export_unity.py

Convenção de eixos: o Godot é destro com a frente em -Z; o Unity é canhoto com a frente em +Z.
  posição Unity = (x, y, -z)      rumo Unity (graus) = -yaw_godot (rad) * 180/pi      direção (dx, dz) -> (dx, -dz)
  (os modelos do Blender já saem com a frente em +Z, ver blender/build_assets.py:export_sdw)

Gera:
  WorldGen/out/unity/height.r32    alturas em metros, float32, 3073 x 3073, linha = z do Unity a crescer
  WorldGen/out/unity/world.json    rotas, portões, provas, túneis, pontes, água, peças, colossos... (coordenadas Unity)
  WorldGen/out/unity/veg.bin       vegetação: int32 n, depois n x (u8 tipo, 5 x f32: x, y, z, rumo, escala)
  Assets/World/Textures/biome.png, roads.png, ocean_mask.png, minimap.png  (já orientadas para o Unity)
"""
import json, math, os, struct
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, '..', 'out'))
DST = os.path.join(SRC, 'unity')
TEX = os.path.normpath(os.path.join(HERE, '..', '..', 'Assets', 'World', 'Textures'))
os.makedirs(DST, exist_ok=True)
os.makedirs(TEX, exist_ok=True)

data = json.load(open(os.path.join(SRC, 'map.json'), encoding='utf-8'))
SIZE, RES, CELL = float(data['size']), int(data['res']), float(data['cell'])
HALF = SIZE / 2
dz = zstandard.ZstdDecompressor()

def P(p):            # posição Godot -> Unity
    return [round(float(p[0]), 2), round(float(p[1]), 2), round(-float(p[2]), 2)]

def D(d):            # direção (dx, dz) Godot -> (dx, dz) Unity
    return [round(float(d[0]), 5), round(-float(d[1]), 5)]

def YAW(y):          # rumo Godot (rad) -> rumo Unity (graus)
    return round(-float(y) * 180.0 / math.pi, 3)

def route(r):
    out = []
    for q in r:
        out += P(q)
    return out

# ------------------------------------------------------------------ alturas
print('alturas...')
h = np.frombuffer(dz.decompress(open(os.path.join(SRC, 'height.zst'), 'rb').read()), dtype=np.float16).astype(np.float32).reshape(RES, RES)
h = h * CELL                                  # o ficheiro guarda metros / célula
h = h[::-1, :].copy()                         # linha 0 = z Godot mínimo = z Unity máximo -> inverter
h.astype('<f4').tofile(os.path.join(DST, 'height.r32'))
print(f'  {RES}x{RES}  min {h.min():.1f}  max {h.max():.1f}')

# ------------------------------------------------------------------ biomas e máscaras
print('texturas...')
bres = int(data['biome_res'])
biome = np.frombuffer(dz.decompress(open(os.path.join(SRC, 'biome.zst'), 'rb').read()), dtype=np.uint8).reshape(bres, bres, 4)
# PNG: linha de cima = v=1 no Unity = z máximo (= z mínimo do Godot): a orientação original já serve
Image.fromarray(biome.copy(), 'RGBA').save(os.path.join(TEX, 'biome.png'))
om = Image.open(os.path.join(SRC, 'ocean_mask.png')).convert('L')
om.save(os.path.join(TEX, 'ocean_mask.png'))
Image.open(os.path.join(SRC, 'minimap.png')).convert('RGB').save(os.path.join(TEX, 'minimap.png'))

# máscara das estradas (4096 px = 6 m/px), na orientação do Unity: linha de cima = z Unity máximo
print('máscara das estradas...')
pts, hws = [], []
for s in data['sections']:
    for v in s['variants']:
        r = np.array(v['route'], float)
        pts.append(r[:, [0, 2]]); hws.append(np.full(len(r), float(v['hw'])))
for e in data['events']:
    r = np.array(e['route'], float)
    hw = 46.0 if e['type'] == 'drag' else 34.0
    pts.append(r[:, [0, 2]]); hws.append(np.full(len(r), hw))
pts = np.vstack(pts); hws = np.concatenate(hws)
# densificar (as rotas têm um ponto a cada ~8 m)
tree = cKDTree(pts)
RM = 4096
cs = np.linspace(-HALF, HALF, RM).astype(np.float32)
zs_all = cs[::-1].copy()                     # linha 0 = z Unity máximo
mask = np.zeros((RM, RM), np.uint8)
for j0 in range(0, RM, 256):
    zs = zs_all[j0:j0 + 256]
    gx, gz = np.meshgrid(cs, -zs)            # z Unity = cs -> z Godot = -cs
    q = np.stack([gx.ravel(), gz.ravel()], 1)
    d, i = tree.query(q, distance_upper_bound=90.0, workers=-1)
    ok = np.isfinite(d)
    v = np.zeros(len(q), np.float32)
    hw = hws[np.minimum(i, len(hws) - 1)]
    t = np.clip((d - (hw - 4.0)) / 8.0, 0, 1)
    v[ok] = (1 - t * t * (3 - 2 * t))[ok]
    mask[j0:j0 + 256] = (v.reshape(gx.shape) * 255).astype(np.uint8)
Image.fromarray(mask, 'L').save(os.path.join(TEX, 'roads.png'))

# ------------------------------------------------------------------ vegetação
print('vegetação...')
words = np.frombuffer(dz.decompress(open(os.path.join(SRC, 'veg.zst'), 'rb').read()), dtype='<u4').reshape(-1, 2)
w0, w1 = words[:, 0].astype(np.int64), words[:, 1].astype(np.int64)
vx = (w0 & 0xFFFF) / 2.0 - HALF
vz = (w0 >> 16) / 2.0 - HALF
vy = (w1 & 0xFFFF) / 64.0 - 100.0
vt = (w1 >> 16) & 0xF
vyaw = ((w1 >> 20) & 0x3F) * (2 * math.pi / 64.0)
vsc = 0.6 + ((w1 >> 26) & 0x3F) * 0.03
with open(os.path.join(DST, 'veg.bin'), 'wb') as fh:
    fh.write(struct.pack('<i', len(words)))
    buf = bytearray()
    for k in range(len(words)):
        buf += struct.pack('<B5f', int(vt[k]), float(vx[k]), float(vy[k]), float(-vz[k]), float(-vyaw[k] * 180 / math.pi), float(vsc[k]))
    fh.write(buf)
print(f'  {len(words)} plantas')

# ------------------------------------------------------------------ mundo (JSON para o JsonUtility do Unity)
print('world.json...')
def placed(rows, named=True):
    out = []
    for r in rows:
        if named:
            name, x, y, z, yaw, sc = r[:6]
        else:
            x, y, z, yaw, sc = r[:5]; name = ''
        out.append({'name': name, 'p': P([x, y, z]), 'yaw': YAW(yaw), 'sc': float(sc)})
    return out

w = {
    'size': SIZE, 'res': RES, 'cell': CELL, 'ground': data['ground'], 'waterY': data['water_y'], 'fallY': data['fall_y'],
    'zones': [{'name': z['name'], 'biome': z['biome'], 'c': [z['c'][0], -z['c'][1]]} for z in data['zones']],
    'start': {'p': P(data['start']['p']), 'dir': D(data['start']['dir']), 'w': 200.0, 'name': 'Partida'},
    'finish': {'p': P(data['finish']['p']), 'dir': D(data['finish']['dir']), 'w': float(data['finish']['w']), 'name': 'Extração'},
    'checkpoints': [{'p': P(c['p']), 'dir': D(c['dir']), 'w': float(c['w']), 'name': c['name']} for c in data['checkpoints']],
    'sections': [{'key': s['key'], 'title': s['title'], 'biome': s['biome'],
                  'variants': [{'name': v['name'], 'level': int(v['level']), 'hw': float(v['hw']), 'length': float(v['length']),
                                'route': route(v['route']), 'jumps': [float(j) for j in v.get('jumps', [])]} for v in s['variants']]} for s in data['sections']],
    'tunnels': [{'name': t['name'], 'p': P(t['p']), 'yaw': YAW(t['yaw']), 'len': float(t['len']), 'tops': [float(x) for x in t['tops']],
                 'step': float(t.get('step', 24.0)), 'w': float(t.get('w', 84.0)), 'thw': float(t.get('thw', 18.0))} for t in data['tunnels']],
    'bridges': [{'name': b['name'], 'p': P(b['p']), 'yaw': YAW(b['yaw']), 'len': float(b['len']), 'width': float(b['width']),
                 'broken': float(b['broken']), 'deep': float(b.get('deep', 46.0))} for b in data['bridges']],
    'aqueducts': [{'p': P(a['p']), 'yaw': YAW(a['yaw']), 'n': int(a['n']), 'seg': float(a['seg']), 'deck': float(a['deck']),
                   'missing': [int(m) for m in a['missing']]} for a in data['aqueducts']],
    'waters': [{'c': [float(x['c'][0]), float(-x['c'][1])], 'sx': float(x['sx']), 'sz': float(x['sz']), 'yaw': YAW(x['yaw']), 'y': float(x['y'])}
               for x in data['waters']],
    'roofs': [{'name': 'canyon_roof', 'p': P(r['p']), 'yaw': YAW(r['yaw']), 'sc': 1.0} for r in data['roofs']],
    'oceanY': float(data['ocean']['y']), 'oceanSize': float(data['ocean']['size']),
    'props': placed(data['props']),
    'colossi': placed(data['colossi']),
    'islands': [{'name': 'float_island', 'p': P(r[:3]), 'yaw': YAW(r[3]), 'sc': float(r[4])} for r in data['islands']],
    'herds': placed(data['herds']),
    'grass': [{'name': 'grass_tuft', 'p': P(r[:3]), 'yaw': YAW(r[3]), 'sc': float(r[4])} for r in data['grass']],
    'flowers': [{'name': 'flowers', 'p': P(r[:3]), 'yaw': YAW(r[3]), 'sc': float(r[4])} for r in data['flowers']],
    'ferns': [{'name': 'fern', 'p': P(r[:3]), 'yaw': YAW(r[3]), 'sc': float(r[4])} for r in data['ferns']],
    'banners': [{'name': 'banner', 'p': P(r[:3]), 'yaw': YAW(r[3]), 'sc': float(r[4])} for r in data['banners']],
    'pads': [{'name': 'pad', 'p': P(r[:3]), 'yaw': YAW(r[3]), 'sc': 1.0} for r in data['pads']],
    'events': [],
    'vegTypes': data['veg_types'],
}
oc = data['ocean'].get('collision_rects', [])
w['oceanRects'] = []          # plano: cx, cz, sx, sz por retângulo (o JsonUtility não lê listas de listas)
for r in oc:
    w['oceanRects'] += [float(r[0]), float(-r[1]), float(r[2]), float(r[3])]
for e in data['events']:
    ev = {'id': e['id'], 'name': e['name'], 'type': e['type'], 'laps': int(e['laps']), 'length': float(e['length']),
          'route': route(e['route']), 'jumps': [float(j) for j in e.get('jumps', [])],
          'gates': [{'p': P(g['p']), 'dir': D(g['dir']), 'w': float(g['w']), 'name': ''} for g in e['gates']],
          'start': {'p': P(e['start']['p']), 'dir': D(e['start']['dir']), 'w': 0.0, 'name': 'Partida'}}
    if 'finish' in e:
        ev['finish'] = {'p': P(e['finish']['p']), 'dir': D(e['finish']['dir']), 'w': float(e['finish']['w']), 'name': 'Chegada'}
    else:
        ev['finish'] = {'p': [0, 0, 0], 'dir': [0, 1], 'w': 0.0, 'name': ''}
    w['events'].append(ev)
json.dump(w, open(os.path.join(DST, 'world.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('  secções', len(w['sections']), 'portões', len(w['checkpoints']), 'túneis', len(w['tunnels']), 'pontes', len(w['bridges']),
      'peças', len(w['props']), 'colossos', len(w['colossi']), 'provas', len(w['events']), 'ocean rects', len(w['oceanRects']) // 4)
print('feito')
