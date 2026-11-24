"""Girasol: a cheerful sunflower, the host of the Sol theme (a sunny morning). The face is the warm seed disc, a ring of
sunny petals frames it like a mane, a green stem neck with a Sol-blue bandana, a leafy jacket and two leaf hands.
Optimistic and encouraging. Drawn in La Calavera's style (charkit); built by build.py as a theme host.
"""
import math
from charkit import Art, LINE, PINK, WHITE, S
from PIL import Image, ImageChops, ImageDraw, ImageFilter

PETAL, PETAL_D, PETAL_L = (247, 210, 26), (240, 170, 20), (255, 232, 110)   # pear yellow, its warm shade, its light
DISC, DISC_D, FACE_C = (128, 72, 34), (88, 46, 22), (198, 122, 58)          # seed disc, seeds, the caramel face
LEAF, LEAF_D, MINT = (54, 165, 88), (34, 120, 64), (112, 224, 147)
BLUE, BLUE_D, CORAL = (0, 100, 190), (0, 72, 146), (255, 94, 99)
IRIS = (0, 100, 190)

HX, HY, HR = 0.5, 0.415, 0.19                     # the seed disc

L = {"jawDrop": 0.05, "jawFade": 0.03, "band": [0.512, 0.526], "jaw": [0.44, 0.56, 0.526, 0.575],
     "eyes": [[0.43, 0.385], [0.57, 0.385]], "socket": [0.04, 0.046], "pupil": 0.023,
     "brows": [[0.43, 0.318], [0.57, 0.318]], "neck": [0.64, 0.72]}

CELEBRATE = dict(blink=1.0, cheer=True)
COMFORT = dict(caring=True)
FACE = (0.29, 0.28, 0.71, 0.70)
THEME = "sol"


def leaf(a, cx, cy, length, width, ang, fill=LEAF, vein=LEAF_D, w=0.005):
    """A pointed leaf from its base (cx, cy) along angle ang, with a centre vein."""
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(41):
        t = i / 40
        pts.append((t, width * math.sin(math.pi * t) ** 0.8 * (1 - 0.25 * t)))
    outline = [(cx + ca * length * t - sa * o, cy + sa * length * t + ca * o) for t, o in pts]
    outline += [(cx + ca * length * t + sa * o, cy + sa * length * t - ca * o) for t, o in reversed(pts[1:-1])]
    a.shape(outline, fill, w=w)
    a.line([(cx + ca * length * t, cy + sa * length * t) for t in (0.05, 0.5, 0.85)], vein, 0.005)
    for t in (0.3, 0.5, 0.7):
        for s in (-1, 1):
            x0, y0 = cx + ca * length * t, cy + sa * length * t
            a.line([(x0, y0), (x0 + ca * width * 0.4 - s * sa * width * 0.4, y0 + sa * width * 0.4 + s * ca * width * 0.4)], vein, 0.003)


def arm(a, side, pts):
    """A leaf stalk from the shoulder out to a leaf hand; pts are (distance from the middle, y)."""
    p = [(0.5 + side * x, y) for x, y in pts]
    a.line(p, LINE, 0.03)
    a.line(p, LEAF, 0.018)


def sparkle(a, x, y, r):
    """A four-point sparkle of sunshine."""
    pts = [(x + math.cos(t) * (r if i % 2 == 0 else r * 0.3), y + math.sin(t) * (r if i % 2 == 0 else r * 0.3))
           for i, t in enumerate(math.pi / 4 * k - math.pi / 2 for k in range(8))]
    a.shape(pts, PETAL_L, w=0.003)


def petals(a, n, r0, r1, width, col, off, outline=LINE):
    for i in range(n):
        t = 2 * math.pi * i / n + off
        ca, sa = math.cos(t), math.sin(t)
        stretch = 1.0 + 0.08 * max(0.0, -sa) - 0.12 * max(0.0, sa)   # longer on top like a mane, short over the neck
        pts = []
        for k in range(25):
            u = k / 24
            r = r0 + (r1 * stretch - r0) * u
            o = width * math.sin(math.pi * (0.12 + 0.88 * u)) ** 0.6
            pts.append((r, o))
        poly = [(HX + ca * r - sa * o, HY + sa * r + ca * o) for r, o in pts]
        poly += [(HX + ca * r + sa * o, HY + sa * r - ca * o) for r, o in reversed(pts[1:-1])]
        a.shape(poly, col, outline, w=0.004)
        a.line([(HX + ca * (r0 + 0.02), HY + sa * (r0 + 0.02)), (HX + ca * (r1 * stretch - 0.03), HY + sa * (r1 * stretch - 0.03))],
               PETAL_D, 0.004)


