# Imports the baked desert textures and builds the landscape material /Game/Desert/M_Desert.
# The ground follows the geology through T_SurfaceMap (baked by UEXDesertBuilder::BuildSurfaceMap from
# FEXDesertTerrain::SurfaceAt): R exposed Kayenta slickrock, G deep dune sand, B gravel and talus, A seep wetness.
# Packed sand everywhere else; steep ground is rock (tri-planar, so slopes do not stretch) with faint broad bands.
# A large-scale tint keeps the sand from visibly repeating. Run after BuildSurfaceMap.
import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
SRC = unreal.Paths.project_dir() + "SourceArt/Desert/"
TEX = "/Game/Desert/Textures/"
HALF_SIZE_CM = 302400.0  # FEXDesertTerrain::HalfSizeM in centimetres
# Another landscape can reuse this material by exec'ing the script with MAT_CONFIG in its globals: material name and
# folder, the surface texture and the world rectangle (cm) that texture covers.
CFG = globals().get("MAT_CONFIG", {})
MAT_DIR = CFG.get("dir", "/Game/Desert")
MAT_NAME = CFG.get("name", "M_Desert")
SURFACE = CFG.get("surface", TEX + "T_SurfaceMap")
SURFACE_ORIGIN_CM = CFG.get("origin_cm", (-HALF_SIZE_CM, -HALF_SIZE_CM))
SURFACE_SIZE_CM = CFG.get("size_cm", (2.0 * HALF_SIZE_CM, 2.0 * HALF_SIZE_CM))
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

path = MAT_DIR + "/" + MAT_NAME
if eal.does_asset_exist(path):
    eal.delete_asset(path)
