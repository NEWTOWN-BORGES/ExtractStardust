"""
Carrega o rdd_route_lib REAL (o que o Blender corre) com stubs de bpy/mathutils,
para poder testar a geometria sem Blender.

Porque funciona: o bpy e o mathutils so sao usados na classe MeshOut (linha 545+);
build_ring, sculpt, erode3d e talus_profile sao numpy puro. Basta injetar modulos
falsos em sys.modules antes de carregar o ficheiro.
"""
import importlib.util
import sys
import types

import numpy as np

ART = (r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust"
       r"\ExtractStardustRDD\Art\Blender")


def stub_modules():
    """Injeta bpy e mathutils minimos, so para o import do modulo passar."""
    if "bpy" not in sys.modules:
        bpy = types.ModuleType("bpy")
        bpy.data = types.SimpleNamespace(meshes=types.SimpleNamespace(new=lambda *a, **k: None),
                                         materials=types.SimpleNamespace(get=lambda *a, **k: None,
                                                                         new=lambda *a, **k: None),
                                         objects=types.SimpleNamespace(new=lambda *a, **k: None))
        bpy.ops = types.SimpleNamespace()
        sys.modules["bpy"] = bpy
    if "mathutils" not in sys.modules:
        mu = types.ModuleType("mathutils")
        mu.kdtree = types.ModuleType("mathutils.kdtree")
        sys.modules["mathutils"] = mu
        sys.modules["mathutils.kdtree"] = mu.kdtree


def load_lib():
    stub_modules()
    if ART not in sys.path:
        sys.path.insert(0, ART)
    spec = importlib.util.spec_from_file_location("rdd_route_lib", ART + r"\rdd_route_lib.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)
    return lib


if __name__ == "__main__":
    lib = load_lib()
    print("rdd_route_lib carregado sem Blender")
    for nome in ("build_ring", "sculpt", "erode3d", "talus_profile", "wall_warp", "integrate", "MeshOut"):
        print(f"  {nome:16s} {'OK' if hasattr(lib, nome) else 'FALTA'}")
    print()
    print("a verificar se a erosao esta no sculpt carregado:")
    import inspect
    src = inspect.getsource(lib.sculpt)
    print("  erode3d chamado no sculpt:", "erode3d(" in src)
    print("  tem parametro erosion_m:", "erosion_m" in inspect.signature(lib.sculpt).parameters)
