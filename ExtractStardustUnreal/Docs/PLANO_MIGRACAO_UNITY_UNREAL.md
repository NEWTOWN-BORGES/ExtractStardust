# Plano e estado da migração Unity → Unreal Engine

Atualizado em 15/10/2026. Este documento acompanha a migração para `ExtractStardust.uproject`, Unreal Engine 5.8. O projecto Unity em `C:\Users\nilto\Desktop\extract uststars\ExtractStardustRDD` é a referência e deve continuar preservado.

## Auditoria da origem

- 42 scripts C# de runtime, aproximadamente 4,8 MB / 8,2 mil linhas.
- Duas cenas Unity: `RDD_red_dust_divide` e `RDD_Sandbox`.
- 24 FBX na exportação de pistas, aproximadamente 0,95 GB: nove sectores de terreno e nove corredores da Red Dust Divide, além do sandbox e peças de teste.
- Cinco chassis em FBX; dois kits de props em FBX.
- Dados de curso `RDDC v1` e grafo `RDDG v2`, JSON de percurso/obstáculos/relatórios, 21 WAV, cinco fontes, duas imagens de cartão e texturas de rocha.
- A Red Dust Divide exportada mede 105,662 km, com 21.137 estações no percurso principal. A malha é muito densa; importação e colisão têm de ser medidas no Unreal antes de otimizar.

## O que está nesta entrega

1. Um projecto principal C++ (`ExtractStardust.uproject`) e um descritor Blueprint (`StardustPreview.uproject`) para pré-visualizar os assets antes da primeira compilação.
2. Uma cópia de referência dos dados artísticos, binários e 42 scripts C# em `SourceAssets/Unity`; nenhuma alteração foi feita na origem por esta migração.
3. Os 24 FBX de pistas, cinco chassis e dois kits de props foram importados; também foram importados duas texturas, quatro imagens, 21 WAV, cinco fontes TTF e sete materiais Unity convertidos, além dos dois materiais de apoio. Existem mapas de inspeção do hangar, Red Dust Divide (18 meshes) e Sandbox (4 meshes); ainda não são mapas jogáveis.
4. Primeira conversão nativa para C++ dos blocos de pilotagem hover, consumíveis, perfil local, compatibilidade de sockets, preview de hangar, checkpoints/voltas e leitores RDDC v1/RDDG v2 com obstáculos; o GameMode já tenta carregar os dados do curso.
5. Configuração de teclas 1–4 para os quatro consumíveis.

## Matriz de cobertura

