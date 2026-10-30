param([Parameter(Mandatory=$true)][string]$LogPath)
$ErrorActionPreference='Stop'
$port=[IO.Ports.SerialPort]::new('COM3',115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$port.DtrEnable=$false; $port.RtsEnable=$false
$buffer=[Text.StringBuilder]::new()
try {
 $port.Open(); [void]$buffer.Append($port.ReadExisting()); $port.Write("poweroff`r")
 $deadline=[DateTime]::UtcNow.AddSeconds(20)
 do {
  Start-Sleep -Milliseconds 200; [void]$buffer.Append($port.ReadExisting())
  if($buffer.ToString() -match 'reboot: Power down|System halted') { break }
 } while([DateTime]::UtcNow -lt $deadline)
} finally {
 if($port.IsOpen) {$port.Close()}; $port.Dispose()
 [IO.File]::WriteAllText([IO.Path]::GetFullPath($LogPath),$buffer.ToString(),[Text.UTF8Encoding]::new($false))
}
$buffer.ToString()
