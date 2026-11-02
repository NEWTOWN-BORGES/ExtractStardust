# Mapa 02 — Selva Esmeralda: o traçado (2026-11-02)

Pedido do jogador: "Vamos criar agora um mapa novo, com mais ou menos 12 a 13 minutos, um mapa de sobrevivência. A
temática não vai ser deserto nem Quénia: florestas, rios, África, Amazónia. Comecem pelo traçado. Muitas bifurcações,
muitas curvas, muitos saltos, bifurcações para cima, para baixo, para a esquerda e para a direita, até chegar a B."

**Este é só o traçado**, para o jogador aprovar. A seguir vem o terreno em Blender (secção 6).

![planta](SELVA_PLANTA.png)
![perfil](SELVA_PERFIL.png)

## 1. Números

| | |
|---|---|
| A → B | **72,4 km** |
| Linha ideal | **12:27** (média de 349 km/h; 550 no máximo, 160-250 nas curvas mais apertadas) |
| Bifurcações | **18**: 4 por cima, 5 por baixo, 3 à esquerda, 6 à direita |
| Saltos | **43**: 27 na estrada e 16 nas bifurcações; o maior é a queda de 190 m da cascata |
| Mundo | 20 × 16 km, de A (delta a sudoeste) a B (delta a nordeste) |

Usa o mesmo modelo do Red Dust Divide (`Scripts/sculpt_expedition_ab.py`):
- 550 km/h no máximo, e uma curva de 120 m faz-se a 200 km/h;
- acelera a 12 m/s² e trava a 30 m/s²;
- a gruta vai a 360 km/h no máximo, por causa da visibilidade.

Script: `python3 Scripts/selva/plan_selva.py` (planta, perfil e `Scripts/selva/selva_plano.json`).

## 2. Os 10 setores: Amazónia e África à vez

| Setor | Inspirado em | km | Tempo | Altitude | Carácter |
|---|---|---|---|---|---|
| **S1 Várzea Alagada** | Amazónia | 6,0 | 0:00-1:05 | 22-27 m | Partida no delta: floresta alagada, bancos de areia, meandros largos e rápidos |
| **S2 Serra Vermelha** | Congo | 9,2 | 1:05-2:31 | 27 → 261 m | Cinco pernas em zigue-zague pela serra de laterite vermelha, ganchos de ~150 m |
| **S3 Salto Kaieteur** | Guiana | 5,5 | 2:31-3:21 | 261 → 62 m | Pelo topo da serra até à beira de uma cascata gigante, depois a descida longa ao lado dela |
| **S4 Corredeiras do Congo** | Congo | 7,4 | 3:21-4:40 | 62 → 39 m | Ao longo do rio, rápidos e afluentes para saltar |
| **S5 Gruta das Raízes** | Amazónia | 3,3 | 4:40-5:13 | 39 → 18 m | Gruta larga debaixo de um monte segurado pelas raízes de sumaúmas, com clarabóias |
| **S6 Mangue Labirinto** | Delta do Níger / foz do Amazonas | 6,2 | 5:13-6:29 | 12-27 m | Curvas técnicas entre o mangue, canais para saltar |
| **S7 Tepui** | Roraima | 7,0 | 6:29-7:41 | 27 → 163 m | À volta da base de uma montanha de mesa de 520 m |
| **S8 Galeria da Savana** | Tanzânia / Zâmbia | 8,1 | 7:41-9:02 | 160-170 m | Savana aberta com embondeiros e acácias ao lado de uma floresta de galeria, muito rápida |
| **S9 Garganta Vitória** | Zâmbia / Zimbabué | 8,3 | 9:02-10:24 | 168 → 38 m | O desfiladeiro em zigue-zague abaixo das Cataratas Vitória |
| **S10 Delta do Okavango** | Botsuana | 11,5 | 10:24-12:27 | 37 → 10 m | Canais e ilhas do delta até à extração em B |

## 3. As 18 bifurcações

Todas saem e voltam à estrada em Y, como no Red Dust Divide.

**Ganho:** é o tempo que cada uma ganha (+) ou perde (−) contra a estrada. Cada bifurcação foi esticada ou encurtada
até valer o que o seu estilo pede:
- **SKILL**: arriscada, cerca de +5 s;
- **RACING**: a linha de corrida, cerca de +2,5 s;
- **SAFE**: segura, cerca de −4 s;
- **salto da cascata**: cerca de +10 s.

