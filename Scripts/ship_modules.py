# Module variants for a ship built with ship_kit (Docs/MODULOS.md). The modules are the old game's catalogue (the
# Unity demo with the five old ships), adapted to the new ships:
# - wings of the ship's own: three per ship, grown from its stock wing (the same root section, so they go through the
#   same slots in the bodywork): short and swept with a tip fin, long with end plates, a second vector surface, braced
#   and thick, or a glider with folded tips and a glowing leading edge;
# - universal pieces that sit on the ship's own bodywork (found with ray casts): armour plates, vents and radiators,
#   tail fins, a scanner mast, a sensor dome, a field drone;
# - the ship split for the game: the core (everything but the wings), the stock wings, and the skeleton (structure and
#   systems without the bodywork: the hangar's x-ray view of the engines and the reactor).
# Called at the end of build_<ship>.py, after finish_ship:  build_modules(globals(), wings=..., palette=..., ...)
# Writes <out>/modules/<ship>_<piece>.fbx, all in the ship's frame (front -Y, up +Z, metres), so in Unreal every piece
# goes on the ship mesh with no offset; and <ship>_modules.json (the pieces and the engine nozzles, for the flames).
import json
import math
import os

import bpy
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
ARMOUR_KINDS = ("light", "guard", "bulwark", "shell", "aegis")
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

    # ------------------------------------------------------------ scene helpers
    def is_wing(self, o):
        return under(o, self.G["Wing_L"]) or under(o, self.G["Wing_R"])

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

    # ------------------------------------------------------------ 3. armour plates on the ship's sides
    def wrap_hit(self, s, y, zc, th):
        """The bodywork round the hull's side at angle th (0 = level with the side, + towards the deck)."""
        d = Vector((s * math.cos(th), 0, math.sin(th)))
        return self.hit(Vector((0, y, zc)) + d * 4.0, -d, 8.0)

    def armour(self, kind):
        sc = self.scale
        # length, angles round the hull (degrees: below the side wall, up onto the deck), thickness, panels along
        L, th0, th1, thick, panels = {"light": (1.25, -12, 22, 0.010, 1), "guard": (1.75, -22, 42, 0.018, 3),
                                      "bulwark": (2.05, -26, 44, 0.038, 2), "shell": (1.65, -24, 46, 0.014, 1),
                                      "aegis": (2.15, -28, 46, 0.042, 1)}[kind]
        L *= sc
        plate = {"light": "Metal_Bright", "guard": self.edge, "bulwark": "Graphite", "shell": "Graphite",
                 "aegis": "Graphite"}[kind]
        gap, stand = 0.035, 0.014                    # between panels; off the bodywork
        reach = 0.42 * max(1.0, sc)                  # how far round the hull a plate may wrap from the side wall
        made = []
        for s, side in ((1, "R"), (-1, "L")):
            c = self.sock.get("Socket_Armor_" + side)
            if c is None:
                continue
            zs = [z for z in (c.z + d * 0.02 for d in range(-30, 31)) if self.side_hit(s, c.y, z)[0] is not None]
            if not zs:
                continue
            zc = (max(zs) + min(zs)) / 2
            edge, _ = self.side_hit(s, c.y, zc)
            half = abs(edge.x) if edge is not None else abs(c.x)
            g = self.group("Module_Armor_%s_%s" % (kind, side))
            part = K.Part("Armor_%s_%s" % (kind.capitalize(), side))
            grids = []
            seg = (L - gap * (panels - 1)) / panels
            for k in range(panels):
                y0 = c.y - L / 2 + k * (seg + gap)
                ths = [math.radians(th0 + (th1 - th0) * j / 6) for j in range(7)]
                mid = min(range(7), key=lambda j: abs(ths[j]))
                grid = [[None] * 9 for _ in range(7)]
                for i in range(9):
                    y = y0 + seg * i / 8
                    side = Vector((s * half, y, zc))
                    col = []
                    for th in ths:
                        loc, nor = self.wrap_hit(s, y, zc, th)
                        ok = loc is not None and s * loc.x >= 0.3 * half and (loc - side).length <= reach
                        col.append((loc, nor.normalized()) if ok else None)
                    if col[mid] is None:
                        col[mid] = (side, Vector((s, 0, 0)))
                    for j in range(mid - 1, -1, -1):           # past the hull's curve (a fin, the belly, the canopy):
                        col[j] = col[j] or col[j + 1]           # the plate stops at the last good row
                    for j in range(mid + 1, 7):
                        col[j] = col[j] or col[j - 1]
                    for j in range(7):
                        grid[j][i] = col[j]
                part.loft([[lc + nr * (stand + thick) for lc, nr in row] for row in grid], lambda i, j: plate)
                grids.append(grid)
            K.orient_out(part, lambda cc: Vector((0, cc.y, zc)))
            made.append(K.shell(part, g, thick=thick, bevel=0.004 if thick > 0.03 else 0.003))
            bits = K.Part("Armor_%s_Bits_%s" % (kind.capitalize(), side))
            top = stand + thick
            for grid in grids:
                for loc, nor in (grid[0][0], grid[0][-1], grid[-1][0], grid[-1][-1], grid[3][0], grid[3][-1]):
                    p0 = loc + nor * top                                                  # bolts
                    bits.cyl(p0 - nor * 0.004, p0 + nor * 0.010, 0.016 if thick > 0.03 else 0.012, "Metal_Bright", 8)
            if kind in ("bulwark", "aegis"):                                              # shock absorbers on the deck
                for grid in grids:
                    for i in (2, 4, 6):
                        loc, nor = grid[-1][i]
                        bits.box(loc + nor * (top + 0.025), (0.12, 0.06, 0.05), "Metal", frame_of(nor))
                for grid in grids:                                                        # steel edge strips
                    for j in (0, 6):
                        loc, nor = grid[j][4]
                        bits.box(loc + nor * (top + 0.004), (seg * 0.96, 0.03, 0.012), "Metal", frame_of(nor))
            if kind == "guard":                                                           # a dark band per panel
                for grid in grids:
                    loc, nor = grid[3][4]
                    bits.box(loc + nor * (top + 0.003), (seg * 0.9, 0.05, 0.008), "Graphite", frame_of(nor))
            if kind == "shell":                                                           # lattice studs, a glowing seam
                for j in range(0, 7, 2):
                    for i in range(0, 9, 2):
                        loc, nor = grids[0][j][i]
                        bits.box(loc + nor * (top + 0.008), (0.07, 0.07, 0.016), "Metal_Bright", frame_of(nor))
                loc, nor = grids[0][3][4]
                bits.box(loc + nor * (top + 0.003), (L * 0.9, 0.012, 0.008), "Emit_Hover", frame_of(nor))
            if kind == "aegis":                                                           # gold frame and a hot seam
                for j in (0, 6):
                    loc, nor = grids[0][j][4]
                    bits.box(loc + nor * (top + 0.006), (L * 0.97, 0.035, 0.014), "Gold", frame_of(nor))
                for i in (0, 8):                                                          # the ends follow the hull
                    col = [grids[0][j][i] for j in range(7)]
                    for j, (loc, nor) in enumerate(col):
                        step = (col[min(j + 1, 6)][0] - col[max(j - 1, 0)][0]).length / (2 if 0 < j < 6 else 1)
                        bits.box(loc + nor * (top + 0.006), (0.035, step * 1.1, 0.014), "Gold", frame_of(nor))
                loc, nor = grids[0][3][4]
                bits.box(loc + nor * (top + 0.003), (L * 0.82, 0.012, 0.010), "Emit_Hot", frame_of(nor))
            made.append(bits.finish(g, bevel=0.0015))
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

    # ------------------------------------------------------------ 6. utility: mast, dome, drone
    def utility(self, kind):
        c = self.sock.get("Socket_Utility")
        if c is None:
            return
        loc, nor = self.top_hit(0.0, c.y)
        if loc is None:
            loc = c
        b = loc + Vector((0, 0, 0.005))
        u = 2.0 * self.scale                          # big enough to read from the hangar camera
        made = []
        g = self.group("Module_Utility_" + kind)
        part = K.Part("Utility_" + kind.capitalize())

        def at(x, y, z):
            return b + Vector((x, y, z)) * u

        if kind == "mast":
            part.box(at(0, 0, 0.02), (0.08 * u, 0.14 * u, 0.04 * u), "Metal")
            part.cyl(at(0, 0, 0.03), at(0, 0, 0.46), 0.012 * u, "Metal_Bright", 10)
            part.box(at(0, 0, 0.32), (0.18 * u, 0.02 * u, 0.02 * u), "Metal")
            part.box(at(0, 0.01, 0.40), (0.06 * u, 0.08 * u, 0.05 * u), "Graphite")
            part.sphere(at(0, 0, 0.47), 0.016 * u, "Emit_Hot", segs=10, rings=6)
        elif kind == "dome":
            part.cyl(at(0, 0, 0), at(0, 0, 0.04), 0.12 * u, "Metal", 24)
            part.cyl(at(0, 0, 0.04), at(0, 0, 0.052), 0.125 * u, "Emit_Hover", 24)
            part.sphere(at(0, 0, 0.052), 0.11 * u, "Glass", scale=(1, 1, 0.75), segs=20, rings=10)
        else:  # drone docked in a cradle
            for dy in (-0.07, 0.07):
                part.box(at(0, dy, 0.025), (0.20 * u, 0.03 * u, 0.05 * u), "Metal")
            d = at(0, 0, 0.08)
            part.box(d, (0.20 * u, 0.16 * u, 0.05 * u), self.main)
            part.box(d + Vector((0, -0.085, 0.0)) * u, (0.08 * u, 0.012 * u, 0.025 * u), "Emit_Hover")
            for sx in (-1, 1):
                for sy in (-1, 1):
                    r = d + Vector((sx * 0.13, sy * 0.10, 0.02)) * u
                    part.cyl(r, r + Vector((0, 0, 0.006 * u)), 0.055 * u, "Graphite", 16)
                    part.box(d + Vector((sx * 0.07, sy * 0.05, 0.015)) * u, (0.10 * u, 0.012 * u, 0.01 * u), "Metal", None)
        made.append(part.finish(g, bevel=0.0012))
        self.export(made, "utility_" + kind)
        self.drop(made)

    # ------------------------------------------------------------ the list for the game
    def manifest(self):
        nozzles = [[round(v.x, 4), round(v.y, 4), round(v.z, 4), self.nozzle_r]
                   for n, v in sorted(self.sock.items()) if n.startswith("Socket_Propulsion")]
        data = {"ship": K.NAME, "pieces": self.pieces, "wings": list(self.wings), "tail": self.tail, "nozzles": nozzles}
        with open(os.path.join(self.dir, "%s_modules.json" % self.stem), "w") as f:
            json.dump(data, f, indent=1)
        print("MODULES %s %d pieces, nozzles %s" % (K.NAME, len(self.pieces), nozzles))


def build_modules(ns, wings, palette, tail="above", scale=1.0, nozzle_r=0.15):
    """wings: three of WING_KINDS; palette: (main paint, accent paint, edge paint) of the ship's wings;
    tail: 'above' (fins on the rear deck) or 'below' (ventral fins, for ships with fins on top already)."""
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
