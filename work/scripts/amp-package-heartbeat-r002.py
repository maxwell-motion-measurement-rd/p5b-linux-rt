"""Build a separate, manual-start heartbeat initramfs; preserve old metadata."""
import gzip, hashlib, json, pathlib, stat
from cpio_newc import read_archive, encode, signature

r = pathlib.Path('/home/wang/p5-amp-20261030-r002')
b = pathlib.Path('/home/wang/p5b-rt-5.4.0')
old_entries = read_archive(b/'staging/rootfs.cpio.gz')
old = {e['path']: e for e in old_entries}
assert len(old) == len(old_entries)
epoch = int((b/'logs/source-date-epoch.txt').read_text())
old_dtb = (b/'build/dtb/system.dtb').read_bytes()
new_dtb = (r/'build/amp-candidate.dtb').read_bytes()
chunks, replaced = [], []
for e in old_entries:
    if e['path'].startswith('boot/') and e['data'] == old_dtb:
        assert e['fields'][4] == 1
        chunks.append(encode(e['name'], e['fields'], new_dtb))
        replaced.append(e['path'])
    else:
        chunks.append(e['raw'])
add = {}
for name in ['opt','opt/amp-heartbeat','lib/firmware']:
    if name not in old:
        add[name] = (stat.S_IFDIR | 0o755, b'')
add['opt/amp-heartbeat/p5_core3_boot.ko'] = (stat.S_IFREG | 0o644, (r/'linux/p5_core3_boot.ko').read_bytes())
add['lib/firmware/p5-core3-heartbeat.bin'] = (stat.S_IFREG | 0o644, (r/'build/p5-core3-heartbeat.bin').read_bytes())
add['opt/amp-heartbeat/IDENTITY'] = (stat.S_IFREG | 0o644, b'AMP heartbeat r002; Linux-managed PMU wake; manual start only; not communication acceptance\n')
ino = max(e['fields'][0] for e in old_entries) + 1
for name, (mode, payload) in add.items():
    assert name not in old
    fields = [ino,mode,0,0,2 if stat.S_ISDIR(mode) else 1,epoch,0,0,0,0,0,0,0]
    chunks.append(encode(name,fields,payload))
    ino += 1
chunks.append(encode('TRAILER!!!',[0]*13,b''))
data = b''.join(chunks)
data += b'\0' * (-len(data) % 512)
target = r/'build/amp-rootfs.cpio.gz'
with target.open('wb') as f:
    with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=epoch,compresslevel=9) as g:
        g.write(data)
after_entries = read_archive(target)
after = {e['path']:e for e in after_entries}
assert len(after) == len(after_entries)
assert set(after) == set(old) | set(add)
for name,e in old.items():
    if name in replaced:
        assert after[name]['data'] == new_dtb and signature(e)[0] == signature(after[name])[0]
    else:
        assert signature(e) == signature(after[name]), name
assert after['opt/amp-heartbeat/p5_core3_boot.ko']['data'].find(b'vermagic=5.4.0-rt1-xilinx-v2020.2-p5b ') >= 0
report = dict(old_entries=len(old), preserved_entries=len(old)-len(replaced),
              replaced_boot_dtbs=replaced, added_paths=list(add),
              rootfs_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              automatic_start=False, board_tested=False)
(r/'build/rootfs-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
