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
- Mostrar imagens a cada passo; pedir confirmação antes de fazer push.
