param([Parameter(Mandatory=$true)][string]$LocalFile,[Parameter(Mandatory=$true)][string]$RemoteName,[Parameter(Mandatory=$true)][string]$LogPath)
$ErrorActionPreference='Stop'
if ($RemoteName -notmatch '^(p5_core3_comm\.ko|p5-core3-comm\.bin|g3_test|g4_test)$') { throw 'Unexpected tool name' }
$bytes=[IO.File]::ReadAllBytes([IO.Path]::GetFullPath($LocalFile))
$s=[IO.Ports.SerialPort]::new('COM3',115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$s.DtrEnable=$false; $s.RtsEnable=$false
$log=[Text.StringBuilder]::new()
function Exchange([string]$cmd,[string]$marker) {
    $s.Write($cmd+"; printf '\n$marker\n'`r")
    $received=''; $end=[DateTime]::UtcNow.AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 10
        $new=$s.ReadExisting(); $received+=$new; [void]$log.Append($new)
        if ($received -match "(?m)^$marker`r?`$") { return }
    } while ([DateTime]::UtcNow -lt $end)
    throw "No acknowledgement: $marker"
}
try {
    $s.Open(); [void]$log.Append($s.ReadExisting())
    Exchange 'amp_upload_saved_stty=$(stty -g); stty -echo; mkdir -p /tmp/amp-r004' '__UPLOAD_BEGIN__'
    Exchange ": > /tmp/amp-r004/$RemoteName.part" '__UPLOAD_EMPTY__'
    for ($offset=0; $offset -lt $bytes.Length; $offset+=192) {
        $count=[Math]::Min(192,$bytes.Length-$offset)
        $escaped=[Text.StringBuilder]::new()
        for ($i=0; $i -lt $count; $i++) { [void]$escaped.Append('\'+[Convert]::ToString($bytes[$offset+$i],8).PadLeft(3,'0')) }
        Exchange ("printf '"+$escaped.ToString()+"' >> /tmp/amp-r004/$RemoteName.part") "__UPLOAD_$offset`__"
        if ($offset -gt 0 -and ($offset % 19200) -eq 0) { Write-Output "Transferred $offset / $($bytes.Length) bytes" }
    }
    Exchange "chmod 644 /tmp/amp-r004/$RemoteName.part; mv /tmp/amp-r004/$RemoteName.part /tmp/amp-r004/$RemoteName; sha256sum /tmp/amp-r004/$RemoteName" '__UPLOAD_FINISH__'
} finally {
    if ($s.IsOpen) {
        try { Exchange 'stty "$amp_upload_saved_stty"; unset amp_upload_saved_stty' '__UPLOAD_RESTORE__' } catch { Write-Warning $_ }
        $s.Close()
    }
    $s.Dispose()
    [IO.File]::WriteAllText([IO.Path]::GetFullPath($LogPath),$log.ToString(),[Text.UTF8Encoding]::new($false))
}
Write-Output "Uploaded $RemoteName ($($bytes.Length) bytes); terminal restored and serial released."
