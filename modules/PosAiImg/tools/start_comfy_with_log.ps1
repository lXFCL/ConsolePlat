$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$Comfy = Join-Path $Root "ComfyUI"
$LogDir = Join-Path $Root "logs"
$OutLog = Join-Path $LogDir "comfy_gesture_install_check.out.log"
$ErrLog = Join-Path $LogDir "comfy_gesture_install_check.err.log"
$Python = "C:\Users\Administrator\.conda\envs\posai-comfy\python.exe"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
foreach ($Log in @($OutLog, $ErrLog)) {
    if (Test-Path -LiteralPath $Log) {
        Remove-Item -LiteralPath $Log -Force
    }
}

Start-Process `
    -FilePath $Python `
    -ArgumentList @("main.py", "--listen", "127.0.0.1", "--port", "8188") `
    -WorkingDirectory $Comfy `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -WindowStyle Hidden

Write-Host $OutLog
Write-Host $ErrLog
