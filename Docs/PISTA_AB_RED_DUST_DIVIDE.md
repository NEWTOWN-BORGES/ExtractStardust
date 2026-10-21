# RED DUST DIVIDE — Expedição de A a B (10-12 minutos)

Gerada por `Scripts/sculpt_expedition_ab.py`. Este documento explica o desenho; os números finais saem do script
(log e `ab_route.json`).

## Porquê uma pista nova

O mundo de 10 × 8 km parecia ótimo visto de cima, mas dentro do jogo era "enorme mas vazio":
- canyons largos e planos, com as paredes longe da nave;
- a pista era só uma fita no chão;
- o horizonte era infinito, sem um sítio onde se olha e se diz "uau, é ali".

A expedição de A a B é um **mundo fechado**: a pista corre sempre entre rocha e o horizonte fecha-se com falésias e
cordilheiras. Antes, a pista de 20 minutos era tão longa que as IAs morriam a meio. Esta tem **10-12 minutos**.

## Regras seguidas

Do GDD (`01_Mapas_Pistas_Expedicoes`, secções 16-19):
- **A geologia é a pista:** superfícies naturais, sem alcatrão nem rails.
- **Larguras do GDD:**

  | Zona | Largura |
  |---|---|
  | Partida | 30-38 m |
  | Aberta | 24-35 m |
  | Principal | 14-24 m |
  | Técnica | 10-16 m |
  | Atalho SKILL | 5-12 m |

- **Raios de curva:** fechada 60-120 m, média 120-250 m, rápida 250-500 m, mega-arco 500 m ou mais.
- **Perfis:** curvas inclinadas naturais (a Red Wall sobe de 8° a 50°), half-pipe no Wash, cavernas com câmara.
- **Bifurcações:** SAFE, RACING e SKILL, cada uma com propósito.
- **Saltos naturais e legíveis:** o piloto vê a receção antes de saltar.
- **Ritmo:** um momento marcante a cada 30-60 s.

Do estudo de desenho de pistas:
- nenhuma curva logo a seguir a uma lomba;
- marcos ao longe para orientação;
- intensidade a subir, com zonas de recuperação.

Do jogador:
- 450-550 km/h nas zonas rápidas e curvas apertadas a ~200 km/h;
- canyons gigantes com fendas e bifurcações entre elas;
- mistura de canyon e deserto;
- túneis, saltos gigantes e pequenos;
- **nada de agulhas finas**;
- **nada de chão plano e vazio**.

## Geologia (Canyonlands)

O mundo tem 16 × 12 km e três andares:
- **Planalto** (Island in the Sky) a ~450 m, com domos de Navajo e mesas.
- **Patamar do White Rim** a ~240 m, claro, com promontórios, reentrâncias e mesas isoladas. Fica entre o planalto e
  o patamar uma falésia em degraus.
- **Fundo do canyon** a 20-40 m, com uma garganta de ~200 m de parede em degraus entre o patamar e o fundo.

Fendas cortam o patamar. A sudoeste há uma bacia de deserto (dunas, arcos, torres e mesas ao estilo do Monument
Valley), fechada por falésias. À volta do mundo, cordilheiras mais altas fecham o horizonte.

## Setores (linha principal; tempos do modelo de velocidade ideal)

