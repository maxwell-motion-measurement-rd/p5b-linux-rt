param([ValidateSet('idle','cpu','mem')][string]$Phase)
$ErrorActionPreference='Stop'
$dir=Join-Path $pwd 'logs/amp/2026-10-30/g5'
$index=0
while($true) {
    Start-Sleep -Seconds 45
    $index++
    $path=Join-Path $dir ("monitor-$Phase-{0:D3}.txt" -f $index)
    & (Join-Path $pwd 'work/scripts/rt-serial-step.ps1') -CommandFile (Join-Path $dir 'progress.cmd') -LogPath $path | Out-Null
    $raw=Get-Content $path -Raw
    $lines=$raw -split "`r?`n"
    Write-Output ([DateTimeOffset]::Now.ToString('o'))
    $lines | Where-Object {$_ -match '^(G5_PROGRESS|linux_tx=|PHASE_PASSED|G5_FAIL|[0-9]+\.[0-9]+ [0-9]+\.[0-9]+$)'} | Write-Output
    if($raw -match "(?m)^PHASE $Phase`r?`n([0-9]+)`r?`n") {
        Write-Output "PHASE_EXIT=$($Matches[1])"
        break
    }
}
