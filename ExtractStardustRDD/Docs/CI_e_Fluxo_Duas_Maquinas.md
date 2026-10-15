# CI e fluxo de duas máquinas

Como o trabalho está dividido entre o PC do trabalho (onde não se pode abrir
Unity nem Blender, por conformidade) e o PC de casa (onde se pode).

**Regra prática:** aqui faz-se tudo o que é texto — código, correções,
validação offline, CI e documentação. Em casa corre-se só o que exige motor:
abrir o Unity, correr o Blender, medir e gerar builds.

> **Estado (2026-10-15): o CI está desligado e não publicado.**
> Decisão: por agora compila-se em casa. O CI compila código, mas não deixa
> jogar, e do trabalho não se pode jogar — logo não trazia vantagem imediata.
> O workflow existe, está pronto, e só corre a pedido (manual). Ver secção 3
> para o ativar quando fizer sentido.

---

## 1. O que corre onde

| Tarefa | Trabalho | Casa | Nuvem (CI, desligado) |
|---|---|---|---|
| Escrever/editar C# | ✅ | ✅ | — |
| Validar compilação dos 8 assemblies | ✅ | ✅ | — |
| Testes de economia (45 701 verificações) | ✅ | ✅ | — |
| Abrir o editor Unity / importar Assets | ❌ | ✅ | ✅ (a ativar) |
| Gerar geometria no Blender | ❌ | ✅ | — |
| Build Windows / APK | ❌ | ✅ | ✅ (a ativar) |
| Medições da Fase 1 (Metrics Lab) | ❌ | ✅ | ✅ (a ativar) |

Nada fica bloqueado: o que não se faz aqui é preparado aqui e corrido em casa
ou na nuvem. Com o CI desligado, **tudo o que precisa de motor corre em casa**;
aqui continua a fazer-se todo o trabalho de texto e validação.

---

## 2. Validação local, sem abrir o Unity

Duas ferramentas que correm em qualquer PC com o editor Unity instalado
(não precisam de licença, GPU, nem de `Library/`):

```powershell
cd ExtractStardustRDD

# Compila os 8 assemblies com o Roslyn do editor
powershell -ExecutionPolicy Bypass -File Tools\check_compile.ps1

# Economia / meta-jogo (puro C#, 45 701 verificações)
powershell -ExecutionPolicy Bypass -File Tools\test_meta.ps1
```

Ambas detetam sozinhas a versão do editor:

1. Lêem `ProjectSettings/ProjectVersion.txt`;
2. Procuram esse editor em `C:\Program Files\Unity\Hub\Editor\<versão>`;
3. Se não existir, usam a versão instalada mais recente e avisam.

Variáveis de ambiente para apontar para outro sítio:

| Variável | Para que serve |
|---|---|
| `UNITY_EDITOR_DATA` | pasta `Editor\Data` do Unity (usada pelas duas ferramentas) |
| `UNITY_HUB_EDITORS` | raiz das versões instaladas, se não for `C:\Program Files\Unity\Hub\Editor` |
| `UNITY_EXE` | `Unity.exe` do pipeline |
| `BLENDER_EXE` | `blender.exe` do pipeline |

Também se pode passar em linha de comando:

```powershell
powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course sandbox `
  -UnityExe "D:\Unity\6000.6.5f1\Editor\Unity.exe" `
  -BlenderExe "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
```

### Validar sem o projeto ter sido aberto

`check_compile.ps1` já não exige `Library\ScriptAssemblies`. Quando essa pasta
não existe, vai buscar as DLLs de pacotes às `BuiltInPackages` do editor e ao
template URP pré-compilado. É o que permite validar código num clone novo.

---

## 3. Ativar o CI (só quando fizer sentido)

**Não é preciso fazer isto agora.** O CI está desligado e não publicado; o jogo
compila em casa sem configuração nenhuma. Esta secção fica para quando o CI
passar a valer a pena.

Só faz sentido ativar quando existir uma destas necessidades:

- querer lançar builds **sem estar em casa**;
- querer build automático a cada `push`;
- a máquina de casa for lenta ao ponto de o build local incomodar.

Ativar são 3 passos:

**1. Pôr os secrets.** Em `github.com/NEWTOWN-BORGES/ExtractStardust` →
**Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Obrigatório | Conteúdo |
|---|---|---|
| `UNITY_LICENSE` | ✅ | conteúdo do ficheiro `C:\ProgramData\Unity\Unity_lic.ulf` |
| `UNITY_EMAIL` | ✅ | email da conta Unity |
| `UNITY_PASSWORD` | ✅ | password da conta Unity |

Para obter o conteúdo do `.ulf` (o `TrimStart` remove o BOM UTF-8):

```powershell
$lic = (Get-Content C:\ProgramData\Unity\Unity_lic.ulf -Raw).TrimStart([char]0xFEFF)
$lic | Set-Clipboard
```

**2. Publicar o ramo** `red-dust-divide-v2`.

**3. Correr** em *Actions → CI → Run workflow*. O build automático em cada
`push` continua desligado; para o ligar, descomentar os gatilhos no `ci.yml`.

