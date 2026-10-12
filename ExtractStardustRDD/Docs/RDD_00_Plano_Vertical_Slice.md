# EXTRACT: STARDUST — RED DUST DIVIDE
## Plano de pré-produção e vertical slice (para aprovação)

Versão 0.1 · 12/10/2026 · Fontes: Doc 01 (Mapas/Pistas/Expedições), Doc 02 (Naves/Equipamentos), Doc 03 (Itens/Consumíveis/Economia) v1.0, prompt de estúdio e imagens de referência.

> **Estado:** PLANO. Nada de produção de conteúdo em larga escala foi feito. Aguarda aprovação.

---

## 0. Milestone 0 — Auditoria do projeto atual

| Item | Encontrado |
|---|---|
| Unity | 6000.3.26f1 |
| Render pipeline | URP 17.3: Forward+ no PC, Forward no Android. Shaders HLSL próprios (terreno, mundo, água, céu, relva) com função PBR própria (`SD_ShadePBR`). |
| Input | Input System 1.20: teclado, gamepad (PS4/PS5/Xbox) e toque. |
| Pacotes | Só URP, Input System, uGUI e VS. **Não tem** Splines, Addressables, Test Framework nem Cinemachine. |
| Cena | Só `Assets/Stardust/Scenes/Main.unity`; tudo é criado por código a partir de um `Bootstrap`. |
| Controlador da nave | `Hovercraft.cs`: cinemático, com sondas de chão em **raycast vertical (Vector3.down)**, colisão por BoxCast e só o yaw controlado. **Não suporta** bank > ~45°, half-pipe nem wall ride, porque procura o chão em −Y do mundo e não em −Y da nave. |
| Física | Fixed timestep 0,02 s (o jogo atual usa o seu próprio passo de 1/60). Sem Rigidbody nas naves. |
| Mapa | Ilha procedural de 24 km (open world de teste), gerada em Python → Blender → importador. |
| Naves | 6 modelos procedurais do Blender. **Atenção (IP):** `racer_twin/hammer/needle/ram/manta` usam dois motores ligados por cabos ao cockpit, ou seja, a disposição de podracer que o Doc 01 §15.1 e o prompt §16 proíbem copiar. **Não podem entrar no novo modo.** |
| Economia/save | `Items.cs`: `SaveData` em JSON no `persistentDataPath`, com raridades, seguro, porquinho e CR. |
| Rede | `LanNet.cs`: UDP numa estrela com relay e descoberta LAN. Sem servidor autoritativo nem backend. |
| Ferramentas | Builds em batch (Windows/Android), simulação headless de corrida, autotests com screenshots. |

**Conclusão:** do código atual só se reaproveita o **know-how** e algumas peças de infraestrutura: build tools, padrão de autotest/sim headless, perfis de qualidade, UIKit, áudio sintetizado e pipeline Blender em batch. Física, mundo, IA, economia e naves serão **novos**, como pediu ("tudo novo").

---

## A. Entendimento do projeto (técnico)

EXTRACT: STARDUST é um **extraction racer**: uma corrida A→B longa (~20 min) em que cada piloto traz uma **build persistente** (chassis + módulos com instâncias únicas), gere **integridade, combustível, temperatura e energia/boost**, e só **preserva** o que leva se cruzar a meta (**EXTRACTED**). Quem é destruído perde os componentes elegíveis não segurados. Esses itens reais vão para um **Expedition Pool**, cujo valor em ✦ é só **avaliação**, e no fim são distribuídos automaticamente aos sobreviventes por classificação. A moeda (**STARDUST ✦**) é segura na carteira; o risco está no equipamento.

A primeira expedição, **RED DUST DIVIDE**, é um canyon natural fictício (Utah/Arizona) em que **a geologia é a pista**: não há asfalto, rails, rampas de metal nem pista construída. A corrida usa banks progressivos até ~50–65°, half-pipes naturais de quilómetros, wall rides curtos, saltos geológicos, cavernas e rotas **SAFE / RACING / SKILL**. Os pilotos são 15–20, numa grelha **5 por fila** ligeiramente desencontrada.

Tecnicamente isto exige:
1. Uma **física antigravidade relativa à superfície**, com sondas no eixo da nave, alinhamento progressivo e aderência dependente da velocidade.
2. **Geometria de pista não-heightfield** (paredes > 60°, cavernas, overhangs), gerada a partir de **metadados de design** sobre splines invisíveis.
3. **IA num grafo de linhas 2D**: progresso ao longo da rota × posição na secção transversal.
4. **Streaming por setores**.
5. Uma **economia com autoridade**: ledger, instâncias únicas e operações idempotentes. Na demo é uma autoridade local com a mesma interface que um servidor teria.

---

## B. Regras não negociáveis (preservadas)

- **Moeda e economia**
  - STARDUST ✦ substitui CR.
  - O pool mostra a **avaliação** dos itens reais. Nunca cria moeda nem itens, nunca duplica e nunca inventa um Lendário.
  - Distribuição automática no fim, sem esperas e sem loot em pista.
