"""The wreck's physics (player, 2026-11-01: "a carcaça das naves destruídas a alta velocidade a voar em frente e a cair
dando várias voltas, cambalhotas; os módulos podem voar carbonizados, são peças separadas; a física dos objetos a voar
depende de como a nave é destruída"). Each piece (the hull, each wing, the tail, the body kit, the cooling) is a box that
flies, spins and hits the ground (and walls) at its corners: an impulse with a little bounce and friction at each
corner that touches, so it tumbles, cartwheels, bounces and comes to rest like a solid thing. AEXWreck runs the same
steps in the game (line traces for the corners). The way the ship died sets how it starts (CAUSES below).
python3 Scripts/physics_sandbox/wreck.py   (prints the scenarios; Scripts/physics_sandbox/wreck_sims.py renders them)
"""
import math

import numpy as np

G = 22.0                  # the game's gravity (m/s^2)
DT = 1.0 / 120.0
RESTITUTION = 0.32
FRICTION = 0.55
LINEAR_DRAG = 0.08
ANGULAR_DRAG = 0.25
# A hard hit is not a clean bounce: the bodywork crumples and a corner digs into the sand, so it catches much harder than
# it slides (a nose landing pole-vaults over the nose) and the crumpling soaks up some of the spin. Without this a box
# tumbling at 100 m/s rolls like a wheel and spins up towards speed / size (35 rad/s).
DIG_SPEED = 10.0          # m/s into the ground: a hard hit
DIG_FRICTION = 1.7
CRUSH = 0.8               # the spin kept after a hard hit
MAX_TIP_SPEED = 45.0      # m/s: the far corner never whirls faster than this round the centre


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def qmat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def qaxis(axis, angle):
    axis = np.asarray(axis, float)
    n = np.linalg.norm(axis)
    if n < 1e-9:
        return np.array([1.0, 0, 0, 0])
    s = math.sin(angle / 2) / n
    return np.array([math.cos(angle / 2), axis[0] * s, axis[1] * s, axis[2] * s])


class Piece:
    def __init__(self, name, half, mass, p, q, v, w):
        self.name = name
        self.h = np.asarray(half, float)
        self.m = float(mass)
        lx, ly, lz = 2 * self.h
        self.ib_inv = 1.0 / (self.m / 12.0 * np.array([ly * ly + lz * lz, lx * lx + lz * lz, lx * lx + ly * ly]))
        self.p = np.asarray(p, float)
        self.q = np.asarray(q, float)
        self.v = np.asarray(v, float)
        self.w = np.asarray(w, float)
        self.asleep = 0.0
        self.track = []
        self.hits = []

    def corners(self):
        R = qmat(self.q)
        out = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    out.append(self.p + R @ (self.h * np.array([sx, sy, sz])))
        return out


def ground(x, y):
    return 0.0, np.array([0.0, 0.0, 1.0])


def step(piece, t, planes):
    if piece.asleep > 0.6:
        piece.track.append((t, piece.p.copy(), piece.q.copy()))
        return
    piece.v[2] -= G * DT
    piece.v *= 1.0 - LINEAR_DRAG * DT
    piece.w *= 1.0 - ANGULAR_DRAG * DT
    piece.p = piece.p + piece.v * DT
    wq = np.array([0.0, *piece.w])
    piece.q = piece.q + 0.5 * qmul(wq, piece.q) * DT
    piece.q /= np.linalg.norm(piece.q)
    R = qmat(piece.q)
    iinv = R @ np.diag(piece.ib_inv) @ R.T
    push = np.zeros(3)
    crushed = False
    for _ in range(2):
        for c in piece.corners():
            for (point, normal) in planes(c):
                depth = float(np.dot(point - c, normal))
                if depth <= 0.0:
                    continue
                push = np.maximum(push, normal * depth) if normal[2] > 0.5 else push + normal * depth * 0.5
                r = c - piece.p
                vc = piece.v + np.cross(piece.w, r)
                vn = float(np.dot(vc, normal))
                if vn >= 0.0:
                    continue
                e = RESTITUTION if vn < -2.0 else 0.0
                kn = 1.0 / piece.m + float(np.dot(normal, np.cross(iinv @ np.cross(r, normal), r)))
                j = -(1.0 + e) * vn / kn
                piece.v = piece.v + normal * j / piece.m
                piece.w = piece.w + iinv @ np.cross(r, normal * j)
                vc = piece.v + np.cross(piece.w, r)
                vt = vc - normal * float(np.dot(vc, normal))
                st = float(np.linalg.norm(vt))
                if st > 1e-4:
                    tdir = vt / st
                    kt = 1.0 / piece.m + float(np.dot(tdir, np.cross(iinv @ np.cross(r, tdir), r)))
                    jt = min((DIG_FRICTION if -vn > DIG_SPEED else FRICTION) * j, st / kt)
                    piece.v = piece.v - tdir * jt / piece.m
                    piece.w = piece.w - iinv @ np.cross(r, tdir * jt)
                if -vn > 6.0:
                    piece.hits.append((t, c.copy(), -vn))
                crushed = crushed or -vn > DIG_SPEED
    if crushed:
        piece.w = piece.w * CRUSH
    spin, cap = float(np.linalg.norm(piece.w)), MAX_TIP_SPEED / float(np.linalg.norm(piece.h))
    if spin > cap:
        piece.w = piece.w * (cap / spin)
    piece.p = piece.p + push * 0.8
    slow = np.linalg.norm(piece.v) < 0.35 and np.linalg.norm(piece.w) < 0.5
    piece.asleep = piece.asleep + DT if slow else 0.0
    piece.track.append((t, piece.p.copy(), piece.q.copy()))


