"""Jungle plant kit for Mapa 02 Selva Esmeralda (Docs/PISTA_SELVA_ESMERALDA.md, section 6): our own trees, palms and
shrubs, built in Blender from code (no third-party assets), with the leaf textures painted by numpy. Nothing here has
collision in the game (as in the desert). Used by Scripts/selva/sculpt_selva.py; export_kit() writes FBX + textures.

The kinds, in the scatter's order (KINDS):
  kapok        sumaúma: emergent 45-58 m, buttress roots (sapopemas), flat umbrella crown on long branches
  canopy_a..c  canopy trees 22-34 m, rounded crowns of leaf-card clusters
  acai         açaí clump: 3-6 thin stems 12-20 m with arching feathery fronds (river banks, flooded forest)
  buriti       buriti palm: thick stem ~20 m, crown of fan leaves (flooded ground)
  cecropia     embaúba: white trunk, candelabra branches, umbrella leaves (road and river edges)
  shrub_a, b   understory 2-5 m
  far_a..c     the canopy trees as opaque blobs (the same shapes, far from the road: fast to render)
  far_kapok    the kapok as blobs
"""
import math
import os

import bpy
import bmesh
import numpy as np

KINDS = ["kapok", "canopy_a", "canopy_b", "canopy_c", "acai", "buriti", "cecropia", "shrub_a", "shrub_b",
         "far_a", "far_b", "far_c", "far_kapok", "stone_a", "stone_b", "branch", "fern"]
# The last four lie on the road (jogador, 2026-11-02: "galhos, arbustos pequenos, pedras no meio da estrada; não podem
# atrapalhar, as naves passam por cima"): all under 0.6 m, no collision.
FOG = dict(color=(0.60, 0.69, 0.74), strength=1.0, dist=2600.0, start=90.0, amount=0.88)


# ---------------------------------------------------------------------------------------------------- 1. textures
def _canvas(w, h, fill):
    rgb = np.empty((h, w, 3), np.float32)
    rgb[:] = fill
    return rgb, np.zeros((h, w), np.float32)


def _leaf(rgb, a, cx, cy, ang, L, W, col, tip=0.75, rib=True, veins=True):
    """One leaf from (cx, cy) along ang (pixels, y down): pointed, lighter along the midrib, darker at the edge."""
    H_, W_ = a.shape
    r = L + W
    x0, x1, y0, y1 = int(max(0, cx - r)), int(min(W_, cx + r)), int(max(0, cy - r)), int(min(H_, cy + r))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    c, s = math.cos(ang), math.sin(ang)
    u = (xx - cx) * c + (yy - cy) * s
    v = -(xx - cx) * s + (yy - cy) * c
    t = np.clip(u / L, 0.0, 1.0)
    half = 0.5 * W * np.clip(np.sin(np.pi * t), 0.0, 1.0) ** tip * (1.0 - 0.3 * t)
    inside = (u > 0) & (u < L) & (np.abs(v) < half)
    if not inside.any():
        return
    q = np.abs(v) / np.maximum(half, 1e-3)
    k = 0.80 + 0.26 * (1.0 - q) - 0.14 * t
    if veins:
        k = k + 0.07 * (np.sin(u * 0.16 + np.abs(v) * 0.32) > 0.92)
    if rib:
        k = k + 0.14 * (np.abs(v) < max(1.0, W * 0.025))
    k = k - 0.10 * (q > 0.88)
    sub, suba = rgb[y0:y1, x0:x1], a[y0:y1, x0:x1]
    sub[:] = np.where(inside[..., None], np.clip(np.asarray(col, np.float32)[None, None] * k[..., None], 0, 1), sub)
    suba[:] = np.where(inside, 1.0, suba)


def _stick(rgb, a, p0, p1, w, col):
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    _leaf(rgb, a, p0[0], p0[1], math.atan2(p1[1] - p0[1], p1[0] - p0[0]), L, w, col, tip=0.05, rib=False, veins=False)


