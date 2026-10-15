# EXTRACT: STARDUST

**RACE. SURVIVE. EXTRACT.** Corrida de extração com naves antigravidade (Unity 6 URP + Blender), PC e Android.

> **Trabalho em curso no ramo `red-dust-divide-v2`.** Para retomar o
> desenvolvimento, começar por **[`ExtractStardustRDD/Docs/ESTADO_Handoff.md`](ExtractStardustRDD/Docs/ESTADO_Handoff.md)** —
> traz o que está feito, o que falta, como verificar sem Unity nem Blender, e as
> convenções que não se devem quebrar.

| Pasta | O que é | Estado |
|---|---|---|
| `ExtractStardustRDD/` | **Projeto principal.** Expedição RED DUST DIVIDE: canyons naturais (Utah/Arizona reinterpretados), naves a 400–450 km/h, geologia modelada no Blender. Modos Exploração, Extração vs bots e PvP local; 5 naves modulares, mochila, mercado, Supply Caches, seguro e Expedition Pool. | Laboratório validado (21/22 testes). Expedição (105,7 km, 9 setores, ~20 min) gerada no Blender. Modos e economia programados e testados fora do Unity. Os 9 assemblies compilam (verificado com `Tools/check_compile.ps1`, sem abrir o editor). Falta correr o editor e medir física/fps em casa. |
| `ExtractStardust/` | Protótipo anterior: ilha de 24 km em mundo aberto (porte do RACESTARS), com expedição, circuitos, Wi-Fi e tela dividida. | Arquivo. |
| `Builds_Jogaveis/` | Jogos compilados (Git LFS). | Ver abaixo. |

## Verificar sem abrir o Unity

O projeto compila-se e testa-se sem licença, sem GPU e sem abrir o editor:

```powershell
cd ExtractStardustRDD
powershell -ExecutionPolicy Bypass -File Tools\check_compile.ps1   # 9/9 assemblies
powershell -ExecutionPolicy Bypass -File Tools\test_meta.ps1       # 45 701 verificações de economia
python Tools\verifica_sculpt_real.py                               # geometria da pista, sem Blender
```

As ferramentas detectam sozinhas a versão do editor instalada.

## Jogar sem o Unity

| Ficheiro | Conteúdo |
|---|---|
| `Builds_Jogaveis/RedDustDivide_Windows.zip` | Laboratório da RED DUST DIVIDE (última build, antes da expedição). Extrair a pasta inteira e abrir `RedDustDivide.exe`. |
| `Builds_Jogaveis/IlhaPrototipo_Windows.zip` | Protótipo da ilha (Windows). |
| `Builds_Jogaveis/IlhaPrototipo_Android.apk` | Protótipo da ilha (Android). |

Os ficheiros grandes estão no Git LFS, que vem com o Git para Windows. Depois de clonar, se aparecerem ficheiros de 1 KB, correr `git lfs pull`.

## Documentação

- Expedição (setores, física, ferramentas): `ExtractStardustRDD/Docs/RDD_01_Expedicao.md`
- Modos, naves modulares, economia, Pool e bots: `ExtractStardustRDD/Docs/RDD_02_Modos_Economia.md`
- Plano e decisões: `ExtractStardustRDD/Docs/RDD_00_Plano_Vertical_Slice.md`
- Validação da física: `ExtractStardustRDD/Docs/M1_Relatorio_Fisica.md`
- Documentos de design (mapas, naves, economia), imagens e vídeo de referência: `ExtractStardustRDD/Docs/referencias/`
- Fotos: `ExtractStardustRDD/Docs/fotos/` (`expedicao` = renders do Blender das paisagens dos 9 setores; `laboratorio_m1` e `zonas_laboratorio` = capturas do Unity). Fotos do protótipo da ilha: `ExtractStardust/Docs/fotos/`.

## Gerar a geologia e compilar

A geometria gerada (FBX, ~1,4 GB) não vai para o repositório. Gera-se a partir dos scripts, sempre igual (sementes fixas): ~2 min o laboratório, ~10 min a expedição.

```powershell
# requisitos: Unity 6000.3.26f1 (com Android Build Support), Blender 5.2
powershell -ExecutionPolicy Bypass -File ExtractStardustRDD/Tools/m1_pipeline.ps1 -Course sandbox -Build
powershell -ExecutionPolicy Bypass -File ExtractStardustRDD/Tools/m1_pipeline.ps1 -Course red_dust_divide -Build
```

O script corre o Blender (`Art/Blender/rdd_build_route.py`), importa no Unity, valida (física, ramos, folgas) e compila `ExtractStardustRDD/Builds/Windows/RedDustDivide.exe`.

Jogo completo (exe com as duas pistas, teste de extração com bots e APK com o laboratório):

```powershell
powershell -ExecutionPolicy Bypass -File ExtractStardustRDD/Tools/m1_pipeline.ps1 -Course red_dust_divide -SkipBlender -SkipValidate -Build -Test -Android
```

Sem Unity: `Tools/test_meta.ps1` (economia, 45 mil verificações) e `Tools/check_compile.ps1` (compila os scripts).

Os percursos são desenhados em `ExtractStardustRDD/Art/Courses/`. `make_red_dust_divide.py` gera `red_dust_divide.json`. `Art/Blender/rdd_plan.py` mostra o mapa, o tempo e as sobreposições sem abrir o Blender.

## Controlos

| Ação | Comando PS4/PS5 | Teclado |
|---|---|---|
| Direção | analógico esquerdo | A / D |
| Acelerar | R2 | W |
| Travar | L2 | S |
| Derrapagem | Quadrado | Espaço |
| Nitro (regenera) | X ou R1 | Shift |
| Usar consumível | L1 (D-pad ↑/↓ escolhe) | 1 / 2 / 3 |
| Reposicionar | Triângulo | R |
| Olhar à volta / para trás | analógico direito / R3 | C |
| Pausa | OPTIONS | Esc |