def simulate(pieces, seconds, planes):
    t = 0.0
    while t < seconds:
        for p in pieces:
            step(p, t, planes)
        t += DT
    return pieces


# How the ship died sets how its pieces start (AEXHoverCraft::Eliminate keeps the last knock: its change of speed, where
# it hit; within 0.4 s of the blast it decides the tumble). Speeds in m/s, spins in rad/s about the ship's axes:
# forward x, left y, up z (nose down = +y spin here: the nose goes down and forward, "cambalhota").
# A spin that "trips" keeps going when the hull touches the ground (the friction under it feeds it): the top rolls the
# way the hull is moving. So the side hit rolls about -x when it is pushed to +y, the forward flips are +y.
CAUSES = {
    'parede': dict(title='De frente contra a rocha a 380 km/h', kmh=380, keep=-0.25, kick=(0, 0, 9), spin=(1.5, -9.0, 1.0),
                   modules=dict(keep=0.55, out=12.0), wall=True),
    'lado': dict(title='Pancada lateral (em T) a 350 km/h', kmh=350, keep=0.8, kick=(0, 26, 9), spin=(-13.0, 1.0, 3.0),
                 modules=dict(keep=0.8, out=11.0)),
    'traseira': dict(title='Empurrão na traseira (PIT) a 450 km/h', kmh=450, keep=1.0, kick=(6, -4, 7), spin=(2.5, 10.0, 4.0),
                     modules=dict(keep=0.95, out=9.0)),
    'aterragem': dict(title='Aterragem de nariz depois de um salto a 400 km/h', kmh=400, keep=1.0, kick=(0, 0, 4), spin=(0.5, 3.0, 0.3),
                      modules=dict(keep=0.95, out=9.0), fall=dict(vz=-26.0, pitch=-24.0, height=2.2)),
    'desgaste': dict(title='Casco a zero a raspar, a 420 km/h', kmh=420, keep=1.0, kick=(0, 0, 8), spin=(3.0, 6.0, 1.5),
                     modules=dict(keep=0.97, out=8.0)),
}


def start(cause, layout, seed=3):
    """layout: [(name, half extents, mass, centre in the ship's frame)]; the hull first."""
    rng = np.random.default_rng(seed)
    c = CAUSES[cause]
    speed = c['kmh'] / 3.6
    fall = c.get('fall')
    pitch = math.radians(fall['pitch']) if fall else 0.0
    q0 = qaxis((0, 1, 0), -pitch)          # nose down: positive rotation about y tips +x down? (checked in wreck_sims)
    R0 = qmat(q0)
    base_v = np.array([speed, 0.0, fall['vz'] if fall else 0.0])
    hull_v = base_v * np.array([c['keep'], 1.0, 1.0]) + np.array(c['kick'], float)
    hull_w = R0 @ np.array(c['spin'], float)
    height = fall['height'] if fall else 1.5
    pieces = []
    for k, (name, half, mass, centre) in enumerate(layout):
        p = np.array([0.0, 0.0, height]) + R0 @ np.asarray(centre, float)
        if k == 0:
            v, w = hull_v, hull_w
        else:
            out = np.asarray(centre, float)
            out = out / max(np.linalg.norm(out), 1e-3)
            v = base_v * np.array([c['modules']['keep'], 1.0, 1.0]) + R0 @ out * c['modules']['out'] * rng.uniform(0.7, 1.3)
            v = v + np.array([0, 0, rng.uniform(3.0, 8.0)]) + rng.normal(0, 1.5, 3)
            w = rng.normal(0, 9.0, 3)
        pieces.append(Piece(name, half, mass, p, q0.copy(), v, w))
    return pieces


def planes_for(cause):
    wall_x = 1.0 if CAUSES[cause].get('wall') else None

    def planes(c):
        out = [(np.array([c[0], c[1], 0.0]), np.array([0.0, 0.0, 1.0]))]
        if wall_x is not None and c[2] < 14.0 and abs(c[1]) < 30.0:
            out.append((np.array([wall_x, c[1], c[2]]), np.array([-1.0, 0.0, 0.0])))
        return out
    return planes


LAYOUT_DEMO = [('hull', (3.0, 0.9, 0.45), 1250, (0, 0, 0)), ('wing_l', (1.0, 1.1, 0.12), 110, (0.6, 2.0, 0)),
               ('wing_r', (1.0, 1.1, 0.12), 110, (0.6, -2.0, 0)), ('tail', (0.5, 0.15, 0.5), 60, (-2.6, 0, 0.6)),
               ('kit', (2.4, 1.0, 0.15), 160, (0.3, 0, -0.45)), ('cooling', (0.6, 0.5, 0.2), 70, (-0.8, 0, 0.5))]

if __name__ == '__main__':
    for cause in CAUSES:
        pcs = simulate(start(cause, LAYOUT_DEMO), 4.0, planes_for(cause))
        hull = pcs[0]
        travel = hull.track[-1][1] - hull.track[0][1]
        turns = 0.0
        air = 0.0
        last = None
        for t, p, q in hull.track:
            if last is not None:
                turns += 2.0 * math.acos(min(1.0, abs(float(np.dot(q, last)))))   # any axis: flips, rolls, spins
            last = q
            air += DT if p[2] > 1.2 else 0.0
        print('%-10s hull travels %5.0f m, turns %.1f times (%.1f s off the ground), %d hard hits, rests %s' % (
            cause, np.linalg.norm(travel[:2]), turns / (2 * math.pi), air, len(hull.hits), 'yes' if hull.asleep > 0.6 else 'no'))