def _save(name, rgb, a, folder):
    h, w = a.shape
    rgba = np.concatenate([rgb, a[..., None]], -1)
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.flipud(rgba).astype(np.float32).ravel())
    path = os.path.join(folder, name + ".png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return path


GREENS = [(0.17, 0.30, 0.10), (0.22, 0.38, 0.12), (0.28, 0.44, 0.14), (0.14, 0.26, 0.09), (0.33, 0.46, 0.15),
          (0.24, 0.34, 0.11)]


def make_textures(folder, seed=7):
    """Leaf cards (sRGB colour, straight alpha). Transparent pixels carry the mean leaf colour (no dark fringes)."""
    os.makedirs(folder, exist_ok=True)
    rng = np.random.default_rng(seed)
    out = {}
    # broad tropical leaves on a twig (canopy trees, shrubs)
    rgb, a = _canvas(1024, 1024, (0.22, 0.35, 0.12))
    _stick(rgb, a, (512, 1010), (520, 140), 9, (0.30, 0.24, 0.15))
    for k in range(18):
        t = k / 17
        y = 960 - 800 * t
        side = 1 if k % 2 else -1
        ang = -math.pi / 2 + side * rng.uniform(0.55, 1.15) + rng.normal(0, 0.08)
        L = rng.uniform(250, 330) * (1.0 - 0.35 * t)
        _stick(rgb, a, (516, y), (516 + side * 18, y - 10), 5, (0.30, 0.24, 0.15))
        _leaf(rgb, a, 516 + side * 14, y - 8, ang, L, L * rng.uniform(0.30, 0.38), GREENS[rng.integers(len(GREENS))])
    out["leaf_broad"] = _save("T_Leaf_Broad", rgb, a, folder)
    # small leaves in a round cluster (kapok crowns, far shrubs)
    rgb, a = _canvas(1024, 1024, (0.24, 0.37, 0.12))
    for k in range(5):
        _stick(rgb, a, (512, 1000), (512 + rng.uniform(-380, 380), rng.uniform(120, 520)), 6, (0.30, 0.25, 0.16))
    for k in range(95):
        r = 430 * math.sqrt(rng.uniform(0.02, 1.0))
        th = rng.uniform(0, 2 * math.pi)
        cx, cy = 512 + r * math.cos(th), 520 + r * math.sin(th) * 0.95
        L = rng.uniform(95, 140)
        _leaf(rgb, a, cx, cy, th + rng.normal(0, 0.5), L, L * 0.42, GREENS[rng.integers(len(GREENS))])
    out["leaf_small"] = _save("T_Leaf_Small", rgb, a, folder)
    # pinnate frond (açaí): rachis up the middle, long thin leaflets hanging forward
    rgb, a = _canvas(512, 1024, (0.22, 0.36, 0.12))
    _stick(rgb, a, (256, 1020), (256, 10), 7, (0.36, 0.40, 0.18))
    for k in range(70):
        t = k / 69
        y = 1000 - 980 * t
        for side in (-1, 1):
            L = (215 - 120 * t) * rng.uniform(0.9, 1.05)
            ang = -math.pi / 2 + side * rng.uniform(1.0, 1.25)
            _leaf(rgb, a, 256, y, ang, L, 16 - 6 * t, GREENS[rng.integers(len(GREENS))], tip=0.5, veins=False)
    out["frond"] = _save("T_Frond", rgb, a, folder)
    # fan leaf (buriti): segments radiating from the petiole
    rgb, a = _canvas(1024, 1024, (0.25, 0.38, 0.13))
    _stick(rgb, a, (512, 1023), (512, 900), 14, (0.36, 0.38, 0.18))
    for k in range(44):
        ang = -math.pi / 2 + (k / 43 - 0.5) * math.radians(170) + rng.normal(0, 0.02)
        L = rng.uniform(780, 880)
        _leaf(rgb, a, 512, 905, ang, L, 34, GREENS[rng.integers(len(GREENS))], tip=0.35, veins=False)
    out["fan"] = _save("T_Fan", rgb, a, folder)
    # palmate umbrella leaves (embaúba), seen from above: silvery green lobes round a centre
    rgb, a = _canvas(512, 512, (0.38, 0.47, 0.30))
    for k in range(9):
        ang = 2 * math.pi * k / 9 + rng.normal(0, 0.05)
        _leaf(rgb, a, 256, 256, ang, rng.uniform(205, 245), 92, (0.40, 0.50, 0.30), tip=0.6)
    out["cecropia"] = _save("T_Cecropia", rgb, a, folder)
    return out


# ---------------------------------------------------------------------------------------------------- 2. materials
def fog_group():
    """Aerial perspective, cheap: the surface fades to the humid haze with distance from the camera."""
    ng = bpy.data.node_groups.get("EXFog")
    if ng is None:
        ng = bpy.data.node_groups.new("EXFog", "ShaderNodeTree")
        ng.interface.new_socket("Shader", in_out="INPUT", socket_type="NodeSocketShader")
        ng.interface.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
        n, l_ = ng.nodes, ng.links
        gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
        cam = n.new("ShaderNodeCameraData")
        sub = n.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.name = "start"
        mx = n.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; mx.inputs[1].default_value = 0.0
        div = n.new("ShaderNodeMath"); div.operation = "DIVIDE"; div.name = "dist"
        ex = n.new("ShaderNodeMath"); ex.operation = "EXPONENT"
        one = n.new("ShaderNodeMath"); one.operation = "SUBTRACT"; one.inputs[0].default_value = 1.0
        amt = n.new("ShaderNodeMath"); amt.operation = "MULTIPLY"; amt.name = "amount"
        em = n.new("ShaderNodeEmission"); em.name = "haze"
        mix = n.new("ShaderNodeMixShader")
        l_.new(cam.outputs["View Distance"], sub.inputs[0])
        l_.new(sub.outputs[0], mx.inputs[0])
        l_.new(mx.outputs[0], div.inputs[0])
        l_.new(div.outputs[0], ex.inputs[0])
        l_.new(ex.outputs[0], one.inputs[1])
        l_.new(one.outputs[0], amt.inputs[0])
        l_.new(amt.outputs[0], mix.inputs[0])
        l_.new(gi.outputs[0], mix.inputs[1])
        l_.new(em.outputs[0], mix.inputs[2])
        l_.new(mix.outputs[0], go.inputs[0])
    n = ng.nodes
    n["start"].inputs[1].default_value = FOG["start"]
    n["dist"].inputs[1].default_value = -FOG["dist"]
    n["amount"].inputs[1].default_value = FOG["amount"]
    n["haze"].inputs["Color"].default_value = (*FOG["color"], 1.0)
    n["haze"].inputs["Strength"].default_value = FOG["strength"]
    return ng


def finish(mat, surface, alpha=None):
    """surface -> haze -> (cut out by alpha) -> output."""
    nt = mat.node_tree
    for nd in [nd for nd in nt.nodes if nd.type == "OUTPUT_MATERIAL"]:
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    fg = nt.nodes.new("ShaderNodeGroup")
    fg.node_tree = fog_group()
    nt.links.new(surface, fg.inputs[0])
    if alpha is None:
        nt.links.new(fg.outputs[0], out.inputs["Surface"])
        return
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(alpha, mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(fg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def _new_mat(name):
    m = bpy.data.materials.get(name)
    if m is not None:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    for nd in list(m.node_tree.nodes):
        m.node_tree.nodes.remove(nd)
    return m


def _tint(nt, lo, hi):
    """Per-instance colour (Object Info random): each tree its own green."""
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*lo, 1.0)
    ramp.color_ramp.elements[1].color = (*hi, 1.0)
    nt.links.new(oi.outputs["Random"], ramp.inputs[0])
    return ramp.outputs[0]


def leaf_material(name, path, lo=(0.75, 0.82, 0.62), hi=(1.25, 1.18, 0.92), translucency=0.35, rough=0.5):
    m = _new_mat(name)
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.interpolation = "Linear"
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs["Color"], mul.inputs[6])
    nt.links.new(_tint(nt, lo, hi), mul.inputs[7])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(mul.outputs[2], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = rough
    tl = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(mul.outputs[2], tl.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = translucency
    nt.links.new(bs.outputs[0], mix.inputs[1])
    nt.links.new(tl.outputs[0], mix.inputs[2])
    finish(m, mix.outputs[0], tex.outputs["Alpha"])
    return m


def bark_material(name, c0, c1, scale=2.5, rings=False, moss=0.0):
    m = _new_mat(name)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c0, 1)
    ramp.color_ramp.elements[1].color = (*c1, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs[0])
    col = ramp.outputs[0]
    if rings:   # embaúba: pale rings round the white stem
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        wave = nt.nodes.new("ShaderNodeMath"); wave.operation = "SINE"
        sc = nt.nodes.new("ShaderNodeMath"); sc.operation = "MULTIPLY"; sc.inputs[1].default_value = 9.0
        nt.links.new(sep.outputs["Z"], sc.inputs[0])
        nt.links.new(sc.outputs[0], wave.inputs[0])
        mixr = nt.nodes.new("ShaderNodeMix"); mixr.data_type = "RGBA"; mixr.blend_type = "DARKEN"
        gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.93
        nt.links.new(wave.outputs[0], gt.inputs[0])
        nt.links.new(gt.outputs[0], mixr.inputs[0])
        nt.links.new(col, mixr.inputs[6])
        mixr.inputs[7].default_value = (0.35, 0.33, 0.28, 1)
        col = mixr.outputs[2]
    if moss > 0:   # moss on what faces up
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], sep.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs[1].default_value, mr.inputs[2].default_value = 0.2, 0.75
        nt.links.new(sep.outputs["Z"], mr.inputs[0])
        mm = nt.nodes.new("ShaderNodeMath"); mm.operation = "MULTIPLY"; mm.inputs[1].default_value = moss
        nt.links.new(mr.outputs[0], mm.inputs[0])
        mixm = nt.nodes.new("ShaderNodeMix"); mixm.data_type = "RGBA"
        nt.links.new(mm.outputs[0], mixm.inputs[0])
        nt.links.new(col, mixm.inputs[6])
        mixm.inputs[7].default_value = (0.10, 0.20, 0.05, 1)
        col = mixm.outputs[2]
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.85
    nt.links.new(col, bs.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bs.inputs["Normal"])
    finish(m, bs.outputs[0])
    return m


def blob_material(name, lo, hi):
    """Far canopy: leafy noise on opaque blobs."""
    m = _new_mat(name)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 1.6
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    tint = _tint(nt, lo, hi)
    mul = nt.nodes.new("ShaderNodeVectorMath"); mul.operation = "SCALE"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs[3].default_value, mr.inputs[4].default_value = 0.6, 1.2
    nt.links.new(vor.outputs["Distance"], mr.inputs[0])
    nt.links.new(tint, mul.inputs[0])
    nt.links.new(mr.outputs[0], mul.inputs["Scale"])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.75
    nt.links.new(mul.outputs[0], bs.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.9
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bs.inputs["Normal"])
    finish(m, bs.outputs[0])
    return m


def make_materials(tex):
    g = (0.10, 0.20, 0.06)
    return dict(
        leaf_broad=leaf_material("M_Leaf_Broad", tex["leaf_broad"]),
        leaf_small=leaf_material("M_Leaf_Small", tex["leaf_small"], lo=(0.8, 0.85, 0.65), hi=(1.3, 1.2, 0.85)),
        frond=leaf_material("M_Frond", tex["frond"], lo=(0.85, 0.9, 0.7), hi=(1.2, 1.15, 0.85), translucency=0.4),
        fan=leaf_material("M_Fan", tex["fan"], lo=(0.85, 0.9, 0.7), hi=(1.25, 1.15, 0.8)),
        cecropia=leaf_material("M_Cecropia", tex["cecropia"], lo=(0.9, 0.95, 0.9), hi=(1.25, 1.25, 1.1), rough=0.6),
        bark=bark_material("M_Bark", (0.07, 0.05, 0.035), (0.20, 0.16, 0.11), moss=0.5),
        bark_kapok=bark_material("M_Bark_Kapok", (0.22, 0.21, 0.18), (0.45, 0.43, 0.38), scale=1.4, moss=0.35),
        bark_cecropia=bark_material("M_Bark_Cecropia", (0.55, 0.55, 0.50), (0.80, 0.79, 0.72), scale=3.0, rings=True),
        bark_palm=bark_material("M_Bark_Palm", (0.20, 0.18, 0.13), (0.38, 0.35, 0.27), scale=4.0, rings=True),
        blob=blob_material("M_FarCanopy", (0.022, 0.060, 0.012), (0.060, 0.125, 0.025)),
        stone=bark_material("M_Stone", (0.13, 0.12, 0.10), (0.36, 0.34, 0.30), scale=1.6, moss=0.6),
        blob_kapok=blob_material("M_FarKapok", (0.030, 0.070, 0.016), (0.070, 0.135, 0.030)),
        ground_green=g,
    )


# ---------------------------------------------------------------------------------------------------- 3. geometry
def _unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-9)


