import unreal, os
src = unreal.Paths.project_dir() + "SourceArt/TestShips/"
tasks = []
for n in ["bastion", "nomad", "strix", "vortex", "wraith"]:
    t = unreal.AssetImportTask()
    t.filename = src + n + ".fbx"
    t.destination_path = "/Game/TestShips"
    t.destination_name = "SM_" + n.upper()
    t.automated = True
    t.save = True
    t.replace_existing = True
    opts = unreal.FbxImportUI()
    opts.import_mesh = True
    opts.import_as_skeletal = False
    opts.import_materials = True
    opts.import_textures = False
    opts.static_mesh_import_data.combine_meshes = True
    t.options = opts
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for n in ["BASTION", "NOMAD", "STRIX", "VORTEX", "WRAITH"]:
    m = unreal.EditorAssetLibrary.load_asset("/Game/TestShips/SM_" + n)
    if m:
        b = m.get_bounds()
        unreal.log("SHIPBOUNDS %s origin=%s extent=%s" % (n, b.origin, b.box_extent))
    else:
        unreal.log_error("SHIPBOUNDS %s MISSING" % n)
