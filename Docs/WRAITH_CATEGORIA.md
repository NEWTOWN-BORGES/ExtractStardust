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
- **Dois motores atrás, de nave espacial** (plasma); as bocas nas pontas dos braços levam ar às bobinas.
- Correções de 2026-10-21: cobertura do cockpit **embutida** no corpo (sem bolha), cockpit **quase ao nível dos
  braços** (braços mais altos, piloto mais baixo), traseira **afunilada** com remate semi-pontiagudo entre os
  motores e **duas barbatanas de tubarão** compridas (ver `Docs/NAVES_REGRAS.md`).
- Pintura **cinza-azulado com laranja**, decalques próprios (WRAITH, 13, emblema da liga).
- Sem lâminas nem espetos (as "lâminas" do PDF são os próprios braços); barbatanas só as de tubarão na traseira.

## Padrão da categoria WRAITH

1. Planta em forquilha (U): dois braços compridos e baixos para a frente, espaço vazio entre eles.
2. Braços facetados e altos (topo quase ao nível do cockpit), a afinar para a frente; boca na ponta, com grelha.
3. Cápsula do cockpit estreita ao centro, na base do U, com o vidro embutido no topo e o piloto sentado baixo.
4. Traseira que afunila entre os dois motores de plasma até um remate semi-pontiagudo; barbatanas de tubarão
   por cima dos motores.
5. Asas curtas na traseira, a descer (20°).
6. Estrutura à vista na forquilha: viga entre os braços e escoras que seguram a cápsula.
7. Pintura clara com arestas laranja, faixa dupla amarela nos braços, número grande.

## Medidas do modelo atual

- 6,28 m × 2,40 m × 0,80 m (z 0,23–1,03), frente em −Y, cima em +Z — o referencial do `wraith.fbx` antigo.
- ~38 000 triângulos, 17 materiais `WRAITH_*`.

## Construção (de dentro para fora)

| Camada | Objetos |
|---|---|
| Estrutura | `Frames` (4 cavernas por braço, 3 na ponte, 2 na cápsula), `Longerons`, `Fork_Structure` (viga e escoras), braçadeiras das asas (`Wing_Structure_*`) |
| Sistemas | `Cockpit_Parts`, `Pilot`, `Reactor_Core` (com as linhas para os motores), `Engine_L/R` (câmara de plasma, bobinas, tubeira), `Intake_Ducts` + `Intakes`, `Radiators`, `Hover_Emitters` |
| Carroçaria | painéis de 12 mm com juntas de 5 mm: `Arm_*`, `Body_*`, `Deck_*`, `Bridge_Front`, `Tail_Cap`, `Tail_Fairing`, `Shark_Fins`, `Pod_*`, `Spine_*`, `Reactor_Cover`, `Canopy` (embutido) + `Canopy_Frame` + `Roll_Hoop`, peles das asas |
| Decalques | `Decals` |
