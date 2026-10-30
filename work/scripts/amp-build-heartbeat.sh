#!/bin/bash
set -euo pipefail
root=/home/wang/p5-amp-20261030-r001
project=/home/wang/petalinux/ALIENTEK-MP
prefix=/home/wang/tools/petalinux/2020.2/tools/xsct/gnu/aarch64/lin/aarch64-none/bin/aarch64-none-elf-
cp -p "$project/project-spec/hw-description/system.xsa" "$root/inputs/"
printf '6f6d739b8db1401329dd2abec4b6efe6c6a4eba3a420ab358e65b20e6e9d8231  %s\n' "$root/inputs/system.xsa" | sha256sum -c -
python3 - "$root" <<'PY'
import sys,zipfile,pathlib,xml.etree.ElementTree as ET
r=pathlib.Path(sys.argv[1])
with zipfile.ZipFile(str(r/'inputs/system.xsa')) as z:
    for n in ['xsa.json','xsa.xml','sysdef.xml','system.hwh']:
        (r/'inputs'/n).write_bytes(z.read(n))
    tree=ET.fromstring(z.read('system.hwh'))
    lines=[]
    for e in tree.iter():
        if e.tag.endswith('MEMRANGE') or (e.tag.endswith('PARAMETER') and any(k in e.get('NAME','') for k in ['DDR','CORTEXA53','TIMESTAMP'])):
            lines.append(ET.tostring(e,encoding='unicode'))
    (r/'inputs/hardware-memory.txt').write_text('\n'.join(lines))
PY
"${prefix}gcc" -c -mcpu=cortex-a53 -ffreestanding -nostdlib "$root/src/start.S" -o "$root/build/start.o"
"${prefix}ld" -T "$root/src/link.ld" -Map="$root/build/core3-heartbeat.map" -o "$root/build/core3-heartbeat.elf" "$root/build/start.o"
"${prefix}readelf" -h -l -S "$root/build/core3-heartbeat.elf" > "$root/build/readelf.txt"
"${prefix}objdump" -d "$root/build/core3-heartbeat.elf" > "$root/build/disassembly.txt"
"${prefix}nm" -n "$root/build/core3-heartbeat.elf" > "$root/build/symbols.txt"
cat "$root/build/readelf.txt"
sha256sum "$root"/src/* "$root"/build/core3-heartbeat.elf "$root"/inputs/system.xsa > "$root/SHA256SUMS"
printf '\nOFFLINE_BUILD_COMPLETE_NOT_DEPLOYABLE\n'
