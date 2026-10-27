# Extracting Stardust — notas para a IA (ler primeiro)

Jogo de **extraction racing** de naves antigravidade (Unreal Engine, `ExtractingStardust.uproject`).
Visão do produto: `Docs/VISAO_JOGO.md` (RACE. SURVIVE. EXTRACT. — A→B, 15/20/30 naves, pool de
espólios na meta; loadout no hangar, sem pickups na pista; monstros mais tarde). O mapa **Red Dust Divide**
é gerado por scripts do Blender em `Scripts/`; a explicação completa está em `Docs/ESTUDO_BLENDKIT_CANYONS.md`
(secções 5 a 12) e o plano do setor S01 em `Docs/MAPA_01_RED_DUST_DIVIDE_S01.md`.

O jogador fala português (PT). Responder em português.

## FEITO EM CASA A 2026-10-26 (ramo ccr-6888126d-pxbtcg, commits locais; builds `Builds\Naves*`)

- **Câmara e condução de 2026-10-20 repostas** (valores de c79fecb). O jogador rejeitou a câmara de ápice e a
  inclinação funda feitas no outro PC (a6ba938). Não mexer na câmara nem na condução sem perguntar.
- **Corrida:** largada em filas retas e presa até à partida (luzes 3-2-1); checkpoints a cada ~2,5 km (+40 cada,
  +300 todos, pagos na extração); HUD em barra (A→B no topo, velocidade segmentada); **casco em barra** como na Unity
  (dano: impacto acima de 16 m/s × 0,85, metade contra naves, no máximo 40 % por pancada, 10 s sem dano no início);
  **explosão** (`AEXExplosion`) quando o casco acaba; ecrã de resultados `UEXResultsWidget` (vitória/derrota, ganhos,
  cartas, medalha, classificação); fim garantido (meta a 45 m do último ponto, resultados 15 s depois ou com Enter).
- **Porquinho** (pool ao vivo) de volta no HUD com os adversários em prova; **bots com carga** (2-6 peças,
  `EXMeta::RollBotCargo`). **Regras do espólio (jogador, 2026-10-27, = `Docs/VISAO_JOGO.md`):** quem é destruído perde
  tudo menos o item seguro (1); tudo vai para o porquinho, dividido no fim por quem extrai, por ordem de chegada (o 1.º
  escolhe primeiro em cada volta). O "espólio de vitória 3/2/1" foi retirado. **Nada de cápsulas/peças a apanhar na
  pista** (testado e rejeitado; código guardado fora do projeto).
- **Gráficos:** Lumen por defeito (`Jogar Leve.bat` = `-EXLow` desliga), nuvens volumétricas, atmosfera com poeira,
  sol baixo, névoa volumétrica, gradação de cor. **Fotorrealista** (escolha do jogador, "tipo Call of Duty"):
  `make_ground_material.py` (fotos CC0 Poly Haven sem repetição, triplanar nas falésias, areia com ondulações em 3
  escalas e brilho do quartzo) e `make_rock_material.py` (arenito triplanar, só nós de textura: as rochas são Nanite);
  naves com `make_ship_materials.py` (pintura, riscos, pó, carbono, metal escovado; passo 3e do `casa_tudo.ps1`).
  Plano e regras: `Docs/PLANO_TEXTURAS.md`. Fotos de prova: `-EXFlightTest -EXLook="x,y,z,yaw,pitch;..."` (vistas em
  `C:\rdd\look_views.txt`).
- **Pista:** larguras e curvas originais (a versão larga/oval foi rejeitada); estrada **natural** (borda que vagueia,
  taludes de 6-22 m e depois falésia; nada "cavado"); ziguezague S3 com paredes de 32 m; túnel liso e largo, aberto
  nas bifurcações do braço (havia um degrau de 4 m e paredes cruzadas); arcos sem colisão; hoodoos a 48 m da borda.
- Atenção: no PowerShell, `Start-Process -ArgumentList` não põe aspas em caminhos com espaços (usar `&` ou aspas).

## PEDIDOS DE 2026-10-25 (noite), por testar em casa

- **Estrelas das naves** (`Docs/MODULOS.md` secção 8b): cada cópia de uma nave dá 1 estrela, até 7, e cada estrela dá
  +2 nos 8 stats base da nave. A cópia só sai na ELITE CACHE (6%). Código em `EXMeta`, `EXProfile`, `EXHangarModel`, `EXHangarWidget`,
  `EXHoverCraft::ApplyShipStats`): compilar e abrir uma ELITE no COFRE (para testar mais depressa, subir
  `EXMeta::ShipCopyChance` a 1).
- **Paredes nas curvas do ziguezague** (`Docs/PISTA_AB_RED_DUST_DIVIDE.md`): meio-oval do lado de fora de cada curva em
  U do Shafer Fall (só aí), que cresce na curva e desce nas retas. Testado a 10 m; gerar a pista a 3 m e ver no Unreal
  que se pode subir por ela.
- **Estrelas no hangar:** as 7 estrelas aparecem por baixo do nome da nave (cheias as que tem, vazias as que faltam) e
  em cada nave da lista NAVE.

