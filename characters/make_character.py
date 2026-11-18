"""Build one character's rigged 2D sheet in Blender, for every Aprende character (generalises avatar-intake/make_calavera.py).
Run:  blender -b -P make_character.py -- <dir> <name>
Reads <dir>/<name>.json (written by build.py): the atlas image, where the moving parts are, and the state overlays.
Writes <dir>/<name>.blend (editable) and <dir>/<name>.glb (what the app loads).

Shape keys, the same for every character so one engine drives them all:
  jawOpen mouthRound blink browUp lookX headYaw headPitch headRoll   (the prototype's eight, same formulas as make_calavera.py)
  think          the pupils glance up and aside, the brows lift
  <overlay>      one per state overlay (celebrate, comfort, wave, glasses, ...): a piece of art folded to a point in the
                 basis that opens to full size; the head keys move it too, so it turns with the head
  <overlay>Swing a rotation of that overlay about a pivot (a waving hand), when the overlay asks for it
Lighter than the prototype's sheet: cells that are fully transparent are dropped, morph targets are exported sparse,
no normals (the material is unlit), and the backdrop is a JPEG.
"""
import bpy, json, math, os, sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
here, name = argv[0], argv[1]
C = json.load(open(os.path.join(here, name + ".json")))
L = C["parts"]
N = C.get("grid", 180)                                   # cells per side of the character sheet
W, DROP = 2.0, 0.07                                       # world width of the sheet; it sits a little low (as make_calavera.py)
AW, AH = C["atlas"]["size"]
clip = np.clip
smooth = lambda m: (lambda c: c * c * (3 - 2 * c))(clip(m, 0, 1))
bpy.ops.wm.read_factory_settings(use_empty=True)


def material(mname, path, alpha):
    mat = bpy.data.materials.new(mname)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    tex.extension = "EXTEND"
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha:
        mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    return mat, tex.image


atlas_mat, atlas_img = material("Character", os.path.join(here, C["atlas"]["image"]), True)
px = np.array(atlas_img.pixels[:], dtype=np.float32).reshape(AH, AW, 4)[::-1]   # rows from the top
alpha = px[..., 3]
bx, by, bw, bh = C["atlas"]["base"]                     # where the character sheet sits in the atlas, in pixels

# ---------- geometry: the sheet, then each overlay; u, v are picture fractions (v from the top) ----------
verts_uv, uvs, faces, part_of = [], [], [], []           # part_of: -1 for the sheet, else the overlay index


def grid(u0, v0, u1, v1, n, m, rect, part, keep_cell):
    """A grid of n x m cells over picture area (u0, v0)-(u1, v1), textured from atlas rect (x, y, w, h)."""
    base = len(verts_uv)
    rx, ry, rw, rh = rect
    for r in range(m + 1):
        for c in range(n + 1):
            fu, fv = c / n, r / m
            verts_uv.append((u0 + (u1 - u0) * fu, v0 + (v1 - v0) * fv))
            uvs.append(((rx + rw * fu) / AW, 1 - (ry + rh * fv) / AH))
            part_of.append(part)
    for r in range(m):
        for c in range(n):
            if keep_cell(r, c):
                i = base + r * (n + 1) + c
                faces.append((i, i + 1, i + n + 2, i + n + 1))


def opaque(rect, n, m, pad=1):
    """Cells of rect that contain (or border) any visible pixel."""
    rx, ry, rw, rh = rect
    a = alpha[ry:ry + rh, rx:rx + rw]
    ch, cw = rh / m, rw / n
    cell = np.zeros((m, n), bool)
    for r in range(m):
        for c in range(n):
            cell[r, c] = a[int(r * ch):int((r + 1) * ch) + 1, int(c * cw):int((c + 1) * cw) + 1].max() > 0.004
    k = cell.copy()
    for dr in range(-pad, pad + 1):                       # keep a ring of empty cells, so edges move smoothly
        for dc in range(-pad, pad + 1):
            k |= np.roll(np.roll(cell, dr, 0), dc, 1)
    return lambda r, c: k[r, c]


grid(0, 0, 1, 1, N, N, (bx, by, bw, bh), -1, opaque((bx, by, bw, bh), N, N))
overlays = C.get("overlays", [])
for k, ov in enumerate(overlays):
    u0, v0, u1, v1 = ov["box"]
    n = max(2, round((u1 - u0) * N)); m = max(2, round((v1 - v0) * N))
    grid(u0, v0, u1, v1, n, m, ov["rect"], k, opaque(ov["rect"], n, m))

uv_ = np.array(verts_uv); u, vt = uv_[:, 0], uv_[:, 1]
part = np.array(part_of)
full = np.stack([W * u - W / 2, np.zeros_like(u), 1 - 2 * vt - DROP], 1)   # where every vertex is when shown
full[part >= 0, 1] = -0.002                                                 # overlays sit just in front of the sheet
co = full.copy()
for k, ov in enumerate(overlays):                                           # basis: each overlay folded to its centre
    sel = part == k
    co[sel] = full[sel].mean(0)

# drop vertices no face uses
used = np.zeros(len(co), bool); used[np.array(faces).ravel()] = True
remap = -np.ones(len(co), int); remap[used] = np.arange(used.sum())
faces = [tuple(remap[i] for i in f) for f in faces]
co, full, u, vt, part = co[used], full[used], u[used], vt[used], part[used]
uvs = [uv for uv, keep in zip(uvs, used) if keep]