> **Aviso de custo:** por omissão a GitHub **cobra** o que passar da quota em vez
> de parar. O plano Free inclui 2 000 minutos/mês e runners Windows gastam o
> dobro. Antes de ligar o build automático, vale a pena pôr um limite de gastos
> em *Settings → Billing → Budgets*.

### Licença Personal (gratuita) — funciona em CI

Documentação oficial do GameCI (*Activation → Personal license*):

> *"Can I use a free Unity license to build my project? **Yes**"*

E sobre portabilidade:

> *"Licenses are not tied to a specific Unity version or platform. You can activate
> the license on any operating system, such as Windows, and use it for builds on
> another platform, like Ubuntu."*

Ou seja, o `.ulf` gerado no Windows serve para os runners `ubuntu-latest`.
**Não** é preciso Plus nem Pro, e **não** se cria `UNITY_SERIAL`.

Se o ficheiro `.ulf` não existir: Unity Hub → Preferences → Licenses → **Add** →
*Get a free personal license*. Mesmo que a licença apareça no Hub, é preciso
clicar em **Add** para o `.ulf` ser gerado.

`UNITY_SERIAL` existe apenas para Plus/Pro (formato `XX-XXXX-XXXX-XXXX-XXXX-XXXX`);
nesse caso não se usa o `.ulf`.

---

## 4. Correr o pipeline em casa

```powershell
cd ExtractStardustRDD

# Só a validação (sem Blender, sem Unity a abrir)
powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -SkipBlender -SkipImport -SkipValidate

# Geologia da pista, import, validação e exe Windows
powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course sandbox -Build

# Expedição completa
powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course red_dust_divide -Build

# Jogo completo (exe + teste de extração com bots + APK)
powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course red_dust_divide `
  -SkipBlender -SkipValidate -Build -Test -Android
```

Requisitos do repositório: **Unity 6000.3.26f1** (com Android Build Support)
e **Blender 5.2**. Se em casa tiveres outras versões, o pipeline deteta-as; para
forçar, usa `-UnityExe` / `-BlenderExe`.

A geometria gerada (FBX, ~1,4 GB) não vai para o repositório: vem de
`Art/Blender/*.py` com sementes fixas, logo é sempre igual.

---

## 5. O CI, em detalhe

`.github/workflows/ci.yml` corre em dois jobs:

- **test** — `game-ci/unity-test-runner@v4`, modo editmode. Tem
  `failIfNoTests: false` porque o projeto ainda não tem assemblies de teste do
  Unity (só `Tests/MetaTests.cs`, que corre fora do editor). Não falha enquanto
  não houver testes.
- **build** — `game-ci/unity-builder@v4`. Manual (`workflow_dispatch`) escolhe
  `StandaloneWindows64` ou `Android`; em push vem Windows por omissão.

Detalhes que evitam falhas:

- `projectPath: ExtractStardustRDD` — o projeto **não** está na raiz do repo.
- Checkout **sem LFS**: os zips/apk em `Builds_Jogaveis/` não entram no build.
- Cache da `Library/` com chave por versão + hash de `Assets/Packages/ProjectSettings`.
- Versão fixada por `env.UNITY_VERSION: 6000.6.5f1`.

Imagens verificadas no Docker Hub (`unityci/editor`):

| Tag | Tamanho | Uso |
|---|---|---|
| `ubuntu-6000.6.5f1-windows-mono-3.2.2` | 5,7 GB | build Windows |
| `ubuntu-6000.6.5f1-android-3.2.2` | 8,1 GB | build APK |
| `windows-6000.6.5f1-base-3.2.2` | 9,0 GB | base para builds pesados |

---

## 6. Estado do repositório

Ramo de trabalho: **`red-dust-divide-v2`** (`main` fica intacto).

Já feito:

- fix `GetInstanceID()` → `GetEntityId()` (a Unity 6000.6 transformou-o em erro
  de compilação e partia 6 assemblies em cascata);
- as três ferramentas detetam o editor e correm sem o abrir;
- workflow de CI.

Por fazer (Fase 1 da V2 — ver `RDD_V2_Plano_Fase0.md`, secção I):

| # | Tarefa | Onde |
|---|---|---|
| 1 | Ramo e esqueleto da V2 | ✅ feito |
| 2 | Ler o GDD e escrever `RDD_V2_Decisoes.md` | trabalho |
| 3 | Cena **Metrics Lab** (reta 4 km, R 35–500 m, banks, half-pipes, saltos) | casa (editor) |
| 4 | Executor batch 5 chassis × CSV | escrita aqui, corrida em casa |
| 5 | Medir com 12–16 bots | casa |
| 6 | Precisão a 40 km da origem | casa |
| 7 | Calcular comprimento p/ 20 min | trabalho (a partir dos CSVs) |
| 8 | `RDD_V2_Metricas.md` + parar para aprovação | trabalho |

O Blender **quase não** entra na Fase 1: a secção E do plano manda gerar as
superfícies íngremes por varrimento de secção em C#, para não esperar 15 min por
iteração. O Blender fica para as peças-herói (Fase 2+).
