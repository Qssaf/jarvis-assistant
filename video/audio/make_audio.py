"""Writes the trailer's soundtrack and sound effects into public/audio (all made here: nothing licensed, nothing
downloaded). 100 BPM, D minor; the bars line up with the scene cuts in src/timing.ts.

    manim/.venv/bin/python audio/make_audio.py
"""
import os
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BEAT = 0.6
BAR = 4 * BEAT
LENGTH = 46.2
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "audio")
rng = np.random.default_rng(7)

PAD = {"Dsus2": [38, 45, 52, 57, 62], "Dm9": [50, 57, 60, 64, 65], "Bbmaj7": [46, 53, 57, 62, 65],
       "C69": [48, 55, 57, 62, 64], "Gm7": [43, 50, 53, 58, 62, 65], "Cadd9": [48, 55, 60, 62, 64],
       "Fmaj9": [41, 48, 52, 55, 57, 60]}
ARP = {"Dsus2": [62, 64, 69, 74, 76], "Dm9": [62, 65, 69, 72, 76], "Bbmaj7": [62, 65, 69, 70, 74],
       "C69": [60, 64, 67, 69, 74], "Gm7": [62, 65, 67, 70, 74], "Cadd9": [60, 62, 64, 67, 72],
       "Fmaj9": [60, 64, 67, 69, 72]}
ROOT = {"Dsus2": 38, "Dm9": 38, "Bbmaj7": 34, "C69": 36, "Gm7": 43, "Cadd9": 36, "Fmaj9": 41}
BARS = ["Dsus2", "Dsus2", "Dm9", "Dm9", "Bbmaj7", "Bbmaj7", "C69", "Dm9", "Dm9", "Bbmaj7", "C69", "Gm7", "Gm7",
        "Cadd9", "Dm9", "Bbmaj7", "Cadd9", "Fmaj9", "Fmaj9", "Fmaj9"]
DRIVE = {7, 8, 9, 10, 14, 15, 16}   # bars with the pulse: the window and the feature cuts
HITS = [4.8, 16.8, 33.6, 40.8]      # scene changes that land


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def t_of(n):
    return np.arange(n) / SR


def place(mix, sound, at, gain=1.0):
    """Adds a mono or stereo `sound` into the stereo `mix` at `at` seconds."""
    i = int(round(at * SR))
    if i >= len(mix):
        return
    if sound.ndim == 1:
        sound = np.stack([sound, sound], axis=1)
    sound = sound[: len(mix) - i]
    mix[i:i + len(sound)] += sound * gain


def band(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)


def lowpass(x, cut):
    return sosfilt(butter(2, cut, btype="low", fs=SR, output="sos"), x, axis=0)


def fade(n, attack, release):
    env = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    env[:a] = 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    env[n - r:] = 0.5 + 0.5 * np.cos(np.pi * np.arange(r) / r)
    return env


def pad(notes, seconds, cutoff=1700.0):
    """A warm stereo pad: three slightly detuned saws per note, built from sines so nothing aliases."""
    n = int(seconds * SR)
    t = t_of(n)
    out = np.zeros((n, 2))
    for note in notes:
        for side, cents in ((0, (-7, 0, 5)), (1, (-5, 0, 7))):
            for c in cents:
                f = hz(note) * 2 ** (c / 1200)
                for k in range(1, min(14, int(7000 / f)) + 1):
                    amp = (1 / k) / np.sqrt(1 + (k * f / cutoff) ** 4)
                    out[:, side] += amp * np.sin(2 * np.pi * k * f * t + rng.uniform(0, 2 * np.pi))
    return out / (len(notes) * 3)


def pluck(note, seconds=1.1):
    t = t_of(int(seconds * SR))
    f = hz(note)
    tone = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t / 0.05) + 0.1 * np.sin(6 * np.pi * f * t) * np.exp(-t / 0.03)
    return tone * np.exp(-t / 0.2) * np.minimum(1, t / 0.003)


