# Destroços e explosão (2026-11-01)

Pedido do jogador:
- "Quero a carcaça das naves destruídas a alta velocidade a voar em frente e a cair, dando várias voltas, cambalhotas.
  Trabalhe essa vista também e melhore a explosão. Veja exemplos online e mande fotos."
- "Os módulos podem voar carbonizados, já que são peças separadas. Se possível, faça-o em Blender."
- "A física dos objetos a voar depende de como a nave é destruída. Faça várias simulações."
- Depois de ver as fotos, escolheu "peças em bolas de fogo" (o casco e os módulos a voar a arder, com rasto de chamas e
  fumo, tipo cometa) e "ver a mexer" (vídeo).

Ficou assim:
- **Simulado aqui:** física das peças em `Scripts/physics_sandbox/wreck.py` e fotos em Blender com `wreck_sims.py`
  (`DESTROCOS_<causa>.jpg`).
- **Vídeo** (`wreck_video.py`, `DESTROCOS_<causa>.mp4` e `.gif`): o que o jogo vai mostrar, com os mesmos números, as
  mesmas texturas animadas e a câmara do jogo (secção 6).
- **No jogo:**
  - `AEXWreck`: o casco e os módulos voam e batem pelos cantos.
  - `AEXHoverCraft::Eliminate`: a causa decide como as peças arrancam.
  - `UpdateCrashCam`: câmara lenta à volta do casco.
  - `AEXExplosion`: a explosão nova.
- **Texturas da explosão e do fogo:** renderizadas em Blender (`Scripts/make_fx_flipbooks.py`, em `SourceArt/FX`).
  Os materiais são feitos pelo `Scripts/make_fx_assets.py` (passo 3d do `casa_tudo.ps1`).

## 1. O que acontece quando o casco acaba

1. **Explosão** no sítio (secção 4), levada um pouco pela velocidade da nave.
2. **Destroços:** o casco, carbonizado, e cada módulo montado (asas, cauda, kit, refrigeração...) passam a peças
   separadas.
   - Cada peça sai com a velocidade da nave e roda conforme a causa da morte (secção 2).
   - Voa, dá cambalhotas e bate no chão e nas paredes. Em cada pancada forte levanta poeira e faíscas, e fogo enquanto
     o casco está quente.
   - **Cada peça voa como uma bola de fogo:** chamas em cima dela, viradas para trás pelo vento do voo (para cima quando
     abranda), e um rasto de chamas atrás que vira fumo. O casco arde 11 s e os módulos 4,5-7 s. O casco também deita
     uma coluna de fumo. As brasas nas fendas apagam-se aos poucos.
   - Ao fim de 15 s as peças encolhem e desaparecem.
3. **Câmara do jogador (como no Burnout):**
   - O tempo abranda para **0,3×** durante 1,6 s (tempo real) e volta a 1× em 0,8 s.
   - A câmara roda à volta do casco, de trás e de lado (−115°) até à frente e de lado (+20°), a 15 m e 4,5 m acima.
   - Segue o casco, não atravessa rochas e fecha o FOV de 58° para 48°.
4. **Takedown** (o jogador destrói um adversário): câmara lenta curta, 0,4× durante ~0,6 s, que volta ao normal em 0,3 s.

## 2. Como morreu → como voa

A nave guarda a última pancada (variação de velocidade e ponto de impacto) e a última aterragem. Se aconteceram até
0,4 s antes de o casco acabar, decidem como as peças arrancam. T = clamp(velocidade / 12, 3, 11) rad/s.

| Causa | Como se reconhece | Arranque do casco | Simulação (4 s, `wreck.py`) |
|---|---|---|---|
| **De frente contra a rocha** | Pancada contra a frente (> 8 m/s) | Ressalta para trás e dá uma **cambalhota para trás** (0,9 T), +3 m/s para cima | 34 m, 1,7 voltas, para |
| **Pancada lateral (em T)** | Pancada de lado (> 60 % dela) | **Barrel roll** para o lado do empurrão (1,35 T), +3 m/s para cima | 176 m, 2,5 voltas |
| **Aterragem de nariz** | Aterragem a mais de 15 m/s | **Cambalhota para a frente** (0,6 T): o nariz enterra-se e o casco salta por cima dele | 99 m, 4,8 voltas |
| **Empurrão na traseira (PIT)** | Pancada por trás | **Cambalhotas para a frente** com torção (T), +4 m/s em frente | 316 m, 6,1 voltas |
| **Desgaste** (casco a zero a raspar) | Nenhuma das outras | **Cambalhotas para a frente** com torção (T) | 255 m, 6,8 voltas |

