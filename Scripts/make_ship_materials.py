# Photoreal ships (player, 2026-10-26: "até nas naves tem de ter texturas", "fotorrealista tipo Call of Duty";
# Docs/PLANO_TEXTURAS.md sec. 5). One master material, /Game/Ships/M_ShipPBR (default lit; the clear coat is folded into
# the roughness, as the Python API does not expose the clear-coat pins), whose surface detail
# is computed on the ship's own coordinates (it rides with the ship, needs no UVs) by kind of finish:
#   0 paint     colour under a clear coat with a little orange peel; fine scratches through to bare metal where stones
#               hit (front and underside); red desert dust settled on the upward faces and sprayed on the underside
#   1 metal     brushed along the ship, roughness streaks
#   2 carbon    twill-woven carbon fibre under a clear coat (Graphite)
#   3 matte     rubber, fabric, ceramic: rough, dusty
#   5 emissive  the lights and glows (the colour times its strength)
# Each ship's material slots (the build scripts' material() calls: colour, metal, rough, coat, emit) become instances
# /Game/Ships/<SHIP>/MI_<SHIP>_<slot> set on every mesh of that ship (the ship, its core, skeleton and module pieces).
# Glass keeps its own translucent material; the Reactor_Glow / Utility_Glow slots are replaced at run time anyway.
# Run after the ships and their modules are imported (casa_tudo.ps1 step 3e).
import os
import re

import unreal

mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
SCRIPTS = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "Scripts/"
SHIPS = ["BASTION", "NOMAD", "STRIX", "VORTEX", "WRAITH"]
failures = []

# ---------------------------------------------------------------------------------------------------- the master
path = "/Game/Ships/M_ShipPBR"
if eal.does_asset_exist(path):
    mat = eal.load_asset(path)
    mel.delete_all_material_expressions(mat)
