# STRIX — padrão da categoria e modelo atual

Modelo gerado por `Scripts/build_strix.py` (Blender 5.2, corre também com `pip install bpy`):

```
python3 Scripts/build_strix.py <pasta>            # strix.blend, strix.fbx e renders de pré-visualização
python3 Scripts/build_strix.py <pasta> --no-render
```

O resultado está em `SourceArt/TestShips/strix.fbx` (+ `strix.blend` e `previews/`). Para o levar ao Unreal,
correr `Scripts/import_test_ships.py` no editor (reimporta `SM_STRIX`).

## Referências e decisões do jogador (2026-10-20)

- Forma base: uma nave de corrida azul/amarela de nariz comprido (a 1.ª imagem), com o padrão confirmado em mais três
  (uma laranja vista de cima, uma vermelha/branca de lado, uma cinzenta com motor grande atrás).
- Só a carroçaria: **sem lâminas nem espetos**; à frente é mais pequena (estreita e baixa). Barbatanas só as
  de tubarão na traseira.
- **Asas a descer** da raiz para as pontas (15°).
- **Um só motor grande, ao centro, na traseira** (não dois), **de nave espacial** (plasma, não de jato).
- A traseira fecha-se num **cone semi-pontiagudo** à volta do motor, com uma **barbatana de tubarão** comprida
  na lombada (2026-10-21; ver `Docs/NAVES_REGRAS.md`).
- Decalques próprios (STRIX, número, emblema estrela-anel); nenhum logótipo das imagens de referência.
- Regras dos PDFs de naves podem ceder quando chocam com o aspeto pedido.

## Padrão da categoria STRIX

1. Nariz comprido e baixo (~55–60% do comprimento), facetado, a alargar e a subir até ao cockpit (cunha).
2. Fundo plano com a ponta levantada e uma sola preta por baixo da ponta.
3. Cockpit recuado e baixo, encaixado na lombada; piloto visível através da cobertura.
4. Atrás do cockpit a lombada sobe até ao bloco do motor (topo amarelo) e a traseira afunila num cone à volta
   do motor de plasma, com a barbatana de tubarão por cima.
5. Asas só no último terço, muito varridas, ponta cortada, a descer para os lados.
6. Superfícies planas com arestas chanfradas (chanfros superiores em azul escuro).
7. Entradas de ar com grelha nos flancos (radiadores no casco, admissão do motor na lombada).
8. Pintura: azul + amarelo + branco em blocos/faixas diagonais, barriga grafite, pequenos avisos (número, triângulos
   vermelhos, seta de resgate, riscas de perigo).

## Medidas do modelo atual

- 6,29 m × 3,00 m × 1,39 m (z 0,09–1,48 com a barbatana), frente em −Y, cima em +Z — o mesmo referencial do
  `strix.fbx` antigo.
- ~40 000 triângulos, 15 materiais `STRIX_*` (cores sem texturas).

## Construção (de dentro para fora)

| Camada | Objetos |
|---|---|
| Estrutura | `Frames` (7 cavernas), `Longerons`, carris da espinha, `Crash_Structure`, `Reactor_Cradle`, apoios do motor, braçadeiras das asas (`Wing_Structure_*`: longarinas e nervuras) |
| Sistemas | `Cockpit_Tub`, `Cockpit_Parts`, `Pilot`, `Reactor_Core`, `Reactor_Lines`, `Engine_Core` (câmara de plasma, bobinas, tubeira), `Intakes`, `Radiators`, `Hover_Emitters` (6 módulos + placa de gravidade, sensores) |
| Carroçaria | painéis de 12 mm com juntas de 5 mm: `Nose_Cap`, `Nose_Top`, `Nose_Side_*`, `Chine_*`, `Belly_*`, `Cowl_*`, `Cockpit_Side_*`, `Side_*`, `Deck_*`, `Spine_*`, `Reactor_Cover`, `Service_Hatch_*`, `Tail_Belly`/`Tail_Side_*`/`Tail_Top` (cone), `Tail_Ring`, `Dorsal_Fin`, `Canopy` + `Canopy_Frame` + `Roll_Hoop`, peles das asas |
| Decalques | `Decals` |

As asas entram por ranhuras nos painéis laterais até às braçadeiras; os emissores ficam em recortes da barriga; as
tampas (reator, serviço) são recortadas do próprio painel com folga. Os `Socket_*` marcam onde os módulos encaixam.
