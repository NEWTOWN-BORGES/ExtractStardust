# HD 2x of the piggy bank sheets (player, 2026-11-01: a separate HD 2x folder, only the per-animation sheets).
# AI upscaling with Real-ESRGAN's anime model (realesr-animevideov3, BSD-3-Clause, by Xintao Wang et al.): x4, then
# scaled down to x2 with area filtering, so the lines stay clean. It does not redraw the pig, but the fine detail it
# adds is estimated by the model. Colour and alpha go through it separately (colour premultiplied over black) and are
# put back together, so the cuts, cells and pivots are exactly those of the native sheets, doubled.
# Runs without PyTorch: the .pth weights are read from their zip, the network is written as an ONNX graph and run with
# onnxruntime. python3 Scripts/piggy_sprites/upscale_hd.py  (needs numpy, pillow, opencv-python-headless, onnx,
# onnxruntime; downloads the 2.5 MB model once).
import io, json, os, pickle, sys, urllib.request, zipfile
import cv2
import numpy as np
import onnx
import onnxruntime as ort
from onnx import helper, numpy_helper, TensorProto
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PIGGY = os.path.join(HERE, '..', '..', 'SourceArt', 'UI', 'Piggy')
OUT = os.path.join(PIGGY, 'HD2x')
MODEL_URL = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth'
CACHE = os.environ.get('PIGGY_SR_CACHE', os.path.join(os.path.expanduser('~'), '.cache', 'piggy_sr'))

class AttrDict(dict):
    """A state dict (PyTorch keeps a _metadata attribute on it)."""


def load_pth(path):
    """A PyTorch zip checkpoint as numpy arrays, without PyTorch."""
    z = zipfile.ZipFile(path)
    root = z.namelist()[0].split('/')[0]
    class Storage:
        def __init__(self, key, dtype):
            self.data = np.frombuffer(z.read('%s/data/%s' % (root, key)), dtype=dtype)
    def rebuild(storage, offset, size, stride, *rest):
        a = storage.data
        return np.lib.stride_tricks.as_strided(a[offset:], shape=tuple(size), strides=tuple(s * a.itemsize for s in stride)).copy()
    class U(pickle.Unpickler):
        def find_class(self, mod, name):
            if name == '_rebuild_tensor_v2':
                return rebuild
            if mod == 'torch' and name.endswith('Storage'):
                return {'FloatStorage': np.float32, 'HalfStorage': np.float16, 'DoubleStorage': np.float64}.get(name, np.float32)
            if mod == 'collections' and name == 'OrderedDict':
                return AttrDict
            return super().find_class(mod, name)
        def persistent_load(self, pid):
            _, dtype, key, _loc, _n = pid
            return Storage(key, dtype)
    return U(io.BytesIO(z.read('%s/data.pkl' % root))).load()

def build_model(params, scale=4):
    """SRVGGNetCompact (conv + PReLU x 17, conv to 3*scale^2, pixel shuffle, plus the nearest-upscaled input)."""
    nodes, inits = [], []
    convs = sorted({int(k.split('.')[1]) for k in params if k.startswith('body.') and k.endswith('.weight') and params[k].ndim == 4})
    x = 'input'
    for i in convs:
        w, b = params['body.%d.weight' % i], params['body.%d.bias' % i]
        inits += [numpy_helper.from_array(w.astype(np.float32), 'w%d' % i), numpy_helper.from_array(b.astype(np.float32), 'b%d' % i)]
        nodes.append(helper.make_node('Conv', [x, 'w%d' % i, 'b%d' % i], ['c%d' % i], pads=[1, 1, 1, 1], kernel_shape=[3, 3]))
        x = 'c%d' % i
        if 'body.%d.weight' % (i + 1) in params and params['body.%d.weight' % (i + 1)].ndim == 1:
            a = params['body.%d.weight' % (i + 1)].astype(np.float32).reshape(-1, 1, 1)
            inits.append(numpy_helper.from_array(a, 'a%d' % i))
            nodes.append(helper.make_node('PRelu', [x, 'a%d' % i], ['p%d' % i]))
            x = 'p%d' % i
    nodes.append(helper.make_node('DepthToSpace', [x], ['up'], blocksize=scale, mode='CRD'))
    inits.append(numpy_helper.from_array(np.array([1, 1, scale, scale], np.float32), 'scales'))
    nodes.append(helper.make_node('Resize', ['input', '', 'scales'], ['base'], mode='nearest'))
    nodes.append(helper.make_node('Add', ['up', 'base'], ['output']))
    g = helper.make_graph(nodes, 'srvgg', [helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3, None, None])],
                          [helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 3, None, None])], inits)
    m = helper.make_model(g, opset_imports=[helper.make_opsetid('', 13)])
    m.ir_version = 8
    so = ort.SessionOptions()
    so.intra_op_num_threads = os.cpu_count() or 4
    return ort.InferenceSession(m.SerializeToString(), so, providers=['CPUExecutionProvider'])