| Área Unity | Estado Unreal | Observação |
|---|---|---|
| Arte 3D e recursos | Importação base concluída | 24/24 FBX de pistas, cinco chassis, dois kits de props, duas texturas, quatro imagens, 21 WAV, cinco fontes TTF e sete materiais Unity convertidos importados; dois materiais auxiliares também existem. Mapas visuais do hangar e dos dois cursos criados; os meshes mantêm as coordenadas exportadas. Relatórios: `IMPORTACAO_CURSOS.txt`, `IMPORTACAO_RECURSOS.txt`, `IMPORTACAO_HANGAR.txt`, `AUDITORIA_LIMITES_MALHAS.txt` e `PREVIEW_CURSOS.txt`. Faltam validação visual, colisões, streaming e integração jogável. |
| Pilotagem e hover | Protótipo C++ criado | Movimento base com suspensão por raycast; ainda precisa de calibração de física contra os valores do Unity. |
| Nitro, casco e consumíveis | Base C++ criada | Quatro slots, efeitos de Repair/Fuel/Coolant/Surge/Stabilizer e perfil local. |
| Hangar / compatibilidade | Base C++ criada | Filtra famílias/tamanhos; o actor mostra uma peça 3D incompatível com material vermelho. A interface completa de seleção ainda falta. |
| Corrida / checkpoints | Base C++ criada, por compilar | O RaceDirector consulta o grafo, atualiza distância/checkpoints e conclui extração com recompensa; falta colocá-lo num mapa, iniciar a sessão a partir do jogo e integrar HUD/resultados. |
| Dados RDDC/RDDG | Parser C++ escrito, integração inicial, por compilar | RDDC v1 e RDDG v2 convertem eixos/metros; obstáculos JSON, posição mais próxima, secção real, faixas, frame, curvatura e ramos estão implementados. RDDC de ambos os cursos está copiado sem alteração e incluído no staging; o RDDG contém as secções usadas pelo GameMode e RaceDirector. Falta consumo pela IA e colocação visual. |
| IA e bots | Por portar | `BotBrain`, `RouteFollower` e `LineFollower`. |
| Streaming, props e obstáculos | Por portar | `SectorStreamer`, `PropField`, grafo e obstáculos; precisa de adaptação para World Partition/ISM. |
| Economia, inventário e progressão | Parcial | Perfil e moeda base; catálogos, raridade, caches, contratos, ledger e relatórios ainda faltam. |
| Ecrãs, HUD, áudio e FX | Parcial | HUD de protótipo; menus, split-screen, áudio, câmara cinematográfica, motion blur e apresentação final ainda faltam. |
| Laboratório de geometria e ferramentas editor | Por portar | `LabGeometry` e ferramentas Unity/Blender não são executadas pelo Unreal; requerem ferramentas editoriais novas. |
| Builds Windows e testes | Pendente | Visual Studio Community 2026 aparece incompleto; MSVC e Windows SDK ainda não foram detectados. Exige toolchain, compilação, validação visual das pistas e sessões de jogo. |

## Etapas de conclusão

### A. Fundamento e compilação

- Instalar a toolchain C++ indicada abaixo.
- Gerar ficheiros do projecto, instalar o Windows SDK e compilar `ExtractStardustEditor Win64 Development`; corrigir os erros de UHT/compilação que surgirem.
- Os 24 FBX de pistas já foram colocados nos mapas visuais `Preview_RedDust` e `Preview_Sandbox`, com os pontos iniciais convertidos dos JSON Unity. Confirmar escala/orientação no editor, gerar colisão simplificada e validar streaming.
- Ajustar a cena para o percurso não carregar dezenas de milhões de triângulos de uma só vez.

### B. Pilotagem e corrida

- Calibrar aceleração, velocidade, forças de suspensão, orientação de superfície, derrapagem, colisões e recuperação a partir de `CraftTuning`/`CraftController`/`HoverSensor`.
- Portar `RaceSession`, `Racer`, `BotBrain`, `LineFollower` e `RouteFollower`; validar largada, checkpoints, ramos e conclusão.
- Implementar persistência/transações idempotentes e resultados de extração.

### C. Hangar e meta-jogo

- Portar os catálogos e regras de `Catalog`, `Items`, `Economy` e `Profile`.
- Construir os ecrãs UMG do hangar, filtros por chassis/socket/tamanho, seleção, montagem, comparação de stats, mochila, loja e caches.
- Ligar a pré-visualização 3D a sockets reais de cada chassis e manter materiais/cores legíveis para compatibilidade.

### D. Apresentação e conteúdo

- Portar câmara, áudio, HUD de corrida, FX de nitro, opções e navegação.
- Portar obstáculos/props e IA sem ultrapassar o orçamento de memória/streaming.
- Recriar as duas cenas e validar corridas completas com teclado e comandos.

### E. Fecho

- Corrigir diferenças visuais/físicas, validar perfis existentes, preparar build de Windows e entregar notas de utilização.
- Atualizar este ficheiro e `Docs/MAPA_PORTES.md` até nenhuma linha estar marcada como por portar.

## Requisitos locais para compilar

