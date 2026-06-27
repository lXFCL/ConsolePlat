param(
    [string[]]$Only = @("ipadapter_sdxl_plus", "clip_vit_h", "openpose_sdxl"),
    [string]$BaseUrl = "https://huggingface.co"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$Models = Join-Path $Root "ComfyUI\models"
$LimitBytes = 30GB

$Jobs = @(
    @{
        Name = "ipadapter_sdxl_plus"
        Url = "$BaseUrl/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors"
        Dest = Join-Path $Models "ipadapter\ip-adapter-plus_sdxl_vit-h.safetensors"
    },
    @{
        Name = "clip_vit_h"
        Url = "$BaseUrl/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors"
        Dest = Join-Path $Models "clip_vision\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
    },
    @{
        Name = "openpose_sdxl"
        Url = "$BaseUrl/xinsir/controlnet-openpose-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors"
        Dest = Join-Path $Models "controlnet\controlnet-openpose-sdxl-1.0.safetensors"
    },
    @{
        Name = "canny_sdxl"
        Url = "$BaseUrl/xinsir/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors"
        Dest = Join-Path $Models "controlnet\controlnet-canny-sdxl-1.0.safetensors"
    }
)

function Format-Size([Int64]$Bytes) {
    if ($Bytes -ge 1GB) { return "{0:N2} GB" -f ($Bytes / 1GB) }
    if ($Bytes -ge 1MB) { return "{0:N2} MB" -f ($Bytes / 1MB) }
    if ($Bytes -ge 1KB) { return "{0:N2} KB" -f ($Bytes / 1KB) }
    return "$Bytes B"
}

$Selected = $Jobs | Where-Object { $Only -contains $_.Name }
if ($Selected.Count -eq 0) {
    throw "No matching model names. Requested: $($Only -join ', ')"
}

$Planned = 0
foreach ($Job in $Selected) {
    if (Test-Path -LiteralPath $Job.Dest) {
        Write-Host "exists: $($Job.Name)"
        continue
    }
    $Head = curl.exe -sS -L -I --retry 2 --connect-timeout 20 $Job.Url
    $LengthLine = $Head | Where-Object { $_ -match "^content-length:\s*\d+" } | Select-Object -Last 1
    if ($LengthLine -match "(\d+)") {
        $Planned += [Int64]$Matches[1]
    }
}

Write-Host "Planned new download: $(Format-Size $Planned)"
if ($Planned -gt $LimitBytes) {
    throw "Refusing to download more than 30GB: $(Format-Size $Planned)"
}

foreach ($Job in $Selected) {
    $Dest = $Job.Dest
    if (Test-Path -LiteralPath $Dest) {
        continue
    }
    $Dir = Split-Path -Parent $Dest
    New-Item -ItemType Directory -Force -Path $Dir | Out-Null
    $Part = "$Dest.part"
    Write-Host "Downloading $($Job.Name)"
    curl.exe -L --progress-bar -C - --retry 10 --retry-delay 5 --connect-timeout 30 -o $Part $Job.Url
    if ($LASTEXITCODE -ne 0) {
        throw "curl failed for $($Job.Name) with exit code $LASTEXITCODE"
    }
    Move-Item -Force -LiteralPath $Part -Destination $Dest
    $Size = (Get-Item -LiteralPath $Dest).Length
    Write-Host "Saved $Dest ($(Format-Size $Size))"
}
