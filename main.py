#!/usr/bin/env python3
"""news-image-20261118 -- one-image summary of Wednesday 18 November 2026.

Draws a deterministic 1024x1024 PNG newspaper poster: a dated header plus
six story panels, each with a hand-drawn pictogram, a headline and one
factual sub-label. Pure Python standard library only; no network access;
the same bytes come out on every run.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   ->  out/entry.png
"""

import math
import os
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024

# ---------------------------------------------------------------- palette
CREAM = (247, 241, 222)
NAVY = (20, 38, 63)
NAVY_DARK = (13, 26, 44)
RED = (178, 34, 34)
GOLD = (212, 160, 23)
INK = (43, 43, 43)
WHITE = (255, 255, 255)
PANEL_LINE = (201, 191, 166)
SKY_BLUE = (220, 233, 242)
SEA = (127, 179, 213)
SAND = (233, 205, 140)
GRASS_BG = (228, 239, 224)
WALL = (240, 230, 210)
LILAC = (239, 230, 240)
MINT = (221, 238, 230)
BROWN = (139, 94, 52)
SKIN = (222, 184, 135)
VIRUS = (201, 48, 48)
VIRUS_LIGHT = (226, 106, 106)

# ---------------------------------------------------------------- canvas
class Canvas:
    """A plain RGB pixel buffer with tiny shape helpers."""

    def __init__(self, width, height, colour):
        self.width = width
        self.height = height
        self.buf = bytearray(width * height * 3)
        self.fill(0, 0, width, height, colour)

    def put(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.buf[i] = colour[0]
            self.buf[i + 1] = colour[1]
            self.buf[i + 2] = colour[2]

    def fill(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        r, g, b = colour
        for yy in range(y0, y1):
            base = (yy * self.width + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.buf[i] = r
                self.buf[i + 1] = g
                self.buf[i + 2] = b

    def hline(self, x, y, length, colour):
        for dx in range(length):
            self.put(x + dx, y, colour)

    def vline(self, x, y, length, colour):
        for dy in range(length):
            self.put(x, y + dy, colour)

    def outline(self, x, y, w, h, colour, thick=2):
        self.fill(x, y, w, thick, colour)
        self.fill(x, y + h - thick, w, thick, colour)
        self.fill(x, y, thick, h, colour)
        self.fill(x + w - thick, y, thick, h, colour)

    def line(self, x0, y0, x1, y1, colour):
        """Bresenham line, works for any slope."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.put(x, y, colour)
            if x == x1 and y == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def thick_line(self, x0, y0, x1, y1, colour, thick=3):
        half = thick // 2
        for ox in range(-half, half + 1):
            for oy in range(-half, half + 1):
                self.line(x0 + ox, y0 + oy, x1 + ox, y1 + oy, colour)

    def disc(self, cx, cy, r, colour):
        for dy in range(-r, r + 1):
            span = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hline(cx - span, cy + dy, span * 2 + 1, colour)

    def ring(self, cx, cy, r, colour):
        steps = max(24, r * 6)
        for k in range(steps + 1):
            a = 2.0 * math.pi * k / steps
            self.put(cx + int(r * math.cos(a)), cy + int(r * math.sin(a)), colour)

    def arc(self, cx, cy, r, a0, a1, colour):
        steps = max(8, int(r * abs(a1 - a0)))
        prev = None
        for k in range(steps + 1):
            a = a0 + (a1 - a0) * k / steps
            px = cx + int(r * math.cos(a))
            py = cy + int(r * math.sin(a))
            if prev is not None:
                self.line(prev[0], prev[1], px, py, colour)
            prev = (px, py)

    def triangle(self, p0, p1, p2, colour):
        """Filled triangle by barycentric sampling of its bounding box."""
        xs = [p0[0], p1[0], p2[0]]
        ys = [p0[1], p1[1], p2[1]]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        d = (p1[1] - p2[1]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[1] - p2[1])
        if d == 0:
            return
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                w0 = ((p1[1] - p2[1]) * (xx - p2[0])
                      + (p2[0] - p1[0]) * (yy - p2[1])) / d
                w1 = ((p2[1] - p0[1]) * (xx - p2[0])
                      + (p0[0] - p2[0]) * (yy - p2[1])) / d
                w2 = 1.0 - w0 - w1
                if w0 >= 0 and w1 >= 0 and w2 >= 0:
                    self.put(xx, yy, colour)

    def star(self, cx, cy, outer, colour):
        inner = max(2, int(outer * 0.45))
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = outer if k % 2 == 0 else inner
            pts.append((cx + int(rad * math.cos(ang)),
                        cy + int(rad * math.sin(ang))))
        for k in range(10):
            a = pts[k]
            b = pts[(k + 1) % 10]
            self.line(a[0], a[1], b[0], b[1], colour)
        self.disc(cx, cy, max(2, outer // 4), colour)

    def burst(self, cx, cy, r, colour):
        """Explosion starburst: spokes plus a hot centre."""
        for k in range(12):
            a = 2.0 * math.pi * k / 12
            x1 = cx + int(r * math.cos(a))
            y1 = cy + int(r * math.sin(a))
            self.thick_line(cx, cy, x1, y1, colour, 2)
        self.disc(cx, cy, max(3, r // 3), GOLD)
        self.disc(cx, cy, max(2, r // 5), WHITE)


# ---------------------------------------------------------------- 5x7 font
# Each glyph is seven rows of five cells; '1' is ink, '0' is empty.
# Designed for this poster: capitals, digits and a little punctuation.
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
    '3': ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "00100", "00100"),
    ',': ("00000", "00000", "00000", "00000", "00000", "00100", "01000"),
    '-': ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    ':': ("00000", "00100", "00000", "00000", "00000", "00100", "00000"),
    ';': ("00000", "00100", "00000", "00000", "00000", "00100", "01000"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '%': ("11001", "10010", "00100", "01000", "01001", "10011", "00000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
}

GLYPH_W = 5
GLYPH_H = 7
GLYPH_STEP = 6  # glyph width + one blank column


def text_width(text, scale):
    if not text:
        return 0
    return len(text) * GLYPH_STEP * scale - scale


def draw_text(cv, x, y, text, scale, colour):
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            glyph = FONT[' ']
        for row in range(GLYPH_H):
            bits = glyph[row]
            for col in range(GLYPH_W):
                if bits[col] == '1':
                    cv.fill(cx + col * scale, y + row * scale,
                            scale, scale, colour)
        cx += GLYPH_STEP * scale
    return cx


def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    lines = []
    for raw in text.split('\n'):
        words = raw.split(' ')
        cur = ''
        for word in words:
            trial = word if not cur else cur + ' ' + word
            if text_width(trial, scale) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


def draw_centered(cv, y, text, scale, colour, width=WIDTH):
    x = (width - text_width(text, scale)) // 2
    draw_text(cv, x, y, text, scale, colour)


# ---------------------------------------------------------------- scenes
# Every scene draws inside a box (sx, sy, sw, sh) at the top of its panel.

def scene_gulf(cv, sx, sy, sw, sh):
    cv.fill(sx, sy, sw, sh, SKY_BLUE)
    sea_y = sy + sh - 38
    cv.fill(sx, sea_y, sw, 38, SEA)
    # dashed wave lines
    for wy in (sea_y + 10, sea_y + 24):
        for wx in range(sx + 8, sx + sw - 8, 26):
            cv.hline(wx, wy, 14, WHITE)
    # island with a missile site on the left
    cv.triangle((sx + 30, sea_y), (sx + 78, sea_y - 52),
                (sx + 126, sea_y), SAND)
    cv.fill(sx + 70, sea_y - 66, 16, 14, NAVY_DARK)
    cv.vline(sx + 78, sea_y - 84, 20, NAVY_DARK)
    cv.burst(sx + 78, sea_y - 92, 16, RED)
    # two jets crossing the sky
    for jx, jy in ((sx + 210, sy + 26), (sx + 268, sy + 48)):
        cv.line(jx - 12, jy - 7, jx + 12, jy + 7, NAVY_DARK)
        cv.line(jx - 12, jy + 7, jx + 12, jy - 7, NAVY_DARK)
    # ship on the sea with a drone above it
    cv.fill(sx + 330, sea_y + 6, 84, 10, NAVY_DARK)
    cv.vline(sx + 372, sea_y - 12, 18, NAVY_DARK)
    cv.disc(sx + 372, sea_y - 16, 4, RED)
    cv.disc(sx + 300, sy + 22, 3, INK)
    cv.disc(sx + 316, sy + 34, 2, INK)


def scene_bridge(cv, sx, sy, sw, sh):
    cv.fill(sx, sy, sw, sh, GRASS_BG)
    water_y = sy + sh - 34
    cv.fill(sx, water_y, sw, 34, SEA)
    for wy in (water_y + 10, water_y + 23):
        for wx in range(sx + 8, sx + sw - 8, 26):
            cv.hline(wx, wy, 14, WHITE)
    deck_y = sy + 52
    # standing decks left and right
    cv.fill(sx + 12, deck_y, 150, 8, NAVY_DARK)
    cv.fill(sx + sw - 162, deck_y, 150, 8, NAVY_DARK)
    # pylons and cables
    for px in (sx + 52, sx + sw - 72):
        cv.fill(px, sy + 12, 8, deck_y - sy - 12 + 8, NAVY_DARK)
        cv.line(px + 4, sy + 14, px - 38, deck_y, NAVY_DARK)
        cv.line(px + 4, sy + 14, px + 46, deck_y, NAVY_DARK)
    # the fallen middle span, tilted down into the water
    cv.thick_line(sx + 168, deck_y + 4, sx + 268, water_y + 16, RED, 5)
    cv.thick_line(sx + 172, deck_y + 10, sx + 262, water_y + 8, NAVY_DARK, 3)
    # smoke puffs over the gap
    cv.disc(sx + 216, sy + 26, 7, (150, 150, 150))
    cv.disc(sx + 238, sy + 16, 9, (170, 170, 170))
    cv.disc(sx + 258, sy + 30, 6, (150, 150, 150))


def scene_summit(cv, sx, sy, sw, sh):
    cv.fill(sx, sy, sw, sh, WALL)
    table_y = sy + 96
    cv.fill(sx + 24, table_y, sw - 48, 7, NAVY_DARK)
    cv.fill(sx + 44, table_y + 7, 8, 16, NAVY_DARK)
    cv.fill(sx + sw - 52, table_y + 7, 8, 16, NAVY_DARK)
    # three flag poles with seated figures beneath them
    flags = [
        (sx + 78, 'china'),
        (sx + 214, 'usa'),
        (sx + 350, 'russia'),
    ]
    for fx, kind in flags:
        cv.vline(fx, sy + 16, table_y - sy - 16, NAVY_DARK)
        if kind == 'china':
            cv.fill(fx + 2, sy + 16, 52, 32, (205, 32, 32))
            cv.disc(fx + 14, sy + 28, 4, GOLD)
            cv.disc(fx + 30, sy + 24, 2, GOLD)
            cv.disc(fx + 34, sy + 32, 2, GOLD)
        elif kind == 'usa':
            cv.fill(fx + 2, sy + 16, 52, 32, WHITE)
            for stripe in range(4):
                cv.fill(fx + 2, sy + 18 + stripe * 8, 52, 3, RED)
            cv.fill(fx + 2, sy + 16, 22, 16, NAVY)
        else:
            cv.fill(fx + 2, sy + 16, 52, 11, WHITE)
            cv.fill(fx + 2, sy + 27, 52, 10, (0, 60, 160))
            cv.fill(fx + 2, sy + 37, 52, 11, RED)
        cv.disc(fx + 28, table_y - 12, 11, SKIN)
        cv.fill(fx + 12, table_y - 4, 32, 5, NAVY_DARK)


def scene_senate(cv, sx, sy, sw, sh):
    cv.fill(sx, sy, sw, sh, SKY_BLUE)
    # ballot box with a big red check
    bx, by = sx + 34, sy + 30
    cv.fill(bx, by, 150, 66, NAVY_DARK)
    cv.fill(bx + 12, by + 14, 126, 40, WHITE)
    cv.fill(bx + 55, by - 6, 40, 7, NAVY_DARK)
    cv.thick_line(bx + 30, by + 36, bx + 58, by + 50, RED, 5)
    cv.thick_line(bx + 58, by + 50, bx + 112, by + 18, RED, 5)
    # paper slip and gold star on the right
    cv.fill(sx + 250, sy + 22, 56, 66, WHITE)
    cv.fill(sx + 250, sy + 22, 56, 5, RED)
    for ly in (sy + 38, sy + 52, sy + 66):
        cv.hline(sx + 260, ly, 36, NAVY)
    cv.star(sx + 380, sy + 52, 34, GOLD)
    draw_text(cv, sx + 348, sy + 96, "56-44", 2, NAVY)


def scene_ebola(cv, sx, sy, sw, sh):
    cv.fill(sx, sy, sw, sh, LILAC)

    def virus(cx, cy, r):
        for k in range(12):
            a = 2.0 * math.pi * k / 12
            x1 = cx + int((r + 9) * math.cos(a))
            y1 = cy + int((r + 9) * math.sin(a))
            cv.line(cx + int(r * 0.8 * math.cos(a)),
                    cy + int(r * 0.8 * math.sin(a)), x1, y1, VIRUS)
            cv.disc(x1, y1, 3, VIRUS)
        cv.disc(cx, cy, r, VIRUS)
        cv.disc(cx - r // 3, cy - r // 3, r // 3, VIRUS_LIGHT)
        cv.disc(cx + r // 3, cy + r // 4, r // 5, VIRUS_LIGHT)

    virus(sx + 96, sy + 58, 26)
    virus(sx + 208, sy + 74, 16)
    # field clinic with a red cross
    cx0 = sx + 300
    cv.fill(cx0, sy + 44, 130, 62, WHITE)
    cv.triangle((cx0 - 8, sy + 44), (cx0 + 65, sy + 14),
                (cx0 + 138, sy + 44), NAVY)
    cv.fill(cx0 + 56, sy + 60, 18, 34, RED)
    cv.fill(cx0 + 47, sy + 69, 36, 16, RED)
    cv.hline(sx, sy + sh - 2, sw, NAVY)


def scene_cyclone(cv, sx, sy, sw, sh):
    cv.fill(sx, sy, sw, sh, MINT)
    # spiral storm: nested arcs around a calm eye
    cx, cy = sx + 120, sy + 66
    for r in (18, 30, 42, 54):
        cv.arc(cx, cy, r, math.pi * 0.15, math.pi * 1.85, NAVY)
    cv.disc(cx, cy, 8, WHITE)
    cv.ring(cx, cy, 8, NAVY)
    # wind streaks
    for wy in (sy + 18, sy + 34, sy + 96, sy + 112):
        for wx in range(sx + 250, sx + sw - 30, 44):
            cv.hline(wx, wy, 26, NAVY)
    # leaning palm on a sandbar above the sea
    sand_y = sy + sh - 30
    cv.fill(sx + 250, sand_y, 180, 12, SAND)
    cv.fill(sx + 250, sand_y + 12, 180, 18, SEA)
    tx = sx + 330
    cv.thick_line(tx, sand_y, tx + 22, sy + 34, BROWN, 5)
    top = (tx + 22, sy + 34)
    for dx, dy in ((-34, 6), (-26, -12), (-8, -18), (10, -16), (26, -6), (30, 10)):
        cv.line(top[0], top[1], top[0] + dx, top[1] + dy, (34, 139, 68))
    cv.disc(top[0] - 4, top[1] + 8, 4, BROWN)
    cv.disc(top[0] + 6, top[1] + 10, 4, BROWN)


# ---------------------------------------------------------------- poster
STORIES = [
    ("US HITS IRAN, IRAN HITS BACK",
     "QESHM ISLAND STRUCK; DRONES AT US BASES IN BAHRAIN AND KUWAIT",
     scene_gulf),
    ("KERCH BRIDGE SPAN FALLS",
     "UKRAINE STRIKES FOR 2ND DAY; ROAD SPAN DROPS INTO THE STRAIT",
     scene_bridge),
    ("XI MEETS PUTIN IN SHENZHEN",
     "TRILATERAL WITH TRUMP SET FOR THURSDAY 19 NOVEMBER",
     scene_summit),
    ("PELTOLA WINS ALASKA SENATE",
     "DEMOCRATS TAKE 56 SEATS IN THE US SENATE",
     scene_senate),
    ("EBOLA CASES DOUBLE IN CONGO",
     "11,000 CASES, 5,400 DEAD, WHO SAYS; CHILDREN HIT HARDEST",
     scene_ebola),
    ("CYCLONE XAVIER HITS COOK IS.",
     "CATEGORY 5 STORM, GUSTS TO 315 KM/H, NORTHERN COOK ISLANDS",
     scene_cyclone),
]


def build_poster():
    cv = Canvas(WIDTH, HEIGHT, CREAM)

    # ---- header band
    cv.fill(0, 0, WIDTH, 150, NAVY)
    draw_centered(cv, 26, "WEDNESDAY 18 NOVEMBER 2026", 4, WHITE)
    sub = "THE WORLD IN ONE IMAGE"
    sw = text_width(sub, 2)
    sx = (WIDTH - sw) // 2
    cv.fill(sx - 26, 100, 10, 10, RED)
    cv.fill(sx + sw + 16, 100, 10, 10, RED)
    draw_text(cv, sx, 94, sub, 2, GOLD)
    cv.fill(0, 146, WIDTH, 4, RED)

    # ---- six panels, two columns by three rows
    px0, py0 = 16, 166
    pw, ph, gap = 488, 275, 16
    for idx, (headline, sublabel, scene) in enumerate(STORIES):
        col = idx % 2
        row = idx // 2
        x = px0 + col * (pw + gap)
        y = py0 + row * (ph + gap)
        cv.fill(x, y, pw, ph, WHITE)
        cv.outline(x, y, pw, ph, PANEL_LINE, 2)
        scene(cv, x + 10, y + 10, pw - 20, 128)

        head_lines = wrap_text(headline, pw - 28, 3)
        hy = y + 150
        for line in head_lines:
            draw_text(cv, x + 14, hy, line, 3, NAVY)
            hy += 24
        sub_lines = wrap_text(sublabel, pw - 28, 2)
        sy = hy + 6
        for line in sub_lines:
            draw_text(cv, x + 14, sy, line, 2, INK)
            sy += 17

    return cv


# ---------------------------------------------------------------- PNG writer
def chunk(kind, data):
    body = kind + data
    return (struct.pack(">I", len(data)) + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))


def encode_png(cv):
    raw = bytearray()
    row_len = cv.width * 3
    for y in range(cv.height):
        raw.append(0)  # filter: none
        start = y * row_len
        raw += cv.buf[start:start + row_len]
    ihdr = struct.pack(">IIBBBBB", cv.width, cv.height, 8, 2, 0, 0, 0)
    out = bytearray(b"\x89PNG\r\n\x1a\n")
    out += chunk(b"IHDR", ihdr)
    out += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    out += chunk(b"IEND", b"")
    return bytes(out)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    poster = build_poster()
    data = encode_png(poster)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)
    print("Wrote %s (%d bytes, %dx%d)" % (path, len(data), WIDTH, HEIGHT))


if __name__ == "__main__":
    main()
