"""Recompute G5 pressure results from a hash-verified board evidence archive."""
import json
import pathlib
import sys
import tarfile

archive = pathlib.Path(sys.argv[1])
with tarfile.open(archive, 'r:gz') as tar:
    files = {}
    for member in tar.getmembers():
        name = pathlib.PurePosixPath(member.name)
        assert not name.is_absolute() and '..' not in name.parts
        if member.isfile():
            assert member.size < 20_000_000
            files[str(name)] = tar.extractfile(member).read()

def read(phase, name):
    return files[f'amp-g5/{phase}/{name}']

def obj(phase, name):
    return json.loads(read(phase, name))

def cpu_ticks(data):
    result = {}
    for line in data.decode().splitlines():
        columns = line.split()
        if columns and columns[0] in ('cpu0', 'cpu1', 'cpu2'):
            result[columns[0]] = list(map(int, columns[1:9]))
    return result

result = {'status': 'passed', 'phases': {}, 'cold_boots_verified': False}
unchanged = ('bad_rx', 'timeouts', 'stale', 'aborted', 'core3_bad', 'peer_timeouts',
    'busy', 'resets', 'host_lost', 'host_restored', 'peer_lost', 'peer_restored',
    'boot_token', 'service_epoch')
for phase in ('idle', 'cpu', 'mem'):
    assert read(phase, 'exit-code').strip() == b'0'
    before = obj(phase, 'snapshot-before.json')
    after = obj(phase, 'snapshot-after-cross.json')
    assert all(after[key] == before[key] for key in unchanged), (phase, 'counter changed')
    assert after['host_lost_active'] == 0
    assert after['linux_tx'] == after['core3_rx']
    assert after['linux_rx'] == after['core3_tx']
    assert after['linux_tx'] - before['linux_tx'] == 300003
    assert after['linux_rx'] - before['linux_rx'] == 300003
    assert after['heartbeat'] > before['heartbeat']
    assert after['host_heartbeat'] > before['host_heartbeat']
    assert read(phase, 'dmesg-before.txt') == read(phase, 'dmesg-after.txt')
    modes = {}
    for mode in ('forward', 'reverse', 'cross'):
        summary = obj(phase, f'{mode}.json')
        samples = []
        for index, line in enumerate(read(phase, f'{mode}.latency-ns').splitlines()):
            number, latency = map(int, line.split())
            assert number == index and latency > 0
            samples.append(latency)
        assert len(samples) == summary['passed'] == 60000
        assert summary['errors'] == 0 and summary['elapsed_ns'] >= 600_000_000_000
        samples.sort()
        metrics = {'min_us': samples[0] // 1000, 'max_us': samples[-1] // 1000,
            'mean_us': sum(samples) // len(samples) // 1000}
        for label, p in [('p50_us',500), ('p95_us',950), ('p99_us',990), ('p999_us',999)]:
            metrics[label] = samples[(len(samples)*p+999)//1000-1]//1000
        assert all(summary[key] == value for key,value in metrics.items()), (phase, mode)
        modes[mode] = dict(summary, measured_transactions_per_second=60000e9/summary['elapsed_ns'])
    start = cpu_ticks(read(phase, 'stat-before.txt'))
    end = cpu_ticks(read(phase, 'stat-after.txt'))
    usage = {}
    for cpu in start:
        delta = [b-a for a,b in zip(start[cpu], end[cpu])]
        usage[cpu] = 100*(sum(delta)-delta[3]-delta[4])/sum(delta)
    if phase != 'idle':
        for cpu in range(3):
            load = read(phase, f'load-{cpu}.txt').decode()
            assert 'stopped=1' in load and 'MEMORY_VERIFY_FAILED' not in load
            assert 'policy=SCHED_OTHER' in load
            if phase == 'mem': assert 'bytes_allocated=268435456' in load
        assert min(usage.values()) >= 90, (phase, 'insufficient CPU activity', usage)
    result['phases'][phase] = dict(modes=modes, cpu_utilization_percent=usage,
        before=before, after=after, telemetry_samples=read(phase,'telemetry.txt').count(b'SAMPLE '))

if 'amp-g5/recovery/results.out' in files:
    assert read('recovery', 'exit-code').strip() == b'0'
    recovery_rows = [json.loads(line) for line in read('recovery', 'results.out').splitlines()]
    assert recovery_rows[-1]['G5_RECOVERY_SUMMARY'] == 'passed'
    cases = recovery_rows[:-1]
    assert len(cases) == 20 and all(row['passed'] for row in cases)
    assert sum(row['case']=='app_killed_before_send' for row in cases) == 5
    assert sum(row['case']=='app_killed_waiting_reply' for row in cases) == 5
    assert sum(row['case']=='communication_service_reset' for row in cases) == 10
    assert all(row['recovered_echoes'] == 100 for row in cases)
    before,after = obj('recovery','before.json'),obj('recovery','after.json')
    for key,delta in dict(timeouts=30,bad_rx=0,core3_bad=20,peer_timeouts=0,
        aborted=5,resets=10,service_epoch=10,host_lost=0,host_restored=0,
        peer_lost=0,peer_restored=0,boot_token=0).items():
        assert after[key]-before[key] == delta, ('recovery',key)
    assert after['linux_tx'] == after['core3_rx'] and after['linux_rx'] == after['core3_tx']
    result['restart_and_service_reset'] = dict(cases=20, summary=recovery_rows[-1], before=before, after=after)

output = archive.parent / 'pressure-results.json'
output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
