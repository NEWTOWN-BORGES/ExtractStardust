# Instalar o compilador C++ para o Extract Stardust

O editor de pré-visualização abre sem compilar C++. O projecto principal (ExtractStardust.uproject) precisa de MSVC e do SDK do Windows para compilar.

## O que instalar

Para Unreal Engine 5.8, a versão mínima publicada é Visual Studio 2022 17.14, MSVC 14.38 e Windows SDK 10.0.22621.0. A configuração incluída selecciona Build Tools para C++ x64/x86 e o SDK 10.0.22621.0. O Visual Studio 2026, MSVC 14.50 e SDK 10.0.26100.0 são a combinação recomendada pela versão 5.8.

## Passos

1. Abre a página oficial [Transferências do Visual Studio](https://visualstudio.microsoft.com/downloads/) e obtém o Visual Studio Community ou Build Tools compatível com o Unreal Engine 5.8. No dia 15/10/2026, a página oficial apresentava o Visual Studio 2026.
2. Se precisares apenas do compilador, escolhe Build Tools for Visual Studio 2026; escolhe Visual Studio Community se também quiseres a IDE. Selecciona o workload Desktop development with C++ e importa ExtractStardust_BuildTools.vsconfig da pasta raiz do projecto. Se o Windows pedir autorização UAC, aprova o instalador.
3. Confirma que estão seleccionados MSVC x64/x86 build tools (14.38 mínimo; 14.50 recomendado) e Windows SDK 10.0.22621.0 no mínimo. No Visual Studio 2026, o SDK 10.0.26100.0 é recomendado pelo Unreal 5.8. A configuração ExtractStardust_BuildTools.vsconfig inclui o workload C++ e o SDK 22621.
4. Instala os componentes e reinicia o Unreal Editor e o Epic Games Launcher.
5. Abre primeiro ExtractStardust.uproject. Quando o Unreal terminar a compilação inicial, confirma que o mapa Content/Stardust/Maps/Preview_Hangar abre e que aparecem os cinco chassis.

A Microsoft documenta a carga **Desktop development with C++** e os componentes do Build Tools em [Instalar as ferramentas MSVC](https://learn.microsoft.com/en-us/cpp/overview/acquire-msvc?view=msvc-170) e [IDs de componentes do Build Tools 2022](https://learn.microsoft.com/pt-pt/visualstudio/install/workload-component-id-vs-build-tools?view=vs-2022).

## Escolher entre pré-visualização e compilação

- ExtractStardustPreview.uproject abre o hangar sem instalar o compilador.
- Para compilar ExtractStardust.uproject, instalar MSVC e Windows SDK é necessário.
- Se os dados móveis forem limitados, fazer a instalação por Wi-Fi. O tamanho transferido varia conforme os componentes seleccionados.
## Estado desta máquina

À última consulta (15/10/2026), `vswhere` identificou Visual Studio Community 2026 (18.11), mas a instalação permanecia incompleta (`isComplete=false`). A pesquisa por MSVC x64/x86 e pelas pastas do Windows SDK ainda não encontrou os componentes necessários; os processos `setup` continuavam ativos. Por isso, ainda não há resultado de compilação C++. Quando o instalador terminar, verificar novamente os componentes e então compilar `ExtractStardustEditor Win64 Development`.

## Abrir sem compilador

Enquanto o compilador não estiver instalado, abre ExtractStardustPreview.uproject. O mapa do hangar já está preparado. A pré-visualização usa os modelos importados e não representa ainda uma versão final jogável do projecto C++.
