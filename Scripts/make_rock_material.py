# Builds the rock material /Game/Desert/M_Rock with no textures (player, 2026-10-20: "remove all the textures"):
# sandstone colour from the per-layer Tint, soft world-height strata, large and small patches of procedural noise
# blended over the three world planes by the surface normal, dark desert varnish streaking down steep faces and sand
# settling on upward faces. The shape's own relief does the rest (no normal map).
# Rebuilt in place, keeping the parameters every instance sets (Tint, StrataContrast, StrataPeriodCm, Varnish,
# TileCm), so MI_Wingate, MI_Navajo, MI_Kayenta and the MI_Rock_* variants and every mesh keep working.
# Run from import_world.py or import_rocks.py.
import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
failures = []
path = "/Game/Desert/M_Rock"
if eal.does_asset_exist(path):
	if not eal.delete_asset(path):
		raise RuntimeError("Could not replace stale material asset " + path)
mat = tools.create_asset("M_Rock", "/Game/Desert", unreal.Material, unreal.MaterialFactoryNew())
# Cooked games only get shaders for declared usages: rocks are Nanite meshes, sometimes instanced.
mat.set_editor_property("used_with_nanite", True)
mat.set_editor_property("used_with_instanced_static_meshes", True)
y_cursor = [0]


def expr(cls, **props):
    y_cursor[0] += 120
    e = mel.create_material_expression(mat, cls, -1000, y_cursor[0])
    for key, value in props.items():
        e.set_editor_property(key, value)
    return e


def scalar(name, value):
    return expr(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)


inputs = [("P", expr(unreal.MaterialExpressionWorldPosition)), ("N", expr(unreal.MaterialExpressionVertexNormalWS)),
          ("Tint", expr(unreal.MaterialExpressionVectorParameter, parameter_name="Tint", default_value=unreal.LinearColor(1.0, 1.0, 1.0, 1.0))),
          ("Contrast", scalar("StrataContrast", 0.3)), ("Period", scalar("StrataPeriodCm", 500.0)),
          ("Varnish", scalar("Varnish", 0.0)), ("Tile", scalar("TileCm", 600.0))]
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
float3 w = pow(abs(N), 4.0);
w /= dot(w, float3(1, 1, 1)) + 1e-4;
float3 pm = P / max(Tile, 100.0);
float n1 = Nz.Fbm(pm.yz) * w.x + Nz.Fbm(pm.xz) * w.y + Nz.Fbm(pm.xy) * w.z;
float n2 = Nz.Value(pm.yz * 9.0) * w.x + Nz.Value(pm.xz * 9.0) * w.y + Nz.Value(pm.xy * 9.0) * w.z;
float up = saturate((N.z - 0.72) / 0.18);
"""
COLOUR = LIB + r"""
float3 col = float3(0.28, 0.10, 0.05) * Tint.rgb;
float band = sin(6.2831 * frac(P.z / max(Period, 50.0) + n1 * 0.6)) * 0.5 + 0.5;
col *= lerp(1.0 - Contrast, 1.0, band) * (0.82 + 0.3 * n1) * (0.94 + 0.12 * n2);
float wv = w.x + w.y + 1e-3;
float streak = (Nz.Value(float2(P.y / 600.0, P.z / 9000.0)) * w.x + Nz.Value(float2(P.x / 600.0, P.z / 9000.0)) * w.y) / wv;
float varnish = saturate((streak - 0.45) * 3.0) * saturate((0.6 - abs(N.z)) / 0.3) * Varnish;
col = lerp(col, col * float3(0.3, 0.22, 0.19), varnish);
col = lerp(col, float3(0.58, 0.18, 0.065) * (0.9 + 0.15 * n1), up);
return col;
"""
ROUGH = LIB + "return lerp(0.86, 0.93, up);"
nodes = []
custom_inputs = []
for name, _ in inputs:
    custom_input = unreal.CustomInput()
    custom_input.set_editor_property("input_name", name)
    custom_inputs.append(custom_input)
for code, out_type in ((COLOUR, unreal.CustomMaterialOutputType.CMOT_FLOAT3), (ROUGH, unreal.CustomMaterialOutputType.CMOT_FLOAT1)):
    node = expr(unreal.MaterialExpressionCustom, code=code, output_type=out_type, inputs=custom_inputs)
    for name, src in inputs:
        if not mel.connect_material_expressions(src, "", node, name):
            failures.append("input " + name)
    nodes.append(node)
for src, prop in ((nodes[0], unreal.MaterialProperty.MP_BASE_COLOR), (nodes[1], unreal.MaterialProperty.MP_ROUGHNESS)):
    if not mel.connect_material_property(src, "", prop):
        failures.append("property %s" % prop)
mel.recompile_material(mat)
eal.save_asset(path)
unreal.log("ROCKMAT saved %s (no textures), failures=%s" % (path, failures))