- **Interface igual às maquetes** (2026-10-26, `Docs/MENU_HANGAR.md`): fontes Inter e Orbitron, ícones, brilhos,
  fotos de cada nave com cada módulo nas cartas (`SourceArt/UI/Thumbs`), HUD da corrida em UMG. Importar com o passo
  3d do `casa_tudo.ps1` e compilar.

- **Condução como antes** (2026-10-26): o Cursor (commit `a6ba938`, 23/10) tinha subido `TurnRateHigh` de 0,8 para 1,05
  e `NoseLeadMaxDeg` de 5 para 8, e a nave escorregava de lado. Voltaram aos valores da Phase 1. A câmara e a nave a
  deitar-se nas curvas ficaram como o Cursor as deixou (o jogador gostou). Asas e caudas valem agora 2 % por ponto de
  Manobra/Estabilidade (eram 0,5 %); sem módulos a condução é a original.

## NAVES NOVAS: falta pô-las no Unreal (2026-10-21; BASTION a 2026-10-25)

As 5 naves (STRIX, WRAITH, NOMAD, VORTEX e BASTION) foram refeitas de dentro para fora (PR #3, ramo
`ccr-6888126d-pxbtcg`) e substituem as antigas. Os FBX novos estão em `SourceArt/TestShips/<nave>.fbx`; as regras e
cada nave estão em `Docs/NAVES_REGRAS.md` e `Docs/<NAVE>_CATEGORIA.md`. A **BASTION** (referência do jogador e depois o
pedido dele, `Docs/BASTION_CATEGORIA.md`): achatada, metida dentro de uma asa de cinza-ardósia, com asas como a
VORTEX (pontas dobradas), carapaça amarela com o motor colossal, airbags de impacto e tomadas de aro laranja.

Para aparecerem no jogo (no PC com o Unreal, depois do `git pull` desse ramo, ou do `extracting-stardust` quando o
PR estiver fundido):
1. Abrir o projeto no editor e correr `Scripts/import_test_ships.py` (Tools → Execute Python Script), ou na linha
   de comandos: `UnrealEditor.exe <caminho>/ExtractingStardust.uproject -ExecutePythonScript=<caminho>/Scripts/import_test_ships.py`.
   Reimporta `/Game/TestShips/SM_*`, que o `EXHoverCraft` já usa.
2. No log, ver as linhas `SHIPBOUNDS`: nariz em −Y, comprimentos de ~5,8 a 7,3 m.
3. Testar no jogo (trocar de nave) e fazer commit dos `.uasset` de `Content/TestShips`.

## MENU E HANGAR (2026-10-25): `Docs/MENU_HANGAR.md`

O menu e o hangar são a mesma oficina iluminada (`AEXHangarStage`), com a nave no prato giratório. Por cima ficam o
menu (Solo, Pelotão 15, Hangar, Sair, briefing com mapa) e o hangar, com 5 separadores: NAVE, EQUIPAR, CONSUMÍVEIS,
LOJA e COFRE. Há carteira de STARDUST guardada e espólio na meta. Interface em UMG feita em código
(`UI/EXUiStyle.h`).

## MÓDULOS, RARIDADES, CAIXAS E CONSUMÍVEIS (2026-10-25): `Docs/MODULOS.md`

Os módulos do jogo antigo (a demo Unity das 5 naves antigas) foram trazidos para as naves novas, com as regras de
`Catalog.cs`, `Items.cs` e `Economy.cs` do `main`.
- **Peças:** 3 asas próprias por nave e as peças universais ajustadas à carroçaria, feitas por
  `Scripts/ship_modules.py`. Ficam em `SourceArt/TestShips/modules/` e importam-se com
  `Scripts/import_ship_modules.py` (passo 3c do `casa_tudo.ps1`).
- **Blindagem = kit de carroçaria** (pedido do jogador, 2026-10-25): faz parte da nave, na pintura dela (saias no
  fundo do casco, lâmina no nariz, aletas atrás nos kits pesados), muda-lhe um pouco as linhas e continua
  aerodinâmica. Nada de placas cinzentas, nada a sair do casco, nada perto do cockpit.
- **Utilidade por dentro:** o scanner, o oracle e o drone ficam dentro do nariz e só se veem no esqueleto, a brilhar.
  Nada de sondas no nariz.
- **Hangar:** no EQUIPAR a nave mostra a peça escolhida. Motor, reator, propulsão e utilidade mostram-se em
  esqueleto, com as chamas de cada motor.
- **Consumíveis:** 4 slots, nas teclas 1-4 e nas setas do comando (cima, baixo, esquerda, direita).
- **Combustível e calor:** são sistemas novos.
- **Caixas:** STANDARD, ADVANCED e ELITE.
- **Fim da expedição:** perdas e espólio com peças reais, também as dos bots.

Escrito na nuvem sem Unreal: em casa, compilar primeiro e seguir a lista "A testar no Unreal" da secção 13 do
documento.

## SOM (2026-10-25): `Docs/SOM.md`

O som é sintetizado ao vivo (`EXSoundSynth.h`, em C++ puro): motor por nave, vento, paredes, eventos e rivais com
Doppler. Antes de compilar ouve-se com `Scripts/audio/render_sound_preview.cpp`, que escreve WAVs. **Os binários Win64
pré-compilados que estão no repositório ficam desatualizados**: compilar com `Scripts\casa_tudo.ps1 -SemPista`.

