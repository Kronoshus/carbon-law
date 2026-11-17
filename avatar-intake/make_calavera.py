"""Build the 2D calavera avatar in Blender from the flat artwork (see calavera_art.py).
Run:  blender -b -P make_calavera.py           (needs calavera.png, calavera-bg.png, calavera.json beside it)
Writes calavera.blend (editable) and calavera.glb (what the page loads with ?avatar=calavera).

A flat, finely divided sheet carrying the artwork, with the same shape keys as the Pankaj avatar, so the page
animates it the same way:
  jawOpen     the lower jaw drops; the dark gap between the teeth stretches into the open mouth
  blink       the eye sockets squash shut
  mouthRound  the jaw narrows (for o / u)
  browUp      the dotted brows lift
  headYaw/Pitch/Roll  the skull turns, nods and tilts on the neck; the suit stays put
  lookX       the glowing pupils move sideways inside the dark sockets
"""
import bpy, json, os
import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(here, "calavera.json")))
N = 320                                                    # grid cells per side
clip = np.clip
bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, path, alpha):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    tex.extension = "EXTEND"
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha:
        mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    return mat


# ---------- the sheet ----------
i = np.arange(N + 1) / N
u, vt = [a.ravel() for a in np.meshgrid(i, i)]             # u across, vt down from the top of the artwork
DROP = 0.07                                                # sits a little low, so the whole sombrero is in view
co = np.stack([2 * u - 1, np.zeros_like(u), 1 - 2 * vt - DROP], 1)
faces = [(r * (N + 1) + c, r * (N + 1) + c + 1, (r + 1) * (N + 1) + c + 1, (r + 1) * (N + 1) + c)
         for r in range(N) for c in range(N)]
me = bpy.data.meshes.new("Avatar")
me.from_pydata(co.tolist(), [], faces)
uv = np.stack([u, 1 - vt], 1)
me.uv_layers.new().data.foreach_set("uv", uv[[v for f in faces for v in f]].ravel())
me.materials.append(material("Calavera", os.path.join(here, "calavera.png"), True))
avatar = bpy.data.objects.new("Avatar", me)
bpy.context.scene.collection.objects.link(avatar)

smooth = lambda m: (lambda c: c * c * (3 - 2 * c))(clip(m, 0, 1))
W = 2.0                                                    # world units per image width
avatar.shape_key_add(name="Basis")


def key(name, dx=0.0, dz=0.0):
    k = co.copy()
    k[:, 0] += dx
    k[:, 2] += dz
    avatar.shape_key_add(name=name).data.foreach_set("co", k.ravel())


# jaw: everything below the tooth gap moves down; the gap itself stretches; it fades out down the neck
b0, b1 = L["band"]
jx0, jx1, _, jy1 = L["jaw"]
inx = smooth((np.minimum(u - (jx0 - 0.04), (jx1 + 0.04) - u)) / 0.02)
jaw = clip((vt - b0) / (b1 - b0), 0, 1) * (1 - smooth((vt - jy1) / 0.035)) * inx
key("jawOpen", dz=-0.07 * jaw)

# blink: each socket (and its petals) squashes to a line through its centre
(rx, ry), dzb = L["socket"], np.zeros_like(u)
for ex, ey in L["eyes"]:
    r = np.hypot((u - ex) / (rx * 1.45), (vt - ey) / (ry * 1.45))
    m = 1 - smooth((r - 0.75) / 0.5)
    dzb += 2 * (vt - ey) * 0.9 * m                     # toward the eye line: z' = z - (z - ez) * 0.9 * m
key("blink", dz=dzb)

# mouthRound: the jaw narrows toward the middle and drops a little
key("mouthRound", dx=-(u - 0.5) * W * 0.18 * jaw, dz=-0.02 * jaw)

# browUp: the dotted arcs above the eyes lift
m = sum(1 - smooth((np.hypot((u - bx) / 0.09, (vt - by) / 0.05) - 0.6) / 0.6) for bx, by in L["brows"])
key("browUp", dz=0.03 * m)

# lookX: the pupils slide sideways; only the plain dark socket around them stretches
m = sum(1 - smooth((np.hypot(u - ex, vt - ey) - L["pupil"] * 1.1) / (L["pupil"] * 1.2)) for ex, ey in L["eyes"])
key("lookX", dx=0.035 * m)

# the head on the neck: full above neck[0], none below neck[1] (the suit stays still)
n0, n1 = L["neck"]
hm = 1 - smooth((vt - n0) / (n1 - n0))
px, pz = 0.0, 1 - 2 * (n0 + n1) / 2 - DROP                        # pivot: the middle of the neck
key("headYaw", dx=hm * (0.05 - 0.04 * (co[:, 0] - px)))    # slides and narrows a little, as if turning
key("headPitch", dz=hm * (-0.03 - 0.03 * (co[:, 2] - pz)))
a = np.radians(5) * hm
dx, dz = co[:, 0] - px, co[:, 2] - pz
key("headRoll", dx=px + dx * np.cos(a) - dz * np.sin(a) - co[:, 0], dz=pz + dx * np.sin(a) + dz * np.cos(a) - co[:, 2])

# ---------- the backdrop: fills the view, set back so it shifts slightly as he moves ----------
bme = bpy.data.meshes.new("Background")
s = 1.5
bme.from_pydata([(-s, 1.6, -s), (s, 1.6, -s), (s, 1.6, s), (-s, 1.6, s)], [], [(0, 1, 2, 3)])
bme.uv_layers.new().data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
bme.materials.append(material("Backdrop", os.path.join(here, "calavera-bg.png"), False))
bpy.context.scene.collection.objects.link(bpy.data.objects.new("Background", bme))

# ---------- save ----------
out = os.path.join(here, "calavera")
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=out + ".blend")
bpy.ops.export_scene.gltf(filepath=out + ".glb", export_format="GLB", export_morph=True)
print("wrote", out + ".blend", out + ".glb")
