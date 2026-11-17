"""Draws the 2D Day of the Dead calavera (sugar skull in a suit) and its backdrop as flat artwork.
Run:  %USERPROFILE%\\avatar-tools\\venv\\Scripts\\python.exe calavera_art.py
Writes calavera.png (character, transparent), calavera-bg.png (papel picado backdrop) and calavera.json
(where the moving parts are, for make_calavera.py). Coordinates are fractions of the image, y measured from the top.
"""
import json, math
from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 4096                       # drawn at 2x, saved at 2048 (smooth edges)
OUT = 2048
BONE, TEETH, LINE, SOCKET = (243, 234, 216), (255, 250, 240), (46, 22, 64), (26, 16, 40)
PINK, TEAL, YELLOW, ORANGE, GOLD, GREEN, PURPLE = ((255, 79, 154), (46, 196, 182), (255, 210, 63), (255, 140, 26),
                                                  (255, 182, 39), (58, 157, 93), (123, 44, 191))
SUIT, LAPEL, SHIRT = (29, 27, 38), (18, 16, 26), (250, 248, 244)

# the moving parts (shared with make_calavera.py)
L = {
    "band": [0.565, 0.580],                 # dark gap between the teeth: stretches into the open mouth
    "jaw": [0.36, 0.64, 0.580, 0.672],      # x0, x1, y0, y1 of the lower jaw
    "eyes": [[0.405, 0.385], [0.595, 0.385]], "socket": [0.072, 0.07],
    "pupil": 0.026, "brows": [[0.405, 0.30], [0.595, 0.30]],
    "neck": [0.70, 0.765],                  # head moves fully above neck[0], not at all below neck[1]
}

K, OY = 0.86, 0.14             # the character is drawn smaller and lower, leaving room above for the sombrero
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
P = lambda x, y: ((0.5 + (x - 0.5) * K) * S, (OY + y * K) * S)