- **Seguro e estados**
  - 1 peça segurada por expedição.
  - Estados VICTORY/EXTRACTED, EXTRACTED, EXTRACTION FAILED, STRANDED e ABANDONED. EXTRACTED ≠ VICTORY.
- **Formato da prova**
  - A→B, sem voltas, ~20 min, 15–20 racers.
  - Grelha 5 por fila, até 4 filas, desencontrada.
- **Pista**
  - Sem asfalto, betão, pista metálica, rails ou barreiras de circuito. A geologia é a pista.
  - Transições de bank graduais, sempre em centenas de metros.
  - Saltos sempre naturais e com receção legível.
  - Cavernas sem cilindros perfeitos.
  - Limites naturais; paredes invisíveis só para segurança técnica.
  - Splines são ferramentas invisíveis e nunca geram fita de pista.
- **Naves e equipamento**
  - 5 chassis horizontais (STRIX, WRAITH, NOMAD, BASTION, VORTEX) com os stats e passivas dos documentos.
  - Raridade não é escada linear (budget 10/13/16/20/23+perk, caps por família).
  - Módulos importantes mudam a aparência física. Identidade 60% chassis / 40% build.
  - Lendário mantém instância, serial, rolls e perk ao mudar de dono.
  - Supply Caches com **10 itens**, sem chassis. Elite tem 4% de Lendário **por caixa**.
  - Epic/Lendário não se vendem diretamente. Venda de duplicados a ~25%. Sem conversão 5 Rare → 1 Epic.
- **Plataformas e IP**
  - Mesma rota e regras no PC e no Android; só a qualidade visual muda.
  - IP original: nada de silhuetas, motores, logos ou sons de Star Wars.
- **Processo**
  - Blockout antes de arte.
  - Nenhuma funcionalidade é dada como pronta sem teste.

---

## C. Conflitos entre documentos e resolução proposta

| # | Conflito | Onde | Resolução proposta |
|---|---|---|---|
| C1 | Moeda CR vs STARDUST | Doc 01 §9–10 vs Doc 03 | **Resolvido pelo override:** STARDUST ✦. "CR" no Doc 01 lê-se como ✦ de avaliação. |
| C2 | Valores dos itens (Comum ~100 CR … Lendário ~8 500) vs (~500 ✦ … ~18 000 ✦) | Doc 01 §10.2/B.2 vs Doc 03 §10 | **Doc 03** (economia). |
| C3 | Prémios por posição (11 posições, 1 500…250) vs (20 posições, 1 600…225) | Doc 01 §10.3 vs Doc 03 §3 | **Doc 03**, mais bónus EXTRACTED de +250. |
| C4 | Proezas: valores e teto (~2 000) vs teto de 500 ✦; "Última Gota" = não reabastecer vs ≤3% de combustível | Doc 01 §10.4 vs Doc 03 §4 | **Doc 03.** Vitória Imaculada substitui as sobrepostas. |
| C5 | Slots: 6 (Motor, Propulsor, Estabilizador, Blindagem, Reator, Navegador) vs 8 famílias (+ Tail, Cooling) e sockets próprios | Doc 01 §7.1 vs Doc 02 §3 | **Doc 02.** |
| C6 | Comprimentos das secções vs tempos do ritmo. Ex.: Red Wall ~3 km mas ocupa 6:00–9:00; a 200 km/h, 3 km duram ~55 s. | Doc 01 §17/§19 | **Para decisão.** Proposta: manter os comprimentos-assinatura (Red Wall 3 km, half-pipe 2,5–4 km, Hollow 2 km) e encher o resto do bloco temporal com terreno de ligação. O comprimento total sai da velocidade medida (o Doc 01 §19 já o autoriza). |
| C7 | Velocidade não definida no design (só "validar em protótipo"), mas bank 50° em R 200 m tem velocidade de equilíbrio ≈ 48 m/s | Física vs §17 | **Proposta (TARGET DE TUNING):** cruzeiro 55–65 m/s (200–235 km/h), boost +25%. Com isto os banks e raios do documento funcionam fisicamente. |
| C8 | "Itens elegíveis não segurados podem ser perdidos": quantos? | Doc 01 §9.1 (não define) | **Para decisão.** Proposta: todos os componentes equipados não segurados ficam em risco e, na destruição, perdem-se **até 3** sorteados com peso por valor (o resto volta). |
| C9 | Stardust "vem principalmente do online", mas não há servidor/backend | Doc 03 §1/§13 | **Proposta:** interface `IEconomyAuthority` com implementação **LocalAuthority** (ledger, idempotência e rolls fora da UI) para a demo offline/bots/LAN, marcada "DEMO LOCAL". Um backend real substitui-a sem mudar o jogo. |
| C10 | Desbloqueio dos 4 chassis além do STRIX está em aberto | Doc 02 §11/§15 | **Proposta:** na demo, os 5 disponíveis (marcado como regra de teste, não final). |
| C11 | Abastecimento: "Última Gota" do Doc 01 implica postos; o Doc 03 só tem Fuel Cell | Doc 01 vs Doc 03 | **Proposta:** sem postos na RED DUST DIVIDE. Combustível só por Fuel Cell (custo de slot/tempo). |
| C12 | Imagens de referência: pórtico "EXTRACT STARDUST", bancadas, faixa listrada no topo de uma parede | PNG vs Doc 01 §15.2 e prompt §3 | **Regra do documento ganha.** Pórtico e público só na largada/extração ("pequena infraestrutura humana"). Na rota, no máximo marcadores raros (bandeiras), **nunca rails**. |
| C13 | Pedido antigo de "bots podracer tipo Star Wars" | Pedido anterior vs regra de IP | **Regra de IP ganha:** naves originais seguindo o Doc 02. Os modelos podracer atuais ficam fora do novo modo. |
| C14 | Energia vs Boost: o Doc 02 separa Energy (Reator) do stat Boost; o Doc 01 diz "Boost/energia" | Doc 01 §13 vs Doc 02 §3 | **Proposta:** o boost consome **Energia** (barra). O Reator define capacidade e recarga. O stat Boost define a força do impulso. O boost também gera **Calor**. |
| C15 | Slots de consumíveis não definidos | Docs 01/03 | **Proposta:** 3 slots, até 2 unidades por slot (custo de oportunidade). TARGET. |