Em todos os casos:
- O sopro da explosão atira o casco 5 a 9 m/s para cima.
- Uma pancada fora do centro soma a sua rotação: (ponto − centro) × Δv / 4.
- Os módulos (110 kg cada) saem com 95 % da velocidade, mais 7-14 m/s para fora e 3-8 para cima, e rodam 6-14 rad/s
  ao acaso.

**Regra do sentido:** a rotação tem de "tropeçar" para o lado para onde o casco vai, ou seja, o topo roda nesse
sentido. Assim o atrito no chão alimenta-a. No sentido contrário, o primeiro toque no chão mata a rotação e o casco
desliza deitado. Foi o que se viu na primeira simulação lateral, que estava ao contrário.

## 3. A física das peças (`AEXWreck::StepPiece` = `wreck.py`)

- **Forma:** cada peça é a caixa da sua malha, com a massa e a inércia dessa caixa. O casco pesa `GetCrashMassKg()`
  (com os módulos), cada módulo 110 kg.
- **Contacto:** os 8 cantos tocam no chão (traço para baixo) e nas paredes e rochas (varrimento ao longo do movimento).
  Cada canto que entra recebe um impulso:
  - ressalto de 0,32 acima de 2 m/s;
  - atrito de 0,55.
- **Pancada forte** (mais de 10 m/s contra o chão): a carroçaria esmaga-se e o canto enterra-se na areia.
  - O atrito passa a **1,7**, e é isto que faz a nave saltar por cima do nariz.
  - A peça fica com **80 %** da rotação.
  - Sem isto, uma caixa aos trambolhões a 100 m/s rola como uma roda e acelera até 35 rad/s, e a aterragem de nariz só
    batia e deslizava.
- **Limite:** a ponta de uma peça nunca gira a mais de 45 m/s à volta do centro (o casco anda à volta de 14 rad/s, ou
  2 voltas por segundo).
- **Números gerais:**
  - gravidade de 22 m/s² (a do jogo);
  - arrasto de 0,08 no movimento e 0,25 na rotação;
  - passos de 1/120 s;
  - a peça para quando fica 0,6 s quase parada.

## 4. A explosão (`AEXExplosion`)

Feita a partir de explosões reais e da prática de efeitos de jogos (fontes no fim):
1. **Clarão:** luz de 6000 cd que cai depressa (36× o sol a 5 m) e núcleo branco de 0,2 s. Eram 90 000 cd, que com a
   câmara lenta deixavam o ecrã branco muito tempo.
2. **Bolas de fogo:** 5 sprites `T_FX_Fireball`, com 64 fotogramas cada.
   - Saem a 0,04 s umas das outras e crescem de 3 m para 11-16 m em 1,6-2,2 s.
   - Rolam, sobem, arrefecem do amarelo-branco para o laranja e o vermelho e acabam em fumo escuro.
3. **Segunda explosão** a 0,32 s, ao lado da primeira e com clarão próprio. Faz a explosão parecer maior (prática
   comum nos efeitos de jogos).
4. **Anel de choque** rente ao chão (46 m em 0,55 s) e **anel de poeira** atrás dele (10 nuvens a 18-26 m/s, cor de
   areia).
5. **Destroços em brasa** (18) e **faíscas** (60), que riscam o ar.
6. **Coluna de fumo** de combustível, quase negro: 8 nuvens que sobem e ficam 4-5,5 s, até 27 m.
7. **Pancadas dos destroços** (`IgniteImpact`): poeira, faíscas e uma língua de fogo nos primeiros 3 s. No máximo 10
   por segundo por destroço.

**Os destroços, cada peça uma bola de fogo:**
- **Chamas** (`T_FX_Fire`, 4 × 4 fotogramas, 16 por segundo, em loop) do tamanho da peça (0,8-1,7×, a encolher com o
  calor).
  - Rodadas no ecrã para irem na direção do vento do voo, mais 4 m/s de calor a subir: para trás a alta velocidade, para
    cima quando a peça abranda.
