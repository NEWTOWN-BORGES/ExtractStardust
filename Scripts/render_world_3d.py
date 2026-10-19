# Oblique 3D views of the whole 10 x 8 km world, in the style of the side-by-side comparison (height colours, sun).
# blender -b -P render_world_3d.py -- <world dir with world_height16.png + canyon_field.json>  (writes mundo_3d_*.png there)
import bpy, numpy as np, json, sys, math

D = sys.argv[sys.argv.index("--") + 1:][0]
CELL = 8.0
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
js = json.load(open(f"{D}/canyon_field.json"))
zlo, zhi = js["z_m"]
SX, SY = js["size_x_m"], js["size_y_m"]
img = bpy.data.images.load(f"{D}/world_height16.png")
img.colorspace_settings.name = "Non-Color"
w, h = img.size
px = np.empty(w * h * 4, np.float32)
img.pixels.foreach_get(px)
s = int(round(CELL / js["cell_m"]))
Hm = (zlo + px.reshape(h, w, 4)[:, :, 0] * (zhi - zlo))[::s, ::s]

STOPS = [(-70, (0.55, 0.40, 0.28)), (0, (0.88, 0.68, 0.45)), (25, (0.86, 0.60, 0.38)), (60, (0.78, 0.42, 0.22)),
         (150, (0.66, 0.30, 0.15)), (330, (0.84, 0.58, 0.40))]
ny, nx = Hm.shape
xs, ys = np.meshgrid(np.arange(nx) * CELL, np.arange(ny) * CELL)
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
nt = mat.node_tree
at = nt.nodes.new("ShaderNodeAttribute")
at.attribute_name = "Col"
nt.links.new(at.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
me.materials.append(mat)
sc.collection.objects.link(bpy.data.objects.new("world", me))

# The circuit as a thin orange ribbon just above the ground.
pts = np.array(js["circuit"]["points"], float)
cu = bpy.data.curves.new("circuit", "CURVE")
cu.dimensions = "3D"
cu.bevel_depth = 9.0
sp = cu.splines.new("POLY")
sp.points.add(len(pts) - 1)
gx = np.clip(((pts[:, 0] + SX / 2) / CELL).astype(int), 0, nx - 1)
gy = np.clip(((pts[:, 1] + SY / 2) / CELL).astype(int), 0, ny - 1)
for k, (p, zx) in enumerate(zip(pts, Hm[gy, gx])):
    sp.points[k].co = (p[0] + SX / 2, p[1] + SY / 2, max(p[2], zx) + 6.0, 1.0)
sp.use_cyclic_u = True
cm = bpy.data.materials.new("circuit")
cm.use_nodes = True
em = cm.node_tree.nodes.new("ShaderNodeEmission")
em.inputs["Color"].default_value = (1.0, 0.35, 0.02, 1)
em.inputs["Strength"].default_value = 2.0
cm.node_tree.links.new(em.outputs[0], cm.node_tree.nodes["Material Output"].inputs[0])
cu.materials.append(cm)
sc.collection.objects.link(bpy.data.objects.new("circuit", cu))

sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(55), 0, math.radians(-135))
sc.collection.objects.link(sun)
wd = bpy.data.worlds.new("w")
wd.use_nodes = True
wd.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.68, 0.85, 1)
wd.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
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

VIEWS = {
    "sul": ((5000, -5600, 5200), (62, 0, 0)),
    "sudoeste": ((-2600, -3600, 3200), (73, 0, -45)),
    "noroeste_canyons": ((-1800, 10200, 2600), (66, 0, -133)),
}
for name, (loc, rot) in VIEWS.items():
    cam.location = loc
    cam.rotation_euler = tuple(math.radians(a) for a in rot)
    sc.render.filepath = f"{D}/mundo_3d_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("VIEW", name)
print("WORLD3D DONE")
