# Modos de jogo, vidas e kit médico (pedido do jogador, 2026-10-21)

**Estado: especificação pronta, nada disto está no código ainda.** Está escrita para a pista nova, a expedição de A a B
(`Docs/PISTA_AB_RED_DUST_DIVIDE.md`, dados em `ab_route.json`). Quem a implementar (no PC com o Unreal) segue a secção
"Implementação" e pergunta ao jogador o que está em "Por decidir".

## 1. O que o jogador pediu

1. **Modo solo**: o jogador sozinho na pista, contra o relógio.
2. **Modo contra bots**: o jogador e **15 bots** (16 naves).
   - As naves que perdem todas as vidas **ficam pelo caminho** (eliminadas).
   - **Só as que sobrevivem contam na meta.**
3. **Vidas consoante as características de cada nave.** A VORTEX é a mais rápida e a mais frágil.
4. **Kit médico de 3 usos, só para o jogador.** Os bots não têm.

## 2. A corrida na pista nova

- **De A a B**, uma só passagem (não há voltas): partida em S1 The Basin, meta em S10 White Rim (Mesa Arch).
  58,6 km na linha ideal, 9:42; com saltos e pilotos reais, 10:30-11:30.
- **Grelha de partida:** o `ab_route.json` traz a grelha 5 × 4 (20 lugares). Usam-se 16: o jogador na posição que
  o modo escolher (a última, ou sorteada) e os 15 bots nos restantes.
- **Progresso = distância ao longo da rota** (comprimento de arco da spline `EXRoute`), não só portões. Dá a
  posição na corrida a qualquer momento e funciona com as bifurcações.
- **Portões** (a atravessar por ordem):
  - um em cada fronteira de setor (S1/S2, S2/S3 ... S9/S10): 9 portões, mais a **meta B**;
  - um portão à entrada e outro à saída de cada bifurcação (SAFE, RACING, SKILL, braço da caverna), de modo que
    um atalho só conta se for atravessado de ponta a ponta.
  - O progresso de quem vai por um atalho salta para o do ponto onde o atalho volta à rota principal.
- **Ordem de chegada:** quem passa a meta B vivo, por tempo. Depois as eliminadas, por distância percorrida
  (a mais longe primeiro). Uma nave eliminada sai da corrida no momento em que perde a última vida.
- **Fim da corrida:** quando o jogador chega a B, ou é eliminado (no contra bots decide-se se continua a ver, ver
  "Por decidir"), ou quando todas as naves vivas chegam.

## 3. Vidas

Cada nave tem um número inteiro de **vidas** que depende das características dela. Vida perdida = um dano grave.

| Dano | Perde |
|---|---|
| Embate de frente contra a rocha ou um pilar (velocidade contra a parede acima do limiar da nave) | 1 vida |
| Aterragem demasiado dura de um salto (velocidade vertical acima do limiar) | 1 vida |
| Raspar na parede (a nave já perde velocidade: `WallScrapeLoss` no `EXHoverCraft`) | nada |

Com a pista nova, o risco e a recompensa ligam-se bem: **os atalhos SKILL** (fendas estreitas, Istmo, lajes) são mais
curtos mas têm paredes mais perto e saltos mais duros, por isso custam vidas a quem erra. O **túnel The Hollow** é
largo e liso (ver `Docs/PISTA_AB_RED_DUST_DIVIDE.md`), por isso não se perde vida só por o atravessar.

Valores propostos (a confirmar com o jogador; as características de jogo de cada nave ainda não estão definidas):

| Nave | Velocidade | Vidas |
|---|---|---|
| VORTEX | a mais rápida | 2 |
| STRIX | rápida | 3 |
| WRAITH | média-alta | 3 |
| NOMAD | média | 4 |
| BASTION | a mais lenta, blindada | 5 |

Os limiares de embate e de aterragem também mudam por nave (a VORTEX parte com menos; a BASTION aguenta mais).

## 4. Kit médico

- **3 usos, só o jogador.** O componente do kit só é criado no jogador: os 15 bots nunca o têm.
- Efeito proposto: **devolve 1 vida**, sem passar o máximo da nave. Não se usa com as vidas cheias. Tem de se
  esperar uns segundos entre dois usos, para não ser uma tecla de imortalidade.
