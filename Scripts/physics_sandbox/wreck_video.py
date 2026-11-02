"""A video of a ship blowing up as the game will show it (player, 2026-11-01: "peças em bolas de fogo", "ver a mexer").
The same numbers and flipbooks as the game, so it previews it:
  - the crash camera (AEXHoverCraft::UpdateCrashCam): slow motion 0.3x for 1.6 s of real time, back to speed over 0.8 s,
    the camera going round the hull from behind (-115 deg) to the front (+20 deg), 15 m out and 4.5 m up;
  - the explosion (AEXExplosion::Ignite): white core, 5 fireballs, the second burst, the dust ring, the shock ring,
    burning debris, sparks and the smoke;
  - the wreck (AEXWreck): the charred VORTEX hull and modules on wreck.py's physics, each burning like a ball of fire
    (flames on it and a trail of fire behind it that turns to smoke), the hull's column of smoke, and dust, sparks and a
    lick of fire where they strike.
The sprites are camera-facing squares of the flipbooks (SourceArt/FX, Scripts/make_fx_flipbooks.py), blended as
M_FX_Flipbook does: premultiplied, their light added and what is behind dimmed by their opacity.
    python3 Scripts/physics_sandbox/wreck_video.py -- <out dir> [causes] [size=960x540] [samples=20] [seconds=4.5] [fps=24]
Writes <out>/wreck_<cause>.mp4 (ffmpeg), <out>/wreck_<cause>.gif (small, for a quick look) and <out>/wreck_<cause>_still.jpg.
"""
import math
import os
import shutil
import subprocess
import sys

import bpy  # noqa: I001  (bpy first: it puts mathutils on the path)
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wreck  # noqa: E402
import wreck_sims as sims  # noqa: E402  (the VORTEX parts, the charred material, the textured ground)

ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
OPTS = dict(a.split('=', 1) for a in ARGS if '=' in a)
PLAIN = [a for a in ARGS if '=' not in a]
OUT = PLAIN[0]
CAUSES = PLAIN[1:] or list(wreck.CAUSES)
WIDTH, HEIGHT = (int(x) for x in OPTS.get('size', '960x540').split('x'))
SAMPLES = int(OPTS.get('samples', 20))
SECONDS = float(OPTS.get('seconds', 4.5))
FPS = int(OPTS.get('fps', 24))
TEST = OPTS.get('test') == '1'           # a few frames on one sheet instead of the video (a quick look)
G_DEBRIS = 14.7                           # AEXExplosion's gravity for debris and sparks (m/s^2)
CANDELA_TO_W = 0.4 * 4.0 * math.pi        # the game's sun is 10 lux, this scene's sun 4 W/m^2: 1 cd ~ 5 W of point light


# ---------------------------------------------------------------------------------------------------- time
def game_time(real):
    """UpdateCrashCam: 0.3x until 1.6 s of real time, then back to 1x by 2.4 s."""
    if real <= 1.6:
        return 0.3 * real
    if real <= 2.4:
        x = real - 1.6
        return 0.48 + 0.3 * x + 0.7 * x * x / 1.6
    return 1.0 + (real - 2.4)


def dilation(real):
    return 0.3 if real < 1.6 else min(1.0, 0.3 + 0.7 * (real - 1.6) / 0.8)


# ---------------------------------------------------------------------------------------------------- the effects (as the game)
class Rng:
    def __init__(self, seed):
        self.r = np.random.default_rng(seed)

    def u(self, a, b):
        return float(self.r.uniform(a, b))

    def vrand(self):
        v = self.r.normal(size=3)
        return v / max(np.linalg.norm(v), 1e-9)


def sprite(kind, pos, vel, delay, life, size, end, inten, smoke, tint=(1.0, 1.0, 1.0), rises=False, start=0.0):
    """An AEXExplosion::AddSprite (cm -> m), born at game time start."""
    return dict(kind=kind, p=np.asarray(pos, float), v=np.asarray(vel, float), t0=start + delay, life=life, size=size,
                end=end, inten=inten, smoke=smoke, tint=tint, rises=rises, rot=float(np.random.default_rng(int(start * 1e4 + delay * 1e6 + size * 1e3)).uniform(-0.4, 0.4)))


def sprite_state(s, t):
    local = t - s['t0']
    if local < 0.0 or local >= s['life']:
        return None
    T = local / s['life']
    k = 1.1 if s['smoke'] else 2.2
    e = math.exp(-k * local)
    p = s['p'] + s['v'] * (1.0 - e) / k
    if s['rises'] and local > 0.4:
        r = local - 0.4
        p = p + np.array([0.0, 0.0, 2.6 / k * (r - (1.0 - math.exp(-k * r)) / k)])
    if s['smoke']:
        size = s['size'] + (s['end'] - s['size']) * math.sqrt(T)
        glow, opac = 1.0, s['inten'] * min(1.0, local / 0.3) * (1.0 - T) ** 2
    else:
        size = s['size'] + (s['end'] - s['size']) * (1.0 - math.exp(-local * 5.0))
        glow, opac = s['inten'] * (1.0 - 0.6 * T), max(0.0, min(1.0, 1.4 - 1.4 * T))
    return (s['kind'], p, size, min(T * 64.0, 63.0), glow, opac, s['tint'], s['rot'])


