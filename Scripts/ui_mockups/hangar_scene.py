# blender -b -P Scripts/ui_mockups/hangar_scene.py -- <out.png>   (or python3 with the bpy module)
# The lit workshop of AEXHangarStage (approximate) with the VORTEX on the turntable and its cyan ring, for the UI mock-ups.
import math, os, sys, bpy
R = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/'
OUT = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def mat(name, col, rough=0.6, metal=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = col + (1,)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = emit + (1,)
        b.inputs['Emission Strength'].default_value = strength
    return m

def box(loc, dims, m, rot=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=(0, 0, rot))
    o = bpy.context.object; o.dimensions = dims
    o.data.materials.append(m); return o

def cyl(loc, r, h, m, verts=96):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc)
    o = bpy.context.object; o.data.materials.append(m); return o

floor = mat('Floor', (0.30, 0.31, 0.33), 0.35)
line = mat('Line', (0.16, 0.16, 0.17), 0.6)
yellow = mat('Yellow', (0.85, 0.62, 0.05), 0.5)
wall = mat('Wall', (0.40, 0.41, 0.44), 0.7)
rib = mat('Rib', (0.36, 0.37, 0.40), 0.5, 0.4)
dark = mat('Dark', (0.08, 0.08, 0.09), 0.4, 0.3)
plat = mat('Platform', (0.16, 0.17, 0.19), 0.35, 0.5)
panel = mat('Panel', (1.0, 0.97, 0.92), 0.5, 0, (1.0, 0.97, 0.92), 9.0)
ring = mat('Ring', (0.1, 0.75, 1.0), 0.3, 0, (0.1, 0.75, 1.0), 18.0)
cab = mat('Cabinet', (0.60, 0.06, 0.04), 0.5, 0.2)
crate = mat('Crate', (0.90, 0.32, 0.06), 0.6)
steel = mat('Steel', (0.50, 0.52, 0.55), 0.35, 0.8)
RX, RY, RH = 32.0, 28.0, 10.0
box((0, 0, -0.05), (RX, RY, 0.1), floor)
for k in range(-7, 8):                       # floor seams
    box((k * 2.2, 0, 0.002), (0.03, RY, 0.004), line)
    box((0, k * 2.0, 0.002), (RX, 0.03, 0.004), line)
for s in (-1, 1):                             # yellow lanes either side of the turntable
    box((s * 6.2, 0, 0.004), (0.18, RY * 0.8, 0.006), yellow)
box((0, -RY / 2, RH / 2), (RX, 0.2, RH), wall)      # back wall (the camera looks to -Y)
box((-RX / 2, 0, RH / 2), (0.2, RY, RH), wall); box((RX / 2, 0, RH / 2), (0.2, RY, RH), wall)
box((0, 0, RH), (RX, RY, 0.2), wall)
for k in range(-6, 7):                        # ribs on the walls
    box((k * 2.6, -RY / 2 + 0.25, RH / 2), (0.35, 0.3, RH), rib)
for k in range(-5, 6):
    box((-RX / 2 + 0.25, k * 2.6, RH / 2), (0.3, 0.35, RH), rib)
    box((RX / 2 - 0.25, k * 2.6, RH / 2), (0.3, 0.35, RH), rib)
for i in range(-2, 3):                        # light panels in the ceiling
    for j in range(-2, 3):
        box((i * 6.0, j * 5.0, RH - 0.15), (3.2, 1.0, 0.06), panel)
box((0, -RY / 2 + 0.4, 7.2), (9.0, 0.06, 1.0), ring)  # the sign glow on the back wall
box((0, -RY / 2 + 0.45, 5.0), (14.0, 0.1, 0.25), dark)
cyl((0, 0, 0.11), 4.4, 0.22, plat)               # the turntable and its ring
cyl((0, 0, 0.23), 4.63, 0.05, ring)
cyl((0, 0, 0.245), 4.5, 0.06, plat)
for x, y, r in ((-11, -9, 0.2), (-12.5, -6, -0.1), (11, -10, 0.15), (12.2, -7.5, 0.05)):
    box((x, y, 0.6), (1.6, 1.2, 1.2), crate, r)
box((-13, -12.5, 1.1), (3.0, 0.8, 2.2), cab); box((13, -12.5, 1.1), (3.0, 0.8, 2.2), cab)
box((-8.5, -12.8, 1.6), (0.12, 0.12, 3.2), steel); box((8.5, -12.8, 1.6), (0.12, 0.12, 3.2), steel)
# the ship, nose to -Y turned a little towards the camera
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=R + 'SourceArt/TestShips/vortex.fbx')
root = bpy.data.objects.new('ship', None); sc.collection.objects.link(root)
for o in bpy.data.objects:
    if o not in before and o.parent is None and o is not root:
        o.parent = root
root.rotation_euler = (0, 0, math.radians(-32))
bpy.context.view_layer.update()
import mathutils
pts = [o.matrix_world @ mathutils.Vector(v) for o in bpy.data.objects if o.type == 'MESH' and o not in before for v in o.bound_box]
pts = [p for p in pts]
lo = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
mid = (lo + hi) / 2
root.location = (-mid.x, -mid.y, 1.0 - lo.z)
# lights: the workshop is lit (key warm, fill cool, top)
def area(loc, size, energy, col, rot=(0, 0, 0)):
    l = bpy.data.lights.new('A', 'AREA'); l.size = size; l.energy = energy; l.color = col
    o = bpy.data.objects.new('A', l); sc.collection.objects.link(o); o.location = loc; o.rotation_euler = rot
area((0, 0, RH - 0.3), 14.0, 3500, (1.0, 0.96, 0.9))
area((7, 7, 6.5), 4.0, 2500, (1.0, 0.92, 0.82), (math.radians(-50), math.radians(35), 0))
area((-7, -6, 6.5), 4.0, 1200, (0.86, 0.9, 1.0), (math.radians(50), math.radians(-35), 0))
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.2, 0.2, 0.22, 1)
# the camera of the menu and the hangar: 12.5 m from the ship, 8 degrees down
cd = bpy.data.cameras.new('Cam'); cd.lens = 30
cam = bpy.data.objects.new('Cam', cd); sc.collection.objects.link(cam)
d, pitch = 10.0, math.radians(8)
cam.location = (0, d * math.cos(pitch), 1.9 + d * math.sin(pitch))
cam.rotation_euler = (math.pi / 2 - pitch, 0, math.pi)
sc.camera = cam
sc.render.engine = 'CYCLES'; sc.cycles.samples = 32; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.view_settings.view_transform = 'AgX'
for look in ('AgX - Punchy', 'Punchy', 'AgX - Medium High Contrast'):
    try:
        sc.view_settings.look = look
        break
    except Exception:
        pass
sc.view_settings.exposure = -0.4
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('HANGAR', OUT)
