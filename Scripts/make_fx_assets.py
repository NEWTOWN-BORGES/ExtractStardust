# The explosion's and the wreck's assets (player, 2026-11-01: "melhore a explosão", "os módulos podem voar carbonizados";
# Docs/DESTROCOS.md). Run in the editor (Tools > Execute Python Script) or with -run=pythonscript, after
# Scripts/make_fx_flipbooks.py has rendered SourceArt/FX (casa_tudo.ps1, step 3d).
#   /Game/FX/T_FX_Fireball, T_FX_Smoke, T_FX_Fire  the flipbooks (RGB = colour premultiplied by opacity, A = opacity)
#   /Game/FX/M_FX_Flipbook  sprite material: unlit, premultiplied alpha (AlphaComposite: thin fire still glows, smoke
#                           darkens what is behind it), two frames blended, soft where it meets the ground.
#                           Parameters (AEXExplosion, AEXWreck): Tex, Cols, Rows, Frame, Color, Intensity, Opacity,
#                           Rotation (radians, clockwise on screen: the flames on a flying piece stream back), FlipV.
#   /Game/FX/M_FX_Char      overlay for the burnt hull and modules: soot darkens the paint (its own light and shape
#                           stay, at a fifth), cracks glowing like embers while "Heat" (1 -> 0) lasts.
import os

import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
SRC = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "SourceArt/FX/"
F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
failures = []

# ---------------------------------------------------------------------------------------------------- the flipbooks
textures = {}
tasks = []
for name in ("Fireball", "Smoke", "Fire"):
    path = SRC + "T_FX_%s.png" % name
    if not os.path.isfile(path):
        failures.append("missing %s (run Scripts/make_fx_flipbooks.py)" % path)
        continue
    t = unreal.AssetImportTask()
    t.filename = path
    t.destination_path = "/Game/FX"
    t.destination_name = "T_FX_%s" % name
    t.automated = True
    t.save = True
    t.replace_existing = True
    tasks.append(t)
tools.import_asset_tasks(tasks)
for name in ("Fireball", "Smoke", "Fire"):
    tex = eal.load_asset("/Game/FX/T_FX_%s" % name)
    if not tex:
        failures.append("T_FX_%s not imported" % name)
        continue
    tex.set_editor_property("srgb", True)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_EFFECTS)
    eal.save_loaded_asset(tex)
    textures[name] = tex


def blend(name):
    mode = getattr(unreal.BlendMode, name, None)
    if mode is None:
        failures.append("no %s in this engine: falling back to translucent" % name)
        mode = unreal.BlendMode.BLEND_TRANSLUCENT
    return mode


def fresh(name):
    path = "/Game/FX/" + name
    if eal.does_asset_exist(path):
        mat = eal.load_asset(path)
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(name, "/Game/FX", unreal.Material, unreal.MaterialFactoryNew())
    return path, mat


class Graph:
    def __init__(self, mat):
        self.mat = mat
        self.y = 0

    def expr(self, cls, **props):
        self.y += 120
        e = mel.create_material_expression(self.mat, cls, -900, self.y)
        for key, value in props.items():
            e.set_editor_property(key, value)
        return e

    def scalar(self, name, value):
        return self.expr(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)

    def custom(self, code, inputs, outputs):
        ins = []
        for name, _src in inputs:
            ci = unreal.CustomInput()
            ci.set_editor_property("input_name", name)
            ins.append(ci)
        node = self.expr(unreal.MaterialExpressionCustom, code=code, output_type=F3, inputs=ins)
        outs = []
        for name, kind in outputs:
            co = unreal.CustomOutput()
            co.set_editor_property("output_name", name)
            co.set_editor_property("output_type", kind)
            outs.append(co)
        node.set_editor_property("additional_outputs", outs)
        for name, src in inputs:
            if not mel.connect_material_expressions(src, "", node, name):
                failures.append("%s: input %s" % (self.mat.get_name(), name))
        return node

    def out(self, node, pin, prop):
        if not mel.connect_material_property(node, pin, prop):
            failures.append("%s: property %s" % (self.mat.get_name(), prop))


# ---------------------------------------------------------------------------------------------------- M_FX_Flipbook
path, mat = fresh("M_FX_Flipbook")
mat.set_editor_property("blend_mode", blend("BLEND_ALPHA_COMPOSITE"))
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property("two_sided", True)
g = Graph(mat)
tex = g.expr(unreal.MaterialExpressionTextureObjectParameter, parameter_name="Tex")
if "Fireball" in textures:
    tex.set_editor_property("texture", textures["Fireball"])
