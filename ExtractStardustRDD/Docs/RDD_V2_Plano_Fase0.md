# RED DUST DIVIDE V2 — Plano (resposta à Master Level Production Directive V2)

Estado: **aguarda aprovação**. Nada da V2 foi criado; o mapa atual fica como protótipo legado.
Fontes: diretiva V2 (este pedido), `Docs/referencias/01_Mapas_Pistas_Expedicoes_EXTRACT_STARDUST_v1_0.pdf` (GDD),
`Docs/referencias/rdd_v2_blueprint.webp` (planta nova), projeto Unity atual (só compatibilidade técnica).

---

## A. Plano de auditoria do projeto (Fase 0, sem modificar nada)

O que já sei do projeto (factos verificados nesta sessão):

| Item | Estado atual |
|---|---|
| Unity | 6000.3.26f1 · URP 17.3.0 · Input System 1.20 |
| Pacotes úteis | **Splines 2.9.1 (instalado)**, Terrain + TerrainPhysics (módulos nativos). Sem Terrain Tools, sem Addressables, sem AI Navigation |
| Blender | 5.2, automação por Python já usada em naves, pista, vegetação e megaestruturas |
| Software de terreno | nenhum instalado (sem Gaea / World Creator / Houdini) |
| Mapa legado | gerador Blender (JSON → corredor + terreno em FBX por setor), 105,7 km, estações de 5 m com secção real (`CourseData`/`CourseGraph`), `SectorStreamer` por distância, adereços em GPU instancing (`PropField`) |
| Checkpoints | por **distância de corrida** (não volumes) |
| IA | `BotBrain`: grafo de rotas + faixas laterais (u), personalidades, dificuldade |
| Corrida | `RaceSession` ponto A→B, meta por distância, último sobrevivente, Expedition Pool |
| Física | `CraftController`: mola de hover a 1,5 m, casco em caixa, aderência lateral limitada, drift, subida de degraus |
| Ferramentas de QA | `TrackProbe` (degraus/buracos/sobreposições/perfis/camadas), registo de batidas no autoteste `-rddextract` |

Ainda a inspecionar antes da Fase 1: o PDF do GDD (decisões aprovadas de mapas/rotas), `HoverSensor` (limites de aderência em paredes),
`ChaseCamera` (comportamento em paredes de 45–65°), regras de spawn/grelha, Physics/Quality/Tags do ProjectSettings.

## B. Ficheiros e cenas a inspecionar

- `Docs/referencias/01_Mapas_Pistas_Expedicoes_EXTRACT_STARDUST_v1_0.pdf`, `rdd_v2_blueprint.webp`
- `Assets/RedDust/Runtime/Vehicle/` (CraftController, CraftTuning, HoverSensor, CraftFactory)
- `Assets/RedDust/Runtime/Track/` (CourseData, CourseGraph, CourseRuntime, SectorStreamer, PropField)
- `Assets/RedDust/Runtime/AI/` (BotBrain, seguidor de rotas), `Runtime/Game/` (RaceSession, Racer, GameDirector)
- `Assets/RedDust/Runtime/Presentation/` (ChaseCamera, SpeedFx, EnvironmentRig)
- `Assets/RedDust/Editor/` (CourseImporter, BuildTools, TrackProbe), `Art/Blender/rdd_*.py`
- Cenas `RDD_Sandbox.unity` e `RDD_red_dust_divide.unity` (só leitura); `ProjectSettings/`, `Packages/manifest.json`

## C. Métricas do veículo a medir (Fase 1)

Dados já conhecidos: colisores (L×A×C) STRIX/VORTEX 3,4×1,0×7,0 m · WRAITH 2,8×0,9×7,2 · NOMAD 3,6×1,1×7,8 · BASTION 4,0×1,2×7,4;
largura visual V2 2,5–3,8 m; hover 1,5 m; velocidade máxima 118 m/s (425 km/h) sem boost.
**Velocidade média real medida no autoteste legado: ~102 m/s (367 km/h)** (piloto automático: 32,1 km em 5:14).

A medir por chassis (5) com piloto automático e registo em CSV:
1. velocidade máxima (com e sem boost), 0→300 km/h, travagem 400→250 km/h;
2. velocidade máxima estável por raio: R = 35 / 60 / 120 / 250 / 500 m (com aderência e com drift);
3. aceleração lateral máxima (g) e raio mínimo por velocidade;
4. ângulo de banking máximo sustentável por velocidade (10–75°) e velocidade mínima para wall-ride a 45 / 55 / 65°;
5. taxa máxima de transição de banking (°/m) sem perder contacto;
6. saltos: distância e altura por lábio (5–25°) e velocidade; velocidade de aterragem que dá dano; queda máxima sem dano;
7. velocidade média por arquétipo de setor (aberto, técnico, half-pipe, gruta) com 12–16 bots;
8. taxa de colisões por largura (7 / 10 / 14 / 24 / 35 m) com tráfego.

