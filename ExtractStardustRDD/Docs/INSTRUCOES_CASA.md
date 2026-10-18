# Instruções para a sessão do PC de casa

Documento para entregar a uma sessão nova (DeepSeek ou humano) no PC de casa.
Objetivo: **fechar o que ficou pendente no PC do trabalho.**

**Ramo:** `red-dust-divide-v2` · **Último commit publicado:** `12ab8c0`

---

## O prompt para colar

> Lê `ExtractStardustRDD/Docs/ESTADO_Handoff.md` e depois
> `ExtractStardustRDD/Docs/INSTRUCOES_CASA.md`.
> Segue os passos por ordem, sem saltar o passo 2.
> Para em cada passo que exija uma decisão minha (ex.: correr o Unity, avaliar o
> aspeto visual) e diz-me exatamente o que fazer e o que esperar.
> Não presumas que algo funciona: verifica e mostra a evidência.

**Antes disso:** confirma a versão do Unity com o passo 0 abaixo — se for mais
antiga que 6000.6.5f1, o projeto não abre.

## Clonar

```powershell
git clone https://github.com/NEWTOWN-BORGES/ExtractStardust.git
cd ExtractStardust
git checkout red-dust-divide-v2
```

> **O `main` NÃO tem este trabalho.** O `main` está 22 commits atrás (parado em
> 13/10). Sem o `checkout` acima ficas com código de dois dias antes, sem erosão,
> sem shaders novos e sem as alterações de motion blur / nitro / hangar.

---

## O que já está feito (não repetir)

Feito e verificado no PC do trabalho:

- ✅ **os shaders compilam** no editor 6000.6.5f1 (era o risco nº1)
- ✅ **a cena do laboratório gera e valida** — 21 zonas, 636 440 vértices
- ✅ **9/9 assemblies** compilam, no Roslyn e no editor
- ✅ **economia:** 45 701/45 701 verificações
- ✅ **erosão 3D e detrito** portados para o Blender (`rdd_route_lib.py`), verificados
  contra o ruído real do projeto
- ✅ **variação macro da cor** no shader (`RDColour.hlsl`)
- ✅ **normal map tangente** com textura procedural
- ✅ projeto atualizado para **Unity 6000.6.5f1** (URP 17.6)

## O que falta (o teu trabalho)

| # | Tarefa | Bloqueada por |
|---|---|---|
| 1 | Instalar Blender 5.2 | nada |
| 2 | Verificar o estado (5 s) | nada |
| 3 | Gerar a geometria do `sandbox` | Blender |
| 4 | **Validar física M1 — o teste T4 (wall-ride)** | passo 3 |
| 5 | Avaliar o aspeto visual das paredes | passo 3 |
| 6 | Medir o fps | passo 3 |
| 7 | Só depois: expedição completa (105 km) | passos 3–4 OK |

---

## Passo 0 — A versão do Unity tem de ser igual ou mais recente

O projeto foi atualizado para **Unity 6000.6.5f1** e os pacotes que pede são
específicos dessa versão:

| Pacote | Versão |
|---|---|
| `com.unity.render-pipelines.universal` | **17.6.0** |
| `com.unity.ugui` | 2.6.0 |
| `com.unity.test-framework` | 1.8.0 |
| `com.unity.inputsystem` | 1.20.0 |
| `com.unity.splines` | 2.9.1 |

**Confirma a versão antes de abrir:**

```powershell
Get-Content ExtractStardustRDD\ProjectSettings\ProjectVersion.txt
Get-ChildItem "C:\Program Files\Unity\Hub\Editor" -Directory | Select-Object -ExpandProperty Name
```

**Compara as duas.**

- **Igual (`6000.6.5f1`)** → perfeito, abre à vontade.
- **Mais recente** (ex.: `6000.7.x`) → abre, mas o Unity vai pedir para atualizar o
  projeto. Aceita; é reversível (o `main` está intacto e o ramo tem 22 commits).
- **Mais ANTIGA** (ex.: `6000.3.x`) → **não abras assim.** O URP 17.6.0 não existe
  nessa versão e o projeto não resolve os pacotes. Instala a 6000.6.5f1 pelo Unity
  Hub → *Installs* → *Install Editor*.

