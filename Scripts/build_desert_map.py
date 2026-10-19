# Builds /Game/Maps/DesertCanyon from code inside the editor, then closes the editor:
# 1. bakes the surface map from the terrain description, 2. rebuilds the landscape material that reads it,
# 3. builds the map (landscape, S01 geology, vegetation, sky).
# Run: UnrealEditor.exe <project> /Engine/Maps/Entry -ExecutePythonScript=<path to this file>
# (import_rocks.py, import_s01.py must have run once before, and after every re-sculpt.)
import unreal

ok = unreal.EXDesertBuilder.build_surface_map()
unreal.log("EXBUILD surface map %s" % ok)
scripts = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "Scripts/"
exec(open(scripts + "make_desert_material.py").read())
ok = unreal.EXDesertBuilder.build_desert_map()
unreal.log("EXBUILD python result %s" % ok)
unreal.SystemLibrary.quit_editor()
