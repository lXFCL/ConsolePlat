param(
    [string]$SourceDir = "E:\1PythonProject\PosAiImg\批量贴图结果\简约艺术字文字印花_BO-306-BO-505_随机主图200张_v2_2026-06-09",
    [string]$TargetDir = "E:\1PythonProject\PosAiImg\批量贴图结果\BO中等标题200"
)

$wordWhite = [string]([char]0x767d) + [string]([char]0x8272)
$wordBlack = [string]([char]0x9ed1) + [string]([char]0x8272)
$wordSimpleArt = [string]([char]0x7b80) + [string]([char]0x7ea6) + [string]([char]0x827a) + [string]([char]0x672f) + [string]([char]0x5b57)
$wordPrintT = [string]([char]0x5370) + [string]([char]0x82b1) + "T" + [string]([char]0x6064)
$wordSummer = [string]([char]0x590f) + [string]([char]0x5b63)
$wordArt = [string]([char]0x827a) + [string]([char]0x672f) + [string]([char]0x5b57)
$wordSimple = [string]([char]0x7b80) + [string]([char]0x7ea6)
$suffixes = @(
    ([string]([char]0x5706) + [string]([char]0x9886) + [string]([char]0x77ed) + [string]([char]0x8896) + " " + [string]([char]0x900f) + [string]([char]0x6c14) + [string]([char]0x5fae) + [string]([char]0x5f39) + [string]([char]0x9488) + [string]([char]0x7ec7) + [string]([char]0x4e0a) + [string]([char]0x8863) + " " + [string]([char]0x65e5) + [string]([char]0x5e38) + [string]([char]0x4f11) + [string]([char]0x95f2) + [string]([char]0x767e) + [string]([char]0x642d)),
    ([string]([char]0x5706) + [string]([char]0x9886) + [string]([char]0x77ed) + [string]([char]0x8896) + " " + [string]([char]0x900f) + [string]([char]0x6c14) + [string]([char]0x8212) + [string]([char]0x9002) + [string]([char]0x9488) + [string]([char]0x7ec7) + [string]([char]0x4e0a) + [string]([char]0x8863) + " " + [string]([char]0x6237) + [string]([char]0x5916) + [string]([char]0x4f11) + [string]([char]0x95f2) + [string]([char]0x65e5) + [string]([char]0x5e38) + [string]([char]0x767e) + [string]([char]0x642d)),
    ([string]([char]0x5706) + [string]([char]0x9886) + [string]([char]0x77ed) + [string]([char]0x8896) + " " + [string]([char]0x8f7b) + [string]([char]0x8584) + [string]([char]0x900f) + [string]([char]0x6c14) + [string]([char]0x9488) + [string]([char]0x7ec7) + [string]([char]0x4e0a) + [string]([char]0x8863) + " " + [string]([char]0x4f11) + [string]([char]0x95f2) + [string]([char]0x901a) + [string]([char]0x52e4) + [string]([char]0x65e5) + [string]([char]0x5e38) + [string]([char]0x767e) + [string]([char]0x642d)),
    ([string]([char]0x5706) + [string]([char]0x9886) + [string]([char]0x77ed) + [string]([char]0x8896) + " " + [string]([char]0x67d4) + [string]([char]0x8f6f) + [string]([char]0x900f) + [string]([char]0x6c14) + [string]([char]0x9488) + [string]([char]0x7ec7) + [string]([char]0x4e0a) + [string]([char]0x8863) + " " + [string]([char]0x590f) + [string]([char]0x5b63) + [string]([char]0x65e5) + [string]([char]0x5e38) + [string]([char]0x767e) + [string]([char]0x642d))
)

New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

$copied = 0
Get-ChildItem -LiteralPath $SourceDir -File -Filter "BO-*.png" | ForEach-Object {
    if ($_.BaseName -match '^(BO-\d+)_(.+)$') {
        $sku = $Matches[1]
        $oldTitle = $Matches[2]
        $color = ""
        if ($oldTitle.Contains($wordWhite)) { $color = $wordWhite }
        elseif ($oldTitle.Contains($wordBlack)) { $color = $wordBlack }

        $phrase = ""
        $start = $oldTitle.IndexOf($wordSimpleArt)
        if ($start -ge 0) {
            $start += $wordSimpleArt.Length
            $end = $oldTitle.IndexOf($wordPrintT, $start)
            if ($end -gt $start) {
                $phrase = $oldTitle.Substring($start, $end - $start).Replace(" ", "")
            }
        }

        $key = 0
        foreach ($ch in ($color + $phrase).ToCharArray()) { $key += [int][char]$ch }
        $suffix = $suffixes[$key % $suffixes.Count]
        $newTitle = $wordSummer + $color + $wordSimple + $wordArt + $phrase + $wordPrintT + " " + $suffix
        $newName = $sku + "_" + $newTitle + ".png"
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $TargetDir $newName) -Force
        $copied += 1
    }
}

Write-Output ("copied " + $copied)
