"""Regista limites locais dos meshes importados para planear a montagem das pistas."""
import os
import unreal


PROJECT_ROOT = unreal.Paths.project_dir()
COURSE_FOLDERS = (
    ("RedDustDivide", "/Game/Stardust/Courses/RedDustDivide"),
    ("Sandbox", "/Game/Stardust/Courses/Sandbox"),
)
OUTPUT = os.path.join(PROJECT_ROOT, "Docs", "AUDITORIA_LIMITES_MALHAS.txt")
LINES = ["Auditoria de limites locais de StaticMesh no Unreal Engine 5.8", ""]
TOTAL = 0
FAILURES = 0

for course_name, folder in COURSE_FOLDERS:
    asset_paths = sorted(unreal.EditorAssetLibrary.list_assets(folder, recursive=False, include_folder=False))
    LINES.append("CURSO | {} | assets={} ".format(course_name, len(asset_paths)))
    for asset_path in asset_paths:
        mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not isinstance(mesh, unreal.StaticMesh):
            continue
        try:
            bounds = mesh.get_bounds()
            origin = bounds.origin
            extent = bounds.box_extent
            minimum = (origin.x - extent.x, origin.y - extent.y, origin.z - extent.z)
            maximum = (origin.x + extent.x, origin.y + extent.y, origin.z + extent.z)
            LINES.append(
                "OK | {} | centro=({:.2f},{:.2f},{:.2f}) | extensao=({:.2f},{:.2f},{:.2f}) | min=({:.2f},{:.2f},{:.2f}) | max=({:.2f},{:.2f},{:.2f})".format(
                    mesh.get_name(), origin.x, origin.y, origin.z,
                    extent.x, extent.y, extent.z,
                    minimum[0], minimum[1], minimum[2],
                    maximum[0], maximum[1], maximum[2],
                )
            )
            TOTAL += 1
        except Exception as exc:
            LINES.append("FALHOU | {} | {}".format(asset_path, exc))
            FAILURES += 1

LINES.append("")
LINES.append("VALIDACAO | meshes lidos={} | falhas={}".format(TOTAL, FAILURES))
with open(OUTPUT, "w", encoding="utf-8") as output_file:
    output_file.write("\n".join(LINES) + "\n")
unreal.log("Extract Stardust: auditoria de meshes concluida: {} meshes, {} falhas. {}".format(TOTAL, FAILURES, OUTPUT))
