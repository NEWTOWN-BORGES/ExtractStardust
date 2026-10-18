param(
	[string]$BlenderExe,
	[string]$CourseSpec
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $ProjectDir

if ([string]::IsNullOrWhiteSpace($CourseSpec)) {
	$CourseSpec = Join-Path $RepoRoot "ExtractStardustRDD\Art\Courses\red_dust_divide.json"
}
$CourseSpec = (Resolve-Path -LiteralPath $CourseSpec).Path

if ([string]::IsNullOrWhiteSpace($BlenderExe)) {
	$BlenderCommand = Get-Command blender.exe -ErrorAction SilentlyContinue
	if ($BlenderCommand) {
		$BlenderExe = $BlenderCommand.Source
	}
	else {
		$BlenderRoots = @("$env:ProgramFiles\Blender Foundation", "${env:ProgramFiles(x86)}\Blender Foundation")
		$BlenderExe = $BlenderRoots |
			Where-Object { Test-Path -LiteralPath $_ } |
			ForEach-Object { Get-ChildItem -LiteralPath $_ -Directory | Sort-Object Name -Descending } |
			ForEach-Object { Join-Path $_.FullName "blender.exe" } |
			Where-Object { Test-Path -LiteralPath $_ } |
			Select-Object -First 1
	}
}
if ([string]::IsNullOrWhiteSpace($BlenderExe) -or -not (Test-Path -LiteralPath $BlenderExe)) {
	throw "Blender não encontrado. Instala-o ou indica o caminho com -BlenderExe."
}
$BlenderExe = (Resolve-Path -LiteralPath $BlenderExe).Path

$Spec = Get-Content -LiteralPath $CourseSpec -Raw | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($Spec.name)) {
	throw "A especificação não contém o campo 'name'."
}
$CourseName = [string]$Spec.name
$Builder = Join-Path $RepoRoot "ExtractStardustRDD\Art\Blender\rdd_build_route.py"
$GeneratedDir = Join-Path $ProjectDir "Saved\GeneratedCourse\$CourseName"
$TracksDir = Join-Path $ProjectDir "Content\Tracks"
New-Item -ItemType Directory -Path $GeneratedDir -Force | Out-Null

Write-Host "A gerar '$CourseName' com Blender. Este processo pode demorar." -ForegroundColor Cyan
& $BlenderExe -b --factory-startup -P $Builder -- $CourseSpec $GeneratedDir
if ($LASTEXITCODE -ne 0) {
	throw "O construtor Blender terminou com código $LASTEXITCODE. Não foram copiados dados para Content/Tracks."
}

$CourseFile = Join-Path $GeneratedDir "${CourseName}_course.bytes"
$GraphFile = Join-Path $GeneratedDir "${CourseName}_graph.bytes"
foreach ($File in @($CourseFile, $GraphFile)) {
	if (-not (Test-Path -LiteralPath $File -PathType Leaf)) {
		throw "Ficheiro de pista esperado não foi criado: $File"
	}
}
foreach ($Check in @(
	@{ File = $CourseFile; Signature = "RDDC" },
	@{ File = $GraphFile; Signature = "RDDG" }
)) {
	$Stream = [System.IO.File]::OpenRead($Check.File)
	try {
		$Reader = [System.IO.BinaryReader]::new($Stream)
		$Signature = [System.Text.Encoding]::ASCII.GetString($Reader.ReadBytes(4))
		if ($Signature -ne $Check.Signature) {
			throw "Assinatura inválida em $($Check.File): esperado $($Check.Signature), recebido $Signature."
		}
	}
	finally {
		$Stream.Dispose()
	}
}

New-Item -ItemType Directory -Path $TracksDir -Force | Out-Null
Copy-Item -LiteralPath $CourseFile -Destination (Join-Path $TracksDir "sandbox_course.bytes") -Force
Copy-Item -LiteralPath $GraphFile -Destination (Join-Path $TracksDir "sandbox_graph.bytes") -Force
Write-Host "RDDC/RDDG validados e copiados para Content/Tracks." -ForegroundColor Green
Write-Host "FBX e pré-visualização para importar/ver: $GeneratedDir" -ForegroundColor Yellow