class MB:
    """Mesh builder: tubes, cards and strips, one material slot per kind of surface."""

    def __init__(self):
        self.v, self.f, self.uv, self.m = [], [], [], []
        self.slots = []

    def _slot(self, mat):
        if mat not in self.slots:
            self.slots.append(mat)
        return self.slots.index(mat)

    def _face(self, idx, uvs, mat):
        self.f.append(idx)
        self.uv.append(uvs)
        self.m.append(self._slot(mat))

    def tube(self, P, R, mat, seg=8):
        P = np.asarray(P, float)
        R = np.broadcast_to(np.asarray(R, float), (len(P),))
        T = np.gradient(P, axis=0)
        T = T / np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
        n = np.cross(T[0], (0, 0, 1) if abs(T[0][2]) < 0.9 else (1, 0, 0))
        n = _unit(n)
        base = len(self.v)
        for i in range(len(P)):
            n = _unit(n - np.dot(n, T[i]) * T[i])
            b = np.cross(T[i], n)
            for j in range(seg):
                a = 2 * math.pi * j / seg
                self.v.append(P[i] + R[i] * (math.cos(a) * n + math.sin(a) * b))
        for i in range(len(P) - 1):
            for j in range(seg):
                j1 = (j + 1) % seg
                a0, a1 = base + i * seg + j, base + i * seg + j1
                b0, b1 = base + (i + 1) * seg + j, base + (i + 1) * seg + j1
                self._face((a0, a1, b1, b0), ((0, 0), (1, 0), (1, 1), (0, 1)), mat)

    def card(self, c, ex, ey, w, h, mat):
        c, ex, ey = np.asarray(c, float), _unit(ex), _unit(ey)
        base = len(self.v)
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            self.v.append(c + ex * sx * w / 2 + ey * sy * h / 2)
        self._face((base, base + 1, base + 2, base + 3), ((0, 0), (1, 0), (1, 1), (0, 1)), mat)

    def strip(self, Q, across, width, mat):
        """A frond: along the points Q, 'across' at each point, width (scalar or per point); V runs along."""
        Q = np.asarray(Q, float)
        W = np.broadcast_to(np.asarray(width, float), (len(Q),))
        base = len(self.v)
        for i in range(len(Q)):
            ac = _unit(across[i])
            self.v.append(Q[i] - ac * W[i] / 2)
            self.v.append(Q[i] + ac * W[i] / 2)
        k = len(Q) - 1
        for i in range(k):
            a0, a1, b0, b1 = base + 2 * i, base + 2 * i + 1, base + 2 * i + 2, base + 2 * i + 3
            self._face((a0, a1, b1, b0), ((0, i / k), (1, i / k), (1, (i + 1) / k), (0, (i + 1) / k)), mat)

    def slab(self, prof_lo, prof_hi, tang, thick, mat):
        """A buttress fin: two faces between a lower and an upper profile, 'thick' apart along 'tang', and its top."""
        lo, hi = np.asarray(prof_lo, float), np.asarray(prof_hi, float)
        th = np.broadcast_to(np.asarray(thick, float), (len(lo),))
        tang = _unit(tang)
        for sgn in (-1, 1):
            base = len(self.v)
            for i in range(len(lo)):
                self.v.append(lo[i] + tang * sgn * th[i] / 2)
                self.v.append(hi[i] + tang * sgn * th[i] / 2)
            for i in range(len(lo) - 1):
                self._face((base + 2 * i, base + 2 * i + 2, base + 2 * i + 3, base + 2 * i + 1),
                           ((0, 0), (1, 0), (1, 1), (0, 1)), mat)
        base = len(self.v)
        for i in range(len(hi)):
            self.v.append(hi[i] - tang * th[i] / 2)
            self.v.append(hi[i] + tang * th[i] / 2)
        for i in range(len(hi) - 1):
            self._face((base + 2 * i, base + 2 * i + 2, base + 2 * i + 3, base + 2 * i + 1), ((0, 0), (1, 0), (1, 1), (0, 1)), mat)

    def blob(self, c, r, mat, rng, subdiv=2, rough=0.25):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
        base = len(self.v)
        ph = rng.uniform(0, 10, 3)
        for vt in bm.verts:
            p = np.array(vt.co)
            k = 1.0 + rough * (math.sin(3.1 * p[0] + ph[0]) * math.sin(2.7 * p[1] + ph[1]) * math.sin(2.3 * p[2] + ph[2]))
            self.v.append(np.asarray(c, float) + p * np.asarray(r, float) * k)
        for fc in bm.faces:
            idx = tuple(base + vt.index for vt in fc.verts)
            self._face(idx, tuple((0.5, 0.5) for _ in idx), mat)
        bm.free()

    def build(self, name, mats):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(map(float, v)) for v in self.v], [], self.f)
        uvl = me.uv_layers.new(name="UVMap")
        flat = [uv for face in self.uv for uv in face]
        uvl.data.foreach_set("uv", np.asarray(flat, np.float32).ravel())
        for s in self.slots:
            me.materials.append(mats[s])
        me.polygons.foreach_set("material_index", np.asarray(self.m, np.int32))
        me.polygons.foreach_set("use_smooth", np.ones(len(self.f), bool))
        me.update()
        return bpy.data.objects.new(name, me)


