from pathlib import Path
import gzip, hashlib, io, json, re, tarfile

root=Path(__file__).resolve().parents[2]
run=root/'logs/rt-diagnostics/2026-10-29/board-trace'
blob=(run/'trace-evidence.tar.gz').read_bytes()
assert hashlib.sha256(blob).hexdigest()=='ec276614e49400ebc621b2e029a79089df03d97dc84472acf26bb36f6f61dbf8'
allowed=set(['rt-pmu-stat.txt','ftrace-capture-mono.sh','ftrace-idle2.sh']+[d+'/'+n for d in ['rt-ftrace-short','rt-ftrace-idle2'] for n in ['buffer-stats.txt','cyclictest.txt','trace.txt.gz','trace_clock.txt']])
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as archive:
    assert set(archive.getnames())==allowed
    for member in archive.getmembers():
        assert member.isfile() and member.name in allowed
        dest=run/'exported'/member.name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(archive.extractfile(member).read())
for name,expected in [('rt-ftrace-short','3ff6a7acf3e29340d0aaa6f6276bcb2306e9bac6c1593da8771d440f70ffecf1'),('rt-ftrace-idle2','cb5936d106801a36abd0758e5eeca3f20f7077547d16f555aeb630bf8e10ccf3')]:
    raw=gzip.decompress((run/'exported'/name/'trace.txt.gz').read_bytes())
    assert hashlib.sha256(raw).hexdigest()==expected
    print(name, len(raw), 'decompressed bytes verified')
kernel=lambda p:re.findall(r'^\[\s*\d+\.\d+\].*$',p.read_text(encoding='utf-8'),re.M)
before,after=kernel(run/'01-verify.txt'),kernel(run/'08-postcheck.txt')
added=[line for line in after if line not in set(before)]
result={'before_kernel_lines':len(before),'after_kernel_lines':len(after),'kernel_log_identical':before==after,'added_kernel_messages':added}
(run/'postcheck.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
