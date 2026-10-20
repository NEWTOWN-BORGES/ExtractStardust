# Imports the generated world's pieces (sculpt_canyon_field.py, sculpt_expansion.py, sculpt_grand_circuit.py,
# export_world_unreal.py) and builds its landscape material:
#  - the rock kit (Nanite; rocks collide on their real surface, dead wood never collides);
#  - the tunnel roofs of the core and of the grand circuit (Nanite, collide);
#  - the surface map and M_World (make_desert_material.py reading the world's surface map).
# Folders come from EX_WORLD_DIR (default C:/rdd/mundo), EX_KIT_DIR (C:/rdd/kit) and EX_MAP_DIR (C:/rdd/mapa).
# Run in the editor or the commandlet; then UEXDesertBuilder::BuildWorldMap builds the map.
import glob
import json
import os

import unreal

WORLD = os.environ.get("EX_WORLD_DIR", "C:/rdd/mundo")
KIT = os.environ.get("EX_KIT_DIR", "C:/rdd/kit")
MAPDIR = os.environ.get("EX_MAP_DIR", "C:/rdd/mapa")
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
WOOD = {"SM_Kit_DeadLog", "SM_Kit_DeadSnag"}
failures = []


def import_meshes(files, destination):
    tasks = []
    for path in files:
        task = unreal.AssetImportTask()
        task.filename = path
        task.destination_path = destination
        task.destination_name = os.path.splitext(os.path.basename(path))[0]
        task.automated = True
        task.save = True
        task.replace_existing = True
        options = unreal.FbxImportUI()
        options.import_mesh = True
        options.import_as_skeletal = False
        options.import_materials = False
        options.import_textures = False
        data = options.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.generate_lightmap_u_vs = False
        data.transform_vertex_to_absolute = True  # tunnel roofs keep their place in the world
        task.options = options
        tasks.append(task)
    tools.import_asset_tasks(tasks)
    return [d + "/" + os.path.splitext(os.path.basename(p))[0] for d, p in ((destination, p) for p in files)]


def finish_meshes(paths, material, collide):
    for path in paths:
        mesh = eal.load_asset(path)
        if not mesh:
            failures.append("missing " + path)
            continue
        nanite = mesh.get_editor_property("nanite_settings")
        nanite.enabled = True
        mesh.set_editor_property("nanite_settings", nanite)
        body = mesh.get_editor_property("body_setup")
        if body:
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if collide(path)
                                     else unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        mesh.set_material(0, material(path))
        eal.save_asset(path)


wingate = eal.load_asset("/Game/Desert/MI_Wingate")
dark = eal.load_asset("/Game/Desert/MI_Rock_Dark")
kit = import_meshes(sorted(glob.glob(KIT + "/*.fbx")), "/Game/World/Kit")
finish_meshes(kit, lambda p: dark if p.rsplit("/", 1)[1] in WOOD else wingate, lambda p: p.rsplit("/", 1)[1] not in WOOD)
roofs = import_meshes(sorted(glob.glob(MAPDIR + "/tunnels/*.fbx")) + sorted(glob.glob(WORLD + "/tunnels_gc/*.fbx")), "/Game/World/Tunnels")
finish_meshes(roofs, lambda p: wingate, lambda p: True)
# Plants grown by sculpt_plants.py (desert species included): vertex colours, never collide.
PLANTS = os.environ.get("EX_PLANT_DIR", "C:/rdd/plantas")
plant_mat = eal.load_asset("/Game/Desert/M_Plant")
plants = import_meshes(sorted(glob.glob(PLANTS + "/*.fbx")), "/Game/Desert/Plants")
finish_meshes(plants, lambda p: plant_mat, lambda p: False)

# Surface map and track map: data, not colour (linear, clamped at the world edge).
for source, name in (("world_surface.png", "T_WorldSurface"), ("world_track.png", "T_WorldTrack")):
    task = unreal.AssetImportTask()
    task.filename = WORLD + "/unreal/" + source
    task.destination_path = "/Game/World"
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    tools.import_asset_tasks([task])
    data = eal.load_asset("/Game/World/" + name)
    data.set_editor_property("srgb", False)
    data.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
    data.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
    eal.save_loaded_asset(data)

scripts = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "Scripts/"
exec(open(scripts + "make_world_material.py").read(), {"__name__": "__main__"})
unreal.log("WORLDIMPORT kit %d roofs %d failures=%s" % (len(kit), len(roofs), failures))
