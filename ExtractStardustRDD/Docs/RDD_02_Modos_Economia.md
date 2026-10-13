# EXTRACT: STARDUST — Modos de jogo, naves modulares e economia (demo)

Implementado segundo o Doc 02 (naves e equipamento) e o Doc 03 (itens, consumíveis e economia), mais as decisões D1–D7 do plano (`RDD_00`).

## Modos

| Modo | Pilotos | Risco | Prémios |
|---|---|---|---|
| **Exploração** | sozinho | nenhum (sem dano, combustível ou perdas) | só o tempo |
| **Extração vs bots** | jogador + 1–19 bots | dano, combustível, calor; até 3 peças não seguradas perdidas para o Pool | ✦ por posição × duração, EXTRACTED +250, proezas, contratos, peças do Pool |
| **PvP local + bots** | 2 jogadores (ecrã dividido) + bots | igual à Extração, cada jogador com o seu perfil | igual; o Pool pode passar peças de um jogador para o outro |

**Comandos no PvP:**
- 2 comandos: um para cada jogador.
- 1 comando: o J1 usa o teclado e o J2 usa o comando.
- Sem comandos: teclado dividido (WASD / setas).

## Controlos na corrida

| Ação | PS4/PS5 | Teclado |
|---|---|---|
| Acelerar / travar | R2 / L2 | W / S |
| Derrapagem | Quadrado | Espaço |
| Nitro | X ou R1 | Shift |
| Usar consumível | L1 (o selecionado) | 1 / 2 / 3 |
| Escolher consumível | D-pad ↑/↓ | — |
| Reposicionar (penaliza) | Triângulo | R |
| Pausa | OPTIONS | Esc |

## Naves e módulos (Doc 02)

**Chassis:** os 5 do Doc 02, com os stats e passivas do documento:

| Chassis | Passiva |
|---|---|
| STRIX | Adaptive Trim |
| WRAITH | Razor Line |
| NOMAD | Long Haul |
| BASTION | Inertial Anchor |
| VORTEX | Overdrive Recovery |

**Sockets por chassis (não é uma lista fixa):**
- VORTEX tem propulsão central.
- BASTION tem blindagem secundária.
- NOMAD tem um slot auxiliar.
- Compatibilidade S/M/L validada pelo `BuildValidator`.

**Catálogo:**
- 31 componentes: os 28 do Doc 02 (6 motores, 5 asas, 4 blindagens, 4 reatores, 3 refrigerações, 3 caudas, 3 utilidades) mais 3 kits de propulsão. A propulsão tem slot no documento mas não tinha contagem.
- 3 lendários: HELIOS V-9, REDLINE-X e AEGIS FRAME. Têm serial persistente, perk e drawback.

**Raridade:**
- Stat budget de 10/13/16/20/23, com caps por família.
- Os drawbacks devolvem budget.

**Física:**
- Os stats viram física no `ShipBuilder.Tuning`; a referência é a STRIX stock. Exemplo: velocidade 61 → ~398 km/h e 82 → ~449 km/h (D3).
- O visual nunca mexe no collider nem no centro de massa.

**Visual:**
- Cada módulo montado muda a nave: motor, propulsores, asas, cauda, placas de blindagem, reator com cor própria, radiadores e mastro/cúpula/drone.
- É provisório, gerado por código e montado por sockets.

## Economia (Doc 03), autoridade local "DEMO LOCAL" (decisão C9)

**Carteira e kit inicial:**
- Perfil novo: ✦1 000 e 4 peças comuns montadas na STRIX (uma delas segurada).
- 2 Repair Foam, 1 Fuel Cell e 1 Coolant Cell.
- Primeira extração: +✦500, uma única vez.

**Prémios:**
- Posição: tabela de 20 lugares (✦1 600 … ✦225).
- EXTRACTED: +250.
- Proezas com teto de ✦500; a Vitória Imaculada substitui as proezas que se sobrepõem.
- 8 contratos.
- Multiplicador de duração calculado pela duração de referência da pista, não pela do jogador:
  - laboratório (~4 min): ×0,35;
  - expedição (~18 min): ×1,0.
