#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run Story Size Estimator (Python version) for Performance specs

.DESCRIPTION
    Runs story-size directly from Python source without needing
    the compiled executable.
#>

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$DocsDir = "D:\Atika\New Volume\New AK\Project\AK.Spec\Performance\specs"
$OutputDir = "D:\Atika\New Volume\New AK\Project\AK.Spec\Performance\story-size"

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Generate timestamped filename
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$OutputFile = Join-Path $OutputDir "story-size-$Timestamp.md"

# Validate
if (-not (Test-Path $DocsDir)) {
    Write-Host "Error: Docs directory not found: $DocsDir" -ForegroundColor Red
    exit 1
}

# Activate venv and run
$VenvActivate = Join-Path $ScriptRoot "venv\Scripts\Activate.ps1"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Story Size Estimator (Python)" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Activate virtual environment
if (Test-Path $VenvActivate) {
    & $VenvActivate
}

# Run Python script
python main.py main `
    --docs-dir $DocsDir `
    --output-md $OutputFile `
    --output enhanced

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Success! Report saved to: $OutputFile" -ForegroundColor Green
}
else {
    Write-Host "`n[ERROR] Failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
