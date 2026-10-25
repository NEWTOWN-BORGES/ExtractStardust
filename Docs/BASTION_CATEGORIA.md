# BASTION — padrão da categoria e modelo atual

Modelo gerado por `Scripts/build_bastion.py` (código comum em `Scripts/ship_kit.py`; regras em `Docs/NAVES_REGRAS.md`):

```
python3 Scripts/build_bastion.py <pasta>            # bastion.blend, bastion.fbx e renders de pré-visualização
python3 Scripts/build_bastion.py <pasta> --no-render
```

O resultado está em `SourceArt/TestShips/bastion.fbx` (+ `bastion.blend`, `previews/bastion_*` e as peças em
`modules/bastion_*`). Para o levar ao Unreal, correr `Scripts/import_test_ships.py` (reimporta `SM_BASTION`) e
`Scripts/import_ship_modules.py` no editor.

## Referência e decisões do jogador (2026-10-25)

- Referência: uma nave pesada e blindada, amarela e cinza-escura, vista de quatro lados, com **airbags de impacto**
  (forma e estilo; sem marcas nem logótipos).
- É o **contrário da VORTEX**: a VORTEX é toda uma asa; a BASTION é **toda um motor**. O corpo é a capa de um único
  motor de plasma colossal, retangular de cantos arredondados, que ocupa a traseira e sai por um colar grosso.
- **Sem asas** (não tem slot de asas, `Docs/MODULOS.md` secção 1).
- Carapaça **amarela** blindada por cima, corpo **cinza-ardósia** por baixo, **laranja** nos aros das tomadas.
- Os airbags da referência ficam **guardados** em caixas redondas nos cantos de baixo, com triângulos vermelhos de
  aviso; as entradas de ar laranja passam a **tomadas de refrigeração** do motor (não é um motor a jato).

## Padrão da categoria BASTION

1. Corpo largo e facetado, mais largo atrás: carapaça amarela (ombro, faceta alta e topo) sobre o corpo de ardósia
   (chanfro de baixo e parede lateral).
2. Nariz rombo e blindado: face de duas cores com dois faróis, janela de sensores e para-choques com risca laranja;
   capô baixo antes do para-brisas.
3. Para-brisas à face na frente da carapaça (facetas altas e topo), com moldura e um pilar ao meio; piloto sentado
   baixo.
4. Cápsulas laterais ao longo da traseira, com tomada de refrigeração de aro laranja à frente, grelha lateral de aro
   laranja e riscas de perigo; afunilam para a cauda.
5. Quatro airbags guardados: os da frente nas paredes do corpo, os de trás nas cápsulas.
6. O corpo afunila à volta do motor até ao colar (sem corte a direito), barbatana de tubarão comprida no dorso.
7. Escotilha redonda no tejadilho com triângulo vermelho, pegas, luzes âmbar nos flancos.

## Medidas do modelo atual

- 7,01 m × 3,41 m × 1,53 m (z 0,21–1,73), frente em −Y, cima em +Z — o referencial do `bastion.fbx` antigo.
- ~52 000 triângulos, 18 materiais `BASTION_*`.

## Construção (de dentro para fora)

| Camada | Objetos |
|---|---|
| Estrutura | `Frames` (8 cavernas), `Longerons`, `Crash_Bumper` (para-choques e caixas de impacto), `Engine_Mounts` (escoras até à capa do motor) |
| Sistemas | `Cockpit_Parts`, `Pilot`, `Reactor_Core` (com as linhas para o motor e as bobinas), `Engine` (câmara de plasma colossal, bobinas, tubeira), `Radiators` (tomadas, grelhas e condutas), `Airbags`, `Hover_Emitters` |
| Carroçaria | painéis de 12 mm com juntas de 5 mm em três troços: `*_Top` e `*_Upper_*` (com o vidro), `*_Shoulder_*`, `*_Side_*`, `*_Chine_*`, `*_Belly`; `Nose_Front` e `Nose_Lights`, `Side_Pods`, `Tail_*` (o cone à volta do motor), `Engine_Collar`, `Collar_Bulkhead`, `Canopy_Frame`, `Hull_Details`, `Shark_Fin` |
| Decalques | `Decals` (BASTION, 05, emblema da liga, triângulos de aviso, riscas de perigo) |

## Módulos

`build_modules` sem asas: núcleo, esqueleto, os 5 kits de carroçaria (ardósia, friso amarelo, rebordo laranja), as 3
refrigerações, as 3 caudas (por baixo, porque o dorso já tem barbatana) e os 3 utilitários dentro do nariz. Imagens
em `previews/kit_bastion.jpg` e `previews/utilidade_bastion.jpg`.
