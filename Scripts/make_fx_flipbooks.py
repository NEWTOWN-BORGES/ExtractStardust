"""Renders the explosion and fire flipbooks in Blender (player, 2026-11-01: "melhore a explosão", "faça-o em Blender").

Procedural Cycles volumes (Mantaflow does not run in the pip bpy build, and noise-shaped volumes with blackbody fire are
enough for sprites seen at 400 km/h), one frame per cell, packed into atlases:
  SourceArt/FX/T_FX_Fireball.png  8 x 8, 64 frames: a white-hot core that swells, rolls and cools into dark smoke
  SourceArt/FX/T_FX_Smoke.png     8 x 8, 64 frames: a lit puff of smoke that billows out and thins (tinted in Unreal:
                                   black smoke, grey smoke, sand-coloured dust)
  SourceArt/FX/T_FX_Fire.png      4 x 4, 16 frames that loop: flames licking up (the burning wreck)
RGB is the colour already multiplied by its opacity (the light of the fire where it is thin, the lit colour of the
smoke), A the opacity: M_FX_Flipbook (Scripts/make_fx_assets.py) draws them with premultiplied alpha (AlphaComposite),
so thin fire still glows and smoke darkens what is behind it. Frame 0 is the top-left cell, row by row.
Also writes SourceArt/FX/preview_<name>.jpg (every frame over desert sand, for checking).

    python3 Scripts/make_fx_flipbooks.py [-- <out dir> [fireball smoke fire] [size=256] [samples=24]]
    blender -b -P Scripts/make_fx_flipbooks.py -- (same arguments)
Then Scripts/make_fx_assets.py imports them and makes the materials (casa_tudo.ps1, step 3d).
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
NAMES = ('fireball', 'smoke', 'fire')
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opts = dict(a.split('=', 1) for a in argv if '=' in a)
plain = [a for a in argv if '=' not in a]
OUT = next((a for a in plain if a not in NAMES), os.path.join(ROOT, 'SourceArt', 'FX'))
ONLY = [a for a in plain if a in NAMES] or list(NAMES)
SIZE = int(opts.get('size', 256))
SAMPLES = int(opts.get('samples', 24))
LIMIT = int(opts.get('frames', 0))      # >0: render only that many frames (quick look); the atlas is not written


# ---------------------------------------------------------------------------------------------------- scene
def reset(ortho):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = SAMPLES
    try:
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 2
    sc.cycles.volume_bounces = 0
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.volume_max_steps = 384
    sc.cycles.volume_biased = True        # ray-marched (the unbiased mode builds an octree of the noise first: 10x slower)
    sc.cycles.volume_step_rate = 1.0
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_mode = 'RGBA'
    w = bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.5, 0.5, 0.5, 1)          # a neutral fill, so the shadow side is not black
    bg.inputs['Strength'].default_value = 0.4
    sun_data = bpy.data.lights.new('Sun', 'SUN')
    sun_data.energy = 6.0
    sun_data.angle = math.radians(3)
    sun = bpy.data.objects.new('Sun', sun_data)
    sc.collection.objects.link(sun)
    sun.rotation_euler = Vector((0.7, 0.15, -0.7)).to_track_quat('-Z', 'Y').to_euler()   # from up and left: shaped, not flat
    cam_data = bpy.data.cameras.new('Cam')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = ortho
    cam = bpy.data.objects.new('Cam', cam_data)
    sc.collection.objects.link(cam)
    cam.location = (0.0, -10.0, 0.0)
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
    sc.camera = cam
    return sc


class Tree:
    """A small helper to wire shader nodes by name; frame values live in Value nodes changed between renders."""

    def __init__(self, mat):
        self.nt = mat.node_tree
        self.nt.nodes.clear()

    def node(self, kind, **inputs):
        n = self.nt.nodes.new(kind)
        for key, value in inputs.items():
            if key.startswith('_'):
                setattr(n, key[1:], value)
            else:
                n.inputs[key].default_value = value
        return n

    def link(self, a, b, out=0, inp=0):
        self.nt.links.new(a.outputs[out] if not isinstance(a, bpy.types.NodeSocket) else a,
                          b.inputs[inp] if not isinstance(b, bpy.types.NodeSocket) else b)
        return b

    def value(self, name, v=0.0):
        n = self.nt.nodes.new('ShaderNodeValue')
        n.name = name
        n.outputs[0].default_value = v
        return n

    def math(self, op, a, b=None, clamp=False):
        n = self.nt.nodes.new('ShaderNodeMath')
        n.operation = op
        n.use_clamp = clamp
        for k, src in enumerate((a, b)):
            if src is None:
                continue
            if isinstance(src, (int, float)):
                n.inputs[k].default_value = src
            else:
                self.link(src, n.inputs[k])
        return n

    def vmath(self, op, a, b=None, scale=None):
        n = self.nt.nodes.new('ShaderNodeVectorMath')
        n.operation = op
        for k, src in enumerate((a, b)):
            if src is None:
                continue
            if isinstance(src, (tuple, list)):
                n.inputs[k].default_value = src
            else:
                self.link(src, n.inputs[k])
        if scale is not None:
            if isinstance(scale, (int, float)):
                n.inputs['Scale'].default_value = scale
            else:
                self.link(scale, n.inputs['Scale'])
        return n

    def noise(self, vec, w, scale, detail, rough=0.55, distort=0.0):
        n = self.nt.nodes.new('ShaderNodeTexNoise')
        n.noise_dimensions = '4D'
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        n.inputs['Distortion'].default_value = distort
        self.link(vec, n.inputs['Vector'])
        if isinstance(w, (int, float)):
            n.inputs['W'].default_value = w
        else:
            self.link(w, n.inputs['W'])
        return n

    def remap(self, src, a, b, c=0.0, d=1.0, smooth=True):
        n = self.nt.nodes.new('ShaderNodeMapRange')
        if smooth:
            n.interpolation_type = 'SMOOTHSTEP'
        n.clamp = True
        for key, v in (('From Min', a), ('From Max', b), ('To Min', c), ('To Max', d)):
            if isinstance(v, (int, float)):
                n.inputs[key].default_value = v
            else:
                self.link(v, n.inputs[key])
        self.link(src, n.inputs['Value'])
        return n


def domain(half):
    bpy.ops.mesh.primitive_cube_add(size=2.0 * half, location=(0, 0, 0))
    o = bpy.context.object
    m = bpy.data.materials.new('Volume')
    m.use_nodes = True
    o.data.materials.append(m)
    return o, m


# ---------------------------------------------------------------------------------------------------- the effects
def billow_ball(smoke):
    """The fireball (smoke=False) or the smoke puff (smoke=True): a dense ball of big rolling billows whose outline is
    broken by lumps, the pattern swelling with the ball (coordinates divided by its radius) and churning in the 4th
    dimension. The fireball burns inside (blackbody: white-yellow at 3500 K down to dull red) and its outside is soot."""
    o, m = domain(1.3)
    T = Tree(m)
    out = T.node('ShaderNodeOutputMaterial')
    pv = T.node('ShaderNodeVolumePrincipled')
    T.link(pv, out, 0, 'Volume')
    R, W, rise, dens, lo, heat, fire = (T.value(n) for n in ('R', 'W', 'RISE', 'DENS', 'LO', 'HEAT', 'FIRE'))
    tc = T.node('ShaderNodeTexCoord')
    centre = T.node('ShaderNodeCombineXYZ')
    T.link(rise, centre, 0, 'Z')
    rel = T.vmath('SUBTRACT', tc.outputs['Object'], centre)
    inv = T.math('DIVIDE', 1.0, R)
    q = T.vmath('SCALE', rel, scale=inv)
    dist = T.vmath('LENGTH', q)
    lumps = T.noise(q, W, 1.0 if not smoke else 0.85, 2.0)
    lump = T.remap(lumps, 0.3, 0.7, -0.24 if not smoke else -0.3, 0.24 if not smoke else 0.3, smooth=False)
    d = T.math('ADD', dist.outputs['Value'], lump)
    shape = T.remap(d, 0.62, 1.0, 1.0, 0.0)
    bil = T.noise(q, T.math('MULTIPLY', W, 1.3), 2.0 if not smoke else 1.7, 5.0 if not smoke else 6.0, 0.55 if not smoke else 0.6,
                  0.15 if not smoke else 0.25)
    hi = T.math('ADD', lo, 0.2)
    sub = T.remap(bil, lo, hi)
    dm = T.math('MULTIPLY', T.math('MULTIPLY', sub, shape), dens)
    pv.inputs['Color'].default_value = (0.75, 0.75, 0.75, 1) if smoke else (0.14, 0.12, 0.1, 1)
    pv.inputs['Anisotropy'].default_value = 0.2
    if smoke:
        T.link(dm, pv, 0, 'Density')
    else:
        hot = T.noise(q, T.math('MULTIPLY', W, 1.7), 3.2, 4.0)
        core = T.remap(d, 0.2, 0.92, 1.0, 0.0)
        hn = T.remap(hot, 0.28, 0.7)
        spot = T.math('MULTIPLY', core, hn)
        # burning gas is thinner than soot: the hot pockets let the fire through
        thin = T.math('SUBTRACT', 1.0, T.math('MULTIPLY', T.math('MULTIPLY', spot, fire), 0.65))
        T.link(T.math('MULTIPLY', dm, thin), pv, 0, 'Density')
        temp = T.math('ADD', T.math('MULTIPLY', T.math('MULTIPLY', spot, heat, clamp=True), 2900.0), 600.0)
        T.link(temp, pv, 0, 'Temperature')
        # the light of a blackbody falls as T^4; soften that to ~T^1.5 so the fire reads while it cools, and put it
        # out with FIRE so the last third is smoke
        soften = T.math('POWER', T.math('DIVIDE', 3500.0, temp), 2.5)
        glow = T.math('MULTIPLY', T.math('MULTIPLY', T.math('MULTIPLY', spot, sub), soften), fire)
        T.link(T.math('MULTIPLY', glow, 20.0), pv, 0, 'Blackbody Intensity')
    return T


def fireball_frame(T, k, n):
    t = k / (n - 1.0)
    swell = (1.0 - math.exp(-6.0 * t)) / (1.0 - math.exp(-6.0))
    out = max(0.0, min(1.0, 1.0 - (t - 0.22) / 0.5)) ** 1.5      # the fire dies between 22 % and 72 % of the life
    set_values(T, R=0.62 + 0.4 * swell, W=1.6 * t, RISE=0.1 * t * t, DENS=30.0 * (1.0 - 0.75 * t ** 1.3),
               LO=0.32 + 0.12 * t, HEAT=math.exp(-1.5 * t) * (1.0 if t > 0.04 else 1.3), FIRE=out)


def smoke_frame(T, k, n):
    t = k / (n - 1.0)
    swell = (1.0 - math.exp(-3.5 * t)) / (1.0 - math.exp(-3.5))
    set_values(T, R=0.55 + 0.45 * swell, W=1.2 * t, RISE=0.08 * t, DENS=20.0 * (1.0 - 0.8 * t ** 1.3), LO=0.3 + 0.16 * t,
               HEAT=0.0, FIRE=0.0)


def flames():
    """Flames licking up from a base: a narrowing column of tongues, the turbulence carried upwards, hottest low in the
    middle. Mostly light, very little smoke (the wreck sends its own smoke puffs)."""
    o, m = domain(1.0)
    T = Tree(m)
    out = T.node('ShaderNodeOutputMaterial')
    pv = T.node('ShaderNodeVolumePrincipled')
    T.link(pv, out, 0, 'Volume')
    up, W = T.value('UP'), T.value('W')
    tc = T.node('ShaderNodeTexCoord')
    sep = T.node('ShaderNodeSeparateXYZ')
    T.link(tc.outputs['Object'], sep.inputs[0])
    zn = T.remap(sep.outputs['Z'], -0.85, 0.95, 0.0, 1.0, smooth=False)
    radius = T.math('MULTIPLY', T.math('POWER', T.math('SUBTRACT', 1.0, zn), 0.45), 0.72)
    xy = T.node('ShaderNodeCombineXYZ')
    T.link(sep.outputs['X'], xy.inputs['X'])
    T.link(sep.outputs['Y'], xy.inputs['Y'])
    rad = T.math('DIVIDE', T.vmath('LENGTH', xy).outputs['Value'], T.math('ADD', radius, 0.02))
    # the turbulence rises: sample it lower and lower as time goes, stretched upwards
    shift = T.node('ShaderNodeCombineXYZ')
    T.link(up, shift.inputs['Z'])
    pos = T.vmath('SUBTRACT', T.vmath('MULTIPLY', tc.outputs['Object'], (1.0, 1.0, 0.62)), shift)
    lick = T.noise(pos, W, 3.0, 6.0, 0.62, 1.2)
    wob = T.remap(lick, 0.3, 0.7, -0.6, 0.6, smooth=False)
    shape = T.remap(T.math('ADD', rad, wob), 1.05, 0.45)
    base = T.remap(zn, 0.0, 0.08)
    body = T.math('MULTIPLY', T.math('MULTIPLY', shape, base), T.remap(lick, 0.42, 0.56))
    T.link(T.math('MULTIPLY', body, 0.7), pv, 0, 'Density')
    pv.inputs['Color'].default_value = (0.05, 0.045, 0.04, 1)
    tn = T.math('MULTIPLY', body, T.math('POWER', T.math('SUBTRACT', 1.0, zn), 0.8), clamp=True)
    T.link(T.math('ADD', T.math('MULTIPLY', tn, 2600.0), 800.0), pv, 0, 'Temperature')
    T.link(T.math('MULTIPLY', tn, 18.0), pv, 0, 'Blackbody Intensity')
    return T


def fire_frame(T, k, n):
    tau = k / 16.0                                             # seconds, 16 frames a second as EXWreck plays them
    set_values(T, UP=2.3 * tau, W=0.9 * tau)


def set_values(T, **values):
    for name, v in values.items():
        T.nt.nodes[name].outputs[0].default_value = v


# ---------------------------------------------------------------------------------------------------- render and pack
def render(sc, path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    a = np.empty(SIZE * SIZE * 4, np.float32)
    img.pixels.foreach_get(a)                                  # premultiplied, scene linear (checked: EXR loads PREMUL)
    bpy.data.images.remove(img)
    os.remove(path)
    return a.reshape(SIZE, SIZE, 4)[::-1].copy()               # top row first


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def knee(x, start=0.8):
    over = np.maximum(x - start, 0.0)
    return np.minimum(x, start) + (1.0 - start) * (1.0 - np.exp(-over / (1.0 - start)))


def save(path, rgba, fmt):
    """Writes an 8-bit image from top-row-first float data (already encoded), through Blender (no PIL needed)."""
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=(fmt == 'PNG'))
    img.alpha_mode = 'STRAIGHT'                                # write the values as they are (they are premultiplied)
    img.pixels.foreach_set(np.ascontiguousarray(rgba[::-1], dtype=np.float32).ravel())
    img.filepath_raw = path
    img.file_format = fmt
    img.save()
    bpy.data.images.remove(img)


def pack(name, frames, cols, scale, kind=None):
    rows = len(frames) // cols
    atlas = np.zeros((rows * SIZE, cols * SIZE, 4), np.float32)
    for k, f in enumerate(frames):
        r, c = divmod(k, cols)
        atlas[r * SIZE:(r + 1) * SIZE, c * SIZE:(c + 1) * SIZE] = f
    rgb = knee(atlas[..., :3] / scale)
    out = np.dstack([srgb(rgb), np.clip(atlas[..., 3:], 0.0, 1.0)])
    save(os.path.join(OUT, 'T_FX_%s.png' % name.capitalize()), out, 'PNG')
    # preview: each frame over sunlit sand, the fire at the strength the game gives it
    gain = {'fireball': 6.0, 'smoke': 0.35, 'fire': 7.0}[kind or name]           # as the game shows them
    sand = np.array([0.52, 0.33, 0.2], np.float32)
    shown = rgb * gain + sand * (1.0 - atlas[..., 3:])
    save(os.path.join(OUT, 'preview_%s.jpg' % name), np.dstack([srgb(knee(shown, 0.7)), np.ones(shown.shape[:2])]), 'JPEG')
    print('FX %s %dx%d frames -> T_FX_%s.png (scale %.3g)' % (name, cols, rows, name.capitalize(), scale))


def make(name):
    if name == 'fire':
        sc = reset(2.0)
        T = flames()
        total, step, cols = 32, fire_frame, 4                  # 32 continuous frames, cross-faded into a 16-frame loop
    else:
        sc = reset(2.6)
        T = billow_ball(smoke=(name == 'smoke'))
        total, step, cols = 64, fireball_frame if name == 'fireball' else smoke_frame, 8
    frames = []
    # a quick look renders a few frames spread over the whole life
    ks = sorted(set(int(round(x)) for x in np.linspace(0, total - 1, LIMIT))) if LIMIT else list(range(total))
    count = len(ks)
    tmp = os.path.join(OUT, '_fx_frame.exr')
    for i, k in enumerate(ks):
        step(T, k, total)
        frames.append(render(sc, tmp))
        print('FX %s frame %d/%d' % (name, i + 1, count), flush=True)
    if LIMIT:
        cols_q = min(count, 8)
        while count % cols_q:
            cols_q -= 1
        peak = max(float(np.percentile(f[..., :3].max(axis=2), 99.7)) for f in frames) or 1.0
        pack(name + '_test', frames, cols_q, peak, kind=name)
        return
    if name == 'fire':
        n = 16
        # loop: frame i shows (1 - i/n) of the frame n later and i/n of its own; frame n-1 then runs into frame 0
        frames = [(1.0 - i / n) * frames[i + n] + (i / n) * frames[i] for i in range(n)]
    # one brightness for the whole atlas, so the cooling stays visible: the brightest 0.3 % of the fire is 1.0
    peak = max(float(np.percentile(f[..., :3].max(axis=2), 99.7)) for f in frames)
    pack(name, frames, cols, peak if peak > 0 else 1.0)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name in ONLY:
        make(name)
