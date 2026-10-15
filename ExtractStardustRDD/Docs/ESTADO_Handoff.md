# Estado do trabalho — handoff entre máquinas

Documento de continuidade. Quem retomar este projeto (noutra sessão, noutra
máquina, ou outra pessoa) deve ler isto primeiro.

**Atualizado:** 2026-10-15

---

## Estado à vista

| Área | Estado |
|---|---|
| Compilação dos 9 assemblies | ✅ verificada sem abrir o editor |
| Economia / meta-jogo | ✅ 45 701 verificações a passar |
| Geometria da pista (com erosão e detrito) | ✅ verificada sobre o sandbox |
| Erosão 3D das paredes | ✅ na pista real (Blender) e no laboratório (C#) |
| Detrito no pé das paredes | ✅ ligado à pista real |
| Variação macro da cor | ✅ no shader partilhado |
| Normal map tangente | ✅ shader + tangentes no import |
| Shaders | ⚠️ **nunca compilados** (sem GPU) |
| Física do wall-ride com erosão | ⚠️ **por reconfirmar no Unity** |
| fps com o shader novo | ⚠️ **por medir** |
| CI | ⏸️ escrito mas desligado e não publicado |

---

## Onde está o código

Ramo de trabalho: **`red-dust-divide-v2`** (o `main` fica intacto).
Remoto: `github.com/NEWTOWN-BORGES/ExtractStardust`

```powershell
git fetch origin
git checkout red-dust-divide-v2
```

## O que foi feito (por ordem, do mais antigo)

1. **Desbloqueou a compilação.** A Unity 6000.6 promoveu `Object.GetInstanceID()`
   a erro (`CS0619`) e isso partia `RedDust.Track` e, em cascata, 5 assemblies.
   Passou a `GetEntityId()`.
2. **Ferramentas portáveis.** `check_compile.ps1`, `test_meta.ps1` e
   `m1_pipeline.ps1` tinham caminhos absolutos e exigiam o editor aberto.
   Passaram a detectar a versão do editor e a funcionar sem `Library/`.
3. **CI no GitHub Actions** (`Docs/ci.yml.referencia`) — **desligado** e **não
   publicado** (publicar em `.github/workflows/` exige o scope `workflow` no
   token). Decisão: por agora compila-se em casa.
4. **Erosão 3D das paredes** — portada do laboratório (C#) para o Blender.
   `erode3d` em `rdd_route_lib.py`, aplicada no `sculpt`.
5. **Cone de detrito** no pé das paredes, também na pista real.
6. **Variação macro da cor** (`RDColour.hlsl`) — mata o efeito de "corredor
   castanho com faixas iguais durante quilómetros". No shader partilhado, logo
   vale para todas as pistas.
7. **Normal map tangente** com textura de rocha procedural.

## Verificação — correr antes de gerar geometria

Não é preciso Blender nem Unity para validar a matemática:

```powershell
python Tools\verifica_sculpt_real.py     # geometria real do sculpt, sobre o sandbox
python Tools\verifica_detrito.py         # perfil: monotonicidade e zona livre
python Tools\verifica_erosao3d.py        # campo 3D: escalas e amplitude
```

O `verifica_sculpt_real.py` carrega o **rdd_route_lib real** com stubs de
`bpy`/`mathutils` (só a classe `MeshOut` os usa) e corre o pipeline completo.
Última execução: **0 NaN, largura útil inalterada, erosão 23,75 m, detrito não
toca na ride line**.

E a compilação dos scripts:

```powershell
powershell -ExecutionPolicy Bypass -File Tools\check_compile.ps1   # 9/9 assemblies
```

## Pendências conhecidas

| # | Pendência | Onde |
|---|---|---|
| 1 | **Reconfirmar a física do wall-ride.** A erosão desloca a parede até ~22 m na banda da ride line (média 1,41 m). O teste T4 do M1 exige superfície ≥ 58–65°. Só se mede no Unity. | `Red Dust / 3. Validar fisica (M1)` |
| 2 | **Medir o fps.** `RDColour.hlsl` faz 80 avaliações de ruído por pixel. Se pesar, `RD_MACRO_FBM3=1` corta para 48, e `RD_MACRO=0` desliga. | material `Geology.mat` |
| 3 | **Validar os shaders.** Não foram compilados (sem GPU no ambiente onde foram escritos). Primeiro `Build` em casa é o teste. | `RDColour.hlsl`, `RDGeology.shader` |
| 4 | **Não há detrito no laboratório com a mesma forma da pista** — são geradores diferentes (C# e Python), com a mesma paleta mas algoritmos separados. | `LabGeometry.cs` vs `rdd_route_lib.py` |
| 5 | **Referências de IP.** Uma das imagens em `Docs/referencias/` é um frame de um jogo comercial. O plano (conflito C13) diz que a regra de IP original ganha. | `Docs/referencias/ref_gameplay_*.jpg` |
| 6 | **Falta acrescentar as novidades ao `spec.json`** se quiseres valores diferentes por pista: `erosion_m`, `erosion_seed`, `talus_h`. Os defaults já estão no código. | `Art/Courses/*.json` |

## Sobre acessos remotos (verificado)

Não há controlo remoto no DSH, e é **deliberado**. O próprio código recusa:

```
error: --host 0.0.0.0 is intentionally not supported yet for safety:
it would expose remote code execution to the network; use 127.0.0.1 instead
```

A documentação explica porquê: *"the server carries no TLS, authentication, or
origin policy of its own"*. O servidor escuta apenas em `127.0.0.1`.

Dois avisos que valem a pena guardar:

- `--trusted-host` **não dá identidade**. A documentação é explícita: *"a trusted
  but unauthenticated request returns 401; these checks never establish identity"*.
  Não é porta dos fundos.
- Expor por túnel (ex.: `cloudflared`, que está instalado nesta máquina) daria
  HTTPS mas **não autenticação** — qualquer pessoa com o URL teria execução de
  código. Não usar.

**Como se resolve a continuidade entre máquinas:** pelo repositório, não por
controlo remoto. Este documento é o canal. Numa sessão nova, em qualquer máquina:

```
Lê ExtractStardustRDD/Docs/ESTADO_Handoff.md e continua o trabalho
```

## Ordem recomendada no PC de casa

**Importante:** a sessão de casa **não gera a geometria nem o build sozinha**. O
Blender e o Unity exigem que os comandos sejam corridos, e o Unity exige presença
humana para abrir o editor. O papel da sessão é **saber o que fazer, em que ordem,
e corrigir o que falhar** — não é automatizar tudo.

E também: **abrir o projeto no Unity não gera a geometria.** O Unity importa o que
existe; quem gera é o pipeline (`m1_pipeline.ps1`).

### Passo 0 — verificar o estado

```powershell
cd ExtractStardustRDD
powershell -ExecutionPolicy Bypass -File Tools\preflight.ps1
```

Diz o que existe, o que falta e o comando exato. Se o Blender não estiver
instalado, ele queixa-se — e é um bloqueio real.

### Passo 1 — validar sem gastar tempo

```powershell
powershell -ExecutionPolicy Bypass -File Tools\check_compile.ps1   # 9/9
python Tools\verifica_sculpt_real.py                               # geometria
```

Se isto falhar, não vale a pena gerar 1,4 GB.

### Passo 2 — abrir o Unity uma vez

O primeiro import de 1119 ficheiros compila os shaders novos. É aqui que aparecem
erros de shader, se houverem. **Vale a pena fazer só isto primeiro**, porque é o
risco menos testado do trabalho.

### Passo 3 — laboratório (rápido, ~2 min)

```powershell
powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course sandbox -Build
```

Depois, no Unity: `Red Dust / 3. Validar fisica (M1)`.

**O teste T4 é o que importa.** A erosão desloca a parede até ~22 m na banda da
ride line; se o wall-ride deixou de funcionar, é aqui que se vê.

### Passo 4 — só depois, a expedição completa

```powershell
powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course red_dust_divide -Build
```

### Expectativa de tempo realista

| Passo | Tempo | Notas |
|---|---|---|
| 1. verificações | minutos | sem Unity nem Blender |
| 2. primeiro import do Unity | **20–40 min** | 1119 ficheiros + compilação de shaders |
| 3. laboratório | ~2 min + build | |
| 4. expedição | ~10 min + import | + build |
| Tutura de problemas | imprevisível | ver riscos abaixo |

**Não é "esperar e jogar".** É correr, ver o que rebenta, corrigir, repetir. O
trabalho foi feito para que os erros apareçam cedo e sejam diagnosticáveis, não
para que não existam.

### Riscos concretos, por ordem de probabilidade

| # | Risco | Sintoma | O que fazer |
|---|---|---|---|
| 1 | **Shader não compila** | erros no Console do Unity | mandar o log; nunca foram compilados (sem GPU) |
| 2 | **Física do wall-ride** | T4 falha no validador | reduzir `erosion_m`, ou restringir o wall-ride |
| 3 | **fps** | abaixo de 60 | `RD_MACRO_FBM3=1` (48 em vez de 80 ruídos/pixel), ou `RD_MACRO=0` |
| 4 | **Blender não instalado** | preflight queixa-se | instalar Blender 5.2 |
| 5 | **Versão do Unity diferente** | aviso do pipeline | já tratado: as ferramentas detectam; se o projeto pedir 6000.3 e só houver 6000.6, o pipeline avisa e usa a instalada |
| 6 | **Primeiro import lento ou trava** | parece pendurado | é normal num i5-4460; esperar |

## Convenções que não se devem quebrar

- **O ruído do projeto está centrado em ZERO.** `rdd_geology.fbm3` vai de −0,67 a
  +0,69 (mede-se em `verifica_port_erosao.py`). O `rd_noise` do shader é que é
  0..1. Trocar as convenções faz a erosão sair a zero ou a oscilar.
- **As sementes de ruído têm de ser INTEIRAS.** O `_hash` do `rdd_geology` faz
  `(seed * 0x9E3779B1) & 0xFFFFFFFF` e rebenta com `TypeError` se for float.
- **Em deslocamento por normal partilhada, nunca usar máscara binária.** O degrau
  arrasta os vértices vizinhos. Usar sempre ramp.
- **O ruído fino (< 4 m) é para textura, não geometria.** Resolvê-lo em geometria
  exigiria ~1 M de triângulos por parede.
- **Não editar ficheiros Python com `Set-Content -Encoding UTF8` da PowerShell
  5.1** — lê UTF-8 como ANSI e corrompe os acentos. Usar a ferramenta de edição.

## Onde está o ouro (documentação)

| Ficheiro | Conteúdo |
|---|---|
| `Docs/RDD_00_Plano_Vertical_Slice.md` | o plano mestre e os milestones M0–M10 |
| `Docs/RDD_V2_Plano_Fase0.md` | o plano da V2 e as 8 tarefas da Fase 1 |
| `Docs/M1_Relatorio_Fisica.md` | M1 validado: 21/22 testes |
| `Docs/RDD_Erosao_Parametros.md` | erosão e detrito: parâmetros e armadilhas |
| `Docs/CI_e_Fluxo_Duas_Maquinas.md` | o fluxo entre o PC do trabalho e o de casa |