O Unreal Engine 5.8 está instalado em `C:\Program Files\Epic Games\UE_5.8` e inclui o runtime .NET 10 usado pelo UnrealBuildTool. À última consulta, `vswhere` identificou Visual Studio Community 2026 (18.11) como instalação incompleta (`isComplete=false`); a verificação dos componentes MSVC e do Windows SDK não encontrou uma toolchain utilizável, e processos do instalador ainda estavam ativos. A compilação C++ continua pendente. Para UE 5.8, instalar MSVC 14.38 ou posterior e Windows SDK 10.0.22621.0 ou posterior; depois repetir a compilação e corrigir eventuais erros de UHT/C++.

## Como executar a pré-visualização

1. Abrir `StardustPreview.uproject` no Unreal 5.8.
2. Abrir o mapa `/Game/Stardust/Maps/Preview_Hangar` para ver os cinco chassis.
3. Abrir `/Game/Stardust/Maps/Preview_RedDust` e `/Game/Stardust/Maps/Preview_Sandbox` para inspecionar os meshes e os pontos iniciais. Os dados de limites estão em `Docs/AUDITORIA_LIMITES_MALHAS.txt` e o registo de montagem em `Docs/PREVIEW_CURSOS.txt`.
4. Consultar `Docs/IMPORTACAO_HANGAR.txt` e `Docs/IMPORTACAO_CURSOS.txt`; os 24 FBX estão nas pastas `Content/Stardust/Courses`.
5. Os assets de pista foram importados com `Scripts/Import_Course_Batch.py`, em lotes limitados e sem colisão. `Scripts/Import_Secondary_Assets.py` também foi executado no Editor Unreal: 5/5 fontes e 7/7 materiais Unity convertidos, sem falhas; os outros recursos já existiam. O relatório é `Docs/IMPORTACAO_RECURSOS.txt`. `Import_And_Build_Previews.py` foi desativado para evitar a importação pesada e o posicionamento incorreto de todos os sectores na origem.
6. Depois de instalar a toolchain, gerar os project files, abrir `ExtractStardust.uproject` e compilar o módulo C++.
## Decisões e riscos conhecidos

- Os bytes de curso usam metros e eixos Unity. Os parsers RDDC/RDDG convertem para centímetros e para X-forward/Z-up do Unreal; a escala e o alinhamento ainda têm de ser confirmados visualmente no jogo.
- Os FBX de pista são extremamente densos. Os 24 assets foram importados em lotes limitados; a máquina chegou a 97% de RAM durante os dois maiores corredores do Sandbox e recuperou após a construção. A importação desativou colisão automática; ainda é necessária colisão simplificada, streaming por sectores e posicionamento do percurso.
- Os FBX estão colocados nos mapas de inspeção com as coordenadas que já vêm nos vértices exportados. Falta confirmar visualmente escala/orientação, gerar colisão simples e validar o streaming; os mapas não devem ser tratados como corridas jogáveis.
- Os sete materiais Unity foram convertidos para materiais Unreal e os materiais auxiliares `M_RedDust` e `M_Incompatible` existem. Ainda falta validar visualmente os materiais nos meshes e atribuir o vermelho incompatível aos pontos de montagem reais.
- A migração ainda não é equivalente ao jogo Unity: a matriz acima é a lista de aceite para concluir o trabalho sem ocultar lacunas.


## Estratégia visual

**Etapa 1 — importação fiel:** importar e organizar todos os recursos existentes como estão na Unity, preservando modelos, texturas, cores, materiais disponíveis e composição original. Montar a versão-base e validar escala, orientação, pistas e leitura visual antes de acrescentar melhorias.

**Etapa 2 — salto gráfico:** depois da versão-base estar completa e validada, melhorar iluminação, materiais, poeira, nitro, câmara e pós-processamento na Unreal. Avaliar Lumen e Nanite apenas quando forem adequados aos assets e ao hardware, medir desempenho e manter a identidade visual do jogo. A pré-visualização atual ainda não demonstra o resultado final de nenhuma das duas etapas.
