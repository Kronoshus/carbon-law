"""The shared character-stage backdrops for the four app themes besides Día de Muertos (sol, huerto, vela, codice).
One square picture per theme, used behind all three characters. Drawn flat and soft, in the style of the per-character
backdrops (pinata_art.backdrop, oso_art.backdrop). The character covers the middle third from y 0.25 down, and the lesson
screen crops roughly y 0.15-0.65, so the detail sits at the top and in the side thirds and the centre stays quiet.
Run:  python characters/backdrops.py [theme ...]   ->  aprende/public/characters/backdrops/<theme>.jpg
"""
import math, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from charkit import Art

S, OUT = 2048, 1024
DEST = Path(__file__).resolve().parent.parent / "aprende/public/characters/backdrops"


def oklch(l, c, h):
    """oklch(l% c h) to an sRGB tuple."""
    a, b = c * math.cos(math.radians(h)), c * math.sin(math.radians(h))
    l /= 100
    l_, m_, s_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3, (l - 0.1055613458 * a - 0.0638541728 * b) ** 3, \
                 (l - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    enc = lambda v: 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return tuple(round(255 * min(1, max(0, enc(v)))) for v in rgb)


def mix(c0, c1, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(c0, c1))


def canvas(stops):
    """A picture with a vertical gradient through stops [(y, colour), ...]."""
    a = Art(1.0, 0.0, size=S, mode="RGBA", bg=(0, 0, 0, 255))
    for y in range(S):
        t = y / S
        for (y0, c0), (y1, c1) in zip(stops, stops[1:]):
            if y0 <= t <= y1:
                a.d.line([(0, y), (S, y)], fill=mix(c0, c1, (t - y0) / (y1 - y0)))
                break
    return a


def layer(a, draw, blur=0.0, alpha=255, tint=(0, 0, 0)):
    """Draw with draw(ImageDraw, art) on a transparent layer, blur it, lay it on the picture at `alpha`. The clear
    pixels carry `tint`, so a blurred edge fades in the drawn colour instead of going grey."""
    lay = Image.new("RGBA", a.img.size, (*tint, 0))
    draw(ImageDraw.Draw(lay), a)
    if blur:
        lay = lay.filter(ImageFilter.GaussianBlur(S * blur))
    if alpha < 255:
        lay.putalpha(lay.split()[3].point(lambda v: v * alpha // 255))
    a.img.alpha_composite(lay)
    a.d = ImageDraw.Draw(a.img)


def glow(a, cx, cy, rx, ry, col, alpha, blur):
    layer(a, lambda d, a: d.ellipse([*a.P(cx - rx, cy - ry), *a.P(cx + rx, cy + ry)], fill=(*col, alpha)), blur, tint=col)


def hill(a, y, amp, waves, phase, col, y_end=1.02):
    pts = [(x / 80, y + amp * math.sin(2 * math.pi * waves * x / 80 + phase)) for x in range(81)]
    a.shape(pts + [(1, y_end), (0, y_end)], col, outline=None)


def petals(a, cx, cy, r, n, col, centre, length=1.0, width=0.42, off=0.0):
    for i in range(n):
        t = 2 * math.pi * i / n + off
        a.d.polygon(a.ell(cx + math.cos(t) * r * 0.55 * length, cy + math.sin(t) * r * 0.55 * length,
                          r * 0.55 * length, r * width, 24, t), fill=col)
    a.dot(cx, cy, r * 0.32, centre)


def leaf(a, x, y, ang, length, width, col):
    """A pointed leaf from (x, y) pointing along ang."""
    c, s = math.cos(ang), math.sin(ang)
    half = [(length * u, width * math.sin(math.pi * u) ** 0.8) for u in [i / 14 for i in range(15)]]
    a.shape([(x + c * u - s * v, y + s * u + c * v) for u, v in half] +
            [(x + c * u + s * v, y + s * u - c * v) for u, v in half[::-1]], col, outline=None)


def finish(a, blur=0.0012):
    img = a.img.convert("RGB")
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(S * blur))
    return img.resize((OUT, OUT), Image.LANCZOS)


# ---------------------------------------------------------------- sol: a sunny morning
def sol():
    PAPER, PEAR, BLUE, CORAL = oklch(97, 0.012, 95), oklch(87, 0.175, 96), oklch(50, 0.17, 250), oklch(70, 0.2, 22)
    MINT, LEAF, HILL1, HILL2 = oklch(82, 0.15, 152), oklch(64, 0.15, 150), oklch(94.5, 0.03, 118), oklch(91.5, 0.045, 135)
    SKY = oklch(89, 0.035, 236)
    a = canvas([(0, SKY), (0.42, mix(SKY, PAPER, 0.75)), (0.62, PAPER), (1, PAPER)])
    glow(a, 0.5, 0.48, 0.26, 0.3, PAPER, 200, 0.07)                       # a quiet bright patch behind the head

    sx, sy, sr = 0.2, 0.19, 0.085                                          # the sun: halo, a ring of soft rays, the disc
    glow(a, sx, sy, 0.24, 0.24, mix(PEAR, PAPER, 0.45), 150, 0.06)
    layer(a, lambda d, a: [d.polygon(a.ell(sx + math.cos(t) * sr * 1.62, sy + math.sin(t) * sr * 1.62, sr * 0.34, sr * 0.15,
                                           20, t), fill=(*mix(PEAR, PAPER, 0.35), 255))
                           for t in (2 * math.pi * i / 14 for i in range(14))])
    a.dot(sx, sy, sr * 1.22, mix(PEAR, PAPER, 0.55))
    a.dot(sx, sy, sr, PEAR)

    def cloud(cx, cy, k):
        puffs = [(-0.068, 0.0, 0.034), (-0.03, -0.024, 0.046), (0.022, -0.034, 0.056), (0.066, -0.004, 0.038)]
        for dy, col in ((0.012, mix(SKY, BLUE, 0.14)), (0.0, (255, 255, 253))):   # a blue underside, then the white
            for dx, py, r in puffs:
                a.dot(cx + dx * k, cy + (py + dy) * k, r * k, col)
            a.d.rounded_rectangle([*a.P(cx - 0.1 * k, cy - 0.01 * k + dy * k), *a.P(cx + 0.1 * k, cy + 0.032 * k + dy * k)],
                                  radius=a.w(0.021 * k), fill=col)

    cloud(0.76, 0.15, 1.2)
    cloud(0.86, 0.37, 0.62)
    cloud(0.13, 0.44, 0.58)
    cloud(0.45, 0.08, 0.5)
    for bx, by, r in ((0.6, 0.2, 0.014), (0.64, 0.24, 0.011), (0.57, 0.26, 0.009)):   # three birds
        a.arc(bx - r, by, r, r * 0.8, math.pi * 1.15, math.pi * 1.85, mix(BLUE, SKY, 0.25), 0.0035)
        a.arc(bx + r, by, r, r * 0.8, math.pi * 1.15, math.pi * 1.85, mix(BLUE, SKY, 0.25), 0.0035)

    hill(a, 0.6, 0.018, 1.2, 0.4, HILL1)
    for tx, ty, r in ((0.07, 0.575, 0.026), (0.115, 0.585, 0.018), (0.2, 0.588, 0.014), (0.8, 0.592, 0.015),
                      (0.86, 0.582, 0.022), (0.915, 0.575, 0.028)):                       # far trees
        a.d.line(a.pts([(tx, ty), (tx, ty + r * 1.7)]), fill=mix(LEAF, HILL1, 0.3), width=a.w(0.005))
        a.dot(tx, ty, r, mix(LEAF, HILL1, 0.3))
        a.dot(tx - r * 0.3, ty - r * 0.3, r * 0.45, mix(LEAF, HILL1, 0.55))
    hill(a, 0.7, 0.022, 0.9, 2.2, HILL2)
    hill(a, 0.83, 0.03, 0.7, 4.0, mix(HILL2, MINT, 0.35))

    rnd = random.Random(5)
    for x0, x1 in ((0.05, 0.3), (0.7, 0.95)):                              # flowers in the side thirds
        for i in range(9):
            x, y = rnd.uniform(x0, x1), rnd.uniform(0.76, 0.95)
            h = rnd.uniform(0.035, 0.06)
            a.line([(x, y), (x + rnd.uniform(-0.006, 0.006), y + h)], LEAF, 0.0045)
            a.d.polygon(a.ell(x + 0.012, y + h * 0.6, 0.012, 0.005, 16, -0.6), fill=LEAF)
            kind = i % 3
            if kind == 0:
                petals(a, x, y, 0.02, 6, CORAL, PEAR)
            elif kind == 1:
                petals(a, x, y, 0.017, 8, (255, 255, 253), PEAR, width=0.32)
            else:
                petals(a, x, y, 0.015, 5, mix(BLUE, SKY, 0.35), PAPER)
        for i in range(14):                                                 # grass tufts
            x, y = rnd.uniform(x0, x1), rnd.uniform(0.8, 0.98)
            for k in (-1, 0, 1):
                a.line([(x, y), (x + k * 0.008, y - 0.022 + abs(k) * 0.006)], mix(LEAF, MINT, 0.4), 0.003)
    return finish(a)


# ---------------------------------------------------------------- huerto: an orchard in daylight
def huerto():
    WARM, PEACH, SUNNY = oklch(97, 0.012, 85), oklch(83, 0.115, 56), oklch(88, 0.14, 85)
    G = lambda l, c=0.1: oklch(l, c, 154)
    TRUNK, CORAL = oklch(48, 0.06, 55), oklch(72, 0.15, 35)
    HZ = 0.53
    a = canvas([(0, mix(WARM, oklch(92, 0.03, 220), 0.5)), (0.3, WARM), (HZ, mix(WARM, PEACH, 0.35)), (1, WARM)])
    glow(a, 0.8, 0.15, 0.2, 0.2, SUNNY, 170, 0.06)                          # sun, top right
    a.dot(0.8, 0.15, 0.065, mix(SUNNY, WARM, 0.35))
    a.dot(0.8, 0.15, 0.052, SUNNY)
    for cx, cy, k in ((0.16, 0.12, 1.0), (0.42, 0.06, 0.6), (0.58, 0.27, 0.5)):   # flat little clouds
        for dx, dy, r in ((-0.05, 0.005, 0.03), (-0.015, -0.015, 0.04), (0.03, -0.005, 0.034), (0.06, 0.008, 0.024)):
            a.dot(cx + dx * k, cy + dy * k, r * k, (255, 254, 250))
        a.d.rectangle([*a.P(cx - 0.05 * k, cy + 0.005 * k), *a.P(cx + 0.06 * k, cy + 0.032 * k)], fill=(255, 254, 250))

    hill(a, HZ - 0.03, 0.015, 1.3, 0.8, G(80, 0.06))                         # far hills, then the orchard floor
    a.d.rectangle([*a.P(0, HZ), *a.P(1, 1.01)], fill=G(66, 0.11))
    row_x = lambda i, y: 0.5 + i * (0.012 + 0.188 * (y - HZ) / (1.01 - HZ))   # the row lines meet on the horizon
    for i in range(-9, 10, 2):                                              # mown strips between the rows
        a.shape([(row_x(i - 0.5, HZ), HZ), (row_x(i + 0.5, HZ), HZ), (row_x(i + 0.5, 1.01), 1.01), (row_x(i - 0.5, 1.01), 1.01)],
                G(70, 0.12), outline=None)
    shade_ = Image.new("L", (1, S), 0)                                      # the floor darkens toward the viewer
    for y in range(S):
        t = (y / S - HZ) / (1 - HZ)
        shade_.putpixel((0, y), int(150 * max(0, t) ** 1.6))
    a.img.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (S, S), G(41)).split(), shade_.resize((S, S)))))
    a.d = ImageDraw.Draw(a.img)

    rnd = random.Random(8)
    FRUIT = (PEACH, SUNNY, CORAL, PEACH)

    def tree(x, y, s, fruit=True):
        a.d.polygon(a.ell(x, y + 0.01 * s, 0.07 * s, 0.014 * s, 40), fill=(*G(41), ))
        a.shape([(x - 0.009 * s, y), (x + 0.009 * s, y), (x + 0.006 * s, y - 0.09 * s), (x - 0.006 * s, y - 0.09 * s)], TRUNK,
                outline=None)
        cy = y - 0.15 * s
        a.dot(x, cy, 0.085 * s, G(48, 0.11))
        a.dot(x - 0.012 * s, cy - 0.012 * s, 0.073 * s, G(58, 0.13))
        a.dot(x - 0.03 * s, cy - 0.03 * s, 0.032 * s, G(66, 0.13))
        if fruit:
            r, placed = 0.011 * min(s, 1.1), []
            for _ in range(int(10 + 10 * s)):
                ang, rr = rnd.uniform(0, 2 * math.pi), 0.07 * s * math.sqrt(rnd.random())
                fx, fy = x + math.cos(ang) * rr, cy + math.sin(ang) * rr
                if any(math.hypot(fx - px, fy - py) < r * 2.6 for px, py in placed):
                    continue
                placed.append((fx, fy))
                a.dot(fx, fy + r * 0.25, r, oklch(55, 0.1, 40))
                a.dot(fx, fy, r, rnd.choice(FRUIT))
                a.dot(fx - r * 0.35, fy - r * 0.35, r * 0.3, WARM)

    trees = [(y, i) for i in (-4, -3, -2, 2, 3, 4) for y in (HZ + 0.012 * 1.55 ** k for k in range(8))]
    for y, i in sorted(trees):                                              # back to front, leaving the middle alley open
        x, s = row_x(i, y), 0.12 + 2.3 * (y - HZ)
        if 0.04 < x < 0.96 and not (0.3 < x < 0.7 and s > 0.4):
            tree(x, y, s, s > 0.3)
    tree(0.11, 1.08, 2.3)                                                   # two big trees framing the stage
    tree(0.89, 1.07, 2.2)
    for x0, x1 in ((0.02, 0.3), (0.7, 0.98)):                               # grass and a few windfalls
        for _ in range(16):
            x, y = rnd.uniform(x0, x1), rnd.uniform(0.86, 0.99)
            for k in (-1, 0, 1):
                a.line([(x, y), (x + k * 0.009, y - 0.026 + abs(k) * 0.007)], G(62, 0.13), 0.0035)
        for _ in range(4):
            x, y = rnd.uniform(x0, x1), rnd.uniform(0.9, 0.97)
            a.dot(x, y, 0.011, rnd.choice(FRUIT))
    return finish(a)


