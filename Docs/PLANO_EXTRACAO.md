# Plano: a extração em corrida como carro-chefe, e progressão para os jogadores voltarem (2026-10-27)

Pedido do jogador: "quem joga hoje não percebe essa mecânica e passa despercebida; vamos precisar de mais itens,
módulos e consumíveis para dar sensação de progressão e fazer as pessoas voltar".

Base: `Docs/VISAO_JOGO.md` (RACE. SURVIVE. EXTRACT.), `Docs/MODULOS.md` (módulos, caixas, consumíveis, estrelas) e
o código atual (`EXMeta`, `EXProfile`, `EXRaceDirector`, `EXHangarModel`, HUD em UMG).
**As decisões marcadas com ❓ são do jogador.** O resto é proposta, e os números são para afinar a jogar.

## 1. O problema: porque é que a extração passa despercebida

Hoje a extração existe nas regras, mas o jogador não a vê nem a decide:
- **Não se vê o que se arrisca.** O valor em risco só aparece no hangar e no fim da corrida. Na pista não há nada que
  lembre "tens 4 800 ✦ a bordo".
- **Não se vê o espólio a crescer.** As naves destruídas alimentam o pool em silêncio, e só se sabe disso no quadro final.
- **Não há escolha.** A meta é só uma linha de chegada. Não há o momento "saio agora com o que tenho ou arrisco mais"
  que define os jogos de extração (Tarkov, Hunt, Arc Raiders).
- **A perda não dói nem ensina.** Quem é destruído vê uma tabela. Não vê o que perdeu nem quem ficou com as peças.

Na prática, é uma corrida com uma tabela de prémios no fim. Para a extração ser o carro-chefe, tem de ser
**visível, decidida e sentida**.

## 2. Os três pilares

1. **VER:** o que levo, quanto vale e quanto há no pool, sempre no ecrã e na própria nave.
2. **DECIDIR:** pontos de extração ao longo da pista e uma janela que fecha em B. Sair cedo é seguro; ir até ao fim
   vale mais.
3. **SENTIR:** o momento da extração e o momento da perda têm de ser os mais fortes do jogo, com som, câmara e ecrã
   próprios.

## 3. A corrida com extração (proposta)

### 3.1 Carga a bordo, visível

- **HUD: "A BORDO".** Junto às vidas fica o valor total que se arrisca (módulos não segurados, consumíveis levados e
  STARDUST recolhido na corrida), a dourado e a pulsar quando a nave leva dano.
- **Na nave:** contentores de carga com o brilho da raridade mais alta a bordo. Os rivais carregados veem-se de longe.
- **Multiplicador por setor:** a carga de corrida (o STARDUST ganho na expedição) cresce a cada setor vencido
  (×1,0 em S1 até ×2,5 em S10). Ir mais longe vale mais.

### 3.2 Pool visível e feed de destruições

- **HUD: "POOL".** Mostra o valor dos itens perdidos pelas naves destruídas e sobe em tempo real.
- **Feed:** "WRAITH-07 destruída: +2 340 ✦ no pool · ÉPICO". O jogador percebe que cada destruição é espólio para quem
  chegar ao fim.
- Os contentores da nave destruída ficam a arder na pista uns segundos: é um marco visual, não um pickup.

### 3.3 Pontos de extração ao longo da pista ❓

- **2 portões de extração antecipada** (por exemplo depois de S4 e de S7), fora da linha ideal, a obrigar a um desvio.
- Quem extrai num deles **fica com o que leva** (carga, módulos, consumíveis) e com o multiplicador desse setor.
  Fica sem o prémio de posição e sem parte do pool.
- É a escolha clássica dos jogos de extração: "saio já em segurança, ou arrisco tudo por mais?".
- Cada portão abre por pouco tempo e só para um número limitado de naves (por exemplo as 4 primeiras a chegar). Isso
  cria duelos para lá entrar.

### 3.4 Janela de extração em B ❓

- Quando a primeira nave chega a B, **a extração fica aberta 60–90 s** (contagem enorme no HUD, sirene e o feixe de
  B visível de toda a pista).
- Quem não passar a tempo fica **STRANDED**: perde a carga de corrida, guarda os módulos e não recebe pool.
- Isto dá urgência aos que vêm atrás e torna a vitória do 1.º uma ameaça para todos.

### 3.5 O momento da extração e o momento da perda

- **Extração:** câmara lenta de 1 s ao cruzar o feixe, um som próprio e "EXTRAÍDO" em grande. Depois aparecem as
  peças ganhas no pool, uma a uma, como as cartas do COFRE.
- **Perda:** "DESTRUÍDA", seguido do que se perdeu (cartas a ficar cinzentas) e de quem ficou com cada peça no fim.
  É a perda que ensina a segurar módulos e a sair cedo.

### 3.6 Ensinar no primeiro minuto

- **Primeira expedição guiada:** 3 regras no briefing ("o que levas pode perder-se", "o pool é dos que extraem",
  "extrai vivo"), com setas no HUD na primeira vez que cada coisa acontece.
- **Briefing antes de cada corrida:** valor a bordo, módulo segurado, portões de extração no mapa e tamanho do pelotão.

## 4. Progressão: razões para voltar

### 4.1 Nível de piloto (conta)
- XP por setor vencido, destruições evitadas e extração (×2 se extrair).
- Os níveis desbloqueiam slots de consumível (4 → 5 → 6), capacidade do cofre, ligas de bots e cosméticos (capacetes,
  fatos e pinturas: já há um piloto próprio por nave).

