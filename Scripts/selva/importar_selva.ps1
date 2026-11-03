# Mapa 02 Selva Esmeralda no Unreal (depois de gerar_selva.ps1): o kit das plantas e o mundo para o Unreal (Blender),
# a importacao para /Game/Selva e o mapa /Game/Maps/Selva. Docs/PISTA_SELVA_ESMERALDA.md, seccao 6.
#   powershell -ExecutionPolicy Bypass -File Scripts\selva\importar_selva.ps1 [-Selva C:\rdd\selva] [-Blender <blender.exe>] [-SemCompilar]
# O passo 0 compila o editor: a montagem do mapa (EXDesertBuilder) esta no C++ (agua sem colisao, 2026-11-02).
param([string]$Selva = "C:\rdd\selva", [string]$UE = "C:\Program Files\Epic Games\UE_5.8", [string]$Blender = "blender", [switch]$SemCompilar)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$RootFwd = $Root -replace '\\', '/'
$Project = Join-Path $Root "ExtractingStardust.uproject"
$SelvaFwd = $Selva -replace '\\', '/'
Set-Location $Root
function Step($Name, $Exe, $Arguments, $Proof) {
    Write-Host "=== $Name ==="
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0 -or ($Proof -and -not (Test-Path $Proof))) { throw "FALHOU: $Name (codigo $LASTEXITCODE)" }
}
if (-not $SemCompilar) {
    Step "0. Compilar o editor (C++)" (Join-Path $UE "Engine\Build\BatchFiles\Build.bat") @("ExtractingStardustEditor", "Win64", "Development", "-Project=$Project", "-WaitMutex") $null
}
Step "1. Kit das plantas (Blender)" $Blender @("--python-use-system-env", "-b", "-P", "Scripts/selva/export_selva_kit.py", "--", "$SelvaFwd/kit") "$Selva\kit\SM_Selva_kapok.fbx"
Step "2. Mundo para o Unreal (Blender)" $Blender @("--python-use-system-env", "-b", "-P", "Scripts/selva/export_selva_unreal.py", "--", $SelvaFwd) "$Selva\ue\props.json"
$env:EX_SELVA_DIR = $SelvaFwd
Step "3. Importar para /Game/Selva" (Join-Path $UE "Engine\Binaries\Win64\UnrealEditor-Cmd.exe") @($Project, "-run=pythonscript", "-script=$RootFwd/Scripts/selva/import_selva.py", "-unattended") $null
$env:EX_WORLD_DIR = "$SelvaFwd/ue"
Write-Host "=== 4. Montar o mapa Selva ==="
$editor = Start-Process -FilePath (Join-Path $UE "Engine\Binaries\Win64\UnrealEditor.exe") -ArgumentList "`"$Project`"", "`"-ExecutePythonScript=$RootFwd/Scripts/selva/build_selva_map.py`"" -PassThru   # quoted: the path has a space
$editor.WaitForExit()
if (-not (Test-Path (Join-Path $Root "Content\Maps\Selva.umap"))) { throw "FALHOU: 4. Montar o mapa Selva" }
Write-Host "SELVA PRONTA: jogar com  ExtractingStardust.exe /Game/Maps/Selva -EXMode=Bots"
