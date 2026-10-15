# Estado do trabalho — handoff entre máquinas

Documento de continuidade. Quem retomar este projeto (noutra sessão, noutra
máquina, ou outra pessoa) deve ler isto primeiro.

**Atualizado:** 2026-10-15

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
