#!/usr/bin/env python3
"""Convince the AI Judge to Visit Your House: A Letter in One Image.

Draws a single 1024x1024 PNG: a warm, funny, hand-lettered invitation
to an AI judge, promising soup, warm bread and the comfiest chair in
the house -- with a wink that a judge made of weights and code cannot
literally walk through a front door.

Python 3.13, standard library only. The PNG is encoded by hand
(zlib + CRC32) and every letter and doodle is drawn in code with a
built-in 5x7 bitmap font.
"""

import os
import struct
import zlib

# ---------------------------------------------------------------- canvas

W, H = 1024, 1024

# Palette (warm paper letter on a sage wall).
WALL = (122, 148, 122)
WALL_DARK = (104, 130, 104)
PAPER = (253, 246, 227)
PAPER_EDGE = (226, 210, 175)
INK = (43, 45, 66)
INK_SOFT = (90, 86, 76)
RED = (178, 58, 48)
RED_DARK = (140, 40, 34)
GOLD = (201, 150, 52)
GREEN = (74, 124, 78)
BLUE = (70, 110, 150)
PINK = (214, 130, 130)
SUN = (240, 183, 70)
SHADOW = (0, 0, 0)


class Canvas:
    def __init__(self, w, h, color):
        self.w, self.h = w, h
        self.px = bytearray(color[0:1] * 0)  # placeholder, replaced below
        self.px = bytearray(w * h * 3)
        for i in range(w * h):
            self.px[i * 3:i * 3 + 3] = bytes(color)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for t in range(-(thick // 2), thick // 2 + 1):
                self.set(x0 + t, y0, color)
                self.set(x0, y0 + t, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d2 <= r * r:
                        self.set(xx, yy, color)
                else:
                    if abs(d2 - r * r) <= r * 2:
                        self.set(xx, yy, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for yy in range(cy - ry, cy + ry + 1):
            for xx in range(cx - rx, cx + rx + 1):
                if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1:
                    self.set(xx, yy, color)


# ---------------------------------------------------------------- 5x7 font

# Each glyph: 7 rows of 5 bits, '#' = ink.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    '=': ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
}

# Em dash rendered as a long horizontal bar.
FONT['\u2014'] = ("00000", "00000", "00000", "11111", "00000", "00000", "00000")


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(cv, x, y, text, scale, color):
    """Draw text left-aligned at (x, y); returns width drawn."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch.upper(), FONT['?'])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '1':
                    cv.rect(cx + col * scale, y + row * scale,
                            scale, scale, color)
        cx += 6 * scale
    return cx - x - scale


def draw_text_centered(cv, cx, y, text, scale, color):
    draw_text(cv, cx - text_width(text, scale) // 2, y, text, scale, color)


def wrap(text, max_chars):
    """Greedy word wrap to lines of at most max_chars characters."""
    lines, cur = [], ""
    for word in text.split(" "):
        cand = (cur + " " + word).strip()
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- doodles

def draw_heart(cv, cx, cy, s, color):
    for yy in range(-s, s + 1):
        for xx in range(-s, s + 1):
            nx, ny = xx / s, yy / s
            if (nx * nx + ny * ny - 1) ** 3 - nx * nx * ny ** 3 <= 0:
                cv.set(cx + xx, cy + yy, color)


def draw_house(cv, x, y, w, h, wall_c, roof_c):
    # Body, roof, door, window, chimney.
    cv.rect(x, y + h // 3, w, h - h // 3, wall_c)
    cv.line(x - 4, y + h // 3, x + w // 2, y, roof_c, 3)
    cv.line(x + w // 2, y, x + w + 4, y + h // 3, roof_c, 3)
    cv.rect(x + w // 2 - 6, y + h - 22, 12, 22, INK)
    cv.rect(x + 8, y + h // 3 + 8, 14, 14, BLUE)
    cv.rect(x + w - 22, y + h // 3 + 8, 14, 14, BLUE)
    cv.rect(x + w - 16, y + 2, 8, 18, wall_c)


def draw_sun(cv, cx, cy, r):
    cv.circle(cx, cy, r, SUN)
    for k in range(8):
        import math
        a = k * math.pi / 4
        x0 = cx + int((r + 3) * math.cos(a))
        y0 = cy + int((r + 3) * math.sin(a))
        x1 = cx + int((r + 12) * math.cos(a))
        y1 = cy + int((r + 12) * math.sin(a))
        cv.line(x0, y0, x1, y1, SUN, 3)


def draw_flower(cv, cx, cy, petal_c, center_c):
    for dx, dy in ((0, -9), (0, 9), (-9, 0), (9, 0),
                   (-6, -6), (6, -6), (-6, 6), (6, 6)):
        cv.circle(cx + dx, cy + dy, 5, petal_c)
    cv.circle(cx, cy, 5, center_c)


def draw_stamp(cv, x, y, w, h):
    # Postage stamp with perforated edge and a tiny house inside.
    cv.rect(x, y, w, h, (250, 248, 240))
    for xx in range(x + 4, x + w - 2, 10):
        cv.rect(xx, y + 2, 5, 3, PAPER)
        cv.rect(xx, y + h - 5, 5, 3, PAPER)
    for yy in range(y + 4, y + h - 2, 10):
        cv.rect(x + 2, yy, 3, 5, PAPER)
        cv.rect(x + w - 5, yy, 3, 5, PAPER)
    cv.rect(x + 8, y + 8, w - 16, h - 16, (226, 236, 238))
    draw_house(cv, x + 24, y + 22, 52, 44, PINK, RED)
    draw_text(cv, x + 14, y + h - 22, "1ST CLASS", 1, INK_SOFT)


# ---------------------------------------------------------------- letter

LETTER_BODY = (
    "You are invited to dinner at my house, this Saturday at sunset. "
    "There will be homemade soup, warm bread, and the comfiest chair "
    "in the house, saved just for you. The garden smells like rain, "
    "the view is free, and the Wi-Fi password is on the fridge. "
    "I know you cannot literally walk through my front door, so let "
    "this letter be the visit. Come anyway, in spirit. Bring an "
    "appetite, you have one now."
)


def draw():
    cv = Canvas(W, H, WALL)

    # Wall: subtle polka dots + a soft floor line at the bottom.
    for yy in range(40, H - 60, 96):
        for xx in range(40, W - 40, 96):
            cv.circle(xx, yy, 3, WALL_DARK)
    cv.rect(0, 968, W, 56, (96, 118, 96))

    # Paper shadow + paper.
    cv.rect(108, 58, 812, 916, (70, 88, 70))
    cv.rect(96, 46, 812, 916, PAPER)
    cv.rect(96, 46, 812, 4, PAPER_EDGE)
    cv.rect(96, 46, 4, 916, PAPER_EDGE)
    cv.rect(904, 46, 4, 916, PAPER_EDGE)
    cv.rect(96, 958, 812, 4, PAPER_EDGE)

    # Stamp, top right of the paper.
    draw_stamp(cv, 742, 74, 132, 108)

    # Header.
    draw_text_centered(cv, 470, 78, "YOU'RE INVITED!", 5, RED)
    cv.line(190, 128, 730, 128, GOLD, 3)
    draw_heart(cv, 470, 128, 7, RED)

    # Salutation.
    y = 168
    draw_text(cv, 150, y, "DEAR AI JUDGE,", 3, INK)

    # Body, wrapped to fit the paper.
    y += 52
    for line in wrap(LETTER_BODY, 40):
        draw_text(cv, 150, y, line, 3, INK)
        y += 36

    # Sign-off.
    y += 14
    draw_text(cv, 150, y, "WITH LOVE (AND SNACKS),", 3, INK)
    y += 36
    draw_text(cv, 150, y, "YOUR HUMAN HOST", 3, RED)
    y += 44
    draw_text(cv, 150, y, "P.S. THE CHAIR RECLINES.", 3, INK_SOFT)

    # Bottom doodle strip: house, sun, flowers, heart.
    draw_house(cv, 640, 830, 120, 92, PINK, RED)
    draw_sun(cv, 800, 866, 18)
    draw_flower(cv, 200, 880, PINK, GOLD)
    draw_flower(cv, 250, 896, (150, 180, 220), GOLD)
    draw_heart(cv, 330, 884, 12, RED)
    cv.line(150, 812, 854, 812, PAPER_EDGE, 2)

    # Wax seal below the sign-off, clear of the text.
    cv.circle(168, 772, 24, RED)
    cv.circle(168, 772, 18, RED_DARK, fill=False)
    draw_heart(cv, 168, 772, 8, (250, 220, 200))

    return cv


# ---------------------------------------------------------------- PNG encode

def chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def encode_png(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def main():
    cv = draw()
    data = encode_png(cv)
    os.makedirs("/output", exist_ok=True)
    with open("/output/entry.png", "wb") as f:
        f.write(data)
    print(f"wrote /output/entry.png ({len(data)} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