- **Rasto de fogo:** uma língua de fogo (`T_FX_Fire` em forma de lágrima, virada para trás) a cada 1/5 do tamanho da
  peça.
  - No máximo 60 por segundo no casco e 40 nos módulos, até 100 por destroço. Vive 0,45 s.
  - Nunca é mais pequena do que o espaço desde a anterior, por isso juntam-se num rasto contínuo.
- **Fumo de cada peça:** cinzento escuro, `T_FX_Smoke` do tamanho da peça, até 80 por destroço. A voar, faz um rasto de
  fumo atrás do fogo.
- O **casco** tem ainda uma luz laranja de 60 cd a 2,5 m, que treme e dá um tom laranja à areia à volta (o sol tem
  10 lux; antes eram 1500 cd, que queimavam o casco de luz), e uma coluna de fumo cinzento (`T_FX_Smoke`, até 45
  nuvens).

**Carbonizado** (`M_FX_Char`, por cima da pintura):
- A fuligem deixa ver a pintura a 4-26 %, com a luz e a forma da nave.
- Fendas em brasa, que tremem e se apagam com `Heat` (de 1 a 0 em 11 s).

Sem os materiais novos (antes do passo 3d), o jogo usa as formas antigas da explosão e as peças voam com a sua cor.

## 5. As texturas (Blender, `Scripts/make_fx_flipbooks.py`)

- **Como são feitas:** volumes procedurais no Cycles, ruído 4D com fogo de corpo negro (3500 K → vermelho). O
  Mantaflow não corre no Blender do pip. Um fotograma por célula:
  - `T_FX_Fireball` (8 × 8): bola de fogo que incha, rola e arrefece até fumo;
  - `T_FX_Smoke` (8 × 8): nuvem iluminada que cresce e se desfaz, tingida no jogo (negro, cinzento, areia);
  - `T_FX_Fire` (4 × 4 em loop): chamas a lamber para cima.
- **Formato:** RGB = cor já multiplicada pela opacidade, A = opacidade. O `M_FX_Flipbook` desenha em *AlphaComposite*
  (alfa pré-multiplicado): o fogo fino continua a brilhar e o fumo escurece o que está atrás.
  - O material mistura dois fotogramas e fica suave onde toca no chão (1,5 m).
  - **Rotation** (radianos) roda a imagem no ecrã, com as bordas esbatidas para não se ver o quadrado. Os sprites da
    explosão vão rodados ±0,4 e os do rasto ±0,6. As chamas das peças rodam com o voo.
  - Se as chamas aparecerem de cabeça para baixo no jogo, pôr **FlipV = 1** no `M_FX_Flipbook`.
- **Velocidade:** `volume_biased` (volumes em ray marching). O modo novo do Cycles constrói antes uma árvore de todo o
  ruído, que custa 25 s por fotograma: assim é 10× mais rápido.
- **Prova:** `SourceArt/FX/preview_<nome>.jpg` mostra cada fotograma sobre areia, ao brilho do jogo.
  O resumo das três está em `Docs/DESTROCOS_texturas.jpg`.

```
python3 Scripts/make_fx_flipbooks.py                 (ou: blender -b -P Scripts/make_fx_flipbooks.py --)
python3 Scripts/make_fx_flipbooks.py -- <pasta> fireball size=128 samples=12 frames=8   (vista rápida)
```

## 6. Simulações e vídeo (para afinar)

```
python3 Scripts/physics_sandbox/wreck.py              (números de cada causa)
python3 Scripts/physics_sandbox/wreck_sims.py -- <pasta> [causas]   (fotos: VORTEX com asas, cauda, kit e refrigeração)
python3 Scripts/physics_sandbox/wreck_video.py -- <pasta> [causas] [size=960x540] [samples=20]   (vídeo; test=1: 8 fotos)
```

**O vídeo** reproduz o jogo:
- a câmara de crash (0,3× durante 1,6 s, a rodar à volta do casco);
- a explosão do `AEXExplosion::Ignite`;
- os destroços do `AEXWreck`: chamas, rastos, fumo, e poeira, faíscas e fogo nas pancadas.

Usa as mesmas texturas animadas, em sprites virados para a câmara como no jogo. As cores vão em ACES, perto do
tonemapper do Unreal. Os vídeos estão em `Docs/DESTROCOS_<causa>.mp4` (e `.gif`, mais pequeno).

