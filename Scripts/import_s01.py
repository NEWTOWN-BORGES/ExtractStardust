# Imports the S01 hero geology (Nanite, collision from the real shape) and the plants (Nanite, vertex colours,
# no collision at all: the craft flies through bushes and trees), and builds their materials:
#  - stratum variants of M_Rock, one per rock layer of the sector (Docs/MAPA_01_RED_DUST_DIVIDE_S01.md, 3);
#  - M_Plant: vertex colour, light passing through leaves (vertex alpha marks leaves).
# Run after import_rocks.py (which builds M_Rock).
import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
ROOT = unreal.Paths.project_dir() + "SourceArt/"
PIECES = ["SM_MesaArch", "SM_IslandButte", "SM_Slab_A", "SM_Slab_B"]
PLANTS = ["SM_Cottonwood_A", "SM_Cottonwood_B", "SM_Juniper_A", "SM_Juniper_B", "SM_Willow", "SM_Sagebrush",
          "SM_DeadBrush", "SM_DryGrass", "SM_GreenGrass", "SM_PricklyPear", "SM_Yucca"]
failures = []


def import_meshes(names, source, destination):
    tasks = []
    for name in names:
        task = unreal.AssetImportTask()
        task.filename = source + name + ".fbx"
        task.destination_path = destination
        task.destination_name = name
        task.automated = True
        task.save = True
        task.replace_existing = True
        options = unreal.FbxImportUI()
        options.import_mesh = True
        options.import_as_skeletal = False
        options.import_materials = False
        options.import_textures = False
        data = options.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.generate_lightmap_u_vs = False
        data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.vertex_color_import_option = unreal.VertexColorImportOption.REPLACE
        task.options = options
        tasks.append(task)
    tools.import_asset_tasks(tasks)


import_meshes(PIECES, ROOT + "S01/", "/Game/Desert/S01")
import_meshes(PLANTS, ROOT + "Plants/", "/Game/Desert/Plants")

# ---- Stratum materials: each rock gets the material of the layer it belongs to, never a random colour.
rock = eal.load_asset("/Game/Desert/M_Rock")
# Tint, strata contrast, strata period (cm), desert varnish strength, texture tile (cm). Massive layers use a
# large tile so the jointed texture does not repeat as lines up the walls.
STRATA = {
    "MI_Navajo": ((1.75, 1.42, 1.12), 0.06, 900.0, 0.2, 1600.0),    # pale cream-orange, massive, cross-bedded
    "MI_Kayenta": ((1.3, 0.98, 0.85), 0.22, 160.0, 0.15, 500.0),    # red-brown, thin ledgy beds
    "MI_Wingate": ((1.55, 1.05, 0.78), 0.04, 1400.0, 0.65, 1800.0), # red-orange, massive, dark varnish streaks
}
for name, (tint, contrast, period, varnish, tile) in STRATA.items():
    path = "/Game/Desert/" + name
    # Updated in place when it exists, so the map keeps its references.
    mi = eal.load_asset(path) if eal.does_asset_exist(path) else \
        tools.create_asset(name, "/Game/Desert", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, rock)
    mel.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(tint[0], tint[1], tint[2], 1.0))
    mel.set_material_instance_scalar_parameter_value(mi, "StrataContrast", contrast)
    mel.set_material_instance_scalar_parameter_value(mi, "StrataPeriodCm", period)
    mel.set_material_instance_scalar_parameter_value(mi, "Varnish", varnish)
    mel.set_material_instance_scalar_parameter_value(mi, "TileCm", tile)
    eal.save_asset(path)

# ---- M_Plant: vertex colour base, leaves (vertex alpha 1) let warm-green light through when backlit.
path = "/Game/Desert/M_Plant"
if eal.does_asset_exist(path):
    plant = eal.load_asset(path)
    mel.delete_all_material_expressions(plant)  # rebuilt in place, so meshes keep their reference
else:
    plant = tools.create_asset("M_Plant", "/Game/Desert", unreal.Material, unreal.MaterialFactoryNew())
plant.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
# Cooked games only get shaders for declared usages: plants are Nanite meshes drawn through instanced components.
plant.set_editor_property("used_with_nanite", True)
plant.set_editor_property("used_with_instanced_static_meshes", True)
y_cursor = [0]


def expr(cls, **props):
    y_cursor[0] += 120
    e = mel.create_material_expression(plant, cls, -800, y_cursor[0])
    for key, value in props.items():
        e.set_editor_property(key, value)
    return e


# The vertex colour node's default output is RGB only: alpha comes from its own "A" output.
vertex = expr(unreal.MaterialExpressionVertexColor)
through = expr(unreal.MaterialExpressionMultiply)
for out, pin in (("", "A"), ("A", "B")):
    if not mel.connect_material_expressions(vertex, out, through, pin):
        failures.append("M_Plant vertex %s" % pin)
transmission = expr(unreal.MaterialExpressionMultiply, const_b=0.7)
mel.connect_material_expressions(through, "", transmission, "A")
roughness = expr(unreal.MaterialExpressionConstant, r=0.82)
specular = expr(unreal.MaterialExpressionConstant, r=0.3)
for src, prop in ((vertex, unreal.MaterialProperty.MP_BASE_COLOR), (transmission, unreal.MaterialProperty.MP_SUBSURFACE_COLOR),
                  (roughness, unreal.MaterialProperty.MP_ROUGHNESS), (specular, unreal.MaterialProperty.MP_SPECULAR)):
    if not mel.connect_material_property(src, "", prop):
        failures.append("M_Plant %s" % prop)
mel.recompile_material(plant)
eal.save_asset(path)

# ---- Mesh settings: Nanite everywhere; rocks and slabs collide on their real surface; plants never collide
# (no simple shapes are generated, and simple-as-complex leaves them with nothing to hit).
navajo = eal.load_asset("/Game/Desert/MI_Navajo")
kayenta = eal.load_asset("/Game/Desert/MI_Kayenta")
plant = eal.load_asset(path)
for folder, names in (("/Game/Desert/S01/", PIECES), ("/Game/Desert/Plants/", PLANTS)):
    for name in names:
        mesh = eal.load_asset(folder + name)
        if not mesh:
            failures.append("missing " + name)
            continue
        nanite = mesh.get_editor_property("nanite_settings")
        nanite.enabled = True
        mesh.set_editor_property("nanite_settings", nanite)
        body = mesh.get_editor_property("body_setup")
        solid = folder.endswith("S01/")
        if body:
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if solid
                                     else unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        if folder.endswith("Plants/"):
            material = plant
        else:
            material = kayenta if name.startswith("SM_Slab") else navajo
        mesh.set_material(0, material)
        eal.save_asset(folder + name)
unreal.log("S01IMPORT pieces %d plants %d failures=%s" % (len(PIECES), len(PLANTS), failures))
