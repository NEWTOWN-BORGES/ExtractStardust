# EXTRACT: STARDUST — Unreal Engine

Projeto paralelo de migração a partir de `ExtractStardustRDD/`. O projeto Unity original permanece intacto.

## Estado

- Projeto C++ configurado para Unreal Engine 5.8.
- `FStardustCraftInput` e `FStardustCraftTuning` iniciam o port dos parâmetros do STRIX stock.
- As fórmulas de direção, mola, amortecimento, aderência e velocidade de curva foram portadas de `CraftTuning.cs`.
- O sensor de hover tem cinco sondas, mistura as propriedades das superfícies e antecipa a normal da pista.
- A classificação de areia, areia funda, slickrock, cascalho e rocha usa Physical Surface Types do Unreal.
- O primeiro controlador C++ reproduz propulsão, travagem, nitro, aderência lateral, drift, mini-turbo e alinhamento à superfície.
- Choques e aterragens fortes reduzem a integridade do casco; velocidade, nitro e integridade são apresentados na telemetria de teste.
- Durante uma corrida com pista válida, combustível e calor seguem o ciclo de corrida do Unity: boost acelera o consumo e o calor, sobreaquecimento bloqueia o boost e causa dano, e combustível esgotado pode deixar a nave encalhada.
- Existe um pawn de teste com casco provisório, câmara chase, comandos de teclado/gamepad e telemetria sobreposta (velocidade, nitro, hover/ar).
- O GameMode cria automaticamente uma plataforma plana e um PlayerStart provisórios para abrir uma sessão física mesmo sem mapa ou assets importados.
- O leitor `FStardustCourseData` carrega RDDC v1, valida os dados e permite interpolar amostras ao longo da pista; a conversão Unity → Unreal troca os eixos para `UE(X=Unity Z, Y=Unity X, Z=Unity Y)`, preservando metros nos dados.
- `FStardustCourseGraphData` lê RDDG v2, valida a hierarquia dos percursos e converte a distância percorrida num ramo para a distância equivalente no percurso principal.
- `UStardustCourseComponent` disponibiliza RDDC/RDDG às Blueprints e ao código C++; expõe amostras do eixo, pontos da linha lateral, localização no ramo e distância de corrida equivalente.
- Quando existe pista RDDC, o GameMode cria dois bots de teste com o seguidor de linha, separados por faixa; aguardam o primeiro aceleramento do jogador e respeitam a velocidade segura em curva.
- `AStardustProceduralCourseActor` constrói a superfície completa e colisão simplificada (amostras a cada 20 m) a partir do RDDC em `Content/Tracks`; o GameMode posiciona a largada pelo primeiro referencial da pista quando o ficheiro está presente.
- `Content/Tracks` contém uma rota jogável RED DUST DIVIDE: 105,662 km, 21 137 estações e perfil de secção original. O grafo desta exportação inclui apenas o percurso principal; os ramos, o terreno/canyon e os FBX artísticos continuam dependentes do Blender.
- O pawn carrega progresso de corrida ao primeiro aceleramento: cronómetro, checkpoints, estado de chegada e eventos Blueprint, com distância de corrida válida também nos ramos; a telemetria mostra relógio, CP e distância ou avisa quando falta o RDDC.
- A recuperação de corrida reposiciona após 1,5 s mais de 20 m fora da zona de condução; quedas de mais de 60 m abaixo da pista reposicionam com dano, recuando 12 estações e evitando gaps.
- O projeto compila como Editor e Game em Unreal Engine 5.8.3 e a build Windows foi empacotada. O smoke test sem renderização confirmou os dados e a geração de 43 secções visuais e 11 de colisão; a validação visual e de condução no viewport ainda falta, tal como integrar os ramos/veículos do Blender, bots com obstáculos, resultados/economia, interface final e áudio.

Os parâmetros de tuning mantêm as unidades SI do Unity: metros, segundos, m/s e m/s². A conversão para as unidades de mundo do Unreal deve acontecer na camada física, com `1 m = 100 cm`, sem alterar os valores de tuning.

As malhas de pista devem usar o canal de colisão `Ground`. Os Physical Surface Types `SurfaceType1` a `SurfaceType4` correspondem, pela ordem, a areia funda, slickrock, cascalho e rocha; o tipo predefinido é areia.

## Integrar uma pista

1. Gerar os ficheiros da pista com `ExtractStardustRDD/Art/Blender/rdd_build_course.py` ou `rdd_build_route.py`, a partir do JSON escolhido em `ExtractStardustRDD/Art/Courses/`.
2. Copiar o ficheiro `<nome>_course.bytes` para `Content/Tracks/sandbox_course.bytes` (ou atualizar `CourseFileName` no GameMode e no ator procedural) e, se tiver ramos, copiar também `<nome>_graph.bytes` para `Content/Tracks/sandbox_graph.bytes`.
3. O `AStardustProceduralCourseActor` cria a superfície transitável e a colisão pelo RDDC; o terreno/canyon visual e os veículos artísticos ainda precisam dos FBX importados no Content Browser.
4. O `UStardustCourseComponent` expõe posição, tangente, referencial, largura, bank, segmento e superfície para checkpoints, linha de corrida e IA.

### Preparar a pista no PC de casa

1. Para exportar apenas dados jogáveis do percurso principal sem Blender, executar `python .\Tools\ExportCourseDataWithoutBlender.py --install`; precisa de Python 3 e NumPy.
2. Para os ramos completos, terreno/canyon e FBX, instalar Blender e executar `powershell -ExecutionPolicy Bypass -File .\Tools\PrepareCourseForUnreal.ps1` (ou passar `-BlenderExe` e `-CourseSpec`).
3. O script Blender valida RDDC/RDDG e copia os dados para `Content/Tracks`; os FBX e a pré-visualização ficam em `Saved/GeneratedCourse/red_dust_divide`.
4. Para importar automaticamente os setores FBX como malhas estáticas combinadas, executar `powershell -ExecutionPolicy Bypass -File .\Tools\ImportGeneratedCourseAssets.ps1`. Se o cache DDC não for gravável, acrescentar `-ForceMemoryDdc`. Os assets importados ficam em `/Game/Environment/Generated/RedDustDivide` e são ignorados pelo Git por serem artefactos regeneráveis de grande dimensão.
4. Abrir o projeto, compilar e carregar em Play para testar a pista e os dois bots de linha.

## Testar no PC de casa

1. Levar/sincronizar a pasta `ExtractStardustUE/` para o PC de casa.
2. Abrir `ExtractStardustUE.uproject` com Unreal Engine 5.8 e deixar gerar os ficheiros do IDE.
3. Compilar o alvo Editor em Development. O projeto abre o mapa base `OpenWorld` incluído no Unreal.
4. Carregar em Play para gerar a superfície da pista RED DUST DIVIDE, o hovercraft de teste, os dois bots e a telemetria.
5. Controlos: W acelera, A/D vira, S trava, Shift usa nitro, Espaço derrapa, Q/E inclina no ar. Gamepad: RT acelera, stick esquerdo vira, LT trava, A boost, X drift.
6. Se preferires testar sem abrir o editor, executar `Saved\Package\Windows\ExtractStardustUE.exe` depois de desempacotar a pasta completa `Saved\Package\Windows`.

O ramo `red-dust-divide-v2` contém os checkpoints locais já enviados para o GitHub.
