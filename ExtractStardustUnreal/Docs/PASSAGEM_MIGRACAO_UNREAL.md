# Passagem de trabalho — migração Extract Stardust para Unreal
Data do checkpoint: 16/10/2026

## Objetivo
Concluir a migração Unity → Unreal Engine 5.8, preservando intacto o Unity. Fazer primeiro uma passagem fiel de conteúdo e funcionamento; só depois melhorar os gráficos. O utilizador pediu a publicação no GitHub para continuar noutro local e esta nota regista o ponto exato da passagem.

## Repositório e segurança
- Repositório raiz: `ExtractStardust`, privado, remote `origin` = `NEWTOWN-BORGES/ExtractStardust`.
- Pasta de migração: `ExtractStardustUnreal/`.
- O Unity original está em `ExtractStardustRDD/`; não o editar nem incluir alterações locais dele nesta branch.
- O repositório raiz tinha várias alterações Unity não commitadas e um atalho não rastreado. Fazer stage por caminho explícito apenas da pasta Unreal.
- Branch dedicada desta migração: `unreal-migration`.
- Os temporários do Unreal estão excluídos por `.gitignore`. Binários de assets estão configurados para Git LFS em `.gitattributes`.

## Estado funcional verificado
- Unreal Engine 5.8.3. `StardustPreview.uproject` permite abrir assets/previews sem compilar C++; `ExtractStardust.uproject` contém o módulo C++.
- Importados: 5 chassis, 24 meshes de curso, kits de props, dados, áudio, materiais, texturas, imagens e fontes. Consultar `Docs/IMPORTACAO_RECURSOS.txt`, `Docs/AUDITORIA_LIMITES_MALHAS.txt`, `Docs/PREVIEW_CURSOS.txt`.
- Mapas de inspeção existentes: `/Game/Stardust/Maps/Preview_Hangar`, `Preview_RedDust`, `Preview_Sandbox`. As pistas são previews: faltam colisão final, streaming, IA, integração ao GameMode/HUD e validação visual/funcional.
- Existem protótipos C++ de pawn, perfil/save, HUD, corrida e leitores RDDC/RDDG. A paridade com o Unity ainda não foi confirmada em jogo.
- As quatro cargas de consumíveis e bindings `1`–`4` aparecem no código, mas ainda precisam de validação no jogo.
- O MSVC x64 já está instalado em `C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.51.36231`.
- A compilação do editor foi tentada. Primeiro foi corrigido `BuildSettingsVersion.V6` para `V7` nos dois targets. A segunda tentativa chegou ao UnrealBuildTool, mas parou porque falta o .NET Framework SDK exigido pelo módulo `SwarmInterface`; ainda não é um erro do C++ do projeto.
- O target de jogo foi compilado com sucesso depois da correcção do HUD para a API `Canvas::DrawText` do UE 5.8. Binário: `Binaries/Win64/ExtractStardust.exe`.
- O teste de arranque do target não cozinhado terminou com erro de leitura de asset (`BufferReader`); isto não é um build jogável standalone. O teste correcto pelo `UnrealEditor.exe` iniciou `StardustPreview` e confirmou `Running engine for game` sem erro fatal. Para distribuir/jogar fora do Editor ainda é necessário `BuildCookRun`.
- Os processos `setup.exe` PID 14836 e 16380 continuam ativos. Não encerrar o instalador à força; confirmar no Visual Studio Installer que foram adicionados Windows SDK e `.NET Framework SDK`.

## Ponto exato em que parei
O hangar já recebeu a primeira passagem funcional.
- `Source/ExtractStardust/Private/StardustHangarPreview.cpp` deixou de fixar apenas `strix`: os cinco chassis têm sockets de motor, propulsão, asas, blindagem, reator, refrigeração, cauda e utilidade; `nomad`, `bastion` e `vortex` têm os sockets adicionais do catálogo.
- `FStardustSocketDefinition` suporta tamanhos múltiplos. `GetCompatibleParts` filtra por família e tamanho; o preview directo de uma peça incompatível aplica o material vermelho e recusa a instalação.
- Foram adicionadas `SetChassis`, `InstallPart`, `RemoveInstalledPart`, `GetSockets` e persistência dos módulos/chassis em `UStardustProfileSubsystem`.
- O preview 3D usa o mesh do chassis e do módulo carregado, com posições de socket em centímetros Unreal. As posições são uma primeira aproximação e precisam de ajuste visual por asset.
- Ainda falta ligar a lista de candidatos e os botões à UI/UMG e reconstruir os módulos instalados a partir do catálogo ao abrir o hangar.
- Referências Unity preservadas em `SourceAssets/Unity/Assets/RedDust/Runtime/Game/ShipBuilder.cs`, `V2ShipVisual.cs` e `SourceAssets/Unity/Assets/RedDust/Runtime/Meta/Catalog.cs` / `Items.cs`.

## Próximas ações
1. Confirmar o commit desta passagem em `origin/unreal-migration`; a branch já recebeu o snapshot inicial de 1,8 GB LFS.
2. Quando o Visual Studio Installer terminar, acrescentar o `.NET Framework SDK 4.6+` e repetir o target de Editor; o Windows 10 SDK já é detectado pelo UnrealBuildTool.
3. Ligar a lista de candidatos e botões UMG ao `GetCompatibleParts`, `PreviewPart` e `InstallPart`; carregar meshes dos IDs reais de `Catalog.cs`.
4. Reconstruir os módulos persistidos ao abrir o hangar e fazer ajuste visual dos transforms por socket.
5. Criar um perfil de `BuildCookRun` para produzir uma build distribuível e testar o fluxo fora do Editor.
6. Portar o restante jogo: física/hover, navegação de percurso, streaming, obstáculos, IA, corrida, HUD/UMG, áudio, economia e telas. Actualizar `Docs/MAPA_PORTES.md` e `Docs/PLANO_MIGRACAO_UNITY_UNREAL.md` apenas com evidência verificada.
7. Fazer o salto gráfico depois de a migração fiel funcionar.

## Referências GitHub
- [Limites de ficheiros/repositório e Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
- [Limite de 2 GiB por push](https://docs.github.com/en/enterprise-cloud@latest/get-started/using-git/troubleshooting-the-2-gb-push-limit)
- [Quotas e faturação LFS](https://docs.github.com/en/billing/concepts/product-billing/git-lfs)

