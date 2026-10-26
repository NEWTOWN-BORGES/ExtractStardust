# Plano das texturas — de vez, sem quadrados

Pedido do jogador (2026-10-26): "texturas ricas, até nas naves, tudo cinematográfico, o mais profissional de sempre,
sem os quadrados — já aviso". Temos Lumen a correr bem no PC, por isso o orçamento gráfico sobe.

## 1. Porque falhou antes

| Tentativa | O que se viu | Causa |
|---|---|---|
| Texturas Poly Haven (2026-10-19) | "a areia não parece areia", repetição | Uma só escala, sem quebrar a repetição; cores de outro deserto (cinzento/castanho); escala do grão errada |
| Texturas feitas em código (2026-10-20) | "tudo quadriculado" | Máscaras de baixa resolução (7,8 m por píxel) comprimidas em blocos 4×4 e cortadas com limiares duros |
| Paredes projetadas de cima | "linhas verticais", "derretido" | A textura esticada nas faces quase verticais |
| Agora: sem texturas (cor por código) | limpo, mas pobre ao perto | Falta grão, fissuras e pedra a sério |

## 2. Regras (para nunca mais haver quadrados)

1. **Nenhuma repetição visível.** Cada textura é lida em "mosaico estocástico": cada ladrilho roda e desloca-se ao acaso
   e mistura-se com os vizinhos (técnica de *texture bombing* / *hex tiling*). A mesma textura entra em duas escalas
   misturadas, e por cima vai uma variação de cor muito larga (centenas de metros). Ao longe a escala aumenta.
2. **Máscaras nunca comprimidas nem cortadas a seco.** Mapas de dados sem compressão, suavizados, misturados por altura
   (a areia entra nas fendas da rocha) e partidos com ruído. Nunca um limiar duro.
3. **Paredes em projeção tripla (triplanar).** Nas encostas a textura é projetada dos três lados e misturada pela
   inclinação: nada esticado.
4. **Escala real.** Grão de areia com ladrilho de ~2 m ao perto e ~16 m ao longe; rocha 4-8 m; estratos da rocha pela
   altura do mundo (como os desenhámos no Blender).
5. **Cor nossa.** As fotos dão o relevo e o detalhe; a cor final vem da nossa paleta (vermelho-laranja do Utah/Arizona),
   para todas as camadas combinarem.
6. **Prova antes do build.** Seis vistas fixas (areia ao perto, estrada, falésia, planalto ao longe, túnel, vista aérea)
   fotografadas antes e depois; só se empacota depois do jogador aprovar.

## 3. Fontes (licenças)

- **CC0 (a IA pode usar e transformar):** Poly Haven e ambientCG. Já temos no PC (`SourceArt/PolyHaven`, 2K): red_sand,
  aerial_sand, gravelly_sand, sandstone_cracks, cliff_side, rock_boulder_dry, dry_ground_rocks, red_laterite_soil_stones,
  aerial_grass_rock. Faltam (download ~150 MB, uma vez): areia de dunas com ondulação, arenito estratificado vermelho,
  e para as naves: metal pintado gasto, riscos, poeira, fibra de carbono, metal escovado.
- **Fab / Megascans do jogador:** a licença diz "uso com IA: Não". A IA não os abre nem transforma; os scripts podem
  referi-los pelo caminho no projeto, se o jogador os descarregar (opção B para as falésias).

## 4. O mapa (Expedição)

Material novo do chão, com Lumen (substitui o atual sem texturas, mantendo o que já funciona):

| Camada | Onde | Como |
|---|---|---|
| Areia vermelha | chão plano | textura de areia + as ondulações do vento já feitas em código + brilho do grão ao sol |
| Estrada | pista (campo de distâncias, já nítido) | areia compactada mais escura, marcas de passagem ao longo, linha clara nas bordas |
| Cascalho | encostas 15-40° | gravelly_sand / dry_ground_rocks, mistura por altura |
| Falésias | encostas > 40° | arenito triplanar + estratos pela altura + manchas escuras de "verniz do deserto" a escorrer |
| Planalto | topo das mesas | sandstone_cracks claro (arenito Navajo) |
| Verde | prados e oásis | relva rasteira, partida com ruído |

As rochas soltas (adereços) usam o mesmo material das falésias, para encaixarem nas paredes, com variação por instância.

## 5. As naves

Hoje as naves têm cor lisa por peça. Plano:

- **Material mestre `M_ShipPBR`:** pintura com verniz e um brilho fino de metalizado; por baixo, metal escovado onde a
  pintura gasta.
- **Desgaste nas arestas:** o Blender grava a curvatura de cada peça nas cores dos vértices ao gerar a nave. O Unreal usa-a
  para lascar a tinta nas arestas e escurecer as frestas entre painéis.
- **Sujidade do deserto:** pó vermelho mais forte em baixo e atrás, por projeção (as naves não precisam de UVs).
- **Materiais por zona:** fibra de carbono nas peças Graphite, metal escovado no Metal, borracha, vidro do cockpit com reflexo.
- **Calor no motor:** o metal à volta do bocal ganha os tons azul e dourado do aquecimento.
- **Decalques nossos:** números e emblemas desenhados por nós.

## 6. Cinematográfico (Lumen)

Já feito: Lumen por defeito, nuvens volumétricas, atmosfera com poeira, sol baixo, névoa volumétrica, gradação de cor.
A seguir: exposição com limites fixos (sem "piscar" ao entrar no túnel), reflexos Lumen na estrada molhada do oásis,
sombras de contacto nas naves, e uma câmara de chegada à meta.

## 7. Fases (cada uma com fotos e aprovação)

1. **F1 Areia e estrada**: material novo no chão plano e na pista; 6 fotos; aprovação.
2. **F2 Falésias e rochas**: triplanar, estratos, verniz; as rochas soltas com o mesmo material; fotos; aprovação.
3. **F3 Cascalho, planalto e verde**: fotos; aprovação.
4. **F4 Naves**: curvatura nas cores dos vértices (Blender), `M_ShipPBR`, fotos das 5 naves no hangar; aprovação.
5. **F5 Build final** e afinação de desempenho.

## 8. Orçamento (GTX 1650, 4 GB)

Até ~10 conjuntos de texturas 2K no chão (~160 MB) e 6 nas naves; mapas de dados sem compressão (~60 MB). Objetivo:
60 fps a 1080p com Lumen e TSR (resolução interna 75 % se for preciso). O atalho "Jogar Leve" fica para PCs mais fracos.
