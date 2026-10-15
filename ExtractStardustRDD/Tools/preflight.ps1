# Verificacao de arranque: "esta tudo pronto para abrir o jogo?"
#
# Corre isto ANTES de abrir o Unity. Diz o que esta feito, o que falta gerar, e o
# que fazer a seguir. Nao altera nada: so le e reporta.
#
# Uso:  powershell -ExecutionPolicy Bypass -File Tools\preflight.ps1
#
# NOTA: este ficheiro e deliberadamente so ASCII. A Windows PowerShell 5.1 le
# ficheiros .ps1 sem BOM como ANSI, o que corrompe acentos e travessoes e parte o
# parsing. Scripts de shell ficam em ASCII; os comentarios acentuados vao nos .md.

$ErrorActionPreference = 'Continue'
$P = Split-Path -Parent $PSScriptRoot
$script:ok = 0; $script:falta = 0; $script:aviso = 0

function Bom($t)    { Write-Host "  [OK]     $t" -ForegroundColor Green;  $script:ok++ }
function Falta($t)  { Write-Host "  [FALTA]  $t" -ForegroundColor Red;    $script:falta++ }
function Aviso($t)  { Write-Host "  [AVISO]  $t" -ForegroundColor Yellow; $script:aviso++ }
function Titulo($t) { Write-Host ""; Write-Host $t -ForegroundColor Cyan }

Write-Host ""
Write-Host "================================================================"
Write-Host " EXTRACT: STARDUST - verificacao de arranque"
Write-Host "================================================================"

# ---------------------------------------------------------------- ferramentas
Titulo "1. Ferramentas"

$ver = (Select-String -Path (Join-Path $P "ProjectSettings\ProjectVersion.txt") `
        -Pattern 'm_EditorVersion:\s*(\S+)' | Select-Object -First 1).Matches.Groups[1].Value
$hubRoot = if ($env:UNITY_HUB_EDITORS) { $env:UNITY_HUB_EDITORS } else { "C:\Program Files\Unity\Hub\Editor" }
$unity = $null
if ($ver -and (Test-Path (Join-Path $hubRoot "$ver\Editor\Unity.exe"))) {
    $unity = Join-Path $hubRoot "$ver\Editor\Unity.exe"
    Bom "Unity $ver (a versao que o projeto pede)"
} else {
    $cand = Get-ChildItem $hubRoot -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName "Editor\Unity.exe" } | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($cand) {
        $unity = $cand
        # <hub>\<versao>\Editor\Unity.exe : a versao e irma de "Editor"
        $verInstalada = Split-Path (Split-Path (Split-Path $cand -Parent) -Parent) -Leaf
        Aviso "o projeto pede Unity $ver; instalada: $verInstalada"
    } else {
        Falta "Unity nao encontrado (o projeto pede $ver)"
    }
}

$blender = $null
foreach ($c in @($env:BLENDER_EXE, "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")) {
    if ($c -and (Test-Path $c)) { $blender = $c; break }
}
if (-not $blender) {
    $g = Get-Command blender -ErrorAction SilentlyContinue
    if ($g) { $blender = $g.Source }
}
if (-not $blender) {
    $blender = Get-ChildItem "C:\Program Files\Blender Foundation" -Directory -ErrorAction SilentlyContinue |
               Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName "blender.exe" } |
               Where-Object { Test-Path $_ } | Select-Object -First 1
}
if ($blender) { Bom "Blender: $blender" }
else { Falta "Blender nao encontrado (necessario para regenerar a geometria)" }

$py = $null
# Cuidado: no Windows o "python" do PATH pode ser o STUB da Microsoft Store (0 bytes
# reais, so imprime um aviso). Por isso exige-se que `import numpy` funcione para o
# considerar um Python utilizavel.
foreach ($c in @($env:DSH_PYTHON, "python", "py")) {
    if (-not $c) { continue }
    $g = Get-Command $c -ErrorAction SilentlyContinue
    if (-not $g) { continue }
    & $g.Source -c "import numpy" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $py = $g.Source; break }
}
if ($py) {
    $vlinha = (& $py -c "import sys;print(sys.version.split()[0])" 2>&1 | Select-Object -First 1)
    Bom "Python $vlinha com numpy ($py)"
} else {
    Aviso "Python utilizavel com numpy nao encontrado no PATH."
    Write-Host "           Os verificadores offline precisam dele. Caminho do DSH:"
    Write-Host "           `$env:DSH_PYTHON ou .dsh\dsh-runtimes\...\python\python.exe"
}

