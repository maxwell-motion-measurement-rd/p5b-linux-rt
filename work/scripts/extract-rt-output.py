import hashlib,re,sys
from pathlib import Path
raw=Path(sys.argv[1]).read_text(encoding='utf-8').replace('\r','')
m=re.search(r'^__DATA_BEGIN__\n(.*?)^__DATA_END__$',raw,re.M|re.S)
if not m: raise ValueError('Missing complete payload markers')
payload=m.group(1).encode('utf-8')
digest=hashlib.sha256(payload).hexdigest()
assert re.search(r'^'+digest+r'  /tmp/rt-audit-run/',raw,re.M), 'Board/local checksum mismatch'
Path(sys.argv[2]).write_bytes(payload)
print(Path(sys.argv[2]).name, len(payload), digest)
