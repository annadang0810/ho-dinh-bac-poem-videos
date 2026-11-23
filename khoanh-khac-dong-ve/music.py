"""Synthesized Vietnamese-flavoured background music (no samples, no copyright claims).

Styles:
  piano  - soft piano, Am-F-C-G (the music used for the first videos)
  tranh  - đàn tranh (16-string zither): plucked pentatonic melody with bends, rolled arpeggios, soft bass
  sao    - sáo trúc (bamboo flute) melody over đàn tranh arpeggios

Length and voice ducking come from timing.json (music drops to ~25% while Hà Hồ is reading).
Usage: python3 music.py music.wav [style] [seconds]      (seconds overrides the length, for demos)
"""
import sys, os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else "music.wav"
STYLE = sys.argv[2] if len(sys.argv) > 2 else "tranh"
TM = json.load(open(os.path.join(HERE, "timing.json"))) if os.path.exists(os.path.join(HERE, "timing.json")) else {}
DUR = float(sys.argv[3]) if len(sys.argv) > 3 else TM.get("dur", 75.0)
SR = 44100; n = int(SR * DUR); out = np.zeros(n)
rng = np.random.default_rng(7)
mf = lambda x: 440 * 2 ** ((x - 69) / 12)

def add(sig, t0, amp=1.0):
    i0 = int(t0 * SR)
    if i0 >= n: return
    m = min(len(sig), n - i0)
    out[i0:i0 + m] += sig[:m] * amp

def piano(f, L):
    t = np.arange(int(L * SR)) / SR
    w = sum(a * np.sin(2 * np.pi * f * k * t) for k, a in [(1, 1), (2, .3), (3, .1), (4, .04)])
    return w * np.exp(-t * 1.1) * (1 - np.exp(-t * 60))

def tranh(f, L=3.0, bend=0.0):
    """plucked steel string: bright attack, upper partials die fast; optional nhấn (pitch bend up after the pluck)"""
    t = np.arange(int(L * SR)) / SR
    fb = f * (1 + bend * np.clip((t - 0.18) / 0.25, 0, 1) * (1 - np.clip((t - 1.0) / 0.4, 0, 1)) + 0.0015 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t - 0.4, 0, 1))
    ph = 2 * np.pi * np.cumsum(fb) / SR
    w = sum((0.9 / k ** 0.9) * np.sin(k * ph + k) * np.exp(-t * (1.4 + 1.1 * k)) for k in range(1, 9))
    return w * (1 - np.exp(-t * 400))

def sao(f, L):
    """bamboo flute: breathy sine with vibrato that grows into the note"""
    t = np.arange(int(L * SR)) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.3) / 0.5, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    env = np.clip(t / 0.12, 0, 1) * np.clip((L - t) / 0.35, 0, 1)
    tone = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    breath = np.convolve(rng.standard_normal(len(t)), np.ones(12) / 12, "same") * 0.05
    return (tone + breath) * env

if STYLE == "piano":
    prog = [[45, 57, 60, 64], [41, 53, 57, 60], [48, 55, 60, 64], [43, 55, 59, 62]]
    mel = [76, 74, 72, 71, 72, 69, 67, 69, 72, 71, 67, 64, 67, 69, 71, 72]
    step = 3.6; c = 0; t = 0.4
    while t < DUR - 3:
        ch = prog[c % 4]
        add(piano(mf(ch[0] - 12), step + 2), t, .20)
        for j, p in enumerate(ch[1:]): add(piano(mf(p), step + 1.5), t + 0.25 * j, .08)
        if 4 < t < DUR - 8:
            for k in range(2): add(piano(mf(mel[(c * 2 + k) % 16]), 3), t + 1.0 + k * 1.6, .07)
        t += step; c += 1
else:
    # D pentatonic (D F G A C), the colour of northern folk tunes; slow, 1 beat = 0.9 s
    B = 0.9
    # (scale degree as midi, beats, bend) — a calm, sighing melody in 4 phrases
    PHRASES = [
        [(74, 1, 0), (72, .5, 0), (69, .5, 0), (72, 2, .02), (69, 1, 0), (67, 1, 0), (69, 2, 0)],
        [(67, 1, 0), (69, .5, 0), (72, .5, 0), (74, 2, .03), (77, 1, 0), (74, 1, 0), (72, 2, 0)],
        [(74, 1, 0), (77, .5, 0), (79, .5, 0), (77, 2, .02), (74, 1, 0), (72, 1, 0), (69, 2, 0)],
        [(67, 1, 0), (65, .5, 0), (67, .5, 0), (69, 2, .03), (67, 1, 0), (65, 1, 0), (62, 2, 0)],
    ]
    BASS = [50, 45, 48, 43]          # D, A, C, G (one per phrase)
    ROLL = {50: [62, 65, 69, 74], 45: [57, 62, 64, 69], 48: [60, 62, 67, 72], 43: [55, 62, 65, 67]}
    t = 0.5; p = 0
    while t < DUR - 4:
        bass = BASS[p % 4]
        add(tranh(mf(bass - 12), 6.0), t, .22)
        for half in (0, 4):                                    # rolled arpeggios (rải), twice per phrase
            for j, q in enumerate(ROLL[bass]):
                add(tranh(mf(q), 3.0), t + half * B + j * 0.11, .07)
        if 3 < t < DUR - 10:
            tt = t
            for (note, beats, bend) in PHRASES[p % 4]:
                if STYLE == "sao" and (p // 4) % 2 == 0:
                    add(sao(mf(note), beats * B * 1.05), tt, .16)
                else:
                    add(tranh(mf(note), 3.2, bend), tt, .14)
                    if beats >= 2: add(tranh(mf(note), 2.0), tt + beats * B * 0.5, .05)   # soft re-pluck
                tt += beats * B
        t += 8 * B; p += 1

# small hall reverb
for d, g in [(0.07, .35), (0.13, .28), (0.23, .22), (0.37, .16), (0.53, .11), (0.79, .07)]:
    k = int(d * SR); out[k:] += out[:-k] * g
tt = np.arange(n) / SR
out *= np.minimum(1, np.minimum(tt / 1.5, (DUR - tt) / 3))
out = out / np.abs(out).max() * 0.55
duck = np.ones(n)
for a, b in TM.get("voice_spans", []) if len(sys.argv) <= 3 else []:
    duck = np.minimum(duck, 1 - 0.75 * np.clip(np.minimum((tt - (a - 0.6)) / 0.6, ((b + 0.8) - tt) / 0.6), 0, 1))
out *= duck
st = np.stack([out, np.roll(out, 400)], 1)
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
