param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
$venv = Join-Path $Root ".venv"
if (-not (Test-Path $venv)) {
    python -m venv $venv
}

$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $Root "requirements.txt")
& $python -m playwright install chromium

Write-Host "ConsolePlat environment ready: $venv"
