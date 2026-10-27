"""Replace only kernel modules and matching boot DTBs in the original initramfs."""
import gzip
import hashlib
import json
import os
import pathlib
import stat
from cpio_newc import read_archive, encode, signature

root = pathlib.Path('/home/wang/p5b-rt-5.4.0')
release = (root/'logs/kernelrelease.txt').read_text().strip()
original = read_archive(root/'inputs/rootfs.cpio.gz')
original_dtb = (root/'inputs/system.dtb').read_bytes()
new_dtb = (root/'build/dtb/system.dtb').read_bytes()
module_base = root/'staging/modules'
module_root = module_base/'lib/modules'
output = root/'staging/rootfs.cpio.gz'
assert (module_root/release/'modules.dep').is_file()
chunks, changed, removed = [], [], []
for entry in original:
    name = entry['path']
    if name == 'lib/modules' or name.startswith('lib/modules/'):
        removed.append(name)
        continue
    if name.startswith('boot/') and name.endswith('.dtb') and entry['data'] == original_dtb:
        assert entry['fields'][4] == 1, 'Unexpected hard-linked boot DTB'
        chunks.append(encode(entry['name'], entry['fields'], new_dtb))
        changed.append(name)
    else:
        chunks.append(entry['raw'])

next_ino = max(entry['fields'][0] for entry in original) + 1
epoch = int((root/'logs/source-date-epoch.txt').read_text().strip())
added = []
paths = [module_root] + list(module_root.rglob('*'))
paths.sort(key=lambda path: (len(path.relative_to(module_base).parts), str(path)))
for path in paths:
    name = path.relative_to(module_base).as_posix()
    if path.name in ('build', 'source') and path.is_symlink():
        continue
    info = path.lstat()
    if stat.S_ISREG(info.st_mode):
        payload = path.read_bytes()
        nlink = 1
    elif stat.S_ISDIR(info.st_mode):
        payload = b''
        nlink = 2
    elif stat.S_ISLNK(info.st_mode):
        payload = os.readlink(str(path)).encode('utf-8')
        nlink = 1
    else:
        raise RuntimeError('Unexpected module file type: %s' % path)
    assert next_ino < 2**32
    fields = [next_ino, info.st_mode, 0, 0, nlink, epoch, len(payload), 0, 0, 0, 0, 0, 0]
    chunks.append(encode(name, fields, payload))
    next_ino += 1
    added.append(name)
chunks.append(encode('TRAILER!!!', [0] * 13, b''))
archive = b''.join(chunks)
archive += b'\0' * (-len(archive) % 512)
with output.open('wb') as handle:
    with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=epoch, compresslevel=9) as stream:
        stream.write(archive)

result = read_archive(output)
old_map = {entry['path']: entry for entry in original}
new_map = {entry['path']: entry for entry in result}
assert len(new_map) == len(result), 'Duplicate output paths'
preserved = 0
for name, entry in old_map.items():
    if name in removed:
        assert name not in new_map or name in added
    elif name in changed:
        assert new_map[name]['data'] == new_dtb
        assert signature(entry)[0] == signature(new_map[name])[0]
    else:
        assert signature(entry) == signature(new_map[name]), 'Changed original metadata/data: %s' % name
        preserved += 1
assert set(new_map) == (set(old_map) - set(removed)) | set(added)
assert stat.S_ISLNK(new_map['init']['fields'][1])
assert new_map['init']['data'] == b'/sbin/init'
assert new_map['sbin/init']['data'] == b'/sbin/init.sysvinit'
assert stat.S_ISREG(new_map['sbin/init.sysvinit']['fields'][1])
assert new_map['sbin/init.sysvinit']['fields'][1] & 0o111
versions = {name.split('/')[2] for name in added if name.startswith('lib/modules/')}
assert versions == {release}
modules = [entry for entry in result if entry['path'].endswith('.ko')]
old_module_paths = {entry['path'].split('/', 3)[3] for entry in original if entry['path'].endswith('.ko')}
new_module_paths = {entry['path'].split('/', 3)[3] for entry in modules}
assert old_module_paths == new_module_paths, 'Old and new module sets differ'
for entry in modules:
    assert entry['fields'][2:4] == [0, 0]
    assert b'vermagic=' + release.encode('ascii') + b' ' in entry['data'], entry['path']
    assert b'preempt_rt' in entry['data'], entry['path']
assert any(entry['path'].endswith('/dmaproxy.ko') for entry in modules)
report = {'release': release, 'original_entries': len(original), 'output_entries': len(result),
          'preserved_entries': preserved, 'replaced_boot_dtbs': changed,
          'removed_old_module_entries': len(removed), 'new_module_entries': len(added),
          'kernel_modules': len(modules), 'archive_uncompressed_bytes': len(archive),
          'archive_compressed_bytes': output.stat().st_size,
          'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
          'verification': 'Original user-space payloads and Unix metadata preserved; modules match new release; init chain resolves.'}
(root/'logs/rootfs-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
