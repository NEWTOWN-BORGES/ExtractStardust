# Em casa, passo a passo (2026-11-02)

Tudo o que foi feito na nuvem desde domingo (física, explosão e destroços, interface igual às maquetas, cartas,
cofre, consumíveis, épicos e lendários, porquinho HD, HUD novo, portões, setas de nitro, sinalética, atalhos em Y e
inspetor) é compilado e importado aqui, por esta ordem. Os comandos correm no PowerShell, **na pasta do projeto**.

## 0. Antes de começar

1. **Fechar o editor do Unreal** (com ele aberto, o código não compila).
2. Buscar o trabalho da nuvem: `git pull origin ccr-6888126d-pxbtcg`
3. Confirmar o que os scripts usam:
   - Unreal em `C:\Program Files\Epic Games\UE_5.8`. Se estiver noutra pasta, junta `-UE "<pasta do Unreal>"` a
     todos os comandos `.ps1`.
   - `blender` no PATH. Se não estiver, junta `-Blender "<caminho>\blender.exe"`.
4. Para a pista nova (passo 2 do script), tem de existir em `C:\rdd`:

   | Pasta ou ficheiro | Se faltar |
   |---|---|
   | `kit\` (14 FBX de rochas) | `blender -b -P Scripts/sculpt_rock_kit.py -- C:/rdd/kit C:/rdd/kit/preview` (~4 min) |
   | `plantas\` (refazer se for anterior a 20/10) | `blender -b -P Scripts/sculpt_plants.py -- C:/rdd/plantas C:/rdd/plantas/preview` |
   | `moldes\` | `mkdir C:\rdd\moldes; Copy-Item C:\rdd\kit\*.fbx, SourceArt\Rocks\*.fbx, SourceArt\S01\*.fbx C:\rdd\moldes` |
   | `strix.fbx` (a nova) | `Copy-Item SourceArt\TestShips\strix.fbx C:\rdd\strix.fbx` |

## 1. Compilar e importar tudo (um comando)

```
powershell -ExecutionPolicy Bypass -File Scripts\casa_tudo.ps1
```

| Passo | O que faz | No log, ver |
|---|---|---|
| 1 | compila o C++ | `Result: Succeeded` |
| 2a | gera a pista A→B a 3 m, com os atalhos em Y (Blender; é o passo mais demorado) | sem erros no fim |
| 2b | exporta a pista para o Unreal | |
| 3a | importa as peças da pista | |
| 3b | importa as 5 naves | `SHIPBOUNDS` (nariz em −Y, 5,8-7,3 m) |
| 3c | importa os módulos, também os épicos e lendários de cada nave | |
| 3d | ícones, fotos e cartas do hangar, arte do HUD e dos menus, porquinho HD, explosão e destroços | `FXASSETS ... 0 problems` |
| 3e | materiais fotorrealistas das naves | |
| 4 | monta o mapa Expedition (abre o editor, grava e fecha sozinho) | `EXPEDITION MAP BUILT` |

No fim aparece `PRONTO`.

- **Sem tempo para a pista:** `... casa_tudo.ps1 -SemPista` faz tudo menos os passos 2a, 2b, 3a e 4. Fica tudo
  menos os atalhos em Y (precisam da pista nova).
- **Falta de memória no 2a:** junta `-Metros 5`.
- **Se um passo falhar**, o script para e escreve `FALHOU: <passo>`. Manda-me:
  - o nome do passo e as primeiras linhas com `error`. No passo 1 estão no ecrã; o log completo está em
    `%LOCALAPPDATA%\UnrealBuildTool\Log.txt`. Nos outros passos, as linhas com `Error` ou `Traceback` de
    `Saved\Logs\ExtractingStardust.log`.

  Eu corrijo na nuvem. Depois fazes `git pull` e recomeças no passo que falhou, sem repetir os anteriores (por
  exemplo `... casa_tudo.ps1 -Desde 3c`). Se o erro foi no passo 1, recomeça com `-Desde 1`.

## 2. Jogar e verificar (por esta ordem)

A consola do jogo abre com a tecla à esquerda do 1. O log fica em `Saved\Logs\ExtractingStardust.log`.

1. **Interface:** `powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1`
   - Em cada ecrã escreve `HighResShot 1` na consola (as fotos vão para `Saved\Screenshots`). Compara cada uma com
     `Docs\UI_MAQUETAS\` e com `Docs\HUD_CORRIDA_MAQUETA.png`; a lista do que tem de se ver está em
     `Docs\UI_MAQUETAS\README.md`.
   - **Se um ecrã for diferente da maqueta, corrige-se o código, não a maqueta.** O logótipo fica laranja.
   - Ecrãs a ver: menu, NAVE (estrelas por baixo do nome), EQUIPAR (cartas 2 × 2, a peça montada na nave),
     CONSUMÍVEIS (cartas com a foto 3D), LOJA (grelha de cartas), COFRE e abrir uma caixa.
   - No COFRE: chips de filtro, ordem e "VENDER NÃO MONTADOS C/I". Teclas: W/S linha, A/D carta, Espaço filtro,
     T ordem, ⌫ vender.
   - A economia de teste está ligada (caixas a 250, 500 e 1000, raros e épicos em quase todas, 5000 STARDUST para o
     1.º lugar), para veres depressa os épicos e lendários de cada nave.
2. **Explosão e física:** `... Scripts\jogar.ps1 -Modo Sandbox`
   - Na consola escreve `EXBoom 0` a `4` (0 desgaste, 1 de frente, 2 de lado, 3 de nariz, 4 por trás). Deves ver:
     destroços a voar como bolas de fogo, câmara lenta 0,3× e o casco a arder com fumo. Se as chamas saírem de cabeça
     para baixo, põe `FlipV = 1` no material `M_FX_Flipbook`.
   - Experimenta as rampas, a mesa, as lombas, a queda de 14 m, as costelas e os 7 bots. O log escreve linhas
     `EXPHYS`. A física afina-se pela tabela da secção 5 de `Docs\FISICA.md`.
3. **Corrida com o pelotão:** `... Scripts\jogar.ps1 -Modo Bots`
   - Aos ~6 s, 9,5 s e 13 s explode um bot à tua frente (`EXRACE CRASHTEST` no log). Sem isto: `-SemAcidentes`.
   - A ver:
     - portões: o próximo é ciano, o de extração em B é dourado e os pilares ficam na borda da estrada;
     - setas de nitro antes dos saltos, placas de chevrons nas curvas e balizas âmbar na areia;
     - HUD novo com o porquinho HD animado, consumíveis nas teclas 1-4 e o ecrã de resultados no fim.
4. **Som (motor novo):** na mesma corrida, acelera a fundo na grelha antes das luzes; o motor bate no limitador
   ("brap-brap"). Depois ouve:
   - as mudanças de potência na partida;
   - os estalos ao largar o acelerador e nas reduções;
   - o nitro: o motor puxa o ar, vem uma pancada e depois o rugido;
   - os rivais a passar.
   Referência: `Docs\SOM\jogo_corrida_v2.mp3`.
5. **Inspetor da pista:** `... Scripts\jogar.ps1 -Modo Inspecao`. A nave corre a pista sozinha e escreve o relatório
   em `Saved\Inspect\relatorio.txt`, com fotos. Manda-me o relatório.

## 2b. Desempenho (o jogo prendia no hangar e no meio das naves; correções de 2026-11-02)

- **Comando PlayStation:** sem comando ligado, o jogo procurava-o a cada 2 s e bloqueava durante a procura. Agora
  procura-o em segundo plano.
- **Fotos, peças e explosões:** as fotos das cartas, as peças das naves e a arte das explosões carregam em fundo ao
  arrancar e ficam na memória. No log aparece `EXPERF a carregar em fundo N recursos`. Antes carregavam do disco na
  primeira vez que apareciam e voltavam a sair da memória um minuto depois.
- **Hangar:** só se refazem as peças que mudam.
- **Naves longe da câmara:** as chamas das naves a mais de 250 m atualizam-se 4 vezes menos (não se nota).
- **Para medir:** o log escreve a cada 10 s `EXPERF NN fps em media, pior imagem NN ms` e escreve `EXPERF hitch NN ms`
  sempre que uma imagem demora mais de 60 ms. Se ainda prender, manda-me essas linhas.
- **No editor (`jogar.ps1`) o jogo prende mais:** na primeira vez que aparece cada efeito, o editor compila-o. O jogo
  empacotado (`Builds\Jogo`, secção 5) não faz isso. Para julgar a fluidez, usa o jogo empacotado.

## 3. O que me mandar

- Os erros de compilação ou dos passos (ver secção 1).
- O `relatorio.txt` do inspetor.
- As fotos dos ecrãs que não batem certo com as maquetas.
- O que achaste da física, da explosão e do som dos motores.

Depois de eu corrigir: `git pull` e `casa_tudo.ps1 -SemPista` (ou `-Desde <passo>`).

## 4. Guardar no GitHub (quando estiver tudo bem)

1. Ver que nenhum ficheiro passa de 100 MB (o GitHub recusa-os):
   `Get-ChildItem -Recurse Content | Where-Object Length -gt 100MB`
2. Gravar e enviar:

```
git pull origin ccr-6888126d-pxbtcg
git add Content Binaries
git commit -m "Casa: compilado e importado (2026-11-02)"
git push origin ccr-6888126d-pxbtcg
```

## 5. Jogo empacotado (opcional), para `Builds\Jogo`

```
& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun -project="$PWD\ExtractingStardust.uproject" -platform=Win64 -clientconfig=Development -build -cook -stage -pak -archive -archivedirectory="$PWD\Builds\Jogo" -noP4 -utf8output
```

## 6. Quando o teste acabar

Diz-me para desligar o modo de teste: os acidentes à frente e a economia de teste (`EXMeta::bTestEconomy`).

## 7. Mapa 02 Selva Esmeralda

- Os 10 setores estão feitos em Blender (fotos em `Docs\SELVA` e `Docs\SELVA\HD`), mas **ainda não entram no
  Unreal**: falta o importador (secção 6 de `Docs/PISTA_SELVA_ESMERALDA.md`).
- **Opcional agora**, para confirmar que o Blender de casa os gera:
  `powershell -ExecutionPolicy Bypass -File Scripts\selva\gerar_selva.ps1`
  - Grava em `C:\rdd\selva\S1` a `S10` o relevo, as plantas e a cena, e demora alguns minutos por setor.
  - Com `-Fotos` faz também as fotos.
  - Da primeira vez instala o scipy no Python do Blender.
