"""
EXTRACT: STARDUST — gera os sons do jogo (síntese procedural, sem assets externos) em Assets/RedDust/Resources/Audio.
  python Tools/gen_audio.py
v2: motor de turbina (ronco + assobio), boost com estalidos, derrapagem, impactos/explosão encorpados, UI suave,
caixas (abrir + revelar carta), e duas músicas em loop (menu calmo; corrida a 120 BPM com bateria, baixo, pad e arpejo).
Loops são periódicos (ruído filtrado por FFT circular, frequências com ciclos inteiros, caudas dobradas para o início).
"""
import os
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Assets', 'RedDust', 'Resources', 'Audio')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)


def t_(sec):
    return np.arange(int(round(SR * sec))) / SR


def save(name, x, peak=0.8):
    x = np.asarray(x, float)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    with wave.open(os.path.join(OUT, name + '.wav'), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    print(name, f"{len(x) / SR:.2f}s")


def spectral(x, shape_fn):
    """Filtro por FFT (circular): shape_fn(freqs) -> ganho."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    return np.fft.irfft(np.fft.rfft(x) * shape_fn(f), n)


def band(f, lo, hi, tilt=0.0):
    g = np.clip((f - lo * 0.7) / (lo * 0.3 + 1e-9), 0, 1) * np.clip((hi * 1.3 - f) / (hi * 0.3), 0, 1)
    return g * (np.maximum(f, 1.0) / 1000.0) ** tilt


def noise(sec, lo, hi, tilt=0.0):
    """Ruído periódico entre lo e hi Hz (loops sem costura)."""
    return spectral(rng.standard_normal(int(round(SR * sec))), lambda f: band(f, lo, hi, tilt))


def lowpass(x, fc, order=2):
    """Passa-baixo suave (one-shots: almofada de zeros para a cauda não dar a volta)."""
    pad = np.concatenate([x, np.zeros(int(SR * 0.25))])
    y = spectral(pad, lambda f: 1.0 / (1.0 + (f / fc) ** (2 * order)) ** 0.5)
    return y[:len(x)]


def env(sec, a=0.005, d=0.3, curve=4.0):
    t = t_(sec)
    return np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-curve * np.maximum(0, t - a) / max(d, 1e-4))


def sine(f, sec, ph=0.0):
    f = np.full(int(round(SR * sec)), f) if np.isscalar(f) else np.asarray(f)
    return np.sin(2 * np.pi * np.cumsum(f) / SR + ph)


def saw(f, sec, nmax=40):
    """Dente de serra limitado em banda (soma de harmónicos)."""
    t = t_(sec)
    n = int(min(nmax, (SR * 0.45) // max(f, 1)))
    return sum(np.sin(2 * np.pi * k * f * t) / k for k in range(1, n + 1)) * (2 / np.pi)


def square(f, sec, nmax=9):
    t = t_(sec)
    return sum(np.sin(2 * np.pi * k * f * t) / k for k in range(1, nmax + 1, 2)) * (4 / np.pi)


def fold(x, L):
    """Dobra a cauda (para lá de L amostras) para o início: loop periódico."""
    y = x[:L].copy()
    tail = x[L:]
    y[:len(tail)] += tail[:L]
    return y


# ===================================================================== motor, boost, vento, derrapagem (loops)
L = 4.0
t = t_(L)
rumble = noise(L, 28, 240, -1.1)
sub = 0.35 * np.sin(2 * np.pi * 48 * t)
pm = 0.55 * np.sin(2 * np.pi * 5 * t)                       # vibrato periódico (20 ciclos)
whine = np.sin(2 * np.pi * 620 * t + pm) + 0.35 * np.sin(2 * np.pi * 1240 * t + 2 * pm) + 0.12 * np.sin(2 * np.pi * 1860 * t + 3 * pm)
hiss = noise(L, 2500, 7000, -0.4)
eng = rumble / np.std(rumble) * 0.55 + sub + whine * 0.16 + hiss / np.std(hiss) * 0.035
save('engine_loop', eng, 0.6)

L = 3.0
t = t_(L)
roar = noise(L, 70, 3200, -0.7)
imp = np.zeros(int(SR * L))
imp[rng.integers(0, len(imp), 260)] = rng.uniform(-1, 1, 260)
crackle = spectral(imp, lambda f: band(f, 600, 5000, -0.2))
boost = roar / np.std(roar) + crackle / np.std(crackle) * 0.35 + 0.4 * np.sin(2 * np.pi * 70 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 12 * t))
save('boost_loop', boost, 0.6)

L = 4.0
t = t_(L)
save('wind_loop', noise(L, 180, 1700, -1.3) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.5 * t)), 0.55)

L = 2.0
t = t_(L)
drift = noise(L, 900, 5200, -0.3) * (0.75 + 0.25 * np.sin(2 * np.pi * 23 * t)) + 0.6 * noise(L, 1650, 1950)
save('drift_loop', drift, 0.5)

# ===================================================================== impactos
sec = 0.5
t = t_(sec)
thump = sine(np.linspace(115, 42, len(t)), sec) * env(sec, 0.002, 0.14)
crunch = noise(sec, 300, 4200, -0.3) * env(sec, 0.001, 0.07)
ring = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((380, 0.5), (1150, 0.3), (2310, 0.15))) * env(sec, 0.001, 0.22, 5)
save('impact', lowpass(thump * 1.4 + crunch / np.std(crunch) * 0.25 + ring * 0.35, 6000))

sec = 0.32
t = t_(sec)
save('land', lowpass(sine(np.linspace(85, 38, len(t)), sec) * env(sec, 0.003, 0.11) + 0.12 * noise(sec, 200, 2500) / 0.05 * env(sec, 0.002, 0.05) * 0.05, 3000), 0.6)

sec = 1.9
t = t_(sec)
boom = sine(np.linspace(62, 28, len(t)), sec) * env(sec, 0.004, 0.75, 3)
expl = (noise(sec, 35, 400, -0.6) * env(sec, 0.004, 1.1, 3) + noise(sec, 400, 3000) * env(sec, 0.002, 0.35, 3) * 0.6
        + noise(sec, 3000, 9000) * env(sec, 0.001, 0.09, 3) * 0.4)
save('explosion', boom * 1.2 + expl / np.std(expl) * 0.35)

# ===================================================================== interface
def chime(freqs, step, dur, bright=0.3):
    total = step * (len(freqs) - 1) + dur
    out = np.zeros(int(round(SR * total)))
    for k, f in enumerate(freqs):
        s = int(round(SR * step * k))
        seg = (np.sin(2 * np.pi * f * t_(dur)) + bright * np.sin(2 * np.pi * 2 * f * t_(dur)) + 0.1 * np.sin(2 * np.pi * 3 * f * t_(dur))) * env(dur, 0.004, dur * 0.45, 4)
        out[s:s + len(seg)] += seg
    return out


save('ui_move', sine(1500, 0.05) * env(0.05, 0.003, 0.018) + 0.02 * rng.standard_normal(int(SR * 0.05)) * env(0.05, 0.001, 0.004), 0.25)
save('ui_ok', chime((880.0, 1318.5), 0.07, 0.22, 0.25), 0.4)
save('ui_back', chime((1318.5, 880.0), 0.07, 0.2, 0.2), 0.35)
save('beep', lowpass(square(660, 0.2) * env(0.2, 0.004, 0.14, 3), 2500), 0.5)
save('go', lowpass((square(1320, 0.7, 5) + 0.6 * np.sin(2 * np.pi * 660 * t_(0.7))) * env(0.7, 0.004, 0.45, 3), 4000), 0.6)
save('checkpoint', chime((1046.5, 1568.0), 0.09, 0.4, 0.3), 0.45)
save('loot', chime((1046.5, 1318.5, 1568.0, 2093.0), 0.06, 0.35, 0.35), 0.45)
save('warning', lowpass(np.concatenate([square(220, 0.15), np.zeros(int(SR * 0.07)), square(220, 0.15)]) * 0.9, 1200), 0.45)
sec = 2.2
ext = chime((523.25, 659.25, 783.99, 1046.5), 0.11, 1.8, 0.3)
pad = sum(saw(f, len(ext) / SR, 20) for f in (261.63, 329.63, 392.0)) * np.minimum(1, t_(len(ext) / SR) / 0.3) * np.exp(-1.6 * t_(len(ext) / SR))
save('extract', ext + lowpass(pad, 1800) * 0.25, 0.6)
# caixas: abrir (sopro a subir + brilho) e revelar carta (pluck); raro/épico/lendário com acorde mais brilhante
sec = 0.9
t = t_(sec)
sweep = spectral(rng.standard_normal(len(t)) * np.linspace(0.2, 1, len(t)), lambda f: band(f, 300, 6000, -0.3))
save('cache_open', sweep * env(sec, 0.5, 0.25, 4) * 2 + chime((1568.0, 2093.0, 2637.0), 0.05, 0.5, 0.4)[:len(t)] * 0.5 if len(chime((1568.0, 2093.0, 2637.0), 0.05, 0.5, 0.4)) >= len(t)
     else sweep * env(sec, 0.5, 0.25, 4) * 2 + np.pad(chime((1568.0, 2093.0, 2637.0), 0.05, 0.5, 0.4), (0, len(t) - len(chime((1568.0, 2093.0, 2637.0), 0.05, 0.5, 0.4)))) * 0.5, 0.5)
save('card', chime((1174.7,), 0.0, 0.18, 0.4), 0.35)
save('card_rare', chime((1318.5, 1975.5, 2637.0), 0.04, 0.6, 0.5), 0.5)

# ===================================================================== música (loops de 16 s, 120 BPM, Am – F – C – G)
BPM, BARS = 120, 8
beat = 60.0 / BPM
L = BARS * 4 * beat
NL = int(round(SR * L))
TAIL = int(SR * 2.5)
chords = [(57, 60, 64), (53, 57, 60), (48, 55, 60), (55, 59, 62)]    # MIDI: Am, F, C, G (2 compassos cada)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def place(buf, seg, start):
    s = int(round(SR * start))
    e = min(len(buf), s + len(seg))
    buf[s:e] += seg[:e - s]


def kick():
    d = 0.32
    return sine(np.linspace(130, 44, int(SR * d)), d) * env(d, 0.002, 0.16, 4)


def snare():
    d = 0.22
    return noise(d, 1200, 7000) / 0.05 * 0.05 * env(d, 0.001, 0.09) + 0.4 * np.sin(2 * np.pi * 190 * t_(d)) * env(d, 0.001, 0.05)


def hat(open_=False):
    d = 0.12 if open_ else 0.04
    return noise(d, 6500, 12000) * env(d, 0.001, d * 0.5)


def pluck(f, d=0.16, bright=0.5):
    return (np.sin(2 * np.pi * f * t_(d)) + bright * (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * 2 * f * t_(d)))) * env(d, 0.002, d * 0.35, 4)


def music(drums):
    total = NL + TAIL
    k_, s_, h_, bass, padb, arp = (np.zeros(total) for _ in range(6))
    for bar in range(BARS):
        ch = chords[bar // 2]
        t0 = bar * 4 * beat
        for b in range(4):
            tb = t0 + b * beat
            if drums:
                place(k_, kick(), tb)
                if b in (1, 3):
                    place(s_, snare(), tb)
                place(h_, hat(), tb + beat / 2)
                place(h_, hat() * 0.5, tb)
            for e in range(2):                          # baixo em colcheias
                f = hz(ch[0] - 24 + (12 if (b == 3 and e == 1) else 0))
                d = beat / 2
                seg = saw(f, d * 0.95, 30) * env(d * 0.95, 0.004, d * 0.5, 3)
                place(bass, seg, tb + e * d)
            for e in range(4):                          # arpejo em semicolcheias
                note = ch[(b * 4 + e) % 3] + 12 + (12 if (e == 3 and b % 2) else 0)
                place(arp, pluck(hz(note), 0.18, 0.4) * (1.0 if e == 0 else 0.7), tb + e * beat / 4)
        if bar % 2 == 0:                                 # pad: um acorde a cada 2 compassos
            d = 8 * beat + 1.5
            seg = sum(saw(hz(m) * dt, d, 18) for m in ch for dt in (0.997, 1.0, 1.004))
            seg *= np.minimum(1, t_(d) / 0.6) * np.exp(-0.25 * np.maximum(0, t_(d) - 8 * beat)) * np.where(t_(d) > 8 * beat, np.exp(-3 * (t_(d) - 8 * beat)), 1)
            place(padb, seg, t0)
    bass = lowpass(fold(bass, NL), 420)
    padb = lowpass(fold(padb, NL), 1400)
    arp = fold(arp, NL)
    arp = arp + 0.35 * np.roll(arp, int(SR * beat * 0.75))   # eco (circular = periódico)
    mix = bass / np.std(bass) * 0.30 + padb / np.std(padb) * 0.16 + arp / np.std(arp) * 0.11
    if drums:
        mix += fold(k_, NL) / np.std(fold(k_, NL)) * 0.30 + fold(s_, NL) / np.std(fold(s_, NL)) * 0.12 + fold(h_, NL) / np.std(fold(h_, NL)) * 0.05
    return mix


save('music_race', music(True), 0.7)
save('music_menu', music(False), 0.6)
