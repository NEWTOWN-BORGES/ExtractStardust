# Auditoria da migração para Unreal Engine

## Estado confirmado no clone

- Ramo verificado: `red-dust-divide-v2`.
- Commit mais recente no clone: `d49c36d` (`Docs: passo 0 — a versão do Unity tem de ser igual ou mais recente`).
- O README identifica `ExtractStardustRDD/` como o projeto principal atual.
- `ExtractStardust/` é descrito como protótipo anterior e arquivado.
- Os dois diretórios são projetos Unity: têm `ProjectSettings/`, cenas `.unity`, scripts C# e dependências Unity.
- No ramo remoto original não existiam ficheiros `.uproject`, `.uasset` ou `.umap`, nem código Unreal.
- Os documentos de handoff e o plano V2 descrevem explicitamente trabalho e validação em Unity.

Conclusão: a migração ainda não tinha começado no ramo remoto. Foi criado um projeto Unreal paralelo localmente; não contém ainda assets convertidos nem a física de jogo.

## Decisão de versão

- Versão alvo: **Unreal Engine 5.8.2**, a versão mais recente da série UE5 confirmada para esta tarefa.
- Este PC tem VS 2026 Community e Build Tools VS 2022 com ferramentas C++ detetadas. O UE 5.8 foi selecionado no Launcher, mas o diretório `UE_5.8` ainda só contém `.egstore/Pending`; o editor e o UnrealBuildTool ainda não estão disponíveis.
- O utilizador indicou que o PC de casa, mais potente, tem Unreal, Unity, Blender e compilador C++. A versão instalada em casa ainda precisa de ser confirmada como 5.8.2.
- O README do projeto atual indica **PC e Android**, que ficam como plataformas alvo iniciais da migração.
- O PC atual foi identificado como Intel Core i5-4460, 4 processadores lógicos, cerca de 16 GB de RAM disponíveis e 525 GB livres em disco. Fica abaixo dos 32 GB de RAM recomendados pela Epic e do baseline prático de 12–16 núcleos para compilações locais.
- Referências oficiais: [anúncio do Unreal Engine 5.8](https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available) e [anúncio do hotfix 5.8.2](https://forums.unrealengine.com/t/5-8-2-hotfix-released/2746335).

## Origem proposta

Usar `ExtractStardustRDD/` como origem da migração, por ser identificado no README como projeto principal. Manter `ExtractStardust/` como referência histórica e preservar ambos sem conversão destrutiva.

## Inventário inicial para portar

| Sistema Unity atual | Destino Unreal a avaliar |
|---|---|
| Dados de pista e grafo de setores | `UDataAsset`/`UPrimaryDataAsset` e structs C++ serializáveis |
| `CraftController`, `CraftTuning`, `HoverSensor` | `APawn`/`UActorComponent`; reproduzir e medir a física de hover em Unreal Chaos |
| `RaceSession`, `Racer`, `GameDirector` | `AGameModeBase`, `AGameStateBase`, `APlayerState` e subsistemas conforme a responsabilidade |
| `RouteFollower`, `LineFollower` e bots | componentes de IA e navegação próprios; validar rotas sobre a geometria da pista |
| `SectorStreamer` | World Partition/Data Layers ou streaming de níveis, após confirmar o formato e a escala do mundo |
| HUD, menus e hangar | UMG; redesenhar bindings e fluxos de input em Enhanced Input |
| economia, catálogo, perfil e regras de itens | portar primeiro a lógica independente do motor para C++ testável, preservando regras e resultados conhecidos |
| shaders HLSL/URP e materiais Unity | reconstruir em Material Editor/HLSL Custom nodes; não assumir compatibilidade direta |
| cenas e assets Unity | reimportar fontes originais quando existirem; cenas, prefabs, colliders e materiais exigem reconstrução/validação |

Esta tabela é um mapeamento inicial, não uma conversão já realizada.

## Sequência recomendada

1. Confirmar versão alvo do Unreal e plataformas de lançamento.
2. Criar um projeto Unreal paralelo, mantendo o Unity funcional como referência.
3. Portar primeiro regras puras de corrida/economia e criar testes de equivalência com os resultados existentes.
4. Construir um mapa de laboratório pequeno, veículo de jogador e física de hover; comparar aceleração, curva, travagem e wall-ride com métricas Unity.
5. Portar pista, checkpoints, streaming, bots e interface em etapas, validando cada etapa dentro do editor Unreal.
6. Só depois migrar a expedição completa, materiais, efeitos, áudio e builds de destino.

## Trabalho local já iniciado

- Projeto C++ paralelo criado em `ExtractStardustUE/`, associado a Unreal 5.8.
- Portados os campos de input e o tuning de STRIX stock de `CraftTuning.cs` para `FStardustCraftInput` e `FStardustCraftTuning`.
- Portadas as funções de cálculo de taxa de curva, mola, amortecimento, aderência e velocidade de curva.
- Portado o sensor de cinco sondas, a mistura de propriedades de superfície e a leitura antecipada da normal.
- Criado um primeiro controlador de movimento C++ com propulsão, travagem, nitro, aderência, drift, mini-turbo e alinhamento à superfície.
- Configurados um canal de colisão `Ground` e tipos físicos para areia funda, slickrock, cascalho e rocha.
- Mantidas as unidades SI da origem nos dados; a camada física Unreal deverá converter metros para centímetros.
- Colisões/dano, subida de degraus, input de jogador, pista e restantes sistemas ainda faltam. A compilação ainda não foi executada; o alvo indicado para validação é o PC de casa com UE 5.8.2.

## Informação ainda necessária para implementar

- Confirmar a versão instalada no PC de casa e compilar a base C++.
- Confirmar que o alvo é o projeto atual `ExtractStardustRDD/`, e não o protótipo arquivado. O README aponta para `ExtractStardustRDD/` como projeto principal, por isso esse é o alvo assumido.
- Disponibilidade dos assets-fonte originais caso algum material ou modelo exista apenas como asset Unity importado.