**Porque não deixo o projeto na versão antiga:** o editor do PC do trabalho é o
6000.6.5f1 e foi ele que fez o upgrade. Reverter agora obrigaria a mexer no
`manifest.json` e no `packages-lock.json` à mão, e os shaders foram validados nesta
versão.

**Se algo correr mal ao abrir:** o estado conhecido bom está no `main`, e o ramo tem
22 commits. Tudo reversível com `git checkout main` ou `git checkout 4834964`.

---

## Passo 1 — Instalar o Blender 5.2

O projeto pede **Blender 5.2**. Os scripts usam `bpy` e são executados com
`blender -b --factory-startup -P script.py`.

Transferir de: <https://download.blender.org/release/Blender5.2/>
Ficheiro: `blender-5.2.2-windows-x64.zip` (portátil, não precisa de admin) ou o `.msi`.

Depois de instalar, confirmar:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --version
```

**Se instalares noutro caminho:** o pipeline aceita `-BlenderExe <caminho>` ou a
variável de ambiente `BLENDER_EXE`.

## Passo 2 — Verificar o estado (5 segundos)

```powershell
cd ExtractStardustRDD
powershell -ExecutionPolicy Bypass -File Tools\preflight.ps1
```

**O que deve dizer:** Unity encontrado, Blender encontrado, Python com numpy
encontrado. E vai queixar-se de `Art\Export` ausente — **é normal**, é o passo 3.

**Não avances se o Blender não for encontrado.** Sem ele não há geometria.

Verificações que não precisam do Blender nem do Unity:

```powershell
powershell -ExecutionPolicy Bypass -File Tools\check_compile.ps1   # 9/9 assemblies
python Tools\verifica_sculpt_real.py                               # geometria da pista
```

## Passo 3 — Gerar a geometria do laboratório (~2 min)

```powershell
powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course sandbox
```

Isto corre **Blender → import no Unity → validação**. Os logs ficam em `Logs/`.

**O que deve aparecer:** `Art/Export/sandbox*` com centenas de MB, e
`Assets/RedDust/Generated/` criado.

> ⚠️ **Este passo é obrigatório antes do validador M1.** Verificado: a cena
> `RDD_Sandbox.unity` tem 782 MeshColliders a apontar para malhas geradas pelo
> Blender. Sem elas a nave cai ao vazio e o relatório falha tudo — **não por a
> física estar má, mas por o cenário não existir.** Não tires conclusões antes
> de o passo 3 estar feito.

## Passo 4 — O teste que importa: T4 (wall-ride)

Abre o projeto no Unity (6000.6.5f1) e corre:

**`Red Dust / 3. Validar física (M1)`**

O relatório sai em `Docs/M1_Relatorio_Fisica.md`. **O que interessa é o T4.**

### Contexto: porque é que o T4 está em risco

A erosão 3D nova desloca a parede da pista **até ~22 m na banda da ride line**
(média 1,41 m). Medido em Python com o ruído real, não estimado.

O M1 original passava o T4 com **2,7 s** de wall-ride a 64°. Se a erosão mudou a
geometria da parede, esse teste pode falhar.

### Se o T4 falhar

Há uma escada de soluções, da menos à mais invasiva:

1. **Reduzir a amplitude da erosão** — em `Art/Courses/sandbox.json`, pôr
   `"erosion_m": 40` (em vez dos 70 por omissão) e regerar.
   Escala medida: 26 m → ~9 m de deslocamento, 70 m → ~23 m, 100 m → ~34 m.
2. **Desligar a erosão só para ver a diferença** — `"erosion_m": 0` e regerar.
   Se o T4 passar com 0 e falhar com 70, está confirmada a causa.
3. **Restringir o wall-ride** — reduzir o ângulo exigido no teste, ou limitar o
   wall-ride a zonas onde a erosão é menor (é uma mudança de design, decide tu).

**Não inventar valores de física para fazer o teste passar.** O T4 existe para
medir a nave. Se ele falha, a informação útil é *que* falha e *porquê*.

## Passo 5 — Avaliar o aspeto (decisão tua)

No Unity, com a cena `RDD_MetricsLab` aberta (gerada em `Red Dust / 9. Gerar Metrics
Lab (V2)`), ou com o `sandbox`:

- as **paredes** deixaram de ser tubos lisos? Vê-se alcova, fluting, cornija?
- o **detrito** no pé assenta naturalmente?
- a **cor** tem variação, ou continua a ser "faixas iguais durante quilómetros"?

**Isto não é verificável por software** — é a tua avaliação. A sessão de casa não
consegue julgar se está bonito; consegue mudar parâmetros.

Parâmetros que mexem no aspeto:

| Parâmetro | Onde | Efeito |
|---|---|---|
| `erosion_m` | `Art/Courses/*.json` | amplitude da erosão (0 desliga) |
| `talus_h` | `Art/Courses/*.json` | altura do cone de detrito (0 desliga) |
| `_MacroAmount` | material `Geology.mat` | variação de cor em escala grande (0 desliga) |
| `_MacroAmount` / `RD_MACRO_FBM3` | `RDColour.hlsl` | qualidade/custo do ruído |

### Nota sobre a cena do laboratório

A cena tem **115,6 MB** e as paredes somam ~585 mil vértices. Se abrir devagar,
reduzir a densidade em `MetricsLabBuilder.cs` e regerar:

| `DensityAlong` × `DensityHeight` | Vértices/parede |
|---|---|
| 440 × 220 (atual) | 97 mil |
| 220 × 120 | 27 mil |
| 110 × 60 | 7 mil |

Menos densidade = menos detalhe de erosão. É um compromisso, não um defeito.

## Passo 6 — Medir o fps

O shader novo faz **80 avaliações de ruído por pixel** (a 1920×1080 e 60 fps são
~9,9 G hashes/s). Para comparação, o verniz existente fazia 16 e o bump 32.

Se faltar fps, por ordem:

| Ação | Onde | Efeito |
|---|---|---|
| `RD_MACRO_FBM3=1` | `RDColour.hlsl` | 80 → 48 ruídos/pixel |
| `_NormalScale = 0` | `Geology.mat` | desliga o normal map |
| `RD_MACRO=0` | `RDColour.hlsl` | desliga a variação macro toda |

Mede **antes e depois** de cada mudança, para saberes o que custa o quê.

## Passo 7 — Só depois: a expedição completa

```powershell
powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course red_dust_divide
```

São ~10 min de Blender (105,7 km, 9 setores) mais o import. Depois o build:

```powershell
powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course red_dust_divide -SkipBlender -Build
```

---

## Regras a respeitar (aprendidas à força)

1. **Em deslocamento por normal partilhada, nunca usar máscara binária.** O degrau
   arrasta os vértices vizinhos. Usar sempre ramp. (Custou 3,7 m de deslocamento
   indevido na ride line.)
2. **O ruído do projeto está centrado em ZERO** (`rdd_geology.fbm3` vai de −0,67 a
   +0,69). O `rd_noise` do shader é que é 0..1. Trocar isto anula a erosão.
3. **As sementes de ruído têm de ser INTEIRAS** — o `_hash` rebenta com float.
4. **Não editar ficheiros Python ou `.ps1` com `Set-Content -Encoding UTF8` da
   PowerShell 5.1.** Lê UTF-8 como ANSI e corrompe acentos. Usar a ferramenta de
   edição; scripts de shell ficam em ASCII.
5. **Verificar antes de gerar.** `python Tools\verifica_sculpt_real.py` corre em
   segundos e valida a geometria sem Blender.

## O que reportar de volta ao PC do trabalho

Para o trabalho continuar, são precisos estes dados:

1. Resultado do **T4** (e do resto do M1): passou ou falhou, com os números
2. **fps** medido, e em que qualidade
3. Impressão **visual** das paredes (o software não julga isto)
4. Se o Blender correu sem erros, ou se houve exceções nos logs de `Logs/`

Com isso, o PC do trabalho continua: afinar `erosion_m`, ajustar o talus, ou mexer
no shader conforme o que os números mostrarem.
