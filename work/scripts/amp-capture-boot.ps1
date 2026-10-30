param([Parameter(Mandatory=$true)][string]$LogPath,[int]$Seconds=120)
$ErrorActionPreference='Stop'
$port=[IO.Ports.SerialPort]::new('COM3',115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$port.DtrEnable=$false; $port.RtsEnable=$false; $port.ReadBufferSize=1048576
$buffer=[Text.StringBuilder]::new(); $target=[IO.Path]::GetFullPath($LogPath)
try {
 $port.Open(); $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
 do {
  $chunk=$port.ReadExisting()
  if($chunk) { [void]$buffer.Append($chunk); [IO.File]::WriteAllText($target,$buffer.ToString(),[Text.UTF8Encoding]::new($false)) }
  if($buffer.ToString() -match 'root@ALIENTEK-MP:~#') { break }
  Start-Sleep -Milliseconds 200
 } while([DateTime]::UtcNow -lt $deadline)
} finally {
 if($port.IsOpen) {$port.Close()}; $port.Dispose()
 [IO.File]::WriteAllText($target,$buffer.ToString(),[Text.UTF8Encoding]::new($false))
}
Write-Output "BOOT_LOG=$target"
Write-Output ('LINUX_PROMPT_OBSERVED='+($buffer.ToString() -match 'root@ALIENTEK-MP:~#'))
