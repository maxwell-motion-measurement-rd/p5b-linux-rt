param([Parameter(Mandatory=$true)][string]$LocalFile,[Parameter(Mandatory=$true)][string]$RemoteName,[Parameter(Mandatory=$true)][string]$LogPath)
$ErrorActionPreference='Stop'
if ($RemoteName -notmatch '^(cyclictest|rtload)$') { throw 'Unexpected tool name' }
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
    Exchange 'rt_upload_saved_stty=$(stty -g); stty -echo; mkdir -p /tmp/rt-audit-tools' '__UPLOAD_BEGIN__'
    Exchange ": > /tmp/rt-audit-tools/$RemoteName.part" '__UPLOAD_EMPTY__'
    for ($offset=0; $offset -lt $bytes.Length; $offset+=192) {
        $count=[Math]::Min(192,$bytes.Length-$offset)
        $escaped=[Text.StringBuilder]::new()
        for ($i=0; $i -lt $count; $i++) { [void]$escaped.Append('\'+[Convert]::ToString($bytes[$offset+$i],8).PadLeft(3,'0')) }
        Exchange ("printf '"+$escaped.ToString()+"' >> /tmp/rt-audit-tools/$RemoteName.part") "__UPLOAD_$offset`__"
    }
    Exchange "chmod 755 /tmp/rt-audit-tools/$RemoteName.part; mv /tmp/rt-audit-tools/$RemoteName.part /tmp/rt-audit-tools/$RemoteName; sha256sum /tmp/rt-audit-tools/$RemoteName" '__UPLOAD_FINISH__'
} finally {
    if ($s.IsOpen) {
        try { Exchange 'stty "$rt_upload_saved_stty"; unset rt_upload_saved_stty' '__UPLOAD_RESTORE__' } catch { Write-Warning $_ }
        $s.Close()
    }
    $s.Dispose()
    [IO.File]::WriteAllText([IO.Path]::GetFullPath($LogPath),$log.ToString(),[Text.UTF8Encoding]::new($false))
}
Write-Output "Uploaded $RemoteName ($($bytes.Length) bytes); terminal restored and serial released."