---

## D. Arquitetura Unity proposta

**Decisão estrutural (para aprovação):**
- Manter o **mesmo projeto Unity**, com um **módulo novo isolado** em `Assets/RedDust/` e assemblies próprias, sem nenhuma referência ao código da ilha.
- A ilha fica no disco como **legado de teste**: não é apagada, mas sai das builds.
- Vantagem: reaproveita a instalação, a licença, o URP e os scripts de build.
- Alternativa: um projeto Unity separado. Isola mais, mas duplica ~5 GB de Library e as ferramentas.

**Assemblies (`.asmdef`):**
- `RedDust.Core`: dados puros, economia, regras e resultados; testável sem cenas.
- `RedDust.Vehicle`: física, stats, assembler, passivas.
- `RedDust.Track`: segmentos, splines, checkpoints, streaming, geração de geologia.
- `RedDust.AI`: grafo de linhas, decisões, perfis.
- `RedDust.Race`: orquestra a corrida, estados, pool, resultados.
- `RedDust.Presentation`: câmera, HUD, áudio, VFX, Hangar.
- `RedDust.Editor`: ferramentas, validadores, gizmos, batch.
- `RedDust.Tests`: Unity Test Framework.

**Cenas:**
- `RDD_Boot`: serviços, perfil de qualidade, save.
- `RDD_Hangar`: garagem 3D, loja, caches, loadout, seguro.
- `RDD_Sandbox`: Milestone 1.
- `RDD_Race`: núcleo com câmera, HUD, managers e grelha. Os setores carregam aditivamente: `RDD_S01_Basin`, `RDD_S02_RedWall`, `RDD_S03_Wash`, `RDD_S04_Hollow`.

**ScriptableObjects (definições imutáveis):**
- `ShipChassisDefinition`: stats base, classe de tamanho, lista de sockets, passiva, prefab do core, envelope físico.
- `EquipmentDefinition`: família, fabricante, raridade-base, regras de stat, ranges de roll, compatibilidade S/M/L, prefab, massa, valor-base, perks possíveis.
- `ConsumableDefinition`: efeito, tempo de uso, preço.
- `RarityTable`: budget, cor, caps por família.
- `CacheDefinition`: preço, odds, garantias.
- `EconomyConfig`: prémios por posição, proezas, contratos, multiplicadores.
- `TrackSegmentDefinition` (ver E), `RouteGraphAsset`, `BotPersonaDefinition`, `QualityProfile` (PC/Android).

**Dados de runtime (mutáveis, persistentes):**
- `EquipmentInstance`: InstanceId (GUID), DefinitionId, Rarity, Rolls, Perk, Drawback, OwnerId, Insured, Source, Serial.
- `ShipBuild`, `PlayerWallet`, `LedgerEntry`, `ContractProgress`.

**Sistemas:**
- **Nave:** `ShipAssembler`, `StatResolver` (puro), `BuildValidator` (puro), `HangarPreview`.
- **Corrida:** `RaceDirector` (estados da corrida), `GridSpawner5x4`, `CheckpointSystem`, `DamageModel`, `ResourceModel` (combustível/calor/energia), `ConsumableRunner`.
- **Mundo:** `SectorStreamer`, `FloatingOrigin`.
- **Economia e transversais:** `ExpeditionPool`, `ResultsResolver`, `TelemetryRecorder`.

**Fronteiras de rede/autoridade:**
- O cliente envia apenas **input** e **intenções**: comprar, equipar, segurar.
- `IRaceAuthority` valida checkpoints, ordem, dano crítico e estado final.
- `IEconomyAuthority` valida carteira, compras, rolls, IDs, serial, perdas, pool e transferências. Todas as operações levam uma `idempotencyKey` e escrevem no ledger.
- **Demo:** `LocalAuthority` corre no mesmo processo (honestamente "não é um servidor").
- **Futuro:** servidor dedicado e backend sem alterar o jogo.

