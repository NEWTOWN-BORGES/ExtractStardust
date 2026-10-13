# EXTRACT: STARDUST — Expedição 01 RED DUST DIVIDE (blockout jogável)

Construída segundo o Doc 01 §16-19 (9 setores, ~20 min, ponto A → B) e as referências NPS (Shafer Trail, Horseshoe Bend, Arches, Balanced Rock, Bryce hoodoos, Island in the Sky, Mesa Arch, White Rim).

| | |
|---|---|
| Comprimento | 105,7 km (percurso principal) + 4 ramos (12,7 km) |
| Tempo estimado | 16,8 min na linha ideal do piloto automático (sem nitro); ~19-20 min para um jogador |
| Altitudes | −82 m (fundo do Wash) a 346 m (topo da mesa); planalto a ~318 m |
| Travagens fortes | 52 (ganchos de 100-125 m, esses de 110-140 m, cotovelos de 140-160 m) |
| Obstáculos no traçado | 89 (pilares em slalom, agulhas, rocha caída), sempre com passagem livre |

## Setores

| # | Setor | km | Nível | Conteúdo principal |
|---|---|---|---|---|
| 1 | THE BASIN | 0-11 | bacia a 262 m, falésias à volta | Grelha 5×4 (56 m), bacia aberta de 260 m para cada lado, ondulações de slickrock, 2 flow jumps, esses técnicos, campo de lajes caídas |
| 2 | BROKEN MESA | 11-20 | sobe de 262 a 335 m | Lajes partidas com degraus e saltos, ganchos técnicos, rocha caída; **bifurcação SAFE** (rota baixa, areia, sem saltos) |
| 3 | SHAFER FALL | 20-30 | desce de 335 a 50 m | 11 pernas e 10 ganchos de 100 m em terraços na falésia (escala Shafer Trail) |
| 4 | THE RED WALL | 30-46 | fundo do canyon, ~45 m | Canyon de aproximação com arco, esses, gargalo de 16 m, canyon das agulhas; **parede de 3 km e 200°** com bank 8° → 50°; **atalho SKILL** com salto; canyon jump; segundo gargalo |
| 5 | HORSESHOE DROP | 46-57 | desce a −30 m | Ferradura de 270° (R 850 m); **SAFE** pela borda exterior; **SKILL** pelo terraço interior com drop; meia ferradura |
| 6 | THE WASH | 57-73 | desfiladeiro, −30 a −80 m | Half-pipe natural com meandros, paredes assimétricas, centro com rocha caída, gargalos, cotovelos de 140-160 m, leito de cascalho, esqueleto de nave |
| 7 | ARCHES RUN | 73-83 | sobe a 170 m | Subida com ganchos, corredores entre fins com arcos, 2 slaloms de agulhas, salto pequeno, planície da rocha equilibrada |
| 8 | THE HOLLOW | 83-94 | caverna de ~150 a 112 m | Entrada ampla, curva, descida, bank, half-pipe, câmara com pilar central (bifurcação interna), segunda câmara, salto de saída, descida à White Rim |
| 9 | WHITE RIM FINALE | 94-106 | bancada a ~46 m | Bancada aberta de 200 m com a garganta do rio ao lado (170 m abaixo), curvas largas, ondulações, hero jump de 60 m, EXTRAÇÃO com arco |

## Física (o que torna a expedição exigente)

- Velocidade máxima 425 km/h (nitro ~490).
- A aderência lateral tem teto de ~4,8 g (`CraftTuning.gripCap = 0.55`). Curvas abaixo de ~300 m a fundo pedem travagem ou derrapagem.
- O bank e as paredes somam aderência, por isso a linha alta da Red Wall é a rápida.
- A IA usa o mesmo modelo (`CraftTuning.CornerSpeed`) e desvia-se dos obstáculos.

## Ferramentas

| Passo | Comando |
|---|---|
| Desenhar a pista | `python Art/Courses/make_red_dust_divide.py` (gera `red_dust_divide.json`) |
| Planear sem Blender | `python Art/Blender/rdd_plan.py Art/Courses/red_dust_divide.json` (mapa, perfil, sobreposições, tempo) |
| Gerar a geologia | `blender -b --factory-startup -P Art/Blender/rdd_build_route.py -- Art/Courses/red_dust_divide.json Art/Export/red_dust_divide` (~10 min) |
| Fotografar sem Unity | `blender -b --factory-startup -P Art/Blender/rdd_render_views.py -- Art/Courses/red_dust_divide.json Art/Export/red_dust_divide Logs/fotos_rdd` |
| Unity (importar, validar, build) | `powershell -File Tools/m1_pipeline.ps1 -Course red_dust_divide -SkipBlender -Build` |

Regras do gerador que a expedição usa:

- Curvas por ângulo (`turn`) e altitudes por objetivo (`to_y`).
- Faixa plana `apron` nas bacias e bancadas abertas.
- Linhas de canyon em pedaços de 600 m, para os switchbacks e as ferraduras ficarem certos.
- Exportação por setores de 13 km. No Unity, `SectorStreamer` liga só a geometria a menos de 5 km.

## Por fazer

- Validação no Unity (bloqueada pela licença do editor): volta completa, ramos, folgas, câmera.
- Medir o tempo real com a física final e ajustar o comprimento para ~20 min.
- Adversários (M3), checkpoints por setor e extração.
- Arte final: rocha-herói (arcos e fins modelados), iluminação de cada setor e som.
