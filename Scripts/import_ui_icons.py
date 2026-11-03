"""Imports the interface art into the Unreal project.

- SourceArt/UI/Icons/<name>.png (Scripts/make_ui_icons.py) -> /Game/UI/Icons/T_Icon_<name>: icons and art, no mipmaps,
  UI texture group, uncompressed so the soft glows keep their edges (EXUi::Icon).
- SourceArt/UI/Thumbs/<ship>_<key>.jpg (Scripts/render_modules.py ... thumbs) -> /Game/UI/Thumbs/T_Thumb_<ship>_<key>:
  the photo of each ship with each module fitted, for the hangar's cards (EXUi::Thumb). Run in the editor (Tools > Execute Python Script) or with
-ExecutePythonScript / -run=pythonscript, as the other import scripts.
"""
import os

import unreal

ROOT = unreal.Paths.project_dir() + "SourceArt/UI/"


def bring(folder, ext, dest, prefix, compress):
    src = ROOT + folder + "/"
    if not os.path.isdir(src):
        unreal.log_warning("UIART %s missing" % src)
        return
    tasks, names = [], []
    for f in sorted(os.listdir(src)):
        if not f.endswith(ext):
            continue
        t = unreal.AssetImportTask()
        t.filename = src + f
        t.destination_path = dest
        t.destination_name = prefix + f[:-len(ext)]
        t.automated = True
        t.save = True
        t.replace_existing = True
        tasks.append(t)
        names.append(f[:-len(ext)])
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    done = 0
    for name in names:
        tex = unreal.EditorAssetLibrary.load_asset(dest + "/" + prefix + name)
        if not tex:
            unreal.log_error("UIART %s%s MISSING" % (prefix, name))
            continue
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT if compress
                                else unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
        tex.set_editor_property("never_stream", True)
        unreal.EditorAssetLibrary.save_loaded_asset(tex)
        done += 1
    unreal.log("UIART %s imported %d of %d" % (folder, done, len(names)))


bring("Icons", ".png", "/Game/UI/Icons", "T_Icon_", False)
bring("Thumbs", ".jpg", "/Game/UI/Thumbs", "T_Thumb_", True)
