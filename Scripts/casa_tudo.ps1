# Tudo o que falta fazer no PC com o Unreal, por ordem, sem precisar da IA (Docs/MODOS_DE_JOGO.md, CLAUDE.md):
#   1. compilar o C++ (modos de jogo: solo e contra 15 bots, vidas, kit medico);
#   2. gerar a pista A-B a 3 m (tunel liso, estradas largas) e exporta-la para o Unreal;
#   3. importar no Unreal as pecas da pista e as naves novas;
#   4. montar o mapa Expedition.
# Uso, na pasta do projeto (PowerShell):
#   powershell -ExecutionPolicy Bypass -File Scripts\casa_tudo.ps1
#   ... -SemPista        so compila e importa as naves (o mapa Expedition fica como esta)
#   ... -Metros 5        pista a 5 m (mais rapido, menos memoria)
# Antes: git pull do ramo; C:\rdd\kit, C:\rdd\moldes, C:\rdd\plantas e C:\rdd\strix.fbx feitos (ver CLAUDE.md).
# Se um passo falhar, o script para e diz qual; a mensagem de erro e o que se mostra a IA.
param(
    [string]$UE = "C:\Program Files\Epic Games\UE_5.8",
    [string]$Blender = "blender",
    [string]$Rdd = "C:\rdd",
    [double]$Metros = 3,
    [switch]$SemPista,
    [switch]$SemCompilar
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Project = Join-Path $Root "ExtractingStardust.uproject"
$Editor = Join-Path $UE "Engine\Binaries\Win64\UnrealEditor.exe"
$EditorCmd = Join-Path $UE "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$Ab = "$Rdd\ab"

function Step($Name, $Exe, [string[]]$Arguments) {
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    Write-Host "$Exe $($Arguments -join ' ')"
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "FALHOU: $Name (codigo $LASTEXITCODE)" }
}

Set-Location $Root
if (-not $SemCompilar) {
    Step "1. Compilar o C++" (Join-Path $UE "Engine\Build\BatchFiles\Build.bat") @(
        "ExtractingStardustEditor", "Win64", "Development", "-Project=$Project", "-WaitMutex")
}
if (-not $SemPista) {
    Step "2a. Pista A-B a $Metros m" $Blender @("-b", "-P", "Scripts/sculpt_expedition_ab.py", "--", $Ab, "$Metros", "forunreal",
        "kit=$Rdd\kit", "molds=$Rdd\moldes", "plants=$Rdd\plantas", "ship=$Rdd\strix.fbx")
    Step "2b. Exportar a pista para o Unreal" $Blender @("-b", "-P", "Scripts/export_ab_unreal.py", "--", $Ab)
    $env:EX_WORLD_DIR = "$Ab\ue"
    $env:EX_KIT_DIR = "$Rdd\kit"
    Step "3a. Importar as pecas da pista" $EditorCmd @($Project, "-run=pythonscript", "-script=$Root\Scripts\import_world.py", "-unattended")
}
Step "3b. Importar as naves novas" $EditorCmd @($Project, "-run=pythonscript", "-script=$Root\Scripts\import_test_ships.py", "-unattended")
Step "3c. Importar os modulos das naves" $EditorCmd @($Project, "-run=pythonscript", "-script=$Root\Scripts\import_ship_modules.py", "-unattended")
if (-not $SemPista) {
    Step "4. Montar o mapa Expedition" $Editor @($Project, "-ExecutePythonScript=$Root\Scripts\build_expedition_map.py")
}
Write-Host ""
Write-Host "PRONTO. Para jogar: powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1 -Modo Bots   (ou Solo)" -ForegroundColor Green
