$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$sourceImage = Join-Path $workspace 'work/artifacts/rt-diagnostics/diagnostic/image.ub'
$expectedOriginal = 'f7c224640ad30359a731a5492f06769b4f081496c88fbe273022c48fd2789484'
$expectedDiagnostic = 'c81f2203d00dcc086fb0e42dc7e321b71f52be94bcf22f2254e37e474edbb943'
$expectedFiles = @{
    'image.ub' = $expectedOriginal
    'BOOT.BIN' = '1459d13f776071430d11c3d1476cd0a1bbfd1476609617a72e762602675d9b9b'
    'boot.scr' = '96a830a29dd3b3ba7063e6e916ead3b4df490c96c062a1854c41bd20fd4ef229'
}
function Hash([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$volume = Get-Volume -DriveLetter F
$disk = Get-Partition -DriveLetter F | Get-Disk
if ($volume.FileSystem -ne 'FAT32' -or $disk.BusType -ne 'USB' -or $disk.Number -ne 2 -or $disk.Size -ne 31954305024) { throw 'Unexpected SD target identity' }
if ((Hash $sourceImage) -ne $expectedDiagnostic) { throw 'Diagnostic source hash mismatch' }
foreach ($name in $expectedFiles.Keys) {
    if ((Hash (Join-Path 'F:\' $name)) -ne $expectedFiles[$name]) { throw "Unexpected current SD file: $name" }
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = Join-Path $workspace "work/artifacts/rt-diagnostics/sd-backup-$stamp"
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($name in $expectedFiles.Keys) {
    Copy-Item -LiteralPath (Join-Path 'F:\' $name) -Destination (Join-Path $backup $name)
    if ((Hash (Join-Path $backup $name)) -ne $expectedFiles[$name]) { throw "Backup mismatch: $name" }
}
$target = 'F:\image.ub'
$stage = "F:\image.ub.diag-stage-$stamp"
if (Test-Path -LiteralPath $stage) { throw 'Staging filename already exists' }
$inputStream = [IO.File]::OpenRead($sourceImage)
try {
    $outputStream = [IO.FileStream]::new($stage,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $inputStream.CopyTo($outputStream); $outputStream.Flush($true) } finally { $outputStream.Dispose() }
} finally { $inputStream.Dispose() }
if ((Hash $stage) -ne $expectedDiagnostic) { throw 'Staged SD image mismatch; original image retained' }
Move-Item -LiteralPath $stage -Destination $target -Force
if ((Hash $target) -ne $expectedDiagnostic) { throw 'Final SD image hash mismatch; restore verified backup before boot' }
foreach ($name in @('BOOT.BIN','boot.scr')) {
    if ((Hash (Join-Path 'F:\' $name)) -ne $expectedFiles[$name]) { throw "Unexpected change: $name" }
}
$record = [ordered]@{
    recorded_at = (Get-Date).ToString('o')
    target = $target
    disk_number = $disk.Number
    disk_bytes = $disk.Size
    filesystem = $volume.FileSystem
    backup_directory = $backup
    backup_files_sha256 = $expectedFiles
    deployed_image_sha256 = (Hash $target)
    deployed_image_bytes = (Get-Item -LiteralPath $target).Length
    boot_bin_and_boot_scr_unchanged = $true
    host_file_flush_completed = $true
    safe_removal_completed = $false
    hardware_boot_verified = $false
    ftrace_executed = $false
}
$json = $record | ConvertTo-Json -Depth 5
[IO.File]::WriteAllText((Join-Path $backup 'deployment.json'),$json,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $workspace 'logs/rt-diagnostics/2026-10-29/sd-deployment.json'),$json,[Text.UTF8Encoding]::new($false))
$json
