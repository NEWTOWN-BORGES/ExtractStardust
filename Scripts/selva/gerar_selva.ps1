# Mapa 02 Selva Esmeralda: gera os 10 setores no Blender (relevo .r16, plantas .json, cena .blend; com -Fotos tambem
# as fotos), um a um, a partir de Scripts/selva/selva_plano.json. Docs/PISTA_SELVA_ESMERALDA.md, seccao 6.
#   powershell -ExecutionPolicy Bypass -File Scripts\selva\gerar_selva.ps1 [-Saida C:\rdd\selva] [-Res 3] [-Fotos] [-Setores 1,2,3]
param([string]$Saida = "C:\rdd\selva", [int]$Res = 3, [switch]$Fotos, [int[]]$Setores = (1..10), [string]$Blender = "blender")
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $raiz
# o script usa scipy: instala-o uma vez no Python do proprio Blender
# --python-use-system-env: pip puts scipy in the user site-packages when Blender's own folder is read-only (2026-11-02),
# and Blender only reads that folder with this flag.
& $Blender --python-use-system-env -b --python-expr "import importlib.util, subprocess, sys; importlib.util.find_spec('scipy') or subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'scipy'])"
foreach ($n in $Setores) {
    $s = "S$n"
    $out = Join-Path $Saida $s
    New-Item -ItemType Directory -Force -Path $out | Out-Null
    $extra = @("res=$Res")
    if (-not $Fotos) { $extra += "noshots" } else { $extra += "size=1600x900"; $extra += "samples=40" }
    Write-Host "== $s -> $out"
    & $Blender --python-use-system-env -b -P "Scripts/selva/sculpt_selva.py" -- $out $s @extra
    # Blender exits 0 even when the script fails: the files are the proof
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $out "selva_${s}.json"))) { throw "falhou $s" }
}
Write-Host "SELVA: setores gerados em $Saida (selva_S<n>_height.r16 + .json, selva_S<n>_props.json, selva_S<n>.blend)"
