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
