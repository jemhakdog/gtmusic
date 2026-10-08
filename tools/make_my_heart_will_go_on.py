"""Build My Heart Will Go On (verse + chorus) as a .gtmusic file.

Melody: letter-notes transcriptions that agree with each other - noobnotes (key of G, same
key as the earlier draft) and piano-keyboard-guide (key of E, same tune transposed).
Chords: verse G D | C G D, chorus Em D C D (chords.vip, akordium and pianowithnate agree).

Grid semantics (verified against Player.js/Constants.js):
  token = <instrument><note letter><accidental>; the letter picks the row and #/b shifts
  the pitch one semitone:
    c=1 d=2 e=3 f=4 g=5 a=6 b=7  = C4..B4      C=8 D=9 E=10 F=11 G=12 A=13 B=14 = C5..B5
  one column = one 16th note, one note per row per column, 15 comma-separated fields.
"""

import pathlib

BPM = 100
BAR = 16
BARS_PER_PHRASE = 2

ROWS = {"c": 1, "d": 2, "e": 3, "f": 4, "g": 5, "a": 6, "b": 7,
        "C": 8, "D": 9, "E": 10, "F": 11, "G": 12, "A": 13, "B": 14}

# pitch name -> (row letter, accidental)
PITCH = {
    "C4": ("c", "-"), "D4": ("d", "-"), "E4": ("e", "-"), "F#4": ("f", "#"), "G4": ("g", "-"),
    "A4": ("a", "-"), "B4": ("b", "-"), "C5": ("C", "-"), "D5": ("D", "-"), "E5": ("E", "-"),
}

# (rhythm unit in columns, melody), 4 = quarter notes, 2 = eighths. Lyric per phrase below.
PHRASES = [
    (4, ["G4", "G4", "G4", "G4", "F#4", "G4"]),                      # Every night in my dreams
    (4, ["G4", "F#4", "G4", "A4", "B4", "A4"]),                      # I see you, I feel you
    (4, ["G4", "G4", "G4", "G4", "F#4", "G4", "G4", "D5"]),          # That is how I know you go on
    (2, ["G4", "A4", "D5", "D5", "C5", "B4", "A4"]),                 # Near, far, wherever you are
    (2, ["B4", "C5", "B4", "A4", "G4", "F#4", "G4", "G4", "D5"]),    # I believe that the heart does go on
    (2, ["G4", "A4", "D5", "D5", "C5", "B4", "A4"]),                 # Once more you open the door
    (2, ["B4", "C5", "B4", "A4", "G4", "F#4", "G4"]),                # And you're here in my heart and
    (2, ["G4", "F#4", "G4", "A4", "B4", "A4", "G4"]),                # my heart will go on and on
]

HARMONY = [["G", "D"], ["C", "G"], ["G", "D"],
           ["Em", "D"], ["C", "D"], ["Em", "D"], ["C", "D"], ["G", "D"]]

CHORDS = {                                  # voicings sit just under the melody
    "G": ["G4", "B4", "D5"],
    "D": ["F#4", "A4", "D5"],
    "C": ["E4", "G4", "C5"],
    "Em": ["E4", "G4", "B4"],
}
BASS_ROOT = {"G": "g", "D": "d", "C": "c", "Em": "e"}   # lowercase = the bass's own low octave
# A row holds one note per column, and the bass root shares its row letter with the piano
# (Bg- and Pg- both want row 5), so pick the first free column of each bar for the two hits.
BASS_HIT_PREF = [0, 8, 2, 10, 4, 12, 6, 14]
CHORD_HITS = [0, 8]

# Drums measured from the real samples (ZCR/s): drum_0 kick(70), drum_1 snare(1700),
# drum_2 hat(2876). A drum's sound is its row mod 7, so each has a lower and an upper row.
KICK, SNARE, HAT = ["B", "b"], ["A", "a"], ["G", "g"]
BEAT = {0: KICK, 4: SNARE, 8: KICK, 12: SNARE, 2: HAT, 6: HAT, 10: HAT, 14: HAT}


def ptok(pitch):
    """Piano token for a pitch name."""
    letter, acc = PITCH[pitch]
    return "P" + letter + acc


def build():
    cols = [[None] * 15 for _ in range(len(PHRASES) * BARS_PER_PHRASE * BAR)]  # 0 unused, 1..14 rows

    def put(col, cands):
        """cands = [(row, token), ...]: first free row wins. The melody is placed first."""
        for r, token in cands:
            if cols[col][r] is None:
                cols[col][r] = token
                return True
        return False

    for i, (unit, melody) in enumerate(PHRASES):
        base = i * BARS_PER_PHRASE * BAR
        for j, pitch in enumerate(melody):
            cols[base + j * unit][ROWS[PITCH[pitch][0]]] = ptok(pitch)
        for bar, chord in enumerate(HARMONY[i]):
            start = base + bar * BAR
            root = BASS_ROOT[chord]
            free = [off for off in BASS_HIT_PREF if cols[start + off][ROWS[root]] is None]
            for off in free[:2]:                               # two bass hits per bar
                cols[start + off][ROWS[root]] = "B" + root + "-"
            for off in CHORD_HITS:
                for pitch in CHORDS[chord]:
                    put(start + off, [(ROWS[PITCH[pitch][0]], ptok(pitch))])
            for off, rows in BEAT.items():
                put(start + off, [(ROWS[n], "D" + n + "-") for n in rows])
    return cols


def main(path="/home/jem/Desktop/projects/gtmusic/GTMusicSim/songs/my_heart_will_go_on.gtmusic"):
    cols = build()
    body = "\n".join(",".join(c or "" for c in col) for col in cols)
    out = pathlib.Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"%cernmusicsim;\nbpm={BPM}\n{body}", encoding="utf-8")
    return out, cols


if __name__ == "__main__":
    out, cols = main()
    assert len(cols) == len(PHRASES) * BARS_PER_PHRASE * BAR
    for col in cols:
        assert len(col) == 15 and all(c is None or len(c) == 3 for c in col)
    for i, (unit, melody) in enumerate(PHRASES):
        base = i * BARS_PER_PHRASE * BAR
        missed = [p for j, p in enumerate(melody) if cols[base + j * unit][ROWS[PITCH[p][0]]] != ptok(p)]
        assert not missed, (i, missed)
        bass = [sum(1 for col in cols[base + b * BAR:base + (b + 1) * BAR]
                    for n in col if n and n[0] == "B")
                for b in range(BARS_PER_PHRASE)]
        assert all(n >= 2 for n in bass), (i, bass)   # every bar keeps its bass roots
        print(f"  phrase {i + 1}: {len(melody)} melody notes kept, bass hits/bar {bass}, harmony {HARMONY[i]}")
    print(f"{out}: {len(cols)} columns, {sum(1 for c in cols for n in c if n)} notes, "
          f"bpm {BPM}, {len(cols) * 60000 / (4 * BPM) / 1000:.1f}s")
