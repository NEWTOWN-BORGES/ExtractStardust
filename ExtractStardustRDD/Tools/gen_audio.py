"""
EXTRACT: STARDUST — gera os sons do jogo (síntese procedural, sem assets externos) em Assets/RedDust/Resources/Audio.
  python Tools/gen_audio.py
Loops (motor, boost, vento, ambiente) são periódicos (ruído filtrado por FFT + frequências com ciclos inteiros): sem cliques.
"""
import os
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Assets', 'RedDust', 'Resources', 'Audio')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def t_(sec):
    return np.arange(int(SR * sec)) / SR


def save(name, x, peak=0.85):
    x = np.asarray(x, float)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    with wave.open(os.path.join(OUT, name + '.wav'), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())
    print(name, f"{len(x) / SR:.2f}s")


def band_noise(sec, lo, hi, tilt=0.0):
    """Ruído periódico (FFT circular) entre lo e hi Hz; tilt < 0 escurece."""
    n = int(SR * sec)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    shape = np.clip((f - lo * 0.7) / (lo * 0.3 + 1e-9), 0, 1) * np.clip((hi * 1.3 - f) / (hi * 0.3), 0, 1)
    shape *= (np.maximum(f, 1.0) / 1000.0) ** tilt
    return np.fft.irfft(spec * shape, n)


def env(sec, a=0.005, d=0.3, curve=4.0):
    t = t_(sec)
    e = np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-curve * np.maximum(0, t - a) / max(d, 1e-4))
    return e


def tone(f, sec, kind='sine'):
    ph = 2 * np.pi * np.cumsum(np.full(int(SR * sec), f) if np.isscalar(f) else f) / SR
    if kind == 'tri':
        return 2 / np.pi * np.arcsin(np.sin(ph))
    return np.sin(ph)


# ---- motor (2 s, loop): fundamental 55 Hz + harmónicos, ronco modulado, assobio de turbina
t = t_(2.0)
eng = sum(a * np.sin(2 * np.pi * 55 * k * t + k) for k, a in ((1, 1.0), (2, 0.7), (3, 0.45), (4, 0.3), (6, 0.15), (8, 0.08)))
eng *= 0.75 + 0.25 * np.sin(2 * np.pi * 15 * t)
eng += 0.12 * np.sin(2 * np.pi * 880 * t) + 0.05 * np.sin(2 * np.pi * 1320 * t)
eng += 0.35 * band_noise(2.0, 60, 600, -0.5)
save('engine_loop', eng, 0.7)

# ---- boost (2 s, loop): sopro largo com pulsação
t = t_(2.0)
save('boost_loop', band_noise(2.0, 250, 4500, -0.2) * (0.8 + 0.2 * np.sin(2 * np.pi * 6 * t)) + 0.15 * np.sin(2 * np.pi * 110 * t), 0.7)

# ---- vento (3 s, loop)
t = t_(3.0)
save('wind_loop', band_noise(3.0, 150, 1400, -0.6) * (0.75 + 0.25 * np.sin(2 * np.pi * (1 / 3) * t)), 0.6)

# ---- impacto: baque + clang metálico inarmónico + estilhaço
sec = 0.6
t = t_(sec)
thump = np.sin(2 * np.pi * np.cumsum(np.linspace(130, 38, len(t))) / SR) * env(sec, 0.002, 0.18)
clang = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((523, 0.5), (811, 0.4), (1307, 0.3), (2113, 0.2))) * env(sec, 0.001, 0.22, 5)
crash = band_noise(sec, 800, 7000) * env(sec, 0.001, 0.06)
save('impact', thump * 1.2 + clang * 0.5 + crash * 0.6)

# ---- aterragem: baque curto
sec = 0.35
t = t_(sec)
save('land', np.sin(2 * np.pi * np.cumsum(np.linspace(90, 40, len(t))) / SR) * env(sec, 0.003, 0.12) + 0.3 * band_noise(sec, 100, 1500) * env(sec, 0.002, 0.05), 0.7)

