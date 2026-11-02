# HUD da corrida (2026-11-01)

Feito a partir da imagem de conceito do jogador: "não tem de ser igual, mas tem de seguir o princípio o máximo
possível, adaptado ao jogo". Maqueta com a arte e as posições do código: `Docs/HUD_CORRIDA_MAQUETA.png`.

## Estilo

- Painéis azul-escuros com borda ciano a brilhar e cantos chanfrados.
- Números em Orbitron inclinados para a frente; legendas em Inter.
- Dourado para o que vale dinheiro, laranja e vermelho para o perigo.
- A arte é feita por `Scripts/make_hud_art.py` (`SourceArt/UI/Icons/hud_*.png`, importada pelo passo 3d como
  `T_Icon_hud_*`). As plantas das naves (`hud_ship_<nave>`) são renders vistos de cima.
- Sem a arte importada, o HUD mostra caixas azuis no lugar dos painéis e continua a funcionar.

## O que fica onde (1920 × 1080)

| Zona | O quê | Dados do jogo |
| --- | --- | --- |
| Topo esquerdo | Logótipo; posição "3/16 POSIÇÃO"; classificação de 8 linhas (planta da nave, nome, EXTRAÍDA ou DESTRUÍDA). A linha do jogador fica acesa e, se ele estiver abaixo do 8.º lugar, ocupa a última linha. | `GetPlayerPlace`, `GetStandings` |
| Topo centro | Cronómetro mm:ss.mmm; separador "CHECKPOINT 3 / 8" (o equivalente às voltas, aqui A→B), que fica vermelho com "VOLTA AO CHECKPOINT N"; barra A→B com checkpoints, rivais, o jogador e os km até B. | relógio da corrida, checkpoints, `GetRaceProgressM` |
| Topo direito | O porquinho HD animado, sentado no canto do painel dourado: moeda, valor, ESPÓLIOS, peças, destruídas, em prova e uma marca por rival. | `GetPool`, `GetLastPoolGain` |
| Direita | Radar: a estrada à volta da nave, que roda com ela (2,4 km), com os checkpoints (passados a dourado, o próximo aceso, o falhado a vermelho), B e os rivais. | `UEXRouteMapWidget::SetRadar` |
| Meio esquerdo | PERIGO! com o aviso mais importante: checkpoint falhado, sentido errado, casco ≤ 25 %, sobreaquecida, sem combustível (e ATENÇÃO! se o combustível está baixo). | |
| Meio direito | "CHECKPOINT N! +40" com troféu e moeda, a entrar da direita; "EXTRAÇÃO!" em B. | `GetLastCheckpointTime` |
| Baixo esquerdo | Os 4 consumíveis em hexágonos: ícone, quantidade, tecla e seta do comando, nome. O hexágono acende a dourado ao usar. | `GetQuickSlots` |
| Baixo centro | Velocidade com KM/H e o BOOST (nitro) em 10 segmentos. Fica ciano a queimar e vermelho se o motor está quente. | `GetSpeedKmh`, `GetNitro` |
| Baixo direito | A planta da nave, uma luz por sistema, CASCO / COMBUSTÍVEL / CALOR em barras com %, VIDAS e EM RISCO. | `GetHullFrac`, `GetFuel`, `GetHeat` |

Diferenças para a imagem de conceito, adaptadas ao jogo:
- não há voltas: o separador do cronómetro mostra o checkpoint;
- ENERGIA e ESCUDO da imagem são aqui o CASCO, o COMBUSTÍVEL e o CALOR;
- as habilidades Q/E/R são os 4 consumíveis (teclas 1-4 e setas do comando);
- o minimapa é um radar local, porque a pista tem 59 km e o traçado inteiro não se leria.

## No canvas (AEXHud)

- A seta-guia desceu para baixo da barra A→B.
- O minimapa antigo e os avisos de calor e combustível saíram, porque passaram para o widget.
- As mensagens ficam à esquerda, entre a classificação e os consumíveis.
- Os avisos de consumível usado ficam por cima do velocímetro.
