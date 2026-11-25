"""Doña Tortuga: a wise, kind old tortoise, the host of the Códice theme (an illuminated manuscript). Calm and unhurried:
long life and patience. Round gold reading glasses, her shell over her shoulders bordered like a manuscript page in gold
and ultramarine, a small ultramarine scarf, a quill tucked in the shell. Drawn in La Calavera's style (charkit).
"""
import math
from charkit import Art, LINE, PINK, WHITE
from PIL import Image, ImageDraw, ImageFilter

SKIN, SKIN_D, SKIN_L = (138, 152, 74), (92, 104, 44), (196, 200, 130)      # olive head, its wrinkles, the pale chin
PARCH, UMBER, ULTRA, GOLD = (243, 234, 218), (110, 72, 40), (41, 66, 171), (222, 184, 102)
ULTRA_D, GOLD_D = (28, 46, 128), (176, 136, 58)
SHELL, SHELL_D = (176, 128, 70), (140, 96, 50)                               # warm amber scutes
EYE = (204, 136, 52)
THEME = "codice"

L = {"jawDrop": 0.045, "jawFade": 0.03, "band": [0.556, 0.566], "jaw": [0.44, 0.56, 0.566, 0.6],
     "eyes": [[0.418, 0.39], [0.582, 0.39]], "socket": [0.036, 0.041], "pupil": 0.021,
     "brows": [[0.412, 0.292], [0.588, 0.292]], "neck": [0.655, 0.73]}
FACE = (0.285, 0.25, 0.715, 0.68)


def quatrefoil(a, cx, cy, r, fill, centre=None):
    for k in range(4):
        t = k * math.pi / 2
        a.blob(cx + math.cos(t) * r * 0.55, cy + math.sin(t) * r * 0.55, r * 0.5, r * 0.5, fill, w=0.002)
    a.dot(cx, cy, r * 0.32, centre or fill)


def along(a, b, t):
    """The point a fraction t along a polyline."""
    seg = [math.dist(b[i], b[i + 1]) for i in range(len(b) - 1)]
    d, i = t * sum(seg), 0
    while i < len(seg) - 1 and d > seg[i]:
        d, i = d - seg[i], i + 1
    f = d / seg[i]
    return (b[i][0] + (b[i + 1][0] - b[i][0]) * f, b[i][1] + (b[i + 1][1] - b[i][1]) * f)


def smooth(p, n=3):
    """Chaikin corner cutting: round a polyline, keeping its ends."""
    for _ in range(n):
        q = [p[0]]
        for a, b in zip(p, p[1:]):
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        p = q + [p[-1]]
    return p


RIM_O = [(0.0, 1.02), (0.03, 0.88), (0.11, 0.775), (0.24, 0.705), (0.38, 0.675), (0.5, 0.67), (0.62, 0.675), (0.76, 0.705),
         (0.89, 0.775), (0.97, 0.88), (1.0, 1.02)]
RIM_O = smooth(RIM_O)
RIM_I = [(0.08, 1.02), (0.1, 0.91), (0.17, 0.825), (0.28, 0.765), (0.4, 0.74), (0.5, 0.735), (0.6, 0.74), (0.72, 0.765),
         (0.83, 0.825), (0.9, 0.91), (0.92, 1.02)]
RIM_I = smooth(RIM_I)


