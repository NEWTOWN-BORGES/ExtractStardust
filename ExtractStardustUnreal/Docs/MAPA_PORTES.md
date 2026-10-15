# Mapa de portabilidade dos scripts Unity

Os 42 scripts fonte estão preservados em `SourceAssets/Unity/Assets/RedDust/Runtime`. Este mapa indica para onde vão os sistemas no projecto Unreal.

| Script Unity | Módulo Unreal alvo | Estado |
|---|---|---|
| `Core/Foundation.cs` | `StardustTypes`, utilitários de unidade e curso | Parcial |
| `Vehicle/CraftController.cs` | `AStardustHoverPawn` | Protótipo; falta equivalência física |
| `Vehicle/CraftTuning.cs` | Data Assets de tuning | Por portar integralmente |
| `Vehicle/HoverSensor.cs` | Raycasts de suspensão | Protótipo dentro do Pawn |
| `Vehicle/CraftFactory.cs` | Factory/Data Assets de chassis | Por portar |
| `Track/CourseData.cs` | `UStardustCourseData` | Parser RDDC v1 e consultas espaciais/faixas escritos; não compilados |
| Track/CourseGraph.cs | UStardustCourseGraph | Parser RDDG v2, obstáculos, localização e ramos; GameMode carrega o grafo e RaceDirector consulta progresso; falta IA/mapa jogável; por compilar |
| `Track/CourseRuntime.cs` | actor/componente de percurso | Por portar |
| `Track/SectorStreamer.cs` | World Partition/streaming por sectores | Por portar |
| `Track/PropField.cs` | ISM/HISM e obstáculos | Por portar |
| `AI/LineFollower.cs` | componente de direção da IA | Por portar |
| `AI/RouteFollower.cs` | controlador de rota com ramos | Por portar |
| `Game/BotBrain.cs` | controlador de bot e personalidade | Por portar |
| Game/RaceSession.cs | AStardustRaceDirector e estado de prova | Progresso no percurso, checkpoints e extração base; falta integrar no mapa e no HUD; por compilar |
| `Game/Racer.cs` | estado de piloto/corrida | Por portar |
| `Game/PilotInput.cs` | bindings Enhanced Input / Pawn | Teclado base e teclas 1–4 feitos |
| `Game/ShipBuilder.cs` | hangar e montagem por sockets | Compatibilidade/preview base |
| `Game/V2ShipVisual.cs` | componentes/sockets do chassis | Por portar |
| `Game/ProfileStore.cs` | `UStardustProfileSubsystem` + SaveGame | Base criada |
| `Game/GameDirector.cs` | GameMode/flow de ecrãs | Parcial |
| `Game/GameScreens.cs` | widgets UMG | Por portar |
| `Game/GameHud.cs` | `AStardustHUD` | HUD técnico inicial criado |
| `Game/RaceHud.cs` | widget de prova/resultado | Por portar |
| `Game/GameAudio.cs` | SoundCue/MetaSounds e AudioSubsystem | WAV importados pelo script |
| `Game/ImpactLog.cs` | telemetria/registro de dano | Por portar |
| `Game/Icons.cs` | assets de UI/ícones | Por portar |
| `Game/GameBoot.cs` | bootstrap/GameInstance | Por portar |
| `Presentation/PlayerCraftInput.cs` | Pawn / Input mapping | Base criada |
| `Presentation/GameInput.cs` | Enhanced Input | Por portar |
| `Presentation/ChaseCamera.cs` | SpringArm/Camera | Base criada |
| `Presentation/SpeedFx.cs` | Niagara/Post Process | Por portar |
| `Presentation/SandboxDirector.cs` | GameMode de teste | Por portar |
| `Presentation/EnvironmentRig.cs` | luz, atmosfera, pós-processamento | Pré-visualização simples |
| `Presentation/DebugOverlay.cs` | widget de depuração | Parcial via HUD |
| `Presentation/CraftLean.cs` | inclinação visual do chassis | Por portar |
| `Meta/MetaTypes.cs` | structs/enums de domínio | Parcial em `StardustTypes.h` |
| `Meta/Catalog.cs` | DataTables/Data Assets | Por portar |
| `Meta/Items.cs` | partes, raridade e geração | Por portar |
| `Meta/Economy.cs` | carteira/transações/loja | Apenas carteira base |
| `Meta/Profile.cs` | `FStardustProfile` | Base criada |
| `Lab/LabGeometry.cs` | ferramentas editor de geometria | Por portar |

## Critérios para dar um módulo como concluído

- Regras iguais ou documentadas como alteração intencional.
- Dados da origem carregados sem perda e com conversão de coordenadas testada.
- Fluxo acessível por UI/input no jogo, sem depender de chamadas manuais de debug.
- Compilação e uma verificação funcional no Unreal 5.8.