else:
    mat = tools.create_asset("M_ShipPBR", "/Game/Ships", unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property("tangent_space_normal", False)
y_cursor = [0]


def expr(cls, **props):
    y_cursor[0] += 120
    e = mel.create_material_expression(mat, cls, -1100, y_cursor[0])
    for key, value in props.items():
        e.set_editor_property(key, value)
    return e


def scalar(name, value):
    return expr(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)


F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
world = expr(unreal.MaterialExpressionWorldPosition)
local = expr(unreal.MaterialExpressionTransformPosition)
local.set_editor_property("transform_source_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
local.set_editor_property("transform_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
# A single-input node: its pin has no name (or "Input" in some versions).
if not (mel.connect_material_expressions(world, "", local, "") or mel.connect_material_expressions(world, "", local, "Input")):
    failures.append("local position")
normal_ws = expr(unreal.MaterialExpressionVertexNormalWS)
camera = expr(unreal.MaterialExpressionCameraPositionWS)
colour = expr(unreal.MaterialExpressionVectorParameter, parameter_name="Colour", default_value=unreal.LinearColor(0.5, 0.5, 0.5, 1.0))
inputs = [("L", local), ("N", normal_ws), ("P", world), ("C", camera), ("Col", colour), ("Metal", scalar("Metallic", 0.0)),
          ("Rgh", scalar("Roughness", 0.45)), ("Coat", scalar("Coat", 0.0)), ("Kind", scalar("Kind", 0.0)), ("Emit", scalar("Emit", 0.0))]

CODE = r"""
struct FEXShip
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
FEXShip S;
float3 q = L / 100.0;                                  // metres, on the ship
float dist = length(P - C) / 100.0;
float nearF = saturate(1.0 - dist / 25.0);
int kind = (int)round(Kind);
float3 base = Col;
float metal = Metal;
float rough = Rgh;
float coat = Coat;
float coatRough = 0.06;
float3 n = N;
float3 emissive = 0;

// Red desert dust: settled on the faces that look up, sprayed on the underside, in patches.
float upF = saturate((N.z - 0.35) / 0.5);
float underF = saturate((-N.z - 0.2) / 0.6);
float patches = S.Fbm(q * 2.3);
float dust = saturate((upF * 0.55 + underF * 0.75) * (patches * 1.4 - 0.25)) * (kind == 5 ? 0.0 : 1.0);

if (kind == 0)
{
    // Paint: orange peel under the coat, and scratches through to bare metal where stones hit (front, underside).
    float peel = S.Value(q * 140.0) - 0.5;
    n = normalize(N + float3(peel, -peel, peel) * 0.02 * nearF);
    float exposure = saturate(underF + saturate(-q.x * 0.4 + 0.2) * 0.3 + 0.15);
    float3 sp = q * float3(9.0, 9.0, 9.0);
    float cell = S.Hash(floor(sp));
    float line_ = abs(frac(dot(frac(sp), normalize(float3(cell, 1.0 - cell, 0.5))) * 6.0) - 0.5);
    float scratch = step(line_, 0.035) * step(0.55, S.Value(q * 3.1)) * exposure * nearF;
    base = lerp(base, float3(0.55, 0.56, 0.58), scratch);
    metal = lerp(metal, 1.0, scratch);
    rough = lerp(rough, 0.35, scratch);
    coat = coat * (1.0 - scratch);
    // A faint fade and grime in the paint itself.
    base *= 0.94 + 0.08 * S.Fbm(q * 0.9);
}
else if (kind == 1)
{
    // Brushed metal: fine streaks along the ship.
    float streak = S.Value(float3(q.x * 2.0, q.y * 260.0, q.z * 260.0));
    rough = saturate(rough + (streak - 0.5) * 0.18);
    base *= 0.92 + 0.12 * streak;
}
else if (kind == 2)
{
    // Twill carbon fibre (6 mm tows) under a glossy coat; far away it settles to its average.
    float3 w = pow(abs(N), 4.0);
    w /= dot(w, float3(1, 1, 1));
    float2 uv = w.z > max(w.x, w.y) ? q.xy : (w.x > w.y ? q.yz : q.xz);
    float2 t = uv / 0.006;
    float twill = frac((floor(t.x) + floor(t.y)) / 4.0) < 0.5 ? 1.0 : 0.0;
    float along = twill > 0.5 ? frac(t.x) : frac(t.y);
    float sheen = 0.75 + 0.25 * sin(along * 3.14159);
    float weave = lerp(0.82, lerp(0.7, 1.15, twill) * sheen, saturate(1.0 - dist / 6.0));
    base = Col * weave;
    coat = max(coat, 0.9);
    coatRough = 0.04;
    rough = 0.35;
}
else if (kind == 3)
{
    // Rubber, fabric, ceramic: matte, a little uneven.
    base *= 0.9 + 0.15 * S.Fbm(q * 4.0);
    rough = saturate(rough + 0.05);
}
else
{
    // The lights and glows.
    emissive = Col * Emit;
    base = Col * 0.2;
    rough = 0.3;
}
float3 dustCol = float3(0.40, 0.17, 0.075) * (0.85 + 0.3 * S.Value(q * 30.0));
base = lerp(base, dustCol, dust * 0.8);
metal = lerp(metal, 0.0, dust);
rough = lerp(rough, 0.95, dust);
coat = coat * (1.0 - dust);
OutMetal = metal;
OutRough = saturate(lerp(rough, coatRough + 0.1, coat * 0.7));   // a coated paint is glossy
OutCoat = saturate(coat);
OutCoatRough = coatRough;
OutNormal = n;
OutEmissive = emissive;
return base;
"""
custom_inputs = []
for name, _src in inputs:
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", name)
    custom_inputs.append(ci)
node = expr(unreal.MaterialExpressionCustom, code=CODE, output_type=F3, inputs=custom_inputs)
outs = []
for name, kind in (("OutMetal", F1), ("OutRough", F1), ("OutCoat", F1), ("OutCoatRough", F1), ("OutNormal", F3), ("OutEmissive", F3)):
    co = unreal.CustomOutput()
    co.set_editor_property("output_name", name)
    co.set_editor_property("output_type", kind)
    outs.append(co)
node.set_editor_property("additional_outputs", outs)
for name, src in inputs:
    if not mel.connect_material_expressions(src, "", node, name):
        failures.append("input " + name)
for out, prop in (("", unreal.MaterialProperty.MP_BASE_COLOR), ("OutMetal", unreal.MaterialProperty.MP_METALLIC),
                  ("OutRough", unreal.MaterialProperty.MP_ROUGHNESS), ("OutNormal", unreal.MaterialProperty.MP_NORMAL),
                  ("OutEmissive", unreal.MaterialProperty.MP_EMISSIVE_COLOR)):
    if not mel.connect_material_property(node, out, prop):
        failures.append("property %s" % prop)
mel.recompile_material(mat)
eal.save_asset(path)

# ---------------------------------------------------------------------------------------------------- the slots
CALL = re.compile(r'(?:material|ensure_mat)\(\s*"(\w+)"\s*,\s*"#([0-9A-Fa-f]{6})"([^)]*)\)')


def lin(hex6):
    c = [int(hex6[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def kwarg(text, name, default):
    m = re.search(r"\b%s\s*=\s*([0-9.]+)" % name, text)
    return float(m.group(1)) if m else default


def slot_defs(ship):
    """name -> (colour, metal, rough, coat, emit) from the ship's build script and the shared module script."""
    defs = {}
    for script in ("ship_modules.py", "build_%s.py" % ship.lower()):
        try:
            text = open(SCRIPTS + script, encoding="utf-8").read()
        except OSError:
            continue
        for m in CALL.finditer(text):
            defs[m.group(1)] = (lin(m.group(2)), kwarg(m.group(3), "metal", 0.0), kwarg(m.group(3), "rough", 0.45),
                                kwarg(m.group(3), "coat", 0.0), kwarg(m.group(3), "emit", 0.0))
    return defs


def kind_of(name, metal, emit):
    if emit > 0.0 or "Emit" in name or "Glow" in name:
        return 5
    if name.startswith("Graphite") or "Carbon" in name:
        return 2
    if metal > 0.5 or name.startswith("Metal") or name in ("Gold", "Chrome"):
        return 1
    if name.startswith("Paint"):
        return 0
    return 3


changed = 0
for ship in SHIPS:
    defs = slot_defs(ship)
    folder = "/Game/Ships/%s" % ship
    meshes = ["/Game/TestShips/SM_%s" % ship] + [p.split(".")[0] for p in eal.list_assets(folder, recursive=False, include_folder=False)
                                                 if p.split("/")[-1].startswith("SM_")]
    made = {}
    for mesh_path in meshes:
        mesh = eal.load_asset(mesh_path)
        if not isinstance(mesh, unreal.StaticMesh):
            continue
        slots = mesh.get_editor_property("static_materials")
        dirty = False
        for index, slot in enumerate(slots):
            slot_name = str(slot.get_editor_property("material_slot_name"))
            old = slot.get_editor_property("material_interface")
            key = (old.get_name() if old else slot_name)
            key = key[len(ship) + 1:] if key.upper().startswith(ship + "_") else key
            key = key[3 + len(ship) + 1:] if key.startswith("MI_") else key
            if key not in defs or key == "Glass" or "Glow" in key:
                continue
            if key not in made:
                colour_, metal_, rough_, coat_, emit_ = defs[key]
                mi_path = "%s/MI_%s_%s" % (folder, ship, key)
                mi = eal.load_asset(mi_path) if eal.does_asset_exist(mi_path) else \
                    tools.create_asset("MI_%s_%s" % (ship, key), folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
                mel.set_material_instance_parent(mi, mat)
                mel.set_material_instance_vector_parameter_value(mi, "Colour", unreal.LinearColor(colour_[0], colour_[1], colour_[2], 1.0))
                mel.set_material_instance_scalar_parameter_value(mi, "Metallic", metal_)
                mel.set_material_instance_scalar_parameter_value(mi, "Roughness", rough_)
                mel.set_material_instance_scalar_parameter_value(mi, "Coat", coat_ if coat_ > 0 else (0.6 if key.startswith("Paint") else 0.0))
                mel.set_material_instance_scalar_parameter_value(mi, "Kind", float(kind_of(key, metal_, emit_)))
                mel.set_material_instance_scalar_parameter_value(mi, "Emit", emit_)
                eal.save_asset(mi_path)
                made[key] = mi
            mesh.set_material(index, made[key])
            dirty = True
        if dirty:
            eal.save_asset(mesh_path)
            changed += 1
    unreal.log("SHIPMAT %s: %d slot materials, %d definitions" % (ship, len(made), len(defs)))
unreal.log("SHIPMAT done: %d meshes, failures=%s" % (changed, failures))