**Streaming:**
- Setores de ~2–4 km como cenas aditivas.
- Preload de 1–2 setores à frente do **líder humano/pelotão**; os de trás são descarregados.
- **Floating origin:** rebase quando a câmera se afasta mais de 4 km da origem; rota contida em ±12 km.
- Addressables entra só quando o tamanho o justificar (Milestone 9).

---

## E. Plano de blockout da RED DUST DIVIDE

### E.1 Método ("a geologia vem primeiro")

1. **Macro-relevo do planalto** num heightfield de baixa frequência: mesas, falésias e vales com estratos.
2. **Canais de erosão** esculpidos nesse relevo ao longo de **splines invisíveis**. Cada segmento tem uma **secção transversal paramétrica**:
   - tipos Flat, Bank, HalfPipe, Wall, Cave, Bowl;
   - parâmetros de largura útil, raio de parede, ângulo de bank, assimetria e profundidade.
3. A **geometria da pista é uma malha esculpida** (não heightfield), varrida pela secção com ruído geológico:
   - lajes e estratos;
   - irregularidade lateral de ±1–4 m;
   - quebras e degraus;
   - overhangs e tetos nas cavernas.
   Não fica nenhuma borda reta nem faixa regular.
4. A secção transversal dá às linhas de corrida uma coordenada **u ∈ [−1, 1]**: fundo, parede média, parede alta. A IA e os checkpoints usam esta coordenada.
5. **Blender** faz a geologia-herói depois do blockout validado: arcos, fins, balanced rock, hoodoos, boca de caverna e lajes.

Tudo é gerado por ferramenta de editor a partir de `TrackSegmentDefinition`. Mudar um número regenera o setor.

### E.2 Campos de `TrackSegmentDefinition`

`SegmentID`, `MainSpline`, `AltSplines[]`, `WidthTarget` (curva), `BankTarget` (curva), `CurveRadiusTarget`, `CrossSection` (+ parâmetros), `SurfaceType` (Sand, Slickrock, Gravel, DeepSand, Rock), `RiskLevel`, `ShortcutID`, `StreamingBounds`, `RecoveryZones[]`, `Checkpoints[]`, `Landmarks[]`, `ExpectedTime`, `TelemetryID`.

### E.3 Vertical slice: ~7 min, ~21–23 km

Valores calculados a ~52 m/s de média (TARGET).

| Setor | Tempo | Comprimento | Largura útil | Bank | Raio | Conteúdo |
|---|---|---|---|---|---|---|
| **S01 THE BASIN (reduzida)** | 0:00–1:10 | ~3,5 km | 34 m na largada → 24–30 m | 0–12° | mega arco de 900 m | Grelha 5×4 em slickrock com areia compactada; ondulações; 2 flow jumps. **Bifurcação 1** aos ~2,2 km: **SAFE** pelo leito largo (+6% de distância); **RACING** pelas lajes partidas com flow jumps (12–16 m). Reunião numa bacia. Landmark: mesa com arco (estilo Mesa Arch) visível desde a largada. |
| **S02 THE RED WALL** | 1:10–3:00 | ~1 km de aproximação + **3 km de parede** | 16–24 m (área total de parede ~60 m de altura) | **8° → 15° → 25° → 35° → 50°** em 3 km | **700 → 200 m** | Três alturas de linha. **Bifurcação 2 (SKILL):** quem estiver na **linha alta 400 m antes** vê uma fenda no topo da parede: **wall jump** natural sobre um fin para uma laje superior (5–9 m) que corta ~300 m. Linha baixa = RACING. Landmark: agulha de 40 m no fim (estilo balanced rock). |
| **S03 THE WASH** | 3:00–5:40 | ~3,5 km | Half-pipe com 40 → 90 m de secção, **assimétrico** (parede esquerda 25 m, direita 50 m) | Paredes até 55–60° | 250–500 m, sinuoso | Fundo curto e congestionado; parede média para ultrapassar. **Bifurcação 3:** wall jump da parede alta direita para uma **bancada superior** (SKILL, 6–9 m) que volta a entrar 600 m depois. Termina numa **natural bowl** que junta as linhas. |
| **S04 THE HOLLOW (saída)** | 5:40–7:00 | ~1,4 km de caverna + 0,8 km de final | 12–30 m variável | Bank interno até 35°, trecho côncavo | 90–200 m | Entrada larga parcialmente colapsada; curva; descida; bank; trecho half-pipe; **câmara** de 70 m; **bifurcação interna** em dois braços (curto/escuro vs largo/iluminado por fissuras); **salto de rocha** de saída "violenta" para o exterior; reta final ondulada até à **zona de EXTRAÇÃO** (pórtico funcional pequeno). |

### E.4 Regras transversais

- **Ritmo:** mudança significativa de leitura a cada 30–60 s. A tabela acima dá ~1 a cada 35 s.
- **Checkpoints:** volumes largos que cobrem toda a secção transversal, todas as alturas e as sub-rotas. Atalhos legítimos têm a sua cadeia própria.
- **Limites naturais:**
  - falésias, areia profunda (lenta) e ravinas;
  - zona de recovery em cada setor;
  - parede invisível só como rede de segurança muito acima e fora da leitura do jogador.
