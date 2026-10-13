# EXTRACT: STARDUST — RED DUST DIVIDE · pipeline do laboratório de física (M1)
# Uso:  powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 [-SkipBlender] [-SkipValidate] [-Build]
param([switch]$SkipBlender, [switch]$SkipValidate, [switch]$Build)
$ErrorActionPreference = "Continue"
$P = Split-Path -Parent $PSScriptRoot
$unity = "C:\Program Files\Unity\Hub\Editor\6000.3.26f1\Editor\Unity.exe"
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$logs = Join-Path $P "Logs"
New-Item -ItemType Directory -Force $logs | Out-Null

function Step($name, $exe, $argList, $log, $pattern) {
  $t = Get-Date
  if ($argList -contains "-logFile") { & $exe @argList | Out-Null } else { & $exe @argList *> $log }
  $code = $LASTEXITCODE
  Write-Host ("{0}: código {1} · {2}s" -f $name, $code, [int]((Get-Date) - $t).TotalSeconds)
  Select-String -Path $log -Pattern $pattern | Select-Object -First 40 | ForEach-Object { Write-Host ("  " + $_.Line) }
  return $code
}

if (-not $SkipBlender) {
  $null = Step "Blender (geologia)" $blender @("-b", "--factory-startup", "-P", "$P\Art\Blender\rdd_build_route.py", "--", "$P\Art\Courses\sandbox.json", "$P\Art\Export\sandbox") "$logs\blender_sandbox.log" "relat|Error|Traceback"
}
$null = Step "Unity (importar + cena)" $unity @("-batchmode", "-nographics", "-projectPath", $P, "-executeMethod", "RedDust.EditorTools.CourseImporter.ImportSandbox", "-logFile", "$logs\unity_import.log") "$logs\unity_import.log" "error CS|\[RDD\]|Exception:"
if (-not $SkipValidate) {
  $null = Step "Unity (validação M1)" $unity @("-batchmode", "-nographics", "-projectPath", $P, "-executeMethod", "RedDust.EditorTools.SandboxValidation.Run", "-logFile", "$logs\unity_validate.log") "$logs\unity_validate.log" "\[RDD M1\]|error CS|Exception"
}
if ($Build) {
  $null = Step "Unity (build Windows)" $unity @("-batchmode", "-projectPath", $P, "-buildTarget", "Win64", "-executeMethod", "RedDust.EditorTools.BuildTools.BuildWindows", "-logFile", "$logs\unity_build.log") "$logs\unity_build.log" "error CS|\[RDD\]|error:"
}