def ell(cx, cy, rx, ry, n=90, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    return [P(cx + rx * math.cos(t) * c - ry * math.sin(t) * s, cy + rx * math.cos(t) * s + ry * math.sin(t) * c)
            for t in (2 * math.pi * i / n for i in range(n))]


def shape(points, fill, outline=LINE, w=0.006):
    pts = [P(*p) if max(p) <= 1.5 else p for p in points]
    if outline:
        d.line(pts + [pts[0]], fill=outline, width=int(w * S * 2), joint="curve")
    d.polygon(pts, fill=fill)


def dot(cx, cy, r, fill):
    d.ellipse([*P(cx - r, cy - r), *P(cx + r, cy + r)], fill=fill)


def flower(cx, cy, r, layers, center):
    for k, (n, length, width, col, off) in enumerate(layers):
        for i in range(n):
            a = 2 * math.pi * i / n + off
            px, py = cx + math.cos(a) * r * length * 0.55, cy + math.sin(a) * r * length * 0.55
            d.polygon(ell(px, py, r * length * 0.5, r * width, 24, a), fill=col, outline=LINE, width=int(S * 0.0015))
    dot(cx, cy, r * 0.32, LINE)
    dot(cx, cy, r * 0.27, center)


def spiral(cx, cy, r, turns, col, w=0.005, flip=1):
    pts = [P(cx + flip * math.cos(t) * r * t / (turns * 2 * math.pi), cy + math.sin(t) * r * t / (turns * 2 * math.pi))
           for t in (turns * 2 * math.pi * i / 120 for i in range(121))]
    d.line(pts, fill=col, width=int(w * S), joint="curve")


# ---------- suit, shirt, bow tie ----------
shape([(0.06, 1.01), (0.10, 0.87), (0.20, 0.805), (0.40, 0.765), (0.60, 0.765), (0.80, 0.805), (0.90, 0.87), (0.94, 1.01)], SUIT)
shape([(0.415, 0.765), (0.585, 0.765), (0.5, 0.94)], SHIRT, w=0.003)
shape([(0.40, 0.765), (0.445, 0.78), (0.5, 0.94), (0.44, 1.01), (0.35, 0.87)], LAPEL, w=0.003)
shape([(0.60, 0.765), (0.555, 0.78), (0.5, 0.94), (0.56, 1.01), (0.65, 0.87)], LAPEL, w=0.003)
shape([(0.5, 0.80), (0.445, 0.775), (0.445, 0.825)], PURPLE, w=0.003)
shape([(0.5, 0.80), (0.555, 0.775), (0.555, 0.825)], PURPLE, w=0.003)
dot(0.5, 0.80, 0.013, LINE), dot(0.5, 0.80, 0.010, PURPLE)
flower(0.665, 0.875, 0.035, [(12, 1.0, 0.33, ORANGE, 0), (9, 0.65, 0.3, GOLD, 0.3)], ORANGE)    # boutonniere

# ---------- neck ----------
for y in (0.675, 0.705, 0.735):
    shape(ell(0.5, y + 0.013, 0.032, 0.014, 40), BONE, w=0.004)

# ---------- skull ----------
cranium = ell(0.5, 0.33, 0.245, 0.235, 160)
face = [(0.288, 0.40), (0.712, 0.40), (0.705, 0.47), (0.672, 0.525), (0.64, 0.565), (0.36, 0.565), (0.328, 0.525), (0.295, 0.47)]
jaw = [(0.36, 0.580), (0.64, 0.580), (0.635, 0.62), (0.605, 0.655), (0.555, 0.672), (0.445, 0.672), (0.395, 0.655), (0.365, 0.62)]
for pts in (cranium, face, jaw):               # outlines first, then the fills, so the parts join without inner lines
    pts = [P(*p) if max(p) <= 1.5 else p for p in pts]
    d.line(pts + [pts[0]], fill=LINE, width=int(0.012 * S), joint="curve")
for pts in (cranium, face, jaw):
    d.polygon([P(*p) if max(p) <= 1.5 else p for p in pts], fill=BONE)
b0, b1 = L["band"]
d.rectangle([*P(0.355, b0), *P(0.645, b1)], fill=LINE)            # the gap between the teeth
for row, (y0, y1) in enumerate(((0.533, b0), (b1, 0.607))):         # upper and lower teeth
    n = 8
    for i in range(n):
        x0 = 0.385 + i * (0.23 / n)
        r = int(S * 0.006)
        d.rounded_rectangle([*P(x0 + 0.002, y0), *P(x0 + 0.23 / n - 0.002, y1)], radius=r, fill=TEETH, outline=LINE, width=int(S * 0.002))

# nose: an upside-down heart
dot(0.488, 0.462, 0.015, LINE), dot(0.512, 0.462, 0.015, LINE)
d.polygon([P(0.4745, 0.468), P(0.5255, 0.468), P(0.5, 0.507)], fill=LINE)

# eyes: flower-petal rims, dark sockets, glowing pupils
(rx, ry) = L["socket"]
for (ex, ey) in L["eyes"]:
    for i in range(14):
        a = 2 * math.pi * i / 14
        col = (PINK, TEAL, YELLOW)[i % 3]
        px, py = ex + math.cos(a) * (rx + 0.016), ey + math.sin(a) * (ry + 0.016)
        d.polygon(ell(px, py, 0.016, 0.0085, 24, a), fill=col, outline=LINE, width=int(S * 0.0015))
    d.polygon(ell(ex, ey, rx + 0.004, ry + 0.004), fill=LINE)
    d.polygon(ell(ex, ey, rx, ry), fill=SOCKET)
    dot(ex, ey, L["pupil"], GOLD)
    dot(ex, ey, L["pupil"] * 0.6, (255, 120, 20))
    dot(ex - 0.009, ey - 0.010, 0.0075, (255, 255, 255))      # sparkle
    dot(ex + 0.008, ey + 0.008, 0.0035, (255, 255, 255))
for (bx, by) in L["brows"]:                     # brows: arcs of dots
    for i in range(7):
        a = math.pi * (1.15 + 0.7 * i / 6)
        dot(bx + math.cos(a) * 0.075, by + 0.075 + math.sin(a) * 0.075 - 0.03, 0.0065, TEAL)   # raised: cheerful

# forehead: a small heart of dots, and an arch of dots under the hat brim
for (ox, oy) in ((0, 0.035), (-0.016, 0.0), (0.016, 0.0), (-0.03, -0.012), (0.03, -0.012), (-0.008, 0.018), (0.008, 0.018), (0, 0)):
    dot(0.5 + ox, 0.215 + oy * 0.9, 0.0062, PINK)
for i in range(15):
    a = math.pi * (1.08 + 0.84 * i / 14)
    dot(0.5 + math.cos(a) * 0.205, 0.33 + math.sin(a) * 0.19, 0.0075, PINK if i % 2 else YELLOW)

# cheeks: rosy blush with a small swirl; the grin curls up at both corners
blush = Image.new("RGBA", (S, S), (0, 0, 0, 0))
for cx in (0.335, 0.665):
    ImageDraw.Draw(blush).ellipse([*P(cx - 0.045, 0.468 - 0.028), *P(cx + 0.045, 0.468 + 0.028)], fill=(255, 105, 150, 120))
blush = blush.filter(ImageFilter.GaussianBlur(S * 0.006))
img.alpha_composite(blush)
d = ImageDraw.Draw(img)
spiral(0.335, 0.468, 0.018, 1.6, PINK, w=0.004, flip=-1), spiral(0.665, 0.468, 0.018, 1.6, PINK, w=0.004)
for side in (-1, 1):                            # the grin: from the ends of the teeth, out and up toward the cheeks
    x0 = 0.5 + side * 0.118
    d.line([P(x0 + side * 0.04 * t, 0.572 - 0.045 * t ** 1.8) for t in [i / 24 for i in range(25)]], fill=LINE,
           width=int(0.007 * S), joint="curve")
    dot(x0 + side * 0.04, 0.527, 0.0045, LINE)   # dimple at the end
# happy eyes: a smiling lower lid across the bottom of each socket (only inside the socket)
for (ex, ey) in L["eyes"]:
    lid = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lid)
    ld.polygon(ell(ex, ey + ry * 1.25, rx * 1.3, ry * 0.62 + 0.007), fill=LINE)
    ld.polygon(ell(ex, ey + ry * 1.25, rx * 1.3, ry * 0.62), fill=BONE)
    inside = Image.new("L", (S, S), 0)
    ImageDraw.Draw(inside).polygon(ell(ex, ey, rx + 0.0045, ry + 0.0045), fill=255)
    img.paste(lid, (0, 0), ImageChops.multiply(inside, lid.split()[3]))
