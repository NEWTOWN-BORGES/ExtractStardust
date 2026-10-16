"""Porta o bloco de erosao de rdd_route_lib.py para rdd_build_course.py.

Os dois ficheiros tem a mesma matematica duplicada; so o route_lib e importado pelo
pipeline, mas manter os dois alinhados evita divergencia silenciosa se um dia o
build_course for reativado.
"""
import re
import sys

P = (r"C:\Users\ADMIN\Documents\deepseek-harness\default-workspace\ExtractStardust"
     r"\ExtractStardustRDD\Art\Blender")
src_p = P + r"\rdd_route_lib.py"
dst_p = P + r"\rdd_build_course.py"

src = open(src_p, encoding="utf-8").read()
dst = open(dst_p, encoding="utf-8").read()

# 1. extrair o bloco de erosao (comentario + erode3d + talus_profile) do route_lib
m = re.search(r"\n# -+ eros\u00e3o das paredes\n.*?(?=\n\nclass CanyonLine:|\ndef wall_warp\(|\Z)",
              src, re.S)
if not m:
    print("NAO encontrei o bloco de erosao no route_lib")
    sys.exit(1)
bloco = m.group(0)
print("bloco extraido:", len(bloco), "bytes")

if "def erode3d(" in dst:
    print("build_course ja tem erode3d; a saltar insercao")
else:
    alvo = re.search(r"\ndef sculpt\(", dst)
    if not alvo:
        print("NAO encontrei def sculpt no build_course")
        sys.exit(1)
    dst = dst[:alvo.start()] + "\n" + bloco.lstrip("\n") + "\n" + dst[alvo.start():]
    print("bloco inserido")

# 2. assinatura de sculpt com os parametros de erosao
old = "def sculpt(rows, P, R, U, loc, ride, col, joints, seed, floor_cls=None, floor_mask=None):"
new = ("def sculpt(rows, P, R, U, loc, ride, col, joints, seed, floor_cls=None, floor_mask=None,\n"
       "           erosion_m=26.0, erosion_seed=7.0):")
if old in dst:
    dst = dst.replace(old, new, 1)
    print("assinatura de sculpt atualizada")
else:
    print("AVISO: assinatura de sculpt nao encontrada")

# 3. aplicar a erosao no corpo de sculpt
alvo_disp = "    disp += rock * (1.15 * relief - 1.6 * jr + 0.45 * rough)"
if alvo_disp in dst and "erode3d(" not in dst.split("def sculpt")[1].split("return")[0]:
    novo_disp = (
        "    if erosion_m > 0.0:\n"
        "        wall_u = np.clip((y - y.min()) / max(1.0, float(y.max() - y.min())), 0.0, 1.0)\n"
        "        erosion = erode3d(y, dist, wall_u, hard, amount=erosion_m, seed=erosion_seed)\n"
        "    else:\n"
        "        erosion = 0.0\n"
        "    disp += rock * (1.15 * relief - 1.6 * jr + 0.45 * rough + erosion)")
    dst = dst.replace(alvo_disp, novo_disp, 1)
    print("erosao aplicada em sculpt")
else:
    print("AVISO: nao apliquei a erosao em sculpt (linha alvo nao encontrada ou ja aplicada)")

open(dst_p, "w", encoding="utf-8").write(dst)
print("escrito:", dst_p)