# ---------------------------------------------------------------- estado do codigo
Titulo "2. Estado do codigo"

$repo = Split-Path $P -Parent
$mudancas = git -C $repo status --short 2>&1
if ($mudancas) {
    Aviso "ha $(($mudancas | Measure-Object).Count) alteracao(oes) nao commitadas"
    $mudancas | Select-Object -First 5 | ForEach-Object { Write-Host "           $_" }
} else {
    Bom "arvore git limpa"
}

$ramo = git -C $repo branch --show-current 2>&1
if ($ramo -eq 'red-dust-divide-v2') { Bom "ramo: $ramo" }
else { Aviso "ramo atual: $ramo (o trabalho esta em red-dust-divide-v2)" }

# ---------------------------------------------------------------- assets gerados
Titulo "3. Assets gerados (o que faz o jogo existir)"

$export = Join-Path $P "Art\Export"
if (Test-Path $export) {
    $f = Get-ChildItem $export -Recurse -File -ErrorAction SilentlyContinue
    $mb = [math]::Round(($f | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    Bom "geometria gerada: $(($f | Measure-Object).Count) ficheiros, $mb MB"
} else {
    Falta "Art\Export ausente - a geometria da pista AINDA NAO FOI GERADA"
}

$gen = Join-Path $P "Assets\RedDust\Generated"
if (Test-Path $gen) { Bom "Assets\RedDust\Generated presente (importado pelo Unity)" }
else { Falta "Assets\RedDust\Generated ausente - falta importar a geometria" }

$lib = Join-Path $P "Library"
if (Test-Path $lib) { Bom "Library do Unity presente (projeto ja importado)" }
else { Aviso "Library ausente - o primeiro import do Unity vai demorar" }

# ---------------------------------------------------------------- cena e build
Titulo "4. Cena e build"

$lab = Join-Path $P "Assets\RedDust\Scenes\RDD_MetricsLab.unity"
if (Test-Path $lab) { Bom "cena do Metrics Lab gerada" }
else { Falta "RDD_MetricsLab.unity ausente - correr no Unity: Red Dust / 9. Gerar Metrics Lab (V2)" }

$builds = Join-Path $repo "Builds_Jogaveis"
$lfs = $false
if (Test-Path $builds) {
    foreach ($f in Get-ChildItem $builds -File -ErrorAction SilentlyContinue) {
        if ($f.Length -lt 1024) { $lfs = $true }
    }
}
if ($lfs) {
    Aviso "os exe em Builds_Jogaveis sao PONTEIROS do Git LFS (133 bytes), nao os jogos."
    Write-Host "           Para os obter: git lfs pull. Mas sao builds ANTIGAS, sem este trabalho."
} elseif (Test-Path $builds) {
    Bom "builds presentes e completas"
}

# ---------------------------------------------------------------- veredicto
Titulo "RESUMO"
Write-Host "  $script:ok verificacoes OK, $script:aviso avisos, $script:falta bloqueios"

if ($script:falta -gt 0) {
    Write-Host ""
    Write-Host "  AINDA NAO e so abrir o jogo. Falta gerar:" -ForegroundColor Yellow
    Write-Host "   1. a geometria da pista (Blender), com erosao e detrito"
    Write-Host "   2. o importe no Unity (CourseImporter)"
    Write-Host "   3. o build do exe"
    Write-Host ""
    Write-Host "  Pista do laboratorio (~2 min), que ja permite ver as paredes novas:" -ForegroundColor Cyan
    Write-Host "   powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course sandbox -Build"
    Write-Host ""
    Write-Host "  Expedicao completa (~10 min + build):" -ForegroundColor Cyan
    Write-Host "   powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course red_dust_divide -Build"
} else {
    Write-Host ""
    Write-Host "  Tudo no sitio. Abre o Unity e corre:" -ForegroundColor Green
    Write-Host "   Red Dust / 3. Validar fisica (M1)   <- o teste T4 e o que importa"
}

Write-Host ""
Write-Host "  Nota: abrir o projeto no Unity NAO gera a geometria nem o exe." -ForegroundColor DarkGray
Write-Host "  O Unity importa o que existe; quem gera e o pipeline." -ForegroundColor DarkGray
Write-Host ""
exit 0
