"""Monta um mapa de inspeção com as malhas FBX preservadas nas coordenadas exportadas."""
import json
import os
import unreal


COURSE_ID = str(os.environ.get("RDD_COURSE_ID", globals().get("COURSE_ID", "red_dust_divide"))).lower()
COURSES = {
    "red_dust_divide": ("RedDustDivide", "Preview_RedDust"),
    "sandbox": ("Sandbox", "Preview_Sandbox"),
}

if COURSE_ID not in COURSES:
    raise RuntimeError("Curso desconhecido: {}".format(COURSE_ID))

FOLDER_NAME, MAP_NAME = COURSES[COURSE_ID]
CONTENT_ROOT = "/Game/Stardust/Courses/{}".format(FOLDER_NAME)
MAP_PATH = "/Game/Stardust/Maps/{}".format(MAP_NAME)
PROJECT_ROOT = unreal.Paths.project_dir()
COURSE_JSON = os.path.join(PROJECT_ROOT, "SourceAssets", "Unity", "Art", "Courses", COURSE_ID + ".json")
REPORT_PATH = os.path.join(PROJECT_ROOT, "Docs", "PREVIEW_CURSOS.txt")

if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
    raise RuntimeError("O mapa ja existe; script interrompido para nao substituir trabalho existente: {}".format(MAP_PATH))

with open(COURSE_JSON, "r", encoding="utf-8") as source_file:
    course_config = json.load(source_file)

# Os FBX do exportador preservam coordenadas de mundo nos vertices. Os bounds foram auditados;
# por isso, os atores ficam na origem sem offsets ou transformacoes que alterem a geometria.
mesh_paths = sorted(unreal.EditorAssetLibrary.list_assets(CONTENT_ROOT, recursive=False, include_folder=False))
mesh_assets = []
for asset_path in mesh_paths:
    short_name = asset_path.rsplit("/", 1)[-1].split(".", 1)[0]
    if short_name == "axis_test":
        continue
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if isinstance(asset, unreal.StaticMesh):
        mesh_assets.append((short_name, asset))

if not mesh_assets:
    raise RuntimeError("Nao foram encontrados StaticMesh em {}".format(CONTENT_ROOT))

level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level_editor.new_level(MAP_PATH, False):
    raise RuntimeError("Nao foi possivel criar o mapa {}".format(MAP_PATH))

zero = unreal.Vector(0.0, 0.0, 0.0)
rotation_zero = unreal.Rotator(0.0, 0.0, 0.0)
spawned_meshes = []
for short_name, mesh in mesh_assets:
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(mesh, zero, rotation_zero)
    if not actor:
        raise RuntimeError("Falha ao colocar o mesh {}".format(short_name))
    actor.set_actor_label(short_name)
    spawned_meshes.append(actor)

start = course_config.get("start", {})
unity_position = start.get("pos", [0.0, 0.0, 0.0])
if len(unity_position) != 3:
    raise RuntimeError("A posicao inicial do curso tem de ter tres componentes.")
start_location = unreal.Vector(
    float(unity_position[2]) * 100.0,
    float(unity_position[0]) * 100.0,
    float(unity_position[1]) * 100.0,
)
start_yaw = float(start.get("yaw", 0.0))
player_start = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.PlayerStart, start_location, unreal.Rotator(0.0, start_yaw, 0.0)
)
if player_start:
    player_start.set_actor_label("PlayerStart_Unity_Export")

light = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.DirectionalLight,
    unreal.Vector(0.0, 0.0, 100000.0),
    unreal.Rotator(-42.0, -28.0, 0.0),
)
if light:
    light.set_actor_label("Preview_Directional_Light")

if not unreal.EditorLoadingAndSavingUtils.save_current_level():
    raise RuntimeError("O mapa {} nao foi gravado.".format(MAP_PATH))

report_lines = [
    "MAPA | {} | {}".format(COURSE_ID, MAP_PATH),
    "Meshes de curso colocados na origem, com coordenadas de mundo do FBX preservadas: {}".format(len(spawned_meshes)),
    "Ponto inicial Unity convertido para Unreal: ({:.1f}, {:.1f}, {:.1f}) cm | yaw {:.1f}".format(
        start_location.x, start_location.y, start_location.z, start_yaw
    ),
    "Aviso: mapa de inspeção visual; ainda sem colisão otimizada, streaming, IA ou GameMode C++ compilado.",
    "",
]
with open(REPORT_PATH, "a", encoding="utf-8") as report_file:
    report_file.write("\n".join(report_lines))
unreal.log("Extract Stardust: {} criado com {} meshes em {}".format(MAP_PATH, len(spawned_meshes), MAP_PATH))
