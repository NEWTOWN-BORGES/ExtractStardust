# Verifica a compilacao dos scripts SEM abrir o Unity (nao precisa de licenca):
# compila cada assembly (asmdef) pela ordem das dependencias com o Roslyn do editor e as DLLs do motor/pacotes.
# Uso:  powershell -ExecutionPolicy Bypass -File Tools\check_compile.ps1
$ErrorActionPreference = "Stop"
$P = Split-Path -Parent $PSScriptRoot

# Descobrir a versao do editor a partir do projeto (portavel entre maquinas).
$editor = $env:UNITY_EDITOR_DATA
if (-not $editor) {
    $ver = (Select-String -Path (Join-Path $P "ProjectSettings\ProjectVersion.txt") -Pattern 'm_EditorVersion:\s*(\S+)' |
            Select-Object -First 1).Matches.Groups[1].Value
    $root = $env:UNITY_HUB_EDITORS
    if (-not $root) { $root = "C:\Program Files\Unity\Hub\Editor" }
    if ($ver -and (Test-Path (Join-Path $root "$ver\Editor\Data"))) {
        $editor = Join-Path $root "$ver\Editor\Data"
    } else {
        # fallback: a versao instalada mais recente
        $cand = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
        if ($cand) { $editor = Join-Path $cand.FullName "Editor\Data" }
    }
    if ($ver -and $editor -notlike "*$ver*") {
        Write-Host "AVISO: o projeto pede Unity $ver mas vai usar $editor"
    }
}
if (-not (Test-Path $editor)) { Write-Host "Editor Unity nao encontrado (definir UNITY_EDITOR_DATA)"; exit 2 }

# Roslyn: o caminho mudou entre versoes do editor (DotNetSdkRoslyn vs DotNetSdk\sdk\<v>\Roslyn).
$csc = Join-Path $editor "DotNetSdkRoslyn\csc.dll"
if (-not (Test-Path $csc)) {
    $c = Get-ChildItem (Join-Path $editor "DotNetSdk") -Recurse -Filter csc.dll -ErrorAction SilentlyContinue |
         Sort-Object FullName | Select-Object -Last 1
    if ($c) { $csc = $c.FullName }
}
$dotnet = Join-Path $editor "NetCoreRuntime\dotnet.exe"
if (-not (Test-Path $dotnet)) { $dotnet = "dotnet" }
if (-not (Test-Path $csc)) { Write-Host "csc.dll (Roslyn) nao encontrado em $editor"; exit 2 }
Write-Host "Editor: $editor"
Write-Host "Roslyn: $csc"
$out = Join-Path $P "Temp\CompileCheck"
New-Item -ItemType Directory -Force $out | Out-Null

$engine = Get-ChildItem (Join-Path $editor "Managed\UnityEngine") -Filter "UnityEngine*.dll" | ForEach-Object { $_.FullName }
$editorDlls = Get-ChildItem (Join-Path $editor "Managed\UnityEngine") -Filter "UnityEditor*.dll" | ForEach-Object { $_.FullName }
# DLLs de pacotes (URP, Input System, Splines, TMP, uGUI).
# 1) Library\ScriptAssemblies, se o projeto ja foi aberto no editor.
# 2) Caso contrario, BuiltInPackages do editor + o template URP (pre-compilado).
$pkgDirs = @()
$sa = Join-Path $P "Library\ScriptAssemblies"
if (Test-Path $sa) { $pkgDirs += $sa }
$pkgDirs += (Join-Path $editor "Resources\PackageManager\BuiltInPackages")
Get-ChildItem (Join-Path $editor "Resources\PackageManager\ProjectTemplates\libcache") -Directory -ErrorAction SilentlyContinue |
    ForEach-Object { $pkgDirs += (Join-Path $_.FullName "ScriptAssemblies") }
$pkgDirs = $pkgDirs | Where-Object { Test-Path $_ }

# Apenas DLLs de topo de cada pasta: com -Recurse entram plugins nativos
# (ex.: UnityDenoisingPlugin.dll) que o Roslyn rejeita por nao terem metadata gerida,
# e a linha de comando fica longa demais para o Windows.
$pkgAll = $pkgDirs | ForEach-Object { Get-ChildItem $_ -Filter "Unity*.dll" -ErrorAction SilentlyContinue } |
          Sort-Object FullName -Unique
