"""Fotos HD da Selva por setor, com o nome do setor e de cada vista (Docs/SELVA/HD/<setor>.jpg).
Uso (nuvem, python3 com bpy e PIL):  python3 Scripts/selva/fotos_hd.py <pasta> 7 8 9 10
Refaz cada setor em <pasta>/s<n> (sculpt_selva.py, so as 6 vistas, 1280x720) e monta a folha 3 x 2."""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
VIEWS = {
 1: ("S1_varzea", ["aerea_partida", "aerea", "piloto_F1", "piloto_reta", "salto_igarape", "salto_tronco_caido"]),
 2: ("S2_serra_vermelha", ["aerea", "gancho_ar", "aerea_partida", "piloto_gancho", "piloto_F3", "piloto_F3b"]),
 3: ("S3_salto_kaieteur", ["aerea_cascata", "aerea", "salto_laje_da_cascata", "piloto_F4", "piloto_F5", "piloto_degrau_da_descida"]),
 4: ("S4_corredeiras_congo", ["oval_ar", "aerea", "piloto_partida", "piloto_F6", "piloto_F7", "piloto_reta"]),
 5: ("S5_gruta_raizes", ["aerea", "piloto_boca_da_gruta", "piloto_gruta", "piloto_F8", "piloto_F9", "piloto_partida"]),
 6: ("S6_mangue_labirinto", ["aerea", "aerea_partida", "salto_canal", "piloto_F10", "piloto_F11", "piloto_partida"]),
 7: ("S7_tepui", ["aerea_tepui", "aerea", "piloto_partida", "piloto_rio", "piloto_F12", "piloto_F13"]),
 8: ("S8_galeria_savana", ["aerea", "piloto_partida", "piloto_reta", "piloto_F14", "piloto_F15", "salto_termiteira"]),
 9: ("S9_garganta_vitoria", ["aerea", "gancho_ar", "piloto_F16", "piloto_F17", "piloto_F17b", "piloto_F17c"]),
 10: ("S10_delta_okavango", ["aerea", "aerea_partida", "piloto_rio", "salto_canal_do_delta", "piloto_F18", "piloto_partida"]),
}
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
plan = json.load(open(os.path.join(REPO, "Scripts/selva/selva_plano.json"), encoding="utf-8"))
SEC = {i + 1: (s["name"], s["where"]) for i, s in enumerate(plan["sectors"])}
FORK = {f["name"].split()[0]: f["name"] for f in plan["forks"]}
TXT = {"aerea": "Vista aérea", "aerea_partida": "Vista aérea da partida", "piloto_partida": "Piloto: partida do setor",
       "piloto_reta": "Piloto: meio do setor", "gancho_ar": "Gancho com parede semi-oval, do ar", "piloto_gancho": "Piloto: entrada no gancho",
       "oval_ar": "Estrada oval, do ar", "aerea_cascata": "A cascata, vista da garganta", "aerea_tepui": "O tepui e a cascata",
       "piloto_rio": "Piloto: dentro do rio", "piloto_gruta": "Piloto: dentro da gruta", "piloto_boca_da_gruta": "Piloto: a boca da gruta",
       "piloto_degrau_da_descida": "Piloto: o degrau da descida", "salto_igarape": "Salto do igarapé", "salto_tronco_caido": "Salto do tronco caído",
       "salto_laje_da_cascata": "Salto da laje da cascata", "salto_canal": "Salto de um canal", "salto_termiteira": "Salto da termiteira",
       "salto_canal_do_delta": "Salto de um canal do delta"}
F_BIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
F_SM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
def label(n):
    fname, views = VIEWS[n]
    name, where = SEC[n]
    tiles = []
    for v in views:
        im = Image.open(os.path.join(BASE, "s%d" % n, "selva_S%d_%s.png" % (n, v))).convert("RGB")
        cap = TXT.get(v) or ("Piloto: " + FORK.get(v.split("_", 1)[1], v.split("_", 1)[1]) if v.startswith("piloto_F") else v)
        d = ImageDraw.Draw(im, "RGBA")
        label = "%s  ·  %s" % (name.split()[0], cap)
        w = d.textlength(label, font=F_SM)
        d.rectangle([0, im.height - 56, w + 36, im.height], fill=(8, 16, 30, 190))
        d.text((18, im.height - 48), label, font=F_SM, fill=(255, 255, 255))
        tiles.append(im)
    W, H = tiles[0].size
    sheet = Image.new("RGB", (3 * W, 2 * H + 110), (8, 16, 30))
    dd = ImageDraw.Draw(sheet)
    dd.text((30, 22), "MAPA 02 SELVA ESMERALDA  ·  %s  (%s)" % (name.upper(), where), font=F_BIG, fill=(255, 196, 64))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % 3) * W, 110 + (k // 3) * H))
    out = os.path.join(REPO, "Docs/SELVA/HD", fname + ".jpg")
    sheet.save(out, quality=88)
    print("labelled", out)


if __name__ == "__main__":
    for n in map(int, sys.argv[2:]):
        fname, views = VIEWS[n]
        out = os.path.join(BASE, "s%d" % n)
        os.makedirs(out, exist_ok=True)
        r = subprocess.run([sys.executable, os.path.join(REPO, "Scripts/selva/sculpt_selva.py"), out, "S%d" % n,
                            "only=" + ",".join(views), "size=1280x720", "samples=20"], cwd=REPO, capture_output=True, text=True)
        print("S%d: rc %d %s" % (n, r.returncode, r.stderr[-300:] if r.returncode else ""), flush=True)
        if r.returncode == 0:
            label(n)
