# RED DUST DIVIDE — Setor S01 THE BASIN + BROKEN MESA (plano de construção)

Fontes lidas: GDD v1.0 §16–19 (Mapas, Pistas e Expedições), `RDD_00_Plano_Vertical_Slice.md` §E,
`RDD_01_Expedicao.md`, `RDD_Erosao_Parametros.md` (pasta de consulta). Nada aleatório: cada peça
abaixo existe por uma razão geológica e cumpre uma função de corrida.

## 1. Regras que mandam (do GDD)

1. **A geologia vem primeiro** (§16.5): construir uma formação plausível e só depois descobrir nela as
   linhas de corrida. Nunca "estrada + rochas à volta".
2. **Nada de asfalto, rails ou barreiras** (§16). Superfícies: areia compactada, slickrock, lajes,
   cascalho, areia funda (§16.4).
3. **Limites naturais** (§17.12): falésias, areia funda, ravinas. Parede invisível só como rede de
   segurança, muito acima e fora da vista.
4. **Obstáculos visíveis, aprendíveis e integrados** (§17.11). Rocha caída só onde há falésia por cima.
5. **Referências: Utah e Arizona** (§18) — Canyonlands (Island in the Sky, White Rim), Shafer Trail,
   Horseshoe Bend, Arches, Balanced Rock, Bryce (hoodoos), Mesa Arch.
6. **Mudança de leitura a cada 30–60 s** (§19.10).

## 2. Escala (decisão D4 do plano antigo: velocidade 400–450 km/h)

| Zona | GDD | Usado aqui (×1,6) |
|---|---|---|
| Bacia de largada | 30–38 m | 48–60 m |
| Wash aberto | 24–35 m | 38–56 m |
| Percurso principal | 14–24 m | 22–38 m |
| Gargalo | 7–12 m | 11–19 m |

| Curva | GDD | Usado aqui (×1,75) |
|---|---|---|
| Mega arco | 500–1 200 m | 875–2 100 m |
| Média | 120–250 m | 210–440 m |

Saltos (plano antigo E.1b): **flow jump** com borda ≤ 7° e até ~1,2 m de altura; receção sempre
visível e inclinada a acompanhar a trajetória.

## 3. A geologia do setor (o "porquê" de cada forma)

Coluna de estratos (de cima para baixo), como em Canyonlands. A **dureza** decide a forma:
camadas duras ficam como **falésias e cornijas**, as moles **recuam em encostas** com detritos.

| Camada | Dureza | Forma que cria | Cor |
|---|---|---|---|
| Navajo | 0,85 | cúpulas, buttes e mesas arredondadas | creme-laranja pálido |
| Kayenta | 0,60 | **a bancada** onde fica a bacia; lajes partidas em degraus | castanho-avermelhado |
| Wingate | 0,97 | falésia vertical maciça, com verniz escuro | vermelho-laranja |
| Chinle | 0,15 | encosta mole por baixo da Wingate, cheia de detritos | roxo-cinza avermelhado |

Cada rocha no mapa recebe o **material da camada a que pertence** (não uma cor sorteada).

## 4. Peças do setor, por ordem de corrida

| # | Peça | Geologia | Função de corrida | Medidas |
|---|---|---|---|---|
| 1 | **A Bacia** | depressão na bancada Kayenta, fundo de slickrock com areia compactada | grelha 5×4 desencontrada; o pelotão estica | grelha 56 m de largura; bacia ~600×400 m; ondulações baixas |
| 2 | **Mesa do Arco** (landmark) | mesa de Navajo com arco na borda (estilo Mesa Arch) | orientação: visível desde a grelha | ~1,5 km da largada, a nordeste |
| 3 | **Saída em mega arco** | leito largo entre lajes baixas | primeira velocidade alta; 2 flow jumps | R ≈ 1 600 m; 38–56 m de largura |
| 4 | **Butte-ilha** (bifurcação 1) | butte de Navajo isolada no meio do leito | divide em duas rotas | — |
| 4a | SAFE: **wash de areia** | canal de areia à volta da butte, com manchas de areia funda | mais longa (+6 %), sem saltos | 38–48 m |
| 4b | RACING: **lajes partidas** | campo de lajes da Kayenta fraturadas | mais curta, com flow jumps nas bordas das lajes | 22–30 m; saltos de 20–28 m |
| 5 | **Bowl de reunião** | bacia côncava onde as duas rotas se juntam | luta de linhas | ~120 m |
| 6 | **O canyon cresce** | a rota desce suavemente e as falésias de Wingate sobem à volta | transição para S02 THE RED WALL | descida de ~60 m; paredes até 80 m |

**Limites:** mar de dunas a oeste e a sul (areia funda), falésias de mesas a norte, escarpa a leste.
**Detritos:** só no pé das falésias de Wingate e das mesas, em cones (ramp, nunca degrau).

## 5. Como se constrói (ordem, sem deitar nada fora)

1. **Macro-relevo** (C++ `FEXDesertTerrain`): bancada, bacia, mar de dunas, montes de base das mesas,
   descida do canyon. Encostas suaves só onde a camada é mole.
2. **Rota** (spline invisível com largura, bank e tipo de secção por troço): usada para esculpir o
   leito, para checkpoints e IA. Nunca gera uma "faixa".
3. **Geologia-herói no Blender**, peça a peça: Mesa do Arco, butte-ilha, cúpulas de Navajo, lajes da
   Kayenta (com as bordas de salto medidas), segmentos de falésia de Wingate, cones de detrito.
4. **Materiais por camada** (Navajo, Kayenta, Wingate, Chinle) + areia compactada / areia funda.
5. **Validação**: voo pela SAFE e pela RACING; medir larguras, saltos e tempo do setor (alvo ~1:10);
   comparar imagens com as referências do NPS.

Depois de S01 aprovado: S02 THE RED WALL, S03 THE WASH, S04 THE HOLLOW (plano antigo E.3b).