- **20 min completos (depois da validação):** BASIN, BROKEN MESA, SHAFER FALL, RED WALL, HORSESHOE DROP, THE WASH, ARCHES RUN, THE HOLLOW, WHITE RIM. São ~60–65 km à velocidade proposta, com a rota enrolada num quadrado de ±12 km para precisão numérica.

---

## F. Física antigravidade

**Modelo:**
- `Rigidbody` dinâmico com interpolação e massa vinda dos dados.
- Fixed timestep de **1/90 s** (TARGET; validar entre 1/60 e 1/120).
- CCD *continuous speculative* nas naves.

**Sondas:**
- 5 **SphereCasts** (r = 0,6 m) ao longo de **−up da nave** (não do mundo): 4 cantos + centro.
- **Look-ahead:** uma sonda extra à frente, proporcional à velocidade, antecipa mudanças de normal em lips e cristas.

**Forças:**
- **Hover:** mola-amortecedor por sonda até à altura alvo (~1,6 m, TARGET), com limite de força.
- **Aderência à superfície:** força para −normal proporcional a v² com teto. É ela que permite wall ride.
  - Abaixo da velocidade mínima de parede (TARGET ~35 m/s a 65°) a aderência cai e a nave desliza ou cai de forma previsível.
  - Em superfícies côncavas (half-pipe, bank em curva) a própria geometria dá a força centrípeta.
- **Propulsão:** ao longo do forward projetado na superfície. Drag quadrático; o stat Speed define o equilíbrio.
- **Controlo lateral:** grip lateral tunável. Handling define a taxa de yaw. Stability define o amortecimento de roll/pitch.

**Alinhamento:**
- Orientação alvo = normal média das sondas, suavizada.
- Correção limitada por **graus/segundo** (Stability), sem snap.
- **Assistência em banks extremos:** mais aderência quando a normal muda progressivamente.

**No ar:**
- Gravidade total.
- Controlo aéreo limitado (pitch/roll ±, do stat Stability e das asas).
- Auto-nivelamento suave para a normal prevista no ponto de aterragem.

**Saltos:** vêm só da geometria (lip). Não há impulso artificial, mas o hover "solta" a nave quando a curvatura convexa excede a aderência.

**Dano:**
- `DamageModel` separado.
- Impacto = componente da velocidade relativa ao longo da normal do contacto, acima de um limiar, × multiplicador de ângulo × resistência (Hull/Armor).
- **Aterragem** = velocidade vertical relativa à normal acima de um limiar.
- Contacto entre naves: impulso lateral (BASTION −25% de deslocamento) e dano baixo.

**Estados de integridade (100/75/50/25/10/0):** visuais (faíscas, fumo, peças soltas) e mecânicos (a partir de 50%, ligeira perda de potência; a partir de 25%, instabilidade).

**Recursos:**
- **Combustível:** consumo por potência (Efficiency).
- **Calor:** sobe com boost, desce com Cooling; sobreaquecimento corta o boost.
- **Energia:** capacidade e recarga do Reator; o boost gasta-a.

**Passivas:** implementadas como `IPassive` com gatilhos medidos (bank > 35° durante 2,5 s, temperatura < 75% durante 60 s, etc.).

**Câmera:** chase com FOV por velocidade, recuo em aceleração, lag lateral, comportamento em salto, impulso de aterragem, **compensação de bank** (o horizonte inclina no máximo ~40% do roll da nave), shake configurável e anti-colisão por SphereCast. Opções de motion blur, shake e FOV.

---

## G. Plano da IA

**Grafo de rotas:**
- Cada segmento tem **linhas** como curvas de u(s), a posição na secção transversal: SAFE, RACING, SKILL, WALL_LEFT, WALL_RIGHT, SHORTCUT, RECOVERY.
- Nós de decisão antes de cada bifurcação, com **ponto de compromisso**. A linha alta do Red Wall tem de ser escolhida 400 m antes.

**Pilotagem:**
- O bot usa **a mesma física** e o mesmo input que o jogador (acelerador, direção, boost).
- **Pure pursuit** sobre a linha escolhida + controlo de velocidade por curvatura, bank previsto e aderência disponível. Calculado offline por segmento: perfil de "velocidade segura".

**Escolhas:** custo dinâmico = tempo esperado + risco × (1 − tolerância do perfil) + tráfego (ocupação da linha) + integridade (com pouco Hull, foge de SKILL) + posição (atrás arrisca mais) + confiança (falhas recentes).
- **Controlo de densidade:** penalidade se muitos bots escolherem o mesmo atalho.

**Ultrapassagem:** deteção de nave à frente na mesma linha → mudança de u para uma linha paralela (em half-pipe sobe a parede). Respeita a distância lateral.

**Perfis** (`BotPersonaDefinition`):

