"""Independently verify and extract G4 serial evidence (preserve board LF bytes)."""
import collections
import hashlib
import json
import pathlib
import re

root = pathlib.Path(__file__).resolve().parents[2]
folder = root / 'logs/amp/2026-10-30/g4'
raw = (folder / 'collected-raw.txt').read_text(encoding='utf-8')
match = re.search(r'^__G4_RESULTS_BEGIN__\n(.*?)^__G4_RESULTS_END__$', raw, re.M | re.S)
assert match, 'Missing result boundaries'
payload = match.group(1).encode('utf-8')
digest = hashlib.sha256(payload).hexdigest()
assert re.search(r'^' + digest + r'  /tmp/amp-r004/g4-results.out$', raw, re.M)
rows = [json.loads(line) for line in payload.decode().splitlines()]
cases = rows[:-1]
summary = rows[-1]
assert len(cases) == summary['cases'] == 250
assert summary['G4_SUMMARY'] == 'passed'
assert all(row['passed'] is True for row in cases)
assert len({(r['case'], r['kind'], r['iteration']) for r in cases}) == 250
counts = dict(collections.Counter(r['case'] for r in cases))
expected = dict(linux_to_core3_fault=80, core3_to_linux_fault=80,
    linux_sequence_wrap=10, core3_sequence_wrap=10, backpressure=10,
    core3_comm_pause=10, linux_consumer_pause=10, app_killed_before_send=5,
    app_killed_waiting_reply=5, communication_service_reset=10,
    core3_heartbeat_pause=10, linux_heartbeat_pause=10)
assert counts == expected
assert 'G4_EXIT_CODE=0\n' in raw and 'DMESG_CMP_RC=0\n' in raw
regression = (folder / 'regression.txt').read_text(encoding='utf-8')
normal = [json.loads(line) for line in regression.splitlines() if line.startswith('{')]
assert {r['mode'] for r in normal} == {'forward', 'reverse', 'cross'}
assert all(r['passed'] == 48 and r['errors'] == 0 for r in normal)
assert 'bad_rx=70 timeouts=150 stale=45' in regression
assert 'core3_bad=110' in regression and 'esr=0 elr=0 far=0' in regression
heartbeats = {}
for name in ('core3_heartbeat_pause', 'linux_heartbeat_pause'):
    values = [r['elapsed_ns'] for r in cases if r['case'] == name]
    heartbeats[name] = dict(min_ns=min(values), max_ns=max(values))
result = dict(status='passed', cases=250, groups=counts, board_stdout_sha256=digest,
    summary=summary, heartbeat_detection=heartbeats, regression=normal,
    dmesg_unchanged=True, g5_executed=False)
(folder / 'g4-results.out').write_bytes(payload)
(folder / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
