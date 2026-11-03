# Física de voo e choques (2026-11-01)

Pedido do jogador:
- "A física não está muito boa nem real. Queria mais realista a subir, descer, quedas, movimento de câmara."
- "As naves, ao baterem uma na outra, é estranho. Queria algo como o Burnout: a alta velocidade chocam, raspam uma na
  outra, empurram, tiram vida e prejudicam a condução, tipo NFS."
- "Aconselho estudar numa sandbox com saltos, rampas, etc."

Ficou assim:
- **Estudado aqui** numa sandbox numérica (`Scripts/physics_sandbox/`, gráficos `FISICA_VERTICAL.png` e
  `FISICA_CHOQUES.png`).
- **No jogo**, em `AEXHoverCraft` (`StepFlight`, `CrashWith`, `TakeCrash`, `UpdateCamera`).
- **Para testar em casa**, a sandbox do jogo (`Scripts\jogar.ps1 -Modo Sandbox`).

A condução em plano não mudou: viragem, aderência, drift e velocidades são as de 2026-10-20, que o jogador aprovou. A
câmara continua a de 2026-10-20 (sem câmara de ápice nem inclinação funda). Só ganhou o atraso vertical e o empurrão
dos choques.

## 1. Subir, descer, quedas (o modelo vertical)

| | Antes | Agora |
|---|---|---|
| Suspensão | Uma mola só, que podia **puxar** a nave para o chão até 1,3 g. Por isso colava-se às lombas. | **Quatro almofadas** (nariz, cauda, lados) que só **empurram**. A ~2 m do chão já não empurram nada, e a nave voa sozinha numa lomba ou à saída de uma rampa. |
| Gravidade | No chão só contava 60 % da inclinação. | **Inteira, sempre.** Subir abranda, descer acelera e cair é cair. |
| Inclinação da nave | Virava para o chão a 160°/s e no ar endireitava para a horizontal a 45°/s, o que não é real. | Tem **inércia**: as almofadas rodam-na no chão. No ar o **nariz segue a trajetória** devagar, sobe na rampa e desce na queda. |
| Costelas e solavancos | O nariz tremia ±5°. | A saia faz a média do chão (0,06 s) e a nave passa lisa. |
| Aterragem | Só abanava a câmara. | As almofadas **comprimem**. Uma aterragem dura **perde velocidade** (1,2 % por m/s acima de 6, até 25 %), abana a câmara e levanta areia. Acima de 20 m/s tira casco, como antes. |
| Velocidade | | Um pouco de **efeito de solo** a alta velocidade (10 m/s² à velocidade máxima, que desaparece quando a nave sobe): mais assente, mas ainda leve numa lomba aguda. |

O que a sandbox numérica mostra (`FISICA_VERTICAL.png`, mesmos números e passos de 1/60 s do C++):
- **Rampa de 14° a 324 km/h:** a mesma altura (26 m) e a mesma distância de antes. **Os saltos da pista continuam a
  dar.** Muda só a nave: o nariz sobe com a rampa e depois desce com a trajetória (antes saltava para a horizontal).
- **Lomba suave (8 m em 160 m) a 396 km/h:** antes colava-se. Agora descola (1,25 s no ar), como um carro de rali.
- **Queda de 12 m:** antes caía direita como uma tábua. Agora o nariz inclina-se com a queda.
- **Costelas de 0,4 m:** antes tremia. Agora passa lisa.

## 2. Câmara nos saltos e quedas

- **Altura:** a câmara segue a altura da nave com um pequeno atraso. Segue também a velocidade vertical, por isso numa
  subida constante não fica para trás. Só aparece quando a velocidade vertical muda:
  - no salto, a nave sobe no ecrã;
  - na queda, a câmara fica um pouco acima;
  - na aterragem, a vista afunda um instante e volta.
  - O atraso vai até 2,5 m (`CamVerticalLag`, `CamVerticalLagMaxM`).
- **Choques:** um choque empurra a vista na direção da pancada e ela volta numa mola rápida (`CamCrashKick`), com o
  abanão.

## 3. Choques entre naves (tipo Burnout)

| | Antes | Agora |
|---|---|---|
| Quem reage | Só a nave que se mexia. A outra era tratada como uma **parede** e nem sentia. Era isso o "estranho". | **As duas**, pela quantidade de movimento repartida pelas massas, com um ressalto pequeno (0,3). Uma BASTION (1950 kg) empurra uma WRAITH (1180 kg). |
| Raspar | Nada. | **Atrito** ao longo do contacto (0,35): trava a mais rápida e puxa a mais lenta, com faíscas e algum casco por segundo (6/s a 20 m/s de diferença). |
| Rodar | Nada. | Uma pancada fora do centro **faz rodar**: na esquina de trás faz a nave dar a volta (PIT), no nariz empurra-a de lado. Até 2,6 rad/s, a passar em ~0,5 s. |
| Condução | Igual. | Uma pancada grande **tira aderência** (desliza), **amortece a direção** (−60 %) e **abana o nariz** durante até 1,1 s. |
| Casco | Impacto acima de 16 m/s × 0,85, metade contra naves. | O que a pancada **muda à velocidade** de cada nave, acima de 4 m/s, × 1,8. A nave leve muda mais e perde mais. Quem bate **com o nariz** perde só 60 %. Continua o máximo de 40 % por pancada e os 10 s sem dano no início. |
| Takedown | | Se a outra nave rebenta com a pancada, o log escreve `EXRACE TAKEDOWN`. |

