"""Package existing validated bytes; never build FIT or add automatic startup."""
import hashlib
import json
import pathlib
import re
import sys
import zipfile

root=pathlib.Path(__file__).resolve().parents[2]
commit=sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}',commit)
artifacts=root/'work/artifacts'
files={}
for name in ('BOOT.BIN','boot.scr','image.ub'):
    files['sd-base-r001/'+name]=(artifacts/'amp-r001/package/experiment'/name).read_bytes()
assert hashlib.sha256(files['sd-base-r001/image.ub']).hexdigest()=='4723c5a96151f3b75c70a10705b5e9d5a80b14b7d2753cf8daa3d7c70cd1d2a0'
for name in ('p5-core3-comm.bin','p5_core3_comm.ko','g3_test','g4_test'):
    files['ram-r004/'+name]=(artifacts/'amp-r004/build'/name).read_bytes()
for name in ('g5_test','g5_load','g5_snapshot','g5_recovery'):
    files['ram-r004/'+name]=(artifacts/'amp-r004/build-g5'/name).read_bytes()
for name in ('core3-comm.elf','core3-comm.map','symbols.txt','disassembly.txt','readelf.txt'):
    files['symbols-r004/'+name]=(artifacts/'amp-r004/build'/name).read_bytes()
files['IDENTITY.json']=(json.dumps(dict(source_commit=commit,base='r001 validated unchanged FIT',
    payload='r004 validated RAM files',automatic_start=False,new_fit_generated=False,
    core3_status_version=4,wire_version=1,kernel_release='5.4.0-rt1-xilinx-v2020.2-p5b'),indent=2)+'\n').encode()
files['README.md']=f'''# P5 AMP manual-load validation snapshot — 2026-10-30

This archive contains existing validated bytes, not a newly generated FIT.
Target: P5 XCZU4EV with the matching original hardware/firmware design.
Source commit: {commit}
Guide: https://github.com/nozomiiiii/p5b-linux-rt/blob/{commit}/docs/build/AMP-REPRODUCE.md
Results: https://github.com/nozomiiiii/p5b-linux-rt/blob/{commit}/docs/reports/amp-stage-summary-20261030.md

1. Check this ZIP against its external .sha256 file, extract to a new directory,
   then run `sha256sum -c SHA256SUMS` from the extracted root.
2. sd-base-r001/ contains the already validated base boot triplet. Back up the
   actual SD triplet before replacement; power down and read back hashes.
3. Boot Linux CPU0-2, then manually copy the matching RAM files to /tmp/amp-r004.
   Follow the guide: default fault_tests=N, query Core3 FORCEDOFF, wake once,
   verify version 4, heartbeat and communication. Insertion alone does not wake.
4. ram-r004/ also contains fault/recovery test tools. Those tests deliberately
   interrupt communication and require explicit fault_tests=1 before Core3 start.
   Do not run them on a client connected to real control work.

No init service or autostart was added. r004 must be manually reloaded after each
power cycle. A started Core3 pins its driver: no hot unload, force-reset or wake
retry. Preserve evidence and use a complete cold power cycle for recovery.
This validates minimal communication, not motor control or product hard realtime.
The 5th cold cycle lacks FSBL/U-Boot capture; the documented Linux and communication
checks passed. Original RT wakeup-latency issues remain separate.
'''.encode()
checks=''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name,data in sorted(files.items()))
files['SHA256SUMS']=checks.encode()
out=artifacts/'p5-amp-manual-r004-20261030.zip'
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name,data in sorted(files.items()):
        info=zipfile.ZipInfo(name,(2026,10,30,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o100644<<16
        archive.writestr(info,data)
with zipfile.ZipFile(out) as archive:
    assert archive.testzip() is None
    for name,data in files.items(): assert archive.read(name)==data
digest=hashlib.sha256(out.read_bytes()).hexdigest()
out.with_suffix(out.suffix+'.sha256').write_text(digest+'  '+out.name+'\n',encoding='ascii')
print(json.dumps(dict(path=str(out),bytes=out.stat().st_size,sha256=digest,source_commit=commit,automatic_start=False)))