def _crown_cards(mb, rng, c, r, n, size, mat, up_bias=0.4, flat=False):
    """Leaf cards in an ellipsoid round c, facing out of it (and a little up): a crown's silhouette is its cards."""
    c, r = np.asarray(c, float), np.asarray(r, float)
    for _ in range(n):
        d = _unit(rng.normal(size=3))
        if flat:
            d[2] = abs(d[2]) * 0.6 + 0.25
            d = _unit(d)
        p = c + d * r * rng.uniform(0.55, 1.0) ** 0.5
        nrm = _unit(d + np.array([0, 0, up_bias]) + rng.normal(0, 0.35, 3))
        if flat:
            nrm = _unit(np.array([0, 0, 1.0]) + d * np.array([0.5, 0.5, 0]) + rng.normal(0, 0.25, 3))
        ex = _unit(np.cross(nrm, rng.normal(size=3)))
        ey = np.cross(nrm, ex)
        s = size * rng.uniform(0.75, 1.25)
        mb.card(p, ex, ey, s, s, mat)


def _bent(p0, p1, rise, n=6):
    t = np.linspace(0, 1, n)[:, None]
    P = np.asarray(p0, float) * (1 - t) + np.asarray(p1, float) * t
    P[:, 2] += rise * np.sin(np.pi * t[:, 0] * 0.5)
    return P


