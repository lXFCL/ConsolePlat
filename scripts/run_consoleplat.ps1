param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Local .venv not found, running setup first..."
    & (Join-Path $PSScriptRoot "setup_portable_env.ps1") -Root $Root
}

& $python (Join-Path $Root "main.py")
