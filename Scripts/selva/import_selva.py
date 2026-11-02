# Imports the Selva Esmeralda into Unreal, apart from the Red Dust Divide (its own folder /Game/Selva, so the desert's
# assets stay as they are): the jungle kit (C:/rdd/selva/kit, SM_Selva_<kind>, with its painted textures; leaves cut out
# by their alpha, two-sided, no collision), the data maps of export_selva_unreal.py (T_SelvaSurface, T_SelvaTrack), the
# ground material M_Selva (make_ground_material.py over those maps) and the water M_SelvaWater. Then
# Scripts/selva/build_selva_map.py builds /Game/Maps/Selva.
#   UnrealEditor-Cmd.exe <project> -run=pythonscript -script=<project>/Scripts/selva/import_selva.py -unattended
import glob
import json
import os
import re

import unreal

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
ROOT = os.environ.get("EX_SELVA_DIR", "C:/rdd/selva")
SCRIPTS = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "Scripts/"
failures = []

# ---- 1. the jungle kit
files = sorted(glob.glob(ROOT + "/kit/*.fbx"))
tasks = []
for path in files:
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = "/Game/Selva/Kit"
    task.destination_name = os.path.splitext(os.path.basename(path))[0]
    task.automated = True
    task.save = True
    task.replace_existing = True
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = True
    options.import_textures = True
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.generate_lightmap_u_vs = False
    task.options = options
    tasks.append(task)
tools.import_asset_tasks(tasks)
for path in files:
    asset = "/Game/Selva/Kit/" + os.path.splitext(os.path.basename(path))[0]
    mesh = eal.load_asset(asset)
    if not mesh:
        failures.append("missing " + asset)
        continue
    body = mesh.get_editor_property("body_setup")
    if body:
        body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
    # Nanite: hundreds of thousands of trees (without it the race ran at 3 fps, 2026-11-02)
    nanite = mesh.get_editor_property("nanite_settings")
    nanite.enabled = True
    mesh.set_editor_property("nanite_settings", nanite)
    eal.save_asset(asset)
# The kit's materials, made here as our own assets in /Game/Selva/Mat and put on every mesh slot by its name. Unreal
# 5.8 imports the FBX materials as material instances without their textures (the trees came out white, 2026-11-02),
# so the imported ones are left aside: the leaves and fronds from their painted textures (kit/tex), cut out by the
# alpha and lit on both sides; bark, stone and the far canopies in their colours.
LEAVES = {"M_Leaf_Broad": "T_Leaf_Broad", "M_Leaf_Small": "T_Leaf_Small", "M_Frond": "T_Frond", "M_Fan": "T_Fan", "M_Cecropia": "T_Cecropia"}
COLOURS = {"M_Bark": (0.16, 0.11, 0.07), "M_Bark_Kapok": (0.34, 0.32, 0.28), "M_Bark_Palm": (0.22, 0.17, 0.12),
           "M_Bark_Cecropia": (0.55, 0.55, 0.5), "M_Stone": (0.28, 0.27, 0.25), "M_Termite": (0.36, 0.19, 0.1),
           "M_FarCanopy": (0.05, 0.16, 0.04), "M_FarKapok": (0.07, 0.19, 0.05)}


