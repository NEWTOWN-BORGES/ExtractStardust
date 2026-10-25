"""Imports the ship modules (Docs/MODULOS.md) into the Unreal project.

SourceArt/TestShips/modules/<ship>_<piece>.fbx (written by Scripts/ship_modules.py at the end of each build_<ship>.py)
-> /Game/Ships/<SHIP>/SM_<SHIP>_<piece>: the core (the ship without wings), the stock wings, the skeleton (the x-ray view)
and every module piece. The import options are those of import_test_ships.py, so every piece lands in the same frame as
/Game/TestShips/SM_<SHIP> and AEXHoverCraft puts it on the ship mesh with no offset.

Run in the editor (Tools > Execute Python Script) or with -ExecutePythonScript=<path>/Scripts/import_ship_modules.py.
Check the MODULEBOUNDS lines in the log: the core must lie inside the whole ship's bounds.
"""
import os

import unreal

SRC = unreal.Paths.project_dir() + "SourceArt/TestShips/modules/"

tasks = []
names = []
for f in sorted(os.listdir(SRC)):
    if not f.endswith(".fbx"):
        continue
    ship, piece = f[:-4].split("_", 1)
    t = unreal.AssetImportTask()
    t.filename = SRC + f
    t.destination_path = "/Game/Ships/" + ship.upper()
    t.destination_name = "SM_%s_%s" % (ship.upper(), piece)
    t.automated = True
    t.save = True
    t.replace_existing = True
    opts = unreal.FbxImportUI()
    opts.import_mesh = True
    opts.import_as_skeletal = False
    opts.import_materials = True
    opts.import_textures = False
    opts.static_mesh_import_data.combine_meshes = True
    opts.static_mesh_import_data.auto_generate_collision = False
    t.options = opts
    tasks.append(t)
    names.append((ship.upper(), piece))
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

for ship in sorted({s for s, _ in names}):
    full = unreal.EditorAssetLibrary.load_asset("/Game/TestShips/SM_" + ship)
    core = unreal.EditorAssetLibrary.load_asset("/Game/Ships/%s/SM_%s_core" % (ship, ship))
    if not core:
        unreal.log_error("MODULEBOUNDS %s core MISSING" % ship)
        continue
    cb = core.get_bounds()
    if full:
        fb = full.get_bounds()
        unreal.log("MODULEBOUNDS %s core origin=%s extent=%s | ship origin=%s extent=%s" % (ship, cb.origin, cb.box_extent, fb.origin, fb.box_extent))
    else:
        unreal.log_warning("MODULEBOUNDS %s core origin=%s extent=%s | /Game/TestShips/SM_%s missing" % (ship, cb.origin, cb.box_extent, ship))
missing = [n for n in names if not unreal.EditorAssetLibrary.does_asset_exist("/Game/Ships/%s/SM_%s_%s" % (n[0], n[0], n[1]))]
unreal.log("MODULES imported %d of %d pieces%s" % (len(names) - len(missing), len(names), "" if not missing else " (missing: %s)" % missing))