| Setor | Tempo | Km | O que é | Bifurcação | Saltos |
|---|---|---|---|---|---|
| S1 The Basin | 0:00-1:24 | 8,0 | Partida (grelha 5 × 4) numa bacia larga do planalto; leito natural entre domos e mesas | — | 3 de fluxo (lábios de laje) |
| S2 Broken Mesa | 1:24-2:37 | 6,3 | Lajes partidas e inclinadas; termina na borda com a vista do canyon | SKILL Lajes (9 saltos de laje em laje) | 2 degraus |
| S3 Shafer Fall | 2:37-3:37 | 5,8 | Descida em ziguezague (4 lances, 3 curvas em U de ~120 km/h) até ao patamar | — | — |
| S4 The Red Wall | 3:37-4:22 | 6,7 | Afluente que nasce no patamar e escava até ao fundo numa curva longa; a parede exterior inclina 8° → 50° | — | 2 cascatas secas grandes |
| S5 Fendas | 4:22-5:06 | 4,1 | Fundo do canyon gigante a passar as fendas | RACING Fenda Larga; SKILL Fenda Estreita (degrau de 7 m) | — |
| S6 Horseshoe | 5:06-5:46 | 4,9 | Curva de 270° à volta do esporão de rocha | SKILL Istmo: fenda pelo istmo e salto de queda | — |
| S7 The Wash | 5:46-6:50 | 6,0 | Leito seco em half-pipe | — | 3 degraus |
| S8 The Hollow | 6:50-7:29 | 3,1 | Caverna: entrada larga, câmara, bifurcação, claraboias, saída a 12 m acima da bacia | Braço da Caverna | salto de saída |
| S9 Arches Run | 7:29-9:03 | 8,5 | Deserto: slalom de torres, três arcos sobre a pista, dunas atravessadas (saltos de crista) | SKILL Arcos | ~10 de duna |
| S10 White Rim | 9:03-9:42 | 5,2 | Subida ao patamar; corrida na borda com a bacia lá em baixo; salto-herói sobre uma ravina; meta B no Mesa Arch | SAFE Contorno (à volta da ravina) | salto-herói |

O total ideal é 58,6 km em 9:42 (média de 362 km/h). Com saltos, travagens e pilotos reais deve dar 10:30-11:30.

## Estradas largas para 16-20 naves (2026-10-21)

O jogador quer 15 a 20 naves lado a lado, 6 ou 7 de frente. A linha principal passou a 56-64 m de largura (semi-largura
28-32 m, antes 10-28), a partir de S1 até S10: S3 Shafer Fall (os 4 lances em zigue-zague) fica com 40 m, por causa
dos cotovelos de 43 m de raio. O túnel The Hollow tem 56 m de chão. As bifurcações RACING e SAFE ficam com 48 e 52 m;
**os atalhos SKILL ficam estreitos de propósito** (12-18 m). A grelha de partida passa a 3 filas de 6 (18 lugares)
em vez de 4 de 5. O traçado e os tempos não mudam (59,0 km, 9:44).

## Túnel e paredes lisas (2026-10-21)

O jogador achou o túnel "horrível, impossível conduzir": as paredes tinham placas e triângulos salientes. Corrigido em
`Scripts/sculpt_expedition_ab.py`:
- **The Hollow é um arco liso**, de meia elipse, com 22-28 m de altura livre no meio. O semi-largura do chão passou de
  14 para 22 m (braço da caverna de 10 para 16 m). As paredes e a abóbada são a malha do teto (`caves/*.fbx`), de uma
  só peça; o chão do túnel é só chão, ao nível da borda da pista. Um heightfield não faz uma parede íngreme limpa (os
  triângulos veem-se como cunhas), por isso o arco é que faz as paredes.
- **Nada de rochas no túnel nem ao lado dele** (120 m): os adereços ficam de fora.
- **Rochas afastadas da pista:** faces de falésia, blocos de talude, pedras, lajes e barbatanas ficam pelo menos 30 m
  (`TRACK_CLEAR`) para lá da borda da pista, por isso as paredes junto à linha ficam lisas.
- `AB_ONLY=08_caverna,07_wash` (variável de ambiente) tira só essas fotos de piloto, para testar sem esperar pelas
  doze.

Falta, no PC com o Unreal: ver o túnel dentro do jogo (as claraboias da caverna são aberturas na malha do teto).

## Gerar

```
blender -b -P Scripts/sculpt_expedition_ab.py -- <pasta> <metros> kit=<kit> plants=<plantas> ship=<strix.fbx>
```

- **Valores de `<metros>`:** 5 para iterar, 4 no PC do trabalho, **3 no PC de casa**.
- **`plan`:** só traçado e tempos (segundos).
- **`noshots`:** terreno, planta com relevo e ficheiros para o Unreal, sem fotos (~3 min a 5 m).

O kit, as plantas e a nave vêm de `sculpt_rock_kit.py`, `sculpt_plants.py` e do `strix.fbx` (branch `main`).

## Saídas

