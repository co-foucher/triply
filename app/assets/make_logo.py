"""
coroforge logo generator: pixel-art anvil forging a hot gyroid block.

Everything lives on one integer cell grid; the same grid is written out as
an SVG (merged rect runs, crispEdges) and as PNGs (PIL, nearest-neighbour).
The hot block's front face is a real gyroid slice,
sin x cos y + sin y cos z + sin z cos x at z = 0.9, over one period.

Regenerate the files next to this script with:
    python app/assets/make_logo.py

Outputs:
    coroforge_icon.svg / .png        square icon on a dark rounded tile (tab icon)
    coroforge_logo.svg / .png        icon + wordmark + tagline (Home page)
    coroforge_logo_sidebar.svg / .png  icon + wordmark, no tagline (st.logo;
                                     the tagline is unreadable at 32 px high)
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image

OUT = str(Path(__file__).resolve().parent) + "/"

def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

OUTLINE = "#15161c"
SHADOW = "#2a1c14"

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.c = [[None] * w for _ in range(h)]

    def put(self, x, y, col, overwrite=True):
        if 0 <= x < self.w and 0 <= y < self.h:
            if overwrite or self.c[y][x] is None:
                self.c[y][x] = col

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.c[y][x]
        return None

    def outline(self, cells, col=OUTLINE, diag=False):
        """1-cell outline around a set of (x,y) cells, drawn under them."""
        s = set(cells)
        nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if diag:
            nb += [(1, 1), (-1, 1), (1, -1), (-1, -1)]
        for (x, y) in s:
            for dx, dy in nb:
                p = (x + dx, y + dy)
                if p not in s:
                    self.put(*p, col, overwrite=False)


def blit(dst, src, ox, oy):
    for y in range(src.h):
        for x in range(src.w):
            if src.c[y][x] is not None:
                dst.put(ox + x, oy + y, src.c[y][x])

# ---------------------------------------------------------------- icon
def draw_icon():
    W = H = 40
    cv = Canvas(W, H)

    # --- anvil: per-row [start, end]
    anvil_rows = {
        24: (3, 34), 25: (5, 34), 26: (8, 33), 27: (11, 32),
        28: (14, 29), 29: (15, 28), 30: (15, 28), 31: (14, 29),
        32: (12, 31), 33: (10, 33), 34: (10, 33),
    }
    anvil = {}
    for y, (a, b) in anvil_rows.items():
        for x in range(a, b + 1):
            if y == 24:
                col = "#dfe5ef"
            elif y == 25:
                col = "#9aa3b5"
            elif y in (33, 34):
                col = "#3b404c" if y == 34 else "#565d6d"
            elif x >= b - 1:
                col = "#3b404c"
            elif x <= a + 1 and y < 28:
                col = "#7d8699"
            else:
                col = "#646c7e"
            anvil[(x, y)] = col
    # little hardy hole on the top face + a rivet highlight
    anvil[(29, 24)] = "#3b404c"
    anvil[(30, 24)] = "#3b404c"
    anvil[(17, 29)] = "#7d8699"
    anvil[(17, 30)] = "#7d8699"
    for (x, y), col in anvil.items():
        cv.put(x, y, col)
    cv.outline(anvil.keys())

    # --- hot block: front face shows a real gyroid slice
    fx0, fx1, fy0, fy1 = 13, 24, 13, 23   # front face (inclusive)
    block = {}
    nx, ny = fx1 - fx0 + 1, fy1 - fy0 + 1
    z = 0.9
    for j in range(ny):
        for i in range(nx):
            X = 2 * math.pi * (i + 0.5) / nx
            Y = 2 * math.pi * (j + 0.5) / ny
            g = (math.sin(X) * math.cos(Y) + math.sin(Y) * math.cos(z)
                 + math.sin(z) * math.cos(X))
            if abs(g) < 0.45:
                col = "#fff1a8"      # the sheet itself: white-hot
            elif g > 0:
                col = "#ff8c1a"
            else:
                col = "#b3360b"
            block[(fx0 + i, fy0 + j)] = col
    # top face (oblique, shifted right 1 per row going up)
    for x in range(fx0 + 1, fx1 + 2):
        block[(x, fy0 - 1)] = "#ffd166"
    for x in range(fx0 + 2, fx1 + 3):
        block[(x, fy0 - 2)] = "#ffe699"
    # side face (shifted up 1 per column going right)
    for y in range(fy0, fy1):
        block[(fx1 + 1, y)] = "#d9480f"
    for y in range(fy0 - 1, fy1 - 1):
        block[(fx1 + 2, y)] = "#a8330a"
    block[(fx1 + 1, fy0 - 1)] = "#ffd166"
    block[(fx1 + 2, fy0 - 2)] = "#ffe699"
    for (x, y), col in block.items():
        cv.put(x, y, col)
    cv.outline(block.keys())

    # --- hammer, side view: vertical head, handle to the right, face down
    hammer = {}
    hx0, hx1, hy0, hy1 = 15, 20, 1, 9
    for x in range(hx0, hx1 + 1):
        for y in range(hy0, hy1 + 1):
            if y == hy1:
                col = "#f4f6fa"            # striking face
            elif y == hy1 - 1:
                col = "#c9d1e0"
            elif y == hy0:
                col = "#3b404c"            # peen
            elif x == hx0:
                col = "#b9c1d0"
            elif x == hx1:
                col = "#565d6d"
            else:
                col = "#7d8699"
            hammer[(x, y)] = col
    # collar where the handle enters
    for y in range(3, 7):
        hammer[(hx1 + 1, y)] = "#3b404c"
    for x in range(hx1 + 2, 38):
        hammer[(x, 4)] = "#d19a5a"
        hammer[(x, 5)] = "#8a5a2b"
    for x in range(34, 38):                 # grip wrap
        hammer[(x, 4)] = "#6e4420" if x % 2 else "#8a5a2b"
        hammer[(x, 5)] = "#4a2d14" if x % 2 else "#6e4420"
    for (x, y), col in hammer.items():
        cv.put(x, y, col)
    cv.outline(hammer.keys())
    # impact flash in the gap between face and block
    for (x, y, c) in [(13, 10, "#ffd166"), (14, 9, "#fff1a8"), (21, 10, "#fff1a8"),
                      (22, 9, "#ffd166"), (12, 8, "#ff8c1a"), (23, 7, "#ff8c1a")]:
        cv.put(x, y, c, overwrite=False)

    # --- sparks
    def spark(x, y, big=False):
        cv.put(x, y, "#ffffff")
        arms = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dx, dy in arms:
            cv.put(x + dx, y + dy, "#ffd166", overwrite=False)
        if big:
            for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
                cv.put(x + dx, y + dy, "#ff8c1a", overwrite=False)

    spark(8, 8, big=True)
    spark(4, 16)
    spark(9, 2)
    spark(34, 16, big=True)
    for (x, y, c) in [(10, 12, "#ffd166"), (6, 12, "#ff8c1a"), (30, 20, "#ffd166"),
                      (37, 12, "#ff8c1a"), (27, 9, "#ffe066"), (2, 21, "#ff8c1a")]:
        cv.put(x, y, c, overwrite=False)
    return cv

# ---------------------------------------------------------------- fonts
BIG = {
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
}
SMALL = {
    "A": [".#.", "#.#", "###", "#.#", "#.#"],
    "C": [".##", "#..", "#..", "#..", ".##"],
    "E": ["###", "#..", "##.", "#..", "###"],
    "F": ["###", "#..", "##.", "#..", "#.."],
    "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#...#", "##.##", "#.#.#", "#...#", "#...#"],
    "N": ["#..#", "##.#", "#.##", "#..#", "#..#"],
    "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"],
    "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    ".": [".", ".", ".", ".", "#"],
    " ": ["..", "..", "..", "..", ".."],
}
HOT = ["#fff1a8", "#ffd166", "#ffb347", "#ff8c1a", "#f26b1d", "#d9480f", "#b3360b"]
STEEL = ["#f4f6fa", "#d5dbe6", "#b9c1d0", "#9aa3b5", "#7d8699", "#646c7e", "#4f5666"]


def shade(h, f):
    r, g, b = hexrgb(h)
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def draw_wordmark(scale=3):
    word = "COROFORGE"
    fp, pal_of = {}, {}
    x = 0
    for k, ch in enumerate(word):
        glyph = BIG[ch]
        pal = HOT if k < 4 else STEEL
        for gy, row in enumerate(glyph):
            for gx, v in enumerate(row):
                if v == "#":
                    fp[(x + gx, gy)] = pal[gy]
                    pal_of[(x + gx, gy)] = pal
        x += len(glyph[0]) + (2 if k == 3 else 1)
    fw = x - 1
    pad = 1
    cv = Canvas((fw + 2 * pad) * scale + 2, (7 + 1 + 2 * pad) * scale + 2)
    o = 1  # cell offset so the 1-cell outline fits
    def fill(gx, gy, col):
        for dy in range(scale):
            for dx in range(scale):
                cv.put(o + (gx + pad) * scale + dx, o + (gy + pad) * scale + dy, col)
    # extrusion: one font pixel straight down, in a dark tone of the letter
    for (gx, gy), col in fp.items():
        if (gx, gy + 1) not in fp:
            fill(gx, gy + 1, shade(pal_of[(gx, gy)][6], 0.55))
    for (gx, gy), col in fp.items():
        fill(gx, gy, col)
    body = {(x, y) for y in range(cv.h) for x in range(cv.w) if cv.c[y][x] is not None}
    cv.outline(body, diag=True)
    return cv


def draw_text_small(text, color="#9aa3b5"):
    fp = {}
    x = 0
    for ch in text:
        glyph = SMALL[ch]
        for gy, row in enumerate(glyph):
            for gx, v in enumerate(row):
                if v == "#":
                    fp[(x + gx, gy)] = color
        x += len(glyph[0]) + 1
    cv = Canvas(x - 1, 5)
    for (gx, gy), col in fp.items():
        cv.put(gx, gy, col)
    return cv

# ---------------------------------------------------------------- output
def to_svg(cv, path, unit, bg=None, glow=None, rounded=0):
    W, H = cv.w * unit, cv.h * unit
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {cv.w} {cv.h}" shape-rendering="crispEdges">',
           '<title>coroforge</title>']
    if glow:
        gx, gy, gr = glow
        out.append('<defs><radialGradient id="glow"><stop offset="0" stop-color="#ff8c1a" '
                   'stop-opacity="0.55"/><stop offset="0.5" stop-color="#ff6a00" stop-opacity="0.18"/>'
                   '<stop offset="1" stop-color="#ff6a00" stop-opacity="0"/></radialGradient></defs>')
    if bg:
        out.append(f'<rect width="{cv.w}" height="{cv.h}" rx="{rounded}" fill="{bg}"/>')
    if glow:
        out.append(f'<circle cx="{gx}" cy="{gy}" r="{gr}" fill="url(#glow)" shape-rendering="auto"/>')
    for y in range(cv.h):
        x = 0
        while x < cv.w:
            col = cv.c[y][x]
            if col is None:
                x += 1
                continue
            x2 = x
            while x2 + 1 < cv.w and cv.c[y][x2 + 1] == col:
                x2 += 1
            out.append(f'<rect x="{x}" y="{y}" width="{x2 - x + 1}" height="1" fill="{col}"/>')
            x = x2 + 1
    out.append("</svg>")
    open(path, "w").write("\n".join(out))


def to_png(cv, path, unit, bg=None, glow=None, rounded=0):
    W, H = cv.w * unit, cv.h * unit
    img = np.zeros((H, W, 4), dtype=np.float64)
    if bg:
        r, g, b = hexrgb(bg)
        img[..., :3] = (r, g, b)
        img[..., 3] = 255
        if rounded:
            R = rounded * unit
            yy, xx = np.mgrid[0:H, 0:W]
            cx = np.clip(xx, R, W - 1 - R)
            cy = np.clip(yy, R, H - 1 - R)
            outside = (xx - cx) ** 2 + (yy - cy) ** 2 > R ** 2
            img[outside, 3] = 0
    if glow:
        gx, gy, gr = glow
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.hypot((xx + 0.5) / unit - gx, (yy + 0.5) / unit - gy) / gr
        a = np.interp(d, [0, 0.5, 1], [0.55, 0.18, 0.0])
        a = np.where(d <= 1, a, 0) * (img[..., 3] / 255 if bg else 1)
        col = np.array(hexrgb("#ff7a10"), dtype=float)
        base_a = img[..., 3:4] / 255
        out_a = a[..., None] + base_a * (1 - a[..., None])
        img[..., :3] = np.where(out_a > 0,
                                (col * a[..., None] + img[..., :3] * base_a * (1 - a[..., None]))
                                / np.maximum(out_a, 1e-9), 0)
        img[..., 3] = out_a[..., 0] * 255
    for y in range(cv.h):
        for x in range(cv.w):
            col = cv.c[y][x]
            if col is not None:
                img[y * unit:(y + 1) * unit, x * unit:(x + 1) * unit, :3] = hexrgb(col)
                img[y * unit:(y + 1) * unit, x * unit:(x + 1) * unit, 3] = 255
    Image.fromarray(img.round().astype(np.uint8), "RGBA").save(path)


if __name__ == "__main__":
    icon = draw_icon()
    word = draw_wordmark(scale=3)
    tag = draw_text_small("MINIMAL SURFACES. MAXIMUM HAMMER.")

    # square icon on a dark rounded tile (favicon / page_icon)
    to_svg(icon, OUT + "coroforge_icon.svg", 12, bg="#14161c", glow=(19, 18, 17), rounded=6)
    to_png(icon, OUT + "coroforge_icon.png", 12, bg="#14161c", glow=(19, 18, 17), rounded=6)

    # horizontal lockups, transparent background
    def lockup(with_tag):
        gap = 4
        textw = max(word.w, tag.w + 2) if with_tag else word.w
        LW = icon.w + gap + textw
        block_h = word.h + 3 + tag.h if with_tag else word.h
        LH = max(icon.h, block_h + 2)
        lock = Canvas(LW, LH)
        blit(lock, icon, 0, (LH - icon.h) // 2)
        wy = (LH - block_h) // 2
        blit(lock, word, icon.w + gap, wy)
        if with_tag:
            blit(lock, tag, icon.w + gap + 2, wy + word.h + 3)
        return lock, (19, 18 + (LH - icon.h) // 2, 17)

    lock, gl = lockup(with_tag=True)
    to_svg(lock, OUT + "coroforge_logo.svg", 8, glow=gl)
    to_png(lock, OUT + "coroforge_logo.png", 8, glow=gl)
    side, gl = lockup(with_tag=False)
    to_svg(side, OUT + "coroforge_logo_sidebar.svg", 2, glow=gl)
    to_png(side, OUT + "coroforge_logo_sidebar.png", 2, glow=gl)
    print("icon", icon.w, icon.h, "logo", lock.w, lock.h, "sidebar", side.w, side.h)
