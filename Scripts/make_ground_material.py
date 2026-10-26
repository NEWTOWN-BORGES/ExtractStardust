# Builds the landscape material /Game/World/M_World with no textures at all (the player found every tiled texture
# "quadriculado"): colour and relief come from the slope, the height and procedural noise computed in the shader.
#  - sand: warm red-orange, wind ripples at two scales (35 cm and 3 m) as an analytic normal and a light/dark crest
#    tint, fine grain up close, all fading with distance so nothing shimmers;
#  - rock: wherever the ground is steep, red-brown with soft beds by height; the high plateau paler (Navajo);
#  - green floor: the expedition's green layer (soft, broken by noise);
#  - road: the track distance field (export_*_unreal.py) cut at the floor's edge: packed darker sand, smooth, with a
#    thin pale band along each edge so the way reads at speed; the cut widens with distance (no shimmering edge).
# The two data maps it reads (track distance, green) are uncompressed and smooth, and only ever used through soft
# ramps: thresholds on compressed or blocky masks were what drew squares on the ground.
# Run from import_world.py (it replaces make_world_material.py).
import json
import os

import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
WORLD = os.environ.get("EX_WORLD_DIR", "C:/rdd/mundo")
meta = json.load(open(WORLD + "/unreal/world_unreal.json"))
failures = []
path = "/Game/World/M_World"
if eal.does_asset_exist(path):
	if not eal.delete_asset(path):
		raise RuntimeError("Could not replace stale material asset " + path)
mat = tools.create_asset("M_World", "/Game/World", unreal.Material, unreal.MaterialFactoryNew())
y_cursor = [0]


def expr(cls, **props):
    y_cursor[0] += 120
    e = mel.create_material_expression(mat, cls, -1000, y_cursor[0])
    for key, value in props.items():
        e.set_editor_property(key, value)
    return e


def link(src, dst, pin, out=""):
    if not mel.connect_material_expressions(src, out, dst, pin):
        failures.append("%s -> %s.%s" % (src.get_name(), dst.get_name(), pin))


def custom(code, inputs, out_type):
    custom_inputs = []
    for name, _ in inputs:
        custom_input = unreal.CustomInput()
        custom_input.set_editor_property("input_name", name)
        custom_inputs.append(custom_input)
    e = expr(unreal.MaterialExpressionCustom, code=code, output_type=out_type, inputs=custom_inputs)
    for name, src in inputs:
        link(src, e, name, "A" if src is surface else "")  # the green layer is the surface map's alpha
    return e


world = expr(unreal.MaterialExpressionWorldPosition)
normal_ws = expr(unreal.MaterialExpressionVertexNormalWS)
camera = expr(unreal.MaterialExpressionCameraPositionWS)
surface = None
uv = custom("return (P.xy - float2(%f, %f)) / float2(%f, %f);" % (tuple(meta["surface_origin_cm"]) + tuple(meta["surface_size_cm"])),
            [("P", world)], unreal.CustomMaterialOutputType.CMOT_FLOAT2)
