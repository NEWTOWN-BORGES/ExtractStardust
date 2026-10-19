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
for asset in TEXTURES:
    files = api(asset)
    for key, short in MAPS.items():
        info = files[key][TEXTURE_RES]["jpg"]
        fetch(info["url"], os.path.join(ROOT, asset, "%s_%s_%s.jpg" % (asset, short, TEXTURE_RES)), info["size"])
        total += info["size"]
    print("POLYHAVEN texture", asset, round(total / 1e6, 1), "MB so far")
for asset in MODELS:
    info = api(asset)["fbx"][MODEL_RES]["fbx"]
    fetch(info["url"], os.path.join(ROOT, asset, os.path.basename(info["url"])), info["size"])
    total += info["size"]
    for rel, inc in info.get("include", {}).items():  # the model's textures, kept at their relative paths
        fetch(inc["url"], os.path.join(ROOT, asset, rel), inc["size"])
        total += inc["size"]
    print("POLYHAVEN model", asset, round(total / 1e6, 1), "MB so far")
print("POLYHAVEN %s total %.1f MB" % ("size" if SIZE_ONLY else "downloaded", total / 1e6))
