"""Generate placeholder WAVs for GTMusicSim/notes/.

Constants.js fetches notes/{piano,bass}_0..25.wav and notes/drum_0..6.wav, so
without these the page 404s and every decodeAudioData call throws. These are
synthesised stand-ins, not the real Growtopia samples - drop the genuine files
over them when you have a Growtopia install.

    python3 tools/make_notes.py
"""

import array
import math
import random
import wave
from pathlib import Path

SR = 22050
OUT = Path(__file__).resolve().parent.parent / "GTMusicSim" / "notes"

PIANO_BASE = 261.626  # C4
BASS_BASE = 130.813  # C3


def semitone(base, n):
    """File index -> pitch. In Constants.js file _1 is C, _3 D, _5 E, _6 F, _8 G,
    _10 A, _12 B, _13 C (octave up), and the flat files sit between them (_2 = Db),
    so index n is n-1 semitones above the base C."""
    return base * (2.0 ** ((n - 1) / 12.0))


def synth(freq, dur, harm=(1.0,), decay=3.0, noise=0.0, drop=0.0, seed=0):
    n = int(SR * dur)
    rnd = random.Random(seed)
    out = [0.0] * n
    phase = 0.0
    for i in range(n):
        t = i / SR
        if drop:
            f = freq * (1.0 + drop * math.exp(-t * 30.0))
        else:
            f = freq
        phase += 2 * math.pi * f / SR
        s = sum(amp * math.sin(phase * h) for h, amp in enumerate(harm, start=1))
        if noise:
            s += noise * (rnd.random() * 2.0 - 1.0)
        attack = min(1.0, t * 200.0)  # ~5ms ramp, avoids a click
        out[i] = math.tanh(s * 0.8) * math.exp(-decay * t) * attack
    return out


def write_wav(path, samples):
    peak = max(abs(s) for s in samples) or 1.0
    scale = 0.85 / peak
    pcm = array.array("h", (int(max(-1.0, min(1.0, s * scale)) * 32767) for s in samples))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def piano(n):
    return synth(semitone(PIANO_BASE, n), 1.5, harm=(1.0, 0.5, 0.25, 0.12), decay=3.0, seed=n)


def bass(n):
    return synth(semitone(BASS_BASE, n), 1.8, harm=(1.0, 0.35, 0.15), decay=2.0, seed=100 + n)


def drum(n):
    # 7 toms/kicks: pitch rises and the noise layer thickens with the index
    return synth(80 * (2.0 ** (n / 6.0)), 0.5, harm=(1.0, 0.4), decay=14.0,
                 noise=0.15 + 0.1 * n, drop=0.8, seed=200 + n)


def plan():
    """(filename, samples) for every file Constants.js asks for. Synthesis is lazy:
    only the files that are actually missing get built."""
    for n in range(26):
        yield f"piano_{n}.wav", lambda n=n: piano(n)
        yield f"bass_{n}.wav", lambda n=n: bass(n)
    for n in range(7):
        yield f"drum_{n}.wav", lambda n=n: drum(n)


def main(force=False):
    OUT.mkdir(parents=True, exist_ok=True)
    written, skipped = [], []
    for name, build in plan():
        path = OUT / name
        if path.exists() and not force:
            skipped.append(name)
            continue
        write_wav(path, build())
        written.append(name)
    if skipped:
        print(f"kept {len(skipped)} existing note(s) (real Growtopia samples win) - pass --force to overwrite")
    return written


def peak_of(path):
    with wave.open(str(path), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, SR)
        frames = array.array("h")
        frames.frombytes(w.readframes(w.getnframes()))
    return max(abs(f) for f in frames) / 32767


def pitch_of(path, span=0.3):
    """Zero-crossing estimate of the fundamental - enough to catch an off-by-an-octave.
    Uses the span between the first and last crossing so sample quantisation drops out."""
    with wave.open(str(path), "rb") as w:
        frames = array.array("h")
        frames.frombytes(w.readframes(int(SR * span)))
    idx = [i for i, (a, b) in enumerate(zip(frames, frames[1:])) if a <= 0 < b]
    assert len(idx) > 4, path
    return (len(idx) - 1) * SR / (idx[-1] - idx[0])


if __name__ == "__main__":
    import sys

    names = main(force="--force" in sys.argv)
    if not names:
        print(f"nothing written, {OUT} already has notes")
        raise SystemExit
    for name in ("piano_0.wav", "piano_24.wav", "bass_25.wav", "drum_6.wav"):
        peak = peak_of(OUT / name)
        assert peak > 0.5, (name, peak)
        print(f"  {name}: peak {peak:.2f}   {(OUT / name).stat().st_size // 1024} KiB")
    # ZCR over-counts on a harmonic tone (piano_1 reads ~7% sharp), so check the
    # ratios - those cancel the bias - plus a loose absolute band for octave errors.
    p0, p1, p13 = (pitch_of(OUT / f"piano_{n}.wav") for n in (0, 1, 13))
    assert abs(p13 / p1 - 2.0) < 0.06, (p1, p13)  # _13 is an octave above _1
    assert abs(p1 / p0 - 2 ** (1 / 12)) < 0.03, (p0, p1)  # _0 is the semitone below
    assert 220 < p1 < 300, p1  # ...and _1 sits around C4
    print(f"  piano_0/1/13 = {p0:.0f}/{p1:.0f}/{p13:.0f} Hz by ZCR")
    print(f"wrote {len(names)} placeholder notes to {OUT}")