# ---- explosão (nave destruída)
sec = 1.6
t = t_(sec)
save('explosion', band_noise(sec, 30, 2500, -0.8) * env(sec, 0.004, 0.55, 3) + 0.8 * np.sin(2 * np.pi * np.cumsum(np.linspace(70, 25, len(t))) / SR) * env(sec, 0.004, 0.6, 3))

# ---- interface
save('ui_move', tone(1900, 0.035) * env(0.035, 0.001, 0.012), 0.35)
save('ui_ok', np.concatenate([tone(660, 0.06, 'tri') * env(0.06, 0.002, 0.05), tone(990, 0.09, 'tri') * env(0.09, 0.002, 0.08)]), 0.45)
save('ui_back', np.concatenate([tone(660, 0.06, 'tri') * env(0.06, 0.002, 0.05), tone(440, 0.09, 'tri') * env(0.09, 0.002, 0.08)]), 0.45)

# ---- contagem e partida
save('beep', tone(880, 0.16, 'tri') * env(0.16, 0.003, 0.12, 3), 0.55)
sec = 0.6
save('go', (tone(1320, sec, 'tri') + 0.7 * tone(660, sec, 'tri') + 0.4 * tone(1980, sec)) * env(sec, 0.003, 0.4, 3), 0.65)

# ---- checkpoint, loot, extração, aviso
sec = 0.4
t = t_(sec)
save('checkpoint', (np.sin(2 * np.pi * 1046 * t) + 0.7 * np.sin(2 * np.pi * 1568 * t) * (t > 0.07)) * env(sec, 0.002, 0.25, 4), 0.5)
loot = np.zeros(int(SR * 0.5))
for k, f in enumerate((784, 988, 1175, 1568)):
    s = int(SR * 0.06 * k)
    seg = tone(f, 0.3, 'tri') * env(0.3, 0.002, 0.18, 4)
    loot[s:s + len(seg)] += seg[:len(loot) - s]
save('loot', loot, 0.55)
sec = 1.6
t = t_(sec)
ext = np.zeros(len(t))
for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
    s = int(SR * 0.12 * k)
    seg = (tone(f, sec - 0.12 * k, 'tri') + 0.3 * tone(f * 2, sec - 0.12 * k)) * env(sec - 0.12 * k, 0.01, 0.9, 2.5)
    ext[s:] += seg
save('extract', ext, 0.6)
w = np.concatenate([tone(196, 0.14, 'tri'), np.zeros(int(SR * 0.06)), tone(196, 0.14, 'tri')])
save('warning', w * 0.9 + 0.3 * np.sign(w) * 0.2, 0.5)

# ---- música ambiente (16 s, loop): pad Am – F – C – G com envelopes que somam 1 (periódico)
sec = 16.0
t = t_(sec)
chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (130.81, 196.0, 261.63), (196.0, 246.94, 293.66)]
pad = np.zeros(len(t))
for i, ch in enumerate(chords):
    c = 2 + i * 4.0                                     # centro de cada acorde (s)
    d = np.angle(np.exp(1j * 2 * np.pi * (t - c) / sec)) / (2 * np.pi) * sec   # distância circular
    win = np.where(np.abs(d) < 4.0, 0.5 + 0.5 * np.cos(np.pi * d / 4.0), 0.0)
    voice = np.zeros(len(t))
    for f in ch:
        for det in (-0.6, 0.0, 0.6):
            fr = round((f + det) * sec) / sec           # ciclos inteiros no loop
            voice += np.sin(2 * np.pi * fr * t) + 0.25 * np.sin(2 * np.pi * 2 * fr * t)
    bass = np.sin(2 * np.pi * round(ch[0] / 2 * sec) / sec * t)
    pad += win * (voice + 1.5 * bass)
pad += 0.25 * band_noise(sec, 200, 3000, -1.0)
save('ambient_loop', pad, 0.5)
