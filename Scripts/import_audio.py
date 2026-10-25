"""Import short, non-looping ship audio cues for the beta."""

import os
import unreal


project_dir = unreal.Paths.project_dir()
source_dir = os.path.join(project_dir, "SourceArt", "Audio")
destination = "/Game/Audio"
assets = [
    ("engine_loop.wav", "SW_EngineLoop", False),
    ("drift_loop.wav", "SW_DriftLoop", False),
    ("nitro_burst.wav", "SW_NitroBurst", False),
]
tasks = []

for filename, asset_name, _ in assets:
    source = os.path.join(source_dir, filename)
    if not os.path.isfile(source):
        raise RuntimeError("Missing generated sound file: " + source)
    task = unreal.AssetImportTask()
    task.filename = source
    task.destination_path = destination
    task.destination_name = asset_name
    task.automated = True
    task.save = True
    task.replace_existing = True
    tasks.append(task)

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

for _, asset_name, looping in assets:
    asset_path = destination + "/" + asset_name
    sound = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not sound:
        raise RuntimeError("Imported sound asset missing: " + asset_path)
    sound.set_editor_property("looping", looping)
    if not unreal.EditorAssetLibrary.save_asset(asset_path):
        raise RuntimeError("Could not save sound asset: " + asset_path)
    unreal.log("EX_AUDIO imported %s looping=%s" % (asset_path, looping))
