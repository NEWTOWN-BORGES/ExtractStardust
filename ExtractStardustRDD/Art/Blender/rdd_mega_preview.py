"""
Pré-visualização das megaestruturas (rdd_mega_kit.py): alinhadas lado a lado com uma nave à escala (6,4 m, vermelha).
  blender -b --factory-startup -P rdd_mega_preview.py -- <saida.png>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

PNG = os.path.abspath(sys.argv[sys.argv.index('--') + 1])
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], '--', PNG.replace('.png', '_tmp.fbx')]
exec(compile(open(os.path.join(HERE, 'rdd_mega_kit.py'), encoding='utf-8').read(), 'rdd_mega_kit.py', 'exec'), globals())

cols = {'Mega_Metal': (0.42, 0.44, 0.47), 'Mega_Rust': (0.47, 0.25, 0.14), 'Mega_Dark': (0.12, 0.12, 0.13), 'Mega_Glow': (1.0, 0.55, 0.2), 'Mega_Cloth': (0.62, 0.08, 0.06)}
for n, c in cols.items():
    if n in bpy.data.materials:
        bpy.data.materials[n].diffuse_color = (*c, 1.0)
place = {'M_Ring': (0, 0, -18, 0), 'M_Hull': (230, 40, -6, 70), 'M_Tower_A': (400, 0, 0, 20), 'M_Gate': (580, 0, 0, 0), 'M_Tower_B': (760, 30, 0, -15), 'M_Pipeline': (900, 0, 0, 90)}
for ob in bpy.context.scene.objects:
    if ob.name in place:
        x, y, z, yaw = place[ob.name]
        ob.location = (x, y, z)
        ob.rotation_euler = (0, 0, math.radians(yaw))
        if ob.name == 'M_Hull':
            ob.rotation_euler = (0, math.radians(14), math.radians(yaw))
# nave à escala e chão
bpy.ops.mesh.primitive_cube_add(size=1, location=(580, -40, 1.0))
ship = bpy.context.active_object
ship.scale = (3.1, 6.4, 1.2)
m = bpy.data.materials.new('Ship')
m.diffuse_color = (0.8, 0.1, 0.06, 1)
ship.data.materials.append(m)
bpy.ops.mesh.primitive_plane_add(size=6000, location=(450, 0, 0))
g = bpy.context.active_object
gm = bpy.data.materials.new('Ground')
gm.diffuse_color = (0.72, 0.5, 0.33, 1)
g.data.materials.append(gm)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'MATERIAL'
sc.display.shading.show_shadows = True
sc.display.shading.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = 2400, 900
cam_data = bpy.data.cameras.new('cam')
cam_data.lens = 35
cam = bpy.data.objects.new('cam', cam_data)
sc.collection.objects.link(cam)
cam.location = (450, -900, 260)
direction = Vector((450, 40, 40)) - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam
sc.world = bpy.data.worlds.new('w')
sc.world.color = (0.78, 0.74, 0.7)
sc.render.filepath = PNG
bpy.ops.render.render(write_still=True)
print('[mega] preview', PNG, flush=True)
