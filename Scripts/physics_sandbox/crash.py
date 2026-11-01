"""Physics sandbox, top view: knocks between ships with the NEW crash model (AEXHoverCraft::CrashWith / TakeCrash, the
same numbers): the momentum shared by the masses with a little bounce, the rub dragging the faster ship back and the
slower forward, the spin of an off-centre knock, the handling upset and the hull lost. The handling here is a simple
stand-in (speed held, grip pulling the slide back), enough to show what a knock does.
python3 Scripts/physics_sandbox/crash.py [out_dir]
"""
import math
import os
import sys

import numpy as np

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
DT = 1.0 / 60.0
MASS = {'VORTEX': 1250, 'STRIX': 1450, 'WRAITH': 1180, 'NOMAD': 1650, 'BASTION': 1950}
C = dict(Restitution=0.3, Friction=0.35, SafeMps=4.0, DamagePerMps=1.8, SpinRadius=1.8, SpinMax=2.6, SpinDecay=2.0,
         WobbleSeconds=1.1, ScrapePerS=6.0, G=22.0)
COLOURS = {'VORTEX': '#ff5a5a', 'STRIX': '#4aa3ff', 'WRAITH': '#5fd17a', 'NOMAD': '#b56cff', 'BASTION': '#ffc23d'}


class Ship:
    def __init__(self, name, x, y, heading_deg, kmh, steer=None):
        self.name = name
        self.m = MASS[name]
        self.p = np.array([x, y], float)
        self.psi = math.radians(heading_deg)
        self.v = np.array([math.cos(self.psi), math.sin(self.psi)]) * kmh / 3.6
        self.target = kmh / 3.6
        self.steer = steer or (lambda t: 0.0)
        self.spin = 0.0
        self.wobble = 0.0
        self.hull = 100.0
        self.scrape = 0.0
        self.cool = 0.0
        self.path = []
        self.hits = []
        self.psi0 = self.psi
        self.hits_any = False
        self.correct_from = 1e9

    def circles(self):
        f = np.array([math.cos(self.psi), math.sin(self.psi)])
        return [self.p + f * d for d in (-2.0, 0.0, 2.0)]

    def fwd(self):
        return np.array([math.cos(self.psi), math.sin(self.psi)])

    def step(self, t):
        self.wobble = max(0.0, self.wobble - DT / C['WobbleSeconds'])
        self.cool = max(0.0, self.cool - DT)
        self.spin *= math.exp(-C['SpinDecay'] * DT)
        speed = np.linalg.norm(self.v)
        # the pilot (or the bot) counter-steers back to the line after a knock
        steer = self.steer(t)
        if self.hits_any and t > self.correct_from:
            steer = max(-1.0, min(1.0, -2.0 * ((self.psi - self.psi0 + math.pi) % (2 * math.pi) - math.pi)))
        turn = 0.8 * steer * (1.0 - 0.6 * self.wobble)
        wob = self.wobble * 0.35 * math.sin(t * 9.0)
        self.psi += (turn + self.spin + wob) * DT
        f = self.fwd()
        side = np.array([-f[1], f[0]])
        lon = float(np.dot(self.v, f))
        lat = float(np.dot(self.v, side))
        grip = 6.0 * (1.0 - 0.7 * self.wobble)
        lat *= math.exp(-grip * DT)
        lon += (self.target - lon) * 1.2 * DT
        self.v = f * lon + side * lat
        self.p = self.p + self.v * DT
        self.path.append((self.p.copy(), self.psi))

    def take(self, dv, point, ram_share, slip):
        anchor = 0.75 if self.name == 'BASTION' else 1.0
        dv = dv * anchor
        if not self.hits_any:
            self.hits_any = True
            self.correct_from = len(self.path) * DT + 0.35   # a reaction time
        kick = float(np.linalg.norm(dv))
        self.v = self.v + dv
        lever = point - self.p
        torque = lever[0] * dv[1] - lever[1] * dv[0]
        self.spin = max(-C['SpinMax'], min(C['SpinMax'], self.spin + torque / C['SpinRadius'] ** 2))
        if kick > 2.5:
            self.wobble = max(self.wobble, min(1.0, max(0.15, kick / 18.0)))
        self.scrape += C['ScrapePerS'] * min(2.0, slip / 20.0) * DT
        dmg = max(0.0, kick - C['SafeMps']) * C['DamagePerMps'] * ram_share
        if dmg > 0 and self.cool <= 0:
            dmg = min(40.0, dmg + self.scrape)
            self.hull -= dmg
            self.scrape = 0.0
            self.cool = 0.2
            self.hits.append((point.copy(), kick, dmg))
        elif self.scrape >= 3.0:
            self.hull -= self.scrape
            self.hits.append((point.copy(), kick, self.scrape))
            self.scrape = 0.0


