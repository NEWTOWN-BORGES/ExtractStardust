# M1 — Relatório de validação da física e da câmera

Gerado automaticamente em 2026-10-12 22:33 · passo fixo 1/90 s · 9 s de simulação real.
Percurso: laboratório (`Art/Courses/sandbox.json`), 14,02 km. Nave: STRIX provisória (CraftTuning por omissão, 425 km/h).

**Resultado: 18/18 testes passam.**

| Teste | O que prova | Critério | Medido | Estado |
|---|---|---|---|---|
| T1 | Hover em leito plano à velocidade máxima | desvio de altura ≤ 0,30 m; contacto ≥ 99% | desvio máx. 0.08 m · contacto 100.0% · 427 km/h | ✅ PASSA |
| T2a | Bank 30° (entrada, curva, saída) | sem snap (Δcima médio 0,1 s ≤ 90°/s); contacto ≥ 99%; desvio lateral ≤ 5 m; 0 impactos | Δcima máx. 54°/s · contacto 100.0% · desvio 0.6 m · inclinação máx. 30° · impactos 0 | ✅ PASSA |
| T2b | Bank 50° (entrada, curva, saída) | sem snap (Δcima médio 0,1 s ≤ 90°/s); contacto ≥ 99%; desvio lateral ≤ 5 m; 0 impactos | Δcima máx. 34°/s · contacto 100.0% · desvio 0.3 m · inclinação máx. 66° · impactos 0 | ✅ PASSA |
| T3 u=0.00 | Half-pipe a fundo | contacto ≥ 98%; erro médio de linha ≤ 0,12; Δcima médio 0,1 s ≤ 120°/s | contacto 100.0% · erro de linha 0.000 · Δcima máx. 4°/s · superfície máx. 0° | ✅ PASSA |
| T3 u=0.45 | Half-pipe a meia parede | contacto ≥ 98%; erro médio de linha ≤ 0,12; Δcima médio 0,1 s ≤ 120°/s | contacto 100.0% · erro de linha 0.013 · Δcima máx. 56°/s · superfície máx. 28° | ✅ PASSA |
| T3 u=0.80 | Half-pipe a parede alta | contacto ≥ 98%; erro médio de linha ≤ 0,12; Δcima médio 0,1 s ≤ 120°/s | contacto 100.0% · erro de linha 0.012 · Δcima máx. 101°/s · superfície máx. 66° | ✅ PASSA |
| T4a | Wall ride natural a ~65° à velocidade máxima | ≥ 2 s seguidos em superfície ≥ 60° com contacto | 2.6 s seguidos · superfície máx. 64° · linha u=0.92 | ✅ PASSA |
| T4b | Parede abaixo da velocidade mínima (30 m/s, sem acelerar) | escorrega ≥ 3 m parede abaixo ou descola em ≤ 2 s | perdeu a linha após 1.10 s · escorregou 8.9 m em 2 s | ✅ PASSA |
| T4c | Parede a 216 km/h (acima da mínima) | segura ≥ 1,5 s em superfície ≥ 58° | 6.0 s | ✅ PASSA |
| T5a | Flow jump (borda natural de 7°) | salto visível: ≥ 1 m acima do hover ou voo ≥ 30 m | altura máx. +1.1 m sobre o hover · voo 0 m | ✅ PASSA |
| T5b | Canyon jump sobre a ravina | atravessa a ravina e aterra do outro lado | voo de 187 m, aterra 140 m depois da ravina | ✅ PASSA |
| T5c | Receção legível | flow jump ≤ 12 m/s; canyon jump ≤ 17 m/s; 0 impactos do casco | 9881 m: voo 187 m, 13.6 m/s · impactos 0 | ✅ PASSA |
| T6 | Caverna curva (teto irregular) | contacto ≥ 98%; folga ao teto ≥ 3 m; 0 impactos | contacto 100.0% · folga mín. 24.1 m · impactos 0 | ✅ PASSA |
| T7 | Sem tunneling a 1,3-1,5x a velocidade máxima | 0 atravessamentos (1000 paredes + 200 quedas no leito) | paredes 0/1000 · leito 0/200 | ✅ PASSA |
| T9 | Leito natural: três linhas viáveis (canal / bancadas) | todas terminam sem quedas nem impactos; diferença de tempo ≤ 12% | u=-0.55: 16.1 s, ar 0.0 s, aterragem máx. 0.0 m/s, Slickrock 78%, Sand 12%, Rock 11% · u=0.00: 16.9 s, ar 0.0 s, aterragem máx. 0.0 m/s, Sand 90%, DeepSand 9%, Slickrock 2% · u=0.55: 16.6 s, ar 0.0 s, aterragem máx. 0.0 m/s, Slickrock 71%, Sand 16%, Rock 12% · diferença 5.2% | ✅ PASSA |
| T8 | Volta completa automática ao laboratório | termina; 0 quedas; sem ficar preso (v > 20 m/s após 20 s) | terminou em 124.5 s · média 404 km/h · v mín. 351 km/h · solo 97.6% · quedas 0 · impactos 0 | ✅ PASSA |
| C1 | Câmera: horizonte | roll da câmera ≤ 40% do roll da nave (+3° de tremor) | excesso máx. 0,0° | ✅ PASSA |
| C2 | Câmera: nunca dentro da geometria | 0 frames | 0 de 28428 frames | ✅ PASSA |
