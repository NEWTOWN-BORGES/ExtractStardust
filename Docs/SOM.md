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
