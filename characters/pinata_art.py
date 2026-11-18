"""Piñata: a colourful burro piñata who hosts the games and quizzes. Phase 1 sketch in La Calavera's style.
Run:  python pinata_art.py   ->  pinata.png (character), pinata-bg.png (backdrop), pinata.json (moving parts, the same
keys as calavera.json, so a make_character.py like make_calavera.py gives her the shared shape keys).
draw(jaw, blink, look, party) renders one pose, for the expression sheet.
"""
import json, math
from charkit import Art, LINE, PINK, TEAL, YELLOW, ORANGE, GOLD, GREEN, PURPLE, WHITE, confetti, S, OUT
from PIL import Image, ImageDraw, ImageFilter

HEAD, HEAD_D = (255, 92, 168), (226, 52, 132)          # crepe-paper pink and its fringe shadow
MUZZLE, MUZZLE_D = (255, 226, 120), (240, 190, 70)
EAR_IN = (255, 210, 63)
BANDS = [TEAL, YELLOW, PINK, ORANGE, PURPLE, GREEN]

L = {"jawDrop": 0.06, "jawFade": 0.03, "band": [0.586, 0.598], "jaw": [0.42, 0.58, 0.598, 0.64], "eyes": [[0.425, 0.355], [0.575, 0.355]],
     "socket": [0.046, 0.054], "pupil": 0.022, "brows": [[0.425, 0.278], [0.575, 0.278]], "neck": [0.69, 0.765]}


def shade(c, f):
    return tuple(int(v * f) for v in c)


def fringe(a, region, colours, y0, y1, step=0.036, base=None, light=None):
    """Rows of crepe-paper fringe filling `region` (a polygon in picture space): each row is a strip of rounded
    paper tongues that overlaps the row below, with a soft shadow under it. base/light alternate for a one-colour piece."""
    def paint(sub):
        rows = int((y1 - y0) / step) + 1
        for r in range(rows):
            y = y0 + r * step
            col = colours[r % len(colours)] if base is None else (base if r % 2 == 0 or not light else light)
            sub.d.polygon(sub.pts([(0, y), (1, y), (1, y + step + 0.004), (0, y + step + 0.004)]), fill=col)
            sub.d.polygon(sub.pts([(0, y), (1, y), (1, y + step * 0.18), (0, y + step * 0.18)]), fill=shade(col, 0.86))
            n = 44
            for i in range(n):
                x = i / n + (0.5 / n if r % 2 else 0)
                sub.d.line(sub.pts([(x, y + step * 0.25), (x, y + step * 0.95)]), fill=shade(col, 0.9), width=sub.w(0.0018))
    a.clip_to(paint, region)


