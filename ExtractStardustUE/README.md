# EXTRACT: STARDUST — Unreal Engine

Projeto paralelo de migração a partir de `ExtractStardustRDD/`. O projeto Unity original permanece intacto.

## Estado

- Projeto C++ configurado para Unreal Engine 5.8.
- `FStardustCraftInput` e `FStardustCraftTuning` iniciam o port dos parâmetros do STRIX stock.
- As fórmulas de direção, mola, amortecimento, aderência e velocidade de curva foram portadas de `CraftTuning.cs`.
- O sensor de hover tem cinco sondas, mistura as propriedades das superfícies e antecipa a normal da pista.
- A classificação de areia, areia funda, slickrock, cascalho e rocha usa Physical Surface Types do Unreal.
- O controlador de movimento e colisões do veículo, pista, interface, bots, progressão, áudio e assets ainda não foram portados.
- Esta base ainda não foi compilada. O PC onde este clone foi preparado só tem Unreal 5.5 e recursos modestos; validar no PC de casa com UE 5.8.2.

Os parâmetros de tuning mantêm as unidades SI do Unity: metros, segundos, m/s e m/s². A conversão para as unidades de mundo do Unreal deve acontecer na camada física, com `1 m = 100 cm`, sem alterar os valores de tuning.

As malhas de pista devem usar o canal de colisão `Ground`. Os Physical Surface Types `SurfaceType1` a `SurfaceType4` correspondem, pela ordem, a areia funda, slickrock, cascalho e rocha; o tipo predefinido é areia.

## Abrir no PC de casa

1. Levar/sincronizar a pasta `ExtractStardustUE/` para o PC de casa.
2. Confirmar que o Epic Games Launcher tem Unreal Engine 5.8.2 e os pré-requisitos de C++ instalados.
3. Abrir `ExtractStardustUE.uproject`, permitir a geração dos ficheiros do IDE e compilar o alvo Editor em Development.
4. Corrigir primeiro quaisquer erros de compilação, depois criar um mapa de teste antes de avançar para a física completa.

O repositório GitHub ainda não recebeu estas alterações locais.
