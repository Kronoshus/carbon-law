"""Colibrí: a friendly hummingbird who hosts the Huerto theme (a green orchard in daylight). Quick, cheerful and caring;
in Mexican tradition the hummingbird brings joy and good news. Drawn in La Calavera's style (charkit): flat shapes, the
plum outline, sparkly eyes with a smiling lower lid, rosy cheeks. The short beak is the mouth: its lower half drops to talk.
"""
import math
from charkit import Art, LINE

THEME = "huerto"
GREEN_D, GREEN, GREEN_L, LIME = (7, 89, 48), (25, 135, 77), (60, 160, 90), (170, 206, 84)      # forest green to a sunlit sheen
TEAL = (40, 170, 160)                                                                       # the blue-green shimmer
PEACH, PEACH_D, CREAM = (255, 179, 124), (236, 140, 92), (255, 244, 228)                    # throat, its scallops, warm white
SUN = (255, 208, 96)
BEAK, BEAK_L, MOUTH, TONGUE = (78, 50, 84), (128, 96, 134), (96, 30, 54), (236, 112, 132)
EYE = (186, 118, 44)                                                                        # warm honey iris
PETAL, PETAL_D = (255, 200, 176), (246, 146, 132)

L = {"jawDrop": 0.032, "jawFade": 0.022, "band": [0.535, 0.543], "jaw": [0.47, 0.53, 0.543, 0.571],
     "eyes": [[0.41, 0.385], [0.59, 0.385]], "socket": [0.046, 0.052], "pupil": 0.025,
     "brows": [[0.405, 0.312], [0.595, 0.312]], "neck": [0.655, 0.73]}
CELEBRATE = dict(blink=1.0, wings="up")
COMFORT = dict(wings="hold", kind=True)
FACE = (0.29, 0.245, 0.71, 0.665)


def ring(cx, cy, rx, ry, rot=0.0, n=60, a0=0.0, a1=2 * math.pi):
    c, s = math.cos(rot), math.sin(rot)
    return [(cx + rx * math.cos(t) * c - ry * math.sin(t) * s, cy + rx * math.cos(t) * s + ry * math.sin(t) * c)
            for t in (a0 + (a1 - a0) * i / n for i in range(n))]


def rotate(points, pivot, ang):
    px, py = pivot
    c, s = math.cos(ang), math.sin(ang)
    return [(px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c) for x, y in points]


def scallops(sub, x0, x1, y0, rows, col, step=0.04, dy=0.03, w=0.0035, skip=None):
    """Rows of small feather arcs (the cast's fur tufts, as feathers)."""
    for r in range(rows):
        for i in range(int((x1 - x0) / step) + 1):
            x, y = x0 + i * step + (step / 2 if r % 2 else 0), y0 + r * dy
            if not (skip and skip(x, y)):
                sub.arc(x, y, step * 0.4, step * 0.27, 0.15 * math.pi, 0.85 * math.pi, col(i, r) if callable(col) else col, w)


def blossom(a, cx, cy, r, leaves=(-0.4, 0.9)):
    """A peach blossom (flor de durazno): five round petals, a sunny centre, two leaves."""
    for ang in leaves:
        p = [(cx + math.cos(ang) * r * d - math.sin(ang) * r * o, cy + math.sin(ang) * r * d + math.cos(ang) * r * o)
             for d, o in ((0.6, 0), (1.3, -0.45), (2.2, 0), (1.3, 0.45))]
        a.shape(p, GREEN_L, w=0.0025)
    for i in range(5):
        t = 2 * math.pi * i / 5 - math.pi / 2
        a.blob(cx + math.cos(t) * r * 0.6, cy + math.sin(t) * r * 0.6, r * 0.55, r * 0.5, PETAL, w=0.0025, rot=t)
        a.blob(cx + math.cos(t) * r * 0.42, cy + math.sin(t) * r * 0.42, r * 0.2, r * 0.15, PETAL_D, w=0, rot=t)
    a.dot(cx, cy, r * 0.3, LINE)
    a.dot(cx, cy, r * 0.24, SUN)


