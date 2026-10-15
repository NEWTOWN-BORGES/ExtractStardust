"""Importa apenas os cinco chassis e cria uma sala de exposicao 3D leve."""
import os
import unreal

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UNITY = os.path.join(PROJECT_ROOT, "SourceAssets", "Unity")
SOURCE = os.path.join(
    UNITY, "Assets", "ExtractStardust", "Vehicles", "V2", "Chassis",
    "Resources", "V2Chassis",
)
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LEVEL_EDITOR = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = []


def import_chassis(name):
    filename = os.path.join(SOURCE, name + ".fbx")
    if not os.path.isfile(filename):
        REPORT.append("FALHOU | ficheiro em falta: " + filename)
        return False

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", filename)
    task.set_editor_property("destination_path", "/Game/Stardust/Vehicles")
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)

    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    static_data = options.get_editor_property("static_mesh_import_data")
    static_data.set_editor_property("combine_meshes", True)
    static_data.set_editor_property("auto_generate_collision", False)
    task.set_editor_property("options", options)

    try:
        TOOLS.import_asset_tasks([task])
        imported = task.get_editor_property("imported_object_paths")
        if imported:
            REPORT.append("OK | " + name + " | " + imported[0])
            return True
        REPORT.append("FALHOU | " + name + " | nenhum asset criado")
    except Exception as exc:
        REPORT.append("FALHOU | " + name + " | " + str(exc))
    return False


def build_hangar():
    map_path = "/Game/Stardust/Maps/Preview_Hangar"
    if unreal.EditorAssetLibrary.does_asset_exist(map_path):
        if not LEVEL_EDITOR.load_level(map_path):
            REPORT.append("FALHOU | nao foi possivel abrir " + map_path)
            return
        for old_actor in ACTORS.get_all_level_actors():
            ACTORS.destroy_actor(old_actor)
    elif not LEVEL_EDITOR.new_level(map_path, False):
        REPORT.append("FALHOU | nao foi possivel criar " + map_path)
        return

    ACTORS.spawn_actor_from_class(
        unreal.DirectionalLight, unreal.Vector(0.0, 0.0, 2500.0),
        unreal.Rotator(-35.0, -25.0, 0.0),
    )
    floor_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
    if floor_mesh:
        floor = ACTORS.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(0.0, 0.0, -120.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        floor.get_component_by_class(unreal.StaticMeshComponent).set_static_mesh(floor_mesh)
        floor.set_actor_scale3d(unreal.Vector(45.0, 15.0, 0.2))

    names = ["strix", "vortex", "wraith", "nomad", "bastion"]
    placed = 0
    for index, name in enumerate(names):
        mesh = unreal.EditorAssetLibrary.load_asset("/Game/Stardust/Vehicles/" + name)
        if not mesh:
            REPORT.append("AVISO | chassis ausente no hangar: " + name)
            continue
        x = (index - 2) * 1800.0
        actor = ACTORS.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(x, 0.0, 80.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        actor.get_component_by_class(unreal.StaticMeshComponent).set_static_mesh(mesh)
        actor.set_actor_label("Chassis " + name.upper())
        placed += 1

    ACTORS.spawn_actor_from_class(
        unreal.CameraActor, unreal.Vector(0.0, -5200.0, 2300.0),
        unreal.Rotator(-18.0, 90.0, 0.0),
    )
    ACTORS.spawn_actor_from_class(
        unreal.PlayerStart, unreal.Vector(0.0, -5200.0, 160.0),
        unreal.Rotator(0.0, 90.0, 0.0),
    )
    LEVEL_EDITOR.save_current_level()
    REPORT.append("MAPA | Preview_Hangar | chassis 3D colocados: " + str(placed))


for chassis_name in ["strix", "vortex", "wraith", "nomad", "bastion"]:
    import_chassis(chassis_name)

build_hangar()
report_path = os.path.join(PROJECT_ROOT, "Docs", "IMPORTACAO_HANGAR.txt")
with open(report_path, "w", encoding="utf-8") as report_file:
    report_file.write("Pre-visualizacao 3D do hangar no Unreal Engine 5.8\n")
    report_file.write("Chassis fonte: " + SOURCE + "\n\n")
    report_file.write("\n".join(REPORT) + "\n")
unreal.log("Extract Stardust: hangar importado. Relatorio: " + report_path)