def draw(jaw=0.0, blink=0.0, look=0.0, party=False):
    a = Art()
    # ---- body: a barrel of rainbow fringe, with a purple paper bow (La Calavera wears a purple bow tie too) ----
    body = a.pts([(0.08, 1.01), (0.12, 0.865), (0.24, 0.79), (0.40, 0.762), (0.60, 0.762), (0.76, 0.79), (0.88, 0.865), (0.92, 1.01)])
    a.d.line(body + [body[0]], fill=LINE, width=a.w(0.012), joint="curve")
    fringe(a, body, BANDS, 0.75, 1.02, 0.045)
    neck = a.pts([(0.43, 0.62), (0.57, 0.62), (0.585, 0.78), (0.415, 0.78)])
    a.d.line(neck + [neck[0]], fill=LINE, width=a.w(0.012), joint="curve")
    fringe(a, neck, [YELLOW, TEAL, PINK], 0.62, 0.79, 0.04)
    for side in (-1, 1):                                   # the bow, then streamers falling from it
        a.shape([(0.5, 0.785), (0.5 + side * 0.075, 0.755), (0.5 + side * 0.075, 0.815)], PURPLE, w=0.003)
        for k, col in enumerate((TEAL, YELLOW, PINK)):
            x0 = 0.5 + side * (0.02 + k * 0.012)
            a.line([(x0 + side * 0.02 * math.sin(t * 6) + side * t * 0.05, 0.80 + t * 0.17) for t in [i / 20 for i in range(21)]],
                   col, 0.009)
    a.dot(0.5, 0.785, 0.016, LINE), a.dot(0.5, 0.785, 0.012, PURPLE)

    # ---- ears, with paper tassels at the tips ----
    for side in (-1, 1):
        cx, rot = 0.5 + side * 0.118, side * 0.33
        a.blob(cx, 0.135, 0.056, 0.155, HEAD, w=0.006, rot=rot)
        a.blob(cx + side * 0.004, 0.15, 0.03, 0.11, EAR_IN, w=0.003, rot=rot)
        tx, ty = cx + side * 0.055, 0.0
        for k, col in enumerate((PINK, TEAL, YELLOW, ORANGE)):
            a.line([(tx, ty), (tx + side * (0.02 + k * 0.012), ty - 0.045 + k * 0.006)], col, 0.008)

    # ---- head and muzzle: outlines first, then fills, so they join without inner lines ----
    head = a.ell(0.5, 0.355, 0.175, 0.178, 160)
    muzzle = a.ell(0.5, 0.56, 0.158, 0.112, 160)
    for p in (head, muzzle):
        a.d.line(p + [p[0]], fill=LINE, width=a.w(0.012), joint="curve")
    fringe(a, head, None, 0.17, 0.62, 0.034, base=HEAD, light=(255, 128, 190))
    shadow = Image.new("RGBA", a.img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon(a.ell(0.5, 0.585, 0.17, 0.12, 120), fill=(120, 20, 70, 90))
    a.img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(S * 0.01)))
    a.d = ImageDraw.Draw(a.img)
    a.d.polygon(muzzle, fill=MUZZLE)
    fringe(a, muzzle, None, 0.45, 0.68, 0.034, base=MUZZLE, light=(255, 236, 160))
    # forelock: a fan of paper strips between the ears
    for k, col in enumerate((PURPLE, TEAL, YELLOW, ORANGE, PINK, GREEN, PURPLE)):
        ang = math.pi * (1.22 + 0.56 * k / 6)
        x0, y0 = 0.5 + math.cos(ang) * 0.02, 0.215
        tip = (0.5 + math.cos(ang) * 0.085, 0.215 + math.sin(ang) * 0.085)
        a.shape([(x0 - 0.012, y0), (x0 + 0.012, y0), tip], col, w=0.0025)

    # ---- face ----
    for (bx, by) in L["brows"]:                       # brows: short paper strips, lifted
        a.arc(bx, by + 0.03, 0.04, 0.025, math.pi * 1.2, math.pi * 1.8, LINE, 0.014)
        a.arc(bx, by + 0.03, 0.04, 0.025, math.pi * 1.22, math.pi * 1.78, PURPLE, 0.008)
    rx, ry = L["socket"]
    for (ex, ey) in L["eyes"]:
        a.eye(ex, ey, rx, ry, GOLD, look, blink, lid_fill=HEAD, sclera=WHITE, pupil=0.024)
        if blink < 0.95:                              # three lashes on the outer side
            side = -1 if ex < 0.5 else 1
            for k in range(3):
                t = math.pi * (1.5 + side * (0.18 + 0.12 * k))
                x, y = ex + math.cos(t) * rx, ey + math.sin(t) * ry * (1 - blink)
                a.line([(x, y), (x + math.cos(t) * 0.022, y + math.sin(t) * 0.022)], LINE, 0.006)
    a.blush([(0.392, 0.565), (0.608, 0.565)], ry=0.022, rx=0.034)
    for side in (-1, 1):                              # nostrils
        a.blob(0.5 + side * 0.045, 0.528, 0.012, 0.018, LINE, w=0, rot=side * 0.35)
    b0, b1 = L["band"]
    gap = (b1 - b0) + jaw * 0.055
    mouth = [(0.425, b0 - 0.006), (0.575, b0 - 0.006), (0.565, b0 + gap * 0.75), (0.53, b0 + gap), (0.47, b0 + gap),
             (0.435, b0 + gap * 0.75)]
    a.shape(mouth, LINE, w=0.004)
    if jaw > 0.2:
        a.blob(0.5, b0 + gap * 0.72, 0.035, gap * 0.28, (240, 90, 120), w=0)
    for x0 in (0.481, 0.501):                         # two friendly front teeth
        a.d.rounded_rectangle([*a.P(x0, b0 - 0.022), *a.P(x0 + 0.018, b0 + 0.001)], radius=a.w(0.004), fill=WHITE,
                              outline=LINE, width=a.w(0.003))
    for side in (-1, 1):                              # the grin curls up at the corners, with a dimple, like La Calavera's
        x0 = 0.5 + side * 0.073
        a.line([(x0 + side * 0.038 * t, b0 - 0.004 - 0.04 * t ** 1.7) for t in [i / 20 for i in range(21)]], LINE, 0.008)
        a.dot(x0 + side * 0.038, b0 - 0.044, 0.005, LINE)
    if party:
        confetti(a, 90, seed=7)
    return a


