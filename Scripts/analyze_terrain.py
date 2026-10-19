# Measures a downloaded terrain .blend: objects, modifiers, materials/textures, height and slope
# distribution, and writes a top-down heightmap + hillshade PNG for study.
# Usage: blender -b --disable-autoexec <file.blend> --python analyze_terrain.py -- <out_prefix>
import bpy, sys, json, math
import numpy as np

out = sys.argv[sys.argv.index("--") + 1]
report = {"file": bpy.data.filepath, "objects": [], "materials": {}}

for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    nodes = {}
    images = []
    for n in mat.node_tree.nodes:
        nodes[n.bl_idname] = nodes.get(n.bl_idname, 0) + 1
        if n.bl_idname == "ShaderNodeTexImage" and n.image:
            images.append([n.image.name, list(n.image.size), n.image.colorspace_settings.name])
    report["materials"][mat.name] = {"nodes": nodes, "images": images}

dg = bpy.context.evaluated_depsgraph_get()
all_xyz = []
for ob in bpy.data.objects:
    entry = {"name": ob.name, "type": ob.type, "dims": [round(d, 1) for d in ob.dimensions],
             "modifiers": [[m.type, m.name] for m in ob.modifiers],
             "materials": [s.material.name for s in ob.material_slots if s.material]}
    if ob.type == "MESH":
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        nv, nf = len(me.vertices), len(me.polygons)
        entry["verts"], entry["faces"] = nv, nf
        if nv:
            co = np.empty(nv * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            mw = np.array(ob.matrix_world, np.float32)
            co = co @ mw[:3, :3].T + mw[:3, 3]
            all_xyz.append(co)
            if nf:
                fn = np.empty(nf * 3, np.float32); me.polygons.foreach_get("normal", fn); fn = fn.reshape(-1, 3)
                fn = fn @ mw[:3, :3].T
                fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-9
                area = np.empty(nf, np.float32); me.polygons.foreach_get("area", area)
                fc = np.empty(nf * 3, np.float32); me.polygons.foreach_get("center", fc); fc = fc.reshape(-1, 3)
                fc = fc @ mw[:3, :3].T + mw[:3, 3]
                slope = np.degrees(np.arccos(np.clip(fn[:, 2], -1, 1)))
                tot = area.sum()
                bins = [(0, 10, "flat 0-10"), (10, 25, "gentle 10-25"), (25, 45, "talus 25-45"),
                        (45, 70, "steep 45-70"), (70, 181, "cliff 70+")]
                entry["slope_area_pct"] = {lbl: round(100 * area[(slope >= a) & (slope < b)].sum() / tot, 1) for a, b, lbl in bins}
                # Height at which flat ground sits (benches/terraces): area-weighted histogram of flat faces.
                flat = slope < 12
                z = fc[:, 2]
                zmin, zmax = float(z.min()), float(z.max())
                hist, edges = np.histogram(z[flat], bins=24, range=(zmin, zmax), weights=area[flat])
                entry["flat_area_by_height"] = [[round(float(edges[i]), 1), round(100 * float(hist[i]) / max(tot, 1e-9), 1)] for i in range(24)]
                # Cliff heights: vertical extent of steep faces per height band.
                steep = slope > 60
                h2, _ = np.histogram(z[steep], bins=24, range=(zmin, zmax), weights=area[steep])
                entry["cliff_area_by_height"] = [round(100 * float(v) / max(tot, 1e-9), 1) for v in h2]
                entry["z_percentiles"] = {p: round(float(np.percentile(co[:, 2], p)), 1) for p in (0, 5, 25, 50, 75, 95, 100)}
        ev.to_mesh_clear()
    report["objects"].append(entry)

# Heightmap + hillshade from all mesh vertices.
if all_xyz:
    co = np.concatenate(all_xyz)
    R = 512
    x0, y0 = co[:, 0].min(), co[:, 1].min()
    span = max(co[:, 0].max() - x0, co[:, 1].max() - y0, 1e-3)
    ix = np.clip(((co[:, 0] - x0) / span * (R - 1)).astype(int), 0, R - 1)
    iy = np.clip(((co[:, 1] - y0) / span * (R - 1)).astype(int), 0, R - 1)
    h = np.full((R, R), -np.inf, np.float32)
    np.maximum.at(h, (iy, ix), co[:, 2])
    # Fill holes from neighbours a few times.
    for _ in range(6):
        m = ~np.isfinite(h)
        if not m.any():
            break
        p = np.pad(h, 1, constant_values=-np.inf)
        nb = np.max(np.stack([p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]]), axis=0)
        h[m] = nb[m]
    h[~np.isfinite(h)] = np.nanmin(h[np.isfinite(h)])
    zlo, zhi = float(h.min()), float(h.max())
    hn = (h - zlo) / max(zhi - zlo, 1e-6)
    cell = span / R
    gy, gx = np.gradient(h, cell)
    az, alt = math.radians(315), math.radians(35)
    shade = np.clip(math.sin(alt) / np.sqrt(1 + gx**2 + gy**2) +
                    math.cos(alt) * (-gx * math.cos(az) - gy * math.sin(az)) / np.sqrt(1 + gx**2 + gy**2), 0, 1)
    for name, data in (("height", hn), ("shade", shade)):
        img = bpy.data.images.new(name, R, R, alpha=False, float_buffer=False)
        px = np.ones((R, R, 4), np.float32)
        px[..., 0] = px[..., 1] = px[..., 2] = data
        img.pixels.foreach_set(px.ravel())
        img.filepath_raw = f"{out}_{name}.png"
        img.file_format = "PNG"
        img.save()
    report["heightmap"] = {"span_m": round(float(span), 1), "z_range_m": [round(zlo, 1), round(zhi, 1)], "res": R}

with open(out + "_report.json", "w") as f:
    json.dump(report, f, indent=1)
print("ANALYZED", out)
