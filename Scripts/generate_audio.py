"""Generate short, non-looping engine, drift and nitro cues for the beta."""

import math
import os
import random
import struct
import wave


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "SourceArt", "Audio")
RATE = 48000


def write_wave(filename, samples, target_peak=0.35):
    os.makedirs(OUT, exist_ok=True)
    peak = max(1e-6, max(abs(sample) for sample in samples))
    scale = target_peak / peak
    pcm = bytearray()
    for sample in samples:
        value = int(max(-1.0, min(1.0, sample * scale)) * 32767.0)
        pcm.extend(struct.pack("<h", value))
    with wave.open(os.path.join(OUT, filename), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(RATE)
        target.writeframes(pcm)


def engine_loop():
    duration = 0.85
    count = int(RATE * duration)
    samples = []
    phase = 0.0
    rng = random.Random(4501)
    low = 0.0
    for index in range(count):
        t = index / RATE
        x = t / duration
        rpm = 46.0 + 26.0 * x
        phase += 2.0 * math.pi * rpm / RATE
        tone = math.sin(phase) * 0.62 + math.sin(phase * 2.0) * 0.16 + math.sin(phase * 3.0) * 0.05
        noise = rng.uniform(-1.0, 1.0)
        low += (noise - low) * 0.035
        envelope = math.sin(math.pi * x) ** 1.8
        samples.append(envelope * (tone + low * 0.10))
    write_wave("engine_loop.wav", samples, target_peak=0.32)


def drift_loop():
    duration = 0.55
    count = int(RATE * duration)
    rng = random.Random(1507)
    low = 0.0
    samples = []
    for index in range(count):
        x = index / count
        noise = rng.uniform(-1.0, 1.0)
        low += (noise - low) * 0.08
        envelope = math.sin(math.pi * x) ** 2.0
        samples.append(envelope * (noise - low * 0.55) * 0.45)
    write_wave("drift_loop.wav", samples, target_peak=0.26)


def nitro_burst():
    duration = 1.35
    count = int(RATE * duration)
    rng = random.Random(93021)
    samples = []
    phase = 0.0
    low = 0.0
    for index in range(count):
        t = index / RATE
        x = t / duration
        envelope = math.sin(math.pi * x) ** 1.7
        frequency = 90.0 + 420.0 * x * x
        phase += 2.0 * math.pi * frequency / RATE
        noise = rng.uniform(-1.0, 1.0)
        low += (noise - low) * 0.06
        whoosh = noise - low * 0.8
        samples.append(envelope * (0.52 * whoosh + 0.38 * math.sin(phase)
                                   + 0.10 * math.sin(phase * 0.5)))
    write_wave("nitro_burst.wav", samples, target_peak=0.38)


if __name__ == "__main__":
    engine_loop()
    drift_loop()
    nitro_burst()
    print("Generated ship audio in", OUT)
