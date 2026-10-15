"""Importa um lote limitado de FBX das pistas e regista o resultado."""
import glob
import os
import unreal

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ART = os.path.join(PROJECT_ROOT, "SourceAssets", "Unity", "Art", "Export")
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
REPORT = []

COURSES = [
    ("red_dust_divide", "RedDustDivide"),
    ("sandbox", "Sandbox"),
]
ALL_MESHES = []
for source_folder, destination_folder in COURSES:
    source_dir = os.path.join(ART, source_folder)
    for filename in sorted(glob.glob(os.path.join(source_dir, "*.fbx"))):
        asset_name = os.path.splitext(os.path.basename(filename))[0]
        asset_path = "/Game/Stardust/Courses/{}/{}".format(destination_folder, asset_name)
        ALL_MESHES.append((filename, destination_folder, asset_name, asset_path))

BATCH_START = int(globals().get("BATCH_START", 0))
BATCH_COUNT = int(globals().get("BATCH_COUNT", 3))
BATCH = ALL_MESHES[BATCH_START:BATCH_START + BATCH_COUNT]


def set_if_supported(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception:
        pass


def import_mesh(filename, destination_folder, asset_name, asset_path):
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        REPORT.append("JA EXISTIA | {}".format(asset_path))
        return

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", filename)
    task.set_editor_property("destination_path", "/Game/Stardust/Courses/{}".format(destination_folder))
    task.set_editor_property("destination_name", asset_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)

    options = unreal.FbxImportUI()
    set_if_supported(options, "import_mesh", True)
    set_if_supported(options, "import_as_skeletal", False)
    set_if_supported(options, "import_materials", False)
    set_if_supported(options, "import_textures", False)
    set_if_supported(options, "mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    static_data = options.get_editor_property("static_mesh_import_data")
    set_if_supported(static_data, "combine_meshes", True)
    set_if_supported(static_data, "auto_generate_collision", False)
    set_if_supported(static_data, "generate_lightmap_u_vs", False)
    task.set_editor_property("options", options)

    try:
        TOOLS.import_asset_tasks([task])
        imported = task.get_editor_property("imported_object_paths")
        if imported:
            REPORT.append("OK | {} | {}".format(os.path.basename(filename), imported[0]))
        else:
            REPORT.append("FALHOU | {} | nenhum asset".format(filename))
    except Exception as exc:
        REPORT.append("FALHOU | {} | {}".format(filename, exc))


for item in BATCH:
    unreal.log("Extract Stardust: importacao de pista {}".format(item[0]))
    import_mesh(*item)

report_path = os.path.join(PROJECT_ROOT, "Docs", "IMPORTACAO_CURSOS.txt")
with open(report_path, "a", encoding="utf-8") as report_file:
    report_file.write("\nLOTE | inicio={} | quantidade={}\n".format(BATCH_START, len(BATCH)))
    report_file.write("\n".join(REPORT) + "\n")
unreal.log("Extract Stardust: lote concluido. Relatorio: {}".format(report_path))