# Maquetas da interface: o jogo tem de ficar IGUAL a estas imagens

Pedido do jogador (2026-11-01): "espero que venha tudo como nas maquetes; deixe isso bem assinalado para aí em casa fazer
exatamente assim". **Estas imagens são a referência.** Se o jogo compilado não ficar assim, é um defeito a corrigir no
código, não nas maquetas (só se muda o desenho se o jogador pedir).

| Ecrã | Maqueta | Código |
|---|---|---|
| Menu inicial | `menu.jpg` | `EXMainMenuWidget.cpp` |
| Hangar · NAVE | `nave.jpg` | `EXHangarWidget.cpp` (+ `EXHangarModel.cpp`) |
| Hangar · EQUIPAR | `equipar.jpg` | idem |
| Hangar · CONSUMÍVEIS | `consumiveis.jpg` | idem |
| Hangar · COFRE (e a LOJA, igual) | `cofre.jpg` | idem |
| Caixa aberta | `caixa.jpg` | idem (`BuildCacheOverlay`) |
| Resultados | `resultados.jpg` | `EXResultsWidget.cpp` |
| HUD da corrida | `../HUD_CORRIDA_MAQUETA.png` | `EXRaceHudWidget.cpp` (`Docs/HUD_CORRIDA.md`) |

O estilo vem todo de `UI/EXUiStyle.h/.cpp`: cores, placas com cantos cortados, `TitleText`, `LabelText` e botões.

## 1. Pôr no jogo (PC de casa)

1. `git pull` do ramo `ccr-6888126d-pxbtcg`.
2. `powershell -ExecutionPolicy Bypass -File Scripts\casa_tudo.ps1 -SemPista`. Compila e corre o **passo 3d**:
   - `import_ui_icons.py` importa a arte `ui_*` e `hud_*`, a moeda `hud_coin` e as fotos de `SourceArt/UI/Thumbs`,
     incluindo as das caixas (`cache_0/1/2`), dos consumíveis (`con_*`) e das peças;
   - `import_piggy.py` importa o porquinho HD.
3. Jogar a 1920 × 1080: `Scripts\jogar.ps1 -Modo Bots`.
4. Tirar uma foto de cada ecrã: na consola (tecla `'` ou `~`), escrever `HighResShot 1`. As fotos ficam em
   `Saved/Screenshots/...`.
5. Pôr cada foto ao lado da maqueta e ver a lista do ponto 3.

## 2. Se aparecer diferente

- **Caixas lisas em vez de placas com cantos cortados, ou retângulos de cor em vez de fotos:** a arte não foi importada.
  O código desenha caixas lisas enquanto faltam os `ui_*`, e o ícone plano enquanto faltam as fotos. Repetir o passo 3d
  e confirmar no log as linhas `UIART ... imported`.
- **Quadrados vazios no lugar de letras:** é um sinal que a fonte não tem. O Orbitron não tem "·" nem "º", que o
  `EXUi::OrbitronSafe` troca por "•" e "°". Se aparecer outro, juntá-lo a essa função.
- **Algo fora do sítio, a mais ou cortado:** medir na foto e acertar o código pelas posições de `Scripts/ui_mockups/screens.py`.
  Esse script desenha as maquetas com as mesmas posições e tamanhos do código. Se alguma medida tiver de mudar, mudar o
  código **e** o script, voltar a gerar as maquetas (`python3 Scripts/ui_mockups/screens.py`) e mostrar ao jogador.
- **Diferenças que contam como iguais:** o fundo 3D (a oficina real e a pista real) e os valores do jogo (nomes, números).

## 3. O que tem de se ver em cada ecrã

**Em todos:**
- [ ] Placas azul-escuras com os cantos de cima à esquerda e de baixo à direita cortados, borda ciano fina a brilhar.
- [ ] Títulos e números em Orbitron, inclinados para a frente, com contorno escuro.
- [ ] STARDUST sempre com a moeda dourada (`hud_coin`), e a carteira numa placa de borda dourada, em cima à direita.
- [ ] Barra de teclas azul-escura em baixo, com uma linha ciano por cima e as teclas em caixinhas.

**Por ecrã:**
- [ ] **Menu:**
  - logótipo em cima à esquerda (laranja; o jogador ainda pode escolher ciano ou branco, ver
    `screens.py logos`);
  - as 4 linhas, com a escolhida numa placa com brilho ciano e barra à esquerda;
  - o briefing à direita, com barra ciano no topo, a rota a ciano, as 3 caixas de números, os chips, o risco a dourado
    e a última expedição a verde.
- [ ] **Topo do hangar:**
  - HANGAR em itálico;
  - 5 separadores inclinados, com o aberto todo ciano e de letras escuras.
- [ ] **NAVE:**
  - a lista das naves com vidas (verde) e estrelas (dourado);
  - o nome da nave grande, branco e com contorno, sobre o prato, com a frase a ciano e as estrelas;
  - o painel da direita com barra ciano no topo;
  - os stats ao centro em baixo;
  - LANÇAR EXPEDIÇÃO num botão ciano-azul com brilho, em baixo à direita.
- [ ] **EQUIPAR:**
  - os slots com a **foto 3D da peça** (as de série mostram a nave);
  - a peça escolhida em cartas 2 × 2 com foto;
  - a etiqueta PRÉ-VISUALIZAÇÃO na cor da raridade;
  - as duas notas presas à nave;
  - os stats com +N verde ou −N vermelho;
  - o botão MONTAR.
- [ ] **CONSUMÍVEIS:**
  - os 4 slots à volta do d-pad com o **consumível em 3D**;
  - o stock em cartas com foto;
  - o resumo ao centro em baixo.
- [ ] **COFRE e LOJA:**
  - os chips de filtro (o ligado a ciano, VENDER NÃO MONTADOS C/I a vermelho);
  - a grelha de 4 × 3 cartas, que cabe toda **acima** da barra de teclas;
  - as caixas como **caixotes 3D**: elite com borda dourada, avançada azul, padrão ciano;
  - a carta grande à direita, com a faixa NOVO nas épicas e lendárias.
- [ ] **Caixa aberta:**
  - fundo escurecido a azul;
  - 10 cartas, com as viradas para baixo mostrando o losango ciano;
  - as épicas e lendárias mais acima, a brilhar, com a faixa NOVO;
  - em baixo, VENDER COMUNS (vermelho) e GUARDAR TUDO (ciano).
- [ ] **Resultados:**
  - EXTRAÍDO com a medalha ao lado, sem tocar nas cartas;
  - a placa dos ganhos com barra verde, e o total sem se sobrepor ao texto;
  - as cartas do espólio com a **foto da nave com a peça**;
  - o porquinho HD no título do espólio;
  - a classificação com as colunas alinhadas e TU a ciano.
- [ ] **HUD da corrida:** como `../HUD_CORRIDA_MAQUETA.png`, ponto por ponto (`Docs/HUD_CORRIDA.md`).

## 4. Voltar a gerar as maquetas

1. A oficina: `python3 Scripts/ui_mockups/hangar_scene.py -- Docs/UI_MAQUETAS/hangar_bg.png`, com o módulo `bpy` ou com
   `blender -b -P`.
2. A pista atrás dos resultados: o render da cena do HUD, que se passa em `UI_MOCK_RACE_BG`.
3. Os ecrãs: `python3 Scripts/ui_mockups/screens.py`. Gera `ui_<ecrã>.png` e uma cópia `<ecrã>.jpg` para aqui.