def glow_bit(shape, pos, vel, life, size, end, inten, colour, start, gravity=0.0, damp=0.0, spin=None, grow='exp7'):
    return dict(shape=shape, p=np.asarray(pos, float), v=np.asarray(vel, float), t0=start, life=life, size=size, end=end,
                inten=inten, colour=colour, g=gravity, damp=damp, spin=spin, grow=grow)


def bit_state(b, t):
    age = t - b['t0']
    if age < 0.0 or age >= b['life']:
        return None
    T = age / b['life']
    p, v = b['p'], b['v']
    if b['damp'] > 0.0:
        k = b['damp']
        e = math.exp(-k * age)
        # dv/dt = -k v - g z: closed form
        vz_inf = -b['g'] / k
        p = p + np.array([v[0] * (1 - e) / k, v[1] * (1 - e) / k, vz_inf * age + (v[2] - vz_inf) * (1 - e) / k])
        vel = np.array([v[0] * e, v[1] * e, vz_inf + (v[2] - vz_inf) * e])
    else:
        vel = v
    if b['grow'] == 'exp7':
        size = b['size'] + (b['end'] - b['size']) * (1.0 - math.exp(-age * 7.0))
    elif b['grow'] == 'sqrt':
        size = b['size'] + (b['end'] - b['size']) * math.sqrt(T)
    else:
        size = b['size'] + (b['end'] - b['size']) * T
    if b['shape'] == 'core':
        inten = b['inten'] * (1.0 - T) ** 2
    elif b['shape'] == 'debris':
        inten = max(0.15, b['inten'] * math.exp(-T * 3.0))
    else:
        inten = b['inten'] * (1.0 - T)
    return (b['shape'], p, vel, size, inten, b['colour'], age)


def ignite(origin, craft_v, rng):
    """AEXExplosion::Ignite with the flipbooks."""
    speed = float(np.linalg.norm(craft_v))
    scale = min(1.3, max(0.7, 0.7 + speed / 200.0))
    scale = min(1.5, max(0.3, scale))
    drift = craft_v * 0.45
    sprites, bits = [], []
    for i in range(5):
        off = np.zeros(3) if i == 0 else rng.vrand() * np.array([1.0, 1.0, 0.5]) * rng.u(1.5, 3.2) * scale
        sprites.append(sprite('fireball', origin + off + [0, 0, 1.2], drift * 0.4 + off * 1.5, i * 0.04, rng.u(1.6, 2.2),
                              3.0 * scale, rng.u(11.0, 16.0) * scale, rng.u(6.0, 9.0), False, rises=True))
    for i in range(2):
        side = np.array([rng.u(-1, 1), rng.u(-1, 1), 0.2])
        side = side / np.linalg.norm(side) * 4.2 * scale
        sprites.append(sprite('fireball', origin + side + [0, 0, 1.5], drift * 0.3 + side, 0.32 + i * 0.05, 1.6, 2.0 * scale,
                              8.5 * scale, 7.0, False, rises=True))
    for i in range(8):
        off = rng.vrand() * np.array([1.0, 1.0, 0.3]) * rng.u(1.0, 4.5) * scale
        sprites.append(sprite('smoke', origin + off + [0, 0, 2.5], drift * 0.25 + off * 0.5 + [0, 0, rng.u(2.5, 4.2)],
                              rng.u(0.25, 0.6), rng.u(4.0, 5.5), 7.0 * scale, rng.u(18.0, 27.0) * scale, rng.u(0.65, 0.85), True,
                              tint=(0.22, 0.2, 0.19)))
    for i in range(10):
        a = 2.0 * math.pi * i / 10.0 + rng.u(-0.2, 0.2)
        out = np.array([math.cos(a), math.sin(a), 0.0])
        sprites.append(sprite('smoke', origin + out * 2.0 - [0, 0, 0.6], drift * 0.2 + out * rng.u(18.0, 26.0) * scale, 0.05,
                              rng.u(1.6, 2.2), 3.5 * scale, 10.0 * scale, 0.55, True, tint=(1.4, 1.0, 0.68)))
    # the white-hot heart (with the flipbooks only this layer of the old fireball is kept), the shock ring
    bits.append(glow_bit('core', origin, np.zeros(3), 0.2, 0.6, 4.0 * scale, 30.0, (1.0, 0.92, 0.7), 0.0))
    bits.append(glow_bit('ring', origin - [0, 0, 1.2], np.zeros(3), 0.55, 1.0, 46.0 * scale, 9.0, (1.0, 0.6, 0.25), 0.0, grow='sqrt'))
    for i in range(18):
        out = rng.vrand() + np.array([0.0, 0.0, 0.9])
        out = out / np.linalg.norm(out)
        size = rng.u(0.25, 0.8)
        bits.append(glow_bit('debris', origin + out * 1.5, drift * 1.2 + out * rng.u(15.0, 42.0) * scale, rng.u(1.6, 2.8), size, size,
                             rng.u(6.0, 14.0), (1.0, 0.4, 0.1), 0.0, G_DEBRIS, 0.6, spin=rng.vrand() * rng.u(4.0, 12.0), grow='none'))
    bits += sparks(60, origin, drift, scale, 1.0, 1.0, 0.0, rng)
    flashes = [(0.0, 6000.0 * scale, 5.0, origin), (0.32, 3500.0 * scale, 6.0, origin)]
    return sprites, bits, flashes, scale


