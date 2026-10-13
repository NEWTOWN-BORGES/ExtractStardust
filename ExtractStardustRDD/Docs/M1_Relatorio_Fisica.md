# M1 — Relatório de validação da física e da câmera

Gerado automaticamente em 2026-10-13 02:32 · passo fixo 1/90 s · 12 s de simulação real.
Percurso: laboratório (`Art/Courses/sandbox.json`), 26,12 km + 2 ramos (R1 Fenda (direita, mais funda) 1,70 km, R2 Bancada (esquerda, mais alta) 1,69 km). Nave: STRIX provisória (CraftTuning por omissão, 425 km/h).

**Resultado: 21/22 testes passam.**

| Teste | O que prova | Critério | Medido | Estado |
|---|---|---|---|---|
| T1 | Hover em leito plano à velocidade máxima | desvio de altura ≤ 0,30 m; contacto ≥ 99% | desvio máx. 0.08 m · contacto 100.0% · 427 km/h | ✅ PASSA |
| T2a | Bank 30° (entrada, curva, saída) | sem snap (Δcima médio 0,1 s ≤ 90°/s); contacto ≥ 99%; desvio lateral ≤ 5 m; 0 impactos | Δcima máx. 51°/s · contacto 100.0% · desvio 0.6 m · inclinação máx. 30° · impactos 0 | ✅ PASSA |
| T2b | Bank 50° (entrada, curva, saída) | sem snap (Δcima médio 0,1 s ≤ 90°/s); contacto ≥ 99%; desvio lateral ≤ 5 m; 0 impactos | Δcima máx. 33°/s · contacto 100.0% · desvio 0.3 m · inclinação máx. 65° · impactos 0 | ✅ PASSA |
| T3 u=0.00 | Half-pipe a fundo | contacto ≥ 98%; erro médio de linha ≤ 0,12; Δcima médio 0,1 s ≤ 120°/s | contacto 100.0% · erro de linha 0.000 · Δcima máx. 4°/s · superfície máx. 0° | ✅ PASSA |
| T3 u=0.45 | Half-pipe a meia parede | contacto ≥ 98%; erro médio de linha ≤ 0,12; Δcima médio 0,1 s ≤ 120°/s | contacto 100.0% · erro de linha 0.013 · Δcima máx. 56°/s · superfície máx. 28° | ✅ PASSA |
| T3 u=0.80 | Half-pipe a parede alta | contacto ≥ 98%; erro médio de linha ≤ 0,12; Δcima médio 0,1 s ≤ 120°/s | contacto 100.0% · erro de linha 0.012 · Δcima máx. 100°/s · superfície máx. 66° | ✅ PASSA |
| T4a | Wall ride natural a ~65° à velocidade máxima | ≥ 2 s seguidos em superfície ≥ 60° com contacto | 2.7 s seguidos · superfície máx. 64° · linha u=0.92 | ✅ PASSA |
| T4b | Parede abaixo da velocidade mínima (30 m/s, sem acelerar) | escorrega ≥ 3 m parede abaixo ou descola em ≤ 2 s | perdeu a linha após 1.02 s · escorregou 11.6 m em 2 s | ✅ PASSA |
| T4c | Parede a 216 km/h (acima da mínima) | segura ≥ 1,5 s em superfície ≥ 58° | 6.0 s | ✅ PASSA |
| T5a | Flow jump (borda natural de 7°) | salto visível: ≥ 1 m acima do hover ou voo ≥ 30 m | altura máx. +1.1 m sobre o hover · voo 0 m | ✅ PASSA |
| T5b | Canyon jump sobre a ravina | atravessa a ravina e aterra do outro lado | voo de 187 m, aterra 140 m depois da ravina | ✅ PASSA |
| T5c | Receção legível | flow jump ≤ 12 m/s; canyon jump ≤ 17 m/s; 0 impactos do casco | 9881 m: voo 187 m, 13.6 m/s · impactos 0 | ✅ PASSA |
| T6 | Caverna curva (teto irregular) | contacto ≥ 98%; folga ao teto ≥ 3 m; 0 impactos | contacto 100.0% · folga mín. 24.1 m · impactos 0 | ✅ PASSA |
| T7 | Sem tunneling a 1,3-1,5x a velocidade máxima | 0 atravessamentos (1000 paredes + 200 quedas no leito) | paredes 0/1000 · leito 0/200 | ✅ PASSA |
| T9 | Leito natural: três linhas viáveis (canal / bancadas) | todas terminam sem quedas nem impactos; diferença de tempo ≤ 12% | u=-0.55: 16.1 s, ar 0.0 s, aterragem máx. 0.0 m/s, Slickrock 78%, Sand 12%, Rock 10% · u=0.00: 16.9 s, ar 0.0 s, aterragem máx. 0.0 m/s, Sand 90%, DeepSand 8%, Slickrock 2% · u=0.55: 16.6 s, ar 0.0 s, aterragem máx. 0.0 m/s, Slickrock 72%, Sand 16%, Rock 12% · diferença 5.2% | ✅ PASSA |
| G2 | Junções e ramos: superfície contínua | 0 buracos; 0 rocha a menos de 6 m por cima da linha de corrida; degrau entre amostras (3 m) ≤ 3 m | 24466 raios · buracos 0 · rocha por cima 0 · maior degrau 1.72 m (R2 Bancada (esquerda, mais alta) 14751 m u=0.60) | ✅ PASSA |
| A1 | Arcos e destroços por cima da pista | arcos/destroços/pedras ≥ 6 m e paredes ≥ 2,5 m acima das linhas de corrida (fora das cavernas) | 33565 pontos · 315 sob arcos/destroços · folga mín. 1.1 m (R2 Bancada (esquerda, mais alta) 15351 m u=-0.9 (GEO_Rocks_R1_001)) · obstruídos 5 | ❌ FALHA |
| G1 R1 | Ramo R1 Fenda (direita, mais funda) | sai, percorre e volta ao principal; 0 quedas; 0 impactos; contacto ≥ 97%; Δcima ≤ 120°/s; reconhecido pelo grafo ≥ 80% | 21.9 s · contacto 100.0% · Δcima máx. 55°/s · impactos 0 · quedas 0 · no ramo 86% do tempo (pelo grafo) · 21.9 s vs 21.7 s no principal | ✅ PASSA |
| G1 R2 | Ramo R2 Bancada (esquerda, mais alta) | sai, percorre e volta ao principal; 0 quedas; 0 impactos; contacto ≥ 97%; Δcima ≤ 120°/s; reconhecido pelo grafo ≥ 80% | 22.4 s · contacto 100.0% · Δcima máx. 58°/s · impactos 0 · quedas 0 · no ramo 86% do tempo (pelo grafo) · 22.4 s vs 21.7 s no principal | ✅ PASSA |
| T8 | Volta completa automática ao laboratório | termina; 0 quedas; sem ficar preso (v > 20 m/s após 20 s) | terminou em 233.1 s · média 403 km/h · v mín. 339 km/h · solo 98.7% · quedas 0 · impactos 0 | ✅ PASSA |
| C1 | Câmera: horizonte | roll da câmera ≤ 40% do roll da nave (+3° de tremor) | excesso máx. 0,0° | ✅ PASSA |
| C2 | Câmera: nunca dentro da geometria | 0 frames | 0 de 44146 frames | ✅ PASSA |
