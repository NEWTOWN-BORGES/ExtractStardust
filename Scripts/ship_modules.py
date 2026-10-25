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

    # ------------------------------------------------------------ 4. vents and radiators
    def cooling(self, kind):
        c = self.sock.get("Socket_Cooling")
        if c is None:
            return
        sc = self.scale
        made = []
        g = self.group("Module_Cooling_" + kind)
        part = K.Part("Cooling_" + kind.capitalize())
        if kind == "vents":
            for s in (-1, 1):
                for dy in (-0.26, 0.26):
                    loc, nor = self.side_hit(s, c.y + dy * sc, c.z + 0.08)
                    if loc is None:
                        continue
                    R = frame_of(nor)
                    part.box(loc + nor * 0.035, (0.46 * sc, 0.22 * sc, 0.06), "Graphite", R)
                    for k in range(5):
                        part.box(loc + nor * 0.068 + R @ Vector((0, (k - 2) * 0.038 * sc, 0)), (0.42 * sc, 0.010, 0.014),
                                 "Black", R)
        else:
            big = kind == "grid"
            ln, wd, ht = (1.10, 0.16, 0.26) if big else (0.70, 0.13, 0.20)
            ln, wd, ht = ln * sc, wd * sc, ht * sc
            for s in (-1, 1):
                edge, _ = self.side_hit(s, c.y, c.z + 0.05)
                half = abs(edge.x) if edge is not None else 0.4
                x = s * half * (0.62 if big else 0.55)
                loc, nor = self.top_hit(x, c.y)
                if loc is None:
                    continue
                base = loc + Vector((0, 0, 0.01))
                part.box(base + Vector((0, 0, 0.02)), (wd + 0.04, ln + 0.04, 0.04), "Metal")       # mount
                part.box(base + Vector((0, 0, 0.04 + ht / 2)), (wd, ln, ht), "Black")              # core
                n = 10 if big else 6
                for k in range(n):
                    yk = base.y - ln / 2 + ln * (k + 0.5) / n
                    part.box(Vector((x, yk, base.z + 0.04 + ht / 2)), (wd + 0.03, 0.006, ht + 0.02), "Metal_Bright")
                part.box(base + Vector((0, 0, 0.05 + ht)), (wd + 0.02, ln + 0.02, 0.012), self.edge)  # top rail
                if big:
                    part.box(base + Vector((0, 0, 0.06 + ht)), (wd * 0.4, ln * 0.9, 0.006), "Emit_Hot")
                part.tube([base + Vector((0, -ln / 2, 0.06)), base + Vector((-s * 0.12, -ln / 2 - 0.08, 0.01))],
                          0.016, "Metal", 8)
        if part.bm.faces:
            made.append(part.finish(g, bevel=0.0012))
        self.export(made, "cooling_" + kind)
        self.drop(made)

    # ------------------------------------------------------------ 5. tail fins
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
    b.manifest()
