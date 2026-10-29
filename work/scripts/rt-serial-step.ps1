param(
    [string]$Port = 'COM3',
    [string]$CommandFile,
    [Parameter(Mandatory=$true)][string]$LogPath,
    [int]$TimeoutSeconds = 25
)
$ErrorActionPreference = 'Stop'
$serial = [System.IO.Ports.SerialPort]::new($Port,115200,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$serial.Handshake = [System.IO.Ports.Handshake]::None
$serial.DtrEnable = $false
$serial.RtsEnable = $false
$serial.ReadBufferSize = 1048576
$output = [System.Text.StringBuilder]::new()
$finished = $false
try {
    $serial.Open()
    Start-Sleep -Milliseconds 300
    [void]$output.Append($serial.ReadExisting())
    if ($CommandFile) {
        $command = (Get-Content -LiteralPath $CommandFile -Raw).Trim()
        if ($command.Contains("`n")) { throw 'Use a single shell command line per step.' }
        $serial.Write($command + "; printf '\n__RT_STEP_DONE__\n'`r")
    } else { $serial.Write("`r") }
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        Start-Sleep -Milliseconds 150
        [void]$output.Append($serial.ReadExisting())
        if ($CommandFile -and $output.ToString() -match '(?m)^__RT_STEP_DONE__\r?$') { $finished=$true; break }
    } while ([DateTime]::UtcNow -lt $deadline)
    Start-Sleep -Milliseconds 250
    [void]$output.Append($serial.ReadExisting())
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
    [System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($LogPath),$output.ToString(),[System.Text.UTF8Encoding]::new($false))
}
Write-Output $output.ToString()
if ($CommandFile -and !$finished) { throw 'Completion marker not received; inspect saved log before further commands.' }