def kick():
    t = t_of(int(0.4 * SR))
    phase = 2 * np.pi * np.cumsum(46 + 70 * np.exp(-t / 0.028)) / SR
    return np.sin(phase) * np.exp(-t / 0.15) * np.minimum(1, t / 0.002)


def hat():
    n = int(0.06 * SR)
    noise = np.diff(np.diff(rng.standard_normal(n + 2)))
    return noise * np.exp(-t_of(n) / 0.014) * 0.25


def sweep(seconds, rising=True, shape=None):
    """Noise that moves through three bands: a riser (builds up) or a whoosh (a bell of loudness)."""
    n = int(seconds * SR)
    x = np.linspace(0, 1, n)
    if not rising:
        x = x  # (a whoosh also climbs; its loudness is what differs)
    noise = rng.standard_normal((n, 2))
    lows, mids, highs = (np.stack([band(noise[:, s], lo, hi) for s in (0, 1)], axis=1)
                         for lo, hi in ((180, 700), (700, 2600), (2600, 9000)))
    w = lambda centre: np.exp(-((x - centre) / 0.33) ** 2)[:, None]  # noqa: E731
    out = lows * w(0.1) + mids * w(0.5) * 0.8 + highs * w(0.95) * 0.6
    env = x ** 2.2 if shape is None else shape(x)
    return out * env[:, None]


def boom(seconds=1.6):
    t = t_of(int(seconds * SR))
    low = np.sin(2 * np.pi * np.cumsum(42 + 26 * np.exp(-t / 0.08)) / SR) * np.exp(-t / 0.5)
    air = lowpass(rng.standard_normal((len(t), 2)), 900) * np.exp(-t / 0.25)[:, None] * 0.5
    return low[:, None] * 0.9 + air


def bell(notes, gap=0.09, decay=0.55, seconds=1.4):
    out = np.zeros(int(seconds * SR))
    for i, note in enumerate(notes):
        t = t_of(len(out) - int(i * gap * SR))
        f = hz(note)
        tone = (np.sin(2 * np.pi * f * t) + 0.22 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t / 0.08)) * np.exp(-t / decay) * np.minimum(1, t / 0.004)
        out[int(i * gap * SR):] += tone
    return out


def reverb(x, seconds=2.6, decay=0.75, wet=0.22):
    n = int(seconds * SR)
    tail = lowpass(rng.standard_normal((n, 2)), 5200) * np.exp(-t_of(n) / decay)[:, None]
    tail[: int(0.012 * SR)] = 0  # (a short gap before the room answers)
    tail /= np.sqrt((tail ** 2).sum(axis=0))
    return x + wet * np.stack([fftconvolve(x[:, s], tail[:, s])[: len(x)] for s in (0, 1)], axis=1)


def save(name, x, peak=0.7):
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    x = x / np.abs(x).max() * peak
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((x * 32767).astype("<i2").tobytes())
    rms = np.sqrt((x ** 2).mean())
    print(f"{name}: {len(x) / SR:.2f} s, peak {20 * np.log10(np.abs(x).max()):.1f} dB, rms {20 * np.log10(rms):.1f} dB")


