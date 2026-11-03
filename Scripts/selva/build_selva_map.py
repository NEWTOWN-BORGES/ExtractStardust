# Builds /Game/Maps/Selva (Mapa 02 Selva Esmeralda) from the folder export_selva_unreal.py wrote, then closes the editor.
# Needs the full editor (not the commandlet):
#   UnrealEditor.exe <project>.uproject -ExecutePythonScript=<project>/Scripts/selva/build_selva_map.py
# Folder from EX_WORLD_DIR (default C:/rdd/selva/ue); EX_QUIT=0 keeps the editor open.
import os

import unreal

folder = os.environ.get("EX_WORLD_DIR", "C:/rdd/selva/ue")
ok = unreal.EXDesertBuilder.build_world_map(folder, "Selva")
unreal.log("SELVA MAP BUILT" if ok else "SELVA MAP FAILED")
if os.environ.get("EX_QUIT", "1") == "1":
    unreal.SystemLibrary.quit_editor()