| Perfil | Comportamento |
|---|---|
| AGGRESSIVE | Risco alto, contacto aceito. |
| SURVIVOR | Prioriza Hull; usa SAFE; repara cedo. |
| TECHNICAL | Banks/SKILL. |
| SPEEDSTER | Secções abertas, boost. |
| ROOKIE | Erros controlados: entrada tardia, linha inconsistente. |

**Dificuldade:** melhora linhas, gestão de boost/calor, conhecimento de atalhos, desvio e uso de consumíveis. **Nunca dá velocidade escondida.**

**Recovery:** linha RECOVERY e reposicionamento em zonas de recovery quando o bot falha um salto ou perde orientação. O tempo perdido é real.

**LOD de IA:** bots longe de qualquer humano correm com física simplificada (menos sondas) em vez de "fantasma estatístico". Validar o custo no Android.

---

## H. Naves e equipamento

**Chassis:** STRIX (M), WRAITH (S/M), NOMAD (M/L), BASTION (L), VORTEX (M), com os stats do Doc 02 §2 e as passivas do §4. O mapeamento stat→física é feito por curvas TARGET (ex.: Speed 72 → ~62 m/s).

**Sockets por chassis**, lidos da definição e não de uma lista fixa:

| Chassis | Sockets |
|---|---|
| Base (STRIX) | `Socket_Engine`, `Socket_Propulsion_L/R`, `Socket_Wing_L/R`, `Socket_Tail`, `Socket_Armor_L/R`, `Socket_Cooling`, `Socket_Reactor`, `Socket_Utility` |
| VORTEX | + `Socket_Propulsion_Center` (3 propulsores) |
| BASTION | + `Socket_Armor_Secondary` |
| NOMAD | + `Socket_Aux_Fuel`, 2.º `Utility` |

**Arte das naves:**
- Nova, no Blender, a seguir à linguagem visual do Doc 02 §4–5.
- **Silhouette test:** as 5 têm de se distinguir em preto, e nenhuma pode ter motores separados ligados por cabos.
- Cada módulo é um prefab com ponto de encaixe, classe S/M/L e **massa por dados**.
- O mesh **não altera** o collider nem o centro de massa: o envelope físico vem do chassis + massa dos dados.

**Conteúdo (28 componentes):**

| Família | Quantidade |
|---|---|
| Motores | 6 |
| Asas/estabilizadores | 5 |
| Blindagens | 4 |
| Reatores | 4 |
| Cooling | 3 |
| Caudas | 3 |
| Nav/Utility | 3 |

Lendários: **HELIOS V-9** (Reator), **REDLINE-X** (Motor), **AEGIS FRAME** (Armor). Pelo menos 3 presets por chassis (QA/bots).

**StatResolver:** final = base do chassis + Σ (rolls dos módulos) + perks + passivas ativas, com caps por família. Não altera assets.

**BuildValidator:** rejeita slot duplicado, classe de tamanho incompatível, budget excedido, cap excedido e conflito de famílias.

**Rolls:** cada definição tem faixas por stat permitido pela família; o roll gasta o budget da raridade e penalizações devolvem budget (custo por stat em curva).

---

## I. Economia

**Carteira e prémios:**
- Carteira ✦: saldo inicial 1 000; First Extraction +500 uma vez.
- Prémio por posição (tabela de 20), EXTRACTED +250, proezas (teto de 500, Vitória Imaculada substitui) e contratos (8).
- Multiplicador por duração: o vertical slice de ~7 min dá **×0,50**.

**Loja e caches:**
- Consumíveis 80–220 ✦.
- Loja de componentes: Common 450–650, Uncommon 900–1 300, Rare 2 400–3 500 em rotação.
- Supply Caches de **10 itens**, com ~4–6 componentes + 4–6 consumíveis e diversidade de categorias:
  - **Standard** 2 500 ✦;
  - **Advanced** 6 000 ✦, mínimo 1 Rare;
  - **Elite** 13 500 ✦ (10 000 opcional em build de teste): 1 Epic garantido + ≥4 Rare+ + **um** roll de 4% para Lendário por caixa.
- Prototype Cache só como recompensa de teste.

**Itens persistentes:** `EquipmentInstance` com GUID e Serial nos Lendários. Toda a criação passa por `IEconomyAuthority` e fica no ledger (source/sink).

**Pool e distribuição:**
- **Expedition Pool:** só recebe instâncias reais perdidas por destruídos; a peça segurada nunca entra.
- HUD mostra "EXPEDITION POOL ✦ X (avaliação)" e notificações de raridade ("LEGENDARY ITEM ADDED").
- **Distribuição:** ordenar os itens por valor e os sobreviventes por posição. Fazer rondas em serpentina limitada (1.º recebe o mais valioso, 2.º o seguinte…) até acabarem os itens. Nunca duplica nem cria.

**Venda e regras de abandono:**
- Venda a 25% do valor. Sem conversão de raridade.
- ABANDONED depois de os itens entrarem em risco **não** os preserva (anti-exploit).

---

## J. Performance

**Orçamentos (TARGET):**

