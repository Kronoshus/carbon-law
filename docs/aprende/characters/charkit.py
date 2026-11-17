"""Shared drawing kit for the Aprende cast, in La Calavera's style (avatar-intake/calavera_art.py):
flat shapes, a thick plum outline, the fiesta palette, sparkly gold eyes with a smiling lower lid, rosy swirl cheeks.
Coordinates are fractions of the picture, y from the top. Phase 1 sketches; Phase 3 builds the rigged GLBs from them.
"""
import math
from PIL import Image, ImageChops, ImageDraw, ImageFilter

S, OUT = 4096, 2048
LINE, SOCKET = (46, 22, 64), (26, 16, 40)
PINK, TEAL, YELLOW, ORANGE, GOLD, GREEN, PURPLE = ((255, 79, 154), (46, 196, 182), (255, 210, 63), (255, 140, 26),
                                                  (255, 182, 39), (58, 157, 93), (123, 44, 191))
WHITE = (255, 250, 240)


class Art:
    """One picture. K, OY shrink and lower the character inside the frame, as in calavera_art.py."""

    def __init__(self, k=0.86, oy=0.14, size=S, mode="RGBA", bg=(0, 0, 0, 0)):
        self.s, self.k, self.oy = size, k, oy
        self.img = Image.new(mode, (size, size), bg)
        self.d = ImageDraw.Draw(self.img)

    def P(self, x, y):
        return ((0.5 + (x - 0.5) * self.k) * self.s, (self.oy + y * self.k) * self.s)

    def w(self, v):
        return max(1, int(v * self.s * self.k))

    def ell(self, cx, cy, rx, ry, n=90, rot=0.0, a0=0.0, a1=2 * math.pi):
        c, s = math.cos(rot), math.sin(rot)
        return [self.P(cx + rx * math.cos(t) * c - ry * math.sin(t) * s, cy + rx * math.cos(t) * s + ry * math.sin(t) * c)
                for t in (a0 + (a1 - a0) * i / n for i in range(n + (0 if a1 - a0 >= 2 * math.pi else 1)))]

    def pts(self, points):
        return [self.P(*p) for p in points]

    def shape(self, points, fill, outline=LINE, w=0.006, raw=False):
        p = points if raw else self.pts(points)
        if outline:
            self.d.line(p + [p[0]], fill=outline, width=self.w(w * 2), joint="curve")
        self.d.polygon(p, fill=fill)

    def blob(self, cx, cy, rx, ry, fill, w=0.006, rot=0.0, outline=LINE):
        self.shape(self.ell(cx, cy, rx, ry, 120, rot), fill, outline, w, raw=True)

    def dot(self, cx, cy, r, fill):
        self.d.ellipse([*self.P(cx - r, cy - r), *self.P(cx + r, cy + r)], fill=fill)

    def line(self, points, fill=LINE, w=0.006):
        self.d.line(self.pts(points), fill=fill, width=self.w(w), joint="curve")

    def arc(self, cx, cy, rx, ry, a0, a1, fill=LINE, w=0.006, n=40):
        self.d.line(self.ell(cx, cy, rx, ry, n, 0, a0, a1), fill=fill, width=self.w(w), joint="curve")

    def flower(self, cx, cy, r, layers, center):
        for n, length, width, col, off in layers:
            for i in range(n):
                a = 2 * math.pi * i / n + off
                px, py = cx + math.cos(a) * r * length * 0.55, cy + math.sin(a) * r * length * 0.55
                self.d.polygon(self.ell(px, py, r * length * 0.5, r * width, 24, a), fill=col, outline=LINE, width=self.w(0.0015))
        self.dot(cx, cy, r * 0.32, LINE)
        self.dot(cx, cy, r * 0.27, center)

    def marigold(self, cx, cy, r):
        self.flower(cx, cy, r, [(12, 1.0, 0.33, ORANGE, 0), (9, 0.65, 0.3, GOLD, 0.3)], ORANGE)

    def spiral(self, cx, cy, r, turns, col, w=0.004, flip=1):
        p = [self.P(cx + flip * math.cos(t) * r * t / (turns * 2 * math.pi), cy + math.sin(t) * r * t / (turns * 2 * math.pi))
             for t in (turns * 2 * math.pi * i / 120 for i in range(121))]
        self.d.line(p, fill=col, width=self.w(w), joint="curve")

    def blush(self, centres, ry=0.028, rx=0.045, alpha=120):
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        for cx, cy in centres:
            ImageDraw.Draw(layer).ellipse([*self.P(cx - rx, cy - ry), *self.P(cx + rx, cy + ry)], fill=(255, 105, 150, alpha))
        self.img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(self.s * 0.006)))
        self.d = ImageDraw.Draw(self.img)
        for i, (cx, cy) in enumerate(centres):
            self.spiral(cx, cy, 0.018, 1.6, PINK, flip=-1 if cx < 0.5 else 1)

    def eye(self, ex, ey, rx, ry, iris, look=0.0, blink=0.0, lid_fill=None, sclera=SOCKET, pupil=None):
        """The cast's eye: a dark (or white) socket, a glowing iris with two sparkles, and a smiling lower lid in the
        face colour (lid_fill). blink=1 closes it into a happy arc. look slides the iris sideways (lookX)."""
        if blink >= 0.95:
            self.arc(ex, ey + ry * 0.2, rx * 0.95, ry * 0.75, math.pi * 1.1, math.pi * 1.9, LINE, 0.009)
            return
        ry2 = ry * (1 - blink)
        self.blob(ex, ey, rx + 0.004, ry2 + 0.004, LINE, w=0)
        self.blob(ex, ey, rx, ry2, sclera, w=0)
        ix = ex + look * rx * 0.45
        pr = pupil or rx * 0.42
        if ry2 > pr * 0.6:
            self.dot(ix, ey, pr, iris)
            self.dot(ix, ey, pr * 0.6, (255, 120, 20) if iris == GOLD else tuple(int(c * 0.55) for c in iris))
            self.dot(ix - pr * 0.35, ey - pr * 0.38, pr * 0.29, (255, 255, 255))
            self.dot(ix + pr * 0.3, ey + pr * 0.3, pr * 0.13, (255, 255, 255))
        if lid_fill:
            lid = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(lid)
            ld.polygon(self.ell(ex, ey + ry2 * 1.25, rx * 1.3, ry2 * 0.62 + 0.007), fill=LINE)
            ld.polygon(self.ell(ex, ey + ry2 * 1.25, rx * 1.3, ry2 * 0.62), fill=lid_fill)
            inside = Image.new("L", self.img.size, 0)
            ImageDraw.Draw(inside).polygon(self.ell(ex, ey, rx + 0.0045, ry2 + 0.0045), fill=255)
            self.img.paste(lid, (0, 0), ImageChops.multiply(inside, lid.split()[3]))
            self.d = ImageDraw.Draw(self.img)

    def clip_to(self, layer_fn, mask_points):
        """Draw with layer_fn(art) into a layer, keep only what falls inside mask_points (a polygon in picture space)."""
        sub = Art(self.k, self.oy, self.s)
        layer_fn(sub)
        m = Image.new("L", self.img.size, 0)
        ImageDraw.Draw(m).polygon(mask_points, fill=255)
        self.img.paste(sub.img, (0, 0), ImageChops.multiply(m, sub.img.split()[3]))
        self.d = ImageDraw.Draw(self.img)

    def save(self, path, out=OUT):
        self.img.resize((out, out), Image.LANCZOS).save(path)
        return self.img


def confetti(art, n=70, seed=3, area=(0.05, 0.02, 0.95, 0.6)):
    import random
    rnd = random.Random(seed)
    cols = [PINK, TEAL, YELLOW, ORANGE, PURPLE, GREEN]
    for _ in range(n):
        x, y = rnd.uniform(area[0], area[2]), rnd.uniform(area[1], area[3])
        r, a = rnd.uniform(0.006, 0.012), rnd.uniform(0, math.pi)
        art.d.polygon(art.ell(x, y, r * 1.6, r * 0.6, 4, a), fill=rnd.choice(cols))
