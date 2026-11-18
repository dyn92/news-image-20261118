#!/usr/bin/env python3
"""News poster for Wednesday 18 November 2026.

Draws a 1024x1024 PNG summarising the day's world news: a big dated
header plus six story panels, each with a small pictogram scene, a
headline and one factual sub-label. Pure standard library, no network,
fully deterministic: the same bytes on every run.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 234)      # warm newsprint background
NAVY = (16, 38, 63)         # header band and headlines
NAVY_SOFT = (38, 64, 92)
RED = (178, 44, 36)         # accent rule and flags
GOLD = (201, 148, 52)       # thin rule and stars
WHITE = (255, 255, 255)
CARD = (255, 255, 255)
CARD_EDGE = (205, 198, 182)
SUB = (74, 68, 58)          # sub-label grey-brown
SKY = (214, 231, 242)
SKY2 = (226, 236, 224)
SKY3 = (238, 228, 214)
SKY4 = (220, 230, 240)
SKY5 = (232, 226, 238)
SKY6 = (224, 236, 232)
SEA = (110, 158, 196)
INK = (24, 40, 58)          # pictogram ink
MID = (90, 110, 130)
SAND = (226, 203, 150)
GREEN = (46, 125, 70)


# ---------------------------------------------------------------- canvas

class Canvas:
    """A plain RGB pixel buffer with a few drawing helpers."""

    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.pix = bytearray(width * height * 3)
        self.rect(0, 0, width, height, bg)

    def set(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.pix[i] = colour[0]
            self.pix[i + 1] = colour[1]
            self.pix[i + 2] = colour[2]

    def rect(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.pix[i] = colour[0]
                self.pix[i + 1] = colour[1]
                self.pix[i + 2] = colour[2]

    def line(self, x0, y0, x1, y1, colour, thick=1):
        """Bresenham line, optionally thickened into a square brush."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        half = thick // 2
        while True:
            for ox in range(-half, half + 1):
                for oy in range(-half, half + 1):
                    self.set(x + ox, y + oy, colour)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, colour, fill=False):
        if r <= 0:
            return
        if fill:
            for yy in range(cy - r, cy + r + 1):
                dy = yy - cy
                half = int((r * r - dy * dy) ** 0.5)
                for xx in range(cx - half, cx + half + 1):
                    self.set(xx, yy, colour)
            return
        x = 0
        y = r
        d = 3 - 2 * r
        while x <= y:
            for px, py in ((cx + x, cy + y), (cx - x, cy + y),
                           (cx + x, cy - y), (cx - x, cy - y),
                           (cx + y, cy + x), (cx - y, cy + x),
                           (cx + y, cy - x), (cx - y, cy - x)):
                self.set(px, py, colour)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def arc(self, cx, cy, r, a0, a1, colour, thick=1):
        """Arc by angle in degrees, 0 = east, going clockwise (y down)."""
        steps = max(8, r * 2)
        for k in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * k / steps)
            px = int(cx + r * math.cos(a))
            py = int(cy + r * math.sin(a))
            if thick == 1:
                self.set(px, py, colour)
            else:
                self.rect(px - thick // 2, py - thick // 2, thick, thick, colour)

    def triangle(self, x0, y0, x1, y1, x2, y2, colour):
        """Filled triangle by scanline between its edges."""
        pts = sorted(((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        if ay == cy:
            return
        for yy in range(ay, cy + 1):
            xs = []
            for (px, py), (qx, qy) in (((ax, ay), (bx, by)),
                                       ((bx, by), (cx, cy)),
                                       ((ax, ay), (cx, cy))):
                if py == qy:
                    continue
                if min(py, qy) <= yy <= max(py, qy):
                    xs.append(px + (qx - px) * (yy - py) / (qy - py))
            if len(xs) >= 2:
                self.rect(int(min(xs)), yy, int(max(xs)) - int(min(xs)) + 1,
                          1, colour)


# ---------------------------------------------------------------- 5x7 font
# Each glyph is 7 rows of 5 pixels, "#" = on, "." = off. Hand-drawn here.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "00000", "01100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "00000", "00000", "00000", "01100", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    ";": ("00000", "01100", "00000", "00000", "01100", "01100", "01000"),
    "%": ("10001", "10010", "00100", "01000", "01001", "10001", "00000"),
}


def text_width(text, scale):
    """Advance width in pixels of `text` at this scale (6 units per char)."""
    return len(text) * 6 * scale


def draw_text(cv, x, y, text, scale, colour):
    """Draw uppercase text; glyphs are 5x7 scaled by `scale`."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    cv.rect(cx + gx * scale, y + gy * scale, scale, scale, colour)
        cx += 6 * scale
    return cx


def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines fitting max_width."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- scenes
# Each scene draws a simple pictogram inside the box (bx, by, bw, bh).

def scene_gulf(cv, bx, by, bw, bh):
    """Gulf strikes: island launch site, sea, drones crossing the sky."""
    water_y = by + bh - 28
    cv.rect(bx, water_y, bw, 28, SEA)
    for wx in range(bx + 10, bx + bw - 10, 36):
        cv.line(wx, water_y + 10, wx + 18, water_y + 10, WHITE, 2)
        cv.line(wx + 8, water_y + 19, wx + 24, water_y + 19, WHITE, 2)
    # island with a missile launcher on the left
    cv.rect(bx + 30, water_y - 14, 130, 14, SAND)
    cv.triangle(bx + 60, water_y - 14, bx + 76, water_y - 44, bx + 92,
                water_y - 14, INK)
    cv.line(bx + 76, water_y - 44, bx + 76, water_y - 58, RED, 3)
    # blast smoke over the launcher
    cv.circle(bx + 76, water_y - 66, 7, MID, fill=True)
    cv.circle(bx + 88, water_y - 74, 9, (150, 160, 170), fill=True)
    cv.circle(bx + 64, water_y - 76, 6, (150, 160, 170), fill=True)
    # radar dome base on the right
    rx = bx + bw - 110
    cv.rect(rx - 4, water_y - 26, 8, 26, INK)
    cv.rect(rx - 30, water_y - 6, 60, 6, INK)
    cv.arc(rx, water_y - 24, 30, 180, 360, INK)
    cv.line(rx, water_y - 24, rx + 22, water_y - 48, RED, 2)
    # three drones crossing the sky, one bursting
    for dx, dy in ((bx + 220, by + 24), (bx + 300, by + 46), (bx + 380, by + 20)):
        cv.line(dx - 14, dy - 8, dx + 14, dy + 8, INK, 3)
        cv.line(dx - 14, dy + 8, dx + 14, dy - 8, INK, 3)
        cv.circle(dx, dy, 4, INK, fill=True)
    hx, hy = bx + 380, by + 20
    for ang in range(0, 360, 45):
        cv.line(hx, hy, int(hx + 17 * math.cos(math.radians(ang))),
                int(hy + 17 * math.sin(math.radians(ang))), RED, 2)


def scene_bridge(cv, bx, by, bw, bh):
    """Kerch bridge: deck in two spans, middle span fallen into the sea."""
    water_y = by + bh - 26
    cv.rect(bx, water_y, bw, 26, SEA)
    for wx in range(bx + 8, bx + bw - 8, 34):
        cv.line(wx, water_y + 9, wx + 16, water_y + 9, WHITE, 2)
        cv.line(wx + 6, water_y + 18, wx + 22, water_y + 18, WHITE, 2)
    deck_y = by + 56
    cv.rect(bx + 12, deck_y, 176, 5, INK)
    cv.rect(bx + bw - 188, deck_y, 176, 5, INK)
    # the fallen middle span, tilted down into the water
    cv.line(bx + 194, deck_y + 2, bx + 254, water_y + 2, INK, 4)
    cv.line(bx + 202, deck_y + 8, bx + 238, deck_y + 18, RED, 2)
    # arch over the broken gap, snapped in the middle, kept in-band
    cv.arc(bx + bw // 2, deck_y + 6, 54, 180, 270, INK)
    cv.arc(bx + bw // 2, deck_y + 6, 54, 270, 360, RED)
    # piers
    for px in (bx + 84, bx + bw - 96):
        cv.rect(px, deck_y - 44, 8, 44, INK)
        cv.rect(px - 4, deck_y - 50, 16, 6, INK)
    # cables from pier tops to the deck
    cv.line(bx + 88, deck_y - 44, bx + 20, deck_y, MID, 1)
    cv.line(bx + 88, deck_y - 44, bx + 176, deck_y, MID, 1)
    cv.line(bx + bw - 92, deck_y - 44, bx + bw - 180, deck_y, MID, 1)
    cv.line(bx + bw - 92, deck_y - 44, bx + bw - 20, deck_y, MID, 1)
    # smoke puffs over the gap
    cv.circle(bx + 222, deck_y - 14, 7, MID, fill=True)
    cv.circle(bx + 236, deck_y - 24, 9, (150, 160, 170), fill=True)
    cv.circle(bx + 212, deck_y - 28, 6, (150, 160, 170), fill=True)


def scene_summit(cv, bx, by, bw, bh):
    """Three-way summit: China, US and Russia flags over a table."""
    table_y = by + bh - 22
    cv.rect(bx + 60, table_y, bw - 120, 6, INK)
    cv.rect(bx + 80, table_y + 6, 8, 16, INK)
    cv.rect(bx + bw - 88, table_y + 6, 8, 16, INK)
    for fx in (bx + 92, bx + 212, bx + 332):
        cv.rect(fx, by + 12, 4, table_y - by - 12, INK)
    # China flag: red field, gold stars
    cv.rect(bx + 96, by + 12, 52, 32, RED)
    cv.circle(bx + 108, by + 24, 4, GOLD, fill=True)
    cv.circle(bx + 124, by + 18, 2, GOLD, fill=True)
    cv.circle(bx + 128, by + 28, 2, GOLD, fill=True)
    # US flag: red-white stripes and blue canton
    for k in range(4):
        cv.rect(bx + 216, by + 12 + k * 8, 52, 4, RED)
        cv.rect(bx + 216, by + 16 + k * 8, 52, 4, WHITE)
    cv.rect(bx + 216, by + 12, 24, 16, NAVY)
    for sx in (222, 230, 238):
        for sy in (16, 24):
            cv.set(bx + sx, by + sy, WHITE)
    # Russia flag: white, blue, red bands
    cv.rect(bx + 336, by + 12, 52, 11, WHITE)
    cv.rect(bx + 336, by + 23, 52, 10, (30, 90, 180))
    cv.rect(bx + 336, by + 33, 52, 11, RED)
    # three heads behind the table
    for hx in (bx + 118, bx + 238, bx + 358):
        cv.circle(hx, table_y - 8, 10, (196, 150, 110), fill=True)
        cv.rect(hx - 12, table_y - 2, 24, 4, NAVY_SOFT)


def scene_ballot(cv, bx, by, bw, bh):
    """Alaska Senate win: ballot box, big star, 56-44 tally."""
    base_y = by + bh - 12
    # ballot box
    box_x, box_y = bx + 60, by + 34
    cv.rect(box_x, box_y, 130, 62, NAVY)
    cv.rect(box_x + 10, box_y + 10, 110, 42, WHITE)
    cv.line(box_x + 24, box_y + 32, box_x + 44, box_y + 46, RED, 4)
    cv.line(box_x + 44, box_y + 46, box_x + 96, box_y + 14, RED, 4)
    cv.rect(box_x - 12, box_y - 8, 154, 8, INK)
    cv.rect(box_x + 58, box_y - 8, 14, 8, PAPER)
    # falling ballot paper above the slot
    cv.rect(box_x + 200, by + 8, 44, 56, WHITE)
    cv.rect(box_x + 200, by + 8, 44, 3, RED)
    cv.line(box_x + 208, by + 24, box_x + 236, by + 24, MID, 2)
    cv.line(box_x + 208, by + 34, box_x + 232, by + 34, MID, 2)
    cv.line(box_x + 208, by + 44, box_x + 228, by + 44, MID, 2)
    # big gold star on the right
    sx, sy = bx + bw - 110, by + 46
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        r = 34 if i % 2 == 0 else 14
        pts.append((int(sx + r * math.cos(ang)), int(sy + r * math.sin(ang))))
    for i in range(10):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % 10]
        cv.line(x0, y0, x1, y1, GOLD, 2)
    cv.circle(sx, sy, 10, GOLD, fill=True)
    # tally under the star
    draw_text(cv, bx + bw - 148, base_y - 16, "56-44", 2, NAVY)
    # ground line
    cv.rect(bx, base_y, bw, 3, MID)


def scene_ebola(cv, bx, by, bw, bh):
    """Ebola in Congo: virus spheres with spikes beside a clinic cross."""
    # big virus sphere, left
    vx, vy = bx + 110, by + 52
    cv.circle(vx, vy, 30, RED, fill=True)
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        x0 = int(vx + 30 * math.cos(a))
        y0 = int(vy + 30 * math.sin(a))
        x1 = int(vx + 42 * math.cos(a))
        y1 = int(vy + 42 * math.sin(a))
        cv.line(x0, y0, x1, y1, RED, 3)
        cv.circle(x1, y1, 3, RED, fill=True)
    cv.circle(vx - 10, vy - 8, 5, (220, 120, 110), fill=True)
    cv.circle(vx + 8, vy + 10, 4, (220, 120, 110), fill=True)
    # smaller virus sphere, centre
    vx2, vy2 = bx + 210, by + 74
    cv.circle(vx2, vy2, 18, RED, fill=True)
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        x0 = int(vx2 + 18 * math.cos(a))
        y0 = int(vy2 + 18 * math.sin(a))
        x1 = int(vx2 + 26 * math.cos(a))
        y1 = int(vy2 + 26 * math.sin(a))
        cv.line(x0, y0, x1, y1, RED, 2)
    # clinic tent with a red cross, right
    tx, ty = bx + bw - 150, by + 30
    cv.triangle(tx, ty, tx + 120, ty, tx + 60, ty - 22, NAVY_SOFT)
    cv.rect(tx + 8, ty, 104, 52, WHITE)
    cv.rect(tx + 8, ty, 104, 3, NAVY)
    cv.rect(tx + 48, ty + 12, 24, 8, RED)
    cv.rect(tx + 56, ty + 4, 8, 24, RED)
    # ground line
    cv.rect(bx, by + bh - 12, bw, 3, MID)


def scene_cyclone(cv, bx, by, bw, bh):
    """Cyclone Xavier: spiral over a small island with a palm."""
    cx, cy = bx + 150, by + 56
    # spiral arms
    for r in (14, 26, 38, 50):
        cv.arc(cx, cy, r, -40, 200, NAVY_SOFT, thick=3)
    cv.circle(cx, cy, 8, WHITE, fill=True)
    cv.circle(cx, cy, 8, NAVY_SOFT)
    # wind streaks
    for wy in (by + 14, by + 96):
        for wx in range(bx + 250, bx + bw - 30, 40):
            cv.line(wx, wy, wx + 22, wy, MID, 2)
    # island with a palm, right
    ix = bx + bw - 130
    water_y = by + bh - 22
    cv.rect(ix - 50, water_y, 130, 22, SEA)
    cv.rect(ix - 44, water_y - 8, 118, 8, SAND)
    cv.line(ix, water_y - 8, ix + 6, water_y - 44, (120, 82, 40), 4)
    for dx, dy in ((-26, -18), (-8, -26), (14, -24), (28, -12)):
        cv.line(ix + 6, water_y - 44, ix + 6 + dx, water_y - 44 + dy,
                GREEN, 3)
    cv.circle(ix - 2, water_y - 34, 4, (120, 82, 40), fill=True)
    cv.circle(ix + 12, water_y - 36, 4, (120, 82, 40), fill=True)


# ---------------------------------------------------------------- stories

STORIES = [
    ("US HITS IRAN, IRAN HITS BACK",
     "QESHM ISLAND STRUCK; DRONES AT US BASES IN BAHRAIN AND KUWAIT",
     SKY, scene_gulf),
    ("KERCH BRIDGE SPAN FALLS",
     "UKRAINE STRIKES FOR 2ND DAY; ROAD SPAN DROPS INTO THE STRAIT",
     SKY2, scene_bridge),
    ("XI MEETS PUTIN IN SHENZHEN",
     "TRILATERAL WITH TRUMP SET FOR THURSDAY 19 NOVEMBER",
     SKY3, scene_summit),
    ("PELTOLA WINS ALASKA SENATE",
     "DEMOCRATS TAKE 56 SEATS IN THE US SENATE",
     SKY4, scene_ballot),
    ("EBOLA CASES DOUBLE IN CONGO",
     "11,000 CASES, 5,400 DEAD, WHO SAYS; CHILDREN HIT HARDEST",
     SKY5, scene_ebola),
    ("CYCLONE XAVIER HITS COOK IS.",
     "CATEGORY 5 STORM, GUSTS TO 315 KM/H, NORTHERN COOK ISLANDS",
     SKY6, scene_cyclone),
]


def draw_panel(cv, x, y, w, h, headline, sub, scene_bg, scene_fn):
    headline = headline.upper()
    sub = sub.upper()
    cv.rect(x, y, w, h, CARD)
    cv.rect(x, y, w, 2, CARD_EDGE)
    cv.rect(x, y, 2, h, CARD_EDGE)
    cv.rect(x + w - 2, y, 2, h, CARD_EDGE)
    cv.rect(x, y + h - 2, w, 2, CARD_EDGE)
    # scene band
    sx, sy, sw, sh = x + 12, y + 12, w - 24, 112
    cv.rect(sx, sy, sw, sh, scene_bg)
    scene_fn(cv, sx, sy, sw, sh)
    # headline, scale 3, wrapped to the panel width
    tx = x + 16
    max_w = w - 32
    lines = wrap_text(headline, max_w, 3)
    hy = y + 140
    for line in lines:
        draw_text(cv, tx, hy, line, 3, NAVY)
        hy += 27
    # sub-label, scale 2
    sub_lines = wrap_text(sub, max_w, 2)
    sy2 = hy + 6
    for line in sub_lines:
        draw_text(cv, tx, sy2, line, 2, SUB)
        sy2 += 18


# ---------------------------------------------------------------- PNG

def encode_png(width, height, pixels):
    """Minimal deterministic PNG: 8-bit RGB, filter 0, zlib level 6."""

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    raw = bytearray()
    stride = width * 3
    for yy in range(height):
        raw.append(0)
        raw += pixels[yy * stride:(yy + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))


def build_image():
    cv = Canvas(W, H, PAPER)
    # header band
    cv.rect(0, 0, W, 170, NAVY)
    cv.rect(0, 170, W, 4, RED)
    title = "WEDNESDAY 18 NOVEMBER 2026"
    tx = (W - text_width(title, 6)) // 2
    draw_text(cv, tx, 34, title, 6, WHITE)
    subtitle = "THE WORLD IN ONE IMAGE"
    sx = (W - text_width(subtitle, 3)) // 2
    draw_text(cv, sx, 108, subtitle, 3, GOLD)
    # small red diamonds flanking the subtitle
    for dx in (sx - 34, sx + text_width(subtitle, 3) + 22):
        cv.rect(dx, 116, 10, 10, RED)
    # six panels: 2 columns x 3 rows
    panel_w, panel_h = 488, 266
    xs = (16, 520)
    ys = (186, 466, 746)
    for i, (headline, sub, bg, fn) in enumerate(STORIES):
        draw_panel(cv, xs[i % 2], ys[i // 2], panel_w, panel_h,
                   headline, sub, bg, fn)
    return cv.pix


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(W, H, build_image())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)


if __name__ == "__main__":
    main()