uv = g.expr(unreal.MaterialExpressionTextureCoordinate)
colour = g.expr(unreal.MaterialExpressionVectorParameter, parameter_name="Color", default_value=unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
# soft where the sprite cuts into the sand or a wall (no hard line), 1.5 m
fade = g.expr(unreal.MaterialExpressionDepthFade)
fade.set_editor_property("fade_distance_default", 150.0)
FLIP_CODE = r"""
float n = max(Cols * Rows, 1.0);
float f = clamp(Frame, 0.0, n - 1.0);
float f0 = floor(f);
float f1 = min(f0 + 1.0, n - 1.0);
float k = f - f0;
float2 uv = float2(UV.x, lerp(UV.y, 1.0 - UV.y, saturate(FlipV)));
// turned clockwise on screen by Rotation round the middle (V runs down); faded out towards the picture's edges, so a
// turned picture never shows its square
float2 d = float2(uv.x - 0.5, 0.5 - uv.y);
float c = cos(Rotation);
float sn = sin(Rotation);
float2 r = float2(d.x * c - d.y * sn, d.x * sn + d.y * c);
uv = float2(0.5 + r.x, 0.5 - r.y);
float inside = smoothstep(0.0, 0.06, min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y)));
uv = saturate(uv);
float2 cell = float2(1.0 / Cols, 1.0 / Rows);
// frame 0 is the top-left cell, row by row (Scripts/make_fx_flipbooks.py)
float2 uv0 = (uv + float2(fmod(f0, Cols), floor(f0 / Cols))) * cell;
float2 uv1 = (uv + float2(fmod(f1, Cols), floor(f1 / Cols))) * cell;
float4 s = lerp(Texture2DSample(Tex, TexSampler, uv0), Texture2DSample(Tex, TexSampler, uv1), k) * inside;
float o = saturate(Opacity) * saturate(Fade);
OutOpacity = saturate(s.a * o);
return s.rgb * Color.rgb * Intensity * o;   // premultiplied: AlphaComposite adds it and darkens behind by OutOpacity
"""
node = g.custom(FLIP_CODE, [("Tex", tex), ("UV", uv), ("Frame", g.scalar("Frame", 0.0)), ("Cols", g.scalar("Cols", 8.0)),
                            ("Rows", g.scalar("Rows", 8.0)), ("Color", colour), ("Intensity", g.scalar("Intensity", 1.0)),
                            ("Opacity", g.scalar("Opacity", 1.0)), ("Rotation", g.scalar("Rotation", 0.0)), ("FlipV", g.scalar("FlipV", 0.0)),
                            ("Fade", fade)],
                [("OutOpacity", F1)])
g.out(node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
g.out(node, "OutOpacity", unreal.MaterialProperty.MP_OPACITY)
mel.recompile_material(mat)
eal.save_asset(path)

# ---------------------------------------------------------------------------------------------------- M_FX_Char
path, mat = fresh("M_FX_Char")
mat.set_editor_property("blend_mode", blend("BLEND_ALPHA_COMPOSITE"))
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
g = Graph(mat)
world = g.expr(unreal.MaterialExpressionWorldPosition)
local = g.expr(unreal.MaterialExpressionTransformPosition)
local.set_editor_property("transform_source_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
local.set_editor_property("transform_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
if not (mel.connect_material_expressions(world, "", local, "") or mel.connect_material_expressions(world, "", local, "Input")):
    failures.append("M_FX_Char: local position")
time = g.expr(unreal.MaterialExpressionTime)
CHAR_CODE = r"""
struct FEXChar
{
    float Hash(float3 p)
    {
        p = frac(p * 0.3183099 + 0.1);
        p *= 17.0;
        return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
    }
    float Value(float3 p)
    {
        float3 i = floor(p);
        float3 f = frac(p);
        f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(lerp(Hash(i), Hash(i + float3(1, 0, 0)), f.x), lerp(Hash(i + float3(0, 1, 0)), Hash(i + float3(1, 1, 0)), f.x), f.y),
                    lerp(lerp(Hash(i + float3(0, 0, 1)), Hash(i + float3(1, 0, 1)), f.x), lerp(Hash(i + float3(0, 1, 1)), Hash(i + float3(1, 1, 1)), f.x), f.y), f.z);
    }
    float Fbm(float3 p)
    {
        float s = 0.0;
        float a = 0.5;
        for (int k = 0; k < 4; ++k) { s += a * Value(p); p = p * 2.07 + 13.0; a *= 0.5; }
        return s / 0.9375;
    }
};
FEXChar S;
float3 q = L / 100.0;                                       // metres, riding with the piece as it tumbles
float soot = S.Fbm(q * 2.5);
float ridge = 1.0 - abs(S.Fbm(q * 4.0 + float3(0.0, 0.0, Time * 0.04)) * 2.0 - 1.0);
float cracks = pow(saturate((ridge - 0.8) / 0.2), 2.0);    // thin lines where the paint split
float flicker = 0.7 + 0.3 * S.Value(float3(q.xy * 3.0, Time * 2.5));
float heat = saturate(Heat);
float3 ember = float3(1.0, 0.3, 0.05) * cracks * flicker * heat * 14.0 + float3(0.5, 0.09, 0.02) * heat * heat * soot * 0.5;
OutOpacity = saturate(0.74 + 0.22 * soot);                  // the paint shows at 4-26 % under the soot
return ember;
"""
node = g.custom(CHAR_CODE, [("L", local), ("Time", time), ("Heat", g.scalar("Heat", 1.0))], [("OutOpacity", F1)])
g.out(node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
g.out(node, "OutOpacity", unreal.MaterialProperty.MP_OPACITY)
mel.recompile_material(mat)
eal.save_asset(path)

if failures:
    for f in failures:
        unreal.log_error("FXASSETS " + f)
unreal.log("FXASSETS textures %d of 3, M_FX_Flipbook, M_FX_Char, %d problems" % (len(textures), len(failures)))
