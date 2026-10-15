# Testes da economia/meta-jogo (RedDust.Meta) SEM Unity: compila com o Roslyn do editor e corre no .NET instalado.
# Uso:  powershell -ExecutionPolicy Bypass -File Tools\test_meta.ps1
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
        $cand = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
        if ($cand) { $editor = Join-Path $cand.FullName "Editor\Data" }
    }
}
if (-not (Test-Path $editor)) { Write-Host "Editor Unity nao encontrado (definir UNITY_EDITOR_DATA)"; exit 2 }

$dotnetUnity = Join-Path $editor "NetCoreRuntime\dotnet.exe"
$csc = Join-Path $editor "DotNetSdkRoslyn\csc.dll"
if (-not (Test-Path $csc)) {
    $c = Get-ChildItem (Join-Path $editor "DotNetSdk") -Recurse -Filter csc.dll -ErrorAction SilentlyContinue |
         Sort-Object FullName | Select-Object -Last 1
    if ($c) { $csc = $c.FullName }
}
$fw = Get-ChildItem "C:\Program Files\dotnet\shared\Microsoft.NETCore.App" -ErrorAction SilentlyContinue |
      Sort-Object Name | Select-Object -Last 1
if (-not $fw) { $fw = Get-ChildItem (Join-Path $editor "NetCoreRuntime\shared\Microsoft.NETCore.App") | Sort-Object Name | Select-Object -Last 1 }
$out = Join-Path $P "Temp\MetaTests"
New-Item -ItemType Directory -Force $out | Out-Null

$refs = @("System.Private.CoreLib", "System.Runtime", "System.Collections", "System.Linq", "System.Console", "netstandard") | ForEach-Object { "-r:" + (Join-Path $fw.FullName "$_.dll") }
$src = @(Get-ChildItem (Join-Path $P "Assets\RedDust\Runtime\Meta") -Filter *.cs | ForEach-Object { $_.FullName }) + (Join-Path $P "Tests\MetaTests.cs")
& $dotnetUnity $csc -nologo -nostdlib -noconfig -langversion:9 -nullable:disable -target:exe "-out:$out\MetaTests.dll" $refs $src
if ($LASTEXITCODE -ne 0) { Write-Host "COMPILACAO FALHOU"; exit 1 }
$ver = $fw.Name
Set-Content -Encoding ascii (Join-Path $out "MetaTests.runtimeconfig.json") "{ `"runtimeOptions`": { `"tfm`": `"net8.0`", `"framework`": { `"name`": `"Microsoft.NETCore.App`", `"version`": `"$ver`" } } }"
& "C:\Program Files\dotnet\dotnet.exe" (Join-Path $out "MetaTests.dll")
exit $LASTEXITCODE