def backdrop():
    a = Art(1.0, 0.0, mode="RGB", bg=(0, 0, 0))
    for y in range(S):
        t = y / S
        a.d.line([(0, y), (S, y)], fill=(int(74 - 40 * t), int(20 + 26 * t), int(80 + 18 * t)))
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([S * 0.18, S * 0.2, S * 0.82, S * 0.84], fill=(255, 90, 170, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.08))
    a.img.paste(glow, (0, 0), glow)
    a.d = ImageDraw.Draw(a.img)
    for row, (y, sag) in enumerate(((0.10, 0.05), (0.22, 0.04))):      # string lights
        xs = [0.03 + i * 0.94 / 60 for i in range(61)]
        yy = lambda x: y + sag * (1 - ((x - 0.5) / 0.47) ** 2)
        a.line([(x, yy(x)) for x in xs], (210, 200, 220), 0.002)
        for i in range(13):
            x = 0.06 + i * 0.07 + row * 0.035
            col = (PINK, YELLOW, TEAL, ORANGE)[(i + row) % 4]
            halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
            ImageDraw.Draw(halo).ellipse([*a.P(x - 0.03, yy(x) - 0.01), *a.P(x + 0.03, yy(x) + 0.05)], fill=(*col, 110))
            halo = halo.filter(ImageFilter.GaussianBlur(S * 0.012))
            a.img.paste(halo, (0, 0), halo)
            a.d = ImageDraw.Draw(a.img)
            a.blob(x, yy(x) + 0.02, 0.011, 0.016, col, w=0)
    confetti(a, 140, seed=11, area=(0.02, 0.3, 0.98, 0.98))
    a.img = a.img.filter(ImageFilter.GaussianBlur(S * 0.0025))
    return a



def rig():
    """Where the moving parts are, as fractions of the 2048 picture (the K, OY of the drawing applied)."""
    X, Y = (lambda x: 0.5 + (x - 0.5) * 0.86), (lambda y: 0.14 + y * 0.86)
    return {"band": [Y(v) for v in L["band"]], "jaw": [X(L["jaw"][0]), X(L["jaw"][1]), Y(L["jaw"][2]), Y(L["jaw"][3])],
            "eyes": [[X(x), Y(y)] for x, y in L["eyes"]], "socket": [v * 0.86 for v in L["socket"]], "pupil": L["pupil"] * 0.86,
            "brows": [[X(x), Y(y)] for x, y in L["brows"]], "neck": [Y(v) for v in L["neck"]],
            "jawDrop": L.get("jawDrop", 0.07), "jawFade": L.get("jawFade", 0.035)}

if __name__ == "__main__":
    draw().save("pinata.png")
    backdrop().save("pinata-bg.png")
    X, Y = (lambda x: 0.5 + (x - 0.5) * 0.86), (lambda y: 0.14 + y * 0.86)
    M = {"band": [Y(v) for v in L["band"]], "jaw": [X(L["jaw"][0]), X(L["jaw"][1]), Y(L["jaw"][2]), Y(L["jaw"][3])],
         "eyes": [[X(x), Y(y)] for x, y in L["eyes"]], "socket": [v * 0.86 for v in L["socket"]], "pupil": L["pupil"] * 0.86,
         "brows": [[X(x), Y(y)] for x, y in L["brows"]], "neck": [Y(v) for v in L["neck"]]}
    json.dump(M, open("pinata.json", "w"), indent=1)
    print("wrote pinata.png, pinata-bg.png, pinata.json")