| Ficheiro | O que é |
|---|---|
| `ab_height16.png` | Mapa de alturas de 16 bits (`z_m` no JSON) |
| `ab_mask.png` | R = inclinação, G = pista, B = camada (bacia/fundo, patamar, planalto, falésia), para o material |
| `ab_route.json` | Pista principal (ponto a cada 4 m, com largura, inclinação, setor e velocidade), ramificações, saltos, lábios, marcos e grelha de partida |
| `ab_props.json` | Arcos, rocha equilibrada, Mesa Arch, pedras, zimbros, mato e troncos |
| `caves/*.fbx` | Tetos da caverna The Hollow (com claraboias) |
| `expedition.blend` | A cena completa |
| Imagens | `ab_relief.png` (planta) e `ab_NN_*.png` (fotos de piloto por setor, com a nave à escala) |

## Vestir o mapa: rochas e plantas

Usa todos os moldes que já temos, juntos numa pasta (`molds=`):
- **O nosso kit:** 14 peças.
- **As rochas esculpidas da Fase 2b:** falésias, mesas, butte, espigões e pedregulhos.
- **As peças do S01:** ilha, mesa com arco e lajes.

As plantas vêm do `sculpt_plants.py`, que já fazia zimbros, choupos, salgueiros, mato, yucas e figo-da-índia, e agora
faz também saguaro, cacto-barril, cholla, árvore-de-josué e árvores mortas.

Cada cópia leva tamanho, rumo, inclinação e escala ligeiramente desigual próprios, fica um pouco enterrada, e
**nunca fica em cima de uma pista**.

| Zona | O que leva |
|---|---|
| Paredes vistas da pista | Falésias (`SM_Cliff_*`) encaixadas no pé da parede, viradas para a pista e com a altura ajustada à parede, para as paredes deixarem de parecer lisas |
| Taludes | Grupos com um bloco grande (pedregulho gigante, bloco fraturado, saliência, rocha-mesa) e 2-6 pedras à volta |
| Chão | Pedras soltas |
| Patamar e planalto | Lajes deitadas segundo o declive do terreno, torres empilhadas, rochas-mesa, zimbros e árvores mortas |
| Deserto | Barbatanas em fila (como as juntas do arenito), saguaros, árvores-de-josué, cholla, cacto-barril, figo-da-índia, yucas, árvores mortas e troncos |
| Fundo dos canyons | Choupos junto ao Wash, troncos, mato e figo-da-índia |
| Ao longe | Mesas, buttes e espigões; os espigões vão alargados, sem agulhas |

### Zonas verdes

- **Prados no fundo dos canyons** (ao estilo do Canyon de Chelly): no canyon principal (Fendas, Ferradura, Wash e a
  montante) e no fundo da garganta da Red Wall, até ~16 m acima do chão, aos retalhos. Têm relva, salgueiros e
  choupos.
- **Enseadas:** a cada ~1,5 km o fundo do canyon principal alarga 60-130 m durante umas centenas de metros, e são as
  enseadas que levam os prados maiores, dos dois lados da pista. Depois o canyon volta a apertar, alternando
  espaços gigantes com passagens apertadas, como pede o GDD (18.1).
- **Oásis no deserto:** uma nascente com lago ao lado da pista, antes do slalom das torres, mais duas nascentes
  pequenas no pé das falésias da bacia, cada uma com o seu lago, relva, choupos e salgueiros.
- **Na pista:** nenhuma; o leito fica de areia e cascalho.
- **Para o Unreal:**
  - `ab_green.png`: máscara de 8 bits (255 = prado), para a camada de relva e a densidade de folhagem;
  - `water` no `ab_route.json`: os lagos, com centro, altura e raio, para pôr Water Bodies.

O `ab_props.json` leva a rotação XYZ em graus e a escala por eixo. O importador do Unreal tem de as aplicar
(trocando o sinal do y, porque o Unreal usa outro sentido para esse eixo).

## No Unreal (o jogador veste)

- **Terreno:** Landscape com o `ab_height16.png`. Material por inclinação e altura, calculado no shader (não pintado
  aos blocos, que dava os "adesivos quadrados"), com a máscara para as camadas.
- **Rochas e plantas:** os Megascans do jogador por cima, colocados pelo jogador.
  - Desert Western Cliff Layered nas paredes da garganta e na falésia do planalto;
  - Rock e Rock Sandstone nos taludes;
  - Large Fallen Tree e Old Tree Branch no Wash.
  Os scripts podem usá-los pelo nome e caminho no projeto, mas os ficheiros não passam pela IA, porque a licença
  deles proíbe o uso com IA.
- **Céu:** o céu de 8K do jogador.