## D. Layout macro de 12 setores (da planta; comprimentos a reescalar com a Fase 1)

**Decisão crítica:** a planta mostra 34,6 km para 20 min (≈ 29 m/s de média). As naves fazem ~102 m/s:
34,6 km ≈ **6–8 min**; 20 min ≈ **90–120 km**. Proposta: construir a V2 com a planta (≈ 35 km, 7–8 min, densa e variada) e
decidir o formato de 20 min depois dos testes. Alternativas: escalar a planta ×2,7 (≈ 95 km) ou baixar as velocidades.

| # | Setor | km (planta) | Arquétipo | Largura útil | Banking | Raios | Cota alvo | Marco dominante | Rotas |
|---|---|---|---|---|---|---|---|---|---|
| 01 | START GRID | 0,0–2,8 | bacia aberta | 30–38 m | 0–10° | 500–1200 | 1 050 m | parede da bacia | grelha 5×4, várias linhas |
| 02 | MESA GATE | 2,8–5,6 | 1.ª compressão | 24–35 m | 10–20° | 250–500 | 1 150 | duas mesas + portal | SAFE canal baixo · RACING slickrock · SKILL plataforma |
| 03 | REDWALL BENDS | 5,6–8,4 | curvas inclinadas | 14–24 m | 10→20→30→40° | 250–800 | 1 250 | parede vermelha | linhas a várias alturas |
| 04 | TWIN ARCH | 8,4–11,2 | marco + salto | 14–30 m | 15–35° | 120–250 | 1 450 (pico) | dois arcos naturais | SAFE sob arco · RACING entre · SKILL alto + salto |
| 05 | DRY BASIN | 11,2–14,0 | bacia de canais | 24–35 m | 0–15° | 500–1200 | 1 250 | agulha distante | canais, ilhas de rocha, convergência |
| 06 | STONE CORRIDOR | 14,0–16,8 | canyon técnico + gruta | 10–16 (7–12 gargalo) | 10–30° | 60–120 | 1 150 | boca do canyon | S, túnel curto, cadeia de grutas |
| 07 | FOSSIL RIDGE | 16,8–20,1 | crista elevada | 14–24 m | 10–25° | 120–250 | 950 (baixo) → crista | costelas fósseis | SAFE baixo · RACING crista · SKILL falésia + salto |
| 08 | SINK TRENCH | 20,1–23,4 | fosso vertical | 14–30 m | 20–45° | 120–250 | 1 150 | o fosso | cima / meio / fundo, transferências |
| 09 | CANYON THROAT | 23,4–26,8 | garganta + half-pipe | 12–25 (half-pipe 40–60) | 30–65° | 250–500 | 1 250 | formação da garganta | curto, pouca ultrapassagem |
| 10 | SANCTUARY RUINS | 26,8–30,2 | ruínas na geologia | 14–30 m | 10–30° | 120–250 | 1 250 | ruínas | através, à volta, sob arco caído |
| 11 | EXTRACTION RIDGE | 30,2–34,6 | subida longa | 24–35 m | 10–25° | 500–1200 | 1 350 (pico) | crista/torre de extração | divisão final SAFE/RACING/SKILL |
| 12 | FINISH BASIN | 34,6 (+0,5 km de saída) | bacia final | 30–40 m | 0–10° | 500–1200 | 1 050 | bacia monumental | chegada larga, continuação pós-meta |

Regras de projeto: transições de banking graduais (máx. ≈ 2°/10 m), sem cruzamentos da pista consigo própria (verificado por ferramenta),
junções de rotas com cotas iguais na zona de fusão (o problema das "camadas" do mapa legado).

## E. Arquitetura de implementação em Unity

- Pasta nova `Assets/ExtractStardust/Expeditions/RedDustDivide_V2/` (Scenes, Terrain, Sectors, Splines, Landmarks, Materials, Rocks, Caves, VFX, AI, Checkpoints, Streaming, Editor, Debug); o legado fica intacto.
- **Dados:** ScriptableObjects `ExpeditionDefinition` e `SectorDefinition` (todos os campos da secção 30) + `RouteDefinition`.
- **Rotas:** Unity Splines (já instalado): um `SplineContainer` por rota (SAFE/RACING/SKILL) com `SplineData` de largura, banking,
  superfície e perfil de secção (vale, banking, half-pipe assimétrico, parede, plataforma, ravina, gruta).
- **Geologia primeiro:**
  - terreno macro em **tiles de Unity Terrain** (1 km, 1 m/px) gerados por ferramenta de editor (bacias, mesas, vales) e escavados pelas rotas;
  - superfícies de corrida íngremes (banking > 35°, half-pipes, paredes, grutas, plataformas) como **malhas por varrimento de secção**
    geradas em C# no editor (iteração rápida, sem esperas de 15 min do Blender), com LODs e colisores;
  - peças-herói (Twin Arch, costelas do Fossil Ridge, Sanctuary Ruins, grutas) em **Blender Python** → FBX em `Landmarks/`.
