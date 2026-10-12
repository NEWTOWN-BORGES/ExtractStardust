# EXTRACT: STARDUST

Corrida de extração com podracers antigravidade numa ilha de 24 km, feita em **Unity 6 (URP)** a partir do RACESTARS (Godot).
A "Grande Corrida" do RACESTARS virou a **Expedição**: uma rota de A até B, com cerca de 120 km e uns 20 minutos de corrida.
Roda no PC (Windows) e no Android.

## Como jogar
- **PC (Windows):** abra `Builds/Windows/ExtractStardust.exe`. Funciona com teclado e com controle de PS4, PS5 ou Xbox.
- **Android (Galaxy A15):**
  1. Copie `Builds/Android/ExtractStardust.apk` para o celular (cabo USB, Google Drive ou WhatsApp para você mesmo).
  2. Abra o arquivo no celular e aceite **instalar de fontes desconhecidas**.
  3. Jogue com o celular deitado.
- **No editor:** no Unity Hub, clique em *Add → Add project from disk* e escolha a pasta `ExtractStardust`. Depois abra a cena `Assets/Stardust/Scenes/Main.unity` e aperte ▶.

## Modos
| Modo | O que é |
|---|---|
| **Expedição** | De A a B pela ilha toda: 30 portões e extração no fim. 15 bots. Tem porquinho, seguro e perdas de verdade. |
| **Circuitos** | Circuitos de várias voltas espalhados pela ilha. Inclui a **Cidadela Titã**, um circuito suspenso a 440 m com 2 saltos e desvios de emergência (os bots ainda caem lá na 2ª volta). 7 bots. |
| **Reta do Sal** | Arrancada de 3 km na planície de sal contra 3 bots. |
| **Explorar a ilha** | Sem relógio. Abra o MAPA para viajar para qualquer ponto. |
| **Tela dividida** | 2 jogadores no mesmo PC. Disponível em todos os eventos de corrida. |
| **Multiplayer Wi-Fi** | Até 4 jogadores na mesma rede: um cria a sala e os outros procuram (ou entram pelo IP). Não tem bots nem economia. |

## Controles
A nave **acelera sozinha**. Travão de mão + virar = **derrapar**: a nave fecha a curva sem perder velocidade.

| Ação | Teclado | PS4/PS5 | Toque |
|---|---|---|---|
| Virar | A / D | analógico esq. / D-pad | < > |
| Travão de mão (derrapar) | S ou Espaço | L2 ou Quadrado | TRAVAR |
| Nitro | W ou Shift | R2 ou X | NITRO |
| Consumível A / B | Q / E (ou 1 / 2) | L1 / R1 | A / B |
| Voltar ao caminho | R | Triângulo | menu de pausa |
| Câmera | C | Bola | — |
| Olhar em volta / centrar | — | analógico dir. / R3 | — |
| Mapa | M | Share / touchpad | MAPA |
| Pausa | Esc ou P | Options | II |

**Tela dividida:** o Jogador 1 usa WASD + Shift esquerdo + Q/E e o 1º controle. O Jogador 2 usa as setas + Shift direito + `.` e `/` e o 2º controle.

## Expedição: regras
- Chegar ao portal de **EXTRAÇÃO** preserva a nave. Ser rápido é bônus.
- Se a nave for destruída, as peças **não seguradas** vão para o **porquinho**.
  No fim, o porquinho é dividido entre quem extraiu, por ordem de chegada.
- Tem **postos de combustível** nos portões 10 e 20.
  A integridade cai com batidas, pousos duros e quedas. Dá para usar o gel de reparo e a célula de combustível.
- Medalhas, créditos e XP são calculados no fim. O progresso e a garagem ficam salvos.

## Gráficos
- **Terreno:** 36 blocos de 4 km com 8 camadas de textura (areia, relva, rocha triplanar nas encostas, estradas e margem molhada).
- **Céu e água:** céu com nuvens, sol e lua. Oceano e lagos com reflexo do céu e espuma.
- **Vegetação:** relva densa em volta da câmera e árvores com variação de cor.
- **Imagem:** pós-processamento ACES com bloom.
- **Modelos:** todos vêm do Blender (`WorldGen/blender/build_assets.py`): 85 modelos, incluindo os 6 podracers. As árvores têm uma versão detalhada que aparece perto da câmera (Média e Alta).
- **Qualidade:** em Opções há Baixa, Média e Alta. O celular começa em Baixa e o PC em Alta.

## Estrutura
| Pasta | Conteúdo |
|---|---|
| `WorldGen/tools/make_map.py` | Gera a ilha: relevo, biomas, rotas, saltos e eventos. |
| `WorldGen/tools/export_unity.py` | Exporta para o Unity. |
| `WorldGen/blender/build_assets.py` | Modelos do Blender. |
| `Assets/Stardust/Editor/WorldImporter.cs` | Menu **Stardust → Importar mundo**: texturas, materiais, modelos e terreno. |
| `Assets/Stardust/Editor/StardustTools.cs` | Builds Windows/Android. |
| `Assets/Stardust/Editor/IslandSimTest.cs` | Corrida sem tela para balancear os bots. |
| `Assets/Stardust/Scripts/Island` | Física da nave, bots, corrida, economia, HUD, câmera, rede LAN, Cidadela Titã. |
| `Assets/Stardust/Scripts/View` | App, menus, áudio. |
| `Assets/Stardust/Shaders` | Terreno, mundo, água, céu e relva (HLSL próprio). |
