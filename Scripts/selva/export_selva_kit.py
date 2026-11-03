# The jungle kit for Unreal: one FBX per kind (SM_Selva_<kind>.fbx) and its painted textures, from jungle_kit.py.
# Usage: blender -b -P Scripts/selva/export_selva_kit.py -- C:/rdd/selva/kit
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jungle_kit as jk  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "C:/rdd/selva/kit"
bpy.ops.wm.read_factory_settings(use_empty=True)
coll, _mats = jk.build_kit(os.path.join(OUT, "tex"))
jk.export_kit(coll, OUT)
print("SELVA KIT", len([f for f in os.listdir(OUT) if f.endswith(".fbx")]), "meshes in", OUT)
