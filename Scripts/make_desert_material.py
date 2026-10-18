# Imports the baked desert textures and builds the landscape auto-material /Game/Desert/M_Desert.
# Sand on gentle ground, sandstone on steep ground (tri-planar, so cliffs do not stretch), horizontal strata
# bands from world height, and a large-scale tint so the sand does not visibly repeat.
import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
SRC = unreal.Paths.project_dir() + "SourceArt/Desert/"
TEX = "/Game/Desert/Textures/"
failures = []

tasks = []
for name in ["T_Sand_D", "T_Sand_N", "T_Rock_D", "T_Rock_N", "T_Macro_D"]:
    task = unreal.AssetImportTask()
    task.filename = SRC + name + ".png"
    task.destination_path = "/Game/Desert/Textures"
    task.automated = True
    task.save = True
    task.replace_existing = True
    tasks.append(task)
tools.import_asset_tasks(tasks)
for name in ["T_Sand_N", "T_Rock_N"]:
    texture = eal.load_asset(TEX + name)
    texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    texture.set_editor_property("srgb", False)
    eal.save_loaded_asset(texture)
macro_texture = eal.load_asset(TEX + "T_Macro_D")
macro_texture.set_editor_property("srgb", False)
eal.save_loaded_asset(macro_texture)

path = "/Game/Desert/M_Desert"
if eal.does_asset_exist(path):
    eal.delete_asset(path)
mat = tools.create_asset("M_Desert", "/Game/Desert", unreal.Material, unreal.MaterialFactoryNew())
y_cursor = [0]


def expr(cls, **props):
    y_cursor[0] += 120
    e = mel.create_material_expression(mat, cls, -1200, y_cursor[0])
    for key, value in props.items():
        e.set_editor_property(key, value)
    return e


def link(src, dst, dst_input, src_output=""):
    if not mel.connect_material_expressions(src, src_output, dst, dst_input):
        failures.append("%s.%s -> %s.%s" % (src.get_name(), src_output, dst.get_name(), dst_input))


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


def sample(texture_name, uv, sampler=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR):
    e = expr(unreal.MaterialExpressionTextureSample, texture=eal.load_asset(TEX + texture_name), sampler_type=sampler,
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


world = expr(unreal.MaterialExpressionWorldPosition)
normal_ws = expr(unreal.MaterialExpressionVertexNormalWS)
xy = mask(world, r=True, g=True)

# Sand: two scales of the same texture plus a very large macro tint.
sand_uv = binary(unreal.MaterialExpressionDivide, xy, 400.0)
sand_uv_far = binary(unreal.MaterialExpressionDivide, xy, 1470.0)
macro = sample("T_Macro_D", binary(unreal.MaterialExpressionDivide, xy, 30000.0), unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
macro_r = mask(macro, r=True)
sand_color = lerp(sample("T_Sand_D", sand_uv), sample("T_Sand_D", sand_uv_far), 0.35)
sand_color = binary(unreal.MaterialExpressionMultiply, sand_color, lerp(0.82, 1.12, macro_r))
sand_normal = sample("T_Sand_N", sand_uv, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)

# Sandstone: tri-planar projection weighted by the surface normal.
n_abs = expr(unreal.MaterialExpressionAbs)
link(normal_ws, n_abs, "")
weights = []
for channel in ("r", "g", "b"):
    w = expr(unreal.MaterialExpressionPower, const_exponent=4.0)
    link(mask(n_abs, **{channel: True}), w, "Base")
    weights.append(w)
weight_sum = binary(unreal.MaterialExpressionAdd, binary(unreal.MaterialExpressionAdd, weights[0], weights[1]), weights[2])
projections = [mask(world, g=True, b=True), mask(world, r=True, b=True), xy]  # seen along X, along Y, from above
rock_color = None
rock_normal = None
for projection, weight in zip(projections, weights):
    uv = binary(unreal.MaterialExpressionDivide, projection, 600.0)
    color = binary(unreal.MaterialExpressionMultiply, sample("T_Rock_D", uv), weight)
    normal = binary(unreal.MaterialExpressionMultiply, sample("T_Rock_N", uv, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL), weight)
    rock_color = color if rock_color is None else binary(unreal.MaterialExpressionAdd, rock_color, color)
    rock_normal = normal if rock_normal is None else binary(unreal.MaterialExpressionAdd, rock_normal, normal)
rock_color = binary(unreal.MaterialExpressionDivide, rock_color, weight_sum)
rock_normal = binary(unreal.MaterialExpressionDivide, rock_normal, weight_sum)

# Strata: brightness bands every 6.5 m of height, wavering with the macro noise.
height = mask(world, b=True)
band_input = binary(unreal.MaterialExpressionAdd, height, binary(unreal.MaterialExpressionMultiply, macro_r, 1500.0))
band = expr(unreal.MaterialExpressionSine, period=650.0)
link(band_input, band, "")
band01 = binary(unreal.MaterialExpressionAdd, binary(unreal.MaterialExpressionMultiply, band, 0.5), 0.5)
rock_color = binary(unreal.MaterialExpressionMultiply, rock_color, lerp(0.7, 1.2, band01))

# Steep ground is rock, gentle ground is sand.
slope = binary(unreal.MaterialExpressionDivide, binary(unreal.MaterialExpressionSubtract, 0.78, mask(normal_ws, b=True)), 0.14)
rock_mask = expr(unreal.MaterialExpressionSaturate)
link(slope, rock_mask, "")

base_color = lerp(sand_color, rock_color, rock_mask)
final_normal = lerp(sand_normal, rock_normal, rock_mask)
roughness = lerp(0.92, 0.8, rock_mask)
specular = expr(unreal.MaterialExpressionConstant, r=0.35)

for src, prop in ((base_color, unreal.MaterialProperty.MP_BASE_COLOR), (final_normal, unreal.MaterialProperty.MP_NORMAL),
                  (roughness, unreal.MaterialProperty.MP_ROUGHNESS), (specular, unreal.MaterialProperty.MP_SPECULAR)):
    if not mel.connect_material_property(src, "", prop):
        failures.append("property %s" % prop)

mel.recompile_material(mat)
eal.save_asset(path)
unreal.log("DESERTMAT saved %s, failures=%s" % (path, failures))
