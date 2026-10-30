$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
function Get-Sha([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$expectedImage = '4723c5a96151f3b75c70a10705b5e9d5a80b14b7d2753cf8daa3d7c70cd1d2a0'
$backup = Get-Content -Raw -LiteralPath (Join-Path $workspace 'logs/amp/2026-10-30/g0/sd-backup.json') | ConvertFrom-Json
$driveInfo = [IO.DriveInfo]::new('F:\')
if ($driveInfo.DriveFormat -ne 'FAT32' -or $driveInfo.TotalSize -ne 31941722112 -or $backup.status -ne 'backup_verified') { throw 'Unexpected card or unverified backup' }
foreach ($property in $backup.files_sha256.PSObject.Properties) {
    if ((Get-Sha (Join-Path 'F:\' $property.Name)) -ne $property.Value) { throw "Card changed: $($property.Name)" }
    if ((Get-Sha (Join-Path $backup.backup_directory $property.Name)) -ne $property.Value) { throw "Backup changed: $($property.Name)" }
}
$sourceImage = Join-Path $workspace 'work/artifacts/amp-r001/package/experiment/image.ub'
if ((Get-Sha $sourceImage) -ne $expectedImage) { throw 'Source image mismatch' }
$stageImage = 'F:\image.ub.amp-r001-stage'
if (Test-Path -LiteralPath $stageImage) { throw 'Stage file already exists; inspect it before retrying' }
$sourceStream = [IO.File]::OpenRead($sourceImage)
try {
    $stageStream = [IO.FileStream]::new($stageImage,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $sourceStream.CopyTo($stageStream); $stageStream.Flush($true) } finally { $stageStream.Dispose() }
} finally { $sourceStream.Dispose() }
if ((Get-Sha $stageImage) -ne $expectedImage) { throw 'Stage mismatch; original image retained' }
Move-Item -LiteralPath $stageImage -Destination 'F:\image.ub' -Force
if ((Get-Sha 'F:\image.ub') -ne $expectedImage) { throw 'Final image mismatch; restore verified backup before boot' }
foreach ($name in @('BOOT.BIN','boot.scr')) {
    if ((Get-Sha (Join-Path 'F:\' $name)) -ne $backup.files_sha256.$name) { throw "Unexpected change: $name" }
}
$record = [ordered]@{
    status = 'image_written_and_readback_verified'
    target = 'F:\image.ub'
    image_bytes = (Get-Item -LiteralPath 'F:\image.ub').Length
    image_sha256 = $expectedImage
    actual_prior_image_sha256 = $backup.files_sha256.'image.ub'
    backup_directory = $backup.backup_directory
    boot_files_unchanged = $true
    file_flush_completed = $true
    safe_removal_completed = $false
    board_boot_verified = $false
    core3_started = $false
}
$json = $record | ConvertTo-Json -Depth 5
[IO.File]::WriteAllText((Join-Path $workspace 'logs/amp/2026-10-30/g0/sd-deployment.json'),$json,[Text.UTF8Encoding]::new($false))
$json
