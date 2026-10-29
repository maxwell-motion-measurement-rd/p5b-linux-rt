"""Add explicit diagnostic tools without changing existing cpio entries."""
import gzip,hashlib,json,pathlib,sys,stat
root=pathlib.Path('/home/wang/p5-rt-diagnostics-20261029/kernel-image')
sys.path.insert(0,str(root/'scripts'))
from cpio_newc import read_archive,encode,signature
archive=root/'staging/rootfs.cpio.gz'
before=read_archive(archive)
old={e['path']:e for e in before}
epoch=int((root/'logs/source-date-epoch.txt').read_text())
ino=max(e['fields'][0] for e in before)+1
chunks=[e['raw'] for e in before]
add={}
for name in ['opt','opt/rt-diagnostics']:
    if name not in old:add[name]=(stat.S_IFDIR|0o755,b'')
paths={'cyclictest':'/home/wang/p5-rt-assess-tools-20261029/output/cyclictest',
       'rtload':'/home/wang/p5-rt-assess-tools-20261029/output/rtload',
       'perf':'/home/wang/p5-rt-diagnostics-20261029/perf-tool',
       'ftrace-short-capture.sh':'/home/wang/p5-rt-diagnostics-20261029/ftrace-short-capture.sh'}
for name,path in paths.items():
    full='opt/rt-diagnostics/'+name
    assert full not in old
    add[full]=(stat.S_IFREG|0o755,pathlib.Path(path).read_bytes())
for name,(mode,data) in add.items():
    fields=[ino,mode,0,0,2 if stat.S_ISDIR(mode) else 1,epoch,len(data),0,0,0,0,0,0]
    chunks.append(encode(name,fields,data));ino+=1
chunks.append(encode('TRAILER!!!',[0]*13,b''))
data=b''.join(chunks);data+=b'\0'*(-len(data)%512)
with archive.open('wb') as f:
    with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=epoch,compresslevel=9) as g:g.write(data)
after={e['path']:e for e in read_archive(archive)}
assert set(after)==set(old)|set(add)
for name,e in old.items():assert signature(e)==signature(after[name]),name
report={'existing_entries_preserved':len(old),'added_paths':list(add),'added_file_sha256':{n:hashlib.sha256(b).hexdigest() for n,(m,b) in add.items() if stat.S_ISREG(m)},'rootfs_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'automatic_startup_added':False}
(root/'logs/diagnostic-tools-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
