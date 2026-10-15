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
- Unreal Engine 5.8.3. `ExtractStardustPreview.uproject` permite abrir assets/previews sem compilar C++; `ExtractStardust.uproject` contém o módulo C++.
- Importados: 5 chassis, 24 meshes de curso, kits de props, dados, áudio, materiais, texturas, imagens e fontes. Consultar `Docs/IMPORTACAO_RECURSOS.txt`, `Docs/AUDITORIA_LIMITES_MALHAS.txt`, `Docs/PREVIEW_CURSOS.txt`.
- Mapas de inspeção existentes: `/Game/Stardust/Maps/Preview_Hangar`, `Preview_RedDust`, `Preview_Sandbox`. As pistas são previews: faltam colisão final, streaming, IA, integração ao GameMode/HUD e validação visual/funcional.
- Existem protótipos C++ de pawn, perfil/save, HUD, corrida e leitores RDDC/RDDG. A compilação do módulo e a paridade com o Unity não foram confirmadas.
- As quatro cargas de consumíveis e bindings `1`–`4` aparecem no código, mas ainda precisam de build e validação no jogo.
- No check atual, os processos `setup.exe` PID 14836 e 16380 ainda respondiam. A última auditoria antes deste checkpoint não encontrou MSVC x64/x86 nem Windows SDK válidos. Reconsultar o Visual Studio Installer e `vswhere` quando estes processos terminarem; não encerrar o instalador à força.

## Ponto exato em que parei
Estava a inspecionar o hangar antes de modificar código. Não foram feitas alterações funcionais no hangar neste checkpoint.
- `Source/ExtractStardust/Private/StardustHangarPreview.cpp` fixa o chassis `strix` e define apenas dois sockets genéricos (`engine` e `utility`).
- `GetCompatibleParts` já aplica compatibilidade por família/tamanho e `PreviewPart` já sabe usar material vermelho, mas não há catálogo real ligado ao fluxo de UI/instalação.
- Pedido do utilizador: listar apenas peças compatíveis com a aeronave atual; mostrar preview 3D do módulo selecionado/instalado; indicar a vermelho uma peça incompatível quando a comparação/preview ocorrer.
- Referências Unity preservadas em `SourceAssets/Unity/Assets/RedDust/Runtime/Game/ShipBuilder.cs`, `V2ShipVisual.cs` e `SourceAssets/Unity/Assets/RedDust/Runtime/Meta/Catalog.cs` / `Items.cs`. A origem tem mais famílias e sockets; parte da aparência é geometria procedural. Portar dados/regras reais em vez de manter os dois sockets de exemplo.

## Próximas ações
1. Confirmar que a branch `unreal-migration` contém apenas o snapshot Unreal, esta nota e os ficheiros de controlo; confirmar que as alterações Unity ficaram unstaged.
2. Fazer push de `unreal-migration` para `origin` quando houver rede rápida. O conteúdo Unreal bruto ronda 1,9 GB antes de ignorar temporários; o envio/clone pode demorar.
3. Terminar o hangar de modo data-driven: chassis selecionável, sockets e limites reais por aeronave, catálogo filtrado por compatibilidade, preview 3D, instalação/persistência e ligação à UI.
4. Depois de MSVC e Windows SDK estarem disponíveis, compilar `ExtractStardust.uproject`, corrigir erros e testar os fluxos no Editor.
5. Portar o restante jogo: física/hover, navegação de percurso, streaming, obstáculos, IA, corrida, HUD/UMG, áudio, economia e telas. Atualizar `Docs/MAPA_PORTES.md` e `Docs/PLANO_MIGRACAO_UNITY_UNREAL.md` apenas com evidência verificada.
6. Fazer o salto gráfico depois de a migração fiel funcionar.

## Referências GitHub
- [Limites de ficheiros/repositório e Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
- [Limite de 2 GiB por push](https://docs.github.com/en/enterprise-cloud@latest/get-started/using-git/troubleshooting-the-2-gb-push-limit)
- [Quotas e faturação LFS](https://docs.github.com/en/billing/concepts/product-billing/git-lfs)

