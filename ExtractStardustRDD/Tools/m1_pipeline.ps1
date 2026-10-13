# EXTRACT: STARDUST - RED DUST DIVIDE - pipeline das pistas (Blender -> Unity -> validacao -> build)
# Uso:  powershell -ExecutionPolicy Bypass -File Tools\m1_pipeline.ps1 [-Course sandbox|red_dust_divide] [-SkipBlender] [-SkipValidate] [-Build]
param([string]$Course = "sandbox", [switch]$SkipBlender, [switch]$SkipValidate, [switch]$Build)
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
  Write-Host ("{0}: codigo {1} - {2}s" -f $name, $code, [int]((Get-Date) - $t).TotalSeconds)
  Select-String -Path $log -Pattern $pattern | Select-Object -First 40 | ForEach-Object { Write-Host ("  " + $_.Line) }
  return $code
}

if (-not $SkipBlender) {
  $null = Step "Blender (geologia $Course)" $blender @("-b", "--factory-startup", "-P", "$P\Art\Blender\rdd_build_route.py", "--", "$P\Art\Courses\$Course.json", "$P\Art\Export\$Course") "$logs\blender_$Course.log" "relat|Error|Traceback"
}
$null = Step "Unity (importar + cena $Course)" $unity @("-batchmode", "-nographics", "-projectPath", $P, "-executeMethod", "RedDust.EditorTools.CourseImporter.ImportCourse", "-course", $Course, "-logFile", "$logs\unity_import_$Course.log") "$logs\unity_import_$Course.log" "error CS|\[RDD\]|Exception:"
if (-not $SkipValidate) {
  $null = Step "Unity (validacao $Course)" $unity @("-batchmode", "-nographics", "-projectPath", $P, "-executeMethod", "RedDust.EditorTools.SandboxValidation.Run", "-course", $Course, "-logFile", "$logs\unity_validate_$Course.log") "$logs\unity_validate_$Course.log" "\[RDD M1\]|error CS|Exception"
}
if ($Build) {
  $null = Step "Unity (build Windows)" $unity @("-batchmode", "-projectPath", $P, "-buildTarget", "Win64", "-executeMethod", "RedDust.EditorTools.BuildTools.BuildWindows", "-logFile", "$logs\unity_build.log") "$logs\unity_build.log" "error CS|\[RDD\]|error:"
}
