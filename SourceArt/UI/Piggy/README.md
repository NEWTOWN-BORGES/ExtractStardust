# Porquinho Mealheiro: sprite sheets 2D

Recortados da folha de referência do jogador em 4K (`source/porquinho_referencia.png`, 4096 × 2731), com o fundo
removido e **sem redesenhar nada**: cada frame é o pixel original, só recortado e com transparência RGBA. Os brilhos ficam
semitransparentes, como luz por cima. Gerados por `Scripts/piggy_sprites/build.py`.

## Ficheiros

| Ficheiro | Frames | Tamanho do frame | FPS | Loop |
| --- | --- | --- | --- | --- |
| `Idle.png` | 6 | 478 × 445 | 8 | sim |
| `Blink.png` | 4 | 470 × 448 | 10 | sim (de vez em quando, por cima do Idle) |
| `Receive_Coins.png` | 8 | 476 × 579 | 12 | não |
| `Reward_Jump.png` | 4 | 752 × 549 | 10 | não |
| `Celebrate.png` | 6 | 544 × 528 | 12 | sim |
| `Reaction.png` | 12 | 488 × 528 | estados | não |
| `Move.png` | 3 | 744 × 448 | 12 | sim |
| `Teleport.png` | 3 | 420 × 435 | 10 | não |
| `FX_Coins.png` | 5 | 183 × 182 | peças | – |
| `FX_Glow.png` | 8 | 528 × 435 | peças | – |
| `Icons.png` (extra) | 4 | 309 × 435 | peças | – |

- `Piggy_Master_Spritesheet.png`: todas as animações, uma por linha, com 8 px transparentes entre frames e linhas.
- `frames/<Animação>_NN.png`: cada frame solto, já no tamanho da sua animação.
- `Piggy_Spritesheet.json`: para cada animação, o nome, o número de frames, a largura e a altura, o retângulo de cada
  frame na folha mestre (`rects_master`) e na sua própria folha (`rects_own_sheet`), o pivot (em px e normalizado),
  o FPS, o loop e os nomes dos frames (nas reações e nos efeitos).

## Pivot e alinhamento

- O pivot fica no centro inferior, nos pés.
- No Idle, Blink, Receive_Coins, Reaction e Move cada frame foi alinhado pelos pés à mesma linha do chão.
- No Reward_Jump, Celebrate e Teleport manteve-se a altura original de cada frame, para o salto não se perder.
- A escala nunca foi mexida.

## O que falta no original (assinalado, não redesenhado)

- **Reward_Jump:** não há frame de descida. O 3.º frame é o ápice e o 4.º já é a aterragem.
- **Teleport:** só há 3 frames (entrada no feixe, materializado, saída no feixe). Não há desaparecimento completo nem
  reaparecimento separado. Para a saída, tocar ao contrário.
- **Move:** só há 3 frames, por isso o ciclo é curto.
- **Reaction:** são 12 estados, um frame cada, e não uma sequência.
  - surpresa_exclamacao, duvida_interrogacao, alerta_aviso, sono_zz;
  - neutro_sorriso, alegria_olhos_fechados, choque_exclamacoes, choro, zanga_fumo, tonto_espiral, amor_coracoes,
    contente_sonolento.
- A **placa de recompensa** ("+12,750") não foi exportada, porque tem o número escrito na imagem.
- **Resolução:** os frames saem à resolução da folha em 4K (o porquinho tem ~350 px). As decisões de recorte (o que é
  tinta, brilho ou fundo, e a que frame pertence cada pixel) são tomadas na primeira versão da mesma folha,
  `source/porquinho_referencia_1536.png`, onde os limiares foram afinados. A cor e a transparência finais vêm sempre
  dos pixels em 4K.

## Versão HD 2×

A pasta `HD2x/` tem só as folhas por animação, ao dobro do tamanho, feitas com ampliação por IA (Real-ESRGAN anime).
Servem para promoção; no jogo usam-se as desta pasta. Ver `HD2x/README.md`.

## No jogo

O HUD da corrida (`UEXRaceHudWidget`) usa os frames HD (`HD2x/frames`, importados para `/Game/UI/Piggy/T_Piggy_*` por
`Scripts/import_piggy.py`, no passo 3d do `casa_tudo.ps1`). O porquinho:
- entra a teletransportar-se quando a corrida aparece;
- fica em Idle e pisca de vez em quando;
- recebe as moedas quando uma nave é destruída e o porquinho cresce;
- salta e celebra quando o jogador extrai;
- chora quando o jogador é destruído ou fica encalhado.

No jogo as texturas ficam a 512 px no máximo (`max_texture_size`), o que chega para o HUD. Para capturas de promoção,
subir esse valor. Se os frames não estiverem importados, o HUD mostra o ícone simples de antes.