- **Checkpoints:** volumes largos (secção inteira, paredes incluídas) com IDs `Sector03_Main_A`, `Sector03_Skill_B`, `Sector03_Reconnect_C`…
- **Ligação ao jogo:** adaptador que converte o grafo V2 para o formato `CourseGraph` atual (estações de 5 m), para manter
  RaceSession, BotBrain, HUD, seta de direção, reposição e as sondas de QA a funcionar.
- **Ferramentas:** `RedDustExpeditionBuilder`, `TerrainChunkBuilder`, `SectionSweepGenerator` (banking/half-pipe), `JumpProfileGenerator`,
  `CheckpointGenerator`, `LandmarkPlacementTool`, `StreamingSectorManager`, `RaceDebugOverlay`; QA com `TrackProbe` (degraus, buracos,
  sobreposições) e registo de batidas.

## F. Estratégia de streaming

- Cena global (céu, sol, dados das rotas, **HLOD do horizonte** de todos os setores) + 12 cenas aditivas de setor.
- `StreamingSectorManager`: setor atual + 2 à frente carregados, 1 atrás; carga assíncrona espalhada por frames;
  com 2 jogadores (PvP), a união dos setores de ambos.
- Adereços por GPU instancing por setor; LOD/HLOD; Android com menos densidade, sombra mais curta e terreno mais grosso.
- Medir: tempo de carga por setor, picos de frame, memória por setor (alvo Android).
- Precisão: com a origem no centro da expedição, ±20 km dão ≈ 2 mm de precisão; testo 40 km na Fase 1 e só implemento
  origem flutuante se aparecer tremor (em PvP de ecrã dividido a origem flutuante é mais difícil).

## G. Grafo de rotas da IA

- Nós (divisões/reuniões) e arestas (linhas) com categoria: SAFE_LINE, RACING_LINE_A, RACING_LINE_B, HIGH_WALL, LOW_WALL,
  SKILL_SHORTCUT, RECOVERY_LINE.
- Cada linha tem: spline, perfil lateral/vertical (u e altura na parede), velocidade mín./máx., risco, comprimento, ganho de tempo,
  marcador de preparação (ex.: estar na HIGH_WALL aos 7,8 km para entrar no atalho dos 8,2 km).
- Escolha por personalidade, dificuldade, posição, tráfego, casco e build; dificuldade alta = melhores linhas, nunca batota de velocidade.
- RECOVERY_LINE para reposição e para bots que saem da linha. Meta da Fase 5: 100% dos bots completam cada rota válida.

## H. Riscos e incógnitas

1. **Velocidade × comprimento** (secção D) — decisão do produtor.
2. Física de hover em paredes de 45–65°+: o limite real da aderência é desconhecido até à Fase 1.
3. Heightmaps não fazem paredes verticais, grutas nem saliências → solução híbrida (malhas por varrimento + peças Blender).
4. Junções de rotas: no legado criaram camadas e degraus → regras de cota e ferramenta de verificação.
5. Larguras de 7–12 m a ~100 m/s com 15–20 naves podem gerar colisões em cadeia → medir na Fase 1.
6. Android: o APK do laboratório tem 1,2 GB → orçamentos rígidos por setor.
7. IA em linhas verticais (HIGH/LOW_WALL) exige novo comportamento no BotBrain.
8. Tempos de build e de envio (upload ≈ 137 KB/s; uma build de 600 MB demora ~1 h a subir).
9. Sem software de terreno instalado: se quiseres Gaea/World Creator, a ligação passa por heightmaps exportados.

## I. Lista exata de tarefas da Fase 1 (depois de aprovares)

1. Criar o ramo `claude/red-dust-divide-v2` (o `main` fica intacto) e o esqueleto de pastas da V2 com README.
2. Ler o GDD (PDF) e registar as decisões aprovadas que afetam a V2 em `Docs/RDD_V2_Decisoes.md`.
3. Gerar por código a cena **Metrics Lab** (`V2/Debug/`): reta de 4 km; círculos R 35/60/120/250/500 m planos e com banking
   10/25/45/65°; half-pipes assimétricos de 40/60/90 m; lábios de salto 5–25° com zonas de aterragem; corredores de 7/10/14/24/35 m; quedas de 5–40 m.
4. Escrever o executor automático (modo batch): os 5 chassis × build de série, piloto automático, CSV com as métricas da secção C.
5. Medir a velocidade média por arquétipo com 12–16 bots e a taxa de colisão por largura.
6. Testar a precisão a 40 km da origem (tremor de física/câmara).
7. Calcular: comprimento para 20 min e para a fatia vertical de 6–8 min; larguras, raios e banking recomendados por arquétipo.
8. Entregar `Docs/RDD_V2_Metricas.md` com tabelas e recomendações. **PARAR** para aprovação da Fase 2 (plano macro com coordenadas).
