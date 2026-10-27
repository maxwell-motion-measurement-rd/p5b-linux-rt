"""Read and write newc archives while retaining original Unix metadata."""
import gzip
import hashlib
import pathlib
import stat


def read_archive(path):
    data = gzip.decompress(pathlib.Path(path).read_bytes())
    entries = []
    offset = 0
    while offset + 110 <= len(data):
        start = offset
        magic = data[offset:offset + 6]
        if magic not in (b'070701', b'070702'):
            raise ValueError('Not a newc archive at offset %d' % offset)
        fields = [int(data[offset + 6 + i * 8:offset + 14 + i * 8], 16) for i in range(13)]
        offset += 110
        name = data[offset:offset + fields[11] - 1].decode('utf-8')
        if data[offset + fields[11] - 1] != 0:
            raise ValueError('Missing filename terminator')
        offset = (offset + fields[11] + 3) & ~3
        payload = data[offset:offset + fields[6]]
        if len(payload) != fields[6]:
            raise ValueError('Truncated payload')
        offset = (offset + fields[6] + 3) & ~3
        if name == 'TRAILER!!!':
            return entries
        normalized = name[2:] if name.startswith('./') else name
        if normalized.startswith('/') or '..' in pathlib.PurePosixPath(normalized).parts:
            raise ValueError('Unsafe archive path: %s' % name)
        entries.append({'name': name, 'path': normalized, 'fields': fields,
                        'data': payload, 'raw': data[start:offset]})
    raise ValueError('No cpio trailer')


def encode(name, fields, payload):
    fields = list(fields)
    name = name.encode('utf-8') + b'\0'
    fields[6] = len(payload)
    fields[11] = len(name)
    fields[12] = 0
    header = b'070701' + b''.join(('%08x' % value).encode('ascii') for value in fields)
    prefix = header + name
    prefix += b'\0' * (-len(prefix) % 4)
    result = prefix + payload
    return result + b'\0' * (-len(result) % 4)


def signature(entry):
    return (tuple(entry['fields'][:6] + entry['fields'][7:11]),
            hashlib.sha256(entry['data']).hexdigest())


if __name__ == '__main__':
    import sys
    entries = read_archive(sys.argv[1])
    paths = [entry['path'] for entry in entries]
    assert len(paths) == len(set(paths)), 'Duplicate archive paths'
    print('CPIO_ENTRIES=%d' % len(entries))
    print('DEVICE_NODES=%d' % sum(stat.S_ISCHR(e['fields'][1]) or stat.S_ISBLK(e['fields'][1]) for e in entries))
    for entry in entries:
        name = entry['path']
        if (name in ('init', 'sbin/init') or name.startswith('etc/modules') or
                name.startswith('etc/modprobe') or name in ('etc/init.d/modutils.sh',)):
            print('PATH=%s mode=%o uid=%d gid=%d nlink=%d' %
                  (name, entry['fields'][1], entry['fields'][2], entry['fields'][3], entry['fields'][4]))
            if stat.S_ISREG(entry['fields'][1]) or stat.S_ISLNK(entry['fields'][1]):
                print(entry['data'].decode('utf-8', errors='replace')[:2500])