def sparks(count, origin, drift, scale, speed, size, start, rng):
    out = []
    for _ in range(count):
        s = rng.u(0.08, 0.16) * size
        vel = drift + rng.vrand() * rng.u(30.0, 75.0) * scale * speed + np.array([0.0, 0.0, 12.0 * speed])
        out.append(glow_bit('spark', origin, vel, rng.u(0.4, 1.1), s, s * 0.3, 40.0, (1.0, 0.75, 0.35), start, G_DEBRIS, 1.5,
                            grow='lin'))
    return out


def ignite_impact(point, vel_m, strength, hot, start, rng):
    """AEXExplosion::IgniteImpact: dust, a lick of fire while the hull is hot, sparks, a small flash."""
    scale = min(1.0, max(0.25, strength))
    drift = vel_m
    sprites = []
    for i in range(3):
        off = rng.vrand() * np.array([1.0, 1.0, 0.2]) * 0.8
        sprites.append(sprite('smoke', point + off + [0, 0, 0.6], drift * 0.5 + off * 3.0 + [0, 0, 2.0], i * 0.03, rng.u(1.4, 2.0),
                              1.5 * scale, 6.0 * scale, 0.6, True, tint=(1.4, 1.0, 0.68), start=start))
    if hot:
        sprites.append(sprite('fireball', point + [0, 0, 0.8], drift * 0.6, 0.0, 0.9, 1.2 * scale, 3.8 * scale, 5.0, False,
                              rises=True, start=start))
    bits = sparks(int(round(10 + 14 * scale)), point, drift, scale, 0.45, 0.8, start, rng)
    flash = (start, 6000.0 * scale * (0.25 if hot else 0.08), 5.0, point)
    return sprites, bits, flash


# ---------------------------------------------------------------------------------------------------- the wreck (as AEXWreck)
def wreck_events(pieces, sizes, seconds, rng):
    """Runs AEXWreck's burning on the simulated tracks: each piece's heat, its tongues of flame (a pool of 140), the
    smoke from every burning piece (a pool of 120) and the strikes (bursts), at the physics' 1/120 s."""
    dt = wreck.DT
    steps = min(len(p.track) for p in pieces)
    burn = [11.0] + [rng.u(4.5, 7.0) for _ in pieces[1:]]
    gap = [0.0] * len(pieces)
    wait = [0.0] * len(pieces)
    puff_timer = [0.0] * len(pieces)
    trails, puffs = [], []

    def take(pool, cap, t):
        alive = [e for e in pool if e['t0'] + e['life'] > t]
        if len(alive) >= cap:
            oldest = max(alive, key=lambda e: (t - e['t0']) / e['life'])
            oldest['life'] = t - oldest['t0']

    for k in range(1, steps):
        t = k * dt
        for i, pc in enumerate(pieces):
            p0, p1 = pc.track[k - 1][1], pc.track[k][1]
            vel = (p1 - p0) / dt
            speed = float(np.linalg.norm(vel))
            heat = max(0.0, 1.0 - t / burn[i])
            stream = np.array([0.0, 0.0, 4.0]) - vel
            stream = stream / max(np.linalg.norm(stream), 1e-6)
            gap[i] += speed * dt
            wait[i] -= dt
            if heat > 0.12 and speed > 4.0 and gap[i] >= max(0.45, 0.2 * sizes[i]) and wait[i] <= 0.0:
                take(trails, 140, t)
                s0 = min(8.0, max(1.1 * sizes[i], 2.5 * gap[i])) * rng.u(0.85, 1.15)
                trails.append(dict(t0=t, p=p1 + rng.vrand() * 0.12 * sizes[i], v=vel * 0.12 + rng.vrand() * 0.6, stream=stream,
                                   life=0.45 * rng.u(0.8, 1.2) * (0.7 + 0.3 * heat), s0=s0, s1=s0 * 1.3, glow=3.5 * heat,
                                   shift=rng.u(0.0, 16.0)))
                gap[i] = 0.0
                wait[i] = 1.0 / (60.0 if i == 0 else 40.0)
            puff_timer[i] -= dt
            if heat > 0.05 and puff_timer[i] <= 0.0:
                hull = i == 0
                puff_timer[i] = (0.16 + (0.06 - 0.16) * heat) if hull else (0.2 + (0.08 - 0.2) * heat)
                take(puffs, 120, t)
                sz = sizes[i]
                puffs.append(dict(t0=t, p=p1 + np.array([rng.u(-0.1, 0.1) * sz, rng.u(-0.1, 0.1) * sz, 0.2 * sz]),
                                  life=rng.u(2.2, 3.0) if hull else rng.u(1.6, 2.4), s0=2.2 if hull else max(1.0, 0.8 * sz),
                                  s1=9.5 if hull else min(7.0, max(3.0, 2.5 * sz)), rot=rng.u(-0.6, 0.6)))
    # the strikes: each piece at most every 0.08 s, the wreck at most every 0.1 s, a module only above 9 m/s
    hits = []
    for i, pc in enumerate(pieces):
        last = -1.0
        for (t, c, vn) in pc.hits:
            if t - last >= 0.08:
                hits.append((t, i, c, vn))
                last = t
    hits.sort(key=lambda h: h[0])
    sprites, bits, flashes = [], [], []
    last = -1.0
    for (t, i, c, vn) in hits:
        if t > seconds or t - last < 0.1 or (i != 0 and vn < 9.0):
            continue
        last = t
        k = min(int(t / dt), steps - 1)
        hull_v = (pieces[0].track[k][1] - pieces[0].track[max(0, k - 1)][1]) / dt
        s, b, f = ignite_impact(np.asarray(c, float), hull_v * 0.3, min(1.0, max(0.25, vn / 20.0)), i == 0 and t < 3.0, t, rng)
        sprites += s
        bits += b
        flashes.append(f)
    return burn, trails, puffs, sprites, bits, flashes


