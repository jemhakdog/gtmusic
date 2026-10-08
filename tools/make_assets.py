"""Generate placeholder 32x32 sprites for GTMusicSim/assets/.

The upstream repo ships no art (README: grab it from your Growtopia install),
and the canvas draws every note from these PNGs - without them the grid stays
blank. These are stand-in colours so the sim is usable; overwrite assets/*.png
with the real sprites whenever you have them.

    python3 tools/make_assets.py
"""

import struct
import zlib
from pathlib import Path

W = H = 32
OUT = Path(__file__).resolve().parent.parent / "GTMusicSim" / "assets"

CLEAR = (0, 0, 0, 0)


def canvas():
    return [CLEAR] * (W * H)


def rect(px, x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(H, y1)):
        for x in range(max(0, x0), min(W, x1)):
            px[y * W + x] = color


def disc(px, cx, cy, r, color):
    for y in range(H):
        for x in range(W):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                px[y * W + x] = color


def brighten(color, factor):
    r, g, b, a = color
    return (min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor)), a)


def keys(px, base):
    """Keyboard stripes."""
    for x in range(6, 27, 5):
        rect(px, x, 6, x + 1, 26, brighten(base, 1.7))


def notch(px):
    rect(px, 5, 20, 13, 27, (10, 12, 16, 255))


def cross(px):
    rect(px, 20, 4, 24, 14, (10, 12, 16, 255))
    rect(px, 17, 7, 27, 11, (10, 12, 16, 255))


def sprite(name, base):
    px = canvas()
    if name == "gear":
        rect(px, 2, 2, 30, 30, (60, 66, 78, 255))
        disc(px, 16, 16, 11, base)
        disc(px, 16, 16, 5, (20, 22, 28, 255))
    elif name == "arack":
        rect(px, 1, 1, 31, 31, base)
        rect(px, 1, 1, 31, 3, brighten(base, 1.5))
        rect(px, 15, 1, 17, 31, (18, 20, 26, 255))
    elif name == "drum":
        rect(px, 2, 2, 30, 30, base)
        disc(px, 16, 16, 10, (24, 16, 18, 255))
        disc(px, 16, 16, 4, brighten(base, 1.5))
    elif name == "blank":
        rect(px, 3, 3, 29, 29, base)
    elif name == "repeat_begin":
        rect(px, 2, 2, 30, 30, base)
        rect(px, 2, 2, 10, 30, (24, 20, 8, 255))
    elif name == "repeat_end":
        rect(px, 2, 2, 30, 30, base)
        rect(px, 22, 2, 30, 30, (24, 20, 8, 255))
    else:  # piano / bass families
        rect(px, 2, 2, 30, 30, base)
        if "piano" in name:
            keys(px, base)
        else:
            rect(px, 9, 5, 12, 27, brighten(base, 1.7))
            rect(px, 20, 5, 23, 27, brighten(base, 1.7))
        if "flat" in name:
            notch(px)
        elif "sharp" in name:
            cross(px)
    return px


def write_png(path, px):
    raw = b"".join(b"\x00" + b"".join(bytes(c) for c in px[y * W:(y + 1) * W]) for y in range(H))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


PALETTE = {
    "gear": (107, 118, 136, 255),
    "arack": (58, 66, 82, 255),
    "piano": (78, 140, 255, 255),
    "flat_piano": (63, 120, 224, 255),
    "sharp_piano": (106, 166, 255, 255),
    "drum": (255, 107, 107, 255),
    "bass": (160, 107, 255, 255),
    "flat_bass": (138, 85, 224, 255),
    "sharp_bass": (180, 140, 255, 255),
    "repeat_begin": (255, 200, 87, 255),
    "repeat_end": (255, 159, 61, 255),
    "blank": (42, 48, 64, 255),
}


def main(force=False):
    OUT.mkdir(parents=True, exist_ok=True)
    written, skipped = [], []
    for name, base in PALETTE.items():
        targets = [(name, base)]
        if name != "gear":  # 'on' = pressed/bright variant of the same sprite
            targets.append((f"{name}_on", brighten(base, 1.45)))
        for stem, color in targets:
            path = OUT / f"{stem}.png"
            if path.exists() and not force:
                skipped.append(path.name)
                continue
            write_png(path, sprite(name, color))
            written.append(path.name)
    if skipped:
        print(f"kept {len(skipped)} existing sprite(s) (real art wins) - pass --force to overwrite")
    return written


def decode(path):
    """Minimal PNG reader, used only by the self-check below."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    pos, chunks = 8, []
    while pos < len(data):
        (size,) = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        chunks.append((tag, data[pos + 8:pos + 8 + size]))
        pos += 12 + size
    header = dict(chunks)[b"IHDR"]
    w, h, depth, color = struct.unpack(">IIBB", header[:10])
    return w, h, depth, color, zlib.decompress(dict(chunks)[b"IDAT"])


def pixel(w, raw, x, y):
    off = y * (1 + w * 4) + 1 + x * 4
    return raw[off:off + 4]


if __name__ == "__main__":
    import sys

    names = main(force="--force" in sys.argv)
    if not names:
        print(f"nothing written, {OUT} already has sprites")
        raise SystemExit
    w, h, depth, color, raw = decode(OUT / "piano.png")
    assert (w, h, depth, color) == (32, 32, 8, 6), (w, h, depth, color)
    assert len(raw) == h * (1 + w * 4), len(raw)
    assert pixel(w, raw, 0, 0) == b"\x00\x00\x00\x00"  # transparent margin
    assert pixel(w, raw, 5, 5) == bytes((78, 140, 255, 255))  # piano body
    assert pixel(w, raw, 11, 10) != bytes((78, 140, 255, 255))  # key stripe
    bw, _, _, _, braw = decode(OUT / "blank.png")
    assert pixel(bw, braw, 5, 5) == bytes((42, 48, 64, 255))
    print(f"wrote {len(names)} sprites to {OUT}")
