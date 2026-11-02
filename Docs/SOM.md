# Som do jogo (2026-10-25)

O som da corrida é **sintetizado ao vivo**, sem gravações em loop, e mistura-se em estéreo a 48 kHz para a nave que tem
a câmara. O DSP está em `Source/ExtractingStardust/Private/Flight/EXSoundSynth.h`, em C++ puro. O mesmo código corre
no jogo, através do componente `UEXCraftAudio`, e no renderizador de pré-visualização, que escreve WAVs sem o Unreal:

```
g++ -O2 -std=c++17 -I Source/ExtractingStardust/Private/Flight Scripts/audio/render_sound_preview.cpp -o render_sound
./render_sound <pasta>      # corrida.wav, passagens.wav, naves.wav
```

## Camadas

- **Motor de plasma**, com timbre próprio para cada nave (`TimbreFor`, no topo do `EXSoundSynth.h`):
  - núcleo: dente de serra sem aliasing, um por motor e ligeiramente desafinados, por isso 2 ou 3 motores batem entre
    si. Passa por um filtro passa-baixo ressonante que abre com o acelerador;
  - "rosnar" de combustão (rajadas de ruído a cada ciclo do motor), apito da turbina, sub-grave e rugido do nitro;
  - o tom segue a velocidade e o acelerador, com inércia de cerca de 0,35 s.
  - Carácter de cada nave:
    - STRIX: dois motores empilhados;
    - WRAITH: três motores, batimento suave;
    - NOMAD: industrial e áspero;
    - BASTION: grave e blindado;
    - VORTEX: agudo, a gritar.
- **Ar:** vento estéreo que sobe de tom e de volume com a velocidade, com rajadas e um chiado perto da velocidade
  máxima. Uma parede perto num dos lados faz um "whoosh" desse lado (sondas de parede da câmara).
- **Contacto:** zumbido do hover junto ao chão, chiar do drift e raspar na parede.
- **Eventos:**
  - embate (pancada grave, estalo e "clank" metálico): em paredes e naves acima de 8 m/s, e ao perder uma vida;
  - aterragem;
  - arranque do nitro.
- **Rivais:** os 8 mais próximos (até 500 m) com o motor de cada um. A distância atenua e abafa o som (absorção do ar),
  há pan esquerda/direita a partir da câmara e efeito Doppler, com uma velocidade do som estilizada de 420 m/s.
- **Mestre:** limitador suave. No hangar o volume fica a 35 % e na contagem a 60 %.

## Afinar

- `TimbreFor` (`EXSoundSynth.h`): tom, motores, apito, rosnar e sub de cada nave.
- `FMixer::Render`: volumes do vento, das paredes, do drift e dos eventos.
- `FillAudioOthers` (`EXHoverCraft.cpp`): distância, Doppler e quantos rivais se ouvem.

Para ouvir uma afinação, mudar o código, correr o `render_sound` e escutar os WAVs. Só depois compilar o jogo.

## Motor v2 (2026-11-02, aprovado e ligado no jogo)

Pedido do jogador: "sons de motores viciantes, com adrenalina". É o `FEngineV2` do `EXSoundSynth.h`, que o `FMixer` usa
para o motor do jogador e para os rivais. O `FEngine` antigo ficou no ficheiro só para o antes/depois.

Para ouvir:
- `Docs/SOM/motor_corrida_v2.mp3`: uma corrida com a STRIX;
- `Docs/SOM/motores_naves_v2.mp3`: as 5 naves;
- `Docs/SOM/antes_depois_v2.mp3`: o mesmo arranque, primeiro com o motor antigo e depois com o novo.

O que tem:
- **Mudanças de potência:** cada nave tem 4 a 6 estágios, e os primeiros são curtos. Dentro de cada um o tom sobe. Na
  mudança há um corte de ignição, o tom cai e vem um "soco".
- **Estalos (afterfire):** ao largar o acelerador e em cada mudança. Nas reduções há também um toque de acelerador.
- **Limitador na grelha:** com o acelerador a fundo antes da partida, o motor bate no corte ("brap-brap").
- **Nitro:** o motor "respira" (−7 dB), vem uma pancada grave a descer e depois o rugido, com o apito a subir.
- **Realismo:**
  - ressonâncias fixas do bocal e do casco;
  - cada explosão diferente da anterior, na força e no tempo;
  - rugido de jato turbulento em estéreo;
  - a turbina vai atrasada em relação às rotações;
  - saturação com o acelerador, e compressor.
- **Mais grave** (jogador, 2026-11-02): o tom ficou cerca de 6 meios-tons abaixo e as ressonâncias 20 % abaixo. Há mais
  sub, saturado para se ouvir também em colunas pequenas, e o rugido, os estalos e a ignição do nitro estão mais fundos.
  Na corrida de teste, a energia abaixo de 150 Hz passou de 13 % para 36 %.
- **Cada nave:**
  - STRIX: dois núcleos, equilibrada, 5 estágios;
  - WRAITH: turbina suave, estágios quase sem corte, 6;
  - NOMAD: áspera, com estoiros, 4;
  - BASTION: grave, com pancadas fundas, 4;
  - VORTEX: aguda, a gritar, 6.

Pré-visualização só do motor:
```
g++ -O2 -std=c++17 -I Source/ExtractingStardust/Private/Flight Scripts/audio/render_engine_preview.cpp -o render_engine
./render_engine <pasta>
```
Com `EX_ENGINE_LOG=1` escreve o estágio e as rotações a cada 0,5 s.

**No jogo:**
- O motor do jogador é estéreo e recebe o `Grounded`.
- Os rivais usam a versão leve e soam a metade (`kOtherEngineGain`), para ficarem ao nível dos antigos.
- O `BoostKick` ficou só com o sopro de ar, porque a pancada do nitro é agora a ignição do próprio motor.
- Os filtros recalculam-se a cada 32 amostras. Com o jogador e 8 rivais, o som gasta o mesmo processador que o antigo
  (cerca de 8 % de um núcleo na nuvem).
- A mistura do jogo com o motor novo ouve-se em `Docs/SOM/jogo_corrida_v2.mp3` e `jogo_passagens_v2.mp3` (rivais a
  passar). Faz-se com o `render_sound_preview.cpp`.

**Sem gravações:** a rede da nuvem bloqueia o freesound e a Wikimedia. Para juntar camadas gravadas (CC0), o jogador tem
de autorizar esses domínios no ambiente.