| Plataforma | FPS | Draw calls | Triângulos visíveis | Sombras |
|---|---|---|---|---|
| PC médio (GTX 1650) | 60 | ≤ 2 500 | ≤ 3 M | 3 cascatas, 400 m |
| Android (Galaxy A15) | 30 estáveis | ≤ 350 | ≤ 400 k | 1 cascata, 80 m |

- Galaxy A15: resolução dinâmica, VFX de poeira reduzidos e qualidade adaptativa com consciência térmica.

**Técnicas:**
- Streaming por setores (cenas aditivas).
- LOD0–3 nas malhas de geologia, geradas pela própria ferramenta (decimação por distância) e HLOD por setor.
- Occlusion culling nos canyons e cavernas.
- GPU instancing para rochas e detritos; pooling de VFX.
- **Poeira híbrida:** partículas perto da nave + camadas de fog/dust baratas ao longe.

**Precisão numérica:** floating origin com rebase a cada 4 km; rota contida em ±12 km.

**Medição contínua:** FrameTimingManager, memória e hitches de streaming registados pela telemetria desde o blockout. No Android, testar no aparelho real.

---

## K. Backlog do vertical slice (por ordem de dependência)

1. **M0** Auditoria ✔ (este documento) + aprovação das decisões C6–C15 e da estrutura do projeto.
2. **M1 — Sandbox técnica**
   - Setup do módulo `RedDust` (asmdefs, cenas, pacotes: Splines, Test Framework).
   - Nave placeholder (caixa com dimensões do STRIX) + física (F).
   - Pista de testes: plano, bank 30°, bank 50°, half-pipe de 300 m, salto natural, transição para parede de 65°, curva de caverna.
   - Câmera + overlays de debug (normais, sondas, bank, velocidade, contactos, FPS).
   - Telemetria de física.
3. **M2 — Blockout RED DUST DIVIDE**
   - Ferramenta de segmentos/secções + gerador de geologia.
   - S01–S04 em blockout (material de grelha e cores de risco), checkpoints em volume, grelha 5×4.
   - Medição de tempo por setor.
4. **M3 — IA**
   - Linhas por segmento, perfil de velocidade segura, grafo e decisões, ultrapassagem, recovery, perfis.
   - Simulação headless de 12–16 bots.
5. **M4 — Naves e equipamento**
   - ScriptableObjects, StatResolver, BuildValidator, ShipAssembler.
   - 5 chassis em placeholder modular, 28 definições, passivas.
6. **M5 — Loop de extração**
   - Dano, combustível, calor, energia, consumíveis, seguro, pool, distribuição, estados e ecrã de resultados.
7. **M6 — Economia**
   - LocalAuthority + ledger + idempotência, carteira, loja, caches, venda, contratos e proezas.
   - Save versionado e Hangar funcional (UI).
8. **M7 — Arte de ambiente seletiva**
   - Materiais de arenito estratificado/slickrock/areia, uma vista-herói, Red Wall, Wash e saída da Hollow.
   - Peças-herói no Blender. Naves finais (5 chassis + módulos).
9. **M8** VFX (poeira, velocidade, impacto, calor), áudio (acústica por espaço) e UI final.
10. **M9** Otimização: perfis PC/Android, LOD/HLOD, streaming, origem, térmica.
11. **M10** QA/balanceamento: telemetria, bots com builds extremas, análise de rotas e exploits.

Cada milestone termina com projeto a compilar, testes automáticos a passar, changelog curto e build Windows (+ APK a partir do M2).

---

## L. Testes de aceitação

| Milestone | Prova mensurável |
|---|---|
| M1 Física | A nave mantém altura ±0,3 m no plano a 65 m/s. Entra em bank 50° sem snap (variação de orientação ≤ 90°/s). Percorre 300 m de half-pipe a 3 alturas sem perder contacto. Wall ride de 65° durante ≥ 2 s acima da velocidade mínima e queda previsível abaixo dela. Zero tunneling a 1,3× a velocidade máxima em 1 000 passagens automáticas. |
| M1 Câmera | O horizonte nunca roda mais de 40% do roll da nave. Nenhum frame com a câmera dentro de geometria no percurso de teste (verificação automática por raycast). |
| M2 Blockout | A grelha 5×4 sai sem sobreposição. Larguras medidas por amostragem dentro dos targets (±15%). Tempo do slice entre 6 e 8 min com bot de referência. Todos os checkpoints atravessáveis em todas as linhas. Pelo menos 2 bifurcações completas com SAFE/RACING/SKILL. |
| M3 IA | 16 bots: ≥ 85% terminam sem intervenção. Ninguém fica preso mais de 10 s. Os bots usam ≥ 2 alturas no Red Wall e no Wash (histograma de u). Cada atalho é escolhido por 10–50% dos bots. A linha SKILL bem executada ganha 2–6 s (medido). |
| M4 Naves | O validator rejeita 100% dos casos ilegais do conjunto de testes. Nenhum chassis com mais de 55% de vitórias em 50 simulações com bots de skill igual. A troca de módulo muda a silhueta (teste de máscara). |
| M5 Extração | Testes unitários garantem que o pool só contém itens perdidos, que a peça segurada não entra, que nada é duplicado e que nada é inventado (simulação de 10 000 corridas). Resultados mostram perdas, seguro, loot e ✦ separados. |
| M6 Economia | Odds medidas em 100 000 caches dentro de ±0,5 pp. Garantias sempre cumpridas. 4% de Lendário por caixa e não por slot. Repetir a mesma idempotencyKey nunca cobra duas vezes. A simulação da curva de ✦ bate com o Doc 03 §12 (±15%). |
| M7–M8 Arte | A "regra do asfalto": nenhuma superfície de pista com material ou geometria artificial (revisão + verificação de materiais). Leitura a velocidade real: o próximo checkpoint/landmark é visível ≥ 3 s antes. |
| M9 Performance | PC: 60 fps (p95 ≤ 16,7 ms) no slice inteiro em qualidade média. Android A15: ≥ 30 fps p95 durante 10 min, sem throttling a baixar abaixo de 25 fps. Hitch de streaming ≤ 8 ms. |

