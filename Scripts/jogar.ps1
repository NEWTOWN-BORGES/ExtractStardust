# Abre o jogo no mapa Expedition (pista A-B) num dos modos (Docs/MODOS_DE_JOGO.md):
#   powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1 -Modo Solo
#   powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1 -Modo Bots
#   powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1 -Modo Hangar
#   powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1 -Modo Teste   (16 naves sozinhas, sai no fim; o log
#                                                                             Saved\Logs tem as linhas EXRACE)
#   powershell -ExecutionPolicy Bypass -File Scripts\jogar.ps1 -Modo Inspecao   (a nave corre a pista toda sozinha e
#                                                    escreve os problemas e fotos em Saved\Inspect\relatorio.txt)
#   -Modo Livre: voo livre, sem vidas nem corrida. Sem -Modo: o menu do jogo (Solo / Bots / Livre / Hangar).
param(
    [ValidateSet("Menu", "Solo", "Bots", "Teste", "Inspecao", "Livre", "Hangar")][string]$Modo = "Menu",
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
    "Inspecao" { $Arguments += @("-EXMode=Solo", "-EXInspect") }   # a nave corre a pista sozinha; relatorio em Saved\Inspect\relatorio.txt
    "Livre" { $Arguments += "-EXNoMenu" }
    "Hangar" { $Arguments += "-EXMode=Hangar" }
}
& $Editor @Arguments
