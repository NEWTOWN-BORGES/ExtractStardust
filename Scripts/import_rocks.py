# Imports the sculpted rocks (Nanite, collision from their real shape), builds the rock material
# (make_rock_material.py) and the per-rock colour variants.
import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
SRC = unreal.Paths.project_dir() + "SourceArt/Rocks/"
TEX = "/Game/Desert/Textures/"
NAMES = ["SM_Mesa_A", "SM_Mesa_B", "SM_Butte_A", "SM_Spire_A", "SM_Spire_B", "SM_Cliff_A", "SM_Cliff_B", "SM_Cliff_C",
         "SM_Boulder_A", "SM_Boulder_B", "SM_Boulder_C"]
failures = []

tasks = []
for name in NAMES:
    task = unreal.AssetImportTask()
    task.filename = SRC + name + ".fbx"
    task.destination_path = "/Game/Desert/Rocks"
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.auto_generate_collision = False
    options.static_mesh_import_data.generate_lightmap_u_vs = False
    task.options = options
    tasks.append(task)
tools.import_asset_tasks(tasks)

# M_Rock: no textures since 2026-10-20 (make_rock_material.py, rebuilt in place with the same parameters).
scripts = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "Scripts/"
exec(open(scripts + "make_rock_material.py").read(), {"__name__": "__main__"})
mat = eal.load_asset("/Game/Desert/M_Rock")

# Colour variants, so neighbouring rocks never look identical.
variants = {"MI_Rock_Red": (1.35, 1.25, 1.2, 0.3), "MI_Rock_Dark": (0.95, 0.85, 0.82, 0.2),
            "MI_Rock_Pale": (1.7, 1.45, 1.25, 0.4), "MI_Rock_Banded": (1.45, 1.25, 1.15, 0.55)}
for name, (r, g, b, strata) in variants.items():
    mi_path = "/Game/Desert/" + name
    if eal.does_asset_exist(mi_path):
        eal.delete_asset(mi_path)
    mi = tools.create_asset(name, "/Game/Desert", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, mat)
    mel.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(r, g, b, 1.0))
    mel.set_material_instance_scalar_parameter_value(mi, "StrataContrast", strata)
    eal.save_asset(mi_path)

# Nanite and collision that follows the sculpted surface.
red = eal.load_asset("/Game/Desert/MI_Rock_Red")
for name in NAMES:
    mesh = eal.load_asset("/Game/Desert/Rocks/" + name)
    if not mesh:
        failures.append("missing " + name)
        continue
    nanite = mesh.get_editor_property("nanite_settings")
    nanite.enabled = True
    mesh.set_editor_property("nanite_settings", nanite)
    body = mesh.get_editor_property("body_setup")
    if body:
        body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh.set_material(0, red)
    eal.save_asset("/Game/Desert/Rocks/" + name)
unreal.log("ROCKS imported %d, failures=%s" % (len(NAMES), failures))
