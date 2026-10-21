# NOMAD — padrão da categoria e modelo atual

Modelo gerado por `Scripts/build_nomad.py` (código comum em `Scripts/ship_kit.py`; regras em `Docs/NAVES_REGRAS.md`):

```
python3 Scripts/build_nomad.py <pasta>            # nomad.blend, nomad.fbx e renders de pré-visualização
python3 Scripts/build_nomad.py <pasta> --no-render
```

O resultado está em `SourceArt/TestShips/nomad.fbx` (+ `nomad.blend` e `previews/nomad_*`). Para o levar ao Unreal,
correr `Scripts/import_test_ships.py` no editor (reimporta `SM_NOMAD`).

## Referência e decisões do jogador (2026-10-21)

- Referência: um "dropship" pesado e industrial visto em cinco imagens (forma e estilo; sem marcas nem símbolos).
- **Três motores de plasma**: duas cápsulas retangulares no alto dos lados e a viga de cima a acabar num motor
  retangular grande atrás.
- As cápsulas ficam **penduradas por cima**, de braços em forma de **asa "A"** que saem da viga (perna reta à
  frente, perna inclinada para trás), **todos laranja**; à frente, um par de **asas pequenas em "A" com as duas
  pernas inclinadas** (canards), também laranja, para dar ar de estabilidade.
- **Módulo de tanques e carga** por baixo da traseira.
- **~1,7 m de altura**; pintura **branca, preta e laranja** com riscas de perigo.
- Pernas de aterragem da referência trocadas por emissores hover e patins.

## Padrão da categoria NOMAD

1. Casco comprido em caixa, facetado, com nariz rombo e blindado: grelha à frente, 4 faróis, para-choques.
2. Cabine alta à frente com janelas embutidas (para-brisas e janelas laterais).
3. Viga comprida por cima, desde trás da cabine até além da traseira, com riscas laranja e pretas no fim, motor
   retangular dentro e barbatana de tubarão por cima.
4. Duas cápsulas de motor retangulares no alto dos lados, com grelha à frente, penduradas de braços laranja em
   "A" que saem da viga; canards pequenos em "A" nos lados do nariz.
5. Módulo de carga cinzento por baixo da traseira (cintas, fechos, tanques lá dentro).
6. Estabilizadores compridos e baixos, a descer um pouco (8°).
7. Radiadores grandes à vista nos flancos e no nariz; patins metálicos ao longo do fundo.

## Medidas do modelo atual

- 7,25 m × 3,30 m × 1,67 m (z 0,22–1,89), frente em −Y, cima em +Z — o referencial do `nomad.fbx` antigo.
- ~45 000 triângulos, 15 materiais `NOMAD_*`.

## Construção (de dentro para fora)

| Camada | Objetos |
|---|---|
| Estrutura | `Frames` (6 cavernas, arcos da viga, gaiola da cabine), `Longerons`, `Crash_Bumper`, `Pod_Clamp_*`, calhas do módulo, `Stabilizer_Structure_*` |
| Sistemas | `Cockpit_Parts`, `Pilot`, `Reactor_Core` (com as linhas para os 3 motores), `Engine_Boom`, `Engine_L/R`, `Radiators`, `Hover_Emitters`, tanques (`Cargo_Fittings`) |
| Carroçaria | painéis de 12 mm com juntas de 5 mm: `Nose_*`, `Side_*`, `Chine_*`, `Belly_*`, `Deck_*`, `Hull_Rear`, `Cabin_*` (janelas embutidas), `Boom_*`, `Shark_Fin`, `Pod_Shroud_*` + `Pod_Grille_*`, `Pod_Arm_*` e `Canard_*` (asas "A"), `Cargo_Module`, peles dos estabilizadores |
| Decalques | `Decals` (NOMAD, 21, emblema da liga) |