def shell(a):
    """The carapace over her shoulders: amber scutes, rimmed by an ultramarine border with a gold vine, like the border of
    an illuminated page."""
    op = a.pts(RIM_O)
    a.d.line(op + [op[0]], fill=LINE, width=a.w(0.012), joint="curve")
    a.d.polygon(op, fill=ULTRA)

    def inside(sub):
        sub.shape(RIM_I, SHELL, outline=GOLD, w=0.0035)
        ip = sub.pts(RIM_I)

        def scutes(s2):                                   # hexagonal scutes, each with a small gold stamp
            r = 0.068
            for col in range(-6, 7):
                for row in range(4):
                    cx, cy = 0.5 + col * 1.5 * r, 0.76 + row * 1.732 * r + (0.866 * r if col % 2 else 0)
                    s2.d.polygon(s2.ell(cx, cy, r, r, 6, 0), fill=SHELL_D)
                    s2.d.polygon(s2.ell(cx, cy, r - 0.007, r - 0.007, 6, 0), fill=SHELL)
                    s2.dot(cx, cy, 0.009, GOLD)
        sub.clip_to(scutes, ip)
        mid = [((o[0] + i[0]) / 2, (o[1] + i[1]) / 2) for o, i in zip(RIM_O, RIM_I)]
        n = 160                                             # the gold vine, winding along the rim, with leaves
        vine = []
        for k in range(n + 1):
            t = 0.03 + 0.94 * k / n
            (x, y), (x2, y2) = along(None, mid, t), along(None, mid, min(1, t + 0.002))
            nx, ny = -(y2 - y), x2 - x
            ln = math.hypot(nx, ny) or 1
            off = 0.011 * math.sin(k / n * 2 * math.pi * 11)
            vine.append((x + nx / ln * off, y + ny / ln * off))
        sub.line(vine, GOLD, 0.004)
        for k in range(22):
            x, y = along(None, mid, 0.05 + 0.9 * k / 21)
            sub.blob(x, y, 0.009, 0.009, PARCH if k % 2 else GOLD, w=0)
            sub.dot(x, y, 0.0035, ULTRA_D)
    a.clip_to(inside, op)


def neck(a):
    """A thick, soft neck coming out of the shell, with loose wrinkles."""
    pts = smooth([(0.385, 0.52), (0.615, 0.52), (0.635, 0.66), (0.66, 0.78), (0.34, 0.78), (0.365, 0.66)], 2)
    a.shape(pts, SKIN, w=0.006)

    def folds(sub):
        shadow = Image.new("RGBA", sub.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).polygon(sub.ell(0.5, 0.6, 0.17, 0.05, 80), fill=(60, 70, 20, 110))
        sub.img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(sub.s * 0.008)))
        sub.d = ImageDraw.Draw(sub.img)
        for k, w in enumerate((0.085, 0.1, 0.11)):
            sub.arc(0.5, 0.635 + k * 0.032, w, 0.018, math.pi * 0.12, math.pi * 0.88, SKIN_D, 0.005)
    a.clip_to(folds, a.pts(pts))


def plastron(a):
    p = [(0.37, 0.75), (0.63, 0.75), (0.66, 1.02), (0.34, 1.02)]
    a.shape(p, PARCH, w=0.005)

    def lines(sub):
        sub.line([(0.5, 0.75), (0.5, 1.02)], UMBER, 0.003)
        for y in (0.84, 0.93):
            sub.arc(0.5, y - 0.03, 0.2, 0.04, math.pi * 0.15, math.pi * 0.85, UMBER, 0.003)
    a.clip_to(lines, a.pts(p))


def scarf(a):
    band = [(0.37, 0.70), (0.5, 0.715), (0.63, 0.70), (0.645, 0.75), (0.5, 0.77), (0.355, 0.75)]
    a.shape(band, ULTRA, w=0.006)
    a.line([(0.365, 0.735), (0.5, 0.752), (0.635, 0.735)], GOLD, 0.003)
    for tail in ([(0.4, 0.74), (0.45, 0.75), (0.47, 0.90), (0.41, 0.89)], [(0.39, 0.745), (0.43, 0.76), (0.40, 0.87), (0.35, 0.85)]):
        a.shape(tail, ULTRA, w=0.005)
        a.line([tail[2], tail[3]], GOLD, 0.004)
    a.blob(0.415, 0.745, 0.03, 0.024, ULTRA_D, w=0.005)        # the knot
    quatrefoil(a, 0.415, 0.745, 0.016, GOLD, ULTRA)


def quill(a):
    a.line([(0.79, 0.86), (0.885, 0.575)], UMBER, 0.006)
    vane = [(0.80, 0.80), (0.83, 0.70), (0.865, 0.60), (0.895, 0.555), (0.9, 0.6), (0.885, 0.70), (0.85, 0.80)]
    a.shape(vane, WHITE, w=0.004)
    a.line([(0.81, 0.83), (0.888, 0.57)], (200, 186, 160), 0.003)
    for k in range(4):
        y = 0.64 + k * 0.04
        a.line([(0.86 - k * 0.012, y), (0.89 - k * 0.01, y - 0.015)], LINE, 0.003)


HEAD = [(0.5 + 0.21 * math.copysign(abs(math.cos(t)) ** (0.8 if math.sin(t) > 0 else 1.0), math.cos(t)),
         0.395 + (0.205 if math.sin(t) > 0 else 0.215) * math.copysign(abs(math.sin(t)) ** (0.8 if math.sin(t) > 0 else 1.0), math.sin(t)))
        for t in (2 * math.pi * i / 200 for i in range(200))]       # a dome on top, a broad soft snout below


