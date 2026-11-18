"""El Oso: a big, happy bear, the gentle guide for the health care directive and the hard conversations (incapacity,
end of life). Calm and kind. Phase 1 sketch in La Calavera's style.
Run:  python oso_art.py  ->  oso.png, oso-bg.png (a calm dusk, fewer and softer things than the fiesta backdrops),
oso.json (moving parts, the same keys as calavera.json).
"""
import json, math
from charkit import Art, LINE, PINK, TEAL, YELLOW, ORANGE, GOLD, GREEN, PURPLE, WHITE, S
from PIL import Image, ImageDraw, ImageFilter

FUR, FUR_D, FUR_L = (176, 112, 64), (138, 84, 46), (226, 182, 128)       # warm brown, its shadow, the muzzle and ears
SWEATER, SWEATER_D = (38, 120, 128), (28, 92, 100)                         # deep teal cardigan
SARAPE = [(214, 76, 96), (246, 196, 82), (46, 160, 150), (250, 238, 214), (123, 44, 191), (232, 120, 40)]
EYE = (120, 66, 30)

L = {"jawDrop": 0.05, "jawFade": 0.03, "band": [0.552, 0.568], "jaw": [0.44, 0.56, 0.568, 0.6], "eyes": [[0.415, 0.385], [0.585, 0.385]],
     "socket": [0.043, 0.047], "pupil": 0.024, "brows": [[0.415, 0.315], [0.585, 0.315]], "neck": [0.655, 0.73]}