def collide(a, b):
    best = None
    for ca in a.circles():
        for cb in b.circles():
            d = np.linalg.norm(ca - cb)
            if best is None or d < best[0]:
                best = (d, ca, cb)
    d, ca, cb = best
    if d >= 2.4:
        return False
    n = (ca - cb) / max(d, 1e-6)
    point = (ca + cb) / 2
    rel = a.v - b.v
    closing = float(np.dot(rel, n))
    tangent = rel - n * closing
    slip = float(np.linalg.norm(tangent))
    inv = 1.0 / a.m + 1.0 / b.m
    imp = np.zeros(2)
    if closing < 0:
        j = -(1 + C['Restitution']) * closing / inv
        imp = n * j
        if slip > 0.5:
            imp -= tangent / slip * min(C['Friction'] * j, slip / inv)
    elif slip > 3.0:
        imp -= tangent / slip * min(slip / inv, C['Friction'] * C['G'] * DT / inv)
    a_rams = np.dot(a.fwd(), -n) > 0.6 and np.dot(a.v, -n) > np.dot(b.v, -n)
    b_rams = np.dot(b.fwd(), n) > 0.6 and np.dot(b.v, n) > np.dot(a.v, n)
    a.take(imp / a.m, point, 0.6 if a_rams else 1.0, slip)
    b.take(-imp / b.m, point, 0.6 if b_rams else 1.0, slip)
    # push apart (the sweep stops the hulls at contact)
    push = (2.4 - d) * n
    a.p += push * (1.0 / a.m) / inv
    b.p -= push * (1.0 / b.m) / inv
    return True


def run(ships, seconds):
    t = 0.0
    while t < seconds:
        for s in ships:
            s.step(t)
        for i in range(len(ships)):
            for j in range(i + 1, len(ships)):
                collide(ships[i], ships[j])
        t += DT
    return ships


def scenarios():
    return [
        ('Raspão lado a lado a 400 km/h: a BASTION (1950 kg) encosta-se à WRAITH (1180 kg)',
         run([Ship('BASTION', 0, -3.4, 0, 400, steer=lambda t: 0.7 if 0.3 < t < 0.8 else (-0.4 if 0.8 < t < 1.3 else 0.0)), Ship('WRAITH', 1, 0.4, 0, 400)], 3.0)),
        ('Empurrão por trás na esquina (PIT): a VORTEX a 430 km/h na traseira da STRIX a 380 km/h',
         run([Ship('VORTEX', -30, 1.6, 0, 430), Ship('STRIX', 0, 0, 0, 380)], 3.0)),
        ('Pancada lateral em T: a NOMAD a 300 km/h no flanco da VORTEX a 300 km/h',
         run([Ship('NOMAD', 31, -31, 90, 300), Ship('VORTEX', 0, 0, 0, 300)], 2.4)),
    ]


def draw(path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    sc = scenarios()
    fig, axes = plt.subplots(len(sc), 1, figsize=(16, 4.6 * len(sc)), facecolor='#0a1426')
    for ax, (title, ships) in zip(axes, sc):
        ax.set_facecolor('#0a1426')
        allp = np.array([p for s in ships for p, _ in s.path])
        for s in ships:
            col = COLOURS[s.name]
            xs = [p[0] for p, _ in s.path]
            ys = [p[1] for p, _ in s.path]
            ax.plot(xs, ys, color=col, lw=1.5, alpha=0.8)
            for k in range(0, len(s.path), 9):
                p, psi = s.path[k]
                c, sn = math.cos(psi), math.sin(psi)
                shape = [(3.0, 0.0), (-3.0, 1.2), (-3.0, -1.2)]
                ax.add_patch(Polygon([(p[0] + c * x - sn * y, p[1] + sn * x + c * y) for x, y in shape], closed=True, fc=col, ec='white',
                                     lw=0.3, alpha=0.75))
            for point, kick, dmg in s.hits:
                ax.plot(point[0], point[1], marker='*', color='white', ms=14)
            total = 100.0 - s.hull
            spin = max((abs(h[1]) for h in s.hits), default=0.0)
            ax.plot([], [], color=col, lw=6, label='%s  %d kg  ·  casco −%.0f%%  ·  maior Δv %.1f m/s' % (s.name, s.m, total, spin))
        ax.set_title(title, color='white', fontsize=13, loc='left')
        ax.set_aspect('equal')
        pad = 6
        ax.set_xlim(allp[:, 0].min() - pad, allp[:, 0].max() + pad)
        ax.set_ylim(allp[:, 1].min() - pad, allp[:, 1].max() + pad)
        ax.tick_params(colors='#8ca5c4')
        for sp in ax.spines.values():
            sp.set_color('#2a3a55')
        ax.legend(loc='upper left', facecolor='#081226', edgecolor='#46dcff', labelcolor='white', fontsize=11)
        ax.set_xlabel('metros (vista de cima)', color='#8ca5c4')
    fig.tight_layout()
    fig.savefig(path, dpi=80, facecolor=fig.get_facecolor())
    for title, ships in sc:
        print(title)
        for s in ships:
            print('   %-8s hull %.0f  hits %s  final heading %.0f deg' % (s.name, s.hull, [(round(k, 1), round(d, 1)) for _, k, d in s.hits],
                                                                       math.degrees(s.psi)))


if __name__ == '__main__':
    draw(os.path.join(OUT, 'fisica_choques.png'))