def draw(jaw=0.0, blink=0.0, look=0.0, cheer=False, caring=False):
    a = Art()
    # ---- leafy jacket over a mint shirt: the shoulders fill the bottom edge ----
    body_pts = [(0.05, 1.01), (0.09, 0.87), (0.2, 0.775), (0.38, 0.73), (0.62, 0.73), (0.8, 0.775), (0.91, 0.87), (0.95, 1.01)]
    a.shape(body_pts, LEAF)
    for side in (-1, 1):                                # each jacket front is a leaf: a midrib and side veins
        half = a.pts([(0.5, 0.73), (0.5 + side * 0.12, 0.73), (0.5 + side * 0.3, 0.765), (0.5 + side * 0.41, 0.87),
                      (0.5 + side * 0.45, 1.01), (0.5, 1.01)])
        def veins(sub, side=side):
            sub.line([(0.5 + side * 0.08, 0.76), (0.5 + side * 0.3, 1.02)], LEAF_D, 0.006)
            for k in range(5):
                x, y = 0.5 + side * (0.11 + k * 0.045), 0.80 + k * 0.053
                sub.line([(x, y), (x + side * 0.12, y - 0.035)], LEAF_D, 0.004)
                sub.line([(x, y), (x - side * 0.05, y + 0.07)], LEAF_D, 0.004)
        a.clip_to(veins, half)
    a.shape([(0.43, 0.735), (0.57, 0.735), (0.535, 1.01), (0.465, 1.01)], MINT, w=0.004)
    for y in (0.87, 0.95):                              # two little sunflower-seed buttons
        a.blob(0.5, y, 0.011, 0.014, DISC, w=0.003)
    # stem neck
    neck = [(0.455, 0.58), (0.545, 0.58), (0.55, 0.76), (0.45, 0.76)]
    a.shape(neck, LEAF)
    a.clip_to(lambda sub: sub.line([(0.522, 0.6), (0.526, 0.76)], MINT, 0.008), a.pts(neck))
    # two small leaves where the stem meets the collar
    for side in (-1, 1):
        leaf(a, 0.5 + side * 0.03, 0.745, 0.11, 0.04, math.pi / 2 - side * (math.pi / 2 - 0.25), LEAF, LEAF_D, 0.004)
    # Sol-blue bandana with white dots, knotted at the side
    band_pts = [(0.41, 0.685), (0.5, 0.70), (0.59, 0.685), (0.595, 0.73), (0.5, 0.745), (0.405, 0.73)]
    tri_pts = [(0.415, 0.72), (0.585, 0.72), (0.5, 0.835)]
    a.shape(tri_pts, BLUE)
    a.shape(band_pts, BLUE)

    def dots(sub):
        for i in range(12):
            for j in range(9):
                sub.dot(0.39 + i * 0.022 + (j % 2) * 0.011, 0.68 + j * 0.02, 0.0045, WHITE)
    a.clip_to(dots, a.pts(tri_pts))
    a.clip_to(dots, a.pts(band_pts))
    a.shape([(0.595, 0.70), (0.655, 0.68), (0.65, 0.72)], BLUE, w=0.003)     # the knot's two ends
    a.shape([(0.595, 0.715), (0.65, 0.755), (0.615, 0.765)], BLUE, w=0.003)
    a.blob(0.597, 0.71, 0.016, 0.016, BLUE_D, w=0.003)

    # ---- leaf hands. Overlays can only add, so the resting hands lie inside the jacket, where the other poses
    # paint jacket over them ----
    if cheer:                                            # both leaves thrown up high, with a few sparkles
        for side in (-1, 1):
            arm(a, side, [(0.27, 0.82), (0.33, 0.74), (0.35, 0.66)])
            leaf(a, 0.5 + side * 0.35, 0.67, 0.23, 0.08, -math.pi / 2 + side * 0.3, MINT, LEAF)
        for x, y, r in ((0.11, 0.42, 0.042), (0.88, 0.36, 0.048), (0.19, 0.2, 0.032), (0.81, 0.13, 0.035)):
            sparkle(a, x, y, r)
    elif caring:                                         # both leaves held to the heart, cradling a little coral heart
        for side in (-1, 1):
            arm(a, side, [(0.27, 0.80), (0.24, 0.86), (0.22, 0.9)])
            leaf(a, 0.5 + side * 0.22, 0.9, 0.17, 0.07, -math.pi / 2 - side * 1.0, MINT, LEAF)
        hx, hy, hs = 0.5, 0.84, 0.06
        heart = [(hx + hs * math.sin(t) ** 3, hy - hs * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t)
                  - math.cos(4 * t)) / 16) for t in (2 * math.pi * i / 80 for i in range(80))]
        a.shape(heart, CORAL, w=0.006)
        a.blob(hx - 0.025, hy - 0.025, 0.012, 0.008, (255, 170, 170), w=0, rot=-0.5)
    else:                                                # resting, folded in front like a host's hands
        for side in (-1, 1):
            arm(a, side, [(0.29, 0.79), (0.34, 0.86), (0.355, 0.95)])
            leaf(a, 0.5 + side * 0.36, 0.96, 0.2, 0.075, -math.pi / 2 - side * 0.8, MINT, LEAF)

    # ---- petals: two rings, the back one deeper gold ----
    petals(a, 14, HR * 0.8, 0.295, 0.05, PETAL_D, math.pi / 14)
    petals(a, 14, HR * 0.8, 0.27, 0.05, PETAL, 0.0)
    # ---- the seed disc, with a caramel face in the middle ----
    disc = a.ell(HX, HY, HR, HR, 180)
    a.d.line(disc + [disc[0]], fill=LINE, width=a.w(0.012), joint="curve")
    a.d.polygon(disc, fill=FACE_C)

    def seeds(sub):                                   # golden-angle seeds, bigger and denser toward the rim
        ga = math.pi * (3 - math.sqrt(5))
        for i in range(700):
            r = HR * math.sqrt(i / 700)
            if r < HR * 0.68:
                continue
            t = i * ga
            k = (r / HR - 0.68) / 0.32
            sub.dot(HX + r * math.cos(t), HY + r * math.sin(t), 0.0025 + 0.0045 * k, DISC if k < 0.45 else DISC_D)
    a.clip_to(seeds, disc)
    a.blush([(0.395, 0.468), (0.605, 0.468)], ry=0.022, rx=0.036, alpha=120)

    # ---- face ----
    for (bx, by) in L["brows"]:
        side = -1 if bx < 0.5 else 1
        if caring:                                       # inner ends lifted: a soft, caring look
            a.line([(bx - side * 0.03, by + 0.004), (bx, by - 0.006), (bx + side * 0.03, by + 0.01)], DISC_D, 0.011)
        else:
            a.arc(bx, by + 0.03, 0.032, 0.02, math.pi * 1.15, math.pi * 1.85, DISC_D, 0.011)
    rx, ry = L["socket"]
    for (ex, ey) in L["eyes"]:
        a.eye(ex, ey, rx, ry, IRIS, look, blink, lid_fill=FACE_C, sclera=WHITE, pupil=L["pupil"])
    a.blob(0.5, 0.455, 0.013, 0.009, DISC_D, w=0)                   # a little seed nose
    b0, b1 = L["band"]
    gap = (b1 - b0) + jaw * 0.045
    mouth = [(0.455, b0 - 0.004)]
    mouth += [(0.5 + 0.045 * math.cos(t), b0 - 0.004 + (gap + 0.014) * math.sin(t)) for t in (math.pi * i / 20 for i in range(21))]
    mouth = [(0.545, b0 - 0.004)] + mouth[1:]
    a.shape(mouth, (90, 30, 50), w=0.004)
    a.blob(0.5, b0 + gap * 0.75 + 0.004, 0.024, 0.006 + gap * 0.25, CORAL, w=0)    # tongue
    for side in (-1, 1):                                 # the smile curls up at the corners
        x0 = 0.5 + side * 0.043
        a.line([(x0 + side * 0.022 * t, b0 - 0.004 - 0.016 * t ** 1.6) for t in [i / 16 for i in range(17)]], LINE, 0.007)
    return a


def rig():
    """Where the moving parts are, as fractions of the 2048 picture (the K, OY of the drawing applied)."""
    X, Y = (lambda x: 0.5 + (x - 0.5) * 0.86), (lambda y: 0.14 + y * 0.86)
    return {"band": [Y(v) for v in L["band"]], "jaw": [X(L["jaw"][0]), X(L["jaw"][1]), Y(L["jaw"][2]), Y(L["jaw"][3])],
            "eyes": [[X(x), Y(y)] for x, y in L["eyes"]], "socket": [v * 0.86 for v in L["socket"]], "pupil": L["pupil"] * 0.86,
            "brows": [[X(x), Y(y)] for x, y in L["brows"]], "neck": [Y(v) for v in L["neck"]],
            "jawDrop": L.get("jawDrop", 0.07), "jawFade": L.get("jawFade", 0.035)}


if __name__ == "__main__":
    draw().save("girasol.png")
