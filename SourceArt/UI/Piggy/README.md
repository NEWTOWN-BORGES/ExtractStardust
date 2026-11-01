# Porquinho Mealheiro: sprite sheets 2D

Recortados da folha de referência do jogador (`source/porquinho_referencia.png`), com o fundo removido e **sem
redesenhar nada**: cada frame é o pixel original, só recortado e com transparência RGBA. Os brilhos ficam
semitransparentes, como luz por cima. Gerados por `Scripts/piggy_sprites/build.py`.

## Ficheiros

| Ficheiro | Frames | Tamanho do frame | FPS | Loop |
| --- | --- | --- | --- | --- |
| `Idle.png` | 6 | 178 × 167 | 8 | sim |
| `Blink.png` | 4 | 176 × 168 | 10 | sim (de vez em quando, por cima do Idle) |
| `Receive_Coins.png` | 8 | 194 × 217 | 12 | não |
| `Reward_Jump.png` | 4 | 288 × 206 | 10 | não |
| `Celebrate.png` | 6 | 208 × 198 | 12 | sim |
| `Reaction.png` | 12 | 182 × 204 | estados | não |
| `Move.png` | 3 | 280 × 167 | 12 | sim |
| `Teleport.png` | 3 | 158 × 163 | 10 | não |
| `FX_Coins.png` | 5 | 68 × 69 | peças | – |
| `FX_Glow.png` | 8 | 197 × 163 | peças | – |
| `Icons.png` (extra) | 4 | 116 × 163 | peças | – |

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
- **Resolução:** a referência tem 1536 × 1024, por isso o porquinho fica com ~130 px. Com o original em 4K, voltar a
  correr o script (basta substituir `source/porquinho_referencia.png`) dá frames ~2,7× maiores, com os mesmos cortes.