def music():
    n = int(LENGTH * SR)
    pads, bass, arps, drums, fx = (np.zeros((n, 2)) for _ in range(5))
    duck = np.ones(n)  # the pad and bass dip under each kick, then swell back

    # the pad and the bass: one stretch per run of bars on the same chord
    bar = 0
    while bar < len(BARS):
        end = bar
        while end + 1 < len(BARS) and BARS[end + 1] == BARS[bar]:
            end += 1
        start, stop = bar * BAR - 0.35, min((end + 1) * BAR + 0.75, LENGTH)
        start = max(start, 0)
        seconds = stop - start
        level = 0.55 if bar < 2 else 1.0
        chord = pad(PAD[BARS[bar]], seconds) * fade(int(seconds * SR), min(1.1, seconds / 2), min(1.1, seconds / 2))[:, None]
        place(pads, chord, start, level)
        if bar >= 2:
            t = t_of(int(seconds * SR))
            f = hz(ROOT[BARS[bar]])
            low = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * fade(len(t), 0.25, min(0.9, seconds / 2))
            place(bass, low, start, 0.9)
        bar = end + 1

    for bar, name in enumerate(BARS[:19]):
        t0 = bar * BAR
        # the arpeggio: eighth notes up and down the chord, with an echo a dotted eighth later
        if 2 <= bar <= 17:
            level = (0.35 + 0.3 * (bar - 2)) if bar < 4 else 1.0 if bar in DRIVE else 0.6
            steps = (0, 1, 2, 3, 4, 3, 2, 1) if bar < 17 else (0, 2, 4)
            for i, step in enumerate(steps):
                at = t0 + i * BEAT / 2 * (1 if bar < 17 else 2)
                note = pluck(ARP[name][step]) * level * (1.0 if i % 2 == 0 else 0.72)
                pan = 0.35 if i % 2 else -0.35
                for echo in range(4):
                    side = pan if echo % 2 == 0 else -pan
                    stereo = np.stack([note * (1 - max(0, side)), note * (1 + min(0, side))], axis=1)
                    place(arps, stereo, at + echo * 0.45, 0.4 ** echo)
        # the pulse
        beats = range(4) if bar in DRIVE else (0,) if 11 <= bar <= 13 else ()
        for b in beats:
            at = t0 + b * BEAT
            place(drums, kick(), at, 0.9 if bar in DRIVE else 0.55)
            i = int(at * SR)
            t = t_of(min(int(0.5 * SR), n - i))
            duck[i:i + len(t)] = np.minimum(duck[i:i + len(t)], 1 - 0.32 * np.exp(-t / 0.16))
            if bar in DRIVE:
                place(drums, hat(), at + BEAT / 2, 0.5)

    for at in (16.8, 33.6):
        place(fx, sweep(1.6), at - 1.6, 0.16)
    for at in HITS:
        place(fx, boom(), at, 0.5 if at != 40.8 else 0.7)

    mix = (pads * 0.5 + bass[:, :1] * 0.32) * duck[:, None] + arps * 0.16 + drums * 0.5 + fx
    mix = reverb(mix)
    mix = np.tanh(mix * 1.15)
    mix *= fade(n, 0.4, 2.6)[:, None]
    return mix


def main():
    save("music.wav", music(), 0.8)
    # the reactor lighting up: a low swell, air rising, then a bright ring as the core catches
    t = t_of(int(2.6 * SR))
    swell = np.sin(2 * np.pi * np.cumsum(40 + 28 * t / 2.6) / SR) * np.clip(t / 1.5, 0, 1) ** 2 * np.exp(-np.clip(t - 1.5, 0, None) / 0.5)
    ignite = swell[:, None] * 0.8 + sweep(2.6, shape=lambda x: np.clip(x / 0.58, 0, 1) ** 2.5 * np.exp(-np.clip(x - 0.58, 0, None) / 0.12)) * 0.35
    place(ignite, bell([74, 81, 86], gap=0.0, decay=0.7, seconds=1.1), 1.5, 0.3)
    save("ignite.wav", reverb(ignite, wet=0.3), 0.75)
    save("whoosh.wav", sweep(0.7, shape=lambda x: np.sin(np.pi * x) ** 2), 0.5)
    save("wake.wav", reverb(np.pad(bell([81, 88]), (0, SR))[:, None].repeat(2, axis=1), wet=0.25), 0.6)
    save("done.wav", reverb(np.pad(bell([88, 93], gap=0.07, decay=0.4), (0, SR))[:, None].repeat(2, axis=1), wet=0.25), 0.5)
    t = t_of(int(0.05 * SR))
    save("tick.wav", np.sin(2 * np.pi * 1900 * t) * np.exp(-t / 0.006) * np.minimum(1, t / 0.0005), 0.35)


if __name__ == "__main__":
    main()