- **BASTION:** a passiva INERTIAL ANCHOR passa a ser real. Os choques mexem-lhe 25 % menos.
- **Massa de cada nave:** a da nave mais os módulos (`GetCrashMassKg`). Os módulos pesados pesam no choque.

O que a sandbox numérica mostra (`FISICA_CHOQUES.png`):
- **Raspão a 400 km/h:** a BASTION encosta-se e afasta a WRAITH. A WRAITH perde 8 % e a BASTION nada; os dois pilotos
  corrigem.
- **Empurrão na esquina de trás (+50 km/h):** as duas perdem 4 % e a da frente roda.
- **Pancada em T a 300 km/h:** brutal. Chegam ao teto de 40 % (a VORTEX, mais leve, muda 87 m/s), voltam a bater
  e rodam muito.

## 4. A sandbox do jogo (para afinar em casa)

`powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1 -Modo Sandbox` (`-EXSandbox`).
- **O sítio:** uma volta de ~7 km construída em código a 2 km de altura, longe do mapa (`AEXPhysicsSandbox`).
- **Na primeira reta, para fora:**
  - rampa pequena de 10°;
  - mesa (rampa de 12°, 60 m de topo, descida);
  - rampa grande de 18° (18,5 m);
  - três lombas suaves de 3, 6 e 10 m;
  - subida de 8° para um planalto que acaba numa **queda de 14 m**;
  - costelas de 0,5 m a cada 8 m.
- **Na segunda reta, para trás,** larga e plana: **7 bots** em pelotão (88 a 95 % do ritmo), para raspar, empurrar e
  fazer rodar.
- **Regras:** dano ligado, combustível sempre cheio. Uma nave que rebenta volta em 3 s, e uma que cai da borda volta à
  volta.
- **No ecrã:** casco, velocidade, altura, chão ou ar, tempo no ar, abanão e rotação.
- **No log, cada salto e cada choque:**
  - `EXPHYS jump ... air= peak= takeoff= land= pitch=`
  - `EXPHYS crash A x B closing= slip= dv=`
  - `-EXPhysLog` escreve estas linhas também numa corrida normal.

**A ver em casa:**
1. As rampas e a mesa: o salto parece real (o nariz sobe e desce com a trajetória) e aterra sem bater de nariz.
2. As lombas: a 400 km/h a nave fica leve e descola um pouco; a 250 km/h não.
3. A queda de 14 m: aterra, abanão, perde um pouco de velocidade, sem rebentar (cai a ~23 m/s).
4. As costelas: a nave passa lisa.
5. O pelotão:
   - raspar de lado dá faíscas e tira pouco;
   - empurrar por trás na esquina faz o bot rodar;
   - uma pancada forte tira aderência e direção por um momento;
   - a BASTION empurra os outros e quase não se mexe.
6. A pista Red Dust Divide: os 19 saltos ainda aterram bem (a distância é a de antes).

## 5. Afinar (todos editáveis no Unreal, categorias Flight|Hover, Flight|Crash, Flight|Camera)

| Se... | Mexer em |
|---|---|
| Descola demais nas lombas | `DownforceMps2` ↑ (10 → 14) |
| Cola demais | `DownforceMps2` ↓ |
| Salta e quica ao aterrar | `PadDamping` ↑ (0,75 → 0,9) |
| Aterragem seca e dura | `PadStiffness` ↓ (45 → 38) |
| Nariz demasiado preguiçoso no ar | `AirAlign` ↑ (5 → 7) |
| Nariz baloiça no ar | `AirAlignDamping` ↑ |
| A nave abana na reta | `AttitudeDamping` ↑ (3 → 4,5) |
| Choques fracos | `CrashDamagePerMps` ↑ (1,8), `CrashSafeMps` ↓ (4) |
| Choques que destroem demais | `CrashDamagePerMps` ↓, `CrashSafeMps` ↑ |
| Roda demais com toques | `CrashSpinRadiusM` ↑ (1,8 → 2,4) ou `CrashSpinMax` ↓ |
| Ressalto demais | `CrashRestitution` ↓ (0,3) |
| Raspar não trava | `CrashFriction` ↑ (0,35) |
| Perde a condução muito tempo | `CrashWobbleSeconds` ↓ (1,1) |
| Câmara demasiado mole nos saltos | `CamVerticalLag` ↑ (4 → 6) |

A sandbox numérica tem os mesmos números: se mudares um no C++, muda-o também em
`Scripts/physics_sandbox/vertical.py` ou `crash.py` e volta a gerar os gráficos.
- `python3 Scripts/physics_sandbox/vertical.py Docs`
- `python3 Scripts/physics_sandbox/crash.py Docs`
