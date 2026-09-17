#!/usr/bin/env python3
"""Write app/icon-192.png and app/icon-512.png - the installable-app icon, drawn, not downloaded.

A PWA is only installable on Android if the manifest names real PNG icons, and a committed binary someone
produced once in a graphics program is exactly the kind of artefact that cannot be audited or rebuilt. So the
icons are generated from the same twelve lines of dot-arithmetic the engine uses: Via, Populus, Acquisitio,
Amissio as four rows of single and double marks. Rebuild with `python3 app/make_icons.py`; the bytes are
deterministic, so a clean clone produces the identical file and CI can hold it to that.
"""
from __future__ import annotations

import pathlib
import struct
import sys
import zlib

APP = pathlib.Path(__file__).resolve().parent
INK = (24, 20, 16, 255)
PAPER = (233, 223, 200, 255)      # a tint that survives being composited on a white launcher background
ACCENT = (93, 74, 134, 255)

# the four mothers, top to bottom: 1 = a single dot, 2 = a pair
MOTHERS = {"Via": [1, 1, 1, 1], "Populus": [2, 2, 2, 2], "Acquisitio": [2, 1, 2, 1], "Amissio": [1, 2, 1, 2]}
SHIELD = [MOTHERS["Via"], MOTHERS["Populus"], MOTHERS["Acquisitio"], MOTHERS["Amissio"]]


def canvas(n: int) -> bytearray:
    return bytearray(n * n * 4)


def put(px: bytearray, n: int, x: int, y: int, rgba: tuple, alpha: float = 1.0) -> None:
    if not (0 <= x < n and 0 <= y < n):
        return
    i = (y * n + x) * 4
    for k in range(3):
        px[i + k] = int(px[i + k] * (1 - alpha) + rgba[k] * alpha)
    px[i + 3] = 255


def disc(px: bytearray, n: int, cx: int, cy: int, r: int, rgba: tuple) -> None:
    """A filled circle with a one-pixel soft edge, so the icon does not crawl on a 1080p phone screen."""
    for y in range(cy - r - 1, cy + r + 2):
        for x in range(cx - r - 1, cx + r + 2):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d <= r - 0.5:
                put(px, n, x, y, rgba)
            elif d <= r + 0.75:
                put(px, n, x, y, rgba, alpha=max(0.0, min(1.0, r + 0.75 - d)))


def _shape(x: int, y: int, n: int, pad: int, cr: int):
    """Signed distance to the edge of the rounded square, or None outside it.

    Written as a distance field rather than a corner test because the naive version painted a ring around the
    whole icon and produced a black frame a pixel wide in some sizes and a heavy one in others.
    """
    dx = min(x - pad, (n - 1 - pad) - x)
    dy = min(y - pad, (n - 1 - pad) - y)
    if dx < 0 or dy < 0:
        return None
    dist = min(dx, dy)
    if dx < cr and dy < cr:
        arc = ((cr - dx) ** 2 + (cr - dy) ** 2) ** 0.5
        if arc > cr:
            return None
        dist = min(dist, cr - arc)
    return dist


def render(n: int) -> bytes:
    """Four mothers side by side, each four rows deep, over the Judge line.

    The first draft drew every figure's rows into one shared column (a staircase), and the second gave the
    paper a tint so pale it vanished on a white launcher and a border so thick the dots looked incidental.
    Both failures were invisible in code review and obvious in a picture - which is why this file renders,
    and CI keeps the bytes.
    """
    px = canvas(n)
    pad, cr = n // 8, n // 6
    stroke = max(1, int(n * 0.010))
    for y in range(n):
        for x in range(n):
            d = _shape(x, y, n, pad, cr)
            if d is None:
                continue
            i = (y * n + x) * 4
            rgb = INK if d < stroke else PAPER
            for k in range(3):
                px[i + k] = rgb[k]
            px[i + 3] = 255
    box = n - 2 * pad
    left, top = pad + int(box * 0.07), pad + int(box * 0.17)
    wide, tall = int(box * 0.86), int(box * 0.62)
    # marks sized for a 48px launcher tile, not for the 512px file: at n//32 the pairs merged into one blob
    # when the phone downscaled it, which is the only size anyone actually reads this at
    r = max(3, n // 22)
    gap = int(r * 2.05)
    for f, figure in enumerate(SHIELD):                    # one column per mother, evenly spaced
        cx = left + int(wide * (2 * f + 1) / 8)
        for row, dots in enumerate(figure):                 # four rows, top to bottom
            cy = top + int(tall * (2 * row + 1) / 8)
            if dots == 1:
                disc(px, n, cx, cy, r, INK)
            else:
                disc(px, n, cx - gap, cy, r, INK)
                disc(px, n, cx + gap, cy, r, INK)
    y0 = top + tall + int(tall * 0.11)                      # the Judge: what all that counting was for
    for y in range(y0, y0 + max(1, int(n * 0.014))):
        for x in range(left, left + wide):
            put(px, n, x, y, ACCENT)
    return bytes(px)


def png(width: int, height: int, rgba: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    raw = b"".join(b"\x00" + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def scanlines(blob: bytes) -> bytes:
    """The uncompressed pixel stream inside a PNG this script wrote (one filter byte 0 per row)."""
    i, idat = 8, b""
    while i + 8 <= len(blob):
        ln = int.from_bytes(blob[i:i + 4], "big")
        tag = blob[i + 4:i + 8]
        if tag == b"IDAT":
            idat += blob[i + 8:i + 8 + ln]
        i += 12 + ln
    return zlib.decompress(idat)


def main() -> int:
    for size in (192, 512):
        blob = png(size, size, render(size))
        out = APP / f"icon-{size}.png"
        if len(sys.argv) > 1 and sys.argv[1] == "--check":
            # compare the pixels, not the file: zlib output can differ between platforms and versions, and an
            # icon whose picture is identical is not a stale artefact just because someone compressed it twice
            if not out.exists():
                print(f"icon-{size}.png is missing - run: python3 app/make_icons.py")
                return 1
            if scanlines(out.read_bytes()) != scanlines(blob):
                print(f"icon-{size}.png does not match what this script draws - run: python3 app/make_icons.py")
                return 1
            print(f"icon-{size}.png: {size}x{size}, {len(out.read_bytes()):,} B, pixels match the drawing")
            continue
        out.write_bytes(blob)
        print(f"wrote {out.name}: {len(blob):,} B, {size}x{size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
