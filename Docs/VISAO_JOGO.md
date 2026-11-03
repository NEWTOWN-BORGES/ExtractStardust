# EXTRACT: STARDUST — o que o jogo é (2026-10-23)

Fonte: pedido do jogador neste dia + GDD Unity (`EXTRACT_STARDUST` docs 01 e 03).
Isto substitui a ideia de “corrida contra o cronómetro com kit médico”.
O código Unreal actual ainda é um protótipo de voo + ranking; **ainda não é este jogo**.

Tagline: **RACE. SURVIVE. EXTRACT.**

## Em uma frase

Corrida de extração A→B: 15 / 20 / 30 naves antigravidade numa pista perigosa (obstáculos, atalhos, perigos).
Quem morre a meio perde o loot que levava. Quem corta a meta extrai: o 1.º leva os melhores espólios,
o último sobrevivente ainda é recompensado por ter chegado vivo.

## Fantasia

Não é só ser o mais rápido. **Preparas-te no hangar** (nave, combustível, kits de reparação, o resto
da carga), arriscas essa build na pista, e tens de **chegar a B vivo** para ficar com o que levavas.
Os destruídos alimentam o **pool de espólios** (só itens realmente perdidos). Os que extraem recebem
esse pool automaticamente no fim, por ordem de chegada.

Referência de **sensação** (não de IP): corridas antigravidade tipo podrace — naves a deitar-se nas
curvas, câmara a seguir o bank, FOV, poeira, som, proximidade das paredes. A identidade é EXTRACT:
STARDUST (geologia, extração, risco), não cópia de naves/logos/cenários de Star Wars.

## Loop

Preparar → arriscar → correr → sobreviver → extrair → resultado → hangar.

Estados no fim: **EXTRACTED** (cruzou B vivo) / **DESTROYED** / **STRANDED** / **ABANDONED**.
Só EXTRACTED recebe o bónus de extração e o loot do pool. DESTROYED perde o equipamento não
segurado (vai para o pool). Stardust já na carteira **não** se perde.

Lobby-alvo: **16 agora** (grelha 3×6), depois **20**, depois **30** quando a pista e o netcode aguentarem.
O GDD da demo falava em até 20; o jogador quer 15/20/30.

## Pista

Expedição **Red Dust Divide**, A→B, ~10–12 min (GDD antigo falava 18–22 min nas expedições longas;
esta pista nova é o “chute” mais curto). Geologia = pista. Rotas **SAFE / RACING / SKILL**.
Obstáculos e perigos fazem parte do desenho. **Monstros / criaturas: mais tarde**, não agora.

## Antes da corrida (loadout) — não há pickups na pista

O jogador confirma: **não se apanham kits em velocidade**. Reparação, combustível e o resto
(Coolant, Stabilizer, Surge, etc.) **levam-se de casa**, escolhidos no hangar antes de A.

Na pista só **usas** o que trouxeste. Quem gasta tudo a meio fica sem margem. Quem cai perde
a carga não segurada. O loot de componentes só muda de dono **no extract**, pelo pool.

## Espólios na meta

- 1.º: prioridade nas raridades altas que existirem no pool
- seguintes: o que restar, por ordem
- último a extrair: ainda ganha (sobrevivência + Stardust de posição + bónus EXTRACTED)
- se o pool esgotar: os que extraíram sem item ainda levam prémio de corrida
- quem morre a meio: **não extrai**, perde o que levava (excepto o que estava segurado)

Moeda: **STARDUST**. O número do pool no HUD é valor estimado dos itens, não dinheiro criado.

## O que falta no Unreal (pedido 2026-10-23)

1. **Menu de jogo** — briefing SOLO / PELOTÃO 15 / HANGAR (loadout completo fica para depois).
2. **Som** — motores, vento, impacto, boost, audição de velocidade. Sem isto a corrida parece muda.
3. **Estilo de piloto** — no código: bank forte, câmara a deitar-se e a olhar o ápice, FOV/blur
   com a velocidade, poeira e risco junto às paredes. Falta validar em jogo (adrenalina a 400–550 km/h).
4. **Extraction loop** — hangar/loadout, pool na meta, combustível e reparação da carga, Stardust.
5. **Pelotão grande** — 20 e 30 corredores, quando a pista (56–64 m) e os bots aguentarem.
6. **Monstros** — depois do loop de extração e da sensação de corrida estarem jogáveis.

O ranking + vidas + kit médico de 3 usos (`Docs/MODOS_DE_JOGO.md`) é **rascunho de sobrevivência**,
não o produto. Manter o que servir (chegada a B, eliminação, bots) e substituir o resto por este doc.
