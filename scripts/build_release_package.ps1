param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = $Root
python (Join-Path $PSScriptRoot "build_release_package.py") --root $Root