def draw(jaw=0.0, blink=0.0, look=0.0, hug=False):
    a = Art()
    # ---- cardigan, buttons, and a sarape scarf wrapped round the neck ----
    a.shape([(0.04, 1.01), (0.08, 0.86), (0.2, 0.765), (0.38, 0.72), (0.62, 0.72), (0.8, 0.765), (0.92, 0.86), (0.96, 1.01)],
            SWEATER)
    body = a.pts([(0.04, 1.01), (0.08, 0.86), (0.2, 0.765), (0.38, 0.72), (0.62, 0.72), (0.8, 0.765), (0.92, 0.86), (0.96, 1.01)])

    def ribs(sub):                                          # knit ribs, kept inside the cardigan
        for side in (-1, 1):
            for k in range(6):
                x = 0.5 + side * (0.12 + k * 0.06)
                sub.line([(x, 0.72), (x - side * 0.02, 1.01)], SWEATER_D, 0.004)
    a.clip_to(ribs, body)
    a.shape([(0.44, 0.74), (0.56, 0.74), (0.54, 1.01), (0.46, 1.01)], (250, 238, 214), w=0.003)   # shirt
    for y in (0.86, 0.94):
        a.dot(0.5, y, 0.011, LINE), a.dot(0.5, y, 0.008, GOLD)
    scarf = [(0.22, 0.74), (0.32, 0.66), (0.5, 0.635), (0.68, 0.66), (0.78, 0.74), (0.68, 0.79), (0.5, 0.775), (0.32, 0.79)]
    sp = a.pts(scarf)
    a.d.line(sp + [sp[0]], fill=LINE, width=a.w(0.012), joint="curve")

    def stripes(sub):
        for k in range(14):
            x = 0.18 + k * 0.047
            sub.d.polygon(sub.pts([(x, 0.6), (x + 0.047, 0.6), (x + 0.02, 0.82), (x - 0.027, 0.82)]), fill=SARAPE[k % len(SARAPE)])
            sub.line([(x + 0.0235, 0.6), (x - 0.0035, 0.82)], (250, 238, 214), 0.002)
    a.clip_to(stripes, sp)
    tail = [(0.6, 0.77), (0.67, 0.775), (0.70, 0.96), (0.62, 0.95)]          # the end that hangs down the front
    tp = a.pts(tail)
    a.d.line(tp + [tp[0]], fill=LINE, width=a.w(0.010), joint="curve")
    a.clip_to(lambda sub: [sub.d.polygon(sub.pts([(0.55, 0.77 + k * 0.03), (0.75, 0.77 + k * 0.03), (0.75, 0.80 + k * 0.03),
                                                   (0.55, 0.80 + k * 0.03)]), fill=SARAPE[k % len(SARAPE)]) for k in range(7)], tp)
    for k in range(7):                                       # fringe on the scarf end
        x = 0.625 + k * 0.011
        a.line([(x, 0.955), (x - 0.002, 0.985)], SARAPE[k % len(SARAPE)], 0.005)
    a.marigold(0.355, 0.735, 0.03)                           # a marigold pinned to the scarf, like La Calavera's boutonniere

    # ---- ears, head, muzzle ----
    for side in (-1, 1):
        a.blob(0.5 + side * 0.2, 0.175, 0.075, 0.07, FUR)
        a.blob(0.5 + side * 0.2, 0.18, 0.042, 0.04, FUR_L, w=0.003)
    head = a.ell(0.5, 0.405, 0.255, 0.235, 180)
    a.d.line(head + [head[0]], fill=LINE, width=a.w(0.012), joint="curve")
    a.d.polygon(head, fill=FUR)

    def fur(sub):                                             # soft fur tufts round the face edge, and on the crown
        for k in range(26):
            t = 2 * math.pi * k / 26
            x, y = 0.5 + math.cos(t) * 0.235, 0.405 + math.sin(t) * 0.215
            sub.arc(x, y, 0.02, 0.012, t + math.pi * 0.6, t + math.pi * 1.4, FUR_D, 0.004)
    a.clip_to(fur, head)
    a.blob(0.5, 0.535, 0.135, 0.095, FUR_L)
    a.blush([(0.36, 0.495), (0.64, 0.495)], ry=0.026, rx=0.042, alpha=110)

    # ---- face: kind eyes with a smiling lower lid, soft brows, a shiny nose, a gentle smile ----
    for (bx, by) in L["brows"]:
        a.arc(bx, by + 0.035, 0.035, 0.02, math.pi * 1.15, math.pi * 1.85, FUR_D, 0.012)
    rx, ry = L["socket"]
    for (ex, ey) in L["eyes"]:
        a.eye(ex, ey, rx, ry, (196, 128, 52), look, blink, lid_fill=FUR, sclera=(40, 22, 30), pupil=0.025)
    nose = [(0.455, 0.478), (0.545, 0.478), (0.54, 0.495), (0.5, 0.53), (0.46, 0.495)]
    a.shape(nose, LINE, w=0.004)
    a.blob(0.485, 0.49, 0.014, 0.007, (110, 80, 120), w=0)
    a.line([(0.5, 0.528), (0.5, 0.556)], LINE, 0.006)
    b0, b1 = L["band"]
    gap = (b1 - b0) + jaw * 0.045
    a.d.rounded_rectangle([*a.P(0.462, b0), *a.P(0.538, b0 + gap)], radius=a.w(0.006), fill=(70, 30, 50),
                          outline=LINE, width=a.w(0.004))                      # a small dark mouth: the jaw key opens it
    if gap > 0.02:
        a.blob(0.5, b0 + gap * 0.72, 0.024, gap * 0.26, (230, 110, 130), w=0)    # tongue, when open
    for side in (-1, 1):                                                       # the smile curls up from its corners
        x0 = 0.5 + side * 0.036
        a.line([(x0 + side * 0.035 * t, b0 + 0.004 - 0.022 * t ** 1.6) for t in [i / 16 for i in range(17)]], LINE, 0.007)
    if hug:                                                   # paws up, as if offering a hug (the "comfort" state)
        for side in (-1, 1):
            a.blob(0.5 + side * 0.22, 0.86, 0.08, 0.07, FUR)
            for k in range(3):
                a.blob(0.5 + side * (0.18 + k * 0.035), 0.815, 0.017, 0.015, FUR_L, w=0.003)
    return a


