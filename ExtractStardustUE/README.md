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
- Com RDDC carregado, o GameMode escolhe essa largada da pista em vez do PlayerStart do mapa (mantendo prioridade para Play From Here). A malha gerada mantém colisão de consulta; se as sondas principais perderem a pista, o sensor tenta recuperá-la pela última normal válida.
- `Content/Tracks` contém uma rota jogável RED DUST DIVIDE: 105,662 km, 21 137 estações e perfil de secção original. O grafo desta exportação inclui apenas o percurso principal; os ramos, o terreno/canyon e os FBX artísticos continuam dependentes do Blender.
- O pawn carrega progresso de corrida ao primeiro aceleramento: cronómetro, checkpoints, estado de chegada e eventos Blueprint, com distância de corrida válida também nos ramos; a telemetria mostra relógio, CP e distância ou avisa quando falta o RDDC.
- A recuperação de corrida reposiciona após 1,5 s mais de 20 m fora da zona de condução; quedas de mais de 60 m abaixo da pista reposicionam com dano, recuando 12 estações e evitando gaps.
- Revalidação local em 2026-10-16 no Unreal Engine 5.8.3: foi instalado no Visual Studio o SDK .NET Framework 4.8.1; os alvos Editor e Game Development compilaram com sucesso. O Editor abriu o mapa base `OpenWorld`.
- Revalidação local em 2026-10-16 com UE 5.8.3: os alvos Editor e Game compilaram; `BuildCookRun` Win64 Development cozinhou 596 pacotes, 0 erros/avisos e criou um pacote local de cerca de 502 MiB. Arrancado com `-nullrhi`, carregou `OpenWorld`, `StardustGameMode`, as 21 137 estações (105,66 km) e 18/18 meshes de ambiente à escala 100. Não valida renderização ou condução; o log registou um aviso de Enhanced Input sem PlayerInput neste arranque automático.
- Revalidação local em 2026-10-16 com UE 5.8.3: o arranque headless colocou o hovercraft na pista (Z≈263,5 m); a sonda inicial atingiu `CollisionMesh` (Z≈261,45 m) e a nave estabilizou em 1,44 m de altura, velocidade vertical ≈0, com 4/5 sondas em contacto durante mais de 10 s. Isto confirma o arranque/contacto básico, mas ainda não testa uma recuperação após queda induzida, imagem nem input manual.
- Os 18 meshes gerados estão agora ligados ao ator do percurso; a escala 100 corrige a unidade dos meshes importados. A posição e aparência ainda precisam de validação visual. A migração total continua incompleta: faltam condução verificada com input, ramos/veículos do Blender, bots com obstáculos, resultados/economia, interface final e áudio.

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
4. Para importar automaticamente os setores FBX como malhas estáticas combinadas, executar `powershell -ExecutionPolicy Bypass -File .\Tools\ImportGeneratedCourseAssets.ps1`. Se o cache DDC não for gravável, acrescentar `-ForceMemoryDdc`. Os 18 `.uasset` de pista deste checkpoint foram adicionados explicitamente ao Git LFS, apesar da regra `.gitignore` para essa pasta; novos artefactos regeneráveis continuam ignorados até serem incluídos explicitamente.
4. Abrir o projeto, compilar e carregar em Play para testar a pista e os dois bots de linha.

## Compilar em Windows

- O projeto está associado ao Unreal Engine 5.8; a tentativa local usa UE 5.8.3.
- Instalar no Visual Studio o SDK do .NET Framework 4.6.0 ou superior (neste PC, o componente .NET Framework 4.8.1 SDK), além das ferramentas C++ e do Windows SDK. O UnrealBuildTool carrega o módulo `SwarmInterface`; sem `NETFXSDKDir`, a geração das regras falha antes de compilar o código do jogo.
- Com o Engine instalado em `C:\Program Files\Epic Games\UE_5.8`, compilar o Editor a partir da raiz do repositório:

```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" ExtractStardustUEEditor Win64 Development "-Project=$PWD\ExtractStardustUE\ExtractStardustUE.uproject" -WaitMutex -NoHotReloadFromIDE
```

### Git LFS para o primeiro teste

`Content/Tracks/sandbox_course.bytes` e `sandbox_graph.bytes` são ficheiros regulares do Git. O percurso procedural funciona sem LFS; os 18 meshes de terreno/canyon são carregados pelo ator para visualização e cook. Sem os UAssets LFS, a pista procedural continua, mas esses meshes visuais ficam ausentes e o log avisa quais faltam. Para os descarregar, usar apenas `git lfs pull --include="ExtractStardustUE/Content/Environment/Generated/RedDustDivide/**" origin red-dust-divide-v2`. Não descarregar o ZIP de jogo nem integrar assets do Fab.

## Testar no PC de casa

1. Levar/sincronizar a pasta `ExtractStardustUE/` para o PC de casa.
2. Abrir `ExtractStardustUE.uproject` com Unreal Engine 5.8 e deixar gerar os ficheiros do IDE.
3. Compilar o alvo Editor em Development. O projeto abre o mapa base `OpenWorld` incluído no Unreal.
4. Carregar em Play para gerar a superfície da pista RED DUST DIVIDE, o hovercraft de teste, os dois bots e a telemetria.
5. Controlos: W acelera, A/D vira, S trava, Shift usa nitro, Espaço derrapa, Q/E inclina no ar. Gamepad: RT acelera, stick esquerdo vira, LT trava, A boost, X drift.
6. O pacote de teste desta máquina está em `Saved\PackageSmokeEnvironment\Windows`; é artefacto local ignorado pelo Git. O smoke test confirmou o arranque com `-nullrhi`, mas não valida imagem nem input. Para repetir, gerar o pacote local com Unreal Automation Tool.

O ramo `red-dust-divide-v2` contém os checkpoints locais já enviados para o GitHub.