def kapok(rng, mats, far=False):
    mb = MB()
    h = rng.uniform(45, 58)
    lean = rng.normal(0, 0.8, 2)
    z = np.linspace(-1.0, h * 0.86, 9)
    t = (z + 1) / (h * 0.86 + 1)
    P = np.stack([lean[0] * t ** 2, lean[1] * t ** 2, z], 1)
    R = 1.55 * (1 - 0.5 * t) + 0.4 * np.exp(-t * 12)
    bark = "blob" if False else "bark_kapok"
    mb.tube(P, R, bark, seg=6 if far else 12)
    if not far:   # buttresses: thin fins snaking out of the trunk foot
        nf = int(rng.integers(6, 9))
        for k in range(nf):
            a = 2 * math.pi * k / nf + rng.normal(0, 0.18)
            Lf, Hf = rng.uniform(4.5, 8.5), rng.uniform(4.0, 7.5)
            rad, tang = np.array([math.cos(a), math.sin(a), 0.0]), np.array([-math.sin(a), math.cos(a), 0.0])
            ph = rng.uniform(0, 6.3)
            rr = np.linspace(0, 1, 8)
            foot = rad[None] * (1.1 + Lf * rr[:, None]) + tang[None] * (0.7 * np.sin(rr * 3.0 + ph))[:, None]
            lo_ = foot + np.array([0, 0, -1.2])
            hi_ = foot + np.c_[np.zeros(8), np.zeros(8), Hf * (1 - rr) ** 1.7 + 0.25]
            mb.slab(lo_, hi_, tang, 0.42 * (1 - 0.6 * rr), bark)
    nb = int(rng.integers(5, 8))
    top = P[-1]
    ends = []
    for b in range(nb):
        az = 2 * math.pi * b / nb + rng.normal(0, 0.25)
        zb = h * rng.uniform(0.74, 0.84)
        L = rng.uniform(10, 16)
        p0 = np.array([lean[0] * (zb / h) ** 2, lean[1] * (zb / h) ** 2, zb])
        p1 = p0 + np.array([math.cos(az) * L, math.sin(az) * L, rng.uniform(4, 8)])
        mb.tube(_bent(p0, p1, 2.5, 5), np.linspace(0.55, 0.2, 5), bark, seg=5 if far else 7)
        ends.append(p1)
    ends.append(top + np.array([0, 0, 2.0]))
    for e in ends:
        rx = rng.uniform(6.5, 9.5)
        if far:
            mb.blob(e + np.array([0, 0, 1.5]), (rx, rx, 3.2), "blob_kapok", rng, subdiv=2)
        else:
            _crown_cards(mb, rng, e + np.array([0, 0, 1.8]), (rx, rx, 2.8), 120, 4.6, "leaf_small", flat=True)
    return mb.build("kapok" if not far else "far_kapok", mats)