def selva_material(name):
    path = "/Game/Selva/Mat/" + name
    if eal.does_asset_exist(path):
        mat = eal.load_asset(path)
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(name, "/Game/Selva/Mat", unreal.Material, unreal.MaterialFactoryNew())
    if name in LEAVES:
        tex_file = ROOT + "/kit/tex/" + LEAVES[name] + ".png"
        task = unreal.AssetImportTask()
        task.filename = tex_file
        task.destination_path = "/Game/Selva/Mat"
        task.destination_name = LEAVES[name]
        task.automated = True
        task.save = True
        task.replace_existing = True
        tools.import_asset_tasks([task])
        tex = eal.load_asset("/Game/Selva/Mat/" + LEAVES[name])
        if not tex:
            failures.append("missing " + tex_file)
            return None
        node = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -400, 0)
        node.set_editor_property("texture", tex)
        mel.connect_material_property(node, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        mel.connect_material_property(node, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        mat.set_editor_property("two_sided", True)
    else:
        c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
        r_, g_, b_ = COLOURS[name]
        c.set_editor_property("constant", unreal.LinearColor(r_, g_, b_, 1.0))
        mel.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 250)
    rough.set_editor_property("r", 0.8)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    eal.save_asset(path)
    return mat


MATS = {}
for mat_name in list(LEAVES) + list(COLOURS):
    made = selva_material(mat_name)
    if made:
        MATS[mat_name] = made


def kit_key(text):
    """M_Leaf_Broad, MI_M_Leaf_Broad, M_Leaf_Broad.001 or Leaf_Broad -> M_Leaf_Broad."""
    text = str(text).split(".")[0]
    while text.startswith("MI_"):
        text = text[3:]
    text = re.sub(r"_\d+$", "", text)
    return text if text.startswith("M_") else "M_" + text


for path in files:
    asset = "/Game/Selva/Kit/" + os.path.splitext(os.path.basename(path))[0]
    mesh = eal.load_asset(asset)
    if not mesh:
        continue
    slots = mesh.get_editor_property("static_materials")
    fitted = 0
    for index, slot in enumerate(slots):
        current = slot.get_editor_property("material_interface")
        keys = [kit_key(slot.get_editor_property("material_slot_name"))] + ([kit_key(current.get_name())] if current else [])
        for key in keys:
            if key in MATS:
                mesh.set_material(index, MATS[key])
                fitted += 1
                break
    if fitted:
        eal.save_asset(asset)
    unreal.log("SELVAIMPORT %s: %d of %d slots with our materials" % (asset.rsplit("/", 1)[1], fitted, len(slots)))
    if fitted < len(slots):
        failures.append("%s: %d of %d slots" % (asset.rsplit("/", 1)[1], fitted, len(slots)))

# ---- 2. the data maps (linear, clamped, full size, as the desert's)
for source, name in (("world_surface.png", "T_SelvaSurface"), ("world_track.png", "T_SelvaTrack")):
    task = unreal.AssetImportTask()
    task.filename = ROOT + "/ue/unreal/" + source
    task.destination_path = "/Game/Selva"
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    tools.import_asset_tasks([task])
    tex = eal.load_asset("/Game/Selva/" + name)
    if not tex:
        failures.append("missing " + name)
        continue
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
    tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE if name == "T_SelvaTrack"
                            else unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
    tex.set_editor_property("never_stream", True)
    eal.save_loaded_asset(tex)

# ---- 3. the ground: the desert's photoreal material over the Selva's maps (forest floor, rock on the steep)
os.environ["EX_GROUND_MAT"] = "/Game/Selva/M_Selva"
os.environ["EX_GROUND_DATA"] = "/Game/Selva/T_Selva"
# The forest floor's own photos (Poly Haven, CC0; Scripts/download_polyhaven.py writes the ones it found to
# SourceArt/PolyHaven/selva_ground.json): leaf litter on the floor, mud with leaves on the road, leafy grass, and none of
# the desert's ripples and glints. Without that file, the desert's photos darkened and greened.
GROUND_PICKS = SCRIPTS[:-len("Scripts/")] + "SourceArt/PolyHaven/selva_ground.json"
if os.path.exists(GROUND_PICKS):
    picks = json.load(open(GROUND_PICKS, encoding="utf-8"))
    os.environ["EX_GROUND_PHOTOS"] = ",".join("%s=%s" % (k, v) for k, v in picks.items())
    os.environ["EX_GROUND_RIPPLES"] = "0.0"
    os.environ["EX_GROUND_TINT"] = "0.82, 0.88, 0.8"   # the shade under the canopy
    unreal.log("SELVAIMPORT ground photos %s" % os.environ["EX_GROUND_PHOTOS"])
else:
    os.environ["EX_GROUND_TINT"] = "0.45, 0.62, 0.36"   # a dark, wet forest floor
    failures.append("no " + GROUND_PICKS + " (run Scripts/download_polyhaven.py): desert photos on the Selva")
exec(open(SCRIPTS + "make_ground_material.py", encoding="utf-8").read(), {"__name__": "__main__"})

# ---- 4. the water: dark green-brown, glossy, opaque
wpath = "/Game/Selva/M_SelvaWater"
if eal.does_asset_exist(wpath):
    water = eal.load_asset(wpath)
    mel.delete_all_material_expressions(water)
else:
    water = tools.create_asset("M_SelvaWater", "/Game/Selva", unreal.Material, unreal.MaterialFactoryNew())
for value, prop in (((0.025, 0.06, 0.05), unreal.MaterialProperty.MP_BASE_COLOR),):
    c = mel.create_material_expression(water, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c.set_editor_property("constant", unreal.LinearColor(value[0], value[1], value[2], 1.0))
    mel.connect_material_property(c, "", prop)
for value, prop, y in ((0.04, unreal.MaterialProperty.MP_ROUGHNESS, 150), (0.9, unreal.MaterialProperty.MP_SPECULAR, 300)):
    c = mel.create_material_expression(water, unreal.MaterialExpressionConstant, -300, y)
    c.set_editor_property("r", value)
    mel.connect_material_property(c, "", prop)
mel.recompile_material(water)
eal.save_asset(wpath)
unreal.log("SELVAIMPORT kit %d meshes, failures=%s" % (len(files), failures))
