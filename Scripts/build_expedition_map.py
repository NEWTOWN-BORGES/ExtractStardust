# Builds /Game/Maps/Expedition (the A->B track) from the folder export_ab_unreal.py wrote, then closes the editor.
# Needs the full editor (not the commandlet):
#   UnrealEditor.exe <project>.uproject -ExecutePythonScript=<project>/Scripts/build_expedition_map.py
# Folder from EX_WORLD_DIR (default C:/rdd/ab/ue); EX_QUIT=0 keeps the editor open.
import os

import unreal

folder = os.environ.get("EX_WORLD_DIR", "C:/rdd/ab/ue")
ok = unreal.EXDesertBuilder.build_world_map(folder, "Expedition")
unreal.log("EXPEDITION MAP BUILT" if ok else "EXPEDITION MAP FAILED")
if os.environ.get("EX_QUIT", "1") == "1":
    unreal.SystemLibrary.quit_editor()
