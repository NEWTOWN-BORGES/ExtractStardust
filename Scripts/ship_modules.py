# Module variants for a ship built with ship_kit (Docs/MODULOS.md). The modules are the old game's catalogue (the
# Unity demo with the five old ships), adapted to the new ships:
# - wings of the ship's own: three per ship, grown from its stock wing (the same root section, so they go through the
#   same slots in the bodywork): short and swept with a tip fin, long with end plates, a second vector surface, braced
#   and thick, or a glider with folded tips and a glowing leading edge;
# - universal pieces fitted to the ship's own bodywork (found with ray casts): the armour as a body kit in the ship's
#   paint (side skirts, a blade round the nose, fins under the tail), vents and radiators, tail fins; and the utility
#   modules inside the nose (a scanner array, a route oracle, a field drone), seen only in the x-ray view;
# - the ship split for the game: the core (everything but the wings), the stock wings, and the skeleton (structure and
#   systems without the bodywork: the hangar's x-ray view of the engines, the reactor and the utility module).
# Called at the end of build_<ship>.py, after finish_ship:  build_modules(globals(), wings=..., palette=..., ...)
# Writes <out>/modules/<ship>_<piece>.fbx, all in the ship's frame (front -Y, up +Z, metres), so in Unreal every piece
# goes on the ship mesh with no offset; and <ship>_modules.json (the pieces and the engine nozzles, for the flames).
import json
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import ship_kit as K

# Wing variants: span, sweep of the leading edge and tip chord against the stock wing (past the slot), the anhedral
# against the stock one, the tip thickness; and what each adds. Names of the old catalogue (Doc 02 sec. 13).
WING_KINDS = {
    "blade": dict(span=0.60, sweep=1.35, chord=0.75, anh=1.0, th=1.0),      # APEX Blade Fins: agility
    "longspan": dict(span=1.65, sweep=0.95, chord=1.15, anh=0.40, th=1.0),  # Meridian Longspan: stability
    "vector": dict(span=1.05, sweep=1.00, chord=1.00, anh=1.0, th=1.0),     # Vanta Vector Surfaces: a second surface
    "brace": dict(span=1.15, sweep=0.90, chord=1.30, anh=0.8, th=1.8),      # Frontier Brace Wings: wall-ride, heavy
    "glide": dict(span=1.45, sweep=1.15, chord=0.85, anh=0.5, th=1.0),      # Oryx Glide Array: air control, relic
}
# Body kits (the armour), in the ship's own paint: skirt thickness and height up the side, how far the lip hangs
# under the hull's lowest line, panels along the skirt, how far the nose blade sticks out and how far back it runs,
# the height of the fins under the tail (0: none); all in metres, times the ship's scale.
ARMOUR_KITS = {
    "light": dict(T=0.036, h=0.17, drop=0.0, panels=1, lip=0.045, lip_len=1.0, fins=0.0),        # APEX Light Skin
    "guard": dict(T=0.060, h=0.23, drop=0.015, panels=3, lip=0.07, lip_len=1.2, fins=0.06),      # Meridian Guard Plates
    "bulwark": dict(T=0.100, h=0.30, drop=0.030, panels=1, lip=0.10, lip_len=1.35, fins=0.08),   # Frontier Bulwark
    "shell": dict(T=0.080, h=0.28, drop=0.020, panels=1, lip=0.06, lip_len=1.1, fins=0.0),       # Oryx Shell Lattice
    "aegis": dict(T=0.090, h=0.30, drop=0.032, panels=1, lip=0.12, lip_len=1.5, fins=0.10),      # AEGIS FRAME
}
ARMOUR_KINDS = tuple(ARMOUR_KITS)
# The bands across each skirt (0 at the seam on the side, 1 at the lip) that are not the main paint: an accent
# pinstripe, the lip and a rub strip in the edge paint, the shell's ribs and glowing seam, the AEGIS gold and hot seam.
ARMOUR_LOOK = {
    "light": [(0.48, 0.56, "accent"), (0.88, 1.0, "edge")],
    "guard": [(0.28, 0.38, "accent"), (0.84, 1.0, "edge")],
    "bulwark": [(0.16, 0.21, "accent"), (0.52, 0.80, "edge"), (0.90, 1.0, "edge")],
    "shell": [(0.36, 0.42, "Emit_Hover"), (0.52, 0.88, "rib"), (0.90, 1.0, "edge")],
    "aegis": [(0.14, 0.18, "Gold"), (0.40, 0.44, "Emit_Hot"), (0.44, 0.78, "accent"), (0.78, 0.82, "Gold"),
              (0.88, 1.0, "edge")],
}
COOLING_KINDS = ("vents", "radiator", "grid")
TAIL_KINDS = ("compact", "twin", "keel")
UTILITY_KINDS = ("mast", "dome", "drone")


def under(o, root):
    while o is not None:
        if o == root:
            return True
        o = o.parent
    return False


def ensure_mat(name, col, metal=0.0, rough=0.45, emit=0.0):
    if name not in K.MAT:
        K.material(name, col, metal=metal, rough=rough, emit=emit)
    return name


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def interp(plan, y):
    """The (z, height) of a skirt plan [(y, z, height)] at y."""
    for a, b in zip(plan, plan[1:]):
        if y <= b[0]:
            f = min(1.0, max(0.0, (y - a[0]) / (b[0] - a[0])))
            return a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f
    return plan[-1][1], plan[-1][2]


def mesh_bvh(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        base = len(verts)
        verts.extend(o.matrix_world @ v.co for v in me.vertices)
        polys.extend([base + i for i in p.vertices] for p in me.polygons)
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys) if polys else None


def frame_of(n, along=Vector((0, 1, 0))):
    """Rotation whose columns are (u along the given direction on the surface, v, n)."""
    n = n.normalized()
    u = (along - n * along.dot(n)).normalized()
    v = n.cross(u)
    return Matrix((u, v, n)).transposed()


