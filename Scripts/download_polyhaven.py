# Downloads the Poly Haven assets the desert uses (CC0: free, commercial use, no attribution needed) into
# SourceArt/PolyHaven/<id>/: texture sets (colour, DirectX normal, ARM = ambient occlusion/roughness/metal) and
# models (FBX with their textures). Run once per PC.
# Usage: python download_polyhaven.py            (download)
#        python download_polyhaven.py --size     (only report the download size)
import json
import os
import sys
import urllib.request

TEXTURES = ["red_sand", "aerial_sand", "sandstone_cracks", "cliff_side", "dry_ground_rocks", "gravelly_sand",
            "red_laterite_soil_stones", "aerial_grass_rock", "rock_boulder_dry"]
TEXTURE_RES = "2k"
MAPS = {"Diffuse": "diff", "nor_dx": "nor_dx", "arm": "arm"}
MODELS = ["dead_tree_trunk", "tree_stump_01", "dry_branches_medium_01", "wild_rooibos_bush", "grass_medium_01",
          "namaqualand_boulder_02", "namaqualand_boulder_05"]
MODEL_RES = "1k"
# The Selva Esmeralda's forest floor (2026-11-02): for each layer of its ground material the first of these that Poly
# Haven has (tried in order; the last one is a desert texture, always there). The picks go to selva_ground.json, which
# Scripts/selva/import_selva.py reads.
SELVA = {"Sa": ["forest_leaves_02", "forest_leaves_03", "forrest_ground_01", "brown_mud_leaves_01", "aerial_grass_rock"],
         "Gr": ["brown_mud_leaves_01", "forrest_ground_01", "red_laterite_soil_stones"],
         "Gs": ["leafy_grass", "forest_ground_04", "aerial_grass_rock"]}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SourceArt", "PolyHaven")
HEADERS = {"User-Agent": "ExtractingStardust-asset-fetch"}
SIZE_ONLY = "--size" in sys.argv


def api(asset):
    return json.load(urllib.request.urlopen(urllib.request.Request("https://api.polyhaven.com/files/" + asset, headers=HEADERS)))


def fetch(url, target, size):
    if SIZE_ONLY or (os.path.exists(target) and os.path.getsize(target) == size):
        return
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS)) as src, open(target, "wb") as dst:
        dst.write(src.read())


total = 0


def texture(asset):
    """Downloads one texture set; False when Poly Haven does not have it (or a map of it)."""
    global total
    try:
        files = api(asset)
        for key, short in MAPS.items():
            info = files[key][TEXTURE_RES]["jpg"]
            fetch(info["url"], os.path.join(ROOT, asset, "%s_%s_%s.jpg" % (asset, short, TEXTURE_RES)), info["size"])
            total += info["size"]
    except Exception as error:   # an unknown id or a missing map: the caller tries the next one
        print("POLYHAVEN texture", asset, "not available:", error)
        return False
    print("POLYHAVEN texture", asset, round(total / 1e6, 1), "MB so far")
    return True


for asset in TEXTURES:
    texture(asset)
picks = {}
for slot, candidates in SELVA.items():
    picks[slot] = next((asset for asset in candidates if texture(asset)), candidates[-1])
if not SIZE_ONLY:
    os.makedirs(ROOT, exist_ok=True)
    json.dump(picks, open(os.path.join(ROOT, "selva_ground.json"), "w"), indent=1)
    print("POLYHAVEN selva ground", picks)
for asset in MODELS:
    info = api(asset)["fbx"][MODEL_RES]["fbx"]
    fetch(info["url"], os.path.join(ROOT, asset, os.path.basename(info["url"])), info["size"])
    total += info["size"]
    for rel, inc in info.get("include", {}).items():  # the model's textures, kept at their relative paths
        fetch(inc["url"], os.path.join(ROOT, asset, rel), inc["size"])
        total += inc["size"]
    print("POLYHAVEN model", asset, round(total / 1e6, 1), "MB so far")
print("POLYHAVEN %s total %.1f MB" % ("size" if SIZE_ONLY else "downloaded", total / 1e6))