def head(a):
    h = a.pts(HEAD)
    a.d.line(h + [h[0]], fill=LINE, width=a.w(0.012), joint="curve")
    a.d.polygon(h, fill=SKIN)

    def scales(sub):                                     # a few soft plates on the crown, a pale lower jaw
        for cx, cy, r in ((0.5, 0.215, 0.05), (0.42, 0.235, 0.04), (0.58, 0.235, 0.04), (0.35, 0.27, 0.035), (0.65, 0.27, 0.035),
                          (0.46, 0.17, 0.035), (0.54, 0.17, 0.035)):
            sub.d.polygon(sub.ell(cx, cy, r, r * 0.8, 6, 0.5), fill=SKIN_D)
            sub.d.polygon(sub.ell(cx, cy - 0.004, r * 0.8, r * 0.62, 6, 0.5), fill=(150, 164, 84))
        b0 = L["band"][0]
        jawline = [(0.5 + s * 0.104 * t, b0 + 0.006 - 0.034 * t ** 1.8) for s in (-1, 1) for t in
                   ([i / 20 for i in range(20, -1, -1)] if s < 0 else [i / 20 for i in range(21)])]
        sub.d.polygon(sub.pts(jawline + [(0.75, 0.75), (0.25, 0.75)]), fill=SKIN_L)
    a.clip_to(scales, h)


def glasses(a):
    (lx, ey), (rx_, _) = L["eyes"]
    R = 0.064
    for x in (lx, rx_):
        a.arc(x, ey, R, R, 0, 2 * math.pi, LINE, 0.016, n=80)
        a.arc(x, ey, R, R, 0, 2 * math.pi, GOLD, 0.008, n=80)
        a.arc(x, ey, R * 0.8, R * 0.8, math.pi * 1.15, math.pi * 1.4, (255, 255, 255), 0.005)   # a glint
    a.arc(0.5, ey - 0.005, 0.02, 0.015, math.pi * 1.1, math.pi * 1.9, LINE, 0.014)
    a.arc(0.5, ey - 0.005, 0.02, 0.015, math.pi * 1.1, math.pi * 1.9, GOLD, 0.007)
    for side in (-1, 1):
        x0 = 0.5 + side * (0.082 + R)
        a.line([(x0, ey - 0.01), (0.5 + side * 0.2, ey - 0.02)], LINE, 0.014)
        a.line([(x0, ey - 0.01), (0.5 + side * 0.2, ey - 0.02)], GOLD, 0.007)


