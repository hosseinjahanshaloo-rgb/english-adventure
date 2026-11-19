"""Generates the game's sound effects as WAV files (run once: python make_sounds.py)."""
import math, struct, wave, random
from pathlib import Path

RATE = 22050
OUT = Path(__file__).parent / "sounds"


def tone(freq, dur, vol=0.5, kind="sine", slide=0.0):
    n = int(RATE * dur)
    out, phase = [], 0.0
    for i in range(n):
        t = i / n
        f = freq * (1 + slide * t)
        phase += 2 * math.pi * f / RATE
        if kind == "square":
            s = 1.0 if math.sin(phase) >= 0 else -1.0
            s *= 0.5
        elif kind == "saw":
            s = ((phase / math.pi) % 2) - 1
            s *= 0.5
        else:
            s = math.sin(phase) + 0.25 * math.sin(2 * phase) + 0.1 * math.sin(3 * phase)
        env = min(1, i / (RATE * 0.008)) * (1 - t) ** 1.5   # quick attack, smooth decay
        out.append(s * env * vol)
    return out


def silence(dur):
    return [0.0] * int(RATE * dur)


def save(name, samples):
    peak = max(1e-9, max(abs(s) for s in samples))
    scale = min(1.0, 0.9 / peak)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(s * scale * 32000)) for s in samples))


def seq(*parts):
    r = []
    for p in parts:
        r += p
    return r


C5, D5, E5, G5, A5, C6, E6 = 523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1318.5

OUT.mkdir(exist_ok=True)
save("click", tone(900, 0.05, 0.5))
save("flip", seq(tone(500, 0.05, 0.4, slide=0.6), tone(750, 0.06, 0.4)))
save("correct", seq(tone(C5, 0.09), tone(E5, 0.09), tone(G5, 0.16, 0.6)))
save("wrong", seq(tone(220, 0.14, 0.5, "saw"), tone(165, 0.26, 0.5, "saw", slide=-0.2)))
save("match", seq(tone(G5, 0.07), tone(C6, 0.14, 0.6)))
save("win", seq(tone(C5, 0.1), tone(E5, 0.1), tone(G5, 0.1), tone(C6, 0.1),
                silence(0.04), tone(G5, 0.08), tone(C6, 0.32, 0.7)))
save("lose", seq(tone(G5, 0.14), tone(E5, 0.14), tone(C5, 0.14), tone(165, 0.4, 0.5, "saw")))
save("badge", seq(tone(E5, 0.08), tone(G5, 0.08), tone(E6, 0.08), tone(C6, 0.08),
                  tone(E6, 0.08), tone(A5 * 2, 0.35, 0.6)))
save("levelup", seq(*[tone(f, 0.09, 0.55) for f in (C5, D5, E5, G5, A5, C6)], tone(E6, 0.4, 0.7)))
print("sounds written to", OUT)