## PARA FAZER EM CASA / NO PC COM O UNREAL (lista da sessão da nuvem, 2026-10-21)

**Atalho (poucos tokens):** `powershell -ExecutionPolicy Bypass -File Scripts\casa_tudo.ps1`. Compila o C++ dos modos
de jogo, gera a pista a 3 m, exporta-a, importa as peças e as naves novas e monta o mapa Expedition. Depois corre-se
`Scripts\jogar.ps1 -Modo Bots` (ou `Solo`, ou `Teste`, que joga sozinho e escreve `EXRACE` no log). Os modos de jogo
estão em `Docs/MODOS_DE_JOGO.md`. Foram escritos sem Unreal à mão, por isso o primeiro passo é ver se compilam.

Feito na nuvem (sem Unreal), em `Scripts/sculpt_expedition_ab.py`, testado só a 10 m: túnel The Hollow em arco liso e
largo, rochas a 30 m ou mais da pista, estradas de 56-64 m (6-7 naves lado a lado, grelha 3 × 6), variável
`AB_ONLY=08_caverna,07_wash` para tirar só algumas fotos. Detalhes em `Docs/PISTA_AB_RED_DUST_DIVIDE.md`.

1. **Juntar o trabalho do PC do trabalho.** A outra sessão (a de 21 de outubro, ~50 %) mexeu em
   `sculpt_expedition_ab.py`, `EXDesertBuilder.cpp` (luzes do túnel nas balizas), `make_ground_material.py`,
   `make_rock_material.py` e neste `CLAUDE.md`, e **não fez push**. Fazer push dela, fundir com o ramo `ccr-6888126d-pxbtcg`
   (PR #3) e resolver os conflitos no script: manter o arco liso do túnel (`tunnel_walls`, `CAVE_EDGE`, `cave_roof`),
   `TRACK_CLEAR` e as larguras da lista `SECTORS`; do resto aceitar o que ela fez.
2. **Gerar a 3 m** (`blender -b -P Scripts/sculpt_expedition_ab.py -- C:/rdd/ab 3 kit=... molds=... plants=... ship=...`),
   ver as fotos de piloto, sobretudo `ab_08_caverna` e `ab_01_partida`, e exportar/importar/montar o mapa
   (`export_ab_unreal.py`, `import_world.py`, `EXDesertBuilder.build_world_map`).
3. **Ver o túnel dentro do Unreal:** o teto `caves/*.fbx` faz agora também as paredes (arco de meia elipse); o chão do
   túnel é só chão. Confirmar colisão (complexa) do teto, luz e claraboias (são aberturas na malha), e que a nave passa
   a ~500 km/h sem raspar. Se a malha der trabalho, aumentar `CAVE_EDGE` ou o número de pontos laterais do `cave_roof`.
4. **Naves:** correr `Scripts/import_test_ships.py` (ver acima) e `Scripts/import_ship_modules.py` (os módulos, ver
   `Docs/MODULOS.md` secção 13). A BASTION já está feita (2026-10-25), com os módulos.
5. **Modos de jogo:** implementar `Docs/MODOS_DE_JOGO.md` (solo, 15 bots, vidas por nave, kit médico de 3 usos só
   para o jogador), depois de perguntar o que está na secção 9 desse documento.
6. **Mar de dunas** (pedido anterior, por fazer): ampliar o deserto e deixar estruturas de canyon soterradas na areia;
   precisa do núcleo do mundo (`C:/rdd/mapa`), que só existe nos PCs do jogador.

## MODOS DE JOGO: ver `Docs/VISAO_JOGO.md` (produto) e `Docs/MODOS_DE_JOGO.md` (rascunho Unreal)

O jogo **não** é só contra o cronómetro. É extração A→B com pelotão grande. O código actual
(solo / 15 bots / vidas / kit médico) é protótipo; falta menu de hub, som, sensação tipo podrace
(câmara + bank), loadout no hangar, pool de espólios e lobbies de 20–30.

## PRIORIDADE ATUAL (2026-10-20): EXPEDIÇÃO DE A A B — `Scripts/sculpt_expedition_ab.py`

O jogador experimentou no Unreal o mundo de 10 × 8 km com o grande circuito e não gostou:
- "enorme mas vazio": não sabia onde estava nem para onde ir;
- a pista eram "tapetes";
- horizonte infinito, sem um "uau, é ali";
- parecia plano;
- as texturas ficaram como "adesivos quadrados".

Pediu uma **pista de mundo fechado de A a B, de 10-12 minutos** ("o chute final"):
- 450-550 km/h nas zonas rápidas e curvas apertadas a 200 km/h;
- bifurcações por cima, por baixo e subterrâneas;
- túneis, saltos gigantes e pequenos;
- mistura de canyon e deserto;
- os canyons gigantes com fendas de que ele gostou.

O desenho segue o GDD do jogador (`EXTRACT_STARDUST_Pacote_Completo_3_Documentos_v1_0/01_Mapas_Pistas_Expedicoes`,
nas Transferências do PC do trabalho: secções 16-19). Está todo em **`Docs/PISTA_AB_RED_DUST_DIVIDE.md`**: setores
S1-S10, geologia, ramificações, saltos, saídas e o que o jogador veste no Unreal.

**Compilar em casa a 3 m** (o jogador pediu que ficasse assinalado):

```
blender -b -P Scripts/sculpt_expedition_ab.py -- C:/rdd/ab 3 kit=C:/rdd/kit molds=C:/rdd/moldes plants=C:/rdd/plantas ship=C:/rdd/strix.fbx
```

Antes de correr:
- **`C:/rdd/moldes`:** juntar numa pasta todos os moldes de rocha, ou seja, os FBX do kit (passo 1), os de
  `SourceArt/Rocks` e os de `SourceArt/S01`.
- **Plantas:** voltar a correr o `sculpt_plants.py` (passo 2), que agora faz também saguaro, cacto-barril, cholla,
  árvore-de-josué e árvores mortas.
- **Escala:** o `ab_props.json` traz rotação XYZ e escala por eixo, e o importador do Unreal tem de as usar.

- Com `plan` no fim só traça e mede tempos, em segundos.
- Com `noshots` faz terreno, planta e ficheiros para o Unreal, sem fotos.
- A 3 m o mundo de 16 × 12 km tem 5333 × 4000 pontos (21 M). Se faltar memória nas fotos (malha do Blender), usar
  `noshots` a 3 m e fazer as fotos a 5 m.

**Estado (2026-10-20, PC do trabalho):** gerada e validada a 5 m, com fotos de piloto de todos os setores (o
jogador disse "estou a gostar do que vejo").
- Pista de 59 km, 9:46 na linha ideal (média de 362 km/h), 19 saltos na principal e 7 ramificações.
- Corrigido: lajes partidas em placas, borda do Shafer aberta, mesas só com 70 m de largura ou mais e filtro de picos
  em 3 passagens (sem agulhas).

**Próximo passo, em casa:**
1. Gerar a 3 m.
2. Levar para o Unreal: adaptar `export_world_unreal.py`, `import_world.py` e `EXDesertBuilder.build_world_map` aos
   ficheiros `ab_height16.png`, `ab_mask.png`, `ab_route.json` (a rota como spline, com balizas nas curvas),
   `ab_props.json` e `caves/*.fbx`.
3. Material por inclinação e altura com Poly Haven/ambientCG.
4. O jogador põe por cima os Megascans e o céu.

Lições, para não repetir:
- desenhar pela experiência do piloto e validar com **fotos de piloto**, não só com vistas aéreas;
- paredes perto da pista, marcos ao fundo das retas, horizonte fechado;
- material do Unreal por inclinação e altura no shader, com a máscara `ab_mask.png`, e não camadas pintadas aos
  blocos.

**Assets do Fab (Megascans, Elite Desert III):** a licença deles diz "Permite uso com IA: Não". O jogador usa-os no
jogo, mas a IA não abre, não lê e não transforma esses ficheiros. Pode escrever scripts que os referem pelo nome e
caminho no projeto. Para o que a IA trata diretamente, usar CC0 (Poly Haven, ambientCG) ou o nosso kit.

## TAREFA AO ABRIR NO PC DE CASA: gerar tudo a 2 m (mais detalhe)

No PC do trabalho tudo foi gerado a **4 m por ponto** (PC fraco). No PC de casa (mais potente) gerar o mundo
inteiro a **2 m**, exatamente com estes passos e por esta ordem. Não mudar parâmetros nem o desenho sem o jogador
pedir: o mapa e o circuito foram aprovados assim.

### 0. Preparar

- `git pull` no branch `extracting-stardust` (não o `main`, que é o projeto Unity antigo).
- Blender 5.x (ou 4.5+) no PATH, ou usar o caminho completo do `blender.exe`. Numpy vem com o Blender.
- **Pasta de saída com caminho curto** (ex.: `C:\rdd`): no Windows caminhos com mais de 260 caracteres fazem o
  Blender e o curl falhar ao abrir ficheiros.
- Memória: a 2 m o mundo tem 5000 × 4000 = 20 M pontos. Recomenda-se ≥ 32 GB de RAM. Se faltar memória, usar
  **3 m** em todos os passos 3 e 4 (o mesmo valor nos dois).

### 1. Kit de rochas (14 peças, um FBX cada) — ~4 min

```
blender -b -P Scripts/sculpt_rock_kit.py -- C:/rdd/kit C:/rdd/kit/preview
```

### 2. Plantas (choupos, zimbros, salgueiros, mato, erva) — segundos

```
blender -b -P Scripts/sculpt_plants.py -- C:/rdd/plantas C:/rdd/plantas/preview
```

(A pré-visualização usa o Workbench/GPU; num PC sem GPU visível para o Blender em modo background isso falha
depois de exportar os FBX — os FBX ficam bons na mesma.)

### 3. Mapa aprovado (canyon 5 km + mar de dunas 2 km, 7 × 5 km) — a 2 m

```
blender -b -P Scripts/sculpt_canyon_field.py -- C:/rdd/mapa 7 7000x5000 2 5000 C:/rdd/kit
```

Argumentos: saída, seed **7** (não mudar), tamanho 7000x5000 m, **2** m por ponto, canyon até 5000 m, pasta do kit.
Verificar no fim do log: `CANYON FIELD ... lap_m ~17500 tunnels ~27` e `SPEED {...}`. Gera
`canyon_field.blend`, `canyon_field_height16.png`, `canyon_field_mask.png`, `canyon_field.json`, `props.json`,
`tunnels/*.fbx` e imagens `canyon_field_*.png`.

### 4. Mundo de 10 × 8 km à volta do mapa aprovado — a 2 m

```
blender -b C:/rdd/mapa/canyon_field.blend -P Scripts/sculpt_expansion.py -- C:/rdd/mapa C:/rdd/mundo C:/rdd/kit C:/rdd/plantas
```

Usa a mesma resolução do passo 3 (lê-a do JSON). Verificar no fim do log: `WORLD ...`, `NEW PROPS ...`,
`EXPANSION DONE`. Gera `world.blend`, `world_height16.png`, `canyon_field.json` (tudo em coordenadas do mundo),
`props.json` (~19 mil peças) e imagens `world_*.png`.

### 4b. Grande circuito (31 km, 5 ramificações) por cima do mundo — a 2 m

```
blender -b C:/rdd/mundo/world.blend -P Scripts/sculpt_grand_circuit.py -- C:/rdd/mundo
```

Testado a 4 m no PC do trabalho: corre do princípio ao fim em ~10 min. O que faz:
- grava no `world.blend` e no `world_height16.png` a escadaria, as rampas e o chão dos túneis;
- faz os tetos dos túneis em `tunnels_gc/*.fbx`;
- tira das pistas os adereços que lá ficavam (751 a 4 m);
- acrescenta `grand_circuit` ao `canyon_field.json`;
- faz as imagens `gc_plan.png`, `gc_piloto_*.png`, `gc_aerea_*.png` e `gc_3d_*.png` (o estilo de que o jogador
  gosta).

Verificar no log: `LAP LENGTH ~31300`, `TUNNELS`, `SAVED`, `GRAND CIRCUIT DONE`. Com `plan` no fim só traça e mede
(~40 s). Mostrar ao jogador a planta, as vistas 3D e as fotos de piloto.

### 5. Fotos e planta (opcional, para mostrar ao jogador)

```
blender -b C:/rdd/mundo/world.blend -P Scripts/render_route_plan.py -- C:/rdd/mundo
blender -b C:/rdd/mapa/canyon_field.blend -P Scripts/render_ships.py -- C:/rdd/mapa <strix.fbx>
```

A STRIX nova (um motor central, asas a descer) está em `SourceArt/TestShips/strix.fbx`, gerada por `Scripts/build_strix.py` (ver `Docs/STRIX_CATEGORIA.md`); a antiga continua no `main` em `ExtractStardustRDD/Assets/ExtractStardust/Vehicles/V2/Chassis/Resources/V2Chassis/strix.fbx`.
Mostrar as imagens ao jogador (ele pede fotos com frequência: vista de cima, geral, piloto, naves).

Vistas 3D do mundo inteiro (cores por altura, circuito a laranja; o jogador **gostou muito deste estilo**):

```
blender -b -P Scripts/render_world_3d.py -- C:/rdd/mundo
```

Mapa de depuração (rocha, chão dos canyons, fendas, dunas, grelha de 500 m) para escolher pontos de passagem:

```
blender -b -P Scripts/debug_world_fields.py -- C:/rdd/mundo/world_fields.npz C:/rdd/mundo/canyon_field.json C:/rdd/mundo/dbg.png
```

## CONTINUAR AQUI — o mundo já está no Unreal (2026-10-19, noite, PC de casa)

- **Mapa `/Game/Maps/RedDustDivide`** (10 × 8 km a 3 m), feito por código. Passos, depois dos passos 1-4 e do circuito:
  1. `blender -b -P Scripts/export_world_unreal.py -- C:/rdd/mundo` (altura em bruto, máscaras de superfície e de pista);
  2. `python Scripts/download_polyhaven.py` (texturas e modelos CC0 do Poly Haven, ~130 MB, uma vez por PC);
  3. `Scripts/import_world.py` no commandlet (kit, tetos dos túneis, máscaras, material `M_World` e `M_Beacon`);
  4. no editor completo: `unreal.EXDesertBuilder.build_world_map("C:/rdd/mundo")`;
  5. teste: `-game /Game/Maps/RedDustDivide -EXFlightTest -EXTestSpeed=100` (segue a rota `EXRoute`); fotos em
     qualquer ponto com `-EXLook="x,y,z,yaw,pitch;..."` (metros do Unreal).
- O jogador escolheu **Poly Haven/ambientCG (CC0)** para os materiais: "nível gaming realismo", não fotografia.
- Pediu que **a pista se veja**: está pintada no chão (areia compactada mais escura) e há 292 balizas com luz
  no exterior das curvas. Corre a ~55 fps na GTX 1650.
- **Assets do Fab que ele tem (Licença Standard, comercial permitido)**, a descarregar no PC do trabalho em
  qualidade média (2K) com Window → Fab → My Library → Add to Project:
  - *Elite Landscapes: Desert III*: aproveitar **só o céu** (esfera, material, panorama, sombras das nuvens) e apagar
    as paisagens de 8K **antes do commit** (são vários GB);
  - Megascans *Desert Western Cliff Layered* (Large 03, XL 01, XL 14), *Formation Layered XL 05*, *Rock* (Cluster
    Large 04, Ledge Medium 05, Medium 08, Pile Small 01), *Patch Ground Slate Small 01*, *Rock Sandstone*,
    *Large Fallen Tree*, *Old Tree Branch* (os *Quarry Cliff* e o *African Slate Quarry* são cinzentos: pouco úteis);
  - *Monument Valley–Style Desert Rock Tower 01 e 02* (Artemus Blay): torres-marco do Monument Valley.
  Integrar: falésias nas paredes dos canyons, torres no Monument Valley, pedras nos taludes, troncos nos canyons
  verdes. Reduzir texturas a 2K antes do commit (o GitHub não aceita ficheiros > 100 MB e não há LFS).
- **Pedido novo do jogador:** o deserto (mar de dunas) não convence. **Ampliá-lo** e deixar **estruturas de canyon
  soterradas na areia** (mesas e paredes meio enterradas a sair das dunas), sem tocar no mapa aprovado nem no circuito.
- Ainda por fazer: o piloto automático do teste escorrega nas dunas e fica preso à saída do túnel A7 (corredor de
  ~18 m), não é defeito do mapa.

## Estado anterior — 2026-10-19 à noite (PC de casa), antes do Unreal

- PC de casa: 16 GB de RAM, por isso os passos 3 e 4 foram feitos a **3 m** (regra da secção 0). No Blender 5.2 o
  céu `NISHITA` chama-se `MULTIPLE_SCATTERING` e `dust_density` chama-se `aerosol_density` (os scripts já tratam
  as duas versões).
- **Grande circuito: o modo completo já correu e grava tudo** (`GRAND CIRCUIT DONE`). A 3 m apareceram 6 toques na
  rocha, todos corrigidos:
  - o A_west passa a ser uma reta pelo eixo do canhão (y = 1500) até à partida do A (o roteador cortava pela mesa
    ao lado, porque o chão do canhão é mais estreito que a faixa junto às paredes);
  - a reta do arco gigante encurtou para ±40 m (o arco está no vértice de um meandro);
  - pontos do slalom (9568, 2330) e do laço norte (4060, 7030) ligeiramente afastados;
  - os 25 m à frente de cada portal (que o `carve` escava) já não contam como toque.
  Resultado: volta de **31 307 m**, **0 toques**, curva mais apertada de 80 m (à saída do arco), 14 saltos.
- Falta, mas é desenho e não erro:
  - a B2 ainda vai por 3 túneis (deve ir por fendas abertas; a foto `gc_piloto_fendas_b2` sai preta por ficar
    dentro de um túnel);
  - a B1 tem 1 toque de 9 m em (988, 1541);
  - a foto do slalom não enquadra as torres.
- Próximo passo grande: secção 6 (levar o mundo para o Unreal).

## Estado anterior — 2026-10-19 (fim do dia no PC do trabalho)

Feito hoje no mundo 10 × 8 km (`sculpt_expansion.py`):
- paredes gigantes em degraus (falésias, patamares, taludes);
- **sem agulhas finas**: toda a rocha com menos de 40 m de espessura é removida, e as torres-marco (Spider Rock e
  outras) ficaram grossas (altura até ~1,6 × o diâmetro). O jogador aprovou ("está ótimo");
- o script escreve `world_fields.npz` (H, floor, rocky, slot, slot_floor, canyon_floor, sea, in_core, badlands, ...).
  Com `FIELDS_ONLY=1` no ambiente, para logo a seguir (~3 min a 4 m), para iterar o circuito sem refazer tudo.

### Tarefa 1 (pedida pelo jogador, EM CURSO): GRANDE CIRCUITO pelo mapa todo

**Estado (fim do dia 2026-10-19):** o `Scripts/sculpt_grand_circuit.py` já existe e o **modo planta** funciona:

```
blender -b -P Scripts/sculpt_grand_circuit.py -- C:/rdd/mundo plan
```

Esse comando escreve `gc_plan.png` e mede tudo; com `GC_CROPS="x0,y0,x1,y1;..."` faz também planta ampliada dessas
zonas (`gc_cropN.png`). Precisa de `world_fields.npz` na pasta do mundo, que o passo 4 já escreve.

- **Atualização (fim da sessão):**
  - traçado afinado: volta de **31,3 km**, 0,1 % das curvas abaixo de 210 m de raio e um único toque na rocha
    (10 m, no portal do túnel da mesa);
  - Spider Rock passa a ser contornado por sul e as Mittens no sentido dos ponteiros do relógio;
  - o `relax` passou a reespaçar os pontos a cada passagem: era isso que fechava as curvas;
  - o modo completo (secções 7-12 do script: terreno, tetos, adereços, JSON, fotos de piloto, vistas 3D) **já
    correu bem a 4 m** (ver o passo 4b). Em casa: refazer os passos 1 a 4b a 2 m e mostrar as imagens ao jogador;
  - corrigidos os ~2 000 picos soltos de 4 m que ficavam no mundo e apareciam como cones afiados nas fotos.
    Agora saem no `sculpt_expansion.py` (e também no circuito, para mundos antigos).
  - os valores abaixo são da versão anterior.
- **Resultado anterior (a 4 m):**
  - volta de **30,5 km**, dos quais 7,1 km do núcleo (A + perna sul do D);
  - secções: Hoodoos (slalom), Dunas, Badlands (túnel de 365 m sob a mesa do meio), North_gap, Planalto_Norte (laço a
    norte do Chinle), Chinle (a norte do Spider Rock), Muerto (pelo arco duplo), Monument;
  - ramificações: B1 1,3 km, B2 2,7 km, B3 1,8 km com 3 túneis, B4 Escadaria 4,7 km com 11 saltos (vãos de 50-72 m,
    3 m de descida cada), B5 1,6 km.
- **Já resolvido:** as curvas apertadas do slalom e da entrada das badlands, os toques na rocha (Spider Rock, Chinle,
  Muerto, boca do A_west) e o modo completo.
- **Melhorias sugeridas para casa (mostrar primeiro as imagens ao jogador e perguntar):**
  - o laço **Planalto_Norte** (a norte do Chinle, x 3900-6100) passa por chão aberto e quase plano, e o jogador não
    gosta de descampados. Pode ir antes por fendas verdadeiras entre os blocos do planalto (no
    `debug_world_fields.py`, o azul entre o castanho) ou ganhar ondulação;
  - a B2 (Fendas) tem 2 túneis curtos; podia ir por fendas abertas;
  - nas bordas do chão dos canyons ficam pequenos dentes da resolução de 4 m; a 2 m diminuem e no Unreal o
    material e as rochas por cima escondem-nos.

Pedido: "um circuito maior ainda, a serpentear, túneis, pelo mapa todo, pelos pontos mais importantes, com
ramificações de caminho, saltos de topo, pelas fendas". Volta atual do mapa aprovado: 17,6 km. Meta: **~33-36 km por
volta** (6-7 min a ~330 km/h de média). Assim 3 voltas ≈ 20 min, e volta a "grande expedição".

Fazer num script novo `Scripts/sculpt_grand_circuit.py`, que corre depois do passo 4:
`blender -b C:/rdd/mundo/world.blend -P Scripts/sculpt_grand_circuit.py -- C:/rdd/mundo`. Lê `world_fields.npz`,
`canyon_field.json` e `props.json`. Reaproveitar do `sculpt_canyon_field.py` estas funções: `astar` com `cost_for`
(chão barato, faixa junto às paredes cara, rocha atravessável = túnel), `relax`, `free_sides` (centrar entre paredes),
a deteção de túneis (≥ 20 m de rocha por cima) e os tetos dos túneis (FBX).

**Sentido da volta**: as dunas têm de ser atravessadas **para norte**. Do lado sul das cristas a encosta é suave, e
a norte fica a face de avalanche (33°, 30-50 m): a subir para norte a nave salta da crista; a descer para sul bateria
numa parede. Por isso a ordem é esta (coordenadas do mundo em metros, origem no canto SO, x para este, y para norte;
núcleo aprovado em x 2000-9000, y 0-5000):

1. **Partida no canal A do núcleo**, para este. O A do JSON já vem de oeste para este, com os seus túneis e a reta
   pela montanha.
2. Perna sul do D (dunas do núcleo, corredor y ≈ 1550) para este, até x ≈ 8400.
3. **Slalom entre as 9 torres (hoodoos)** do fim das dunas, para norte, de y 1300 a 2950. As posições estão em
   `landmarks.hoodoos`; pontos de passagem alternados 70 m a oeste e a este de cada torre; raio mínimo 70 m.
4. **Mar de dunas para norte** em x ≈ 9300, de y 2950 a ~4800: saltos nas cristas. Rota de superfície, sem escavar.
5. **Badlands para oeste** (y ≈ 5500-5800), entre as mesas e as suas saias de ravinas, até ao North_gap
   (6450, 5800).
6. North_gap para norte até ao **Chinle** (6500, 6550). Depois o Chinle para oeste: chão verde, rio, passa ao lado
   do **Spider Rock** (≈ 3700, 6600), até à junção com o Muerto (1250, 6600).
7. **Muerto para sul** (canyon gigante com meandros), a passar pelo **arco duplo** gigante a 35 % do Muerto (adereço
   `SM_Kit_Arch` à escala 3,2: ver se a pista cabe por baixo).
8. **Planície do Monument Valley**, em S entre as mesas: (140, 1260) → (190, 720) → (560, 330) → (1250, 560) →
   (1750, 1080) → ponta oeste do A (2023, 1500). Fecha a volta.

Ramificações (todas voltam à principal):
- **B1 atalho A_west**: do Muerto (≈ 900, 1600) pelo canyon A_west direto à ponta do A (salta a planície).
- **B2 Fendas**: sai do Chinle no Spider Rock, desce o canyon Monument até ≈ (3300, 5600) e vai para oeste pela rede
  de fendas (chão azul no mapa de depuração; troncos de 20-60 m). Volta ao Chinle em x ≈ 2300. Largura mínima 12 m,
  raio mínimo 60 m.
- **B3 Túnel do Muerto**: do Chinle (2300, 6350), uma reta ("S") até ao Muerto (1000, 5300), em túnel pelo planalto.
- **B4 Rota alta / Escadaria**: blocos de topo plano NOVOS em fila para oeste, cada um 3 m mais baixo que o anterior
  (vãos de 35-60 m = saltos). Entra-se por uma rampa de areia (duna encostada, H = max, nunca escava; ~9-10°) e
  sai-se por outra rampa, que volta à principal perto do North_gap. Faixa candidata: y ≈ 5750-5850, a norte das mesas
  das badlands, entre x 9600 e 7200, fora do núcleo (y > 5000). Confirmar no mapa de depuração que ali há chão livre.
- **B5 Planície de cascalho**: em x ≈ 9880, plana e rápida, em alternativa aos saltos das dunas.

Larguras: principal 36 m (mínimo 22 m), raio mínimo 150 m; fendas 20 m (mínimo 12 m).

Regras: a pista **nunca destrói** o mapa. Nas rotas de superfície nada é escavado. Onde há rocha, vai em túnel
(heightfield aberto só debaixo do teto, como no núcleo). As rampas e os blocos só acrescentam terreno. Tirar das
pistas as rochas e plantas do `props.json` (largura + 6 m).

Saídas: `grand_circuit` no JSON (pontos, comprimento, ramificações com onde saem e entram, túneis, saltos, rampas,
verificação de velocidade); `tunnels_gc/*.fbx`; planta; vistas 3D no estilo do `render_world_3d.py` com as fitas das
rotas; e fotos de piloto (Spider Rock, arco do Muerto, fendas, salto da escadaria, salto de duna, slalom, entrada de
túnel).

### Tarefa 2: o mapa maior da outra IA (gerado a 18 de outubro)

O jogador tem um mapa **maior** que o nosso, gerado por outra IA a 2026-10-18, e quer juntá-lo ao nosso.
**Não é** o S01 da Fase 2c (c8fedc8, 6 × 6 km; ele confirmou). Ele vai mostrá-lo, ou faz a junção em casa.
Ideia guardada: o nosso mundo de 10 × 8 km como Landscape no Unreal, com as rochas, plantas e materiais da 2c por
cima. `Scripts/compare_maps.py` compara dois mapas à mesma escala (vista de cima e 3D lado a lado).

### Tarefa 3 (só quando o jogador disser): modo de corrida de sobrevivência e nave nova

- Modo de corrida estilo evento Eliminator do Forza: equipas espalhadas pelo mapa a uma distância segura; um portão
  aparece aleatoriamente no minimapa e é preciso atravessá-lo vivo ("portão 3 de 20"). No fim recolhem-se os
  espólios (ainda por definir).
- Equipas de 3 membros com 2 naves: o 3.º membro teleporta-se entre as duas naves e dispara contra os inimigos (como
  no anime Oban Star-Racers). Para isso é precisa uma **nave nova com posto de artilheiro**, a desenhar segundo a
  Bíblia V2 / Prompt Mestre das naves (PDFs do jogador). Fase A: 3 propostas de silhueta.

### 6. Depois: levar para o Unreal (próximo passo combinado)

1. Importar `world_height16.png` como Landscape (Z scale no `canyon_field.json`, campo `heightmap_note`).
2. **Material do Unreal com texturas**: estratos, fissuras e grão da rocha nas paredes, ondulações na areia,
   usando a máscara (`canyon_field_mask.png`: R inclinação, G detritos, B camada). É isto que tira o aspeto
   "plasticina / serrilhado" que o jogador notou nas imagens do Blender.
3. **Rochas e plantas por cima**: colocar as peças do `props.json` (malha, posição, rotação, escala) como
   instâncias (Nanite para rochas); cones de pedregulhos e lascas nas paredes pela máscara de detritos.
4. Tetos dos túneis (`tunnels/*.fbx`) como malhas estáticas; o circuito (`circuit.points`) como spline de rota.

## Regras e decisões do jogador (não desfazer)

- **A pista nunca destrói o mapa**: washes só no chão; onde atravessam uma mesa vão em túnel; no máximo cortes
  pequenos e subtis.
- **Circuito misturado** (escolha dele): o circuito sinuoso com curvas de drift — as naves vão a 450 km/h, mas
  não sempre, de propósito — mais **duas retas que atravessam a montanha** (wash A a sul e a diagonal R). Rejeitou
  o circuito todo desenhado em vales largos (perdia o carácter).
- **Mesas de alturas variadas**: baixas, médias e torres até ~90 m; topos inclinados que servem de rampa para
  subir; topos em patamares para saltar de topo em topo; caminho livre por cima.
- **Vegetação**: nada de colisão (bater num arbusto a alta velocidade não faz sentido).
- **Mundo de 10 × 8 km**: o mapa aprovado fica intacto no centro-sul; canyons gigantes a oeste e norte (estilo
  Canyon de Chelly / Spider Rock e Monument Valley, as aéreas que ele deu como melhor exemplo), nascendo a crescer a
  partir do mapa atual; **fendas** ramificadas onde se pode conduzir (gostou muito); **nada de chão plano** nas
  zonas novas (ondulações grandes e pequenas, alguns trechos retos); dunas a terminar a leste numa planície de
  cascalho com pedras escuras e torres.
- **Sem agulhas finas a apontar para o céu**; as paredes descem em degraus com saliências e rachaduras pequenas
  (2-5 m), não em quedas a pique até ao chão.
- Mostrar imagens a cada passo; pedir confirmação antes de fazer push.