def backdrop():
    """A calm dusk: deep blue-violet, a low moon, two candles, a few marigolds. No string lights or confetti."""
    a = Art(1.0, 0.0, mode="RGB", bg=(0, 0, 0))
    for y in range(S):
        t = y / S
        a.d.line([(0, y), (S, y)], fill=(int(38 - 12 * t), int(34 + 20 * t), int(86 - 6 * t)))
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([S * 0.2, S * 0.22, S * 0.8, S * 0.86], fill=(255, 170, 110, 55))
    moon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(moon).ellipse([S * 0.74, S * 0.08, S * 0.9, S * 0.24], fill=(255, 236, 196, 200))
    for layer, blur in ((glow, 0.09), (moon, 0.004)):
        layer = layer.filter(ImageFilter.GaussianBlur(S * blur))
        a.img.paste(layer, (0, 0), layer)
    a.d = ImageDraw.Draw(a.img)
    import random
    rnd = random.Random(5)
    for k in range(40):                                        # a few faint stars
        a.dot(rnd.uniform(0.02, 0.98), rnd.uniform(0.02, 0.5), 0.002 + (k % 3) * 0.001, (230, 226, 255))
    for x in (0.16, 0.84):                                     # two candles
        a.d.rectangle([*a.P(x - 0.014, 0.72), *a.P(x + 0.014, 0.83)], fill=(245, 236, 210))
        light = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(light).ellipse([*a.P(x - 0.06, 0.63), *a.P(x + 0.06, 0.75)], fill=(255, 190, 80, 140))
        light = light.filter(ImageFilter.GaussianBlur(S * 0.025))
        a.img.paste(light, (0, 0), light)
        a.d = ImageDraw.Draw(a.img)
        a.d.polygon(a.ell(x, 0.70, 0.008, 0.018, 30), fill=(255, 200, 60))
    for i, x in enumerate([0.07, 0.25, 0.75, 0.93]):
        a.marigold(x, 0.88 + (i % 2) * 0.04, 0.05)
    a.img = a.img.filter(ImageFilter.GaussianBlur(S * 0.003))
    return a



def rig():
    """Where the moving parts are, as fractions of the 2048 picture (the K, OY of the drawing applied)."""
    X, Y = (lambda x: 0.5 + (x - 0.5) * 0.86), (lambda y: 0.14 + y * 0.86)
    return {"band": [Y(v) for v in L["band"]], "jaw": [X(L["jaw"][0]), X(L["jaw"][1]), Y(L["jaw"][2]), Y(L["jaw"][3])],
            "eyes": [[X(x), Y(y)] for x, y in L["eyes"]], "socket": [v * 0.86 for v in L["socket"]], "pupil": L["pupil"] * 0.86,
            "brows": [[X(x), Y(y)] for x, y in L["brows"]], "neck": [Y(v) for v in L["neck"]],
            "jawDrop": L.get("jawDrop", 0.07), "jawFade": L.get("jawFade", 0.035)}

if __name__ == "__main__":
    draw().save("oso.png")
    backdrop().save("oso-bg.png")
    X, Y = (lambda x: 0.5 + (x - 0.5) * 0.86), (lambda y: 0.14 + y * 0.86)
    M = {"band": [Y(v) for v in L["band"]], "jaw": [X(L["jaw"][0]), X(L["jaw"][1]), Y(L["jaw"][2]), Y(L["jaw"][3])],
         "eyes": [[X(x), Y(y)] for x, y in L["eyes"]], "socket": [v * 0.86 for v in L["socket"]], "pupil": L["pupil"] * 0.86,
         "brows": [[X(x), Y(y)] for x, y in L["brows"]], "neck": [Y(v) for v in L["neck"]]}
    json.dump(M, open("oso.json", "w"), indent=1)
    print("wrote oso.png, oso-bg.png, oso.json")
