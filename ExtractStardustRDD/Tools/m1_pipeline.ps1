# EXTRACT: STARDUST - RED DUST DIVIDE - pipeline das pistas (Blender -> Unity -> validacao -> build)
# Uso:  powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 [-Course sandbox|red_dust_divide] [-SkipBlender] [-SkipImport] [-SkipValidate] [-Build] [-Android] [-Test]
#   -Build  exe Windows (todas as pistas)   -Android  APK (laboratorio)   -Test  extracao automatica com bots no exe
# Jogo completo:  powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 -Course red_dust_divide -SkipBlender -SkipValidate -Build -Test -Android
param([string]$Course = "sandbox", [string]$BuildDir = "Builds\Windows", [switch]$SkipBlender, [switch]$SkipImport, [switch]$SkipValidate, [switch]$Build, [switch]$Android, [switch]$Test,
      [string]$UnityExe, [string]$BlenderExe)
$ErrorActionPreference = "Continue"
$P = Split-Path -Parent $PSScriptRoot

# --- descoberta do Unity (portavel entre maquinas) ---
function Find-Unity {
    if ($UnityExe) { if (Test-Path $UnityExe) { return $UnityExe } else { Write-Host "UnityExe indicado nao existe: $UnityExe" } }
    if ($env:UNITY_EXE -and (Test-Path $env:UNITY_EXE)) { return $env:UNITY_EXE }
    $ver = (Select-String -Path (Join-Path $P "ProjectSettings\ProjectVersion.txt") -Pattern 'm_EditorVersion:\s*(\S+)' |
            Select-Object -First 1).Matches.Groups[1].Value
    $root = if ($env:UNITY_HUB_EDITORS) { $env:UNITY_HUB_EDITORS } else { "C:\Program Files\Unity\Hub\Editor" }
    if ($ver) { $p = Join-Path $root "$ver\Editor\Unity.exe"; if (Test-Path $p) { return $p } }
    $cand = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName "Editor\Unity.exe" } | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($cand) { Write-Host "AVISO: o projeto pede Unity $ver; a usar $cand"; return $cand }
    return $null
}

# --- descoberta do Blender (portavel entre maquinas) ---
function Find-Blender {
    if ($BlenderExe) { if (Test-Path $BlenderExe) { return $BlenderExe } else { Write-Host "BlenderExe indicado nao existe: $BlenderExe" } }
    if ($env:BLENDER_EXE -and (Test-Path $env:BLENDER_EXE)) { return $env:BLENDER_EXE }
    $cmd = Get-Command blender -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $bases = @("C:\Program Files\Blender Foundation", "$env:LOCALAPPDATA\Programs\Blender Foundation",
               "C:\Program Files\Blender Foundation\Blender", "D:\Program Files\Blender Foundation")
    foreach ($b in $bases) {
        if (Test-Path $b) {
            $p = Get-ChildItem $b -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending |
                 ForEach-Object { Join-Path $_.FullName "blender.exe" } | Where-Object { Test-Path $_ } | Select-Object -First 1
            if ($p) { return $p }
            $direct = Join-Path $b "blender.exe"
            if (Test-Path $direct) { return $direct }
        }
    }
    return $null
}

$unity = Find-Unity
$blender = Find-Blender
if (-not $SkipImport -or -not $SkipValidate -or $Build -or $Android) {
    if (-not $unity) { Write-Host "Unity nao encontrado. Instalar o editor ou usar -UnityExe / UNITY_EXE."; exit 2 }
    Write-Host "Unity:   $unity"
}
if (-not $SkipBlender) {
    if (-not $blender) { Write-Host "Blender nao encontrado. Instalar o Blender ou usar -BlenderExe / BLENDER_EXE."; exit 2 }
    Write-Host "Blender: $blender"
}
$logs = Join-Path $P "Logs"
New-Item -ItemType Directory -Force $logs | Out-Null

function Step($name, $exe, $argList, $log, $pattern) {
  $t = Get-Date
  if ($argList -contains "-logFile") { & $exe @argList | Out-Null } else { & $exe @argList *> $log }
  $code = $LASTEXITCODE
  Write-Host ("{0}: codigo {1} - {2}s" -f $name, $code, [int]((Get-Date) - $t).TotalSeconds)
  Select-String -Path $log -Pattern $pattern | Select-Object -First 40 | ForEach-Object { Write-Host ("  " + $_.Line) }
  return $code
}

if (-not $SkipBlender) {
  $null = Step "Blender (geologia $Course)" $blender @("-b", "--factory-startup", "-P", "$P\Art\Blender\rdd_build_route.py", "--", "$P\Art\Courses\$Course.json", "$P\Art\Export\$Course") "$logs\blender_$Course.log" "relat|Error|Traceback"
}
if (-not $SkipImport) {
  $null = Step "Unity (importar + cena $Course)" $unity @("-batchmode", "-nographics", "-projectPath", $P, "-executeMethod", "RedDust.EditorTools.CourseImporter.ImportCourse", "-course", $Course, "-logFile", "$logs\unity_import_$Course.log") "$logs\unity_import_$Course.log" "error CS|\[RDD\]|Exception:"
}
if (-not $SkipValidate) {
  $null = Step "Unity (validacao $Course)" $unity @("-batchmode", "-nographics", "-projectPath", $P, "-executeMethod", "RedDust.EditorTools.SandboxValidation.Run", "-course", $Course, "-logFile", "$logs\unity_validate_$Course.log") "$logs\unity_validate_$Course.log" "\[RDD M1\]|error CS|Exception"
}
if ($Build) {
  $null = Step "Unity (build Windows)" $unity @("-batchmode", "-projectPath", $P, "-buildTarget", "Win64", "-executeMethod", "RedDust.EditorTools.BuildTools.BuildWindows", "-buildDir", $BuildDir, "-logFile", "$logs\unity_build.log") "$logs\unity_build.log" "error CS|\[RDD\]|error:"
}
if ($Test) {
  $exe = Join-Path $P "$BuildDir\RedDustDivide.exe"
  $null = Step "Teste extracao (exe, laboratorio, 7 bots)" $exe @("-batchmode", "-nographics", "-pista", "sandbox", "-rddextract", "-bots", "7", "-timescale", "3", "-logFile", "$logs\extract_test.log") "$logs\extract_test.log" "\[RDD extract\]|^  [ 0-9]|Pool:|Jogador:|Exception"
}
if ($Android) {
  $null = Step "Unity (build Android)" $unity @("-batchmode", "-projectPath", $P, "-buildTarget", "Android", "-executeMethod", "RedDust.EditorTools.BuildTools.BuildAndroid", "-logFile", "$logs\unity_build_android.log") "$logs\unity_build_android.log" "error CS|\[RDD\]|error:"
}
