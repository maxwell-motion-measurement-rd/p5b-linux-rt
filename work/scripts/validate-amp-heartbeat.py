"""Check actual linked ELF and disassembly; does not validate board coexistence."""
import json
import pathlib
import re
import struct
import sys

root = pathlib.Path(sys.argv[1])
elf_name = sys.argv[2] if len(sys.argv)>2 else 'core3-heartbeat.elf'
data = (root / elf_name).read_bytes()
assert data[:6] == b'\x7fELF\x02\x01'
assert struct.unpack_from('<H', data, 18)[0] == 183
entry, phoff = struct.unpack_from('<QQ', data, 24)
phentsize, phnum = struct.unpack_from('<HH', data, 54)
assert entry == 0x60000000
segments = []
for i in range(phnum):
    kind, flags, off, va, pa, fs, ms, align = struct.unpack_from('<IIQQQQQQ', data, phoff + i*phentsize)
    if kind == 1:
        assert va == pa and 0x60000000 <= pa < pa+ms <= 0x60200000
        assert fs <= ms and off+fs <= len(data)
        segments.append(dict(start=hex(pa), end=hex(pa+ms), filesz=fs, memsz=ms))
assert segments
symbols = {}
for line in (root/'symbols.txt').read_text().splitlines():
    parts = line.split()
    if len(parts) == 3:
        symbols[parts[2]] = int(parts[0], 16)
assert symbols['vectors'] % 2048 == 0
assert symbols['l1_table'] % 4096 == symbols['l2_table'] % 4096 == 0
assert symbols['__stack_top'] % 16 == 0
assert symbols['__bss_end'] <= symbols['__stack_top'] <= 0x60200000
asm = (root/'disassembly.txt').read_text()
instructions = []
for line in asm.splitlines():
    m = re.match(r'\s*[0-9a-f]+:\s+[0-9a-f]{8}\s+(.+)', line)
    if m:
        instructions.append(m[1].lower())
assert instructions
for ins in instructions:
    assert not re.match(r'(dc|ic|smc|hvc)\s', ins), ins
    if ins.startswith('tlbi'):
        assert ins.strip() == 'tlbi\talle3' or re.fullmatch(r'tlbi\s+alle3', ins), ins
assert any(re.match(r'mrs\s+x0,\s*currentel', x) for x in instructions)
assert any(re.match(r'msr\s+daifset', x) for x in instructions)
assert not re.search(r'\bUND\b', (root/'symbols.txt').read_text())
print(json.dumps(dict(status='offline_checks_passed', load_segments=segments,
                     instructions=len(instructions), board_tested=False,
                     deployable=False,
                     pending=['boot-time reservation', 'PMU/ATF lifecycle', 'memory-type and security review', 'board validation']), indent=2))
