# Extract Stardust — Unreal Engine

Port em desenvolvimento do projeto Unity para Unreal Engine 5.8. O projeto Unity original foi preservado sem alterações.

## Projetos

- `ExtractStardustPreview.uproject`: projeto Blueprint para abrir e inspecionar os recursos sem compilar C++.
- `ExtractStardust.uproject`: projeto principal com a base C++; a compilação ainda depende de MSVC e Windows SDK e não está validada.

## Abrir a pré-visualização

1. Abra `ExtractStardustPreview.uproject` no Unreal Engine 5.8.
2. No Content Browser, abra `/Game/Stardust/Maps/Preview_Hangar` para ver os cinco chassis em 3D.
3. Para inspecionar as pistas, abra `/Game/Stardust/Maps/Preview_RedDust` ou `/Game/Stardust/Maps/Preview_Sandbox`. Os 22 meshes de percurso estão colocados nas coordenadas de mundo preservadas pelos FBX; os pontos iniciais foram convertidos dos JSON Unity.
4. Os 24 FBX estão importados em `/Game/Stardust/Courses/RedDustDivide` e `/Game/Stardust/Courses/Sandbox`; props, texturas, imagens e áudio estão em `/Game/Stardust/Props`, `Textures`, `UI` e `Audio`.

Os mapas de pista são previews visuais. Ainda faltam validação visual de escala/orientação, colisão otimizada, streaming, integração do GameMode C++, HUD e IA para se tornarem jogáveis. Consulte `Docs/PREVIEW_CURSOS.txt` e `Docs/AUDITORIA_LIMITES_MALHAS.txt`.

A primeira passagem da migração preserva o aspeto de origem. O salto gráfico será uma etapa posterior, depois de todo o conteúdo estar importado, montado e validado.

## O que já existe

- Base C++ de pilotagem hover com aceleração, direção, suspensão por raycast, nitro e colisão.
- Quatro consumíveis associados às teclas `1`, `2`, `3` e `4`.
- Perfil local, filtro de compatibilidade de módulos, pré-visualização 3D e indicação vermelha de incompatibilidade.
- RaceDirector com progresso no percurso, checkpoints e extração base; leitores RDDC v1 e RDDG v2 carregam percursos/obstáculos e localizam a nave. A integração no mapa, no HUD e na IA ainda está pendente; o código C++ aguarda compilação.
- Hangar de pré-visualização com os cinco chassis; mapas visuais Preview_RedDust (18 meshes) e Preview_Sandbox (4 meshes); 24 FBX de pista e dois kits de props convertidos em malhas estáticas.
- Duas texturas, quatro imagens, 21 ficheiros de áudio, cinco fontes TTF e sete materiais Unity convertidos. O relatório confirma 5/5 fontes, 7/7 materiais e zero falhas; estão também criados dois materiais auxiliares.
- Dados binários, JSON, sons, texturas, imagens, fontes e 42 scripts C# originais preservados em `SourceAssets/Unity`.

O conteúdo artístico base foi importado. A última verificação encontrou o Visual Studio Community 2026 incompleto, sem MSVC/Windows SDK utilizáveis; o instalador ainda estava ativo e o código C++ não foi compilado. Isto não é uma migração completa nem tem paridade funcional com o Unity. O estado, as lacunas e as etapas estão em `Docs/PLANO_MIGRACAO_UNITY_UNREAL.md`.

## Controlos previstos para o protótipo

- `W` / seta para cima: acelerar.
- `A/D` ou setas esquerda/direita: virar.
- `S` / seta para baixo: travar.
- `Shift`: nitro.
- `1`–`4`: consumíveis.
- `R`: reposicionar.

Os controlos C++ estão sujeitos a validação depois da compilação do módulo. Para importar novamente os recursos pequenos sem reimportar as pistas, use `Scripts/Import_Secondary_Assets.py`; o script ignora assets que já existem.
