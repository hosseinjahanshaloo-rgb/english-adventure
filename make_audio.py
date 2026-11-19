"""Generates pronunciation audio (audio/<slug>.ogg) for every word and sentence in data/lesson*.json.
Needs (Linux):  sudo apt install espeak-ng mbrola mbrola-us1 vorbis-tools
Run again after adding or editing lessons:  python make_audio.py
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

BASE = Path(__file__).parent
OUT = BASE / "audio"
VOICE, SPEED = "mb-us1", "120"      # mb-us1 = US English female; slower speed for learners
FIX = {"read": "[[r'i:d]]", "use": "[[j'u:z]]", "wind": "[[w'Ind]]"}   # words espeak may misread


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:80]


def main():
    OUT.mkdir(exist_ok=True)
    texts = []
    for p in sorted((BASE / "data").glob("lesson*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        texts += [w["en"] for w in d["words"]] + [s["en"] for s in d["sentences"]]
    done = set()
    for t in texts:
        name = slug(t)
        if name in done:
            continue
        done.add(name)
        say = FIX.get(t.lower(), t)
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "x.wav"
            subprocess.run(["espeak-ng", "-v", VOICE, "-s", SPEED, "-w", str(wav), say], check=True)
            subprocess.run(["oggenc", "-q", "3", "-Q", "-o", str(OUT / f"{name}.ogg"), str(wav)], check=True)
    print(len(done), "audio files in", OUT)


if __name__ == "__main__":
    main()