def wing(a, side, ang=0.0):
    """A small folded wing that hangs from the shoulder like an arm: round coverts on top, long primaries below.
    ang lifts it about the shoulder, outward (celebrate) or, when negative, inward across the breast (comfort)."""
    pv = (0.5 + side * 0.225, 0.71)
    R = lambda pts: rotate(pts, pv, -side * ang)
    x = lambda dx: pv[0] + side * dx
    spine = lambda t: (x(0.005 + 0.045 * t ** 1.5), 0.655 + 0.4 * t)                  # the wing's centre line, top to tip
    half = lambda t: 0.088 * math.sin(math.pi * t) ** 0.5 * (1 - 0.45 * t)
    ts = [i / 40 for i in range(41)]
    outline = R([(spine(t)[0] - half(t), spine(t)[1]) for t in ts] + [(spine(t)[0] + half(t), spine(t)[1]) for t in ts[::-1]])
    a.shape(outline, GREEN_D, w=0.006)
    poly = a.pts(outline)

    def detail(sub):
        cov = R(ring(x(0.005), 0.72, 0.1, 0.07, 0, 60))
        sub.d.polygon(sub.pts(cov), fill=GREEN)
        sub.d.line(sub.pts(cov[30:] + cov[:1]), fill=LINE, width=sub.w(0.006), joint="curve")
        for k, dx in enumerate((-0.03, 0.005, 0.04)):                    # primaries: long feather edges
            sub.line(R([(x(dx), 0.78), (x(dx + 0.02), 0.9), (x(dx + 0.035), 1.06)]), LINE, 0.005)
            sub.line(R([(x(dx + 0.012), 0.79), (x(dx + 0.032), 0.9), (x(dx + 0.047), 1.05)]), TEAL, 0.004)
        for r in range(2):
            for i in range(4):
                cx, cy = R([(x(-0.05 + i * 0.034 + (0.017 if r else 0)), 0.69 + r * 0.03)])[0]
                sub.arc(cx, cy, 0.014, 0.01, 0.15 * math.pi - side * ang, 0.85 * math.pi - side * ang, LIME if r == 0 else GREEN_L, 0.004)
    a.clip_to(detail, poly)


