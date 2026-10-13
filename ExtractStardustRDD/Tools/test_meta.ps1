# Testes da economia/meta-jogo (RedDust.Meta) SEM Unity: compila com o Roslyn do editor e corre no .NET instalado.
# Uso:  powershell -ExecutionPolicy Bypass -File Tools\test_meta.ps1
$ErrorActionPreference = "Stop"
$P = Split-Path -Parent $PSScriptRoot
$editor = "C:\Program Files\Unity\Hub\Editor\6000.3.26f1\Editor\Data"
$dotnetUnity = Join-Path $editor "NetCoreRuntime\dotnet.exe"
$csc = Join-Path $editor "DotNetSdkRoslyn\csc.dll"
$fw = Get-ChildItem "C:\Program Files\dotnet\shared\Microsoft.NETCore.App" | Sort-Object Name | Select-Object -Last 1
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
