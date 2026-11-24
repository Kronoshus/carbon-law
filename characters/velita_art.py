"""Velita: a gentle candle, the host of the Vela theme (a calm candle at night). A cream wax body whose upper part is
her face, a warm ochre flame on top like a tuft of hair, soft wax drips, a pink ribbon, and a small brass holder that
forms the shoulders. Peaceful and patient: the light that keeps you company. In La Calavera's style (charkit.py).
"""
import math
from charkit import Art, LINE, PINK, GOLD, S
from PIL import Image, ImageDraw, ImageFilter

WAX, WAX_D, WAX_L = (247, 237, 214), (228, 208, 172), (255, 251, 238)     # parchment wax, its shadow, its highlight
FLAME, FLAME_M, FLAME_C = (232, 150, 44), (250, 196, 72), (255, 240, 196)  # ochre flame, its middle, its bright core
BRASS, BRASS_D, BRASS_L = (204, 152, 62), (156, 106, 40), (240, 204, 120)
RIBBON, RIBBON_D, HEART = (214, 128, 124), (180, 96, 96), (234, 102, 118)   # the theme's touch of pink
IRIS, BROW = (204, 132, 44), (150, 100, 62)
THEME = "vela"

L = {"jawDrop": 0.05, "jawFade": 0.03, "band": [0.552, 0.566], "jaw": [0.44, 0.56, 0.566, 0.6], "eyes": [[0.415, 0.385], [0.585, 0.385]],
     "socket": [0.041, 0.046], "pupil": 0.024, "brows": [[0.415, 0.312], [0.585, 0.312]], "neck": [0.64, 0.74]}

X0, X1, TOP, CUP = 0.3, 0.7, 0.235, 0.735          # the candle's sides and the line of its melted top rim


def glow(a, cx, cy, rx, ry, col, blur):
    layer = Image.new("RGBA", a.img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([*a.P(cx - rx, cy - ry), *a.P(cx + rx, cy + ry)], fill=col)
    a.img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(S * blur)))
    a.d = ImageDraw.Draw(a.img)


def teardrop(cx, base, h, w, lean=0.0, n=60):
    """A flame: round at the bottom, a soft point at the top that leans (and curls) sideways."""
    pts = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        s = (1 - math.cos(t)) / 2                      # 0 at the tip, 1 at the base
        y = base - h * (1 - s ** 0.9)
        x = cx + w * math.sin(t) * (0.25 + 0.75 * s) + lean * (1 - s) ** 2
        pts.append((x, y))
    return pts


