"""Turn the firm's website portrait into what make_avatar.py needs.
Run (in the avatar-tools Python env, it has OpenCV + the face models):
    %USERPROFILE%\\avatar-tools\\venv\\Scripts\\python.exe prep_photo.py
Reads  photos/Carbon-Law-Group-Los-Angeles-Pankaj-Raval-Founder-Of-Carbon-Law.jpg
Writes pankaj2.png  (square head-and-shoulders crop, face sharpened, background made transparent)
       pankaj2.json (98 face landmarks as fractions: u left->right, v bottom->top)

ponytail: OUTLINE and CROP are hand-drawn for this photo; redraw them for another one.
"""
import json, os, sys
from pathlib import Path
import cv2, numpy as np, torch
torch.set_grad_enabled(False)

ROOT = Path(__file__).parent
SAD = Path.home() / "avatar-tools" / "SadTalker"
SRC = ROOT / "photos" / "Carbon-Law-Group-Los-Angeles-Pankaj-Raval-Founder-Of-Carbon-Law.jpg"
CROP = (220, 0, 660)   # x, y, size in source pixels (stops short of the window frame at his elbow)
# He leans ~5 degrees in this photo (shoulder line; the head tilts ~10). Rotate the whole photo to level the
# shoulders before cutting him out: the photo runs on below the crop, so no slanted edge shows.
# make_avatar.py levels the rest of the head tilt on the neck. Negative = clockwise.
TILT, PIVOT = -6.0, (505, 240)   # degrees; the face centre in source pixels
# rough outline of the person in source pixels, clockwise from the top of the hair
OUTLINE = [(490, 26), (560, 38), (607, 90), (622, 150), (627, 185), (642, 200), (637, 270), (617, 300), (612, 325),
           (632, 315), (700, 355), (800, 385), (860, 410), (872, 450), (884, 560), (906, 700), (236, 700), (240, 600),
           (262, 480), (288, 440), (360, 410), (432, 372), (424, 345), (414, 310), (386, 272), (379, 225), (380, 130),
           (400, 70), (440, 34)]
S = 2                  # upscale

os.chdir(SAD)          # the face models are looked up in ./gfpgan/weights
sys.path.insert(0, str(SAD))
from gfpgan import GFPGANer
from facexlib.detection import init_detection_model
from facexlib.alignment import init_alignment_model

img = cv2.imread(str(SRC))

# 1. sharpen the face (the source face is only ~230 px wide) and upscale 2x
_, _, big = GFPGANer(model_path="gfpgan/weights/GFPGANv1.4.pth", upscale=S, arch="clean", channel_multiplier=2,
                     bg_upsampler=None).enhance(img, has_aligned=False, only_center_face=True, paste_back=True)

# 2. sit him up straight (the hand outline turns with the photo)
R = cv2.getRotationMatrix2D((PIVOT[0] * S, PIVOT[1] * S), TILT, 1.0)   # OpenCV: positive = counter-clockwise
big = cv2.warpAffine(big, R, big.shape[1::-1], flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
outline = cv2.transform(np.array([OUTLINE], np.float64) * S, R)[0]

# 3. cut him out: hand outline seeds GrabCut, which finds the exact edge
poly = np.zeros(big.shape[:2], np.uint8)
cv2.fillPoly(poly, [outline.astype(np.int32)], 1)
k = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r * S + 1,) * 2)
mask = np.where(poly == 1, cv2.GC_PR_FGD, cv2.GC_PR_BGD).astype(np.uint8)
mask[cv2.erode(poly, k(22)) == 1] = cv2.GC_FGD
mask[cv2.dilate(poly, k(16)) == 0] = cv2.GC_BGD
cv2.grabCut(big, mask, None, np.zeros((1, 65)), np.zeros((1, 65)), 6, cv2.GC_INIT_WITH_MASK)
alpha = np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8) * 255
alpha = cv2.GaussianBlur(cv2.erode(alpha, np.ones((3, 3), np.uint8)), (5, 5), 0)   # shave the fringe, soften

x, y, n = (c * S for c in CROP)
out = np.dstack([big, alpha])[y:y + n, x:x + n]
cv2.imwrite(str(ROOT / "pankaj2.png"), out)

# 4. face landmarks (WFLW 98 points)
face = out[..., :3].copy()
box = init_detection_model("retinaface_resnet50", half=False, model_rootpath="gfpgan/weights").detect_faces(face, 0.9)[0]
x0, y0, x1, y1 = box[:4]
m = 0.1 * max(x1 - x0, y1 - y0)
x0, y0, x1, y1 = (int(max(0, v)) for v in (x0 - m, y0 - m, x1 + m, y1 + m))
lm = init_alignment_model("awing_fan", model_rootpath="gfpgan/weights").get_landmarks(face[y0:y1, x0:x1]) + (x0, y0)
(ROOT / "pankaj2.json").write_text(json.dumps([[px / n, 1 - py / n] for px, py in lm.tolist()]))

if len(sys.argv) > 1:  # debug picture: python prep_photo.py check.png
    dbg = (face * (out[..., 3:] / 255) + 255 * (1 - out[..., 3:] / 255) * (0, 1, 0)).astype(np.uint8)
    for i, (px, py) in enumerate(lm):
        cv2.circle(dbg, (int(px), int(py)), 3, (0, 0, 255), -1)
    cv2.imwrite(sys.argv[1], dbg)
print("wrote pankaj2.png, pankaj2.json")
