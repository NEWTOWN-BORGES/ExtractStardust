# Builds the landscape material /Game/World/M_World, photoreal (player, 2026-10-26: "fotorrealista tipo Call of Duty",
# "texturas ricas, sem os quadrados"; Docs/PLANO_TEXTURAS.md). CC0 photo-scanned materials (Poly Haven, 2K: colour,
# DirectX normal, AO/roughness/metal), one per layer:
#   sand        red_sand                  flat floor, with the wind ripples computed in the shader on top
#   road        dry_ground_rocks + sand   the track as a natural dry wash of the canyon (player, 2026-10-26: "natural,
#                                         não algo cavado"): pebbles and sand, its edge wandering, no built border
#   gravel      dry_ground_rocks          talus and mid slopes
#   cliff       cliff_side                steep walls, projected from three sides (nothing stretched), strata by height
#   plateau     sandstone_cracks          the high slickrock (Navajo)
#   grass       aerial_grass_rock         the green floors
# No visible repetition anywhere: every layer is read twice, shifted by a slowly varying index and blended (Quilez's
# technique), at two scales, under a very wide colour variation; the UVs wrap so the precision holds far from the
# origin, with the gradients of the unwrapped UVs so the mip level never jumps. The data maps (track, green) stay
# uncompressed and are only used through soft ramps. Each layer's colour is balanced to one desert palette, so the photos
# from different places sit together. The normal leaves the material in world space.
# Run from import_world.py (EX_WORLD_DIR) after the data maps are imported; imports the photos it needs if missing.
import json
import os

import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
WORLD = os.environ.get("EX_WORLD_DIR", "C:/rdd/mundo")
meta = json.load(open(WORLD + "/unreal/world_unreal.json"))
SRC = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "SourceArt/PolyHaven/"
TEX = "/Game/World/Textures/"
LAYERS = ["red_sand", "dry_ground_rocks", "cliff_side", "sandstone_cracks", "aerial_grass_rock"]
failures = []


def photo(name, kind):
    """/Game/World/Textures/T_<name>_<kind>, imported from SourceArt/PolyHaven if missing; data, compression and
    streaming set for a world-position material (never streamed: the streamer cannot see these UVs)."""
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
                            else (unreal.TextureCompressionSettings.TC_MASKS if kind == "arm" else unreal.TextureCompressionSettings.TC_DEFAULT))
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD)
    tex.set_editor_property("never_stream", True)
    eal.save_loaded_asset(tex)
    return tex


path = "/Game/World/M_World"
if eal.does_asset_exist(path):
    mat = eal.load_asset(path)
    mel.delete_all_material_expressions(mat)  # rebuilt in place, so the landscape keeps its reference
else:
    mat = tools.create_asset("M_World", "/Game/World", unreal.Material, unreal.MaterialFactoryNew())
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
        failures.append("%s -> %s.%s" % (src.get_name(), dst.get_name(), pin))


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


F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F2 = unreal.CustomMaterialOutputType.CMOT_FLOAT2
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3

world = expr(unreal.MaterialExpressionWorldPosition)
normal_ws = expr(unreal.MaterialExpressionVertexNormalWS)
camera = expr(unreal.MaterialExpressionCameraPositionWS)
uv = custom("return (P.xy - float2(%f, %f)) / float2(%f, %f);" % (tuple(meta["surface_origin_cm"]) + tuple(meta["surface_size_cm"])),
            [("P", world, "")], F2)