def draw(jaw=0.0, blink=0.0, look=0.0, hands=False, sparkle=False, caring=False):
    a = Art()
    shell(a)
    neck(a)
    plastron(a)
    quill(a)
    head(a)
    a.flower(0.655, 0.225, 0.034, [(5, 1.0, 0.36, ULTRA, 0.3)], GOLD)      # a small flower pinned on, for Doña
    a.blush([(0.37, 0.49), (0.63, 0.49)], ry=0.024, rx=0.04, alpha=110)

    # ---- face: gentle brows, kind eyes behind round gold glasses, nostrils, a slow smile ----
    for (bx, by) in L["brows"]:
        tilt = (0.012 if bx < 0.5 else -0.012) if caring else 0.0
        a.arc(bx, by + 0.03 - abs(tilt), 0.04, 0.02, math.pi * 1.15 + tilt * 12, math.pi * 1.85 + tilt * 12, SKIN_D, 0.014)
    rx, ry = L["socket"]
    for (ex, ey) in L["eyes"]:
        a.eye(ex, ey, rx, ry, EYE, look, blink, lid_fill=SKIN, sclera=(40, 22, 30), pupil=0.021)
        if blink < 0.95:                                 # a soft, heavy upper lid: an old, calm tortoise
            a.arc(ex, ey + 0.004, rx * 1.15, ry * 1.1, math.pi * 1.12, math.pi * 1.88, SKIN_D, 0.006)
            side = -1 if ex < 0.5 else 1
            for k in range(2):                           # two lashes on the outer side
                t = math.pi * (1.5 + side * (0.26 + 0.13 * k))
                x, y = ex + math.cos(t) * rx * 1.05, ey + math.sin(t) * ry * (1 - blink) * 1.05
                a.line([(x, y), (x + math.cos(t) * 0.016, y + math.sin(t) * 0.016)], LINE, 0.005)
    glasses(a)
    for side in (-1, 1):
        a.blob(0.5 + side * 0.022, 0.488, 0.006, 0.008, LINE, w=0)
    b0, b1 = L["band"]
    gap = (b1 - b0) + jaw * 0.04
    a.d.rounded_rectangle([*a.P(0.465, b0), *a.P(0.535, b0 + gap)], radius=a.w(0.005), fill=(70, 30, 50),
                          outline=LINE, width=a.w(0.004))
    if gap > 0.02:
        a.blob(0.5, b0 + gap * 0.72, 0.022, gap * 0.26, (230, 110, 130), w=0)
    for side in (-1, 1):                                 # a wide, slow smile, curling up at the corners
        x0 = 0.5 + side * 0.034
        a.line([(x0 + side * 0.07 * t, b0 + 0.006 - 0.034 * ((0.034 + 0.07 * t) / 0.104) ** 1.8 + 0.0) for t in [i / 20 for i in range(21)]], LINE, 0.007)

    scarf(a)
    if hands:                                             # her front feet crossed over her heart, a gentle hug (the "comfort" state)
        claws = []
        for s in (1, -1):                                 # the right foot first, the left one laid over it
            tx, ty = 0.5 - s * 0.07, 0.8 + (0.0 if s < 0 else 0.02)    # the toes, reaching up to the other shoulder
            foot = smooth([(0.5 + s * 0.24, 1.02), (0.5 + s * 0.16, 0.9), (tx + s * 0.03, ty - 0.045), (tx - s * 0.035, ty - 0.035),
                           (tx - s * 0.05, ty + 0.015), (tx + s * 0.01, ty + 0.06), (0.5 + s * 0.1, 1.02)], 2)
            a.shape(foot, SKIN, w=0.006)
            a.clip_to(lambda sub: [sub.d.polygon(sub.ell(0.5 + s * (0.06 + 0.05 * k), ty + 0.07 + 0.04 * k, 0.024, 0.017, 6, 0),
                                                 fill=SKIN_D) for k in range(3)], a.pts(foot))
            claws.append((s, tx, ty))
        for s, tx, ty in claws:                           # three pale claws at the toes
            for k in range(3):
                t = math.pi * (1.0 if s > 0 else 0.0) + s * (0.7 - 0.55 * k)
                a.blob(tx - s * 0.005 + math.cos(t) * 0.04, ty - 0.01 + math.sin(t) * 0.035, 0.01, 0.008, PARCH, w=0.0025, rot=t)
    if sparkle:                                           # a few gold glints for a job well done
        for x, y, r in ((0.2, 0.25, 0.03), (0.8, 0.22, 0.026), (0.15, 0.5, 0.02), (0.86, 0.46, 0.022), (0.27, 0.1, 0.018)):
            a.shape([(x, y - r), (x + r * 0.28, y - r * 0.28), (x + r, y), (x + r * 0.28, y + r * 0.28), (x, y + r),
                     (x - r * 0.28, y + r * 0.28), (x - r, y), (x - r * 0.28, y - r * 0.28)], GOLD, w=0.003)
    return a


CELEBRATE = dict(blink=1.0, sparkle=True)
COMFORT = dict(blink=1.0, hands=True, caring=True)


def rig():
    """Where the moving parts are, as fractions of the 2048 picture (the K, OY of the drawing applied)."""
    X, Y = (lambda x: 0.5 + (x - 0.5) * 0.86), (lambda y: 0.14 + y * 0.86)
    return {"band": [Y(v) for v in L["band"]], "jaw": [X(L["jaw"][0]), X(L["jaw"][1]), Y(L["jaw"][2]), Y(L["jaw"][3])],
            "eyes": [[X(x), Y(y)] for x, y in L["eyes"]], "socket": [v * 0.86 for v in L["socket"]], "pupil": L["pupil"] * 0.86,
            "brows": [[X(x), Y(y)] for x, y in L["brows"]], "neck": [Y(v) for v in L["neck"]],
            "jawDrop": L.get("jawDrop", 0.07), "jawFade": L.get("jawFade", 0.035)}


if __name__ == "__main__":
    draw().save("tortuga.png")