def canopy(rng, mats, name, h, crown, far=False, zlo=0.42, ncl=(7, 10)):
    """A canopy tree: short trunk, big branches, a broad irregular crown of clusters from zlo*h up (and, far away, the
    same clusters as blobs)."""
    mb = MB()
    zt = h * (zlo + 0.12)
    bend = rng.normal(0, 0.7, 2)
    z = np.linspace(-0.8, zt, 6)
    t = (z + 0.8) / (zt + 0.8)
    P = np.stack([bend[0] * np.sin(t * 2.4), bend[1] * np.sin(t * 2.4), z], 1)
    rt = 0.55 * crown / 16
    mb.tube(P, np.linspace(rt * 1.25, rt * 0.75, 6), "bark", seg=6 if far else 9)
    nb = int(rng.integers(*ncl))
    for b in range(nb):
        az = 2 * math.pi * b / nb + rng.normal(0, 0.35)
        u = rng.uniform(0.0, 1.0)
        rr = crown * (0.22 + 0.22 * (1 - u) * rng.uniform(0.6, 1.0))         # low clusters spread wide, high ones close in
        zc = h * (zlo + 0.08 + (0.88 - zlo) * u)
        c = np.array([math.cos(az) * rr, math.sin(az) * rr, zc])
        mb.tube(_bent(P[-1], c, 1.5, 4), np.linspace(rt * 0.6, rt * 0.25, 4), "bark", seg=5)
        r = np.array([crown * rng.uniform(0.22, 0.32), crown * rng.uniform(0.22, 0.32), h * rng.uniform(0.10, 0.16)])
        if far:
            mb.blob(c, r, "blob", rng, subdiv=3)
        else:
            _crown_cards(mb, rng, c, r, int(rng.integers(90, 130)), rng.uniform(3.4, 4.3), "leaf_broad")
    c = np.array([0, 0, h * 0.86])
    r = np.array([crown * 0.3, crown * 0.3, h * 0.12])
    if far:
        mb.blob(c, r, "blob", rng, subdiv=3)
    else:
        _crown_cards(mb, rng, c, r, 120, 3.8, "leaf_broad")
    return mb.build(name, mats)