track = expr(unreal.MaterialExpressionTextureSample, texture=eal.load_asset("/Game/World/T_WorldTrack"),
             sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
link(uv, track, "UVs")
surface = expr(unreal.MaterialExpressionTextureSample, texture=eal.load_asset("/Game/World/T_WorldSurface"),
               sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
link(uv, surface, "UVs")

# The photos as texture objects: the shader reads them all through the first one's sampler (one sampler, many
# textures: well under the 16-sampler limit).
SHORT = {"red_sand": "Sa", "dry_ground_rocks": "Gr", "cliff_side": "Cl",
         "sandstone_cracks": "Pl", "aerial_grass_rock": "Gs"}
tex_inputs = []
for name in LAYERS:
    for kind, suffix in (("diff", "D"), ("nor_dx", "N"), ("arm", "A")):
        tex = photo(name, kind)
        node = expr(unreal.MaterialExpressionTextureObject, texture=tex,
                    sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind == "nor_dx"
                    else (unreal.MaterialSamplerType.SAMPLERTYPE_MASKS if kind == "arm" else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR))
        tex_inputs.append((SHORT[name] + suffix, node, ""))

CODE = r"""
struct FEXGround
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
    // One photo layer read without visible tiling: twice, shifted by a slowly varying index, blended by a soft mask.
    void Tap(Texture2D D, Texture2D Nm, Texture2D A, SamplerState S, float2 uv, float2 dx, float2 dy,
             out float3 Col, out float2 Nxy, out float3 Arm)
    {
        float l = Value(uv * 0.11) * 8.0;
        float i = floor(l);
        float f = l - i;
        float2 oa = frac(sin(float2(3.1, 7.7) * i) * 437.585);
        float2 ob = frac(sin(float2(3.1, 7.7) * (i + 1.0)) * 437.585);
        float2 w = uv - floor(uv / 64.0) * 64.0;
        float3 ca = D.SampleGrad(S, w + oa, dx, dy).rgb;
        float3 cb = D.SampleGrad(S, w + ob, dx, dy).rgb;
        float b = smoothstep(0.2, 0.8, f - 0.1 * dot(ca - cb, float3(1, 1, 1)));
        Col = lerp(ca, cb, b);
        Nxy = lerp(Nm.SampleGrad(S, w + oa, dx, dy).xy, Nm.SampleGrad(S, w + ob, dx, dy).xy, b) * 2.0 - 1.0;
        Arm = lerp(A.SampleGrad(S, w + oa, dx, dy).rgb, A.SampleGrad(S, w + ob, dx, dy).rgb, b);
    }
};
FEXGround G;
#define EXS SaDSampler
float3 Pm = P / 100.0;                                   // metres
float2 q = Pm.xy;
float2 qdx = ddx(q), qdy = ddy(q);
float3 Pdx = ddx(Pm), Pdy = ddy(Pm);
float dist = length(P - C) / 100.0;
float nearF = saturate(1.0 - dist / 80.0);
float farF = saturate((dist - 40.0) / 220.0);

// ---- Where each layer goes (all soft: no hard thresholds anywhere).
float steep = saturate((0.80 - N.z) / 0.18);
float talus = saturate((0.97 - N.z) / 0.14) * (1.0 - steep);
float sdf = T.r * 64.0 - 32.0;                           // metres from the floor's edge, negative inside
float soft = max(0.35, dist * 0.004);
// The wash's edge wanders a few metres either way and fades over several, as a dry riverbed's does.
float edgeNoise = (G.Fbm(q / 22.0) - 0.5) * 8.0 + (G.Value(q / 5.0) - 0.5) * 2.0;
float road = saturate(0.5 - (sdf + edgeNoise) / (soft + 3.5));
float berm = 0.0;
float plateau = saturate((Pm.z - 395.0) / 45.0) * (1.0 - steep);
float green = saturate((Gm - 0.4 + (G.Fbm(q / 9.0) - 0.5) * 0.6) * 3.0) * (1.0 - steep);
float breakup = G.Fbm(q / 7.0) - 0.5;
talus = saturate(talus + breakup * 0.5 * talus);

float3 col = 0;
float3 nWS = 0;
float rough = 0;
float ao = 0;
float wsum = 0;
float3 c1, c2, a1, a2;
float2 n1, n2;
float crest = 0.0;
float glint = 0.0;

// ---- Flat layers (projected from above): weight, then two scales.
float wSand = (1.0 - steep) * (1.0 - talus) * (1.0 - road) * (1.0 - plateau) * (1.0 - green);
float wRoad = road * (1.0 - steep * 0.8);
float wGrav = talus * (1.0 - road);
float wPlat = plateau * (1.0 - road) * (1.0 - talus);
float wGrass = green * (1.0 - road);
float wCliff = steep * (1.0 - road * 0.2);
float3 flatN = 0;

[branch] if (wSand > 0.002)
{
    G.Tap(SaD, SaN, SaA, EXS, q / 2.2, qdx / 2.2, qdy / 2.2, c1, n1, a1);
    G.Tap(SaD, SaN, SaA, EXS, q / 11.0 + 17.3, qdx / 11.0, qdy / 11.0, c2, n2, a2);
    float m = lerp(0.35, 1.0, farF);
    float3 c = lerp(c1, c2, m) * float3(2.05, 1.5, 1.0);
    col += c * wSand; flatN += float3(lerp(n1, n2, m) * 0.8, 0) * wSand; rough += lerp(a1.g, a2.g, m) * wSand; ao += lerp(a1.r, a2.r, m) * wSand; wsum += wSand;
}
[branch] if (wRoad > 0.002)
{
    // The dry wash: pebbles where the water ran, sand between them, in patches.
    G.Tap(GrD, GrN, GrA, EXS, q / 3.2 + 5.1, qdx / 3.2, qdy / 3.2, c1, n1, a1);
    G.Tap(SaD, SaN, SaA, EXS, q / 2.2 + 11.3, qdx / 2.2, qdy / 2.2, c2, n2, a2);
    float m = saturate(0.55 + (G.Fbm(q / 9.0) - 0.5) * 0.9);
    float3 c = lerp(c2 * float3(2.05, 1.5, 1.0), c1 * float3(1.18, 0.9, 0.94), m) * 0.94;
    col += c * wRoad; flatN += float3(lerp(n2, n1, m), 0) * wRoad; rough += lerp(a2.g, a1.g, m) * wRoad; ao += lerp(a2.r, a1.r, m) * wRoad; wsum += wRoad;
}
[branch] if (wGrav > 0.002)
{
    G.Tap(GrD, GrN, GrA, EXS, q / 3.5 + 9.7, qdx / 3.5, qdy / 3.5, c1, n1, a1);
    G.Tap(GrD, GrN, GrA, EXS, q / 15.0 + 2.9, qdx / 15.0, qdy / 15.0, c2, n2, a2);
    float m = lerp(0.3, 1.0, farF);
    float3 c = lerp(c1, c2, m) * float3(1.08, 0.84, 0.94);
    col += c * wGrav; flatN += float3(lerp(n1, n2, m), 0) * wGrav; rough += lerp(a1.g, a2.g, m) * wGrav; ao += lerp(a1.r, a2.r, m) * wGrav; wsum += wGrav;
}
[branch] if (wPlat > 0.002)
{
    G.Tap(PlD, PlN, PlA, EXS, q / 6.0 + 3.3, qdx / 6.0, qdy / 6.0, c1, n1, a1);
    G.Tap(PlD, PlN, PlA, EXS, q / 25.0 + 7.1, qdx / 25.0, qdy / 25.0, c2, n2, a2);
    float m = lerp(0.3, 1.0, farF);
    float3 c = lerp(c1, c2, m) * float3(0.875, 0.84, 0.91);
    col += c * wPlat; flatN += float3(lerp(n1, n2, m), 0) * wPlat; rough += lerp(a1.g, a2.g, m) * wPlat; ao += lerp(a1.r, a2.r, m) * wPlat; wsum += wPlat;
}
[branch] if (wGrass > 0.002)
{
    G.Tap(GsD, GsN, GsA, EXS, q / 4.0 + 1.7, qdx / 4.0, qdy / 4.0, c1, n1, a1);
    col += c1 * wGrass; flatN += float3(n1, 0) * wGrass; rough += a1.g * wGrass; ao += a1.r * wGrass; wsum += wGrass;
}
// The flat layers' normal onto the ground (whiteout blend), plus the wind ripples on loose sand.
{
    float2 wind = float2(0.82, 0.57);
    float warp = G.Fbm(q / 23.0) - 0.5;
    float k1 = frac(dot(q, wind) / 0.35 + warp * 4.0);
    float k2 = frac(dot(q, wind * 0.95 + float2(-wind.y, wind.x) * 0.3) / 3.0 + warp);
    float k0 = frac(dot(q, wind) / 0.12 + warp * 9.0);
    float r0 = (cos(6.2831 * k0) + 0.5 * cos(12.5662 * k0)) * 0.004 * (6.2831 / 0.12) * saturate(1.0 - dist / 22.0);
    float r1 = (cos(6.2831 * k1) + 0.5 * cos(12.5662 * k1)) * 0.012 * (6.2831 / 0.35) * nearF;
    float r2 = (cos(6.2831 * k2) + 0.4 * cos(12.5662 * k2)) * 0.05 * (6.2831 / 3.0) * saturate(1.0 - dist / 600.0);
    float loose = wSand / max(wsum + wCliff, 1e-3) * (1.0 - road) + berm * 0.5;
    float2 ripple = -wind * (r0 + r1 + r2) * loose;
    // Ripple crests catch the light and are made of finer, paler grains; the troughs hold the coarser, darker ones.
    crest = (0.05 * sin(6.2831 * k1) * nearF + 0.035 * sin(6.2831 * k2) * saturate(1.0 - dist / 600.0)) * loose;
    // Quartz grains glinting in the sun, close by.
    glint = step(0.9975, G.Hash(floor(q * 55.0))) * saturate(1.0 - dist / 10.0) * loose;
    float fade = lerp(1.0, 0.45, farF);   // far away the photo's small relief would only shimmer
    float2 t = (wsum > 0.0 ? flatN.xy / max(wsum, 1e-3) : float2(0.0, 0.0)) * fade + ripple;
    nWS += normalize(float3(t + N.xy, N.z)) * wsum;
}

// ---- Cliffs: the sandstone photo projected from the three sides (image top up, so its beds lie flat).
[branch] if (wCliff > 0.002)
{
    float3 bw = pow(abs(N), 4.0);
    bw /= dot(bw, float3(1, 1, 1));
    float3 cc = 0;
    float3 cn = 0;
    float2 cr = 0;
    for (int s = 0; s < 2; ++s)
    {
        float sc = s == 0 ? 7.0 : 29.0;
        float sw = s == 0 ? lerp(0.6, 0.15, farF) : lerp(0.4, 0.85, farF);
        float2 ox = float2(3.7, 1.9) * s;
        if (bw.x > 0.02)
        {
            G.Tap(ClD, ClN, ClA, EXS, float2(Pm.y, -Pm.z) / sc + ox, float2(Pdx.y, -Pdx.z) / sc, float2(Pdy.y, -Pdy.z) / sc, c1, n1, a1);
            cc += c1 * bw.x * sw; cn += float3(abs(1.0) * N.x, n1.x + N.y, -n1.y + N.z) * bw.x * sw; cr += float2(a1.g, a1.r) * bw.x * sw;
        }
        if (bw.y > 0.02)
        {
            G.Tap(ClD, ClN, ClA, EXS, float2(Pm.x, -Pm.z) / sc + ox, float2(Pdx.x, -Pdx.z) / sc, float2(Pdy.x, -Pdy.z) / sc, c1, n1, a1);
            cc += c1 * bw.y * sw; cn += float3(n1.x + N.x, N.y, -n1.y + N.z) * bw.y * sw; cr += float2(a1.g, a1.r) * bw.y * sw;
        }
        if (bw.z > 0.02)
        {
            G.Tap(ClD, ClN, ClA, EXS, Pm.xy / sc + ox, Pdx.xy / sc, Pdy.xy / sc, c1, n1, a1);
            cc += c1 * bw.z * sw; cn += float3(n1.x + N.x, n1.y + N.y, N.z) * bw.z * sw; cr += float2(a1.g, a1.r) * bw.z * sw;
        }
    }
    // The walls' beds by height (Wingate red below, paler Kayenta ledges higher), and dark desert varnish streaks.
    float beds = 0.86 + 0.14 * sin(Pm.z * 0.55 + G.Fbm(q / 40.0) * 4.0);
    float streak = G.Value(float2(dot(q, float2(0.7, 0.7)) / 5.0, Pm.z / 80.0));
    float varnish = saturate((streak - 0.55) * 3.0) * 0.45;
    float3 c = cc * float3(1.52, 1.21, 1.36) * beds * (1.0 - varnish);
    col += c * wCliff;
    nWS += normalize(cn) * wCliff;
    rough += cr.x * wCliff;
    ao += cr.y * wCliff;
    wsum += wCliff;
}

col /= max(wsum, 1e-3);
nWS = normalize(nWS);
rough /= max(wsum, 1e-3);
ao /= max(wsum, 1e-3);
// The wide variation every real desert has: patches of lighter and darker ground, and wind streaks along the dunes.
float macro = 0.84 + 0.32 * G.Fbm(q / 340.0);
float wstreak = 0.94 + 0.12 * G.Value(float2(dot(q, float2(0.82, 0.57)) / 420.0, dot(q, float2(-0.57, 0.82)) / 35.0));
col *= macro * lerp(wstreak, 1.0, steep);
col *= 1.0 + crest;
col = lerp(col, col * 1.6, glint);
col = min(col, 0.85);
NormalWS = nWS;
Rough = saturate(lerp(lerp(rough, 0.92, 0.15), 0.2, glint));
AmbOcc = saturate(lerp(1.0, ao, 0.8));
return col;
"""
ins = [("P", world, ""), ("N", normal_ws, ""), ("C", camera, ""), ("T", track, ""), ("Gm", surface, "A")] + tex_inputs
ground = custom(CODE, ins, F3, extra_outputs=(("NormalWS", F3), ("Rough", F1), ("AmbOcc", F1)))
spec = expr(unreal.MaterialExpressionConstant, r=0.35)
for out, prop in (("", unreal.MaterialProperty.MP_BASE_COLOR), ("NormalWS", unreal.MaterialProperty.MP_NORMAL),
                  ("Rough", unreal.MaterialProperty.MP_ROUGHNESS), ("AmbOcc", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)):
    if not mel.connect_material_property(ground, out, prop):
        failures.append("property %s" % prop)
if not mel.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR):
    failures.append("specular")
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
unreal.log("WORLDMAT saved %s (photoreal, %d photo layers), failures=%s" % (path, len(LAYERS), failures))