def sr(sess, img, tile=192, pad=12, scale=4, skip=None):
    """img HxWx3 in 0..1 -> (4H)x(4W)x3, in tiles with a margin; tiles where skip is all False are left black."""
    h, w = img.shape[:2]
    out = np.zeros((h * scale, w * scale, 3), np.float32)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            y0, x0, y1, x1 = y, x, min(h, y + tile), min(w, x + tile)
            if skip is not None and not skip[y0:y1, x0:x1].any():
                continue
            Y0, X0, Y1, X1 = max(0, y0 - pad), max(0, x0 - pad), min(h, y1 + pad), min(w, x1 + pad)
            t = img[Y0:Y1, X0:X1].transpose(2, 0, 1)[None].astype(np.float32)
            r = sess.run(None, {'input': t})[0][0].transpose(1, 2, 0)
            oy, ox = (y0 - Y0) * scale, (x0 - X0) * scale
            out[y0 * scale:y1 * scale, x0 * scale:x1 * scale] = r[oy:oy + (y1 - y0) * scale, ox:ox + (x1 - x0) * scale]
    return np.clip(out, 0, 1)

def main():
    os.makedirs(CACHE, exist_ok=True)
    pth = os.path.join(CACHE, 'realesr-animevideov3.pth')
    if not os.path.exists(pth):
        urllib.request.urlretrieve(MODEL_URL, pth)
    ck = load_pth(pth)
    sess = build_model(ck.get('params', ck))
    meta = json.load(open(os.path.join(PIGGY, 'Piggy_Spritesheet.json')))
    os.makedirs(OUT, exist_ok=True)
    only = set(a for a in sys.argv[1:] if not a.startswith('--'))
    for a in meta['animations']:
        if only and a['name'] not in only:
            continue
        src = np.array(Image.open(os.path.join(PIGGY, a['file'])).convert('RGBA')).astype(np.float32) / 255.0
        h, w = src.shape[:2]
        al = src[..., 3]
        vis = cv2.dilate((al > 0).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        prem = src[..., :3] * al[..., None]
        p4 = sr(sess, prem, skip=vis)
        a4 = sr(sess, np.repeat(al[..., None], 3, axis=2), skip=vis).mean(axis=2)
        p2 = cv2.resize(p4, (w * 2, h * 2), interpolation=cv2.INTER_AREA)
        a2 = np.clip(cv2.resize(a4, (w * 2, h * 2), interpolation=cv2.INTER_AREA), 0, 1)
        a2[a2 < 1.5 / 255] = 0
        rgb = np.clip(p2 / np.maximum(a2, 1e-4)[..., None], 0, 1)
        rgb[a2 == 0] = 0
        out = np.dstack([rgb, a2])
        Image.fromarray(np.round(out * 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, a['file']), optimize=True)
        print('HD2x', a['name'], '%dx%d' % (w * 2, h * 2), flush=True)
    hd = {'source': meta['source'] + '; HD 2x by AI upscaling (Real-ESRGAN realesr-animevideov3, x4 then area x0.5)',
          'scale_from_native': 2, 'gap_px': meta['gap_px'] * 2, 'animations': []}
    for a in meta['animations']:
        b = dict(a)
        b['frame_width'], b['frame_height'] = a['frame_width'] * 2, a['frame_height'] * 2
        b['pivot_px'] = [v * 2 for v in a['pivot_px']]
        b['rects_own_sheet'] = [[v * 2 for v in r] for r in a['rects_own_sheet']]
        b.pop('rects_master', None)
        hd['animations'].append(b)
    with open(os.path.join(OUT, 'Piggy_Spritesheet_HD2x.json'), 'w') as f:
        json.dump(hd, f, indent=1, ensure_ascii=False)

CHAR_ANIMS = ('IDLE', 'BLINK', 'RECEIVE_COINS', 'REWARD_JUMP', 'CELEBRATE', 'REACTION', 'MOVE', 'TELEPORT')


def write_frames():
    """The pig's frames cut from the HD sheets for the game (HD2x/frames/<Anim>_NN.png), padded at the right and the
    bottom to multiples of 4 (block compression); the pivot stays where it was (top-left origin)."""
    meta = json.load(open(os.path.join(OUT, 'Piggy_Spritesheet_HD2x.json')))
    d = os.path.join(OUT, 'frames')
    os.makedirs(d, exist_ok=True)
    for a in meta['animations']:
        if a['name'] not in CHAR_ANIMS:
            continue
        sheet = Image.open(os.path.join(OUT, a['file'])).convert('RGBA')
        W, H = a['frame_width'], a['frame_height']
        W4, H4 = (W + 3) // 4 * 4, (H + 3) // 4 * 4
        for i, (x, y, w, h) in enumerate(a['rects_own_sheet']):
            f = Image.new('RGBA', (W4, H4), (0, 0, 0, 0))
            f.paste(sheet.crop((x, y, x + w, y + h)), (0, 0))
            f.save(os.path.join(d, '%s_%02d.png' % (a['file'][:-4], i)), optimize=True)
        print('frames', a['name'], len(a['rects_own_sheet']), '%dx%d' % (W4, H4))


if __name__ == '__main__':
    if '--frames' in sys.argv:
        write_frames()
    else:
        main()
        write_frames()