def acai(rng, mats):
    mb = MB()
    for s in range(int(rng.integers(3, 7))):
        base = np.array([*rng.normal(0, 0.8, 2), -0.5])
        h = rng.uniform(12, 20)
        out = _unit(np.array([*rng.normal(0, 1, 2), 0.0])) * rng.uniform(0.6, 2.2)
        t = np.linspace(0, 1, 7)[:, None]
        P = base + np.c_[out[0] * t[:, 0] ** 2, out[1] * t[:, 0] ** 2, h * t[:, 0]]
        mb.tube(P, 0.11, "bark_palm", seg=6)
        top = P[-1]
        nf = int(rng.integers(11, 15))
        for k in range(nf):
            az = 2 * math.pi * k / nf + rng.normal(0, 0.15)
            el = math.radians(rng.uniform(25, 65))
            L = rng.uniform(4.4, 5.6)
            hd = np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)])
            tt = np.linspace(0, 1, 7)
            Q = top[None] + hd[None] * L * tt[:, None] - np.array([0, 0, 1.0])[None] * (3.0 * tt ** 2)[:, None]
            side = _unit(np.cross(hd, (0, 0, 1)))
            down = _unit(np.cross(side, hd))
            for sg in (-1, 1):                     # each half hangs 40 degrees below the rachis
                ac = side * math.cos(0.7) * sg - down * math.sin(0.7)
                off = ac * np.linspace(0.6, 1.2, 7)[:, None] * (1 - 0.6 * tt[:, None] ** 3) * 0.5
                mb.strip(Q + off, [ac] * len(tt), np.linspace(0.6, 1.2, 7) * (1 - 0.6 * tt ** 3), "frond")
    return mb.build("acai", mats)


def buriti(rng, mats):
    mb = MB()
    h = rng.uniform(18, 25)
    P = np.c_[np.zeros(6), np.zeros(6), np.linspace(-0.5, h, 6)] + np.c_[rng.normal(0, 0.3, 6).cumsum() * 0.2,
                                                                          rng.normal(0, 0.3, 6).cumsum() * 0.2, np.zeros(6)]
    mb.tube(P, np.linspace(0.34, 0.26, 6), "bark_palm", seg=8)
    top = P[-1]
    nf = int(rng.integers(12, 17))
    for k in range(nf):
        az = 2 * math.pi * k / nf + rng.normal(0, 0.2)
        el = math.radians(rng.uniform(10, 70))
        hd = np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)])
        pet = top + hd * rng.uniform(2.5, 3.8)
        mb.tube([top, pet], 0.07, "bark_palm", seg=4)
        side = _unit(np.cross(hd, (0, 0, 1)))
        up = _unit(np.cross(side, hd))
        s = rng.uniform(5.0, 6.4)
        mb.card(pet + hd * s * 0.45, side, hd * 0.8 + up * 0.2, s, s, "fan")
    return mb.build("buriti", mats)


def cecropia(rng, mats):
    mb = MB()
    h = rng.uniform(14, 21)
    P = np.c_[rng.normal(0, 0.25, 5).cumsum() * 0.3, rng.normal(0, 0.25, 5).cumsum() * 0.3, np.linspace(-0.5, h * 0.7, 5)]
    mb.tube(P, np.linspace(0.24, 0.15, 5), "bark_cecropia", seg=7)
    for b in range(int(rng.integers(4, 7))):
        az = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(2.5, 5.5)
        p1 = P[-1] + np.array([math.cos(az) * L, math.sin(az) * L, rng.uniform(2.5, h * 0.3)])
        mb.tube(_bent(P[-1], p1, 1.2, 4), np.linspace(0.12, 0.06, 4), "bark_cecropia", seg=5)
        for k in range(int(rng.integers(6, 10))):
            a2 = rng.uniform(0, 2 * math.pi)
            c = p1 + np.array([math.cos(a2) * rng.uniform(0.5, 2.4), math.sin(a2) * rng.uniform(0.5, 2.4), rng.uniform(-0.6, 0.6)])
            nrm = _unit(np.array([0, 0, 1.0]) + rng.normal(0, 0.5, 3))
            ex = _unit(np.cross(nrm, rng.normal(size=3)))
            s = rng.uniform(2.6, 3.4)
            mb.card(c, ex, np.cross(nrm, ex), s, s, "cecropia")
    return mb.build("cecropia", mats)


