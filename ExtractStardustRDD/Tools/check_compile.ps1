# Verifica a compilacao dos scripts SEM abrir o Unity (nao precisa de licenca):
# compila cada assembly (asmdef) pela ordem das dependencias com o Roslyn do editor e as DLLs do motor/pacotes.
# Uso:  powershell -ExecutionPolicy Bypass -File Tools\check_compile.ps1
$ErrorActionPreference = "Stop"
$P = Split-Path -Parent $PSScriptRoot
$editor = "C:\Program Files\Unity\Hub\Editor\6000.3.26f1\Editor\Data"
$dotnet = Join-Path $editor "NetCoreRuntime\dotnet.exe"
$csc = Join-Path $editor "DotNetSdkRoslyn\csc.dll"
$out = Join-Path $P "Temp\CompileCheck"
New-Item -ItemType Directory -Force $out | Out-Null

$engine = Get-ChildItem (Join-Path $editor "Managed\UnityEngine") -Filter "UnityEngine*.dll" | ForEach-Object { $_.FullName }
$editorDlls = Get-ChildItem (Join-Path $editor "Managed\UnityEngine") -Filter "UnityEditor*.dll" | ForEach-Object { $_.FullName }
$packages = Get-ChildItem (Join-Path $P "Library\ScriptAssemblies") -Filter "Unity*.dll" | Where-Object { $_.Name -notmatch "Test|DocCodeSamples|Editor" } | ForEach-Object { $_.FullName }
$packagesEditor = Get-ChildItem (Join-Path $P "Library\ScriptAssemblies") -Filter "Unity*.dll" | Where-Object { $_.Name -notmatch "Test|DocCodeSamples" } | ForEach-Object { $_.FullName }
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
    $res = & $dotnet $csc -nologo -noconfig -nostdlib -langversion:9 -nullable:disable -nowarn:CS1701,CS1702,CS0618 -target:library "-define:$def" "-out:$(Join-Path $out ($a.n + '.dll'))" ($refs | Sort-Object -Unique) $src 2>&1
    $errs = $res | Where-Object { $_ -match "error CS" }
    if ($LASTEXITCODE -ne 0) { $failed++; Write-Host "FALHA $($a.n)"; $errs | Select-Object -First 40 | ForEach-Object { Write-Host "  $_" } }
    else { $warn = ($res | Where-Object { $_ -match "warning CS" }).Count; Write-Host "OK    $($a.n) ($($src.Count) ficheiros, $warn avisos)" }
}
if ($failed -gt 0) { exit 1 } else { exit 0 }