Fotos em `Docs/DESTROCOS_<causa>.jpg`. Em cada uma:
- a câmara segue o casco;
- a nave tem rastos fantasma de 0,05 s;
- a bola de fogo fica onde a nave morreu e arrefece;
- há poeira onde as peças bateram.

## 7. Em casa

1. Compilar e correr `Scripts\casa_tudo.ps1 -SemPista`. O passo 3d importa as texturas e faz o `M_FX_Flipbook` e o
   `M_FX_Char`. Ver no log `FXASSETS textures 3 of 3 ... 0 problems`.
2. `Scripts\jogar.ps1 -Modo Sandbox` e, na consola (a tecla do til, ou a que está por baixo do Esc), **`EXBoom 0`** a **`EXBoom 4`**:
   - 0 desgaste;
   - 1 de frente;
   - 2 lateral;
   - 3 nariz;
   - 4 traseira.
   A nave volta 3 s depois. Log: `EXRACE BOOM`.
3. Ver:
   - a câmara lenta e a câmara à volta;
   - o casco a voar em frente e às voltas;
   - os módulos carbonizados;
   - a bola de fogo a arrefecer em fumo;
   - o anel de poeira;
   - cada peça a voar como uma bola de fogo, com as chamas para trás e o rasto a virar fumo (comparar com os vídeos).
   - Ver os fps com `stat fps` durante uma explosão perto e com vários bots a explodir (secção 8).
4. **Afinar:**
   - a física, em `EXWreck.cpp` (constantes no topo, iguais às do `wreck.py`);
   - o arranque por causa, em `AEXHoverCraft::Eliminate`;
   - a câmara, em `UpdateCrashCam` (0,3×, 1,6 s, 15 m);
   - a explosão, em `AEXExplosion::Ignite`.

## 8. Fps (jogador, 2026-11-02: "cuidado com as quedas de fps")

- **Sem reconstruir o render a cada fotograma:** antes, mudar o tamanho de um sprite (`UMaterialBillboardComponent`)
  reconstruía o seu estado de render em todos os fotogramas, e com centenas de sprites vivos era o que pesava.
  - Agora o quadrado cresce aos degraus de 25 % e a imagem cresce dentro dele com o parâmetro `Zoom` do `M_FX_Flipbook`
    (`Flight/EXFxSprite.h`).
  - Fica uma reconstrução a cada poucas décimas de segundo, em vez de uma por fotograma.
- **Peças acabadas não gastam:** sprites e peças da explosão que já acabaram deixam de ser atualizados.
- **Pela distância à câmara:**
  - até 120 m: tudo;
  - de 120 a 300 m: metade do rasto e do fumo, sem estoiros nas pancadas;
  - acima de 300 m: só as chamas em cima das peças.
  - Uma explosão a mais de 250 m é mais pequena: 3 bolas de fogo, sem segunda explosão, metade do fumo e da poeira, 8
    destroços e 20 faíscas.
- **Muitos destroços ao mesmo tempo:** o rasto e o fumo repartem-se. Com 4 destroços cada um deixa metade, com 6 um
  terço.
- **Tetos por destroço:** 100 línguas de fogo e 80 nuvens de fumo, reutilizando as mais velhas. Cada pancada dá 6-14
  faíscas (eram 10-24).
- **Se ainda houver quebras em casa:** baixar `MaxTrails`, `MaxSmoke`, `HullTrailRate` e `ModuleTrailRate` (topo de
  `EXWreck.cpp`), ou `NearM`/`FarM`.

## Fontes (exemplos vistos)

- [Burnout Paradise, análise (bit-tech)](https://bit-tech.net/reviews/gaming/xbox/burnout_paradise/3/): câmara lenta e
  vista do acidente.
- [ESRB, Burnout Paradise Remastered](https://www.esrb.org/ratings/35370): os carros "capotam, dão cambalhotas e
  desfazem-se" em câmara lenta.
- [realtimevfx, explosão em jogo](https://realtimevfx.com/t/explosion-effect-help-needed/16021): clarão, bolas de fogo
  em camadas, explosão secundária, fumo que fica.
- [Houdini, onda de choque pyro](https://www.sidefx.com/docs/houdini/shelf/pyrosimpleshockwave.html): anel de choque e
  poeira rente ao chão.
- [CMU, Animating Explosions](https://www.ri.cmu.edu/publications/animating-explosions): bola de fogo que sobe, rola e
  arrefece até fumo.
