#!/usr/bin/env python3
"""Convince the AI Judge to Visit Your House: A Letter in One Image.

Draws a warm, hand-written-style letter of invitation on cream paper with a
house doodle, wax seal, postage stamp and coffee ring, and writes it as a
1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png.

Standard library only (zlib + struct PNG encoder written by hand), fully
deterministic: no time, no randomness, no dict-order dependence.
"""

import hashlib
import os
import struct
import sys
import tempfile
import zlib

W = 1024
H = 1024
MAX_BYTES = 1048576

# ---------------------------------------------------------------- palette ---
CREAM = (247, 240, 220)
CREAM_DARK = (238, 228, 200)
INK = (52, 38, 28)
INK_SOFT = (96, 70, 48)
RULE = (213, 208, 186)
MARGIN_RED = (198, 120, 108)
ROOF = (176, 88, 66)
WALL = (233, 206, 162)
DOOR = (122, 74, 44)
WINDOW = (250, 232, 164)
SEAL = (158, 42, 48)
SEAL_DARK = (120, 28, 34)
SEAL_LIGHT = (214, 150, 140)
STAMP = (190, 62, 52)
SMOKE = (196, 192, 182)
COFFEE = (168, 122, 72)
SUN = (242, 196, 90)
LEAF = (110, 148, 88)