d = ImageDraw.Draw(img)
for (tx, ty) in ((0.295, 0.33), (0.705, 0.33)):
    for k, (ox, oy) in enumerate(((0, 0), (0.014, -0.012), (0.014, 0.012), (-0.002, 0.024), (-0.002, -0.024))):
        dot(tx + (ox if tx < 0.5 else -ox), ty + oy, 0.0055, (TEAL, PINK, YELLOW)[k % 3])
dot(0.492, 0.632, 0.009, PINK), dot(0.508, 0.632, 0.009, PINK)
d.polygon([P(0.4835, 0.635), P(0.5165, 0.635), P(0.5, 0.655)], fill=PINK)

# ---------- sombrero ----------
STRAW, STRAW_D, RED = (236, 184, 82), (196, 140, 52), (226, 46, 74)
crown = [(0.355, 0.085), (0.375, -0.02), (0.40, -0.095), (0.44, -0.135), (0.5, -0.148),
         (0.56, -0.135), (0.60, -0.095), (0.625, -0.02), (0.645, 0.085)]
shape(crown, STRAW, w=0.006)
for k in range(5):                              # woven lines on the crown
    y = -0.10 + k * 0.035
    d.line([P(0.405 - k * 0.008, y), P(0.595 + k * 0.008, y)], fill=STRAW_D, width=int(0.003 * S))