# ---------------------------------------------------------------- vela: the candle-lit still life at night
def vela():
    INK, PARCH, OCHRE = oklch(15, 0.012, 60), oklch(93, 0.03, 85), oklch(74, 0.13, 80)
    WOOD = oklch(24, 0.035, 55)
    a = canvas([(0, INK), (0.55, oklch(21, 0.03, 58)), (0.78, oklch(26, 0.04, 60)), (1, oklch(20, 0.03, 58))])
    glow(a, 0.5, 0.62, 0.55, 0.42, OCHRE, 45, 0.09)                          # the room's warm light

    # a tall arched window, top left, with a few stars
    wx0, wx1, wy0, wy1 = 0.09, 0.27, 0.1, 0.44
    win = a.ell((wx0 + wx1) / 2, wy0 + 0.09, (wx1 - wx0) / 2, 0.09, 40, 0, math.pi, 2 * math.pi) + a.pts([(wx1, wy1), (wx0, wy1)])
    a.d.polygon(win, fill=oklch(27, 0.04, 255))
    for sx_, sy_ in ((0.13, 0.17), (0.21, 0.14), (0.17, 0.27), (0.24, 0.33), (0.115, 0.37)):
        a.dot(sx_, sy_, 0.0035, PARCH)
    a.dot(0.22, 0.22, 0.026, mix(PARCH, OCHRE, 0.2))
    a.dot(0.232, 0.212, 0.022, oklch(27, 0.04, 255))
    a.d.line(win + [win[0]], fill=oklch(31, 0.04, 60), width=a.w(0.012))
    a.line([((wx0 + wx1) / 2, wy0), ((wx0 + wx1) / 2, wy1)], oklch(31, 0.04, 60), 0.008)
    a.line([(wx0, 0.27), (wx1, 0.27)], oklch(31, 0.04, 60), 0.008)
    a.d.rectangle([*a.P(wx0 - 0.02, wy1), *a.P(wx1 + 0.02, wy1 + 0.018)], fill=oklch(30, 0.04, 60))

    # the table
    a.d.rectangle([*a.P(0, 0.8), *a.P(1, 1.01)], fill=WOOD)
    a.d.rectangle([*a.P(0, 0.8), *a.P(1, 0.812)], fill=oklch(34, 0.05, 62))

    flames = []

    def candle(x, top, w, base=0.81):
        a.d.polygon(a.ell(x, base, w * 1.7, 0.01, 40), fill=oklch(17, 0.02, 55))   # shadow on the table
        a.d.rounded_rectangle([*a.P(x - w, top), *a.P(x + w, base)], radius=a.w(w * 0.25), fill=mix(PARCH, OCHRE, 0.12))
        a.d.rectangle([*a.P(x + w * 0.35, top + 0.01), *a.P(x + w, base)], fill=mix(PARCH, WOOD, 0.22))
        a.d.polygon(a.ell(x, top, w, w * 0.32, 30), fill=PARCH)
        for dx, ln in ((-0.6, 0.05), (0.15, 0.028), (0.7, 0.04)):           # drips
            a.d.rounded_rectangle([*a.P(x + dx * w - w * 0.16, top), *a.P(x + dx * w + w * 0.16, top + ln)],
                                  radius=a.w(w * 0.16), fill=PARCH)
        a.line([(x, top), (x, top - 0.014)], INK, 0.003)
        flames.append((x, top - 0.035, w))

    candle(0.18, 0.46, 0.028)                                                # left group
    candle(0.27, 0.62, 0.024)
    candle(0.1, 0.68, 0.03)
    # an hourglass, right, between candles
    hx, hy0, hy1, hw = 0.8, 0.6, 0.8, 0.05
    a.d.rectangle([*a.P(hx - hw - 0.012, hy1 - 0.018), *a.P(hx + hw + 0.012, hy1)], fill=oklch(33, 0.05, 62))
    a.d.rectangle([*a.P(hx - hw - 0.012, hy0), *a.P(hx + hw + 0.012, hy0 + 0.018)], fill=oklch(33, 0.05, 62))
    glass = [(hx - hw, hy0 + 0.018), (hx + hw, hy0 + 0.018), (hx + 0.006, (hy0 + hy1) / 2), (hx + hw, hy1 - 0.018),
             (hx - hw, hy1 - 0.018), (hx - 0.006, (hy0 + hy1) / 2)]
    a.shape(glass, oklch(30, 0.03, 70), outline=None)
    a.shape([(hx - hw * 0.45, hy0 + 0.06), (hx + hw * 0.45, hy0 + 0.06), (hx, (hy0 + hy1) / 2)], mix(OCHRE, WOOD, 0.3), outline=None)
    a.shape([(hx, hy1 - 0.05), (hx + hw * 0.8, hy1 - 0.018), (hx - hw * 0.8, hy1 - 0.018)], mix(OCHRE, WOOD, 0.3), outline=None)
    a.line([(hx, (hy0 + hy1) / 2), (hx, hy1 - 0.05)], mix(OCHRE, WOOD, 0.3), 0.002)
    for side in (-1, 1):
        a.line([(hx + side * (hw + 0.006), hy0 + 0.018), (hx + side * (hw + 0.006), hy1 - 0.018)], oklch(40, 0.06, 65), 0.006)
        a.line([(hx + side * hw * 0.92, hy0 + 0.022), (hx + side * 0.008, (hy0 + hy1) / 2), (hx + side * hw * 0.92, hy1 - 0.022)],
               mix(PARCH, WOOD, 0.45), 0.0025)
    a.d.rectangle([*a.P(hx - hw - 0.012, hy0), *a.P(hx + hw + 0.012, hy0 + 0.004)], fill=mix(OCHRE, WOOD, 0.35))
    a.d.rectangle([*a.P(hx - hw - 0.012, hy1 - 0.018), *a.P(hx + hw + 0.012, hy1 - 0.014)], fill=mix(OCHRE, WOOD, 0.35))
    candle(0.9, 0.5, 0.027)                                                  # right group
    candle(0.69, 0.71, 0.022)
    candle(0.4, 0.75, 0.02)                                                  # two low ones at the front, mostly behind
    candle(0.6, 0.73, 0.02)
    # a little wall shelf on the right for one more candle
    BRASS = oklch(36, 0.05, 62)
    a.d.rectangle([*a.P(0.82, 0.25), *a.P(0.92, 0.262)], fill=BRASS)
    a.d.rectangle([*a.P(0.82, 0.25), *a.P(0.92, 0.253)], fill=oklch(46, 0.07, 70))
    for bx in (0.835, 0.905):                                               # two small corbels under it
        a.shape([(bx - 0.007, 0.262), (bx + 0.007, 0.262), (bx + 0.004, 0.29), (bx - 0.004, 0.29)], BRASS, outline=None)
    candle(0.87, 0.16, 0.018, base=0.25)
    for x, y, w in flames:                                                   # glows, then the flames on top
        glow(a, x, y + 0.01, w * 6, w * 6, OCHRE, 70, 0.04)
        glow(a, x, y, w * 2.2, w * 2.6, mix(OCHRE, PARCH, 0.3), 110, 0.012)
    for x, y, w in flames:
        f = w * 0.55
        body = [(x + f * math.cos(t), y + f * 0.9 * math.sin(t)) for t in (math.pi * i / 20 for i in range(21))]
        a.shape(body + [(x - f * 0.55, y - f * 1.3), (x, y - f * 2.6), (x + f * 0.55, y - f * 1.3)], OCHRE, outline=None)
        a.blob(x, y - f * 0.1, f * 0.5, f * 0.85, mix(OCHRE, PARCH, 0.7), w=0, outline=None)

    rnd = random.Random(4)
    for _ in range(26):                                                      # specks of light drifting in the warm air
        x, y = rnd.choice([rnd.uniform(0.04, 0.3), rnd.uniform(0.7, 0.96)]), rnd.uniform(0.12, 0.75)
        a.dot(x, y, rnd.uniform(0.0015, 0.003), mix(OCHRE, PARCH, 0.4))
    return finish(a, 0.0018)


