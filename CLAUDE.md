# Extracting Stardust — notas para a IA (ler primeiro)

Jogo de corrida de naves antigravidade (Unreal Engine, `ExtractingStardust.uproject`). O mapa **Red Dust Divide**
é gerado por scripts do Blender em `Scripts/`; a explicação completa está em `Docs/ESTUDO_BLENDKIT_CANYONS.md`
(secções 5 a 12) e o plano do setor S01 em `Docs/MAPA_01_RED_DUST_DIVIDE_S01.md`.

O jogador fala português (PT). Responder em português.

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

### 5. Fotos e planta (opcional, para mostrar ao jogador)

```
blender -b C:/rdd/mundo/world.blend -P Scripts/render_route_plan.py -- C:/rdd/mundo
blender -b C:/rdd/mapa/canyon_field.blend -P Scripts/render_ships.py -- C:/rdd/mapa <strix.fbx>
```

O `strix.fbx` está no branch `main`: `ExtractStardustRDD/Assets/ExtractStardust/Vehicles/V2/Chassis/Resources/V2Chassis/strix.fbx`.
Mostrar as imagens ao jogador (ele pede fotos com frequência: vista de cima, geral, piloto, naves).

Vistas 3D do mundo inteiro (cores por altura, circuito a laranja; o jogador **gostou muito deste estilo**):

```
blender -b -P Scripts/render_world_3d.py -- C:/rdd/mundo
```

Mapa de depuração (rocha, chão dos canyons, fendas, dunas, grelha de 500 m) para escolher pontos de passagem:

```
blender -b -P Scripts/debug_world_fields.py -- C:/rdd/mundo/world_fields.npz C:/rdd/mundo/canyon_field.json C:/rdd/mundo/dbg.png
```

## CONTINUAR AQUI — estado em 2026-10-19 (fim do dia no PC do trabalho)

Feito hoje no mundo 10 × 8 km (`sculpt_expansion.py`):
- paredes gigantes em degraus (falésias, patamares, taludes);
- **sem agulhas finas**: toda a rocha com menos de 40 m de espessura é removida, e as torres-marco (Spider Rock e
  outras) ficaram grossas (altura até ~1,6 × o diâmetro). O jogador aprovou ("está ótimo");
- o script escreve `world_fields.npz` (H, floor, rocky, slot, slot_floor, canyon_floor, sea, in_core, badlands, ...).
  Com `FIELDS_ONLY=1` no ambiente, para logo a seguir (~3 min a 4 m), para iterar o circuito sem refazer tudo.

### Tarefa 1 (pedida pelo jogador, começada mas NADA gerado ainda): GRANDE CIRCUITO pelo mapa todo

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