def trail_state(tr, t, cam_right, cam_up):
    """A tongue of flame: drifting and slowing, rising a little, its flames along its stream (turned on screen)."""
    age = t - tr['t0']
    if age < 0.0 or age >= tr['life']:
        return None
    T = age / tr['life']
    e = math.exp(-2.0 * age)
    p = tr['p'] + tr['v'] * (1.0 - e) / 2.0 + np.array([0.0, 0.0, 1.0 / 2.0 * (age - (1.0 - e) / 2.0)])
    size = tr['s0'] + (tr['s1'] - tr['s0']) * T
    angle = math.atan2(float(np.dot(tr['stream'], cam_right)), float(np.dot(tr['stream'], cam_up)))
    return ('fire', p + tr['stream'] * 0.33 * size, size, (tr['shift'] + age * 16.0) % 16.0, tr['glow'] * (1.0 - T),
            (1.0 - T) ** 1.5 * min(1.0, age / 0.03), (1.0, 1.0, 1.0), angle)


def puff_state(pf, t):
    age = t - pf['t0']
    if age < 0.0 or age >= pf['life']:
        return None
    T = age / pf['life']
    p = pf['p'] + np.array([0.0, 0.0, 1.6 * age])
    return ('smoke', p, pf['s0'] + (pf['s1'] - pf['s0']) * math.sqrt(T), T * 63.0, 1.0, 0.7 * min(1.0, age / 0.2) * (1.0 - T) ** 2,
            (0.32, 0.3, 0.29), pf['rot'])


def sprite_material(name, path, cols):
    """M_FX_Flipbook in Cycles: two frames of the atlas blended, premultiplied (light added, behind dimmed by opacity).
    Per object: frame, glow (Intensity), opac (Opacity), tint (Color)."""
    img = bpy.data.images.load(path)
    img.alpha_mode = 'CHANNEL_PACKED'
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    L = nt.links.new

    def attr(n):
        a = N('ShaderNodeAttribute')
        a.attribute_type = 'OBJECT'
        a.attribute_name = n
        return a

    def math_(op, a, b=None):
        n = N('ShaderNodeMath')
        n.operation = op
        for k, src in enumerate((a, b)):
            if src is None:
                continue
            if isinstance(src, (int, float)):
                n.inputs[k].default_value = src
            else:
                L(src, n.inputs[k])
        return n.outputs[0]

    out = N('ShaderNodeOutputMaterial')
    uv = N('ShaderNodeTexCoord')
    sep0 = N('ShaderNodeSeparateXYZ')
    L(uv.outputs['UV'], sep0.inputs[0])
    # turned clockwise on screen by 'rot' round the middle (as M_FX_Flipbook); outside the picture is empty
    rot = attr('rot').outputs['Fac']
    cs, sn = math_('COSINE', rot), math_('SINE', rot)
    dx, dy = math_('SUBTRACT', sep0.outputs['X'], 0.5), math_('SUBTRACT', sep0.outputs['Y'], 0.5)
    rx = math_('ADD', math_('SUBTRACT', math_('MULTIPLY', dx, cs), math_('MULTIPLY', dy, sn)), 0.5)
    ry = math_('ADD', math_('ADD', math_('MULTIPLY', dx, sn), math_('MULTIPLY', dy, cs)), 0.5)
    edge = math_('MINIMUM', math_('MINIMUM', rx, math_('SUBTRACT', 1.0, rx)), math_('MINIMUM', ry, math_('SUBTRACT', 1.0, ry)))
    fade = N('ShaderNodeMapRange')
    fade.interpolation_type = 'SMOOTHSTEP'
    fade.clamp = True
    fade.inputs['From Min'].default_value = 0.0
    fade.inputs['From Max'].default_value = 0.06
    L(edge, fade.inputs['Value'])
    inside = fade.outputs['Result']
    sep = N('ShaderNodeCombineXYZ')
    L(math_('MINIMUM', math_('MAXIMUM', rx, 0.0), 1.0), sep.inputs['X'])
    L(math_('MINIMUM', math_('MAXIMUM', ry, 0.0), 1.0), sep.inputs['Y'])
    rsep = N('ShaderNodeSeparateXYZ')
    L(sep.outputs[0], rsep.inputs[0])
    sep = rsep
    n = float(cols * cols)
    f = math_('MINIMUM', math_('MAXIMUM', attr('frame').outputs['Fac'], 0.0), n - 1.0)
    f0 = math_('FLOOR', f)
    f1 = math_('MINIMUM', math_('ADD', f0, 1.0), n - 1.0)
    k = math_('SUBTRACT', f, f0)
    samples = []
    for fi in (f0, f1):
        col = math_('SUBTRACT', fi, math_('MULTIPLY', math_('FLOOR', math_('DIVIDE', fi, float(cols))), float(cols)))
        row = math_('FLOOR', math_('DIVIDE', fi, float(cols)))
        u = math_('DIVIDE', math_('ADD', sep.outputs['X'], col), float(cols))
        v = math_('DIVIDE', math_('ADD', sep.outputs['Y'], math_('SUBTRACT', float(cols - 1), row)), float(cols))
        comb = N('ShaderNodeCombineXYZ')
        L(u, comb.inputs['X'])
        L(v, comb.inputs['Y'])
        tex = N('ShaderNodeTexImage')
        tex.image = img
        tex.extension = 'CLIP'
        L(comb.outputs[0], tex.inputs['Vector'])
        samples.append(tex)
    mixc = N('ShaderNodeMix')
    mixc.data_type = 'RGBA'
    L(k, mixc.inputs['Factor'])
    L(samples[0].outputs['Color'], mixc.inputs[6])
    L(samples[1].outputs['Color'], mixc.inputs[7])
    alpha = math_('ADD', math_('MULTIPLY', samples[0].outputs['Alpha'], math_('SUBTRACT', 1.0, k)),
                  math_('MULTIPLY', samples[1].outputs['Alpha'], k))
    opac = math_('MULTIPLY', attr('opac').outputs['Fac'], inside)
    a = math_('MINIMUM', math_('MULTIPLY', alpha, opac), 1.0)
    # emission = rgb * tint * glow * opac
    tinted = N('ShaderNodeMix')
    tinted.data_type = 'RGBA'
    tinted.blend_type = 'MULTIPLY'
    tinted.inputs['Factor'].default_value = 1.0
    L(mixc.outputs[2], tinted.inputs[6])
    L(attr('tint').outputs['Color'], tinted.inputs[7])
    strength = math_('MULTIPLY', attr('glow').outputs['Fac'], opac)
    em = N('ShaderNodeEmission')
    L(tinted.outputs[2], em.inputs['Color'])
    L(strength, em.inputs['Strength'])
    tr = N('ShaderNodeBsdfTransparent')
    inv = math_('SUBTRACT', 1.0, a)
    grey = N('ShaderNodeCombineColor')
    for ch in ('Red', 'Green', 'Blue'):
        L(inv, grey.inputs[ch])
    L(grey.outputs[0], tr.inputs['Color'])
    add = N('ShaderNodeAddShader')
    L(tr.outputs[0], add.inputs[0])
    L(em.outputs[0], add.inputs[1])
    L(add.outputs[0], out.inputs['Surface'])
    set_no_light(m)
    return m


