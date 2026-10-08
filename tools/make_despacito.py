"""Build Despacito (chorus) as a .gtmusic file for Cernodile's simulator.

Melody: letter-notes transcription of the chorus (piano-keyboard-guide.com).
Chords: the song's single loop Bm - G - D - A, one bar each, at 89 BPM.
Grid semantics, verified against Player.js/Constants.js:
  token = <instrument><note letter><accidental>   e.g. Pb-  PC#  DB-
  the letter picks the row and "#"/"b" moves the pitch one semitone:
    c=1 d=2 e=3 f=4 g=5 a=6 b=7  = C4..B4      C=8 D=9 E=10 F=11 G=12 A=13 B=14 = C5..B5
  one column = one 16th note; one note per row per column.
"""

import pathlib

BPM = 89
BAR = 16   # sixteenths per 4/4 bar
BARS = 8   # the chorus, twice

ROW = {"c": 1, "d": 2, "e": 3, "f": 4, "g": 5, "a": 6, "b": 7,
       "C": 8, "D": 9, "E": 10, "F": 11, "G": 12, "A": 13, "B": 14}


def tok(inst, note, acc="-"):
    """inst: P (piano) / B (bass) / D (drum); note = the natural row the pitch sits on."""
    return inst + note + acc


# Melody, 4 bars. The [4][5][3] sixteenth grouping mirrors the syllable grouping in
# the transcription: "Des-pa-ci-to" | "quie-ro res-pi-rar tu" + "cue-llo des-pa-ci-to".
CHORUS = [
    [(0, "D", "-"), (4, "C", "#"), (8, "b", "-"), (12, "f", "#")],
    [(0, "f", "#"), (1, "f", "#"), (2, "f", "#"), (3, "f", "#"),
     (5, "b", "-"), (6, "b", "-"), (7, "b", "-"), (8, "b", "-"), (9, "b", "-"),
     (11, "a", "-"), (12, "b", "-"), (13, "g", "-")],
    [(0, "g", "-"), (1, "g", "-"), (2, "g", "-"), (3, "g", "-"),
     (5, "b", "-"), (6, "b", "-"), (7, "b", "-"), (8, "b", "-"), (9, "b", "-"),
     (11, "C", "#"), (12, "D", "-"), (13, "a", "-")],
    [(0, "a", "-"), (1, "a", "-"), (2, "a", "-"), (3, "a", "-"),
     (5, "D", "-"), (6, "D", "-"), (7, "D", "-"), (8, "D", "-"), (9, "D", "-"),
     (11, "E", "-"), (12, "E", "-"), (13, "C", "#")],
]

BASS_ROOT = ["b", "g", "d", "a"]                    # Bm, G, D, A
CHORDS = [[("b", "-"), ("D", "-"), ("F", "#")],    # Bm: B4 D5 F#5
          [("g", "-"), ("b", "-"), ("D", "-")],     # G : G4 B4 D5
          [("a", "-"), ("D", "-"), ("F", "#")],     # D : A4 D5 F#5
          [("a", "-"), ("C", "#"), ("E", "-")]]     # A : A4 C#5 E5
STABS = [2, 6, 10, 14]                              # off-beat comping
BASS_HITS = [0, 6, 8, 14]

# Drums picked by measuring the real samples (zero-crossing rate per second):
# drum_0 = kick (70), drum_1 = snare (1700), drum_2 = closed hat (2876), drum_6 = open (3176).
# A drum's sound is its row mod 7, so each sound has two usable rows - take whichever
# row the melody is not already using in that column.
KICK, SNARE, HAT, OPEN = ["B", "b"], ["A", "a"], ["G", "g"], ["C", "c"]
BEAT = {0: KICK, 2: HAT, 4: SNARE, 6: HAT, 8: KICK, 10: HAT, 12: SNARE, 14: HAT}


def build():
    cols = [[None] * 15 for _ in range(BARS * BAR)]   # field 0 is unused, 1..14 = rows

    def put(col, cands):
        """cands = [(row, token), ...]: first free row wins (the melody is placed first)."""
        for row, token in cands:
            if cols[col][row] is None:
                cols[col][row] = token
                return True
        return False

    for bar in range(BARS):
        base, loop = bar * BAR, bar % 4
        for off, note, acc in CHORUS[loop]:                       # melody first: never displaced
            cols[base + off][ROW[note]] = tok("P", note, acc)
        for off in BASS_HITS:                                     # bass root
            note = BASS_ROOT[loop]
            put(base + off, [(ROW[note], tok("B", note))])
        for off, sounds in BEAT.items():                          # one drum per 16th
            cands = OPEN if base + off == 0 else sounds           # crash on the first hit
            put(base + off, [(ROW[n], tok("D", n)) for n in cands])
        for off in STABS:                                         # off-beat comping
            for note, acc in CHORDS[loop]:
                put(base + off, [(ROW[note], tok("P", note, acc))])
    return cols


def main(path="/home/jem/Desktop/projects/gtmusic/GTMusicSim/songs/despacito.gtmusic"):
    cols = build()
    body = "\n".join(",".join(c or "" for c in col) for col in cols)
    out = pathlib.Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"%cernmusicsim;\nbpm={BPM}\n{body}", encoding="utf-8")
    return out, cols


if __name__ == "__main__":
    out, cols = main()
    # self-check: shape, one note per row per column, and every melody note intact
    assert len(cols) == BARS * BAR
    for col in cols:
        assert len(col) == 15 and all(c is None or len(c) == 3 for c in col)
    for bar in range(BARS):
        base, loop = bar * BAR, bar % 4
        missed = [(off, note) for off, note, acc in CHORUS[loop]
                  if cols[base + off][ROW[note]] != tok("P", note, acc)]
        assert not missed, (bar, missed)
        mel = sum(1 for c in cols[base:base + BAR] for n in c if n and n[0] == "P")
        print(f"  bar {bar + 1}: {len(CHORUS[loop])} melody notes kept, {mel} piano notes with chords")
    print(f"{out}: {len(cols)} columns, {sum(1 for c in cols for n in c if n)} notes, "
          f"bpm {BPM}, {len(cols) * 60000 / (4 * BPM) / 1000:.1f}s")