def draw(jaw=0.0, blink=0.0, look=0.0, wings="down", kind=False):
    a = Art()
    # ---- body: green shoulders, a peach throat that runs down into a warm-white breast ----
    body_pts = [(0.06, 1.01), (0.1, 0.87), (0.18, 0.75), (0.3, 0.655), (0.5, 0.6), (0.7, 0.655), (0.82, 0.75), (0.9, 0.87),
                (0.94, 1.01)]
    a.shape(body_pts, GREEN)

    def breast(sub):
        sub.d.polygon(sub.pts(ring(0.5, 0.93, 0.25, 0.3, 0, 90)), fill=CREAM)
        scallops(sub, 0.33, 0.67, 0.8, 5, (240, 220, 196), dy=0.045)
        sub.d.polygon(sub.pts(ring(0.5, 0.66, 0.2, 0.135, 0, 90)), fill=PEACH)
        scallops(sub, 0.34, 0.66, 0.66, 3, PEACH_D, dy=0.035)
        for k in range(2):                                    # shoulder sheen
            scallops(sub, 0.08 + k * 0.62, 0.3 + k * 0.62, 0.79 - 0.0 * k, 3, GREEN_L, step=0.035, dy=0.04,
                     skip=lambda x, y: abs(x - 0.5) < 0.26)
    a.clip_to(breast, a.pts(body_pts))

    # ---- head: a round green crown with a sprout of a crest ----
    for k, rot in enumerate((-0.5, 0.0, 0.5)):
        f = rotate(ring(0.5, 0.165, 0.018, 0.05), (0.5, 0.215), rot)
        a.shape(f, (GREEN, GREEN_L, GREEN)[k], w=0.005)
        a.dot(*rotate([(0.5, 0.13)], (0.5, 0.215), rot)[0], 0.008, LIME)
    head = a.ell(0.5, 0.405, 0.212, 0.2, 180)
    a.d.line(head + [head[0]], fill=LINE, width=a.w(0.012), joint="curve")
    a.d.polygon(head, fill=GREEN)

    def face(sub):
        scallops(sub, 0.32, 0.7, 0.235, 3, lambda i, r: TEAL if (i + r) % 3 == 0 else LIME, dy=0.032)
        throat = sub.pts(ring(0.5, 0.65, 0.2, 0.085, 0, 90))
        sub.d.polygon(throat, fill=PEACH)
        cheeks = [sub.pts(ring(0.5 + s * 0.072, 0.53, 0.098, 0.072, 0, 90)) for s in (-1, 1)]   # warm-white cheeks
        for p in cheeks:
            sub.d.line(p + [p[0]], fill=LINE, width=sub.w(0.008), joint="curve")
        for p in cheeks:
            sub.d.polygon(p, fill=CREAM)
        sub.d.polygon(sub.ell(0.5, 0.57, 0.09, 0.05), fill=CREAM)                       # the chin, under the beak
    a.clip_to(face, head)
    a.blush([(0.39, 0.525), (0.61, 0.525)], ry=0.022, rx=0.034, alpha=120)

    # ---- eyes, the hummingbird's white spot behind each eye, brows ----
    for (bx, by) in L["brows"]:
        tilt = (1 if bx < 0.5 else -1) * (0.28 if kind else 0.0)
        a.d.line(a.ell(bx, by + 0.035, 0.036, 0.022, 40, tilt, math.pi * 1.15, math.pi * 1.85), fill=GREEN_D,
                 width=a.w(0.012), joint="curve")
    for (ex, ey) in L["eyes"]:
        side = -1 if ex < 0.5 else 1
        a.blob(ex + side * 0.07, ey - 0.014, 0.011, 0.007, CREAM, w=0, rot=side * -0.4)
    rx, ry = L["socket"]
    for (ex, ey) in L["eyes"]:
        a.eye(ex, ey, rx, ry, EYE, look, blink, lid_fill=GREEN, sclera=(36, 22, 34), pupil=0.026)

    # ---- the beak: the upper half stays, the lower half drops to talk (the jaw band) ----
    b0, b1 = L["band"]
    gap = (b1 - b0) + jaw * 0.04
    for side in (-1, 1):                                       # the smile curls up from the beak's corners
        a.line([(0.5 + side * (0.02 + 0.05 * t), 0.522 + 0.006 * math.sin(math.pi * t) - 0.026 * t ** 2) for t in
                [i / 16 for i in range(17)]], LINE, 0.007)
    a.shape([(0.484, b0 - 0.006), (0.516, b0 - 0.006), (0.514, b0 + gap), (0.486, b0 + gap)], MOUTH, w=0.003)
    if jaw > 0.2:
        a.blob(0.5, b0 + gap * 0.72, 0.009, gap * 0.22, TONGUE, w=0)
    lo = b0 + gap
    a.shape([(0.485, lo), (0.515, lo), (0.508, lo + 0.018), (0.5, lo + 0.032), (0.492, lo + 0.018)], BEAK_L, w=0.005)
    upper = [(0.5, 0.466), (0.514, 0.476), (0.523, 0.497), (0.52, 0.52), (0.516, b0), (0.5, b0 + 0.003), (0.484, b0),
             (0.48, 0.52), (0.477, 0.497), (0.486, 0.476)]
    a.shape(upper, BEAK, w=0.005)
    a.line([(0.494, 0.482), (0.492, 0.522)], BEAK_L, 0.005)                                  # a little shine

    # ---- wings, and the blossom ----
    if wings == "down":
        for side in (-1, 1):
            wing(a, side)
        blossom(a, 0.31, 0.725, 0.036)
    elif wings == "up":                                        # celebrate: wings lifted high, a happy buzz
        for side in (-1, 1):
            wing(a, side, 2.15)
            for k in range(3):
                a.arc(0.5 + side * 0.3, 0.42, 0.05 + k * 0.03, 0.09 + k * 0.04, math.pi * (1 if side < 0 else 0) - 0.5,
                      math.pi * (1 if side < 0 else 0) + 0.5, SUN, 0.006)
        for x, y, r in ((0.17, 0.2, 0.013), (0.83, 0.17, 0.011), (0.12, 0.38, 0.011), (0.88, 0.36, 0.013)):
            a.blob(x, y, r, r * 0.65, PETAL, w=0.002, rot=x * 6)
        blossom(a, 0.31, 0.725, 0.036)
    else:                                                      # comfort: wings drawn in, holding the blossom to the heart
        for side in (-1, 1):
            wing(a, side, -0.62)
        blossom(a, 0.5, 0.84, 0.055, leaves=(-0.6, 3.7))
    return a


def rig():
    """Where the moving parts are, as fractions of the 2048 picture (the K, OY of the drawing applied)."""
    X, Y = (lambda x: 0.5 + (x - 0.5) * 0.86), (lambda y: 0.14 + y * 0.86)
    return {"band": [Y(v) for v in L["band"]], "jaw": [X(L["jaw"][0]), X(L["jaw"][1]), Y(L["jaw"][2]), Y(L["jaw"][3])],
            "eyes": [[X(x), Y(y)] for x, y in L["eyes"]], "socket": [v * 0.86 for v in L["socket"]], "pupil": L["pupil"] * 0.86,
            "brows": [[X(x), Y(y)] for x, y in L["brows"]], "neck": [Y(v) for v in L["neck"]],
            "jawDrop": L.get("jawDrop", 0.07), "jawFade": L.get("jawFade", 0.035)}


if __name__ == "__main__":
    draw().save("colibri.png")
