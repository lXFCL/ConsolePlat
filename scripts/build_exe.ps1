param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$Environment = "flask"
)

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = $Root
python (Join-Path $PSScriptRoot "build_exe.py") --root $Root --env $Environment