def draw(jaw=0.0, blink=0.0, look=0.0, bright=False, care=False):
    a = Art()
    # ---- the brass holder: a wide dish that fills the bottom edge, a stem, and a broad cup that makes her shoulders ----
    glow(a, 0.5, 0.95, 0.42, 0.06, (40, 24, 10, 90), 0.01)
    dish = a.ell(0.5, 0.95, 0.45, 0.085, 140)
    a.d.line(dish + [dish[0]], fill=LINE, width=a.w(0.012), joint="curve")
    a.d.polygon(dish, fill=BRASS_D)
    a.blob(0.5, 0.925, 0.4, 0.06, BRASS, w=0.004)
    a.arc(0.5, 0.925, 0.34, 0.04, math.pi * 1.12, math.pi * 1.42, BRASS_L, 0.008)
    ring = (0.85, 0.86)                                    # a ring handle on her left, like a chamberstick
    a.blob(*ring, 0.06, 0.05, BRASS, w=0.006)
    a.blob(*ring, 0.032, 0.026, (0, 0, 0, 0), w=0.004)
    a.shape([(0.40, 0.93), (0.60, 0.93), (0.56, 0.80), (0.44, 0.80)], BRASS_D, w=0.005)              # stem
    a.blob(0.5, 0.80, 0.08, 0.02, BRASS, w=0.004)
    a.blob(0.5, CUP, 0.33, 0.045, BRASS_D, w=0.006)                                                 # inside of the cup
    # ---- the candle: cream wax with soft, rounded shoulders, a shadowed side and a highlight ----
    R = 0.06
    body = ([(X0, CUP + 0.06)] + [(X0 + R - R * math.cos(t), TOP + R - R * math.sin(t)) for t in [i / 12 * math.pi / 2 for i in range(13)]]
            + [(X1 - R + R * math.sin(t), TOP + R - R * math.cos(t)) for t in [i / 12 * math.pi / 2 for i in range(13)]] + [(X1, CUP + 0.06)])
    bp = a.pts(body)
    a.d.line(bp + [bp[0]], fill=LINE, width=a.w(0.012), joint="curve")
    a.d.polygon(bp, fill=WAX)

    def shading(sub):
        sub.d.polygon(sub.pts([(0.645, 0.2), (0.75, 0.2), (0.75, 0.8), (0.645, 0.8)]), fill=WAX_D)
        sub.d.polygon(sub.pts([(0.325, 0.3), (0.345, 0.3), (0.345, 0.62), (0.325, 0.62)]), fill=WAX_L)
        # melted wax over the top: a soft cap whose drips run down at her shoulders
        drips = ((0.665, 0.085, 0.022), (0.6, 0.035, 0.016), (0.345, 0.065, 0.02), (0.405, 0.025, 0.014))
        edge = []
        for i in range(201):
            x = 0.75 - 0.5 * i / 200
            y = 0.262 + 0.004 * math.sin(x * 70) + sum(ln * max(0.0, 1 - ((x - c) / r) ** 2) ** 0.4 for c, ln, r in drips)
            edge.append((x, y))
        cap = [(0.25, 0.2), (0.75, 0.2)] + edge
        sub.shape(cap, WAX_L, outline=LINE, w=0.0035)
    a.clip_to(shading, bp)
    a.d.line(bp + [bp[0]], fill=LINE, width=a.w(0.012), joint="curve")
    a.blob(0.5, TOP + 0.022, 0.13, 0.018, WAX, w=0.003, outline=WAX_D)                       # the little pool of melted wax on top
    lip = (a.ell(0.5, CUP, 0.33, 0.045, 60, 0, 0, math.pi) + a.ell(0.5, CUP + 0.05, 0.31, 0.05, 60, 0, math.pi, 0))
    a.shape(lip, BRASS, raw=True)                                               # the cup's front lip, over the candle
    a.arc(0.5, CUP + 0.022, 0.29, 0.04, math.pi * 0.62, math.pi * 0.88, BRASS_L, 0.009)

    # ---- the flame, with its glow, standing on a short wick: her tuft of hair ----
    h, w, lean = (0.24, 0.085, 0.04) if bright else (0.185, 0.072, 0.04)    # overlays only add, so the bright flame covers the base one
    glow(a, 0.5, TOP - h * 0.45, 0.2 if bright else 0.15, 0.2 if bright else 0.16, (255, 190, 90, 120 if bright else 80), 0.03)
    a.line([(0.5, TOP + 0.01), (0.5, TOP - 0.04)], LINE, 0.012)
    base = TOP - 0.022
    a.shape(teardrop(0.5, base, h, w, lean), FLAME, w=0.006)
    a.shape(teardrop(0.5, base - 0.006, h * 0.72, w * 0.7, lean * 0.7), FLAME_M, outline=None)
    a.shape(teardrop(0.5, base - 0.012, h * 0.42, w * 0.4, lean * 0.4), FLAME_C, outline=None)
    if bright:                                              # a few happy sparkles around the flame
        for sx, sy, r in ((0.33, 0.02, 0.022), (0.68, -0.03, 0.026), (0.73, 0.12, 0.016), (0.27, 0.14, 0.015)):
            a.shape([(sx, sy - r), (sx + r * 0.3, sy - r * 0.3), (sx + r, sy), (sx + r * 0.3, sy + r * 0.3), (sx, sy + r),
                     (sx - r * 0.3, sy + r * 0.3), (sx - r, sy), (sx - r * 0.3, sy - r * 0.3)], FLAME_M, w=0.003)

    # ---- a pink ribbon tied round her, a nod to La Calavera's bow tie ----
    band = a.pts([(X0, 0.635), (X1, 0.635), (X1, 0.668), (X0, 0.668)])
    a.d.line(band + [band[0]], fill=LINE, width=a.w(0.008))
    a.d.polygon(band, fill=RIBBON)
    for side in (-1, 1):
        a.shape([(0.5 + side * 0.01, 0.66), (0.5 + side * 0.045, 0.725), (0.5 + side * 0.022, 0.72)], RIBBON_D, w=0.003)
        a.shape([(0.5, 0.652), (0.5 + side * 0.075, 0.62), (0.5 + side * 0.07, 0.687)], RIBBON, w=0.004)
    a.blob(0.5, 0.652, 0.018, 0.02, RIBBON, w=0.004)

    # ---- face: soft brows, kind eyes with the smiling lower lid, rosy cheeks, a gentle smile ----
    a.blush([(0.36, 0.48), (0.64, 0.48)], ry=0.026, rx=0.04, alpha=105)
    for (bx, by) in L["brows"]:
        side = -1 if bx < 0.5 else 1
        if care:                                            # caring: the inner ends lift a little
            a.line([(bx - side * 0.03, by - 0.006), (bx, by - 0.004), (bx + side * 0.03, by + 0.008)], BROW, 0.011)
        else:
            a.arc(bx, by + 0.035, 0.034, 0.02, math.pi * 1.15, math.pi * 1.85, BROW, 0.011)
    rx, ry = L["socket"]
    for (ex, ey) in L["eyes"]:
        a.eye(ex, ey, rx, ry, IRIS, look, blink, lid_fill=WAX, sclera=(46, 26, 30), pupil=0.024)
        if blink < 0.95:                                    # two soft lashes on the outer side
            side = -1 if ex < 0.5 else 1
            for k in range(2):
                t = math.pi * (1.5 + side * (0.26 + 0.14 * k))
                x, y = ex + math.cos(t) * rx, ey + math.sin(t) * ry * (1 - blink)
                a.line([(x, y), (x + math.cos(t) * 0.018, y + math.sin(t) * 0.018)], LINE, 0.006)
    if care:                                                # caring: two little wax hands hold a glowing pink heart
        glow(a, 0.5, 0.67, 0.1, 0.08, (255, 200, 120, 130), 0.014)
        heart = [(0.5 + 0.06 * math.sin(t) ** 3, 0.668 - 0.05 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t)
                 - math.cos(4 * t)) / 16) for t in [i / 60 * 2 * math.pi for i in range(60)]]
        a.shape(heart, HEART, w=0.005)
        a.blob(0.476, 0.646, 0.013, 0.008, (255, 196, 190), w=0, rot=-0.6)
        for side in (-1, 1):
            a.blob(0.5 + side * 0.055, 0.7, 0.032, 0.026, WAX_L, w=0.005, rot=side * 0.6)
    b0, b1 = L["band"]
    gap = (b1 - b0) + jaw * 0.045
    a.d.rounded_rectangle([*a.P(0.462, b0), *a.P(0.538, b0 + gap)], radius=a.w(0.007), fill=(96, 40, 56),
                          outline=LINE, width=a.w(0.004))
    if gap > 0.02:
        a.blob(0.5, b0 + gap * 0.72, 0.022, gap * 0.26, (232, 120, 130), w=0)
    for side in (-1, 1):
        x0 = 0.5 + side * 0.033
        a.line([(x0 + side * 0.034 * t, b0 + 0.004 - 0.022 * t ** 1.6) for t in [i / 16 for i in range(17)]], LINE, 0.007)
    return a


CELEBRATE = dict(blink=1.0, bright=True)
COMFORT = dict(blink=1.0, care=True)
FACE = (0.255, 0.185, 0.745, 0.675)


def rig():
    """Where the moving parts are, as fractions of the 2048 picture (the K, OY of the drawing applied)."""
    X, Y = (lambda x: 0.5 + (x - 0.5) * 0.86), (lambda y: 0.14 + y * 0.86)
    return {"band": [Y(v) for v in L["band"]], "jaw": [X(L["jaw"][0]), X(L["jaw"][1]), Y(L["jaw"][2]), Y(L["jaw"][3])],
            "eyes": [[X(x), Y(y)] for x, y in L["eyes"]], "socket": [v * 0.86 for v in L["socket"]], "pupil": L["pupil"] * 0.86,
            "brows": [[X(x), Y(y)] for x, y in L["brows"]], "neck": [Y(v) for v in L["neck"]],
            "jawDrop": L.get("jawDrop", 0.07), "jawFade": L.get("jawFade", 0.035)}