def set_no_light(m):
    # hundreds of glowing sprites as light sources make every frame slow and noisy: the point lights do the fire's light
    for owner in (m, getattr(m, 'cycles', None)):
        if owner is not None and hasattr(owner, 'emission_sampling'):
            owner.emission_sampling = 'NONE'


def glow_material():
    """M_FX_Glow as an additive glow: per object colour and strength, soft towards the edges."""
    m = bpy.data.materials.new('Glow')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    col = nt.nodes.new('ShaderNodeAttribute')
    col.attribute_type = 'OBJECT'
    col.attribute_name = 'colour'
    st = nt.nodes.new('ShaderNodeAttribute')
    st.attribute_type = 'OBJECT'
    st.attribute_name = 'inten'
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.5
    soft = nt.nodes.new('ShaderNodeMath')
    soft.operation = 'MULTIPLY'
    inv = nt.nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs['Facing'], inv.inputs[1])
    nt.links.new(inv.outputs[0], soft.inputs[0])
    nt.links.new(st.outputs['Fac'], soft.inputs[1])
    nt.links.new(col.outputs['Color'], em.inputs['Color'])
    nt.links.new(soft.outputs[0], em.inputs['Strength'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs['Surface'])
    set_no_light(m)
    return m


def pool(n, maker, name):
    objs = []
    for k in range(n):
        o = maker()
        o.name = '%s%03d' % (name, k)
        o.hide_render = True
        o.visible_shadow = False
        o.visible_diffuse = False
        o.visible_glossy = False
        o.visible_transmission = False
        o.visible_volume_scatter = False
        objs.append(o)
    return objs


def plane():
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    return bpy.context.object


def sphere():
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, segments=16, ring_count=8)
    return bpy.context.object


def ring():
    bpy.ops.mesh.primitive_torus_add(major_radius=0.5, minor_radius=0.012, major_segments=64, minor_segments=8)
    return bpy.context.object


def cube():
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    return bpy.context.object


