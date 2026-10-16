import glob
import json
import os
import sys

import unreal


DESTINATION_PATH = "/Game/Environment/Generated/RedDustDivide"


def log(message):
    unreal.log("[RedDustDivideImport] " + str(message))


def write_report(generated_dir, success, imported_count, failures, error=""):
    report_path = os.path.join(generated_dir, "unreal_import_report.json")
    with open(report_path, "w", encoding="utf-8") as report_file:
        json.dump(
            {
                "success": success,
                "imported_assets": imported_count,
                "failed_sources": sorted(set(failures)),
                "error": error,
            },
            report_file,
            indent=2,
        )


def import_assets():
    generated_dir = os.environ.get("RDD_GENERATED_DIR")
    if not generated_dir:
        generated_dir = os.path.join(unreal.Paths.project_saved_dir(), "GeneratedCourse", "red_dust_divide")
    generated_dir = os.path.abspath(generated_dir)
    if not os.path.isdir(generated_dir):
        raise RuntimeError("Generated course folder does not exist: " + generated_dir)

    source_files = sorted(
        glob.glob(os.path.join(generated_dir, "red_dust_divide_corridor_*.fbx"))
        + glob.glob(os.path.join(generated_dir, "red_dust_divide_terrain_*.fbx"))
    )
    if not source_files:
        raise RuntimeError("No corridor or terrain FBX files found in: " + generated_dir)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    tasks = []
    for source_file in source_files:
        options = unreal.FbxImportUI()
        options.set_editor_property("import_mesh", True)
        options.set_editor_property("import_as_skeletal", False)
        options.set_editor_property("import_materials", False)
        options.set_editor_property("import_textures", False)

        mesh_options = options.get_editor_property("static_mesh_import_data")
        mesh_options.set_editor_property("combine_meshes", True)
        mesh_options.set_editor_property("auto_generate_collision", False)
        mesh_options.set_editor_property("generate_lightmap_u_vs", True)

        task = unreal.AssetImportTask()
        task.set_editor_property("filename", source_file)
        task.set_editor_property("destination_path", DESTINATION_PATH)
        task.set_editor_property("destination_name", os.path.splitext(os.path.basename(source_file))[0])
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("save", True)
        task.set_editor_property("options", options)
        task.set_editor_property("factory", unreal.FbxFactory())
        tasks.append(task)

    log("Importing {} sector FBX files from {}".format(len(tasks), generated_dir))
    asset_tools.import_asset_tasks(tasks)

    imported_paths = []
    failures = []
    for source_file, task in zip(source_files, tasks):
        paths = task.get_editor_property("imported_object_paths")
        if not paths:
            failures.append(os.path.basename(source_file))
            continue
        imported_paths.extend(paths)
        for asset_path in paths:
            asset = unreal.EditorAssetLibrary.load_asset(asset_path)
            if not isinstance(asset, unreal.StaticMesh):
                failures.append(os.path.basename(source_file))
                continue
            bounds = asset.get_bounds()
            log("{} bounds origin={} extent={}".format(
                asset_path,
                bounds.origin,
                bounds.box_extent,
            ))

    unreal.EditorAssetLibrary.save_directory(DESTINATION_PATH, only_if_is_dirty=False)
    log("Imported {} assets into {}".format(len(imported_paths), DESTINATION_PATH))
    if failures:
        raise RuntimeError("FBX import failed for: " + ", ".join(sorted(set(failures))))
    return len(imported_paths), generated_dir


generated_dir = os.environ.get("RDD_GENERATED_DIR")
try:
    imported_count, generated_dir = import_assets()
    write_report(generated_dir, True, imported_count, [])
except Exception as error:
    log("ERROR: " + str(error))
    unreal.log_error(str(error))
    if generated_dir and os.path.isdir(generated_dir):
        write_report(generated_dir, False, 0, [], str(error))
    sys.exit(1)
finally:
    unreal.SystemLibrary.quit_editor()