- No solo e no contra bots vale o mesmo.

## 5. Bots (15)

- Seguem a rota `EXRoute` com uma linha de corrida (desvio lateral), e a velocidade de cada ponto do
  `ab_route.json` como limite (`vel`).
- Três níveis de perícia, repartidos pelos 15 (por exemplo 5, 6 e 4): mudam a velocidade a que entram nas curvas, a
  margem às paredes e a escolha das bifurcações (os melhores arriscam SKILL; os piores vão por SAFE).
- **Sofrem o mesmo dano que o jogador** (os mesmos limiares), por isso alguns acabam eliminados pelo caminho.
- Cada bot escolhe uma nave e leva as vidas dela. Nunca têm kit médico.
- **Colisões entre naves:** começar sem colisão entre naves (atravessam-se), para os bots não se eliminarem uns aos
  outros por azar. Ver "Por decidir".

## 6. Solo

- Sem bots. Mantêm-se as vidas e o kit médico.
- Ganha-se chegando a B; conta o tempo. Com 0 vidas a tentativa acaba (ver "Por decidir").

## 7. HUD

- Vidas (marcadores), kit médico (3 → 0), posição na corrida ("4 / 16", só no contra bots), setor atual, tempo.
- Aviso quando uma nave é eliminada ("VORTEX #7 eliminada no S6").
- No fim, o quadro de resultados: quem chegou (tempos) e quem ficou pelo caminho (setor onde caiu).

## 8. Implementação (por onde pegar no código)

O que já existe (`Source/ExtractingStardust`):
- `AEXHoverCraft` (voo, hover, colisão em `Tick`, com o embate numa parede perto de `WallBounce`/`WallScrapeLoss`; a
  spline `EXRoute` é procurada pela etiqueta do ator) e `UEXCraftFx`.
- `AEXHud` (HUD de corrida em mapas com a spline `EXRoute`), `AEXGameMode` (modo de teste de voo).
- A pista é carregada por `EXDesertBuilder.build_world_map` / `Scripts/export_ab_unreal.py` (rota em spline, balizas).

O que falta, por esta ordem:
1. **`FEXShipStats`** (tabela de dados por nave): nome, vidas, velocidade máxima, limiar de embate, limiar de
   aterragem. O `AEXHoverCraft` lê-a ao escolher a nave.
2. **`UEXLifeComponent`** na nave: vidas, `ApplyHit(causa, intensidade)`, evento de eliminação. O embate chama-o no
   sítio onde já trata a parede; a aterragem, onde já trata o contacto com o chão após um salto.
3. **`UEXMedKitComponent`** só no jogador: 3 cargas, `Use()`, tempo de espera.
4. **`AEXRoute`** (ou componente na spline): portões por setor e por bifurcação, a partir do `ab_route.json`;
   `DistanceAlongRoute(ator)`.
5. **`AEXRaceGameMode`**: modo `Solo` e modo `Bots` (`?Mode=Solo` / `?Mode=Bots`), grelha de partida, portões,
   eliminações, classificação, fim da corrida.
6. **`AEXBotController`** (AIController): segue a spline, travagem pelas curvas, escolha de bifurcação por perícia.
7. **HUD** (secção 7) em `AEXHud`.
8. **Teste automático**, na linha do `-EXFlightTest`: `-EXRaceTest -EXBots=15` corre a corrida sem jogador, escreve
   no log as eliminações e a classificação, e falha se um bot não chegar a avançar nos primeiros 60 s.

## 9. Por decidir (perguntar ao jogador)

- Número de vidas por nave e os limiares de dano (a tabela da secção 3 é só uma proposta).
- O que o kit médico recupera (1 vida, ou uma parte) e se tem tempo de espera.
- O que acontece no solo com 0 vidas: fim da tentativa, ou recomeçar do último portão.
- No contra bots, se o jogador eliminado continua a ver a corrida.
- Se as naves se tocam ou se atravessam.
- Se os bots escolhem nave ao acaso ou de forma equilibrada.
- Se há tempo limite por portão (nada disso foi pedido: a eliminação é só pelas vidas).
