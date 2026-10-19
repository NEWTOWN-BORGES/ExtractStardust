# Estudo: 10 terrenos do BlendKit (referência para recriar no Red Dust Divide)

Baixados a 2026-10-19 na versão 1K (BlendKit, todos **grátis** e **Royalty Free**: podem entrar no jogo
compilado, não podem ser redistribuídos soltos). Abertos no Blender 4.5 com scripts desligados e medidos por
`analyze_terrain.py` (área por inclinação, plataformas planas por altura, materiais, heightmap e relevo sombreado).

Decisão do jogador: **recriar o nosso próprio**, usando estes modelos como estudo.

## 1. Os 10 modelos

| Modelo | Autor | Tamanho (m) | Faces | O que tem de útil | Serve para |
|---|---|---|---|---|---|
| [Canyon Desert Landscape](https://www.blendkit.com/asset-gallery-detail/edf789a1-964e-4480-86a0-ac3a1205f55e/) | EB Adventure Photoscans | 1338 × 1338 × 80 | 572 k | campo de **mesas e buttes** com paredes verticais caneladas e chão de areia entre elas | **S01 The Basin**, Broken Mesa |
| [Eroded Canyon Terrain](https://www.blendkit.com/asset-gallery-detail/224c447a-3f65-47bd-bd5c-e45bdf316b84/) | Bipro Fx | 1500 × 1500 × 188 | 145 k | **canyon escavado** num planalto: topo plano, paredes íngremes, fundo sinuoso | **S02 The Red Wall**, descida do S01 |
| [Sandstone Island Terrain](https://www.blendkit.com/asset-gallery-detail/4a532445-a7cd-43fd-95ad-ae06378fc94b/) | GLADIATOR ALE GATOR | 4096 × 4096 × 1140 | 1,0 M | **butte-ilha** gigante a sair de planície plana | butte-ilha (bifurcação 1), horizonte |
| [Sandstone Cliffs](https://www.blendkit.com/asset-gallery-detail/37caa53b-2c45-470a-9b9d-a1aacaf7e343/) | GLADIATOR ALE GATOR | 4096 × 4096 × 1059 | 1,0 M | **escarpa** contínua (planície a 0 m, topo a 840–930 m) | escarpa a leste, limites naturais |
| [Sandstone Cracks Terrain](https://www.blendkit.com/asset-gallery-detail/ffb1d299-a6ec-4853-93d2-044d85ec9c38/) | GLADIATOR ALE GATOR | 4102 × 4096 × 573 | 1,0 M | planalto **rachado em fendas** largas | S03 The Wash, fendas |
| [Desert Sandstone Dunes](https://www.blendkit.com/asset-gallery-detail/53b58dba-a1e5-410c-b48c-83e9c9864de5/) | GLADIATOR ALE GATOR | 4096 × 4096 × 412 | 1,0 M | arenito ondulado em **degraus** (bancadas a cada ~17 m) | bancada Kayenta, lajes partidas |
| [Eroded Ridge Terrain](https://www.blendkit.com/asset-gallery-detail/b87cfaf0-f78d-452f-93e0-52461350c941/) | Bipro Fx | 1500 × 1500 × 208 | 158 k | cristas com **ravinas de erosão** (pouca falésia) | encostas de Chinle |
| [Sand Dunes with Rocky Cliffs](https://www.blendkit.com/asset-gallery-detail/3eb2a9de-2901-42b8-991a-be491dcedf27/) | EB Adventure Photoscans | 198 × 198 × 20 | 1,5 M | dunas a encostar em rocha (pequeno, muito detalhe) | transição duna → rocha |
| [Dunes by the lake](https://www.blendkit.com/asset-gallery-detail/7bb55b89-1483-453f-a046-868be067ac8f/) | EB Adventure Photoscans | 4096 × 4096 × 488 | 653 k | mar de dunas (76 % plano) + lago | mar de dunas a oeste/sul (sem o lago) |
| [Desert Procedural](https://www.blendkit.com/asset-gallery-detail/80db9f4e-cc39-4613-9457-6d7a35ac17bd/) | Ibrohim Toxirov | 203 × 200 × 8 | 637 k (Geometry Nodes) | **material de areia** (ondas + ruído) e erva espalhada por nós | material de areia com ondulações |

## 2. O que as medições mostram

Inclinação, em % da área de cada terreno:

| Modelo | Plano 0–10° | Suave 10–25° | Detritos 25–45° | Íngreme 45–70° | Falésia 70°+ |
|---|---|---|---|---|---|
| Canyon Desert Landscape | 32 | 30 | 14 | 12 | **12** |
| Eroded Canyon | 45 | 20 | 17 | 15 | 3 |
| Sandstone Island | 51 | 10 | 11 | 19 | **9** |
| Sandstone Cliffs | 48 | 20 | 12 | 17 | 3 |
| Desert Sandstone Dunes | 33 | 41 | 16 | 10 | 1 |
| Eroded Ridge | 33 | 41 | 20 | 5 | 0 |

**Lições para a nossa geologia:**

1. **Plano ou vertical, pouco no meio.** Os bons canyons têm ~⅓ a ½ da área plana (chão e topos) e ~¼ íngreme
   ou falésia; as encostas de 25–45° são só os **cones de detritos** no pé das paredes. É isto que dá a leitura
   "Utah": topo plano → parede → rampa de detritos → chão. As nossas regras do S01 (Wingate vertical, Chinle mole
   por baixo, detritos em cone) estão certas; falta **mais área de falésia verdadeira** (>70°).
2. **Bancadas a alturas fixas.** As plataformas planas aparecem em degraus regulares: Canyon Desert a 10, 14 e
   17 m; Desert Sandstone Dunes a cada ~17 m; Eroded Canyon com 35 % da área no planalto a 172–180 m. Cada
   camada dura deixa uma bancada. → Gerar o relevo como **soma de camadas** com cotas fixas (Kayenta, Wingate,
   Navajo), não como ruído contínuo.
3. **Paredes caneladas.** As falésias das mesas têm **sulcos verticais** (erosão da água a escorrer), não
   estrias horizontais. Isto confirma a regra da Fase 2c: "sem estrias, sem bojos derretidos".
4. **Topos irregulares, bordas recortadas.** No relevo sombreado, cada mesa tem um contorno com reentrâncias
   e "dedos" (planta de mesa = forma recortada, nunca círculo ou retângulo), e o topo tem pequenas ondulações.
5. **Escala.** O campo de mesas tem 1,3 km e as mesas 40–70 m de altura: a 450 km/h atravessa-se em ~10 s.
   Para o setor (~1:10), precisamos de **várias zonas destas encadeadas** ou de as escalar ×1,5–2.

## 3. Como foram feitos (e como recriamos)

Os 4 terrenos do GLADIATOR ALE GATOR e os 2 da Bipro Fx são **heightmaps de 4096 px exportados de um
gerador de erosão** (texturas `Height Map`, `ColorErosion`, `Slope`, `AO` típicas do Gaea / World Machine).
O Canyon Desert Landscape usa as mesmas máscaras (`ColorErosion_Out`, `Slope_Out`) mais texturas de rocha
digitalizada. O material é sempre: **cor guiada pela máscara de erosão + mistura rocha/areia pela
inclinação**.

Receita para o nosso gerador (Blender, `sculpt_rocks.py` / `FEXDesertTerrain`):

1. **Camadas com cota fixa** (terraces): `altura = soma de degraus suavizados por camada`, cada camada com a
   sua dureza (já temos a tabela Navajo 0,85 / Kayenta 0,60 / Wingate 0,97 / Chinle 0,15).
2. **Contorno das mesas** por ruído de domínio deformado (domain warp) sobre a máscara da camada, para as
   bordas recortadas com dedos e reentrâncias.
3. **Erosão térmica** (material solto escorre até ao ângulo de repouso ~33°) → cria os cones de detritos no
   pé das paredes sem tocar no topo.
4. **Erosão hidráulica leve** (gotas que escavam) só nas paredes → sulcos verticais (caneladura).
5. **Máscaras exportadas** com o heightmap: inclinação, fluxo de água (erosão), deposição. O material do
   Unreal usa-as: areia onde é plano/deposição, rocha estratificada onde é íngreme, verniz escuro nas
   linhas de fluxo.

Primeiro alvo: recriar o **Canyon Desert Landscape** à nossa escala como a zona da Bacia do S01, e comparar
as nossas medições com a tabela acima (meta: falésia 70°+ ≥ 10 %, plano 30–45 %).

## 4. Ficheiros

Os `.blend` (1K, ~330 MB no total) **não vão para o repositório**. Para voltar a baixar: abrir os links da
tabela com o add-on BlendKit no Blender, ou pedir ao Claude para os baixar pela API pública (grátis, sem login).

## 5. Protótipo: `Scripts/sculpt_canyon_field.py` (2026-10-19)

Primeiro gerador com a receita da secção 3, independente da pipeline atual (não mexe no mapa nem no Unreal).
Gera um campo de mesas de **2 × 2 km** (1024 × 1024 amostras a 2 m, o mesmo espaçamento do `FEXDesertTerrain`)
em ~1,5 min no PC do trabalho:

```
blender -b -P Scripts/sculpt_canyon_field.py -- <pasta_saida> [seed] [amostras]
```

Saídas: heightmap 16 bits (importação de Landscape no Unreal), máscara (R inclinação, G detritos, B camada),
`.blend` com a malha colorida e duas imagens (vista alta e vista do piloto a 4 m do chão).

O que faz: campo de massa rochosa com domain warp (contornos recortados), juntas que partem as mesas em
blocos, caneluras com profundidade variável, bancadas da Kayenta, parede de Navajo em dois andares onde há
recuo, borda arredondada, topos com fendas, detritos a 33° com pedregulhos, cores por camada (estratos,
banda clara sob a borda, verniz escuro, manchas de slickrock no chão) e céu físico com sol baixo.

Medições (seed 7, 2 km), comparadas com o Canyon Desert Landscape:

| | Plano | Suave | Detritos | Íngreme | Falésia 70°+ |
|---|---|---|---|---|---|
| BlendKit | 32 | 30 | 14 | 12 | 12 |
| Protótipo | 46 | 19 | 21 | 4 | **10** |

O chão fica de propósito mais plano do que a referência: é onde se corre a 450 km/h.

Próximos passos: importar o heightmap no Unreal como Landscape e voar por ele; material do Unreal a ler a
máscara (o detalhe fino de estratos e verniz vai para a textura, não para a cor por vértice); encaixar a rota
do S01 (bacia de largada aberta, butte-ilha na bifurcação) definindo zonas obrigatórias no campo de rocha.

## 6. Kit de rochas: `Scripts/sculpt_rock_kit.py`

Inspirado em 9 modelos do BlendKit (7 grátis baixados e estudados; 2 pagos só como referência visual):
Rocks, Big Flat Rock, Rock Cliff Overhang, Rugged Coastal Rock, Rock Rugged Arch Formation, Stylized Rough
Landscape Rock, Drainage Ditch (CC0) e os pagos Desert Rugged Arch Rock / Desert Rugged Rock Formation.
Nenhum é de canyon de arenito: recriamos as formas com a nossa geologia (camadas de arenito, juntas, cor do Utah).

```
blender -b -P Scripts/sculpt_rock_kit.py -- <pasta_fbx> <prefixo_preview>
```

14 peças, um FBX cada (pivot no chão), ~4 min no PC do trabalho:

| Classe | Peças |
|---|---|
| Pequenas | `SM_Kit_Stone_1..4` (0,6–3,9 m, blocos partidos e gastos), `SM_Kit_FlatSlab` (laje em duas camadas) |
| Gigantes | `SM_Kit_Overhang` (lasca com ressalto, 6 m), `SM_Kit_FracturedBlock` (bloco estratificado), `SM_Kit_Boulder_Giant` (8 m) |
| Mega | `SM_Kit_Arch` (arco de 16 m), `SM_Kit_StackedTower` (13 m), `SM_Kit_TableRock` (rocha-mesa com chapéu), `SM_Kit_Fin` (lâmina de 14 m, como em Arches) |
| Madeira seca | `SM_Kit_DeadLog` (tronco caído, 7,7 m), `SM_Kit_DeadSnag` (árvore morta de pé, 5,4 m) |

Método: volumes simples → remesh voxel → fraturas por planos (`rock_lib.fracture`) → camadas de arenito
irregulares (cada camada com o seu ressalto, trechos maciços sem camadas) → erosão, juntas e grão → decimate.
Madeira: esqueleto + modificador Skin, veio esticado ao longo dos ramos. Detalhe fino fica para as texturas.

## 7. Rede de drenagem, circuito e túneis (em `sculpt_canyon_field.py`)

Regra do jogador: **a pista não destrói o mapa.** Os washes só escavam o chão aberto (3–4 m de fundo, margem
íngreme com 2 ressaltos no lado de fora das curvas, margem suave no de dentro, como no "Drainage Ditch").
Onde um wash atravessa uma mesa, passa num **túnel**: o terreno abre só o chão e uma peça à parte
(`SM_Tunnel_*.fbx`) repõe o topo da mesa por cima, com abóbada natural (16 m livres no meio). Cortes em mesas
só onde não há outra hipótese, estreitos (no seed 7: 4 toques de 6–17 m).

- Traçado por A* sobre o chão (como a água): caro junto às paredes, por isso os washes ficam afastados das
  mesas e atravessam-nas a direito; depois centram-se na passagem e estreitam (até 16 m) onde ela aperta.
- Rede (seed 7): wash sul A e norte B, ligados a oeste pelo afluente C e a leste pela depressão D (fora da
  drenagem, com rampa ao sair e ao voltar a entrar); braço E (rota alternativa à volta de uma ilha);
  afluentes G e H a entrar pelas bordas. 8 túneis.
- **Circuito: 4,5 km por volta** (A → D → B → C). Pontos a cada 8 m no `canyon_field.json` (`circuit`),
  junto com a rede (`network`), túneis e cortes.
- `Scripts/render_route_plan.py` desenha a planta dos trajetos por cima do terreno.

## 8. Notas para o PC de casa (próximo passo, quando o terreno entrar no Unreal)

1. **Material do Unreal com texturas**: estratos, fissuras e grão da rocha nas paredes, e ondulações na
   areia, usando a máscara que o gerador já exporta (`canyon_field_mask.png`: R inclinação, G detritos,
   B camada).
2. **Rochas esculpidas por cima**: as rochas Nanite que já fizemos (e o kit novo), como cones de
   pedregulhos e lascas nas paredes, colocadas pela máscara de detritos.
3. Importar `canyon_field_height16.png` como Landscape (Z scale no `canyon_field.json`), os tetos dos
   túneis como malhas estáticas e o circuito como spline de rota.

## 9. Mapa grande: canyon de 5 km + mar de dunas de 2 km

```
blender -b -P Scripts/sculpt_canyon_field.py -- <saida> 7 7000x5000 4 5000 <pasta_fbx_do_kit>
```

(7 × 5 km, 4 m por ponto neste PC; em casa usar 2 m: `... 7000x5000 2 5000 ...`). O mapa de 2 km continua a
sair com `-- <saida> 7 1024`.

- **Canyon (oeste, 5 km)**: as mesmas regras de geologia; perto do mar de dunas as mesas rareiam e ficam como
  ilhas meio enterradas na areia (rampas de areia contra as paredes).
- **Mar de dunas (leste, 2 km)**: vento de sul → dunas transversais compridas com cristas este-oeste que se
  partem a cada ~1 km; rampa a sul côncava (fica mais íngreme no topo) e face de deslizamento a norte (~30°):
  quem conduz para norte sobe a rampa e salta na crista (saltos e acrobacias). Cristas de 15–35 m, a ~320 m
  umas das outras; dunas pequenas de ~2 m por cima. Dois corredores baixos este-oeste para as pernas da volta.
- **Rede e circuito**: washes A (sul), B (norte), M (meio), ligações C (oeste) e K, braços E e F, afluentes
  G e H. A volta sai do canyon pelo wash A, faz um laço nas dunas (D: corredor sul para leste, subida para
  norte a saltar as cristas, corredor norte para oeste), volta pelo wash B e fecha pelo C.
- **Esculturas no mapa** (kit da secção 6): pedras e lajes nos cones de detritos, blocos gigantes no pé das
  paredes, rochas mega como marcos no chão aberto, mega meio enterradas na transição para as dunas, troncos e
  árvores mortas nas margens dos washes; nada a menos de 30 m de uma rota. Colocações em `props.json`
  (malha, posição, rotação, escala) para o Unreal; no `.blend` entram como instâncias.

Resultado (seed 7, 4 m): volta de **18,6 km**, 18 túneis, 4 938 esculturas colocadas (3 755 pedras, 584 blocos
gigantes, 66 mega, 33 meio enterradas, 500 troncos), ~35 min neste PC.

## 10. Circuito misturado (escolha do jogador) e mesas de alturas variadas

Testámos um circuito todo desenhado primeiro (curvas ≥ 250 m, vales abertos à volta): bom para 450 km/h mas
perdia o carácter. O jogador escolheu **misturar**: as naves vão a 450 km/h, mas não sempre; tem de haver curvas
de drift. Ficou:

- **O circuito sinuoso de antes** (washes A, B, C e o laço D nas dunas), com curvas de drift (raio mínimo
  suavizado a ~100 m, sem cotovelos impossíveis) e larguras de 32–36 m (mínimo 22 m).
- **Duas retas pela montanha**: no wash A a sul (atravessa a mesa em túnel) e a diagonal **R**, do wash M
  até ao B. Nos waypoints, `"S"` marca o início de um troço a direito, que passa pelo que estiver à frente.
- **Mesas de alturas variadas**: mesas baixas (10–20 m), médias e torres até ~90 m; topos inclinados
  (cuestas) que descem até ao chão como rampas (subir e saltar na borda); topos em patamares com escarpas de
  ~10 m (saltos de topo em topo); topos mais lisos para andar livre por cima. Túneis só com ≥ 20 m de rocha.
- Resultado (seed 7, 4 m): volta de 17,6 km, 27 túneis. Toques nas paredes: 52 contados, mas muitos são agora
  bordas de mesas baixas (rampas) — afinar a contagem para só contar falésias (> 10 m).
- `Scripts/render_ships.py`: fotos de escala com a nave STRIX (6,4 m) — topo, perseguição, lateral, salto.

## 11. Pendente

- Afinar os toques nas paredes (contar e evitar só os de falésias a sério).
- Versão de vales (circuito desenhado primeiro) guardada como alternativa nas notas desta sessão; pode
  voltar para troços específicos.

## 12. Mundo de 10 × 8 km: `Scripts/sculpt_expansion.py`

O mapa aprovado (7 × 5 km) **fica exatamente como está** no centro-sul; o mundo cresce à volta dele:

```
blender -b <core>/canyon_field.blend -P Scripts/sculpt_expansion.py -- <core> <saida> <pasta_fbx_kit> <pasta_fbx_plantas> [seed]
```

(plantas: `Scripts/sculpt_plants.py`; o kit: `Scripts/sculpt_rock_kit.py`). ~40 min a 4 m neste PC.

- **Oeste (2 km) e norte (3 km): canyons gigantes** (Canyon de Chelly / Monument Valley). Nascem do mapa atual:
  junto a ele as mesas têm o tamanho de agora; mais longe crescem até um planalto de 230–310 m. Canyons
  principais com meandros: **Chinle** (todo o norte) e **Muerto** (oeste); os washes A e B do circuito e o
  afluente H continuam até eles (pouco fundos à saída do mapa, 300 m mais dentro — como em de Chelly: 9 m na
  boca, >300 m dentro). Fundos verdes, rio barrento, choupos e salgueiros; zimbros e mato no planalto.
- **Fendas**: rede ramificada de canyons laterais que corta o planalto em blocos; ramos principais de 20–60 m
  (conduz-se a alta velocidade), ramos finos de 6–12 m (slot canyons). Fundos limpos de detritos e de pedras.
- **Chão ondulado**: ondulações grandes (20–35 m em ~1 km), médias e pequenas, com trechos retos.
- **Marcos um a um**: Spider Rock (agulhas de 240 e 200 m na confluência Monument/Chinle) e mais agulhas;
  buttes de Monument Valley numa planície a sudoeste; 3 mesas de badlands com saias de ravinas entre as dunas e
  o planalto (nordeste); arco duplo gigante e uma lâmina enorme (kit em escala); alcovas nas paredes.
- **Leste (1 km)**: o mar de dunas continua (espelho do último km, cristas alinhadas) e acaba numa planície
  de cascalho com pedras escuras de basalto e um grupo de torres de rocha.
- Costura com o mapa atual em espelho distorcido, que se transforma no terreno novo em ~300 m.
- Saídas: `world_height16.png`, `world.blend`, `canyon_field.json` (tudo em coordenadas do mundo, com os
  canyons gigantes na rede e a lista de marcos), `props.json` (~19 mil peças: núcleo + expansão).
- Referências: Spider Rock ~230–245 m; paredes de 9 m na boca a >300 m (NHMU, MiraCosta, montagna.tv).