| | Tipo | Estilo | O que é | km (estrada) | Ganho |
|---|---|---|---|---|---|
| **F1 Igapó** | direita | RACING | entre árvores dentro de água, rente à água | 2,4 (2,4) | +2,8 s |
| **F2 Banco de Areia** | esquerda | SAFE | banco de areia largo e rápido | 2,2 (2,1) | −3,8 s |
| **F3 Pontes da Copa** | **CIMA** | SKILL | pontes suspensas e troncos gigantes a 35 m do chão, sobe a serra e passa **por cima** de um gancho da estrada | 3,9 (5,5) | +5,1 s |
| **F4 Salto da Cascata** | **BAIXO** | RACING | pela beira do salto e **lá para baixo**: queda de 190 m para o lago | 2,7 (3,3) | +8,4 s |
| **F5 Trilho da Névoa** | direita | SKILL | patamar estreito na névoa da cascata, por dentro da descida | 2,4 (2,9) | +5,8 s |
| **F6 Ilhas das Corredeiras** | direita | SKILL | saltos de ilha em ilha no meio dos rápidos | 2,6 (2,6) | +4,2 s |
| **F7 Leito Seco** | **BAIXO** | RACING | leito seco do rio, 18 m abaixo da margem | 1,9 (2,1) | +1,3 s |
| **F8 Raízes Gigantes** | **CIMA** | SKILL | por cima do monte da gruta, pelas raízes | 2,3 (2,4) | +1,5 s |
| **F9 Rio Subterrâneo** | **BAIXO** | RACING | o andar de baixo da gruta, junto ao rio subterrâneo | 1,7 (1,8) | −0,6 s |
| **F10 Canal Estreito** | esquerda | SKILL | canais apertados entre o mangue | 2,7 (2,8) | +3,7 s |
| **F11 Palafitas** | direita | SAFE | passadiço sobre uma aldeia de palafitas, 12 m acima da água | 3,4 (3,0) | −4,5 s |
| **F12 Topo do Tepui** | **CIMA** | SKILL | rampa até ao topo (520 m), saltos entre blocos de rocha e mergulho de volta | 4,6 (5,2) | +12,8 s* |
| **F13 Fenda do Tepui** | **BAIXO** | RACING | uma fenda dentro da base do tepui, 30 m abaixo | 2,6 (2,7) | +1,2 s |
| **F14 Savana Aberta** | esquerda | RACING | savana aberta a mais de 500 km/h, termiteiras para saltar | 3,0 (3,0) | +2,9 s |
| **F15 Floresta de Galeria** | direita | SKILL | dentro da floresta de galeria, junto ao rio | 3,0 (3,5) | +4,7 s |
| **F16 Ponte do Comboio** | **CIMA** | RACING | a velha ponte do comboio por cima da garganta, 60-70 m acima, corta os zigue-zagues | 5,4 (5,4) | +1,4 s |
| **F17 Fundo da Garganta** | **BAIXO** | SKILL | o fundo da garganta, ao lado dos rápidos do Zambeze | 2,7 (3,4) | +4,1 s |
| **F18 Calçada do Lago** | direita | RACING | calçada a direito por cima do lago | 4,5 (3,8) | +3,4 s |

\* **F12:** o modelo de tempo ainda não conta a subida de 440 m nem os saltos lá em cima. Afinar quando houver
terreno.

**Ainda por afinar:** F8 e F9 (a gruta em três níveis) ficaram abaixo do ganho do seu estilo. A estrada na gruta é lenta
e quase direita, e por isso um atalho mal ganha tempo. Afina-se com o terreno.

**Três níveis ao mesmo tempo:**
- **Na gruta:** as raízes por cima (F8), a estrada no meio e o rio subterrâneo por baixo (F9).
- **Na serra:** as Pontes da Copa (F3) passam por cima de um gancho da estrada.
- **Na cascata:** há três escolhas: saltar (F4), a névoa (F5) ou descer pela estrada.

## 4. Os saltos (43)

**Na estrada (27):**

| Setor | Saltos |
|---|---|
| S1 | igarapé, tronco caído |
| S2 | crista da serra |
| S3 | laje da cascata, degrau da descida |
| S4 | 2 afluentes, 2 rápidos |
| S5 | boca e saída da gruta |
| S6 | 2 canais e uma raiz |
| S7 | talude, rampa de basalto |
| S8 | 2 termiteiras, rio de areia, lomba |
| S9 | 3 ressaltos do desfiladeiro |
| S10 | 3 canais do delta, ilha |

**Nas bifurcações (16):**

| Bifurcação | Saltos |
|---|---|
| F1 | raízes |
| F3 | ponte partida, tronco |
| F4 | **a queda de 190 m** |
| F6 | 3 ilhas |
| F8 | raiz, descida |
| F11 | cais |
| F12 | 2 fendas no topo, mergulho |
| F14 | termiteira |
| F16 | fim da ponte |
| F17 | rochedo |

## 5. Sobrevivência

A extração continua igual: quem é destruído perde a carga para o porquinho e só quem chega a B a leva
(`Docs/VISAO_JOGO.md`). A selva pode trazer perigos próprios, **por decidir com o jogador**:
- árvores que caem na estrada;
- cheias que fecham o Leito Seco (F7);
- névoa da cascata que tira a vista;
- chuva tropical que tira aderência;
- mais tarde, os monstros da visão: crocodilos e hipopótamos nos rios, enxames no mangue.

## 6. Próximos passos (depois de o jogador aprovar o traçado)

1. **Terreno em Blender:** um `Scripts/selva/sculpt_selva.py` como o `sculpt_expedition_ab.py`.
   - Os rios a correr ao lado da estrada, o delta e os mangues.
   - A serra vermelha, a cascata com o lago, a gruta em três níveis com clarabóias, o tepui com falésias, a savana e a
     garganta em zigue-zague.
   - Fotos de piloto em cada setor.
2. **Vegetação** (CC0 ou o nosso kit em Blender):
   - floresta: sumaúmas com raízes em tábua, palmeiras, fetos arbóreos, lianas;
   - mangue;
   - savana: embondeiros e acácias;
   - nada com colisão, como no deserto.
3. **Unreal:**
   - água (rios, cascata, lago);
   - névoa húmida e luz filtrada pelas copas;
   - sinalética e portões como no Red Dust Divide.
