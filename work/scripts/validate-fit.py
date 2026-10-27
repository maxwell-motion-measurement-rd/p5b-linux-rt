import gzip
import hashlib
import json
import pathlib
import struct
from fdt_read import parse, string, cell

root = pathlib.Path('/home/wang/p5b-rt-5.4.0')
fit_path = root/'deploy/rt/image.ub'
fit = fit_path.read_bytes()
nodes = parse(fit)
default = string(nodes['/configurations']['default'])
config = nodes['/configurations/' + default]
expected = {'kernel': root/'build/arch/arm64/boot/Image.gz',
            'fdt': root/'build/dtb/system.dtb',
            'ramdisk': root/'staging/rootfs.cpio.gz'}
report = {'default_configuration': default, 'components': {}}
for key, path in expected.items():
    node_path = '/images/' + string(config[key])
    node = nodes[node_path]
    payload = node['data']
    digest = hashlib.sha256(payload).digest()
    assert payload == path.read_bytes(), 'FIT contains wrong %s' % key
    hashes = [props for name, props in nodes.items()
              if name.startswith(node_path + '/') and name.count('/') == node_path.count('/') + 1
              and props.get('algo') == b'sha256\0']
    assert len(hashes) == 1 and hashes[0]['value'] == digest, 'Bad FIT component hash'
    report['components'][key] = {'path': node_path, 'bytes': len(payload), 'sha256': digest.hex()}

kernel_node = nodes['/images/' + string(config['kernel'])]
image = (root/'build/arch/arm64/boot/Image').read_bytes()
assert gzip.decompress(kernel_node['data']) == image
assert image[56:60] == b'ARMd', 'Not an arm64 Image'
assert len(image) <= 60 * 1024 * 1024, 'Image exceeds existing U-Boot CONFIG_SYS_BOOTM_LEN'
image_span = struct.unpack_from('<Q', image, 16)[0]
load = cell(kernel_node['load'])
entry = cell(kernel_node['entry'])
assert load == entry == 0x80000
assert 0 < image_span < 0x10000000 - load
dtb = parse(nodes['/images/' + string(config['fdt'])]['data'])
cpus = {name: cell(props['reg']) for name, props in dtb.items()
        if name.startswith('/cpus/') and props.get('device_type') == b'cpu\0'}
assert cpus == {'/cpus/cpu@0': 0, '/cpus/cpu@1': 1, '/cpus/cpu@2': 2}
assert string(dtb['/chosen']['bootargs']) == 'earlycon console=ttyPS0,115200 rdinit=/init rw'
assert dtb['/memory']['reg'][:16] == struct.pack('>4I', 0, 0, 0, 0x7ff00000)
assert 0x10000000 + len(fit) < 0x7ff00000
report.update({'cpus': cpus, 'bootargs': string(dtb['/chosen']['bootargs']),
               'kernel_load': hex(load), 'kernel_entry': hex(entry),
               'kernel_image_memory_span': image_span, 'fit_load': '0x10000000',
               'uboot_decompression_limit_bytes': 60 * 1024 * 1024,
               'fit_bytes': len(fit), 'fit_sha256': hashlib.sha256(fit).hexdigest(),
               'hardware_boot_verified': False})
(root/'logs/fit-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