def render_cause(cause, objs):
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.name.startswith(('G_', 'S_', 'V_', 'W_', 'Cam', 'Sun', 'P_', 'F_', 'L_')):
            bpy.data.objects.remove(o, do_unlink=True)
    rng = Rng(11)
    layout = [(n, tuple(max(0.05, x) for x in h), m, c) for n, o, m, c, h in objs]
    pieces = wreck.simulate(wreck.start(cause, layout), SECONDS, wreck.planes_for(cause))
    sizes = [2.0 * max(h) for _, h, _, _ in layout]
    tg_end = game_time(SECONDS)
    origin = pieces[0].track[0][1].copy()
    c = wreck.CAUSES[cause]
    hull_v0 = (pieces[0].track[1][1] - pieces[0].track[0][1]) / wreck.DT
    craft_v = hull_v0 - np.array([0.0, 0.0, c['kick'][2]])        # the blast's kick up is the wreck's, not the craft's
    exp_sprites, exp_bits, flashes, _ = ignite(origin, craft_v, rng)
    burn, trails, puffs, hit_sprites, hit_bits, hit_flashes = wreck_events(pieces, sizes, tg_end, rng)
    sprites = exp_sprites + hit_sprites
    bits = exp_bits + hit_bits
    flashes = flashes + hit_flashes
    phases = [rng.u(0.0, 16.0) for _ in pieces]

    # the stage: sand, the rock wall if it hit one, the sun and the sky
    sand = sims.texture_mat('G_Sand', 'SourceArt/Desert/T_Sand_D.png', 0.08, (1.0, 0.8, 0.62, 1))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    g = bpy.context.object
    g.name = 'G_Ground'
    g.scale = (1400, 500, 1)
    g.data.materials.append(sand)
    wall_x = None
    if c.get('wall'):
        wall_x = 1.0
        rock = sims.texture_mat('G_Rock', 'SourceArt/Desert/T_Rock_D.png', 0.05, (0.95, 0.55, 0.38, 1))
        bpy.ops.mesh.primitive_cube_add(location=(wall_x + 6.0, 0, 9.0))
        w = bpy.context.object
        w.name = 'G_Wall'
        w.scale = (6.0, 34.0, 9.0)
        w.data.materials.append(rock)
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 4.0
    sun.angle = math.radians(1.5)
    so = bpy.data.objects.new('Sun', sun)
    sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(55), 0, math.radians(35))
    world = bpy.data.worlds.new('W')
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.62, 0.78, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 2
    sc.cycles.transparent_max_bounces = 128
    sc.render.resolution_x, sc.render.resolution_y = WIDTH, HEIGHT
    sc.view_settings.view_transform = 'ACES 1.3'      # near the game's tonemapper (AgX bleaches the fire to peach)
    sc.render.image_settings.file_format = 'PNG'

    mats = {k: sprite_material('F_%s' % k, os.path.join(ROOT, 'SourceArt', 'FX', 'T_FX_%s.png' % k.capitalize()), cols)
            for k, cols in (('fireball', 8), ('smoke', 8), ('fire', 4))}
    glow = glow_material()
    sprite_pool = pool(420, plane, 'P_Sprite')
    bit_pool = pool(380, sphere, 'P_Bit')
    ring_pool = pool(1, ring, 'P_Ring')
    debris_pool = pool(18, cube, 'P_Debris')
    for o in bit_pool + ring_pool + debris_pool:
        o.data.materials.append(glow)
    light_pool = []
    for k in range(6):
        ld = bpy.data.lights.new('L_%d' % k, 'POINT')
        ld.shadow_soft_size = 0.6
        ld.color = (1.0, 0.62, 0.3)
        lo = bpy.data.objects.new('L_%d' % k, ld)
        sc.collection.objects.link(lo)
        light_pool.append(lo)
    for _, o, _, _, _ in objs:
        o.hide_render = False
        o.rotation_mode = 'QUATERNION'
        o['alpha'] = 1.0
    cd = bpy.data.cameras.new('Cam')
    cd.sensor_fit = 'VERTICAL'
    cam = bpy.data.objects.new('Cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam

    # the crash camera, from where the chase camera was (behind the ship, which heads +x); it goes the way the wreck
    # flies, unless the wreck comes back at it (bounced off a wall): then it keeps the ship's heading
    heading = np.array([1.0, 0.0, 0.0])
    flat = np.array([craft_v[0], craft_v[1], 0.0])
    cam_dir = flat / np.linalg.norm(flat) if np.linalg.norm(flat) > 2.0 and np.dot(flat, heading) >= 0.0 else heading
    cam_pos = origin - heading * 9.0 + np.array([0.0, 0.0, 3.0])
    frames_dir = os.path.join(OUT, '_frames_%s' % cause)
    os.makedirs(frames_dir, exist_ok=True)
    nframes = int(round(SECONDS * FPS))
    still = None
    for fi in range(nframes):
        real = (fi + 1) / FPS
        t = min(game_time(real), SECONDS - 0.01)
        step = min(int(t / wreck.DT), min(len(p.track) for p in pieces) - 1)
        hull = pieces[0].track[step][1]
        hv = (pieces[0].track[step][1] - pieces[0].track[max(0, step - 1)][1]) / wreck.DT
        hflat = np.array([hv[0], hv[1], 0.0])
        if np.linalg.norm(hflat) > 3.0 and np.dot(hflat / np.linalg.norm(hflat), cam_dir) > -0.2:
            want = hflat / np.linalg.norm(hflat)
            ang = math.acos(max(-1.0, min(1.0, float(np.dot(cam_dir, want)))))
            turn = min(ang, math.radians(90.0) / FPS)
            if ang > 1e-4:
                axis = np.cross(cam_dir, want)
                axis = axis / max(np.linalg.norm(axis), 1e-9)
                cam_dir = cam_dir * math.cos(turn) + np.cross(axis, cam_dir) * math.sin(turn)
                cam_dir = cam_dir / np.linalg.norm(cam_dir)
        side = np.cross(cam_dir, [0.0, 0.0, 1.0])          # to the right, as UE's Up x Dir in its left-handed axes
        side = side / np.linalg.norm(side)
        orbit = math.radians(min(-115.0 + 45.0 * real, 20.0))
        desired = hull + (cam_dir * math.cos(orbit) + side * math.sin(orbit)) * 15.0 + np.array([0.0, 0.0, 4.5])
        cam_pos = cam_pos + (desired - cam_pos) * min(1.0, 3.5 / FPS)
        shown = cam_pos.copy()
        if wall_x is not None:
            shown[0] = min(shown[0], wall_x - 1.0)
        shown[2] = max(shown[2], 1.0)
        cam.location = Vector(shown)
        cam.rotation_euler = (Vector(hull) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cd.angle = math.radians(58.0 + (48.0 - 58.0) * min(1.0, real / 2.0))
        cam_q = cam.rotation_euler.to_quaternion()

        # the pieces, charred and glowing as they burn out
        for k, ((_, o, _, _, _), pc) in enumerate(zip(objs, pieces)):
            _, p, q = pc.track[step]
            o.location = Vector(p)
            o.rotation_quaternion = (q[0], q[1], q[2], q[3])
            o['heat'] = max(0.15, 1.0 - t / burn[k])
            o.update_tag()
        # every sprite alive now: the explosion's, the strikes', the flames on the pieces, their trails, the hull's smoke
        alive = []
        for s in sprites:
            st = sprite_state(s, t)
            if st:
                alive.append(st)
        cam_right = np.array(cam_q @ Vector((1.0, 0.0, 0.0)))
        cam_up = np.array(cam_q @ Vector((0.0, 1.0, 0.0)))
        for k, pc in enumerate(pieces):
            heat = max(0.0, 1.0 - t / burn[k])
            if heat > 0.02:
                p = pc.track[step][1]
                pv = (pc.track[step][1] - pc.track[max(0, step - 1)][1]) / wreck.DT
                stream = np.array([0.0, 0.0, 4.0]) - pv
                stream = stream / max(np.linalg.norm(stream), 1e-6)
                size = sizes[k] * (1.1 + 1.2 * heat)
                angle = math.atan2(float(np.dot(stream, cam_right)), float(np.dot(stream, cam_up)))
                alive.append(('fire', p + stream * 0.33 * size, size, (t * 16.0 + phases[k]) % 16.0, 5.0 * heat,
                              min(1.0, heat * 1.6), (1.0, 1.0, 1.0), angle))
        for tr in trails:
            st = trail_state(tr, t, cam_right, cam_up)
            if st:
                alive.append(st)
        for pf in puffs:
            st = puff_state(pf, t)
            if st:
                alive.append(st)
        for o, st in zip(sprite_pool, alive[:len(sprite_pool)]):
            kind, p, size, frame, gl, op, tint, rot = st
            o.hide_render = False
            o.active_material = mats[kind]
            o.location = Vector(p)
            o.rotation_mode = 'QUATERNION'
            o.rotation_quaternion = cam_q
            o.scale = (size, size, 1.0)
            o['frame'], o['glow'], o['opac'], o['tint'] = float(frame), float(gl), float(op), tuple(float(x) for x in tint)
            o['rot'] = float(rot)
            o.update_tag()
        for o in sprite_pool[len(alive):]:
            o.hide_render = True
        # the glowing bits: the heart, the shock ring, the debris, the sparks
        live_bits = [st for st in (bit_state(b, t) for b in bits) if st]
        spheres = [st for st in live_bits if st[0] in ('core', 'spark')]
        for o, st in zip(bit_pool, spheres):
            shape, p, vel, size, inten, colour, age = st
            o.hide_render = False
            o.location = Vector(p)
            if shape == 'spark':
                # the streak a spark leaves in one game frame (motion blur in the game)
                sp = float(np.linalg.norm(vel))
                d = vel / max(sp, 1e-6)
                o.rotation_mode = 'QUATERNION'
                o.rotation_quaternion = Vector(d).to_track_quat('Z', 'Y')
                o.scale = (size, size, size + sp * 0.012)
            else:
                o.rotation_mode = 'XYZ'
                o.rotation_euler = (0, 0, 0)
                o.scale = (size, size, size)
            o['colour'], o['inten'] = tuple(colour), float(inten)
            o.update_tag()
        for o in bit_pool[len(spheres):]:
            o.hide_render = True
        rings = [st for st in live_bits if st[0] == 'ring']
        for o in ring_pool:
            o.hide_render = not rings
            if rings:
                _, p, _, size, inten, colour, _ = rings[0]
                o.location = Vector(p)
                o.scale = (size, size, size * 0.6)
                o['colour'], o['inten'] = tuple(colour), float(inten)
                o.update_tag()
        debris = [st for st in live_bits if st[0] == 'debris']
        for o, (st, b) in zip(debris_pool, [(bit_state(b, t), b) for b in bits if b['shape'] == 'debris' and bit_state(b, t)]):
            _, p, _, size, inten, colour, age = st
            o.hide_render = False
            o.location = Vector(p)
            o.rotation_mode = 'XYZ'
            o.rotation_euler = tuple(b['spin'] * age)
            o.scale = (size, size * 0.6, size * 0.15)
            o['colour'], o['inten'] = tuple(colour), float(inten)
            o.update_tag()
        for o in debris_pool[len(debris):]:
            o.hide_render = True
        # the lights: the flashes (the blast, its second burst, the strikes) and the burning hull
        lights = []
        for (t0, cd_, decay, at) in flashes:
            if t >= t0:
                lights.append((at + np.array([0.0, 0.0, 1.0]), cd_ * math.exp(-(t - t0) * decay)))
        lights.sort(key=lambda x: -x[1])
        heat_hull = max(0.0, 1.0 - t / burn[0])
        lights = [(hull + np.array([0.0, 0.0, 2.5]), 60.0 * heat_hull)] + lights
        for lo, lt in zip(light_pool, lights + [None] * len(light_pool)):
            if lt is None or lt[1] < 2.0:
                lo.hide_render = True
                continue
            lo.hide_render = False
            lo.location = Vector(lt[0])
            lo.data.energy = lt[1] * CANDELA_TO_W
        path = os.path.join(frames_dir, 'f%04d.png' % fi)
        if TEST and fi not in test_frames(nframes):
            continue
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if still is None and real >= 0.9:
            still = path
        print('VIDEO %s frame %d/%d (game %.2f s, %d sprites)' % (cause, fi + 1, nframes, t, len(alive)), flush=True)
    return frames_dir, nframes, still


def test_frames(nframes):
    return sorted(set(int(round(x)) for x in np.linspace(nframes * 0.06, nframes - 1, 8)))


def test_sheet(cause, frames_dir, nframes):
    from PIL import Image, ImageDraw, ImageFont
    small = ImageFont.truetype(os.path.join(ROOT, 'Content', 'UI', 'Fonts', 'Inter-ExtraBold.otf'), 18)
    picks = test_frames(nframes)
    tw, th = WIDTH // 2, HEIGHT // 2
    sheet = Image.new('RGB', (tw * 4, th * 2), (8, 18, 38))
    d = ImageDraw.Draw(sheet)
    for k, fi in enumerate(picks):
        im = Image.open(os.path.join(frames_dir, 'f%04d.png' % fi)).convert('RGB').resize((tw, th))
        x, y = (k % 4) * tw, (k // 4) * th
        sheet.paste(im, (x, y))
        real = (fi + 1) / FPS
        d.rectangle([x + 6, y + 6, x + 190, y + 32], fill=(3, 8, 20))
        d.text((x + 12, y + 8), ('%.2f s (jogo %.2f s)' % (real, game_time(real))).replace('.', ','), font=small, fill=(150, 225, 255))
    sheet.save(os.path.join(OUT, 'wreck_%s_test.jpg' % cause), quality=88)
    shutil.rmtree(frames_dir)


def label_frames(cause, frames_dir, nframes):
    """The cause and the slow motion written on the frames."""
    from PIL import Image, ImageDraw, ImageFont
    fonts = os.path.join(ROOT, 'Content', 'UI', 'Fonts')
    big = ImageFont.truetype(os.path.join(fonts, 'Orbitron-Black.ttf'), max(18, HEIGHT // 22))
    small = ImageFont.truetype(os.path.join(fonts, 'Inter-ExtraBold.otf'), max(14, HEIGHT // 30))
    for fi in range(nframes):
        path = os.path.join(frames_dir, 'f%04d.png' % fi)
        im = Image.open(path).convert('RGB')
        d = ImageDraw.Draw(im)
        title = wreck.CAUSES[cause]['title'].upper()
        d.rectangle([0, 0, WIDTH, HEIGHT // 13], fill=(3, 8, 20))
        d.text((16, HEIGHT // 80), title, font=big, fill=(238, 245, 255))
        real = (fi + 1) / FPS
        if dilation(real) < 0.99:
            tag = 'CÂMARA LENTA %.1fx' % dilation(real)
            tag = tag.replace('.', ',')
            w = d.textlength(tag, font=small)
            d.rectangle([WIDTH - w - 32, HEIGHT // 13 + 10, WIDTH - 12, HEIGHT // 13 + 14 + HEIGHT // 26], fill=(3, 8, 20))
            d.text((WIDTH - w - 22, HEIGHT // 13 + 12), tag, font=small, fill=(255, 196, 64))
        im.save(path)


def encode(cause, frames_dir, nframes, still):
    mp4 = os.path.join(OUT, 'wreck_%s.mp4' % cause)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(frames_dir, 'f%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-movflags', '+faststart', mp4], check=True)
    gif = os.path.join(OUT, 'wreck_%s.gif' % cause)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(frames_dir, 'f%04d.png'),
                    '-vf', 'fps=12,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer',
                    gif], check=True)
    if still:
        from PIL import Image
        Image.open(still).convert('RGB').save(os.path.join(OUT, 'wreck_%s_still.jpg' % cause), quality=90)
    shutil.rmtree(frames_dir)
    print('VIDEO %s -> %s' % (cause, mp4), flush=True)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    parts = sims.build_parts()
    for cause in CAUSES:
        frames_dir, nframes, still = render_cause(cause, parts)
        if TEST:
            test_sheet(cause, frames_dir, nframes)
            continue
        label_frames(cause, frames_dir, nframes)
        encode(cause, frames_dir, nframes, still)
