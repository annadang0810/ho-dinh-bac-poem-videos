"""Soft synthesized piano (Am-F-C-G, 3.6 s per chord) for 'Mùa đông thương mẹ'.
Length and voice ducking come from timing.json (music drops to ~25% while Hà Hồ is reading).
Usage: python3 music.py music.wav"""
import sys, os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TM = json.load(open(os.path.join(HERE, "timing.json")))
SR = 44100; DUR = TM["dur"]; n = int(SR * DUR); out = np.zeros(n)

def note(f, t0, L, amp):
    i0 = int(t0 * SR); m = min(int(L * SR), n - i0)
    if m <= 0: return
    t = np.arange(m) / SR
    w = sum(a * np.sin(2 * np.pi * f * k * t) for k, a in [(1, 1), (2, .3), (3, .1), (4, .04)])
    out[i0:i0 + m] += w * np.exp(-t * 1.1) * (1 - np.exp(-t * 60)) * amp
m = lambda x: 440 * 2 ** ((x - 69) / 12)
prog = [[45, 57, 60, 64], [41, 53, 57, 60], [48, 55, 60, 64], [43, 55, 59, 62]]
mel = [76, 74, 72, 71, 72, 69, 67, 69, 72, 71, 67, 64, 67, 69, 71, 72]
step = 3.6; c = 0; t = 0.4
while t < DUR - 3:
    ch = prog[c % 4]
    note(m(ch[0] - 12), t, step + 2, .20)
    for j, p in enumerate(ch[1:]): note(m(p), t + 0.25 * j, step + 1.5, .08)
    if 4 < t < DUR - 8:
        for k in range(2): note(m(mel[(c * 2 + k) % 16]), t + 1.0 + k * 1.6, 3, .07)
    t += step; c += 1
for d, g in [(0.09, .4), (0.17, .3), (0.29, .22), (0.43, .15), (0.61, .1)]:
    k = int(d * SR); out[k:] += out[:-k] * g
tt = np.arange(n) / SR
out *= np.minimum(1, np.minimum(tt / 1.5, (DUR - tt) / 3))
out = out / np.abs(out).max() * 0.55
# duck under the voice (smooth 0.6 s ramps)
duck = np.ones(n)
for a, b in TM.get("voice_spans", []):
    duck = np.minimum(duck, 1 - 0.75 * np.clip(np.minimum((tt - (a - 0.6)) / 0.6, ((b + 0.8) - tt) / 0.6), 0, 1))
out *= duck
st = np.stack([out, np.roll(out, 400)], 1)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "music.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
