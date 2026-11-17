"""Build the avatar in Blender from the prepared portrait (see prep_photo.py).
Run:  blender -b -P make_avatar.py -- pankaj2.png      (needs pankaj2.json beside it)
Writes avatar.blend (editable) and avatar.glb (what the web page loads).

What it builds:
  Avatar      cut-out portrait pushed into a head/nose/torso relief.
              The mesh is slit between the lips so the jaw really opens.
              Shape keys: jawOpen, blink.
  MouthInside dark plane behind the slit (what you see when the mouth opens).
  Background  blurred law-office bookshelf, set back so it shifts behind him as he moves.

ponytail: single-photo relief, fine for small head movements only.
"""
import bpy, bmesh, json, os, sys, tempfile
import numpy as np

photo = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
out = os.path.join(os.path.dirname(photo), "avatar")
tmp = tempfile.mkdtemp()
N = 280                                                                # grid cells per side

clip = np.clip
bpy.ops.wm.read_factory_settings(use_empty=True)


def save_image(name, arr):
    """float RGBA array (row 0 = bottom) -> packed Blender image."""
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.filepath_raw, img.file_format = os.path.join(tmp, name + ".png"), "PNG"
    img.save()
    return img


def material(name, img=None, color=(1, 1, 1, 1), alpha=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    if img:
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.extension = "EXTEND" if alpha else "REPEAT"   # cut-outs must not wrap: exported as clamp-to-edge
        mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha:
            mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    return mat


def quad(name, corners, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata(corners, [], [(0, 1, 2, 3)])
    me.uv_layers.new().data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ---------- 1. photo + landmarks (WFLW 98 points; u: left->right, v: bottom->top) ----------
cutout = bpy.data.images.load(photo)
W, H = cutout.size
px = np.empty(W * H * 4, np.float32)
cutout.pixels.foreach_get(px)
alpha = px.reshape(H, W, 4)[..., 3]
L = np.array(json.load(open(os.path.splitext(photo)[0] + ".json")))

CHIN_V = L[16, 1]
cu, fw = (L[0, 0] + L[32, 0]) / 2, (L[32, 0] - L[0, 0]) / 2            # face centre and half-width
top = np.nonzero(alpha[:, int(cu * W)] > 0.5)[0].max() / H              # top of the hair
HEAD = dict(cu=cu, cv=(top + CHIN_V) / 2, ru=fw * 1.45, rv=(top - CHIN_V) / 2 * 1.08)
DEPTH = 2 * HEAD["ru"]                                                 # as deep as it is wide: a round head
NOSE = L[54]
EYES = [(e[:, 0].mean(), e[:, 1].mean(), np.ptp(e[:, 0]) / 2, np.ptp(e[:, 1]) / 2 * 1.15) for e in (L[60:68], L[68:76])]
MOUTH_L, MOUTH_R = L[76], L[82]                                        # mouth corners
slit = L[[76, 88, 95, 94, 93, 92, 82]]                                 # corner, along the inner lower lip, corner
slit = slit[np.argsort(slit[:, 0])]
anchor_u, anchor_v = slit[:, 0], slit[:, 1]

def bound(u):  # height of the mouth slit at u (clamped outside the mouth)
    return np.interp(u, anchor_u, anchor_v)

CU, HW = (MOUTH_L[0] + MOUTH_R[0]) / 2, (MOUTH_R[0] - MOUTH_L[0]) / 2
JAW_DROP = 0.65 * (bound(CU) - CHIN_V)                                 # jaw travel (mesh units)

# ---------- 3. relief mesh ----------
g = np.arange(N + 1) / N
U, V = np.meshgrid(g, g)                  # vertex (i, j) -> index i*(N+1)+j, v=i/N, u=j/N
U, V = U.ravel(), V.ravel()

def depth_at(u, v):
    d = 1 - ((u - HEAD["cu"]) / HEAD["ru"]) ** 2 - ((v - HEAD["cv"]) / HEAD["rv"]) ** 2
    head = DEPTH * clip(d, 0, None) ** 0.7
    nose = 0.2 * DEPTH * np.exp(-(((u - NOSE[0]) / (0.2 * fw)) ** 2 + ((v - NOSE[1] - 0.17 * fw) / (0.4 * fw)) ** 2))
    torso = 0.18 * np.sqrt(clip(1 - ((u - HEAD["cu"]) / 0.6) ** 2, 0, None)) * clip((CHIN_V + 0.015 - v) / 0.15, 0, 1)
    return np.maximum(head, torso) + nose

verts = np.stack([2 * U - 1, -depth_at(U, V), 2 * V - 1], axis=1)
idx = lambda i, j: i * (N + 1) + j
faces = [(idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)) for i in range(N) for j in range(N)]
me = bpy.data.meshes.new("Avatar")
me.from_pydata(verts.tolist(), [], faces)

# slit the mesh along the teeth edge (staircase along grid edges)
r = np.rint(bound((np.arange(N) + 0.5) / N) * N).astype(int)      # slit row for each column of cells
jL, jR = int(np.ceil(MOUTH_L[0] * N)), int(np.floor(MOUTH_R[0] * N))
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
pairs = [(idx(r[j], j), idx(r[j], j + 1)) for j in range(jL, jR)]
for j in range(jL, jR - 1):
    a, b = sorted((r[j], r[j + 1]))
    pairs += [(idx(i, j + 1), idx(i + 1, j + 1)) for i in range(a, b)]
cut = [bm.edges.get((bm.verts[a], bm.verts[b])) for a, b in pairs]
bmesh.ops.split_edges(bm, edges=cut)
bm.verts.index_update(); bm.faces.index_update()
face_lower = [(f // N) < r[f % N] for f in range(N * N)]          # is this cell below the slit?
lower = np.array([all(face_lower[f.index] for f in v.link_faces) for v in bm.verts])
bm.to_mesh(me)
bm.free()
print(f"slit added {len(me.vertices) - (N + 1) ** 2} vertices")

co = np.empty(len(me.vertices) * 3, np.float32)
me.vertices.foreach_get("co", co)
co = co.reshape(-1, 3)
u, v = (co[:, 0] + 1) / 2, (co[:, 2] + 1) / 2   # = the photo position of each vertex (UVs below)

# Sit him up straight. prep_photo.py levelled his shoulders; turn the head on the neck, about the chin, by what is
# left of the tilt of his eye line. Only the shape moves: the photo stays pinned to u, v.
def head_mask(u, v):
    m = clip((v - (CHIN_V - 0.07)) / 0.07, 0, 1) * clip((1.2 - np.abs(u - HEAD["cu"]) / HEAD["ru"]) / 0.2, 0, 1)
    return m * m * (3 - 2 * m)                     # 1 on the head, easing to 0 down the neck and at the shoulders

px, pz = 2 * HEAD["cu"] - 1, 2 * CHIN_V - 1
le, re_ = np.mean(L[60:68], 0), np.mean(L[68:76], 0)
TILT = np.arctan2(re_[1] - le[1], re_[0] - le[0])   # radians, + = the viewer's-right eye sits higher
print(f"levelling head tilt of {np.degrees(TILT):.1f} degrees")

def level(x, z, u, v):
    a = -TILT * head_mask(u, v)
    dx, dz = x - px, z - pz
    return px + dx * np.cos(a) - dz * np.sin(a), pz + dx * np.sin(a) + dz * np.cos(a)

co[:, 0], co[:, 2] = level(co[:, 0], co[:, 2], u, v)
me.vertices.foreach_set("co", co.ravel())

vi = np.empty(len(me.loops), np.int32)
me.loops.foreach_get("vertex_index", vi)
me.uv_layers.new().data.foreach_set("uv", np.stack([u[vi], v[vi]], axis=1).ravel())
me.materials.append(material("Photo", cutout, alpha=True))
avatar = bpy.data.objects.new("Avatar", me)
bpy.context.scene.collection.objects.link(avatar)

# ---------- 4. shape keys ----------
avatar.shape_key_add(name="Basis")

# jawOpen: everything below the slit drops as one piece, widening toward the chin, fading into the neck
vb = bound(u)
deep = clip((vb - v) / (bound(CU) - CHIN_V), 0, 1)
across = clip(1 - ((u - CU) / (HW * (1 + 0.7 * deep))) ** 2, 0, None) ** 0.7
fade = np.where(v < CHIN_V, clip(1 - (CHIN_V - v) / 0.04, 0, 1), 1)
jaw = co.copy()
jaw[:, 2] -= JAW_DROP * lower * across * fade
avatar.shape_key_add(name="jawOpen").data.foreach_set("co", jaw.ravel())

# blink: squash each eye opening down onto the lower lid, upper-lid skin follows
dv = np.zeros_like(v)
for cu, cv, ru, rv in EYES:
    h = clip(1 - ((u - cu) / (ru * 1.2)) ** 2, 0, None) ** 0.5
    lo, hi = cv - rv, cv + rv
    lid = 1.5 * rv                                   # how far above the eye the skin stretches (stops short of the brow)
    inside, above = (v >= lo) & (v <= hi), (v > hi) & (v < hi + lid)
    dv -= np.where(inside, (v - lo) * h, 0) + np.where(above, (hi - lo) * h * (1 - (v - hi) / lid), 0)
blink = co.copy()
blink[:, 2] += 2 * dv
avatar.shape_key_add(name="blink").data.foreach_set("co", blink.ravel())

# mouthRound: lips drawn toward the centre, corners slightly down (o / u sounds, and it relaxes the photo's smile)
w = np.exp(-(((u - CU) / (1.5 * HW)) ** 2 + ((v - bound(CU) + 0.1 * HW) / (0.8 * HW)) ** 2))
rnd = co.copy()
rnd[:, 0] -= 0.7 * (u - CU) * w
rnd[:, 2] -= 0.3 * HW * w * clip(((u - CU) / HW) ** 2, 0, 1)
avatar.shape_key_add(name="mouthRound").data.foreach_set("co", rnd.ravel())

# browUp: both eyebrows lift (emphasis while speaking)
brow = co.copy()
for b in (L[33:42], L[42:51]):
    bu, bv, bw = b[:, 0].mean(), b[:, 1].mean(), np.ptp(b[:, 0]) / 2
    brow[:, 2] += 0.5 * bw * np.exp(-(((u - bu) / (1.3 * bw)) ** 2 + ((v - bv) / (0.6 * bw)) ** 2))
avatar.shape_key_add(name="browUp").data.foreach_set("co", brow.ravel())

# The head moves on the neck, separately from the shoulders. The page drives these from -1 to 1.
#   headYaw / headPitch shift each point in proportion to its depth, which is what a small real rotation does;
#   headRoll tips the head sideways about the chin.
hm = head_mask(u, v)
near = -co[:, 1]                                               # how far each point sticks out toward the camera
for name, dx, dz in (("headYaw", 0.12 * near, 0), ("headPitch", 0, 0.12 * near),
                     ("headRoll", -0.06 * (co[:, 2] - pz), 0.06 * (co[:, 0] - px))):
    k = co.copy()
    k[:, 0] += dx * hm
    k[:, 2] += dz * hm
    avatar.shape_key_add(name=name).data.foreach_set("co", k.ravel())

# lookX: the iris slides sideways inside each eye opening (-1 to 1), lids stay put
look = co.copy()
for cu_, cv_, ru_, rv_ in EYES:
    look[:, 0] += 0.6 * ru_ * clip(1 - ((u - cu_) / ru_) ** 2 - ((v - cv_) / rv_) ** 2, 0, 1)
avatar.shape_key_add(name="lookX").data.foreach_set("co", look.ravel())

# ---------- 5. inside of the mouth ----------
# a dark patch that follows the face surface a little behind it, so it only shows through the slit
A, B = 16, 10
pu, pv = np.meshgrid(np.linspace(MOUTH_L[0] - 0.2 * HW, MOUTH_R[0] + 0.2 * HW, A), np.linspace(anchor_v.min() - JAW_DROP * 0.75, max(MOUTH_L[1], MOUTH_R[1]) + 0.012, B))
pu, pv = pu.ravel(), pv.ravel()
pm = bpy.data.meshes.new("MouthInside")
mx, mz = level(2 * pu - 1, 2 * pv - 1, pu, pv)                    # follows the levelled head
pm.from_pydata(np.stack([mx, -(depth_at(pu, pv) - 0.10), mz], axis=1).tolist(), [],
               [(i * A + j, i * A + j + 1, (i + 1) * A + j + 1, (i + 1) * A + j) for i in range(B - 1) for j in range(A - 1)])
quv = [(jj / (A - 1), ii / (B - 1)) for i in range(B - 1) for j in range(A - 1) for ii, jj in ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))]
pm.uv_layers.new().data.foreach_set("uv", np.array(quv).ravel())
ty, tx = np.mgrid[0:40, 0:64]                                      # dark mouth with a soft tongue low in the middle
tongue = clip(1.3 - ((tx / 64 - 0.5) / 0.3) ** 2 - ((ty / 40 - 0.2) / 0.35) ** 2, 0, 1)[..., None]
inner = (0.05, 0.012, 0.012) + tongue * (0.17, 0.04, 0.05)
pm.materials.append(material("Mouth", save_image("mouth", np.dstack([inner, np.ones((40, 64))]))))
inside = bpy.data.objects.new("MouthInside", pm)
bpy.context.scene.collection.objects.link(inside)
inside.parent = avatar

# ---------- 6. background: blurred law-office bookshelf ----------
S, SHELVES, BOARD = 1024, 5, 16
rng = np.random.default_rng(11)
sets = [(0.60, 0.47, 0.30), (0.33, 0.08, 0.09), (0.09, 0.14, 0.27), (0.10, 0.22, 0.14), (0.20, 0.13, 0.09)]  # buff, burgundy, navy, green, brown
wall = np.empty((S, S, 3), np.float32)
wall[:] = (0.10, 0.075, 0.06)
sh = S // SHELVES
for s in range(SHELVES):
    y0, x = s * sh + BOARD, 12
    wall[s * sh:y0] = (0.23, 0.15, 0.10)                                   # shelf board
    while x < S - 40:
        colour, height = np.array(sets[rng.integers(len(sets))]), int(sh * rng.uniform(0.66, 0.84))
        for _ in range(rng.integers(4, 10)):                               # a run of matching volumes
            w = int(rng.integers(26, 40))
            if x + w > S - 12:
                break
            wall[y0:y0 + height, x:x + w - 3] = colour * rng.uniform(0.85, 1.1)   # plain spines: no bright bands
            x += w
        x += int(rng.integers(0, 50))                                      # gap between sets
def blur(a, k):
    """3 box blurs per axis ~ a gaussian; a is (rows, cols, channels)."""
    for axis in (0, 1):
        for _ in range(3):
            p = np.pad(a, [(k + 1, k) if i == axis else (0, 0) for i in range(3)], mode="edge")
            c = np.cumsum(p, axis=axis)
            n = a.shape[axis]
            a = (np.take(c, np.arange(2 * k + 1, 2 * k + 1 + n), axis=axis) - np.take(c, np.arange(n), axis=axis)) / (2 * k + 1)
    return a

wall = blur(wall, 18)                                                      # well out of focus behind him
wall = 0.65 * wall + 0.35 * wall.mean(axis=(0, 1))                         # lower contrast, so he stands out
yy, xx = np.mgrid[0:S, 0:S] / S
light = 0.7 + 0.6 * clip(1 - np.hypot(xx - 0.25, yy - 0.75), 0, 1)        # soft window light from upper left
wall = clip(wall * light[..., None] * 1.3, 0, 1)
backdrop = save_image("backdrop", np.dstack([wall, np.ones((S, S), np.float32)]))
quad("Background", [(-3, 1.6, -3), (3, 1.6, -3), (3, 1.6, 3), (-3, 1.6, 3)], material("Backdrop", backdrop))

# ---------- 6b. soft shadow on the wall behind him (light from the upper left) ----------
sil = blur(alpha[::4, ::4, None].astype(np.float32), 10)[..., 0]
shade = save_image("shadow", np.dstack([np.zeros(sil.shape + (3,), np.float32), 0.45 * sil]))
y, ox, oz = 0.45, 0.06, -0.05                                              # behind him, shifted right and down
shadow = quad("Shadow", [(-1 + ox, y, -1 + oz), (1 + ox, y, -1 + oz), (1 + ox, y, 1 + oz), (-1 + ox, y, 1 + oz)],
              material("ShadowMat", shade, alpha=True))
shadow.parent = avatar

# ---------- 7. save ----------
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=out + ".blend")
bpy.ops.export_scene.gltf(filepath=out + ".glb", export_format="GLB", export_morph=True)
print("wrote", out + ".blend", out + ".glb")