# ---------------------------------------------------------------- codice: an illuminated manuscript page
def codice():
    PARCH, UMBER, ULTRA, GOLD = oklch(94, 0.024, 82), oklch(23, 0.025, 55), oklch(43, 0.17, 268), oklch(80, 0.11, 85)
    GOLD_D = oklch(64, 0.11, 75)
    a = canvas([(0, PARCH), (1, mix(PARCH, oklch(88, 0.035, 78), 0.6))])
    noise = Image.effect_noise((S // 32, S // 32), 40).resize((S, S), Image.BICUBIC).filter(ImageFilter.GaussianBlur(S * 0.01))
    stain = Image.new("RGBA", (S, S), (*oklch(80, 0.05, 70), 0))
    stain.putalpha(noise.point(lambda v: max(0, v - 128) // 3))
    a.img.alpha_composite(stain)
    layer(a, lambda d, a: d.rectangle([*a.P(-0.1, -0.1), *a.P(1.1, 1.1)], outline=(*oklch(70, 0.06, 65), 120),
                                      width=a.w(0.2)), blur=0.05)          # edges a little darker, like an old page
    a.d = ImageDraw.Draw(a.img)

    O, I = 0.07, 0.135                                                       # outer and inner edge of the border band
    rule = lambda d, a: [d.line(a.pts([(0.2, y), (0.8, y)]), fill=(*UMBER, 34), width=a.w(0.0016))
                         for y in [0.2 + 0.042 * k for k in range(17)]]
    layer(a, rule)
    layer(a, lambda d, a: [d.line(a.pts([(x, 0.17), (x, 0.9)]), fill=(*UMBER, 30), width=a.w(0.0016)) for x in (0.2, 0.8)])

    def rect(m, col, w):
        a.d.rectangle([*a.P(m, m), *a.P(1 - m, 1 - m)], outline=col, width=a.w(w))

    BAND = mix(PARCH, (255, 255, 255), 0.35)
    for box in ((O, O, 1 - O, I), (O, 1 - I, 1 - O, 1 - O), (O, O, I, 1 - O), (1 - I, O, 1 - O, 1 - O)):
        a.d.rectangle([*a.P(*box[:2]), *a.P(*box[2:])], fill=BAND)
    rect(O, UMBER, 0.004)
    rect(O + 0.007, GOLD, 0.005)
    rect(I, UMBER, 0.003)
    rect(I - 0.006, GOLD, 0.003)

    def vine(p0, p1, waves, amp):
        """A gold stem waving from p0 to p1 with ultramarine leaves, curls and gold berries in each bay."""
        (x0, y0), (x1, y1) = p0, p1
        L = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        nx, ny = -uy, ux
        at = lambda t, off: (x0 + ux * L * t + nx * off, y0 + uy * L * t + ny * off)
        stem = [at(i / 200, amp * math.sin(2 * math.pi * waves * i / 200)) for i in range(201)]
        a.line(stem, GOLD_D, 0.0075)
        a.line(stem, GOLD, 0.0045)
        for k in range(int(waves * 2)):
            t = (k + 0.5) / (waves * 2)
            side = 1 if k % 2 == 0 else -1
            bx, by = at(t, side * amp)
            # each crest sends a pair of ultramarine leaves down into the bay below it and a trefoil out above it
            for fwd in (-1, 1):
                dx, dy = fwd * ux - side * nx * 1.3, fwd * uy - side * ny * 1.3
                leaf(a, bx, by, math.atan2(dy, dx), 0.025, 0.0085, ULTRA)
            for q in range(3):
                qa = math.atan2(side * ny, side * nx) + (q - 1) * 1.1
                a.dot(bx + side * nx * 0.008 + math.cos(qa) * 0.0035, by + side * ny * 0.008 + math.sin(qa) * 0.0035, 0.003, ULTRA)
            a.dot(bx, by, 0.0055, GOLD_D)
            a.dot(bx, by, 0.0042, GOLD)

    m = (O + I) / 2 + 0.003
    vine((m, I + 0.02), (m, 1 - I - 0.02), 5, 0.0145)
    vine((1 - m, I + 0.02), (1 - m, 1 - I - 0.02), 5, 0.0145)
    vine((I + 0.02, m), (1 - I - 0.02, m), 5, 0.0145)
    vine((I + 0.02, 1 - m), (1 - I - 0.02, 1 - m), 5, 0.0145)
    for cx in (m, 1 - m):                                                    # corner roundels
        for cy in (m, 1 - m):
            a.dot(cx, cy, 0.031, UMBER)
            a.dot(cx, cy, 0.028, GOLD)
            petals(a, cx, cy, 0.024, 4, ULTRA, GOLD, width=0.5, off=math.pi / 4)

    # an ornamented square in the top left, where an initial would sit (left empty of letters: a flower on blue)
    x0, y0, x1, y1 = 0.17, 0.17, 0.33, 0.33
    a.d.rectangle([*a.P(x0 - 0.008, y0 - 0.008), *a.P(x1 + 0.008, y1 + 0.008)], fill=GOLD, outline=UMBER, width=a.w(0.003))
    a.d.rectangle([*a.P(x0, y0), *a.P(x1, y1)], fill=ULTRA)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for k in range(4):
        t = math.pi / 2 * k + math.pi / 4
        leaf(a, cx + math.cos(t) * 0.03, cy + math.sin(t) * 0.03, t, 0.04, 0.011, GOLD)
    petals(a, cx, cy, 0.04, 8, GOLD, ULTRA, width=0.36)
    for dx in (-1, 1):
        for dy in (-1, 1):
            a.dot(cx + dx * 0.068, cy + dy * 0.068, 0.006, GOLD)

    # top right: an hourglass in gold and umber, with a little spray of leaves
    hx, hy0, hy1, hw = 0.75, 0.17, 0.32, 0.034
    for y in (hy0, hy1 - 0.014):
        a.d.rounded_rectangle([*a.P(hx - hw - 0.012, y), *a.P(hx + hw + 0.012, y + 0.014)], radius=a.w(0.004), fill=GOLD,
                              outline=UMBER, width=a.w(0.0025))
    glass = [(hx - hw, hy0 + 0.014), (hx + hw, hy0 + 0.014), (hx + 0.004, (hy0 + hy1) / 2), (hx + hw, hy1 - 0.014),
             (hx - hw, hy1 - 0.014), (hx - 0.004, (hy0 + hy1) / 2)]
    a.shape(glass, mix(PARCH, (255, 255, 255), 0.4), outline=UMBER, w=0.0014)
    a.shape([(hx - hw * 0.5, hy0 + 0.05), (hx + hw * 0.5, hy0 + 0.05), (hx, (hy0 + hy1) / 2)], GOLD, outline=None)
    a.shape([(hx, hy1 - 0.04), (hx + hw * 0.85, hy1 - 0.016), (hx - hw * 0.85, hy1 - 0.016)], GOLD, outline=None)
    for side in (-1, 1):
        a.line([(hx + side * (hw + 0.006), hy0 + 0.014), (hx + side * (hw + 0.006), hy1 - 0.014)], UMBER, 0.004)
        stem = [(hx + side * (0.05 + 0.035 * math.sin(u * math.pi * 0.6)), hy1 - 0.01 - 0.11 * u) for u in [i / 20 for i in range(21)]]
        a.line(stem, GOLD_D, 0.004)
        for k, u in enumerate((0.3, 0.55, 0.8)):
            px, py = stem[int(u * 20)]
            leaf(a, px, py, -math.pi / 2 + side * (1.1 - 0.25 * k), 0.026, 0.008, ULTRA)
        a.dot(*stem[-1], 0.006, GOLD_D)
        a.dot(*stem[-1], 0.0045, GOLD)

    # bottom left: a quill lying across the margin, its tip in a little ink pot
    a.blob(0.2, 0.835, 0.03, 0.012, UMBER, w=0, outline=None)
    a.d.rounded_rectangle([*a.P(0.172, 0.79), *a.P(0.228, 0.835)], radius=a.w(0.01), fill=UMBER)
    a.d.rectangle([*a.P(0.183, 0.78), *a.P(0.217, 0.792)], fill=GOLD, outline=UMBER, width=a.w(0.0025))
    a.d.rounded_rectangle([*a.P(0.18, 0.8), *a.P(0.188, 0.826)], radius=a.w(0.004), fill=mix(UMBER, PARCH, 0.35))
    a.d.rectangle([*a.P(0.172, 0.807), *a.P(0.228, 0.813)], fill=ULTRA)
    qa = -0.75                                                                # the quill leans up and to the right
    along = lambda u, off: (0.2 + math.cos(qa) * u - math.sin(qa) * off, 0.8 + math.sin(qa) * u + math.cos(qa) * off)
    vane = [along(0.05 + 0.13 * i / 20, 0.016 * math.sin(math.pi * i / 20) ** 0.7) for i in range(21)]
    vane += [along(0.05 + 0.13 * (1 - i / 20), -0.022 * math.sin(math.pi * (1 - i / 20)) ** 0.7) for i in range(21)]
    a.shape(vane, mix(PARCH, (255, 255, 255), 0.6), outline=UMBER, w=0.0012)
    for k in range(1, 9):                                                     # barbs
        u = 0.05 + 0.13 * k / 9
        a.line([along(u, 0), along(u + 0.018, -0.02 * math.sin(math.pi * k / 9) ** 0.7)], mix(UMBER, PARCH, 0.55), 0.0012)
    a.line([along(-0.005, 0), along(0.2, 0)], UMBER, 0.0028)
    return finish(a, 0.0008)


THEMES = {"sol": sol, "huerto": huerto, "vela": vela, "codice": codice}

if __name__ == "__main__":
    DEST.mkdir(parents=True, exist_ok=True)
    for name in sys.argv[1:] or THEMES:
        THEMES[name]().save(DEST / f"{name}.jpg", quality=86)
        print("wrote", DEST / f"{name}.jpg")
