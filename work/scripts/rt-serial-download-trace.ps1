param([Parameter(Mandatory=$true)][string]$OutputFile,[Parameter(Mandatory=$true)][string]$LogPath)
$ErrorActionPreference='Stop'
$expectedLength=1056409
$expectedHash='ec276614e49400ebc621b2e029a79089df03d97dc84472acf26bb36f6f61dbf8'
$s=[IO.Ports.SerialPort]::new('COM3',115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$s.DtrEnable=$false; $s.RtsEnable=$false; $s.ReadBufferSize=1048576
$writer=[IO.StreamWriter]::new([IO.Path]::GetFullPath($LogPath),$false,[Text.UTF8Encoding]::new($false))
$part=[IO.Path]::GetFullPath($OutputFile)+'.part'
$stream=[IO.File]::Open($part,[IO.FileMode]::Create,[IO.FileAccess]::Write,[IO.FileShare]::None)
$sha=[Security.Cryptography.SHA256]::Create()
$records=@()
try {
    $s.Open(); $writer.Write($s.ReadExisting())
    for ($index=0;$index*16384 -lt $expectedLength;$index++) {
        $verified=$false
        for ($attempt=1;$attempt -le 3;$attempt++) {
            $begin="__CHUNK_B_$index`__"; $end="__CHUNK_E_$index`__"; $done="__CHUNK_D_$index`__"
            $read="dd if=/tmp/rt-trace-evidence.tar.gz bs=16384 skip=$index count=1 2>/dev/null"
            $command="printf '$begin\n'; $read | od -An -v -tx1 | tr -d ' \n'; printf '\n$end\n'; $read | sha256sum; printf '$done\n'"
            $s.Write($command+"`r")
            $response=[Text.StringBuilder]::new(); $deadline=[DateTime]::UtcNow.AddSeconds(30)
            do {
                Start-Sleep -Milliseconds 10
                [void]$response.Append($s.ReadExisting())
                if ($response.ToString() -match "(?m)^$done`r?`$") { break }
            } while ([DateTime]::UtcNow -lt $deadline)
            $raw=$response.ToString(); $writer.Write($raw); $writer.Flush()
            $match=[regex]::Match($raw,"(?ms)^$begin`r?`n([0-9a-f]+)`r?`n$end`r?`$")
            $hashMatch=[regex]::Match($raw,'(?m)^([0-9a-f]{64})\s+-\r?$')
            if (!$match.Success -or !$hashMatch.Success) { continue }
            $hex=$match.Groups[1].Value
            if (($hex.Length % 2) -ne 0) { continue }
            $bytes=[Convert]::FromHexString($hex)
            $localHash=[Convert]::ToHexString($sha.ComputeHash($bytes)).ToLowerInvariant()
            $length=[Math]::Min(16384,$expectedLength-$index*16384)
            if ($bytes.Length -ne $length -or $localHash -ne $hashMatch.Groups[1].Value) { continue }
            $stream.Write($bytes,0,$bytes.Length)
            $records+=@{chunk=$index;bytes=$bytes.Length;sha256=$localHash;attempt=$attempt}
            $verified=$true
            break
        }
        if (!$verified) { throw "Chunk $index failed verification after retries" }
        if (($index % 8) -eq 0) { Write-Output "Verified $([Math]::Min(($index+1)*16384,$expectedLength)) / $expectedLength bytes" }
    }
    $stream.Flush($true)
} finally {
    $stream.Dispose(); $writer.Dispose(); $sha.Dispose()
    if ($s.IsOpen) { $s.Close() }; $s.Dispose()
}
$actual=(Get-FileHash -LiteralPath $part -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expectedHash) { throw 'Whole-file hash mismatch' }
Move-Item -LiteralPath $part -Destination ([IO.Path]::GetFullPath($OutputFile)) -Force
@{bytes=$expectedLength;sha256=$actual;chunks=$records;verified=$true;serial_released=$true} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath ($OutputFile+'.json') -Encoding utf8
Write-Output "All chunks and final SHA-256 verified; serial released: $actual"