me = bpy.data.meshes.new("Avatar")
me.from_pydata(co.tolist(), [], faces)
me.uv_layers.new().data.foreach_set("uv", np.array([uvs[v] for f in faces for v in f]).ravel())
me.materials.append(atlas_mat)
avatar = bpy.data.objects.new("Avatar", me)
bpy.context.scene.collection.objects.link(avatar)
avatar.shape_key_add(name="Basis")


def key(kname, dx=0.0, dz=0.0, absolute=None):
    k = co.copy() if absolute is None else absolute.copy()
    k[:, 0] += dx
    k[:, 2] += dz
    kb = avatar.shape_key_add(name=kname)
    kb.data.foreach_set("co", k.ravel())
    kb.value = 0.0                                        # exported as the default weight: every key starts off


# ---------- the prototype's eight keys (formulas from make_calavera.py), computed where each vertex is shown ----------
b0, b1 = L["band"]
jx0, jx1, _, jy1 = L["jaw"]
drop, fade = L.get("jawDrop", 0.07), L.get("jawFade", 0.035)
inx = smooth((np.minimum(u - (jx0 - 0.04), (jx1 + 0.04) - u)) / 0.02)
jaw = clip((vt - b0) / (b1 - b0), 0, 1) * (1 - smooth((vt - jy1) / fade)) * inx
key("jawOpen", dz=-drop * jaw)

(rx, ry), dzb = L["socket"], np.zeros_like(u)
for ex, ey in L["eyes"]:
    r = np.hypot((u - ex) / (rx * 1.45), (vt - ey) / (ry * 1.45))
    m = 1 - smooth((r - 0.75) / 0.5)
    dzb += 2 * (vt - ey) * 0.9 * m
key("blink", dz=dzb)
key("mouthRound", dx=-(u - 0.5) * W * 0.18 * jaw, dz=-0.02 * jaw)

brow = sum(1 - smooth((np.hypot((u - bx_) / 0.09, (vt - by_) / 0.05) - 0.6) / 0.6) for bx_, by_ in L["brows"])
key("browUp", dz=0.03 * brow)
pupil = sum(1 - smooth((np.hypot(u - ex, vt - ey) - L["pupil"] * 1.1) / (L["pupil"] * 1.2)) for ex, ey in L["eyes"])
key("lookX", dx=0.035 * pupil)

n0, n1 = L["neck"]
hm = 1 - smooth((vt - n0) / (n1 - n0))
px_, pz = 0.0, 1 - 2 * (n0 + n1) / 2 - DROP
key("headYaw", dx=hm * (0.05 - 0.04 * (full[:, 0] - px_)))
key("headPitch", dz=hm * (-0.03 - 0.03 * (full[:, 2] - pz)))
a = np.radians(5) * hm
dx, dz = full[:, 0] - px_, full[:, 2] - pz
key("headRoll", dx=px_ + dx * np.cos(a) - dz * np.sin(a) - full[:, 0], dz=pz + dx * np.sin(a) + dz * np.cos(a) - full[:, 2])
key("think", dx=-0.025 * pupil, dz=0.022 * pupil + 0.02 * brow)

# ---------- one key per overlay: it opens to full size; optional swing about a pivot ----------
for k, ov in enumerate(overlays):
    sel = (part == k)
    opened = co.copy(); opened[sel] = full[sel]
    key(ov["key"], absolute=opened)
    if "swing" in ov:
        (sx, sy), deg = ov["swing"]["pivot"], ov["swing"]["deg"]
        cx, cz = W * sx - W / 2, 1 - 2 * sy - DROP
        a = np.radians(deg)
        d_x, d_z = full[:, 0] - cx, full[:, 2] - cz
        sw = co.copy()
        sw[sel, 0] = co[sel, 0] + (cx + d_x[sel] * np.cos(a) - d_z[sel] * np.sin(a) - full[sel, 0])
        sw[sel, 2] = co[sel, 2] + (cz + d_x[sel] * np.sin(a) + d_z[sel] * np.cos(a) - full[sel, 2])
        kb = avatar.shape_key_add(name=ov["key"] + "Swing")
        kb.data.foreach_set("co", sw.ravel())
        kb.value = 0.0

# ---------- the backdrop: fills the view, set back so it shifts slightly as the character moves ----------
if C.get("background"):
    bme = bpy.data.meshes.new("Background")
    s = 1.5
    bme.from_pydata([(-s, 1.6, -s), (s, 1.6, -s), (s, 1.6, s), (-s, 1.6, s)], [], [(0, 1, 2, 3)])
    bme.uv_layers.new().data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    bme.materials.append(material("Backdrop", os.path.join(here, C["background"]), False)[0])
    bpy.context.scene.collection.objects.link(bpy.data.objects.new("Background", bme))

out = os.path.join(here, name)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=out + ".blend")
bpy.ops.export_scene.gltf(filepath=out + ".glb", export_format="GLB", export_morph=True, export_morph_normal=False,
                          export_normals=False, export_try_sparse_sk=True, export_image_format="WEBP", export_image_quality=90)
print("wrote", out + ".glb", "vertices", len(co), "faces", len(faces), "keys", len(avatar.data.shape_keys.key_blocks) - 1)
