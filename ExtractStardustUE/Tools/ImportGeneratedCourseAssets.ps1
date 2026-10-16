param(
    [string]$GeneratedDir,
    [string]$UnrealEditor,
    [switch]$ForceMemoryDdc
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$ProjectFile = Join-Path $ProjectDir "ExtractStardustUE.uproject"
$ImportScript = Join-Path $PSScriptRoot "ImportGeneratedCourseAssets.py"

if ([string]::IsNullOrWhiteSpace($GeneratedDir)) {
	$GeneratedDir = Join-Path $ProjectDir "Saved\GeneratedCourse\red_dust_divide"
}
$GeneratedDir = (Resolve-Path -LiteralPath $GeneratedDir).Path

if ([string]::IsNullOrWhiteSpace($UnrealEditor)) {
	$UnrealEditor = Join-Path $env:ProgramFiles "Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
}
if (-not (Test-Path -LiteralPath $UnrealEditor -PathType Leaf)) {
	throw "UnrealEditor.exe não encontrado. Indica o caminho com -UnrealEditor."
}

$FbxFiles = @(Get-ChildItem -LiteralPath $GeneratedDir -Filter "red_dust_divide_*.fbx" -File |
	Where-Object { $_.Name -match '^red_dust_divide_(corridor|terrain)_\d+\.fbx$' })
if ($FbxFiles.Count -eq 0) {
	throw "Não foram encontrados FBX de percurso/terreno em: $GeneratedDir"
}

$ImportReport = Join-Path $GeneratedDir "unreal_import_report.json"
Remove-Item -LiteralPath $ImportReport -Force -ErrorAction SilentlyContinue

$PreviousGeneratedDir = $env:RDD_GENERATED_DIR
try {
	$env:RDD_GENERATED_DIR = $GeneratedDir
	$Arguments = @(
		"`"$ProjectFile`"",
		"-ExecutePythonScript=`"$ImportScript`"",
		"-unattended",
		"-nop4",
		"-nosplash",
		"-nullrhi",
		"-stdout",
		"-FullStdOutLogOutput"
	)
	if ($ForceMemoryDdc) {
		$Arguments += "-DDC-ForceMemoryCache"
	}
	$EditorProcess = Start-Process -FilePath $UnrealEditor -ArgumentList $Arguments -WorkingDirectory $ProjectDir -PassThru -Wait -WindowStyle Hidden
	if ($EditorProcess.ExitCode -ne 0) {
		throw "A importação do Unreal terminou com código $($EditorProcess.ExitCode)."
	}
	if (-not (Test-Path -LiteralPath $ImportReport -PathType Leaf)) {
		throw "O Unreal não criou o relatório de importação esperado: $ImportReport"
	}
	$Result = Get-Content -LiteralPath $ImportReport -Raw | ConvertFrom-Json
	if (-not $Result.success -or $Result.failed_sources.Count -gt 0 -or $Result.imported_assets -ne $FbxFiles.Count) {
		throw "Importação incompleta: $($Result | ConvertTo-Json -Compress)"
	}
}
finally {
	$env:RDD_GENERATED_DIR = $PreviousGeneratedDir
}

Write-Host "Importação concluída: $($FbxFiles.Count) FBX em /Game/Environment/Generated/RedDustDivide." -ForegroundColor Green
