"""Imports the piggy bank's HD frames for the race HUD (Docs: SourceArt/UI/Piggy/README.md).

SourceArt/UI/Piggy/HD2x/frames/<Anim>_NN.png -> /Game/UI/Piggy/T_Piggy_<Anim>_NN: UI texture group, no mipmaps, never
streamed, block-compressed with alpha, at most 512 px in the game (the HD source stays in the asset; raise
max_texture_size for promo captures). UEXRaceHudWidget plays them (idle, blink, coins when the pool grows, the jump and
the celebration on extraction). Run in the editor (Tools > Execute Python Script) or with -run=pythonscript.
"""
import os

import unreal

SRC = unreal.Paths.project_dir() + "SourceArt/UI/Piggy/HD2x/frames/"
DEST = "/Game/UI/Piggy"


def main():
    if not os.path.isdir(SRC):
        unreal.log_warning("PIGGY %s missing" % SRC)
        return
    names = [f[:-4] for f in sorted(os.listdir(SRC)) if f.endswith(".png")]
    tasks = []
    for n in names:
        t = unreal.AssetImportTask()
        t.filename = SRC + n + ".png"
        t.destination_path = DEST
        t.destination_name = "T_Piggy_" + n
        t.automated = True
        t.save = True
        t.replace_existing = True
        tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    done = 0
    for n in names:
        tex = unreal.EditorAssetLibrary.load_asset(DEST + "/T_Piggy_" + n)
        if not tex:
            unreal.log_error("PIGGY T_Piggy_%s MISSING" % n)
            continue
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
        tex.set_editor_property("never_stream", True)
        tex.set_editor_property("max_texture_size", 512)
        unreal.EditorAssetLibrary.save_loaded_asset(tex)
        done += 1
    unreal.log("PIGGY imported %d of %d frames" % (done, len(names)))


main()
