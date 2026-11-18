"""La Calavera's state and costume overlays, drawn as transparent layers over his unchanged art (avatar-intake/calavera.png).
Same coordinate frame as calavera_art.py (character drawn at K = 0.86, OY = 0.14), so charkit.Art(0.86, 0.14) lines up.
  celebrate  happy closed eyes          wave     a raised skeletal hand in his suit sleeve (swings from the shoulder)
  glasses    round reading glasses      pen      a fountain pen in his breast pocket (signing day)
"""
import math
from PIL import Image
from charkit import Art, LINE, GOLD, PURPLE

BONE, SUIT, SHIRT = (243, 234, 216), (29, 27, 38), (250, 248, 244)
EYES, SOCKET = [(0.405, 0.385), (0.595, 0.385)], (0.072, 0.07)
SHOULDER = (0.865, 0.905)                         # the arm's pivot, art coordinates
SWING = {"wave": {"pivot": [0.5 + (SHOULDER[0] - 0.5) * 0.86, 0.14 + SHOULDER[1] * 0.86], "deg": -16}}


def out(a):
    return a.img.resize((2048, 2048), Image.LANCZOS)


def celebrate():
    a = Art()
    rx, ry = SOCKET
    for ex, ey in EYES:
        a.blob(ex, ey, rx + 0.006, ry + 0.006, BONE, w=0)                       # cover the socket and its lid
        a.arc(ex, ey + 0.022, rx * 0.78, ry * 0.62, math.pi * 1.08, math.pi * 1.92, LINE, 0.018)   # a smiling closed eye
    return out(a)


def glasses():
    a = Art()
    rx, _ = SOCKET
    frame, r = (122, 74, 26), rx + 0.032
    for ex, ey in EYES:
        a.blob(ex, ey, r, r * 0.92, (255, 255, 255, 46), w=0)                   # a faint glass shine (the layer is transparent)
        a.arc(ex, ey, r, r * 0.92, 0, 2 * math.pi, LINE, 0.016, n=90)
        a.arc(ex, ey, r, r * 0.92, 0, 2 * math.pi, frame, 0.009, n=90)
        a.arc(ex - 0.03, ey - 0.03, r * 0.55, r * 0.5, math.pi * 1.15, math.pi * 1.45, (255, 255, 255), 0.006)
    (x0, y0), (x1, _) = EYES
    a.arc(0.5, y0 + 0.004, x1 - 0.5 - r, 0.02, math.pi * 1.1, math.pi * 1.9, LINE, 0.014)   # the bridge
    a.arc(0.5, y0 + 0.004, x1 - 0.5 - r, 0.02, math.pi * 1.1, math.pi * 1.9, frame, 0.007)
    for side in (-1, 1):                                                         # temples, toward the ears
        xs = 0.5 + side * (x1 - 0.5 + r)
        a.line([(xs, y0 - 0.006), (xs + side * 0.06, y0 - 0.02)], LINE, 0.014)
        a.line([(xs, y0 - 0.006), (xs + side * 0.06, y0 - 0.02)], frame, 0.007)
    return out(a)


def pen():
    a = Art()
    x, top, bot, w = 0.30, 0.80, 0.905, 0.024
    a.shape([(x - w, top), (x + w, top), (x + w, bot), (x - w, bot)], PURPLE, w=0.005)                       # barrel
    a.shape([(x - w, top), (x + w, top), (x + w * 0.6, top - 0.034), (x - w * 0.6, top - 0.034)], (50, 30, 70), w=0.005)  # cap
    a.line([(x + w * 0.45, top - 0.024), (x + w * 0.45, top + 0.06)], GOLD, 0.009)                                    # clip
    a.dot(x + w * 0.45, top + 0.063, 0.008, GOLD)
    a.line([(x - w * 0.5, top + 0.02), (x - w * 0.5, bot - 0.01)], (160, 90, 220), 0.005)                            # shine
    a.shape([(0.23, bot), (0.37, bot), (0.37, bot + 0.016), (0.23, bot + 0.016)], (18, 16, 26), w=0.003)             # pocket edge
    return out(a)


def wave():
    a = Art()
    sx, sy = SHOULDER
    wx, wy = 0.90, 0.66                                                           # wrist
    ang = math.atan2(wy - sy, wx - sx)
    nx, ny = -math.sin(ang), math.cos(ang)
    w = 0.05
    a.shape([(sx + nx * w, sy + ny * w), (wx + nx * w * 0.85, wy + ny * w * 0.85),
             (wx - nx * w * 0.85, wy - ny * w * 0.85), (sx - nx * w, sy - ny * w)], SUIT, w=0.006)                # sleeve
    a.blob(wx, wy + 0.004, 0.044, 0.012, SHIRT, w=0.004, rot=ang)                                                # cuff
    s = 1.6                                                                       # hand scale
    hx, hy = wx + 0.004, wy - 0.06 * s                                            # palm centre
    a.blob(hx, hy, 0.034 * s, 0.04 * s, BONE, w=0.006)
    for dx, ln in ((-0.024, 0.055), (-0.008, 0.066), (0.008, 0.064), (0.024, 0.052)):                          # fingers
        fx0, fy0 = hx + dx * s, hy - 0.03 * s
        fx1, fy1 = fx0 + dx * s * 0.25, fy0 - ln * s
        a.line([(fx0, fy0), (fx1, fy1)], LINE, 0.034)
        a.line([(fx0, fy0), (fx1, fy1)], BONE, 0.021)
        a.dot(fx1, fy1, 0.017, LINE); a.dot(fx1, fy1, 0.0105, BONE)                    # round fingertip
        a.dot(fx0 + (fx1 - fx0) * 0.5, fy0 + (fy1 - fy0) * 0.5, 0.005, LINE)        # knuckle
    tx0, ty0 = hx - 0.03 * s, hy + 0.005 * s
    a.line([(tx0, ty0), (tx0 - 0.032 * s, ty0 - 0.03 * s)], LINE, 0.034)                                       # thumb
    a.line([(tx0, ty0), (tx0 - 0.032 * s, ty0 - 0.03 * s)], BONE, 0.021)
    a.blob(hx, hy, 0.024 * s, 0.028 * s, BONE, w=0)                                                             # clean palm
    a.dot(hx - 0.004, hy + 0.006, 0.006 * s, (255, 79, 154)); a.dot(hx + 0.004, hy + 0.006, 0.006 * s, (255, 79, 154))  # a heart,
    a.d.polygon([a.P(hx - 0.0095 * s, hy + 0.0075 * s), a.P(hx + 0.0095 * s, hy + 0.0075 * s), a.P(hx, hy + 0.02 * s)],  # like his chin
                fill=(255, 79, 154))
    return out(a)


def layers():
    return {"celebrate": celebrate(), "glasses": glasses(), "pen": pen(), "wave": wave()}