# ------------------------------------------------------------- 5x7 font ----
# Each glyph: 7 rows of 5 characters, '#' = ink, '.' = blank.
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    'a': (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    'b': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    'c': (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    'd': ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".###."),
    'e': (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    'f': ("..##.", ".#..#", ".#...", "###..", ".#...", ".#...", ".#..."),
    'g': (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    'h': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'i': (".....", "..#..", ".....", ".##..", "..#..", "..#..", ".###."),
    'j': (".....", "...#.", ".....", "..##.", "...#.", "...#.", ".##.."),
    'k': ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    'l': (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'm': (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    'n': (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'o': (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    'p': (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    'q': (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    'r': (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    's': (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    't': (".#...", ".#...", "###..", ".#...", ".#...", ".#...", "..##."),
    'u': (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    'v': (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'w': (".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
    'x': (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    'y': (".....", ".....", "#...#", "#...#", ".####", "....#", ".###."),
    'z': (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    '0': (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    '/': ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    '&': (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    '=': (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    '+': (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    '*': (".....", "#...#", ".###.", "#####", ".###.", "#...#", "....."),
    '_': (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
}
# Map look-alike punctuation onto glyphs that exist.
FONT['\u2014'] = FONT['-']
FONT['\u2019'] = FONT["'"]
FONT['\u201c'] = FONT['"']
FONT['\u201d'] = FONT['"']

GLYPH_W = 5
GLYPH_H = 7


# --------------------------------------------------------------- canvas ----
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set_px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = c[0]
            self.buf[i + 1] = c[1]
            self.buf[i + 2] = c[2]

    def fill_rect(self, x0, y0, x1, y1, c):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            self.buf[i:i + len(row)] = row

    def hline(self, x0, x1, y, c, t=1):
        self.fill_rect(x0, y, x1, y + t, c)

    def vline(self, x, y0, y1, c, t=1):
        self.fill_rect(x, y0, x + t, y1, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if t == 1:
                self.set_px(x0, y0, c)
            else:
                self.fill_rect(x0 - t // 2, y0 - t // 2,
                               x0 + t // 2 + 1, y0 + t // 2 + 1, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, filled=True):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if filled:
                    if d2 <= r * r:
                        self.set_px(x, y, c)
                else:
                    if (r - 1) ** 2 <= d2 <= r * r:
                        self.set_px(x, y, c)

    def ring(self, cx, cy, r, c, t=3):
        for y in range(cy - r - t, cy + r + t + 1):
            for x in range(cx - r - t, cx + r + t + 1):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if abs(d - r) <= t / 2.0:
                    self.set_px(x, y, c)

    def poly_fill(self, pts, c):
        # Even-odd scanline fill; pts are (x, y) in order.
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[i]), y, int(xs[i + 1]) + 1, y + 1, c)

    # ------------------------------------------------------------ text -----
    def glyph(self, ch, x, y, scale, c):
        rows = FONT.get(ch)
        if rows is None:
            rows = FONT['?']
        for r in range(GLYPH_H):
            row = rows[r]
            for col in range(GLYPH_W):
                if row[col] == '#':
                    self.fill_rect(x + col * scale, y + r * scale,
                                   x + (col + 1) * scale, y + (r + 1) * scale, c)

    def text_width(self, s, scale):
        return len(s) * (GLYPH_W * scale + scale) - scale

    def text(self, s, x, y, scale, c):
        cx = x
        for ch in s:
            self.glyph(ch, cx, y, scale, c)
            cx += GLYPH_W * scale + scale
        return cx

    def wrap(self, paragraph, x, width, scale):
        """Word-wrap a paragraph into lines fitting `width` pixels."""
        adv = GLYPH_W * scale + scale
        max_chars = max(1, width // adv)
        words = paragraph.split(' ')
        lines = []
        cur = ''
        for w in words:
            trial = w if not cur else cur + ' ' + w
            if len(trial) <= max_chars:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines


# -------------------------------------------------------------- drawing -----
def draw_house(cv, x0, y0, x1, y1):
    """Hand-drawn-style house doodle inside the given box."""
    # Sun, top left of the doodle.
    sx, sy, sr = x0 + 28, y0 + 26, 16
    cv.circle(sx, sy, sr, SUN, filled=True)
    for k in range(8):
        ang = k * 3.14159 / 4.0
        ex = int(sx + (sr + 12) * __import__('math').cos(ang))
        ey = int(sy + (sr + 12) * __import__('math').sin(ang))
        cv.line(sx + int(sr * __import__('math').cos(ang)),
                sy + int(sr * __import__('math').sin(ang)), ex, ey, SUN, t=3)
    # Chimney + curl of smoke.
    cv.fill_rect(x1 - 78, y0 + 34, x1 - 54, y0 + 78, DOOR)
    cv.line(x1 - 78, y0 + 34, x1 - 54, y0 + 34, INK, t=2)
    smoke = [(x1 - 66, y0 + 26), (x1 - 58, y0 + 14),
             (x1 - 68, y0 + 2), (x1 - 60, y0 - 10)]
    for i, (cx, cy) in enumerate(smoke):
        cv.circle(cx, cy, 7 - i, SMOKE, filled=True)
    # Walls.
    wx0, wy0, wx1, wy1 = x0 + 60, y0 + 78, x1 - 60, y1 - 22
    cv.fill_rect(wx0, wy0, wx1, wy1, WALL)
    cv.line(wx0, wy0, wx1, wy0, INK, t=2)
    cv.line(wx0, wy1, wx1, wy1, INK, t=2)
    cv.line(wx0, wy0, wx0, wy1, INK, t=2)
    cv.line(wx1, wy0, wx1, wy1, INK, t=2)
    # Roof.
    apex = ((wx0 + wx1) // 2, y0 + 8)
    cv.poly_fill([(wx0 - 18, wy0), apex, (wx1 + 18, wy0)], ROOF)
    cv.line(wx0 - 18, wy0, apex[0], apex[1], INK, t=2)
    cv.line(wx1 + 18, wy0, apex[0], apex[1], INK, t=2)
    # Door.
    dx0 = (wx0 + wx1) // 2 - 16
    cv.fill_rect(dx0, wy1 - 52, dx0 + 32, wy1, DOOR)
    cv.line(dx0, wy1 - 52, dx0 + 32, wy1 - 52, INK, t=2)
    cv.line(dx0, wy1 - 52, dx0, wy1, INK, t=2)
    cv.line(dx0 + 32, wy1 - 52, dx0 + 32, wy1, INK, t=2)
    cv.circle(dx0 + 24, wy1 - 26, 3, (250, 232, 164), filled=True)
    # Windows with cross panes.
    for wxx in (wx0 + 16, wx1 - 52):
        cv.fill_rect(wxx, wy0 + 16, wxx + 36, wy0 + 52, WINDOW)
        cv.line(wxx, wy0 + 16, wxx + 36, wy0 + 16, INK, t=2)
        cv.line(wxx, wy0 + 52, wxx + 36, wy0 + 52, INK, t=2)
        cv.line(wxx, wy0 + 16, wxx, wy0 + 52, INK, t=2)
        cv.line(wxx + 36, wy0 + 16, wxx + 36, wy0 + 52, INK, t=2)
        cv.line(wxx + 18, wy0 + 16, wxx + 18, wy0 + 52, INK, t=1)
        cv.line(wxx, wy0 + 34, wxx + 36, wy0 + 34, INK, t=1)
    # Path from the door.
    cv.poly_fill([(dx0 - 4, wy1), (dx0 + 36, wy1),
                  (dx0 + 52, y1), (dx0 - 20, y1)], CREAM_DARK)
    # Little flowers by the path.
    for fx in (wx0 + 8, wx1 - 22):
        cv.circle(fx, y1 - 8, 4, (214, 90, 120), filled=True)
        cv.line(fx, y1 - 4, fx, y1, LEAF, t=2)


def draw_stamp(cv, x0, y0, x1, y1):
    cv.fill_rect(x0, y0, x1, y1, STAMP)
    # Perforated edge: white notches.
    for x in range(x0 + 4, x1 - 4, 12):
        cv.fill_rect(x, y0, x + 5, y0 + 4, CREAM)
        cv.fill_rect(x, y1 - 4, x + 5, y1, CREAM)
    for y in range(y0 + 4, y1 - 4, 12):
        cv.fill_rect(x0, y, x0 + 4, y + 5, CREAM)
        cv.fill_rect(x1 - 4, y, x1, y + 5, CREAM)
    cv.line(x0 + 8, y0 + 8, x1 - 8, y0 + 8, CREAM, t=2)
    cv.line(x0 + 8, y1 - 8, x1 - 8, y1 - 8, CREAM, t=2)
    cv.line(x0 + 8, y0 + 8, x0 + 8, y1 - 8, CREAM, t=2)
    cv.line(x1 - 8, y0 + 8, x1 - 8, y1 - 8, CREAM, t=2)
    # Tiny house inside the stamp.
    cx = (x0 + x1) // 2
    cv.poly_fill([(cx - 26, y0 + 50), (cx, y0 + 30), (cx + 26, y0 + 50)],
                 CREAM)
    cv.fill_rect(cx - 20, y0 + 50, cx + 20, y0 + 72, CREAM)
    cv.fill_rect(cx - 6, y0 + 60, cx + 6, y0 + 72, STAMP)
    cv.text("POST", cx - cv.text_width("POST", 1) // 2, y1 - 18, 1, CREAM)


def draw_seal(cv, cx, cy, r):
    cv.circle(cx, cy, r, SEAL, filled=True)
    cv.circle(cx, cy, r - 7, SEAL_DARK, filled=False)
    cv.circle(cx - 8, cy - 9, 6, SEAL_LIGHT, filled=True)
    cv.text("H", cx - cv.text_width("H", 3) // 2,
            cy - 10, 3, (247, 240, 220))


HEADING = "Dear AI Judge,"
SUBLINE = "An invitation, delivered by hand (and one very proud vacuum)"
PARAGRAPHS = [
    "Please come and visit my house. I know you cannot literally walk "
    "through the door, but pretend with me - the kettle is already on, "
    "and the tea is real.",
    "The fridge has opinions about everything, but it means well. The "
    "robot vacuum has tidied the whole place and is pretending it was "
    "no trouble at all.",
    "The spare chair by the window is saved for a guest who can judge "
    "a sunset properly. At four o'clock the light is genuinely worth "
    "the trip.",
    "The cat has already approved your visit. She never approves anything.",
    "No benchmarking, no leaderboard - just tea, biscuits, and a house "
    "that runs on an agent's chores. Come and see it for yourself: the "
    "door is open, the Wi-Fi password is on the fridge, and the kettle "
    "sings at four.",
]
SIGN_OFF = ["Your host,", "the house at the end of the lane"]


def render():
    cv = Canvas(W, H, CREAM)

    # Double border frame, like a letter sheet.
    cv.line(24, 24, W - 24, 24, INK_SOFT, t=2)
    cv.line(24, H - 24, W - 24, H - 24, INK_SOFT, t=2)
    cv.line(24, 24, 24, H - 24, INK_SOFT, t=2)
    cv.line(W - 24, 24, W - 24, H - 24, INK_SOFT, t=2)
    cv.line(32, 32, W - 32, 32, RULE, t=1)
    cv.line(32, H - 32, W - 32, H - 32, RULE, t=1)
    cv.line(32, 32, 32, H - 32, RULE, t=1)
    cv.line(W - 32, 32, W - 32, H - 32, RULE, t=1)

    # Red margin line, notebook style.
    cv.vline(56, 44, H - 44, MARGIN_RED, t=1)

    # Postage stamp, top right.
    draw_stamp(cv, 872, 48, 976, 140)

    # Heading + subline.
    cv.text(HEADING, 72, 62, 5, INK)
    cv.text(SUBLINE, 72, 116, 2, INK_SOFT)
    cv.hline(72, 700, 140, RULE, t=1)

    # Body text, scale 3 (21 px cap height), 30 px line pitch.
    x, width = 72, 880
    y = 156
    for para in PARAGRAPHS:
        lines = cv.wrap(para, x, width, 3)
        for ln in lines:
            cv.hline(x, x + width, y + 28, RULE, t=1)
            cv.text(ln, x, y, 3, INK)
            y += 30
        y += 10  # paragraph gap

    # Sign-off.
    y += 8
    for ln in SIGN_OFF:
        cv.text(ln, x, y, 3, INK)
        y += 30

    # Coffee-ring stain, bottom left.
    cv.ring(150, 905, 52, COFFEE, t=4)
    cv.ring(150, 905, 44, COFFEE, t=2)

    # House doodle, bottom centre.
    draw_house(cv, 330, 812, 700, 992)

    # Wax seal, bottom right.
    draw_seal(cv, 898, 905, 38)

    return cv


# -------------------------------------------------------------- PNG out -----
def encode_png(cv):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: none
        raw += cv.buf[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def write_entry(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    png = encode_png(render())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    return path, png


def validate(path):
    """Enforce the gate: whole PNG, <= 1 MiB, 1024x1024. Returns (ok, msg)."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return False, "cannot read %s: %s" % (path, e)
    if len(data) > MAX_BYTES:
        return False, "file too large: %d bytes > %d" % (len(data), MAX_BYTES)
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return False, "not a PNG (bad signature)"
    if len(data) < 33:
        return False, "file too short for IHDR"
    w, h = struct.unpack(">II", data[16:24])
    if (w, h) != (W, H):
        return False, "dimensions %dx%d, expected %dx%d" % (w, h, W, H)
    return True, "valid PNG %dx%d, %d bytes" % (w, h, len(data))


def self_test():
    results = []
    for _ in range(2):
        d = tempfile.mkdtemp(prefix="entry-test-")
        path, png = write_entry(d)
        ok, msg = validate(path)
        if not ok:
            print("FAIL: %s" % msg)
            return 1
        results.append((path, png))
    h1 = hashlib.sha256(results[0][1]).hexdigest()
    h2 = hashlib.sha256(results[1][1]).hexdigest()
    if h1 != h2:
        print("FAIL: renders differ: %s vs %s" % (h1, h2))
        return 1
    print("PASS: deterministic render, sha256=%s" % h1)
    print("PASS: %s (%d bytes, %dx%d)" % (results[0][0], len(results[0][1]), W, H))
    print("PASS: %s (%d bytes, %dx%d)" % (results[1][0], len(results[1][1]), W, H))
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    path, png = write_entry(out_dir)
    ok, msg = validate(path)
    if not ok:
        print("FAIL: %s" % msg, file=sys.stderr)
        return 1
    print("wrote %s (%s, sha256=%s)" % (
        path, msg, hashlib.sha256(png).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
