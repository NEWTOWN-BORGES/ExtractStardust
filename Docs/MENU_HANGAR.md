# Menu, hangar e economia (2026-10-25)

O menu e o hangar passam a ser a mesma cena: a oficina (`AEXHangarStage`, 32 × 28 × 10 m, feita em código a 12 km
da pista e 3 km de altura), com a nave escolhida no prato giratório. Ao abrir o jogo as luzes acendem fila a fila.
O jogador recusou o menu escuro: a garagem fica sempre iluminada e visível.

## Menu (`UEXMainMenuWidget`, maqueta aprovada `menu.png`)

- À esquerda, o logo e quatro linhas: **01 EXPEDIÇÃO SOLO, 02 PELOTÃO 15, 03 HANGAR, 04 SAIR**. A linha escolhida
  acende-se e mostra a descrição.
- À direita, o briefing: mapa da rota (`UEXRouteMapWidget`, a linha de corrida vista de cima), distância, duração
  estimada, atalhos, nave, carga, valor em risco e resultado da última expedição.
- A carteira de STARDUST fica em cima e as teclas em baixo.
- Controlo com W/S ou as setas do comando, Enter ou Cruz, Tab para trocar de nave e Esc para sair. O rato acende e
  clica as linhas.

## Hangar (`UEXHangarWidget`, maqueta aprovada `hangar2.png`)

- A câmara aproxima-se da nave.
- **Naves:** lista à esquerda, com as vidas em losangos.
- **Carga da expedição:** painel à direita com a capacidade da nave, os itens (quantidade e preço) e o valor em risco.
- **Números da nave** em baixo: velocidade de ponta, vidas, espaços de carga e o choque que tira uma vida.
- **Botão LANÇAR EXPEDIÇÃO:** usa o modo escolhido antes no menu (Pelotão 15 por omissão).
- **Teclas:**
  - W/S escolhem o item e A/D mudam a quantidade;
  - Tab, 1 a 5 ou as setas do comando trocam de nave;
  - rato, Q/E ou o analógico direito rodam a câmara, e a roda dá zoom;
  - Espaço liga ou desliga a rotação automática;
  - Enter lança a expedição e Esc volta ao menu.

## Economia (`EXProfile.h`: `UEXProfileSave`, `EXEconomy`)

- **Perfil:** guardado no slot `EXProfile`. Um perfil novo começa com 3000 STARDUST, 2 kits de reparação e 1 surge.
- **Itens:**

  | Item | Preço | Peso | Efeito |
  | --- | --- | --- | --- |
  | Kit de reparação | 150 | 1 | +1 vida (H ou Quadrado) |
  | Surge | 200 | 1 | Enche o nitro (F ou seta para cima) |
  | Escudo | 300 | 2 | O próximo embate não tira vida |
  | Combustível | — | — | Em breve |

- **Capacidade por nave:** VORTEX 3, STRIX 4, WRAITH 5, BASTION 6, NOMAD 7. Ao trocar para uma nave mais pequena,
  o excesso volta à loja e o dinheiro é devolvido.
- **Fim da expedição (`AEXRaceDirector::SettleExtraction`):**
  - quem chega a B fica **EXTRACTED**: guarda o que sobrou da carga e recebe 250, mais 30 por cada nave que chegou
    depois de si, mais uma parte do espólio;
  - o espólio é a soma da carga dos **DESTROYED**. Divide-se por ordem de chegada: o 1.º leva a maior parte;
  - quem é destruído perde a carga. Quem ainda vai a caminho fica **STRANDED**;
  - o STARDUST da carteira nunca se perde.

## A afinar no Unreal

- **Luz da oficina** (`EXHangarStage.cpp`): `WorkLumens` (1300 por painel) e os focos. Está dimensionada como o
  deserto (sol de 10 lux), para a exposição automática funcionar igual nos dois.
- **Enquadramento da câmara do menu** (`EXHoverCraft.cpp`): `ShowroomDistCm` (12,5 m) e `ShowroomPitchDeg` (8°).
- **Interface:** toda em UMG feita em código, com a fonte Roboto do motor. A Orbitron das maquetas pode entrar
  depois, como asset de fonte.
