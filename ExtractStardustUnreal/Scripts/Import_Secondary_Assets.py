"""Importa recursos pequenos sem reimportar pistas nem reconstruir mapas pesados."""
import glob
import os
import unreal

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UNITY = os.path.join(PROJECT_ROOT, "SourceAssets", "Unity")
ASSETS = os.path.join(UNITY, "Assets")
ART = os.path.join(UNITY, "Art", "Export")
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
REPORT = []


def set_if_supported(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception:
        pass


def import_one(filename, destination, is_fbx=False):
    name = os.path.splitext(os.path.basename(filename))[0]
    asset_path = destination.rstrip("/") + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        REPORT.append("JA EXISTIA | {}".format(asset_path))
        return

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", filename)
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)

    if is_fbx:
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
            REPORT.append("FALHOU | {} | nenhum asset criado".format(filename))
    except Exception as exc:
        REPORT.append("FALHOU | {} | {}".format(filename, exc))


def import_pattern(pattern, destination, is_fbx=False):
    for filename in sorted(glob.glob(pattern)):
        import_one(filename, destination, is_fbx)


def create_tint_material(name, color):
    path = "/Game/Stardust/Materials/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        REPORT.append("JA EXISTIA | " + path)
        return
    try:
        material = TOOLS.create_asset(name, "/Game/Stardust/Materials", unreal.Material, unreal.MaterialFactoryNew())
        expression = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionVectorParameter, -300, 0
        )
        expression.set_editor_property("parameter_name", "TintColor")
        expression.set_editor_property("default_value", unreal.LinearColor(*color))
        unreal.MaterialEditingLibrary.connect_material_property(
            expression, "RGB", unreal.MaterialProperty.MP_BASE_COLOR
        )
        unreal.EditorAssetLibrary.save_loaded_asset(material)
        REPORT.append("OK | material | " + path)
    except Exception as exc:
        REPORT.append("FALHOU | material {} | {}".format(path, exc))


# Os FBX densos das pistas são geridos separadamente por Import_Course_Batch.py.
import_pattern(os.path.join(ASSETS, "RedDust", "Resources", "Props", "*.fbx"), "/Game/Stardust/Props", True)
import_pattern(os.path.join(ASSETS, "RedDust", "Materials", "*.png"), "/Game/Stardust/Textures")
import_pattern(os.path.join(ASSETS, "RedDust", "Resources", "UI", "*.jpg"), "/Game/Stardust/UI")
import_pattern(os.path.join(ASSETS, "RedDust", "Resources", "Audio", "*.wav"), "/Game/Stardust/Audio")
import_pattern(os.path.join(ART, "red_dust_divide", "*_preview.png"), "/Game/Stardust/UI")
import_pattern(os.path.join(ART, "sandbox", "*_preview.png"), "/Game/Stardust/UI")
create_tint_material("M_RedDust", (0.38, 0.16, 0.07, 1.0))
create_tint_material("M_Incompatible", (1.0, 0.015, 0.025, 1.0))

report_path = os.path.join(PROJECT_ROOT, "Docs", "IMPORTACAO_RECURSOS.txt")
with open(report_path, "w", encoding="utf-8") as report_file:
    report_file.write("Importacao de props, texturas, UI e audio para Unreal Engine 5.8\n")
    report_file.write("Os FBX densos das pistas estao em IMPORTACAO_CURSOS.txt.\n\n")
    report_file.write("\n".join(REPORT) + "\n")
