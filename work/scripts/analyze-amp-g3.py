"""Cross-check board result summaries, raw latencies, and both endpoint counters."""
import hashlib, json, pathlib, re, sys
r=pathlib.Path(sys.argv[1])
def summaries(path):
    rows=[]
    for line in path.read_text(encoding='utf-8-sig').replace('\r','').splitlines():
        if line.startswith('{"mode":'):
            rows.append(json.loads(line))
    return rows
smoke=summaries(r/'smoke.txt')
full=summaries(r/'batch-results.txt')
assert {x['mode']:x['passed'] for x in smoke}==dict(forward=48,reverse=48,cross=48)
assert {x['mode']:x['passed'] for x in full}==dict(forward=10000,reverse=10000,cross=100)
assert len(smoke)==len(full)==3
assert all(x['errors']==0 for x in smoke+full)
assert len({x['session'] for x in smoke+full})==6
assert len({x['epoch'] for x in smoke+full})==1
text=(r/'batch-results.txt').read_text(encoding='utf-8-sig').replace('\r','')
assert re.search(r'^G3_BATCH_COMPLETE$',text,re.M)
assert re.search(r'^BATCH_EXIT=0$',text,re.M)
assert re.search(r'^DMESG_CMP_RC=0$',text,re.M)
stats_lines=re.findall(r'^linux_tx=.*$',text,re.M)
assert stats_lines
stats={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',stats_lines[-1])}
expected_frames=sum(1+x['passed']*(1 if x['mode']=='forward' else 2) for x in smoke+full)
for key in ['linux_tx','linux_rx','core3_tx','core3_rx']:
    assert stats[key]==expected_frames,(key,stats[key],expected_frames)
for key in ['bad_rx','timeouts','stale','core3_bad']:
    assert stats[key]==0,(key,stats[key])
status_lines=re.findall(r'^attempted=.*$',text,re.M)
assert status_lines
status=dict(re.findall(r'(\w+)=([0-9a-f]+)',status_lines[-1]))
for key,value in dict(attempted='1',result='0',pm_query='0',pm_state='1',magic='504d4143',
                      version='3',core='3',el='12',state='1',reason='0',esr='0',elr='0',far='0').items():
    assert status.get(key)==value,(key,status.get(key))
assert int(status['token'])==full[0]['epoch']
assert re.search(r'^CPU_ONLINE 0-2$',text,re.M)
raw=(r/'latencies-raw.txt').read_text(encoding='utf-8-sig').replace('\r','')
for row in full:
    mode=row['mode']; marker=mode.upper()
    block=re.search(r'^__LATENCY_'+marker+r'_BEGIN__\n(.*?)^__LATENCY_'+marker+r'_END__$',raw,re.M|re.S)
    assert block,mode
    pairs=[tuple(map(int,m)) for m in re.findall(r'^(\d+) (\d+)$',block[1],re.M)]
    assert [i for i,t in pairs]==list(range(row['passed'])),mode
    times=[t for i,t in pairs]; ordered=sorted(times); n=len(times)
    calculated=dict(min_us=ordered[0]//1000,max_us=ordered[-1]//1000,mean_us=sum(times)//n//1000)
    for label,p in [('p50_us',500),('p95_us',950),('p99_us',990),('p999_us',999)]:
        calculated[label]=ordered[(n*p+999)//1000-1]//1000
    for key,val in calculated.items(): assert row[key]==val,(mode,key,row[key],val)
    artifact=r/(mode+'-latency-ns.txt')
    artifact.write_bytes(''.join('%d %d\n'%pair for pair in pairs).encode('ascii'))
    digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
    checksum=re.search(r'^([0-9a-f]{64})  /tmp/amp-g3-'+mode+r'\.latency-ns$',raw,re.M)
    assert checksum and checksum[1]==digest,('latency export checksum',mode)
    row['latency_sha256']=digest
    row['observed_transactions_hz']=round(n*1e9/row['elapsed_ns'],4)
result=dict(result='G3_passed',full=full,smoke=smoke,frames_each_direction=expected_frames,
            counters=stats,dmesg='before and after byte-identical',linux_online='0-2',
            runtime='r001 base image plus verified r003 RAM module/firmware/test binary',
            recovery_tested=False,pressure_tested=False)
(r/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
