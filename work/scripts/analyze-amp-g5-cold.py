"""Verify completed G5 cold cycles; never infer completion from a prepared directory."""
import hashlib
import json
import pathlib
import re

root=pathlib.Path(__file__).resolve().parents[2]
base=root/'logs/amp/2026-10-30/g5'
artifacts=root/'work/artifacts/amp-r004'
hashes={name:hashlib.sha256((artifacts/sub/name).read_bytes()).hexdigest()
    for name,sub in [('p5-core3-comm.bin','build'),('p5_core3_comm.ko','build'),
        ('g5_test','build-g5'),('g5_snapshot','build-g5')]}
zero=('bad_rx','timeouts','stale','aborted','core3_bad','peer_timeouts','busy','resets',
    'host_lost','host_restored','peer_lost','peer_restored','host_lost_active')
results=[]
for cycle in range(1,6):
    directory=base/f'cold-{cycle:02}'
    if not (directory/'test.txt').exists(): break
    boot_path=directory/'boot.txt'
    boot=boot_path.read_text(encoding='utf-8') if boot_path.exists() else ''
    boot_scope='FSBL/U-Boot/Linux'
    if 'Xilinx Zynq MP First Stage Boot Loader' not in boot or 'U-Boot 2020.01' not in boot:
        # A complete early boot transcript is evidence coverage, not a communication
        # acceptance condition. Permit only an explicitly recorded acquisition gap,
        # with user-confirmed power cycling and a captured fresh Linux startup.
        note=json.loads((directory/'boot-capture-note.json').read_text(encoding='utf-8'))
        assert note['user_confirmed_power_cycle'] is True
        partial=(directory/note['source']).read_text(encoding='utf-8')
        assert re.search(r'^\[\s+[0-4]\.\d+\]',partial,re.M)
        assert 'Run /init as init process' in partial and 'root@ALIENTEK-MP:~#' in partial
        assert 'Unmounting local filesystems...' in (directory/'poweroff.txt').read_text(encoding='utf-8')
        boot_scope='Linux partial; FSBL/U-Boot not captured (documented listener timeout)'
    pre=(directory/'preflight-ready.txt').read_text(encoding='utf-8')
    assert re.search(r'^5\.4\.0-rt1-xilinx-v2020\.2-p5b$',pre,re.M)
    assert re.search(r'^0-2$',pre,re.M) and not re.search(r'^p5_core3_comm ',pre,re.M)
    verified=(directory/'verified.txt').read_text(encoding='utf-8')
    for name,digest in hashes.items():
        assert re.search('^'+digest+'  /tmp/amp-r004/'+re.escape(name)+'$',verified,re.M)
    assert 'attempted=0 result=0 pm_query=0 pm_state=0 ' in verified
    assert re.search('^N$',verified,re.M)
    start=(directory/'start.txt').read_text(encoding='utf-8')
    assert re.search('^START_RC=0$',start,re.M)
    assert 'magic=504d4143 version=4 core=3 el=12 freq=99999000 ' in start
    assert 'state=1 reason=0 ' in start and 'esr=0 elr=0 far=0' in start
    test=(directory/'test.txt').read_text(encoding='utf-8')
    assert re.search('^COLD_COMM_RC=0$',test,re.M)
    assert re.search('^COLD_DMESG_CMP_RC=0$',test,re.M)
    assert re.search('^0-2$',test,re.M)
    rows=[json.loads(line) for line in test.splitlines() if line.startswith('{')]
    before,after=rows[0],rows[-1]
    modes=rows[1:-1]
    assert len(modes)==3 and {m['mode'] for m in modes}=={'forward','reverse','cross'}
    assert all(m['passed']==100 and m['errors']==0 and m['missed_release']==0 for m in modes)
    assert all(before[key]==after[key]==0 for key in zero)
    assert all(before[key]==0 and after[key]==503 for key in ('linux_tx','linux_rx','core3_tx','core3_rx'))
    assert after['heartbeat']>before['heartbeat'] and after['host_heartbeat']>before['host_heartbeat']
    assert before['boot_token']==after['boot_token']==before['service_epoch']==after['service_epoch']
    assert all(m['epoch']==after['service_epoch'] for m in modes)
    assert 'fault_tests=0' in test and 'esr=0 elr=0 far=0' in test
    results.append(dict(cycle=cycle,status='passed',boot_capture_scope=boot_scope,fault_tests=False,before=before,after=after,modes=modes))

result=dict(completed=len(results),required=5,status='passed' if len(results)==5 else 'in_progress',cycles=results)
(base/'cold-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(f'INDEPENDENT_COLD_VERIFICATION={len(results)}/5')
