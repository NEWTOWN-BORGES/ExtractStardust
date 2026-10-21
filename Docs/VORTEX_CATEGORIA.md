# VORTEX — padrão da categoria e modelo atual

Modelo gerado por `Scripts/build_vortex.py` (código comum em `Scripts/ship_kit.py`; regras em `Docs/NAVES_REGRAS.md`):

```
python3 Scripts/build_vortex.py <pasta>            # vortex.blend, vortex.fbx e renders de pré-visualização
python3 Scripts/build_vortex.py <pasta> --no-render
```

O resultado está em `SourceArt/TestShips/vortex.fbx` (+ `vortex.blend` e `previews/vortex_*`). Para o levar ao
Unreal, correr `Scripts/import_test_ships.py` no editor (reimporta `SM_VORTEX`).

## Referência e decisões do jogador (2026-10-21)

- Pequena e rápida; gasta muito combustível e aquece (as características de jogo fazem-se depois).
- Referência: um caça em delta vermelho e branco visto em duas imagens (forma e estilo; sem armas nem marcas).
- O corpo é o cockpit dentro de uma asa em ponta, em "A" (delta), com o vidro embutido na aresta do topo.
- **Um só motor grande** atrás, **dentro da estrutura do corpo em asa**: a caixa à parte não combinava, por isso a
  traseira desce depois do cockpit e estreita à volta do motor. O motor é largo e deitado (trapézio de cantos
  arredondados, a seguir as facetas, regra dos motores "conforme caber no chassi") e sai por um colar escuro no fim.
- **Asas grandes** para as curvas, com as **pontas dobradas para cima**.
- Pintura **vermelho-laranja e branco** (bordos brancos), asas brancas, motor cinza escuro.

## Padrão da categoria VORTEX

1. Corpo em delta comprido e pontiagudo, bordos finos, facetas a subir até uma aresta central.
2. Cockpit embutido na aresta (vidro à face), piloto muito reclinado.
3. Motor grande dentro da cauda do corpo: a aresta desce atrás do cockpit e a cauda estreita até ao bocal (colar
   escuro com lábio, sem corte a direito).
4. Asas grandes e varridas a sair dos lados da traseira, pontas dobradas para cima.
5. Grelhas de calor nas facetas atrás do cockpit; emissores hover redondos por baixo.

## Medidas do modelo atual

- 5,83 m × 3,32 m × 0,69 m (z 0,26–0,96), frente em −Y, cima em +Z — o referencial do `vortex.fbx` antigo.
- ~36 000 triângulos, 14 materiais `VORTEX_*`.

## Construção (de dentro para fora)

| Camada | Objetos |
|---|---|
| Estrutura | `Frames` (6 cavernas em trapézio), `Longerons`, `Engine_Mounts` (2 cavernas em anel na cauda), `Wing_Structure_*` (longarinas, nervuras, braçadeiras) |
| Sistemas | `Cockpit_Parts`, `Pilot`, `Reactor_Core` (com a linha para o motor), `Engine` (câmara de plasma, bobinas, tubeira), `Radiators`, `Hover_Emitters` (redondos) |
| Carroçaria | painéis de 12 mm com juntas de 5 mm: `Nose_Cap`, `Body_Top` (com o vidro), `Body_Facet_*`, `Body_Edge_*`, `Body_Chine_*`, `Body_Belly`, `Tail_*` (os mesmos painéis na cauda), `Tail_Collar` (à volta do bocal), `Canopy_Frame`, peles das asas, `Wing_Fold_*` (pontas dobradas) |
| Decalques | `Decals` (11, VORTEX, emblema da liga) |
