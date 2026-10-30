param([Parameter(Mandatory=$true)][ValidateRange(1,5)][int]$Cycle)
$ErrorActionPreference='Stop'
$dir=Join-Path $pwd ("logs/amp/2026-10-30/g5/cold-{0:D2}" -f $Cycle)
New-Item -ItemType Directory -Force $dir | Out-Null
foreach($name in @('p5-core3-comm.bin','p5_core3_comm.ko')) {
    & (Join-Path $pwd 'work/scripts/amp-serial-upload-r004.ps1') -LocalFile (Join-Path $pwd "work/artifacts/amp-r004/build/$name") -RemoteName $name -LogPath (Join-Path $dir "upload-$name.txt") | Out-Null
    Write-Output "UPLOADED=$name"
}
foreach($name in @('g5_test','g5_snapshot')) {
    & (Join-Path $pwd 'work/scripts/amp-serial-upload-g5.ps1') -LocalFile (Join-Path $pwd "work/artifacts/amp-r004/build-g5/$name") -RemoteName $name -LogPath (Join-Path $dir "upload-$name.txt") | Out-Null
    Write-Output "UPLOADED=$name"
}
$command='sha256sum /tmp/amp-r004/p5-core3-comm.bin /tmp/amp-r004/p5_core3_comm.ko /tmp/amp-r004/g5_test /tmp/amp-r004/g5_snapshot; chmod 755 /tmp/amp-r004/g5_test /tmp/amp-r004/g5_snapshot; mkdir -p /lib/firmware; cp /tmp/amp-r004/p5-core3-comm.bin /lib/firmware/p5-core3-comm.bin; insmod /tmp/amp-r004/p5_core3_comm.ko; printf "INSMOD_RC=%s\n" $?; cat /sys/module/p5_core3_comm/parameters/fault_tests; cat /sys/bus/platform/devices/core3-heartbeat/status'
[IO.File]::WriteAllText((Join-Path $dir 'insert.cmd'),$command,[Text.UTF8Encoding]::new($false))
& (Join-Path $pwd 'work/scripts/rt-serial-step.ps1') -CommandFile (Join-Path $dir 'insert.cmd') -LogPath (Join-Path $dir 'insert.txt')
