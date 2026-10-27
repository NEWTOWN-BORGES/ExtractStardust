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
- A primeira versão era toda um motor, sem asas (o "contrário da VORTEX" das notas antigas). Depois de a ver, o
  jogador pediu-a **mais achatada**, **metida dentro de uma asa** e **com asas como a VORTEX**. É o modelo atual (a
  primeira versão fica no histórico do git, commit `16dacc3`).
- O corpo é uma **asa larga de cinza-ardósia**, de bordos finos, e a **carapaça amarela** blindada (cockpit e motor)
  fica encaixada no meio dela. O **motor de plasma colossal**, largo e baixo, ocupa a traseira da carapaça e sai por
  um colar grosso.
- **Asas varridas** a sair dos bordos da asa-corpo, com as **pontas dobradas para cima**; bordo de ataque laranja.
- Pintura **amarela, cinza-ardósia e laranja**. As entradas de ar laranja da referência são **tomadas de
  refrigeração** (não é um motor a jato) nos flancos da carapaça; os airbags ficam **guardados** em escotilhas
  redondas na asa, com triângulos vermelhos de aviso.

## Padrão da categoria BASTION

1. Asa-corpo larga e achatada (1,06 m de altura), mais larga atrás, de bordos finos, com a superfície da asa a subir
   devagar até à carapaça.
2. Carapaça amarela no meio, de flancos inclinados e topo plano, com o para-brisas à face na frente (flancos e
   topo, moldura e pilar ao meio); piloto reclinado.
3. Nariz pequeno com dois faróis, janela de sensores e para-choques com risca laranja.
4. Tomadas de refrigeração de aro laranja nos flancos da carapaça, com riscas de perigo à frente.
5. Quatro airbags guardados em escotilhas redondas na superfície da asa.
6. Asas varridas dos bordos, pontas dobradas para cima, emblema da liga em cima.
7. A carapaça afunila à volta do motor até ao colar (sem corte a direito), barbatana de tubarão comprida no topo.
8. Escotilha redonda no tejadilho com triângulo vermelho, pegas, luzes âmbar nos bordos.

## Medidas do modelo atual

- 6,88 m × 4,02 m × 1,06 m (z 0,22–1,29 com a barbatana), frente em −Y, cima em +Z — o referencial do `bastion.fbx`
  antigo.
- ~53 000 triângulos, 18 materiais `BASTION_*`.

## Construção (de dentro para fora)

| Camada | Objetos |
|---|---|
| Estrutura | `Frames` (8 cavernas, sem os bordos finos da asa), `Longerons`, `Crash_Bumper`, `Engine_Mounts` (escoras até à capa do motor), `Wing_Structure_*` (longarinas, nervuras, braçadeiras) |
| Sistemas | `Cockpit_Parts`, `Pilot`, `Reactor_Core` (com as linhas para o motor e as bobinas), `Engine` (câmara de plasma larga e baixa, bobinas, tubeira), `Radiators` (tomadas, grelhas e condutas), `Airbags`, `Hover_Emitters` |
| Carroçaria | painéis de 12 mm com juntas de 5 mm em três troços: `*_Top` e `*_Flank_*` (com o vidro e as tomadas), `*_Wing_*` (com as escotilhas), `*_Edge_*` e `*_Chine_*` (com as ranhuras das asas), `*_Belly`; `Nose_Front` e `Nose_Lights`, `Tail_*` (o cone à volta do motor), `Engine_Collar`, `Collar_Bulkhead`, `Canopy_Frame`, `Hull_Details`, `Shark_Fin`, peles das asas, `Wing_Fold_*` |
| Decalques | `Decals` (BASTION, 05, emblema da liga, triângulos de aviso, riscas de perigo) |

## Módulos

`build_modules` como nas outras naves: núcleo, esqueleto, asa de série e as 3 asas próprias (Longspan, Brace,
Glide), os 5 kits de carroçaria (ardósia, friso amarelo, rebordo laranja), as 3 refrigerações, as 3 caudas (por
baixo, porque o topo já tem barbatana) e os 3 utilitários dentro do nariz. No jogo, a BASTION passou a ter slot de
asas (`EXMeta.cpp`). Imagens em `previews/kit_bastion.jpg`, `previews/asas_bastion.jpg` e
`previews/utilidade_bastion.jpg`.
