# EXTRACT: STARDUST — Unreal Engine

Projeto paralelo de migração a partir de `ExtractStardustRDD/`. O projeto Unity original permanece intacto.

## Estado

- Projeto C++ configurado para Unreal Engine 5.8.
- `FStardustCraftInput` e `FStardustCraftTuning` iniciam o port dos parâmetros do STRIX stock.
- As fórmulas de direção, mola, amortecimento, aderência e velocidade de curva foram portadas de `CraftTuning.cs`.
- O sensor de hover tem cinco sondas, mistura as propriedades das superfícies e antecipa a normal da pista.
- A classificação de areia, areia funda, slickrock, cascalho e rocha usa Physical Surface Types do Unreal.
- O primeiro controlador C++ reproduz propulsão, travagem, nitro, aderência lateral, drift, mini-turbo e alinhamento à superfície.
- Existe um pawn de teste com casco provisório, câmara chase, comandos de teclado/gamepad e telemetria sobreposta (velocidade, nitro, hover/ar).
- O GameMode cria automaticamente uma plataforma plana e um PlayerStart provisórios para abrir uma sessão física mesmo sem mapa ou assets importados.
- O leitor `FStardustCourseData` carrega RDDC v1, valida os dados e permite interpolar amostras ao longo da pista; a conversão Unity → Unreal troca os eixos para `UE(X=Unity Z, Y=Unity X, Z=Unity Y)`, preservando metros nos dados.
- A base C++ compila no Unreal Engine 5.8. Faltam testar a sessão no viewport, importar as pistas/veículos do Blender, e portar colisões/dano, bots, progressão, interface final e áudio.

Os parâmetros de tuning mantêm as unidades SI do Unity: metros, segundos, m/s e m/s². A conversão para as unidades de mundo do Unreal deve acontecer na camada física, com `1 m = 100 cm`, sem alterar os valores de tuning.

As malhas de pista devem usar o canal de colisão `Ground`. Os Physical Surface Types `SurfaceType1` a `SurfaceType4` correspondem, pela ordem, a areia funda, slickrock, cascalho e rocha; o tipo predefinido é areia.

## Testar no PC de casa

1. Levar/sincronizar a pasta `ExtractStardustUE/` para o PC de casa.
2. Abrir `ExtractStardustUE.uproject` com Unreal Engine 5.8 e deixar gerar os ficheiros do IDE.
3. Compilar o alvo Editor em Development. O projeto abre o mapa base `OpenWorld` incluído no Unreal.
4. Carregar em Play: aparece uma plataforma temporária, o hovercraft cúbico e telemetria no ecrã.
5. Controlos: W acelera, A/D vira, S trava, Shift usa nitro, Espaço derrapa, Q/E inclina no ar. Gamepad: RT acelera, stick esquerdo vira, LT trava, A boost, X drift.
6. A plataforma é apenas um laboratório de movimento; a pista RDD real e as naves artísticas serão ligadas depois de importar os assets do Blender.

O repositório GitHub ainda não recebeu estas alterações locais porque a credencial guardada no GitHub CLI está inválida.
