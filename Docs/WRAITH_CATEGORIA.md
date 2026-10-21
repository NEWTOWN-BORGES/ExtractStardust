# WRAITH — padrão da categoria e modelo atual

Modelo gerado por `Scripts/build_wraith.py` (o código comum às naves está em `Scripts/ship_kit.py`):

```
python3 Scripts/build_wraith.py <pasta>            # wraith.blend, wraith.fbx e renders de pré-visualização
python3 Scripts/build_wraith.py <pasta> --no-render
```

O resultado está em `SourceArt/TestShips/wraith.fbx` (+ `wraith.blend` e `previews/wraith_*`). Para o levar ao
Unreal, correr `Scripts/import_test_ships.py` no editor (reimporta `SM_WRAITH`).

## Referências e decisões do jogador (2026-10-21)

- Seis imagens de naves em forquilha. A forma mistura a 1 (traseira com dois motores e asas a descer), a 2 (braços
  grossos e cápsula do cockpit elevada) e a 6 (braços robustos com grelhas laterais).
- **Dois motores atrás**, alimentados por entradas de ar nas pontas dos braços.
- Pintura **cinza-azulado com laranja**, decalques próprios (WRAITH, 13, emblema da liga).
- Sem lâminas, espetos nem barbatanas soltas: as "lâminas" do PDF são os próprios braços.

## Padrão da categoria WRAITH

1. Planta em forquilha (U): dois braços compridos e baixos para a frente, espaço vazio entre eles.
2. Braços facetados, a afinar para a frente; boca de admissão na ponta, com grelha.
3. Cápsula do cockpit estreita e elevada ao centro, na base do U, com cobertura comprida.
4. Traseira compacta e mais alta, com os motores atrás.
5. Asas curtas na traseira, a descer (20°).
6. Estrutura à vista na forquilha: viga entre os braços e escoras que seguram a cápsula.
7. Pintura clara com arestas laranja, faixa dupla amarela nos braços, número grande.

## Medidas do modelo atual

- 6,43 m × 2,40 m × 0,90 m (z 0,23–1,13), frente em −Y, cima em +Z — o referencial do `wraith.fbx` antigo.
- ~38 000 triângulos, 16 materiais `WRAITH_*`.

## Construção (de dentro para fora)

| Camada | Objetos |
|---|---|
| Estrutura | `Frames` (4 cavernas por braço, 3 na ponte, 2 na cápsula), `Longerons`, `Fork_Structure` (viga e escoras), braçadeiras das asas (`Wing_Structure_*`) |
| Sistemas | `Cockpit_Parts`, `Pilot`, `Reactor_Core` (com as linhas para os motores), `Engine_L/R`, `Intake_Ducts` + `Intakes`, `Radiators`, `Hover_Emitters` |
| Carroçaria | painéis de 12 mm com juntas de 5 mm: `Arm_*`, `Body_*`, `Deck_*`, `Bridge_Front`, `Tail_Cap`, `Pod_*`, `Spine_*`, `Reactor_Cover`, `Canopy` + `Canopy_Frame` + `Roll_Hoop`, peles das asas |
| Decalques | `Decals` |
