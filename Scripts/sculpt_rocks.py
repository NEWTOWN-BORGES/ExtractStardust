# Sculpts the desert rock set in Blender, one piece at a time, each with its own shape, size and seed:
# mesas, buttes, spires, canyon cliff walls and boulders. Mesas, buttes and cliffs are massive sandstone
# (Navajo, Wingate) as in the Utah references: vertical walls split by a few deep joint clefts into broad rounded
# columns whose tops separate, flaring a little into the talus at the foot; no ledges up the walls, no dense
# striations. Spires keep stacked beds (Bryce hoodoos). Detail: erosion, joints and grit displacement.
# Exports one FBX per rock (pivot at ground level) and a sunlit preview of the whole set.
# Usage: blender -b -P sculpt_rocks.py -- <fbx_output_dir> <preview_png>
import bpy
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
PREVIEW = argv[1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rock_lib import boulder, column, finish, sunlit_preview  # noqa: E402

# Alcoves are off for now: as round scoops they read as "eye sockets" in the game.
WALL = dict(ledge=0.0, grooves=0, groove_depth=0.0, segments=192, flare=0.03, alcoves=0.0)
rocks = []
# Mesas: wide and flat-topped, a deep cleft every ~20 m, ragged rim, spalled alcoves.
rocks.append(finish(column("SM_Mesa_A", 11, 50, 42, 55, bulge=0.2, top_dome=0.02, rim=0.06, joints=20.0, joint_depth=5.0,
                           joint_width=3.0, crenel=0.05, **WALL), 50, 20.0, 1.4, 2.0, 0.25, 0.45))
rocks.append(finish(column("SM_Mesa_B", 23, 60, 38, 40, bulge=0.22, top_dome=0.03, rim=0.06, joints=22.0, joint_depth=5.0,
                           joint_width=3.0, crenel=0.06, **WALL), 60, 22.0, 1.4, 2.0, 0.25, 0.45))
# Butte: tall, rounded top.
rocks.append(finish(column("SM_Butte_A", 37, 24, 18, 65, bulge=0.2, taper=0.1, top_dome=0.12, top_rough=0.04, rim=0.12,
                           joints=12.0, joint_depth=3.0, joint_width=1.8, crenel=0.05, **WALL), 24, 10.0, 1.0, 1.5, 0.2, 0.5))
# Hoodoos: narrow necks under a wider hard caprock, stacked uneven beds (banded on purpose, like Bryce).
rocks.append(finish(column("SM_Spire_A", 41, 8, 7, 42, segments=96, rings=80, cap_rings=8, layers=8, ledge=0.12, bulge=0.3, taper=0.3, spire=0.35, caprock=0.9, top_dome=0.04, grooves=10, groove_depth=0.1), 8, 2.5, 0.8, 0.9, 0.15, 0.55, joint_stretch=8.0))
rocks.append(finish(column("SM_Spire_B", 53, 6, 5, 30, segments=96, rings=64, cap_rings=8, layers=5, ledge=0.16, bulge=0.35, taper=0.15, spire=0.8, grooves=8, groove_depth=0.12), 6, 2.0, 0.7, 0.7, 0.12, 0.55, joint_stretch=8.0))
# Canyon cliff walls (Wingate): long walls of rounded columns between joint clefts; the back is buried.
rocks.append(finish(column("SM_Cliff_A", 61, 45, 12, 60, bulge=0.15, top_dome=0.02, rim=0.05, joints=16.0, joint_depth=4.5,
                           joint_width=2.2, crenel=0.07, **WALL), 45, 18.0, 1.4, 2.0, 0.25, 0.45))
rocks.append(finish(column("SM_Cliff_B", 73, 40, 14, 45, bulge=0.18, top_dome=0.03, rim=0.05, joints=14.0, joint_depth=4.0,
                           joint_width=2.0, crenel=0.07, **WALL), 40, 16.0, 1.3, 2.0, 0.25, 0.45))
rocks.append(finish(column("SM_Cliff_C", 89, 55, 10, 75, bulge=0.14, top_dome=0.02, rim=0.05, joints=18.0, joint_depth=4.0,
                           joint_width=2.4, crenel=0.07, **WALL), 55, 20.0, 1.5, 2.0, 0.25, 0.45))
# Boulders: blocks fallen onto the talus.
rocks.append(boulder("SM_Boulder_A", 3, 3.0, 0.7))
rocks.append(boulder("SM_Boulder_B", 5, 5.5, 0.55))
rocks.append(boulder("SM_Boulder_C", 7, 1.8, 0.8))

for obj in rocks:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(OUT, obj.name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_scale_options='FBX_SCALE_UNITS',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', use_mesh_modifiers=True)
    print("ROCK", obj.name, len(obj.data.polygons), "faces", round(obj.dimensions.x), round(obj.dimensions.y), round(obj.dimensions.z))

# Preview: the set in a row, lit like the game.
x = 0.0
for obj in rocks:
    width = obj.dimensions.x
    obj.location.x = x + width * 0.5
    x += width + 8.0
sunlit_preview(rocks, [(PREVIEW, (x * 0.5, -x * 0.95, x * 0.1), (x * 0.5, 0.0, 20.0), 35)], (1800, 650))
print("SCULPT DONE")
