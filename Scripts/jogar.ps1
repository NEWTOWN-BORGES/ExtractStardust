# Abre o jogo no mapa Expedition (pista A-B) num dos modos (Docs/MODOS_DE_JOGO.md):
#   powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1 -Modo Solo
#   powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1 -Modo Bots
#   powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1 -Modo Teste   (16 naves sozinhas, sai no fim; o log
#                                                                             Saved\Logs tem as linhas EXRACE)
#   -Modo Livre: voo livre, sem vidas nem corrida (como antes). Sem -Modo: o menu do jogo (Solo / Bots / Livre).
param(
    [ValidateSet("Menu", "Solo", "Bots", "Teste", "Livre")][string]$Modo = "Menu",
    [string]$UE = "C:\Program Files\Epic Games\UE_5.8"
)
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Project = Join-Path $Root "ExtractingStardust.uproject"
$Editor = Join-Path $UE "Engine\Binaries\Win64\UnrealEditor.exe"
$Arguments = @($Project, "/Game/Maps/Expedition", "-game", "-windowed", "-ResX=1600", "-ResY=900", "-log")
switch ($Modo) {
    "Solo" { $Arguments += "-EXMode=Solo" }
    "Bots" { $Arguments += "-EXMode=Bots" }
    "Teste" { $Arguments += @("-EXMode=Bots", "-EXRaceTest") }
    "Livre" { $Arguments += "-EXNoMenu" }
}
& $Editor @Arguments
