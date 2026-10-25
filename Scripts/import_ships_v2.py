import unreal, os

source_dir = os.path.join(unreal.Paths.project_dir(), "SourceArt", "ShipsV2")
destination = "/Game/ShipsV2"
ships = ["STRIX", "NOMAD", "VORTEX", "WRAITH"]
tasks = []

for name in ships:
    source = os.path.join(source_dir, name + "_V2.fbx")
    asset_path = destination + "/SM_V2_" + name
    if not os.path.isfile(source):
        raise RuntimeError("Missing V2 FBX: " + source)
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        unreal.log("SHIPV2 already imported; preserving asset: " + asset_path)
        continue
    task = unreal.AssetImportTask()
    task.filename = source
    task.destination_path = destination
    task.destination_name = "SM_V2_" + name
    task.automated = True
    task.save = True
    task.replace_existing = False
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = True
    options.import_textures = False
    options.static_mesh_import_data.combine_meshes = True
    task.options = options
    tasks.append(task)

if tasks:
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

for name in ships:
    asset_path = destination + "/SM_V2_" + name
    mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not mesh:
        raise RuntimeError("Imported static mesh missing: " + asset_path)
    bounds = mesh.get_bounds()
    materials = []
    for slot in mesh.get_editor_property("static_materials"):
        material = slot.get_editor_property("material_interface")
        slot_name = slot.get_editor_property("material_slot_name")
        materials.append("%s=%s" % (slot_name, material.get_name() if material else "<empty>"))
    if not materials:
        raise RuntimeError("No imported material slots found: " + asset_path)
    unreal.log("SHIPV2 %s origin=%s extent=%s material_slots=%d materials=%s" %
               (name, bounds.origin, bounds.box_extent, len(materials), materials))
