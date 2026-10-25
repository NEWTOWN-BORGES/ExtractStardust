"""Refresh beta audio and no-image-texture materials without reimporting map or kit meshes."""

import os
import unreal


scripts_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "Scripts/"
for script_name in ("import_audio.py", "make_rock_material.py", "make_ground_material.py"):
    script_path = scripts_dir + script_name
    with open(script_path, "r", encoding="utf-8") as source:
        exec(compile(source.read(), script_path, "exec"), {"__name__": "__main__"})
    unreal.log("BETA_REFRESH completed %s" % script_name)

unreal.log("BETA_REFRESH audio cues are one-shot; landscape and kit materials use no image textures")