$packages       = $pkgAll | Where-Object { $_.Name -notmatch "Test|DocCodeSamples" -and $_.Name -notmatch "\.Editor\." } | ForEach-Object { $_.FullName }
$packagesEditor = $pkgAll | Where-Object { $_.Name -notmatch "Test|DocCodeSamples" } | ForEach-Object { $_.FullName }
if ($pkgDirs.Count -eq 0) { Write-Host "AVISO: sem DLLs de pacotes; assemblies que usam URP/InputSystem vao falhar" }
$netstd = Join-Path $editor "NetStandard\ref\2.1.0\netstandard.dll"
$defines = "UNITY_6000_3_OR_NEWER;UNITY_2023_1_OR_NEWER;UNITY_STANDALONE_WIN;UNITY_STANDALONE;ENABLE_INPUT_SYSTEM"

$asms = @(
    @{ n = "RedDust.Core"; d = "Assets\RedDust\Runtime\Core"; r = @() },
    @{ n = "RedDust.Track"; d = "Assets\RedDust\Runtime\Track"; r = @("RedDust.Core") },
    @{ n = "RedDust.Vehicle"; d = "Assets\RedDust\Runtime\Vehicle"; r = @("RedDust.Core", "RedDust.Track") },
    @{ n = "RedDust.AI"; d = "Assets\RedDust\Runtime\AI"; r = @("RedDust.Core", "RedDust.Track", "RedDust.Vehicle") },
    @{ n = "RedDust.Presentation"; d = "Assets\RedDust\Runtime\Presentation"; r = @("RedDust.Core", "RedDust.Track", "RedDust.Vehicle", "RedDust.AI") },
    @{ n = "RedDust.Meta"; d = "Assets\RedDust\Runtime\Meta"; r = @(); pure = $true },
    @{ n = "RedDust.Game"; d = "Assets\RedDust\Runtime\Game"; r = @("RedDust.Core", "RedDust.Track", "RedDust.Vehicle", "RedDust.AI", "RedDust.Presentation", "RedDust.Meta") },
    @{ n = "RedDust.Editor"; d = "Assets\RedDust\Editor"; r = @("RedDust.Core", "RedDust.Track", "RedDust.Vehicle", "RedDust.AI", "RedDust.Presentation", "RedDust.Meta", "RedDust.Game"); editor = $true }
)
$failed = 0
foreach ($a in $asms) {
    $src = Get-ChildItem (Join-Path $P $a.d) -Recurse -Filter *.cs | ForEach-Object { $_.FullName }
    $refs = @("-r:$netstd")
    if (-not $a.pure) { $refs += $engine | ForEach-Object { "-r:$_" }; $refs += $packages | ForEach-Object { "-r:$_" } }
    if ($a.editor) { $refs += $editorDlls | ForEach-Object { "-r:$_" }; $refs += $packagesEditor | ForEach-Object { "-r:$_" } }
    $refs += $a.r | ForEach-Object { "-r:" + (Join-Path $out "$_.dll") }
    $def = $defines
    if ($a.editor) { $def += ";UNITY_EDITOR;UNITY_EDITOR_WIN" }
    # Todas as referencias vao num ficheiro de resposta: a linha de comando do
    # Windows tem limite (~32k caracteres) e o assembly Editor estourava-o.
    function To-Rsp([string[]]$paths) { $paths | Where-Object { $_ } | ForEach-Object { '"-r:' + $_ + '"' } }
    $rsp = @(To-Rsp $($refs -replace '^-r:', ''))
    $rspFile = Join-Path $out "$($a.n).rsp"
    [System.IO.File]::WriteAllLines($rspFile, $rsp, (New-Object System.Text.UTF8Encoding($false)))
    $res = & $dotnet $csc -nologo -noconfig -nostdlib -langversion:9 -nullable:disable `
        -nowarn:CS1701,CS1702,CS0618 -target:library "-define:$def" `
        "-out:$(Join-Path $out ($a.n + '.dll'))" "@$rspFile" $src 2>&1
    $errs = $res | Where-Object { $_ -match "error CS" }
    if ($LASTEXITCODE -ne 0) { $failed++; Write-Host "FALHA $($a.n)"; $errs | Select-Object -First 40 | ForEach-Object { Write-Host "  $_" } }
    else { $warn = ($res | Where-Object { $_ -match "warning CS" }).Count; Write-Host "OK    $($a.n) ($($src.Count) ficheiros, $warn avisos)" }
}
if ($failed -gt 0) { exit 1 } else { exit 0 }