unreal.log("Extract Stardust: recursos adicionais processados. Relatorio: {}".format(report_path))
# Importar fontes TTF e converter materiais Unity da fase de fidelidade.
def import_font(filename):
    name = os.path.splitext(os.path.basename(filename))[0]
    asset_path = "/Game/Stardust/Fonts/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        REPORT.append("JA EXISTIA | fonte | " + asset_path)
        return
    try:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", filename)
        task.set_editor_property("destination_path", "/Game/Stardust/Fonts")
        task.set_editor_property("destination_name", name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("save", True)
        task.set_editor_property("factory", unreal.FontFileImportFactory())
        TOOLS.import_asset_tasks([task])
        imported = task.get_editor_property("imported_object_paths")
        if imported:
            REPORT.append("OK | fonte | {} | {}".format(name, ", ".join(imported)))
        else:
            REPORT.append("FALHOU | fonte | {} | nenhum asset criado".format(name))
    except Exception as exc:
        REPORT.append("FALHOU | fonte {} | {}".format(name, exc))


def create_unity_material(name, color, metallic, smoothness, emission):
    asset_name = "M_" + name
    asset_path = "/Game/Stardust/Materials/" + asset_name
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        REPORT.append("JA EXISTIA | material convertido | " + asset_path)
        return
    try:
        material = TOOLS.create_asset(
            asset_name, "/Game/Stardust/Materials", unreal.Material, unreal.MaterialFactoryNew()
        )
        set_if_supported(material, "blend_mode", unreal.BlendMode.BLEND_OPAQUE)
        set_if_supported(material, "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)

        base_color = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionVectorParameter, -500, 0
        )
        base_color.set_editor_property("parameter_name", "BaseColor")
        base_color.set_editor_property("default_value", unreal.LinearColor(*color))
        unreal.MaterialEditingLibrary.connect_material_property(
            base_color, "RGB", unreal.MaterialProperty.MP_BASE_COLOR
        )

        for index, (parameter, value, property_name) in enumerate((
            ("Metallic", metallic, unreal.MaterialProperty.MP_METALLIC),
            ("Roughness", 1.0 - smoothness, unreal.MaterialProperty.MP_ROUGHNESS),
            ("Specular", 0.2, unreal.MaterialProperty.MP_SPECULAR),
        )):
            expression = unreal.MaterialEditingLibrary.create_material_expression(
                material, unreal.MaterialExpressionScalarParameter, -250, index * 180
            )
            expression.set_editor_property("parameter_name", parameter)
            expression.set_editor_property("default_value", float(value))
            unreal.MaterialEditingLibrary.connect_material_property(expression, "", property_name)

        if any(component > 0.0 for component in emission[:3]):
            emissive = unreal.MaterialEditingLibrary.create_material_expression(
                material, unreal.MaterialExpressionVectorParameter, -500, 700
            )
            emissive.set_editor_property("parameter_name", "EmissionColor")
            emissive.set_editor_property("default_value", unreal.LinearColor(*emission))
            unreal.MaterialEditingLibrary.connect_material_property(
                emissive, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR
            )

        unreal.EditorAssetLibrary.save_loaded_asset(material)
        REPORT.append("OK | material Unity convertido | {}".format(asset_path))
    except Exception as exc:
        REPORT.append("FALHOU | material Unity {} | {}".format(name, exc))


for font_file in sorted(glob.glob(os.path.join(ASSETS, "RedDust", "Resources", "Fonts", "*.ttf"))):
    import_font(font_file)

UNITY_MATERIALS = [
    ("Mega_Cloth", (0.62, 0.08, 0.06, 1.0), 0.0, 0.10, (0.0, 0.0, 0.0, 1.0)),
    ("Mega_Dark", (0.12, 0.12, 0.13, 1.0), 0.5, 0.35, (0.0, 0.0, 0.0, 1.0)),
    ("Mega_Glow", (1.0, 0.55, 0.2, 1.0), 0.0, 0.50, (3.0, 1.6500001, 0.6, 3.0)),
    ("Mega_Metal", (0.42, 0.44, 0.47, 1.0), 0.6, 0.45, (0.0, 0.0, 0.0, 1.0)),
    ("Mega_Rust", (0.47, 0.25, 0.14, 1.0), 0.2, 0.25, (0.0, 0.0, 0.0, 1.0)),
    ("PropLit", (1.0, 1.0, 1.0, 1.0), 0.0, 0.50, (0.0, 0.0, 0.0, 1.0)),
    ("Water", (0.16, 0.34, 0.32, 1.0), 0.0, 0.93, (0.0, 0.0, 0.0, 1.0)),
]
for material_data in UNITY_MATERIALS:
    create_unity_material(*material_data)

with open(report_path, "w", encoding="utf-8") as report_file:
    report_file.write("Importacao e conversao de recursos para Unreal Engine 5.8\n")
    report_file.write("\n".join(REPORT) + "\n")
font_total = len(glob.glob(os.path.join(ASSETS, "RedDust", "Resources", "Fonts", "*.ttf")))
font_failures = sum(1 for item in REPORT if item.startswith("FALHOU | fonte "))
material_failures = sum(1 for item in REPORT if item.startswith("FALHOU | material Unity "))
all_failures = sum(1 for item in REPORT if item.startswith("FALHOU |"))
REPORT.append(
    "VALIDACAO FINAL | fontes TTF: {}/{} | materiais Unity convertidos: {}/{} | falhas totais: {}".format(
        font_total - font_failures, font_total,
        len(UNITY_MATERIALS) - material_failures, len(UNITY_MATERIALS),
        all_failures
    )
)
with open(report_path, "w", encoding="utf-8") as report_file:
    report_file.write("Importacao e conversao de recursos para Unreal Engine 5.8\n")
    report_file.write("\n".join(REPORT) + "\n")
unreal.log("Extract Stardust: importacao base terminada. Relatorio: {}".format(report_path))