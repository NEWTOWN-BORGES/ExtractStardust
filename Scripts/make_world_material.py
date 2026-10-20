# Builds the world's landscape material /Game/World/M_World from the Poly Haven texture sets (CC0) downloaded by
# download_polyhaven.py, layered by the world's surface map (export_world_unreal.py: R bare rock on the mesa tops,
# G deep dune sand, B gravel and talus, A green canyon floor) and by slope (steep ground is cliff, projected from
# the sides so it does not stretch):
#   sand: red_sand            dunes: aerial_sand (tinted, wind ripples)      mesa tops: sandstone_cracks
#   gravel: gravelly_sand, red_laterite_soil_stones in patches               green floor: aerial_grass_rock
#   cliffs: cliff_side
# Every layer gives colour, normal, roughness and ambient occlusion (ARM map). Borders between layers follow the
# texture's own relief (height blend), and a very large tint breaks the repetition. Run from import_world.py.
import json
import os

import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
PH = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "SourceArt/PolyHaven/"
TEXDIR = "/Game/World/Textures"
WORLD = os.environ.get("EX_WORLD_DIR", "C:/rdd/mundo")
# The player chose textures made by code (bake_world_textures.py) over photo sets.
WT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "SourceArt/WorldTex/"
SETS = ["ex_sand", "ex_dunes", "ex_slick", "ex_cliff", "ex_gravel", "ex_green"]
failures = []

# ---- Textures: colour (sRGB), DirectX normal, ARM masks (linear).
tasks = []
for name in SETS:
    for kind in ("diff", "nor_dx", "arm"):
        task = unreal.AssetImportTask()
        task.filename = "%sT_%s_%s.png" % (WT, name, kind)
        task.destination_path = TEXDIR
        task.destination_name = "T_%s_%s" % (name, kind)
        task.automated = True
        task.save = True
        task.replace_existing = True
        tasks.append(task)
tools.import_asset_tasks(tasks)
for name in SETS:
    for kind, settings in (("nor_dx", unreal.TextureCompressionSettings.TC_NORMALMAP), ("arm", unreal.TextureCompressionSettings.TC_MASKS)):
        path = "%s/T_%s_%s" % (TEXDIR, name, kind)
        tex = eal.load_asset(path)
        if not tex:
            failures.append("missing " + path)
            continue
        tex.set_editor_property("compression_settings", settings)
        tex.set_editor_property("srgb", False)
        eal.save_loaded_asset(tex)

meta = json.load(open(WORLD + "/unreal/world_unreal.json"))
path = "/Game/World/M_World"
if eal.does_asset_exist(path):
    eal.delete_asset(path)
mat = tools.create_asset("M_World", "/Game/World", unreal.Material, unreal.MaterialFactoryNew())
y_cursor = [0]
NORMAL = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
MASKS = unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
LINEAR = unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR


def expr(cls, **props):
    y_cursor[0] += 120
    e = mel.create_material_expression(mat, cls, -1400, y_cursor[0])
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


def mask(src, r=False, g=False, b=False, a=False, out=""):
    e = expr(unreal.MaterialExpressionComponentMask, r=r, g=g, b=b, a=a)
    link(src, e, "", out)
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


def vec2(x, y):
    return expr(unreal.MaterialExpressionConstant2Vector, r=x, g=y)


