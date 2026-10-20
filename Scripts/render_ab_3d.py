# Oblique 3D views of the A -> B expedition in the style of render_world_3d.py (height colours, sun), with the main
# line coloured by sector and the branches in white.
# blender -b -P render_ab_3d.py -- <dir with ab_height16.png + ab_route.json>  (writes ab_3d_*.png there)
import bpy, numpy as np, json, sys, math

D = sys.argv[sys.argv.index("--") + 1:][0]
CELL = 10.0
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
js = json.load(open(f"{D}/ab_route.json"))
zlo, zhi = js["z_m"]
SX, SY = js["size_m"]
img = bpy.data.images.load(f"{D}/ab_height16.png")
img.colorspace_settings.name = "Non-Color"
w, h = img.size
px = np.empty(w * h * 4, np.float32)
img.pixels.foreach_get(px)
s = max(1, int(round(CELL / js["cell_m"])))
Hm = (zlo + px.reshape(h, w, 4)[:, :, 0] * (zhi - zlo))[::s, ::s]
STOPS = [(0, (0.80, 0.55, 0.35)), (90, (0.76, 0.48, 0.28)), (200, (0.66, 0.32, 0.16)), (235, (0.82, 0.70, 0.54)),
         (270, (0.78, 0.62, 0.44)), (400, (0.64, 0.32, 0.17)), (470, (0.82, 0.58, 0.38)), (700, (0.60, 0.40, 0.30))]
ny, nx = Hm.shape
cs = js["cell_m"] * s
xs, ys = np.meshgrid(np.arange(nx) * cs, np.arange(ny) * cs)
co = np.stack([xs, ys, Hm], -1).reshape(-1, 3).astype(np.float32)
i = np.arange(ny * nx).reshape(ny, nx)
quads = np.stack([i[:-1, :-1], i[:-1, 1:], i[1:, 1:], i[1:, :-1]], -1).reshape(-1, 4)
me = bpy.data.meshes.new("world")
me.vertices.add(len(co))
me.vertices.foreach_set("co", co.ravel())
me.loops.add(quads.size)
me.loops.foreach_set("vertex_index", quads.ravel().astype(np.int32))
me.polygons.add(len(quads))
me.polygons.foreach_set("loop_start", (np.arange(len(quads)) * 4).astype(np.int32))
me.update(calc_edges=True)
me.shade_smooth()
zs = np.array([t[0] for t in STOPS], float)
rgb = np.stack([np.interp(Hm.ravel(), zs, [t[1][c] for t in STOPS]) for c in range(3)] + [np.ones(Hm.size)], -1)
ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
ca.data.foreach_set("color", rgb.astype(np.float32).ravel())
mat = bpy.data.materials.new("ground")
mat.use_nodes = True
at = mat.node_tree.nodes.new("ShaderNodeAttribute")
at.attribute_name = "Col"
mat.node_tree.links.new(at.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
me.materials.append(mat)
sc.collection.objects.link(bpy.data.objects.new("world", me))
COLS = [(0.95, 0.85, 0.30), (0.95, 0.55, 0.15), (0.90, 0.25, 0.10), (0.75, 0.10, 0.10), (0.55, 0.25, 0.75),
        (0.20, 0.45, 0.95), (0.15, 0.75, 0.85), (0.10, 0.10, 0.10), (0.95, 0.75, 0.55), (0.35, 0.80, 0.30)]


def ribbon(name, pts, colour, depth):
    pts = np.asarray(pts, float)
    if len(pts) < 2:
        return
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = depth
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for k, (x, y, z) in enumerate(pts):
        sp.points[k].co = (x + SX / 2, y + SY / 2, z + 6.0, 1.0)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    em = m.node_tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*colour, 1)
    em.inputs["Strength"].default_value = 2.0
    m.node_tree.links.new(em.outputs[0], m.node_tree.nodes["Material Output"].inputs[0])
    cu.materials.append(m)
    sc.collection.objects.link(bpy.data.objects.new(name, cu))


mp = np.array(js["main"]["points"])
msec = np.array(js["main"]["sector"])
for k in range(len(js["sectors"])):
    ii = np.flatnonzero(msec == k)
    if len(ii):
        ribbon(f"S{k + 1}", mp[max(0, ii[0] - 1):ii[-1] + 1][::2], COLS[k % len(COLS)], 18.0)
for nm, b in js["branches"].items():
    ribbon(nm, np.array(b["points"])[::2], (1.0, 1.0, 1.0), 11.0)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(55), 0, math.radians(-135))
sc.collection.objects.link(sun)
wd = bpy.data.worlds.new("w")
wd.use_nodes = True
wd.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.68, 0.85, 1)
wd.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
sc.world = wd
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 30
cam.data.clip_end = 100000
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 24
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.view_settings.view_transform = "Standard"
VIEWS = {"sul": ((8000, -7600, 7600), (60, 0, 0)), "sudoeste": ((-3800, -4800, 5200), (70, 0, -45)),
         "nordeste": ((19800, 16000, 5600), (68, 0, 140))}
for name, (loc, rot) in VIEWS.items():
    cam.location = loc
    cam.rotation_euler = tuple(math.radians(v) for v in rot)
    sc.render.filepath = f"{D}/ab_3d_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("VIEW", name)
print("AB3D DONE")
