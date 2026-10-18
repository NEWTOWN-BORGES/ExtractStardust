# Imports the sculpted rocks (Nanite, collision from their real shape) and builds the rock material:
# tri-planar sandstone with height strata, sand settling on upward faces, and per-rock colour variants.
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

y_cursor = [0]
path = "/Game/Desert/M_Rock"
if eal.does_asset_exist(path):
    eal.delete_asset(path)
mat = tools.create_asset("M_Rock", "/Game/Desert", unreal.Material, unreal.MaterialFactoryNew())


def expr(cls, **props):
    y_cursor[0] += 120
    e = mel.create_material_expression(mat, cls, -1200, y_cursor[0])
    for key, value in props.items():
        e.set_editor_property(key, value)
    return e


def link(src, dst, pin, out=""):
    if not mel.connect_material_expressions(src, out, dst, pin):
        failures.append("%s -> %s.%s" % (src.get_name(), dst.get_name(), pin))


def binary(cls, a, b):
    e = expr(cls)
    for value, pin in ((a, "A"), (b, "B")):
        if isinstance(value, (int, float)):
            e.set_editor_property("const_" + pin.lower(), float(value))
        else:
            link(value, e, pin)
    return e


def mask(src, r=False, g=False, b=False):
    e = expr(unreal.MaterialExpressionComponentMask, r=r, g=g, b=b, a=False)
    link(src, e, "")
    return e


def sample(name, uv, sampler=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR):
    e = expr(unreal.MaterialExpressionTextureSample, texture=eal.load_asset(TEX + name), sampler_type=sampler,
             sampler_source=unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    link(uv, e, "UVs")
    return e


def lerp(a, b, alpha):
    e = expr(unreal.MaterialExpressionLinearInterpolate)
    for value, pin in ((a, "A"), (b, "B"), (alpha, "Alpha")):
        if isinstance(value, (int, float)):
            e.set_editor_property("const_" + pin.lower(), float(value))
        else:
            link(value, e, pin)
    return e


def scalar(name, value):
    return expr(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)


world = expr(unreal.MaterialExpressionWorldPosition)
normal_ws = expr(unreal.MaterialExpressionVertexNormalWS)
n_abs = expr(unreal.MaterialExpressionAbs)
link(normal_ws, n_abs, "")
weights = []
for channel in ("r", "g", "b"):
    w = expr(unreal.MaterialExpressionPower, const_exponent=4.0)
    link(mask(n_abs, **{channel: True}), w, "Base")
    weights.append(w)
weight_sum = binary(unreal.MaterialExpressionAdd, binary(unreal.MaterialExpressionAdd, weights[0], weights[1]), weights[2])
tile = scalar("TileCm", 600.0)
color = None
normal = None
for projection, weight in zip([mask(world, g=True, b=True), mask(world, r=True, b=True), mask(world, r=True, g=True)], weights):
    uv = binary(unreal.MaterialExpressionDivide, projection, tile)
    c = binary(unreal.MaterialExpressionMultiply, sample("T_Rock_D", uv), weight)
    n = binary(unreal.MaterialExpressionMultiply, sample("T_Rock_N", uv, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL), weight)
    color = c if color is None else binary(unreal.MaterialExpressionAdd, color, c)
    normal = n if normal is None else binary(unreal.MaterialExpressionAdd, normal, n)
color = binary(unreal.MaterialExpressionDivide, color, weight_sum)
normal = binary(unreal.MaterialExpressionDivide, normal, weight_sum)

# Strata bands from world height, then the per-rock tint.
band = expr(unreal.MaterialExpressionSine, period=500.0)
link(mask(world, b=True), band, "")
band01 = binary(unreal.MaterialExpressionAdd, binary(unreal.MaterialExpressionMultiply, band, 0.5), 0.5)
contrast = scalar("StrataContrast", 0.3)
color = binary(unreal.MaterialExpressionMultiply, color, lerp(binary(unreal.MaterialExpressionSubtract, 1.0, contrast), 1.0, band01))
tint = expr(unreal.MaterialExpressionVectorParameter, parameter_name="Tint", default_value=unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
color = binary(unreal.MaterialExpressionMultiply, color, tint)

# Sand settles on ledges and tops (upward-facing surfaces).
sand_uv = binary(unreal.MaterialExpressionDivide, mask(world, r=True, g=True), 400.0)
up = binary(unreal.MaterialExpressionDivide, binary(unreal.MaterialExpressionSubtract, mask(normal_ws, b=True), 0.72), 0.18)
sand_mask = expr(unreal.MaterialExpressionSaturate)
link(up, sand_mask, "")
color = lerp(color, sample("T_Sand_D", sand_uv), sand_mask)

for src, prop in ((color, unreal.MaterialProperty.MP_BASE_COLOR), (normal, unreal.MaterialProperty.MP_NORMAL),
                  (lerp(0.82, 0.93, sand_mask), unreal.MaterialProperty.MP_ROUGHNESS)):
    if not mel.connect_material_property(src, "", prop):
        failures.append("property %s" % prop)
mel.recompile_material(mat)
eal.save_asset(path)

# Colour variants, so neighbouring rocks never look identical.
variants = {"MI_Rock_Red": (1.0, 1.0, 1.0, 0.3), "MI_Rock_Dark": (0.62, 0.56, 0.55, 0.2),
            "MI_Rock_Pale": (1.3, 1.12, 0.95, 0.4), "MI_Rock_Banded": (1.08, 0.95, 0.9, 0.55)}
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
