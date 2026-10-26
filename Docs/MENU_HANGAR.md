# Menu, hangar e economia (2026-10-25)

O menu e o hangar passam a ser a mesma cena: a oficina (`AEXHangarStage`, 32 × 28 × 10 m, feita em código a 12 km
da pista e 3 km de altura), com a nave escolhida no prato giratório. Ao abrir o jogo as luzes acendem fila a fila.
O jogador recusou o menu escuro: a garagem fica sempre iluminada e visível.

## Menu (`UEXMainMenuWidget`, maqueta aprovada `menu.png`)

- À esquerda, o logo e quatro linhas: **01 EXPEDIÇÃO SOLO, 02 PELOTÃO 15, 03 HANGAR, 04 SAIR**. A linha escolhida
  acende-se e mostra a descrição.
- À direita, o briefing: mapa da rota (`UEXRouteMapWidget`, a linha de corrida vista de cima), distância, duração
  estimada, atalhos, nave, módulos e consumíveis, valor em risco e resultado da última expedição.
- A carteira de STARDUST fica em cima e as teclas em baixo.
- Controlo com W/S ou as setas do comando, Enter ou Cruz, Tab para trocar de nave e Esc para sair. O rato acende e
  clica as linhas.

## Hangar (`UEXHangarWidget` + `UEXHangarModel`)

Os módulos, as caixas e os consumíveis estão em `Docs/MODULOS.md` (secção 10, separadores e teclas).

- **Câmara:** aproxima-se da nave. O rato ou o analógico direito rodam-na, e a roda ou os gatilhos dão zoom. Espaço
  liga ou desliga a rotação automática.
- **Separadores:** Q/E ou os botões de ombro.
  - **NAVE:** as naves, com as vidas, e o botão **LANÇAR EXPEDIÇÃO** (Enter), que usa o modo escolhido antes no menu
    (Pelotão 15 por omissão).
  - **EQUIPAR:** os slots e as peças, com a nave a mostrar a peça escolhida.
  - **CONSUMÍVEIS:** os 4 slots rápidos.
  - **LOJA:** caixas e módulos.
  - **COFRE:** abrir caixas e vender peças.
- **Outras teclas:**
  - W/S escolhem a linha e A/D a opção;
  - Tab ou 1 a 5 trocam de nave;
  - Esc volta ao menu (com uma caixa aberta, fecha primeiro a caixa).

## Economia (`EXMeta.h`, `EXProfile.h`)

- **Perfil:** guardado no slot `EXProfile` (versão 2).
- **Perfil novo:** 3000 STARDUST, uma STANDARD CACHE e os consumíveis do jogo antigo.
- **Perfis do protótipo de carga:** ficam com o STARDUST e recebem o mesmo kit inicial.
- **Fim da expedição (`AEXRaceDirector::SettleExtraction`):**
  - quem chega a B fica **EXTRACTED** e recebe o prémio do lugar (tabela do doc 03 × 0,70) mais 250; a primeira
    extração dá mais 500, uma vez só;
  - quem é destruído (**DESTROYED**) perde até 3 módulos montados (nunca o segurado) e os consumíveis que levava;
  - essas peças reais, também as dos bots, formam o espólio. Reparte-se em serpentina por valor entre os
    EXTRACTED;
  - quem ainda vai a caminho fica **STRANDED**: fica com tudo e não ganha nada;
  - o STARDUST da carteira nunca se perde.

## A afinar no Unreal

- **Luz da oficina** (`EXHangarStage.cpp`): `WorkLumens` (1300 por painel) e os focos. Está dimensionada como o
  deserto (sol de 10 lux), para a exposição automática funcionar igual nos dois.
- **Enquadramento da câmara do menu** (`EXHoverCraft.cpp`): `ShowroomDistCm` (12,5 m) e `ShowroomPitchDeg` (8°).
- **Interface:** toda em UMG feita em código.

## Igual às maquetes (2026-10-26, pedido do jogador: "não aceito menos")

- **Fontes:** Inter (texto) e Orbitron (títulos, nomes das naves, velocidade), em `Content/UI/Fonts` (OFL), empacotadas
  com o jogo (`DirectoriesToAlwaysStageAsUFS`). Sem os ficheiros, volta a Roboto.
- **Arte:** `Scripts/make_ui_icons.py` desenha os ícones (famílias, consumíveis, caixas, cópia de nave, estrela) e a arte
  da interface (brilhos, riscas do verso das cartas, gema do STARDUST, d-pad, barras de chama, logo do menu).
- **Fotos dos módulos:** `Scripts/render_modules.py <modulos> <nave> <saida> thumbs` fotografa cada nave com cada módulo
  montado (180 fotos de 496 × 316, em `SourceArt/UI/Thumbs`): asas, kits, refrigeração e caudas por fora; motor (com a
  chama), propulsão (nitro na cor), reator (brilho na cor) e utilitário (no nariz) no esqueleto.
- **Importar:** `Scripts/import_ui_icons.py` (passo 3d do `casa_tudo.ps1`) → `/Game/UI/Icons` e `/Game/UI/Thumbs`.
- **Hangar** (`UEXHangarWidget`): slots com ícone, nome na cor da raridade, classe e escudo do seguro; peças com barra
  de chama, raridade, valor com a gema e chips verdes e vermelhos; legenda por baixo da nave e notas presas às peças;
  consumíveis à volta do d-pad e stock com botões COMPRAR; cartas da caixa com a foto da nave com o módulo, brilho da
  raridade, faixa NOVO nos épicos, verso com riscas, "VENDER COMUNS (25%)" (⌫) e "GUARDAR TUDO" (Enter); Enter revela
  uma carta, Espaço todas. Na LOJA e no COFRE, o módulo escolhido aparece como carta com a foto.
- **Menu:** logo em imagem, linhas e títulos em Orbitron, oficina iluminada (o menu escuro foi recusado).
- **HUD da corrida** (`UEXRaceHudWidget`, maquete `hud.png`): posição e tempo, vidas e valor em risco, velocidade com
  as barras e os 4 consumíveis com ícones. O minimapa, a seta e as mensagens continuam no `AEXHud`.
