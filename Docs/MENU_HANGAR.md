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

## O estilo do HUD em todos os ecrãs (2026-11-01)

Pedido do jogador: "a mesma direção de arte para os menus iniciais, hangar e cofre... tudo profissional". O menu, o hangar
(todos os separadores), o cofre, a caixa aberta e os resultados passam a ter o estilo do HUD da corrida
(`Docs/HUD_CORRIDA.md`). Maquetas em `Docs/UI_MAQUETAS/` (menu, nave, equipar, cofre, caixa).

- **Cores** (`EXUiStyle.h`):
  - placas azul-escuras (`Plate`);
  - ciano nas bordas, na seleção e no botão principal (`Accent`, `AccentHot`);
  - dourado no STARDUST, nos prémios e nas estrelas (`Gold`);
  - vermelho-laranja no perigo e nas perdas (`Danger`);
  - verde nas vidas e nos ganhos (`Ok`);
  - texto branco-azulado (`Fore`) e cinza-azulado (`Quiet`).

  As cores antigas (`Rust`, `Bone`, `Sand`) saíram.
- **Formas** (`Scripts/make_hud_art.py menu`, ficheiros `ui_*`):
  - placas com dois cantos cortados, o de cima à esquerda e o de baixo à direita: painéis, linhas, chips e teclas;
  - cartas com só o canto de baixo à direita cortado, porque a foto enche o topo;
  - separadores inclinados como os números do HUD;
  - o botão principal, de ciano a azul.

  A arte é branca e o jogo pinta-a (`EXUi::Frame`, `SetShapeBrush`, `ShapeImage`). Serve assim para qualquer cor e
  tamanho, e os cantos ficam nítidos.
- **Letra:**
  - títulos e números em Orbitron inclinado, com contorno escuro (`TitleText`);
  - etiquetas em Inter extra negrito espaçado (`LabelText`).
- **Seleção:**
  - linha escolhida com fundo azul mais claro, um brilho ciano que se desvanece para a direita e borda ciano;
  - separador aberto em ciano, com letras escuras;
  - carta escolhida com contorno ciano;
  - no cofre, o chip "VENDER NÃO MONTADOS C/I" fica a vermelho.
- **STARDUST:** é sempre a moeda dourada do porquinho (`hud_coin`): na carteira, nos preços e nos valores.
- **Oficina:** o anel do prato giratório e o letreiro passam a ciano (`EXHangarStage.cpp`, `Rim`).
- **Cofre:** as três filas de cartas tapavam a barra de teclas. As cartas passam a 0,74 e o contador vai para a linha do
  título.
- **Maquetas:** `Scripts/ui_mockups/screens.py` desenha-as sobre um render aproximado da oficina
  (`Scripts/ui_mockups/hangar_scene.py`), com a arte, as posições e os tamanhos do código.
- **Importar e compilar:** o passo 3d do `casa_tudo.ps1` traz os `ui_*` novos (pelo `import_ui_icons.py`). Depois,
  compilar com `Scripts\casa_tudo.ps1 -SemPista`.
- **Ícones 3D** (pedido do jogador, 2026-11-01: "tem de mostrar os ícones 3D"). Onde havia um ícone plano, aparece agora
  a foto 3D:
  - as caixas STANDARD, ADVANCED e ELITE são caixotes 3D próprios (`Scripts/make_caches.py`), com as fotos em
    `SourceArt/UI/Thumbs/cache_<n>.jpg` e os modelos em `SourceArt/Caches`. A cor de cada uma é ciano, azul e dourado;
  - os slots do EQUIPAR mostram a peça montada. A peça de série mostra a nave;
  - os slots rápidos dos CONSUMÍVEIS mostram o consumível em 3D;
  - as cartas dos resultados mostram a nave com a peça, e o porquinho HD aparece no título do espólio.

  O ícone plano só aparece enquanto as fotos não estiverem importadas (passo 3d).
- **Resultados:**
  - o título passa a 52, para caber com a medalha;
  - o total e as colunas da classificação já não se sobrepõem;
  - a etiqueta passa a ser só "SEGURA";
  - o Orbitron não tem "·" nem "º", por isso o `TitleText` troca-os por "•" e "°" (`EXUi::OrbitronSafe`).