def sample(asset, uv, sampler=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR):
    e = expr(unreal.MaterialExpressionTextureSample, texture=eal.load_asset(asset), sampler_type=sampler,
             sampler_source=unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    link(uv, e, "UVs")
    return e


class Layer:
    """Colour, normal, roughness, ambient occlusion and a height (the colour's brightness) for one ground type."""

    def __init__(self, name, uv, tint=None, normal_strength=1.0):
        diff = sample("%s/T_%s_diff" % (TEXDIR, name), uv)
        self.color = mul(diff, colour(*tint)) if tint else diff
        n = sample("%s/T_%s_nor_dx" % (TEXDIR, name), uv, NORMAL)
        self.normal = n if normal_strength >= 1.0 else lerp(colour(0.0, 0.0, 1.0), n, normal_strength)
        arm = sample("%s/T_%s_arm" % (TEXDIR, name), uv, MASKS)
        self.rough = mask(arm, g=True)
        self.ao = mask(arm, r=True)
        self.height = mask(diff, g=True)

    @staticmethod
    def blend(a, b, alpha):
        out = Layer.__new__(Layer)
        out.color, out.normal = lerp(a.color, b.color, alpha), lerp(a.normal, b.normal, alpha)
        out.rough, out.ao, out.height = lerp(a.rough, b.rough, alpha), lerp(a.ao, b.ao, alpha), lerp(a.height, b.height, alpha)
        return out


def height_blend(weight, layer_height, sharp=4.0):
    """Turns a soft weight into a border that follows the incoming layer's relief (stones first, sand last)."""
    return saturate(add(mul(sub(weight, 0.5), sharp), add(mul(sub(layer_height, 0.5), 1.5), 0.5)))


world = expr(unreal.MaterialExpressionWorldPosition)
normal_ws = expr(unreal.MaterialExpressionVertexNormalWS)
xy = mask(world, r=True, g=True)

# Surface map and track map over the real (unpadded) world.
world_uv = div(sub(xy, vec2(*meta["surface_origin_cm"])), vec2(*meta["surface_size_cm"]))
surface = sample("/Game/World/T_WorldSurface", world_uv, LINEAR)
track_map = mask(sample("/Game/World/T_WorldTrack", world_uv, LINEAR), r=True)
rock_map, deep_map, gravel_map = mask(surface, r=True), mask(surface, g=True), mask(surface, b=True)
green_map = mask(surface, a=True, out="RGBA")
macro = mask(sample("/Game/Desert/Textures/T_Macro_D", div(xy, 40000.0), LINEAR), r=True)
patch = mask(sample("/Game/Desert/Textures/T_Macro_D", div(xy, 6000.0), LINEAR), r=True)

# Layers (tiling in cm per repeat).
sand = Layer("ex_sand", div(xy, 400.0))
dunes = Layer("ex_dunes", div(xy, 700.0))
tops = Layer("ex_slick", div(xy, 900.0))
gravel = Layer("ex_gravel", div(xy, 300.0))
green = Layer("ex_green", div(xy, 500.0))

# Cliffs: projected along X and along Y, weighted by how much the slope faces each way.
n_abs = expr(unreal.MaterialExpressionAbs)
link(normal_ws, n_abs, "")
wx = expr(unreal.MaterialExpressionPower, const_exponent=8.0)  # sharp: diagonal faces do not smear two projections
link(mask(n_abs, r=True), wx, "Base")
wy = expr(unreal.MaterialExpressionPower, const_exponent=8.0)
link(mask(n_abs, g=True), wy, "Base")
side = saturate(div(wy, add(add(wx, wy), 0.0001)))
cliff = Layer.blend(Layer("ex_cliff", div(mask(world, g=True, b=True), 1500.0), normal_strength=0.5),
                    Layer("ex_cliff", div(mask(world, r=True, b=True), 1500.0), normal_strength=0.5), side)

# Stack: sand -> dunes -> gravel -> green -> mesa tops -> cliffs on steep ground.
ground = Layer.blend(sand, dunes, height_blend(deep_map, dunes.height))
ground = Layer.blend(ground, gravel, height_blend(gravel_map, gravel.height))
ground = Layer.blend(ground, green, height_blend(green_map, green.height))
ground = Layer.blend(ground, tops, height_blend(rock_map, tops.height))
# The race line: sand packed hard and darkened by the craft, smoother, so the way ahead reads at speed.
packed = Layer.__new__(Layer)
packed.color = mul(sand.color, colour(0.72, 0.64, 0.58))
packed.normal = lerp(colour(0.0, 0.0, 1.0), sand.normal, 0.35)
packed.rough = mul(sand.rough, 0.85)
packed.ao = sand.ao
packed.height = sand.height
steep = saturate(div(sub(0.8, mask(normal_ws, b=True)), 0.18))
ground = Layer.blend(ground, packed, mul(saturate(mul(track_map, 1.4)), 0.85))
ground = Layer.blend(ground, cliff, steep)

# One very large tint (kilometres) so no two valleys look the same.
base = mul(ground.color, lerp(0.86, 1.1, macro))
for src, prop in ((base, unreal.MaterialProperty.MP_BASE_COLOR), (ground.normal, unreal.MaterialProperty.MP_NORMAL),
                  (ground.rough, unreal.MaterialProperty.MP_ROUGHNESS), (ground.ao, unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
                  (expr(unreal.MaterialExpressionConstant, r=0.3), unreal.MaterialProperty.MP_SPECULAR)):
    if not mel.connect_material_property(src, "", prop):
        failures.append("property %s" % prop)
mel.recompile_material(mat)
eal.save_asset(path)

# ---- M_Beacon: the glowing guide posts on the outside of the bends.
bpath = "/Game/World/M_Beacon"
if eal.does_asset_exist(bpath):
    eal.delete_asset(bpath)
mat = tools.create_asset("M_Beacon", "/Game/World", unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property("used_with_instanced_static_meshes", True)
for src, prop in ((colour(0.05, 0.02, 0.01), unreal.MaterialProperty.MP_BASE_COLOR),
                  (colour(12.0, 3.2, 0.5), unreal.MaterialProperty.MP_EMISSIVE_COLOR)):
    if not mel.connect_material_property(src, "", prop):
        failures.append("beacon %s" % prop)
mel.recompile_material(mat)
eal.save_asset(bpath)
unreal.log("WORLDMAT saved %s, failures=%s" % (path, failures))
