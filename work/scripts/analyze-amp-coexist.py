"""Validate the captured 600-second heartbeat record, not the message path."""
import json, pathlib, re, sys

source = pathlib.Path(sys.argv[1])
raw = source.read_text(encoding='utf-8-sig').replace('\r','')
samples = []
pending = None
for line in raw.splitlines():
    m = re.fullmatch(r'SAMPLE (\d+) ([0-9.]+) ([0-9.]+)', line.strip())
    if m:
        pending = dict(index=int(m[1]), uptime_s=float(m[2]))
    elif pending is not None and line.startswith('attempted='):
        pending['status'] = dict(re.findall(r'(\w+)=([0-9a-f]+)', line))
    elif pending is not None and line.startswith('CPU_ONLINE '):
        pending['cpus'] = line.split(None,1)[1]
        samples.append(pending)
        pending = None
assert 'COEXIST_600S_COMPLETE' in raw, 'Run not complete'
assert [s['index'] for s in samples] == list(range(21)), 'Missing/duplicate samples'
expected = dict(attempted='1', result='0', pm_query='0', pm_state='1',
                magic='504d4143', version='2', core='3', el='12',
                state='1', reason='0', esr='0', elr='0', far='0')
for s in samples:
    assert s['cpus'] == '0-2', s
    for key,val in expected.items():
        assert s['status'].get(key) == val, (s['index'],key,s['status'].get(key))
    st = s['status']
    assert int(st['freq']) > 0 and st['freq'] == st['host_freq'] == st['configured_freq']
tokens = {s['status']['token'] for s in samples}
assert len(tokens) == 1, 'Core3 token changed'
elapsed = samples[-1]['uptime_s'] - samples[0]['uptime_s']
assert elapsed >= 600, elapsed
heartbeats = [int(s['status']['heartbeat']) for s in samples]
assert all(b>a for a,b in zip(heartbeats, heartbeats[1:])), 'Heartbeat stalled or reset'
report = dict(result='600s_heartbeat_coexistence_passed', samples=len(samples),
              elapsed_s=round(elapsed,2), linux_online='0-2', core3_el=3,
              core3_token=next(iter(tokens)), counter_frequency_hz=int(samples[0]['status']['freq']),
              heartbeat_start=heartbeats[0], heartbeat_end=heartbeats[-1],
              heartbeat_increment=heartbeats[-1]-heartbeats[0],
              observed_heartbeat_hz=round((heartbeats[-1]-heartbeats[0])/elapsed,4),
              image='r001 FIT with verified r002 temporary RAM module/firmware',
              message_echo_tested=False, pressure_tested=False,
              dmesg_review='required separately')
print(json.dumps(report,indent=2))