- Destruído ou encalhado: 25% do prémio de posição. Abandonado: nada.

**Consumíveis:**
- Os 6 do Doc 03, com ícone, preço e efeito.
- 3 slots com até 2 unidades cada.
- Reparar abranda a nave (custa tempo).

**Loja:**
- 3 comuns, 2 incomuns e 1 raro, dentro das faixas de preço.
- A rotação muda depois de cada corrida. Epic e Legendary nunca estão à venda.

**Supply Caches (Mercado):** exatamente 10 itens, 4–6 componentes de famílias diferentes mais consumíveis, nunca chassis.

| Caixa | Preço | Probabilidades |
|---|---|---|
| Standard | ✦2 500 | 70 / 27 / 3 |
| Advanced | ✦6 000 | 20 / 50 / 27 / 3, mínimo 1 Rare |
| Elite | ✦13 500 | 25 / 55 / 20, 1 Epic e 4+ Rare garantidos, **um** roll de 4% de Lendário por caixa |

**Venda:** 25% da avaliação. Não há conversão de raridades.

**Idempotência:**
- Caixas, compras e resultados têm id de transação; repetir não paga nem cobra duas vezes.
- O ledger regista as entradas e saídas.

## Expedition Pool e seguro

**O que entra no Pool:**
- Antes da expedição escolhe-se 1 peça segurada (Hangar).
- Destruído, encalhado ou abandonado: até 3 peças montadas e não seguradas, sorteadas com peso pelo valor, vão para o Pool (D7). Os consumíveis levados também se perdem.
- O Pool só recebe instâncias reais. Os bots levam peças reais geradas para o lobby offline; nada é inventado para encher recompensas.

**Distribuição no fim:**
- Em serpentina por valor, entre os EXTRACTED: o 1.º recebe a peça mais valiosa.
- A peça muda de dono sem mudar de id, serial nem rolls.

**HUD e resultados:**
- O HUD mostra a avaliação "EXPEDITION POOL ✦…" e as notificações (RACER DESTROYED, POOL +✦, LEGENDARY ITEM ADDED).
- O relatório mostra **LEVEI / PERDI / GANHEI**, o Stardust ganho e a peça segurada SALVA.

**Conflito resolvido:** o pedido "ganhar loot durante a corrida" vs o Doc 01 §9.2 ("nada de loot manual em pista").
- Não há caixas na pista.
- O loot que se "ganha" durante a corrida é o Pool a crescer à medida que rivais são destruídos; recebe-se ao extrair.

## Bots (Doc 01 §12.2)

**Personalidades:** Agressivo, Sobrevivente, Técnico, Velocista e Novato.

**O que muda entre elas e a dificuldade:**
- a margem nas curvas;
- o uso de boost e o limite de calor;
- as escolhas SAFE/SKILL nas bifurcações (mais SAFE quando danificados);
- o momento em que reparam;
- os erros controlados (Novato).

**Linhas:** cada bot tem a sua altura de linha (fundo, meio ou alto das paredes) e ultrapassa mudando de linha.

**Sem batota:** os bots usam a mesma física, o mesmo dano e o mesmo combustível do jogador.

## Testes

| Comando | O que prova |
|---|---|
| `powershell -File Tools/test_meta.ps1` | 45 691 verificações sem Unity: catálogo, budgets/caps, probabilidades das caixas (Standard 70,7/26,5/2,8; Elite com Lendário em 3,9% das caixas), Pool sem duplicar nem inventar, seguro, prémios, idempotência |
| `powershell -File Tools/check_compile.ps1` | compila todas as assemblies com o Roslyn do Unity, sem licença |
| `Tools/m1_pipeline.ps1 ... -Build -Test` | extração automática no exe (`-rddextract`) com 7 bots: verifica o Pool e grava o relatório |

## Por validar no Unity (licença)

- Jogar os 3 modos e afinar:
  - o dano por impacto;
  - o consumo de combustível;
  - o calor;
  - a agressividade dos bots.
- Desempenho com 12–20 naves (PC) e 8 (Android).
- Expedição no Android: precisa de uma versão móvel da geologia. Por agora o APK leva o laboratório.