class Builder:
    def __init__(self, ns, wings, palette, tail, scale, nozzle_r):
        self.ns, self.G = ns, ns["G"]
        self.wings, self.tail, self.scale, self.nozzle_r = wings, tail, scale, nozzle_r
        self.main, self.accent, self.edge = palette
        self.stem = K.NAME.lower()
        self.dir = os.path.join(K.OUT, "modules")
        os.makedirs(self.dir, exist_ok=True)
        self.pieces = []
        for name, col, metal, rough, emit in (("Metal", "#7E848B", 1.0, 0.45, 0.0), ("Metal_Bright", "#C2C7CC", 1.0, 0.22, 0.0),
                                              ("Graphite", "#2B2E33", 0.0, 0.6, 0.0), ("Black", "#101113", 0.0, 0.35, 0.0),
                                              ("Emit_Hover", "#5FE3FF", 0.0, 0.3, 3.0), ("Emit_Hot", "#FF7A2E", 0.0, 0.3, 6.0),
                                              ("Emit_Plasma", "#8FDFFF", 0.0, 0.3, 10.0), ("Gold", "#D9A932", 1.0, 0.3, 0.0),
                                              ("Glass", "#9FC6DA", 0.0, 0.05, 0.0)):
            ensure_mat(name, col, metal, rough, emit)
        self.sock = {o.name: Vector(o.location) for o in K.SHIP.objects if o.parent == self.G["Sockets"]}
        dg = bpy.context.evaluated_depsgraph_get()
        verts, polys = [], []
        for o in K.SKINS:
            if o.type != 'MESH' or self.is_wing(o) or self.is_decal(o) or o.name.startswith("Canopy"):
                continue
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            base = len(verts)
            verts.extend(o.matrix_world @ v.co for v in me.vertices)
            # the canopy glass is left out: armour stops at its edge instead of climbing over it
            glass = [bool(sl.material) and "Glass" in sl.material.name for sl in o.material_slots]
            polys.extend([base + i for i in p.vertices] for p in me.polygons
                         if not (p.material_index < len(glass) and glass[p.material_index]))
            ev.to_mesh_clear()
        self.bvh = BVHTree.FromPolygons(verts, polys)   # the bodywork, for placing pieces on it
        self.y_min, self.y_max = min(v.y for v in verts), max(v.y for v in verts)
        self.z_low, self.z_high = min(v.z for v in verts), max(v.z for v in verts)
        self.nose_y = self.y_min
        self.z_steps = [self.z_low - 0.01 + 0.01 * k for k in range(int((self.z_high - self.z_low) / 0.01) + 3)]
        self.cache, self.bay = {}, None
        # the front of the canopy: its glass high on the hull (a lens low on the nose is not it)
        mid, glass = (self.z_low + self.z_high) / 2, []
        for o in K.SHIP.objects:
            if o.type != 'MESH':
                continue
            mats = [bool(sl.material) and "Glass" in sl.material.name for sl in o.material_slots]
            glass.extend((o.matrix_world @ o.data.vertices[i].co) for p in o.data.polygons
                         if o.name.startswith("Canopy") or (p.material_index < len(mats) and mats[p.material_index])
                         for i in p.vertices)
        glass = [v for v in glass if v.z > mid]
        self.canopy_y = min(v.y for v in glass) if glass else self.y_min + 0.4 * (self.y_max - self.y_min)
        self.canopy_y1 = max(v.y for v in glass) if glass else self.canopy_y + 1.0
        self.wing_bvh = mesh_bvh(self.meshes(self.is_wing))
        self.hover_bvh = mesh_bvh(self.meshes(lambda o: under(o, self.G["Hover"]))) if "Hover" in self.G else None

    # ------------------------------------------------------------ scene helpers
    def is_wing(self, o):               # (the BASTION has no wings, nor their groups)
        return any(under(o, self.G[n]) for n in ("Wing_L", "Wing_R") if n in self.G)

    def is_decal(self, o):
        return under(o, self.G["Decals"])

    def meshes(self, keep):
        return [o for o in K.SHIP.objects if o.type == 'MESH' and not o.name.startswith("cut") and keep(o)]

    def export(self, objs, piece):
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in objs:
            o.hide_viewport = False
            o.hide_set(False)
            o.select_set(True)
        path = os.path.join(self.dir, "%s_%s.fbx" % (self.stem, piece))
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, use_mesh_modifiers=True,
                                 mesh_smooth_type='FACE', add_leaf_bones=False, apply_unit_scale=True,
                                 use_custom_props=False)
        self.pieces.append(piece)
        print("MODULE %s %s (%d objects)" % (K.NAME, piece, len(objs)))

    def drop(self, objs):
        for o in objs:
            if o in K.SKINS:
                K.SKINS.remove(o)
            me = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)

    def group(self, name):
        return K.group(name, self.G["Sockets"].parent)

    def built_in(self, g):
        return [o for o in K.SHIP.objects if o.type == 'MESH' and under(o, g)]

    def hit(self, origin, direction, dist=10.0):
        loc, nor, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized(), dist)
        return (loc, nor) if loc is not None else (None, None)

    def side_hit(self, s, y, z):
        return self.hit((s * 4.0, y, z), (-s, 0, 0), 8.0)

    def top_hit(self, x, y, below=False):
        return self.hit((x, y, -3.0), (0, 0, 1)) if below else self.hit((x, y, 5.0), (0, 0, -1))

    # ------------------------------------------------------------ 1. the split: core, stock wings, skeleton
    def split(self):
        self.export(self.meshes(lambda o: not self.is_wing(o)), "core")
        if self.meshes(self.is_wing):
            self.export(self.meshes(self.is_wing), "wing_stock")
        glow = ensure_mat("Reactor_Glow", "#FF8A3D", rough=0.3, emit=8.0)
        for o in self.meshes(lambda o: under(o, self.G["Reactor"])):
            for i, m in enumerate(o.data.materials):
                if m is not None and "Emit" in m.name:
                    o.data.materials[i] = K.MAT[glow]
        skins = set(K.SKINS)
        self.export(self.meshes(lambda o: o not in skins and not self.is_decal(o)), "skeleton")

    # ------------------------------------------------------------ 2. wings of the ship's own
    def wing(self, kind):
        ns, p = self.ns, WING_KINDS[kind]
        WING, stock_at, stock_loop = ns["WING"], ns["wing_at"], ns["wing_loop"]
        x0 = (ns.get("WING_X") or [r[0] for r in WING])[0]
        x1 = WING[-1][0]
        # Up to just outside the hull side the section stays the stock one (it goes through the slots in the panels);
        # past it the wing is free. The side is found above the slot.
        r0 = stock_at(x0)
        side, _ = self.side_hit(1, (r0[0] + r0[1]) / 2, r0[2] + 0.06)
        hull_x = abs(side.x) if side is not None else x0 + 0.10
        xs = max(x0 + 0.06, min(hull_x + 0.04, x0 + 0.5 * (x1 - x0)))
        les, tes, mids, ths = stock_at(xs)
        let, tet, midt, tht = stock_at(x1)
        xt = xs + (x1 - xs) * p["span"]
        tle = les + (let - les) * p["sweep"]
        tte = tle + (tet - let) * p["chord"]
        anh = math.atan2(mids - midt, x1 - xs) * p["anh"]
        tmid = mids - (xt - xs) * math.tan(anh)
        tth = tht * p["th"]

        def at(x):
            if x <= xs:
                return stock_at(x)
            f = min(1.0, (x - xs) / (xt - xs))
            return les + (tle - les) * f, tes + (tte - tes) * f, mids + (tmid - mids) * f, ths + (tth - ths) * f

        def loop(x, grow=0.0):
            if x <= xs:
                return stock_loop(x, grow)
            le, te, mid, th = at(x)
            th += 2 * grow
            le, te = le - grow, te + grow
            e = min(0.08, 0.08 * (te - le))
            return [(le, mid - th / 6), (le, mid + th / 6), (le + e, mid + th / 2), (te - 0.03, mid + th / 2),
                    (te, mid + th / 6), (te, mid - th / 6), (te - 0.03, mid - th / 2), (le + e, mid - th / 2)]

        made = []
        x_acc = xt - 0.28 * (xt - x0)
        le_mat = "Metal_Bright" if kind == "brace" else self.edge
        for s, side in ((1, "R"), (-1, "L")):
            g = self.group("Module_Wing_%s_%s" % (kind, side))

            def w3d(x, y, z, s=s):
                return Vector((s * x, y, z))

            def w_centre(c):
                le, te, mid, th = at(abs(c.x))
                return Vector((c.x, (le + te) / 2, mid))

            spar = K.Part("Wing_Structure_" + side)
            a0, a1 = at(x0 - 0.02), at(xt - 0.05)
            for f in (0.45, 0.85):
                a = (x0 - 0.02, a0[0] + f * (a0[1] - a0[0]), a0[2])
                b = (xt - 0.05, a1[0] + f * (a1[1] - a1[0]), a1[2])
                spar.tube([(s * a[0], a[1], a[2]), (s * b[0], b[1], b[2])], 0.02 if f < 0.5 else 0.014, "Metal",
                          square=True)
            for x in (xs, (xs + xt) / 2, xt - 0.07):
                L = K.inset(loop(x), 0.010)
                spar.loft([[Vector((s * (x + d), q.x, q.y)) for q in L] for d in (-0.005, 0.005)],
                          lambda i, j: "Metal", closed_u=True, cap0="Metal", cap1="Metal")
            zr = at(x0)[2]
            for f in (0.45, 0.85):
                spar.box((s * x0, a0[0] + f * (a0[1] - a0[0]), zr), (0.06, 0.10, 0.09), "Metal")   # root clamps
            made.append(spar.finish(g, bevel=0.002))

            def skin(name, t0, t1, m_fn):
                pp = K.Part(name + "_" + side)
                K.surface(pp, loop, t0, t1, x0, xt, [xs, (xs + xt) / 2], w3d, (False, False))
                K.orient_out(pp, w_centre)
                K.paint(pp, m_fn)
                return K.shell(pp, g, thick=0.006, bevel=0.0015)

            made.append(skin("Wing_Top", 2, 3, lambda c, n: self.accent if abs(c.x) > x_acc else self.main))
            made.append(skin("Wing_Bottom", 6, 7, lambda c, n: "Graphite"))
            made.append(skin("Wing_TE", 3, 6, lambda c, n: self.edge))
            made.append(skin("Wing_LE", 7, 10, lambda c, n: le_mat))
            tip = K.Part("Wing_Tip_" + side)
            L = loop(xt - K.GAP / 2)
            tip.loft([[Vector((s * (xt - K.GAP / 2 - d), q[0], q[1])) for q in L] for d in (0, 0.01)],
                     lambda i, j: self.edge, closed_u=True, cap0=self.edge, cap1=self.edge)
            made.append(tip.finish(g, bevel=0.002, skin=True))

            extra = K.Part("Wing_%s_Extra_%s" % (kind.capitalize(), side))
            tle_, tte_, tmid_, tth_ = at(xt - 0.03)
            chord = tte_ - tle_
            if kind == "blade":           # a small fin standing on the tip
                K.shark_fin(extra, lambda y: tmid_ + tth_ / 2, s * (xt - 0.05), (tle_ + 0.10 * chord, tte_ - 0.02),
                            (tle_ + 0.55 * chord, tte_), 0.22, 0.028, self.accent, self.edge, math.radians(8), s)
            elif kind == "longspan":      # end plates, above and below the tip
                extra.box((s * (xt + 0.010), (tle_ + tte_) / 2 + 0.02, tmid_ + 0.04), (0.02, chord + 0.10, 0.30),
                          self.edge)
                extra.box((s * (xt + 0.022), (tle_ + tte_) / 2 + 0.02, tmid_ + 0.04), (0.005, chord * 0.6, 0.20),
                          self.accent)
            elif kind == "vector":        # a second, smaller surface over the wing on two pylons, glowing trailing edge
                xa, xb = xs + 0.10 * (xt - xs), xt - 0.04
                rise = 0.18
                vrows = []
                for x in (xa, (xa + xb) / 2, xb):
                    le, te, mid, th = at(x)
                    vle, vte = le + 0.45 * (te - le), te + 0.04
                    vth = 0.5 * th
                    sec = [(vle, mid + rise), (vle + 0.04, mid + rise + vth / 2), (vte - 0.03, mid + rise + vth / 3),
                           (vte, mid + rise), (vte - 0.03, mid + rise - vth / 3), (vle + 0.04, mid + rise - vth / 2)]
                    vrows.append([Vector((s * x, y, z)) for y, z in sec])
                extra.loft(vrows, lambda i, j: self.accent if j < 3 else "Graphite", closed_u=True, cap0=self.edge,
                           cap1=self.edge)
                for x in (xa + 0.06, xb - 0.10):
                    le, te, mid, th = at(x)
                    yy = le + 0.70 * (te - le)
                    extra.box((s * x, yy, mid + rise / 2 + th / 4), (0.025, 0.10, rise - th / 2), "Metal")
                lx = (xa + xb) / 2
                le, te, mid, th = at(lx)
                extra.box((s * lx, te + 0.035, mid + rise), (xb - xa, 0.012, 0.008), "Emit_Hover")
            elif kind == "brace":         # a strut under the wing from the hull side, an armoured leading edge
                xm = x0 + 0.62 * (xt - x0)
                le, te, mid, th = at(xm)
                lr, tr, mr, hr = at(x0 + 0.02)
                ym = le + 0.45 * (te - le)
                extra.tube([(s * (x0 - 0.05), lr + 0.45 * (tr - lr), mr - 0.20), (s * xm, ym, mid - th / 2)], 0.022,
                           "Metal", 10)
                extra.cyl((s * xm, ym - 0.05, mid - th / 2 - 0.01), (s * xm, ym + 0.05, mid - th / 2 - 0.01), 0.03,
                          "Metal_Bright", 10)
            elif kind == "glide":         # tips folded up, a glowing leading edge
                K.shark_fin(extra, lambda y: tmid_ + tth_ / 2, s * (xt - 0.04), (tle_ + 0.05 * chord, tte_),
                            (tle_ + 0.75 * chord, tte_ + 0.06), 0.34, 0.03, self.accent, self.edge,
                            math.radians(28), s)
                pts = []
                for k in range(6):
                    x = xs + (xt - 0.06 - xs) * k / 5
                    le, te, mid, th = at(x)
                    pts.append((s * x, le - 0.006, mid))
                extra.tube(pts, 0.008, "Emit_Plasma", 8)
            made.append(extra.finish(g, bevel=0.0015, smooth_angle=50))
        self.export(made, "wing_" + kind)
        self.drop(made)

    # ------------------------------------------------------------ 3. body kits (the armour)
    def side_x(self, s, y, z):
        """How far out the bodywork is at (y, z) on side s, seen from outside, or None (past the hull there)."""
        key = (s, round(y, 4), round(z, 4))
        if key not in self.cache:
            loc, _ = self.side_hit(s, y, z)
            self.cache[key] = abs(loc.x) if loc is not None else None
        return self.cache[key]

    def side_span(self, s, y):
        """The lowest and the highest point of the hull side at y, or None."""
        zs = [z for z in self.z_steps if self.side_x(s, y, z) is not None]
        return (zs[0], zs[-1]) if zs else None

    def wing_floor(self, s, y, x0, reach):
        """The lowest underside of the stock wing from x0 out to x0 + reach at y, or None (or no wings at all)."""
        if self.wing_bvh is None:
            return None
        zs = []
        for k in range(6):
            loc, _, _, _ = self.wing_bvh.ray_cast(Vector((s * (x0 + reach * k / 5), y, self.z_low - 1.0)),
                                                  Vector((0, 0, 1)), 5.0)
            if loc is not None:
                zs.append(loc.z)
        return min(zs) if zs else None

    def footprint(self, y):
        """The hull's underside across y, its lowest stretch only: one [(x, z), ...] per body (one hull, or two
        booms). Narrow gaps (the hover emitters' cut-outs) do not split a body."""
        hits = []
        for k in range(321):
            x = -1.6 + 0.01 * k
            loc, _ = self.hit((x, y, self.z_low - 1.0), (0, 0, 1), 5.0)
            hits.append((x, loc.z) if loc is not None else None)
        zs = [h[1] for h in hits if h]
        if not zs:
            return []
        top = min(zs) + 0.10
        bodies = []
        for h in hits:
            if h is None or h[1] > top:
                continue
            if bodies and h[0] - bodies[-1][-1][0] < 0.45:
                bodies[-1].append(h)
            else:
                bodies.append([h])
        return [b for b in bodies if len(b) >= 3]

    def skirt_plans(self, s, kit, y_start):
        """Where the skirt runs on side s: [(y, lowest z of the side, height up it)] along the longest stretch behind
        y_start where the side is tall enough and the stock wing leaves room over it (it goes on under a low wing,
        lower). The seam line never climbs or drops faster than 30 cm a metre, so it eases down before a wing
        instead of stepping. Never up past the waist."""
        sc, T, dy = self.scale, kit["T"] * self.scale, 0.04
        rows = []
        y = y_start
        while y < self.y_max - 0.05 * (self.y_max - self.y_min):
            span = self.side_span(s, y)
            row = None
            if span:
                z_b, z_t = span
                h = min(kit["h"] * sc, 0.5 * (z_t - z_b))
                x0 = self.side_x(s, y, z_b + 0.01) or 0.0
                near = self.wing_floor(s, y, x0, 0.02)          # over the seam
                out = self.wing_floor(s, y, x0, T + 0.06)       # over the lip
                if near is not None:
                    h = min(h, near - z_b - 0.02)
                if h >= 0.05 * sc and (out is None or out > z_b + 0.04):
                    row = [y, z_b, h, self.side_x(s, y, z_b + 0.5 * h) or 0.0]
            rows.append(row)
            y += dy
        for i in range(1, len(rows) - 1):               # one or two odd stations (a ray down a panel gap) are bridged
            if rows[i] is None and rows[i - 1] is not None:
                j = next((j for j in (i + 1, i + 2) if j < len(rows) and rows[j] is not None), None)
                if j is not None:
                    for k in range(i, j):
                        f = (k - i + 1) / (j - i + 1)
                        rows[k] = [a + (b - a) * f for a, b in zip(rows[i - 1], rows[j])]
        runs, cur = [], []
        for row in rows:
            # a step in the side or in its bottom line (an intake, a wing glove) ends the stretch too
            if row is None or (cur and (abs(row[3] - cur[-1][3]) > 0.03 or abs(row[1] - cur[-1][1]) > 0.025)):
                runs, cur = runs + [cur], []
            if row is not None:
                cur.append(row)
        run = max(runs + [cur], key=len)
        if len(run) * dy < 0.5 * sc:
            return []
        hs = [r[2] for r in run]
        for i in range(1, len(hs)):                     # the seam's slope, both ways
            hs[i] = min(hs[i], hs[i - 1] + 0.3 * dy)
        for i in range(len(hs) - 2, -1, -1):
            hs[i] = min(hs[i], hs[i + 1] + 0.3 * dy)
        zb = [r[1] for r in run]                        # the bottom line: the lowest round each station, averaged
        lo = [min(zb[max(0, i - 2):i + 3]) for i in range(len(zb))]
        for i, r in enumerate(run):
            w, v = lo[max(0, i - 3):i + 4], hs[max(0, i - 2):i + 3]
            r[1], r[2] = sum(w) / len(w), sum(v) / len(v)
        return [r[:3] for r in run] and [[r[:3] for r in run]]

    def skirt_grid(self, s, plan, us, Lf):
        """The bodywork under a skirt, station by station: the heights of the section, how far out the hull is at
        each (raw, and smoothed along the skirt, hanging straight over the lower chamfer, so the panel is clean),
        and a safe point just inside it."""
        ya = plan[0][0]
        grid = []
        for y, z_b, h in plan:
            h *= 0.55 + 0.45 * smooth((y - ya) / Lf)             # the seam sweeps down to the point at the front
            zs = [z_b + h + (0.004 - h) * u for u in us]
            raw = []
            for z in zs:
                x = self.side_x(s, y, z)
                raw.append(x if x is not None else (raw[-1] if raw else 0.0))
            env, m = [], 0.0
            for x in raw:
                m = max(m, x)
                env.append(m)
            grid.append([y, zs, raw, env])
        n, M = len(grid), len(us)
        smo = [[0.0] * M for _ in range(n)]
        ins = [[0.0] * M for _ in range(n)]
        for k in range(M):                      # along the skirt: the highest round each station, then averaged
            hi = [max(grid[j][3][k] for j in range(max(0, i - 1), min(n, i + 2))) for i in range(n)]
            for i in range(n):
                w = hi[max(0, i - 3):i + 4]
                smo[i][k] = sum(w) / len(w)
                ins[i][k] = min(grid[j][2][k] for j in range(max(0, i - 1), min(n, i + 2))) - 0.006
        return [(g[0], g[1], g[2], smo[i], ins[i]) for i, g in enumerate(grid)]

    @staticmethod
    def grid_at(grid, y):
        for a, b in zip(grid, grid[1:]):
            if y <= b[0]:
                f = min(1.0, max(0.0, (y - a[0]) / (b[0] - a[0])))
                return [[p + (q - p) * f for p, q in zip(u, v)] for u, v in zip(a[1:], b[1:])]
        return [list(v) for v in grid[-1][1:]]

    def skirts(self, part, kind, kit, y_start):
        sc = self.scale
        T, drop, Lf, Lr = kit["T"] * sc, kit["drop"] * sc, 0.80 * sc, 0.30 * sc
        bands = ARMOUR_LOOK[kind]
        us = sorted({k / 12 for k in range(13)} | {u for a, b, _ in bands for u in (a, b)})
        us = [u for i, u in enumerate(us) if i == 0 or u - us[i - 1] > 0.012]
        b0 = 0.004 / T                                               # the seam stands 4 mm off the bodywork
        shape = {"shell": lambda u: 1 - (1 - u) ** 2.2, "aegis": lambda u: u ** 1.7,
                 "bulwark": lambda u: smooth(min(1.0, 1.25 * u))}.get(kind, smooth)

        def look(u, y):
            for a, b, m in bands:
                if a <= u <= b:
                    if m == "rib":                                   # the shell's ribs, 4 cm every 16 cm
                        return self.accent if int(round((y - self.y_min) / 0.04)) % 4 == 0 else self.main
                    return {"accent": self.accent, "edge": self.edge}.get(m, m)
            return self.main

        M = len(us)
        for s in (1, -1):
            for plan in self.skirt_plans(s, kit, y_start):
                grid = self.skirt_grid(s, plan, us, Lf)
                ya, yb = plan[0][0], plan[-1][0]
                n = kit["panels"] if yb - ya > 1.2 * sc else 1
                cuts = [ya + (yb - ya) * k / n for k in range(n + 1)]
                for k in range(n):
                    pa, pb = cuts[k] + (0.01 if k else 0.0), cuts[k + 1] - (0.01 if k < n - 1 else 0.0)
                    ys = [pa] + [r[0] for r in plan if pa + 0.015 < r[0] < pb - 0.015] + [pb]
                    rows = []
                    for y in ys:
                        zs, raw, smo, ins = self.grid_at(grid, y)
                        ramp = smooth((y - ya) / Lf) * smooth((yb - y) / Lr)
                        out = [Vector((s * (r + ramp * (m - r) + T * ramp * (b0 + (1 - b0) * shape(u))), y,
                                       z - drop * ramp * u * u)) for r, m, z, u in zip(raw, smo, zs, us)]
                        under = Vector((s * (ins[-1] - 0.014), y, out[-1].z))
                        rows.append(out + [under] + [Vector((s * x, y, z)) for x, z in zip(ins[::-1], zs[::-1])])

                    def m_fn(i, j, ys=ys):
                        if j < M - 1:
                            return look((us[j] + us[j + 1]) / 2, ys[i])
                        return self.edge if j < M + 1 else self.main
                    part.loft(rows, m_fn, closed_u=True, cap0=self.edge, cap1=self.edge)

    def splitter(self, part, kit):
        """A blade round the bottom of the nose (round each boom's nose on a twin-boom ship), sticking out past the
        hull by kit['lip'] at the tip and fading into the bodywork kit['lip_len'] further back."""
        sc = self.scale
        D, Ls, tk0, w_in = kit["lip"] * sc, kit["lip_len"] * sc, (0.016 + 0.1 * kit["T"]) * sc, 0.04
        y0 = self.y_min
        while y0 < self.y_min + 1.0 and not self.footprint(y0):
            y0 += 0.02
        chains = []                               # per body: rows of (y, left x, left z, right x, right z)
        y = y0
        while y <= y0 + Ls:
            for b in self.footprint(y):
                row = (y, b[0][0], b[0][1], b[-1][0], b[-1][1])
                c = (row[1] + row[3]) / 2
                near = [ch for ch in chains if ch[-1][0] > y - 0.08 and abs((ch[-1][1] + ch[-1][3]) / 2 - c) < 0.3]
                if near:
                    near[0].append(row)
                elif y < y0 + 0.15:
                    chains.append([row])
            y += 0.05
        chains = [ch for ch in chains if len(ch) >= 4]
        if not chains:
            return
        x_min = min(ch[0][1] for ch in chains)
        x_max = max(ch[0][3] for ch in chains)
        for ch in chains:
            ya = ch[0][0]
            pts = []                              # (x, y, z, side or None at the tip, the ship's outermost edge?)
            for y, xl, zl, xr, zr in reversed(ch):
                pts.append((xl, y, zl, -1, ch[0][1] <= x_min + 1e-6))
            cx, half, zf = (ch[0][1] + ch[0][3]) / 2, (ch[0][3] - ch[0][1]) / 2, (ch[0][2] + ch[0][4]) / 2
            arc = []
            for k in range(1, 8):                 # the tip, a flat half-ellipse ahead of the first station
                a = math.pi * k / 8
                arc.append((cx - half * math.cos(a), ya - 0.5 * max(half, 0.05) * math.sin(a), zf, None, True))
            pts += arc
            for y, xl, zl, xr, zr in ch:
                pts.append((xr, y, zr, 1, ch[0][3] >= x_max - 1e-6))
            # the outline smoothed (the underside is found on a 1 cm grid, the chamfers are faceted)
            sm = []
            for k in range(len(pts)):
                w = pts[max(0, k - 2):k + 3]
                sm.append((sum(p[0] for p in w) / len(w), sum(p[1] for p in w) / len(w), sum(p[2] for p in w) / len(w)))
            ds = []
            for k, (x, y, z, side, outer) in enumerate(pts):
                f = min(1.0, max(0.0, (y - ya) / Ls))
                d = D * (1 - f) ** 1.2
                if side is not None and outer:    # just past the hull's widest point near the bottom
                    wide = max([self.side_x(side, y, z + dz) or 0.0 for dz in (0.0, 0.015, 0.03)])
                    d = min(max(d, wide - abs(x) + 0.5 * d), d + 0.05 * sc)
                elif side is not None:
                    d *= 0.6
                ds.append(d * (1 - smooth((f - 0.7) / 0.3)))
            ds = [sum(ds[max(0, k - 3):k + 4]) / len(ds[max(0, k - 3):k + 4]) for k in range(len(ds))]
            rows = []
            for k, (x, y, z) in enumerate(sm):
                p0, p1 = sm[max(k - 1, 0)], sm[min(k + 1, len(sm) - 1)]
                tan = Vector((p1[0] - p0[0], p1[1] - p0[1], 0)).normalized()
                n = Vector((-tan.y, tan.x, 0))
                if n.dot(Vector((x - cx, y - (ya + 0.3), 0))) < 0:
                    n = -n
                f = min(1.0, max(0.0, (y - ya) / Ls))
                d, tk = ds[k], tk0 * (0.35 + 0.65 * (1 - f))
                c = Vector((x, y, z))
                rows.append([c - n * w_in + Vector((0, 0, 0.004)), c + n * d + Vector((0, 0, 0.004)),
                             c + n * (d + 0.35 * tk) + Vector((0, 0, -0.5 * tk)), c + n * d + Vector((0, 0, -tk)),
                             c - n * w_in + Vector((0, 0, -tk))])
            part.loft(rows, lambda i, j: self.accent if j in (1, 2) else self.edge, closed_u=True, cap0=self.edge,
                      cap1=self.edge)

    def diffuser(self, part, kit):
        """Two fins under the end of the hull's lowest part, growing towards the tail, clear of the hover emitters."""
        sc = self.scale
        hd, Lf, tf = kit["fins"] * sc, 0.62 * sc, 0.016 * sc
        y = self.y_max - 0.02
        while y > self.y_min and not any(b for b in self.footprint(y) if min(z for _, z in b) < self.z_low + 0.12):
            y -= 0.03
        bodies = self.footprint(y - 0.04)
        if not bodies:
            return
        y_end = y - 0.01
        xs = [min(b[0][0] for b in bodies) + 0.07 * sc, max(b[-1][0] for b in bodies) - 0.07 * sc]
        for x0 in xs:
            for x in (x0, x0 - math.copysign(0.05, x0), x0 - math.copysign(0.10, x0)):
                rows, clash = [], False
                for k in range(9):
                    yy = y_end - Lf + Lf * k / 8
                    loc, _ = self.hit((x, yy, self.z_low - 1.0), (0, 0, 1), 5.0)
                    if loc is None or loc.z > self.z_low + 0.16:
                        rows = []
                        break
                    top, hgt = loc.z + 0.004, hd * max(0.06, (k / 8) ** 1.3)
                    pad, _, _, _ = self.hover_bvh.ray_cast(Vector((x, yy, self.z_low - 1.0)), Vector((0, 0, 1)), 5.0) \
                        if self.hover_bvh else (None, None, None, None)
                    if pad is not None and pad.z < top + 0.01:
                        clash = True
                        break
                    rows.append([Vector((x - tf / 2, yy, top)), Vector((x + tf / 2, yy, top)),
                                 Vector((x + tf / 2, yy, top - hgt)), Vector((x - tf / 2, yy, top - hgt))])
                if rows and not clash:
                    part.loft(rows, lambda i, j: self.accent if j == 2 else self.edge, closed_u=True,
                              cap0=self.edge, cap1=self.edge)
                    break

    def armour(self, kind):
        """A body kit in the ship's own paint: it changes the lines a little and stays clean. Side skirts along the
        bottom of the hull (under the waist, never near the canopy, under the wings), a blade round the nose, and
        on the heavier kits fins under the tail."""
        kit = ARMOUR_KITS[kind]
        g = self.group("Module_Armor_" + kind)
        part = K.Part("Armor_" + kind.capitalize())
        self.splitter(part, kit)
        self.skirts(part, kind, kit, self.nose_y + (kit["lip_len"] - 0.35) * self.scale)
        if kit["fins"]:
            self.diffuser(part, kit)
        made = [part.finish(g, smooth_angle=40)] if part.bm.faces else []
        self.export(made, "armor_" + kind)
        self.drop(made)

    # ------------------------------------------------------------ 4. tail fins (the cooling is in section 7, flush)
    def tail_fins(self, kind):
        c = self.sock.get("Socket_Tail")
        if c is None:
            return
        below = self.tail == "below"
        sc = self.scale
        y_end = c.y
        made = []
        g = self.group("Module_Tail_" + kind)
        part = K.Part("Tail_" + kind.capitalize())

        def base_fn(x):
            def f(y):
                loc, _ = self.top_hit(x, y, below)
                if loc is None:
                    loc, _ = self.top_hit(x, y_end - 0.6, below)
                return loc.z if loc is not None else c.z
            return f

        flip = math.pi if below else 0.0
        if kind == "compact":
            K.shark_fin(part, base_fn(0.0), 0.0, (y_end - 0.85 * sc, y_end - 0.10), (y_end - 0.35 * sc, y_end + 0.02),
                        0.40 * sc, 0.045, self.main, self.edge, flip, 1)
        elif kind == "twin":
            for s in (-1, 1):
                x = s * 0.24 * sc
                cant = math.pi - math.radians(18) if below else math.radians(18)     # canted outwards either way
                K.shark_fin(part, base_fn(x), x, (y_end - 0.95 * sc, y_end - 0.15), (y_end - 0.45 * sc, y_end),
                            0.44 * sc, 0.04, self.main, self.edge, cant, s)
        else:  # keel: long and low, with vent slots
            K.shark_fin(part, base_fn(0.0), 0.0, (y_end - 1.60 * sc, y_end - 0.05), (y_end - 0.60 * sc, y_end + 0.05),
                        0.27 * sc, 0.055, "Graphite", self.edge, flip, 1)
            f = base_fn(0.0)
            for k in range(4):
                y = y_end - 1.25 * sc + k * 0.22 * sc
                z = f(y) + (-0.07 if below else 0.07)
                part.box((0, y, z), (0.056, 0.12, 0.03), "Black")
        made.append(part.finish(g, bevel=0.0015, smooth_angle=50))
        self.export(made, "tail_" + kind)
        self.drop(made)

    # ------------------------------------------------------------ 6. utility: inside the nose, seen in the x-ray view
    def utility_bay(self):
        """The room inside the nose, ahead of the cockpit, for the utility module: (centre, half sizes) of the largest
        box clear of the structure and the systems (the skeleton) and 2 cm inside the bodywork. Off the centre line
        (one in each boom) only when the centre has no room."""
        if self.bay:
            return self.bay
        dg = bpy.context.evaluated_depsgraph_get()
        skins = set(K.SKINS)
        verts, polys = [], []
        for o in self.meshes(lambda o: o not in skins and not self.is_decal(o) and not self.is_wing(o)):
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            base = len(verts)
            verts.extend(o.matrix_world @ v.co for v in me.vertices)
            polys.extend([base + i for i in p.vertices] for p in me.polygons)
            ev.to_mesh_clear()
        systems = BVHTree.FromPolygons(verts, polys)
        P = np.array([tuple(v) for v in verts]) if verts else np.zeros((0, 3))

        def inside(p):                          # (not downwards: the belly has the hover emitters' cut-outs)
            loc, _, _, dist = self.bvh.find_nearest(p)
            if loc is None or dist < 0.02:
                return False
            return all(self.bvh.ray_cast(p, Vector(d), 3.0)[0] is not None for d in ((0, 0, 1), (1, 0, 0), (-1, 0, 0)))

        def clear(c, hs):
            lo, hi = np.array(c - hs) - 0.015, np.array(c + hs) + 0.015
            if np.any(np.all((P > lo) & (P < hi), axis=1)):
                return False
            # the faces and edges of the box, its corners a little in (the pieces do not fill them)
            if not all(inside(c + Vector((hs.x * i, hs.y * j, hs.z * k)) * (0.8 if i and j and k else 1.0))
                       for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1) if (i, j, k) != (0, 0, 0)):
                return False
            bv = [c + Vector((hs.x * i, hs.y * j, hs.z * k)) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
            box = BVHTree.FromPolygons(bv, [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4),
                                            (1, 5, 7, 3)])
            return not systems.overlap(box)

        sc = self.scale

        def search(xs_at, sizes):
            for f in sizes:
                hx, hy = 0.21 * f * sc, 0.30 * f * sc
                y = self.canopy_y - 0.06 - hy
                while y - hy > self.nose_y + 0.25:          # from just ahead of the cockpit towards the tip
                    for x in xs_at(y):
                        bots = [self.hit((x + dx, y, self.z_low - 1.0), (0, 0, 1))[0] for dx in (-0.1, 0.0, 0.1)]
                        bots = [b.z for b in bots if b is not None]
                        top = self.hit((x, y, self.z_high + 1.0), (0, 0, -1))[0]
                        if not bots or top is None or top.z <= min(bots):
                            continue
                        hs = Vector((hx, hy, min(0.11 * sc, (top.z - min(bots)) / 2 - 0.035)))
                        z = min(bots) + 0.035 + hs.z
                        while hs.z >= 0.045 and z + hs.z <= top.z - 0.035:
                            c = Vector((x, y, z))
                            if clear(c, hs) and (x == 0 or clear(Vector((-x, y, z)), hs)):
                                return c, hs
                            z += 0.02
                    y -= 0.04
            return None

        def booms(y):                           # off the centre line: the middle of each boom (twin-boom ships)
            return sorted({round(abs(sum(p[0] for p in b) / len(b)), 2) for b in self.footprint(y)
                           if abs(sum(p[0] for p in b) / len(b)) > 0.25})

        bay = (search(lambda y: [0.0], (1.0, 0.86, 0.74, 0.64, 0.55)) or search(booms, (0.74, 0.64, 0.55, 0.47))
               or search(lambda y: [0.0], (0.47, 0.40, 0.34, 0.30, 0.26)))
        if bay:
            self.bay = bay
            print("UTILITY BAY %s centre (%.2f, %.2f, %.2f) half (%.2f, %.2f, %.2f)%s" % (
                K.NAME, *bay[0], *bay[1], " and its mirror" if bay[0].x else ""))
            return bay
        c = self.sock.get("Socket_Utility", Vector((0, self.nose_y + 0.8, self.z_low + 0.15)))
        self.bay = (Vector((0, c.y + 0.4, c.z + 0.08)), Vector((0.09, 0.13, 0.05)) * sc)
        print("UTILITY BAY %s: no clear room, fallback under the utility socket" % K.NAME)
        return self.bay

    def utility(self, kind):
        """The utility modules sit inside the nose, ahead of the cockpit: hidden in flight, seen in the hangar's x-ray
        view, where they glow. mast: the scanner array (a dish looking ahead, over its electronics); dome: the route
        oracle (a glowing data core in gimbal bands, over a finned block); drone: the field drone folded in its
        launch bay. On a twin-boom ship with the room off the centre line, one in each boom."""
        bay, hs = self.utility_bay()
        glow = ensure_mat("Utility_Glow", "#5FE3FF", rough=0.3, emit=8.0)
        g = self.group("Module_Utility_" + kind)
        part = K.Part("Utility_" + kind.capitalize())
        for c in [bay] + ([Vector((-bay.x, bay.y, bay.z))] if bay.x else []):   # one in each boom when off-centre
            self.utility_piece(part, kind, c, hs, glow)
        made = [part.finish(g, bevel=0.0012)]
        self.export(made, "utility_" + kind)
        self.drop(made)

    def utility_piece(self, part, kind, c, hs, glow):
        def at(x, y, z):
            return c + Vector((x * hs.x, y * hs.y, z * hs.z))

        def ring(centre, u, v, R, r, m, n=32):
            rows = []
            for i in range(n):
                a = 2 * math.pi * i / n
                p, out = centre + (u * math.cos(a) + v * math.sin(a)) * R, u * math.cos(a) + v * math.sin(a)
                rows.append([p + (out * math.cos(b) + u.cross(v).normalized() * math.sin(b)) * r
                             for b in (2 * math.pi * j / 8 for j in range(8))])
            part.loft(rows, lambda i, j: m, closed_u=True, closed_v=True)

        r = min(hs.x, hs.z)
        X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
        if kind == "mast":
            part.box(at(0, 0.05, -0.92), (1.7 * hs.x, 1.8 * hs.y, 0.16 * hs.z), "Metal")             # sled
            part.box(at(0, 0.48, -0.25), (1.3 * hs.x, 0.85 * hs.y, 1.2 * hs.z), "Graphite")           # electronics
            for k in range(3):                                                                        # status lights
                part.box(at(-0.35 + 0.35 * k, 0.48, 0.37), (0.18 * hs.x, 0.6 * hs.y, 0.05 * hs.z), glow)
            part.cyl(at(0, -0.30, -0.84), at(0, -0.30, -0.10), 0.22 * r, "Metal", 12)                  # turning post
            head = at(0, -0.55, 0.05)
            part.cyl(head + Y * 0.02, head - Y * 0.03, 0.92 * r, "Metal_Bright", 24)                  # the dish
            ring(head - Y * 0.035, X, Z, 0.92 * r, 0.012, glow)                                       # glowing rim
            part.sphere(head - Y * 0.05, 0.18 * r, glow, segs=12, rings=6)                            # emitter
            for dx in (-0.25, 0.25):
                part.tube([at(dx, 0.05, 0.0), at(dx, -0.25, 0.05), head + X * (dx * hs.x) + Y * 0.04], 0.010,
                          "Black", 6)
        elif kind == "dome":                    # the route oracle: a glowing data core lying along the nose
            part.box(at(0, 0, -0.84), (1.5 * hs.x, 1.6 * hs.y, 0.30 * hs.z), "Graphite")              # base block
            for k in range(8):                                                                        # heat fins
                part.box(at(0, -0.7 + 0.2 * k, -0.58), (1.3 * hs.x, 0.04 * hs.y, 0.26 * hs.z), "Metal")
            rc = min(0.62 * hs.z, 0.5 * hs.x)
            a, b = at(0, -0.62, 0.22), at(0, 0.62, 0.22)
            part.cyl(a, b, rc, glow, 20)                                                              # the core
            part.sphere(a, rc, glow, segs=20, rings=10)
            part.sphere(b, rc, glow, segs=20, rings=10)
            for f, m in ((-0.42, "Metal_Bright"), (0.0, "Gold"), (0.42, "Metal_Bright")):             # gimbal bands
                ring(at(0, f, 0.22), X, Z, rc + 0.012, 0.009, m)
            for f in (-0.42, 0.42):                                                                   # cradle
                part.box(at(0, f, -0.42), (0.25 * hs.x, 0.08 * hs.y, 0.55 * hs.z), "Metal")
        else:
            for dx in (-0.62, 0.62):                                                                  # launch rails
                part.box(at(dx, 0, -0.9), (0.12 * hs.x, 1.9 * hs.y, 0.12 * hs.z), "Metal")
            body = at(0, 0, -0.25)
            part.box(body, (0.70 * hs.x, 1.0 * hs.y, 0.55 * hs.z), self.accent)
            part.box(at(0, 0, 0.04), (0.5 * hs.x, 0.7 * hs.y, 0.06 * hs.z), self.edge)                 # top cover
            part.box(at(0, -0.52, -0.25), (0.36 * hs.x, 0.05 * hs.y, 0.22 * hs.z), glow)              # the eye
            rr = 0.34 * min(hs.x, hs.y)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    hub = at(0.62 * sx, 0.58 * sy, -0.10)
                    part.tube([body + Vector((0.2 * sx * hs.x, 0.3 * sy * hs.y, 0)), hub], 0.012, "Graphite", 6)
                    part.cyl(hub, hub + Z * (0.06 * hs.z), rr, "Graphite", 20)                        # rotor
                    ring(hub + Z * (0.07 * hs.z), X, Y, rr, 0.006, glow, 24)                          # its guard
                    part.cyl(hub + Z * (0.06 * hs.z), hub + Z * (0.10 * hs.z), 0.18 * rr, "Metal_Bright", 10)
            for dy in (-0.95, 0.95):                                                                  # the hatch
                part.box(at(0, dy, 0.92), (1.9 * hs.x, 0.06 * hs.y, 0.10 * hs.z), "Metal")
            for dx in (-0.95, 0.95):
                part.box(at(dx, 0, 0.92), (0.06 * hs.x, 1.9 * hs.y, 0.10 * hs.z), "Metal")

    # ------------------------------------------------------------ the list for the game
    # ------------------------------------------------------------ 7. epic and legendary designs, of their own
    # Player, 2026-11-01: an epic or a legendary is not the common piece with gold and lights stuck on ("brega"): each
    # has a design of its own, recognisable on the track, in the ship's own paint, from real aerodynamics:
    # - wings: the epic a two-element slotted wing (a main plane and a flap behind it with a gap, as on race cars);
    #   the legendary a box wing (Prandtl's "best wing system": a lower and an upper wing joined at the tips by a fin);
    # - tails: the epic a V (butterfly) tail, the legendary a T tail;
    # - body kits: the epic an aero kit (canards on the nose corners, a blade along each flank, a splitter); the
    #   legendary a streamliner (sweeping side fairings running on past the stern, like a Le Mans longtail);
    # - cooling, in the bodywork like every cooling module now: the epic long gills and NACA ducts with carbon
    #   surrounds, the legendary a long flank channel with fins deep inside and a perforated outlet;
    # - engines change inside only (the x-ray view) and, outside, in their flame or plasma (EXMeta::Flame): the epic
    #   with a regenerative tube-wall jacket, cables and cyan neon, the legendary with a helical jacket and neon in the
    #   ship's colour, all inside the bodywork (engine_tier).
    # Exported as <family>_ep / <family>_lg (wing, tail, armor, cooling, engine); AEXHoverCraft fits them for an
    # epic / legendary item of that family (the engine's in the x-ray view only).
    @staticmethod
    def foil(le, te, mid, th, camber=0.0, pitch=0.0, n=8):
        """An aerofoil from le to te along y round height mid (NACA 4-digit thickness th in metres, a light camber,
        the trailing edge raised by 'pitch'): a closed loop of 2n (y, z), the top first from the leading edge."""
        c = te - le
        us = [0.004 + 0.996 * (1 - math.cos(math.pi * k / n)) / 2 for k in range(n + 1)]

        def half(u):
            return 5 * th * (0.2969 * math.sqrt(u) - 0.126 * u - 0.3516 * u ** 2 + 0.2843 * u ** 3 - 0.1036 * u ** 4)

        def line(u):
            return mid + camber * c * 4 * u * (1 - u) + pitch * u

        return [(le + u * c, line(u) + half(u)) for u in us] + [(le + u * c, line(u) - half(u)) for u in reversed(us[1:-1])]

    @staticmethod
    def plate(part, pts, th, m):
        """A flat plate th thick over the outline pts (3D, in one plane)."""
        pts = [Vector(p) for p in pts]
        n = (pts[1] - pts[0]).cross(pts[-1] - pts[0]).normalized()
        part.loft([[p + n * th / 2 for p in pts], [p - n * th / 2 for p in pts]], lambda i, j: m, closed_u=True, cap0=m, cap1=m)

    def foil_mats(self, top, bottom, le, n=8):
        return lambda i, j: le if j in (0, 2 * n - 1) else (top if j < n else bottom)

    # ---- cooling in the bodywork: flush patches that hug the hull (gills, NACA ducts, intakes, louvres)
    def hull_sheet(self, part, s, uv, nu, nv, lift, m, top=False, closed=False, mode=None):
        """A thin sheet hugging the hull 'lift' off it: uv(u, v) -> (y, z) on side s, or (x, y) on the deck (top);
        mode 'inner': on the inside face of side s, seen from the centre line (between a fork's prongs)."""
        rows = []
        for i in range(nv + 1):
            row = []
            for j in range(nu + (0 if closed else 1)):
                a, b = uv(j / nu, i / nv)
                if top:
                    loc, nor = self.top_hit(a, b)
                elif mode == "inner":
                    loc, nor = self.hit((0.0, a, b), (s, 0, 0), 4.0)
                else:
                    loc, nor = self.side_hit(s, a, b)
                if loc is None:
                    return False
                if (nor.z < 0) if top else ((nor.x * s > 0) if mode == "inner" else (nor.x * s < 0)):
                    nor = -nor
                row.append(loc + nor * lift)
            rows.append(row)
        part.loft(rows, lambda i, j: m, closed_u=closed)
        return True

    def band(self, s, ys, step=0.02):
        """The tallest run of hull side, in z, that every y in ys has (rays that slip deep into a gap don't count)."""
        zs = np.arange(self.z_low + 0.01, self.z_high, step)
        ok = np.ones(len(zs), bool)
        for y in ys:
            xs_ = np.array([self.side_x(s, y, z) or 0.0 for z in zs])
            ok &= xs_ > 0.2 * xs_.max() if xs_.max() > 0 else np.zeros(len(zs), bool)
        best, run = None, None
        for z, f in zip(zs, ok):
            run = ((run[0] if run else z), z) if f else None
            if run and (best is None or run[1] - run[0] > best[1] - best[0]):
                best = run
        return best

    def gills(self, part, s, yc, zc, n, length, pitch, surround=None, lip=None, mode=None):
        """n slanted gill slits on the side s round (yc, zc), dark inside, a lip on each trailing edge; fitted into
        the tallest run of flank there."""
        sl = math.tan(math.radians(24))
        w = 0.022 * self.scale
        hs = length + 0.05
        if mode != "inner":
            ext = n * pitch / 2 + length * sl / 2 + 0.04
            b = self.band(s, (yc - ext, yc, yc + ext))
            if b is None or b[1] - b[0] < 0.06:
                return
            length = min(length, 0.8 * (b[1] - b[0]))
            hs = min(length + 0.05, 0.96 * (b[1] - b[0]))
            zc = min(max(zc, b[0] + hs / 2), b[1] - hs / 2)
        if surround:
            self.hull_sheet(part, s, lambda u, v: (yc + (u - 0.5) * (n * pitch + 0.06) + (v - 0.5) * length * sl,
                                                   zc + (v - 0.5) * hs), 6, 3, 0.0012, surround, mode=mode)
        for k in range(n):
            y = yc + (k - (n - 1) / 2) * pitch
            self.hull_sheet(part, s, lambda u, v, y=y: (y + (u - 0.5) * w + (v - 0.5) * length * sl, zc + (v - 0.5) * length),
                            1, 4, 0.0022, "Black", mode=mode)
            self.hull_sheet(part, s, lambda u, v, y=y: (y + w / 2 + u * 0.007 + (v - 0.5) * length * sl, zc + (v - 0.5) * length),
                            1, 4, 0.0045, lip or self.edge, mode=mode)

    def naca(self, part, xc, y_f, length, w0, w1, lip=None):
        """A NACA duct on the deck: narrow in front, opening to the rear, flush, dark inside, sharp lips."""
        def half(v):
            return w0 + (w1 - w0) * (3 * v * v - 2 * v ** 3)
        self.hull_sheet(part, 0, lambda u, v: (xc + (u - 0.5) * 2 * half(v), y_f + v * length), 2, 8, 0.0022, "Black", top=True)
        for e in (0, 1):
            self.hull_sheet(part, 0, lambda u, v, e=e: (xc + (e - 0.5) * 2 * half(v) + (e - 0.5) * 2 * u * 0.006, y_f + v * length),
                            1, 8, 0.0045, lip or self.edge, top=True)
        self.hull_sheet(part, 0, lambda u, v: (xc + (u - 0.5) * 2 * w1, y_f + length + v * 0.01), 4, 1, 0.007, lip or self.edge,
                        top=True)

    def louvres(self, part, s, uv_box, n, slat, top=False, base="Black"):
        """A field of n louvre slats over a dark panel; uv_box(u, v) maps the panel."""
        self.hull_sheet(part, s, uv_box, 4, 4, 0.0018, base, top=top)
        for k in range(n):
            v0 = (k + 0.25) / n
            self.hull_sheet(part, s, lambda u, v, v0=v0: uv_box(0.04 + 0.92 * u, v0 + v * 0.45 / n), 4, 1, 0.005, slat, top=top)

    def cooling_site(self):
        """Where the cooling goes: the socket's y kept behind the canopy, the flank height and the deck's half width."""
        c = self.sock.get("Socket_Cooling")
        if c is None:
            return None
        y = max(c.y, self.canopy_y1 + 0.12)
        span = self.side_span(1, y)
        mid = (span[0] + span[1]) / 2 if span else c.z
        half = self.side_x(1, y, mid) or 0.4
        return c, y, span, half

    def cooling(self, kind):
        """Cooling in the bodywork (player, 2026-11-01: the square radiators on the deck spoilt the lines and the
        aerodynamics): vents are gills in the flanks, the radiator two NACA ducts on the deck with louvred outlets,
        the grid flush side intakes and a louvred outlet; dark inside, sharp lips, nothing standing up."""
        site = self.cooling_site()
        if site is None:
            return
        c, y, span, half = site
        sc = self.scale
        g = self.group("Module_Cooling_" + kind)
        part = K.Part("Cooling_" + kind.capitalize())
        if kind == "vents" and span:
            for s in (-1, 1):
                self.gills(part, s, y, span[0] + 0.62 * (span[1] - span[0]), 4, 0.16 * sc, 0.07 * sc)
        elif kind == "radiator":
            for s in (-1, 1):
                xc = s * half * 0.42
                self.naca(part, xc, y - 0.20 * sc, 0.48 * sc, 0.022, 0.11 * sc)
                self.louvres(part, 0, lambda u, v, xc=xc: (xc + (u - 0.5) * 0.20 * sc, y + 0.40 * sc + v * 0.16 * sc), 4,
                             self.main, top=True)
        elif kind == "grid" and span:
            zc = span[0] + 0.40 * (span[1] - span[0])
            for s in (-1, 1):
                a, b = 0.22 * sc, 0.055 * sc
                self.hull_sheet(part, s, lambda u, v: (y + a * v * math.cos(2 * math.pi * u), zc + b * v * math.sin(2 * math.pi * u)),
                                24, 3, 0.0022, "Black", closed=True)
                self.hull_sheet(part, s, lambda u, v: (y + a * (1.0 + 0.10 * v) * math.cos(math.pi * (0.1 + 0.8 * u)),
                                                       zc + b * (1.0 + 0.25 * v) * math.sin(math.pi * (0.1 + 0.8 * u))), 12, 1, 0.006,
                                self.edge)
            self.louvres(part, 0, lambda u, v: ((u - 0.5) * 0.46 * sc, y + 0.55 * sc + v * 0.28 * sc), 7, self.main, top=True)
        made = [part.finish(g, bevel=0.0, smooth_angle=30)] if part.bm.faces else []
        self.export(made, "cooling_" + kind)
        self.drop(made)

    def world_verts(self, objs):
        dg = bpy.context.evaluated_depsgraph_get()
        pts = []
        for o in objs:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            pts.extend(tuple(o.matrix_world @ v.co) for v in me.vertices)
            ev.to_mesh_clear()
        return np.array(pts, float) if pts else np.zeros((0, 3))

    # Each ship has its own epics and legendaries, grown from its own chassis (player, 2026-11-01: "cada nave tem de
    # ter o seu próprio módulo épico e lendário conforme a sua estrutura"): (epic, legendary) design per family.
    TIER_DESIGNS = {
        # VORTEX keeps the first set, drawn on it (initial_*). (The engines are dressed on each chassis's own:
        # engine_tier.)
        "VORTEX": dict(wing=("initial", "initial"), tail=("initial", "initial"), armor=("initial", "initial"),
                       cooling=("initial", "initial")),
        # BASTION, the heavy capsule in a flat wing with the colossal flat engine: a slab wing with a slat / a box wing;
        # twin outboard fins / three fins; side shields / carapace skirts and a ram; big NACA ducts / a fan of louvres.
        "BASTION": dict(wing=("slab", "box"), tail=("outboard2", "triple"), armor=("shields", "carapace"),
                        cooling=("naca_big", "fan")),
        # STRIX, the needle with the down-swept delta and two stacked engines (redone, player 2026-11-01: "very
        # odd"): a cranked double delta / a Concorde-like ogee wing; swept tailplanes / anhedral tailplanes (F-4);
        # leading-edge root extensions / LERX with the needle sleeve and fairings; a louvred deck panel / three NACA
        # ducts.
        "STRIX": dict(wing=("cranked", "ogival"), tail=("tailplanes", "anhedral"), armor=("lerx", "needle_lerx"),
                      cooling=("deck_louvres", "naca3")),
        # WRAITH, the fork with the cockpit pod between its prongs and three engines: a scimitar wing / tandem wings;
        # twin fins at the corners / an H tail; blades on the prongs / a bridge between the prongs; gills inside the
        # fork / channels along the prongs.
        "WRAITH": dict(wing=("scimitar", "tandem"), tail=("corner2", "aitch"), armor=("prong_blades", "bridge"),
                       cooling=("inner_gills", "prong_channels")),
        # NOMAD, the dropship with pods on its arms: a long wing with sharklets / a swept wing with tip pods; fins on
        # the pods / a Y tail; nose cones on the pods / cones and boat tails; scoops on the pods / perforated pods.
        "NOMAD": dict(wing=("sharklet", "tip_pods"), tail=("pod_fins", "wye"), armor=("pod_cones", "pod_tails"),
                      cooling=("pod_scoops", "pod_perf")),
    }

    def design(self, family, leg):
        d = self.TIER_DESIGNS.get(K.NAME.upper(), self.TIER_DESIGNS["VORTEX"])
        return d[family][1 if leg else 0]

    def tier_pieces(self):
        # written out so Scripts/make_ship_materials.py finds them (it reads the ensure_mat calls)
        ensure_mat("Carbon_Tier", "#1C1C21", metal=0.25, rough=0.30)
        ensure_mat("Titanium", "#8E939A", metal=1.0, rough=0.34)
        ensure_mat("Ceramic_Dark", "#3A3633", rough=0.7)
        ensure_mat("Emit_HotDim", "#FF7A2E", rough=0.4, emit=1.4)
        ensure_mat("Copper_Coil", "#C8743A", metal=1.0, rough=0.3)
        print("TIER %s pods %s" % (K.NAME, {k: [round(v, 2) for v in p] for k, p in self.pods().items()}))
        for leg in (False, True):
            for family in ("wing", "tail", "armor", "cooling", "engine"):
                getattr(self, family + "_tier")(leg)

    # ---- the first epic / legendary set, drawn on the VORTEX (player, 2026-11-01: "the VORTEX can keep the first epic
    # and legendary set, I only asked that the others vary"): a slotted two-element wing / a Prandtl box wing, a V tail /
    # a T tail, an aero kit / a streamliner, long gills and NACA ducts / a flank channel and a perforated outlet.
    def initial_wing(self, leg):
        ns = self.ns
        if not self.wings or "wing_at" not in ns:
            return
        WING, stock_at = ns["WING"], ns["wing_at"]
        x0 = (ns.get("WING_X") or [r[0] for r in WING])[0]
        x1 = WING[-1][0]
        r0 = stock_at(x0)
        side, _ = self.side_hit(1, (r0[0] + r0[1]) / 2, r0[2] + 0.06)
        hull_x = abs(side.x) if side is not None else x0 + 0.10
        xs = max(x0 + 0.06, min(hull_x + 0.04, x0 + 0.5 * (x1 - x0)))
        les, tes, mids, ths = stock_at(xs)
        let, tet, midt, tht = stock_at(x1)
        if leg:      # box wing: the lower wing swept back a little more, joined to the upper one by a fin
            xt, tle, tch, anf, tth = xs + (x1 - xs) * 1.12, les + (let - les) * 1.30, (tet - let) * 0.80, 0.45, tht * 0.9
        else:        # slotted wing: a longer main plane, a flap over its trailing edge
            xt, tle, tch, anf, tth = xs + (x1 - xs) * 1.30, les + (let - les) * 1.15, (tet - let) * 0.72, 0.6, tht * 0.85
        tte = tle + tch
        tmid = mids - (xt - xs) * math.tan(math.atan2(mids - midt, x1 - xs) * anf)

        def at(x):
            if x <= xs:
                return stock_at(x)
            f = min(1.0, (x - xs) / (xt - xs))
            return les + (tle - les) * f, tes + (tte - tes) * f, mids + (tmid - mids) * f, ths + (tth - ths) * f

        made = []
        stations = [x0 - 0.02, xs] + [xs + (xt - xs) * k / 6 for k in range(1, 7)]
        for s, sd in ((1, "R"), (-1, "L")):
            g = self.group("Module_Wing_%s_%s" % ("lg" if leg else "ep", sd))
            part = K.Part("Wing_%s_%s" % ("Box" if leg else "Slotted", sd))
            part.loft([[Vector((s * x, y, z)) for y, z in self.foil(*at(x), camber=0.015)] for x in stations],
                      self.foil_mats(self.main, "Graphite", self.edge), closed_u=True, cap0=self.edge, cap1=self.edge)
            if not leg:
                rows = []
                for k in range(6):
                    x = xs + 0.05 + (xt - 0.03 - xs - 0.05) * k / 5
                    le, te, mid, th = at(x)
                    fc = 0.36 * (te - le)
                    fle = te - 0.14 * fc
                    rows.append([Vector((s * x, y, z)) for y, z in self.foil(fle, fle + fc, mid + 0.6 * th + 0.03, 0.11 * fc,
                                                                              camber=0.05, pitch=0.03)])
                part.loft(rows, self.foil_mats(self.accent, "Carbon_Tier", self.edge), closed_u=True, cap0=self.edge,
                          cap1=self.edge)
                le, te, mid, th = at(xt)
                c = te - le
                ztop = mid + 0.6 * th + 0.03 + 0.11 * c
                xp = s * (xt + 0.008)
                self.plate(part, [(xp, le + 0.05 * c, mid - th * 0.8 - 0.03), (xp, te + 0.34 * c, mid - th * 0.5 - 0.02),
                                  (xp, te + 0.40 * c, ztop + 0.07), (xp, le + 0.48 * c, mid + 0.10)], 0.014, self.edge)
                self.plate(part, [(xp + s * 0.008, le + 0.50 * c, mid + 0.075), (xp + s * 0.008, te + 0.34 * c, ztop + 0.045),
                                  (xp + s * 0.008, te + 0.36 * c, ztop + 0.055), (xp + s * 0.008, le + 0.50 * c, mid + 0.088)],
                           0.004, self.accent)
            else:
                H = 0.34 * self.scale
                fle_t = tle + 0.30 * tch
                fte_t = fle_t + 0.85 * tch
                rows = []
                for k in range(6):                       # the tip fin, a vertical aerofoil from wing to wing
                    f = k / 5
                    le_, te_ = tle + (fle_t - tle) * f, tte + (fte_t - tte) * f
                    rows.append([Vector((s * xt + s * v, y, tmid + H * f)) for y, v in self.foil(le_, te_, 0.0, 0.11 * (te_ - le_))])
                part.loft(rows, self.foil_mats(self.edge, self.edge, self.edge), closed_u=True, cap0=self.edge, cap1=self.edge)
                yc_r = (les + tes) / 2 + 0.45 * (tes - les)
                xr = zr = None
                for k in range(14):                      # the upper wing's root: on the hull side, up the flank
                    zr = mids + H * 0.85 - 0.03 * k
                    xr = self.side_x(s, yc_r, zr)
                    if xr is not None:
                        break
                if xr is None or zr < mids + 0.10:       # a low hull: the upper wing stands on the deck's shoulder
                    xr, zr = None, None
                    for f in (0.70, 0.60, 0.50, 0.40):
                        loc, _ = self.top_hit(s * hull_x * f, yc_r)
                        if loc is not None:
                            xr, zr = abs(loc.x), loc.z - 0.01
                            break
                if xr is not None:
                    c_r = 0.9 * (tes - les)
                    rows = []
                    for k in range(6):
                        f = k / 5
                        x = xr - 0.02 + (xt - (xr - 0.02)) * f
                        le_ = (yc_r - c_r / 2) + (fle_t - (yc_r - c_r / 2)) * f
                        te_ = (yc_r + c_r / 2) + (fte_t - (yc_r + c_r / 2)) * f
                        z = zr + (tmid + H - zr) * f
                        th = 0.8 * ths + (0.8 * tth - 0.8 * ths) * f
                        rows.append([Vector((s * x, y, zz)) for y, zz in self.foil(le_, te_, z, th, camber=0.015)])
                    part.loft(rows, self.foil_mats(self.accent, "Graphite", self.edge), closed_u=True, cap0=self.edge,
                              cap1=self.edge)
                    part.tube([Vector((s * (xr + 0.02 + (xt - xr - 0.06) * f), (yc_r + c_r / 2) + (fte_t - (yc_r + c_r / 2)) * f + 0.004,
                                       zr + (tmid + H - zr) * f)) for f in (0.0, 0.5, 1.0)], 0.004, "Emit_Hover", 6)
            made.append(part.finish(g, bevel=0.0015, smooth_angle=40))
        self.export(made, "wing_lg" if leg else "wing_ep")
        self.drop(made)


    def initial_tail(self, leg):
        c = self.sock.get("Socket_Tail")
        if c is None:
            return
        below = self.tail == "below"
        sc, y_end, up = self.scale, c.y, (-1.0 if below else 1.0)

        def base_fn(x):
            def f(y):
                loc, _ = self.top_hit(x, y, below)
                if loc is None:
                    loc, _ = self.top_hit(x, y_end - 0.6, below)
                return loc.z if loc is not None else c.z
            return f

        g = self.group("Module_Tail_" + ("lg" if leg else "ep"))
        part = K.Part("Tail_" + ("T" if leg else "V"))
        if not leg:              # V tail: two fins from the centre line, 38 degrees out each
            for s in (-1, 1):
                cant = math.pi - math.radians(38) if below else math.radians(38)
                K.shark_fin(part, base_fn(s * 0.03), s * 0.03, (y_end - 1.00 * sc, y_end - 0.05), (y_end - 0.42 * sc, y_end + 0.10),
                            0.50 * sc, 0.042, self.main, "Carbon_Tier", cant, s)
            f = base_fn(0.0)
            part.tube([Vector((0, y, f(y) + 0.012 * up)) for y in np.linspace(y_end - 0.95 * sc, y_end - 0.06, 8)], 0.028,
                      self.edge, 10)
        else:                    # T tail: a tall fin, a swept stabiliser on top, a titanium bullet at the joint
            root, tip, height = (y_end - 1.25 * sc, y_end - 0.02), (y_end - 0.50 * sc, y_end + 0.12), 0.58 * sc
            K.shark_fin(part, base_fn(0.0), 0.0, root, tip, height, 0.05, self.main, self.edge, math.pi if below else 0.0, 1)
            le_t, te_t = tip[0] + 0.4 * (tip[1] - tip[0]), tip[1] - 0.35 * (tip[1] - tip[0])
            ztop = base_fn(0.0)((le_t + te_t) / 2) - 0.01 + up * height
            S = 0.46 * sc
            rows = []
            for x in (-S, -0.5 * S, 0.0, 0.5 * S, S):
                f = abs(x) / S
                cc = (0.40 - 0.20 * f) * sc
                le = le_t - 0.12 * sc + 0.20 * sc * f
                rows.append([Vector((x, y, z)) for y, z in self.foil(le, le + cc, ztop - up * 0.04 * sc * f, 0.10 * cc)])
            part.loft(rows, self.foil_mats(self.accent, "Graphite", self.edge), closed_u=True, cap0=self.edge, cap1=self.edge)
            part.lathe((0, le_t - 0.14 * sc, ztop), (0, te_t + 0.12 * sc, ztop), [(0, 0.0), (0.15, 0.028), (0.6, 0.036), (1, 0.0)],
                       lambda k: "Titanium", 20)
        made = [part.finish(g, bevel=0.0015, smooth_angle=50)]
        self.export(made, "tail_lg" if leg else "tail_ep")
        self.drop(made)


    def initial_armor(self, leg):
        g = self.group("Module_Armor_" + ("lg" if leg else "ep"))
        part = K.Part("Armor_" + ("Streamliner" if leg else "Aero"))
        sc, L = self.scale, self.y_max - self.y_min
        if not leg:
            for s in (-1, 1):
                for k, fy in enumerate((0.10, 0.17)):       # two canards on each nose corner
                    y = self.y_min + fy * L
                    span = self.side_span(s, y)
                    if not span:
                        continue
                    z = span[0] + 0.40 * (span[1] - span[0])
                    x = self.side_x(s, y, z)
                    if x is None:
                        continue
                    w = (0.15 - 0.03 * k) * sc
                    self.plate(part, [(s * (x - 0.01), y - 0.09 * sc, z), (s * (x + w), y - 0.02 * sc, z + 0.035),
                                      (s * (x + w), y + 0.03 * sc, z + 0.035), (s * (x - 0.01), y + 0.07 * sc, z)], 0.012, self.accent)
                rows = []                                    # a sharp blade along the flank
                ys = np.linspace(self.y_min + 0.24 * L, self.y_max - 0.10 * L, 26)
                for i, y in enumerate(ys):
                    span = self.side_span(s, y)
                    if not span:
                        continue
                    z = span[0] + 0.45 * (span[1] - span[0])
                    x = self.side_x(s, y, z)
                    if x is None:
                        continue
                    t = i / (len(ys) - 1)
                    out = 0.05 * sc * smooth(t / 0.12) * smooth((1 - t) / 0.2) + 0.004
                    rows.append([Vector((s * (x - 0.006), y, z - 0.022)), Vector((s * (x + out), y, z - 0.004)),
                                 Vector((s * (x + out), y, z + 0.004)), Vector((s * (x - 0.006), y, z + 0.016))])
                if len(rows) > 3:
                    part.loft(rows, lambda i, j: self.edge if j == 1 else self.accent, closed_u=True, cap0=self.accent,
                              cap1=self.accent)
            y0 = self.y_min + 0.08 * L                       # a splitter under the nose
            fp = self.footprint(y0)
            if fp:
                xs_ = [p[0] for b in fp for p in b]
                zb = min(p[1] for b in fp for p in b)
                w, xc = (max(xs_) - min(xs_)) / 2 * 0.95, (max(xs_) + min(xs_)) / 2
                self.plate(part, [(xc - w, y0 + 0.10, zb - 0.006), (xc + w, y0 + 0.10, zb - 0.006),
                                  (xc + 0.8 * w, self.y_min - 0.10 * sc, zb + 0.004), (xc - 0.8 * w, self.y_min - 0.10 * sc, zb + 0.004)],
                           0.014, self.edge)
        else:
            for s in (-1, 1):
                ys = np.linspace(self.y_min + 0.20 * L, self.y_max - 0.02, 30)
                prof = []
                for i, y in enumerate(ys):
                    span = self.side_span(s, y)
                    if not span:
                        continue
                    t = i / (len(ys) - 1)
                    zlo, ztop = span[0] + 0.01, span[0] + (0.22 + 0.28 * t) * (span[1] - span[0])
                    col = [(self.side_x(s, y, ztop + (zlo - ztop) * k / 6), ztop + (zlo - ztop) * k / 6) for k in range(7)]
                    if any(x is None for x, _ in col):
                        continue
                    prof.append((y, col, 0.05 * sc * smooth(t / 0.18) * (0.6 + 0.4 * t)))
                if len(prof) < 4:
                    continue
                y_l, col_l, off_l = prof[-1]
                for k in range(1, 5):                        # the longtail: on past the stern, closing to a blade
                    f = k / 4
                    top = col_l[0][1]
                    prof.append((y_l + 0.30 * sc * f, [(x, top + (z - top) * (1 - 0.6 * f)) for x, z in col_l], off_l * (1 - 0.85 * f)))
                rows = [[Vector((s * (x + off), y, z)) for x, z in col] + [Vector((s * (x - 0.004), y, z)) for x, z in reversed(col)]
                        for y, col, off in prof]
                n_out = len(prof[0][1])
                part.loft(rows, lambda i, j: self.accent if j == 0 else (self.main if j < n_out - 1 else
                                                                        (self.edge if j == n_out - 1 else "Graphite")),
                          closed_u=True, cap0=self.main, cap1=self.edge)
        made = [part.finish(g, bevel=0.0015, smooth_angle=40)] if part.bm.faces else []
        if made:
            self.export(made, "armor_lg" if leg else "armor_ep")
            self.drop(made)


    def initial_cooling(self, leg):
        site = self.cooling_site()
        if site is None:
            return
        c, y, span, half = site
        sc = self.scale
        g = self.group("Module_Cooling_" + ("lg" if leg else "ep"))
        part = K.Part("Cooling_" + ("Channel" if leg else "Gills"))
        if not leg:
            if span:
                for s in (-1, 1):
                    self.gills(part, s, y + 0.05 * sc, span[0] + 0.58 * (span[1] - span[0]), 6, 0.22 * sc, 0.075 * sc,
                               surround="Carbon_Tier", lip="Titanium")
            for s in (-1, 1):
                self.naca(part, s * half * 0.40, y - 0.25 * sc, 0.55 * sc, 0.022, 0.12 * sc, lip="Carbon_Tier")
        else:
            if span:
                zc = span[0] + 0.55 * (span[1] - span[0])
                Lc, hc = 0.85 * sc, 0.045 * sc
                for s in (-1, 1):
                    def box(u, v, zc=zc):
                        return y + (u - 0.5) * Lc, zc + (v - 0.5) * hc + (u - 0.5) * 0.03
                    self.hull_sheet(part, s, box, 12, 2, 0.0022, "Black")
                    self.hull_sheet(part, s, lambda u, v: box(0.03 + 0.94 * u, 0.42 + 0.16 * v), 12, 1, 0.0026, "Emit_HotDim")
                    for k in range(12):                      # fins deep inside the channel
                        self.hull_sheet(part, s, lambda u, v, k=k: box((k + 0.5) / 12 + (u - 0.5) * 0.006, 0.1 + 0.8 * v), 1, 1,
                                        0.0034, "Titanium")
                    self.hull_sheet(part, s, lambda u, v: box(u, 1.0 + v * 0.18), 12, 1, 0.005, self.edge)
            px, py = 0.40 * sc, 0.26 * sc                    # a perforated titanium outlet on the deck
            if self.hull_sheet(part, 0, lambda u, v: ((u - 0.5) * px, y + 0.50 * sc + v * py), 4, 4, 0.0018, "Titanium", top=True):
                for i in range(6):
                    for j in range(14):
                        cx, cy = (j + 0.5) / 14, (i + 0.5) / 6
                        self.hull_sheet(part, 0, lambda u, v, cx=cx, cy=cy: ((cx - 0.5 + (u - 0.5) * 0.035) * px,
                                                                            y + 0.50 * sc + (cy + (v - 0.5) * 0.09) * py),
                                        1, 1, 0.0026, "Black", top=True)
        made = [part.finish(g, bevel=0.0, smooth_angle=30)] if part.bm.faces else []
        if made:
            self.export(made, "cooling_lg" if leg else "cooling_ep")
            self.drop(made)


    # ---- shared helpers for the designs
    def half_at(self, y):
        span = self.side_span(1, y)
        if not span:
            return 0.4
        xs_ = [self.side_x(1, y, span[0] + (span[1] - span[0]) * k / 8) for k in range(9)]
        xs_ = [x for x in xs_ if x is not None]
        return max(xs_) if xs_ else 0.4

    def widest(self, s, y):
        span = self.side_span(s, y)
        if not span:
            return None
        best = None
        for z in np.linspace(span[0], span[1], 12):
            x = self.side_x(s, y, z)
            if x is not None and (best is None or x > best[0]):
                best = (x, z)
        return best

    def wedge_line(self, part, s, pts, out_max, th, m_body, m_edge, taper=(0.12, 0.2)):
        """A sharp strake along the hull through pts [(hull x, y, z)], reaching out_max, tapered at both ends."""
        rows = []
        for i, (x, y, z) in enumerate(pts):
            t = i / max(1, len(pts) - 1)
            out = out_max * smooth(t / taper[0]) * smooth((1 - t) / taper[1]) + 0.004
            rows.append([Vector((s * (x - 0.006), y, z - th)), Vector((s * (x + out), y, z - 0.003)),
                         Vector((s * (x + out), y, z + 0.003)), Vector((s * (x - 0.006), y, z + 0.7 * th))])
        if len(rows) > 3:
            part.loft(rows, lambda i, j: m_edge if j == 1 else m_body, closed_u=True, cap0=m_body, cap1=m_body)

    def flank_line(self, s, y0, y1, fz, n=26):
        """Hull points along side s from y0 to y1 at fraction fz of the side's height."""
        pts = []
        for y in np.linspace(y0, y1, n):
            span = self.side_span(s, y)
            if not span:
                continue
            z = span[0] + fz * (span[1] - span[0])
            x = self.side_x(s, y, z)
            if x is not None:
                pts.append((x, y, z))
        return pts

    def chine_line(self, s, y0, y1, n=30):
        pts = []
        for y in np.linspace(y0, y1, n):
            w = self.widest(s, y)
            if w:
                pts.append((w[0], y, w[1]))
        return pts

    def bodies_at(self, y):
        """The hull's separate bodies across y: (centre x, half width, underside z), from the footprint."""
        out = []
        for b in self.footprint(y):
            xs_, zs_ = [p[0] for p in b], [p[1] for p in b]
            out.append(((min(xs_) + max(xs_)) / 2, (max(xs_) - min(xs_)) / 2, min(zs_)))
        return out

    def outer_bodies(self, y0f, y1f, n=36, min_x=0.25):
        """Bodies off the centre line (pods, prongs) between fractions y0f..y1f of the length: per side,
        [x, half width, underside z, front y, back y]."""
        L = self.y_max - self.y_min
        seen = {}
        for y in np.linspace(self.y_min + y0f * L, self.y_min + y1f * L, n):
            for b in self.bodies_at(y):
                if abs(b[0]) < min_x:
                    continue
                k = 1 if b[0] > 0 else -1
                e = seen.setdefault(k, [b[0], b[1], b[2], y, y])
                e[3], e[4] = min(e[3], y), max(e[4], y)
                e[0], e[1], e[2] = (e[0] + b[0]) / 2, max(e[1], b[1]), min(e[2], b[2])
        return seen

    def pods(self):
        """Pods or prongs off the centre line, per side [x, half width, underside z, front y, back y, centre z]: from
        the footprint, or from the side engines when the pods hang on arms (they join the hull in the footprint)."""
        pods = self.outer_bodies(0.15, 0.95)
        if pods:
            return pods
        out = {}
        for c, r, yf, Lc, Re, hx, hz in self.engines():
            if abs(c.x) < 0.25:
                continue
            s = 1 if c.x > 0 else -1
            y0 = c.y                                       # forward along the pod's outer face while it lasts
            for y in np.arange(c.y - 0.05, self.y_min, -0.05):
                so, _ = self.side_hit(s, y, c.z)
                if so is None or abs(so.x) < abs(c.x):
                    break
                y0 = float(y)
            ym = (y0 + c.y) / 2
            so, _ = self.side_hit(s, ym, c.z)
            lo, _ = self.top_hit(c.x, ym, below=True)
            out[s] = [c.x, abs(so.x) - abs(c.x) if so is not None else hx, lo.z if lo is not None else c.z - hz, y0, c.y, c.z]
        return out

    def nose_point(self):
        L = self.y_max - self.y_min
        span = self.side_span(1, self.y_min + 0.02 * L)
        return Vector((0.0, self.y_min, (span[0] + span[1]) / 2 if span else (self.z_low + self.z_high) / 2))

    # ---- wings
    def wing_frame(self):
        ns = self.ns
        if not self.wings or "wing_at" not in ns:
            return None
        WING, stock_at = ns["WING"], ns["wing_at"]
        x0 = (ns.get("WING_X") or [r[0] for r in WING])[0]
        x1 = WING[-1][0]
        r0 = stock_at(x0)
        side, _ = self.side_hit(1, (r0[0] + r0[1]) / 2, r0[2] + 0.06)
        hull_x = abs(side.x) if side is not None else x0 + 0.10
        xs = max(x0 + 0.06, min(hull_x + 0.04, x0 + 0.5 * (x1 - x0)))
        les, tes, mids, ths = stock_at(xs)
        let, tet, midt, tht = stock_at(x1)
        return dict(at=stock_at, x0=x0, x1=x1, xs=xs, hull_x=hull_x, les=les, tes=tes, mids=mids, ths=ths, let=let,
                    tet=tet, midt=midt, tht=tht, S=x1 - xs, cr=tes - les, ct=max(tet - let, 0.2))

    def wing_loft(self, part, s, F, outer, top, bottom="Graphite", camber=0.015, root=True):
        """A wing from foil stations [(x, le, te, mid, th)] past the hull side; the root goes through the stock slot."""
        st = [(x,) + tuple(F["at"](x)) for x in (F["x0"] - 0.02, F["xs"])] if root else []
        st += outer
        part.loft([[Vector((s * x, y, z)) for y, z in self.foil(le, te, mid, th, camber)] for x, le, te, mid, th in st],
                  self.foil_mats(top, bottom, self.edge), closed_u=True, cap0=self.edge, cap1=self.edge)

    @staticmethod
    def lerp_st(a, b, f):
        return tuple(p + (q - p) * f for p, q in zip(a, b))

    def wing_tier(self, leg):
        F = self.wing_frame()
        if F is None:
            return
        kind = self.design("wing", leg)
        if kind == "initial":
            return self.initial_wing(leg)
        made = []
        for s, sd in ((1, "R"), (-1, "L")):
            g = self.group("Module_Wing_%s_%s" % ("lg" if leg else "ep", sd))
            part = K.Part("Wing_%s_%s" % (kind.capitalize(), sd))
            getattr(self, "w_" + kind)(part, s, F)
            made.append(part.finish(g, bevel=0.0015, smooth_angle=40))
        self.export(made, "wing_lg" if leg else "wing_ep")
        self.drop(made)

    def w_cranked(self, part, s, F):
        """A cranked delta: a steep inner sweep, a kink, a gentler outer panel, a raked tip folded up."""
        xs, S, cr, ct = F["xs"], F["S"], F["cr"], F["ct"]
        r = (xs, F["les"], F["tes"], F["mids"], F["ths"])
        k = (xs + 0.50 * S, F["les"] + 0.62 * cr, F["tes"] + 0.06 * cr, F["mids"] - 0.03 * S, F["ths"] * 0.8)
        xt = xs + 1.15 * S
        le_t = k[1] + 0.30 * (xt - k[0])
        t = (xt, le_t, le_t + 0.62 * ct, k[3] - 0.05 * S, F["tht"] * 0.8)
        self.wing_loft(part, s, F, [self.lerp_st(r, k, 0.5), k, self.lerp_st(k, t, 0.5), t], self.main)
        c = t[2] - t[1]
        K.shark_fin(part, lambda y: t[3] + t[4] / 2, s * (xt - 0.02), (t[1] + 0.05 * c, t[2]), (t[1] + 0.55 * c, t[2] + 0.06),
                    0.24 * self.scale, 0.024, self.accent, self.edge, math.radians(10), s)

    def w_ogival(self, part, s, F):
        """An ogival wing: the leading edge curving back all along, the tips drooping."""
        xs, S, cr = F["xs"], F["S"], F["cr"]
        out = []
        for f in np.linspace(0.12, 1.0, 9):
            le = F["les"] + cr * 0.95 * f ** 1.7
            chord = cr - (cr - 0.30 * cr) * f ** 1.3
            out.append((xs + 1.18 * S * f, le, le + chord, F["mids"] - 0.16 * S * f ** 2.2, F["ths"] * (1 - 0.55 * f)))
        self.wing_loft(part, s, F, out, self.main)

    def w_slab(self, part, s, F):
        """A short, thick, square slab of a wing with a slat ahead of it and a square end plate: built for knocks."""
        xs, S, cr = F["xs"], F["S"], F["cr"]
        xt = xs + 0.85 * S
        st = [(x, F["les"] + 0.12 * (x - xs), F["les"] + 0.12 * (x - xs) + 0.95 * cr, F["mids"], F["ths"] * (1.35 - 0.2 * (x - xs) / (xt - xs)))
              for x in (xs + 0.2 * (xt - xs), xt)]
        self.wing_loft(part, s, F, st, self.main)
        rows = []
        for x in np.linspace(xs + 0.05, xt - 0.02, 4):
            le = F["les"] + 0.12 * (x - xs)
            c = 0.95 * cr
            rows.append([Vector((s * x, y, z)) for y, z in self.foil(le - 0.22 * c - 0.02, le - 0.02, F["mids"] - 0.02, 0.022 * c * 4 * 0.25,
                                                                      camber=0.06)])
        part.loft(rows, self.foil_mats(self.accent, "Graphite", self.edge), closed_u=True, cap0=self.edge, cap1=self.edge)
        le = F["les"] + 0.12 * (xt - xs)
        c = 0.95 * cr
        xp = s * (xt + 0.01)
        self.plate(part, [(xp, le - 0.26 * c, F["mids"] - 0.10), (xp, le + c + 0.04, F["mids"] - 0.10),
                          (xp, le + c + 0.04, F["mids"] + 0.16), (xp, le - 0.18 * c, F["mids"] + 0.16)], 0.02, self.edge)

    def w_box(self, part, s, F):
        """Prandtl's box wing: a lower wing through the slot, an upper wing from the hull's shoulder, joined at the tips
        by a fin."""
        xs, S, cr, ct = F["xs"], F["S"], F["cr"], F["ct"]
        les, tes, mids, ths = F["les"], F["tes"], F["mids"], F["ths"]
        xt, tle, tch = xs + 1.12 * S, les + (F["let"] - les) * 1.30, ct * 0.80
        tmid = mids - (xt - xs) * math.tan(math.atan2(mids - F["midt"], S) * 0.45)
        tth = F["tht"] * 0.9
        tte = tle + tch
        self.wing_loft(part, s, F, [self.lerp_st((xs, les, tes, mids, ths), (xt, tle, tte, tmid, tth), f) for f in (0.33, 0.66, 1.0)], self.main)
        H = 0.34 * self.scale
        fle_t, fte_t = tle + 0.30 * tch, tle + 0.30 * tch + 0.85 * tch
        rows = []
        for k in range(6):
            f = k / 5
            le_, te_ = tle + (fle_t - tle) * f, tte + (fte_t - tte) * f
            rows.append([Vector((s * xt + s * v, y, tmid + H * f)) for y, v in self.foil(le_, te_, 0.0, 0.11 * (te_ - le_))])
        part.loft(rows, self.foil_mats(self.edge, self.edge, self.edge), closed_u=True, cap0=self.edge, cap1=self.edge)
        yc_r = (les + tes) / 2 + 0.45 * (tes - les)
        xr = zr = None
        for k in range(14):
            zr = mids + H * 0.85 - 0.03 * k
            xr = self.side_x(s, yc_r, zr)
            if xr is not None:
                break
        if xr is None or zr < mids + 0.10:
            xr = zr = None
            for f in (0.70, 0.60, 0.50, 0.40):
                loc, _ = self.top_hit(s * F["hull_x"] * f, yc_r)
                if loc is not None:
                    xr, zr = abs(loc.x), loc.z - 0.01
                    break
        if xr is None:
            return
        c_r = 0.9 * cr
        root, tip = (xr - 0.02, yc_r - c_r / 2, yc_r + c_r / 2, zr, 0.8 * ths), (xt, fle_t, fte_t, tmid + H, 0.8 * tth)
        self.wing_loft(part, s, F, [self.lerp_st(root, tip, f) for f in np.linspace(0, 1, 6)], self.accent, root=False)

    def w_scimitar(self, part, s, F):
        """A scimitar: a crescent, both edges curving back towards a narrow tip."""
        xs, S, cr = F["xs"], F["S"], F["cr"]
        out = []
        for f in np.linspace(0.15, 1.0, 8):
            le = F["les"] + cr * (0.15 * f + 0.85 * f * f)
            out.append((xs + 1.15 * S * f, le, le + cr * (1 - 0.62 * f), F["mids"] - 0.05 * S * f, F["ths"] * (1 - 0.5 * f)))
        self.wing_loft(part, s, F, out, self.main)

    def w_tandem(self, part, s, F):
        """Tandem wings: a slim front wing through the slot and a second one behind it from the hull side, staggered
        and a little lower, like a dragonfly's (the WRAITH's prongs, again)."""
        xs, S, cr = F["xs"], F["S"], F["cr"]
        les, mids, ths = F["les"], F["mids"], F["ths"]
        a = (xs + 0.15 * S, les + 0.05, les + 0.05 + 0.55 * cr, mids + 0.02, ths * 0.8)
        b = (xs + 1.0 * S, les + 0.35 * S, les + 0.35 * S + 0.32 * cr, mids + 0.04, ths * 0.6)
        self.wing_loft(part, s, F, [a, self.lerp_st(a, b, 0.5), b], self.main)
        yc = F["tes"] + 0.25 * cr
        z = mids - 0.05
        xr = self.side_x(s, yc, z)
        if xr is None:
            return
        r2 = (xr - 0.02, yc - 0.25 * cr, yc + 0.25 * cr, z, ths * 0.7)
        t2 = (xr + 0.8 * S, yc - 0.25 * cr + 0.30 * S, yc + 0.10 * cr + 0.30 * S, z - 0.03, ths * 0.5)
        self.wing_loft(part, s, F, [r2, self.lerp_st(r2, t2, 0.5), t2], self.accent, root=False)

    def w_sharklet(self, part, s, F):
        """A long, straight, slender wing with a blended winglet standing on the tip (endurance, the dropship's)."""
        xs, S, cr = F["xs"], F["S"], F["cr"]
        r = (xs, F["les"], F["tes"], F["mids"], F["ths"])
        xt = xs + 1.45 * S
        t = (xt, F["les"] + 0.10 * S, F["les"] + 0.10 * S + 0.45 * cr, F["mids"] + 0.04 * S, F["ths"] * 0.7)
        self.wing_loft(part, s, F, [self.lerp_st(r, t, f) for f in (0.3, 0.65, 1.0)], self.main)
        c = t[2] - t[1]
        K.shark_fin(part, lambda y: t[3] + t[4] / 2, s * (xt - 0.02), (t[1] + 0.10 * c, t[2]), (t[1] + 0.60 * c, t[2] + 0.04),
                    0.26 * self.scale, 0.022, self.accent, self.edge, math.radians(15), s)

    def w_tip_pods(self, part, s, F):
        """A swept, slender wing carrying a pod on each tip (the dropship's long-range tanks)."""
        xs, S, cr = F["xs"], F["S"], F["cr"]
        r = (xs, F["les"], F["tes"], F["mids"], F["ths"])
        xt = xs + 1.30 * S
        t = (xt, F["les"] + 0.45 * S, F["les"] + 0.45 * S + 0.50 * cr, F["mids"] + 0.02 * S, F["ths"] * 0.7)
        self.wing_loft(part, s, F, [self.lerp_st(r, t, f) for f in (0.3, 0.65, 1.0)], self.main)
        R = 0.065 * self.scale
        part.lathe((s * xt, t[1] - 0.18, t[3]), (s * xt, t[2] + 0.28, t[3]),
                   [(0, 0.0), (0.10, R * 0.7), (0.28, R), (0.80, R * 0.92), (1.0, R * 0.25)],
                   lambda k: self.edge if k == 0 else self.accent, 24, cap1=self.edge)

    # ---- tails
    def tail_base(self, x, below):
        c = self.sock["Socket_Tail"]

        def f(y):
            loc, _ = self.top_hit(x, y, below)
            if loc is None:
                loc, _ = self.top_hit(x, c.y - 0.6, below)
            return loc.z if loc is not None else c.z
        return f

    def stabiliser(self, part, x0, x1, le, chord0, chord1, sweep, z, droop):
        """A horizontal aerofoil across x0..x1, its middle chord0, its tips chord1 swept back by 'sweep'."""
        rows = []
        for x in np.linspace(x0, x1, 5):
            f = abs(2 * (x - x0) / (x1 - x0) - 1)
            c = chord0 + (chord1 - chord0) * f
            rows.append([Vector((x, y, zz)) for y, zz in self.foil(le + sweep * f, le + sweep * f + c, z - droop * f, 0.10 * c)])
        part.loft(rows, self.foil_mats(self.accent, "Graphite", self.edge), closed_u=True, cap0=self.edge, cap1=self.edge)

    def tail_tier(self, leg):
        c = self.sock.get("Socket_Tail")
        if c is None:
            return
        kind = self.design("tail", leg)
        if kind == "initial":
            return self.initial_tail(leg)
        g = self.group("Module_Tail_" + ("lg" if leg else "ep"))
        part = K.Part("Tail_" + kind.capitalize())
        getattr(self, "t_" + kind)(part, c, self.tail == "below")
        made = [part.finish(g, bevel=0.0015, smooth_angle=50)]
        self.export(made, "tail_lg" if leg else "tail_ep")
        self.drop(made)

    def fin(self, part, x, below, root, tip, height, thick, skin, edge, cant=0.0, side=1):
        K.shark_fin(part, self.tail_base(x, below), x, root, tip, height, thick, skin, edge,
                    (math.pi - cant) if below else cant, side)

    def t_outboard2(self, part, c, below):
        sc = self.scale
        x = 0.85 * self.half_at(c.y - 0.4 * sc)
        for s in (-1, 1):
            self.fin(part, s * x, below, (c.y - 0.85 * sc, c.y), (c.y - 0.35 * sc, c.y + 0.08), 0.42 * sc, 0.05, self.main, self.edge,
                     math.radians(-10), s)

    def t_triple(self, part, c, below):
        sc = self.scale
        self.fin(part, 0.0, below, (c.y - 1.05 * sc, c.y), (c.y - 0.45 * sc, c.y + 0.10), 0.50 * sc, 0.05, self.main, self.edge)
        x = 0.8 * self.half_at(c.y - 0.4 * sc)
        for s in (-1, 1):
            self.fin(part, s * x, below, (c.y - 0.80 * sc, c.y), (c.y - 0.30 * sc, c.y + 0.06), 0.38 * sc, 0.045, self.accent, self.edge,
                     math.radians(12), s)

    def t_corner2(self, part, c, below):
        sc = self.scale
        x = 0.75 * self.half_at(c.y - 0.4 * sc)
        for s in (-1, 1):
            self.fin(part, s * x, below, (c.y - 0.85 * sc, c.y), (c.y - 0.35 * sc, c.y + 0.08), 0.42 * sc, 0.04, self.main, self.edge,
                     math.radians(20), s)

    def t_aitch(self, part, c, below):
        sc = self.scale
        x = 0.75 * self.half_at(c.y - 0.4 * sc)
        height = 0.45 * sc
        up = -1.0 if below else 1.0
        tops = []
        for s in (-1, 1):
            root, tip = (c.y - 0.85 * sc, c.y), (c.y - 0.40 * sc, c.y + 0.08)
            self.fin(part, s * x, below, root, tip, height, 0.04, self.main, self.edge)
            tops.append(self.tail_base(s * x, below)((tip[0] + tip[1]) / 2) - 0.01 + up * height * 0.92)
        le = c.y - 0.40 * sc + 0.25 * 0.48 * sc
        self.stabiliser(part, -x - 0.06, x + 0.06, le, 0.30 * sc, 0.26 * sc, 0.04 * sc, sum(tops) / 2, 0.0)

    def t_pod_fins(self, part, c, below):
        sc = self.scale
        pods = self.pods()
        for s in (-1, 1):
            p = pods.get(s)
            x = p[0] if p else s * 0.8 * self.half_at(c.y - 0.4 * sc)
            yb = p[4] if p else c.y
            self.fin(part, x, below, (yb - 0.70 * sc, yb), (yb - 0.30 * sc, yb + 0.06), 0.34 * sc, 0.035, self.accent, self.edge,
                     math.radians(8), s)

    def t_wye(self, part, c, below):
        sc = self.scale
        for s in (-1, 1):
            self.fin(part, s * 0.04, below, (c.y - 0.95 * sc, c.y - 0.05), (c.y - 0.40 * sc, c.y + 0.08), 0.44 * sc, 0.04,
                     self.main, self.edge, math.radians(40), s)
        self.fin(part, 0.0, not below, (c.y - 0.70 * sc, c.y - 0.02), (c.y - 0.30 * sc, c.y + 0.06), 0.24 * sc, 0.035,
                 self.accent, self.edge)

    # ---- body kits
    def armor_tier(self, leg):
        kind = self.design("armor", leg)
        if kind == "initial":
            return self.initial_armor(leg)
        g = self.group("Module_Armor_" + ("lg" if leg else "ep"))
        part = K.Part("Armor_" + kind.capitalize())
        getattr(self, "a_" + kind)(part)
        made = [part.finish(g, bevel=0.0015, smooth_angle=40)] if part.bm.faces else []
        if made:
            self.export(made, "armor_lg" if leg else "armor_ep")
            self.drop(made)

    def canards(self, part, fys=(0.10, 0.17)):
        sc, L = self.scale, self.y_max - self.y_min
        for s in (-1, 1):
            for k, fy in enumerate(fys):
                y = self.y_min + fy * L
                span = self.side_span(s, y)
                if not span:
                    continue
                z = span[0] + 0.40 * (span[1] - span[0])
                x = self.side_x(s, y, z)
                if x is None:
                    continue
                w = (0.15 - 0.03 * k) * sc
                self.plate(part, [(s * (x - 0.01), y - 0.09 * sc, z), (s * (x + w), y - 0.02 * sc, z + 0.035),
                                  (s * (x + w), y + 0.03 * sc, z + 0.035), (s * (x - 0.01), y + 0.07 * sc, z)], 0.012, self.accent)

    def streamliner(self, part, depth=0.05, top=(0.22, 0.28)):
        sc, L = self.scale, self.y_max - self.y_min
        for s in (-1, 1):
            prof = []
            ys = np.linspace(self.y_min + 0.20 * L, self.y_max - 0.02, 30)
            for i, y in enumerate(ys):
                span = self.side_span(s, y)
                if not span:
                    continue
                t = i / (len(ys) - 1)
                zlo, ztop = span[0] + 0.01, span[0] + (top[0] + top[1] * t) * (span[1] - span[0])
                col = [(self.side_x(s, y, ztop + (zlo - ztop) * k / 6), ztop + (zlo - ztop) * k / 6) for k in range(7)]
                if any(x is None for x, _ in col):
                    continue
                prof.append((y, col, depth * sc * smooth(t / 0.18) * (0.6 + 0.4 * t)))
            if len(prof) < 4:
                continue
            y_l, col_l, off_l = prof[-1]
            for k in range(1, 5):
                f = k / 4
                ztop = col_l[0][1]
                prof.append((y_l + 0.30 * sc * f, [(x, ztop + (z - ztop) * (1 - 0.6 * f)) for x, z in col_l], off_l * (1 - 0.85 * f)))
            rows = [[Vector((s * (x + off), y, z)) for x, z in col] + [Vector((s * (x - 0.004), y, z)) for x, z in reversed(col)]
                    for y, col, off in prof]
            n_out = len(prof[0][1])
            part.loft(rows, lambda i, j: self.accent if j == 0 else (self.main if j < n_out - 1 else (self.edge if j == n_out - 1 else "Graphite")),
                      closed_u=True, cap0=self.main, cap1=self.edge)

    def a_aero(self, part):
        sc, L = self.scale, self.y_max - self.y_min
        self.canards(part)
        for s in (-1, 1):
            self.wedge_line(part, s, self.flank_line(s, self.y_min + 0.24 * L, self.y_max - 0.10 * L, 0.45), 0.05 * sc, 0.022,
                            self.accent, self.edge)
        y0 = self.y_min + 0.08 * L
        fp = self.footprint(y0)
        if fp:
            xs_ = [p[0] for b in fp for p in b]
            zb = min(p[1] for b in fp for p in b)
            w, xc = (max(xs_) - min(xs_)) / 2 * 0.95, (max(xs_) + min(xs_)) / 2
            self.plate(part, [(xc - w, y0 + 0.10, zb - 0.006), (xc + w, y0 + 0.10, zb - 0.006),
                              (xc + 0.8 * w, self.y_min - 0.10 * sc, zb + 0.004), (xc - 0.8 * w, self.y_min - 0.10 * sc, zb + 0.004)], 0.014, self.edge)

    def a_shields(self, part):
        """Thick shields on the flanks in the ship's paint, bulging and rounded fore and aft."""
        sc, L = self.scale, self.y_max - self.y_min
        for s in (-1, 1):
            rows = []
            ys = np.linspace(self.y_min + 0.30 * L, self.y_max - 0.15 * L, 14)
            for i, y in enumerate(ys):
                span = self.side_span(s, y)
                if not span:
                    continue
                t = i / (len(ys) - 1)
                h = span[1] - span[0]
                col = [(self.side_x(s, y, span[0] + h * (0.66 - 0.40 * k / 6)), span[0] + h * (0.66 - 0.40 * k / 6)) for k in range(7)]
                if any(x is None for x, _ in col):
                    continue
                bulge = 0.075 * sc * smooth(t / 0.15) * smooth((1 - t) / 0.15)
                outer = [Vector((s * (x + bulge * math.sin(math.pi * (0.15 + 0.7 * k / 6))), y, z)) for k, (x, z) in enumerate(col)]
                rows.append(outer + [Vector((s * (x - 0.004), y, z)) for x, z in reversed(col)])
            if len(rows) > 3:
                part.loft(rows, lambda i, j: self.accent if j == 0 else (self.main if j < 6 else (self.edge if j == 6 else "Graphite")),
                          closed_u=True, cap0=self.main, cap1=self.main)

    def a_carapace(self, part):
        """Carapace skirts sweeping down the flanks and a ram across the nose."""
        sc, L = self.scale, self.y_max - self.y_min
        self.streamliner(part, depth=0.06, top=(0.30, 0.30))
        y0 = self.y_min + 0.06 * L
        bs = self.bodies_at(y0)
        if bs:
            xc, hw, zb = bs[0]
            rows = [[Vector((x, y, z)) for y, z in self.foil(self.y_min - 0.06 * sc, self.y_min + 0.10 * sc, zb + 0.05, 0.05 * sc)]
                    for x in np.linspace(xc - hw * 1.05, xc + hw * 1.05, 5)]
            part.loft(rows, self.foil_mats(self.edge, self.edge, self.edge), closed_u=True, cap0=self.edge, cap1=self.edge)

    def a_needle(self, part):
        """Fairings along the flanks and a sleeve of two fine strakes along the needle nose."""
        sc, L = self.scale, self.y_max - self.y_min
        self.streamliner(part, depth=0.045, top=(0.20, 0.25))
        for s in (-1, 1):
            pts = self.flank_line(s, self.y_min + 0.03 * L, self.y_min + 0.32 * L, 0.78, 18)
            self.wedge_line(part, s, pts, 0.025 * sc, 0.010, self.accent, self.edge, (0.10, 0.25))

    def a_prong_blades(self, part):
        sc, L = self.scale, self.y_max - self.y_min
        for s in (-1, 1):
            self.wedge_line(part, s, self.flank_line(s, self.y_min + 0.04 * L, self.y_min + 0.58 * L, 0.5), 0.05 * sc, 0.02,
                            self.accent, self.edge, (0.10, 0.20))

    def a_bridge(self, part):
        """A wing bridging the two prongs near their tips, and a spear on each prong."""
        sc, L = self.scale, self.y_max - self.y_min
        prongs = self.outer_bodies(0.02, 0.30, 20, 0.12)
        if len(prongs) == 2:
            yb = self.y_min + 0.14 * L
            zc = None
            xi = []
            for s in (-1, 1):
                for z_try in np.linspace(self.z_low + 0.05, self.z_high - 0.05, 12):
                    loc, _ = self.hit((0.0, yb, z_try), (s, 0, 0), 4.0)
                    if loc is not None:
                        xi.append(abs(loc.x))
                        zc = z_try if zc is None else zc
                        break
            if len(xi) == 2 and zc is not None:
                xin = min(xi) + 0.02
                rows = [[Vector((x, y, z)) for y, z in self.foil(yb - 0.15 * sc, yb + 0.15 * sc, zc, 0.035 * sc, camber=0.03)]
                        for x in np.linspace(-xin, xin, 5)]
                part.loft(rows, self.foil_mats(self.accent, "Graphite", self.edge), closed_u=True, cap0=self.edge, cap1=self.edge)
            for s, p in prongs.items():
                span = self.side_span(s, p[3] + 0.04)
                z = (span[0] + span[1]) / 2 if span else p[2] + p[1]
                n = Vector((p[0], p[3], z))
                part.lathe(n + Vector((0, 0.05, 0)), n - Vector((0, 0.26 * sc, 0)), [(0, min(p[1], 0.05)), (0.5, 0.02), (1.0, 0.002)],
                           lambda k: self.edge, 14, cap0=self.edge)
        else:
            self.a_prong_blades(part)

    def pod_cone(self, part, p, front=True, length=0.40):
        sc = self.scale
        y = p[3] if front else p[4]
        span = None if len(p) > 5 else self.side_span(1 if p[0] > 0 else -1, y + (0.05 if front else -0.05))
        z = p[5] if len(p) > 5 else ((span[0] + span[1]) / 2 if span else p[2] + p[1])
        r = max(0.04, min(p[1], (span[1] - span[0]) / 2 if span else p[1]))
        d = -1.0 if front else 1.0
        a = Vector((p[0], y - d * 0.06, z))
        b = Vector((p[0], y + d * length * sc, z))
        part.lathe(a, b, [(0, r * 1.02), (0.35, r * 0.85), (0.8, r * 0.35), (1.0, 0.004)], lambda k: self.accent if k < 2 else self.edge, 24,
                   cap0=self.accent)

    def a_pod_cones(self, part):
        pods = self.pods()
        if not pods:
            return self.a_aero(part)
        for p in pods.values():
            self.pod_cone(part, p, True)

    def a_pod_tails(self, part):
        pods = self.pods()
        if not pods:
            return self.a_aero(part)
        for p in pods.values():
            self.pod_cone(part, p, True, 0.46)
            self.pod_cone(part, p, False, 0.50)

    def t_tailplanes(self, part, c, below):
        """Swept tailplanes out of the engine shroud's flanks at mid height, flat, a titanium pivot fairing at each root."""
        self.tailplanes(part, c, 0.42, 0.0)

    def t_anhedral(self, part, c, below):
        """Anhedral tailplanes (the F-4's), drooping like the STRIX's down-swept wing, longer, a pivot fairing each."""
        self.tailplanes(part, c, 0.50, 0.20)

    def tailplanes(self, part, c, reach, droop):
        sc = self.scale
        y = c.y - 0.55 * sc
        span = self.side_span(1, y)
        if not span:
            return
        z = span[0] + 0.55 * (span[1] - span[0])
        hx = self.side_x(1, y, z) or 0.3
        X = hx + reach * sc
        self.stabiliser(part, -X, X, y - 0.22 * sc, 0.60 * sc, 0.20 * sc, 0.34 * sc, z, droop * sc * X / max(X - hx, 0.1))
        for s in (-1, 1):
            part.lathe((s * (hx + 0.01), y - 0.26 * sc, z), (s * (hx + 0.01), y + 0.30 * sc, z),
                       [(0, 0.0), (0.2, 0.030), (0.7, 0.032), (1, 0.0)], lambda k: "Titanium", 16)

    def a_lerx(self, part):
        """Leading-edge root extensions (F/A-18, Su-27): a thin blended strake on each side from beside the cockpit
        to the wing's leading edge at the wing's root height, in the paint, growing towards the wing."""
        F = self.wing_frame()
        if F is None:
            return self.a_aero(part)
        sc = self.scale
        y0, y1 = self.canopy_y - 0.55 * sc, F["les"] + 0.04 * F["cr"]
        z = F["mids"] + 0.25 * F["ths"]
        for s in (-1, 1):
            ys = np.linspace(y0, y1, 12)
            pts = [(self.side_x(s, y, z), y) for y in ys]
            pts = [(x, y) for x, y in pts if x is not None]
            if len(pts) < 4:
                continue
            cf = np.polyfit([y for _, y in pts], [x for x, _ in pts], 2)
            line = [(float(np.polyval(cf, y)), float(y), z) for y in np.linspace(pts[0][1], pts[-1][1], 24)]
            self.wedge_line(part, s, line, 0.26 * sc, 0.018, self.accent, self.edge, (0.95, 0.02))

    def a_needle_lerx(self, part):
        self.a_lerx(part)
        self.a_needle(part)

    def c_deck_louvres(self, part, c, y, span, half):
        """A louvred panel flush in the deck behind the canopy: titanium slats over a dark well, a carbon surround."""
        sc = self.scale
        w, L = min(0.44 * sc, 1.2 * half), 0.40 * sc
        self.hull_sheet(part, 0, lambda u, v: ((u - 0.5) * (w + 0.05), y - 0.025 + v * (L + 0.05)), 6, 6, 0.0012, "Carbon_Tier",
                        top=True)
        self.louvres(part, 0, lambda u, v: ((u - 0.5) * w, y + v * L), 9, "Titanium", top=True)

    # ---- cooling (all flush in the bodywork)
    def cooling_tier(self, leg):
        site = self.cooling_site()
        if site is None:
            return
        kind = self.design("cooling", leg)
        if kind == "initial":
            return self.initial_cooling(leg)
        g = self.group("Module_Cooling_" + ("lg" if leg else "ep"))
        part = K.Part("Cooling_" + kind.capitalize())
        getattr(self, "c_" + kind)(part, *site)
        made = [part.finish(g, bevel=0.0, smooth_angle=30)] if part.bm.faces else []
        if made:
            self.export(made, "cooling_lg" if leg else "cooling_ep")
            self.drop(made)

    def channel(self, part, s, y, zc, Lc, hc, mode=None):
        def box(u, v):
            return y + (u - 0.5) * Lc, zc + (v - 0.5) * hc + (u - 0.5) * 0.03
        self.hull_sheet(part, s, box, 12, 2, 0.0022, "Black", mode=mode)
        self.hull_sheet(part, s, lambda u, v: box(0.03 + 0.94 * u, 0.42 + 0.16 * v), 12, 1, 0.0026, "Emit_HotDim", mode=mode)
        for k in range(12):
            self.hull_sheet(part, s, lambda u, v, k=k: box((k + 0.5) / 12 + (u - 0.5) * 0.006, 0.1 + 0.8 * v), 1, 1, 0.0034, "Titanium", mode=mode)
        self.hull_sheet(part, s, lambda u, v: box(u, 1.0 + v * 0.18), 12, 1, 0.005, self.edge, mode=mode)

    def perforated(self, part, xc, y0, px, py, rows=6, cols=14):
        if self.hull_sheet(part, 0, lambda u, v: (xc + (u - 0.5) * px, y0 + v * py), 4, 4, 0.0018, "Titanium", top=True):
            for i in range(rows):
                for j in range(cols):
                    cx, cy = (j + 0.5) / cols, (i + 0.5) / rows
                    self.hull_sheet(part, 0, lambda u, v, cx=cx, cy=cy: (xc + (cx - 0.5 + (u - 0.5) * 0.035) * px, y0 + (cy + (v - 0.5) * 0.09) * py),
                                    1, 1, 0.0026, "Black", top=True)

    def c_channel(self, part, c, y, span, half):
        sc = self.scale
        if span:
            for s in (-1, 1):
                self.channel(part, s, y, span[0] + 0.55 * (span[1] - span[0]), 0.85 * sc, 0.045 * sc)
        self.perforated(part, 0.0, y + 0.50 * sc, 0.40 * sc, 0.26 * sc)

    def c_naca_big(self, part, c, y, span, half):
        sc = self.scale
        for s in (-1, 1):
            self.naca(part, s * half * 0.42, y - 0.30 * sc, 0.70 * sc, 0.026, 0.16 * sc, lip="Carbon_Tier")

    def c_fan(self, part, c, y, span, half):
        """A fan of curved louvres on the carapace behind the cockpit, titanium lips, and a perforated outlet."""
        sc = self.scale
        for k in range(7):
            a = math.radians(-60 + 20 * k)
            cx, cy = math.sin(a) * half * 0.55, y + 0.10 * sc - math.cos(a) * 0.12 * sc
            d = Vector((math.sin(a), -math.cos(a)))
            n = Vector((-d.y, d.x))

            def slot(u, v, cx=cx, cy=cy, d=d, n=n, w=0.022):
                p = Vector((cx, cy)) + d * (u - 0.5) * 0.24 * sc + n * (v - 0.5) * w
                return p.x, p.y
            self.hull_sheet(part, 0, slot, 4, 1, 0.0022, "Black", top=True)
            self.hull_sheet(part, 0, lambda u, v, slot=slot: slot(u, 1.0 + v * 0.5, w=0.022), 4, 1, 0.005, "Titanium", top=True)
        self.perforated(part, 0.0, y + 0.45 * sc, 0.30 * sc, 0.18 * sc, 5, 10)

    def c_naca3(self, part, c, y, span, half):
        sc = self.scale
        for xf in (-0.45, 0.0, 0.45):
            self.naca(part, xf * half, y - 0.20 * sc, 0.48 * sc, 0.02, 0.10 * sc, lip="Titanium")
        self.perforated(part, 0.0, y + 0.42 * sc, 0.36 * sc, 0.20 * sc)

    def c_inner_gills(self, part, c, y, span, half):
        """Gills on the inner faces of the prongs, out of the airflow's way between them."""
        sc, L = self.scale, self.y_max - self.y_min
        yg = self.y_min + 0.30 * L
        for s in (-1, 1):
            for z_try in np.linspace(self.z_low + 0.05, self.z_high - 0.05, 12):
                loc, _ = self.hit((0.0, yg, z_try), (s, 0, 0), 4.0)
                if loc is not None:
                    self.gills(part, s, yg, z_try, 5, 0.12 * sc, 0.06 * sc, surround="Carbon_Tier", lip="Titanium", mode="inner")
                    break

    def c_prong_channels(self, part, c, y, span, half):
        sc, L = self.scale, self.y_max - self.y_min
        yp = self.y_min + 0.28 * L
        sp = self.side_span(1, yp)
        if sp:
            for s in (-1, 1):
                self.channel(part, s, yp, sp[0] + 0.5 * (sp[1] - sp[0]), 0.75 * sc, 0.035 * sc)

    def c_pod_scoops(self, part, c, y, span, half):
        sc = self.scale
        pods = self.pods()
        for s, p in pods.items():
            yc = (p[3] + p[4]) / 2
            sp = self.side_span(s, yc)
            if not sp:
                continue
            zc = p[5] if len(p) > 5 else sp[0] + 0.45 * (sp[1] - sp[0])
            a, b = 0.20 * sc, 0.05 * sc
            self.hull_sheet(part, s, lambda u, v: (yc + a * v * math.cos(2 * math.pi * u), zc + b * v * math.sin(2 * math.pi * u)), 24, 3,
                            0.0022, "Black", closed=True)
            self.hull_sheet(part, s, lambda u, v: (yc + a * (1.0 + 0.10 * v) * math.cos(math.pi * (0.1 + 0.8 * u)),
                                                   zc + b * (1.0 + 0.25 * v) * math.sin(math.pi * (0.1 + 0.8 * u))), 12, 1, 0.006, "Titanium")

    def c_pod_perf(self, part, c, y, span, half):
        sc = self.scale
        pods = self.pods()
        for s, p in pods.items():
            yc = (p[3] + p[4]) / 2
            self.perforated(part, p[0], yc - 0.20 * sc, min(0.9 * 2 * p[1], 0.30 * sc), 0.40 * sc, 8, 8)
        if not pods:
            self.c_channel(part, c, y, span, half)

    # ---- engines: inside only (the x-ray view), never out of the bodywork; outside, their flame or plasma
    # (EXMeta::Flame). Player, 2026-11-01: rings that stood out of the bodywork were wrong; "detailed, like cables,
    # tubes, regeneration, nothing extravagant, a few neon cables". Each engine is dressed on its own body: an epic
    # with a tube-wall regenerative jacket (copper tubes along the chamber and the nozzle, as on rocket engines),
    # manifold collars, coolant lines and a harness with two cyan neon cables; a legendary with a helical jacket and
    # neon cables in the ship's own colour. What joins the engines follows each chassis: crossover pipes between
    # STRIX's stacked pair, a manifold across WRAITH's three, nothing out along NOMAD's arms.
    def engines(self):
        """Each engine: (nozzle centre, nozzle radius, front y, length, radius of its body, its x and z extents).
        Its parts' points (the nearest engine's, in x-z) are kept in self.engine_pts for its shape."""
        nozzles = [Vector(v) for n, v in sorted(self.sock.items()) if n.startswith("Socket_Propulsion")]
        G = self.G.get("Propulsion")
        if not nozzles or G is None:
            return []
        skins = set(K.SKINS)
        V = self.world_verts([o for o in K.SHIP.objects if o.type == 'MESH' and under(o, G) and o not in skins])
        r = self.nozzle_r
        if len(V):
            dist = np.stack([np.hypot(V[:, 0] - c.x, V[:, 2] - c.z) for c in nozzles])
            near = np.argmin(dist, axis=0)
        out, self.engine_pts = [], {}
        for i, c in enumerate(nozzles):
            sel = V[(np.hypot(V[:, 0] - c.x, V[:, 2] - c.z) < 1.8 * r) & (V[:, 1] < c.y + 0.05)] if len(V) else V
            Lc = float(np.clip(c.y - (sel[:, 1].min() if len(sel) else c.y - 1.2), 0.5, 3.0))
            Re = max(float(np.percentile(np.hypot(sel[:, 0] - c.x, sel[:, 2] - c.z), 90)) if len(sel) else r * 1.2, r * 1.05)
            hx = max(float(np.percentile(np.abs(sel[:, 0] - c.x), 95)) if len(sel) else Re, r * 1.05)
            hz = max(float(np.percentile(np.abs(sel[:, 2] - c.z), 95)) if len(sel) else Re, r * 1.05)
            e = (c, r, c.y - Lc, Lc, Re, hx, hz)
            own = V[(near == i) & (dist[i] < 4.0 * r) & (V[:, 1] > c.y - Lc - 0.05) & (V[:, 1] < c.y + 0.05)] if len(V) else V
            self.engine_pts[id(e)] = own
            out.append(e)
        return out

    def engine_shape(self, e):
        """The engine's body along it, from its own parts: y samples, half extents (ax, az) at each, the superellipse
        exponent (2 round, 5 a rounded box), and how far the bodywork is from its axis at each y in 24 directions."""
        c, r, yf, Lc, Re, hx, hz = e
        P = self.engine_pts.get(id(e), np.zeros((0, 3)))
        ys = np.linspace(yf + 0.03 * Lc, c.y - 0.02 * Lc, 12)
        ax, az = [], []
        for y in ys:
            sl = P[np.abs(P[:, 1] - y) < 0.07 * Lc] if len(P) else P
            if len(sl) >= 6:
                ax.append(float(np.percentile(np.abs(sl[:, 0] - c.x), 95)))
                az.append(float(np.percentile(np.abs(sl[:, 2] - c.z), 95)))
            else:
                ax.append(np.nan)
                az.append(np.nan)
        ax, az = np.array(ax), np.array(az)
        for arr, fall in ((ax, hx), (az, hz)):
            ok = ~np.isnan(arr)
            arr[:] = np.interp(ys, ys[ok], arr[ok]) if ok.any() else fall
            np.clip(arr, 0.6 * r, 3.0 * r, out=arr)
        n = 2.0
        if len(P):
            q = np.minimum(np.abs(P[:, 0] - c.x) / max(hx, 1e-3), np.abs(P[:, 2] - c.z) / max(hz, 1e-3))
            n = 5.0 if float(np.percentile(q, 98)) > 0.8 else 2.0
        angs = np.linspace(0, 2 * math.pi, 24, endpoint=False)
        rho = np.full((len(ys), len(angs)), np.inf)
        for i, y in enumerate(ys):
            for k, t in enumerate(angs):
                loc, _ = self.hit((c.x, y, c.z), (math.cos(t), 0, math.sin(t)), 3.0)
                if loc is not None:
                    rho[i, k] = math.hypot(loc.x - c.x, loc.z - c.z)
        return dict(c=c, ys=ys, ax=ax, az=az, n=n, rho=rho, angs=angs)

    def spot(self, sh, y, th, off, margin=0.012):
        """A point round the engine's body at y, angle th, 'off' out from it, held inside the bodywork."""
        c, ys, rho, angs = sh["c"], sh["ys"], sh["rho"], sh["angs"]
        a = float(np.interp(y, ys, sh["ax"])) + off
        b = float(np.interp(y, ys, sh["az"])) + off
        ct, st = math.cos(th), math.sin(th)
        x = a * math.copysign(abs(ct) ** (2.0 / sh["n"]), ct)
        z = b * math.copysign(abs(st) ** (2.0 / sh["n"]), st)
        d = math.hypot(x, z)
        k = int(round((math.atan2(z, x) % (2 * math.pi)) / (2 * math.pi) * len(angs))) % len(angs)
        i = int(np.clip(np.searchsorted(ys, y), 1, len(ys) - 1))
        lim = min(rho[i - 1, k], rho[i, k], rho[i - 1, (k + 1) % len(angs)], rho[i - 1, k - 1])
        if d > lim - margin:
            f = max(lim - margin, 0.0) / max(d, 1e-6)
            x, z = x * f, z * f
        return Vector((c.x + x, y, c.z + z))

    def collar(self, part, sh, y, off, rad, m, n=48):
        pts = [self.spot(sh, y, 2 * math.pi * k / n, off) for k in range(n)]
        part.tube(pts + [pts[0]], rad, m, 8)

    def engine_tier(self, leg):
        E = self.engines()
        if not E:
            return
        ensure_mat("Neon_Cyan", "#5FE3FF", rough=0.3, emit=6.0)
        ensure_mat("Neon_VORTEX", "#FF2A55", rough=0.3, emit=8.0)
        ensure_mat("Neon_BASTION", "#FFC23F", rough=0.3, emit=8.0)
        ensure_mat("Neon_STRIX", "#3F8FFF", rough=0.3, emit=8.0)
        ensure_mat("Neon_WRAITH", "#2FFF8F", rough=0.3, emit=8.0)
        ensure_mat("Neon_NOMAD", "#9B6BFF", rough=0.3, emit=8.0)
        neon = ("Neon_" + K.NAME) if ("Neon_" + K.NAME) in K.MAT and leg else "Neon_Cyan"
        g = self.group("Module_Engine_" + ("lg" if leg else "ep"))
        part = K.Part("Engine_" + ("Legendary" if leg else "Epic"))
        shapes = [self.engine_shape(e) for e in E]
        for e, sh in zip(E, shapes):
            self.regen(part, e, sh, leg)
            self.harness(part, e, sh, neon, leg)
        self.links(part, E, shapes, neon, leg)
        made = [part.finish(g, bevel=0.0, smooth_angle=40)] if part.bm.faces else []
        if made:
            self.export(made, "engine_lg" if leg else "engine_ep")
            self.drop(made)

    def regen(self, part, e, sh, leg):
        """The regenerative jacket on the chamber and the nozzle: copper tubes along it (epic) or wound round it in
        three helices (legendary), between two titanium manifold collars."""
        c, r, yf, Lc, Re, hx, hz = e
        sc = self.scale
        y0, y1 = yf + 0.10 * Lc, c.y - 0.05 * Lc
        tr = 0.0065 * sc
        ym = (y0 + y1) / 2
        per = 2 * math.pi * math.sqrt((float(np.interp(ym, sh["ys"], sh["ax"])) ** 2 + float(np.interp(ym, sh["ys"], sh["az"])) ** 2) / 2)
        if not leg:
            n = int(np.clip(per / 0.024, 24, 64))
            ys = np.linspace(y0, y1, 10)
            for k in range(n):
                part.tube([self.spot(sh, y, 2 * math.pi * (k + 0.5) / n, tr) for y in ys], tr, "Copper_Coil", 6)
        else:
            pitch = 0.11 * sc
            turns = (y1 - y0) / pitch
            m = max(24, int(turns * 28))
            for j in range(3):
                th0 = 2 * math.pi * j / 3
                part.tube([self.spot(sh, y0 + (y1 - y0) * t, th0 + 2 * math.pi * turns * t, tr * 1.3)
                           for t in np.linspace(0, 1, m)], tr * 1.3, "Copper_Coil", 6)
        for y in (y0, y1):
            self.collar(part, sh, y, 2.8 * tr, 0.013 * sc, "Titanium")
        if leg:                                           # bolts round the injector collar
            for k in range(16):
                p = self.spot(sh, y0, 2 * math.pi * k / 16, 2.8 * tr + 0.012)
                part.sphere(p, 0.0065 * sc, "Metal_Bright", segs=8, rings=5)

    def harness(self, part, e, sh, neon, leg):
        """Coolant lines low on the engine and a harness over it: two braided cables in clips and neon cables
        (straight, cyan, on an epic; four in a slow quarter turn, the ship's colour, on a legendary)."""
        c, r, yf, Lc, Re, hx, hz = e
        sc = self.scale
        y0, y1 = yf + 0.06 * Lc, c.y - 0.12 * Lc
        ys = np.linspace(y0, y1, 12)
        for side in (-1, 1):                                  # coolant lines from the nozzle collar to the injector
            th = math.radians(270 + side * 38)
            part.tube([self.spot(sh, y, th, 0.034 * sc) for y in ys], 0.010 * sc, "Titanium", 8)
        for side in (-1, 1):                                  # braided cables over the top, in clips
            th = math.radians(90 + side * 24)
            part.tube([self.spot(sh, y, th, 0.030 * sc) for y in ys], 0.008 * sc, "Graphite", 8)
            for y in np.linspace(y0 + 0.08 * Lc, y1 - 0.04 * Lc, max(2, int((y1 - y0) / (0.22 * sc)))):
                p = self.spot(sh, y, th, 0.030 * sc)
                part.box(p, (0.024 * sc, 0.012 * sc, 0.024 * sc), "Titanium")
        if not leg:
            for side in (-1, 1):
                th = math.radians(90 + side * 52)
                part.tube([self.spot(sh, y, th, 0.024 * sc) for y in ys], 0.0042 * sc, neon, 6)
        else:
            for j in range(4):
                th0 = math.radians(45 + 90 * j)
                part.tube([self.spot(sh, y, th0 + 0.5 * math.pi * t, 0.040 * sc) for t, y in zip(np.linspace(0, 1, 16), np.linspace(y0, y1, 16))],
                          0.0055 * sc, neon, 6)

    def links(self, part, E, shapes, neon, leg):
        """What joins the engines, after each chassis: crossover pipes between a stacked pair (STRIX), a manifold
        across a row (WRAITH); pods on arms (NOMAD) and single engines have none."""
        if len(E) < 2:
            return
        sc = self.scale
        pairs = []
        for i in range(len(E)):
            for j in range(i + 1, len(E)):
                a, b = E[i][0], E[j][0]
                gap = math.hypot(a.x - b.x, a.z - b.z)
                if gap < 3.2 * max(E[i][4], E[j][4]):         # neighbours in the same body (not pods out on arms)
                    pairs.append((i, j))
        for i, j in pairs:
            (a, _, yfa, *_), (b, _, yfb, *_) = E[i], E[j]
            th_a = math.atan2(b.z - a.z, b.x - a.x)
            th_b = th_a + math.pi
            for f in (0.12, 0.88):
                y = max(yfa, yfb) + f * (min(a.y, b.y) - max(yfa, yfb))
                p, q = self.spot(shapes[i], y, th_a, 0.02 * sc), self.spot(shapes[j], y, th_b, 0.02 * sc)
                if (p - q).length > 0.01:
                    part.tube([p, (p + q) / 2, q], 0.011 * sc, "Titanium", 8)
            y = max(yfa, yfb) + 0.5 * (min(a.y, b.y) - max(yfa, yfb))
            p, q = self.spot(shapes[i], y, th_a + 0.35, 0.02 * sc), self.spot(shapes[j], y, th_b - 0.35, 0.02 * sc)
            if (p - q).length > 0.01:
                part.tube([p, (p + q) / 2, q], 0.0045 * sc * (1.25 if leg else 1.0), neon, 6)

    def manifest(self):
        nozzles = [[round(v.x, 4), round(v.y, 4), round(v.z, 4), self.nozzle_r]
                   for n, v in sorted(self.sock.items()) if n.startswith("Socket_Propulsion")]
        data = {"ship": K.NAME, "pieces": self.pieces, "wings": list(self.wings), "tail": self.tail, "nozzles": nozzles}
        if self.bay:
            data["utility_bay"] = [round(v, 3) for v in (*self.bay[0], *self.bay[1])]
        with open(os.path.join(self.dir, "%s_modules.json" % self.stem), "w") as f:
            json.dump(data, f, indent=1)
        print("MODULES %s %d pieces, nozzles %s" % (K.NAME, len(self.pieces), nozzles))


def build_modules(ns, wings, palette, tail="above", scale=1.0, nozzle_r=0.15):
    """wings: three of WING_KINDS (none for a ship without a wing slot); palette: (main paint, accent paint, edge
    paint) for the wings and the body kits; tail: 'above' (fins on the rear deck) or 'below' (ventral fins, for ships
    with fins on top already)."""
    b = Builder(ns, wings, palette, tail, scale, nozzle_r)
    b.split()
    for kind in wings:
        b.wing(kind)
    for kind in ARMOUR_KINDS:
        b.armour(kind)
    for kind in COOLING_KINDS:
        b.cooling(kind)
    for kind in TAIL_KINDS:
        b.tail_fins(kind)
    for kind in UTILITY_KINDS:
        b.utility(kind)
    b.tier_pieces()
    b.manifest()