### 4.2 Maestria por nave (além das estrelas)
- Cada nave tem níveis próprios (por km feitos e extrações com ela).
- Os níveis dão pinturas, um 2.º módulo segurado com essa nave e uma variante da passiva (por exemplo OVERDRIVE
  RECOVERY II).

### 4.3 Módulos: profundidade em vez de só raridade
- **Melhoria +1 a +5:** desmontar módulos dá materiais (fragmentos de Stardust, liga e núcleos). Os materiais sobem
  um módulo de nível, com um pequeno custo de massa ou calor.
- **Conjuntos de fabricante:** 2 ou 4 peças do mesmo fabricante (APEX, Meridian, Frontier, Vanta…) dão um bónus de
  conjunto (por exemplo, APEX 4 peças: +8 % de mini-turbo).
- **Famílias novas** (encaixam nos slots existentes ou num slot novo de CARGA):
  - **Porão de carga** (slot novo): mais capacidade e multiplicador de carga, à custa de massa.
  - **Âncora de seguro:** segura 1 módulo extra se a nave cair, e ocupa a utilidade.
  - **Baliza de extração:** permite extrair num portão fechado, uma vez por corrida.
- **Exóticos** (acima de lendário, 0,5 % na ELITE): um efeito único cada um. Exemplos: rasto de plasma que aquece quem
  vem atrás; casco que devolve 1 vida depois de 3 setores sem dano.

### 4.4 Consumíveis novos (os 6 atuais ficam)

| Consumível | Efeito | Escolha que cria |
| --- | --- | --- |
| Shield Pulse | absorve o próximo embate (6 s) | defesa antes de um troço difícil |
| Jump Jet | salto 2× mais alto (para as rotas altas) | atalho arriscado |
| Drag Chute | travagem forte sem perder a linha | curvas apertadas a 200 km/h |
| Ghost Field | 3 s sem colisão com rivais | passar no meio do pelotão |
| Cargo Lock | 1 contentor fica seguro se a nave cair | proteger a carga grande |
| Flare | mostra os perigos dos próximos 2 km | rotas desconhecidas |
| Emergency Extract | extrai já com 50 % da carga e acaba a corrida | saída de emergência |

Sem pickups na pista, como o jogador decidiu: tudo isto leva-se do hangar.

### 4.5 Ritmo de recompensas (o que traz as pessoas de volta)
- **Contratos diários (3) e semanais (5):** por exemplo "extrai 3 vezes com mais de 5 000 ✦ a bordo" ou "chega a B
  com a BASTION sem reparar". Pagam STARDUST, materiais e caixas.
- **Sequência de extrações:** cada extração seguida soma +10 % aos prémios, até +50 %. Uma destruição quebra a
  sequência, o que dá tensão a cada corrida.
- **Primeira vitória do dia:** caixa ADVANCED.
- **Ligas de pelotão** (Bronze → Prata → Ouro → Diamante): bots melhores, pool maior e caixas melhores no fim.
- **Temporadas de 6–8 semanas:** passe de expedição (cosméticos e materiais), pista ou variante nova, exóticos novos.
- **Coleção:** um códex de módulos, pinturas e estrelas, com prémios por completar famílias.

## 5. Fases de implementação

| Fase | O quê | Onde, no código |
| --- | --- | --- |
| **A. Ver** | HUD "A BORDO" e "POOL", feed de destruições, contentores visíveis na nave, briefing com valor e portões | `EXRaceHudWidget`, `EXRaceDirector` (eventos de destruição e valor do pool), `EXHoverCraft` (contentores) |
| **B. Decidir** | janela de extração em B (STRANDED), 2 portões de extração antecipada, multiplicador por setor | `EXRaceDirector`, a rota (`ab_route.json`: setores e portões), `EXMeta` (prémios) |
| **C. Sentir** | ecrãs de EXTRAÍDO e DESTRUÍDA com cartas, câmara lenta, som próprio | widget novo de resultados, `EXSoundSynth` |
| **D. Ensinar** | primeira expedição guiada, setas de ajuda | `EXProfile` (marca de tutorial), HUD |
| **E. Progressão 1** | nível de piloto, contratos diários e semanais, sequência de extrações | `EXProfile` (versão 3), `EXMeta`, hangar (separador CONTRATOS) |
| **F. Itens 1** | 7 consumíveis novos, porão de carga, âncora de seguro, baliza de extração | `EXMeta` (catálogo), `EXHoverCraft` (efeitos), ícones (`make_ui_icons.py`) |
| **G. Itens 2** | melhoria +1…+5 com materiais, conjuntos de fabricante, exóticos | `EXMeta`, hangar (EQUIPAR e COFRE) |
| **H. Longo prazo** | maestria por nave, ligas, temporadas e passe, códex | perfil, menu, backend quando houver multijogador |

Recomendo começar pela ordem **A → B → C**. Sem ver, decidir e sentir a extração, mais itens não resolvem o problema.
Os itens (F, G) dão profundidade depois de a extração ser clara.

## 6. Decisões do jogador ❓

1. **Portões de extração antecipada** (3.3): ✅ o jogador quer, melhorados (2026-10-27: "já temos, mas vamos
   melhorar"). No código atual só se extrai em B: os portões são a construir (`EXRaceDirector` e a rota).
2. **Janela em B** (3.4): ❌ não é precisa (2026-10-27). Quem chega a B vivo extrai, como agora.
3. **Carga de corrida a crescer por setor** (3.1): sim? Com que multiplicador máximo?
4. **Combate entre naves:** continua sem armas (só empurrões e paredes)? Os consumíveis de 4.4 são todos defensivos ou
   de mobilidade.
5. **Ordem das fases:** A → B → C primeiro, ou há algum sistema de progressão que queiras logo?