mat = tools.create_asset(MAT_NAME, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
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


def mul(a, b):
    return binary(unreal.MaterialExpressionMultiply, a, b)


def add(a, b):
    return binary(unreal.MaterialExpressionAdd, a, b)


def sub(a, b):
    return binary(unreal.MaterialExpressionSubtract, a, b)


def div(a, b):
    return binary(unreal.MaterialExpressionDivide, a, b)


def mask(src, r=False, g=False, b=False, a=False):
    e = expr(unreal.MaterialExpressionComponentMask, r=r, g=g, b=b, a=a)
    link(src, e, "")
    return e


def sample(texture_name, uv, sampler=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR):
    asset = texture_name if texture_name.startswith("/") else TEX + texture_name
    e = expr(unreal.MaterialExpressionTextureSample, texture=eal.load_asset(asset), sampler_type=sampler,
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


def saturate(value):
    e = expr(unreal.MaterialExpressionSaturate)
    link(value, e, "")
    return e


def colour(r, g, b):
    return expr(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(r, g, b, 1.0))


NORMAL = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
LINEAR = unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
world = expr(unreal.MaterialExpressionWorldPosition)
normal_ws = expr(unreal.MaterialExpressionVertexNormalWS)
xy = mask(world, r=True, g=True)

# Where the geology says what the ground is (one texel per 2.95 m, blended).
surface_uv = div(sub(xy, expr(unreal.MaterialExpressionConstant2Vector, r=SURFACE_ORIGIN_CM[0], g=SURFACE_ORIGIN_CM[1])),
                 expr(unreal.MaterialExpressionConstant2Vector, r=SURFACE_SIZE_CM[0], g=SURFACE_SIZE_CM[1]))
surface = sample(SURFACE, surface_uv, LINEAR)
slick_map = mask(surface, r=True)
deep_map = mask(surface, g=True)
gravel_map = mask(surface, b=True)
seep_map = expr(unreal.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
link(surface, seep_map, "", "RGBA")

# Packed sand: two scales of the same texture plus a very large macro tint.
sand_uv = div(xy, 400.0)
macro = sample("T_Macro_D", div(xy, 30000.0), LINEAR)
macro_r = mask(macro, r=True)
sand_d = sample("T_Sand_D", sand_uv)
sand_color = lerp(sand_d, sample("T_Sand_D", div(xy, 1470.0)), 0.35)
sand_color = mul(sand_color, lerp(0.82, 1.12, macro_r))
sand_normal = sample("T_Sand_N", sand_uv, NORMAL)
# Fine noise that breaks the soft surface-map edges into ragged natural borders.
edge_noise = sub(mask(sample("T_Macro_D", div(xy, 900.0), LINEAR), r=True), 0.5)

# Deep dune sand: paler and pinker, fine wind ripples, softer relief.
deep_uv = div(xy, 230.0)
deep_color = mul(sample("T_Sand_D", deep_uv), colour(1.12, 0.98, 0.86))
deep_normal = lerp(sample("T_Sand_N", deep_uv, NORMAL), colour(0.0, 0.0, 1.0), 0.35)

# Kayenta slickrock seen from above: jointed red-brown sandstone pavement.
slick_uv = div(xy, 900.0)
slick_color = mul(sample("T_Rock_D", slick_uv), mul(colour(1.02, 0.8, 0.68), lerp(0.88, 1.08, macro_r)))
slick_normal = sample("T_Rock_N", slick_uv, NORMAL)

# Gravel and talus: sand full of small broken rock, greyer and darker.
gravel_uv = div(xy, 140.0)
gravel_rock = mul(sample("T_Rock_D", gravel_uv), colour(0.78, 0.7, 0.68))
gravel_color = lerp(sand_color, gravel_rock, 0.6)
gravel_normal = sample("T_Rock_N", gravel_uv, NORMAL)

# Steep ground: tri-planar rock weighted by the surface normal, with faint broad bands (Chinle slopes).
n_abs = expr(unreal.MaterialExpressionAbs)
link(normal_ws, n_abs, "")
weights = []
for channel in ("r", "g", "b"):
    w = expr(unreal.MaterialExpressionPower, const_exponent=4.0)
    link(mask(n_abs, **{channel: True}), w, "Base")
    weights.append(w)
weight_sum = add(add(weights[0], weights[1]), weights[2])
projections = [mask(world, g=True, b=True), mask(world, r=True, b=True), xy]  # seen along X, along Y, from above
rock_color = None
rock_normal = None
for projection, weight in zip(projections, weights):
    uv = div(projection, 900.0)
    c = mul(sample("T_Rock_D", uv), weight)
    n = mul(sample("T_Rock_N", uv, NORMAL), weight)
    rock_color = c if rock_color is None else add(rock_color, c)
    rock_normal = n if rock_normal is None else add(rock_normal, n)
rock_color = div(rock_color, weight_sum)
rock_normal = div(rock_normal, weight_sum)
height = mask(world, b=True)
band = expr(unreal.MaterialExpressionSine, period=1.0)
link(div(add(height, mul(macro_r, 1500.0)), 900.0), band, "")
band01 = add(mul(band, 0.5), 0.5)
rock_color = mul(rock_color, mul(lerp(0.9, 1.06, band01), lerp(colour(1.0, 0.86, 0.84), colour(1.0, 0.95, 0.9), band01)))

slope = div(sub(0.78, mask(normal_ws, b=True)), 0.14)
rock_mask = saturate(slope)

# Layer the ground: sand, then deep sand, slickrock and gravel where the map says, then steep rock.
deep_a = saturate(add(mul(sub(deep_map, 0.5), 3.0), add(mul(edge_noise, 1.2), 0.5)))
slick_a = saturate(add(mul(sub(slick_map, 0.5), 3.0), add(mul(edge_noise, 1.6), 0.5)))
gravel_a = saturate(add(mul(sub(gravel_map, 0.45), 2.5), add(mul(edge_noise, 1.0), 0.5)))
base_color = lerp(sand_color, deep_color, deep_a)
base_normal = lerp(sand_normal, deep_normal, deep_a)
base_color = lerp(base_color, slick_color, slick_a)
base_normal = lerp(base_normal, slick_normal, slick_a)
base_color = lerp(base_color, gravel_color, gravel_a)
base_normal = lerp(base_normal, gravel_normal, gravel_a)
base_color = lerp(base_color, rock_color, rock_mask)
final_normal = lerp(base_normal, rock_normal, rock_mask)
# Seeps: damp, darker soil with a green cast.
base_color = mul(base_color, lerp(colour(1.0, 1.0, 1.0), colour(0.62, 0.66, 0.5), mul(seep_map, 0.85)))

roughness = lerp(lerp(lerp(0.92, 0.82, slick_a), 0.86, gravel_a), 0.8, rock_mask)
specular = expr(unreal.MaterialExpressionConstant, r=0.35)

for src, prop in ((base_color, unreal.MaterialProperty.MP_BASE_COLOR), (final_normal, unreal.MaterialProperty.MP_NORMAL),
                  (roughness, unreal.MaterialProperty.MP_ROUGHNESS), (specular, unreal.MaterialProperty.MP_SPECULAR)):
    if not mel.connect_material_property(src, "", prop):
        failures.append("property %s" % prop)

mel.recompile_material(mat)
eal.save_asset(path)
unreal.log("DESERTMAT saved %s, failures=%s" % (path, failures))
