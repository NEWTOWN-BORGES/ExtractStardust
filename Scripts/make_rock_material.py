# Builds the rock material /Game/Desert/M_Rock, photoreal (player, 2026-10-26: "fotorrealista tipo Call of Duty";
# Docs/PLANO_TEXTURAS.md): the same CC0 sandstone photo as the canyon walls of M_World (cliff_side), projected from the
# three sides so nothing stretches, read twice per side with a slowly varying shift so it never repeats in place, under
# the per-layer Tint, soft strata by world height, dark desert varnish streaking down steep faces and sand settling on
# upward faces. The textures are read by ordinary texture nodes (shared sampler), not inside the HLSL: the rocks are
# Nanite, where only the graph's samples get their derivatives right.
# Rebuilt in place, keeping the parameters every instance sets (Tint, StrataContrast, StrataPeriodCm, Varnish, TileCm),
# so MI_Wingate, MI_Navajo, MI_Kayenta and the MI_Rock_* variants and every mesh keep working.
# Run from import_world.py or import_rocks.py.
import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
SRC = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "SourceArt/PolyHaven/"
TEX = "/Game/World/Textures/"
failures = []


def photo(name, kind):
    path = TEX + "T_%s_%s" % (name, kind)
    if not eal.does_asset_exist(path):
        task = unreal.AssetImportTask()
        task.filename = SRC + "%s/%s_%s_2k.jpg" % (name, name, kind)
        task.destination_path = TEX[:-1]
        task.destination_name = "T_%s_%s" % (name, kind)
        task.automated = True
        task.save = True
        task.replace_existing = True
        tools.import_asset_tasks([task])
    tex = eal.load_asset(path)
    if not tex:
        failures.append("missing " + path)
        return None
    tex.set_editor_property("srgb", kind == "diff")
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP if kind == "nor_dx"
                            else unreal.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD)
    tex.set_editor_property("never_stream", True)
    eal.save_loaded_asset(tex)
    return tex


path = "/Game/Desert/M_Rock"
if eal.does_asset_exist(path):
    mat = eal.load_asset(path)
    mel.delete_all_material_expressions(mat)
else:
    mat = tools.create_asset("M_Rock", "/Game/Desert", unreal.Material, unreal.MaterialFactoryNew())
# Cooked games only get shaders for declared usages: rocks are Nanite meshes, sometimes instanced.
mat.set_editor_property("used_with_nanite", True)
mat.set_editor_property("used_with_instanced_static_meshes", True)
mat.set_editor_property("tangent_space_normal", False)
y_cursor = [0]


def expr(cls, **props):
    y_cursor[0] += 120
    e = mel.create_material_expression(mat, cls, -1200, y_cursor[0])
    for key, value in props.items():
        e.set_editor_property(key, value)
    return e


def link(src, dst, pin, out=""):
    if not mel.connect_material_expressions(src, out, dst, pin):
        failures.append("%s.%s -> %s.%s" % (src.get_name(), out, dst.get_name(), pin))


def custom(code, inputs, out_type, extra_outputs=()):
    custom_inputs = []
    for name, _src, _out in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        custom_inputs.append(ci)
    e = expr(unreal.MaterialExpressionCustom, code=code, output_type=out_type, inputs=custom_inputs)
    if extra_outputs:
        outs = []
        for name, kind in extra_outputs:
            co = unreal.CustomOutput()
            co.set_editor_property("output_name", name)
            co.set_editor_property("output_type", kind)
            outs.append(co)
        e.set_editor_property("additional_outputs", outs)
    for name, src, out in inputs:
        link(src, e, name, out)
    return e


def scalar(name, value):
    return expr(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)


