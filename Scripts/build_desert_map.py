# Builds /Game/Maps/DesertCanyon from code inside the editor, then closes the editor.
# Run: UnrealEditor.exe <project> -ExecutePythonScript=<path to this file>
import unreal

ok = unreal.EXDesertBuilder.build_desert_map()
unreal.log("EXBUILD python result %s" % ok)
unreal.SystemLibrary.quit_editor()
