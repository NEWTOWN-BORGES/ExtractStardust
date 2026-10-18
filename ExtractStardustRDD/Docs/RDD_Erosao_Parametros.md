# Erosão e detrito — parâmetros e verificação

Como o aspeto das paredes se controla, e como se verifica antes de gerar 1,4 GB de
geometria.

## Onde está o quê

| Peça | Ficheiro | Âmbito |
|---|---|---|
| `erode3d` (recuo por dureza) | `Art/Blender/rdd_route_lib.py` | pista real (é o que o pipeline usa) |
| `sculpt` com erosão | `Art/Blender/rdd_route_lib.py` | paredes da secção de corrida |
| `Erode3D` (equivalente em C#) | `Assets/RedDust/Runtime/Lab/LabGeometry.cs` | Metrics Lab |
| Gerador/verificador | `Tools/verifica_detrito.py`, `Tools/verifica_erosao3d.py` | verificação local |

> `Art/Blender/rdd_build_course.py` tem uma **cópia** da mesma matemática. Não é
> importado pelo pipeline atual (o `rdd_build_route.py` importa o `rdd_route_lib`),
> mas foi mantido em sincronia para não haver divergência silenciosa.

## Parâmetros

Em `Art/Courses/<pista>.json`:

| Campo | Por omissão | Efeito |
|---|---|---|
| `erosion_m` | `70.0` | amplitude da erosão das paredes em metros. **0 desliga** e volta ao aspeto anterior |
| `erosion_seed` | `7` | semente. **Tem de ser inteiro** |
| `talus_h` | `9.0` | altura do cone de detrito no pé das paredes. **0 desliga** |

### Amplitude da erosão

Medida sobre o sandbox (a escala é aproximadamente proporcional):

| `erosion_m` | Deslocamento máximo |
|---|---|
| 26 | ~9 m (discreto demais a 100 m/s) |
| **70** | **~24 m** ← por omissão |
| 100 | ~34 m |
| 150 | ~52 m |

Ordem de grandeza por camada (medido com o ruído real do projeto):

| Camada | Dureza | Recuo máximo |
|---|---|---|
| Chinle | 0,15 | ~5,8 m |
| Organ Rock | 0,30 | ~7,4 m |
| Moenkopi | 0,45 | intermédio |
| Navajo | 0,85 | quase nulo |
| Wingate | 0,97 | ~0,05 m (cornija) |

A camada mole recua e forma alcova; a dura resiste e sobressai. É isso que dá a
leitura de canyon.

## Duas armadilhas que já custaram tempo

**1. O ruído do projeto está centrado em ZERO, não em 0,5.**

`rdd_geology.fbm3` usa `_G3` e `floor`, e vai de **−0,67 a +0,69** (medido). O
`rd_noise` do shader é que é 0..1 (usa `frac`). As duas convenções convivem no
projeto e trocá-las faz a erosão sair a zero ou a oscilar.

**2. Só recuo, nunca projeção.**

Como o ruído é bidirecional, a erosão apontaria para dentro do corredor em metade
dos pontos — o que não é erosão e **estreita a pista**. As larguras do design (e as
medições da Fase 1) contam com elas. Por isso o `depth` é cortado em zero: a
erosão só afasta a parede, e o corredor fica sempre igual ou mais largo.

**3. Deslocamento com máscara dura arrasta os vizinhos.**

O cone de detrito começou por usar uma máscara binária (`acima > 8 m`). Os vértices
abaixo do limite não recebiam `t_height`, mas como **todos** são deslocados pela
normal partilhada `(Nw)`, o degrau de 0 para `talus_h` entre vértices vizinhos
arrastava-os para fora. Resultado medido: **3,7 m de deslocamento na banda da ride
line** — tornaria o wall-ride pouco fiável.

Corrigido com um ramp quadrático (`u²`) que arranca a 0 m e chega a `talus_h` aos
25 m acima do limite. Passou de 3,7 m para **0,776 m** nessa banda.

Lição geral: em deslocamento por normal partilhada, **nunca usar máscara binária —
usar sempre ramp**.

## Verificar antes de gerar

```powershell
python Tools/verifica_detrito.py       # perfil: monotonicidade, continuidade, zona livre
python Tools/verifica_erosao3d.py      # campo 3D: escalas e amplitude
```

Os dois importam o `rdd_geology` **real** do projeto (numpy puro, sem `bpy`), logo
testam a matemática que vai correr no Blender.

Critérios que têm de passar:

| Critério | Porquê |
|---|---|
| `sempre >= 0` no recuo | senão a pista estreita |
| monotonicidade do perfil | senão a malha auto-intersecta |
| detrito nunca abaixo da zona livre | senão a largura útil diminui |
| correlação moleza ↔ recuo > 0,9 | senão a geologia não se lê |

## Verificação do pipeline (em casa)

Depois de gerar, confirmar que não há sobreposições da pista consigo própria:

```powershell
blender -b -P Art/Blender/rdd_overlap_check.py -- Art/Courses/sandbox.json
```

O `rdd_overlap_check.py` já existe para isto.

## O que **não** está feito

- o **detrito** só existe no laboratório; na pista real o `talus_profile` está
  escrito e verificado mas ainda **não ligado** ao `build_ring`
- as **cores por dureza** na pista real vêm do `Column.sample` do Blender (já
  existiam); a versão por vértice que fiz é do laboratório