track = expr(unreal.MaterialExpressionTextureSample, texture=eal.load_asset("/Game/World/T_WorldTrack"),
             sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
link(uv, track, "UVs")
surface = expr(unreal.MaterialExpressionTextureSample, texture=eal.load_asset("/Game/World/T_WorldSurface"),
               sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
link(uv, surface, "UVs")

# HLSL shared by the three outputs. A Custom node's code is the body of a function, so the noise lives in a struct.
# Inputs: P world position (cm), N vertex normal, C camera (cm), T track distance sample, G green layer (surface A).
# Noise: value noise on a lattice wrapped every 1024 cells and hashed without sine (exact at any distance from the
# origin); periodic phases go through frac() first for the same reason.
LIB = r"""
struct FEXNoise
{
    float Hash(float2 p)
    {
        p = p - 1024.0 * floor(p / 1024.0);
        float3 p3 = frac(float3(p.xyx) * 0.1031);
        p3 += dot(p3, p3.yzx + 33.33);
        return frac((p3.x + p3.y) * p3.z);
    }
    float Value(float2 p)
    {
        float2 i = floor(p);
        float2 f = frac(p);
        f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), f.x), lerp(Hash(i + float2(0, 1)), Hash(i + float2(1, 1)), f.x), f.y);
    }
    float Fbm(float2 p)
    {
        float s = 0.0;
        float a = 0.5;
        for (int k = 0; k < 4; ++k) { s += a * Value(p); p = p * 2.03 + 17.0; a *= 0.5; }
        return s / 0.9375;
    }
};
FEXNoise Nz;
float2 q = P.xy / 100.0;
float dist = length(P - C) / 100.0;
float steep = saturate((0.80 - N.z) / 0.18);
float talus = saturate((0.96 - N.z) / 0.12) * (1.0 - steep);
float sdf = T.r * 64.0 - 32.0;
float soft = max(0.35, dist * 0.004);
float road = saturate(0.5 - sdf / soft);
float band = saturate(1.0 - abs(abs(sdf) - 1.25) / max(0.8, soft)) * saturate(1.0 - dist / 1400.0);
float zm = P.z / 100.0;
float big = Nz.Fbm(q / 320.0);
float mid = Nz.Fbm(q / 45.0);
float green = saturate((G - 0.4 + (Nz.Fbm(q / 9.0) - 0.5) * 0.6) * 3.0) * (1.0 - steep);
float2 wind = float2(0.82, 0.57);
float warp = Nz.Fbm(q / 23.0) - 0.5;
float c1 = frac(dot(q, wind) / 0.35 + warp * 4.0);
float c2 = frac(dot(q, wind * 0.95 + float2(-wind.y, wind.x) * 0.3) / 3.0 + warp);
float fadeS = saturate(1.0 - dist / 70.0);
float fadeL = saturate(1.0 - dist / 600.0);
float sandness = (1.0 - steep) * (1.0 - talus * 0.6) * (1.0 - road) * (1.0 - green);
"""
COLOUR = LIB + r"""
float fine = Nz.Value(q * 3.1);
float grain = Nz.Value(q * 41.0) * saturate(1.0 - dist / 18.0);
float3 sandDark = float3(0.38, 0.10, 0.035);
float3 sandMid = float3(0.58, 0.18, 0.065);
float3 sandPale = float3(0.70, 0.33, 0.15);
float3 sand = lerp(sandDark, sandMid, saturate(big * 1.6 - 0.25));
sand = lerp(sand, sandPale, saturate(mid * 1.8 - 0.95) * 0.7);
float crest = (sin(6.2831 * c1) * fadeS * 0.5 + sin(6.2831 * c2) * fadeL) * 0.035;
sand *= 0.95 + 0.07 * fine + 0.08 * grain + crest;
float beds = sin(6.2831 * frac(zm / 7.0 + Nz.Fbm(q / 60.0) * 0.5)) * 0.5 + 0.5;
float3 rock = lerp(float3(0.24, 0.06, 0.028), float3(0.46, 0.15, 0.06), beds * 0.55 + mid * 0.45);
rock = lerp(rock, float3(0.62, 0.36, 0.20), saturate((zm - 400.0) / 60.0) * 0.75);
float3 rubble = lerp(float3(0.34, 0.10, 0.045), float3(0.46, 0.16, 0.07), fine);
float3 col = lerp(sand, rubble, talus * 0.7);
col = lerp(col, rock, steep);
col = lerp(col, lerp(float3(0.10, 0.13, 0.04), float3(0.20, 0.23, 0.07), mid), green);
float3 packed = lerp(float3(0.20, 0.045, 0.018), float3(0.27, 0.075, 0.03), mid) * (0.98 + 0.035 * fine);
col = lerp(col, packed, road * (1.0 - steep * 0.7));
// Keep the Blender terrain and track mask; warm double shoulders make the existing road read clearly at speed.
col = lerp(col, float3(0.88, 0.43, 0.16), band * (1.0 - steep) * 0.82);
return col;
"""
NORMAL = LIB + r"""
float d1 = (cos(6.2831 * c1) + 0.5 * cos(12.5662 * c1)) * 0.012 * (6.2831 / 0.35) * fadeS;
float d2 = (cos(6.2831 * c2) + 0.4 * cos(12.5662 * c2)) * 0.05 * (6.2831 / 3.0) * fadeL;
float2 g = wind * (d1 + d2) * sandness;
float2 r = (float2(Nz.Value(q * 1.7), Nz.Value(q * 1.7 + 31.0)) - 0.5) * (0.3 * steep + 0.2 * talus) * fadeL;
return normalize(float3(r.x - g.x, r.y - g.y, 1.0));
"""
ROUGH = LIB + "return lerp(lerp(0.94, 0.82, steep), 0.88, road);"
ins = [("P", world), ("N", normal_ws), ("C", camera), ("T", track), ("G", surface)]
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
colour_node = custom(COLOUR, ins, F3)
normal_node = custom(NORMAL, ins, F3)
rough_node = custom(ROUGH, ins, F1)
spec = expr(unreal.MaterialExpressionConstant, r=0.3)
for src, prop in ((colour_node, unreal.MaterialProperty.MP_BASE_COLOR), (normal_node, unreal.MaterialProperty.MP_NORMAL),
                  (rough_node, unreal.MaterialProperty.MP_ROUGHNESS), (spec, unreal.MaterialProperty.MP_SPECULAR)):
    if not mel.connect_material_property(src, "", prop):
        failures.append("property %s" % prop)
mel.recompile_material(mat)
eal.save_asset(path)

# Guide posts, as before.
bpath = "/Game/World/M_Beacon"
if eal.does_asset_exist(bpath):
    mat = eal.load_asset(bpath)
    mel.delete_all_material_expressions(mat)
else:
    mat = tools.create_asset("M_Beacon", "/Game/World", unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property("used_with_instanced_static_meshes", True)
for value, prop in (((0.05, 0.02, 0.01), unreal.MaterialProperty.MP_BASE_COLOR), ((12.0, 3.2, 0.5), unreal.MaterialProperty.MP_EMISSIVE_COLOR)):
    c = expr(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(value[0], value[1], value[2], 1.0))
    if not mel.connect_material_property(c, "", prop):
        failures.append("beacon %s" % prop)
mel.recompile_material(mat)
eal.save_asset(bpath)
unreal.log("WORLDMAT saved %s (no textures), failures=%s" % (path, failures))
