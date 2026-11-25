"""Build every Aprende character with one command:  python characters/build.py [calavera pinata oso]
For each character: draw the art and its states (PIL), turn each state into an overlay (the pixels that differ from the
base art), pack base + overlays into one atlas, write <name>.json, run Blender (make_character.py), and copy the GLB, a
still image and the backdrop into aprende/public/characters/. Needs Pillow + numpy, and Blender (env BLENDER, default
Blender 5.3 on Windows when run from WSL). La Calavera's base art is avatar-intake/calavera.png, used unchanged.
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).parent
ROOT = HERE.parent
OUT = HERE / "out"
APP = ROOT / "aprende" / "public" / "characters"
BLENDER = os.environ.get("BLENDER", "/mnt/c/Program Files/Blender Foundation/Blender 5.3/blender.exe")
SIZE = 2048
sys.path.insert(0, str(HERE))


def win(p):
    """Windows Blender needs Windows paths when we run from WSL."""
    if BLENDER.endswith(".exe"):
        return subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True, check=True).stdout.strip()
    return str(p)


def diff_overlay(base, state, grow=6):
    """The state's pixels wherever it differs from the base (plus a small margin), transparent elsewhere."""
    a, b = np.asarray(base, np.int16), np.asarray(state, np.int16)
    mask = Image.fromarray((np.abs(a - b).max(-1) > 6).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(grow * 2 + 1))
    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    out.paste(state, (0, 0), mask)
    return out


def pack(base, overlays, pad=4):
    """Base art at the atlas origin, each overlay cropped to its content and stacked in columns to the right.
    -> atlas image, base rect, {key: (box in picture fractions, rect in atlas px)}"""
    crops = []
    for key, img in overlays.items():
        bb = img.getbbox()
        if not bb:
            raise SystemExit(f"overlay {key} is empty")
        crops.append((key, img.crop(bb), bb))
    cols, x, y, colw = [], SIZE + pad, 0, 0
    placed = {}
    for key, crop, bb in sorted(crops, key=lambda c: -c[1].height):
        if y + crop.height > SIZE:
            x, y, colw = x + colw + pad, 0, 0
        placed[key] = (crop, bb, (x, y))
        y += crop.height + pad
        colw = max(colw, crop.width)
    width = -(-(x + colw) // 4) * 4
    atlas = Image.new("RGBA", (width, SIZE), (0, 0, 0, 0))
    atlas.paste(base, (0, 0))
    info = {}
    for key, (crop, (x0, y0, x1, y1), (ax, ay)) in placed.items():
        atlas.paste(crop, (ax, ay))
        info[key] = ([x0 / SIZE, y0 / SIZE, x1 / SIZE, y1 / SIZE], [ax, ay, x1 - x0, y1 - y0])
    return atlas, [0, 0, SIZE, SIZE], info


def render(art):
    """charkit art (drawn at 2x) -> the 2048 px image the rig uses."""
    return art.img.resize((SIZE, SIZE), Image.LANCZOS)


def character_pinata():
    import pinata_art as P
    base = render(P.draw())
    states = {"celebrate": render(P.draw(blink=1.0))}
    return base, render(P.backdrop()), {k: diff_overlay(base, v) for k, v in states.items()}, P.rig(), {}


def character_oso():
    import oso_art as O
    base = render(O.draw())
    states = {"celebrate": render(O.draw(blink=1.0)), "comfort": render(O.draw(blink=1.0, hug=True))}
    return base, render(O.backdrop()), {k: diff_overlay(base, v) for k, v in states.items()}, O.rig(), {}


def character_calavera():
    import calavera_states as S
    base = Image.open(ROOT / "avatar-intake" / "calavera.png").convert("RGBA")
    bg = Image.open(ROOT / "avatar-intake" / "calavera-bg.png").convert("RGB")
    rig = json.load(open(ROOT / "avatar-intake" / "calavera.json"))
    layers = S.layers()                                  # transparent 2048 layers drawn over the unchanged base
    return base, bg, layers, rig, S.SWING


# The theme hosts (one per Memento Mori theme; La Calavera hosts Día de Muertos). Each art module has draw(jaw, blink,
# look, **state), rig(), CELEBRATE / COMFORT state kwargs, FACE (the head's box, fractions of the picture) and THEME.
HOSTS = {"girasol": "girasol_art", "colibri": "colibri_art", "velita": "velita_art", "tortuga": "tortuga_art"}


def character_host(name):
    import importlib
    A = importlib.import_module(HOSTS[name])
    base = render(A.draw())
    states = {"celebrate": render(A.draw(**A.CELEBRATE)), "comfort": render(A.draw(**A.COMFORT))}
    bg = Image.open(APP / "backdrops" / f"{A.THEME}.jpg").convert("RGB")        # the theme's own backdrop
    return base, bg, {k: diff_overlay(base, v) for k, v in states.items()}, A.rig(), {}


BUILD = {"calavera": character_calavera, "pinata": character_pinata, "oso": character_oso,
         **{n: (lambda n=n: character_host(n)) for n in HOSTS}}


def build(name):
    base, bg, overlays, rig, swing = BUILD[name]()
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    atlas, base_rect, info = pack(base, overlays)
    atlas.save(d / f"{name}-atlas.png", optimize=True)
    bg.resize((1024, 1024), Image.LANCZOS).save(d / f"{name}-bg.jpg", quality=86)
    spec = {"atlas": {"image": f"{name}-atlas.png", "size": list(atlas.size), "base": base_rect},
            "parts": rig, "background": f"{name}-bg.jpg", "grid": 140,
            "overlays": [dict(key=k, box=box, rect=rect, **({"swing": swing[k]} if k in swing else {}))
                         for k, (box, rect) in info.items()]}
    (d / f"{name}.json").write_text(json.dumps(spec, indent=1))
    r = subprocess.run([BLENDER, "-b", "-P", win(HERE / "make_character.py"), "--", win(d), name], capture_output=True, text=True)
    if r.returncode or not (d / f"{name}.glb").exists():
        raise SystemExit(f"Blender failed for {name}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    print(next((l for l in r.stdout.splitlines() if l.startswith("wrote")), ""))
    APP.mkdir(parents=True, exist_ok=True)
    shutil.copy(d / f"{name}.glb", APP / f"{name}.glb")
    base.resize((1024, 1024), Image.LANCZOS).save(APP / f"{name}.png", optimize=True)      # still image (no WebGL)
    shutil.copy(d / f"{name}-bg.jpg", APP / f"{name}-bg.jpg")
    if name in HOSTS:                                                                        # the face on the map and the welcome
        import importlib
        x0, y0, x1, y1 = importlib.import_module(HOSTS[name]).FACE
        scene = bg.resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA")                     # on its backdrop, like the others
        scene.alpha_composite(base)
        face = scene.crop((int(x0 * SIZE), int(y0 * SIZE), int(x1 * SIZE), int(y1 * SIZE))).resize((240, 240), Image.LANCZOS)
        face.convert("RGB").save(ROOT / "aprende" / "public" / "img" / f"{name}-face.png", optimize=True)
    for label, img in overlays.items():                                                     # previews for review
        prev = base.copy(); prev.alpha_composite(img)
        prev.resize((512, 512), Image.LANCZOS).save(d / f"preview-{label}.png")


if __name__ == "__main__":
    for n in sys.argv[1:] or list(BUILD):
        build(n)