shape([(0.37, 0.005), (0.63, 0.005), (0.64, 0.06), (0.36, 0.06)], RED, w=0.004)      # hat band
for k in range(12):                             # zigzag on the band
    x = 0.37 + k * 0.0217
    d.line([P(x, 0.045), P(x + 0.0108, 0.02), P(x + 0.0217, 0.045)], fill=YELLOW, width=int(0.004 * S))
for side in (-1, 1):
    d.polygon(ell(0.5 + side * 0.06, 0.035, 0.035, 0.012, 40, side * 0.25), fill=GREEN, outline=LINE, width=int(S * 0.0015))
flower(0.5, 0.03, 0.055, [(18, 1.0, 0.22, ORANGE, 0), (14, 0.75, 0.24, GOLD, 0.2), (10, 0.5, 0.28, YELLOW, 0.1)], ORANGE)
brim = ell(0.5, 0.105, 0.43, 0.07, 200)
shape(brim, STRAW, w=0.007)
d.polygon(ell(0.5, 0.105, 0.38, 0.05, 200), fill=STRAW_D)                            # inner ring
d.polygon(ell(0.5, 0.098, 0.37, 0.044, 200), fill=STRAW)
d.polygon([P(0.355, 0.085), P(0.645, 0.085), P(0.645, 0.098), P(0.355, 0.098)], fill=STRAW)  # crown meets brim
for k in range(26):                             # pink and teal triangles round the brim edge
    t = 2 * math.pi * k / 26
    x, y = 0.5 + math.cos(t) * 0.405, 0.105 + math.sin(t) * 0.06
    dot(x, y, 0.009, (PINK, TEAL)[k % 2])
for k in range(9):                              # pompoms hanging from the front of the brim
    x = 0.17 + k * 0.0825
    y = 0.105 + 0.07 * math.sqrt(max(0.0, 1 - ((x - 0.5) / 0.43) ** 2))
    d.line([P(x, y), P(x, y + 0.02)], fill=LINE, width=int(0.003 * S))
    dot(x, y + 0.028, 0.011, LINE)
    dot(x, y + 0.028, 0.009, (PINK, YELLOW, TEAL, ORANGE)[k % 4])

img.resize((OUT, OUT), Image.LANCZOS).save("calavera.png")
K, OY = 1.0, 0.0                                # the backdrop fills the whole picture

# ---------- backdrop: night sky gradient, papel picado, marigolds and candles ----------
bg = Image.new("RGB", (S, S))
g = ImageDraw.Draw(bg)
for y in range(S):
    t = y / S
    g.line([(0, y), (S, y)], fill=(int(42 - 20 * t), int(17 + 40 * t), int(69 + 10 * t)))
glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
gg = ImageDraw.Draw(glow)
gg.ellipse([S * 0.18, S * 0.18, S * 0.82, S * 0.82], fill=(255, 140, 60, 70))     # warm glow behind him
bg.paste(glow.filter(ImageFilter.GaussianBlur(S * 0.08)), (0, 0), glow.filter(ImageFilter.GaussianBlur(S * 0.08)))
g = ImageDraw.Draw(bg)
cols = [PINK, ORANGE, TEAL, YELLOW, PURPLE, GREEN]
for row, (y, sag, w) in enumerate(((0.12, 0.035, 0.085), (0.21, 0.03, 0.07))):
    n = int(0.9 / w)
    xs = [0.05 + i * 0.9 / n for i in range(n + 1)]
    yy = lambda x: y + sag * (1 - ((x - 0.5) / 0.45) ** 2)
    g.line([(x * S, yy(x) * S) for x in [0.05 + i * 0.9 / 60 for i in range(61)]], fill=(220, 220, 220), width=6)
    for i in range(n):
        x0, x1 = xs[i] + 0.006, xs[i + 1] - 0.006
        top, h = yy((x0 + x1) / 2), w * 1.1
        col = cols[(i + row * 3) % len(cols)]
        flag = [(x0 * S, top * S), (x1 * S, top * S), (x1 * S, (top + h) * S),
                ((x1 - (x1 - x0) / 4) * S, (top + h * 0.9) * S), ((x0 + x1) / 2 * S, (top + h) * S),
                ((x0 + (x1 - x0) / 4) * S, (top + h * 0.9) * S), (x0 * S, (top + h) * S)]
        g.polygon(flag, fill=col)
        cx, cy, r = (x0 + x1) / 2 * S, (top + h * 0.45) * S, (x1 - x0) * S * 0.22
        hole = tuple(int(c * 0.25 + v * 0.75) for c, v in zip(col, (40, 30, 70)))
        for k in range(8):                                                 # cut-out flower
            a = 2 * math.pi * k / 8
            g.ellipse([cx + math.cos(a) * r - r * 0.32, cy + math.sin(a) * r - r * 0.32,
                       cx + math.cos(a) * r + r * 0.32, cy + math.sin(a) * r + r * 0.32], fill=hole)
        g.ellipse([cx - r * 0.45, cy - r * 0.45, cx + r * 0.45, cy + r * 0.45], fill=hole)
        for k in (-1, 1):
            g.rectangle([cx + k * r * 1.6 - r * 0.12, cy + r * 1.3, cx + k * r * 1.6 + r * 0.12, cy + r * 1.9], fill=hole)
d = ImageDraw.Draw(bg)                          # reuse flower() on the backdrop
for i, x in enumerate([0.08, 0.17, 0.27, 0.73, 0.83, 0.92, 0.12, 0.88, 0.22, 0.78]):
    y = 0.80 + (i % 3) * 0.035 + (0.04 if i >= 6 else 0)
    flower(x, y, 0.045 + (i % 2) * 0.01, [(16, 1.0, 0.24, ORANGE, 0), (12, 0.7, 0.26, GOLD, 0.2)], ORANGE)
for x in (0.20, 0.33, 0.67, 0.80):                                         # candles
    d.rectangle([*P(x - 0.012, 0.70), *P(x + 0.012, 0.79)], fill=(245, 236, 210))
    light = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(light).ellipse([*P(x - 0.05, 0.62), *P(x + 0.05, 0.72)], fill=(255, 190, 80, 150))
    light = light.filter(ImageFilter.GaussianBlur(S * 0.02))
    bg.paste(light, (0, 0), light)
    d = ImageDraw.Draw(bg)
    d.polygon(ell(x, 0.685, 0.007, 0.016, 30), fill=(255, 200, 60))
bg = bg.filter(ImageFilter.GaussianBlur(S * 0.0025))                       # a touch soft, so he stays in front
bg.resize((OUT, OUT), Image.LANCZOS).save("calavera-bg.png")
X, Y = (lambda x: 0.5 + (x - 0.5) * 0.86), (lambda y: 0.14 + y * 0.86)   # same K, OY as the character
M = {"band": [Y(v) for v in L["band"]], "jaw": [X(L["jaw"][0]), X(L["jaw"][1]), Y(L["jaw"][2]), Y(L["jaw"][3])],
     "eyes": [[X(x), Y(y)] for x, y in L["eyes"]], "socket": [v * 0.86 for v in L["socket"]], "pupil": L["pupil"] * 0.86,
     "brows": [[X(x), Y(y - 0.01)] for x, y in L["brows"]], "neck": [Y(v) for v in L["neck"]]}
json.dump(M, open("calavera.json", "w"), indent=1)
print("wrote calavera.png, calavera-bg.png, calavera.json")