def shrub(rng, mats, name):
    mb = MB()
    r = rng.uniform(2.2, 3.8)
    h = rng.uniform(3.0, 6.5)
    for k in range(int(rng.integers(3, 6))):
        top = np.array([*rng.normal(0, r * 0.3, 2), h * rng.uniform(0.5, 0.9)])
        mb.tube([np.array([0, 0, -0.3]), top], 0.06, "bark", seg=4)
    _crown_cards(mb, rng, (0, 0, h * 0.55), (r, r, h * 0.55), int(rng.integers(40, 65)), rng.uniform(1.3, 1.9), "leaf_broad",
                 up_bias=0.2)
    return mb.build(name, mats)


def stone(rng, mats, name, size):
    mb = MB()
    mb.blob((0, 0, size * 0.12), (size, size * rng.uniform(0.6, 0.9), size * 0.42), "stone", rng, subdiv=2, rough=0.35)
    return mb.build(name, mats)


def branch(rng, mats):
    """A fallen branch lying on the road, with two or three twigs."""
    mb = MB()
    L = rng.uniform(2.6, 4.0)
    P = _bent((-L / 2, 0, 0.09), (L / 2, rng.uniform(-0.4, 0.4), 0.06), 0.05, 6)
    mb.tube(P, np.linspace(0.11, 0.05, 6), "bark", seg=6)
    for k in range(int(rng.integers(2, 4))):
        a = P[int(rng.integers(1, 5))]
        side = 1 if k % 2 else -1
        mb.tube([a, a + np.array([rng.uniform(0.2, 0.6), side * rng.uniform(0.5, 1.0), 0.02])], [0.05, 0.02], "bark", seg=4)
    return mb.build("branch", mats)


def fern(rng, mats):
    """A low fern on the road's edge: fronds arching out, 0.4 m high."""
    mb = MB()
    n = int(rng.integers(9, 13))
    for k in range(n):
        az = 2 * math.pi * k / n + rng.normal(0, 0.15)
        hd = np.array([math.cos(az), math.sin(az), 0.0])
        tt = np.linspace(0, 1, 5)
        L = rng.uniform(0.7, 1.05)
        Q = hd[None] * L * tt[:, None] + np.array([0, 0, 1.0])[None] * (0.45 * np.sin(np.pi * tt * 0.8))[:, None]
        mb.strip(Q, [np.cross(hd, (0, 0, 1))] * 5, np.linspace(0.18, 0.32, 5) * (1 - 0.5 * tt ** 2), "frond")
    return mb.build("fern", mats)


def build_kit(tex_dir, seed=11):
    """All the kinds, in a collection 'JungleKit' (excluded from the view: the scatter instances it). Returns
    (collection, materials). Objects are named '<NN>_<kind>' so the scatter's index matches KINDS."""
    tex = make_textures(tex_dir)
    mats = make_materials(tex)
    rng = np.random.default_rng(seed)
    objs = [kapok(rng, mats),
            canopy(rng, mats, "canopy_a", 30, 20), canopy(rng, mats, "canopy_b", 22, 15, zlo=0.3, ncl=(6, 9)),
            canopy(rng, mats, "canopy_c", 36, 26, zlo=0.5, ncl=(8, 12)),
            acai(rng, mats), buriti(rng, mats), cecropia(rng, mats),
            shrub(rng, mats, "shrub_a"), shrub(rng, mats, "shrub_b")]
    rng2 = np.random.default_rng(seed)        # the far versions: the same random draws, so the same shapes
    kp = kapok(rng2, mats, far=True)
    fa = canopy(rng2, mats, "far_a", 30, 20, far=True)
    fb = canopy(rng2, mats, "far_b", 22, 15, far=True, zlo=0.3, ncl=(6, 9))
    fc = canopy(rng2, mats, "far_c", 36, 26, far=True, zlo=0.5, ncl=(8, 12))
    objs += [fa, fb, fc, kp]
    rng3 = np.random.default_rng(seed + 5)
    objs += [stone(rng3, mats, "stone_a", 0.55), stone(rng3, mats, "stone_b", 0.9), branch(rng3, mats), fern(rng3, mats)]
    coll = bpy.data.collections.get("JungleKit") or bpy.data.collections.new("JungleKit")
    for i, (o, kind) in enumerate(zip(objs, KINDS)):
        o.name = "%02d_%s" % (i, kind)
        coll.objects.link(o)
    return coll, mats


def export_kit(coll, folder):
    """One FBX per kind for Unreal (no collision: Docs/PISTA_SELVA_ESMERALDA.md, section 6)."""
    os.makedirs(folder, exist_ok=True)
    scene = bpy.context.scene
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)
    for o in coll.objects:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.export_scene.fbx(filepath=os.path.join(folder, "SM_Selva_%s.fbx" % o.name.split("_", 1)[1]), use_selection=True,
                                 apply_unit_scale=True, bake_space_transform=True, path_mode="COPY", embed_textures=False)