---

## Decisões aprovadas (12/10/2026)

| # | Decisão |
|---|---|
| D1 | **Projeto Unity novo e separado:** `extract uststars/ExtractStardustRDD`, sem nenhuma referência ao projeto da ilha. A ilha fica intacta onde está. |
| D2 | **Física das naves 100% nova.** A gameplay antiga (aceleração automática, derrapagem com travão de mão, boost/nitro, dano/combustível/reparação, porquinho/seguro/resultados, sensação da câmera) é **reaproveitada como design** e reescrita/melhorada na arquitetura nova. |
| D3 | **Velocidade: 400–450 km/h de velocidade máxima sem boost** (BASTION ~400 → WRAITH ~450, conforme stat Speed e build). O boost ultrapassa brevemente. Fecha a decisão em aberto "velocidades máximas" do Doc 01 §28. |
| D4 | **A pista adapta-se à velocidade** (Doc 01 §16.3 e §19: fica fechada a proporção e a função, não os metros). Fatores iniciais ajustáveis: **larguras ×1,6** e **raios ×1,75**, medidos no laboratório de física (M1). Comprimentos saem de ritmo × velocidade: **vertical slice ≈ 38–40 km**, **expedição completa ≈ 100–110 km**. Floating origin obrigatório; rota enrolada dentro de ±16 km. |
| D5 | **Geologia modelada no Blender** com o máximo de realismo, num processo geológico (não blocos): (1) macro-relevo de planalto/mesas; (2) estratificação do arenito (camadas duras formam saliências, moles recuam); (3) fraturas verticais (jointing); (4) erosão hídrica/térmica; (5) canais de corrida esculpidos com as secções de design; (6) cavernas orgânicas; (7) formações-herói (arcos, fins, hoodoos, balanced rock); (8) talus/detritos; (9) LOD0–3. Exportação por **pipeline FBX validado** (teste automático de eixos e escala). Texturas PBR reais (CC0) no passe de arte. |
| D6 | **Ordem sem desperdício:** o laboratório de física (M1) e o blockout (M2) já usam as mesmas ferramentas de geologia do Blender. O passe de arte (M7) aprofunda o detalhe sobre a forma já validada; não se deita geometria fora. |
| D7 | Propostas C8–C15 adotadas por omissão: até 3 peças perdidas; 5 chassis disponíveis; sem postos de combustível; 3 slots de consumíveis; LocalAuthority na demo. |

### Larguras e raios escalados (iniciais, TARGET)

| Zona | Doc 01 | ×1,6 | | Curva | Doc 01 | ×1,75 |
|---|---|---|---|---|---|---|
| Bacia de largada | 30–38 m | **48–60 m** | | Mega arco | 500–1 200 m | **875–2 100 m** |
| Wash aberto | 24–35 m | **38–56 m** | | Rápida | 250–500 m | **440–875 m** |
| Percurso principal | 14–24 m | **22–38 m** | | Média | 120–250 m | **210–440 m** |
| Secção técnica | 10–16 m | **16–26 m** | | Fechada | 60–120 m | **105–210 m** |
| Gargalo | 7–12 m | **11–19 m** | | Extrema (atalho) | 35–60 m | **60–105 m** |
| Atalho skill | 5–9 m | **8–14 m** | | Red Wall | 700 → 180–250 m | **1 225 → 315–440 m** |
| Half-pipe (secção) | 40–90+ m | **64–145+ m** | | | | |

## Decisões que preciso que aprove antes de produzir

1. **Estrutura:** mesmo projeto Unity, com módulo `Assets/RedDust/` isolado e a ilha fora das builds (recomendado), **ou** projeto Unity separado?
2. **C6/C7, velocidade e comprimentos:** cruzeiro 55–65 m/s (200–235 km/h) + boost, com os comprimentos-assinatura mantidos e o total derivado da velocidade?
3. **C8, perdas:** até 3 componentes não segurados perdidos por destruição?
4. **C10/C11/C15:** os 5 chassis disponíveis na demo, sem postos de combustível e 3 slots de consumíveis?
5. **C9:** autoridade local (`LocalAuthority`) com interface de servidor para a demo?