F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F2 = unreal.CustomMaterialOutputType.CMOT_FLOAT2
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
world = expr(unreal.MaterialExpressionWorldPosition)
normal_ws = expr(unreal.MaterialExpressionVertexNormalWS)
tint = expr(unreal.MaterialExpressionVectorParameter, parameter_name="Tint", default_value=unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
contrast = scalar("StrataContrast", 0.3)
period = scalar("StrataPeriodCm", 500.0)
varnish = scalar("Varnish", 0.0)
tile = scalar("TileCm", 700.0)

# The six UVs (two shifted readings on each of the three sides) and the blend between the two readings of each side.
UVGEN = r"""
struct FEXRockUV
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
    // Two readings of one side: the shifts of the index's floor and the next one, and how far between them.
    void Pair(float2 uv, out float2 A, out float2 B, out float Blend)
    {
        float l = Value(uv * 0.11) * 8.0;
        float i = floor(l);
        float2 w = uv - floor(uv / 64.0) * 64.0;
        A = w + frac(sin(float2(3.1, 7.7) * i) * 437.585);
        B = w + frac(sin(float2(3.1, 7.7) * (i + 1.0)) * 437.585);
        Blend = smoothstep(0.2, 0.8, l - i);
    }
};
FEXRockUV R;
float3 Pm = P / max(Tile, 100.0);
float2 a, b;
float bl;
R.Pair(float2(Pm.y, -Pm.z), a, b, bl); float2 X0 = a; X1 = b; BX = bl;
R.Pair(float2(Pm.x, -Pm.z) + 3.7, a, b, bl); Y0 = a; Y1 = b; BY = bl;
R.Pair(Pm.xy + 7.3, a, b, bl); Z0 = a; Z1 = b; BZ = bl;
return X0;
"""
uvgen = custom(UVGEN, [("P", world, ""), ("Tile", tile, "")], F2,
               extra_outputs=(("X1", F2), ("Y0", F2), ("Y1", F2), ("Z0", F2), ("Z1", F2), ("BX", F1), ("BY", F1), ("BZ", F1)))
diff = photo("cliff_side", "diff")
nrm = photo("cliff_side", "nor_dx")
samples = []
for uv_out in ("", "X1", "Y0", "Y1", "Z0", "Z1"):
    for tex, kind in ((diff, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR), (nrm, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)):
        s = expr(unreal.MaterialExpressionTextureSample, texture=tex, sampler_type=kind,
                 sampler_source=unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        link(uvgen, s, "UVs", uv_out)
        samples.append(s)

SHADE = r"""
float3 w = pow(abs(N), 4.0);
w /= dot(w, float3(1, 1, 1));
float3 cx = lerp(CX0, CX1, BX), cy = lerp(CY0, CY1, BY), cz = lerp(CZ0, CZ1, BZ);
float3 nx = lerp(NX0, NX1, BX), ny = lerp(NY0, NY1, BY), nz = lerp(NZ0, NZ1, BZ);
// Each side's photo normal onto the surface (whiteout), with the photo's top kept up on the walls.
float3 wx = float3(N.x, nx.x + N.y, -nx.y + N.z);
float3 wy = float3(ny.x + N.x, N.y, -ny.y + N.z);
float3 wz = float3(nz.x + N.x, nz.y + N.y, N.z);
NormalWS = normalize(wx * w.x + wy * w.y + wz * w.z);
float3 col = (cx * w.x + cy * w.y + cz * w.z) * float3(1.52, 1.21, 1.36);   // balanced to the canyon walls of M_World
// The rock layer's own colour (Tint, ~1.45 on average) and its beds by height.
col *= Tint.rgb / 1.45;
float band = sin(6.2831 * frac(P.z / max(Period, 50.0))) * 0.5 + 0.5;
col *= lerp(1.0 - Contrast, 1.0, band);
// Desert varnish: dark streaks down steep faces.
float steepF = saturate((0.6 - abs(N.z)) / 0.3);
float streak = frac(sin(dot(floor(float2(P.x + P.y, P.z * 0.02) / float2(260.0, 1.0)), float2(12.9898, 78.233))) * 43758.5453);
col = lerp(col, col * float3(0.32, 0.24, 0.2), saturate((streak - 0.55) * 3.0) * steepF * Varnish);
// Red sand settled on the upward faces.
float up = saturate((N.z - 0.75) / 0.18);
col = lerp(col, float3(0.42, 0.17, 0.075), up * 0.85);
Rough = lerp(0.82, 0.94, up);
return min(col, 0.85);
"""
names = []
for side in ("X", "Y", "Z"):
    for k in ("0", "1"):
        names += [("C" + side + k), ("N" + side + k)]
shade_inputs = [("N", normal_ws, ""), ("P", world, ""), ("Tint", tint, ""), ("Contrast", contrast, ""), ("Period", period, ""),
                ("Varnish", varnish, ""), ("BX", uvgen, "BX"), ("BY", uvgen, "BY"), ("BZ", uvgen, "BZ")]
for name, node in zip(names, samples):
    shade_inputs.append((name, node, ""))
shade = custom(SHADE, shade_inputs, F3, extra_outputs=(("NormalWS", F3), ("Rough", F1)))
for out, prop in (("", unreal.MaterialProperty.MP_BASE_COLOR), ("NormalWS", unreal.MaterialProperty.MP_NORMAL),
                  ("Rough", unreal.MaterialProperty.MP_ROUGHNESS)):
    if not mel.connect_material_property(shade, out, prop):
        failures.append("property %s" % prop)
mel.recompile_material(mat)
eal.save_asset(path)
unreal.log("ROCKMAT saved %s (photoreal cliff_side, triplanar), failures=%s" % (path, failures))
